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
  G6  a dedup vale SEMPRE; `BILLING_DEDUP_TEST_DISABLED=1` DESLIGA, e so em `test`.
      CONTROLE pelo motor: `_send_test_messages` com o recibo ja no ledger nao
      reenvia; com a flag, reenvia. 📊 a de 17/08 produziu os MESMOS 7 boletos
      em 10 e em 11/09.
  G7  `agrupar_por_segurado` sobre o ACERVO de 10-11/09 (7 itens, 4 segurados):
      4 parcelas do mesmo CNPJ = 1 grupo = 1 mensagem + 4 PDFs + 4 RESERVAS;
      dois segurados nunca se fundem; sem documento o fallback e o NOME; dois
      portais nunca cabem na mesma mensagem; dois `company_id` nunca fazem grupo
      misto; `segurado_chave` NAO leva portal e `chave_do_grupo` leva.
  G8  a janela de N dias por `segurado_chave` (SEM o portal): retem com motivo,
      DATA e a ORIGEM da identidade; 8 dias cobra; sem documento tambem retem; a
      mesma pessoa na OUTRA seguradora tambem; e o ledger da outra corretora
      NUNCA atravessa.
  G10 a rotina enfileira `login_check` de CADA portal antes de qualquer
      `cobranca_sweep`; breaker aberto (`credencial_recusada` / `fora_do_ar`
      dentro do prazo) nao gera job nenhum; canario reprovado nao abre varredura.
  G12  (BLOCO 4 -- entra quando o bloco entrar)

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
        `--mutar` roda as mutacoes M1..M10 por COPIA, cada uma em SUBPROCESSO sobre
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
    enviados = asyncio.run(BC._send_test_messages(BancoLeve(), rotina, [item], [], c_teste, blockers))
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
# O BANCO LEVE -- so o que a janela de N dias, o ledger e a reserva pedem
# ==========================================================================
#
# ⚠️ Ele NAO implementa regra nenhuma da cobranca: e acesso a dado (select com
# `eq`/`in_`, update, e o RPC da reserva devolvendo `ganhou`). Quem decide o que
# fazer com as linhas e sempre o motor do produto (CLAUDE.md §9.4). Quem prova a
# funcao do banco contra o Postgres de verdade e o VERIFY da migration.

CO_BETA = "bbbbbbbb-0000-0000-0000-00000000b2fa"
#: 🔴 O valor ANTIGO da flag, montado em duas partes DE PROPOSITO: escrito
#: inteiro, este arquivo seria o proprio sobrevivente que o §0.4 manda cacar.
VALOR_ANTIGO_DA_FLAG = "BILLING_DEDUP_TEST_" + "ENABLED"


class _Tabela:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self.op, self.carga, self.colunas = "select", None, "*"
        self.filtros, self.dentro = [], []

    def select(self, *a, **k):
        self.colunas = str(a[0]) if a else "*"
        return self

    def eq(self, c, v):
        self.filtros.append((str(c), v))
        return self

    def in_(self, c, vs):
        self.dentro.append((str(c), [str(x) for x in vs]))
        return self

    def gte(self, *a, **k):
        self.banco.gte.append(tuple(str(x) for x in a))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def update(self, carga, **k):
        self.op, self.carga = "update", carga
        return self

    def upsert(self, carga, **k):
        self.op, self.carga = "upsert", carga
        return self

    def insert(self, carga, **k):
        self.op, self.carga = "insert", carga
        return self

    def _casa(self, linha):
        for c, v in self.filtros:
            if str(linha.get(c)) != str(v):
                return False
        for c, vs in self.dentro:
            if str(linha.get(c)) not in vs:
                return False
        return True

    def execute(self):
        if self.nome in self.banco.cai:
            raise RuntimeError("FONTE_INDISPONIVEL: %s (duble)" % self.nome)
        linhas = self.banco.dados.setdefault(self.nome, [])
        self.banco.registro.append({"tabela": self.nome, "op": self.op,
                                    "colunas": self.colunas,
                                    "filtros": list(self.filtros),
                                    "in": list(self.dentro)})
        if self.op == "select":
            return types.SimpleNamespace(data=[dict(l) for l in linhas if self._casa(l)])
        if self.op in ("insert", "upsert"):
            cargas = self.carga if isinstance(self.carga, list) else [self.carga or {}]
            for c in cargas:
                linhas.append(dict(c))
            return types.SimpleNamespace(data=[dict(c) for c in cargas])
        if self.op == "update":
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self.carga or {})
            return types.SimpleNamespace(data=[dict(l) for l in tocadas])
        raise AssertionError(self.op)


