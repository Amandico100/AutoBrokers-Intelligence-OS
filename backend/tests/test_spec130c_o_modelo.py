# -*- coding: utf-8 -*-
"""SPEC-130-C · F3 — O MODELO que as páginas leem: as fotos, os prêmios e o selo da corretora DA PÁGINA, e o RAMO certo.

O que é REAL (CLAUDE.md §9.4 — o teste chama o MOTOR): `proposta.montar_proposta` / `publicar_cotacao` (a porta, a
comparação, as opções, a anfitriã), o workflow `cotacao.chat`, o LEITOR do robô e a LINHA do motor sobre as gravações
REAIS de RE (`fixtures/agger_ramos/gravacao_*`) e o script de exemplo. Dublê SÓ na BORDA:
  · o banco (o `BancoU1` em memória dos mundos da 130-A/132-B/129-C);
  · a leitura das fotos/prêmios da marca (`app.services.brand.fotos`, a F1 — escrita em paralelo): um módulo de borda
    que lê `brand_assets(kind='photo')` e `brand_profiles.awards` COM o filtro `company_id`, como o contrato F1↔F3 diz;
  · o Hub (`_gravar_e_compartilhar`/`link_que_ainda_vale`) onde o teste só precisa do MODELO — o (e) publica de verdade.

Os guardas e as mutações (CLAUDE.md §9.3 — o guarda consegue ficar vermelho; registradas na entrega da F3):
  (a) duas corretoras com fotos DIFERENTES (bytes conhecidos): a página de A só tem as de A — venda, renovação, QCM
      (A vencedora; o canal técnico também tem foto, para o vazamento aparecer) e o exemplo.
      Mutação: o QCM lê as fotos pelo company_id do SOLICITANTE (o canal) → VERMELHO.
  (b) RE (16/2/18) e vida (91): `bem`, `faq`, `sinistro`, `venda` sem palavra de carro.
      Mutação: a FAQ de auto de volta no RE (`pagina_da_cotacao` ignora o ramo) → VERMELHO.
  (c) AUTO byte a byte: o modelo de hoje = o do commit base (ee4f3eb) fora `anfitria.fotos/premios/selo`.
  (d) a vida PUBLICA a página (o workflow) — revê a D-129D-16.
  (e) a leitura das fotos falha → a página é publicada sem fotos.
⛔ Nenhum nome de corretora (CLAUDE.md §13.9): os do mundo são fictícios. Nenhum CPF/telefone real.
Rodar: cd backend && python -m pytest tests/test_spec130c_o_modelo.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec132b_a_conversa as B  # noqa: E402
import test_spec132b_a_pagina_de_venda as V  # noqa: E402
from test_spec132b_a_conversa import ambiente, mundo  # noqa: E402,F401  (fixtures do (d))

from app.services.cotacao import workflow as WF  # noqa: E402
from app.services.multicalculo import comparacao as CMP  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import manual_de_negociacao as MANUAL  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402
from scripts import publicar_exemplo_da_pagina as EX  # noqa: E402

BASE = "https://app.exemplo.test"
AGORA = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
#: as palavras de CARRO que nunca aparecem numa página de RE ou de vida (SPEC §3)
PALAVRAS_DE_CARRO = re.compile(r"\b(?:carros?|guinchos?|fipe|b[oô]nus|bater|bati|batida|oficinas?|ve[ií]culos?)\b",
                               re.I)
RAMOS_SEM_CARRO = (PED.RAMO_CONDOMINIO, PED.RAMO_RESIDENCIAL, PED.RAMO_EMPRESARIAL, PED.RAMO_VIDA)


def rodar(coro):
    return asyncio.run(coro)


# =====================================================================================================================
# a BORDA da F1: as fotos e os prêmios da marca, lidos COM o filtro company_id (o contrato F1↔F3)
# =====================================================================================================================
def webp(cor) -> bytes:
    """Uma imagem WEBP pequena e DISTINTA por cor (os bytes provam de quem é a foto)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), cor).save(buf, "WEBP", quality=90)
    return buf.getvalue()


def data_url(dados: bytes) -> str:
    return "data:image/webp;base64," + base64.b64encode(dados).decode("ascii")


class BordaDasFotos:
    """O `app.services.brand.fotos` de borda: o MESMO contrato da F1 (`fotos_da_pagina(db, company_id, teto)` e
    `premios(db, company_id)`), lendo o banco dublê com o filtro `company_id` no SELECT."""

    def __init__(self, falhar: bool = False):
        self.lidas, self.falhar = [], falhar

    def fotos_da_pagina(self, db, company_id, teto=4):
        self.lidas.append(("fotos", company_id))
        if self.falhar:
            raise RuntimeError("o storage das fotos caiu")
        linhas = (db.table("brand_assets").select("id, company_id, kind, storage_ref, caption, sort_order")
                  .eq("company_id", company_id).eq("kind", "photo").execute().data or [])
        linhas = sorted((l for l in linhas if l.get("company_id") == company_id), key=lambda l: l.get("sort_order") or 0)
        return [{"src": l["storage_ref"], "legenda": l.get("caption") or ""} for l in linhas][:teto]

    def premios(self, db, company_id):
        self.lidas.append(("premios", company_id))
        linhas = (db.table("brand_profiles").select("company_id, awards").eq("company_id", company_id)
                  .execute().data or [])
        return [dict(a) for l in linhas if l.get("company_id") == company_id for a in (l.get("awards") or [])]


