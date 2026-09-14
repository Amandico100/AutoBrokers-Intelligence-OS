# -*- coding: utf-8 -*-
"""A FERRAMENTA DO TURNO DEIXA RASTRO -- gate de bloco da SPEC-EXTRA-001.1 (E).

⚠️ Este arquivo NAO conta no teto de 12 guardas novos da SPEC (proposta 10): ele
e o GATE do BLOCO E para P-PILOTO-18, nao um guarda novo de produto.

O QUE A PENDENCIA DIZIA, E POR QUE ESTAVA VENCIDA
------------------------------------------------------------------------------
P-PILOTO-18: *"o chat do painel nao registra que ferramenta o agente chamou ...
sem `tool_invocations`"*.

📊 Conferido em 13 e 14/09/2026 -- **a tabela existe e o chat grava nela**:

```
tool_invocations                                   277 linhas (140 desde 09/09)
app/agents/nodes.py:1057   registro = _abrir_registro_de_invocacao(...)
                           with registro:   <- ENVOLVE toda execucao de tool
app/services/skills/gateway.py:294   db.table("tool_invocations").insert({...})
input_summary com 11 digitos seguidos               0 de 277
```

🔴 Escrever a SPEC pela pendencia teria criado uma SEGUNDA gravacao de tool call
ao lado da que existe -- motor paralelo (CLAUDE.md 5). O que faltava era outra
coisa, e este arquivo guarda as quatro:

```
[G1] a LIGACAO com o turno   `trace_id` = "<session_id>|<client_request_id>"
[G2] a JUNCAO de volta       `payload.turn.tool_calls`, lido pelo /chat/stream
[G3] o que NUNCA se grava    argumento cru (o `document` de uma consulta E CPF)
[G4] o SILENCIO na falha     `_RegistroInerte` passa a CONTAR quantas vezes
[G5] o CONTEXTO atravessa    marcar_turno -> task -> thread (e o par de controle)
```

⛔ UMA ESCRITA, DOIS LEITORES. O escritor continua sendo o no de tool. O
`/chat/stream` so LE de volta, pela chave que o proprio turno montou -- e as
duas pontas chamam a MESMA `chave_de_rastro` (CLAUDE.md 9.4: um formato medido
num lugar e montado noutro e um formato sobre outra coisa).

SEGURANCA
------------------------------------------------------------------------------
```
· banco 100% em memoria; nenhuma leitura e nenhuma escrita de banco real
· nenhuma rede, nenhum provedor de LLM
· o "CPF" usado em [G3] e a sentinela 12345678901 -- nunca um documento real
```

AS MUTACOES -- por COPIA, em SUBPROCESSO, so com `--mutar`
------------------------------------------------------------------------------
    M1  `trace_id` volta a ser so o `session_id`      -> [G1] [G2] vermelho
    M2  `resumo_da_entrada` grava o argumento CRU     -> [G3] vermelho
    M3  o `_RegistroInerte` para de contar            -> [G4] vermelho

Rodar (a partir de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_ferramenta_do_turno_deixa_rastro.py
    ... --mutar
"""
from __future__ import annotations

import asyncio
import importlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
_TESTES = os.path.dirname(os.path.abspath(__file__))
if _TESTES not in sys.path:
    sys.path.insert(0, _TESTES)

PASS = 0
FAIL = 0

#: Sentinela. ⛔ Nunca um documento real (CLAUDE.md 7).
CPF_SENTINELA = "12345678901"
TOOL = "infocap_policy_lookup"
#: 📊 `chave_de_registro(infocap_policy_lookup)` em 14/09/2026.
TOOL_KEY = "insurance.policy_lookup"
CAPABILITY = "operational.infocap.policy_lookup.read"


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))
    return bool(cond)


def _ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return fh.read()


# ==========================================================================
# O BANCO DUBLE **SINCRONO** -- o lado de quem ESCREVE
#
# ⚠️ Por que nao reusar o `BancoDubleD` do `test_o_chat_fala_tipado`: o
# `execute()` dele e `async`, porque o `/chat/stream` fala com o cliente ASYNC.
# O `RegistroDeInvocacao` roda dentro do no de tool e fala com o cliente
# SINCRONO (`get_supabase_client`) -- `await` nenhum. Sao duas formas de
# cliente porque a PRODUCAO tem duas. O leitor async continua vindo de la
# (G2 importa o arreio), e so o escritor sincrono e montado aqui.
# ==========================================================================
class _RespostaSync:
    def __init__(self, data):
        self.data = data


