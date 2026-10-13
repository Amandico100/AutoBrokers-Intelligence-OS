# -*- coding: utf-8 -*-
"""SPEC-131-B G3 — Meu perfil (o WhatsApp de trabalho, a ausência), a SITUAÇÃO de cada pessoa em Equipe e a aba
Configurar da Renovação gravando pela config que JÁ existe.

O que se prova, sempre pelo SERVIÇO real (CLAUDE.md §9.4 — `perfil_do_membro`, `config.erros_da_edicao`,
`servicos_da_corretora.gravar/retrato`, o router real com a chave interna):
  · WhatsApp de trabalho (D-131-41): E.164; só a PRÓPRIA pessoa grava o dela (nem o admin); exige a confirmação; grava
    no MEMBRO desta corretora (a mesma pessoa noutra corretora não muda); ⛔ nada em `integrations`
  · ausência (D-131-08): OUTRA pessoa, ativa, da MESMA corretora; período válido; sem sobreposição; quem pede é a pessoa
    ou o admin; apagar só o que é desta corretora
  · isolamento (§7): DUAS corretoras com a MESMA pessoa nas duas — nada atravessa; o número nunca sai na situação
  · Configurar: opções 1–3, teto por conta por noite e antecipação passam a ser editáveis (as chaves que a madrugada
    lê); econômica/mínima e número fora da faixa são RECUSADOS
⛔ Nomes fictícios (§13.9): corretora_a/corretora_b, pessoa_a1… Nenhum telefone real (o número de teste é inventado).
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import date
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services import perfil_do_membro as P  # noqa: E402

A = "a131b000-0000-4000-8000-00000000000a"          # corretora_a
B = "b131b000-0000-4000-8000-00000000000b"          # corretora_b
A1 = "a131b000-0000-4000-8000-0000000000a1"         # pessoa_a1 (comercial; TAMBÉM membro da corretora_b)
A2 = "a131b000-0000-4000-8000-0000000000a2"         # pessoa_a2 (comercial)
ADM = "a131b000-0000-4000-8000-0000000000ad"        # admin da corretora_a
SAIU = "a131b000-0000-4000-8000-0000000000a9"       # saiu da corretora_a (vínculo inativo)
B1 = "b131b000-0000-4000-8000-0000000000b1"         # pessoa_b1 (só da corretora_b)
HOJE = date(2026, 10, 14)
NUMERO = "+5511912345678"                           # 💭 inventado
NUMERO_B = "+5521987654321"                         # 💭 inventado


# =====================================================================================================================
# o banco dublê — PostgREST mínimo, que aplica SÓ os filtros pedidos (esquecer o company_id = vazar)
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.lim, self.op, self.valor = [], None, "select", None

    @property
    def not_(self):
        self._negar = True
        return self

    def select(self, colunas="*"):
        if self.tabela in self.banco.tabelas_ausentes:
            raise RuntimeError(f"relation {self.tabela} does not exist")
        if any(c.strip() in self.banco.colunas_ausentes.get(self.tabela, ()) for c in colunas.split(",")):
            raise RuntimeError(f"column {self.tabela} does not exist")
        return self

    def eq(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: l.get(c) == v)
        return self

    def in_(self, c, vs):
        self.filtros.append(lambda l, c=c, vs=tuple(vs): l.get(c) in vs)
        return self

    def lte(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c)) <= v)
        return self

    def gte(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c)) >= v)
        return self

    def is_(self, c, v):
        assert v == "null" and getattr(self, "_negar", False)
        self.filtros.append(lambda l, c=c: l.get(c) is not None)
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.lim = n
        return self

    def insert(self, linha):
        self.op, self.valor = "insert", dict(linha)
        return self

    def update(self, patch):
        self.op, self.valor = "update", dict(patch)
        return self

    def delete(self):
        self.op = "delete"
        return self

    def execute(self):
        linhas = self.banco.tabelas.setdefault(self.tabela, [])
        casam = [l for l in linhas if all(f(l) for f in self.filtros)]
        if self.op == "insert":
            nova = {"id": f"{len(linhas) + 1:08d}-0000-4000-8000-000000000000", **self.valor}
            linhas.append(nova)
            self.banco.escritas.append((self.tabela, "insert", copy.deepcopy(nova)))
            return _Resp([copy.deepcopy(nova)])
        if self.op == "update":
            for l in casam:
                l.update(copy.deepcopy(self.valor))
                self.banco.escritas.append((self.tabela, "update", copy.deepcopy(l)))
            return _Resp(copy.deepcopy(casam))
        if self.op == "delete":
            for l in casam:
                linhas.remove(l)
                self.banco.escritas.append((self.tabela, "delete", copy.deepcopy(l)))
            return _Resp(copy.deepcopy(casam))
        return _Resp(copy.deepcopy(casam[: self.lim] if self.lim else casam))


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: [dict(l) for l in v] for k, v in tabelas.items()}
        self.escritas = []
        self.tabelas_ausentes, self.colunas_ausentes = set(), {}

    def table(self, nome):
        return _Consulta(self, nome)


def _membro(cid, uid, *, role="member", status="active", owner=False, **extra):
    return {"company_id": cid, "user_id": uid, "role": role, "status": status, "is_owner": owner, "funcoes": [],
            "whatsapp_trabalho_e164": None, "whatsapp_trabalho_confirmado_em": None, **extra}


def _usuario(uid, nome):
    primeiro, _, resto = nome.partition(" ")
    return {"id": uid, "first_name": primeiro, "last_name": resto, "status": "active", "deleted_at": None}


def banco_de_duas_corretoras() -> Banco:
    return Banco(
        company_members=[
            _membro(A, A1, funcoes=["comercial"]), _membro(A, A2, funcoes=["comercial"]),
            _membro(A, ADM, role="admin"), _membro(A, SAIU, status="inactive"),
            # a MESMA pessoa_a1 também é da corretora_b — com o número DELA lá
            _membro(B, A1, whatsapp_trabalho_e164=NUMERO_B, whatsapp_trabalho_confirmado_em="2026-10-01T10:00:00+00:00"),
            _membro(B, B1),
        ],
        users_v2=[_usuario(A1, "Pessoa Aum"), _usuario(A2, "Pessoa Adois"), _usuario(ADM, "Admin Acorretora"),
                  _usuario(SAIU, "Pessoa Saiu"), _usuario(B1, "Pessoa Bum")],
        membro_ausencias=[
            # uma ausência da corretora_b, ATIVA hoje, com o mesmo user_id (pessoa_a1) — não pode aparecer na A
            {"id": "bbbbbbbb-0000-4000-8000-000000000001", "company_id": B, "user_id": A1, "substituto_user_id": B1,
             "de": "2026-10-10", "ate": "2026-10-20"},
        ],
        portal_accounts=[], multicalculo_calculos=[], integrations=[],
    )


def _linha(banco, cid, uid):
    return next(m for m in banco.tabelas["company_members"] if m["company_id"] == cid and m["user_id"] == uid)


# =====================================================================================================================
# 1. o WhatsApp de trabalho (D-131-41)
# =====================================================================================================================
@pytest.mark.parametrize("entrada,esperado", [
    ("(11) 9 1234-5678", NUMERO), ("11912345678", NUMERO), ("+55 11 91234-5678", NUMERO), ("5511912345678", NUMERO),
    ("(11) 3123-4567", "+551131234567"),                          # fixo com WhatsApp Business (8 dígitos)
])
def test_o_numero_vira_e164(entrada, esperado):
    assert P.normalizar_whatsapp(entrada) == esperado


# §9.3 (conserto K1, RT-P3/J-P3): "+351 …" era aceito e o CHECK do banco o recusava (500). A regra do Python agora É a
# do CHECK (+55, fixo 2–5): o número de outro país vira recusa com a frase de correção
@pytest.mark.parametrize("entrada", ["", "abc", "123", "(01) 91234-5678", "(11) 8123-45678", "+0011912345678",
                                     "+55 11 91234-567890", "+351 912 345 678"])
def test_numero_que_nao_e_whatsapp_e_recusado(entrada):
    with pytest.raises(P.Recusa):
        P.normalizar_whatsapp(entrada)


def test_a_pessoa_grava_o_dela_no_membro_desta_corretora_e_a_outra_corretora_nao_muda():
    banco = banco_de_duas_corretoras()
    r = P.gravar_whatsapp_trabalho(banco, A, A1, numero="(11) 9 1234-5678", confirmo=True, por_user_id=A1)
    assert r["numero"] == NUMERO and r["confirmado"] is True
    assert _linha(banco, A, A1)["whatsapp_trabalho_e164"] == NUMERO
    assert _linha(banco, A, A1)["whatsapp_trabalho_confirmado_em"]
    # 🔴 a MESMA pessoa na corretora_b: o número de lá ficou como estava (o filtro é company_id + user_id)
    assert _linha(banco, B, A1)["whatsapp_trabalho_e164"] == NUMERO_B
    # ⛔ nenhum pareamento: nada em integrations, e só UMA linha escrita
    assert banco.tabelas["integrations"] == []
    assert [(t, op) for t, op, _ in banco.escritas] == [("company_members", "update")]


def test_so_a_propria_pessoa_grava_nem_o_admin_e_a_confirmacao_e_obrigatoria():
    banco = banco_de_duas_corretoras()
    with pytest.raises(P.Recusa, match="própria pessoa"):
        P.gravar_whatsapp_trabalho(banco, A, A1, numero=NUMERO, confirmo=True, por_user_id=ADM)
    with pytest.raises(P.Recusa, match="Confirme"):
        P.gravar_whatsapp_trabalho(banco, A, A1, numero=NUMERO, confirmo=False, por_user_id=A1)
    with pytest.raises(P.Recusa, match="Confirme"):
        P.gravar_whatsapp_trabalho(banco, A, A1, numero=NUMERO, confirmo="sim", por_user_id=A1)   # só True vale
    with pytest.raises(P.Recusa, match="ativo"):
        P.gravar_whatsapp_trabalho(banco, A, SAIU, numero=NUMERO, confirmo=True, por_user_id=SAIU)
    with pytest.raises(P.Recusa, match="ativo"):                       # pessoa da B pedindo na A: não é membro de A
        P.gravar_whatsapp_trabalho(banco, A, B1, numero=NUMERO, confirmo=True, por_user_id=B1)
    assert banco.escritas == []
    # CONTROLE: o mesmo pedido, pela própria pessoa e confirmado, passa (o guarda PODE ficar verde)
    P.gravar_whatsapp_trabalho(banco, A, A1, numero=NUMERO, confirmo=True, por_user_id=A1)
    assert len(banco.escritas) == 1


def test_remover_apaga_so_o_desta_corretora():
    banco = banco_de_duas_corretoras()
    P.gravar_whatsapp_trabalho(banco, A, A1, numero=NUMERO, confirmo=True, por_user_id=A1)
    P.remover_whatsapp_trabalho(banco, A, A1, por_user_id=A1)
    assert _linha(banco, A, A1)["whatsapp_trabalho_e164"] is None
    assert _linha(banco, B, A1)["whatsapp_trabalho_e164"] == NUMERO_B
    with pytest.raises(P.Recusa):
        P.remover_whatsapp_trabalho(banco, A, A1, por_user_id=ADM)


# =====================================================================================================================
# 2. a ausência (D-131-08)
# =====================================================================================================================
def _criar(banco, **kw):
    base = dict(user_id=A1, substituto_user_id=A2, de="2026-10-20", ate="2026-10-30", por_user_id=A1, hoje=HOJE)
    base.update(kw)
    return P.criar_ausencia(banco, A, **base)


def test_a_ausencia_valida_grava_com_a_corretora_e_quem_criou():
    banco = banco_de_duas_corretoras()
    r = _criar(banco)
    assert r["company_id"] == A and r["user_id"] == A1 and r["substituto_user_id"] == A2 and r["criado_por"] == A1
    gravadas = [a for a in banco.tabelas["membro_ausencias"] if a["company_id"] == A]
    assert len(gravadas) == 1 and gravadas[0]["id"] == r["id"]
    assert (gravadas[0]["de"], gravadas[0]["ate"]) == ("2026-10-20", "2026-10-30")


@pytest.mark.parametrize("kw,frase", [
    ({"substituto_user_id": A1}, "OUTRA pessoa"),                                 # a própria pessoa
    ({"substituto_user_id": B1}, "ativa da equipe desta corretora"),              # de OUTRA corretora
    ({"substituto_user_id": SAIU}, "ativa da equipe desta corretora"),            # saiu da equipe
    ({"de": "2026-10-30", "ate": "2026-10-20"}, "antes do dia de saída"),          # período invertido
    ({"de": "2026-10-01", "ate": "2026-10-05"}, "já passou"),                     # todo no passado
    ({"de": "2026-10-20", "ate": "2027-10-20"}, "até 180 dias"),                  # longo demais
    ({"de": "20/10/2026"}, "inválida"),                                           # data fora do ISO
    ({"user_id": SAIU, "por_user_id": SAIU}, "não está ativa"),                   # dono fora da equipe
    ({"por_user_id": A2}, "administrador"),                                       # colega marcando a de outra pessoa
])
def test_a_ausencia_invalida_e_recusada_e_nada_e_gravado(kw, frase):
    banco = banco_de_duas_corretoras()
    antes = copy.deepcopy(banco.tabelas["membro_ausencias"])
    with pytest.raises(P.Recusa, match=frase):
        _criar(banco, **kw)
    assert banco.tabelas["membro_ausencias"] == antes


def test_o_admin_marca_a_de_outra_pessoa_e_a_sobreposicao_e_recusada():
    banco = banco_de_duas_corretoras()
    _criar(banco, por_user_id=ADM)                                                # o admin pode
    with pytest.raises(P.Recusa, match="Já existe"):
        _criar(banco, de="2026-10-25", ate="2026-11-05")                          # sobrepõe a de 20–30/10
    # 🔴 a ausência da MESMA pessoa na corretora_b (10–20/10) não conta como sobreposição na A
    _criar(banco, de="2026-11-01", ate="2026-11-03")
    assert len([a for a in banco.tabelas["membro_ausencias"] if a["company_id"] == A]) == 2


def test_apagar_so_a_desta_corretora_e_so_quem_pode():
    banco = banco_de_duas_corretoras()
    r = _criar(banco)
    with pytest.raises(P.Recusa, match="não existe nesta corretora"):            # o id da B, pedido pela A
        P.apagar_ausencia(banco, A, ausencia_id="bbbbbbbb-0000-4000-8000-000000000001", por_user_id=ADM)
    with pytest.raises(P.Recusa, match="administrador"):
        P.apagar_ausencia(banco, A, ausencia_id=r["id"], por_user_id=A2)
    P.apagar_ausencia(banco, A, ausencia_id=r["id"], por_user_id=A1)
    assert [a["company_id"] for a in banco.tabelas["membro_ausencias"]] == [B]    # a da B ficou


# =====================================================================================================================
# 3. as leituras — duas corretoras, a mesma pessoa nas duas
# =====================================================================================================================
def test_o_perfil_le_so_a_corretora_da_sessao():
    banco = banco_de_duas_corretoras()
    _criar(banco)
    na_a = P.ler_perfil(banco, A, A1, hoje=HOJE)
    na_b = P.ler_perfil(banco, B, A1, hoje=HOJE)
    assert na_a["whatsapp_trabalho"]["numero"] is None and na_b["whatsapp_trabalho"]["numero"] == NUMERO_B
    assert [x["user_id"] for x in na_a["ausencias"]] == [A2]                      # só a da A (a da B não)
    assert [x["user_id"] for x in na_b["ausencias"]] == [B1] and na_b["ausencias"][0]["ativa"] is True
    # a lista para escolher quem cobre: OUTRAS pessoas ATIVAS DESTA corretora (nem eu, nem quem saiu, nem a B)
    assert {p["user_id"] for p in na_a["pessoas"]} == {A2, ADM}
    assert {p["user_id"] for p in na_b["pessoas"]} == {B1}
    # quem cobre vê que cobre
    assert [x["user_id"] for x in P.ler_perfil(banco, A, A2, hoje=HOJE)["cubro"]] == [A1]


def test_a_situacao_da_equipe_nao_atravessa_e_nunca_mostra_o_numero():
    banco = banco_de_duas_corretoras()
    P.gravar_whatsapp_trabalho(banco, A, A2, numero=NUMERO, confirmo=True, por_user_id=A2)
    _criar(banco, de="2026-10-14", ate="2026-10-16")                              # ativa HOJE
    sa = P.situacao_da_equipe(banco, A, hoje=HOJE)
    sb = P.situacao_da_equipe(banco, B, hoje=HOJE)
    por = {p["user_id"]: p for p in sa["pessoas"]}
    assert set(por) == {A1, A2, ADM}                                              # sem quem saiu, sem a B
    assert por[A2]["whatsapp_trabalho_confirmado"] is True and por[A1]["whatsapp_trabalho_confirmado"] is False
    assert por[A1]["ausencia"] == {"ate": "2026-10-16", "substituto": "Pessoa"}
    assert por[A2]["ausencia"] is None and por[A1]["agger"]["situacao"] == "nao_conectado"
    # na B, a pessoa_a1 tem o número confirmado e a ausência DE LÁ — e nada da A
    por_b = {p["user_id"]: p for p in sb["pessoas"]}
    assert set(por_b) == {A1, B1} and por_b[A1]["whatsapp_trabalho_confirmado"] is True
    assert por_b[A1]["ausencia"]["ate"] == "2026-10-20"
    # ⛔ o número nunca sai da situação (só sim/não)
    for corpo in (sa, sb):
        texto = json.dumps(corpo, ensure_ascii=False)
        assert NUMERO not in texto and NUMERO_B not in texto and "912345678" not in texto


def test_sem_as_colunas_da_migration_a_tela_abre_mesmo_assim():
    banco = banco_de_duas_corretoras()
    banco.colunas_ausentes["company_members"] = {"whatsapp_trabalho_e164"}
    banco.tabelas_ausentes.add("membro_ausencias")
    perfil = P.ler_perfil(banco, A, A1, hoje=HOJE)
    assert perfil["whatsapp_trabalho"]["disponivel"] is False and perfil["ausencia_disponivel"] is False
    s = P.situacao_da_equipe(banco, A, hoje=HOJE)
    assert {p["whatsapp_trabalho_confirmado"] for p in s["pessoas"]} == {None}


# =====================================================================================================================
# 4. a aba Configurar grava pela config que JÁ existe (o backend de Serviços, a mesma rota)
# =====================================================================================================================
def test_configurar_edita_as_chaves_da_madrugada_e_recusa_o_proibido():
    from app.services.multicalculo import config as CFG

    ok = {"renovacao": {"opcoes": ["anterior", "franquia_reduzida"], "teto_por_conta_noite": 20,
                        "antecipar_ate_dias": 0}}
    assert CFG.erros_da_edicao(ok) == []
    for ruim in ({"opcoes": ["anterior", "economica"]}, {"opcoes": []}, {"opcoes": ["anterior", "anterior"]},
                 {"opcoes": ["anterior", "franquia_reduzida", "completa_mais", "minima"]},
                 {"teto_por_conta_noite": 0}, {"teto_por_conta_noite": 61}, {"teto_por_conta_noite": 2.5},
                 {"antecipar_ate_dias": 21}, {"antecipar_ate_dias": -1}):
        assert CFG.erros_da_edicao({"renovacao": ruim}), ruim
    # ⛔ a cotação não ganhou as chaves da renovação; o aceite do Prosseguir segue fora da tela
    assert CFG.erros_da_edicao({"cotacao": {"opcoes": ["anterior"]}})
    assert CFG.erros_da_edicao({"renovacao": {"prosseguir_aceites": []}})


def test_o_que_a_tela_grava_volta_pelo_retrato_e_a_madrugada_le_o_mesmo():
    from app.api import servicos_da_corretora as S
    from app.services.multicalculo import config as CFG
    import test_spec1310_f4_servicos as F4S

    banco = F4S.Banco(multicalculo_config=[{"company_id": F4S.A, "atualizado_em": "v1", "config": {}}],
                      multicalculo_adesoes=[])
    antes = S.retrato(banco, F4S.A)
    assert antes["efetivo"]["renovacao"]["opcoes"] == list(CFG.PADRAO_DO_PRODUTO["servicos"]["renovacao"]["opcoes"])
    assert antes["faixas"]["teto_por_conta_noite"] == list(CFG.TETO_POR_CONTA_NOITE_FAIXA)
    assert antes["faixas"]["opcoes_da_renovacao"][0] == "anterior"
    depois = S.gravar(banco, F4S.A, versao="v1", servicos={"renovacao": {
        "modo": "calcular", "excecoes_do_modo": [], "opcoes": ["anterior"], "teto_por_conta_noite": 30,
        "antecipar_ate_dias": 3, "renovacao": {"antecedencia_dias": 15}}})
    efe = depois["efetivo"]["renovacao"]
    assert (efe["opcoes"], efe["teto_por_conta_noite"], efe["antecipar_ate_dias"], efe["antecedencia_dias"]) == (
        ["anterior"], 30, 3, 15)
    # o MESMO leitor da madrugada vê o que a tela gravou
    cfg = CFG.mesclar(banco.tabelas["multicalculo_config"][0]["config"], "renovacao")
    assert CFG.opcoes_da_renovacao(cfg) == ("anterior",) and CFG.teto_por_conta_noite(cfg) == 30
    assert CFG.antecipar_ate_dias(cfg) == 3 and CFG.antecedencia_dias(cfg) == 15
    # a outra corretora não tem linha nenhuma
    assert [l["company_id"] for l in banco.tabelas["multicalculo_config"]] == [F4S.A]


# =====================================================================================================================
# 5. o router: monta, exige a chave interna, devolve a frase da recusa
# =====================================================================================================================
def test_as_rotas_do_perfil_montam_e_exigem_a_chave(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api import contas_da_corretora as CONTAS

    banco = banco_de_duas_corretoras()
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste")
    monkeypatch.setattr(CONTAS, "_db", lambda: banco)
    app = FastAPI()
    app.include_router(CONTAS.router)
    c = TestClient(app)
    h = {"X-AutoBrokers-Internal-Key": "chave-de-teste"}
    assert c.get(f"/api/contas-da-corretora/perfil?company_id={A}&user_id={A1}").status_code == 401
    assert c.get(f"/api/contas-da-corretora/perfil?company_id={A}&user_id={A1}", headers=h).status_code == 200
    r = c.put("/api/contas-da-corretora/perfil/whatsapp-de-trabalho", headers=h,
              json={"company_id": A, "user_id": A1, "por_user_id": ADM, "numero": NUMERO, "confirmo": True})
    assert r.status_code == 422 and "própria pessoa" in r.json()["detail"]
    r = c.post("/api/contas-da-corretora/perfil/ausencias", headers=h,
               json={"company_id": A, "user_id": A1, "por_user_id": A1, "substituto_user_id": A1,
                     "de": "2099-01-01", "ate": "2099-01-02"})
    assert r.status_code == 422 and "OUTRA" in r.json()["detail"]
    s = c.get(f"/api/contas-da-corretora/equipe/situacao?company_id={B}", headers=h)
    assert s.status_code == 200 and {p["user_id"] for p in s.json()["pessoas"]} == {A1, B1}
