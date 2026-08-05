"""O tratador de erro também é código — e ele roda quando ninguém está olhando.

A HISTÓRIA
----------
📊 Autópsia de 05/08/2026. Vinte e três documentos normativos ficaram presos no
estado `fetching` por **oito dias**, invisíveis, sem alarme nenhum.

A causa não foi o Firecrawl ter ficado sem crédito. Foi o tratador escrito para
lidar com a falta de crédito:

    "last_checked_at": _agora(),                              ← datetime CRU
    "next_check_at": (_agora() + timedelta(hours=6)).isoformat(),
    "updated_at": _agora(),                                   ← datetime CRU

O httpx serializa o corpo com `json.dumps(..., allow_nan=False)` e **sem**
`default=`. Um `datetime` cru estoura `TypeError`. A exceção sobe, escapa de
`ingerir()`, escapa de `reconferir_pendentes()`, e morre num `logger.warning`
que imprime só o **nome** da exceção — sem mensagem, sem id do documento.

O status fica `fetching`. E `vencidos()`, a única função que reencontra trabalho
pendente, procura em `('ingested','discovered','unreachable')`. `fetching` não
está lá.

📊 O tratador nasceu no commit `d20868c`, 25/07 21:25 -03, com a mensagem
*"credito esgotado nao e defeito do documento"*. Os 23 travaram **1h37 depois**.
**O código escrito para impedir o encalhe é o que o causou.**

O QUE ESTE TESTE GUARDA
-----------------------
Não guarda "as linhas 402 e 404 têm isoformat" — isso quebraria ao mover uma
linha. Guarda que **nenhuma gravação de data neste arquivo manda um objeto
`datetime` para o banco**, varrendo a árvore sintática. Vale para a próxima
também.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
`teste_o_defeito_de_antes_realmente_estourava` reconstrói o dicionário exatamente
como estava e prova que ele **estoura** pelo caminho real de serialização. Sem
essa linha, um teste que passa não distingue "o conserto funciona" de "isto
nunca foi problema".
"""
from __future__ import annotations

import ast
import json
import os
import sys
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
ALVO = os.path.abspath(os.path.join(
    AQUI, "..", "app", "services", "knowledge", "insurance_corpus.py"))

FALHAS: list = []


