# -*- coding: utf-8 -*-
"""O Sentinela responde pelo canal por onde a conversa entrou.

📊 O DEFEITO, medido em 18/08/2026 no acionamento real da Allianz residencial.

    01:51:33  Allianz manda a tela do reparo eletrico
    01:52:21  o Sentinela responde "1"  <- CERTO
              o transcript grava "respondi 1"
              o envio cai em integration=None e a excecao e engolida
    01:55:41  "O seu atendimento esta sendo encerrado por inatividade"

248 segundos. O painel dizia "respondi 1". A Allianz jurava que ninguem falou.
As duas coisas eram verdade.

## Por que `integration` era None

📊 A Resulta tem QUATRO conexoes de WhatsApp e UMA ativa: o Observador
(`ab-obs-04b5cdbc04-1`, `purpose='observer'`). E `observer` esta em
`PROPOSITOS_QUE_NUNCA_ENVIAM`.

A regra e boa e FICA. Ela existe porque o segurado nao pode receber mensagem
de um numero que a corretora pareou justamente para ficar calado.

📊 E religar conexao amanha NAO resolve: o dashboard pareia o WhatsApp da
corretora COMO observador. A conexao que voltar a ficar ativa sera observer de
novo, e o Sentinela continuaria mudo.

## A distincao que o conserto faz

  INICIATIVA PROPRIA   cobranca, relatorio, sugestao, alerta a frio
                       -> continua PROIBIDO pelo observador. Surpresa.

  RESPOSTA             o corredor ja mandou dezenas de mensagens para a URA
                       por este mesmo canal, no mesmo minuto. O Sentinela esta
                       terminando a frase de uma conversa que ja existe, com a
                       SEGURADORA -- que nao e segurado de ninguem.
                       -> responde por onde a conversa entrou.

METADE DESTE ARQUIVO E CONTROLE, porque o risco do conserto e afrouxar a
proibicao sem querer.
"""
from __future__ import annotations

import ast
import os
import sys

# O console do Windows e cp1252 e engasga com emoji. Reconfigurar a saida e
# melhor que tirar os emojis: eles marcam o que importa no relatorio.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


with open(os.path.join(RAIZ, "app/tasks/dispatch_watchdog.py"), encoding="utf-8") as fh:
    FONTE_WD = fh.read()
with open(os.path.join(RAIZ, "app/services/dispatch_router.py"), encoding="utf-8") as fh:
    FONTE_RT = fh.read()
with open(os.path.join(RAIZ, "app/api/webhook.py"), encoding="utf-8") as fh:
    FONTE_WH = fh.read()
with open(os.path.join(RAIZ, "app/services/integration_service.py"), encoding="utf-8") as fh:
    FONTE_IS = fh.read()

# Executa o resolvedor REAL, extraido do arquivo -- nao uma copia escrita aqui.
_ns: dict = {}
_i = FONTE_WD.index("def _canal_da_conversa(")
_j = FONTE_WD.index("async def _support_alert(")
exec("import logging\nlogger = logging.getLogger('t')\n"
     "from typing import Any, Dict\n" + FONTE_WD[_i:_j], _ns)  # noqa: S102
_canal_da_conversa = _ns["_canal_da_conversa"]

OBSERVADOR = {"id": "obs-1", "purpose": "observer", "provider": "evolution-go",
              "identifier": "ab-obs-04b5cdbc04-1", "is_active": True}


