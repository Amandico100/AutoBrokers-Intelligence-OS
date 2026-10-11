# -*- coding: utf-8 -*-
"""SPEC-131-0 F2 — o DONO da renovação, e a pessoa da corretora que responde por ele (D-131-0-03/30/31).

O FIO que este arquivo atravessa: a InfoCap NA REDE (dublê só do `urlopen`, com a FORMA REAL do `/prod_docs` avulso
medida em 11/10/2026) → `FonteInfocap.prod_docs_avulso` REAL (`_get`, `_linhas`, a chave de cache REAL) →
`dono.regra_de_dono` (a linha da corretora ou o padrão do SISTEMA, lido do pacote) → `dono.aplicar_regra` →
`membro_produtores` → `company_members`/`users_v2` no banco dublê com as travas da migration 20261011_03.

O que cada teste guarda:
    ① o dono é o `indireto="F"` — mesmo quando ele está na ORDEM 3 (📊 1º só em 37/99 e 24/217)
    ② a regra da corretora vence a padrão, e a origem diz quem decidiu
    ③ 0 desmarcados → sem_dono · 2 → ambíguo · o mesmo produtor repetido não é ambíguo
    ④ membro inativo, usuário inativo ou apagado → sem_membro (nunca o user_id dele)
    ⑤ duas corretoras, o MESMO codpro e o MESMO nosnum: nem o cache nem o vínculo cruzam (+ CONTROLE que cruza)
    ⑥ o vínculo: só membro ativo DESTA corretora; o mesmo código não é de duas pessoas; desvincular de outra = 0
    ⑦ a régua: conta, separa, e NÃO é carimbo — a regra `ordem 1` dá um dono em 100 % e a régua mostra que erra
    ⑧ as sugestões: por nome sem o papel, nunca gravam
    ⑨ a rota interna: chave, recusas, a regra validada e o "voltar ao padrão"
    ⑩ a InfoCap da corretora é aberta pelo `_abrir(company_id)` — nunca por nome de corretora (§13.9)

⛔ Nenhum nome real: corretora_a/corretora_b, membro_a/membro_b; senha "senha-de-teste-1".
"""
from __future__ import annotations

import asyncio
import io
import json
import sys
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
from app.comercial import fonte_infocap as FI  # noqa: E402
from app.providers.infocap_analytics_provider import chave_de_cache  # noqa: E402
from app.services.sistema_de_gestao import dono as DONO  # noqa: E402

CHAVE = "chave-interna-de-teste"
SENHA = "senha-de-teste-1"
AGORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
NOSNUM_COMUM = 91175   # 📊 o MESMO nosnum existe nos dois bancos medidos (BLOCO0-INFOCAP §2)

U = ("uuid", False, None)
UN = ("uuid", True, None)
TN = ("text", True, None)
ESQUEMA_F2 = {
    "company_members": {"id": ("uuid", False, "UUID"), "user_id": U, "company_id": U, "role": TN,
                        "status": ("text", False, "active"), "created_at": ("ts", False, "NOW")},
    "users_v2": {"id": ("uuid", False, "UUID"), "first_name": TN, "last_name": TN,
                 "status": ("text", False, "active"), "deleted_at": ("ts", True, None)},
    # 📊 a migration 20261011_03
    "membro_produtores": {"id": ("uuid", False, "UUID"), "company_id": U, "user_id": U, "sistema": ("text", False, None),
                          "codfil": ("int", False, 1), "codigo_produtor": ("text", False, None),
                          "nome_produtor": TN, "papel_cru": TN, "criado_por": UN, "criado_em": ("ts", False, "NOW")},
    "regras_de_dono": {"company_id": U, "sistema": ("text", False, None), "regra": ("jsonb", False, None),
                       "atualizado_por": UN, "atualizado_em": ("ts", False, "NOW")},
}


class BancoF2(D.BancoEmMemoria):
    """As travas da migration 20261011_03 que o código pode violar."""

    def _travas(self, tabela, nova, velha):
        super()._travas(tabela, nova, velha)
        if tabela == "company_members":
            self._unico(tabela, "company_members_user_id_company_id_key", ("user_id", "company_id"), nova, velha)
        elif tabela == "membro_produtores":
            self._check("ck_membro_produtores_sistema", nova["sistema"] in ("infocap", "quiver", "outro"))
            self._check("ck_membro_produtores_codigo", bool(str(nova["codigo_produtor"]).strip()))
            self._check("ck_membro_produtores_codfil", int(nova["codfil"]) >= 1)
            self._unico(tabela, "uq_membro_produtores_codigo", ("company_id", "sistema", "codfil", "codigo_produtor"),
                        nova, velha)
            self._fk(tabela, "fk_membro_produtores_membro", (("user_id", "user_id"), ("company_id", "company_id")),
                     "company_members", nova)
        elif tabela == "regras_de_dono":
            self._unico(tabela, "regras_de_dono_pkey", ("company_id", "sistema"), nova, velha)
            self._check("ck_regras_de_dono_objeto", isinstance(nova["regra"], dict))


