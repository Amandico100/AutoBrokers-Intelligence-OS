# -*- coding: utf-8 -*-
"""modelo: claude-opus-5-5 · SPEC-131-0-B2 · L4-A — OS AVISOS DO SISTEMA PELA LINHA DO USUÁRIO, prontos e DESLIGADOS.

D-132F-04 / D-1310B2-06: os avisos (renovações calculadas, licença do Agger, falha de conexão) saem pelo WhatsApp da
PRÓPRIA pessoa como um DESTINO do `DeliveryExecutor` (o publicador que existe — CLAUDE.md §5), e nascem DESLIGADOS:
`AVISOS_WHATSAPP_LIGADO` ausente = nada sai e o registro anota "teria enviado". Ligar é do Founder, POR TIPO.

O que este arquivo prova (o motor é o REAL — `linha_do_usuario.avisos.avisar`, `estado.linha_do_dono`,
`DeliveryExecutor.entregar` com a `delivery_policy` de verdade; dublê SÓ na borda: o banco em memória e o
`enviar_pela_linha` da L2, que é escrito em paralelo):

    1. 🔴 chave ausente/vazia/"true" → 0 envios e 1 registro `avisos_desligados` (a MUTAÇÃO 6 da SPEC)
    2. chave com UM tipo → só ele sai; com dois → os dois; o texto vai como veio (o prefixo é da L2)
    3. sem linha conectada (nenhuma, desconectada, inativa) → `sem_linha`, nada sai
    4. duas corretoras: o aviso de A nunca vai à linha de B nem grava em B; toda leitura filtra company_id + dono
    5. nenhum texto (nem pedaço, nem telefone) no registro nem no log
    6. "WhatsApp desconectado" NUNCA sai pela linha (só pelo central), mesmo listado na chave · tipo desconhecido recusa
    7. o envio falhou / a L2 não está instalada → motivo escrito, nada levanta
    8. o DeliveryExecutor: o canal `linha_do_usuario` chama `avisar`; sem ele no perfil, `avisar` nem é chamado e os
       canais antigos dão o mesmo resultado · publicação da corretora (sem pessoa) não vira aviso
    9. a limpeza do anti-eco apaga só o que tem > 7 dias (todas as corretoras) e nunca menos de 1 dia

Mutação 6: `python tests/test_spec1310b2_avisos.py --mutar` (cópia dos bytes; o aviso sai com a chave ausente; exige
VERMELHO; restaura por cópia e confere os bytes).
⛔ Dados fictícios: uuids sintéticos, telefones 💭 inventados (5511900000001…), nenhuma corretora real (CLAUDE.md §13.9).
Rodar: cd backend && python -m pytest tests/test_spec1310b2_avisos.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import logging
import subprocess
import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
# `app.services/__init__` carrega o `Settings` (6 campos obrigatórios). Num worktree sem `.env`, valores FICTÍCIOS —
# só quando não há `.env` nenhum (na árvore principal/bateria o `.env` manda e este bloco não toca o ambiente).
if not (Path.cwd() / ".env").exists() and not (BACKEND / ".env").exists():
    import os

    for _k, _v in (("SUPABASE_URL", "https://supabase.invalid"), ("SUPABASE_KEY", "chave-de-mentira"),
                   ("OPENAI_API_KEY", "chave-de-mentira"), ("ENCRYPTION_KEY", "chave-de-mentira"),
                   ("MINIO_ROOT_USER", "usuario-de-mentira"), ("MINIO_ROOT_PASSWORD", "senha-de-mentira")):
        os.environ.setdefault(_k, _v)

ALFA = "aaaaaaaa-0000-4000-8000-0000000000a1"
BETA = "bbbbbbbb-0000-4000-8000-0000000000b1"
U1 = "11111111-0000-4000-8000-000000000001"     # Alfa, linha conectada
U2 = "22222222-0000-4000-8000-000000000002"     # Alfa, sem linha
U3 = "33333333-0000-4000-8000-000000000003"     # Beta, linha conectada
U4 = "44444444-0000-4000-8000-000000000004"     # Alfa, linha que caiu (ativa, desconectada)
U5 = "55555555-0000-4000-8000-000000000005"     # Alfa, linha inativa (a pessoa desconectou)
TEL = {U1: "+5511900000001", U3: "+5521900000003", U4: "+5511900000004", U5: "+5511900000005"}   # 💭 inventados
TEXTO = "Renovações de 15/10: 12 calculadas, 3 pedem conferência."                                # 💭 ilustrativo
CHAVE = "AVISOS_WHATSAPP_LIGADO"
MODULO_DA_L2 = "app.services.linha_do_usuario.entrada"
COLUNAS_DO_REGISTRO = {"id", "company_id", "user_id", "tipo", "criado_em", "enviado", "motivo_nao_enviado"}


# =====================================================================================================================
# a borda: o banco em memória (PostgREST síncrono) — confere as FKs e CHECKs da migration e guarda cada consulta
# =====================================================================================================================
class _Resp:
    def __init__(self, data, count=None):
        self.data, self.count = data, count


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.op, self.carga, self.lim, self.ordem = [], "select", None, None, None

    def _f(self, op, campo, valor, teste):
        self.filtros.append((op, campo, valor, teste))
        return self

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def eq(self, c, v):
        return self._f("eq", c, v, lambda l: (l.get(c) is v) if isinstance(v, bool) else str(l.get(c)) == str(v))

    def in_(self, c, vs):
        return self._f("in", c, vs, lambda l: str(l.get(c)) in [str(x) for x in vs])

    def gte(self, c, v):
        return self._f("gte", c, v, lambda l: l.get(c) is not None and str(l.get(c)) >= str(v))

    def lt(self, c, v):
        return self._f("lt", c, v, lambda l: l.get(c) is not None and str(l.get(c)) < str(v))

    def is_(self, c, v):
        return self._f("is", c, v, lambda l: l.get(c) is None)

    def order(self, c, desc=False, **_k):
        self.ordem = (c, desc)
        return self

    def limit(self, n):
        self.lim = n
        return self

    def insert(self, carga):
        self.op, self.carga = "insert", carga
        return self

    def update(self, carga):
        self.op, self.carga = "update", dict(carga)
        return self

    def delete(self):
        self.op = "delete"
        return self

    def execute(self):
        self.banco.consultas.append({"tabela": self.tabela, "op": self.op,
                                     "filtros": [(o, c, v) for o, c, v, _ in self.filtros],
                                     "carga": copy.deepcopy(self.carga)})
        linhas = self.banco.dados.setdefault(self.tabela, [])
        casam = [l for l in linhas if all(t(l) for *_x, t in self.filtros)]
        if self.op == "select":
            if self.ordem:
                c, desc = self.ordem
                casam = sorted(casam, key=lambda l: str(l.get(c) or ""), reverse=desc)
            if self.lim:
                casam = casam[: self.lim]
            return _Resp(copy.deepcopy(casam), count=len(casam))
        if self.op == "insert":
            saida = []
            for nova in (self.carga if isinstance(self.carga, list) else [self.carga]):
                nova = copy.deepcopy(dict(nova))
                self.banco.conferir(self.tabela, nova)
                nova.setdefault("id", str(uuid.uuid4()))
                linhas.append(nova)
                saida.append(copy.deepcopy(nova))
            return _Resp(saida)
        if self.op == "update":
            for l in casam:
                l.update(copy.deepcopy(self.carga))
            return _Resp(copy.deepcopy(casam))
        if self.op == "delete":
            linhas[:] = [l for l in linhas if l not in casam]
            return _Resp(copy.deepcopy(casam))     # o PostgREST devolve as linhas apagadas (return=representation)
        raise AssertionError(self.op)


class Banco:
    def __init__(self, **tabelas):
        self.dados = {k: [dict(l) for l in v] for k, v in tabelas.items()}
        self.consultas = []

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, nome):
        return self.dados.setdefault(nome, [])

    def conferir(self, tabela, nova):
        """As FKs e os CHECKs da migration 20261015_01 que tocam o registro."""
        if tabela != "linha_avisos_registro":
            return
        import re

        membro = any(str(m["company_id"]) == str(nova.get("company_id")) and str(m["user_id"]) == str(nova.get("user_id"))
                     for m in self.linhas("company_members"))
        if not membro:
            raise RuntimeError('23503 insert violates foreign key constraint "fk_linha_avisos_registro_membro"')
        if not re.match(r"^[a-z0-9_]{1,64}$", str(nova.get("tipo") or "")):
            raise RuntimeError('23514 violates check constraint "ck_linha_avisos_registro_tipo"')
        if not (nova.get("enviado") is True or nova.get("motivo_nao_enviado")):
            raise RuntimeError('23514 violates check constraint "ck_linha_avisos_registro_motivo"')
        nova.setdefault("criado_em", datetime.now(timezone.utc).isoformat())
        nova.setdefault("enviado", False)

    def registro(self, **filtro):
        return [r for r in self.linhas("linha_avisos_registro") if all(str(r.get(k)) == str(v) for k, v in filtro.items())]


def _membro(cid, uid):
    return {"company_id": cid, "user_id": uid, "role": "member", "status": "active"}


def _linha(cid, uid, *, status="connected", ativa=True):
    return {"id": str(uuid.uuid4()), "company_id": cid, "owner_user_id": uid, "provider": "evolution-go",
            "purpose": "linha_do_usuario", "instance_id": f"ab-lu-{uid[:8]}", "identifier": f"ab-lu-{uid[:8]}",
            "is_active": ativa, "channel_status": status, "paired_phone_e164": TEL[uid],
            "paired_jid": TEL[uid].lstrip("+") + "@s.whatsapp.net", "linha_jid": TEL[uid].lstrip("+") + "@s.whatsapp.net",
            "linha_lid": None, "linha_conectada_em": "2026-10-15T10:00:00+00:00", "linha_desconectada_em": None,
            "linha_motivo": None, "descartadas_total": 0, "created_at": "2026-10-15T09:59:00+00:00", "token": "cifrado"}


@pytest.fixture
def banco():
    return Banco(
        company_members=[_membro(ALFA, U1), _membro(ALFA, U2), _membro(BETA, U3), _membro(ALFA, U4), _membro(ALFA, U5)],
        integrations=[
            _linha(ALFA, U1), _linha(BETA, U3),
            _linha(ALFA, U4, status="disconnected"),
            _linha(ALFA, U5, status="disconnected", ativa=False),
            # 🧪 controle: o número de ATENDIMENTO da Alfa (outro purpose, sem dono) — nunca é "a linha" de ninguém
            {"id": str(uuid.uuid4()), "company_id": ALFA, "owner_user_id": None, "provider": "evolution-go",
             "purpose": "attendance", "instance_id": "ab-atendimento-alfa", "is_active": True,
             "channel_status": "connected", "paired_phone_e164": "+5511900000099", "created_at": "2026-01-01"},
        ],
        linha_avisos_registro=[], linha_mensagens_do_sistema=[], briefing_publications=[])


class EnvioDaLinha:
    """O dublê do `enviar_pela_linha` da L2 (contrato: async (db, linha, texto_markdown) -> {enviadas, ids})."""

    def __init__(self, enviadas=1, explodir=False):
        self.chamadas, self.enviadas, self.explodir = [], enviadas, explodir

    async def enviar_pela_linha(self, db, linha, texto_markdown):
        self.chamadas.append({"linha": copy.deepcopy(linha), "texto": texto_markdown})
        if self.explodir:
            raise RuntimeError("provedor fora do ar")
        return {"enviadas": self.enviadas, "ids": [f"id-{i}" for i in range(self.enviadas)]}


@pytest.fixture
def envio(monkeypatch):
    dublê = EnvioDaLinha()
    modulo = types.ModuleType(MODULO_DA_L2)
    modulo.enviar_pela_linha = dublê.enviar_pela_linha
    monkeypatch.setitem(sys.modules, MODULO_DA_L2, modulo)
    return dublê


@pytest.fixture(autouse=True)
def _linha_ligada(monkeypatch):
    """A PREMISSA deste arquivo: a linha está LIGADA para todos (`LINHA_DO_USUARIO_LIGADA=1`) e só a chave dos AVISOS
    varia. (fix/linha-por-pessoa: o aviso agora confere `estado.ligada_para(user_id)` antes da chave dos avisos — a
    pessoa fora da lista é `linha_desligada`, provado em `test_linha_por_pessoa.py`.)"""
    monkeypatch.setenv("LINHA_DO_USUARIO_LIGADA", "1")


@pytest.fixture
def A():
    from app.services.linha_do_usuario import avisos

    return avisos


def _avisar(A, db, cid, uid, tipo="renovacoes_calculadas", texto=TEXTO):
    return asyncio.run(A.avisar(db, company_id=cid, user_id=uid, tipo=tipo, texto_markdown=texto))


# =====================================================================================================================
# 1 · 🔴 a chave ausente: nada sai, e o registro diz "teria enviado" (a MUTAÇÃO 6)
# =====================================================================================================================
@pytest.mark.parametrize("valor", [None, "", "   ", "1", "true", "todos", "renovacao"])
def test_chave_ausente_nada_sai_e_registra_teria_enviado(A, banco, envio, monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv(CHAVE, raising=False)
    else:
        monkeypatch.setenv(CHAVE, valor)
    for tipo in A.TIPOS:
        r = _avisar(A, banco, ALFA, U1, tipo)
        assert r["enviado"] is False and r["motivo"] == "avisos_desligados" and r["registrado"] is True, (tipo, r)
    assert envio.chamadas == [], "com a chave ausente/sem tipo, NENHUM aviso pode sair"
    regs = banco.registro(company_id=ALFA, user_id=U1)
    assert len(regs) == len(A.TIPOS) == 3
    assert {r["tipo"] for r in regs} == set(A.TIPOS)
    assert all(r["enviado"] is False and r["motivo_nao_enviado"] == "avisos_desligados" for r in regs)


# =====================================================================================================================
# 2 · a chave com UM tipo: só ele sai
# =====================================================================================================================
def test_chave_com_um_tipo_so_ele_sai(A, banco, envio, monkeypatch):
    monkeypatch.setenv(CHAVE, "renovacoes_calculadas")
    r1 = _avisar(A, banco, ALFA, U1, "renovacoes_calculadas")
    r2 = _avisar(A, banco, ALFA, U1, "licenca_do_agger")
    r3 = _avisar(A, banco, ALFA, U1, "falha_de_conexao")
    assert (r1["enviado"], r1["motivo"]) == (True, None)
    assert (r2["enviado"], r2["motivo"]) == (False, "avisos_desligados")
    assert (r3["enviado"], r3["motivo"]) == (False, "avisos_desligados")
    assert len(envio.chamadas) == 1
    ch = envio.chamadas[0]
    assert ch["linha"]["company_id"] == ALFA and ch["linha"]["owner_user_id"] == U1
    # o prefixo "▸ AutoBrokers\n" é da L2 (a função dela o põe): aqui o texto vai COMO VEIO, sem prefixo duplicado
    assert ch["texto"] == TEXTO and "AutoBrokers" not in ch["texto"]
    regs = banco.registro(company_id=ALFA, user_id=U1)
    assert sorted((r["tipo"], r["enviado"], r["motivo_nao_enviado"]) for r in regs) == [
        ("falha_de_conexao", False, "avisos_desligados"),
        ("licenca_do_agger", False, "avisos_desligados"),
        ("renovacoes_calculadas", True, None),
    ]


def test_chave_com_dois_tipos_e_separadores(A, banco, envio, monkeypatch):
    monkeypatch.setenv(CHAVE, " Renovacoes_Calculadas ; licenca_do_agger,tipo_que_nao_existe ")
    assert A.tipos_ligados() == frozenset({"renovacoes_calculadas", "licenca_do_agger"})
    saiu = [_avisar(A, banco, ALFA, U1, t)["enviado"] for t in A.TIPOS]
    assert saiu == [True, True, False]
    assert len(envio.chamadas) == 2


# =====================================================================================================================
# 3 · sem linha conectada: nada sai, `sem_linha`
# =====================================================================================================================
@pytest.mark.parametrize("dono", [U2, U4, U5], ids=["sem_linha", "linha_caida", "linha_inativa"])
def test_sem_linha_conectada(A, banco, envio, monkeypatch, dono):
    monkeypatch.setenv(CHAVE, ",".join(A.TIPOS))
    r = _avisar(A, banco, ALFA, dono)
    assert (r["enviado"], r["motivo"], r["registrado"]) == (False, "sem_linha", True)
    assert envio.chamadas == []
    regs = banco.registro(company_id=ALFA, user_id=dono)
    assert [(x["enviado"], x["motivo_nao_enviado"]) for x in regs] == [(False, "sem_linha")]


def test_sem_linha_tambem_com_a_chave_ausente(A, banco, envio, monkeypatch):
    """'teria enviado' só é verdade se havia por onde enviar: sem linha, o motivo é `sem_linha` (o que ligar a chave
    NÃO mudaria)."""
    monkeypatch.delenv(CHAVE, raising=False)
    assert _avisar(A, banco, ALFA, U2)["motivo"] == "sem_linha"
    assert envio.chamadas == []


# =====================================================================================================================
# 4 · duas corretoras: o aviso de A nunca vai à linha de B nem grava em B
# =====================================================================================================================
def test_duas_corretoras(A, banco, envio, monkeypatch):
    monkeypatch.setenv(CHAVE, ",".join(A.TIPOS))
    # U3 tem linha conectada NA BETA. Um aviso "da Alfa" para U3 (não é membro da Alfa) não acha linha nem grava em B.
    r = _avisar(A, banco, ALFA, U3)
    assert r["enviado"] is False and r["motivo"] == "sem_linha"
    assert envio.chamadas == []
    assert banco.registro(company_id=BETA) == [], "o aviso de A não pode gravar na corretora B"
    assert r["registrado"] is False, "U3 não é membro da Alfa: a FK composta do registro recusa (e nada levanta)"

    # os dois lados de verdade: cada aviso sai pela linha DA SUA corretora, do SEU dono
    assert _avisar(A, banco, ALFA, U1)["enviado"] is True
    assert _avisar(A, banco, BETA, U3)["enviado"] is True
    assert [(c["linha"]["company_id"], c["linha"]["owner_user_id"]) for c in envio.chamadas] == [(ALFA, U1), (BETA, U3)]
    assert {r["company_id"] for r in banco.registro(user_id=U1)} == {ALFA}
    assert {r["company_id"] for r in banco.registro(user_id=U3)} == {BETA}

    # 🔴 toda leitura de linha filtra company_id E o dono NO BANCO (o backend é service role — CLAUDE.md §7)
    leituras = [q for q in banco.consultas if q["tabela"] == "integrations" and q["op"] == "select"]
    assert leituras
    for q in leituras:
        campos = {(o, c) for o, c, _v in q["filtros"]}
        assert {("eq", "company_id"), ("eq", "owner_user_id"), ("eq", "purpose")} <= campos, q["filtros"]
    escritas = [q for q in banco.consultas if q["tabela"] == "linha_avisos_registro"]
    assert escritas and all(q["op"] == "insert" for q in escritas), "o aviso só INSERE no registro (nunca lê/apaga)"


def test_a_linha_devolvida_de_outra_corretora_e_recusada_em_python(A, banco, envio, monkeypatch):
    """Um filtro esquecido (aqui: o banco IGNORA o company_id) não vira envio pela linha de outra corretora."""
    monkeypatch.setenv(CHAVE, ",".join(A.TIPOS))
    original = _Consulta.eq

    def eq_que_esquece(self, c, v):
        if self.tabela == "integrations" and c in ("company_id", "owner_user_id"):
            return self
        return original(self, c, v)

    monkeypatch.setattr(_Consulta, "eq", eq_que_esquece)
    r = _avisar(A, banco, ALFA, U2)    # U2 não tem linha; o banco "esquecido" devolve as linhas de U1/U3/U4/U5
    assert r["enviado"] is False and r["motivo"] == "sem_linha"
    assert envio.chamadas == []


# =====================================================================================================================
# 5 · nenhum texto no registro (nem no log)
# =====================================================================================================================
def test_nenhum_texto_no_registro_nem_no_log(A, banco, envio, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv(CHAVE, "renovacoes_calculadas")
    envio_que_falha = EnvioDaLinha(enviadas=0)
    _avisar(A, banco, ALFA, U1, "renovacoes_calculadas")
    _avisar(A, banco, ALFA, U1, "licenca_do_agger")
    _avisar(A, banco, ALFA, U2, "renovacoes_calculadas")
    monkeypatch.setattr(sys.modules[MODULO_DA_L2], "enviar_pela_linha", envio_que_falha.enviar_pela_linha)
    _avisar(A, banco, ALFA, U1, "renovacoes_calculadas")
    regs = banco.linhas("linha_avisos_registro")
    assert len(regs) == 4
    pedacos = [TEXTO, "Renovações", "12 calculadas", "conferência"] + list(TEL.values()) + [t.lstrip("+") for t in TEL.values()]
    for r in regs:
        assert set(r) <= COLUNAS_DO_REGISTRO, set(r) - COLUNAS_DO_REGISTRO
        assert not any(p in str(v) for v in r.values() for p in pedacos), r
    log = caplog.text
    assert not any(p in log for p in pedacos), "texto ou telefone vazou no log"


# =====================================================================================================================
# 6 · "WhatsApp desconectado" só pelo central · tipo desconhecido · identidade inválida
# =====================================================================================================================
def test_whatsapp_desconectado_nunca_sai_pela_linha(A, banco, envio, monkeypatch):
    monkeypatch.setenv(CHAVE, "whatsapp_desconectado,renovacoes_calculadas")
    assert "whatsapp_desconectado" not in A.TIPOS
    r = _avisar(A, banco, ALFA, U1, "whatsapp_desconectado")
    assert (r["enviado"], r["motivo"], r["registrado"]) == (False, "so_pelo_central", False)
    assert envio.chamadas == [] and banco.linhas("linha_avisos_registro") == []


@pytest.mark.parametrize("tipo", ["", None, "cobranca", "Renovações calculadas"])
def test_tipo_desconhecido_recusa_sem_ler_nem_gravar(A, banco, envio, monkeypatch, tipo):
    monkeypatch.setenv(CHAVE, ",".join(A.TIPOS))
    r = _avisar(A, banco, ALFA, U1, tipo)
    assert (r["enviado"], r["motivo"], r["registrado"], r["tipo"]) == (False, "tipo_desconhecido", False, None)
    assert envio.chamadas == [] and banco.consultas == []


@pytest.mark.parametrize("cid,uid", [("", U1), (ALFA, ""), ("nao-e-uuid", U1), (ALFA, "1 or 1=1")])
def test_identidade_invalida_recusa(A, banco, envio, monkeypatch, cid, uid):
    monkeypatch.setenv(CHAVE, ",".join(A.TIPOS))
    r = _avisar(A, banco, cid, uid)
    assert (r["enviado"], r["motivo"], r["registrado"]) == (False, "identidade_invalida", False)
    assert envio.chamadas == [] and banco.consultas == []


# =====================================================================================================================
# 7 · o envio falhou / a L2 não está instalada: motivo escrito, nada levanta
# =====================================================================================================================
def test_envio_que_nao_saiu(A, banco, monkeypatch):
    monkeypatch.setenv(CHAVE, "renovacoes_calculadas")
    for dublê, motivo in ((EnvioDaLinha(enviadas=0), "falha_no_envio"), (EnvioDaLinha(explodir=True), "falha_no_envio")):
        modulo = types.ModuleType(MODULO_DA_L2)
        modulo.enviar_pela_linha = dublê.enviar_pela_linha
        monkeypatch.setitem(sys.modules, MODULO_DA_L2, modulo)
        r = _avisar(A, banco, ALFA, U1)
        assert (r["enviado"], r["motivo"]) == (False, motivo)
        assert len(dublê.chamadas) == 1
    monkeypatch.setitem(sys.modules, MODULO_DA_L2, None)     # a L2 ausente: o import tardio falha
    r = _avisar(A, banco, ALFA, U1)
    assert (r["enviado"], r["motivo"]) == (False, "envio_indisponivel")
    regs = banco.registro(company_id=ALFA, user_id=U1)
    assert [x["motivo_nao_enviado"] for x in regs] == ["falha_no_envio", "falha_no_envio", "envio_indisponivel"]


def test_o_contrato_da_l2_e_import_tardio(A):
    """O `avisos.py` importa `enviar_pela_linha` DENTRO da função (a L2 escreve em paralelo); no topo, nada da L2."""
    fonte = Path(A.__file__).read_text(encoding="utf-8")
    topo = fonte.split("\nasync def ", 1)[0].split("\ndef ", 1)[0]
    assert "linha_do_usuario.entrada" not in "\n".join(l for l in topo.splitlines() if l.startswith(("import", "from")))
    assert "from app.services.linha_do_usuario.entrada import enviar_pela_linha" in fonte


# =====================================================================================================================
# 8 · o DeliveryExecutor: o canal novo chama `avisar`; os antigos não mudam
# =====================================================================================================================
def _publicacao(cid=ALFA, uid=U1, secao="renovacao"):
    return {"id": str(uuid.uuid4()), "company_id": cid, "user_id": uid, "headline": "Renovações de 15/10",
            "critical_count": 1, "recommendation_count": 0, "briefing_type": "on_demand",
            "payload": {"sections": [{"key": secao, "items": []}]}}


def _canais(resultado):
    return {c["canal"]: c for c in resultado["delivery_detail"]["canais"]}


def test_o_executor_com_o_canal_novo_chama_avisar_desligado(banco, envio, monkeypatch):
    from app.services.intelligence.delivery_executor import CANAIS_CONHECIDOS, DeliveryExecutor

    monkeypatch.delenv(CHAVE, raising=False)
    monkeypatch.delenv("APP_PUBLIC_URL", raising=False)
    assert "linha_do_usuario" in CANAIS_CONHECIDOS
    r = DeliveryExecutor(banco).entregar(_publicacao(), perfil={"channels": ["dashboard", "linha_do_usuario"]})
    canais = _canais(r)
    assert canais["dashboard"]["ok"] is True
    assert canais["linha_do_usuario"]["ok"] is False and "desligad" in canais["linha_do_usuario"]["motivo"]
    assert r["delivery_status"] == "partial"
    assert envio.chamadas == []
    assert [(x["tipo"], x["motivo_nao_enviado"]) for x in banco.registro(company_id=ALFA, user_id=U1)] == [
        ("renovacoes_calculadas", "avisos_desligados")]


def test_o_executor_com_o_canal_novo_ligado_manda_a_manchete(banco, envio, monkeypatch):
    from app.services.intelligence.delivery_executor import DeliveryExecutor

    monkeypatch.setenv(CHAVE, "renovacoes_calculadas")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://app.exemplo.test/")
    r = DeliveryExecutor(banco).entregar(_publicacao(), perfil={"channels": ["dashboard", "linha_do_usuario"]})
    assert _canais(r)["linha_do_usuario"]["ok"] is True and r["delivery_status"] == "sent"
    assert len(envio.chamadas) == 1
    # só a manchete e o link (como o canal whatsapp) — nunca o relatório
    assert envio.chamadas[0]["texto"] == "Renovações de 15/10\n\nhttps://app.exemplo.test/dashboard/entregas"
    assert envio.chamadas[0]["linha"]["owner_user_id"] == U1


def test_o_executor_publicacao_sem_pessoa_ou_sem_tipo(banco, envio, monkeypatch):
    from app.services.intelligence.delivery_executor import DeliveryExecutor
    from app.services.linha_do_usuario import avisos

    monkeypatch.setenv(CHAVE, ",".join(avisos.TIPOS))
    chamadas = []
    original = avisos.avisar

    def espiao(*a, **k):
        chamadas.append(k)
        return original(*a, **k)

    monkeypatch.setattr(avisos, "avisar", espiao)
    da_corretora = DeliveryExecutor(banco).entregar(_publicacao(uid=None),
                                                    perfil={"channels": ["dashboard", "linha_do_usuario"]})
    assert "pessoa" in _canais(da_corretora)["linha_do_usuario"]["motivo"]
    sem_tipo = DeliveryExecutor(banco).entregar(_publicacao(secao="outra_coisa"),
                                                perfil={"channels": ["dashboard", "linha_do_usuario"]})
    assert _canais(sem_tipo)["linha_do_usuario"]["ok"] is False
    assert chamadas == [] and envio.chamadas == [] and banco.linhas("linha_avisos_registro") == []
    # o tipo explícito no perfil vence a dedução pela seção
    explicito = DeliveryExecutor(banco).entregar(_publicacao(secao="outra_coisa"), perfil={
        "channels": ["dashboard", "linha_do_usuario"], "aviso_tipo": "licenca_do_agger"})
    assert _canais(explicito)["linha_do_usuario"]["ok"] is True
    assert [k["tipo"] for k in chamadas] == ["licenca_do_agger"]


def test_controle_os_canais_antigos_nao_chamam_avisar(banco, envio, monkeypatch):
    """🧪 LINHA DE CONTROLE: sem `linha_do_usuario` no perfil, `avisar` NUNCA é chamado e os canais antigos dão o
    mesmo resultado com o módulo de avisos sabotado (se o executor dependesse dele, o resultado mudaria)."""
    from app.services.intelligence.delivery_executor import DeliveryExecutor
    from app.services.linha_do_usuario import avisos

    monkeypatch.setenv(CHAVE, ",".join(avisos.TIPOS))
    monkeypatch.delenv("APP_PUBLIC_URL", raising=False)
    perfil = {"channels": ["dashboard", "email", "whatsapp"], "recipient_refs": {"email": [], "whatsapp": []}}
    antes = DeliveryExecutor(banco).entregar(_publicacao(), perfil=perfil)

    def sabotado(*_a, **_k):
        raise AssertionError("avisar não pode ser chamado por canal antigo")

    monkeypatch.setattr(avisos, "avisar", sabotado)
    depois = DeliveryExecutor(banco).entregar(_publicacao(), perfil=perfil)
    tirar = lambda r: [(c["canal"], c["ok"], c["motivo"]) for c in r["delivery_detail"]["canais"]]  # noqa: E731
    assert tirar(antes) == tirar(depois)
    assert [c for c, *_ in tirar(antes)] == ["dashboard", "email", "whatsapp"]
    assert envio.chamadas == [] and banco.linhas("linha_avisos_registro") == []


def test_a_secao_da_renovacao_e_a_mesma_do_motor(A):
    """A dedução do tipo pela seção usa o MESMO nome que `renovacao.registrar_aviso` publica."""
    from app.services.multicalculo.renovacao import SECAO_DO_AVISO

    assert A.SECAO_DA_RENOVACAO == SECAO_DO_AVISO
    assert A.tipo_da_publicacao({"payload": {"sections": [{"key": SECAO_DO_AVISO}]}}) == "renovacoes_calculadas"
    assert A.tipo_da_publicacao({"payload": {"sections": [{"key": "x"}]}}) is None


# =====================================================================================================================
# 9 · a limpeza do anti-eco (P-132C-04): só o que tem > 7 dias
# =====================================================================================================================
def test_a_limpeza_apaga_so_mais_de_7_dias(A, banco):
    agora = datetime.now(timezone.utc)
    integ = {ALFA: banco.linhas("integrations")[0]["id"], BETA: banco.linhas("integrations")[1]["id"]}

    def msg(cid, idade, n):
        return {"id": str(uuid.uuid4()), "integration_id": integ[cid], "company_id": cid, "message_id": f"m{n}",
                "hash_texto": "a" * 64, "enviada_em": (agora - idade).isoformat()}

    banco.dados["linha_mensagens_do_sistema"] = [
        msg(ALFA, timedelta(days=8), 1), msg(BETA, timedelta(days=30), 2),          # vão
        msg(ALFA, timedelta(days=6, hours=23), 3), msg(BETA, timedelta(minutes=1), 4),  # ficam
    ]
    assert A.limpar_anti_eco(banco) == 2
    assert sorted(m["message_id"] for m in banco.linhas("linha_mensagens_do_sistema")) == ["m3", "m4"]
    q = [x for x in banco.consultas if x["tabela"] == "linha_mensagens_do_sistema"]
    assert [(x["op"], [(o, c) for o, c, _ in x["filtros"]]) for x in q] == [("delete", [("lt", "enviada_em")])]
    # dias < 1 (ou lixo) é inválido → o padrão de 7: o anti-eco dos últimos 10 min não some por um parâmetro errado
    assert A.limpar_anti_eco(banco, dias=0) == 0 and A.limpar_anti_eco(banco, dias=-5) == 0
    assert A.limpar_anti_eco(banco, dias="lixo") == 0
    assert sorted(m["message_id"] for m in banco.linhas("linha_mensagens_do_sistema")) == ["m3", "m4"]


def test_a_limpeza_nunca_levanta(A):
    class Quebrado:
        def table(self, _n):
            raise RuntimeError("banco fora do ar")

    assert A.limpar_anti_eco(Quebrado()) == 0


# =====================================================================================================================
# a MUTAÇÃO 6 — o aviso sai com a chave ausente → este arquivo TEM de ficar VERMELHO
# =====================================================================================================================
ALVO = BACKEND / "app" / "services" / "linha_do_usuario" / "avisos.py"
LINHA_GUARDA = "    elif tipo not in tipos_ligados():"
LINHA_MUTANTE = "    elif False:  # MUTACAO 6"


def _mutar() -> int:
    original = ALVO.read_bytes()
    texto = original.decode("utf-8")
    assert texto.count(LINHA_GUARDA) == 1, "a linha-guarda sumiu ou duplicou: a mutação não sabe o que mudar"
    try:
        ALVO.write_bytes(texto.replace(LINHA_GUARDA, LINHA_MUTANTE).encode("utf-8"))
        r = subprocess.run([sys.executable, "-m", "pytest", str(Path(__file__)), "-q", "-p", "no:cacheprovider",
                            "-k", "chave_ausente"], cwd=str(BACKEND), capture_output=True, text=True)
        print(r.stdout[-1500:])
    finally:
        ALVO.write_bytes(original)
    assert ALVO.read_bytes() == original, "a restauração por cópia falhou"
    if r.returncode == 0:
        print("MUTACAO 6: o guarda ficou VERDE com o aviso saindo — o guarda NAO guarda")
        return 1
    print("MUTACAO 6: VERMELHO como devia (restaurado por copia, bytes conferidos)")
    return 0


if __name__ == "__main__":
    if "--mutar" in sys.argv:
        raise SystemExit(_mutar())
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