class _IntegFake:
    """O `integration_service`, o mínimo para exercitar o resolvedor."""

    def __init__(self, por_id=None, plataforma=None):
        self._por_id = por_id or {}
        self._plataforma = plataforma
        self.pediu_plataforma = False
        self.filtrou_por_empresa = None
        self.supabase = self

    # --- encadeamento do cliente Supabase ---
    def table(self, _n):
        self._filtros = {}
        return self

    def select(self, *_a):
        return self

    def eq(self, campo, valor):
        self._filtros[campo] = valor
        if campo == "company_id":
            self.filtrou_por_empresa = valor
        return self

    def limit(self, _n):
        return self

    def execute(self):
        ident = self._filtros.get("id")
        empresa = self._filtros.get("company_id")
        linha = self._por_id.get(ident)
        # 🔴 O filtro por empresa e obrigatorio (CLAUDE.md §7): o backend usa
        # service role, e RLS sozinha nao protege contra erro de filtro.
        if linha and empresa and linha.get("company_id") != empresa:
            linha = None
        return type("R", (), {"data": [linha] if linha else []})()

    def get_platform_whatsapp_integration(self, _cid):
        self.pediu_plataforma = True
        return self._plataforma


# `prepare_integration_for_runtime` decifra segredos; aqui devolve a linha.
sys.modules.setdefault(
    "app.services.whatsapp.integration_secrets",
    type("M", (), {"prepare_integration_for_runtime": staticmethod(lambda x: x)})())

# ==========================================================================
print("\n[1] Com o canal na sessao, ele responde por ele")
# ==========================================================================

CANAL = {**OBSERVADOR, "company_id": "resulta"}
integ = _IntegFake(por_id={"obs-1": CANAL}, plataforma=None)
achado = _canal_da_conversa(integ, "resulta", {"integration_id": "obs-1"})

check("acha o canal da conversa", achado is not None and achado.get("id") == "obs-1",
      "era exatamente aqui que devolvia None e a resposta certa se perdia")
check("e nem chega a pedir o canal de plataforma", integ.pediu_plataforma is False)
check("filtrou por company_id (CLAUDE.md §7)", integ.filtrou_por_empresa == "resulta")

# 🔴 CONTROLE de tenant: canal de OUTRA corretora nao pode ser devolvido.
integ2 = _IntegFake(por_id={"obs-1": {**OBSERVADOR, "company_id": "autofleet"}},
                    plataforma=None)
check("CONTROLE: canal de OUTRA corretora nao vaza",
      _canal_da_conversa(integ2, "resulta", {"integration_id": "obs-1"}) is None,
      "cross-tenant e P0")

# ==========================================================================
print("\n[2] CONTROLE -- sem canal na sessao, nada mudou")
# ==========================================================================
#
# Sem estas linhas, um resolvedor que devolvesse SEMPRE alguma coisa passaria
# no bloco [1] e teria quebrado o comportamento de todas as outras corretoras.

PLATAFORMA = {"id": "plat-9", "purpose": "attendance", "company_id": "amandus"}
integ3 = _IntegFake(por_id={}, plataforma=PLATAFORMA)
check("CONTROLE: sessao sem canal cai no caminho de sempre",
      _canal_da_conversa(integ3, "amandus", {}) == PLATAFORMA)
check("CONTROLE: e ele REALMENTE pediu o canal de plataforma",
      integ3.pediu_plataforma is True)

integ4 = _IntegFake(por_id={}, plataforma=None)
check("CONTROLE: sem nenhum dos dois, devolve None (nao inventa canal)",
      _canal_da_conversa(integ4, "amandus", {"integration_id": "nao-existe"}) is None)

integ5 = _IntegFake(por_id={}, plataforma=PLATAFORMA)
check("CONTROLE: id que nao existe cai no canal de plataforma, nao quebra",
      _canal_da_conversa(integ5, "amandus", {"integration_id": "fantasma"}) == PLATAFORMA)

# ==========================================================================
print("\n[3] 🔴 A PROIBICAO DO OBSERVADOR CONTINUA INTEIRA")
# ==========================================================================
#
# Este e o bloco que importa. O conserto vale para RESPOSTA. Iniciativa
# propria — cobranca, relatorio, sugestao — nao pode ter sido afrouxada.

