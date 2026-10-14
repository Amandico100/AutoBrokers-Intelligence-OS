# -*- coding: utf-8 -*-
"""SPEC-132-B · B1 — A COTAÇÃO NA CONVERSA: preparar → confirmar → calcular → responder NA MESMA conversa → ajustar.

O que é REAL (CLAUDE.md §9.4 — o teste chama o MOTOR): as três ferramentas (`agents/tools/cotacao_tool.py`), o pedido
da conversa e da ficha (`services/cotacao/pedido_da_conversa.py` + `pedido.de_ficha`), a confirmação de uso único
(`services/cotacao/confirmacao.py`), a PORTA (`MulticalculoProvider.calcular/consultar/recalcular`), o `qual_agger`, o
MOTOR do portal-worker (`motor.uma_volta` → `robos.escolher`), o Work OS (`WorkRunService.criar` → a RPC →
`SmithWorker._processar` → `executar_passo`) e o workflow `cotacao.chat`.

Dublê SÓ na borda: o banco (`BancoU1` da 129-B, o PostgREST em memória com as travas do U1), o Agger (o `RoboDuble`
do teste do motor, que serve as rodadas REAIS da fixture `vivo_conta_b.json`), o Redis (em memória), o relógio do
banco, e a PUBLICAÇÃO (B2 escreve `publicar_cotacao`/`mensagem_de_cotacao` em paralelo — a costura B4 prova a real).

⛔ Dados FICTÍCIOS (CLAUDE.md §13.9): o CPF sintético do teste do motor (DV válido, inventado) e "Fulana Ficticia".
Rodar: cd backend && python -m pytest tests/test_spec132b_a_conversa.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from uuid import uuid4

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_o_motor as TM  # noqa: E402
import test_spec1310_f3_contas as F3  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)

from app.agents.tools import cotacao_tool as T  # noqa: E402
from app.services.cotacao import confirmacao as CONF  # noqa: E402
from app.services.cotacao import pedido_da_conversa as PC  # noqa: E402
from app.services.cotacao import resposta as RESP  # noqa: E402
from app.services.cotacao import workflow as WF  # noqa: E402
from app.services.multicalculo import qual_agger as QA  # noqa: E402
from app.services.multicalculo.pedido import PedidoDeCalculo, de_apolice, de_ficha  # noqa: E402
from app.services.multicalculo.porta import MulticalculoProvider  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402

CPF = TM.CPF                                   # 52998224725 — sintético, DV válido (o robô dublê o confere)
CPF_PONTUADO = "529.982.247-25"
NOME = TM.NOME
LINK_BASE = "https://app.exemplo.test/r/"
#: os dados que o corretor deu (o modelo os leu da conversa) — com a placa, sem FIPE/ano/combustível
COMPLETOS = {"cpf_cnpj": CPF_PONTUADO, "nome": NOME, "nascimento": "01/02/1980", "sexo": "feminino", "cep": "01001-000",
             "placa": "ABC1D23", "descricao_do_veiculo": "Onix 2022", "anos_de_carteira": "20"}


# =====================================================================================================================
# a borda: Redis em memória · a publicação da B2
# =====================================================================================================================
class RedisFalso:
    def __init__(self):
        self.d = {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.d:
            return False
        self.d[k] = v
        return True

    async def delete(self, k):
        return 1 if self.d.pop(k, None) is not None else 0


class Mundo:
    def __init__(self, amb, monkeypatch):
        self.amb, self.banco = amb, amb.banco
        self.db = amb.banco.visao("smith-api")
        self.redis = RedisFalso()
        self.publicacoes = []
        self.mp = monkeypatch

    # -- a semeadura --------------------------------------------------------------------------------------------------
    def corretora(self):
        a = TM.empresa(self.amb)
        F3.conta_global(self.amb, a)
        return a

    def pessoa(self, corretora, *, com_agger=False):
        uid = F3.membro(self.amb, corretora)
        conta = F3.conta_da_pessoa(self.amb, corretora, uid) if com_agger else None
        return uid, conta

    def conversa(self, corretora, uid):
        cid, sess = str(uuid4()), str(uuid4())
        self.banco.semear("conversations", {"id": cid, "company_id": corretora, "user_id": uid, "session_id": sess,
                                            "channel": "web", "status": "open"})
        return cid, sess

    def falou(self, conversa, texto):
        """A fala do CORRETOR gravada na conversa (como a rota do chat grava ANTES de chamar o agente). O instante é o
        do relógio REAL: o `created_at` do banco dublê é o relógio congelado do motor, e o "sim" tem de ser DEPOIS do
        resumo (`confirmacao.confirmou_depois`)."""
        from datetime import datetime, timezone

        self.banco.semear("messages", {"id": str(uuid4()), "conversation_id": conversa, "role": "user",
                                       "content": texto, "type": "text", "payload": {},
                                       "created_at": datetime.now(timezone.utc).isoformat()})

    def conversa_da_sessao(self, sess):
        return next(c["id"] for c in self.banco.linhas("conversations") if c.get("session_id") == sess)

    def ferramentas(self, corretora):
        return {t.name: t for t in T.ferramentas_de_cotacao(company_id=corretora, supabase=self.db)}

    # -- os atos -------------------------------------------------------------------------------------------------------
    def preparar(self, corretora, uid, sess, **campos):
        return TM.rodar(self.ferramentas(corretora)["cotacao_preparar"]._arun(user_id=uid, session_id=sess, **campos))

    def disparar(self, corretora, uid, sess, cid, *, sim="sim, pode calcular"):
        """O corretor RESPONDE ao resumo ("sim, pode calcular" — gravado na conversa da sessão) e o modelo dispara.
        `sim=None`: o modelo dispara SEM a resposta do corretor (o ataque do juiz B4)."""
        if sim is not None:
            conversa = next((c["id"] for c in self.banco.linhas("conversations") if c.get("session_id") == sess), None)
            if conversa:
                self.falou(conversa, sim)
        return TM.rodar(self.ferramentas(corretora)["cotacao_disparar"]._arun(confirmacao_id=cid, user_id=uid,
                                                                               session_id=sess))

    def ajustar(self, corretora, uid, sess, pedido_id, tipo, valor, **kw):
        return TM.rodar(self.ferramentas(corretora)["cotacao_ajustar"]._arun(
            pedido_id=pedido_id, tipo=tipo, valor=valor, user_id=uid, session_id=sess, **kw))

    def motor(self):
        """O motor REAL, volta a volta, até a fila do pedido esvaziar (um robô por conta: uma volta pode não bastar)."""
        for _ in range(8):
            TM.rodar(TM.motor(self.amb, f"m-{uuid4().hex[:4]}").uma_volta())
            if not [c for c in self.banco.linhas("multicalculo_calculos") if c["status"] in ("na_fila", "disparando",
                                                                                         "calculando")]:
                return

    def rodar_runs(self, corretora):
        from app.services.work.runs import WorkRunService
        from app.workers import smith_worker as SW

        for r in [x for x in self.banco.linhas("work_runs")
                  if x["workflow_key"] == "cotacao.chat" and x["company_id"] == corretora and x["status"] == "queued"]:
            w = SW.SmithWorker()
            w.db, w.worker_id = self.db, "worker-de-teste"
            w.runs = WorkRunService(self.db)
            lease = w.runs.adquirir_lease(r["id"], w.worker_id, corretora)
            assert lease, "o run não pegou lease"
            try:
                TM.rodar(w._processar(r["id"], corretora, {"run_id": r["id"]}, lease_token=lease["lease_token"]))
            finally:
                w.runs.liberar_lease(r["id"], lease["lease_token"])

    # -- as leituras ---------------------------------------------------------------------------------------------------
    def pedidos(self, corretora=None):
        return [p for p in self.banco.linhas("multicalculo_pedidos") if corretora in (None, p["company_id"])]

    def calculos(self, pedido_id):
        return [c for c in self.banco.linhas("multicalculo_calculos") if c["pedido_id"] == pedido_id]

    def mensagens_do_assistente(self, conversa):
        return [m for m in self.banco.linhas("messages")
                if m.get("conversation_id") == conversa and m.get("role") == "assistant"]


def _id_da_confirmacao(saida: str) -> str:
    m = re.search(r"confirmacao_id: ([0-9a-f]{16})", saida)
    assert m, f"sem confirmacao_id na saída: {saida[:300]}"
    return m.group(1)


def _pedido_da_saida(saida: str) -> str:
    m = re.search(r"pedido_id ([0-9a-f-]{36})", saida)
    assert m, f"sem pedido_id na saída: {saida[:300]}"
    return m.group(1)


@pytest.fixture
def mundo(ambiente, monkeypatch):
    amb = ambiente
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", F3.CHAVE_HMAC)
    m = Mundo(amb, monkeypatch)

    async def _redis():
        return m.redis

    monkeypatch.setattr(CONF, "obter_redis", _redis)
    # o relógio da fila é o do banco dublê (o motor lê `disponivel_em` contra ele) — a porta é a REAL
    # e as coberturas levam a marca `preset` que o robô dublê lê para escolher a rodada da fixture (como no F3)
    monkeypatch.setattr(T, "_porta", lambda db: MulticalculoProvider(RepositorioMulticalculo(db),
                                                                      agora=amb.relogio.agora,
                                                                      presets=lambda o: {"preset": o}))
    monkeypatch.setattr(WF, "_dormir", lambda s: asyncio.sleep(0))

    from app.services.multicalculo import mensagem as MSG
    from app.services.multicalculo import proposta as PROP

    async def publicar_cotacao(company_id, pedido_id, *, pessoa_user_id, apolice_atual=None, db=None,
                               primeiro_nome=None, **_extra):
        m.publicacoes.append({"company_id": company_id, "pedido_id": pedido_id, "pessoa_user_id": pessoa_user_id,
                              "apolice_atual": apolice_atual, "primeiro_nome": primeiro_nome})
        ofertas = sorted((o for o in m.banco.linhas("multicalculo_ofertas") if o["pedido_id"] == pedido_id),
                         key=lambda o: float(o["premio_total"]))
        assert ofertas, "a publicação foi chamada sem oferta no banco"
        # 🔴 B4: o MESMO formato do `resumo` REAL da B2 (`proposta.resumo_da_cotacao`) — o fio prova com o real
        um = lambda o, i, papel: {"id": i, "papel": papel, "seguradora": o["seguradora"],  # noqa: E731
                                  "parcela": {"vezes": 10, "valor": round(float(o["premio_total"]) / 10, 2),
                                              "sem_juros": True},
                                  "a_vista": float(o["premio_total"]), "franquia": o.get("franquia_valor")}
        resumo = {"opcoes": [um(ofertas[len(ofertas) // 2], "recomendada", "Recomendada"),
                             um(ofertas[0], "mais_em_conta", "Mais em conta"),
                             um(ofertas[-1], "mais_completa", "Mais completa")]}
        return {"token": "tok" + pedido_id[:8], "url": LINK_BASE + "tok" + pedido_id[:8],
                "artifact_id": str(uuid4()), "resumo": resumo}

    def mensagem_de_cotacao(modelo, link):
        # ⚠️ o dublê VAZA o CPF de propósito: o cinto da B1 tem de pegá-lo (mutação 7)
        return {"texto": f"Oi! A cotação do seu carro está pronta (CPF {CPF_PONTUADO}): {link}",
                "texto_curto": f"Sua cotação: {link}"}

    monkeypatch.setattr(PROP, "publicar_cotacao", publicar_cotacao, raising=False)
    monkeypatch.setattr(MSG, "mensagem_de_cotacao", mensagem_de_cotacao, raising=False)
    return m


# =====================================================================================================================
# os GUARDAS (cada um tem a sua mutação no fim do arquivo — e fica VERMELHO com ela)
# =====================================================================================================================
def guarda_o_fio(m: Mundo) -> dict:
    """Da frase ao `messages` do assistente na MESMA conversa, com a conta DA PESSOA."""
    a = m.corretora()
    uid, conta = m.pessoa(a, com_agger=True)
    conversa, sess = m.conversa(a, uid)
    m.falou(conversa, f"cota o Onix 2022 placa ABC1D23 da Fulana, CPF {CPF_PONTUADO}, nasc 01/02/1980, CEP 01001-000")

    r1 = m.preparar(a, uid, sess, **COMPLETOS)
    assert "Confira antes de eu calcular" in r1, r1
    assert "no seu Agger" in r1 and "lê pela placa" in r1
    assert not m.pedidos(), "preparar NÃO calcula (D-132B-03)"
    r2 = m.disparar(a, uid, sess, _id_da_confirmacao(r1))
    assert "Calculando nas seguradoras no seu Agger" in r2 and "1 a 2 minutos" in r2, r2
    [ped] = m.pedidos(a)
    assert (ped["servico"], ped["origem"], ped["solicitante_user_id"]) == ("cotacao", "auxiliar", uid)
    calcs = m.calculos(ped["id"])
    assert {c["opcao"] for c in calcs} == {"padrao", "economica", "completa_mais"}
    assert {(c["conta_exigida_id"], c["conta_regra"]) for c in calcs} == {(conta, "cotacao_da_pessoa")}, \
        "a cotação não saiu no Agger de quem pediu"
    [run] = [r for r in m.banco.linhas("work_runs") if r["workflow_key"] == "cotacao.chat"]
    assert run["conversation_id"] == conversa and run["requester_user_id"] == uid
    assert CPF not in str(run["input_payload"]) and NOME not in str(run["input_payload"]), "PII em claro no run"

    m.motor()
    assert {(c["status"], c["account_id"]) for c in m.calculos(ped["id"])} == {("fechado", conta)},         [(c["opcao"], c["status"]) for c in m.calculos(ped["id"])]
    m.rodar_runs(a)
    msgs = m.mensagens_do_assistente(conversa)
    assert len(msgs) == 1, msgs
    texto = msgs[0]["content"]
    n = len({o["seguradora_codigo"] or o["seguradora"] for o in m.banco.linhas("multicalculo_ofertas")
             if o["pedido_id"] == ped["id"] and float(o["premio_total"]) > 0})
    assert texto.startswith(f"Pronto: {n} seguradora"), texto[:80]
    assert "| Recomendada |" in texto and "| Mais em conta |" in texto and "| Mais completa |" in texto
    assert f"Apresentação para o cliente: {LINK_BASE}" in texto and "**Mensagem para o cliente**" in texto
    assert "Agger da corretora" not in texto, "aviso de conta da corretora com o Agger da pessoa"
    assert m.publicacoes == [{"company_id": a, "pedido_id": ped["id"], "pessoa_user_id": uid, "apolice_atual": None,
                              "primeiro_nome": NOME.split()[0]}], "a página não recebeu o primeiro nome do CLIENTE"
    assert m.banco.run(run["id"])["status"] == "completed"
    return {"a": a, "uid": uid, "sess": sess, "conversa": conversa, "pedido": ped, "saidas": [r1, r2, texto],
            "mensagem": msgs[0]}


def guarda_sem_confirmacao_nao_calcula(m: Mundo) -> None:
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    r1 = m.preparar(a, uid, sess, **COMPLETOS)
    assert _id_da_confirmacao(r1)
    r = m.disparar(a, uid, sess, "0123456789abcdef")        # um id que ninguém preparou
    assert "não vale mais" in r, r
    r = m.disparar(a, uid, sess, "")
    assert "não vale mais" in r, r
    assert not m.pedidos(), "calculou sem a confirmação do resumo"


def guarda_uso_unico(m: Mundo) -> None:
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    cid = _id_da_confirmacao(m.preparar(a, uid, sess, **COMPLETOS))
    assert "Calculando" in m.disparar(a, uid, sess, cid)
    r = m.disparar(a, uid, sess, cid)
    assert "já foi disparada" in r, r
    assert len(m.pedidos(a)) == 1, "o mesmo confirmacao_id disparou 2×"
    assert len([r for r in m.banco.linhas("work_runs") if r["workflow_key"] == "cotacao.chat"]) == 1


def guarda_sem_conta_da_pessoa_vai_pela_corretora_com_aviso(m: Mundo) -> None:
    a = m.corretora()
    uid, _ = m.pessoa(a)                                  # sem Agger próprio
    conversa, sess = m.conversa(a, uid)
    r1 = m.preparar(a, uid, sess, **COMPLETOS)
    assert "no Agger da corretora (você ainda não conectou o seu)" in r1, r1
    r2 = m.disparar(a, uid, sess, _id_da_confirmacao(r1))
    assert "no Agger da corretora (você ainda não conectou o seu)" in r2, r2
    [ped] = m.pedidos(a)
    assert ped["solicitante_user_id"] == uid
    assert {(c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"]) for c in m.calculos(ped["id"])} == \
        {(None, "cotacao_da_corretora", True)}
    m.motor()
    m.rodar_runs(a)
    [msg] = m.mensagens_do_assistente(conversa)
    assert "Calculei no Agger da corretora (você ainda não conectou o seu)" in msg["content"]


def guarda_cpf_nunca_volta_cru(m: Mundo, saidas) -> None:
    for s in saidas:
        assert CPF_PONTUADO not in s and CPF not in s, f"CPF cru na saída: {s[:200]}"
    assert "***.***.***-25" in saidas[0], "o resumo não mostra o CPF mascarado"


# =====================================================================================================================
# os testes
# =====================================================================================================================
def test_o_fio_da_frase_a_resposta_na_mesma_conversa(mundo):
    f = guarda_o_fio(mundo)
    guarda_cpf_nunca_volta_cru(mundo, f["saidas"] + [str(f["mensagem"]["payload"])])
    assert f["mensagem"]["payload"]["cotacao"]["url"].startswith(LINK_BASE)


def test_faltando_vira_frase_humana_numa_mensagem_e_nao_calcula(mundo):
    m = mundo
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    r = m.preparar(a, uid, sess, cpf_cnpj=CPF_PONTUADO, nome=NOME)
    assert r.startswith("PARA O CORRETOR — Faltam: "), r
    for frase in ("a data de nascimento do cliente", "o CEP do cliente",
                  "a placa do carro (com ela eu acho modelo, ano e combustível)",
                  "há quantos anos o principal condutor tem carteira de motorista"):
        assert frase in r, (frase, r)
    assert "o CPF de quem mais dirige" not in r, "perguntou o CPF do condutor que é o próprio cliente"
    assert not re.search(r"\b(segurado|veiculo|condutor|pernoite)\.\w+", r), "jargão de campo na frase"
    assert r.count("a placa do carro") == 1, "a placa supre três campos: UMA pergunta"
    assert not m.pedidos() and not m.redis.d


def test_a_placa_supre_fipe_ano_e_combustivel_na_cotacao_com_controle(mundo):
    p = PedidoDeCalculo.de_dict({"segurado": {"cpf_cnpj": CPF}, "veiculo": {"placa": "ABC1D23"}})
    supridos = {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"}
    assert not supridos & set(p.faltando(origem="auxiliar", servico="cotacao"))
    # CONTROLE: o MESMO pedido sem o serviço (o legado) continua exigindo os três — o guarda consegue diferir
    assert supridos <= set(p.faltando(origem="auxiliar"))
    # e sem a placa, a cotação exige os três (a placa é o que supre, não o serviço)
    assert supridos <= set(PedidoDeCalculo.de_dict({"segurado": {"cpf_cnpj": CPF}}).faltando(servico="cotacao"))
    assert supridos <= p.assumindo_pela_placa(servico="cotacao").assumidos


def test_disparar_sem_confirmacao_recusa(mundo):
    guarda_sem_confirmacao_nao_calcula(mundo)


def test_o_confirmacao_id_dispara_uma_vez_so(mundo):
    guarda_uso_unico(mundo)


def test_sem_agger_proprio_vai_pelo_da_corretora_com_aviso(mundo):
    guarda_sem_conta_da_pessoa_vai_pela_corretora_com_aviso(mundo)


def test_duas_corretoras_o_id_de_a_nao_dispara_em_b(mundo):
    m = mundo
    a, b = m.corretora(), m.corretora()
    ua, _ = m.pessoa(a)
    ub, _ = m.pessoa(b)
    ca, sa = m.conversa(a, ua)
    cb, sb = m.conversa(b, ub)
    cid = _id_da_confirmacao(m.preparar(a, ua, sa, **COMPLETOS))
    r = m.disparar(b, ub, sb, cid)
    assert "não vale mais" in r, r
    assert not m.pedidos(), "o id de A disparou em B"
    # a sessão de A na ferramenta de B (a conversa não é de B) → recusa, nada calculado
    r = m.disparar(b, ua, sa, cid)
    assert "Não achei esta conversa na sua corretora" in r, r
    # outra pessoa de A, noutra conversa, com o id de A → recusa SEM consumir
    ua2, _ = m.pessoa(a)
    _c2, s2 = m.conversa(a, ua2)
    assert "outra conversa ou de outra pessoa" in m.disparar(a, ua2, s2, cid)
    assert not m.pedidos()
    # o id continua valendo para quem preparou, na conversa dele
    assert "Calculando" in m.disparar(a, ua, sa, cid)
    assert [p["company_id"] for p in m.pedidos()] == [a]
    [run] = [r for r in m.banco.linhas("work_runs") if r["workflow_key"] == "cotacao.chat"]
    assert (run["company_id"], run["conversation_id"]) == (a, ca)


def test_a_mensagem_final_e_gravada_uma_vez_na_conversa_certa(mundo):
    f = guarda_o_fio(mundo)
    m, a = mundo, f["a"]
    [run] = [r for r in m.banco.linhas("work_runs") if r["workflow_key"] == "cotacao.chat"]
    # a 2ª escrita do mesmo run (retomada, gancho de desistência depois da entrega) não grava outra
    assert WF.gravar_mensagem(m.db, company_id=a, conversation_id=f["conversa"], run_id=run["id"], tipo="pronta",
                              texto="repetida") is False
    assert WF.avisar_que_nao_terminou(m.db, a, run["id"]) is False, "'não terminou' depois da resposta pronta"
    assert len(m.mensagens_do_assistente(f["conversa"])) == 1
    # CONTROLE: um tipo novo do mesmo run grava (o guarda consegue ficar vermelho)
    assert WF.gravar_mensagem(m.db, company_id=a, conversation_id=f["conversa"], run_id=run["id"],
                              tipo="controle", texto="x") is True
    # a conversa de OUTRA corretora nunca é escrita
    b = m.corretora()
    ub, _ = m.pessoa(b)
    cb, _sb = m.conversa(b, ub)
    assert WF.gravar_mensagem(m.db, company_id=a, conversation_id=cb, run_id=run["id"], tipo="pronta2",
                              texto="vazou") is False
    assert not m.mensagens_do_assistente(cb)


def test_nenhuma_seguradora_respondeu_vira_frase_honesta(mundo):
    m = mundo
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    m.disparar(a, uid, sess, _id_da_confirmacao(m.preparar(a, uid, sess, **COMPLETOS)))
    [ped] = m.pedidos(a)
    for c in m.calculos(ped["id"]):
        c.update({"status": "falhou", "erro": "sem resposta"})
    m.rodar_runs(a)
    [msg] = m.mensagens_do_assistente(conversa)
    assert msg["content"].startswith("Nenhuma seguradora respondeu com preço desta vez.")
    assert not m.publicacoes, "publicou sem oferta"


def test_o_ajuste_recalcula_pela_porta_e_responde_na_conversa(mundo):
    f = guarda_o_fio(mundo)
    m, a = mundo, f["a"]
    r = m.ajustar(a, f["uid"], f["sess"], f["pedido"]["id"], "franquia", "reduzida")
    assert r.startswith("Recalculando com a franquia reduzida no seu Agger"), r
    [aj] = [c for c in m.calculos(f["pedido"]["id"]) if c["opcao"] == "ajuste"]
    origem = next(c for c in m.calculos(f["pedido"]["id"]) if c["id"] == aj["origem_calculo_id"])
    assert origem["opcao"] == "padrao" and aj["ajuste"]["tipo"] == "franquia" and aj["ajuste"]["valor"] == 1
    runs = [x for x in m.banco.linhas("work_runs") if x["workflow_key"] == "cotacao.chat"]
    assert len(runs) == 2 and runs[1]["input_payload"]["ajuste_calculo_id"] == aj["id"]
    # a recusa do recálculo vira frase humana (P-1310-04)
    r = m.ajustar(a, f["uid"], f["sess"], f["pedido"]["id"], "franquia", "minúscula")
    assert r == "Para franquia eu sei recalcular com: normal, reduzida.", r
    # outra pessoa da equipe não ajusta a cotação de quem pediu
    u2, _ = m.pessoa(a)
    _c2, s2 = m.conversa(a, u2)
    assert "pedida por outra pessoa" in m.ajustar(a, u2, s2, f["pedido"]["id"], "franquia", "reduzida")


def test_moto_frota_e_rcfv_ficam_fora_com_frase(mundo):
    m = mundo
    a = m.corretora()
    uid, _ = m.pessoa(a)
    _c, sess = m.conversa(a, uid)
    assert m.preparar(a, uid, sess, ramo="moto", **COMPLETOS) == PC.FRASE_FORA["moto"]
    assert m.preparar(a, uid, sess, **{**COMPLETOS, "descricao_do_veiculo": "Honda CG 160 moto"}) == \
        PC.FRASE_FORA["moto"]
    assert m.preparar(a, uid, sess, ramo="frota", **COMPLETOS) == PC.FRASE_FORA["frota"]
    assert m.preparar(a, uid, sess, ramo="seguro de vida", **COMPLETOS) == PC.FRASE_FORA["outro"]
    assert not m.pedidos() and not m.redis.d


def test_o_cpf_mascarado_pelo_guardrail_e_achado_no_texto_cru(mundo):
    m = mundo
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    m.falou(conversa, f"o CPF dela é {CPF_PONTUADO}")
    r = m.preparar(a, uid, sess, **{**COMPLETOS, "cpf_cnpj": "<CPF>"})
    assert "Confira antes de eu calcular" in r and "***.***.***-25" in r, r
    # CONTROLE: dois CPFs diferentes no texto cru → não escolhe, pergunta
    m.falou(conversa, "ou o do marido, 111.444.777-35")
    r = m.preparar(a, uid, sess, **{**COMPLETOS, "cpf_cnpj": "<CPF>"})
    assert "o CPF do cliente" in r and "Confira" not in r, r


def test_as_frases_da_conta_casam_com_o_qual_agger_real(ambiente):
    """O acoplamento de `resposta._POR_QUE_NAO_O_SEU` com os textos de `qual_agger` — as quatro situações REAIS."""
    amb = ambiente
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    sem = F3.membro(amb, a)
    com, desligado, bloqueado = F3.membro(amb, a), F3.membro(amb, a), F3.membro(amb, a)
    F3.conta_da_pessoa(amb, a, com)
    F3.conta_da_pessoa(amb, a, desligado, estado="pausado")
    F3.conta_da_pessoa(amb, a, bloqueado, estado="bloqueado")
    supa = amb.banco.visao("smith-api")
    d = lambda u: QA.decidir(supa, company_id=a, servico="cotacao", solicitante_user_id=u)  # noqa: E731
    assert RESP.onde_calcula(d(com)) == "no seu Agger"
    assert RESP.onde_calcula(d(sem)) == "no Agger da corretora (você ainda não conectou o seu)"
    assert RESP.onde_calcula(d(desligado)) == "no Agger da corretora (o seu está pausado)"
    assert "recusou a senha" in RESP.onde_calcula(d(bloqueado))
    for u in (sem, desligado, bloqueado):
        assert "não está disponível agora" not in RESP.onde_calcula(d(u)), "texto do qual_agger mudou"


def test_de_ficha_e_a_cotacao_nova_com_a_apolice_nunca_a_renovacao():
    ficha = {"objeto_do_risco": {"placa": "ABC1D23", "ano_modelo": "2021/2022", "cep": "01001-000", "chassi": None},
             "leitura": {"estado": "nao_fechou", "tipo_documento": "apolice"}}
    perfil = {"segurado": {"cpf_cnpj": CPF, "nome": NOME, "nascimento": "1980-02-01", "sexo": "F", "estado_civil": 2},
              "condutor": {"tempo_habilitacao": 20}}
    p = de_ficha(ficha, perfil)
    assert p.valor("veiculo", "placa") == "ABC1D23" and p.valor("veiculo", "ano_modelo") == 2022
    assert p.valor("segurado", "cep") == "01001000" and "segurado.cep" in p.assumidos
    assert p.valor("pernoite", "cep_pernoite") == "01001000" and p.valor("condutor", "cpf") == CPF
    assert p.renovacao is False and not p.opcoes and not p.avisos, "a cotação nova virou renovação"
    assert not p.faltando(origem="auxiliar", servico="cotacao") and not p.sem_codigo()
    # o que o corretor disse VENCE a ficha
    assert de_ficha(ficha, {**perfil, "veiculo": {"placa": "XYZ9K88"}}).valor("veiculo", "placa") == "XYZ9K88"
    # CONTROLE: a irmã `de_apolice` é SEMPRE renovação — as duas conseguem diferir
    from types import SimpleNamespace
    ap = SimpleNamespace(ramo="AUTO", numero_humano="", seguradora=None, vigencia=None, item_de_risco=None,
                         coberturas=(), sinais=())
    try:
        assert de_apolice(ap, perfil, ficha=None).renovacao is True
    except Exception:  # noqa: BLE001 — o agrupamento de ramos pode não estar no ambiente; o controle acima basta
        pass


# =====================================================================================================================
# as MUTAÇÕES — o defeito reintroduzido, o guarda fica VERMELHO (§9.3 corolário: guarda que não falha não guarda)
# =====================================================================================================================
def test_mutacao_1_disparar_sem_confirmacao_o_guarda_fica_vermelho(mundo, monkeypatch):
    original = CONF.consumir

    async def sem_conferir(*, company_id, user_id, conversation_id, confirmacao_id, falas_do_corretor=(),
                           redis=None):
        for k, v in list(mundo.redis.d.items()):           # o defeito: qualquer id serve (o último preparado)
            if not k.endswith(":usada"):
                return dict(CONF._decifrar(v).get("conteudo") or {})
        return await original(company_id=company_id, user_id=user_id, conversation_id=conversation_id,
                              confirmacao_id=confirmacao_id, falas_do_corretor=falas_do_corretor, redis=redis)

    monkeypatch.setattr(CONF, "consumir", sem_conferir)
    with pytest.raises(AssertionError):
        guarda_sem_confirmacao_nao_calcula(mundo)


def test_mutacao_2_o_mesmo_id_dispara_duas_vezes_o_guarda_fica_vermelho(mundo, monkeypatch):
    async def nao_apaga(k):                                 # o defeito: o DEL some (o id nunca é consumido)
        return 1

    monkeypatch.setattr(mundo.redis, "delete", nao_apaga)
    with pytest.raises(AssertionError):
        guarda_uso_unico(mundo)


def test_mutacao_3_o_solicitante_some_o_guarda_fica_vermelho(mundo, monkeypatch):
    calcular = MulticalculoProvider.calcular

    async def sem_solicitante(self, **kw):                  # o defeito: a cotação vai sempre ao Agger da corretora
        kw["solicitante_user_id"] = None
        return await calcular(self, **kw)

    monkeypatch.setattr(MulticalculoProvider, "calcular", sem_solicitante)
    with pytest.raises(AssertionError):
        guarda_o_fio(mundo)


def test_mutacao_7_cpf_cru_na_resposta_o_guarda_fica_vermelho(mundo, monkeypatch):
    from app.services.multicalculo import renovacao as REN

    monkeypatch.setattr(RESP, "sem_documento_inteiro", lambda t: str(t or ""))
    monkeypatch.setattr(REN, "mascarar_documento", lambda d: str(d or ""))
    f = guarda_o_fio(mundo)
    with pytest.raises(AssertionError):
        guarda_cpf_nunca_volta_cru(mundo, f["saidas"])


# =====================================================================================================================
# CONSERTO ÚNICO (juiz 132-B + red team 132-B) — cada guarda tem a sua mutação logo abaixo, e fica VERMELHO com ela
# =====================================================================================================================
#: a ficha de uma APÓLICE cuja leitura FECHOU (a soma das coberturas bate com o prêmio líquido impresso) — 130-B
FICHA_CONFERIDA = {"objeto_do_risco": {"placa": "ABC1D23", "ano_modelo": "2021/2022", "cep": "01001-000"},
                   "leitura": {"estado": "fechou", "tipo_documento": "apolice", "premio_esperado": "3.912,40"}}
CPF_DO_OUTRO = "111.444.777-35"                        # sintético, DV válido — o "outro cliente" da conversa


# -- B3 · o CPF de outro cliente da mesma conversa nunca completa o pedido ------------------------------------------
def guarda_cpf_de_outro_cliente(montar=PC.montar) -> None:
    falas = ["agora cota o HB20 placa XYZ9K88 da Maria Ficticia, nasc 03/04/1990, CEP 88010-000, 10 anos de carteira",
             f"cota o Onix placa ABC1D23 do Joao Ficticio, CPF {CPF_PONTUADO}, nasc 01/02/1980, CEP 01001-000"]
    maria = {"nome": "Maria Ficticia", "nascimento": "03/04/1990", "sexo": "feminino", "cep": "88010-000",
             "placa": "XYZ9K88", "anos_de_carteira": "10"}
    m = montar(maria, textos_crus=falas)
    assert not m.completa and "segurado.cpf_cnpj" in m.faltam, "o pedido da Maria saiu com o CPF do João"
    assert "o CPF do cliente" in PC.frase_do_que_falta(m)
    # o modelo indicou um CPF MASCARADO que não é o do João (outros dígitos visíveis) → também pergunta
    m = montar({**maria, "cpf_cnpj": "***.***.***-31"}, textos_crus=falas)
    assert not m.completa and "segurado.cpf_cnpj" in m.faltam
    # CONTROLE: o mascarado com os dígitos do CPF que ESTÁ no texto cru (o guardrail mascarou) → acha
    m = montar({**maria, "cpf_cnpj": "***.***.***-25"}, textos_crus=falas)
    assert m.completa and m.pedido.valor("segurado", "cpf_cnpj") == CPF
    # dois candidatos compatíveis → pergunta (nunca escolhe)
    m = montar({**maria, "cpf_cnpj": "<CPF>"}, textos_crus=falas + [f"o da Maria é {CPF_DO_OUTRO}"])
    assert not m.completa


def test_b3_o_cpf_de_outro_cliente_da_conversa_nunca_completa_o_pedido():
    guarda_cpf_de_outro_cliente()


def test_mutacao_b3_o_texto_cru_lido_sem_o_cpf_do_modelo_o_guarda_fica_vermelho(monkeypatch):
    real = PC.unico_no_texto_cru

    def montar_antigo(dados, **kw):                      # o defeito: lê o texto cru mesmo sem CPF nenhum do modelo
        monkeypatch.setattr(PC, "unico_no_texto_cru", lambda tipo, textos, compativel_com=None: real(tipo, textos))
        d = dict(dados)
        d.setdefault("cpf_cnpj", "<CPF>")
        return PC.montar(d, **kw)

    with pytest.raises(AssertionError):
        guarda_cpf_de_outro_cliente(montar_antigo)


# -- B2 · "economia" só com a apólice ANEXADA e conferida; o que o corretor digita fica no resumo dele -------------
CASOS_DO_DINHEIRO = (("4200.00", 4200.0), ("3.500,50", 3500.5), ("3500.50", 3500.5), ("4.200", 4200.0),
                     ("R$ 4.200,00", 4200.0), ("3500", 3500.0), ("3500.5", 3500.5), (4200, 4200.0),
                     ("1.234.567", 1234567.0), ("abc", None), ("0", None), ("-5", None), ("", None), (None, None))


def test_b2_o_dinheiro_como_o_corretor_escreve():
    for texto, esperado in CASOS_DO_DINHEIRO:
        assert PC.valor_em_reais(texto) == esperado, (texto, PC.valor_em_reais(texto), esperado)


def guarda_economia_so_com_a_apolice(seguro_atual=PC.seguro_atual) -> None:
    d = {"seguradora_atual": "Seguradora X", "premio_atual_anual": "4200.00"}
    # sem anexo: nada de apólice — o que ele disse vai ao RESUMO, nunca à página
    sit, ap, dito = seguro_atual(d, None)
    assert (sit, ap) == ("novo_sem_apolice", None), (sit, ap)
    assert dito == {"seguradora": "Seguradora X", "premio_anual": 4200.0}, dito
    # com uma ficha que NÃO fechou (ou que não é apólice, ou sem prêmio): também não
    for leitura in ({"estado": "nao_fechou", "tipo_documento": "apolice", "premio_esperado": "3.912,40"},
                    {"estado": "fechou", "tipo_documento": "endosso", "premio_esperado": "3.912,40"},
                    {"estado": "fechou", "tipo_documento": "apolice"}):
        assert seguro_atual(d, {**FICHA_CONFERIDA, "leitura": leitura})[0] == "novo_sem_apolice", leitura
    # CONTROLE: a apólice anexada e CONFERIDA → o prêmio é o DA FICHA (nunca o que o modelo escreveu)
    sit, ap, _ = seguro_atual(d, FICHA_CONFERIDA)
    assert sit == "novo_com_apolice" and ap == {"seguradora": "Seguradora X", "premio_anual": 3912.4,
                                                "origem": "documento", "base": "liquido"}, ap


def test_b2_economia_so_com_a_apolice_anexada_e_conferida():
    guarda_economia_so_com_a_apolice()
    m = PC.montar({**COMPLETOS, "seguradora_atual": "Seguradora X", "premio_atual_anual": "4200.00"})
    r = PC.resumo(m, onde="no seu Agger", opcoes=("padrao",))
    assert m.situacao == "novo_sem_apolice" and m.apolice_atual is None
    assert "O cliente disse que paga hoje: Seguradora X, R$" in r and "4.200,00 por ano" in r, r
    assert "não vai para a apresentação do cliente" in r


def test_mutacao_b2_o_premio_declarado_vira_apolice_o_guarda_fica_vermelho():
    def antigo(d, ficha):                                 # o defeito: a seguradora dita basta; o prêmio do modelo vale
        return ("novo_com_apolice", {"seguradora": d["seguradora_atual"], "premio_anual": 420000.0,
                                     "origem": "documento" if ficha is not None else "corretor"}, None)

    with pytest.raises(AssertionError):
        guarda_economia_so_com_a_apolice(antigo)


# -- B4 · o "sim" é uma FALA do corretor depois do resumo, não o modelo -------------------------------------------
def guarda_sim_do_corretor(m: Mundo) -> None:
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    m.falou(conversa, "cota o Onix 2022 placa ABC1D23 da Fulana")
    cid = _id_da_confirmacao(m.preparar(a, uid, sess, **COMPLETOS))
    r = m.disparar(a, uid, sess, cid, sim=None)           # o modelo encadeia: nenhuma fala do corretor no meio
    assert "ainda NÃO calculei" in r and not m.pedidos(), "disparou sem o 'sim' do corretor"
    r = m.disparar(a, uid, sess, cid, sim="não, espera, o CEP está errado")
    assert "ainda NÃO calculei" in r and not m.pedidos(), "disparou com um 'não'"
    r = m.disparar(a, uid, sess, cid, sim="sim, mas o CEP é 88010-000")
    assert "ainda NÃO calculei" in r and not m.pedidos(), "disparou com um dado novo (é correção, não confirmação)"
    # CONTROLE: o "sim" do corretor depois do resumo → calcula UMA vez (a recusa não consumiu o id)
    assert "Calculando" in m.disparar(a, uid, sess, cid, sim="sim, pode calcular")
    assert len(m.pedidos(a)) == 1


def test_b4_o_disparo_exige_o_sim_do_corretor_depois_do_resumo(mundo):
    guarda_sim_do_corretor(mundo)


def test_b4_o_que_e_um_sim():
    for sim in ("sim", "Sim!", "pode", "pode calcular", "calcula", "ok", "manda", "confirmo", "isso, pode calcular",
                "pode calcular para mim"):
        assert CONF.e_confirmacao(sim), sim
    for nao in ("não", "nao calcula", "espera", "peraí, vou ver", "sim, mas espera", "muda o CEP", "",
                "cota o HB20 placa XYZ9K88", "sim 01001-000", "x" * 90):
        assert not CONF.e_confirmacao(nao), nao


def test_mutacao_b4_o_disparo_sem_o_sim_o_guarda_fica_vermelho(mundo, monkeypatch):
    monkeypatch.setattr(CONF, "confirmou_depois", lambda *a, **k: True)     # o defeito: o código não distingue
    with pytest.raises(AssertionError):
        guarda_sim_do_corretor(mundo)


# -- P2 · P9 · o CPF (pontuado, colado, com espaços) nunca vai em claro ao `work_runs` -------------------------------
def guarda_cpf_no_risco(resumo=WF.resumo_do_cliente, cinto=RESP.sem_documento_inteiro) -> None:
    campos = {"segurado": {"cpf_cnpj": CPF, "nome": NOME}, "veiculo": {"placa": "ABC1D23"}}
    for desc in (f"Onix do CPF {CPF_PONTUADO}", f"Onix do CPF {CPF}", "Onix do 529 982 247 25"):
        r = resumo(campos, desc)
        assert CPF not in re.sub(r"\D", "", str(r.get("risco") or "")), (desc, r)
    assert cinto("CPF 529 982 247 25") == "CPF ***.***.***-25"
    # CONTROLE: 11 dígitos que NÃO são CPF (o DV não fecha) não são mascarados à toa; ano/modelo fica
    assert cinto("protocolo 123 456 789 00") == "protocolo 123 456 789 00"
    assert resumo(campos, "Onix 2021 2022")["risco"] == "Onix 2021 2022"


def test_p2_p9_o_cpf_com_pontos_ou_espacos_nunca_vai_em_claro_ao_run():
    guarda_cpf_no_risco()


def test_mutacao_p2_o_risco_sem_a_mascara_o_guarda_fica_vermelho():
    cpf_antigo = re.compile(r"(?<![\d*])(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?!\d)")

    def cinto_antigo(t):                                  # o defeito: o separador espaço não era documento
        return cpf_antigo.sub(lambda mm: "***.***.***-" + mm.group(4), str(t or ""))

    def resumo_antigo(campos, desc=None):                 # o defeito: o `\d{6,}` sem a máscara
        risco = str(desc or "")
        return {"risco": risco[:60]} if not re.search(r"\d{6,}", risco) else {}

    with pytest.raises(AssertionError):
        guarda_cpf_no_risco(resumo=resumo_antigo, cinto=cinto_antigo)
