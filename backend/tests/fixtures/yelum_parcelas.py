# -*- coding: utf-8 -*-
"""Respostas REAIS do Novo MEC da Yelum — com os dados trocados.

📊 Capturadas do HAR do founder e de visita real em 12/08/2026 (Resulta). A
**estrutura** é fiel: mesmas chaves, mesma grafia (`TelePhoneNumber` com o P
maiúsculo no meio, `PolicyRenewed ` com espaço no fim — os dois são erros da
Yelum, e um parser que os "conserta" para de casar).

Os **dados** são inventados (SPEC-023A §4). Nenhum segurado real aparece aqui.

Os casos existem de propósito:

    FB · vencida há 30 dias   -> o caminho feliz
    DC · débito em conta      -> nunca vira boleto
    CC · cartão de crédito    -> idem, e com motivo de recusa
    FB · vence amanhã         -> a carência de 48 h
"""

# ---------------------------------------------------------------------------
# GET /payment/installment/overdue?filter=count   — a TESTEMUNHA
# ---------------------------------------------------------------------------
CONTADOR = {"Total": 4}
CONTADOR_MAIOR = {"Total": 9}     # o portal conta 9, a janela só alcança 4

# ---------------------------------------------------------------------------
# POST /payment/installment/search-by-brokerlist
# ---------------------------------------------------------------------------
def lista(venc_atrasada: str, venc_amanha: str, *, total: int = 4) -> dict:
    """Datas entram no momento do teste — fixture com data fixa envelhece."""
    return {
        "total": total,
        "response": [
            {"Status": "Atrasado", "IssuanceID": 2, "ProductName": "Yelum Engenharia - Construção",
             "PolicyNumber": "600000000000101", "Amount": "1.672,62", "ExtDueDate": None,
             "Tax": "114,96", "ContractID": 50000001, "RejDate": None,
             "CommercialProductName": None, "BrokerName": "CORRETORA DE EXEMPLO LTDA",
             "InstallmentID": 2, "PaymentModality": "FB", "AmountCorrected": "0,00",
             "StatusID": "1", "RejReason": None, "CustomerName": "ARINALDO PEIXOTO SOARES",
             "DueDate": venc_atrasada, "PaymentModalityDesc": "Boleto bancário",
             "OriginalDueDate": venc_atrasada, "OriginalAmount": "1.672,62"},
            {"Status": "Atrasado", "IssuanceID": 1, "ProductName": "Yelum Auto",
             "PolicyNumber": "600000000000202", "Amount": "474,17", "ExtDueDate": None,
             "Tax": "31,05", "ContractID": 50000002, "RejDate": venc_atrasada,
             "CommercialProductName": None, "BrokerName": "CORRETORA DE EXEMPLO LTDA",
             "InstallmentID": 3, "PaymentModality": "DC", "AmountCorrected": "0,00",
             "StatusID": "1", "RejReason": "SALDO INSUFICIENTE",
             "CustomerName": "BENEDITA ALMEIDA CAMPOS", "DueDate": venc_atrasada,
             "PaymentModalityDesc": "Débito em conta", "OriginalDueDate": venc_atrasada,
             "OriginalAmount": "474,17"},
            {"Status": "Atrasado", "IssuanceID": 1, "ProductName": "Yelum Residencial",
             "PolicyNumber": "600000000000303", "Amount": "343,00", "ExtDueDate": None,
             "Tax": "22,45", "ContractID": 50000003, "RejDate": None,
             "CommercialProductName": None, "BrokerName": "CORRETORA DE EXEMPLO LTDA",
             "InstallmentID": 4, "PaymentModality": "CC", "AmountCorrected": "0,00",
             "StatusID": "1", "RejReason": "CARTAO EXPIRADO",
             "CustomerName": "CLARISSE BRANDAO MOURA", "DueDate": venc_atrasada,
             "PaymentModalityDesc": "Cartão de crédito", "OriginalDueDate": venc_atrasada,
             "OriginalAmount": "343,00"},
            {"Status": "Atrasado", "IssuanceID": 3, "ProductName": "Yelum Comércio e Serviços",
             "PolicyNumber": "600000000000404", "Amount": "1.229,63", "ExtDueDate": None,
             "Tax": "80,10", "ContractID": 50000004, "RejDate": None,
             "CommercialProductName": None, "BrokerName": "CORRETORA DE EXEMPLO LTDA",
             "InstallmentID": 11, "PaymentModality": "FB", "AmountCorrected": "0,00",
             "StatusID": "1", "RejReason": None,
             "CustomerName": "DOMINGOS COMERCIO DE PECAS LTDA", "DueDate": venc_amanha,
             "PaymentModalityDesc": "Boleto bancário", "OriginalDueDate": venc_amanha,
             "OriginalAmount": "1.229,63"},
        ],
    }

