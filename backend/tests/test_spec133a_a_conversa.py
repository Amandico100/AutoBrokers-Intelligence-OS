# -*- coding: utf-8 -*-
"""SPEC-133-A F2 — A CONVERSA do canal (U4 · U5 · U6) e O TESTE DO FIO da fatia.

O FIO (o card da SPEC §1, do lado da F2), com o MOTOR real em cada elo — dublê só na borda (CLAUDE.md §9.4):

    "oi" → conversa.responder (estado vazio) → consentimento "sim" → as respostas (placa, CEP, CPF fictício válido…)
      → Resposta.disparar (o perfil) → cotacao.disparar → MulticalculoProvider.calcular REAL (origem='canal',
        corretoras = as adesões ATIVAS do canal, opcoes = OPCOES_DO_CANAL) — nunca PerfilIncompleto/PedidoIncompleto
        só com a placa → Work Run `canal.cotacao` (WorkRunService.criar REAL → RPC) → o motor grava o quadro (dublê do
        portal-worker) → SmithWorker._processar REAL → workflow canal.cotacao → porta.consultar → publicar_proposta REAL
        (Hub + marca + comparação) → mensagem_para → os balões chegam ao dublê de `envio.enviar` com "Prontinho" e /r/
      → runs.dormir → relógio → despertar_vencidos → lembrete 1 → lembrete 2 → NUNCA um 3º.

Borda: o banco (PostgREST em memória da 129-B/130-A), o relógio, o modelo, e os módulos da F1 (`repositorio`, `envio`
— escritos em PARALELO contra o contrato §3; aqui, dublês com as MESMAS assinaturas).

⛔ Dados fictícios: CPF sintético com DV válido, placa/telefone/nome inventados (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a_a_conversa.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cryptography.fernet import Fernet  # noqa: E402

import dubles_do_work_os as D  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402

BASE = "https://app.exemplo.test"
TEL = "+5500900000001"          # DDD 00 não existe: telefone impossível de ser de alguém
TEL_2 = "+5500900000002"
CPF_FICTICIO = "529.982.247-25"  # DV válido, inventado (o mesmo dos testes da 129-B)
CHAVE_HMAC = "chave-hmac-sintetica-de-teste-0123456789"


# =====================================================================================================================
# os dublês da F1 (contrato §3) — mesmas assinaturas, estado em memória
# =====================================================================================================================
class RepoDuble:
    def __init__(self):
        self.estados: dict = {}
        self.consentimentos: list = []
        self.leads: list = []

    def eh_canal(self, db, company_id):
        return True

    def registrar_consentimento(self, db, company_id, telefone_e164, *, aceito, versao_do_texto):
        self.consentimentos.append((company_id, telefone_e164, aceito, versao_do_texto))

    def registrar_lead(self, db, company_id, telefone_e164, *, primeiro_nome=None, pedido_id=None):
        self.leads.append((company_id, telefone_e164, primeiro_nome, pedido_id))

    def carregar_estado(self, db, company_id, telefone_e164):
        return copy.deepcopy(self.estados.get((company_id, telefone_e164), {}))

    def salvar_estado(self, db, company_id, telefone_e164, estado):
        self.estados[(company_id, telefone_e164)] = copy.deepcopy(estado)

    # o teto do dia (costura 133-A: o resultado e os lembretes do run contam nele) — a régua REAL da F1
    enviadas: dict = {}

    def teto_de_mensagens(self, config):
        from app.services.multicalculo.config import PADRAO_DO_PRODUTO

        chave = "teto_mensagens_por_dia"
        return int(((config or {}).get("canal") or {}).get(chave) or PADRAO_DO_PRODUTO["canal"][chave])

    def enviadas_hoje(self, db, company_id, telefone_e164):
        return self.enviadas.get((company_id, telefone_e164), 0)

    def contar_enviadas(self, db, company_id, telefone_e164, quantas):
        self.enviadas[(company_id, telefone_e164)] = self.enviadas_hoje(db, company_id, telefone_e164) + quantas
        return self.enviadas[(company_id, telefone_e164)]

    def mascarar(self, telefone):
        return "..." + str(telefone)[-4:]

    # conserto 133-A (item 4): o run confere o convite ANTES de cada lembrete — o dublê responde como a F1 (o convidado
    # ativo, ou None depois de removido)
    removidos: set = set()

    def convidado(self, db, company_id, telefone_e164):
        return None if (company_id, telefone_e164) in self.removidos else {"id": "convidado-ficticio"}


class EnvioDuble:
    def __init__(self):
        self.enviados: list = []      # (company_id, telefone, [balões])

    async def enviar(self, db, company_id, telefone_e164, baloes):
        self.enviados.append((company_id, telefone_e164, list(baloes)))
        return len(baloes)

    @staticmethod
    def numero_do_canal(db, company_id):
        """O número pareado da integração ATIVA do canal (a régua da F1, sobre o MESMO banco do mundo)."""
        linhas = getattr(db.table("integrations").select("*").eq("company_id", company_id).eq("is_active", True)
                         .execute(), "data", None) or []
        dig = "".join(ch for l in linhas[:1] for ch in str(l.get("paired_phone_e164") or "") if ch.isdigit())
        return dig or None

    def textos(self, telefone=TEL):
        return ["\n".join(b) for (_c, t, b) in self.enviados if t == telefone]


class ModeloProibido:
    """O fio responde só por REGRA: se o modelo for chamado, o teste quebra (CPF/placa nunca vão ao modelo)."""

    def __init__(self):
        self.chamadas = 0

    async def ainvoke(self, mensagens):
        self.chamadas += 1
        raise AssertionError("o modelo foi chamado numa resposta que a regra entende")


@pytest.fixture
def canal(monkeypatch):
    """Instala os dublês da F1 como `app.services.canal.repositorio` / `.envio` (o pacote pode ainda não existir)."""
    try:
        import app.services.canal as pacote  # noqa: F401
    except Exception:  # noqa: BLE001 — o __init__ é da F1; antes dele, um pacote-namespace com o MESMO caminho
        pacote = types.ModuleType("app.services.canal")
        pacote.__path__ = [str(BACKEND / "app" / "services" / "canal")]
        monkeypatch.setitem(sys.modules, "app.services.canal", pacote)
    repo, envio = RepoDuble(), EnvioDuble()
    mod_repo = types.ModuleType("app.services.canal.repositorio")
    mod_env = types.ModuleType("app.services.canal.envio")
    repo.enviadas = {}
    repo.removidos = set()
    for nome in ("eh_canal", "registrar_consentimento", "registrar_lead", "carregar_estado", "salvar_estado",
                 "teto_de_mensagens", "enviadas_hoje", "contar_enviadas", "mascarar", "convidado"):
        setattr(mod_repo, nome, getattr(repo, nome))
    mod_env.enviar = envio.enviar
    mod_env.numero_do_canal = envio.numero_do_canal
    monkeypatch.setitem(sys.modules, "app.services.canal.repositorio", mod_repo)
    monkeypatch.setitem(sys.modules, "app.services.canal.envio", mod_env)
    monkeypatch.setattr(pacote, "repositorio", mod_repo, raising=False)
    monkeypatch.setattr(pacote, "envio", mod_env, raising=False)
    from app.services.canal import conversa, cotacao, workflows  # noqa: F401

    return types.SimpleNamespace(repo=repo, envio=envio, conversa=conversa, cotacao=cotacao, workflows=workflows)


def rodar(coro):
    return asyncio.run(coro)


def falar(c, db, company_id, falas, *, telefone=TEL, estado=None, llm=None, midia=None):
    """Um turno por fala, como `entrada.turno` faz: responder → salvar_estado → enviar."""
    estado = c.repo.carregar_estado(db, company_id, telefone) if estado is None else estado
    r = None
    for f in falas:
        r = rodar(c.conversa.responder(db, company_id, telefone, f, midia, estado, config=None,
                                       llm=llm or ModeloProibido()))
        c.repo.salvar_estado(db, company_id, telefone, r.estado)
        if r.baloes:
            rodar(c.envio.enviar(db, company_id, telefone, r.baloes))
        estado = r.estado
    return r


#: as respostas reais de uma pessoa, uma por pergunta (ver o roteiro em `conversa.ROTEIRO`)
FALAS_DO_PERFIL = ["ABC1D23", "01001-000", "não", "uns 800 km", "não", CPF_FICTICIO, "Pessoa Sintetica Teste",
                   "01/02/1980", "homem", "20", "3.500"]


# =====================================================================================================================
# o motor (dublê do portal-worker): grava o quadro do canário nos cálculos que a PORTA enfileirou
# =====================================================================================================================
def motor_grava_o_quadro(banco, *, pedido_id: str, dados: dict) -> int:
    """Como o motor deixaria: padrão/econômica com as ofertas REAIS do canário (saneadas); a mínima sem preço."""
    calcs = [c for c in banco.linhas("multicalculo_calculos") if c["pedido_id"] == pedido_id]
    fonte = {(e["corretora_company_id"], e["opcao"]): e for e in dados["estados"]}
    gravadas = 0
    for c in calcs:
        e = fonte.get((c["company_id"], c["opcao"]))
        if e is None:
            banco.linhas("multicalculo_calculos")[banco.linhas("multicalculo_calculos").index(c)].update(
                {"status": "falhou", "erro": "sem resposta da seguradora"})
            continue
        c.update({"status": "fechado", "negocio_ref": f"negocio-{e['versao']}", "versao": e["versao"],
                  "quadro_pronto_em": banco.relogio.iso(), "primeira_oferta_em": banco.relogio.iso()})
        for o in dados["ofertas"]:
            if o["calculo_id"] != e["calculo_id"]:
                continue
            linha = {k: copy.deepcopy(v) for k, v in o.items() if k not in ("corretora_company_id", "id")}
            linha.update({"calculo_id": c["id"], "pedido_id": pedido_id, "company_id": c["company_id"],
                          "solicitante_company_id": c["solicitante_company_id"], "comissao_percentual": 17.37})
            banco.semear("multicalculo_ofertas", linha)
            gravadas += 1
    return gravadas


async def rodar_o_run(db, run_id: str, company_id: str):
    """Uma volta do worker REAL: lease (CAS) → `SmithWorker._processar` (o contexto real) → libera a lease."""
    from app.services.work.runs import WorkRunService
    from app.workers import smith_worker as SW

    w = SW.SmithWorker()
    w.db, w.worker_id = db, "worker-de-teste"
    w.runs = WorkRunService(db)
    lease = w.runs.adquirir_lease(run_id, w.worker_id, company_id)
    assert lease, "o run não pegou lease"
    try:
        await w._processar(run_id, company_id, {"run_id": run_id}, lease_token=lease["lease_token"])
    finally:
        w.runs.liberar_lease(run_id, lease["lease_token"])


def acordar(banco, db, run_id: str):
    """O relógio anda até o `wake_at` do run + 30 s (o despertador do `smith-worker` passa a cada 60 s) e o
    despertador REAL roda com o registro que o worker passa. Sem `wake_at` (concluído, cancelado) → nada acorda."""
    from app.services.work.runs import WorkRunService
    from app.workers import smith_worker as SW

    wake = D._para_ts(banco.run(run_id).get("wake_at"))
    if wake is None:
        return []
    banco.relogio.avancar(max(0.0, (wake - banco.relogio.agora()).total_seconds()) + 30)
    return WorkRunService(db).despertar_vencidos(SW.SmithWorker()._registro_de_workflows())


@pytest.fixture
def mundo(monkeypatch, canal):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", CHAVE_HMAC)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    m.relogio.instalar()
    yield m
    m.relogio.desinstalar()


# =====================================================================================================================
# 🔴 O TESTE DO FIO
# =====================================================================================================================
def test_o_fio_da_conversa(mundo, canal, monkeypatch):
    m, c = mundo, canal
    from app.services.multicalculo import porta as P

    chamadas = []
    original = P.MulticalculoProvider.calcular

    async def espiao(self, **kw):
        chamadas.append(dict(kw))
        return await original(self, **kw)

    monkeypatch.setattr(P.MulticalculoProvider, "calcular", espiao)

    proibido = ModeloProibido()
    # ① "oi" do estado vazio → apresentação + consentimento (nenhuma pergunta de dado pessoal antes do "sim")
    r = falar(c, m.db, m.canal, ["oi"], llm=proibido)
    assert r.estado["etapa"] == "consentimento" and r.disparar is None
    texto = "\n".join(r.baloes)
    assert "o seu CPF e o seu carro vão às seguradoras pelas corretoras parceiras do Quem Cobra Menos, para cotar; " \
           "ninguém é obrigado a fechar" in texto
    assert "placa" not in texto.lower() and "cpf de quem" not in texto.lower()

    # ② "sim" → o consentimento é registrado ANTES da 1ª pergunta
    r = falar(c, m.db, m.canal, ["sim"], llm=proibido)
    assert c.repo.consentimentos == [(m.canal, TEL, True, c.conversa.VERSAO_DO_CONSENTIMENTO)]
    assert "placa" in "\n".join(r.baloes).lower()

    # ③ as respostas reais, uma por pergunta → o perfil completo
    r = falar(c, m.db, m.canal, FALAS_DO_PERFIL, llm=proibido)
    assert proibido.chamadas == 0, "o modelo foi chamado numa resposta que a regra entende (CPF/placa no modelo?)"
    assert r.disparar, f"a conversa não disparou (etapa {r.estado.get('etapa')})"
    assert r.estado["etapa"] == "calculando"
    assert "calculando" in "\n".join(r.baloes).lower()

    # ④ disparar → a porta REAL com origem canal, as adesões ATIVAS e as opções do canal
    run_id = rodar(c.cotacao.disparar(m.db, m.canal, TEL, r.disparar, r.estado))
    assert run_id
    assert len(chamadas) == 1
    kw = chamadas[0]
    assert kw["origem"] == "canal" and kw["company_id"] == m.canal
    assert sorted(kw["corretoras"]) == sorted([m.alfa, m.beta])
    assert tuple(kw["opcoes"]) == P.OPCOES_DO_CANAL
    pedidos = [p for p in m.banco.linhas("multicalculo_pedidos") if p["origem"] == "canal"]
    assert len(pedidos) == 1 and pedidos[0]["company_id"] == m.canal
    assert sorted(set(pedidos[0]["corretoras"])) == sorted([m.alfa, m.beta])
    run = m.banco.run(run_id)
    assert run["workflow_key"] == "canal.cotacao" and run["company_id"] == m.canal
    # 🔴 o payload do run (que vai ao banco em claro) não leva telefone, CPF, placa nem nome
    bruto = json.dumps(run["input_payload"], ensure_ascii=False)
    for proibido in ("0090000000", "52998224725", "529.982", "ABC1D23", "Sintetica"):
        assert proibido not in bruto, proibido
    estado = c.repo.carregar_estado(m.db, m.canal, TEL)
    assert estado["pedido_id"] == pedidos[0]["id"] and estado["run_id"] == run_id
    assert "52998224725" not in json.dumps(estado), "o CPF ficou no estado depois do disparo"
    assert c.repo.leads and c.repo.leads[-1][3] == pedidos[0]["id"]

    # ⑤ o motor grava o quadro → o run acompanha, publica e entrega
    assert motor_grava_o_quadro(m.banco, pedido_id=pedidos[0]["id"], dados=m.dados) > 0
    antes = len(c.envio.enviados)
    rodar(rodar_o_run(m.db, run_id, m.canal))
    novos = ["\n".join(b) for (_c, t, b) in c.envio.enviados[antes:] if t == TEL]
    assert len(novos) == 1, novos
    entrega = novos[0]
    assert "Prontinho" in entrega and f"{BASE}/r/" in entrega
    assert m.banco.run(run_id)["status"] == "waiting_input"          # dorme até o lembrete 1
    estado = c.repo.carregar_estado(m.db, m.canal, TEL)
    assert estado["etapa"] == "resultado" and estado["resultado"]["url"].startswith(f"{BASE}/r/")
    assert estado["resultado"]["anfitria_nome"] == M.MARCA_ALFA

    # ⑥ sem resposta: lembrete 1 → lembrete 2 → e NUNCA um 3º
    lembretes = []
    for _ in range(8):
        acordou = acordar(m.banco, m.db, run_id)
        if not acordou:
            continue
        antes = len(c.envio.enviados)
        rodar(rodar_o_run(m.db, run_id, m.canal))
        lembretes += ["\n".join(b) for (_c, t, b) in c.envio.enviados[antes:] if t == TEL]
    assert len(lembretes) == 2, lembretes
    assert m.banco.run(run_id)["status"] == "completed"
    for t in lembretes:
        baixo = t.lower()
        assert not any(p in baixo for p in ("mais barato do mercado", "corra", "só hoje", "expira em")), t


def test_resposta_depois_do_resultado_cancela_os_lembretes(mundo, canal):
    m, c = mundo, canal
    falar(c, m.db, m.canal, ["oi", "sim"] + FALAS_DO_PERFIL)
    estado = c.repo.carregar_estado(m.db, m.canal, TEL)
    r = falar(c, m.db, m.canal, ["3.500"], estado={**estado, "etapa": "premio"})   # o mesmo disparo, idempotente
    run_id = rodar(c.cotacao.disparar(m.db, m.canal, TEL, r.disparar, r.estado))
    pedido_id = c.repo.carregar_estado(m.db, m.canal, TEL)["pedido_id"]
    motor_grava_o_quadro(m.banco, pedido_id=pedido_id, dados=m.dados)
    rodar(rodar_o_run(m.db, run_id, m.canal))
    # a pessoa responde → a conversa marca no estado e pede o cancelamento do run
    falar(c, m.db, m.canal, ["vou pensar, obrigado"],
          llm=types.SimpleNamespace(ainvoke=_responde_json({"valor": "duvida", "fora_do_escopo": False})))
    estado = c.repo.carregar_estado(m.db, m.canal, TEL)
    assert estado.get("respondeu_em")
    antes = len(c.envio.enviados)
    for _ in range(4):
        if acordar(m.banco, m.db, run_id):
            rodar(rodar_o_run(m.db, run_id, m.canal))
    assert [t for (_c, t, _b) in c.envio.enviados[antes:]] == [], "lembrete saiu depois da resposta"
    assert m.banco.run(run_id)["status"] in ("cancelled", "completed")


def test_o_guarda_do_lembrete_le_o_estado_mesmo_sem_o_cancelamento(mundo, canal, monkeypatch):
    """Linha de controle do G8: tira o cancelamento do run — o lembrete continua NÃO saindo (o estado manda)."""
    m, c = mundo, canal
    monkeypatch.setattr(c.cotacao, "cancelar_lembretes", lambda *a, **k: False)
    r = falar(c, m.db, m.canal, ["oi", "sim"] + FALAS_DO_PERFIL)
    run_id = rodar(c.cotacao.disparar(m.db, m.canal, TEL, r.disparar, r.estado))
    motor_grava_o_quadro(m.banco, pedido_id=c.repo.carregar_estado(m.db, m.canal, TEL)["pedido_id"], dados=m.dados)
    rodar(rodar_o_run(m.db, run_id, m.canal))
    falar(c, m.db, m.canal, ["não, obrigado"])
    antes = len(c.envio.enviados)
    for _ in range(4):
        if acordar(m.banco, m.db, run_id):
            rodar(rodar_o_run(m.db, run_id, m.canal))
    assert [b for (_c, t, b) in c.envio.enviados[antes:]] == []
    assert m.banco.run(run_id)["status"] == "completed"


def _responde_json(obj):
    async def ainvoke(_mensagens):
        return types.SimpleNamespace(content=json.dumps(obj))
    return ainvoke


# =====================================================================================================================
# G4 — o consentimento vem antes de qualquer dado pessoal; "não" encerra sem guardar nada
# =====================================================================================================================
def test_nao_ao_consentimento_encerra_e_nao_guarda_nada(canal):
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    falar(c, db, cid, ["oi"])
    r = falar(c, db, cid, ["não"])
    assert c.repo.consentimentos == [(cid, TEL, False, c.conversa.VERSAO_DO_CONSENTIMENTO)]
    assert set(r.estado) <= {"versao", "etapa", "consentimento", "consentimento_em"}, r.estado
    assert r.estado["etapa"] == "recusou" and r.disparar is None
    assert "não guardei" in "\n".join(r.baloes).lower()


def test_dado_pessoal_antes_do_sim_nao_e_guardado(canal):
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    falar(c, db, cid, ["oi"])
    r = falar(c, db, cid, ["ABC1D23"])                                 # a placa ANTES do sim
    assert r.estado["etapa"] == "consentimento" and "ABC1D23" not in json.dumps(r.estado)
    r = falar(c, db, cid, ["foto"], midia={"tipo": "image", "ref": "midia-ficticia-1"})
    assert "midia-ficticia-1" not in json.dumps(r.estado) and c.repo.consentimentos == []


def test_midia_depois_do_sim_e_guardada_por_referencia_e_a_conversa_segue(canal):
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    falar(c, db, cid, ["oi", "sim"])
    r = falar(c, db, cid, [""], midia={"tipo": "document", "ref": "midia-ficticia-2", "nome": "apolice.pdf"})
    assert r.estado["midias"] == [{"tipo": "document", "ref": "midia-ficticia-2"}]
    assert r.estado["etapa"] == "placa" and "placa" in "\n".join(r.baloes).lower()


# =====================================================================================================================
# a REGRA primeiro; o modelo só para a resposta livre; modelo fora → pergunta de novo, nunca inventa
# =====================================================================================================================
@pytest.mark.parametrize("texto,ok", [("ABC1234", True), ("abc-1d23", True), ("ABC 1D23", True),
                                      ("AB1234", False), ("ABCD123", False), ("1234ABC", False)])
def test_placa_antiga_e_mercosul(canal, texto, ok):
    assert (canal.conversa.validar_placa(texto) is not None) is ok


@pytest.mark.parametrize("texto,ok", [("529.982.247-25", True), ("52998224725", True), ("529.982.247-24", False),
                                      ("111.111.111-11", False), ("1234", False)])
def test_cpf_com_digito_verificador(canal, texto, ok):
    assert (canal.conversa.validar_cpf(texto) is not None) is ok


def test_resposta_livre_vai_ao_modelo_e_o_modelo_e_reconferido_pela_regra(canal):
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    falar(c, db, cid, ["oi", "sim", "ABC1D23", "01001000", "não"])
    llm = types.SimpleNamespace(ainvoke=_responde_json({"valor": 1200, "fora_do_escopo": False}))
    r = falar(c, db, cid, ["rodo bastante, tipo mil e duzentos"], llm=llm)
    assert r.estado["respostas"]["km_mensal"] == 1200 and r.estado["etapa"] == "jovem"
    # o modelo inventa um número fora da régua → a regra recusa e pergunta de novo
    falar(c, db, cid, [], estado={**r.estado, "etapa": "km_mensal"})
    llm_ruim = types.SimpleNamespace(ainvoke=_responde_json({"valor": 999999, "fora_do_escopo": False}))
    r2 = falar(c, db, cid, ["sei lá, muito"], estado={**r.estado, "etapa": "km_mensal"}, llm=llm_ruim)
    assert r2.estado["etapa"] == "km_mensal" and "km" in "\n".join(r2.baloes).lower()


def test_modelo_fora_do_ar_pergunta_de_novo(canal):
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    falar(c, db, cid, ["oi", "sim", "ABC1D23", "01001000", "não"])

    async def quebrado(_m):
        raise TimeoutError("modelo fora")

    r = falar(c, db, cid, ["rodo bastante"], llm=types.SimpleNamespace(ainvoke=quebrado))
    assert r.estado["etapa"] == "km_mensal" and "km_mensal" not in r.estado.get("respostas", {})


def test_o_perfil_da_conversa_fecha_o_pedido_do_canal_so_com_a_placa(canal):
    """G5 — o perfil que a conversa monta passa por `faltando(origem='canal')`, `sem_codigo` e `perfil_faltando`."""
    from app.services.multicalculo.pedido import PedidoDeCalculo

    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    r = falar(c, db, cid, ["oi", "sim"] + FALAS_DO_PERFIL)
    p = PedidoDeCalculo.de_dict(r.disparar["pedido"], assumidos=r.disparar["assumidos"])
    assert p.faltando(origem="canal") == [] and p.sem_codigo() == [] and p.perfil_faltando() == []
    assert p.valor("veiculo", "fipe") is None                       # ninguém perguntou o código FIPE
    assert p.faltando() and set(p.faltando()) == {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"}
    assert r.disparar["premio_atual_declarado"] == 3500.0 and r.disparar["primeiro_nome"] == "Pessoa"


def test_aplicativo_sem_codigo_medido_oferece_a_corretora(canal):
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    r = falar(c, db, cid, ["oi", "sim", "ABC1D23", "01001000", "sim"])
    assert r.disparar is None and r.estado["etapa"] == "oferta_ajuda"
    assert "corretora" in "\n".join(r.baloes).lower()


def test_perfil_fechado_sem_disparo_nao_prende_a_pessoa_em_calculando(canal, monkeypatch):
    """Costura com a F1: o limite do dia barra o `disparar` DEPOIS do perfil fechar. Sem run, a pessoa não fica presa
    em "calculando" e as respostas (CPF) somem do estado."""
    c = canal
    db = object()
    cid = "c1300000-0000-4000-8000-00000000ca1a"
    r = falar(c, db, cid, ["oi", "sim"] + FALAS_DO_PERFIL)
    assert r.disparar and r.estado["etapa"] == "calculando" and not r.estado.get("run_id")
    r2 = falar(c, db, cid, ["e aí?"])
    assert r2.estado["etapa"] == "calculando"                       # logo depois: ainda espera o run
    monkeypatch.setattr(c.conversa, "SEM_DISPARO_APOS_S", -1)
    r3 = falar(c, db, cid, ["e aí?"])
    assert r3.estado["etapa"] == "falhou" and "respostas" not in r3.estado
    assert "52998224725" not in json.dumps(r3.estado)
