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


def lente_tentativas_sem_preco(dados, corretoras):
    """SPEC-133-A F0: pares DISTINTOS (cálculo das OPÇÕES × seguradora) com recusa/erro/sem resposta (a fixture só tem
    `seguradora_recusou`), contados à mão."""
    op = {e["calculo_id"]: e["opcao"] for e in dados["estados"]}
    return len({(e["calculo_id"], e["seguradora_codigo"]) for e in dados["eventos"]
                if e["corretora_company_id"] in corretoras and op.get(e["calculo_id"]) in OPCOES_DO_PEDIDO
                and e["tipo"] == "seguradora_recusou"})


def lente_seguradoras_consultadas(dados, corretoras):
    """Todas as que RECEBERAM o pedido nas opções: com oferta ou com recusa. D-130A1-15 ("tudo gera ponto"): a linha de
    assinatura conta como o Agger a lista (código próprio)."""
    op = {e["calculo_id"]: e["opcao"] for e in dados["estados"]}
    com_oferta = {o["seguradora_codigo"] for o in dados["ofertas"] if o["corretora_company_id"] in corretoras
                  and op.get(o["calculo_id"]) in OPCOES_DO_PEDIDO}
    recusas = {e["seguradora_codigo"] for e in dados["eventos"] if e["corretora_company_id"] in corretoras
               and op.get(e["calculo_id"]) in OPCOES_DO_PEDIDO and e["tipo"] == "seguradora_recusou"}
    return len(com_oferta | recusas)


def lente_extremos(dados, corretoras):
    """SPEC-133-A F0: o MENOR e o MAIOR preço de todos — as ofertas das OPÇÕES, de todas as corretoras, que cobrem o
    carro (compreensiva, casco 100 %, sem assinatura); o maior é o maior dos preços de cada seguradora × corretora ×
    opção (a menor oferta de cada uma)."""
    op = {e["calculo_id"]: e["opcao"] for e in dados["estados"]}
    menor = {}
    for o in dados["ofertas"]:
        c = o["coberturas"]
        if (o["corretora_company_id"] in corretoras and op.get(o["calculo_id"]) in OPCOES_DO_PEDIDO
                and str(c.get("tipoPadronizado") or c.get("tipo") or "") == "Compreensiva" and c.get("casco") == 100
                and "assinatura" not in str(o["seguradora"]).lower() and float(o["premio_total"]) > 0):
            k = (o["corretora_company_id"], o["seguradora_codigo"], op[o["calculo_id"]])
            menor[k] = min(menor.get(k, float("inf")), float(o["premio_total"]))
    return min(menor.values()), max(menor.values())


