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

SPEC-130-A.1 (D-130A1-01): `mensagem_do_canal(modelo, link)` → ≤ 3 balões do comparador ao consumidor (o vencedor,
o volume REAL de cotações, o tempo, a economia com a origem da conta, 2 cartões, o melhor preço por seguradora, quem
é a corretora e UMA pergunta no fim). `mensagem_para` escolhe pela ORIGEM: canal → a do canal; senão → a da carteira
(esta, `mensagem_whatsapp`, não muda e não fala do canal — G3).

PURA: só lê o modelo (o CONTRATO §5) e devolve texto. Quem ENVIA é a 133-A.
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Dict, List, Mapping, Optional

from app.services.multicalculo.config import PADRAO_DO_PRODUTO, normalizar

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


def _cobre_menos(o: Mapping[str, Any], *, curto: bool = False) -> Optional[str]:
    """J-P1 (juiz, 06/10) · D-MC-67: a opção mais barata porque CORTA cobertura diz o que corta, em UMA linha — nunca
    só "R$ X a menos". Vem do `por_que_mais_barata` do modelo ("Mesma Youse da recomendada, com franquia … e …")."""
    texto = re.sub(r"\s+", " ", str(o.get("por_que_mais_barata") or "")).strip().rstrip(".")
    if not texto:
        return None
    m = re.search(r",\s*com\s+(.+)$", texto)
    corpo = m.group(1) if m else texto
    if curto:
        partes = re.split(r",\s*|\s+e\s+(?=[^,]+$)", corpo)
        corpo = partes[0] + (" e outras diferenças" if len(partes) > 1 else "")
    return f"_Cobre menos: {corpo}._"


def _porque(o: Mapping[str, Any], *, com_motivo: bool = True, curto: bool = False) -> Optional[str]:
    """A linha de "por quê": o que a opção cobre a menos (nunca cai), senão o 1º motivo (cai primeiro no aperto)."""
    corte = _cobre_menos(o, curto=curto)
    if corte:
        return corte
    if not com_motivo:
        return None
    texto = next(iter(o.get("motivos") or []), None)
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


def _mesmo_preco_da_1a(modelo: Mapping[str, Any], preco: Any) -> bool:
    """O duelo entre corretoras só se afirma se o preço da vencedora É o da 1ª opção (crítico final, 06/10)."""
    ops = [o for o in (modelo.get("opcoes") or []) if isinstance(o, Mapping)]
    try:
        return bool(ops) and abs(float(preco) - float(ops[0].get("premio_anual"))) < 0.01
    except (TypeError, ValueError):
        return False


def _linha_da_anfitria(modelo: Mapping[str, Any]) -> Optional[str]:
    """UMA linha, só com dado verdadeiro do modelo, nesta ordem de força: a vitória entre corretoras (canal), a nota
    do Google CONFIRMADA, os anos de casa. Nada disso → só quem atende."""
    anf = modelo.get("anfitria") or {}
    nome = str(anf.get("nome") or "").strip()
    if not nome:
        return None
    entre = [e for e in (modelo.get("entre_corretoras") or []) if isinstance(e, Mapping)]
    venc = next((e for e in entre if e.get("vencedora") and e.get("corretora") == nome), None)
    if len(entre) > 1 and venc is not None and _mesmo_preco_da_1a(modelo, venc.get("melhor_completa")):
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

    # o aperto tira, nesta ordem: o motivo, o convite, as parcelas — e só no fim encurta o "cobre menos" (nunca o tira)
    tentativas = [(True, True, True, False), (False, True, True, False), (False, False, True, False),
                  (False, False, False, False), (False, False, False, True)]
    balao1 = ""
    for com_porque, com_convite, com_parcelas, curto in tentativas:
        blocos = [_abertura(modelo)]
        for o in ops:
            linha = _linha_da_opcao(o, com_parcelas=com_parcelas)
            pq = _porque(o, com_motivo=com_porque, curto=curto)
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


