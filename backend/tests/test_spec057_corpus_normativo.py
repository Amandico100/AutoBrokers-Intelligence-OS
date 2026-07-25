"""SPEC-057 Bloco H — garantias do corpus normativo.

O que se prova aqui: que o corpus só aceita o que é norma, que ele reconhece a
identidade legal do documento, e que a mesma norma re-lida não vira documento
novo.

    python backend/tests/test_spec057_corpus_normativo.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FALHAS: list[str] = []

for nome in ("app", "app.services", "app.services.knowledge"):
    if nome not in sys.modules:
        p = types.ModuleType(nome)
        p.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = p

_spec = importlib.util.spec_from_file_location(
    "app.services.knowledge.insurance_corpus",
    os.path.join(RAIZ, "app/services/knowledge/insurance_corpus.py"))
corpus = importlib.util.module_from_spec(_spec)
corpus.__package__ = "app.services.knowledge"
sys.modules["app.services.knowledge.insurance_corpus"] = corpus
_spec.loader.exec_module(corpus)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def teste_identidade_legal():
    print("\n[1] O número de processo SUSEP é a identidade do documento")
    texto = ("CONDIÇÕES GERAIS — SEGURO AUTOMÓVEL\n"
             "Processo SUSEP nº 15414.900123/2023-45\n"
             "Vigência a partir de 01/03/2024.")
    checar(corpus.extrair_susep(texto) == "15414.900123/2023-45",
           "extrai o número de processo", str(corpus.extrair_susep(texto)))
    checar(corpus.extrair_vigencia(texto) == "2024-03-01",
           "extrai a vigência declarada no documento",
           str(corpus.extrair_vigencia(texto)))
    checar(corpus.extrair_susep("documento qualquer sem processo") is None,
           "texto sem processo devolve None")


def teste_so_aceita_norma():
    print("\n[2] O filtro recusa o que não é norma")
    recusar = [
        ("Tabela de preços do restaurante", "cardápio e valores", "https://x.com/menu.pdf"),
        ("Relatório anual", "resultados do exercício", "https://empresa.com/ri.pdf"),
        ("Condições gerais", "condições gerais de uso do site",
         "https://loja-qualquer.com/termos.pdf"),
    ]
    for titulo, texto, url in recusar:
        r = corpus.classificar(titulo, texto, url)
        checar(r is None, f"recusa '{titulo[:38]}'", str(r))

    checar(corpus.classificar("", "documento solto", "https://qualquer.com/a.pdf") is None,
           "documento sem seguradora reconhecida é recusado")


def teste_reconhece_norma_de_verdade():
    print("\n[3] Reconhece norma de verdade, e de quem é")
    casos = [
        ("Condições Gerais Seguro Auto", "processo SUSEP",
         "https://www.portoseguro.com.br/condicoes-gerais-auto.pdf",
         "porto", "auto", "condicoes_gerais"),
        ("Manual do Segurado", "seguro residencial da Allianz",
         "https://www.allianz.com.br/manual.pdf",
         "allianz", "residencial", "manual_do_segurado"),
        ("Circular SUSEP nº 621", "dispõe sobre seguro de vida",
         "https://www.gov.br/susep/circular-621.pdf",
         "susep", "vida", "circular_susep"),
    ]
    for titulo, texto, url, seg, ramo, tipo in casos:
        r = corpus.classificar(titulo, texto, url)
        ok = r and r["insurer_key"] == seg and r["product_line"] == ramo and r["doc_kind"] == tipo
        checar(bool(ok), f"classifica '{titulo[:34]}'",
               "" if ok else f"veio={r}")


def teste_susep_sozinho_basta():
    print("\n[4] Processo SUSEP no texto basta para reconhecer norma")
    r = corpus.classificar(
        "Documento", "Processo SUSEP nº 15414.900987/2024-11 — Porto Seguro",
        "https://www.portoseguro.com.br/doc.pdf")
    checar(r is not None and r["doc_kind"] == "condicoes_gerais",
           "documento com processo SUSEP é tratado como condição geral",
           str(r))


def teste_hash_ignora_reformatacao():
    print("\n[5] Re-renderização do PDF não é 'mudança na origem'")
    a = "Artigo 1.  A cobertura   compreende\n\n  danos materiais."
    b = "Artigo 1. A cobertura compreende danos materiais."
    checar(corpus._hash(a) == corpus._hash(b),
           "espaço e quebra de linha diferentes geram o MESMO hash",
           "senão o corpus acusaria mudança toda semana e re-ingeriria à toa")

    c = "Artigo 1. A cobertura compreende danos materiais e corporais."
    checar(corpus._hash(a) != corpus._hash(c),
           "mudança real de conteúdo gera hash diferente")


def teste_cobertura_do_mercado():
    print("\n[6] Cobertura do vocabulário do setor")
    checar(len(corpus.SEGURADORAS) >= 14,
           f"{len(corpus.SEGURADORAS)} seguradoras/órgãos reconhecidos")
    checar(len(corpus.RAMOS) >= 13, f"{len(corpus.RAMOS)} ramos reconhecidos")
    checar("susep" in corpus.SEGURADORAS and "cnseg" in corpus.SEGURADORAS,
           "órgãos reguladores entram junto das seguradoras")


def main() -> int:
    print("=" * 68)
    print("SPEC-057 BLOCO H — CORPUS NORMATIVO")
    print("=" * 68)
    teste_identidade_legal()
    teste_so_aceita_norma()
    teste_reconhece_norma_de_verdade()
    teste_susep_sozinho_basta()
    teste_hash_ignora_reformatacao()
    teste_cobertura_do_mercado()

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  X {f}")
        return 1
    print("TODAS AS GARANTIAS VERIFICADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
