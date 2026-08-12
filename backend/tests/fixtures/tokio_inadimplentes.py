# -*- coding: utf-8 -*-
"""Respostas REAIS do Portal Parceiros da Tokio — com os dados trocados.

📊 Capturadas do HAR do founder em 12/08/2026 (corretora AutoFleet). A
**estrutura** é fiel byte a byte: mesmas tags, mesma ordem, mesma notação de
número, mesmos nomes de campo com a maiúscula que a Tokio usa
(`FlagSucesso`, `ListaVencimentosProrrogacao`, `cUrlCSF`).

Os **dados** são inventados — nome, CPF, apólice, título e telefone (SPEC-023A
§4). Nenhum segurado real aparece aqui, e a fixture pode ser lida por qualquer
pessoa do time sem virar vazamento.

Os quatro casos existem de propósito, e cada um já quebrou alguma coisa:

    ARINALDO   FICHA, vencida há 30 dias   -> o caminho feliz
    BENEDITA   DÉBITO, repique = S         -> nunca vira boleto (§ ROTAS/regra)
    CLARISSE   FICHA, 2 parcelas pendentes -> a armadilha da parcela errada
    DOMINGOS   FICHA, vence amanhã         -> a carência de 48 h
"""

# ---------------------------------------------------------------------------
# POST /portais/bff/v1/clientes/reports/parcelas/xml
# ---------------------------------------------------------------------------
RELATORIO_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sumarioClientesInadimplentes>
    <clientesInadimplentes>
        <cdApoliceTmsr>41000101</cdApoliceTmsr>
        <cdCorretor>099001</cdCorretor>
        <cdEndosso>0</cdEndosso>
        <cdRamo>312</cdRamo>
        <cdRamoTmsr>312</cdRamoTmsr>
        <codModuloProduto>00007</codModuloProduto>
        <codigoNegocio>170000001</codigoNegocio>
        <comissaoParcela>80.00</comissaoParcela>
        <cpfCnpjCliente>111.222.333-44</cpfCnpjCliente>
        <dddTelefone1>47</dddTelefone1>
        <dddTelefone3>47</dddTelefone3>
        <dtVencimento>{VENC_ATRASADA}</dtVencimento>
        <formaPagto>FICHA</formaPagto>
        <ideFact>900000001</ideFact>
        <idePol>70000001</idePol>
        <linha>10001</linha>
        <nmCliente>ARINALDO PEIXOTO SOARES</nmCliente>
        <nomeCorretor>CORRETORA DE EXEMPLO LTDA</nomeCorretor>
        <nroCarga>5000</nroCarga>
        <nroParcela>4</nroParcela>
        <numCert>180000001</numCert>
        <numOper>3400000001</numOper>
        <numTelefone1>33330001</numTelefone1>
        <numTelefone3>988880001</numTelefone3>
        <premioParcela>1191.89</premioParcela>
        <repique>N</repique>
        <tipo>A</tipo>
        <tipoApolice>ACX</tipoApolice>
    </clientesInadimplentes>
    <clientesInadimplentes>
        <cdApoliceTmsr>41000202</cdApoliceTmsr>
        <cdCorretor>099001</cdCorretor>
        <cdEndosso>0</cdEndosso>
        <cdRamo>312</cdRamo>
        <cdRamoTmsr>312</cdRamoTmsr>
        <codModuloProduto>00007</codModuloProduto>
        <codigoNegocio>170000002</codigoNegocio>
        <comissaoParcela>68.08</comissaoParcela>
        <cpfCnpjCliente>222.333.444-55</cpfCnpjCliente>
        <dddTelefone1>48</dddTelefone1>
        <dddTelefone3>48</dddTelefone3>
        <dtVencimento>{VENC_ATRASADA}</dtVencimento>
        <formaPagto>D&#201;BITO</formaPagto>
        <ideFact>900000002</ideFact>
        <idePol>70000002</idePol>
        <linha>10002</linha>
        <motivo>DEBITO NAO EFETUADO - INSUFICIENCIA DE FUNDOS</motivo>
        <nmCliente>BENEDITA ALMEIDA CAMPOS</nmCliente>
        <nomeCorretor>CORRETORA DE EXEMPLO LTDA</nomeCorretor>
        <nroCarga>5000</nroCarga>
        <nroParcela>3</nroParcela>
        <numCert>180000002</numCert>
        <numOper>3400000002</numOper>
        <numTelefone1>33330002</numTelefone1>
        <numTelefone3>988880002</numTelefone3>
        <premioParcela>474.17</premioParcela>
        <repique>S</repique>
        <tipo>A</tipo>
        <tipoApolice>ACX</tipoApolice>
    </clientesInadimplentes>
    <clientesInadimplentes>
        <cdApoliceTmsr>41000303</cdApoliceTmsr>
        <cdCorretor>099001</cdCorretor>
        <cdEndosso>0</cdEndosso>
        <cdRamo>312</cdRamo>
        <cdRamoTmsr>312</cdRamoTmsr>
        <codModuloProduto>00007</codModuloProduto>
        <codigoNegocio>170000003</codigoNegocio>
        <comissaoParcela>44.73</comissaoParcela>
        <cpfCnpjCliente>333.444.555-66</cpfCnpjCliente>
        <dddTelefone1>48</dddTelefone1>
        <dddTelefone3>48</dddTelefone3>
        <dtVencimento>{VENC_ATRASADA}</dtVencimento>
        <formaPagto>FICHA</formaPagto>
        <ideFact>900000003</ideFact>
        <idePol>70000003</idePol>
        <linha>10003</linha>
        <nmCliente>CLARISSE BRANDAO MOURA</nmCliente>
        <nomeCorretor>CORRETORA DE EXEMPLO LTDA</nomeCorretor>
        <nroCarga>5000</nroCarga>
        <nroParcela>3</nroParcela>
        <numCert>180000003</numCert>
        <numOper>3400000003</numOper>
        <numTelefone1>99990003</numTelefone1>
        <numTelefone3>991310003</numTelefone3>
        <premioParcela>343.00</premioParcela>
        <repique>N</repique>
        <tipo>A</tipo>
        <tipoApolice>ACX</tipoApolice>
    </clientesInadimplentes>
    <clientesInadimplentes>
        <cdApoliceTmsr>41000404</cdApoliceTmsr>
        <cdCorretor>099001</cdCorretor>
        <cdEndosso>0</cdEndosso>
        <cdRamo>531</cdRamo>
        <cdRamoTmsr>531</cdRamoTmsr>
        <codModuloProduto>00007</codModuloProduto>
        <codigoNegocio>170000004</codigoNegocio>
        <comissaoParcela>50.58</comissaoParcela>
        <cpfCnpjCliente>44.555.666/0001-77</cpfCnpjCliente>
        <dddTelefone1>27</dddTelefone1>
        <dddTelefone3>27</dddTelefone3>
        <dtVencimento>{VENC_AMANHA}</dtVencimento>
        <formaPagto>FICHA</formaPagto>
        <ideFact>900000004</ideFact>
        <idePol>70000004</idePol>
        <linha>10004</linha>
        <nmCliente>DOMINGOS COMERCIO DE PECAS LTDA</nmCliente>
        <nomeCorretor>CORRETORA DE EXEMPLO LTDA</nomeCorretor>
        <nroCarga>5000</nroCarga>
        <nroParcela>11</nroParcela>
        <numCert>180000004</numCert>
        <numOper>3400000004</numOper>
        <numTelefone1>33330004</numTelefone1>
        <numTelefone3>988880004</numTelefone3>
        <premioParcela>362.03</premioParcela>
        <repique>N</repique>
        <tipo>A</tipo>
        <tipoApolice>ACX</tipoApolice>
    </clientesInadimplentes>
    <comissaoNaoRecebida>243.39</comissaoNaoRecebida>
    <demaisParcelasPendentes>4</demaisParcelasPendentes>
    <primeiraParcelaPendente>0</primeiraParcelaPendente>
    <quantidadeClientes>4</quantidadeClientes>
    <quantidadeParcelas>4</quantidadeParcelas>
    <valorPremios>2371.09</valorPremios>
