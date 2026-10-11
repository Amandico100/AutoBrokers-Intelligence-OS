# -*- coding: utf-8 -*-
"""SPEC-129-C · F2 — o lado do APP por ramo: pedido, porta, config e comparação (U6 · U7 · U8).

O FIO DESTA FATIA (por ramo: condomínio 16 · residencial 2 · empresarial 18):
    PedidoDeCalculo.de_dict(ramo, risco)  → MulticalculoProvider.calcular (REAL: autorização, comissão do ramo pela
    config, o validador do CONTRATO, as coberturas pelo resolvedor dos PRESETS, cifra) → banco DUBLÊ
    (`dubles.banco_multicalculo.BancoU1`, o PostgREST em memória com as travas do U1) → as RESPOSTAS REAIS das 9
    gravações (`fixtures/agger_ramos/gravacao_*.json`) lidas pelo LEITOR real (`leitor_agger.ler_rodada` +
    `eventos_do_calculo`) e gravadas pela LINHA real do motor (`Motor._linha_da_oferta`) → `porta.consultar` +
    `config.carregar` (REAIS) → `comparacao.comparar` → o ranking.

O contrato do pedido de RE, o resolvedor das coberturas e o LEITOR de RE são os da F1 (`contrato.CAMPOS_DO_PEDIDO_RE`
· `problemas_do_pedido_re` · `presets.coberturas_re` · `leitor_agger.COBERTURAS_DA_OFERTA_RE`) — usados como estão.
Dublê só na BORDA: o banco (PostgREST em memória) e a resposta do Agger (as gravações reais).
§9.3: no começo da fatia o leitor perdia a básica de RE (lista branca de auto); a F1 a trouxe — a lição migrou para
`test_oferta_sem_a_basica_cai_na_regua_generica_e_avisa` (a régua de RE nunca é inventada sem a básica).
⛔ Dado SINTÉTICO (CNPJ/CPF/endereço inventados); as gravações já vêm saneadas; nenhum nome de corretora (§13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129c_o_app_por_ramo.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
from app.services.multicalculo import comparacao as C  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo.porta import (MulticalculoProvider, PedidoIncompleto, RamoNaoSuportado,  # noqa: E402
                                             coberturas_de_re, cpf_hmac)
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from dubles.banco_multicalculo import BancoU1, instalar_esquema  # noqa: E402
from portal_worker.multicalculo import contrato as K  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as PRE  # noqa: E402
from portal_worker.multicalculo.leitor_agger import eventos_do_calculo, ler_rodada  # noqa: E402

FIX = BACKEND / "tests" / "fixtures" / "agger_ramos"
CHAVE_HMAC = "chave-hmac-ficticia-129c-0123456789"
CNPJ = "11222333000181"
CPF = "52998224725"
NOME_RAMO = {16: "condominio", 2: "residencial", 18: "empresarial"}


def carregar(nome: str) -> dict:
    return json.loads((FIX / f"{nome}.json").read_text(encoding="utf-8"))


# =====================================================================================================================
# O formulário da TELA → o contrato (para a contagem INDEPENDENTE do que o pedido tem de trazer)
# =====================================================================================================================
#: campo do FORMULÁRIO (fixture) → (grupo, campo do contrato da F1). O que não está aqui é COBERTURA (vem da opção) ou
#: vigência (o robô preenche) — e por isso NÃO é do pedido.
MAPA_DO_FORMULARIO = {
    "comum": {"cpfCnpj": ("segurado", "cpf_cnpj"), "nome": ("segurado", "nome"), "dataNasc": ("segurado", "nascimento"),
              "fone": ("segurado", "telefone"), "email": ("segurado", "email"), "cep": ("risco", "cep"),
              "uf": ("risco", "uf"), "cidade": ("risco", "cidade"), "bairro": ("risco", "bairro"),
              "logradouro": ("risco", "logradouro"), "numero": ("risco", "numero"),
              "complemento": ("risco", "complemento"), "isDanosIncendioRaioExplosao": ("risco", "valor_basica"),
              "valorDeNovo": ("risco", "valor_de_novo"), "imovelObjetoSegurado": ("risco", "objeto")},
    16: {"imovelAtividade": ("risco", "tipo_imovel"), "anoFundacao": ("risco", "ano_fundacao"),
         "estruturaCondominio": ("risco", "estrutura"), "qtdBlocos": ("risco", "blocos"),
         "qtdElevadores": ("risco", "elevadores"), "pavimentos": ("risco", "pavimentos")},
    2: {"imovelConstrucao": ("risco", "construcao"), "imovelTipoResidencia": ("risco", "tipo_imovel"),
        "imovelUso": ("risco", "uso")},
    18: {"imovelPavimentacao": ("risco", "pavimento"), "imovelConstrucao": ("risco", "construcao"),
         "imovelLocalEstabelecimento": ("risco", "localizacao"),
         "imovelAtividadeProfissionalLocal": ("risco", "atividade")},
}


def _coberturas_do_formulario(f: dict) -> set:
    """As chaves de COBERTURA da tela (as do pacote da conta + a assistência) — vêm da OPÇÃO, nunca do pedido."""
    return set(f["pacote_prata_da_conta"][0]["coberturas"]) | {"assist24hs"}


# =====================================================================================================================
# Os pedidos de cada ramo — os CÓDIGOS das gravações reais (às vezes como o RÓTULO da tela), o resto sintético
# =====================================================================================================================
ENDERECO = {"cep": "88000-000", "uf": "SC", "cidade": "Cidade Ficticia", "bairro": "Centro",
            "logradouro": "Rua Ficticia", "numero": "100"}
GRAVACAO_DO_FIO = {16: "gravacao_condominio_1", 2: "gravacao_residencial_2", 18: "gravacao_empresarial_2"}


def _extras_da_gravacao(nome: str) -> dict:
    """As coberturas que o corretor MANDOU naquele negócio real (> 0), menos a básica e a assistência."""
    g = carregar(nome)
    cob = set(PRE.CHAVES_DE_COBERTURA_RE[g["ramo"]]) - {"assist24hs", PED.CHAVE_DA_BASICA}
    return {k: v for k, v in g["versao"]["configuracoes"].items()
            if k in cob and isinstance(v, (int, float)) and not isinstance(v, bool) and v}


def dados(ramo: int, **troca) -> dict:
    cfg = carregar(GRAVACAO_DO_FIO[ramo])["versao"]["configuracoes"]
    risco = {**ENDERECO, "valor_basica": cfg[PED.CHAVE_DA_BASICA], "extras": _extras_da_gravacao(GRAVACAO_DO_FIO[ramo])}
    if ramo == 16:
        seg = {"cpf_cnpj": "11.222.333/0001-81", "nome": "Condominio Ficticio"}
        risco.update(tipo_imovel="Residencial", estrutura="Vertical", ano_fundacao=cfg["anoFundacao"],
                     blocos=cfg["qtdBlocos"], pavimentos=cfg["pavimentos"], elevadores=cfg["qtdElevadores"])
    elif ramo == 2:
        seg = {"cpf_cnpj": CPF, "nome": "Pessoa Ficticia", "nascimento": "01/02/1980"}
        risco.update(construcao="Superior", tipo_imovel=cfg["imovelTipoResidencia"], uso="Habitual",
                     objeto="Prédio + Conteúdo")
    else:
        seg = {"cpf_cnpj": CNPJ, "nome": "Empresa Ficticia"}
        risco.update(pavimento="Térreo", construcao=cfg["imovelConstrucao"], localizacao="Outros",
                     atividade="Escritório", cnae="6911701", objeto=cfg["imovelObjetoSegurado"])
    d = {"segurado": seg, "risco": risco}
    for g, v in troca.items():
        d[g] = {**d.get(g, {}), **v}
    return d


# =====================================================================================================================
# O mundo: duas corretoras + o canal, a porta REAL sobre o banco dublê
# =====================================================================================================================
@pytest.fixture
def mundo(monkeypatch):
    from cryptography.fernet import Fernet

    instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    relogio = D.Relogio(datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))
    banco = BancoU1(relogio)
    canal, a, b = (str(uuid4()) for _ in range(3))
    banco.semear("companies", {"id": canal, "company_kind": "platform_canal", "is_technical": True})
    for c in (a, b):
        banco.semear("companies", {"id": c, "company_kind": "client"})
        banco.semear("multicalculo_adesoes", {"canal_company_id": canal, "corretora_company_id": c, "ativa": True})
    # a corretora A configurou: comissão do empresarial 7,5 % e a Tokio como a preferida no condomínio
    banco.semear("multicalculo_config", {"company_id": a, "config": {
        "comissao": {"por_ramo": {"18": 7.5}}, "preferencias_de_seguradoras": {"16": ["Tokio"]}}})
    porta = MulticalculoProvider(RepositorioMulticalculo(banco.visao("smith-api")),
                                 ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC}, agora=relogio.agora)
    return SimpleNamespace(banco=banco, relogio=relogio, porta=porta, canal=canal, a=a, b=b)


def rodar(coro):
    return asyncio.run(coro)


def motor_grava_a_gravacao(m, pedido_id: str, calculo: dict, gravacao: dict, *, sem_basica: bool = False):
    """O que o MOTOR grava da resposta: o LEITOR real lê os itens da gravação e a LINHA real do motor monta a oferta."""
    ramo = gravacao["ramo"]
    rodada = ler_rodada({"calculos": gravacao["calculos"], "ramo": ramo})
    g = SimpleNamespace(pedido_id=pedido_id, company_id=calculo["company_id"],
                        solicitante_company_id=calculo["solicitante_company_id"])
    fake = SimpleNamespace(agora=m.relogio.agora)
    for resp in rodada.respostas:
        for o in resp.ofertas:
            linha = MOT.Motor._linha_da_oferta(fake, g, calculo, o, nova=True)
            if sem_basica:                                   # um leitor que perdesse a básica (o de antes da F1)
                linha["coberturas"].pop(PED.CHAVE_DA_BASICA, None)
            m.banco.semear("multicalculo_ofertas", linha)
    for i, e in enumerate(eventos_do_calculo([rodada])):
        if e.tipo == K.SEGURADORA_RECUSOU:
            m.banco.semear("multicalculo_eventos", {
                "calculo_id": calculo["id"], "pedido_id": pedido_id, "company_id": calculo["company_id"],
                "solicitante_company_id": calculo["solicitante_company_id"], "tipo": e.tipo,
                "seguradora": e.seguradora, "seguradora_codigo": e.seguradora_codigo, "familia": e.familia,
                "chave": f"rec|{i}", "t_s": 1.0})


def calcular_e_comparar(m, ramo: int, gravacao: str, *, company=None, sem_basica=False, eventos_extra=()):
    company = company or m.a
    pedido = PED.PedidoDeCalculo.de_dict(dados(ramo), ramo=ramo)
    aberto = rodar(m.porta.calcular(company_id=company, pedido=pedido, origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos")
                if c["pedido_id"] == aberto.pedido_id and c["opcao"] == "padrao")
    motor_grava_a_gravacao(m, aberto.pedido_id, calc, carregar(gravacao), sem_basica=sem_basica)
    for ev in eventos_extra:
        m.banco.semear("multicalculo_eventos", {"calculo_id": calc["id"], "pedido_id": aberto.pedido_id,
                                                "company_id": company, "solicitante_company_id": company, **ev})
    cfg, andamento = rodar(m.porta._config_e_andamento(company_id=company, pedido_id=aberto.pedido_id))
    ped = next(p for p in m.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
    q = C.comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg, ramo=ped["ramo"])
    return aberto, ped, q, andamento


def _contagem_independente(gravacao: str):
    """Da gravação CRUA, sem o código do produto: quantas seguradoras deram preço e quantas não."""
    itens = carregar(gravacao)["calculos"]
    com = [i for i in itens if any(isinstance(r, dict) and (r.get("premio") or 0) > 0 for r in i.get("resultados") or [])]
    return len(com), len(itens) - len(com)


# =====================================================================================================================
# 🔴 O TESTE DO FIO, por ramo
# =====================================================================================================================
#: 📊 o esperado CONTADO À MÃO nas gravações (resultados[].coberturas · premio), com a régua escrita na SPEC:
#:  condomínio_1: HDI sem impacto/RC condomínio/portões, Porto sem impacto, Axa sem RC síndico → só Allianz e Tokio
#:  residencial_2: as 8 com básica 550.000, elétricos 10.000 e vendaval 45.000 (RC não vem em nenhuma → não exigida)
#:  empresarial_2: Tokio sem danos elétricos (4 das 5 o trazem) → Chubb, HDI, Bradesco, Porto
ESPERADO = {
    16: {"ranking": [("Allianz", 10427.56), ("Tokio Marine", 13841.45)],
         "diferentes": {"HDI", "Axa", "Porto"}, "recusas": {"Chubb", "Bradesco"}},
    2: {"ranking": [("Bradesco", 475.48), ("Zurich", 511.68), ("Allianz", 568.32), ("Mapfre", 568.37),
                    ("Yelum", 641.13), ("HDI", 752.12), ("Tokio Marine", 1246.3), ("Porto", 1654.76)],
        "diferentes": set(), "recusas": set()},
    18: {"ranking": [("Chubb", 333.84), ("HDI", 413.2), ("Bradesco", 553.84), ("Porto", 678.89)],
         "diferentes": {"Tokio Marine"}, "recusas": {"Axa", "Mapfre", "Allianz", "Yelum"}},
}


@pytest.mark.parametrize("ramo", [16, 2, 18])
def test_o_fio_por_ramo_pedido_porta_banco_leitor_comparacao(mundo, ramo):
    m = mundo
    aberto, ped, q, andamento = calcular_e_comparar(m, ramo, GRAVACAO_DO_FIO[ramo])

    # ── o pedido gravado com o RAMO certo e o risco CIFRADO, como o do auto ──
    assert ped["ramo"] == ramo and ped["origem"] == "auxiliar" and ped["opcoes"] == ["padrao", "economica"]
    assert CNPJ not in ped["pedido_cifrado"] and CPF not in ped["pedido_cifrado"]
    assert "Rua Ficticia" not in ped["pedido_cifrado"] and "88000000" not in ped["pedido_cifrado"]
    from app.services import portal_vault

    claro = json.loads(portal_vault.decrypt(ped["pedido_cifrado"]))
    doc = CNPJ if ramo in (16, 18) else CPF
    assert claro["ramo"] == ramo and claro["segurado"]["cpf_cnpj"] == doc
    assert K.problemas_do_pedido_re(claro) == ()          # o dict cifrado é o que o CONTRATO aceita (o robô o lê)
    assert ped["cpf_hmac"] == cpf_hmac(doc, chave=CHAVE_HMAC)
    assert claro["risco"]["cep"] == "88000000" and claro["risco"]["valor_basica"] == float(
        carregar(GRAVACAO_DO_FIO[ramo])["versao"]["configuracoes"][PED.CHAVE_DA_BASICA])
    # os rótulos viraram os CÓDIGOS medidos na tela (fixture formulario_*)
    if ramo == 16:
        assert (claro["risco"]["tipo_imovel"], claro["risco"]["estrutura"]) == (1, 1)
    elif ramo == 2:
        assert (claro["risco"]["construcao"], claro["risco"]["uso"], claro["risco"]["objeto"]) == (4, 1, 3)
        assert claro["segurado"]["nascimento"] == "1980-02-01"
    else:
        assert (claro["risco"]["pavimento"], claro["risco"]["localizacao"]) == ("0", "0")
    # D-129C-05: a comissão EXPLÍCITA do ramo (A configurou 7,5 no empresarial; os outros = a entrada)
    assert claro["comissao_desconto"]["comissao_percentual"] == (7.5 if ramo == 18 else 15.0)
    # ── as coberturas de cada cálculo: o resolvedor dos presets (F1) com a BÁSICA e as extras do PEDIDO ──
    calcs = {c["opcao"]: c for c in m.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id}
    assert set(calcs) == {"padrao", "economica"}
    basica, extras = claro["risco"]["valor_basica"], claro["risco"]["extras"]
    assert extras
    for opcao, c in calcs.items():
        assert c["coberturas"] == PRE.coberturas_re(ramo, opcao, basica, extras)
        assert c["coberturas"][PED.CHAVE_DA_BASICA] == basica
        assert all(c["coberturas"][k] == v for k, v in extras.items())

    # ── a comparação: o ranking por prêmio anual, conferido contra a contagem à mão e a contagem crua ──
    esp = ESPERADO[ramo]
    assert q.resumo["regua"] == "re"
    assert [(l["seguradora"], l["premio_anual"]) for l in q.ranking()] == esp["ranking"]
    assert {d["seguradora"] for d in q.diferentes} == esp["diferentes"]
    assert {r["seguradora"] for r in q.nao_responderam} == esp["recusas"]
    com_preco, sem_preco = _contagem_independente(GRAVACAO_DO_FIO[ramo])
    assert len(q.ranking()) + len(q.diferentes) == com_preco and len(q.nao_responderam) == sem_preco
    premios = [l["premio_anual"] for l in q.ranking()]
    assert premios == sorted(premios)
    # 🔴 G3: a margem que a resposta de RE traz DENTRO das coberturas (percComissao) não sai da comparação
    for l in q.ranking():
        assert not any(k.lower().startswith("perccomissao") for k in l["coberturas_brutas"])
    ops = C.opcoes(q, situacao="novo_sem_apolice", config=CFG.mesclar(None))
    assert ops and all("comissao" not in json.dumps(o["coberturas"]).lower() for o in ops)
    assert all(c["nome"] != c["chave"] for o in ops for c in o["coberturas"] if c["chave"] in C.NOME_DA_COBERTURA_RE)


def test_os_motivos_do_condominio_dizem_o_que_falta_em_portugues(mundo):
    _a, _p, q, _and = calcular_e_comparar(mundo, 16, "gravacao_condominio_1")
    motivos = {d["seguradora"]: d["motivo"] for d in q.diferentes}
    assert motivos["HDI"] == "não inclui Impacto de veículos, RC Condomínio, Portões"
    assert motivos["Porto"] == "não inclui Impacto de veículos"
    assert motivos["Axa"] == "não inclui RC Síndico"
    assert {r["seguradora"]: r["motivo"] for r in q.nao_responderam}["Chubb"] == "não aceitou este risco"


def test_a_preferida_e_marcada_e_nunca_esconde_as_outras(mundo):
    """D-129C-07: A prefere a Tokio no condomínio — ela é MARCADA, continua em 2º (o preço manda) e a Allianz fica."""
    _a, _p, q, _and = calcular_e_comparar(mundo, 16, "gravacao_condominio_1")
    linhas = {l["seguradora"]: l for l in q.ranking()}
    assert linhas["Tokio Marine"]["preferida"] is True and linhas["Tokio Marine"]["ordem_de_preferencia"] == 1
    assert linhas["Allianz"]["preferida"] is False and [l["seguradora"] for l in q.ranking()][0] == "Allianz"
    # a corretora B não tem preferência: ninguém marcado, mesmo ranking
    _a, _p, qb, _and = calcular_e_comparar(mundo, 16, "gravacao_condominio_1", company=mundo.b)
    assert not any(l["preferida"] for l in qb.ranking())
    assert [l["seguradora"] for l in qb.ranking()] == [l["seguradora"] for l in q.ranking()]


def test_no_mesmo_premio_a_preferida_vem_antes():
    a = "a0000000-0000-4000-8000-0000000000c1"
    estados = [{"calculo_id": "c1", "corretora_company_id": a, "opcao": "padrao"}]
    base = {"calculo_id": "c1", "corretora_company_id": a, "premio_total": 900.0, "pacote": "P",
            "coberturas": {PED.CHAVE_DA_BASICA: 500000, "isDanosEletricos": 10000}}
    ofertas = [dict(base, id="o1", seguradora="Allianz", seguradora_codigo=5),
               dict(base, id="o2", seguradora="Tokio", seguradora_codigo=11)]
    sem = C.comparar(ofertas, estados=estados, ramo=2)
    assert [l["seguradora"] for l in sem.ranking()] == ["Allianz", "Tokio Marine"]
    cfg = CFG.mesclar({"preferencias_de_seguradoras": {"2": [11]}})        # por CÓDIGO do Agger
    com = C.comparar(ofertas, estados=estados, ramo=2, config=cfg)
    assert [l["seguradora"] for l in com.ranking()] == ["Tokio Marine", "Allianz"]


def test_a_seguradora_sem_atividade_compativel_sai_listada(mundo):
    """D-129C-04: o robô anuncia a seguradora sem atividade inequívoca (`contrato.SEM_ATIVIDADE_COMPATIVEL`) — a
    comparação a LISTA, em frase de gente."""
    ev = {"tipo": K.SEM_ATIVIDADE_COMPATIVEL, "seguradora": "Sura", "seguradora_codigo": 49, "familia": K.DADO,
          "chave": "sem_ativ|49", "t_s": 0.5}
    _a, _p, q, _and = calcular_e_comparar(mundo, 18, "gravacao_empresarial_2", eventos_extra=[ev])
    rec = {r["seguradora"]: r for r in q.nao_responderam}
    assert rec["Sura"]["motivo"] == "não tem na lista dela a atividade deste negócio"
    assert {l["seguradora"] for l in q.ranking()} == {s for s, _ in ESPERADO[18]["ranking"]}


def test_oferta_sem_a_basica_cai_na_regua_generica_e_avisa(mundo):
    """📊 11/10 (início da fatia): o leitor com a lista branca de AUTO descartava a básica de RE. Se isso voltar, a
    comparação NÃO inventa a régua de RE: cai para a genérica E o resumo diz `generica_sem_basica` (visível)."""
    _a, _p, q, _and = calcular_e_comparar(mundo, 16, "gravacao_condominio_1", sem_basica=True)
    assert q.resumo["regua"] == "generica_sem_basica"


def test_basica_diferente_da_maioria_nao_e_comparavel():
    """A seguradora que calculou OUTRA básica (incêndio) não entra no ranking — o preço seria de outro seguro.
    📊 nenhuma das 9 gravações tem básica divergente (a mutação m10 passava verde): este guarda a regra."""
    a = "a0000000-0000-4000-8000-0000000000c3"
    estados = [{"calculo_id": "c1", "corretora_company_id": a, "opcao": "padrao"}]

    def of(i, seg, cod, premio, basica):
        return {"id": f"o{i}", "calculo_id": "c1", "corretora_company_id": a, "premio_total": premio, "pacote": "P",
                "seguradora": seg, "seguradora_codigo": cod,
                "coberturas": {PED.CHAVE_DA_BASICA: basica, "isDanosEletricos": 10000, "isDanosVendaval": 45000}}

    q = C.comparar([of(1, "Allianz", 5, 700.0, 550000), of(2, "HDI", 4, 650.0, 550000),
                    of(3, "Mapfre", 3, 400.0, 300000)], estados=estados, ramo=2)
    assert [l["seguradora"] for l in q.ranking()] == ["HDI", "Allianz"]
    assert [(d["seguradora"], d["chave_motivo"]) for d in q.diferentes] == [("Mapfre", "basica_diferente")]
    assert "R$ 300.000" in q.diferentes[0]["motivo"] and "R$ 550.000" in q.diferentes[0]["motivo"]


def test_a_margem_dentro_das_coberturas_nunca_sai_da_comparacao():
    """🔴 G3 (2ª rede): 📊 as 9 gravações trazem `percComissao` DENTRO de `resultados[].coberturas` (ex.: 30). O leitor
    da F1 o tira; se uma linha o trouxer mesmo assim, a comparação não o põe no ranking nem nas linhas públicas."""
    a = "a0000000-0000-4000-8000-0000000000c2"
    estados = [{"calculo_id": "c1", "corretora_company_id": a, "opcao": "padrao"}]
    of = {"id": "o1", "calculo_id": "c1", "corretora_company_id": a, "premio_total": 900.0, "pacote": "P",
          "seguradora": "Allianz", "seguradora_codigo": 5,
          "coberturas": {PED.CHAVE_DA_BASICA: 500000, "percComissao": 30, "percDescontoResid": 5}}
    q = C.comparar([of], estados=estados, ramo=2)
    linha = q.ranking()[0]
    assert set(linha["coberturas_brutas"]) == {PED.CHAVE_DA_BASICA}
    assert [c["chave"] for c in C.coberturas_publicas(of, ramo=2)] == [PED.CHAVE_DA_BASICA]


@pytest.mark.parametrize("nome", sorted(p.stem for p in FIX.glob("gravacao_*.json")))
def test_as_9_gravacoes_passam_pela_comparacao_sem_perder_seguradora(mundo, nome):
    g = carregar(nome)
    _a, _p, q, _and = calcular_e_comparar(mundo, g["ramo"], nome)
    com_preco, sem_preco = _contagem_independente(nome)
    assert len(q.ranking()) + len(q.diferentes) == com_preco and len(q.nao_responderam) == sem_preco
    assert q.ranking(), nome                               # toda gravação real tem ao menos uma comparável
    assert q.resumo["regua"] == "re"


# =====================================================================================================================
# O pedido e a porta por ramo: o que falta, o que não tem código, o canal, as opções, a renovação
# =====================================================================================================================
def test_o_que_cada_formulario_exige_e_o_que_o_pedido_cobra():
    """📊 os obrigatórios da TELA (43 · 33 · 16, fixtures) menos as coberturas (vêm da opção) e a vigência (o robô
    preenche) = o que o PEDIDO tem de trazer — contado à parte e conferido contra o que o CONTRATO cobra. Diferenças
    DECLARADAS: `valor_de_novo` é obrigatório na tela do condomínio/residencial mas opcional no contrato (a tela abre
    em "Sim" — vai como observação ao juiz); a comissão é do contrato (D-129C-05), não da tela."""
    for ramo, n_tela in ((16, 43), (2, 33), (18, 16)):
        f = carregar(f"formulario_{NOME_RAMO[ramo]}")
        obrig = [c["campo"] for c in f["campos"] if c.get("obrigatorio")]
        assert len(obrig) == f["n_obrigatorios"] == n_tela
        do_pedido = {c for c in obrig if c not in _coberturas_do_formulario(f) - {PED.CHAVE_DA_BASICA}
                     and c not in ("vigenciaIni", "vigenciaFim")}
        mapa = {**MAPA_DO_FORMULARIO["comum"], **MAPA_DO_FORMULARIO[ramo]}
        assert do_pedido <= set(mapa), do_pedido - set(mapa)
        esperado = {".".join(mapa[c]) for c in do_pedido} - {"risco.valor_de_novo"}
        esperado |= {"comissao_desconto.comissao_percentual"}
        assert set(PED.PedidoDeCalculo.de_dict({}, ramo=ramo).faltando()) == esperado, ramo


def test_pedido_de_re_incompleto_volta_com_o_campo_que_falta(mundo):
    m = mundo
    sem = dados(18)
    del sem["risco"]["valor_basica"], sem["risco"]["atividade"]
    with pytest.raises(PedidoIncompleto) as e:
        rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(sem, ramo=18), origem="auxiliar"))
    assert set(e.value.campos) == {"risco.valor_basica", "risco.atividade"}
    # sem código medido: o rótulo que a tela não tem, a básica que não é número
    ruim = dados(2, risco={"construcao": "Madeira de lei", "valor_basica": "muito"})
    with pytest.raises(PedidoIncompleto) as e2:
        rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(ruim, ramo=2), origem="auxiliar"))
    assert set(e2.value.campos) == {"risco.construcao", "risco.valor_basica"}
    # a extra fora das coberturas do ramo, e a básica disfarçada de extra (ela é `risco.valor_basica`)
    fora = PED.PedidoDeCalculo.de_dict(dados(2, risco={"extras": {"bike": 3000, "garagista": 1,
                                                                  PED.CHAVE_DA_BASICA: 9}}), ramo=2)
    assert fora.sem_codigo() == ["risco.extras.garagista", f"risco.extras.{PED.CHAVE_DA_BASICA}"]
    # renovação de RE → pergunta antes os QUATRO que a tela exige marcada a renovação (costura 129-C: o contrato pedia
    # só a seguradora anterior; 📊 formulario_*.json `libera_quando` — a lição migrou, §9.3)
    renov = PED.PedidoDeCalculo.de_dict(dados(16, renovacao={"renovacao": "sim"}), ramo=16)
    assert renov.renovacao is True and renov.com_comissao(10).faltando() == [
        "renovacao.fim_vigencia_anterior", "renovacao.seguradora_anterior", "renovacao.sinistros_anterior",
        "renovacao.bonus_anterior"]
    zero = PED.PedidoDeCalculo.de_dict(dados(16, renovacao={"renovacao": "sim", "seguradora_anterior": "HDI",
                                                            "fim_vigencia_anterior": "31/10/2026",
                                                            "sinistros_anterior": 0, "bonus_anterior": 0}), ramo=16)
    assert zero.com_comissao(10).faltando() == []                 # 0 sinistro e bônus 0 são RESPOSTAS, não vazios
    assert m.banco.linhas("multicalculo_pedidos") == []          # nada gravado em nenhuma recusa
    with pytest.raises(PED.CampoDesconhecido):
        PED.PedidoDeCalculo.de_dict(dados(2, veiculo={"placa": "ABC1D23"}), ramo=2)   # grupo do carro no RE


def test_o_canal_com_ramo_de_re_e_recusado_sem_gravar(mundo):
    m = mundo
    pedido = PED.PedidoDeCalculo.de_dict(dados(16), ramo=16)
    with pytest.raises(RamoNaoSuportado):
        rodar(m.porta.calcular(company_id=m.canal, pedido=pedido, corretoras=[m.a], origem="canal"))
    with pytest.raises(RamoNaoSuportado):
        rodar(m.porta.calcular(company_id=m.a, pedido=pedido, origem="canal"))
    with pytest.raises(RamoNaoSuportado):                            # o canal como "auxiliar" também não
        rodar(m.porta.calcular(company_id=m.canal, pedido=pedido, corretoras=[m.a], origem="auxiliar"))
    assert m.banco.linhas("multicalculo_pedidos") == [] and m.banco.linhas("multicalculo_calculos") == []
    cap = m.porta.capacidades(16)
    assert cap["suportado"] and cap["canal"] is False and cap["opcoes"] == ("padrao", "economica")
    assert "canal" not in cap["origens"] and m.porta.capacidades(5)["suportado"] is False


def test_opcoes_de_re_sao_padrao_e_mais_em_conta(mundo):
    m = mundo
    pedido = PED.PedidoDeCalculo.de_dict(dados(2), ramo=2)
    for opcao in ("completa_mais", "minima"):
        with pytest.raises(ValueError, match="opções aceitas: padrao, economica"):
            rodar(m.porta.calcular(company_id=m.a, pedido=pedido, opcoes=("padrao", opcao), origem="auxiliar"))
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=pedido, opcoes=("economica",), origem="auxiliar"))
    assert [c["opcao"] for c in aberto.calculos] == ["economica"]


def test_a_basica_e_sempre_a_do_pedido_mesmo_com_coberturas_explicitas(mundo):
    """D-129C-03: quem chama pode mandar as coberturas da opção — a Básica continua a do PEDIDO."""
    m = mundo
    explicitas = {"padrao": {PED.CHAVE_DA_BASICA: 1, "assist24hs": 2, "isDanosEletricos": 7000}}
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(dados(2), ramo=2),
                                    opcoes=("padrao",), coberturas=explicitas, origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    assert calc["coberturas"] == {PED.CHAVE_DA_BASICA: 550000.0, "assist24hs": 2, "isDanosEletricos": 7000}
    assert coberturas_de_re({PED.CHAVE_DA_BASICA: 5}, PED.PedidoDeCalculo.de_dict(dados(16), ramo=16)) == {
        PED.CHAVE_DA_BASICA: 34500000.0}


def test_recalcular_re_nunca_manda_o_codigo_do_carro(mundo):
    m = mundo
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(dados(16), ramo=16),
                                    opcoes=("padrao",), origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    calc.update(negocio_ref="neg-ficticio", versao=1, status="fechado")
    for ruim in ({"tipo": "carro_reserva", "valor": "7 dias"}, {"tipo": "franquia", "valor": 2},
                 {"tipo": "assistencia", "valor": "platina"}):
        with pytest.raises(ValueError):
            rodar(m.porta.recalcular(company_id=m.a, calculo_id=calc["id"], ajuste=ruim))
    # 🔴 "básica" no CARRO é 4; no RE é 1 (📊 formulario_*: Não 0 · Básica 1 · Intermediária 2 · Completa 3)
    for rotulo, codigo in (("basica", 1), ("Intermediária", 2)):
        ok = rodar(m.porta.recalcular(company_id=m.a, calculo_id=calc["id"],
                                      ajuste={"tipo": "assistencia", "valor": rotulo}))
        novo = next(c for c in m.banco.linhas("multicalculo_calculos") if c["id"] == ok["id"])
        assert novo["ajuste"]["valor"] == codigo and novo["coberturas"]["assist24hs"] == codigo
        assert novo["coberturas"][PED.CHAVE_DA_BASICA] == calc["coberturas"][PED.CHAVE_DA_BASICA]


def test_o_auto_continua_igual_na_porta():
    """G3 do lado do app: o pedido do AUTO não passa pelo caminho de RE (o catálogo, o dict e as opções de sempre)."""
    from portal_worker.multicalculo.contrato import CAMPOS_DO_PEDIDO_AUTO

    p = PED.PedidoDeCalculo.de_dict({"segurado": {"cpf_cnpj": CPF}})
    assert not p.e_re and set(p.para_dict()) == {"ramo", *CAMPOS_DO_PEDIDO_AUTO, "questionario", "seguradoras",
                                                 "assumidos"}
    from app.services.multicalculo.porta import OPCOES, OPCOES_POR_RAMO

    assert OPCOES_POR_RAMO[31] is OPCOES and "minima" in OPCOES
    with pytest.raises(PED.RamoIndisponivel):
        PED.PedidoDeCalculo.de_dict({}, ramo=5)


def test_o_repr_do_pedido_de_re_nao_mostra_valores():
    p = PED.PedidoDeCalculo.de_dict(dados(18), ramo=18)
    texto = repr(p)
    assert CNPJ not in texto and "Ficticia" not in texto and "800000" not in texto and "ramo=18" in texto
    assert p.documento == CNPJ
