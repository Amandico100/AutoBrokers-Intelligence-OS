# -*- coding: utf-8 -*-
"""Duas decisões do Founder de 08/09/2026, com guarda que consegue ficar vermelho.

```
(A) as cartas do pós-acionamento são de TODAS as corretoras, não de duas
(B) o follow-up sai DEPOIS do horário combinado, e nunca fora de 08:00–19:00
```

🔴 **Por que cada asserção aqui pode falhar.** A lição do `CLAUDE.md` §9.3 é que
um guarda sem como falhar é carimbo. Então:

* a tabela de horários tem `18:59 → 18:59` **e** `19:00 → 08:00 do dia
  seguinte` — quem apagar a janela quebra a segunda; quem trocar `>=` por `>`
  quebra exatamente uma;
* o fuso de **Manaus** aparece com o MESMO instante UTC do caso de São Paulo, e
  responde diferente. Quem ignorar `AGENT_OS_TENANT_TIMEZONE` e voltar a
  escrever `America/Sao_Paulo` no código faz este caso ficar vermelho;
* o guarda das 22h é medido chamando **`pode_falar_com_o_cliente`**, não a
  função de janela — é o §9.4 aplicado: o que se afirma é o comportamento do
  MOTOR, não do regex que ele por acaso usa. Um dublê de banco que diria "pode"
  em tudo prova que a recusa veio da hora, e o caso das 10h prova que o dublê
  **consegue** dizer "pode".

⛔ NENHUMA mensagem sai (o canal nem chega a ser importado: a porta recusa
antes). NENHUM banco real é tocado. Zero PII.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.atendimento import acompanhamento as A  # noqa: E402

SP = "America/Sao_Paulo"
MANAUS = "America/Manaus"


def _utc(ano, mes, dia, hora, minuto=0):
    return datetime(ano, mes, dia, hora, minuto, tzinfo=timezone.utc)


def _local(tz_nome, ano, mes, dia, hora, minuto=0):
    return datetime(ano, mes, dia, hora, minuto,
                    tzinfo=A.fuso_da_corretora(tz_nome))


def _em(quando, tz_nome):
    """O instante devolvido, lido no fuso da corretora — `(dia, hora, minuto)`."""
    local = quando.astimezone(A.fuso_da_corretora(tz_nome))
    return (local.day, local.hour, local.minute)


# ===========================================================================
# (B1) A função PURA — a tabela de casos
# ===========================================================================

# 📊 `POS_ACIONAMENTO_ESPERA_MINUTOS=90` é o valor de produção em 08/09/2026.
ESPERA = 90

TABELA = [
    # (nome, combinado_local|None, agora_local, tz, dia/hora/min esperados)
    ("protocolo às 17h, sem agendamento → 18:30 do mesmo dia",
     None, _local(SP, 2026, 9, 9, 17, 0), SP, (9, 18, 30)),
    ("protocolo às 18h → 19:30 é tarde demais → 08:00 do dia seguinte",
     None, _local(SP, 2026, 9, 9, 18, 0), SP, (10, 8, 0)),
    ("protocolo às 6h da manhã → a janela abre às 08:00 do mesmo dia",
     None, _local(SP, 2026, 9, 9, 6, 0), SP, (9, 8, 0)),
    ("agendado para as 10h → a pergunta sai 11:30, não às 10h",
     _local(SP, 2026, 9, 9, 10, 0), _local(SP, 2026, 9, 9, 8, 30), SP, (9, 11, 30)),
    ("período da TARDE combinado (base 18:00) → 08:00 do dia seguinte",
     _local(SP, 2026, 9, 9, 18, 0), _local(SP, 2026, 9, 9, 9, 0), SP, (10, 8, 0)),
    # 🔴 O caso que fica vermelho se alguém voltar a escrever o fuso no código:
    #    17:20 UTC é 14:20 em São Paulo e 13:20 em Manaus. Com +90 dá 15:50 e
    #    14:50 — dias iguais, HORAS diferentes.
    ("o mesmo instante UTC, lido em MANAUS, dá uma hora a menos",
     None, _utc(2026, 9, 9, 17, 20), MANAUS, (9, 14, 50)),
    ("e o MESMO instante em São Paulo dá 15:50 — o controle do caso acima",
     None, _utc(2026, 9, 9, 17, 20), SP, (9, 15, 50)),
]


@pytest.mark.parametrize("nome,combinado,agora,tz,esperado", TABELA,
                         ids=[c[0][:40] for c in TABELA])
def test_a_tabela_do_horario_do_follow_up(nome, combinado, agora, tz, esperado):
    envio = A.calcular_envio_do_follow_up(agora, combinado, ESPERA, tz)
    assert _em(envio, tz) == esperado, nome


def test_a_borda_da_janela_consegue_separar_1859_de_1900():
    """🔴 A LINHA DE CONTROLE da janela (§9.2): um minuto muda a resposta.

    Sem este par, um `_empurrar_para_a_janela` que adiasse TUDO passaria — e um
    que não adiasse NADA também.
    """
    dentro = A.calcular_envio_do_follow_up(
        _local(SP, 2026, 9, 9, 17, 29), None, ESPERA, SP)
    fora = A.calcular_envio_do_follow_up(
        _local(SP, 2026, 9, 9, 17, 30), None, ESPERA, SP)
    assert _em(dentro, SP) == (9, 18, 59)
    assert _em(fora, SP) == (10, 8, 0)


def test_um_agendamento_no_passado_nao_nasce_vencido():
    """A seguradora responde tarde: a base já passou, e o envio é AGORA — nunca
    um instante anterior ao relógio, que faria o vigia disparar na hora."""
    agora = _local(SP, 2026, 9, 9, 15, 0)
    envio = A.calcular_envio_do_follow_up(
        agora, _local(SP, 2026, 9, 8, 9, 0), ESPERA, SP)
    assert envio >= agora.astimezone(timezone.utc)
    assert _em(envio, SP) == (9, 15, 0)


def test_o_fim_do_periodo_e_lido_do_formato_real_da_sessao():
    """📊 O formato real de `{day, periodo}` (`corridor_playbooks:9032-9040`):
    o dia vem com o nome da semana colado e o período vem por extenso."""
    fim = A.fim_do_periodo_combinado(
        {"day": "quinta-feira 20/08/2026", "periodo": "tarde das 13:00 as 18:00"}, SP)
    assert fim is not None
    assert (fim.astimezone(A.fuso_da_corretora(SP)).hour) == 18

    manha = A.fim_do_periodo_combinado(
        {"day": "20/08/2026", "periodo": "manha"}, SP)
    assert manha is not None and manha.astimezone(A.fuso_da_corretora(SP)).hour == 12

    # ⛔ RECUSA é resposta — e é o que impede o produto de inventar um horário.
    assert A.fim_do_periodo_combinado({"day": "amanhã", "periodo": "tarde"}, SP) is None
    assert A.fim_do_periodo_combinado({"day": "20/08/2026", "periodo": "assim que der"}, SP) is None
    assert A.fim_do_periodo_combinado({"day": "20/08/2026", "at": "14h"}, SP) is None
    assert A.fim_do_periodo_combinado(None, SP) is None


# ===========================================================================
# (B2) O GUARDA na hora de ENVIAR — dublê de banco que diz "pode" em tudo
# ===========================================================================


class _Res:
    def __init__(self, data):
        self.data = data

    def __await__(self):
        async def _eu():
            return self
        return _eu().__await__()


class _Tabela:
    """Dublê de PostgREST que responde SIM a tudo — de propósito.

    🔴 É isto que dá direito à conclusão: se a porta recusar, a recusa só pode
    ter vindo da HORA, porque todos os outros desligadores estão dizendo
    "pode". E o teste das 10h prova que o dublê consegue dizer "pode".
    """

    def __init__(self, nome):
        self.nome = nome

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self.nome == "companies":
            return _Res([{"id": "empresa-1", "agent_enabled": True,
                          "acionamento_profile": {"acompanhamento": True}}])
        if self.nome == "agents":
            return _Res([{"id": "a1", "is_active": True, "agent_role": "attendance"}])
        return _Res([])


class _Cliente:
    def table(self, nome):
        return _Tabela(nome)


class _DB:
    client = _Cliente()


class _Relogio:
    """Congela `datetime.now(timezone.utc)` DENTRO de `acompanhamento`.

    ⚠️ O guarda lê o relógio por conta própria (é a hora do ENVIO, não a do
    cálculo). Congelar aqui é o que torna "22h em São Paulo" um fato do teste.
    """

    def __init__(self, quando):
        self.quando = quando
        self.original = None

    def __enter__(self):
        self.original = A.dentro_da_janela_do_follow_up
        quando = self.quando
        A.dentro_da_janela_do_follow_up = (
            lambda agora_utc=None, tz=None: self.original(agora_utc or quando, tz))
        return self

    def __exit__(self, *a):
        A.dentro_da_janela_do_follow_up = self.original
        return False


def _porta(quando_utc, tz_nome):
    anterior = os.environ.get("AGENT_OS_TENANT_TIMEZONE")
    os.environ["AGENT_OS_TENANT_TIMEZONE"] = tz_nome
    try:
        with _Relogio(quando_utc):
            return asyncio.run(A.pode_falar_com_o_cliente(
                _DB(), "empresa-1", {"id": "c1", "status": "active"}))
    finally:
        if anterior is None:
            os.environ.pop("AGENT_OS_TENANT_TIMEZONE", None)
        else:
            os.environ["AGENT_OS_TENANT_TIMEZONE"] = anterior


def test_a_porta_cala_as_22h_locais():
    """01:00 UTC = 22:00 em São Paulo. ⛔ Nada sai."""
    pode, porque = _porta(_utc(2026, 9, 10, 1, 0), SP)
    assert pode is False
    assert porque == "fora_da_janela_local"


def test_a_porta_fala_as_10h_locais():
    """🔴 A LINHA DE CONTROLE do guarda: o MESMO dublê, outra hora, outra
    resposta. Sem ela, um dublê quebrado provaria a recusa por engano."""
    pode, porque = _porta(_utc(2026, 9, 9, 13, 0), SP)
    assert pode is True, porque
    assert porque == ""


def test_a_janela_e_lida_no_fuso_da_corretora():
    """19:30 UTC = 16:30 em São Paulo (fala) e 15:30 em Manaus (fala também);
    23:30 UTC = 20:30 em SP (cala) e 19:30 em Manaus (cala, 19h é o fecho)."""
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 19, 30), SP) is True
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 19, 30), MANAUS) is True
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 23, 30), SP) is False
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 23, 30), MANAUS) is False
    # 📊 22:30 UTC = 18:30 em Manaus (dentro) e 19:30 em SP (fora) — o par que
    #    prova que o fuso MUDA a resposta, e não só o rótulo do log.
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 22, 30), MANAUS) is True
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 22, 30), SP) is False


def test_um_nome_de_fuso_desconhecido_cai_em_menos_tres_e_NAO_e_erro(monkeypatch):
    """📊 O comportamento REAL de `platform_outbound.fuso_da_corretora:382-388`:
    nome inválido **não levanta** — ele cai em `UTC-3` (o contêiner sem tzdata
    é o caso que a linha existe para atender).

    ⚠️ Este teste afirma o que a função FAZ, não o que seria bonito ela fazer.
    Um teste que exigisse `False` aqui estaria guardando uma verdade que não
    existe, e ensinaria a ignorar teste (§9.3).
    """
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 13, 0),
                                           "Marte/Olympus_Mons") is True   # 10:00
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 10, 1, 0),
                                           "Marte/Olympus_Mons") is False  # 22:00


def test_a_janela_falha_FECHADA_quando_o_relogio_nao_responde(monkeypatch):
    """⛔ Não saber que horas são é razão para calar, nunca para mandar.

    🔴 E o par prova que o guarda CONSEGUE dizer `True`: mesma hora, mesma
    chamada, só o leitor de fuso quebrado.
    """
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 13, 0), SP) is True

    def _quebrado(_tz=None):
        raise RuntimeError("tzdata sumiu")

    monkeypatch.setattr(A, "fuso_da_corretora", _quebrado)
    assert A.dentro_da_janela_do_follow_up(_utc(2026, 9, 9, 13, 0), SP) is False


# ===========================================================================
# (B3) A LIGAÇÃO — o motor de verdade, não a função pura sozinha (§9.4)
# ===========================================================================


def _agendar(captured, tz_nome=SP, espera="90"):
    """Roda `_pos_acionamento_do_checkpoint` e devolve o `vence_em` gravado.

    🔴 É o MOTOR que se mede: a função pura já tem tabela própria acima. O que
    falta provar é que alguém a CHAMA — a lição do §9.4, cujo custo medido foi
    um agendamento com 72 asserções verdes que nunca chegava ao cliente.
    """
    import app.atendimento.acompanhamento as _A
    import app.services.dispatch_router as R
    import app.services.o_fim_do_atendimento as F

    gravado = {}

    async def _abrir(db, **kw):
        gravado.update(kw)

    async def _entregar(db, **kw):
        gravado["novidade"] = kw.get("texto")

    class _Vazia(_Tabela):
        def execute(self):
            return _Res([])

    class _ClienteVazio:
        def table(self, nome):
            return _Vazia(nome)

    class _DBVazio:
        client = _ClienteVazio()

    abrir_antes, entregar_antes = F.abrir_espera, _A.entregar_novidade
    tz_antes = os.environ.get("AGENT_OS_TENANT_TIMEZONE")
    espera_antes = os.environ.get("POS_ACIONAMENTO_ESPERA_MINUTOS")
    F.abrir_espera = _abrir
    _A.entregar_novidade = _entregar
    os.environ["AGENT_OS_TENANT_TIMEZONE"] = tz_nome
    if espera:
        os.environ["POS_ACIONAMENTO_ESPERA_MINUTOS"] = espera
    else:
        os.environ.pop("POS_ACIONAMENTO_ESPERA_MINUTOS", None)
    try:
        asyncio.run(R._pos_acionamento_do_checkpoint(
            _DBVazio(), "22222222-2222-2222-2222-222222222222",
            {"mirror_conversation_id": "11111111-1111-1111-1111-111111111111",
             "captured": captured}, "captured"))
    finally:
        F.abrir_espera, _A.entregar_novidade = abrir_antes, entregar_antes
        for chave, valor in (("AGENT_OS_TENANT_TIMEZONE", tz_antes),
                             ("POS_ACIONAMENTO_ESPERA_MINUTOS", espera_antes)):
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor
    return gravado


def test_a_espera_do_pos_acionamento_vence_no_HORARIO_DO_FOLLOW_UP():
    """⚠️ `vence_em` era o instante PROMETIDO — a espera vencia às 17h e o vigia
    perguntava "deu tudo certo?" no minuto em que o guincho encostava."""
    g = _agendar({"protocol": "5181",
                  "schedule": {"day": "09/09/2026", "at": "17h"}})
    assert g.get("scope") == "pos_acionamento"
    assert _em(datetime.fromisoformat(g["vence_em_iso"]), SP) == (9, 18, 30)


def test_a_hora_do_agendamento_nao_pode_sumir():
    """📊 08/09/2026: `'17h'.replace('h',':').strip(':')` era `'17'`, e `_DATA_BR`
    exige separador — a linha não casava e a espera nascia à MEIA-NOITE.

    ⚠️ A janela da Porto (`{from: '8 h'}`) perdia a hora em 100% dos casos:
    a âncora dela captura literalmente `(\\d{1,2}\\s?h)`.
    """
    from app.services.dispatch_router import _prazo_do_agendamento as P

    assert P({"schedule": {"day": "09/09/2026", "at": "17h"}}) == \
        "2026-09-09T20:00:00+00:00"
    assert P({"schedule": {"day": "09/09/2026", "from": "8 h", "to": "12 h"}}) == \
        "2026-09-09T11:00:00+00:00"
    # 🔴 O CONTROLE: o formato que já funcionava continua funcionando.
    assert P({"schedule": {"day": "09/09/2026", "at": "14:30"}}) == \
        "2026-09-09T17:30:00+00:00"


def test_as_48h_de_espera_da_seguradora_nao_se_somam_ao_agendamento():
    """🔴 O defeito medido em 08/09/2026, e ele acendeu o `[M1p]` da 097.1.

    ```
    combinado CONHECIDO    -> 45 min (90 em produção): "deu tudo certo?"
    combinado DESCONHECIDO -> 48 h  : "seguradora, cadê a resposta?"
    ```

    ⛔ Somar as 48 h a um agendamento das 14:00 pergunta **dois dias depois** do
    guincho — e, porque o DIA muda, o comparador anuncia ao segurado *"a
    seguradora atualizou a previsão"* sobre a mesma data.

    ⚠️ Sem `POS_ACIONAMENTO_ESPERA_MINUTOS` no ambiente, para que o padrão
    de cada uma apareça: é aí que os dois números se separam.
    """
    g = _agendar({"protocol": "5181",
                  "schedule": {"day": "12/09/2026", "at": "14:00"}}, espera="")
    assert _em(datetime.fromisoformat(g["vence_em_iso"]), SP) == (12, 14, 45)

    # 🔴 A LINHA DE CONTROLE: SEM agendamento, a espera longa continua de pé —
    #    é ela que impede o produto de cobrar a seguradora 45 min depois.
    sem = _agendar({"protocol": "5181"}, espera="")
    longe = datetime.fromisoformat(sem["vence_em_iso"])
    assert (longe - datetime.now(timezone.utc)).total_seconds() > 24 * 3600


def test_o_periodo_da_tarde_nao_vira_pergunta_de_manha():
    """📊 Para `{day, periodo}` o `_prazo_do_agendamento` devolve o dia à
    MEIA-NOITE. Usar isso como base perguntaria às 08:00 sobre um serviço da
    TARDE — a base honesta é o fim do período (18:00), e 18:00+90 vira 08:00 do
    dia SEGUINTE."""
    g = _agendar({"protocol": "5181",
                  "schedule": {"day": "quinta-feira 10/09/2026",
                               "periodo": "tarde das 13:00 as 18:00"}})
    assert _em(datetime.fromisoformat(g["vence_em_iso"]), SP) == (11, 8, 0)


def test_a_frase_ao_segurado_diz_a_previsao_da_SEGURADORA_nao_a_do_robo():
    """⛔ Depois desta SPEC `vence_em` é a hora em que o ROBÔ pergunta. Chamar
    isso de "previsão da seguradora" é o campo que mente da `CLAUDE.md` §12.1 —
    e ele mentiria por um DIA inteiro, porque 18h+90 cai no dia seguinte."""
    import app.services.dispatch_router as R

    fonte = R.__file__
    with open(fonte, encoding="utf-8") as fh:
        corpo = fh.read()
    trecho = corpo[corpo.find("async def _pos_acionamento_do_checkpoint"):]
    trecho = trecho[:trecho.find("async def _abrir_espera_do_travamento")]
    assert "_dia_e_mes(prometido or vence)" in trecho
    assert "_dia_e_mes(vence)\n" not in trecho


# ===========================================================================
# (A) As cartas globais — 6, e a 2ª rodada continua 6
# ===========================================================================


class _SeederFalso:
    """Dublê do acervo global: guarda um dicionário `document_id -> chunks`.

    🔴 Ele reproduz a REGRA do seeder de verdade (`_ingest_seed_sync`): apaga o
    `document_id` antes de inserir. É por isso que a segunda rodada substitui.
    ⚠️ E ele CONSEGUE duplicar — se o script passasse um `stem` com o relógio
    ou um contador dentro, o acervo teria 12 e o teste ficaria vermelho.
    """

    def __init__(self):
        self.acervo = {}
        self.rodadas = 0

    def __call__(self, stem, titulo, conteudo, digest):
        self.rodadas += 1
        doc_id = "seed-%s" % stem
        self.acervo.pop(doc_id, None)          # o delete do seeder
        self.acervo[doc_id] = {"titulo": titulo, "hash": digest, "chunks": 1}
        return 1


def _publicador():
    import importlib.util

    caminho = (Path(__file__).resolve().parents[1] / "scripts"
               / "publicar_cartas_0971.py")
    spec = importlib.util.spec_from_file_location("publicar_cartas_0971", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_o_global_publica_seis_e_a_segunda_rodada_continua_seis(monkeypatch, capsys):
    P = _publicador()
    seeder = _SeederFalso()

    import app.services.global_knowledge_seed as SEED
    monkeypatch.setattr(SEED, "_ingest_seed_sync", seeder)
    # ⛔ O banco não é tocado: a conferência do rótulo é um dublê que não fala.
    monkeypatch.setattr(P, "_conferir_a_corretora_global", lambda cliente: None)
    monkeypatch.setattr(P, "_empresa_global", lambda: "rotulo-de-teste")

    class _SB:
        client = object()

    monkeypatch.setattr("app.core.database.get_supabase_client", lambda: _SB())

    assert P.publicar_global() == 0
    assert len(seeder.acervo) == 6, sorted(seeder.acervo)
    assert seeder.rodadas == 6
    saida = capsys.readouterr().out
    assert "VERIFY: 6/6 cartas globais" in saida
    assert "FALTOU" not in saida

    # ---- a 2ª rodada: substitui, não soma ---------------------------------
    assert P.publicar_global() == 0
    assert len(seeder.acervo) == 6, "a 2ª rodada DUPLICOU o acervo global"
    assert seeder.rodadas == 12, "a 2ª rodada não republicou as 6"


def test_cada_carta_tem_um_stem_proprio_e_estavel():
    """🔴 O `document_id` é o que torna a rodada idempotente. Dois `stem` iguais
    fariam uma carta apagar a outra; um `stem` instável faria 6 virar 12."""
    P = _publicador()
    from app.atendimento.pos_acionamento import CARTAS

    stems = [P._stem(c) for c in CARTAS]
    assert len(set(stems)) == len(CARTAS) == 6, stems
    assert stems == [P._stem(c) for c in CARTAS], "o stem mudou entre duas leituras"
    assert all(s.startswith("pos-acionamento-") for s in stems)


def test_o_modo_por_tenant_avisa_que_a_decisao_e_global(capsys):
    """⚠️ Publicar por corretora deixou de ser o modo certo para estas cartas —
    e quem rodar o padrão precisa VER isso, não descobrir depois."""
    P = _publicador()
    assert P.plano() == 0
    saida = capsys.readouterr().out
    assert "GLOBAL" in saida and "--global" in saida


def test_o_global_escreve_na_colecao_que_o_runtime_le():
    """🔴 O achado que decidiu o desenho: `search_service` NÃO lê
    `company_<GLOBAL_KNOWLEDGE_COMPANY_ID>` — só `autobrokers_global`.

    Este guarda fica vermelho se alguém trocar o trilho do `--global` de volta
    para `documents`, que daria um `VERIFY` verde e zero leitura no runtime.
    """
    fonte = (Path(__file__).resolve().parents[1] / "scripts"
             / "publicar_cartas_0971.py").read_text(encoding="utf-8")
    corpo = fonte[fonte.find("def publicar_global"):fonte.find("def plano(")]
    assert "_ingest_seed_sync" in corpo
    assert '"documents"' not in corpo and "'documents'" not in corpo

    from app.services.knowledge_scope import (GLOBAL_COLLECTION,
                                              NAMESPACE_CANON, ORCAMENTO_GLOBAL)

    assert GLOBAL_COLLECTION == "autobrokers_global"
    # ⚠️ Namespace fora do orçamento não é filtrado errado: ele simplesmente não
    #    é PROCURADO. As cartas entram como `canon` (é o que o seeder grava).
    assert any(NAMESPACE_CANON in faixa for _r, faixa, _c in ORCAMENTO_GLOBAL)
