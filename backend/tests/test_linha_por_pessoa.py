# -*- coding: utf-8 -*-
"""fix/linha-por-pessoa (SPEC-131-0-B2) — `LINHA_DO_USUARIO_LIGADA` ligada SÓ para uma lista de user_id.

O Founder precisa fazer o 1º teste da linha (o canário + a medição M1–M6) pela TELA DE VERDADE sem que mais ninguém
veja o botão. A chave aceita, além de "1/true/on/sim" (todos), uma LISTA de user_id → só essas pessoas: veem o bloco
(estado), conectam (conectar/qr), recebem resposta no webhook e recebem avisos. Ausente, vazia ou lixo = ninguém.
O ponto ÚNICO é `linha_do_usuario.estado.ligada_para(user_id)`.

O motor é o REAL (dublê só na borda — os arreios dos testes da B2, importados, não copiados):
    1. a leitura da chave: "1" → todos · ""/"0"/"abc"/um item torto → ninguém · uuid com espaços/maiúsculas → normaliza
    2. a tela: com a lista = [A], A vê `nao_conectada`, B vê `desligada`; B conectar → recusado SEM chamar o Evolution
    3. o webhook: evento na linha de B (fora da lista) → ignorado como a chave ausente: 0 turno, 0 envio
    4. os avisos: B fora da lista → registro `linha_desligada`, nenhum envio (mesmo com o tipo ligado nos avisos)
    5. quem não é membro ativo da corretora da sessão → `desligada` (o bloco some)

Mutação: `python tests/test_linha_por_pessoa.py --mutar` (`ligada_para` ignora a lista → VERMELHO; restaura por cópia).
⛔ Dados fictícios: uuids sintéticos, "Corretora Alfa/Beta" (CLAUDE.md §13.9). Nenhum user_id real em arquivo nenhum.
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_linha_por_pessoa.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec1310b2_avisos as AV  # noqa: E402  (o banco em memória dos avisos e o dublê do envio)
import test_spec1310b2_entrada as EN  # noqa: E402  (o arreio do webhook da linha)
import test_spec1310b2_pareamento as PA  # noqa: E402  (o arreio do pareamento: Evolution GO falso)
from test_spec132c_o_atalho import fio  # noqa: E402,F401  (fixture)
from test_spec1310b2_entrada import lu  # noqa: E402,F401  (fixture)
from test_spec1310b2_pareamento import mesa  # noqa: E402,F401  (fixture)

from app.services.linha_do_usuario import estado as E  # noqa: E402
from app.services.linha_do_usuario import pareamento as P  # noqa: E402

CHAVE = "LINHA_DO_USUARIO_LIGADA"
A_, B_ = PA.U1, PA.U2          # duas pessoas da MESMA corretora (Alfa) no arreio do pareamento


def _run(coro):
    return asyncio.run(coro)


# =====================================================================================================================
# 1. a leitura da chave — o ponto único
# =====================================================================================================================
@pytest.mark.parametrize("valor", ["1", "true", "TRUE", " on ", "sim", "yes", "ligada"])
def test_um_valor_de_ligado_liga_todos(monkeypatch, valor):
    monkeypatch.setenv(CHAVE, valor)
    assert E.ligada_para(A_) and E.ligada_para(B_) and E.ligada_para(PA.U3) and E.ligada()


@pytest.mark.parametrize("valor", [None, "", "   ", "0", "false", "off", "abc", "nao", "123",
                                   f"{A_},abc", f"{A_};{B_[:-1]}"])
def test_ausente_vazio_ou_lixo_nao_liga_ninguem_e_nao_quebra(monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv(CHAVE, raising=False)
    else:
        monkeypatch.setenv(CHAVE, valor)
    assert not E.ligada_para(A_) and not E.ligada_para(B_) and not E.ligada()
    assert not E.ligada_para(None) and not E.ligada_para("") and not E.ligada_para("abc")


def test_a_lista_liga_so_quem_esta_nela_e_normaliza(monkeypatch):
    monkeypatch.setenv(CHAVE, f"  {A_.upper()} ,  {PA.U3}  ")
    assert E.ligada_para(A_) and E.ligada_para(A_.upper()) and E.ligada_para(f" {A_} ") and E.ligada_para(PA.U3)
    assert not E.ligada_para(B_) and not E.ligada_para(None) and not E.ligada_para("")
    assert E.ligada()                                                # "existe alguém ligado?" → sim
    monkeypatch.setenv(CHAVE, f"{A_}; {B_}\n")                       # ponto e vírgula e quebra de linha também
    assert E.ligada_para(A_) and E.ligada_para(B_) and not E.ligada_para(PA.U3)


# =====================================================================================================================
# 2. a tela: estado, conectar e qr — só quem está na lista
# =====================================================================================================================
def test_a_tela_so_aparece_para_quem_esta_na_lista(mesa, monkeypatch):
    monkeypatch.setenv(CHAVE, A_)
    assert _run(P.estado(mesa.banco, PA.ALFA, A_))["estado"] == "nao_conectada"
    assert _run(P.estado(mesa.banco, PA.ALFA, B_)) == {"estado": "desligada", "numero_mascarado": None,
                                                       "desde": None, "motivo": None}
    # B tenta conectar (ex.: chamando a rota direto) → recusado ANTES de tocar no Evolution
    r = _run(P.conectar(mesa.banco, PA.ALFA, B_))
    assert r["estado"] == "desligada" and r["qr"] is None and r["motivo"] == E.FRASE_DESLIGADA
    assert _run(P.qr(mesa.banco, PA.ALFA, B_))["estado"] == "desligada"
    assert mesa.evo.pedidos == [] and PA._linhas_da_linha(mesa.banco) == []
    # CONTROLE: A, na lista, conecta de verdade (o Evolution é chamado e o QR é dele)
    ra = _run(P.conectar(mesa.banco, PA.ALFA, A_))
    assert ra["estado"] == "aguardando_qr" and ra["qr"] and mesa.evo.pedidos
    assert [x["owner_user_id"] for x in PA._linhas_da_linha(mesa.banco)] == [A_]


def test_a_api_da_tela_respeita_a_lista(mesa, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.linha_do_usuario as API

    monkeypatch.setattr(API, "_db", lambda: mesa.banco)
    app = FastAPI()
    app.include_router(API.router)
    c, h = TestClient(app), {"X-AutoBrokers-Internal-Key": PA.CHAVE_INTERNA}
    monkeypatch.setenv(CHAVE, A_.upper())
    assert c.get("/api/linha-do-usuario/estado", headers=h,
                 params={"company_id": PA.ALFA, "user_id": B_}).json()["estado"] == "desligada"
    rb = c.post("/api/linha-do-usuario/conectar", headers=h,
                json={"company_id": PA.ALFA, "user_id": B_, "por_user_id": B_})
    assert rb.status_code == 200 and rb.json()["estado"] == "desligada" and mesa.evo.pedidos == []
    assert c.get("/api/linha-do-usuario/estado", headers=h,
                 params={"company_id": PA.ALFA, "user_id": A_}).json()["estado"] == "nao_conectada"


def test_quem_nao_e_membro_da_corretora_ve_desligada(mesa, monkeypatch):
    monkeypatch.setenv(CHAVE, "1")
    assert _run(P.estado(mesa.banco, PA.ALFA, PA.U3))["estado"] == "desligada"     # U3 é só da Beta
    assert _run(P.estado(mesa.banco, PA.ALFA, PA.FORA))["estado"] == "desligada"   # de corretora nenhuma
    assert _run(P.estado(mesa.banco, PA.BETA, PA.U3))["estado"] == "nao_conectada"  # CONTROLE: na dele, aparece
    monkeypatch.setenv(CHAVE, PA.U3)                                                 # na lista, mas da corretora errada
    assert _run(P.estado(mesa.banco, PA.ALFA, PA.U3))["estado"] == "desligada"
    assert mesa.evo.pedidos == []


# =====================================================================================================================
# 3. o webhook: a linha cujo DONO está fora da lista é contada e ignorada (como a chave ausente)
# =====================================================================================================================
def test_o_webhook_ignora_a_linha_de_quem_esta_fora_da_lista(lu, monkeypatch):
    monkeypatch.setenv(CHAVE, EN.U1)                                 # só o dono da linha A (Alfa)
    escritas = len(lu.banco.escritas)
    r = lu.postar("oi, quanto fica o seguro?", token=EN.TOKEN_B, chat=EN.JID_B)   # a linha de U2 (Beta)
    assert r == {"status": "ignored", "reason": "linha_desligada"}
    assert lu.evento({"event": "Connected", "data": {}}, token=EN.TOKEN_B)["reason"] == "linha_desligada"
    assert lu.turnos == [] and lu.fio.grafo == [] and lu.fio.envio.enviados == []
    assert lu.banco.escritas[escritas:] == [] and lu.banco.linhas("messages") == []
    assert lu.fio.taps == [] and lu.fio.pipeline == []                # e não caiu no resto do webhook
    # a saída direta pela linha de U2 também não sai
    r = asyncio.run(EN.ENT.enviar_pela_linha(lu.banco, E.linha_do_dono(lu.banco, EN.BETA, EN.U2), "oi"))
    assert r["enviadas"] == 0 and r["motivo"] == "desligada"
    # CONTROLE: a linha de U1 (na lista) responde
    assert lu.postar("quanto fica o seguro do meu cliente?")["status"] == "accepted"
    assert lu.turnos == [1] and lu.da_linha("int-linha-a") and lu.da_linha("int-linha-b") == []


# =====================================================================================================================
# 4. os avisos: a pessoa fora da lista → 'linha_desligada', nada sai
# =====================================================================================================================
def _avisos_mundo(monkeypatch):
    banco = AV.Banco(company_members=[AV._membro(AV.ALFA, AV.U1), AV._membro(AV.BETA, AV.U3)],
                     integrations=[AV._linha(AV.ALFA, AV.U1), AV._linha(AV.BETA, AV.U3)],
                     linha_avisos_registro=[], linha_mensagens_do_sistema=[])
    envio = AV.EnvioDaLinha()
    modulo = types.ModuleType(AV.MODULO_DA_L2)
    modulo.enviar_pela_linha = envio.enviar_pela_linha
    monkeypatch.setitem(sys.modules, AV.MODULO_DA_L2, modulo)
    monkeypatch.setenv(AV.CHAVE, "renovacoes_calculadas,licenca_do_agger,falha_de_conexao")   # os avisos LIGADOS
    from app.services.linha_do_usuario import avisos

    return banco, envio, avisos


def _avisar(avisos, banco, cid, uid):
    return asyncio.run(avisos.avisar(banco, company_id=cid, user_id=uid, tipo="renovacoes_calculadas",
                                     texto_markdown="Renovações de hoje: 2 calculadas."))   # 💭 ilustrativo


def test_aviso_para_quem_esta_fora_da_lista_so_registra(monkeypatch):
    banco, envio, avisos = _avisos_mundo(monkeypatch)
    monkeypatch.setenv(CHAVE, AV.U3)                                 # só U3 (Beta); U1 fora
    r = _avisar(avisos, banco, AV.ALFA, AV.U1)
    assert (r["enviado"], r["motivo"], r["registrado"]) == (False, "linha_desligada", True)
    assert envio.chamadas == []
    (reg,) = banco.registro(company_id=AV.ALFA, user_id=AV.U1)
    assert reg["enviado"] is False and reg["motivo_nao_enviado"] == "linha_desligada"
    assert "linha_desligada" in avisos.FRASES
    # chave ausente: ninguém recebe, mesmo com os avisos ligados
    monkeypatch.delenv(CHAVE)
    assert _avisar(avisos, banco, AV.BETA, AV.U3)["motivo"] == "linha_desligada" and envio.chamadas == []
    # CONTROLE: U3 na lista → o aviso sai pela linha DELE
    monkeypatch.setenv(CHAVE, AV.U3)
    r3 = _avisar(avisos, banco, AV.BETA, AV.U3)
    assert r3["enviado"] is True and len(envio.chamadas) == 1
    assert envio.chamadas[0]["linha"]["owner_user_id"] == AV.U3


# =====================================================================================================================
# a MUTAÇÃO (por cópia) — `python tests/test_linha_por_pessoa.py --mutar`
# =====================================================================================================================
MUTACOES = [
    ("ligada_para ignora a lista (qualquer valor volta a ligar TODOS)",
     "app/services/linha_do_usuario/estado.py",
     "    return str(user_id or \"\").strip().lower() in lista\n",
     "    return bool(str(os.getenv(CHAVE_LIGADA) or \"\").strip())\n",
     "test_"),
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
            print(f"{rotulo}: {'VERMELHO (o guarda pegou)' if vermelho else 'MUTACAO NAO PEGOU'}")
            print("\n".join(l for l in r.stdout.splitlines() if l.startswith("FAILED") or "passed" in l
                            or "failed" in l)[-2500:])
            falhas += 0 if vermelho else 1
        finally:
            caminho.write_bytes(bruto)                          # 🔴 restaura POR CÓPIA DOS BYTES
            assert caminho.read_bytes() == bruto, f"{rotulo}: {arquivo} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())
