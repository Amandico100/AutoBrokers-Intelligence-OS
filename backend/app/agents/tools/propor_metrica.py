# -*- coding: utf-8 -*-
"""O chat PROPÕE a métrica que não existe — SPEC-094.1 · BLOCO D.

O dono pergunta *"qual a comissão média por produtor só nas apólices de
frota?"*. Não existe. O teto do que este produto faz com isso é **propor**:

```
✅ descrever a métrica que responderia            PropostaDeMetrica
✅ apontar a que já existe e é parecida           parecida_com (ref ②)
✅ registrar a proposta como Work Run + Approval  este arquivo
⛔ calcular                                       nunca
⛔ publicar Artifact com ela                      nunca
⛔ PROMOVER                                       não existe a ferramenta
```

🔴 **A ausência da tool de promover é a peça, não uma omissão.** Modelado no MCP
do Cube (ref ①), que *"deliberately exposes no commit tool"*: remover a
capacidade, não pedir contenção ao prompt. A promoção é um `git commit` de um
humano seguindo `docs/canon/COMO-NASCE-UM-RELATORIO.md`, mais o CLI
`python -m app.comercial.metricas.promover`.

⚠️ Esta tool **não decide se o pedido é legítimo**. Quem descobre que a métrica
não existe é a `executive_intelligence` (`listar_metricas` e a recusa de view
desconhecida); esta aqui só registra o que o dono mandou registrar. Duas
autoridades sobre a mesma pergunta divergiriam no primeiro sinônimo.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, ClassVar, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CARIMBO_REGISTRADA = "PROPOSTA_REGISTRADA"
CARIMBO_JA_EXISTIA = "PROPOSTA_JA_EXISTIA"
CARIMBO_FALHOU = "PROPOSTA_FALHOU"

COMO_FALAR = (
    "Diga ao dono que a proposta foi REGISTRADA PARA REVISÃO — e que nenhum "
    "número foi calculado nem será, até um humano registrar a definição. Cite "
    "o nome sugerido e o id da proposta. Se houver `parecida_com`, ofereça a "
    "métrica que JÁ EXISTE agora mesmo, porque ela responde hoje o que a "
    "proposta responderia depois. Você não aprova e não promove nada: quem "
    "decide é gente."
)


class RecusaSemTenant(RuntimeError):
    """Não há corretora nesta sessão. 🔴 Levanta — não grava "para ninguém"."""


class PedidoDeMetrica(BaseModel):
    """O que o modelo preenche. ⛔ Nenhum campo aceita um NÚMERO."""

    pedido: str = Field(
        description=(
            "A pergunta do dono, como ele falou: 'comissão média por produtor "
            "só nas apólices de frota'. É dela que sai o nome sugerido e a "
            "busca por métrica parecida. Obrigatório."),
    )
    confirmado: bool = Field(
        default=False,
        description=(
            "true SOMENTE depois de o dono dizer que quer registrar a "
            "proposta. Pergunte antes: 'quer que eu registre a proposta para "
            "revisão?'. Sem confirmação, esta ferramenta não grava nada."),
    )


class ProporMetricaTool(BaseTool):
    """Registra uma proposta de métrica como trabalho durável com aprovação."""

    exige_async: ClassVar[bool] = True

    name: str = "propor_metrica"
    description: str = (
        "REGISTRA A PROPOSTA de uma métrica que o sistema ainda NÃO tem, "
        "quando o dono pede um número que não existe e CONFIRMA que quer a "
        "proposta registrada. Ela cria um pedido de revisão para um humano — "
        "não calcula nada, não devolve número e não cria a métrica. "
        "Antes de usar, confira o que já existe com a ferramenta de panorama "
        "executivo em modo `listar_metricas`: a métrica pedida quase sempre já "
        "está lá com outro nome. "
        "NUNCA use para responder uma pergunta; use para registrar que ela "
        "ficou sem resposta."
    )
    args_schema: Type[BaseModel] = PedidoDeMetrica

    company_id: Optional[str] = None
    supabase: Any = None
    #: Quem pediu, quando o grafo souber. Vai como `source_id` do run.
    solicitante: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        raise RuntimeError(
            "ProporMetricaTool exige execução assíncrona. Quem chamou ignorou "
            "`exige_async=True` — o executor precisa aguardar `_arun`.")

    async def _arun(self, pedido: str = "", confirmado: bool = False,
                    **_: Any) -> str:
        try:
            return await self._montar(pedido, confirmado)
        except Exception as exc:  # noqa: BLE001
            logger.error("[094.1 PROPOSTA] falhou (%s): %s",
                         type(exc).__name__, exc)
            return self._erro_legivel(exc)

    # ------------------------------------------------------------------ #
    async def _montar(self, pedido: str, confirmado: bool) -> str:
        company_id = str(self.company_id or "").strip()
        if not company_id:
            raise RecusaSemTenant(
                "não há corretora nesta sessão: uma proposta sem `company_id` "
                "apareceria no painel da corretora errada")
        texto = str(pedido or "").strip()
        if not texto:
            raise ValueError("proposta sem pedido: não há o que propor")

        from app.comercial.metricas import registry
        from app.comercial.proposta import propor_a_partir_do_pedido

        proposta = propor_a_partir_do_pedido(texto, registry.todas(),
                                             registry.POLICY_VALID_FROM)

        # 🔴 Sem confirmação, NADA é gravado — e a resposta já traz a
        # duplicata. É a ordem do Euno (ref ②): revisar contra o catálogo ANTES
        # de a proposta existir, porque duplicata é o modo de falha real.
        if not confirmado:
            return ("PROPOSTA_NAO_CONFIRMADA · nada foi registrado.\n\n"
                    + proposta.frase()
                    + "\n\nPergunte ao dono se ele quer que você registre esta "
                    "proposta para revisão, e só chame esta ferramenta de novo "
                    "com `confirmado=true` depois que ele disser que sim.")

        db = getattr(self.supabase, "client", self.supabase)
        if db is None:
            raise RuntimeError("sem cliente de banco para registrar a proposta")
        saida = await asyncio.to_thread(self._registrar, db, company_id,
                                        proposta)

        carimbo = CARIMBO_JA_EXISTIA if saida.get("reused") else CARIMBO_REGISTRADA
        corpo = json.dumps({
            "run_id": saida.get("run_id"),
            "approval_id": saida.get("approval_id"),
            "estado": "em revisão — nenhum número foi calculado",
            **proposta.serializar(),
        }, ensure_ascii=False, allow_nan=False)
        return (f"{carimbo} · a proposta `{proposta.nome_sugerido}` está "
                "aguardando decisão de um humano. NENHUM número foi "
                "calculado.\n\n"
                f"<<PROPOSTA\n{corpo}\nPROPOSTA>>\n\n{COMO_FALAR}")

    # ------------------------------------------------------------------ #
    def _registrar(self, db: Any, company_id: str, proposta: Any) -> dict:
        """A escrita inteira, FORA do event loop.

        🔴 `propor()` é uma corrotina — porque `criar_registro_sem_fila` serve
        os dois clientes, o síncrono e o assíncrono —, mas metade do que ela
        chama é I/O **bloqueante**: `WorkApprovalService.solicitar()` e o
        `INSERT` de `work_events` usam o cliente síncrono do Supabase. Deixá-los
        no loop travaria TODAS as conversas do processo enquanto a proposta é
        gravada, que é a lição medida da 081 (`asyncio.to_thread` nas duas
        tools comerciais).

        ⚠️ Por isso um `asyncio.run` DENTRO da thread: um loop novo, num
        trabalhador que não é o do FastAPI, e a corrotina roda inteira ali.
        """
        from app.services.work.metric_proposal import propor

        return asyncio.run(propor(db, company_id=company_id,
                                  proposta=proposta,
                                  solicitante=self.solicitante))

    # ------------------------------------------------------------------ #
    @staticmethod
    def _erro_legivel(exc: Exception) -> str:
        nome = type(exc).__name__
        conhecida = nome.startswith("Falha") or nome.startswith("Recusa")
        motivo = str(exc)[:220] if conhecida else nome
        return (
            f"{CARIMBO_FALHOU} · a proposta NÃO foi registrada. É PROIBIDO "
            "dizer que ela está em revisão, e é PROIBIDO responder a pergunta "
            "do dono com qualquer número. Diga a verdade e ofereça tentar de "
            f"novo. Motivo interno: {motivo}"
        )


# --------------------------------------------------------------------------
def ferramenta_de_proposta(*, company_id: Optional[str],
                           supabase: Any) -> List[BaseTool]:
    """A tool, ou lista vazia. Nunca levanta na montagem do grafo.

    🔴 Ela entra pela LISTA de `ferramentas_comerciais`, herdando o `if` de
    papel de `graph.py:528`. Fora dele, o agente de ATENDIMENTO poderia abrir
    `work_runs` em nome da corretora a partir de uma frase do segurado.
    """
    if not company_id or supabase is None:
        return []
    supabase = getattr(supabase, "client", supabase)
    return [ProporMetricaTool(company_id=str(company_id), supabase=supabase)]
