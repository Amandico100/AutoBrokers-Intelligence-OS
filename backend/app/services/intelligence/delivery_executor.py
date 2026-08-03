"""Entrega o briefing — e diz o motivo quando não entrega. SPEC-064 Bloco E.

O defeito que este arquivo existe para consertar
------------------------------------------------
Medido em 02/08/2026::

    briefing_publications ......... 26
    delivery_status = 'pending' ... 26  (100%)
    delivery_policy.decidir() ..... ZERO chamadores em produção

A política de entrega existia, era pura, bem escrita e testada — e **ninguém a
chamava**. O sistema publicava o briefing, gravava `pending`, e ficava assim
para sempre. Não havia bug: havia um fio solto entre duas peças prontas.

O que este módulo NÃO faz
-------------------------
**Não é um motor de envio.** Ele decide (chamando a política que já existe) e
delega ao caminho de envio que já existe. CLAUDE.md §5 — nada de segundo
publisher ao lado do que há.

A regra que atravessa tudo aqui
-------------------------------
> **`pending` mudo é proibido.**

Toda publicação sai deste módulo com um estado FINAL e um motivo legível:

    sent       entregou em todos os canais que tentou
    partial    entregou em uns e falhou em outros
    failed     tentou e nenhum funcionou
    skipped    a política decidiu não entregar agora, e diz por quê

Estes quatro **não são invenção deste módulo**: são o vocabulário que a coluna
já aceita, declarado em `briefing_publications_delivery_ck`::

    pending | sent | partial | failed | skipped | not_applicable

Escrevi `delivered`/`delivered_partial` na primeira versão e o banco recusou —
o teste tinha passado porque o banco falso não valida constraint. Ficou a
lição: **estado que o schema não conhece não é estado, é exceção esperando
acontecer.**

Um canal indisponível — chave de e-mail vazia, WhatsApp sem governador — **não
é uma falha silenciosa: é um motivo escrito**. É a diferença entre "não sei o
que aconteceu" e "sei exatamente o que falta ligar".
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from .delivery_policy import ContextoDeEntrega, decidir, em_quiet_hours

logger = logging.getLogger(__name__)

# Canais que o Bloco E sabe executar. `push` fica de fora de propósito: sem
# service worker registrado, prometer push seria inventar entrega.
CANAIS_CONHECIDOS = ("dashboard", "email", "whatsapp")

# O vocabulário da coluna, copiado do CHECK `briefing_publications_delivery_ck`.
# Escrever um valor fora daqui não vira erro de lógica: vira exceção do banco
# no meio de uma publicação que já deu certo.
STATUS_PERMITIDOS = ("pending", "sent", "partial", "failed", "skipped", "not_applicable")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class ResultadoDeCanal:
    """O que aconteceu num canal, e por quê. O motivo é para humano ler."""

    __slots__ = ("canal", "ok", "motivo", "detalhe")

    def __init__(self, canal: str, ok: bool, motivo: str, detalhe: Any = None):
        self.canal = canal
        self.ok = ok
        self.motivo = motivo
        self.detalhe = detalhe

    def como_dict(self) -> dict:
        d = {"canal": self.canal, "ok": self.ok, "motivo": self.motivo}
        if self.detalhe is not None:
            d["detalhe"] = self.detalhe
        return d


class DeliveryExecutor:
    """Recebe uma publicação já gravada e a entrega — ou explica por que não."""

    def __init__(self, db):
        self.db = getattr(db, "client", db)

    # ------------------------------------------------------------------
    # O ponto de entrada
    # ------------------------------------------------------------------

    def entregar(self, publicacao: dict, *, perfil: Optional[dict] = None) -> dict:
        """Decide, executa e grava o estado final. Nunca deixa em `pending`.

        Devolve o mesmo dicionário que grava, para quem chamou poder registrar.
        """
        perfil = perfil or {}
        pub_id = publicacao.get("id")
        if not pub_id:
            return {"ok": False, "erro": "publicação sem id"}

        ctx = self._contexto(publicacao, perfil)
        decisao = decidir(ctx, agora_utc=_agora(), perfil=perfil)

        # A política pode decidir que agora não é hora. Isso NÃO é falha — e
        # precisa ficar registrado com o motivo dela, não com um genérico.
        canais_pedidos = [c for c in (decisao.canais or []) if c in CANAIS_CONHECIDOS]

        # O dashboard é o registro, e ele sempre acontece: a publicação existir
        # JÁ é a entrega no painel. Deixá-lo de fora faria o corretor ver
        # "não entregue" numa coisa que está na tela dele.
        if "dashboard" not in canais_pedidos:
            canais_pedidos.insert(0, "dashboard")

        resultados = [self._executar(canal, publicacao, perfil, decisao)
                      for canal in canais_pedidos]

        entregues = [r for r in resultados if r.ok]
        falhados = [r for r in resultados if not r.ok]

        if entregues and not falhados:
            status = "sent"
        elif entregues and falhados:
            status = "partial"
        elif not entregues and falhados:
            status = "failed"
        else:
            status = "skipped"

        detalhe = {
            "decidido_em": _agora().isoformat(),
            "motivo_da_politica": decisao.motivo,
            "push": decisao.push,
            "quiet_hours": em_quiet_hours(
                _agora(),
                timezone_nome=perfil.get("timezone") or "America/Sao_Paulo",
                quiet_hours=perfil.get("quiet_hours"),
            ),
            "canais": [r.como_dict() for r in resultados],
        }
        if decisao.adiar_para:
            detalhe["adiar_para"] = decisao.adiar_para

        self._gravar(pub_id, status, detalhe)
        return {"ok": True, "delivery_status": status, "delivery_detail": detalhe}

    # ------------------------------------------------------------------
    # Os canais
    # ------------------------------------------------------------------

    def _executar(self, canal: str, publicacao: dict, perfil: dict,
                  decisao) -> ResultadoDeCanal:
        try:
            if canal == "dashboard":
                return self._dashboard(publicacao)
            if canal == "email":
                return self._email(publicacao, perfil)
            if canal == "whatsapp":
                return self._whatsapp(publicacao, perfil, decisao)
        except Exception as exc:  # noqa: BLE001
            # Uma exceção num canal não pode derrubar os outros — nem virar
            # `pending`. Ela vira motivo.
            logger.warning("[Entrega] canal %s explodiu: %s", canal, type(exc).__name__)
            return ResultadoDeCanal(canal, False, f"erro inesperado: {type(exc).__name__}")
        return ResultadoDeCanal(canal, False, "canal desconhecido")

    def _dashboard(self, publicacao: dict) -> ResultadoDeCanal:
        """O painel é o registro. A publicação existir É a entrega."""
        return ResultadoDeCanal(
            "dashboard", True,
            "está no painel, em Entregas",
            {"publication_id": publicacao.get("id")})

    def _email(self, publicacao: dict, perfil: dict) -> ResultadoDeCanal:
        """E-mail leva o conteúdo completo. Hoje depende de provedor.

        PENDÊNCIA P-13 — `SENDGRID_API_KEY` está vazia, e o provedor definitivo
        é decisão da SPEC-069 (Amazon SES). O canal fica CONSTRUÍDO e
        DESLIGADO: quando a chave existir, ele entrega sem mais nenhuma
        mudança de código.

        O que ele NÃO faz é fingir. Sem provedor, o motivo é escrito.
        """
        destinos = self._destinatarios(perfil)
        if not destinos:
            return ResultadoDeCanal(
                "email", False,
                "nenhum destinatário de e-mail configurado no perfil")

        try:
            from app.services.email_service import get_email_service
            servico = get_email_service()
        except Exception as exc:  # noqa: BLE001
            return ResultadoDeCanal("email", False,
                                    f"serviço de e-mail indisponível: {type(exc).__name__}")

        if not getattr(servico, "api_key", None):
            return ResultadoDeCanal(
                "email", False,
                "provedor de e-mail não configurado (PENDENCIAS.md P-13)")

        assunto = publicacao.get("headline") or "Seu checklist do AutoBrokers"
        corpo = publicacao.get("summary_text") or ""
        enviados, erros = [], []
        for destino in destinos:
            try:
                ok = servico.send_email(to_email=destino, subject=assunto,
                                        html_content=f"<p>{corpo}</p>")
                (enviados if ok else erros).append(destino)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Entrega] e-mail falhou: %s", type(exc).__name__)
                erros.append(destino)

        if enviados:
            return ResultadoDeCanal("email", True,
                                    f"enviado para {len(enviados)} destinatário(s)",
                                    {"falhas": len(erros)})
        return ResultadoDeCanal("email", False, "nenhum e-mail saiu")

    def _whatsapp(self, publicacao: dict, perfil: dict, decisao) -> ResultadoDeCanal:
        """WhatsApp leva **só a manchete e o link**. Nunca o relatório inteiro.

        E não sai antes do governador de envio existir.

        PENDÊNCIA P-14 — **resolvida na SPEC-063 Bloco C**. Até ela, não havia
        limitação de taxa em lugar nenhum, e mandar briefing por WhatsApp seria
        repetir o defeito da cobrança, que percorria 50 destinatários sem pausa.

        A guarda continua sendo dura de propósito: uma flag de configuração
        poderia ser ligada por engano. Uma dependência de código não. Ela
        permanece aqui — se o governador for removido ou renomeado, este canal
        volta a se fechar sozinho, em vez de passar a enviar sem freio.

        O briefing é mensagem **fria**: é a plataforma falando primeiro. Ele vai
        pela mesma porta governada de qualquer outra fria, e aceita ser adiado.
        """
        try:
            from app.services.whatsapp import outbound_governor
        except Exception:  # noqa: BLE001
            return ResultadoDeCanal(
                "whatsapp", False,
                "governador de envio ainda não existe — o briefing não sai por "
                "WhatsApp até a SPEC-063 Bloco C (PENDENCIAS.md P-14)")

        destinos = self._telefones(perfil)
        if not destinos:
            return ResultadoDeCanal(
                "whatsapp", False,
                "governador presente, mas o perfil não tem nenhum telefone de "
                "WhatsApp em recipient_refs — não há para quem enviar")

        company_id = publicacao.get("company_id")
        if not company_id:
            return ResultadoDeCanal(
                "whatsapp", False,
                "governador presente, mas a publicação não diz de qual corretora "
                "é — sem corretora não há canal nem teto de vazão")

        veredito = outbound_governor.governar_envio_sync(str(company_id))
        if not veredito.pode:
            # Não é falha: é o governador funcionando. O motivo dele já vem
            # escrito para humano — não reescrevo por cima.
            return ResultadoDeCanal("whatsapp", False,
                                    f"governador adiou: {veredito.motivo}",
                                    {"esperar_s": veredito.esperar_s})

        texto = self._manchete_curta(publicacao)
        enviados, erros = [], []
        for numero in destinos:
            try:
                # `temperatura=QUENTE` porque o slot de vazão JÁ foi reservado
                # na linha acima. Pedir de novo por dentro consumiria um segundo
                # slot para a mesma aproximação e travaria o próximo destinatário
                # por mais 4–8 min sem motivo.
                res = outbound_governor.send_to_client_guarded(
                    str(company_id), numero, texto, "briefing",
                    (publicacao.get("headline") or "briefing")[:120],
                    temperatura=outbound_governor.QUENTE)
                res = self._esperar(res)
                (enviados if (res or {}).get("ok") else erros).append(numero)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Entrega] WhatsApp falhou: %s", type(exc).__name__)
                erros.append(numero)

        if enviados:
            return ResultadoDeCanal(
                "whatsapp", True,
                f"governador liberou e a manchete saiu para {len(enviados)} "
                f"número(s)", {"falhas": len(erros)})
        return ResultadoDeCanal("whatsapp", False,
                                "governador liberou, mas nenhuma mensagem saiu "
                                "do canal de WhatsApp da corretora")

    @staticmethod
    def _esperar(resultado: Any) -> dict:
        """`send_to_client_guarded` é corrotina. Este módulo é síncrono."""
        import asyncio
        import inspect

        if not inspect.isawaitable(resultado):
            return resultado or {}
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(resultado) or {}
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, resultado).result(timeout=30) or {}

    def _manchete_curta(self, publicacao: dict) -> str:
        """Manchete + link. Nunca o relatório: WhatsApp não é onde se lê análise.

        O link aponta para o painel, que é onde o briefing já está — a mensagem
        é um aviso com endereço, não uma cópia do conteúdo.
        """
        manchete = str(publicacao.get("headline") or "Seu checklist do AutoBrokers").strip()
        base = (os.getenv("APP_PUBLIC_URL") or "").strip().rstrip("/")
        if base:
            return f"{manchete[:180]}\n\n{base}/dashboard/entregas"
        return manchete[:180]

    def _telefones(self, perfil: dict) -> list[str]:
        refs = perfil.get("recipient_refs")
        if isinstance(refs, dict):
            refs = refs.get("whatsapp") or refs.get("phones") or refs.get("telefones") or []
        elif isinstance(refs, (str, list)):
            # `recipient_refs` plano é lista de e-mail (é assim que `_destinatarios`
            # a lê). Sem a chave explícita de WhatsApp, não há telefone aqui.
            refs = []
        saida = []
        for t in (refs or []):
            digitos = "".join(c for c in str(t) if c.isdigit())
            if len(digitos) >= 10:
                saida.append(digitos)
        return saida

    # ------------------------------------------------------------------

    def _contexto(self, publicacao: dict, perfil: dict) -> ContextoDeEntrega:
        """Traduz a publicação para o que a política sabe julgar."""
        criticos = int(publicacao.get("critical_count") or 0)
        recomendacoes = int(publicacao.get("recommendation_count") or 0)
        return ContextoDeEntrega(
            # Crítico é o que fura o silêncio. Sem item crítico, o briefing é
            # informação do dia — e informação do dia não acorda ninguém.
            severidade="critical" if criticos > 0 else "medium",
            categoria=str(publicacao.get("briefing_type") or ""),
            # "Ação clara" é o que a política exige para permitir push. Um
            # briefing sem nada acionável não vira notificação.
            tem_acao_clara=recomendacoes > 0 or criticos > 0,
            pushes_hoje=self._pushes_hoje(publicacao.get("company_id")),
            operacao_24h=bool(perfil.get("operacao_24h")),
        )

    def _pushes_hoje(self, company_id: Optional[str]) -> int:
        """Quantas publicações já foram entregues hoje — o teto é por dia."""
        if not company_id:
            return 0
        try:
            inicio = _agora().replace(hour=0, minute=0, second=0, microsecond=0)
            r = (self.db.table("briefing_publications")
                 .select("id", count="exact")
                 .eq("company_id", company_id)
                 .in_("delivery_status", ["sent", "partial"])
                 .gte("published_at", inicio.isoformat())
                 .limit(1).execute())
            return int(getattr(r, "count", 0) or 0)
        except Exception:  # noqa: BLE001
            return 0

    def _destinatarios(self, perfil: dict) -> list[str]:
        refs = perfil.get("recipient_refs")
        if isinstance(refs, dict):
            refs = refs.get("email") or refs.get("emails") or []
        if isinstance(refs, str):
            refs = [refs]
        return [e for e in (refs or []) if isinstance(e, str) and "@" in e]

    def _gravar(self, pub_id: str, status: str, detalhe: dict) -> None:
        try:
            self.db.table("briefing_publications").update({
                "delivery_status": status,
                "delivery_detail": detalhe,
            }).eq("id", pub_id).execute()
        except Exception as exc:  # noqa: BLE001
            # Se nem o registro do estado funciona, o `pending` fica — mas
            # ruidoso, no log, com o motivo. Nunca em silêncio.
            logger.error("[Entrega] não consegui gravar o estado de %s: %s",
                         pub_id, type(exc).__name__)