# --------------------------------------------------------------------------------------------------------------------
# A InfoCap NA REDE — a forma REAL (📊 11/10/2026, `GET /prod_docs?codfil=&nosnum=` e `/produtores?texto=&codage=1`)
# --------------------------------------------------------------------------------------------------------------------
def pd(nosnum, codpro, ordem, indireto, nome, codfil=1):
    """Uma linha do `/prod_docs` AVULSO com TODAS as chaves que a API devolve (o código é `codpro`, não `cod_pro`)."""
    return {"codfil": codfil, "nosnum": nosnum, "codage": 1, "codpro": codpro, "perpart": 0.0, "indireto": indireto,
            "ordem": ordem, "datrep_prot": None, "campo_base_r": 1, "base_r": 1000.0, "per_r": 5.0, "val_r": 50.0,
            "forma_repasse_r": 1, "campo_base_rc": 1, "base_rc": 0.0, "per_rc": 0.0, "val_rc": 0.0,
            "forma_repasse_rc": 1, "campo_base_ra": 1, "val_ra": 0.0, "campo_base_rp": 1, "base_rp": 0.0,
            "per_rp": 0.0, "val_rp": 0.0, "forma_repasse_rp": 1, "cod_com_ind": None, "taxa_repasse": 0,
            "nome_agente": "AGENTE FICTICIO", "nome_produtor": nome}


def renov(nosnum, codfil=1, tipdoc="A", cancelado="F"):
    """Uma linha de `/renovacoes` (as chaves que importam + o nome do CLIENTE, que nunca pode sair da régua)."""
    return {"codfil": codfil, "nosnum": nosnum, "tipdoc": tipdoc, "cancelado": cancelado,
            "cliente": "CLIENTE FICTICIO DE TESTE", "cic": "000.000.000-00", "ramo": "RESI", "fimvig": "01/11/2026",
            "prod_docs": [{"cod_pro": 11, "ordem": 1, "produtor": "PRODUTOR UM INDICADOR"}]}


class InfocapNaRede:
    """`urllib.request.urlopen` falso: responde por TOKEN (cada corretora tem o seu banco) e conta as chamadas.
    O cache do Redis vira um dicionário — com a chave REAL que `FonteInfocap._get` monta."""

    def __init__(self, monkeypatch):
        self.bancos = {}       # token -> {"prod_docs": {(codfil, nosnum): [linhas]}, "produtores": [...], "renov": [...]}
        self.chamadas = []
        self.cache = {}
        monkeypatch.setattr(FI.urllib.request, "urlopen", self._urlopen)
        monkeypatch.setattr(FI, "_cache_ler", lambda chave: self.cache.get(chave))
        monkeypatch.setattr(FI, "_cache_gravar", lambda chave, valor: self.cache.__setitem__(chave, valor))

    def fonte(self, company_id, token, *, rotulo=None):
        f = FI.FonteInfocap(login=f"{token}@exemplo.invalid", senha=SENHA,
                            rotulo=rotulo if rotulo is not None else chave_de_cache(company_id, "conexao-" + token))
        f._token = token   # já autenticada: o dublê é só a rede
        self.bancos.setdefault(token, {"prod_docs": {}, "produtores": [], "renov": []})
        return f

    def _urlopen(self, req, timeout=None):
        url = urllib.parse.urlparse(req.full_url)
        params = dict(urllib.parse.parse_qsl(url.query, keep_blank_values=True))
        token = req.headers.get("Authorization")
        banco = self.bancos[token]
        self.chamadas.append((token, url.path, params))
        if url.path == "/prod_docs":
            linhas = banco["prod_docs"].get((int(params["codfil"]), int(params["nosnum"])), [])
            corpo = {"header": {"count": len(linhas)}, "prod_docs": linhas}
        elif url.path == "/produtores":
            assert params.get("codage") == "1", "📊 sem codage a rota dá 500"
            corpo = {"header": {"count": len(banco["produtores"])}, "produtores": banco["produtores"]}
        elif url.path == "/renovacoes":
            corpo = {"header": {"count": len(banco["renov"])}, "renovacoes": banco["renov"]}
        else:
            raise AssertionError(f"rota inesperada {url.path}")
        return io.BytesIO(json.dumps(corpo).encode("utf-8"))


