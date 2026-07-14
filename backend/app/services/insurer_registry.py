"""REGISTRO DE SEGURADORAS (SPEC-034 Onda 2) — canais como DADOS versionados.

Fonte da verdade dos canais de WhatsApp de assistência por seguradora:
- `whatsapp`: número ATIVO (planilha da corretora — validado em produção).
- `whatsapp_alternativo`: número achado em pesquisa oficial (12/07) AINDA NÃO
  confirmado pelas atendentes — NUNCA usar até o founder confirmar (caso Yelum:
  a pesquisa apontou outro número, mas o da planilha segue funcionando).
- `ramos`: o que cada canal atende (base p/ o Cartógrafo saber O QUE mapear).

Resolução de telefone em produção: env INSURER_CONTACT_{KEY}_ASSISTENCIA
continua mandando (resolve_insurer_contact); este registro é o fallback e o
catálogo de mapeamento. Escopo atual: ASSISTÊNCIA no WhatsApp (sinistro fica
para o futuro; vidros é portal web — SPEC-033/Playwright, fora daqui).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# status_validacao: confirmado (em uso real) | planilha (não testado ainda)
# | divergente (pesquisa apontou outro nº — aguardando confirmação do founder)
INSURER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "allianz": {
        "label": "Allianz", "whatsapp": "551140901444", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": ["auto", "moto", "caminhao", "frota", "residencial"],
        "fallback_telefone": {"auto": "08000130700", "residencial": "08000177178"},
    },
    "alfa": {
        "label": "Alfa", "whatsapp": "551143931567", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": ["auto", "moto", "carga", "residencial_vinculada_ao_auto"],
        "notas": "Residencial/empresarial/condomínio independentes NÃO confirmados neste canal.",
    },
    "azul": {
        "label": "Azul Seguros", "whatsapp": "552139062985", "whatsapp_alternativo": "",
        "status_validacao": "confirmado", "ramos": ["auto"],
        "notas": "Auto não possui assistência residencial vinculada.",
    },
    "bradesco": {
        "label": "Bradesco Seguros", "whatsapp": "551130031022",
        "whatsapp_alternativo": "552140042702",
        "status_validacao": "confirmado",
        "ramos": ["auto", "residencial"],
        "notas": "Atendentes confirmaram 14/07: OS DOIS números funcionam. Mantido o da planilha como ativo; 21 4004-2702 é reserva validada.",
    },
    "hdi": {
        "label": "HDI", "whatsapp": "551155020700", "whatsapp_alternativo": "5511995248188",
        "status_validacao": "confirmado",
        "ramos": ["auto", "residencial"],
        "notas": "Atendentes confirmaram 14/07: os dois funcionam. Planilha ativo; alternativo é reserva validada.",
        "fallback_telefone": {"vida_funeral": "08000162727"},
    },
    "itau": {
        "label": "Itaú Seguros", "whatsapp": "551130039303", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": ["auto", "residencial"],
        "notas": ("ESTRATÉGIA (founder 14/07 — corretora não usa Itaú): a EMISSORA decide. "
                  "Produto Porto vendido pelo Itaú → este número (é o canal da Porto, validado). "
                  "Produto Itaú-próprio → SEM canal confirmado: tratar como sem WhatsApp (handoff) até confirmação."),
    },
    "mapfre": {
        "label": "Mapfre", "whatsapp": "551140040101", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": ["auto", "residencial"],
        "fallback_telefone": {"residencial_emergencia": "08007775318"},
    },
    "porto": {
        "label": "Porto Seguro", "whatsapp": "551130039303", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": ["auto", "moto", "caminhao", "taxi", "residencial", "vida"],
    },
    "tokio": {
        "label": "Tokio Marine", "whatsapp": "5511995786546", "whatsapp_alternativo": "5511953022395",
        "status_validacao": "confirmado",
        "ramos": ["auto", "residencial"],
        "notas": "Atendentes confirmaram 14/07: o número OFICIAL agora é 11 99578-6546 (o antigo virou reserva). ATENÇÃO: atualizar o env INSURER_CONTACT_TOKIO_ASSISTENCIA (env tem prioridade sobre o registro).",
    },
    "yelum": {
        "label": "Yelum", "whatsapp": "551131321001", "whatsapp_alternativo": "551132061414",
        "status_validacao": "divergente",
        "ramos": ["auto", "vida", "residencial", "empresarial"],
        "notas": "Número da planilha SEGUE FUNCIONANDO (validado em teste real 11/07). Alternativo aguarda confirmação.",
        "fallback_telefone": {"auto_vida": "08007014120", "residencial_empresarial": "08007025100"},
    },
    "youse": {
        "label": "Youse", "whatsapp": "", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": [],
        "notas": "SEM WhatsApp de assistência — acionamento por app/telefone (3003 5770 / 0800 730 9901). Nunca tentar WhatsApp.",
    },
    "zurich": {
        "label": "Zurich", "whatsapp": "551128902121", "whatsapp_alternativo": "",
        "status_validacao": "confirmado",
        "ramos": ["auto", "residencial", "vida", "patrimonial", "empresarial"],
        "notas": "Ressalva de horário: páginas divergem entre 24h e comercial. Fallback 0800 729 1400 fora do horário.",
        "fallback_telefone": {"assistencia_brasil": "08007291400"},
    },
}


def get_insurer(key: str) -> Optional[Dict[str, Any]]:
    return INSURER_REGISTRY.get(str(key or "").strip().lower())


def registry_whatsapp(key: str) -> str:
    """Número ATIVO da assistência (planilha) — fallback quando o env não define."""
    info = get_insurer(key)
    return str((info or {}).get("whatsapp") or "")


def mapping_targets() -> List[Dict[str, Any]]:
    """Agenda de trabalho do Cartógrafo: (seguradora, número, ramos a mapear).
    Só assistência WhatsApp; Youse fica de fora (sem canal)."""
    targets = []
    for key, info in INSURER_REGISTRY.items():
        if not info.get("whatsapp"):
            continue
        targets.append({
            "insurer_key": key, "label": info["label"], "whatsapp": info["whatsapp"],
            "ramos": list(info.get("ramos") or []),
            "status_validacao": info.get("status_validacao"),
        })
    return targets
