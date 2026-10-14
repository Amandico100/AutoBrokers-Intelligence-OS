# -*- coding: utf-8 -*-
"""SPEC-131-A · F5 — O PERFIL DO SEGURADO: o que o Agger exige e a apólice não traz.

📊 O canário da F4 (13/10): todo AUTO real ficou `pendente(falta_dado)` com 16 campos faltando. Este arquivo prova, com o
MOTOR real (`FonteInfocap._get` → os leitores novos → `perfil_da_renovacao.montar` → a borda `madrugada.perfil_do_segurado`
→ `pedido.de_apolice` → a MESMA conta da porta → `porta.calcular` real sobre o banco dublê) e dublê SÓ na rede da InfoCap:

  · o perfil sai da InfoCap na FORMA REAL medida em 12/10 (envelopes `{"header", "documento": [..], "historico": [..]}`,
    `{"header", "cliente": [..]}`, `{"header", "itens": [..]}`; `fipe` e `anofab` INTEIROS; `padrao` "T") e o AUTO fica
    `pronta` → `calculando` na porta real;
  · cada SUPOSIÇÃO sai marcada "não conferido" com o porquê (e vira `assumido` no pedido) — a mutação que tira uma marca
    fica VERMELHA (`test_toda_suposicao_sai_marcada`);
  · campo ausente → `pendente(falta_dado)` com o NOME; cadastro de outra pessoa ou CPF inválido → não entra;
  · na renovação a placa supre FIPE/ano/combustível (D-133A-03 estendida; F6: os 7 códigos da tela); na cotação,
    não (a linha de controle); o rótulo da InfoCap → o código da tela, e as 3 tabelas são a mesma (F6);
  · o cadastro do cliente NÃO fica no cache.

⛔ Tudo sintético (o CPF de exemplo da 129-B, "Pessoa Sintetica"); nenhuma corretora pelo nome (CLAUDE.md §13.9).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec131a_o_perfil.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import io
import json
import sys
import urllib.parse
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec131a_o_fio as FIO  # noqa: E402
import test_spec131a_o_pedido_da_renovacao as F2T  # noqa: E402
from test_spec131a_o_fio import mundo_real  # noqa: E402,F401  (fixture)
import app.comercial.fonte_infocap as FI  # noqa: E402
from app.services.multicalculo import madrugada as M  # noqa: E402
from app.services.multicalculo import pedido as P  # noqa: E402
from app.services.multicalculo import perfil_da_renovacao as PR  # noqa: E402

#: a borda REAL (o fixture `mundo_real` a troca pelo perfil sintético da F2 — aqui ela volta)
BORDA_REAL = M.perfil_do_segurado
CPF = "52998224725"            # o CPF de exemplo da 129-B (F2T.CPF), só dígitos — 📊 a forma de `/cliente.cpf_cnpj`
HOJE = date(2026, 10, 13)


# ---------------------------------------------------------------------------------------------------------------------
# A InfoCap NA REDE, na forma REAL medida (12/10) — só as três rotas do perfil; o resto vai ao dublê da 131-0
# ---------------------------------------------------------------------------------------------------------------------
def documento(codcli=4242, sinistro="F", inivig="01/11/2025", fimvig="01/11/2026"):
    return {"codfil": 1, "codcli": codcli, "sinistro": sinistro, "sit_sinistro": "0" if sinistro == "F" else "1",
            "sit_sinistro_txt": "APÓLICE SEM SINISTRO", "inivig": inivig, "fimvig": fimvig, "per_c": 20.0,
            "ramo_abrev": "AUTO", "tabela_itens": "AUTOMOVEL"}


def cliente(*, cpf=CPF, datanas="01/02/1980", sexo="F", estado_civil="CASADO(A)", cod="2", pessoa="F",
            cep="88000000", nome="PESSOA SINTETICA DE TESTE"):
    return {"codfil": 1, "codigo": 4242, "nome": nome, "cpf_cnpj": cpf, "datanas": datanas, "sexo": sexo,
            "estado_civil": estado_civil, "cod_estado_civil": cod, "pessoa": pessoa, "dt_venchab": None,
            "cidade": "CIDADE SINTETICA", "estado": "SC",
            "enderecos": [{"codfil": 1, "codigo": 1, "tipo": "R", "padrao": "T", "cep": cep, "logradouro": "RUA X",
                           "numero": "1", "complemento": "", "bairro": "CENTRO", "cidade": "CIDADE SINTETICA",
                           "estado": "SC"}]}


def item_auto(*, placa="AAA1A11", fipe=13277, combustivel="Alcool/Gasolina", bonusclas="07"):
    return {"codfil": 1, "nosnum": 0, "item": 1, "cancelado": "F", "placa": placa, "chassi": "9BWZZZ377VT000001",
            "anofab": 2019, "anomod": 2020, "fipe": fipe, "combustivel": combustivel, "bonusclas": bonusclas,
            "bonus": 0, "zerokm": "F", "categoria": "Passeio", "veiculo": "VEICULO SINTETICO", "garantias": []}


def item_resi():
    return {"codfil": 1, "nosnum": 0, "item": 1, "cancelado": "F", "cep": "88000000", "endereco": "RUA SINTETICA, 10",
            "numero": "", "complemento": "", "bairro": "CENTRO", "cidade": "CIDADE SINTETICA", "estado": "SC",
            "tipo_imovel": "CASA", "garantias": []}


class RedeDoPerfil:
    """`urllib.request.urlopen` falso para `/documento`, `/cliente` e `/itens` (por token e nosnum/codcli); o que não é
    dele vai ao dublê de antes (`anterior`). O cache é o dicionário do dublê da 131-0 (ou um próprio)."""

    def __init__(self, monkeypatch, anterior=None):
        self.anterior = anterior
        self.docs, self.clientes, self.itens = {}, {}, {}
        self.chamadas = []
        self.cache = {}
        monkeypatch.setattr(FI.urllib.request, "urlopen", self._urlopen)
        if anterior is None:
            monkeypatch.setattr(FI, "_cache_ler", lambda chave: self.cache.get(chave))
            monkeypatch.setattr(FI, "_cache_gravar", lambda chave, valor: self.cache.__setitem__(chave, valor))

    def _urlopen(self, req, timeout=None):
        url = urllib.parse.urlparse(req.full_url)
        params = dict(urllib.parse.parse_qsl(url.query, keep_blank_values=True))
        token = req.headers.get("Authorization")
        if url.path == "/documento":
            doc = self.docs.get((token, str(params["nosnum"])))
            corpo = {"header": {"count": 1 if doc else 0}, "documento": [doc] if doc else [],
                     "historico": [{"data": "01/01/2025", "descricao": "LINHA DO HISTORICO"}], "acompanhamento": {}}
        elif url.path == "/cliente":
            c = self.clientes.get((token, str(params["codigo"])))
            corpo = {"header": {"count": 1 if c else 0}, "cliente": [c] if c else []}
        elif url.path == "/itens":
            assert params.get("data"), "📊 sem `data` a rota dá 404 para a renovação que ainda não começou"
            linhas = self.itens.get((token, str(params["nosnum"])), [])
            corpo = {"header": {"count": len(linhas)}, "itens": linhas}
        elif self.anterior is not None:
            return self.anterior(req, timeout)
        else:
            raise AssertionError(f"rota inesperada {url.path}")
        self.chamadas.append((token, url.path))
        return io.BytesIO(json.dumps(corpo).encode("utf-8"))

    def semear(self, token, nosnum, *, doc=None, cli=None, itens=None):
        doc = doc if doc is not None else documento()
        self.docs[(token, str(nosnum))] = doc
        if cli is not None:
            self.clientes[(token, str(doc["codcli"]))] = cli
        self.itens[(token, str(nosnum))] = list(itens or [])


def _fonte_solta(rede, token="token-p"):
    f = FI.FonteInfocap(login=f"{token}@exemplo.invalid", senha="x", rotulo=f"teste-{token}")
    f._token = token
    return f


def _montar(monkeypatch, *, ramo="AUTO", doc=None, cli=None, itens=None, hoje=HOJE, item=None):
    rede = RedeDoPerfil(monkeypatch)
    rede.semear("token-p", 777, doc=doc, cli=cli if cli is not None else cliente(),
                itens=itens if itens is not None else [item_auto()])
    apolice, ficha = FIO.ficha_sintetica(ramo)
    alvo = item if item is not None else {"codfil": 1, "nosnum": 777, "ramo_sigla": ramo}
    perfil, nao = PR.montar("corretora-x", alvo, apolice, ficha, _fonte_solta(rede), hoje=hoje)
    return perfil, nao, rede


# =====================================================================================================================
# 1. O FIO: a InfoCap medida → o pedido que a porta REAL aceita
# =====================================================================================================================
def _uma_corretora_com_o_perfil(m, monkeypatch, *, cli=None, itens_auto=None):
    linhas = FIO.cinco_renovacoes()
    for linha in linhas:
        linha["cic"] = F2T.CPF                    # o documento da LISTA é o do cadastro (a conferência de identidade)
    c = FIO.montar_corretora(m, "token-a", renovacoes=linhas)
    FIO.agger_da_corretora(m, c.id)
    rede = RedeDoPerfil(monkeypatch, anterior=m.rede._urlopen)
    rede.semear("token-a", linhas[0]["nosnum"], cli=cli if cli is not None else cliente(),
                itens=itens_auto if itens_auto is not None else [item_auto()])
    # o RESI é de OUTRO cliente (outro `codcli`): cada cadastro responde pela apólice dele
    rede.semear("token-a", linhas[1]["nosnum"], doc=documento(codcli=4343), cli=cliente(), itens=[item_resi()])
    monkeypatch.setattr(M, "perfil_do_segurado", BORDA_REAL)
    return c, linhas, rede


def _avaliar(m, c, sigla):
    asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == sigla)
    cfg = M.carregar_config(m.db, c.id)
    return item, asyncio.run(M._avaliar(m.db, c.id, item, m.fontes[c.id], cfg))


def test_o_perfil_sai_da_infocap_e_o_auto_vai_a_porta_real(mundo_real, monkeypatch):
    m = mundo_real
    c, _linhas, rede = _uma_corretora_com_o_perfil(m, monkeypatch)
    item, (estado, motivo, pedido, dados) = _avaliar(m, c, "AUTO")
    assert (estado, motivo) == ("pronta", None), dados
    # MEDIDO da InfoCap (nunca suposto): o segurado, o ano, o combustível, o bônus, o sinistro
    assert pedido.valor("segurado", "cpf_cnpj") == CPF and pedido.valor("segurado", "nascimento") == "1980-02-01"
    assert pedido.valor("segurado", "sexo") == "F" and pedido.valor("segurado", "cep") == "88000000"
    assert (pedido.valor("veiculo", "ano_fabricacao"), pedido.valor("veiculo", "ano_modelo")) == (2019, 2020)
    assert pedido.valor("veiculo", "combustivel") == 6                        # "Alcool/Gasolina" = Flex (código 6)
    assert pedido.valor("renovacao", "bonus_anterior") == 7                   # a classe de bônus NUNCA se perde
    assert pedido.valor("renovacao", "sinistros_anterior") == 0
    # a FIPE da InfoCap (inteira, sem os zeros) NÃO entra: a placa supre — declarado
    assert pedido.valor("veiculo", "fipe") is None and "veiculo.fipe" not in M.o_que_falta(pedido)
    # SUPOSTO, marcado — e `assumido` no pedido (o robô e a página sabem)
    assert pedido.valor("condutor", "tempo_habilitacao") == PR.TETO_DO_TEMPO_DE_HABILITACAO
    assert pedido.valor("segurado", "estado_civil") == 2 and pedido.valor("condutor", "cpf") == CPF
    for nome in ("condutor.tempo_habilitacao", "segurado.estado_civil", "condutor.cpf", "pernoite.cep_pernoite",
                 "veiculo.fipe"):
        assert nome in pedido.assumidos, nome
        assert nome in dados["nao_conferidos"], nome
    # o evento leva NOMES e as frases das regras — nunca um valor
    texto = json.dumps(dados, ensure_ascii=False)
    for valor in (CPF, "1980", "88000000", "AAA1A11", "PESSOA SINTETICA"):
        assert valor not in texto, valor
    # a porta REAL aceita (a MESMA conta: a placa supre na renovação) → `calculando`
    r = asyncio.run(M.calcular_dia(m.db, c.id, FIO.DIA))
    auto = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "AUTO")
    assert auto["estado"] == "calculando" and auto["pedido_id"], (r, auto["estado"], auto.get("motivo"))
    # 2 corretoras: cada leitura foi no banco DA corretora (o token dela) — e o cadastro não ficou no cache
    assert {t for t, _rota in rede.chamadas} == {"token-a"}
    assert not [k for k in m.rede.cache if ":/cliente:" in k], "o cadastro do cliente foi para o cache"


def test_re_o_endereco_do_risco_sai_do_item_e_o_que_falta_tem_nome(mundo_real, monkeypatch):
    m = mundo_real
    c, _linhas, _rede = _uma_corretora_com_o_perfil(m, monkeypatch)
    _item, (estado, motivo, _pedido, dados) = _avaliar(m, c, "RESI")
    assert (estado, motivo) == ("pendente", "falta_dado")
    faltam = set(dados["faltando"])
    assert not faltam & {"risco.cep", "risco.logradouro", "risco.bairro", "risco.cidade", "risco.uf",
                         "segurado.cpf_cnpj", "segurado.nome", "segurado.nascimento",
                         "renovacao.sinistros_anterior"}, faltam
    # o que a InfoCap NÃO tem continua faltando, com o nome (nunca inventado): o tipo do imóvel, o bônus do RE
    assert {"risco.tipo_imovel", "renovacao.bonus_anterior"} <= faltam


# =====================================================================================================================
# 2. O QUE FALTA DE VERDADE → pendente(falta_dado) com o NOME
# =====================================================================================================================
def test_sem_nascimento_o_item_fica_pendente_com_os_nomes(mundo_real, monkeypatch):
    m = mundo_real
    c, _l, _r = _uma_corretora_com_o_perfil(m, monkeypatch, cli=cliente(datanas=None))
    _item, (estado, motivo, pedido, dados) = _avaliar(m, c, "AUTO")
    assert (estado, motivo, pedido) == ("pendente", "falta_dado", None)
    assert {"segurado.nascimento", "condutor.nascimento", "condutor.tempo_habilitacao"} <= set(dados["faltando"])
    # CONTROLE: o mesmo item COM o nascimento fecha (a régua que acusou é a mesma que libera)
    c2, _l2, _r2 = _uma_corretora_com_o_perfil(m, monkeypatch)
    _i2, (estado2, *_resto) = _avaliar(m, c2, "AUTO")
    assert estado2 == "pronta"


def test_a_infocap_fora_nao_inventa_nada(mundo_real, monkeypatch):
    m = mundo_real
    c, linhas, rede = _uma_corretora_com_o_perfil(m, monkeypatch)
    rede.docs.pop(("token-a", str(linhas[0]["nosnum"])))            # o /documento não acha a apólice
    _item, (estado, motivo, _p, dados) = _avaliar(m, c, "AUTO")
    assert (estado, motivo) == ("pendente", "falta_dado")
    assert "segurado.cpf_cnpj" in dados["faltando"] and "condutor.tempo_habilitacao" in dados["faltando"]


def test_cadastro_de_outra_pessoa_ou_cpf_invalido_nao_entra(monkeypatch):
    item = {"codfil": 1, "nosnum": 777, "ramo_sigla": "AUTO", "documento_mascarado": "***.***.***-99"}
    perfil, nao, _r = _montar(monkeypatch, item=item)
    assert "cpf_cnpj" not in perfil.get("segurado", {}) and "nascimento" not in perfil.get("segurado", {})
    assert "não é o do segurado" in nao["segurado.cpf_cnpj"]
    # CONTROLE: os 2 últimos dígitos certos → entra
    perfil, _nao, _r = _montar(monkeypatch, item={**item, "documento_mascarado": "***.***.***-25"})
    assert perfil["segurado"]["cpf_cnpj"] == CPF
    # CPF que não fecha o dígito → não entra (P-1310-02)
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(cpf="52998224726"))
    assert "cpf_cnpj" not in perfil.get("segurado", {}) and "dígito" in nao["segurado.cpf_cnpj"]


# =====================================================================================================================
# 3. AS REGRAS — cada suposição com a marca e o porquê
# =====================================================================================================================
def test_tempo_de_habilitacao_idade_menos_18_limitado(monkeypatch):
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(datanas="01/02/1980"))
    assert perfil["condutor"]["tempo_habilitacao"] == 10 and nao["condutor.tempo_habilitacao"] == PR.POR_QUE_TEMPO
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(datanas="13/10/2004"))           # 22 anos
    assert perfil["condutor"]["tempo_habilitacao"] == 4 and nao["condutor.tempo_habilitacao"] == PR.POR_QUE_TEMPO_JOVEM
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(datanas="14/10/2008"))           # 17 anos: sem tempo
    assert "tempo_habilitacao" not in perfil.get("condutor", {})


@pytest.mark.parametrize("rotulo,codigo,porque", [
    ("CASADO(A)", 2, PR.POR_QUE_ESTADO_CIVIL), ("SOLTEIRO(A)", 1, PR.POR_QUE_ESTADO_CIVIL),
    ("DIVORCIADO(A)", 4, PR.POR_QUE_ESTADO_CIVIL), ("VIÚVO(A)", 2, PR.POR_QUE_ESTADO_CIVIL_PADRAO),
    (None, 2, PR.POR_QUE_ESTADO_CIVIL_PADRAO)])
def test_estado_civil_pelo_rotulo_so_os_codigos_observados(monkeypatch, rotulo, codigo, porque):
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(estado_civil=rotulo, cod="9"))   # o código da InfoCap NÃO decide
    assert perfil["segurado"]["estado_civil"] == codigo and nao["segurado.estado_civil"] == porque


def test_sexo_vazio_sai_do_nome_marcado_ou_fica_faltando(monkeypatch):
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(sexo="", nome="MARIA SINTETICA"))
    assert perfil["segurado"]["sexo"] == "F" and nao["segurado.sexo"] == PR.POR_QUE_SEXO_PELO_NOME
    perfil, nao, _r = _montar(monkeypatch, cli=cliente(sexo="", nome="XQZWK SINTETICO"))   # fora da tabela
    assert "sexo" not in perfil.get("segurado", {}) and "segurado.sexo" not in nao


#: F6 — o rótulo da InfoCap → o código da TELA do Agger. 📊 13/10, a lista do campo Combustível lida no bundle do app:
#: GASOLINA 1 · ALCOOL 2 · DIESEL 3 · ELÉTRICO 5 · FLEX 6 · TETRAFUEL 10 · HÍBRIDO 11 (controle: FLEX 6 = 18/18 corpos).
#: Os rótulos da InfoCap são os do F5 (📊 40 AUTO: Flex 13 · Gasolina 7 · Diesel 3 · Eletrico 2 · Hibrido 1 …).
COMBUSTIVEL_DA_TELA = {"gasolina": 1, "alcool": 2, "diesel": 3, "eletrico": 5, "flex": 6, "tetrafuel": 10, "hibrido": 11}


@pytest.mark.parametrize("rotulo,codigo", [
    ("Alcool/Gasolina", 6), ("Gasolina", 1), ("GASOLINA", 1), ("Diesel", 3), ("Elétrico", 5), ("Eletrico", 5),
    ("Híbrido", 11), ("Hibrido", 11), ("Alcool", 2), ("Etanol", 2), ("Flex", 6), ("Tetrafuel", 10)])
def test_combustivel_pelo_rotulo_da_infocap_vira_o_codigo_da_tela(monkeypatch, rotulo, codigo):
    perfil, nao, _r = _montar(monkeypatch, itens=[item_auto(combustivel=rotulo)])
    assert "veiculo.combustivel" not in nao                     # VEIO da InfoCap: não é suposição
    apolice, ficha = FIO.ficha_sintetica("AUTO")
    pedido = P.de_apolice(apolice, perfil, ficha=ficha, config=F2T.CONFIG)
    assert pedido.valor("veiculo", "combustivel") == codigo, rotulo
    assert pedido.sem_codigo() == [] and "veiculo.combustivel" not in M.o_que_falta(pedido)


@pytest.mark.parametrize("rotulo", ["", None, "Nao Informado", "GNV", "Querosene"])
def test_combustivel_sem_rotulo_conhecido_a_placa_supre_marcado_e_sem_placa_falta(monkeypatch, rotulo):
    perfil, nao, _r = _montar(monkeypatch, itens=[item_auto(combustivel=rotulo)])
    assert "combustivel" not in perfil["veiculo"]
    assert nao["veiculo.combustivel"] == PR.POR_QUE_PELA_PLACA            # a placa supre — DECLARADO
    apolice, ficha = FIO.ficha_sintetica("AUTO")
    pedido = P.de_apolice(apolice, perfil, ficha=ficha, config=F2T.CONFIG)
    assert pedido.valor("veiculo", "combustivel") is None and "veiculo.combustivel" not in M.o_que_falta(pedido)
    # CONTROLE: sem placa nada é suprido do nada — falta, com o nome
    sem_placa = P.de_apolice(F2T._apolice("AUTO"), {**perfil, "veiculo": {}}, ficha=None, config=F2T.CONFIG)
    assert "veiculo.combustivel" in sem_placa.faltando(origem="auxiliar", servico="renovacao")


def test_as_tres_tabelas_do_combustivel_sao_a_mesma():
    """InfoCap → rótulo (`perfil_da_renovacao`), rótulo → código (`contrato.CODIGOS_MEDIDOS`: a porta — o canal também)
    e o rótulo da FIPE → código (`montador.js`, na página): UMA lista, a da tela. Mudou uma, este guarda fica vermelho."""
    import re as _re
    from portal_worker.multicalculo.contrato import CODIGOS_MEDIDOS

    assert CODIGOS_MEDIDOS[("veiculo", "combustivel")] == COMBUSTIVEL_DA_TELA
    assert set(PR.COMBUSTIVEL_NO_AGGER.values()) <= set(COMBUSTIVEL_DA_TELA)
    js = (BACKEND / "portal_worker" / "multicalculo" / "montador.js").read_text(encoding="utf-8")
    bloco = _re.search(r"const COMBUSTIVEL = \[(.*?)\];", js, _re.S).group(1)       # a FORMA da declaração (§9.4)
    pares = {k.lower(): int(v) for k, v in _re.findall(r"\['([A-Z]+)', (\d+)\]", bloco)}
    assert pares == COMBUSTIVEL_DA_TELA


def test_o_montador_traduz_o_rotulo_da_fipe_como_a_tela():
    """O MOTOR na página (`montador.js` `codigoDoCombustivel` e `montarAutomovel`), rodado no node: o rótulo da tabela
    FIPE do modelo → o código, para TODO combustível (a F5 só traduzia o Flex — 📊 64/64 recusas); vazio → nada."""
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("sem node nesta máquina")
    js = (BACKEND / "portal_worker" / "multicalculo" / "montador.js").as_posix()
    prog = ("global.window={};eval(require('fs').readFileSync(%r,'utf8'));const M=window.__abM;"
            "const r={};for(const x of ['Gasolina','Flex','Diesel','\\u00c1lcool','El\\u00e9trico','H\\u00edbrido',"
            "'Tetrafuel','']) r[x]=M.codigoDoCombustivel(x);"
            "const fm=[{modelo:'X',fipeValores:[{valor:1,mesVersaoTabela:9,anoVersaoTabela:2026,combustivel:'Diesel'},"
            "{valor:2,mesVersaoTabela:8,anoVersaoTabela:2026,combustivel:'Flex'}]}];"
            "r.auto=M.montarAutomovel({combustivel:null},{fipe:'1',anoMod:2020},fm).combustivel;"
            "r.vence=M.montarAutomovel({combustivel:1},{fipe:'1',anoMod:2020},fm).combustivel;"
            "console.log(JSON.stringify(r))") % js
    saida = json.loads(subprocess.run([node, "-e", prog], capture_output=True, text=True, encoding="utf-8",
                                      timeout=60, check=True).stdout)
    assert saida == {"Gasolina": 1, "Flex": 6, "Diesel": 3, "Álcool": 2, "Elétrico": 5, "Híbrido": 11, "Tetrafuel": 10,
                     "": None, "auto": 3, "vence": 1}     # a tabela MAIS RECENTE decide; o pedido VENCE a FIPE


def test_sinistro_e_fipe(monkeypatch):
    perfil, nao, _r = _montar(monkeypatch, doc=documento(sinistro="T"))
    assert perfil["renovacao"]["sinistros_anterior"] == 1 and nao["renovacao.sinistros_anterior"] == PR.POR_QUE_SINISTRO
    perfil, nao, _r = _montar(monkeypatch)
    assert perfil["renovacao"]["sinistros_anterior"] == 0 and "renovacao.sinistros_anterior" not in nao
    # FIPE de 7 dígitos só SEM placa (a placa supre; o pedido venceria a placa no montador)
    item = {"codfil": 1, "nosnum": 777, "ramo_sigla": "AUTO"}
    rede = RedeDoPerfil(monkeypatch)
    rede.semear("token-p", 777, cli=cliente(), itens=[item_auto(placa="-", fipe=1327770)])
    apolice, ficha = F2T._apolice("AUTO"), None
    perfil, nao = PR.montar("x", item, apolice, ficha, _fonte_solta(rede), hoje=HOJE)
    assert perfil["veiculo"]["fipe"] == "1327770" and "placa" not in perfil["veiculo"]
    rede.itens[("token-p", "777")] = [item_auto(placa="-", fipe=13277)]                 # 5 dígitos: nunca completada
    rede.cache.clear()
    perfil, nao = PR.montar("x", item, apolice, ficha, _fonte_solta(rede), hoje=HOJE)
    assert "fipe" not in perfil.get("veiculo", {})


#: 🔴 O GUARDA: toda SUPOSIÇÃO (o que não veio como valor da InfoCap) sai MARCADA, com o porquê. A mutação de tirar uma
#: marca — `por("condutor", "tempo_habilitacao", tempo)` sem o motivo — fica VERMELHA aqui.
SUPOSICOES_DO_AUTO = ("condutor.tempo_habilitacao", "segurado.estado_civil", "condutor.cpf", "condutor.nome",
                      "condutor.nascimento", "condutor.sexo", "condutor.estado_civil", "condutor.relacao_com_segurado",
                      "pernoite.cep_pernoite", "veiculo.fipe", "veiculo.uso", "pernoite.garagem_residencia",
                      "questionario.km_mensal", "condutor.jovem_condutor")


def test_toda_suposicao_sai_marcada(monkeypatch):
    perfil, nao, _r = _montar(monkeypatch)
    for nome in SUPOSICOES_DO_AUTO:
        assert nao.get(nome), f"{nome} foi suposto sem a marca de 'não conferido'"
    # e o que VEIO da InfoCap não é marcado como suposto (a marca não é carimbo)
    for nome in ("segurado.cpf_cnpj", "segurado.nascimento", "segurado.sexo", "segurado.cep",
                 "veiculo.ano_fabricacao", "veiculo.combustivel", "renovacao.bonus_anterior"):
        assert nome not in nao, nome
    # os valores supostos estão no perfil (o tempo) — a marca acompanha um valor real, nunca um vazio
    assert perfil["condutor"]["tempo_habilitacao"] == 10


# =====================================================================================================================
# 4. A PLACA SUPRE NA RENOVAÇÃO (e, desde a SPEC-132-B, na COTAÇÃO) — e não no pedido sem serviço (a linha de controle)
# =====================================================================================================================
def test_a_placa_supre_fipe_ano_e_combustivel_na_renovacao_e_o_pedido_sem_servico_continua_exigindo():
    """F6 (§9.3 — a verdade da F5 venceu): o combustível VOLTA a ser suprido pela placa na renovação, porque os 7 códigos
    da tela foram medidos e o montador traduz o rótulo da FIPE como a tela (a F5 o tirou: só o Flex tinha código).
    §9.3 de novo (SPEC-132-B, B4): este teste se chamava "…e_nao_na_cotacao" — verdade vencida: a SPEC-132-B C4 pôs a
    cotação no conjunto (`SERVICOS_EM_QUE_A_PLACA_SUPRE`). A linha de controle que ficou é o pedido SEM serviço (o
    legado), que continua exigindo os três; a asserção não afrouxou."""
    apolice, ficha = FIO.ficha_sintetica("AUTO")
    perfil = F2T._perfil_auto()
    perfil["veiculo"] = {}                                    # sem FIPE, ano e combustível
    pedido = P.de_apolice(apolice, perfil, ficha=ficha, config=F2T.CONFIG)
    supridos = {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"}
    assert not supridos & set(pedido.faltando(origem="auxiliar", servico="renovacao"))
    assert not supridos & set(M.o_que_falta(pedido))         # a madrugada usa a MESMA conta da porta
    # e a cotação (SPEC-132-B C4) também é suprida pela MESMA placa
    assert not supridos & set(pedido.faltando(origem="auxiliar", servico="cotacao"))
    # CONTROLE: o pedido sem o serviço (mesma origem `auxiliar`, o legado) continua exigindo os três
    assert supridos <= set(pedido.faltando(origem="auxiliar"))
    assert supridos <= pedido.assumindo_pela_placa(servico="renovacao").assumidos
    # e o canal (D-133A-03) segue como era — fora desta fatia (ver o relatório)
    assert "veiculo.combustivel" not in pedido.faltando(origem="canal")
    # sem placa a regra não vale (nada é suprido do nada)
    sem_placa = P.de_apolice(F2T._apolice("AUTO"), perfil, ficha=None, config=F2T.CONFIG)
    assert supridos <= set(sem_placa.faltando(origem="auxiliar", servico="renovacao"))


# =====================================================================================================================
# 5. O CANÁRIO COM CÁLCULO: "processar estes cálculos" — o motor de produção não toca o que tem espera no futuro
# =====================================================================================================================
import test_spec129b_o_motor as TM  # noqa: E402
import test_spec1310_f3_contas as F3  # noqa: E402
import test_spec131a_a_madrugada_no_agger as MNA  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from test_spec131a_a_madrugada_no_agger import amb  # noqa: E402,F401  (fixture)
from portal_worker.multicalculo import motor as MOT  # noqa: E402


def _motor(amb, nome, **kw):
    visao = amb.banco.visao(nome)

    async def upload(supa, caminho, blob, content_type="application/pdf"):
        return caminho

    return MOT.Motor(visao, sessoes=MNA.SessoesDaMadrugada(amb.mundo, nome), robo=TM.RoboDuble(amb.mundo, visao),
                     sessao_mod=TM.SESSAO_MOD, dono=nome, agora=amb.relogio.agora, batida_s=0.02, upload=upload,
                     freio=lambda: False, canario=False, **kw)


def test_o_canario_processa_so_os_seus_calculos_e_a_producao_nao_os_toca(amb):
    from datetime import timedelta

    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, _conta = MNA.montar_dono(amb, a)
    aberto = MNA.renovar(amb, a, dono, politica=None)
    pid = aberto.pedido_id
    futuro = (amb.relogio.agora() + timedelta(hours=6)).isoformat()
    def meus():
        return [c for c in amb.banco.linhas("multicalculo_calculos") if c["pedido_id"] == pid]

    for c in meus():
        c["disponivel_em"] = futuro                  # o que o canário grava: a fila global não o vê antes de 6 h
    assert {c["disponivel_em"] for c in meus()} == {futuro}
    # o motor de PRODUÇÃO (a fila inteira) não reserva
    assert TM.rodar(_motor(amb, "motor-de-producao").uma_volta()) == 0
    # CONTROLE: o do canário SEM a entrada nova também não (a espera vale para ele)
    assert TM.rodar(_motor(amb, "canario-sem-entrada", somente_pedidos={pid}).uma_volta()) == 0
    assert {c["status"] for c in meus()} == {"na_fila"} and not any(c.get("dono") for c in meus())
    # o do canário COM a entrada: reserva os SEUS, já, e é ele o dono
    assert TM.rodar(_motor(amb, "motor-do-canario", somente_pedidos={pid}, ignorar_espera=True).uma_volta()) == 1
    assert meus() and all(c["status"] != "na_fila" for c in meus())
    assert {c.get("dono") for c in meus()} == {"motor-do-canario"}
    # ⛔ nunca a fila inteira sem a espera
    with pytest.raises(ValueError, match="somente_pedidos"):
        _motor(amb, "x", ignorar_espera=True)
