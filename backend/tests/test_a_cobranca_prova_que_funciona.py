# -*- coding: utf-8 -*-
"""SPEC-EXTRA-001.6 -- A COBRANCA PROVA QUE FUNCIONA. Os guardas G1..G8 e G12.

O QUE ELE GUARDA (proposta §11; BLOCO 0 medido em 13/09/2026)

  G1  o texto REAL da cobranca vira UM balao pelos dois caminhos (porta real e modo
      teste) -- e a conversa (follow-up, saudacao) continua em baloes. CONTROLE:
      o mesmo texto, humanizado, parte em 2+; o dublê VE a diferenca.
      📊 13/09: texto 332 ch -> 2 baloes · nota 321 -> 2 · teste 520 -> 3.
  G2  job `failed` com `error IS NULL` e `evidence.message` cheio -> o motivo
      aparece. O corpus e a linha REAL da Mapfre de 11/09.
      📊 `error` e NULL em 100% dos jobs de cobranca da historia.
  G3  `interpret_login` das 6 journeys sobre as 6 telas REAIS transcritas
      (`tests/corpus/telas_reais_de_portal/`): ZERO "nao reconhecida" para tela de
      credencial recusada; NENHUMA journey classifica `done` uma tela de login;
      os dashboards reais continuam `done`/indecisos, nunca `failed`.
  G4  `attendant_name` vazio em modo real -> rotina RETIDA, zero envios, motivo
      em portugues. CONTROLE: em `test` o default "nossa equipe" continua.
  G5  uma linha de `platform_sends` por COMPONENTE (`billing` · `billing_nota` ·
      `billing_doc`), o PDF contado, e `context_note_for` devolvendo UMA linha
      de cobranca para um cliente com 1 cobranca + 3 boletos.
  G6..G8, G12  (BLOCO 1 / BLOCO 4 -- entram quando os blocos entrarem)

COMO ELE FUNCIONA -- sem rede, sem banco, sem mensagem
  🔴 CADA GATE EXECUTA O MOTOR (CLAUDE.md §9.4): `send_message` REAL com um
  provider dublê que CONTA os baloes que chegariam ao canal; `_entregar_agora`
  REAL; `_send_test_messages` REAL; `normalize_billing_config` REAL;
  `interpret_login` REAL de cada journey sobre o texto REAL das telas.
  Nenhum helper reimplementa a regra.

⛔ SEGURANCA: nenhuma mensagem sai; telefones sinteticos 5500900000001+ (DDD 00
   nao existe); corretora sentinela "Corretora Alfa"; nenhum nome real.

Rodar:  PYTHONIOENCODING=utf-8 python tests/test_a_cobranca_prova_que_funciona.py
        (de dentro de `backend/`)  ·  `--so G3` roda so um gate
        `--mutar` roda as mutacoes M1..M5 por COPIA, cada uma em SUBPROCESSO sobre
        o arquivo mutado, restaurando por copia em `finally`. `--mutar M3` so ela.
        ⛔ `--mutar` escreve em `backend/app/` e `backend/portal_worker/` -- so
        com a arvore PARADA. ⛔ Nunca `git checkout` para restaurar.
"""
from __future__ import annotations

import asyncio
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

PASS = FAIL = 0


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


CORPUS_TELAS = os.path.join(RAIZ, "tests", "corpus", "telas_reais_de_portal")
ACERVO = json.loads(_ler(os.path.join(RAIZ, "tests", "corpus", "cobranca_acervo_2026-09-11.json")))
CO_ALFA = ACERVO["company_id"]
TEL_EQUIPE = "5500900000009"
TEL_TESTE = "5500900000008"
MAPFRE_MSG_REAL = "a MAPFRE recusou a credencial (autenticacao invalida)"   # 📊 evidence.message de 11/09


# ==========================================================================
# O DUBLE DO CANAL -- conta os baloes que `send_message` entregaria
# ==========================================================================

class _Resultado:
    ok = True
    success = True


class ProviderDuble:
    """O que o Evolution receberia. `send_text` e chamado UMA vez por balao."""

    def __init__(self):
        self.textos = []

    def send_text(self, to_number, text):
        self.textos.append(str(text))
        return _Resultado()


