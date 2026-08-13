# -*- coding: utf-8 -*-
"""Fixture da MAPFRE — ESTRUTURA real, DADOS inventados (SPEC-023A §4).

Medido em 13/08/2026 numa sessao real da AutoFleet. Nenhum CPF, nome, apolice
ou valor aqui pertence a alguem: as chaves e os formatos sao os do portal, o
conteudo e ficcao.

O que cada peca guarda
======================
    BROKERS ................. as DUAS corretoras que UM login enxerga.
                              E o coracao do gate cross-tenant.
    BROKERS_AMBIGUO ......... duas linhas com o MESMO nome -> a journey para.
    BROKERS_SEM_ALVO ........ nenhuma bate o account_label -> a journey para.
    LISTA_VENCIDAS .......... duas parcelas em BOLETO, o caso feliz.
    LISTA_MISTA ............. as QUATRO formas de pagamento vistas nos dados,
                              incluindo a forma 5 que NAO existe no dropdown.
    PAGINA_1 / PAGINA_2 ..... `total` maior que a pagina -> obriga paginar.
    DOCUMENTO_BOLETO ........ o envelope com o PDF em Base64.
    DOCUMENTO_SEM_PDF ....... o mesmo envelope com lixo dentro.

📊 As duas carteiras de BROKERS sao DISJUNTAS de proposito: foi o que a medicao
real mostrou (59 parcelas/21 clientes numa, 8/4 na outra, zero em comum). Um
teste em que as duas pudessem ser iguais nao guardaria nada.
"""
from __future__ import annotations

import base64

# --------------------------------------------------------------------------
# GET /api/1.0.0/distributor/{distributorId}/brokers
# --------------------------------------------------------------------------
RESULTA = "RESULTA CORRETORA DE SEGUROS L"
AUTOFLEET = "AUTO FLEET R CORRETORA DE SEGU"

BROKERS = [
    {"brokerId": "12542146", "brokerDesc": RESULTA},
    {"brokerId": "55744776", "brokerDesc": AUTOFLEET},
]

# Duas linhas com o mesmo rotulo: nao da para escolher, entao nao se escolhe.
BROKERS_AMBIGUO = [
    {"brokerId": "11111111", "brokerDesc": AUTOFLEET},
    {"brokerId": "22222222", "brokerDesc": AUTOFLEET},
]

BROKERS_SEM_ALVO = [
    {"brokerId": "99999999", "brokerDesc": "OUTRA CORRETORA QUALQUER SA"},
]

BROKERS_VAZIO: list = []


# --------------------------------------------------------------------------
# POST /api/1.0.0/distributor/{distributorId}/receipts
# --------------------------------------------------------------------------
def _item(*, doc, nome, apolice, endosso="0", parcela="1", de="12",
          status="02", forma="4", forma_desc="BOLETO", valor=294.35,
          vencimento="2026-07-26T00:00:00Z", broker="55744776",
          produto="AUTOMOVEIS", produto_cod="231", pj=False):
    """Um item da lista, no formato exato que a MAPFRE devolve."""
    if pj:
        pessoa = {"legalPerson": {"companyName": nome,
                                  "identityDocumentNumber": doc,
                                  "identityDocumentType": 1}}
    else:
        pessoa = {"naturalPerson": {"personName": {"name": nome, "middleName": None,
                                                   "firstSurname": None,
                                                   "secondSurname": None},
                                    "identityDocumentNumber": doc,
                                    "identityDocumentType": 0}}
    return {
        "client": {"clientId": f"{doc}_1", "status": None, **pessoa,
                   # 📊 O portal manda os dois VAZIOS. O WhatsApp vem da gestao.
                   "mainPhone": "", "email": "", "category": "02"},
        "receipt": {
            "receiptId": f"{apolice}_{endosso}_{parcela}",
            "receiptNumber": f"{parcela}/{de}",
            "receiptStatusCode": status,
            "receiptTotFinalAmn": valor,
            "paymentMethodTypeCode": forma,
            "paymentMethodTypeDesc": forma_desc,
            "policyId": f"31_{produto_cod}_{apolice}_{endosso}_TWM",
            "policyNumber": apolice,
            "businessLine": "00",
            "endorsementId": endosso,
            "endorsementNumber": endosso,
            "productCode": produto_cod,
            "productDesc": produto,
            "dueDate": vencimento,
        },
        "brokerProductionKey": {"broker": {"brokerDesc": None, "brokerId": broker},
                                "productionsKeys": ["130183"]},
        "allowedActions": None,
    }


