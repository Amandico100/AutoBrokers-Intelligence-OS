# -*- coding: utf-8 -*-
"""SPEC-129-C F1 — o lado do PORTAL por ramo: contrato · presets · montador · robô · leitor (Condomínio 16 ·
Residencial 2 · Empresarial 18; o AUTO 31 byte a byte igual).

O FIO (por ramo): o PEDIDO do contrato (`contrato.PedidoDeCalculoRE`) → as coberturas da opção
(`presets.coberturas_re`) → `agger_robo.disparar` num Chromium REAL contra o Agger DUBLÊ (tests/dubles/agger_duble.py,
aqui com a config, as atividades e a RESPOSTA das 9 gravações reais saneadas — tests/fixtures/agger_ramos/) → o corpo
montado NA PÁGINA pelo montador.js → `acompanhar` (GET calculos, lista branca DO RAMO) → `leitor_agger` REAL → as
ofertas. O corpo é conferido contra a FORMA gravada (as chaves de `configuracoes` e dos itens, a comissão no item, a
vigência); as ofertas, contra uma contagem INDEPENDENTE feita aqui direto no JSON das fixtures.

Mutações que ficam VERMELHAS: comissão fora do item · cobertura dentro do item no RE · atividade errada aceita ·
o auto alterado (o hash do corpo do auto da 129-B).
⛔ Dado FICTÍCIO (CNPJ/CPF de exemplo, endereço inventado); nenhum nome de corretora (§13.9).
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129c_o_portal_por_ramo.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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

FIX = BACKEND / "tests" / "fixtures" / "agger_ramos"
MONTADOR = (BACKEND / "portal_worker" / "multicalculo" / "montador.js").read_text(encoding="utf-8")
RAMO = {"condominio": 16, "residencial": 2, "empresarial": 18}
NOME_DO = {v: k for k, v in RAMO.items()}
SEGREDOS = ("SEGREDO-", "TOKEN-")
VIGENCIA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")   # 📊 o formato gravado ('…T17:47:20.353Z')
CNPJ = "11222333000181"     # CNPJ de exemplo (dígitos válidos), não é de ninguém do piloto
CPF = "00000000191"


def _grav(nome: str, i: int) -> dict:
    return json.loads((FIX / f"gravacao_{nome}_{i}.json").read_text(encoding="utf-8"))


def _form(nome: str) -> dict:
    return json.loads((FIX / f"formulario_{nome}.json").read_text(encoding="utf-8"))


def _endereco() -> dict:
    return {"cep": "88000000", "logradouro": "Rua Ficticia", "numero": "100", "bairro": "Centro",
            "cidade": "Cidade Ficticia", "uf": "SC"}


def pedido_re(ramo: int, **risco_extra) -> dict:
    if ramo == 16:
        seg = {"cpf_cnpj": CNPJ, "nome": "Condominio Ficticio"}
        risco = {**_endereco(), "valor_basica": 14_000_000, "tipo_imovel": 1, "estrutura": 1, "ano_fundacao": "2005",
                 "blocos": "4", "pavimentos": "5", "elevadores": 0, "protecoes": [1, 7]}
        ren = {"renovacao": True, "seguradora_anterior": "AXA Seguros", "bonus_anterior": 5, "sinistros_anterior": 0,
               "fim_vigencia_anterior": "2026-10-31"}
        com = 25
    elif ramo == 2:
        seg = {"cpf_cnpj": CPF, "nome": "Pessoa Ficticia", "nascimento": "1980-01-01"}
        risco = {**_endereco(), "valor_basica": 550_000, "tipo_imovel": 1, "construcao": 1, "uso": 1, "objeto": 3}
        ren = {}
        com = 20
    else:
        seg = {"cpf_cnpj": CNPJ, "nome": "Empresa Ficticia"}
        risco = {**_endereco(), "valor_basica": 800_000, "atividade": "escritório", "pavimento": "2",
                 "localizacao": "0", "construcao": 1, "objeto": 3}
        ren = {}
        com = 20
    risco.update(risco_extra)
    return C.PedidoDeCalculoRE.de_dict({"ramo": ramo, "segurado": seg, "risco": risco, "renovacao": ren,
                                        "comissao_desconto": {"comissao_percentual": com}}).para_dict()


# ======================================================================================================================
# node — o montador.js puro (a mesma fonte que o robô carrega na página)
# ======================================================================================================================
def _node(corpo_js: str, entrada) -> object:
    if not shutil.which("node"):
        pytest.skip("node ausente")
    js = "const window = {};\n" + MONTADOR + "\nconst M = window.__abM;\nconst a = JSON.parse(require('fs')" \
         ".readFileSync(0, 'utf8'));\n" + corpo_js
    r = subprocess.run(["node", "-e", js], input=json.dumps(entrada).encode("utf-8"), capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:500]
    return json.loads(r.stdout)


# ======================================================================================================================
# 1. O CONTRATO
# ======================================================================================================================
def test_contrato_os_codigos_sao_os_dos_formularios_medidos():
    """Cada código de lista do contrato é uma opção da tela, lida AGORA no formulario_<ramo>.json (contagem própria)."""
    campo_da_tela = {(16, "tipo_imovel"): "imovelAtividade", (16, "estrutura"): "estruturaCondominio",
                     (2, "tipo_imovel"): "imovelTipoResidencia", (2, "construcao"): "imovelConstrucao",
                     (2, "uso"): "imovelUso", (2, "objeto"): "imovelObjetoSegurado",
                     (18, "pavimento"): "imovelPavimentacao", (18, "localizacao"): "imovelLocalEstabelecimento",
                     (18, "construcao"): "imovelConstrucao", (18, "objeto"): "imovelObjetoSegurado"}
    for (ramo, nome), campo in campo_da_tela.items():
        tela = next(c for c in _form(NOME_DO[ramo])["campos"] if c["campo"] == campo)
        codigos = {o["codigo"] for o in tela["opcoes"]}
        validos = C.CODIGOS_VALIDOS_RE[(ramo, nome)]
        assert {str(c) for c in validos} == {str(c) for c in codigos}, (ramo, nome)
        if ramo == 18 and nome in ("pavimento", "localizacao"):
            assert all(isinstance(c, str) for c in validos)          # 📊 TEXTO no corpo
    # os 2 campos de equipamentos do condomínio = os códigos de sisProtecaoIncendRoubo
    tela = {o["codigo"] for c in _form("condominio")["campos"] if c["campo"] in ("equipamentosSeguranca", "equipamentosIncendio")
            for o in c["opcoes"]}
    assert C.CODIGOS_VALIDOS_RE[(16, "protecoes")] == frozenset(tela)
    # todo campo sim/não do bem é um booleano da tela (vira_campo_booleano) — nenhum inventado
    for nome, ramo in RAMO.items():
        booleanos = {o["vira_campo_booleano"] for c in _form(nome)["campos"] for o in c.get("opcoes") or []
                     if "vira_campo_booleano" in o}
        do_contrato = {C.chave_no_corpo(ramo, "risco", n) for n, _c, _o in C.CAMPOS_DO_PEDIDO_RE[ramo]["risco"]
                       if C.tipo_do_campo_re("risco", n) == "booleano" and n != "valor_de_novo"}
        assert do_contrato <= booleanos, (nome, do_contrato - booleanos)
    # o filtro global de seguradoras = o medido
    for nome, ramo in RAMO.items():
        assert list(C.SEGURADORAS_DO_RAMO[ramo]) == _form(nome)["seguradoras"]["habilitadas_no_agger_global"]


def test_contrato_valida_por_ramo_e_so_diz_nomes():
    assert C.problemas_do_pedido_re(pedido_re(16)) == ()
    ruim = pedido_re(18)
    ruim["risco"].pop("atividade")
    ruim["risco"]["pavimento"] = 2                        # inteiro: o corpo quer o TEXTO "2"
    ruim["comissao_desconto"] = {}
    ruim["risco"]["construcao"] = 9
    probs = C.problemas_do_pedido_re(ruim)
    assert set(probs) == {"risco.atividade", "risco.pavimento:codigo", "risco.construcao:codigo",
                          "comissao_desconto.comissao_percentual"}
    assert not any(CNPJ in p for p in probs)
    with pytest.raises(ValueError, match="comissao_percentual"):
        C.PedidoDeCalculoRE.de_dict(ruim)
    assert "Empresa" not in repr(C.PedidoDeCalculoRE.de_dict(pedido_re(18)))
    assert C.campos_do_pedido(31) is C.CAMPOS_DO_PEDIDO_AUTO
    with pytest.raises(ValueError):
        C.Ajuste("franquia", 2, ramo=16)
    C.Ajuste("assistencia", 3, ramo=16)


# ======================================================================================================================
# 2. OS PRESETS — nenhum valor segurado fixo; os códigos de assistência do RE
# ======================================================================================================================
def test_presets_re_basica_do_pedido_e_opcoes():
    for nome, ramo in RAMO.items():
        form = {c["campo"] for c in _form(nome)["campos"]}
        assert set(P.CHAVES_DE_COBERTURA_RE[ramo]) - {"responsabilidadeCivilOperacoes"} <= form
        pad = P.coberturas_re(ramo, "padrao", 1_234_567)
        eco = P.coberturas_re(ramo, "economica", 1_234_567)
        assert set(pad) == set(eco) == set(P.CHAVES_DE_COBERTURA_RE[ramo])
        assert pad[P.CHAVE_DA_BASICA] == eco[P.CHAVE_DA_BASICA] == 1_234_567       # a Básica é a do PEDIDO
        assert eco["assist24hs"] == 1                                              # Básica = 1 no RE (não 4)
        com_valor = {k for k, v in eco.items() if v and k not in ("assist24hs", P.CHAVE_DA_BASICA)}
        assert com_valor <= {k for k, v in pad.items() if v}                       # a "mais em conta" ⊂ padrão
        assert len(com_valor) < len({k for k, v in pad.items() if v}) - 2
    assert P.coberturas_re(16, "padrao", 1)["assist24hs"] == 3
    assert P.coberturas_re(2, "padrao", 1)["assist24hs"] == 2
    # a escala: um condomínio pequeno não herda o aluguel de um grande; a RC não escala
    peq, gde = P.coberturas_re(16, "padrao", 700_000), P.coberturas_re(16, "padrao", 40_000_000)
    assert peq["isDanosAluguel"] < gde["isDanosAluguel"] == 300_000
    assert peq["isValorSindico"] == gde["isValorSindico"] == 300_000
    assert P.coberturas_re(16, "padrao", 700_000, {"isDanosAluguel": 1})["isDanosAluguel"] == 1   # o pedido vence
    with pytest.raises(ValueError):
        P.coberturas_re(16, "padrao", 0)
    with pytest.raises(ValueError):
        P.coberturas_re(16, "padrao", 1_000, {"carroReserva": 1})
    # o AUTO não mudou
    assert P.coberturas_de("padrao")["assist24hs"] == 1 and P.coberturas_de("economica")["assist24hs"] == 4
    assert P.ORDEM == ("padrao", "economica", "completa_mais", "minima")


# ======================================================================================================================
# 3. O AUTO byte a byte (G3) — o hash do que o montador e o robô da 129-B produzem, tirado ANTES da 129-C
# ======================================================================================================================
# 📊 tirado em 11/10 com o montador.js/agger_robo.py do HEAD b1b65a4 (scratchpad do builder F1, auto_hash.py)
HASH_AUTO_MONTADOR = "8d3160924111c392da37e52d3fc07d5c6e29e55bfde387aa6a852399c962b15d"
HASH_AUTO_ROBO = "62eb124bd8d7a64e5b3b8861a0a697d38aa4feae694d66c4e5aa35bd6807f3c0"


def _saidas_do_auto():
    from dubles.agger_duble import AggerDuble
    cfg = AggerDuble().config
    versao = {"ramo": 31, "calculos": [dict(seguradora=c["seguradora"], percComissao=17, vidros=1, tipoFranquia=2,
                                            assist24hs=4, carroReserva=1) for c in cfg[:5]]}
    ajustes = [{"tipo": "franquia", "valor": 2, "seguradora": None},
               {"tipo": "assistencia", "valor": 4, "seguradora": 8},
               {"tipo": "percentual_fipe", "valor": 90, "seguradora": None},
               {"tipo": "cobertura", "valor": {"vidros": 0, "loginWs": "x"}, "seguradora": None},
               {"tipo": "comissao", "valor": 22, "seguradora": None}]
    js = _node(r"""
