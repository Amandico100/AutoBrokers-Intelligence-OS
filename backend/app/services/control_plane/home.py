"""Home executiva do Portal Admin. SPEC-061 §12.

O princípio, na frase da SPEC
-----------------------------
*"A Home não deve ser uma grade de métricas sem hierarquia."*

A Home de hoje mostra `MRR R$ 0,00`, `Total de Empresas 5`, `Total de Usuários
9`, `Aprovações Pendentes 0` — quatro números do mesmo tamanho, nenhum deles
dizendo o que fazer. O Founder resumiu: *"não consigo entender de fato tudo"*.

O problema não é a falta de números. É que **todos têm o mesmo peso visual**,
então nenhum tem peso nenhum. Quatro caixas iguais obrigam a pessoa a ler as
quatro e decidir sozinha qual importa — que é exatamente o trabalho que a tela
deveria ter feito.

A ordem da §12.1 resolve isso, e ela é hierárquica de propósito:

    1. estado geral        → uma frase. O que está acontecendo?
    2. precisa de decisão  → o que só anda se alguém agir
    3. corretoras em risco → onde dói
    4. operação            → o que está rodando
    5. números             → contexto, subordinado ao resto

§12.2 tem uma regra que vale mais que todo o resto:

> "Não mostrar 'Tudo saudável' quando fontes estiverem stale ou indisponíveis."

Uma Home que diz "tudo bem" porque não conseguiu ler é pior que uma Home
quebrada: a quebrada manda procurar, a mentirosa manda dormir.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

DIAS_SEM_ATIVIDADE_PREOCUPA = 14


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class HomeExecutiva:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def montar(self, *, permissions: set[str], dias: int = 7) -> dict:
        falhas: list[str] = []
        decisoes = self._precisa_de_decisao(permissions, falhas)
        risco = self._corretoras_em_risco(permissions, falhas)
        operacao = self._operacao(permissions, falhas)
        numeros = self._numeros(permissions, dias, falhas)

        return {
            "ok": True,
            # A frase vem PRIMEIRO e é montada depois de tudo, porque ela
            # precisa saber o que falhou para não mentir.
            "estado_geral": self._frase(decisoes, risco, operacao, falhas),
            "fontes_indisponiveis": falhas,
            "precisa_de_decisao": decisoes,
            "corretoras_em_risco": risco,
            "operacao": operacao,
            "numeros": numeros,
        }

    # ------------------------------------------------------------------

    def _frase(self, decisoes: list[dict], risco: list[dict],
               operacao: dict, falhas: list[str]) -> dict:
        """Uma frase que diz o que está acontecendo. §12.2.

        Nunca "tudo saudável" com fonte indisponível: essa é a única regra que
        a §12.2 escreve com todas as letras, e é a que separa uma Home útil de
        uma Home que manda dormir.
        """
        if falhas:
            return {
                "tom": "incerto",
                "texto": (f"Não consegui ler {len(falhas)} fonte(s): "
                          f"{', '.join(falhas[:3])}. O que aparece abaixo está "
                          "incompleto — não é um retrato de tudo."),
            }

        criticas = [d for d in decisoes if d.get("risco") == "alto"]
        if criticas:
            return {"tom": "atencao",
                    "texto": (f"{len(criticas)} decisão(ões) de alto risco "
                              "esperando alguém. É por aí que se começa.")}
        if decisoes:
            return {"tom": "atencao",
                    "texto": (f"{len(decisoes)} item(ns) só andam se alguém "
                              "decidir. Nada urgente.")}
        if risco:
            return {"tom": "atencao",
                    "texto": (f"Nada esperando decisão, mas {len(risco)} "
                              "corretora(s) merecem um olhar.")}
        if operacao.get("travados"):
            return {"tom": "atencao",
                    "texto": (f"{operacao['travados']} trabalho(s) parado(s) "
                              "sem sinal de vida.")}
        return {"tom": "estavel",
                "texto": "Operação estável. Nada esperando você agora."}

    def _precisa_de_decisao(self, permissions: set[str],
                            falhas: list[str]) -> list[dict]:
        """§12.3 — o que só anda se um humano agir.

        Cada item traz o que a §12.3 exige: o que houve, por que importa, quem
        é afetado, há quanto tempo e a ação recomendada. Um cartão que diz
        apenas "3 aprovações pendentes" devolve o trabalho de investigar para
        quem abriu a tela.
        """
        itens: list[dict] = []

        if "approvals.read" in permissions:
            linhas = self._ler("approval_requests",
                               "id, company_id, action_type, risk_level, created_at",
                               {"status": "pending"}, falhas, "aprovações")
            for l in linhas[:10]:
                alto = str(l.get("risk_level")) in ("high", "critical")
                itens.append({
                    "tipo": "aprovacao",
                    "o_que": f"Aprovação de {l.get('action_type') or 'ação'}",
                    "por_que": ("A ação não acontece enquanto ninguém decidir."
                                if not alto else
                                "Ação de alto risco parada esperando decisão."),
                    "company_id": l.get("company_id"),
                    "desde": l.get("created_at"),
                    "acao": "Aprovar ou recusar",
                    "href": "/admin/inbox",
                    "risco": "alto" if alto else "medio",
                })

        if "security.read" in permissions:
            linhas = self._ler("platform_incidents",
                               "id, incident_key, severity, status, summary, detected_at",
                               None, falhas, "incidentes")
            for l in linhas:
                if str(l.get("status")) not in ("open", "acknowledged", "mitigated"):
                    continue
                itens.append({
                    "tipo": "incidente",
                    "o_que": f"Incidente {l.get('severity')}: {l.get('summary')}",
                    "por_que": "Afeta a plataforma ou várias corretoras.",
                    "company_id": None,
                    "desde": l.get("detected_at"),
                    "acao": "Acompanhar e resolver",
                    "href": "/admin/governanca",
                    "risco": "alto" if str(l.get("severity")) == "sev1" else "medio",
                })

        if "knowledge.curate" in permissions:
            linhas = self._ler("knowledge_candidates", "id, created_at",
                               {"status": "pending"}, falhas, "conhecimento")
            if linhas:
                itens.append({
                    "tipo": "conhecimento",
                    "o_que": f"{len(linhas)} candidato(s) a conhecimento",
                    "por_que": ("Enquanto não forem revisados, o que eles sabem "
                                "não chega a corretora nenhuma."),
                    "company_id": None,
                    "desde": min((str(l.get("created_at") or "") for l in linhas),
                                 default=None) or None,
                    "acao": "Revisar e publicar ou descartar",
                    "href": "/admin/knowledge-base",
                    "risco": "baixo",
                })

        ordem = {"alto": 0, "medio": 1, "baixo": 2}
        itens.sort(key=lambda i: (ordem.get(i["risco"], 3), str(i.get("desde") or "")))
        return itens

    def _corretoras_em_risco(self, permissions: set[str],
                             falhas: list[str]) -> list[dict]:
        """§12.1 item 3 — onde dói.

        Duas perguntas: quem está com trabalho falhando, e quem **parou de
        usar**. A segunda quase nunca aparece em painel, e é a que antecede o
        cancelamento: corretora provisionada e silenciosa há duas semanas não
        está "estável", está sem uso.
        """
        if "companies.read" not in permissions:
            return []

        empresas = self._ler("companies", "id, company_name", None, falhas,
                             "corretoras")
        if not empresas:
            return []

        desde = (_agora() - timedelta(days=30)).isoformat()
        runs = self._ler("work_runs", "company_id, status, created_at", None,
                         falhas, "trabalhos", limite=1000)

        por_empresa: dict[str, dict] = {}
        for r in runs:
            cid = str(r.get("company_id") or "")
            if not cid:
                continue
            d = por_empresa.setdefault(cid, {"falhas": 0, "ultimo": ""})
            if str(r.get("status")) == "failed":
                d["falhas"] += 1
            criado = str(r.get("created_at") or "")
            if criado > d["ultimo"]:
                d["ultimo"] = criado

        saida = []
        for e in empresas:
            cid = str(e.get("id"))
            d = por_empresa.get(cid, {"falhas": 0, "ultimo": ""})
            motivos = []
            if d["falhas"] >= 3:
                motivos.append(f"{d['falhas']} trabalhos falharam")
            dias_parada = None
            if d["ultimo"]:
                try:
                    quando = datetime.fromisoformat(d["ultimo"].replace("Z", "+00:00"))
                    dias_parada = (_agora() - quando).days
                    if dias_parada >= DIAS_SEM_ATIVIDADE_PREOCUPA:
                        motivos.append(f"sem atividade há {dias_parada} dias")
                except Exception:  # noqa: BLE001
                    pass
            else:
                motivos.append("nunca teve atividade registrada")

            if motivos:
                saida.append({
                    "company_id": cid,
                    "nome": e.get("company_name"),
                    "motivos": motivos,
                    "dias_sem_atividade": dias_parada,
                    "href": "/admin/corretoras",
                })
        return saida

    def _operacao(self, permissions: set[str], falhas: list[str]) -> dict:
        if "work_runs.read" not in permissions:
            return {}
        from .read_models import CentralDeTrabalhos

        try:
            return CentralDeTrabalhos(self.raw).resumo(dias=7)
        except Exception as exc:  # noqa: BLE001
            falhas.append("trabalhos")
            logger.warning("[Home] operação: %s", type(exc).__name__)
            return {}

    def _numeros(self, permissions: set[str], dias: int,
                 falhas: list[str]) -> list[dict]:
        """§12.4 — contexto, **subordinado às decisões**.

        Por isso vêm por último na resposta e sem destaque: um número que não
        muda o que você faz hoje não merece o topo da tela.
        """
        saida: list[dict] = []
        if "companies.read" in permissions:
            empresas = self._ler("companies", "id", None, falhas, "corretoras")
            saida.append({"rotulo": "Corretoras", "valor": len(empresas)})
        if "work_runs.read" in permissions:
            desde = (_agora() - timedelta(days=dias)).isoformat()
            runs = [r for r in self._ler("work_runs", "id, created_at", None,
                                         falhas, "trabalhos", limite=1000)
                    if str(r.get("created_at") or "") >= desde]
            saida.append({"rotulo": f"Trabalhos ({dias}d)", "valor": len(runs)})
        return saida

    # ------------------------------------------------------------------

    def _ler(self, tabela: str, campos: str, filtros: Optional[dict],
             falhas: list[str], nome_humano: str,
             limite: int = 200) -> list[dict]:
        """Leitura que REGISTRA a falha em vez de escondê-la.

        É a diferença desta classe para a Inbox: lá, uma fonte fora do ar
        silencia um bloco. Aqui, ela muda a FRASE do topo — porque a Home
        afirma o estado geral, e afirmar sobre o que não foi lido é o defeito
        que a §12.2 proíbe.
        """
        try:
            q = self.db.table(tabela).select(campos).limit(limite)
            for c, v in (filtros or {}).items():
                q = q.eq(c, v)
            return q.execute().data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Home] '%s' indisponível: %s", tabela,
                           type(exc).__name__)
            if nome_humano not in falhas:
                falhas.append(nome_humano)
            return []
