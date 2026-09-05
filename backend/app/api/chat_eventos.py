# -*- coding: utf-8 -*-
"""O PROTOCOLO do turno — SPEC-096 · BLOCO B.1.

Este módulo é **puro**: só biblioteca padrão. Nada de FastAPI, nada de banco,
nada de rede. Ele é o vocabulário que o `/chat/stream` fala no modo painel, e
por ser puro ele pode ser lido, testado e mutado sem subir o produto inteiro.

```
Envelope(seq, type, turn, payload)   um evento do turno, com `protocol` v1
CATALOGO_DE_ESTAGIOS                 a tool vira FRASE DA CORRETORA
erro_seguro(exc)                     a exceção vira {code, correlation_id, ...}
pecas_do_turno                       o ContextVar onde o Artifact Hub deixa o
                                     que publicou DURANTE este turno
```

🔴 **Três regras que este arquivo existe para cumprir:**

1. **Nada de nome técnico na tela** (R6). O corretor lê *"Consultando a
   apólice"*, nunca `infocap_policy_lookup`. Tool sem entrada no catálogo cai no
   genérico — o estágio some para o usuário, mas o nome do fornecedor nunca
   vaza.
2. **Nada de exceção crua no browser** (R7). `erro_seguro` NUNCA devolve
   `str(exc)`: devolve um código de família, um `correlation_id` novo (para
   casar com o log) e uma frase que alguém entende.
3. **Um evento é um envelope, não um `{"token"}`.** Tipo, sequência e turno
   viajam sempre juntos — é o que permite à tela remontar a ordem e descartar
   duplicata.
"""
from __future__ import annotations

import json
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ===========================================================================
# O protocolo
# ===========================================================================

#: A versão do vocabulário. A tela recusa o que não conhece.
PROTOCOLO = "autobrokers.interaction.v1"

#: Os tipos de evento do modo painel — a ORDEM canônica do turno feliz é
#: `turn.accepted → stage.* → assistant.content.delta* → artifact.ready* →
#: assistant.content.completed → turn.completed`.
TIPOS = (
    "turn.accepted",
    "stage.started",
    "stage.completed",
    "assistant.content.delta",
    "assistant.content.completed",
    "artifact.ready",
    "policy.blocked",
    "policy.notice",
    "error",
    "heartbeat",
    "turn.completed",
)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Envelope:
    """Um evento do turno, pronto para virar uma linha de SSE."""

    seq: int
    type: str
    turn: Any = None
    payload: Dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=_agora)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "protocol": PROTOCOLO,
            "seq": int(self.seq),
            "type": str(self.type),
            "turn": self.turn,
            "payload": self.payload or {},
            "occurred_at": self.occurred_at,
        }

    def sse(self) -> str:
        """A linha de SSE. `ensure_ascii=False` porque a corretora fala português."""
        return "data: %s\n\n" % json.dumps(self.as_dict(), ensure_ascii=False)


class Sequenciador:
    """O `seq` é monotônico POR TURNO — é assim que a tela sabe se perdeu algo."""

    def __init__(self, turno: Any = None) -> None:
        self._n = 0
        self.turno = turno

    def envelope(self, tipo: str, payload: Optional[Dict[str, Any]] = None) -> Envelope:
        self._n += 1
        return Envelope(seq=self._n, type=tipo, turn=self.turno, payload=payload or {})

    def sse(self, tipo: str, payload: Optional[Dict[str, Any]] = None) -> str:
        return self.envelope(tipo, payload).sse()


# ===========================================================================
# O ERRO — família, correlação, frase humana
#
# 🔴 A ordem deste bloco não é decorativa: `_CAMPOS_DO_ERRO` é a DECLARAÇÃO, e
# a conferência no fim do arquivo recusa o módulo inteiro se o construtor
# deixar de honrá-la. Um campo renomeado num lugar só derruba o import — que é
# muito melhor do que um erro sem frase humana chegando à tela.
# ===========================================================================

_CAMPOS_DO_ERRO = ("code", "correlation_id", "message_human")

#: As famílias de falha. O código é o que o log e a tela compartilham; a causa
#: real fica no log do servidor, nunca na resposta.
CODIGOS = {
    "model",
    "tool",
    "retrieval",
    "transport",
    "policy",
    "billing",
    "no_agent",
    "agent_not_found",
    "human_mode",
    "unknown",
}