@pytest.fixture
def mundo(monkeypatch):
    for tabela, cols in ESQUEMA_F2.items():
        monkeypatch.setitem(D.ESQUEMA, tabela, cols)
    DONO._padrao_bruto.cache_clear()
    banco = BancoF2(D.Relogio(AGORA))
    a, b = str(uuid4()), str(uuid4())
    for c in (a, b):
        banco.semear("companies", {"id": c})
    membro_a, membro_b, membro_a2 = str(uuid4()), str(uuid4()), str(uuid4())
    for uid, nome, c in ((membro_a, "Membro", a), (membro_a2, "Outra Pessoa", a), (membro_b, "Membro Bê", b)):
        banco.semear("users_v2", {"id": uid, "first_name": nome, "last_name": "Teste"})
        banco.semear("company_members", {"user_id": uid, "company_id": c, "role": "member"})
    rede = InfocapNaRede(monkeypatch)
    yield SimpleNamespace(banco=banco, db=banco.visao("smith-api"), a=a, b=b, membro_a=membro_a,
                          membro_a2=membro_a2, membro_b=membro_b, rede=rede)
    DONO._padrao_bruto.cache_clear()


def _dono(m, company_id, fonte, nosnum=NOSNUM_COMUM, codfil=1):
    return asyncio.run(DONO.dono_da_apolice(m.db, company_id, codfil=codfil, nosnum=nosnum, fonte=fonte))


def _quatro_produtores(nosnum, dono_codpro=247, dono_ordem=3, dono_nome="247 - M. PESSOA A FECHADORA"):
    """📊 a forma típica: 4 produtores, o ordem 1 é INDICADOR, o dono (`indireto F`) está na ordem 3."""
    linhas = [pd(nosnum, 11, 0, "T", "PRODUTOR UM INDICADOR"), pd(nosnum, 12, 0, "T", "PRODUTORA DOIS INDICADORA"),
              pd(nosnum, 13, 0, "T", "PRODUTOR QUATRO EXECUTIVO")]
    linhas.insert(dono_ordem - 1, pd(nosnum, dono_codpro, 0, "F", dono_nome))
    for i, linha in enumerate(linhas):   # a posição é a da lista: uma ordem por produtor, como a API devolve
        linha["ordem"] = i + 1
    return linhas


# ① ===================================================================================================================
def test_o_dono_e_o_indireto_F_mesmo_na_ordem_3(mundo):
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    m.rede.bancos["token-a"]["prod_docs"][(1, NOSNUM_COMUM)] = _quatro_produtores(NOSNUM_COMUM)
    DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codfil=1, codigo_produtor="247")
    r = _dono(m, m.a, fonte)
    assert r.status == "ok", r
    assert r.codigo_produtor == "247", "o dono é o produtor com a caixa 'Ind.' desmarcada — não o 1º da lista"
    assert r.user_id == m.membro_a
    assert r.papel_cru == "FECHADORA" and r.regra_origem == DONO.ORIGEM_PADRAO
    # a regra padrão veio do PACOTE (viaja na imagem), não de `docs/`
    padrao = DONO.regra_padrao_do_sistema("infocap")
    assert (padrao.campo, padrao.igual, padrao.codigo, padrao.rota) == ("indireto", "F", "codpro", "/prod_docs")
    # a chamada foi o /prod_docs AVULSO, com codfil e nosnum
    assert ("token-a", "/prod_docs", {"codfil": "1", "nosnum": str(NOSNUM_COMUM)}) in m.rede.chamadas


