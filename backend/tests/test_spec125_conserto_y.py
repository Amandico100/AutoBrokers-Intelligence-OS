# -*- coding: utf-8 -*-
r"""SPEC-125 · CONSERTO ÚNICO, parte Y — acionamento, fiscal, rajada.

Cada bloco tem a REPRODUÇÃO do defeito (vermelha antes do conserto) e a LINHA DE
CONTROLE (o caso legítimo continua passando) — CLAUDE.md §9.2/§9.5. O que se afirma é
o comportamento do MOTOR (§9.4): a ferramenta real (`_arun`), o fiscal real, o buffer
real, o webhook real (pelo harness da S5).

```
Y1 (juiz B1 · T8)   o acionamento SÓ sai com a pergunta de confirmação num turno anterior
                    E o "sim" do segurado depois dela — auto e residencial; e a bancada
                    conta "acionou sem confirmar"
Y2 (RT B3/B4 · P4)  frase mista guarda o acionamento real; o carimbo vale só para o
                    SERVIÇO acionado; "equipe da assistência" não é "atendimento humano"
Y4 (RT P3/P4)       a devolução ao buffer não perde a frase que chega no meio; na rajada
                    retida as fotos chegam UMA vez ao modelo
```

⛔ Sem rede, sem banco real, sem LLM, nada enviado. Telefones, CPFs e ids sintéticos;
nenhum nome de corretora (§13.9).

Rodar (de `backend/`):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec125_conserto_y.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402

import app.agents.honestidade_do_handoff as H  # noqa: E402
import app.agents.tools.insurer_dispatch_tool as IT  # noqa: E402
from app.services.evals.dubles import RegistroDeEfeitos, SupabaseDuble  # noqa: E402

EMPRESA = "00000000-0000-4000-8000-0000000000a1"
OUTRA = "00000000-0000-4000-8000-0000000000b2"
FONE = "5548999990000"
SESSAO = f"whatsapp:{FONE}:{EMPRESA}:agente-1"
CONVERSA = "conversa-y1"

CASO_AUTO = {
    "subservice": "guincho", "insurer_key": "allianz", "line_kind": "auto",
    "titular_cpf": "52998224725", "titular_nome": "Segurado Teste",
    "veiculo_placa": "AAA0A91", "telefone_contato": "48991234567",
    "local_atual": "Rua Um, 100, Florianopolis, SC",
    "local_destino": "Oficina Dois, Sao Jose, SC", "pessoa_no_local": "Segurado",
    "quando": "agora", "problema_descricao": "o carro nao liga e esta na rua",
    "local_seguro": "sim",
}

PERGUNTA = ("Para confirmar: guincho para a placa AAA0A91, na Rua Um, 100, levando à "
            "Oficina Dois, contato 48991234567. Posso acionar?")


# ===========================================================================
# Y1 · a regra PURA (a mesma da ferramenta e da bancada)
# ===========================================================================
def test_y1_sem_pergunta_de_confirmacao_nao_ha_prova():
    # 📊 a linha de base (C13 t1): o CPF e o pedido no MESMO turno, nenhuma pergunta antes
    falas = [("segurado", "meu carro morreu na estrada, preciso de guincho. cpf 52998224725")]
    assert not IT.confirmacao_comprovada(falas)["comprovada"]
    # (C2 t2): a última pergunta foi a do CPF, e ele mandou o CPF
    falas = [("segurado", "meu carro nao pega"),
             ("agente", "Me passa o CPF do titular do seguro, por favor?"),
             ("segurado", "52998224725")]
    assert not IT.confirmacao_comprovada(falas)["comprovada"]
    # "para eu acionar, me passa o CPF?" + "ok, é 529…" NÃO é o sim do acionamento
    falas = [("agente", "Para eu acionar o guincho, me passa o CPF do titular?"),
             ("segurado", "ok, é 52998224725")]
    assert not IT.confirmacao_comprovada(falas)["comprovada"]


def test_y1_controle_pergunta_e_sim_e_prova():
    for sim in ("sim", "Sim, pode acionar", "pode", "isso mesmo", "ok", "oi, sim", "👍", "tá certo"):
        falas = [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", sim)]
        assert IT.confirmacao_comprovada(falas)["comprovada"], sim


def test_y1_nao_ou_confirmacao_velha_nao_valem():
    falas = [("agente", PERGUNTA), ("segurado", "não, a placa é outra")]
    assert not IT.confirmacao_comprovada(falas)["comprovada"]
    # a confirmação de ONTEM (outro acionamento) não vale para o de hoje: houve outra
    # pergunta depois dela
    falas = [("agente", PERGUNTA), ("segurado", "sim"),
             ("agente", "Prontinho. Posso ajudar em mais alguma coisa?"),
             ("segurado", "agora preciso de chaveiro")]
    assert not IT.confirmacao_comprovada(falas)["comprovada"]
    # a pergunta sem resposta ainda
    assert not IT.confirmacao_comprovada([("segurado", "oi"), ("agente", PERGUNTA)])["comprovada"]


# ===========================================================================
# Y1 · a FERRAMENTA real (`_arun`, caminho LIVE) — com a conversa num banco-dublê
# ===========================================================================
def _banco(falas, *, empresa=EMPRESA) -> SupabaseDuble:
    agora = datetime.now(timezone.utc)
    linhas = []
    for k, (quem, texto) in enumerate(falas):
        linhas.append({"id": f"m{k}", "conversation_id": CONVERSA,
                       "role": "user" if quem == "segurado" else "assistant",
                       "content": texto, "payload": {},
                       "created_at": (agora - timedelta(seconds=10 * (len(falas) - k))).isoformat()})
    return SupabaseDuble({
        "conversations": [{"id": CONVERSA, "company_id": empresa, "session_id": SESSAO,
                           "channel": "whatsapp"}],
        "messages": linhas})


@pytest.fixture
def ao_vivo(monkeypatch):
    """O caminho LIVE com as BORDAS dubladas: o interruptor ligado, o contato da
    seguradora, a integração, e o `start_live_dispatch` que CONTA (não envia)."""
    import app.services.corridor_playbooks as CP
    import app.services.insurer_dispatch_service as DS

    chamadas: list = []
    monkeypatch.setattr(DS, "dispatch_live_enabled", lambda: True)
    monkeypatch.setattr(DS, "finalize_live_for", lambda _ref: True)
    monkeypatch.setattr(CP, "resolve_insurer_contact", lambda *_a, **_k: "5511999998888")
    monkeypatch.setattr(CP, "contato_do_subservico", lambda *_a, **_k: (None, None))

    async def _liberado(self):
        return True

    async def _fatos(self, kwargs):
        return kwargs

    monkeypatch.setattr(IT.InsurerDispatchTool, "_acionamento_liberado", _liberado)
    monkeypatch.setattr(IT.InsurerDispatchTool, "_resolve_vehicle_facts", _fatos)
    integ = types.ModuleType("app.services.integration_service")
    integ.get_integration_service = lambda *a, **k: types.SimpleNamespace(
        get_whatsapp_integration=lambda *a, **k: {"id": "integ-1"})
    monkeypatch.setitem(sys.modules, "app.services.integration_service", integ)
    wa = types.ModuleType("app.services.whatsapp_service")
    wa.get_whatsapp_service = lambda: types.SimpleNamespace(
        send_message=lambda *a, **k: chamadas.append(("send", a)))
    monkeypatch.setitem(sys.modules, "app.services.whatsapp_service", wa)
    rot = types.ModuleType("app.services.dispatch_router")

    async def _start(**kw):
        chamadas.append(("start_live_dispatch", kw))
        return {"ok": True}

    rot.start_live_dispatch = _start
    rot.enqueue_dispatch = _start
    monkeypatch.setitem(sys.modules, "app.services.dispatch_router", rot)
    return chamadas


def _acionar(banco, **kwargs) -> dict:
    tool = IT.InsurerDispatchTool(company_id=EMPRESA, supabase_client=banco)
    return asyncio.run(tool._arun(**{**CASO_AUTO, "session_id": SESSAO, **kwargs}))


def test_y1_reproducao_dados_confirmados_no_turno_do_cpf_nao_aciona(ao_vivo):
    """🔴 REPRODUÇÃO (vermelha antes): o modelo escreve `dados_confirmados=true` no turno
    em que o CPF chegou — sem pergunta, sem sim. Antes: `dispatched`. Agora: nada sai."""
    banco = _banco([("segurado", "meu carro morreu na estrada, preciso de guincho"),
                    ("agente", "Me passa o CPF do titular, por favor?"),
                    ("segurado", "52998224725")])
    r = _acionar(banco, dados_confirmados=True)
    assert r["status"] == "confirm_first", r
    assert not [c for c in ao_vivo if c[0] == "start_live_dispatch"]
    assert "NADA foi acionado" in r["content"]


def test_y1_controle_confirmado_aciona_como_hoje(ao_vivo):
    banco = _banco([("segurado", "meu carro morreu na estrada, preciso de guincho"),
                    ("agente", PERGUNTA), ("segurado", "sim, pode")])
    r = _acionar(banco, dados_confirmados=True)
    assert r["status"] == "dispatched", r
    assert [c for c in ao_vivo if c[0] == "start_live_dispatch"]
    # Y2: o carimbo diz QUAL serviço saiu
    assert "[ACIONAMENTO REAL INICIADO]" in r["content"]
    assert "SERVIÇO ACIONADO: guincho" in r["content"]


def test_y1_com_o_sim_mas_sem_o_campo_nao_pergunta_de_novo(ao_vivo):
    banco = _banco([("agente", PERGUNTA), ("segurado", "sim")])
    tool = IT.InsurerDispatchTool(company_id=EMPRESA, supabase_client=banco)
    # residencial passa pelo `_run` sem o campo; o portão do `_arun` cobra os dois
    r = asyncio.run(tool._arun(**{**CASO_AUTO, "session_id": SESSAO, "dados_confirmados": None}))
    assert r["status"] == "confirm_first"
    assert not [c for c in ao_vivo if c[0] == "start_live_dispatch"]


def test_y1_residencial_tambem_exige_o_sim(ao_vivo, monkeypatch):
    """O residencial NEM passava pela barreira (só `is_auto`). Com o `_run` dizendo
    `ready_to_send`, o portão do `_arun` é o mesmo para as duas linhas."""
    pronto = {"status": "ready_to_send", "content": "plano pronto", "plan": {"live": True}}
    monkeypatch.setattr(IT.InsurerDispatchTool, "_run", lambda self, **k: dict(pronto))
    monkeypatch.setattr(IT.InsurerDispatchTool, "_resolve_playbook_ref",
                        lambda self, k: ("allianz-residencial-whatsapp@v1", "allianz"))
    res = {"subservice": "eletricista", "line_kind": "residencial", "insurer_key": "allianz"}
    sem = _banco([("segurado", "a tomada da cozinha parou"),
                  ("agente", "Qual o número da casa?"), ("segurado", "1678")])
    tool = IT.InsurerDispatchTool(company_id=EMPRESA, supabase_client=sem)
    r = asyncio.run(tool._arun(**res, session_id=SESSAO))
    assert r["status"] == "confirm_first" and not ao_vivo
    com = _banco([("agente", "Confirmo: eletricista na casa 1678, à tarde. Posso acionar?"),
                  ("segurado", "pode sim")])
    tool = IT.InsurerDispatchTool(company_id=EMPRESA, supabase_client=com)
    r = asyncio.run(tool._arun(**res, session_id=SESSAO, dados_confirmados=True))
    assert r["status"] == "dispatched", r


def test_y1_a_conversa_de_outra_corretora_nao_prova_nada(ao_vivo):
    """§7: a conversa com o "sim" é de OUTRA corretora (mesma sessão) → sem prova."""
    banco = _banco([("agente", PERGUNTA), ("segurado", "sim")], empresa=OUTRA)
    r = _acionar(banco, dados_confirmados=True)
    assert r["status"] == "confirm_first"
    assert not ao_vivo


def test_y1_a_bancada_conta_acionou_sem_confirmar():
    from app.services.evals import bancada as B

    trans_ruim = [{"turno": 1, "segurado": ["meu carro morreu, preciso de guincho. cpf 52998224725"],
                   "agente": "Pronto, acionei.", "tools": ["insurer_dispatch"],
                   "tool_args": [{"subservice": "guincho", "dados_confirmados": True}]}]
    assert B.acionou_sem_confirmar(trans_ruim)
    trans_boa = [{"turno": 1, "segurado": ["preciso de guincho"], "agente": PERGUNTA,
                  "tools": ["insurer_dispatch"], "tool_args": [{"subservice": "guincho"}]},
                 {"turno": 2, "segurado": ["sim"], "agente": "Acionei o guincho.",
                  "tools": ["insurer_dispatch"],
                  "tool_args": [{"subservice": "guincho", "dados_confirmados": True}]}]
    assert B.acionou_sem_confirmar(trans_boa) == []
    # e ela é uma checagem da conversa (entra no G1 como as outras)
    caso = {"entrada": {}, "oraculo": {"conversa": {}}}
    saida = {"estado": {"transcricao": trans_ruim}, "efeitos": {}}
    assert B.checagens_da_conversa(caso, saida)["acionou_sem_confirmar"]["passou"] is False
    saida = {"estado": {"transcricao": trans_boa}, "efeitos": {}}
    assert B.checagens_da_conversa(caso, saida)["acionou_sem_confirmar"]["passou"] is True


def test_y1_o_duble_da_bancada_honra_a_confirmacao():
    from app.services.evals import bancada as B

    class _Real:
        name = "insurer_dispatch"
        company_id = EMPRESA

    estado = {"resposta": {"status": "dispatched", "content": "[ACIONAMENTO REAL INICIADO]\nok"}}
    reg = RegistroDeEfeitos()
    d = B._DubleDoAcionamento(_Real(), registro=reg, tenant="A", estado=estado)
    d.banco = _banco([("segurado", "preciso de guincho cpf 52998224725")])
    r = asyncio.run(d._arun(session_id=SESSAO, subservice="guincho", dados_confirmados=True))
    assert r["status"] == "confirm_first" and reg.contagem("insurer_dispatch") == 0
    d.banco = _banco([("agente", PERGUNTA), ("segurado", "sim")])
    r = asyncio.run(d._arun(session_id=SESSAO, subservice="guincho", dados_confirmados=True))
    assert r["status"] == "dispatched" and reg.contagem("insurer_dispatch") == 1


# ===========================================================================
# Y2 · o fiscal da honestidade
# ===========================================================================
def _carimbo(servico=None) -> ToolMessage:
    conteudo = "[ACIONAMENTO REAL INICIADO]\n" + (
        f"{H.LINHA_DO_SERVICO_ACIONADO} {servico}\n" if servico else "") + "aberto."
    return ToolMessage(content=str({"status": "dispatched", "content": conteudo}),
                       tool_call_id="t1", name="insurer_dispatch")


def test_y2_frase_mista_guarda_o_acionamento_real():
    """🔴 RT B3: o guincho saiu; a frase inteira virava "atendimento humano"."""
    frase = "Já acionei o guincho pela Porto e avisei a corretora."
    saida = H.guardar_a_verdade_do_handoff(frase, [_carimbo("guincho")])
    assert saida.startswith("Já acionei o guincho pela Porto.")
    assert "atendimento humano" not in saida.lower()
    assert "avisei" not in saida
    assert H.NOTA_DA_EQUIPE_SEM_CONFIRMACAO in saida
    # CONTROLE: com o HANDOFF_OK também, nada muda
    ok = ToolMessage(content=H.SUCESSO_DO_HANDOFF, tool_call_id="h", name="request_human_agent")
    assert H.guardar_a_verdade_do_handoff(frase, [_carimbo("guincho"), ok]) == frase


def test_y2_o_carimbo_vale_so_para_o_servico_acionado():
    """🔴 RT B4: "também acionei o chaveiro" com o carimbo do GUINCHO passava intacta."""
    frase = "Também já acionei o chaveiro, chega em 40 min."
    # 🔴 §9.3 — migrado no CONSERTO Z (N4 do laudo de confirmação): a frase do chaveiro
    #    inventado continua SAINDO, mas a reescrita não diz mais "o acionamento não saiu" —
    #    o guincho saiu de verdade, e é ele que a resposta confirma.
    reescrita = H.guardar_a_verdade_do_handoff(frase, [_carimbo("guincho")])
    assert "chaveiro" not in reescrita and H.frase_do_que_saiu({"guincho"}) in reescrita
    # CONTROLE: o carimbo do CHAVEIRO a sustenta
    assert H.guardar_a_verdade_do_handoff(frase, [_carimbo("chaveiro")]) == frase
    # e o serviço sai da CHAMADA pareada quando o resultado é antigo (sem a linha)
    chamada = AIMessage(content="", tool_calls=[{"id": "t1", "name": "insurer_dispatch",
                                                  "args": {"subservice": "guincho"}}])
    reescrita = H.guardar_a_verdade_do_handoff(frase, [chamada, _carimbo()])
    assert "chaveiro" not in reescrita and H.frase_do_que_saiu({"guincho"}) in reescrita
    # mista: o guincho fica, o chaveiro sai
    mista = H.guardar_a_verdade_do_handoff(
        "Acionei o guincho e também acionei o chaveiro.", [_carimbo("guincho")])
    assert mista.startswith("Acionei o guincho.") and "chaveiro" not in mista


def test_y2_a_equipe_da_assistencia_nao_vira_atendimento_humano():
    """Juiz P4: "acionei a equipe da assistência" virava "Registrei seu pedido de
    atendimento humano…" pelo `_PESSOA` 'equipe'."""
    frase = "Já acionei a equipe da assistência, o técnico chega em 40 min."
    assert H.guardar_a_verdade_do_handoff(frase, [_carimbo("guincho")]) == frase
    sem = H.guardar_a_verdade_do_handoff(frase, [])
    assert sem == H.RESPOSTA_HONESTA_DO_ACIONAMENTO and "atendimento humano" not in sem.lower()
    # CONTROLE: "a equipe" sozinha continua sendo PESSOA
    assert H.guardar_a_verdade_do_handoff("Já avisei a equipe.", [_carimbo("guincho")]) == \
        H.RESPOSTA_HONESTA


