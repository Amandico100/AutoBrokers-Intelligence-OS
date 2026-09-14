# -*- coding: utf-8 -*-
r"""G10 — UMA CONVERSA POR CONTRAPARTE. SPEC-EXTRA-001.2 BLOCO E2.

🔴 **O defeito que este guarda fecha.** 📊 Medido no banco de producao em
13/09/2026: **175 conversas-fantasma** de `@lid`, **100% abertas**, 10 delas com
pausa de atendente presa numa linha que ninguem consegue abrir — e a de numero
**175** nasceu enquanto a SPEC era escrita. A causa nao e o `@lid`: e haver
**DUAS resolucoes de conversa sem chave em comum**.

```
webhook.get_or_create_conversation     procura por (company_id, user_id, channel)
espelho_chat._espelhar_com_desfecho    procura por (company_id, user_id, channel)
                                       — e `user_id` sai do telefone, que a
                                         fantasma nao tem
```

📊 E nada no schema impedia a proxima: `conversations_session_id_key` e UNIQUE,
mas o `@lid` gera um `session_id` DIFERENTE — **a fantasma nascia legalmente**.

```
 [GE2a] A CHAVE       o mesmo contato como @lid (com alternativo) e como telefone
                      -> UMA chave. E o LID sem alternativo -> "" (nunca inventar)
 [GE2b] O PIPELINE    `get_or_create_conversation` REAL reusa a conversa aberta
                      achada pela contraparte, e grava `contraparte` ao criar
 [GE2c] O ESPELHO     o resolvedor do espelho faz o mesmo, com a MESMA funcao
 [GE2d] O BANCO       o indice recusa a 2a aberta; e os DOIS PARES: outra
                      corretora e ACEITA, conversa FECHADA nao bloqueia
 [GE2e] OS DOIS MOTORES  a regra do backfill em SQL e a mesma do Python (§9.4)
```

⛔ SEGURANCA: sem rede, sem banco, sem Redis. Telefones e LIDs 100% sinteticos.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_uma_conversa_por_contraparte.py
    ... --so GE2b   ·   ... --mutar   ·   ... --mutar M-E2a
"""
from __future__ import annotations

import ast
import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
WEBHOOK = os.path.join(RAIZ, "app", "api", "webhook.py")
ESPELHO = os.path.join(RAIZ, "app", "services", "atlas", "espelho_chat.py")
M2 = os.path.join(RAIZ, "supabase", "migrations",
                  "20260914_08_spec_extra001_2_contraparte_unica.sql")
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

PASS = 0
FAIL = 0

#: ⛔ 100% SINTETICO. Um LID real tem ~15 digitos e nao comeca com 55.
TELEFONE = "5511900000001"
LID = "199887766554433"
EMPRESA_A = "empresa-A"
EMPRESA_B = "empresa-B"


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O CARREGADOR — a funcao REAL do webhook.py, sem importar o modulo (~77 s)
# ===========================================================================
class _LoggerMudo:
    def __getattr__(self, _nome):
        return lambda *a, **k: None


