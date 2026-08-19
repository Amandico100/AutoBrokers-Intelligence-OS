# -*- coding: utf-8 -*-
"""A sessao caida volta sozinha -- e o aviso ao grupo diz o que realmente houve.

O QUE ACONTECEU DE VERDADE (18/08/2026 10:35)
=============================================

A HDI entregou 1 boleto. A Allianz falhou e o grupo da corretora recebeu:

    "ALLIANZ - nao consegui ler a lista de parcelas"

O Founder foi investigar leitura de tabela. Nao era leitura de tabela.

📊 A evidencia do job (`portal_jobs`, portal_key='allianz_corretor',
status='needs_human') diz, campo por campo:

    logged_in: true                 session_reused: true
    epac_token_before: {expired: false, mins_to_exp: 472}
    navegacao: /private/home -> /private/application/static -> blank
               -> /drbl13/SEAServlet -> /idp/
    body_text: VAZIO                profiler.screens: 0
    acoes_recusadas: "Gestao", "Consultas", "Inicio" -- alvo nao existe
    stage: inadimplentes_nao_localizado

A sessao reaproveitada estava morta DO LADO DO SERVIDOR. O relogio do token
local dizia que faltavam 7h48, e o unico gatilho de relogin era
`tok_before["expired"] is True`. Nao disparou. Nenhuma tela renderizou.

📊 E a jornada NAO esta quebrada: em 17/08 ela rodou 5 vezes e funcionou nas 5
(`inadimplentes_count=3`, `boletos_download_ok=3`, `inadimplentes_rows_seen=38`).

⚠️ POR QUE O CONSERTO NAO PODE SER "SEMPRE RELIGAR"

Ha aviso no proprio codigo: forcar login fresco em sessao SAUDAVEL quebrou o
acesso a inadimplentes (job a9733bb5). Por isso cada guarda deste arquivo tem
um CONTROLE: a mesma pergunta feita sobre uma sessao VIVA tem de responder
"nao esta morta". Um detector que responde "morta" para tudo nao detecta nada.

O QUE ESTE ARQUIVO GUARDA
-------------------------
[1] o diagnostico de sessao morta separa morto de vivo (com CONTROLE)
[2] o sweep religa UMA vez -- e so quando ha evidencia positiva de morte
[3] cada estagio de falha tem a SUA frase no aviso ao grupo humano
[4] o boleto entregue e registrado, e a falha de registro aparece
"""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))


# --------------------------------------------------------------------------
# Bootstrap: a jornada Allianz importa so stdlib + JourneyResult; o
# billing_collection precisa dos pacotes app.* sem executar os __init__ deles
# (que puxam openai e amigos).
# --------------------------------------------------------------------------
import portal_worker.journeys.allianz_corretor as AZ  # noqa: E402


def _load(nome: str, caminho: str):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(RAIZ, caminho))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


