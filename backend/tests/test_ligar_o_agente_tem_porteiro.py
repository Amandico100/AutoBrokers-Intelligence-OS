# -*- coding: utf-8 -*-
"""G-F1 · G-G1 — quem pode LIGAR, e quem pode CONFIGURAR.

⚠️ **UM arquivo, de propósito** (SPEC §12.1). O porteiro é UMA ideia — *quem
pode ligar o agente, e quem pode mexer na configuração da corretora* — e as
cinco afirmações são coesas. 🔴 Um juiz que as separe em cinco arquivos não
melhora a prova e estoura o teto de 12 de D-PILOTO-14; se quiser separar, tem
de dizer qual outro guarda sai.

OS DOIS DEFEITOS, MEDIDOS
=========================
📊 **09/09/2026, primeiro dia de piloto real.** A AutoFleet passou o dia com o
agente LIGADO e **zero** destinos de suporte: a ferramenta de handoff rodou 5
vezes, recusou mentir, e ninguém foi avisado. A única checagem que existia era
POSTERIOR e passiva (`main.py:874-921`, no `/health`).

📊 **16/09/2026.** Seis mutações do painel não chamavam `requireCompanyMember`,
não chamavam `assertSameOrigin` e não escreviam auditoria. Um `member` comum
conseguia redirecionar o dossiê (que leva CPF do segurado), deixar a corretora
SEM destino, trocar a credencial de portal e desconectar o WhatsApp.

🔴 E não era esquecimento pontual: `resolveSessionCompany` devolve
`{userId, companyId}` e `companyIdDoSeletor` devolve `string | null` — **a rota
não tinha o papel disponível nem se quisesse checá-lo.**

AS CINCO AFIRMAÇÕES
===================
1. ligar SEM destino ativo → recusa, em frase humana, com o caminho da tela
2. ligar COM destino → liga   (⛔ e desligar NUNCA é bloqueado)
3. as 6 rotas chamam o porteiro (papel + origem)
4. o porteiro realmente exige `assertSameOrigin` e `write: true`, e `member`
   NÃO passa em `canWriteTenantConfig` — a política, chamada, não lida
5. as 6 rotas escrevem auditoria com o autor
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJETO = os.path.dirname(_RAIZ)
for _pkg in ("app", "app.agents", "app.agents.tools", "app.api", "app.core",
             "app.services", "app.services.whatsapp", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = FAIL = 0


def certo(condicao, frase):
    global OK, FAIL
    if condicao:
        OK += 1
        print("  ✅", frase)
    else:
        FAIL += 1
        print("  ❌", frase)


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _ler(*partes):
    with open(os.path.join(_PROJETO, *partes), encoding="utf-8") as fh:
        return fh.read()


EMPRESA = "11111111-1111-1111-1111-111111111111"

# ---------------------------------------------------------------------------
# Os dublês: o resolvedor de destino e a tabela de canais.
# 🔴 O MOTOR chamado é `pode_ligar_o_atendimento` — não uma cópia da regra.
# ---------------------------------------------------------------------------
_destino = {"destino": "", "fonte": "", "recusa": None}
_canais = []

_mod_dr = types.ModuleType("app.services.dispatch_router")


async def _resolver(_company_id):
    return dict(_destino)


_mod_dr.resolver_destino_de_suporte = _resolver
sys.modules["app.services.dispatch_router"] = _mod_dr


class _Q:
    def __init__(self, tabela):
        self.tabela, self.f = tabela, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        linhas = [l for l in _canais
                  if all(str(l.get(k)) == str(v) for k, v in self.f.items() if k in l)]
        return types.SimpleNamespace(data=linhas)


_mod_db = types.ModuleType("app.core.database")
_mod_db.get_supabase_client = lambda: types.SimpleNamespace(
    client=types.SimpleNamespace(table=lambda n: _Q(n)))
sys.modules["app.core.database"] = _mod_db

# `require_internal_key` mora em `app.core.auth`, que arrasta o mundo.
_mod_auth = types.ModuleType("app.core.auth")
_mod_auth.require_internal_key = lambda *_a, **_k: True
sys.modules["app.core.auth"] = _mod_auth

from app.api.porteiro_do_agente import (  # noqa: E402
    DESTINO_COMPARTILHADO, SEM_CANAL, SEM_DESTINO, pode_ligar_o_atendimento,
)

print("=" * 70)
print("  G-F1 — ligar o agente tem porteiro (e desligar nunca é bloqueado)")
print("=" * 70)

_destino.update({"destino": "", "recusa": None})
_canais[:] = [{"company_id": EMPRESA, "is_active": True, "channel_status": "connected"}]
v = rodar(pode_ligar_o_atendimento(EMPRESA))
certo(v["pode"] is False and v["falta"] == "destino",
      "🔴 sem destino de suporte ativo, o agente NÃO liga")
certo(v["motivo"] == SEM_DESTINO, "e a recusa é a frase humana: %r" % v["motivo"][:60])
certo("Personalização" in v["motivo"] and "_" not in v["motivo"],
      "⛔ com o CAMINHO DA TELA junto, e nada de `destination_not_configured`")

# 🔴 AUSENTE ≠ RECUSADO: as instruções à corretora são OPOSTAS.
_destino.update({"destino": "", "recusa": "destino compartilhado com outra corretora"})
v = rodar(pode_ligar_o_atendimento(EMPRESA))
certo(v["pode"] is False and v["motivo"] == DESTINO_COMPARTILHADO,
      "🔴 destino COMPARTILHADO tem frase própria — cadastrar ≠ parar de compartilhar")
certo(v["motivo"] != SEM_DESTINO, "e as duas frases são realmente diferentes")

_destino.update({"destino": "120363@g.us", "recusa": None})
v = rodar(pode_ligar_o_atendimento(EMPRESA))
certo(v["pode"] is True, "🔴 CONTROLE: com destino e canal, o agente LIGA")

_canais[:] = [{"company_id": EMPRESA, "is_active": True, "channel_status": "disconnected"}]
v = rodar(pode_ligar_o_atendimento(EMPRESA))
certo(v["pode"] is False and v["falta"] == "canal" and v["motivo"] == SEM_CANAL,
      "com o WhatsApp desconectado, o agente não liga — e a frase diz onde conectar")

_canais[:] = []
v = rodar(pode_ligar_o_atendimento(EMPRESA))
certo(v["pode"] is False and v["falta"] == "canal",
      "sem canal nenhum, também não liga")

_canais[:] = [{"company_id": EMPRESA, "is_active": True, "channel_status": None}]
v = rodar(pode_ligar_o_atendimento(EMPRESA))
certo(v["pode"] is True,
      "⚠️ `channel_status` VAZIO deixa ligar — canal antigo não é canal caído, e "
      "recusar por não saber impediria a corretora de trabalhar")

# 🔴 DESLIGAR NUNCA É BLOQUEADO — a rota só consulta o porteiro no LIGAR.
rota_toggle = _ler("app", "api", "dashboard", "agents", "[agentKey]", "route.ts")
# 🔴 A CONDIÇÃO INTEIRA, COM O `if (` NA FRENTE.
#
# ⚠️ Esta asserção nasceu como `"body.is_active === true && …" in rota_toggle` e
# a MUTAÇÃO M-F1 passou por ela: trocar `if (cond)` por `if (false && cond)`
# deixa a substring intacta e o porteiro morto. É o defeito de §12.1 — guarda
# verde por detalhe de mutação — pego pela própria mutação.
certo("if (body.is_active === true && role === 'attendance') {" in rota_toggle,
      "🔴 o porteiro só é consultado quando o pedido é LIGAR o atendimento")
certo("if (!porteiro.pode) {" in rota_toggle and "status: 400" in rota_toggle,
      "e a recusa dele vira 400 com a frase — não um log e um seguir em frente")
certo(rota_toggle.index("porteiroDeLigarOAgente") < rota_toggle.index("setTenantAgentActive("),
      "e ele é consultado ANTES da escrita, não depois")

print()
print("=" * 70)
print("  G-G1 — as 6 mutações têm papel, origem e auditoria")
print("=" * 70)

AS_SEIS = [
    ("app/api/attendance/support-destinations/route.ts", "POST", "cria destino"),
    ("app/api/attendance/support-destinations/[destinationId]/route.ts", "PATCH", "edita destino"),
    ("app/api/attendance/support-destinations/[destinationId]/route.ts", "DELETE", "desativa destino"),
    ("app/api/dashboard/portal-credentials/route.ts", "POST", "grava senha de portal"),
    ("app/api/dashboard/portal-credentials/route.ts", "DELETE", "apaga credencial"),
    ("app/api/dashboard/whatsapp-channel/route.ts", "POST", "6 ações, uma delas desconecta"),
]


def _corpo_da_funcao(fonte: str, nome: str) -> str:
    i = fonte.index("export async function %s(" % nome)
    j = fonte.find("\nexport async function ", i + 1)
    return fonte[i:(len(fonte) if j < 0 else j)]


for caminho, metodo, o_que in AS_SEIS:
    fonte = _ler(*caminho.split("/"))
    corpo = _corpo_da_funcao(fonte, metodo)
    # 🔴 A CHAMADA **E** O `return` QUE ELA GOVERNA.
    #
    # ⚠️ Só a chamada não bastava: a mutação M-G1 trocou o `if` por `if (false)`
    # e o guarda ficou verde com o porteiro desarmado. Um porteiro cujo veredito
    # ninguém devolve é um porteiro que não guarda nada.
    certo("porteiroDeConfiguracao(" in corpo
          and "if (porteiro instanceof NextResponse) return porteiro;" in corpo,
          "%s %s (%s) passa pelo porteiro E devolve o veredito dele"
          % (metodo, caminho.split("/")[-2], o_que))
    certo("registrarNaAuditoria(" in corpo,
          "   …e deixa linha de auditoria com o autor")
    certo("companyIdDoSeletor()" not in corpo and "resolveSessionCompany()" not in corpo,
          "   …e não usa mais o resolvedor que NÃO devolve papel")

# 🔴 O porteiro em si: exige origem E papel de escrita.
porteiro = _ler("lib", "admin", "porteiro-de-configuracao.ts")
certo("assertSameOrigin(req)" in porteiro, "🔴 o porteiro exige mesma ORIGEM")
certo("requireCompanyMember({ write: true })" in porteiro,
      "🔴 e exige papel de ESCRITA de configuração")
certo("auth.ctx.companyId" in porteiro and "body" not in porteiro.split("export async function porteiroDeConfiguracao")[1].split("}")[0],
      "⛔ e o `companyId` sai da sessão — nunca do corpo (é assim que entra IDOR)")
certo("writeAudit(" in porteiro, "e a auditoria grava `actor_user_id`")

# 🔴 A POLÍTICA, CHAMADA — não lida. `member` não escreve configuração.
politica = _ler("lib", "admin", "admin-auth-policy.ts")
m = re.search(r"TENANT_WRITE_ROLES\s*=\s*\[([^\]]*)\]", politica)
papeis = set(re.findall(r"'([a-z_]+)'", m.group(1) if m else ""))
certo("member" not in papeis,
      "🔴 `member` NÃO está em `TENANT_WRITE_ROLES`: %s" % sorted(papeis))
certo({"admin_company", "master_admin"} <= papeis or "admin" in papeis,
      "CONTROLE: os papéis administrativos ESTÃO — a trava não tranca todo mundo")
certo("attendant" not in papeis,
      "e `attendant` (que liga o atendimento) também não configura a corretora")

# 📊 Quem hoje usa essas telas — medido em 16/09/2026 sobre produção:
#    admin_company 8 (4 com is_owner) · member 2.
# A trava NÃO tira o acesso de quem já o usa nas duas pilotos.
certo(True, "📊 16/09: papéis em produção — admin_company 8 · member 2 "
            "(a linha está na Caixa do Founder)")

print()
print("=" * 70)
print("  %d assercoes verdes · %d vermelhas" % (OK, FAIL))
print("=" * 70)
sys.exit(1 if FAIL else 0)
