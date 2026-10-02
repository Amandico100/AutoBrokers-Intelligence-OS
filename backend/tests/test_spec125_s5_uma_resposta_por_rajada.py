# -*- coding: utf-8 -*-
r"""SPEC-125 S5 — UMA RESPOSTA POR RAJADA (texto e imagens).

> Ordem do Founder (01/10/2026): *"ele fala 5 frases e o agente respondia as 5…
> 8 imagens e uma explicação — não adianta responder todas"*.

📊 O defeito, reproduzido com as funções REAIS no BLOCO 0 (B0-125 §1): 5 frases
com a digitação de verdade (4/9/6/12 s) viravam **3 respostas**; 8 fotos a cada
4 s + a explicação viravam **2** (o teto de 25 s cortava a rajada no meio).

O QUE ESTE ARQUIVO RODA — o MOTOR inteiro, com dublê só nas BORDAS:

```
_buffer_or_dispatch_text (REAL, a entrada do webhook)
  -> MessageBufferService.add_message / prontas / trava de turno (REAIS)
  -> buffer_processor.processar_buffers_prontos (REAL, varredura de 1 s)
  -> webhook.process_whatsapp_message_background (REAL, o turno inteiro)
       _midia_do_turno (REAL)  -> [BORDA] subir a foto + a visão
       [BORDA] o modelo (LangChainService) -> as 4 perguntas da saída (REAIS)
  -> [BORDA] o envio ao WhatsApp, que CONTA
```

Redis em memória com TTL no RELÓGIO DUBLADO; PostgREST em memória que filtra
(o do harness `test_a_atendente_fala_e_o_robo_cala.py`). O relógio só anda
quando todo turno em voo está PARADO numa espera dublada (modelo ou visão): o
que se mede é a regra, não a velocidade da máquina.

```
 [R1] 5 frases (4/9/6/12 s), modelo no 📊 p50 (5,4 s)  -> 1 resposta, com as 5
 [R1b] o mesmo, modelo no 📊 p90 (17,9 s)                -> 1 resposta
 [R2] 8 fotos a cada 4 s + a explicação                  -> 1 resposta, 8 descrições
      numeradas + a explicação; as 8 URLs guardadas; visão em paralelo (<= 4)
 [R3] mensagem nova DURANTE a geração                    -> a 1ª resposta NÃO sai
 [R4] CONTROLE: uma mensagem só                          -> no MESMO segundo de hoje
 [MUT-A] sem a 4ª pergunta        -> R1 e R3 ficam VERMELHOS
 [MUT-B] teto estendido = 25 s    -> R2 fica VERMELHO
 [ANTES/DEPOIS] as medidas, pelo mesmo motor
```

📊 Latências do modelo: `conversation_logs.response_time_ms`, 566 turnos,
14/09/2026 — p50 5,4 s · p90 17,9 s (citadas em `message_buffer_service.py:45`).
💭 A latência da visão (3 s por foto) é ILUSTRATIVA: serve para comparar série
× paralelo, não é medição.

⛔ Sem rede, sem banco, sem Redis de verdade, sem LLM, nada enviado. Telefones e
ids 100% sintéticos; nenhum nome de corretora ou pessoa (CLAUDE.md §13.9).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec125_s5_uma_resposta_por_rajada.py -q -p no:cacheprovider
    PYTHONIOENCODING=utf-8 python tests/test_spec125_s5_uma_resposta_por_rajada.py     (imprime as medidas)
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import os
import sys
import time
from datetime import datetime, timedelta

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)
os.environ["SEM_REDE"] = "1"

# 🔴 O harness do webhook, reusado (CLAUDE.md §5): o dublê vem ANTES do import.
import test_a_atendente_fala_e_o_robo_cala as H  # noqa: E402

# ⚠️ O MOTOR SOBE NA EXECUÇÃO, nunca na coleta: o `conftest` fotografa a coleta e
# devolve os atributos de `app.*` depois dela — um `H.motor()` aqui deixava o
# harness em cache com o dublê do banco DESFEITO para o arquivo seguinte
# (📊 01/10/2026: `test_a_janela_esta_ligada_nos_portoes` vermelho logo depois).
W = M = VS = BP = None


def _reatar_os_pacotes() -> None:
    """📊 01/10/2026: com este arquivo PRIMEIRO na sessão, a devolução da coleta
    (`conftest._devolver`) tirava `app.core` de `vars(app)` com `app.core` ainda
    em `sys.modules` — e `import app.core.database as x` (o do harness) caía em
    `ImportError: cannot import name 'core' from 'app'`. Reata pai → filho; o
    `conftest` devolve tudo no fim do arquivo, como sempre."""
    for nome, mod in list(sys.modules.items()):
        if mod is None or not nome.startswith("app."):
            continue
        pai, _ponto, filho = nome.rpartition(".")
        pacote = sys.modules.get(pai)
        if pacote is not None and not hasattr(pacote, filho):
            setattr(pacote, filho, mod)


def _motor() -> None:
    global W, M, VS, BP
    _reatar_os_pacotes()
    W = H.motor()
    import app.services.message_buffer_service as _m
    import app.services.vision_service as _vs
    import app.tasks.buffer_processor as _bp

    M, VS, BP = _m, _vs, _bp

TELEFONE = H.TELEFONE
INTEGRACAO = "int-1"                   # o `_integration_id` do harness
#: a chave do buffer — o MESMO formato de `MessageBufferService.chave`.
CHAVE = "whatsapp_buffer:%s:%s" % (INTEGRACAO, TELEFONE)

#: 📊 p50 e p90 de `conversation_logs.response_time_ms` (14/09/2026, 566 turnos).
MODELO_P50_S = 5.4
MODELO_P90_S = 17.9
#: 💭 ilustrativo — só para comparar série × paralelo.
VISAO_S = 3.0


# ===========================================================================
# O RELÓGIO DUBLADO e a espera que o faz andar
# ===========================================================================
RELOGIO = [datetime(2026, 10, 1, 12, 0, 0)]
T0 = [RELOGIO[0]]


class _Agora:
    @staticmethod
    def now():
        return RELOGIO[0]

    @staticmethod
    def fromisoformat(texto):
        return datetime.fromisoformat(texto)


def _t() -> float:
    return (RELOGIO[0] - T0[0]).total_seconds()


#: Quem está PARADO numa espera dublada, por varredura (o dono vem do contexto:
#: as tarefas do `gather` da visão herdam a cópia do contexto de quem as criou).
DONO = contextvars.ContextVar("dono_da_varredura", default=None)
PARADOS: dict = {}          # id_da_espera -> dono
EM_VOO_VISAO = [0, 0]       # [agora, pico]


async def esperar_virtual(segundos: float, *, visao: bool = False) -> None:
    alvo = RELOGIO[0] + timedelta(seconds=float(segundos))
    marca = object()
    PARADOS[id(marca)] = DONO.get()
    if visao:
        EM_VOO_VISAO[0] += 1
        EM_VOO_VISAO[1] = max(EM_VOO_VISAO[1], EM_VOO_VISAO[0])
    try:
        while RELOGIO[0] < alvo:
            await asyncio.sleep(0.001)
    finally:
        PARADOS.pop(id(marca), None)
        if visao:
            EM_VOO_VISAO[0] -= 1


# ===========================================================================
# O REDIS DUBLÊ — o que o buffer, a trava e a contabilidade do varredor usam
# ===========================================================================
class _Pipe:
    def __init__(self, r):
        self.r, self.acoes = r, []

    def get(self, k):
        self.acoes.append(("get", k))

    def delete(self, k):
        self.acoes.append(("delete", k))

    async def execute(self):
        return [await getattr(self.r, a)(k) for a, k in self.acoes]


class RedisDuble:
    def __init__(self):
        self.dados: dict = {}

    def _vivo(self, k):
        item = self.dados.get(k)
        if item is None:
            return None
        valor, expira = item
        if expira is not None and RELOGIO[0] >= expira:
            self.dados.pop(k, None)
            return None
        return valor

    async def get(self, k):
        return self._vivo(k)

    async def mget(self, ks):
        return [self._vivo(k) for k in ks]

    async def set(self, k, v, nx=False, ex=None):
        if nx and self._vivo(k) is not None:
            return None
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ex)) if ex else None)
        return True

    async def setex(self, k, ttl, v):
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ttl)))
        return True

    async def delete(self, k):
        return 1 if self.dados.pop(k, None) is not None else 0

    async def expire(self, k, ttl):
        valor = self._vivo(k)
        if valor is None:
            return False
        self.dados[k] = (valor, RELOGIO[0] + timedelta(seconds=int(ttl)))
        return True

    async def hset(self, k, mapping=None):
        atual = self._vivo(k) or {}
        atual.update(mapping or {})
        self.dados[k] = (atual, None)
        return True

    async def hincrby(self, k, campo, n=1):
        atual = self._vivo(k) or {}
        atual[campo] = int(atual.get(campo, 0)) + int(n)
        self.dados[k] = (atual, None)
        return atual[campo]

    async def eval(self, script, _n, chave, token, *resto):
        atual = self._vivo(chave)
        if script == M.LUA_LIBERA_SE_FOR_MEU:
            if atual == token:
                self.dados.pop(chave, None)
                return 1
            return 0
        if script == M.LUA_RENOVA_SE_FOR_MEU:
            if atual == token:
                self.dados[chave] = (atual, RELOGIO[0] + timedelta(seconds=int(resto[0])))
                return 1
            return 0
        raise AssertionError("script Lua desconhecido no dublê")

    def pipeline(self):
        return _Pipe(self)


# ===========================================================================
# AS BORDAS: o modelo, a visão, o envio
# ===========================================================================
ESTADO: dict = {}


class EnvioQueConta(H.EnvioFalso):
    def send_message(self, to_number=None, text=None, integration=None, *a, **k):
        super().send_message(to_number=to_number, text=text, integration=integration)
        self.enviados[-1]["t"] = _t()
        return True


class ModeloDuble:
    """`LangChainService` — devolve `RESPOSTA-n` depois de pensar `latencia` s
    VIRTUAIS, e guarda o que LEU. ⚠️ É borda: as 4 perguntas da saída, a
    gravação e o envio que vêm depois são os do webhook de verdade."""

    def __init__(self, *_a, **_k):
        pass

    async def process_message(self, *_a, **k):
        n = len(ESTADO["geracoes"]) + 1
        ESTADO["geracoes"].append({"n": n, "inicio": _t(),
                                   "leu": str(k.get("user_message") or "")})
        await esperar_virtual(ESTADO["latencia"])
        return "RESPOSTA-%d" % n, {}


async def _subir_foto(url, *_a, **_k):
    return url.replace("https://wa.invalido/", "https://storage.invalido/")


async def _descrever(url, *_a, **_k):
    ESTADO["visoes"] += 1
    await esperar_virtual(VISAO_S, visao=True)
    return "descrição de %s" % url.rsplit("/", 1)[-1]


async def _conversa_fixa(**_k):
    return "real"


def _preparar(latencia: float) -> M.MessageBufferService:
    RELOGIO[0] = datetime(2026, 10, 1, 12, 0, 0)
    T0[0] = RELOGIO[0]
    M.datetime = _Agora
    servico = M.MessageBufferService(RedisDuble())
    M._buffer_service_instance = servico

    H.agente_ligado(True)
    b = H.zerar_banco()
    H.semear_as_duas_conversas(b)

    import app.services.billing_gate as _porteira
    import app.services.billing_replies as _cobranca
    import app.services.platform_outbound as _plataforma

    async def _sem_nota(*_a, **_k):
        return None

    _porteira.pode_consumir = lambda *_a, **_k: (True, "ok")
    _cobranca.contexto_de_cobranca = _sem_nota
    _cobranca.telefones_da_equipe_de_cobranca = _sem_nota
    _plataforma.context_note_for = _sem_nota

    W.whatsapp_service = EnvioQueConta()
    W.integration_service = H.ServicoDeIntegracaoFalso(H.integracao())
    W.LangChainService = ModeloDuble
    W.get_or_create_conversation = _conversa_fixa
    W.process_image_for_vision = _subir_foto
    VS.describe_image = _descrever

    ESTADO.clear()
    ESTADO.update({"latencia": float(latencia), "geracoes": [], "visoes": 0})
    EM_VOO_VISAO[0] = EM_VOO_VISAO[1] = 0
    PARADOS.clear()
    return servico


def _texto(t: float, texto: str) -> tuple:
    return (t, {"text": {"message": texto}})


def _foto(t: float, n: int, legenda: str = "") -> tuple:
    return (t, {"image": {"imageUrl": "https://wa.invalido/foto-%02d.jpg" % n,
                          "caption": legenda}})


async def _simular(eventos, duracao_s: int) -> None:
    """A varredura de 1 s do produto, sobre o relógio dublado.

    A cada segundo: entram as mensagens daquele segundo (pela entrada REAL do
    webhook), dispara UMA varredura REAL, e o relógio só anda quando cada
    varredura em voo terminou ou está parada numa espera dublada.
    """
    fila = sorted(eventos, key=lambda e: e[0])
    varreduras: list = []
    n_msg = 0
    for segundo in range(int(duracao_s) + 1):
        while fila and fila[0][0] <= segundo:
            _quando, corpo = fila.pop(0)
            n_msg += 1
            entrada = {"connectedPhone": "554800000000", "phone": TELEFONE,
                       "isGroup": False, "fromMe": False,
                       "messageId": "WAMSG-S5-%03d" % n_msg,
                       "senderName": "Segurado", "_integration_id": INTEGRACAO}
            entrada.update(corpo)
            await W._buffer_or_dispatch_text(entrada, TELEFONE)

        dono = "varredura-%d" % segundo

        async def _varrer(dono=dono):
            DONO.set(dono)
            return await BP.processar_buffers_prontos(
                [CHAVE], M._buffer_service_instance,
                W.process_whatsapp_message_background)

        varreduras.append((dono, asyncio.create_task(_varrer())))

        limite = time.monotonic() + 20.0
        while True:
            vivas = [d for d, tarefa in varreduras if not tarefa.done()]
            paradas = set(PARADOS.values())
            if all(d in paradas for d in vivas):
                break
            if time.monotonic() > limite:
                raise AssertionError("o turno não parou numa espera em 20 s reais")
            await asyncio.sleep(0.002)
        RELOGIO[0] = RELOGIO[0] + timedelta(seconds=1)
    for _d, tarefa in varreduras:
        await tarefa


def _o_que_este_arquivo_troca() -> list:
    import app.services.atlas.attendance_capture as _captura
    import app.services.billing_gate as _porteira
    import app.services.billing_replies as _cobranca
    import app.services.platform_outbound as _plataforma

    return [(M, "datetime"), (M, "_buffer_service_instance"),
            (W, "whatsapp_service"), (W, "integration_service"),
            (W, "LangChainService"), (W, "get_or_create_conversation"),
            (W, "process_image_for_vision"), (VS, "describe_image"),
            (_porteira, "pode_consumir"), (_cobranca, "contexto_de_cobranca"),
            (_cobranca, "telefones_da_equipe_de_cobranca"),
            (_plataforma, "context_note_for"),
            (_captura, "attendance_agent_active")]


def rodar(eventos, *, latencia: float, duracao_s: int = 120) -> dict:
    """Roda o cenário e DEVOLVE o mundo como achou. ⚠️ Sem isto o relógio
    dublado ficava em `M.datetime` e envenenava o arquivo seguinte da bateria
    (📊 01/10/2026: 3 guardas vizinhos vermelhos no mesmo processo)."""
    _motor()
    import app.services.o_fim_do_atendimento as _fim

    guardado = [(alvo, nome, getattr(alvo, nome))
                for alvo, nome in _o_que_este_arquivo_troca()]
    # o memo "uma linha de silêncio por conversa/dia" é do PROCESSO: a conversa
    # sintética "real" é a mesma dos guardas vizinhos — devolve como achou.
    # E o memo da LEITURA LARGA da janela (vale `_TURNO_SEGUNDOS`, chave = o
    # banco do harness + "real"): 📊 01/10/2026, sem esta devolução o guarda
    # `test_a_janela_esta_ligada_nos_portoes` rodado logo depois lia as falas
    # DESTE arquivo e ficava vermelho ("o silêncio virou UMA linha": 0).
    memos = [(d, dict(d)) for d in (_fim._SILENCIO_JA_ANOTADO,
                                    _fim._MEMO_DA_LEITURA_LARGA)]
    try:
        _preparar(latencia)
        asyncio.run(_simular(eventos, duracao_s))
        return _colher()
    finally:
        for alvo, nome, valor in guardado:
            setattr(alvo, nome, valor)
        for d, antes in memos:
            d.clear()
            d.update(antes)


def _colher() -> dict:
    envio = W.whatsapp_service
    linhas = H.banco().linhas("messages")
    return {
        "enviados": list(envio.enviados),
        "geracoes": list(ESTADO["geracoes"]),
        "visoes": ESTADO["visoes"],
        "pico_visao": EM_VOO_VISAO[1],
        "linhas_do_segurado": [l for l in linhas if l.get("role") == "user"],
        "linhas_do_agente": [l for l in linhas if l.get("role") == "assistant"],
        "buffer_sobrou": M._buffer_service_instance.redis._vivo(CHAVE),
    }


# ===========================================================================
# OS CENÁRIOS (mensagens 100% sintéticas)
# ===========================================================================
CINCO_FRASES = ["oi bom dia", "bati o carro", "to na BR 101 perto do posto",
                "ninguem se machucou", "o que eu faco"]
#: os intervalos da ordem: 4 / 9 / 6 / 12 s
CINCO_FRASES_T = [0, 4, 13, 19, 31]
EXPLICACAO = "essas sao as fotos do vidro quebrado"


def eventos_cinco_frases():
    return [_texto(t, f) for t, f in zip(CINCO_FRASES_T, CINCO_FRASES)]


def eventos_oito_fotos():
    return [_foto(4 * k, k + 1) for k in range(8)] + [_texto(30, EXPLICACAO)]


def eventos_nova_durante_a_geracao():
    return [_texto(0, "bati o carro na esquina."), _texto(10, "ninguem se machucou")]


def eventos_uma_so():
    return [_texto(0, "bati o carro na esquina.")]


def _sentida(r: dict) -> dict:
    """A geração cuja resposta SAIU."""
    if len(r["enviados"]) != 1:
        return {}
    n = int(str(r["enviados"][0]["texto"]).split("-")[-1])
    return next((g for g in r["geracoes"] if g["n"] == n), {})


# ---------------------------------------------------------------------------
# Os GUARDAS — devolvem a lista do que falhou (vazia = verde). É o que deixa a
# mutação provar que eles CONSEGUEM ficar vermelhos (CLAUDE.md §9.3/§9.5).
# ---------------------------------------------------------------------------
def guarda_cinco_frases(r: dict) -> list:
    falhas = []
    if len(r["enviados"]) != 1:
        falhas.append("respostas enviadas = %d (esperado 1)" % len(r["enviados"]))
        return falhas
    leu = _sentida(r).get("leu", "")
    for frase in CINCO_FRASES:
        if leu.count(frase) != 1:
            falhas.append("a resposta enviada leu %r %d vez(es)" % (frase, leu.count(frase)))
    if "5 mensagens seguidas" not in leu:
        falhas.append("o modelo não soube que eram 5 mensagens seguidas")
    chat = "\n".join(str(l.get("content")) for l in r["linhas_do_segurado"])
    for frase in CINCO_FRASES:
        if chat.count(frase) != 1:
            falhas.append("o chat da corretora tem %r %d vez(es)" % (frase, chat.count(frase)))
    if len(r["linhas_do_agente"]) != 1:
        falhas.append("linhas do agente no chat = %d (uma resposta retida foi gravada?)"
                      % len(r["linhas_do_agente"]))
    if r["buffer_sobrou"]:
        falhas.append("sobrou mensagem no buffer sem resposta")
    return falhas


def guarda_oito_fotos(r: dict) -> list:
    falhas = []
    if len(r["enviados"]) != 1:
        falhas.append("respostas enviadas = %d (esperado 1)" % len(r["enviados"]))
        return falhas
    leu = _sentida(r).get("leu", "")
    for k in range(1, 9):
        if ("foto %d de 8" % k) not in leu or ("foto-%02d.jpg" % k) not in leu:
            falhas.append("a foto %d não chegou descrita e numerada" % k)
    if EXPLICACAO not in leu:
        falhas.append("a explicação não chegou na mesma resposta das fotos")
    if "9 mensagens seguidas (8 fotos)" not in leu:
        falhas.append("o modelo não soube que eram 9 mensagens (8 fotos)")
    urls = []
    for linha in r["linhas_do_segurado"]:
        urls.extend((linha.get("payload") or {}).get("image_urls") or [])
    if sorted(set(urls)) != ["https://storage.invalido/foto-%02d.jpg" % k for k in range(1, 9)]:
        falhas.append("as 8 URLs não foram guardadas (%d)" % len(set(urls)))
    if r["pico_visao"] > M_MIDIAS() or r["pico_visao"] < 2:
        falhas.append("visão simultânea = %d (esperado 2..%d)" % (r["pico_visao"], M_MIDIAS()))
    if r["visoes"] != 8:
        falhas.append("chamadas de visão = %d (esperado 8: nenhuma foto descrita 2x)"
                      % r["visoes"])
    return falhas


def guarda_nova_durante_a_geracao(r: dict) -> list:
    falhas = []
    textos = [e["texto"] for e in r["enviados"]]
    if "RESPOSTA-1" in textos:
        falhas.append("a 1ª resposta SAIU mesmo com mensagem nova chegando durante a geração")
    if len(textos) != 1:
        falhas.append("respostas enviadas = %d (esperado 1)" % len(textos))
        return falhas
    leu = _sentida(r).get("leu", "")
    if "bati o carro na esquina." not in leu or "ninguem se machucou" not in leu:
        falhas.append("a resposta enviada não leu as duas mensagens")
    if "NÃO foi enviada" not in leu:
        falhas.append("o modelo não soube que a resposta anterior não saiu")
    return falhas


def M_MIDIAS() -> int:
    return int(W.MIDIAS_SIMULTANEAS_DO_TURNO)


class _Mutacao:
    """Troca um nome por um tempo e DEVOLVE — a árvore nunca é tocada."""

    def __init__(self, *trocas):
        self.trocas = trocas
        self.guardado = []

    def __enter__(self):
        _motor()
        for alvo, nome, valor in self.trocas:
            alvo = globals()[alvo] if isinstance(alvo, str) else alvo
            self.guardado.append((alvo, nome, getattr(alvo, nome)))
            setattr(alvo, nome, valor)
        return self

    def __exit__(self, *_):
        for alvo, nome, valor in reversed(self.guardado):
            setattr(alvo, nome, valor)


async def _nunca_retem(*_a, **_k):
    return False


SEM_A_4A_PERGUNTA = ("W", "_segurar_se_a_rajada_continuou", _nunca_retem)
TETO_DE_25 = ("M", "TETO_DA_RAJADA_ESTENDIDO_SEGUNDOS", 25)
VISAO_EM_SERIE = ("W", "MIDIAS_SIMULTANEAS_DO_TURNO", 1)


# ===========================================================================
# OS TESTES
# ===========================================================================
def test_r1_cinco_frases_com_a_digitacao_real_viram_uma_resposta():
    r = rodar(eventos_cinco_frases(), latencia=MODELO_P50_S)
    assert not guarda_cinco_frases(r), guarda_cinco_frases(r)


def test_r1b_cinco_frases_com_o_modelo_lento_tambem():
    r = rodar(eventos_cinco_frases(), latencia=MODELO_P90_S)
    assert not guarda_cinco_frases(r), guarda_cinco_frases(r)


def test_r2_oito_fotos_e_a_explicacao_viram_uma_resposta():
    r = rodar(eventos_oito_fotos(), latencia=MODELO_P50_S)
    assert not guarda_oito_fotos(r), guarda_oito_fotos(r)


def test_r3_mensagem_nova_durante_a_geracao_segura_a_primeira_resposta():
    r = rodar(eventos_nova_durante_a_geracao(), latencia=MODELO_P50_S)
    assert not guarda_nova_durante_a_geracao(r), guarda_nova_durante_a_geracao(r)
    assert len(r["geracoes"]) == 2


def test_r4_controle_uma_mensagem_so_sai_no_mesmo_segundo_de_hoje():
    """LINHA DE CONTROLE: o caso comum não pode ficar mais lento à toa."""
    depois = rodar(eventos_uma_so(), latencia=MODELO_P50_S)
    with _Mutacao(SEM_A_4A_PERGUNTA, TETO_DE_25, VISAO_EM_SERIE):
        antes = rodar(eventos_uma_so(), latencia=MODELO_P50_S)
    assert len(depois["enviados"]) == 1 and len(antes["enviados"]) == 1
    assert depois["enviados"][0]["t"] == antes["enviados"][0]["t"], (
        depois["enviados"], antes["enviados"])
    # janela de 8 s + o modelo (5,4 s, que o relógio de 1 s arredonda para cima)
    assert depois["enviados"][0]["t"] == 8 + 6
    assert len(depois["geracoes"]) == 1
    # e a linha do chat de uma mensagem só não ganhou nada (nem aviso, nem URL)
    linha = depois["linhas_do_segurado"][0]
    assert linha["content"] == "bati o carro na esquina."
    assert "image_urls" not in (linha.get("payload") or {})
    assert "mensagens seguidas" not in depois["geracoes"][0]["leu"]


def test_mut_a_sem_a_quarta_pergunta_os_guardas_ficam_vermelhos():
    with _Mutacao(SEM_A_4A_PERGUNTA):
        r1 = rodar(eventos_cinco_frases(), latencia=MODELO_P50_S)
        r3 = rodar(eventos_nova_durante_a_geracao(), latencia=MODELO_P50_S)
    assert guarda_cinco_frases(r1), "R1 continuou verde SEM a 4ª pergunta"
    assert guarda_nova_durante_a_geracao(r3), "R3 continuou verde SEM a 4ª pergunta"
    assert len(r1["enviados"]) >= 2 and "RESPOSTA-1" in [e["texto"] for e in r3["enviados"]]


def test_mut_b_com_o_teto_de_25_s_as_oito_fotos_viram_duas_respostas():
    with _Mutacao(TETO_DE_25, SEM_A_4A_PERGUNTA):
        r2 = rodar(eventos_oito_fotos(), latencia=MODELO_P50_S)
    assert guarda_oito_fotos(r2), "R2 continuou verde com o teto de 25 s"
    assert len(r2["enviados"]) == 2


def test_a_retencao_tem_teto_quem_escreve_sem_parar_e_respondido():
    """Uma mensagem a cada 5 s por 2 minutos: a resposta sai depois de no
    máximo REPLANEJAMENTOS_MAX retenções — ninguém fica sem resposta."""
    eventos = [_texto(5 * k, "mensagem numero %d" % (k + 1)) for k in range(24)]
    r = rodar(eventos, latencia=MODELO_P50_S, duracao_s=200)
    retidas = len(r["geracoes"]) - len(r["enviados"])
    assert r["enviados"], "ninguém respondeu quem escreve sem parar"
    assert r["enviados"][0]["t"] <= 80, r["enviados"][0]
    assert retidas <= M.REPLANEJAMENTOS_MAX * len(r["enviados"]), (retidas, len(r["enviados"]))
    assert not r["buffer_sobrou"]


# ===========================================================================
# AS MEDIDAS — ANTES (4ª pergunta fora, teto 25 s, visão em série) × DEPOIS
# ===========================================================================
def medir() -> list:
    casos = [
        ("5 frases 4/9/6/12 s · modelo p50", eventos_cinco_frases, MODELO_P50_S),
        ("5 frases 4/9/6/12 s · modelo p90", eventos_cinco_frases, MODELO_P90_S),
        ("8 fotos a cada 4 s + explicação", eventos_oito_fotos, MODELO_P50_S),
        ("msg nova durante a geração", eventos_nova_durante_a_geracao, MODELO_P50_S),
        ("CONTROLE: uma mensagem só", eventos_uma_so, MODELO_P50_S),
    ]
    saida = []
    for nome, eventos, lat in casos:
        with _Mutacao(SEM_A_4A_PERGUNTA, TETO_DE_25, VISAO_EM_SERIE):
            a = rodar(eventos(), latencia=lat)
        d = rodar(eventos(), latencia=lat)
        saida.append((nome, a, d))
    return saida


def main() -> int:
    print("SPEC-125 S5 — ANTES × DEPOIS (o mesmo motor; ANTES = sem a 4ª pergunta,"
          " teto 25 s, visão em série)")
    for nome, a, d in medir():
        print("  %-36s respostas %d -> %d · 1ª resposta em %s -> %s s · última em %s -> %s s"
              " · gerações %d -> %d" % (
                  nome, len(a["enviados"]), len(d["enviados"]),
                  a["enviados"][0]["t"] if a["enviados"] else "-",
                  d["enviados"][0]["t"] if d["enviados"] else "-",
                  a["enviados"][-1]["t"] if a["enviados"] else "-",
                  d["enviados"][-1]["t"] if d["enviados"] else "-",
                  len(a["geracoes"]), len(d["geracoes"])))
    falhas = 0
    for nome, teste in sorted(globals().items()):
        if nome.startswith("test_") and callable(teste):
            try:
                teste()
                print("  OK  %s" % nome)
            except AssertionError as erro:
                falhas += 1
                print("  X   %s — %s" % (nome, str(erro)[:400]))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
