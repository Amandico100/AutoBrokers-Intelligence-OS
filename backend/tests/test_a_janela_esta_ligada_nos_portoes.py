# -*- coding: utf-8 -*-
"""A janela da palavra humana está LIGADA nos portões — não só escrita.

> **O TESTE DO PRODUTO:** *"A Regina respondeu este segurado anteontem, pelo
> celular dela. Ele volta hoje. O robô não responde — nem na entrada, nem
> depois de já ter escrito a resposta."*

🔴 **POR QUE ESTE ARQUIVO EXISTE, e ele é o §9.4 do `CLAUDE.md` em pessoa.**

`a_ia_deve_calar` nasceu em 09/09/2026 com sete cenários verdes em
`test_a_ultima_palavra_humana_manda.py` — e **nenhum chamador**. Uma regra sem
chamador é uma regra que não roda: exatamente o agendamento com 72 asserções
verdes que nunca chegava ao cliente. Lá se prova que o motor DECIDE certo; aqui
se prova que alguém o **CONSULTA**, e que o veredito dele **manda**.

```
① entrada do webhook   a mensagem do segurado chega e a IA não é acionada
② saída do webhook     ela falou enquanto o modelo escrevia → resposta DESCARTADA
③ follow-up            o "deu tudo certo?" automático não sai por cima dela
```

⚠️ **AS LINHAS DE CONTROLE** (§9.2), porque sem elas um dublê quebrado provaria
o silêncio por engano:

```
conversa SEM palavra humana        → o segurado É respondido
N = 0 (a regra desligada)          → o segurado É respondido
o motor neutralizado               → a mensagem PASSA (logo é ele quem segura)
```

📊 **E os dublês não são novos** (`CLAUDE.md` §5): o banco, o Redis, o envio e o
carregador do `webhook.py` vêm de `test_a_atendente_fala_e_o_robo_cala.py`, que
já roda `process_whatsapp_message_background` de verdade. Um segundo dublê de
PostgREST ao lado daquele seria motor paralelo — e o dia em que os dois
discordassem seria o dia em que o guarda mentiria.

⛔ Sem rede, sem banco, sem Redis, sem mensagem enviada. Zero PII: telefones
sintéticos e nome de papel ("a atendente").
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

# 🔴 O harness do webhook, reusado inteiro — dublês, carregador e tudo.
import test_a_atendente_fala_e_o_robo_cala as H  # noqa: E402

EMPRESA = H.EMPRESA
TELEFONE = H.TELEFONE
CONVERSA = "real"

_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print("  OK  %s%s" % (o_que, ("  (%s)" % evidencia) if evidencia else ""))
    else:
        print("  X   %s%s" % (o_que, ("  (%s)" % evidencia) if evidencia else ""))
        _PROBLEMAS.append(o_que)


def par(acusou: bool, o_que: str, evidencia: str = "") -> None:
    """A linha de CONTROLE: `acusou=True` quando o guarda CONSEGUIU ficar
    vermelho. Um guarda que não consegue falhar não guarda nada (§9.3)."""
    checar(acusou, "CONTROLE — " + o_que, evidencia)


# ===========================================================================
# O RELÓGIO — sempre relativo ao AGORA, nunca uma data cravada
# ===========================================================================
#
# ⚠️ Cravar `2026-09-09` faria este arquivo mudar de cor sozinho amanhã. A
# janela é uma diferença de dias, e é assim que ela se mede.

def _ha(dias: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()


def _fala_da_atendente(texto: str, *, dias_atras: float = 2.0) -> dict:
    """A linha REAL que o espelho grava quando ela responde pelo celular:
    `role='assistant'` + `payload.origem='espelho'` (`espelho_chat.py:610`).
    ⛔ `claimed_by` continua VAZIO — ela não clicou em botão nenhum, e é isso
    que só a janela enxerga."""
    return {"conversation_id": CONVERSA, "role": "assistant", "content": texto,
            "created_at": _ha(dias_atras), "payload": {"origem": "espelho"}}


# ===========================================================================
# ① e ② OS PORTÕES DO WEBHOOK — o pipeline de verdade
# ===========================================================================

def _rodar_o_turno(*, mensagens=(), durante_o_turno=None) -> dict:
    """Roda `process_whatsapp_message_background` de verdade.

    Devolve `{"enviados": [...], "atividades": [...]}`. 🔴 O que se mede é o
    que o segurado RECEBEU — não o que alguma função devolveu.
    """
    w = H.motor()
    H.agente_ligado(True)
    b = H.zerar_banco()
    H.semear_as_duas_conversas(b)
    if mensagens:
        b.semear("messages", list(mensagens))

    # 🔴 O QUE SE TROCA NO MÓDULO, SE DEVOLVE. 📊 Medido em 09/09/2026: deixar
    #    `integration_service` como dublê aqui derrubava
    #    `test_098_builder_b_unit::test_r9` quando os dois rodavam no MESMO
    #    processo (`AttributeError: ... has no attribute
    #    'get_whatsapp_integration'`). Um guarda que quebra o vizinho é um
    #    guarda que ensina a rodar a suíte em pedaços.
    guardado = {nome: getattr(w, nome, None) for nome in
                ("whatsapp_service", "integration_service", "LangChainService",
                 "get_or_create_conversation")}

    envio = H.EnvioFalso()
    w.whatsapp_service = envio
    w.integration_service = H.ServicoDeIntegracaoFalso(H.integracao())

    import app.services.billing_gate as _porteira
    import app.services.billing_replies as _cobranca
    import app.services.platform_outbound as _plataforma

    _porteira.pode_consumir = lambda *_a, **_k: (True, "ok")

    async def _sem_nota(*_a, **_k):
        return None

    _cobranca.contexto_de_cobranca = _sem_nota
    _cobranca.telefones_da_equipe_de_cobranca = _sem_nota
    _plataforma.context_note_for = _sem_nota

    class _LangChainFalso:
        def __init__(self, *_a, **_k):
            pass

        async def process_message(self, *_a, **_k):
            # 📊 8 a 25 segundos, medidos. É a janela em que ela responde pelo
            #    celular e o portão da ENTRADA já perguntou.
            if durante_o_turno is not None:
                durante_o_turno(b)
            return "Claro! Vou verificar sua apolice agora mesmo.", {}

    w.LangChainService = _LangChainFalso
    w.get_or_create_conversation = _conversa_fixa

    try:
        asyncio.run(w.process_whatsapp_message_background({
            "connectedPhone": "554800000000", "phone": TELEFONE, "isGroup": False,
            "fromMe": False, "text": {"message": "Oi, e sobre o guincho de ontem"},
            "messageId": "WAMSG-IN-1", "senderName": "Segurado",
            "_integration_id": "int-1",
        }))
    finally:
        for nome, valor in guardado.items():
            if valor is None:
                if hasattr(w, nome):
                    delattr(w, nome)
            else:
                setattr(w, nome, valor)
    return {"enviados": envio.enviados, "atividades": b.linhas("agent_activities")}


async def _conversa_fixa(**_k) -> str:
    return CONVERSA


def teste_a_entrada_nao_aciona_a_ia_quando_a_atendente_falou():
    print("\n[1] ENTRADA — ela falou há 2 dias; o segurado volta e a IA não fala")
    _esquecer_o_feed()
    r = _rodar_o_turno(mensagens=[_fala_da_atendente(
        "Ja acionei o guincho para voce, qualquer coisa me chama")])
    checar(not r["enviados"],
           "NADA foi enviado ao segurado",
           "a palavra dela vale por %s dias" % _n_dias())

    # A Regina precisa VER que o robô calou — uma linha, no feed que já existe.
    linhas = [l for l in r["atividades"] if "silêncio" in str(l.get("title") or "")]
    checar(len(linhas) == 1,
           "o silêncio virou UMA linha em `agent_activities` (sem tabela nova)",
           "%d linha(s)" % len(linhas))

    # E ela não se repete a cada mensagem: o segurado insiste, o feed não incha.
    r2 = _rodar_o_turno(mensagens=[_fala_da_atendente(
        "Ja acionei o guincho para voce, qualquer coisa me chama")])
    repetidas = [l for l in r2["atividades"] if "silêncio" in str(l.get("title") or "")]
    checar(not repetidas,
           "e a SEGUNDA mensagem do mesmo dia não escreve outra linha",
           "uma por conversa por dia")


def teste_o_CONTROLE_da_entrada_conversa_sem_palavra_humana():
    print("\n[1c] CONTROLE — a MESMA conversa, sem palavra humana nenhuma")
    _esquecer_o_feed()
    r = _rodar_o_turno()
    par(len(r["enviados"]) == 1,
        "sem palavra humana o segurado É respondido",
        "%d envio(s) — o pipeline consegue falar" % len(r["enviados"]))


def teste_a_saida_descarta_quando_ela_fala_durante_o_turno():
    print("\n[2] SAÍDA — ela escreve enquanto o modelo escreve: resposta descartada")
    _esquecer_o_feed()

    def _ela_fala_agora(b):
        # ⚠️ Texto DIFERENTE do que o robô ia dizer, de propósito: se fosse o
        #    mesmo, `e_eco_do_agente` o trataria como eco do próprio produto —
        #    e o guarda ficaria verde pela razão errada.
        b.semear("messages", [_fala_da_atendente(
            "Oi! Sou eu, ja estou vendo isso para voce", dias_atras=0.0)])

    r = _rodar_o_turno(durante_o_turno=_ela_fala_agora)
    checar(not r["enviados"],
           "a resposta pronta NÃO chega ao segurado",
           "o portão da entrada perguntou antes de ela escrever")


def teste_o_CONTROLE_do_N_zero_desliga_a_regra():
    print("\n[1d] CONTROLE — `JANELA_SILENCIO_HUMANO_DIAS=0` desliga a regra")
    _esquecer_o_feed()
    antes = os.environ.get("JANELA_SILENCIO_HUMANO_DIAS")
    os.environ["JANELA_SILENCIO_HUMANO_DIAS"] = "0"
    try:
        r = _rodar_o_turno(mensagens=[_fala_da_atendente("Ja acionei o guincho")])
    finally:
        if antes is None:
            os.environ.pop("JANELA_SILENCIO_HUMANO_DIAS", None)
        else:
            os.environ["JANELA_SILENCIO_HUMANO_DIAS"] = antes
    par(len(r["enviados"]) == 1,
        "com N=0 a MESMA conversa volta a ser respondida",
        "desligado é desligado — e é o que prova que era a janela")


def teste_o_CONTROLE_do_motor_neutralizado():
    print("\n[1e] CONTROLE — com o motor neutralizado, a mensagem PASSA")
    _esquecer_o_feed()
    import app.services.o_fim_do_atendimento as F

    original = F.a_ia_deve_calar

    async def _nunca_cala(*_a, **_k):
        return False, ""

    F.a_ia_deve_calar = _nunca_cala
    try:
        r = _rodar_o_turno(mensagens=[_fala_da_atendente("Ja acionei o guincho")])
    finally:
        F.a_ia_deve_calar = original
    par(len(r["enviados"]) == 1,
        "é `a_ia_deve_calar` quem segura a resposta — nada mais",
        "trocado o motor, o mesmo cenário fala")


# ===========================================================================
# ③ O FOLLOW-UP — a porta do pós-acionamento
# ===========================================================================
#
# ⚠️ `pode_falar_com_o_cliente` fala com o cliente ENQUANTO SÓ O PRODUTO está
# olhando: é a saída que mais precisa da janela, e a única que ninguém vê
# acontecer.

class _RespostaAsync:
    """A resposta do `AsyncSupabaseClient`: tem `.data` **e** é aguardável."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        async def _eu():
            return self

        return _eu().__await__()


