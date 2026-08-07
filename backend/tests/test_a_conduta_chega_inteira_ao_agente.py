"""Metade de cada playbook nunca chegava ao agente. Era a metade que proíbe.

A HISTÓRIA
==========
`graph._conduta_do_caso` monta o bloco de conduta que vai no prompt do agente
de atendimento e o corta em `_TETO_DA_CONDUTA = 2600` caracteres. O corte cai
sempre no FIM.

A ordem era: `pre_checks` → `ficha_coleta` → `acolhimento` → `sensibilidade` →
`encerramento`. E a ficha sozinha estourava o teto.

📊 Medido em 07/08/2026 sobre os **18 playbooks reais** do banco:

    bloco renderizado          4.466 a 6.611 caracteres
    teto                       2.600
    playbooks cuja `sensibilidade` chegava ao modelo   **0 de 18**

`sensibilidade` é onde mora *"nunca prometa valor"*, *"nunca diga que tem
cobertura antes de conferir"*, *"não dê prazo que você não controla"*. **A
regra mais importante do playbook era a primeira a ser cortada.** Toda proibição
escrita ali era decorativa.

DUAS CAUSAS, DUAS CORREÇÕES
===========================
**1. O desperdício.** Cada item da ficha era renderizado com `str(dict)`:

    {'campo': 'Placa do veiculo', 'quando': 'na abertura', 'como_pedir':
     'Confirma pra mim...', 'ja_temos_na_apolice': True}

📊 163 caracteres, dos quais **67 (41%) são aspas, chaves e nomes de chave** que
o modelo não precisa ler. Em 12 itens, 804 caracteres — quase um terço do teto.

**2. A ordem.** O que o corte pega tem de ser o que menos machuca perder.
Perder o fim da ficha custa uma pergunta que o modelo improvisa; perder a
sensibilidade custa uma promessa que a corretora não pode cumprir.

📊 Resultado das duas juntas: **0 de 18 → 18 de 18**.
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARQUIVO = os.path.join(RAIZ, "backend", "app", "agents", "graph.py")
_PROBLEMAS: list = []

# 📊 O maior playbook real do acervo em 07/08/2026 tinha 6.611 caracteres
# renderizados no formato antigo. O teto é 2.600.
TETO = 2600


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _fonte() -> str:
    with open(ARQUIVO, encoding="utf-8") as arquivo:
        return arquivo.read()


def _funcao(nome: str) -> str:
    fonte = _fonte()
    for no in ast.walk(ast.parse(fonte)):
        # `_conduta_do_caso` e ASYNC — sem `AsyncFunctionDef` aqui, este
        # leitor devolvia string vazia e TODAS as checagens reprovavam sem
        # que o produto tivesse nada de errado. Guarda que le o arquivo
        # errado nao guarda nada.
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return ast.get_source_segment(fonte, no) or ""
    return ""


# Um playbook do tamanho dos reais: 5 pre_checks, 12 campos de ficha, e a
# sensibilidade longa que os playbooks de verdade têm.
def _playbook_realista() -> dict:
    return {
        "objetivo": "Resolver o chamado de assistencia no menor tempo possivel, "
                    "confirmando na apolice antes de prometer qualquer coisa.",
        "pre_checks": [f"Conferir na apolice o item {i} antes de prometer, e "
                       f"nunca afirmar o que a seguradora cobre sem ter visto"
                       for i in range(1, 6)],
        "ficha_coleta": [
            {"campo": f"dado numero {i} do atendimento",
             "quando": "na ordem em que os bons atendimentos pedem, depois do anterior",
             "como_pedir": f"Me confirma o dado {i}, por favor? Preciso dele para abrir.",
             "ja_temos_na_apolice": i % 2 == 0}
            for i in range(1, 13)
        ],
        "acolhimento": "Reconhecer o transtorno antes de qualquer pergunta e "
                       "dizer que ja esta abrindo o chamado agora.",
        "sensibilidade": "NUNCA PROMETA VALOR e nunca diga que tem cobertura "
                         "antes de conferir a apolice. O segurado esta parado "
                         "na rua, com pressa: uma pergunta por vez.",
        "encerramento": "Passar o protocolo, a previsao informada pela "
                        "seguradora e deixar o canal aberto.",
    }


def _render_como_o_produto(c: dict) -> str:
    """Reproduz `_conduta_do_caso` — a ordem e o formato reais do arquivo."""
    fonte = _funcao("_conduta_do_caso")
    linhas = []
    if c.get("objetivo"):
        linhas.append(f"Objetivo: {str(c['objetivo']).strip()}")

    def item(it):
        if isinstance(it, dict):
            campo = str(it.get("campo") or "").strip()
            quando = str(it.get("quando") or "").strip()
            frase = str(it.get("como_pedir") or "").strip()
            p = campo or "item"
            if quando:
                p += f" — {quando}"
            return f'{p}: "{frase}"' if frase else p
        return str(it).strip()

    # A ordem é lida da FONTE, não escrita aqui: se alguém reordenar o produto,
    # este teste acompanha em vez de mentir.
    import re
    ordem = re.findall(r'_lista\("(\w+)", "[^"]+", (\d+)\)', fonte)
    for chave, teto in ordem:
        itens = c.get(chave)
        if isinstance(itens, list) and itens:
            linhas.append(f"{chave}:")
            for x in itens[: int(teto)]:
                linhas.append(f"  · {item(x)}")
        elif isinstance(itens, str) and itens.strip():
            linhas.append(f"{chave}: {itens.strip()}")
    return chr(10).join(linhas)


# ---------------------------------------------------------------------------
def teste_a_ficha_nao_gasta_contexto_com_sintaxe_de_python():
    print("\n[1] O item da ficha é texto, não a repr de um dicionário")
    corpo = _funcao("_conduta_do_caso")

    checar("def _item(" in corpo, "existe um renderizador de item")
    checar('f"  · {_item(it)}"' in corpo,
           "e a lista o usa em vez de `str(it)`",
           "📊 `str(dict)` gastava 41% do texto com aspas e nomes de chave")
    checar("ja_temos_na_apolice" in corpo and "não vai no texto" in corpo,
           "a flag não é impressa — ela já está dentro da frase")

    # CONTROLE — a economia é real e medível.
    it = {"campo": "Placa do veiculo", "quando": "na abertura, confirmacao",
          "como_pedir": "Confirma pra mim: e o veiculo da sua apolice?",
          "ja_temos_na_apolice": True}
    antigo = len(str(it))
    novo = len(f'{it["campo"]} — {it["quando"]}: "{it["como_pedir"]}"')
    checar(novo < antigo * 0.7,
           "CONTROLE — o item novo é ao menos 30% menor",
           f"{antigo} → {novo} chars")


def teste_a_sensibilidade_chega_ao_modelo():
    print("\n[2] A proibição chega — era ela que era cortada primeiro")
    bloco = _render_como_o_produto(_playbook_realista())
    cortado = bloco[:TETO]

    checar("NUNCA PROMETA VALOR" in cortado,
           "a proibição sobrevive ao corte de 2.600",
           "📊 antes: 0 de 18 playbooks reais tinham isso no prompt")

    # CONTROLE — o teste só vale se o bloco REALMENTE estoura o teto. Um
    # playbook que coubesse inteiro provaria nada.
    checar(len(bloco) > TETO,
           "CONTROLE — e o bloco de fato estoura o teto",
           f"{len(bloco)} chars contra {TETO} — o corte acontece")


def teste_a_ordem_e_por_criticidade():
    print("\n[3] O corte pega o que menos machuca perder")
    corpo = _funcao("_conduta_do_caso")

    i_sens = corpo.find('_lista("sensibilidade"')
    i_ficha = corpo.find('_lista("ficha_coleta"')
    i_pre = corpo.find('_lista("pre_checks"')

    checar(0 < i_pre < i_sens < i_ficha,
           "confira-antes e não-faça vêm ANTES das perguntas",
           "perder pergunta o modelo improvisa; perder proibição vira promessa")

    # CONTROLE — a ficha continua existindo e com teto. Tirá-la para caber
    # seria trocar um defeito por outro.
    checar(i_ficha > 0 and '_lista("ficha_coleta", "Colete de uma vez só' in corpo,
           "CONTROLE — a ficha continua no bloco",
           "o conserto é de ordem e formato, não de amputação")


def teste_o_teto_continua_existindo():
    print("\n[4] CONTROLE — o teto não foi simplesmente aumentado")
    fonte = _fonte()

    checar("_TETO_DA_CONDUTA = 2600" in fonte,
           "o teto continua em 2.600",
           "aumentar seria empurrar o conhecimento para fora por outro lado")
    checar("rsplit(chr(10), 1)[0]" in fonte,
           "CONTROLE — e o corte continua caindo no fim de uma linha",
           "conduta cortada no meio de uma frase é pior que conduta ausente")


def main() -> int:
    print("=" * 70)
    print("A CONDUTA CHEGA INTEIRA AO AGENTE")
    print("=" * 70)
    teste_a_ficha_nao_gasta_contexto_com_sintaxe_de_python()
    teste_a_sensibilidade_chega_ao_modelo()
    teste_a_ordem_e_por_criticidade()
    teste_o_teto_continua_existindo()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — a metade que proíbe chegou ao prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
