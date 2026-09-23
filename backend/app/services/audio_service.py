"""
Serviço de Áudio — transcrição pelo modelo da ROTA `transcricao` (SPEC-116), ASYNC.
"""

import base64
import logging
import os
import tempfile

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


#: O papel do Model Router que transcreve (SPEC-116 U8; D-116-13: whisper-1
#: desliga em 26/02/2027 — a troca é uma linha da ROTA, depois da bancada).
PAPEL_DA_TRANSCRICAO = "transcricao"


def _modelo_da_rota() -> str:
    from app.factories.model_policy import resolver

    return resolver(PAPEL_DA_TRANSCRICAO).model


class AudioService:
    """Transcrição de áudio (async) pelo modelo da ROTA `transcricao`.

    🔴 SPEC-116 U8: o id era literal nos dois caminhos. PONTO DE INJEÇÃO:
    `AudioService(chave, modelo=..., cliente=...)` — `cliente` é qualquer objeto
    com `audio.transcriptions.create` (a bancada e os testes passam um dublê);
    `modelo` fixa o braço. Sem `modelo`, a rota é lida a CADA transcrição (a
    troca vale sem reiniciar). ⛔ Sem rota → `ModeloNaoResolvido` (nunca um
    modelo por omissão).
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
        """`verbose_json` (traz a DURAÇÃO, que é o que se cobra) só existe no
        Whisper; os `gpt-*-transcribe` aceitam só json/text e devolvem `usage`."""
        return str(modelo or "").startswith("whisper-")

    def _registrar_uso(self, transcript, modelo: str, *, company_id, agent_id, details: dict) -> None:
        """Ledger da transcrição: duração (Whisper) ou tokens (`usage`)."""
        from .usage_service import get_usage_service

        duracao = getattr(transcript, "duration", None)
        uso = getattr(transcript, "usage", None)
        entrada = saida = 0
        if duracao:
            entrada = int(duracao)
        elif uso is not None:
            entrada = int(getattr(uso, "input_tokens", 0) or 0)
            saida = int(getattr(uso, "output_tokens", 0) or 0)
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
        Transcreve áudio em base64 usando Whisper API (async).
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

            # Criar arquivo temporário (I/O local, rápido, ok ser sync)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            try:
                logger.info(f"[AUDIO] Sending to Whisper API: {temp_file_path}")

                modelo = self.modelo
                with open(temp_file_path, "rb") as audio_file:
                    # ✅ ASYNC: await na chamada à API da OpenAI
                    extras = {"response_format": "verbose_json"} if self._formato_detalhado(modelo) else {}
                    transcript = await self.client.audio.transcriptions.create(
                        model=modelo,
                        file=audio_file,
                        language="pt",
                        **extras,
                    )

                transcribed_text = transcript.text

                # Track cost (sync, rápido, ok por enquanto)
                try:
                    self._registrar_uso(transcript, modelo, company_id=company_id,
                                        agent_id=agent_id, details={})
                except Exception as e:
                    logger.warning(f"[AUDIO] Cost tracking failed: {e}")

                logger.info(
                    f"[AUDIO] Transcription successful: {transcribed_text[:100]}..."
                )

                return transcribed_text

            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.debug(f"[AUDIO] Temporary file deleted: {temp_file_path}")

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

            with tempfile.NamedTemporaryFile(
                suffix=extension, delete=False
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            try:
                logger.info(f"[AUDIO] Sending to Whisper API: {temp_file_path}")

                modelo = self.modelo
                with open(temp_file_path, "rb") as audio_file:
                    # ✅ ASYNC: await na chamada à API
                    # 🔴 SPEC-116 U8: `verbose_json` também aqui. Sem ele o
                    # Whisper não devolve `duration` e ESTE caminho (o do
                    # WhatsApp) nunca entrava no ledger.
                    extras = {"response_format": "verbose_json"} if self._formato_detalhado(modelo) else {}
                    transcript = await self.client.audio.transcriptions.create(
                        model=modelo,
                        file=audio_file,
                        language="pt",
                        **extras,
                    )

                transcribed_text = transcript.text

                try:
                    if company_id:
                        self._registrar_uso(transcript, modelo, company_id=company_id,
                                            agent_id=agent_id, details={"source": "whatsapp"})
                except Exception as e:
                    logger.warning(f"[AUDIO] Cost tracking failed: {e}")

                logger.info(
                    f"[AUDIO] Transcription successful: {transcribed_text[:100]}..."
                )

                return transcribed_text

            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.debug(f"[AUDIO] Temporary file deleted: {temp_file_path}")

        except httpx.HTTPError as e:
            logger.error(f"[AUDIO] Error downloading audio: {str(e)}")
            raise Exception(f"Failed to download audio from URL: {str(e)}") from e
        except ValueError as e:
            logger.error(f"[AUDIO] Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[AUDIO] Transcription error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to transcribe audio from URL: {str(e)}") from e