def armar_canal():
    """Liga o provider dublê no seam REAL de `send_message` e devolve o contador."""
    import app.services.whatsapp.registry as REG
    import app.services.whatsapp.voz_propria as VP
    import app.services.whatsapp_service as WS

    duble = ProviderDuble()
    REG.resolve_provider = lambda integration: duble
    VP.registrar_nossa_fala = lambda *a, **k: None
    WS._dormir = lambda *a, **k: None

    class ServicoDuble(WS.WhatsappService):
        documentos = []

        def send_document(self, to_number, url, filename, integration):
            ServicoDuble.documentos.append((to_number, url, filename))
            return True

    WS.get_whatsapp_service = lambda: ServicoDuble()
    return duble, ServicoDuble


INTEGRACAO = {"id": "int-alfa", "provider": "evolution-go", "company_id": CO_ALFA,
              "config": {}, "is_active": True}


def item_do_acervo(indice=1):
    return dict(ACERVO["itens"][indice])


def cfg(modo="equipe", **over):
    from app.services import billing_collection as BC

    raw = {"kind": "billing_collection", "send_mode": modo, "team_number": TEL_EQUIPE,
           "test_number": TEL_TESTE, "confirmacao_cliente": True,
           "attendant_name": "Atendente Alfa", "brokerage_name": "Corretora Alfa"}
    raw.update(over)
    return BC.normalize_billing_config(raw)


def capturar_registros():
    """Troca `record_platform_send` por um coletor `(phone, kind, summary)`."""
    from app.services import platform_outbound as PO

    linhas = []

    async def _rec(company_id, phone, kind, summary):
        linhas.append({"company_id": str(company_id), "phone": str(phone),
                       "kind": str(kind), "summary": str(summary)})

    PO.record_platform_send = _rec
    return linhas


# ==========================================================================
# G1 -- UM BALAO pelos dois caminhos
# ==========================================================================

def gate_G1():
    print("\n[G1] o texto REAL da cobranca vira UM balao -- porta real e modo teste")
    from app.services import billing_collection as BC
    from app.services import platform_outbound as PO
    from app.services.whatsapp.balloons import split_whatsapp_balloons

    c = cfg("equipe")
    item = item_do_acervo(1)
    texto = BC.build_customer_message(item, c["message_template"], c)
    nota = BC._nota_interna_para_a_equipe(item, c)

    # CONTROLE -- o texto real, humanizado, PARTE. Sem isto, "1 balao" nao
    # provaria que alguem decidiu nada (CLAUDE.md §9.3).
    check("CONTROLE: o texto real humanizado parte em 2+ baloes (%d ch)" % len(texto),
          len(split_whatsapp_balloons(texto) or [texto]) >= 2,
          len(split_whatsapp_balloons(texto) or [texto]))
    check("CONTROLE: a nota interna humanizada parte em 2+ baloes (%d ch)" % len(nota),
          len(split_whatsapp_balloons(nota) or [nota]) >= 2)

    # A decisao mora no produto, por `kind`.
    check("`e_documento('billing_equipe')`", PO.e_documento("billing_equipe") is True)
    check("`e_documento('billing_equipe_nota')`", PO.e_documento("billing_equipe_nota") is True)
    check("`e_documento('billing_cliente')`", PO.e_documento("billing_cliente") is True)
    check("`e_documento('acionamento_followup')` e FALSO -- conversa continua conversa",
          PO.e_documento("acionamento_followup") is False)
    check("e a saudacao de religamento tambem nao e documento",
          PO.e_documento("saudacao_religamento") is False)

    duble, _ = armar_canal()
    capturar_registros()

    async def entregar(kind, t):
        duble.textos.clear()
        r = await PO._entregar_agora(CO_ALFA, TEL_EQUIPE, t, kind, "s", integration=INTEGRACAO)
        return r, len(duble.textos)

    for kind, t, rotulo in (("billing_equipe", texto, "o texto final"),
                            ("billing_equipe_nota", nota, "a nota interna"),
                            ("billing_cliente", texto, "o texto ao cliente")):
        r, n = asyncio.run(entregar(kind, t))
        check("porta REAL · %s (`%s`) chega em UM balao" % (rotulo, kind), r.get("ok") and n == 1,
              "ok=%s baloes=%d" % (r.get("ok"), n))
        check("  ... e chega INTEIRO (o balao e o texto)", duble.textos == [t])

    r, n = asyncio.run(entregar("acionamento_followup", texto))
    check("CONTROLE: o MESMO texto como conversa (`acionamento_followup`) parte em %d baloes" % n,
          r.get("ok") and n >= 2, n)

    # -- o modo TESTE, pelo motor `_send_test_messages` ----------------------
    duble.textos.clear()
    c_teste = cfg("test")
    BC._find_whatsapp_integration = lambda client, company_id: INTEGRACAO
    BC._already_sent_recibos = lambda *a, **k: set()
    BC._signed_boleto_url = lambda client, path: ""
    BC._record_sent = lambda *a, **k: True

    async def _governador(company_id, orcamento_s, *, para_numero_de_teste=False):
        return True, "", 0.0

    async def _reg(*a, **k):
        return None

    BC._esperar_o_governador = _governador
    BC._registrar_no_governador = _reg
    rotina = {"id": "rot-alfa", "company_id": CO_ALFA, "config": c_teste,
              "delivery": {"number": TEL_TESTE}}
    blockers = []
    enviados = asyncio.run(BC._send_test_messages(None, rotina, [item], [], c_teste, blockers))
    check("modo TESTE: 1 simulacao enviada pelo motor", len(enviados) == 1 and enviados[0].get("ok"),
          (enviados, blockers))
    check("modo TESTE: a simulacao (%d ch) chega em UM balao" % (len(duble.textos[0]) if duble.textos else 0),
          len(duble.textos) == 1, len(duble.textos))
    check("CONTROLE: a mesma simulacao humanizada partiria em 3",
          bool(duble.textos) and len(split_whatsapp_balloons(duble.textos[0])) >= 3)


