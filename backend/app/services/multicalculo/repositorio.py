# -*- coding: utf-8 -*-
"""O acesso ao banco da porta do multicálculo — SPEC-129-B U2 (o contrato é o da migration 20261005_01).

🔴 TODA leitura de pedido, cálculo, oferta e evento leva o filtro do SOLICITANTE (`company_id` do pedido ·
`solicitante_company_id` do resto) AQUI, no repositório — o backend usa service role e a RLS sem policy não protege
contra erro de filtro (CLAUDE.md §7). A ÚNICA leitura sem tenant é `fila_a_frente`, que só traz (prioridade,
disponivel_em) para contar a posição na fila — nenhum id, nenhuma corretora.

`db` é o cliente PostgREST (`get_supabase_client().client`): `.table(...).select/insert/update/eq/in_/gt/order/limit`.
Síncrono, como o resto do produto; a porta chama por `asyncio.to_thread`.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

PEDIDOS = "multicalculo_pedidos"
CALCULOS = "multicalculo_calculos"
OFERTAS = "multicalculo_ofertas"
EVENTOS = "multicalculo_eventos"
ADESOES = "multicalculo_adesoes"

#: o que a porta lê de um cálculo (nunca `pedido_cifrado`, que mora no pedido e só o motor decifra)
_COLS_CALCULO = ("id, pedido_id, solicitante_company_id, company_id, opcao, coberturas, status, negocio_ref, versao, "
                 "origem_calculo_id, ajuste, prioridade, expira_em, disponivel_em, disparado_em, primeira_oferta_em, "
                 "quadro_pronto_em, fechado_em, erro, criado_em")
_COLS_OFERTA = ("id, calculo_id, pedido_id, company_id, seguradora, seguradora_codigo, pacote, tipo_de_pacote, "
                "premio_total, premio_mensal, franquia_valor, franquia_tipo, coberturas, parcelamentos, tem_pdf, "
                "alertas, comissao_percentual, recebida_em, atualizada_em")
_COLS_EVENTO = ("id, calculo_id, pedido_id, company_id, tipo, seguradora, seguradora_codigo, pacote, tipo_de_pacote, "
                "familia, oferta_id, t_s, criado_em")


def _dados(resposta: Any) -> List[Dict[str, Any]]:
    return list(getattr(resposta, "data", None) or [])


class RepositorioMulticalculo:
    def __init__(self, db: Any = None):
        self._db = db

    @property
    def db(self) -> Any:
        if self._db is None:
            from app.core.database import get_supabase_client

            self._db = get_supabase_client().client
        return self._db

    # ------------------------------------------------------------------ empresas e adesões
    def tipos_de_empresa(self, ids: Iterable[str]) -> Dict[str, str]:
        """{company_id: company_kind} das que existem (as que faltam não aparecem)."""
        alvo = sorted({str(i) for i in ids})
        if not alvo:
            return {}
        linhas = _dados(self.db.table("companies").select("id, company_kind").in_("id", alvo).execute())
        return {str(l["id"]): str(l.get("company_kind") or "") for l in linhas}

    def adesoes_ativas(self, *, canal_company_id: str, corretoras: Iterable[str]) -> set:
        alvo = sorted({str(c) for c in corretoras})
        if not alvo:
            return set()
        linhas = _dados(self.db.table(ADESOES).select("corretora_company_id, ativa")
                        .eq("canal_company_id", str(canal_company_id))
                        .in_("corretora_company_id", alvo).eq("ativa", True).execute())
        return {str(l["corretora_company_id"]) for l in linhas if l.get("ativa") is True}

    # ------------------------------------------------------------------ escrita
    def gravar_pedido(self, pedido: Dict[str, Any], calculos: List[Dict[str, Any]]
                      ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """1 pedido + N cálculos. Sem transação no PostgREST: se os cálculos falharem, o pedido sai (CASCADE)."""
        criado = _dados(self.db.table(PEDIDOS).insert(pedido).execute())
        if not criado:
            raise RuntimeError("o banco não devolveu o pedido gravado")
        linha = criado[0]
        try:
            gravados = _dados(self.db.table(CALCULOS).insert(calculos).execute())
        except Exception:
            self.db.table(PEDIDOS).delete().eq("id", linha["id"]).eq("company_id", linha["company_id"]).execute()
            raise
        return linha, gravados

    def inserir_calculo(self, calculo: Dict[str, Any]) -> Dict[str, Any]:
        gravado = _dados(self.db.table(CALCULOS).insert(calculo).execute())
        if not gravado:
            raise RuntimeError("o banco não devolveu o cálculo gravado")
        return gravado[0]

    def reabrir_pedido(self, *, company_id: str, pedido_id: str) -> None:
        """F4 (costura): o recálculo entra num pedido que o motor já FECHOU (todos os cálculos terminais). Sem
        reabrir, o motor cancela o cálculo novo (`pedido.status != aberto` → cancelado). Cancelado não reabre."""
        self.db.table(PEDIDOS).update({"status": "aberto"}).eq("id", str(pedido_id)).eq(
            "company_id", str(company_id)).eq("status", "fechado").execute()

    def cancelar(self, *, company_id: str, pedido_id: str) -> int:
        """Pedido → cancelado; cálculos ainda na fila → cancelado. Os que já estão no robô o motor termina."""
        feito = _dados(self.db.table(PEDIDOS).update({"status": "cancelado"})
                       .eq("id", str(pedido_id)).eq("company_id", str(company_id)).execute())
        if not feito:
            return 0
        canc = _dados(self.db.table(CALCULOS).update({"status": "cancelado"})
                      .eq("pedido_id", str(pedido_id)).eq("solicitante_company_id", str(company_id))
                      .eq("status", "na_fila").execute())
        return len(canc)

    # ------------------------------------------------------------------ leitura (sempre do solicitante)
    def pedido(self, *, company_id: str, pedido_id: str) -> Optional[Dict[str, Any]]:
        linhas = _dados(self.db.table(PEDIDOS)
                        .select("id, company_id, origem, ramo, opcoes, corretoras, quadro_s, status, criado_em")
                        .eq("id", str(pedido_id)).eq("company_id", str(company_id)).limit(1).execute())
        return linhas[0] if linhas else None

    def calculos_do_pedido(self, *, company_id: str, pedido_id: str) -> List[Dict[str, Any]]:
        return _dados(self.db.table(CALCULOS).select(_COLS_CALCULO)
                      .eq("pedido_id", str(pedido_id)).eq("solicitante_company_id", str(company_id))
                      .order("criado_em").execute())

    def calculo(self, *, company_id: str, calculo_id: str) -> Optional[Dict[str, Any]]:
        linhas = _dados(self.db.table(CALCULOS).select(_COLS_CALCULO)
                        .eq("id", str(calculo_id)).eq("solicitante_company_id", str(company_id))
                        .limit(1).execute())
        return linhas[0] if linhas else None

    def ofertas_do_pedido(self, *, company_id: str, pedido_id: str) -> List[Dict[str, Any]]:
        return _dados(self.db.table(OFERTAS).select(_COLS_OFERTA)
                      .eq("pedido_id", str(pedido_id)).eq("solicitante_company_id", str(company_id))
                      .order("premio_total").limit(1000).execute())

    def eventos_do_pedido(self, *, company_id: str, pedido_id: str, desde_evento: int = 0) -> List[Dict[str, Any]]:
        return _dados(self.db.table(EVENTOS).select(_COLS_EVENTO)
                      .eq("pedido_id", str(pedido_id)).eq("solicitante_company_id", str(company_id))
                      .gt("id", int(desde_evento or 0)).order("id").limit(1000).execute())

    def fila_a_frente(self) -> List[Dict[str, Any]]:
        """(prioridade, disponivel_em) de TODO cálculo na fila — só para contar a posição. Nenhum id sai daqui."""
        return _dados(self.db.table(CALCULOS).select("prioridade, disponivel_em")
                      .eq("status", "na_fila").order("prioridade").limit(5000).execute())
