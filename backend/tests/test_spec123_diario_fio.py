# -*- coding: utf-8 -*-
"""SPEC-123 F4 — O TESTE DO FIO do diário de decisões.

O fio, elo a elo, com o MOTOR real em cada elo (dublê só na borda: o banco em memória, com
as COLUNAS do banco real e as travas da migration `20260930_04`):

  diario_de_decisoes.registrar_decisao          (o que o destravador chama — F1a)
    → a linha mascarada + o evento curto `cerebro.decisao` em work_events (dispatch_router._evento)
    → GET /api/dashboard/decisoes como a corretora A (vê) e como a B (não vê)   ← a ROTA REAL, em node
    → POST "errado" + "o certo era…" pela dona (a B recebe 404)
    → scripts/diario_para_bancada.exportar      → pendentes.jsonl (nunca casos.jsonl), sem PII
    → diario_de_decisoes.propor_carta_sync      → carta `proposta_diario` com card_hash
    → curadoria_cartas.publicar_lote_sync       → NÃO publica a proposta (e publica o controle)

Duas corretoras REAIS: os `company_id` vêm de um SELECT read-only no banco (sem nome — §13.9).
Sem banco na máquina, o teste do fio PULA (e diz por quê); os guardas de unidade rodam igual.

    cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec123_diario_fio.py -q
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPO = RAIZ.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))
sys.path.insert(0, str(RAIZ / "scripts"))

from app.services import diario_de_decisoes as D  # noqa: E402

MIGRATION = RAIZ / "supabase" / "migrations" / "20260930_04_spec123_diario_de_decisoes.sql"


# ─────────────────────────────────────────────────────────────────────────────
# O banco REAL — só leitura (colunas, CHECKs e duas corretoras)
# ─────────────────────────────────────────────────────────────────────────────
def _dsn():
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        try:
            from dotenv import load_dotenv

            load_dotenv(RAIZ / ".env")
        except Exception:  # noqa: BLE001
            pass
        dsn = os.environ.get("SUPABASE_DB_URL")
    return dsn


@pytest.fixture(scope="module")
def banco():
    dsn = _dsn()
    if not dsn:
        pytest.skip("SUPABASE_DB_URL ausente: o fio precisa das colunas e de duas corretoras REAIS")
    try:
        import psycopg
    except ImportError:
        pytest.skip("psycopg (v3) não instalado")
    with psycopg.connect(dsn, prepare_threshold=None) as c:
        with c.cursor() as cur:
            # 🔴 NUNCA `SET` de sessão pelo pooler: só a transação é read only.
            cur.execute("begin; set transaction read only")
            cur.execute("select table_name, column_name from information_schema.columns "
                        "where table_schema='public' and table_name = any(%s)",
                        (["diario_de_decisoes", "work_events", "knowledge_cards", "work_runs"],))
            colunas = {}
            for t, col in cur.fetchall():
                colunas.setdefault(t, set()).add(col)
            cur.execute("select conname, pg_get_constraintdef(oid) from pg_constraint "
                        "where conrelid='public.diario_de_decisoes'::regclass and contype='c'")
            checks = dict(cur.fetchall())
            cur.execute("select id from companies order by id limit 2")
            empresas = [str(r[0]) for r in cur.fetchall()]
            cur.execute("rollback")
    assert len(empresas) == 2, "o fio precisa de DUAS corretoras reais"
    return {"colunas": colunas, "checks": checks, "A": empresas[0], "B": empresas[1]}


# ─────────────────────────────────────────────────────────────────────────────
# A borda: o banco em memória, com as colunas REAIS e as travas da migration
# ─────────────────────────────────────────────────────────────────────────────
class ErroDoBanco(Exception):
    pass


class Mundo:
    def __init__(self, colunas=None):
        self.t = {}
        self.colunas = colunas or {}
        self.registro = []

    def rows(self, nome):
        return self.t.setdefault(nome, [])

    def _travas(self, nome, linha):
        cols = self.colunas.get(nome)
        if cols:
            desconhecidas = set(linha) - cols
            if desconhecidas:  # o PGRST204 do PostgREST
                raise ErroDoBanco(f"coluna inexistente em {nome}: {sorted(desconhecidas)}")
        if nome == "diario_de_decisoes":
            for c in ("company_id", "chave_idempotencia", "origem", "classe", "acao", "modo",
                      "explicacao_para_gente"):
                if not linha.get(c):
                    raise ErroDoBanco(f"not null: {c}")
            if linha["origem"] not in D.ORIGENS or linha["classe"] not in D.CLASSES \
                    or linha["acao"] not in D.ACOES or linha["modo"] not in D.MODOS:
                raise ErroDoBanco("check lista fechada")
            if linha["modo"] == "sombra" and linha["acao"] != "nao_agiu":
                raise ErroDoBanco("ck_diario_sombra_nao_agiu")
            if linha.get("veredito") == "errado" and len((linha.get("o_certo_era") or "").strip()) < 3:
                raise ErroDoBanco("ck_diario_errado_tem_o_certo")
            if linha.get("limiar") is not None and not (70 <= linha["limiar"] <= 100):
                raise ErroDoBanco("ck_diario_limiar")
            run = linha.get("work_run_id")
            if run and not any(r["id"] == run and r["company_id"] == linha["company_id"]
                               for r in self.rows("work_runs")):
                raise ErroDoBanco("fk_diario_run_mesma_corretora")


class Q:
    def __init__(self, mundo, nome, assincrono):
        self.m, self.nome, self.async_ = mundo, nome, assincrono
        self.op, self.payload, self.pred, self.lim, self.upsert_ = "select", None, [], None, None
        mundo.registro.append(self)

    def select(self, *_a, **_k):
        return self

    def insert(self, p):
        self.op, self.payload = "insert", p
        return self

    def update(self, p):
        self.op, self.payload = "update", p
        return self

    def upsert(self, p, on_conflict=None, ignore_duplicates=False):
        self.op, self.payload, self.upsert_ = "upsert", p, (on_conflict, ignore_duplicates)
        return self

    def eq(self, c, v):
        self.pred.append(("eq", c, v))
        return self

    def is_(self, c, v):
        self.pred.append(("is", c, v))
        return self

    def in_(self, c, v):
        self.pred.append(("in", c, v))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self.lim = n
        return self

    def _casa(self, l):
        for op, c, v in self.pred:
            x = l.get(c)
            if op == "eq" and str(x) != str(v):
                return False
            if op == "is" and not (x is None if v in (None, "null") else x == v):
                return False
            if op == "in" and str(x) not in [str(i) for i in v]:
                return False
        return True

    def _rodar(self):
        rows = self.m.rows(self.nome)
        if self.op == "insert":
            linha = {"id": str(uuid.uuid4()), "created_at": "2026-09-30T12:00:00+00:00",
                     "resultado": "pendente", "veredito": None, "sugere_regra": False, **self.payload}
            self.m._travas(self.nome, self.payload)
            if self.nome == "diario_de_decisoes" and any(
                    r["company_id"] == linha["company_id"]
                    and r["chave_idempotencia"] == linha["chave_idempotencia"] for r in rows):
                raise ErroDoBanco("uq_diario_idempotencia")
            rows.append(linha)
            return [dict(linha)]
        if self.op == "upsert":
            self.m._travas(self.nome, self.payload)
            chave = self.upsert_[0]
            if any(r.get(chave) == self.payload.get(chave) for r in rows):
                return []
            linha = {"id": str(uuid.uuid4()), "created_at": "2026-09-30T12:00:00+00:00", **self.payload}
            rows.append(linha)
            return [dict(linha)]
        alvo = [r for r in rows if self._casa(r)]
        if self.op == "update":
            cols = self.m.colunas.get(self.nome)
            if cols and set(self.payload) - cols:
                raise ErroDoBanco(f"coluna inexistente em {self.nome}: {sorted(set(self.payload) - cols)}")
            for r in alvo:
                novo = {**r, **self.payload}
                if self.nome == "diario_de_decisoes":
                    self.m._travas(self.nome, novo)
                r.update(self.payload)
            return [dict(r) for r in alvo]
        if self.lim is not None:
            alvo = alvo[: self.lim]
        return [dict(r) for r in alvo]

    def execute(self):
        res = type("R", (), {"data": self._rodar()})()
        if self.async_:
            async def _a():
                return res
            return _a()
        return res


class Banco:
    def __init__(self, mundo, assincrono):
        self.client = self
        self.m, self.a = mundo, assincrono

    def table(self, nome):
        return Q(self.m, nome, self.a)


# ─────────────────────────────────────────────────────────────────────────────
# Guardas de unidade (sem banco)
# ─────────────────────────────────────────────────────────────────────────────
def test_a_frase_e_de_gente():
    f = D.frase_para_gente(seguradora="porto", tela="*Qual a amperagem da bateria?*\n1 - 40A\n2 - 60A",
                           classe="responder_com_dado", acao="respondeu_ura", valor="60A", nota=88,
                           segunda_opiniao={"concordou": True}, motivo="nota_alta_sem_chute")
    assert f.startswith('Porto Seguro perguntou "Qual a amperagem da bateria?".'), f
    assert 'O agente respondeu "60A"' in f and "certeza 88%" in f and "segunda opinião concordou" in f, f
    # D7: nenhum nome de variável, nenhuma chave de classe, nenhuma marca de mascarador
    assert not re.search(r"\w+_\w+|\{[A-Z]", f), f
    for acao, trecho in (("perguntou_segurado", "perguntou ao segurado"), ("chamou_pessoa", "chamou uma pessoa"),
                         ("nao_agiu", "apenas observou")):
        g = D.frase_para_gente(seguradora="hdi", tela="Confirma? ", classe="deduzir", acao=acao,
                               valor="{PLACA}", nota=None, segunda_opiniao=None, motivo="")
        assert trecho in g and not re.search(r"\w+_\w+|\{[A-Z]", g), g


def test_as_listas_batem_com_o_banco(banco):
    """As constantes do serviço são as MESMAS dos CHECKs do banco (não duas verdades)."""
    defs = banco["checks"]
    for nome, lista in (("ck_diario_origem", D.ORIGENS), ("ck_diario_classe", D.CLASSES),
                        ("ck_diario_acao", D.ACOES), ("ck_diario_modo", D.MODOS)):
        achados = set(re.findall(r"'(\w+)'::text", defs[nome]))
        assert achados == set(lista), (nome, achados, lista)
    achados = set(re.findall(r"'(\w+)'::text", defs["ck_diario_resultado"]))
    # SPEC-125 S6: os sinais de erro leve da conversa entraram na mesma lista (migration 20261001_05)
    assert achados == {"pendente", *D.RESULTADOS_FINAIS, *D.SINAIS_DE_ERRO_LEVE}, achados
    assert len(defs) == 18, sorted(defs)        # 16 da SPEC-123 + ck_diario_momento(_e_da_conversa) da SPEC-125


# ─────────────────────────────────────────────────────────────────────────────
# O TESTE DO FIO
# ─────────────────────────────────────────────────────────────────────────────
def _registrar(A, run, chave, **k):
    base = dict(company_id=A, origem="acionamento", work_run_id=run, conversation_id=None,
                seguradora="porto", ramo="auto", rota="porto-auto-whatsapp@v1", servico="guincho",
                tela="Sr. Marcelino Tavares, confirme a placa XYZ1A23 do veículo?\n1 - Sim\n2 - Não",
                classe="responder_com_dado", acao="respondeu_ura", valor="1", nota=91, limiar=70,
                motivo="a placa do caso confere", explicacao_para_gente="", modelo="gpt-6.1-sol",
                segunda_opiniao=None, modo="on", gatilho="conferencia_divergente:placa",
                chave_idempotencia=chave,
                sessao={"slots": {"segurado_nome": "Marcelino Tavares", "placa": "XYZ1A23"}})
    base.update(k)
    return asyncio.run(D.registrar_decisao(**base))


def test_o_fio_do_diario(banco, monkeypatch, tmp_path):
    A, B = banco["A"], banco["B"]
    mundo = Mundo(banco["colunas"])
    run_a, run_b = str(uuid.uuid4()), str(uuid.uuid4())
    mundo.rows("work_runs").extend([{"id": run_a, "company_id": A}, {"id": run_b, "company_id": B}])
    banco_async = Banco(mundo, assincrono=True)

    async def _cliente():
        return banco_async

    monkeypatch.setattr(D, "_cliente", _cliente)

    # ① registrar — A e B com a MESMA chave (a idempotência é por corretora: sem o filtro, a B
    #    receberia o id da A e ficaria sem linha — o GET da B abaixo ficaria vazio).
    chave = "destrava:porto:tela-igual-nas-duas"
    id_a = _registrar(A, run_a, chave)
    id_b = _registrar(B, run_b, chave, seguradora="hdi", classe="deduzir", nota=77)
    assert id_a and id_b and id_a != id_b, (id_a, id_b)
    assert _registrar(A, run_a, chave) == id_a, "idempotência: a mesma decisão não vira duas linhas"
    diario = mundo.rows("diario_de_decisoes")
    assert len(diario) == 2, len(diario)
    la = next(l for l in diario if l["id"] == id_a)
    # SPEC-125 S6 (ordem do Founder): o texto COMPLETO mora SÓ em `tela_completa`/`valor_completo`
    # (a corretora dona lê); TODA outra coluna continua mascarada — a lição migra, não morre (§9.3).
    assert "XYZ1A23" in la["tela_completa"]
    texto = json.dumps({k: v for k, v in la.items() if k not in ("tela_completa", "valor_completo")},
                       ensure_ascii=False)
    assert "XYZ1A23" not in texto and "Marcelino" not in texto and "Tavares" not in texto, texto
    assert la["company_id"] == A and la["work_run_id"] == run_a and la["tela_hash"]
    assert "Porto Seguro" in la["explicacao_para_gente"] and not re.search(r"\w+_\w+|\{[A-Z]",
                                                                          la["explicacao_para_gente"])
    eventos = [e for e in mundo.rows("work_events") if e["event_type"] == D.EVENTO]
    assert len(eventos) == 2, eventos                      # um por decisão NOVA, nunca na repetição
    ev_a = next(e for e in eventos if e["company_id"] == A)
    assert ev_a["payload_redacted"] == {"diario_id": id_a} and ev_a["work_run_id"] == run_a

    # ①b o ponteiro de OUTRA corretora é recusado — a decisão fica, sem o ponteiro
    id_x = _registrar(A, run_b, "destrava:ponteiro-cruzado")
    lx = next(l for l in diario if l["id"] == id_x)
    assert lx["company_id"] == A and lx["work_run_id"] is None

    # ② o que aconteceu depois — só nas linhas DAQUELE acionamento DAQUELA corretora
    assert asyncio.run(D.marcar_resultado(company_id=B, work_run_id=run_a, resultado="protocolo_saiu")) == 0
    assert asyncio.run(D.marcar_resultado(company_id=A, work_run_id=run_a, resultado="protocolo_saiu")) == 1
    assert la["resultado"] == "protocolo_saiu" and la["resultado_em"]
    for q in mundo.registro:
        if q.nome == "diario_de_decisoes" and q.op in ("select", "update"):
            assert any(p[0] == "eq" and p[1] == "company_id" for p in q.pred), \
                f"🔴 consulta ao diário SEM filtro de corretora: {q.op} {q.pred}"

    # ③ a ROTA REAL da corretora, em node: A vê, B não vê, B não avalia, A marca "errado"
    entrada, saida = tmp_path / "fio_in.json", tmp_path / "fio_out.json"
    linhas = [l for l in diario if l["id"] in (id_a, id_b)]
    entrada.write_text(json.dumps({"A": A, "B": B, "idA": id_a, "idB": id_b, "linhas": linhas},
                                  ensure_ascii=False), encoding="utf-8")
    p = subprocess.run(["node", str(REPO / "scripts" / "o-diario-e-de-quem-decidiu.test.mjs"), "--fio",
                        str(entrada), str(saida)], capture_output=True, text=True, encoding="utf-8",
                       cwd=str(REPO), timeout=120)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-2000:]
    volta = json.loads(saida.read_text(encoding="utf-8"))
    assert id_a in volta["vistos"]["gA"] and id_a not in volta["vistos"]["gB"], volta["vistos"]
    depois = {l["id"]: l for l in volta["linhas"]}
    assert depois[id_a]["veredito"] == "errado" and depois[id_a]["o_certo_era"], depois[id_a]
    assert depois[id_b]["veredito"] is None
    for l in diario:                                        # o banco em memória recebe o POST
        if l["id"] in depois:
            l.update(depois[l["id"]])
    # o POST que veio pela rota passa nas travas do banco (errado ⇒ o certo)
    mundo._travas("diario_de_decisoes", next(l for l in diario if l["id"] == id_a))

    # ③b a corretora escreveu PII no "o certo era" — a bancada não pode levar
    next(l for l in diario if l["id"] == id_a)["o_certo_era"] = (
        "Responder 1: a placa XYZ1A23 confere, CPF 123.456.789-09, processo 31.26.123456.01")

    # ④ o errado vira caso PENDENTE de bancada (nunca casos.jsonl), sem PII
    import diario_para_bancada as DB
    from test_spec116_bancada_corpus import CAMPOS, varrer_pii

    pendentes = tmp_path / "pendentes.jsonl"
    banco_sync = Banco(mundo, assincrono=False)
    with pytest.raises(ValueError):
        DB.exportar(banco_sync, company_id=A, aplicar=True, destino=tmp_path / "casos.jsonl")
    placar = DB.exportar(banco_sync, company_id=A, aplicar=True, destino=pendentes)
    assert placar["casos_novos"] == 1 and placar["carimbadas"] == 1, placar
    casos = [json.loads(l) for l in pendentes.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(casos) == 1
    caso = casos[0]
    for campo in CAMPOS:
        assert campo in caso, campo
    assert caso["origem"] == f"diario {id_a}" and caso["papel"] == "cerebro"
    assert caso["oraculo"]["cerebro"]["aceitas"] == [caso["oraculo"]["cerebro"]["o_certo_era"]]
    assert varrer_pii(pendentes.read_text(encoding="utf-8")) == [], pendentes.read_text(encoding="utf-8")
    la = next(l for l in diario if l["id"] == id_a)
    assert la["virou_caso_em"] and la["caso_chave"] == caso["chave"]
    assert DB.exportar(banco_sync, company_id=A, aplicar=True, destino=pendentes)["casos_novos"] == 0
    assert DB.exportar(banco_sync, company_id=B, aplicar=True, destino=pendentes)["casos_novos"] == 0

    # ⑤ o master vira rascunho de carta — `proposta_diario`, com card_hash
    r = D.propor_carta_sync(id_a, db=banco_sync)
    assert r["ok"] and r["carta_id"], r
    carta = next(c for c in mundo.rows("knowledge_cards") if c["id"] == r["carta_id"])
    assert carta["status"] == D.STATUS_DA_CARTA_DO_DIARIO == "proposta_diario"
    assert carta["card_hash"] == hashlib.md5(carta["card_text"].lower().encode("utf-8")).hexdigest()
    assert "XYZ1A23" not in carta["card_text"] and "123.456.789-09" not in carta["card_text"], carta
    assert la["carta_rascunho_id"] == r["carta_id"]
    assert D.propor_carta_sync(id_a, db=banco_sync)["motivo"] == "ja_existia"
    assert D.propor_carta_sync(id_b, db=banco_sync)["motivo"] == "so_decisao_errada_vira_carta"

    # ⑥ o publicador AUTOMÁTICO não publica a proposta — e publica o controle `pending_review`
    controle = {"id": str(uuid.uuid4()), "card_hash": "controle", "status": "pending_review",
                "card_text": "Na assistência 24h do seguro auto, o guincho atende até 200 km por acionamento.",
                "insurer_key": None, "ramo": "auto", "category": None, "source_unit_id": None,
                "pii_check": {}, "temas": None}
    mundo.rows("knowledge_cards").append(controle)
    from app.core import database as DBmod
    from app.services import attendance_distiller as AD
    from app.services import curadoria_cartas as CC

    monkeypatch.setattr(DBmod, "get_supabase_client", lambda: banco_sync)
    monkeypatch.setattr(AD, "publish_card_sync", lambda c: True)
    monkeypatch.setattr(CC, "reconciliar_indice_sync", lambda *a, **k: {"limpas": 0, "falhas": 0})
    lote = CC.publicar_lote_sync()
    assert controle["status"] == "published", ("CONTROLE: o publicador tinha de publicar a pending_review", lote)
    assert carta["status"] == "proposta_diario", "🔴 a proposta do diário foi PUBLICADA sozinha"
    assert lote["publicadas"] == 1, lote


def test_a_bancada_so_le_casos_jsonl():
    """`pendentes.jsonl` fica fora da bancada até alguém revisar (o carregador só lê casos.jsonl)."""
    from app.services.evals import bancada as B

    assert all(not str(c.get("origem", "")).startswith("diario ") for c in B.carregar_casos("cerebro"))
    assert (RAIZ / "tests" / "corpus" / "bancada" / "cerebro" / "pendentes.jsonl").exists()


def test_o_admin_do_backend_aceita_a_proposta_e_vira_carta(monkeypatch):
    """O espelho lista `proposta_diario`, recusa status inventado, e o botão do master chega ao serviço."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import admin_atlas as AA
    from app.core import database as DBmod
    from app.core.auth import require_master_admin

    mundo = Mundo()
    mundo.rows("knowledge_cards").extend([
        {"id": "c1", "status": "proposta_diario", "card_text": "x", "created_at": "2026-09-30"},
        {"id": "c2", "status": "pending_review", "card_text": "y", "created_at": "2026-09-30"}])
    monkeypatch.setattr(DBmod, "get_supabase_client", lambda: Banco(mundo, assincrono=False))
    chamadas = []
    monkeypatch.setattr(D, "propor_carta_sync",
                        lambda i: chamadas.append(i) or ({"ok": True, "carta_id": "c9", "motivo": "criada"}
                                                         if i == "ok" else {"ok": False, "motivo": "decisao_nao_encontrada"}))
    app = FastAPI()
    app.include_router(AA.router)
    app.dependency_overrides[require_master_admin] = lambda: {"master": True}
    cli = TestClient(app)
    r = cli.get("/api/admin/atlas/espelho/cards", params={"status": "proposta_diario"})
    assert r.status_code == 200 and [c["id"] for c in r.json()["cards"]] == ["c1"], r.text
    assert cli.get("/api/admin/atlas/espelho/cards", params={"status": "chute"}).status_code == 400
    assert cli.post("/api/admin/atlas/diario/ok/carta").json()["carta_id"] == "c9"
    assert cli.post("/api/admin/atlas/diario/nao/carta").status_code == 404
    assert chamadas == ["ok", "nao"]
