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

    import asyncio
    import portal_worker.journeys.allianz_corretor as allianz_corretor
    from portal_worker.journeys import get_journey
    from portal_worker.journeys.allianz_corretor import (
        _attach_expanded_details,
        _extract_menu_candidates,
        _looks_like_ficha_gestao,
        _looks_like_inadimplentes_result,
        _looks_like_policy_context,
        _policy_context_matches_customer,
        _looks_like_recibos_list,
        _merge_recibos_context,
        _policy_search_terms,
        _receipt_click_terms,
        _extract_new_window_url_from_onclick,
        _safe_home_inadimplencias_text,
        _should_restart_policy_search_from_home,
        _summarize_policy_search_component,
        _summarize_policy_search_debug,
        _summarize_download_debug,
        _summarize_network_trace,
        _summarize_policy_result_trace,
        build_boleto_storage_path,
        extract_inadimplentes_from_rows,
        extract_recibos_from_rows,
        extract_totals_from_rows,
        _sanitize_trace_url,
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
    totals = extract_totals_from_rows([
        {"cells": ["711110", "2013 - Residencia Digital", "14", "2", "2", "477,58", "17,76"]},
        {"cells": ["711110", "2024 - Empresa PME", "18", "2", "2", "2.916,32", "603,03"]},
        {"cells": ["Cd.Corretor", "Ramo", "Qtd.Apolices", "Qtd.Pcs.", "Premio", "Comissao"]},
    ])
    check("extrai dois ramos do resultado totais", len(totals) == 2, totals)
    check("totais preserva ramo residencial", totals[0].get("ramo") == "2013 - Residencia Digital", totals)
    check("totais preserva qtd pcs empresa", totals[1].get("qtd_pcs") == 2, totals)
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
    check(
        "contexto operacional pode confirmar pelo nome do segurado",
        _policy_context_matches_customer(
            "DADOS GERAIS (AZR) Lista Recibos Ficha Gestao Nome MONICA BONELLI PAULO PRAZERES",
            {"cliente_nome": "MONICA BONELLI PAULO PRAZERES"},
        ) is True,
    )
    check(
        "busca de apolice pode partir do resultado legado",
        _should_restart_policy_search_from_home("PARCELAS INADIMPLENTES RESULTADO - POR PARCELA Recibo Parc. Apolice Susep") is False,
    )
    check(
        "busca de apolice nao reinicia quando ja esta no contexto",
        _should_restart_policy_search_from_home("Gerais Segurado Dados Risco Coberturas Lista Recibos Ficha Gestao") is False,
    )
    menu_candidates = _extract_menu_candidates({
        "menus": [
            {"label": "Vendas", "url": "/vendas"},
            {
                "label": "Consultas",
                "children": [
                    {"title": "Recibo/Pagamento", "path": "/drbl00/recibos/control.do"},
                    {"title": "Apólices/Proposta", "url": "/drbl00/apolice/control.do"},
                ],
            },
        ],
    })
    check("menu trace encontra recibo/pagamento", any("Recibo" in c.get("label", "") for c in menu_candidates), menu_candidates)
    check("menu trace preserva url operacional", any("recibos" in c.get("url", "") for c in menu_candidates), menu_candidates)
    terms = _receipt_click_terms({"recibo": "318946949", "parcela": "3/10", "vencimento": "01/07/2026"})
    check("termos de clique priorizam recibo", terms[0] == "318946949", terms)
    check("termos de clique incluem parcela", "3/10" in terms, terms)
    search_terms = _policy_search_terms({
        "cliente_nome": "MONICA BONELLI PAULO PRAZERES",
        "cpf_cnpj": "03184509923",
        "apolice_susep": "5177202623140183705",
        "recibo": "317418783",
    })
    check(
        "termos de busca priorizam NOME (fluxo real do corretor, prints 2026-07-10)",
        search_terms[0] == "MONICA BONELLI PAULO PRAZERES",
        search_terms,
    )
    check(
        "apolice susep concatenada NAO e termo de busca (portal responde 'Apolice inexistente')",
        "5177202623140183705" not in search_terms,
        search_terms,
    )
    check("termos de busca mantem CPF como fallback", "03184509923" in search_terms, search_terms)
    check(
        "modal de busca vazia e detectado",
        allianz_corretor.search_result_is_empty("Pesquisa de Cliente: FULANO Não foram encontrados resultados FECHAR"),
    )
    check(
        "modal 'Apolice inexistente' e tratado como busca vazia",
        allianz_corretor.search_result_is_empty("Pesquisa de Apólice: 5177202623140183705 Apólice inexistente FECHAR"),
    )
    check(
        "existe relogin fresco para busca degradada por sessao restaurada",
        callable(getattr(allianz_corretor, "_relogin_fresh", None)),
    )
    check(
        "ficha gestao reconhecida pela tela REAL (Indexar/registros/Descripcion — print p13)",
        allianz_corretor._looks_like_ficha_gestao(
            "Allianz Nota Indexar EP - P- APÓLICE - 13758374700000 - 16 (16) registros "
            "Fecha Tipo Modelo Descripcion Usuario Carta Inadimplência - Aviso DLGAFP"
        ),
    )
    check(
        "ficha gestao reconhecida so pelo header mesmo sem a carta na primeira dobra",
        allianz_corretor._looks_like_ficha_gestao(
            "Nota Indexar EP - P- APÓLICE - 13758374700000 - 16 (16) registros Fecha Tipo Modelo Descripcion Usuario"
        ),
    )
    check(
        "tela de login nao passa por ficha gestao",
        allianz_corretor._looks_like_ficha_gestao("Bem-vindo(a) à Allianznet Iniciar Sessão Esqueceu a senha?") is False,
    )
    check(
        "lista de recibos nao passa por ficha gestao",
        allianz_corretor._looks_like_ficha_gestao(
            "LISTAGEM DE RECIBOS (AZR) Recibo Parcelas Contador Endosso Tipo Recibo Pendente Gestor Cobrança Pendentes"
        ) is False,
    )
    check(
        "existe varredura de abas do contexto por fileManagement (popup fora do expect_popup)",
        callable(getattr(allianz_corretor, "_find_ficha_gestao_page", None)),
    )
    check(
        "accessToken extraido da URL do botao Ficha Gestao",
        allianz_corretor._access_token_from_url(
            "https://x/ngx-file-management/fileManagement?uid=BA068610&accessToken=eyJhbGc.payload.sig&checksum=Z"
        ) == "eyJhbGc.payload.sig",
    )
    check(
        "URL sem accessToken retorna vazio (nao inventa token)",
        allianz_corretor._access_token_from_url("https://x/fileManagement?uid=BA068610") == "",
    )
    check(
        "existe injecao de Authorization no BFF da Ficha Gestao (route interception)",
        callable(getattr(allianz_corretor, "_install_bff_auth_route", None)),
    )
    import inspect as _insp_fg

    _fg_src = _insp_fg.getsource(allianz_corretor._install_bff_auth_route)
    check(
        "injecao usa os headers reais do request que funciona (Bearer + epac-company-id + x-rws-rootapp)",
        "authorization" in _fg_src and "epac-company-id" in _fg_src and "x-rws-rootapp" in _fg_src,
    )
    check(
        "download tenta o botao real 'Acesso a detalhes estendidos'",
        "Acesso a detalhes estendidos" in _insp_fg.getsource(allianz_corretor._download_current_pdf),
    )
    import inspect as _insp_ctx

    _ctx_src = _insp_ctx.getsource(allianz_corretor._open_policy_context_for_item)
    check(
        "busca tenta de novo apos relogin fresco (2 passadas)",
        "_relogin_fresh" in _ctx_src and "range(2)" in _ctx_src,
    )
    _fill_src = _insp_ctx.getsource(allianz_corretor._fill_global_search_for_category)
    check(
        "barra global priorizada por placeholder Pesquisar (nao cai em campo de filtro)",
        "esquisar" in _fill_src,
    )
    check(
        "tela com resultados nao e tratada como vazia",
        allianz_corretor.search_result_is_empty("Pesquisa de Cliente: FULANO 2 resultados encontrados") is False,
    )
    check(
        "existe fechador de modal bloqueante",
        callable(getattr(allianz_corretor, "_dismiss_blocking_modal", None)),
    )
    import inspect as _inspect

    _click_src = _inspect.getsource(allianz_corretor._click_customer_search_result)
    check("resultado de busca aceita match por apolice susep", "wantApolice" in _click_src)
    _sweep_src = _inspect.getsource(allianz_corretor.cobranca_sweep)
    check(
        "needs_human de download orienta sobre janela noturna da busca",
        "empty_search_terms" in _sweep_src and "horario comercial" in _sweep_src,
    )
    check(
        "busca de apolice tem preenchimento sem submeter para escolher categoria",
        callable(getattr(allianz_corretor, "_fill_global_search_for_category", None)),
    )
    check(
        "busca de cliente tem clique especifico no resultado do modal",
        callable(getattr(allianz_corretor, "_click_customer_search_result", None)),
    )
    check(
        "botoes cinza do rodape Allianz tem clique especifico",
        callable(getattr(allianz_corretor, "_click_section_button_candidate", None)),
    )
    check(
        "botoes que abrem janela usam clique trusted do Playwright",
        callable(getattr(allianz_corretor, "_click_section_button_candidate_trusted", None)),
    )
    search_debug = _summarize_policy_search_debug([
        {"placeholder": "Susep", "value": "0711110", "x": 270, "y": 330, "w": 80, "h": 20, "near_text": "FILTRO Susep Codigo Corretor"},
        {"placeholder": "Pesquisar ...", "value": "", "x": 30, "y": 170, "w": 520, "h": 36, "near_text": "Pesquisar"},
    ])
    check("debug de busca prioriza campo pesquisar", search_debug.get("inputs", [{}])[0].get("placeholder") == "Pesquisar ...", search_debug)
    component = _summarize_policy_search_component([
        {"tag": "span", "cls": "nx-icon nx-icon--search", "x": 565, "y": 180, "w": 28, "h": 28, "html": "<span class='nx-icon nx-icon--search'></span>"},
        {"tag": "span", "cls": "nx-icon nx-icon--info", "x": 602, "y": 180, "w": 28, "h": 28, "html": "<span class='nx-icon nx-icon--info'></span>"},
    ])
    check("debug do componente prioriza icone de busca", component.get("nodes", [{}])[0].get("cls") == "nx-icon nx-icon--search", component)
    row_trace = _summarize_policy_result_trace(
        [
            {"text": "317418783", "tag": "td", "cursor": "default", "cell_index": 0},
            {"text": "5177202623140183705", "tag": "td", "cursor": "pointer", "cell_index": 2, "onclick": "openPolicy()"},
            {"text": "Gerar Planilha", "tag": "button", "cursor": "pointer", "cell_index": -1},
        ],
        {"recibo": "317418783", "apolice_susep": "5177202623140183705"},
    )
    check("trace da linha prioriza celula da apolice clicavel", row_trace.get("row_candidates", [{}])[0].get("text") == "5177202623140183705", row_trace)
    network_trace = _summarize_network_trace([
        {"kind": "request", "method": "GET", "url": "https://www.allianznet.com.br/assets/logo.png"},
        {"kind": "request", "method": "GET", "url": "https://www.allianznet.com.br/ngx-azb-epac/private/application/static?token=abc&apolice=123"},
        {"kind": "response", "status": 200, "url": "https://www.allianznet.com.br/ngx-file-management/fileManagement?uid=UID000000"},
    ])
    check("trace de rede remove token sensivel", "token=abc" not in str(network_trace), network_trace)
    check("trace de rede prioriza rotas Allianz relevantes", network_trace.get("events", [{}])[0].get("url", "").find("application/static") >= 0, network_trace)
    check(
        "sanitizacao de URL preserva rota e remove senha",
        _sanitize_trace_url("https://x.test/path?senha=abc&uid=UID000000") == "https://x.test/path?uid=UID000000",
    )
    ficha_onclick = (
        "sendMenuVerticalEventNewWindow('https://www.allianznet.com.br:443/ngx-file-management/"
        "fileManagement?uid=UID000000&token=abc123&codCia=4', 'menu.fichagestao');"
    )
    extracted_ficha_url = _extract_new_window_url_from_onclick(ficha_onclick)
    check("extrai URL de janela nova da Ficha Gestao", "ngx-file-management/fileManagement" in extracted_ficha_url, extracted_ficha_url)
    check("URL operacional extraida nao deve ir sanitizada para navegacao", "token=abc123" in extracted_ficha_url, extracted_ficha_url)
    check("sanitizacao de URL da ficha remove token", "token=abc123" not in _sanitize_trace_url(extracted_ficha_url), _sanitize_trace_url(extracted_ficha_url))
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
    check("home alerta reconhece inadimplencias", _safe_home_inadimplencias_text("INADIMPLÊNCIAS 4 ?") is True)
    check("home alerta reconhece sem acento", _safe_home_inadimplencias_text("Inadimplencias 8") is True)
    check("home alerta rejeita chat", _safe_home_inadimplencias_text("Precisa falar com a gente? CHAT ALLIANZ") is False)
    check("home alerta rejeita cotacao", _safe_home_inadimplencias_text("NOVA COTACAO") is False)

    async def _exercise_receipt_open_without_row_click():
        calls = []

        class _FakePage:
            async def wait_for_timeout(self, _ms):
                pass

        async def fake_all_body_text(_page):
            return "PARCELAS INADIMPLENTES RESULTADO - POR PARCELA Recibo Parc. Apolice Susep"

        async def fake_record_trace(*_args, **_kwargs):
            calls.append("record_trace")

        async def forbidden_row_click(*_args, **_kwargs):
            calls.append("row_click")
            return False

        async def fake_open_context(*_args, **_kwargs):
            calls.append("open_policy_context")
            return True

        async def fake_click_text(_page, candidates, **_kwargs):
            calls.append(("click_text", tuple(candidates)))
            return "Lista Recibos" in tuple(candidates)

        async def fake_wait_recibos(*_args, **_kwargs):
            calls.append("wait_recibos")
            return True

        saved = {
            "_all_body_text": allianz_corretor._all_body_text,
            "_record_policy_result_trace": allianz_corretor._record_policy_result_trace,
            "_click_row_candidate": allianz_corretor._click_row_candidate,
            "_open_policy_context_for_item": allianz_corretor._open_policy_context_for_item,
            "_click_text_candidate": allianz_corretor._click_text_candidate,
            "_wait_until_recibos_list": allianz_corretor._wait_until_recibos_list,
        }
        try:
            allianz_corretor._all_body_text = fake_all_body_text
            allianz_corretor._record_policy_result_trace = fake_record_trace
            allianz_corretor._click_row_candidate = forbidden_row_click
            allianz_corretor._open_policy_context_for_item = fake_open_context
            allianz_corretor._click_text_candidate = fake_click_text
            allianz_corretor._wait_until_recibos_list = fake_wait_recibos
            opened = await allianz_corretor._open_receipts_for_item(
                _FakePage(),
                {"recibo": "318946949", "parcela": "3/10", "cliente_nome": "DEBORA LUZIA ROSA"},
                {},
                {},
            )
            return opened, calls
        finally:
            for name, value in saved.items():
                setattr(allianz_corretor, name, value)

    opened, receipt_calls = asyncio.run(_exercise_receipt_open_without_row_click())
    check("abre recibos sem clicar em linha inadimplente", opened is True, receipt_calls)
    check("fluxo nao clica em linha de recibo/inadimplente", "row_click" not in receipt_calls, receipt_calls)
    ordered = (
        "open_policy_context" in receipt_calls
        and "wait_recibos" in receipt_calls
        and receipt_calls.index("open_policy_context") < receipt_calls.index("wait_recibos")
    )
    check("fluxo abre contexto da apolice antes de Lista Recibos", ordered, receipt_calls)

    async def _exercise_inadimplencias_entry_before_search():
        calls = []

        class _FakePage:
            async def wait_for_timeout(self, _ms):
                pass

        async def fake_wait_entry(*_args, **_kwargs):
            calls.append("wait_entry")
            return True

        async def fake_body(_page):
            calls.append("body")
            return "Inicio Alertas de Negocio INADIMPLÊNCIAS 4 APOLICES A RENOVAR"

        async def fake_open_totals(*_args, **_kwargs):
            calls.append("open_totals")
            return False

        async def fake_click_home(*_args, **_kwargs):
            calls.append("click_home_inadimplencias")
            return True

        async def fake_wait_result(*_args, **_kwargs):
            calls.append("wait_result")
            return True

        async def forbidden_global_search(*_args, **_kwargs):
            calls.append("global_search")
            return False

        async def forbidden_adaptive(*_args, **_kwargs):
            calls.append("adaptive")
            class _Result:
                status = "needs_human"
                message = "should not run"
            return _Result()

        saved = {
            "_wait_for_inadimplencias_entry": allianz_corretor._wait_for_inadimplencias_entry,
            "_all_body_text": allianz_corretor._all_body_text,
            "_open_parcela_from_totals_if_needed": allianz_corretor._open_parcela_from_totals_if_needed,
            "_click_home_inadimplencias_entry": allianz_corretor._click_home_inadimplencias_entry,
            "_wait_until_inadimplentes_result": allianz_corretor._wait_until_inadimplentes_result,
            "_fill_global_search": allianz_corretor._fill_global_search,
            "_semantic_navigation_review": allianz_corretor._semantic_navigation_review,
        }
        try:
            allianz_corretor._wait_for_inadimplencias_entry = fake_wait_entry
            allianz_corretor._all_body_text = fake_body
            allianz_corretor._open_parcela_from_totals_if_needed = fake_open_totals
            allianz_corretor._click_home_inadimplencias_entry = fake_click_home
            allianz_corretor._wait_until_inadimplentes_result = fake_wait_result
            allianz_corretor._fill_global_search = forbidden_global_search
            allianz_corretor._semantic_navigation_review = forbidden_adaptive
            ok = await allianz_corretor._ensure_inadimplentes_page(_FakePage(), {}, {})
            return ok, calls
        finally:
            for name, value in saved.items():
                setattr(allianz_corretor, name, value)

    entry_ok, entry_calls = asyncio.run(_exercise_inadimplencias_entry_before_search())
    check("home inadimplencias abre antes da busca global", entry_ok is True, entry_calls)
    check("entrada nao usa busca generica cobranca", "global_search" not in entry_calls, entry_calls)
    check("entrada nao chama adaptativo quando alerta existe", "adaptive" not in entry_calls, entry_calls)

    async def _exercise_totals_page_stays_on_totals():
        calls = []

        class _FakePage:
            async def wait_for_timeout(self, _ms):
                pass

        async def fake_wait_entry(*_args, **_kwargs):
            calls.append("wait_entry")
            return True

        async def fake_body(_page):
            calls.append("body")
            return "Parcelas Inadimplentes RESULTADO - TOTAIS Cd.Corretor Ramo Qtd.Apolices Qtd.Pcs Premio Comissao"

        async def forbidden_open_totals(*_args, **_kwargs):
            calls.append("open_first_total")
            return True

        saved = {
            "_wait_for_inadimplencias_entry": allianz_corretor._wait_for_inadimplencias_entry,
            "_all_body_text": allianz_corretor._all_body_text,
            "_open_parcela_from_totals_if_needed": allianz_corretor._open_parcela_from_totals_if_needed,
        }
        try:
            allianz_corretor._wait_for_inadimplencias_entry = fake_wait_entry
            allianz_corretor._all_body_text = fake_body
            allianz_corretor._open_parcela_from_totals_if_needed = forbidden_open_totals
            ok = await allianz_corretor._ensure_inadimplentes_page(_FakePage(), {}, {})
            return ok, calls
        finally:
            for name, value in saved.items():
                setattr(allianz_corretor, name, value)

    totals_ok, totals_calls = asyncio.run(_exercise_totals_page_stays_on_totals())
    check("entrada aceita Resultado - Totais como area de inadimplentes", totals_ok is True, totals_calls)
    check("entrada nao abre primeira linha dos totais", "open_first_total" not in totals_calls, totals_calls)

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