# ---------------------------------------------------------------------------
# POST /customer/searchCustomerPolicy   {"PolicyNumber": "…"}
#
# 📊 Repare: e-mail preenchido e telefone VAZIO. Foi assim no registro real —
# é a prova de que o telefone do portal não serve como destinatário.
# ---------------------------------------------------------------------------
CLIENTE = {"response": [{
    "CustomerID": "11122233344",
    "CustomerName": "ARINALDO PEIXOTO SOARES",
    "SocialName": "",
    "EmailAddress": "EXEMPLO@EXEMPLO.COM.BR",
    "PolicyNumber": "600000000000101",
    "ValidityStartDate": "2025-02-26T03:00:00.000Z",
    "ValidityEndDate": "2027-07-01T03:00:00.000Z",
    "TelephoneAreaCode": "",
    "TelePhoneNumber": "",
    "IssuanceID": 1,
    "IssuanceType": "Apólice",
}]}

CLIENTE_PJ = {"response": [{
    "CustomerID": "44555666000177",
    "CustomerName": "DOMINGOS COMERCIO DE PECAS LTDA",
    "EmailAddress": "EXEMPLO@EXEMPLO.COM.BR",
    "PolicyNumber": "600000000000404",
    "TelephoneAreaCode": "", "TelePhoneNumber": "",
}]}

# ---------------------------------------------------------------------------
# POST /payment/getPaymentInstallments   — repare no formato do valor
#
# 🔴 `1672.62` aqui, `1.672,62` na lista. MESMA API, endpoints diferentes.
# ---------------------------------------------------------------------------
PARCELAS_DA_APOLICE = {"response": [
    {"ContractID": 50000001, "PolicyNumber": "600000000000101", "IssuanceID": 2,
     "InstallmentID": 1, "Amount": "1672.6", "Status": "Quitado",
     "DueDate": "2026-07-08T03:00:00.000Z", "Extended": "No",
     "AmountCorrected": "0", "AmountReceived": "1711.2",
     "Modality": "FB", "ModalityDesc": "Boleto bancário"},
    {"ContractID": 50000001, "PolicyNumber": "600000000000101", "IssuanceID": 2,
     "InstallmentID": 2, "Amount": "1672.62", "Status": "Atrasado",
     "DueDate": "2026-08-08T03:00:00.000Z", "Extended": "No",
     "AmountCorrected": "0", "AmountReceived": "0",
     "Modality": "FB", "ModalityDesc": "Boleto bancário"},
    {"ContractID": 50000001, "PolicyNumber": "600000000000101", "IssuanceID": 2,
     "InstallmentID": 3, "Amount": "1672.62", "Status": "A Vencer",
     "DueDate": "2026-09-08T03:00:00.000Z", "Extended": "No",
     "AmountCorrected": "0", "AmountReceived": "0",
     "Modality": "FB", "ModalityDesc": "Boleto bancário"},
]}

# ---------------------------------------------------------------------------
# GET /payment/policy/{n}/issuance/{n}/simulatepaymentmethodchange
#
# 🚫 A journey NUNCA chama — está aqui só porque é ele que documenta as formas
# de pagamento que a Yelum aceita, e a regra do débito nasce dessa lista.
# ---------------------------------------------------------------------------
FORMAS_DE_PAGAMENTO = {
    "allowChange": False,
    "claimIndicate": False,
    "allowedPaymentMethod": [
        {"paymentModality": "DC", "paymentModalityDescription": "Débito em conta",
         "warningMessages": None, "isActualModality": False},
        {"paymentModality": "CC", "paymentModalityDescription": "Cartão de crédito",
         "warningMessages": None, "isActualModality": False},
        {"paymentModality": "PX", "paymentModalityDescription": "QR Code Pix",
         "warningMessages": None, "isActualModality": False},
    ],
    "currentModality": {"currentmodality": "FB", "modalityDescription": "Boleto bancário",
                        "warningMessages": None},
    "errorMessages": ["A parcela 2 está vencida e não permite alteração."],
}
