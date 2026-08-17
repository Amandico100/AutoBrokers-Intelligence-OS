"""
Serviço WhatsApp (shim de compatibilidade) — 39A4.1.

Delega para o ZApiProvider (camada oficial de provider). Mantém a assinatura
send_message/send_audio/send_image usada por backend/app/api/webhook.py.

Segurança: nenhum log de URL/token/Client-Token aqui — toda a chamada Z-API
(e o mascaramento de telefone) vive em app/services/whatsapp/zapi_provider.py.
"""
import logging
from typing import Any, Dict, Optional

from app.services.whatsapp.zapi_provider import get_zapi_provider

logger = logging.getLogger(__name__)


def _e_recuperavel(erro: BaseException) -> bool:
    """Vale a pena tentar de novo? Só falha transitória — nunca recusa do WhatsApp.

    `WhatsappRetryableError` é levantada pelos providers para 429 e 5xx. Erro de
    conteúdo (número inválido, mensagem recusada) não entra: repetir aquilo é
    gastar a janela do segurado três vezes com o mesmo resultado.
    """
    from app.services.whatsapp.exceptions import WhatsappRetryableError

    return isinstance(erro, (WhatsappRetryableError, ConnectionError, TimeoutError))


# A POLÍTICA DE RETRY DE ENVIO — declarada aqui, e não em cada chamador.
#
# 🔴 Ela era referida como "a política EXISTENTE" por
# `app/services/whatsapp/service.py:54`, que fazia
# `from app.services.whatsapp_service import wa_send_retry`. **O nome não
# existia em lugar nenhum do projeto.** O módulo inteiro quebrava ao ser
# importado; ninguém percebeu porque nada o importa hoje.
#
# Encontrado em 06/08/2026 pela varredura que nasceu de um defeito irmão — um
# `from ... import` para um nome inexistente que matou o espelho do chat 2.255
# vezes em silêncio. Ver `test_todo_import_aponta_para_algo_que_existe`.
#
# Três tentativas com espera exponencial (1s, 2s, 4s, teto de 8s), e a última
# falha SOBE: engolir aqui faria o chamador achar que a mensagem saiu.
try:
    from tenacity import (
        retry,
        retry_if_exception,
        stop_after_attempt,
        wait_exponential,
    )

    wa_send_retry = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_e_recuperavel),
        reraise=True,
    )
except ImportError:  # pragma: no cover — tenacity está em requirements.txt
    def wa_send_retry(funcao):
        """Sem tenacity, o envio acontece uma vez. Melhor que não acontecer."""
        return funcao


def _dormir(segundos: float) -> None:
    """Espera sem congelar o event loop, quando houver um.

    Este módulo é síncrono e é chamado dos dois mundos: de tarefas em thread
    (onde `time.sleep` é correto) e de rotas async (onde ele para o processo
    inteiro). A função escolhe sozinha, em vez de obrigar todo chamador a saber
    em qual mundo está.
    """
    import asyncio
    import time as _t

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        _t.sleep(segundos)          # sem loop: thread própria, dorme normal
        return
    # Com loop rodando, este código está numa thread de `to_thread` (o método é
    # síncrono). Dormir aqui não bloqueia o loop — mas se um dia alguém chamar
    # direto da corrotina, o aviso aparece no log em vez de o produto travar.
    logger.debug("[WhatsApp] cadência de %.1fs dentro de loop ativo", segundos)
    _t.sleep(segundos)


