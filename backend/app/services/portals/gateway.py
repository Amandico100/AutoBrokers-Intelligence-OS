# -*- coding: utf-8 -*-
"""PortalExecutionGateway — a ponte única do Work OS para o Portal Worker.

SPEC-075 Bloco B. Este módulo é o **único** lugar onde um pedido de negócio
vira um `portal_job`. Não é um segundo Tool Gateway: quem autoriza continua
sendo `capabilities` + `tool_definitions` + Tool Gateway + approval. Aqui a
autorização é **revalidada** e o pedido é **traduzido**.

O que a ponte resolve, na ordem (SPEC-075 §10.2)
=================================================
    1  company_id presente
    2  a ação autorizada bate com a que a journey faz     ← §9.2, fail-closed
    3  a operação existe no registro
    4  que portal atende esta operação
    5  que conta desta corretora entra nesse portal
    6  a journey que implementa a operação NAQUELE portal
    7  idempotência, quando material
    8  abre a tool_invocation
    9  cria o portal_job com linhagem
   10  espera OU devolve o handle
   11  traduz para o resultado canônico
   12  fecha a tool_invocation

Nenhum desses passos é decidido por LLM. O modelo diz o RESULTADO que quer; o
resto é código lendo registro.

Por que a ponte nasce em `legacy`
==================================
🔴 `PORTAL_EXECUTION_GATEWAY_MODE` tem três valores e o default é `legacy`. Em
`legacy` este módulo não executa nada — os chamadores atuais seguem como estão.
Em `shadow` ele RESOLVE e registra o que teria feito, sem criar job. Só em `on`
ele executa.

Isso não é excesso de cuidado: `billing_collection` e `portal_tool` funcionam
hoje, em produção, com dinheiro de corretora e pedidos no nome de segurados.
Uma ponte nova que se prove igual em sombra antes de assumir é a diferença
entre migrar e apostar. É o mesmo desenho que o `TOOL_GATEWAY_MODE` já usa
nesta casa — e que já pagou por si (📊 51 diffs registrados em sombra na
madrugada de 15→16/08 sem afetar nenhuma execução).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Callable, Dict, Optional

from app.services.portals import contracts as C
from app.services.portals.resolver import (
    CONTA_AMBIGUA, CONTA_AUSENTE, CONTA_DE_OUTRA_CORRETORA, CONTA_INDISPONIVEL,
    resolver_conta, resolver_portal,
)

logger = logging.getLogger(__name__)

# Teto de espera no modo `await`. Alinhado ao `POLL_TIMEOUT_S=150` que o
# `portal_tool` já usa — o agente que espera está numa conversa de WhatsApp, e
# ninguém segura um segurado esperando mais que isso.
ESPERA_MAXIMA_S = int(os.getenv("PORTAL_GATEWAY_WAIT_S", "150") or 150)
ESPERA_ENTRE_LEITURAS_S = 5

STATUS_TERMINAIS = ("done", "needs_human", "failed")
STATUS_EM_CURSO = ("queued", "running")


def modo_do_gateway() -> str:
    """`legacy` | `shadow` | `on`. Valor irreconhecível vira `legacy`."""
    return C.modo_valido(os.getenv("PORTAL_EXECUTION_GATEWAY_MODE"), C.MODO_LEGACY)


# --------------------------------------------------------------------------
# Tradução de estado técnico → estado de NEGÓCIO (Bloco H)
# --------------------------------------------------------------------------
def traduzir_estado(job: Dict[str, Any]) -> str:
    """O que aconteceu, na linguagem de quem pediu.

    🔴 O status técnico do job NÃO é a resposta. A SPEC-074 provou o custo
    disso: um job `failed` pode ter deixado um atendimento aberto na
    seguradora, e responder "falhou" convida o segurado a pedir de novo — um
    segundo pedido, pago, no nome dele.

    Por isso a ordem aqui é: primeiro a prova de efeito, depois o rótulo.
    """
    evidence = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
    status = str(job.get("status") or "").strip()

    # 1º — o mundo. Efeito incerto vence qualquer rótulo.
    try:
        from portal_worker.guardrails import (
            FASES_INCERTAS, fase_do_efeito, tem_prova_de_efeito,
        )

        fase = fase_do_efeito(evidence)
        if fase in FASES_INCERTAS and not tem_prova_de_efeito(evidence):
            return C.NEGOCIO_TALVEZ_COMMITADO
    except Exception:  # noqa: BLE001
        # Sem o guardrails (contexto sem portal_worker), a leitura direta ainda
        # protege o caso que importa.
        efeito = evidence.get("critical_effect")
        if isinstance(efeito, dict) and str(efeito.get("phase") or "") in (
                "armed", "submitted", "unknown"):
            return C.NEGOCIO_TALVEZ_COMMITADO

    # 2º — estado de negócio que a própria journey declarou (SPEC-074).
    vidros = evidence.get("vidros_estado")
    if isinstance(vidros, dict) and vidros.get("estado") == "aguardando_escolha_do_segurado":
        return C.NEGOCIO_PRECISA_HUMANO

    # 3º — o rótulo técnico.
    if status == "done":
        capt = job.get("params") or {}
        if isinstance(capt, dict) and capt.get("_nada_a_fazer"):
            return C.NEGOCIO_NADA_A_FAZER
        return C.NEGOCIO_OK
    if status == "needs_human":
        return C.NEGOCIO_PRECISA_HUMANO
    if status in STATUS_EM_CURSO:
        return C.NEGOCIO_PRECISA_HUMANO  # ainda não terminou; quem espera decide
    return C.NEGOCIO_FALHOU


# --------------------------------------------------------------------------
# O Gateway
# --------------------------------------------------------------------------
class PortalExecutionGateway:
    """Ponte de provider. Recebe pedido de negócio, devolve resultado canônico.

    O `supabase` é injetado; o `agora` e o `dormir` também, para que o teste
    possa exercer o laço de espera sem esperar de verdade. Isso não é enfeite:
    um laço de espera que só é testado com `sleep` real nunca é testado no
    caminho que importa — o do timeout.
    """

    def __init__(self, supabase: Any, *,
                 agora: Optional[Callable[[], float]] = None,
                 dormir: Optional[Callable[[float], Any]] = None) -> None:
        self.supabase = supabase
        self._agora = agora or time.monotonic
        self._dormir = dormir or time.sleep

    # -- passo 2 a 6: resolução pura, sem escrever nada -------------------
    def resolver(self, req: C.PortalExecutionRequest) -> Dict[str, Any]:
        """Resolve tudo que dá para resolver SEM criar job.

        Separado da execução de propósito: é exatamente isto que o modo
        `shadow` roda, e é isto que um teste consegue exercer sem banco.
        """
        from portal_worker.journeys import (
            conflito_de_efeito, journey_para_operacao,
        )

        if not str(req.company_id or "").strip():
            return {"ok": False, "resultado": C.recusa(
                C.NEGOCIO_NAO_AUTORIZADO, "company_id ausente",
                operation_key=req.operation_key)}

        portal_key, motivo_portal = resolver_portal(
            req.operation_key,
            insurer_key=req.insurer_key,
            portal_key_hint=req.portal_key_hint,
            hint_confiavel=req.hints_utilizaveis())
        if not portal_key:
            return {"ok": False, "resultado": C.recusa(
                C.NEGOCIO_NAO_SUPORTADO, motivo_portal,
                operation_key=req.operation_key)}

        definicao = journey_para_operacao(portal_key, req.operation_key)
        if definicao is None:
            return {"ok": False, "resultado": C.recusa(
                C.NEGOCIO_NAO_SUPORTADO,
                f"`{portal_key}` nao tem journey para `{req.operation_key}`",
                operation_key=req.operation_key, portal_key=portal_key)}

        # 🔴 §9.2 — a autorização recebida não pode ser mais fraca que o efeito
        # que a journey produz. Este é o portão que impede uma tool autorizada
        # como leitura de acabar criando um pedido.
        if req.effect_class_autorizada:
            reprova, motivo = conflito_de_efeito(
                req.effect_class_autorizada, definicao.effect_class)
            if reprova:
                return {"ok": False, "resultado": C.recusa(
                    C.NEGOCIO_NAO_AUTORIZADO, motivo,
                    operation_key=req.operation_key, portal_key=portal_key,
                    pode_repetir=False)}

        conta = resolver_conta(
            self.supabase, company_id=req.company_id, portal_key=portal_key,
            account_id_hint=req.account_id_hint,
            hint_confiavel=req.hints_utilizaveis())
        if not conta.pode_executar:
            estado = {
                CONTA_AUSENTE: C.NEGOCIO_SEM_CONEXAO,
                CONTA_AMBIGUA: C.NEGOCIO_PRECISA_HUMANO,
                CONTA_DE_OUTRA_CORRETORA: C.NEGOCIO_NAO_AUTORIZADO,
                CONTA_INDISPONIVEL: C.NEGOCIO_SEM_CONEXAO,
            }.get(conta.estado, C.NEGOCIO_SEM_CONEXAO)
            return {"ok": False, "resultado": C.recusa(
                estado, conta.motivo, operation_key=req.operation_key,
                portal_key=portal_key,
                pode_repetir=(conta.estado != CONTA_DE_OUTRA_CORRETORA))}

        return {"ok": True, "portal_key": portal_key, "definicao": definicao,
                "conta": conta, "motivo_portal": motivo_portal}

    # -- passo 7: idempotência --------------------------------------------
    def chave_de_idempotencia(self, req: C.PortalExecutionRequest,
                              definicao: Any) -> Optional[str]:
        """A chave, quando o efeito é material. `None` para leitura.

        Se o chamador trouxe uma chave, ela vence — ele conhece o negócio
        melhor que a ponte. `portal_params.chave_de_idempotencia` continua
        sendo a autoridade para vidros, e é ela que chega aqui pronta.

        Sem chave do chamador, a ponte deriva uma da impressão do pedido. É
        pior que uma chave de negócio (não sabe que "vidro da porta" e "vidro
        de porta" são a mesma coisa), mas é infinitamente melhor que nenhuma.
        """
        if not C.precisa_de_idempotencia(getattr(definicao, "effect_class", "")):
            return None
        if req.idempotency_key:
            return str(req.idempotency_key)
        return f"gw:{req.impressao_do_pedido()}"

    def procurar_pedido_vivo(self, company_id: str,
                             chave: str) -> Optional[Dict[str, Any]]:
        """Já existe job vivo para esta chave nesta corretora?

        Mesma regra que a SPEC-074 provou necessária: `failed` **com prova de
        efeito** é um pedido vivo disfarçado, e tratá-lo como morto libera o
        segundo pedido pago.
        """
        if not chave:
            return None
        try:
            r = (self.supabase.table("portal_jobs")
                 .select("id, status, evidence, error, created_at, idempotency_key")
                 .eq("company_id", company_id)
                 .eq("idempotency_key", chave)
                 .order("created_at", desc=True)
                 .limit(5).execute())
        except Exception:  # noqa: BLE001
            logger.warning("[portais] busca de pedido vivo indisponivel")
            return None

        for linha in (r.data or []):
            job = dict(linha)
            if str(job.get("status")) != "failed":
                return job
            try:
                from portal_worker.guardrails import tem_prova_de_efeito

                if tem_prova_de_efeito(job.get("evidence")):
                    return job
            except Exception:  # noqa: BLE001
                ev = job.get("evidence")
                if isinstance(ev, dict) and str(ev.get("protocolo") or "").strip():
                    return job
        return None

    # -- passo 8 a 12: execução -------------------------------------------
    def executar(self, req: C.PortalExecutionRequest) -> C.PortalExecutionResult:
        """O caminho canônico completo."""
        modo = modo_do_gateway()

        resolucao = self.resolver(req)
        if not resolucao.get("ok"):
            return resolucao["resultado"]

        portal_key = resolucao["portal_key"]
        definicao = resolucao["definicao"]
        conta = resolucao["conta"]
        chave = self.chave_de_idempotencia(req, definicao)

        if modo != C.MODO_ON:
            # Sombra: resolveu, registrou, não criou nada. O valor está em
            # saber que a ponte CHEGARIA na mesma journey que o caminho legado.
            logger.info("[portais][%s] resolveria %s -> %s.%s (conta=%s)",
                        modo, req.operation_key, portal_key,
                        definicao.journey_key, conta.account_label or "-")
            return C.PortalExecutionResult(
                business_state=C.NEGOCIO_NADA_A_FAZER,
                operation_key=req.operation_key, portal_key=portal_key,
                idempotency_key=chave,
                motivo=f"gateway em `{modo}`: resolveu e nao executou",
                data={"journey_key": definicao.journey_key,
                      "effect_class": definicao.effect_class,
                      "account_label": conta.account_label,
                      "modo": modo})

        # -- idempotência: o pedido já existe? -----------------------------
        if chave:
            vivo = self.procurar_pedido_vivo(req.company_id, chave)
            if vivo:
                # Conferência do Stripe: mesma chave, corpo diferente = erro.
                registro = C.IdempotencyRecord(
                    idempotency_key=chave,
                    request_fingerprint=str(
                        ((vivo.get("evidence") or {}) if isinstance(
                            vivo.get("evidence"), dict) else {}
                         ).get("gateway_fingerprint") or ""),
                    portal_job_id=str(vivo.get("id")))
                if registro.conflita_com(req):
                    return C.recusa(
                        C.NEGOCIO_NAO_AUTORIZADO,
                        "a mesma chave de idempotencia chegou com um pedido "
                        "DIFERENTE: devolver o resultado antigo entregaria a "
                        "resposta de outro pedido",
                        operation_key=req.operation_key, portal_key=portal_key,
                        pode_repetir=False)
                return self._esperar_e_traduzir(
                    str(vivo.get("id")), req, portal_key, chave,
                    ja_existia=True)

        job_id = self._criar_job(req, portal_key, definicao, conta, chave)
        if not job_id:
            return C.recusa(C.NEGOCIO_FALHOU,
                            "nao consegui enfileirar o trabalho no portal",
                            operation_key=req.operation_key, portal_key=portal_key)

        if req.wait_mode == C.ESPERA_ENFILEIRAR:
            return C.PortalExecutionResult(
                business_state=C.NEGOCIO_PRECISA_HUMANO,
                operation_key=req.operation_key, portal_key=portal_key,
                portal_job_id=job_id, work_run_id=req.work_run_id,
                idempotency_key=chave,
                motivo="enfileirado; o desfecho chega pelo Work Run",
                message="o trabalho foi enfileirado")

        return self._esperar_e_traduzir(job_id, req, portal_key, chave)

    # -- privados ---------------------------------------------------------
    def _criar_job(self, req: C.PortalExecutionRequest, portal_key: str,
                   definicao: Any, conta: Any, chave: Optional[str]) -> Optional[str]:
        """Cria o `portal_job` COM linhagem — Bloco D.

        A linhagem é o que faz o job deixar de ser órfão: dá para perguntar
        "de que Work Run veio este pedido?" e "que tool o gerou?". Hoje isso é
        impossível, e por isso um job que deu errado não tem história.
        """
        linha: Dict[str, Any] = {
            "company_id": req.company_id,
            "portal_key": portal_key,
            "journey": definicao.journey_key,
            "params": dict(req.business_input or {}),
            "status": "queued",
        }
        if conta.account_id:
            linha["account_id"] = conta.account_id
        if chave:
            linha["idempotency_key"] = chave
        if req.session_id:
            linha["session_id"] = req.session_id
        if req.agent_id:
            linha["agent_id"] = req.agent_id

        # A linhagem vai em colunas quando elas existirem, e SEMPRE no
        # evidence — para que a ponte funcione antes e depois da migration.
        # Um recurso que só existe depois de um SQL aplicado à mão é um
        # recurso que não existe no dia em que alguém precisa dele.
        linhagem = {k: v for k, v in {
            "work_run_id": req.work_run_id,
            "work_step_id": req.work_step_id,
            "skill_release_id": req.skill_release_id,
            "tool_release_id": req.tool_release_id,
            "user_id": req.user_id,
            "operation_key": req.operation_key,
        }.items() if v}
        linha["evidence"] = {
            "gateway": {"modo": C.MODO_ON, "linhagem": linhagem,
                        "effect_class": definicao.effect_class},
            "gateway_fingerprint": req.impressao_do_pedido(),
        }

        try:
            r = self.supabase.table("portal_jobs").insert(linha).execute()
            dados = (r.data or [])
            return str(dados[0].get("id")) if dados else None
        except Exception as e:  # noqa: BLE001
            texto = str(e)
            if "23505" in texto or "duplicate key" in texto.lower():
                # Corrida: outro processo inseriu a mesma chave. Não é erro —
                # é a idempotência funcionando. Anexa ao que já existe.
                vivo = self.procurar_pedido_vivo(req.company_id, chave or "")
                if vivo:
                    return str(vivo.get("id"))
            logger.error("[portais] insert de portal_job falhou: %s", type(e).__name__)
            return None

    def _ler_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            r = (self.supabase.table("portal_jobs")
                 .select("id, status, evidence, error, params")
                 .eq("id", job_id).limit(1).execute())
            dados = (r.data or [])
            return dict(dados[0]) if dados else None
        except Exception:  # noqa: BLE001
            return None

    def _esperar_e_traduzir(self, job_id: str, req: C.PortalExecutionRequest,
                            portal_key: str, chave: Optional[str],
                            *, ja_existia: bool = False) -> C.PortalExecutionResult:
        limite = self._agora() + ESPERA_MAXIMA_S
        job: Optional[Dict[str, Any]] = None
        while self._agora() < limite:
            job = self._ler_job(job_id)
            if job and str(job.get("status")) in STATUS_TERMINAIS:
                break
            self._dormir(ESPERA_ENTRE_LEITURAS_S)

        if not job:
            return C.recusa(C.NEGOCIO_FALHOU, "nao consegui ler o trabalho criado",
                            operation_key=req.operation_key, portal_key=portal_key)

        if str(job.get("status")) not in STATUS_TERMINAIS:
            # 🔴 Tempo esgotado NÃO é falha: o trabalho continua rodando lá. Dizer
            # "falhou" aqui faria o chamador tentar de novo sobre um job vivo.
            return C.PortalExecutionResult(
                business_state=C.NEGOCIO_PRECISA_HUMANO,
                operation_key=req.operation_key, portal_key=portal_key,
                portal_job_id=job_id, work_run_id=req.work_run_id,
                idempotency_key=chave, pode_repetir=False,
                motivo="ainda em andamento quando a espera acabou",
                message="o trabalho continua rodando; NAO peca de novo")

        estado = traduzir_estado(job)
        evidence = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
        return C.PortalExecutionResult(
            business_state=estado,
            operation_key=req.operation_key, portal_key=portal_key,
            portal_job_id=job_id, work_run_id=req.work_run_id,
            idempotency_key=chave,
            pode_repetir=(estado not in C.NAO_REPETIR),
            data={k: v for k, v in evidence.items()
                  if k not in ("gateway", "gateway_fingerprint")},
            message=str(job.get("error") or "") if estado == C.NEGOCIO_FALHOU else "",
            motivo=("pedido ja existia; anexei ao que estava em curso"
                    if ja_existia else ""),
            raw={"status": job.get("status")})