class _ConsultaSync:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.op, self.carga = [], None, None

    def select(self, *a, **k):
        self.op = "select"; return self

    def insert(self, carga):
        self.op, self.carga = "insert", carga; return self

    def update(self, carga):
        self.op, self.carga = "update", carga; return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor)); return self

    def limit(self, n): return self
    def order(self, *a, **k): return self

    def _casa(self, linha):
        return all(str(linha.get(c)) == str(v) for c, v in self.filtros)

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        if self.op == "select":
            return _RespostaSync([dict(l) for l in linhas if self._casa(l)])
        if self.op == "insert":
            nova = dict(self.carga)
            nova.setdefault("id", str(uuid.uuid4()))
            linhas.append(nova)
            return _RespostaSync([dict(nova)])
        if self.op == "update":
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self.carga)
            return _RespostaSync([dict(l) for l in tocadas])
        raise AssertionError(self.op)


class BancoSync:
    def __init__(self, dados=None):
        self.dados = dados or {}

    def table(self, nome):
        return _ConsultaSync(self, nome)


def _banco_do_escritor():
    """O catalogo minimo que o `RegistroDeInvocacao` le antes de gravar."""
    return BancoSync({
        "tool_definitions": [{"id": "tool-def-1", "tool_key": TOOL_KEY,
                              "capability_key": CAPABILITY, "is_active": True}],
        "tool_releases": [{"id": "tool-rel-1", "tool_id": "tool-def-1",
                           "status": "published", "is_default": True}],
        "tool_invocations": [],
    })


class _TrocaCliente:
    """Troca `app.core.database.get_supabase_client` pelo banco dublado."""

    def __init__(self, banco):
        self._banco = banco

    def __enter__(self):
        self._mod = importlib.import_module("app.core.database")
        self._antes = self._mod.get_supabase_client
        self._mod.get_supabase_client = lambda *a, **k: self._banco
        return self

    def __exit__(self, *exc):
        self._mod.get_supabase_client = self._antes
        return False


def _limpar_cache_do_catalogo():
    """O catalogo e cache de PROCESSO -- entre casos ele nao pode vazar."""
    rec = importlib.import_module("app.services.skills.invocation_recorder")
    rec._CATALOGO.clear()


# ==========================================================================
# G1 -- A INVOCACAO GRAVA A CHAVE DO TURNO
#
# 🔴 Aqui roda a CADEIA REAL: `nodes._abrir_registro_de_invocacao` ->
# `RegistroDeInvocacao` -> `ToolGateway.registrar_invocacao` -> insert. Nada e
# reimplementado.
# ==========================================================================
def _invocar_de_verdade(banco, *, company_id, session_id, turno, args,
                        resultado="ok"):
    nodes = importlib.import_module("app.agents.nodes")
    rec = importlib.import_module("app.services.skills.invocation_recorder")
    _limpar_cache_do_catalogo()
    nodes.zerar_registros_inertes()
    rec.marcar_turno(turno)
    estado = {"company_id": company_id, "session_id": session_id}
    with _TrocaCliente(banco):
        registro = nodes._abrir_registro_de_invocacao(
            estado, tool_name=TOOL, tool_args=args)
        with registro:
            registro.ok(resultado)
    return registro


