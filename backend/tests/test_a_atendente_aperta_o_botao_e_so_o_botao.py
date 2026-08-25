# -*- coding: utf-8 -*-
"""A atendente aperta o botão — e só o botão. SPEC-093, BLOCO A.

📊 **O problema, medido em 25/08/2026:**

```
company_members ativos:   8 admin_company  +  2 member
o botão exige:            owner|admin|admin_company|master_admin
member ∉ lista            →  403 admin_required
```

⚠️ E dar `admin_company` às duas resolveria o botão **e abriria a configuração
inteira** — prompt do agente, integrações, billing.

✅ **E não precisa de migration:** 📊 `company_members.role` é `character varying`
**sem CHECK e sem enum** — as únicas constraints são as duas FK, a PK e a UNIQUE
`(user_id, company_id)`. Criar `attendant` é dado, não schema.

## 🔴 POR QUE ESTE ARQUIVO EXISTE, E NÃO SÓ O `.mjs`

📊 Medido: `scripts/admin-auth-policy.test.mjs` existe desde a TA2-B e
**ninguém o executa** — não está no `gate.yml`, não está no `package.json`, e
nenhum pytest o chama. 📊 `grep -rn "admin-auth-policy.test" .github/ package.json
backend/tests/` → **vazio**.

> **Um teste que ninguém roda não guarda nada.** O `gate.yml` roda
> `python -m pytest tests/ -q` (linha 138) — então é daqui que ele passa a rodar.

⚠️ Este guarda **lança processo**, e por isso pertence aos 87 seriais da bateria
(protocolo §bateria). ⛔ E ele **nunca** pode virar `xfail`: quarentena é para
asserção vencida, nunca para quem tem filho.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent.parent
TESTE_MJS = RAIZ / "scripts" / "admin-auth-policy.test.mjs"
POLITICA = RAIZ / "lib" / "admin" / "admin-auth-policy.ts"
ROTA = RAIZ / "app" / "api" / "dashboard" / "agents" / "[agentKey]" / "route.ts"

_NODE = shutil.which("node")
_sem_node = pytest.mark.skipif(_NODE is None, reason="node ausente neste ambiente")


def _rodar_mjs(caminho: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_NODE, str(caminho)], cwd=str(RAIZ), capture_output=True, text=True,
        timeout=90, encoding="utf-8", errors="replace",
        env={**os.environ, "NODE_OPTIONS": ""},
    )


# ---------------------------------------------------------------------------
# 1. O GATE DO BLOCO A — e ele passa a RODAR
# ---------------------------------------------------------------------------

@_sem_node
def test_a_politica_de_autorizacao_passa():
    """Os cinco gates do BLOCO A, executados de verdade."""
    r = _rodar_mjs(TESTE_MJS)
    assert r.returncode == 0, (
        "a política de autorização reprovou:\n"
        + (r.stdout or "")[-2500:] + "\n" + (r.stderr or "")[-800:])
    assert "0 falharam" in (r.stdout or ""), (r.stdout or "")[-600:]


@_sem_node
def test_CONTROLE_o_teste_de_politica_CONSEGUE_reprovar():
    """§9.3 — prove que o executor acima enxerga vermelho.

    🔴 Sem esta linha, um `node` que saísse 0 por qualquer motivo (arquivo
    vazio, import silencioso, script trocado) faria o guarda acima passar
    para sempre. Ele é o executor: se ele não vê falha, ele não guarda.
    """
    falso = RAIZ / "scripts" / "_controle_politica_falha.test.mjs"
    falso.write_text(
        "let pass=0,fail=0;\n"
        "function assert(n,c){if(c){pass++}else{fail++;console.log('  x '+n)}}\n"
        "assert('esta asserção é falsa DE PROPÓSITO', false);\n"
        "console.log(`\\n== Resumo: ${pass} passaram, ${fail} falharam ==`);\n"
        "process.exit(fail ? 1 : 0);\n",
        encoding="utf-8")
    try:
        r = _rodar_mjs(falso)
        assert r.returncode != 0, (
            "o executor devolveu 0 para um teste que FALHA — ele não consegue "
            "ver vermelho, e portanto não guarda nada")
        assert "1 falharam" in (r.stdout or "")
    finally:
        falso.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 2. GATE ③ — a corretora vem da SESSÃO, nunca do corpo
# ---------------------------------------------------------------------------

def test_GATE_3_a_corretora_vem_da_SESSAO_e_nao_do_corpo():
    """⛔ *"`attendant` de OUTRA corretora tenta alternar → 403"*.

    🔴 A prova é estrutural, e é mais forte que um teste de caso: **não existe
    campo de empresa para forjar.** A rota resolve a corretora em
    `requireCompanyMember`, que a lê da sessão e confere a associação ativa —
    e o `setTenantAgentActive` recebe `auth.ctx.companyId`.

    ⚠️ Se um dia alguém passar `body.company_id` adiante, este guarda quebra.
    """
    fonte = ROTA.read_text(encoding="utf-8")
    assert "auth.ctx.companyId" in fonte, (
        "a rota parou de usar a corretora da SESSÃO")
    for proibido in ("body.company_id", "body.companyId",
                     "params.company_id", "searchParams.get('company"):
        assert proibido not in fonte, (
            f"a rota passou a aceitar `{proibido}` — a corretora deixou de vir "
            "da sessão, e um attendant alcança o agente de outra")


def test_a_decisao_e_PURA_e_mora_na_politica():
    """🔴 A decisão tem de ser testável sem sessão, cookie e banco.

    Um gate que precise dos três é um gate que ninguém roda — e foi assim que
    `admin-auth-policy.test.mjs` ficou sem executor por semanas.
    """
    politica = POLITICA.read_text(encoding="utf-8")
    assert "export function decidirPatchDeAgente" in politica
    assert "export function canToggleAttendanceAgent" in politica
    assert "ATTENDANCE_TOGGLE_ROLES" in politica

    fonte = ROTA.read_text(encoding="utf-8")
    assert "decidirPatchDeAgente(" in fonte, (
        "a rota parou de usar a decisão pura — a lógica voltou para dentro do "
        "handler, onde o gate não a alcança")


def test_o_papel_novo_NAO_herda_escrita_de_configuracao():
    """⚠️ A separação é o ponto: se `attendant` entrasse em `TENANT_WRITE_ROLES`,
    dar o papel a alguém daria o prompt do agente junto."""
    politica = POLITICA.read_text(encoding="utf-8")
    i_write = politica.index("export const TENANT_WRITE_ROLES")
    linha = politica[i_write:politica.index("\n", i_write)]
    assert "attendant" not in linha, (
        "`attendant` entrou em TENANT_WRITE_ROLES — o papel passou a abrir a "
        "configuração inteira, que é exatamente o que ele existe para evitar")