# ② ===================================================================================================================
def test_a_regra_da_corretora_vence_a_padrao_e_a_origem_e_dita(mundo):
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    m.rede.bancos["token-a"]["prod_docs"][(1, NOSNUM_COMUM)] = _quatro_produtores(NOSNUM_COMUM)
    DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codigo_produtor="247")
    DONO.vincular(m.db, m.a, user_id=m.membro_a2, sistema="infocap", codigo_produtor="11")
    # a corretora A grava a regra `ordem 1` (a regra errada que o código antigo usava) — e ela VENCE
    regra = DONO.gravar_regra(m.db, m.a, "infocap", {"campo": "ordem", "igual": 1, "codigo": "codpro",
                                                     "nome": "nome_produtor", "papel_no_nome": True})
    assert regra.origem == DONO.ORIGEM_CORRETORA and regra.igual == "1"
    r = _dono(m, m.a, fonte)
    assert (r.status, r.codigo_produtor, r.user_id, r.regra_origem) == ("ok", "11", m.membro_a2, "corretora")
    # a regra da A não vale para a B (filtro company_id): a B continua no padrão
    assert DONO.regra_de_dono(m.db, m.b).origem == DONO.ORIGEM_PADRAO
    # voltar ao padrão
    assert DONO.apagar_regra(m.db, m.a, "infocap") == 1
    r2 = _dono(m, m.a, fonte)
    assert (r2.codigo_produtor, r2.user_id, r2.regra_origem) == ("247", m.membro_a, DONO.ORIGEM_PADRAO)
    # uma linha ilegível no banco (escrita por fora) NÃO vale: cai no padrão e a origem conta a verdade
    m.banco.semear("regras_de_dono", {"company_id": m.a, "sistema": "infocap", "regra": {"campo": "x y"}})
    assert DONO.regra_de_dono(m.db, m.a).origem == DONO.ORIGEM_PADRAO


# ③ ===================================================================================================================
def test_zero_desmarcados_e_sem_dono_dois_e_ambiguo(mundo):
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    pdocs = m.rede.bancos["token-a"]["prod_docs"]
    pdocs[(1, 1)] = [pd(1, 11, 1, "T", "UM INDICADOR"), pd(1, 12, 2, "T", "DOIS INDICADOR")]
    pdocs[(1, 2)] = [pd(2, 11, 1, "F", "UM FECHADOR"), pd(2, 12, 2, "F", "DOIS FECHADOR")]
    pdocs[(1, 3)] = [pd(3, 247, 1, "F", "DONO FECHADOR"), pd(3, "0247", 2, "F", "DONO FECHADOR")]
    # (1, 4) não existe: a API devolve vazio
    assert _dono(m, m.a, fonte, nosnum=1).status == "sem_dono"
    amb = _dono(m, m.a, fonte, nosnum=2)
    assert amb.status == "ambiguo" and amb.codigo_produtor is None and amb.user_id is None
    mesmo = _dono(m, m.a, fonte, nosnum=3)
    assert mesmo.status == "sem_membro" and mesmo.codigo_produtor == "247", "o MESMO produtor duas vezes é UM dono"
    vazio = _dono(m, m.a, fonte, nosnum=4)
    assert vazio.status == "sem_dono" and "não devolveu" in vazio.motivo


# ④ ===================================================================================================================
@pytest.mark.parametrize("como", ["vinculo_inativo", "usuario_inativo", "usuario_apagado"])
def test_membro_inativo_e_sem_membro(mundo, como):
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    m.rede.bancos["token-a"]["prod_docs"][(1, NOSNUM_COMUM)] = _quatro_produtores(NOSNUM_COMUM)
    DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codigo_produtor="247")
    assert _dono(m, m.a, fonte).user_id == m.membro_a, "CONTROLE: ativo, ele é o dono"
    if como == "vinculo_inativo":
        next(v for v in m.banco.linhas("company_members") if v["user_id"] == m.membro_a)["status"] = "inactive"
    elif como == "usuario_inativo":
        next(u for u in m.banco.linhas("users_v2") if u["id"] == m.membro_a)["status"] = "lead"
    else:
        next(u for u in m.banco.linhas("users_v2") if u["id"] == m.membro_a)["deleted_at"] = AGORA.isoformat()
    r = _dono(m, m.a, fonte)
    assert (r.status, r.user_id, r.codigo_produtor) == ("sem_membro", None, "247")
    assert DONO.membro_do_produtor(m.db, m.a, "infocap", 1, 247) is None