class BancoLeve:
    def __init__(self, ledger=(), cai=(), eventos=None):
        self.dados = {"billing_sent_log": [dict(l) for l in (ledger or [])]}
        self.registro, self.rpcs, self.gte = [], [], []
        self.cai = set(cai)
        self.eventos = eventos if eventos is not None else []
        self._n = 0
        self.client = self

    def table(self, nome):
        return _Tabela(self, nome)

    def rpc(self, nome, params=None):
        self.rpcs.append({"nome": nome, "params": dict(params or {})})
        self.eventos.append(("reserva", str(nome)))
        if nome in self.cai:
            raise RuntimeError("FONTE_INDISPONIVEL: rpc %s (duble)" % nome)
        self._n += 1
        dados = ([{"id": "bsl-%d" % self._n, "ganhou": True, "status": "reservado"}]
                 if nome == "billing_reservar_obrigacao" else [])
        return types.SimpleNamespace(execute=lambda: types.SimpleNamespace(data=dados))

    def ledger(self):
        return list(self.dados.get("billing_sent_log") or [])


def dias_atras(n):
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def ddmm(n):
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%d/%m")


def linha_do_ledger(chave, quando_dias, status="entregue_equipe", company_id=None,
                    send_mode="real", recibo=None):
    """Uma cobranca que JA saiu, no ledger. `sent_at` nulo = o caso do `incerto`."""
    quando = dias_atras(quando_dias)
    return {"id": "ant-%s" % (recibo or chave), "company_id": company_id or CO_ALFA,
            "send_mode": send_mode, "status": status, "segurado_chave": chave,
            "portal_key": "portal_de_ontem", "recibo": recibo or ("ANTIGO-" + chave),
            "sent_at": None if status == "incerto" else quando,
            "updated_at": quando, "text_ok": True, "doc_ok": True,
            "modalidade": "equipe", "encaminhado_ao_cliente_em": None}


def armar_a_porta(eventos=None):
    """Troca `send_to_client_guarded` por um coletor. ⛔ Nada sai."""
    from app.services import platform_outbound as PO

    chamadas = []
    eventos = eventos if eventos is not None else []

    async def _porta(company_id, destino, texto, **k):
        eventos.append(("porta", str(k.get("kind") or "")))
        chamadas.append({"company_id": str(company_id), "destino": str(destino),
                         "texto": str(texto), "kind": k.get("kind"),
                         "documento": k.get("documento"),
                         "ledger_ref": k.get("ledger_ref")})
        tem_doc = bool(k.get("documento"))
        return {"ok": True, "doc_ok": (True if tem_doc else None),
                "status": ("entregue_equipe" if tem_doc else "aceito_pelo_canal"),
                "integration_id": "int-alfa"}

    PO.send_to_client_guarded = _porta
    return chamadas


def rodar_entrega(fila, ledger=(), *, modo="equipe", dias=None, cai=()):
    """Roda o MOTOR real (`_entregar_cobranca_real`) sobre um ledger de mentira."""
    from app.services import billing_collection as BC

    eventos = []
    banco = BancoLeve(ledger, cai=cai, eventos=eventos)
    over = {"dias_entre_cobrancas_do_mesmo_segurado": dias} if dias is not None else {}
    c = cfg(modo, **over)
    BC._find_whatsapp_integration = lambda client, company_id: INTEGRACAO

    incidentes = []

    async def _inc(company_id, titulo, detalhe=""):
        incidentes.append(str(titulo))

    BC._incidente = _inc
    chamadas = armar_a_porta(eventos)
    blockers = []
    boletos = [{"recibo": i.get("recibo"), "ok": True,
                "storage_path": "prova/%s.pdf" % i.get("recibo")} for i in fila]
    entregas = asyncio.run(BC._entregar_cobranca_real(
        banco, {"id": "rot-alfa", "company_id": CO_ALFA}, list(fila), boletos, c, blockers))
    return {"chamadas": chamadas, "entregas": entregas, "blockers": blockers,
            "banco": banco, "incidentes": incidentes, "eventos": eventos}


# ==========================================================================
# G6 -- a dedup vale SEMPRE; a flag passa a DESLIGAR, e so no modo `test`
# ==========================================================================