# O caso feliz: duas vencidas, as duas em boleto, da MESMA apolice.
LISTA_VENCIDAS = {
    "version": "2.0",
    "total": 2,
    "list": [
        _item(doc="11122233344", nome="CLIENTE DE TESTE UM", apolice="1000000000001",
              parcela="8", valor=294.35, vencimento="2026-07-26T00:00:00Z"),
        _item(doc="11122233344", nome="CLIENTE DE TESTE UM", apolice="1000000000001",
              parcela="9", valor=294.35, vencimento="2026-07-26T00:00:00Z"),
    ],
}

# 🔴 As QUATRO formas vistas nos dados reais. A `5` nao aparece no <ion-select>
# da tela — quem montar a regra pela tela deixa ela passar como se fosse boleto.
LISTA_MISTA = {
    "version": "2.0",
    "total": 5,
    "list": [
        _item(doc="11122233344", nome="PAGA COM BOLETO", apolice="1000000000001",
              parcela="8", forma="4", forma_desc="BOLETO"),
        _item(doc="22233344455", nome="PAGA COM CARTAO", apolice="1000000000002",
              parcela="3", forma="1", forma_desc="CARTÃO DE CRÉDITO"),
        _item(doc="33344455566", nome="PAGA COM DEBITO", apolice="1000000000003",
              parcela="5", forma="2", forma_desc="DÉBITO EM CONTA"),
        _item(doc="44455566677", nome="DEBITO DE OUTRO CODIGO", apolice="1000000000004",
              parcela="2", forma="5", forma_desc="DÉBITO EM CONTA"),
        _item(doc="55566677788", nome="EMPRESA DE TESTE LTDA", apolice="1000000000005",
              parcela="4", forma="4", forma_desc="BOLETO", pj=True),
    ],
}

# A carteira da OUTRA corretora — nenhum cliente em comum com a de cima.
LISTA_DA_OUTRA_CORRETORA = {
    "version": "2.0",
    "total": 2,
    "list": [
        _item(doc="90090090001", nome="CLIENTE DA OUTRA UM", apolice="2000000000001",
              parcela="2", broker="12542146"),
        _item(doc="90090090002", nome="CLIENTE DA OUTRA DOIS", apolice="2000000000002",
              parcela="7", broker="12542146"),
    ],
}

# `total` maior que o que a pagina traz: obriga paginar antes de concluir.
PAGINA_1 = {
    "version": "2.0", "total": 3,
    "list": [_item(doc="11122233344", nome="UM", apolice="1000000000001", parcela="1")],
}
PAGINA_2 = {
    "version": "2.0", "total": 3,
    "list": [_item(doc="22233344455", nome="DOIS", apolice="1000000000002", parcela="2")],
}
PAGINA_3 = {
    "version": "2.0", "total": 3,
    "list": [_item(doc="33344455566", nome="TRES", apolice="1000000000003", parcela="3")],
}

LISTA_VAZIA = {"version": "2.0", "total": 0, "list": []}

# 🔴 http 200 com corpo que nao da para ler. NAO e carteira em dia.
LISTA_ILEGIVEL: dict = {}


# --------------------------------------------------------------------------
# GET /api/1.0.0/policy/document/BO_{receiptId}
# --------------------------------------------------------------------------
_PDF_FALSO = (b"%PDF-1.5\n1 0 obj<</Type/Catalog>>endobj\n"
              b"trailer<</Root 1 0 R>>\n%%EOF\n")

DOCUMENTO_BOLETO = {
    "documentId": "BO_1000000000001_0_8",
    "documentData": {"documentContent": base64.b64encode(_PDF_FALSO).decode()},
    "documentMetadata": {
        "url": None, "name": "1000000000001", "type": "pdf",
        "issueDocumentTypeCode": None, "issueDocumentTypeDesc": None,
        "description": "BO", "dateCapture": "2026-08-13T10:00:00Z",
        "status": None, "URL": None, "owner": None,
        # 📊 Este numero MENTE: o PDF real tinha 19.985 bytes e o campo dizia
        # 67.548. Validar por ele reprovaria um documento bom.
        "size": 67548,
        "mimeType": "APPLICATION_PDF", "source": "DCTM",
    },
}

DOCUMENTO_SEM_PDF = {
    "documentId": "BO_1000000000002_0_3",
    "documentData": {"documentContent": base64.b64encode(b"<html>erro</html>").decode()},
    "documentMetadata": {"description": "BO", "mimeType": "APPLICATION_PDF"},
}

DOCUMENTO_VAZIO = {"documentId": "BO_1000000000003_0_5", "documentData": {}}


# --------------------------------------------------------------------------
# POST /api/1.0.0/distributor/{id}/receipts/{n}/actions  — so leitura
# --------------------------------------------------------------------------
ACOES = {"allowChangePaymentMethod": "N", "allowReschedule": "N",
         "hasHistory": "N", "rescheduleObservations": {"code": 103, "description": None}}
