# -*- coding: utf-8 -*-
"""SPEC-048 - Isolamento real entre corretoras + variaveis vivas + Equipe.

Cobre: requireCompanyMember honra a empresa ATIVA com papel do VINCULO (era o
seam que fazia os dados de uma corretora vazarem na outra), /api/user/profile
mostra a empresa ativa, formulario do agente edita o valor CRU (variaveis
preservadas) com preview renderizado separado, equipe listada por vinculos com
gestao completa no dashboard (add/edit/remove so admin; dono protegido).
Standalone (source checks, sem pytest).
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


def _src(rel):
    return (WEB / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
print("\n[1] Seam unico - requireCompanyMember multi-empresa")

_auth = _src("lib/admin/admin-auth.ts")
check("honra s.activeCompanyId", "s.activeCompanyId" in _auth)
check("valida vinculo em company_members por request", "company_members" in _auth)
check("papel/is_owner vem DO VINCULO da empresa ativa",
      "member.role" in _auth and "member.is_owner" in _auth)
check("sem vinculo na empresa ativa = 403",
      "no_membership_active_company" in _auth)
check("fallback primaria preservado (users_v2)", "tenantCompanyConsistent" in _auth)

_prof = _src("app/api/user/profile/route.ts")
check("perfil mostra o nome da empresa ATIVA", "activeCompanyName" in _prof)

# ---------------------------------------------------------------------------
print("\n[2] Variaveis vivas no agente")

_bp = _src("lib/admin/agent-blueprints-canonical.ts")
check("form recebe o valor CRU salvo (nao o renderizado)",
      "value: savedVars[v.key] ?? v.default" in _bp)
check("preview renderizado separado no payload", "preview: { ...eff.variables_used }" in _bp)

_cli = _src("app/dashboard/personalizacao/agentes/AgentConfigClient.tsx")
check("apresentacao usa o preview renderizado",
      "config.preview?.opening_message" in _cli)
check("dica de variaveis nos campos de abertura/encerramento",
      "{{attendant_name}}" in _cli and "{{company_name}}" in _cli)

# ---------------------------------------------------------------------------
print("\n[3] Equipe da corretora no dashboard")

_store = _src("lib/admin/tenant-overview-store.ts")
check("equipe listada pelos VINCULOS (company_members)",
      "from('company_members')" in _store.replace('"', "'"))
check("papel do vinculo, nao do usuario", "ROLE_LABEL[m.role]" in _store)

_team = _src("app/api/dashboard/team/route.ts")
check("POST adiciona pessoa (usuario novo ou vinculo)", "hashPassword" in _team and "upsert" in _team)
check("PATCH edita dados/papel/senha", "password_hash" in _team)
check("DELETE remove SO o vinculo", "company_members').delete" in _team.replace('"', "'"))
check("escritas exigem admin (write: true)", _team.count("write: true") >= 3)
check("nao remove a si mesmo", "auth.ctx.userId" in _team and "si mesmo" in _team)
check("dono protegido (nao remove/rebaixa)", "is_owner" in _team and "403" in _team)
check("GET expoe can_manage p/ esconder botoes de membro comum", "can_manage" in _team)

_tc = _src("app/dashboard/personalizacao/equipe/TeamClient.tsx")
check("clique no membro abre modal com dados", "openMember" in _tc and "modalOpen" in _tc)
check("adicionar pessoa com senha provisoria", "Adicionar pessoa" in _tc and "mudar123" in _tc)
check("membro comum nao gerencia", "canManage" in _tc)

# ---------------------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"RESULTADO: {PASS} ok, {FAIL} falhas")
for name, detail in FAILURES:
    print(f"  FALHOU: {name} {detail}")
sys.exit(1 if FAIL else 0)
