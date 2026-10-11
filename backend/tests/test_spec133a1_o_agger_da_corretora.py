# -*- coding: utf-8 -*-
"""SPEC-133-A.1 F3 — o "Agger da corretora" na tela de conexões (D-133A1-03/04).

O FIO: a rota REAL (`app/api/portal.py`, FastAPI TestClient) → o serviço REAL (`conta_do_robo`) → `portal_accounts`
no banco dublê com as travas do U1 (`dubles.banco_multicalculo.BancoU1`) → o cofre REAL (Fernet) → o robô do motor
resolve a conta (`robos.escolher`, o MESMO que o motor chama antes de calcular). Dublê só na borda: o banco.

E o que cada teste guarda:
    ① a tela liga o robô: a conta nasce `ativo`, com a janela padrão, a senha no cofre — e o motor a escolhe
    ② dois tenants: a corretora A grava o Agger DELA e nunca toca na B (nem nas contas do comando da própria A)
    ③ o comando e a tela gravam IGUAL — o mesmo serviço, o mesmo registro (a tela reabre a conta do comando)
    ④ desconectar apaga a senha do cofre, pausa, e o histórico fica
    ⑤ a senha nunca aparece: nem em resposta, nem em log, nem no erro inesperado
    ⑥ os estados que a tela mostra vêm do que o robô grava (bloqueado → "a senha foi recusada"; cálculo → último uso)

⛔ Nenhuma senha real: todas são fictícias, geradas aqui.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
from dubles.banco_multicalculo import BancoU1, instalar_esquema  # noqa: E402
from portal_worker.multicalculo import comando_robo as CMD  # noqa: E402
from portal_worker.multicalculo import conta_do_robo as CR  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402

CHAVE = "chave-interna-de-teste"
SENHA = "Senha-Ficticia-Da-Tela-" + uuid4().hex[:8]
LOGIN = "cotador-ficticio@exemplo.invalid"
#: uma quarta-feira 12:00 em Brasília — dentro da janela padrão (seg-sab 07–22)
QUARTA_MEIO_DIA = datetime(2026, 10, 7, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def mundo(monkeypatch):
    from cryptography.fernet import Fernet
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import portal as API

    instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    banco = BancoU1(D.Relogio(QUARTA_MEIO_DIA))
    a, b = str(uuid4()), str(uuid4())
    for c in (a, b):
        banco.semear("companies", {"id": c, "company_kind": "client"})
    visao = banco.visao("smith-api")
    monkeypatch.setattr(API, "get_supabase_client", lambda: SimpleNamespace(client=visao))
    app = FastAPI()
    app.include_router(API.router)
    cli = TestClient(app, raise_server_exceptions=False)
    return SimpleNamespace(banco=banco, supa=visao, a=a, b=b, cli=cli, api=API)


def _post(m, company_id, acao, **extra):
    return m.cli.post("/api/portal/agger-da-corretora", headers={"X-AutoBrokers-Internal-Key": CHAVE},
                      json={"company_id": company_id, "acao": acao, **extra})


def _get(m, company_id):
    return m.cli.get("/api/portal/agger-da-corretora", params={"company_id": company_id},
                     headers={"X-AutoBrokers-Internal-Key": CHAVE})


def _contas(m, company_id=None):
    return [c for c in m.banco.linhas("portal_accounts")
            if c["portal_key"] == "agger" and (company_id is None or c["company_id"] == company_id)]


def _da_tela(m, company_id):
    return [c for c in _contas(m, company_id) if c["account_label"] == CR.ROTULO_DA_CORRETORA]


# ① ===================================================================================================================
def test_o_fio_a_tela_liga_o_robo_e_o_motor_escolhe_a_conta(mundo):
    from portal_worker import vault

    m = mundo
    assert _get(m, m.a).json()["conta"]["situacao"] == "nao_conectado"
    r = _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA)
    assert r.status_code == 200, r.text
    [conta] = _da_tela(m, m.a)
    assert conta["robo_estado"] == "ativo" and conta["username"] == LOGIN
    assert vault.decrypt(conta["secret_encrypted"]) == SENHA, "a senha está no cofre (a MESMA chave do worker)"
    assert conta["robo_janela"] == CR.JANELA_PADRAO and conta["robo_teto_por_hora"] is None
    retrato = r.json()["conta"]
    assert retrato["situacao"] == "aguardando" and retrato["tem_senha"] is True
    assert retrato["usuario"] == CR.mascarar(LOGIN) and set(retrato["acoes"]) >= {"pausar", "trocar_senha",
                                                                                    "desconectar"}
    # o motor resolve a conta que a tela gravou (o fim do fio): mesma corretora, dentro da janela, com a lease
    escolhida = ROB.escolher(m.supa, m.a, "quem_cobra_menos", dono="motor-teste", agora=QUARTA_MEIO_DIA)
    assert escolhida is not None and escolhida["id"] == conta["id"]
    # CONTROLE: domingo às 12h está fora da janela padrão — o motor NÃO a usa (a janela gravada é a que ele lê)
    ROB.liberar(m.supa, escolhida, "motor-teste")
    domingo = QUARTA_MEIO_DIA + timedelta(days=4)
    assert ROB.escolher(m.supa, m.a, "quem_cobra_menos", dono="motor-teste", agora=domingo) is None


# ② ===================================================================================================================
def test_dois_tenants_a_corretora_a_grava_o_dela_e_nunca_o_da_b(mundo):
    from portal_worker import vault

    m = mundo
    # a B já tem o Agger dela pela tela; a A tem um robô do RODÍZIO cadastrado pelo comando (outro rótulo)
    assert _post(m, m.b, "conectar", usuario="b-" + LOGIN, senha="Senha-Da-B-Ficticia").status_code == 200
    rodizio = CR.cadastrar(m.supa, company_id=m.a, rotulo="robo-2", usuario="rodizio@exemplo.invalid",
                           senha="Senha-Do-Rodizio-Ficticia", estado="ativo", janela=None, teto=None,
                           cifrar=vault.encrypt)
    antes_b = [dict(c) for c in _contas(m, m.b)]
    antes_rodizio = dict(next(c for c in _contas(m, m.a) if c["id"] == rodizio["id"]))
    # a tela da A, sem Agger próprio, não enxerga nem o da B nem o do rodízio
    assert _get(m, m.a).json()["conta"]["situacao"] == "nao_conectado"
    assert _post(m, m.a, "desconectar").status_code == 409, "sem a conta global, nada a desconectar"
    assert _post(m, m.a, "pausar").status_code == 409
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    assert _post(m, m.a, "pausar").status_code == 200
    assert _post(m, m.a, "desconectar").status_code == 200
    assert [dict(c) for c in _contas(m, m.b)] == antes_b, "a B não mudou"
    assert dict(next(c for c in _contas(m, m.a) if c["id"] == rodizio["id"])) == antes_rodizio, \
        "a conta do rodízio (comando) não é da tela"
    assert len(_da_tela(m, m.a)) == 1 and len(_da_tela(m, m.b)) == 1
    assert _get(m, m.b).json()["conta"]["situacao"] == "aguardando"


# ③ ===================================================================================================================
def test_o_comando_e_a_tela_gravam_igual_e_o_mesmo_registro(mundo):
    from portal_worker import vault

    m = mundo
    saida = []
    rc = CMD.main(["cadastrar", "--corretora", m.b, "--rotulo", CR.ROTULO_DA_CORRETORA, "--usuario", LOGIN,
                   "--estado", "ativo", "--janela", "seg-sab,07:00-22:00"],
                  supa=m.supa, ler_senha=lambda: SENHA, cifrar=vault.encrypt, escrever=saida.append)
    assert rc == 0, saida
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    [pelo_comando], [pela_tela] = _da_tela(m, m.b), _da_tela(m, m.a)
    iguais = ("portal_key", "account_label", "username", "health", "robo_estado", "robo_janela",
              "robo_teto_por_hora", "robo_ocupada_ate", "robo_dono", "robo_batida_em")
    assert {k: pelo_comando[k] for k in iguais} == {k: pela_tela[k] for k in iguais}
    assert vault.decrypt(pelo_comando["secret_encrypted"]) == vault.decrypt(pela_tela["secret_encrypted"])
    # a tela REABRE a conta do comando (nunca uma segunda): trocar o login e a senha mantém o id
    assert _get(m, m.b).json()["conta"]["id"] == pelo_comando["id"]
    r = _post(m, m.b, "trocar_senha", senha="Senha-Nova-Ficticia-9")
    assert r.status_code == 200, r.text
    [depois] = _da_tela(m, m.b)
    assert depois["id"] == pelo_comando["id"] and depois["username"] == LOGIN, "login em branco = mantém"
    assert vault.decrypt(depois["secret_encrypted"]) == "Senha-Nova-Ficticia-9" and depois["robo_estado"] == "ativo"
    # e o comando LISTA o que a tela gravou, com o login mascarado
    lista = []
    assert CMD.main(["listar", "--corretora", m.a], supa=m.supa, escrever=lista.append) == 0
    assert any(CR.ROTULO_DA_CORRETORA in l and CR.mascarar(LOGIN) in l and "ativo" in l for l in lista), lista


# ④ ===================================================================================================================
def _semear_calculo(m, company_id, conta_id, quando):
    pid = str(uuid4())
    m.banco.semear("multicalculo_pedidos", {"id": pid, "company_id": company_id, "origem": "quem_cobra_menos",
                                            "pedido_cifrado": "x"})
    m.banco.semear("multicalculo_calculos", {"pedido_id": pid, "solicitante_company_id": company_id,
                                             "company_id": company_id, "opcao": "padrao", "coberturas": {},
                                             "account_id": conta_id, "disparado_em": quando, "status": "falhou"})


def test_desconectar_apaga_a_senha_do_cofre_pausa_e_o_historico_fica(mundo):
    m = mundo
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    [conta] = _da_tela(m, m.a)
    _semear_calculo(m, m.a, conta["id"], QUARTA_MEIO_DIA.isoformat())
    r = _post(m, m.a, "desconectar")
    assert r.status_code == 200, r.text
    [conta] = _da_tela(m, m.a)
    assert conta["secret_encrypted"] is None and conta["robo_estado"] == "pausado"
    assert len([c for c in m.banco.linhas("multicalculo_calculos") if c["account_id"] == conta["id"]]) == 1
    retrato = r.json()["conta"]
    assert retrato["situacao"] == "desconectado" and retrato["acoes"][0] == "conectar"
    assert _post(m, m.a, "religar").status_code == 409, "sem senha não religa"
    assert ROB.escolher(m.supa, m.a, "quem_cobra_menos", dono="m", agora=QUARTA_MEIO_DIA) is None
    # reconectar volta a MESMA conta (o histórico continua apontando para ela)
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    [de_novo] = _da_tela(m, m.a)
    assert de_novo["id"] == conta["id"] and de_novo["robo_estado"] == "ativo"


# ⑤ ===================================================================================================================
def test_a_senha_nunca_aparece_em_resposta_nem_em_log(mundo, caplog, monkeypatch):
    m = mundo
    caplog.set_level(logging.DEBUG)
    respostas = [
        _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA),
        _get(m, m.a),
        _post(m, m.a, "pausar"),
        _post(m, m.a, "religar"),
        _post(m, m.a, "janela", janela={"dias": "seg-sex", "inicio": "08:00", "fim": "18:00"}),
        _post(m, m.a, "janela", janela={"dias": "toda hora", "inicio": "x", "fim": "y"}),   # recusa
        _post(m, m.a, "trocar_senha", senha=SENHA + "-2"),
    ]
    assert [r.status_code for r in respostas] == [200, 200, 200, 200, 200, 409, 200]
    # o erro INESPERADO com a senha no corpo da exceção (a linha do banco ecoada) não vaza
    def explode(*a, **k):
        raise ValueError(f"linha com {SENHA} e {LOGIN}")
    monkeypatch.setattr(CR, "trocar_senha", explode)
    respostas.append(_post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA))
    assert respostas[-1].status_code == 500
    [conta] = _da_tela(m, m.a)
    tudo = "\n".join(r.text for r in respostas) + "\n" + caplog.text
    for segredo in (SENHA, LOGIN, conta["secret_encrypted"], "secret_encrypted", "robo_dono"):
        assert segredo not in tudo, segredo
    assert CR.mascarar(LOGIN) in respostas[1].text, "CONTROLE: o login mascarado aparece (o guarda consegue falhar)"


# ⑥ ===================================================================================================================
def test_os_estados_da_tela_vem_do_que_o_robo_grava(mundo):
    m = mundo
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    [conta] = _da_tela(m, m.a)
    # o motor recusou a senha → `bloqueado` (o CAS do motor, `robos.marcar_estado`)
    assert ROB.marcar_estado(m.supa, {**conta, "robo_estado": "ativo"}, ROB.BLOQUEADO)
    c = _get(m, m.a).json()["conta"]
    assert c["situacao"] == "senha_recusada" and "recusou" in c["rotulo"] and "religar" not in c["acoes"]
    assert _post(m, m.a, "religar").status_code == 409, "senha recusada só volta trocando a senha"
    assert _post(m, m.a, "trocar_senha", senha="Senha-Certa-Ficticia").status_code == 200
    # o 1º cálculo saiu → "funcionando", com o último uso
    _semear_calculo(m, m.a, conta["id"], QUARTA_MEIO_DIA.isoformat())
    c = _get(m, m.a).json()["conta"]
    assert c["situacao"] == "funcionando" and c["ultimo_uso"], c
    assert _post(m, m.a, "pausar").json()["conta"]["situacao"] == "pausado"
    assert _post(m, m.a, "religar").json()["conta"]["situacao"] == "funcionando"


def test_duas_gravacoes_pela_tela_dao_uma_conta_so(mundo):
    """D-131-0-04 (gerente, nota 92): até a SPEC-131-0, UMA conta Agger por corretora pela tela — a global.
    📊 O motor trata TODAS as contas Agger da corretora como um rodízio único (`robos.candidatos`): uma segunda conta
    entrando pela tela (o Agger de uma comercial) faria o Quem Cobra Menos cotar nela."""
    from portal_worker import vault

    m = mundo
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    r = _post(m, m.a, "conectar", usuario="outro-" + LOGIN, senha="Outra-Senha-Ficticia")
    assert r.status_code == 200, r.text
    assert len(_contas(m, m.a)) == 1, "salvar de novo atualiza a MESMA conta"
    [conta] = _contas(m, m.a)
    assert conta["username"] == "outro-" + LOGIN and vault.decrypt(conta["secret_encrypted"]) == "Outra-Senha-Ficticia"
    assert conta["robo_estado"] == "ativo"
    assert not [a for a in r.json()["conta"]["acoes"] if "adicionar" in a or "outr" in a], "sem 'adicionar outro'"
    assert len(ROB.candidatos(m.supa, m.a)) == 1, "o rodízio do motor vê UMA conta"


def test_a_tela_generica_de_credenciais_continua_recusando_o_agger(mundo):
    """D-129B-11 continua no `/credentials`: o upsert genérico gravaria login/senha sem estado de robô."""
    m = mundo
    r = m.cli.post("/api/portal/credentials", headers={"X-AutoBrokers-Internal-Key": CHAVE},
                   json={"company_id": m.a, "portal_key": "agger", "username": LOGIN, "password": SENHA})
    assert r.status_code == 403 and not _contas(m, m.a)


# ⑦ ===================================================================================================================
# CONSERTO 133-A.1 (red R1 · P2): o MESMO login do Agger em duas contas de robô da corretora = duas sessões que se
# derrubam (o motor gira entre as duas: `robos.escolher`). O serviço único recusa — pela tela E pelo comando.
def _ativas(m, company_id):
    return [c for c in ROB.candidatos(m.supa, company_id) if c["robo_estado"] == "ativo"]


def test_R1_o_mesmo_login_nao_entra_em_duas_contas_do_robo(mundo):
    from portal_worker import vault

    m = mundo
    CR.cadastrar(m.supa, company_id=m.a, rotulo="robo-1", usuario=LOGIN, senha="Senha-Robo1-Ficticia",
                 estado="ativo", janela=None, teto=None, cifrar=vault.encrypt)
    # a tela com o MESMO login — escrito com caixa e espaços diferentes — é recusada, e nada é gravado
    r = _post(m, m.a, "conectar", usuario="  " + LOGIN.upper().replace("@", " @") + " ", senha=SENHA)
    assert r.status_code == 409, r.text
    assert "outra conta do robô" in r.json()["detail"] and "trocar senha" in r.json()["detail"]
    assert not _da_tela(m, m.a) and len(_ativas(m, m.a)) == 1
    # CONTROLE: outro login entra (o guarda não recusa tudo)
    assert _post(m, m.a, "conectar", usuario="outro-" + LOGIN, senha=SENHA).status_code == 200
    # trocar o login da tela PARA o do robo-1 também é recusado (o login antigo e a senha antiga ficam)
    [antes] = _da_tela(m, m.a)
    assert _post(m, m.a, "trocar_senha", usuario=LOGIN, senha="Outra-Ficticia-1").status_code == 409
    [depois] = _da_tela(m, m.a)
    assert depois == antes
    # o COMANDO: cadastrar outro robô com o login que a tela usa → recusa (sem pedir a senha)
    saida, pediu = [], []
    rc = CMD.main(["cadastrar", "--corretora", m.a, "--rotulo", "robo-3", "--usuario", "Outro-" + LOGIN,
                   "--estado", "ativo"], supa=m.supa, ler_senha=lambda: pediu.append(1) or "x-ficticia",
                  cifrar=vault.encrypt, escrever=saida.append)
    assert rc != 0 and not pediu and any("outra conta do robô" in s for s in saida), saida
    assert len(_ativas(m, m.a)) == 2 and len({c["username"].lower() for c in _ativas(m, m.a)}) == 2
    # a OUTRA corretora pode usar o mesmo login (a regra é por corretora)
    assert _post(m, m.b, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200


def test_R1_conta_sem_senha_nao_prende_o_login_e_religar_confere(mundo):
    """A conta desconectada (sem senha) não roda — não prende o login. Mas devolver a senha a ela (trocar-senha) ou
    religar uma duplicata antiga com senha é recusado enquanto outra conta usa o login."""
    from portal_worker import vault

    m = mundo
    velha = CR.cadastrar(m.supa, company_id=m.a, rotulo="robo-1", usuario=LOGIN, senha="Senha-Velha-Ficticia",
                         estado="ativo", janela=None, teto=None, cifrar=vault.encrypt)
    CR.apagar_senha(m.supa, {"id": velha["id"], "company_id": m.a})
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    with pytest.raises(CR.Recusa, match="outra conta do robô"):
        CR.trocar_senha(m.supa, {"id": velha["id"], "company_id": m.a}, "Nova-Ficticia-2", cifrar=vault.encrypt)
    # a duplicata do legado (as duas com senha): religar a pausada é recusado
    m.banco.semear("portal_accounts", {"id": str(uuid4()), "company_id": m.a, "portal_key": "agger",
                                       "account_label": "robo-legado", "username": LOGIN.upper(),
                                       "secret_encrypted": vault.encrypt("x-ficticia"), "health": "unknown",
                                       "robo_estado": "pausado", "robo_janela": None, "robo_teto_por_hora": None})
    leg = next(c for c in _contas(m, m.a) if c["account_label"] == "robo-legado")
    with pytest.raises(CR.Recusa, match="outra conta do robô"):
        CR.religar(m.supa, leg, "ativo")
    assert next(c for c in _contas(m, m.a) if c["account_label"] == "robo-legado")["robo_estado"] == "pausado"
    assert len(_ativas(m, m.a)) == 1


# ⑧ ===================================================================================================================
# CONSERTO (red R2 · P3): senha RECUSADA pelo Agger (`bloqueado`) só volta com senha NOVA — o servidor confere as
# ações do estado, não só a tela. Cada volta com a senha velha é mais um login errado no Agger (risco de travar).
def test_R2_bloqueado_so_volta_com_senha_nova(mundo):
    m = mundo
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    [c] = _da_tela(m, m.a)
    assert ROB.marcar_estado(m.supa, {**c, "robo_estado": "ativo"}, ROB.BLOQUEADO)
    r = _post(m, m.a, "pausar")
    assert r.status_code == 409 and "troque a senha" in r.json()["detail"].lower(), r.text
    assert _da_tela(m, m.a)[0]["robo_estado"] == "bloqueado", "pausar numa bloqueada não muda nada"
    assert _post(m, m.a, "religar").status_code == 409
    assert _da_tela(m, m.a)[0]["robo_estado"] == "bloqueado"
    with pytest.raises(CR.Recusa):  # o comando também: o serviço é um só
        CR.pausar(m.supa, _da_tela(m, m.a)[0])
    assert _da_tela(m, m.a)[0]["robo_estado"] == "bloqueado"
    # CONTROLE: com a senha NOVA ela volta
    assert _post(m, m.a, "trocar_senha", senha="Senha-Nova-Ficticia-3").status_code == 200
    assert _da_tela(m, m.a)[0]["robo_estado"] == "ativo"
    # pausar duas vezes (clique duplo) não é erro
    assert _post(m, m.a, "pausar").status_code == 200 and _post(m, m.a, "pausar").status_code == 200


# ⑨ ===================================================================================================================
# CONSERTO (red R3 · P3): a tela só toca na conta GLOBAL de robô — nunca numa conta `teste` (login de PESSOA).
def test_R3_a_tela_nunca_toca_em_conta_de_pessoa_e_o_rotulo_e_so_do_robo(mundo):
    from portal_worker import vault

    m = mundo
    pessoa = "pessoa-comercial@exemplo.invalid"
    janela = {"dias": "seg-sex", "inicio": "20:00", "fim": "23:59"}
    with pytest.raises(CR.Recusa, match="reservado"):  # a porta do comando fecha o rótulo para `teste`
        CR.cadastrar(m.supa, company_id=m.a, rotulo=CR.ROTULO_DA_CORRETORA, usuario=pessoa, senha="x-ficticia",
                     estado="teste", janela=janela, teto=None, cifrar=vault.encrypt)
    # o legado: uma conta `teste` com o rótulo da tela (gravada antes do conserto)
    m.banco.semear("portal_accounts", {"id": str(uuid4()), "company_id": m.a, "portal_key": "agger",
                                       "account_label": CR.ROTULO_DA_CORRETORA, "username": pessoa,
                                       "secret_encrypted": vault.encrypt("x-ficticia"), "health": "unknown",
                                       "robo_estado": "teste", "robo_janela": janela, "robo_teto_por_hora": None})
    [antes] = _da_tela(m, m.a)
    retrato = _get(m, m.a).json()["conta"]
    assert retrato["situacao"] == "teste" and retrato["acoes"] == []
    for acao, extra in (("trocar_senha", {"senha": "nova-ficticia"}), ("conectar", {"usuario": LOGIN, "senha": SENHA}),
                        ("pausar", {}), ("religar", {}), ("desconectar", {}), ("janela", {"janela": janela})):
        r = _post(m, m.a, acao, **extra)
        assert r.status_code == 409 and "pessoa" in r.json()["detail"], (acao, r.text)
    assert _da_tela(m, m.a) == [antes], "nada mudou"
    with pytest.raises(CR.Recusa, match="reservado"):  # nem o comando religa o rótulo como `teste`
        CR.religar(m.supa, {**antes, "robo_estado": "pausado"}, "teste")


# ⑩ ===================================================================================================================
# CONSERTO (red R4 · P3): limites de tamanho — login ≤ 254, senha ≤ 256; vazio recusado.
def test_R4_limites_do_login_e_da_senha(mundo):
    from portal_worker import vault

    m = mundo
    assert _post(m, m.a, "conectar", usuario="a" * 255, senha=SENHA).status_code == 409
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha="s" * 257).status_code == 409
    assert _post(m, m.a, "conectar", usuario="", senha=SENHA).status_code == 409
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha="").status_code == 409
    assert not _contas(m, m.a)
    # CONTROLE: no limite exato entra
    assert _post(m, m.a, "conectar", usuario="a" * 254, senha="s" * 256).status_code == 200
    assert _post(m, m.a, "trocar_senha", usuario="b" * 255, senha=SENHA).status_code == 409
    assert _post(m, m.a, "trocar_senha", senha="s" * 257).status_code == 409
    assert _da_tela(m, m.a)[0]["username"] == "a" * 254
    with pytest.raises(CR.Recusa):
        CR.cadastrar(m.supa, company_id=m.a, rotulo="robo-9", usuario="c" * 255, senha="x-ficticia",
                     estado="ativo", janela=None, teto=None, cifrar=vault.encrypt)
