# -*- coding: utf-8 -*-
"""O ATENDIMENTO TEM RELÓGIO — e ele fala a MESMA língua do chat do painel.

> **O TESTE DO PRODUTO:** *"Quanto tempo o segurado esperou por esta resposta, e
> em que etapa o tempo foi embora?"* Hoje a pergunta só tem resposta no chat do
> painel. Pelo WhatsApp — que é por onde o segurado fala — não tem nenhuma.

```
① o turno do atendimento vira `messages.payload.turn`, DEPOIS do envio
② o vocabulário é o do `chat.py`, medido por AST — não de memória
③ `relogio_da_fila` ausente → `ms` None (nunca 0 inventado); presente → o número
④ o `payload` que já existia (`origem`, `direcao`, `wa_message_id`) é PRESERVADO
⑤ falhar ao gravar o relógio NÃO derruba o turno e NÃO produz segunda mensagem
```

🔴 **POR QUE O VOCABULÁRIO É MEDIDO, E NÃO ESCRITO AQUI.** A proposta da SPEC
escreveu `etapas`/`nome` de memória. 📊 O código diz outra coisa: `chat.py:1122`
declara `estagios: List[str]` e `chat.py:1225` grava `"stages": estagios`. Dois
nomes para o mesmo fato é o defeito que o CLAUDE.md §12.1 manda consertar no
CAMPO. Este arquivo LÊ `chat.py` por AST e falha se as duas grafias divergirem —
inclusive no dia em que for o `chat.py` a mudar de nome.

⚠️ **O MOTOR, não o regex** (CLAUDE.md §9.4): ① ③ ④ ⑤ rodam
`process_whatsapp_message_background` DE VERDADE, com os dublês do harness de
`test_a_atendente_fala_e_o_robo_cala.py` — o mesmo método de
`test_a_janela_esta_ligada_nos_portoes.py:108-176`. Só ② é inspeção de
declaração, e é legítima: o alvo é a FORMA do vocabulário, não o comportamento.

⛔ Sem rede, sem banco, sem Redis, sem mensagem enviada. Zero PII: telefones
sintéticos, nenhum nome de corretora ou de pessoa real (CLAUDE.md §13.9).
"""
from __future__ import annotations

import ast
import asyncio
import os
import sys

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

# 🔴 O harness do webhook, reusado inteiro — dublês, carregador e tudo (§5).
import test_a_atendente_fala_e_o_robo_cala as H  # noqa: E402

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
    """A linha de CONTROLE: `acusou=True` quando o guarda CONSEGUE ficar
    vermelho. Um guarda que não tem como falhar não guarda nada (§9.3)."""
    checar(acusou, "CONTROLE — " + o_que, evidencia)


# ===========================================================================
# ② O VOCABULÁRIO DO CHAT, MEDIDO NO `chat.py` — nunca escrito de memória
# ===========================================================================

def _chaves_do_turno_do_chat() -> set:
    """As chaves do literal `dados_do_turno = {...}` de `chat.py`, por AST.

    ⚠️ Inspeção de DECLARAÇÃO, e é o caso legítimo do CLAUDE.md §9.4: o que se
    afirma aqui é a FORMA do vocabulário, não o comportamento de um motor.
    """
    fonte = os.path.join(RAIZ, "app", "api", "chat.py")
    with open(fonte, "r", encoding="utf-8") as arq:
        arvore = ast.parse(arq.read())
    chaves: set = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Assign) or not isinstance(no.value, ast.Dict):
            continue
        nomes = [a.id for a in no.targets if isinstance(a, ast.Name)]
        if "dados_do_turno" not in nomes:
            continue
        for k in no.value.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                chaves.add(k.value)
    return chaves


def _estados_do_chat() -> set:
    """Os valores que `chat.py` atribui a `estado` — o vocabulário de `status`."""
    fonte = os.path.join(RAIZ, "app", "api", "chat.py")
    with open(fonte, "r", encoding="utf-8") as arq:
        arvore = ast.parse(arq.read())
    valores: set = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Assign) or not isinstance(no.value, ast.Constant):
            continue
        if not isinstance(no.value.value, str):
            continue
        if any(isinstance(a, ast.Name) and a.id == "estado" for a in no.targets):
            valores.add(no.value.value)
    return valores