# ==========================================================================
# G2 -- o motivo do portal aparece, inclusive no `failed`
# ==========================================================================

def gate_G2():
    print("\n[G2] `failed` com `error IS NULL` e `evidence.message` cheio -> o motivo aparece")
    from app.services import billing_collection as BC

    job_real = {"portal_key": "mapfre_corretor", "status": "failed", "error": None,
                "evidence": {"message": MAPFRE_MSG_REAL}}
    linha = BC._blocker_do_job(job_real)
    check("a linha do relatorio traz o motivo REAL da Mapfre", MAPFRE_MSG_REAL in linha, linha)
    check("e diz de que portal e", "mapfre_corretor" in linha and "failed" in linha, linha)

    # CONTROLE: `error` continua valendo quando e o unico que existe (requeue).
    so_error = BC._blocker_do_job({"portal_key": "hdi_corretor", "status": "failed",
                                   "error": "worker reiniciou", "evidence": {}})
    check("CONTROLE: sem `evidence.message`, `error` ainda aparece", "worker reiniciou" in so_error, so_error)
    nada = BC._blocker_do_job({"portal_key": "hdi_corretor", "status": "timeout", "error": None, "evidence": {}})
    check("sem nenhum dos dois, diz que nao ha motivo registrado", "sem motivo registrado" in nada, nada)
    nh = BC._blocker_do_job({"portal_key": "zurich_corretor", "status": "needs_human", "error": None,
                             "evidence": {"message": "a Zurich devolveu http 200 com ZERO parcelas"}})
    check("CONTROLE: `needs_human` continua com a frase de sempre", nh.startswith("portal zurich_corretor: precisa de humano (a Zurich"), nh)
    check("`done` nao gera blocker", BC._blocker_do_job({"portal_key": "x", "status": "done"}) == "")


# ==========================================================================
# G3 -- as 6 journeys sobre as 6 telas REAIS
# ==========================================================================

JOURNEYS = ("allianz", "hdi", "mapfre", "tokiomarine", "yelum", "zurich")
MODULO = {"allianz": "allianz_corretor", "hdi": "hdi_corretor", "mapfre": "mapfre_corretor",
          "tokiomarine": "tokio_corretor", "yelum": "yelum_corretor", "zurich": "zurich_corretor"}
TELAS = {
    # tela -> (journey dona, e credencial recusada?)
    "allianz_corretor-needs_human-20260911.txt": ("allianz", True),
    "mapfre_corretor-failed-20260911.txt": ("mapfre", True),
    "zurich_corretor-needs_human-20260911.txt": ("zurich", False),   # dashboard logado (varredura vazia)
    "hdi_corretor-done-20260911.txt": ("hdi", False),
    "tokiomarine_corretor-done-20260911.txt": ("tokiomarine", False),
    "yelum_corretor-done-20260911.txt": ("yelum", False),
}
# ⚠️ Nao existe print real de dashboard da Allianz (ultimo `done` 17/08, antes da
#    prova de desfecho). Este e o texto SINTETICO que ja vivia no teste da SPEC-023.
ALLIANZ_DASHBOARD_SINTETICO = "Allianz Corretor principal Parcelas Inadimplentes Nova Cotacao Sair"