def gate_G1():
    print("\n[G1] a invocacao grava a chave do TURNO, nao so a da sessao")
    rec = importlib.import_module("app.services.skills.invocation_recorder")
    nodes = importlib.import_module("app.agents.nodes")

    company = str(uuid.uuid4())
    sessao = str(uuid.uuid4())
    turno = str(uuid.uuid4())
    banco = _banco_do_escritor()

    _invocar_de_verdade(banco, company_id=company, session_id=sessao,
                        turno=turno, args={"document": CPF_SENTINELA,
                                           "user_query": "x"})

    linhas = banco.dados["tool_invocations"]
    if not check("[G1] a invocacao foi GRAVADA (uma linha)", len(linhas) == 1,
                 "linhas=%d" % len(linhas)):
        return
    linha = linhas[0]
    esperado = rec.chave_de_rastro(sessao, turno)
    check("[G1] a chave e montada por `chave_de_rastro` (um formato, um lugar)",
          esperado == "%s|%s" % (sessao, turno), "esperado=%r" % esperado)
    check("[G1] `trace_id` da linha == a chave do turno",
          linha.get("trace_id") == esperado,
          "gravado=%r esperado=%r" % (linha.get("trace_id"), esperado))
    check("[G1] a sessao continua legivel na chave (prefixo)",
          str(linha.get("trace_id") or "").startswith(sessao))
    check("[G1] o `company_id` vai na linha (CLAUDE.md 7 -- service role)",
          str(linha.get("company_id")) == company)
    check("[G1] a capability da tool foi resolvida pelo catalogo real",
          linha.get("capability_key") == CAPABILITY,
          "gravado=%r" % linha.get("capability_key"))
    check("[G1] a invocacao FECHOU como `succeeded` (nao ficou 'running')",
          linha.get("status") == "succeeded", "status=%r" % linha.get("status"))
    check("[G1] o contador de inertes e ZERO no caminho feliz",
          nodes.registros_inertes() == 0,
          "inertes=%d motivos=%r" % (nodes.registros_inertes(),
                                     nodes.motivos_inertes()))

    # --- PAR DE CONTROLE: FORA de um turno de chat (Rotina, worker) ---------
    # 🔴 Sem este par, [G1] passaria com um codigo que grudasse "|None" em tudo.
    #
    # ⚠️ O FATO MUDOU EM 14/09/2026, e a assercao mudou com ele (CLAUDE.md 9.3).
    # Ate aqui este par afirmava *"fora de turno o rastro e SO a sessao"* — e era
    # verdade, e era o DEFEITO: a sessao pura e exatamente a chave que a leitura
    # do `/chat/stream` montava num turno sem `client_request_id`, e o
    # `.eq("trace_id", chave)` colhia estas linhas como se fossem as do turno.
    # A licao migra em vez de morrer: o que se exige agora e que a forma de fora
    # de turno seja DISTINGUIVEL — e que ela nao seja a sessao pura.
    banco2 = _banco_do_escritor()
    _invocar_de_verdade(banco2, company_id=company, session_id=sessao,
                        turno=None, args={"user_query": "x"})
    linha2 = banco2.dados["tool_invocations"][0]
    check("[G1] CONTROLE: fora de turno, o rastro e `<sessao>|-` (nunca a sessao pura)",
          linha2.get("trace_id") == "%s|%s" % (sessao, rec.MARCA_SEM_TURNO)
          and linha2.get("trace_id") != sessao,
          "gravado=%r" % linha2.get("trace_id"))
    check("[G1] CONTROLE: a sessao continua legivel no prefixo",
          str(linha2.get("trace_id") or "").startswith(sessao))
    check("[G1] CONTROLE: e as duas formas CONSEGUEM ser diferentes",
          linha2.get("trace_id") != linha.get("trace_id"))


# ==========================================================================
# G2 -- O TURNO ENCONTRA A INVOCACAO POR JUNCAO
#
# Roda o `/chat/stream` DE PRODUCAO (arreio do `test_o_chat_fala_tipado`), com
# a linha que o [G1] gravou de verdade ja no banco.
# ==========================================================================
def _arreio():
    return importlib.import_module("test_o_chat_fala_tipado")


def _rodar_turno(arreio, chat_mod, banco, *, sessao, crid, eventos):
    import httpx
    from fastapi import FastAPI  # noqa: F401 — o arreio monta a app

    async def _ida():
        with arreio._TrocaModulosD(arreio._montar_stubs_d(banco)):
            arreio.EVENTOS_DO_GRAFO_D[:] = eventos
            app = arreio._montar_app_d(chat_mod, banco)
            corpo = {"chatInput": "detalhe a apolice", "sessionId": sessao,
                     "companyId": arreio.CO_ALFA_D, "agentId": arreio.AGENTE_D,
                     "assistantMessageId": str(uuid.uuid4())}
            # ⚠️ `crid=None` e um turno REAL sem `client_request_id` (o campo e
            # opcional em `/chat/stream`): e o caso que o PAR DE CONTROLE 4 mede.
            if crid is not None:
                corpo["client_request_id"] = crid
            t = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=t, base_url="http://t",
                                         timeout=30) as c:
                await c.post("/chat/stream", json=corpo,
                             headers={"X-Internal-Key": arreio.CHAVE_INTERNA_D})
        gravadas = [m for m in banco.dados["messages"] if m.get("role") == "assistant"]
        return ((gravadas[0].get("payload") or {}).get("turn") or {}) if gravadas else {}

    return asyncio.run(_ida())