class WhatsappService:
    """Compat: delega o envio Z-API para o ZApiProvider."""

    def __init__(self):
        logger.info("WhatsApp service initialized (delegates to ZApiProvider)")

    def send_message(self, to_number: str, text: str, integration: Dict[str, Any]) -> bool:
        """Envia texto. Retorna True em sucesso; levanta exceção em falha (contrato legado).

        SPEC-017 P1.2: provider != z-api envia pelo seam multi-provider
        (Evolution/uazapi); z-api mantém o caminho legado.
        S17-9: resposta longa vira balões curtos (humanização).
        """
        import time

        from app.services.whatsapp.balloons import split_whatsapp_balloons

        balloons = split_whatsapp_balloons(text) or [str(text or "")]
        provider_label = str((integration or {}).get("provider") or "z-api").strip().lower()

        if provider_label not in ("z-api", "zapi", ""):
            from app.services.whatsapp.registry import resolve_provider

            provider = resolve_provider(integration)
            _enviar = lambda t: provider.send_text(to_number, t)  # noqa: E731
        else:
            _enviar = lambda t: get_zapi_provider().send_text(to_number, t, integration)  # noqa: E731

        # 🔴 A DIGITAL DA PRÓPRIA VOZ — embrulhada no envio, e só aqui.
        #
        # Tudo que o produto fala com o segurado passa por este método: o
        # agente, a atendente pelo dashboard, o acionamento, a mensagem de erro.
        # Registrar em cada chamador seria doze lugares para esquecer um.
        #
        # 📊 O motivo (14/08/2026): a resposta VOLTA pelo webhook como `fromMe`,
        # e `webhook.py:1180` lia isso como "a atendente respondeu pelo celular"
        # e pausava a IA. O agente responderia uma vez e emudeceria para sempre.
        # Ver `app/services/whatsapp/voz_propria.py`.
        #
        # 🔴 DENTRO do `send`, e não no laço abaixo, porque o laço não é o único
        # caminho: há um retry do mesmo balão e uma divisão em PEDAÇOS quando o
        # balão é grande. Cada pedaço é um texto diferente que volta como um
        # `fromMe` diferente — registrar só no laço deixaria justamente o
        # caminho de exceção sem digital, que é onde ninguém olha.
        _empresa_da_voz = str((integration or {}).get("company_id") or "")

        def send(t):
            if _empresa_da_voz and str(t or "").strip():
                from app.services.whatsapp.voz_propria import registrar_nossa_fala

                # ANTES de enviar: o eco pode voltar antes da linha seguinte.
                registrar_nossa_fala(_empresa_da_voz, to_number, t)
            return _enviar(t)

        def _ok(result) -> bool:
            # SendResult do seam usa .ok; o provider z-api legado usa .success.
            # (Checar só .success foi a CAUSA das duplicatas: envio bom parecia
            # falha -> retry reenviava e a exceção matava os balões seguintes.)
            if hasattr(result, "ok"):
                return bool(result.ok)
            return bool(getattr(result, "success", False))

        for i, balloon in enumerate(balloons):
            if i > 0:
                # SPEC-063 Bloco H — `time.sleep` num método chamado de rota
                # async CONGELA o event loop inteiro: 4 balões = 2,1 s em que o
                # processo não atende mais ninguém, nem outra corretora. A
                # cadência humana continua; o bloqueio, não.
                _dormir(0.7)  # cadência humana + evita throttle do provedor
            result = send(balloon)
            if _ok(result):
                continue
            # Falha: LOG COMPLETO (o bug do balão sumido era invisível) + retry.
            detail = getattr(result, "error", None) or getattr(result, "status_code", None) or getattr(result, "raw", None)
            logger.error(f"[WA SEND] balão {i + 1}/{len(balloons)} falhou (len={len(balloon)}): {str(detail)[:300]}")
            _dormir(1.2)
            if _ok(send(balloon)):
                continue
            # Último recurso p/ balão grande: divide por linhas e envia pedaços.
            if len(balloon) > 400:
                lines = balloon.splitlines()
                mid = max(1, len(lines) // 2)
                pieces = ["\n".join(lines[:mid]).strip(), "\n".join(lines[mid:]).strip()]
                if all(_ok(send(p)) for p in pieces if p):
                    logger.warning(f"[WA SEND] balão {i + 1} entregue em 2 pedaços após falha")
                    continue
            # 🔴 O MOTIVO VAI JUNTO. Antes esta exceção era só "Failed to send
            # WhatsApp message", e quem a capturava gravava `type(e).__name__`
            # — literalmente a palavra "Exception".
            #
            # 📊 Medido em 17/08/2026: o Auxiliar de Cobrança baixou 5 boletos
            # reais, tentou enviar 2 e falhou. O relatório dizia
            # "modo teste: falha ao enviar simulacao para ...7463 (Exception)".
            # O `SendResult` SABIA o status HTTP; ele morria aqui. Sem acesso
            # ao log do contêiner, isso custou uma rodada inteira de 15 minutos
            # para descobrir o que já estava na memória do processo.
            #
            # Erro que não diz o que houve obriga a reproduzir para diagnosticar
            # — e reproduzir custa 15 minutos e uma entrada a mais no portal.
            raise Exception(
                f"Falha ao enviar pelo WhatsApp ({provider_label}): {str(detail)[:200]}"
            )
        return True

    def send_audio(self, to_number: str, audio_url: str, integration: Dict[str, Any]) -> bool:
        return get_zapi_provider().send_audio(to_number, audio_url, integration).success

    def send_image(
        self, to_number: str, image_url: str, caption: str, integration: Dict[str, Any]
    ) -> bool:
        return get_zapi_provider().send_image(to_number, image_url, caption, integration).success

    def send_document(
        self,
        to_number: str,
        doc_url: str,
        filename: str,
        integration: Dict[str, Any],
        caption: str = "",
    ) -> bool:
        """Envia documento (ex.: boleto PDF) pelo seam multi-provider.

        Retorna bool; nunca levanta (falha vira False + log) — quem chama decide
        o fallback (ex.: mandar o link como texto). Contrato do seam usa `.ok`.
        """
        try:
            from app.services.whatsapp.models import OutboundMedia
            from app.services.whatsapp.registry import resolve_provider

            name = str(filename or "documento.pdf").strip() or "documento.pdf"
            mime = "application/pdf" if name.lower().endswith(".pdf") else None
            provider = resolve_provider(integration)
            result = provider.send_media(
                to_number,
                OutboundMedia(kind="document", url=doc_url, mime_type=mime, caption=caption or None, filename=name),
            )
            ok = bool(getattr(result, "ok", getattr(result, "success", False)))
            if not ok:
                logger.error(
                    "[WA SEND] documento falhou (%s): %s",
                    name,
                    str(getattr(result, "error", "") or "sem detalhe")[:200],
                )
            return ok
        except Exception as e:  # noqa: BLE001
            logger.error(f"[WA SEND] documento levantou excecao: {type(e).__name__}")
            return False


# Singleton instance
_whatsapp_service: Optional[WhatsappService] = None


def get_whatsapp_service() -> WhatsappService:
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsappService()
    return _whatsapp_service