MENSAGENS_HUMANAS = {
    "model": "Não consegui gerar a resposta agora. Tente de novo em instantes.",
    "tool": "Uma das consultas falhou no meio do caminho. Pode pedir de novo?",
    "retrieval": "Não consegui abrir os documentos da corretora agora. Tente de novo em instantes.",
    "transport": "A conexão caiu no meio da resposta. Pode pedir de novo?",
    "policy": "Não posso seguir com este pedido.",
    "billing": "Os créditos da corretora acabaram. Fale com quem administra a conta.",
    "no_agent": "Nenhum agente configurado para esta corretora.",
    "agent_not_found": "O agente desta conversa nao esta mais disponivel.",
    "human_mode": "Alguem da equipe assumiu esta conversa.",
    "unknown": "Algo deu errado por aqui. Tente de novo em instantes.",
}

#: As famílias que o texto da exceção sugere, quando quem chamou não soube dizer.
#: 📊 As palavras vêm dos erros que o `/chat/stream` já registrava em log.
_PISTAS = (
    ("model", ("rate limit", "openai", "anthropic", "context length", "completion", "api key")),
    ("transport", ("connection", "timeout", "closed", "unreachable", "socket", "eof")),
    ("retrieval", ("qdrant", "embedding", "collection", "vector")),
)


def familia_do_erro(exc: BaseException) -> str:
    """Adivinha a família SEM deixar o texto da exceção sair daqui."""
    texto = ("%s %s" % (type(exc).__name__, exc)).lower()
    for codigo, pistas in _PISTAS:
        if any(p in texto for p in pistas):
            return codigo
    return "unknown"


def erro_seguro(exc: BaseException, *, code: str = "unknown") -> Dict[str, Any]:
    """A exceção vira um erro que pode ir ao browser.

    ⛔ **Nunca** `str(exc)`: o texto de uma exceção carrega URL com token,
    payload de terceiro e nome de pessoa. O que sai daqui é família + a
    correlação para achar o log.
    """
    codigo = code if code in CODIGOS else "unknown"
    if codigo == "unknown":
        codigo = familia_do_erro(exc)
    return {
        "code": codigo,
        "correlation_id": uuid.uuid4().hex,
        "message_human": MENSAGENS_HUMANAS.get(codigo, MENSAGENS_HUMANAS["unknown"]),
    }


# ===========================================================================
# O CATÁLOGO DE ESTÁGIOS — a tool vira frase da corretora
#
# ⛔ O `name` da tool é nome de FORNECEDOR e de ARQUITETURA. Ele não sai daqui.
# 📊 04/09/2026: 38 tools declaradas
#    (`grep -rhn 'name: str = "' backend/app/agents/tools/*.py | sort -u`).
# ===========================================================================

#: 🔴 O genérico vem ANTES do catálogo de propósito: é o padrão, não a exceção.
#: Tool nova, tool de MCP (nome de terceiro), tool que ninguém catalogou — todas
#: caem aqui, e a tela continua dizendo algo verdadeiro.
ESTAGIO_GENERICO = {"key": "generic", "label": "Trabalhando nisso…"}

_DOCUMENTOS = {"key": "documents.reading", "label": "Conferindo documentos"}
_APOLICE = {"key": "policy.reading", "label": "Conferindo a apólice"}
_CARTEIRA = {"key": "portfolio.consulting", "label": "Consultando a carteira"}
_SEGURADORA = {"key": "insurer.consulting", "label": "Consultando a seguradora"}
_FONTES = {"key": "sources.researching", "label": "Pesquisando fontes"}
_RELATORIO = {"key": "report.preparing", "label": "Preparando o relatório"}
_TRABALHO = {"key": "work.organizing", "label": "Organizando o trabalho"}
_EQUIPE = {"key": "team.calling", "label": "Chamando alguém da equipe"}

