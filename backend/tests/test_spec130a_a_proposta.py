# -*- coding: utf-8 -*-
"""SPEC-130-A F3 · U4 + U7 — A PROPOSTA (o modelo) e o PUBLICAR, sobre o pedido REAL do canário no banco dublê.

    o resumo FECHA a conta (contado por fora do motor) · a anfitriã: marca PUBLICADA ou neutra, Google só confirmado,
    WhatsApp declarado > atendimento (nunca o observador) · o logo: só imagem, com teto · a validade da config ·
    o arredondamento único · juros com nome · a FAQ do caso · a comissão nunca sai (cerca de saída com mutação) ·
    publicar de novo = versão nova · nada gravado sem endereço público / sem o que propor · o comando (ensaio e
    publicação, sem segredo na saída) · G8 nos arquivos novos da F3.

⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a_a_proposta.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import base64
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.multicalculo import proposta as P  # noqa: E402
from app.services.multicalculo.comando_proposta import executar  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402

BASE = "https://app.exemplo.test"
AGORA = datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc)       # 08:00 em Brasília
TABELAS_DO_HUB = ("artifacts", "artifact_versions", "artifact_renders", "artifact_shares", "artifact_events")


def _montar(m, situacao="novo_sem_apolice", **kw):
    return asyncio.run(P.montar_proposta(m.dono, m.pedido_id, situacao, db=m.db, agora=AGORA, **kw))


def _opcao_do_calculo(dados):
    return {e["calculo_id"]: e["opcao"] for e in dados["estados"]}


# =====================================================================================================================
# o resumo FECHA a conta — contado por fora do motor
# =====================================================================================================================
def test_o_resumo_fecha_a_conta_sem_dupla_contagem(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    mod = _montar(m)
    r = mod["resumo"]
    assert r["seguradoras_cotadas"] == r["com_preco_comparavel"] + r["com_produto_diferente"] + r["nao_responderam"]
    assert r["com_preco_comparavel"] == len(mod["ranking"])
    assert r["nao_responderam"] == len(mod["nao_responderam"]) and r["corretoras_comparadas"] == 2

    # 🔬 por fora: as seguradoras (por código) da ANFITRIÃ na padrão
    d, op = m.dados, _opcao_do_calculo(m.dados)
    da_anf = [o for o in d["ofertas"] if o["corretora_company_id"] == m.alfa and op[o["calculo_id"]] == "padrao"]
    completas = {o["seguradora_codigo"] for o in da_anf if o["coberturas"].get("tipoPadronizado") == "Compreensiva"
                 and o["coberturas"].get("casco") == 100 and "assinatura" not in o["seguradora"].lower()}
    com_oferta = {o["seguradora_codigo"] for o in da_anf}
    recusas = {e["seguradora_codigo"] for e in d["eventos"] if e["corretora_company_id"] == m.alfa
               and op[e["calculo_id"]] == "padrao"} - com_oferta
    assert r["com_preco_comparavel"] == len(completas)
    assert r["com_produto_diferente"] == len(com_oferta - completas)
    assert r["nao_responderam"] == len(recusas)
    # ninguém em dois lugares: quem tem preço não está entre os que não responderam
    assert not ({x["seguradora"] for x in mod["ranking"]} & {x["seguradora"] for x in mod["nao_responderam"]})


# =====================================================================================================================
# a comissão nunca sai — DOIS tenants (o canal recebe None; a dona recebe o número e ele não chega ao modelo)
# =====================================================================================================================
@pytest.mark.parametrize("solicitante", ["canal", "beta"])
def test_a_comissao_nunca_chega_ao_modelo(monkeypatch, solicitante):
    m = M.montar_mundo(monkeypatch, solicitante=solicitante)
    mod = _montar(m)
    texto = repr(mod)
    assert "comiss" not in texto.lower() and "17.37" not in texto and "17,37" not in texto


def test_a_cerca_de_saida_da_comissao_fica_vermelha_com_a_chave():
    """🔴 GUARDA: a cerca procura a chave em qualquer profundidade (mutação: devolver sem olhar → este teste falha)."""
    P._sem_comissao({"opcoes": [{"id": "x", "coberturas": [{"chave": "casco"}]}]})          # controle: limpo passa
    with pytest.raises(AssertionError, match="comiss"):
        P._sem_comissao({"opcoes": [{"id": "x", "extra": {"Comissao_percentual": 15}}]})


# =====================================================================================================================
# a ANFITRIÃ
# =====================================================================================================================
def test_a_anfitria_vencedora_veste_a_marca_publicada_e_o_google_confirmado(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    a = _montar(m)["anfitria"]
    assert a["nome"] == M.MARCA_ALFA and a["marca_cadastrada"] is True
    assert a["logo_data_url"] == M.LOGO_DATA_URL
    assert a["tema_claro"]["mode"] == "light" and a["tema_escuro"]["mode"] == "dark"
    assert a["cores"]["primaria"].upper() == "#1D5579"
    assert a["google"] == {"nota": 4.9, "avaliacoes": 37, "fonte": "Google, ficha confirmada, 06/10/2026"}
    assert (a["cidade"], a["desde"], a["susep"], a["site"]) == ("Florianópolis - SC", 2009, "SUSEP 202031234",
                                                                "orion-ficticia.test")
    assert a["whatsapp"] == M.WHATS_ALFA


def test_sem_marca_publicada_fica_neutra_e_o_whatsapp_e_o_de_atendimento(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    a = _montar(m)["anfitria"]
    assert a == {"nome": M.NOME_BETA, "marca_cadastrada": False, "whatsapp": "5548999990002"}


def test_o_numero_do_observador_nunca_vira_o_quero_fechar(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    for linha in m.banco.linhas("integrations"):
        if linha.get("purpose") == "attendance":
            linha["is_active"] = False
    mod = _montar(m)
    assert "whatsapp" not in mod["anfitria"] and mod["cta"] is None
    assert "999990003" not in repr(mod)


def test_o_google_so_entra_confirmado_na_config_da_anfitria(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    m.banco.linhas("multicalculo_config").clear()
    assert "google" not in _montar(m)["anfitria"]


# =====================================================================================================================
# o LOGO — só imagem, com teto
# =====================================================================================================================
def _png(tamanho: int) -> bytes:
    return M.PNG_1X1 + b"\0" * max(0, tamanho - len(M.PNG_1X1))


def test_o_logo_aceita_imagem_e_recusa_o_resto():
    corre = asyncio.run
    assert corre(P.logo_embutido(M.LOGO_DATA_URL)) == M.LOGO_DATA_URL
    svg = "data:image/png;base64," + base64.b64encode(b"<svg onload='x()'></svg>").decode()
    assert corre(P.logo_embutido(svg)) is None                         # o cabeçalho mente; os bytes decidem
    grande = "data:image/png;base64," + base64.b64encode(_png(P.TETO_DO_LOGO_BYTES + 1)).decode()
    assert corre(P.logo_embutido(grande)) is None
    no_teto = "data:image/png;base64," + base64.b64encode(_png(P.TETO_DO_LOGO_BYTES)).decode()
    assert corre(P.logo_embutido(no_teto)) == no_teto                  # controle: no teto passa

    async def baixa_png(url):
        assert url == "https://cdn.exemplo.test/logo.png"
        return M.PNG_1X1, "image/png"

    async def explode(url):
        raise TimeoutError("rede")

    assert corre(P.logo_embutido("https://cdn.exemplo.test/logo.png", baixar=baixa_png)) == M.LOGO_DATA_URL
    assert corre(P.logo_embutido("https://cdn.exemplo.test/logo.png", baixar=explode)) is None
    assert corre(P.logo_embutido("http://169.254.169.254/logo.png", baixar=baixa_png)) is None   # só https


# =====================================================================================================================
# validade · arredondamento · juros · nível · a FAQ do caso
# =====================================================================================================================
def test_a_validade_e_hoje_mais_a_menor_validade_do_quadro_na_config(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    assert _montar(m)["validade_ate"] == "2026-10-11"                 # padrão do produto (5 dias), de 06/10
    m.banco.linhas("multicalculo_config")[0]["config"]["validade"] = {"padrao_dias": 9,
                                                                      "por_seguradora": {"Youse": 2}}
    assert _montar(m)["validade_ate"] == "2026-10-08"                 # a MENOR do quadro (a Youse está nele)


def test_o_arredondamento_unico_dos_textos_derivados():
    assert P.arredondar_texto("Franquia de R$ 5.170,54 (R$ 375,54 menor)") == "Franquia de R$ 5.171 (R$ 376 menor)"
    assert P.arredondar_texto("R$ 0,50 e R$ 0,49 e R$ 1.234") == "R$ 1 e R$ 0 e R$ 1.234"
    assert P.arredondar_texto("Em até 10x de R$ 555,83") == "Em até 10x de R$ 555,83"     # a parcela é FATO
    assert P.reais_inteiros(4784.5) == "R$ 4.785" and P.reais_inteiros(4784.49) == "R$ 4.784"


def test_juros_com_nome_e_parcelas_sem_juros_so_quando_batem():
    sem = {"premio_total": 1000.0, "parcelamentos": [{"parcelas": 4, "demais_parcelas": 250.0, "primeira_parcela": 250.0},
                                                     {"parcelas": 10, "demais_parcelas": 115.0,
                                                      "primeira_parcela": 115.0}]}
    assert P._parcelas_sem_juros(sem) == {"vezes": 4, "valor": 250.0}
    assert P._parcelas_sem_juros({"premio_total": 1000.0, "parcelamentos": [{"parcelas": 10,
                                                                               "demais_parcelas": 115.0}]}) is None
    assert P._texto_de_parcela("Em até 10x de R$ 115,00", None) == "Em até 10x de R$ 115,00 com juros"
    assert P._texto_de_parcela("Em até 4x de R$ 250,00", {"vezes": 4}) == "Em até 4x de R$ 250,00 sem juros"


def test_as_opcoes_do_modelo_sem_ref_interno_com_nivel_e_textos_arredondados(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    mod = _montar(m)
    for o in mod["opcoes"]:
        assert "ref" not in o and all("nivel" in c for c in o["coberturas"])
        for t in o["motivos"] + o["o_que_muda"]:
            assert not __import__("re").search(r"(?<!x de )R\$ [\d.]+,\d{2}", t), t
    rec, eco = mod["opcoes"][0], mod["opcoes"][1]
    nivel = lambda o, k: next(c["nivel"] for c in o["coberturas"] if c["chave"] == k)   # noqa: E731
    assert nivel(rec, "reserva") > nivel(eco, "reserva")                # 15 dias × 7 dias
    assert eco["por_que_mais_barata"].startswith(f"Mesma {rec['seguradora']} da recomendada, com franquia normal")


def test_a_faq_e_do_caso_e_so_sobre_opcoes_que_existem(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    sem = _montar(m)
    perguntas = [f["p"] for f in sem["faq"]]
    assert "Qual opção eu tenho hoje?" not in perguntas                 # sem apólice não existe "igual à atual"
    outras = next(f["r"] for f in sem["faq"] if f["p"].startswith("Outras seguradoras"))
    assert f"{sem['resumo']['seguradoras_cotadas']} seguradoras consultadas" in outras
    com = _montar(m, situacao="novo_com_apolice", apolice_atual={"seguradora": "Tokio", "premio_anual": 6100})
    assert com["opcoes"][0]["id"] == "igual_a_atual"
    assert "Qual opção eu tenho hoje?" in [f["p"] for f in com["faq"]]


# =====================================================================================================================
# PUBLICAR — versão nova, recusas antes de gravar
# =====================================================================================================================
def test_publicar_de_novo_e_versao_nova_da_mesma_peca(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    um = asyncio.run(P.publicar_proposta(m.dono, m.pedido_id, "novo_sem_apolice", db=m.db, base_url=BASE))
    dois = asyncio.run(P.publicar_proposta(m.dono, m.pedido_id, "novo_sem_apolice", db=m.db, base_url=BASE))
    assert um["artifact_id"] == dois["artifact_id"] and (um["versao"], dois["versao"]) == (1, 2)
    status = sorted((v["version"], v["status"]) for v in m.banco.linhas("artifact_versions"))
    assert status == [(1, "superseded"), (2, "published")]
    assert len(m.banco.linhas("artifacts")) == 1 and um["token"] != dois["token"]


def test_sem_endereco_publico_nada_e_gravado(monkeypatch):
    for v in ("PUBLIC_APP_URL", "NEXT_PUBLIC_APP_URL", "SMITH_WEB_URL", "FRONTEND_URL"):
        monkeypatch.delenv(v, raising=False)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    with pytest.raises(P.LinkSemEndereco):
        asyncio.run(P.publicar_proposta(m.dono, m.pedido_id, "novo_sem_apolice", db=m.db))
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)


def test_sem_oferta_completa_nada_e_gravado(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    m.banco.linhas("multicalculo_ofertas").clear()
    with pytest.raises(P.PropostaImpossivel):
        asyncio.run(P.publicar_proposta(m.dono, m.pedido_id, "novo_sem_apolice", db=m.db, base_url=BASE))
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)


# =====================================================================================================================
# o COMANDO — ensaio não grava; confirmar publica; saída sem segredo nem comissão
# =====================================================================================================================
def _comando(m, *args):
    saida = io.StringIO()
    codigo = asyncio.run(executar(["--pedido", m.pedido_id, *args], db=m.db, saida=saida))
    return codigo, saida.getvalue()


def test_o_comando_ensaia_sem_gravar_e_publica_com_confirmar(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", "segredo-que-nao-pode-sair-0123456789")
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    codigo, texto = _comando(m, "--nome", "mariana")
    assert codigo == 0 and "ENSAIO" in texto and all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)
    codigo, texto = _comando(m, "--confirmar")
    assert codigo == 0 and f"link: {BASE}/r/" in texto and len(m.banco.linhas("artifacts")) == 1
    for proibido in ("segredo-que-nao-pode-sair", "17,37", "17.37", "comiss", "cifrado-ficticio"):
        assert proibido not in texto.lower()


def test_o_comando_recusa_solicitante_errado_e_pedido_mal_escrito(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    assert _comando(m, "--solicitante", m.alfa, "--confirmar")[0] == 2
    saida = io.StringIO()
    assert asyncio.run(executar(["--pedido", "d0bb15ba"], db=m.db, saida=saida)) == 2
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)


# =====================================================================================================================
# G8 — nenhum número comercial nos arquivos novos da F3 (a mesma varredura da F1)
# =====================================================================================================================
def test_g8_nenhum_numero_comercial_nos_arquivos_da_f3():
    import test_spec130a_a_config as G8

    servico = BACKEND / "app" / "services" / "multicalculo"
    achados = []
    for arq in ("proposta.py", "mensagem.py", "comando_proposta.py"):
        achados += G8.varrer((servico / arq).read_text(encoding="utf-8"), arq)
    assert achados == []
