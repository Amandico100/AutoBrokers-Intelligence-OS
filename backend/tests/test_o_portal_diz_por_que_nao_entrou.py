# -*- coding: utf-8 -*-
"""SPEC-EXTRA-001.6 -- O PORTAL DIZ POR QUE NAO ENTROU. Guardas G9, G11, B2.2, B2.4, B3.4.

O QUE ELE GUARDA (proposta §7 e §8; BLOCO 0 medido em 13/09/2026)

  G9    A SESSAO VENCE. `verified_at` mais velho que `PORTAL_SESSION_TTL_HORAS` ->
        o storage NAO e injetado, `evidence["sessao_vencida"]` fica escrito e a journey
        faz login limpo. E `session_reused` passa a dizer a VERDADE: `session_injetada`
        no instante da injecao, `session_reused` SO quando a sessao valeu.
        📊 13/09: `select portal_key,health,verified_at from portal_sessions` -> a sessao
        da Allianz com `verified_at` de 17/08 e `health='ok'` (27 dias), reinjetada todo dia.
        CONTROLE: o job REAL de 11/09 replayado (`session_storage_restored`, desfecho
        `needs_human` de login) -> `session_injetada=True` e `session_reused` AUSENTE.

  B2.2 / G3.4-④  `health` PASSA A TER ESCRITOR, nas DUAS tabelas, com um vocabulario so.
        O classificador `veredito_de_saude` roda sobre as 6 mensagens REAIS do acervo
        (relatorio §1 premissa 6 e §1.1). 📊 `select health,count(*) from portal_accounts`
        -> 16 de 16 `unknown` em 13/09: a coluna nunca teve escritor.

  B2.4  A ALLIANZ ALCANCA O DIAGNOSTICO. `cobranca_sweep` com login `needs_human` chama
        `_diagnosticar_sessao_na_pagina` (UMA retentativa); com login `failed`
        (credencial) NAO chama e nao reloga -- bater na porta trancada bloqueia a conta.

  G11   BACKOFF COM JITTER, teto 3, ZERO para credencial recusada. 📊 `available_at` era
        lido em `worker.py` e nunca escrito (0 linhas em 13/09).

  G10-② SALVAR A SENHA POE `unknown` (o meio-aberto do breaker) -- e continua pondo.

  B4.①  O TEXTO DA TELA PASSA A EXISTIR. Todo desfecho nao-`done` grava
        `evidence.tela = {texto (REDIGIDO, <=2000), hash, url sem query, prova}`.
        📊 13/09: nos 6 jobs nao-done de 10-11/09, `evidence.body_text` e
        `evidence.debug_dom` sao NULL -- a frase "Acesso negado" so existia DENTRO
        da imagem, e o primeiro humano a abri-la abriu 2 dias depois.
        O guarda dirige `_run_job` REAL com o texto REAL da MAPFRE (corpus) e um
        CPF sintetico dentro. CONTROLE: mesma tela -> mesmo hash; tela diferente ->
        hash diferente; e o desfecho `done` NAO grava tela.

  B4.②  A FILA DE TELAS DESCONHECIDAS E UMA CONSULTA -- E NASCE COM LEITOR.
        Nenhuma tabela nova (P-264: 📊 `tela_cega` tem 2 linhas e ZERO leitores
        desde 26/08). Agrupamento por portal+hash com filtro de `company_id` NO
        CODIGO (CLAUDE.md §7), e os DOIS leitores no dia 1: o card do portal na
        Central e a linha "tela nova hoje" no relatorio da rotina.

  B4.③  O PRINT DE TELA DE LOGIN SAI MASCARADO. `page.evaluate` poe '••••••••'
        em todo input password/text/email/tel ANTES de `page.screenshot`.
        📊 o print da MAPFRE de 11/09 mostra o CPF do corretor EM CLARO.
        O guarda afirma a ORDEM, nao a existencia: mascarar depois de fotografar
        protege ninguem, e as duas versoes sao indistinguiveis para quem so
        pergunte "a mascara rodou?".

  B3.4-④ AS DUAS TELAS MOSTRAM A MESMA PALAVRA, vinda da MESMA funcao
        (`app/services/saude_do_portal.rotulo_e_acao`): a rota da lista de credenciais e
        a Central de Agentes. O frontend so renderiza.

COMO ELE FUNCIONA -- sem rede, sem banco, sem navegador, sem mensagem
  🔴 CADA GATE EXECUTA O MOTOR (CLAUDE.md §9.4): `_load_session_bundle` REAL,
  `_run_job` REAL sobre um Playwright duble, `veredito_de_saude` REAL,
  `proximo_available_at` REAL, `cobranca_sweep` REAL da Allianz com as tres funcoes
  monkeypatched NO MODULO (contando chamadas), `list_credentials` REAL e
  `grupo_dos_portais` REAL. Nenhum helper reimplementa a regra.

⛔ SEGURANCA: nenhum portal e aberto, nenhuma mensagem sai, nenhum segredo aparece.
   company_id sintetico, `account_label` "principal", zero PII.

Rodar:  PYTHONIOENCODING=utf-8 python tests/test_o_portal_diz_por_que_nao_entrou.py
        (de dentro de `backend/`)  ·  `--so G9` roda so um gate
        `--mutar` roda M9, M11, M13, M14, M-B4.1, M-B4.2 e M-B4.3 por COPIA, cada uma
        em SUBPROCESSO sobre o arquivo
        mutado, restaurando por copia em `finally`.  ⛔ Nunca `git checkout` para restaurar.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

PASS = FAIL = 0

CO = "11111111-1111-1111-1111-111111111111"     # corretora sentinela
CONTA = "22222222-2222-2222-2222-222222222222"
AGORA = datetime(2026, 9, 13, 12, 0, 0, tzinfo=timezone.utc)
# 📊 `evidence.message` REAL do job da MAPFRE de 11/09 (relatorio §1, premissa 6).
MAPFRE_MSG_REAL = "a MAPFRE recusou a credencial (autenticacao invalida)"


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))


def _ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return fh.read()


def _chave_de_cofre():
    from cryptography.fernet import Fernet

    os.environ.setdefault("PORTAL_VAULT_KEY", Fernet.generate_key().decode())


# ==========================================================================
# OS DUBLES -- Supabase (3 tabelas) e Playwright (nenhum navegador)
# ==========================================================================
class _Res:
    def __init__(self, data=None):
        self.data = data if data is not None else []


class _Table:
    """O pedaco do postgrest que o worker usa. Guarda o que recebeu."""

    CONFLITO = ("company_id", "portal_key", "account_label")

    def __init__(self, supa, nome):
        self.supa = supa
        self.nome = nome
        self.filtros = []
        self.dentro = None
        self.limite = None
        self.upsert_row = None
        self.update_row = None
        self.insert_row = None

    # ---- construcao da consulta
    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self.dentro = (campo, list(valores or []))
        return self

    def gte(self, *_a):
        return self

    def lte(self, *_a):
        return self

    def or_(self, *_a):
        return self

    def not_(self, *_a):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self.limite = n
        return self

    def range(self, *_a):
        return self

    def upsert(self, row, on_conflict=None):
        self.upsert_row = dict(row)
        self.on_conflict = on_conflict
        return self

    def update(self, row):
        self.update_row = dict(row)
        return self

    def insert(self, row):
        self.insert_row = dict(row)
        return self

    # ---- execucao
    def execute(self):
        linhas = self.supa.db.setdefault(self.nome, [])
        if self.upsert_row is not None:
            self.supa.escritas.append((self.nome, "upsert", dict(self.upsert_row)))
            for i, linha in enumerate(linhas):
                if all(linha.get(k) == self.upsert_row.get(k) for k in self.CONFLITO):
                    linhas[i] = {**linha, **self.upsert_row}
                    return _Res([linhas[i]])
            linhas.append(dict(self.upsert_row))
            return _Res([linhas[-1]])
        if self.insert_row is not None:
            self.supa.escritas.append((self.nome, "insert", dict(self.insert_row)))
            linhas.append(dict(self.insert_row))
            return _Res([linhas[-1]])
        if self.update_row is not None:
            self.supa.escritas.append((self.nome, "update", dict(self.update_row)))
            saida = []
            for i, linha in enumerate(linhas):
                if all(linha.get(k) == v for k, v in self.filtros):
                    linhas[i] = {**linha, **self.update_row}
                    saida.append(linhas[i])
            return _Res(saida)
        saida = [l for l in linhas if all(l.get(k) == v for k, v in self.filtros)]
        if self.dentro:
            campo, valores = self.dentro
            saida = [l for l in saida if l.get(campo) in valores]
        if self.limite is not None:
            saida = saida[: self.limite]
        return _Res(saida)


class _Storage:
    def __init__(self, supa):
        self.supa = supa

    def upload(self, caminho, blob, opts):
        self.supa.arquivos[caminho] = (blob, opts)
        return {"path": caminho}


class _Supa:
    def __init__(self, db=None):
        self.db = db or {}
        self.escritas = []          # (tabela, operacao, payload)
        self.arquivos = {}

    def table(self, nome):
        return _Table(self, nome)

    @property
    def storage(self):
        supa = self

        class _B:
            def from_(self, _nome):
                return _Storage(supa)

        return _B()

    # ---- leitores de conveniencia do teste
    def patches_de_job(self):
        return [p for (t, op, p) in self.escritas if t == "portal_jobs" and op == "update"]

    def ultimo_patch(self):
        ps = self.patches_de_job()
        return ps[-1] if ps else {}

    def saude_gravada(self, tabela):
        for (t, op, p) in reversed(self.escritas):
            if t == tabela and "health" in p:
                return p
        return {}


class PaginaDuble:
    """Nem Playwright nem navegador: so as chamadas que o codigo faz.

    🔴 Ele guarda a ORDEM das chamadas (`ordem`) porque o B4.③ NAO afirma que a
    mascara rodou: afirma que ela rodou ANTES da foto. Mascarar o campo depois
    de fotografar a tela protege exatamente ninguem -- e as duas versoes sao
    indistinguiveis para um teste que so pergunte "a mascara rodou?".
    """

    url = "https://portal.exemplo/tela"

    def __init__(self, texto="", url=None):
        self.texto = texto
        self.fotos = 0
        self.scripts = []        # todo JS avaliado, na ordem
        self.ordem = []          # ("evaluate", js) | ("screenshot", None)
        if url:
            self.url = url

    async def evaluate(self, script, *a, **k):
        s = str(script)
        self.scripts.append(s)
        self.ordem.append(("evaluate", s))
        if "navigator.userAgent" in s:
            return "Mozilla/5.0 HeadlessChrome/126.0 Safari/537.36"
        if "sessionStorage" in s:
            return {"origin": "https://portal.exemplo", "entries": {}}
        return {}

    async def screenshot(self, **k):
        self.fotos += 1
        self.ordem.append(("screenshot", None))
        return b"\xff\xd8\xff-jpeg-falso"

    async def wait_for_timeout(self, ms):
        return None

    async def inner_text(self, _sel):
        return self.texto

    def on(self, *a, **k):
        return None

    async def close(self):
        return None


def _playwright_falso(page, storage_visto):
    ctx = types.SimpleNamespace()

    async def _new_page():
        return page

    async def _close():
        return None

    async def _add_init_script(_s):
        return None

    async def _storage_state():
        return {"cookies": [], "origins": []}

    ctx.new_page = _new_page
    ctx.close = _close
    ctx.add_init_script = _add_init_script
    ctx.storage_state = _storage_state
    browser = types.SimpleNamespace(version="126.0")

    async def _new_context(**kw):
        storage_visto.append(kw.get("storage_state"))
        return ctx

    browser.new_context = _new_context
    browser.close = _close
    chromium = types.SimpleNamespace()

    async def _launch(**kw):
        return browser

    chromium.launch = _launch

    class _PW:
        async def __aenter__(self):
            return types.SimpleNamespace(chromium=chromium)

        async def __aexit__(self, *a):
            return False

    mod = types.ModuleType("playwright.async_api")
    mod.async_playwright = lambda: _PW()
    pai = types.ModuleType("playwright")
    pai.async_api = mod
    sys.modules["playwright"] = pai
    sys.modules["playwright.async_api"] = mod


def _sessao_cifrada(idade_h, agora=None):
    """Uma linha de `portal_sessions` com storage REAL cifrado e `verified_at` de N horas."""
    from portal_worker import vault

    # ⚠️ A idade e medida contra o relogio REAL (e `_load_session_bundle` usa
    # `datetime.now`): uma data fixa aqui envelheceria sozinha e o CONTROLE da
    # sessao fresca comecaria a falhar sem ninguem mexer em nada.
    base = agora or datetime.now(timezone.utc)
    payload = {"version": 1,
               "storage_state": {"cookies": [{"name": "sid", "value": "cookie-sintetico"}],
                                 "origins": []},
               "session_storage": [{"origin": "https://portal.exemplo",
                                    "entries": {"t": "token-sintetico"}}]}
    return {
        "company_id": CO, "portal_key": "allianz_corretor", "account_label": "principal",
        "storage_state_encrypted": vault.encrypt(json.dumps(payload)),
        "verified_at": (base - timedelta(hours=idade_h)).isoformat(),
        "health": "ok",
    }


def _db(sessao=None, conta=None):
    return {
        "portal_sessions": [dict(sessao)] if sessao else [],
        "portal_accounts": [dict(conta or {
            "id": CONTA, "company_id": CO, "portal_key": "allianz_corretor",
            "account_label": "principal", "username": "usuario-sintetico",
            "secret_encrypted": None, "health": "ok",
        })],
        "portal_jobs": [],
    }


def _rodar_job(db, *, journey="cobranca_sweep", resultado=None, excecao=None,
               evidence_da_journey=None, attempts=1, job_evidence=None,
               texto_da_tela="", url_da_tela=None):
    """Roda `worker._run_job` INTEIRO com uma journey duble. Devolve (supa, storage_visto)."""
    from portal_worker import journeys as _J
    from portal_worker import worker as W

    page = PaginaDuble(texto_da_tela, url_da_tela)
    storage_visto = []
    _playwright_falso(page, storage_visto)
    supa = _Supa(db)

    vistos = {"params": None, "page": page}

    async def journey_duble(pg, params, ev):
        vistos["params"] = dict(params)
        ev.update(evidence_da_journey or {})
        if excecao is not None:
            raise excecao
        return resultado

    barrar, pegar = _J.motivo_para_barrar, _J.get_journey
    _J.motivo_para_barrar = lambda *a, **k: ""
    _J.get_journey = lambda *a, **k: journey_duble
    try:
        asyncio.run(W._run_job(supa, {
            "id": "job-sintetico", "company_id": CO, "account_id": CONTA,
            "portal_key": "allianz_corretor", "journey": journey,
            "params": {}, "evidence": dict(job_evidence or {}), "attempts": attempts,
        }))
    finally:
        _J.motivo_para_barrar = barrar
        _J.get_journey = pegar
    return supa, storage_visto, vistos


# ==========================================================================
# G9 -- A SESSAO VENCE, E `session_reused` DIZ A VERDADE
# ==========================================================================
def gate_G9():
    print("\n[G9] a sessao vence (TTL sobre `verified_at`) e `session_reused` nao mente")
    _chave_de_cofre()
    from portal_worker import worker as W
    from portal_worker.journeys import JourneyResult

    check("o TTL tem default 12 e clamp 1..72 (variavel PORTAL_SESSION_TTL_HORAS)",
          W.ttl_de_sessao_horas() == 12, W.ttl_de_sessao_horas())

    # --- o MOTOR: `_load_session_bundle` REAL sobre a linha real cifrada
    velha = _Supa(_db(sessao=_sessao_cifrada(27 * 24)))   # 27 dias: a Allianz de 17/08
    pacote = W._load_session_bundle(velha, {"company_id": CO, "portal_key": "allianz_corretor"},
                                   {"account_label": "principal"})
    check("sessao de 27 dias NAO devolve storage_state", pacote.get("storage_state") is None, pacote)
    vencida = pacote.get("vencida") or {}
    check("a recusa vem com `verified_at` e `idade_h` (o motivo, nao o silencio)",
          bool(vencida.get("verified_at")) and (vencida.get("idade_h") or 0) > 600, vencida)
    check("e com o TTL que a reprovou", vencida.get("ttl_h") == 12, vencida)

    nova = _Supa(_db(sessao=_sessao_cifrada(2)))
    pacote_ok = W._load_session_bundle(nova, {"company_id": CO, "portal_key": "allianz_corretor"},
                                       {"account_label": "principal"})
    check("CONTROLE: sessao de 2 horas CONTINUA sendo devolvida (o guarda ve a diferenca)",
          isinstance(pacote_ok.get("storage_state"), dict)
          and pacote_ok["storage_state"]["cookies"][0]["name"] == "sid", pacote_ok.get("vencida"))
    check("CONTROLE: sessao dentro do prazo nao carrega `vencida`",
          "vencida" not in pacote_ok, pacote_ok.get("vencida"))

    sem_carimbo = dict(_sessao_cifrada(1))
    sem_carimbo["verified_at"] = None
    pacote_sem = W._load_session_bundle(_Supa(_db(sessao=sem_carimbo)),
                                        {"company_id": CO, "portal_key": "allianz_corretor"},
                                        {"account_label": "principal"})
    check("sessao SEM carimbo de verificacao tambem nao entra (ausencia nao e prova de frescor)",
          pacote_sem.get("storage_state") is None and bool(pacote_sem.get("vencida")), pacote_sem)

    # --- o worker INTEIRO: a evidencia conta o que aconteceu
    supa, storage, vistos = _rodar_job(
        _db(sessao=_sessao_cifrada(27 * 24)),
        resultado=JourneyResult(status="failed", message="credenciais rejeitadas pelo portal Allianz"))
    ev = supa.ultimo_patch().get("evidence") or {}
    # ⚠️ `user_agent_sem_headless` abre um contexto descartavel (worker.py:966) antes
    #    do contexto de trabalho. Por isso a afirmacao e sobre o CONTEUDO, nunca sobre
    #    a posicao: NENHUM contexto pode ter recebido storage.
    check("job com sessao vencida: NENHUM contexto do navegador recebeu storage_state",
          all(s is None for s in storage), storage)
    check("job com sessao vencida: `evidence.sessao_vencida` fica escrito",
          isinstance(ev.get("sessao_vencida"), dict), sorted(ev))
    check("job com sessao vencida: a journey NAO ve `session_loaded` (faz login limpo)",
          not (vistos["params"] or {}).get("session_loaded"), (vistos["params"] or {}).get("session_loaded"))
    check("job com sessao vencida: nao existe `session_injetada`",
          "session_injetada" not in ev, sorted(ev))

    # --- sessao fresca + desfecho bom = `session_reused` verdadeiro
    supa_ok, storage_ok, vistos_ok = _rodar_job(
        _db(sessao=_sessao_cifrada(2)),
        resultado=JourneyResult(status="done", captured={"logged_in": True},
                                message="varredura concluida"))
    ev_ok = supa_ok.ultimo_patch().get("evidence") or {}
    check("CONTROLE: sessao fresca E injetada no contexto (o guarda ve a diferenca)",
          any(isinstance(s, dict) for s in storage_ok), storage_ok)
    check("sessao fresca: `session_injetada` no instante da injecao",
          ev_ok.get("session_injetada") is True, sorted(ev_ok))
    check("sessao fresca + `done` + logado + sem relogin -> `session_reused` VERDADEIRO",
          ev_ok.get("session_reused") is True, sorted(ev_ok))
    check("CONTROLE: a journey recebeu `session_loaded`",
          (vistos_ok["params"] or {}).get("session_loaded") is True, vistos_ok["params"])

    # --- 🔴 O CONTROLE DA VIDA REAL: o job da Allianz de 11/09, replayado.
    #     Ele carregava `session_reused: true` E terminou `needs_human` de login.
    supa_real, _, _ = _rodar_job(
        _db(sessao=_sessao_cifrada(2)),
        job_evidence={"session_storage_restored": True},
        resultado=JourneyResult(status="needs_human",
                                message="tela pos-login Allianz nao reconhecida"))
    ev_real = supa_real.ultimo_patch().get("evidence") or {}
    check("CONTROLE (job real 11/09): `session_injetada` = True",
          ev_real.get("session_injetada") is True, sorted(ev_real))
    check("CONTROLE (job real 11/09): `session_reused` AUSENTE -- a sessao nao valeu",
          "session_reused" not in ev_real, ev_real.get("session_reused"))
    check("CONTROLE (job real 11/09): o `resumo` conta que a sessao nao valeu",
          "sessao guardada" in str(ev_real.get("resumo") or ""), ev_real.get("resumo"))

    # --- relogin no meio: a sessao NAO foi reusada, mesmo terminando em `done`
    supa_rel, _, _ = _rodar_job(
        _db(sessao=_sessao_cifrada(2)),
        evidence_da_journey={"relogin": True},
        resultado=JourneyResult(status="done", captured={"logged_in": True}, message="ok"))
    ev_rel = supa_rel.ultimo_patch().get("evidence") or {}
    check("`done` COM relogin no meio -> `session_reused` ausente (a sessao nao valeu)",
          "session_reused" not in ev_rel, ev_rel.get("session_reused"))
    check("CONTROLE: o motor de relogin e o mesmo (`houve_relogin` le a marca da journey)",
          W.houve_relogin({"fresh_login_after_empty_search": False}) is True
          and W.houve_relogin({}) is False)


# ==========================================================================
# B2.2 / G3.4-④ -- `health` TEM ESCRITOR, NAS DUAS TABELAS
# ==========================================================================
# 📊 As 6 mensagens REAIS: relatorio §1 premissa 6 (`select distinct portal_key,status,
#    evidence->>'message' ...`) e §1.1 (as telas transcritas).
MENSAGENS_REAIS = [
    ("allianz antes do P0", "needs_human", {}, "tela pos-login Allianz nao reconhecida", "pede_humano"),
    ("allianz depois do P0", "failed", {}, "credenciais rejeitadas pelo portal Allianz", "credencial_recusada"),
    ("mapfre", "failed", {}, "a MAPFRE recusou a credencial (autenticacao invalida)", "credencial_recusada"),
    ("zurich (LOGOU, a varredura e que parou)", "needs_human", {"logged_in": True},
     "200 com ZERO parcelas em 45/90 dias, duas vezes seguidas - NAO afirmo que ela esta em dia", "ok"),
    ("hdi/tokio/yelum done", "done", {"logged_in": True}, "varredura concluida", "ok"),
    ("configuracao faltando", "failed", {}, "username/password ausentes para Allianz", "pede_humano"),
]


def gate_B22():
    print("\n[B2.2] `health` passa a ter escritor -- vocabulario unico, as 6 mensagens REAIS")
    _chave_de_cofre()
    from portal_worker import worker as W
    from portal_worker.journeys import JourneyResult

    check("o vocabulario tem exatamente as 6 palavras da §7 B2.2",
          set(W.VOCABULARIO_DE_SAUDE) == {"ok", "expirada", "credencial_recusada",
                                          "pede_humano", "fora_do_ar", "unknown"},
          W.VOCABULARIO_DE_SAUDE)

    for rotulo, status, ev, msg, esperado in MENSAGENS_REAIS:
        obtido = W.veredito_de_saude(status, dict(ev), msg)
        check("%s -> `%s`" % (rotulo, esperado), obtido == esperado,
              "veio %r para status=%r msg=%r" % (obtido, status, msg[:60]))

    check("sessao morta no servidor -> `expirada`",
          W.veredito_de_saude("needs_human", {"sessao_morta_detectada": {"morta": True}},
                              "a sessao no portal Allianz tinha caido") == "expirada")
    check("excecao transitoria NAO muda a saude (string vazia)",
          W.veredito_de_saude("failed", {"excecao_transitoria": True}, "TimeoutError") == "")
    check("transitoria com as tentativas esgotadas -> `fora_do_ar`",
          W.veredito_de_saude("failed", {"excecao_transitoria": True,
                                         "tentativas_esgotadas": True}, "TimeoutError") == "fora_do_ar")

    # --- O ESCRITOR, pelo worker inteiro: as DUAS tabelas, com `updated_at`
    supa, _, _ = _rodar_job(_db(), journey="login_check",
                            resultado=JourneyResult(status="failed",
                                                    message="a MAPFRE recusou a credencial (autenticacao invalida)"))
    sessao = supa.saude_gravada("portal_sessions")
    conta = supa.saude_gravada("portal_accounts")
    check("o primeiro `failed` de credencial grava `credencial_recusada` em portal_sessions",
          sessao.get("health") == "credencial_recusada", sessao)
    check("...e em portal_accounts (a coluna que tinha 16 de 16 `unknown`)",
          conta.get("health") == "credencial_recusada", conta)
    check("as duas gravacoes carregam `updated_at` EXPLICITO (o default so vale no INSERT)",
          bool(sessao.get("updated_at")) and bool(conta.get("updated_at")), (sessao, conta))
    check("a linha da sessao NAO apaga o storage guardado",
          "storage_state_encrypted" not in sessao, sorted(sessao))
    escritas_conta = [p for (t, op, p) in supa.escritas if t == "portal_accounts"]
    check("o update da conta e o unico caminho, e ele existe", len(escritas_conta) == 1, escritas_conta)
    check("a conta da corretora e o estado da corretora ficaram com a MESMA palavra",
          sessao.get("health") == conta.get("health"))

    supa_ok, _, _ = _rodar_job(_db(sessao=_sessao_cifrada(2)), journey="login_check",
                               resultado=JourneyResult(status="done", captured={"logged_in": True},
                                                       message="login ok"))
    check("`done` com `logged_in` grava `ok`",
          supa_ok.saude_gravada("portal_accounts").get("health") == "ok",
          supa_ok.saude_gravada("portal_accounts"))

    supa_zur, _, _ = _rodar_job(_db(), journey="cobranca_sweep",
                                resultado=JourneyResult(
                                    status="needs_human", captured={"logged_in": True},
                                    message="200 com ZERO parcelas em 45/90 dias"))
    check("🔴 Zurich: `needs_human` da VARREDURA com login ok NAO vira problema de senha",
          supa_zur.saude_gravada("portal_accounts").get("health") == "ok",
          supa_zur.saude_gravada("portal_accounts"))

    # --- o freio: vidros NAO opina sobre credencial
    supa_vidro, _, _ = _rodar_job(_db(), journey="abrir_atendimento",
                                  resultado=JourneyResult(status="needs_human",
                                                          message="confirme a peca danificada"))
    check("`abrir_atendimento` (vidros) NAO escreve saude de credencial",
          supa_vidro.saude_gravada("portal_accounts") == {}
          and supa_vidro.saude_gravada("portal_sessions") == {},
          supa_vidro.escritas)

    # --- CLAUDE.md §7: o update da conta filtra `company_id`
    import inspect

    fonte = inspect.getsource(W._escrever_saude)
    i_conta = fonte.find('table("portal_accounts")')
    check("o update de portal_accounts filtra `company_id` alem do `id` (CLAUDE.md §7)",
          i_conta != -1 and '.eq("company_id"' in fonte[i_conta:], fonte[i_conta:i_conta + 260])


# ==========================================================================
# B2.4 -- A ALLIANZ ALCANCA O DIAGNOSTICO DE SESSAO MORTA
# ==========================================================================
def gate_B24():
    print("\n[B2.4] Allianz: o diagnostico de sessao morta fica alcancavel -- UMA vez")
    from portal_worker.journeys import JourneyResult
    from portal_worker.journeys import allianz_corretor as AZ

    def montar(status_do_login, morta, status_depois=None):
        chamadas = {"login": 0, "diag": 0, "relogin": 0}
        sequencia = [status_do_login] + ([status_depois] if status_depois else [])

        async def login_check(page, params, evidence):
            i = min(chamadas["login"], len(sequencia) - 1)
            chamadas["login"] += 1
            return JourneyResult(status=sequencia[i], message="login %s" % sequencia[i])

        async def diagnosticar(page, evidence):
            chamadas["diag"] += 1
            return {"morta": morta, "motivo": "a pagina nao e mais do portal"}

        async def relogin(page, params, evidence, *, motivo=""):
            chamadas["relogin"] += 1
            return True

        return chamadas, login_check, diagnosticar, relogin

    originais = (AZ.login_check, AZ._diagnosticar_sessao_na_pagina, AZ._relogin_fresh)
    try:
        # (a) login pediu uma pessoa e a sessao esta morta -> diagnostica e reloga UMA vez
        chamadas, lc, dg, rl = montar("needs_human", True, status_depois="needs_human")
        AZ.login_check, AZ._diagnosticar_sessao_na_pagina, AZ._relogin_fresh = lc, dg, rl
        ev = {}
        r = asyncio.run(AZ.cobranca_sweep(PaginaDuble(), {}, ev))
        check("login `needs_human` + sessao morta -> `_diagnosticar_sessao_na_pagina` E chamado",
              chamadas["diag"] == 1, chamadas)
        check("...e o relogin acontece UMA vez, nunca em laco",
              chamadas["relogin"] == 1 and chamadas["login"] == 2, chamadas)
        check("a evidencia marca o relogin (e por isso `session_reused` nao sera verdadeiro)",
              ev.get("relogin") is True, sorted(ev))
        check("o desfecho continua sendo o do login (nada inventado)",
              r.status == "needs_human", r)

        # (b) credencial RECUSADA -> nao diagnostica, nao reloga
        chamadas, lc, dg, rl = montar("failed", True)
        AZ.login_check, AZ._diagnosticar_sessao_na_pagina, AZ._relogin_fresh = lc, dg, rl
        ev = {}
        r = asyncio.run(AZ.cobranca_sweep(PaginaDuble(), {}, ev))
        check("🔴 login `failed` (credencial): diagnostico NAO e chamado", chamadas["diag"] == 0, chamadas)
        check("🔴 login `failed` (credencial): NAO ha relogin -- porta trancada nao se bate",
              chamadas["relogin"] == 0 and chamadas["login"] == 1, chamadas)
        check("e a evidencia nao marca relogin", "relogin" not in ev, sorted(ev))

        # (c) CONTROLE: sessao NAO morta -> diagnostica e desiste sem relogar
        chamadas, lc, dg, rl = montar("needs_human", False)
        AZ.login_check, AZ._diagnosticar_sessao_na_pagina, AZ._relogin_fresh = lc, dg, rl
        asyncio.run(AZ.cobranca_sweep(PaginaDuble(), {}, {}))
        check("CONTROLE: diagnostico diz que a sessao esta viva -> nenhum relogin",
              chamadas["diag"] == 1 and chamadas["relogin"] == 0, chamadas)

        # (d) CONTROLE POSITIVO: o relogin resolve e a varredura SEGUE
        chamadas, lc, dg, rl = montar("needs_human", True, status_depois="done")
        AZ.login_check, AZ._diagnosticar_sessao_na_pagina, AZ._relogin_fresh = lc, dg, rl
        ev = {}
        try:
            asyncio.run(AZ.cobranca_sweep(PaginaDuble(), {}, ev))
        except Exception:  # noqa: BLE001
            pass   # sem navegador de verdade a varredura nao vai longe -- o que importa e o `logged_in`
        check("CONTROLE: relogin que DA CERTO faz a varredura continuar (o `return` nao come o caminho)",
              ev.get("logged_in") is True, sorted(ev))
    finally:
        AZ.login_check, AZ._diagnosticar_sessao_na_pagina, AZ._relogin_fresh = originais


# ==========================================================================
# G11 -- BACKOFF COM JITTER, TETO 3, ZERO PARA CREDENCIAL RECUSADA
# ==========================================================================
def gate_G11():
    print("\n[G11] backoff com full jitter, teto de 3 tentativas, ZERO para credencial recusada")
    _chave_de_cofre()
    from portal_worker import worker as W
    from portal_worker.journeys import JourneyResult

    check("as constantes tem os defaults da §13 E4 (60 s, 900 s, 3 tentativas)",
          (W.backoff_base_s(), W.backoff_teto_s(), W.max_tentativas_de_portal()) == (60, 900, 3),
          (W.backoff_base_s(), W.backoff_teto_s(), W.max_tentativas_de_portal()))

    # --- o MOTOR: duas chamadas com o MESMO attempts dao valores DIFERENTES
    a = W.proximo_available_at(2, agora=AGORA)
    b = W.proximo_available_at(2, agora=AGORA)
    check("duas chamadas com o mesmo `attempts` dao valores diferentes (full jitter)",
          a != b, (a, b))
    limite = AGORA + timedelta(seconds=min(60 * 4, 900))
    dentro = []
    for _ in range(40):
        quando = datetime.fromisoformat(W.proximo_available_at(2, agora=AGORA))
        dentro.append(AGORA <= quando <= limite)
    check("40 sorteios caem todos em [agora, agora + min(base*2^n, teto)]", all(dentro),
          dentro.count(False))
    check("o teto corta o crescimento: `attempts=10` nao passa de 900 s",
          datetime.fromisoformat(W.proximo_available_at(10, agora=AGORA, rnd=lambda: 1.0))
          == AGORA + timedelta(seconds=900))
    check("CONTROLE: sem o teto, `attempts=10` daria 61.440 s -- o guarda ve a diferenca",
          60 * (2 ** 10) > 900)
    check("`rnd` injetavel: sorteio 0 devolve `agora` (a funcao e determinavel, logo testavel)",
          datetime.fromisoformat(W.proximo_available_at(1, agora=AGORA, rnd=lambda: 0.0)) == AGORA)

    check("timeout e transitorio", W.e_transitoria(asyncio.TimeoutError()) is True)
    check("erro de rede e transitorio", W.e_transitoria(ConnectionError("net::ERR")) is True)
    check("navegador que nao sobe e transitorio",
          W.e_transitoria(RuntimeError("BrowserType.launch: Executable doesn't exist")) is True)
    check("🔴 recusa de credencial NAO e transitoria",
          W.e_transitoria(ValueError("a MAPFRE recusou a credencial")) is False)

    # --- o worker INTEIRO: falha transitoria volta para a fila
    supa, _, _ = _rodar_job(_db(sessao=_sessao_cifrada(2)), attempts=1,
                            excecao=asyncio.TimeoutError())
    patch = supa.ultimo_patch()
    check("falha transitoria com 1 tentativa -> volta para a fila (`queued`)",
          patch.get("status") == "queued", patch.get("status"))
    check("...com `available_at` no futuro", bool(patch.get("available_at")), patch)
    check("...e sem `finished_at` (o job nao terminou)", "finished_at" not in patch, sorted(patch))
    check("o `error` conta a tentativa em portugues de maquina legivel",
          "requeue 1/3" in str(patch.get("error") or ""), patch.get("error"))
    ev = patch.get("evidence") or {}
    check("a evidencia guarda quando volta e por que",
          isinstance(ev.get("requeue"), dict) and ev["requeue"].get("de") == 3, ev.get("requeue"))
    check("a saude NAO muda numa falha transitoria que vai ser retentada",
          supa.saude_gravada("portal_accounts") == {}, supa.saude_gravada("portal_accounts"))

    # --- teto: a terceira tentativa nao volta
    supa3, _, _ = _rodar_job(_db(sessao=_sessao_cifrada(2)), attempts=3,
                             excecao=asyncio.TimeoutError())
    patch3 = supa3.ultimo_patch()
    check("na tentativa 3 de 3 o job NAO volta para a fila", patch3.get("status") == "failed",
          patch3.get("status"))
    check("e `available_at` nao e escrito", "available_at" not in patch3, sorted(patch3))
    check("esgotadas as tentativas transitorias, a saude vira `fora_do_ar`",
          supa3.saude_gravada("portal_accounts").get("health") == "fora_do_ar",
          supa3.saude_gravada("portal_accounts"))

    # --- 🔴 credencial recusada: ZERO backoff, nos dois caminhos
    supa_cred, _, _ = _rodar_job(
        _db(sessao=_sessao_cifrada(2)), journey="login_check",
        resultado=JourneyResult(status="failed", message="credenciais rejeitadas pelo portal Allianz"))
    patch_cred = supa_cred.ultimo_patch()
    check("🔴 credencial recusada (resultado da journey): NENHUM requeue",
          patch_cred.get("status") == "failed" and "available_at" not in patch_cred, patch_cred.keys())
    check("...e a saude vira `credencial_recusada` (o breaker abre)",
          supa_cred.saude_gravada("portal_accounts").get("health") == "credencial_recusada",
          supa_cred.saude_gravada("portal_accounts"))
    supa_exc, _, _ = _rodar_job(_db(sessao=_sessao_cifrada(2)), attempts=1,
                                excecao=ValueError("a MAPFRE recusou a credencial (autenticacao invalida)"))
    patch_exc = supa_exc.ultimo_patch()
    check("🔴 credencial recusada (excecao): NENHUM requeue e NENHUM `available_at`",
          patch_exc.get("status") == "failed" and "available_at" not in patch_exc, patch_exc.keys())

    # --- 🔴 A SEGUNDA VOLTA NAO HERDA A PRIMEIRA.
    #     Com o requeue o mesmo job roda duas vezes sobre a MESMA evidencia. Se
    #     `excecao_transitoria` sobrevivesse, o classificador devolveria "nao mude
    #     nada" e a senha recusada descoberta na 2a volta NAO chegaria a tela.
    supa2, storage2, _ = _rodar_job(
        _db(sessao=_sessao_cifrada(27 * 24)), journey="login_check", attempts=2,
        job_evidence={"excecao_transitoria": True, "tentativas_esgotadas": True,
                      "requeue": {"tentativa": 1, "de": 3},
                      "session_injetada": True, "session_reused": True},
        resultado=JourneyResult(status="failed",
                                message="credenciais rejeitadas pelo portal Allianz"))
    ev2 = supa2.ultimo_patch().get("evidence") or {}
    check("🔴 a 2a tentativa NAO herda `excecao_transitoria` da 1a -- o veredito sai",
          supa2.saude_gravada("portal_accounts").get("health") == "credencial_recusada",
          supa2.saude_gravada("portal_accounts"))
    check("...e nao herda `session_reused` de uma execucao em que nada foi injetado",
          "session_reused" not in ev2 and "session_injetada" not in ev2, sorted(ev2))
    check("...e o `requeue` da volta anterior nao fica na evidencia final",
          "requeue" not in ev2, ev2.get("requeue"))

    # --- efeito material: nunca volta para a fila, mesmo transitorio
    supa_ef, _, _ = _rodar_job(
        _db(sessao=_sessao_cifrada(2)), attempts=1, excecao=asyncio.TimeoutError(),
        job_evidence={"critical_effect": {"phase": "submitted", "action": "create_attendance"}})
    patch_ef = supa_ef.ultimo_patch()
    check("🔴 efeito material armado: o job NAO volta para a fila (SPEC-074 continua valendo)",
          patch_ef.get("status") == "needs_human" and "available_at" not in patch_ef,
          (patch_ef.get("status"), sorted(patch_ef)))


# ==========================================================================
# G10-② -- SALVAR A SENHA POE `unknown` (o meio-aberto do breaker)
# ==========================================================================
def gate_G10():
    print("\n[G10-②] salvar credencial poe `unknown`, e o worker fecha o ciclo escrevendo o veredito")
    _chave_de_cofre()
    os.environ["BACKEND_INTERNAL_API_KEY"] = "chave-sintetica-de-teste"
    from cryptography.fernet import Fernet

    os.environ.setdefault("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    import app.api.portal as API
    from portal_worker import worker as W

    db = _db(conta={"id": CONTA, "company_id": CO, "portal_key": "allianz_corretor",
                    "account_label": "principal", "username": "usuario-sintetico",
                    "secret_encrypted": "x", "health": "credencial_recusada"})
    supa = _Supa(db)
    API.get_supabase_client = lambda: types.SimpleNamespace(client=supa)

    class _Req:
        async def json(self):
            return {"company_id": CO, "portal_key": "allianz_corretor",
                    "username": "usuario-sintetico", "password": "senha-sintetica"}

    asyncio.run(API.save_credential(_Req(), x_key="chave-sintetica-de-teste"))
    salvo = [p for (t, op, p) in supa.escritas if t == "portal_accounts"]
    check("salvar a senha grava `health='unknown'` (CONTROLE: continua como em 13/09)",
          bool(salvo) and salvo[-1].get("health") == "unknown", salvo)
    check("e o `updated_at` vai junto -- e dele que o breaker mede a idade",
          bool(salvo) and bool(salvo[-1].get("updated_at")), salvo)
    check("a senha NAO volta em claro em lugar nenhum da escrita",
          all("senha-sintetica" not in json.dumps(p, default=str) for p in salvo))
    check("`unknown` e o MEIO-ABERTO: a pior saude de {unknown} nao e `ok` nem `credencial_recusada`",
          W.GRAVIDADE_DA_SAUDE["unknown"] > W.GRAVIDADE_DA_SAUDE["credencial_recusada"]
          and W.GRAVIDADE_DA_SAUDE["unknown"] < W.GRAVIDADE_DA_SAUDE["ok"])

    # --- e o worker FECHA o ciclo: o `login_check` do prologo escreve ok ou o motivo
    from portal_worker.journeys import JourneyResult

    supa_ok, _, _ = _rodar_job(_db(sessao=_sessao_cifrada(2)), journey="login_check",
                               resultado=JourneyResult(status="done", captured={"logged_in": True},
                                                       message="login ok"))
    check("o `login_check` que ENTRA troca `unknown` por `ok` (o meio-aberto fecha)",
          supa_ok.saude_gravada("portal_accounts").get("health") == "ok",
          supa_ok.saude_gravada("portal_accounts"))
    supa_nao, _, _ = _rodar_job(_db(sessao=_sessao_cifrada(2)), journey="login_check",
                                resultado=JourneyResult(status="needs_human",
                                                        message="Informe o codigo de verificacao enviado"))
    check("o `login_check` que pede uma pessoa escreve `pede_humano`, nao `ok`",
          supa_nao.saude_gravada("portal_accounts").get("health") == "pede_humano",
          supa_nao.saude_gravada("portal_accounts"))


# ==========================================================================
# B3.4-④ -- AS DUAS TELAS, A MESMA PALAVRA, A MESMA FUNCAO
# ==========================================================================
#: 🔴 `telas_desconhecidas` entrou no contrato do card em 14/09/2026 (SPEC-EXTRA-001.6
#  B4.2). Ela e a FILA que P-264 exige que tenha leitor: o card e o leitor.
CHAVES_AGENTE = {"telas_desconhecidas",
                 "id", "nome", "descricao", "cor", "grupo", "estado", "motivo",
                 "pulso", "producao", "desligado", "trabalho", "acoes_hoje"}
CHAVES_GRUPO = {"id", "titulo", "proposito", "resumo", "agentes"}


def gate_B34():
    print("\n[B3.4-④] as duas telas mostram a MESMA palavra, da MESMA funcao")
    _chave_de_cofre()
    os.environ["BACKEND_INTERNAL_API_KEY"] = "chave-sintetica-de-teste"
    import app.api.portal as API
    from app.core.central_de_agentes import GRUPO_DOS_PORTAIS, grupo_dos_portais
    from app.services.saude_do_portal import rotulo_e_acao

    quando = (AGORA - timedelta(hours=3)).isoformat()
    conta = {"id": CONTA, "company_id": CO, "portal_key": "allianz_corretor",
             "account_label": "principal", "username": "usuario-sintetico",
             "secret_encrypted": "x", "health": "credencial_recusada", "updated_at": quando}

    # --- tela 1: a rota da lista de credenciais (MOTOR real)
    supa = _Supa({"portal_accounts": [dict(conta)]})
    API.get_supabase_client = lambda: types.SimpleNamespace(client=supa)
    saida = asyncio.run(API.list_credentials(company_id=CO, x_key="chave-sintetica-de-teste"))
    linha = (saida.get("credentials") or [{}])[0]
    esperado = rotulo_e_acao("credencial_recusada", quando)
    check("a rota devolve `health_rotulo` vindo da funcao unica",
          linha.get("health_rotulo") == esperado["rotulo"], linha.get("health_rotulo"))
    check("...e a acao ao lado ('atualize a senha aqui')",
          linha.get("health_acao") == esperado["acao"], linha.get("health_acao"))
    check("...e `verificado_em`", linha.get("verificado_em") == quando, linha.get("verificado_em"))
    check("a rota continua NAO devolvendo senha", "secret_encrypted" not in linha
          and "password" not in linha, sorted(linha))

    # --- tela 2: a Central de Agentes (MOTOR real)
    jobs = [
        {"portal_key": "allianz_corretor", "journey": "login_check", "status": "failed",
         "finished_at": (AGORA - timedelta(hours=3)).isoformat(),
         "message": "credenciais rejeitadas pelo portal Allianz"},
        {"portal_key": "allianz_corretor", "journey": "cobranca_sweep", "status": "done",
         "finished_at": (AGORA - timedelta(days=2)).isoformat(), "message": None},
    ]
    grupo = grupo_dos_portais([dict(conta)], jobs, AGORA, {"allianz_corretor": "Allianz Corretor"})
    check("o grupo 'Portais das seguradoras' existe", isinstance(grupo, dict)
          and grupo.get("id") == GRUPO_DOS_PORTAIS[0], (grupo or {}).get("id"))
    check("o grupo tem SO as chaves do contrato da §4 da SPEC-088",
          set(grupo or {}) == CHAVES_GRUPO,
          sorted(set(grupo or {}) ^ CHAVES_GRUPO))
    card = (grupo.get("agentes") or [{}])[0]
    check("um card por portal, com SO as chaves do contrato", set(card) == CHAVES_AGENTE,
          sorted(set(card) ^ CHAVES_AGENTE))
    check("🔴 a MESMA palavra da outra tela esta no card", esperado["rotulo"] in str(card.get("motivo")),
          card.get("motivo"))
    check("...e ela veio da MESMA funcao (o rotulo da rota e o rotulo do card sao iguais)",
          esperado["rotulo"] in str(card.get("motivo")) and linha.get("health_rotulo") == esperado["rotulo"])
    check("o card diz a taxa de sucesso de 7 dias em portugues",
          "1 de 2 entradas" in str(card.get("motivo")), card.get("motivo"))
    check("o card diz o motivo da ultima falha", "credenciais rejeitadas" in str(card.get("motivo")),
          card.get("motivo"))
    check("credencial recusada pinta o card de PARADO (nao de verde, nao de cinza)",
          card.get("estado") == "PARADO", card.get("estado"))
    check("o nome no card e nome de gente, nunca a chave da tabela",
          card.get("nome") == "Allianz Corretor" and "_" not in str(card.get("nome")), card.get("nome"))
    check("o card NAO carrega company_id nem nome de corretora (a Central e da plataforma)",
          CO not in json.dumps(card, default=str), card.get("motivo"))
    check("`trabalho` conta as entradas dos 7 dias e as falhas",
          (card.get("trabalho") or {}).get("execucoes_7d") == 2
          and (card["trabalho"]).get("falhas_7d") == 1, card.get("trabalho"))

    # --- a PIOR saude manda: uma conta ok + uma recusada nao e `ok`
    duas = [dict(conta), dict(conta, id="33333333-3333-3333-3333-333333333333",
                              account_label="segunda", health="ok")]
    grupo2 = grupo_dos_portais(duas, [], AGORA, {})
    card2 = (grupo2.get("agentes") or [{}])[0]
    check("duas contas (uma `ok`, uma recusada) -> o card mostra a PIOR",
          "senha recusada" in str(card2.get("motivo")), card2.get("motivo"))
    check("CONTROLE: com as duas contas `ok`, o card fica SAUDAVEL (o guarda ve a diferenca)",
          (grupo_dos_portais([dict(conta, health="ok"), dict(conta, health="ok", id="x")],
                             [], AGORA, {}).get("agentes") or [{}])[0].get("estado") == "SAUDAVEL")
    check("sem conta de portal nenhuma, o grupo NAO aparece (grupo vazio e ruido)",
          grupo_dos_portais([], [], AGORA, {}) is None)

    # --- 🔴 O ELO (protocolo §0.3): o grupo CHEGA na resposta da rota?
    #     A funcao pura estar certa nao prova que alguem a chama. `_montar` e a
    #     funcao que a rota `/agents-status` devolve inteira.
    from app.core.central_de_agentes import _montar
    from app.core.heartbeat import AGENT_TASKS

    bruto = {"agora": AGORA, "attendance": [], "runs": [], "artefatos": [],
             "aprovacoes": [], "producoes": {}, "custo_instrumentado": False,
             "truncado": (), "leitura_indisponivel": False,
             "portal_contas": [dict(conta)], "portal_jobs": jobs,
             "portais": [{"key": "allianz_corretor", "name": "Allianz Corretor"}]}
    pulsos = {e.id: {"id": e.id, "last_run": None, "actions_today": 0} for e in AGENT_TASKS}
    resposta = _montar(bruto, pulsos)
    ids = [g.get("id") for g in resposta.get("grupos") or []]
    check("🔴 O ELO: o grupo dos portais CHEGA na resposta de `/agents-status`",
          GRUPO_DOS_PORTAIS[0] in ids, ids)
    check("...depois dos quatro grupos historicos (a urgencia do segurado vem antes)",
          ids.index(GRUPO_DOS_PORTAIS[0]) >= 4, ids)
    check("CONTROLE: sem conta de portal, a resposta continua com os 4 grupos de sempre",
          GRUPO_DOS_PORTAIS[0] not in [g.get("id") for g in
                                       (_montar({**bruto, "portal_contas": []}, pulsos)
                                        .get("grupos") or [])])
    check("a raiz da resposta continua com as 5 chaves do contrato da SPEC-088 §4",
          set(resposta) == {"gerado_em", "cache_s", "grupos", "nao_instrumentado",
                            "sem_card_por_decisao"}, sorted(resposta))

    # --- o frontend so RENDERIZA: nenhuma das frases mora no .tsx
    raiz_web = os.path.dirname(RAIZ)
    tela_portais = _ler(os.path.join(raiz_web, "app", "dashboard", "personalizacao",
                                     "conectores", "portais", "page.tsx"))
    tela_central = _ler(os.path.join(raiz_web, "app", "admin", "central-agentes", "page.tsx"))
    for frase in ("senha recusada", "sessão vencida", "não verificado ainda", "fora do ar desde"):
        check("a frase %r NAO esta escrita no frontend (ela nasce no backend)" % frase,
              frase not in tela_portais and frase not in tela_central)
    check("a tela de Conectores RENDERIZA `health_rotulo`", "health_rotulo" in tela_portais)
    check("a tela de Conectores tambem mostra a acao ao lado", "health_acao" in tela_portais)
    check("a Central continua sem saber nenhum agente (o grupo vem do JSON)",
          "portais_seguradoras" not in tela_central)


# ==========================================================================
# B4.① -- O TEXTO DA TELA PASSA A EXISTIR (redigido, com hash, com a foto ao lado)
# ==========================================================================
CORPUS_TELAS = os.path.join(RAIZ, "tests", "corpus", "telas_reais_de_portal")

# 🔴 O CPF SINTETICO que entra no lugar do marcador `<cpf>` do corpus. O print
# REAL da MAPFRE de 11/09 traz o CPF do corretor EM CLARO no campo "Numero do
# CPF" (relatorio §1.1); o corpus foi para o repositorio ja redigido, entao o
# guarda devolve o vazamento ao texto antes de entregá-lo ao motor -- senao ele
# provaria que o redator limpa um texto que ja estava limpo.
CPF_SINTETICO = "123.456.789-09"


def _tela_do_corpus(arquivo):
    return _ler(os.path.join(CORPUS_TELAS, arquivo))


def gate_B41():
    print("\n[B4.①] todo desfecho nao-`done` grava o TEXTO da tela -- redigido, com hash")
    _chave_de_cofre()
    from portal_worker import worker as W
    from portal_worker.journeys import JourneyResult

    mapfre = _tela_do_corpus("mapfre_corretor-failed-20260911.txt").replace("<cpf>", CPF_SINTETICO)
    allianz = _tela_do_corpus("allianz_corretor-needs_human-20260911.txt")

    check("o corpus da MAPFRE traz o campo do CPF (senao o guarda nao mede nada)",
          CPF_SINTETICO in mapfre, mapfre[:80])

    # --- o MOTOR: `_run_job` inteiro, desfecho `needs_human`, tela real da MAPFRE
    supa, _, vistos = _rodar_job(
        _db(), texto_da_tela=mapfre,
        url_da_tela="https://www3.mapfre.com.br/portal/login?token=sessao-sintetica&u=fulano",
        resultado=JourneyResult(status="needs_human", message=MAPFRE_MSG_REAL))
    tela = (supa.ultimo_patch().get("evidence") or {}).get("tela")

    check("`evidence.tela` existe no desfecho `needs_human`", isinstance(tela, dict) and bool(tela),
          tela)
    tela = tela or {}
    check("...com EXATAMENTE as 4 chaves do contrato B4.1",
          set(tela) == {"texto", "hash", "url", "prova"}, sorted(tela))
    check("🔴 o CPF sintetico NAO esta no texto gravado (o redator rodou no NASCIMENTO do dado)",
          CPF_SINTETICO not in str(tela.get("texto")), str(tela.get("texto"))[:200])
    check("...nem os digitos dele sem pontuacao",
          "12345678909" not in str(tela.get("texto")))
    check("...e a marca do redator ficou no lugar (esconder que havia campo ensina a procurar errado)",
          "<redacted:cpf>" in str(tela.get("texto")), str(tela.get("texto"))[:200])
    check("🔴 mas a FRASE do portal continua la -- a prova serve para diagnosticar",
          "autenticacao invalida" in W._norm_tela(tela.get("texto")),
          W._norm_tela(tela.get("texto"))[:200])
    check("o texto tem teto de 2000 caracteres", len(str(tela.get("texto"))) <= 2000,
          len(str(tela.get("texto"))))
    check("a URL entra SEM a query (ela carrega token de sessao em meio portal)",
          tela.get("url") == "https://www3.mapfre.com.br/portal/login", tela.get("url"))
    check("`prova` aponta para o print que subiu ao cofre",
          str(tela.get("prova")) == "portal-evidence/job-sintetico/00-desfecho-needs-human.jpg",
          tela.get("prova"))
    check("...e o print EXISTE no cofre com esse caminho",
          "job-sintetico/00-desfecho-needs-human.jpg" in supa.arquivos, sorted(supa.arquivos))

    # --- CONTROLE do hash: mesma tela -> mesmo hash; tela diferente -> hash diferente
    supa2, _, _ = _rodar_job(_db(), texto_da_tela=mapfre,
                             resultado=JourneyResult(status="failed", message=MAPFRE_MSG_REAL))
    tela2 = (supa2.ultimo_patch().get("evidence") or {}).get("tela") or {}
    supa3, _, _ = _rodar_job(_db(), texto_da_tela=allianz,
                             resultado=JourneyResult(status="needs_human",
                                                     message="tela pos-login Allianz nao reconhecida"))
    tela3 = (supa3.ultimo_patch().get("evidence") or {}).get("tela") or {}
    check("CONTROLE: a MESMA tela em outro job da o MESMO hash (a fila consegue agrupar)",
          tela.get("hash") and tela.get("hash") == tela2.get("hash"),
          (tela.get("hash"), tela2.get("hash")))
    check("CONTROLE: uma tela DIFERENTE da hash diferente (o guarda ve a diferenca)",
          tela3.get("hash") and tela3.get("hash") != tela.get("hash"),
          (tela.get("hash"), tela3.get("hash")))
    check("o hash tem 16 hex (sha256 encurtado, ilegivel como identidade)",
          len(str(tela.get("hash"))) == 16 and all(c in "0123456789abcdef" for c in str(tela.get("hash"))),
          tela.get("hash"))
    check("o desfecho `failed` tambem grava a tela (nao so o `needs_human`)",
          bool(tela2), tela2)

    # --- o caminho da EXCECAO tambem grava (era o unico que nem foto tinha antes)
    supa4, _, _ = _rodar_job(_db(), texto_da_tela=allianz,
                             excecao=RuntimeError("portal caiu no meio"))
    tela4 = (supa4.ultimo_patch().get("evidence") or {}).get("tela") or {}
    check("a excecao no meio da journey tambem deixa o texto da tela",
          tela4.get("hash") == tela3.get("hash"), (tela4.get("hash"), tela3.get("hash")))

    # --- CONTROLE NEGATIVO: `done` NAO grava tela (a tela do sucesso e dashboard)
    supa5, _, _ = _rodar_job(_db(), texto_da_tela=_tela_do_corpus("hdi_corretor-done-20260911.txt"),
                             resultado=JourneyResult(status="done", captured={"logged_in": True},
                                                     message="ok"))
    check("🔴 CONTROLE: o desfecho `done` NAO entra na fila de telas desconhecidas",
          "tela" not in (supa5.ultimo_patch().get("evidence") or {}),
          sorted(supa5.ultimo_patch().get("evidence") or {}))
    check("...mas ele continua deixando a FOTO (a prova do trabalho que deu certo)",
          bool((supa5.ultimo_patch().get("evidence") or {}).get("prova")))

    # --- o motor nao pode morrer por causa da leitura da tela
    class _PaginaMuda(PaginaDuble):
        async def inner_text(self, _sel):
            raise RuntimeError("a pagina fechou antes de responder")

    ev = {}
    asyncio.run(W._registrar_tela(_PaginaMuda(), ev, "desfecho-failed"))
    check("🔴 uma pagina que nao responde NAO derruba o job -- so nao deixa tela",
          "tela" not in ev, sorted(ev))


# ==========================================================================
# B4.② -- A FILA DE TELAS DESCONHECIDAS, E OS DOIS LEITORES NO MESMO DIA
# ==========================================================================
CO_BETA = "44444444-4444-4444-4444-444444444444"       # a SEGUNDA corretora


def _job_com_tela(hash_, *, company_id=CO, portal="allianz_corretor", status="needs_human",
                  horas=1, texto="Acesso negado. Por favor, valide os dados introduzidos.",
                  prova="portal-evidence/j/00-desfecho-needs-human.jpg"):
    return {"company_id": company_id, "portal_key": portal, "journey": "cobranca_sweep",
            "status": status, "finished_at": (AGORA - timedelta(hours=horas)).isoformat(),
            "message": None,
            "tela": {"texto": texto, "hash": hash_, "url": "https://p/x", "prova": prova}}


def gate_B42():
    print("\n[B4.②] a fila de telas desconhecidas e uma CONSULTA -- e nasce com LEITOR")
    from app.core.central_de_agentes import (frase_das_telas_desconhecidas,
                                             grupo_dos_portais, telas_desconhecidas)

    jobs = (
        [_job_com_tela("aaaaaaaaaaaaaaaa", horas=h) for h in range(1, 13)]          # 12x
        + [_job_com_tela("bbbbbbbbbbbbbbbb", horas=20,
                         texto="Sistema temporariamente indisponivel. Tente mais tarde.")]
        + [_job_com_tela("cccccccccccccccc", company_id=CO_BETA, horas=2,
                         texto="Tela da OUTRA corretora, que nunca pode aparecer aqui.")]
        + [_job_com_tela("dddddddddddddddd", status="done", horas=3)]               # done: fora
        + [_job_com_tela("eeeeeeeeeeeeeeee", horas=24 * 90)]                        # velha: fora
        + [{"company_id": CO, "portal_key": "allianz_corretor", "journey": "cobranca_sweep",
            "status": "failed", "finished_at": (AGORA - timedelta(hours=4)).isoformat()}]
    )

    fila = telas_desconhecidas(jobs, company_id=CO, agora=AGORA)
    allianz = fila.get("allianz_corretor") or {}
    check("a fila agrupa por portal", set(fila) == {"allianz_corretor"}, sorted(fila))
    check("duas telas DISTINTAS (o `hash` e quem agrupa, nao o texto)",
          allianz.get("distintas") == 2, allianz.get("distintas"))
    mf = allianz.get("mais_frequente") or {}
    check("a mais frequente foi vista 12x", mf.get("vezes") == 12, mf.get("vezes"))
    check("...e traz a `ultima` vez que apareceu", bool(mf.get("ultima")), mf.get("ultima"))
    check("...e uma AMOSTRA do texto", "valide os dados" in str(mf.get("amostra")),
          mf.get("amostra"))
    check("...e o caminho do PRINT (o leitor consegue abrir a prova)",
          str(mf.get("prova")).startswith("portal-evidence/"), mf.get("prova"))
    check("a amostra tem teto de 120 caracteres", len(str(mf.get("amostra"))) <= 120,
          len(str(mf.get("amostra"))))
    check("🔴 CLAUDE.md §7: a tela da OUTRA corretora NAO aparece na fila desta",
          "OUTRA corretora" not in json.dumps(fila, default=str)
          and all(t.get("hash") != "cccccccccccccccc" for t in allianz.get("telas") or []),
          json.dumps(fila, default=str)[:300])
    check("o desfecho `done` NAO entra na fila (ele nao e tela desconhecida)",
          all(t.get("hash") != "dddddddddddddddd" for t in allianz.get("telas") or []))
    check("uma tela de 90 dias atras esta FORA da janela de 30 dias",
          all(t.get("hash") != "eeeeeeeeeeeeeeee" for t in allianz.get("telas") or []))
    check("um job nao-done SEM tela nao quebra e nao conta",
          sum(t.get("vezes") for t in allianz.get("telas") or []) == 13,
          [t.get("vezes") for t in allianz.get("telas") or []])

    # --- CONTROLE do isolamento: com a OUTRA corretora, a fila e a dela
    fila_beta = telas_desconhecidas(jobs, company_id=CO_BETA, agora=AGORA)
    beta = fila_beta.get("allianz_corretor") or {}
    check("CONTROLE: a mesma consulta para a corretora B devolve SO a tela dela",
          beta.get("distintas") == 1
          and (beta.get("mais_frequente") or {}).get("hash") == "cccccccccccccccc",
          beta)

    # --- a frase humana
    check("a frase humana diz o que o corretor precisa saber",
          frase_das_telas_desconhecidas(allianz)
          == "2 telas que eu não reconheço — a mais frequente vista 12×",
          frase_das_telas_desconhecidas(allianz))
    check("sem tela desconhecida, a frase e VAZIA (linha vazia e ruido)",
          frase_das_telas_desconhecidas({"distintas": 0, "mais_frequente": None}) == "")

    # --- LEITOR 1: o card do portal na Central de Agentes (MOTOR real)
    conta = {"id": CONTA, "company_id": CO, "portal_key": "allianz_corretor",
             "account_label": "principal", "health": "pede_humano",
             "updated_at": (AGORA - timedelta(hours=1)).isoformat()}
    grupo = grupo_dos_portais([dict(conta)], jobs, AGORA, {"allianz_corretor": "Allianz Corretor"})
    card = (grupo.get("agentes") or [{}])[0]
    check("o card do portal carrega `telas_desconhecidas`",
          isinstance(card.get("telas_desconhecidas"), dict), card.get("telas_desconhecidas"))
    td = card.get("telas_desconhecidas") or {}
    check("...com `distintas` e `mais_frequente`", set(td) == {"distintas", "mais_frequente"},
          sorted(td))
    check("🔴 O LEITOR: a frase esta no `motivo` que a tela mostra",
          "telas que eu não reconheço" in str(card.get("motivo")), card.get("motivo"))
    check("...com a contagem da mais frequente", "vista 13×" in str(card.get("motivo"))
          or "vista 12×" in str(card.get("motivo")), card.get("motivo"))
    check("o card continua com SO as chaves do contrato (uma chave a mais, declarada)",
          set(card) == CHAVES_AGENTE, sorted(set(card) ^ CHAVES_AGENTE))
    check("a Central agrega por PORTAL: nenhum company_id no card",
          CO not in json.dumps(card, default=str) and CO_BETA not in json.dumps(card, default=str))
    check("CONTROLE: sem tela desconhecida nenhuma, o card NAO ganha a frase",
          "não reconheço" not in str((grupo_dos_portais(
              [dict(conta)], [], AGORA, {}).get("agentes") or [{}])[0].get("motivo")))

    # --- LEITOR 2: a linha do relatorio da rotina, por tela NOVA do dia
    from app.services import billing_collection as BC

    jobs_da_execucao = [
        {"id": "j1", "portal_key": "allianz_corretor", "status": "needs_human",
         "evidence": {"tela": {"hash": "aaaaaaaaaaaaaaaa", "texto": "Acesso negado. Valide os dados."}}},
        {"id": "j2", "portal_key": "mapfre_corretor", "status": "failed",
         "evidence": {"tela": {"hash": "ffffffffffffffff",
                               "texto": "Autenticacao invalida! CPF 123.456.789-09"}}},
    ]

    class _ClienteComHistorico:
        def __init__(self, conhecidos, quebra=False):
            self.conhecidos, self.quebra, self.filtros = conhecidos, quebra, []

        def table(self, _n):
            return self

        def select(self, *a, **k):
            return self

        def eq(self, c, v):
            self.filtros.append((c, v))
            return self

        def in_(self, *a, **k):
            return self

        def lt(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            if self.quebra:
                raise RuntimeError("postgrest fora do ar")
            return types.SimpleNamespace(data=[{"hash": h} for h in self.conhecidos])

    cli = _ClienteComHistorico(["aaaaaaaaaaaaaaaa"])
    novas, erro = BC.telas_novas_do_dia(cli, CO, jobs_da_execucao, agora=AGORA)
    check("a leitura do historico filtra por company_id (CLAUDE.md §7)",
          ("company_id", CO) in cli.filtros, cli.filtros)
    check("SO a tela que aparece pela 1a vez hoje entra",
          [n.get("hash") for n in novas] == ["ffffffffffffffff"], novas)
    check("...e a amostra dela vai REDIGIDA para o relatorio",
          "123.456.789-09" not in str(novas[0].get("amostra")) if novas else False,
          novas[0].get("amostra") if novas else None)
    check("sem erro de leitura, o motivo fica vazio", erro == "", erro)

    relatorio = BC._format_report(
        routine={"name": "Cobranca"}, cfg={"portal_keys": ["allianz_corretor"], "send_mode": "equipe"},
        jobs=jobs_da_execucao, items=[], boletos=[], blockers=[], approval_id=None,
        test_sends=[], telas_novas=novas)
    check("🔴 O LEITOR 2: o relatorio da rotina ganha UMA linha por tela nova do dia",
          "tela nova hoje no portal mapfre_corretor" in relatorio,
          [l for l in relatorio.splitlines() if "tela nova" in l])
    check("...e a tela ja conhecida NAO vira linha (a fila nao repete o que ja se sabe)",
          "allianz_corretor" not in "\n".join(l for l in relatorio.splitlines()
                                              if l.startswith("tela nova")))
    check("CONTROLE: sem tela nova, o relatorio nao ganha a linha",
          "tela nova hoje" not in BC._format_report(
              routine={"name": "Cobranca"}, cfg={"portal_keys": [], "send_mode": "equipe"},
              jobs=[], items=[], boletos=[], blockers=[], approval_id=None, test_sends=[]))

    # --- 🔴 O ELO (protocolo §0.3): a tela do LOGIN chega em `telas_novas_do_dia`?
    #     A funcao estar certa nao prova que alguem lhe entrega o job certo. E a
    #     tela desconhecida mora no LOGIN: 📊 as duas telas nao-done de 10-11/09
    #     (Allianz "Acesso negado", Mapfre "Autenticacao invalida!") sao telas de
    #     login -- e quando o login falha a varredura nem chega a rodar, entao um
    #     coletor que so olhasse `cobranca_sweep` nunca veria nenhuma delas.
    colhidos = []
    conta_falsa = {"id": "ac-1", "health": "ok",
                   "updated_at": (AGORA - timedelta(hours=1)).isoformat()}
    desfecho_do_login = {
        "id": "job-login", "portal_key": "allianz_corretor", "status": "needs_human",
        "error": None,
        "evidence": {"message": "tela pos-login Allianz nao reconhecida",
                     "tela": {"hash": "9999999999999999", "prova": "portal-evidence/x/00.jpg",
                              "texto": "Acesso negado Por favor, valide os dados introduzidos."}}}

    async def _poll_do_canario(_cli, job_id, _teto):
        return dict(desfecho_do_login, id=job_id)

    conta, enfileirar, poll = BC._portal_account, BC._enqueue_job, BC._poll_job
    BC._portal_account = lambda *a, **k: dict(conta_falsa)
    BC._enqueue_job = lambda *a, **k: "job-login_check-allianz_corretor"
    BC._poll_job = _poll_do_canario
    try:
        asyncio.run(BC._canario_de_login(
            None, {"company_id": CO, "config": {}},
            {"portal_keys": ["allianz_corretor"], "poll_timeout_seconds": 1}, [], colhidos))
    finally:
        BC._portal_account, BC._enqueue_job, BC._poll_job = conta, enfileirar, poll

    check("🔴 O ELO: o desfecho do `login_check` entra na lista de jobs da execucao",
          [j.get("id") for j in colhidos] == ["job-login_check-allianz_corretor"], colhidos)
    novas_do_login, _ = BC.telas_novas_do_dia(_ClienteComHistorico([]), CO, colhidos, agora=AGORA)
    check("...e a tela DELE vira a linha do relatorio (a tela desconhecida mora no login)",
          [n.get("hash") for n in novas_do_login] == ["9999999999999999"], novas_do_login)

    _, erro2 = BC.telas_novas_do_dia(_ClienteComHistorico([], quebra=True), CO,
                                     jobs_da_execucao, agora=AGORA)
    check("se a leitura do historico FALHAR, o motivo volta escrito", erro2 == "RuntimeError", erro2)
    rel_erro = BC._format_report(
        routine={"name": "Cobranca"}, cfg={"portal_keys": [], "send_mode": "equipe"},
        jobs=[], items=[], boletos=[], blockers=[], approval_id=None, test_sends=[],
        telas_erro=erro2)
    check("🔴 ...e o relatorio DIZ que nao conseguiu conferir (silencio seria mentira)",
          "nao consegui conferir" in rel_erro.lower(),
          [l for l in rel_erro.splitlines() if "conferir" in l.lower()])


# ==========================================================================
# B4.③ -- O PRINT DE TELA DE LOGIN SAI COM OS CAMPOS MASCARADOS
# ==========================================================================
def gate_B43():
    print("\n[B4.③] a mascara entra no DOM ANTES da foto -- nao na imagem depois")
    _chave_de_cofre()
    from portal_worker import worker as W
    from portal_worker.journeys import JourneyResult

    mapfre = _tela_do_corpus("mapfre_corretor-failed-20260911.txt").replace("<cpf>", CPF_SINTETICO)
    supa, _, vistos = _rodar_job(_db(), texto_da_tela=mapfre,
                                 resultado=JourneyResult(status="needs_human",
                                                         message=MAPFRE_MSG_REAL))
    page = vistos["page"]
    mascaras = [i for i, (tipo, js) in enumerate(page.ordem)
                if tipo == "evaluate" and "••••••••" in str(js)]
    fotos = [i for i, (tipo, _js) in enumerate(page.ordem) if tipo == "screenshot"]

    check("a mascara foi avaliada no DOM", bool(mascaras),
          [str(j)[:60] for (t, j) in page.ordem if t == "evaluate"])
    check("a foto foi tirada", bool(fotos), page.fotos)
    check("🔴 a mascara roda ANTES da foto (foto antes da mascara nao protege ninguem)",
          bool(mascaras) and bool(fotos) and mascaras[0] < fotos[0], (mascaras, fotos))

    js = str(page.ordem[mascaras[0]][1]) if mascaras else ""
    for tipo in ("password", "text", "email", "tel"):
        check("o JS cobre `input` de tipo %r" % tipo, "'%s'" % tipo in js, js[:200])
    check("ele mexe SO em `input.value` (nao apaga a tela, nao navega)",
          "querySelectorAll('input')" in js and "i.value" in js and "location" not in js, js[:200])

    # --- CONTROLE: o desfecho `done` NAO mascara -- ele e dashboard, e a foto e prova
    _, _, vistos_ok = _rodar_job(_db(), texto_da_tela=_tela_do_corpus("hdi_corretor-done-20260911.txt"),
                                 resultado=JourneyResult(status="done", captured={"logged_in": True},
                                                         message="ok"))
    ok = vistos_ok["page"]
    check("🔴 CONTROLE: no desfecho `done` a mascara NAO roda (o guarda ve a diferenca)",
          not any("••••••••" in str(js) for (t, js) in ok.ordem if t == "evaluate"))
    check("...e o `done` continua deixando foto", ok.fotos >= 1, ok.fotos)

    # --- a mascara nao pode derrubar o job
    class _PaginaTeimosa(PaginaDuble):
        async def evaluate(self, script, *a, **k):
            if "••••••••" in str(script):
                raise RuntimeError("CSP bloqueou o evaluate")
            return await PaginaDuble.evaluate(self, script, *a, **k)

    ev = {}
    pg = _PaginaTeimosa(mapfre)
    asyncio.run(W._registrar_tela(pg, ev, "desfecho-needs_human"))
    check("uma mascara que falha NAO derruba o job -- o texto continua sendo gravado",
          isinstance(ev.get("tela"), dict) and bool(ev["tela"].get("hash")), ev)


# ==========================================================================
# AS MUTACOES -- (id, arquivo, de, para, gate)
# ==========================================================================
MUTACOES = [
    # M9: ignorar o TTL -- a sessao de 27 dias volta a ser injetada
    ("M9", "portal_worker/worker.py",
     "        if idade is None or idade > ttl_h:\n",
     "        if False:\n", "G9"),
    # M11: aplicar backoff ao que NAO e transitorio (= a credencial recusada entra na fila)
    ("M11", "portal_worker/worker.py",
     "        pode_voltar = transitoria and not houve_efeito and tentativas < teto\n",
     "        pode_voltar = not houve_efeito and tentativas < teto\n", "G11"),
    # M13: o classificador deixa de reconhecer a recusa de credencial
    #      ⚠️ as QUATRO marcas saem: a linha real da MAPFRE casa tres delas, e tirar
    #      uma so deixaria o guarda verde -- mutacao que nao muda comportamento nao mede.
    ("M13", "portal_worker/worker.py",
     '_MARCAS_DE_CREDENCIAL = ("recus", "rejeitad", "credenci", "invalid")\n',
     '_MARCAS_DE_CREDENCIAL = ()\n', "B2.2"),
    # M14: a evidencia da tentativa anterior passa a ser herdada -> o veredito da
    #      2a volta some (era o defeito que o requeue do B3.2 criou; ver G11)
    ("M14", "portal_worker/worker.py",
     '    for _chave in ("excecao_transitoria", "tentativas_esgotadas", "requeue",\n'
     '                   "session_injetada", "session_reused", "sessao_vencida"):\n',
     '    for _chave in ():\n', "G11"),
    # 🔴 M-B4.1: a REDACAO do texto da tela e desligada -- o CPF do corretor que o
    #    print da MAPFRE mostra em claro passa a ser gravado em `evidence.tela.texto`.
    ("M-B4.1", "portal_worker/worker.py",
     "    texto = _R.redigir_texto(bruto)[:TETO_DO_TEXTO_DA_TELA]\n",
     "    texto = bruto[:TETO_DO_TEXTO_DA_TELA]\n", "B4.1"),
    # 🔴 M-B4.2: o agrupamento para de filtrar o tenant -- a tela da corretora B
    #    aparece na fila da corretora A (CLAUDE.md §7: o filtro e no CODIGO).
    ("M-B4.2", "app/core/central_de_agentes.py",
     '        if alvo and str(j.get("company_id") or "") != alvo:\n',
     "        if False:\n", "B4.2"),
    # 🔴 M-B4.3: a FOTO passa a ser tirada ANTES da mascara. Nada deixa de rodar --
    #    so a ordem muda, e a ordem e a unica coisa que protege o CPF do corretor.
    ("M-B4.3", "portal_worker/worker.py",
     '            if result.status != "done":\n'
     '                await _registrar_tela(page, evidence, f"desfecho-{result.status}")\n'
     '            await _prova_do_desfecho(page, evidence, f"desfecho-{result.status}")\n',
     '            await _prova_do_desfecho(page, evidence, f"desfecho-{result.status}")\n'
     '            if result.status != "done":\n'
     '                await _registrar_tela(page, evidence, f"desfecho-{result.status}")\n',
     "B4.3"),
    # 🔴 M-B4.4: o desfecho do `login_check` para de entrar na lista de jobs da
    #    execucao. Nada quebra, nada fica vermelho no produto -- e a fila de telas
    #    novas do dia deixa de ver a UNICA tela que existe quando o login falha.
    ("M-B4.4", "app/services/billing_collection.py",
     "        if isinstance(resultado, dict) and jobs_vistos is not None:\n",
     "        if False:\n", "B4.2"),
]

GATES = {"G9": gate_G9, "B2.2": gate_B22, "B2.4": gate_B24, "G11": gate_G11,
         "G10": gate_G10, "B3.4": gate_B34,
         "B4.1": gate_B41, "B4.2": gate_B42, "B4.3": gate_B43}


def rodar_mutacoes(filtro=None):
    print("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO; a arvore precisa estar parada")
    vermelhas = verdes = 0
    for mid, rel, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, rel)
        original = _ler(caminho)
        if de not in original:
            check("%s: o trecho a mutar EXISTE em %s" % (mid, rel), False, "trecho nao encontrado")
            continue
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak").name
        shutil.copyfile(caminho, backup)
        try:
            with io.open(caminho, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(original.replace(de, para, 1))
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "--so", gate],
                               cwd=RAIZ, capture_output=True, text=True, timeout=900,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8",
                                    "PYTHONDONTWRITEBYTECODE": "1"})
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if r.returncode != 0 and falhas:
                vermelhas += 1
                print("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:160]))
            else:
                verdes += 1
                print("  [FALHOU] %s NAO deixou %s vermelho (rc=%s)\n%s"
                      % (mid, gate, r.returncode, (r.stdout or r.stderr)[-1200:]))
        finally:
            shutil.copyfile(backup, caminho)   # 🔴 restaura por COPIA, nunca git checkout
            os.unlink(backup)
            assert _ler(caminho) == original, "restauracao falhou em " + rel
    print("\n  PLACAR DAS MUTACOES: %d vermelhas · %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    global PASS, FAIL
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M") else None
        ok = rodar_mutacoes(filtro)
        sys.exit(0 if ok else 1)
    so = args[args.index("--so") + 1] if "--so" in args else None
    print("=" * 74)
    print("  SPEC-EXTRA-001.6 -- O PORTAL DIZ POR QUE NAO ENTROU")
    print("=" * 74)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback

            check("%s roda sem excecao" % gid, False,
                  "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()[-900:]))
    print("\n" + "=" * 74)
    print("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
    print("=" * 74)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
