# -*- coding: utf-8 -*-
"""SPEC-047 - Multi-empresa (mesmo email em 2 corretoras) + WhatsApp por corretora.

Cobre: canal GO por corretora (resolucao via integrations, criacao via global
key, fallback env legado, HISTORY_SYNC no subscribe, desativacao de canais
antigos da mesma funcao), superficie unica de pareamento (modal sem escolha
falsa; Conectores aponta pro hub), sessao com empresa ativa validada por
company_members, endpoint de troca, seletor no TenantNav, migracao RLS+members.
Standalone (stubs, sem pytest).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _src(rel, base=None):
    return ((base or WEB) / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
print("\n[1] Backend - canal GO POR corretora")

_ch = _src("app/api/whatsapp_channel.py", ROOT)
check("resolucao por linha da corretora (integrations)", "_go_company_channel" in _ch)
check("criacao de instancia via EVOLUTION_GO_GLOBAL_KEY", "EVOLUTION_GO_GLOBAL_KEY" in _ch)
check("instancia nomeada por corretora (ab-<company>)", "_go_instance_name" in _ch)
check("token proprio por instancia (secrets)", "secrets.token_hex(16)" in _ch)
check("modo cofre no create (readMessages/alwaysOnline off)",
      '"readMessages": False' in _ch and '"ignoreGroups": True' in _ch)
# A lição é a mesma de sempre — HISTORY_SYNC precisa estar assinado, senão o
# Espelho não recebe o histórico do pareamento fresco. O que mudou em 06/08/2026
# foi ONDE ela se prova.
#
# Este check procurava a string literal neste arquivo. Ficou vencido quando a
# lista saiu daqui: quatro lugares montavam o corpo do `/instance/connect` e os
# quatro discordavam — este mandava 3 eventos, o orquestrador 4, o admin_atlas 3,
# e o reconector NENHUM. 📊 O reconector, mandando `{"immediate": True}`, fazia o
# Evolution Go gravar `Events="MESSAGE"` e `Webhook=""` por cima: três das quatro
# instâncias em produção estavam sem webhook e a captura das duas corretoras
# estava parada há 42 h e 67 h.
#
# Agora existe um corpo só, e o guarda cobre os QUATRO chamadores em vez de um.
# Manter a asserção antiga ensinaria a ignorar teste: ela ficaria vermelha por
# uma consolidação correta.
_sec = _src("app/services/whatsapp/channel_security.py", ROOT)
check("HISTORY_SYNC assinado (Espelho no pareamento fresco)",
      '"HISTORY_SYNC"' in _sec and "EVENTOS_DO_CANAL" in _sec)
check("o canal usa o corpo unico de connect (nao monta o seu)",
      "corpo_do_connect(webhook_url)" in _ch)
check("env de instancia unica virou fallback legado", "_go_env_fallback" in _ch)
check("uma funcao = um canal ativo (desativa antigos)",
      '"is_active": False}' in _ch.replace("'", '"') or '{"is_active": False}' in _ch)
check("QR resolve a instancia da corretora",
      "_go_resolve(company_id" in _ch or "_go_get(company_id" in _ch)
# SPEC-050: evoluiu de falha explicita para AUTO-CURA (delete+recria fantasma)
check("instancia existente sem registro = auto-cura (delete+recria)",
      "_go_find_by_name" in _ch and "instance/delete/" in _ch)

# ---------------------------------------------------------------------------
print("\n[2] Superficie unica de pareamento")

_modal = _src("components/vault/WhatsAppChannelModal.tsx")
check("modal sem escolha falsa GO x classico",
      "Evolution (clássico)" not in _modal and "setStep" not in _modal and "choose" not in _modal)
check("modal vai direto ao pareamento", "WhatsAppChannelCard" in _modal)
check("Meta segue anunciada como em preparacao", "Em preparação" in _modal)

_con = _src("app/dashboard/personalizacao/conectores/page.tsx")
check("Conectores: card WhatsApp aponta pro hub da corretora",
      "/dashboard/personalizacao/corretora/whatsapp" in _con)
check("Conectores: sem modal proprio de pareamento", "WhatsAppChannelModal" not in _con)

# ---------------------------------------------------------------------------
print("\n[3] Multi-empresa - sessao, troca e seletor")

_sess = _src("lib/iron-session.ts")
check("SessionData tem activeCompanyId", "activeCompanyId" in _sess)
_srv = _src("lib/auxiliaries/server.ts")
check("resolveSessionCompany honra empresa ativa", "session.activeCompanyId" in _srv)
check("empresa ativa validada contra company_members a cada request",
      "company_members" in _srv and "maybeSingle" in _srv)
_login = _src("app/api/auth/login/route.ts")
check("login reseta a empresa ativa", "activeCompanyId = null" in _login)
_api = _src("app/api/auth/companies/route.ts")
check("GET lista empresas do usuario", "company_members" in _api and "companies:" in _api)
check("POST troca so com vinculo ativo", "status', 'active'" in _api.replace('"', "'") and "403" in _api)
_nav = _src("components/layout/TenantNav.tsx")
check("TenantNav tem seletor de empresa (>1 vinculo)",
      "myCompanies.length > 1" in _nav and "switchCompany" in _nav)
check("troca recarrega o dashboard inteiro", "window.location.assign" in _nav)

# ---------------------------------------------------------------------------
print("\n[4] Migracao - RLS + company_members")

_mig = _src("supabase/migrations/20260721_01_spec047_rls_e_company_members.sql", ROOT)
for t in ("billing_sent_log", "ura_maps", "broker_insights", "playbook_overlays",
          "conversation_scorecards", "agent_activities"):
    check(f"RLS ligado em {t}", f"public.{t} ENABLE ROW LEVEL SECURITY" in _mig)
check("company_members com UNIQUE(user_id, company_id)",
      "UNIQUE (user_id, company_id)" in _mig)
check("seed exclui usuarios sinteticos de whatsapp", "@whatsapp.smith.ai" in _mig)
check("company_members com RLS", "company_members ENABLE ROW LEVEL SECURITY" in _mig)

# ---------------------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"RESULTADO: {PASS} ok, {FAIL} falhas")
for name, detail in FAILURES:
    print(f"  FALHOU: {name} {detail}")
sys.exit(1 if FAIL else 0)
