"""SPEC-062 §33 — Prontidão em quatro níveis, e a Decisão de Lançamento.

A pergunta
----------
> *"Podemos ir ao ar?"*

Ela parece uma pergunta só e são quatro, com donos diferentes. Misturá-las é o
que produz aquele "acho que está pronto" que ninguém consegue defender:

    PLATAFORMA  a infraestrutura responde? (banco, storage, fila, índice)
    RELEASE     este commit passou no que tinha de passar?
    CORRETORA   *esta* corretora tem o que precisa para operar?
    COMERCIAL   existe preço aprovado? ← hoje NÃO, e é decisão do Founder

Uma corretora pode estar 100% pronta enquanto a plataforma está degradada. Um
release pode estar verde enquanto o comercial não existe. Responder "sim" sem
separar os quatro é como dizer que o carro está pronto porque tem gasolina.

O que este módulo NÃO faz
-------------------------
Não decide o lançamento. Ele **monta a evidência** e diz o que falta. A decisão
é do Founder e fica registrada em `launch_decisions` — porque daqui a seis
meses "por que fomos ao ar naquele dia?" precisa de resposta consultável.

A regra do "não sei"
--------------------
Item que não pôde ser verificado conta como **NÃO pronto**, nunca como pronto.
Um checklist que dá o benefício da dúvida é um checklist que aprova o que não
olhou.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _item(chave: str, pronto: bool, frase: str, bloqueia: bool = True) -> dict:
    return {"chave": chave, "pronto": bool(pronto), "frase": frase,
            "bloqueia": bloqueia}


class Prontidao:
    def __init__(self, supabase_client: Any = None):
        raw = supabase_client or self._padrao()
        self.db = getattr(raw, "client", raw) if raw else None

    @staticmethod
    def _padrao() -> Any:
        try:
            from ...core.database import get_supabase_client

            return get_supabase_client()
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    def plataforma(self) -> dict:
        """§33.1 — a infraestrutura responde?

        Reusa os mesmos checadores do `/health`. Ter um segundo verificador
        seria um segundo motor (CLAUDE.md §5) e, pior, dois diagnósticos
        diferentes para o mesmo problema.
        """
        itens: list[dict] = []
        try:
            from ...main import _checar_qdrant, _checar_redis, _checar_storage

            for nome, checador, frase_ok, frase_nao in (
                ("storage", _checar_storage, "Storage responde e o bucket existe.",
                 "Storage fora do ar — nenhum Artifact é gerado."),
                ("redis", _checar_redis, "Redis responde.",
                 "Redis fora do ar — fila, lock e cache param."),
                ("qdrant", _checar_qdrant, "Índice responde.",
                 "Índice fora do ar — a busca de conhecimento degrada."),
            ):
                try:
                    r = checador() or {}
                    ok = bool(r.get("conectado"))
                except Exception as exc:  # noqa: BLE001
                    ok, r = False, {"erro": type(exc).__name__}
                itens.append(_item(nome, ok, frase_ok if ok else frase_nao))
        except Exception as exc:  # noqa: BLE001
            itens.append(_item("infra", False,
                               f"Não foi possível verificar a infraestrutura "
                               f"({type(exc).__name__}). Não verificado conta "
                               f"como não pronto."))

        itens.append(_item(
            "banco", bool(self.db),
            "Banco acessível." if self.db else "Banco inacessível."))
        return self._fechar("plataforma", itens)

    # ------------------------------------------------------------------
    def release(self) -> dict:
        """§33.2 — este commit passou no que tinha de passar?"""
        itens: list[dict] = []
        candidato = None
        try:
            from ..evals.runner import commit_atual

            sha = commit_atual()
            if sha and self.db:
                rows = (self.db.table("release_candidates").select("*")
                        .ilike("commit_sha", f"{sha}%").limit(1).execute().data or [])
                candidato = rows[0] if rows else None
            itens.append(_item("commit_conhecido", bool(sha),
                               f"Rodando o commit {sha}." if sha
                               else "Não sei qual commit está rodando."))
        except Exception as exc:  # noqa: BLE001
            itens.append(_item("commit_conhecido", False,
                               f"Não foi possível ler o commit ({type(exc).__name__})."))

        manifesto = (candidato or {}).get("manifesto") or {}
        gate = manifesto.get("gate_de_conduta") or {}
        verde = bool(gate.get("verde"))
        itens.append(_item(
            "gate_de_conduta", verde,
            f"Gate verde: {gate.get('passaram')} de {gate.get('total')}." if verde
            else "Sem manifesto com gate verde para este commit. "
                 "Rode `python backend/scripts/release_manifest.py --gravar`."))

        arvore = (manifesto.get("codigo") or {}).get("arvore_limpa")
        itens.append(_item(
            "arvore_limpa", arvore is True,
            "A árvore estava limpa quando o manifesto foi gerado." if arvore
            else "O que roda pode não ser o que o commit diz — havia alteração "
                 "não commitada.",
            bloqueia=False))
        return self._fechar("release", itens)

    # ------------------------------------------------------------------
    def corretora(self, company_id: str) -> dict:
        """§33.3 — esta corretora tem o que precisa para operar?

        Lê o mesmo estado que a tela `/dashboard/personalizacao/prontidao`
        mostra para o corretor. Duas fontes divergentes para a mesma pergunta é
        como se produz discussão em vez de decisão.
        """
        itens: list[dict] = []
        if not self.db:
            return self._fechar("corretora", [
                _item("banco", False, "Banco inacessível — nada verificado.")])

        def _conta(tabela: str, **filtros) -> int:
            try:
                q = self.db.table(tabela).select("id")
                for k, v in filtros.items():
                    q = q.eq(k, v)
                return len(q.limit(200).execute().data or [])
            except Exception:  # noqa: BLE001
                return -1  # -1 = não verificado, e não verificado não é pronto

        core = _conta("agents", company_id=company_id, agent_role="core")
        atend = _conta("agents", company_id=company_id, agent_role="attendance")
        equipe = _conta("users_v2", company_id=company_id)
        conhecimento = _conta("documents", company_id=company_id)

        canal = -1
        try:
            rows = (self.db.table("integrations")
                    .select("channel_status, purpose, is_active")
                    .eq("company_id", company_id).eq("provider", "evolution-go")
                    .eq("purpose", "observer").eq("is_active", True)
                    .limit(1).execute().data or [])
            from ..whatsapp.channel_state import esta_conectado
            canal = 1 if rows and esta_conectado(rows[0].get("channel_status")) else 0
        except Exception:  # noqa: BLE001
            canal = -1

        itens += [
            _item("agente_core", core > 0,
                  "O chat interno existe." if core > 0
                  else "Sem chat interno — a corretora não tem assistente."),
            _item("agente_atendimento", atend > 0,
                  "O agente de atendimento está provisionado (ligar é decisão "
                  "da corretora)." if atend > 0
                  else "Sem agente de atendimento provisionado."),
            _item("whatsapp", canal == 1,
                  "WhatsApp pareado e conectado." if canal == 1
                  else ("WhatsApp não pareado — sem ele o Observador não tem o "
                        "que observar." if canal == 0
                        else "Não foi possível verificar o WhatsApp.")),
            _item("equipe", equipe > 0,
                  f"{equipe} pessoa(s) com acesso." if equipe > 0
                  else "Ninguém com acesso."),
            _item("conhecimento", conhecimento > 0,
                  f"{conhecimento} documento(s) no conhecimento." if conhecimento > 0
                  else "Sem conhecimento carregado — as respostas ficam genéricas.",
                  bloqueia=False),
        ]
        return self._fechar("corretora", itens)

    # ------------------------------------------------------------------
    def comercial(self) -> dict:
        """§33.4 — existe catálogo comercial aprovado?

        Hoje NÃO, e é decisão do Founder (D22). Este nível existe para que a
        ausência apareça como ausência, e não como esquecimento.
        """
        from ..billing_gate import cobranca_ligada, fronteira_comercial

        fronteira = fronteira_comercial()
        return self._fechar("comercial", [
            _item("catalogo_aprovado", bool(fronteira),
                  f"Lançamento comercial marcado para {fronteira}." if fronteira
                  else "Sem catálogo comercial aprovado (D22). Nada é cobrado, "
                       "e é assim que deve ser até o Founder decidir preço."),
            _item("cobranca_coerente", (not cobranca_ligada()) or bool(fronteira),
                  "Cobrança e fronteira comercial estão coerentes."
                  if (not cobranca_ligada()) or fronteira
                  else "PERIGO: cobrança LIGADA sem fronteira comercial definida."),
        ])

    # ------------------------------------------------------------------
    def completa(self, company_id: Optional[str] = None) -> dict:
        niveis = {
            "plataforma": self.plataforma(),
            "release": self.release(),
            "comercial": self.comercial(),
        }
        if company_id:
            niveis["corretora"] = self.corretora(company_id)

        # Comercial NÃO bloqueia operar — bloqueia VENDER. Uma corretora pode
        # trabalhar plenamente sem catálogo de preço; é exatamente o estado de
        # hoje. Tratar os dois como a mesma coisa faria o painel dizer "não
        # pronto" para um sistema que está funcionando.
        pode_operar = all(n["pronto"] for k, n in niveis.items() if k != "comercial")
        pode_vender = pode_operar and niveis["comercial"]["pronto"]

        pendentes = [f"{k}: {i['frase']}"
                     for k, n in niveis.items()
                     for i in n["itens"] if not i["pronto"] and i["bloqueia"]]

        return {
            "niveis": niveis,
            "pode_operar": pode_operar,
            "pode_vender": pode_vender,
            "pendencias": pendentes,
            "frase": (
                "Tudo pronto: dá para operar e para vender."
                if pode_vender else
                ("Dá para OPERAR. Vender depende do catálogo comercial (D22)."
                 if pode_operar else
                 f"Ainda não dá para operar — {len(pendentes)} pendência(s).")),
            "verificado_em": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    def registrar_decisao(self, *, decisao: str, por: str,
                          motivo: str, company_id: Optional[str] = None) -> Optional[str]:
        """§33.5 — a decisão fica escrita, com a evidência do momento.

        Daqui a seis meses, "por que fomos ao ar naquele dia?" precisa de
        resposta consultável — não de memória.
        """
        if not self.db:
            return None
        if decisao not in ("go", "no_go", "adiado"):
            return None
        try:
            r = self.db.table("launch_decisions").insert({
                "decisao": decisao, "decidido_por": por[:120],
                "motivo": motivo[:1000], "company_id": company_id,
                "evidencia": self.completa(company_id),
            }).execute()
            return (r.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            logger.error("[Prontidao] decisão não registrada: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------
    @staticmethod
    def _fechar(nivel: str, itens: list[dict]) -> dict:
        bloqueadores = [i for i in itens if not i["pronto"] and i["bloqueia"]]
        return {
            "nivel": nivel,
            "pronto": not bloqueadores,
            "itens": itens,
            "faltam": [i["frase"] for i in bloqueadores],
        }