#: "N corretoras" em qualquer forma — o que a mensagem e a página do canal NUNCA dizem (Founder 07/10)
RE_NUMERO_DE_CORRETORAS = re.compile(r"\b\d+\s+(?:corretoras|corretora)\b", re.I)


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

    # --- 🔬 G2 (§9.3 — a lição MIGRA, SPEC-133-A F0): "Fiz N Cotações" = a BASE da config + o real, e o real é contado
    # à parte — preços que voltaram nas opções + tentativas sem preço. Tudo recontado por fora.
    n = lente_cotacoes(m.dados, m.corretoras)
    assert n == 82                     # 📊 o canário d0bb15ba (05/10): 38 padrão + 44 econômica; o ajuste (22) fora
    falhas = lente_tentativas_sem_preco(m.dados, m.corretoras)
    assert falhas == 6                 # as 6 recusas da fixture, todas em cálculos `padrao`
    base = cfg["canal"]["volume"]["base"]
    assert base == CFG.PADRAO_DO_PRODUTO["canal"]["volume"]["base"]           # sem linha do canal: o padrão
    assert modelo["resumo"]["cotacoes_realizadas"] == n
    assert modelo["resumo"]["volume_do_canal"] == {"base": base, "precos": n, "sem_preco": falhas,
                                                   "total": base + n + falhas}
    segs = lente_seguradoras_consultadas(m.dados, m.corretoras)
    assert modelo["resumo"]["seguradoras_consultadas"] == segs
    assert baloes[0].splitlines()[1] == \
        f"Fiz {base + n + falhas} Cotações entre Corretoras de Nível 5 e {segs} Seguradoras."
    # 🔴 CONTROLE (§9.3 corolário): com o recálculo de volta na conta, o número é OUTRO — e não aparece no texto
    errado = lente_cotacoes(m.dados, m.corretoras, com_ajuste=True)
    assert errado == 104 and errado != n
    assert f"Fiz {base + errado + falhas} " not in texto and f"Fiz {base + errado} " not in texto
    assert f"Fiz {base + n} " not in texto                                   # sem as falhas é outro número
    # 🔴 Founder 07/10: NUNCA o número de corretoras, em balão nenhum (o pedido tem 2)
    assert modelo["resumo"]["corretoras_comparadas"] == 2
    assert RE_NUMERO_DE_CORRETORAS.findall(texto) == []
    assert baloes[0].splitlines()[0] == \
        f"Prontinho, Mariana! Descobrimos Quem Cobra Menos no Seguro do seu {modelo['bem']['apelido']}"

    # --- o VENCEDOR: a anfitriã (a corretora que cobrou menos) com a seguradora da 1ª opção
    rec = modelo["opcoes"][0]
    assert "*Quem cobra menos?* " in baloes[0]
    assert f"Corretora {M.MARCA_ALFA} com {rec['seguradora']}" in baloes[0] or \
        f"{M.MARCA_ALFA} com {rec['seguradora']}" in baloes[0]
    assert "Quem Cobra Menos" in baloes[0]                            # o nome do canal (config, não constante)

    # --- 🔬 a economia (SPEC-133-A F0): sem preço atual, o MAIOR − o MENOR de todos; sem parêntese
    para, de = lente_extremos(m.dados, m.corretoras)
    eco = modelo["resumo"]["economia"]
    assert round(eco["de"], 2) == round(de, 2) and round(eco["para"], 2) == round(para, 2)
    assert eco["contra"] == "maior"
    assert f"Você deve economizar até *{_br_inteiro(de - para)}* por ano" in baloes[0]
    assert "_(" not in texto and "mais cara" not in texto and "economiza até" not in texto
    # o preço cheio NÃO está no balão 1 (só nos cartões)
    assert MSG._brl(rec["premio_anual"]) not in baloes[0] and MSG._brl(rec["premio_anual"]) in baloes[1]

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
              "tempo_do_calculo_s", "volume_do_canal", "seguradoras_consultadas", "tentativas_sem_preco"):
        sem["resumo"].pop(k, None)
    t = _texto(sem, cfg)
    for some in ("Cotações", "Fiz ", "segundos", "minutos", "economizar", "None", " 0 "):
        assert some not in t, some
    assert "*Quem cobra menos?*" in t and LINK in t and t.startswith("Prontinho, Mariana!")   # o resto fica de pé


def test_g4_sem_seguradoras_sem_selo_a_frase_encolhe_sem_buraco(canal):
    modelo, cfg = canal
    sem = copy.deepcopy(modelo)
    sem["resumo"].pop("seguradoras_consultadas")
    sem["anfitria"].pop("selo")
    total = sem["resumo"]["volume_do_canal"]["total"]
    assert _texto(sem, cfg).splitlines()[1] == f"Fiz {total} Cotações."
    sem["cliente"], sem["bem"] = None, None
    assert _texto(sem, cfg).splitlines()[0] == "Prontinho! Descobrimos Quem Cobra Menos no seu Seguro Auto"


