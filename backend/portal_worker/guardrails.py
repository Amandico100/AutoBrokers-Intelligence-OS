# -*- coding: utf-8 -*-
"""Classe de efeito, guarda de ação e recuperação transacional — SPEC-073 Bloco B.

O problema que este módulo existe para resolver
===============================================
📊 Medido em 16/08/2026, lendo `worker.py:83-101`:

    stale_running_patch() seleciona `id, started_at, created_at, attempts`
    e NUNCA lê `evidence`.

Um job que morreu **depois** de o portal criar o atendimento — com o protocolo
já emitido e gravado na evidência — voltava para `queued` e recomeçava do passo
1. O portal de vidros diz, em texto: *"se o item possuir lateralidade será
necessário abrir uma nova solicitação"*. Recomeçar não conserta: **cria um
segundo pedido na seguradora**, e o segurado descobre quando dois vidraceiros
aparecem.

O mesmo defeito existia no botão de retentar do dashboard
(`lib/portal/hitl.ts:58`), que só conferia `status == 'needs_human'`.

A distinção que desfaz o problema
=================================
Nem toda ação merece o mesmo medo:

    READ_ONLY ............. login · navegar · filtrar · listar · baixar PDF
                            exportar relatório
    REVERSIBLE_UI ......... preencher campo ainda não enviado · abrir dropdown
                            selecionar opção antes de confirmar
    MATERIAL_SIDE_EFFECT .. criar atendimento · agendar · cancelar
                            alterar pagamento · enviar à seguradora

🔴 **Semântica vence verbo HTTP.** Exportar relatório é POST e é `READ_ONLY`.
Quem classifica é a capacidade, não o método.

E a regra que fecha a porta
===========================
Se um efeito material talvez tenha acontecido, **retry cego é proibido**. Não
"provavelmente deu errado, tenta de novo": `needs_human` com dossiê, e
reconciliação depois.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

# --------------------------------------------------------------------------
# Classes de efeito
# --------------------------------------------------------------------------
READ_ONLY = "read_only"
REVERSIBLE_UI = "reversible_ui"
MATERIAL_SIDE_EFFECT = "material_side_effect"

CLASSES_VALIDAS: Tuple[str, ...] = (READ_ONLY, REVERSIBLE_UI, MATERIAL_SIDE_EFFECT)

# Ordem de severidade. Serve ao caso "a Tool diz READ e a Journey diz MATERIAL":
# vence sempre a proteção MAIS FORTE, nunca a mais permissiva.
_SEVERIDADE: Dict[str, int] = {READ_ONLY: 0, REVERSIBLE_UI: 1, MATERIAL_SIDE_EFFECT: 2}

# --------------------------------------------------------------------------
# Fases do efeito material. A ordem é a da vida real, e cada uma responde a uma
# pergunta diferente sobre o que o mundo lá fora já sabe.
# --------------------------------------------------------------------------
FASE_ARMED = "armed"          # vou clicar. Nada aconteceu ainda.
FASE_SUBMITTED = "submitted"  # cliquei. Não sei a resposta.
FASE_CONFIRMED = "confirmed"  # aconteceu, e eu tenho a prova (protocolo).
FASE_UNKNOWN = "unknown"      # saiu da minha mão e a resposta se perdeu.

FASES_INCERTAS: Tuple[str, ...] = (FASE_ARMED, FASE_SUBMITTED, FASE_UNKNOWN)

CHAVE_EFEITO = "critical_effect"


class AcaoBloqueada(RuntimeError):
    """O guard recusou. Carrega o motivo em `classe`, para virar evidência."""

    def __init__(self, mensagem: str, *, classe: str = "action_blocked") -> None:
        super().__init__(mensagem)
        self.classe = classe


def normalizar_classe(valor: Any) -> str:
    """Texto solto vira classe conhecida. Desconhecido cai no mais seguro.

    🔴 O default é `MATERIAL_SIDE_EFFECT` de propósito. Uma classe escrita
    errado não pode virar permissão — se o autor da journey digitou
    `"read-only"` com hífen, o pior desfecho aceitável é o guard pedir liberação
    explícita, nunca deixar passar um clique que cria atendimento.
    """
    v = str(valor or "").strip().lower().replace("-", "_")
    return v if v in CLASSES_VALIDAS else MATERIAL_SIDE_EFFECT


def classe_mais_forte(a: Any, b: Any) -> str:
    """Divergência entre duas fontes resolve para a proteção maior (SPEC-075 §9.2)."""
    ca, cb = normalizar_classe(a), normalizar_classe(b)
    return ca if _SEVERIDADE[ca] >= _SEVERIDADE[cb] else cb


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(*partes: Any) -> str:
    """Identidade semântica do efeito, sem PII bruta — SPEC-073 B3.

    Serve para responder *"o efeito que eu ia causar é o mesmo que já causei?"*
    sem gravar placa, CPF ou apólice na evidência. Hash, não conteúdo.
    """
    crua = "|".join(str(p or "").strip().lower() for p in partes)
    return hashlib.sha256(crua.encode("utf-8", "ignore")).hexdigest()[:16]


# --------------------------------------------------------------------------
# Leitura da evidência — funções puras, usadas pelo worker, pelos testes e
# (espelhadas) pelo dashboard.
# --------------------------------------------------------------------------
def efeito_critico(evidence: Any) -> Optional[Dict[str, Any]]:
    """O bloco `critical_effect` do job, se existir."""
    if not isinstance(evidence, dict):
        return None
    ef = evidence.get(CHAVE_EFEITO)
    return ef if isinstance(ef, dict) and ef else None


def fase_do_efeito(evidence: Any) -> str:
    """`""` quando não há efeito material registrado."""
    ef = efeito_critico(evidence)
    if not ef:
        return ""
    return str(ef.get("phase") or "").strip().lower()


def tem_prova_de_efeito(evidence: Any) -> bool:
    """Existe prova autoritativa de que o pedido nasceu?

    🔴 O protocolo é prova superior à fase. A journey de vidros grava
    `evidence["protocolo"]` logo após cada clique, justamente porque essa é a
    janela mais cara do fluxo — e um job pode terminar `failed` **com** o
    protocolo dentro. Quem só olha `status` conclui o contrário do que houve.
    """
    if not isinstance(evidence, dict):
        return False
    if str(evidence.get("protocolo") or "").strip():
        return True
    ef = efeito_critico(evidence)
    if ef:
        if str(ef.get("phase") or "").lower() == FASE_CONFIRMED:
            return True
        if str(ef.get("receipt") or "").strip():
            return True
    return False


def pode_repetir_com_seguranca(evidence: Any) -> bool:
    """`True` só quando é possível PROVAR que nada material aconteceu.

    Ausência de informação **não** é prova de ausência de efeito: sem
    `critical_effect` e sem protocolo, a operação nunca armou um efeito, e aí
    sim repetir é seguro. Com fase incerta, a resposta é não.
    """
    if tem_prova_de_efeito(evidence):
        return False
    fase = fase_do_efeito(evidence)
    if not fase:
        return True
    return fase not in FASES_INCERTAS


def motivo_de_bloqueio(evidence: Any) -> str:
    """A frase que vai para `error`/`human_reason`. Precisa ensinar o que fazer."""
    if tem_prova_de_efeito(evidence):
        return ("efeito material CONFIRMADO (protocolo/recibo registrado): "
                "reexecutar criaria uma segunda operacao no portal. "
                "Continue pelo atendimento existente.")
    fase = fase_do_efeito(evidence)
    if fase in FASES_INCERTAS:
        return (f"efeito material incerto (fase={fase}): a operacao pode ter "
                "acontecido no portal. Reconcilie/consulte antes de qualquer "
                "nova tentativa — NAO reexecute.")
    return ""


# --------------------------------------------------------------------------
# Recuperação de job órfão — a substituta transacional de stale_running_patch
# --------------------------------------------------------------------------
def decidir_recuperacao(job: Dict[str, Any],
                        *,
                        idade_segundos: float,
                        limite_segundos: float,
                        max_tentativas: int = 2) -> Optional[Dict[str, Any]]:
    """O patch de recuperação de um job `running` órfão — ou `None` para deixar em paz.

    🔴 Esta função é a correção do defeito medido: a versão anterior decidia
    olhando só idade e tentativas. Agora a **evidência manda**.

        sem efeito material .......... comportamento antigo, preservado
                                       (1ª vez volta para a fila; reincidente falha)
        efeito confirmado ............ NUNCA volta para a fila
        efeito armed/submitted/unknown NUNCA volta para a fila

    O controle que prova que ela não virou paranoia: um job read-only órfão
    continua sendo recuperado exatamente como antes.
    """
    if idade_segundos < limite_segundos:
        return None

    evidence = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
    tentativas = int(job.get("attempts") or 0)

    if not pode_repetir_com_seguranca(evidence):
        return {
            "status": "needs_human",
            "error": motivo_de_bloqueio(evidence),
            "finished_at": _agora(),
            "evidence": {
                **evidence,
                "recovery": {
                    "decision": "nao_reexecutar",
                    "reason": "material_effect_uncertain_or_confirmed",
                    "phase": fase_do_efeito(evidence) or "protocolo_presente",
                    "at": _agora(),
                },
            },
        }

    if tentativas < max_tentativas:
        return {"status": "queued",
                "error": "requeue: worker reiniciou durante a execucao anterior"}

    return {
        "status": "failed",
        "error": (f"job orfao apos {tentativas} tentativa(s): worker interrompido "
                  "durante a execucao"),
        "finished_at": _agora(),
    }


def pode_retentar_pelo_dashboard(job: Dict[str, Any], company_id: str) -> Tuple[bool, str]:
    """A mesma regra do recovery, para o botão de retentar do HITL.

    📊 O botão conferia apenas `status == 'needs_human' && company_id ==`. E o
    caminho adaptativo produz `needs_human` **carregando protocolo** — é para
    isso que `aviso_de_pedido_aberto()` existe. Ou seja: dava para reabrir pelo
    dashboard um pedido que já tinha nascido.

    Devolve `(pode, motivo)`. O motivo vai para a tela — recusar sem explicar
    faz o operador tentar de novo por outro caminho.
    """
    if not isinstance(job, dict):
        return False, "job inexistente"
    if str(job.get("company_id") or "") != str(company_id or ""):
        return False, "job de outra corretora"
    if str(job.get("status") or "") != "needs_human":
        return False, "somente job em needs_human pode ser retentado"
    evidence = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
    if not pode_repetir_com_seguranca(evidence):
        return False, motivo_de_bloqueio(evidence)
    return True, ""


# --------------------------------------------------------------------------
# O guarda
# --------------------------------------------------------------------------
@dataclass
class PortalActionGuard:
    """Decide se uma ação pode acontecer. Fail-closed por construção.

    O guard NÃO sabe o que é um atendimento de vidro nem uma parcela vencida —
    quem sabe é a journey. Ele sabe três coisas, e são as três que importam:

        1. discovery observa, não age;
        2. efeito material exige liberação EXPLÍCITA de quem tem autoridade;
        3. modelo nenhum eleva a própria permissão.
    """

    job_id: str = ""
    company_id: str = ""
    portal_key: str = ""
    journey: str = ""
    discovery_mode: bool = False
    # Liberação vinda do caminho governado (`params["confirm"]`, gate do agente,
    # approval). Nasce False: quem não foi liberado não age.
    material_liberado: bool = False
    # 🔴 O nome do ÚNICO botão/ação material que esta journey espera executar.
    # Liberar "efeito material" em geral não basta: no passo 7 do portal de
    # vidros convivem "Confirmar", "Agendar a domicílio" e "Cancelar
    # atendimento", e um modelo com permissão genérica pode escolher o errado
    # com a melhor das intenções. Quem sabe qual é o certo é a journey — então é
    # ela que nomeia, e qualquer outro botão material é recusado.
    acao_material_esperada: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    _checkpoint: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    bloqueios: list = field(default_factory=list)

    # -- decisão pura, sem I/O: é ela que os testes e as mutações atacam ----
    def avaliar(self, action_class: Any, *, origem: str = "journey") -> Tuple[bool, str]:
        """`(permitido, motivo)`. Nunca levanta — quem levanta é `before()`."""
        classe = normalizar_classe(action_class)

        if classe in (READ_ONLY, REVERSIBLE_UI):
            # Discovery pode ler e pode preencher; o que ele não pode é enviar.
            return True, ""

        if self.discovery_mode:
            return False, ("discovery_mode: efeito material bloqueado — "
                           "discovery observa, mede e compara; nao age")

        if origem in ("vision", "model", "llm"):
            # R7 na sua forma mais dura: visão INTERPRETA, nunca comete.
            # Se o que ela viu realmente pede confirmação, quem confirma é a
            # journey no passo seguinte — não a imagem.
            return False, ("origem=%s nao executa efeito material: visao propoe, "
                           "runtime/journey autoriza" % origem)

        if not self.material_liberado:
            return False, ("efeito material sem liberacao explicita "
                           "(confirm/approval ausente)")

        return True, ""

    def acao_material_permitida(self, rotulo: Any) -> Tuple[bool, str]:
        """Este botão material específico é o que a journey declarou esperar?

        `material_liberado=True` responde *"pode haver um efeito material aqui"*.
        Esta função responde *"pode ser ESTE"* — e as duas perguntas são
        diferentes. A segunda é a que impede o clique certo na hora errada.
        """
        esperada = str(self.acao_material_esperada or "").strip().lower()
        if not esperada:
            return False, ("a journey nao declarou qual acao material espera; "
                           "clique material recusado por construcao")
        alvo = str(rotulo or "").strip().lower()
        if esperada in alvo or alvo in esperada:
            return True, ""
        return False, (f"acao material {rotulo!r} diferente da esperada pela "
                       f"journey ({self.acao_material_esperada!r})")

    async def before(self,
                     *,
                     action: str,
                     action_class: Any,
                     details: Optional[Dict[str, Any]] = None,
                     origem: str = "journey") -> None:
        """Chamada obrigatória antes de qualquer ação classificada.

        Para efeito material permitido, ARMA o checkpoint **antes** de a ação
        acontecer. Essa ordem é o ponto inteiro do bloco B: se o processo morrer
        no clique, o banco já sabe que havia um clique em curso.
        """
        permitido, motivo = self.avaliar(action_class, origem=origem)
        classe = normalizar_classe(action_class)

        if not permitido:
            self.bloqueios.append({"action": action, "class": classe,
                                   "origem": origem, "motivo": motivo,
                                   "at": _agora()})
            raise AcaoBloqueada(f"{action}: {motivo}", classe="material_blocked")

        if classe == MATERIAL_SIDE_EFFECT:
            await self.armar(action=action, details=details or {})

    async def armar(self, *, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """`phase=armed` no banco, antes do efeito."""
        det = details or {}
        bloco = {
            "name": action,
            "phase": FASE_ARMED,
            "armed_at": _agora(),
            "fingerprint": fingerprint(self.company_id, self.portal_key,
                                       self.journey, action,
                                       det.get("idempotency_key") or ""),
            "resume_policy": "reconcile_before_retry",
        }
        await self._gravar(bloco)

    async def submetido(self, *, receipt: str = "") -> None:
        """`phase=submitted` — saiu da minha mão, ainda não sei o desfecho."""
        await self._avancar(FASE_SUBMITTED, receipt=receipt)

    async def confirmado(self, *, receipt: str = "") -> None:
        """`phase=confirmed` — existe prova autoritativa (protocolo/recibo)."""
        await self._avancar(FASE_CONFIRMED, receipt=receipt)

    async def incerto(self, *, motivo: str = "") -> None:
        """`phase=unknown` — a chamada saiu e a resposta se perdeu.

        É o estado mais importante do módulo, porque é o único em que a
        tentação de "tentar de novo" é forte e errada.
        """
        await self._avancar(FASE_UNKNOWN, motivo=motivo)

    async def _avancar(self, fase: str, *, receipt: str = "", motivo: str = "") -> None:
        atual = efeito_critico(self.evidence) or {}
        if not atual:
            # Avançar fase sem ter armado é sinal de journey mal escrita; ainda
            # assim registramos, porque perder o rastro é pior que registrar tarde.
            atual = {"name": "desconhecido", "phase": FASE_ARMED,
                     "armed_at": _agora(),
                     "resume_policy": "reconcile_before_retry",
                     "armed_late": True}
        bloco = {**atual, "phase": fase, f"{fase}_at": _agora()}
        if receipt:
            bloco["receipt"] = str(receipt)
        if motivo:
            bloco["reason"] = str(motivo)[:300]
        await self._gravar(bloco)

    async def _gravar(self, bloco: Dict[str, Any]) -> None:
        self.evidence[CHAVE_EFEITO] = bloco
        if self._checkpoint is not None:
            await self._checkpoint({CHAVE_EFEITO: bloco})