class _ConsultaAsync:
    """O MESMO PostgREST de mentira do harness (filtra, ordena e limita de
    verdade) — só que aguardável. ⛔ Reescrever o filtro aqui seria um segundo
    motor, e o dia em que os dois discordassem seria o dia da mentira."""

    def __init__(self, consulta):
        self._c = consulta

    def __getattr__(self, nome):
        alvo = getattr(self._c, nome)

        def _envolver(*a, **k):
            saida = alvo(*a, **k)
            return self if saida is self._c else saida

        return _envolver

    def execute(self):
        return _RespostaAsync(self._c.execute().data)


class BancoAsync:
    def __init__(self, banco):
        self._b = banco
        self.client = self

    def table(self, nome):
        return _ConsultaAsync(self._b.table(nome))


def _mundo_do_follow_up(*, com_palavra_humana: bool):
    b = H.zerar_banco()
    H.semear_as_duas_conversas(b)
    b.semear("companies", [{"id": EMPRESA, "agent_enabled": True,
                            "acionamento_profile": {"acompanhamento": True}}])
    b.semear("agents", [{"id": "a1", "company_id": EMPRESA,
                         "is_active": True, "agent_role": "attendance"}])
    if com_palavra_humana:
        b.semear("messages", [_fala_da_atendente("Ja falei com a seguradora")])
    return b


