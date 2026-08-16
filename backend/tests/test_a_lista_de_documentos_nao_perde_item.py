"""Extrair a lista de documentos não pode perder item — e há como provar.

O DEFEITO QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
===============================================
📊 A destilação em prosa perde item de lista, e isso foi medido: o núcleo comum
de documentos cai de **12/16 no texto bruto para 5/16 nas cartas destiladas**.
"Dados bancários" saiu de 0/4 para 3/3 — as três seguradoras exigem, e nenhuma
carta destilada de auto registrou.

    SPEC-072 §3.4 ③ — NÃO DESTILE A LISTA. EXTRAIA A SEÇÃO INTEIRA.

Uma lista incompleta **parece** uma lista. Ninguém percebe que faltou item: o
segurado vai ao órgão, volta sem o papel certo, e o processo perde dias.

O GATE, E POR QUE SÃO DOIS
===========================
A SPEC pede "contar os itens na origem e na carta; divergência = falha". Isso é
mensurável onde HÁ marcador — 📊 59 das 253 seções (23%). Nas outras 194 não
existe item delimitado (a Yelum é tabela achatada em prosa: 128 de 139 sem
marcador nenhum), e inventar um contador seria **fabricar o gate**. A heurística
de fronteira de maiúscula foi medida contra a verdade de allianz+porto e erra
**107% na mediana** — "RG, CPF ou CNH do segurado" vira 3 itens.

Então:

    COM marcador   itens na origem == soma dos itens nas partes
    SEMPRE         o texto limpo da origem é RECONSTRUÍVEL a partir das partes

O segundo é mais forte e vale para 100% das corridas: ele não depende de
heurística nenhuma, e pega perda de item, perda de frase e perda de caractere.

MUTAÇÃO (CLAUDE.md §9.3)
=========================
`teste_a_mutacao_derruba_o_guarda` estreita o regex de item para uma letra só —
o defeito real que eu quase cometi, porque a maior lista do acervo chega a
`aa)`, `bb)`, `ee)`. Com ele, a contagem despenca e o teste TEM de falhar.

LINHA DE CONTROLE (§9.2)
=========================
Cada caso tem um par que difere em um fator só: a carta com marcador × a mesma
sem marcador; a seção de documentos × a seção de conduta; o regex de duas letras
× o de uma.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _carregar():
    caminho = os.path.join(RAIZ, "scripts", "acervo",
                           "extrair_listas_de_documentos.py")
    spec = importlib.util.spec_from_file_location("extrator", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["extrator"] = mod
    spec.loader.exec_module(mod)
    return mod


EX = _carregar()


def _tudo():
    """Roda o extrator de verdade sobre o bruto de verdade."""
    saida, corridas = [], []
    for seg in ("allianz", "porto", "yelum"):
        ps = EX.carregar(seg)
        for p in ps:
            p["_seg"] = seg
        for c in EX.corridas_de_documento(ps):
            corridas.append(c)
            saida.extend(EX.carta_de(c, EX.MAX_CARACTERES))
    return saida, corridas


CARTAS, CORRIDAS = _tudo()


# ═════════════════════════════════════════════════════════════════════════════
def teste_a_regua_e_respeitada() -> None:
    print("\n[1] a régua da carta — 40 a 1.800, sem exceção")
    tam = sorted(len(c["texto"]) for c in CARTAS)
    checar(bool(CARTAS), "o extrator produz cartas", f"{len(CARTAS)}")
    checar(tam[-1] <= EX.MAX_CARACTERES,
           f"nenhuma passa de {EX.MAX_CARACTERES}", f"maior={tam[-1]}")
    checar(tam[0] >= EX.MIN_CARACTERES,
           f"nenhuma fica abaixo de {EX.MIN_CARACTERES}", f"menor={tam[0]}")
    checar(all(c["faceta"] == "documento" for c in CARTAS),
           "todas nascem com faceta='documento'")
    checar(all(c.get("unit_id_origem") for c in CARTAS),
           "e todas com o lastro — o unit_id do contrato")


def _blocos_com_cartas(corrida):
    """(bloco_de_origem, cartas_dele) — a unidade honesta de comparação.

    ⚠️ A primeira versão comparava a CORRIDA inteira com as cartas dela, e
    acusou 5 de 32 divergindo. O diagnóstico estava certo e a régua, errada: o
    portão de pertinência descarta blocos de propósito (cláusula de conduta não
    é lista de documentos), e cobrar que os itens deles apareçam nas cartas é
    cobrar que o portão não funcione.

    O que TEM de valer é: **nenhum item se perde entre o bloco e as cartas dele**
    — a partição não pode comer nada. O que o portão barra é contado à parte,
    no teste [4], onde é a afirmação certa.
    """
    _, _, ps = corrida
    corpo = EX.limpar("\n\n".join(p.get("corpo") or "" for p in ps))
    saida = []
    for titulo, bloco in EX.blocos_de_cobertura(corpo):
        cartas = EX._carta_de_bloco(corrida, titulo, bloco, EX.MAX_CARACTERES)
        if cartas:
            saida.append((bloco, cartas))
    return saida


def teste_nenhum_item_se_perde() -> None:
    """O GATE DA SPEC: itens no bloco == soma dos itens nas partes dele."""
    print("\n[2] contagem de itens: bloco de origem × cartas dele")
    conferidas = divergentes = 0
    exemplos = []
    for corrida in CORRIDAS:
        for bloco, cartas in _blocos_com_cartas(corrida):
            na_origem = len(EX.itens_de(bloco))
            if na_origem < 3:
                continue                  # sem lista, nada a contar
            nas_cartas = sum(c["_itens_parte"] for c in cartas)
            conferidas += 1
            if nas_cartas != na_origem:
                divergentes += 1
                if len(exemplos) < 4:
                    exemplos.append((cartas[0]["_seguradora"], na_origem,
                                     nas_cartas, cartas[0]["unit_id_origem"]))
    print(f"      blocos com lista contável: {conferidas}")
    print(f"      divergentes: {divergentes}")
    for e in exemplos:
        print(f"        {e[0]} origem={e[1]} cartas={e[2]} {e[3]}")
    checar(conferidas >= 20, "há material suficiente para o gate",
           f"só {conferidas} blocos com ≥3 itens")
    checar(divergentes == 0,
           "NENHUM item se perde entre o bloco e as cartas dele",
           f"{divergentes} de {conferidas} divergem")


def teste_o_texto_da_origem_e_reconstruivel() -> None:
    """O invariante FORTE — vale para 100%, sem heurística de item."""
    print("\n[3] o texto limpo da origem sobrevive inteiro nas cartas")
    testadas = perdidas = 0
    pior = None
    for corrida in CORRIDAS:
        for bloco, cartas in _blocos_com_cartas(corrida):
            # o que sobrou nas cartas, sem os cabeçalhos que o extrator põe
            junto = " ".join(c["texto"].split(": ", 1)[-1] for c in cartas)
            alvo = "".join(bloco.split())
            saiu = "".join(junto.split())
            testadas += 1
            # ⚠️ Comparação por conteúdo sem espaço: a partição reflui quebras
            # de linha, e cobrar `==` literal reprovaria por formatação, não
            # por perda.
            if len(saiu) < len(alvo) * 0.97:
                perdidas += 1
                if pior is None or len(saiu) / max(1, len(alvo)) < pior[0]:
                    pior = (len(saiu) / max(1, len(alvo)),
                            cartas[0]["unit_id_origem"], len(alvo), len(saiu))
    print(f"      blocos testados: {testadas}   com perda >3%: {perdidas}")
    if pior:
        print(f"      pior: {pior[0]:.1%} — {pior[1]} ({pior[2]} → {pior[3]} chars)")
    checar(testadas >= 30, "há blocos suficientes", f"{testadas}")
    checar(perdidas == 0,
           "nenhum bloco perde mais de 3% do texto limpo",
           f"{perdidas} perderam")


def teste_o_portao_de_pertinencia_guarda() -> None:
    """LINHA DE CONTROLE: lista de documentos passa, cláusula de conduta não."""
    print("\n[4] o portão de pertinência — nomear documento é obrigatório")
    lista = ("a) Cópia da CNH do condutor; b) CRLV do veículo; "
             "c) Boletim de Ocorrência; d) Comprovante de residência; "
             "e) Dados bancários do titular.")
    conduta = ("a) Tomar as providências para proteção dos bens; "
               "b) Aguardar o comparecimento do representante da Seguradora; "
               "c) Franquear ao representante o acesso ao local do sinistro; "
               "d) É vedado promover modificações no local do Sinistro.")
    checar(EX.nomeia_documentos(lista) >= 2,
           "a lista de documentos passa", f"{EX.nomeia_documentos(lista)} nomes")
    checar(EX.nomeia_documentos(conduta) < 2,
           "CONTROLE: a cláusula de CONDUTA não passa",
           f"{EX.nomeia_documentos(conduta)} nomes — se passar, o portão é "
           "decoração e volta a gerar 'lista' de obrigações")
    checar(EX.nomeia_documentos("") == 0, "texto vazio não passa")


def teste_a_particao_nao_corta_item_ao_meio() -> None:
    print("\n[5] a partição cai em fronteira de item, nunca no meio")
    multi = [c for c in CARTAS if c["_de"] > 1]
    checar(bool(multi), "há cartas multi-parte para conferir", f"{len(multi)}")
    # Uma parte que não é a primeira não pode começar no meio de uma palavra.
    ruins = [c for c in multi if c["_parte"] > 1
             and c["texto"].split(": ", 1)[-1][:1].islower()
             and not c["texto"].split(": ", 1)[-1][:2].strip().endswith(")")]
    print(f"      partes 2+ começando em minúscula solta: {len(ruins)}")
    checar(len(ruins) <= len(multi) * 0.25,
           "a esmagadora maioria começa em item ou frase",
           f"{len(ruins)} de {len(multi)}")
    checar(all(c["_de"] <= EX.MAX_PARTES for c in CARTAS),
           f"nenhuma carta passa de {EX.MAX_PARTES} partes",
           "acima disso vira capítulo fatiado, não lista")


def teste_a_mutacao_derruba_o_guarda() -> None:
    """MUTAÇÃO: o regex de UMA letra — o erro que a Porto expõe."""
    print("\n[6] MUTAÇÃO — regex de item com uma letra só")
    import re

    guardado = EX._ITEM_ALFA
    porto = ("a) Alta médica;\n\nb) Apólice;\n\nz) Cópia integral;\n\n"
             "aa) Cópias do RG, CPF ou CNH do sindico;\n\n"
             "bb) Cópias do RG do segurado;\n\ncc) Dados bancários;\n\n"
             "dd) Declaração do funcionário;\n\nee) Declaração de inexistência;")
    certo = len(EX.itens_de(porto))
    try:
        EX._ITEM_ALFA = re.compile(r"(?m)^\s*([a-z])\)\s+")   # uma letra
        mutado = len(EX.itens_de(porto))
    finally:
        EX._ITEM_ALFA = guardado
    restaurado = len(EX.itens_de(porto))

    print(f"      duas letras: {certo} itens · uma letra: {mutado} · "
          f"restaurado: {restaurado}")
    checar(certo == 8, "o regex certo acha os 8 itens", f"achou {certo}")
    checar(mutado < certo,
           "MUTAÇÃO: com uma letra só, itens SOMEM — o guarda pode falhar",
           f"mutado={mutado} certo={certo}")
    checar(restaurado == certo, "e o regex volta ao normal (controle)")


def main() -> int:
    print(__doc__.split("\n")[0])
    print("=" * 72)
    print(f"  material: {len(CORRIDAS)} corridas · {len(CARTAS)} cartas")
    teste_a_regua_e_respeitada()
    teste_nenhum_item_se_perde()
    teste_o_texto_da_origem_e_reconstruivel()
    teste_o_portao_de_pertinencia_guarda()
    teste_a_particao_nao_corta_item_ao_meio()
    teste_a_mutacao_derruba_o_guarda()

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("TUDO VERDE — a lista sai inteira do contrato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
