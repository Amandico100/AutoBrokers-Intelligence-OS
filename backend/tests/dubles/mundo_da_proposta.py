# -*- coding: utf-8 -*-
"""O MUNDO da proposta — SPEC-130-A F3 (a costura). UM dublê para o fio, a proposta e a mensagem.

O banco é o `BancoU1` da 129-B (o PostgREST em memória com as travas do U1: FKs compostas, CHECKs, `unique`), semeado
com o pedido REAL do canário (`fixtures/proposta/ofertas_canario_saneadas.json`: 104 ofertas, 5 cálculos, 6 eventos)
como o MOTOR o gravaria: `multicalculo_pedidos` → `multicalculo_calculos` → `multicalculo_ofertas`/`eventos`. As tabelas
do Hub (`artifacts*`, `report_templates`), da marca (`brand_profiles`, `brand_assets`), `integrations` e
`multicalculo_config` entram sem esquema (o dublê aceita qualquer coluna e devolve `id`/`created_at`).

O que é REAL de propósito (CLAUDE.md §9.4 — o teste chama o MOTOR): a porta (`MulticalculoProvider.consultar` +
`RepositorioMulticalculo`), a comparação, o Artifact Hub (`ArtifactService`) e o `snapshot_para_artefato` da marca.
O retrato da produção (📊 06/10/2026, `execute_sql` só leitura no projeto do produto): o CANAL não tem linha em
`brand_profiles`; das 2 corretoras aderidas, 1 tem a marca PUBLICADA (temas + logo `data:image/png`) e a outra só um
rascunho; nenhuma tem `contact.whatsapp`; cada uma tem 1 integração `observer` conectada com número pareado.

⛔ Nomes FICTÍCIOS (CLAUDE.md §13.9): "Orion"/"Vega" são personagens do teste, nunca constante do produto.
"""
from __future__ import annotations

import base64
import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Optional

import dubles_do_work_os as D
from dubles.banco_multicalculo import BancoU1, instalar_esquema

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "proposta" / "ofertas_canario_saneadas.json"

#: a comissão ESCRITA no banco (a fixture vem sem ela): um número que não aparece em nenhum outro lugar, para que
#: "0 ocorrência" seja uma afirmação que PODE falhar (§9.3 corolário)
COMISSAO_NO_BANCO = 17.37

#: o PNG 1×1 que faz o papel do logo publicado (📊 em produção o logo é `data:image/png;base64,…`)
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
LOGO_DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode("ascii")

NOME_ALFA = "Orion Corretora Ficticia"          # companies.company_name (corretora_a — a VENCEDORA no canário)
MARCA_ALFA = "Orion Seguros Ficticia"            # brand_profiles.display_name (publicada)
NOME_BETA = "Vega Corretora Ficticia"           # companies.company_name (corretora_b)
MARCA_BETA = "Vega Seguros Rascunho"            # brand_profiles.display_name (NÃO publicada)
NOME_CANAL = "Canal Comparador Ficticio"
WHATS_ALFA = "5548999990001"                    # declarado na marca publicada (contact.whatsapp)
WHATS_BETA_ATENDIMENTO = "+55 48 99999-0002"    # integração de ATENDIMENTO ativa
WHATS_BETA_OBSERVER = "+55 48 99999-0003"       # integração OBSERVER (o número do observador — não é o da venda)


def dados_do_canario() -> Dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _paleta(primaria: str, acento: str) -> Dict[str, Any]:
    from app.services.brand.system import build_design_system

    s = build_design_system(primaria, acento)
    return {"primary": s["primary"], "accent": s["accent"], "scales": s["scales"], "themes": s["themes"],
            "audit": s["audit"], "origin": "website"}


