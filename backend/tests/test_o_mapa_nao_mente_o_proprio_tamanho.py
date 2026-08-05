"""O mapa não mente o próprio tamanho — nem escolhe as telas por sorteio.

A HISTÓRIA
----------
📊 Medido em 05/08/2026, antes de qualquer mapa ser promovido a `active`:

    render_map_for_llm(map_obj, max_nodes=30)  →  list(nodes.items())[:30]

A chave de cada nó é `sha1(...)[:12]`, e o mapa mora em JSONB — que **não
preserva ordem de inserção**. Todas as chaves têm 12 caracteres, então a ordem
era **lexicográfica sobre o digest**: uma amostra pseudo-aleatória estável, sem
nenhuma relação com o fluxo da URA.

    allianz  1.323 nós  →  o modelo veria 30  (2,3%)
    porto      840 nós  →  3,6%

E o prompt anunciava o resultado como **"MAPA COMPLETO DA URA DESTA
SEGURADORA"**. Injetar 2% rotulado como 100% é pior do que não injetar nada: o
modelo não tem como desconfiar do próprio prompt, e quando a tela atual não
estivesse entre as trinta ele escolheria a menos errada — com confiança.

O QUE ESTE TESTE GUARDA
-----------------------
Três coisas, e nenhuma delas é "a lista tem 30 itens":

1. a **raiz** entra sempre — sem ela o modelo não sabe onde o fluxo começa;
2. tela marcada `nao_rota` **não** é renderizada como rota;
3. o corte é por **quantas vezes a tela foi vista**, não por digest.

E o rótulo diz **quantas de quantas**.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
`teste_o_corte_antigo_realmente_sorteava` reconstrói o corte de antes e prova
que ele **deixava a raiz de fora** e **incluía tela morta**. Sem essa linha, um
teste verde não distingue "o conserto funciona" de "tanto faz".
"""
from __future__ import annotations

import importlib.util
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ALVO = os.path.abspath(os.path.join(
    AQUI, "..", "app", "services", "ura_map_service.py"))

FALHAS: list = []