def gate_G3():
    print("\n[G3] `interpret_login` das 6 journeys x 6 telas reais: credencial recusada = `failed`")
    mods = {}
    for j in JOURNEYS:
        try:
            mods[j] = importlib.import_module("portal_worker.journeys." + MODULO[j])
        except Exception as e:  # noqa: BLE001
            check("journey %s importa" % j, False, "%s: %s" % (type(e).__name__, e))
    for j, m in mods.items():
        check("`%s.interpret_login` existe e e puro (texto, url)" % j, callable(getattr(m, "interpret_login", None)))

    textos = {t: _ler(os.path.join(CORPUS_TELAS, t)) for t in TELAS}
    check("o corpus tem as 6 telas", all(textos[t].strip() for t in TELAS))

    def classificar(j, texto):
        try:
            return mods[j].interpret_login(texto, "")
        except Exception as e:  # noqa: BLE001
            return types.SimpleNamespace(status="EXCECAO", message=str(e))

    for tela, (dona, recusada) in TELAS.items():
        r_dona = classificar(dona, textos[tela]) if dona in mods else None
        if recusada:
            check("%s -> a propria journey diz `failed` (credencial recusada), nao 'nao reconhecida'" % tela,
                  r_dona is not None and getattr(r_dona, "status", None) == "failed",
                  getattr(r_dona, "status", r_dona) and getattr(r_dona, "message", ""))
        else:
            st = getattr(r_dona, "status", None) if r_dona is not None else None
            check("%s (dashboard logado) -> a propria journey NAO diz `failed` (%s)" % (tela, st or "texto nao decide"),
                  st in (None, "done"), (st, getattr(r_dona, "message", "")))
        # 🔴 o inverso do obvio: NENHUMA journey pode dar `done` numa tela de LOGIN
        if recusada:
            for j in mods:
                r = classificar(j, textos[tela])
                check("  %s sobre %s nunca e `done` (falso positivo)" % (j, tela.split("-")[0]),
                      getattr(r, "status", None) != "done", getattr(r, "status", None))

    # controles positivos
    if "allianz" in mods:
        r = mods["allianz"].interpret_login(ALLIANZ_DASHBOARD_SINTETICO)
        check("CONTROLE (sintetico): o dashboard da Allianz continua `done`", r.status == "done", r)
        r = mods["allianz"].interpret_login("Usuario ou senha invalida")
        check("CONTROLE de compatibilidade: a frase antiga ainda da `failed`", r.status == "failed", r)
        # o dialeto do motor: cada entrada de _FAIL tem de ser IGUAL a `_norm` dela mesma
        fora = [f for f in mods["allianz"]._FAIL if mods["allianz"]._norm(f) != f]
        check("toda frase de `_FAIL` esta no dialeto do `_norm` (sem acento, sem maiuscula)", not fora, fora)
        n = mods["allianz"]._norm(textos["allianz_corretor-needs_human-20260911.txt"])
        check("o texto REAL normalizado contem 'acesso negado' E 'valide os dados'",
              "acesso negado" in n and "valide os dados" in n)
    if "hdi" in mods:
        r = mods["hdi"].interpret_login(textos["hdi_corretor-done-20260911.txt"], "https://www.hdi.com.br/digital2/home")
        check("CONTROLE (real): o dashboard da HDI e `done`", r.status == "done", r)


# ==========================================================================
# G4 -- sem o nome de quem assina, a rotina nao sai
# ==========================================================================

