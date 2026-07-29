"""Nenhum crédito é gasto sem alguém ter dito um número. E o RAG não para.

O que aconteceu em 29/07/2026
-----------------------------
O Founder colocou US$ 6 e clicou em "Processar aprendizado". A estimativa era
de US$ 1. Sumiu tudo em uma rodada.

A estimativa não estava errada por pouco — estava errada de premissa. O botão
não processa "um lote": ele processa **até a fila secar ou o crédito acabar**.
Com 6.118 conversas na fila, o teto real era o saldo do cartão.

A trava
-------
`DESTILADOR_TETO_POR_RODADA` é o número máximo de conversas que UMA rodada pode
ler. Em 0, nenhuma chamada de modelo acontece — nem estágio 1, nem playbook,
que é a chamada mais cara do sistema.

O botão e o agendador chamam a MESMA `distill_once`. A trava mora lá dentro, e
não no botão: uma trava que só existe na tela é uma trava que o agendador
atravessa às três da manhã.

O que a trava NÃO pode travar
-----------------------------
Curar e publicar. Nenhuma das duas chama modelo de linguagem — só o embedding,
que custa centavos — e são exatamente o caminho por onde as cartas escritas
pelos subagentes do plano Max chegam ao RAG.

Se a trava desligasse a publicação junto, o efeito seria o pior possível: o
conhecimento seria produzido de graça, ficaria parado no banco, e ninguém
saberia por quê. É por isso que este teste existe.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.core", ("app", "core"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m
_banco = types.ModuleType("app.core.database")
_banco.get_supabase_client = lambda: None
sys.modules["app.core.database"] = _banco

_spec = importlib.util.spec_from_file_location(
    "app.services.attendance_distiller",
    os.path.join(RAIZ, "app", "services", "attendance_distiller.py"))
DIST = importlib.util.module_from_spec(_spec)
sys.modules["app.services.attendance_distiller"] = DIST
_spec.loader.exec_module(DIST)

FONTE = inspect.getsource(DIST.distill_once)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _trecho(de: str, ate: str) -> str:
    i = FONTE.find(de)
    j = FONTE.find(ate, i + 1) if i >= 0 else -1
    return FONTE[i:j] if i >= 0 and j > i else ""


def teste_o_teto_e_zero_por_padrao():
    print("\n[1] Sem ninguém dizer um número, o gasto é zero")
    checar("_teto_de_gasto()" in FONTE,
           "o teto existe e tem leitor próprio",
           "`_env_int` faz max(1,...) e transformaria teto 0 em 1 conversa "
           "MAIS um playbook no modelo caro, toda rodada")
    for bruto in (None, "", "abc", "0", "-5", " 0 "):
        if bruto is None:
            os.environ.pop("DESTILADOR_TETO_POR_RODADA", None)
        else:
            os.environ["DESTILADOR_TETO_POR_RODADA"] = bruto
        checar(DIST._teto_de_gasto() == 0,
               f"valor {bruto!r} resulta em teto travado",
               f"devolveu {DIST._teto_de_gasto()}")
    os.environ.pop("DESTILADOR_TETO_POR_RODADA", None)


def teste_o_teto_corta_as_duas_chamadas_de_modelo():
    print("\n[2] O teto corta as DUAS etapas que chamam modelo")
    checar("min(teto," in _trecho("max_sessions = ", "min_group"),
           "estágio 1 (ler conversas) é limitado pelo teto")
    checar("min(teto," in _trecho("por_rodada = ", "grupos = "),
           "estágio 2 (playbook, o mais caro) também",
           "sem isto, teto 0 ainda sintetizaria playbooks no modelo forte")
    checar("if max_sessions > 0 else []" in FONTE,
           "com teto 0 a fila nem é lida")


def teste_a_trava_mora_no_motor_e_nao_no_botao():
    print("\n[3] A trava mora na função, não na tela")
    # O agendador não passa pelo botão. Uma trava só na rota seria atravessada
    # pela rodada automática sem ninguém ver.
    rota = os.path.join(RAIZ, "app", "api", "admin_atlas.py")
    with open(rota, encoding="utf-8") as fh:
        fonte_rota = fh.read()
    checar("DESTILADOR_TETO_POR_RODADA" in FONTE,
           "`distill_once` conhece o teto — é por onde o agendador passa")
    checar("teto" in fonte_rota and "TRAVADA" in fonte_rota,
           "e a tela informa o estado, em vez de prometer o que não vai fazer")


def teste_publicar_no_rag_continua_funcionando():
    print("\n[4] Travar o gasto NÃO pode travar o conhecimento")
    # Com a destilação externa, fila vazia passou a ser o caso normal. O
    # `return` antecipado abortava a rodada e as cartas ficavam sem publicar.
    checar("if not sessions:\n        return stats" not in FONTE,
           "fila vazia não aborta mais a rodada",
           "era o `return` que impedia a publicação das cartas escritas por fora")
    i = FONTE.find("teto = _teto_de_gasto()")
    checar(i >= 0, "a rodada lê o teto pelo leitor próprio")
    depois = FONTE[i:] if i >= 0 else ""
    checar("publicar_lote_sync" in depois,
           "publicar acontece DEPOIS da trava, e não é cortado por ela")
    checar("curar_sync" in depois, "curar também")
    # Nenhuma das duas pode estar dentro de um `if teto`.
    i = FONTE.find("curar_sync")
    linha = FONTE[FONTE.rfind("\n", 0, i):i]
    checar("teto" not in linha, "a curadoria não está condicionada ao teto")


def main() -> int:
    print("=" * 70)
    print("NENHUM CRÉDITO SEM AUTORIZAÇÃO — E O RAG NÃO PARA")
    print("=" * 70)
    for teste in (teste_o_teto_e_zero_por_padrao,
                  teste_o_teto_corta_as_duas_chamadas_de_modelo,
                  teste_a_trava_mora_no_motor_e_nao_no_botao,
                  teste_publicar_no_rag_continua_funcionando):
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
    print("O GASTO EXIGE UM NÚMERO; A PUBLICAÇÃO NÃO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