# ⑤ ===================================================================================================================
def test_duas_corretoras_mesmo_codpro_e_mesmo_nosnum_nao_se_cruzam(mundo):
    m = mundo
    fa, fb = m.rede.fonte(m.a, "token-a"), m.rede.fonte(m.b, "token-b")
    # o MESMO nosnum nos dois bancos; na A o dono é o 247, na B é o 300
    m.rede.bancos["token-a"]["prod_docs"][(1, NOSNUM_COMUM)] = _quatro_produtores(NOSNUM_COMUM, dono_codpro=247)
    m.rede.bancos["token-b"]["prod_docs"][(1, NOSNUM_COMUM)] = _quatro_produtores(NOSNUM_COMUM, dono_codpro=300,
                                                                                    dono_nome="300 OUTRO FECHADOR")
    # o MESMO codpro 247 ligado a uma pessoa em CADA corretora (bancos diferentes: é legítimo)
    DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codigo_produtor="247")
    DONO.vincular(m.db, m.b, user_id=m.membro_b, sistema="infocap", codigo_produtor="247")
    ra = _dono(m, m.a, fa)            # aquece o cache com o dado da A
    rb = _dono(m, m.b, fb)
    assert (ra.codigo_produtor, ra.user_id) == ("247", m.membro_a)
    assert rb.codigo_produtor == "300", "a B leu o banco DELA, não o cache da A"
    assert rb.status == "sem_membro" and rb.user_id is None, "o 300 não tem vínculo na B — e nunca vira membro da A"
    assert [c[0] for c in m.rede.chamadas if c[1] == "/prod_docs"] == ["token-a", "token-b"]
    assert DONO.membro_do_produtor(m.db, m.a, "infocap", 1, "247") == m.membro_a
    assert DONO.membro_do_produtor(m.db, m.b, "infocap", 1, "247") == m.membro_b
    # o cache: a segunda leitura de cada uma vem do cache DELA (nenhuma chamada nova)
    antes = len(m.rede.chamadas)
    assert _dono(m, m.b, fb).codigo_produtor == "300" and _dono(m, m.a, fa).codigo_produtor == "247"
    assert len(m.rede.chamadas) == antes
    assert all(k.startswith(("comercial:" + m.a + ":", "comercial:" + m.b + ":")) for k in m.rede.cache)
    # 🔴 CONTROLE (§9.3: o guarda CONSEGUE ficar vermelho): duas fontes com o MESMO rótulo cruzam pelo cache —
    #    é exatamente o defeito que a chave `company_id:connection_id` de `_abrir` impede
    m.rede.cache.clear()
    mesma = "rotulo-que-nao-distingue"
    xa, xb = m.rede.fonte(m.a, "token-a", rotulo=mesma), m.rede.fonte(m.b, "token-b", rotulo=mesma)
    assert _dono(m, m.a, xa).codigo_produtor == "247"
    assert _dono(m, m.b, xb).codigo_produtor == "247", "CONTROLE: com o rótulo igual, a B leria o dono da A"


# ⑥ ===================================================================================================================
def test_o_vinculo_so_aceita_membro_ativo_desta_corretora(mundo):
    m = mundo
    with pytest.raises(DONO.Recusa, match="não é membro ativo"):
        DONO.vincular(m.db, m.a, user_id=m.membro_b, sistema="infocap", codigo_produtor="247")
    r1 = DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codigo_produtor="0247", nome_produtor=
                       "247 - M. PESSOA A FECHADORA")
    assert r1["ja_existia"] is False
    [linha] = [v for v in m.banco.linhas("membro_produtores") if v["company_id"] == m.a]
    assert linha["codigo_produtor"] == "247" and linha["papel_cru"] == "FECHADORA", "código sem zero; papel do nome"
    assert DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codigo_produtor=247)["ja_existia"] is True
    with pytest.raises(DONO.Recusa, match="outra pessoa"):
        DONO.vincular(m.db, m.a, user_id=m.membro_a2, sistema="infocap", codigo_produtor="247")
    # a trava do BANCO também recusa (a corrida que passa pela checagem do código)
    with pytest.raises(Exception, match="uq_membro_produtores_codigo"):
        m.db.table("membro_produtores").insert({"company_id": m.a, "user_id": m.membro_a2, "sistema": "infocap",
                                                "codigo_produtor": "247"}).execute()
    # e a FK composta recusa a pessoa de OUTRA corretora mesmo por fora do serviço
    with pytest.raises(Exception, match="fk_membro_produtores_membro"):
        m.db.table("membro_produtores").insert({"company_id": m.a, "user_id": m.membro_b, "sistema": "infocap",
                                                "codigo_produtor": "999"}).execute()
    # desvincular com o id da A, pedido pela B: zero linhas
    assert DONO.desvincular(m.db, m.b, linha["id"]) == 0
    assert DONO.desvincular(m.db, m.a, linha["id"]) == 1
    assert DONO.listar_vinculos(m.db, m.a) == []