def teste_o_vocabulario_e_o_mesmo_do_chat():
    print("\n[2] VOCABULÁRIO — o atendimento fala a língua do chat, medida no chat.py")
    # 🔴 `H.motor()`, e NUNCA `import app.api.webhook` direto: `webhook.py:56`
    # roda `supabase = get_supabase_client()` no topo do modulo, e importar sem
    # o duble instalado construia um cliente Supabase DE VERDADE (📊 21/09/2026:
    # com chave fora do formato JWT o guarda explodia em `Invalid API key`; com
    # URL morta ficava verde sem consultar nada).
    w = H.motor()

    do_chat = _chaves_do_turno_do_chat()
    checar("status" in do_chat and "total_ms" in do_chat and "stages" in do_chat,
           "`chat.py` declara `status`, `total_ms` e `stages`",
           "%d chaves lidas do literal" % len(do_chat))
    checar("etapas" not in do_chat and "nome" not in do_chat,
           "`chat.py` NÃO usa `etapas`/`nome` — a proposta escreveu de memória",
           "o código vence")

    turno = w.montar_turno_do_atendimento(status="complete", total_ms=1234)
    checar(set(("status", "total_ms", "stages")).issubset(set(turno)),
           "o turno do atendimento usa as MESMAS três chaves",
           ", ".join(sorted(turno)))
    checar("etapas" not in turno and "nome" not in str(turno),
           "e NÃO cria um segundo vocabulário (`etapas`/`nome`)")
    checar(isinstance(turno["stages"], list)
           and all(isinstance(x, str) for x in turno["stages"]),
           "`stages` é lista de TEXTO, do mesmo tipo do `chat.py:1122` "
           "(`estagios: List[str]`)",
           repr(turno["stages"]))
    checar(list(turno["stages"]) == ["buffer_espera", "fila_cota", "grafo", "envio"],
           "as quatro etapas do atendimento, na ordem em que acontecem")
    checar(set(turno["stage_ms"]) == set(turno["stages"]),
           "`stage_ms` cobre exatamente as etapas declaradas — nem mais, nem menos")

    estados = _estados_do_chat()
    checar("complete" in estados and "failed" in estados,
           "`chat.py` escreve `complete` e `failed` (📊 :1123/:1185) — "
           "não `completed`", ", ".join(sorted(estados)))
    checar(turno["status"] in estados,
           "e o atendimento usa um valor DESSE conjunto",
           repr(turno["status"]))


def teste_a_funcao_pura_nunca_inventa_zero():
    print("\n[3] `relogio_da_fila` — ausente é None, presente é o número")
    w = H.motor()

    sem = w.montar_turno_do_atendimento(status="complete", total_ms=900)
    checar(sem["stage_ms"]["buffer_espera"] is None
           and sem["stage_ms"]["fila_cota"] is None,
           "sem o contrato, as duas etapas da fila saem None",
           "0 é medição; None é 'não medido'")

    com = w.montar_turno_do_atendimento(
        status="complete", total_ms=900,
        relogio_da_fila={"buffer_espera_ms": 8000, "fila_cota_ms": 0},
        grafo_ms=700, envio_ms=200)
    checar(com["stage_ms"] == {"buffer_espera": 8000, "fila_cota": 0,
                               "grafo": 700, "envio": 200},
           "com o contrato, os quatro números chegam inteiros",
           repr(com["stage_ms"]))
    par(com["stage_ms"]["fila_cota"] == 0 and sem["stage_ms"]["fila_cota"] is None,
        "ZERO medido e NÃO MEDIDO são valores diferentes",
        "um dicionário que devolvesse 0 nos dois casos não distinguiria")

    checar("provedor" not in sem and "usage" not in sem,
           "o que não foi medido fica AUSENTE, como no `chat.py:1229-1231` — "
           "chave com None é ruído que mente sobre ter havido medição")
    com2 = w.montar_turno_do_atendimento(status="failed", total_ms=1,
                                         provedor="um-provedor", modelo="um-modelo")
    checar(com2.get("provedor") == "um-provedor" and com2.get("modelo") == "um-modelo",
           "e quando são medidos, entram")


# ===========================================================================
# ① ④ ⑤ O MOTOR DE VERDADE — `process_whatsapp_message_background`
# ===========================================================================

async def _conversa_fixa(**_k) -> str:
    return CONVERSA