</sumarioClientesInadimplentes>
"""

# O mesmo documento com UM registro a menos que o total declarado. Serve para
# provar que o guarda da testemunha CONSEGUE falhar — um guarda que não tem como
# falhar não guarda nada (CLAUDE.md §9.3).
RELATORIO_XML_TRUNCADO = RELATORIO_XML.replace(
    "<quantidadeParcelas>4</quantidadeParcelas>",
    "<quantidadeParcelas>7</quantidadeParcelas>")


# ---------------------------------------------------------------------------
# GET /portais/visao-cliente-corretor/detalhe/apolice/<doc>/<idePol>
#
# Só o bloco `Dados Parcela` — é o único que a cobrança lê. A armadilha está
# aqui: as parcelas 3 E 4 estão `Pendente`, e só a 3 é a do relatório.
# ---------------------------------------------------------------------------
DETALHE_HTML = """<div class="row">
    <div class="col-md-12 list-consulta margin-top table-responsive">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>N&ordm; Parcela</th><th>N&deg; T&iacute;tulo</th>
                    <th>Data Vencimento</th><th>Valor</th>
                    <th>Situa&ccedil;&atilde;o Parcela</th><th>Data Pagamento</th>
                    <th>Tipo Pagamento</th><th>A&ccedil;&atilde;o</th><th>PIX</th>
                </tr>
            </thead>
            <tbody>
                    <tr id="tr-parcela-1" data-numerotitulo="7200000001">
                        <td>1</td>
                        <td>7200000001</td>
                        <td>17/06/2026</td>
                        <td>R$ 343,00</td>
                        <td>Pago</td>
                        <td>14/06/2026</td>
                        <td>FICHA DE COMPENSA&Ccedil;&Atilde;O</td>
                        <td id="parcela1">-</td>
                        <td></td>
                    </tr>
                    <tr id="tr-parcela-2" data-numerotitulo="7200000002">
                        <td>2</td>
                        <td>7200000002</td>
                        <td>10/07/2026</td>
                        <td>R$ 343,00</td>
                        <td>Pago</td>
                        <td>29/07/2026</td>
                        <td>FICHA DE COMPENSA&Ccedil;&Atilde;O</td>
                        <td id="parcela2">-</td>
                        <td></td>
                    </tr>
                    <tr id="tr-parcela-3" data-numerotitulo="7200000003">
                        <td>3</td>
                        <td>7200000003</td>
                        <td>10/08/2026</td>
                        <td>R$ 343,00</td>
                        <td>Pendente</td>
                        <td>-</td>
                        <td>FICHA DE COMPENSA&Ccedil;&Atilde;O</td>
                        <td id="parcela3">
                            <button class="btn btn-default btn-sm" onclick="VisaoUnicaClienteJS.carregarVencimentoPermitidoBoleto(&#39;7200000003&#39;,&#39;3&#39;,&#39;null&#39;,&#39;null&#39;,&#39;null&#39;, &#39;R$&#39;);">
                                <i class="fa fa-file-pdf-o fa-lg"></i>
                            </button>
                        </td>
                        <td>
                            <button class="btn btn-default btn-sm" onclick="VisaoUnicaClienteJS.validarParcelaPix(&#39;7200000003&#39;,&#39;FIC&#39;,&#39;CLARISSE BRANDAO MOURA&#39;,&#39;333.444.555-66&#39;,&#39;00007&#39;,&#39;0531&#39;,&#39;41000303&#39; ,&#39;0&#39; ,&#39;99001&#39;,&#39;99001&#39;);">
                                <i class="fa fa-qrcode fa-lg"></i>
                            </button>
                        </td>
                    </tr>
                    <tr id="tr-parcela-4" data-numerotitulo="7200000004">
                        <td>4</td>
                        <td>7200000004</td>
                        <td>10/09/2026</td>
                        <td>R$ 343,53</td>
                        <td>Pendente</td>
                        <td>-</td>
                        <td>FICHA DE COMPENSA&Ccedil;&Atilde;O</td>
                        <td id="parcela4">
                            <button class="btn btn-default btn-sm" onclick="VisaoUnicaClienteJS.carregarVencimentoPermitidoBoleto(&#39;7200000004&#39;,&#39;4&#39;,&#39;null&#39;,&#39;null&#39;,&#39;null&#39;, &#39;R$&#39;);">
                                <i class="fa fa-file-pdf-o fa-lg"></i>
                            </button>
                        </td>
                        <td>
                            <button class="btn btn-default btn-sm" onclick="VisaoUnicaClienteJS.validarParcelaPix(&#39;7200000004&#39;,&#39;FIC&#39;,&#39;CLARISSE BRANDAO MOURA&#39;,&#39;333.444.555-66&#39;,&#39;00007&#39;,&#39;0531&#39;,&#39;41000303&#39; ,&#39;0&#39; ,&#39;99001&#39;,&#39;99001&#39;);">
                                <i class="fa fa-qrcode fa-lg"></i>
                            </button>
                        </td>
                    </tr>
            </tbody>
        </table>
    </div>
