"""O Atendente alcança o portal de vidros — e continua sem a chave genérica.

Por que este teste existe
-------------------------
Durante quatro semanas a conclusão registrada foi: *"conflito canônico — a
SPEC-053 diz que atendimento externo não recebe ferramenta genérica; o caso de
ouro da SPEC-020 é vidros pelo Atendente. Precisa de decisão do Founder."*

📊 **Medido em 04/08/2026 (Supabase dcajcvlzcjbmyapmklil), não havia conflito.**
Havia um portão conferindo a chave errada — e mais duas travas que nenhuma
decisão humana resolveria, porque eram contradições do próprio registro:

    tenant.portal.execute      provider = NULL,  requires_connection = true
      -> PROVIDER_SLUGS.get("", []) == []  ->  needs_connection PARA SEMPRE.
         Não existe conexão que resolva. Não há tela onde clicar.

    operational.portal.assistance.*   requires_connection = true
      -> exigia linha em `portal_accounts` para um portal que não tem login:
         📊 portals.cred_kind = 'public' nos DOIS portais de vidros
            (15 portais de corretor são 'login_password' — esses continuam
             exigindo, e é certo que exijam)

    graph.py                   if "tenant.portal.execute" in _active
      -> exigia a chave GENÉRICA para soltar uma ferramenta ESPECÍFICA

A terceira é a que criou a discussão inteira. `portal_action` não é genérica:
jornada fixa, parâmetros montados no servidor a partir da InfoCap, `confirm`
cravado em False. Isso é o **corredor definido** que a própria SPEC-053 5.2
manda usar — *"corredores definidos; menor privilégio"*. E o corredor já tinha
chave própria, já ligada para o Atendente desde sempre:
`operational.portal.assistance.prepare`.

O que este teste protege — e o CONTROLE que importa
----------------------------------------------------
O guarda mais importante daqui é o **[4]**: ele falha se alguém "resolver o
conflito" ligando `tenant.portal.execute` para `attendance`. Essa seria a
correção errada — daria a um agente exposto a texto de estranho no WhatsApp a
chave de **todos** os portais, que é exatamente o que a 053 5.2 proíbe.

Cada guarda roda o resolver REAL contra um banco de mentira, e cada um tem um
caso de controle que **precisa reprovar**. Sem isso, um resolver que devolvesse
'active' para tudo passaria neste arquivo inteiro.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

FALHAS: list[str] = []

CHAVE_DO_CORREDOR = "operational.portal.assistance.prepare"
CHAVE_GENERICA = "tenant.portal.execute"

# Escopo real da linha do banco (📊 lido em 04/08/2026). Não pode ser `{}`: o
# resolver nega capability HIGH sem escopo declarado (SPEC-054 Bloco C).
ESCOPO_PREPARE = {
    "read": True, "write": False, "operations": ["read", "prepare"],
    "side_effect": False, "tenant_scoped": True, "max_calls_per_run": 5,
    "requires_approval_before_submit": True,
}


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_py(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


# --------------------------------------------------------------------------
# Um banco de mentira que responde como o de verdade. Assim o teste exercita o
# resolver REAL — não uma cópia da lógica dele, que é o erro clássico: a cópia
# concorda com o autor, nunca com a produção.
# --------------------------------------------------------------------------
class _Consulta:
    def __init__(self, linhas):
        self._linhas = list(linhas)

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        return _Consulta([l for l in self._linhas if l.get(campo) == valor])

    def in_(self, campo, valores):
        return _Consulta([l for l in self._linhas if l.get(campo) in set(valores)])

    def execute(self):
        return type("R", (), {"data": self._linhas})()


class _BancoDeMentira:
    def __init__(self, tabelas):
        self._tabelas = tabelas

    def table(self, nome):
        return _Consulta(self._tabelas.get(nome, []))


def _banco(*, capabilities, papel="attendance", contas_de_portal=(), conexoes=(),
           bindings=None, desligadas=()):
    """Monta o banco. `capabilities` é uma lista de dicts como no Supabase."""
    padrao = [
        {"capability_key": c["capability_key"], "agent_role": papel,
         "enabled": True, "scope": c.pop("_scope", ESCOPO_PREPARE)}
        for c in capabilities
    ]
    return _BancoDeMentira({
        "capability_bindings": bindings if bindings is not None else padrao,
        "capabilities": capabilities,
        "tenant_capability_entitlements": [
            {"company_id": "empresa-1", "capability_key": k, "enabled": False} for k in desligadas],
        "tenant_connections": list(conexoes),
        "portal_accounts": list(contas_de_portal),
    })


def _carregar_resolver():
    """Carrega o resolver REAL pelo caminho do arquivo.

    `import app.agents.capability_resolver` puxaria `app/agents/__init__.py`, que
    importa o grafo inteiro (langgraph), e `app.core.config` (pydantic_settings)
    — dependências de runtime que não existem na máquina de teste. O resolver em
    si não precisa de nenhuma das duas: `settings` só é consultado para tavily e
    docling, que não são providers de portal.

    Então o config vira um dublê e o resolver é carregado direto. O que roda aqui
    é a função de produção, byte a byte — não uma reescrita dela.
    """
    import importlib.util
    import types

    if "app.core.config" not in sys.modules:
        pacote = sys.modules.setdefault("app", types.ModuleType("app"))
        pacote.__path__ = [os.path.join(RAIZ, "backend", "app")]
        core = sys.modules.setdefault("app.core", types.ModuleType("app.core"))
        core.__path__ = [os.path.join(RAIZ, "backend", "app", "core")]
        config = types.ModuleType("app.core.config")
        config.settings = type("S", (), {"TAVILY_API_KEY": None, "DOCLING_SERVICE_URL": None})()
        sys.modules["app.core.config"] = config

    caminho = os.path.join(RAIZ, "backend", "app", "agents", "capability_resolver.py")
    spec = importlib.util.spec_from_file_location("_capability_resolver_real", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.resolve_active_capabilities


def _resolver(banco, papel="attendance"):
    return _carregar_resolver()(banco, "empresa-1", papel)


def _cap(chave, *, provider, requires_connection, risk="high", scope=None):
    d = {"capability_key": chave, "is_active": True, "owner": "operational",
         "requires_connection": requires_connection, "provider": provider, "risk": risk}
    if scope is not None:
        d["_scope"] = scope
    return d


# --------------------------------------------------------------------------

def teste_provider_nulo_e_uma_permissao_inalcancavel():
    print("\n[1] Provider nulo + exige conexão = permissão que nunca fica pronta")

    # É esta a combinação que ficou quatro semanas no banco. Nenhuma conexão
    # resolve, porque o mapa de slugs é consultado pelo NOME do provider.
    r = _resolver(_banco(
        capabilities=[_cap(CHAVE_GENERICA, provider=None, requires_connection=True)],
        papel="core",
        contas_de_portal=[{"company_id": "empresa-1", "portal_key": "x", "health": "unknown"}],
    ), papel="core")
    checar(r.get(CHAVE_GENERICA, {}).get("status") == "needs_connection",
           "com provider NULO, nem uma conta de portal saudável libera",
           f"status={r.get(CHAVE_GENERICA, {}).get('status')}")

    # CONTROLE: com o provider nomeado, a MESMA conta libera. Se este não
    # passar, o guarda de cima estaria medindo outra coisa.
    r2 = _resolver(_banco(
        capabilities=[_cap(CHAVE_GENERICA, provider="portal_worker", requires_connection=True)],
        papel="core",
        contas_de_portal=[{"company_id": "empresa-1", "portal_key": "x", "health": "unknown"}],
    ), papel="core")
    checar(r2.get(CHAVE_GENERICA, {}).get("status") == "active",
           "CONTROLE — com provider nomeado, a mesma conta libera",
           f"status={r2.get(CHAVE_GENERICA, {}).get('status')}")

    # E a migration nomeia o provider.
    mig = _ler("backend", "supabase", "migrations",
               "20260804_01_spec065_o_portal_de_vidros_e_publico.sql")
    checar("provider   = 'portal_worker'" in mig and CHAVE_GENERICA in mig,
           "a migration nomeia o provider da chave genérica")


def teste_portal_publico_nao_pode_exigir_credencial():
    print("\n[2] Portal público não exige conexão; portal com login continua exigindo")

    # A corretora nova: nenhuma conta de portal cadastrada. É o caso da
    # AutoFleet 📊 (0 linhas em portal_accounts em 04/08/2026) e de toda
    # corretora que entrar amanhã.
    sem_conta = dict(capabilities=[
        _cap(CHAVE_DO_CORREDOR, provider="portal_worker", requires_connection=False)],
        contas_de_portal=[])
    r = _resolver(_banco(**sem_conta))
    checar(r.get(CHAVE_DO_CORREDOR, {}).get("status") == "active",
           "corretora SEM conta de portal abre vidros (o portal é público)",
           f"status={r.get(CHAVE_DO_CORREDOR, {}).get('status')}")

    # CONTROLE 1 — o estado de ANTES da migration tem de reprovar. Se este
    # devolvesse 'active', o guarda de cima não estaria medindo nada.
    r2 = _resolver(_banco(capabilities=[
        _cap(CHAVE_DO_CORREDOR, provider="portal_worker", requires_connection=True)],
        contas_de_portal=[]))
    checar(r2.get(CHAVE_DO_CORREDOR, {}).get("status") == "needs_connection",
           "CONTROLE — exigindo conexão, a mesma corretora era barrada",
           f"status={r2.get(CHAVE_DO_CORREDOR, {}).get('status')}")

    # CONTROLE 2 — o que NÃO pode ter sido afrouxado junto. Cobrança e apólice
    # acontecem em portal de corretor: 📊 15 portais, todos login_password.
    # Se alguém "simplificar" tirando a exigência de todos, este reprova.
    r3 = _resolver(_banco(capabilities=[
        _cap("operational.portal.billing.read", provider="portal_worker", requires_connection=True)],
        contas_de_portal=[]))
    checar(r3.get("operational.portal.billing.read", {}).get("status") == "needs_connection",
           "CONTROLE — cobrança (portal COM login) continua exigindo conexão",
           f"status={r3.get('operational.portal.billing.read', {}).get('status')}")

    mig = _ler("backend", "supabase", "migrations",
               "20260804_01_spec065_o_portal_de_vidros_e_publico.sql")
    # Só o SQL EXECUTÁVEL. A primeira versão deste guarda leu o arquivo inteiro
    # e reprovou por causa do cabeçalho — o VERIFY cita billing.read de
    # propósito, para dizer que ele NÃO deve mudar. Um detector que não separa
    # comentário de comando acusa justamente a documentação de estar certa.
    comandos = "\n".join(l for l in mig.split("\n") if not l.lstrip().startswith("--"))
    checar("requires_connection = false" in comandos, "a migration desobriga a conexão")
    checar("billing" not in comandos and "policy.read" not in comandos,
           "a migration NÃO mexe em cobrança nem em apólice",
           "afrouxar as duas junto abriria portal de corretor sem credencial")


def teste_o_portao_confere_a_chave_do_corredor():
    print("\n[3] O portão do portal_action aceita a chave do CORREDOR")
    graph = _sem_comentario_py(_ler("backend", "app", "agents", "graph.py"))

    trecho = ""
    for linha in graph.split("\n"):
        if "PortalActionTool" in linha:
            break
        if "_active" in linha and "portal" in linha.lower():
            trecho = linha
    # (o `if` que precede a anexação da tool)
    janela = graph.split("PortalActionTool", 1)[0][-400:]

    checar(CHAVE_DO_CORREDOR in janela,
           "o portão conhece operational.portal.assistance.prepare",
           "sem ela o Atendente nunca recebe a ferramenta — era a trava real")
    checar(CHAVE_GENERICA in janela,
           "o portão continua aceitando a chave genérica",
           "core e auxiliary dependem dela; trocar em vez de somar seria regressão")
    checar(re.search(r"_active\s*&\s*\{", janela) is not None,
           "as duas chaves são alternativas (basta UMA)",
           f"janela={janela[-160:].strip()[:150]}")


def teste_a_chave_generica_continua_negada_ao_atendente():
    print("\n[4] CONTROLE DA SPEC — o Atendente NÃO ganha a chave genérica")
    print("     (este é o guarda que reprova a correção errada)")

    # A SPEC-053 5.2, literal: "corredores definidos; menor privilégio; sem
    # ferramentas genéricas". `portal.execute` — entre em qualquer portal e
    # faça qualquer coisa — é a ferramenta genérica. Ela fica fora.
    caps = [_cap(CHAVE_GENERICA, provider="portal_worker", requires_connection=True)]
    banco = _banco(
        capabilities=caps,
        contas_de_portal=[{"company_id": "empresa-1", "portal_key": "x", "health": "unknown"}],
        bindings=[{"capability_key": CHAVE_GENERICA, "agent_role": "attendance",
                   "enabled": False, "scope": {"disabled_reason": "SPEC-053 5.2"}}],
    )
    r = _resolver(banco)
    checar(CHAVE_GENERICA not in r,
           "binding desligado NÃO chega ao runtime",
           f"resolvido={r}")

    # Nenhuma migration do repositório pode religar isso por baixo.
    pasta = os.path.join(RAIZ, "backend", "supabase", "migrations")
    religam: list[str] = []
    for arq in sorted(os.listdir(pasta)):
        if not arq.endswith(".sql"):
            continue
        sql = open(os.path.join(pasta, arq), encoding="utf-8").read()
        corpo = "\n".join(l for l in sql.split("\n") if not l.lstrip().startswith("--"))
        if CHAVE_GENERICA not in corpo or "attendance" not in corpo:
            continue
        # 20260706_06 é a migration de origem (ligava para os três papéis) e a
        # SPEC-054 Bloco C a corrigiu depois. O que não pode é NOVA migration
        # religando — por isso a janela é por data.
        if arq >= "20260802" and re.search(r"enabled\s*=\s*true|,\s*true\s*\)", corpo):
            religam.append(arq)
    checar(not religam,
           "nenhuma migration nova religa a chave genérica para o Atendente",
           f"{religam}")


def teste_o_banco_concorda():
    print("\n[5] O banco concorda com o código (pulado sem credencial)")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        print("      (sem credencial — caso pulado)")
        return
    try:
        import httpx
    except ImportError:
        print("      (sem httpx — caso pulado)")
        return

    def rest(caminho, **params):
        r = httpx.get(f"{url.rstrip('/')}/rest/v1/{caminho}", params=params,
                      headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=20)
        return r.json() if r.status_code == 200 else None

    caps = rest("capabilities", select="capability_key,provider,requires_connection",
                capability_key="like.*portal*") or []
    for c in caps:
        checar(c.get("provider") is not None,
               f"{c['capability_key']} tem provider",
               "provider nulo + exige conexão = inalcançável para sempre")
    for c in caps:
        if c["capability_key"].startswith("operational.portal.assistance."):
            checar(c.get("requires_connection") is False,
                   f"{c['capability_key']} não exige conexão (portal público)")
        if c["capability_key"] in ("operational.portal.billing.read",
                                   "operational.portal.policy.read"):
            checar(c.get("requires_connection") is True,
                   f"{c['capability_key']} CONTINUA exigindo conexão (portal com login)")

    binds = rest("capability_bindings", select="capability_key,agent_role,enabled",
                 capability_key=f"eq.{CHAVE_GENERICA}", agent_role="eq.attendance") or []
    if binds:
        checar(binds[0].get("enabled") is False,
               "no banco, a chave genérica segue negada ao Atendente (SPEC-053 5.2)")

    # A regra de onde ela veio: portal público não pede credencial.
    portais = rest("portals", select="key,category,cred_kind") or []
    vidros = [p for p in portais if p.get("category") == "vidros"]
    checar(bool(vidros) and all(p.get("cred_kind") == "public" for p in vidros),
           "os portais de vidros continuam públicos",
           "se um passar a pedir login, a regra do caso [2] muda e este teste avisa")


def main() -> int:
    print("=" * 70)
    print("O ATENDENTE ALCANCA O PORTAL DE VIDROS — SEM A CHAVE GENERICA")
    print("=" * 70)
    for teste in (teste_provider_nulo_e_uma_permissao_inalcancavel,
                  teste_portal_publico_nao_pode_exigir_credencial,
                  teste_o_portao_confere_a_chave_do_corredor,
                  teste_a_chave_generica_continua_negada_ao_atendente,
                  teste_o_banco_concorda):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CORREDOR ESTA ABERTO E A PORTA GENERICA CONTINUA FECHADA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