def _postar_turno_sem_crid(arreio, chat_mod, banco, *, sessao):
    """O `/chat/stream` do PAINEL sem `client_request_id` — devolve o status.

    ⚠️ `_rodar_turno` nao serve aqui: ele le a mensagem gravada, e o ponto
    deste caso e que NAO se grava nada.
    """
    import httpx

    async def _ida():
        with arreio._TrocaModulosD(arreio._montar_stubs_d(banco)):
            arreio.EVENTOS_DO_GRAFO_D[:] = [arreio._delta_d("resposta")]
            app = arreio._montar_app_d(chat_mod, banco)
            corpo = {"chatInput": "detalhe a apolice", "sessionId": sessao,
                     "companyId": arreio.CO_ALFA_D, "agentId": arreio.AGENTE_D,
                     "assistantMessageId": str(uuid.uuid4())}
            t = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=t, base_url="http://t",
                                         timeout=30) as c:
                r = await c.post("/chat/stream", json=corpo,
                                 headers={"X-Internal-Key": arreio.CHAVE_INTERNA_D})
                return r.status_code

    return asyncio.run(_ida())


def gate_G2():
    print("\n[G2] o `payload.turn` encontra a invocacao POR JUNCAO")
    arreio = _arreio()
    chat_mod = importlib.import_module("app.api.chat")
    rec = importlib.import_module("app.services.skills.invocation_recorder")

    sessao = str(uuid.uuid4())
    crid = str(uuid.uuid4())

    # 🔴 A LINHA VEM DO ESCRITOR REAL (o mesmo caminho do [G1]), nao de um
    # dicionario escrito a mao: se a escrita e a leitura discordarem do
    # formato, este gate e o que fica vermelho.
    escritor = _banco_do_escritor()
    _invocar_de_verdade(escritor, company_id=arreio.CO_ALFA_D,
                        session_id=sessao, turno=crid,
                        args={"document": CPF_SENTINELA, "user_query": "x"})
    invocacao = dict(escritor.dados["tool_invocations"][0])
    invocacao["started_at"] = "2026-09-14T12:00:00Z"
    invocacao["latency_ms"] = 431

    chave_antiga = os.environ.get("ADMIN_API_KEY")
    os.environ["ADMIN_API_KEY"] = arreio.CHAVE_INTERNA_D
    try:
        banco = arreio._banco_padrao_d(conversas=[])
        banco.dados["tool_invocations"] = [invocacao]
        turno = _rodar_turno(
            arreio, chat_mod, banco, sessao=sessao, crid=crid,
            eventos=[{"kind": "tool_start", "name": TOOL},
                     arreio._delta_d("a apolice esta vigente"),
                     {"kind": "tool_end", "name": TOOL}])

        chamadas = turno.get("tool_calls")
        if not check("[G2] o turno gravado tem `tool_calls`", bool(chamadas),
                     "turn=%r" % (turno,)):
            return
        check("[G2] uma chamada, e e a da ferramenta de apolice",
              len(chamadas) == 1 and chamadas[0].get("capability_key") == CAPABILITY,
              "tool_calls=%r" % (chamadas,))
        check("[G2] a juncao traz status, latencia e erro (o que `stages` nao sabe)",
              chamadas[0].get("status") == "succeeded"
              and chamadas[0].get("latency_ms") == 431
              and "error_code" in chamadas[0],
              "tool_calls=%r" % (chamadas,))
        check("[G2] `stages` continua existindo (um NAO substitui o outro)",
              isinstance(turno.get("stages"), list) and turno.get("stages"))
        # ⛔ PII: nada do argumento vai para o turno.
        check("[G2] o CPF sentinela NAO aparece em lugar nenhum do turno",
              CPF_SENTINELA not in repr(turno))

        # --- PAR DE CONTROLE 1: invocacao de OUTRO turno nao entra ----------
        banco2 = arreio._banco_padrao_d(conversas=[])
        outra = dict(invocacao)
        outra["trace_id"] = rec.chave_de_rastro(sessao, str(uuid.uuid4()))
        banco2.dados["tool_invocations"] = [outra]
        turno2 = _rodar_turno(
            arreio, chat_mod, banco2, sessao=sessao, crid=str(uuid.uuid4()),
            eventos=[{"kind": "tool_start", "name": TOOL},
                     arreio._delta_d("resposta"),
                     {"kind": "tool_end", "name": TOOL}])
        check("[G2] CONTROLE: a invocacao de OUTRO turno da MESMA sessao nao entra",
              "tool_calls" not in turno2, "turn=%r" % (turno2,))

        # --- PAR DE CONTROLE 2: invocacao de OUTRA CORRETORA nao entra ------
        # 🔴 CLAUDE.md 7: o backend usa service role -- quem protege e o filtro
        # no codigo, nao a RLS.
        banco3 = arreio._banco_padrao_d(conversas=[])
        crid3 = str(uuid.uuid4())
        alheia = dict(invocacao)
        alheia["company_id"] = arreio.CO_BETA_D
        alheia["trace_id"] = rec.chave_de_rastro(sessao, crid3)
        banco3.dados["tool_invocations"] = [alheia]
        turno3 = _rodar_turno(
            arreio, chat_mod, banco3, sessao=sessao, crid=crid3,
            eventos=[{"kind": "tool_start", "name": TOOL},
                     arreio._delta_d("resposta"),
                     {"kind": "tool_end", "name": TOOL}])
        check("[G2] CONTROLE: invocacao de OUTRA corretora com a MESMA chave "
              "NAO atravessa", "tool_calls" not in turno3, "turn=%r" % (turno3,))

        # --- PAR DE CONTROLE 3: turno SEM ferramenta nao inventa lista ------
        banco4 = arreio._banco_padrao_d(conversas=[])
        banco4.dados["tool_invocations"] = []
        turno4 = _rodar_turno(
            arreio, chat_mod, banco4, sessao=sessao, crid=str(uuid.uuid4()),
            eventos=[arreio._delta_d("resposta sem ferramenta")])
        check("[G2] CONTROLE: turno sem ferramenta nao grava `tool_calls: []`",
              "tool_calls" not in turno4, "turn=%r" % (turno4,))

        # --- PAR DE CONTROLE 4: A SESSAO INTEIRA NAO VIRA "ESTE TURNO" ------
        #
        # 🔴 O que o juiz de 14/09/2026 apontou: `chave_de_rastro(sessao, None)`
        # devolvia **a sessao pura**, e e exatamente isso que o no de tool grava
        # FORA de turno. Se a leitura do `/chat/stream` montasse a chave sem
        # `client_request_id`, o `.eq("trace_id", chave)` colheria a sessao
        # inteira e a gravaria como "as ferramentas deste turno".
        #
        # 📊 MEDIDO no mesmo dia, e e o elo (protocolo §0.3): a leitura roda
        # SO no modo painel (`chat.py` retorna `StreamingResponse` do widget
        # antes de `_gerar`), e o painel **recusa com 400** um turno sem
        # `client_request_id`. Isto e, hoje a metade da LEITURA nao tem como ser
        # alcancada — o que estava errado de verdade era a metade da ESCRITA (a
        # chave indistinguivel), guardada no [G1].
        #
        # Este par guarda as duas coisas que SAO alcancaveis:
        #   a) a recusa do painel — a trava que torna o resto inalcancavel;
        #   b) que ela e medida no MOTOR, nao lida no texto.
        # ⚠️ A trava escrita ao lado da juncao (`if client_request_id`) e
        # profundidade: ela existe para o dia em que alguem tornar o campo
        # opcional no painel, e nao tem como ficar vermelha enquanto o 400 valer.
        # ⚠️ `chave_de_rastro(s, None)` consulta o TURNO EM VOO. Aqui nao ha
        # turno em voo — e o `marcar_turno(None)` e o que torna isso um fato do
        # teste, e nao uma sobra de contexto de um turno anterior.
        rec.marcar_turno(None)
        chave_fora = rec.chave_de_rastro(sessao, None)
        check("[G2] CONTROLE: fora de turno a chave e `<sessao>|-`, nao a sessao",
              chave_fora == "%s|%s" % (sessao, rec.MARCA_SEM_TURNO)
              and chave_fora != sessao, "chave=%r" % (chave_fora,))
        banco5 = arreio._banco_padrao_d(conversas=[])
        banco5.dados["tool_invocations"] = [dict(invocacao, trace_id=chave_fora)]
        codigo = _postar_turno_sem_crid(arreio, chat_mod, banco5, sessao=sessao)
        check("[G2] 🔴 o painel RECUSA um turno sem `client_request_id` (400)",
              codigo == 400, "status=%r" % (codigo,))
        gravadas = [m for m in banco5.dados["messages"] if m.get("role") == "assistant"]
        check("[G2] e nada foi gravado — a invocacao de fora de turno nao virou "
              "`tool_calls` de ninguem", not gravadas, "msgs=%d" % len(gravadas))
        # 🔴 O PAR do par: com `client_request_id`, a MESMA montagem ACHA.
        # Sem isto, "nao achou" tanto pode ser a trava quanto o arreio quebrado.
        banco6 = arreio._banco_padrao_d(conversas=[])
        crid6 = str(uuid.uuid4())
        banco6.dados["tool_invocations"] = [
            dict(invocacao, trace_id=rec.chave_de_rastro(sessao, crid6))]
        turno6 = _rodar_turno(
            arreio, chat_mod, banco6, sessao=sessao, crid=crid6,
            eventos=[{"kind": "tool_start", "name": TOOL},
                     arreio._delta_d("resposta"),
                     {"kind": "tool_end", "name": TOOL}])
        check("[G2] CONTROLE: o MESMO arreio, COM turno, acha a invocacao",
              bool(turno6.get("tool_calls")), "turn=%r" % (turno6,))
    finally:
        if chave_antiga is None:
            os.environ.pop("ADMIN_API_KEY", None)
        else:
            os.environ["ADMIN_API_KEY"] = chave_antiga