</div>
"""

# ---------------------------------------------------------------------------
# POST /portais/bff/v1/consulta-unica/financeiro/prorrogacao
# ---------------------------------------------------------------------------
# Parcela AINDA A VENCER: uma única data, zero multa, zero juros.
PRORROGACAO_LIMPA = {
    "dataComparacao": "2026-09-10",
    "DataVencimentoOriginal": "10/09/2026",
    "FlagSucesso": True,
    "LinhaDigitavel": "03399.53465 54100.072310 78760.701017 1 15650000034353",
    "ListaVencimentosProrrogacao": [
        {"dataComparacao": "2026-09-10", "dataVencimento": "10/09/2026",
         "valorJuros": 0, "valorMulta": 0, "valorTotalProrrogacao": 343.53},
    ],
    "MensagemErro": "",
    "ValorOriginal": 343.53,
}

# Parcela JÁ VENCIDA: a data original (10/08) NÃO é opção. Só datas futuras, e
# cada uma com o seu acréscimo. A mais próxima é a mais barata.
PRORROGACAO_VENCIDA = {
    "dataComparacao": "2026-08-14",
    "DataVencimentoOriginal": "10/08/2026",
    "FlagSucesso": True,
    "LinhaDigitavel": "03399.53465 54100.071866 12318.001018 9 15340000119189",
    "ListaVencimentosProrrogacao": [
        {"dataComparacao": "2026-08-20", "dataVencimento": "20/08/2026",
         "valorJuros": 13.90, "valorMulta": 23.84, "valorTotalProrrogacao": 1229.63},
        {"dataComparacao": "2026-08-14", "dataVencimento": "14/08/2026",
         "valorJuros": 5.56, "valorMulta": 23.84, "valorTotalProrrogacao": 1221.29},
        {"dataComparacao": "2026-08-27", "dataVencimento": "27/08/2026",
         "valorJuros": 23.63, "valorMulta": 23.84, "valorTotalProrrogacao": 1239.36},
    ],
    "MensagemErro": "",
    "ValorOriginal": 1191.89,
}

PRORROGACAO_RECUSADA = {
    "FlagSucesso": False,
    "MensagemErro": "Titulo nao localizado",
    "ListaVencimentosProrrogacao": [],
}

# ---------------------------------------------------------------------------
# POST /portais/bff/v1/consulta-unica/financeiro/boleto
# ---------------------------------------------------------------------------
BOLETO_OK = {
    "cAceite": "N",
    "cAgeCtaCeden": "3689/5346541",
    "cCodBco": "0033",
    "cCodigoBarras": "03391156500000343539534654100072317876070101",
    "cDescRetCode": "SOLICITAÇÃO EFETUADA COM SUCESSO",
    "cLinhaDigitavelBl1": "03399.53465",
    "cLinhaDigitavelBl2": "54100.072310",
    "cLinhaDigitavelBl3": "78760.701017",
    "cLinhaDigitavelBl4": "15650000034353",
    "cNomCed": "Tokio Marine Seguradora S.A.",
    "cNome": "CLARISSE BRANDAO MOURA",
    "cNossoNumero": "7200000003",
    "cUrlCSF": "https://portal.tokiomarine.com.br/docstore-services/rest/download/"
               "00000000-0000-4000-8000-000000000001",
}

BOLETO_SEM_URL = {"cDescRetCode": "TITULO JA BAIXADO", "cUrlCSF": ""}

# ---------------------------------------------------------------------------
# POST /portais/bff/v1/consulta-unica/pix/validar
#
# 📊 Resposta real quando existe parcela anterior pendente. Guardada porque o
# PIX é o próximo serviço a nascer aqui, e a regra já está medida.
# ---------------------------------------------------------------------------
PIX_BLOQUEADO = {
    "idecnvcobr": None,
    "mensagem": "Não é possivel realizar o pagamento. Parcela anterior pendente",
    "codigo_mensagem": 5,
    "permite_pagamento_pix": False,
    "valor_atual": None,
    "valor_original": None,
}

# ---------------------------------------------------------------------------
# GraphQL
# ---------------------------------------------------------------------------
USUARIO_JSON = {"data": {"buscarUsuario": {
    "codigoInterno": 99001,
    "codigoParceiroNegocioPrimario": 99001,
    "tipoUsuario": "CORRETOR",
    "nome": "FULANO DE",
    "nomeParceiroNegocioPrimario": "CORRETORA DE EXEMPLO LTDA",
    "__typename": "Usuario"}}}

RAMOS_JSON = {"data": {"buscarRamos": [
    {"codigo": "0", "nome": "RISCOS DIGITAIS", "grupo": "RISCOS DIGITAIS", "__typename": "Ramo"},
    {"codigo": "312", "nome": "AUTOMOVEL", "grupo": "AUTO", "__typename": "Ramo"},
    {"codigo": "531", "nome": "AUTOMOVEL", "grupo": "AUTO", "__typename": "Ramo"},
]}}


def relatorio(venc_atrasada: str, venc_amanha: str, *, truncado: bool = False) -> str:
    """Datas entram no momento do teste — fixture com data fixa envelhece."""
    base = RELATORIO_XML_TRUNCADO if truncado else RELATORIO_XML
    return base.replace("{VENC_ATRASADA}", venc_atrasada).replace("{VENC_AMANHA}", venc_amanha)
