# -*- coding: utf-8 -*-
"""SPEC-122 · CONSERTO ÚNICO, parte X — o fluxo `sem_chute` → segurado, e a SOMBRA.

Cada teste reproduz um achado dos laudos (red team `RT-*`, juiz `J-*`) pelo MOTOR, com a tela
REAL do acervo (`tests/corpus/telas_reais`), e traz a sua linha de CONTROLE. O fio e os dublês são
os de `test_spec122_sombra_e_sem_chute.py` (dublê só na BORDA: cliente do modelo, banco, Redis,
WhatsApp). ⛔ Nada sai da máquina.
"""
from __future__ import annotations

import asyncio
import inspect
import json

import pytest

# 🔴 AC/CP/R/D vêm do FIO COERENTE do arquivo irmão (P-121-28), nunca de `app.services` direto:
#    na suíte, o `app.services.insurer_dispatch_service` do `sys.modules` pode ser a CÓPIA que
#    outro arquivo gravou — e o `monkeypatch` cairia num motor que o roteador não chama.
from tests.test_spec122_sombra_e_sem_chute import (  # noqa: F401 — `amb` e `_fio_fixo` são fixtures
    AC, CLIENTE, CORPUS, CP, D, EMPRESA_A, R, REF_HDI, REF_PORTO, TELA_RISCO_HDI, TELA_SEM_PASSO,
    URA, _a_seguradora, _ao_cliente, _fio_fixo, _ligar, _responder, _risco_hdi,
    _turno_da_fase_humana, amb, rodar_turno, salvar, sessao, tela_real,
)


def _carregar():
    return asyncio.run(R.load_active_dispatch(EMPRESA_A, URA))


def _provedor_da_sombra() -> str:
    """SPEC-123 F1a: a sombra chama o PRIMÁRIO do papel `destravador` (não mais o do `dispatch`)."""
    from app.factories.llm_factory import LLMFactory
    from app.services.destravador import PAPEL

    return LLMFactory.resolver_para({}, {}, papel=PAPEL).provider


# =============================================================================
# RT-B1 · a NAVEGAÇÃO nunca é oferecida ao segurado, e nunca volta como resposta
# =============================================================================
def test_RT_B1_a_pergunta_nao_oferece_voltar_e_nenhuma_das_anteriores_continua(amb):
    s = _risco_hdi(amb)
    rotulos = [r for _d, r in s["esperando_do_segurado"]["opcoes"]]
    assert "Voltar" in TELA_RISCO_HDI, "o CONTROLE: a tela real TEM a opção de navegação"
    assert not [r for r in rotulos if CP.rotulo_e_de_navegacao(r) and not r.startswith("Nenhuma")], rotulos
    assert "Nenhuma das anteriores" in rotulos, "a resposta de quem está num lugar seguro sumiu"
    assert "Voltar" not in _ao_cliente(amb)[0]


@pytest.mark.parametrize("resposta", ["6", "voltar", "Voltar ao menu", "menu", "sair"])
def test_RT_B1_navegacao_do_segurado_vai_a_uma_pessoa_e_nada_vai_a_ura(amb, resposta):
    """📊 A8: "6" (era "Voltar") ia à URA e ao slot, e o motor respondia "Voltar" em laço."""
    _risco_hdi(amb)
    assert _responder(amb, resposta) is True
    s = _carregar()
    assert _a_seguradora(amb) == []
    assert s["state"] == "needs_human" and s["reason"] == "sem_chute:situacao_risco_opcao"
    assert not s["slots"].get("situacao_risco_opcao")


def test_RT_B1_em_todas_as_telas_reais_nenhuma_pergunta_oferece_navegacao():
    """Sobre o ACERVO inteiro das seguradoras com ida e volta: o motor casa o passo, o pedido
    lista as opções — e nenhuma é navegação. CONTROLE: a tela crua tinha navegação em alguma."""
    pedidos, tinha_navegacao = 0, 0
    for ref in ("hdi-auto-whatsapp@v1", "yelum-auto-whatsapp@v3", "hdi-residencial-whatsapp@v1",
                "yelum-residencial-whatsapp@v1", REF_PORTO):
        pb = D.get_playbook(ref)
        if not pb:
            continue
        arq = CORPUS / f"{pb['insurer_key']}-{pb.get('line_kind') or 'auto'}.jsonl"
        if not arq.exists():
            continue
        for linha in arq.read_text(encoding="utf-8").splitlines():
            t = json.loads(linha)["text"]
            for sub in (pb.get("subservices") or {}):
                passo = D.match_ura_step(pb, t, subservice=sub)
                if not (passo and passo.get("sem_chute")):
                    continue
                req = list(passo.get("requires") or [])
                ped = D.sem_chute_ao_segurado(pb, passo["step"], req, t,
                                              {"client_phone": "x", "slots": {}}, estado_antes="ura")
                if ped and ped["opcoes"]:
                    pedidos += 1
                    tinha_navegacao += any(D.navega_para_o_segurado(r) for r in D._rotulos_da_tela(t))
                    assert not [r for _d, r in ped["opcoes"] if D.navega_para_o_segurado(r)], (ref, t[:120])
                break
    assert pedidos >= 5 and tinha_navegacao >= 1, (pedidos, tinha_navegacao)


