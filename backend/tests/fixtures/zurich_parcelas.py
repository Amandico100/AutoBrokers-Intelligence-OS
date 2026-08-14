# -*- coding: utf-8 -*-
"""Fixture da Zurich — ESTRUTURA real, DADOS inventados (SPEC-023A §4).

Medido em 13/08/2026 na captura da AutoFleet: 37 parcelas numa janela de 30
dias. Nenhum CPF, nome, apolice ou valor aqui pertence a alguem.

O que cada peca guarda
======================
    LISTA ................. os quatro casos que a carteira real tinha:
                            Pago · Aprovado · pendente-com-boleto · pendente-em-debito
    LISTA_VALOR_QUEBRADO .. o item com "1,287,99" -- virgula de milhar E de
                            decimal na mesma string. O parser antigo devolve None.
    BOLETO ................ FileContents e um ARRAY DE BYTES, nao base64.
    BOLETO_SEM_PDF ........ o mesmo envelope com lixo dentro.
    DETALHE_APOLICE ....... devolve Sucursal/CodigoCarteira, que a lista NAO tem
    DETALHE_SEGURADO ...... onde mora o CPF/CNPJ

📊 O portal ja calcula `diasAtraso`. Os itens abaixo mantem a coerencia entre
`dataVencimentoFormated` e `diasAtraso` para a data-base 13/08/2026 — senao o
teste da testemunha nao guardaria nada.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# GET /ParcelaVencidaCorretor/ListarParcelaVencida?dataInicial=&dataFinal=
# --------------------------------------------------------------------------
def _item(*, apolice, parcela, valor, venc, dias, situacao, tipo,
          payment_no, nosso_numero="TIA00000001", obs=None, nome="CLIENTE DE TESTE",
          ramo="31", ramo_desc="AUTOMOVEL", endosso=0, certificado=0):
    """Um item no formato exato que a Zurich devolve.

    `dataVencimento` vem no formato do ASP.NET (`/Date(ms)/`) e SEMPRE junto do
    `dataVencimentoFormated` — a journey le o segundo, que nao depende de fuso.
    """
    return {
        "numeroApolice": apolice,
        "numeroCertificado": certificado,
        "numeroEndossoSPY": endosso,
        "digitoEndossoSPY": 0,
        "nossoNumero": nosso_numero,
        "numeroPrestacao": parcela,
        "dataVencimento": "/Date(1785985200000)/",
        "dataVencimentoFormated": f"{venc} 03:00:00",
        "diasAtraso": dias,
        "valorParcela": valor,
        # 🔴 IDENTICO ao valorParcela em 37 de 37 itens reais. O nome mente.
        "valorJuros": valor,
        "valorAcrescimo": 0,
        "valorDesconto": 0,
        "indicadorEmitido": "S",
        "nomeSegurado": nome,
        "payment_no": payment_no,
        "ramo": ramo,
        "descricaoRamo": ramo_desc,
        "situacaoParcela": situacao,
        "originalInvoiceIndicator": "Y",
        "indicadorErro": None,
        "codigoErro": None,
        "descricaoErro": None,
        "tipoPagamento": tipo,
        # a coluna O.B.S da tela — o texto que a atendente le
        "situacaoParcelaDescricao": obs,
        "vida": False,
        "TipoSeguro": {"Name": None, "Id": 0},
        "NumeroSeguro": 0,
    }


# 📊 Os quatro casos que a carteira real tinha, mantendo as proporcoes.
LISTA = {
    "corretor": [
        # o inadimplente de verdade: era debito, o debito falhou, virou boleto
        _item(apolice=10001, parcela=8, valor="638,95", venc="06/08/2026", dias=7,
              situacao="Parcela pendente", tipo="Boleto", payment_no=900000001,
              nosso_numero="0060000000001", obs="Débito não autorizado",
              nome="EMPRESA DE TESTE LTDA"),
        # pendente mas em DEBITO e vencendo hoje: nao e inadimplente, e nao tem boleto
        _item(apolice=10002, parcela=6, valor="680,21", venc="13/08/2026", dias=0,
              situacao="Parcela pendente", tipo="Débito", payment_no=900000002,
              nosso_numero=None, obs="Débito agendado", nome="CLIENTE DOIS"),
        # "Aprovado" = em processamento. NAO e inadimplente.
        _item(apolice=10003, parcela=7, valor="1,287,99", venc="13/08/2026", dias=0,
              situacao="Aprovado", tipo="Cartão de Crédito", payment_no=900000003,
              nome="CLIENTE TRES"),
        # pago
        _item(apolice=10004, parcela=10, valor="209,50", venc="26/07/2026", dias=18,
              situacao="Pago", tipo="Cartão de Crédito", payment_no=900000004,
              nome="CLIENTE QUATRO"),
    ],
    "AcionamentoSinistroVida": None,
}

# 🔴 O caso que quebra o parser antigo: virgula de milhar E de decimal.
#    📊 `_valor("1,287,99")` devolve None nos parsers da Yelum e da MAPFRE.
LISTA_VALOR_QUEBRADO = {
    "corretor": [
        _item(apolice=99001, parcela=3, valor="1,287,99", venc="01/08/2026", dias=12,
              situacao="Parcela pendente", tipo="Boleto", payment_no=111111111,
              nosso_numero="0061000000001", nome="CLIENTE DO VALOR GRANDE"),
    ],
    "AcionamentoSinistroVida": None,
}

# Uma forma de pagamento que a tela oferece e os dados nunca mostraram.
# 📊 O filtro da busca lista: 1 Boleto · 2 Debito em conta · 3 Cartao de credito
#    · 4 Pix · 5 Carne. Só tres apareceram nos dados. Por isso: lista de PERMISSAO.
LISTA_FORMA_DESCONHECIDA = {
    "corretor": [
        _item(apolice=99002, parcela=2, valor="500,00", venc="01/08/2026", dias=12,
              situacao="Parcela pendente", tipo="Pix", payment_no=222222222,
              nome="CLIENTE DO PIX"),
        _item(apolice=99003, parcela=2, valor="500,00", venc="01/08/2026", dias=12,
              situacao="Parcela pendente", tipo="Carnê", payment_no=333333333,
              nome="CLIENTE DO CARNE"),
    ],
    "AcionamentoSinistroVida": None,
}

LISTA_VAZIA = {"corretor": [], "AcionamentoSinistroVida": None}

# 🔴 http 200 com corpo que nao da para ler. NAO e carteira em dia.
LISTA_ILEGIVEL: dict = {}
LISTA_SEM_A_CHAVE = {"AcionamentoSinistroVida": None}


# --------------------------------------------------------------------------
# GET /SegundaViaBoletoCorretor/GerarBoleto?...
# --------------------------------------------------------------------------
_PDF_FALSO = (b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n"
              b"trailer<</Root 1 0 R>>\n%%EOF\n")

# 🔴 FileContents e um ARRAY DE BYTES (serializacao do FileContentResult do
#    ASP.NET), NAO base64. Tratar como base64 devolve lixo.
BOLETO = {
    "ExibeMsg": True,
    "Msg": "Prezado, o boleto estará registrado e disponível para pagamento no dia 14/08/2026.",
    "Boleto": {"FileContents": list(_PDF_FALSO),
               "ContentType": "application/pdf",
               "FileDownloadName": "SegundaViaBoleto.pdf"},
}

BOLETO_SEM_PDF = {
    "ExibeMsg": False, "Msg": None,
    "Boleto": {"FileContents": list(b"<html>erro</html>"),
               "ContentType": "application/pdf",
               "FileDownloadName": "SegundaViaBoleto.pdf"},
}

BOLETO_VAZIO = {"ExibeMsg": False, "Msg": None, "Boleto": None}
BOLETO_SEM_CONTEUDO = {"ExibeMsg": False, "Msg": None, "Boleto": {"FileContents": []}}


# --------------------------------------------------------------------------
# GET /Apolice/DetalheApolice  ->  o que a LISTA nao tem
# --------------------------------------------------------------------------
DETALHE_APOLICE = {
    "NumeroApoliceAnterior": None, "NumeroEndosso": 0, "NumeroCertificado": 0,
    "NumeroItem": 0,
    "Sucursal": "042",                 # <- so aqui
    "CodigoCorretor": None,
    "CodigoCarteira": "0531",          # <- diferente do `ramo` da lista (31)
    "Situacao": "Emitida",
    "CodigoSegurado": "00000000",
    "Produto": "PRODUTO DE TESTE AUTO",
    "PolicyNoAlt": "00000000000000000000000000000",   # <- so aqui
    "Ramo": "31",
    "TipoApolice": "01", "DescricaoTipoApolice": "Individual",
}

DETALHE_APOLICE_INCOMPLETO = {"NumeroEndosso": 0, "Situacao": "Emitida"}


# --------------------------------------------------------------------------
# GET /Apolice/DetalheDadosSegurado  ->  onde mora o CPF/CNPJ
# --------------------------------------------------------------------------
DETALHE_SEGURADO_PJ = {
    "NomeSegurado": "EMPRESA DE TESTE LTDA",
    "CodigoSegurado": "00000000",
    "CpfCgcSegurado": "11222333000181",
    "NumeroDocumentoSegurado": "11222333000181",
    "IndicadorTipoPessoa": 2,
    "TelefoneDDDSegurado": None, "TelefoneSegurado": "4700000000",
    "Email": "contato@exemplo-de-teste.com.br",
    "CidadeSegurado": "FLORIANOPOLIS", "UfSegurado": "SC",
}

DETALHE_SEGURADO_PF = {
    "NomeSegurado": "CLIENTE PESSOA FISICA",
    "CpfCgcSegurado": "11122233344",
    "NumeroDocumentoSegurado": "11122233344",
    "IndicadorTipoPessoa": 1,
    "TelefoneSegurado": "4700000001", "Email": "",
}

DETALHE_SEGURADO_SEM_DOC = {"NomeSegurado": "SEM DOCUMENTO", "CpfCgcSegurado": ""}
