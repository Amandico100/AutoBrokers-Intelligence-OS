# -*- coding: utf-8 -*-
r"""M-D2 — A DIVERGENCIA APARECE INTEIRA. SPEC-EXTRA-001.1 BLOCO D.

🔴 **Este guarda vai do TEXTO CRU DO PDF ate a frase que chega ao modelo, sem
injecao em lugar nenhum.** O M-C2 provou a reconciliacao injetando as linhas do
PDF no pack "na forma que o extrator VAI produzir". Aqui o extrator produz.

```
linhas cruas do PDF  ->  extract_policy_document_evidence   (o MOTOR)
                     ->  _build_evidence_pack               (o MOTOR)
                     ->  apolice_reconciliada_do_pack       (o MOTOR)
                     ->  _build_llm_briefing                (o MOTOR)
```

```
 [GD2a] AS DUAS TABELAS  HDI 10 coverage_row + 6 deductible_prose + 4 installment_row (Σ R$ 306,60)
                         Allianz 20 coverage_row + 1 assistance_plan (Σ R$ 24.960,60)
                         e "Premio Liquido" NAO e cobertura em nenhuma das duas
 [GD2b] AS DUAS FONTES   franquia 550 (cadastro) x 600 (documento) — as DUAS, com origem
                         premio 19,17 x 17,25 — as DUAS, ditas
 [GD2c] A FORMA          forma de pagamento = Cartao (das PARCELAS) + sinal `cabecalho_divergente`
 [GD2d] OS CAMPOS        `tabela_itens` -> nome do plano (`nao_sabemos_ainda`)
                         `sit_renovacao_txt` -> SINAL, e a vigencia continua vindo das DATAS
 [GD2e] A PROSA          `itens[].observacoes` vira franquia quando NAO ha valor — e o PAR:
                         onde ha valor, o valor fica
 [GD2f] A ALLIANZ        21 coberturas; `Despesas Fixas` com "168 Hrs" como TEXTO (e carencia,
                         nao franquia — um numero ali seria uma franquia inventada)
```

📊 Os numeros vem de dois arquivos MEDIDOS em 14/09/2026, sem PII:
`tests/fixtures/pdf_tabelas_reais_extra0011.json` (as linhas cruas dos dois PDFs
reais, como o parser `direct_text` as entrega) e
`tests/fixtures/golden_apolices_extra0011.json` (o cadastro pela porta).

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem API, sem PII.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_divergencia_aparece_inteira.py
    ... --so GD2b   ·   ... --medir   ·   ... --mutar [M-D2a]
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
FIXTURES = os.path.join(TESTES, "fixtures")
GOLDEN = os.path.join(FIXTURES, "golden_apolices_extra0011.json")
TABELAS = os.path.join(FIXTURES, "pdf_tabelas_reais_extra0011.json")
HARNESS = os.path.join(TESTES, "test_toda_linha_tem_origem.py")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")

PASS = 0
FAIL = 0
MEDIDAS: dict = {}

#: ⛔ SINTETICO. O locator real (codfil/nosnum) nunca entra num arquivo de teste.
LOCATOR = {"provider": "infocap", "codfil": "1", "nosnum": "999001"}


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)   # type: ignore[union-attr]
    return mod


# 🔴 UM montador do `/documento` e do `/itens`, nao dois: sao os do M-A2.
_HA = _carregar("_harness_md2", HARNESS)


def _json(caminho):
    return json.load(io.open(caminho, encoding="utf-8"))


def golden():
    return _json(GOLDEN)["apolices"]


def tabelas():
    return _json(TABELAS)


def _numero(texto):
    """`"R$ 1.234,56"` -> `Decimal("1234.56")`. Sem reimplementar o parser: a
    conta e do TESTE, sobre a saida do motor."""
    bruto = str(texto or "").replace("R$", "").strip().replace(".", "").replace(",", ".")
    return Decimal(bruto or "0")


# ===========================================================================
# O CAMINHO INTEIRO — do texto cru do PDF ao briefing, tudo motor
# ===========================================================================
def evidencia_do_pdf(apelido):
    """As linhas CRUAS do PDF -> `evidence_items`, pelo EXTRATOR DE PRODUCAO."""
    from app.services.policy_document_evidence_service import (
        extract_policy_document_evidence,
    )

    fixture = tabelas()[apelido]
    paginas = [{"page_number": 1, "content": "\n".join(fixture["linhas"])}]
    itens = extract_policy_document_evidence(
        paginas,
        question="quais sao as coberturas dessa apolice?",
        document_id="doc-de-teste",
        company_id="tenant-de-teste",
        policy_locator=LOCATOR,
        content_hash="hash-de-teste",
    )
    return itens, fixture


def pack_do_caminho_inteiro(apelido, *, com_documento=True, itens_crus=None):
    """`_build_evidence_pack` de PRODUCAO + o documento lido pelo EXTRATOR."""
    from app.api import infocap_connector as CN

    dados = golden()[apelido]
    documento_cru = _HA.documento_cru(dados)
    itens = itens_crus if itens_crus is not None else _HA.itens_crus(apelido, dados)
    pack = CN._build_evidence_pack(documento_cru, None, None, True,
                                   envelope={"documento": [documento_cru]}, items=itens)
    if com_documento:
        evidencia, fixture = evidencia_do_pdf(apelido)
        pack["official_policy_document_evidence"] = {
            "evidence_items": evidencia,
            "page_count": fixture["paginas"],
            "extraction_mode": fixture["parser"],
        }
    return pack, dados


def apolice_do_caminho_inteiro(apelido, **kw):
    from app.providers.infocap_policy_provider import apolice_reconciliada_do_pack

    pack, dados = pack_do_caminho_inteiro(apelido, **kw)
    return apolice_reconciliada_do_pack(pack), pack, dados


def briefing_do_caminho_inteiro(apelido, pergunta="quais sao as coberturas dessa apolice?"):
    """O BRIEFING que chega ao modelo — pelo motor inteiro, sem atalho."""
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool
    from app.services.policy_answer_composer import compose_policy_answer_with_meta

    pack, dados = pack_do_caminho_inteiro(apelido)
    resultado = {
        "ok": True,
        "status": "found",
        "selected": {
            "policy_number": "900000000000001",   # ⛔ sintetico
            "insurer_key": dados["seguradora_abrev"],
            "product": dados["ramo_abrev"],
            "valid_from": dados["vigencia"]["inicio"],
            "valid_to": dados["vigencia"]["fim"],
            "policy_status": dados["status_cru_do_fornecedor"],
        },
        "policy_evidence_pack": pack,
        "auto_selected_reason": "única apólice vigente do cliente",
    }
    meta = compose_policy_answer_with_meta(question=pergunta, result=resultado)
    return InfocapPolicyLookupTool._build_llm_briefing(
        resultado, meta, pergunta, client_facing=False), pack, dados


def por_kind(itens):
    contagem: dict = {}
    for item in itens:
        estruturado = item.get("structured") or {}
        kind = str(estruturado.get("kind") or "")
        if kind:
            contagem[kind] = contagem.get(kind, 0) + 1
    return contagem


def estruturados(itens, kind):
    return [i.get("structured") or {} for i in itens
            if (i.get("structured") or {}).get("kind") == kind]


# ===========================================================================
# [GD2a] AS DUAS TABELAS — o extrator REAL sobre o texto REAL
# ===========================================================================
def gate_GD2a():
    _p("\n[GD2a] AS DUAS TABELAS -- o extrator sobre as linhas CRUAS dos dois PDFs")

    itens_hdi, fixture_hdi = evidencia_do_pdf("hdi_residencial")
    contagem = por_kind(itens_hdi)
    medir("hdi_kinds", contagem)
    check("[GD2a] 🔴 HDI: 10 `coverage_row` (o layout sem `R$` — eram ZERO em 14/09)",
          contagem.get("coverage_row") == 10, contagem)
    check("[GD2a] HDI: 6 `deductible_prose` (a franquia da HDI vem em PROSA)",
          contagem.get("deductible_prose") == 6, contagem)
    check("[GD2a] HDI: 4 `installment_row` (e delas sai a forma de pagamento)",
          contagem.get("installment_row") == 4, contagem)

    soma = sum((_numero(e.get("premium")) for e in estruturados(itens_hdi, "coverage_row")),
               Decimal("0"))
    medir("hdi_soma_dos_premios", str(soma))
    check("[GD2a] 🔴 HDI: Σ dos premios das 10 linhas = R$ 306,60 = o premio liquido",
          soma == Decimal(str(fixture_hdi["esperado"]["soma_dos_premios"])), soma)

    itens_all, fixture_all = evidencia_do_pdf("allianz_condominio")
    contagem_all = por_kind(itens_all)
    medir("allianz_kinds", contagem_all)
    check("[GD2a] 🔴 Allianz: 20 `coverage_row` + 1 `assistance_plan` (era 1, e era "
          "'Premio Liquido')",
          contagem_all.get("coverage_row") == 20 and contagem_all.get("assistance_plan") == 1,
          contagem_all)
    soma_all = sum(
        (_numero(e.get("premium")) for e in
         estruturados(itens_all, "coverage_row") + estruturados(itens_all, "assistance_plan")),
        Decimal("0"))
    medir("allianz_soma_dos_premios", str(soma_all))
    check("[GD2a] Allianz: Σ = R$ 24.960,60 = o premio liquido",
          soma_all == Decimal(str(fixture_all["esperado"]["soma_dos_premios"])), soma_all)

    # 🔴 A LINHA QUE NAO PODE ESTAR LA. Cada rotulo de PREMIO/IOF/total tem de
    #    ficar fora das coberturas das DUAS apolices.
    rotulos = [str(e.get("label") or "") for e in estruturados(itens_all, "coverage_row")]
    rotulos += [str(e.get("label") or "") for e in estruturados(itens_hdi, "coverage_row")]
    proibidos = [r for r in rotulos if any(
        t in r.lower() for t in ("prêmio", "premio", "total a pagar", "custo d", "i.o.f",
                                 "limite máximo", "limite maximo", "adicional de parcel"))]
    medir("linhas_de_premio_lidas_como_cobertura", len(proibidos))
    check("[GD2a] 🔴 nenhuma linha de PREMIO/IOF/total virou cobertura", not proibidos, proibidos)

    # 🔴 O PAR que da direito a conclusao: o detector de rotulo-que-nao-e-cobertura
    #    CONSEGUE dizer sim e CONSEGUE dizer nao.
    from app.services.policy_document_evidence_service import rotulo_nao_e_cobertura

    check("[GD2a] PAR-A: 'Premio Liquido' e recusado, COM motivo escrito",
          bool(rotulo_nao_e_cobertura("Prêmio Líquido")),
          rotulo_nao_e_cobertura("Prêmio Líquido"))
    check("[GD2a] PAR-B: e 'Danos Eletricos' NAO e recusado",
          rotulo_nao_e_cobertura("Danos Elétricos") is None)


# ===========================================================================
# [GD2b] AS DUAS FONTES — 550 x 600 e 19,17 x 17,25, com origem em cada
# ===========================================================================
def gate_GD2b():
    _p("\n[GD2b] AS DUAS FONTES -- franquia 550 x 600 e premio 19,17 x 17,25")
    apolice, _pack, _dados = apolice_do_caminho_inteiro("hdi_residencial")
    medir("hdi_coberturas_reconciliadas", len(apolice.coberturas))
    check("[GD2b] a HDI reconciliada tem 10 coberturas (6 do cadastro + 4 so do PDF)",
          len(apolice.coberturas) == 10, len(apolice.coberturas))

    danos = [c for c in apolice.coberturas if "Danos Eletricos" in c.rotulo]
    if not check("[GD2b] a cobertura de Danos Eletricos existe", len(danos) == 1,
                 [c.rotulo for c in apolice.coberturas]):
        return
    cobertura = danos[0]

    campos = {d.campo for d in cobertura.divergencias}
    check("[GD2b] 🔴 a MESMA cobertura diverge em DOIS campos: franquia E premio",
          {"franquia", "prêmio"} <= campos, campos)
    franquia = next(d for d in cobertura.divergencias if d.campo == "franquia")
    check("[GD2b] 🔴 a franquia do CADASTRO (550) nao foi apagada",
          "550" in str(franquia.valor_sistema_de_gestao), franquia.valor_sistema_de_gestao)
    check("[GD2b] 🔴 e a do DOCUMENTO (600) esta la, em prosa",
          "600,00" in str(franquia.valor_documento_oficial), franquia.valor_documento_oficial)
    premio = next(d for d in cobertura.divergencias if d.campo == "prêmio")
    check("[GD2b] premio: 19,17 (cadastro) x 17,25 (documento) — os dois",
          str(premio.valor_sistema_de_gestao) == "19.17"
          and str(premio.valor_documento_oficial) == "17.25",
          (premio.valor_sistema_de_gestao, premio.valor_documento_oficial))
    check("[GD2b] a franquia que FICA no campo vem do documento, e diz isso",
          cobertura.franquia.origem == "documento_oficial"
          and "600,00" in str(cobertura.franquia.valor),
          (cobertura.franquia.origem, cobertura.franquia.valor))

    # 🔴 O ELO: a divergencia CHEGA ao texto que o modelo le.
    briefing, _p2, _d2 = briefing_do_caminho_inteiro("hdi_residencial")
    trecho = briefing[briefing.find("Danos Eletricos"):][:700]
    check("[GD2b] 🔴 O ELO: as DUAS aparecem no briefing (600,00 e 550,00)",
          "600,00" in trecho and "550,00" in trecho, trecho[:400])
    check("[GD2b] e a discordancia e DITA, com as duas fontes nomeadas",
          "as duas fontes discordam" in trecho and "o documento oficial diz" in trecho
          and "o sistema de gestão diz" in trecho, trecho[:400])
    check("[GD2b] ⛔ e o briefing NAO escolhe por conta do corretor",
          "nao escolha por conta" in briefing, briefing[-1200:])

    # 📊 A regra das franquias em prosa e FALSIFICAVEL, e duas das tres
    #    associacoes CONFIRMAM o cadastro (Incendio 350, Vidros 150).
    por_rotulo = {c.rotulo: str(c.franquia.valor) for c in apolice.coberturas}
    check("[GD2b] 🔴 CONTROLE: Incendio -> minimo R$ 350,00 = o que o cadastro ja dizia",
          "350,00" in por_rotulo.get("Incendio", ""), por_rotulo.get("Incendio"))
    check("[GD2b] 🔴 CONTROLE: Quebra de Vidros -> R$ 150,00 = o que o cadastro ja dizia",
          "150,00" in por_rotulo.get("Quebra de Vidros", ""), por_rotulo.get("Quebra de Vidros"))
    sobra = apolice.sinal("franquia_em_prosa_sem_dono")
    medir("hdi_franquias_em_prosa_sem_dono", (sobra.detalhe or {}).get("quantidade") if sobra else 0)
    check("[GD2b] ⛔ as 3 prosas que o documento nao sabe de quem sao NAO foram adivinhadas: "
          "viram sinal", sobra is not None and (sobra.detalhe or {}).get("quantidade") == 3,
          sobra)


# ===========================================================================
# [GD2c] A FORMA DE PAGAMENTO — das PARCELAS, e o cabecalho declarado
# ===========================================================================
def gate_GD2c():
    _p("\n[GD2c] A FORMA -- Cartao (das PARCELAS) x Boleto (o cabecalho que mente)")
    apolice, pack, _dados = apolice_do_caminho_inteiro("hdi_residencial")

    check("[GD2c] 📊 o cabecalho do fornecedor diz 'Boleto Bancário'",
          (pack.get("premium_summary") or {}).get("payment_method") == "Boleto Bancário",
          (pack.get("premium_summary") or {}).get("payment_method"))
    check("[GD2c] 🔴 e a forma de pagamento da apolice e 'Cartão de Crédito' — das PARCELAS",
          str(apolice.forma_de_pagamento) == "Cartão de Crédito", apolice.forma_de_pagamento)
    sinal = apolice.sinal("cabecalho_divergente")
    check("[GD2c] o sinal `cabecalho_divergente` esta aceso, com as duas pontas",
          sinal is not None
          and (sinal.detalhe or {}).get("no_cabecalho") == "Boleto Bancário"
          and (sinal.detalhe or {}).get("nas_parcelas") == ["Cartão de Crédito"], sinal)

    briefing, _p2, _d2 = briefing_do_caminho_inteiro("hdi_residencial")
    check("[GD2c] 🔴 O ELO: o briefing diz Cartao e diz que leu das PARCELAS",
          "forma_de_pagamento: Cartão de Crédito (lida das PARCELAS)" in briefing,
          briefing[briefing.find("forma_de_pagamento"):][:260])
    check("[GD2c] e o cabecalho divergente e DECLARADO, nao apagado",
          "o cabecalho do cadastro diz Boleto Bancário" in briefing,
          briefing[briefing.find("forma_de_pagamento"):][:260])

    # 🔴 O PAR: na Allianz o cabecalho e as parcelas CONCORDAM (boleto nos dois)
    #    -> nenhum sinal. Sem este par, "o sinal acendeu" tanto poderia ser a
    #    divergencia quanto um sinal que acende sempre.
    outra, _pa, _da = apolice_do_caminho_inteiro("allianz_condominio")
    check("[GD2c] 🔴 PAR: Allianz — cabecalho e parcelas concordam -> SEM sinal",
          outra.sinal("cabecalho_divergente") is None
          and str(outra.forma_de_pagamento) == "Boleto Bancário",
          (outra.sinal("cabecalho_divergente"), outra.forma_de_pagamento))

    # 📊 As parcelas do PDF tambem foram lidas, e concordam com o cadastro.
    from app.providers.infocap_policy_provider import apolice_documental_do_pack

    documental = apolice_documental_do_pack(pack)
    medir("hdi_parcelas_lidas_do_pdf", len(documental.parcelas) if documental else 0)
    check("[GD2c] as 4 parcelas do PDF foram lidas, e a forma delas e Cartao",
          documental is not None and len(documental.parcelas) == 4
          and all(str(p.forma_de_pagamento.valor) == "Cartão de Crédito"
                  for p in documental.parcelas),
          documental.parcelas if documental else None)


# ===========================================================================
# [GD2d] OS CAMPOS QUE NINGUEM LIA — `tabela_itens` e `sit_renovacao_txt`
# ===========================================================================
def gate_GD2d():
    _p("\n[GD2d] OS CAMPOS -- `tabela_itens` e `sit_renovacao_txt` chegam com VALOR")
    apolice, pack, dados = apolice_do_caminho_inteiro("hdi_residencial", com_documento=False)

    sinais_do_provedor = pack.get("provider_signals") or {}
    medir("provider_signals_no_pack", sorted(sinais_do_provedor.keys()))
    check("[GD2d] 🔴 o pack carrega `tabela_itens` com VALOR (era so um booleano)",
          sinais_do_provedor.get("tabela_itens") == "PACOTE", sinais_do_provedor)
    check("[GD2d] e carrega `sit_renovacao_txt` com VALOR",
          bool(sinais_do_provedor.get("sit_renovacao_txt")), sinais_do_provedor)

    plano = apolice.plano_de_assistencia
    check("[GD2d] 🔴 `tabela_itens` vira o NOME do plano, com origem do cadastro",
          plano is not None and plano.nome.valor == "PACOTE"
          and plano.nome.origem == "sistema_de_gestao", plano)
    check("[GD2d] ⛔ e o estado e `nao_sabemos_ainda`: nome de plano NAO e lista de servicos",
          plano is not None and plano.estado == "nao_sabemos_ainda", plano)

    sinal = apolice.sinal("situacao_de_renovacao")
    check("[GD2d] `sit_renovacao_txt` vira SINAL, com o texto da fonte",
          sinal is not None and str((sinal.detalhe or {}).get("texto") or "").strip() != "",
          sinal)

    # 🔴 O PAR QUE IMPORTA: o sinal NAO decide vigencia. 📊 As duas apolices do
    #    golden trazem "Recebido e nao entregue ao cliente" — um estado de
    #    ENTREGA DE DOCUMENTO. Quem decide e `classificar_vigencia`, por DATA.
    from app.providers.policy_data_provider import classificar_vigencia

    texto = str((sinal.detalhe or {}).get("texto") or "") if sinal else ""
    check("[GD2d] 🔴 o texto do fornecedor nao diz vigencia nenhuma "
          "('Recebido e nao entregue' e sobre o DOCUMENTO)",
          "vigente" not in texto.lower(), texto)
    check("[GD2d] 🔴 e a vigencia da apolice veio das DATAS, nao do texto",
          apolice.vigencia == classificar_vigencia(
              dados["vigencia"]["inicio"], dados["vigencia"]["fim"], dados["cancelado"]),
          (apolice.vigencia, dados["vigencia"]))

    briefing, _p2, _d2 = briefing_do_caminho_inteiro("hdi_residencial")
    check("[GD2d] 🔴 O ELO: o plano chega ao modelo COM o aviso de que e so o nome",
          "plano_de_assistencia:" in briefing
          and "nao prometa servico" in briefing,
          briefing[briefing.find("plano_de_assistencia"):][:300])


# ===========================================================================
# [GD2e] A PROSA — `itens[].observacoes` vira franquia quando NAO ha valor
# ===========================================================================
def _itens_com_observacoes(dados, *, prosa):
    """O `/itens` da HDI com o campo `observacoes` preenchido.

    📊 O acervo real de `/itens` que temos mascarado (a Allianz) NAO tem o campo
    — por isso a prosa e SINTETICA e esta declarada aqui. O que o gate mede e o
    CANO: se `observacoes` existir na fonte, ele chega ao corretor. ⚠️ E o PAR
    e o que da direito a conclusao: a garantia que JA tem franquia nao e
    sobrescrita pela prosa.
    """
    garantias = [dict(g) for g in dados["cadastro_sistema_de_gestao"]["garantias"]]
    return [{"item": 1, "observacoes": prosa, "garantias": garantias}]


def gate_GD2e():
    _p("\n[GD2e] A PROSA -- `itens[].observacoes` vira franquia so onde NAO ha valor")
    from app.providers.infocap_policy_provider import apolice_do_pack

    dados = golden()["hdi_residencial"]
    prosa = "15% Sobre os Prejuizos Indenizaveis, com o Minimo de R$ 999,00"
    itens = _itens_com_observacoes(dados, prosa=prosa)
    pack, _d = pack_do_caminho_inteiro("hdi_residencial", com_documento=False, itens_crus=itens)

    secoes = pack.get("coverage_sections") or []
    medir("coberturas_com_observacoes_no_pack",
          len([s for s in secoes if s.get("item_observacoes")]))
    check("[GD2e] 🔴 `observacoes` chega ao pack, por cobertura (era descartado)",
          all(s.get("item_observacoes") == prosa for s in secoes), secoes[:2])
    riscos = pack.get("risk_objects") or []
    check("[GD2e] e tambem no objeto do risco",
          bool(riscos) and riscos[0].get("observacoes") == prosa, riscos)

    apolice = apolice_do_pack(pack)
    sem_valor = [c for c in apolice.coberturas if c.rotulo == "ROUBO"]
    com_valor = [c for c in apolice.coberturas if c.rotulo == "DANOS ELÉTRICOS"]
    check("[GD2e] 🔴 a cobertura SEM franquia no cadastro recebe a prosa",
          len(sem_valor) == 1 and str(sem_valor[0].franquia.valor) == prosa,
          sem_valor[0].franquia if sem_valor else None)
    check("[GD2e] 🔴 PAR: a cobertura que JA tem franquia mantem o valor dela (550), "
          "nao a prosa",
          len(com_valor) == 1 and "550" in str(com_valor[0].franquia.valor),
          com_valor[0].franquia if com_valor else None)

    # ⛔ O par de controle do CANO: sem `observacoes`, ninguem inventa prosa.
    pack_sem, _d2 = pack_do_caminho_inteiro("hdi_residencial", com_documento=False)
    apolice_sem = apolice_do_pack(pack_sem)
    roubo = [c for c in apolice_sem.coberturas if c.rotulo == "ROUBO"]
    check("[GD2e] ⛔ CONTROLE: sem `observacoes`, a franquia continua indisponivel",
          len(roubo) == 1 and not roubo[0].franquia.tem_valor,
          roubo[0].franquia if roubo else None)


# ===========================================================================
# [GD2f] A ALLIANZ — 21 coberturas e a carencia que nao vira franquia
# ===========================================================================
def gate_GD2f():
    _p("\n[GD2f] A ALLIANZ -- 21 coberturas, e '168 Hrs' continua TEXTO")
    apolice, pack, _dados = apolice_do_caminho_inteiro("allianz_condominio")
    medir("allianz_coberturas_reconciliadas", len(apolice.coberturas))
    check("[GD2f] 📊 o cadastro traz 15", len(pack.get("coverage_sections") or []) == 15,
          len(pack.get("coverage_sections") or []))
    check("[GD2f] 🔴 e a apolice reconciliada tem 21 (as 6 que so o documento tem entram)",
          len(apolice.coberturas) == 21, [c.rotulo for c in apolice.coberturas])
    rotulos = [c.rotulo for c in apolice.coberturas]
    check("[GD2f] 🔴 'Prêmio Líquido' NAO esta entre as coberturas",
          not any("Líquido" in r or "Liquido" in r for r in rotulos), rotulos)

    fixas = [c for c in apolice.coberturas if "Despesas Fixas" in c.rotulo]
    check("[GD2f] `Despesas Fixas` existe", len(fixas) == 1, rotulos)
    if fixas:
        valor = str(fixas[0].franquia.valor)
        check("[GD2f] 🔴 e a franquia dela e o TEXTO '168 Hrs' — e CARENCIA, nao dinheiro",
              "168 Hrs" in valor, valor)
        check("[GD2f] ⛔ e nenhum R$ foi inventado nela", "R$" not in valor, valor)

    assistencia = [c for c in apolice.coberturas if "Assistência 24h" in c.rotulo]
    check("[GD2f] 🔴 a `Assistência 24h` do PDF (R$ 23,88) nao virou so 'plano': "
          "ela e cobertura E a divergencia com o cadastro (0,00) e dita",
          len(assistencia) == 1
          and str(assistencia[0].premio.valor) == "23.88"
          and any(d.campo == "prêmio" for d in assistencia[0].divergencias),
          assistencia[0] if assistencia else None)

    briefing, _p2, _d2 = briefing_do_caminho_inteiro("allianz_condominio")
    check("[GD2f] O ELO: o briefing anuncia as 21 e manda listar TODAS",
          "coberturas_item_a_item (21 contratadas" in briefing
          and "LISTE TODAS na resposta" in briefing,
          briefing[briefing.find("coberturas_item_a_item"):][:220])


# ===========================================================================
# [GD2g] OS AVISOS — escrever o sinal nao era MOSTRAR o sinal
# ===========================================================================
#
# 🔴 📊 Medido em 14/09/2026: a porta escreve 5 sinais e o briefing lia **2**.
# `rotulo_ambiguo`, `franquia_em_prosa_sem_dono` e `situacao_de_renovacao` eram
# gravados no modelo e morriam ali — nenhum leitor, em lugar nenhum. E a
# pendencia `P-E0011-FRANQUIA-EM-PROSA-SEM-DONO` afirmava, com todas as letras,
# *"o corretor VE o sinal"*: ele nunca viu.
#
# ⚠️ E o que ja tinha linha PROPRIA continua com ela, e nao entra duas vezes:
# `cadastro_incompleto` (`aviso_sobre_o_cadastro`) e `cabecalho_divergente`
# (dentro de `forma_de_pagamento`). Um corretor que le o mesmo aviso duas vezes
# aprende a nao ler nenhum.
def _briefing_de(pack, dados):
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool
    from app.services.policy_answer_composer import compose_policy_answer_with_meta

    pergunta = "quais sao as coberturas dessa apolice?"
    resultado = {
        "ok": True, "status": "found",
        "selected": {
            "policy_number": "900000000000001",   # ⛔ sintetico
            "insurer_key": dados["seguradora_abrev"], "product": dados["ramo_abrev"],
            "valid_from": dados["vigencia"]["inicio"], "valid_to": dados["vigencia"]["fim"],
            "policy_status": dados["status_cru_do_fornecedor"],
        },
        "policy_evidence_pack": pack,
        "auto_selected_reason": "única apólice vigente do cliente",
    }
    meta = compose_policy_answer_with_meta(question=pergunta, result=resultado)
    return InfocapPolicyLookupTool._build_llm_briefing(
        resultado, meta, pergunta, client_facing=False)


def _bloco_de_avisos(briefing):
    """As linhas `- …` da secao `avisos_da_apolice` (vazio quando nao existe)."""
    texto = str(briefing or "")
    inicio = texto.find("avisos_da_apolice")
    if inicio < 0:
        return []
    linhas = []
    for linha in texto[inicio:].split("\n")[1:]:
        if linha.startswith("- "):
            linhas.append(linha)
        else:
            break
    return linhas


def gate_GD2g():
    _p("\n[GD2g] OS AVISOS -- os 5 sinais da porta chegam ao corretor, em prosa")
    from app.providers.policy_data_provider import Sinal, frase_do_sinal

    # ① A HDI real, pelo motor: as 3 franquias sem dono CHEGAM ao briefing.
    apolice, pack, dados = apolice_do_caminho_inteiro("hdi_residencial")
    codigos = [s.codigo for s in apolice.sinais]
    medir("sinais_na_apolice_hdi", len(codigos))
    check("[GD2g] 📊 a HDI real acende 4 sinais na porta",
          set(codigos) == {"situacao_de_renovacao", "cabecalho_divergente",
                           "franquia_em_prosa_sem_dono", "cadastro_incompleto"},
          codigos)

    briefing = _briefing_de(pack, dados)
    avisos = _bloco_de_avisos(briefing)
    medir("avisos_no_briefing_hdi", len(avisos))
    if not check("[GD2g] 🔴 o briefing TEM a secao `avisos_da_apolice`", bool(avisos),
                 briefing[:500]):
        return
    texto_dos_avisos = "\n".join(avisos)
    check("[GD2g] 🔴 e ela traz as 3 franquias que o cadastro nao tem dono para",
          "3 franquias" in texto_dos_avisos
          and "R$ 800,00" in texto_dos_avisos
          and "R$ 650,00" in texto_dos_avisos
          and "R$ 300,00" in texto_dos_avisos, texto_dos_avisos)
    check("[GD2g] e ela DIZ o que fazer com isso (confirmar na seguradora)",
          "Confirme na seguradora" in texto_dos_avisos, texto_dos_avisos)
    check("[GD2g] 🔴 `situacao_de_renovacao` tambem chega — e DIZ que nao decide vigencia",
          "não decide vigência" in texto_dos_avisos, texto_dos_avisos)

    # ⚠️ E o que ja tem linha propria NAO se repete.
    check("[GD2g] `cadastro_incompleto` continua na linha propria dele, e so nela",
          "aviso_sobre_o_cadastro:" in briefing
          and not any("prêmio líquido na soma" in a for a in avisos),
          avisos)
    check("[GD2g] `cabecalho_divergente` idem (dentro de `forma_de_pagamento`)",
          "o cabecalho do cadastro diz" in briefing
          and not any("cabeçalho do cadastro e as parcelas discordam" in a for a in avisos),
          avisos)

    # ⛔ Nenhum aviso nomeia o fornecedor nem carrega codigo em `snake_case`.
    check("[GD2g] ⛔ nenhum aviso nomeia o fornecedor",
          "InfoCap" not in texto_dos_avisos, texto_dos_avisos)
    check("[GD2g] ⛔ e nenhum imprime o codigo cru do sinal",
          not any("_" in a.split("«")[0] for a in avisos), avisos)

    # ② A SONDA: `rotulo_ambiguo` — 1 linha de cadastro, 2 candidatas do MESMO
    #    grupo e SEM limite para desempatar. 📊 Nenhuma das duas apolices reais
    #    produz este sinal; sem a sonda ele nunca seria exercitado.
    sonda_pack = dict(pack)
    sonda_pack["coverage_sections"] = [
        {"label": "VIDROS", "amount": None, "deductible": None, "premium": "R$ 11,50"},
    ]
    sonda_pack["official_policy_document_evidence"] = {
        "evidence_items": [
            {"page_number": 1, "evidence_type": "coverage",
             "structured": {"kind": "coverage_row", "label": "Vidros",
                            "lmi": None, "premium": "R$ 11,50"}},
            {"page_number": 1, "evidence_type": "coverage",
             "structured": {"kind": "coverage_row", "label": "Vidros",
                            "lmi": None, "premium": "R$ 47,36"}},
        ],
        "page_count": 1, "extraction_mode": "direct_text",
    }
    from app.providers.infocap_policy_provider import apolice_reconciliada_do_pack

    da_sonda = apolice_reconciliada_do_pack(sonda_pack)
    ambiguo = da_sonda.sinal("rotulo_ambiguo")
    check("[GD2g] 🔴 SONDA: 2 candidatas do mesmo grupo sem limite -> `rotulo_ambiguo`",
          ambiguo is not None, [s.codigo for s in da_sonda.sinais])
    avisos_da_sonda = _bloco_de_avisos(_briefing_de(sonda_pack, dados))
    check("[GD2g] 🔴 e ele CHEGA ao briefing, com o rotulo e as candidatas",
          any("VIDROS" in a and "Vidros" in a and "não escolha por conta" in a
              for a in avisos_da_sonda), avisos_da_sonda)

    # 🔴 O PAR DE CONTROLE: uma apolice SEM sinal nenhum nao ganha a secao.
    #    Sem ele, "a secao apareceu" tanto poderia ser o sinal quanto a secao
    #    ser incondicional.
    controle_pack = dict(sonda_pack)
    controle_pack["official_policy_document_evidence"] = {
        "evidence_items": [
            {"page_number": 1, "evidence_type": "coverage",
             "structured": {"kind": "coverage_row", "label": "Vidros",
                            "lmi": "R$ 5.000,00", "premium": "R$ 11,50"}},
        ],
        "page_count": 1, "extraction_mode": "direct_text",
    }
    controle_pack["premium_summary"] = {}
    controle_pack["installments"] = []
    # ⚠️ `provider_signals` e de onde vem `situacao_de_renovacao`: a apolice de
    #    CONTROLE e uma em que a fonte nao mandou nenhum desses campos.
    controle_pack["provider_signals"] = {}
    de_controle = apolice_reconciliada_do_pack(controle_pack)
    check("[GD2g] PAR-CONTROLE: a apolice de controle nao acende sinal nenhum",
          not de_controle.sinais, [s.codigo for s in de_controle.sinais])
    check("[GD2g] PAR-CONTROLE: e o briefing dela NAO tem `avisos_da_apolice`",
          not _bloco_de_avisos(_briefing_de(controle_pack, dados)),
          _bloco_de_avisos(_briefing_de(controle_pack, dados)))

    # 🔴 O sinal DESCONHECIDO nao some: ele vira frase generica, em palavras.
    generica = frase_do_sinal(Sinal("um_sinal_que_ninguem_traduziu", {}))
    check("[GD2g] sinal sem traducao vira frase generica, sem `snake_case`",
          "um sinal que ninguem traduziu" in generica and "_" not in generica,
          generica)


GATES = {
    "GD2a": gate_GD2a,
    "GD2b": gate_GD2b,
    "GD2c": gate_GD2c,
    "GD2d": gate_GD2d,
    "GD2e": gate_GD2e,
    "GD2f": gate_GD2f,
    "GD2g": gate_GD2g,
}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
MUTACOES = [
    # (a) o `forma_pag` do CABECALHO voltando a vencer -> o corretor manda o
    #     segurado pagar boleto de uma apolice que esta no cartao.
    ("M-D2a", "app/agents/tools/infocap_tool.py",
     "            forma = apolice.forma_de_pagamento",
     '            forma = (pack.get("premium_summary") or {}).get("payment_method")',
     "GD2c"),
    # (b) `observacoes` descartado -> a franquia em prosa some.
    ("M-D2b", "app/providers/infocap_policy_provider.py",
     '    for secao in (pack or {}).get("coverage_sections") or []:',
     "    for secao in []:",
     "GD2e"),
    # (c) a divergencia de franquia resolvida em SILENCIO (o documento vence e o
    #     cadastro desaparece) -> o corretor nunca sabe que as fontes discordam.
    ("M-D2c", "app/providers/policy_data_provider.py",
     "        if de_corp is not None and do_pdf is not None and de_corp != do_pdf:",
     "        if False:",
     "GD2b"),
    # (d) "Premio Liquido" aceito como cobertura -> volta o 1 de 21 de 14/09.
    ("M-D2d", "app/services/policy_document_evidence_service.py",
     '    chave = _rotulo_chave(rotulo)\n    if not chave:',
     "    return None\n    chave = _rotulo_chave(rotulo)\n    if not chave:",
     "GD2a"),
    # 🔴 (f) a secao `avisos_da_apolice` sai do briefing -> os 3 sinais sem linha
    #     propria voltam a ser escritos e nao lidos. 📊 E o estado de 14/09/2026.
    ("M-D2f", "app/agents/tools/infocap_tool.py",
     "            avisos = [\n"
     "                frase_do_sinal(sinal)\n"
     "                for sinal in (getattr(apolice, \"sinais\", ()) or ())\n"
     "                if sinal.codigo not in ja_ditos\n"
     "            ]",
     "            avisos = []",
     "GD2g"),
    # 🔴 (g) a traducao some e o codigo cru vai ao modelo -> `snake_case` no
    #     texto do produto, e um aviso que o corretor nao entende.
    ("M-D2g", "app/providers/policy_data_provider.py",
     '    if codigo == "franquia_em_prosa_sem_dono":',
     '    if False:',
     "GD2g"),
    # (e) o extrator volta a exigir `R$` -> a HDI perde as 10 linhas de uma vez.
    ("M-D2e", "app/services/policy_document_evidence_service.py",
     '    if "R$" not in texto:',
     '    if "R$" not in texto and False:',
     "GD2a"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011d2").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  M-D2 -- A DIVERGENCIA APARECE INTEIRA  (SPEC-EXTRA-001.1 BLOCO D)")
        _p("=" * 78)
    _HA._bloquear_a_rede()
    try:
        for gid, fn in GATES.items():
            if so and gid != so:
                continue
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                import traceback
                check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                      "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    finally:
        _HA._devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_a_divergencia_aparece_inteira():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
