# -*- coding: utf-8 -*-
"""SPEC-129-D V1 — o lado do PORTAL da Vida Individual (ramo 91): contrato · presets · montador · robô · leitor · sessão.

A verdade do corpo é a GRAVAÇÃO (📊 BLOCO 0 M6, entrada 3, 16/10/2026 — `tests/fixtures/agger_ramos/vida_*.json`):
o corpo do `calcularV2` de vida, o formulário (códigos do JS do app) e o resultado (7 de 7 "instabilidade").

O que cada bloco prova — sempre pelo MOTOR real (CLAUDE.md §9.4): o `montador.js` e o `JS_PREPARAR`/`JS_PROFISSOES` do
robô rodam em node (a MESMA fonte que a página carrega), com o Agger dublado só na BORDA (o `fetch`):
  (1) o corpo montado para o pedido de teste = a FORMA gravada (chaves e tipos; credenciais à parte)
  (2) "mais em conta" manda Morte acidental = 0 e IPA = 0 EXPLÍCITOS (📊 a tela copia a Morte para as duas)
  (3) profissão por seguradora: só IGUALDADE do texto normalizado; Bradesco (sem bloco) entra; Mapfre (0 opções) sai
      listada; nenhuma → `profissao_sem_casamento`
  (4) comissão de vida 0 → `comissao_de_vida_nao_configurada`, nunca um número inventado
  (5) o leitor transforma a recusa gravada em recusa POR seguradora, nunca oferta
  (6) auto e RE byte a byte: os testes da 129-B/129-C (rodados à parte, um por vez) + o despacho por ramo aqui
  (7) o prazo da licença: uma leitura que nunca volta não prende o login

⛔ Tudo sintético: nenhum login, nenhum cálculo, nenhum banco; CPF de exemplo (dígitos válidos, de ninguém).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec129d_portal_vida.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import agger_sessao as S  # noqa: E402
from portal_worker.multicalculo import contrato as C  # noqa: E402
from portal_worker.multicalculo import leitor_agger as L  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402

FIX = BACKEND / "tests" / "fixtures" / "agger_ramos"
MONTADOR = (BACKEND / "portal_worker" / "multicalculo" / "montador.js").read_text(encoding="utf-8")
GRAVADO = json.loads((FIX / "vida_calcularV2_corpo.json").read_text(encoding="utf-8"))
FORMULARIO = json.loads((FIX / "vida_formulario.json").read_text(encoding="utf-8"))
RESULTADO = json.loads((FIX / "vida_resultado.json").read_text(encoding="utf-8"))
COT_GRAVADA = GRAVADO["corpo"]["cotacao"]
ITEM_GRAVADO = {it["seguradora"]: it for it in COT_GRAVADA["calculos"]}
#: 📊 a busca de profissão gravada (`getOptionsBySegFull?executionType=9&filterText=Analista de sistemas`): 13 blocos
BLOCOS = [{"seguradora": b["seguradora"], "KeyValue": b["opcoes"]} for b in FORMULARIO["profissao"]["blocos"]]

CPF = "52998224725"          # CPF de exemplo da 129-B (dígitos válidos), de ninguém
CEP = "88000000"
ENDERECO_DO_CEP = {"logradouro": "Rua Ficticia", "cidade": "Cidade Ficticia", "bairro": "Centro", "uf": "SC"}
AGORA = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)

#: as chaves que o MONTADOR põe no item (o resto é a config da seguradora): tiradas do item gravado para fazer a config
_DO_MONTADOR = ("percComissao", "percDesconto", "idIntegracaoCfg", "idIntegracaoCfgSeg", "valoresAjusteSeguradora",
                "percAgenciamento", "libertyDescontoRegional", "nome")
#: as chaves que a config tem e a TELA não copia para o item (📊 o item gravado não as tem; a config da conta tem
#: percComissaoVida/percDescontoVida — `vida_formulario.json` seguradoras.na_conta)
_SO_DA_CONFIG = {"id": "cfg-id", "usuario": "usuario-cfg", "percComissaoVida": 0, "percDescontoVida": 0,
                 "percComissaoEmpres": 0, "percComissaoResid": 0, "percDescontoEmpres": 0, "percDescontoResid": 0}


def config_da_conta(**por_seguradora) -> list:
    """`GET api-prod/calculo/seguradoras` sintético: cada item gravado menos o que o montador põe, mais as chaves só da
    config; + Mapfre (3, de vida, sem profissão na busca) e duas que NÃO são de vida (Azul 10, Sura 24)."""
    cfg = []
    for cod, it in ITEM_GRAVADO.items():
        c = {k: v for k, v in it.items() if k not in _DO_MONTADOR}
        if cod != 12:                       # 📊 só na Yelum a chave vem no MEIO do item (é da config); nas outras, no fim
            c.pop("libertyCodigoEstabelecimento", None)
        c.update(_SO_DA_CONFIG)
        c["percComissao"] = 15             # a comissão do AUTO na config: a vida NUNCA a usa
        c["percDesconto"] = 3
        if cod == 4:
            c.pop("percAgenciamentoVida", None)    # 📊 a HDI não tem a chave
        cfg.append(c)
    mapfre = {k: v for k, v in ITEM_GRAVADO[1].items() if k not in _DO_MONTADOR and not k.startswith("bradesco")}
    mapfre.update(_SO_DA_CONFIG, seguradora=3, nomeSeguradora="Mapfre", percComissao=15, percDesconto=3)
    mapfre.pop("libertyCodigoEstabelecimento", None)
    cfg.append(mapfre)
    for cod, nome in ((10, "Azul"), (24, "Sura")):
        cfg.append({"seguradora": cod, "nomeSeguradora": nome, "ativo": True, "credenciaisValidas": True,
                    "idIntegracao": f"cfg-{cod}", **_SO_DA_CONFIG})
    for c in cfg:
        c.update(por_seguradora.get(str(c["seguradora"]), {}))
    return cfg


def pedido_vida(**troca) -> dict:
    """O dict que a porta (V2, `PedidoDeCalculo.para_dict`) entrega ao robô — os dados de TESTE da gravação."""
    p = {"ramo": 91,
         "segurado": {"cpf": CPF, "nome": "PESSOA SINTETICA", "data_nascimento": "1985-05-10", "sexo": "Masculino",
                      "estado_civil": "Casado(a)", "cep": CEP, "profissao_texto": "Analista de sistemas"},
         "vida": {"capital_morte": 100000.0, "fumante": False, "renda_mensal": 8000.0, "esporte_radical": False,
                  "vigencia_inicio": "2026-10-17", "origem": "cotacao"},
         "comissao_desconto": {"comissao_percentual": 10.0},
         "seguradoras": [], "assumidos": [], "coberturas": {}, "pacotes": {}}
    for g, v in troca.items():
        p[g] = v if not isinstance(v, dict) else {**p.get(g, {}), **v}
    return p


# ======================================================================================================================
# node — a MESMA fonte que a página carrega (montador.js + as funções JS do robô), o Agger só na borda (`fetch`)
# ======================================================================================================================
def _sem_node():
    if not shutil.which("node"):
        pytest.skip("node ausente")


def _node(corpo_js: str, entrada) -> object:
    _sem_node()
    js = "globalThis.window = {};\n" + MONTADOR + "\nconst M = window.__abM;\nconst a = JSON.parse(require('fs')" \
         ".readFileSync(0, 'utf8'));\n" + corpo_js
    r = subprocess.run(["node", "-e", js], input=json.dumps(entrada).encode("utf-8"), capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:800]
    return json.loads(r.stdout)


_PAGINA = r"""
globalThis.fetch = async (u, o) => {
  for (const [pedaco, status, corpo] of a.rotas) if (String(u).includes(pedaco)) {
    a.chamadas.push(String(u));
    return {status, ok: status < 300, text: async () => JSON.stringify(corpo), json: async () => corpo};
  }
  return {status: 404, ok: false, text: async () => 'null', json: async () => null};
};
a.chamadas = [];
const f = (0, eval)(a.fonte);
(async () => {
  const r = await f(a.args);
  process.stdout.write(JSON.stringify({r, corpo: window.__abCorpo === undefined ? null : window.__abCorpo,
                                       chamadas: a.chamadas}));
})().catch(e => { console.error(String(e && e.stack || e)); process.exit(3); });
"""


def rotas(cfg=None, blocos=None) -> list:
    return [["/calculo/seguradoras", 200, cfg if cfg is not None else config_da_conta()],
            ["/calculo/cep", 200, ENDERECO_DO_CEP],
            ["getOptionsBySegFull?executionType=9", 200, BLOCOS if blocos is None else blocos]]


class SessaoNode:
    """A `Sessao` do robô com a página trocada por node: `avaliar` roda a fonte JS REAL; o POST não sai (conta)."""

    bases = {"api": "https://api.agger.invalid", "pdocs": "https://pdocs.agger.invalid"}

    def __init__(self, rotas_):
        self.rotas = rotas_
        self.corpo = None
        self.enviado = None
        self.escritas = 0
        self.chamadas: list = []

    async def garantir_token(self):
        return None

    def token(self, k):
        return f"TOKEN-{k}"

    def contagem_de_escritas(self):
        return {"calcularV2": self.escritas}

    def registrar_negocio(self, ref):
        return None

    async def avaliar(self, fonte, args):
        if fonte == R.JS_ENVIAR:
            if self.corpo is None:
                return {"fase": "antes", "erro": "sem_corpo"}
            self.enviado, self.corpo = self.corpo, None
            self.escritas += 1
            return {"fase": "post", "status": 201, "resposta": {"idIntegracao": "neg-vida-1", "versao": 1},
                    "mensagem": None}
        out = _node(_PAGINA, {"fonte": fonte, "args": args, "rotas": self.rotas})
        self.chamadas += out["chamadas"]
        if fonte == R.JS_PREPARAR:
            self.corpo = out["corpo"]
        return out["r"]


def disparar(pedido, coberturas, rotas_=None):
    s = SessaoNode(rotas_ if rotas_ is not None else rotas())
    try:
        d = asyncio.run(R.disparar(s, pedido, coberturas))
    except R.DisparoRecusado as e:
        return s, e
    return s, d


def _tipo(v) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "numero"
    if v is None:
        return "nulo"
    if isinstance(v, dict):
        return "obj:" + ",".join(sorted(f"{k}={_tipo(x)}" for k, x in v.items()))
    return type(v).__name__


# ======================================================================================================================
# 0. O CONTRATO — o 91, os nomes do app e os códigos lidos da TELA
# ======================================================================================================================
def test_0_o_ramo_91_e_o_catalogo_e_o_do_app():
    assert C.RAMO_VIDA == 91 and C.RAMO_VIDA not in C.RAMOS_RE and C.RAMO_VIDA in C.RAMOS
    assert C.NOME_DO_RAMO[91] == "vida"                     # 📊 a rota do formulário gravado: /cotacao/vida/formulario
    assert FORMULARIO["rota"] == "/cotacao/vida/formulario" and GRAVADO["ramo"] == 91 == COT_GRAVADA["ramo"]
    nomes = {g: tuple(c[0] for c in cs) for g, cs in C.CAMPOS_DO_PEDIDO_VIDA.items()}
    assert nomes == {
        "segurado": ("cpf", "nome", "data_nascimento", "sexo", "estado_civil", "cep", "profissao_texto",
                     "profissao_codigo_infocap"),
        "vida": ("capital_morte", "coberturas_extras", "fumante", "renda_mensal", "esporte_radical",
                 "vigencia_inicio", "origem"),
        "comissao_desconto": ("comissao_percentual", "agenciamento_percentual")}
    assert C.campos_do_pedido(91) is C.CAMPOS_DO_PEDIDO_VIDA


def test_0_os_codigos_sao_os_do_js_da_tela():
    js = FORMULARIO["codigos_do_js"]
    assert set(C.CODIGOS_MEDIDOS_VIDA["sexo"].values()) == set(js["sexo"])
    assert {str(v) for v in C.CODIGOS_MEDIDOS_VIDA["estado_civil"].values()} == set(js["estadoCivil"])
    assert {str(v) for v in P.FUNERAL_VIDA.values()} == set(js["assistFuneral"])
    # cada rótulo da tela casa com o seu código (nenhum por ordem)
    for cod, rotulo in js["estadoCivil"].items():
        assert C.codigo_de_vida("estado_civil", rotulo) == int(cod), rotulo
    for cod, rotulo in js["sexo"].items():
        assert C.codigo_de_vida("sexo", rotulo) == cod


def test_0_o_validador_nunca_presume_saude_e_diz_so_nomes():
    assert C.problemas_do_pedido_vida(pedido_vida()) == ()
    p = pedido_vida(vida={"fumante": None, "renda_mensal": None, "esporte_radical": None})
    assert set(C.problemas_do_pedido_vida(p)) >= {"vida.fumante", "vida.renda_mensal", "vida.esporte_radical"}
    assert "vida.fumante:sim_nao" in C.problemas_do_pedido_vida(pedido_vida(vida={"fumante": "nao"}))
    assert "vida.coberturas_extras.carro:desconhecido" in C.problemas_do_pedido_vida(
        pedido_vida(vida={"coberturas_extras": {"carro": 10}}))
    assert "comissao_desconto.comissao_percentual:valor" in C.problemas_do_pedido_vida(
        pedido_vida(comissao_desconto={"comissao_percentual": 0}))
    for problema in C.problemas_do_pedido_vida(pedido_vida(segurado={"cpf": "123"}, vida={"renda_mensal": -1})):
        assert CPF not in problema and "8000" not in problema


# ======================================================================================================================
# 1. O CORPO = A GRAVAÇÃO (o pedido de teste do BLOCO 0, pelo robô e montador REAIS)
# ======================================================================================================================
def test_1_o_corpo_de_vida_tem_a_forma_gravada():
    s, d = disparar(pedido_vida(), P.coberturas_vida(P.PADRAO, 100000))
    assert isinstance(d, R.Disparo), getattr(d, "motivo", d)
    assert d.ramo == 91 and s.escritas == 1
    corpo = s.enviado
    # o envelope: {cotacao, negocio: null, correlationId} — sem corretoraId
    assert set(corpo) == set(GRAVADO["corpo"]) == {"cotacao", "negocio", "correlationId"}
    assert corpo["negocio"] is None and corpo["correlationId"] == corpo["cotacao"]["correlationId"]
    cot = corpo["cotacao"]
    assert set(cot) == set(COT_GRAVADA), set(cot) ^ set(COT_GRAVADA)
    assert (cot["ramo"], cot["tipo"], cot["integracaoInfo"]) == (91, 5, 1)
    assert cot["vigenciaIni"].startswith("2026-10-17T") and cot["correlationId"].startswith(R.PREFIXO_DA_MARCA)
    # o segurado: as MESMAS chaves e tipos; estado civil NÚMERO, sexo "M", renda número, sem profissão
    seg = cot["segurado"]
    assert {k: _tipo(v) for k, v in seg.items()} == {k: _tipo(v) for k, v in COT_GRAVADA["segurado"].items()}
    assert (seg["estadoCivil"], seg["sexo"], seg["rendaMensal"], seg["cpfCnpj"], seg["cep"]) == (2, "M", 8000, CPF, CEP)
    assert seg["dataNasc"].startswith("1985-05-10T") and "profissao" not in json.dumps(seg)
    assert {seg[k] for k in ENDERECO_DO_CEP} == set(ENDERECO_DO_CEP.values())      # o CEP completou o endereço
    # as configurações: as MESMAS chaves e tipos (com os restos de RE nulos)
    cfg = cot["configuracoes"]
    assert {k: _tipo(v) for k, v in cfg.items()} == {k: _tipo(v) for k, v in COT_GRAVADA["configuracoes"].items()}
    assert (cfg["fumante"], cfg["praticaEsporteRadical"], cfg["isAppMorte"]) == (False, 0, 100000)
    assert cfg["funeral"] == {"tipo": 0, "valor": None} and cfg["DIT"] == {"qtdDiarias": None, "valor": 0}
    # os itens: as seguradoras com profissão IGUAL (HDI, Porto) + a que não pede (Bradesco); cada item com as
    # MESMAS chaves e tipos do item gravado da mesma seguradora
    por = {it["seguradora"]: it for it in cot["calculos"]}
    assert sorted(por) == [1, 4, 8]
    for cod, it in por.items():
        grav = ITEM_GRAVADO[cod]
        assert set(it) == set(grav), (cod, set(it) ^ set(grav))
        assert {k: _tipo(v) for k, v in it.items()} == {k: _tipo(v) for k, v in grav.items()}, cod
        assert (it["percComissao"], it["percDesconto"], it["percAgenciamento"]) == (10, 0, 0), cod
        assert it["libertyDescontoRegional"] == 1 and it["idIntegracaoCfg"] == it["idIntegracao"]
        for k in _SO_DA_CONFIG:
            assert k not in it, (cod, k)
    assert por[4]["valoresAjusteSeguradora"] == ITEM_GRAVADO[4]["valoresAjusteSeguradora"]      # HDI 10183
    assert por[8]["valoresAjusteSeguradora"] == ITEM_GRAVADO[8]["valoresAjusteSeguradora"]      # Porto 3023
    assert "valoresAjusteSeguradora" not in por[1]                                               # Bradesco
    # quem saiu é LISTADO (nunca some calado): Mapfre sem opção + as 4 cuja única opção é OUTRA profissão
    assert {(c, m) for c, _n, m in d.fora_da_vida} == {(3, "profissao"), (5, "profissao"), (7, "profissao"),
                                                       (11, "profissao"), (12, "profissao")}
    # o robô só LEU (seguradoras, cep, profissão) e não chamou nada fora disso
    assert all(any(p in u for p in ("/calculo/seguradoras", "/calculo/cep", "getOptionsBySegFull?executionType=9"))
               for u in s.chamadas)


def test_1_o_pedido_da_porta_real_chega_ao_corpo(monkeypatch):
    """A costura V2 → V1: o `PedidoDeCalculo` de vida do APP (`para_dict`) é o que o robô aceita, sem tradução extra."""
    monkeypatch.setenv("MULTICALCULO_VIDA_LIGADO", "1")
    from app.services.multicalculo import pedido as PED
    dados = {"segurado": {k: v for k, v in pedido_vida()["segurado"].items()},
             "vida": {**pedido_vida()["vida"], "renda_mensal": "8.000,00"},
             "comissao_desconto": {"comissao_percentual": 10}}
    claro = PED.PedidoDeCalculo.de_dict(dados, ramo=91).para_dict()
    assert C.problemas_do_pedido_vida(claro) == ()
    base = R.cotacao_do_pedido(claro, coberturas=PED.coberturas_de_vida_da_opcao("padrao", 100000.0), agora=AGORA)
    assert base["cotacao"]["segurado"]["sexo"] == "M" and base["cotacao"]["segurado"]["estadoCivil"] == 2
    assert base["cotacao"]["segurado"]["rendaMensal"] == 8000 and base["comissao"] == 10
    # um só lugar para as coberturas por opção: o preset do portal e a função do app dizem o mesmo
    for opcao in (P.PADRAO, P.ECONOMICA, P.ANTERIOR):
        extras = {"isAppInvalidez": 50000.0, "funeral": 2.0}
        assert P.coberturas_vida(opcao, 200000, extras) == PED.coberturas_de_vida_da_opcao(opcao, 200000, extras)


def test_1_auto_e_re_seguem_o_seu_caminho():
    """O 91 ganhou o SEU caminho: auto e RE não passam por ele (o byte a byte é dos testes da 129-B/129-C)."""
    assert R.lista_de_calculos(31) == R.LISTA_CALCULOS and R.lista_de_calculos(16) == R.LISTA_CALCULOS_RE
    assert R.lista_de_calculos(91) == R.LISTA_CALCULOS_VIDA != R.LISTA_CALCULOS_RE
    assert L.endpoint_de_calculos(2) == "cotacao_calculos_re" and L.endpoint_de_calculos(91) == "cotacao_calculos_vida"
    with pytest.raises(ValueError):
        C.Ajuste("comissao", 20, ramo=91)          # o recálculo de vida não existe nesta versão (a porta recusa antes)


# ======================================================================================================================
# 2. "MAIS EM CONTA" = só a Morte; Morte acidental e IPA = 0 EXPLÍCITOS (📊 a tela copia a Morte para as duas)
# ======================================================================================================================
def test_2_mais_em_conta_manda_ma_e_ipa_zero():
    # 📊 o CONTROLE: na gravação a pessoa digitou só a Morte e a TELA mandou MA e IPA = a Morte
    assert COT_GRAVADA["configuracoes"]["isAppMorteAcidental"] == COT_GRAVADA["configuracoes"]["isAppMorte"] == 100000
    assert COT_GRAVADA["configuracoes"]["isAppInvalidez"] == 100000
    s, d = disparar(pedido_vida(), P.coberturas_vida(P.ECONOMICA, 100000, {"isAppInvalidez": 40000}))
    cfg = s.enviado["cotacao"]["configuracoes"]
    assert cfg["isAppMorte"] == 100000
    assert cfg["isAppMorteAcidental"] == 0 and cfg["isAppInvalidez"] == 0
    assert "isAppMorteAcidental" in cfg and "isAppInvalidez" in cfg        # explícitos, nunca ausentes
    assert cfg["funeral"]["tipo"] == 0 and cfg["DIT"]["valor"] == 0 and cfg["isDoencasGravesGrupo"]["valor"] == 0
    # a PADRÃO leva as coberturas do pedido e só elas (nada copiado da Morte)
    pad = R.cotacao_do_pedido(pedido_vida(), coberturas=P.coberturas_vida(P.PADRAO, 100000, {"isAppInvalidez": 40000,
                                                                                             "funeral": 2}),
                              agora=AGORA)["cotacao"]["configuracoes"]
    assert (pad["isAppInvalidez"], pad["isAppMorteAcidental"], pad["funeral"]) == (40000, 0, {"tipo": 2, "valor": None})


def test_2_o_capital_e_o_do_pedido_e_cobertura_desconhecida_e_recusada():
    with pytest.raises(R.DisparoRecusado):
        R.cotacao_do_pedido(pedido_vida(), coberturas={"capital_morte": 1.0}, agora=AGORA)
    with pytest.raises(R.DisparoRecusado):
        R.cotacao_do_pedido(pedido_vida(), coberturas={"capital_morte": 100000, "carroReserva": 2}, agora=AGORA)
    with pytest.raises(R.DisparoRecusado):          # esporte radical "sim": o Agger pede QUAL esporte — nunca um palpite
        R.cotacao_do_pedido(pedido_vida(vida={"esporte_radical": True}), coberturas={"capital_morte": 100000},
                            agora=AGORA)


def test_2_coberturas_da_ficha_so_o_que_casa():
    """📊 os rótulos das garantias de VIND na InfoCap (BLOCO 0 M2): o que não casa fica FORA e volta como sobra."""
    linhas = [("MORTE ACIDENTAL", 250000), ("INVALIDEZ POR ACIDENTE", 100000), ("INVALIDEZ POR DOENÇA", 80000),
              ("INVALIDEZ FUNC PER P/DOEN", 80000), ("ASSISTÊNCIA FUNERAL", 5000), ("CONJUGÊ-MORTE", 50000),
              ("Assistência Funeral Familiar", 7000), ("Diária por Incapacidade Temporária", 150),
              ("Doenças Graves", 30000)]
    extras, sobra = P.coberturas_de_vida_da_ficha_com_sobra(linhas)
    assert extras == {"isAppMorteAcidental": 250000.0, "isAppInvalidez": 100000.0, "isInvalidezDoenca": 80000.0,
                      "funeral": 2, "DIT": 150.0, "isDoencasGravesGrupo": 30000.0}
    assert set(sobra) == {"ASSISTÊNCIA FUNERAL", "CONJUGÊ-MORTE"}       # funeral sem dizer qual · morte de OUTRA pessoa
    assert P.coberturas_de_vida_da_ficha(linhas) == extras
    # dois capitais diferentes para a MESMA cobertura: nenhum é escolhido
    extras, sobra = P.coberturas_de_vida_da_ficha_com_sobra([("INVALIDEZ POR DOENÇA", 80000),
                                                            ("INVALIDEZ FUNC PER P/DOEN", 90000)])
    assert extras == {} and len(sobra) == 2


# ======================================================================================================================
# 3. A PROFISSÃO por seguradora — só IGUALDADE do texto normalizado (D-129D-06 revista pelo ao vivo)
# ======================================================================================================================
def _respostas(blocos=None):
    return [{"termo": "x", "status": 200, "opcoes": BLOCOS if blocos is None else blocos}]


def test_3_profissao_igual_casa_e_a_de_automacao_nao():
    esc, com_bloco, _amb = R.escolher_profissoes(_respostas(), "Analista de sistemas")
    assert esc[4]["Key"] == "10183" and esc[8]["Key"] == "3023"         # HDI exato · Porto em CAIXA ALTA
    for cod in (5, 7, 11, 12, 25):                                     # a única opção é "…de automação": NÃO casa
        assert cod not in esc, cod
    assert 3 in com_bloco and 3 not in esc                              # Mapfre: bloco com 0 opções → sai
    assert 1 not in com_bloco                                           # Bradesco: sem bloco → não pede profissão
    esc2, _cb, _a = R.escolher_profissoes(_respostas(), "  ANALISTA de  sistemas de AUTOMACAO ")
    assert {5, 7, 11, 12, 25} <= set(esc2) and 4 not in esc2 and 8 not in esc2
    # duas opções IGUAIS com códigos diferentes no mesmo bloco: ambígua, nenhuma escolhida
    dup = [{"seguradora": 4, "KeyValue": [{"Key": "1", "Value": "Advogado", "Description": None},
                                          {"Key": "2", "Value": "ADVOGADO", "Description": None}]}]
    esc3, _cb, amb = R.escolher_profissoes(_respostas(dup), "advogado")
    assert esc3 == {} and amb == [4]


def test_3_nenhuma_seguradora_com_a_profissao_e_um_codigo_legivel():
    s, e = disparar(pedido_vida(segurado={"profissao_texto": "Astronauta"}, seguradoras=[3, 4, 5]),
                    P.coberturas_vida(P.PADRAO, 100000))
    assert isinstance(e, R.DisparoRecusado) and e.motivo.startswith("profissao_sem_casamento"), e
    assert s.escritas == 0 and s.enviado is None
    assert {c for c, _n, _m in e.fora_da_vida} == {3, 4, 5}


def test_3_a_busca_que_falhou_nunca_manda_sem_profissao():
    s, e = disparar(pedido_vida(), P.coberturas_vida(P.PADRAO, 100000),
                    rotas_=[r for r in rotas() if "getOptionsBySegFull" not in r[0]])
    assert isinstance(e, R.DisparoRecusado) and s.escritas == 0


def test_3_a_busca_200_sem_nenhum_bloco_nao_manda_nada():
    """Conserto K1 (red team B1): 📊 antes, `200 []` mandava o cálculo às 8 seguradoras, NENHUMA com profissão. Zero
    blocos = a busca não serve (não é "ninguém pede profissão") → `profissao_busca_falhou`, nada sai."""
    for vazia in ([], [{"seguradora": None, "KeyValue": []}]):
        s, e = disparar(pedido_vida(), P.coberturas_vida(P.PADRAO, 100000), rotas(blocos=vazia))
        assert isinstance(e, R.DisparoRecusado) and e.motivo.startswith("profissao_busca_falhou"), (vazia, e)
        assert s.escritas == 0 and s.enviado is None and s.corpo is None
    # o montador também recusa sozinho (a defesa na página): `comBloco` vazio → erro, nenhum cálculo
    r = _node("process.stdout.write(JSON.stringify(M.montarCalculosVida(a.segs, {status: [1, 4, 8], comissao: 10, "
              "profissoes: {}, comBloco: []})))", {"segs": config_da_conta()})
    assert r["erro"] == "profissao_busca_falhou" and r["calculos"] == []
    # CONTROLE (a guarda consegue diferir): blocos de OUTRAS seguradoras e a Bradesco AUSENTE → ela entra sem profissão
    s, d = disparar(pedido_vida(), P.coberturas_vida(P.PADRAO, 100000), rotas(blocos=[b for b in BLOCOS
                                                                                     if b["seguradora"] == 4]))
    assert isinstance(d, R.Disparo), getattr(d, "motivo", d)
    por = {it["seguradora"]: it for it in s.enviado["cotacao"]["calculos"]}
    assert 1 in por and "valoresAjusteSeguradora" not in por[1] and por[4]["valoresAjusteSeguradora"]


def test_3_a_pontuacao_nao_impede_a_igualdade():
    """Conserto K1 (red team P8): o ponto final não é outra profissão; o RESTO continua exigindo igualdade."""
    for texto in ("Analista de sistemas.", "Analista, de sistemas!", "  analista   DE   SISTEMAS; "):
        esc, _cb, _a = R.escolher_profissoes(_respostas(), texto)
        assert esc[4]["Key"] == "10183" and esc[8]["Key"] == "3023", texto
        assert not {5, 7, 11, 12, 25} & set(esc), texto
    esc, _cb, _a = R.escolher_profissoes(_respostas(), "Analista de sistemas de automação.")   # CONTROLE
    assert 4 not in esc and 8 not in esc and {5, 7, 11, 12, 25} <= set(esc)


def test_2_a_mais_em_conta_nunca_leva_ma_nem_ipa_de_quem_chama():
    """Conserto K1 (red team P2): mesmo que quem chama mande MA/IPA (ou qualquer extra, ou outro capital) na "mais em
    conta", ela é SÓ a Morte com o capital do pedido. `coberturas_da_opcao_vida` é a porta única das coberturas
    EXPLÍCITAS de quem chama (a renovação); a padrão/anterior as levam como vieram (CONTROLE)."""
    explicitas = {"capital_morte": 1.0, "isAppMorteAcidental": 100000, "isAppInvalidez": 100000, "funeral": 2}
    assert P.coberturas_vida(P.ECONOMICA, 100000, explicitas) == {"capital_morte": 100000.0}
    eco = P.coberturas_da_opcao_vida(P.ECONOMICA, 100000, explicitas)
    assert eco == {"capital_morte": 100000.0}
    cfg = P.configuracoes_de_vida(eco)
    assert (cfg["isAppMorte"], cfg["isAppMorteAcidental"], cfg["isAppInvalidez"], cfg["funeral"]["tipo"]) == (100000,
                                                                                                         0, 0, 0)
    pad = P.coberturas_da_opcao_vida(P.PADRAO, 100000, explicitas)                              # CONTROLE
    assert pad == {"capital_morte": 100000.0, "isAppMorteAcidental": 100000.0, "isAppInvalidez": 100000.0,
                   "funeral": 2.0}
    with pytest.raises(ValueError):
        P.coberturas_da_opcao_vida("completa_mais", 100000, explicitas)


# ======================================================================================================================
# 4. A COMISSÃO de vida — a do pedido, ou a da conta; 0/ausente → código, NUNCA um número inventado
# ======================================================================================================================
def test_4_comissao_zero_em_todas_e_um_codigo_e_nada_sai():
    sem = pedido_vida(comissao_desconto={})
    sem["comissao_desconto"] = {}
    s, e = disparar(sem, P.coberturas_vida(P.PADRAO, 100000))        # 📊 a conta gravada tem percComissaoVida 0 nas 8
    assert isinstance(e, R.DisparoRecusado) and e.motivo.startswith("comissao_de_vida_nao_configurada"), e
    assert s.escritas == 0 and s.enviado is None


def test_4_comissao_da_conta_por_seguradora_e_quem_tem_zero_sai_listada():
    sem = pedido_vida()
    sem["comissao_desconto"] = {}
    cfg = config_da_conta(**{"4": {"percComissaoVida": 12}, "8": {"percComissaoVida": 8, "percAgenciamentoVida": 50},
                             "1": {"percComissaoVida": None}})
    s, d = disparar(sem, P.coberturas_vida(P.PADRAO, 100000), rotas_=rotas(cfg))
    assert isinstance(d, R.Disparo), getattr(d, "motivo", d)
    por = {it["seguradora"]: it for it in s.enviado["cotacao"]["calculos"]}
    assert sorted(por) == [4, 8]
    assert (por[4]["percComissao"], por[4]["percAgenciamento"]) == (12, 0)     # HDI sem a chave de agenciamento → 0
    assert (por[8]["percComissao"], por[8]["percAgenciamento"]) == (8, 50)
    assert (1, "comissao") in {(c, m) for c, _n, m in d.fora_da_vida}          # Bradesco sem comissão: listada
    # a comissão do AUTO da config (15) nunca vai num item de vida
    assert all(it["percComissao"] != 15 for it in por.values())


# ======================================================================================================================
# 5. O LEITOR — a recusa gravada vira recusa POR seguradora, nunca oferta
# ======================================================================================================================
def _filtrar_como_a_pagina(itens, ramo):
    return _node("process.stdout.write(JSON.stringify(M.filtrar(a.c, a.l)))", {"c": itens, "l": R.lista_de_calculos(ramo)})


def test_5_a_recusa_gravada_vira_recusa_por_seguradora():
    filtrado = _filtrar_como_a_pagina(RESULTADO["calculos"], 91)
    limpos, sujos = R.separar_itens(filtrado, 91)
    assert sujos == [] and len(limpos) == 7
    assert "redacted" not in json.dumps(limpos)                       # nenhuma config/credencial passou a lista branca
    rodada = L.ler_rodada(limpos, t_s=10.0, ramo=91)
    assert rodada.fechado and rodada.ofertas == () and rodada.ramo == 91
    assert {r.familia for r in rodada.respostas} == {C.INSTABILIDADE}
    assert sorted(r.seguradora_codigo for r in rodada.respostas) == [1, 4, 5, 7, 8, 11, 12]
    ev = L.eventos_entre(None, rodada)
    recusas = [e for e in ev if e.tipo == C.SEGURADORA_RECUSOU]
    assert len(recusas) == 7 and all(e.familia == C.INSTABILIDADE and "instabilidade" in e.motivo for e in recusas)
    assert [e.tipo for e in ev].count(C.CONJUNTO_FECHADO) == 1 and not any(e.tipo == C.NOVA_OFERTA for e in ev)
    # a amostra do meio da espera: PENDENTE, nunca recusa
    pend = L.ler_rodada([_filtrar_como_a_pagina([RESULTADO["pendente_amostra"]], 91)[0]], ramo=91)
    assert pend.respostas[0].familia == C.PENDENTE and not pend.fechado


def test_5_uma_oferta_de_vida_na_forma_comum_e_lida_sem_saude():
    """💭 NÃO há resposta de vida COM preço gravada (📊 7 de 7 "instabilidade"): este item é SINTÉTICO, na forma comum do
    resultado (a mesma do RE da 129-C). O canário da V3 é quem prova os rótulos reais."""
    item = {"seguradora": 4, "seguradoraTxt": "Hdi", "nomeSeguradora": "Hdi", "retorno": True, "retornoErro": False,
            "percComissao": 10, "login": "SEGREDO-LOGIN", "fumante": False,
            "resultados": [{"premio": 612.34, "premioMensal": 51.03, "identificacao": "Vida Individual",
                            "packageType": 0, "pathPdf": "https://x.invalid/a.pdf",
                            "coberturas": {"isAppMorte": 100000, "isAppInvalidez": 0, "percComissao": 10,
                                           "fumante": False, "rendaMensal": 8000},
                            "parcelamentos": [{"parcelas": 12, "tipoPag": 1, "premioPrimeiraParc": 51.03,
                                               "premioDemaisParc": 51.03}]}]}
    filtrado = _filtrar_como_a_pagina([item], 91)
    texto = json.dumps(filtrado)
    for proibido in ("SEGREDO-LOGIN", "fumante", "rendaMensal", "8000", "x.invalid"):
        assert proibido not in texto, proibido
    limpos, sujos = R.separar_itens(filtrado, 91)
    assert sujos == []
    r = L.ler_rodada(limpos, ramo=91).respostas[0]
    assert r.familia == C.OFERTA and r.ofertas[0].premio_total == 612.34 and r.ofertas[0].ramo == 91
    assert dict(r.ofertas[0].coberturas) == {"isAppMorte": 100000, "isAppInvalidez": 0}
    assert r.ofertas[0].comissao_percentual == 10 and r.ofertas[0].franquia_valor is None


# ======================================================================================================================
# 7. O PRAZO DA LICENÇA (📊 ao vivo 16/10: a leitura do corpo de /usuario/current não voltou em 2 de 2 logins)
# ======================================================================================================================
def test_7_uma_leitura_da_licenca_que_nunca_volta_nao_prende_o_login(caplog):
    async def cenario():
        nunca = asyncio.get_running_loop().create_future()          # a `Response.body()` que nunca volta
        sessao = SimpleNamespace(_tokens={}, pagina=None, bases={"api": "https://api.agger.invalid"})
        t0 = time.monotonic()
        await asyncio.wait_for(S.Sessoes._completar_licenca(SimpleNamespace(), sessao, {"respondeu": True}, [nunca]),
                               timeout=S.PRAZO_DA_LICENCA_S + 3)
        return time.monotonic() - t0, nunca.cancelled()

    with caplog.at_level(logging.INFO, logger="portal_worker.multicalculo"):
        dt, cancelada = asyncio.run(cenario())
    assert dt <= S.PRAZO_DA_LICENCA_S + 1, dt
    assert cancelada                                                    # a leitura presa não fica viva
    assert any("licença" in r.getMessage() for r in caplog.records)     # e o login registra que seguiu sem ela
    assert 0 < S.PRAZO_DA_LICENCA_S <= 10


def test_nada_de_saude_ou_renda_no_log(caplog):
    with caplog.at_level(logging.DEBUG):
        disparar(pedido_vida(vida={"renda_mensal": 12345.0}), P.coberturas_vida(P.PADRAO, 100000))
        disparar(pedido_vida(vida={"fumante": None}), P.coberturas_vida(P.PADRAO, 100000))
    texto = " ".join(r.getMessage() for r in caplog.records)
    for proibido in ("12345", "fumante", "renda", CPF, "PESSOA SINTETICA"):
        assert proibido not in texto, proibido
