"""Registro de invocação de ferramenta. SPEC-056 §Tool Gateway.

Por que este arquivo existe
---------------------------
O `ToolGateway` já tinha `registrar_invocacao()` e `finalizar_invocacao()`
escritos — e **ninguém os chamava**. A consequência apareceu no Bloco 0 da
SPEC-061 como um número:

    tool_invocations = 0

com 43 Work Runs concluídos e o produto em uso. O Gateway decidia *quais*
ferramentas o agente recebia e depois perdia a chamada de vista: a execução
acontecia no `tool_node` do LangGraph, que não falava com ele.

O que se perde sem este registro:

* **diagnóstico** — o corretor diz "ele não conseguiu consultar a apólice" e
  não há como saber se a ferramenta falhou, se foi negada por capability ou se
  o modelo nunca a chamou;
* **custo** — invocação sem registro é custo sem dono;
* **o Admin da SPEC-061** — que governa exatamente estes objetos e, sem eles,
  seria uma tela sobre tabela vazia;
* **a prova de que o Gateway é o caminho** — sem invocação gravada, "passou
  pelo Gateway" é afirmação sem evidência.

O que este módulo NÃO é
-----------------------
Não é um segundo Gateway nem um writer paralelo. Ele **chama** os métodos que
já existem em `ToolGateway`. A única coisa nova aqui é o ponto de amarração
entre o executor de ferramenta e o Gateway.

Regra de ouro: **falhar ao registrar nunca derruba a ferramenta**. Contabilidade
quebrada é ruim; trabalho do corretor perdido é pior.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from contextvars import ContextVar
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ===========================================================================
# A LIGAÇÃO COM O TURNO — P-PILOTO-18, reescrita
#
# 🔴 A PENDÊNCIA ESTAVA VENCIDA. Ela dizia "o chat não registra que ferramenta
# o agente chamou … sem `tool_invocations`". 📊 Conferido em 14/09/2026: a
# tabela existe, tem 277 linhas (140 desde 09/09) e o chat grava nela desde
# `nodes.py:1057`. Escrever a SPEC pela pendência teria criado uma SEGUNDA
# gravação de tool call ao lado da que existe — motor paralelo (CLAUDE.md §5).
#
# O que faltava era a JUNÇÃO: `messages.payload.turn` conhece o
# `client_request_id`; `tool_invocations` conhecia só o `session_id`. Quem
# perguntasse "que ferramentas ESTE turno chamou?" não tinha por onde.
#
# 🔴 A ESCOLHA DA CHAVE, com nota (protocolo §9). Notas do builder E, 14/09:
#
#   (a) `trace_id = "<session_id>|<client_request_id>"`          nota 88  ← ESCOLHIDA
#       coluna que JÁ existe, escritor que JÁ existe, ZERO DDL — e por isso
#       esta SPEC continua com UMA migration só (a de dado). 📊 `grep -rn
#       "trace_id" backend/app --include=*.py` em 14/09 devolve 6 linhas,
#       TODAS de escrita: não há leitor para quebrar. A sessão continua
#       legível (prefixo), e o turno vira sufixo exato.
#   (b) `trace_id = client_request_id` quando existir, senão `session_id`
#                                                                nota 62
#       a mesma coluna passa a guardar DUAS coisas sem marcador — quem lesse
#       não saberia qual das duas tem na mão (CLAUDE.md §12.1).
#   (c) chave nova dentro de `input_summary` (jsonb)             nota 55
#       `input_summary` é o resumo REDIGIDO dos ARGUMENTOS. Meter roteamento
#       ali é um nome que mente, e a consulta por jsonb é mais cara que por
#       uma coluna text já indexada por `(company_id, started_at)`.
#
# ⚠️ Por que ContextVar e não uma chave no estado do grafo: `AgentState` é um
# `TypedDict` e o `StateGraph` monta os canais a partir das ANOTAÇÕES dele —
# uma chave não declarada é descartada. Declará-la criaria um canal novo no
# checkpointer (que é banco) para carregar um id de request. O ContextVar é o
# mesmo padrão que o `/chat/stream` já usa para as peças do turno
# (`pecas_do_turno`, `app/api/chat.py`): a task COPIA o contexto no
# `create_task`, e o nó de tool roda dentro dela.
# ===========================================================================

#: O turno em voo neste contexto async. `None` fora de um turno de chat (uma
#: Rotina, um Work Run, o worker) — e aí o rastro é só a sessão, como era.
TURNO_EM_CURSO: ContextVar[Optional[str]] = ContextVar(
    "autobrokers_turno_em_curso", default=None)


def marcar_turno(client_request_id: Optional[str]):
    """Declara qual turno está em voo. Devolve o token para `reset`, se quiser."""
    valor = str(client_request_id).strip() if client_request_id else None
    return TURNO_EM_CURSO.set(valor or None)


def turno_em_curso() -> Optional[str]:
    """O turno em voo, ou `None`. Nunca levanta."""
    try:
        return TURNO_EM_CURSO.get()
    except LookupError:  # pragma: no cover — só se o default sumir
        return None


#: 🔴 A marca do que foi invocado FORA de um turno de chat (Rotina, Work Run,
#: worker, ou um turno que não trouxe `client_request_id`).
#:
#: Ela existe porque `chave_de_rastro(sessao, None)` devolvia **a sessão pura** —
#: e a sessão pura é um PREFIXO de nada e um IGUAL de tudo: a leitura do
#: `/chat/stream`, num turno sem `client_request_id`, montava a mesma chave e o
#: `.eq("trace_id", chave)` colhia as invocações de QUALQUER outro momento
#: daquela sessão, apresentando-as como "as ferramentas deste turno".
#: 📊 Medido em 14/09/2026: `chave_de_rastro(s, None) == s` e
#: `_abrir_registro_de_invocacao` grava exatamente isso fora de turno.
MARCA_SEM_TURNO = "-"


def chave_de_rastro(session_id: Any, turno: Optional[str] = None) -> Optional[str]:
    """O `trace_id` que liga a invocação ao TURNO — um formato só, num lugar só.

    🔴 Quem GRAVA (`nodes._abrir_registro_de_invocacao`) e quem LÊ (o
    `/chat/stream`, ao montar `payload.turn.tool_calls`) chamam ESTA função. Duas
    montagens do mesmo formato escritas separado divergem, e a junção volta
    vazia sem ninguém ver — exatamente o defeito que o CLAUDE.md §9.4 descreve.

    ```
    com turno   "<sessao>|<client_request_id>"   a chave de UM turno
    sem turno   "<sessao>|-"                     DISTINGUIVEL, e nunca igual a nenhuma
    ```

    ⚠️ A chave sem turno **não é chave de leitura de turno nenhum**: quem lê o
    turno só monta a chave quando tem `client_request_id` (`chat.py`). O `|-`
    existe para que, mesmo se alguém a montasse, ela não casasse com a de um
    turno real.
    """
    if turno is None:
        turno = turno_em_curso()
    sessao = str(session_id or "").strip()
    marca = str(turno or "").strip()
    if not sessao:
        return None
    return "%s|%s" % (sessao, marca or MARCA_SEM_TURNO)

# Cache de processo: tool_key -> (tool_release_id, capability_key) ou None.
# O catálogo muda por deploy/publicação, não por turno de conversa. Consultar o
# banco a cada chamada de ferramenta somaria latência à conversa do corretor
# para reler uma linha que não mudou.
_CATALOGO: dict[str, Optional[tuple[str, str]]] = {}

# Campos que nunca entram no resumo da entrada, nem truncados. `input_summary`
# é um jsonb que fica no banco e aparece no Admin — CPF de segurado e telefone
# de cliente não têm o que fazer ali.
_CAMPOS_SENSIVEIS = frozenset({
    "cpf", "cnpj", "documento", "document", "telefone", "phone", "email",
    "senha", "password", "token", "api_key", "secret", "chave", "authorization",
    "placa", "numero_apolice", "policy_number", "cartao", "card",
})


def _carregar(db: Any, tool_key: str) -> Optional[tuple[str, str]]:
    """`(tool_release_id, capability_key)` da release publicada padrão."""
    if tool_key in _CATALOGO:
        return _CATALOGO[tool_key]

    encontrado: Optional[tuple[str, str]] = None
    try:
        cliente = getattr(db, "client", db)
        defs = (cliente.table("tool_definitions")
                .select("id, capability_key")
                .eq("tool_key", tool_key).eq("is_active", True)
                .limit(1).execute()).data or []
        if defs:
            rels = (cliente.table("tool_releases")
                    .select("id, is_default")
                    .eq("tool_id", defs[0]["id"]).eq("status", "published")
                    .execute()).data or []
            escolhida = next((r for r in rels if r.get("is_default")),
                             rels[0] if rels else None)
            if escolhida:
                encontrado = (escolhida["id"], defs[0].get("capability_key") or "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Invocacao] catalogo de %s: %s", tool_key, type(exc).__name__)
        # NÃO cacheia o negativo quando a falha foi de leitura: um erro de rede
        # transitório deixaria a ferramenta sem registro até o próximo deploy.
        return None

    _CATALOGO[tool_key] = encontrado
    if encontrado is None:
        # Aqui o negativo É cacheado: a ferramenta simplesmente não está no
        # Registry, e isso só muda com publicação — que reinicia o processo.
        logger.info("[Invocacao] '%s' não está no Registry; sem registro", tool_key)
    return encontrado


def fingerprint(argumentos: dict) -> str:
    """Identidade da entrada sem guardar a entrada.

    É o que permite dizer "esta é a mesma chamada de antes" sem manter o CPF do
    segurado no banco de auditoria.
    """
    try:
        canonico = json.dumps(argumentos or {}, sort_keys=True,
                              ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        canonico = str(argumentos)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:32]


def resumo_da_entrada(argumentos: dict) -> dict:
    """Resumo auditável: quais campos vieram, não o que havia neles."""
    resumo: dict[str, Any] = {}
    for chave, valor in (argumentos or {}).items():
        nome = str(chave).lower()
        if any(s in nome for s in _CAMPOS_SENSIVEIS):
            resumo[chave] = "[omitido]"
        elif isinstance(valor, (int, float, bool)) or valor is None:
            resumo[chave] = valor
        elif isinstance(valor, str):
            resumo[chave] = {"tipo": "texto", "tamanho": len(valor)}
        elif isinstance(valor, (list, tuple)):
            resumo[chave] = {"tipo": "lista", "itens": len(valor)}
        elif isinstance(valor, dict):
            resumo[chave] = {"tipo": "objeto", "campos": len(valor)}
        else:
            resumo[chave] = {"tipo": type(valor).__name__}
    return resumo


class RegistroDeInvocacao:
    """Contexto de uma chamada. Use como gerenciador de contexto.

    ```python
    with RegistroDeInvocacao(db, company_id=cid, nome_da_tool="web_search",
                             argumentos=args) as reg:
        resultado = tool._run(**args)
        reg.ok(resultado)
    ```

    Sem `ok()` e sem exceção, a invocação fecha como `failed` — porque uma
    invocação que abre e não fecha é pior que nenhuma: ela fica eternamente
    "running" e polui qualquer contagem de trabalho em andamento.
    """

    def __init__(self, db: Any, *, company_id: Optional[str],
                 nome_da_tool: str, argumentos: Optional[dict] = None,
                 work_run_id: Optional[str] = None,
                 work_step_id: Optional[str] = None,
                 skill_release_id: Optional[str] = None,
                 trace_id: Optional[str] = None):
        self.db = db
        self.company_id = str(company_id) if company_id else None
        self.nome_da_tool = nome_da_tool
        self.argumentos = argumentos or {}
        self.work_run_id = work_run_id
        self.work_step_id = work_step_id
        self.skill_release_id = skill_release_id
        self.trace_id = trace_id
        self.invocation_id: Optional[str] = None
        self._inicio = 0.0
        self._fechado = False

    def __enter__(self) -> "RegistroDeInvocacao":
        self._inicio = time.monotonic()
        self._abrir()
        return self

    def __exit__(self, tipo, valor, tb) -> bool:
        if not self._fechado:
            if tipo is not None:
                self.erro(codigo=getattr(valor, "__class__", type(valor)).__name__)
            else:
                # Saiu sem chamar ok() nem levantar: fecha como falha, porque
                # não sabemos se deu certo e "running" para sempre é pior.
                self.erro(codigo="sem_resultado")
        return False  # nunca engole a exceção da ferramenta

    # ------------------------------------------------------------------

    def _abrir(self) -> None:
        if not self.company_id or not self.db:
            return
        try:
            from ...agents.gateway_cutover import chave_de_registro
            from .gateway import ToolGrant, ToolGateway

            tool_key = chave_de_registro(_Nomeada(self.nome_da_tool))
            catalogo = _carregar(self.db, tool_key)
            if not catalogo:
                return
            release_id, capability_key = catalogo

            fp = fingerprint(self.argumentos)
            # A chave de invocação inclui o instante: duas consultas iguais na
            # mesma conversa são DUAS chamadas, e colapsá-las esconderia
            # repetição — que é justamente um sintoma que o Admin precisa ver.
            chave = f"{self.work_run_id or 'chat'}:{tool_key}:{fp}:{int(time.time()*1000)}"

            gateway = ToolGateway(self.db)
            grant = ToolGrant(
                tool_key=tool_key, tool_release_id=release_id,
                capability_key=capability_key, implementation_kind="native",
                name=self.nome_da_tool, description="", input_schema={},
                side_effect_class="read", risk_level="low",
                requires_approval=False, requires_connection=False)
            self.invocation_id = gateway.registrar_invocacao(
                company_id=self.company_id, grant=grant, invocation_key=chave,
                input_fingerprint=fp, status="running",
                work_run_id=self.work_run_id, work_step_id=self.work_step_id,
                skill_release_id=self.skill_release_id,
                input_summary=resumo_da_entrada(self.argumentos),
                trace_id=self.trace_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Invocacao] não aberta para %s: %s",
                           self.nome_da_tool, type(exc).__name__)

    def ok(self, resultado: Any = None) -> None:
        self._fechar("succeeded", resultado=resultado)

    def erro(self, *, codigo: str) -> None:
        self._fechar("failed", codigo=codigo)

    def negada(self, *, motivo: str) -> None:
        """Negativa também é registro — §Gateway.

        É assim que o Admin descobre que o corretor está esbarrando numa
        conexão faltando, em vez de só ver o agente "não conseguindo".
        """
        self._fechar("denied", codigo=motivo)

    def _fechar(self, status: str, *, resultado: Any = None,
                codigo: Optional[str] = None) -> None:
        if self._fechado:
            return
        self._fechado = True
        if not self.invocation_id:
            return
        try:
            from .gateway import ToolGateway

            ToolGateway(self.db).finalizar_invocacao(
                self.invocation_id, status=status,
                output_summary=_resumo_da_saida(resultado),
                latency_ms=int((time.monotonic() - self._inicio) * 1000),
                error_code=codigo)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Invocacao] não fechada: %s", type(exc).__name__)


class _Nomeada:
    """Adaptador mínimo: `chave_de_registro` espera algo com `.name`."""

    def __init__(self, nome: str):
        self.name = nome


#: 🔴 SPEC-EXTRA-001.5 BLOCO E — A PROCEDÊNCIA DA RESPOSTA DE COBERTURA.
#:
#: A lista é FECHADA de propósito. Copiar o dict inteiro que vier na chave
#: `cobertura` transformaria este resumo num campo livre: bastaria alguém
#: acrescentar `pergunta` ou `cliente` ao veredito para o CPF do segurado
#: passar a ser gravado em `tool_invocations` sem ninguém ver. 📊 Hoje são
#: 289 linhas e ZERO CPF cru (17/09/2026), e é assim que continua.
#:
#: ⚠️ `documento` já vem como presença (`"presente"`/`"ausente"`) de
#: `VereditoDeCobertura.para_registro()`; o `documento_id` é um UUID interno,
#: não é dado de pessoa, e é o que liga a resposta à condição geral citada.
_CAMPOS_DA_ORIGEM = (
    "estado", "servico", "tipo", "insurer_key", "ramo", "produto", "plano",
    "nivel", "plano_id", "documento_id", "pagina", "documento", "origem",
    "confianca", "gancho",
)


def _origem_da_cobertura(cobertura: Any) -> Optional[dict]:
    """Só os campos da lista fechada, e só escalares. Nada mais entra."""
    if not isinstance(cobertura, dict) or not cobertura.get("estado"):
        return None
    fora = {}
    for chave in _CAMPOS_DA_ORIGEM:
        valor = cobertura.get(chave)
        if valor is None or isinstance(valor, (str, int, float, bool)):
            fora[chave] = valor
    return fora


def _resumo_da_saida(resultado: Any) -> dict:
    """Tamanho e forma da saída — nunca o conteúdo.

    O retorno de uma ferramenta pode conter dado de segurado. O que o Admin
    precisa saber é se veio vazio, se veio grande demais, se deu erro — não o
    que estava escrito.
    """
    if resultado is None:
        return {"vazio": True}
    if isinstance(resultado, str):
        return {"tipo": "texto", "tamanho": len(resultado),
                "vazio": not resultado.strip()}
    if isinstance(resultado, dict):
        resumo = {"tipo": "objeto", "campos": sorted(resultado.keys())[:20],
                  "ok": bool(resultado.get("ok", True))}
        origem = _origem_da_cobertura(resultado.get("cobertura"))
        if origem:
            resumo["cobertura"] = origem
        return resumo
    if isinstance(resultado, (list, tuple)):
        return {"tipo": "lista", "itens": len(resultado)}
    return {"tipo": type(resultado).__name__}