# =============================================================================
# RT-B2 · o `sem_chute` de DECISÃO não vira pergunta
# =============================================================================
TELA_SERVICO_ABERTO = tela_real("porto-auto", r"tem um servi[çc]o aberto")


def test_RT_B2_servico_aberto_porto_volta_a_ir_a_uma_pessoa_e_o_caso_nao_e_corrompido(amb):
    """📊 A9/A10: virava pergunta "qual servico o cliente precisa", e o "Não" da URA
    sobrescrevia `servico_texto` — o menu de serviços respondia "Não"."""
    salvar(EMPRESA_A, sessao(REF_PORTO, "guincho", slots={"servico_texto": "guincho"}))
    s = rodar_turno(amb, EMPRESA_A, TELA_SERVICO_ABERTO)
    assert s["state"] == "needs_human" and s["reason"] == "sem_chute:servico_texto"
    assert "esperando_do_segurado" not in s
    assert not [t for t in _ao_cliente(amb) if "Só mais uma informação" in t]
    assert s["slots"]["servico_texto"] == "guincho" and _a_seguradora(amb) == []


def test_RT_B2_CONTROLE_o_envio_do_servico_aberto_e_o_de_antes_da_spec_122(amb, monkeypatch):
    """"Como antes" medido: o MESMO envio com a tabela D2 vazia (o `sem_chute` de antes)."""
    def _rodar():
        amb.enviadas.clear(); amb.wa.clear(); amb.grupo.clear(); amb.redis.d.clear()
        salvar(EMPRESA_A, sessao(REF_PORTO, "guincho", slots={"servico_texto": "guincho"}))
        s = rodar_turno(amb, EMPRESA_A, TELA_SERVICO_ABERTO)
        return list(amb.enviadas), list(amb.grupo), s["state"], s.get("reason")
    agora = _rodar()
    monkeypatch.setattr(D, "IDA_E_VOLTA_AO_SEGURADO", {})
    assert _rodar() == agora


def test_RT_B2_a_lista_de_perguntaveis_e_so_de_dado_e_existe_nos_playbooks():
    decisao = {"servico_aberto_porto_auto", "bateria_submenu", "taxi_oferta", "taxi_alem_do_guincho",
               "selecionar_veiculo_porto", "cr_motivo"}
    assert not (decisao & set(D.SEM_CHUTE_PERGUNTAVEL))
    passos = {p["step"] for nome in dir(CP) for v in [getattr(CP, nome)]
              if isinstance(v, dict) and v.get("ura_steps") for p in v["ura_steps"] if p.get("sem_chute")}
    assert set(D.SEM_CHUTE_PERGUNTAVEL) <= passos, set(D.SEM_CHUTE_PERGUNTAVEL) - passos
    assert decisao <= passos, "o controle da lista tem de nomear passos que existem"
    # a pergunta é ao SEGURADO: 2ª pessoa, sem "o cliente", sem nota de cobertura
    for passo, copia in D.SEM_CHUTE_PERGUNTAVEL.items():
        assert " o cliente" not in copia and "cobert" not in copia and "ele " not in copia, passo


TELA_PASSAGEIROS_HDI = tela_real("hdi-auto", r"^Para quantos passageiros\?")


def test_RT_B2_passo_de_texto_o_slot_guarda_o_que_o_segurado_disse(amb):
    salvar(EMPRESA_A, sessao(REF_HDI, "guincho", slots={"problema_descricao": "o carro morreu"}))
    s = rodar_turno(amb, EMPRESA_A, TELA_PASSAGEIROS_HDI)
    assert s["esperando_do_segurado"]["slot"] == "taxi_passageiros", s.get("reason")
    assert "quantas pessoas vão no táxi" in _ao_cliente(amb)[0]
    assert _responder(amb, "3 pessoas") is True
    s = _carregar()
    assert _a_seguradora(amb) == ["3 pessoas"] and s["slots"]["taxi_passageiros"] == "3 pessoas"


