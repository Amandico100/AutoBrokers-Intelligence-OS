# -*- coding: utf-8 -*-
"""SPEC-130-B · O CONSERTO ÚNICO — os achados do juiz e do red team, cada um com o seu guarda.

    B1  o juiz confere a LINHA (rótulo, limite, trecho de uma linha, total recusado, linha uma vez só)
    B2  o modelo fora (429 / exceção / JSON truncado) não é leitura final: relê depois; 3 tentativas → final
    B3  laudo, BO, aviso de sinistro, orçamento de oficina → `outro` (o texto mascarado chega; o ledger volta)
    B4  "em andamento" só com 2º plano agendado de verdade
    J1  o hit sem leitura desta versão relê o PDF ORIGINAL pelo leitor tolerante
    J2  a máscara (CPF/telefone/CEP/RG/nascimento) — e o dinheiro intacto
    J3  linha do modelo que não fecha não vira `coverage_row` (o cadastro fica)
    J5  `companyId` vazio não vira "None" · J6 o registro fora do laço async
    P2  teto do texto ao modelo · P7 objeto do risco nunca no JSON ao modelo

O MOTOR é o real. Dublê SÓ na borda (modelo, MinIO, banco, Redis, docling). ⛔ Todo PDF é GERADO, todo valor 💭
sintético. ⛔ Nenhuma chamada a modelo, banco ou rede.
Rodar:  cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_spec130b_conserto.py -q
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import threading
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.providers import policy_data_provider as P  # noqa: E402
from app.services import policy_document_evidence_service as S  # noqa: E402
from tests.test_spec130b_o_motor import (  # noqa: E402
    TOKIO, ModeloDublado, RedisDublado, _pedir, _servico, gerar_pdf, paginas_de, servico_de_documentos,
)

L1 = "Incendio, Raio e Explosao 5.000.000,00 16.771,96"
L2 = "Danos Eletricos 600.000,00 15.103,93"
ESPERADO = "31875.89"


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch):
    monkeypatch.delenv("LEITOR_APOLICE_MODELO", raising=False)
    monkeypatch.delenv("LEITOR_APOLICE_ORCAMENTO_S", raising=False)
    S._TAREFAS_EM_SEGUNDO_PLANO.clear()
    yield


def _modelo_que_devolve(linhas):
    async def _m(texto, *, company_id, **_k):
        _m.chamadas += 1
        return json.dumps({"linhas": linhas})
    _m.chamadas = 0
    return _m


def _ler(linhas_do_modelo, pages=None, **kw):
    kw.setdefault("premio_esperado", ESPERADO)
    return asyncio.run(S.ler_documento_de_seguro(
        pages or paginas_de(TOKIO), company_id="corretora-A",
        leitor_modelo=_modelo_que_devolve(linhas_do_modelo), **kw))


def _rows(r, metodo=None):
    return [i["structured"] for i in r["evidence_items"] if (i.get("structured") or {}).get("kind") == "coverage_row"
            and (metodo is None or i.get("extraction_method") == metodo)]


def _honesto():
    return [{"pagina": 1, "rotulo": "Incendio, Raio e Explosao", "limite": "5.000.000,00", "premio": "16.771,96",
             "trecho": L1},
            {"pagina": 1, "rotulo": "Danos Eletricos", "limite": "600.000,00", "premio": "15.103,93", "trecho": L2}]


# =====================================================================================================================
# B1 · o juiz da LINHA
# =====================================================================================================================
def test_b1_controle_o_modelo_honesto_fecha_e_o_limite_fica():
    r = _ler(_honesto())
    assert r["leitura"]["estado"] == "fechou" and r["leitura"]["conferencia"] == "linha"
    assert {x["label"]: x["lmi"] for x in _rows(r, "modelo")} == {
        "Incendio, Raio e Explosao": "R$ 5.000.000,00", "Danos Eletricos": "R$ 600.000,00"}


@pytest.mark.parametrize("nome, linhas, motivo", [
    ("rotulos trocados entre linhas reais", [
        {"pagina": 1, "rotulo": "Danos Eletricos", "limite": "9.999.999,00", "premio": "16.771,96", "trecho": L1},
        {"pagina": 1, "rotulo": "Roubo e Furto Qualificado", "limite": "1.000,00", "premio": "15.103,93",
         "trecho": L2}], "rotulo_fora_do_trecho"),
    ("a linha do premio liquido com rotulo de cobertura", [
        {"pagina": 1, "rotulo": "Incendio", "limite": "5.000.000,00", "premio": "31.875,89",
         "trecho": "Premio Liquido R$ 31.875,89"}], "trecho_de_total"),
    ("o trecho e a pagina inteira", [
        {"pagina": 1, "rotulo": "Cobertura Ampla", "premio": "31.875,89",
         "trecho": " ".join(S.mascarar_texto_de_apolice("\n".join(TOKIO)).split())}], "trecho_fora_de_uma_linha"),
])
def test_b1_o_juiz_recusa_a_linha_que_a_soma_deixava_passar(nome, linhas, motivo):
    r = _ler(linhas)
    assert r["leitura"]["estado"] == "nao_fechou", (nome, r["leitura"])
    assert not _rows(r, "modelo"), nome
    degrau = [d for d in r["leitura"]["degraus"] if d["degrau"] == "modelo"][0]
    assert degrau["motivos_do_descarte"].get(motivo), (nome, degrau)


def test_b1_a_linha_total_do_quadro_e_recusada():
    pages = paginas_de([l for l in TOKIO if not l.startswith("Premio")] + ["Total 31.875,89",
                                                                            "Premio Liquido R$ 31.875,89"])
    r = _ler([{"pagina": 1, "rotulo": "Total", "premio": "31.875,89", "trecho": "Total 31.875,89"}], pages=pages)
    assert r["leitura"]["estado"] == "nao_fechou" and not _rows(r, "modelo")
    # ⚠️ "Perda Total" É cobertura (AUTO): o filtro de total não a derruba
    assert S.trecho_nao_e_cobertura("Colisao - Perda Total 50.000,00 1.200,00") is None
    assert S.trecho_nao_e_cobertura("Total a pagar 1.200,00")
    assert S.trecho_nao_e_cobertura("01 14/05/2026 R$ 82,31 Em transito")


def test_b1_o_limite_inventado_cai_e_a_linha_fica():
    linhas = _honesto()
    linhas[1] = dict(linhas[1], limite="9.999.999,00")          # não está no trecho
    linhas[0] = dict(linhas[0], limite="16.771,96")             # é o PRÊMIO, não outro valor do trecho
    r = _ler(linhas)
    assert r["leitura"]["estado"] == "fechou"
    assert {x["label"]: x["lmi"] for x in _rows(r, "modelo")} == {
        "Incendio, Raio e Explosao": None, "Danos Eletricos": None}


def test_b1_a_mesma_linha_do_documento_conta_uma_vez():
    # ⚠️ as duas citações extras passam no rótulo (senão o guarda testado seria o do rótulo, não este)
    for extra in ({"pagina": 1, "rotulo": "Danos Eletricos", "premio": "15.103,93", "trecho": L2},   # idêntica
                  {"pagina": 1, "rotulo": "Eletricos", "premio": "15.103,93",
                   "trecho": "Eletricos 600.000,00 15.103,93"}):                                       # um PEDAÇO
        r = _ler(_honesto() + [extra])
        assert r["leitura"]["estado"] == "fechou" and len(_rows(r, "modelo")) == 2, extra
        degrau = [d for d in r["leitura"]["degraus"] if d["degrau"] == "modelo"][0]
        assert degrau["motivos_do_descarte"] == {"linha_repetida": 1}, degrau
    # controle: a linha que o documento TEM duas vezes conta duas vezes
    pages = paginas_de(["APOLICE DE SEGURO", "Coberturas Limite Premio", L2, L2, "Premio Liquido R$ 30.207,86"])
    r2 = _ler([{"pagina": 1, "rotulo": "Danos Eletricos", "premio": "15.103,93", "trecho": L2}] * 2,
              pages=pages, premio_esperado="30207.86")
    assert r2["leitura"]["estado"] == "fechou" and len(_rows(r2, "modelo")) == 2


def test_b1_rotulo_embrulhado_em_duas_linhas_vale_e_a_linha_cruzada_nao():
    """📊 Régua do conserto: o PyPDF2 quebra o rótulo longo (Tokio/Allianz EMPR) — 26 linhas caíam por isso."""
    pages = paginas_de(["APOLICE DE SEGURO", "Coberturas Limite Premio",
                        "Incendio, Raio, Explosao e Queda", "de Aeronave 5.000.000,00 16.771,96", L2,
                        "Premio Liquido R$ 31.875,89"])
    embrulhada = {"pagina": 1, "rotulo": "Incendio, Raio, Explosao e Queda de Aeronave", "limite": "5.000.000,00",
                  "premio": "16.771,96", "trecho": "Incendio, Raio, Explosao e Queda de Aeronave 5.000.000,00 16.771,96"}
    r = _ler([embrulhada, _honesto()[1]], pages=pages)
    assert r["leitura"]["estado"] == "fechou", r["leitura"]
    degrau = [d for d in r["leitura"]["degraus"] if d["degrau"] == "modelo"][0]
    assert degrau["motivos_do_descarte"] == {"aceitas_em_rotulo_embrulhado": 1}
    # ⛔ o ATAQUE: o rótulo da linha de CIMA (que tem os valores dela) com o prêmio da linha de BAIXO —
    #    rótulo no trecho ✓, prêmio no pedaço de baixo ✓; só a regra "a de cima não tem valor" o barra
    cruzada = {"pagina": 1, "rotulo": "Incendio, Raio e Explosao", "premio": "15.103,93",
               "trecho": L1 + " " + L2}
    r2 = _ler([cruzada], pages=paginas_de(["APOLICE DE SEGURO", L1, L2, "Premio Liquido R$ 31.875,89"]))
    assert not _rows(r2, "modelo")
    assert [d for d in r2["leitura"]["degraus"] if d["degrau"] == "modelo"][0]["motivos_do_descarte"] == {
        "trecho_fora_de_uma_linha": 1, "fora:2_linhas_cima_com_valor": 1}
    # ⛔ três linhas nunca
    tres = paginas_de(["APOLICE", "Incendio, Raio,", "Explosao e Queda", "de Aeronave 5.000.000,00 16.771,96"])
    r3 = _ler([dict(embrulhada, premio="16.771,96")], pages=tres, premio_esperado="16771.96")
    assert not _rows(r3, "modelo")


def test_b1_separador_trocado_nao_vira_valor():
    assert S._valores_do_trecho("Incendio 5.000.000,00 16,771.96") == [Decimal("5000000.00")]
    # ⛔ e a cola do extrator continua valendo (📊 Tokio/PyPDF2)
    assert S._valores_do_trecho("Danos Eletricos 600.000,00 15.103,9312.345,00") == [
        Decimal("600000.00"), Decimal("15103.93"), Decimal("12345.00")]


@pytest.mark.parametrize("rotulo, trecho, esperado", [
    ("Incendio, Raio e Explosao", L1, True),
    ("Incêndio Raio Explosão", "INCENDIORAIO E EXPLOSAO 5.000.000,00 16.771,96", True),    # PyPDF2 cola palavras
    ("Danos Elétricos", "DANOS ELET. 600.000,00 15.103,93", True),                          # abreviação no trecho
    ("Responsabilidade Civil Familiar Ampla", "Resp. Civil Familiar Ampla 100.000,00 50,00", True),
    ("Danos Eletricos", L1, False),
    ("Roubo", "Cobertura A ...... LMI 100.000,00 ...... 600,00", False),
    ("Vendaval Granizo", "Vendaval 10.000,00 12,00", False),                                  # 1 de 2 = 50 %
])
def test_b1_a_regua_do_rotulo_no_trecho(rotulo, trecho, esperado):
    assert S.rotulo_no_trecho(rotulo, trecho) is esperado


def test_b1_visao_rotulo_de_total_recusado_limite_menor_que_o_premio_cai_e_a_ficha_diz_soma():
    import fitz

    d = fitz.open()
    d.new_page()
    pdf = d.tobytes()
    d.close()

    async def _visao(imagens, *, company_id, **_k):
        return json.dumps({"linhas": [
            {"pagina": 1, "rotulo": "Total do premio", "premio": "500,00"},
            {"pagina": 1, "rotulo": "Incendio", "limite": "1,00", "premio": "300,00"},
            {"pagina": 1, "rotulo": "Vendaval", "limite": "10.000,00", "premio": "200,00"}]})

    r = asyncio.run(S.ler_documento_de_seguro(
        [], company_id="corretora-A", premio_esperado="500.00", leitor_visao=_visao,
        leitor_modelo=_modelo_que_devolve([]), parser_por_pagina={"1": "sem_texto"}, file_bytes=pdf))
    assert r["leitura"]["estado"] == "fechou" and r["leitura"]["conferencia"] == "soma"
    assert {x["label"]: x["lmi"] for x in _rows(r, "visao")} == {"Incendio": None, "Vendaval": "R$ 10.000,00"}
    ficha = S.ficha_para_o_modelo(r, audiencia="segurado")
    assert "Conferida pela soma, lida de imagem" in ficha


def test_b1_de_ponta_a_ponta_o_lmi_inventado_nao_passa_por_cima_do_cadastro():
    from app.providers.infocap_policy_provider import apolice_documental_do_pack, apolice_do_pack

    r = _ler([{"pagina": 1, "rotulo": "Danos Eletricos", "limite": "9.999.999,00", "premio": "16.771,96",
               "trecho": L1},
              {"pagina": 1, "rotulo": "Incendio, Raio e Explosao", "limite": "1.000,00", "premio": "15.103,93",
               "trecho": L2}])
    documental = apolice_documental_do_pack({"official_policy_document_evidence": {**r, "ok": True}})
    cadastro = apolice_do_pack({"coverage_sections": [
        {"label": "Incendio, Raio e Explosao", "amount": "R$ 5.000.000,00"},
        {"label": "Danos Eletricos", "amount": "R$ 600.000,00"}]})
    apolice = P.reconciliar(cadastro, documental)
    assert {c.rotulo: (c.limite.valor, c.limite.origem) for c in apolice.coberturas} == {
        "Incendio, Raio e Explosao": (Decimal("5000000.00"), "sistema_de_gestao"),
        "Danos Eletricos": (Decimal("600000.00"), "sistema_de_gestao")}
    assert apolice.sinal("documento_nao_conferido") is not None


# =====================================================================================================================
# J3 · o que NÃO fecha não vira cobertura — fica só no registro
# =====================================================================================================================
def test_j3_linha_do_modelo_que_nao_fecha_fica_so_no_registro():
    r = _ler([_honesto()[0]])                                                    # metade da tabela
    assert r["leitura"]["estado"] == "nao_fechou"
    assert not _rows(r, "modelo"), "linha que não fechou não pode vencer o cadastro"
    assert r["leitura"]["linhas_nao_conferidas"] == 1
    assert [i["structured"]["label"] for i in r["linhas_nao_conferidas"]] == ["Incendio, Raio e Explosao"]
    ds = servico_de_documentos()
    ds.supabase.tabelas["documents"] = [{"id": "d1", "company_id": "corretora-A", "metadata": {}}]
    S.PolicyDocumentEvidenceService._guardar_leitura(ds, document_id="d1", company_id="corretora-A",
                                                     content_hash="h" * 64, resultado=r)
    ficha = ds.carregar_leitura("d1", "corretora-A")
    assert len(ficha["linhas_nao_conferidas"]) == 1
    assert "linhas_nao_conferidas" not in json.dumps(ds.supabase.tabelas["documents"][0]["metadata"]["leitura"]
                                                     .get("degraus"))


def test_j3_o_pdf_misto_fecha_com_o_texto_e_a_imagem_juntos():
    """O modelo leu a página de texto (sem fechar); a visão leu a escaneada; JUNTOS fecham."""
    import fitz

    d = fitz.open()
    p1 = d.new_page()
    p1.insert_text((50, 72), "APOLICE DE SEGURO", fontsize=9)
    d.new_page()                                                              # a página 2 é só imagem
    pdf = d.tobytes()
    d.close()
    pages = [{"page_number": 1, "content": "APOLICE DE SEGURO\nCoberturas\n" + L1}]

    async def _visao(imagens, *, company_id, **_k):
        return json.dumps({"linhas": [{"pagina": 2, "rotulo": "Danos Eletricos", "limite": "600.000,00",
                                       "premio": "15.103,93"}]})

    r = asyncio.run(S.ler_documento_de_seguro(
        pages, company_id="corretora-A", premio_esperado=ESPERADO, leitor_modelo=_modelo_que_devolve([_honesto()[0]]),
        leitor_visao=_visao, parser_por_pagina={"1": "pypdf2", "2": "sem_texto"}, file_bytes=pdf))
    assert r["leitura"]["estado"] == "fechou", r["leitura"]
    assert sorted(i.get("extraction_method") for i in r["evidence_items"]
                  if (i.get("structured") or {}).get("kind") == "coverage_row") == ["modelo", "visao"]
    assert "linhas_nao_conferidas" not in r


# =====================================================================================================================
# B2 · o modelo fora não é leitura final
# =====================================================================================================================
class _ModeloInstavel(ModeloDublado):
    def __init__(self, falhas=1, **kw):
        super().__init__(**kw)
        self.falhas = falhas

    async def __call__(self, texto, *, company_id):
        if self.falhas > 0:
            self.falhas -= 1
            self.recebido.append(texto)
            raise RuntimeError("429 (dublê)")
        return await super().__call__(texto, company_id=company_id)


def test_b2_o_429_nao_e_final_a_proxima_dentro_da_espera_nao_paga_e_depois_rele(monkeypatch):
    pdf = gerar_pdf([TOKIO])
    modelo = _ModeloInstavel(falhas=1)
    servico = _servico(modelo=modelo, redis=RedisDublado())
    r1 = asyncio.run(_pedir(servico, "corretora-A", pdf))
    assert r1["leitura"]["estado"] == "modelo_indisponivel" and r1["leitura"]["tentativas"] == 1
    r2 = asyncio.run(_pedir(servico, "corretora-A", pdf))
    assert r2["cache_status"] == "hit" and r2["leitura"]["estado"] == "modelo_indisponivel"
    assert len(modelo.recebido) == 1, "dentro da espera o modelo não é chamado de novo"
    # passou a hora da próxima tentativa → relê, e o modelo saudável fecha
    agora = S._agora()
    monkeypatch.setattr(S, "_agora", lambda: agora + timedelta(seconds=S.ESPERA_DO_MODELO_INDISPONIVEL_S + 1))
    r3 = asyncio.run(_pedir(servico, "corretora-A", pdf))
    assert r3["leitura"]["estado"] == "fechou" and len(modelo.recebido) == 2


def test_b2_tres_tentativas_viram_nao_fechou_final(monkeypatch):
    pdf = gerar_pdf([TOKIO])
    modelo = _ModeloInstavel(falhas=99)
    servico = _servico(modelo=modelo, redis=RedisDublado())
    agora = [S._agora()]
    monkeypatch.setattr(S, "_agora", lambda: agora[0])
    estados = []
    for _ in range(4):
        estados.append(asyncio.run(_pedir(servico, "corretora-A", pdf))["leitura"])
        agora[0] = agora[0] + timedelta(seconds=S.ESPERA_DO_MODELO_INDISPONIVEL_S + 1)
    assert [e["estado"] for e in estados] == ["modelo_indisponivel", "modelo_indisponivel", "nao_fechou", "nao_fechou"]
    assert estados[2]["motivo"] == "modelo_indisponivel_em_3_tentativas"
    assert len(modelo.recebido) == 3, "depois da 3ª, a leitura é final: não relê para sempre"


@pytest.mark.parametrize("resposta", [
    '{"linhas":[{"pagina":1,"rotulo":"Danos Eletricos","limite":"600.000,00","premio":"15.103,93","trecho":"Danos Eletr',
    "isto nao e json {", "{}",
])
def test_b2_json_truncado_ou_invalido_e_modelo_indisponivel(resposta):
    async def _m(texto, *, company_id, **_k):
        return resposta
    r = asyncio.run(S.ler_documento_de_seguro(paginas_de(TOKIO), company_id="A", premio_esperado=ESPERADO,
                                              leitor_modelo=_m))
    assert r["leitura"]["estado"] == "modelo_indisponivel"
    # controle: "li e não achei nada" (`{"linhas": []}`) É resposta — `nao_fechou` final
    assert _ler([])["leitura"]["estado"] == "nao_fechou"


# =====================================================================================================================
# B3 · documento de sinistro não é apólice
# =====================================================================================================================
SINISTRO = {
    "laudo": ["LAUDO DE VISTORIA DE SINISTRO", "Referente a apolice n 123456 e ao sinistro 789",
              "Danos constatados: porta traseira amassada"],
    "boletim_ocorrencia": ["BOLETIM DE OCORRENCIA N 2026-001", "Natureza: colisao de veiculo",
                           "o veiculo segurado pela apolice 555 foi atingido"],
    "aviso": ["AVISO DE SINISTRO", "Apolice: 777888", "Descricao: alagamento na garagem"],
    "orcamento": ["ORCAMENTO DE SERVICOS N 4512", "Oficina Exemplo Funilaria",
                  "Para-choque dianteiro substituicao R$ 1.250,00", "Total do orcamento R$ 2.740,00"],
}


@pytest.mark.parametrize("nome", list(SINISTRO))
def test_b3_documento_de_sinistro_e_outro(nome):
    assert S.tipo_de_documento(paginas_de(SINISTRO[nome])) == "outro"


def test_b3_controles_o_que_e_de_seguro_continua_de_seguro():
    assert S.tipo_de_documento(paginas_de(TOKIO)) == "apolice"
    # a apólice que cita "Aviso de Sinistro: 0800" no cabeçalho continua apólice (tem o prêmio do contrato)
    assert S.tipo_de_documento(paginas_de(["Central de Aviso de Sinistro 0800 000 0000"] + TOKIO)) == "apolice"
    assert S.tipo_de_documento(paginas_de(["ORCAMENTO DE SEGURO RESIDENCIAL", "Premio 100,00"])) == "cotacao"
    assert S.tipo_de_documento(paginas_de(["ENDOSSO N 12 DE RESTITUICAO", "Apolice n 99"])) == "endosso"
    # a palavra "apólice" sozinha não faz apólice
    assert S.tipo_de_documento(paginas_de(["Declaro que li a apolice"])) == "desconhecido"


@pytest.mark.parametrize("nome, enum", [("laudo", "laudo"), ("boletim_ocorrencia", "boletim_ocorrencia")])
def test_b3_o_conteudo_chega_ao_modelo_e_o_ledger_volta_ao_enum_de_antes(monkeypatch, nome, enum):
    from app.api.webhook import CABECALHO_DO_DOCUMENTO, MARCA_DO_DOCUMENTO, nome_do_documento
    from app.services import sanitization_service as SS
    from app.services import vision_service as V
    from app.services.claims_shadow import tipo_de_documento as tipo_do_ledger

    monkeypatch.setattr(SS.SanitizationService, "__init__", lambda self, *a, **k: None)
    monkeypatch.setattr(SS.SanitizationService, "_docling_parse",
                        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("docling dublado")))

    async def _nunca(*_a, **_k):
        raise AssertionError("documento de sinistro não vai ao leitor de coberturas")
    monkeypatch.setattr(S, "_leitor_modelo_padrao", _nunca)
    texto = asyncio.run(V.conteudo_do_anexo(gerar_pdf([SINISTRO[nome]]), "documento.pdf", company_id="A",
                                            audiencia="segurado"))
    assert texto and SINISTRO[nome][2].split()[-1] in texto and "Documento: apólice" not in texto
    mensagem = "%s\n\n%s\n%s\n[FIM DO DOCUMENTO]" % (MARCA_DO_DOCUMENTO % "documento.pdf",
                                                     CABECALHO_DO_DOCUMENTO % "documento", texto)
    assert tipo_do_ledger(nome_do_documento(mensagem, {"document": {"fileName": "documento.pdf"}}), mensagem) == enum


# =====================================================================================================================
# B4 · "em andamento" só quando algo está em andamento
# =====================================================================================================================
def test_b4_anexo_que_estoura_o_orcamento_nao_promete_retorno():
    pdf = gerar_pdf([TOKIO])
    r = asyncio.run(S.ler_anexo_de_seguro(pdf, "apolice.pdf", company_id="A", orcamento_s=1.0,
                                          leitor_modelo=ModeloDublado(atraso=3.0)))
    assert r["leitura"]["estado"] == "pendente" and r["leitura"]["em_andamento"] is False
    ficha = S.ficha_para_o_modelo(r)
    assert "andamento" not in ficha and "não consegui conferir a tabela inteira" in ficha


def test_b4_corp_sem_redis_nao_promete_e_com_segundo_plano_promete(monkeypatch):
    from app.agents.tools import infocap_tool as T

    monkeypatch.setenv("LEITOR_APOLICE_ORCAMENTO_S", "0.05")
    pdf = gerar_pdf([TOKIO])
    sem = asyncio.run(_pedir(_servico(modelo=ModeloDublado(atraso=0.3), redis=None), "corretora-A", pdf))
    assert sem["leitura"]["em_andamento"] is False
    for texto in (S.ficha_para_o_modelo(sem), T._linha_da_leitura_nao_conferida({"official_policy_document_evidence": sem}),
                  P.frase_do_sinal(P.Sinal("documento_nao_conferido", {"estado": "pendente", "em_andamento": False}))):
        assert "andamento" not in texto, texto

    # linha de controle: COM 2º plano agendado, "em andamento" é verdade e é dito
    servico = _servico(modelo=ModeloDublado(atraso=0.3), redis=RedisDublado())

    async def _com():
        r = await _pedir(servico, "corretora-A", pdf)
        await asyncio.gather(*list(servico.tarefas_em_segundo_plano))
        return r
    com = asyncio.run(_com())
    assert com["leitura"]["em_andamento"] is True and "em andamento" in S.ficha_para_o_modelo(com)
    assert "em andamento" in T._linha_da_leitura_nao_conferida({"official_policy_document_evidence": com})


# =====================================================================================================================
# J1 · o PDF guardado ANTES da 130-B é relido pelo leitor tolerante
# =====================================================================================================================
def test_j1_o_hit_sem_leitura_desta_versao_rele_o_pdf_original(monkeypatch):
    pdf = gerar_pdf([TOKIO])
    ds = servico_de_documentos()
    monkeypatch.setenv("LEITOR_APOLICE_MODELO", "0")
    asyncio.run(_pedir(_servico(ds=ds), "corretora-A", pdf))
    monkeypatch.setenv("LEITOR_APOLICE_MODELO", "1")
    doc = ds.supabase.tabelas["documents"][0]
    # o documento "de antes": páginas VELHAS vazias (o PyPDF2 inteiro que caía), metadata vazio, sem leitura
    raw = "corretora-A/raw/%s.json" % doc["id"]
    ds.minio.objetos[raw] = json.dumps({"pages": []}).encode("utf-8")
    ds.minio.objetos.pop("corretora-A/raw/%s.leitura.json" % doc["id"], None)
    doc["metadata"] = {}
    modelo = ModeloDublado()
    r = asyncio.run(_pedir(_servico(modelo=modelo, ds=ds), "corretora-A", pdf))
    assert r["cache_status"] == "hit" and r["leitura"]["estado"] == "fechou", r["leitura"]
    assert r["leitura"]["parser_por_pagina"] == {"1": "pypdf2"}
    # linha de controle: SEM o original no MinIO, valem as páginas guardadas (vazias → nada a ler)
    ds.minio.objetos.pop(doc["minio_path"])
    ds.minio.objetos.pop("corretora-A/raw/%s.leitura.json" % doc["id"], None)
    r2 = asyncio.run(_pedir(_servico(modelo=ModeloDublado(), ds=ds), "corretora-A", pdf))
    assert r2["leitura"]["estado"] != "fechou"


# =====================================================================================================================
# J2 · a máscara
# =====================================================================================================================
PII = ["CPF 123 456 789 09", "CPF 123.456.789/09", "Tel 11 98765 4321", "Celular 98765 4321", "Tel 11.98765.4321",
       "Tel (11) 8765 4321", "Tel (11) 9 8765-4321", "CEP 01310100", "RG 12.345.678-9", "RG MG-12.345.678",
       "RG 1234567", "Nascimento 01/02/1980", "Data de Nascimento: 01/02/1980"]
DINHEIRO = ["R$ 600.000,00", "600.000,00", "1.500.000,00", "R$ 1500000,00", "15.103,93", "0,00", "R$ 23,88",
            "1.000.000.000,00", "LMI 1000,00", "Vig 2025-2026", "Vig 2025 2026", "16.771,96 15.103,93",
            "17.539,151.803,19", "R$ 150000000,00", "Incendio 133.000,00   45,64", "Franquia 10% minimo de R$ 600,00",
            "Roubo 5000,00", "Pag 01/2026 R$ 1.234,56", "Total 12345678,90", "Valor 123456789,00",
            "RCF 100.000,00 1.234,56", "Guincho ate 1000 km", "Vidros 1.500,00 120,00", "R$ 15000000",
            "Vencimento 10/11/2026", "Limite 1.000.000"]


def test_j2_a_mascara_pega_as_formas_que_vazavam_e_nunca_toca_dinheiro():
    for texto in PII:
        mascarado = S.mascarar_texto_de_apolice(texto)
        digitos = re.sub(r"\D", "", texto.split(" ", 1)[1])
        assert digitos not in re.sub(r"\D", "", mascarado), (texto, mascarado)
    for texto in DINHEIRO:
        assert S.mascarar_texto_de_apolice(texto) == texto, texto


# =====================================================================================================================
# P2 · o teto do texto ao modelo
# =====================================================================================================================
def test_p2_o_texto_ao_modelo_tem_teto_e_a_pagina_com_valores_vai_primeiro():
    paginas = [{"page_number": n, "content": "Clausula %d: condicoes gerais do contrato de seguro. " % n * 60}
               for n in range(1, 301)]
    paginas.append({"page_number": 301, "content": "APOLICE\nCoberturas Limite Premio\n%s\n%s" % (L1, L2)})
    modelo = ModeloDublado()
    r = asyncio.run(S.ler_documento_de_seguro(paginas, company_id="A", premio_esperado=ESPERADO,
                                              leitor_modelo=modelo))
    assert len(modelo.recebido[0]) <= S.TETO_DO_TEXTO_AO_MODELO
    assert "[pagina 301]" in modelo.recebido[0], "a página da tabela (com valores) vai primeiro"
    assert r["leitura"]["texto_ao_modelo"]["cortado"] is True
    assert r["leitura"]["estado"] == "fechou"
    # controle: abaixo do teto, nada é cortado nem registrado
    assert "texto_ao_modelo" not in _ler(_honesto())["leitura"]


# =====================================================================================================================
# P7 · o objeto do risco nunca no JSON que vai ao modelo
# =====================================================================================================================
def test_p7_objeto_do_risco_fora_do_json_ao_modelo(monkeypatch):
    from app.agents import nodes as N

    monkeypatch.setattr(N, "_policy_intelligence_v2", lambda: False)
    result = {"content": "", "data": {"policy_evidence_pack": {"official_policy_document_evidence": {
        "leitura": {"estado": "fechou"}, "objeto_do_risco": {"placa": "ABC1D23", "chassi": "9BWZZZ377VT004251"}}}}}
    texto = N._conteudo_da_consulta_para_o_modelo(result)
    assert "ABC1D23" not in texto and "objeto_do_risco" not in texto and '"fechou"' in texto
    assert result["data"]["policy_evidence_pack"]["official_policy_document_evidence"]["objeto_do_risco"], \
        "o dado do PEDIDO não é apagado — só não vai ao modelo"


# =====================================================================================================================
# J5 · J6
# =====================================================================================================================
def test_j5_company_id_vazio_nao_vira_none(monkeypatch):
    from app.api import chat as C
    from app.services import vision_service as V

    recebido = {}

    async def _baixar(_url):
        return b"%PDF-1.4"

    async def _conteudo(dados, nome, *, company_id, audiencia, **_k):
        recebido["company_id"] = company_id
        return "ficha"
    monkeypatch.setattr(V, "baixar_documento", _baixar)
    monkeypatch.setattr(V, "conteudo_do_anexo", _conteudo)
    asyncio.run(C.anexar_documento_do_corretor("oi", "https://exemplo.invalido/x.pdf", "x.pdf", company_id=None))
    assert recebido["company_id"] == ""
    asyncio.run(C.anexar_documento_do_corretor("oi", "https://exemplo.invalido/x.pdf", "x.pdf", company_id="None"))
    assert recebido["company_id"] == ""


def test_j6_o_registro_da_leitura_roda_fora_do_laco():
    ds = servico_de_documentos()
    threads = []
    original = ds.guardar_leitura

    def _espiao(*a, **k):
        threads.append(threading.get_ident())
        return original(*a, **k)
    ds.guardar_leitura = _espiao
    asyncio.run(_pedir(_servico(modelo=ModeloDublado(), ds=ds), "corretora-A", gerar_pdf([TOKIO])))
    assert threads and all(t != threading.get_ident() for t in threads)
