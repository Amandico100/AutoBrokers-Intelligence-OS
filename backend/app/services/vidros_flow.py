# -*- coding: utf-8 -*-
"""Plano de trabalho de vidros — antes de abrir o navegador. SPEC-074 Blocos B e C.

O maior ganho de qualidade não é IA melhor dentro do browser. É **não abrir o
browser até o atendimento estar pronto** — e saber, antes, se ele cabe num
pedido só.

Duas perguntas que este módulo responde, e nenhuma delas precisa de rede:

    1. quantos PEDIDOS este relato gera?      (`separar_itens`)
    2. este trabalho é do portal mesmo?       (`resolver_canal`)

🔴 Por que o multi-item existe
==============================
📊 O portal diz, em texto que aparece em TODAS as telas:

    "O Atendimento Web permite apenas a SELEÇÃO DE 1 (UM) ITEM PARA
     TROCA/REPARO POR ATENDIMENTO."

e, no passo 1:

    "Se o item escolhido possuir lateralidade (por exemplo, lado esquerdo e
     lado direito), será necessário abrir uma nova solicitação para o outro
     lado."

Quem disser *"quebraram os dois vidros do lado esquerdo"* precisa de DOIS
pedidos. Mandar tudo numa string faria o robô abrir um, capturar um protocolo, e
o segurado descobrir que faltou metade quando o vidraceiro fosse embora.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Canais possíveis para um trabalho. A escolha é do sistema, não do prompt.
CANAL_PORTAL_PUBLICO = "portal_publico"
CANAL_WHATSAPP = "whatsapp_corredor"
CANAL_HUMANO = "human_handoff"

# 📊 Famílias que o portal de vidros atende, medidas no catálogo real
# (`GET /apolices/itens-cobertos`): vidro, para-brisa, vigia, retrovisor,
# farol, lanterna, teto, máquina de vidro. Película entra quando vinculada.
_FAMILIA_DO_PORTAL = (
    "vidro", "parabrisa", "para-brisa", "para brisa", "vigia", "retrovisor",
    "farol", "farolete", "lanterna", "teto solar", "teto panoramico",
    "maquina de vidro", "pelicula", "lente", "pisca", "capa de retrovisor",
)

# 🔴 O que NUNCA vai para o portal de vidros, por mais que a palavra apareça.
# Sinistro de colisão não é troca de peça — mandar para lá cria um atendimento
# de vidraçaria para um carro que precisa de guincho.
_FORA_DO_PORTAL = (
    "colisao", "batida", "capotou", "capotagem", "roubo do veiculo",
    "furto do veiculo", "incendio", "enchente total", "perda total",
    "guincho", "pane seca", "pane eletrica", "bateria", "chaveiro",
    "pneu furado", "socorro",
)

_LADOS = {
    "motorista": ("motorista", "esquerdo", "esquerda"),
    "carona": ("carona", "passageiro", "direito", "direita"),
}
_POSICOES = {
    "dianteira": ("dianteir", "frente", "frontal"),
    "traseira": ("traseir", "tras", "atras", "fundo"),
}


def _norm(txt: Any) -> str:
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass(frozen=True)
class ItemDeTrabalho:
    """UM item físico = UM atendimento no portal."""

    peca: str
    lado: str = ""
    posicao: str = ""
    relato: str = ""

    @property
    def descricao_curta(self) -> str:
        partes = [self.peca]
        if self.posicao:
            partes.append(self.posicao)
        if self.lado:
            partes.append(f"lado {self.lado}")
        return " ".join(p for p in partes if p)


def separar_itens(peca: Any, relato: Any = "",
                  especificos: Optional[Dict[str, Any]] = None) -> List[ItemDeTrabalho]:
    """Quantos pedidos este relato gera?

    Devolve 1 item no caso comum. Devolve N quando o relato nomeia mais de um
    lado ou mais de uma posição para a mesma peça — e aí cada um é um pedido.

    🔴 Deliberadamente CONSERVADOR: só separa quando o texto nomeia os dois
    lados de forma explícita. "Quebraram os vidros" (plural vago) devolve UM
    item e deixa a pergunta para o atendente. Abrir dois pedidos por
    interpretação de plural seria pior que perguntar.
    """
    especificos = especificos or {}
    texto = f"{_norm(peca)} {_norm(relato)}"
    base = str(peca or "").strip()
    if not base:
        return []

    lados = [nome for nome, marcas in _LADOS.items()
             if any(m in texto for m in marcas)]
    posicoes = [nome for nome, marcas in _POSICOES.items()
                if any(m in texto for m in marcas)]

    # O que o segurado já respondeu no 80% manda mais que o relato solto.
    lado_resp = _norm(especificos.get("lado_motorista_ou_carona"))
    if lado_resp:
        for nome, marcas in _LADOS.items():
            if any(m in lado_resp for m in marcas):
                lados = [nome]
                break
    pos_resp = _norm(especificos.get("porta_dianteira_ou_traseira"))
    if pos_resp:
        for nome, marcas in _POSICOES.items():
            if any(m in pos_resp for m in marcas):
                posicoes = [nome]
                break

    if len(lados) >= 2:
        return [ItemDeTrabalho(peca=base, lado=l,
                               posicao=posicoes[0] if len(posicoes) == 1 else "",
                               relato=str(relato or "")) for l in sorted(lados)]
    if len(posicoes) >= 2:
        return [ItemDeTrabalho(peca=base, posicao=p,
                               lado=lados[0] if len(lados) == 1 else "",
                               relato=str(relato or "")) for p in sorted(posicoes)]

    return [ItemDeTrabalho(peca=base,
                           lado=lados[0] if lados else "",
                           posicao=posicoes[0] if posicoes else "",
                           relato=str(relato or ""))]


def resolver_canal(*, peca: Any, relato: Any = "", seguradora: Any = "",
                   tem_apolice: bool = True) -> Dict[str, Any]:
    """Portal, WhatsApp ou humano — decidido por regra, não por prompt.

    A SPEC-074 B2 é explícita sobre o porquê: hoje essa decisão está espalhada
    entre prompt, `insurer_dispatch_tool`, `portal_tool` e playbook. Quatro
    cópias de uma regra acabam discordando, e o dia em que discordam manda um
    guincho para a vidraçaria.
    """
    texto = f"{_norm(peca)} {_norm(relato)}"

    if not str(peca or "").strip():
        return {"canal": CANAL_HUMANO, "motivo": "peca nao informada",
                "pode_portal": False}

    # 🔴 A exclusão vem ANTES da inclusão. "Quebrei o vidro na colisão" tem as
    # duas palavras — e o que manda é a colisão, que é sinistro, não vidraçaria.
    for fora in _FORA_DO_PORTAL:
        if fora in texto:
            return {"canal": CANAL_WHATSAPP,
                    "motivo": f"'{fora}' nao e trabalho do portal de vidros",
                    "pode_portal": False}

    if not tem_apolice:
        return {"canal": CANAL_HUMANO, "motivo": "sem apolice localizada",
                "pode_portal": False}

    for fam in _FAMILIA_DO_PORTAL:
        if fam in texto:
            return {"canal": CANAL_PORTAL_PUBLICO,
                    "motivo": f"familia '{fam}' e atendida pelo portal",
                    "pode_portal": True}

    return {"canal": CANAL_HUMANO,
            "motivo": "peca fora das familias medidas do portal",
            "pode_portal": False}


@dataclass
class PlanoDeVidros:
    """O que o agente precisa saber ANTES de abrir o navegador."""

    canal: str = CANAL_HUMANO
    motivo: str = ""
    pode_portal: bool = False
    itens: List[ItemDeTrabalho] = field(default_factory=list)
    perguntas_ao_segurado: List[str] = field(default_factory=list)
    lacunas_do_provedor: List[str] = field(default_factory=list)
    pronto: bool = False

    @property
    def multi_item(self) -> bool:
        return len(self.itens) > 1

    def para_evidencia(self) -> Dict[str, Any]:
        return {
            "canal": self.canal,
            "pode_portal": self.pode_portal,
            "itens": [i.descricao_curta for i in self.itens],
            "multi_item": self.multi_item,
            "faltam_do_segurado": len(self.perguntas_ao_segurado),
            "faltam_do_provedor": len(self.lacunas_do_provedor),
            "pronto": self.pronto,
            "motivo": self.motivo[:200],
        }


def montar_plano(*, peca: Any, relato: Any = "", seguradora: Any = "",
                 tem_apolice: bool = True,
                 especificos: Optional[Dict[str, Any]] = None,
                 ja_sei: Optional[Dict[str, Any]] = None) -> PlanoDeVidros:
    """O plano completo, sem tocar em rede.

    Reusa `o_que_falta` do catálogo de perguntas que já existe — não cria um
    segundo lugar que decide o que perguntar.
    """
    rota = resolver_canal(peca=peca, relato=relato, seguradora=seguradora,
                          tem_apolice=tem_apolice)
    plano = PlanoDeVidros(canal=rota["canal"], motivo=rota["motivo"],
                          pode_portal=rota["pode_portal"])
    if not rota["pode_portal"]:
        return plano

    plano.itens = separar_itens(peca, relato, especificos)

    try:
        from app.services.perguntas_do_portal_de_vidros import (
            DO_PROVEDOR, o_que_falta,
        )

        faltam = o_que_falta(str(peca or ""), ja_sei or {})
        plano.perguntas_ao_segurado = [p.texto for p in faltam
                                       if p.de_quem != DO_PROVEDOR]
        plano.lacunas_do_provedor = [p.campo for p in faltam
                                     if p.de_quem == DO_PROVEDOR]
    except Exception:  # noqa: BLE001
        # O catálogo é opcional para o plano: sem ele o robô ainda sabe o canal
        # e o número de itens. Falhar aqui não pode impedir o roteamento.
        plano.perguntas_ao_segurado = []

    plano.pronto = bool(plano.itens) and not plano.perguntas_ao_segurado
    return plano
