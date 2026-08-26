# -*- coding: utf-8 -*-
"""O travamento vira evidência — e o clique tem dono. SPEC-093, BLOCO C.

📊 **O problema, medido no banco de produção em 25/08/2026:**

```
work_runs  com unblock_state = 'assumido_por_humano' ......  0
work_events com actor_type humano em 27.985 eventos ......  0
work_steps com marca `manual` ............................  0
work_events com evento de Cérebro ou Sentinela ...........  0
```

`note_manual_outbound` tocava **só no Redis**. A atendente respondia à
seguradora pelo WhatsApp dela, o caso saía de `needs_human`, e
`decidir_travamento` gravava `retomado_pelo_robo`: **o robô levava o crédito do
trabalho dela.**

> 🔴 Sem este bloco, duas semanas de atendimento real produzem **zero linhas**
> sobre onde o produto falha.

## ⚠️ E um defeito que a medição encontrou de lado

`acionamentos-travados/route.ts` escrevia `actor_type: 'human'`. 📊 O CHECK
`ck_work_events_actor` aceita exatamente `system | worker | user | agent |
admin | provider` — **`human` não está na lista.** Todo INSERT de linha do tempo
do botão *assumir* era recusado pelo Postgres, dentro de um `catch` que só
imprime no console. 📊 E o banco concorda: **0 linhas** com ator humano.

O guarda ⑧ deste arquivo lê os dois lados — o CHECK que o banco tem e o valor
que o código escreve — e é o único jeito de isso não voltar.

## O que este arquivo guarda, em uma frase

> **Cada travamento é UM evento contável, e quem destravou tem nome.**
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

# 🔴 O DUBLÊ DE BANCO É REUSADO, NÃO COPIADO (CLAUDE.md §5).
#
# `test_o_desfecho_nao_apaga_o_travamento` já tem o `BancoFalso` com a regra do
# `IN` que não casa NULO, o carregador do router e o `_com_o_pacote_app` que
# impede o verde-por-ModuleNotFoundError. Uma segunda cópia divergiria na
# primeira correção que só uma das duas recebesse.
from test_o_desfecho_nao_apaga_o_travamento import (  # noqa: E402
    ROUTER, BancoFalso, _com_o_pacote_app,
)

RAIZ = Path(__file__).resolve().parent.parent
ROTA_PAINEL = RAIZ.parent / "app" / "api" / "dashboard" / "acionamentos-travados" / "route.ts"


# ---------------------------------------------------------------------------
# O CENÁRIO
# ---------------------------------------------------------------------------

def _sessao(**extra):
    s = {
        "work_run_id": "run-A", "company_id": "c-resulta",
        "playbook_ref": "allianz-residencial-whatsapp@v1",
        "state": "needs_human", "reason": "missing_slots:problema_eletrico_opcao",
        "step_counts": {"menu_tipo_servico": 1, "problema_eletrico_opcao": 1},
        "insurer_phone": "5511999999999", "case_id": "caso-1",
    }
    s.update(extra)
    return s


def _banco(estado=None, company="c-resulta"):
    b = BancoFalso()
    b.dados["work_runs"] = [{
        "id": "run-A", "company_id": company, "status": "waiting_input",
        "unblock_state": estado,
    }]
    b.dados["work_events"] = []
    return b


def _eventos(banco, tipo=None):
    linhas = banco.dados.get("work_events") or []
    return [l for l in linhas if tipo is None or l.get("event_type") == tipo]


async def _marcar(banco, session, fase, fase_anterior, company="c-resulta"):
    """Chama `_marcar_travamento` REAL com o dublê — e prova que chegou nele."""
    with _com_o_pacote_app():
        await ROUTER._marcar_travamento(banco, "run-A", fase, fase_anterior,
                                        company_id=company, session=session)


def _rodar(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# ① corredor trava → 1 evento contável, com rota e tela
# ---------------------------------------------------------------------------

def test_GATE_1_travou_UM_evento_contavel_com_rota_e_tela():
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))

    abertos = _eventos(b, "travamento.aberto")
    assert len(abertos) == 1, f"esperava 1 evento de travamento, veio {len(abertos)}"
    carga = abertos[0]["payload_redacted"]
    assert carga["rota"] == "allianz-residencial-whatsapp@v1"
    assert carga["tela"] == "problema_eletrico_opcao", (
        "a tela não foi identificada — sem ela o piloto não diz ONDE o produto "
        f"falha, só que falhou. Veio: {carga.get('tela')!r}")
    assert abertos[0]["severity"] == "warning"


def test_a_tela_sai_do_step_counts_quando_o_motivo_nao_a_nomeia():
    """📊 `sentinela_stall` e `insurer_closed` não nomeiam tela no motivo."""
    s = _sessao(reason="sentinela_stall")
    assert ROUTER.tela_do_travamento(s) == "problema_eletrico_opcao"


def test_CONTROLE_acionamento_que_vai_bem_nao_gera_evento_nenhum():
    """§9.3 — **um gravador que grava sempre não mede nada.**

    🔴 É a mesma linha de controle que `decidir_travamento` já carrega, agora
    para os eventos: `ura → captured → monitoring` não pode produzir uma única
    linha de travamento.
    """
    b = _banco()
    s = _sessao(state="captured", reason="")
    for antes, agora in (("", "ura"), ("ura", "captured"), ("captured", "monitoring")):
        _rodar(_marcar(b, s, agora, antes))
    assert _eventos(b) == [], (
        f"acionamento que foi bem gerou {len(_eventos(b))} eventos de travamento")


# ---------------------------------------------------------------------------
# ② o Sentinela destrava → o evento diz `sentinela`
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("quem,ator", [
    ("sentinela", "agent"), ("cerebro", "agent"), ("vigia", "agent"),
])
def test_GATE_2_e_4_o_agente_que_destravou_tem_NOME(quem, ator):
    b = _banco(estado="travado")
    s = _sessao(destravado_por=quem)
    _rodar(_marcar(b, s, "ura", "needs_human"))

    ev = _eventos(b, "travamento.destravado")
    assert len(ev) == 1
    assert ev[0]["payload_redacted"]["por"] == quem
    assert ev[0]["actor_type"] == ator, (
        f"ator '{ev[0]['actor_type']}' — o CHECK do banco só aceita "
        f"{ROUTER.ATORES_VALIDOS}")


# ---------------------------------------------------------------------------
# ③ 🔴 um humano clica no WhatsApp → o evento diz `humano`, NÃO `robo`
# ---------------------------------------------------------------------------

def _o_humano_clica(banco, session, texto="Confirmo, pode abrir o chamado."):
    """A atendente responde à seguradora pelo WhatsApp DELA — caminho REAL.

    🔴 ESTE ATALHO NÃO EXISTE POR CONVENIÊNCIA. A primeira versão do gate ②
    marcava `session["destravado_por"] = "humano"` à mão, e por isso passava
    **com a marca desligada em `note_manual_outbound`** — a função que o BLOCO
    C.1 existe para mudar. 📊 Medido: a mutação obrigatória da SPEC deixou os
    24 testes VERDES.

    ⚠️ Um guarda que pula a função que o bloco muda não guarda o bloco
    (CLAUDE.md §9.3). Aqui o clique atravessa o Redis (dublê), a marca na
    sessão, a coluna e a linha do tempo — igual à produção.
    """
    guardado = {}

    async def _carregar(company_id, insurer_phone):
        return session

    async def _salvar(company_id, insurer_phone, sessao):
        guardado["sessao"] = sessao

    async def _db_falso():
        return banco

    originais = (ROUTER.load_active_dispatch, ROUTER.save_active_dispatch, ROUTER._db)
    ROUTER.load_active_dispatch = _carregar
    ROUTER.save_active_dispatch = _salvar
    ROUTER._db = _db_falso
    try:
        with _com_o_pacote_app():
            ok = _rodar(ROUTER.note_manual_outbound(
                "c-resulta", "5511999999999", texto))
    finally:
        (ROUTER.load_active_dispatch, ROUTER.save_active_dispatch,
         ROUTER._db) = originais

    assert ok is True, "`note_manual_outbound` recusou o clique"
    assert guardado.get("sessao") is session, (
        "a sessão não foi salva — a marca do humano morre no fim da função e "
        "QUALQUER asserção abaixo seria verde por acidente")
    return session


def test_GATE_3_o_clique_do_humano_NAO_e_creditado_ao_robo():
    """🔴 **O gate que o bloco existe para guardar.**

    ⚠️ A mutação obrigatória da SPEC é aqui: desligue a marca do humano em
    `note_manual_outbound` e este teste **tem** de ficar vermelho. 📊 E fica —
    foi medido, depois de a primeira versão deste teste **não** ficar.
    """
    b = _banco(estado="travado")
    s = _o_humano_clica(b, _sessao())

    # a atendente falou — e o produto já sabe, antes mesmo de a fase mudar
    assert b.dados["work_runs"][0]["unblock_state"] == "assumido_por_humano"
    assert len(_eventos(b, "travamento.assumido")) == 1
    assert s.get("destravado_por") == "humano", (
        "`note_manual_outbound` não marcou quem trabalhou — a próxima fase vai "
        "creditar o robô")

    # e quando a fase anda, o crédito é dela
    b.dados["work_runs"][0]["unblock_state"] = "travado"
    _rodar(_marcar(b, s, "ura", "needs_human"))

    ev = _eventos(b, "travamento.destravado")
    assert len(ev) == 1
    carga = ev[0]["payload_redacted"]
    assert carga["por"] == "humano", (
        "o trabalho da atendente foi creditado ao robô — que é exatamente a "
        "mentira que o BLOCO C existe para consertar")
    assert carga["canal"] == "whatsapp"
    assert ev[0]["actor_type"] == "user"

    # E a coluna NÃO recebe `retomado_pelo_robo`.
    assert b.dados["work_runs"][0]["unblock_state"] == "travado", (
        "`retomado_pelo_robo` foi gravado por cima de um destravamento humano")


def test_GATE_3b_o_clique_entra_no_transcript_marcado_como_humano():
    """O Espelho continua completo — era o que a função já fazia bem, e não
    pode ter sido quebrado por ganhar três escritas novas."""
    b = _banco(estado="travado")
    s = _o_humano_clica(b, _sessao(), texto="Confirmo, pode abrir o chamado.")
    ultima = s["transcript"][-1]
    assert ultima["manual"] is True and ultima["via"] == "humano"
    assert ultima["text"] == "Confirmo, pode abrir o chamado."
    assert ultima.get("at"), "a hora do clique não foi registrada"


def test_GATE_3c_o_clique_sem_sessao_viva_nao_inventa_nada():
    """Sem dispatch ativo não há acionamento para assumir."""
    async def _sem_sessao(company_id, insurer_phone):
        return None

    original = ROUTER.load_active_dispatch
    ROUTER.load_active_dispatch = _sem_sessao
    try:
        with _com_o_pacote_app():
            assert _rodar(ROUTER.note_manual_outbound(
                "c-resulta", "5511999999999", "oi")) is False
    finally:
        ROUTER.load_active_dispatch = original


def test_CONTROLE_sem_marca_nenhuma_o_credito_E_do_robo():
    """§9.2 — a linha de controle que dá direito à conclusão acima.

    🔴 Sem ela, um bug que escrevesse `humano` sempre passaria no gate ③ e o
    arquivo inteiro provaria nada. A URA voltando a falar sozinha **é** retomada
    pelo robô, e apagar isso trocaria uma mentira por outra.
    """
    b = _banco(estado="travado")
    _rodar(_marcar(b, _sessao(), "ura", "needs_human"))

    ev = _eventos(b, "travamento.destravado")
    assert len(ev) == 1
    assert ev[0]["payload_redacted"]["por"] == "robo"
    assert ev[0]["actor_type"] == "system"
    assert b.dados["work_runs"][0]["unblock_state"] == "retomado_pelo_robo", (
        "a retomada pelo robô parou de ser gravada — o gate ③ acima passaria "
        "por um `if` que nunca decide nada")


def test_a_decisao_PURA_e_a_condicao_a_mais():
    """A condição do C.1 é testável sem banco, sem Redis e sem rede."""
    assert ROUTER.decidir_travamento("ura", "needs_human") == "retomado_pelo_robo"
    assert ROUTER.decidir_travamento("ura", "needs_human",
                                     destravado_por="humano") is None
    # 🔴 CÉREBRO E SENTINELA SÃO O ROBÔ PARA A COLUNA.
    #
    # ⚠️ A primeira versão fazia os dois suprimirem `retomado_pelo_robo`, e a
    # coluna ficava `travado` PARA SEMPRE depois de um destrave automático: o
    # caso aparecia na Fila como travado tendo sido retomado. Quem distingue
    # qual robô trabalhou é o EVENTO — é o C.2 inteiro.
    for automatico in ("cerebro", "sentinela", "vigia"):
        assert ROUTER.decidir_travamento(
            "ura", "needs_human", destravado_por=automatico) == "retomado_pelo_robo", (
            f"`{automatico}` suprimiu a retomada pelo robô — a coluna fica "
            "`travado` para sempre")
    # `robo` explícito continua sendo robô — não é marca de gente.
    assert ROUTER.decidir_travamento("ura", "needs_human",
                                     destravado_por="robo") == "retomado_pelo_robo"
    # E travar continua travando.
    assert ROUTER.decidir_travamento("needs_human", "ura",
                                     destravado_por="humano") == "travado"


# ---------------------------------------------------------------------------
# ⑤ 🔴 trava DUAS vezes no mesmo run → DOIS eventos (o furo do `unblock_state`)
# ---------------------------------------------------------------------------

def test_GATE_5_travou_duas_vezes_no_mesmo_run_DOIS_eventos():
    """🔴 **O furo que a coluna não tem como tapar.**

    `work_runs.unblock_state` é UMA coluna: trava, destrava, trava de novo — e
    no fim há um só valor. A pergunta *"quantas vezes travou hoje"* não tem
    resposta possível a partir dela.

    ⚠️ E a segunda passagem por `travado` **não muda coluna nenhuma**: o filtro
    `IS NULL` a barra, com razão. Se os eventos dependessem da mudança de
    coluna, o segundo travamento seria invisível.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))          # travou
    _rodar(_marcar(b, s, "ura", "needs_human"))          # a URA voltou sozinha
    s["reason"] = "missing_slots:confirmar_endereco"
    _rodar(_marcar(b, s, "needs_human", "ura"))          # travou de novo

    abertos = _eventos(b, "travamento.aberto")
    assert len(abertos) == 2, (
        f"dois travamentos produziram {len(abertos)} eventos — a contagem do "
        "piloto está errada por construção")
    telas = [e["payload_redacted"]["tela"] for e in abertos]
    assert telas == ["problema_eletrico_opcao", "confirmar_endereco"], (
        f"os dois travamentos não distinguem a tela: {telas}")

    # 🔴 A COLUNA, sozinha, contaria UM. Esta asserção prova o furo: ela
    # ficou em `retomado_pelo_robo` — UM valor — enquanto os eventos contam DOIS
    # travamentos, com telas diferentes.
    assert b.dados["work_runs"][0]["unblock_state"] == "retomado_pelo_robo"