def gate_G4():
    print("\n[G4] `attendant_name` vazio em modo real -> RETIDA, com motivo em portugues")
    from app.services import billing_collection as BC

    sem = cfg("equipe", attendant_name="")
    check("`equipe` sem nome -> `retido_legado` (nada sai)", sem["send_mode"] == BC.MODO_RETIDO, sem["send_mode"])
    check("  ... e o motivo fala de quem ASSINA", "assina" in str(sem.get("retido_motivo")), sem.get("retido_motivo"))
    check("  ... e o modo escolhido continua legivel", sem.get("send_mode_original") == "equipe")
    sem2 = cfg("cliente", attendant_name="   ")
    check("`cliente` com nome em branco -> retido tambem", sem2["send_mode"] == BC.MODO_RETIDO, sem2["send_mode"])
    sem3 = cfg("equipe")
    sem3_raw = {k: v for k, v in sem3.items()}
    sem3_raw.pop("attendant_name", None)
    check("`equipe` sem a CHAVE (o config real de 13/09 nao a tem) -> retido",
          BC.normalize_billing_config({"kind": "billing_collection", "send_mode": "equipe",
                                       "team_number": TEL_EQUIPE})["send_mode"] == BC.MODO_RETIDO)
    com = cfg("equipe", attendant_name="Atendente Alfa")
    check("CONTROLE: com o nome, `equipe` segue `equipe`", com["send_mode"] == "equipe", com["send_mode"])
    teste = cfg("test", attendant_name="")
    check("CONTROLE: em `test` sem nome NAO retem (destino e a propria corretora)", teste["send_mode"] == "test")
    txt = BC.build_customer_message(item_do_acervo(1), teste["message_template"], teste)
    check("  ... e o default 'nossa equipe' continua valendo la", "nossa equipe" in txt)
    # a rotina inteira, retida, nao chama a porta
    entregas = asyncio.run(BC._entregar_cobranca_real(None, {"id": "r", "company_id": CO_ALFA}, [item_do_acervo(1)], [], sem, []))
    check("`_entregar_cobranca_real` com o config retido devolve ZERO entregas", entregas == [], entregas)


# ==========================================================================
# G5 -- uma linha por COMPONENTE; o PDF contado; o leitor humano ve UMA cobranca
# ==========================================================================

class _Q:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a):
        return self

    def gte(self, *a):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        return types.SimpleNamespace(data=list(self._rows))


class _Supa:
    def __init__(self, rows):
        self.client = self
        self._rows = rows

    def table(self, name):
        assert name == "platform_sends", name
        return _Q(self._rows)


def gate_G5():
    print("\n[G5] `platform_sends`: `billing` · `billing_nota` · `billing_doc` -- e o leitor ve UMA cobranca")
    from app.services import billing_collection as BC
    from app.services import platform_outbound as PO
    import app.core.database as DB

    duble, Svc = armar_canal()
    linhas = capturar_registros()
    c = cfg("equipe")
    item = item_do_acervo(1)
    texto = BC.build_customer_message(item, c["message_template"], c)
    nota = BC._nota_interna_para_a_equipe(item, c)

    async def _assinar(documento):
        return "https://cofre.exemplo/boleto.pdf", str(documento.get("filename") or "boleto.pdf")

    PO._assinar_documento = _assinar
    doc = {"bucket": "portal-evidence", "path": "x/y.pdf", "filename": "boleto-B-0001.pdf"}

    async def _tudo():
        await PO._entregar_agora(CO_ALFA, TEL_EQUIPE, nota, "billing_equipe_nota", "nota", integration=INTEGRACAO)
        await PO._entregar_agora(CO_ALFA, TEL_EQUIPE, texto, "billing_equipe", "cobranca", integration=INTEGRACAO,
                                 documento=doc)

    asyncio.run(_tudo())
    kinds = [l["kind"] for l in linhas]
    check("nota -> `billing_nota`; texto -> `billing`; PDF -> `billing_doc` (3 linhas, uma por componente)",
          sorted(kinds) == ["billing", "billing_doc", "billing_nota"], kinds)
    check("o PDF foi de fato entregue pelo dublê (`send_document` chamado 1x)", len(Svc.documentos) == 1, Svc.documentos)
    check("o texto da cobranca e contado com o `kind` de sempre, `billing` (o modo teste grava assim)",
          "billing" in kinds and "billing_equipe" not in kinds, kinds)

    # o modo TESTE tambem conta o PDF
    linhas.clear()
    asyncio.run(BC._registrar_documento_no_governador(CO_ALFA, TEL_TESTE, item))
    check("modo teste: o PDF vira uma linha `billing_doc`", [l["kind"] for l in linhas] == ["billing_doc"], linhas)

    # 🔴 O LEITOR HUMANO: 1 cobranca + 3 boletos + 1 nota = UMA linha de contexto
    agora = PO._agora().isoformat()
    rows = [{"phone": TEL_EQUIPE, "kind": "billing", "summary": "cobranca da parcela (Tokio)", "sent_at": agora},
            {"phone": TEL_EQUIPE, "kind": PO.KIND_DO_DOCUMENTO_DA_COBRANCA, "summary": "boleto anexado (1)", "sent_at": agora},
            {"phone": TEL_EQUIPE, "kind": PO.KIND_DO_DOCUMENTO_DA_COBRANCA, "summary": "boleto anexado (2)", "sent_at": agora},
            {"phone": TEL_EQUIPE, "kind": PO.KIND_DO_DOCUMENTO_DA_COBRANCA, "summary": "boleto anexado (3)", "sent_at": agora},
            {"phone": TEL_EQUIPE, "kind": "billing_nota", "summary": "nota interna", "sent_at": agora}]
    DB.get_supabase_client = lambda: _Supa(rows)
    nota_ctx = asyncio.run(PO.context_note_for(CO_ALFA, TEL_EQUIPE)) or ""
    check("`context_note_for` devolve UMA linha de cobranca (nao tres boletos)",
          nota_ctx.count("cobranca da parcela") == 1 and "boleto anexado" not in nota_ctx and "nota interna" not in nota_ctx,
          nota_ctx)
    # CONTROLE: a mutacao M5 grava o PDF como `billing` -- e ai o contexto encheria.
    rows_m5 = [dict(r, kind="billing") for r in rows]
    DB.get_supabase_client = lambda: _Supa(rows_m5)
    ctx_m5 = asyncio.run(PO.context_note_for(CO_ALFA, TEL_EQUIPE)) or ""
    check("CONTROLE: se tudo fosse `billing`, o contexto teria 3 pecas (o guarda consegue ver)",
          ctx_m5.count("(em ") == 3, ctx_m5)
    check("nenhum card da Central conta componente (heartbeat.py nao cita `billing_doc`/`billing_nota`)",
          "billing_doc" not in _ler(os.path.join(RAIZ, "app", "core", "heartbeat.py"))
          and "billing_nota" not in _ler(os.path.join(RAIZ, "app", "core", "heartbeat.py")))


