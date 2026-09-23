# -*- coding: utf-8 -*-
"""O RELÓGIO DO MODELO — teto por chamada, o que é transitório, e o breaker por provedor.

SPEC-EXTRA-001.8 · BLOCO C (§7). **Uma corretora não trava a outra.**

🔴 O DEFEITO QUE ESTE ARQUIVO FECHA. Uma chamada ao modelo que fica pendurada
segura a vaga de atendimento até o SDK desistir por conta própria — e o default
do SDK é dele, não nosso. 📊 21/09/2026, `grep -n "timeout\\|max_retries"
app/factories/llm_factory.py` devolvia **ZERO** linhas: a fábrica passava
`model`, `max_tokens`, `api_key`, `callbacks`, `streaming` e `temperature`, e
mais nada. Enquanto uma corretora esperava esse tempo, a mensagem da outra
ficava na fila atrás dela.

⛔ ESTE ARQUIVO NÃO É UMA FÁBRICA NOVA (CLAUDE.md §5). Ele não cria nem escolhe
modelo: só diz **quanto tempo** uma chamada pode durar, **o que** merece ser
repetido e **quando** parar de bater num provedor que está fora do ar. A única
fábrica continua sendo `app/factories/llm_factory.py`.

⛔ E NÃO É O BREAKER DE PORTAIS DA EXTRA-001.6. Aquele é por conta de portal
(`portal_accounts.health`), mora no `portal-worker` e o meio-aberto dele é o
gesto humano de salvar a senha nova. Este é por PROVEDOR de LLM, mora no
`smith-api` e volta por relógio. 📊 21/09/2026,
`grep -rn -i "breaker|backoff|full.jitter" app --include=*.py -l` devolveu 13
arquivos e **nenhum** helper genérico de breaker: o que existe é
`whatsapp/channel_state.py:313 espera_do_backoff` (backoff de RECONEXÃO de
canal, fixo, sem jitter, teto 30 min) e o backoff da fila de Work Runs
(`work/queue.py:221`). Nenhum dos dois é o relógio de uma chamada de LLM.
A consolidação dos três num helper só fica registrada como pendência — esticar
o de canal para servir de breaker de provedor seria esticar a peça errada.

O QUE O SDK JÁ FAZ, MEDIDO — e por isso NÃO se empilha um segundo laço aqui
------------------------------------------------------------------------
📊 21/09/2026, lido no fonte instalado (openai 2.54.0 · anthropic 0.116.0):

  `openai/_base_client.py:821 _should_retry` e `anthropic/_base_client.py:842`
  repetem 408, 409, 429 e >= 500, obedecem `x-should-retry`, e terminam em
  `return False` — ou seja, **400/401/403/404 NÃO são repetidos**.
  `anthropic/_base_client.py:877 _should_retry_exception` repete também
  `APIConnectionError`/`APITimeoutError`, andando pela cadeia de `__cause__`.

Isso é exatamente a regra da SPEC §7.3. Um segundo laço de retry por cima
daria 3 × 3 = 9 tentativas — justamente o atraso que esta SPEC existe para
matar. Então aqui ficam só (a) a CLASSIFICAÇÃO que o breaker usa, (b) o
backoff full-jitter como função pura e (c) o breaker.

⚠️ A EXCEÇÃO MEDIDA — GOOGLE. `langchain_google_genai/chat_models.py:176-205`
monta o retry do tenacity com
`retry_if_exception_type(ResourceExhausted) | ServiceUnavailable | GoogleAPIError`,
e 📊 `issubclass(Unauthenticated, GoogleAPIError) is True`. Ou seja: **o SDK do
Google repete credencial recusada**, e o default dele é `max_retries=6`
(`chat_models.py:177`) — seis voltas com espera exponencial de até 60 s. Baixar
para `LLM_MAX_RETRIES` (2) corta o estrago de ~63 s para ~3 s, mas não conserta
a classificação do SDK: isso vai como pendência.

Rollback: `LLM_TIMEOUT_SEGUNDOS=0` faz a fábrica **não passar** o kwarg e o SDK
volta a decidir sozinho. `LLM_BREAKER_FALHAS=0` desliga o breaker.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


def _inteiro(nome: str, padrao: int) -> int:
    try:
        return int(str(os.getenv(nome, padrao)).strip())
    except (TypeError, ValueError):
        return padrao


def _decimal(nome: str, padrao: float) -> float:
    try:
        return float(str(os.getenv(nome, padrao)).strip())
    except (TypeError, ValueError):
        return padrao


#: 🔴 O TETO POR CHAMADA. 📊 21/09/2026, produção: o TURNO inteiro do chat tem
#: mediana 39 s, p95 107 s e máximo 136 s (n=41). ⚠️ Turno NÃO é chamada: um
#: turno tem várias idas ao modelo mais as ferramentas do meio, por isso a regra
#: "p95 × 3" da proposta de 13/09 NÃO se aplica ao teto por chamada — ela daria
#: 321 s, cinco minutos e meio de vaga presa. 90 s por chamada cobre a chamada
#: mais lenta que já medimos com folga e ainda devolve a vaga dentro do turno.
#: Remedir quando o atendimento gravar `payload.turn` (pendência).
#:
#: ⚠️ STREAMING NÃO É CORTADO POR ISTO. Os SDKs entregam este número ao httpx
#: como `httpx.Timeout(90)`, e o `read` do httpx é o tempo **entre dois
#: pedaços** — não o total. Uma resposta longa que segue emitindo delta não
#: bate no teto; uma que emudece, bate. É o relógio de SILÊNCIO que a §7.2
#: pede, cobrado uma camada abaixo.
TIMEOUT_S = _decimal("LLM_TIMEOUT_SEGUNDOS", 90.0)

#: Quantas voltas o SDK pode dar sozinho. 2 = até 3 tentativas no total.
#: ⚠️ Negativo = não passa o kwarg (o SDK decide). `0` é valor legítimo: uma
#: tentativa e pronto.
MAX_RETRIES = _inteiro("LLM_MAX_RETRIES", 2)

#: O breaker por provedor. `LLM_BREAKER_FALHAS=0` desliga.
BREAKER_FALHAS = _inteiro("LLM_BREAKER_FALHAS", 5)
BREAKER_JANELA_S = _inteiro("LLM_BREAKER_JANELA_SEGUNDOS", 60)
BREAKER_SEGUNDOS = _inteiro("LLM_BREAKER_SEGUNDOS", 120)
#: Quanto tempo o estado "meio-aberto" dura depois que o aberto vence. Sem esta
#: janela não existe sonda: a chave sumiria e todo mundo passaria de uma vez.
BREAKER_MEIO_S = _inteiro("LLM_BREAKER_MEIO_SEGUNDOS", 60)
#: Quanto tempo a sonda segura a vez. Se o processo que pegou a sonda morrer sem
#: reportar, ela vence e outro tenta — nunca fica ninguém de sonda para sempre.
BREAKER_SONDA_S = _inteiro("LLM_BREAKER_SONDA_SEGUNDOS", 30)

#: Backoff full-jitter da §7.3: espera = random(0, base · 2ⁿ), teto 30 s.
BACKOFF_BASE_S = _decimal("LLM_BACKOFF_BASE_SEGUNDOS", 2.0)
BACKOFF_TETO_S = _decimal("LLM_BACKOFF_TETO_SEGUNDOS", 30.0)

#: 🔴 O TETO DE TODO CLIENTE HTTP QUE NÃO TINHA NENHUM (§7.5). 💭 30 s de leitura
#: e 10 s de conexão: são chamadas de controle (MCP, OAuth), não de atendimento.
#: Um cliente sem `timeout` é um cliente que espera para sempre — o default do
#: httpx é 5 s, mas só de CONEXÃO quando construído via `httpx.Client`; o
#: `AsyncClient()` sem argumento usa `Timeout(5.0)` em tudo... e qualquer
#: mudança de versão do httpx muda isso sem avisar. Escrever o número é o que
#: impede a biblioteca de decidir por nós.
TIMEOUT_HTTP_S = _decimal("HTTP_TIMEOUT_SEGUNDOS", 30.0)
TIMEOUT_HTTP_CONEXAO_S = _decimal("HTTP_TIMEOUT_CONEXAO_SEGUNDOS", 10.0)

def _provedores_do_catalogo() -> tuple:
    """Os provedores que têm modelo de CONVERSA usável no catálogo (SPEC-116 U6d).

    ⚠️ Lido do SNAPSHOT versionado (`modelos_snapshot.json`), não do banco: este
    módulo é importado cedo e a varredura do breaker itera esta tupla — nenhuma
    consulta ao banco na importação. O snapshot é gerado do banco
    (`scripts/gerar_snapshot_de_modelos.py`). Os quatro de sempre vêm primeiro e
    nunca saem (o breaker deles já tem chave no Redis de produção).
    """
    base = ["openai", "anthropic", "google", "openrouter"]
    try:
        import json

        from app.factories.model_policy import LIFECYCLES_USAVEIS, SNAPSHOT_PATH

        cat = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")).get("catalogo") or {}
        for linha in cat.values():
            prov = str(linha.get("provider") or "").strip().lower()
            if (prov and prov not in base and linha.get("tipo") == "chat"
                    and linha.get("lifecycle") in LIFECYCLES_USAVEIS):
                base.append(prov)
    except Exception as exc:  # noqa: BLE001 — sem snapshot, os quatro de sempre
        logger.warning("[RelogioDoModelo] catálogo indisponível (%s) — só os 4 provedores de "
                       "sempre", type(exc).__name__)
    return tuple(base)


PROVEDORES = _provedores_do_catalogo()


def timeout_http() -> httpx.Timeout:
    """O teto padrão de um `httpx.AsyncClient` do backend."""
    return httpx.Timeout(TIMEOUT_HTTP_S, connect=TIMEOUT_HTTP_CONEXAO_S)


# ===========================================================================
# O TETO POR CHAMADA — o que a fábrica passa aos QUATRO construtores
# ===========================================================================
#
# ⚠️ O NOME DO KWARG É MEDIDO, NÃO PRESUMIDO. 📊 21/09/2026, nas versões
# instaladas (langchain-openai 1.0.3 · langchain-anthropic 1.1.0 ·
# langchain-google-genai 3.1.0), lido por `Classe.model_fields`:
#
#     ChatOpenAI                campo `request_timeout`          alias `timeout`
#     ChatAnthropic             campo `default_request_timeout`  alias `timeout`
#     ChatGoogleGenerativeAI    campo `timeout`                  alias `request_timeout`
#     todos                     campo `max_retries`  (Anthropic default 2, Google 6)
#
# Os três aceitam o alias `timeout=` na construção — por isso UM dicionário só
# serve aos quatro construtores. O guarda lê o ATRIBUTO do objeto construído,
# com o nome certo de cada classe; ler o fonte provaria só que a linha existe.
def kwargs_de_relogio() -> dict:
    """O teto e o número de voltas, prontos para `Chat*(**params)`.

    Dicionário VAZIO quando o relógio está desligado — e desligado é o rollback:
    o SDK volta ao default dele, exatamente como antes desta SPEC.
    """
    kwargs: dict = {}
    if TIMEOUT_S and TIMEOUT_S > 0:
        kwargs["timeout"] = TIMEOUT_S
    if MAX_RETRIES >= 0:
        kwargs["max_retries"] = MAX_RETRIES
    return kwargs


# ===========================================================================
# A CLASSIFICAÇÃO — o que merece outra tentativa, e o que não merece nenhuma
# ===========================================================================
#: Status HTTP que valem outra tentativa. É a mesma lista que os dois SDKs
#: aplicam (📊 `openai/_base_client.py:842-861`), escrita aqui porque o BREAKER
#: precisa da decisão mesmo quando o erro chega pelo callback, já embrulhado.
_STATUS_TRANSITORIO = (408, 409, 429)

#: 🔴 Definitivo, nunca transitório. Repetir um 401 queima a cota da corretora e
#: atrasa todo mundo — e nenhuma espera conserta uma chave errada.
_STATUS_DEFINITIVO = (400, 401, 403, 404, 422)

#: Classes de erro que dizem "a rede piscou" em qualquer um dos SDKs, sem que a
#: gente precise importar openai, anthropic e google só para um isinstance.
_NOMES_TRANSITORIOS = (
    "timeout", "timedout", "connection", "connect", "ratelimit",
    "serviceunavailable", "internalserver", "overloaded", "apistatus",
    "resourceexhausted", "toomanyrequests", "remoteprotocol", "readerror",
)

#: ⚠️ Estes CONTÊM "connect"/"permission" mas são veredito final. A ordem
#: importa: o nome definitivo é conferido ANTES do transitório.
_NOMES_DEFINITIVOS = (
    "authentication", "unauthenticated", "permissiondenied", "notfound",
    "badrequest", "invalidrequest", "unprocessable", "invalidargument",
)


def _status_de(exc: BaseException) -> Optional[int]:
    """O status HTTP escondido no erro, venha ele de qual SDK vier."""
    for atributo in ("status_code", "code", "status"):
        valor = getattr(exc, atributo, None)
        if isinstance(valor, bool):
            continue
        if isinstance(valor, int) and 100 <= valor <= 599:
            return valor
    resposta = getattr(exc, "response", None)
    valor = getattr(resposta, "status_code", None)
    if isinstance(valor, int) and 100 <= valor <= 599:
        return valor
    return None


def e_transitorio(exc: BaseException) -> bool:
    """Este erro merece outra tentativa — e conta para o breaker?

    🔴 O DEFAULT É **NÃO**. Um erro que não sabemos classificar quase sempre é
    defeito nosso (um `KeyError` no meio do prompt, um `ValueError` de parse), e
    abrir o breaker de um provedor por causa de um bug nosso seria exatamente o
    que esta SPEC evita: uma corretora derrubando o atendimento das outras.

    Anda pela cadeia de `__cause__` porque os SDKs embrulham (é o que o próprio
    `anthropic/_base_client.py:877` faz).
    """
    vistos: set = set()
    atual: Optional[BaseException] = exc
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))

        status = _status_de(atual)
        if status is not None:
            if status in _STATUS_DEFINITIVO:
                return False
            if status in _STATUS_TRANSITORIO or status >= 500:
                return True

        nome = type(atual).__name__.lower()
        if any(p in nome for p in _NOMES_DEFINITIVOS):
            return False
        if isinstance(atual, (asyncio.TimeoutError, TimeoutError,
                              ConnectionError, httpx.TimeoutException,
                              httpx.TransportError)):
            return True
        if any(p in nome for p in _NOMES_TRANSITORIOS):
            return True

        atual = atual.__cause__
    return False


def motivo_de_reserva(exc: BaseException) -> Optional[str]:
    """Este erro autoriza a RESERVA da rota? Devolve o motivo, ou `None`.

    SPEC-116 U6c / D-116-07: 429 · 5xx · timeout · conexão — o provedor não
    respondeu, e outro provedor pode responder. ⛔ 400/401/403/404/422 NÃO: um
    pedido que o provedor recusou é defeito nosso (ou da chave), e mandá-lo a
    outro modelo só esconderia o defeito. A decisão de SE pode (antes ou depois
    da 1ª tool com efeito) é de quem chama — este só classifica.
    """
    if not e_transitorio(exc):
        return None
    vistos: set = set()
    atual: Optional[BaseException] = exc
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        status = _status_de(atual)
        if status == 429:
            return "429"
        if status is not None and status >= 500:
            return "5xx"
        if status in (408, 409):
            return str(status)
        nome = type(atual).__name__.lower()
        if (isinstance(atual, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException))
                or "timeout" in nome or "timedout" in nome):
            return "timeout"
        atual = atual.__cause__
    return "conexao"


def espera_do_backoff(tentativa: int) -> float:
    """PURO: quantos segundos esperar antes da tentativa `n`. Full jitter.

    `espera = random(0, base · 2ⁿ)`, base 2 s, teto 30 s — a forma da §7.3.
    🔴 O SORTEIO NÃO É ENFEITE: sem ele, N processos que falharam juntos voltam
    juntos, e o provedor que já estava mal leva a mesma rajada de novo.

    ⚠️ HOJE ESTA FUNÇÃO NÃO TEM CHAMADOR NO PRODUTO, e isso está escrito de
    propósito: o retry de LLM é do SDK (ver o cabeçalho), e empilhar um segundo
    laço seria o atraso que a SPEC mata. Ela existe testada para quem for
    escrever a espera do lado de fora do SDK (a retenção da §8) — e enquanto não
    houver chamador, a pendência registra isso em vez de o código fingir que
    protege alguém.
    """
    if tentativa <= 0:
        return 0.0
    teto = min(BACKOFF_BASE_S * (2 ** (tentativa - 1)), BACKOFF_TETO_S)
    return random.uniform(0.0, teto)


# ===========================================================================
# O BREAKER POR PROVEDOR
# ===========================================================================
#
# 🔴 POR PROVEDOR, NÃO POR CORRETORA, e a razão é o isolamento: a Anthropic cair
# é fato do mundo, não da Resulta. Um breaker por corretora abriria N vezes pelo
# mesmo fato, e cada corretora pagaria N timeouts para descobrir sozinha o que a
# primeira já sabia.
#
# 🔴 E POR ISSO 401 NÃO ABRE NADA. 📊 21/09/2026, `app/core/utils.py:38-49`: a
# chave vem de `os.getenv("ANTHROPIC_API_KEY")` & cia — é GLOBAL hoje, e os 15
# chamadores de `create_llm` passam todos por `get_api_key_for_provider`. Mas o
# dia em que uma corretora trouxer a chave dela, um 401 dela abriria o provedor
# para TODAS: seria literalmente o defeito que esta SPEC tem no título. Além
# disso, nenhum relógio conserta chave errada — meio-aberto de 120 s em 120 s
# bateria na porta para sempre. Credencial recusada é assunto do dono da chave.
#
# ⛔ FAIL-OPEN, SEMPRE. Redis fora nunca pode calar o atendimento: sem Redis o
# breaker degrada para memória do processo, e com estado limpo ele **deixa
# passar**. Um breaker que fecha a porta porque o Redis caiu é um segundo
# incidente em cima do primeiro.
#
# ⛔ E BREAKER ABERTO NÃO VIRA SILÊNCIO. Quem PERGUNTA é quem RETÉM: este módulo
# só responde "pode?" — a mensagem do segurado fica guardada pelo processador
# (§8), e nada chega a ele. Ver a API pública no fim do arquivo.
_PREFIXO = "llm_breaker"


def _chaves(provedor: str) -> tuple:
    p = provedor_normalizado(provedor)
    return (f"{_PREFIXO}:{p}",            # aberto  (EX BREAKER_SEGUNDOS)
            f"{_PREFIXO}:{p}:meio",       # meio-aberto (EX BREAKER_SEGUNDOS+MEIO)
            f"{_PREFIXO}:{p}:sonda",      # SET NX: UMA sonda por vez
            f"{_PREFIXO}:{p}:falhas")     # INCR + EXPIRE na janela


def provedor_normalizado(provedor: Any) -> str:
    """O nome do provedor como chave — nunca vazio, nunca de duas formas.

    ⚠️ SPEC-116: um provedor fora da tupla NÃO vira mais "openai" — a falha do
    xAI contava no breaker da OpenAI (EVIDENCIAS/03 F6). Vazio continua sendo
    "openai" (o legado de agente sem provedor).
    """
    nome = str(provedor or "").strip().lower()
    return nome or "openai"


def provedor_configurado(company_config: Optional[dict],
                         agent_data: Optional[dict]) -> str:
    """O provedor que a fábrica VAI usar para este agente desta corretora.

    🔴 SPEC-116: é a MESMA pergunta que a fábrica faz — o Model Router
    (`LLMFactory.resolver_para`): a ROTA do papel pode ter trocado o provedor
    gravado no agente, e a costura precisa perguntar pelo breaker do provedor
    por onde a chamada VAI sair. Duas regras = pergunta por um, chamada por outro.
    Sem resposta do roteador (config inválida), o gravado — é só uma pergunta
    de leitura, e ela nunca levanta.
    """
    try:
        from app.factories.llm_factory import LLMFactory

        return provedor_normalizado(LLMFactory.resolver_para(company_config, agent_data).provider)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[RelogioDoModelo] roteador sem resposta (%s) — provedor gravado",
                     type(exc).__name__)
    fonte = agent_data if agent_data else (company_config or {})
    escolhido = fonte.get("llm_provider") or (company_config or {}).get("llm_provider")
    return provedor_normalizado(escolhido or "openai")


# --- o estado, e o degrau para memória quando o Redis falta ----------------
#: Memória de processo. ⚠️ Degradação declarada: sem Redis, cada processo
#: descobre a queda sozinho — o que é pior que compartilhar, e melhor que
#: bloquear ou explodir.
_MEMORIA: dict = {}


class _RedisDeMemoria:
    """Os cinco comandos que o breaker usa, com a semântica do Redis de verdade.

    ⛔ Não é um Redis: é o degrau de quando ele falta. `set(nx=, ex=)`, `get`,
    `exists`, `incr`, `expire`, `delete` — e o TTL vence pelo relógio.
    """

    def __init__(self, dados: dict):
        self.dados = dados

    def _vivo(self, chave):
        item = self.dados.get(chave)
        if item is None:
            return None
        valor, expira = item
        if expira is not None and _agora() >= expira:
            self.dados.pop(chave, None)
            return None
        return valor

    async def get(self, chave):
        return self._vivo(chave)

    async def exists(self, chave):
        return 1 if self._vivo(chave) is not None else 0

    async def set(self, chave, valor, ex=None, nx=False):
        if nx and self._vivo(chave) is not None:
            return None
        self.dados[chave] = (str(valor), (_agora() + ex) if ex else None)
        return True

    async def incr(self, chave):
        atual = self._vivo(chave)
        novo = int(atual or 0) + 1
        expira = self.dados.get(chave, (None, None))[1] if atual is not None else None
        self.dados[chave] = (str(novo), expira)
        return novo

    async def expire(self, chave, segundos):
        if self._vivo(chave) is None:
            return 0
        self.dados[chave] = (self.dados[chave][0], _agora() + segundos)
        return 1

    async def delete(self, *chaves):
        return sum(1 for c in chaves if self.dados.pop(c, None) is not None)


def _agora() -> float:
    """O relógio, num lugar só — é por aqui que o guarda envelhece o breaker."""
    return time.monotonic()


_AVISOU_SEM_REDIS = [False]


async def _cliente():
    """O Redis, ou a memória do processo. ⛔ NUNCA levanta."""
    try:
        from app.core.redis import get_async_redis_client
        return await get_async_redis_client()
    except Exception as exc:  # noqa: BLE001
        if not _AVISOU_SEM_REDIS[0]:
            _AVISOU_SEM_REDIS[0] = True
            logger.warning(
                "[RelogioDoModelo] sem Redis (%s) — o breaker passa a valer "
                "só dentro deste processo", type(exc).__name__)
        return _RedisDeMemoria(_MEMORIA)


async def provedor_disponivel(provedor: str) -> bool:
    """Pode chamar este provedor agora?

    🔴 É a pergunta que a COSTURA faz ANTES de consumir o buffer — quem pergunta
    é quem retém a mensagem. Responder `False` aqui nunca vira "não entendi" ao
    segurado; vira mensagem guardada.

    Três respostas, nesta ordem:
      aberto      → False (o provedor está fora há menos de BREAKER_SEGUNDOS)
      meio-aberto → True para UMA sonda só (`SET NX`, o padrão do redis.io que
                    `portal_worker/leases.py:130-145` já roda em produção),
                    False para as outras
      fechado     → True
    """
    if BREAKER_FALHAS <= 0:
        return True
    aberto, meio, sonda, _ = _chaves(provedor)
    try:
        cliente = await _cliente()
        if await cliente.get(aberto):
            return False
        if not await cliente.exists(meio):
            return True
        # Meio-aberto: a vez é de quem conquistar a sonda, e de mais ninguém.
        conquistou = await cliente.set(sonda, "1", ex=BREAKER_SONDA_S, nx=True)
        return bool(conquistou)
    except Exception as exc:  # noqa: BLE001
        # ⛔ Fail-open: uma falha de infraestrutura nossa não cala o atendimento.
        logger.warning("[RelogioDoModelo] breaker indisponível (%s) — deixando "
                       "passar", type(exc).__name__)
        return True


async def registrar_sucesso(provedor: str) -> None:
    """Deu certo: o provedor está de pé e o breaker fecha.

    Também zera o contador — a regra é N falhas SEGUIDAS dentro da janela; uma
    resposta boa no meio prova que não era queda.
    """
    if BREAKER_FALHAS <= 0:
        return
    try:
        cliente = await _cliente()
        await cliente.delete(*_chaves(provedor))
    except Exception as exc:  # noqa: BLE001
        logger.debug("[RelogioDoModelo] sucesso não registrado (%s)",
                     type(exc).__name__)


async def registrar_falha(provedor: str, exc: BaseException) -> None:
    """Deu errado: conta a falha e, no limite, abre o breaker.

    🔴 SÓ O TRANSITÓRIO CONTA. 401/403/400/404 passam batido de propósito (ver o
    bloco acima): chave recusada é assunto de quem tem a chave, não queda de
    provedor — e abrir por causa dela seria uma corretora travando as outras.
    """
    if BREAKER_FALHAS <= 0:
        return
    if not e_transitorio(exc):
        # ⛔ Só o NOME do provedor e a CLASSE do erro. Chave, telefone e nome de
        # corretora nunca entram em log (CLAUDE.md §7, §13.3).
        logger.info("[RelogioDoModelo] %s: %s é definitivo — não conta para o "
                    "breaker", provedor_normalizado(provedor), type(exc).__name__)
        return

    aberto, meio, sonda, falhas = _chaves(provedor)
    try:
        cliente = await _cliente()
        # A sonda do meio-aberto falhou: reabre o relógio inteiro e devolve a
        # sonda, senão o provedor ficaria sendo sondado de 30 em 30 s.
        if await cliente.exists(meio) and not await cliente.get(aberto):
            await _abrir(cliente, aberto, meio, sonda, falhas)
            return
        n = await cliente.incr(falhas)
        if n == 1:
            await cliente.expire(falhas, BREAKER_JANELA_S)
        if n >= BREAKER_FALHAS:
            await _abrir(cliente, aberto, meio, sonda, falhas)
    except Exception as erro_infra:  # noqa: BLE001
        logger.warning("[RelogioDoModelo] falha não registrada (%s)",
                       type(erro_infra).__name__)


async def _abrir(cliente, aberto, meio, sonda, falhas) -> None:
    """Abre o breaker: barrado por BREAKER_SEGUNDOS, depois UMA sonda."""
    await cliente.set(aberto, str(int(time.time())), ex=BREAKER_SEGUNDOS)
    await cliente.set(meio, "1", ex=BREAKER_SEGUNDOS + BREAKER_MEIO_S)
    await cliente.delete(sonda, falhas)
    logger.warning("[RelogioDoModelo] breaker ABERTO por %ss", BREAKER_SEGUNDOS)


async def estado_do_breaker(provedor: str) -> dict:
    """O estado, para quem precisa CONTAR a coisa ao dono da corretora.

    `{"estado": "fechado"|"aberto"|"meio_aberto", "aberto_ha_s": int|None}` —
    é daqui que sai a frase "o provedor está fora do ar há N minutos".
    """
    aberto, meio, _sonda, _falhas = _chaves(provedor)
    try:
        cliente = await _cliente()
        marca = await cliente.get(aberto)
        if marca:
            try:
                ha = max(0, int(time.time()) - int(marca))
            except (TypeError, ValueError):
                ha = None
            return {"estado": "aberto", "aberto_ha_s": ha}
        if await cliente.exists(meio):
            return {"estado": "meio_aberto", "aberto_ha_s": None}
    except Exception as exc:  # noqa: BLE001
        logger.debug("[RelogioDoModelo] estado indisponível (%s)",
                     type(exc).__name__)
    return {"estado": "fechado", "aberto_ha_s": None}


# ===========================================================================
# QUEM ALIMENTA O BREAKER — o callback que a fábrica anexa
# ===========================================================================
#
# ⚖️ POR QUE UM CALLBACK, e não um embrulho no `ainvoke`: o callback vê TODA
# chamada de modelo do sistema — os 15 chamadores de `create_llm`, o nó `agent`,
# os subagentes e o streaming — porque é a fábrica que o anexa, no mesmo lugar
# onde o `CostCallbackHandler` já é o escritor único do custo. Um embrulho em
# `graph.ainvoke` veria só o chat. ⛔ O que o callback NÃO consegue é BLOQUEAR:
# quando ele roda, a chamada já saiu. Por isso alimentar e perguntar são duas
# peças: `provedor_disponivel()` é a porta, este é o sensor.
try:  # pragma: no cover - langchain sempre presente no produto
    from langchain_core.callbacks import AsyncCallbackHandler
except Exception:  # noqa: BLE001
    AsyncCallbackHandler = object  # type: ignore


class RelogioDoModeloCallback(AsyncCallbackHandler):  # type: ignore[misc]
    """Alimenta o breaker do provedor com o desfecho de cada chamada.

    É ASSÍNCRONO de propósito: o caminho do produto é `ainvoke`/`astream_events`,
    e o breaker escreve em Redis. Um handler síncrono teria de abrir um laço de
    eventos dentro do laço de eventos.

    ⛔ NUNCA derruba a resposta: toda falha aqui é log e segue. Perder uma
    medição é ruim; perder a resposta do corretor por causa dela é pior.
    """

    def __init__(self, provedor: str):
        super().__init__()
        self.provedor = provedor_normalizado(provedor)

    async def on_llm_end(self, response, **kwargs) -> None:  # noqa: D102, ANN001
        try:
            await registrar_sucesso(self.provedor)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[RelogioDoModelo] on_llm_end (%s)", type(exc).__name__)

    async def on_llm_error(self, error: BaseException, **kwargs) -> None:  # noqa: D102
        try:
            await registrar_falha(self.provedor, error)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[RelogioDoModelo] on_llm_error (%s)", type(exc).__name__)


# ===========================================================================
# A API PÚBLICA, para a fatia da costura
# ===========================================================================
#   provedor_configurado(company_config, agent_data) -> str
#   await provedor_disponivel(provedor) -> bool      # pergunte ANTES; False = RETENHA
#   await registrar_sucesso(provedor) -> None        # a fábrica já alimenta
#   await registrar_falha(provedor, exc) -> None     # a fábrica já alimenta
#   await estado_do_breaker(provedor) -> dict        # para a frase ao dono
#   e_transitorio(exc) -> bool ·  espera_do_backoff(n) -> float
#   motivo_de_reserva(exc) -> str|None   # SPEC-116: 429/5xx/timeout/conexão
__all__ = [
    "TIMEOUT_S", "MAX_RETRIES", "PROVEDORES",
    "kwargs_de_relogio", "timeout_http", "e_transitorio", "espera_do_backoff",
    "provedor_normalizado", "provedor_configurado",
    "provedor_disponivel", "registrar_sucesso", "registrar_falha",
    "estado_do_breaker", "RelogioDoModeloCallback", "motivo_de_reserva",
]