def test_GATE_5b_o_humano_no_meio_NAO_engole_o_segundo_travamento():
    """A mesma conta, com uma pessoa destravando pelo caminho REAL.

    ⚠️ O painel achou o inverso deste caso: um filtro de idempotência que
    olhasse só *"já há evento?"* engoliria o segundo travamento. Ele olha o
    estado durável — e depois da assunção humana o estado deixa de ser
    `travado`, então o travamento seguinte conta.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    s = _o_humano_clica(b, s)                            # caminho REAL
    _rodar(_marcar(b, s, "ura", "needs_human"))
    s["reason"] = "missing_slots:confirmar_endereco"
    _rodar(_marcar(b, s, "needs_human", "ura"))

    assert len(_eventos(b, "travamento.aberto")) == 2
    quem = [e["payload_redacted"]["por"]
            for e in _eventos(b, "travamento.destravado")]
    assert quem == ["humano"], quem


def test_GATE_5c_a_varredura_de_5_em_5_min_NAO_conta_de_novo():
    """🔴 O achado mais silencioso do painel.

    `reconciliar_acionamentos_orfaos` roda a cada 5 minutos e chama
    `_marcar_travamento(..., fase_anterior="")`. Sem a leitura do estado
    durável, um `needs_human` emitiria `travamento.aberto` **em toda passada,
    para sempre** — e `entrada` é lido do banco e nunca regravado, então nada
    na sessão cortava o laço.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert len(_eventos(b, "travamento.aberto")) == 1
    for _ in range(5):                                   # cinco varreduras
        _rodar(_marcar(b, dict(_sessao()), "needs_human", ""))
    assert len(_eventos(b, "travamento.aberto")) == 1, (
        f"a varredura contou de novo: {len(_eventos(b, 'travamento.aberto'))} "
        "eventos para UM travamento")


