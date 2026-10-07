# -*- coding: utf-8 -*-
"""SPEC-130-A.1 F2 — A MENSAGEM DO CANAL (G2 · G3 · G4 · G9 · D-130A1-01/02/03/04/06 · D-130A-08 revogada).

O FIO (a 1ª entrega desta fatia, nasceu VERMELHO):
    o pedido REAL do canário (104 ofertas, 2 corretoras) gravado no banco DUBLÊ como o motor o deixa
      → `proposta.montar_proposta` (porta.consultar → comparacao → o modelo, com o resumo REAL)
      → `mensagem.mensagem_para(modelo, link)` (origem canal → `mensagem_do_canal`; corretora → a da carteira)
      → afirmações sobre os BALÕES: o vencedor, "Cotações realizadas" = a contagem INDEPENDENTE das ofertas do dublê,
        sem comissão, sem a perdedora, sem "Quem Cobra Menos" quando a origem é corretora, linha sem dado some.
    bordas: só o banco (o PostgREST em memória). Porta, comparação e proposta são as REAIS (CLAUDE.md §9.4).

🔬 LENTE DO DADO: todo número que a mensagem publica (cotações, seguradoras, economia, anos de mercado) é recontado
AQUI, direto da fixture, sem `comparacao` nem `proposta`.

⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar:
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a1_a_mensagem_do_canal.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import io
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import mensagem as MSG  # noqa: E402
from app.services.multicalculo.comando_proposta import executar  # noqa: E402
from app.services.multicalculo.proposta import montar_proposta  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402

LINK = "https://app.exemplo.test/r/tOkEn_ficticio_0123456789abcdefghijklmnopq"
AGORA = datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc)
#: onde gravar os balões do canário para leitura humana — só quando a variável existe (nunca um caminho de máquina)
SCRATCH = Path(os.environ["MC_BALOES_DIR"]) if os.environ.get("MC_BALOES_DIR") else None


def _montar(m, situacao="novo_sem_apolice", apolice=None):
    ctx: dict = {}
    modelo = asyncio.run(montar_proposta(m.dono, m.pedido_id, situacao, apolice, primeiro_nome="Mariana", db=m.db,
                                         agora=AGORA, _contexto=ctx))
    return modelo, ctx["cfg_sol"]


def _br_inteiro(v: float) -> str:
    return "R$ " + f"{int(abs(v) + 0.5):,}".replace(",", ".")


# =====================================================================================================================
# a LENTE independente — direto da fixture, sem `comparacao` nem `proposta`
# =====================================================================================================================
#: as OPÇÕES do pedido (escritas aqui à mão, não importadas da porta: a lente não lê o código que confere)
OPCOES_DO_PEDIDO = ("padrao", "economica", "completa_mais", "minima")


def lente_cotacoes(dados, corretoras, *, com_ajuste=False):
    """D-130A1-02 (conserto 130-A.1): os preços que VOLTARAM nos cálculos das OPÇÕES do pedido, de todas as
    corretoras — o recálculo (`opcao='ajuste'`) NÃO é comparação. `com_ajuste=True` = a conta ERRADA (o defeito)."""
    op = {e["calculo_id"]: e["opcao"] for e in dados["estados"]}
    return sum(1 for o in dados["ofertas"] if o["corretora_company_id"] in corretoras and float(o["premio_total"]) > 0
               and (com_ajuste or op.get(o["calculo_id"]) in OPCOES_DO_PEDIDO))


def lente_seguradoras_das_opcoes(dados, corretoras):
    """Seguradoras distintas (por código) com preço NAS OPÇÕES; o produto de ASSINATURA é linha de uma seguradora."""
    op = {e["calculo_id"]: e["opcao"] for e in dados["estados"]}
    return len({o["seguradora_codigo"] for o in dados["ofertas"] if o["corretora_company_id"] in corretoras
                and float(o["premio_total"]) > 0 and op.get(o["calculo_id"]) in OPCOES_DO_PEDIDO
                and "assinatura" not in str(o["seguradora"]).lower()})


def lente_mais_cara_completa(dados, corretoras):
    """A MAIS CARA entre as completas (a menor de cada seguradora × corretora, na opção padrão)."""
    op = {e["calculo_id"]: e["opcao"] for e in dados["estados"]}
    menor = {}
    for o in dados["ofertas"]:
        c = o["coberturas"]
        if (o["corretora_company_id"] in corretoras and op.get(o["calculo_id"]) == "padrao"
                and str(c.get("tipoPadronizado") or c.get("tipo") or "") == "Compreensiva" and c.get("casco") == 100
                and "assinatura" not in str(o["seguradora"]).lower()):
            k = (o["corretora_company_id"], o["seguradora_codigo"])
            menor[k] = min(menor.get(k, float("inf")), float(o["premio_total"]))
    return max(menor.values())


# =====================================================================================================================
# O FIO — o pedido real do CANAL → os balões do canal
# =====================================================================================================================
def test_o_fio_do_canal_pedido_real_ate_os_baloes(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    modelo, cfg = _montar(m)
    assert modelo["origem"] == "canal"
    baloes = MSG.mensagem_para(modelo, LINK, config=cfg)
    texto = "\n".join(baloes)

    # --- a forma: ≤ 3 balões, cada um no teto, o link no ÚLTIMO com a validade e UMA pergunta no fim
    assert 1 <= len(baloes) <= 3
    medida = MSG.conferir_do_canal(baloes)
    assert medida["proibidas"] == [] and medida["emojis"] <= 3   # a régua da SPEC-130-A.1 §3
    assert max(medida["caracteres_por_balao"]) <= MSG.TETO_POR_BALAO_DO_CANAL
    assert LINK in baloes[-1] and all(LINK not in b for b in baloes[:-1])
    assert "Os preços valem até 11/10/2026." in baloes[-1]
    ultima = baloes[-1].strip().splitlines()[-1]
    assert ultima.endswith("?") and M.MARCA_ALFA in ultima

    # --- 🔬 G2: o volume é o número REAL de preços que voltaram — contado por fora
    n = lente_cotacoes(m.dados, m.corretoras)
    assert n == 82                     # 📊 o canário d0bb15ba (05/10): 38 padrão + 44 econômica; o ajuste (22) fora
    assert modelo["resumo"]["cotacoes_realizadas"] == n
    assert f"Cotações realizadas: *{n}*" in texto and f"*{n} comparações*" in texto
    # 🔴 CONTROLE (§9.3 corolário): com o recálculo de volta na conta, o número é OUTRO — e não aparece no texto
    errado = lente_cotacoes(m.dados, m.corretoras, com_ajuste=True)
    assert errado == 104 and errado != n
    assert f"Cotações realizadas: *{errado}*" not in texto and f"*{errado} comparações*" not in texto
    segs = lente_seguradoras_das_opcoes(m.dados, m.corretoras)
    assert modelo["resumo"]["seguradoras_com_preco"] == segs
    assert f"entre 2 corretoras e {segs} seguradoras" in texto
    # o guarda CONSEGUE ver a diferença: a fórmula do Founder daria outro número (§9.3 corolário)
    formula = segs * 3 * 2 + 100
    assert formula != n and str(formula) not in texto

    # --- o VENCEDOR: a anfitriã (a corretora que cobrou menos) com a seguradora da 1ª opção
    rec = modelo["opcoes"][0]
    assert "*Quem cobra menos?*" in baloes[0]
    assert f"Corretora {M.MARCA_ALFA} com {rec['seguradora']}" in baloes[0] or \
        f"{M.MARCA_ALFA} com {rec['seguradora']}" in baloes[0]
    assert "Quem Cobra Menos" in baloes[0]                            # o nome do canal (config, não constante)

    # --- 🔬 a economia: a mais cara com a mesma cobertura completa − a mais barata MOSTRADA
    de = lente_mais_cara_completa(m.dados, m.corretoras)
    para = min(o["premio_anual"] for o in modelo["opcoes"])
    eco = modelo["resumo"]["economia"]
    assert round(eco["de"], 2) == round(de, 2) and round(eco["para"], 2) == round(para, 2)
    assert f"Você economiza até *{_br_inteiro(de - para)}* por ano" in texto
    assert "vs_atual" not in eco                                     # sem apólice: nada contra o "preço atual"

    # --- quem é a corretora: lista, linha sem dado some
    assert "*Quem é a corretora que cobra menos?*" in texto
    assert "Corretora Nível 5" in texto and "só aceite corretoras Nível 5" in texto
    assert "Google: 4,9 (37 avaliações)" in texto
    assert "SUSEP: 202031234" in texto and "SUSEP: SUSEP" not in texto
    assert f"{AGORA.year - 2009} anos de mercado" in texto
    assert "Reclame Aqui" not in texto                               # sem fonte hoje: a linha não aparece

    # --- G3/D-MC-55: nada de comissão, nada da perdedora
    for proibido in (M.NOME_BETA, M.MARCA_BETA, "Vega", "17,37", "17.37", "comiss", "None", "%"):
        assert proibido not in texto, proibido
    # o "Melhor preço por seguradora": as N primeiras do ranking (config), e o resto no link
    quantas = int(cfg["canal"]["lista_por_seguradora"])
    for r in modelo["ranking"][:quantas]:
        assert f"{r['seguradora']} · {_br_inteiro(r['premio_anual'])}" in texto
    assert "_Lista completa no link abaixo._" in texto
    if len(modelo["ranking"]) > quantas:
        assert f"{modelo['ranking'][quantas]['seguradora']} · " not in texto

    if SCRATCH is not None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        (SCRATCH / "baloes_canario.txt").write_text(
            "\n\n".join(f"[balão {i}] ({len(b)} caracteres)\n{b}" for i, b in enumerate(baloes, 1)), encoding="utf-8")


def test_g3_a_mensagem_da_carteira_nao_fala_do_canal(monkeypatch):
    """O MESMO quadro pedido pela própria corretora → a mensagem da 130-A, sem uma palavra do canal."""
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    modelo, cfg = _montar(m)
    assert modelo["origem"] == "corretora" and "canal" not in modelo and "selo" not in modelo["anfitria"]
    baloes = MSG.mensagem_para(modelo, LINK, config=cfg)
    assert baloes == MSG.mensagem_whatsapp(modelo, LINK, config=cfg)
    texto = "\n".join(baloes)
    for proibido in ("Quem Cobra Menos", "Quem cobra menos", "Nível 5", "Cotações realizadas", "comparações"):
        assert proibido not in texto, proibido


def test_g3_o_modelo_do_canal_marcado_como_corretora_cai_na_carteira(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    modelo, cfg = _montar(m)
    como_corretora = copy.deepcopy(modelo)
    como_corretora["origem"] = "corretora"
    texto = "\n".join(MSG.mensagem_para(como_corretora, LINK, config=cfg))
    assert "Quem Cobra Menos" not in texto and "Nível 5" not in texto and "Cotações realizadas" not in texto


# =====================================================================================================================
# G4 — linha sem dado SOME (nunca "None", nunca um zero inventado)
# =====================================================================================================================
@pytest.fixture
def canal(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    return _montar(m)


def _texto(modelo, cfg):
    return "\n".join(MSG.mensagem_do_canal(modelo, LINK, config=cfg))


def test_g4_sem_google_sem_susep_sem_desde_as_linhas_somem(canal):
    modelo, cfg = canal
    base = _texto(modelo, cfg)
    assert "Google:" in base and "SUSEP:" in base and "anos de mercado" in base
    for chave, sumida in (("google", "Google:"), ("susep", "SUSEP"), ("desde", "anos de mercado")):
        sem = copy.deepcopy(modelo)
        sem["anfitria"].pop(chave)
        t = _texto(sem, cfg)
        assert sumida not in t and "None" not in t, chave


def test_g4_sem_selo_nao_ha_nivel_5_nem_o_atencao(canal):
    modelo, cfg = canal
    sem = copy.deepcopy(modelo)
    sem["anfitria"].pop("selo")
    t = _texto(sem, cfg)
    assert "Nível 5" not in t and "Atenção" not in t


def test_g4_sem_contagem_sem_tempo_sem_economia_as_linhas_somem(canal):
    modelo, cfg = canal
    sem = copy.deepcopy(modelo)
    for k in ("cotacoes_realizadas", "seguradoras_com_preco", "corretoras_comparadas", "economia",
              "tempo_do_calculo_s"):
        sem["resumo"].pop(k, None)
    t = _texto(sem, cfg)
    for some in ("Cotações realizadas", "comparações", "Tempo:", "economiza", "None", " 0 "):
        assert some not in t, some
    assert "*Quem cobra menos?*" in t and LINK in t                   # o resto da mensagem continua de pé


def test_g4_o_tempo_aparece_quando_foi_medido_pelo_caminho_real(monkeypatch):
    """O tempo = do pedido criado à última oferta recebida (💭 aqui as ofertas chegam em 47 s, escritas no dublê)."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    criado = datetime.fromisoformat(m.banco.linhas("multicalculo_pedidos")[0]["criado_em"].replace("Z", "+00:00"))
    for i, o in enumerate(m.banco.linhas("multicalculo_ofertas")):
        o["recebida_em"] = (criado + timedelta(seconds=min(47, 5 + i))).isoformat()
    modelo, cfg = _montar(m)
    assert modelo["resumo"]["tempo_do_calculo_s"] == 47
    assert "Tempo: *47 segundos*" in _texto(modelo, cfg)
    # D-130A1-14 (§9.3 — a lição migra): 135 s passa do teto padrão e a linha SOME; com o teto da config, aparece
    modelo["resumo"]["tempo_do_calculo_s"] = 135
    assert "Tempo:" not in _texto(modelo, cfg)
    largo = copy.deepcopy(cfg)
    largo["canal"]["tempo_exibido_ate_s"] = 600
    assert "Tempo: *2 min 15 s*" in _texto(modelo, largo)