for _n in ("app", "app.services", "app.core"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []

BC = _load("app.services.billing_collection", "app/services/billing_collection.py")


# ==========================================================================
print("\n[1] O diagnostico de sessao morta -- e o CONTROLE que da direito a")
print("    conclusao: sessao viva NAO pode ser diagnosticada como morta")
# ==========================================================================

MENU_VIVO = (
    "Corretor Principal  Vendas  Consultas  Gestao  Nova Cotacao\n"
    "PARCELAS INADIMPLENTES  Fale com a gente agora  Tempo Sessao 29:58"
)

# O caso real de 18/08, campo por campo.
CASO_18_08 = dict(
    url_atual="https://www.allianznet.com.br/idp/",
    urls_vistas=[
        "https://www.allianznet.com.br/ngx-azb-epac/private/home",
        "https://www.allianznet.com.br/ngx-azb-epac/private/application/static",
        "about:blank",
        "https://www.allianznet.com.br/drbl13/SEAServlet",
        "https://www.allianznet.com.br/idp/",
    ],
    body_text="",
    acoes_recusadas=[
        {"acao": "click", "alvo": "Gestao", "motivo": "alvo nao existe na tela atual"},
        {"acao": "click", "alvo": "Consultas", "motivo": "alvo nao existe na tela atual"},
        {"acao": "click", "alvo": "Inicio", "motivo": "alvo nao existe na tela atual"},
    ],
)

d_morta = AZ.diagnosticar_sessao_morta(**CASO_18_08)
check("o job de 18/08 e diagnosticado como sessao MORTA", d_morta.get("morta") is True, d_morta)
check("e o motivo cita o provedor de identidade (/idp/), nao a leitura da tabela",
      "identidade" in str(d_morta.get("motivo") or "").lower(), d_morta.get("motivo"))
check("o sinal do /idp/ final foi visto",
      d_morta["sinais"]["url_final_no_idp"] is True, d_morta["sinais"])
check("o sinal da tela vazia foi visto",
      d_morta["sinais"]["tela_vazia"] is True, d_morta["sinais"])
check("os tres alvos de menu recusados foram contados",
      d_morta["sinais"]["alvos_de_menu_recusados"] == 3, d_morta["sinais"])

# ---- CONTROLE 1: a MESMA funcao sobre a home saudavel de 17/08 -----------
d_viva = AZ.diagnosticar_sessao_morta(
    url_atual="https://www.allianznet.com.br/ngx-azb-epac/private/home",
    urls_vistas=["https://www.allianznet.com.br/ngx-azb-epac/private/home"],
    body_text=MENU_VIVO,
    acoes_recusadas=[],
)
check("CONTROLE: a home saudavel NAO e diagnosticada como morta",
      d_viva.get("morta") is False, d_viva)
check("CONTROLE: e sem motivo nenhum escrito", not d_viva.get("motivo"), d_viva)

# ---- CONTROLE 2: fator que nao muda o resultado nao e a causa ------------
# O SEAServlet aparece no trace do job que falhou. Ele tambem aparece em
# navegacao saudavel: sozinho, NAO prova morte. Se um dia provar, esta linha
# fica vermelha e alguem tem de decidir de novo.
d_seaservlet = AZ.diagnosticar_sessao_morta(
    url_atual="https://www.allianznet.com.br/ngx-azb-epac/private/home",
    urls_vistas=["https://www.allianznet.com.br/drbl13/SEAServlet"],
    body_text=MENU_VIVO,
    acoes_recusadas=[],
)
check("CONTROLE: SEAServlet no trace, com o menu na tela, NAO e morte",
      d_seaservlet.get("morta") is False, d_seaservlet)
check("mas o sinal fica registrado para quem investigar",
      d_seaservlet["sinais"]["trace_passou_por_seaservlet"] is True, d_seaservlet["sinais"])

# ---- CONTROLE 3: tela sem inadimplentes, mas com o portal inteiro --------
# Este e o caso que o job a9733bb5 ensinou a NAO tratar como sessao morta:
# a sessao esta viva, o portal responde, so a tela de inadimplentes nao veio.
d_so_faltou_tela = AZ.diagnosticar_sessao_morta(
    url_atual="https://www.allianznet.com.br/ngx-azb-epac/private/home",
    urls_vistas=[],
    body_text=MENU_VIVO + "\nNenhum registro encontrado para o filtro",
    acoes_recusadas=[{"acao": "click", "alvo": "Gerar Planilha", "motivo": "alvo nao existe na tela atual"}],
)
check("CONTROLE: portal vivo sem a tela de inadimplentes NAO vira relogin",
      d_so_faltou_tela.get("morta") is False, d_so_faltou_tela)

# ---- a tela de login de volta e morte, com ou sem /idp/ ------------------
d_login = AZ.diagnosticar_sessao_morta(
    url_atual="https://www.allianznet.com.br/ngx-azb-epac/public/home",
    urls_vistas=[],
    body_text="Bem-vindo(a) a AllianzNet\nIniciar Sessao\nEsqueceu a senha?",
    acoes_recusadas=[],
)
check("a tela de login de volta tambem e sessao morta", d_login.get("morta") is True, d_login)

# ---- o token local dizendo 'valido' nao muda o diagnostico --------------
# 📊 mins_to_exp=472 no job que falhou. O diagnostico NAO olha o relogio local
# de proposito: foi exatamente ele que mentiu.
_src_diag = inspect.getsource(AZ.diagnosticar_sessao_morta)
check("o diagnostico nao consulta o relogio do token local (foi ele que mentiu)",
      "_epac_token_age" not in _src_diag
      and "mins_to_exp" not in _src_diag
      and '"expired"' not in _src_diag, _src_diag[:200])


# ==========================================================================
print("\n[2] O sweep religa UMA vez -- nunca zero quando morreu, nunca duas")
# ==========================================================================


class PaginaDeMentira:
    """So o que `cobranca_sweep` chama direto na pagina."""

    url = "https://www.allianznet.com.br/idp/"

    async def wait_for_timeout(self, _ms):
        return None


def _rodar_sweep(*, chega_na_tela, morta, relogin_ok=True):
    """Devolve (resultado, evidence, quantas vezes religou)."""
    original = {n: getattr(AZ, n) for n in (
        "login_check", "_epac_token_age", "_install_api_capture",
        "_ensure_inadimplentes_page", "_diagnosticar_sessao_na_pagina",
        "_relogin_fresh", "_collect_inadimplentes_items", "_body_text",
    )}
    tentativas = {"ensure": 0, "relogin": 0}

    async def fake_login(page, params, evidence):
        return AZ.JourneyResult(status="done", captured={"logged_in": True})

    async def fake_token(page):
        # o relogio local mentindo, como em 18/08
        return {"has_token": True, "expired": False, "mins_to_exp": 472}

    async def fake_ensure(page, params, evidence):
        tentativas["ensure"] += 1
        return bool(chega_na_tela[min(tentativas["ensure"] - 1, len(chega_na_tela) - 1)])

    async def fake_diag(page, evidence):
        return {"morta": morta, "motivo": "o portal devolveu o navegador para a tela de identidade (/idp/)"
                if morta else "", "sinais": {}}

    async def fake_relogin(page, params, evidence, *, motivo=""):
        tentativas["relogin"] += 1
        return relogin_ok

    async def fake_items(page, max_items, evidence):
        return [{"recibo": "1", "cliente_nome": "FULANO", "vencimento": "01/08/2026"}]

    async def fake_body(page):
        return ""

    AZ.login_check = fake_login
    AZ._epac_token_age = fake_token
    AZ._install_api_capture = lambda page, sink: None
    AZ._ensure_inadimplentes_page = fake_ensure
    AZ._diagnosticar_sessao_na_pagina = fake_diag
    AZ._relogin_fresh = fake_relogin
    AZ._collect_inadimplentes_items = fake_items
    AZ._body_text = fake_body
    evidence: dict = {}
    try:
        res = asyncio.run(AZ.cobranca_sweep(
            PaginaDeMentira(), {"download_boletos": False, "max_boletos": 3}, evidence))
    finally:
        for nome, valor in original.items():
            setattr(AZ, nome, valor)
    return res, evidence, tentativas


# --- o caso de 18/08: morreu, religou, chegou na segunda ------------------
res, ev, t = _rodar_sweep(chega_na_tela=[False, True], morta=True)
check("sessao morta: religou exatamente UMA vez", t["relogin"] == 1, t)
check("sessao morta: tentou a tela exatamente DUAS vezes", t["ensure"] == 2, t)
check("e a cobranca terminou (nao virou needs_human)", res.status == "done", res.message)
check("a evidencia registra o diagnostico", "sessao_morta_detectada" in ev, list(ev))
check("a evidencia registra que houve relogin por sessao morta",
      ev.get("relogin_por_sessao_morta") is True, ev.get("relogin_por_sessao_morta"))

# --- CONTROLE: sessao VIVA, tela nao veio -> ZERO relogin ----------------
res_v, ev_v, t_v = _rodar_sweep(chega_na_tela=[False], morta=False)
check("CONTROLE: sessao viva sem a tela NAO religa (licao do job a9733bb5)",
      t_v["relogin"] == 0, t_v)
check("CONTROLE: e nem tenta a tela uma segunda vez", t_v["ensure"] == 1, t_v)
check("CONTROLE: o estagio continua sendo o de sempre",
      (res_v.captured or {}).get("stage") == "inadimplentes_nao_localizado", res_v.captured)

# --- morreu, religou, e mesmo assim nao chegou ---------------------------
res_x, ev_x, t_x = _rodar_sweep(chega_na_tela=[False, False], morta=True)
check("morta e nao voltou: religou UMA vez so (nunca laco)", t_x["relogin"] == 1, t_x)
check("morta e nao voltou: devolve needs_human", res_x.status == "needs_human", res_x)
check("com o estagio REAL (sessao caiu), nao 'nao localizei a tela'",
      (res_x.captured or {}).get("stage") == "sessao_caiu_no_portal", res_x.captured)
check("e a mensagem fala em sessao, nao em leitura de lista",
      "sessao" in res_x.message.lower() and "lista de parcelas" not in res_x.message.lower(),
      res_x.message)

# --- morreu e o proprio relogin falhou -----------------------------------
res_r, ev_r, t_r = _rodar_sweep(chega_na_tela=[False], morta=True, relogin_ok=False)
check("relogin que falha nao e tentado de novo", t_r["relogin"] == 1, t_r)
check("e nao gasta uma segunda entrada no portal", t_r["ensure"] == 1, t_r)
check("a evidencia diz que o relogin falhou",
      ev_r.get("relogin_por_sessao_morta") is False, ev_r.get("relogin_por_sessao_morta"))

# --- a porta velha (token vencido pelo relogio) continua funcionando ------
_src_sweep = inspect.getsource(AZ.cobranca_sweep)
check("o gatilho antigo (token vencido) continua no sweep",
      'tok_before.get("expired") is True' in _src_sweep)


# ==========================================================================
print("\n[3] Cada estagio tem a SUA frase -- o rotulo nao pode mentir")
# ==========================================================================

MAPA = BC.O_QUE_HOUVE_POR_ESTAGIO
check("os tres estagios antigos continuam cobertos",
      all(k in MAPA for k in ("lista_nao_lida", "sem_linhas_extraiveis",
                              "inadimplentes_nao_localizado")), list(MAPA))
check("e o estagio novo (sessao caiu) tambem", "sessao_caiu_no_portal" in MAPA, list(MAPA))
check("NENHUMA frase se repete -- era esse o defeito de 18/08",
      len(set(MAPA.values())) == len(MAPA), MAPA)
check("nenhuma frase e a frase antiga que mandou o Founder para o lugar errado",
      all(v != "nao consegui ler a lista de parcelas" for v in MAPA.values()), MAPA)
check("a frase de 'nem cheguei na tela' NAO fala em ler tabela/lista",
      "ler" not in MAPA["inadimplentes_nao_localizado"].lower(),
      MAPA["inadimplentes_nao_localizado"])
check("a frase de sessao caida fala em sessao/login",
      any(p in MAPA["sessao_caiu_no_portal"].lower() for p in ("sessão", "sessao", "login")),
      MAPA["sessao_caiu_no_portal"])
check("as frases sao para humano de corretora (sem jargao de codigo)",
      not any(t in " ".join(MAPA.values()).lower()
              for t in ("stage", "idp", "token", "parser", "dom", "http")), MAPA)

_src_exec = inspect.getsource(BC.execute_billing_collection_routine)
check("o aviso ao grupo consulta o mapa, nao uma frase fixa",
      "O_QUE_HOUVE_POR_ESTAGIO" in _src_exec)
check("e a frase unica sumiu do arquivo",
      '"nao consegui ler a lista de parcelas"' not in inspect.getsource(BC))


def _frase(estagio):
    return MAPA.get(estagio)


check("CONTROLE: estagio desconhecido nao produz aviso nenhum",
      _frase("boletos_nao_baixados") is None and _frase("") is None)


# ==========================================================================
print("\n[4] O boleto entregue fica registrado -- e a falha de registro APARECE")
# ==========================================================================

check("a decisao de deduplicar mora num lugar so, com nome",
      callable(getattr(BC, "dedup_de_envio_ativa", None)))
check("modo live deduplica", BC.dedup_de_envio_ativa("live", env={}) is True)
check("modo approval deduplica", BC.dedup_de_envio_ativa("approval", env={}) is True)
check("modo teste NAO deduplica por padrao (nota 88, 17/08/2026)",
      BC.dedup_de_envio_ativa("test", env={}) is False)
check("CONTROLE: mas o modo teste pode deduplicar quando o Founder ligar",
      BC.dedup_de_envio_ativa("test", env={BC.FLAG_DEDUP_TESTE: "1"}) is True)


class ConsultaDeMentira:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self._f = banco, tabela, []

    def select(self, *_a, **_k):
        return self

    def eq(self, coluna, valor):
        self._f.append((coluna, valor))
        return self

    def upsert(self, linha, on_conflict=""):
        self.banco.upserts.append({"tabela": self.tabela, "linha": linha, "on_conflict": on_conflict})
        if self.tabela in self.banco.quebradas:
            self._erro = True
        else:
            self.banco.linhas.setdefault(self.tabela, []).append(linha)
        return self

    def execute(self):
        if self.tabela in self.banco.quebradas:
            raise RuntimeError("banco fora do ar")
        linhas = self.banco.linhas.get(self.tabela, [])
        for coluna, valor in self._f:
            linhas = [l for l in linhas if str(l.get(coluna)) == str(valor)]
        return types.SimpleNamespace(data=linhas)


class BancoDeMentira:
    def __init__(self, linhas=None, quebradas=()):
        self.linhas = dict(linhas or {})
        self.quebradas = set(quebradas)
        self.upserts = []

    def table(self, nome):
        return ConsultaDeMentira(self, nome)


class WhatsappDeMentira:
    def __init__(self):
        self.textos, self.docs = [], []

    def send_message(self, numero, texto, _integ):
        self.textos.append((numero, texto))
        return True

    def send_document(self, numero, url, nome, _integ):
        self.docs.append((numero, url, nome))
        return True


def _entregar(*, banco, send_mode="test", env=None, itens=None):
    """Roda o caminho de entrega de verdade, com o banco e o WhatsApp de mentira."""
    zap = WhatsappDeMentira()
    sys.modules["app.services.whatsapp_service"] = types.SimpleNamespace(
        get_whatsapp_service=lambda: zap)
    original = {n: getattr(BC, n) for n in (
        "_find_whatsapp_integration", "_signed_boleto_url",
        "_esperar_o_governador", "_registrar_no_governador")}
    BC._find_whatsapp_integration = lambda client, company_id: {"id": "wa1"}
    BC._signed_boleto_url = lambda client, path: ("https://x/" + str(path)) if path else ""

    async def _liberado(company_id, orcamento, para_numero_de_teste=False):
        return True, "ok", 0.0

    async def _registra(company_id, numero, item, cfg):
        return None

    BC._esperar_o_governador = _liberado
    BC._registrar_no_governador = _registra
    itens = itens if itens is not None else [
        {"recibo": "111", "cliente_nome": "ANA", "vencimento": "01/08/2026", "portal": "hdi_corretor"},
        {"recibo": "222", "cliente_nome": "BENTO", "vencimento": "02/08/2026", "portal": "hdi_corretor"},
    ]
    boletos = [{"recibo": "111", "ok": True, "storage_path": "b/111.pdf"},
               {"recibo": "222", "ok": True, "storage_path": "b/222.pdf"}]
    cfg = BC.normalize_billing_config({"send_mode": send_mode, "test_number": "5547999997463"})
    blockers: list = []
    velho = dict(os.environ)
    try:
        os.environ.pop(BC.FLAG_DEDUP_TESTE, None)
        os.environ.update(env or {})
        enviados = asyncio.run(BC._send_test_messages(
            banco, {"company_id": "resulta", "delivery": {}}, itens, boletos, cfg, blockers))
    finally:
        os.environ.clear()
        os.environ.update(velho)
        for nome, valor in original.items():
            setattr(BC, nome, valor)
    return enviados, blockers, zap


# --- hoje (19/08), modo teste: nada muda. A demonstracao do Founder roda. --
banco = BancoDeMentira()
enviados, blockers, zap = _entregar(banco=banco)
check("modo teste: os dois segurados sao entregues", len([e for e in enviados if e["ok"]]) == 2, enviados)
check("modo teste: o PDF vai junto", len(zap.docs) == 2, zap.docs)
check("modo teste: NADA e gravado em billing_sent_log (repetir amanha e o objetivo)",
      banco.upserts == [], banco.upserts)

# --- CONTROLE: o mesmo banco, o mesmo caminho, com a dedup LIGADA ---------
banco2 = BancoDeMentira(linhas={"billing_sent_log": [
    {"company_id": "resulta", "recibo": "111", "send_mode": "test"}]})
enviados2, blockers2, zap2 = _entregar(banco=banco2, env={BC.FLAG_DEDUP_TESTE: "1"})
check("CONTROLE: com a dedup ligada, quem ja recebeu NAO recebe de novo",
      [e["recibo"] for e in enviados2] == ["222"], enviados2)
check("CONTROLE: e quem recebeu agora entra na tabela",
      [u["linha"]["recibo"] for u in banco2.upserts] == ["222"], banco2.upserts)
check("CONTROLE: gravado com a chave do indice unico que existe no banco",
      banco2.upserts and banco2.upserts[0]["on_conflict"] == "company_id,recibo,send_mode",
      banco2.upserts)
check("CONTROLE: e o relatorio diz quantos foram pulados",
      any("ja enviados" in b for b in blockers2), blockers2)

# --- a falha de gravacao NAO pode ser engolida ---------------------------
banco3 = BancoDeMentira(quebradas=("billing_sent_log",))
enviados3, blockers3, zap3 = _entregar(banco=banco3, env={BC.FLAG_DEDUP_TESTE: "1"})
check("banco fora do ar: a entrega acontece assim mesmo",
      len([e for e in enviados3 if e["ok"]]) == 2, enviados3)
check("mas a falha de registro VIRA linha no relatorio (nao some)",
      any("registr" in b.lower() for b in blockers3), blockers3)
check("e o proprio envio carrega que nao foi registrado",
      all(e.get("registrado") is False for e in enviados3), enviados3)
# `from __future__ import annotations` deixa a anotacao como texto: comparar com
# o objeto `bool` daria falso por motivo errado.
check("`_record_sent` devolve se gravou -- nao devolve None e um `pass`",
      inspect.signature(BC._record_sent).return_annotation in (bool, "bool"),
      inspect.signature(BC._record_sent).return_annotation)
check("e a excecao vira log de erro, nao `except: pass`",
      "logger.error" in inspect.getsource(BC._record_sent), inspect.getsource(BC._record_sent))

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