def test_CONTROLE_o_filtro_de_idempotencia_NAO_engole_travamento_de_verdade():
    """§9.3 — prove que o filtro sabe deixar passar.

    🔴 Sem esta linha, um filtro que suprimisse TODO `aberto` passaria no
    teste acima e apagaria a contagem inteira do piloto.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    _rodar(_marcar(b, s, "ura", "needs_human"))
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert len(_eventos(b, "travamento.aberto")) == 2


def test_o_destrave_pelo_PAINEL_e_um_BURACO_CONHECIDO_e_delimitado():
    """⚠️ **O botão *assumir* grava no BANCO e não toca na sessão do Redis.**

    🔴 ESTE TESTE JÁ AFIRMOU O CONTRÁRIO, E A AFIRMAÇÃO ESTAVA CERTA POR
    POUCO TEMPO.

    O painel achou o buraco (o `destravado` saindo `por: robo` logo depois de um
    `assumido` humano), e o conserto foi ler `work_runs.unblock_state` e creditar
    o humano. ⚠️ **O juiz de confirmação mostrou o preço desse conserto:**

    📊 `assumido_por_humano` é **grudento** — a escrita de `travado` filtra por
    `IS NULL`, a de `retomado_pelo_robo` por `== 'travado'`. Nenhuma escrita
    posterior o tira. Então creditar a partir da coluna fazia **todo destrave
    seguinte daquele run** virar trabalho de pessoa, inclusive os do robô — a
    mesma mentira do eco da própria voz, com o gatilho invertido.

    > 🔴 O crédito mora na SESSÃO, que é por travamento. A coluna é por RUN, e
    > um valor por run não sabe atribuir N travamentos.

    ## O que fica, e por que é aceitável

    ⛔ O `travamento.destravado` do caminho do painel sai `por: robo`. ✅ Mas o
    `travamento.assumido` que a **própria rota** grava, com `canal: dashboard`,
    continua na linha do tempo — a pergunta *"uma pessoa assumiu?"* tem resposta.

    📊 E o caminho **não é alcançável hoje**: a rota `acionamentos-travados` tem
    zero consumidores em `*.tsx` (P-251). Registrado em `PENDENCIAS.md`.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    # a atendente clica no PAINEL: o banco muda, a sessão não
    b.dados["work_runs"][0]["unblock_state"] = "assumido_por_humano"
    _rodar(_marcar(b, s, "ura", "needs_human"))

    ev = _eventos(b, "travamento.destravado")[0]
    assert ev["payload_redacted"]["por"] == "robo", (
        "o crédito voltou a sair da COLUNA — e a coluna é grudenta: todo "
        "destrave seguinte deste run passa a ser creditado a uma pessoa")
    # ✅ e a coluna NÃO foi pisada: quem assumiu continua com o nome dele
    assert b.dados["work_runs"][0]["unblock_state"] == "assumido_por_humano"