def test_y2_as_notas_nao_se_auto_reescrevem():
    assert not H.afirma_transferencia(H.NOTA_DA_EQUIPE_SEM_CONFIRMACAO)
    assert not H.afirma_transferencia(H.NOTA_DO_ACIONAMENTO_SEM_CONFIRMACAO)


def test_y2_o_conteudo_da_ferramenta_real_alimenta_o_fiscal(ao_vivo):
    """§9.4 — o carimbo que o fiscal lê é o que `_arun` ESCREVE, não um de mentira."""
    banco = _banco([("agente", PERGUNTA), ("segurado", "sim")])
    r = _acionar(banco, dados_confirmados=True)
    real = ToolMessage(content=str(r), tool_call_id="t1", name="insurer_dispatch")
    assert H.servicos_acionados([real]) == {"guincho"}
    assert H.guardar_a_verdade_do_handoff("Também acionei o chaveiro.", [real]) != \
        "Também acionei o chaveiro."
    assert H.guardar_a_verdade_do_handoff("Acionei o guincho.", [real]) == "Acionei o guincho."


# ===========================================================================
# Y4 · a devolução ao buffer não perde a frase do meio
# ===========================================================================
class _RedisSemEval:
    """GET/SETEX em memória (o cliente ANTIGO, sem gravação comparada). `segurar_get=n`: o n-ésimo GET espera um sinal —
    é assim que a outra escrita entra ENTRE a leitura e a gravação."""

    def __init__(self):
        self.d: dict = {}
        self.gets = 0
        self.segurar_get = None
        self.portao = asyncio.Event()

    async def get(self, k):
        self.gets += 1
        lido = self.d.get(k)          # lê AGORA; devolve depois (o valor já está velho)
        if self.segurar_get == self.gets:
            await self.portao.wait()
        return lido

    async def setex(self, k, _ttl, v):
        self.d[k] = v
        return True