def gate_G6():
    print("\n[G6] a dedup e o padrao; `BILLING_DEDUP_TEST_DISABLED` desliga -- e so `test`")
    from app.services import billing_collection as BC

    check("a flag se chama `BILLING_DEDUP_TEST_DISABLED` (ela DESLIGA)",
          BC.FLAG_DEDUP_TESTE_DESLIGADA == "BILLING_DEDUP_TEST_DISABLED",
          getattr(BC, "FLAG_DEDUP_TESTE_DESLIGADA", "nao existe"))
    check("`test` SEM a flag -> DEDUPLICA (o padrao invertido em 13/09)",
          BC.dedup_de_envio_ativa("test", env={}) is True)
    check("`test` com a flag ligada -> nao deduplica (o dia de demonstracao)",
          BC.dedup_de_envio_ativa("test", env={"BILLING_DEDUP_TEST_DISABLED": "1"}) is False)
    for modo in ("equipe", "cliente", "live", "approval", "none"):
        check("⛔ a flag NAO toca `%s`" % modo,
              BC.dedup_de_envio_ativa(modo, env={"BILLING_DEDUP_TEST_DISABLED": "1"}) is True)
    check("e `test` com a flag em `false` continua deduplicando (nao e `bool('false')`)",
          BC.dedup_de_envio_ativa("test", env={"BILLING_DEDUP_TEST_DISABLED": "false"}) is True)

    # 🔴 A REGRA DO COMANDO (protocolo §0.4): o valor ANTIGO morreu no backend/.
    sobreviventes = []
    for raiz, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", ".venv")]
        for nome in arquivos:
            if not nome.endswith((".py", ".md", ".example", ".env")):
                continue
            caminho = os.path.join(raiz, nome)
            try:
                if VALOR_ANTIGO_DA_FLAG in _ler(caminho):
                    sobreviventes.append(os.path.relpath(caminho, RAIZ))
            except Exception:  # noqa: BLE001
                pass
    check("`%s` nao sobrevive em backend/ (sobrevivente = defeito)" % VALOR_ANTIGO_DA_FLAG,
          not sobreviventes, sobreviventes)

    # -- O MOTOR: `_send_test_messages` de verdade, com o recibo JA no ledger --
    duble, _ = armar_canal()
    capturar_registros()
    c_teste = cfg("test")
    item = item_do_acervo(1)
    BC._find_whatsapp_integration = lambda client, company_id: INTEGRACAO
    BC._signed_boleto_url = lambda client, path: ""
    BC._record_sent = lambda *a, **k: True
    _already_original = BC._already_sent_recibos
    BC._already_sent_recibos = lambda client, company_id, send_mode: {str(item.get("recibo"))}

    async def _governador(company_id, orcamento_s, *, para_numero_de_teste=False):
        return True, "", 0.0

    async def _reg(*a, **k):
        return None

    BC._esperar_o_governador = _governador
    BC._registrar_no_governador = _reg
    rotina = {"id": "rot-alfa", "company_id": CO_ALFA, "config": c_teste,
              "delivery": {"number": TEL_TESTE}}

    antes = os.environ.pop("BILLING_DEDUP_TEST_DISABLED", None)
    try:
        duble.textos.clear()
        blockers = []
        enviados = asyncio.run(BC._send_test_messages(BancoLeve(), rotina, [item], [], c_teste, blockers))
        check("MOTOR: em `test`, o recibo que ja saiu NAO sai de novo (0 envios)",
              enviados == [] and not duble.textos, (enviados, duble.textos))
        check("  ... e o relatorio diz que pulou", any("anti-duplicacao" in b for b in blockers), blockers)
        # CONTROLE: com a flag, o MESMO recibo sai -- e e o que prova que a
        # assercao acima mediu a dedup, e nao um motor quebrado.
        os.environ["BILLING_DEDUP_TEST_DISABLED"] = "1"
        duble.textos.clear()
        blockers2 = []
        enviados2 = asyncio.run(BC._send_test_messages(BancoLeve(), rotina, [item], [], c_teste, blockers2))
        check("CONTROLE: com a flag ligada, o mesmo recibo sai (1 envio)",
              len(enviados2) == 1 and len(duble.textos) == 1, (enviados2, duble.textos))
    finally:
        os.environ.pop("BILLING_DEDUP_TEST_DISABLED", None)
        if antes is not None:
            os.environ["BILLING_DEDUP_TEST_DISABLED"] = antes
        BC._already_sent_recibos = _already_original


# ==========================================================================
# G7 -- 1 mensagem por segurado, N boletos; nunca dois tenants, nunca dois portais
# ==========================================================================