# ⑦ ===================================================================================================================
def test_a_regua_conta_separa_e_nao_e_carimbo(mundo):
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    banco = m.rede.bancos["token-a"]
    banco["renov"] = [renov(101), renov(102), renov(103), renov(104), renov(105, cancelado="T"),
                      renov(106, tipdoc="E"), renov(101)]   # a 101 repetida conta UMA vez
    banco["prod_docs"][(1, 101)] = _quatro_produtores(101, dono_codpro=247, dono_ordem=3)
    banco["prod_docs"][(1, 102)] = _quatro_produtores(102, dono_codpro=247, dono_ordem=2)
    banco["prod_docs"][(1, 103)] = _quatro_produtores(103, dono_codpro=300, dono_ordem=1,
                                                      dono_nome="300 OUTRO PRODUTOR")
    banco["prod_docs"][(1, 104)] = [pd(104, 11, 1, "T", "UM INDICADOR")]
    DONO.vincular(m.db, m.a, user_id=m.membro_a, sistema="infocap", codigo_produtor="247")
    r = asyncio.run(DONO.medir_regra(m.db, m.a, fonte=fonte))
    assert r["status"] == "ok" and r["regra_origem"] == DONO.ORIGEM_PADRAO
    assert (r["apolices"], r["com_um_dono"], r["sem_dono"], r["ambiguas"], r["falhas"]) == (4, 3, 1, 0, 0)
    assert r["confere_com_o_padrao"] == 3
    assert r["por_papel_cru"] == {"FECHADORA": 2, "sem rótulo": 1}
    assert r["posicao_do_dono"] == {"1": 1, "2": 1, "3": 1}
    assert (r["donos_distintos"], r["donos_sem_membro"], r["apolices_sem_membro"]) == (2, 1, 1)
    assert "CLIENTE FICTICIO" not in json.dumps(r, ensure_ascii=False), "⛔ a régua nunca devolve nome de cliente"
    assert "000.000.000" not in json.dumps(r)
    # 🔴 a regra `ordem 1` (o código antigo) dá UM dono em toda apólice com produtor — `com_um_dono` sobe para 4/4 —
    #    e erra o dono: só a 103 confere com o padrão. É por isso que a régua tem `confere_com_o_padrao`.
    errada = asyncio.run(DONO.medir_regra(m.db, m.a, fonte=fonte,
                                          regra={"campo": "ordem", "igual": 1, "codigo": "codpro"}))
    assert errada["regra_origem"] == DONO.ORIGEM_INJETADA
    assert errada["com_um_dono"] == 4 and errada["confere_com_o_padrao"] == 1
    # em SÉRIE: um /prod_docs por apólice, nunca para a cancelada nem para o endosso
    pedidos = [int(c[2]["nosnum"]) for c in m.rede.chamadas if c[1] == "/prod_docs"]
    assert sorted(set(pedidos)) == [101, 102, 103, 104]
    # o limite corta e diz que cortou
    curta = asyncio.run(DONO.medir_regra(m.db, m.a, fonte=fonte, limite=2))
    assert curta["apolices"] == 2 and curta["apolices_na_janela"] == 4 and curta["limite_atingido"] is True


# ⑧ ===================================================================================================================
def test_as_sugestoes_comparam_o_nome_sem_o_papel_e_nunca_gravam(mundo):
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    m.rede.bancos["token-a"]["produtores"] = [
        {"codigo": 126, "nome": "M. MEMBRO FECHADORA"},            # → "Membro Teste"
        {"codigo": 13, "nome": "R.L.S. - FECHADOR"},               # só iniciais: nada a sugerir
        {"codigo": 247, "nome": "247 - OUTRA PESSOA INDICADORA"},  # já vinculado
        {"codigo": 155, "nome": "SEG SUL SEGUROS"},
    ]
    DONO.vincular(m.db, m.a, user_id=m.membro_a2, sistema="infocap", codigo_produtor="247")
    antes = [dict(v) for v in m.banco.linhas("membro_produtores")]
    r = asyncio.run(DONO.sugerir_vinculos(m.db, m.a, fonte=fonte))
    assert r["status"] == "ok"
    por = {p["codigo_produtor"]: p for p in r["produtores"]}
    assert por["126"]["sugestao"]["user_id"] == m.membro_a and por["126"]["papel_cru"] == "FECHADORA"
    assert por["126"]["nome_sem_papel"] == "M. MEMBRO"
    assert por["13"]["sugestao"] is None and por["13"]["papel_cru"] == "FECHADOR"
    assert por["155"]["sugestao"] is None and por["155"]["papel_cru"] is None
    assert por["247"]["vinculo"]["user_id"] == m.membro_a2 and por["247"]["sugestao"] is None
    assert [p["codigo_produtor"] for p in r["produtores"]][:2] == ["247", "126"], "vinculados, depois sugeridos"
    assert {x["user_id"] for x in r["membros"]} == {m.membro_a, m.membro_a2}, "só a equipe DESTA corretora"
    assert m.banco.linhas("membro_produtores") == antes, "⛔ sugerir nunca grava"


