# -*- coding: utf-8 -*-
"""SPEC-132-C C1 — a verificação do "Meu WhatsApp de trabalho" por POSSE (D-132C-02).

Tudo pelo MOTOR real (CLAUDE.md §9.4): `atalho.verificacao` (gerar, consumir, quem é este telefone),
`perfil_do_membro` (trocar o número APAGA a verificação) e o router real com a chave interna. Dublê só na borda: o
banco (PostgREST mínimo que aplica SÓ os filtros pedidos — esquecer o company_id = vazar) e o segredo do HMAC (env).

Mutações da régua (§6) que estes testes têm de pegar:
  (2) código usado 2×                 → `test_codigo_e_de_uso_unico`
  (3) código de A vincula membro de B → `test_o_membro_vinculado_e_sempre_o_do_codigo_*`
Conserto único (laudos JUIZ/RED-TEAM-132-C) — `python tests/test_spec132c_verificacao.py --mutar` (por cópia):
  V-P1  o código vale de qualquer celular → `test_o_codigo_de_outro_celular_*`
  V-G   sem teto global                   → `test_o_teto_global_*`
  V-D   gera com o número não declarado   → `test_gerar_exige_*`
  V-L   o perfil oferece com o atalho desligado → `test_desligado_*`
O código AMARRA o número declarado: todo membro que ATIVA tem o número salvo e confirmado no Meu perfil.
⛔ Nomes fictícios (§13.9): corretora_a/corretora_b, pessoa_a1… Telefones inventados.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import subprocess  # noqa: E402

from app.services import perfil_do_membro as P  # noqa: E402
from app.services.atalho import verificacao as V  # noqa: E402

A = "a132c000-0000-4000-8000-00000000000a"          # corretora_a
B = "b132c000-0000-4000-8000-00000000000b"          # corretora_b
CANAL = "c132c000-0000-4000-8000-00000000000c"      # a empresa da PLATAFORMA (company_kind=platform_canal)
A1 = "a132c000-0000-4000-8000-0000000000a1"         # pessoa_a1 — TAMBÉM membro da corretora_b
A2 = "a132c000-0000-4000-8000-0000000000a2"         # pessoa_a2
SAIU = "a132c000-0000-4000-8000-0000000000a9"       # vínculo inativo na corretora_a
B1 = "b132c000-0000-4000-8000-0000000000b1"         # pessoa_b1 (só da corretora_b)
CEL_A1 = "+5511912345678"                           # 💭 inventado
CEL_A2 = "+5511987654321"                           # 💭 inventado
CEL_B1 = "+5521998765432"                           # 💭 inventado
ASSISTENTE = "5511955554444"                        # 💭 inventado — o número do AutoBrokers
T0 = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)


# =====================================================================================================================
# o banco dublê
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class ViolacaoUnica(Exception):
    pass


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.lim, self.op, self.valor, self._negar = [], None, "select", None, False
        self.colunas_filtradas = []

    @property
    def not_(self):
        self._negar = True
        return self

    def select(self, colunas="*"):
        return self

    def eq(self, c, v):
        self.colunas_filtradas.append(c)
        self.filtros.append(lambda l, c=c, v=v: l.get(c) == v)
        return self

    def in_(self, c, vs):
        self.filtros.append(lambda l, c=c, vs=tuple(vs): l.get(c) in vs)
        return self

    def gte(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c)) >= v)
        return self

    def is_(self, c, v):
        assert v == "null"
        if self._negar:
            self.filtros.append(lambda l, c=c: l.get(c) is not None)
        else:
            self.filtros.append(lambda l, c=c: l.get(c) is None)
        self._negar = False
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

    def execute(self):
        linhas = self.banco.tabelas.setdefault(self.tabela, [])
        casam = [l for l in linhas if all(f(l) for f in self.filtros)]
        if self.op == "insert":
            nova = {"id": f"{len(linhas) + 1:08d}-0000-4000-8000-000000000000", "usado_em": None,
                    "invalidado_em": None, **self.valor} if self.tabela == V.TABELA_CODIGOS else \
                {"id": f"{len(linhas) + 1:08d}-0000-4000-8000-000000000000", **self.valor}
            self.banco.conferir_unicos(self.tabela, linhas + [nova])
            linhas.append(nova)
            self.banco.escritas.append((self.tabela, "insert", copy.deepcopy(nova)))
            return _Resp([copy.deepcopy(nova)])
        if self.op == "update":
            depois = [dict(l, **self.valor) if l in casam else l for l in linhas]
            self.banco.conferir_unicos(self.tabela, depois)
            for l in casam:
                l.update(copy.deepcopy(self.valor))
                self.banco.escritas.append((self.tabela, "update", copy.deepcopy(l)))
            return _Resp(copy.deepcopy(casam))
        return _Resp(copy.deepcopy(casam[: self.lim] if self.lim else casam))


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: [dict(l) for l in v] for k, v in tabelas.items()}
        self.escritas = []

    def table(self, nome):
        return _Consulta(self, nome)

    def conferir_unicos(self, tabela, linhas):
        """Os índices únicos da migration 20261014_03 — o banco também recusa (o cinto do Python não é a única porta)."""
        if tabela == V.TABELA_CODIGOS:
            ativos = [(l["company_id"], l["user_id"]) for l in linhas
                      if l.get("usado_em") is None and l.get("invalidado_em") is None]
            if len(ativos) != len(set(ativos)):
                raise ViolacaoUnica("duplicate key value violates unique constraint uq_whatsapp_atalho_codigo_ativo")
        if tabela == "company_members":
            vs = [(l["company_id"], l["whatsapp_trabalho_e164"]) for l in linhas
                  if l.get("whatsapp_trabalho_verificado_em")]
            if len(vs) != len(set(vs)):
                raise ViolacaoUnica("duplicate key value violates unique constraint "
                                    "uq_company_members_whatsapp_verificado")


def _membro(cid, uid, *, status="active", **extra):
    return {"company_id": cid, "user_id": uid, "role": "member", "status": status, "is_owner": False,
            "whatsapp_trabalho_e164": None, "whatsapp_trabalho_confirmado_em": None,
            "whatsapp_trabalho_verificado_em": None, **extra}


def _declarado(cel):
    return {"whatsapp_trabalho_e164": cel, "whatsapp_trabalho_confirmado_em": T0.isoformat()}


def _usuario(uid, nome):
    primeiro, _, resto = nome.partition(" ")
    return {"id": uid, "first_name": primeiro, "last_name": resto, "status": "active", "deleted_at": None}


def banco(com_assistente=True) -> Banco:
    return Banco(
        companies=[{"id": A, "company_name": "Corretora Alfa", "company_kind": "client"},
                   {"id": B, "company_name": "Corretora Beta", "company_kind": "client"},
                   {"id": CANAL, "company_name": "AutoBrokers Canal", "company_kind": "platform_canal"}],
        # o número DECLARADO e confirmado no Meu perfil (o código só vale mandado dele — conserto P1)
        company_members=[_membro(A, A1, **_declarado(CEL_A1)), _membro(A, A2, **_declarado(CEL_A2)),
                         _membro(A, SAIU, status="inactive"), _membro(B, A1), _membro(B, B1, **_declarado(CEL_B1))],
        users_v2=[_usuario(A1, "Pessoa Aum"), _usuario(A2, "Pessoa Adois"), _usuario(SAIU, "Pessoa Saiu"),
                  _usuario(B1, "Pessoa Bum")],
        integrations=([{"company_id": CANAL, "purpose": "assistente", "is_active": True,
                        "paired_phone_e164": "+" + ASSISTENTE, "channel_status": "connected"}]
                      if com_assistente else []),
        whatsapp_atalho_codigos=[], whatsapp_atalho_tentativas=[],
    )


@pytest.fixture(autouse=True)
def _segredo(monkeypatch):
    for nome in V.ENVS_DO_SEGREDO:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.delenv(V.ENV_DO_NUMERO, raising=False)
    monkeypatch.setenv("ATALHO_CODIGO_SEGREDO", "segredo-de-teste-132c")
    monkeypatch.setenv("ATALHO_WHATSAPP_LIGADO", "1")


def _linha(b, cid, uid):
    return next(m for m in b.tabelas["company_members"] if m["company_id"] == cid and m["user_id"] == uid)


def consumir(b, telefone, texto, agora=None):
    return asyncio.run(V.consumir_codigo(b, telefone_remetente_e164=telefone, texto=texto, agora=agora or T0))


def gerar(b, cid, uid, agora=None):
    return V.gerar_codigo(b, company_id=cid, user_id=uid, agora=agora or T0)


# =====================================================================================================================
# 1. o código: aleatório, só o hash, 15 min, wa.me
# =====================================================================================================================
def test_o_codigo_tem_6_digitos_vale_15_min_e_so_o_hash_e_gravado(caplog):
    b = banco()
    with caplog.at_level(logging.DEBUG):
        r = gerar(b, A, A1)
    assert len(r["codigo"]) == 6 and r["codigo"].isdigit() and r["texto"] == f"ATIVAR {r['codigo']}"
    assert r["expira_em"] == (T0 + timedelta(minutes=15)).isoformat() and r["validade_minutos"] == 15
    assert r["numero_assistente"] == ASSISTENTE
    assert r["wa_me_url"] == f"https://wa.me/{ASSISTENTE}?text=ATIVAR%20{r['codigo']}"
    [linha] = b.tabelas[V.TABELA_CODIGOS]
    # 🔴 o código em claro NUNCA é gravado: só o HMAC (64 hex), e nenhuma coluna guarda o código
    assert linha["codigo_hash"] == V.hash_do_codigo(r["codigo"]) and len(linha["codigo_hash"]) == 64
    assert r["codigo"] not in [str(v) for v in linha.values()]
    assert (linha["company_id"], linha["user_id"]) == (A, A1)
    # ⛔ nem no log
    assert r["codigo"] not in caplog.text
    # CONTROLE (o guarda PODE ficar vermelho): o hash de outro código é outro
    assert V.hash_do_codigo("000000") != V.hash_do_codigo("000001")


def test_o_hash_depende_do_segredo_da_aplicacao(monkeypatch):
    h1 = V.hash_do_codigo("123456")
    monkeypatch.setenv("ATALHO_CODIGO_SEGREDO", "outro-segredo")
    assert V.hash_do_codigo("123456") != h1           # sha256 puro do código seria quebrável com 10⁶ tentativas


def test_sem_segredo_nao_gera_codigo_e_a_ativacao_cala(monkeypatch):
    b = banco()
    monkeypatch.delenv("ATALHO_CODIGO_SEGREDO")
    with pytest.raises(V.Recusa, match="ainda não está disponível"):
        gerar(b, A, A1)
    assert b.tabelas[V.TABELA_CODIGOS] == []
    r = consumir(b, CEL_A1, "ATIVAR 123456")
    assert not r.ok and not r.responder and r.motivo == "sem_segredo"


def test_sem_numero_do_assistente_o_codigo_sai_sem_link_e_o_perfil_diz_que_nao_esta_ligado():
    b = banco(com_assistente=False)
    r = gerar(b, A, A1)
    assert r["wa_me_url"] is None and r["numero_assistente"] is None
    assert P.ler_perfil(b, A, A1)["atalho_whatsapp"] == {"disponivel": False}


def test_o_numero_do_assistente_e_so_o_da_plataforma_e_o_env_e_o_reserva(monkeypatch):
    b = banco(com_assistente=False)
    # uma CORRETORA com uma integração purpose=assistente não vira o número do AutoBrokers
    b.tabelas["integrations"].append({"company_id": A, "purpose": "assistente", "is_active": True,
                                      "paired_phone_e164": "+5511900001111", "channel_status": "connected"})
    assert V.numero_do_assistente(b) is None
    monkeypatch.setenv(V.ENV_DO_NUMERO, "+55 11 95555-4444")
    assert V.numero_do_assistente(b) == ASSISTENTE
    # e a integração da PLATAFORMA vence o env
    monkeypatch.setenv(V.ENV_DO_NUMERO, "5511900002222")
    assert V.numero_do_assistente(banco()) == ASSISTENTE


def test_so_membro_ativo_pede_codigo_e_o_teto_por_hora():
    b = banco()
    with pytest.raises(V.Recusa, match="ativo"):
        gerar(b, A, SAIU)
    with pytest.raises(V.Recusa, match="ativo"):
        gerar(b, A, B1)                                  # pessoa da B pedindo na A
    for i in range(V.TETO_DE_CODIGOS_POR_HORA):
        gerar(b, A, A1, agora=T0 + timedelta(minutes=i))
    with pytest.raises(V.Recusa, match="última hora"):
        gerar(b, A, A1, agora=T0 + timedelta(minutes=10))
    # passada a hora, volta a poder
    gerar(b, A, A1, agora=T0 + timedelta(minutes=70))


def test_pedir_outro_codigo_invalida_o_anterior():
    b = banco()
    velho = gerar(b, A, A1)["codigo"]
    novo = gerar(b, A, A1, agora=T0 + timedelta(minutes=1))["codigo"]
    if velho == novo:
        pytest.skip("sorteio repetiu o código (1 em 10⁶)")
    r = consumir(b, CEL_A1, f"ATIVAR {velho}", agora=T0 + timedelta(minutes=2))
    assert not r.ok and r.motivo == "codigo_invalido" and not r.responder
    assert consumir(b, CEL_A1, f"ATIVAR {novo}", agora=T0 + timedelta(minutes=2)).ok


@pytest.mark.parametrize("texto,esperado", [
    ("ATIVAR 123456", "123456"), ("ativar 123456", "123456"), ("  Ativar   123456  ", "123456"),
    ("ATIVAR 123 456", "123456"), ("*ATIVAR 123456*", "123456"), ("ATIVAR: 123456.", "123456"),
    ("ATIVAR123456", "123456"),
    ("ATIVAR 12345", None), ("ATIVAR 1234567", None), ("quero ATIVAR 123456", None), ("123456", None),
    ("ATIVAR abcdef", None), ("", None), (None, None),
])
def test_a_mensagem_de_ativacao_tolera_caixa_e_espacos(texto, esperado):
    assert V.codigo_da_ativacao(texto) == esperado


# =====================================================================================================================
# 2. consumir: a posse grava o número do REMETENTE no membro DO CÓDIGO
# =====================================================================================================================
def test_o_fio_da_verificacao_ativa_grava_e_responde_pronto():
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    r = consumir(b, CEL_A1, f"ATIVAR {codigo}", agora=T0 + timedelta(minutes=3))
    assert r.ok and r.responder and (r.company_id, r.user_id) == (A, A1) and r.nome == "Pessoa Aum"
    assert r.mensagem.startswith("Pronto, Pessoa!") and "Corretora Alfa" in r.mensagem
    m = _linha(b, A, A1)
    assert m["whatsapp_trabalho_e164"] == CEL_A1
    assert m["whatsapp_trabalho_verificado_em"] == (T0 + timedelta(minutes=3)).isoformat()
    assert m["whatsapp_trabalho_confirmado_em"] == T0.isoformat()                    # o do Meu perfil, intocado
    # o perfil mostra a verificação
    w = P.ler_perfil(b, A, A1)["whatsapp_trabalho"]
    assert w["verificado"] is True and w["verificado_em"] and w["confirmado"] is True
    # e o telefone vira identidade (só este membro)
    assert V.membros_verificados_por_telefone(b, CEL_A1) == [
        {"company_id": A, "user_id": A1, "nome": "Pessoa Aum", "nome_da_corretora": "Corretora Alfa"}]


def test_codigo_e_de_uso_unico():
    """Mutação (2): o MESMO código consumido duas vezes — a 2ª é recusada (e cala)."""
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    assert consumir(b, CEL_A1, f"ATIVAR {codigo}").ok
    r2 = consumir(b, CEL_A2, f"ATIVAR {codigo}")
    assert not r2.ok and r2.motivo == "codigo_invalido" and not r2.responder
    # o 2º remetente NÃO virou o número de ninguém
    assert _linha(b, A, A1)["whatsapp_trabalho_e164"] == CEL_A1
    assert V.membros_verificados_por_telefone(b, CEL_A2) == []
    assert [l["usado_em"] for l in b.tabelas[V.TABELA_CODIGOS]] == [T0.isoformat()]


def test_codigo_vencido_e_recusado():
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    r = consumir(b, CEL_A1, f"ATIVAR {codigo}", agora=T0 + timedelta(minutes=15, seconds=1))
    assert not r.ok and r.motivo == "codigo_invalido" and not r.responder
    assert _linha(b, A, A1)["whatsapp_trabalho_verificado_em"] is None
    # CONTROLE: um segundo antes de vencer, o mesmo código passa
    assert consumir(b, CEL_A1, f"ATIVAR {codigo}", agora=T0 + timedelta(minutes=14, seconds=59)).ok


def test_o_membro_vinculado_e_sempre_o_do_codigo_mesma_pessoa_em_duas_corretoras():
    """Mutação (3): pessoa_a1 é membro da A e da B. O código pedido NA A só verifica o vínculo da A."""
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    r = consumir(b, CEL_A1, f"ATIVAR {codigo}")
    assert r.ok and r.company_id == A
    assert _linha(b, A, A1)["whatsapp_trabalho_verificado_em"]
    assert _linha(b, B, A1)["whatsapp_trabalho_verificado_em"] is None              # 🔴 a B não mudou
    assert _linha(b, B, A1)["whatsapp_trabalho_e164"] is None
    assert [m["company_id"] for m in V.membros_verificados_por_telefone(b, CEL_A1)] == [A]


def test_o_membro_vinculado_e_sempre_o_do_codigo_nunca_o_dono_do_telefone():
    """Mutação (3): o código de pessoa_b1 (corretora_b), mandado do celular que a pessoa_a2 cadastrou na A, verifica a
    pessoa_b1 na B — nunca a pessoa_a2 (o número de quem manda não escolhe o membro; o código escolhe)."""
    b = banco()
    _linha(b, A, A2).update(whatsapp_trabalho_e164=CEL_B1, whatsapp_trabalho_confirmado_em=T0.isoformat())
    codigo = gerar(b, B, B1)["codigo"]
    r = consumir(b, CEL_B1, f"ATIVAR {codigo}")
    assert r.ok and (r.company_id, r.user_id) == (B, B1)
    assert _linha(b, B, B1)["whatsapp_trabalho_verificado_em"]
    assert _linha(b, A, A2)["whatsapp_trabalho_verificado_em"] is None
    escritas_em_membros = [(l["company_id"], l["user_id"]) for t, op, l in b.escritas if t == "company_members"]
    assert escritas_em_membros == [(B, B1)]


def test_o_mesmo_numero_em_dois_membros_da_mesma_corretora_e_recusado():
    b = banco()
    assert consumir(b, CEL_A1, f"ATIVAR {gerar(b, A, A1)['codigo']}").ok
    _linha(b, A, A2).update(whatsapp_trabalho_e164=CEL_A1)          # A2 declarou o número que A1 já verificou
    _linha(b, B, A1).update(**_declarado(CEL_A1))                   # a mesma pessoa, na B, declara o mesmo número
    codigo2 = gerar(b, A, A2)["codigo"]
    r = consumir(b, CEL_A1, f"ATIVAR {codigo2}")
    assert not r.ok and r.motivo == "numero_de_outra_pessoa" and r.responder and "outra pessoa" in r.mensagem
    assert _linha(b, A, A2)["whatsapp_trabalho_verificado_em"] is None
    # o código não foi gasto (a pessoa pode corrigir) e a recusa foi contada nele
    linha2 = next(l for l in b.tabelas[V.TABELA_CODIGOS] if l["user_id"] == A2)
    assert linha2["usado_em"] is None and linha2["tentativas"] == 1
    # CONTROLE: o mesmo número, verificado por OUTRA corretora (a mesma pessoa na B), é permitido
    assert consumir(b, CEL_A1, f"ATIVAR {gerar(b, B, A1)['codigo']}").ok
    assert sorted(m["company_id"] for m in V.membros_verificados_por_telefone(b, CEL_A1)) == [A, B]


def test_o_indice_unico_do_banco_tambem_recusa_e_o_codigo_volta_a_valer(monkeypatch):
    """A corrida: o cinto do Python não viu o outro membro, o índice `uq_company_members_whatsapp_verificado` viu."""
    b = banco()
    assert consumir(b, CEL_A1, f"ATIVAR {gerar(b, A, A1)['codigo']}").ok
    _linha(b, A, A2).update(whatsapp_trabalho_e164=CEL_A1)
    codigo2 = gerar(b, A, A2)["codigo"]
    original = _Consulta.execute

    def cego(self):  # o SELECT "outro membro DESTA corretora com este número verificado" volta vazio (a corrida)
        if self.tabela == "company_members" and self.op == "select" and                 {"company_id", "whatsapp_trabalho_e164"} <= set(self.colunas_filtradas):
            return _Resp([])
        return original(self)
    monkeypatch.setattr(_Consulta, "execute", cego)
    r = consumir(b, CEL_A1, f"ATIVAR {codigo2}")
    assert not r.ok and r.motivo == "numero_de_outra_pessoa" and r.responder
    assert _linha(b, A, A2)["whatsapp_trabalho_verificado_em"] is None
    # o código não foi gasto pela corrida perdida
    assert next(l for l in b.tabelas[V.TABELA_CODIGOS] if l["user_id"] == A2)["usado_em"] is None


def test_codigo_de_membro_que_saiu_cala():
    b = banco()
    codigo = gerar(b, A, A2)["codigo"]
    _linha(b, A, A2)["status"] = "inactive"
    r = consumir(b, CEL_A2, f"ATIVAR {codigo}")
    assert not r.ok and r.motivo == "membro_inativo" and not r.responder
    assert _linha(b, A, A2)["whatsapp_trabalho_verificado_em"] is None


def test_teto_de_tentativas_erradas_por_numero_cala_ate_o_codigo_certo():
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    errado = f"{(int(codigo) + 1) % 10 ** 6:06d}"
    for _ in range(V.TETO_DE_TENTATIVAS_ERRADAS_POR_HORA):
        r = consumir(b, CEL_A1, f"ATIVAR {errado}")
        assert r.motivo == "codigo_invalido" and not r.responder
    r = consumir(b, CEL_A1, f"ATIVAR {codigo}")
    assert not r.ok and r.motivo == "teto_de_tentativas" and not r.responder
    assert _linha(b, A, A1)["whatsapp_trabalho_verificado_em"] is None
    # ⛔ nenhuma linha guarda o telefone em claro nem o texto
    for l in b.tabelas[V.TABELA_TENTATIVAS]:
        assert set(l) == {"id", "telefone_hash", "criado_em"} and "11912345678" not in l["telefone_hash"]
    # outro número não é afetado (o teto é POR número): A2, do número dela, ativa
    assert consumir(b, CEL_A2, f"ATIVAR {gerar(b, A, A2)['codigo']}").ok


def test_numero_de_outro_pais_e_mensagem_qualquer_calam():
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    assert consumir(b, "+351912345678", f"ATIVAR {codigo}").motivo == "numero_invalido"
    assert consumir(b, CEL_A1, "oi, tudo bem?").motivo == "nao_e_ativacao"
    assert b.tabelas[V.TABELA_TENTATIVAS] == []          # nada registrado de quem só disse "oi"


def test_o_telefone_sem_o_9_vira_a_forma_canonica():
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    # "1234-5678" depois do DDD não é celular nem fixo do Brasil (o CHECK do banco recusaria): cala
    assert consumir(b, "551112345678@s.whatsapp.net", f"ATIVAR {codigo}").motivo == "numero_invalido"
    b2 = banco()
    _linha(b2, A, A1).update(whatsapp_trabalho_e164="+5511991234567")   # declarado com o 9; a conta antiga manda sem
    codigo2 = gerar(b2, A, A1)["codigo"]
    assert consumir(b2, "551191234567", f"ATIVAR {codigo2}").ok              # conta antiga sem o 9
    assert _linha(b2, A, A1)["whatsapp_trabalho_e164"] == "+5511991234567"
    assert V.membros_verificados_por_telefone(b2, "551191234567")[0]["user_id"] == A1
    assert V.membros_verificados_por_telefone(b2, "+55 11 99123-4567")[0]["user_id"] == A1


# =====================================================================================================================
# 3. quem é este telefone (a C2 chama) e o Meu perfil
# =====================================================================================================================
def test_so_membro_ativo_e_verificado_e_identidade():
    b = banco()
    # confirmado por clique, NÃO verificado: não é identidade (D-131-0 V37)
    _linha(b, A, A2).update(whatsapp_trabalho_e164=CEL_A2, whatsapp_trabalho_confirmado_em=T0.isoformat())
    assert V.membros_verificados_por_telefone(b, CEL_A2) == []
    assert consumir(b, CEL_A2, f"ATIVAR {gerar(b, A, A2)['codigo']}").ok
    assert len(V.membros_verificados_por_telefone(b, CEL_A2)) == 1
    _linha(b, A, A2)["status"] = "inactive"                                   # saiu da corretora
    assert V.membros_verificados_por_telefone(b, CEL_A2) == []
    assert V.membros_verificados_por_telefone(b, "") == []


def test_trocar_o_numero_no_meu_perfil_apaga_a_verificacao():
    b = banco()
    assert consumir(b, CEL_A1, f"ATIVAR {gerar(b, A, A1)['codigo']}").ok
    # gravar o MESMO número (mesma pessoa, de novo): a verificação fica
    P.gravar_whatsapp_trabalho(b, A, A1, numero="(11) 9 1234-5678", confirmo=True, por_user_id=A1)
    assert _linha(b, A, A1)["whatsapp_trabalho_verificado_em"]
    # trocar: apaga
    r = P.gravar_whatsapp_trabalho(b, A, A1, numero=CEL_A2, confirmo=True, por_user_id=A1)
    assert r["verificado"] is False and _linha(b, A, A1)["whatsapp_trabalho_verificado_em"] is None
    assert V.membros_verificados_por_telefone(b, CEL_A1) == [] == V.membros_verificados_por_telefone(b, CEL_A2)
    # remover: apaga também
    assert consumir(b, CEL_A2, f"ATIVAR {gerar(b, A, A1, agora=T0 + timedelta(minutes=1))['codigo']}",
                    agora=T0 + timedelta(minutes=2)).ok
    P.remover_whatsapp_trabalho(b, A, A1, por_user_id=A1)
    assert _linha(b, A, A1)["whatsapp_trabalho_verificado_em"] is None
    assert P.ler_perfil(b, A, A1)["whatsapp_trabalho"]["verificado"] is False


def test_antes_da_migration_o_perfil_continua_gravando_e_lendo():
    """Expand-first: sem a coluna `whatsapp_trabalho_verificado_em` (migration 20261014_03 não aplicada) o Meu perfil
    da 131-B não quebra."""
    b = banco()
    for m in b.tabelas["company_members"]:
        m.pop("whatsapp_trabalho_verificado_em")
    original = _Consulta.execute

    def sem_coluna(self):
        if self.tabela == "company_members" and self.op == "update" and P.COLUNA_VERIFICADO in (self.valor or {}):
            raise RuntimeError("column company_members.whatsapp_trabalho_verificado_em does not exist")
        return original(self)
    _Consulta.execute = sem_coluna
    try:
        r = P.gravar_whatsapp_trabalho(b, A, A1, numero=CEL_A1, confirmo=True, por_user_id=A1)
        assert r["numero"] == CEL_A1 and _linha(b, A, A1)["whatsapp_trabalho_e164"] == CEL_A1
        P.remover_whatsapp_trabalho(b, A, A1, por_user_id=A1)
        assert _linha(b, A, A1)["whatsapp_trabalho_e164"] is None
    finally:
        _Consulta.execute = original
    assert P.ler_perfil(b, A, A1)["whatsapp_trabalho"]["disponivel"] is True


def test_a_rota_gera_so_para_a_propria_pessoa(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import contas_da_corretora as CC

    b = banco()
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste")
    monkeypatch.setattr(CC, "_db", lambda: b)
    app = FastAPI()
    app.include_router(CC.router)
    cli = TestClient(app, raise_server_exceptions=False)
    url = "/api/contas-da-corretora/perfil/whatsapp-de-trabalho/codigo"
    hk = {"X-AutoBrokers-Internal-Key": "chave-de-teste"}
    assert cli.post(url, json={"company_id": A, "user_id": A1, "por_user_id": A1}).status_code == 401
    r = cli.post(url, json={"company_id": A, "user_id": A2, "por_user_id": A1}, headers=hk)
    assert r.status_code == 422 and b.tabelas[V.TABELA_CODIGOS] == []
    r = cli.post(url, json={"company_id": A, "user_id": SAIU, "por_user_id": SAIU}, headers=hk)
    assert r.status_code == 422 and "ativo" in r.json()["detail"]
    r = cli.post(url, json={"company_id": A, "user_id": A1, "por_user_id": A1}, headers=hk)
    assert r.status_code == 200 and r.json()["ok"] is True and len(r.json()["codigo"]) == 6
    assert r.json()["wa_me_url"].startswith(f"https://wa.me/{ASSISTENTE}?text=ATIVAR%20")
    assert [(l["company_id"], l["user_id"]) for l in b.tabelas[V.TABELA_CODIGOS]] == [(A, A1)]


# =====================================================================================================================
# 4. O CONSERTO ÚNICO — o código amarra o número DECLARADO, o teto global, e o atalho desligado não oferece código
# =====================================================================================================================
def test_gerar_exige_o_numero_declarado_e_confirmado():
    b = banco()
    _linha(b, A, A1).update(whatsapp_trabalho_e164=None, whatsapp_trabalho_confirmado_em=None)
    with pytest.raises(V.Recusa, match="Primeiro salve e confirme"):
        gerar(b, A, A1)
    _linha(b, A, A1).update(whatsapp_trabalho_e164=CEL_A1)          # número sem a confirmação da pessoa
    with pytest.raises(V.Recusa, match="Primeiro salve e confirme"):
        gerar(b, A, A1)
    assert b.tabelas[V.TABELA_CODIGOS] == []
    # CONTROLE: confirmado, gera
    _linha(b, A, A1).update(whatsapp_trabalho_confirmado_em=T0.isoformat())
    assert len(gerar(b, A, A1)["codigo"]) == 6


def test_desligado_nao_gera_codigo_e_o_perfil_diz_em_breve(monkeypatch):
    b = banco()
    assert P.ler_perfil(b, A, A1)["atalho_whatsapp"] == {"disponivel": True}      # CONTROLE: ligado e com número
    monkeypatch.delenv("ATALHO_WHATSAPP_LIGADO")
    assert P.ler_perfil(b, A, A1)["atalho_whatsapp"] == {"disponivel": False}
    with pytest.raises(V.Recusa, match="Em breve"):
        gerar(b, A, A1)
    assert b.tabelas[V.TABELA_CODIGOS] == []


def test_o_codigo_de_outro_celular_cala_conta_e_nao_muda_o_membro():
    """P1: A1 já verificou CEL_A1 e pede um código novo; o código mandado de OUTRO celular → silêncio, uma tentativa
    contada, a linha do membro IDÊNTICA (número, confirmação, verificação). O mesmo código, do número dela, vale."""
    b = banco()
    assert consumir(b, CEL_A1, f"ATIVAR {gerar(b, A, A1)['codigo']}").ok
    antes = copy.deepcopy(_linha(b, A, A1))
    codigo = gerar(b, A, A1, agora=T0 + timedelta(minutes=1))["codigo"]
    r = consumir(b, CEL_B1, f"ATIVAR {codigo}", agora=T0 + timedelta(minutes=2))
    assert not r.ok and not r.responder and r.motivo == "numero_nao_declarado"
    assert _linha(b, A, A1) == antes
    assert V.membros_verificados_por_telefone(b, CEL_B1) == []
    assert len(b.tabelas[V.TABELA_TENTATIVAS]) == 1
    assert [e for e in b.escritas if e[0] == "company_members"][1:] == []       # só a 1ª ativação escreveu no membro
    # CONTROLE: o mesmo código, do número declarado, verifica de novo
    assert consumir(b, CEL_A1, f"ATIVAR {codigo}", agora=T0 + timedelta(minutes=3)).ok


def test_o_teto_global_cala_quem_roda_numeros():
    """P1 (teto global): 12 números × 5 palpites = 60 chutes. Os primeiros 💭 30 contam; daí em diante, silêncio para
    TODOS — até o código certo, do número certo, espera a hora passar."""
    b = banco()
    codigo = gerar(b, A, A1)["codigo"]
    errado = f"{(int(codigo) + 1) % 10 ** 6:06d}"
    motivos = []
    for i in range(12):
        for _ in range(5):
            motivos.append(consumir(b, f"+55119{70000000 + i:08d}", f"ATIVAR {errado}").motivo)
    assert motivos.count("codigo_invalido") == V.TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA
    assert motivos.count("teto_global") == 60 - V.TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA
    assert consumir(b, CEL_A1, f"ATIVAR {codigo}").motivo == "teto_global"
    assert _linha(b, A, A1)["whatsapp_trabalho_verificado_em"] is None
    # passada a hora, o dono do código (dentro da validade dele: um novo) ativa
    novo = gerar(b, A, A1, agora=T0 + timedelta(minutes=61))["codigo"]
    assert consumir(b, CEL_A1, f"ATIVAR {novo}", agora=T0 + timedelta(minutes=62)).ok


# =====================================================================================================================
# as MUTAÇÕES do conserto (por cópia) — `python tests/test_spec132c_verificacao.py --mutar`
# =====================================================================================================================
MUTACOES = [
    ("V-P1 o código vale de qualquer celular", "app/services/atalho/verificacao.py",
     "            or not _mesmo_telefone(membro.get(\"whatsapp_trabalho_e164\"), e164):\n",
     "            and not _mesmo_telefone(membro.get(\"whatsapp_trabalho_e164\"), e164):\n",
     "test_o_codigo_de_outro_celular"),
    ("V-G sem teto global", "app/services/atalho/verificacao.py",
     "    if _tentativas_erradas_no_total(db, t0) >= TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA:\n",
     "    if False:\n",
     "test_o_teto_global"),
    ("V-D gera sem o número declarado", "app/services/atalho/verificacao.py",
     "    if not (membro.get(\"whatsapp_trabalho_e164\") and membro.get(\"whatsapp_trabalho_confirmado_em\")):\n"
     "        # 🔴 P1",
     "    if False:\n        # 🔴 P1",
     "test_gerar_exige"),
    ("V-L o perfil oferece com o atalho desligado", "app/services/perfil_do_membro.py",
     "        return {\"disponivel\": bool(ligado() and numero_do_assistente(db))}\n",
     "        return {\"disponivel\": bool(numero_do_assistente(db))}\n",
     "test_desligado"),
]


def _mutar() -> int:
    falhas = 0
    for rotulo, arquivo, de, para, teste in MUTACOES:
        caminho = BACKEND / arquivo
        bruto = caminho.read_bytes()
        original = bruto.decode("utf-8")
        crlf = "\r\n" in original
        de_, para_ = (de.replace("\n", "\r\n"), para.replace("\n", "\r\n")) if crlf else (de, para)
        assert original.count(de_) == 1, f"{rotulo}: o trecho não está UMA vez em {arquivo}"
        try:
            caminho.write_bytes(original.replace(de_, para_).encode("utf-8"))
            r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-q", "-p", "no:cacheprovider", "-k", teste],
                               cwd=str(BACKEND), capture_output=True, text=True)
            vermelho = r.returncode != 0
            print(f"{rotulo}: {'VERMELHO (o guarda pegou)' if vermelho else 'MUTACAO NAO PEGOU'} — {teste}")
            falhas += 0 if vermelho else 1
        finally:
            caminho.write_bytes(bruto)                          # 🔴 restaura POR CÓPIA DOS BYTES
            assert caminho.read_bytes() == bruto, f"{rotulo}: {arquivo} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())