# =====================================================================================================================
# SPEC-130-A.1 — A MENSAGEM DO CANAL (o comparador ao consumidor; D-130A1-01/02/03/04/06)
# =====================================================================================================================
#: cada balão do canal cabe numa tela de celular sem "ler mais" (💭 ~650, o pedido do gerente)
TETO_POR_BALAO_DO_CANAL = 650
EMOJI_DO_VENCEDOR = "🏆"
EMOJI_DO_SELO = "✅"
#: o canal não fala de desconto em "%" nem de "desconto" (o Founder: nunca "%" de desconto) — além das da carteira
FRASES_PROIBIDAS_NO_CANAL = FRASES_PROIBIDAS + ("%", "desconto")
_RE_DIAS = re.compile(r"(\d+)\s*(?:dias|di[áa]rias)", re.I)
#: a conta do relógio, sem número solto (o G8 varre este arquivo)
_MINUTO = int(timedelta(minutes=1).total_seconds())


def _n(v: Any) -> Optional[int]:
    """Um inteiro POSITIVO do modelo, ou None (a linha some — G4)."""
    if isinstance(v, bool):
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _tempo(segundos: Any) -> Optional[str]:
    s = _n(segundos)
    if s is None:
        return None
    if s < _MINUTO:
        return f"{s} segundo{'s' if s != 1 else ''}"
    m, r = divmod(s, _MINUTO)
    if m < _MINUTO:
        return f"{m} min {r} s" if r else f"{m} min"
    h, m = divmod(m, _MINUTO)
    return f"{h} h {m} min" if m else f"{h} h"


def _de_quem(nome: str) -> str:
    """ "Corretora X" — sem repetir quando o nome já diz que é corretora."""
    return nome if "corretora" in normalizar(nome) else f"Corretora {nome}"


def _preco_do_vencedor(o: Mapping[str, Any]) -> List[str]:
    """O parcelado em DESTAQUE, com os juros com NOME e o total; "sem juros" só quando é verdade."""
    premio = _brl(o["premio_anual"])
    p, sj = o.get("parcelas"), o.get("parcelas_sem_juros")
    p = p if isinstance(p, Mapping) and _n(p.get("vezes")) and p.get("valor") else None
    sj = sj if isinstance(sj, Mapping) and _n(sj.get("vezes")) and sj.get("valor") else None
    if p and int(p["vezes"]) > 1:
        vezes, valor = int(p["vezes"]), float(p["valor"])
        if sj and int(sj["vezes"]) == vezes:
            return [f"*{vezes}x de {_brl(valor)}* sem juros", f"Total: *{premio}* por ano"]
        linhas = [f"*{vezes}x de {_brl(valor)}* com juros, total {_brl_inteiro(vezes * valor)}"]
        linhas.append(f"ou *{premio}* por ano" + (f" · até {int(sj['vezes'])}x sem juros" if sj else ""))
        return linhas
    return [f"*{premio}* por ano" + (f" · até {int(sj['vezes'])}x sem juros" if sj else "")]


def _abertura_do_canal(modelo: Mapping[str, Any]) -> List[str]:
    from app.services.multicalculo.comparacao import RAMO_AUTO

    canal = str((modelo.get("canal") or {}).get("nome") or "").strip()
    seguro = "seguro auto" if _n(modelo.get("ramo")) == RAMO_AUTO else "seguro"
    titulo = (f"*{canal} no seu {seguro} foi encontrado* {EMOJI_DO_VENCEDOR}" if canal
              else f"*Encontramos quem cobra menos no seu {seguro}* {EMOJI_DO_VENCEDOR}")
    r = modelo.get("resumo") or {}
    n = _n(r.get("cotacoes_realizadas"))
    segs, corrs = _n(r.get("seguradoras_com_preco")), _n(r.get("corretoras_comparadas"))
    linhas = [titulo]
    if n:                 # 🔴 D-130A1-02: o número REAL de preços que voltaram — lido do resumo, nunca recalculado aqui
        if segs and corrs and corrs > 1:
            linhas.append(f"Vencedor em *{n} comparações* entre {corrs} corretoras e {segs} seguradoras.")
        elif segs:
            linhas.append(f"Vencedor em *{n} comparações* de {segs} seguradoras.")
        else:
            linhas.append(f"Vencedor em *{n} comparações*.")
    return linhas