def test_g4_o_tempo_aparece_quando_foi_medido_pelo_caminho_real(monkeypatch):
    """O tempo = do pedido criado à última oferta recebida (💭 aqui as ofertas chegam em 47 s, escritas no dublê)."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    criado = datetime.fromisoformat(m.banco.linhas("multicalculo_pedidos")[0]["criado_em"].replace("Z", "+00:00"))
    for i, o in enumerate(m.banco.linhas("multicalculo_ofertas")):
        o["recebida_em"] = (criado + timedelta(seconds=min(47, 5 + i))).isoformat()
    modelo, cfg = _montar(m)
    assert modelo["resumo"]["tempo_do_calculo_s"] == 47
    assert " Seguradoras em 47 segundos." in _texto(modelo, cfg)
    # D-130A1-14 (§9.3 — a lição migra; SPEC-133-A F0: teto padrão 180 s): 200 s passa do teto e o tempo SOME
    modelo["resumo"]["tempo_do_calculo_s"] = 200
    assert _tempo_no_texto(_texto(modelo, cfg)) == [] and " Seguradoras." in _texto(modelo, cfg)
    largo = copy.deepcopy(cfg)
    largo["canal"]["tempo_exibido_ate_s"] = 600
    assert _tempo_no_texto(_texto(modelo, largo)) == ["3,4 minutos"]        # 200/60 = 3,33… → para CIMA


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


def _tempo_no_texto(texto):
    """SPEC-133-A F0: o tempo agora fecha a frase "Fiz … Seguradoras em <tempo>." (não há mais linha "Tempo:")."""
    return re.findall(r" em (\d+(?:,\d)? (?:segundos?|minutos?))\.", texto)


_linhas_de_tempo = _tempo_no_texto


def test_d14_o_padrao_do_teto_vem_da_config():
    assert CFG.PADRAO_DO_PRODUTO["canal"]["tempo_exibido_ate_s"] > 0


def test_d14_47_segundos_aparece(monkeypatch):
    texto, cfg = _com_tempo(monkeypatch, 47)
    assert "tempo_exibido_ate_s" in cfg["canal"]                         # o padrão chega mesmo sem a linha
    assert _linhas_de_tempo(texto) == ["47 segundos"]


def test_d14_495_segundos_nenhuma_linha_de_tempo(monkeypatch):
    """O canário: 8 min 15 s — a linha some, e nenhum tempo menor que o medido toma o lugar dela."""
    texto, _ = _com_tempo(monkeypatch, 495)
    assert _linhas_de_tempo(texto) == [] and "8 min" not in texto and "segundos" not in texto
    assert "minutos" not in texto and "8,2" not in texto and "8,3" not in texto
    assert "*Quem cobra menos?*" in texto and LINK in texto              # o resto da mensagem continua de pé


def test_d14_teto_600_na_config_do_solicitante_mostra_8_min_15_s(monkeypatch):
    texto, cfg = _com_tempo(monkeypatch, 495, teto_do_canal=600)
    assert cfg["canal"]["tempo_exibido_ate_s"] == 600
    assert _linhas_de_tempo(texto) == ["8,3 minutos"]                   # 8,25 → para CIMA, nunca 8,2


def test_d14_o_teto_da_anfitria_nao_vale_para_o_canal(monkeypatch):
    """A config que chega é a do SOLICITANTE: a anfitriã com teto 600 não destrava o tempo do pedido do canal."""
    texto, cfg = _com_tempo(monkeypatch, 495, teto_da_anfitria=600)
    assert cfg["canal"]["tempo_exibido_ate_s"] == CFG.PADRAO_DO_PRODUTO["canal"]["tempo_exibido_ate_s"]
    assert _linhas_de_tempo(texto) == []


def test_d14_teto_igual_ao_tempo_aparece(monkeypatch):
    texto, _ = _com_tempo(monkeypatch, 495, teto_do_canal=495)
    assert _linhas_de_tempo(texto) == ["8,3 minutos"]
    texto, _ = _com_tempo(monkeypatch, 496, teto_do_canal=495)          # controle: um segundo acima, some
    assert _linhas_de_tempo(texto) == []


def test_d14_sem_a_chave_na_config_vale_o_padrao(canal):
    modelo, cfg = canal
    sem = copy.deepcopy(cfg)
    sem["canal"].pop("tempo_exibido_ate_s")
    padrao = CFG.PADRAO_DO_PRODUTO["canal"]["tempo_exibido_ate_s"]
    m = copy.deepcopy(modelo)
    m["resumo"]["tempo_do_calculo_s"] = padrao
    assert _tempo_no_texto(_texto(m, sem)) != []
    m["resumo"]["tempo_do_calculo_s"] = padrao + 1
    assert _tempo_no_texto(_texto(m, sem)) == []


def test_g4_o_dubl_e_sem_relogio_nao_inventa_tempo(canal):
    """No dublê todas as linhas nascem no MESMO instante: 0 s não é medida — o campo não existe e a linha some."""
    modelo, cfg = canal
    assert "tempo_do_calculo_s" not in modelo["resumo"] and _tempo_no_texto(_texto(modelo, cfg)) == []


# =====================================================================================================================
# G2 — a contagem vem do resumo; o texto não refaz conta nenhuma
# =====================================================================================================================
def test_g2_o_texto_le_o_total_do_modelo_e_nao_refaz_a_conta(canal):
    """O texto lê `volume_do_canal.total` (montado na proposta com a base da config): a base nunca entra duas vezes,
    e nenhuma fórmula de seguradoras × cálculos × corretoras aparece."""
    modelo, cfg = canal
    m2 = copy.deepcopy(modelo)
    m2["resumo"].update({"cotacoes_realizadas": 7, "seguradoras_consultadas": 5, "corretoras_comparadas": 2,
                         "volume_do_canal": {"base": 0, "precos": 7, "sem_preco": 0, "total": 7}})
    t = _texto(m2, cfg)
    assert "Fiz 7 Cotações entre Corretoras de Nível 5 e 5 Seguradoras." in t
    assert "107" not in t and "130" not in t and "Fiz 30 " not in t      # base de novo · 5 × 3 × 2 + 100 · 5 × 3 × 2


@pytest.mark.parametrize("corretoras", [2, 3])
def test_nenhum_numero_de_corretoras_na_mensagem_nem_na_pagina_do_canal(canal, corretoras):
    """Founder 07/10: NUNCA o número de corretoras — nem nos balões, nem na página do canal (com 2 e com 3)."""
    from app.services.artifacts import proposta_html as PH

    modelo, cfg = canal
    m2 = copy.deepcopy(modelo)
    venc = next(e for e in m2["entre_corretoras"] if e["vencedora"])
    m2["entre_corretoras"] = [venc] + [{"corretora": None, "melhor_completa": venc["melhor_completa"] + 100 * i,
                                        "vencedora": False} for i in range(1, corretoras)]
    m2["resumo"]["corretoras_comparadas"] = corretoras
    assert RE_NUMERO_DE_CORRETORAS.findall("\n".join(MSG.mensagem_para(m2, LINK, config=cfg))) == []
    doc = PH.render_proposta(m2)
    visivel = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", doc, flags=re.S))
    assert RE_NUMERO_DE_CORRETORAS.findall(visivel.replace("\u00a0", " ")) == []
    assert "corretoras parceiras pelo melhor preço" in visivel                # o duelo continua, sem o número
    prev = PH.previa_do_modelo(m2)
    assert prev["corretoras"] is None and RE_NUMERO_DE_CORRETORAS.findall(prev["descricao"]) == []


def test_controle_o_varredor_de_corretoras_acha_o_numero():
    assert RE_NUMERO_DE_CORRETORAS.findall("Vencedor entre 2 corretoras e 13 seguradoras") == ["2 corretoras"]
    assert RE_NUMERO_DE_CORRETORAS.findall("comparou 3 Corretoras pelo melhor preço") == ["3 Corretoras"]


# =====================================================================================================================
# juros com nome · a mais em conta diz o que deixa de cobrir · contra o preço atual só com apólice
# =====================================================================================================================
def _linha_do_vencedor(b1):
    return next(l for l in b1.splitlines() if l.startswith("*Quem cobra menos?*"))


def test_a_parcela_em_destaque_e_o_menor_valor_com_o_numero_em_negrito(canal):
    """SPEC-133-A F0 (técnica de preço): `12x de *R$ 345,82*` — o menor valor de parcela da oferta, com ou sem juros;
    o "12x de" sem negrito; o preço cheio fora do balão 1."""
    modelo, cfg = canal
    m2 = copy.deepcopy(modelo)
    rec = m2["opcoes"][0]
    rec["parcelas"] = {"vezes": 12, "valor": 345.82}
    rec["parcelas_sem_juros"] = {"vezes": 6, "valor": 621.76}
    b1 = MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]
    assert _linha_do_vencedor(b1).endswith(f"com {rec['seguradora']} · 12x de *R$ 345,82*")
    assert "*12x" not in b1 and "juros" not in b1 and "621,76" not in b1
    assert MSG._brl(rec["premio_anual"]) not in b1 and "Total" not in b1
    rec["parcelas_sem_juros"] = {"vezes": 12, "valor": 345.82}                 # o mesmo sem juros: igual
    assert _linha_do_vencedor(MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]).endswith("12x de *R$ 345,82*")
    rec["parcelas"] = {"vezes": 10, "valor": 399.90}                           # com 10x, diz 10x (nunca constante)
    rec["parcelas_sem_juros"] = {"vezes": 4, "valor": 999.75}
    b1 = MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]
    assert _linha_do_vencedor(b1).endswith("10x de *R$ 399,90*") and "12x" not in b1
    rec.pop("parcelas")
    rec.pop("parcelas_sem_juros")                                              # sem parcelamento: sem preço na linha
    assert _linha_do_vencedor(MSG.mensagem_do_canal(m2, LINK, config=cfg)[0]).endswith(f"com {rec['seguradora']}")


def test_a_mais_em_conta_diz_o_que_deixa_de_cobrir(canal):
    modelo, cfg = canal
    barata = next(o for o in modelo["opcoes"][1:] if o["premio_anual"] < modelo["opcoes"][0]["premio_anual"])
    assert barata.get("por_que_mais_barata")
    t = _texto(modelo, cfg)
    assert f"*{barata['rotulo']}*" in t and "_Cobre menos:" in t


def _eco_e_texto(m, situacao="novo_sem_apolice", apolice=None, declarado=None):
    ctx: dict = {}
    modelo = asyncio.run(montar_proposta(m.dono, m.pedido_id, situacao, apolice, primeiro_nome="Mariana", db=m.db,
                                         agora=AGORA, premio_atual_declarado=declarado, _contexto=ctx))
    return modelo["resumo"].get("economia"), "\n".join(MSG.mensagem_para(modelo, LINK, config=ctx["cfg_sol"]))


def test_a_economia_contra_a_apolice_contra_o_declarado_e_sem_nenhum(monkeypatch):
    """SPEC-133-A F0: até = o preço ATUAL (apólice; senão o declarado na conversa) − o MENOR de todos; sem nenhum
    preço atual, o MAIOR − o MENOR. Sem parêntese, sem segunda linha."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    menor, maior = lente_extremos(m.dados, m.corretoras)
    apolice = {"seguradora": "Seguradora Ficticia Fora", "premio_anual": 6000.0}
    eco, t = _eco_e_texto(m, "novo_com_apolice", apolice)
    assert eco == {"ate": round(6000.0 - menor, 2), "de": 6000.0, "para": round(menor, 2), "contra": "atual"}
    assert f"Você deve economizar até *{_br_inteiro(6000.0 - menor)}* por ano" in t
    assert "seguro atual" not in t and "_(" not in t
    eco, t = _eco_e_texto(m, declarado=8900.0)                                 # o que a pessoa disse
    assert eco["contra"] == "atual" and eco["ate"] == round(8900.0 - menor, 2)
    assert f"Você deve economizar até *{_br_inteiro(8900.0 - menor)}* por ano" in t
    eco, _t = _eco_e_texto(m, "novo_com_apolice", apolice, declarado=8900.0)    # a apólice vence o declarado
    assert eco["de"] == 6000.0
    eco, t = _eco_e_texto(m)                                                   # nenhum: o maior − o menor
    assert eco["contra"] == "maior" and eco["ate"] == round(maior - menor, 2)
    assert f"Você deve economizar até *{_br_inteiro(maior - menor)}* por ano" in t
    eco, t = _eco_e_texto(m, declarado=round(menor + 0.5, 2))                  # menos de R$ 1: a linha some
    assert "economizar" not in t
    eco, t = _eco_e_texto(m, declarado=round(menor - 50, 2))                   # paga MENOS hoje: nada de economia
    assert eco is None and "economizar" not in t
    with pytest.raises(ValueError):
        _eco_e_texto(m, declarado=-1)