def gate_G7():
    print("\n[G7] `agrupar_por_segurado` sobre o ACERVO de 10-11/09: 4 parcelas = 1 mensagem")
    from app.services import billing_collection as BC

    itens = [dict(i) for i in ACERVO["itens"]]
    grupos = BC.agrupar_por_segurado(itens)
    check("os 7 itens do acervo viram 4 grupos (4 segurados)", len(grupos) == 4,
          [(g.get("segurado_chave"), len(g.get("parcelas") or [])) for g in grupos])
    tamanhos = sorted(len(g["parcelas"]) for g in grupos)
    check("um grupo tem as 4 parcelas do MESMO CNPJ; os outros tres tem 1",
          tamanhos == [1, 1, 1, 4], tamanhos)
    grande = [g for g in grupos if len(g["parcelas"]) == 4]
    check("o grupo de 4 e identificado por DOCUMENTO",
          len(grande) == 1 and str(grande[0]["segurado_chave"]).startswith("doc:"),
          [g["segurado_chave"] for g in grande])
    check("  ... e as 4 parcelas sao de UMA seguradora so",
          len({str(p.get("portal")) for p in grande[0]["parcelas"]}) == 1)
    check("o segurado SEM documento agrupa por NOME (fallback)",
          any(str(g["segurado_chave"]).startswith("nome:") for g in grupos),
          [g["segurado_chave"] for g in grupos])
    check("dois segurados distintos NUNCA se fundem",
          len({g["segurado_chave"] for g in grupos}) == 4)
    check("a ordem entre grupos e a da divida mais VELHA de cada um",
          [str(g["parcelas"][0].get("vencimento")) for g in grupos]
          == sorted(str(g["parcelas"][0].get("vencimento")) for g in grupos),
          [str(g["parcelas"][0].get("vencimento")) for g in grupos])

    # 🔴 as DUAS chaves, e a diferenca entre elas e o produto
    it = dict(ACERVO["itens"][1])
    check("`segurado_chave` NAO leva o portal (a janela vale entre seguradoras)",
          str(it["portal"]) not in BC.segurado_chave(it), BC.segurado_chave(it))
    check("`chave_do_grupo` LEVA o portal (a mensagem nomeia UMA seguradora)",
          str(it["portal"]) in BC.chave_do_grupo(it), BC.chave_do_grupo(it))
    dois_portais = BC.agrupar_por_segurado([dict(it, portal="hdi_corretor", recibo="X-1"),
                                            dict(it, portal="yelum_corretor", recibo="X-2")])
    check("o MESMO segurado em duas seguradoras -> DOIS grupos (nunca uma mensagem)",
          len(dois_portais) == 2, [g["chave_do_grupo"] for g in dois_portais])
    check("  ... e a `segurado_chave` dos dois e a MESMA",
          dois_portais[0]["segurado_chave"] == dois_portais[1]["segurado_chave"],
          [g["segurado_chave"] for g in dois_portais])
    mistos = BC.agrupar_por_segurado([dict(it, company_id=CO_ALFA, recibo="T-1"),
                                      dict(it, company_id=CO_BETA, recibo="T-2")])
    check("🔴 dois `company_id` na entrada NUNCA produzem grupo misto (CLAUDE.md §7)",
          len(mistos) == 2 and all(len(g["parcelas"]) == 1 for g in mistos),
          [(g["chave_do_grupo"], len(g["parcelas"])) for g in mistos])
    sem_nada = BC.agrupar_por_segurado([{"recibo": "S-1"}, {"recibo": "S-2"}])
    check("sem documento E sem nome, a identidade e o recibo (nunca funde dois)",
          len(sem_nada) == 2 and all(str(g["segurado_chave"]).startswith("recibo:")
                                     for g in sem_nada),
          [g["segurado_chave"] for g in sem_nada])

    # -- O MOTOR: o grupo de 4 sai como 1 nota + 1 texto + 4 PDFs --------------
    fila = [dict(i) for i in ACERVO["itens"] if str(i.get("recibo")).startswith("B-")]
    r = rodar_entrega(fila)
    chamadas = r["chamadas"]
    com_texto = [c for c in chamadas if str(c["texto"]).strip()]
    com_doc = [c for c in chamadas if c["documento"]]
    notas = [c for c in chamadas if c["kind"] == "billing_equipe_nota"]
    check("MOTOR: as 4 parcelas do mesmo CNPJ -> UM texto ao cliente",
          len([c for c in com_texto if c["kind"] == "billing_equipe"]) == 1,
          [(c["kind"], len(c["texto"])) for c in chamadas])
    check("MOTOR: UMA nota interna para a equipe (nao quatro)", len(notas) == 1, len(notas))
    check("MOTOR: QUATRO documentos, um por parcela", len(com_doc) == 4,
          [str((c["documento"] or {}).get("filename")) for c in com_doc])
    check("MOTOR: cada PDF viaja com o `ledger_ref` da SUA parcela",
          len({str((c["ledger_ref"] or {}).get("id")) for c in com_doc}) == 4,
          [str((c["ledger_ref"] or {}).get("id")) for c in com_doc])
    reservas = [x for x in r["banco"].rpcs if x["nome"] == "billing_reservar_obrigacao"]
    check("MOTOR: QUATRO reservas -- a reserva continua POR PARCELA",
          len(reservas) == 4, len(reservas))
    check("  ... com os 4 recibos, e a MESMA `segurado_chave` nos quatro",
          len({p["params"].get("p_recibo") for p in reservas}) == 4
          and len({p["params"].get("p_segurado_chave") for p in reservas}) == 1,
          [(p["params"].get("p_recibo"), p["params"].get("p_segurado_chave")) for p in reservas])
    check("  ... e ela e a chave por DOCUMENTO, que e o que a janela le",
          str(reservas[0]["params"].get("p_segurado_chave") or "").startswith("doc:"),
          reservas[0]["params"].get("p_segurado_chave"))
    ev = r["eventos"]
    primeira_porta = next((i for i, e in enumerate(ev) if e[0] == "porta"), -1)
    ultima_reserva = max([i for i, e in enumerate(ev) if e[0] == "reserva"] or [99])
    check("🔴 MOTOR: as 4 reservas vem ANTES do primeiro efeito do grupo",
          primeira_porta > ultima_reserva, ev)
    check("MOTOR: as 4 parcelas aparecem no relatorio (uma entrega por parcela)",
          len(r["entregas"]) == 4, r["entregas"])

    # A COPY do plural, sobre o texto que o motor montou
    texto = [c for c in com_texto if c["kind"] == "billing_equipe"][0]["texto"]
    c_equipe = cfg("equipe")
    for pedaco in ("as parcelas", "Seguem os boletos abaixo.", "estão pendentes",
                   "gerou novos boletos"):
        check("plural: o texto diz %r" % pedaco, pedaco in texto, texto[:200])
    check("plural: as 4 apolices distintas viram `Apólices:`",
          "Apólices:" in texto and "APOL-B1" in texto and "APOL-B4" in texto, texto[-120:])
    check("plural: a lista de parcelas usa virgula e `e` antes da ultima",
          BC.lista_de_parcelas(["2/6", "3/6", "4/6"]) == "2/6, 3/6 e 4/6",
          BC.lista_de_parcelas(["2/6", "3/6", "4/6"]))
    # 🔴 N=1 continua BYTE A BYTE o template de hoje
    um = dict(ACERVO["itens"][0])
    grupo_de_um = BC.agrupar_por_segurado([um])[0]
    check("N=1 usa o template de hoje BYTE A BYTE",
          BC.mensagem_do_grupo(grupo_de_um, c_equipe)
          == BC.build_customer_message(um, c_equipe["message_template"], c_equipe))
    check("CONTROLE: e o do grupo de 4 e DIFERENTE do singular da 1a parcela",
          BC.mensagem_do_grupo(grande[0], c_equipe)
          != BC.build_customer_message(grande[0]["parcelas"][0],
                                       c_equipe["message_template"], c_equipe))
    # template PERSONALIZADO pela corretora: singular, com a LISTA no lugar da parcela
    c_pers = cfg("equipe", message_template="Oi {primeiro_nome}, parcela {numero_parcela}.")
    pers = BC.mensagem_do_grupo(grande[0], c_pers)
    check("template personalizado: nao inventamos plural -- a LISTA entra em `{numero_parcela}`",
          pers.startswith("Oi ") and "3/12" in pers, pers)


