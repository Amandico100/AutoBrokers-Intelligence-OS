"""SPEC-061 — as colunas que o Control Plane lê existem de verdade.

Por que este arquivo existe
---------------------------
A Inbox lia `approval_requests.action_key`. A coluna real é `action_type` — eu
escrevi de memória. O leitor tolerante (`_ler`, que devolve `[]` quando a
consulta falha) engolia o erro: a caixa **nunca mostraria aprovação nenhuma**,
sem nada na tela indicando por quê.

Esse é o preço de um leitor que não derruba a tela: ele também não avisa. A
tolerância é certa — uma fonte fora do ar não pode zerar a caixa — mas ela
precisa de um teste do lado de fora, senão vira silêncio.

E `company_integrations`, que o Cockpit lia, **não existe**: a tabela é
`integrations`, e a coluna de estado é `channel_status`.

Como este teste funciona
------------------------
Ele extrai do código os pares `(tabela, colunas)` de cada `.table(...).select(...)`
e compara com o schema real, exportado abaixo. Sem banco, sem rede.

O schema é uma cópia — e uma cópia envelhece. Por isso ele vem com a data e a
instrução de como regerar: um teste que compara com uma cópia velha é pior que
nenhum, porque dá confiança falsa.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

# Consultado em 27/07/2026 no projeto `dcajcvlzcjbmyapmklil`. Para regerar:
#
#   select table_name, string_agg(column_name, ',' order by ordinal_position)
#     from information_schema.columns
#    where table_schema='public' and table_name in (...)
#    group by 1;
SCHEMA: dict[str, set[str]] = {
    "work_runs": set(
        "id company_id requester_user_id requester_agent_id parent_run_id "
        "correlation_id source_type source_id outcome_type outcome_title "
        "outcome_description status priority risk_level visibility "
        "owner_user_id runtime_kind workflow_key workflow_version thread_id "
        "graph_version input_payload input_fingerprint result_summary "
        "result_payload error_code error_message progress_percent "
        "current_step_key idempotency_key cost_budget_brl cost_actual_brl "
        "currency requested_at queued_at started_at paused_at finished_at "
        "cancel_requested_at cancelled_at next_attempt_at lease_owner "
        "lease_token lease_expires_at heartbeat_at created_at updated_at "
        "skill_release_id capability_pack_release_id".split()),
    "work_steps": set(
        "id work_run_id company_id step_key ordinal name step_type status "
        "risk_level capability_key idempotency_key started_at finished_at".split()),
    "work_attempts": set(
        "id company_id work_run_id work_step_id attempt_number worker_id "
        "lease_token status started_at finished_at error_class error_code "
        "error_message_redacted retryable retry_after metrics trace_id "
        "created_at".split()),
    "approval_requests": set(
        "id company_id tenant_connection_id permission_grant_id "
        "requested_by_user_id approved_by_user_id subject_type subject_id "
        "action_type status risk_level preview request_payload "
        "approval_result error_message expires_at approved_at rejected_at "
        "executed_at created_at updated_at work_run_id work_step_id "
        "idempotency_key action_fingerprint decision decision_payload "
        "requested_preview requested_at resolved_at resolved_by_user_id".split()),
    "integrations": set(
        "id company_id provider identifier token instance_id base_url "
        "is_active created_at client_token buffer_enabled "
        "buffer_debounce_seconds buffer_max_wait_seconds agent_id updated_at "
        "webhook_token_hash webhook_token_prefix alert_target channel_status "
        "last_seen_at purpose".split()),
    "research_monitors": set(
        "id company_id user_id name monitor_type topic source_policy_filter "
        "url_filters query_spec cadence schedule_spec timezone change_policy "
        "severity_policy channels budget_brl is_active health health_reason "
        "last_run_at last_change_at consecutive_failures routine_id "
        "created_at updated_at".split()),
    "platform_incidents": set(
        "id incident_key severity status scope summary impact_summary "
        "started_at detected_at acknowledged_at resolved_at owner_user_id "
        "source_refs work_run_id postmortem_artifact_id created_at "
        "updated_at".split()),
    "admin_inbox_states": set(
        "id admin_user_id source_type source_id state snoozed_until "
        "note_redacted updated_at".split()),
    "companies": set("id company_name created_at".split()),
}

# Tabelas que os read models tocam e cujo schema não foi copiado aqui. Cada
# entrada é uma decisão: ou o schema entra na cópia acima, ou a tabela fica
# declarada como não verificada — nunca esquecida em silêncio.
NAO_VERIFICADAS = {
    "intelligence_signals": "schema da SPEC-059, coberto por test_spec059",
    "knowledge_candidates": "schema da SPEC-052",
    "research_requests": "schema da SPEC-060, coberto por test_spec060",
    "tenant_auxiliaries": "schema da SPEC-058",
    "artifacts": "schema da SPEC-057",
    "platform_admin_role_bindings": "criada nesta SPEC, verificada na migration",
    "platform_admin_permission_overrides": "idem",
    "admin_audit_events": "idem",
    "admin_support_sessions": "idem",
    "admin_saved_views": "idem",
    "tool_definitions": "schema da SPEC-056",
    "tool_releases": "schema da SPEC-056",
}

ARQUIVOS = [
    "app/services/control_plane/inbox.py",
    "app/services/control_plane/read_models.py",
    "app/services/control_plane/rbac.py",
    "app/services/control_plane/audit.py",
]

# `.table("x").select("a, b, c")` — inclusive quebrado em várias linhas.
PADRAO = re.compile(
    r'\.table\(\s*"([a-z_]+)"\s*\)\s*(?:\.\s*)?\n?\s*\.\s*select\(\s*("(?:[^"]|"\s*\n\s*")*")',
    re.M)

# `self._ler("tabela", "colunas", …)` — o leitor tolerante da Inbox. Ele monta
# a consulta com variáveis, então o padrão acima não o enxerga. E é EXATAMENTE
# aqui que o defeito estava: um erro de coluna some dentro do `except` e a
# fonte simplesmente nunca aparece na caixa.
PADRAO_LER = re.compile(
    r'_ler\(\s*"([a-z_]+)"\s*,\s*("(?:[^"]|"\s*\n\s*")*")', re.M)


def sem_comentario(fonte: str) -> str:
    """Comentário não é consulta.

    Sem isto, a própria explicação do defeito ("a coluna é `action_type`, não
    `action_key`") fazia o teste acusar o defeito que ela descreve.
    """
    linhas = []
    for l in fonte.split("\n"):
        corte = l.find("#")
        linhas.append(l[:corte] if corte >= 0 and '"' not in l[:corte] else l)
    return "\n".join(linhas)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def colunas_de(bloco: str) -> list[str]:
    """`"a, b, " "c"` → ['a','b','c']. Concatenação implícita incluída."""
    junto = "".join(re.findall(r'"([^"]*)"', bloco))
    return [c.strip() for c in junto.split(",") if c.strip() and c.strip() != "*"]


def teste_colunas_existem():
    print("\n[1] Toda coluna lida existe na tabela")
    total = 0
    for rel in ARQUIVOS:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.exists(caminho):
            checar(False, f"{rel} existe")
            continue
        with open(caminho, encoding="utf-8") as fh:
            fonte = sem_comentario(fh.read())

        for tabela, bloco in PADRAO.findall(fonte) + PADRAO_LER.findall(fonte):
            total += 1
            if tabela in NAO_VERIFICADAS:
                continue
            if tabela not in SCHEMA:
                checar(False,
                       f"'{tabela}' tem schema conhecido ou está declarada",
                       f"em {rel}. Acrescente a SCHEMA ou a NAO_VERIFICADAS "
                       f"com o motivo.")
                continue
            faltando = [c for c in colunas_de(bloco) if c not in SCHEMA[tabela]]
            checar(not faltando, f"{rel} → {tabela}",
                   f"coluna(s) inexistente(s): {faltando}")
    checar(total > 0, "o padrão encontrou consultas para verificar",
           f"{total} encontradas")


def teste_tabelas_existem():
    print("\n[2] Toda tabela lida existe")
    conhecidas = set(SCHEMA) | set(NAO_VERIFICADAS)
    for rel in ARQUIVOS:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding="utf-8") as fh:
            fonte = fh.read()
        for tabela in set(re.findall(r'\.table\(\s*"([a-z_]+)"\s*\)', fonte)):
            checar(tabela in conhecidas, f"{rel} → tabela '{tabela}' é conhecida",
                   "não está em SCHEMA nem em NAO_VERIFICADAS")


def teste_o_defeito_que_originou_este_arquivo():
    print("\n[3] Os dois defeitos que motivaram este teste não voltam")
    with open(os.path.join(RAIZ, "app/services/control_plane/inbox.py"),
              encoding="utf-8") as fh:
        inbox = sem_comentario(fh.read())
    checar("action_key" not in inbox,
           "a Inbox não lê `action_key` (a coluna é `action_type`)")
    checar("action_type" in inbox, "e lê `action_type`")

    with open(os.path.join(RAIZ, "app/services/control_plane/read_models.py"),
              encoding="utf-8") as fh:
        cockpit = sem_comentario(fh.read())
    checar("company_integrations" not in cockpit,
           "o Cockpit não lê `company_integrations` (a tabela é `integrations`)")
    checar('table("integrations")' in cockpit, "e lê `integrations`")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 — AS COLUNAS QUE O CONTROL PLANE LÊ EXISTEM")
    print("=" * 68)
    for teste in (teste_colunas_existem, teste_tabelas_existem,
                  teste_o_defeito_que_originou_este_arquivo):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("NENHUMA CONSULTA LÊ COLUNA QUE NÃO EXISTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