def test_o_credito_do_HUMANO_nao_sobrevive_ao_destrave_seguinte():
    """🔴 **O cenário exato que o juiz de confirmação escreveu.**

    ⚠️ A oscilação `ura ↔ needs_human` *"acontece toda hora"* — está na
    docstring de `registrar_checkpoint`. Então o segundo destrave do mesmo run
    é comum, não excepcional:

    ```
    trava #1 → a atendente responde pelo WhatsApp → destrava #1  (humano)
    trava #2 → a URA volta a falar sozinha        → destrava #2  (robô)
    ```

    🔴 Se o crédito viesse da coluna, o segundo também sairia `humano` — e a
    conta que o BLOCO C existe para produzir (*"quanto trabalho humano o produto
    ainda custa"*) sairia inflada para sempre.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    s = _o_humano_clica(b, s)                     # caminho REAL: grava a coluna
    assert b.dados["work_runs"][0]["unblock_state"] == "assumido_por_humano"
    _rodar(_marcar(b, s, "ura", "needs_human"))   # destrava #1

    s["reason"] = "missing_slots:confirmar_endereco"
    _rodar(_marcar(b, s, "needs_human", "ura"))   # trava #2
    _rodar(_marcar(b, s, "ura", "needs_human"))   # destrava #2 — a URA, sozinha

    quem = [e["payload_redacted"]["por"]
            for e in _eventos(b, "travamento.destravado")]
    assert quem == ["humano", "robo"], (
        f"o crédito do humano atravessou o travamento seguinte: {quem}")
    assert len(_eventos(b, "travamento.aberto")) == 2


def test_a_marca_NAO_e_perdida_numa_COPIA_da_sessao():
    """🔴 `session = dict(session)` rebindava o nome local.

    ⚠️ As escritas do rodapé (`travado_desde`, e a limpeza da marca) caíam na
    **cópia**, e quem salva a sessão é o chamador — que tem a original. Depois de
    uma assunção humana, `travado_desde` nunca mais persistia e
    `segundos_travado` sumia de todos os destraves seguintes daquele run.
    """
    b = _banco()
    s = _sessao()
    b.dados["work_runs"][0]["unblock_state"] = "assumido_por_humano"
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert s.get("travado_desde"), (
        "o relógio do travamento foi escrito numa cópia e se perdeu")
    _rodar(_marcar(b, s, "ura", "needs_human"))
    carga = _eventos(b, "travamento.destravado")[0]["payload_redacted"]
    assert "segundos_travado" in carga


def test_a_varredura_NAO_engole_travamento_de_verdade():
    """🔴 O outro achado do juiz: o filtro de idempotência era largo demais.

    ⚠️ A primeira versão filtrava **toda** abertura cuja coluna estivesse em
    `travado`. Se a escrita best-effort de `assumido_por_humano` falhar, a coluna
    fica `travado` **para sempre** — e a partir daí todo travamento daquele run
    sumia da contagem.

    Agora o filtro é só da varredura (`fase_anterior == ""`), que é onde ele
    nasceu. Uma transição REAL de fase é sempre um travamento novo.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert b.dados["work_runs"][0]["unblock_state"] == "travado"

    # a assunção humana FALHOU no banco (best-effort): a coluna fica `travado`
    s["destravado_por"] = "humano"
    _rodar(_marcar(b, s, "ura", "needs_human"))
    assert b.dados["work_runs"][0]["unblock_state"] == "travado"

    # e o travamento SEGUINTE, que é real, continua contando
    s["reason"] = "missing_slots:confirmar_endereco"
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert len(_eventos(b, "travamento.aberto")) == 2, (
        "o filtro de idempotência engoliu um travamento de verdade")


