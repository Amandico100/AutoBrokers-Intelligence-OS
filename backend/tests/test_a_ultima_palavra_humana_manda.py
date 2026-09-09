# -*- coding: utf-8 -*-
"""A última palavra humana da corretora manda — PLANO-HANDOFF-E-PAUSA §2 · U3.

> **O TESTE DO PRODUTO:** *"A Regina respondeu a este segurado ontem. Ele volta
> hoje. O robô fica calado — e continua calado até ela devolver a conversa ou
> até passarem N dias sem ela escrever."*

```
o agente responde ao segurado SE, E SÓ SE:
  1. não há palavra humana da corretora nesta conversa nos últimos N dias
  2. e a conversa não está reivindicada nem em HUMAN_REQUESTED
  3. e o agente está ligado                                  (fora deste teste)
```

🔴 **O MOTOR É CHAMADO, nunca o regex dele** (`CLAUDE.md` §9.4). Os sete
cenários da tabela do plano passam por `a_ia_deve_calar`, com um dublê de
PostgREST cujas linhas têm as colunas REAIS de `messages`
(`tests/fixtures/schema_vivo.json`: `role`, `content`, `created_at`, `payload`).

⛔ **E cada mutação abaixo tem de ficar VERMELHA** — senão o guarda é carimbo
(§9.3). Elas estão em `test_as_mutacoes_ficam_vermelhas`, e cada uma é o
comportamento de um defeito plausível, não de um typo:

```
N = 0          a regra desligada           → o cenário da Regina deixa de calar
N = 10**6      a janela infinita           → "3 meses" deixa de responder
origem='dashboard' ignorada                → a atendente do PAINEL vira invisível
`#nota` contada como palavra humana        → anotar volta a ser assumir
o eco do próprio agente contado como humano → o robô se cala para sempre
```

⚠️ **LINHA DE CONTROLE** (§9.2): a mesma conversa, sem mensagem humana nenhuma
— o agente responde. Sem ela, um dublê quebrado provaria o silêncio por engano.

⛔ Zero banco real. Zero mensagem enviada. Zero PII: todos os telefones e nomes
são inventados.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import o_fim_do_atendimento as F  # noqa: E402

AGORA = datetime(2026, 9, 9, 14, 0, tzinfo=timezone.utc)
EMPRESA = "corretora-autofleet"
CONVERSA = "conversa-1"


# ===========================================================================
# 0. O DUBLÊ — e ele fala o esquema VIVO de `messages`
# ===========================================================================

_SCHEMA = json.load(io.open(
    Path(__file__).resolve().parent / "fixtures" / "schema_vivo.json",
    encoding="utf-8"))["tabelas"]


def test_o_duble_usa_as_colunas_reais_de_messages():
    """🔴 O guarda do guarda: se `messages` perder ou ganhar uma coluna que este
    teste usa, é aqui que se descobre — não em produção."""
    colunas = set(_SCHEMA["messages"])
    assert {"role", "content", "created_at", "payload",
            "conversation_id"} <= colunas
    # ⛔ `messages` NÃO tem `company_id` — é o motivo de o §7 depender do
    #    `conversation_id` já ter sido resolvido com a corretora.
    assert "company_id" not in colunas
    assert {"claimed_by", "status", "resolvido_em"} <= set(_SCHEMA["conversations"])


def _msg(role, *, quando, texto="tudo bem", origem=None, nota=False):
    """Uma linha de `messages` como o PostgREST a devolve."""
    payload = {}
    if origem:
        payload["origem"] = origem
    if nota:
        payload["nota_interna"] = True
    return {"role": role, "content": texto,
            "created_at": quando.isoformat(),
            "payload": payload or None}


def _humana(dias_atras, *, origem="espelho", texto="oi, aqui é a Regina",
            nota=False, horas_atras=0):
    return _msg("assistant", origem=origem, nota=nota, texto=texto,
                quando=AGORA - timedelta(days=dias_atras, hours=horas_atras))


def _agente(dias_atras, texto="Sinto muito! Me diga a placa, por favor."):
    """A fala que o webhook grava no passo 8: `assistant` e SEM payload."""
    return _msg("assistant", texto=texto,
                quando=AGORA - timedelta(days=dias_atras))


def _segurado(dias_atras, texto="bati o carro"):
    return _msg("user", texto=texto, quando=AGORA - timedelta(days=dias_atras))


class _Res:
    def __init__(self, data):
        self.data = data

    def __await__(self):
        async def _eu():
            return self
        return _eu().__await__()


class _Tabela:
    def __init__(self, nome, linhas, quebrar):
        self.nome, self.linhas, self.quebrar = nome, linhas, quebrar

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self.quebrar:
            raise RuntimeError("PostgREST fora do ar")
        if self.nome == "messages":
            # O PostgREST devolve `order(desc=True)`: mais nova primeiro.
            return _Res(sorted(self.linhas, key=lambda m: m["created_at"],
                               reverse=True))
        if self.nome == "conversations":
            return _Res([{"id": CONVERSA}])
        return _Res([])


class _DB:
    """Dublê que diz "não há nada" por padrão — assim, quando o motor cala, a
    recusa só pode ter vindo das linhas que ESTE caso colocou."""

    def __init__(self, linhas=(), quebrar=False):
        self.linhas, self.quebrar = list(linhas), quebrar

    @property
    def client(self):
        db = self

        class _C:
            def table(self, nome):
                return _Tabela(nome, db.linhas, db.quebrar)
        return _C()


def _conversa(**campos):
    base = {"id": CONVERSA, "status": "open", "claimed_by": None,
            "claimed_by_name": None, "resolvido_em": None}
    base.update(campos)
    return base


def _porta(linhas=(), *, conversa=None, companhia=None, n_dias=None,
           quebrar=False):
    """🔴 O MOTOR REAL, com o relógio congelado no `agora` do caso."""
    return asyncio.run(F.a_ia_deve_calar(
        _DB(linhas, quebrar), company_id=EMPRESA,
        conversa=conversa or _conversa(), companhia=companhia,
        agora=AGORA, n_dias=n_dias))


N = 7  # o default do Founder, fixado em 09/09/2026


# ===========================================================================
# 1. OS SETE CENÁRIOS DA TABELA DO PLANO §2
# ===========================================================================

def test_1_regina_falou_ha_3_dias_o_agente_cala():
    """*"Regina começou há 3 dias, segurado volta hoje"* → **cala**."""
    calar, motivo = _porta([_agente(4), _humana(3), _segurado(0)], n_dias=N)
    assert calar is True
    # 🔴 O motivo é uma FRASE em português, com o prazo e a saída.
    assert "há 3 dias" in motivo
    assert "13/09" in motivo, motivo          # ela falou em 06/09; 06 + 7 = 13/09
    assert "devolver" in motivo


def test_2_regina_falou_ha_3_meses_o_agente_atende():
    """*"Regina falou há 3 meses, segurado volta hoje"* → **responde**, e o
    prompt manda tratar como ASSUNTO NOVO."""
    linhas = [_humana(92), _segurado(0)]
    calar, motivo = _porta(linhas, n_dias=N)
    assert calar is False, motivo
    assert motivo == ""

    bloco = F.contexto_do_reencontro(linhas, agora=AGORA, n_dias=N)
    assert "ASSUNTO NOVO" in bloco
    assert "3 meses" in bloco
    assert "MEMÓRIA" in bloco


def test_3_agente_desligado_e_religado_nao_ha_palavra_humana():
    """*"agente começou 09/09, foi desligado, religado 13/09"* → **responde**.

    ⚠️ A conversa é inteira do robô: `assistant` sem payload, mais o eco
    espelhado de cada balão. Nenhuma delas é palavra humana."""
    fala = "Bom dia! Em que posso ajudar?"
    linhas = [_segurado(4), _agente(4, fala),
              # o eco do WhatsApp, segundos depois, marcado como espelho
              _msg("assistant", origem="espelho", texto="Bom dia!",
                   quando=AGORA - timedelta(days=4) + timedelta(seconds=6)),
              _segurado(0)]
    calar, motivo = _porta(linhas, n_dias=N)
    assert calar is False, motivo


def test_4_segurado_volta_13_dias_depois_numa_conversa_so_do_agente():
    """*"agente atendeu 09/09, segurado volta 22/09"* → **responde**, sem
    confundir a janela do handoff com a janela do assunto."""
    linhas = [_segurado(13), _agente(13), _segurado(0)]
    calar, motivo = _porta(linhas, n_dias=N)
    assert calar is False, motivo
    # E o prompt sabe que é assunto novo — 13 > 7.
    assert "ASSUNTO NOVO" in F.contexto_do_reencontro(linhas, agora=AGORA, n_dias=N)


def test_5_o_prazo_conta_da_ULTIMA_mensagem_dela_nao_da_primeira():
    """*"cala por N dias contados da última mensagem dela, renovado a cada"*.

    🔴 O caso decisivo: ela falou **há 9 dias** (fora da janela) e **há 2**
    (dentro). Um motor que olhasse a PRIMEIRA responderia — e falaria por cima
    de um sinistro que ela está conduzindo.
    """
    linhas = [_agente(10), _humana(9), _segurado(5), _humana(2), _segurado(0)]
    calar, motivo = _porta(linhas, n_dias=N)
    assert calar is True
    assert "há 2 dias" in motivo, motivo
    # 🔴 E a DATA é a prova aritmética de qual das duas mensagens contou:
    #    a de 07/09 vence em 14/09; a de 31/08 teria vencido em 07/09.
    assert "14/09" in motivo, motivo


def test_6_nota_nao_e_palavra_humana():
    """*"Regina anota sem assumir"* → `#nota` **não** cala o robô.

    ⛔ As duas marcas, porque as duas existem no acervo: o painel grava
    `payload.nota_interna` E prefixa o `content`; o espelho só tem o prefixo.
    """
    so_painel = [_humana(1, origem="dashboard", texto="#nota conferir a placa",
                         nota=True), _segurado(0)]
    so_prefixo = [_humana(1, origem="espelho", texto="#nota conferir a placa"),
                  _segurado(0)]
    for linhas in (so_painel, so_prefixo):
        calar, motivo = _porta(linhas, n_dias=N)
        assert calar is False, motivo

    # 🔴 A LINHA DE CONTROLE da estreiteza: `"o robô errou #nota"` NÃO é nota —
    #    é intervenção, e cala. Sem este par, uma regra que ignorasse toda
    #    mensagem com `#nota` em qualquer posição passaria.
    calar, _ = _porta([_humana(1, texto="o robô errou #nota"), _segurado(0)],
                      n_dias=N)
    assert calar is True


def test_7_reivindicada_cala_independentemente_de_N():
    """*"reivindicada só volta pelo botão Devolver ao agente"*.

    🔴 E cala **mesmo com N = 0**, isto é, mesmo com a regra da janela
    desligada: são duas razões independentes, e confundi-las seria dar à env o
    poder de desfazer o "Assumir" da atendente.
    """
    dona = _conversa(claimed_by="user-77", claimed_by_name="Regina")
    for n in (N, 0):
        calar, motivo = _porta([_segurado(0)], conversa=dona, n_dias=n)
        assert calar is True
        assert "Regina" in motivo and "Devolver ao agente" in motivo

    pediu = _conversa(status=F.HUMAN_REQUESTED)
    calar, motivo = _porta([_segurado(0)], conversa=pediu, n_dias=0)
    assert calar is True
    assert "pediu para falar com uma pessoa" in motivo


def test_CONTROLE_sem_palavra_humana_nenhuma_o_agente_responde():
    """🔴 A LINHA DE CONTROLE (§9.2). O MESMO dublê, as mesmas conversas, sem a
    mensagem da atendente — e a resposta muda. É ela que dá direito a creditar
    o silêncio dos casos acima à palavra humana, e a mais nada."""
    calar, motivo = _porta([_agente(3), _segurado(3), _segurado(0)], n_dias=N)
    assert calar is False, motivo
    assert motivo == ""


# ===========================================================================
# 2. AS MUTAÇÕES — cada uma tem de ficar VERMELHA
# ===========================================================================

CENARIO_DA_REGINA = [_agente(4), _humana(3), _segurado(0)]
CENARIO_DOS_3_MESES = [_humana(92), _segurado(0)]


def test_as_mutacoes_ficam_vermelhas():
    """⛔ Sem isto o arquivo inteiro é carimbo (`CLAUDE.md` §9.3).

    Cada linha abaixo é o comportamento de um defeito plausível, e o `assert`
    afirma que o defeito **muda a resposta** — se não mudasse, o caso verde
    correspondente estaria passando por acaso.
    """
    # (a) N = 0 — a regra desligada. O cenário 1 deixa de calar.
    assert _porta(CENARIO_DA_REGINA, n_dias=0)[0] is False

    # (b) N = infinito — a janela que nunca vence. O cenário 2 deixa de atender.
    assert _porta(CENARIO_DOS_3_MESES, n_dias=10 ** 6)[0] is True

    # (c) `origem='dashboard'` ignorada — a atendente do PAINEL vira invisível.
    do_painel = [_humana(1, origem="dashboard", texto="já estou vendo, Sr. João"),
                 _segurado(0)]
    assert _porta(do_painel, n_dias=N)[0] is True
    origens = F.ORIGENS_HUMANAS
    try:
        F.ORIGENS_HUMANAS = ("espelho",)          # a mutação
        assert _porta(do_painel, n_dias=N)[0] is False, (
            "com 'dashboard' fora da lista o motor TEM de deixar de calar — "
            "se não deixa, o caso do painel estava verde por acaso")
    finally:
        F.ORIGENS_HUMANAS = origens

    # (d) `#nota` contada como palavra humana — anotar voltaria a ser assumir.
    nota = [_humana(1, texto="#nota conferir a placa"), _segurado(0)]
    assert _porta(nota, n_dias=N)[0] is False
    original = F.e_anotacao
    try:
        F.e_anotacao = lambda m: False            # a mutação
        assert _porta(nota, n_dias=N)[0] is True, (
            "sem a regra do `#nota` a anotação TEM de calar o robô — se não "
            "cala, o caso 6 estava verde por acaso")
    finally:
        F.e_anotacao = original

    # (e) o eco do próprio agente contado como humano — o robô se calaria para
    #     sempre depois da PRIMEIRA resposta. 📊 É o defeito que
    #     `whatsapp/voz_propria.py` documenta desde 14/08.
    fala = "Bom dia! Em que posso ajudar?"
    com_eco = [_agente(1, fala),
               _msg("assistant", origem="espelho", texto="Bom dia!",
                    quando=AGORA - timedelta(days=1) + timedelta(seconds=6)),
               _segurado(0)]
    assert _porta(com_eco, n_dias=N)[0] is False
    original = F.e_eco_do_agente
    try:
        F.e_eco_do_agente = lambda m, f: False    # a mutação
        assert _porta(com_eco, n_dias=N)[0] is True, (
            "sem o reconhecimento do eco o agente TEM de se calar sozinho — "
            "se não se cala, o cenário 3 estava verde por acaso")
    finally:
        F.e_eco_do_agente = original


def test_o_eco_exige_as_DUAS_condicoes():
    """🔴 O par que prova que nem (A) nem (B) sozinha bastaria.

    ⚠️ A atendente que digita, meia hora depois, uma frase que por acaso está
    contida na fala do robô **não** é eco. E a que responde em 40 segundos
    com texto próprio — a corrida C'' do plano — também não é.
    """
    fala = "Bom dia! Em que posso ajudar?"
    base = _agente(1, fala)

    # (A) sem (B): mesmo texto, meia hora depois → é PESSOA, e cala.
    tarde = [base, _msg("assistant", origem="espelho", texto="Bom dia!",
                        quando=AGORA - timedelta(days=1) + timedelta(minutes=30)),
             _segurado(0)]
    assert _porta(tarde, n_dias=N)[0] is True

    # (B) sem (A): 40 segundos depois, texto que o robô não disse → PESSOA.
    rapida = [base, _msg("assistant", origem="espelho",
                         texto="deixa comigo, eu assumo",
                         quando=AGORA - timedelta(days=1) + timedelta(seconds=40)),
              _segurado(0)]
    assert _porta(rapida, n_dias=N)[0] is True


# ===========================================================================
# 3. N — env, override por corretora, e o que NÃO pode desligar a regra
# ===========================================================================

def test_o_N_vem_do_default_da_env_e_do_perfil_da_corretora(monkeypatch):
    monkeypatch.delenv(F._ENV_DA_JANELA, raising=False)
    assert F.janela_de_silencio_dias() == 7          # 📊 o default do Founder
    assert F.janela_de_silencio_dias({}) == 7

    monkeypatch.setenv(F._ENV_DA_JANELA, "15")
    assert F.janela_de_silencio_dias() == 15
    # 🔴 O override da corretora VENCE a env.
    assert F.janela_de_silencio_dias(
        {"acionamento_profile": {"janela_silencio_humano_dias": 3}}) == 3
    # `0` é legítimo: desliga a regra nesta corretora.
    assert F.janela_de_silencio_dias(
        {"acionamento_profile": {"janela_silencio_humano_dias": 0}}) == 0
    # O painel pode gravar `7.0`.
    assert F.janela_de_silencio_dias(
        {"acionamento_profile": {"janela_silencio_humano_dias": "7.0"}}) == 7

    # ⛔ E o que NÃO pode acontecer: um typo DESLIGAR a proteção em silêncio.
    for lixo in ("", "sete", None, -1, True, {"a": 1}):
        assert F.janela_de_silencio_dias(
            {"acionamento_profile": {"janela_silencio_humano_dias": lixo}}) == 15, lixo


def test_o_perfil_da_corretora_chega_ao_motor():
    """🔴 O §9.4: o que se afirma é o comportamento do MOTOR sobre o perfil
    real, não o da função de leitura isolada."""
    perfil_curto = {"acionamento_profile": {"janela_silencio_humano_dias": 1}}
    perfil_longo = {"acionamento_profile": {"janela_silencio_humano_dias": 30}}
    # A Regina falou há 3 dias: com N=1 já venceu; com N=30, não.
    assert _porta(CENARIO_DA_REGINA, companhia=perfil_curto)[0] is False
    assert _porta(CENARIO_DA_REGINA, companhia=perfil_longo)[0] is True


# ===========================================================================
# 4. FAIL-CLOSED — a dúvida cala
# ===========================================================================

def test_falha_de_leitura_cala():
    """⛔ Banco fora do ar → o agente **não** fala. Mesma direção do
    `voz_propria` e do `pode_falar_com_o_cliente`."""
    calar, motivo = _porta([_segurado(0)], n_dias=N, quebrar=True)
    assert calar is True
    assert "não consegui ler o histórico" in motivo
    # 🔴 CONTROLE: o MESMO dublê, sem quebrar, responde — a recusa veio da
    #    falha de leitura e de mais nada.
    assert _porta([_segurado(0)], n_dias=N, quebrar=False)[0] is False


def test_sem_corretora_o_agente_nao_fala():
    calar, motivo = asyncio.run(F.a_ia_deve_calar(
        _DB(), company_id="", conversa=_conversa(), agora=AGORA, n_dias=N))
    assert calar is True
    assert "sem corretora" in motivo


def test_uma_conversa_encerrada_nao_fica_calada_para_sempre():
    """⚠️ `pausar_ia` já decide isto (a pausa é do atendimento VIVO) e este
    motor não pode desfazer: com `resolvido_em`, o dono de setembro não pode
    calar o robô em dezembro."""
    velha = _conversa(claimed_by="user-77", claimed_by_name="Regina",
                      resolvido_em="2026-06-01T10:00:00+00:00")
    calar, _ = _porta([_segurado(0)], conversa=velha, n_dias=N)
    assert calar is False


# ===========================================================================
# 5. ASSUNTO NOVO e RELIGAMENTO — o bloco do prompt
# ===========================================================================

def test_o_religamento_nao_cumprimenta_como_inicio():
    """📊 09/09/2026: *"bom dia, é bom começar o dia com você"* na 30ª mensagem
    de um sinistro com vítima. O bloco existe para essa linha não nascer."""
    linhas = [_segurado(0, "e aí, saiu o guincho?"),
              _msg("assistant", texto="Já pedi o guincho, aguarde.",
                   quando=AGORA - timedelta(hours=2))]
    bloco = F.contexto_do_reencontro(linhas, agora=AGORA, n_dias=N)
    assert "EM ANDAMENTO" in bloco
    assert "NÃO cumprimente" in bloco
    assert "2 horas" in bloco
    # ⛔ E NÃO é assunto novo: 2 horas < 7 dias.
    assert "ASSUNTO NOVO" not in bloco


def test_a_mensagem_que_acabou_de_chegar_nao_conta_como_reencontro():
    """🔴 `webhook.py` grava o que o segurado escreveu ANTES de montar o prompt.

    Sem a folga do turno, "a última mensagem da conversa" seria sempre a
    própria — e o assunto novo nunca seria visto. Este é o caso que fica
    vermelho se alguém tirar `_TURNO_SEGUNDOS`.
    """
    linhas = [_humana(92), _msg("user", texto="oi, tudo bem?", quando=AGORA)]
    assert "ASSUNTO NOVO" in F.contexto_do_reencontro(linhas, agora=AGORA, n_dias=N)


def test_no_meio_de_um_atendimento_normal_o_bloco_e_vazio():
    """⚠️ `""` é a resposta mais comum, e é a certa: token a mais em todo turno
    compete com o que importa. **A LINHA DE CONTROLE dos dois casos acima.**"""
    linhas = [_msg("user", texto="ABC1234",
                   quando=AGORA - timedelta(minutes=5)),
              _msg("user", texto="e agora?", quando=AGORA)]
    assert F.contexto_do_reencontro(linhas, agora=AGORA, n_dias=N) == ""
    # Conversa sem nada antes do turno: também vazio.
    assert F.contexto_do_reencontro([_msg("user", texto="oi", quando=AGORA)],
                                    agora=AGORA, n_dias=N) == ""
    assert F.contexto_do_reencontro([], agora=AGORA, n_dias=N) == ""


def test_o_bloco_do_reencontro_resolve_a_conversa_pela_sessao_com_a_corretora():
    """🔴 §7: a conversa é achada por `company_id` + `session_id`, nunca só pelo
    `session_id` — o backend usa service role e atravessa a RLS inteira."""
    bloco = asyncio.run(F.bloco_do_reencontro(
        _DB(CENARIO_DOS_3_MESES), company_id=EMPRESA, session_id="sessao-x",
        agora=AGORA, n_dias=N))
    assert "ASSUNTO NOVO" in bloco
    # Sem corretora não há bloco — e não há consulta.
    assert asyncio.run(F.bloco_do_reencontro(
        _DB(CENARIO_DOS_3_MESES), company_id="", session_id="sessao-x",
        agora=AGORA, n_dias=N)) == ""
    # ⚠️ Banco fora do ar aqui NÃO cala ninguém: o pior caso é o agente falar
    #    sem a dica, que é o comportamento de antes de 09/09.
    assert asyncio.run(F.bloco_do_reencontro(
        _DB(CENARIO_DOS_3_MESES, quebrar=True), company_id=EMPRESA,
        session_id="sessao-x", agora=AGORA, n_dias=N)) == ""


def test_o_motor_atravessa_o_cliente_SINCRONO_do_graph():
    """🔴 O guarda do `_executar`, e ele nasceu de um defeito medido.

    📊 Os serviços recebem o `AsyncSupabaseClient` e escrevem `await
    …execute()`; o `graph.py` recebe o cliente SÍNCRONO. Um `await` sobre a
    resposta síncrona levanta `TypeError`, o `except` do chamador engole, e o
    bloco **nunca aparece no prompt** sem nada ficar vermelho (§9.1).
    """
    class _TabelaSincrona(_Tabela):
        def execute(self):                     # devolve dado CRU, não awaitable
            return type("R", (), {"data": _Tabela.execute(self).data})()

    class _ClienteSincrono:
        def __init__(self, linhas):
            self.linhas = linhas

        def table(self, nome):
            return _TabelaSincrona(nome, self.linhas, False)

    # ⚠️ E sem o wrapper `.client`: `graph.py` passa as duas formas.
    bloco = asyncio.run(F.bloco_do_reencontro(
        _ClienteSincrono(CENARIO_DOS_3_MESES), company_id=EMPRESA,
        session_id="sessao-x", agora=AGORA, n_dias=N))
    assert "ASSUNTO NOVO" in bloco


# ===========================================================================
# 6. O MOTOR É UM SÓ — nenhuma segunda régua de janela (§5)
# ===========================================================================

def test_o_graph_chama_o_motor_e_nao_reimplementa_a_janela():
    """⛔ `CLAUDE.md` §5: consolidar antes de duplicar. O `graph.py` pode
    IMPORTAR `bloco_do_reencontro`; não pode ter régua própria."""
    texto = io.open(Path(__file__).resolve().parents[1] / "app" / "agents" /
                    "graph.py", encoding="utf-8").read()
    assert "bloco_do_reencontro" in texto
    assert "JANELA_SILENCIO_HUMANO_DIAS" not in texto
    assert "ORIGENS_HUMANAS" not in texto


def test_pausar_ia_continua_sendo_o_helper_unico_e_intocado():
    """⚠️ A regra nova SOMA — não substitui. `pausar_ia` segue puro e com as
    duas razões de sempre, porque `saudacao_do_religamento`, `chat.py`,
    `webhook.py` e `acompanhamento.py` dependem dela como está."""
    assert F.pausar_ia({"status": F.HUMAN_REQUESTED}) is True
    assert F.pausar_ia({"claimed_by": "user-77"}) is True
    assert F.pausar_ia({"claimed_by": "user-77",
                        "resolvido_em": "2026-06-01T10:00:00+00:00"}) is False
    assert F.pausar_ia({"status": "open"}) is False
    assert F.pausar_ia(None) is False


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(pytest.main([__file__, "-v"]))
