"""A Factory pelo chat. SPEC-058 §9 e §14.

É o que fecha a promessa do produto:

    "Um único comando central que entende o negócio da corretora, escolhe a
     Skill correta, delega para o Auxiliar adequado e entrega o trabalho."

O corretor diz *"queria que alguém acompanhasse os boletos vencendo"* e o
sistema responde com uma **proposta**, não com uma criação.

Por que propor e não criar
--------------------------
Criar Auxiliar no meio de uma conversa produz coisas que ninguém pediu e
ninguém sabe desligar. Seis meses depois a corretora tem onze auxiliares, três
fazendo a mesma coisa, e ninguém lembra quem criou. A proposta separa a
intenção da instalação — e a instalação passa pela tela, onde há botão de
desfazer.

E quando o sistema **não** sabe fazer, ele diz isso e registra a lacuna. Um
"não consigo" honesto que vira dado de roadmap vale mais do que um Auxiliar
meia-boca que o corretor desliga na primeira semana.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class _PedidoIn(BaseModel):
    pedido: str = Field(
        description="O que o corretor quer que aconteça, nas palavras dele. "
                    "Não reescreva nem resuma — o texto original é o que agrupa "
                    "pedidos iguais de corretoras diferentes.")


class AvaliarAutomacaoTool(BaseTool):
    """Decide o padrão de trabalho certo. Nunca cria nada sozinha."""

    name: str = "avaliar_automacao"
    description: str = (
        "Use quando o corretor pedir para algo passar a acontecer sozinho, ou disser "
        "que queria que alguém cuidasse de alguma coisa: acompanhar boletos, avisar "
        "sobre renovações, cuidar da cobrança, mandar relatório toda semana. "
        "Devolve a PROPOSTA do formato certo — trabalho único, rotina ou Auxiliar — "
        "e diz se já existe algo pronto que resolve. Não cria nada: apresente a "
        "proposta ao corretor e espere ele confirmar."
    )
    args_schema: Type[BaseModel] = _PedidoIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, pedido: str, **_: Any) -> str:
        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora para avaliar isso."

        from ...services.auxiliaries.factory import AuxiliaryFactory

        try:
            f = AuxiliaryFactory(self.supabase)
            r = f.avaliar(company_id=self.company_id, texto=pedido,
                          user_id=self.user_id, source="chat")
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Factory] avaliacao falhou")
            return (f"Não consegui avaliar isso agora ({type(exc).__name__}). "
                    "Posso fazer o trabalho uma vez, se você quiser.")

        partes: list[str] = []

        reusa = r.get("reusa")
        if reusa:
            # Reuso vem primeiro e sozinho: propor criar algo novo quando já
            # existe é o jeito mais rápido de parecer burro.
            partes.append(r.get("mensagem_humana") or "Já existe algo que faz isso.")
            partes.append("\n[Não crie nada. Apresente esta informação ao corretor "
                          "e pergunte se ele quer ajustar o que já existe.]")
            return "\n".join(partes)

        padrao = r.get("padrao")
        rotulos = {
            "one_shot_work_run": "fazer agora, uma vez",
            "saved_routine": "uma rotina, rodando sozinha na agenda",
            "installed_auxiliary": "um Auxiliar instalado, com configuração e histórico próprios",
            "workflow_instance": "um fluxo com etapas que dependem umas das outras",
            "specialized_executor": "um executor determinístico",
            "agent_backed_auxiliary": "um Auxiliar com raciocínio próprio",
        }
        partes.append(f"**Formato indicado:** {rotulos.get(padrao, padrao)}")
        partes.append(f"_Motivo:_ {r.get('motivo')}")

        skill = r.get("skill")
        if skill:
            partes.append(f"_Já existe a capacidade **{skill.get('nome')}** para isso._")
        elif padrao in ("saved_routine", "installed_auxiliary"):
            # Sem Skill publicada, prometer recorrência é prometer o que não se
            # pode entregar. Melhor dizer agora.
            partes.append(
                "_Ainda não há uma capacidade publicada que faça exatamente isso. "
                "Diga ao corretor que você pode fazer o trabalho agora, e que a "
                "versão automática entra na fila de novidades._")
            try:
                f.registrar_lacuna(
                    gap_type="missing_skill", descricao=pedido,
                    company_id=self.company_id, request_id=r.get("request_id"))
            except Exception:  # noqa: BLE001
                pass

        if r.get("confianca", 0) < 0.5:
            partes.append(
                "_A intenção não ficou clara. Pergunte ao corretor com que "
                "frequência isso deveria acontecer antes de propor qualquer coisa._")

        partes.append(f"\n{r.get('mensagem_humana', '')}")
        partes.append(
            "\n[Apresente a proposta ao corretor com suas palavras e ESPERE a "
            "confirmação dele. Não instale, não crie rotina e não prometa que já "
            "está funcionando.]")
        return "\n".join(p for p in partes if p)


def ferramenta_de_automacao(*, company_id: Optional[str], supabase: Any,
                            user_id: Optional[str] = None) -> list[BaseTool]:
    if not company_id or supabase is None:
        return []
    return [AvaliarAutomacaoTool(company_id=company_id, supabase=supabase, user_id=user_id)]