# =============================================================================
# RT-B3 + RT-P2 (+ J-P1) · só a opção traduzida pelo MOTOR contra a tela de AGORA
# =============================================================================
def _vencer_e_reabrir(amb):
    s = _risco_hdi(amb)
    esp = dict(s["esperando_do_segurado"], de_acionamento_anterior=True)
    s.pop("esperando_do_segurado")
    s["espera_vencida"] = esp
    s["state"] = "ura"
    s.pop("falta_para_a_ura", None)
    salvar(EMPRESA_A, s)


def test_RT_B3_no_slot_texto_livre_nao_entra_cru_no_slot_de_tecla_e_vai_a_uma_pessoa(amb):
    """📊 A4: 'estou na estrada de terra perto de um posto' entrava em `situacao_risco_opcao` e a
    URA reaberta o recebia quando a tela de risco voltava."""
    _vencer_e_reabrir(amb)
    assert _responder(amb, "estou na estrada de terra perto de um posto") is True
    s = _carregar()
    assert not s["slots"].get("situacao_risco_opcao")
    assert s["state"] == "needs_human" and _a_seguradora(amb) == []


def test_RT_B3_CONTROLE_no_slot_com_uma_opcao_guarda_o_rotulo_e_o_motor_o_usa(amb):
    _vencer_e_reabrir(amb)
    assert _responder(amb, "2") is True
    s = _carregar()
    assert s["slots"]["situacao_risco_opcao"] == "Via com pouco movimento" and s["state"] == "ura"
    assert _a_seguradora(amb) == []                         # no_slot: nada sai AGORA
    amb.enviadas.clear(); amb.wa.clear()
    rodar_turno(amb, EMPRESA_A, TELA_RISCO_HDI)
    assert _a_seguradora(amb) == ["Via com pouco movimento"]


def test_RT_P2_a_ura_mudou_de_tela_durante_a_espera_a_resposta_vai_a_uma_pessoa(amb):
    """📊 A2: 'Via com pouco movimento' saía depois de uma tela 'Não entendi… Voltar / Responder
    novamente' — a resposta ia contra a tela da PERGUNTA, não a de agora."""
    _risco_hdi(amb)
    rodar_turno(amb, EMPRESA_A, tela_real("hdi-auto", r"N[ãa]o entendi\. Lembre-se"))
    assert _responder(amb, "2") is True
    s = _carregar()
    assert _a_seguradora(amb) == [] and s["state"] == "needs_human"


# =============================================================================
# RT-P1 · a MESMA tela repetida com a pergunta no ar é a MESMA pendência
# =============================================================================
def test_RT_P1_a_tela_repetida_nao_vira_handoff_e_a_resposta_ainda_e_levada(amb):
    _risco_hdi(amb)
    s = rodar_turno(amb, EMPRESA_A, TELA_RISCO_HDI)          # 📊 A1: a URA reenvia a mesma tela
    assert s["state"] == "ura" and "reason" not in s and s.get("esperando_do_segurado")
    assert len(_ao_cliente(amb)) == 1, _ao_cliente(amb)      # só a pergunta; nenhum "Não consegui…"
    assert amb.grupo == [] and _a_seguradora(amb) == []
    assert _responder(amb, "2") is True
    assert _a_seguradora(amb) == ["Via com pouco movimento"]
    assert _carregar()["state"] == "ura"


# =============================================================================
# J-B1 · "local seguro" do portão + BR 282 NÃO vira "Nenhuma das anteriores"
# =============================================================================
def test_J_B1_br_282_com_local_seguro_nao_responde_sozinho_e_pergunta(amb):
    """📊 `juiz_br282.py`, a sessão real do caso `cer-T-sem_chute-hdi-074` (BR 282): o motor
    respondia "Nenhuma das anteriores" à HDI, negando "Rodovia" pelo segurado."""
    salvar(EMPRESA_A, sessao(REF_HDI, "guincho", slots={
        "local_atual": "BR 282, sentido Florianopolis", "local_situacao": "local seguro"}))
    s = rodar_turno(amb, EMPRESA_A, TELA_RISCO_HDI)
    assert _a_seguradora(amb) == [] and not s["slots"].get("situacao_risco_opcao")
    assert s["esperando_do_segurado"]["slot"] == "situacao_risco_opcao"     # D-122 D2: pergunta


