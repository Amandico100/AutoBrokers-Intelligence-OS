"""Conhecimento novo desafia conhecimento velho — ou o RAG afirma os dois.

A HISTÓRIA
==========
📊 07/08/2026, cartas sobre boleto da Porto, TODAS `published` ao mesmo tempo:

    28–29/07  "Porto Seguro emite boleto ATUALIZADO quando há parcela em
               aberto, com novo prazo de vencimento"
    28–29/07  "Na Porto é possível gerar boleto atualizado para parcela vencida"
    ────────────────────────────────────────────────────────────────────────
    30/07     "Na Porto o boleto NÃO É MAIS atualizado: ele continua com o
               vencimento original"
    30/07     "A Porto DEIXOU DE atualizar boleto"

**Cinco afirmavam, três negavam, zero foram aposentadas.** O agente respondia
uma ou outra por sorte da busca.

E dizer a um segurado *"peça o boleto atualizado"* quando a Porto deixou de
emitir faz ele esperar, o prazo passar e **a apólice cancelar**. O dano não é
uma resposta feia: é um cliente sem seguro.

A CAUSA ERA ESTRUTURAL, NÃO DE NENHUMA CARTA
============================================
`escolher_representantes` compara a carta nova com as outras cartas novas do
mesmo lote. **Conhecimento novo nunca desafiava conhecimento velho.** O código
já documentava este caso exato como motivo de existir `despublicar_carta_sync`
— a função foi escrita, e nunca foi chamada, porque só rodava por clique.

O QUE ESTE ARQUIVO GUARDA
=========================
Que a carta nova é comparada com o ACERVO, que a velha sai do índice com o
ponteiro para quem a substituiu — e, principalmente, **que carta boa não é
aposentada por engano**. Aposentar demais é pior que aposentar de menos: o
primeiro apaga conhecimento em silêncio.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _carregar_curadoria():
    """Carrega `curadoria_cartas` sem o pacote (que puxa `openai`).

    O módulo é PURO — logging, re, unicodedata, typing. Carrega direto, e é ele
    que define `tem_negacao`: a polaridade mora aqui e `memory_fabric` importa
    daqui, não o contrário. A dependência aponta para o lado leve de propósito,
    e isso foi descoberto quebrando o teste do destilador ao fazer o inverso.
    """
    nome = "_teste_curadoria"
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, "backend", "app", "services", "curadoria_cartas.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _carta(cid: str, texto: str, seg=None, cat="cobranca") -> dict:
    return {"id": cid, "card_text": texto, "insurer_key": seg,
            "category": cat, "ramo": "auto"}


# 📊 Os textos REAIS que estão publicados no acervo hoje (07/08/2026).
AFIRMA_1 = ("Porto Seguro emite boleto atualizado quando há parcela em aberto, "
            "com novo prazo de vencimento")
AFIRMA_2 = ("Na Porto é possível gerar boleto atualizado para parcela vencida, "
            "com nova data de vencimento, sem depender de reprogramação formal "
            "da parcela.")
NEGA_1 = ("Na Porto o boleto nao e mais atualizado: ele continua com o "
          "vencimento original e, conforme as instrucoes impressas no proprio "
          "documento, ha cerca de 55 dias para pagar")
NEGA_2 = ("A Porto deixou de atualizar boleto: a parcela em aberto é paga no "
          "mesmo boleto original em até 55 dias após o vencimento, e o banco "
          "calcula juros e multa")


# ---------------------------------------------------------------------------
def teste_o_caso_real_da_porto():
    print("\n[1] O caso que motivou tudo — a Porto e o boleto")
    C = _carregar_curadoria()

    publicadas = [_carta("velha-1", AFIRMA_1, "porto"),
                  _carta("velha-2", AFIRMA_2, "porto")]
    novas = [_carta("nova-1", NEGA_1, "porto")]

    pares = C.achar_contradicoes(novas, publicadas)
    aposentadas = {a for a, _n in pares}

    checar(len(pares) >= 1,
           "a carta que NEGA aposenta a que AFIRMA",
           f"{len(pares)} par(es): {sorted(aposentadas)}")
    checar(all(n == "nova-1" for _a, n in pares),
           "e quem substitui é a mais nova — a seguradora mudou a regra")


def teste_nao_aposenta_carta_boa():
    print("\n[2] CONTROLE — o que NÃO pode ser aposentado")
    C = _carregar_curadoria()

    # Mesma polaridade: duas cartas que afirmam a mesma coisa não se
    # contradizem. No máximo são quase-cópias — e isso é outro tratamento.
    checar(not C.achar_contradicoes([_carta("n", AFIRMA_2, "porto")],
                                    [_carta("v", AFIRMA_1, "porto")]),
           "CONTROLE — duas cartas que AFIRMAM não se aposentam",
           "seria consolidação, não contradição")

    # Seguradora diferente: a regra da Porto não aposenta a da HDI. Este é o
    # falso positivo mais caro possível — apagaria conhecimento correto de
    # outra companhia.
    checar(not C.achar_contradicoes([_carta("n", NEGA_1, "hdi")],
                                    [_carta("v", AFIRMA_1, "porto")]),
           "CONTROLE — regra da HDI não aposenta regra da Porto",
           "cada companhia responde pela sua")

    # Categoria diferente: cobrança não aposenta sinistro, mesmo na mesma
    # companhia e com as mesmas palavras.
    checar(not C.achar_contradicoes(
        [_carta("n", NEGA_1, "porto", cat="sinistro")],
        [_carta("v", AFIRMA_1, "porto", cat="cobranca")]),
           "CONTROLE — cobrança não aposenta sinistro")

    # Assunto diferente na mesma seguradora e categoria: negar uma coisa não
    # aposenta a afirmação sobre outra.
    outro = ("Na Porto o débito automático não é autorizado quando a conta "
             "está sem saldo na data")
    checar(not C.achar_contradicoes([_carta("n", outro, "porto")],
                                    [_carta("v", AFIRMA_1, "porto")]),
           "CONTROLE — assunto diferente não aposenta",
           "há negação, mas as cartas não falam da mesma coisa")

    # Carta curta demais não aposenta nada: pouca palavra, muita coincidência.
    checar(not C.achar_contradicoes([_carta("n", "Não.", "porto")],
                                    [_carta("v", AFIRMA_1, "porto")]),
           "CONTROLE — carta curta demais não derruba ninguém")


def teste_uma_velha_nao_e_aposentada_duas_vezes():
    print("\n[3] Cada carta velha é aposentada por UMA nova")
    C = _carregar_curadoria()

    pares = C.achar_contradicoes(
        [_carta("nova-1", NEGA_1, "porto"), _carta("nova-2", NEGA_2, "porto")],
        [_carta("velha-1", AFIRMA_1, "porto")])
    aposentadas = [a for a, _n in pares]
    checar(len(aposentadas) == len(set(aposentadas)),
           "nenhuma velha aparece duas vezes na lista",
           "aposentar duas vezes gravaria dois substitutos e o histórico mentiria")


def teste_a_curadoria_le_o_acervo_e_anota_quem_substituiu():
    print("\n[4] A curadoria olha o acervo, e a saída deixa rastro")
    caminho = os.path.join(RAIZ, "backend", "app", "services", "curadoria_cartas.py")
    with open(caminho, encoding="utf-8") as arquivo:
        fonte = arquivo.read()
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("_acervo_publicado_sync(db)" in cmd and "achar_contradicoes(" in cmd,
           "`curar_sync` compara com as cartas PUBLICADAS",
           "antes comparava só com as outras do mesmo lote")
    checar('.eq("status", "published")' in cmd and ".range(inicio, inicio + 999)" in cmd,
           "e lê o acervo inteiro, paginado",
           "📊 12.071 publicadas = 13 páginas; sem paginar viriam 1.000")
    checar('"substituida_por"' in cmd,
           "a carta aposentada guarda QUEM a substituiu",
           "aposentadoria que não se explica é igual a apagamento por engano")
    # 🔴 07/08/2026 — ESTA LINHA PROCURAVA A CHAMADA, E A CHAMADA NÃO ERA O PONTO.
    #
    # Ela exigia o texto `despublicar_carta_sync(id_antiga)`. Ele estava lá — e
    # o defeito também: o retorno era **descartado**, e a função devolvia `True`
    # com o Qdrant fora do ar. O guarda via a chamada acontecer e não via que
    # ninguém escutava a resposta.
    #
    # O que importa não é chamar: é conferir. E a ordem, que era metade do
    # defeito — o banco era marcado ANTES, então uma recusa do índice deixava
    # exatamente o estado que esta linha existia para impedir.
    checar("if not despublicar_carta_sync(" in cmd,
           "e ela sai do ÍNDICE antes de o banco mudar — com o retorno conferido",
           "status mudado sem vetor apagado = auditoria vê removida e a busca entrega")
    checar('"status": "superseded"' not in cmd,
           "CONTROLE — e a aposentadoria não grava o status por conta própria",
           "quem grava é o removedor, DEPOIS de o vetor sair")
    checar('"contraditas_aposentadas"' in cmd,
           "o resultado da rodada diz quantas foram aposentadas")

    # CONTROLE — a falha de uma não pode derrubar as outras.
    checar("except Exception as erro:" in fonte and "[CURADORIA] não consegui aposentar" in fonte,
           "CONTROLE — uma que falha não impede as demais",
           "cada carta contradita ainda publicada é uma resposta errada")


def main() -> int:
    print("=" * 70)
    print("A CARTA NOVA DESAFIA O ACERVO")
    print("=" * 70)
    teste_o_caso_real_da_porto()
    teste_nao_aposenta_carta_boa()
    teste_uma_velha_nao_e_aposentada_duas_vezes()
    teste_a_curadoria_le_o_acervo_e_anota_quem_substituiu()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — a regra que mudou aposenta a que valia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