def _numeros_do_canal(modelo: Mapping[str, Any]) -> List[str]:
    r = modelo.get("resumo") or {}
    linhas = []
    n = _n(r.get("cotacoes_realizadas"))
    if n:
        linhas.append(f"Cotações realizadas: *{n}*")
    t = _tempo(r.get("tempo_do_calculo_s"))
    if t:
        linhas.append(f"Tempo: *{t}*")
    eco = r.get("economia") if isinstance(r.get("economia"), Mapping) else {}
    if eco.get("ate") and eco.get("de") and float(eco["ate"]) >= 0.5:
        if eco.get("mesma_cobertura"):
            origem = (f"da cotação completa mais cara, {_brl_inteiro(eco['de'])}, para a mais barata com a mesma "
                      "cobertura")
        else:
            rot = next((str(o.get("rotulo") or "") for o in modelo.get("opcoes") or []
                        if isinstance(o, Mapping) and o.get("id") == eco.get("para_opcao")), "") or "mais em conta"
            origem = (f"da cotação completa mais cara, {_brl_inteiro(eco['de'])}, para a opção "
                      f"{rot.lower()}, que cobre menos")
        linhas.append(f"Você economiza até *{_brl_inteiro(eco['ate'])}* por ano _({origem})_")
    va = eco.get("vs_atual") if isinstance(eco.get("vs_atual"), Mapping) else None
    if va and va.get("valor") and float(va["valor"]) >= 0.5:
        linhas.append(f"São *{_brl_inteiro(va['valor'])} a menos que o seu seguro atual* "
                      f"({_brl_inteiro(va['atual'])} por ano), com cobertura completa")
    return linhas


def _vencedor(modelo: Mapping[str, Any], rec: Mapping[str, Any]) -> List[str]:
    nome = str((modelo.get("anfitria") or {}).get("nome") or "").strip()
    quem = f"{_de_quem(nome)} com {rec.get('seguradora')}" if nome else str(rec.get("seguradora") or "")
    return ["*Quem cobra menos?*", quem] + _preco_do_vencedor(rec)


def _basicas(o: Mapping[str, Any]) -> Optional[str]:
    """Só as coberturas BÁSICAS, numa linha: batida/roubo, terceiros, carro reserva (o resto está no link)."""
    partes = []
    for c in o.get("coberturas") or []:
        if not isinstance(c, Mapping):
            continue
        valor = str(c.get("valor") or "").strip()
        if c.get("chave") == "casco":
            partes.append("Batida, roubo e incêndio")
        elif c.get("chave") == "terceiros" and valor:
            partes.append(f"terceiros {valor}")
        elif c.get("chave") == "reserva":
            m = _RE_DIAS.search(valor)
            if m:
                partes.append(f"carro reserva {int(m.group(1))} dias")
    return " · ".join(partes) if partes else None


def _cobre_menos_do_canal(o: Mapping[str, Any], *, curto: bool) -> Optional[str]:
    """O que a mais em conta deixa de cobrir: o `por_que_mais_barata`; senão o `o_que_muda` (sem as linhas de preço
    e de seguradora)."""
    linha = _cobre_menos(o, curto=curto)
    if linha:
        return linha
    itens = [str(t).strip().rstrip(".") for t in o.get("o_que_muda") or []
             if str(t).strip() and not str(t).startswith("R$") and not str(t).startswith("Seguradora ")]
    if not itens:
        return None
    itens = [i[:1].lower() + i[1:] for i in (itens[:1] if curto else itens)]
    corpo = itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]
    return f"_Cobre menos: {corpo}._"


def _cartao(o: Mapping[str, Any], *, com_basicas: bool, cobre_menos: bool, curto: bool) -> str:
    cab = f"*{o.get('rotulo') or 'Opção'}*" + (f" · nota {int(o['nota'])}" if _n(o.get("nota")) else "")
    linha = f"{o.get('seguradora')} · *{_brl(o['premio_anual'])} por ano*"
    f = o.get("franquia") or {}
    if isinstance(f, Mapping) and f.get("valor"):
        linha += f" · franquia {_brl_inteiro(f['valor'])}"
    extra = _cobre_menos_do_canal(o, curto=curto) if cobre_menos else (_basicas(o) if com_basicas else None)
    return "\n".join([cab, linha] + ([extra] if extra else []))