def test_J_B1_local_seguro_do_portao_nunca_alimenta_nenhuma_das_anteriores(amb):
    """A regra, sem depender do endereço: a pergunta do portão ("seguro, escuro ou deserto") não
    cobre Rodovia nem Alagamento — a resposta dela não nega as duas pelo segurado."""
    salvar(EMPRESA_A, sessao(REF_HDI, "guincho", slots={
        "local_atual": "Rua das Flores 10, Centro", "local_situacao": "local seguro"}))
    s = rodar_turno(amb, EMPRESA_A, TELA_RISCO_HDI)
    assert _a_seguradora(amb) == [] and s["esperando_do_segurado"]["slot"] == "situacao_risco_opcao"


def test_J_B1_CONTROLE_endereco_urbano_com_relato_seguro_continua_respondendo(amb):
    salvar(EMPRESA_A, sessao(REF_HDI, "guincho", slots={
        "local_atual": "Rua das Flores 10, Centro",
        "problema_descricao": "estou num lugar seguro, bem iluminado"}))
    rodar_turno(amb, EMPRESA_A, TELA_RISCO_HDI)
    assert _a_seguradora(amb) == ["Nenhuma das anteriores"]


@pytest.mark.parametrize("endereco", ["BR 282, sentido Florianopolis", "BR-101 km 30",
                                      "SC-401, Florianopolis", "SP 330 sentido capital",
                                      "Estrada Geral do Sertao", "Rodovia Castello Branco"])
def test_J_B1_o_veto_de_rodovia_ve_federal_estadual_e_estrada(endereco):
    slots = {"local_atual": endereco, "problema_descricao": "estou num lugar seguro"}
    D._derivar_teclas_do_caso(slots)
    assert slots.get("situacao_risco_opcao") is None, slots


# =============================================================================
# RT-P6 · o VALOR que aceita custo vira PESSOA, em qualquer tela
# =============================================================================
@pytest.mark.parametrize("valor", ["Sim, aceito o custo de R$ 200", "concordo com o valor",
                                   "Pode cobrar", "Tudo bem, R$ 150,00"])
def test_RT_P6_valor_que_aceita_custo_vira_pessoa(valor):
    s = sessao(REF_PORTO, "guincho")
    saida = json.dumps({"acao": "RESPONDER", "valor": valor, "motivo": "x"})
    d = AC.decidir(saida, s, TELA_SEM_PASSO, estruturada=True)
    assert (d["acao_final"], d["proibicao"]) == ("PESSOA", "aceite_de_custo"), d
    # CONTROLE: a MESMA saída sem a proibição ligada — o guarda é o que segura
    sem = AC.decidir(saida, s, TELA_SEM_PASSO, estruturada=True,
                     proibicoes=[p for p in AC.PROIBICOES if p != "aceite_de_custo"])
    assert sem["proibicao"] != "aceite_de_custo"


def test_RT_P6_CONTROLE_resposta_sem_custo_continua():
    d = AC.decidir('{"acao": "RESPONDER", "valor": "Para você", "motivo": "x"}',
                   sessao(REF_PORTO, "guincho"), TELA_SEM_PASSO, estruturada=True)
    assert d["proibicao"] != "aceite_de_custo"


# =============================================================================
# RT-P4 / J-P2 · a sombra não alimenta o DISJUNTOR nem usa a RESERVA de produção
# =============================================================================
@pytest.fixture
def breaker(monkeypatch):
    """O relógio REAL (`relogio_do_modelo`), com o Redis de memória do próprio módulo."""
    from app.core import relogio_do_modelo as RM

    dados: dict = {}

    async def _cliente():
        return RM._RedisDeMemoria(dados)

    monkeypatch.setattr(RM, "_cliente", _cliente)
    monkeypatch.setattr(RM, "BREAKER_FALHAS", 3)
    return RM


def test_RT_P4_n_falhas_da_sombra_nao_abrem_o_disjuntor_de_producao(amb, breaker):
    _ligar(amb, EMPRESA_A)
    amb.saida_do_modelo = ConnectionError("provedor caiu")     # transitório: CONTA para o breaker
    for i in range(5):
        _turno_da_fase_humana(amb, run=f"run-p4-{i}")
    assert len(amb.chamadas_ao_modelo) == 5 and amb.sombras() == []
    assert not any(c["relogio"] for c in amb.chamadas_ao_modelo)
    # §9.3 — SPEC-123: o provedor que a sombra usa é o do destravador; é ESSE breaker que não pode abrir
    prov = _provedor_da_sombra()
    assert {c["papel"] for c in amb.chamadas_ao_modelo} == {"destravador"}
    assert asyncio.run(breaker.estado_do_breaker(prov))["estado"] == "fechado"
    assert amb.chamadas_de_producao == [], "a sombra passou pelo helper COM reserva"