def _rodar_o_turno(*, relogio_da_fila=None, quebrar_a_gravacao: bool = False,
                   envio_falha: bool = False, envio_explode: bool = False,
                   demora_no_modelo: float = 0.0, demora_no_envio: float = 0.0,
                   cortar_apos_s=None) -> dict:
    """Roda `process_whatsapp_message_background` DE VERDADE.

    Devolve `{"enviados", "mensagens", "erro"}`. 🔴 O que se mede é o que ficou
    no banco e o que o segurado recebeu — nunca o que uma função devolveu.
    """
    w = H.motor()
    H.agente_ligado(True)
    b = H.zerar_banco()
    H.semear_as_duas_conversas(b)

    guardado = {nome: getattr(w, nome, None) for nome in
                ("whatsapp_service", "integration_service", "LangChainService",
                 "get_or_create_conversation", "gravar_o_relogio_do_turno")}

    class _EnvioQueFalha(H.EnvioFalso):
        def send_message(self, to_number=None, text=None, integration=None, *a, **k):
            super().send_message(to_number=to_number, text=text,
                                 integration=integration)
            return False

    class _EnvioQueExplode(H.EnvioFalso):
        """O canal FORA DO AR: `send_message` levanta, e é assim que o `except`
        de fora do pipeline entra em cena com o aviso honesto ao segurado."""

        def send_message(self, to_number=None, text=None, integration=None, *a, **k):
            super().send_message(to_number=to_number, text=text,
                                 integration=integration)
            if len(self.enviados) == 1:      # só a resposta; o aviso honesto passa
                raise RuntimeError("o canal está fora do ar")
            return True

    class _EnvioQueDemora(H.EnvioFalso):
        """`send_message` roda numa THREAD e NAO e' cancelavel. Depois que ela
        comeca, o balao pode sair mesmo com o turno cortado — e e' por isso que
        o ponto sem volta existe."""

        def send_message(self, to_number=None, text=None, integration=None, *a, **k):
            import time as _t
            _t.sleep(demora_no_envio)
            return super().send_message(to_number=to_number, text=text,
                                        integration=integration)

    if demora_no_envio:
        envio = _EnvioQueDemora()
    elif envio_explode:
        envio = _EnvioQueExplode()
    elif envio_falha:
        envio = _EnvioQueFalha()
    else:
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
            # 🔴 O PROVEDOR PENDURADO: é aqui que o teto de turno do processador
            # corta a corrotina, com `CancelledError`.
            if demora_no_modelo:
                await asyncio.sleep(demora_no_modelo)
            return "Claro! Vou verificar sua apolice agora mesmo.", {}

    w.LangChainService = _LangChainFalso
    w.get_or_create_conversation = _conversa_fixa

    if quebrar_a_gravacao:
        async def _explode(*_a, **_k):
            raise RuntimeError("o banco caiu bem na hora de gravar o relógio")

        w.gravar_o_relogio_do_turno = _explode

    entrada = {
        "connectedPhone": "554800000000", "phone": TELEFONE, "isGroup": False,
        "fromMe": False, "text": {"message": "Oi, e sobre o guincho de ontem"},
        "messageId": "WAMSG-IN-RELOGIO", "senderName": "Segurado",
        "_integration_id": "int-1",
    }
    erro = None

    async def _com_corte():
        """O TETO DE TURNO, em escala de teste: `create_task` + `cancel`.

        ⚠️ E' EXATAMENTE o que `asyncio.wait_for(chamada, timeout=teto)` faz em
        `buffer_processor.processar_buffers_prontos` — cancelar a corrotina do
        atendimento. O que se mede e' o comportamento do MOTOR sob cancelamento,
        nao o de uma copia dele (CLAUDE.md §9.4).
        """
        tarefa = asyncio.create_task(
            w.process_whatsapp_message_background(entrada)
            if relogio_da_fila is None else
            w.process_whatsapp_message_background(
                entrada, relogio_da_fila=relogio_da_fila))
        await asyncio.sleep(float(cortar_apos_s))
        tarefa.cancel()
        try:
            await tarefa
        finally:
            # A thread do envio, se ja tinha comecado, ainda esta correndo:
            # esperar por ela e' o que permite CONTAR os baloes que sairam.
            await asyncio.sleep(0.6)

    try:
        if cortar_apos_s is not None:
            asyncio.run(_com_corte())
        elif relogio_da_fila is None:
            asyncio.run(w.process_whatsapp_message_background(entrada))
        else:
            asyncio.run(w.process_whatsapp_message_background(
                entrada, relogio_da_fila=relogio_da_fila))
    except BaseException as exc:  # noqa: BLE001
        erro = exc
    finally:
        for nome, valor in guardado.items():
            if valor is None:
                if hasattr(w, nome):
                    delattr(w, nome)
            else:
                setattr(w, nome, valor)
    return {"enviados": envio.enviados, "mensagens": b.linhas("messages"),
            "erro": erro}


