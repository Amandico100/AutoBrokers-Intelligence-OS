"""
Message Buffer Service for WhatsApp message aggregation.

Implements debounce pattern to combine consecutive user messages
before processing with LLM, reducing API calls and improving response coherence.

ASYNC VERSION: All Redis operations are non-blocking.

SPEC-EXTRA-001.2 BLOCO AB — três coisas novas moram aqui, e nenhuma delas é
peça nova de infraestrutura (CLAUDE.md §5):

  A TRAVA DE TURNO   `whatsapp_turno:{escopo}:{telefone}` — MESMA chave do
                     buffer, com token e liberação por script que compara o
                     valor (Redis SET/locks, §20 E01). É o mesmo `SET NX EX`
                     que o webhook já usa para dedupe e o mesmo padrão de
                     claim-com-token do `route_sentinel`.
  A JANELA           duas funções PURAS (`tracos_da_mensagem` e
                     `janela_de_espera`) substituem a COMPARAÇÃO de
                     `should_process`. O mecanismo é o de sempre.
  OS ITENS           o buffer passa a guardar itens tipados (`v: 2`), porque
                     foto, áudio e documento entram nele. A leitura tolera o
                     formato antigo enquanto o TTL de 60 s drena.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import settings
from app.core.redis import get_async_redis_client

logger = logging.getLogger(__name__)


# =============================================================================
# A TRAVA DE TURNO — constantes
# =============================================================================
#: Irmão de `whatsapp_buffer`. O escopo é o MESMO (SPEC-063 Bloco H).
TURNO_PREFIXO = "whatsapp_turno"

#: 📊 Medido em 14/09/2026 sobre `conversation_logs.response_time_ms` (566
#: turnos): p50 5,4 s · p90 17,9 s · máx 53,4 s. 90 s é ~1,7x o máximo medido
#: — folga para o envio (que soma segundos) sem prender a conversa meio minuto
#: depois de um processo morrer. Decisão D-E0012-01.
TURNO_TTL_SEGUNDOS = max(5, int(getattr(settings, "TURNO_TTL_SEGUNDOS", 90) or 90))

#: E01 exige teto na renovação: um turno que renova para sempre é um turno que
#: nunca solta a conversa.
TURNO_RENOVACOES_MAX = max(0, int(getattr(settings, "TURNO_RENOVACOES_MAX", 3) or 0))

#: 🔴 O script LITERAL da documentação do Redis (§20 E01). ⛔ Nunca `DEL` cego:
#: um `DEL` sem comparar o valor apaga a trava de OUTRO turno — o que devolve
#: exatamente o defeito que a trava existe para matar.
LUA_LIBERA_SE_FOR_MEU = (
    'if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) '
    'else return 0 end'
)

#: Renovar é o mesmo desenho: só quem é dono estende.
LUA_RENOVA_SE_FOR_MEU = (
    'if redis.call("get",KEYS[1]) == ARGV[1] then '
    'return redis.call("expire",KEYS[1],ARGV[2]) else return 0 end'
)

#: O rótulo que `chave()` usa quando não há escopo nenhum. 🔴 Ele NÃO isola
#: corretoras — é por isso que `abrir_turno` o RECUSA (§5.3, opção A).
ESCOPO_SEM_INTEGRACAO = "sem-integracao"


@dataclass(frozen=True)
class Turno:
    """A posse de uma conversa enquanto uma resposta está sendo montada."""

    escopo: str
    phone: str
    token: str


# =============================================================================
# A JANELA QUE ESCUTA O CONTEÚDO — duas funções PURAS
# =============================================================================
#
# 🔴 São DUAS de propósito. `tracos_da_mensagem` é a única que lê TEXTO: ela
# roda sobre o acervo real, por script, e o que sai dela são traços. É o que
# permite medir no acervo sem versionar uma linha de conversa de segurado
# (§13). `janela_de_espera` decide, e é ela que roda no CI sobre o corpus.
#
# 📊 A distribuição que justifica três números, e não um (14/09/2026, sobre
# `attendance_transcripts.wa_timestamp`, 52.099 intervalos): 0-3 s 59,7% ·
# 3-8 s 15,5% · 8-18 s 16,3% · 18-25 s 5,8% · >25 s 2,9%. Uma janela fixa de
# 8 s agrega 75% e fragmenta o resto; uma de 18 s agrega 91% e cobra 18 s de
# TODA resposta, inclusive daquela em que o segurado só disse "sim".

#: 🔴 É o número da Meta (§20 E02: o indicador de digitação é descartado "after
#: 25 seconds"), e é o mesmo teto da rajada. Uma constante, duas vidas.
TETO_DA_RAJADA_SEGUNDOS = 25

JANELA_DADO_CURTO_SEGUNDOS = max(
    1, int(getattr(settings, "JANELA_DADO_CURTO_SEGUNDOS", 3) or 3))
JANELA_FRASE_COMPLETA_SEGUNDOS = max(
    1, int(getattr(settings, "JANELA_FRASE_COMPLETA_SEGUNDOS", 8) or 8))
JANELA_FRASE_INACABADA_SEGUNDOS = max(
    1, int(getattr(settings, "JANELA_FRASE_INACABADA_SEGUNDOS", 18) or 18))

#: Teto da re-leitura do buffer antes de gerar (§6.3).
REPLANEJAMENTOS_MAX = max(0, int(getattr(settings, "REPLANEJAMENTOS_MAX", 2) or 0))

#: <= N caracteres é pré-condição de "dado curto" — nunca a regra inteira.
DADO_CURTO_MAX_CHARS = 24

#: Lista FECHADA, em português. ⚠️ Fechada é a regra: um conectivo a mais é uma
#: frase a mais esperando 18 s, e isso se mede antes de acrescentar.
CONECTIVOS_FINAIS = frozenset({
    "e", "ou", "mas", "porem", "porém", "porque", "por", "pois", "que", "de",
    "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "para", "pra",
    "pro", "com", "sem", "ai", "aí", "entao", "então", "tipo", "sobre", "ate",
    "até", "desde", "como", "quando", "se", "num", "numa", "ao", "aos", "a",
    "o", "os", "as", "um", "uma", "meu", "minha", "seu", "sua", "esse", "essa",
    "este", "esta", "aquele", "aquela", "mais", "menos", "muito", "ja", "já",
})

#: Dois tokens: o começo de uma locução que não termina frase.
CONECTIVOS_FINAIS_DUPLOS = frozenset({
    "so que", "só que", "por que", "ja que", "já que", "sendo que", "mesmo que",
    "alem de", "além de", "depois de", "antes de", "por causa", "em vez",
})

#: Palavras de confirmação — o "sim" que fecha a rajada em 3 s.
CONFIRMACOES_CURTAS = frozenset({
    "sim", "nao", "não", "ok", "okay", "certo", "isso", "pode", "ta", "tá",
    "tah", "blz", "beleza", "claro", "perfeito", "exato", "correto",
    "positivo", "negativo", "aham", "uhum", "sim senhor", "pode sim",
    "tudo bem", "ta bom", "tá bom", "isso mesmo", "confirmo", "confirmado",
    "s", "n", "obrigado", "obrigada", "valeu", "certo isso",
})

_PONTUACAO_FINAL = ".!?…"

#: Faixas de emoji/pictograma. Um emoji no fim de uma frase é ponto final —
#: 📊 é assim que o segurado encerra no WhatsApp, e não com ".".
_FAIXAS_DE_EMOJI = (
    (0x1F000, 0x1FAFF), (0x2190, 0x21FF), (0x2600, 0x27BF), (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F), (0x2190, 0x2BFF),
)

_SO_DIGITOS_E_PONTUACAO = re.compile(r"^[\d\s\.\-\/,:()+]+$")

#: 🔴 UM token, sem espaço, com pelo menos um dígito: é IDENTIFICADOR — placa
#: (`ABC1D23`), CPF, CEP, protocolo, apólice, número de sinistro. Sem esta
#: linha, a placa caía em "frase inacabada" e o segurado esperava 18 s para
#: ouvir de volta o que respondeu em 2 — foi o guarda G2b que a encontrou.
_IDENTIFICADOR = re.compile(r"^[\wÀ-ÿ][\wÀ-ÿ\.\-\/]*$", re.UNICODE)
_NAO_PALAVRA = re.compile(r"[^\wÀ-ÿ]+", re.UNICODE)


def _e_emoji(ch: str) -> bool:
    ponto = ord(ch)
    return any(ini <= ponto <= fim for ini, fim in _FAIXAS_DE_EMOJI)


@dataclass(frozen=True)
class Tracos:
    """O que se sabe de uma mensagem SEM guardar o que ela diz."""

    n_chars: int
    termina_em_pontuacao_final: bool
    termina_em_conectivo: bool
    dado_curto: bool
    tipo: str = "text"


def tracos_da_mensagem(texto: Optional[str], *, tipo: str = "text") -> Tracos:
    """Roda sobre o TEXTO REAL. É esta função que o script de medição aplica
    ao acervo — e é a ÚNICA desta SPEC que lê texto (§13).

    ⛔ Não guarda, não loga e não devolve nenhum pedaço do texto.
    """
    bruto = str(texto or "")
    limpo = bruto.strip()
    n_chars = len(limpo)
    tipo_norm = str(tipo or "text").strip().lower() or "text"

    if not limpo:
        return Tracos(n_chars=0, termina_em_pontuacao_final=False,
                      termina_em_conectivo=False, dado_curto=False, tipo=tipo_norm)

    ultimo = limpo[-1]
    pont_final = ultimo in _PONTUACAO_FINAL or _e_emoji(ultimo)

    baixo = limpo.lower()
    palavras = [p for p in _NAO_PALAVRA.split(baixo) if p]
    conectivo = False
    if palavras and not pont_final:
        conectivo = palavras[-1] in CONECTIVOS_FINAIS
        if not conectivo and len(palavras) >= 2:
            conectivo = " ".join(palavras[-2:]) in CONECTIVOS_FINAIS_DUPLOS

    dado_curto = False
    if n_chars <= DADO_CURTO_MAX_CHARS:
        sem_pontuacao = baixo.strip(_PONTUACAO_FINAL + " ")
        nucleo = limpo.strip(_PONTUACAO_FINAL + " ")
        dado_curto = (
            bool(_SO_DIGITOS_E_PONTUACAO.match(limpo))
            or sem_pontuacao in CONFIRMACOES_CURTAS
            or bool(_IDENTIFICADOR.match(nucleo)
                    and any(c.isdigit() for c in nucleo)))

    return Tracos(n_chars=n_chars, termina_em_pontuacao_final=pont_final,
                  termina_em_conectivo=conectivo, dado_curto=dado_curto,
                  tipo=tipo_norm)


def janela_de_espera(t: Tracos) -> int:
    """Segundos de ociosidade que fecham a rajada. PURA: sem I/O, sem banco.

    🔴 O piso `max(...DEBOUNCE..., 8)` que morreu aqui tornava a
    janela de 3 s impossível por CONSTRUÇÃO — nenhuma configuração descia dela.
    """
    # mídia sem legenda: o segurado quase sempre manda a explicação logo atrás
    if t.tipo != "text" and t.n_chars == 0:
        return JANELA_FRASE_COMPLETA_SEGUNDOS
    # documento: o texto extraído é longo e não diz nada sobre o ritmo de quem
    # o enviou — os traços dele seriam os do PDF, não os da pessoa
    if t.tipo == "document":
        return JANELA_FRASE_COMPLETA_SEGUNDOS
    if t.dado_curto:
        return JANELA_DADO_CURTO_SEGUNDOS
    if t.termina_em_pontuacao_final and not t.termina_em_conectivo:
        return JANELA_FRASE_COMPLETA_SEGUNDOS
    return JANELA_FRASE_INACABADA_SEGUNDOS


def partes_da_chave(chave: str) -> tuple:
    """`whatsapp_buffer:{escopo}:{telefone}` -> `(escopo, telefone)`."""
    texto = str(chave or "")
    if ":" not in texto:
        return "", texto
    _prefixo, resto = texto.split(":", 1)
    if ":" not in resto:
        return "", resto
    escopo, phone = resto.rsplit(":", 1)
    return escopo, phone


def itens_do_buffer(buffer: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Os itens do buffer no formato v2 — ou os textos do v1 convertidos.

    🔴 A compatibilidade dura <= 60 s (`BUFFER_TTL_SECONDS`), o tempo de drenar
    o que estava no Redis quando o deploy subiu. Não é ponte permanente.
    """
    dados = buffer or {}
    itens = dados.get("itens")
    if isinstance(itens, list):
        return [i for i in itens if isinstance(i, dict)]
    return [{"tipo": "text", "texto": str(m or "")}
            for m in (dados.get("messages") or [])]