# =====================================================================================================================
# D-130A1-14 — o tempo é verdadeiro ou não aparece, e só até o teto da config do SOLICITANTE
# 📊 canário real 07/10: último preço aos 495 s ("8 min 15 s") contra a promessa de segundos
# =====================================================================================================================
def _com_tempo(monkeypatch, segundos, *, teto_do_canal=None, teto_da_anfitria=None):
    """O caminho real (`montar_proposta` → `CFG.carregar`): o tempo medido nas ofertas do dublê e os tetos escritos
    nas linhas de `multicalculo_config` do SOLICITANTE (o canal) e da ANFITRIÃ (corretora_a)."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    if teto_do_canal is not None:
        m.banco.semear("multicalculo_config", {"company_id": m.canal,
                                               "config": {"canal": {"tempo_exibido_ate_s": teto_do_canal}}})
    if teto_da_anfitria is not None:
        linha = next(l for l in m.banco.linhas("multicalculo_config") if l["company_id"] == m.alfa)
        linha["config"]["canal"] = {"tempo_exibido_ate_s": teto_da_anfitria}
    criado = datetime.fromisoformat(m.banco.linhas("multicalculo_pedidos")[0]["criado_em"].replace("Z", "+00:00"))
    for o in m.banco.linhas("multicalculo_ofertas"):
        o["recebida_em"] = (criado + timedelta(seconds=segundos)).isoformat()
    modelo, cfg = _montar(m)
    assert modelo["resumo"]["tempo_do_calculo_s"] == segundos
    return "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg)), cfg


def _linhas_de_tempo(texto):
    return [l for l in texto.splitlines() if l.startswith("Tempo")]


def test_d14_o_padrao_do_teto_vem_da_config():
    assert CFG.PADRAO_DO_PRODUTO["canal"]["tempo_exibido_ate_s"] > 0


def test_d14_47_segundos_aparece(monkeypatch):
    texto, cfg = _com_tempo(monkeypatch, 47)
    assert "tempo_exibido_ate_s" in cfg["canal"]                         # o padrão chega mesmo sem a linha
    assert _linhas_de_tempo(texto) == ["Tempo: *47 segundos*"]


def test_d14_495_segundos_nenhuma_linha_de_tempo(monkeypatch):
    """O canário: 8 min 15 s — a linha some, e nenhum tempo menor que o medido toma o lugar dela."""
    texto, _ = _com_tempo(monkeypatch, 495)
    assert _linhas_de_tempo(texto) == [] and "8 min" not in texto and "segundos" not in texto
    assert "*Quem cobra menos?*" in texto and LINK in texto              # o resto da mensagem continua de pé


def test_d14_teto_600_na_config_do_solicitante_mostra_8_min_15_s(monkeypatch):
    texto, cfg = _com_tempo(monkeypatch, 495, teto_do_canal=600)
    assert cfg["canal"]["tempo_exibido_ate_s"] == 600
    assert _linhas_de_tempo(texto) == ["Tempo: *8 min 15 s*"]


def test_d14_o_teto_da_anfitria_nao_vale_para_o_canal(monkeypatch):
    """A config que chega é a do SOLICITANTE: a anfitriã com teto 600 não destrava o tempo do pedido do canal."""
    texto, cfg = _com_tempo(monkeypatch, 495, teto_da_anfitria=600)
    assert cfg["canal"]["tempo_exibido_ate_s"] == CFG.PADRAO_DO_PRODUTO["canal"]["tempo_exibido_ate_s"]
    assert _linhas_de_tempo(texto) == []


def test_d14_teto_igual_ao_tempo_aparece(monkeypatch):
    texto, _ = _com_tempo(monkeypatch, 495, teto_do_canal=495)
    assert _linhas_de_tempo(texto) == ["Tempo: *8 min 15 s*"]
    texto, _ = _com_tempo(monkeypatch, 496, teto_do_canal=495)          # controle: um segundo acima, some
    assert _linhas_de_tempo(texto) == []


def test_d14_sem_a_chave_na_config_vale_o_padrao(canal):
    modelo, cfg = canal
    sem = copy.deepcopy(cfg)
    sem["canal"].pop("tempo_exibido_ate_s")
    padrao = CFG.PADRAO_DO_PRODUTO["canal"]["tempo_exibido_ate_s"]
    m = copy.deepcopy(modelo)
    m["resumo"]["tempo_do_calculo_s"] = padrao
    assert any(l.startswith("Tempo") for l in _texto(m, sem).splitlines())
    m["resumo"]["tempo_do_calculo_s"] = padrao + 1
    assert not any(l.startswith("Tempo") for l in _texto(m, sem).splitlines())


def test_g4_o_dubl_e_sem_relogio_nao_inventa_tempo(canal):
    """No dublê todas as linhas nascem no MESMO instante: 0 s não é medida — o campo não existe e a linha some."""
    modelo, cfg = canal
    assert "tempo_do_calculo_s" not in modelo["resumo"] and "Tempo:" not in _texto(modelo, cfg)


# =====================================================================================================================
# G2 — a contagem vem do resumo; o texto não refaz conta nenhuma
# =====================================================================================================================
def test_g2_o_texto_le_o_resumo_e_nao_uma_formula(canal):
    modelo, cfg = canal
    m2 = copy.deepcopy(modelo)
    m2["resumo"].update({"cotacoes_realizadas": 7, "seguradoras_com_preco": 5, "corretoras_comparadas": 2})
    t = _texto(m2, cfg)
    assert "Cotações realizadas: *7*" in t and "*7 comparações*" in t
    assert "130" not in t and "Cotações realizadas: *30*" not in t       # 5 × 3 × 2 + 100 · 5 × 3 × 2


def test_g2_uma_corretora_so_nao_diz_entre_corretoras(canal):
    modelo, cfg = canal
    m2 = copy.deepcopy(modelo)
    m2["resumo"].pop("corretoras_comparadas")
    t = _texto(m2, cfg)
    assert "corretoras e" not in t and f"de {m2['resumo']['seguradoras_com_preco']} seguradoras" in t


# =====================================================================================================================
# juros com nome · a mais em conta diz o que deixa de cobrir · contra o preço atual só com apólice
# =====================================================================================================================
def test_juros_com_nome_e_sem_juros_so_quando_verdade(canal):
    modelo, cfg = canal
    m2 = copy.deepcopy(modelo)
    rec = m2["opcoes"][0]
    rec["parcelas"] = {"vezes": 12, "valor": 345.82}
    rec["parcelas_sem_juros"] = {"vezes": 6, "valor": 621.76}
    b1 = MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]
    assert "*12x de R$ 345,82* com juros, total R$ 4.150" in b1
    assert f"ou *6x de R$ 621,76* sem juros ({MSG._brl(rec['premio_anual'])})" in b1
    rec["parcelas_sem_juros"] = {"vezes": 12, "valor": 345.82}
    b1 = MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]
    assert "*12x de R$ 345,82* sem juros" in b1 and "com juros" not in b1
    rec.pop("parcelas_sem_juros")
    b1 = MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]
    assert "sem juros" not in b1 and "com juros, total" in b1


def test_a_mais_em_conta_diz_o_que_deixa_de_cobrir(canal):
    modelo, cfg = canal
    barata = next(o for o in modelo["opcoes"][1:] if o["premio_anual"] < modelo["opcoes"][0]["premio_anual"])
    assert barata.get("por_que_mais_barata")
    t = _texto(modelo, cfg)
    assert f"*{barata['rotulo']}*" in t and "_Cobre menos:" in t


def test_contra_o_preco_atual_so_com_apolice(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    modelo, cfg = _montar(m, "novo_com_apolice", {"seguradora": "Seguradora Ficticia Fora", "premio_anual": 6000.0})
    va = modelo["resumo"]["economia"]["vs_atual"]
    rec = modelo["opcoes"][0]
    assert round(va["atual"], 2) == 6000.0 and round(va["valor"], 2) == round(6000.0 - rec["premio_anual"], 2)
    assert f"{_br_inteiro(6000.0 - rec['premio_anual'])} a menos que o seu seguro atual" in _texto(modelo, cfg)


# =====================================================================================================================
# G9 — nenhuma remuneração no modelo (D-130A-08 revogada: "nós não vendemos seguros")
# =====================================================================================================================
def _chaves(obj, caminho="modelo"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{caminho}.{k}"
            yield from _chaves(v, f"{caminho}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _chaves(v, f"{caminho}[{i}]")


@pytest.mark.parametrize("solicitante", ["canal", "beta"])
def test_g9_nenhuma_remuneracao_no_modelo(monkeypatch, solicitante):
    m = M.montar_mundo(monkeypatch, solicitante=solicitante)
    modelo, cfg = _montar(m)
    assert [c for c in _chaves(modelo) if "remunera" in c.lower()] == []
    assert "remuneracao_cnsp_382" not in CFG.PADRAO_DO_PRODUTO and "remuneracao_cnsp_382" not in cfg


def test_g9_controle_o_varredor_acha_a_chave_quando_ela_esta_la():
    assert [c for c in _chaves({"a": [{"mostrar_remuneracao": False}]}) if "remunera" in c] == \
        ["modelo.a[0].mostrar_remuneracao"]


# =====================================================================================================================
# o medidor do canal acha o que proíbe (senão ele não guarda nada)
# =====================================================================================================================
def test_o_conferir_do_canal_acha_quando_esta_la():
    m = MSG.conferir_do_canal(["O mais barato do mercado, 20% de desconto, corra! 🏆🏆🏆🏆", "x" * 900])
    assert {"mais barato do mercado", "%", "desconto", "corra"} <= set(m["proibidas"])
    assert m["emojis"] == 4 and max(m["caracteres_por_balao"]) == 900


# =====================================================================================================================
# o COMANDO — o ensaio imprime a mensagem certa pela origem (nada é gravado nem enviado)
# =====================================================================================================================
def _ensaio(m):
    saida = io.StringIO()
    codigo = asyncio.run(executar(["--pedido", m.pedido_id], db=m.db, saida=saida))
    return codigo, saida.getvalue()


def test_o_comando_ensaia_a_mensagem_do_canal(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    codigo, texto = _ensaio(m)
    assert codigo == 0 and "ENSAIO" in texto and "Cotações realizadas" in texto and "[balão 3]" in texto
    assert m.banco.linhas("artifacts") == []


def test_o_comando_ensaia_a_mensagem_da_carteira(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    codigo, texto = _ensaio(m)
    assert codigo == 0 and "Cotações realizadas" not in texto and "Quem Cobra Menos" not in texto
    assert "[balão 2]" in texto and "[balão 3]" not in texto