def test_o_credito_nao_atravessa_o_travamento_seguinte():
    """⚠️ Um humano destrava hoje; a URA cai de novo e o robô retoma amanhã.

    Se a marca não fosse limpa, o humano levaria o crédito das duas vezes.
    """
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    s["destravado_por"] = "humano"
    _rodar(_marcar(b, s, "ura", "needs_human"))
    assert s.get("destravado_por") is None, "a marca do humano ficou grudada"
    _rodar(_marcar(b, s, "needs_human", "ura"))
    _rodar(_marcar(b, s, "ura", "needs_human"))

    quem = [e["payload_redacted"]["por"] for e in _eventos(b, "travamento.destravado")]
    assert quem == ["humano", "robo"], f"crédito errado no segundo ciclo: {quem}"


def test_quanto_tempo_ficou_travado():
    """*"quanto tempo ficou travado — do `needs_human` até a fase seguinte"*."""
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert s.get("travado_desde"), "o relógio do travamento não começou"
    _rodar(_marcar(b, s, "ura", "needs_human"))
    carga = _eventos(b, "travamento.destravado")[0]["payload_redacted"]
    assert "segundos_travado" in carga and carga["segundos_travado"] >= 0


# ---------------------------------------------------------------------------
# ⑥ ninguém destrava → o run continua `travado`, e aparece na Fila
# ---------------------------------------------------------------------------

def test_GATE_6_ninguem_destrava_o_run_continua_travado_e_na_Fila():
    b = _banco()
    s = _sessao()
    _rodar(_marcar(b, s, "needs_human", "ura"))
    assert b.dados["work_runs"][0]["unblock_state"] == "travado"
    assert _eventos(b, "travamento.destravado") == []

    # 📊 O filtro EXATO da Fila (`acionamentos-travados/route.ts`, default
    # `estado=travado`). Se o caso não tem este valor, ninguém o vê.
    assert b.dados["work_runs"][0]["unblock_state"] == "travado"


# ---------------------------------------------------------------------------
# ⑦ dois tenants: o travamento de um não conta para o outro
# ---------------------------------------------------------------------------

