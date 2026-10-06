# -*- coding: utf-8 -*-
"""A MENSAGEM do WhatsApp que leva a proposta — SPEC-130-A U6 (D-MC-74, D-MC-71, D-MC-55).

    mensagem_whatsapp(modelo, link) → [balão 1, balão 2]

balão 1  o resultado honesto ("Das N seguradoras que cotei, X deram preço com a mesma cobertura completa") + no
         MÁXIMO as opções que a config manda (padrão do produto: a recomendada e a mais em conta), cada uma com
         `*negrito*` no rótulo e no preço, os juros COM NOME ("com juros, total R$ …" ou "sem juros") e uma linha de
         "por quê" em `_itálico_`.
balão 2  o link + "Os preços valem até <data>" + UMA linha verdadeira da anfitriã (nota do Google confirmada, anos de
         casa ou a vitória entre as corretoras — só o que o modelo traz).

⛔ Nunca: "o mais barato do mercado", cronômetro/urgência falsa (D-MC-71), comissão (G3), o nome da corretora que
perdeu (D-MC-55 — o modelo nem o carrega). ≤ 700 caracteres no total; ≤ 2 emojis. Referência: o `whatsapp.html`
aprovado no D0 (`scratchpad/design/d3-carteira-v4/montar_whatsapp.py`).

PURA: só lê o modelo (o CONTRATO §5) e devolve texto. Quem ENVIA é a 133-A.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional

from app.services.multicalculo.config import PADRAO_DO_PRODUTO

TETO_DE_CARACTERES = 700
EMOJI_DO_RESULTADO = "✅"
#: o que a mensagem NUNCA diz (o guarda dos testes procura cada uma; D-MC-71/74, G3)
FRASES_PROIBIDAS = ("mais barato do mercado", "menor preço do mercado", "só hoje", "so hoje", "corra",
                    "últimas horas", "ultimas horas", "expira em", "acaba hoje", "antes que acabe", "comiss")


def _brl(v: Any) -> str:
    inteiro, _, cent = f"{float(v):,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{cent}"


def _brl_inteiro(v: Any) -> str:
    n = int(abs(float(v)) + 0.5)
    return "R$ " + f"{n:,}".replace(",", ".")


def _data(iso: Any) -> Optional[str]:
    m = re.match(r"^(?P<a>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})", str(iso or ""))
    return f"{m['d']}/{m['m']}/{m['a']}" if m else None


def _parcelas(o: Mapping[str, Any]) -> str:
    """Os juros com NOME: "sem juros" só quando o parcelamento bate com o prêmio; senão "com juros, total R$ …"."""
    sj = o.get("parcelas_sem_juros")
    if isinstance(sj, Mapping) and sj.get("vezes") and sj.get("valor"):
        return f" ou {int(sj['vezes'])}x de {_brl(sj['valor'])} sem juros"
    p = o.get("parcelas")
    if isinstance(p, Mapping) and p.get("vezes") and p.get("valor") and int(p["vezes"]) > 1:
        total = int(p["vezes"]) * float(p["valor"])
        return f" ou {int(p['vezes'])}x de {_brl(p['valor'])} com juros, total {_brl_inteiro(total)}"
    return ""


def _escolhidas(modelo: Mapping[str, Any], quantas: int) -> List[Mapping[str, Any]]:
    """A 1ª opção (a de referência da situação) + a "Mais em conta" se houver; senão a seguinte. D-MC-74."""
    ops = [o for o in (modelo.get("opcoes") or []) if isinstance(o, Mapping) and o.get("premio_anual")]
    if not ops or quantas < 1:
        return []
    saida = [ops[0]]
    resto = sorted(ops[1:], key=lambda o: not (o.get("id") in ("mais_em_conta", "economica")
                                               or str(o.get("rotulo") or "").strip().lower() == "mais em conta"))
    saida += resto[: max(0, quantas - 1)]
    return saida


def _porque(o: Mapping[str, Any]) -> Optional[str]:
    texto = next(iter(o.get("motivos") or []), None) or o.get("por_que_mais_barata")
    texto = re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(".")
    return f"_{texto}._" if texto else None


def _linha_da_opcao(o: Mapping[str, Any], *, com_parcelas: bool) -> str:
    linha = f"*{o.get('rotulo') or 'Opção'}:* {o.get('seguradora')}, *{_brl(o['premio_anual'])} por ano*"
    if com_parcelas:
        linha += _parcelas(o)
    f = o.get("franquia") or {}
    if f.get("valor"):
        tipo = str(f.get("tipo") or "").strip().lower()
        linha += f". Franquia {tipo + ' ' if tipo else ''}de {_brl(f['valor'])}"
    return linha + "."


def _abertura(modelo: Mapping[str, Any]) -> str:
    nome = ((modelo.get("cliente") or {}).get("primeiro_nome") or "").strip()
    bem = modelo.get("bem") or {}
    apelido = (bem.get("apelido") or "").strip()
    r = modelo.get("resumo") or {}
    cotadas, iguais = int(r.get("seguradoras_cotadas") or 0), int(r.get("com_preco_comparavel") or 0)
    ola = f"Pronto, {nome}!" if nome else "Pronto!"
    para = f" para o seu {apelido}" if apelido else ""
    if cotadas == 1:
        conta = f"Cotei{para} em 1 seguradora"
    else:
        conta = f"Das {cotadas} seguradoras que cotei{para}"
    verbo = "deu" if iguais == 1 else "deram"
    return f"{ola} {conta}, {iguais} {verbo} preço com a mesma cobertura completa. {EMOJI_DO_RESULTADO}"


def _linha_da_anfitria(modelo: Mapping[str, Any]) -> Optional[str]:
    """UMA linha, só com dado verdadeiro do modelo, nesta ordem de força: a vitória entre corretoras (canal), a nota
    do Google CONFIRMADA, os anos de casa. Nada disso → só quem atende."""
    anf = modelo.get("anfitria") or {}
    nome = str(anf.get("nome") or "").strip()
    if not nome:
        return None
    entre = [e for e in (modelo.get("entre_corretoras") or []) if isinstance(e, Mapping)]
    if len(entre) > 1 and any(e.get("vencedora") and e.get("corretora") == nome for e in entre):
        return f"Quem atende é a {nome}, que teve o menor preço entre as {len(entre)} corretoras comparadas."
    g = anf.get("google")
    if isinstance(g, Mapping) and g.get("nota") and g.get("avaliacoes"):
        nota = f"{float(g['nota']):.1f}".replace(".", ",")
        return f"{nome}, nota {nota} no Google ({int(g['avaliacoes'])} avaliações)."
    if anf.get("desde"):
        return f"{nome}, atendendo desde {int(anf['desde'])}."
    return f"Quem vai cuidar do seu seguro: {nome}."


def mensagem_whatsapp(modelo: Mapping[str, Any], link: str, *, config: Optional[Mapping[str, Any]] = None
                      ) -> List[str]:
    """Os 2 balões (D-MC-74). Se passar do teto, encolhe nesta ordem: o "por quê", o convite, as parcelas."""
    cfg = config or PADRAO_DO_PRODUTO
    quantas = int(((cfg.get("opcoes") or {}).get("no_whatsapp")) or PADRAO_DO_PRODUTO["opcoes"]["no_whatsapp"])
    ops = _escolhidas(modelo, quantas)
    n_pagina = len(modelo.get("opcoes") or [])
    convite = (f"_No link abaixo dá para comparar as {n_pagina} opções lado a lado._" if n_pagina > 1
               else "_No link abaixo estão todos os detalhes._")

    validade = _data(modelo.get("validade_ate"))
    segundo = [str(link or "").strip()]
    if validade:
        segundo.append(f"Os preços valem até {validade}.")
    anf = _linha_da_anfitria(modelo)
    if anf:
        segundo.append(anf)
    balao2 = "\n".join(s for s in segundo if s)

    tentativas = [(True, True, True), (False, True, True), (False, False, True), (False, False, False)]
    balao1 = ""
    for com_porque, com_convite, com_parcelas in tentativas:
        blocos = [_abertura(modelo)]
        for o in ops:
            linha = _linha_da_opcao(o, com_parcelas=com_parcelas)
            pq = _porque(o) if com_porque else None
            blocos.append(linha + (f"\n{pq}" if pq else ""))
        if com_convite:
            blocos.append(convite)
        balao1 = "\n\n".join(blocos)
        if len(balao1) + len(balao2) <= TETO_DE_CARACTERES:
            break
    return [balao1, balao2]


def conferir(baloes: List[str]) -> Dict[str, Any]:
    """O que o guarda mede (e a 133-A pode conferir antes de enviar): tamanho, emojis e frases proibidas."""
    texto = "\n".join(baloes)
    emojis = len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", texto))
    baixo = texto.lower()
    return {"caracteres": len(texto), "emojis": emojis,
            "proibidas": [f for f in FRASES_PROIBIDAS if f in baixo]}
