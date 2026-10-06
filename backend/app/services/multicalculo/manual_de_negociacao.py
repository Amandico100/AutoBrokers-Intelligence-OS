# -*- coding: utf-8 -*-
"""O MANUAL DE NEGOCIAÇÃO como DADO — SPEC-130-A U2 (consumido pela 133-A, pela página e pela 135).

Fonte: `docs/canon/programa-multicalculo/ESTRATEGIA-COMERCIAL-DAS-CORRETORAS.md` §1 (o que as comerciais fazem e o
que o cliente pergunta) e as decisões D-MC-66…72. Nada aqui é constante comercial: todo NÚMERO (comissão, alvo,
limite) vem de `config` (o `PADRAO_DO_PRODUTO` ⊕ a corretora) e entra no texto quando o manual é MONTADO
(`montar(config)`). O guarda G8 confere que nenhum número comercial está escrito neste arquivo.

Regras de texto (CLAUDE.md §13.9 e D-MC-59/71): resposta curta, honesta, sem promessa que a corretora não controla,
sem nome de corretora, sem "o mais barato do mercado", sem urgência falsa.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional

from app.services.multicalculo.config import PADRAO_DO_PRODUTO


def _pct(v: Any) -> str:
    f = float(v)
    return f"{int(f)} %" if f.is_integer() else f"{f:.1f} %".replace(".", ",")


# ---------------------------------------------------------------------------------------------------------------------
# As ALAVANCAS do "mais barato" (D-MC-67 a ordem · D-MC-68 os limites). A ORDEM vem da config.
# ---------------------------------------------------------------------------------------------------------------------
_ALAVANCAS: Dict[str, Dict[str, Any]] = {
    "desconto": {"nome": "desconto que a seguradora libera", "corta_cobertura": False,
                 "como": "o percentual de desconto da seguradora no Agger (`percDesconto`); nas seguradoras que "
                         "ignoram a comissão é o ÚNICO botão da margem"},
    "comissao": {"nome": "comissão da corretora", "corta_cobertura": False,
                 "como": "de {entrada} para {autonomo} sozinho; {piso} só com concorrência declarada E o corretor "
                         "aprovando; nunca abaixo de {piso}"},
    "franquia": {"nome": "franquia maior", "corta_cobertura": True,
                 "como": "franquia {franquia} — dito ao cliente em \"o que mudou\""},
    "carro_reserva": {"nome": "menos dias de carro reserva", "corta_cobertura": True,
                      "como": "carro reserva {carro_reserva} — dito ao cliente"},
    "vidros": {"nome": "vidros básicos", "corta_cobertura": True, "como": "vidros {vidros} — dito ao cliente"},
    "assistencia": {"nome": "assistência básica", "corta_cobertura": True,
                    "como": "assistência {assistencia} — dito ao cliente"},
}

# ---------------------------------------------------------------------------------------------------------------------
# As 9 OBJEÇÕES reais (ESTRATEGIA §1.5) — resposta curta e honesta; `acao` = o que o agente faz
# ---------------------------------------------------------------------------------------------------------------------
_OBJECOES: List[Dict[str, str]] = [
    {"chave": "melhorar_preco", "pergunta": "Dá para melhorar o preço?",
     "resposta": "Talvez. Posso pedir o desconto que a seguradora libera e rever a minha margem. Me diga quanto "
                 "você quer pagar que eu procuro o caminho.",
     "acao": "cotacao_alvo"},
    {"chave": "reduzir_franquia", "pergunta": "Tem como reduzir a franquia mantendo o valor?",
     "resposta": "Franquia menor costuma deixar o seguro um pouco mais caro. Posso recalcular com a franquia "
                 "reduzida e te mostrar a diferença exata.",
     "acao": "recalcular_franquia_reduzida"},
    {"chave": "outras_seguradoras", "pergunta": "Outras seguradoras não ficaram melhores?",
     "resposta": "Cotei em todas que aceitaram o seu perfil. A lista completa, do menor preço ao maior, está na "
                 "página — inclusive as que ofereceram um produto diferente, com o porquê.",
     "acao": "mostrar_ranking"},
    {"chave": "qual_tenho_hoje", "pergunta": "Qual opção eu tenho hoje?",
     "resposta": "A opção \"igual à sua atual\" repete as coberturas da sua apólice; as outras mostram o que muda.",
     "acao": "mostrar_igual_a_atual"},
    {"chave": "banco_cooperativa", "pergunta": "No banco ou na cooperativa é mais barato.",
     "resposta": "Pode ser — compare franquia, carro reserva e o valor para terceiros. Proteção de cooperativa não "
                 "é seguro regulado pela SUSEP e costuma cobrir menos.",
     "acao": "comparar_coberturas"},
    {"chave": "endosso_concessionaria", "pergunta": "Vou ver se o endosso da concessionária compensa.",
     "resposta": "Combinado. Quando tiver o valor, me mande que eu comparo as coberturas lado a lado para você.",
     "acao": "comparar_coberturas"},
    {"chave": "parcelar_mais", "pergunta": "Dá para parcelar mais?",
     "resposta": "Cada seguradora tem o seu limite de parcelas. As que aparecem são as maiores que ela aceita; "
                 "no cartão, algumas parcelam sem comprometer o limite inteiro.",
     "acao": "mostrar_parcelas"},
    {"chave": "sinistro_quem_ligo", "pergunta": "Se eu bater, ligo para quem? Para o 0800?",
     "resposta": "Para a sua corretora, pelo WhatsApp. Ela orienta o que fazer e abre o aviso na seguradora com você.",
     "acao": "mostrar_sinistro"},
    {"chave": "uso_aplicativo", "pergunta": "Uso o carro para aplicativo (Uber).",
     "resposta": "Obrigado por avisar — muda a cotação. Nem toda seguradora aceita carro de aplicativo e o preço é "
                 "diferente; eu calculo só nas que aceitam.",
     "acao": "recalcular_uso_aplicativo"},
]

# ---------------------------------------------------------------------------------------------------------------------
# As 3 ESTRATÉGIAS por situação (D-MC-66 · D-MC-69 · D-130A-09)
# ---------------------------------------------------------------------------------------------------------------------
_ESTRATEGIAS: Dict[str, Dict[str, Any]] = {
    "renovacao": {
        "quando": "~{antecedencia} dias antes do fim da vigência",
        "comissao": "≥ a do ano anterior; tenta +{mais_min}–{mais_max} pp",
        "mira": "o preço do ano anterior (ou um pouco menor, sem sinistro)",
        "opcoes": ["sua_renovacao", "mais_em_conta", "mais_completa"],
    },
    "novo_com_apolice": {
        "quando": "assim que a apólice atual é lida",
        "comissao": "{entrada} + o desconto que a seguradora libera",
        "mira": "as MESMAS coberturas noutra seguradora, ~{alvo_min}–{alvo_max} abaixo do preço atual quando der, "
                "guardando margem",
        "opcoes": ["igual_a_atual", "mais_em_conta", "mais_completa"],
    },
    "novo_sem_apolice": {
        "quando": "no pedido",
        "comissao": "{entrada}",
        "mira": "a menor completa + a econômica + a completa+ quando houver",
        "opcoes": ["recomendada", "mais_em_conta", "mais_completa_ou_outra_completa"],
    },
}

# os passos do sinistro que são VERDADE para qualquer corretora (a dela, se cadastrada, troca estes)
_SINISTRO: List[str] = [
    "Avise a sua corretora pelo WhatsApp assim que puder",
    "Ela orienta o que fazer e abre o aviso de sinistro na seguradora",
    "A seguradora analisa o caso e indica os próximos passos (vistoria, oficina ou documentos)",
    "A corretora acompanha com a seguradora até o fim",
]


# ---------------------------------------------------------------------------------------------------------------------
def montar(config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """O manual inteiro, com os números DA CORRETORA (config) já no texto. Devolve uma cópia."""
    cfg = config or PADRAO_DO_PRODUTO
    com = cfg["comissao"]
    cortes = cfg["cortes_de_cobertura"]
    ren = cfg["renovacao"]
    alvo = cfg["alvo_abaixo_da_atual_pct"]
    valores = {"entrada": _pct(com["entrada"]), "autonomo": _pct(com["autonomo_minimo"]), "piso": _pct(com["piso"]),
               "franquia": cortes.get("franquia"), "carro_reserva": cortes.get("carro_reserva"),
               "vidros": cortes.get("vidros"), "assistencia": cortes.get("assistencia"),
               "antecedencia": ren["antecedencia_dias"], "mais_min": _num(ren["comissao_a_mais_pp"]["minimo"]),
               "mais_max": _num(ren["comissao_a_mais_pp"]["maximo"]), "alvo_min": _num(alvo["minimo"]),
               "alvo_max": _pct(alvo["maximo"])}
    alavancas = []
    for i, chave in enumerate(cfg["ordem_do_mais_barato"], start=1):
        base = _ALAVANCAS.get(chave)
        if not base:
            continue
        alavancas.append({"ordem": i, "chave": chave, "nome": base["nome"],
                          "corta_cobertura": base["corta_cobertura"], "como": base["como"].format(**valores)})
    estrategias = {}
    for sit, e in _ESTRATEGIAS.items():
        estrategias[sit] = {k: (v.format(**valores) if isinstance(v, str) else list(v)) for k, v in e.items()}
    return {
        "alavancas": alavancas,
        "limites": {"comissao_entrada": float(com["entrada"]), "comissao_autonoma_minima": float(com["autonomo_minimo"]),
                    "comissao_piso": float(com["piso"]),
                    "regra": f"até {valores['autonomo']} o agente aplica sozinho; {valores['piso']} só com "
                             f"concorrência declarada e o corretor aprovando (D-MC-68); nunca abaixo de "
                             f"{valores['piso']}"},
        "objecoes": copy.deepcopy(_OBJECOES),
        "estrategias": estrategias,
        "faq": faq_padrao(cfg),
        "sinistro": sinistro_padrao(cfg),
    }


def _num(v: Any) -> str:
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:.1f}".replace(".", ",")


def faq_padrao(config: Optional[Mapping[str, Any]] = None) -> List[Dict[str, str]]:
    """As dúvidas da PÁGINA = as objeções reais (§1.5), pergunta e resposta curta. A corretora troca pela config
    (`faq`: lista de {pergunta, resposta})."""
    proprio = (config or {}).get("faq")
    if isinstance(proprio, list) and proprio and all(
            isinstance(i, Mapping) and i.get("pergunta") and i.get("resposta") for i in proprio):
        return [{"pergunta": str(i["pergunta"]), "resposta": str(i["resposta"])} for i in proprio]
    return [{"pergunta": o["pergunta"], "resposta": o["resposta"]} for o in _OBJECOES]


def sinistro_padrao(config: Optional[Mapping[str, Any]] = None) -> List[str]:
    """Os passos do sinistro que são verdade para QUALQUER corretora; a dela (config `sinistro`) substitui."""
    proprio = (config or {}).get("sinistro")
    if isinstance(proprio, list) and proprio and all(isinstance(i, str) and i.strip() for i in proprio):
        return [i.strip() for i in proprio]
    return list(_SINISTRO)


def objecao(chave: str) -> Optional[Dict[str, str]]:
    return next((dict(o) for o in _OBJECOES if o["chave"] == chave), None)