# ==========================================================================
# G8 -- uma cobranca por segurado a cada N dias, por `segurado_chave`
# ==========================================================================

def gate_G8():
    print("\n[G8] a janela de N dias: retem com motivo, DATA e a ORIGEM da identidade")
    from app.services import billing_collection as BC

    check("o default sao 7 dias (D-PILOTO-18)", BC.DIAS_ENTRE_COBRANCAS_PADRAO == 7,
          getattr(BC, "DIAS_ENTRE_COBRANCAS_PADRAO", "nao existe"))
    c = cfg("equipe", dias_entre_cobrancas_do_mesmo_segurado=99)
    check("a tela manda o numero e o motor CLAMPA em 1..30",
          c.get("dias_entre_cobrancas_do_mesmo_segurado") == 30,
          c.get("dias_entre_cobrancas_do_mesmo_segurado"))
    check("  ... e 0 sobe para 1",
          cfg("equipe", dias_entre_cobrancas_do_mesmo_segurado=0)
          .get("dias_entre_cobrancas_do_mesmo_segurado") == 1)
    check("  ... e sem a chave vale o padrao",
          cfg("equipe").get("dias_entre_cobrancas_do_mesmo_segurado") == 7)

    # ---- O LEITOR DO LEDGER, com DUAS corretoras na mesa --------------------
    doc_b = "doc:" + ACERVO["itens"][1]["cpf_cnpj"]
    linhas = [
        linha_do_ledger(doc_b, 3),
        linha_do_ledger("doc:falhou", 1, status="falhou"),
        linha_do_ledger("doc:reservado", 1, status="reservado"),
        linha_do_ledger("doc:adiado", 1, status="adiado"),
        linha_do_ledger("doc:suprimido", 1, status="suprimido"),
        linha_do_ledger("doc:incerto", 2, status="incerto"),
        linha_do_ledger("doc:parcial", 2, status="parcial"),
        linha_do_ledger("doc:aceito", 2, status="aceito_pelo_canal"),
        linha_do_ledger("doc:velho", 9),
        linha_do_ledger("doc:00000000000191", 1, company_id=CO_BETA),
        linha_do_ledger("doc:sotest", 1, send_mode="test"),
    ]
    recentes = BC._segurados_cobrados_recentemente(BancoLeve(linhas), CO_ALFA, 7)
    check("o segurado cobrado ha 3 dias esta na janela", doc_b in recentes, sorted(recentes))
    for estado in ("aceito", "parcial", "incerto"):
        check("`%s` CONTA como cobrado (alguem recebeu, ou pode ter recebido)" % estado,
              ("doc:" + estado) in recentes, sorted(recentes))
    for estado in ("falhou", "reservado", "adiado", "suprimido"):
        check("`%s` NAO conta (ninguem recebeu nada)" % estado,
              ("doc:" + estado) not in recentes, sorted(recentes))
    check("fora da janela (9 dias) nao aparece", "doc:velho" not in recentes)
    check("🔴 o ledger da OUTRA corretora NUNCA atravessa (CLAUDE.md §7)",
          "doc:00000000000191" not in recentes, sorted(recentes))
    check("o modo `test` nao entra na janela do modo real", "doc:sotest" not in recentes)
    check("a data que volta e a do envio (para a frase dizer QUANDO)",
          str(recentes.get(doc_b, ""))[:10] == dias_atras(3)[:10], recentes.get(doc_b))
    levantou = False
    try:
        BC._segurados_cobrados_recentemente(BancoLeve(linhas, cai={"billing_sent_log"}), CO_ALFA, 7)
    except Exception:  # noqa: BLE001
        levantou = True
    check("🔴 falha de leitura LEVANTA -- nunca devolve vazio (R04)", levantou)

    # ---- O MOTOR: o grupo retido, com a frase que a pessoa le ---------------
    b1 = [dict(ACERVO["itens"][1])]
    r = rodar_entrega(b1, [linha_do_ledger(doc_b, 3)])
    check("MOTOR: cobrado ha 3 dias -> ZERO envios", r["chamadas"] == [],
          [(c["kind"], c["destino"]) for c in r["chamadas"]])
    motivos = " | ".join(r["blockers"])
    check("  ... o relatorio diz que ja foi cobrado, com a DATA",
          "cobrado em " + ddmm(3) in motivos, motivos)
    check("  ... diz a REGRA (1 cobranca a cada 7 dias)",
          "cada 7 dias" in motivos, motivos)
    check("  ... e diz que a identidade veio do CPF/CNPJ",
          "CPF/CNPJ" in motivos, motivos)
    check("  ... e diz QUANDO volta", "volta em " + ddmm(-4) in motivos, motivos)
    check("  ... e a parcela NAO desaparece: entra nas entregas como `retido`",
          [e for e in r["entregas"] if str(e.get("status")) == "retido"], r["entregas"])
    check("  ... e nada foi reservado (nao se reserva o que nao vai sair)",
          not [x for x in r["banco"].rpcs if x["nome"] == "billing_reservar_obrigacao"],
          r["banco"].rpcs)

    # CONTROLE: 8 dias -> COBRA. E o que da direito a conclusao acima.
    r8 = rodar_entrega(b1, [linha_do_ledger(doc_b, 8)])
    check("CONTROLE: cobrado ha 8 dias -> COBRA (a janela nao e uma trava eterna)",
          len([c for c in r8["chamadas"] if c["documento"]]) == 1,
          [(c["kind"], bool(c["documento"])) for c in r8["chamadas"]])

    # 🔴 A MESMA PESSOA NA OUTRA SEGURADORA -- a janela ignora o portal
    outra = [dict(ACERVO["itens"][1], portal="yelum_corretor", recibo="Y-0001")]
    r_outra = rodar_entrega(outra, [linha_do_ledger(doc_b, 2)])
    check("🔴 a mesma pessoa na OUTRA seguradora TAMBEM e retida",
          r_outra["chamadas"] == [], [(c["kind"]) for c in r_outra["chamadas"]])

    # CONTROLE: o segurado SEM documento tambem e retido -- e a frase muda
    d = [dict(ACERVO["itens"][6])]
    chave_d = BC.segurado_chave(d[0])
    r_d = rodar_entrega(d, [linha_do_ledger(chave_d, 1)])
    check("CONTROLE: o segurado SEM documento tambem e retido (pelo NOME)",
          r_d["chamadas"] == [], [(c["kind"]) for c in r_d["chamadas"]])
    motivo_d = " | ".join(r_d["blockers"])
    check("  ... e a frase diz que a identidade veio do NOME",
          "NOME" in motivo_d and "documento" in motivo_d, motivo_d)
    check("  ... e ensina a discordar pela tela",
          "libere pela tela" in motivo_d, motivo_d)
    # 🔴 O PAR DE TENANT: a MESMA chave, no ledger da OUTRA corretora, nao retem
    r_beta = rodar_entrega(d, [linha_do_ledger(chave_d, 1, company_id=CO_BETA)])
    check("🔴 PAR: a mesma chave no ledger da OUTRA corretora NAO retem (cobra)",
          len([c for c in r_beta["chamadas"] if c["documento"]]) == 1,
          [(c["kind"], bool(c["documento"])) for c in r_beta["chamadas"]])

    # ---- E O MODO TESTE TAMBEM: o ensaio precisa ensaiar o que vai acontecer --
    duble, _ = armar_canal()
    capturar_registros()
    c_teste = cfg("test")
    BC._find_whatsapp_integration = lambda client, company_id: INTEGRACAO
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
    duble.textos.clear()
    blk = []
    banco_teste = BancoLeve([linha_do_ledger(doc_b, 2, send_mode="test")])
    enviados = asyncio.run(BC._send_test_messages(banco_teste, rotina, b1, [], c_teste, blk))
    check("modo TESTE: a janela tambem vale la (o ensaio ensaia o que vai acontecer)",
          enviados == [] and not duble.textos, (enviados, duble.textos))
    check("  ... e o motivo aparece no relatorio do teste",
          any("foi cobrado em" in b for b in blk), blk)
    # CONTROLE: a linha do ledger do modo REAL nao segura o modo TESTE (nem o
    # contrario) -- sao dois mundos, e a janela le o mundo em que esta.
    duble.textos.clear()
    banco_real = BancoLeve([linha_do_ledger(doc_b, 2, send_mode="real")])
    enviados2 = asyncio.run(BC._send_test_messages(banco_real, rotina, b1, [], c_teste, []))
    check("CONTROLE: a cobranca REAL de 2 dias atras nao segura a SIMULACAO",
          len(enviados2) == 1, enviados2)