def montar_mundo(monkeypatch, *, solicitante: str = "canal", comissao: Optional[float] = COMISSAO_NO_BANCO,
                 canal_com_marca: bool = False) -> SimpleNamespace:
    """O banco com o pedido do canário gravado.

    `solicitante="canal"`: o pedido do CANAL nas duas corretoras (o canário real de 05/10).
    `solicitante="beta"`: o MESMO quadro, só a parte da corretora_b, pedido pela própria corretora_b."""
    instalar_esquema(monkeypatch, com_porta=True)
    relogio = D.Relogio(datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc))
    banco = BancoU1(relogio)
    dados = dados_do_canario()
    alfa, beta = dados["corretoras"]["corretora_a"], dados["corretoras"]["corretora_b"]
    canal = "c1300000-0000-4000-8000-00000000ca1a"
    intruso = "c1300000-0000-4000-8000-0000000017e0"

    banco.semear("companies", {"id": canal, "company_kind": "platform_canal", "company_name": NOME_CANAL,
                               "is_technical": True})
    banco.semear("companies", {"id": alfa, "company_kind": "client", "company_name": NOME_ALFA})
    banco.semear("companies", {"id": beta, "company_kind": "client", "company_name": NOME_BETA})
    banco.semear("companies", {"id": intruso, "company_kind": "client", "company_name": "Gama Intrusa Ficticia"})
    banco.semear("multicalculo_adesoes", {"canal_company_id": canal, "corretora_company_id": alfa, "ativa": True,
                                          "criada_em": "2026-10-01T12:00:00+00:00"})
    banco.semear("multicalculo_adesoes", {"canal_company_id": canal, "corretora_company_id": beta, "ativa": True,
                                          "criada_em": "2026-10-02T12:00:00+00:00"})

    # a MARCA (o retrato de 06/10): Orion publicada com logo e WhatsApp declarado; Vega rascunho; o canal sem linha
    logo_id = str(uuid.uuid4())
    banco.semear("brand_assets", {"id": logo_id, "company_id": alfa, "kind": "logo", "storage_ref": LOGO_DATA_URL,
                                  "mime_type": "image/png", "width": 1, "height": 1, "has_transparency": True})
    banco.semear("brand_profiles", {
        "company_id": alfa, "display_name": MARCA_ALFA, "is_published": True,
        "palette": _paleta("#1D5579", "#EE7501"), "logo_asset_id": logo_id,
        "contact": {"whatsapp": f"https://wa.me/{WHATS_ALFA}", "phones": ["(48) 3333-0000"]},
        "service_area": "Florianópolis - SC", "founded_year": 2009, "susep_code": "SUSEP 202031234",
        "website_url": "https://www.orion-ficticia.test/", "tagline": "Seguro com gente de verdade"})
    banco.semear("brand_profiles", {
        "company_id": beta, "display_name": MARCA_BETA, "is_published": False,
        "palette": _paleta("#2E7D32", "#F9A825"),
        "contact": {"whatsapp": "5548999990099"}, "founded_year": 1999})
    if canal_com_marca:
        banco.semear("brand_profiles", {"company_id": canal, "display_name": NOME_CANAL, "is_published": False})
    banco.semear("integrations", {"company_id": beta, "provider": "evolution-go", "purpose": "observer",
                                  "is_active": True, "channel_status": "connected",
                                  "paired_phone_e164": WHATS_BETA_OBSERVER})
    banco.semear("integrations", {"company_id": beta, "provider": "evolution-go", "purpose": "attendance",
                                  "is_active": True, "channel_status": "connected",
                                  "paired_phone_e164": WHATS_BETA_ATENDIMENTO})
    # a ficha do Google CONFIRMADA só pela Orion (a busca por nome nunca entra — U4)
    banco.semear("multicalculo_config", {"company_id": alfa, "config": {
        "google_confirmado": {"nota": 4.9, "avaliacoes": 37, "data": "06/10/2026", "fonte": "Google, ficha confirmada"}}})

    if solicitante == "canal":
        dono, corretoras = canal, [alfa, beta]
    elif solicitante == "beta":
        dono, corretoras = beta, [beta]
    else:
        raise ValueError(solicitante)
    pedido_id = dados["pedido_id"]
    gravar_pedido(banco, dados, dono=dono, corretoras=corretoras, comissao=comissao)
    return SimpleNamespace(banco=banco, relogio=relogio, dados=dados, alfa=alfa, beta=beta, canal=canal,
                           intruso=intruso, dono=dono, pedido_id=pedido_id, corretoras=corretoras,
                           db=banco.visao("smith-api"))


def gravar_pedido(banco: BancoU1, dados: Dict[str, Any], *, dono: str, corretoras: Iterable[str],
                  comissao: Optional[float]) -> None:
    """Grava o pedido como o MOTOR o deixaria (as travas do U1 conferem cada linha)."""
    corretoras = list(corretoras)
    pedido_id = dados["pedido_id"]
    banco.semear("multicalculo_pedidos", {
        "id": pedido_id, "company_id": dono, "origem": "teste", "ramo": 31, "opcoes": ["padrao", "economica"],
        "corretoras": corretoras, "pedido_cifrado": "cifrado-ficticio", "cpf_hmac": "0" * 64, "quadro_s": 60,
        "status": "fechado"})
    for e in dados["estados"]:
        if e["corretora_company_id"] not in corretoras:
            continue
        banco.semear("multicalculo_calculos", {
            "id": e["calculo_id"], "pedido_id": pedido_id, "solicitante_company_id": dono,
            "company_id": e["corretora_company_id"], "opcao": e["opcao"], "coberturas": {}, "status": "fechado",
            "negocio_ref": f"negocio-{e['versao']}", "versao": e["versao"],
            "origem_calculo_id": e.get("origem_calculo_id"), "prioridade": 0})
    for o in dados["ofertas"]:
        if o["corretora_company_id"] not in corretoras:
            continue
        linha = {k: copy.deepcopy(v) for k, v in o.items() if k != "corretora_company_id"}
        linha.update({"company_id": o["corretora_company_id"], "solicitante_company_id": dono,
                      "comissao_percentual": comissao})
        banco.semear("multicalculo_ofertas", linha)
    for ev in dados["eventos"]:
        if ev["corretora_company_id"] not in corretoras:
            continue
        linha = {k: v for k, v in ev.items() if k != "corretora_company_id"}
        linha.update({"company_id": ev["corretora_company_id"], "solicitante_company_id": dono,
                      "chave": f"evento-{ev['id']}"})
        banco.semear("multicalculo_eventos", linha)