def test_GATE_7_o_travamento_de_uma_corretora_nao_conta_para_a_outra():
    """CLAUDE.md §7 — nenhum dado atravessa tenants."""
    b = _banco()
    b.dados["work_runs"].append({
        "id": "run-B", "company_id": "c-autofleet", "status": "waiting_input",
        "unblock_state": None})

    _rodar(_marcar(b, _sessao(), "needs_human", "ura", company="c-resulta"))

    eventos = _eventos(b)
    assert len(eventos) == 1
    assert eventos[0]["company_id"] == "c-resulta"
    assert all(e["company_id"] != "c-autofleet" for e in eventos), (
        "um evento da Resulta apareceu na AutoFleet")
    # e o run da outra corretora não foi tocado
    outro = next(l for l in b.dados["work_runs"] if l["id"] == "run-B")
    assert outro["unblock_state"] is None


def test_CONTROLE_a_outra_corretora_CONSEGUE_ter_evento():
    """§9.3 — *"quando o teste comparar duas coisas, prove que elas CONSEGUEM
    ser diferentes"*. Sem isto, `!= 'c-autofleet'` passaria com zero eventos."""
    b = _banco(company="c-autofleet")
    _rodar(_marcar(b, _sessao(), "needs_human", "ura", company="c-autofleet"))
    assert [e["company_id"] for e in _eventos(b)] == ["c-autofleet"]


# ---------------------------------------------------------------------------
# ⑧ o ator que o banco RECUSA
# ---------------------------------------------------------------------------

def test_GATE_8_ninguem_escreve_um_actor_type_que_o_CHECK_recusa():
    """📊 `ck_work_events_actor` aceita seis valores. `human` não é um deles.

    🔴 O painel escrevia `actor_type: 'human'` — INSERT recusado pelo Postgres,
    dentro de um `catch` que só imprime no console. 📊 O banco concorda: **0
    linhas** com ator humano em 27.985 eventos.

    ## ⚠️ O QUE ESTE GUARDA NÃO PODE FAZER, E É HONESTO DIZER

    Ele **não compara com o banco**. 📊 O CHECK `ck_work_events_actor` não tem
    DDL em nenhuma das 68 migrations do repositório (é uma das 9 versões
    aplicadas sem arquivo — `MIGRATIONS-AUTHORITY.md` §4), e um teste que abrisse
    conexão não rodaria no `gate.yml`.

    O que ele guarda é o LADO DO CÓDIGO: a lista que o produto usa, medida
    contra o banco em 25/08/2026 e escrita aqui como referência inspecionável —

    ```sql
    -- SELECT pg_get_constraintdef(oid) FROM pg_constraint
    --  WHERE conname = 'ck_work_events_actor';
    CHECK (actor_type = ANY (ARRAY['system','worker','user','agent','admin','provider']))
    ```

    🔴 Trazer esse CHECK para uma migration versionada está em `PENDENCIAS.md`.
    """
    assert ROUTER.ATORES_VALIDOS == (
        "system", "worker", "user", "agent", "admin", "provider")
    assert "human" not in ROUTER.ATORES_VALIDOS

    fonte = ROTA_PAINEL.read_text(encoding="utf-8")
    assert "actor_type: 'human'" not in fonte, (
        "o painel voltou a escrever um ator que o CHECK do banco recusa — a "
        "linha do tempo do botão `assumir` morre no primeiro clique")
    assert "actor_type: 'user'" in fonte

    # e o ator inválido nunca vaza pelo backend: cai para `system`, não estoura.
    b = _banco(estado="travado")
    _rodar(_marcar(b, _sessao(destravado_por="chef_de_cozinha"), "ura", "needs_human"))
    ev = _eventos(b, "travamento.destravado")[0]
    assert ev["actor_type"] in ROUTER.ATORES_VALIDOS
    assert ev["payload_redacted"]["por"] == "robo", (
        "um destravador desconhecido virou nome no relatório — o crédito tem "
        "de cair para `robo`, não inventar um agente")


def test_o_valor_do_assumido_e_o_QUE_O_BANCO_ACEITA():
    """🔴 A SPEC escreve `destravado_por_humano`; o CHECK do banco não o aceita.

    📊 `work_runs_unblock_state_check` aceita exatamente
    `travado | retomado_pelo_robo | assumido_por_humano | resolvido |
    abandonado`. E 📊 o botão *arquivar* filtra
    `.in(['travado','assumido_por_humano'])` — um sexto valor faria o caso
    **sumir da Fila**, que é o defeito que esta SPEC existe para matar.
    """
    assert ROUTER.ASSUMIDO_POR_HUMANO == "assumido_por_humano"
    fonte = ROTA_PAINEL.read_text(encoding="utf-8")
    assert "destravado_por_humano" not in fonte


# ---------------------------------------------------------------------------
# C.1 — o clique escreve de verdade
# ---------------------------------------------------------------------------

def test_C1_o_clique_no_whatsapp_marca_a_coluna_E_a_linha_do_tempo():
    b = _banco(estado="travado")
    s = _sessao()

    async def _db_falso():
        return b

    original = ROUTER._db
    ROUTER._db = _db_falso
    try:
        with _com_o_pacote_app():
            _rodar(ROUTER._registrar_assuncao_humana(
                "c-resulta", s, canal="whatsapp"))
    finally:
        ROUTER._db = original

    assert b.dados["work_runs"][0]["unblock_state"] == "assumido_por_humano"
    ev = _eventos(b, "travamento.assumido")
    assert len(ev) == 1
    assert ev[0]["actor_type"] == "user"
    assert ev[0]["payload_redacted"]["canal"] == "whatsapp"
    assert ev[0]["payload_redacted"]["estava_travado"] is True