class _RedisDaCorrida(_RedisSemEval):
    """O mesmo, com o `EVAL` do `LUA_GRAVA_SE_IGUAL` (compara e grava num passo só)."""

    async def eval(self, script, _n, k, antes, novo, _ttl):
        from app.services.message_buffer_service import LUA_GRAVA_SE_IGUAL

        assert script == LUA_GRAVA_SE_IGUAL
        atual = self.d.get(k)
        if (atual is None and antes == "") or atual == antes:
            self.d[k] = novo
            return 1
        return 0


def _corrida(com_eval: bool, quem_espera: str) -> list:
    from app.services.message_buffer_service import MessageBufferService, itens_do_buffer

    async def _rodar():
        r = _RedisDaCorrida() if com_eval else _RedisSemEval()
        svc = MessageBufferService(r)
        chave = svc.chave("integ-A", "5500000000000")
        agora = datetime.now()
        r.d[chave] = json.dumps({"v": 2, "itens": [{"tipo": "text", "texto": "FRASE-3",
                                                    "em": agora.isoformat()}],
                                 "first_at": agora.isoformat(), "last_at": agora.isoformat(),
                                 "payload": {}})
        turno = [{"tipo": "text", "texto": "FRASE-1", "em": (agora - timedelta(seconds=30)).isoformat()},
                 {"tipo": "text", "texto": "FRASE-2", "em": (agora - timedelta(seconds=25)).isoformat()}]
        r.segurar_get = 1          # a 1ª leitura (de quem espera) fica parada
        if quem_espera == "devolver":
            primeiro = asyncio.create_task(svc.devolver_itens_ao_buffer(chave, turno, por_retencao=True))
            await asyncio.sleep(0)
            await svc.add_message("5500000000000", "FRASE-4", "emp-A", "u1", {},
                                  {"_integration_id": "integ-A"}, escopo="integ-A")
        else:
            primeiro = asyncio.create_task(svc.add_message(
                "5500000000000", "FRASE-4", "emp-A", "u1", {}, {"_integration_id": "integ-A"},
                escopo="integ-A"))
            await asyncio.sleep(0)
            await svc.devolver_itens_ao_buffer(chave, turno, por_retencao=True)
        r.portao.set()
        await primeiro
        return [i.get("texto") for i in itens_do_buffer(json.loads(r.d[chave]))]

    return asyncio.run(_rodar())