def _porta(banco):
    """Chama `pode_falar_com_o_cliente` de verdade, com a HORA liberada.

    ⚠️ A hora local tem guarda próprio (`test_o_follow_up_respeita_o_horario…`)
    e é o PRIMEIRO desligador: sem liberá-la, este arquivo mediria o relógio da
    máquina em vez da janela.
    """
    from app.atendimento import acompanhamento as A

    antes = A.dentro_da_janela_do_follow_up
    A.dentro_da_janela_do_follow_up = lambda *_a, **_k: True
    try:
        return asyncio.run(A.pode_falar_com_o_cliente(
            BancoAsync(banco), EMPRESA,
            {"id": CONVERSA, "status": "open", "user_phone": TELEFONE}))
    finally:
        A.dentro_da_janela_do_follow_up = antes


def teste_o_follow_up_nao_fala_por_cima_da_atendente():
    print("\n[3] FOLLOW-UP — o 'deu tudo certo?' não sai por cima dela")
    _esquecer_o_feed()
    H.motor()  # garante o mundo dublado carregado

    pode, porque = _porta(_mundo_do_follow_up(com_palavra_humana=True))
    checar(pode is False and porque == "palavra_humana_recente",
           "a porta RECUSA, e o `suprimida_por` diz a razão certa",
           "(%r, %r)" % (pode, porque))

    pode2, porque2 = _porta(_mundo_do_follow_up(com_palavra_humana=False))
    par(pode2 is True and porque2 == "",
        "sem palavra humana a MESMA porta LIBERA",
        "(%r, %r)" % (pode2, porque2))

    antes = os.environ.get("JANELA_SILENCIO_HUMANO_DIAS")
    os.environ["JANELA_SILENCIO_HUMANO_DIAS"] = "0"
    try:
        pode3, porque3 = _porta(_mundo_do_follow_up(com_palavra_humana=True))
    finally:
        if antes is None:
            os.environ.pop("JANELA_SILENCIO_HUMANO_DIAS", None)
        else:
            os.environ["JANELA_SILENCIO_HUMANO_DIAS"] = antes
    par(pode3 is True,
        "com N=0 o follow-up volta a sair",
        "(%r, %r)" % (pode3, porque3))