def test_C1_o_clique_NAO_pisa_em_quem_assumiu_antes():
    """⚠️ Mesmo filtro atômico do botão do painel: quem chegou primeiro fica."""
    b = _banco(estado="resolvido")
    s = _sessao()

    async def _db_falso():
        return b

    original = ROUTER._db
    ROUTER._db = _db_falso
    try:
        with _com_o_pacote_app():
            _rodar(ROUTER._registrar_assuncao_humana("c-resulta", s, canal="whatsapp"))
    finally:
        ROUTER._db = original

    assert b.dados["work_runs"][0]["unblock_state"] == "resolvido", (
        "a assunção pelo WhatsApp pisou num caso já resolvido")
    # mas o evento SAI: a pessoa falou com a seguradora, e isso aconteceu.
    assert _eventos(b, "travamento.assumido")[0]["payload_redacted"][
        "estava_travado"] is False


# ---------------------------------------------------------------------------
# C.3 — o Cérebro e o Sentinela deixam rastro
# ---------------------------------------------------------------------------

def test_C3_o_cerebro_e_o_sentinela_deixam_rastro():
    """📊 Hoje só existe `beat("cerebro")` no Redis — e o Sentinela, nem isso.

    ⚠️ Sem isso o piloto não responde à pergunta do Founder: *"quero ver o
    desempenho do Vigia, Sentinela e do Cérebro"*.
    """
    b = _banco()
    s = _sessao()

    async def _db_falso():
        return b

    original = ROUTER._db
    ROUTER._db = _db_falso
    try:
        with _com_o_pacote_app():
            assert _rodar(ROUTER.registrar_ato_do_agente(
                "c-resulta", s, agente="cerebro",
                mensagem="redigiu", payload={"tentativa": 1})) is True
    finally:
        ROUTER._db = original

    ev = _eventos(b, "agente.cerebro")
    assert len(ev) == 1
    assert ev[0]["actor_type"] == "agent"
    assert ev[0]["payload_redacted"]["rota"] == "allianz-residencial-whatsapp@v1"
    assert ev[0]["payload_redacted"]["tela"] == "problema_eletrico_opcao"


def test_C3_o_codigo_dos_dois_agentes_CHAMA_o_registro():
    """Estrutural: a chamada existe nos dois pontos, e é onde o ato ACONTECE."""
    router = (RAIZ / "app" / "services" / "dispatch_router.py").read_text(encoding="utf-8")
    watchdog = (RAIZ / "app" / "tasks" / "dispatch_watchdog.py").read_text(encoding="utf-8")
    assert router.count('agente="cerebro"') == 2, (
        "a segunda redação (retentativa aceita) parou de contar — um desempenho "
        "que só registra acertos de primeira não é desempenho")
    assert 'agente="sentinela"' in watchdog
    # e o Sentinela marca quem destravou, senão o crédito vai para o robô
    assert 'session["destravado_por"] = "sentinela"' in watchdog


def test_C3_o_registro_NUNCA_derruba_o_acionamento():
    """Best-effort: contar travamento não pode matar o acionamento que trava."""
    async def _db_explode():
        raise RuntimeError("banco fora")

    original = ROUTER._db
    ROUTER._db = _db_explode
    try:
        with _com_o_pacote_app():
            assert _rodar(ROUTER.registrar_ato_do_agente(
                "c-resulta", _sessao(), agente="cerebro", mensagem="x")) is False
    finally:
        ROUTER._db = original


def test_sem_run_duravel_nao_ha_o_que_registrar():
    """Sessão sem `work_run_id` — nada a gravar, e nada estoura."""
    with _com_o_pacote_app():
        assert _rodar(ROUTER.registrar_ato_do_agente(
            "c-resulta", {"playbook_ref": "x"}, agente="cerebro",
            mensagem="x")) is False


# ---------------------------------------------------------------------------
# ⛔ CLAUDE.md §13.3 — presença, nunca conteúdo
# ---------------------------------------------------------------------------

def test_nenhum_evento_carrega_telefone_CPF_ou_nome():
    """⛔ Quem guarda o conteúdo da conversa é o Espelho."""
    b = _banco(estado="travado")
    s = _sessao(client_phone="5511987654321",
                slots={"cpf": "12345678901", "nome": "Fulano de Tal"},
                transcript=[{"direction": "in", "text": "meu CPF é 12345678901"}])
    _rodar(_marcar(b, s, "needs_human", "ura"))
    s["destravado_por"] = "humano"
    _rodar(_marcar(b, s, "ura", "needs_human"))

    despejo = repr(_eventos(b))
    for segredo in ("5511987654321", "12345678901", "Fulano"):
        assert segredo not in despejo, (
            f"`{segredo[:4]}...` vazou para `work_events` — §13.3 é presença, "
            "nunca conteúdo")