# ==========================================================================
# G3 -- O QUE NUNCA SE GRAVA: o argumento cru
# ==========================================================================
def gate_G3():
    print("\n[G3] o argumento CRU nunca entra no banco de auditoria")
    rec = importlib.import_module("app.services.skills.invocation_recorder")

    resumo = rec.resumo_da_entrada({"document": CPF_SENTINELA, "user_query": "x"})
    check("[G3] `document` vira '[omitido]'",
          resumo.get("document") == "[omitido]", "resumo=%r" % (resumo,))
    check("[G3] `user_query` vira {tipo: texto, tamanho: 1}",
          resumo.get("user_query") == {"tipo": "texto", "tamanho": 1},
          "resumo=%r" % (resumo,))
    for campo in ("cpf", "cnpj", "telefone", "phone", "policy_number", "placa",
                  "token", "password"):
        r = rec.resumo_da_entrada({campo: "0" * 14})
        check("[G3] `%s` tambem e omitido" % campo, r.get(campo) == "[omitido]",
              "r=%r" % (r,))
    # CONTROLE: campo inocente NAO e omitido -- senao o resumo nao serve a nada
    # e "esta tudo protegido" viraria "nao da para auditar nada".
    r = rec.resumo_da_entrada({"pagina": 3, "forcar": True, "ramo": "auto"})
    check("[G3] CONTROLE: campo sem dado pessoal mantem o valor",
          r == {"pagina": 3, "forcar": True,
                "ramo": {"tipo": "texto", "tamanho": 4}}, "r=%r" % (r,))

    # ⚠️ OVER-REDACAO CONHECIDA, medida aqui e registrada como pendencia
    # P-E0011-REDACAO-POR-SUBSTRING: `_CAMPOS_SENSIVEIS` casa por SUBSTRING, e
    # `document_evidence_requested` (um booleano, sem dado pessoal nenhum) casa
    # com `document` e sai `[omitido]`. 🔴 Isto esta ESCRITO como afirmacao para
    # o proximo leitor NAO "consertar" a regra e transformar over-redacao em
    # vazamento: errar para o lado de omitir e a escolha certa, e mexer nela
    # exige medir os 277 registros de novo.
    r2 = rec.resumo_da_entrada({"document_evidence_requested": True})
    check("[G3] a redacao por substring omite ate o booleano "
          "`document_evidence_requested` (over-redacao DECLARADA, nao defeito)",
          r2.get("document_evidence_requested") == "[omitido]", "r=%r" % (r2,))

    # E a prova sobre o que FOI GRAVADO de fato, pelo escritor real.
    banco = _banco_do_escritor()
    _invocar_de_verdade(banco, company_id=str(uuid.uuid4()),
                        session_id=str(uuid.uuid4()), turno=str(uuid.uuid4()),
                        args={"document": CPF_SENTINELA, "user_query": "x"},
                        resultado={"ok": True, "cliente": "NOME DO SEGURADO"})
    linha = banco.dados["tool_invocations"][0]
    check("[G3] a linha gravada NAO tem o CPF sentinela em canto nenhum",
          CPF_SENTINELA not in repr(linha), "linha=%r" % (linha,))
    # 🔴 A MESMA consulta que mediu a producao: 📊 14/09/2026, `input_summary`
    # com 11+ digitos seguidos = **0 de 277**. ⚠️ Sobre `input_summary` e
    # `output_summary`, NAO sobre a linha inteira: o `invocation_key` carrega
    # `int(time.time()*1000)` -- 13 digitos que sao RELOGIO, nao documento. Uma
    # regua que reprovasse por causa deles reprovaria a producao inteira e
    # ensinaria a ignorar o guarda.
    check("[G3] nenhuma sequencia de 11+ digitos em `input_summary`/`output_summary`",
          not re.search(r"\d{11,}", repr(linha.get("input_summary"))
                        + repr(linha.get("output_summary"))),
          "input=%r" % (linha.get("input_summary"),))
    check("[G3] o `input_summary` guarda as CHAVES, nao os valores",
          set((linha.get("input_summary") or {}).keys()) == {"document", "user_query"},
          "input_summary=%r" % (linha.get("input_summary"),))
    check("[G3] o `output_summary` guarda forma e tamanho, nunca o conteudo",
          "NOME DO SEGURADO" not in repr(linha.get("output_summary")),
          "output_summary=%r" % (linha.get("output_summary"),))
    check("[G3] o `input_fingerprint` identifica a entrada sem guarda-la",
          bool(linha.get("input_fingerprint"))
          and CPF_SENTINELA not in str(linha.get("input_fingerprint")))