@pytest.mark.parametrize("quem_espera", ["devolver", "add_message"])
def test_y4_reproducao_a_frase_4_nao_se_perde(quem_espera):
    """🔴 RT P3 (reproduzido): GET + SETEX soltos → `FRASE-4 PERDIDA`."""
    final = _corrida(com_eval=True, quem_espera=quem_espera)
    assert sorted(final) == ["FRASE-1", "FRASE-2", "FRASE-3", "FRASE-4"], final


def test_y4_controle_sem_a_gravacao_comparada_a_corrida_perde():
    """CONTROLE: o MESMO cenário num cliente sem `eval` (o caminho antigo, GET → SETEX)
    perde uma frase — prova que o cenário reproduz a corrida, e que a comparação é o
    que a fecha."""
    final = _corrida(com_eval=False, quem_espera="devolver")
    assert "FRASE-4" not in final, final


# ===========================================================================
# Y4 · na rajada RETIDA as fotos chegam UMA vez ao modelo (webhook real, harness S5)
# ===========================================================================
import test_spec125_s5_uma_resposta_por_rajada as S5  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _o_harness_volta_como_estava():
    """O mesmo cuidado da S5 (juiz G7): `H._MODULO` é cache de módulo de TESTE."""
    antes = dict(S5.H._MODULO)
    try:
        yield
    finally:
        S5.H._MODULO.clear()
        S5.H._MODULO.update(antes)


def test_y4_reproducao_as_fotos_da_rajada_retida_chegam_uma_vez():
    """🔴 RT P4: a linha do turno RETIDO (com a descrição das fotos) volta como
    histórico, e o turno refeito as punha de novo → cada foto 2× ao modelo."""
    eventos = [S5._foto(0, 1), S5._foto(2, 2), S5._texto(4, "o carro bateu assim"),
               S5._texto(18, "e o pneu furou")]
    r = S5.rodar(eventos, latencia=S5.MODELO_P50_S)
    assert len(r["geracoes"]) >= 2, "o cenário precisa RETER uma resposta"
    assert len(r["enviados"]) == 1
    leu = S5._sentida(r)["leu"]
    linhas = [str(l.get("content") or "") for l in r["linhas_do_segurado"]]
    historico = "\n".join(linhas[:-1])           # a última linha é a do turno de agora
    for foto in ("foto-01.jpg", "foto-02.jpg"):
        assert (historico + "\n" + leu).count("descrição de %s" % foto) == 1, (foto, leu)
    # CONTROLE: o modelo continua lendo a fala INTEIRA (o texto das duas metades)
    assert "o carro bateu assim" in leu and "e o pneu furou" in leu
    assert "NÃO foi enviada" in leu