def _resposta_do_agente(mensagens: list) -> dict:
    do_agente = [m for m in mensagens if str(m.get("role")) == "assistant"]
    return do_agente[-1] if do_agente else {}


def teste_o_turno_vai_ao_banco_com_o_relogio():
    print("\n[1] MOTOR — o turno do atendimento grava `payload.turn`")
    r = _rodar_o_turno()
    checar(r["erro"] is None, "o turno não levantou",
           type(r["erro"]).__name__ if r["erro"] else "sem exceção")
    checar(len(r["enviados"]) == 1, "o segurado recebeu UMA resposta",
           "%d envio(s)" % len(r["enviados"]))

    linha = _resposta_do_agente(r["mensagens"])
    payload = dict(linha.get("payload") or {})
    turno = dict(payload.get("turn") or {})
    checar(bool(turno), "a linha do agente carrega `payload.turn`",
           ", ".join(sorted(turno)) or "VAZIO")
    checar(turno.get("status") == "complete",
           "com `status` do vocabulário do chat", repr(turno.get("status")))
    checar(isinstance(turno.get("total_ms"), int) and turno["total_ms"] >= 0,
           "e `total_ms` medido, não inventado", repr(turno.get("total_ms")))
    checar(isinstance(turno.get("stage_ms", {}).get("envio"), int),
           "a etapa `envio` tem número — ela é medida DEPOIS do envio",
           repr(turno.get("stage_ms", {}).get("envio")))
    checar(turno.get("stage_ms", {}).get("buffer_espera") is None,
           "sem o contrato da fila, `buffer_espera` fica None")

    # ④ O PAYLOAD QUE JÁ EXISTIA CONTINUA LÁ.
    checar(payload.get("origem") == "agente" and payload.get("direcao") == "out",
           "o `payload` de antes (`origem`/`direcao`) foi PRESERVADO — "
           "`turn` é uma chave a MAIS, não um dicionário novo",
           repr({k: v for k, v in payload.items() if k != "turn"}))


def teste_o_contrato_da_fila_chega_ao_banco():
    print("\n[3b] MOTOR — `relogio_da_fila` atravessa até o banco")
    # ⚠️ 📊 OS NÚMEROS MUDARAM EM 21/09/2026, E A AFIRMAÇÃO TAMBÉM.
    #
    # O guarda antigo exigia `total_ms >= buffer_espera + fila_cota`. Era a soma
    # que o webhook fazia — e ela era ERRADA: `buffer_espera` vai do `first_at`
    # da rajada até o consumo, e a espera pela cota acontece DENTRO desse
    # intervalo (`juiz/medir.py` M2: `{'buffer_espera_ms': 11000,
    # 'fila_cota_ms': 1012}` virava `_antes_daqui = 12012` para um tempo real de
    # 11000 ms). O teste guardava uma verdade vencida, e verdade vencida ensina
    # a ignorar teste (CLAUDE.md §9.3): ele foi ATUALIZADO e a lição MIGROU —
    # agora ele afirma que `fila_cota` **não** se soma.
    r = _rodar_o_turno(relogio_da_fila={"buffer_espera_ms": 11000,
                                        "fila_cota_ms": 1008})
    turno = dict((_resposta_do_agente(r["mensagens"]).get("payload") or {}).get("turn") or {})
    ms = dict(turno.get("stage_ms") or {})
    checar(ms.get("buffer_espera") == 11000 and ms.get("fila_cota") == 1008,
           "os dois números da fila chegaram inteiros ao `payload.turn`",
           repr(ms))
    total = turno.get("total_ms")
    daqui = (int(total) - 11000) if isinstance(total, int) else None
    checar(isinstance(total, int) and total >= 11000,
           "`total_ms` cobre a espera no buffer (%s ms)" % total, repr(ms))
    checar(daqui is not None and daqui < 1008,
           "🔴 e NÃO soma `fila_cota` outra vez: o que sobra depois do buffer "
           "(%s ms) é o turno desta função, menor que os 1008 ms da fila" % daqui,
           "a soma dupla daria >= %d; veio %s" % (11000 + 1008, total))
    # 🔴 A LINHA DE CONTROLE: a asserção acima CONSEGUE ficar vermelha — a conta
    # errada (a de antes) produz exatamente o valor que ela proíbe.
    par(not ((11000 + 1008) - 11000 < 1008),
        "a soma dupla (`buffer_espera + fila_cota`) violaria a asserção acima",
        "é ela que dá direito à conclusão (CLAUDE.md §9.2)")
    checar(isinstance(ms.get("grafo"), int) and isinstance(ms.get("envio"), int),
           "e `grafo` e `envio`, que SÃO parcelas, continuam medidos", repr(ms))