def checar(condicao: bool, descricao: str, porque: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  X     {descricao}")
        if porque:
            print(f"        {porque}")
        FALHAS.append(descricao)


def _carregar():
    """Carrega pelo caminho — o pacote `app` puxa dependência que a máquina
    de desenvolvimento não tem, e reprovar por isso ensina a ignorar teste."""
    spec = importlib.util.spec_from_file_location("_ura_sob_teste", ALVO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ura_sob_teste"] = mod
    spec.loader.exec_module(mod)
    return mod


ura = _carregar()


def _mapa_de_prova() -> dict:
    """Um mapa onde a resposta certa e a errada são visivelmente diferentes.

    A raiz recebe um id que cai no FIM da ordem lexicográfica, e as telas
    mortas recebem ids que caem no começo. Assim o corte antigo escolhe
    exatamente o pior conjunto possível — que é o ponto.
    """
    nodes = {}
    # 40 telas MORTAS, com id no começo do alfabeto e muitas amostras.
    for i in range(40):
        nodes[f"aaa{i:09d}"] = {
            "kind": "menu", "text": f"Aviso institucional {i}", "nao_rota": True,
            "samples": 99, "order": i, "options": [],
        }
    # 5 telas VIVAS, id no meio, com contagem de amostras diferente entre si.
    vivas = [("mmm000000001", "Digite o CPF", 50, 1),
             ("mmm000000002", "Escolha o servico", 40, 2),
             ("mmm000000003", "Informe a placa", 30, 3),
             ("mmm000000004", "Confirme o endereco", 20, 4),
             ("mmm000000005", "Aguarde o guincho", 3, 5)]
    for nid, texto, vistas, ordem in vivas:
        nodes[nid] = {"kind": "menu", "text": texto, "samples": vistas,
                      "order": ordem,
                      "options": [{"label": "Auto", "reply": "1"}]}
    # A RAIZ, com id no FIM do alfabeto e poucas amostras.
    nodes["zzz000000001"] = {"kind": "menu", "text": "Bem-vindo a assistencia",
                             "samples": 2, "order": 0,
                             "options": [{"label": "Auto", "reply": "1"}]}
    return {"root": "zzz000000001", "nodes": nodes,
            "coverage": {"pct": 37}}


def teste_o_corte_antigo_realmente_sorteava() -> None:
    """CONTROLE. O corte de antes deixava a raiz fora e enchia de tela morta."""
    print("\n[1] CONTROLE: os dois lados conseguem ser diferentes")
    mapa = _mapa_de_prova()
    nodes = mapa["nodes"]

    # exatamente como era: list(nodes.items())[:30]
    antigos = list(nodes.items())[:30]
    ids_antigos = [nid for nid, _ in antigos]

    checar(mapa["root"] not in ids_antigos,
           "o corte antigo NÃO incluía a tela inicial",
           "se incluísse, o conserto da raiz não teria o que consertar")
    mortas = sum(1 for _nid, n in antigos if n.get("nao_rota"))
    checar(mortas > 0,
           f"e enchia a lista de tela morta ({mortas} de 30)")


def teste_a_raiz_entra_sempre() -> None:
    print("\n[2] A tela inicial nunca fica de fora")
    mapa = _mapa_de_prova()
    txt = ura.render_map_for_llm(mapa, max_nodes=3)
    checar("Bem-vindo a assistencia" in txt, "a raiz está no texto renderizado")
    checar("[TELA INICIAL]" in txt, "e vem marcada como inicial")


def teste_tela_morta_nao_vira_rota() -> None:
    print("\n[3] Tela que não leva a lugar nenhum não é oferecida")
    mapa = _mapa_de_prova()
    txt = ura.render_map_for_llm(mapa, max_nodes=30)
    checar("Aviso institucional" not in txt,
           "nenhuma tela `nao_rota` foi renderizada",
           "renderizá-la ensina o modelo a escolher uma saída morta")


def teste_ordena_por_quantas_vezes_foi_vista() -> None:
    print("\n[4] O corte é por evidência, não por digest")
    mapa = _mapa_de_prova()
    txt = ura.render_map_for_llm(mapa, max_nodes=3)
    checar("Digite o CPF" in txt,
           "a tela mais vista (50 amostras) entrou")
    checar("Aguarde o guincho" not in txt,
           "e a mais rara (3 amostras) ficou de fora do corte de 3")


def teste_o_rotulo_diz_quantas_de_quantas() -> None:
    print("\n[5] O rótulo não mente o tamanho")
    mapa = _mapa_de_prova()
    resumo = ura.resumo_honesto_do_mapa(mapa, max_nodes=30)
    checar("30 de 46" in resumo,
           f"o resumo declara a amostra e o total ({resumo!r})")
    checar("cobertura observada 37%" in resumo,
           "e leva a cobertura observada junto")

    vazio = ura.resumo_honesto_do_mapa({}, max_nodes=30)
    checar("0 de 0" in vazio, "mapa vazio não explode e diz zero")


def teste_o_prompt_nao_diz_mais_completo() -> None:
    print("\n[6] A palavra que causou o problema saiu do prompt")
    caminho = os.path.abspath(os.path.join(
        AQUI, "..", "app", "services", "insurer_dispatch_service.py"))
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    checar("MAPA COMPLETO DA URA" not in fonte,
           "o prompt não afirma mais que o mapa é completo")
    checar("resumo_honesto_do_mapa" in fonte,
           "e passou a declarar o tamanho da amostra")


def main() -> int:
    print("=" * 72)
    print("O MAPA NAO MENTE O PROPRIO TAMANHO")
    print("=" * 72)
    for teste in (teste_o_corte_antigo_realmente_sorteava,
                  teste_a_raiz_entra_sempre,
                  teste_tela_morta_nao_vira_rota,
                  teste_ordena_por_quantas_vezes_foi_vista,
                  teste_o_rotulo_diz_quantas_de_quantas,
                  teste_o_prompt_nao_diz_mais_completo):
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
    print("A RAIZ ENTRA, A TELA MORTA SAI, E O ROTULO DIZ A VERDADE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