def test_a_minima_entra_no_menor_de_todos_e_o_produto_diferente_nao(monkeypatch):
    """A mínima (4º cálculo) é uma opção do pedido: o preço dela entra no menor de todos. O produto DIFERENTE (aqui, a
    oferta mais barata do pedido virada em terceiros-só) nunca."""
    import uuid

    m = M.montar_mundo(monkeypatch, solicitante="canal")
    menor, _maior = lente_extremos(m.dados, m.corretoras)
    base = next(o for o in m.banco.linhas("multicalculo_ofertas") if float(o["premio_total"]) == menor)
    calc = next(c for c in m.banco.linhas("multicalculo_calculos") if c["id"] == base["calculo_id"])
    novo = str(uuid.uuid4())
    m.banco.semear("multicalculo_calculos", dict(calc, id=novo, opcao="minima", versao=4))
    m.banco.semear("multicalculo_ofertas", dict(copy.deepcopy(base), id=str(uuid.uuid4()), calculo_id=novo,
                                                premio_total=round(menor - 300, 2)))
    diferente = copy.deepcopy(base)
    diferente["coberturas"]["casco"] = 0                                    # não cobre o carro: produto diferente
    m.banco.semear("multicalculo_ofertas", dict(diferente, id=str(uuid.uuid4()), calculo_id=novo, premio_total=99.0,
                                                pacote="Pacote Ficticio Terceiros"))
    eco, t = _eco_e_texto(m)
    assert eco["para"] == round(menor - 300, 2)                               # a mínima, nunca os 99 do diferente


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
    assert codigo == 0 and "ENSAIO" in texto and "Fiz " in texto and "[balão 3]" in texto
    assert m.banco.linhas("artifacts") == []


