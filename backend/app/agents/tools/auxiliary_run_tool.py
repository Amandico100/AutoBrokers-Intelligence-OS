"""O chat manda um Auxiliar trabalhar agora. SPEC-064 Bloco G.

A lacuna que este arquivo fecha
-------------------------------
O plano de execução tinha isto como decisão **D9**:

    "O chat principal chama qualquer auxiliar. O corretor pede no chat e
     recebe ali mesmo, na hora — em vez de esperar a rotina. Mesmo motor,
     resposta síncrona."

E **nenhuma SPEC a implementou.** A SPEC-064 Bloco G cobria criar e editar
Auxiliar pelo chat; executar caiu entre as SPECs. O corretor podia instalar um
Auxiliar e depois esperar a rotina — mesmo quando queria o resultado agora.

O que este módulo NÃO é
-----------------------
**Não é um segundo executor.** Ele enfileira `bridge.auxiliary.execute`, que é
o mesmo workflow que a Rotina usa. Um Auxiliar chamado pelo chat e chamado
pela agenda percorre o MESMO caminho, passa pelos MESMOS gates e produz o
MESMO Artifact (CLAUDE.md §5).

A diferença é só quem puxou o gatilho — e isso fica registrado em
`source_type`, para o histórico saber distinguir "rodou porque eu pedi" de
"rodou sozinho".
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class _ExecutarIn(BaseModel):
    slug: str = Field(
        description="O identificador do Auxiliar, como aparece no catálogo "
                    "(ex.: 'cobranca-feita', 'checklist-6h'). Se o corretor "
                    "disse o nome ('a Cobrança'), traduza para o slug.")
    observacao: Optional[str] = Field(
        default=None,
        description="O que o corretor pediu de diferente nesta execução, nas "
                    "palavras dele. Não vira configuração permanente.")


class AuxiliaryRunTool(BaseTool):
    """Roda AGORA um Auxiliar que a corretora já ligou.

    Use quando o corretor pedir o trabalho de um Auxiliar sem querer esperar a
    rotina: *"roda a cobrança agora"*, *"me dá o checklist de hoje"*.

    NÃO use para:
      * ligar um Auxiliar que ele não instalou — isso é decisão dele, na tela
      * Auxiliar em "em breve" — não existe ainda
      * criar rotina — para isso existe a ferramenta da Factory
    """

    name: str = "executar_auxiliar"
    description: str = (
        "Roda agora um Auxiliar que a corretora JÁ tem ligado, sem esperar a "
        "rotina. Informe o slug do Auxiliar. Devolve o número do trabalho para "
        "acompanhar. Não liga Auxiliar desligado e não cria nada."
    )
    args_schema: Type[BaseModel] = _ExecutarIn

    supabase_client: Any = None
    company_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, supabase_client: Any, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.supabase_client = supabase_client
        self.company_id = company_id

    # ------------------------------------------------------------------

    def _run(self, slug: str, observacao: Optional[str] = None,
             user_id: Optional[str] = None, **_) -> str:
        """`user_id` chega POR TURNO, injetado pelo nó de ferramentas.

        Ele não pode vir do construtor: o grafo é cacheado por (empresa,
        agente) e reusado em muitas conversas — um usuário amarrado na
        montagem faria o trabalho de uma pessoa nascer no nome de outra.
        """
        if not self.company_id:
            return "Não consegui identificar a corretora desta conversa."

        db = getattr(self.supabase_client, "client", self.supabase_client)
        slug = (slug or "").strip().lower()
        if not slug:
            return "Preciso saber qual Auxiliar você quer que eu rode."

        instalado = self._instalado(db, slug)
        if not instalado:
            return self._explicar_ausencia(db, slug)

        if instalado.get("status") != "active":
            nome = instalado.get("name") or slug
            return (f"O {nome} está desligado. Você pode ligar em Auxiliares — "
                    f"eu não ligo por conta própria, porque quem decide o que "
                    f"trabalha para você é você.")

        return self._enfileirar(instalado, observacao, user_id)

    async def _arun(self, slug: str, observacao: Optional[str] = None,
                    user_id: Optional[str] = None, **kwargs) -> str:
        import asyncio

        return await asyncio.to_thread(self._run, slug, observacao,
                                       user_id=user_id, **kwargs)

    # ------------------------------------------------------------------

    def _instalado(self, db, slug: str) -> Optional[dict]:
        """A instalação DESTA corretora. O filtro por company_id é obrigatório."""
        try:
            r = (db.table("tenant_auxiliaries")
                 .select("id, slug, name, status, config")
                 .eq("company_id", self.company_id)
                 .eq("slug", slug)
                 .maybe_single().execute())
            return (r.data or None) if r else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ExecutarAuxiliar] leitura falhou: %s", type(exc).__name__)
            return None

    def _explicar_ausencia(self, db, slug: str) -> str:
        """Não instalado é diferente de não existir — e a resposta muda."""
        try:
            r = (db.table("auxiliary_templates")
                 .select("name, catalog_state, missing_for_launch")
                 .eq("slug", slug).maybe_single().execute())
            tpl = (r.data or None) if r else None
        except Exception:  # noqa: BLE001
            tpl = None

        if not tpl:
            return (f"Não encontrei um Auxiliar chamado '{slug}'. "
                    f"Você pode ver todos em Auxiliares.")

        nome = tpl.get("name") or slug
        if tpl.get("catalog_state") == "coming_soon":
            falta = tpl.get("missing_for_launch") or ""
            return (f"O {nome} ainda não está pronto. "
                    + (f"{falta} " if falta else "")
                    + "Assim que estiver, ele aparece disponível em Auxiliares.")

        return (f"O {nome} existe, mas a sua corretora ainda não ligou. "
                f"Ele está em Auxiliares — dá para ligar em um clique, e "
                f"desligar quando quiser.")

    def _enfileirar(self, instalado: dict, observacao: Optional[str],
                    user_id: Optional[str] = None) -> str:
        """Mesmo workflow da Rotina. Só a origem muda."""
        try:
            from app.services.work.runs import WorkRunService
        except Exception as exc:  # noqa: BLE001
            logger.error("[ExecutarAuxiliar] motor indisponível: %s", type(exc).__name__)
            return "O motor de trabalhos não está disponível agora."

        nome = instalado.get("name") or instalado.get("slug")
        aux_id = instalado.get("id")

        # A chave de idempotência inclui o minuto: dois pedidos iguais no mesmo
        # minuto reaproveitam o run, e o corretor não dispara dois trabalhos
        # por ter mandado a mensagem duas vezes.
        from datetime import datetime, timezone

        minuto = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        chave = f"chat:{self.company_id}:{aux_id}:{minuto}"

        try:
            linha = WorkRunService(self.supabase_client).criar(
                company_id=self.company_id,
                source_type="chat",          # a origem que distingue do agendado
                outcome_type="auxiliary.run",
                outcome_title=f"{nome} — pedido no chat",
                workflow_key="bridge.auxiliary.execute",
                idempotency_key=chave,
                input_payload={
                    "tenant_auxiliary_id": aux_id,
                    # A observação vai como contexto DESTA execução. Ela não
                    # vira configuração: para gravar preferência existe a rota
                    # de config, e ela pede confirmação explícita.
                    "observacao_do_pedido": observacao or None,
                },
                requester_user_id=user_id,
                priority=40,                 # pedido humano na frente do agendado
                risk_level="low",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[ExecutarAuxiliar] enfileiramento falhou: %s", type(exc).__name__)
            return (f"Não consegui colocar o {nome} para rodar agora. "
                    f"Tente de novo em instantes.")

        run_id = linha.get("run_id") or linha.get("id")
        if linha.get("reused"):
            return (f"O {nome} já está rodando — pedi há pouco. "
                    f"O resultado aparece em Entregas.")

        return (f"Coloquei o {nome} para rodar agora. "
                f"O resultado aparece em Entregas quando terminar"
                + (f" (trabalho {str(run_id)[:8]})." if run_id else "."))