# ==========================================================================
# G4 -- O SILENCIO NA FALHA PASSA A TER NUMERO
# ==========================================================================
def gate_G4():
    print("\n[G4] a auditoria muda passa a ser CONTADA")
    nodes = importlib.import_module("app.agents.nodes")

    # caminho feliz -> 0  (ja medido no [G1], repetido aqui isolado)
    banco = _banco_do_escritor()
    _invocar_de_verdade(banco, company_id=str(uuid.uuid4()),
                        session_id=str(uuid.uuid4()), turno=str(uuid.uuid4()),
                        args={"user_query": "x"})
    check("[G4] caminho feliz: contador de inertes = 0",
          nodes.registros_inertes() == 0,
          "inertes=%d" % nodes.registros_inertes())

    # sem company_id -> 1, e com o MOTIVO escrito
    nodes.zerar_registros_inertes()
    with _TrocaCliente(_banco_do_escritor()):
        registro = nodes._abrir_registro_de_invocacao(
            {"session_id": "s"}, tool_name=TOOL, tool_args={})
        with registro:
            registro.ok("nada")
    check("[G4] sem `company_id`: contador de inertes = 1",
          nodes.registros_inertes() == 1,
          "inertes=%d" % nodes.registros_inertes())
    check("[G4] e o MOTIVO fica escrito ('sem_company_id')",
          nodes.motivos_inertes().get("sem_company_id") == 1,
          "motivos=%r" % (nodes.motivos_inertes(),))
    check("[G4] o inerte NAO derruba a ferramenta (o `with` roda inteiro)",
          registro.ok("x") is None and registro.erro(codigo="x") is None)

    # 🔴 A prova de que os dois estados CONSEGUEM ser diferentes.
    nodes.zerar_registros_inertes()
    check("[G4] CONTROLE: `zerar_registros_inertes` zera de verdade",
          nodes.registros_inertes() == 0 and nodes.motivos_inertes() == {})


