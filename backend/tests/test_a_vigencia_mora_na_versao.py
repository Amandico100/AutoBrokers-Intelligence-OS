# -*- coding: utf-8 -*-
"""A vigência mora na versão — e a anterior é fechada por quem abre a nova.

Por que este arquivo existe
---------------------------
📊 Medido no projeto `dcajcvlzcjbmyapmklil` em 08/08/2026:

    normative_documents ............................ 35 linhas
       com effective_until ..........................  0
       com version_label ............................  0
    normative_document_versions .................... 29 linhas
       version mínima 1, version máxima .............  1
       com superseded_at ............................  0

⚠️ Um levantamento anterior concluiu que "não existe coluna onde escrever".
📊 Falso — as colunas existem desde a versão `20260725215808`. O defeito era de
**escritor**: `insurance_corpus.py` encadeava versões desde 25/07 e o
encadeamento nunca rodou, porque nenhum documento chegou à segunda captura.

Diagnóstico errado leva a conserto errado. "Falta coluna" teria produzido uma
coluna nova ao lado de duas vazias — três lugares para a mesma verdade.

O que este arquivo guarda
------------------------
1. A vigência da SUSEP ganha da que o PDF declara, e a do PDF ganha do nada —
   mas **nenhum degrau inventa uma data**.
2. `effective_until` só é escrito quando a SUSEP publicou a Data de Fim.
   `superseded_at` é escrito sempre. São fatos diferentes de donos diferentes.
3. A anterior é fechada **antes** de a nova ser inserida — porque
   `normative_versao_aberta_uk` (migration 01) recusaria a ordem contrária.
4. `normative_documents` recebe o espelho, e o espelho tem um escritor só.

Toda afirmação tem uma linha de CONTROLE ao lado (CLAUDE.md §9.2): o caso
vizinho que PRECISA continuar acontecendo. Um guarda testado só contra o caso
que deve falhar fica mais guloso a cada correção, e o custo aparece no caso
certo que sumiu em silêncio.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

for _n in ("app", "app.services", "app.services.knowledge", "app.services.research"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []

_spec = importlib.util.spec_from_file_location(
    "app.services.knowledge.insurance_corpus",
    RAIZ / "app" / "services" / "knowledge" / "insurance_corpus.py")
corpus = importlib.util.module_from_spec(_spec)
sys.modules["app.services.knowledge.insurance_corpus"] = corpus
_spec.loader.exec_module(corpus)

FALHAS: list = []


def checar(condicao: bool, nome: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X     {nome}  {detalhe}")


# ── o banco de mentira ────────────────────────────────────────────────────────
#
# Ele registra CADA escrita, **na ordem**. A ordem é metade do que este arquivo
# prova: "fecha a anterior antes de abrir a nova" não é verificável num duplo
# que só guarda o estado final.

DOC_ID = "3f2b9c14-0a7e-4d55-9b31-6c8f0e2a1d47"


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, db, tabela):
        self.db, self.t = db, tabela
        self.acao = self.payload = None
        self.filtros: dict = {}
        self.menor = self.nulo = None
        self.single = False

    def select(self, *_a, **_k):
        self.acao = "select"
        return self

    def eq(self, coluna, valor):
        self.filtros[coluna] = valor
        return self

    def lt(self, coluna, valor):
        self.menor = (coluna, valor)
        return self

    def is_(self, coluna, valor):
        self.nulo = (coluna, valor)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, _n):
        return self

    def maybe_single(self):
        self.single = True
        return self

    def update(self, payload):
        self.acao, self.payload = "update", dict(payload)
        return self

    def insert(self, payload):
        self.acao, self.payload = "insert", dict(payload)
        return self

    def execute(self):
        if self.acao == "select":
            if self.t == "normative_documents":
                return _Resposta(dict(self.db.documento) if self.single
                                 else [dict(self.db.documento)])
            return _Resposta([dict(v) for v in self.db.versoes])
        self.db.escritas.append((self.acao, self.t, self.payload,
                                 dict(self.filtros), self.menor, self.nulo))
        if self.acao == "insert" and self.t == "normative_document_versions":
            self.db.versoes.insert(0, dict(self.payload))
        if self.acao == "update" and self.t == "normative_document_versions":
            for v in self.db.versoes:
                if self.menor and not (v.get("version", 0) < self.menor[1]):
                    continue
                if self.nulo and v.get("superseded_at") is not None:
                    continue
                v.update(self.payload)
        if self.acao == "update" and self.t == "normative_documents":
            self.db.documento.update(self.payload)
        return _Resposta([self.payload])


class BancoDeMentira:
    def __init__(self, documento=None, versoes=()):
        self.documento = dict(documento or _documento())
        self.versoes = [dict(v) for v in versoes]
        self.escritas: list = []

    def table(self, nome):
        return _Consulta(self, nome)

    # os atalhos que os testes leem
    def gravadas(self, acao, tabela):
        return [e for e in self.escritas if e[0] == acao and e[1] == tabela]

    def ordem(self):
        return [(e[0], e[1]) for e in self.escritas]


def _documento(**extra):
    base = {
        "id": DOC_ID, "insurer_key": "porto", "insurer_name": "Porto Seguro",
        "product_line": "auto", "doc_kind": "condicoes_gerais",
        "title": "Condições Gerais CG140", "source_url": "https://exemplo/cg140.pdf",
        "susep_process": "15414.100233/2004-59", "status": "ingested",
        "content_hash": "hash-de-ontem", "check_interval_days": 45,
        "effective_from": None, "effective_until": None, "version_label": None,
    }
    base.update(extra)
    return base


def _versao(n, **extra):
    v = {"id": f"v-{n}", "version": n, "document_id": DOC_ID,
         "qdrant_doc_id": None, "superseded_at": None}
    v.update(extra)
    return v


TEXTO = ("CONDIÇÕES GERAIS — vigência a partir de 01/07/2024. " * 40)


def _servico(db, *, texto=TEXTO, chunks=120):
    s = corpus.InsuranceCorpusService(db)

    async def _buscar(_url, _company):
        return texto, None

    async def _global(_doc, _texto, _susep, _vig):
        _global.visto = dict(_doc)
        return chunks

    async def _guardar(_id, _n, _texto):
        return {"storage_ref": None, "text_storage_ref": None,
                "source_bytes": None, "source_media_type": None,
                "arquivado_em": None, "erros": {}}

    s._buscar = _buscar
    s._ingerir_no_global = _global
    s._guardar_a_fonte = _guardar
    s._visto = _global
    return s


def _ingerir(db, **kw):
    s = _servico(db)
    return asyncio.run(s.ingerir(DOC_ID, **kw))


# ── 1. de onde vem a data ─────────────────────────────────────────────────────

SUSEP = {"effective_from": "2026-07-01", "effective_until": None,
         "version_label": "CG144", "susep_version_id": "998877",
         "fim_da_anterior": "2026-06-30"}


def teste_a_susep_ganha_do_texto_e_o_texto_ganha_do_nada():
    print("\n[1] Três degraus, e nenhum deles inventa uma data")

    do_susep = corpus.InsuranceCorpusService._vigencia_da_versao(
        _documento(), TEXTO, SUSEP)
    checar(do_susep["effective_from"] == "2026-07-01"
           and do_susep["fonte"] == "susep_rep2",
           "com registro da SUSEP, a data é a dele e a fonte diz isso",
           str(do_susep))
    checar(do_susep["version_label"] == "CG144"
           and do_susep["susep_version_id"] == "998877",
           "o rótulo e o id de download vêm junto", str(do_susep))

    # CONTROLE 1 — sem SUSEP, a MESMA chamada cai no texto do documento e
    # MARCA a queda. Sem esta linha, o teste acima passaria igual se a função
    # devolvesse 'susep_rep2' sempre.
    do_texto = corpus.InsuranceCorpusService._vigencia_da_versao(
        _documento(), TEXTO, None)
    checar(do_texto["effective_from"] == "2024-07-01"
           and do_texto["fonte"] == "texto_do_documento",
           "CONTROLE: sem SUSEP, a data vem do PDF e a fonte muda",
           str(do_texto))

    # CONTROLE 2 — sem SUSEP e sem data no texto: `indeterminado`, e NENHUMA
    # data. A §3.3 manda registrar `indeterminado`, nunca "não mudou".
    do_nada = corpus.InsuranceCorpusService._vigencia_da_versao(
        _documento(), "texto sem data nenhuma", None)
    checar(do_nada["effective_from"] is None
           and do_nada["fonte"] == "indeterminado",
           "CONTROLE 2: sem nada, `indeterminado` e data NULA", str(do_nada))

    # CONTROLE 3 — o degrau do texto NUNCA escreve effective_until. Um fim de
    # comercialização inventado tiraria da busca um documento que ainda vale.
    checar(do_texto["effective_until"] is None and do_nada["effective_until"] is None,
           "CONTROLE 3: fora da SUSEP, `effective_until` fica NULO",
           f"{do_texto['effective_until']!r} / {do_nada['effective_until']!r}")

    # CONTROLE 4 — e a SUSEP CONSEGUE escrevê-lo. Sem esta linha, "nunca
    # escreve" seria indistinguível de "a coluna não é escrita por ninguém".
    encerrado = corpus.InsuranceCorpusService._vigencia_da_versao(
        _documento(), TEXTO, {**SUSEP, "effective_until": "2026-12-31"})
    checar(encerrado["effective_until"] == "2026-12-31",
           "CONTROLE 4: com a Data de Fim da SUSEP, ela É escrita",
           str(encerrado["effective_until"]))


# ── 2. a vigência é gravada na versão ─────────────────────────────────────────

def teste_a_versao_recebe_a_vigencia_e_o_documento_recebe_o_espelho():
    print("\n[2] A verdade na versão; o espelho no documento")
    db = BancoDeMentira(versoes=[_versao(1)])
    r = _ingerir(db, vigencia_susep=SUSEP)
    checar(r["ok"] and r["versao"] == 2, "a captura virou a versão 2", str(r))

    nova = db.gravadas("insert", "normative_document_versions")[0][2]
    checar(nova["effective_from"] == "2026-07-01"
           and nova["version_label"] == "CG144"
           and nova["vigencia_fonte"] == "susep_rep2"
           and nova["susep_version_id"] == "998877",
           "a versão nova nasce com a vigência do registro oficial", str(nova))

    espelho = db.gravadas("update", "normative_documents")[-1][2]
    checar(espelho["effective_from"] == "2026-07-01"
           and espelho["version_label"] == "CG144",
           "e `normative_documents` recebe o espelho — 📊 estava NULL em 35/35",
           str({k: espelho.get(k) for k in
                ("effective_from", "effective_until", "version_label")}))

    # CONTROLE — o espelho é ESCRITO, não herdado. Com outra vigência, ele
    # muda. Sem esta linha, um espelho que copiasse o valor antigo (None)
    # passaria no teste acima quando o valor antigo por acaso coincidisse.
    db2 = BancoDeMentira(versoes=[_versao(1)])
    _ingerir(db2, vigencia_susep={**SUSEP, "effective_from": "2025-01-15",
                                  "version_label": "CG139"})
    espelho2 = db2.gravadas("update", "normative_documents")[-1][2]
    checar(espelho2["effective_from"] == "2025-01-15"
           and espelho2["version_label"] == "CG139",
           "CONTROLE: outra vigência produz outro espelho", str(espelho2["effective_from"]))


# ── 3. quem fecha a anterior ──────────────────────────────────────────────────

def teste_a_anterior_e_fechada_antes_de_a_nova_ser_aberta():
    print("\n[3] A ordem não é estética — é o índice único parcial")
    db = BancoDeMentira(versoes=[_versao(1)])
    _ingerir(db, vigencia_susep=SUSEP)

    das_versoes = [a for a, t in db.ordem() if t == "normative_document_versions"]
    checar(das_versoes[:2] == ["update", "insert"],
           "fecha (update) e SÓ DEPOIS abre (insert)", str(das_versoes))

    fecha = db.gravadas("update", "normative_document_versions")[0]
    checar(fecha[2].get("superseded_at") is not None,
           "a anterior ganha `superseded_at` — 📊 estava em ZERO de 29",
           str(fecha[2]))
    checar(fecha[4] == ("version", 2) and fecha[5] == ("superseded_at", "null"),
           "e só as versões anteriores AINDA ABERTAS são tocadas", str(fecha[4:6]))

    # CONTROLE — a PRIMEIRA captura não fecha nada. Um fechador que dispara
    # sempre não encadeia versão: ele fecharia a própria linha que acabou de
    # nascer, e o índice parcial passaria a recusar a captura seguinte.
    db2 = BancoDeMentira(versoes=[])
    r2 = _ingerir(db2, vigencia_susep=SUSEP)
    checar(r2["primeira"] and r2["versao"] == 1,
           "CONTROLE: sem versão anterior, é a primeira", str(r2["versao"]))
    checar(db2.gravadas("update", "normative_document_versions") == [],
           "CONTROLE 2: e nenhum fechamento é escrito",
           str(db2.gravadas("update", "normative_document_versions")))


def teste_superseded_e_effective_until_nao_sao_a_mesma_data():
    print("\n[4] Um fato nosso e um fato da SUSEP, em colunas diferentes")

    # Sem Data de Fim publicada: fecha o NOSSO lado e só.
    db = BancoDeMentira(versoes=[_versao(1)])
    _ingerir(db, vigencia_susep={**SUSEP, "fim_da_anterior": None})
    fecha = db.gravadas("update", "normative_document_versions")[0][2]
    checar(fecha.get("superseded_at") is not None,
           "sem Data de Fim, `superseded_at` é escrito assim mesmo", str(fecha))
    checar("effective_until" not in fecha,
           "e `effective_until` NÃO é inventado — é a escada que a §3.2 proíbe",
           str(fecha))

    # CONTROLE — com a Data de Fim publicada, ela É gravada, com a procedência.
    # Sem esta linha, "não inventa" seria indistinguível de "nunca escreve".
    db2 = BancoDeMentira(versoes=[_versao(1)])
    _ingerir(db2, vigencia_susep=SUSEP)
    fecha2 = db2.gravadas("update", "normative_document_versions")[0][2]
    checar(fecha2.get("effective_until") == "2026-06-30"
           and fecha2.get("vigencia_fonte") == "susep_rep2",
           "CONTROLE: com a Data de Fim da SUSEP, ela é gravada na anterior",
           str(fecha2))
    checar(fecha2.get("superseded_at") is not None,
           "CONTROLE 2: e `superseded_at` continua sendo escrito junto",
           str(fecha2))


# ── 4. a migration existe e diz o que faz ─────────────────────────────────────

MIGRACOES = {
    "20260808_01_spec070_a_vigencia_mora_na_versao.sql":
        ("normative_versao_aberta_uk", "vigencia_fonte"),
    "20260808_02_spec070_o_indice_sabe_de_que_versao_veio.sql":
        ("qdrant_doc_id", "norm-' || v.document_id"),
    "20260808_03_spec070_a_carta_sabe_de_que_contrato_saiu.sql":
        ("source_document_id", "on delete restrict"),
    "20260808_04_spec070_o_pdf_e_o_texto_tem_endereco.sql":
        ("text_storage_ref", "arquivado_em"),
}


def teste_toda_migration_tem_apply_verify_e_rollback():
    print("\n[5] APPLY / VERIFY / ROLLBACK escritos ANTES (CLAUDE.md §8)")
    pasta = RAIZ / "supabase" / "migrations"
    for nome, marcas in MIGRACOES.items():
        caminho = pasta / nome
        checar(caminho.exists(), f"{nome[:34]}… existe", str(caminho))
        if not caminho.exists():
            continue
        fonte = caminho.read_text(encoding="utf-8")
        for exigido in ("APPLY:", "VERIFY:", "ROLLBACK:"):
            checar(exigido in fonte, f"{nome[13:34]}… declara {exigido}")
        checar("if not exists" in fonte.lower() or "if exists" in fonte.lower(),
               f"{nome[13:34]}… é idempotente")
        for marca in marcas:
            checar(marca in fonte, f"{nome[13:34]}… faz o que promete ({marca[:24]})")

    # CONTROLE — a busca CONSEGUE não achar. Sem isto, um `in` sobre string
    # vazia (arquivo ausente lido como "") passaria em tudo acima.
    checar("normative_versao_aberta_uk" not in
           (pasta / "20260808_04_spec070_o_pdf_e_o_texto_tem_endereco.sql")
           .read_text(encoding="utf-8"),
           "CONTROLE: a conferência sabe dizer NÃO — a 04 não cria o guarda da 01")


def teste_nenhuma_migration_nova_foi_aplicada_no_banco():
    print("\n[6] Escritas, não aplicadas — quem aplica é o Founder")
    manifesto = (RAIZ / "supabase" / "migrations" / "MANIFEST.md").read_text(
        encoding="utf-8")
    checar("não aplicada" in manifesto,
           "o MANIFEST declara as migrations da SPEC-067 como não aplicadas")
    checar("SEM_ARQUIVO" in manifesto and "spec057_h1_normative_corpus" in manifesto,
           "e registra as duas tabelas do acervo como SEM_ARQUIVO")

    # CONTROLE — o DDL reconstruído existe e se declara proibido de aplicar.
    ddl = (RAIZ.parent / "docs" / "canon" / "sql" / "reconstruidas"
           / "20260725215808_spec057_h1_normative_corpus.sql")
    checar(ddl.exists(), "CONTROLE: o DDL reconstruído foi escrito", str(ddl))
    if ddl.exists():
        texto = ddl.read_text(encoding="utf-8")
        checar("PROIBIDO APLICAR" in texto,
               "CONTROLE 2: e ele se declara proibido de aplicar")
        checar("normative_versions_append_only" in texto,
               "CONTROLE 3: e traz o gatilho real, lido do catálogo")


def main() -> int:
    print("=" * 74)
    print("A VIGÊNCIA MORA NA VERSÃO — E A ANTERIOR É FECHADA POR QUEM ABRE")
    print("=" * 74)
    for teste in (teste_a_susep_ganha_do_texto_e_o_texto_ganha_do_nada,
                  teste_a_versao_recebe_a_vigencia_e_o_documento_recebe_o_espelho,
                  teste_a_anterior_e_fechada_antes_de_a_nova_ser_aberta,
                  teste_superseded_e_effective_until_nao_sao_a_mesma_data,
                  teste_toda_migration_tem_apply_verify_e_rollback,
                  teste_nenhuma_migration_nova_foi_aplicada_no_banco):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("A DATA DA SUSEP É GRAVADA NA VERSÃO; A ANTERIOR FECHA; NADA É INVENTADO")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
