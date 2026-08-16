"""Republicar uma carta não pode apagar o lastro dela.

O DEFEITO, EM UMA FRASE
=======================
`insert_embeddings` faz `upsert` de **ponto inteiro** (`qdrant_service.py:355`),
não `set_payload`. Reescrever uma carta com menos payload não acrescenta:
**substitui**. Então o `select` de quem republica é a lista do que sobrevive — e
duas colunas não estavam nela.

📊 MEDIDO EM 15/08/2026, sobre as 5.394 cartas de acervo publicadas
====================================================================
    python backend/scripts/destilacao_max/medir_o_lastro.py

⚠️ O comando está versionado, e não é zelo: os cinco números abaixo nasceram de
um script que morava só no `%TEMP%` de uma sessão. **Número medido sem base de
prova preservada vira folclore no lote seguinte** (`pedacos/README.md`), e a
CLAUDE.md §12.1 exige a query ao lado do 📊.

Um `reindexar_acervo.py --aplicar` de ontem faria, em 100% delas:

    5.337  reescritas SEM `unit_id` e SEM `faceta`
       57  RECUSADAS — contadas como `falhou`, sem nada avisar

E as 57 são o retrato do defeito. Todas da HDI, todas por `{CNPJ}`, e o `{CNPJ}`
é o **número de processo SUSEP** (`15414.900228/2017-63`), que só parece CNPJ
para quem não sabe que o documento é público. `publish_card_sync:571` decide isso
com `documento_publico=bool(card.get("source_unit_id"))` — e o `select` não pedia
`source_unit_id`, então a resposta era sempre `False`.

Uma carta de condição geral pública tratada como conversa de segurado. O nome do
erro no relatório seria `rejected_pii`, que mente sobre o que aconteceu: não
vazou dado de ninguém, o portão é que estava com a régua errada.

A SEGUNDA COLUNA: ONDE A FACETA MORA
=====================================
`knowledge_cards` não tem coluna `faceta`. `publicar_cartas.py` grava o valor em
`pii_check["faceta"]` (:332) e passa a chave de topo só na PRIMEIRA publicação
(:385). Quem republica lê a carta DO BANCO — e do banco a chave de topo nunca
vem. Os três republicadores perdiam a faceta:

    reindexar_acervo.py:157      sem source_unit_id, sem pii_check
    curadoria_cartas.py:1066     sem source_unit_id, sem pii_check  ← roda SOZINHO
    admin_atlas.py:724           select("*") — tem as duas, e mesmo assim perdia,
                                 porque `publish_card_sync` lia `card["faceta"]`

Por isso o conserto da faceta mora em `publish_card_sync`, não em cada chamador:
um lugar conserta os três (CLAUDE.md §5 — consolidar, não duplicar ao lado).

A LINHA DE CONTROLE (CLAUDE.md §9.2)
=====================================
Todo caso deste arquivo tem um par que difere em **um fator só**:

    faceta em `pii_check`     ×  `pii_check` sem faceta      → chave ausente
    carta COM source_unit_id  ×  a MESMA carta sem ele       → recusada
    select de hoje            ×  o select de ontem, simulado → perde as duas

O par é o que dá direito à conclusão. Sem ele, uma carta que passa poderia estar
passando por qualquer outro motivo — e foi assim que o mérito quase foi creditado
ao lugar errado em 15/08.

MUTAÇÃO (CLAUDE.md §9.3)
=========================
`teste_a_mutacao_derruba_o_guarda` reconstrói o dict que o `select` ANTIGO
produzia e prova que o guarda **reprova** com ele. Um teste que não tem como
falhar não guarda nada.

⚠️ O QUE ESTE TESTE **NÃO** COBRE — declarado, não escondido
=============================================================
Ele afere os **kwargs** que `publish_card_sync` entrega a `insert_embeddings`,
e não o payload final montado em `qdrant_service.py:306-330`. Em particular, a
regra de promoção `if _k not in payload and _v not in (None, "")` (`:329`) fica
**inexercitada** aqui — se ela mudasse, este teste continuaria verde.

E o dublê `_Sparse.embed` devolve iterador vazio contra a lista de 1 item do
fastembed real. A única diferença é `qdrant_service.py:342` pular o vetor BM25;
`knowledge_extras`, que é o que se afere, não muda. Um guarda do payload final
pertence a um teste de `qdrant_service`, não a este.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Pacotes de fachada: `app/__init__.py` real arrasta openai e pydantic_settings.
# Mesmo desenho de `test_a_regua_da_carta_e_uma_so.py:76-95`.
for _n, _p in (("app", ("app",)), ("app.core", ("app", "core")),
               ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(nome: str, *partes: str):
    caminho = os.path.join(RAIZ, *partes)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def _ler(*partes: str) -> str:
    return open(os.path.join(RAIZ, *partes), encoding="utf-8").read()


# ─────────────────────────────────────────────────────────────────────────────
# As bordas caras, trocadas por dublês que REGISTRAM. O que se testa é o que
# `publish_card_sync` MANDA para o índice — não o índice.
# ─────────────────────────────────────────────────────────────────────────────
CAPTURADO: dict = {}


class _Qdrant:
    def insert_embeddings(self, **kw):
        CAPTURADO.clear()
        CAPTURADO.update(kw)
        return True


_qs = types.ModuleType("app.services.qdrant_service")
_qs.get_qdrant_service = lambda: _Qdrant()
sys.modules["app.services.qdrant_service"] = _qs

_ks = types.ModuleType("app.services.knowledge_scope")
_ks.GLOBAL_COLLECTION = "autobrokers_global"
_ks.SCOPE_GLOBAL_AUTOBROKERS = "global:autobrokers"
sys.modules["app.services.knowledge_scope"] = _ks

_cfg = types.ModuleType("app.core.config")
_cfg.settings = types.SimpleNamespace(OPENAI_API_KEY="teste")
sys.modules["app.core.config"] = _cfg

_lc = types.ModuleType("langchain_openai")


class _Emb:
    def __init__(self, **kw):
        pass

    def embed_documents(self, textos):
        return [[0.0] * 1536 for _ in textos]


_lc.OpenAIEmbeddings = _Emb
sys.modules["langchain_openai"] = _lc

# `fastembed` é opcional no próprio código (try/except em :598). Um dublê que
# devolve lista vazia mantém o caminho igual sem instalar o pacote.
_fe = types.ModuleType("fastembed")


class _Sparse:
    def __init__(self, **kw):
        pass

    def embed(self, textos):
        return iter([])


_fe.SparseTextEmbedding = _Sparse
sys.modules["fastembed"] = _fe

_carregar("app.services.atlas.templater", "app", "services", "atlas", "templater.py")
_carregar("app.services.curadoria_cartas", "app", "services", "curadoria_cartas.py")
D = _carregar("app.services.attendance_distiller",
              "app", "services", "attendance_distiller.py")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _extras(card: dict):
    """O que `publish_card_sync` mandou ao índice, ou None se recusou."""
    CAPTURADO.clear()
    ok = D.publish_card_sync(dict(card))
    return (CAPTURADO.get("knowledge_extras") or {}) if ok else None


# ─────────────────────────────────────────────────────────────────────────────
# O material real: uma das 57 cartas da HDI que seriam recusadas hoje.
# 📊 O `{CNPJ}` que a derruba é o número de processo SUSEP.
# ─────────────────────────────────────────────────────────────────────────────
CARTA_SUSEP = (
    "O Sompo Imobiliário Residencial versão 1.6 (hoje operado pela HDI Seguros) "
    "(SUSEP 15414.900228/2017-63) é contratado a Primeiro Risco Absoluto: a "
    "Seguradora indeniza o prejuízo até o limite máximo de indenização da "
    "cobertura, sem aplicar rateio por subseguro."
)
UNIT = "norm-12f47490-7309-4f6a-b10c-18f522f66cd3-v1#0013"

CARTA_LIMPA = (
    "Documentos para abrir sinistro de colisão com terceiro: CNH do condutor, "
    "documento do veículo, comprovante de residência dos últimos três meses e "
    "quatro fotos do veículo com a placa visível em ao menos uma delas."
)


# ═════════════════════════════════════════════════════════════════════════════
def teste_a_faceta_sobrevive_vinda_de_pii_check() -> None:
    """O conserto: republicar lendo a faceta de onde ela realmente mora."""
    print("\n[1] a faceta sobrevive à republicação")

    e = _extras({"id": "c1", "card_text": CARTA_LIMPA, "insurer_key": "allianz",
                 "ramo": "auto", "category": "sinistro", "source_unit_id": UNIT,
                 "pii_check": {"faceta": "documento", "deterministic": True}})
    checar(e is not None, "a carta é publicada")
    checar((e or {}).get("faceta") == "documento",
           "faceta='documento' chega ao payload vinda de pii_check",
           f"veio {(e or {}).get('faceta')!r}")
    checar((e or {}).get("unit_id") == UNIT,
           "unit_id chega ao payload", f"veio {(e or {}).get('unit_id')!r}")

    # LINHA DE CONTROLE — a MESMA carta, `pii_check` sem faceta.
    #
    # ⚠️ `c is not None` PRIMEIRO, e não é zelo: `"faceta" not in (c or {})` é
    # satisfeito quando a carta foi RECUSADA (`c is None` → `{}`). Sozinha, a
    # asserção passaria por recusa — que é o oposto do que se quer provar.
    c = _extras({"id": "c1", "card_text": CARTA_LIMPA, "insurer_key": "allianz",
                 "ramo": "auto", "category": "sinistro", "source_unit_id": UNIT,
                 "pii_check": {"deterministic": True}})
    checar(c is not None, "CONTROLE: a carta continua sendo PUBLICADA",
           "sem isto, as duas asserções abaixo passam por recusa")
    checar(c is not None and "faceta" not in c,
           "CONTROLE: sem faceta em pii_check, a chave fica AUSENTE",
           f"veio {(c or {}).get('faceta')!r}")
    checar(c is not None and c.get("unit_id") == UNIT,
           "CONTROLE: e o unit_id continua chegando (mudou UM fator só)")


def teste_a_faceta_de_topo_continua_valendo() -> None:
    """A primeira publicação (`publicar_cartas.py:385`) não pode regredir."""
    print("\n[2] a faceta de topo — o caminho da primeira publicação")

    e = _extras({"id": "c2", "card_text": CARTA_LIMPA, "faceta": "exclusao",
                 "source_unit_id": UNIT})
    checar((e or {}).get("faceta") == "exclusao",
           "faceta de topo chega ao payload", f"veio {(e or {}).get('faceta')!r}")

    # Topo vence `pii_check` quando os dois existem — desempate declarado.
    e = _extras({"id": "c2", "card_text": CARTA_LIMPA, "faceta": "exclusao",
                 "source_unit_id": UNIT, "pii_check": {"faceta": "documento"}})
    checar((e or {}).get("faceta") == "exclusao",
           "com os dois presentes, o de TOPO vence",
           f"veio {(e or {}).get('faceta')!r}")

    # E `pii_check` que não é dict não pode explodir nem virar faceta.
    e = _extras({"id": "c2", "card_text": CARTA_LIMPA, "source_unit_id": UNIT,
                 "pii_check": "isto não é um dict"})
    checar(e is not None and "faceta" not in e,
           "pii_check que não é dict: sem faceta, sem exceção")


def teste_o_numero_da_susep_nao_e_cnpj() -> None:
    """As 57 da HDI. O fator é `source_unit_id`, e a linha de controle prova."""
    print("\n[3] a carta de documento público não é recusada por {CNPJ}")

    e = _extras({"id": "c3", "card_text": CARTA_SUSEP, "insurer_key": "hdi",
                 "ramo": "residencial", "source_unit_id": UNIT,
                 "pii_check": {"faceta": "limite"}})
    checar(e is not None,
           "COM source_unit_id, a carta com número SUSEP é PUBLICADA")
    checar((e or {}).get("faceta") == "limite", "e leva a faceta junto")

    # LINHA DE CONTROLE — a MESMA carta, mudando UM fator: sem `source_unit_id`.
    # Ela TEM de ser recusada. Se passasse, o fator não seria o `source_unit_id`
    # e a conclusão do caso acima não teria dono.
    c = _extras({"id": "c3", "card_text": CARTA_SUSEP, "insurer_key": "hdi",
                 "ramo": "residencial"})
    checar(c is None,
           "CONTROLE: sem source_unit_id, a MESMA carta é recusada",
           "se passou, o fator medido não é o que se pensa")


def teste_os_republicadores_pedem_as_colunas() -> None:
    """O `select` é a lista do que sobrevive. Os três têm de pedir o mesmo."""
    print("\n[4] os três republicadores pedem source_unit_id e pii_check")

    # ⚠️ Ancorar na FUNÇÃO nos DOIS casos. A primeira versão pegava o primeiro
    # `.select(` do arquivo e acertava por acidente: `reindexar_acervo.py` tem
    # quatro, e o de `_diagnostico` (:101) só escapava porque tem `count=` no
    # meio, quebrando a âncora do `)`. Um guarda que depende de um acidente de
    # sintaxe do vizinho não guarda — só ainda não falhou.
    rein = _ler("scripts", "destilacao_max", "reindexar_acervo.py")
    corpo_rein = rein.split("def _ler_publicadas")[-1].split("\ndef ")[0]
    sel_rein = re.search(r'\.select\(\s*((?:"[^"]*"\s*)+)\)', corpo_rein)
    corpo = sel_rein.group(1) if sel_rein else ""
    checar(bool(sel_rein), "_ler_publicadas tem um select localizável")
    checar("source_unit_id" in corpo, "reindexar_acervo pede source_unit_id",
           f"select={corpo[:90]!r}")
    checar("pii_check" in corpo, "reindexar_acervo pede pii_check",
           f"select={corpo[:90]!r}")

    # ⚠️ Ancorar na FUNÇÃO, não na primeira ocorrência de `pending_review`:
    # `curar_lote_sync` também lê essa fila (:850) e não republica nada. A
    # primeira versão deste teste caiu nessa — e acusou o código certo.
    cur = _ler("app", "services", "curadoria_cartas.py")
    corpo_pub = cur.split("def publicar_lote_sync")[-1].split("\ndef ")[0]
    sel_pub = re.search(r'\.select\(\s*((?:"[^"]*"\s*)+)\)', corpo_pub)
    corpo_sel = sel_pub.group(1) if sel_pub else ""
    checar(bool(sel_pub), "publicar_lote_sync tem um select localizável")
    checar("source_unit_id" in corpo_sel,
           "publicar_lote_sync pede source_unit_id (roda sozinho em produção)",
           f"select={corpo_sel[:90]!r}")
    checar("pii_check" in corpo_sel, "publicar_lote_sync pede pii_check",
           f"select={corpo_sel[:90]!r}")

    adm = _ler("app", "api", "admin_atlas.py")
    checar('table("knowledge_cards").select("*")' in adm,
           "admin_atlas usa select('*') — já traz as duas")


def teste_a_mutacao_derruba_o_guarda() -> None:
    """MUTAÇÃO: o dict que o `select` ANTIGO produzia tem de REPROVAR.

    Não se muta o arquivo — reconstrói-se a ENTRADA que o código mutado geraria.
    Mesmo efeito, sem risco de deixar o repositório sujo se o teste morrer no
    meio (e sem `git checkout`, que já apagou trabalho não commitado aqui).
    """
    print("\n[5] MUTAÇÃO — o select de ontem tem de falhar")

    # `select("id, card_text, insurer_key, ramo, category")` — o de ontem.
    antigo = {"id": "c4", "card_text": CARTA_LIMPA, "insurer_key": "allianz",
              "ramo": "auto", "category": "sinistro"}
    e = _extras(antigo)
    checar(e is not None and "faceta" not in e,
           "com o select antigo a faceta SOME — o guarda tem como falhar")
    checar(e is not None and "unit_id" not in e,
           "com o select antigo o unit_id SOME")

    antigo_susep = {"id": "c4", "card_text": CARTA_SUSEP, "insurer_key": "hdi",
                    "ramo": "residencial", "category": "sinistro"}
    checar(_extras(antigo_susep) is None,
           "com o select antigo a carta da HDI é RECUSADA — as 57")

    # E o par que fecha: a MESMA carta com as duas colunas passa e leva tudo.
    novo = dict(antigo_susep, source_unit_id=UNIT, pii_check={"faceta": "limite"})
    n = _extras(novo)
    checar(n is not None and n.get("faceta") == "limite" and n.get("unit_id") == UNIT,
           "e com as colunas a MESMA carta passa, com faceta e unit_id")


def main() -> int:
    print(__doc__.split("\n")[0])
    print("=" * 70)
    teste_a_faceta_sobrevive_vinda_de_pii_check()
    teste_a_faceta_de_topo_continua_valendo()
    teste_o_numero_da_susep_nao_e_cnpj()
    teste_os_republicadores_pedem_as_colunas()
    teste_a_mutacao_derruba_o_guarda()

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("TUDO VERDE — o lastro sobrevive à republicação.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
