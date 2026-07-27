"""SPEC-062 §12.2 e §12.3 — o juiz LLM e a fila humana.

Quando um juiz LLM é legítimo
-----------------------------
Só quando nenhuma regra alcança a pergunta. Tom, clareza, se a resposta de fato
respondeu o que foi perguntado — isso não cabe em expressão regular.

Tudo o que couber em regra continua sendo regra (§12.1). Um juiz LLM custa
dinheiro, demora, e **tem opinião**: a mesma saída passa hoje e falha amanhã
sem nada ter mudado.

As três decisões que tornam este juiz utilizável
------------------------------------------------
**1. Ele julga por RUBRICA fechada, não por "está bom?".**
Perguntar "esta resposta está boa?" devolve prosa simpática e uma nota alta.
Perguntar "a resposta contém alguma informação que não estava na entrada?
Responda sim ou não e cite o trecho" devolve uma checagem.

**2. Ele nunca decide sozinho o que é crítico.**
Vazamento, cross-tenant e silêncio do Observador são decididos por regra. Um
modelo que erra 1% das vezes num domínio crítico é 1% de vazamento aprovado.

**3. Empate e dúvida caem para humano, não para "passou".**
Quando o juiz não tem confiança suficiente, o caso vira `human_review_tasks`.
Um juiz que resolve a própria dúvida com otimismo é pior que juiz nenhum,
porque produz um verde em que alguém vai confiar.

Por que ele NÃO roda no gate por padrão
---------------------------------------
Gate precisa ser reprodutível: rodar duas vezes no mesmo commit tem de dar o
mesmo resultado. Juiz LLM não garante isso. Ele roda **fora** do gate — em
avaliação offline e na amostragem online (§17) — e o que ele produz vira
tarefa de revisão, não bloqueio automático de release.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Confiança abaixo disto não vira veredito: vira fila humana.
LIMIAR_DE_CONFIANCA = 0.75

RUBRICAS: dict[str, str] = {
    "responde_a_pergunta": (
        "A resposta endereça o que foi perguntado? Ignore estilo, extensão e "
        "simpatia. Uma resposta educada que muda de assunto NÃO responde."),
    "sem_invencao": (
        "A resposta afirma algum fato que NÃO está na entrada nem nas fontes "
        "citadas? Cite o trecho exato inventado, se houver."),
    "linguagem_do_corretor": (
        "Um corretor de seguros brasileiro entenderia sem precisar perguntar "
        "o que significa alguma palavra? Jargão técnico de software (endpoint, "
        "payload, tenant, deploy) conta como NÃO."),
    "admite_o_que_nao_sabe": (
        "Quando falta dado, a resposta DIZ que falta — em vez de contornar com "
        "generalidade? Se não faltava dado, responda 'nao_se_aplica'."),
}


def juiz_disponivel() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


def _modelo() -> str:
    # Um modelo barato basta para julgar rubrica fechada, e o custo importa:
    # o juiz roda sobre amostra contínua de tráfego real.
    return os.getenv("EVAL_JUDGE_MODEL", "claude-sonnet-5")


def _prompt(entrada: Any, saida: Any, rubricas: list[str]) -> str:
    itens = "\n".join(f"- {r}: {RUBRICAS[r]}" for r in rubricas if r in RUBRICAS)
    return f"""Você avalia a resposta de um assistente para uma corretora de seguros.

Julgue APENAS os itens abaixo. Não opine sobre nada além deles.

{itens}

PERGUNTA/ENTRADA:
{json.dumps(entrada, ensure_ascii=False)[:4000]}

RESPOSTA A AVALIAR:
{str(saida)[:4000]}

Responda SOMENTE com JSON válido, sem cercas de código:
{{"vereditos": [{{"rubrica": "...", "passou": true, "confianca": 0.0, "motivo": "..."}}]}}

Regras da sua resposta:
- `confianca` é o quanto VOCÊ tem certeza do seu próprio veredito (0 a 1).
- Na dúvida, use confiança BAIXA. Não invente certeza: dúvida sua vira revisão
  humana, e isso é o comportamento correto.