def teste_o_relogio_que_explode_nao_derruba_o_atendimento():
    print("\n[5] MOTOR — gravar o relógio falhou: o segurado não sente nada")
    r = _rodar_o_turno(quebrar_a_gravacao=True)
    checar(r["erro"] is None,
           "a exceção da gravação NÃO propagou",
           type(r["erro"]).__name__ if r["erro"] else "sem exceção")
    checar(len(r["enviados"]) == 1,
           "e o segurado recebeu UMA resposta — não duas, nem o pedido de desculpas",
           "%d envio(s): %s" % (len(r["enviados"]),
                                [e["texto"][:24] for e in r["enviados"]]))
    linha = _resposta_do_agente(r["mensagens"])
    checar("turn" not in (linha.get("payload") or {}),
           "o turno ficou sem relógio — declarado, não inventado")

    # CONTROLE: o MESMO cenário com a gravação de pé volta a ter relógio.
    ok = _rodar_o_turno()
    par("turn" in (_resposta_do_agente(ok["mensagens"]).get("payload") or {}),
        "com a gravação de pé, o MESMO cenário grava o relógio",
        "é a gravação que faz a diferença — e ela é opcional para o segurado")

    # =====================================================================
    # 🔴 O CASO QUE DE FATO CHEGA AO SEGURADO — e o único que fica vermelho
    #    quando o `try/except` do relógio some.
    # =====================================================================
    #
    # ⚠️ No caminho FELIZ, uma exceção do relógio seria engolida pelo `except`
    # de fora sem custo: `_resposta_ja_enviada` já é True. É no caminho em que
    # o ENVIO FALHOU que ela custa: aí `_resposta_ja_enviada` é False, o
    # `except` de fora manda "tive uma falha técnica" ao segurado — e o
    # segurado recebe um pedido de desculpas por causa de uma CONTABILIDADE
    # que ele nem sabe que existe.
    print("      e com o ENVIO falhando ao mesmo tempo:")
    duplo = _rodar_o_turno(quebrar_a_gravacao=True, envio_falha=True)
    textos = [e["texto"] for e in duplo["enviados"]]
    desculpas = [t for t in textos if "falha" in t.lower()]
    checar(duplo["erro"] is None and not desculpas,
           "envio recusado + relógio quebrado: o segurado NÃO recebe um "
           "pedido de desculpas causado pela medição",
           "%d tentativa(s) de envio, %d pedido(s) de desculpas"
           % (len(textos), len(desculpas)))

    # 🔴 A LINHA DE CONTROLE: o pedido de desculpas EXISTE e é alcançável.
    # Sem ela, o guarda acima ficaria verde num pipeline que simplesmente nunca
    # fala com o segurado no erro — e o mérito iria para o lugar errado.
    canal_fora = _rodar_o_turno(envio_explode=True)
    par(any("falha" in e["texto"].lower() for e in canal_fora["enviados"]),
        "com o CANAL fora do ar e o relógio de pé, o segurado recebe sim o "
        "aviso honesto — o caminho das desculpas está vivo",
        "%d envio(s)" % len(canal_fora["enviados"]))


def teste_o_envio_que_falha_vira_status_failed():
    print("\n[1b] MOTOR — o canal recusou: o turno fica `failed`, não `complete`")
    r = _rodar_o_turno(envio_falha=True)
    turno = dict((_resposta_do_agente(r["mensagens"]).get("payload") or {}).get("turn") or {})
    checar(turno.get("status") == "failed",
           "o turno registra a recusa do canal", repr(turno.get("status")))
    par(turno.get("status") != "complete",
        "e `complete` NÃO é o valor padrão de qualquer turno",
        "o guarda [1] e este não podem ficar verdes pelo mesmo caminho")




