# -*- coding: utf-8 -*-
"""SPEC-130-B · F5 — A COSTURA: a saída REAL de uma fatia é a entrada da outra.

    PDF (💭 sintético) → document_service.extrair_paginas_tolerante            (F1, REAL)
      → ler_documento_de_seguro (regex → juiz → modelo DUBLÊ → juiz)           (F1, REAL)
      → pack.official_policy_document_evidence → apolice_documental_do_pack    (F2, REAL)
      → reconciliar                                                           (F1, REAL)
      → multicalculo.pedido.de_apolice (condomínio)                           (F4, REAL)
    e o MESMO resultado → ficha_para_o_modelo / conteudo_do_anexo (F3) sem PII,
    e → infocap_tool._com_documento → invocation_recorder._resumo_da_saida   (C1, o registro)

E os consertos da costura: C2 (leitura que não fechou, 0 linhas → o sinal acende), C3 (`/itens` do
veículo com `data=`), C4 (o nome do arquivo mascarado no texto do turno).

⛔ Dublê SÓ na borda: o modelo, o HTTP da InfoCap. Nenhuma chamada real, nenhum banco.
Rodar:  cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_spec130b_costura.py -q
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

CNPJ = "12.345.678/0001-90"          # 💭 sintético
TELEFONE = "(11) 98765-4321"         # 💭 sintético
CPF = "123.456.789-09"               # 💭 sintético

# 💭 layout "Tokio": LMI e prêmio sem R$ — o regex lê ZERO linhas, o modelo (dublê) lê as duas
TOKIO_COND = [
    "APOLICE DE SEGURO CONDOMINIO",
    "Segurado: CONDOMINIO EXEMPLO CNPJ " + CNPJ,
    "Sindico: telefone " + TELEFONE,
    "Local do risco CEP: 88000-000",
    "Coberturas Limite Premio",
    "Incendio, Raio e Explosao 5.000.000,00 16.771,96",
    "Danos Eletricos 600.000,00 15.103,93",
    "Premio Liquido R$ 31.875,89",
]
ESPERADO = Decimal("31875.89")


def _pdf(linhas):
    import fitz

    doc = fitz.open()
    pagina = doc.new_page()
    for i, linha in enumerate(linhas):
        pagina.insert_text((50, 72 + 14 * i), linha, fontsize=9)
    dados = doc.tobytes()
    doc.close()
    return dados


class _Modelo:
    """Dublê do degrau 2: lê SÓ o texto que recebe e devolve `<rótulo> <limite> <prêmio>` com o trecho literal."""

    def __init__(self, cego: bool = False):
        self.chamadas, self.textos, self.cego = 0, [], cego

    async def __call__(self, texto, *, company_id, **_k):
        self.chamadas += 1
        self.textos.append(texto)
        linhas = []
        for bruta in ([] if self.cego else texto.splitlines()):
            m = re.match(r"^(.+?) ([\d.]+,\d{2}) ([\d.]+,\d{2})$", bruta.strip())
            if m:
                linhas.append({"pagina": 1, "rotulo": m.group(1), "limite": m.group(2), "premio": m.group(3),
                               "trecho": bruta.strip()})
        return json.dumps({"linhas": linhas})


def _ler(linhas, *, esperado=ESPERADO, modelo=None):
    from app.services.document_service import extrair_paginas_tolerante
    from app.services.policy_document_evidence_service import ler_documento_de_seguro

    pdf = _pdf(linhas)
    pages, parser, total = extrair_paginas_tolerante(pdf)
    return asyncio.run(ler_documento_de_seguro(
        pages, company_id="corretora-A", premio_esperado=esperado, fonte_do_esperado="corp", file_bytes=pdf,
        total_paginas=total, parser_por_pagina=parser, leitor_modelo=modelo or _Modelo(),
        document_id="doc-costura", content_hash="h" * 64,
        policy_locator={"provider": "infocap", "codfil": "1", "nosnum": "999001"}))


def _pack(resultado):
    return {"official_policy_document_evidence": {**resultado, "ok": True, "document_status": "evidence_ready",
                                                  "cache_status": "miss"}}


def _apolice_cond(coberturas=()):
    from app.providers.policy_data_provider import (
        Apolice, RamoCanonico, SeguradoraCanonica, Vigencia,
    )

    return Apolice(apolice_ref="sintetica:1", numero_humano="0000000001",
                   seguradora=SeguradoraCanonica(chave="PORT", coenti="05886"),
                   ramo=RamoCanonico(abreviatura="COND"),
                   vigencia=Vigencia(inicio=date(2025, 11, 1), fim=date(2026, 11, 1), situacao="VIGENTE"),
                   coberturas=tuple(coberturas))


def _cob(rotulo, limite, premio):
    from app.providers.policy_data_provider import CampoComOrigem, Cobertura, indisponivel_por, normalizar_rotulo

    return Cobertura(rotulo=rotulo, rotulo_normalizado=normalizar_rotulo(rotulo),
                     limite=CampoComOrigem(valor=Decimal(limite), origem="sistema_de_gestao"),
                     franquia=indisponivel_por(),
                     premio=CampoComOrigem(valor=Decimal(premio), origem="sistema_de_gestao"))


PERFIL_COND = {
    "segurado": {"cpf_cnpj": "11.222.333/0001-81", "nome": "Condominio Sintetico"},
    "risco": {"logradouro": "Rua Sintetica", "bairro": "Centro", "cidade": "Cidade Sintetica", "uf": "SC",
              "tipo_imovel": "residencial", "estrutura": "vertical", "ano_fundacao": "2005", "blocos": "1",
              "pavimentos": "5", "elevadores": 0},
    "renovacao": {"bonus_anterior": 5, "sinistros_anterior": 0},
}


# =====================================================================================================================
# C8 · O FIO INTEIRO — motor → porta → reconciliar → pedido de renovação (condomínio)
# =====================================================================================================================
def test_costura_condominio_do_pdf_ao_pedido_de_renovacao():
    from app.providers.infocap_policy_provider import apolice_documental_do_pack
    from app.providers.policy_data_provider import reconciliar
    from app.services.multicalculo import config as CFG
    from app.services.multicalculo import pedido as PED
    from portal_worker.multicalculo.contrato import problemas_do_pedido_re

    modelo = _Modelo()
    resultado = _ler(TOKIO_COND, modelo=modelo)
    leitura = resultado["leitura"]
    assert modelo.chamadas == 1 and leitura["estado"] == "fechou", leitura
    # ⛔ o modelo leu o texto MASCARADO
    assert CNPJ not in modelo.textos[0] and "98765-4321" not in modelo.textos[0]

    documental = apolice_documental_do_pack(_pack(resultado))                       # F2
    assert documental is not None and len(documental.linhas) == 2
    assert documental.leitura["estado"] == "fechou" and documental.tipo_documento == "apolice"
    assert documental.objeto_do_risco["cep"] == "88000-000"

    apolice = reconciliar(_apolice_cond(), documental)                               # F1
    assert apolice.sinal("documento_nao_conferido") is None
    pedido = PED.de_apolice(apolice, PERFIL_COND, ficha=documental,                  # F4
                            config=CFG.PADRAO_DO_PRODUTO).com_comissao(15.0)
    d = pedido.para_dict()
    assert pedido.ramo == 16
    assert d["risco"]["valor_basica"] == pytest.approx(CFG.basica_renovada(CFG.PADRAO_DO_PRODUTO, 16, 5000000))
    assert d["risco"]["cep"] == "88000000"                                           # o objeto do risco do MOTOR
    assert pedido.avisos == frozenset()
    assert pedido.faltando() == [] and problemas_do_pedido_re(d) == ()


def test_costura_o_mesmo_resultado_vai_ao_modelo_da_conversa_sem_pii(monkeypatch):
    from app.services import policy_document_evidence_service as S
    from app.services.vision_service import conteudo_do_anexo

    resultado = _ler(TOKIO_COND)
    for audiencia in ("segurado", "corretor"):
        ficha = S.ficha_para_o_modelo(resultado, audiencia=audiencia)
        assert "Conferida" in ficha and "Incendio, Raio e Explosao" in ficha
        assert CNPJ not in ficha and "98765-4321" not in ficha and "88000-000" not in ficha
    assert "[CEP]" in S.ficha_para_o_modelo(resultado, audiencia="corretor")

    # e pelo caminho do ANEXO (F3): bytes → ler_anexo_de_seguro → ficha. O modelo é o dublê, na borda.
    modelo = _Modelo()
    monkeypatch.setattr(S, "_leitor_modelo_padrao", modelo)
    texto = asyncio.run(conteudo_do_anexo(_pdf(TOKIO_COND), "apolice.pdf", company_id="corretora-A",
                                          audiencia="segurado", orcamento_s=30))
    assert texto and "Conferida" in texto
    assert CNPJ not in texto and "98765-4321" not in texto


def test_regua_o_escaneado_vai_direto_a_visao_sem_pagar_o_modelo_com_texto_vazio():
    """📊 Régua F5: EMPR-PORT-18 (16/16 páginas sem texto) fechou pela VISÃO, sem o degrau do modelo —
    este guarda prende o comportamento (sem página de texto, o modelo de texto não é chamado)."""
    import fitz

    from app.services.document_service import extrair_paginas_tolerante
    from app.services.policy_document_evidence_service import ler_documento_de_seguro

    doc = fitz.open()
    pagina = doc.new_page()
    pagina.draw_rect(fitz.Rect(50, 50, 300, 200), color=(0, 0, 0), fill=(0.5, 0.5, 0.5))   # só desenho
    pdf = doc.tobytes()
    doc.close()
    pages, parser, total = extrair_paginas_tolerante(pdf)
    assert parser == {"1": "sem_texto"}

    modelo = _Modelo()
    visao_chamadas = []

    async def _visao(imagens, *, company_id, **_k):
        visao_chamadas.append([n for n, _ in imagens])
        return json.dumps({"linhas": [{"pagina": 1, "rotulo": "Incendio", "limite": "100.000,00",
                                       "premio": "500,00", "trecho": "Incendio 100.000,00 500,00"}]})

    resultado = asyncio.run(ler_documento_de_seguro(
        pages, company_id="corretora-A", premio_esperado=Decimal("500.00"), fonte_do_esperado="corp",
        file_bytes=pdf, total_paginas=total, parser_por_pagina=parser, leitor_modelo=modelo, leitor_visao=_visao))
    assert modelo.chamadas == 0, "texto vazio não vai ao modelo"
    assert visao_chamadas == [[1]]
    assert resultado["leitura"]["estado"] == "fechou"
    assert [d["degrau"] for d in resultado["leitura"]["degraus"]] == ["regex", "visao"]


@pytest.mark.parametrize("premio, trecho, esperado", [
    ("15103.93", "Danos Eletricos 600.000,00 15.103,9312.345,00", True),   # 📊 Tokio/PyPDF2: valores COLADOS
    ("12345.00", "Danos Eletricos 600.000,00 15.103,9312.345,00", True),   # o 2º valor colado também conta
    ("500.00", "Incendio 100.000,00 500,00", True),
    ("1234.56", "Roubo 1234,56", True),                                     # sem separador de milhar
    ("2345.67", "LMI 12.345,67", False),                                    # ⛔ nunca o meio de um número
    ("345.67", "LMI 2.345,67", False),
    ("500.01", "Incendio 100.000,00 500,00", False),
    ("100.00", "Incendio 100.000,00 500,00", False),
])
def test_regua_o_premio_no_trecho_le_valores_colados_sem_afrouxar(premio, trecho, esperado):
    from app.services.policy_document_evidence_service import _premio_no_trecho

    assert _premio_no_trecho(Decimal(premio), trecho) is esperado


def test_regua_a_reserva_pymupdf_le_a_tabela_linha_a_linha(monkeypatch):
    """📊 Régua F5: Sura AUTO (19/19 páginas pela reserva) — a tabela saía COLUNA por coluna."""
    import fitz

    from app.services import document_service as D

    doc = fitz.open()
    pagina = doc.new_page()
    rotulos, premios = ["Casco", "Danos Materiais", "Danos Corporais"], ["2.702,92", "320,09", "129,42"]
    for i, r in enumerate(rotulos):                        # a COLUNA dos rótulos primeiro ...
        pagina.insert_text((50, 100 + 20 * i), r, fontsize=9)
    for i, p in enumerate(premios):                        # ... e depois a dos prêmios (o fluxo da Sura)
        pagina.insert_text((400, 100 + 20 * i), p, fontsize=9)
    pdf = doc.tobytes()
    doc.close()

    class _PyPDF2QueFalha:                                 # a borda: o PyPDF2 da Sura (IndexError por página)
        def __init__(self, *_a, **_k):
            self.pages = [SimpleNamespace(extract_text=lambda: (_ for _ in ()).throw(IndexError()))]

    monkeypatch.setattr(D.PyPDF2, "PdfReader", _PyPDF2QueFalha)
    pages, parser, _total = D.extrair_paginas_tolerante(pdf)
    assert parser == {"1": "pymupdf"}
    linhas = [" ".join(l.split()) for l in pages[0]["content"].splitlines()]
    for r, p in zip(rotulos, premios):
        assert r + " " + p in linhas, linhas               # rótulo e prêmio na MESMA linha → trecho literal


# =====================================================================================================================
# C2 · a leitura que NÃO fechou e não leu linha nenhuma acende o sinal; o cadastro fica
# =====================================================================================================================
def test_c2_leitura_sem_linhas_que_nao_fechou_avisa_o_corretor_e_mantem_o_cadastro():
    from app.providers.infocap_policy_provider import apolice_documental_do_pack
    from app.providers.policy_data_provider import reconciliar

    resultado = _ler(TOKIO_COND, modelo=_Modelo(cego=True))                          # o modelo não acha nada
    assert resultado["leitura"]["estado"] == "nao_fechou" and resultado["leitura"]["linhas"] == 0

    documental = apolice_documental_do_pack(_pack(resultado))
    assert documental is not None, "a leitura que não fechou tem de chegar ao reconciliar (C2)"
    assert documental.linhas == ()

    cadastro = _apolice_cond([_cob("INCENDIO RAIO EXPLOSAO", "5000000.00", "16771.96")])
    apolice = reconciliar(cadastro, documental)
    sinal = apolice.sinal("documento_nao_conferido")
    assert sinal is not None and sinal.detalhe["estado"] == "nao_fechou"
    assert [c.rotulo for c in apolice.coberturas] == ["INCENDIO RAIO EXPLOSAO"]     # o cadastro FICA
    assert apolice.coberturas[0].limite.origem == "sistema_de_gestao"

    # ⛔ linha de controle: SEM leitura registrada → None (ausência de leitura ≠ ausência de cobertura)
    sem_leitura = dict(resultado)
    sem_leitura.pop("leitura")
    assert apolice_documental_do_pack(_pack(sem_leitura)) is None
    assert reconciliar(cadastro, None).sinal("documento_nao_conferido") is None


# =====================================================================================================================
# C1 · o estado da leitura chega a `tool_invocations.output_summary` — e só ele
# =====================================================================================================================
_PROIBIDO = re.compile(r"\d{6,}|R\$|https?:|@|\d{3}\.\d{3}\.\d{3}-\d{2}")


def test_c1_o_recorder_registra_o_bloco_documento_da_tool_sem_pii():
    from app.agents.tools import infocap_tool as T
    from app.services.skills import invocation_recorder as R

    pack = _pack(_ler(TOKIO_COND))
    pack["official_policy_document_evidence"]["source_url"] = "https://s3.exemplo.invalido/x.pdf?Signature=1"
    det = {"ok": True, "policy": {"cpf": CPF, "numapo": "1234567890"}, "policy_evidence_pack": pack}
    # o retorno REAL da tool (o mesmo `_com_documento` do `execute`)
    resposta = T._com_documento({"content": "apolice do CPF " + CPF, "data": det, "found": True}, det)
    resumo = R._resumo_da_saida(resposta)

    doc = resumo.get("documento")
    assert doc is not None, "o bloco `documento` da tool não chegou ao output_summary (P-LEITOR-04)"
    assert doc["estado_da_leitura"] == "fechou" and doc["fechou"] is True and doc["linhas"] == 2
    from app.services.policy_document_evidence_service import LEITOR_VERSAO

    assert doc["leitor_versao"] == LEITOR_VERSAO     # 130B.2 desde o conserto único (o juiz da linha)
    assert doc["degraus"] == ["regex", "modelo.venceu"], doc                         # a costura F1 × F2
    assert set(doc) <= set(R._CAMPOS_DO_DOCUMENTO)
    assert not _PROIBIDO.search(json.dumps(resumo, ensure_ascii=False)), resumo
    # as duas listas fechadas não divergem
    assert R._CAMPOS_DO_DOCUMENTO == T._CAMPOS_DO_DOCUMENTO


def test_c1_o_recorder_nao_confia_em_quem_o_chama():
    from app.services.skills import invocation_recorder as R

    hostil = {"ok": True, "documento": {
        "estado_da_leitura": CPF, "document_status": "https://x.invalido", "linhas": "5", "fechou": "sim",
        "degraus": ["regex", {"degrau": "modelo"}, "12345678909"], "soma": "31.875,89", "cliente": "Fulano"}}
    doc = R._resumo_da_saida(hostil).get("documento") or {}
    assert doc == {"degraus": ["regex"]}, doc


# =====================================================================================================================
# C3 · `/itens` do veículo leva a MESMA `data=` da F2
# =====================================================================================================================
def _vehicle_item(monkeypatch, *, inivig, fimvig):
    import httpx

    import app.api.infocap_connector as C

    pedidos = []

    def _responder(req: httpx.Request) -> httpx.Response:
        pedidos.append(req)
        caminho = req.url.path
        if caminho == "/login":
            return httpx.Response(200, json={"token": "tk"})
        if caminho == "/cliente_cpf":
            return httpx.Response(200, json=[])
        if caminho == "/documentos":
            return httpx.Response(200, json=[{"nosnum": "999001", "codfil": 1, "ramo": "AUTOMOVEL"}])
        if caminho == "/documento":
            return httpx.Response(200, json=[{"nosnum": "999001", "inivig": inivig, "fimvig": fimvig,
                                              "cancelado": "F"}])
        if caminho == "/itens":
            return httpx.Response(200, json={"itens": [{"placa": "AAA0A00"}]})
        return httpx.Response(404, json={})

    real = httpx.AsyncClient

    class _Cliente(real):
        def __init__(self, *a, **k):
            k["transport"] = httpx.MockTransport(_responder)
            super().__init__(*a, **k)

    async def _conexao(_db, **_k):
        return {"selected_connection": {"connection_config": {"base_url": "https://corp.invalido"},
                                        "encrypted_secret_ref": "x"}}

    monkeypatch.setattr(C.httpx, "AsyncClient", _Cliente)
    monkeypatch.setattr(C, "_require_internal_key", lambda *_a, **_k: None)
    monkeypatch.setattr(C, "_resolve_infocap_connection", _conexao)
    monkeypatch.setattr(C, "get_encryption_service",
                        lambda: SimpleNamespace(decrypt=lambda _c: json.dumps({"username": "u", "password": "p"})))
    payload = SimpleNamespace(company_id="corretora-A", document="52998224725", tenant_connection_id=None,
                              policy_number=None)
    asyncio.run(C.infocap_vehicle_item(payload, x_autobrokers_internal_key="k", db=None))
    return [p for p in pedidos if p.url.path == "/itens"]


def test_c3_itens_do_veiculo_leva_data_na_renovacao_ainda_nao_iniciada(monkeypatch):
    inicio = date.today() + timedelta(days=20)
    itens = _vehicle_item(monkeypatch, inivig=inicio.strftime("%d/%m/%Y"),
                          fimvig=(inicio + timedelta(days=365)).strftime("%d/%m/%Y"))
    assert len(itens) == 1
    assert itens[0].url.params.get("data") == inicio.strftime("%d/%m/%Y")           # o INÍCIO, não hoje


def test_c3_linha_de_controle_sem_vigencia_sem_data(monkeypatch):
    itens = _vehicle_item(monkeypatch, inivig="", fimvig="")
    assert len(itens) == 1 and "data" not in itens[0].url.params


# =====================================================================================================================
# C4 · o NOME do arquivo vai MASCARADO no texto do turno
# =====================================================================================================================
def test_c4_o_nome_do_arquivo_com_cpf_vai_mascarado_e_o_reconhecedor_continua_lendo():
    from app.api.webhook import CABECALHO_DO_DOCUMENTO, MARCA_DO_DOCUMENTO, nome_do_documento
    from app.services.claims_shadow import tipo_de_documento
    from app.services.vision_service import nome_do_anexo_para_o_modelo

    cru = "boletim de ocorrencia " + CPF + ".pdf"
    nome = nome_do_anexo_para_o_modelo(cru)
    assert CPF not in nome and "<CPF>" in nome and "[" not in nome and "]" not in nome
    assert nome_do_anexo_para_o_modelo("12345678909.pdf") == "<NUMERO>.pdf"
    assert nome_do_anexo_para_o_modelo("apolice 2026.pdf") == "apolice 2026.pdf"      # sem PII: intacto
    assert nome_do_anexo_para_o_modelo("") == "documento"
    for molde in (MARCA_DO_DOCUMENTO, CABECALHO_DO_DOCUMENTO):
        texto = molde % nome
        assert nome_do_documento(texto, None) == nome                                # o reconhecedor lê inteiro
    # o classificador da sombra dá o MESMO enum para o nome cru e o mascarado
    assert tipo_de_documento(nome) == tipo_de_documento(cru)


def test_c4_o_webhook_e_o_chat_usam_o_nome_mascarado(monkeypatch):
    import inspect

    import app.api.chat as chat
    import app.api.webhook as webhook
    import app.services.vision_service as V

    # o webhook: a inspeção da DECLARAÇÃO (o ramo `document` mora dentro do handler do Evolution)
    fonte = inspect.getsource(webhook)
    assert "MARCA_DO_DOCUMENTO % fname_no_texto" in fonte and "CABECALHO_DO_DOCUMENTO % fname_no_texto" in fonte
    assert not re.search(r"(MARCA|CABECALHO)_DO_DOCUMENTO % fname\b", fonte)

    # o chat: o comportamento, com o download e o leitor na borda
    async def _baixar(_url):
        return b"%PDF-1.4"

    async def _conteudo(*_a, **_k):
        return "Documento: apólice."

    monkeypatch.setattr(V, "baixar_documento", _baixar)
    monkeypatch.setattr(V, "conteudo_do_anexo", _conteudo)
    saida = asyncio.run(chat.anexar_documento_do_corretor("veja", "https://x.invalido/a.pdf",
                                                          "rg " + CPF + ".pdf", company_id="A"))
    assert CPF not in saida and "<CPF>" in saida

    async def _falha(*_a, **_k):
        return None

    monkeypatch.setattr(V, "conteudo_do_anexo", _falha)
    aviso = asyncio.run(chat.anexar_documento_do_corretor("veja", "https://x.invalido/a.pdf",
                                                          "rg " + CPF + ".pdf", company_id="A"))
    assert "AVISO INTERNO" in aviso and CPF not in aviso