class EspiaoDaF1(BordaDasFotos):
    """O módulo REAL da F1 (`app.services.brand.fotos`), com um olho em QUEM foi lido (o company_id de cada leitura)."""

    def __init__(self):
        super().__init__()
        from app.services.brand import fotos as REAL

        self.real = REAL

    def fotos_da_pagina(self, db, company_id, teto=4):
        self.lidas.append(("fotos", company_id))
        return self.real.fotos_da_pagina(db, company_id, teto=teto)

    def premios(self, db, company_id):
        self.lidas.append(("premios", company_id))
        return self.real.premios(db, company_id)


def instalar_borda(monkeypatch, borda: Optional[BordaDasFotos] = None) -> BordaDasFotos:
    """Sem `borda`: a F1 REAL com o espião (o preferido). Com `borda`: o dublê (a falha do (e))."""
    import app.services.brand as pacote

    borda = borda or EspiaoDaF1()
    mod = types.ModuleType("app.services.brand.fotos")
    mod.fotos_da_pagina, mod.premios = borda.fotos_da_pagina, borda.premios
    monkeypatch.setitem(sys.modules, "app.services.brand.fotos", mod)
    monkeypatch.setattr(pacote, "fotos", mod, raising=False)
    return borda


def semear_marca(banco, company_id: str, cor, premio: str) -> bytes:
    """Duas fotos (a 2ª de outra cor) e um prêmio para a corretora; devolve os bytes da 1ª."""
    dados = webp(cor)
    banco.semear("brand_assets", {"id": str(uuid4()), "company_id": company_id, "kind": "photo",
                                  "storage_ref": data_url(dados), "caption": f"foto de {premio}", "sort_order": 1,
                                  "is_current": True, "mime_type": "image/webp"})
    banco.semear("brand_assets", {"id": str(uuid4()), "company_id": company_id, "kind": "photo",
                                  "storage_ref": data_url(webp(tuple(255 - c for c in cor))), "caption": "",
                                  "sort_order": 2, "is_current": True, "mime_type": "image/webp"})
    perfis = [b for b in banco.linhas("brand_profiles") if b["company_id"] == company_id]
    if perfis:
        perfis[0]["awards"] = [{"nome": premio, "ano": 2025}]
    else:
        banco.semear("brand_profiles", {"company_id": company_id, "is_published": False,
                                        "awards": [{"nome": premio, "ano": 2025}]})
    return dados


def bytes_das_fotos(modelo) -> list:
    return [base64.b64decode(f["src"].split(",", 1)[1]) for f in (modelo.get("anfitria") or {}).get("fotos") or []]


def capturar_o_hub(monkeypatch, modulo=P) -> list:
    """A borda do Hub: `publicar_cotacao` devolve o MODELO sem gravar artefato (o (e) publica de verdade)."""
    vistos = []

    def gravar(db, company_id, pedido_id, modelo, ctx, base, **kw):
        vistos.append(modelo)
        return {"url": f"{base}/r/tok", "token": "tok", "artifact_id": str(uuid4()), "versao": 1}

    monkeypatch.setattr(modulo, "_gravar_e_compartilhar", gravar)
    monkeypatch.setattr(modulo, "link_que_ainda_vale", lambda *a, **k: None)
    return vistos


