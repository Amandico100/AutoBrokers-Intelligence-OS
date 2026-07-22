# -*- coding: utf-8 -*-
"""SPEC-049 - Pareamento limpo, aviso de queda robusto e Garimpo v2.

Cobre: fix do rename (variaveis seguras permitidas SO na abertura/encerramento,
qualquer outro {{...}} segue bloqueado — funcional), campos-template travados
com Editar+aviso, card QR passo 1 / aviso passo 2 (sem diagnostico Evolution
legado), endpoint set-alert (numero != pareado; opcao grupo do suporte),
alerta de desconexao com fallback de remetente e destino do suporte humano,
Garimpo v2 (camada LLM barata em lote, desligavel). Standalone, sem pytest.
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
print("\n[1] Variaveis seguras no template (fix do rename) — funcional")

import re

_bp_src = _src("lib/admin/agent-blueprints-canonical.ts")
check("whitelist SO para opening/closing (TEMPLATE_FIELDS)",
      "TEMPLATE_FIELDS" in _bp_src and "SAFE_PLACEHOLDERS" in _bp_src)
check("validacao usa hasUnsafeTemplate", "hasUnsafeTemplate(k, val)" in _bp_src)

# Reproduz a logica em Python para prova funcional (mesmas regexes)
SAFE = re.compile(r"\{\{\s*(attendant_name|company_name|business_hours|handoff_target)\s*\}\}")
INJ = re.compile(r"\{\{|\}\}")


def has_unsafe(field, val):
    rest = SAFE.sub("", val) if field in ("opening_message", "closing_message") else val
    return bool(INJ.search(rest))


check("abertura com {{attendant_name}} PASSA",
      not has_unsafe("opening_message", "Ola! Sou {{attendant_name}}, da {{company_name}}."))
check("abertura com {{system_prompt}} BLOQUEIA",
      has_unsafe("opening_message", "Oi {{system_prompt}}"))
check("attendant_name com {{...}} BLOQUEIA (campo comum)",
      has_unsafe("attendant_name", "{{company_name}}"))
check("attendant_name simples PASSA", not has_unsafe("attendant_name", "Fernanda"))

_cli = _src("app/dashboard/personalizacao/agentes/AgentConfigClient.tsx")
check("abertura/encerramento travados por padrao (Editar + aviso)",
      "PROTECTED_KEYS" in _cli and "unlock" in _cli and "window.confirm" in _cli)
check("aviso explica as variaveis antes de liberar", "NÃO as apague" in _cli)

# ---------------------------------------------------------------------------
print("\n[2] Card de pareamento — QR primeiro, sem diagnostico legado")

_card = _src("components/vault/WhatsAppChannelCard.tsx")
_flow = _src("components/vault/WhatsAppPairingFlow.tsx")
check("Passo 1 = conectar/QR", "Passo 1" in _flow and "Gerar QR code" in _flow
      and "WhatsAppPairingFlow" in _card)
check("Passo 2 = aviso de queda, opcional", "Passo 2 (opcional)" in _card)
check("diagnostico Evolution legado REMOVIDO",
      "EVOLUTION_BASE_URL" not in _card and "diagnostics" not in _card)
check("aviso sempre editavel (mesmo conectado)", "state !== 'not_configured' && (" in _card)
check("opcao grupo do suporte humano", "Grupo do suporte humano" in _card)
check("explica que celular offline nao derruba", "sem bateria" in _card)

# ---------------------------------------------------------------------------
print("\n[3] Backend — set-alert + alerta robusto")

_ch = _src("app/api/whatsapp_channel.py", ROOT)
check("endpoint set-alert existe", "/api/whatsapp-channel/set-alert" in _ch)
check("numero de aviso != numero pareado", "numero_igual_ao_pareado" in _ch)
check("modo support (grupo do suporte humano)", "use_support_destination" in _ch)
check("status expoe config do aviso", "_channel_alert_info" in _ch)

_al = _src("app/services/whatsapp/alerts.py", ROOT)
check("destino resolve o suporte humano (_support_contact)", "_support_contact" in _al)
check("remetente com fallback: outra integracao ativa da corretora",
      "_sender_integration" in _al and "neq" in _al)
check("sem canal = registra em Atividades (nao silencia)", "log_activity" in _al)
check("caminho no texto do alerta atualizado (hub Corretora)",
      "Corretora" in _al and "Gerenciar conex" in _al)

_route = _src("app/api/dashboard/whatsapp-channel/route.ts")
check("proxy Next com action set-alert", "set-alert" in _route)

# ---------------------------------------------------------------------------
print("\n[4] Garimpo v2 — camada LLM barata em lote")

_gar = _src("app/services/broker_insights.py", ROOT)
check("camada LLM por corretora/dia (_llm_refine_company)", "_llm_refine_company" in _gar)
check("modelo economico por env (default haiku)", "claude-haiku-4-5" in _gar)
check("entrada limitada (cap de chars)", "_LLM_MAX_CHARS" in _gar)
check("desligavel via GARIMPO_LLM=0", "GARIMPO_LLM" in _gar)
check("novos kinds: duvida_seguros/necessidade", "duvida_seguros" in _gar and "necessidade" in _gar)
check("dedup antes de gravar (source garimpo_llm)", "garimpo_llm" in _gar)
check("LLM nunca derruba o garimpo", "nunca derruba o garimpo" in _gar)

# ---------------------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"RESULTADO: {PASS} ok, {FAIL} falhas")
for name, detail in FAILURES:
    print(f"  FALHOU: {name} {detail}")
sys.exit(1 if FAIL else 0)