# ==========================================================================
# G10 -- o canario de login roda ANTES da varredura, e o breaker aberto barra
# ==========================================================================

def gate_G10():
    print("\n[G10] `login_check` de cada portal ANTES de qualquer `cobranca_sweep`")
    from app.services import billing_collection as BC

    check("as duas jornadas tem nome, e sao as do worker",
          (BC.JORNADA_DA_VARREDURA, BC.JORNADA_DO_CANARIO) == ("cobranca_sweep", "login_check"),
          (getattr(BC, "JORNADA_DA_VARREDURA", "?"), getattr(BC, "JORNADA_DO_CANARIO", "?")))
    check("o breaker do `fora_do_ar` tem prazo com default e clamp (1..72h)",
          BC.portal_breaker_horas({}) == 6
          and BC.portal_breaker_horas({"PORTAL_BREAKER_HORAS": "999"}) == 72
          and BC.portal_breaker_horas({"PORTAL_BREAKER_HORAS": "0"}) == 1,
          BC.portal_breaker_horas({}))
    check("o teto de espera do canario tem default 120s e clamp (30..600)",
          BC.login_check_teto_s({}) == 120
          and BC.login_check_teto_s({"BILLING_LOGIN_CHECK_TETO_S": "5"}) == 30
          and BC.login_check_teto_s({"BILLING_LOGIN_CHECK_TETO_S": "9000"}) == 600)

    from datetime import datetime, timedelta, timezone

    def ha(horas):
        return (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()

    # allianz: ok · hdi: senha recusada · mapfre: fora do ar HA POUCO ·
    # tokiomarine: fora do ar HA MUITO (o breaker reabre) · yelum: unknown e o
    # login falha · zurich: sem credencial nenhuma
    contas = {
        "allianz_corretor": {"id": "ac-1", "health": "ok", "updated_at": ha(1)},
        "hdi_corretor": {"id": "ac-2", "health": "credencial_recusada", "updated_at": ha(30)},
        "mapfre_corretor": {"id": "ac-3", "health": "fora_do_ar", "updated_at": ha(2)},
        "tokiomarine_corretor": {"id": "ac-4", "health": "fora_do_ar", "updated_at": ha(20)},
        "yelum_corretor": {"id": "ac-5", "health": "unknown", "updated_at": ha(5)},
        "zurich_corretor": None,
    }
    enfileirados = []

    def _conta(client, company_id, portal_key):
        return dict(contas[portal_key]) if contas.get(portal_key) else None

    def _enfileirar(client, routine, portal_key, account, cfg_, **k):
        jornada = str(k.get("journey") or BC.JORNADA_DA_VARREDURA)
        enfileirados.append((portal_key, jornada))
        return "job-%s-%s" % (jornada, portal_key)

    async def _poll(client, job_id, timeout_seconds):
        portal = str(job_id).split("-", 2)[-1]
        if BC.JORNADA_DO_CANARIO in str(job_id):
            if portal == "yelum_corretor":
                return {"id": job_id, "portal_key": portal, "status": "failed", "error": None,
                        "evidence": {"message": "a YELUM recusou a credencial (autenticacao invalida)"}}
            return {"id": job_id, "portal_key": portal, "status": "done", "evidence": {}}
        return {"id": job_id, "portal_key": portal, "status": "done", "evidence": {}}

    async def _avisar(client, company_id, texto, rotulo, *, suprimir=False):
        return True

    BC._portal_account = _conta
    BC._enqueue_job = _enfileirar
    BC._poll_job = _poll
    BC.avisar_suporte_humano = _avisar
    BC._company_name = lambda client, company_id: "Corretora Alfa"
    BC._gerar_artefato_da_cobranca = lambda *a, **k: None

    rotina = {"id": "rot-alfa", "company_id": CO_ALFA,
              "config": {"kind": "billing_collection", "send_mode": "none",
                         "portal_keys": list(contas.keys())}}
    try:
        relatorio = asyncio.run(BC.execute_billing_collection_routine(BancoLeve(), rotina))
    except Exception as e:  # noqa: BLE001
        import traceback
        check("[G10] a rotina roda", False, "%s: %s\n%s" % (type(e).__name__, e,
                                                            traceback.format_exc()[-600:]))
        return

    jornadas = [j for _, j in enfileirados]
    canarios = [p for p, j in enfileirados if j == BC.JORNADA_DO_CANARIO]
    varreduras = [p for p, j in enfileirados if j == BC.JORNADA_DA_VARREDURA]
    check("🔴 TODO `login_check` sai ANTES de qualquer `cobranca_sweep`",
          jornadas and jornadas.index(BC.JORNADA_DA_VARREDURA) > max(
              [i for i, j in enumerate(jornadas) if j == BC.JORNADA_DO_CANARIO] or [-1]),
          enfileirados)
    check("o canario visita os portais com credencial e breaker fechado",
          sorted(canarios) == ["allianz_corretor", "tokiomarine_corretor", "yelum_corretor"],
          sorted(canarios))
    check("⛔ `credencial_recusada` NAO gera job nenhum (nem canario, nem varredura)",
          "hdi_corretor" not in [p for p, _ in enfileirados], enfileirados)
    check("⛔ `fora_do_ar` DENTRO do prazo do breaker nao gera job nenhum",
          "mapfre_corretor" not in [p for p, _ in enfileirados], enfileirados)
    check("CONTROLE: `fora_do_ar` VELHO (20h > 6h) volta a ser tentado",
          "tokiomarine_corretor" in canarios, canarios)
    check("CONTROLE: `unknown` e meio-aberto -- tenta UMA vez, pelo proprio canario",
          "yelum_corretor" in canarios, canarios)
    check("🔴 o canario que NAO terminou `done` nao abre varredura",
          "yelum_corretor" not in varreduras, varreduras)
    check("so varre quem passou pelo canario",
          sorted(varreduras) == ["allianz_corretor", "tokiomarine_corretor"], sorted(varreduras))
    check("a senha recusada vira linha do relatorio, com o que FAZER",
          "senha recusada pelo portal" in relatorio
          and "Conectores" in relatorio, relatorio[-1200:])
    check("o portal fora do ar diz desde quando e quando se tenta de novo",
          "fora do ar desde" in relatorio and "tento de novo" in relatorio, relatorio[-1200:])
    check("o motivo do canario reprovado vem de `_blocker_do_job` (o texto REAL do portal)",
          "recusou a credencial" in relatorio, relatorio[-1200:])
    check("o portal sem credencial continua com a linha de sempre",
          "sem credencial conectada" in relatorio, relatorio[-1200:])


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
    # 🔴 M6 inverte o DEFAULT de volta: em `test`, so deduplica com a flag ligada.
    ("M6", "app/services/billing_collection.py",
     "    return not _truthy(fonte.get(FLAG_DEDUP_TESTE_DESLIGADA))\n",
     "    return _truthy(fonte.get(FLAG_DEDUP_TESTE_DESLIGADA))\n", "G6"),
    # 🔴 M7 poe o portal na chave do SEGURADO -- e a janela deixa de valer entre
    #    seguradoras, que e a pergunta que as DUAS chaves existem para separar.
    ("M7", "app/services/billing_collection.py",
     '        return f"doc:{doc}"\n',
     '        return "doc:%s|%s" % (doc, item.get("portal") or "")\n', "G7"),
    # 🔴 M8 ignora a janela de N dias: nenhum grupo e retido.
    ("M8", "app/services/billing_collection.py",
     '        cobrado_em = recentes.get(chave_do_segurado)\n',
     "        cobrado_em = None\n", "G8"),
    # 🔴 M10 abre a varredura mesmo com o breaker aberto ou o canario reprovado.
    ("M10", "app/services/billing_collection.py",
     "            if account is None:\n                continue\n",
     '            if account is None:\n                account = {"id": None}\n', "G10"),
]

GATES = {"G1": gate_G1, "G2": gate_G2, "G3": gate_G3, "G4": gate_G4, "G5": gate_G5,
         "G6": gate_G6, "G7": gate_G7, "G8": gate_G8, "G10": gate_G10}


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