# ===========================================================================
# utilitários
# ===========================================================================

def _n_dias() -> int:
    from app.services.o_fim_do_atendimento import janela_de_silencio_dias

    return janela_de_silencio_dias()


def _esquecer_o_feed() -> None:
    """A memória do "uma linha por dia" é do PROCESSO: um teste não pode herdar
    a do anterior, senão o cenário seguinte mediria o de trás."""
    from app.services.o_fim_do_atendimento import _SILENCIO_JA_ANOTADO

    _SILENCIO_JA_ANOTADO.clear()


def main() -> int:
    print("=" * 72)
    print("A JANELA DA PALAVRA HUMANA ESTÁ LIGADA NOS PORTÕES")
    print("=" * 72)
    teste_a_entrada_nao_aciona_a_ia_quando_a_atendente_falou()
    teste_o_CONTROLE_da_entrada_conversa_sem_palavra_humana()
    teste_a_saida_descarta_quando_ela_fala_durante_o_turno()
    teste_o_CONTROLE_do_N_zero_desliga_a_regra()
    teste_o_CONTROLE_do_motor_neutralizado()
    teste_o_follow_up_nao_fala_por_cima_da_atendente()

    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print("%d PROBLEMA(S):" % len(_PROBLEMAS))
        for p in _PROBLEMAS:
            print("  - %s" % p)
        return 1
    print("TUDO VERDE — a regra tem chamador, e o veredito dele manda.")
    return 0


def test_a_janela_esta_ligada_nos_portoes():
    """A porta do pytest — o mesmo roteiro, uma asserção só."""
    assert main() == 0, _PROBLEMAS


if __name__ == "__main__":
    sys.exit(main())