def test_RT_P4_CONTROLE_o_mesmo_modelo_com_o_relogio_abre_o_disjuntor(amb, breaker):
    """O guarda consegue ficar vermelho: as MESMAS falhas, pelo modelo que `create_llm` entrega
    (relógio anexado), abrem o breaker."""
    from app.factories.llm_factory import LLMFactory
    from langchain_core.messages import HumanMessage, SystemMessage

    amb.saida_do_modelo = ConnectionError("provedor caiu")
    from app.services.destravador import PAPEL

    r = LLMFactory.resolver_para({}, {}, papel=PAPEL)
    for _ in range(3):
        llm = LLMFactory.create_llm({}, {}, company_id=EMPRESA_A, service_type="x", modelo_resolvido=r)
        with pytest.raises(ConnectionError):
            asyncio.run(llm.ainvoke([SystemMessage(content="s"), HumanMessage(content="u")]))
    assert asyncio.run(breaker.estado_do_breaker(r.provider))["estado"] == "aberto"


def test_RT_P4_com_o_disjuntor_aberto_a_sombra_nao_chama(amb, breaker):
    _ligar(amb, EMPRESA_A)
    asyncio.run(breaker._abrir(asyncio.run(breaker._cliente()), *breaker._chaves(_provedor_da_sombra())))
    _turno_da_fase_humana(amb)
    assert amb.chamadas_ao_modelo == [] and amb.chamadas_de_producao == []


def test_RT_P4_a_cota_teto_de_sombras_em_voo(amb):
    async def _agendar():
        t = AC.agendar_sombra(EMPRESA_A, {}, "tela", {})
        if t is not None:
            await t
        return t
    # CONTROLE: com o teto livre, dentro de um loop, a sombra é agendada
    assert asyncio.run(_agendar()) is not None
    AC._SOMBRAS.update({"a", "b"})
    try:
        assert asyncio.run(_agendar()) is None
    finally:
        AC._SOMBRAS.difference_update({"a", "b"})


# =============================================================================
# RT-P5 · o rastro da sombra não leva nome solto
# =============================================================================
NOME = "Joaquim Beltrano Sintetico"


def test_RT_P5_nome_solto_nao_vai_para_work_events(amb):
    from app.services.intelligence.redaction_service import mascara_de_tela

    assert NOME in mascara_de_tela(f"o segurado é {NOME}"), "CONTROLE: o mascarador de tela sozinho deixa passar"
    _ligar(amb, EMPRESA_A)
    # SPEC-123: a saída no formato do DESTRAVADOR — a pergunta com o nome CHEGA ao payload
    #    (no formato velho ela virava "saída inválida" e o guarda passava sem nada a mascarar).
    amb.saida_do_modelo = json.dumps({"classe": "perguntar_ao_segurado", "acao": "PERGUNTAR_AO_SEGURADO",
                                      "valor": f"{NOME.split()[0]}, qual o seu CPF?", "nota": 50,
                                      "motivo": f"o titular é {NOME}"})
    salvar(EMPRESA_A, sessao(REF_PORTO, "guincho", estado="human_phase", slots={"nome": NOME}))

    async def _producao(sess, tela):
        return f"Para {NOME}"
    rodar_turno(amb, EMPRESA_A, TELA_SEM_PASSO + f"\nOlá {NOME.upper()}", provider=_producao)
    [ev] = amb.sombras()
    assert ev["payload_redacted"]["destravador"]["acao_final"] == "PERGUNTAR_AO_SEGURADO", (
        "o CONTROLE: a pergunta com o nome tem de ter chegado ao payload")
    gravado = json.dumps(ev["payload_redacted"], ensure_ascii=False)
    assert not [p for p in NOME.split() if p.lower() in gravado.lower()], gravado[:600]
    assert "{NOME}" in gravado