# ⑨ ===================================================================================================================
@pytest.fixture
def api(mundo, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import contas_da_corretora as API

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setattr(API, "get_supabase_client", lambda: SimpleNamespace(client=mundo.db))
    fontes = {mundo.a: mundo.rede.fonte(mundo.a, "token-a"), mundo.b: mundo.rede.fonte(mundo.b, "token-b")}

    async def _abrir(db, company_id):
        if company_id not in fontes:
            raise RuntimeError("sem conexão")
        return fontes[company_id]

    monkeypatch.setattr(DONO, "abrir_fonte", _abrir)
    app = FastAPI()
    app.include_router(API.router)
    return SimpleNamespace(cli=TestClient(app, raise_server_exceptions=False), m=mundo, fontes=fontes)


H = {"X-AutoBrokers-Internal-Key": CHAVE}
BASE = "/api/contas-da-corretora/sistema-de-gestao"


def test_a_rota_interna_vincula_valida_e_mede(api):
    c, m = api.cli, api.m
    assert c.get(f"{BASE}/vinculos", params={"company_id": m.a}).status_code == 401, "sem a chave interna"
    r = c.post(f"{BASE}/vincular", headers=H, json={"company_id": m.a, "user_id": m.membro_b, "sistema": "infocap",
                                                    "codigo_produtor": "247"})
    assert r.status_code == 409 and "membro ativo" in r.json()["detail"]
    r = c.post(f"{BASE}/vincular", headers=H, json={"company_id": m.a, "user_id": m.membro_a, "sistema": "infocap",
                                                    "codfil": 1, "codigo_produtor": "247",
                                                    "nome_produtor": "247 - M. MEMBRO FECHADORA"})
    assert r.status_code == 200, r.text
    vid = r.json()["id"]
    lista = c.get(f"{BASE}/vinculos", headers=H, params={"company_id": m.a}).json()
    assert [v["codigo_produtor"] for v in lista["vinculos"]] == ["247"]
    assert lista["vinculos"][0]["nome_do_membro"] == "Membro Teste" and lista["vinculos"][0]["membro_ativo"] is True
    assert c.get(f"{BASE}/vinculos", headers=H, params={"company_id": m.b}).json()["vinculos"] == []
    assert c.delete(f"{BASE}/vincular", headers=H, params={"company_id": m.b, "id": vid}).status_code == 404
    # a regra: GET diz a padrão; PUT valida a forma; PUT null volta ao padrão
    g = c.get(f"{BASE}/regra", headers=H, params={"company_id": m.a}).json()
    assert g["regra"]["origem"] == "padrao_do_sistema" and g["regra"]["campo"] == "indireto"
    ruim = c.put(f"{BASE}/regra", headers=H, json={"company_id": m.a, "sistema": "infocap",
                                                   "regra": {"campo": "ordem", "igual": 1, "codigo": "codpro",
                                                             "rota": "/documento"}})
    assert ruim.status_code == 422 and "ainda não é lida" in ruim.json()["detail"]
    ruim2 = c.put(f"{BASE}/regra", headers=H, json={"company_id": m.a, "regra": {"campo": "indireto", "igual": "F",
                                                                                 "codigo": "codpro", "dono": "x"}})
    assert ruim2.status_code == 422 and "não conheço" in ruim2.json()["detail"]
    boa = c.put(f"{BASE}/regra", headers=H, json={"company_id": m.a, "regra": {"campo": "indireto", "igual": "F",
                                                                               "codigo": "codpro"}})
    assert boa.status_code == 200 and boa.json()["regra"]["origem"] == "corretora"
    volta = c.put(f"{BASE}/regra", headers=H, json={"company_id": m.a, "regra": None})
    assert volta.json()["regra"]["origem"] == "padrao_do_sistema"
    # medir: a InfoCap DA corretora (pelo abrir_fonte) — e a corretora sem conexão recebe "sem_conexao", não 500
    api.m.rede.bancos["token-a"]["renov"] = [renov(101)]
    api.m.rede.bancos["token-a"]["prod_docs"][(1, 101)] = _quatro_produtores(101)
    med = c.post(f"{BASE}/medir", headers=H, json={"company_id": m.a}).json()
    assert (med["apolices"], med["com_um_dono"], med["apolices_sem_membro"]) == (1, 1, 0)
    outra = str(uuid4())
    assert c.post(f"{BASE}/medir", headers=H, json={"company_id": outra}).json()["status"] == "sem_conexao"
    assert c.post(f"{BASE}/medir", headers=H, json={"company_id": "nao-e-uuid"}).status_code == 400
    assert c.delete(f"{BASE}/vincular", headers=H, params={"company_id": m.a, "id": vid}).status_code == 200


# ⑩ ===================================================================================================================
def test_a_infocap_da_corretora_abre_pelo_abrir_e_nunca_por_nome(mundo, monkeypatch):
    from app.providers import infocap_analytics_provider as IAP

    m = mundo
    pedidos = []
    fonte = m.rede.fonte(m.a, "token-a")

    async def _abrir(self, *, company_id, db=None, connection_id=None, slug=None):
        pedidos.append((company_id, slug))
        return fonte, "conexao-a", "impressao", db

    def _por_nome(*_a, **_k):
        raise AssertionError("⛔ credencial por NOME de corretora (CLAUDE.md §13.9)")

    monkeypatch.setattr(IAP.InfocapAnalyticsProvider, "_abrir", _abrir)
    monkeypatch.setattr(FI.FonteInfocap, "para_empresa", classmethod(lambda cls, slug: _por_nome()))
    m.rede.bancos["token-a"]["prod_docs"][(1, NOSNUM_COMUM)] = _quatro_produtores(NOSNUM_COMUM)
    r = asyncio.run(DONO.dono_da_apolice(m.db, m.a, codfil=1, nosnum=NOSNUM_COMUM))
    assert r.codigo_produtor == "247" and pedidos == [(m.a, None)]

    async def _sem(self, **_k):
        raise IAP.FalhaDoProvider("a corretora não tem uma conexão InfoCap utilizável")

    monkeypatch.setattr(IAP.InfocapAnalyticsProvider, "_abrir", _sem)
    r2 = asyncio.run(DONO.dono_da_apolice(m.db, m.b, codfil=1, nosnum=NOSNUM_COMUM))
    assert r2.status == "sem_conexao" and r2.user_id is None


def test_a_forma_da_regra_e_recusada_com_frase_de_gente():
    with pytest.raises(DONO.Recusa):
        DONO.validar_regra(["indireto", "F"])
    with pytest.raises(DONO.Recusa, match="outro sistema"):
        DONO.validar_regra({"sistema": "quiver", "campo": "indireto", "igual": "F", "codigo": "codpro"}, "infocap")
    with pytest.raises(DONO.Recusa, match="qual campo decide"):
        DONO.validar_regra({"campo": "", "igual": "F", "codigo": "codpro"})
    ok = DONO.validar_regra({"campo": "indireto", "igual": "f", "codigo": "codpro", "_nota": "comentário cai"})
    assert ok == {"sistema": "infocap", "rota": "/prod_docs", "campo": "indireto", "igual": "F", "codigo": "codpro",
                  "nome": None, "papel_no_nome": False}
    assert DONO.papel_do_nome("17-L.G.A. – FECHADOR") == "FECHADOR"
    assert DONO.papel_do_nome("M. CONSULTORA FULANA") is None
    assert DONO.nome_sem_papel("247 - M. PESSOA A FECHADORA") == "M. PESSOA A"


def test_o_papel_escrito_no_nome_nunca_decide_o_dono(mundo):
    """§9.3 — a lição que morava no `producer-roles.<corretora>.json` (SPEC-094, M3): o rótulo da fonte (FECHADOR,
    EXECUTIVO…) é PROCEDÊNCIA, nunca veredito. Hoje: o papel cru vai para `papel_cru`; quem decide o dono é a regra."""
    m = mundo
    fonte = m.rede.fonte(m.a, "token-a")
    # o FECHADOR está desmarcado-NÃO (indireto T); o dono é um produtor SEM rótulo de papel
    m.rede.bancos["token-a"]["prod_docs"][(1, 7)] = [pd(7, 11, 1, "T", "ALGUEM FECHADOR"),
                                                     pd(7, 12, 2, "F", "ALGUEM SEM ROTULO")]
    r = _dono(m, m.a, fonte, nosnum=7)
    assert r.codigo_produtor == "12" and r.papel_cru is None
    assert not list((BACKEND / "app" / "data" / "providers" / "infocap").glob("producer-roles.*.json")), \
        "o mapa por NOME de corretora foi aposentado (§13.9) — o vínculo mora em membro_produtores"
