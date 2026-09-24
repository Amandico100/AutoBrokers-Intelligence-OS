"""
Serviço de Áudio — transcrição pelo modelo da ROTA `transcricao` (SPEC-116), ASYNC.
"""

import base64
import logging
import os
import tempfile
from typing import Optional

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


#: O papel do Model Router que transcreve (SPEC-116 U8; D-116-13: whisper-1
#: desliga em 26/02/2027). 📊 24/09/2026 a rota é `gpt-transcribe` (Founder,
#: conclusão da Onda A — migration 20260924_01).
PAPEL_DA_TRANSCRICAO = "transcricao"

#: Contexto de domínio enviado como `prompt` à API de transcrição — GOVERNADO:
#: ⛔ nunca PII (nome de segurado, placa, CPF, telefone, nome de corretora). Só
#: o ofício e os NOMES DE SEGURADORAS, lidos da fonte canônica da plataforma
#: (`insurer_registry.INSURER_REGISTRY`, dado global de produto — seguradora não
#: é cliente). EVIDENCIAS/04 l.54: o gpt-transcribe aceita "keyword hints,
#: contexto livre"; o whisper-1 também aceita `prompt`.
CONTEXTO_DE_DOMINIO = "Atendimento de corretora de seguros no Brasil."
TERMOS_DO_OFICIO = ("apólice", "sinistro", "assistência 24 horas", "guincho", "franquia",
                    "vistoria", "segurado", "corretora")
LIMITE_DO_PROMPT = 600  # caracteres — dica curta; o modelo não precisa de mais


def prompt_de_dominio() -> str:
    """O `prompt` da transcrição: contexto + vocabulário, sem PII, com teto."""
    try:
        from app.services.insurer_registry import INSURER_REGISTRY

        seguradoras = sorted({str(v.get("label") or "").strip()
                              for v in INSURER_REGISTRY.values() if v.get("label")})
    except Exception:  # noqa: BLE001 — sem o registro, só o contexto genérico
        seguradoras = []
    partes = [CONTEXTO_DE_DOMINIO, "Termos frequentes: " + ", ".join(TERMOS_DO_OFICIO) + "."]
    if seguradoras:
        partes.append("Seguradoras: " + ", ".join(seguradoras) + ".")
    return " ".join(partes)[:LIMITE_DO_PROMPT]


def _modelo_da_rota() -> str:
    from app.factories.model_policy import resolver

    return resolver(PAPEL_DA_TRANSCRICAO).model


def duracao_local_em_segundos(dados: bytes, extensao: str) -> Optional[float]:
    """Duração do áudio SEM biblioteca de mídia (o ledger cobra por MINUTO).

    WAV pelo cabeçalho; OGG (o áudio do WhatsApp) pela posição de grânulo da
    ÚLTIMA página (Opus = 48 kHz sempre, menos o pre-skip; Vorbis = taxa do
    cabeçalho de identificação). Outros formatos → None (quem chama não inventa).
    """
    ext = (extensao or "").lower().lstrip(".")
    try:
        if ext == "wav":
            import io
            import wave

            with wave.open(io.BytesIO(dados)) as w:
                taxa = w.getframerate()
                return (w.getnframes() / float(taxa)) if taxa else None
        if ext in ("ogg", "oga", "opus"):
            ultima = dados.rfind(b"OggS")
            if ultima < 0 or len(dados) < ultima + 14:
                return None
            granulo = int.from_bytes(dados[ultima + 6:ultima + 14], "little", signed=True)
            if granulo <= 0:
                return None
            i = dados.find(b"OpusHead", 0, 4096)
            if i >= 0:
                pre_skip = int.from_bytes(dados[i + 10:i + 12], "little") if len(dados) >= i + 12 else 0
                return max(granulo - pre_skip, 0) / 48000.0
            i = dados.find(b"\x01vorbis", 0, 4096)
            if i >= 0 and len(dados) >= i + 16:
                taxa = int.from_bytes(dados[i + 12:i + 16], "little")
                return granulo / float(taxa) if taxa else None
    except Exception:  # noqa: BLE001 — duração é para o ledger; nunca derruba a transcrição
        return None
    return None


