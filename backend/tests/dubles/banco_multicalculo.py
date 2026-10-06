# -*- coding: utf-8 -*-
"""O BANCO DUBLÊ do multicálculo — SPEC-129-B (extraído do teste do motor na F4, a costura).

`dubles_do_work_os.BancoEmMemoria` (o PostgREST: CAS que devolve só a linha que casou, filtros com a semântica do
SQL) + o esquema do U1 da SPEC (migration 20261005_01) e as travas dele que o motor e a porta podem violar
(CHECKs, FKs compostas, `unique(calculo_id, chave)`, `unique` da oferta). Usado por `test_spec129b_o_motor.py` e
`test_spec129b_o_fio.py` — UM dublê, não dois.

⚠️ O que ele NÃO prova: o banco real (isso é o VERIFY da migration, `test_spec129b_o_banco.py`, e o canário).
"""
from __future__ import annotations

import dubles_do_work_os as D
from portal_worker.multicalculo import robos as ROB

U = ("uuid", False, None)
UN = ("uuid", True, None)
TN = ("text", True, None)
TSN = ("ts", True, None)
ESQUEMA_U1 = {
    "multicalculo_pedidos": {
        "id": ("uuid", False, "UUID"), "company_id": U, "origem": ("text", False, None),
        "ramo": ("int", False, 31), "opcoes": ("jsonb", False, "JSON:[]"), "corretoras": ("jsonb", False, "JSON:[]"),
        "pedido_cifrado": ("text", False, None), "cpf_hmac": TN, "quadro_s": ("int", False, 60),
        "status": ("text", False, "aberto"), "criado_em": ("ts", False, "NOW"), "atualizado_em": ("ts", False, "NOW"),
    },
    "multicalculo_calculos": {
        "id": ("uuid", False, "UUID"), "pedido_id": U, "solicitante_company_id": U, "company_id": U,
        "opcao": ("text", False, None), "coberturas": ("jsonb", False, None), "status": ("text", False, "na_fila"),
        "account_id": UN, "negocio_ref": TN, "versao": ("int", True, None), "origem_calculo_id": UN,
        "ajuste": ("jsonb", True, None), "prioridade": ("int", False, 5), "expira_em": TSN, "disponivel_em": TSN,
        "tentativas": ("int", False, 0), "dono": TN, "batida_em": TSN, "disparado_em": TSN,
        "primeira_oferta_em": TSN, "quadro_pronto_em": TSN, "fechado_em": TSN, "erro": TN,
        "criado_em": ("ts", False, "NOW"),
    },
    "multicalculo_ofertas": {
        "id": ("uuid", False, "UUID"), "calculo_id": U, "pedido_id": U, "company_id": U, "solicitante_company_id": U,
        "seguradora": TN, "seguradora_codigo": ("int", True, None), "pacote": TN, "tipo_de_pacote": ("int", True, None),
        "premio_total": ("num", False, None), "premio_mensal": ("num", True, None), "franquia_valor": ("num", True, None),
        "franquia_tipo": TN, "coberturas": ("jsonb", True, None), "parcelamentos": ("jsonb", True, None),
        "tem_pdf": ("bool", False, False), "pdf_path": TN, "alertas": ("jsonb", True, None),
        "comissao_percentual": ("num", True, None), "recebida_em": ("ts", False, "NOW"),
        "atualizada_em": ("ts", False, "NOW"),
    },
    "multicalculo_eventos": {
        "id": ("int", False, "SERIAL"), "calculo_id": U, "pedido_id": U, "company_id": U, "solicitante_company_id": U,
        "tipo": ("text", False, None), "seguradora": TN, "seguradora_codigo": ("int", True, None), "pacote": TN,
        "tipo_de_pacote": ("int", True, None), "familia": TN, "oferta_id": UN, "chave": ("text", False, None),
        "t_s": ("num", True, None), "criado_em": ("ts", False, "NOW"),
    },
}
COLUNAS_ROBO = {"robo_estado": TN, "robo_teto_por_hora": ("int", True, None), "robo_janela": ("jsonb", True, None),
                "robo_ocupada_ate": TSN, "robo_dono": TN, "robo_batida_em": TSN}