# ==========================================================================
# G5 -- O TURNO ATRAVESSA TASK E THREAD
#
# 🔴 O ELO que ninguem mede sozinho: a chave so chega ao no de tool se o
# ContextVar sobreviver ao `create_task` do `/chat/stream` E ao salto para
# thread que o LangChain faz em tool sincrona. Sem este gate, [G1] provaria a
# montagem da chave e nada sobre ela CHEGAR la (protocolo 0.3).
# ==========================================================================
def gate_G5():
    print("\n[G5] a marca do turno atravessa `create_task` e `to_thread`")
    rec = importlib.import_module("app.services.skills.invocation_recorder")

    async def _prova():
        rec.marcar_turno("turno-A")

        async def _dentro_da_task():
            de_dentro = rec.turno_em_curso()
            na_thread = await asyncio.to_thread(rec.turno_em_curso)
            return de_dentro, na_thread

        # a task COPIA o contexto na criacao -- e e por isso que o
        # `marcar_turno` do `/chat/stream` vem ANTES do `create_task`.
        return await asyncio.create_task(_dentro_da_task())

    de_dentro, na_thread = asyncio.run(_prova())
    check("[G5] a task criada DEPOIS da marca ve o turno", de_dentro == "turno-A",
          "visto=%r" % de_dentro)
    check("[G5] e a thread do executor tambem ve", na_thread == "turno-A",
          "visto=%r" % na_thread)

    # --- PAR DE CONTROLE: task criada ANTES da marca NAO ve --------------
    # 🔴 E isto que prova que a marca e por TURNO, e nao uma global disfarcada.
    async def _controle():
        rec.marcar_turno(None)
        vista = {}

        async def _antes():
            await asyncio.sleep(0.05)
            vista["valor"] = rec.turno_em_curso()

        tarefa = asyncio.create_task(_antes())
        rec.marcar_turno("turno-B")
        await tarefa
        return vista["valor"], rec.turno_em_curso()

    de_fora, aqui = asyncio.run(_controle())
    check("[G5] CONTROLE: task criada ANTES da marca NAO ve o turno",
          de_fora is None, "visto=%r" % de_fora)
    check("[G5] CONTROLE: e quem marcou continua vendo o seu", aqui == "turno-B")

    # o `/chat/stream` marca ANTES do create_task -- a ordem importa
    fonte = _ler(os.path.join(RAIZ, "app", "api", "chat.py"))
    pos_marca = fonte.find("marcar_turno(client_request_id)")
    pos_task = fonte.find("task = asyncio.create_task(_gerar(fila))")
    check("[G5] no `/chat/stream`, `marcar_turno` vem ANTES do `create_task`",
          0 < pos_marca < pos_task, "marca=%d task=%d" % (pos_marca, pos_task))