def _mais_em_conta(modelo: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """A opção MAIS BARATA que a 1ª (a econômica, ou a mínima no canal) — é a "Mais em conta" por definição."""
    ops = [o for o in (modelo.get("opcoes") or []) if isinstance(o, Mapping) and o.get("premio_anual")]
    baratas = [o for o in ops[1:] if float(o["premio_anual"]) < float(ops[0]["premio_anual"])] if ops else []
    return min(baratas, key=lambda o: float(o["premio_anual"])) if baratas else None


def _por_seguradora(modelo: Mapping[str, Any], quantas: int) -> List[str]:
    ranking = [r for r in (modelo.get("ranking") or []) if isinstance(r, Mapping) and r.get("premio_anual")]
    if not ranking or quantas < 1:
        return []
    return (["*Melhor preço por seguradora*"]
            + [f"{r.get('seguradora')} · {_brl_inteiro(r['premio_anual'])}" for r in ranking[:quantas]]
            + ["_Lista completa no link abaixo._"])


def _anos(modelo: Mapping[str, Any], desde: Any) -> Optional[str]:
    ano = _n(desde)
    m = re.match(r"^(\d{4})", str(modelo.get("gerado_em") or modelo.get("validade_ate") or ""))
    if not ano or not m:
        return None
    anos = int(m.group(1)) - ano
    return f"{anos} ano{'s' if anos != 1 else ''} de mercado" if anos >= 1 else None


def _quem_e(modelo: Mapping[str, Any]) -> List[str]:
    """A lista da corretora: só o que o modelo traz (linha sem dado some — G4). Reclame Aqui: só com fonte (hoje
    não há nenhuma, então a linha nunca aparece)."""
    anf = modelo.get("anfitria") or {}
    nome = str(anf.get("nome") or "").strip()
    if not nome:
        return []
    linhas = ["*Quem é a corretora que cobra menos?*", nome]
    selo = str(anf.get("selo") or "").strip()
    if selo:
        linhas.append(f"{EMOJI_DO_SELO} {selo}")
    g = anf.get("google")
    if isinstance(g, Mapping) and g.get("nota") and _n(g.get("avaliacoes")):
        nota = f"{float(g['nota']):.1f}".replace(".", ",")
        av = int(g["avaliacoes"])
        linhas.append(f"Google: {nota} ({av} {'avaliações' if av != 1 else 'avaliação'})")
    ra = anf.get("reclame_aqui")
    if isinstance(ra, Mapping) and ra.get("nota") and ra.get("fonte"):
        linhas.append(f"Reclame Aqui: {str(ra['nota']).replace('.', ',')}")
    susep = re.sub(r"^\s*susep\b[\s:nº°.#-]*", "", str(anf.get("susep") or ""), flags=re.I).strip()
    if susep:
        linhas.append(f"SUSEP: {susep}")
    anos = _anos(modelo, anf.get("desde"))
    if anos:
        linhas.append(anos)
    return linhas


def _atencao(modelo: Mapping[str, Any]) -> Optional[str]:
    selo = str((modelo.get("anfitria") or {}).get("selo") or "").strip()
    if not selo:
        return None
    m = re.match(r"^corretora\s+(.+)$", selo, re.I)
    return f"_Atenção: só aceite corretoras {m.group(1)}._" if m else f"_Atenção: só aceite quem tem o selo {selo}._"


def _motivo_do_link(modelo: Mapping[str, Any]) -> Optional[str]:
    """O motivo FORTE para abrir o link — só o que a página de fato tem."""
    n_op, n_rk = len(modelo.get("opcoes") or []), len(modelo.get("ranking") or [])
    # o ranking da página é o da ANFITRIÃ na completa — outro número que o "N seguradoras" do topo (todas as corretoras,
    # todas as opções); por isso a lista vai SEM número: dois números verdadeiros e diferentes confundem
    partes = ([f"as {n_op} opções lado a lado"] if n_op > 1 else []) + \
        (["o preço de cada seguradora"] if n_rk > 1 else []) + \
        (["como acionar o seguro"] if modelo.get("sinistro") else [])
    if not partes:
        return None
    corpo = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
    return f"_No link: {corpo}._"


def mensagem_do_canal(modelo: Mapping[str, Any], link: str, *, config: Optional[Mapping[str, Any]] = None
                      ) -> List[str]:
    """Os ≤ 3 balões do CANAL (D-130A1-01): ① o vencedor, o volume REAL, o tempo, a economia com a origem da conta ·
    ② os 2 cartões (a 1ª opção com as coberturas básicas; a mais em conta com o que deixa de cobrir) e o melhor preço
    por seguradora · ③ quem é a corretora, o selo, o link com a validade e UMA pergunta no fim (D-130A1-06).

    Só dado do modelo; linha sem dado some. Se um balão passar do teto, encolhe nesta ordem: as coberturas básicas,
    o "cobre menos" (curto, nunca some), a lista por seguradora (à metade), o motivo do link."""
    cfg = config or PADRAO_DO_PRODUTO
    ops = [o for o in (modelo.get("opcoes") or []) if isinstance(o, Mapping) and o.get("premio_anual")]
    if not ops:
        return mensagem_whatsapp(modelo, link, config=config)
    rec = ops[0]
    quantas = (_n((cfg.get("canal") or {}).get("lista_por_seguradora"))
               or int(PADRAO_DO_PRODUTO["canal"]["lista_por_seguradora"]))

    balao1 = "\n\n".join(b for b in ("\n".join(_abertura_do_canal(modelo)), "\n".join(_numeros_do_canal(modelo)),
                                     "\n".join(_vencedor(modelo, rec))) if b)

    barata = _mais_em_conta(modelo)
    balao2 = ""
    for com_basicas, curto, lista in ((True, False, quantas), (False, False, quantas), (False, True, quantas),
                                      (False, True, max(1, quantas // 2))):
        blocos = [_cartao(rec, com_basicas=com_basicas, cobre_menos=False, curto=curto)]
        if barata is not None:
            blocos.append(_cartao(barata, com_basicas=False, cobre_menos=True, curto=curto))
        por_seg = _por_seguradora(modelo, lista)
        if por_seg:
            blocos.append("\n".join(por_seg))
        balao2 = "\n\n".join(blocos)
        if len(balao2) <= TETO_POR_BALAO_DO_CANAL:
            break

    validade = _data(modelo.get("validade_ate"))
    nome = str((modelo.get("anfitria") or {}).get("nome") or "").strip()
    pergunta = f"Quer fechar esse preço com a {nome}?" if nome else "Quer fechar esse preço?"
    quem = "\n".join(_quem_e(modelo))
    balao3 = ""
    for com_motivo in (True, False):
        fim = [l for l in (_atencao(modelo), _motivo_do_link(modelo) if com_motivo else None) if l]
        fim.append(str(link or "").strip())
        if validade:
            fim.append(f"Os preços valem até {validade}.")
        fim.append(pergunta)
        balao3 = "\n\n".join(b for b in (quem, "\n".join(fim)) if b)
        if len(balao3) <= TETO_POR_BALAO_DO_CANAL:
            break
    return [b for b in (balao1, balao2, balao3) if b]


def conferir_do_canal(baloes: List[str]) -> Dict[str, Any]:
    """O que o guarda mede na mensagem do canal: balões, tamanho de cada um, emojis e as frases proibidas."""
    texto = "\n".join(baloes)
    baixo = texto.lower()
    return {"baloes": len(baloes), "caracteres_por_balao": [len(b) for b in baloes], "caracteres": len(texto),
            "emojis": len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", texto)),
            "proibidas": [f for f in FRASES_PROIBIDAS_NO_CANAL if f in baixo]}


def mensagem_para(modelo: Mapping[str, Any], link: str, *, config: Optional[Mapping[str, Any]] = None) -> List[str]:
    """D-130A1-01: a mensagem pela ORIGEM do pedido — o canal ganha a do comparador; a corretora, a da carteira (a da
    SPEC-130-A, que não fala do canal)."""
    if str(modelo.get("origem") or "") == "canal":
        return mensagem_do_canal(modelo, link, config=config)
    return mensagem_whatsapp(modelo, link, config=config)