def test_o_comando_aceita_o_preco_atual_declarado(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    menor, _maior = lente_extremos(m.dados, m.corretoras)
    for valor in ("8900,00", "8.900,00", "8900.00"):
        saida = io.StringIO()
        assert asyncio.run(executar(["--pedido", m.pedido_id, "--atual", valor], db=m.db, saida=saida)) == 0
        assert f"Você deve economizar até *{_br_inteiro(8900.0 - menor)}* por ano" in saida.getvalue()
    saida = io.StringIO()
    assert asyncio.run(executar(["--pedido", m.pedido_id, "--atual", "abc"], db=m.db, saida=saida)) == 2
    assert "--atual" in saida.getvalue() and m.banco.linhas("artifacts") == []


# =====================================================================================================================
# SPEC-133-A F0 — a BASE do volume vem SÓ da config (a ordem do Founder: teste controlado, desligável com base 0)
# =====================================================================================================================
def _volume_com_base(monkeypatch, base):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    if base is not None:
        m.banco.semear("multicalculo_config", {"company_id": m.canal, "config": {"canal": {"volume": {"base": base}}}})
    modelo, cfg = _montar(m)
    return m, modelo, "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))


@pytest.mark.parametrize("base", [0, 37])
def test_a_base_do_volume_vem_so_da_config_do_canal(monkeypatch, base):
    """🔴 GUARDA: com a base 0 na config do canal, "Fiz N" = SÓ o real (preços + tentativas sem preço, contados por
    fora). Uma base escrita no código fica VERMELHA aqui (mutação registrada na entrega)."""
    m, modelo, texto = _volume_com_base(monkeypatch, base)
    real = lente_cotacoes(m.dados, m.corretoras) + lente_tentativas_sem_preco(m.dados, m.corretoras)
    assert modelo["resumo"]["volume_do_canal"]["base"] == base
    assert f"Fiz {base + real} Cotações " in texto
    assert f"Fiz {CFG.PADRAO_DO_PRODUTO['canal']['volume']['base'] + real} " not in texto   # controle: dá para ver


def test_a_base_da_anfitria_nao_vale_para_o_canal(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    linha = next(l for l in m.banco.linhas("multicalculo_config") if l["company_id"] == m.alfa)
    linha["config"]["canal"] = {"volume": {"base": 5000}}
    modelo, _cfg = _montar(m)
    assert modelo["resumo"]["volume_do_canal"]["base"] == CFG.PADRAO_DO_PRODUTO["canal"]["volume"]["base"]


def test_a_carteira_nao_leva_volume_do_canal(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    modelo, cfg = _montar(m)
    assert "volume_do_canal" not in modelo["resumo"]
    assert "Fiz " not in "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))


def test_o_comando_ensaia_a_mensagem_da_carteira(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    codigo, texto = _ensaio(m)
    assert codigo == 0 and "Cotações realizadas" not in texto and "Quem Cobra Menos" not in texto
    assert "[balão 2]" in texto and "[balão 3]" not in texto
