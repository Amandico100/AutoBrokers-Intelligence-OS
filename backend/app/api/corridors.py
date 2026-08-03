"""Catálogo de corredores — a lista vem de QUEM EXECUTA (SPEC-063, 03/08/2026).

O DEFEITO QUE ISTO DESFAZ
=========================
Havia DUAS coisas chamadas corredor, e a tela lia a errada:

    corridor_templates       TABELA no banco    2 linhas    ← a TELA lia isto
    corridor_playbooks.py    CÓDIGO            13 corredores ← isto EXECUTA

📊 Banco de produção, 03/08/2026, `select count(*) from corridor_templates`:
duas linhas — "Allianz Residencial — Assistência Residencial" e "Allianz
Residencial — Eletricista". Os dez corredores de auto que rodam há meses e os
dois residenciais novos NUNCA apareceram na página de Corredores. A corretora
olhava a tela e via um produto menor do que o que ela já tinha comprado.

O GLOSSARIO já declara que o corredor mora em `corridor_playbooks.py`. Esta
rota é a ponte que faltava: o Next pergunta, o Python responde com o que o
motor realmente sabe fazer. **Nenhuma lista é reescrita aqui** — tudo sai de
`list_playbooks()` / `get_playbook()`, e o que não estiver declarado lá não
aparece na tela. Duas listas divergem; é exatamente o defeito que estamos
desfazendo.

UM CARD POR (SEGURADORA × RAMO)
===============================
Decisão do founder, 03/08/2026, literal:

    "o corretor não quer saber se tem subcorredores, subserviços... vai
     confundir ele. Allianz Residencial e aí já vai tudo no pacote. Ele só
     precisa saber que Allianz Residencial está sendo atendida."

Por isso o corredor é a unidade, e os subserviços vão DENTRO dele — como texto,
nunca como coisa ligável. São 13 cards, não 40.

E O CARD DIZ A VERDADE
======================
Nem todo corredor abre chamado. `outcome` por subserviço (`abre`/`encaminha`)
sai do playbook e vai inteiro para a tela: 📊 o vidro da Porto termina num
FORMULÁRIO e o da Zurich numa ORIENTAÇÃO — nos dois, a seguradora não abre nada
por este canal. Prometer abertura onde só há encaminhamento é a mesma mentira
que a SPEC-063 acabou de tirar da tela de Seguradoras.

Read-only e sem dado de corretora: o catálogo é o mesmo para todas. Quem sabe
o que ESTA corretora ativou é `tenant_corridors`, e isso o Next resolve do lado
dele.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException

router = APIRouter()


def _require_internal_key(provided: Optional[str]) -> None:
    """Mesma porta interna do espelho de acionamentos (`dispatch_monitor`).

    O catálogo não é segredo, mas também não é público: quem pergunta é o
    servidor do Next, nunca o navegador do corretor."""
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


# COPY DE TELA — não é catálogo. As chaves canônicas continuam sendo as do
# playbook (`canonical_subservice`); isto aqui só decide como a palavra aparece
# para o corretor, com acento e maiúscula. Subserviço sem entrada aqui cai no
# rótulo do próprio playbook e, na falta dele, na própria chave: um trabalho
# novo aparece na tela no dia em que entra no código, sem passar por aqui.
_SUBSERVICO_DISPLAY = {
    "guincho": "Guincho",
    "bateria": "Bateria",
    "pneu": "Troca de pneu",
    "chaveiro": "Chaveiro",
    "vidros": "Vidros",
    "encanador": "Encanador",
    "desentupimento": "Desentupimento",
    "eletricista": "Eletricista",
    "eletrodomesticos": "Eletrodomésticos",
}

_RAMO_DISPLAY = {"auto": "Auto", "residencial": "Residencial"}
_CANAL_DISPLAY = {"whatsapp": "WhatsApp"}


def _rotulo_seguradora(insurer_key: str) -> str:
    """O nome que a corretora reconhece ("HDI", "Porto Seguro", "Azul Seguros").

    Vem do REGISTRO DE SEGURADORAS, que já é a fonte desses rótulos no produto.
    Seguradora sem registro aparece pela própria chave capitalizada — visível e
    errado é melhor que ausente e invisível."""
    try:
        from app.services.insurer_registry import INSURER_REGISTRY

        rotulo = str((INSURER_REGISTRY.get(insurer_key) or {}).get("label") or "").strip()
        if rotulo:
            return rotulo
    except Exception:  # noqa: BLE001
        pass
    return insurer_key.upper() if len(insurer_key) <= 3 else insurer_key.capitalize()


def _rotulo_subservico(chave: str, rotulos_do_playbook: Dict[str, Any]) -> str:
    display = _SUBSERVICO_DISPLAY.get(chave)
    if display:
        return display
    do_playbook = str(rotulos_do_playbook.get(chave) or "").strip()
    if do_playbook:
        return do_playbook[:1].upper() + do_playbook[1:]
    return chave.replace("_", " ").capitalize()


def build_corridor_catalog() -> List[Dict[str, Any]]:
    """Os corredores que o motor sabe executar, um por (seguradora × ramo).

    Importado direto pelo teste — por isso não depende de request nem de
    banco. Se `corridor_playbooks` ganhar um corredor amanhã, ele aparece aqui
    e na tela sem ninguém editar lista nenhuma."""
    from app.services.corridor_playbooks import (
        OUTCOME_ABRE,
        get_playbook,
        list_playbooks,
    )

    corredores: List[Dict[str, Any]] = []
    for ref in list_playbooks():
        pb = get_playbook(ref) or {}
        rotulos = pb.get("subservice_labels") or {}
        menu = pb.get("subservice_menu_map") or {}

        subservicos: List[Dict[str, Any]] = []
        for chave, dados in (pb.get("subservices") or {}).items():
            dados = dados or {}
            encaminhamento = dados.get("referral") or {}
            subservicos.append({
                "key": chave,
                "label": _rotulo_subservico(chave, rotulos),
                # `abre` = vai até o protocolo · `encaminha` = a seguradora
                # entrega formulário/orientação e o caso encerra resolvido.
                "outcome": str(dados.get("outcome") or OUTCOME_ABRE),
                "referral_kind": str(encaminhamento.get("kind") or "") or None,
                # Existe tecla de menu OBSERVADA para este trabalho? Sem ela o
                # corredor chega até a rota e para — e a tela tem de dizer isso.
                "menu_mapeado": bool(menu.get(chave) or dados.get("tipo_servico_opcao")),
            })
        subservicos.sort(key=lambda s: str(s["label"]).lower())

        desfechos = {str(s["outcome"]) for s in subservicos}
        if not desfechos:
            resumo = ""
        elif len(desfechos) == 1:
            resumo = desfechos.pop()
        else:
            resumo = "misto"

        insurer_key = str(pb.get("insurer_key") or "")
        line_kind = str(pb.get("line_kind") or "")
        canal = str(pb.get("channel") or "")
        rotulo_seguradora = _rotulo_seguradora(insurer_key)
        rotulo_ramo = _RAMO_DISPLAY.get(line_kind, line_kind.capitalize())

        corredores.append({
            # Identidade do card: o `playbook_id`, estável entre versões
            # (yelum já está em v3 e continua sendo o mesmo corredor).
            "corridor_id": str(pb.get("playbook_id") or ""),
            "playbook_ref": ref,
            "version": pb.get("version"),
            "insurer_key": insurer_key,
            "insurer_label": rotulo_seguradora,
            "line_kind": line_kind,
            "line_label": rotulo_ramo,
            "channel": canal,
            "channel_label": _CANAL_DISPLAY.get(canal, canal.capitalize()),
            "title": f"{rotulo_seguradora} · {rotulo_ramo}",
            "description": str(pb.get("description") or ""),
            "subservices": subservicos,
            "outcome_summary": resumo,
            # Sinistro e risco grave nunca são do corredor. Isto não é frase de
            # marketing: sai dos gatilhos de handoff declarados no playbook.
            "handoff_sinistro": any(
                "sinistro" in str(t).lower() for t in (pb.get("handoff_triggers") or [])
            ),
            "menu_mapeado": any(bool(s["menu_mapeado"]) for s in subservicos),
        })

    corredores.sort(key=lambda c: (str(c["insurer_label"]).lower(), str(c["line_label"]).lower()))
    return corredores


@router.get("/api/corridors/catalog")
async def corridors_catalog(
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """O catálogo de corredores, como o CÓDIGO o declara."""
    _require_internal_key(x_autobrokers_internal_key)
    corredores = build_corridor_catalog()
    return {
        "ok": True,
        "source": "backend/app/services/corridor_playbooks.py",
        "total": len(corredores),
        "corridors": corredores,
    }
