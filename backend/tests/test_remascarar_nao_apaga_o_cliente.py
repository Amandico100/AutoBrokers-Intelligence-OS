"""Consertar vazamento não pode apagar conhecimento. SPEC-040/052.

O erro
------
Em 29/07/2026 os subagentes acharam dez vetores de vazamento de PII em um dia.
A cada conserto eu reaplicava o mascarador corrigido nos lotes que ainda não
tinham sido destilados — rodando `templatize` sobre o transcript **inteiro**.

`cliente` está na lista de rótulos do `_LABELED_VALUE`, e a regra é ancorada em
início de linha. Então:

    CLIENTE: bom dia, meu vidro trincou ontem no estacionamento
    → CLIENTE: {VALOR}

Toda fala do segurado virou `{VALOR}`. Três vezes. Quem percebeu foi um
subagente destilando o lote 013:

> "a mascaração de origem colapsa quase toda fala do CLIENTE em {VALOR}, o que
>  impede reconstruir `perguntas_na_ordem` e derruba o teto de fatos
>  extraíveis"

Eu estava consertando vazamento e apagando conhecimento no mesmo gesto — e o
resultado ainda parecia certo, porque um transcript mascarado demais continua
sendo um transcript válido. 278 sessões voltaram para a fila e os lotes foram
reexportados do banco.

A regra
-------
`templatize` foi desenhado para ver UMA mensagem por vez. Reaplicá-lo num
transcript montado é sempre errado. `remascarar` desmonta a linha, mascara só o
texto da mensagem e remonta — e por isso é idempotente.

Este teste existe porque o defeito é invisível: nenhum erro, nenhum alarme, só
conhecimento que silenciosamente deixa de existir.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

_spec = importlib.util.spec_from_file_location(
    "mascarar", os.path.join(RAIZ, "scripts", "destilacao_max", "mascarar.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

CONVERSA = (
    "CLIENTE: bom dia, meu vidro trincou ontem no estacionamento\n"
    "ATENDENTE: bom dia! a trinca é maior que uma moeda de 1 real?\n"
    "CLIENTE: é menorzinha, do tamanho de uma unha\n"
    "ATENDENTE: então dá reparo, sem franquia\n"
    "CLIENTE: meu cartão é 4111 1111 1111 1111\n"
    "CLIENTE: segue banco 341 agencia 1234 conta 56789-0\n"
)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def teste_a_armadilha_existe_e_e_real():
    print("\n[1] `templatize` no transcript inteiro APAGA o cliente")
    # Documenta o perigo. Se um dia isto parar de acontecer, ótimo — mas o
    # teste de baixo é que garante o comportamento que importa.
    direto = M.templatize(CONVERSA)
    checar("CLIENTE: {VALOR}" in direto,
           "reaplicar direto colapsa a fala do segurado (é a armadilha)",
           "se mudou, reveja `_LABELED_VALUE` antes de relaxar este arquivo")


def teste_o_remascarar_preserva_a_fala():
    print("\n[2] `remascarar` mantém o que o segurado disse")
    saida = M.remascarar(CONVERSA)
    checar("meu vidro trincou ontem" in saida,
           "a fala do segurado sobrevive inteira")
    checar("do tamanho de uma unha" in saida,
           "inclusive a resposta que decide reparo x troca")
    checar("CLIENTE: {VALOR}" not in saida,
           "nenhuma linha do cliente vira {VALOR}",
           "é o defeito que devolveu 278 sessões para a fila")
    checar("a trinca é maior que uma moeda" in saida,
           "e a pergunta da atendente também — é dela que sai o playbook")


def teste_o_remascarar_ainda_mascara():
    print("\n[3] E continua sendo um portão de PII")
    saida = M.remascarar(CONVERSA)
    checar("4111 1111 1111 1111" not in saida, "o cartão é mascarado")
    checar("{CARTAO}" in saida, "com o rótulo certo")
    checar("56789-0" not in saida, "a conta bancária é mascarada")
    checar("341" not in saida.replace("{VALOR}", ""), "o banco também")


def teste_e_idempotente():
    print("\n[4] Rodar duas vezes dá o mesmo resultado")
    # A cada conserto de PII o mascarador é reaplicado nos lotes pendentes.
    # Se não fosse idempotente, cada passada comeria um pouco mais.
    uma = M.remascarar(CONVERSA)
    duas = M.remascarar(uma)
    checar(uma == duas, "duas passadas não comem nada a mais",
           "não idempotente: cada conserto de PII apagaria mais conhecimento")


def main() -> int:
    print("=" * 70)
    print("CONSERTAR VAZAMENTO NÃO PODE APAGAR CONHECIMENTO")
    print("=" * 70)
    for teste in (teste_a_armadilha_existe_e_e_real,
                  teste_o_remascarar_preserva_a_fala,
                  teste_o_remascarar_ainda_mascara,
                  teste_e_idempotente):
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
    print("O PORTÃO PROTEGE O DADO E DEIXA O CONHECIMENTO PASSAR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