# ---------------------------------------------------------------------------
# 🔴 O ECO DA PRÓPRIA VOZ — o blocker que DUAS lentes cegas acharam
# ---------------------------------------------------------------------------

def test_o_ECO_DO_ROBO_nao_assume_o_caso():
    """🔴 **O BLOCO C, ao contrário.**

    📊 `webhook.py` chama `note_manual_outbound` para TODO `fromMe` — e a
    resposta que o próprio Cérebro mandou à seguradora **volta como `fromMe`**.
    Com as escritas duráveis do C.1, isso gravaria `assumido_por_humano` e um
    evento de ator `user` para uma mensagem que nenhuma pessoa escreveu.

    ⚠️ Uma URA de 15 turnos produziria ~15 linhas duráveis dizendo que um humano
    trabalhou onde só o robô falou — e a métrica que esta SPEC existe para
    produzir nasceria inteira errada.

    O guarda `e_a_nossa_propria_voz` existe desde 06/08 e já era consultado no
    webhook. Só faltava ser **usado** nesta chamada.
    """
    b = _banco(estado="travado")
    s = _sessao()

    async def _carregar(company_id, insurer_phone):
        return s

    async def _salvar(company_id, insurer_phone, sessao):
        pass

    async def _db_falso():
        return b

    originais = (ROUTER.load_active_dispatch, ROUTER.save_active_dispatch, ROUTER._db)
    ROUTER.load_active_dispatch, ROUTER.save_active_dispatch = _carregar, _salvar
    ROUTER._db = _db_falso
    try:
        with _com_o_pacote_app():
            ok = _rodar(ROUTER.note_manual_outbound(
                "c-resulta", "5511999999999",
                "Confirmo, pode abrir o chamado.", foi_humano=False))
    finally:
        (ROUTER.load_active_dispatch, ROUTER.save_active_dispatch,
         ROUTER._db) = originais

    assert ok is True, "o espelho tem de continuar registrando o eco"
    assert s["transcript"][-1]["via"] == "robo"
    assert s["transcript"][-1]["manual"] is False
    assert s.get("destravado_por") is None, (
        "o eco da própria voz marcou a sessão como trabalho humano")
    assert b.dados["work_runs"][0]["unblock_state"] == "travado", (
        "o eco do robô gravou `assumido_por_humano` — o BLOCO C ao contrário")
    assert _eventos(b, "travamento.assumido") == [], (
        "o eco do robô virou uma linha do tempo dizendo que uma pessoa assumiu")


def test_CONTROLE_a_MESMA_chamada_com_foi_humano_True_ASSUME():
    """§9.3 — prove que as duas conseguem ser diferentes.

    🔴 Sem esta linha, um `note_manual_outbound` que nunca assumisse nada
    passaria no teste acima e o BLOCO C inteiro estaria desligado.
    """
    b = _banco(estado="travado")
    s = _o_humano_clica(b, _sessao())
    assert s["transcript"][-1]["via"] == "humano"
    assert s["transcript"][-1]["manual"] is True
    assert s.get("destravado_por") == "humano"
    assert b.dados["work_runs"][0]["unblock_state"] == "assumido_por_humano"
    assert len(_eventos(b, "travamento.assumido")) == 1


def test_o_WEBHOOK_passa_quem_falou():
    """Estrutural: sem esta linha o conserto acima guarda um parâmetro que
    ninguém preenche.

    📊 É o único chamador de `note_manual_outbound` no produto.
    """
    webhook = (RAIZ / "app" / "api" / "webhook.py").read_text(encoding="utf-8")
    i = webhook.index("await note_manual_outbound(")
    chamada = webhook[i:webhook.index(")", webhook.index("foi_humano", i))]
    assert "foi_humano=not _fomos_nos" in chamada, (
        "o webhook parou de dizer QUEM falou — o eco do próprio robô volta a "
        "ser gravado como trabalho de uma pessoa")
    # e `_fomos_nos` continua sendo calculado pelo guarda de verdade
    assert "e_a_nossa_propria_voz(" in webhook


def test_a_marca_NAO_sobrevive_a_um_travamento_novo():
    """🔴 O segundo blocker da mesma lente.

    ⚠️ Limpar a marca só no destrave deixava uma marca posta **fora** de
    qualquer travamento ser consumida pelo travamento seguinte: um `fromMe` na
    fase `ura` marcava `humano`, e horas depois a URA voltando a falar sozinha
    era contada como trabalho de pessoa — e `decidir_travamento` ainda suprimia
    o `retomado_pelo_robo` que era a verdade.
    """
    b = _banco()
    s = _sessao(destravado_por="humano", canal_do_destrave="whatsapp")
    _rodar(_marcar(b, s, "needs_human", "ura"))          # abre um travamento
    assert s.get("destravado_por") is None, (
        "a marca sobreviveu à abertura de um travamento novo")

    _rodar(_marcar(b, s, "ura", "needs_human"))          # a URA volta sozinha
    ev = _eventos(b, "travamento.destravado")[0]
    assert ev["payload_redacted"]["por"] == "robo"
    assert b.dados["work_runs"][0]["unblock_state"] == "retomado_pelo_robo", (
        "a marca velha suprimiu o `retomado_pelo_robo` de um destrave que foi "
        "mesmo do robô")