STATUS = ("na_fila", "disparando", "calculando", "fechado", "falhou", "incerto", "cancelado", "expirado")
FK_DO_CALCULO = (("calculo_id", "id"), ("pedido_id", "pedido_id"), ("company_id", "company_id"),
                 ("solicitante_company_id", "solicitante_company_id"))


class BancoU1(D.BancoEmMemoria):
    """O banco dublê com as travas do U1 que o motor pode violar."""

    def _travas(self, tabela, nova, velha):
        super()._travas(tabela, nova, velha)
        if tabela == "multicalculo_calculos":
            self._check("ck_mc_calculos_status", nova["status"] in STATUS)
            # o CHECK de HOJE: 20261005_01 alargado pela 20261006_02 (SPEC-130-A F4, a completa+)
            self._check("ck_mc_calculos_opcao", nova["opcao"] in ("padrao", "economica", "completa_mais", "ajuste"))
            self._check("ck_mc_calculos_negocio",
                        nova["status"] not in ("calculando", "fechado")
                        or (bool(nova.get("negocio_ref")) and nova.get("versao") is not None))
            self._fk(tabela, "fk_mc_calculos_conta_mesma_corretora",
                     (("account_id", "id"), ("company_id", "company_id")), "portal_accounts", nova)
            self._fk(tabela, "fk_mc_calculos_pedido",
                     (("pedido_id", "id"), ("solicitante_company_id", "company_id")), "multicalculo_pedidos", nova)
        elif tabela == "multicalculo_ofertas":
            self._fk(tabela, "fk_mc_ofertas_calculo", FK_DO_CALCULO, "multicalculo_calculos", nova)
            self._unico(tabela, "uq_mc_ofertas", ("calculo_id", "seguradora_codigo", "pacote", "tipo_de_pacote"),
                        nova, velha)
            self._check("ck_mc_ofertas_premio", float(nova["premio_total"]) > 0)
        elif tabela == "multicalculo_eventos":
            if velha is not None:
                raise D.erro_do_banco("P0001", "evento não se reescreve")
            self._fk(tabela, "fk_mc_eventos_calculo", FK_DO_CALCULO, "multicalculo_calculos", nova)
            self._unico(tabela, "uq_mc_eventos_chave", ("calculo_id", "chave"), nova, velha)
        elif tabela == "portal_accounts":
            self._check("ck_robo_estado", nova.get("robo_estado") in (None,) + ROB.ESTADOS)
            self._check("ck_robo_teste_tem_janela",
                        nova.get("robo_estado") != "teste" or nova.get("robo_janela") is not None)


#: o que a PORTA lê além do motor: o tipo da empresa e as adesões do canal (D-129B-05)
COMPANIES_U1 = {"id": ("uuid", False, "UUID"), "company_kind": ("text", True, None),
                "company_name": ("text", True, None), "is_technical": ("bool", True, None)}
ADESOES_U1 = {"id": ("uuid", False, "UUID"), "canal_company_id": U, "corretora_company_id": U,
              "ativa": ("bool", False, True), "criada_em": ("ts", False, "NOW"), "desativada_em": TSN}


def instalar_esquema(monkeypatch, *, com_porta: bool = False) -> None:
    """Põe o esquema do U1 no dublê (desfeito pelo monkeypatch ao fim do teste)."""
    for tabela, cols in ESQUEMA_U1.items():
        monkeypatch.setitem(D.ESQUEMA, tabela, cols)
    monkeypatch.setitem(D.ESQUEMA, "portal_accounts", {**D.ESQUEMA["portal_accounts"], **COLUNAS_ROBO})
    if com_porta:
        monkeypatch.setitem(D.ESQUEMA, "companies", {**D.ESQUEMA["companies"], **COMPANIES_U1})
        monkeypatch.setitem(D.ESQUEMA, "multicalculo_adesoes", ADESOES_U1)