def texto_do_item(item: Dict[str, Any]) -> str:
    """O que este item DIZ — legenda incluída. Vazio quando é mídia muda."""
    dados = item or {}
    return str(dados.get("texto") or dados.get("legenda") or "")


#: O que o prompt vê no lugar de uma mídia sem legenda. ⚠️ A DESCRIÇÃO da
#: imagem e a TRANSCRIÇÃO do áudio acontecem no TURNO (webhook), não aqui: este
#: módulo não faz I/O de rede.
MARCA_DE_MIDIA = {
    "image": "🖼️ [Imagem enviada]",
    "audio": "[Mensagem de voz]",
    "document": "[Documento enviado]",
}


def texto_combinado_dos_itens(itens: List[Dict[str, Any]]) -> str:
    """O texto que vai ao modelo — mídia muda vira marca, nunca linha vazia."""
    linhas = []
    for item in itens or []:
        texto = texto_do_item(item).strip()
        if texto:
            linhas.append(texto)
            continue
        marca = MARCA_DE_MIDIA.get(str((item or {}).get("tipo") or "").lower())
        if marca:
            linhas.append(marca)
    return "\n".join(linhas)


class MessageBufferService:
    """
    Manages message buffering in Redis with debounce logic (async).
    """

    def __init__(self, redis_client):
        """Recebe o cliente async já inicializado."""
        self.redis = redis_client

    @classmethod
    async def create(cls) -> "MessageBufferService":
        """Factory method async para criar instância com Redis conectado."""
        redis_client = await get_async_redis_client()
        return cls(redis_client)

    @staticmethod
    def chave(escopo: str, phone: str) -> str:
        """A chave do buffer, com TENANT dentro — SPEC-063 Bloco H.

        Era `whatsapp_buffer:{phone}`. Só o telefone.

        O mesmo segurado pode falar com DUAS corretoras (ele tem seguro de auto
        numa e residencial na outra — é comum). Dentro da janela de 8 a 25
        segundos, as duas conversas caíam na MESMA chave: as mensagens eram
        concatenadas e `data["payload"] = payload` sobrescrevia o payload, então
        o conjunto todo era processado sob a integração da ÚLTIMA mensagem.

        A corretora B recebia a pergunta que o cliente fez para a corretora A, e
        respondia com o agente dela. Vazamento entre corretoras, no caminho mais
        quente do produto.

        `escopo` é o id da integração — o identificador mais específico que o
        webhook tem quando o buffer é escrito. Sem ele, cai em
        `sem-integracao`, que continua isolando por não ser o telefone sozinho.
        """
        esc = str(escopo or "").strip() or "sem-integracao"
        return f"whatsapp_buffer:{esc}:{phone}"

    # ------------------------------------------------------------------ #
    # O BUFFER
    # ------------------------------------------------------------------ #
    async def add_message(
        self,
        phone: str,
        message: str,
        company_id: str,
        user_id: str,
        integration: Dict,
        payload: Dict,
        escopo: str = "",
        *,
        tipo: str = "text",
        midia: Optional[Dict] = None,
        wa_message_id: str = "",
    ) -> bool:
        """
        Add message to buffer (async).
        Returns True if this is the first message in buffer.

        SPEC-EXTRA-001.2 §6.2: o item é TIPADO. Foto, áudio e documento entram
        aqui pelos mesmos três pontos de onde desviavam para geração imediata —
        e a legenda viaja NO MESMO item que o arquivo.
        """
        # O escopo vem do chamador; se não vier, o payload carrega o id da
        # integração desde a rota com token (SPEC-017 P1.2).
        # Cadeia do mais específico para o menos: id da integração (rotas com
        # token) → número conectado da corretora (rota legada, que resolve o
        # tenant por ele) → um rótulo fixo. O rótulo fixo NÃO isola, e é por
        # isso que a rota legada tem de morrer (H.2 desta mesma SPEC).
        escopo = str(
            escopo
            or (payload or {}).get("_integration_id")
            or (payload or {}).get("connectedPhone")
            or ""
        ).strip()
        key = self.chave(escopo, phone)
        now_iso = datetime.now().isoformat()

        item: Dict[str, Any] = {
            "tipo": str(tipo or "text").strip().lower() or "text",
            "em": now_iso,
        }
        if str(tipo or "text").strip().lower() == "text":
            item["texto"] = str(message or "")
        else:
            item["legenda"] = str(message or "")
            if midia:
                item["midia"] = dict(midia)
        if wa_message_id:
            item["wa_message_id"] = str(wa_message_id)

        raw_data = await self.redis.get(key)

        if raw_data:
            data = json.loads(raw_data)
            data.setdefault("v", 2)
            data["itens"] = itens_do_buffer(data) + [item]
            data.pop("messages", None)
            data["last_at"] = now_iso

            # O ÚLTIMO PAYLOAD VENCE — MENOS PARA O `interactive`.
            #
            # Sobrescrever o payload é o certo para telefone, id e integração: o
            # mais recente é o mais verdadeiro. Mas o `interactive` carrega o
            # `flow_token` do formulário nativo, e ele é ÚNICO na janela: chega
            # numa mensagem só, e as seguintes vêm sem ele.
            #
            # A URA da família HDI manda rajadas — o formulário e, logo atrás,
            # um aviso de fila. Com a sobrescrita crua, o aviso apagava o token
            # do formulário, e a resposta ficava sem endereço. O motor pausaria
            # com `formulario_pronto_sem_flow_token` e ninguém saberia que a
            # causa foi um debounce de 8 segundos.
            #
            # Interativa nova vence a antiga; ausência não vence presença.
            anterior = (data.get("payload") or {}).get("interactive")
            novo = dict(payload or {})
            if anterior and not novo.get("interactive"):
                novo["interactive"] = anterior
            data["payload"] = novo
            is_first = False
        else:
            data = {
                "v": 2,
                "itens": [item],
                "first_at": now_iso,
                "last_at": now_iso,
                "company_id": company_id,
                "user_id": user_id,
                "integration": integration,
                "payload": payload,
            }
            is_first = True

        await self.redis.setex(key, settings.BUFFER_TTL_SECONDS, json.dumps(data))

        msg_count = len(data["itens"])
        logger.debug(f"[BUFFER] Added message for {phone}. Count: {msg_count}")
        return is_first

    async def should_process(self, key: str) -> bool:
        """
        Check if buffer should be processed (janela adaptativa ou teto).

        Recebe a CHAVE COMPLETA, não o telefone. O varredor já a tem em mãos —
        remontá-la a partir de `key.split(":")[-1]` era o que amarrava o buffer
        a um formato de chave de uma parte só.

        🔴 SPEC-EXTRA-001.2 §6.1: a COMPARAÇÃO mudou; o mecanismo, não. A
        ociosidade que fecha a rajada sai de `janela_de_espera` sobre os traços
        do ÚLTIMO item — 3 s para um dado curto, 8 s para uma frase completa,
        18 s para uma frase que ficou pela metade.
        """
        phone = str(key).rsplit(":", 1)[-1]
        raw_data = await self.redis.get(key)

        if not raw_data:
            return False

        data = json.loads(raw_data)
        itens = itens_do_buffer(data)

        now = datetime.now()
        first_at = datetime.fromisoformat(data["first_at"])
        last_at = datetime.fromisoformat(data["last_at"])

        seconds_since_last = (now - last_at).total_seconds()
        seconds_since_first = (now - first_at).total_seconds()

        ultimo = itens[-1] if itens else {}
        espera = janela_de_espera(tracos_da_mensagem(
            texto_do_item(ultimo), tipo=str(ultimo.get("tipo") or "text")))

        if seconds_since_last >= espera:
            logger.info(
                f"[BUFFER] Trigger JANELA ({espera}s) for {phone} "
                f"({seconds_since_last:.1f}s idle, {len(itens)} itens buffered)"
            )
            return True

        # 🔴 O teto é a constante da Meta (25 s). O env só pode DESCER dele:
        # um `BUFFER_MAX_WAIT_SECONDS` de 300 (que o `.env.example` já ensinou)
        # seguraria o segurado cinco minutos, e o "digitando..." da Meta some
        # sozinho aos 25 — a promessa vazia nasceria do próprio teto.
        teto = min(int(settings.BUFFER_MAX_WAIT_SECONDS or TETO_DA_RAJADA_SEGUNDOS),
                   TETO_DA_RAJADA_SEGUNDOS)
        if seconds_since_first >= teto:
            logger.info(
                f"[BUFFER] Trigger TETO ({teto}s) for {phone} "
                f"({seconds_since_first:.1f}s duration, {len(itens)} itens buffered)"
            )
            return True

        return False

    async def get_and_clear_buffer(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Atomically get buffer and delete from Redis (async).
        Pipeline continua atômico em async. Recebe a CHAVE COMPLETA.
        """
        phone = str(key).rsplit(":", 1)[-1]

        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        raw_data = results[0]

        if not raw_data:
            return None

        buffer_data = json.loads(raw_data)
        logger.info(
            f"[BUFFER] Cleared buffer for {phone}. "
            f"Itens: {len(itens_do_buffer(buffer_data))}"
        )
        return buffer_data

    async def mesclar_o_que_chegou(self, key: str) -> List[Dict[str, Any]]:
        """Os itens que chegaram DEPOIS do início do turno (§6.3).

        🔴 O que isto mata: a mensagem que chega no segundo 9 de uma janela de
        18 s hoje espera o turno inteiro e vira resposta separada. Com a
        releitura, ela entra na MESMA.

        ⚠️ O que isto NÃO mata: a mensagem que chega DURANTE a geração do
        modelo. Essa fica no buffer e a trava impede que vire turno paralelo —
        ela é respondida no turno seguinte, inteira.

        Mesmo `get`+`delete` atômico do `get_and_clear_buffer`: um motor só.
        """
        try:
            pipe = self.redis.pipeline()
            pipe.get(key)
            pipe.delete(key)
            resultados = await pipe.execute()
        except Exception as erro:  # noqa: BLE001
            # Falhar aqui não pode custar a resposta que já está montada: o que
            # não foi lido continua no buffer e vira o turno seguinte.
            logger.warning("[BUFFER] re-leitura falhou (%s)", type(erro).__name__)
            return []
        bruto = resultados[0] if resultados else None
        if not bruto:
            return []
        try:
            return itens_do_buffer(json.loads(bruto))
        except Exception:  # noqa: BLE001
            return []

    def get_combined_message(self, buffer: Dict) -> str:
        """
        Combine buffered messages into single text.
        NÃO precisa ser async (sem I/O).

        Lê `itens` (v2) ou `messages` (v1) — a compatibilidade dura o TTL.
        """
        return texto_combinado_dos_itens(itens_do_buffer(buffer))

    # ------------------------------------------------------------------ #
    # A TRAVA DE TURNO (SPEC-EXTRA-001.2 §5)
    # ------------------------------------------------------------------ #
    @staticmethod
    def chave_do_turno(escopo: str, phone: str) -> str:
        """`whatsapp_turno:{escopo}:{phone}` — MESMO escopo do buffer."""
        esc = str(escopo or "").strip() or ESCOPO_SEM_INTEGRACAO
        return f"{TURNO_PREFIXO}:{esc}:{phone}"

    @staticmethod
    def escopo_serve_para_travar(escopo: str) -> bool:
        """🔴 FAIL-CLOSED: escopo vazio (ou `sem-integracao`) NÃO trava.

        `chave()` colapsa a ausência de escopo em `sem-integracao`, que é um
        rótulo FIXO: duas corretoras com o mesmo segurado cairiam na MESMA
        chave de turno e **uma travaria a outra** — exatamente o que a
        D-PILOTO-07 proíbe. Recusar custa a resposta dessa rota; aceitar custa
        a resposta da corretora errada, e esse custo não é reversível.
        """
        esc = str(escopo or "").strip()
        return bool(esc) and esc != ESCOPO_SEM_INTEGRACAO

    async def abrir_turno(self, escopo: str, phone: str, *,
                          ttl_s: int = 0) -> Optional[str]:
        """`SET chave token NX EX ttl`. Token se ganhou; `None` se não.

        O token é `uuid4().hex` — E01: *"set a non-guessable large random
        string"*. ⛔ Sem token não há liberação segura: qualquer um apagaria a
        trava de qualquer um.
        """
        if not self.escopo_serve_para_travar(escopo):
            # ⚠️ Nem telefone, nem escopo, nem texto: o feed exige `company_id`,
            # e neste ponto do caminho ele ainda é "pending" (`webhook.py`
            # grava o buffer antes de resolver o tenant). Quem lê esta linha é
            # quem opera — e o que ela precisa dizer é QUAL rota não identifica
            # a corretora, não com quem o segurado estava falando.
            logger.warning(
                "[TURNO] recusado: a conversa chegou sem integração identificada "
                "— o agente não responde por uma corretora que não sei qual é")
            return None
        if not str(phone or "").strip():
            logger.warning("[TURNO] recusado: evento sem contraparte identificável")
            return None

        token = uuid4().hex
        chave = self.chave_do_turno(escopo, phone)
        ttl = int(ttl_s or TURNO_TTL_SEGUNDOS)
        try:
            ganhou = await self.redis.set(chave, token, nx=True, ex=ttl)
        except Exception as erro:  # noqa: BLE001
            # ⛔ Redis fora do ar não é permissão para dois turnos paralelos.
            logger.error("[TURNO] não consegui abrir o turno (%s) — não respondo",
                         type(erro).__name__)
            return None
        return token if ganhou else None

    async def renovar_turno(self, escopo: str, phone: str, token: str, *,
                            ttl_s: int = 0, renovacoes_feitas: int = 0) -> bool:
        """EVAL: renova SÓ se o valor ainda for o token. Teto de renovações."""
        if not token or renovacoes_feitas >= TURNO_RENOVACOES_MAX:
            return False
        chave = self.chave_do_turno(escopo, phone)
        ttl = int(ttl_s or TURNO_TTL_SEGUNDOS)
        try:
            resultado = await self.redis.eval(
                LUA_RENOVA_SE_FOR_MEU, 1, chave, token, str(ttl))
        except Exception as erro:  # noqa: BLE001
            logger.warning("[TURNO] renovação falhou (%s)", type(erro).__name__)
            return False
        return bool(resultado)

    async def ainda_sou_o_dono(self, escopo: str, phone: str, token: str) -> bool:
        """A reconferência antes de enviar (E01: a trava pode ter expirado).

        ⛔ Falha de leitura devolve `False`: não conseguir provar a posse nunca
        é permissão para falar — é a mesma direção do portão de silêncio.
        """
        if not token:
            return False
        chave = self.chave_do_turno(escopo, phone)
        try:
            atual = await self.redis.get(chave)
        except Exception as erro:  # noqa: BLE001
            logger.error("[TURNO] não consegui reconferir a posse (%s) — não envio",
                         type(erro).__name__)
            return False
        if atual is None:
            return False
        if isinstance(atual, (bytes, bytearray)):
            atual = atual.decode("utf-8", "replace")
        return str(atual) == str(token)

    async def fechar_turno(self, escopo: str, phone: str, token: str) -> bool:
        """EVAL com o script literal da doc do Redis. ⛔ NUNCA `DEL` cego."""
        if not token:
            return False
        chave = self.chave_do_turno(escopo, phone)
        try:
            resultado = await self.redis.eval(
                LUA_LIBERA_SE_FOR_MEU, 1, chave, token)
        except Exception as erro:  # noqa: BLE001
            # O TTL fecha sozinho. Perder a liberação custa <= TTL de espera;
            # apagar a trava de outro turno custa duas respostas.
            logger.warning("[TURNO] liberação falhou (%s) — o TTL fecha",
                           type(erro).__name__)
            return False
        return bool(resultado)


# Singleton será inicializado no startup do FastAPI
# NÃO instanciar aqui porque precisa de await
_buffer_service_instance: Optional[MessageBufferService] = None


async def get_message_buffer_service() -> MessageBufferService:
    """Retorna singleton do MessageBufferService (lazy init async)."""
    global _buffer_service_instance
    if _buffer_service_instance is None:
        _buffer_service_instance = await MessageBufferService.create()
    return _buffer_service_instance