const out = {};
out.padrao = M.montarCalculos(a.cfg, a.padrao, 15, null);
out.econ = M.montarCalculos(a.cfg, a.econ, null, 3);
out.versao = M.montarDaVersao(a.cfg, a.versao);
for (const aj of a.ajustes) { const cot = {calculos: M.montarCalculos(a.cfg, a.padrao, 15, null), automoveis: [{pctAjuste: 100}]};
  const n = M.aplicarAjuste(cot, aj); out['aj_' + aj.tipo + '_' + n] = cot; }
process.stdout.write(JSON.stringify(out));""", {"cfg": cfg, "padrao": P.coberturas_de("padrao"),
                                                 "econ": P.coberturas_de("economica"), "versao": versao,
                                                 "ajustes": ajustes})
    ped = {"ramo": 31, "segurado": {"cpf_cnpj": CPF, "nome": "Pessoa Ficticia", "nascimento": "1980-01-01",
                                    "sexo": "F", "estado_civil": 2, "cep": "88000000"},
           "veiculo": {"placa": "TST1A23", "ano_modelo": 2012}, "pernoite": {},
           "condutor": {"tempo_habilitacao": 11, "relacao_com_segurado": "proprio"},
           "renovacao": {"renovacao": True, "seguradora_anterior": "HDI", "bonus_anterior": 3,
                         "fim_vigencia_anterior": "2026-11-01"},
           "coberturas": {}, "pacotes": {}, "comissao_desconto": {"comissao_percentual": 15},
           "questionario": {"km_mensal": 900}, "seguradoras": [], "assumidos": []}
    return js, ped


def _hash(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()


def test_g3_o_auto_byte_a_byte(monkeypatch):
    js, ped = _saidas_do_auto()
    monkeypatch.setattr(R, "correlation_id", lambda: "ab0b0000-0000-4000-a000-000000000000")
    py = R.cotacao_do_pedido(ped, agora=datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc))
    assert _hash(js) == HASH_AUTO_MONTADOR
    assert _hash(py) == HASH_AUTO_ROBO
    # MUTAÇÃO "auto alterado": uma chave a mais num item do auto → o hash acusa
    js["padrao"][0]["isDanosIncendioRaioExplosao"] = 1
    assert _hash(js) != HASH_AUTO_MONTADOR
    py["cotacao"]["ramo"] = 16
    assert _hash(py) != HASH_AUTO_ROBO


# ======================================================================================================================
# 4. O MONTADOR de RE (node)
# ======================================================================================================================
def _config_da_gravacao(g: dict, ramo: int) -> list:
    """A config `calculo/seguradoras` que o dublê serve: as seguradoras do negócio gravado (com o nome da config,
    a comissão/desconto POR RAMO como a conta mede — 📊 formulario_*.json `seguradoras.na_conta`) + iscas: Azul (10)
    e Itaú (9) ativas (nunca no RE), Sompo (6) ativa mas fora do ramo, e uma do ramo INATIVA."""
    from dubles.agger_duble import segredos_do_item
    out = []
    for it in g["versao"]["calculos"]:
        c = int(it["seguradora"])
        out.append({"id": 9000 + c, "seguradora": c, "nomeSeguradora": it.get("seguradoraTxt") or f"Seg {c}",
                    "ativo": True, "idIntegracao": f"cfg-{c}", "usuario": f"SEGREDO-LOGIN-usuario-{c}",
                    "percComissao": 0, "percDesconto": 0, "percComissaoCond": 10, "percDescontoCond": 25 if c == 5 else None,
                    "percComissaoResid": 10, "percDescontoResid": None, "percComissaoEmpres": 0,
                    "percDescontoEmpres": None, "susep": "000000", "credenciaisValidas": True,
                    **segredos_do_item(f"cfg{c}")})
    for c, ativo in ((10, True), (9, True), (6, True), (19, False)):
        out.append({"id": 9000 + c, "seguradora": c, "nomeSeguradora": f"Isca {c}", "ativo": ativo,
                    "idIntegracao": f"cfg-{c}", "percComissao": 0, **segredos_do_item(f"isca{c}")})
    return out


def _esperadas(g: dict, ramo: int) -> set:
    """Contagem PRÓPRIA: as seguradoras do negócio gravado ∩ a lista global medida do ramo, fora Azul/Aliro."""
    glob = set(_form(NOME_DO[ramo])["seguradoras"]["habilitadas_no_agger_global"])
    return {int(i["seguradora"]) for i in g["versao"]["calculos"]} & glob - {10, 22}


def test_montador_re_comissao_no_item_e_sem_cobertura():
    g = _grav("condominio", 1)
    cfg = _config_da_gravacao(g, 16)
    r = _node("process.stdout.write(JSON.stringify([M.montarCalculosRE(a.cfg, 16, 25, null, {status: a.st}),"
              " M.montarCalculosRE(a.cfg, 16, null, null, {status: a.st}), M.CAMPO_DO_AJUSTE_RE]))",
              {"cfg": cfg, "st": list(C.SEGURADORAS_DO_RAMO[16])})
    ok, sem, campo = r
    assert sem["erro"] == "sem_comissao" and sem["calculos"] == []
    assert {i["seguradora"] for i in ok["calculos"]} == _esperadas(g, 16)
    assert all(i["percComissao"] == 25 for i in ok["calculos"])
    assert next(i for i in ok["calculos"] if i["seguradora"] == 5)["percDesconto"] == 25   # 📊 = percDescontoCond
    assert not any(k in i for i in ok["calculos"] for k in set(P.CHAVES_DE_COBERTURA) | {
        k for ks in P.CHAVES_DE_COBERTURA_RE.values() for k in ks})
    assert campo == dict(P.CAMPO_DO_AJUSTE_RE)                                              # o gêmeo


# ======================================================================================================================
# 5. O LEITOR — as 9 respostas gravadas pela lista branca do RAMO (JS) → 2ª rede → leitor; contagem independente
# ======================================================================================================================
_FAMILIAS_ESPERADAS = {   # lidas à mão nas mensagens das fixtures (seguradora → família)
    ("condominio", 1): {32: C.ACEITACAO, 1: C.ACEITACAO}, ("condominio", 2): {1: C.DADO},
    ("condominio", 3): {32: C.DESCONHECIDA, 18: C.DESCONHECIDA}, ("residencial", 1): {}, ("residencial", 2): {},
    ("residencial", 3): {32: C.DESCONHECIDA}, ("empresarial", 1): {35: C.CREDENCIAL},
    ("empresarial", 2): {35: C.DADO, 3: C.DADO, 5: C.DADO, 12: C.ACEITACAO},
    ("empresarial", 3): {3: C.DESCONHECIDA, 7: C.DESCONHECIDA, 4: C.DESCONHECIDA, 11: C.DESCONHECIDA},
}


def _ofertas_contadas_a_mao(g: dict) -> list:
    out = []
    for it in g["calculos"]:
        for r in it.get("resultados") or []:
            p = r.get("premio")
            if isinstance(p, (int, float)) and p > 0:
                out.append((int(it["seguradora"]), round(float(p), 2), len(r.get("parcelamentos") or [])))
    return sorted(out)


@pytest.mark.parametrize("nome,i", [(n, i) for n in RAMO for i in (1, 2, 3)])
def test_leitor_re_as_9_gravacoes(nome, i):
    g = _grav(nome, i)
    ramo = RAMO[nome]
    filtrado = _node("process.stdout.write(JSON.stringify(M.filtrar(a.c, a.l)))",
                     {"c": g["calculos"], "l": R.lista_de_calculos(ramo)})
    limpos, sujos = R.separar_itens(filtrado, ramo)
    assert sujos == []
    rodada = L.ler_rodada(limpos, ramo=ramo)
    got = sorted((o.seguradora_codigo, round(o.premio_total, 2), len(o.parcelamentos)) for o in rodada.ofertas)
    assert got == _ofertas_contadas_a_mao(g)
    assert all(o.ramo == ramo and o.franquia_valor in (0.0, None) and o.franquia_tipo is None for o in rodada.ofertas)
    recusas = {r.seguradora_codigo: r.familia for r in rodada.respostas if r.familia != C.OFERTA}
    assert recusas == _FAMILIAS_ESPERADAS[(nome, i)]
    if i < 3:   # recentes: as coberturas de RE ecoadas (a Básica e a assistência em TEXTO) chegam na oferta
        for o in rodada.ofertas:
            cob = dict(o.coberturas)
            assert cob.get("isDanosIncendioRaioExplosao") == g["versao"]["configuracoes"]["isDanosIncendioRaioExplosao"]
            assert not (set(cob) & {"casco", "carroReserva", "isAppMorte", "tipoFranquia"})
        assert any(isinstance(dict(o.coberturas).get("assist24hs"), str) for o in rodada.ofertas)
    # a lista branca do AUTO não serve ao RE (as coberturas de RE sumiriam) — linha de controle
    so_auto = _node("process.stdout.write(JSON.stringify(M.filtrar(a.c, a.l)))",
                    {"c": g["calculos"], "l": R.lista_de_calculos(31)})
    assert not any("isDanosIncendioRaioExplosao" in (r.get("coberturas") or {})
                   for it in so_auto for r in it.get("resultados") or [])


def test_leitor_re_familias_e_motivos_e_o_auto_nao_muda():
    lim = ["636 - Valor de IS da cobertura PERDA OU PAG DE ALUG.,supera o máximo permitido (120.000,00)"]
    assert L.classificar_mensagens(lim, 18) == C.DADO and L.motivo_de_recusa_re(lim) == "limite_de_cobertura"
    assert L.classificar_mensagens(["Atividade declinada"], 18) == C.ACEITACAO
    assert L.classificar_mensagens(["A comissão deve possuir um valor entre 10% e 30%"], 18) == C.COMERCIAL
    assert L.classificar_mensagens(["Usuário sem autorização para cotar construção madeira"], 2) == C.ACEITACAO
    agua = ["Danos por água acima do limite máximo"]
    assert L.classificar_mensagens(agua, 16) == C.DADO
    assert L.classificar_mensagens(agua, 31) == C.ACEITACAO          # o auto continua com a regra dele


# ======================================================================================================================
# 6. A ATIVIDADE do empresarial (D-129C-04) — casa ou sai listada, nunca um código errado
# ======================================================================================================================
def _amostra(termo: str) -> list:
    """📊 as opções REAIS de `getOptionsBySegFull` medidas em 11/10 (formulario_empresarial.json)."""
    a = _form("empresarial")["atividade_por_seguradora"]["amostra_medida_11_10"][termo]
    return [{"seguradora": s["seguradora"], "KeyValue": [{"Key": k, "Value": v, "Description": None}
                                                          for k, v in s["amostra"]]} for s in a]


def _escolha_humana(g: dict) -> dict:
    return {int(it["seguradora"]): it["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]["Key"]
            for it in g["versao"]["calculos"] if it.get("valoresAjusteSeguradora")}


def test_atividade_escritorio_2o_andar_bate_com_a_escolha_humana():
    g = _grav("empresarial", 2)
    humano = _escolha_humana(g)                       # 📊 9 seguradoras, escolhidas por uma pessoa no Agger
    esc, fora = A.escolher_atividades([{"termo": "escritorio", "opcoes": _amostra("escritorio")}], "escritório",
                                      pavimento="2", seguradoras=humano)
    iguais = {s for s in esc if esc[s]["Key"] == humano[s]}
    assert iguais == set(humano) - {8}                # 8 de 9 iguais à pessoa
    assert fora == {8: "nenhum"}                      # Porto: as 2 opções medidas são "informática/publicidade" → SAI
    assert all(esc[s]["Key"] == humano[s] for s in esc)   # nenhum código diferente do humano foi aceito
    # térreo muda o código das que têm um por andar (Allianz 90100, Yelum 102) — e só delas
    terreo, _ = A.escolher_atividades([{"termo": "escritorio", "opcoes": _amostra("escritorio")}], "escritório",
                                      pavimento="0", seguradoras=humano)
    assert {s for s in terreo if terreo[s]["Key"] != esc[s]["Key"]} == {5, 12}
    # sem pavimento, um código "por andar" não é inequívoco → Allianz e Yelum saem
    _s, sem_andar = A.escolher_atividades([{"termo": "escritorio", "opcoes": _amostra("escritorio")}], "escritório",
                                          seguradoras=humano)
    assert {5, 12} <= set(sem_andar)


def test_atividade_padaria_casa_e_a_ambigua_sai_listada():
    esc, fora = A.escolher_atividades([{"termo": "padaria", "opcoes": _amostra("padaria")}], "padaria")
    assert fora == {3: "ambiguo"}                     # Mapfre: "PADARIA - CONFEITARIAS" × "PADARIA - PADARIA"
    assert esc[35]["Key"] == "COM,10365"              # Axa: "Padarias" (exato) e não "…Produtos"
    assert esc[1]["Key"] == "4,1.1.814"               # Bradesco: o depósito sai (o pedido não diz depósito)
    assert esc[13]["Key"] == "420-11,01"
    assert len(esc) == 14
    # e um termo que nenhuma seguradora tem → todas saem
    esc2, fora2 = A.escolher_atividades([{"termo": "x", "opcoes": []}], "fábrica de fogos de artifício",
                                        seguradoras=[1, 8])
    assert esc2 == {} and fora2 == {1: "nenhum", 8: "nenhum"}


def _defeitos_de_atividade(escolhidas: dict, esperado: dict) -> list:
    return [s for s, kv in escolhidas.items() if esperado.get(s) != kv["Key"]]


def test_mutacao_atividade_errada_aceita_fica_vermelha(monkeypatch):
    g = _grav("empresarial", 1)
    humano = _escolha_humana(g)
    opcoes = _opcoes_estetica(g)
    esc, fora = A.escolher_atividades(opcoes, "clínica de estética", pavimento="0", seguradoras=humano)
    assert _defeitos_de_atividade(esc, humano) == [] and fora == {}
    # MUTAÇÃO: um escolhedor que aceita o 1º candidato (a isca "ESTÉTICA AUTOMOTIVA" vem primeiro) → vermelho
    monkeypatch.setattr(A, "escolher", lambda ops, *a, **k: (ops[0], "mutante") if ops else (None, "nenhum"))
    mut, _ = A.escolher_atividades(opcoes, "clínica de estética", pavimento="0", seguradoras=humano)
    assert len(_defeitos_de_atividade(mut, humano)) == len(humano)


def _opcoes_estetica(g: dict) -> list:
    """As respostas de `getOptionsBySegFull` para os termos da estética: por seguradora, uma ISCA ('ESTÉTICA
    AUTOMOTIVA', primeira) + a opção que a pessoa escolheu no negócio gravado (📊 gravacao_empresarial_1)."""
    blocos = []
    for it in g["versao"]["calculos"]:
        kv = it["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]
        blocos.append({"seguradora": int(it["seguradora"]), "KeyValue": [
            {"Key": f"ISCA-{it['seguradora']}", "Value": "ESTETICA AUTOMOTIVA / LAVA-RAPIDO", "Description": None},
            {"Key": kv["Key"], "Value": kv["Value"], "Description": kv.get("Description")}]})
    return [{"termo": t, "opcoes": blocos} for t in A.termos_de_busca("clínica de estética")]


# ======================================================================================================================
# 7. O TESTE DO FIO — Chromium REAL + Agger DUBLÊ com as gravações de RE
# ======================================================================================================================
def _dubleRE(ramo: int, g: dict, opcoes_por_termo: dict):
    from dubles.agger_duble import AggerDuble

    class AggerDubleRE(AggerDuble):
        def __init__(self):
            super().__init__()
            self.config = _config_da_gravacao(g, ramo)
            self.resposta = g["calculos"]
            self.opcoes = {A.normalizar(k): v for k, v in opcoes_por_termo.items()}
            self.termos_pedidos = []

        def _versao(self, ref, neg, versao, cid, usuario, calculos, criada_ha_h=0.0, cot=None):
            v = super()._versao(ref, neg, versao, cid, usuario, calculos, criada_ha_h, cot)
            v["ramo"] = (cot or {}).get("ramo", ramo)
            v.pop("automoveis", None)
            return v

        def _rodadas_da_versao(self, versao):
            # o Agger devolve só as seguradoras que foram calculadas (as que estão na versão)
            for neg in self.negocios.values():
                for v in neg["versoes"]:
                    if v["versao"] == versao:
                        enviadas = {int(c["seguradora"]) for c in v["calculos"]}
                        return [[it for it in self.resposta if int(it["seguradora"]) in enviadas]]
            return [self.resposta]

        async def _pdocs(self, req, caminho):
            if caminho == "/calculo/getOptionsBySegFull":
                if not (req.headers.get("Authorization") or "").startswith("TOKEN-PDOCS-"):
                    return self._json(req, {"message": "sem token"}, 401)
                termo = A.normalizar(req.query.get("filterText"))
                self.termos_pedidos.append(termo)
                blocos = copy.deepcopy(self.opcoes.get(termo, []))
                for b in blocos:          # o Agger real devolve segredo onde pode: a lista branca tem de cortar
                    b["loginWs"] = "SEGREDO-ATIV"
                return self._json(req, blocos)
            return await super()._pdocs(req, caminho)

    return AggerDubleRE()


async def _com_agger_re(duble, fn):
    pw_api = pytest.importorskip("playwright.async_api")
    from portal_worker.multicalculo import agger_sessao as S
    d = await duble.iniciar()
    try:
        async with pw_api.async_playwright() as pw:
            nav = await pw.chromium.launch(headless=True)
            try:
                return await fn(d, S.Sessoes(nav, url_base=d.base))
            finally:
                await nav.close()
    finally:
        await d.parar()


def _conta():
    from dubles.agger_duble import EMAIL
    return {"id": "conta-robo-re", "username": EMAIL, "robo_estado": "teste"}


def defeitos_do_corpo_re(cot: dict, ramo: int, comissao: float, recentes: list, config: list) -> list:
    """O corpo montado × a FORMA das gravações recentes do ramo. Vazio = bate."""
    d = []
    topo = set().union(*(set(g["versao"]) for g in recentes))
    if set(cot) - topo:
        d.append(f"topo fora da forma gravada: {sorted(set(cot) - topo)}")
    for k in ("automoveis", "tpCobertura", "CI"):
        if k in cot:
            d.append(f"chave de auto no RE: {k}")
    if cot.get("ramo") != ramo:
        d.append("ramo")
    for k in ("vigenciaIni", "vigenciaFim"):
        if not VIGENCIA.match(str(cot.get(k) or "")):
            d.append(f"vigência fora do formato gravado: {k}")
    cfg_grav = set().union(*({k for k in g["versao"]["configuracoes"] if not k.endswith(("Txt", "TxtRS"))}
                             for g in recentes))
    cfg = cot.get("configuracoes") or {}
    if set(cfg) - cfg_grav:
        d.append(f"configuracoes fora da forma gravada: {sorted(set(cfg) - cfg_grav)}")
    precisa = set(P.CHAVES_DE_COBERTURA_RE[ramo]) | {
        C.chave_no_corpo(ramo, "risco", n) for n, _c, o in C.CAMPOS_DO_PEDIDO_RE[ramo]["risco"] if o} - {None}
    if precisa - set(cfg):
        d.append(f"configuracoes sem: {sorted(precisa - set(cfg))}")
    g1 = recentes[0]["versao"]["configuracoes"]
    for k, v in cfg.items():
        gv = g1.get(k)
        if v is None or gv is None or str(gv).startswith("<"):
            continue
        num = (int, float)
        if (isinstance(v, bool) != isinstance(gv, bool)) or (isinstance(gv, str) != isinstance(v, str)) or (
                isinstance(gv, num) and not isinstance(v, num)):
            d.append(f"tipo de configuracoes.{k}")
    chaves_cfg = set().union(*(set(c) for c in config))
    item_grav = set().union(*(set(i) for g in recentes for i in g["versao"]["calculos"]))
    cobertura = set(P.CHAVES_DE_COBERTURA) | {k for ks in P.CHAVES_DE_COBERTURA_RE.values() for k in ks}
    for it in cot.get("calculos") or []:
        if set(it) & cobertura:
            d.append(f"cobertura dentro do item {it.get('seguradora')}: {sorted(set(it) & cobertura)}")
        if (set(it) - chaves_cfg) - item_grav:
            d.append(f"chave inventada no item: {sorted((set(it) - chaves_cfg) - item_grav)}")
        if it.get("percComissao") != comissao:
            d.append(f"comissão fora do item {it.get('seguradora')}")
        tem_ativ = bool((it.get("valoresAjusteSeguradora") or {}).get("imovelAtividadeProfissionalLocal"))
        if tem_ativ != (ramo == 18):
            d.append(f"atividade no item {it.get('seguradora')}")
    if "percComissao" in cfg:
        d.append("comissão em configuracoes")
    return d


@pytest.mark.parametrize("nome", list(RAMO))
def test_o_fio_por_ramo_do_pedido_as_ofertas(nome, monkeypatch):
    from dubles.agger_duble import SENHA
    import playwright  # noqa: F401  (pula se não houver)
    ramo = RAMO[nome]
    g = _grav(nome, 1)
    recentes = [g, _grav(nome, 2)]
    if ramo == 18:
        ped = pedido_re(18, atividade="clínica de estética", pavimento="0")
        opcoes = {o["termo"]: o["opcoes"] for o in _opcoes_estetica(g)}
    else:
        ped = pedido_re(ramo)
        opcoes = {}
    duble = _dubleRE(ramo, g, opcoes)
    retornos = []
    pw_api = pytest.importorskip("playwright.async_api")
    original = pw_api.Page.evaluate

    async def espia(pagina, *a, **k):
        r = await original(pagina, *a, **k)
        retornos.append(json.dumps(r, ensure_ascii=False, default=str))
        return r
    monkeypatch.setattr(pw_api.Page, "evaluate", espia)
    basica = ped["risco"]["valor_basica"]
    comissao = ped["comissao_desconto"]["comissao_percentual"]

    async def corpo(d, sessoes):
        sessao = await sessoes.obter(_conta(), senha=SENHA, negocios_do_robo=set())
        disp = await R.disparar(sessao, ped, P.coberturas_re(ramo, "padrao", basica))
        assert disp.ramo == ramo and disp.versao == 1 and disp.sem_atividade == ()
        post = d.posts_calcular[-1]
        cot = post["cotacao"]
        assert defeitos_do_corpo_re(cot, ramo, comissao, recentes, d.config) == []
        assert {i["seguradora"] for i in cot["calculos"]} == _esperadas(g, ramo)
        assert all(i.get("loginWs", "").startswith("SEGREDO-") for i in cot["calculos"])   # credencial vai ao Agger
        assert cot["configuracoes"][P.CHAVE_DA_BASICA] == basica
        assert cot["configuracoes"]["imovelCep"] == "88000000" and cot["segurado"]["cpfCnpj"] in (CNPJ, CPF)
        if ramo == 18:
            humano = _escolha_humana(g)
            got = {i["seguradora"]: i["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]["Key"]
                   for i in cot["calculos"]}
            assert got == {s: humano[s] for s in got} and set(got) == _esperadas(g, ramo)
            assert not any(k.startswith("ISCA") for k in got.values())
            assert set(d.termos_pedidos) == set(A.termos_de_busca("clínica de estética"))
        if ramo == 16:
            assert cot["renovacao"] is True and cot["seguradoraAnteriorId"] and cot["sinistrosAnterior"] == "0"
            assert cot["configuracoes"]["sisProtecaoIncendRoubo"] == [1, 7] and cot["segurado"]["tipoPessoa"] == "J"
        # a "mais em conta": versão 2 do MESMO negócio, só as essenciais e assistência Básica
        eco = await R.disparar(sessao, ped, P.coberturas_re(ramo, "economica", basica), negocio_ref=disp.negocio_ref)
        assert (eco.negocio_ref, eco.versao) == (disp.negocio_ref, 2)
        ceco = d.posts_calcular[-1]["cotacao"]
        assert ceco["configuracoes"]["assist24hs"] == 1
        assert defeitos_do_corpo_re(ceco, ramo, comissao, recentes, d.config) == []
        # acompanhar → o leitor REAL → as ofertas = a contagem à mão na fixture
        eventos = []

        async def ao_evento(e):
            eventos.append(e)
        final = await R.acompanhar(sessao, disp, ao_evento=ao_evento, intervalo_s=0.05, quadro_s=0.3, teto_s=60)
        assert final.fechado and final.ramo == ramo
        got = sorted((o.seguradora_codigo, round(o.premio_total, 2), len(o.parcelamentos)) for o in final.ofertas)
        assert got == _ofertas_contadas_a_mao(g)
        assert {e.seguradora_codigo for e in eventos if e.tipo == C.NOVA_OFERTA} == {x[0] for x in got}
        assert all(e.ramo == ramo for e in eventos)
        # recálculo de RE: a assistência muda em `configuracoes`; a comissão (e a atividade) vêm da versão-base
        rec = await R.recalcular(sessao, disp.negocio_ref, versao_base=1, ajuste=C.Ajuste("assistencia", 0))
        rcot = d.posts_calcular[-1]["cotacao"]
        assert rec.ramo == ramo and rcot["configuracoes"]["assist24hs"] == 0
        assert {i["percComissao"] for i in rcot["calculos"]} == {comissao}
        assert rcot["configuracoes"]["isDanosEletricos"] == cot["configuracoes"]["isDanosEletricos"]  # da padrão
        if ramo == 18:
            assert all(i["valoresAjusteSeguradora"] == next(
                c for c in cot["calculos"] if c["seguradora"] == i["seguradora"])["valoresAjusteSeguradora"]
                for i in rcot["calculos"])
        n = len(d.posts_calcular)
        with pytest.raises(R.DisparoRecusado):          # ajuste de auto num negócio de RE: nada sai
            await R.recalcular(sessao, disp.negocio_ref, versao_base=1, ajuste=C.Ajuste("franquia", 2))
        assert len(d.posts_calcular) == n
        await sessoes.fechar(_conta()["id"])
        return final

    final = asyncio.run(_com_agger_re(duble, corpo))
    assert retornos and [s for s in SEGREDOS for r in retornos if s in r] == []
    assert [s for s in SEGREDOS if s in repr(final)] == []


def test_o_fio_empresarial_escritorio_porto_sai_e_e_narrada(monkeypatch):
    from dubles.agger_duble import SENHA
    pytest.importorskip("playwright.async_api")
    g = _grav("empresarial", 2)
    humano = _escolha_humana(g)
    duble = _dubleRE(18, g, {"escritorio": _amostra("escritorio")})
    ped = pedido_re(18)       # escritório, 2º andar em diante

    async def corpo(d, sessoes):
        sessao = await sessoes.obter(_conta(), senha=SENHA, negocios_do_robo=set())
        disp = await R.disparar(sessao, ped, P.coberturas_re(18, "padrao", ped["risco"]["valor_basica"]))
        cot = d.posts_calcular[-1]["cotacao"]
        got = {i["seguradora"]: i["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]["Key"]
               for i in cot["calculos"]}
        assert got == {s: humano[s] for s in humano if s != 8}       # 8 de 9 iguais à pessoa; a Porto fora
        assert [c for c, _n in disp.sem_atividade] == [8]
        eventos = []

        async def ao_evento(e):
            eventos.append(e)
        final = await R.acompanhar(sessao, disp, ao_evento=ao_evento, intervalo_s=0.05, teto_s=60)
        sem = [e for e in eventos if e.tipo == C.SEM_ATIVIDADE_COMPATIVEL]
        # §9.3: a família era DADO; o conserto 129-C a fez a MESMA da comparação (o nome do tipo)
        assert [(e.seguradora_codigo, e.familia) for e in sem] == [(8, C.SEM_ATIVIDADE)] and eventos[0] is sem[0]
        assert 8 not in {o.seguradora_codigo for o in final.ofertas}
        # MUTAÇÃO comissão fora do item / cobertura no item → a régua da forma fica vermelha
        mut = copy.deepcopy(cot)
        for i in mut["calculos"]:
            i.pop("percComissao")
        mut["configuracoes"]["percComissao"] = 20
        assert any("comissão" in x for x in defeitos_do_corpo_re(mut, 18, 20, [g, _grav("empresarial", 1)], d.config))
        mut2 = copy.deepcopy(cot)
        mut2["calculos"][0]["vidros"] = 10000
        assert any("cobertura dentro do item" in x
                   for x in defeitos_do_corpo_re(mut2, 18, 20, [g, _grav("empresarial", 1)], d.config))
        mut3 = copy.deepcopy(cot)
        mut3["calculos"][0].pop("valoresAjusteSeguradora")
        assert any("atividade" in x for x in defeitos_do_corpo_re(mut3, 18, 20, [g, _grav("empresarial", 1)], d.config))
        # nenhuma atividade casa → recusado ANTES do POST
        n = len(d.posts_calcular)
        with pytest.raises(R.DisparoRecusado, match="atividade"):
            await R.disparar(sessao, pedido_re(18, atividade="fábrica de fogos de artifício"),
                             P.coberturas_re(18, "padrao", 800_000))
        assert len(d.posts_calcular) == n
        # sem comissão → recusado ANTES de qualquer rede (D-129C-05)
        sem_com = pedido_re(18)
        sem_com["comissao_desconto"] = {}
        with pytest.raises(R.DisparoRecusado, match="comissao"):
            await R.disparar(sessao, sem_com, {})
        assert len(d.posts_calcular) == n
        await sessoes.fechar(_conta()["id"])

    asyncio.run(_com_agger_re(duble, corpo))
