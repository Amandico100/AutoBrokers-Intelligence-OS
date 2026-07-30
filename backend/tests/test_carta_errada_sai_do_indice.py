"""Despublicar tem de chegar ao índice, e não só ao banco. SPEC-052.

O defeito real, encontrado em 30/07/2026
----------------------------------------
Três cartas afirmavam percentual de franquia como se fosse fixo — e duas delas
discordavam entre si sobre a MESMA cobertura: 20% numa, 15% na outra. A
discordância é a prova de que o número é da apólice, não da cobertura.

Ao corrigi-las, o script marcou `superseded` no banco e a remoção do Qdrant
falhou (rodava fora do servidor, sem a credencial do índice). Resultado: o banco
dizia "removida" e a busca continuava entregando o texto errado. É o pior estado
possível, porque a auditoria fica limpa e o agente continua errando.

Fingir sucesso é o defeito. Marcar a pendência é a correção:

    banco diz removida  +  índice ainda responde  =  mentira silenciosa
    banco diz removida  +  marca `qdrant_pendente` =  trabalho pendente

Este arquivo prova as duas garantias que impedem a mentira voltar:

1. A reconciliação existe, procura pela marca certa, e só apaga a marca quando
   o ponto sai de verdade.
2. Publicar reconcilia ANTES de publicar — carta errada que fica no índice
   responde junto com a certa que a substitui, e a busca não sabe qual é qual.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m

_spec = importlib.util.spec_from_file_location(
    "app.services.curadoria_cartas",
    os.path.join(RAIZ, "app", "services", "curadoria_cartas.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _fonte(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def teste_a_reconciliacao_existe_e_procura_a_marca_certa():
    print("\n[1] A reconciliação procura quem ficou para trás")
    checar(hasattr(C, "reconciliar_indice_sync"),
           "`reconciliar_indice_sync` existe")

    src = _fonte("app", "services", "curadoria_cartas.py")
    corpo = src[src.find("def reconciliar_indice_sync"):]
    corpo = corpo[:corpo.find("\ndef ", 10)]

    checar("qdrant_pendente" in corpo,
           "filtra pela marca `qdrant_pendente`")
    checar("despublicar_carta_sync" in corpo,
           "usa o removedor que já existe — não abre um caminho paralelo")
    # A marca só pode sair quando o ponto saiu. Se `pop` estivesse fora do
    # `if`, uma falha de rede apagaria a pendência e a carta errada ficaria
    # no índice para sempre, agora sem ninguém sabendo.
    depois_do_if = corpo[corpo.find("if despublicar_carta_sync"):]
    checar("pop(\"qdrant_pendente\"" in depois_do_if or
           "pop('qdrant_pendente'" in depois_do_if,
           "a marca só sai depois que o ponto saiu")


def teste_publicar_reconcilia_antes():
    print("\n[2] A carta velha sai antes de a nova entrar")
    src = _fonte("app", "services", "curadoria_cartas.py")
    corpo = src[src.find("def publicar_lote_sync"):]
    corpo = corpo[:corpo.find("\ndef ", 10)]

    chama = corpo.find("reconciliar_indice_sync()")
    publica = corpo.find("publish_card_sync(c)")
    checar(chama != -1, "publicar_lote_sync chama a reconciliação")
    checar(chama != -1 and publica != -1 and chama < publica,
           "reconcilia ANTES de publicar",
           "a errada tem de sair antes de a certa entrar, senão as duas respondem")
    checar("indice_reconciliado" in corpo,
           "devolve quantos pontos saíram — rodada silenciosa esconde falha")


def teste_o_script_de_correcao_marca_quando_nao_consegue():
    print("\n[3] Quem não conseguiu remover, avisa")
    src = _fonte("scripts", "destilacao_max", "corrigir.py")

    checar("qdrant_pendente" in src,
           "o script grava a marca quando o Qdrant não responde")
    # O ponto central: a marca tem de ser gravada no MESMO update que muda o
    # status. Dois updates separados podem deixar o status mudado e a marca não.
    bloco = src[src.find("pendente = True"):src.find("trocadas += 1")]
    checar("status" in bloco and "qdrant_pendente" in bloco
           and bloco.count(".update(") == 1,
           "status e marca vão no mesmo update",
           "separados, uma falha entre os dois recria o defeito")
    checar(re.search(r"pendente\s*=\s*not\s+despublicar_carta_sync", src) is not None,
           "sucesso do removedor decide a marca — não o fato de não ter dado erro",
           "`despublicar_carta_sync` devolve False sem levantar exceção")


def teste_a_carta_corrigida_ensina_a_verificar():
    print("\n[4] A correção não troca um número errado por outro")
    # Lido com `ast` e não com regex: os textos são literais adjacentes
    # quebrados em várias linhas, e o Python os concatena. Uma regex por aspas
    # vê seis pedaços onde existem três frases — e mediria a frase errada.
    import ast

    arvore = ast.parse(_fonte("scripts", "destilacao_max", "corrigir.py"))
    novos: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(
                getattr(a, "id", "") == "TROCAS" for a in no.targets):
            for par in no.value.values:          # (motivo, texto novo)
                texto = par.elts[1]
                if isinstance(texto, ast.Constant) and isinstance(texto.value, str):
                    novos.append(texto.value)

    checar(len(novos) >= 3, f"há textos de substituição ({len(novos)})")
    com_numero = [t for t in novos if re.search(r"\d{1,3}\s*%|R\$\s*\d|\d+\s*mil litros", t)]
    checar(not com_numero, "nenhum texto novo fixa percentual ou valor",
           f"ainda fixam: {com_numero[:1]}")
    ensinam = [t for t in novos
               if re.search(r"(confirm|verific|consult|da apolice|varia|muda de apolice)", t)]
    checar(len(ensinam) == len(novos),
           "todos os textos novos mandam verificar na apólice",
           f"{len(novos) - len(ensinam)} não mandam")


if __name__ == "__main__":
    print("=" * 66)
    print("CARTA ERRADA SAI DO ÍNDICE, NÃO SÓ DO BANCO")
    print("=" * 66)
    teste_a_reconciliacao_existe_e_procura_a_marca_certa()
    teste_publicar_reconcilia_antes()
    teste_o_script_de_correcao_marca_quando_nao_consegue()
    teste_a_carta_corrigida_ensina_a_verificar()
    print("\n" + "=" * 66)
    if FALHAS:
        print(f"FALHOU ({len(FALHAS)})")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TUDO VERDE")