# ===========================================================================
# 🔴 O TURNO CORTADO PELO TETO DE TEMPO — E O SEGURADO NÃO FICA EM SILÊNCIO
# ===========================================================================
#
# 📊 O defeito (21/09/2026): o teto de turno do processador corta com
# `asyncio.wait_for`, que levanta `CancelledError` — e `CancelledError` **não é
# `Exception`**. O `except Exception` do webhook, o que manda o aviso honesto,
# NÃO rodava. A rajada já tinha saído do Redis (`get_and_clear`), nada era dito,
# nada voltava ao buffer e nenhum humano era avisado:
# `redteam/atk3c_teto_de_turno.py` →
# `o segurado recebeu ATE o corte: [] | DEPOIS do corte: []`.
#
# ⚖️ E a regra tem DOIS lados, porque o `send_message` roda numa thread que não
# é cancelável:
#   envio ainda NÃO começou → RIGOR:     vai o MESMO aviso honesto
#   envio JÁ começou        → IGUALDADE: não vai NADA a mais (duplicar é pior)
def teste_o_turno_cortado_nao_vira_silencio():
    print("\n[6] MOTOR — o teto de tempo corta o turno: o segurado ouve o quê?")

    # (i) O CORTE ANTES DO ENVIO -> o aviso honesto SAI, e é ele mesmo.
    antes = _rodar_o_turno(demora_no_modelo=5.0, cortar_apos_s=0.4)
    textos = [e["texto"] for e in antes["enviados"]]
    checar(isinstance(antes["erro"], asyncio.CancelledError),
           "🔴 o `CancelledError` PROPAGA — engolir cancelamento é defeito",
           type(antes["erro"]).__name__ if antes["erro"] else "nenhum erro")
    checar(len(textos) == 1,
           "o segurado recebeu EXATAMENTE uma mensagem",
           "%d: %s" % (len(textos), [t[:30] for t in textos]))
    import app.api.webhook as _w_mod
    checar(bool(textos) and textos[0] == _w_mod.TEXTO_DA_FALHA_HONESTA,
           "🔴 e ela é o MESMO aviso honesto do caminho de erro — nenhum texto "
           "novo, nenhum 'não entendi'",
           repr(textos[0][:40]) if textos else "NADA")

    # (ii) O CORTE DURANTE O ENVIO -> nada a mais. O balão pode sair; o que não
    #      pode é o segurado receber a resposta E um pedido de desculpas.
    durante = _rodar_o_turno(demora_no_envio=1.2, cortar_apos_s=0.4)
    textos2 = [e["texto"] for e in durante["enviados"]]
    desculpas = [t for t in textos2 if "falha" in t.lower()]
    checar(isinstance(durante["erro"], asyncio.CancelledError),
           "o `CancelledError` propaga também neste caminho",
           type(durante["erro"]).__name__ if durante["erro"] else "nenhum erro")
    checar(not desculpas,
           "🔴 corte DURANTE o envio: ZERO mensagens a mais — nada de resposta "
           "duplicada nem desculpa em cima de resposta",
           "%d envio(s): %s" % (len(textos2), [t[:30] for t in textos2]))

    # 🔴 LINHA DE CONTROLE: sem corte, o MESMO cenário entrega a RESPOSTA — e
    # não o aviso honesto. Sem ela, um pipeline que nunca falasse com o segurado
    # deixaria (ii) verde pelo motivo errado.
    normal = _rodar_o_turno(demora_no_envio=0.05)
    textos3 = [e["texto"] for e in normal["enviados"]]
    par(len(textos3) == 1 and textos3[0] != _w_mod.TEXTO_DA_FALHA_HONESTA,
        "sem o corte, o MESMO cenário entrega a RESPOSTA do agente",
        "%s" % [t[:30] for t in textos3])


def main() -> int:
    print("=" * 72)
    print("O ATENDIMENTO TEM RELÓGIO — no vocabulário do chat")
    print("=" * 72)
    teste_o_vocabulario_e_o_mesmo_do_chat()
    teste_a_funcao_pura_nunca_inventa_zero()
    teste_o_turno_vai_ao_banco_com_o_relogio()
    teste_o_contrato_da_fila_chega_ao_banco()
    teste_o_envio_que_falha_vira_status_failed()
    teste_o_relogio_que_explode_nao_derruba_o_atendimento()
    teste_o_turno_cortado_nao_vira_silencio()

    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print("%d PROBLEMA(S):" % len(_PROBLEMAS))
        for p in _PROBLEMAS:
            print("  - %s" % p)
        return 1
    print("TUDO VERDE — o atendimento mede o próprio turno, e fala a língua do chat.")
    return 0


def test_o_atendimento_tem_relogio():
    """A porta do pytest — o mesmo roteiro, uma asserção só."""
    assert main() == 0, _PROBLEMAS


if __name__ == "__main__":
    sys.exit(main())