CATALOGO_DE_ESTAGIOS: Dict[str, Dict[str, str]] = {
    # documentos da corretora
    "knowledge_base_search": _DOCUMENTOS,
    "filesystem_search": _DOCUMENTOS,
    "filesystem_read_section": _DOCUMENTOS,
    "filesystem_get_outline": _DOCUMENTOS,
    "filesystem_get_metadata": _DOCUMENTOS,
    "document_read": _DOCUMENTOS,
    # a apólice do segurado
    "infocap_policy_lookup": _APOLICE,
    "buscar_veiculo": _APOLICE,
    # a carteira e a operação
    "resumo_atendimentos": _CARTEIRA,
    "atlas_rotas": _CARTEIRA,
    "briefing_da_corretora": _CARTEIRA,
    "prioridades_da_corretora": _CARTEIRA,
    "listar_entregas": _CARTEIRA,
    # a seguradora, do outro lado
    "insurer_dispatch": _SEGURADORA,
    "portal_action": _SEGURADORA,
    # fontes externas
    "web_search": _FONTES,
    "web_search_deep": _FONTES,
    "pesquisar_na_web": _FONTES,
    "analisar_site": _FONTES,
    "web_scrape": _FONTES,
    # o entregável
    "gerar_relatorio": _RELATORIO,
    "raio_x_comercial": _RELATORIO,
    "radar_de_renovacoes": _RELATORIO,
    "executive_intelligence": _RELATORIO,
    "csv_analytics": _RELATORIO,
    # o trabalho que fica de pé sozinho
    "executar_auxiliar": _TRABALHO,
    "create_routine": _TRABALHO,
    "list_routines": _TRABALHO,
    "manage_routine": _TRABALHO,
    "avaliar_automacao": _TRABALHO,
    "propor_metrica": _TRABALHO,
    # 📊 lidas na docstring da tool (04/09/2026): as três são ajuste/registro do
    # acompanhamento do corretor, não consulta de dado.
    "monitorar_fonte": _TRABALHO,
    "preferencias_de_briefing": _TRABALHO,
    "responder_recomendacao": _TRABALHO,
    # gente
    "request_human_agent": _EQUIPE,
    # ⚠️ Estas ficam no genérico DE PROPÓSITO: o que elas fazem depende de quem
    # está do outro lado (subagente, API do cliente, servidor de terceiro), e
    # anunciar um passo específico seria inventar.
    "delegate_to_subagent": ESTAGIO_GENERICO,
    "http_api": ESTAGIO_GENERICO,
    "control_plane_read": ESTAGIO_GENERICO,
}


def estagio_da_tool(nome: str) -> Dict[str, str]:
    """A frase que o corretor lê. Tool desconhecida → o genérico, nunca o nome."""
    entrada = CATALOGO_DE_ESTAGIOS.get(str(nome or "").strip())
    return dict(entrada or ESTAGIO_GENERICO)


# ===========================================================================
# As PEÇAS publicadas DURANTE o turno
#
# 🔴 Um ContextVar, e não uma variável de módulo: `asyncio.create_task` COPIA o
# contexto, então cada turno enxerga a própria lista e nenhuma outra. Quem
# publica (`ArtifactService.publicar`) só empurra o `artifact_id`; o título e o
# tipo saem de um SELECT ao fim do turno — 📊 `publicar` seleciona
# `id, artifact_id, version, status, brand_snapshot`, e não tem título nenhum
# para dar.
# ===========================================================================

pecas_do_turno: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "pecas_do_turno", default=None
)


def registrar_peca(artifact_id: str, **extra: Any) -> None:
    """Chamado de dentro do Artifact Hub. Fora de um turno, não faz nada."""
    lista = pecas_do_turno.get(None)
    if lista is None or not artifact_id:
        return
    if any(p.get("artifact_id") == artifact_id for p in lista):
        return
    peca = {"artifact_id": str(artifact_id)}
    peca.update({k: v for k, v in extra.items() if v is not None})
    lista.append(peca)


def href_da_peca(artifact_id: str) -> str:
    return "/dashboard/entregas/%s" % artifact_id


# ===========================================================================
# A CONFERÊNCIA DE IMPORT — o módulo recusa subir mentindo
# ===========================================================================

_amostra = erro_seguro(RuntimeError("uma exceção qualquer"), code="model")
if tuple(sorted(_amostra)) != tuple(sorted(_CAMPOS_DO_ERRO)):
    raise RuntimeError(
        "chat_eventos: `erro_seguro` deixou de honrar os campos declarados em "
        "_CAMPOS_DO_ERRO %r — quem consome o erro na tela quebraria em silêncio."
        % (_CAMPOS_DO_ERRO,)
    )
if set(MENSAGENS_HUMANAS) != CODIGOS:
    raise RuntimeError(
        "chat_eventos: há código sem frase humana (ou frase sem código): %r"
        % (set(MENSAGENS_HUMANAS) ^ CODIGOS,)
    )
del _amostra
