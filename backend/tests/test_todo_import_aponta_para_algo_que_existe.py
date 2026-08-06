"""Todo import aponta para algo que existe.

A HISTÓRIA — 06/08/2026, e custou o dia inteiro do Founder
==========================================================
A ponte do espelho fazia:

    from app.services.integration_service import integration_service

Aquele nome **não existe**. O módulo exporta a fábrica
`get_integration_service(client)`. O resultado, medido no Redis de produção:

    espelho_contadores: {"erro:ImportError": 2255}

2.255 tentativas, todas mortas no import — e o `/health` dizendo
`espelho_no_chat: true`, porque a função EXISTIA; ela só nunca corria. A
corretora via uma tela vazia e eu via um sinal verde.

POR QUE OS TESTES NÃO PEGARAM
=============================
Porque eu havia **dublado** o módulo:

    falso.integration_service = _Servico()      # o nome que eu IMAGINEI

O dublê tinha a forma da minha suposição. Todo teste ficou verde contra uma
API que não existe. **Um dublê valida o que você acha, não o que está lá.**

O QUE ESTE ARQUIVO FAZ
======================
Lê o código de verdade — sem importar nada, sem rede, sem banco — e confere que
cada `from X import Y` aponta para um `Y` que realmente existe em `X`. É a
classe inteira de erro, não o caso de ontem.

📊 Na primeira execução ele encontrou, além do defeito do espelho, mais três em
produção que ninguém sabia (ver `PENDENCIAS.md` P-121).
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(RAIZ, "backend", "app")
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _nomes_do_modulo(arvore: ast.Module) -> set:
    """O que um `from modulo import X` consegue alcançar.

    Só o NÍVEL DE MÓDULO: função, classe, atribuição e o que o próprio módulo
    importa (reexportação é uso legítimo). Nome definido dentro de função não
    entra — e é justamente essa a distinção que o defeito de 06/08 explorou.
    """
    nomes = set()
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nomes.add(no.name)
        elif isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name):
                    nomes.add(alvo.id)
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            nomes.add(no.target.id)
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            for a in no.names:
                nomes.add(a.asname or a.name.split(".")[0])
        elif isinstance(no, (ast.If, ast.Try)):
            # `try: import X except: ...` e `if TYPE_CHECKING:` também exportam.
            for filho in ast.walk(no):
                if isinstance(filho, (ast.Import, ast.ImportFrom)):
                    for a in filho.names:
                        nomes.add(a.asname or a.name.split(".")[0])
                elif isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    nomes.add(filho.name)
                elif isinstance(filho, ast.Assign):
                    for alvo in filho.targets:
                        if isinstance(alvo, ast.Name):
                            nomes.add(alvo.id)
    return nomes


def _mapear() -> tuple:
    """(exportados por módulo, conjunto de pacotes). Sem importar nada."""
    exportados, pacotes = {}, set()
    for base, _, arquivos in os.walk(BASE):
        for nome in arquivos:
            if not nome.endswith(".py"):
                continue
            caminho = os.path.join(base, nome)
            relativo = os.path.relpath(caminho, os.path.join(RAIZ, "backend"))
            modulo = relativo[:-3].replace(os.sep, ".")
            if modulo.endswith(".__init__"):
                modulo = modulo[: -len(".__init__")]
                pacotes.add(modulo)
            try:
                arvore = ast.parse(open(caminho, encoding="utf-8").read())
            except SyntaxError:
                continue
            exportados[modulo] = _nomes_do_modulo(arvore)
    return exportados, pacotes


def teste_nenhum_import_aponta_para_o_vazio():
    print("\n[1] Todo `from X import Y` tem um Y de verdade")
    exportados, pacotes = _mapear()
    checar(len(exportados) > 200,
           "o mapa cobre o backend inteiro", f"{len(exportados)} módulos")

    quebrados = []
    for base, _, arquivos in os.walk(BASE):
        for nome in arquivos:
            if not nome.endswith(".py"):
                continue
            caminho = os.path.join(base, nome)
            try:
                arvore = ast.parse(open(caminho, encoding="utf-8").read())
            except SyntaxError:
                continue
            for no in ast.walk(arvore):
                if not isinstance(no, ast.ImportFrom) or no.level:
                    continue
                alvo = no.module or ""
                if alvo not in exportados:
                    continue  # módulo de fora do projeto: não é assunto daqui
                for a in no.names:
                    if a.name == "*":
                        continue
                    if a.name in exportados[alvo]:
                        continue
                    # `from pacote import submodulo` é válido e não aparece
                    # como nome no `__init__`.
                    if alvo in pacotes and f"{alvo}.{a.name}" in exportados:
                        continue
                    rel = os.path.relpath(caminho, RAIZ)
                    quebrados.append(f"{rel}:{no.lineno} — from {alvo} import {a.name}")

    checar(not quebrados,
           "nenhum import aponta para nome inexistente",
           f"{len(quebrados)} quebrado(s)")
    for q in quebrados:
        print(f"       ↳ {q}")


def teste_o_guarda_consegue_reprovar():
    print("\n[2] CONTROLE — e ele pega o defeito real de 06/08/2026")
    # Reproduz o caso exato: um módulo que exporta a FÁBRICA e um import que
    # pede o objeto. Se este bloco passasse, o guarda acima seria decoração.
    modulo = ast.parse(
        "def get_integration_service(c=None):\n    return None\n"
        "_integration_service = None\n")
    nomes = _nomes_do_modulo(modulo)

    checar("get_integration_service" in nomes,
           "a fábrica é vista como exportada")
    checar("integration_service" not in nomes,
           "CONTROLE — e o objeto que NÃO existe não é inventado",
           "era este nome que a ponte importava, 2.255 vezes por nada")

    # E um nome definido DENTRO de função não conta como exportado — foi essa
    # distinção que o defeito explorou.
    dentro = ast.parse("def f():\n    escondido = 1\n    return escondido\n")
    checar("escondido" not in _nomes_do_modulo(dentro),
           "CONTROLE — nome de dentro de função não é importável")


def main() -> int:
    print("=" * 70)
    print("TODO IMPORT APONTA PARA ALGO QUE EXISTE")
    print("=" * 70)
    teste_nenhum_import_aponta_para_o_vazio()
    teste_o_guarda_consegue_reprovar()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — nenhum import morre em silêncio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