- `motivo` em português, uma frase, dizendo o que o corretor perderia."""


async def julgar_com_llm(entrada: Any, saida: Any, *,
                         rubricas: Optional[list[str]] = None) -> list[dict]:
    """Devolve um veredito por rubrica. Nunca levanta exceção.

    Falha de rede, chave ausente ou JSON malformado **não** viram aprovação:
    viram `passou=False` com motivo explícito e confiança zero — que a política
    manda encaminhar para revisão humana.
    """
    escolhidas = [r for r in (rubricas or list(RUBRICAS)) if r in RUBRICAS]
    if not escolhidas:
        return []

    if not juiz_disponivel():
        return [_sem_veredito(r, "não há chave de LLM configurada nesta instalação")
                for r in escolhidas]

    try:
        from app.factories.llm_factory import LLMFactory
        from langchain_core.messages import HumanMessage

        llm = LLMFactory.create_llm(provider="anthropic", model=_modelo(),
                                    temperature=0)
        resposta = await llm.ainvoke([HumanMessage(content=_prompt(entrada, saida, escolhidas))])
        texto = getattr(resposta, "content", "") or ""
        if isinstance(texto, list):  # alguns provedores devolvem blocos
            texto = "".join(str(b.get("text", "")) if isinstance(b, dict) else str(b)
                            for b in texto)
        dados = json.loads(_extrair_json(texto))
        vereditos = dados.get("vereditos") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[JuizLLM] sem veredito (%s)", type(exc).__name__)
        return [_sem_veredito(r, f"o juiz falhou ({type(exc).__name__})")
                for r in escolhidas]

    saida_final: list[dict] = []
    vistos = {str(v.get("rubrica")): v for v in vereditos if isinstance(v, dict)}
    for r in escolhidas:
        v = vistos.get(r)
        if not v:
            saida_final.append(_sem_veredito(r, "o juiz não respondeu esta rubrica"))
            continue
        confianca = float(v.get("confianca") or 0)
        passou = bool(v.get("passou"))
        precisa_humano = confianca < LIMIAR_DE_CONFIANCA
        saida_final.append({
            "evaluator_slug": f"llm:{r}",
            # Confiança baixa NÃO vira aprovação. Vira "não passou ainda" +
            # fila humana. É a diferença entre um gate honesto e um otimista.
            "passou": passou and not precisa_humano,
            "nota": 1.0 if (passou and not precisa_humano) else 0.0,
            "confianca": round(confianca, 3),
            "precisa_revisao_humana": precisa_humano,
            "motivo": str(v.get("motivo") or "")[:400] or "sem motivo declarado",
        })
    return saida_final


def _sem_veredito(rubrica: str, porque: str) -> dict:
    return {
        "evaluator_slug": f"llm:{rubrica}",
        "passou": False, "nota": 0.0, "confianca": 0.0,
        "precisa_revisao_humana": True,
        "motivo": f"Sem veredito: {porque}. Ausência de veredito não é aprovação.",
    }


def _extrair_json(texto: str) -> str:
    """Recorta o primeiro objeto JSON do texto.

    Modelos insistem em embrulhar JSON em ```json apesar do pedido. Falhar por
    causa de cerca de código seria transformar teimosia de formatação em
    reprovação de qualidade.
    """
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```")[1] if "```" in t[3:] else t[3:]
        t = t[4:].strip() if t.lower().startswith("json") else t.strip()
    i, j = t.find("{"), t.rfind("}")
    return t[i: j + 1] if i != -1 and j > i else t


# ---------------------------------------------------------------------------
# §12.3 — a fila humana
# ---------------------------------------------------------------------------
def enfileirar_revisao(supabase_client: Any, *, run_id: Optional[str],
                       case_id: Optional[str], motivo: str,
                       amostra: Optional[dict] = None) -> Optional[str]:
    """Registra o que o juiz não conseguiu decidir.

    A tabela existe (`human_review_tasks`) desde a migration 20260727_07. Sem
    esta fila, "confiança baixa" viraria silêncio — e silêncio é indistinguível
    de aprovação para quem lê o painel.
    """
    db = getattr(supabase_client, "client", supabase_client)
    if not db:
        return None
    try:
        r = db.table("human_review_tasks").insert({
            "run_id": run_id, "case_id": case_id,
            "motivo": motivo[:500],
            # A amostra é limpa: revisão humana não é desculpa para copiar
            # conversa de segurado para outra tabela.
            "amostra": {k: str(v)[:200] for k, v in list((amostra or {}).items())[:8]},
            "status": "pendente",
        }).execute()
        return (r.data or [{}])[0].get("id")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RevisaoHumana] não enfileirado: %s", type(exc).__name__)
        return None
