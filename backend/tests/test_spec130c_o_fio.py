# -*- coding: utf-8 -*-
"""SPEC-130-C · F4 — O TESTE DO FIO (a costura: a saída REAL de uma fatia é a entrada da outra).

    a foto (BYTES de JPEG reais) pelo ESCRITOR da F1 (`brand.fotos.adicionar_foto`) para a corretora A, e OUTRA (outros
    bytes) para a B · o prêmio só para A (`brand.fotos.salvar_premios`)
  → a publicação pelo caminho do PRODUTO: `proposta.publicar_cotacao` (AUTO, o pedido do canário; e RE condomínio, a
    gravação REAL da 129-C pelo leitor e pela linha do motor), `publicar_renovacao` de A e `publicar_proposta` do canal
    (o Quem Cobra Menos, A vencedora) — `montar_anfitria` (F3) → o render (F2) → o Hub
  → o HTML que o `/r/` SERVE (`ArtifactService.abrir_compartilhado`)
  → no HTML servido: a foto de A (o `src` EXATO que o escritor gravou) só nas páginas de A, a de B só nas de B; "premiada"
    só nas de A; o título do bloco pelo momento; o RE sem palavra de carro; a renovação no esqueleto da venda (sem o 3D da
    carteira) com o "1 de N".

Dublê SÓ na borda (CLAUDE.md §9.4): o banco (o `BancoU1` em memória da 129-B, com as travas do U1) e o histórico da
InfoCap da renovação (fora: sem "N anos"). Porta, comparação, leitor, motor, F1, F3, F2 e o Hub são REAIS.

Mutações (o guarda fica VERMELHO — CLAUDE.md §9.3):
  · a F1 lê as fotos SEM o filtro `company_id`              → test_mutacao_fotos_sem_filtro_*
  · `montar_anfitria` sem as fotos (o elo F1 → F3 cortado)   → test_mutacao_montar_anfitria_sem_fotos_*
  · "premiada" sem prêmio (a F3 manda o prêmio de A a todos)  → test_mutacao_premio_de_a_em_todas_*
E o índice ANTIGO (até a migration 20261016_04): a 2ª foto vira a frase do suporte, nunca um 500 cru.

⛔ Dados FICTÍCIOS (CLAUDE.md §13.9). Rodar: cd backend && python -m pytest tests/test_spec130c_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import io
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec130c_as_paginas as AS  # noqa: E402
import test_spec130c_fotos_da_marca as F1T  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.brand import fotos as FOTOS  # noqa: E402
from app.services.brand.capture import EntradaRecusada  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402
from test_spec130a_o_fio import CHROME, texto_visivel  # noqa: E402

BASE = "https://app.exemplo.test"
DONO = "d0d00000-0000-4000-8000-0000000130c4"          # o comercial dono da apólice renovada (da corretora A)
QUEM_SOBE = "c0c00000-0000-4000-8000-0000000130c4"     # quem sobe a foto na Identidade
RENOVACAO = "ae000000-0000-4000-8000-0000000130c4"
MARCA_B = "Vega Seguros Ficticia"
PREMIO_DE_A = "Corretora destaque regional"
#: as palavras de CARRO que nunca aparecem numa página de RE (SPEC §3) — o texto que se LÊ. ⚠️ "veículos" NÃO entra
#: aqui: "Impacto de veículos" é uma cobertura REAL do condomínio (📊 `comparacao.NOME_DA_COBERTURA_RE`, e o exemplo de
#: condomínio de 16/10 a mostra) — a régua sobre o texto inteiro daria alarme falso
PALAVRAS_DE_CARRO = re.compile(r"\b(?:carros?|guinchos?|fipe|b[oô]nus|bater|bati|batida|oficinas?)\b", re.I)
TITULO = {"venda": "Por que fechar com a ", "renovacao": "Mais um ano em boas mãos",
          "canal": "Quem é a corretora que cobra menos?"}


def rodar(coro):
    return asyncio.run(coro)


# =====================================================================================================================
# os BYTES (o que a corretora sobe) — JPEG de verdade, com ruído (não comprime a nada), uma cor por corretora
# =====================================================================================================================
def jpeg(cor) -> bytes:
    from PIL import Image

    base = Image.new("RGB", (1400, 1000), cor)
    ruido = Image.effect_noise((1400, 1000), 30).convert("RGB")
    buf = io.BytesIO()
    Image.blend(base, ruido, 0.25).save(buf, "JPEG", quality=85)
    return buf.getvalue()


# =====================================================================================================================
# o mundo: o canário (o canal em A e B) + um pedido de AUTO de cada corretora + o de renovação de A + o RE de cada uma
# =====================================================================================================================
def clonar_o_canario(banco, *, dono: str, corretoras, servico: str, deslocamento: int) -> str:
    """O pedido do canário gravado de novo (ids novos) como o MOTOR o deixaria, para `dono` — devolve o pedido_id."""
    dados = M.dados_do_canario()
    velhos = ({dados["pedido_id"]} | {e["calculo_id"] for e in dados["estados"]}
              | {e["origem_calculo_id"] for e in dados["estados"] if e.get("origem_calculo_id")}
              | {o["id"] for o in dados["ofertas"]})
    texto = json.dumps(dados, ensure_ascii=False)
    for v in velhos:
        texto = texto.replace(v, str(uuid4()))
    novo = json.loads(texto)
    for ev in novo["eventos"]:
        ev["id"] = int(ev["id"]) + deslocamento
    M.gravar_pedido(banco, novo, dono=dono, corretoras=corretoras, comissao=M.COMISSAO_NO_BANCO)
    next(p for p in banco.linhas("multicalculo_pedidos") if p["id"] == novo["pedido_id"])["servico"] = servico
    return novo["pedido_id"]


def montar(monkeypatch):
    from cryptography.fernet import Fernet

    import test_spec129c_o_app_por_ramo as RE

    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    m = M.montar_mundo(monkeypatch, solicitante="canal")          # o QCM: o pedido do canal em A (vencedora) e B
    a, b = m.alfa, m.beta
    for perfil in m.banco.linhas("brand_profiles"):                # 📊 16/10 as duas corretoras-piloto: marca publicada
        if perfil["company_id"] == b:
            perfil.update({"is_published": True, "display_name": MARCA_B, "susep_code": "SUSEP 10.2030405"})
    m.venda_a = clonar_o_canario(m.banco, dono=a, corretoras=[a], servico="cotacao", deslocamento=1000)
    m.venda_b = clonar_o_canario(m.banco, dono=b, corretoras=[b], servico="cotacao", deslocamento=2000)
    m.renov_a = clonar_o_canario(m.banco, dono=a, corretoras=[a], servico="renovacao", deslocamento=3000)
    seg = next(o["seguradora"] for o in m.banco.linhas("multicalculo_ofertas") if o["pedido_id"] == m.renov_a)
    m.banco.semear("users_v2", {"id": DONO, "first_name": "Bruna Ficticia"})
    m.banco.semear("company_members", {"user_id": DONO, "company_id": a, "status": "active",
                                       "whatsapp_trabalho_e164": "+5548988880130",
                                       "whatsapp_trabalho_confirmado_em": "2026-10-12T10:00:00+00:00"})
    m.banco.semear("renovacoes", {
        "id": RENOVACAO, "company_id": a, "sistema": "infocap", "codfil": 1, "nosnum": "900130",
        "fimvig": "2026-10-20", "ramo_sigla": "AUTO", "seguradora_atual": seg, "premio_atual": 7900.0,
        "cliente_nome_curto": "Ana", "documento_mascarado": "***.***.***-12", "dono_user_id": DONO,
        "estado": "calculada", "pedido_id": m.renov_a, "versao": 1})
    # o RE: a porta REAL abre o pedido; o LEITOR e a LINHA do motor gravam a resposta REAL da gravação da 129-C
    porta = RE.MulticalculoProvider(RE.RepositorioMulticalculo(m.banco.visao("smith-api")),
                                    ambiente={"MULTICALCULO_HMAC_KEY": RE.CHAVE_HMAC}, agora=m.relogio.agora)
    ns = SimpleNamespace(banco=m.banco, relogio=m.relogio, porta=porta, a=a)
    gravacao = RE.GRAVACAO_DO_FIO[PED.RAMO_CONDOMINIO]
    m.re_a = RE.calcular_e_comparar(ns, PED.RAMO_CONDOMINIO, gravacao, company=a)[0].pedido_id
    m.re_b = RE.calcular_e_comparar(ns, PED.RAMO_CONDOMINIO, gravacao, company=b)[0].pedido_id
    return m


def servido(m, token: str) -> str:
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s and s.get("html"), "o link não abriu"
    return s["html"]


def publicar_tudo(m) -> dict:
    """As 6 páginas pelo caminho do produto → {nome: (corretora, momento, HTML SERVIDO)}."""
    a, b = m.alfa, m.beta
    pags = {}
    for nome, cid, pid in (("venda_a", a, m.venda_a), ("venda_b", b, m.venda_b), ("re_a", a, m.re_a),
                           ("re_b", b, m.re_b)):
        r = rodar(P.publicar_cotacao(cid, pid, pessoa_user_id=None, db=m.db, base_url=BASE, primeiro_nome="Ana"))
        pags[nome] = (cid, "venda", servido(m, r["token"]))
    r = rodar(P.publicar_renovacao(a, RENOVACAO, pessoa=DONO, db=m.db, base_url=BASE,
                                   historico=lambda *_a: (_ for _ in ()).throw(RuntimeError("InfoCap fora"))))
    pags["renovacao_a"] = (a, "renovacao", servido(m, r["token"]))
    r = rodar(P.publicar_proposta(m.canal, m.pedido_id, "novo_sem_apolice", db=m.db, base_url=BASE))
    pags["qcm"] = (a, "canal", servido(m, r["token"]))                # a anfitriã do QCM é A (a vencedora do canário)
    return pags


def bloco(doc: str) -> str:
    achado = re.search(r'<section class="s bc" id="corretora".*?</section>', doc, re.S)
    assert achado, "a página servida não tem o bloco da corretora"
    return achado.group(0)


# =====================================================================================================================
# o GUARDA do fio (as mutações no fim do arquivo o deixam VERMELHO)
# =====================================================================================================================
def guarda_o_fio(m) -> dict:
    a, b = m.alfa, m.beta
    # ① a foto e o prêmio pelo ESCRITOR da F1 (os bytes decidem; a foto é reduzida e sai sem EXIF)
    foto_a = FOTOS.adicionar_foto(m.db, a, QUEM_SOBE, jpeg((200, 40, 40)), "A equipe no escritório")["src"]
    foto_b = FOTOS.adicionar_foto(m.db, b, QUEM_SOBE, jpeg((40, 40, 200)), "Nosso atendimento")["src"]
    assert foto_a.startswith("data:image/webp;base64,") and foto_b.startswith("data:image/webp;base64,")
    assert foto_a != foto_b, "controle: as duas fotos têm de ser DIFERENTES para o guarda conseguir falhar"
    assert FOTOS.salvar_premios(m.db, a, QUEM_SOBE, [{"nome": PREMIO_DE_A, "ano": 2025}]) == \
        [{"nome": PREMIO_DE_A, "ano": 2025}]

    # ② as páginas pelo caminho do produto → ③ o HTML que o /r/ SERVE
    pags = publicar_tudo(m)
    minha, outra = {a: foto_a, b: foto_b}, {a: foto_b, b: foto_a}
    for nome, (cid, momento, doc) in pags.items():
        bc = bloco(doc)
        vis = texto_visivel(doc)
        # a foto da corretora DA PÁGINA (o src exato que o escritor gravou), nunca a da outra
        assert f'src="{minha[cid]}"' in bc, f"{nome}: a foto da corretora da página não chegou ao HTML servido"
        assert outra[cid] not in doc, f"{nome}: a foto da OUTRA corretora vazou para a página"
        # "premiada" só com prêmio cadastrado (A); nunca em B (CDC art. 37, D-130C-04)
        if cid == a:
            assert "Corretora premiada" in vis and f"{PREMIO_DE_A} · 2025" in vis, f"{nome}: o prêmio de A não chegou"
        else:
            assert "premiad" not in vis.lower(), f"{nome}: 'premiada' numa corretora sem prêmio"
            assert PREMIO_DE_A not in doc
        # o título do bloco pelo momento
        assert texto_visivel(re.search(r'<h2 id="h-corretora">(.*?)</h2>', bc, re.S).group(1)).startswith(
            TITULO[momento]), f"{nome}: o título do bloco não é o do momento {momento}"
        assert "Corretora Nível 5" in texto_visivel(bc), f"{nome}: o selo do programa sumiu"
    assert texto_visivel(bloco(pags["venda_a"][2])).startswith(f"Por que fechar com a {M.MARCA_ALFA}")
    assert texto_visivel(bloco(pags["venda_b"][2])).startswith(f"Por que fechar com a {MARCA_B}")

    # ④ o RE (condomínio, a gravação REAL): nenhuma palavra de carro no que se lê
    for nome in ("re_a", "re_b"):
        achadas = sorted({x.lower() for x in PALAVRAS_DE_CARRO.findall(texto_visivel(pags[nome][2]))})
        assert achadas == [], f"{nome}: palavra de carro numa página de condomínio: {achadas}"
    # CONTROLE: a régua pega palavra de carro (a página de AUTO a tem) — o guarda consegue ficar vermelho
    assert PALAVRAS_DE_CARRO.search(texto_visivel(pags["venda_a"][2])), "controle: o AUTO deveria falar de carro"

    # ⑤ a renovação no esqueleto da venda: sem o 3D da carteira, com o "1 de N"
    ren = pags["renovacao_a"][2]
    assert not AS.cartao_com_3d(ren), "a renovação voltou ao cartão 3D da carteira"
    assert re.search(r'<body class="[^"]*\bvenda\b', ren) and 'id="count"' in ren

    # ⑥ CONSERTO KA (laudos 130-C), no HTML SERVIDO das 6 páginas: o selo diz compromissos e NUNCA que alguém confere
    #    (D-130C-11); nenhuma chave crua (`{corretora}`); fora do auto nenhuma "Franquia R$ 0" (a gravação REAL de RE)
    for nome, (_cid, _momento, doc) in pags.items():
        assert AS.selo_afirma_o_que_ninguem_confere(doc) == [], f"{nome}: o selo afirma conferência que ninguém faz"
        assert "compromisso" in texto_visivel(bloco(doc)), f"{nome}: o selo sem os compromissos"
        assert AS.chaves_cruas(doc) == [], f"{nome}: chave crua na página: {AS.chaves_cruas(doc)}"
    for nome in ("re_a", "re_b"):
        assert not re.search(r"[Ff]ranquia:?\s+R\$\s*0(?![\d.,]*[1-9])", texto_visivel(pags[nome][2])), \
            f"{nome}: 'Franquia R$ 0' numa página de condomínio"
    return {"pags": pags, "foto_a": foto_a, "foto_b": foto_b}


def test_o_fio_da_foto_na_identidade_ao_html_que_o_cliente_abre(monkeypatch):
    guarda_o_fio(montar(monkeypatch))


# =====================================================================================================================
# as MUTAÇÕES — o elo cortado, o guarda fica VERMELHO
# =====================================================================================================================
def test_mutacao_fotos_sem_filtro_company_id_o_fio_fica_vermelho(monkeypatch):
    """A régua (1) da SPEC: a F1 lê as fotos sem o filtro `company_id` → a página de B mostra a foto de A."""
    m = montar(monkeypatch)

    def sem_filtro(db, company_id, teto=4):
        linhas = (db.table("brand_assets").select("storage_ref, caption, sort_order").eq("kind", "photo")
                  .execute().data or [])
        return [{"src": l["storage_ref"], "legenda": l.get("caption") or ""} for l in linhas][:teto]

    monkeypatch.setattr(FOTOS, "fotos_da_pagina", sem_filtro)
    with pytest.raises(AssertionError, match="OUTRA corretora vazou"):
        guarda_o_fio(m)


def test_mutacao_montar_anfitria_sem_fotos_o_fio_fica_vermelho(monkeypatch):
    """O elo F1 → F3 cortado: `montar_anfitria` não lê as fotos → nenhuma página as mostra."""
    m = montar(monkeypatch)

    async def nenhuma(db, company_id):
        return []

    monkeypatch.setattr(P, "fotos_da_anfitria", nenhuma)
    with pytest.raises(AssertionError, match="não chegou ao HTML servido"):
        guarda_o_fio(m)


def test_mutacao_premio_de_a_em_todas_o_fio_fica_vermelho(monkeypatch):
    """A régua (2): "premiada" numa corretora sem prêmio (a F3 lê os prêmios de A para qualquer página)."""
    m = montar(monkeypatch)
    real = FOTOS.premios
    monkeypatch.setattr(FOTOS, "premios", lambda db, company_id: real(db, m.alfa))
    with pytest.raises(AssertionError, match="corretora sem prêmio"):
        guarda_o_fio(m)


# =====================================================================================================================
# o ÍNDICE ANTIGO (até o Founder rodar a 20261016_04): a 2ª foto vira a frase do suporte — nunca um 500 cru
# =====================================================================================================================
class BancoComOIndiceAntigo(F1T.Banco):
    """O dublê BURRO da F1 + o índice que AINDA está no banco: `brand_assets_one_current_per_kind (company_id, kind)
    WHERE is_current` — recusa a 2ª foto atual com o erro que o PostgREST devolve (código, mensagem, detalhe)."""

    def conferir(self, nome, linha, outras):
        super().conferir(nome, linha, outras)
        if nome == "brand_assets" and linha.get("is_current"):
            for o in outras:
                if (o.get("is_current") and str(o.get("company_id")) == str(linha.get("company_id"))
                        and o.get("kind") == linha.get("kind")):
                    raise _erro_do_postgrest("brand_assets_one_current_per_kind")


def _erro_do_postgrest(indice: str) -> Exception:
    from postgrest.exceptions import APIError

    return APIError({"code": "23505", "message": f'duplicate key value violates unique constraint "{indice}"',
                     "details": "Key (company_id, kind)=(aaaaaaaa-0000-4000-8000-00000000000a, photo) already exists.",
                     "hint": None})


def test_a_2a_foto_com_o_indice_antigo_vira_a_frase_do_suporte_no_servico_e_na_rota(monkeypatch):
    db = BancoComOIndiceAntigo()
    primeira = FOTOS.adicionar_foto(db, F1T.A, F1T.USUARIO, F1T._png(cor=(200, 20, 20)), "primeira")
    assert primeira["src"].startswith("data:image/webp;base64,")
    with pytest.raises(EntradaRecusada) as exc:
        FOTOS.adicionar_foto(db, F1T.A, F1T.USUARIO, F1T._png(cor=(20, 200, 20)), "segunda")
    assert str(exc.value) == FOTOS.FRASE_FALTA_A_MIGRATION
    assert "20261016_04" in str(exc.value) and "suporte" in str(exc.value)
    assert len(db.linhas("brand_assets", company_id=F1T.A)) == 1, "a recusa gravou alguma coisa"
    # a outra corretora não é afetada (o índice é por corretora)
    FOTOS.adicionar_foto(db, F1T.B, F1T.USUARIO, F1T._png(cor=(20, 20, 200)), None)

    # a ROTA do backend (o que o Next repassa à tela em `error`): 400 com a frase, nunca 500
    cli, h = F1T._cliente_da_api(db, monkeypatch)
    r = cli.post("/api/brand/photos", headers=h, data={"company_id": F1T.A},
                 files={"foto": ("foto.jpg", F1T._jpeg(), "image/jpeg")})
    assert r.status_code == 400, r.text
    assert r.json() == {"ok": False, "error": FOTOS.FRASE_FALTA_A_MIGRATION}


def test_so_a_violacao_do_indice_antigo_vira_frase_o_resto_sobe_como_era():
    """CONTROLE: o índice NOVO (`…_exceto_foto`, que começa igual), outro 23505 e um erro qualquer NÃO viram a frase —
    sobem como eram (a rota responde 500 e o log diz). Sem isto o guarda de cima passaria traduzindo TUDO."""
    assert FOTOS.bate_no_indice_antigo(_erro_do_postgrest("brand_assets_one_current_per_kind"))
    assert FOTOS.bate_no_indice_antigo(ValueError(
        '23505 duplicate key value violates unique constraint "brand_assets_one_current_per_kind"'))
    assert not FOTOS.bate_no_indice_antigo(_erro_do_postgrest("brand_assets_one_current_per_kind_exceto_foto"))
    assert not FOTOS.bate_no_indice_antigo(_erro_do_postgrest("brand_assets_pkey"))
    assert not FOTOS.bate_no_indice_antigo(RuntimeError("banco fora"))

    class Outro(F1T.Banco):
        def conferir(self, nome, linha, outras):
            raise _erro_do_postgrest("brand_assets_pkey")

    with pytest.raises(Exception) as exc:
        FOTOS.adicionar_foto(Outro(), F1T.A, F1T.USUARIO, F1T._png(), None)
    assert not isinstance(exc.value, EntradaRecusada) and "brand_assets_pkey" in str(exc.value)


# =====================================================================================================================
# a COSTURA do texto do ramo (a leitura das páginas de exemplo, 16/10) — cada frase errada achada, com o guarda
# =====================================================================================================================
def test_costura_o_texto_do_ramo_sai_certo_da_fonte():
    from app.services.artifacts import proposta_apresentacao as AP
    from app.services.artifacts import proposta_cotacao_html as PV

    # (1) "Das outras 2, 2 não deram preço." repetia o número → "As outras 2 não deram preço."
    assert PV._as_outras({"diferentes": 0, "nr": 2}) == "As outras 2 não deram preço."
    assert PV._as_outras({"diferentes": 3, "nr": 0}) == "As outras 3 só ofereceram produtos diferentes."
    assert PV._as_outras({"diferentes": 4, "nr": 1}) == \
        "Das outras 5, 4 só ofereceram produtos diferentes e 1 não deu preço."          # CONTROLE: o auto de sempre
    # (2) a renovação sem WhatsApp: a corretora fala na 1ª pessoa ("Fale com a gente"), nunca "a corretora" sem nome
    ops = [{"id": "sua_renovacao", "rotulo": "Sua renovação", "parcelas": {"vezes": 12, "valor": 18.93}}]
    for ramo in (PED.RAMO_VIDA, PED.RAMO_CONDOMINIO, 31):
        faq = json.dumps(P.faq_da_renovacao(ramo=ramo, opcoes=ops + [{"id": "franquia_reduzida",
                                                                      "rotulo": "Franquia reduzida"}],
                                            com_whatsapp=False), ensure_ascii=False)
        assert "a corretora" not in faq.lower(), (ramo, faq)
    assert "Fale com a gente se quiser outro valor" in json.dumps(
        P.faq_da_renovacao(ramo=PED.RAMO_VIDA, opcoes=ops, com_whatsapp=False), ensure_ascii=False)
    # (3) "Valor de novo R$ 1": a cobertura SIM/NÃO do RE vira o nome do seguro e "Incluída"; zero some
    modelo = {"ramo": PED.RAMO_RESIDENCIAL}
    linhas = AP.coberturas_para_o_cliente([{"coberturas": [
        {"chave": "valorDeNovo", "nome": "valorDeNovo", "valor": "R$ 1"},
        {"chave": "isDanosEletricos", "nome": "Danos elétricos", "valor": "R$ 80.000"}]}], modelo)[0]["coberturas"]
    assert [(c["nome"], c["valor"]) for c in linhas] == [("Reposição pelo valor de novo", "Incluída"),
                                                        ("Danos elétricos", "R$ 80.000")]
    zero = AP.coberturas_para_o_cliente([{"coberturas": [{"chave": "valorDeNovo", "nome": "valorDeNovo",
                                                          "valor": "R$ 0"}]}], modelo)[0]["coberturas"]
    assert zero == []
    # (4) o motivo "das outras opções comparadas" com UMA opção só na página sai; com 2, fica (a comparação não muda)
    assert P.MOTIVO_DAS_OUTRAS_OPCOES == "Mesma configuração de coberturas das outras opções comparadas"
    from app.services.multicalculo import comparacao as CMP

    assert P.MOTIVO_DAS_OUTRAS_OPCOES in Path(CMP.__file__).read_text(encoding="utf-8"), \
        "a frase da comparação mudou: o filtro da página não casa mais com ela"