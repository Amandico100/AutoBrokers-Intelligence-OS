"""SPEC-062 §26 — Unit Economics. O que cada corretora custa, de verdade.

A pergunta que este arquivo responde
------------------------------------
> *"Quanto me custa manter esta corretora no ar por mês?"*

Sem essa resposta, precificar é adivinhar. O Founder pretende cobrar com margem
sobre consumo, e hoje não existe nenhum lugar que diga quanto uma corretora
consome — nem por corretora, nem por modelo, nem por tipo de trabalho.

Duas fontes, e nenhuma delas descartada
---------------------------------------
    usage_events      ledger da SPEC-062 §21.1: atribui o gasto a skill, tool,
                      work run e artifact. Ligado ao gargalo de LLM agora.
    token_usage_logs  ledger legado: 1.239 linhas de um ano de trabalho. Sabe o
                      modelo e o custo, não sabe de qual trabalho veio.

O legado não é lixo — é o único histórico que existe. Descartá-lo seria jogar
fora a única base para comparar antes e depois. Então as duas são lidas, e a
origem de cada número aparece na resposta. Quem lê sabe de onde veio.

O que este módulo NÃO faz
-------------------------
Não calcula margem, não aplica multiplicador, não converte para preço ao
cliente. `provider_cost` e `customer_price` são coisas diferentes (§23.1), e o
segundo não existe enquanto o Founder não aprovar o catálogo comercial (§4 lei
17). Misturar os dois aqui é exatamente como cobrança retroativa nasce.

Custo é fato. Preço é decisão.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Teto de leitura. Um mês de tráfego real de dezenas de corretoras não cabe
# numa resposta de API, e truncar em silêncio faria o número parecer menor do
# que é — o pior defeito possível num relatório de custo. Quando trunca, diz.
TETO = 5000


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _brl(usd: float, cotacao: float) -> float:
    return round(float(usd or 0) * float(cotacao or 0), 4)


class EconomiaPorCorretora:
    """Custo real de provedor, por corretora, por modelo e por tipo de trabalho."""

    def __init__(self, supabase_client: Any, *, cotacao_dolar: float = 6.0):
        self.db = getattr(supabase_client, "client", supabase_client)
        self.cotacao = float(cotacao_dolar or 6.0)

    # ------------------------------------------------------------------
    def montar(self, *, dias: int = 30,
               company_id: Optional[str] = None) -> dict:
        desde = (_agora() - timedelta(days=max(1, int(dias)))).isoformat()

        eventos, truncou_eventos = self._ler_eventos(desde, company_id)
        legado, truncou_legado = self._ler_legado(desde, company_id)
        nomes = self._nomes_das_empresas()

        por_empresa: dict[str, dict] = defaultdict(
            lambda: {"custo_usd": 0.0, "tokens": 0, "eventos": 0,
                     "por_modelo": defaultdict(float),
                     "por_fonte": defaultdict(float)})

        for ev in eventos:
            cid = str(ev.get("company_id") or "")
            if not cid:
                continue
            alvo = por_empresa[cid]
            custo = float(ev.get("provider_cost_usd") or 0)
            alvo["custo_usd"] += custo
            alvo["tokens"] += int(ev.get("input_tokens") or 0) + int(ev.get("output_tokens") or 0)
            alvo["eventos"] += 1
            alvo["por_modelo"][ev.get("model") or "(sem modelo)"] += custo
            # `skill_slug` antes de `source`: saber que o gasto veio da skill
            # "renovacao" vale mais do que saber que veio do "chat".
            alvo["por_fonte"][ev.get("skill_slug") or ev.get("tool_name")
                              or ev.get("source") or "(sem origem)"] += custo

        for log in legado:
            cid = str(log.get("company_id") or "")
            if not cid:
                continue
            alvo = por_empresa[cid]
            custo = float(log.get("total_cost_usd") or 0)
            alvo["custo_usd"] += custo
            alvo["tokens"] += int(log.get("input_tokens") or 0) + int(log.get("output_tokens") or 0)
            alvo["eventos"] += 1
            alvo["por_modelo"][log.get("model_name") or "(sem modelo)"] += custo
            alvo["por_fonte"][log.get("service_type") or "(sem origem)"] += custo

        linhas = []
        for cid, dados in por_empresa.items():
            linhas.append({
                "company_id": cid,
                "corretora": nomes.get(cid, "(corretora removida)"),
                "custo_provedor_usd": round(dados["custo_usd"], 6),
                "custo_provedor_brl": _brl(dados["custo_usd"], self.cotacao),
                "tokens": dados["tokens"],
                "eventos": dados["eventos"],
                "por_modelo": self._maiores(dados["por_modelo"]),
                "por_fonte": self._maiores(dados["por_fonte"]),
            })
        linhas.sort(key=lambda x: x["custo_provedor_usd"], reverse=True)

        total_usd = sum(l["custo_provedor_usd"] for l in linhas)

        return {
            "periodo_dias": dias,
            "cotacao_dolar": self.cotacao,
            "corretoras": linhas,
            "total": {
                "custo_provedor_usd": round(total_usd, 6),
                "custo_provedor_brl": _brl(total_usd, self.cotacao),
                "corretoras_com_consumo": len(linhas),
            },
            "procedencia": {
                "usage_events": len(eventos),
                "token_usage_logs": len(legado),
                # Quando o ledger novo ainda está vazio, o número vem todo do
                # legado — e o legado não sabe de qual trabalho o gasto veio.
                # Dizer isso evita que alguém leia "por_fonte" como se fosse
                # atribuição fina quando não é.
                "atribuicao_fina_disponivel": len(eventos) > 0,
            },
            "frase": self._frase(linhas, total_usd, len(eventos)),
            "truncado": bool(truncou_eventos or truncou_legado),
            "aviso_de_truncagem": (
                f"A leitura parou em {TETO} registros por fonte. O custo real do "
                "período é MAIOR que o mostrado." if (truncou_eventos or truncou_legado)
                else None),
            # §23.1 — a separação tem que estar escrita na resposta, não só na
            # cabeça de quem escreveu o código.
            "aviso": ("Custo de PROVEDOR. Não é preço ao cliente, não tem "
                      "margem aplicada e não é cobrança."),
        }

    # ------------------------------------------------------------------
    def _frase(self, linhas: list[dict], total_usd: float, eventos: int) -> str:
        if not linhas:
            return "Nenhum consumo registrado no período."
        maior = linhas[0]
        parte = (f"; a maior é {maior['corretora']} com "
                 f"R$ {maior['custo_provedor_brl']:.2f}") if len(linhas) > 1 else ""
        origem = "" if eventos else (" O número vem do ledger legado: ainda não "
                                     "há atribuição por skill ou ferramenta.")
        return (f"{len(linhas)} corretora(s) consumiram R$ "
                f"{_brl(total_usd, self.cotacao):.2f} em custo de provedor{parte}."
                f"{origem}")

    @staticmethod
    def _maiores(contador: dict, quantos: int = 5) -> list[dict]:
        ordenado = sorted(contador.items(), key=lambda x: x[1], reverse=True)
        return [{"nome": n, "custo_usd": round(v, 6)} for n, v in ordenado[:quantos]]

    def _nomes_das_empresas(self) -> dict[str, str]:
        try:
            r = self.db.table("companies").select("id, company_name").execute()
            return {str(x["id"]): x.get("company_name") or "(sem nome)"
                    for x in (r.data or [])}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[UnitEconomics] nomes: %s", type(exc).__name__)
            return {}

    def _ler_eventos(self, desde: str,
                     company_id: Optional[str]) -> tuple[list[dict], bool]:
        try:
            q = (self.db.table("usage_events")
                 .select("company_id, provider_cost_usd, input_tokens, "
                         "output_tokens, model, source, skill_slug, tool_name")
                 .gte("occurred_at", desde).limit(TETO))
            if company_id:
                q = q.eq("company_id", str(company_id))
            linhas = (q.execute().data) or []
            return linhas, len(linhas) >= TETO
        except Exception as exc:  # noqa: BLE001
            # Uma fonte fora do ar não pode zerar o relatório inteiro — o
            # resultado sai com a outra, e `procedencia` mostra o buraco.
            logger.warning("[UnitEconomics] usage_events: %s", type(exc).__name__)
            return [], False

    def _ler_legado(self, desde: str,
                    company_id: Optional[str]) -> tuple[list[dict], bool]:
        try:
            q = (self.db.table("token_usage_logs")
                 .select("company_id, total_cost_usd, input_tokens, "
                         "output_tokens, model_name, service_type")
                 .gte("created_at", desde).limit(TETO))
            if company_id:
                q = q.eq("company_id", str(company_id))
            linhas = (q.execute().data) or []
            return linhas, len(linhas) >= TETO
        except Exception as exc:  # noqa: BLE001
            logger.warning("[UnitEconomics] token_usage_logs: %s", type(exc).__name__)
            return [], False
