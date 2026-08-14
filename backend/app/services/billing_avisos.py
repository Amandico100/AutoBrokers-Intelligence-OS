# -*- coding: utf-8 -*-
"""As mensagens que a Cobrança manda para o grupo de suporte humano.

Para quem lê o grupo
====================
São três, e cada uma abre com um título e uma cor diferentes — para quem abre o
WhatsApp saber do que se trata antes de ler a primeira linha:

    🔴 COBRANÇA · PRECISA DE VOCÊ    alguém em atraso que o robô não resolve
    🟠 COBRANÇA · PORTAL COM PROBLEMA  o robô não conseguiu ler o portal
    🔵 COBRANÇA · RESUMO               o que aconteceu na execução

Por que o formato é este
------------------------
O anterior era uma linha só, separada por barras::

    - CONDOMINIO EXEMPLO | apolice 01.008.119.003755 | parcela 02/06 | vcto 09/08/26

Cabe num terminal. Não cabe na tela de um celular, onde a atendente vai ler —
ela quebra em três linhas no meio de um número de apólice, e o WhatsApp para
contato **nem estava lá**. A pessoa teria de abrir o sistema de gestão para
descobrir para quem ligar, que é justamente o trabalho que o aviso existe para
poupar.

Agora cada informação tem sua linha, sempre na mesma ordem, **em toda
seguradora** — e o telefone vem em negrito, logo abaixo do nome, porque é a
primeira coisa que ela vai tocar.

O que NÃO entra aqui
--------------------
Mensagem para o segurado. Estes textos vão para o grupo INTERNO da corretora, e
por isso podem trazer telefone e apólice completos — são dados que a corretora
já tem. A regra de mascarar vale para log, artifact e RAG, não para o aviso que
a própria dona do dado recebe.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

TIPO_TAREFA = "tarefa"
TIPO_PROBLEMA = "problema"
TIPO_RESUMO = "resumo"

_CABECALHOS = {
    TIPO_TAREFA: "🔴 *COBRANÇA · PRECISA DE VOCÊ*",
    TIPO_PROBLEMA: "🟠 *COBRANÇA · PORTAL COM PROBLEMA*",
    TIPO_RESUMO: "🔵 *COBRANÇA · RESUMO*",
}

_SEPARADOR = "━━━━━━━━━━━━━━━━━"


def _digits(v: Any) -> str:
    return "".join(c for c in str(v or "") if c.isdigit())


def telefone_legivel(numero: Any) -> str:
    """5547999990001 -> (47) 99999-0001. O que a pessoa vê e disca.

    Devolve o que veio quando não reconhece o formato: um número estranho é
    melhor que um número escondido — a atendente decide o que fazer com ele.
    """
    d = _digits(numero)
    if len(d) >= 12 and d.startswith("55"):
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return str(numero or "sem telefone")


def _data_br(iso_ou_br: Any) -> str:
    texto = str(iso_ou_br or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", texto)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)[2:]}"
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", texto)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)[2:]}"
    return texto


def _dias_de_atraso(vencimento: Any, hoje: Optional[datetime] = None) -> Optional[int]:
    texto = str(vencimento or "").strip()
    hoje = hoje or datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    for formato, alvo in (("%Y-%m-%d", texto), ("%d/%m/%Y", texto), ("%d/%m/%y", texto)):
        try:
            venc = datetime.strptime(alvo, formato)
            return max(0, (hoje.date() - venc.date()).days)
        except (ValueError, TypeError):
            continue
    return None


def _quando(dias: Optional[int]) -> str:
    if dias is None:
        return ""
    if dias == 0:
        return " _(hoje)_"
    if dias == 1:
        return " _(há 1 dia)_"
    return f" _(há {dias} dias)_"


def _linha(rotulo: str, valor: Any) -> str:
    return f"{rotulo} {valor}" if str(valor or "").strip() else ""


def _bloco_do_segurado(n: int, item: Dict[str, Any]) -> str:
    """Um segurado, uma linha por informação, sempre na mesma ordem."""
    nome = str(item.get("cliente_nome") or "Segurado sem nome no portal").strip()
    dias = _dias_de_atraso(item.get("vencimento"))
    venc = _data_br(item.get("vencimento"))
    valor = item.get("valor")
    valor_txt = (f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                 if isinstance(valor, (int, float)) else str(valor or ""))
    ramo = str(item.get("item_segurado") or item.get("ramo") or item.get("modalidade") or "").strip()
    seguradora = str(item.get("nome_seguradora") or item.get("seguradora") or "").strip()
    apolice = str(item.get("apolice_susep") or item.get("documento") or item.get("apolice") or "").strip()
    parcela = str(item.get("parcela") or "").strip()

    linhas = [
        f"*{n} · {nome.upper()}*",
        _linha("📱", f"*{telefone_legivel(item.get('whatsapp'))}*") if item.get("whatsapp")
        else "📱 _sem telefone no cadastro_",
        _linha("🏢", " · ".join(x for x in (seguradora, ramo) if x)),
        _linha("🧾 Apólice", apolice),
        _linha("📆 Parcela", f"{parcela} · venceu {venc}{_quando(dias)}" if parcela
               else (f"venceu {venc}{_quando(dias)}" if venc else "")),
        _linha("💰", valor_txt),
        _linha("⚠️", item.get("motivo")),
        _linha("📌", f"_{item['observacao']}_" if item.get("observacao") else ""),
        _linha("➡️", f"*{item['acao']}*" if item.get("acao") else ""),
    ]
    return "\n".join(x for x in linhas if x)


def _rodape_origem(corretora: str, agora: Optional[datetime] = None) -> str:
    agora = agora or datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    return f"_{corretora} · {agora.strftime('%d/%m às %H:%M')}_"


def aviso_de_tarefas(corretora: str, itens: List[Dict[str, Any]],
                     agora: Optional[datetime] = None) -> str:
    """🔴 Segurados em atraso que o robô não resolve — a equipe assume."""
    if not itens:
        return ""
    quantos = len(itens)
    plural = "segurados" if quantos > 1 else "segurado"
    partes = [
        _CABECALHOS[TIPO_TAREFA],
        _rodape_origem(corretora, agora),
        "",
        f"*{quantos} {plural} em atraso, e a seguradora não emite boleto para {'eles' if quantos > 1 else 'ele'}.*",
        "A conversão precisa ser feita no portal, por uma pessoa.",
        "",
    ]
    for n, item in enumerate(itens, start=1):
        partes.append(_SEPARADOR)
        partes.append(_bloco_do_segurado(n, item))
        partes.append("")
    partes.append(_SEPARADOR)
    partes.append("_Nenhum destes recebeu mensagem. O contato é seu._")
    return "\n".join(partes).strip()


def aviso_de_portal(corretora: str, seguradora: str, o_que_houve: str,
                    agora: Optional[datetime] = None) -> str:
    """🟠 O robô não conseguiu ler o portal — e não afirma que está tudo em dia.

    Este é o aviso do "guarda". Decisão do founder (12/08/2026): ele vai para o
    GRUPO HUMANO, nunca para o segurado. O segurado não tem o que fazer com a
    informação de que um robô não conseguiu abrir uma tela.
    """
    return "\n".join([
        _CABECALHOS[TIPO_PROBLEMA],
        _rodape_origem(corretora, agora),
        "",
        f"*{seguradora} — {o_que_houve}*",
        "",
        "⚠️ *Não estou afirmando que a carteira está em dia.*",
        "",
        "➡️ *Conferir na mão, no portal, se há alguém em atraso*",
        "_Vou tentar de novo na próxima execução._",
    ])


def aviso_de_resumo(corretora: str, *, seguradoras: List[str], enviados: int,
                    pendentes: int, tarefas: int, sem_telefone: List[Dict[str, Any]],
                    agora: Optional[datetime] = None) -> str:
    """🔵 O que aconteceu na execução. Uma linha por desfecho."""
    partes = [
        _CABECALHOS[TIPO_RESUMO],
        _rodape_origem(corretora, agora),
        "",
        f"Seguradoras varridas: {', '.join(seguradoras) if seguradoras else 'nenhuma'}",
    ]
    if enviados:
        partes.append(f"✅ {enviados} boleto(s) enviado(s)")
    if pendentes:
        partes.append(f"⏳ {pendentes} ficam para amanhã _(limite de envios do dia)_")
    if tarefas:
        partes.append(f"🔴 {tarefas} precisam de você _(mensagem acima)_")
    for item in sem_telefone[:5]:
        nome = str(item.get("cliente_nome") or "Segurado").upper()
        apolice = str(item.get("apolice_susep") or item.get("documento") or "")
        partes.append(f"❌ sem telefone no cadastro: {nome} · apólice {apolice}")
    if not (enviados or pendentes or tarefas or sem_telefone):
        partes.append("Nenhum inadimplente nesta execução.")
    return "\n".join(partes)