def carregar_do_fonte(caminho, nomes, extras=None):
    fonte = io.open(caminho, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    escolhidos = [no for no in arvore.body
                  if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and no.name in nomes]
    faltando = set(nomes) - {n.name for n in escolhidos}
    check("todos os nomes pedidos existem em %s" % os.path.basename(caminho),
          not faltando, "sumiram: %s" % sorted(faltando))
    modulo = ast.Module(body=escolhidos, type_ignores=[])
    ns = {"__name__": "webhook_recortado", "asyncio": asyncio,
          "datetime": datetime, "timezone": timezone, "logger": _LoggerMudo(),
          "Optional": __import__("typing").Optional,
          "ZAPIWebhookPayload": object}
    ns.update(extras or {})
    exec(compile(ast.fix_missing_locations(modulo), caminho, "exec"), ns)  # noqa: S102
    return ns


# ⚠️ `_conversa_da_contraparte` e `e_duplicata_do_banco` entram junto (J4):
#    o resolvedor real os chama, e recortar só um dos três provaria um motor
#    que não existe.
MOTOR = carregar_do_fonte(WEBHOOK, ["get_or_create_conversation",
                                   "_conversa_da_contraparte",
                                   "e_duplicata_do_banco"])

from app.services.whatsapp.identidade_do_evento import (  # noqa: E402
    contraparte_de, telefone_do_evento,
)


# ===========================================================================
# O DUBLE DO BANCO — e ele SIMULA o indice unico parcial da M2
# ===========================================================================
class _Unico(Exception):
    pass


class _Consulta:
    def __init__(self, banco, nome):
        self.banco = banco
        self.nome = nome
        self.filtros = {}
        self.negados = {}
        self._linha = None

    # --- leitura -----------------------------------------------------------
    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def neq(self, campo, valor):
        self.negados[campo] = valor
        return self

    def is_(self, campo, _nulo):
        self.filtros[campo] = None
        return self

    def limit(self, _n):
        return self

    def update(self, _dados):
        self._acao = "update"
        return self

    # --- escrita -----------------------------------------------------------
    def insert(self, linha):
        self._linha = dict(linha)
        return self

    def execute(self):
        if self._linha is not None:
            return self._inserir()
        # 🔴 A CORRIDA (J4): as `esconder_leituras` primeiras buscas não
        #    enxergam a linha — é o outro resolvedor criando a conversa DEPOIS
        #    desta busca e ANTES deste insert. O índice, esse, enxerga sempre.
        if self.banco.esconder_leituras > 0:
            self.banco.esconder_leituras -= 1
            return _Resposta([])
        achadas = []
        for linha in self.banco.conversas:
            if all(linha.get(k) == v for k, v in self.filtros.items()) \
                    and all(linha.get(k) != v for k, v in self.negados.items()):
                achadas.append(linha)
        return _Resposta(achadas)

    def _inserir(self):
        linha = dict(self._linha)
        linha.setdefault("id", "conv-%d" % (len(self.banco.conversas) + 1))
        # 🔴 O INDICE UNICO PARCIAL DA M2, aqui como duble:
        #    (company_id, contraparte) WHERE channel='whatsapp'
        #      AND agent_id IS NULL AND status <> 'closed' AND contraparte IS NOT NULL
        if self.banco.indice_ligado and self._no_indice(linha):
            for outra in self.banco.conversas:
                if self._no_indice(outra) \
                        and outra.get("company_id") == linha.get("company_id") \
                        and outra.get("contraparte") == linha.get("contraparte"):
                    raise _Unico('{"code":"23505","message":"duplicate key value '
                                 'violates unique constraint '
                                 '\\"uq_conversations_contraparte_aberta\\""}')
        self.banco.conversas.append(linha)
        return _Resposta([linha])

    @staticmethod
    def _no_indice(linha):
        return (linha.get("channel") == "whatsapp"
                and linha.get("agent_id") is None
                and str(linha.get("status") or "") != "closed"
                and linha.get("contraparte") is not None)


class _Resposta:
    def __init__(self, data):
        self.data = data


class BancoDuble:
    def __init__(self, conversas=None, indice_ligado=True, esconder_leituras=0):
        self.conversas = list(conversas or [])
        self.indice_ligado = indice_ligado
        self.esconder_leituras = int(esconder_leituras)

    def table(self, nome):
        return _Consulta(self, nome)


class _Payload:
    def __init__(self, phone, nome="Segurado"):
        self.phone = phone
        self.senderName = nome


# ===========================================================================
# OS GATES
# ===========================================================================
def ge2a():
    _p("\n[GE2a] a CHAVE: @lid com alternativo e telefone dao a MESMA chave")
    jid = "%s@lid" % LID
    alt = "%s@s.whatsapp.net" % TELEFONE
    por_lid = contraparte_de(jid, alt)
    por_telefone = contraparte_de(TELEFONE)
    por_jid_de_linha = contraparte_de(alt)
    check("@lid + alternativo -> o telefone", por_lid == TELEFONE, por_lid)
    check("telefone cru -> ele mesmo", por_telefone == TELEFONE, por_telefone)
    check("jid de linha -> o telefone", por_jid_de_linha == TELEFONE, por_jid_de_linha)
    check("🔴 UMA chave, nao duas",
          por_lid == por_telefone == por_jid_de_linha,
          (por_lid, por_telefone, por_jid_de_linha))
    check("⛔ @lid SEM alternativo -> \"\" (nunca inventar telefone)",
          contraparte_de(jid) == "", contraparte_de(jid))
    check("⛔ o LID ja gravado em `user_phone` (15 digitos, sem 55) -> \"\"",
          contraparte_de(LID) == "", contraparte_de(LID))
    # 🔴 O PAR que impede a regra de engolir telefone brasileiro: 5548988887777
    #    tem EXATAMENTE 13 digitos e e um celular de verdade.
    check("PAR: um celular BR de 13 digitos NAO e confundido com LID",
          contraparte_de("5548988887777") == "5548988887777",
          contraparte_de("5548988887777"))
    check("e a normalizacao continua sendo a de `telefone_do_evento` (um motor so)",
          contraparte_de(jid, alt) == telefone_do_evento(
              {"remoteJid": jid, "remoteJidAlt": alt}))


def ge2b():
    _p("\n[GE2b] o PIPELINE reusa a conversa da contraparte, e grava a chave")
    # A conversa ja existe, criada quando o chat vinha por @lid: o `user_id` e
    # OUTRO, e so a contraparte as liga.
    banco = BancoDuble([{
        "id": "conv-real", "company_id": EMPRESA_A, "user_id": "user-antigo",
        "channel": "whatsapp", "agent_id": None, "status": "open",
        "contraparte": TELEFONE, "unread_count": 0,
    }])
    conv = asyncio.run(MOTOR["get_or_create_conversation"](
        banco, company_id=EMPRESA_A, user_id="user-NOVO",
        session_id="sessao-nova", message_text="oi",
        payload=_Payload(TELEFONE), channel="whatsapp", agent_id=None))
    check("🔴 reusou a conversa aberta da contraparte", conv == "conv-real", conv)
    check("e NAO criou uma segunda", len(banco.conversas) == 1,
          len(banco.conversas))

    # Conversa nova: a chave nasce preenchida.
    banco2 = BancoDuble([])
    conv2 = asyncio.run(MOTOR["get_or_create_conversation"](
        banco2, company_id=EMPRESA_A, user_id="user-1", session_id="s1",
        message_text="oi", payload=_Payload(TELEFONE), channel="whatsapp",
        agent_id=None))
    check("a conversa nova nasce com `contraparte` preenchida",
          banco2.conversas[0].get("contraparte") == TELEFONE,
          banco2.conversas[0].get("contraparte"))
    check("e devolve o id dela", bool(conv2), conv2)

    # ⛔ O LID cru: a conversa nasce com `contraparte` NULA — nao ganha chave e
    #    nao bloqueia ninguem pelo indice parcial.
    banco3 = BancoDuble([])
    asyncio.run(MOTOR["get_or_create_conversation"](
        banco3, company_id=EMPRESA_A, user_id="user-lid", session_id="s-lid",
        message_text="oi", payload=_Payload(LID), channel="whatsapp",
        agent_id=None))
    check("⛔ conversa de LID cru nasce com `contraparte` NULA",
          banco3.conversas[0].get("contraparte") is None,
          banco3.conversas[0].get("contraparte"))


def ge2f():
    _p("\n[GE2f] 23505 do indice novo NAO mata o turno: o resolvedor rele (J4)")
    # 📊 O defeito medido: `get_or_create_conversation` terminava em
    #    `except: raise`. Com o indice `uq_conversations_contraparte_aberta`
    #    (M2) no ar e DOIS resolvedores (pipeline e espelho), a corrida entre
    #    eles derrubava o turno ANTES de gravar a mensagem: o segurado nao
    #    recebia nada, e nada no log dizia que a conversa ja existia.
    banco = BancoDuble([{
        "id": "conv-do-espelho", "company_id": EMPRESA_A, "user_id": "user-esp",
        "channel": "whatsapp", "agent_id": None, "status": "open",
        "contraparte": TELEFONE, "unread_count": 3,
    }], esconder_leituras=2)   # as 2 buscas do resolvedor nao a enxergam
    conv = asyncio.run(MOTOR["get_or_create_conversation"](
        banco, company_id=EMPRESA_A, user_id="user-pipeline",
        session_id="s-corrida", message_text="oi",
        payload=_Payload(TELEFONE), channel="whatsapp", agent_id=None))
    check("\U0001F534 levou 23505 e RELEU: devolveu a conversa que ja existia",
          conv == "conv-do-espelho", conv)
    check("e NAO criou uma segunda conversa", len(banco.conversas) == 1,
          len(banco.conversas))

    # ⛔ O PAR: 23505 de OUTRA causa (ou a conversa sumiu no meio) continua
    #    subindo. Um `except` que engole tudo devolveria id inventado.
    banco2 = BancoDuble([], esconder_leituras=0)
    banco2.conversas.append({
        "id": "conv-fechada", "company_id": EMPRESA_A, "user_id": "u",
        "channel": "whatsapp", "agent_id": None, "status": "closed",
        "contraparte": TELEFONE, "unread_count": 0})
    # a fechada nao esta no indice, entao nao ha 23505 nenhum: a nova nasce
    conv2 = asyncio.run(MOTOR["get_or_create_conversation"](
        banco2, company_id=EMPRESA_A, user_id="u2", session_id="s2",
        message_text="oi", payload=_Payload(TELEFONE), channel="whatsapp",
        agent_id=None))
    check("PAR: conversa FECHADA nao bloqueia — a nova nasce", conv2 != "conv-fechada",
          conv2)
    check("e o banco fica com as duas", len(banco2.conversas) == 2,
          len(banco2.conversas))

    # ⛔ E o ESPELHO tem o mesmo conserto, com a mesma leitura do 23505.
    fonte_esp = io.open(ESPELHO, encoding="utf-8").read()
    pos_insert = fonte_esp.find('nova = (cliente.table("conversations").insert({')
    trecho = fonte_esp[pos_insert:pos_insert + 3000] if pos_insert > 0 else ""
    check("o espelho tambem trata 23505 na criacao da conversa",
          "23505" in trecho and "duplicate key" in trecho,
          "sem isso o espelho cai inteiro naquela mensagem")


def ge2c():
    _p("\n[GE2c] o ESPELHO usa a MESMA funcao e a MESMA chave")
    fonte = io.open(ESPELHO, encoding="utf-8").read()
    # 🔴 A pergunta do §0.3 ("quem E o escritor HOJE"), sobre a AST do resolvedor
    #    real: ele tem de IMPORTAR `contraparte_de`, procurar por `contraparte`
    #    antes de criar, e GRAVAR a coluna.
    arvore = ast.parse(fonte)
    alvo = None
    for no in ast.walk(arvore):
        if isinstance(no, ast.AsyncFunctionDef) and no.name == "_espelhar_com_desfecho":
            alvo = no
    check("`_espelhar_com_desfecho` existe", alvo is not None)
    if alvo is None:
        return
    trecho = ast.dump(alvo)
    check("importa `contraparte_de` (a mesma funcao do pipeline)",
          "contraparte_de" in trecho)
    check("procura por `contraparte` ANTES de criar",
          trecho.count("'contraparte'") >= 2 or trecho.count('"contraparte"') >= 2,
          trecho.count("'contraparte'"))
    check("e a busca por `user_id` FICA (conversa anterior ao backfill tem chave NULA)",
          "'user_id'" in trecho or '"user_id"' in trecho)
    # 🔴 O par de comportamento, pelo motor puro: o espelho normaliza com
    #    `_digitos(counterparty)`, e `contraparte_de` sobre esse valor da a mesma
    #    chave que o pipeline da sobre `payload.phone`.
    check("mesma chave nas duas portas de entrada",
          contraparte_de("+55 (11) 90000-0001") == contraparte_de(TELEFONE)
          == TELEFONE,
          contraparte_de("+55 (11) 90000-0001"))


def ge2d():
    _p("\n[GE2d] o BANCO: a 2a aberta e recusada — e os DOIS pares")
    aberta = {"id": "conv-1", "company_id": EMPRESA_A, "user_id": "u1",
              "channel": "whatsapp", "agent_id": None, "status": "open",
              "contraparte": TELEFONE, "unread_count": 0}
    banco = BancoDuble([aberta])
    recusou = False
    try:
        banco.table("conversations").insert(
            {"company_id": EMPRESA_A, "channel": "whatsapp", "agent_id": None,
             "status": "open", "contraparte": TELEFONE}).execute()
    except _Unico:
        recusou = True
    check("🔴 a SEGUNDA conversa aberta da mesma contraparte e RECUSADA (23505)",
          recusou and len(banco.conversas) == 1, len(banco.conversas))

    # PAR 1 — outra corretora com a MESMA contraparte: ACEITA.
    banco2 = BancoDuble([dict(aberta)])
    banco2.table("conversations").insert(
        {"company_id": EMPRESA_B, "channel": "whatsapp", "agent_id": None,
         "status": "open", "contraparte": TELEFONE}).execute()
    check("PAR: a MESMA contraparte em OUTRA corretora e ACEITA "
          "(isolar nao e bloquear)", len(banco2.conversas) == 2,
          len(banco2.conversas))

    # PAR 2 — conversa FECHADA nao bloqueia a nova.
    fechada = dict(aberta, status="closed")
    banco3 = BancoDuble([fechada])
    banco3.table("conversations").insert(
        {"company_id": EMPRESA_A, "channel": "whatsapp", "agent_id": None,
         "status": "open", "contraparte": TELEFONE}).execute()
    check("PAR: conversa FECHADA nao bloqueia a nova", len(banco3.conversas) == 2,
          len(banco3.conversas))

    # PAR 3 — a fantasma antiga (`contraparte` NULA) nao trava ninguem.
    fantasma = dict(aberta, id="conv-f", contraparte=None)
    banco4 = BancoDuble([fantasma])
    banco4.table("conversations").insert(
        {"company_id": EMPRESA_A, "channel": "whatsapp", "agent_id": None,
         "status": "open", "contraparte": None}).execute()
    check("PAR: duas linhas com `contraparte` NULA convivem (indice parcial)",
          len(banco4.conversas) == 2, len(banco4.conversas))


def ge2e():
    _p("\n[GE2e] OS DOIS MOTORES: a regra do backfill e a mesma do Python")
    # 🔴 CLAUDE.md §9.4, o corolario: "um padrao medido com um motor e aplicado
    #    com outro e um padrao sobre outra coisa". A recusa de `_parece_telefone`
    #    e `length >= 13 AND nao comeca com 55`. Se o SQL do backfill nao
    #    carregar as DUAS clausulas, ele nao e a mesma regra — e os LIDs entram
    #    como se fossem telefone.
    #
    # ⚠️ Esta e a EXCECAO legitima do §9.4: regex sobre a DECLARACAO, para
    #    conferir a FORMA dela. O comportamento continua sendo afirmado pelo
    #    motor, em GE2a.
    check("a migration M2 existe", os.path.exists(M2), M2)
    if not os.path.exists(M2):
        return
    sql = io.open(M2, encoding="utf-8").read()
    corpo = sql.split("(b) O BACKFILL")[-1].split("(c) O")[0]
    check("o backfill recusa `length(...) >= 13`", ">= 13" in corpo)
    check("e recusa quem nao comeca com '55'", "<> '55'" in corpo)
    check("e so preenche onde `contraparte` ainda e NULA",
          "contraparte IS NULL" in corpo)
    check("⛔ o indice NAO e criado com CONCURRENTLY (tabela de 879 linhas, "
          "14/09/2026 — e CONCURRENTLY exigiria rodar fora de transacao)",
          "INDEX CONCURRENTLY" not in sql.upper())
    check("o indice traz as QUATRO clausulas do contrato",
          all(c in sql for c in ("channel = 'whatsapp'", "agent_id IS NULL",
                                 "status <> 'closed'", "contraparte IS NOT NULL")))
    check("e a consulta D0 de duplicatas esta escrita ANTES do indice",
          "having count(*) > 1" in sql.lower())


GATES = {"GE2a": ge2a, "GE2b": ge2b, "GE2f": ge2f, "GE2c": ge2c, "GE2d": ge2d, "GE2e": ge2e}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
MUTACOES = [
    # (a) 🔴 A MUTACAO DO CARD: desligar a normalizacao de `@lid`.
    #     O LID deixa de resolver pelo alternativo -> duas chaves.
    ("M-E2a", "app/services/whatsapp/identidade_do_evento.py",
     '    if remoto.endswith("@lid"):',
     "    if False:",
     "GE2a"),
    # (b) a busca por contraparte some do pipeline -> a fantasma nº 176 nasce.
    # \u26a0\ufe0f A ancora mudou em 14/09/2026 (J4): a busca inline virou
    #    `_conversa_da_contraparte`, a MESMA funcao que a releitura do 23505
    #    usa. Desligar a funcao desliga as duas pontas de uma vez.
    ("M-E2b", "app/api/webhook.py",
     "    if not contraparte:\n        return None",
     "    return None  # MUTACAO\n    if not contraparte:\n        return None",
     "GE2b"),
    # (c) a coluna deixa de ser gravada na criacao -> a chave nunca existe.
    ("M-E2c", "app/api/webhook.py",
     '            "contraparte": contraparte or None,',
     '            "contraparte": None,',
     "GE2b"),
    # (d) o `_parece_telefone` afrouxa -> o LID de 15 digitos vira "telefone",
    #     e a fantasma passa a ganhar chave (e a bloquear a conversa real).
    ("M-E2d", "app/services/whatsapp/identidade_do_evento.py",
     "    if len(digitos) >= DIGITOS_DE_TELEFONE_BR and not digitos.startswith(\"55\"):\n"
     "        return False",
     "    if False:\n        return False",
     "GE2a"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `text=True` sozinho decodifica com a codepage do Windows (cp1252) e
        # ESTOURA no primeiro emoji da saida — `r.stdout` volta VAZIO, `falhas`
        # fica vazia, e a mutacao vermelha e contada como verde. Medido em
        # 14/09/2026: M-E3b (4 linhas [FALHOU]) reportada como "NAO deixou
        # vermelho". ⚠️ Um harness que nao le a saida nao mede mutacao nenhuma.
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-e0012g10").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  G10 -- UMA CONVERSA POR CONTRAPARTE  (SPEC-EXTRA-001.2 E2)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_uma_conversa_por_contraparte():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
