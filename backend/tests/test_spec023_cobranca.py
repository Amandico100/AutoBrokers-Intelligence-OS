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
        _looks_like_inadimplentes_result,
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

    recibos = extract_recibos_from_rows([
        {"cells": ["111", "1", "0", "111", "Seguro", "01/06/2026", "04/07/2026", "865,28", "Pendente", "04/07/2026"]},
        {"cells": ["222", "2", "0", "222", "Seguro", "01/05/2026", "04/06/2026", "865,28", "Cobrado", "04/06/2026"]},
    ])
    check("filtra apenas recibos pendentes", len(recibos) == 1 and recibos[0].get("recibo") == "111", recibos)

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

    print(f"\nPASS={PASS} FAIL={FAIL}")
    if FAIL:
        for name, detail in FAILURES:
            print(f" - {name}: {detail}")
        raise SystemExit(1)


if __name__ == "__main__":
    run()