# =====================================================================================================================
# (a) DUAS CORRETORAS — a foto de A nunca na página de B (venda, renovação, QCM com A vencedora, exemplo)
# =====================================================================================================================
def test_a_qcm_mostra_as_fotos_da_vencedora_nunca_do_canal_nem_da_outra(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    borda = instalar_borda(monkeypatch)
    foto_a = semear_marca(m.banco, m.alfa, (200, 30, 30), "Prêmio A")
    foto_b = semear_marca(m.banco, m.beta, (30, 30, 200), "Prêmio B")
    foto_canal = semear_marca(m.banco, m.canal, (30, 200, 30), "Prêmio do canal")
    modelo = rodar(P.montar_proposta(m.canal, m.pedido_id, "novo_sem_apolice", db=m.db, agora=AGORA))
    assert modelo["origem"] == "canal"
    fotos = bytes_das_fotos(modelo)
    assert fotos and fotos[0] == foto_a, "a página do QCM não mostra a foto da corretora VENCEDORA"
    assert foto_b not in fotos and foto_canal not in fotos, "foto de outra corretora (ou do canal) na página"
    assert modelo["anfitria"]["premios"] == [{"nome": "Prêmio A", "ano": 2025}]
    assert {cid for _q, cid in borda.lidas} == {m.alfa}, f"leu a marca de quem não é a anfitriã: {borda.lidas}"
    # o selo do canal segue a regra de sempre (D-130A1-04)
    assert modelo["anfitria"]["selo"] == CFG.PADRAO_DO_PRODUTO["canal"]["selo"]["nome"]


def test_a_venda_e_a_renovacao_da_corretora_so_com_as_fotos_dela(monkeypatch):
    m = V.mundo(monkeypatch)                                   # o pedido da beta, pedido pela própria beta
    borda = instalar_borda(monkeypatch)
    foto_a = semear_marca(m.banco, m.alfa, (200, 30, 30), "Prêmio A")
    foto_b = semear_marca(m.banco, m.beta, (30, 30, 200), "Prêmio B")
    vistos = capturar_o_hub(monkeypatch)
    rodar(P.publicar_cotacao(m.beta, m.pedido_id, pessoa_user_id=V.CORRETOR, db=m.db, base_url=BASE, agora=AGORA))
    venda = vistos[-1]
    assert bytes_das_fotos(venda)[0] == foto_b and foto_a not in bytes_das_fotos(venda)
    assert venda["anfitria"]["premios"] == [{"nome": "Prêmio B", "ano": 2025}]
    assert venda["anfitria"]["selo"] == "Corretora Nível 5", "o selo do programa não chegou à página de venda"
    # a RENOVAÇÃO (o modelo que `publicar_renovacao` monta): a MESMA anfitriã, as MESMAS fotos
    seg = venda["opcoes"][0]["seguradora"]
    ren = rodar(P.montar_proposta(m.beta, m.pedido_id, "renovacao", {"seguradora": seg}, db=m.db, agora=AGORA))
    assert bytes_das_fotos(ren)[0] == foto_b and foto_a not in bytes_das_fotos(ren)
    assert {cid for _q, cid in borda.lidas} == {m.beta}


def test_a_o_exemplo_de_cada_corretora_com_as_fotos_dela(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    instalar_borda(monkeypatch)
    foto_a = semear_marca(m.banco, m.alfa, (200, 30, 30), "Prêmio A")
    foto_b = semear_marca(m.banco, m.beta, (30, 30, 200), "Prêmio B")
    for cid, minha, outra in ((m.alfa, foto_a, foto_b), (m.beta, foto_b, foto_a)):
        modelo, _ctx, _pid = rodar(EX.montar_modelo_de_exemplo(EX.SoLeitura(m.db), cid, "venda", agora=AGORA))
        assert bytes_das_fotos(modelo)[0] == minha and outra not in bytes_das_fotos(modelo)


def test_a_sem_foto_o_exemplo_desenha_4_ilustracoes_marcadas_e_a_corretora_real_nao(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    instalar_borda(monkeypatch)                # ninguém tem foto (📊 16/10: nenhuma corretora tem)
    modelo, _c, _p = rodar(EX.montar_modelo_de_exemplo(EX.SoLeitura(m.db), m.alfa, "venda", agora=AGORA))
    fotos = modelo["anfitria"]["fotos"]
    assert [f["legenda"] for f in fotos] == list(EX.LEGENDAS_ILUSTRATIVAS)
    for f in fotos:
        dados = base64.b64decode(f["src"].split(",", 1)[1])
        assert dados[:4] == b"RIFF" and dados[8:12] == b"WEBP" and len(dados) <= EX.TETO_DA_ILUSTRACAO
    assert modelo["anfitria"]["premios"] == [EX.PREMIO_DE_EXEMPLO] and modelo["exemplo"] is True
    sem, _c, _p = rodar(EX.montar_modelo_de_exemplo(EX.SoLeitura(m.db), m.alfa, "venda", agora=AGORA,
                                                    sem_fotos=True, sem_premio=True))
    assert sem["anfitria"]["fotos"] == [] and sem["anfitria"]["premios"] == []
    # CONTROLE: a página REAL da mesma corretora, sem foto cadastrada, NÃO ganha ilustração nem prêmio
    real = rodar(P.montar_proposta(m.canal, m.pedido_id, "novo_sem_apolice", db=m.db, agora=AGORA))
    assert real["anfitria"]["fotos"] == [] and real["anfitria"]["premios"] == []
    assert not [l for l in m.banco.linhas("brand_assets") if l.get("kind") == "photo"], "o exemplo gravou foto"


def test_a_o_selo_a_corretora_desliga_e_nao_renomeia(monkeypatch):
    cfg = CFG.mesclar(None, "cotacao")
    s = "SUSEP 202031234"                                     # conserto KB (D-130C-11): o selo exige a SUSEP
    assert P.selo_da_corretora(cfg, susep=s) == "Corretora Nível 5"
    assert P.selo_da_corretora(CFG.mesclar({"canal": {"selo": {"ligado": False}}}, "cotacao"), susep=s) is None
    assert P.selo_da_corretora(CFG.mesclar({"canal": {"selo": {"nome": "Corretora Nota 10"}}}, "cotacao"),
                               susep=s) == "Corretora Nível 5", "a corretora renomeou o selo do programa (D-130A1-04)"
    for sem in (None, "", "   "):                             # sem SUSEP → sem selo, com a config ligada
        assert P.selo_da_corretora(cfg, susep=sem) is None, repr(sem)
    assert P.selo_da_corretora(cfg) is None, "fechado por padrão: quem não passa a SUSEP não ganha o selo"
    assert P.criterios_do_selo(cfg) is None, "itens do selo inventados (a config não os tem)"
    assert P.criterios_do_selo({"canal": {"selo_criterios": [["SUSEP ativa", "conferida"]]}}) == [["SUSEP ativa",
                                                                                                    "conferida"]]


def test_a_foto_que_nao_e_imagem_nunca_entra(monkeypatch):
    """A cerca de saída: SVG com script, URL externa e PNG falso (bytes de executável) não viram foto."""
    class Torta(BordaDasFotos):
        def fotos_da_pagina(self, db, company_id, teto=4):
            svg = base64.b64encode(b"<svg onload=alert(1)>").decode()
            return [{"src": "data:image/svg+xml;base64," + svg, "legenda": "x"},
                    {"src": "https://exemplo.test/foto.webp", "legenda": "x"},
                    {"src": "data:image/png;base64," + base64.b64encode(b"MZ\x90\x00executavel").decode(),
                     "legenda": "x"},
                    {"src": data_url(webp((1, 2, 3))), "legenda": "y" * 200}]

    instalar_borda(monkeypatch, Torta())
    fotos = rodar(P.fotos_da_anfitria(None, str(uuid4())))
    assert len(fotos) == 1 and len(fotos[0]["legenda"]) == P.TETO_DA_LEGENDA


# =====================================================================================================================
# (b) RE e VIDA — o bem, as dúvidas e o "se acontecer" do ramo, sem nenhuma palavra de carro
# =====================================================================================================================
def _palavras_de_carro(modelo) -> list:
    texto = json.dumps({k: modelo.get(k) for k in ("bem", "faq", "sinistro", "venda")}, ensure_ascii=False)
    return sorted({x.lower() for x in PALAVRAS_DE_CARRO.findall(texto)})


@pytest.fixture
def mundo_re(monkeypatch):
    """O mundo da 129-C (a porta REAL sobre o banco dublê; o motor grava as RESPOSTAS REAIS das gravações)."""
    import test_spec129c_o_app_por_ramo as RE
    from cryptography.fernet import Fernet

    RE.instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    relogio = RE.D.Relogio(AGORA)
    banco = RE.BancoU1(relogio)
    canal, a, b = (str(uuid4()) for _ in range(3))
    banco.semear("companies", {"id": canal, "company_kind": "platform_canal", "is_technical": True})
    for c in (a, b):
        banco.semear("companies", {"id": c, "company_kind": "client", "company_name": "Corretora Ficticia"})
    porta = RE.MulticalculoProvider(RE.RepositorioMulticalculo(banco.visao("smith-api")),
                                    ambiente={"MULTICALCULO_HMAC_KEY": RE.CHAVE_HMAC}, agora=relogio.agora)
    return SimpleNamespace(banco=banco, relogio=relogio, porta=porta, canal=canal, a=a, b=b, RE=RE,
                           db=banco.visao("smith-api"))


@pytest.mark.parametrize("ramo", [PED.RAMO_CONDOMINIO, PED.RAMO_RESIDENCIAL, PED.RAMO_EMPRESARIAL])
def test_b_re_a_venda_a_carteira_e_a_renovacao_sem_palavra_de_carro(mundo_re, monkeypatch, ramo):
    m = mundo_re
    aberto, _ped, q, _and = m.RE.calcular_e_comparar(m, ramo, m.RE.GRAVACAO_DO_FIO[ramo])
    vistos = capturar_o_hub(monkeypatch)
    rodar(P.publicar_cotacao(m.a, aberto.pedido_id, pessoa_user_id=None, db=m.db, base_url=BASE, agora=AGORA))
    venda = vistos[-1]
    assert venda["ramo"] == ramo
    assert venda["bem"] == {"rotulo": P.ROTULO_DO_BEM[ramo], "descricao": None, "ano": None, "apelido": None}
    assert _palavras_de_carro(venda) == [], _palavras_de_carro(venda)
    assert any("cobertura básica" in f["p"] for f in venda["faq"]), "a FAQ não é a do ramo"
    assert venda["sinistro"] == MANUAL.sinistro_padrao(None, com_whatsapp=False, ramo=ramo)
    # a carteira (o `_faq` das objeções) e a renovação (`faq_da_renovacao`) do MESMO pedido
    carteira = rodar(P.montar_proposta(m.a, aberto.pedido_id, "novo_sem_apolice", db=m.db, agora=AGORA))
    assert carteira["faq"] and _palavras_de_carro(carteira) == [], _palavras_de_carro(carteira)
    seg = carteira["opcoes"][0]["seguradora"]
    ren = rodar(P.montar_proposta(m.a, aberto.pedido_id, "renovacao", {"seguradora": seg}, db=m.db, agora=AGORA))
    assert ren["faq"] and _palavras_de_carro(ren) == [], _palavras_de_carro(ren)
    # nada pessoal no bem: o nome, o CPF/CNPJ e o endereço do pedido (sintéticos) não chegam ao modelo
    tudo = json.dumps(venda, ensure_ascii=False)
    for pessoal in ("Rua Ficticia", "Condominio Ficticio", "Pessoa Ficticia", "Empresa Ficticia", m.RE.CPF, m.RE.CNPJ):
        assert pessoal not in tudo, pessoal


@pytest.mark.parametrize("ramo", RAMOS_SEM_CARRO)
@pytest.mark.parametrize("pagina", ["venda", "renovacao"])
def test_b_o_exemplo_de_cada_ramo_pelo_leitor_e_pela_comparacao_sem_palavra_de_carro(monkeypatch, ramo, pagina):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    instalar_borda(monkeypatch)
    modelo, _c, _p = rodar(EX.montar_modelo_de_exemplo(EX.SoLeitura(m.db), m.alfa, pagina, ramo=ramo, agora=AGORA))
    assert modelo["ramo"] == ramo and modelo["bem"]["rotulo"] == P.ROTULO_DO_BEM[ramo]
    assert modelo["opcoes"] and all(o["premio_anual"] > 0 for o in modelo["opcoes"])
    assert _palavras_de_carro(modelo) == [], _palavras_de_carro(modelo)
    if ramo != PED.RAMO_VIDA:                                 # as opções são as da gravação REAL (o ranking contado à mão)
        import test_spec129c_o_app_por_ramo as RE

        assert modelo["ranking"][0]["seguradora"] == RE.ESPERADO[ramo]["ranking"][0][0]
    else:                                                     # 📊 o canário de vida: a Porto, R$ 227,16/ano
        assert [(o["seguradora"], o["premio_anual"]) for o in modelo["opcoes"]][0][1] == 227.16


def test_b_vida_as_duvidas_falam_de_capital_e_saude_e_nunca_inventam_prazo():
    ops = [{"id": "sua_renovacao", "rotulo": "Sua renovação", "parcelas": {"vezes": 12, "valor": 18.93}}]
    faq = P.faq_da_renovacao(ramo=PED.RAMO_VIDA, opcoes=ops, vence_em="2026-11-20", com_whatsapp=True,
                             reajuste_capital_pct=5.0)
    texto = json.dumps(faq, ensure_ascii=False)
    assert "art. 766" in texto and "capital" in texto and "reajustado em 5 %" in texto and "20/11/2026" in texto
    assert not re.search(r"\b(car[eê]ncia|\d+\s*dias|prazo)\b", texto, re.I), "prazo/carência inventados"
    assert PALAVRAS_DE_CARRO.findall(texto) == []
    venda = CFG.pagina_da_cotacao(CFG.mesclar(None, "cotacao"), ramo=PED.RAMO_VIDA)
    assert any("766" in f["resposta"] for f in venda["faq"]) and not re.search(r"vistoria", json.dumps(venda), re.I)


def test_b_o_auto_continua_igual_nas_funcoes_de_texto():
    cfg = CFG.mesclar(None, "cotacao")
    assert CFG.pagina_da_cotacao(cfg, ramo=CMP.RAMO_AUTO) == CFG.pagina_da_cotacao(cfg) == CFG.pagina_da_cotacao(None)
    assert len(CFG.pagina_da_cotacao(cfg)["faq"]) == 7 and "E se eu bater o carro?" in json.dumps(
        CFG.pagina_da_cotacao(cfg), ensure_ascii=False)
    for w in (True, False):
        assert MANUAL.sinistro_padrao(cfg, com_whatsapp=w, ramo=CMP.RAMO_AUTO) == MANUAL.sinistro_padrao(
            cfg, com_whatsapp=w)
    # a lista PRÓPRIA da corretora vale no auto; fora dele, os passos do ramo (foram escritos para carro)
    proprio = {"sinistro": ["Ligue para nós se bater o carro"]}
    assert MANUAL.sinistro_padrao(proprio) == ["Ligue para nós se bater o carro"]
    assert PALAVRAS_DE_CARRO.findall(" ".join(MANUAL.sinistro_padrao(proprio, ramo=PED.RAMO_RESIDENCIAL))) == []


# =====================================================================================================================
# (c) AUTO byte a byte — o modelo de hoje = o do commit base (ee4f3eb) fora anfitria.fotos/premios/selo
# =====================================================================================================================
#: 📊 16/10/2026: `scratchpad/f3/antes.py` roda `retratos_do_auto` com o `proposta.py` do commit base (`git show
#: ee4f3eb:…`, carregado ao lado) e com o de hoje — os dois deram ESTES hashes (o retrato é o de ANTES da F3).
RETRATO_DO_AUTO = {
    "canal_qcm": "cbd8aac9c62ded11dcb5e5c9ee63ab8b2188375b3d5a2d6248521da13906de38",
    "carteira": "db46a7ccc356bb9da66032eb2082db07039a7101840316ac1889dab0584911ba",
    "renovacao": "3b2e77ec5845f088faa3f9b5c7d344a30c1077839473ef9dae7b1a9ca37e2c19",
    "venda": "9764523dad24247a836f2bf7e4af93e90531b8f00d2504b3e03915675843c032",
}


def _normalizado(modelo) -> str:
    m = json.loads(json.dumps(modelo, ensure_ascii=False, default=str))
    m.pop("gerado_em", None)
    anf = m.get("anfitria") or {}
    for k in ("fotos", "premios"):
        anf.pop(k, None)
    if m.get("origem") != "canal":                            # na carteira o selo é NOVO; no canal ele não muda
        anf.pop("selo", None)
        anf.pop("selo_criterios", None)
    return hashlib.sha256(json.dumps(m, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def retratos_do_auto(modulo) -> dict:
    """Os 4 modelos de AUTO (QCM, carteira, renovação, venda) montados por `modulo` (o proposta.py de hoje ou o do
    commit base) sobre os MESMOS mundos — o hash de cada um, normalizado."""
    from _pytest.monkeypatch import MonkeyPatch

    saida = {}
    mp = MonkeyPatch()
    try:
        m = M.montar_mundo(mp, solicitante="canal")
        saida["canal_qcm"] = _normalizado(rodar(modulo.montar_proposta(m.canal, m.pedido_id, "novo_sem_apolice",
                                                                       db=m.db, agora=AGORA)))
    finally:
        mp.undo()
    mp = MonkeyPatch()
    try:
        m = V.mundo(mp)
        saida["carteira"] = _normalizado(rodar(modulo.montar_proposta(m.beta, m.pedido_id, "novo_sem_apolice",
                                                                      db=m.db, agora=AGORA)))
        vistos = capturar_o_hub(mp, modulo)
        rodar(modulo.publicar_cotacao(m.beta, m.pedido_id, pessoa_user_id=V.CORRETOR, db=m.db, base_url=BASE,
                                      agora=AGORA, primeiro_nome="Ana"))
        saida["venda"] = _normalizado(vistos[-1])
        seg = vistos[-1]["opcoes"][0]["seguradora"]
        saida["renovacao"] = _normalizado(rodar(modulo.montar_proposta(m.beta, m.pedido_id, "renovacao",
                                                                       {"seguradora": seg}, db=m.db, agora=AGORA)))
    finally:
        mp.undo()
    return saida


def test_c_o_modelo_de_auto_e_o_de_antes_fora_os_tres_campos_novos():
    assert retratos_do_auto(P) == RETRATO_DO_AUTO


# =====================================================================================================================
# (d) a VIDA publica a página (o workflow `cotacao.chat`) — revê a D-129D-16 (D-130C-08)
# =====================================================================================================================
def test_d_a_entrega_de_vida_publica_a_pagina_como_os_outros_ramos(mundo, monkeypatch):
    monkeypatch.setenv(PED.ENV_VIDA, "1")
    m = mundo
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    from test_spec129d_cotacao_nova import VIDA_COMPLETA, _cota

    _cota(m, a, uid, sess, **VIDA_COMPLETA)
    [ped] = m.pedidos(a)
    assert ped["ramo"] == PED.RAMO_VIDA

    class PortaDasOfertas:          # a borda: o que o robô de vida trouxe (📊 o canário V3 da 129-D prova o real)
        async def consultar(self, *, company_id, pedido_id):
            return SimpleNamespace(estados=[{"status": "fechado"}],
                                   ofertas=[{"seguradora": "Seguradora Alfa", "premio_total": 227.16}])

    publicadas = []

    async def publicar_cotacao(company_id, pedido_id, *, pessoa_user_id, apolice_atual=None, db=None,
                               primeiro_nome=None, **_kw):          # a borda: a publicação (o modelo é o (b)/(c))
        publicadas.append((company_id, pedido_id))
        return {"token": "tokvida", "url": B.LINK_BASE + "tokvida", "artifact_id": str(uuid4()),
                "resumo": {"opcoes": [{"id": "recomendada", "papel": "Recomendada", "seguradora": "Seguradora Alfa",
                                       "parcela": {"vezes": 12, "valor": 18.93, "sem_juros": True},
                                       "a_vista": 227.16, "franquia": None}]}}

    monkeypatch.setattr(WF, "_porta", lambda db: PortaDasOfertas())
    monkeypatch.setattr(P, "publicar_cotacao", publicar_cotacao)
    m.rodar_runs(a)
    assert publicadas == [(a, ped["id"])], "a vida não publicou a página (ou publicou de outro pedido)"
    [msg] = m.mensagens_do_assistente(conversa)
    texto = msg["content"]
    assert f"Apresentação para o cliente: {B.LINK_BASE}" in texto and "página de vida" not in texto.lower(), texto
    assert not hasattr(WF, "NOTA_DA_VIDA") and not hasattr(WF, "_opcoes_de_vida_sem_pagina")


# =====================================================================================================================
# (e) a leitura das fotos FALHA → a página é publicada assim mesmo, sem fotos (nunca cai)
# =====================================================================================================================
def test_e_a_leitura_das_fotos_falha_e_a_pagina_sai_sem_fotos(monkeypatch):
    m = V.mundo(monkeypatch)
    borda = instalar_borda(monkeypatch, BordaDasFotos(falhar=True))
    semear_marca(m.banco, m.beta, (30, 30, 200), "Prêmio B")
    pub = rodar(P.publicar_cotacao(m.beta, m.pedido_id, pessoa_user_id=V.CORRETOR, db=m.db, base_url=BASE,
                                   agora=AGORA))
    assert pub["url"].startswith(f"{BASE}/r/") and pub["modelo"]["anfitria"]["fotos"] == []
    assert pub["modelo"]["anfitria"]["premios"] == [{"nome": "Prêmio B", "ano": 2025}], "um erro apagou o outro"
    assert ("fotos", m.beta) in borda.lidas
    html = V._servido(m, pub["token"])
    assert "data:image/webp" not in html
    # e sem o módulo da F1 (ImportError) também: listas vazias, nunca exceção
    monkeypatch.setitem(sys.modules, "app.services.brand.fotos", None)
    import app.services.brand as pacote
    monkeypatch.delattr(pacote, "fotos", raising=False)
    anf = rodar(P.montar_anfitria(m.db, m.beta, CFG.mesclar(None, "cotacao")))
    assert anf["fotos"] == [] and anf["premios"] == []


# =====================================================================================================================
# CONSERTO KB — (1) o selo Nível 5 fora do canal só com a SUSEP · (2) o capital da vida no modelo · (7) a etiqueta
# =====================================================================================================================
def _perfil(m, cid):
    return next(b for b in m.banco.linhas("brand_profiles") if b["company_id"] == cid)


def test_kb1_duas_corretoras_o_selo_nivel_5_so_na_que_tem_susep(monkeypatch):
    """Red team BLOCKER 1 (D-130C-11): a corretora SEM SUSEP saía "Nível 5 · Registro ativo na SUSEP". Duas corretoras
    com a marca PUBLICADA e a config padrão (selo ligado): a alfa com SUSEP ganha o selo; a beta, sem, não."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    instalar_borda(monkeypatch)
    beta = _perfil(m, m.beta)
    beta.update(is_published=True, palette=_perfil(m, m.alfa)["palette"])     # publicada como a alfa, SEM SUSEP
    cfg = CFG.mesclar(None, "cotacao")
    com = rodar(P.montar_anfitria(m.db, m.alfa, cfg))
    sem = rodar(P.montar_anfitria(m.db, m.beta, cfg))
    assert com["susep"] == "SUSEP 202031234" and com["selo"] == "Corretora Nível 5"
    assert sem["marca_cadastrada"] is True and "susep" not in sem
    assert "selo" not in sem and "selo_criterios" not in sem, "Nível 5 sem SUSEP preenchida (CDC art. 37)"
    beta["susep_code"] = "   "                                                 # só espaços = vazia
    assert "selo" not in rodar(P.montar_anfitria(m.db, m.beta, cfg))


def test_kb1_a_venda_real_sem_susep_sai_sem_selo_e_o_canal_segue_a_regra_dele(monkeypatch):
    """O caminho do produto: `publicar_cotacao` da corretora sem SUSEP → sem selo (com SUSEP o (a) acima prova o selo).
    CONTROLE: o QCM (o canal) segue a regra de hoje — a vencedora sem SUSEP continua com o selo do CANAL."""
    m = V.mundo(monkeypatch)
    instalar_borda(monkeypatch)
    _perfil(m, m.beta)["susep_code"] = None
    vistos = capturar_o_hub(monkeypatch)
    rodar(P.publicar_cotacao(m.beta, m.pedido_id, pessoa_user_id=V.CORRETOR, db=m.db, base_url=BASE, agora=AGORA))
    assert "selo" not in vistos[-1]["anfitria"] and "susep" not in vistos[-1]["anfitria"]
    c = M.montar_mundo(monkeypatch, solicitante="canal")
    instalar_borda(monkeypatch)
    _perfil(c, c.alfa)["susep_code"] = ""
    qcm = rodar(P.montar_proposta(c.canal, c.pedido_id, "novo_sem_apolice", db=c.db, agora=AGORA))
    assert qcm["origem"] == "canal" and qcm["anfitria"]["selo"] == CFG.PADRAO_DO_PRODUTO["canal"]["selo"]["nome"]


def test_kb2_o_capital_da_vida_e_a_origem_pelo_leitor_real():
    """O elo (D-129D-17): o LEITOR grava `capital_pedido` quando a seguradora não ecoa o capital (📊 a Porto do canário
    16/10) e `isAppMorte` quando ecoa. `capital_da_vida` lê os dois, com a origem — e nunca inventa."""
    import test_spec129d_portal_vida as PV

    porto = PV._oferta_lida(PV._item_da_porto_do_canario(), capital_pedido=100000.0)        # sem eco → o pedido
    assert P.capital_da_vida(porto) == {"valor": 100000.0, "origem": "pedido"}
    eco = PV._oferta_lida(PV._item_da_porto_do_canario(isAppMorte=150000), capital_pedido=100000.0)
    assert P.capital_da_vida(eco) == {"valor": 150000.0, "origem": "seguradora"}
    assert P.capital_da_vida(PV._oferta_lida(PV._item_da_porto_do_canario())) is None      # nada → nada
    for ruim in ({}, None, {"capital_pedido": 0}, {"isAppMorte": True}, {"capital_pedido": "Selecione"},
                 {"isAppMorte": -1}, {"capital_pedido": float("nan")}):
        assert P.capital_da_vida(ruim) is None, ruim


def test_kb2_as_opcoes_de_vida_levam_o_capital_e_o_auto_nunca():
    ops = [{"id": "recomendada", "ref": {"oferta_id": "o1", "opcao": "padrao"}, "motivos": [], "o_que_muda": [],
            "coberturas": [], "parcelas": None, "premio_anual": 227.16, "seguradora": "Porto Seguro"}]
    vida = [{"id": "o1", "coberturas": {"capital_pedido": 100000}}]
    cfg = CFG.mesclar(None, "cotacao")
    [o], _b = P.opcoes_da_pagina(ops, vida, cfg, ramo=PED.RAMO_VIDA)
    assert o["capital_segurado"] == {"valor": 100000.0, "origem": "pedido"}
    # no AUTO `isAppMorte` é a APP por passageiro (📊 test_spec131a: 5000) — nunca vira "capital segurado"
    auto = [{"id": "o1", "coberturas": {"isAppMorte": 5000}}]
    for ramo in (CMP.RAMO_AUTO, None):
        [a], _b = P.opcoes_da_pagina(ops, auto, cfg, ramo=ramo)
        assert "capital_segurado" not in a
    [sem], _b = P.opcoes_da_pagina(ops, [{"id": "o1", "coberturas": {}}], cfg, ramo=PED.RAMO_VIDA)
    assert "capital_segurado" not in sem, "capital inventado numa oferta sem número"


@pytest.mark.parametrize("pagina", ["venda", "renovacao"])
def test_kb2_o_exemplo_de_vida_leva_o_capital_do_pedido_na_porto_do_canario(monkeypatch, pagina):
    """O exemplo de vida (o leitor REAL sobre o resultado gravado + a Porto do canário, o capital do CORPO real
    `vida_calcularV2_corpo.json`): a Porto R$ 227,16 leva o capital PEDIDO, marcado como tal."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    instalar_borda(monkeypatch)
    modelo, _c, _p = rodar(EX.montar_modelo_de_exemplo(EX.SoLeitura(m.db), m.alfa, pagina, ramo=PED.RAMO_VIDA,
                                                       agora=AGORA))
    porto = next(o for o in modelo["opcoes"] if o["premio_anual"] == 227.16)
    assert porto["capital_segurado"] == {"valor": 100000.0, "origem": "pedido"}, porto.get("capital_segurado")


def test_kb7_a_etiqueta_exemplo_longe_do_canto():
    """Laudo de design 130-C: o canto arredondado do cartão cortava o "EXEMPLO" (a 28 px do canto). Agora a etiqueta
    fica a ≥ 8 % do maior lado, nos dois eixos — o pixel do canto antigo é FUNDO, o da nova posição é a etiqueta."""
    from PIL import Image

    assert EX.margem_da_etiqueta(960, 640) >= 0.08 * 960
    for f in EX.ilustracoes_da_marca(None):
        img = Image.open(io.BytesIO(base64.b64decode(f["src"].split(",", 1)[1]))).convert("RGB")
        mg = EX.margem_da_etiqueta(*img.size)
        assert min(img.getpixel((mg + 12, mg + 27))) >= 215, "a etiqueta não está na margem nova"
        assert min(img.getpixel((40, 40))) < 215, "a etiqueta continua colada ao canto"
