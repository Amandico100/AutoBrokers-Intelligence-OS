# -*- coding: utf-8 -*-
"""SPEC-EXTRA-001.6 -- A COBRANCA PROVA QUE FUNCIONA. G1..G8, G10, G12 e G13.

O QUE ELE GUARDA (proposta §11; BLOCO 0 medido em 13/09/2026, corrigido em 14/09
pela lente do dado -- ver G7)

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
  G7  🔴 A FORMA REAL DO ACERVO. 📊 14/09: as "4 parcelas do mesmo CNPJ" da Tokio
      sao 4 LANCAMENTOS do MESMO recibo, mesma apolice, mesma parcela "1", mesmo
      vencimento, e UM boleto cujo valor e a soma dos quatro. `consolidar_por_recibo`
      funde: 1 grupo, 1 parcela, 1 PDF, 1 RESERVA, ZERO bloqueios (antes eram 3
      bloqueios FALSOS por execucao, "reservadas e sem desfecho"), e a nota da
      atendente diz "4 lancamentos num boleto". O caminho "N boletos" continua
      provado por 💭 Segurado E (2 recibos distintos, 2 PDFs, 2 reservas) -- e e
      ele que prova A-5: dois recibos numerados "1" viram "1 (apólice …AAAA) e
      1 (apólice …BBBB)". Mais: P6 (documento so vale com 11 ou 14 digitos nao
      todos iguais), P7 (o `company_id` da EXECUCAO entra na chave quando o item
      nao o carrega -- 📊 o worker nunca o carrega) e A-7 (ramo numerico nao e
      nome de bem: nada de "do seguro do 180" nem "do seguro do seguro").
      Continua guardando: dois segurados nunca se fundem; sem documento o fallback
      e o NOME; dois portais nunca cabem na mesma mensagem; dois `company_id`
      nunca fazem grupo misto; `segurado_chave` NAO leva portal, `chave_do_grupo` leva.
  G8  a janela de N dias por `segurado_chave` (SEM o portal): retem com motivo,
      DATA e a ORIGEM da identidade; 8 dias cobra; sem documento tambem retem; a
      mesma pessoa na OUTRA seguradora tambem; e o ledger da outra corretora
      NUNCA atravessa.
  G10 a rotina enfileira `login_check` de CADA portal antes de qualquer
      `cobranca_sweep`; breaker aberto (`credencial_recusada` / `fora_do_ar`
      dentro do prazo) nao gera job nenhum; canario com VEREDITO RUIM (`failed`)
      nao abre varredura -- mas 🔴 canario que NAO TERMINOU (`timeout`) VARRE
      ASSIM MESMO, com a linha "varri assim mesmo" no relatorio (📊 a fila real
      tem mediana de 144 s e maximo de 511 s num worker serial; com o teto antigo
      de 120 s, 5 de 6 portais eram descartados por AUSENCIA de veredito). O teto
      passa a 600 s (clamp 60..900). E 🔴 P8: um `login_check` que ja esta na fila
      e REUSADO -- duas execucoes no mesmo minuto = 1 login por portal.
  G12 o RELATORIO DA EXECUCAO sai sem CPF/CNPJ nem telefone inteiros -- so os 4
      ultimos digitos (`_mascarar_documento` / `_mascarar_telefone`, no
      `_format_report` REAL, sobre um item do acervo anonimizado). 📊 13/09:
      7 de 49 execucoes tem `CPF/CNPJ` em claro em `routine_runs.output_full`,
      6 delas com digitos. CONTROLE: a NOTA INTERNA a atendente CONTINUA com o
      WhatsApp legivel -- ela precisa discar, e um guarda que so dissesse "nao
      tem telefone em lugar nenhum" ficaria verde no dia em que a atendente
      perdesse o numero (CLAUDE.md §9.3).
  G13 `veredito_de_saude` (A-4): "sessao invalida" casa com a marca "invalid" das
      credenciais -- e uma sessao caida virava `credencial_recusada`, que so fecha
      por GESTO HUMANO. As marcas de SESSAO CAIDA passam a ser lidas ANTES, e
      "credenciais ausentes" vira `pede_humano` (nao ha senha para trocar).
      CONTROLES: as frases REAIS da Mapfre e da Allianz continuam recusa.

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
        `--mutar` roda as 18 mutacoes (M1..M13, com M3b/M7b..M7e/M10b/M10c) por
        COPIA, cada uma em SUBPROCESSO sobre
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

        # -- 🔴 P5: o DASHBOARD e contado ANTES da lista de recusa --------------
        #    "acesso negado" e "valide os dados" entraram em `_FAIL` no P0.3 e sao
        #    genericas o bastante para aparecer num TOAST sobre a tela JA LOGADA.
        #    `failed` com marca de credencial abre o breaker ate alguem salvar uma
        #    senha nova: a corretora pararia de ser varrida por um aviso de
        #    permissao.
        hits_real = sum(1 for s in mods["allianz"]._DASHBOARD_SIGNALS if s in n)
        check("a tela REAL de recusa tem hits=0 de dashboard (por isso continua `failed`)",
              hits_real == 0, hits_real)
        com_toast = ALLIANZ_DASHBOARD_SINTETICO + " Acesso negado. Por favor, valide os dados."
        r = mods["allianz"].interpret_login(com_toast)
        check("🔴 P5: dashboard sintetico + 'acesso negado' num toast -> `done` (nao `failed`)",
              r.status == "done", (r.status, getattr(r, "message", "")))
        r_real = mods["allianz"].interpret_login(textos["allianz_corretor-needs_human-20260911.txt"])
        check("CONTROLE: a tela REAL da Allianz (hits=0) CONTINUA `failed`",
              r_real.status == "failed", (r_real.status, getattr(r_real, "message", "")))
        r_1hit = mods["allianz"].interpret_login("Vendas. Acesso negado, valide os dados.")
        check("CONTROLE: UM sinal de dashboard nao basta -- 1 hit ainda e `failed`",
              r_1hit.status == "failed", (r_1hit.status, getattr(r_1hit, "message", "")))
        r_2fa = mods["allianz"].interpret_login(ALLIANZ_DASHBOARD_SINTETICO + " informe o codigo de verificacao")
        check("CONTROLE: o CAPTCHA/2FA continua vencendo o dashboard (`needs_human`)",
              r_2fa.status == "needs_human", (r_2fa.status, getattr(r_2fa, "message", "")))
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
        #: 🔴 A-2(e) -- o INDICE UNICO PARCIAL do banco, modelado:
        #:     billing_sent_log_obrigacao_uniq (company_id, portal_key, recibo)
        #:     WHERE send_mode = 'real'
        #: Sem isto o duble dizia "ganhou" a toda chamada, e o guarda nunca veria
        #: o que a producao via: a 2a reserva do MESMO recibo perde, e a funcao
        #: devolve o id da linha que ja existe com o status atual dela. Era esse
        #: ramo que produzia os 3 bloqueios falsos dos 4 lancamentos da Tokio.
        self.obrigacoes = {}
        self.client = self

    def table(self, nome):
        return _Tabela(self, nome)

    def rpc(self, nome, params=None):
        self.rpcs.append({"nome": nome, "params": dict(params or {})})
        self.eventos.append(("reserva", str(nome)))
        if nome in self.cai:
            raise RuntimeError("FONTE_INDISPONIVEL: rpc %s (duble)" % nome)
        dados = []
        if nome == "billing_reservar_obrigacao":
            p = dict(params or {})
            chave = (str(p.get("p_company_id")), str(p.get("p_portal_key")),
                     str(p.get("p_recibo")))
            ja = self.obrigacoes.get(chave)
            if ja is None:
                self._n += 1
                ja = {"id": "bsl-%d" % self._n, "status": "reservado"}
                self.obrigacoes[chave] = ja
                dados = [{"id": ja["id"], "ganhou": True, "status": ja["status"]}]
            else:
                # `ON CONFLICT ... DO NOTHING` + o SELECT que a funcao faz depois:
                # o MESMO id, o status ATUAL, e `ganhou` falso.
                dados = [{"id": ja["id"], "ganhou": False, "status": ja["status"]}]
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
# G7 -- A FORMA REAL DO ACERVO: 4 lancamentos = 1 boleto = 1 reserva = 1 PDF
#       (e o caminho "N boletos" continua provado, por 💭 Segurado E)
# ==========================================================================
#
# 🔴 14/09/2026 -- ESTE GUARDA PROVAVA UM CAMINHO QUE A PRODUCAO NAO TEM.
# O corpus dizia que Segurado B tinha 4 parcelas com 4 recibos. 📊 A lente do
# dado mediu `portal_jobs.evidence->'inadimplentes'` de 11/09 e achou outra
# coisa: 4 LANCAMENTOS do MESMO recibo, mesma apolice, mesma parcela "1", mesmo
# vencimento, e UM boleto cujo valor e a soma dos quatro. Com a forma real,
# `_boletos_by_recibo` devolve 1 chave, o laco reservava 1 e produzia
# 3 BLOQUEIOS FALSOS por execucao ("nao cobrada agora — reservadas e sem
# desfecho") -- e o plural dizia "as parcelas 1".
#
# ⚠️ CLAUDE.md §9.4: "o texto da tela vem do acervo, nao da imaginacao". Vale
# para a FORMA do dado tambem.

def gate_G7():
    print("\n[G7] a forma REAL: 4 lancamentos = 1 boleto = 1 reserva; 2 recibos = 2 PDFs")
    from app.services import billing_collection as BC

    itens = [dict(i) for i in ACERVO["itens"]]
    grupos = BC.agrupar_por_segurado(itens, CO_ALFA)
    check("os 7 itens do acervo viram 4 grupos (4 segurados)", len(grupos) == 4,
          [(g.get("segurado_chave"), len(g.get("parcelas") or [])) for g in grupos])
    tamanhos = sorted(len(g["parcelas"]) for g in grupos)
    check("🔴 depois de consolidar por recibo, TODO grupo tem UMA parcela "
          "(os 4 lancamentos de B sao UM boleto)", tamanhos == [1, 1, 1, 1], tamanhos)
    b = [g for g in grupos if str(g["parcelas"][0].get("recibo")) == "B-0001"]
    check("o grupo de B existe e e identificado por DOCUMENTO",
          len(b) == 1 and str(b[0]["segurado_chave"]).startswith("doc:"),
          [g["segurado_chave"] for g in grupos])
    b = b[0] if b else {"parcelas": [{}]}
    check("  ... e a parcela consolidada diz que sao 4 lancamentos",
          b["parcelas"][0].get("lancamentos") == 4, b["parcelas"][0].get("lancamentos"))
    check("  ... e o valor e a SOMA dos quatro (676.31+684.05+643.77+733.13)",
          b["parcelas"][0].get("valor") == 2737.26, b["parcelas"][0].get("valor"))
    check("  ... e o numero da parcela NAO muda (e o que a seguradora escreveu)",
          str(b["parcelas"][0].get("numero_parcela")) == "1",
          b["parcelas"][0].get("numero_parcela"))
    check("o segurado SEM documento agrupa por NOME (fallback)",
          any(str(g["segurado_chave"]).startswith("nome:") for g in grupos),
          [g["segurado_chave"] for g in grupos])
    check("dois segurados distintos NUNCA se fundem",
          len({g["segurado_chave"] for g in grupos}) == 4)
    check("a ordem entre grupos e a da divida mais VELHA de cada um",
          [str(g["parcelas"][0].get("vencimento")) for g in grupos]
          == sorted(str(g["parcelas"][0].get("vencimento")) for g in grupos),
          [str(g["parcelas"][0].get("vencimento")) for g in grupos])

    # -- `consolidar_por_recibo`, a funcao PURA, com os controles que dao
    #    direito a conclusao acima (CLAUDE.md §9.2) -----------------------------
    sinteticos = [dict(i) for i in ACERVO["sinteticos"]]
    check("CONTROLE: dois recibos DISTINTOS continuam duas parcelas",
          len(BC.consolidar_por_recibo(sinteticos)) == 2,
          [p.get("recibo") for p in BC.consolidar_por_recibo(sinteticos)])
    check("  ... e nenhuma delas ganha `lancamentos` (so quem consolidou ganha)",
          all("lancamentos" not in p for p in BC.consolidar_por_recibo(sinteticos)))
    check("CONTROLE: o MESMO recibo em portais DIFERENTES nao se funde",
          len(BC.consolidar_por_recibo([{"portal": "a", "recibo": "R"},
                                        {"portal": "b", "recibo": "R"}])) == 2)
    check("CONTROLE: linha SEM recibo nunca se funde com outra",
          len(BC.consolidar_por_recibo([{"portal": "p", "recibo": ""},
                                        {"portal": "p", "recibo": ""}])) == 2)
    misto = BC.consolidar_por_recibo([{"portal": "p", "recibo": "R", "valor": 10.0},
                                      {"portal": "p", "recibo": "R", "valor": "a combinar"}])
    check("valor nao-numerico NAO e somado -- fica o do primeiro (somar texto e inventar)",
          len(misto) == 1 and misto[0]["valor"] == 10.0, misto)

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

    # -- 🔴 P7: o `company_id` da EXECUCAO entra na chave quando o ITEM nao o tem
    #    📊 o worker devolve os inadimplentes SEM `company_id` em 100% dos jobs,
    #    entao ate aqui a clausula de tenant so existia no guarda.
    sem_tenant = dict(ACERVO["itens"][1])
    check("o item do acervo NAO carrega `company_id` (e a forma que o worker devolve)",
          "company_id" not in sem_tenant, sorted(sem_tenant))
    ka = BC.chave_do_grupo(sem_tenant, CO_ALFA)
    kb = BC.chave_do_grupo(sem_tenant, CO_BETA)
    check("🔴 P7: sem `company_id` no item, a chave usa o da EXECUCAO",
          ka != kb and ka.startswith(CO_ALFA) and kb.startswith(CO_BETA), (ka, kb))
    check("  ... e o `company_id` do ITEM vence o da execucao (o dado, nao a suposicao)",
          BC.chave_do_grupo(dict(sem_tenant, company_id=CO_BETA), CO_ALFA).startswith(CO_BETA),
          BC.chave_do_grupo(dict(sem_tenant, company_id=CO_BETA), CO_ALFA))
    check("CONTROLE: sem nenhum dos dois, a chave e `segurado_chave|portal` (forma de hoje)",
          BC.chave_do_grupo(sem_tenant).startswith("doc:"), BC.chave_do_grupo(sem_tenant))
    g_alfa = BC.agrupar_por_segurado([dict(sem_tenant)], CO_ALFA)[0]
    check("  ... e o GRUPO tambem carrega o `company_id` da execucao",
          g_alfa.get("company_id") == CO_ALFA, g_alfa.get("company_id"))

    # -- 🔴 P6: documento que nao pode SER documento cai no NOME ---------------
    check("P6: '000.000/0' (7 digitos) NAO vira identidade por documento",
          BC.segurado_chave({"cpf_cnpj": "000.000/0", "cliente_nome": "Fulano"}).startswith("nome:"),
          BC.segurado_chave({"cpf_cnpj": "000.000/0", "cliente_nome": "Fulano"}))
    check("P6: '00000000000' (11 digitos, TODOS iguais) NAO vira identidade",
          BC.segurado_chave({"cpf_cnpj": "00000000000", "cliente_nome": "Fulano"}).startswith("nome:"),
          BC.segurado_chave({"cpf_cnpj": "00000000000", "cliente_nome": "Fulano"}))
    check("  ... e dois segurados com o MESMO lixo no campo NAO viram um so",
          len(BC.agrupar_por_segurado([{"cpf_cnpj": "000.000/0", "cliente_nome": "Fulano",
                                        "recibo": "L-1", "portal": "p"},
                                       {"cpf_cnpj": "000.000/0", "cliente_nome": "Beltrano",
                                        "recibo": "L-2", "portal": "p"}])) == 2)
    check("CONTROLE: um CNPJ de 14 digitos de verdade CONTINUA virando `doc:`",
          BC.segurado_chave({"cpf_cnpj": "00000000000272"}) == "doc:00000000000272",
          BC.segurado_chave({"cpf_cnpj": "00000000000272"}))
    check("CONTROLE: e um CPF de 11 digitos tambem",
          BC.segurado_chave({"cpf_cnpj": "123.456.789-09"}) == "doc:12345678909",
          BC.segurado_chave({"cpf_cnpj": "123.456.789-09"}))

    # -- O MOTOR sobre a FORMA REAL: 1 texto + 1 nota + 1 PDF + 1 reserva ------
    fila = [dict(i) for i in ACERVO["itens"] if str(i.get("recibo")).startswith("B-")]
    check("o acervo traz os 4 lancamentos de B com o MESMO recibo",
          len(fila) == 4 and len({str(i["recibo"]) for i in fila}) == 1,
          [i["recibo"] for i in fila])
    r = rodar_entrega(fila)
    chamadas = r["chamadas"]
    com_texto = [c for c in chamadas if str(c["texto"]).strip()]
    com_doc = [c for c in chamadas if c["documento"]]
    notas = [c for c in chamadas if c["kind"] == "billing_equipe_nota"]
    check("MOTOR: os 4 lancamentos -> UM texto ao cliente",
          len([c for c in com_texto if c["kind"] == "billing_equipe"]) == 1,
          [(c["kind"], len(c["texto"])) for c in chamadas])
    check("MOTOR: UMA nota interna para a equipe", len(notas) == 1, len(notas))
    check("MOTOR: UM documento -- e um boleto so, porque o portal emitiu um so",
          len(com_doc) == 1, [str((c["documento"] or {}).get("filename")) for c in com_doc])
    reservas = [x for x in r["banco"].rpcs if x["nome"] == "billing_reservar_obrigacao"]
    check("MOTOR: UMA reserva (a reserva e por RECIBO, e o recibo e um so)",
          len(reservas) == 1, [p["params"].get("p_recibo") for p in reservas])
    check("🔴 MOTOR: ZERO bloqueios -- nenhum 'reservadas e sem desfecho' falso",
          r["blockers"] == [], r["blockers"])
    check("MOTOR: UMA entrega no relatorio (nao quatro)", len(r["entregas"]) == 1, r["entregas"])
    check("  ... e a `segurado_chave` da reserva e a chave por DOCUMENTO",
          str(reservas[0]["params"].get("p_segurado_chave") or "").startswith("doc:")
          if reservas else False,
          reservas[0]["params"].get("p_segurado_chave") if reservas else None)
    ev = r["eventos"]
    primeira_porta = next((i for i, e in enumerate(ev) if e[0] == "porta"), -1)
    ultima_reserva = max([i for i, e in enumerate(ev) if e[0] == "reserva"] or [99])
    check("🔴 MOTOR: a reserva vem ANTES do primeiro efeito do grupo",
          primeira_porta > ultima_reserva, ev)
    nota_txt = notas[0]["texto"] if notas else ""
    check("a NOTA da atendente diz que o boleto tem 4 lancamentos",
          "4 lançamentos num boleto" in nota_txt,
          [l for l in nota_txt.splitlines() if "Parcela" in l])
    check("  ... com o valor SOMADO, que e o que ela vai conferir no portal",
          "2.737,26" in nota_txt, [l for l in nota_txt.splitlines() if "Parcela" in l])

    c_equipe = cfg("equipe")
    texto = [c for c in com_texto if c["kind"] == "billing_equipe"][0]["texto"]
    check("o texto da forma real e o SINGULAR de hoje, byte a byte",
          texto == BC.build_customer_message(b["parcelas"][0],
                                             c_equipe["message_template"], c_equipe), texto[:200])
    check("  ... e ele NAO diz 'as parcelas 1' (o plural falso de antes)",
          "as parcelas" not in texto, texto[:200])

    # -- 💭 O CAMINHO "N BOLETOS": Segurado E, dois recibos na mesma seguradora -
    fila_e = [dict(i) for i in ACERVO["sinteticos"]]
    grupos_e = BC.agrupar_por_segurado(fila_e, CO_ALFA)
    check("💭 E: dois recibos distintos = UM grupo com DUAS parcelas",
          len(grupos_e) == 1 and len(grupos_e[0]["parcelas"]) == 2,
          [(g["segurado_chave"], len(g["parcelas"])) for g in grupos_e])
    re_ = rodar_entrega(fila_e)
    doc_e = [c for c in re_["chamadas"] if c["documento"]]
    notas_e = [c for c in re_["chamadas"] if c["kind"] == "billing_equipe_nota"]
    texto_e = [c for c in re_["chamadas"]
               if c["kind"] == "billing_equipe" and str(c["texto"]).strip()]
    reservas_e = [x for x in re_["banco"].rpcs if x["nome"] == "billing_reservar_obrigacao"]
    check("💭 E: DOIS documentos, um por recibo", len(doc_e) == 2,
          [str((c["documento"] or {}).get("filename")) for c in doc_e])
    check("💭 E: cada PDF viaja com o `ledger_ref` da SUA parcela",
          len({str((c["ledger_ref"] or {}).get("id")) for c in doc_e}) == 2,
          [str((c["ledger_ref"] or {}).get("id")) for c in doc_e])
    check("💭 E: DUAS reservas, com os dois recibos",
          len(reservas_e) == 2 and len({p["params"].get("p_recibo") for p in reservas_e}) == 2,
          [p["params"].get("p_recibo") for p in reservas_e])
    check("💭 E: UM texto e UMA nota (nada picotado)",
          len(texto_e) == 1 and len(notas_e) == 1, (len(texto_e), len(notas_e)))
    check("💭 E: ZERO bloqueios", re_["blockers"] == [], re_["blockers"])

    # A COPY do plural, sobre o texto que o motor montou
    t_e = texto_e[0]["texto"] if texto_e else ""
    for pedaco in ("as parcelas", "Seguem os boletos abaixo.", "estão pendentes",
                   "gerou novos boletos"):
        check("plural: o texto diz %r" % pedaco, pedaco in t_e, t_e[:220])
    check("plural: as apolices distintas viram `Apólices:`",
          "Apólices:" in t_e, t_e[-160:])
    check("🔴 A-5: DOIS recibos numerados '1' aparecem OS DOIS, com a apolice",
          "1 (apólice …AAAA) e 1 (apólice …BBBB)" in t_e, t_e[:260])
    check("plural: a lista de parcelas usa virgula e `e` antes da ultima",
          BC.lista_de_parcelas(["2/6", "3/6", "4/6"]) == "2/6, 3/6 e 4/6",
          BC.lista_de_parcelas(["2/6", "3/6", "4/6"]))
    check("CONTROLE: quando os numeros JA sao distintos, o rotulo e o numero e mais nada",
          BC.rotulos_das_parcelas([{"numero_parcela": "2/6", "numero_apolice": "X"},
                                   {"numero_parcela": "3/6", "numero_apolice": "Y"}])
          == ["2/6", "3/6"],
          BC.rotulos_das_parcelas([{"numero_parcela": "2/6", "numero_apolice": "X"},
                                   {"numero_parcela": "3/6", "numero_apolice": "Y"}]))
    check("CONTROLE: sem apolice para distinguir, o numero se REPETE ('1 e 1')",
          BC.lista_de_parcelas(BC.rotulos_das_parcelas([{"numero_parcela": "1"},
                                                        {"numero_parcela": "1"}])) == "1 e 1",
          BC.rotulos_das_parcelas([{"numero_parcela": "1"}, {"numero_parcela": "1"}]))

    # 🔴 N=1 continua BYTE A BYTE o template de hoje
    um = dict(ACERVO["itens"][0])
    grupo_de_um = BC.agrupar_por_segurado([um])[0]
    check("N=1 usa o template de hoje BYTE A BYTE",
          BC.mensagem_do_grupo(grupo_de_um, c_equipe)
          == BC.build_customer_message(um, c_equipe["message_template"], c_equipe))
    check("CONTROLE: e o do grupo de DOIS e DIFERENTE do singular da 1a parcela",
          BC.mensagem_do_grupo(grupos_e[0], c_equipe)
          != BC.build_customer_message(grupos_e[0]["parcelas"][0],
                                       c_equipe["message_template"], c_equipe))
    # template PERSONALIZADO pela corretora: singular, com a LISTA no lugar da parcela
    c_pers = cfg("equipe", message_template="Oi {primeiro_nome}, parcela {numero_parcela}.")
    pers = BC.mensagem_do_grupo(grupos_e[0], c_pers)
    check("template personalizado: nao inventamos plural -- a LISTA entra em `{numero_parcela}`",
          pers.startswith("Oi ") and "apólice …AAAA" in pers, pers)

    # -- 🔴 A-7: o item REAL da Tokio (ramo "180", sem descricao) --------------
    #    📊 os 5 itens reais da Tokio chegam sem `item_segurado`/`veiculo`/`bem`
    #    e com `ramo="180"`: a mensagem dizia "do seguro do 180". Sem o ramo, o
    #    default dizia "do seguro do seguro". As duas frases chegaram ao segurado.
    tokio = dict(ACERVO["itens"][1], ramo="180")
    check("A-7: ramo numerico NAO e nome de bem", BC._insured_item_name(tokio, default="") == "",
          BC._insured_item_name(tokio, default=""))
    msg = BC.build_customer_message(tokio, c_equipe["message_template"], c_equipe)
    check("A-7: a mensagem NAO diz 'do seguro do 180'", "do seguro do 180" not in msg, msg[:220])
    check("A-7: nem 'do seguro do seguro'", "do seguro do seguro" not in msg, msg[:220])
    check("A-7: a frase fica 'do seguro ainda está pendente'",
          "do seguro ainda está pendente" in msg, msg[:220])
    com_bem = BC.build_customer_message(dict(tokio, item_segurado="Fiat Mobi 2020"),
                                        c_equipe["message_template"], c_equipe)
    check("CONTROLE: com um bem de verdade, o nome ENTRA na frase (o guarda ve a diferenca)",
          "do seguro do Fiat Mobi 2020 ainda está pendente" in com_bem, com_bem[:220])
    check("CONTROLE: nome com digitos ('Fiat Mobi 2020') continua sendo nome",
          BC._insured_item_name({"item_segurado": "Fiat Mobi 2020"}) == "Fiat Mobi 2020")
    check("CONTROLE: template PERSONALIZADO nao e reescrito -- recebe a palavra de sempre",
          BC.build_customer_message(tokio, "Oi {primeiro_nome}, {item_segurado}.", c_equipe)
          .endswith(", seguro."),
          BC.build_customer_message(tokio, "Oi {primeiro_nome}, {item_segurado}.", c_equipe))


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
    # 🔴 B1 -- 📊 a fila real tem mediana de 144 s e maximo de 511 s, e o worker
    #    e SERIAL (PORTAL_WORKER_CONCURRENCY=1). Com teto de 120 s, do 2o portal
    #    em diante o `_poll_job` devolvia `timeout`.
    check("o teto de espera do canario tem default 600s e clamp (60..900)",
          BC.login_check_teto_s({}) == 600
          and BC.login_check_teto_s({"BILLING_LOGIN_CHECK_TETO_S": "5"}) == 60
          and BC.login_check_teto_s({"BILLING_LOGIN_CHECK_TETO_S": "9000"}) == 900,
          (BC.login_check_teto_s({}), BC.login_check_teto_s({"BILLING_LOGIN_CHECK_TETO_S": "5"}),
           BC.login_check_teto_s({"BILLING_LOGIN_CHECK_TETO_S": "9000"})))
    check("o teto novo cobre o PIOR tempo de fila medido (511 s)",
          BC.login_check_teto_s({}) > 511, BC.login_check_teto_s({}))
    check("a variavel de ambiente esta escrita no docstring (P4)",
          "BILLING_LOGIN_CHECK_TETO_S" in (BC.login_check_teto_s.__doc__ or ""),
          BC.login_check_teto_s.__doc__)

    from datetime import datetime, timedelta, timezone

    def ha(horas):
        return (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()

    # allianz: ok · hdi: senha recusada · mapfre: fora do ar HA POUCO ·
    # tokiomarine: fora do ar HA MUITO (o breaker reabre) E o canario NAO TERMINA
    # a tempo -- o caso da fila real (📊 mediana 144 s, maximo 511 s, worker
    # serial) · yelum: unknown e o login FALHA · zurich: sem credencial nenhuma
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
            if portal == "tokiomarine_corretor":
                # 🔴 B1 -- o que `_poll_job` devolve quando o RELOGIO acaba: nao e
                #    veredito nenhum sobre a credencial, e o texto diz isso.
                return {"id": job_id, "portal_key": portal, "status": "timeout",
                        "error": "portal_job nao terminou dentro do tempo limite",
                        "evidence": {}}
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
    check("🔴 o canario com VEREDITO RUIM (`failed`) nao abre varredura",
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

    # -- 🔴 B1: AUSENCIA DE VEREDITO NAO E VEREDITO RUIM ----------------------
    #    📊 Com teto de 120 s contra uma fila de mediana 144 s (maximo 511 s) num
    #    worker serial, o `login_check` estourava o relogio e o portal era
    #    DESCARTADO: 5 de 6 portais deixavam de ser varridos, com todos os gates
    #    verdes e o relatorio dizendo que o teste de entrada falhou -- o que era
    #    falso. `timeout` diz "o worker nao respondeu", nao "a senha esta errada".
    check("🔴 o canario que NAO TERMINOU (`timeout`) VARRE assim mesmo",
          "tokiomarine_corretor" in varreduras, varreduras)
    check("  ... e o relatorio diz isso, em portugues, sem acusar a senha",
          "o teste de entrada nao terminou em" in relatorio
          and "varri assim mesmo" in relatorio, relatorio[-1600:])
    check("  ... e a frase avisa quem vai dizer a verdade se a senha estiver errada",
          "se a senha estiver errada o relatorio dira" in relatorio, relatorio[-1600:])
    check("CONTROLE: o `failed` continua sendo descarte (o guarda ve a diferenca)",
          "nao varri este portal nesta execucao" in relatorio, relatorio[-1600:])

    # -- 🔴 P8: UM `login_check` POR PORTAL, mesmo com duas execucoes juntas ---
    #    Login repetido em portal de seguradora nao e desperdicio: e o gesto que
    #    faz a seguradora bloquear a conta da corretora.
    banco_com_fila = BancoLeve()
    banco_com_fila.dados["portal_jobs"] = [{
        "id": "job-login_check-allianz_corretor", "company_id": CO_ALFA,
        "portal_key": "allianz_corretor", "journey": "login_check",
        "status": "queued", "created_at": ha(0)}]
    enfileirados.clear()
    try:
        asyncio.run(BC.execute_billing_collection_routine(banco_com_fila, rotina))
    except Exception as e:  # noqa: BLE001
        check("[G10] a 2a execucao roda", False, "%s: %s" % (type(e).__name__, e))
    canarios2 = [p for p, j in enfileirados if j == BC.JORNADA_DO_CANARIO]
    varreduras2 = [p for p, j in enfileirados if j == BC.JORNADA_DA_VARREDURA]
    check("🔴 P8: o `login_check` que JA esta na fila e REUSADO (nao enfileira outro)",
          "allianz_corretor" not in canarios2, canarios2)
    check("  ... e o portal reusado continua sendo varrido (reusar nao e descartar)",
          "allianz_corretor" in varreduras2, varreduras2)
    check("CONTROLE: os OUTROS portais continuam enfileirando o canario deles",
          "tokiomarine_corretor" in canarios2 and "yelum_corretor" in canarios2, canarios2)
    # CONTROLE: um job login_check TERMINADO nao e reusado -- o veredito de 40min
    # atras nao responde "a credencial entra AGORA?".
    banco_terminado = BancoLeve()
    banco_terminado.dados["portal_jobs"] = [{
        "id": "job-login_check-allianz_corretor", "company_id": CO_ALFA,
        "portal_key": "allianz_corretor", "journey": "login_check",
        "status": "done", "created_at": ha(0)}]
    enfileirados.clear()
    try:
        asyncio.run(BC.execute_billing_collection_routine(banco_terminado, rotina))
    except Exception:  # noqa: BLE001
        pass
    check("CONTROLE: job `done` na tabela NAO e reusado (enfileira um canario novo)",
          "allianz_corretor" in [p for p, j in enfileirados if j == BC.JORNADA_DO_CANARIO],
          enfileirados)


# ==========================================================================
# G12 -- O RELATORIO DA EXECUCAO SAI SEM CPF E SEM TELEFONE INTEIRO
#        (e a NOTA A ATENDENTE continua com o telefone -- e o CONTROLE)
# ==========================================================================
#
# 📊 Medido em 13/09/2026 (relatorio §1, premissa 11):
#     select count(*) from routine_runs r join routines t on t.id=r.routine_id
#      where t.config->>'kind'='billing_collection' and r.output_full like '%CPF/CNPJ%'
#     -> 7 de 49 execucoes, 6 delas com digitos de documento.
#
# 🔴 TRES NIVEIS DE EXPOSICAO, DE PROPOSITO (proposta §9 B4.4):
#     ledger ............ guarda `to_phone`, comentado, e nao sai dali
#     nota a atendente .. WhatsApp LEGIVEL -- ela precisa DISCAR
#     relatorio/artifact  mascarados -- o relatorio e legivel por qualquer sessao
#                         autenticada da corretora, e o artifact pode virar link
#                         publico de 30 dias
#
# E por isso o CONTROLE deste guarda e a nota interna: um guarda que so afirmasse
# "nao tem telefone em lugar nenhum" ficaria verde no dia em que alguem apagasse
# o telefone da nota da atendente -- e a atendente ficaria sem como ligar
# (CLAUDE.md §9.3: prove que as duas coisas CONSEGUEM ser diferentes).
def _maior_corrida_de_digitos(texto):
    maior, atual = 0, 0
    for ch in str(texto or ""):
        atual = atual + 1 if ch.isdigit() else 0
        maior = max(maior, atual)
    return maior


def gate_G12():
    print("\n[G12] o relatorio da execucao sai sem CPF/CNPJ nem telefone inteiros")
    from app.services import billing_collection as BC

    com_documento = item_do_acervo(1)      # CNPJ de 14 digitos + WhatsApp
    sem_telefone = item_do_acervo(0)       # documento, `whatsapp` vazio
    doc = str(com_documento["cpf_cnpj"])
    tel = str(com_documento["whatsapp"])
    check("o item do acervo TEM documento e telefone (senao o guarda nao mede nada)",
          len(doc) >= 11 and len(tel) >= 12, (len(doc), len(tel)))

    relatorio = BC._format_report(
        routine={"name": "Cobranca de boletos"}, cfg=cfg("equipe"),
        jobs=[{"id": "j1", "portal_key": "tokiomarine_corretor", "status": "done"}],
        items=[com_documento, sem_telefone], boletos=[], blockers=[],
        approval_id=None, test_sends=[], estados={"entregue_equipe": 1})

    check("🔴 o CNPJ inteiro NAO esta no relatorio da execucao", doc not in relatorio, doc[:4])
    check("🔴 o telefone inteiro NAO esta no relatorio da execucao", tel not in relatorio)
    check("...nem o telefone sem o 55 na frente", tel[2:] not in relatorio)
    check("...nem o documento do segurado SEM telefone", str(sem_telefone["cpf_cnpj"]) not in relatorio)
    check("os 4 ultimos digitos do documento FICAM (a atendente precisa distinguir dois homonimos)",
          "CPF/CNPJ ...%s" % doc[-4:] in relatorio,
          [l for l in relatorio.splitlines() if "CPF/CNPJ" in l])
    check("...e os 4 ultimos do telefone tambem",
          "WhatsApp: ...%s" % tel[-4:] in relatorio,
          [l for l in relatorio.splitlines() if "WhatsApp" in l])
    check("quem nao tem telefone continua dizendo POR QUE (`sem telefone (...)`)",
          "sem telefone (nao encontrado)" in relatorio,
          [l for l in relatorio.splitlines() if "sem telefone" in l])
    check("🔴 nenhuma corrida de 8+ digitos sobrou no relatorio inteiro",
          _maior_corrida_de_digitos(relatorio) < 8,
          [l for l in relatorio.splitlines() if _maior_corrida_de_digitos(l) >= 8])
    check("o relatorio continua dizendo o nome do cliente (mascarar demais cega a atendente)",
          com_documento["cliente_nome"] in relatorio)
    check("...e o valor e o vencimento", "676,31" in relatorio or "676.31" in relatorio,
          [l for l in relatorio.splitlines() if "676" in l])

    # --- 🔴 O CONTROLE: a NOTA INTERNA continua com o telefone LEGIVEL
    nota = BC._nota_interna_para_a_equipe(com_documento, cfg("equipe"))
    legivel = BC._whatsapp_legivel(tel)
    check("CONTROLE: a nota a atendente CONTEM o WhatsApp legivel", legivel in nota,
          [l for l in nota.splitlines() if "WhatsApp" in l])
    check("...com TODOS os digitos do numero (ela precisa discar)",
          "".join(c for c in legivel if c.isdigit()) == tel, legivel)
    check("🔴 o guarda VE a diferenca: a nota tem o numero, o relatorio nao",
          legivel in nota and legivel not in relatorio)

    # --- e a nota do GRUPO (N parcelas, 1 mensagem) tambem continua com o numero
    grupo = {"parcelas": [item_do_acervo(1), item_do_acervo(5)]}
    nota_grupo = BC._nota_interna_do_grupo(grupo, cfg("equipe"))
    check("CONTROLE: a nota do grupo de N parcelas tambem mantem o WhatsApp legivel",
          legivel in nota_grupo, [l for l in nota_grupo.splitlines() if "WhatsApp" in l])

    # --- a peca do Artifact Hub continua sem documento (ela ja era assim; nao regrediu)
    blocos = BC.compor_peca_da_cobranca(
        routine={"name": "Cobranca"}, cfg=cfg("equipe"), items=[com_documento], boletos=[],
        fila=[com_documento], retidos=[], tarefas=[], blockers=[], test_sends=[])
    check("CONTROLE de regressao: a peca do Artifact Hub continua sem documento inteiro",
          doc not in json.dumps(blocos, default=str, ensure_ascii=False))


# ==========================================================================
# G13 -- SESSAO CAIDA NAO E SENHA RECUSADA (e credencial AUSENTE tambem nao)
# ==========================================================================
#
# 🔴 14/09/2026, lente do dado (A-4). `_MARCAS_DE_CREDENCIAL` tem `"invalid"`, e
# `"sessao invalida"` casa com ela. O classificador lia as marcas de credencial
# ANTES das de sessao caida -- entao uma sessao que caiu (estado TRANSITORIO: a
# proxima execucao faz login e entra) virava `credencial_recusada`, que so fecha
# por GESTO HUMANO na tela de Conectores. Ou seja: o portal da corretora ficava
# desligado por tempo indefinido, e a linha do relatorio mandava trocar uma senha
# que estava certa.
#
# A ORDEM e a correcao; a lista continua a mesma.

def gate_G13():
    print("\n[G13] `veredito_de_saude`: sessao caida != senha recusada != falta cadastrar")
    from portal_worker import worker as W

    check("as marcas de credencial realmente contem 'invalid' (senao o guarda nao mede nada)",
          "invalid" in W._MARCAS_DE_CREDENCIAL, W._MARCAS_DE_CREDENCIAL)
    check("e 'sessao invalida' esta nas marcas de SESSAO CAIDA",
          "sessao invalida" in W._MARCAS_DE_SESSAO_CAIDA, W._MARCAS_DE_SESSAO_CAIDA)
    check("🔴 'sessao invalida' num `failed` -> `expirada`, NAO `credencial_recusada`",
          W.veredito_de_saude("failed", {}, "a sessao invalida foi descartada") == W.SAUDE_EXPIRADA,
          W.veredito_de_saude("failed", {}, "a sessao invalida foi descartada"))
    check("🔴 'voltou para o login' num `failed` -> `expirada`",
          W.veredito_de_saude("failed", {}, "o portal voltou para o login") == W.SAUDE_EXPIRADA,
          W.veredito_de_saude("failed", {}, "o portal voltou para o login"))
    check("🔴 'credenciais ausentes' -> `pede_humano` (nao ha senha para trocar)",
          W.veredito_de_saude("failed", {}, "credenciais ausentes") == W.SAUDE_PEDE_HUMANO,
          W.veredito_de_saude("failed", {}, "credenciais ausentes"))
    check("  ... e 'username/password ausentes' tambem",
          W.veredito_de_saude("failed", {}, "username/password ausentes") == W.SAUDE_PEDE_HUMANO,
          W.veredito_de_saude("failed", {}, "username/password ausentes"))
    # 🔴 OS CONTROLES: o que o guarda NAO pode ter quebrado
    real_mapfre = "a MAPFRE recusou a credencial (autenticacao invalida)"
    check("CONTROLE: a frase REAL da Mapfre continua `credencial_recusada`",
          W.veredito_de_saude("failed", {}, real_mapfre) == W.SAUDE_CREDENCIAL_RECUSADA,
          W.veredito_de_saude("failed", {}, real_mapfre))
    real_allianz = "credenciais rejeitadas pelo portal Allianz"
    check("CONTROLE: a frase REAL da Allianz continua `credencial_recusada`",
          W.veredito_de_saude("failed", {}, real_allianz) == W.SAUDE_CREDENCIAL_RECUSADA,
          W.veredito_de_saude("failed", {}, real_allianz))
    check("CONTROLE: `done` continua `ok`, mesmo citando a sessao caida (relogin deu certo)",
          W.veredito_de_saude("done", {}, "a sessao caiu e eu entrei de novo") == W.SAUDE_OK)
    check("CONTROLE: `logged_in` vence tudo (o `needs_human` da Zurich e da VARREDURA)",
          W.veredito_de_saude("needs_human", {"logged_in": True}, "http 200 com ZERO parcelas")
          == W.SAUDE_OK)
    check("CONTROLE: excecao transitoria sem tentativas esgotadas continua '' (nao mexe)",
          W.veredito_de_saude("failed", {"excecao_transitoria": True}, "timeout") == "")
    check("CONTROLE: 'tela pos-login Allianz nao reconhecida' continua `pede_humano`",
          W.veredito_de_saude("needs_human", {}, "tela pos-login Allianz nao reconhecida")
          == W.SAUDE_PEDE_HUMANO,
          W.veredito_de_saude("needs_human", {}, "tela pos-login Allianz nao reconhecida"))
    check("🔴 o guarda VE a diferenca: as duas frases dao vereditos DIFERENTES",
          W.veredito_de_saude("failed", {}, "a sessao invalida foi descartada")
          != W.veredito_de_saude("failed", {}, real_mapfre))


# ==========================================================================
# AS MUTACOES -- (id, arquivo, de, para, gate)
# ==========================================================================

MUTACOES = [
    ("M1", "app/services/platform_outbound.py",
     '    "billing_cliente",       # o texto ao segurado, quando o modo cliente for ligado\n', "", "G1"),
    ("M2", "app/services/billing_collection.py",
     '    motivo = evidencia.get("message") or (job or {}).get("error")\n',
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
    # 🔴 M7b desliga a CONSOLIDACAO por recibo: os 4 lancamentos do mesmo boleto
    #    voltam a ser 4 parcelas, 1 reserva ganha e 3 perdem -> 3 BLOQUEIOS
    #    FALSOS por execucao, que e o defeito que a lente do dado mediu.
    ("M7b", "app/services/billing_collection.py",
     '        grupo["parcelas"] = ordenar_para_entrega(consolidar_por_recibo(grupo["parcelas"]))\n',
     '        grupo["parcelas"] = ordenar_para_entrega(grupo["parcelas"])\n', "G7"),
    # 🔴 M7c aceita candidato so-numerico como nome de bem: volta "do seguro do 180".
    ("M7c", "app/services/billing_collection.py",
     '        # "180" e "0180" são código de ramo; "Fiat Mobi 2020" tem dígitos e é nome.\n'
     '        if all((ch.isdigit() or ch in " .,-/") for ch in texto):\n'
     "            continue\n", "", "G7"),
    # 🔴 M7d aceita qualquer lixo como documento: dois segurados com "000.000/0"
    #    no campo viram UM, e a janela de N dias segura a cobranca do segundo.
    ("M7d", "app/services/billing_collection.py",
     "    if doc and len(doc) in (11, 14) and len(set(doc)) > 1:\n",
     "    if doc:\n", "G7"),
    # 🔴 M7e ignora o `company_id` da execucao na chave do grupo (P7).
    ("M7e", "app/services/billing_collection.py",
     '    empresa = (str((item or {}).get("company_id") or "").strip().lower()\n'
     '               or str(company_id or "").strip().lower())\n',
     '    empresa = str((item or {}).get("company_id") or "").strip().lower()\n', "G7"),
    # 🔴 M10 abre a varredura mesmo com o breaker aberto ou o canario reprovado.
    ("M10", "app/services/billing_collection.py",
     "            if account is None:\n                continue\n",
     '            if account is None:\n                account = {"id": None}\n', "G10"),
    # 🔴 M10b volta a DESCARTAR o portal cujo canario nao terminou: e o defeito
    #    que tirava 5 de 6 portais da varredura com todos os gates verdes.
    ("M10b", "app/services/billing_collection.py",
     "        if status not in TERMINAL_JOB_STATUSES:\n",
     "        if False:\n", "G10"),
    # 🔴 M10c desliga a dedup do `login_check`: duas execucoes no mesmo minuto
    #    fazem DOIS logins por portal na seguradora.
    ("M10c", "app/services/billing_collection.py",
     "        if job_ja_na_fila:\n",
     "        if False:\n", "G10"),
    # 🔴 M12 desliga a mascara do relatorio da execucao: o documento e o telefone do
    #    segurado voltam inteiros para `routine_runs.output_full` -- que foi
    #    exatamente como as 7 execucoes de 📊 10 e 11/09 ficaram com CPF em claro.
    ("M12", "app/services/billing_collection.py",
     '            doc = _mascarar_documento(item.get("cpf_cnpj")) or "?"\n'
     '            phone = (_mascarar_telefone(item.get("whatsapp"))\n',
     '            doc = item.get("cpf_cnpj") or "?"\n'
     '            phone = (str(item.get("whatsapp") or "")\n', "G12"),
    # 🔴 M3b volta a ler a lista de recusa ANTES de contar o dashboard: um toast
    #    de "acesso negado" sobre a tela LOGADA vira `failed` -> breaker aberto
    #    ate alguem trocar uma senha que esta certa (P5).
    ("M3b", "portal_worker/journeys/allianz_corretor.py",
     "    if hits < 2 and any(item in text for item in _FAIL):\n",
     "    if any(item in text for item in _FAIL):\n", "G3"),
    # 🔴 M13 volta a ler as marcas de CREDENCIAL antes das de SESSAO CAIDA: uma
    #    sessao caida ("sessao invalida" casa com "invalid") vira senha recusada,
    #    e o breaker fica aberto ate um gesto humano (A-4).
    ("M13", "portal_worker/worker.py",
     "    if (str(status) == \"failed\" and not caiu and not falta_cadastrar\n"
     "            and any(m in texto for m in _MARCAS_DE_CREDENCIAL)):\n",
     "    if str(status) == \"failed\" and any(m in texto for m in _MARCAS_DE_CREDENCIAL):\n",
     "G13"),
]

GATES = {"G1": gate_G1, "G2": gate_G2, "G3": gate_G3, "G4": gate_G4, "G5": gate_G5,
         "G6": gate_G6, "G7": gate_G7, "G8": gate_G8, "G10": gate_G10, "G12": gate_G12,
         "G13": gate_G13}


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