# ==========================================================================
# AS MUTACOES -- (id, arquivo, de, para, gate)
# ==========================================================================

MUTACOES = [
    ("M1", "app/services/platform_outbound.py",
     '    "billing_cliente",       # o texto ao segurado, quando o modo cliente for ligado\n', "", "G1"),
    ("M2", "app/services/billing_collection.py",
     '    motivo = ((job or {}).get("evidence") or {}).get("message") or (job or {}).get("error")\n',
     '    motivo = (job or {}).get("error")\n', "G2"),
    # 🔴 as DUAS frases: tirar so "acesso negado" deixaria "valide os dados" casar
    #    e o guarda continuaria verde -- mutacao que nao muda comportamento nao mede.
    ("M3", "portal_worker/journeys/allianz_corretor.py",
     '    "acesso negado",\n    "valide os dados",\n', "", "G3"),
    ("M4", "app/services/billing_collection.py",
     "    elif send_mode in MODOS_REAIS and not str(\n", "    elif False and not str(\n", "G4"),
    ("M5", "app/services/platform_outbound.py",
     'KIND_DO_DOCUMENTO_DA_COBRANCA = "billing_doc"\n', 'KIND_DO_DOCUMENTO_DA_COBRANCA = "billing"\n', "G5"),
]

GATES = {"G1": gate_G1, "G2": gate_G2, "G3": gate_G3, "G4": gate_G4, "G5": gate_G5}


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
                               cwd=RAIZ, capture_output=True, text=True, timeout=600,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if r.returncode != 0 and falhas:
                vermelhas += 1
                print("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:160]))
            else:
                verdes += 1
                print("  [FALHOU] %s NAO deixou %s vermelho (rc=%s)\n%s" % (mid, gate, r.returncode, (r.stdout or r.stderr)[-1200:]))
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
    print("=" * 70)
    print("  SPEC-EXTRA-001.6 -- A COBRANCA PROVA QUE FUNCIONA")
    print("=" * 70)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            check("%s roda sem excecao" % gid, False, "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()[-800:]))
    print("\n" + "=" * 70)
    print("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
    print("=" * 70)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