def checar(condicao: bool, descricao: str, porque: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  X     {descricao}")
        if porque:
            print(f"        {porque}")
        FALHAS.append(descricao)


def _serializa_como_o_httpx(corpo: dict) -> None:
    """Exatamente como `httpx._content.encode_json` monta o corpo.

    Sem `default=`. É por isso que um `datetime` cru não passa — e é por isso
    que reproduzir aqui prova alguma coisa: um `json.dumps` frouxo, com
    `default=str`, aceitaria o defeito e o teste passaria mentindo.
    """
    json.dumps(corpo, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


# --------------------------------------------------------------------- #
# [1] CONTROLE — o defeito de antes estourava mesmo?
# --------------------------------------------------------------------- #
def teste_o_defeito_de_antes_realmente_estourava() -> None:
    print("\n[1] CONTROLE: os dois lados conseguem ser diferentes")
    agora = datetime.now(timezone.utc)

    como_estava = {
        "status": "discovered",
        "fetch_error": "credito do Firecrawl esgotado — aguardando plano",
        "last_checked_at": agora,                                    # cru
        "next_check_at": (agora + timedelta(hours=6)).isoformat(),
        "updated_at": agora,                                         # cru
    }
    estourou = False
    try:
        _serializa_como_o_httpx(como_estava)
    except TypeError:
        estourou = True
    checar(estourou, "o dicionário DE ANTES estoura ao ser serializado",
           "se isto passar, o defeito nunca existiu e o teste não guarda nada")

    como_ficou = {**como_estava,
                  "last_checked_at": agora.isoformat(),
                  "updated_at": agora.isoformat()}
    passou = True
    try:
        _serializa_como_o_httpx(como_ficou)
    except TypeError:
        passou = False
    checar(passou, "e o dicionário DE AGORA serializa sem erro")


# --------------------------------------------------------------------- #
# [2] O guarda de verdade — varre o arquivo inteiro
# --------------------------------------------------------------------- #
_CHAVES_DE_DATA = (
    "last_checked_at", "next_check_at", "updated_at", "created_at",
    "superseded_at", "approved_at", "ingested_at", "published_at",
    "fetched_at", "discovered_at",
)


def _valor_e_texto(no: ast.AST) -> bool:
    """O valor gravado vira texto antes de sair daqui?

    Aceita `x.isoformat()`, `str(...)`, texto literal e `None`. Recusa uma
    chamada nua como `_agora()`, que devolve `datetime`.
    """
    if isinstance(no, ast.Constant):
        return no.value is None or isinstance(no.value, str)
    if isinstance(no, ast.Call):
        alvo = no.func
        if isinstance(alvo, ast.Attribute) and alvo.attr == "isoformat":
            return True
        if isinstance(alvo, ast.Name) and alvo.id == "str":
            return True
        return False
    if isinstance(no, ast.JoinedStr):   # f-string
        return True
    if isinstance(no, ast.BoolOp):      # a or b — os dois lados têm de valer
        return all(_valor_e_texto(v) for v in no.values)
    if isinstance(no, ast.IfExp):
        return _valor_e_texto(no.body) and _valor_e_texto(no.orelse)
    return False


def teste_nenhuma_data_vai_crua_para_o_banco() -> None:
    print("\n[2] Nenhuma gravação de data manda `datetime` para o banco")
    with open(ALVO, encoding="utf-8") as fh:
        fonte = fh.read()
    arvore = ast.parse(fonte)

    suspeitas = []
    conferidas = 0
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Dict):
            continue
        for chave, valor in zip(no.keys, no.values):
            if not (isinstance(chave, ast.Constant) and isinstance(chave.value, str)):
                continue
            if chave.value not in _CHAVES_DE_DATA:
                continue
            conferidas += 1
            if not _valor_e_texto(valor):
                suspeitas.append((chave.value, getattr(valor, "lineno", "?")))

    checar(conferidas >= 10,
           f"o varredor encontrou as gravações de data ({conferidas} conferidas)",
           "se este número cair para perto de zero, o varredor parou de varrer "
           "e o teste passa sem olhar nada")
    checar(not suspeitas,
           "nenhuma delas manda objeto de data cru",
           "suspeitas: " + ", ".join(f"`{c}` na linha {l}" for c, l in suspeitas))


# --------------------------------------------------------------------- #
# [3] O varredor consegue enxergar o defeito? (§9.3)
# --------------------------------------------------------------------- #
def teste_o_varredor_consegue_reprovar() -> None:
    print("\n[3] E o varredor reconhece o defeito quando ele existe")
    ruim = ast.parse("d = {'updated_at': _agora(), 'status': 'x'}")
    achou = []
    for no in ast.walk(ruim):
        if isinstance(no, ast.Dict):
            for chave, valor in zip(no.keys, no.values):
                if (isinstance(chave, ast.Constant) and chave.value in _CHAVES_DE_DATA
                        and not _valor_e_texto(valor)):
                    achou.append(chave.value)
    checar(achou == ["updated_at"],
           "um `_agora()` cru é reconhecido como suspeito")

    bom = ast.parse("d = {'updated_at': _agora().isoformat()}")
    falso_positivo = []
    for no in ast.walk(bom):
        if isinstance(no, ast.Dict):
            for chave, valor in zip(no.keys, no.values):
                if (isinstance(chave, ast.Constant) and chave.value in _CHAVES_DE_DATA
                        and not _valor_e_texto(valor)):
                    falso_positivo.append(chave.value)
    checar(not falso_positivo,
           "e um `.isoformat()` NÃO é acusado à toa")


# --------------------------------------------------------------------- #
# [4] O estado transitório precisa ser varrido
# --------------------------------------------------------------------- #
def teste_fetching_nao_pode_ser_orfao_para_sempre() -> None:
    """`ingerir()` marca `fetching` antes da rede. Quem morre ali fica invisível."""
    print("\n[4] O estado transitório é reencontrável")
    with open(ALVO, encoding="utf-8") as fh:
        fonte = fh.read()

    marca_fetching = '"status": "fetching"' in fonte or "'status': 'fetching'" in fonte
    checar(marca_fetching, "o código realmente marca `fetching` antes de ir à rede",
           "se isto mudar, o resto deste teste guarda um fato que não existe mais")

    # `vencidos()` é a ÚNICA função que reencontra trabalho pendente.
    corpo = fonte[fonte.find("def vencidos"):]
    corpo = corpo[:corpo.find("\n    def ", 10)] if "\n    def " in corpo[10:] else corpo[:4000]
    varre_fetching = "fetching" in corpo
    checar(varre_fetching,
           "e `vencidos()` inclui `fetching` na varredura",
           "PENDENTE por decisão: sem isto, um documento que morre entre marcar "
           "e responder fica invisível para sempre. Ver P-98.")


def main() -> int:
    print("=" * 72)
    print("O TRATADOR DE ERRO TAMBEM E CODIGO")
    print("=" * 72)
    for teste in (teste_o_defeito_de_antes_realmente_estourava,
                  teste_nenhuma_data_vai_crua_para_o_banco,
                  teste_o_varredor_consegue_reprovar,
                  teste_fetching_nao_pode_ser_orfao_para_sempre):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"FALHOU — {len(FALHAS)} verificacoes")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("NENHUMA DATA VAI CRUA, E O VARREDOR CONSEGUE REPROVAR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
