# -*- coding: utf-8 -*-
"""SPEC-129-C — o CONSERTO, lado do portal (juiz 129-C B1/B2/P1 · red B1/P5 · canário AO VIVO §3.2/§3.5/§3.6/§3.7).

O que cada bloco prova, e a MUTAÇÃO que o deixa vermelho (CLAUDE.md §9.3: um guarda que não falha não guarda nada):
  1. a ATIVIDADE (B1): a etapa CLASSE não aceita um rótulo quando o pedido tem palavra que nem o rótulo nem a classe
     cobrem — nas DUAS direções — e os acertos de hoje continuam. Mutação: a regra antiga (classe pelo sinônimo, sem
     olhar a exclusão do pedido, vocabulário que cobre tudo) → os 7 casos do juiz/red voltam a receber o código errado.
  2. a BUSCA (canário #2): mais de um termo (o texto + o radical de cada palavra + os da classe), medida num filtro
     por trecho sobre os rótulos MEDIDOS (formulario_empresarial.json) — e a escolha continua com a mesma regra.
  3. a BÁSICA (B2, D-129C-03): o ajuste de cobertura nunca muda a Básica — no Python (as chaves que o robô manda) e no
     node (o montador.js REAL), e no FIO (Chromium REAL + Agger dublê: recalcular com a Básica no ajuste). Mutação: o
     montador sem a trava → a Básica do ajuste vai ao Agger.
  4. a RC OPERAÇÕES (red P5): cada RC com o seu valor do pedido.
  5. o MOTIVO (canário #5): o leitor carrega o texto da recusa; o MOTOR (o real, com o banco dublê da 129-B) o grava
     saneado quando a coluna existe e grava o evento SEM ele quando a migration ainda não foi aplicada.
  6. os PDFs (canário #7): as classes de falha chegam ao log, nunca uma URL.
  7. a FAMÍLIA do "sem atividade compatível" é a da comparação; `valorDeNovo` numa forma só.
⛔ Dado FICTÍCIO; nenhum nome de corretora (§13.9).
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129c_conserto_portal.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import atividade_empresarial as A  # noqa: E402
from portal_worker.multicalculo import contrato as C  # noqa: E402
from portal_worker.multicalculo import leitor_agger as L  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402

import test_spec129c_o_portal_por_ramo as F1  # noqa: E402  (os helpers da F1: node, gravações, Agger dublê de RE)

FIX = BACKEND / "tests" / "fixtures" / "agger_ramos"


def _bloco(seg: int, *rotulos: str) -> dict:
    return {"seguradora": seg, "KeyValue": [{"Key": f"K{seg}-{i}", "Value": v, "Description": None}
                                            for i, v in enumerate(rotulos)]}


# ======================================================================================================================
# 1. A ATIVIDADE — juiz B1 + red B1
# ======================================================================================================================
# (pedido, rótulo que a seguradora tem) → a seguradora tem de SAIR. As duas direções do juiz e do red, com os rótulos
# que eles usaram (📊 laudos 129c-juiz.md B1 e 129c-red.md B1 / a1_atividade.py).
ERRADOS = [
    ("estética automotiva", "CABELEIREIROS, SALAO DE BELEZA E/OU ESTETICA"),     # pedido automotivo × rótulo de beleza
    ("estética automotiva", "CLINICA DE ESTETICA"),
    ("lava-rápido e estética automotiva", "CLINICA DE ESTETICA"),
    ("clínica de estética", "ESTETICA AUTOMOTIVA / LAVA-RAPIDO"),                # pedido de beleza × rótulo automotivo
    ("oficina de costura", "OFICINA MECANICA DE VEICULOS"),
    ("oficina de costura", "OFICINA MECANICA"),
    ("aluguel de máquinas", "FABRICA DE MAQUINAS"),
    ("consultório odontológico", "CONSULTORIO MEDICO"),
    ("clínica médica", "ARTIGOS MEDICOS E HOSPITALARES (COMERCIO)"),
    ("dentista", "ARTIGOS MEDICOS E HOSPITALARES (COMERCIO)"),
    ("loja de artigos médicos", "CONSULTORIO MEDICO"),
    ("escritório de informática", "ESCRITORIO EM GERAL"),
    ("posto de combustível", "LOJA DE CONVENIENCIA EM POSTO DE COMBUSTIVEL"),
]
# e os que TÊM de continuar casando pela classe (controle: a regra nova não pode ser "ninguém casa")
CERTOS = [
    ("clínica de estética", "CABELEIREIROS, SALAO DE BELEZA E/OU ESTETICA"),
    ("salão de beleza", "CABELEIREIROS, BARBEARIA, SALÃO DE BELEZA E/OU ESTÉTICA"),
    ("clínica médica", "CONSULTORIO MEDICO"),
    ("consultório odontológico", "CONSULTORIO ODONTOLOGICO"),
    ("dentista", "CLINICA ODONTOLOGICA"),
    ("loja de artigos médicos", "ARTIGOS MEDICOS E HOSPITALARES (COMERCIO)"),
    ("oficina mecânica", "OFICINA MECANICA DE VEICULOS"),
    ("escritório de advocacia", "ESCRITORIO EM GERAL"),
    ("edifícios desocupados", "Imóvel desocupado"),
]


@pytest.mark.parametrize("pedido,rotulo", ERRADOS)
def test_b1_a_classe_nao_aceita_o_rotulo_errado(pedido, rotulo):
    assert A.escolher([{"Key": "K", "Value": rotulo}], pedido, pavimento="0") == (None, "nenhum")


@pytest.mark.parametrize("pedido,rotulo", CERTOS)
def test_b1_controle_a_classe_ainda_casa_o_certo(pedido, rotulo):
    o, motivo = A.escolher([{"Key": "K", "Value": rotulo}], pedido, pavimento="0")
    assert o == {"Key": "K", "Value": rotulo} and motivo in ("exato", "palavras", "classe")


# 📊 medido 11/10 com `_regra_antiga`: 12 dos 13 recebiam o código (só a isca na direção que a F1 já testava saía)
N_ERRADOS_NA_REGRA_ANTIGA = 12


def _regra_antiga(monkeypatch):
    """A MUTAÇÃO: o escolhedor de antes do conserto — a 1ª classe pelo sinônimo (sem olhar a exclusão do pedido), a
    classe aceita qualquer palavra do pedido, e a "clinica_saude" de antes (consultório + odonto + artigos médicos)."""
    antiga_saude = {"sinonimos": ("clinica medica", "consultorio", "odontolog", "dentista", "dentari",
                                  "artigos medicos", "medico", "medica"),
                    "termos": ("consultorio", "clinica"), "vocabulario": ("",),
                    "aceita": re.compile(r"consultorio|clinica (medica|odontolog)|odontolog|dentari|medic"),
                    "exclui": re.compile(r"estetic|veterinar")}
    classes = []
    for nome, c in A.CLASSES:
        if nome in ("artigos_medicos", "odontologia", "consultorio_medico"):
            if nome == "artigos_medicos":
                classes.append(("clinica_saude", antiga_saude))
            continue
        classes.append((nome, {**c, "vocabulario": ("",)}))
    monkeypatch.setattr(A, "CLASSES", tuple(classes))
    monkeypatch.setattr(A, "QUALIFICADORES", ("deposito", "shopping", "aeroporto", "posto de combustivel"))

    def classe_antiga(atividade, cnae=None):
        txt = A.normalizar(atividade)
        for nome, c in A.CLASSES:
            if any(s in txt for s in c["sinonimos"]):
                return nome
        return None
    monkeypatch.setattr(A, "classe_do_pedido", classe_antiga)


def test_b1_mutacao_a_regra_antiga_fica_vermelha(monkeypatch):
    _regra_antiga(monkeypatch)
    aceitos = [(p, r) for p, r in ERRADOS if A.escolher([{"Key": "K", "Value": r}], p, pavimento="0")[0] is not None]
    assert len(aceitos) == N_ERRADOS_NA_REGRA_ANTIGA, aceitos
    assert ("estética automotiva", "CABELEIREIROS, SALAO DE BELEZA E/OU ESTETICA") in aceitos
    assert ("consultório odontológico", "CONSULTORIO MEDICO") in aceitos
    assert ("dentista", "ARTIGOS MEDICOS E HOSPITALARES (COMERCIO)") in aceitos


def _opcoes_da_gravacao_1(com_isca: bool) -> list:
    """Os rótulos REAIS que uma pessoa escolheu para a estética (📊 gravacao_empresarial_1, 8 seguradoras)."""
    g = json.loads((FIX / "gravacao_empresarial_1.json").read_text(encoding="utf-8"))
    blocos = []
    for it in g["versao"]["calculos"]:
        kv = it["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]
        kvs = [{"Key": kv["Key"], "Value": kv["Value"], "Description": None}]
        if com_isca:
            kvs.insert(0, {"Key": f"ISCA-{it['seguradora']}", "Value": "ESTETICA AUTOMOTIVA / LAVA-RAPIDO",
                           "Description": None})
        blocos.append({"seguradora": int(it["seguradora"]), "KeyValue": kvs})
    return blocos, {int(it["seguradora"]): it["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]["Key"]
                    for it in g["versao"]["calculos"]}


@pytest.mark.parametrize("pedido", ["estética automotiva", "lava-jato e estética automotiva"])
def test_b1_a_prova_do_red_estetica_automotiva_sai_em_todas(pedido):
    blocos, humano = _opcoes_da_gravacao_1(com_isca=False)
    esc, fora = A.escolher_atividades([{"termo": t, "opcoes": blocos} for t in A.termos_de_busca(pedido)], pedido,
                                      pavimento="0", seguradoras=humano)
    assert esc == {} and set(fora) == set(humano)                      # 📊 antes: 8 de 8 recebiam salão/clínica
    # e a busca não pede ao Agger a CLASSE errada (a de beleza): só o texto e os radicais do próprio pedido
    assert A.classe_do_pedido(pedido) is None and "beleza" not in A.termos_de_busca(pedido)


def test_b1_controle_clinica_de_estetica_continua_8_de_8_iguais_a_pessoa():
    blocos, humano = _opcoes_da_gravacao_1(com_isca=True)
    pedido = "clínica de estética"
    esc, fora = A.escolher_atividades([{"termo": t, "opcoes": blocos} for t in A.termos_de_busca(pedido)], pedido,
                                      pavimento="0", seguradoras=humano)
    assert fora == {} and {s: kv["Key"] for s, kv in esc.items()} == humano


def test_b1_os_acertos_medidos_de_hoje_continuam():
    def amostra(t):
        a = F1._form("empresarial")["atividade_por_seguradora"]["amostra_medida_11_10"][t]
        return [{"seguradora": s["seguradora"], "KeyValue": [{"Key": k, "Value": v, "Description": None}
                                                             for k, v in s["amostra"]]} for s in a]
    humano = F1._escolha_humana(F1._grav("empresarial", 2))
    esc, fora = A.escolher_atividades([{"termo": "escritorio", "opcoes": amostra("escritorio")}], "escritório",
                                      pavimento="2", seguradoras=humano)
    assert {s for s in esc if esc[s]["Key"] == humano[s]} == set(humano) - {8} and fora == {8: "nenhum"}   # 8 de 9
    esc, fora = A.escolher_atividades([{"termo": "padaria", "opcoes": amostra("padaria")}], "padaria")
    assert len(esc) == 14 and fora == {3: "ambiguo"}


# ======================================================================================================================
# 2. A BUSCA — canário #2 ("edifícios desocupados": 📊 1 opção em 15 blocos)
# ======================================================================================================================
def _pool() -> dict:
    """Todos os rótulos MEDIDOS de `getOptionsBySegFull` (formulario_empresarial.json, 4 termos × 15 seguradoras) + o
    único que o canário achou ("Edifícios desocupados", Allianz 5)."""
    pool: dict = {}
    for v in F1._form("empresarial")["atividade_por_seguradora"]["amostra_medida_11_10"].values():
        for s in v:
            for k, rot in s["amostra"]:
                pool.setdefault(s["seguradora"], {})[k] = rot
    pool.setdefault(5, {})["ED-5"] = "Edifícios desocupados"
    return pool


def _agger_por_trecho(pool: dict, termos) -> list:
    """💭 o filtro da tela, simulado: devolve o rótulo que CONTÉM o termo, sem acento (📊 o canário pediu
    "edificios desocupados" e veio "Edifícios desocupados" — sem acento casa com acento)."""
    out = []
    for t in termos:
        n = A.normalizar(t)
        out.append({"termo": t, "opcoes": [{"seguradora": s, "KeyValue": [
            {"Key": k, "Value": v, "Description": None} for k, v in d.items() if n in A.normalizar(v)]}
            for s, d in pool.items()]})
    return out


@pytest.mark.parametrize("pedido,antes,depois", [
    # 📊 medido com a função abaixo, 11/10 (seguradoras com código escolhido: só o texto × os termos novos)
    ("padaria e confeitaria", 3, 10), ("restaurantes", 2, 14), ("farmácias e drogarias", 2, 11),
    ("escritórios", 3, 11), ("drogaria", 11, 11)])
def test_busca_com_mais_de_um_termo_acha_mais_sem_relaxar(pedido, antes, depois):
    pool = _pool()

    def escolhidas(termos):
        esc, _ = A.escolher_atividades(_agger_por_trecho(pool, termos), pedido, pavimento="0", seguradoras=list(pool))
        return esc
    so_texto = escolhidas([A.normalizar(pedido)])
    novos = escolhidas(A.termos_de_busca(pedido))
    assert (len(so_texto), len(novos)) == (antes, depois)
    # sem relaxar: cada código escolhido tem TODAS as palavras do pedido no rótulo (etapa PALAVRAS) — nenhum veio da
    # etapa CLASSE por um rótulo que não diz o pedido
    ps = A.palavras(pedido)
    assert all(all(A._tem_palavra(A.rotulo_limpo(kv["Value"]), p) for p in ps) for kv in novos.values())


def test_busca_edificios_desocupados_pede_o_radical_e_so_casa_desocupado():
    termos = A.termos_de_busca("edifícios desocupados")
    assert termos[0] == "edificios desocupados" and {"edifici", "desocupad"} <= set(termos)
    assert len(termos) <= A.MAX_TERMOS
    # 💭 rótulos hipotéticos de outras seguradoras (NÃO medidos): o desocupado casa; terreno/obra/residência saem
    pool = {5: {"a": "Edifícios desocupados"}, 1: {"b": "Imóvel desocupado"}, 4: {"c": "PREDIO DESOCUPADO"},
            8: {"d": "TERRENO DESOCUPADO"}, 11: {"e": "IMOVEL DESOCUPADO EM REFORMA"},
            12: {"f": "Edifício residencial desocupado"}, 3: {"g": "EDIFICIO DE ESCRITORIOS"}}
    esc, fora = A.escolher_atividades(_agger_por_trecho(pool, termos), "edifícios desocupados", pavimento="0",
                                      seguradoras=list(pool))
    assert set(esc) == {5, 1, 4} and set(fora) == {8, 11, 12, 3}


# ======================================================================================================================
# 3. A BÁSICA no ajuste — juiz B2 (D-129C-03: a Básica de RE vem SÓ do pedido)
# ======================================================================================================================
def test_b2_as_chaves_do_ajuste_nao_tem_a_basica():
    for ramo, chaves in P.CHAVES_DO_AJUSTE_RE.items():
        assert P.CHAVE_DA_BASICA not in chaves
        assert set(chaves) == set(P.CHAVES_DE_COBERTURA_RE[ramo]) - {P.CHAVE_DA_BASICA}


def test_b2_o_robo_manda_ao_montador_as_chaves_sem_a_basica(monkeypatch):
    visto = {}

    async def preparar(sessao, args):
        visto.update(args)
        return "ok"
    monkeypatch.setattr(R, "_preparar_e_enviar", preparar)
    aj = C.Ajuste("cobertura", {P.CHAVE_DA_BASICA: 1000, "vidros": 5000})
    asyncio.run(R.recalcular(object(), "NEG", versao_base=1, ajuste=aj))
    assert all(P.CHAVE_DA_BASICA not in ks for ks in visto["chaves_re"].values())
    assert visto["chaves_re"]["16"] and "vidros" in visto["chaves_re"]["16"]


_AJUSTE_JS = ("const cot = {ramo: 16, configuracoes: {isDanosIncendioRaioExplosao: 9000000, vidros: 0}, calculos: []};"
              "const n = M.aplicarAjuste(cot, a.aj, {chaves: a.chaves});"
              "process.stdout.write(JSON.stringify([n, cot.configuracoes]))")


@pytest.mark.parametrize("lista", ["do_robo", "com_a_basica"])
def test_b2_node_o_montador_nunca_muda_a_basica(lista):
    chaves = P.CHAVES_DO_AJUSTE_RE if lista == "do_robo" else P.CHAVES_DE_COBERTURA_RE   # 2ª: a trava do próprio JS
    entrada = {"aj": {"tipo": "cobertura", "valor": {P.CHAVE_DA_BASICA: 1000, "vidros": 5000}, "seguradora": None},
               "chaves": {str(r): list(k) for r, k in chaves.items()}}
    n, cfg = F1._node(_AJUSTE_JS, entrada)
    assert cfg == {P.CHAVE_DA_BASICA: 9000000, "vidros": 5000} and n == 1
    # só a Básica no ajuste → nada a aplicar → o robô recusa ("ajuste_sem_alvo"), nada sai
    entrada["aj"]["valor"] = {P.CHAVE_DA_BASICA: 1000}
    n, cfg = F1._node(_AJUSTE_JS, entrada)
    assert n == 0 and cfg[P.CHAVE_DA_BASICA] == 9000000


def test_b2_mutacao_montador_sem_a_trava_fica_vermelho(monkeypatch):
    sem_trava = F1.MONTADOR.replace(" && k !== CHAVE_DA_BASICA_RE", "")
    assert sem_trava != F1.MONTADOR
    monkeypatch.setattr(F1, "MONTADOR", sem_trava)
    entrada = {"aj": {"tipo": "cobertura", "valor": {P.CHAVE_DA_BASICA: 1000, "vidros": 5000}, "seguradora": None},
               "chaves": {str(r): list(k) for r, k in P.CHAVES_DE_COBERTURA_RE.items()}}
    _n, cfg = F1._node(_AJUSTE_JS, entrada)
    assert cfg[P.CHAVE_DA_BASICA] == 1000          # o defeito do juiz B2 reproduzido: a Básica do ajuste vai ao Agger


def test_b2_o_fio_recalcular_com_a_basica_no_ajuste_manda_a_do_pedido(monkeypatch):
    """Chromium REAL + Agger dublê (a gravação condominio_1): disparar → recalcular(cobertura com a Básica) → o corpo
    que chega ao Agger leva a Básica do PEDIDO e o resto do ajuste."""
    from dubles.agger_duble import SENHA
    pytest.importorskip("playwright.async_api")
    g = F1._grav("condominio", 1)
    ped = F1.pedido_re(16)
    basica = ped["risco"]["valor_basica"]
    duble = F1._dubleRE(16, g, {})

    async def corpo(d, sessoes):
        sessao = await sessoes.obter(F1._conta(), senha=SENHA, negocios_do_robo=set())
        disp = await R.disparar(sessao, ped, P.coberturas_re(16, "padrao", basica))
        assert d.posts_calcular[-1]["cotacao"]["configuracoes"][P.CHAVE_DA_BASICA] == basica
        aj = C.Ajuste("cobertura", {P.CHAVE_DA_BASICA: 1000, "vidros": 77_000})
        await R.recalcular(sessao, disp.negocio_ref, versao_base=1, ajuste=aj)
        cfg = d.posts_calcular[-1]["cotacao"]["configuracoes"]
        n = len(d.posts_calcular)
        with pytest.raises(R.DisparoRecusado):    # só a Básica no ajuste: nada a mudar → nada sai
            await R.recalcular(sessao, disp.negocio_ref, versao_base=1,
                               ajuste=C.Ajuste("cobertura", {P.CHAVE_DA_BASICA: 1000}))
        assert len(d.posts_calcular) == n
        await sessoes.fechar(F1._conta()["id"])
        return cfg
    cfg = asyncio.run(F1._com_agger_re(duble, corpo))
    assert cfg[P.CHAVE_DA_BASICA] == basica and cfg["vidros"] == 77_000


# ======================================================================================================================
# 4. A RC OPERAÇÕES — red P5
# ======================================================================================================================
@pytest.mark.parametrize("extras,rc,rcop", [
    ({"responsabilidadeCivil": 100_000, "responsabilidadeCivilOperacoes": 300_000}, 100_000, 300_000),  # as duas
    ({"responsabilidadeCivil": 100_000}, 100_000, 100_000),            # só a RC → a Operações acompanha (📊 gravados)
    ({"responsabilidadeCivilOperacoes": 300_000}, 300_000, 300_000),   # só a Operações → a RC acompanha
    ({}, 125_000, 125_000),                                            # nenhuma → o preset (125 mil, as duas)
])
def test_p5_cada_rc_com_o_seu_valor_do_pedido(extras, rc, rcop):
    ped = F1.pedido_re(18, extras=extras) if extras else F1.pedido_re(18)
    cob = P.coberturas_re(18, "padrao", ped["risco"]["valor_basica"], extras or None)
    cfg = R.cotacao_do_pedido(ped, coberturas=cob)["cotacao"]["configuracoes"]
    assert (cfg["responsabilidadeCivil"], cfg["responsabilidadeCivilOperacoes"]) == (rc, rcop)


# ======================================================================================================================
# 5. O MOTIVO da recusa — canário #5
# ======================================================================================================================
def test_motivo_o_leitor_carrega_o_texto_da_recusa_das_gravacoes():
    g = F1._grav("empresarial", 2)
    r = L.ler_rodada({"corpo": g["calculos"], "ramo": 18}, ramo=18)
    rec = {e.seguradora_codigo: e for e in L.eventos_entre(None, r) if e.tipo == C.SEGURADORA_RECUSOU}
    assert set(rec) == {35, 3, 5, 12}
    # 📊 contagem independente: as mensagens cruas de `erros` de cada item, direto no JSON da fixture
    for it in g["calculos"]:
        s = int(it["seguradora"])
        if s in rec:
            cruas = [m for m in (it.get("erros") or []) if isinstance(m, str) and m.strip()]
            for res in it.get("resultados") or []:
                cruas += [m for m in (res.get("erros") or []) if isinstance(m, str) and m.strip()]
            assert cruas and " ".join(cruas[0].split())[:40] in rec[s].motivo
            assert len(rec[s].motivo) <= C.MOTIVO_MAX
    # o motivo NÃO muda a identidade do evento (a chave do motor e a igualdade)
    e = rec[12]
    assert e == C.Evento(e.tipo, e.t_s, e.seguradora, e.seguradora_codigo, e.familia, None, e.ramo)


def _motor_129b():
    import test_spec129b_o_motor as M
    return M


def _ambiente(monkeypatch):
    """O MESMO ambiente do teste do motor da 129-B (banco dublê com as travas do U1, Agger dublê da §6.4)."""
    M = _motor_129b()
    from types import SimpleNamespace
    from cryptography.fernet import Fernet

    M.instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    from portal_worker import leases
    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)
    relogio = M.D.Relogio(M.T0)
    return SimpleNamespace(banco=M.BancoU1(relogio), relogio=relogio, mundo=M.MundoAgger())


@pytest.mark.parametrize("com_coluna", [True, False])
def test_motivo_o_motor_grava_saneado_e_sobrevive_sem_a_coluna(com_coluna, monkeypatch, caplog):
    M = _motor_129b()
    amb = _ambiente(monkeypatch)
    if com_coluna:      # o esquema DEPOIS da migration 20261011_01
        monkeypatch.setitem(M.D.ESQUEMA, "multicalculo_eventos",
                            {**M.D.ESQUEMA["multicalculo_eventos"], "motivo": ("text", True, None)})
    caplog.set_level(logging.INFO)
    canal, a, b = M.empresa(amb), M.empresa(amb), M.empresa(amb)
    M.robo(amb, a), M.robo(amb, b)
    _pid, ids = M.pedido(amb, canal, [a, b])
    m = M.motor(amb, "motor-1")
    assert M.rodar(m.uma_volta()) == 2
    for cid in ids:
        assert M.calc(amb, cid)["status"] == "fechado"
    evs = [e for e in amb.banco.linhas("multicalculo_eventos") if e["tipo"] == C.SEGURADORA_RECUSOU]
    # 📊 leitor puro sobre a fixture do auto (vivo_conta_b): 3 recusas por cálculo × 4 cálculos
    assert len(evs) == 12
    if com_coluna:
        assert all(e["motivo"] for e in evs)
        assert {e["familia"] for e in evs} == {"ACEITACAO", "DADO", "COMERCIAL"}
        textos = " ".join(e["motivo"] for e in evs)
        assert "Calcule como Reno" in textos and "http" not in textos.lower()
        assert all(len(e["motivo"]) <= C.MOTIVO_MAX for e in evs)
        assert "sem a coluna `motivo`" not in caplog.text
    else:
        assert all("motivo" not in e for e in evs)
        assert caplog.text.count("sem a coluna `motivo`") == 1        # avisa UMA vez e segue sem o motivo
    M.rodar(m.desligar())


def test_motivo_o_redator_tira_url_e_documento_do_texto_da_seguradora():
    from portal_worker.multicalculo import motor as MOT
    texto = "Proponente 529.982.247-25 com restrição, veja https://seguradora.example/x?token=abc123"
    limpo = MOT.erro_curto(texto, C.MOTIVO_MAX)
    assert "529.982.247-25" not in limpo and "52998224725" not in limpo and "https" not in limpo
    assert limpo.startswith("Proponente")


# ======================================================================================================================
# 6. Os PDFs — canário #7: o porquê de cada falha, nunca a URL
# ======================================================================================================================
def test_pdfs_as_classes_de_falha_passam_e_o_resto_nao():
    r = {"pdfs": [], "falhas": 4, "motivos": {"http_403": 2, "rede": 1, "so_nome": 1,
                                               "https://quotation-files.example/a.pdf": 1, "nao_pdf": True}}
    assert R.motivos_dos_pdfs(r) == {"http_403": 2, "rede": 1, "so_nome": 1}
    assert R.motivos_dos_pdfs(None) == {} and R.motivos_dos_pdfs({"motivos": "x"}) == {}
    # a página conta por CLASSE (o mesmo texto que o Python aceita)
    for k in ("'http_'", "conta('rede')", "conta('nao_pdf')", "conta('grande')", "conta('so_nome')"):
        assert k in R.JS_PDFS


def test_pdfs_copiar_loga_as_classes(caplog):
    class Sessao:
        bases = {"api": "https://api.example", "pdocs": "https://pdocs.example"}

        def token(self, qual):
            return "TOKEN-" + qual

        async def avaliar(self, js, args):
            assert js is R.JS_PDFS
            return {"pdfs": [], "falhas": 3, "motivos": {"rede": 2, "http_404": 1}}
    caplog.set_level(logging.INFO)
    disp = R.Disparo("NEG", 1, 0.0)
    assert asyncio.run(R.copiar_pdfs(Sessao(), disp)) == {}
    assert "3 não copiados {'http_404': 1, 'rede': 2}" in caplog.text


# ======================================================================================================================
# 7. A FAMÍLIA do "sem atividade compatível" e o `valorDeNovo`
# ======================================================================================================================
def test_familia_sem_atividade_e_a_da_comparacao():
    from app.services.multicalculo import comparacao as CMP
    assert C.SEM_ATIVIDADE == CMP.SEM_ATIVIDADE == C.SEM_ATIVIDADE_COMPATIVEL.upper()
    assert C.SEM_ATIVIDADE in C.FAMILIAS


def test_familia_sem_atividade_no_motor(monkeypatch):
    M = _motor_129b()
    amb = _ambiente(monkeypatch)
    from types import SimpleNamespace
    from portal_worker.multicalculo import motor as MOT
    canal, a = M.empresa(amb), M.empresa(amb)
    M.robo(amb, a)
    pid, ids = M.pedido(amb, canal, [a], opcoes=("padrao",))
    m = M.motor(amb, "motor-1")
    g = SimpleNamespace(pedido_id=pid, company_id=a, solicitante_company_id=canal)
    M.rodar(m._gravar_sem_atividade(g, {"id": ids[0]}, [(8, "Porto Seguro"), (11, "Tokio")], 18))
    evs = [e for e in amb.banco.linhas("multicalculo_eventos") if e["tipo"] == C.SEM_ATIVIDADE_COMPATIVEL]
    assert {e["seguradora_codigo"] for e in evs} == {8, 11} and {e["familia"] for e in evs} == {C.SEM_ATIVIDADE}
    assert MOT  # o motor REAL


@pytest.mark.parametrize("ecoado,esperado", [("Sim", 1), ("SIM", 1), ("Não", 0), (1, 1), (0, 0), (True, 1),
                                             ("Talvez", "Talvez")])
def test_valor_de_novo_numa_forma_so_no_re(ecoado, esperado):
    item = {"seguradora": 5, "seguradoraTxt": "Allianz", "resultados": [
        {"premio": 1000.0, "identificacao": "Pacote", "packageType": 0,
         "coberturas": {"valorDeNovo": ecoado, "isDanosIncendioRaioExplosao": 100000}}]}
    o = L.ler_resposta(item, 16).ofertas[0]
    assert dict(o.coberturas)["valorDeNovo"] == esperado
    # o auto não muda (não há `valorDeNovo` "Sim" no auto e a regra é só do RE)
    assert L.sim_nao("Sim") == 1