check("`observer` continua em PROPOSITOS_QUE_NUNCA_ENVIAM",
      'PROPOSITOS_QUE_NUNCA_ENVIAM = frozenset({"observer"})' in FONTE_IS)
check("`pode_enviar` continua existindo e sendo a regra",
      "def pode_enviar" in FONTE_IS)
check("`get_platform_whatsapp_integration` continua chamando `pode_enviar`",
      "self.pode_enviar(integ)" in FONTE_IS)

# 🔴 O resolvedor novo NAO pode ter sido plugado em quem fala por iniciativa.
for arquivo, rotulo in (
    ("app/services/billing_collection.py", "a Cobranca"),
    ("app/services/weekly_report.py", "o relatorio semanal"),
    ("app/services/proactive_suggestions.py", "as sugestoes proativas"),
    ("app/services/platform_outbound.py", "o governador de saida"),
):
    caminho = os.path.join(RAIZ, arquivo)
    if not os.path.exists(caminho):
        continue
    with open(caminho, encoding="utf-8") as fh:
        conteudo = fh.read()
    check(f"{rotulo} NAO usa o canal da conversa",
          "_canal_da_conversa" not in conteudo,
          "iniciativa propria continua obedecendo a proibicao do observador")

# ==========================================================================
print("\n[4] O canal chega ate a sessao -- a corrente inteira")
# ==========================================================================


def grava_o_canal(fonte: str) -> bool:
    """Existe uma atribuicao real de `session["integration_id"]`?

    Le a arvore. Casar a string pegaria o comentario que explica o conserto —
    ja aconteceu sete vezes nesta SPEC.
    """
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Assign):
            continue
        for alvo in no.targets:
            if (isinstance(alvo, ast.Subscript)
                    and getattr(alvo.value, "id", "") == "session"
                    and getattr(getattr(alvo, "slice", None), "value", None) == "integration_id"):
                return True
    return False


check("o roteador GRAVA o canal na sessao", grava_o_canal(FONTE_RT))
_SEM = chr(10).join(["def f():", '    # session["integration_id"] = x', "    return 1"])
check("CONTROLE: o detector nao acha a gravacao num comentario",
      not grava_o_canal(_SEM))

arvore_rt = ast.parse(FONTE_RT)
rota = next(n for n in ast.walk(arvore_rt)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == "try_route_insurer_inbound")
check("o roteador ACEITA `integration_id`",
      "integration_id" in [a.arg for a in rota.args.kwonlyargs + rota.args.args])
check("e ele e opcional -- nenhum chamador antigo quebra",
      len(rota.args.kw_defaults) == len(rota.args.kwonlyargs))

check("o webhook PASSA o id da integracao do inbound",
      "integration_id=str((integration or {}).get(" in FONTE_WH)

check("e o Vigia usa o resolvedor novo, nao a chamada crua",
      "_canal_da_conversa(integrations, company_id, session)" in FONTE_WD)
# 🔴 A assercao anterior era `a chamada crua sumiu do arquivo` e estava ERRADA:
# ela AINDA existe, e deve existir -- e o fallback DENTRO de
# `_canal_da_conversa`. O que nao pode e ela estar no LACO do Vigia, que era
# de onde vinha o `None`. A diferenca so aparece lendo a arvore.
def _chama_crua_dentro_de(fonte: str, funcao: str) -> bool:
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if no.name != funcao:
            continue
        for x in ast.walk(no):
            if (isinstance(x, ast.Call)
                    and getattr(x.func, "attr", "") == "get_platform_whatsapp_integration"):
                return True
    return False


check("CONTROLE: a chamada crua saiu do LACO do Vigia",
      not _chama_crua_dentro_de(FONTE_WD, "check_dispatch_watchdog"))
check("CONTROLE: mas ela CONTINUA no resolvedor, como fallback",
      _chama_crua_dentro_de(FONTE_WD, "_canal_da_conversa"),
      "sem fallback, corretora COM canal proprio perderia o dela")

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