class AudioService:
    """Transcrição de áudio (async) pelo modelo da ROTA `transcricao`.

    🔴 SPEC-116 U8: o id era literal nos dois caminhos. PONTO DE INJEÇÃO:
    `AudioService(chave, modelo=..., cliente=...)` — `cliente` é qualquer objeto
    com `audio.transcriptions.create` (a bancada e os testes passam um dublê);
    `modelo` fixa o braço (a bancada pode fixar um DEPRECATED como baseline).
    Sem `modelo`, a rota é lida a CADA transcrição (a troca vale sem reiniciar).
    ⛔ Sem rota → `ModeloNaoResolvido` (nunca um modelo por omissão).

    A chamada é a API de TRANSCRIÇÃO da OpenAI (`/audio/transcriptions`), não a
    fábrica de chat.
    """

    def __init__(self, openai_api_key: str, *, modelo: str = None, cliente=None):
        self.client = cliente if cliente is not None else AsyncOpenAI(api_key=openai_api_key)
        self._modelo_fixo = modelo
        logger.info("Audio service initialized (papel transcricao, async)")

    @property
    def modelo(self) -> str:
        return self._modelo_fixo or _modelo_da_rota()

    @staticmethod
    def _formato_detalhado(modelo: str) -> bool:
        """`verbose_json` (traz a DURAÇÃO) só é documentado no Whisper; o
        `gpt-transcribe` não o documenta (EVIDENCIAS/04 l.54) → `json`, e a
        duração do ledger é medida AQUI (`duracao_local_em_segundos`)."""
        return str(modelo or "").startswith("whisper-")

    def _parametros(self, modelo: str) -> dict:
        return {
            "model": modelo,
            "language": "pt",
            "prompt": prompt_de_dominio(),
            "response_format": "verbose_json" if self._formato_detalhado(modelo) else "json",
        }

    async def _transcrever(self, dados: bytes, extensao: str):
        """(transcript, modelo, duração local) — UMA chamada à API de transcrição."""
        with tempfile.NamedTemporaryFile(suffix=extensao, delete=False) as temp_file:
            temp_file.write(dados)
            temp_file_path = temp_file.name
        try:
            modelo = self.modelo
            logger.info("[AUDIO] Enviando à API de transcrição (%s)", modelo)
            with open(temp_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    file=audio_file, **self._parametros(modelo))
            return transcript, modelo, duracao_local_em_segundos(dados, extensao)
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    @staticmethod
    def _unidade(modelo: str) -> Optional[str]:
        try:
            from app.factories.model_policy import catalogo

            return (catalogo().get(modelo) or {}).get("unit")
        except Exception:  # noqa: BLE001
            return None

    def _registrar_uso(self, transcript, modelo: str, *, company_id, agent_id, details: dict,
                       duracao_local: Optional[float] = None) -> None:
        """Ledger da transcrição. Modelo cobrado por MINUTO (`unit=minute`):
        `input_tokens` = SEGUNDOS (a conta de `usage_service.calculate_cost`) —
        da resposta (`duration` do verbose_json ou `usage.seconds`) ou medidos
        localmente. Modelo por token: `usage.input/output_tokens`."""
        from .usage_service import get_usage_service

        uso = getattr(transcript, "usage", None)

        def _u(chave):
            return uso.get(chave) if isinstance(uso, dict) else getattr(uso, chave, None)

        duracao = getattr(transcript, "duration", None)
        if not duracao and uso is not None and _u("type") == "duration":
            duracao = _u("seconds")
        if not duracao:
            duracao = duracao_local
        entrada = saida = 0
        if self._unidade(modelo) == "minute" or (duracao and uso is None):
            if not duracao:
                logger.warning("[AUDIO] ledger: %s é cobrado por minuto e a duração não pôde ser "
                               "medida — linha NÃO gravada (sem inventar)", modelo)
                return
            entrada = max(1, int(round(float(duracao))))
        elif uso is not None:
            entrada = int(_u("input_tokens") or 0)
            saida = int(_u("output_tokens") or 0)
        if not (entrada or saida):
            return
        get_usage_service().track_cost_sync(
            service_type="audio",
            model=modelo,
            input_tokens=entrada,
            output_tokens=saida,
            company_id=company_id,
            agent_id=agent_id,
            details={**details, "papel": PAPEL_DA_TRANSCRICAO, "modelo_resolvido": modelo,
                     "duration_seconds": duracao},
        )

    async def transcribe_audio(
        self,
        audio_base64: str,
        company_id: str = None,
        agent_id: str = None
    ) -> str:
        """
        Transcreve áudio em base64 pela API de transcrição (modelo da rota), async.
        Não bloqueia o event loop durante a chamada à API.

        Args:
            audio_base64: Áudio em formato base64
            company_id: ID da empresa (para billing)
            agent_id: ID do agente (para billing)

        Returns:
            Texto transcrito

        Raises:
            ValueError: Se o áudio estiver vazio ou inválido
            Exception: Se houver erro na transcrição
        """
        try:
            if not audio_base64:
                raise ValueError("Audio data is empty")

            logger.info("[AUDIO] Starting audio transcription")

            # Decodificar base64 (CPU-bound, rápido, ok ser sync)
            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"[AUDIO] Decoded audio size: {len(audio_bytes)} bytes")

            transcript, modelo, duracao = await self._transcrever(audio_bytes, ".webm")
            transcribed_text = transcript.text

            try:
                self._registrar_uso(transcript, modelo, company_id=company_id,
                                    agent_id=agent_id, details={}, duracao_local=duracao)
            except Exception as e:
                logger.warning(f"[AUDIO] Cost tracking failed: {e}")

            logger.info(f"[AUDIO] Transcription successful: {transcribed_text[:100]}...")
            return transcribed_text

        except ValueError as e:
            logger.error(f"[AUDIO] Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[AUDIO] Transcription error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}") from e

    async def transcribe_audio_from_url(
        self,
        audio_url: str,
        company_id: str = None,
        agent_id: str = None
    ) -> str:
        """
        Transcreve áudio a partir de URL (async).
        Usado para WhatsApp.

        Args:
            audio_url: URL do áudio
            company_id: ID da empresa (para billing)
            agent_id: ID do agente (para billing)

        Returns:
            Texto transcrito

        Raises:
            ValueError: Se a URL estiver vazia ou inválida
            Exception: Se houver erro no download ou transcrição
        """
        try:
            if not audio_url:
                raise ValueError("Audio URL is empty")

            logger.info(f"[AUDIO] Downloading audio from URL: {audio_url[:100]}...")

            # ✅ ASYNC: Usar httpx para download async
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.get(audio_url)
                response.raise_for_status()

            audio_bytes = response.content
            logger.info(f"[AUDIO] Downloaded audio size: {len(audio_bytes)} bytes")

            content_type = response.headers.get("Content-Type", "")

            extension_map = {
                "audio/ogg": ".ogg",
                "audio/mpeg": ".mp3",
                "audio/mp4": ".m4a",
                "audio/wav": ".wav",
                "audio/webm": ".webm",
            }

            extension = extension_map.get(content_type, ".ogg")

            logger.info(f"[AUDIO] Detected format: {content_type} -> {extension}")

            transcript, modelo, duracao = await self._transcrever(audio_bytes, extension)
            transcribed_text = transcript.text

            try:
                if company_id:
                    self._registrar_uso(transcript, modelo, company_id=company_id,
                                        agent_id=agent_id, details={"source": "whatsapp"},
                                        duracao_local=duracao)
            except Exception as e:
                logger.warning(f"[AUDIO] Cost tracking failed: {e}")

            logger.info(f"[AUDIO] Transcription successful: {transcribed_text[:100]}...")
            return transcribed_text

        except httpx.HTTPError as e:
            logger.error(f"[AUDIO] Error downloading audio: {str(e)}")
            raise Exception(f"Failed to download audio from URL: {str(e)}") from e
        except ValueError as e:
            logger.error(f"[AUDIO] Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[AUDIO] Transcription error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to transcribe audio from URL: {str(e)}") from e