# =============================================================================
# J-P3 · o prompt que a sombra roda é o do PRODUTO, e a sombra não importa a bancada
# =============================================================================
def test_J_P3_a_sombra_monta_o_prompt_do_destravador_do_produto(amb, monkeypatch):
    """§9.3 — SPEC-123 F1a: a sombra deixou de rodar a V2 da bancada e passou a rodar o DESTRAVADOR.
    A lição fica: o prompt que a sombra roda é, byte a byte, o que o compositor do PRODUTO
    (`destravador.compor_mensagens`, o mesmo que a bancada da F2 importa) monta — e nem o módulo da
    sombra nem o destravador importam a bancada."""
    from app.services import destravador as DT
    from app.services.evals import bancada

    assert bancada.mensagens_da_variante is AC.mensagens_da_variante      # a V0–V3 da 122 continua
    assert "from app.services.evals" not in inspect.getsource(AC)
    assert "from app.services.evals" not in inspect.getsource(DT)
    vistas = []
    original = DT.compor_mensagens

    def _espiao(sessao_, tela_, **k):
        vistas.append((json.loads(json.dumps(sessao_, default=str)), tela_, dict(k)))
        return original(sessao_, tela_, **k)
    monkeypatch.setattr(DT, "compor_mensagens", _espiao)
    _ligar(amb, EMPRESA_A)
    _turno_da_fase_humana(amb)
    [ch] = amb.chamadas_ao_modelo
    [(s, tela, k)] = vistas
    medida = original(s, tela, **k)                                    # o que a BANCADA mediria
    assert "O ROTEIRO AUTOMÁTICO TRAVOU" in medida["system"]
    assert (ch["system"], ch["user"]) == (medida["system"], medida["user"])


# =============================================================================
# RT-P9 · a chave de dedupe: DEPOIS do sucesso, e do acionamento
# =============================================================================
def test_RT_P9_falha_do_modelo_nao_marca_a_tela_e_ela_e_remedida(amb):
    _ligar(amb, EMPRESA_A)
    amb.saida_do_modelo = ConnectionError("x")
    _turno_da_fase_humana(amb)
    assert amb.sombras() == [] and len(amb.chamadas_ao_modelo) == 1
    amb.saida_do_modelo = '{"classe": "nunca_sozinho", "acao": "PESSOA", "valor": "", "nota": 30, "motivo": "x"}'
    rodar_turno(amb, EMPRESA_A, TELA_SEM_PASSO, provider=lambda *_: _async("Para você"))
    assert len(amb.sombras()) == 1 and len(amb.chamadas_ao_modelo) == 2
    # CONTROLE: gravada, a mesma tela no mesmo acionamento NÃO chama de novo
    rodar_turno(amb, EMPRESA_A, TELA_SEM_PASSO, provider=lambda *_: _async("Para você"))
    assert len(amb.chamadas_ao_modelo) == 2


async def _async(v):
    return v


def test_RT_P9_sem_acionamento_nao_ha_chave_nem_chamada(amb):
    assert AC._chave_de_dedupe(EMPRESA_A, {}, "tela") == ""
    a = AC._chave_de_dedupe(EMPRESA_A, {"work_run_id": "r1"}, "tela")
    b = AC._chave_de_dedupe(EMPRESA_A, {"work_run_id": "r2"}, "tela")
    assert a and b and a != b
    _ligar(amb, EMPRESA_A)
    s = sessao(REF_PORTO, "guincho", estado="human_phase", run="")
    s.pop("case_id", None)
    p = asyncio.run(AC.sombra_do_cerebro(EMPRESA_A, s, TELA_SEM_PASSO, {"acao": "RESPONDER", "valor": "x"}))
    assert p is None and amb.chamadas_ao_modelo == []



def test_N1_apartamento_nao_vira_rodovia_na_bradesco():
    """🔴 Confirmação da SPEC-122 (N1): o veto largo de rodovia não pode ESCOLHER "Rodovia".
    CONTROLE: BR com número, "km 12", SP-330 e "rodovia" continuam escolhendo Rodovia."""
    from app.services.insurer_dispatch_service import _derivar_teclas_do_caso

    def via(endereco):
        slots = {"local_atual": endereco}
        _derivar_teclas_do_caso(slots)
        return slots.get("via_ou_rodovia_opcao")

    for urbano in ("Rua das Flores 10 ap 101", "Rua X 5, ap 42, bloco 3",
                   "Av Paulista 1000 al 12", "Aracaju SE 10"):
        assert via(urbano) != "Rodovia", urbano
    for rodovia in ("BR 282, sentido Florianopolis", "BR-101 km 30", "SP-330 perto do posto",
                    "Rodovia dos Bandeirantes", "estou no km 12 da estrada"):
        assert via(rodovia) == "Rodovia", rodovia