GATES = {"G1": gate_G1, "G2": gate_G2, "G3": gate_G3, "G4": gate_G4, "G5": gate_G5}


# ==========================================================================
# AS MUTACOES -- (id, arquivo, de, para, gate)
# ==========================================================================
MUTACOES = [
    ("M1", "app/agents/nodes.py",
     "            trace_id=chave_de_rastro(state.get(\"session_id\")))",
     "            trace_id=str(state.get(\"session_id\") or \"\") or None)",
     "G1"),
    ("M1b", "app/agents/nodes.py",
     "            trace_id=chave_de_rastro(state.get(\"session_id\")))",
     "            trace_id=str(state.get(\"session_id\") or \"\") or None)",
     "G2"),
    ("M2", "app/services/skills/invocation_recorder.py",
     '            resumo[chave] = "[omitido]"',
     "            resumo[chave] = valor",
     "G3"),
    ("M3", "app/agents/nodes.py",
     "        _REGISTROS_INERTES += 1",
     "        _REGISTROS_INERTES += 0",
     "G4"),
    # 🔴 M4: o painel deixa de exigir `client_request_id` -- e a trava que hoje
    #    torna a juncao sem turno inalcancavel. Sem ela, um turno sem turno
    #    passa a rodar, e so a trava escrita ao lado da juncao o segura.
    ("M4", "app/api/chat.py",
     '    if modo == "painel" and not client_request_id:',
     '    if False and modo == "painel" and not client_request_id:',
     "G2"),
    # 🔴 M5: o rastro de fora de turno volta a ser a SESSAO PURA -- a metade da
    #    escrita do mesmo defeito.
    ("M5", "app/services/skills/invocation_recorder.py",
     '    return "%s|%s" % (sessao, marca or MARCA_SEM_TURNO)',
     '    return ("%s|%s" % (sessao, marca)) if marca else sessao',
     "G1"),
]


def rodar_mutacoes(filtro=None):
    print("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO; a arvore parada")
    vermelhas = verdes = 0
    for mid, rel, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, rel)
        original = _ler(caminho)
        if de not in original:
            check("%s: o trecho a mutar EXISTE em %s" % (mid, rel), False,
                  "ancora ausente: %r" % de[:80])
            verdes += 1
            continue
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak").name
        shutil.copyfile(caminho, backup)
        try:
            with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
                fh.write(original.replace(de, para, 1))
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--so", gate],
                cwd=RAIZ, capture_output=True, text=True, timeout=600,
                env={**os.environ, "PYTHONIOENCODING": "utf-8",
                     "PYTHONDONTWRITEBYTECODE": "1"})
            falhas = [l.strip() for l in (r.stdout or "").splitlines()
                      if "[FALHOU]" in l]
            if r.returncode != 0 and falhas:
                vermelhas += 1
                print("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:160]))
            else:
                verdes += 1
                print("  [FALHOU] %s NAO deixou %s vermelho (rc=%s)\n%s"
                      % (mid, gate, r.returncode, (r.stdout or r.stderr)[-1500:]))
        finally:
            shutil.copyfile(backup, caminho)   # 🔴 restaura por COPIA
            os.unlink(backup)
            assert _ler(caminho) == original, "restauracao falhou em " + rel
    print("\n  PLACAR DAS MUTACOES: %d vermelhas · %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M") else None
        sys.exit(0 if rodar_mutacoes(filtro) else 1)
    so = args[args.index("--so") + 1] if "--so" in args else None
    print("=" * 74)
    print("  A FERRAMENTA DO TURNO DEIXA RASTRO -- P-PILOTO-18 (BLOCO E)")
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
