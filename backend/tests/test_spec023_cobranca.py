"""SPEC-023 P3/P4 - Allianz cobranca + rotina global.

Rodar: python backend/tests/test_spec023_cobranca.py
Testes puros: nao acessam portal, InfoCap nem WhatsApp. Protegem o contrato que
o worker e o motor de rotinas precisam expor em producao.
"""

import os
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def run():
    print("== SPEC-023 P3/P4 - cobranca ==\n")

    from portal_worker.journeys import get_journey
    from portal_worker.journeys.allianz_corretor import (
        _attach_expanded_details,
        _looks_like_ficha_gestao,
        _looks_like_inadimplentes_result,
        _looks_like_policy_context,
        _looks_like_recibos_list,
        _merge_recibos_context,
        _policy_search_terms,
        _receipt_click_terms,
        _summarize_policy_search_debug,
        _summarize_download_debug,
        build_boleto_storage_path,
        extract_inadimplentes_from_rows,
        extract_recibos_from_rows,
    )

    check(
        "registry resolve allianz cobranca_sweep",
        callable(get_journey("allianz_corretor", "cobranca_sweep")),
    )

    rows = [
        {
            "cells": [
                "123456789",
                "5310000000001",
                "777",
                "0",
                "10/07/2026",
                "15/07/2026",
                "04/07/2026",
                "1.234,56",
                "123,45",
            ],
            "detail": "Segurado: DEBORA LUZIA ROSA CPF/CNPJ: 103.851.159-38 Modalidade: Debito em Conta",
        },
        {"cells": ["cabecalho", "ApÃ³lice Susep", "Vcto."], "detail": ""},
    ]
    parsed = extract_inadimplentes_from_rows(rows)
    check("extrai 1 inadimplente", len(parsed) == 1, parsed)
    first = parsed[0] if parsed else {}
    check("normaliza CPF/CNPJ sem mascara", first.get("cpf_cnpj") == "10385115938", first)
    check("mantem nome do segurado", first.get("cliente_nome") == "DEBORA LUZIA ROSA", first)
    check("extrai vencimento", first.get("vencimento") == "04/07/2026", first)
    check("extrai premio como numero", first.get("valor") == 1234.56, first)
    check(
        "menu da home nao e lista de inadimplentes",
        _looks_like_inadimplentes_result("Inicio Parcelas Inadimplentes Documentacao Chat Allianz") is False,
    )
    check(
        "resultado/tabela e lista de inadimplentes",
        _looks_like_inadimplentes_result("Resultado por Parcela Apolice Susep Vcto. Premio Recibo") is True,
    )
    parsed_shifted = extract_inadimplentes_from_rows([
        {
            "cells": [
                "Recolher/Abrir informacao extendida",
                "317418783",
                "3/10",
                "5177202623140183705",
                "0",
                "000000",
                "20/08/2026",
                "20/08/2026",
                "01/07/2026",
                "96,95",
                "0,03",
            ],
            "detail": "Segurado: MONICA BONELLI PAULO PRAZERES CPF/CNPJ: 03184509923 Modalidade: Debito em Conta",
        }
    ])
    shifted = parsed_shifted[0] if parsed_shifted else {}
    check("formato real com expansor extrai recibo", shifted.get("recibo") == "317418783", shifted)
    check("formato real com expansor extrai parcela", shifted.get("parcela") == "3/10", shifted)
    check("formato real com expansor extrai CPF", shifted.get("cpf_cnpj") == "03184509923", shifted)
    check("formato real com expansor extrai vcto", shifted.get("vencimento") == "01/07/2026", shifted)
    attached_rows = _attach_expanded_details([
        {"cells": ["317418783", "3/10", "5177202623140183705", "0", "000000", "20/08/2026", "20/08/2026", "01/07/2026", "96,95", "0,03"], "detail": "317418783 3/10 5177202623140183705"},
        {"cells": ["Segurado: MONICA BONELLI PAULO PRAZERES", "CPF/CNPJ: 03184509923"], "detail": "Segurado: MONICA BONELLI PAULO PRAZERES CPF/CNPJ: 03184509923 Modalidade: Debito em Conta"},
    ])
    attached = extract_inadimplentes_from_rows(attached_rows)[0]
    check("anexa detalhe expandido ao recibo anterior", attached.get("cpf_cnpj") == "03184509923", attached)

    recibos = extract_recibos_from_rows([
        {"cells": ["111", "1", "0", "111", "Seguro", "01/06/2026", "04/07/2026", "865,28", "Pendente", "04/07/2026"]},
        {"cells": ["222", "2", "0", "222", "Seguro", "01/05/2026", "04/06/2026", "865,28", "Cobrado", "04/06/2026"]},
    ])
    check("filtra apenas recibos pendentes", len(recibos) == 1 and recibos[0].get("recibo") == "111", recibos)
    recibos_print = extract_recibos_from_rows([
        {
            "cells": [
                "318946949",
                "3/10",
                "0",
                "0",
                "CART",
                "15/04/2026",
                "01/07/2026",
                "58,24",
                "Pendente",
                "04/07/2026",
                "711110",
            ]
        }
    ])
    recibo_print = recibos_print[0] if recibos_print else {}
    check("lista recibos do print extrai parcela pendente", recibo_print.get("parcela") == "3/10", recibo_print)
    check("lista recibos do print extrai vencimento", recibo_print.get("vencimento") == "01/07/2026", recibo_print)
    check("lista recibos do print extrai valor", recibo_print.get("valor") == 58.24, recibo_print)
    check(
        "reconhece tela listagem de recibos",
        _looks_like_recibos_list("LISTAGEM DE RECIBOS (AZR) Recibos Parcela Premio Status Recibo Pendente") is True,
    )
    check(
        "home nao e listagem de recibos",
        _looks_like_recibos_list("Inicio Parcelas Inadimplentes Nova Cotacao Fale com a gente agora") is False,
    )
    check(
        "reconhece ficha gestao em nova janela",
        _looks_like_ficha_gestao("EP - P- APOLICE - 13758374700000 - 16 registros Tipo Modelo Description Carta Inadimplencia - Aviso") is True,
    )
    check(
        "reconhece contexto de apolice com botoes Allianz",
        _looks_like_policy_context("Inicio DEBORA LUZIA ROSA Gerais Segurado Dados Risco Coberturas Clausulas SDD Resumo Lista Recibos Ficha Gestao") is True,
    )
    check(
        "resultado por parcela nao e contexto de apolice",
        _looks_like_policy_context("PARCELAS INADIMPLENTES RESULTADO - POR PARCELA Recibo Parc. Apolice Susep Gerar Planilha Voltar") is False,
    )
    terms = _receipt_click_terms({"recibo": "318946949", "parcela": "3/10", "vencimento": "01/07/2026"})
    check("termos de clique priorizam recibo", terms[0] == "318946949", terms)
    check("termos de clique incluem parcela", "3/10" in terms, terms)
    search_terms = _policy_search_terms({
        "cliente_nome": "MONICA BONELLI PAULO PRAZERES",
        "cpf_cnpj": "03184509923",
        "apolice_susep": "5177202623140183705",
        "recibo": "317418783",
    })
    check("termos de busca priorizam segurado", search_terms[0] == "MONICA BONELLI PAULO PRAZERES", search_terms)
    check("termos de busca incluem apolice", "5177202623140183705" in search_terms, search_terms)
    search_debug = _summarize_policy_search_debug([
        {"placeholder": "Susep", "value": "0711110", "x": 270, "y": 330, "w": 80, "h": 20, "near_text": "FILTRO Susep Codigo Corretor"},
        {"placeholder": "Pesquisar ...", "value": "", "x": 30, "y": 170, "w": 520, "h": 36, "near_text": "Pesquisar"},
    ])
    check("debug de busca prioriza campo pesquisar", search_debug.get("inputs", [{}])[0].get("placeholder") == "Pesquisar ...", search_debug)
    merged = _merge_recibos_context(
        {"cliente_nome": "", "item_segurado": ""},
        "Apolice 137583747 Item 0 Apolice SUSEP 5177-2026-23-14-0186415 "
        "Ramo 2013-Residencia Digital Nome DEBORA LUZIA ROSA Incluido Historico",
    )
    check("contexto da listagem preenche ramo como item segurado", merged.get("item_segurado") == "2013-Residencia Digital", merged)
    check("contexto da listagem preenche nome", merged.get("cliente_nome") == "DEBORA LUZIA ROSA", merged)
    debug = _summarize_download_debug(
        "Resultado por Parcela ... Operar Lista Recibos Ficha Gestao Historico da Apolice ...",
        [
            {"text": "Nova Cotacao", "tag": "button", "x": 100, "y": 20},
            {"text": "Lista Recibos", "tag": "span", "x": 800, "y": 690},
            {"text": "Ficha Gestao", "tag": "span", "x": 700, "y": 690},
        ],
    )
    check("debug de download preserva snippet relevante", "Lista Recibos" in debug.get("text_snippet", ""), debug)
    check("debug de download prioriza acoes relevantes", debug.get("actions", [{}])[0].get("text") == "Lista Recibos", debug)

    path = build_boleto_storage_path(
        company_id="company-123",
        job_id="job-abc",
        portal_key="allianz_corretor",
        recibo="123456789",
        cpf_cnpj="10385115938",
        cliente_nome="DEBORA LUZIA ROSA",
    )
    check("path fica no bucket por tenant/job", path.startswith("company-123/allianz_corretor/job-abc/"), path)
    check("path nao contem CPF", "10385115938" not in path, path)
    check("path nao contem nome", "DEBORA" not in path.upper(), path)
    check("path termina em PDF", path.endswith(".pdf"), path)

    spec = importlib.util.spec_from_file_location(
        "billing_collection",
        str(ROOT / "app" / "services" / "billing_collection.py"),
    )
    billing_collection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(billing_collection)
    BILLING_KIND = billing_collection.BILLING_KIND
    customer_send_allowed = billing_collection.customer_send_allowed
    is_billing_routine = billing_collection.is_billing_routine
    normalize_billing_config = billing_collection.normalize_billing_config
    selected_portal_keys = billing_collection.selected_portal_keys
    test_send_number = billing_collection.test_send_number
    build_customer_message = billing_collection.build_customer_message

    routine = {"config": {"kind": BILLING_KIND, "portal_keys": ["allianz_corretor"]}}
    check("detecta rotina de cobranca por config.kind", is_billing_routine(routine) is True)
    check("rotina comum nao vira cobranca", is_billing_routine({"config": {"kind": "news"}}) is False)

    cfg = normalize_billing_config({"kind": BILLING_KIND})
    check("default seleciona Allianz", selected_portal_keys(cfg) == ["allianz_corretor"], cfg)
    check("default exige aprovacao", cfg.get("approval_required") is True, cfg)
    check("default e modo teste", cfg.get("send_mode") == "test", cfg)
    check("default herda numero de teste da entrega se vazio", normalize_billing_config(
        {"kind": BILLING_KIND, "send_mode": "test"},
        {"channel": "whatsapp", "number": "(47) 98808-7463"},
    ).get("test_number") == "47988087463")
    check("modo teste usa apenas numero de teste", test_send_number({
        "kind": BILLING_KIND,
        "send_mode": "test",
        "test_number": "55 (47) 98808-7463",
    }) == "5547988087463")
    check("modo aprovacao nao envia teste", test_send_number({
        "kind": BILLING_KIND,
        "send_mode": "approval",
        "test_number": "5547988087463",
    }) == "")
    check("modo teste exige numero minimamente valido", test_send_number({
        "kind": BILLING_KIND,
        "send_mode": "test",
        "test_number": "123",
    }) == "")

    os.environ.pop("BILLING_CUSTOMER_SEND_ENABLED", None)
    check("sem env nao envia cliente", customer_send_allowed({"send_mode": "live"}, env={}) is False)
    check(
        "env + live + sem aprovacao permite cliente",
        customer_send_allowed(
            {"send_mode": "live", "approval_required": False},
            env={"BILLING_CUSTOMER_SEND_ENABLED": "true"},
        ) is True,
    )
    check(
        "aprovacao ligada bloqueia envio direto",
        customer_send_allowed(
            {"send_mode": "live", "approval_required": True},
            env={"BILLING_CUSTOMER_SEND_ENABLED": "true"},
        ) is False,
    )
    cfg_msg = normalize_billing_config({
        "kind": BILLING_KIND,
        "attendant_name": "Even",
        "brokerage_name": "Resulta Seguros",
        "message_template": "",
    })
    msg = build_customer_message({
        "cliente_nome": "Sra. Rita",
        "seguradora": "ALLIANZ",
        "parcela": "9/10",
        "item_segurado": "BYD SONG",
        "apolice_susep": "5177202523312376574",
        "valor": 58.24,
    }, cfg_msg["message_template"], cfg_msg)
    check("mensagem nova usa nome da atendente", "Aqui e a Even, da Resulta Seguros" in msg, msg)
    check("mensagem nova usa parcela em negrito", "parcela *9/10*" in msg, msg)
    check("mensagem nova usa item segurado em negrito", "seguro do *BYD SONG*" in msg, msg)
    check("mensagem nova usa apolice em negrito", "Apolice: *5177202523312376574*" in msg, msg)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    if FAIL:
        for name, detail in FAILURES:
            print(f" - {name}: {detail}")
        raise SystemExit(1)


if __name__ == "__main__":
    run()
