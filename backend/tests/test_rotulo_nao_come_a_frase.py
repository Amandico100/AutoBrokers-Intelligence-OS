"""O rótulo de formulário não pode engolir uma frase de conhecimento.

O defeito
---------
`_LABELED_VALUE` mascara "Rótulo: valor" — "Placa: QJQ0A91" vira
"Placa: {VALOR}". Mas os dois-pontos eram OPCIONAIS e o valor era `(.+)$`,
guloso até o fim da linha. Resultado:

    templatize("Boleto de seguro não pago até a data limite leva ao
                cancelamento da apólice")
    → "Boleto {VALOR}"

`_card_pii_clean` reprova todo texto que o templatize mudaria. Então **qualquer
carta que começasse por boleto, sinistro, apólice, protocolo, atendimento,
nome, cliente, contrato ou pedido era marcada como PII e nunca chegava ao
RAG** — sem erro, sem alarme, sem ninguém saber que faltava.

Medido em 29/07/2026, com dado real: das 306 cartas barradas por PII, **51
(17%) eram conhecimento legítimo**, nenhuma com dado de pessoa. Era o pior
conhecimento para se perder: "boleto" e "sinistro" são os assuntos que o
segurado mais pergunta.

A regra agora
-------------
Com dois-pontos, é rótulo de formulário e o valor é do cliente — mascara.
Sem dois-pontos, só mascara se o valor PARECER valor: começa com dígito
("Assistência 8923467") ou é código/nome em caixa alta ("Placa QJQ0A91").
Prosa em minúscula é frase, não campo.

Este teste anda nas duas direções de propósito. Um mascarador que só é testado
contra vazamento fica cada vez mais guloso a cada correção, e o custo aparece
onde ninguém olha: no conhecimento que silenciosamente não existe.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m

_spec = importlib.util.spec_from_file_location(
    "app.services.atlas.templater",
    os.path.join(RAIZ, "app", "services", "atlas", "templater.py"))
_T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_T)
templatize = _T.templatize


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# Frases reais de carta de conhecimento, todas começando por um rótulo.
CONHECIMENTO = [
    "Boleto de seguro não pago até a data limite leva ao cancelamento da apólice",
    "Sinistro de vidros não gera perda de bônus na renovação",
    "Apólice cancelada por falta de pagamento pode ser reativada em 30 dias",
    "Protocolo de atendimento é informado ao segurado ao final da ligação",
    "Atendimento de guincho cobre até 200 km da residência do segurado",
    "Cliente sem habilitação pode apresentar declaração da família no sinistro",
    "Contrato de seguro residencial cobre danos elétricos mediante laudo",
    "Parcelas no cartão são lançadas mês a mês, e não como compra parcelada",
    # Achadas por um subagente destilando o lote 002 em 29/07/2026: a palavra
    # depois de "protocolo" era engolida mesmo sendo prosa.
    "O protocolo aberto na seguradora deve ser informado ao segurado",
    "Protocolo de atendimento é gerado automaticamente pela central",
    "O chassi precisa constar no documento enviado para a vistoria",
    # A conta e o banco viraram rotulos: prosa que comeca com eles tem de
    # sobreviver, senao o conserto de PII apaga conhecimento de cobranca.
    "A conta corrente do segurado deve ser informada no formulário",
    "Banco emissor identificado no canto superior esquerdo do boleto",
    "O beneficiário apresenta documento de identidade na retirada do reserva",
]

# Rótulos de verdade, de tela de comprovante — estes TÊM de ser mascarados.
DADOS_DE_CLIENTE = [
    "Placa: QJQ0A91",
    "Placa QJQ0A91",
    "Nome: João da Silva",
    "Assistência: 8923467",
    "Assistência 8923467",
    "Protocolo 4471902",
    "Telefone: (11) 99999-8888",
    "CPF: 123.456.789-00",
    "Modelo: Gol 1.0",
    "Agendamento: 28/01/2026, entre 10h00 e 12h00",
    "Endereço: Rua das Flores, 100",
    # CARTÃO DE CRÉDITO — o dado mais sensível que aparece numa conversa de
    # corretora, e o mascarador não o via até 29/07/2026. Três subagentes
    # acharam o mesmo buraco em lotes diferentes, no mesmo dia: parceiros e
    # segurados colam número, validade e titular no WhatsApp.
    "4111 1111 1111 1111",
    "5432109876543210",
    "4111-1111-1111-1111",
    "cartão 4111.1111.1111.1111 validade 12/28",
    "validade: 03/2029",
    # AutoFleet, lote 001-002: nome, CPF e dados bancarios completos do
    # beneficiario de um reembolso; CPF dentro do nome de um PDF; placa
    # digitada em minusculas. Agencia e conta nao estavam em lista nenhuma —
    # e sao o que basta para o dinheiro sair para o lugar errado.
    "Agência: 1234",
    "Conta corrente 98765-4",
    "Banco: 341",
    "PIX: joao@email.com",
    "CTPS_12345678900.pdf",
    "abc1d23",
    "ABC1D23",
]


def teste_a_frase_de_conhecimento_sobrevive():
    print("\n[1] Frase que ENSINA não pode virar {VALOR}")
    for frase in CONHECIMENTO:
        saida = templatize(frase)
        checar(saida == frase,
               f"passa: {frase[:46]}…",
               f"virou: {saida}" if saida != frase else "")


def teste_o_dado_do_cliente_continua_barrado():
    print("\n[2] E o dado do cliente continua sendo mascarado")
    for linha in DADOS_DE_CLIENTE:
        saida = templatize(linha)
        checar(saida != linha, f"mascara: {linha[:46]}",
               "passou intacto — vazaria para a LLM" if saida == linha else "")


def teste_cartao_nao_vira_cpf_nem_telefone():
    print("\n[3] O cartão é mascarado INTEIRO, e não em pedaços")
    # A regra de telefone morderia "1111 1111" do meio de um cartão e deixaria
    # os outros oito dígitos expostos. Por isso a regra de cartão vem antes
    # dela — e depois de CPF e CNPJ, que mantêm o rótulo próprio.
    saida = templatize("4111 1111 1111 1111")
    checar(saida.strip() == "{CARTAO}",
           "o número inteiro vira um único {CARTAO}",
           f"virou: {saida!r}")
    checar(templatize("123.456.789-00").strip() == "{CPF}",
           "e o CPF continua sendo {CPF}, não {CARTAO}")
    checar(templatize("12.345.678/0001-90").strip() == "{CNPJ}",
           "e o CNPJ continua sendo {CNPJ}")
    checar("{CEP}" in templatize("CEP 01310-100"),
           "e o CEP não é confundido com cartão")


def teste_a_carta_chega_ao_rag():
    print("\n[3] A consequência real: a carta chega ao RAG")
    # `_card_pii_clean` é exatamente `templatize(t) == t`. Reproduzir a
    # comparação aqui é o ponto do teste: é ela que decide publicar ou barrar.
    barradas = [f for f in CONHECIMENTO if templatize(f) != f]
    checar(not barradas,
           "nenhuma das 8 cartas de conhecimento é barrada por PII",
           f"{len(barradas)} barrada(s): {barradas[:2]}")


def main() -> int:
    print("=" * 70)
    print("O RÓTULO NÃO COME A FRASE — E O DADO DO CLIENTE NÃO ESCAPA")
    print("=" * 70)
    for teste in (teste_a_frase_de_conhecimento_sobrevive,
                  teste_o_dado_do_cliente_continua_barrado,
                  teste_cartao_nao_vira_cpf_nem_telefone,
                  teste_a_carta_chega_ao_rag):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("CONHECIMENTO PASSA; DADO DE PESSOA, NÃO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
