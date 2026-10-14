"""A página de COTAÇÃO = a página de VENDA da corretora — SPEC-132-B · B2 (D-132B-01/02/08).

Três páginas para três momentos (D-131-40): a "carteira" da 130-A (o comando antigo, sem `servico`), a RENOVAÇÃO da 131-B
(quem JÁ é cliente) e esta — quem AINDA NÃO é cliente. É um TEMPLATE ÚNICO para todas as corretoras: a cara de cada uma
vem do modelo (a marca PUBLICADA, `css_do_tema`), nunca de uma constante deste arquivo (CLAUDE.md §13.9).

```
e_venda           o modelo é da página de venda? (situação de cliente novo, corretora, marcador `pagina="venda"`)
render_cotacao    modelo (CONTRATO §5 + `venda`) -> str (o documento inteiro)
previa_da_cotacao o que a prévia do link diz (as MESMAS chaves de `previa_do_modelo`), sem dado pessoal
```

A ordem (§4 da SPEC; cada bloco SEM DADO SOME — D-132B-02, nunca um número, ano, nota ou diferencial inventado):

    cabeçalho da marca (SUSEP) · hero com a recomendada (a PARCELA em destaque) · as 3 opções + comparar coberturas ·
    economia (SÓ com a apólice atual) · por que fechar com a corretora (fatos do banco) · quem vai cuidar de você ·
    como funciona depois do sim · se acontecer alguma coisa · perguntas antes de fechar · fecho · rodapé legal

⛔ NUNCA aqui: o nome do canal comparador, o selo do programa, duelo/ranking entre corretoras, "a melhor das N", contagem
regressiva, depoimento. O mesmo esqueleto técnico da carteira: CSS base + tema, o script IDÊNTICO a
`SCRIPT_DA_PROPOSTA` (o hash da CSP do `/r/` não muda), funciona SEM JavaScript (carrossel por `scroll-snap`, abas
âncoras, `<details>`), imprime, AA claro/escuro, alvos ≥ 44 px, nenhuma fonte < 12 px.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import quote

from . import proposta_apresentacao as AP
from . import proposta_html as PH
from .proposta_estilo import CSS_DA_PROPOSTA

#: as situações de quem AINDA NÃO é cliente (a renovação tem a página dela)
SITUACOES_DA_VENDA = ("novo_sem_apolice", "novo_com_apolice")
#: o marcador que `proposta.publicar_cotacao` grava no modelo (o comando antigo não grava: segue a carteira)
PAGINA_DE_VENDA = "venda"

_e = PH._e
#: quantos diferenciais da corretora a página mostra (mais que isso vira lista de cadastro, não argumento) e o teto de
#: seguradoras parceiras lidas da marca (a conta de "N seguradoras parceiras"). São do DESENHO da página — não são
#: número comercial; `multicalculo/proposta.py` os lê daqui (guarda G8 da 130-A)
TETO_DE_DIFERENCIAIS = 6
TETO_DE_PARCEIRAS_LIDAS = 60
_RE_PARCELA = re.compile(r"\b\d+\s*x\b", re.I)     # "Em até 10x de R$ …": a parcela já está no cartão (uma só)


def e_venda(modelo: Any) -> bool:
    """A página de VENDA vale para cliente novo (sem ou com apólice), da própria corretora, quando o modelo veio da
    cotação (`pagina="venda"`, gravado por `publicar_cotacao`, ou `servico="cotacao"`). O canal nunca."""
    return (isinstance(modelo, dict) and modelo.get("origem") != "canal"
            and modelo.get("situacao") in SITUACOES_DA_VENDA
            and (modelo.get("pagina") == PAGINA_DE_VENDA or modelo.get("servico") == "cotacao"))


# =====================================================================================================================
# os dados que a página lê
# =====================================================================================================================
def _e_mais_em_conta(o: dict) -> bool:
    return (o.get("id") in ("mais_em_conta", "economica")
            or bool(isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip()))


def opcoes_da_venda(modelo: dict) -> list[dict]:
    """As opções NA ORDEM da página de venda (§4): a recomendada (a 1ª do ranking real), a mais em conta, a mais
    completa — no máximo 3. A MESMA ordem no hero, nos cartões, no comparar, na barra, no chat e na mensagem."""
    ops = PH._ordenadas(modelo)
    if not ops:
        return []
    return [ops[0]] + sorted(ops[1:], key=lambda o: not _e_mais_em_conta(o))


def _venda(modelo: dict) -> dict:
    v = modelo.get("venda")
    return v if isinstance(v, dict) else {}


def _pagina_padrao() -> dict:
    """Os textos padrão do produto (`servicos.cotacao.pagina`), quando o modelo não os traz."""
    from app.services.multicalculo.config import PADRAO_DO_PRODUTO

    return dict(((PADRAO_DO_PRODUTO.get("servicos") or {}).get("cotacao") or {}).get("pagina") or {})


def _textos(lista: Any) -> list[str]:
    return [s.strip() for s in (lista or []) if isinstance(s, str) and s.strip()]


def _perguntas(lista: Any) -> list[dict]:
    saida = []
    for f in lista or []:
        if not isinstance(f, dict):
            continue
        p = str(f.get("pergunta") or f.get("p") or "").strip()
        r = str(f.get("resposta") or f.get("r") or "").strip()
        if p and r:
            saida.append({"p": p, "r": r})
    return saida


def _susep(anf: dict) -> str:
    """O número da SUSEP sem o prefixo que às vezes vem junto no cadastro ("SUSEP 202031234" → "202031234")."""
    s = str(anf.get("susep") or "").strip()
    return re.sub(r"(?i)^\s*susep\s*(?:n\s*[º°o.]*\s*)?[:\-]?\s*", "", s).strip()


def _parcela(o: dict) -> Optional[dict]:
    """UMA parcela por opção, a mesma regra em todo lugar (laudo 131-B: nunca duas parcelas para a mesma opção):
    a maior sem juros; senão a maior com juros (com o total escrito)."""
    pc = AP.parcelas(o)
    if pc["sem_juros"] and pc["sem_juros"][0] > 1:
        v, val = pc["sem_juros"]
        return {"vezes": v, "valor": val, "sem_juros": True, "total": None}
    if pc["com_juros"]:
        v, val, total, _ = pc["com_juros"]
        return {"vezes": v, "valor": val, "sem_juros": False, "total": total}
    return None


def parcela_em_texto(o: dict, *, juros: bool = False) -> str:
    """"10x de R$ 478,43" (espaço comum; com `juros`, + " sem juros"/" com juros") — ou o preço por ano, sem parcela.
    Para a barra, a prévia e o chat."""
    p = _parcela(o)
    if p:
        return (f"{p['vezes']}x de {PH._brl(p['valor'])}"
                + ((" sem juros" if p["sem_juros"] else " com juros") if juros else ""))
    preco = PH._brl(o.get("premio_anual"))
    return f"{preco} por ano" if preco else ""


def _numero_grande(valor: Any) -> str:
    s = AP.brl(valor).replace("R$" + AP.NB, "")
    inteiro, _, cent = s.partition(",")
    return (f'<span class="cur">R$</span><span class="int">{_e(inteiro)}</span>'
            f'<span class="dec">,{_e(cent)}</span>')


A_VISTA = "à" + AP.NB + "vista"            # laudo de design 132-B, item 8: "à / vista" nunca quebra


def _total_parcelado(o: dict) -> Optional[Any]:
    """Quanto a pessoa paga NO TOTAL se parcelar (a regra de `_parcela`): o total com juros, ou o próprio preço."""
    p = _parcela(o)
    if not p:
        return None
    return AP.dec(p["total"]) if p["total"] is not None else AP.dec(o.get("premio_anual"))


def a_vista_na_frente(ops: list[dict]) -> bool:
    """🔴 Laudo de design 132-B, D3: o número grande dos cartões é a PARCELA — enquanto a ordem das parcelas for a mesma
    do preço à vista. Quando inverte (a "Mais em conta" à vista com a parcela MAIOR que a da Recomendada, porque uma é
    sem juros e a outra com) ou quando nem todas têm parcela, o número grande dos TRÊS passa a ser o preço à vista —
    nunca um cartão "mais em conta" com o número maior."""
    linhas = [(AP.dec(o.get("premio_anual")), _parcela(o)) for o in ops]
    if len({bool(p) for _a, p in linhas}) > 1:
        return True
    for a1, p1 in linhas:
        for a2, p2 in linhas:
            if None not in (a1, a2) and p1 and p2 and a1 < a2 and AP.dec(p1["valor"]) > AP.dec(p2["valor"]):
                return True
    return False


def _bloco_do_preco(o: dict, cls: str, *, a_vista: bool = False) -> str:
    """O número forte (a parcela), o "10x de" discreto e, embaixo, o que fecha a conta: juros e à vista. Com
    `a_vista` (D3), o número forte é o preço à vista e a parcela desce para a linha de baixo."""
    p = _parcela(o)
    avista = AP.brl(o.get("premio_anual"))
    if a_vista and avista:
        linha2 = ""
        if p:
            linha2 = (f"ou {p['vezes']}x de {AP.brl(p['valor'])} sem juros." if p["sem_juros"] else
                      f"ou {p['vezes']}x de {AP.brl(p['valor'])} com juros, total {AP.brl(p['total'], False)}.")
        return (f'<div class="{cls}"><p class="pv"><span class="num">{_numero_grande(o.get("premio_anual"))}</span>'
                f' <span class="vz depois">{A_VISTA}</span></p>'
                + (f' <p class="pj">{_e(AP.nbsp(linha2))}</p>' if linha2 else "") + "</div>")
    if p:
        juros = ("sem juros" if p["sem_juros"]
                 else f"com juros, total {AP.brl(p['total'], False)}")
        linha2 = f"{juros}. Ou {avista} {A_VISTA}." if avista else f"{juros}."
        return (f'<div class="{cls}"><p class="pv"><span class="vz">{p["vezes"]}x de</span> '
                f'<span class="num">{_numero_grande(p["valor"])}</span></p>'
                f' <p class="pj">{_e(AP.nbsp(linha2))}</p></div>')
    if avista:
        return (f'<div class="{cls}"><p class="pv"><span class="num">{_numero_grande(o.get("premio_anual"))}</span>'
                f' <span class="vz depois">por ano</span></p></div>')
    return ""


def _nota_da_inversao(o: dict, rec: dict, rotulo_rec: str) -> str:
    """D3: o cartão mais barato À VISTA cuja parcela é MAIOR que a da recomendada diz por quê — só com os números do
    modelo (total parcelado de cada uma, nº de parcelas)."""
    a, b = AP.dec(o.get("premio_anual")), AP.dec(rec.get("premio_anual"))
    po, pr = _parcela(o), _parcela(rec)
    if o is rec or None in (a, b) or not po or not pr or not a < b or not AP.dec(po["valor"]) > AP.dec(pr["valor"]):
        return ""
    to, tr = _total_parcelado(o), _total_parcelado(rec)
    if to is not None and tr is not None and to > tr:
        return (f"Mais barata {A_VISTA}. Parcelada, a opção “{rotulo_rec}” sai mais em conta"
                + (" (sem juros)." if pr["sem_juros"] else "."))
    if po["vezes"] < pr["vezes"]:
        return (f"Mais barata {A_VISTA}. A parcela é maior porque são {po['vezes']} vezes, e não "
                f"{pr['vezes']} como na opção “{rotulo_rec}”.")
    return ""


def _franquia(o: dict) -> str:
    """Sem centavos: o MESMO arredondamento dos motivos do cartão ("Franquia reduzida: R$ 5.171" e, logo acima,
    "R$ 5.170,54" eram o mesmo número com duas caras — laudo de design 132-B, D4)."""
    fq = o.get("franquia") if isinstance(o.get("franquia"), dict) else {}
    return AP.brl(fq.get("valor"), False)


def _motivos(o: dict) -> list[str]:
    return [m.strip() for m in o.get("motivos") or [] if isinstance(m, str) and m.strip() and not _RE_PARCELA.search(m)]


def _conta(modelo: dict) -> Optional[dict]:
    return PH._conta_do_resumo(modelo)


def _economia(modelo: dict, rec: Optional[dict]) -> Optional[dict]:
    """🔴 Mutação 5 da SPEC: economia SÓ com a apólice atual lida (`situacao=novo_com_apolice` e a conta feita CONTRA
    o preço atual). É o preço de hoje menos o da RECOMENDADA (a opção que a página propõe), só quando ≥ R$ 1 — um
    aumento nunca aparece como vantagem."""
    if rec is None or modelo.get("situacao") != "novo_com_apolice":
        return None
    eco = (modelo.get("resumo") or {}).get("economia") if isinstance(modelo.get("resumo"), dict) else None
    if not isinstance(eco, dict) or eco.get("contra") != "atual":
        return None
    hoje, novo = AP.dec(eco.get("de")), AP.dec(rec.get("premio_anual"))
    if hoje is None or novo is None or AP.reais(hoje - novo) is None or AP.reais(hoje - novo) < 1:
        return None
    return {"menos": hoje - novo, "hoje": hoje}


def _anos(anf: dict, modelo: dict) -> Optional[tuple[int, int]]:
    desde = AP.numero_inteiro(anf.get("desde"))
    ano_ref = re.match(r"^(\d{4})", str(modelo.get("gerado_em") or ""))
    if desde and ano_ref and 0 < int(ano_ref.group(1)) - desde < 200:
        return int(ano_ref.group(1)) - desde, desde
    return None


def _google(anf: dict) -> Optional[tuple[str, int]]:
    g = anf.get("google") if isinstance(anf.get("google"), dict) else None
    if not g:
        return None
    nota, n = AP.dec(g.get("nota")), AP.numero_inteiro(g.get("avaliacoes"))
    if nota is None or n is None or n < 1:
        return None
    return f"{nota:.1f}".replace(".", ","), n


def _sobre(texto: Any, teto: int = 160) -> str:
    """O "sobre" da corretora numa frase só (laudo de design 132-B, D2): sem marcação, a 1ª frase inteira até `teto`
    caracteres — maior que isso, nada (nunca uma frase cortada no meio, nunca a história societária inteira)."""
    t = re.sub(r"[#*_>`\[\]]+", "", str(texto or ""))
    t = re.sub(r"\(\s*https?://[^)]*\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    primeira = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].strip() if t else ""
    return primeira if len(primeira) <= teto else ""


def _substituir(texto: str, *, corretora: str, validade: str) -> str:
    return (texto.replace("{corretora}", corretora or "corretora")
            .replace("{validade}", validade or "a data de validade desta cotação"))


# =====================================================================================================================
# a prévia do link (og:* e o PNG) — sem dado pessoal
# =====================================================================================================================
def previa_da_cotacao(modelo: dict) -> dict:
    """As MESMAS chaves de `previa_do_modelo` (o PNG lê estas). Sem o primeiro nome, o carro, CPF ou placa."""
    ops = opcoes_da_venda(modelo)
    rec = ops[0] if ops else {}
    anf = PH._anfitria(modelo)
    marca = str(anf.get("nome") or "").strip()
    seguradora = str(rec.get("seguradora") or "").strip()
    parcela = parcela_em_texto(rec, juros=True) if rec else ""
    validade = PH._data_curta(modelo.get("validade_ate"))
    conta = _conta(modelo)
    partes = []
    if conta and conta["cotadas"] > 1:
        partes.append(f"{conta['cotadas']} seguradoras comparadas, sem custo.")
    if marca:
        partes.append(f"Preparada por {marca}.")
    if validade:
        partes.append(f"Válida até {validade}.")
    fq = rec.get("franquia") if isinstance(rec.get("franquia"), dict) else {}
    return {
        "titulo": (f"A cotação do seu seguro: {seguradora}, {parcela}" if seguradora and parcela
                   else "A cotação do seu seguro está pronta"),
        "descricao": " ".join(partes) or "As opções que separamos para você.",
        "manchete": "A cotação do seu seguro está pronta",
        "seguradora": seguradora,
        "rotulo": str(rec.get("rotulo") or "").strip(),
        "preco": PH._brl(rec.get("premio_anual")),
        "franquia_tipo": str(fq.get("tipo") or "").strip(),
        "franquia": PH._brl(fq.get("valor")),
        "comparadas": conta["cotadas"] if conta else None,
        "corretoras": None,
        "canal": "",
        "marca": marca,
        "logo": PH._logo(anf),
        "validade": validade,
    }


# =====================================================================================================================
# o CSS só da venda — as variáveis são as do tema da carteira (claro/escuro, impressão)
# =====================================================================================================================
CSS_DA_VENDA = r"""
body.venda{background:var(--canvas)}
.venda .wrap{max-width:720px}
.exemplo{background:var(--surface-2);color:var(--ink);border-bottom:1px solid var(--line);font-size:13px;line-height:1.3;
  text-align:center;padding:8px 16px;font-weight:550}
/* cabeçalho da marca: o nome e o registro (autoridade) */
.vtop{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:14px;padding-bottom:6px}
.cred{margin:0;display:grid;justify-items:end;text-align:right;font-size:13px;line-height:1.3;color:var(--ink-muted)}
.cred b{font-weight:600;color:var(--ink-strong)}
/* D5 / item 11: o logo legível (36 px; 40 no notebook) e a placa do escuro do tamanho do logo */
.venda .brand img{height:36px;max-width:180px;object-fit:contain}
.venda .plate{display:inline-flex;width:max-content}
/* hero */
.vhero{padding-top:18px}
.vhero h1{margin:0;font-size:32px;line-height:1.06;font-weight:620;letter-spacing:-.028em;color:var(--ink-strong);
  font-variation-settings:'wdth' 86;text-wrap:balance;max-width:18ch}
.vhero .lede{margin:12px 0 0;font-size:16.5px;line-height:1.45;color:var(--ink);max-width:40ch}
.oferta{position:relative;isolation:isolate;margin:22px 0 0;border-radius:26px;padding:20px 20px 18px;background:var(--pass1);
  color:var(--pass1-on);box-shadow:0 1px 0 rgb(255 255 255 / .10) inset,0 22px 44px -26px rgb(var(--shadow-tint) / .55);overflow:hidden}
.oferta::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(120% 80% at 12% -12%, rgb(255 255 255 / .20), rgb(255 255 255 / 0) 60%)}
.of-tag{display:inline-flex;align-items:center;gap:6px;min-height:28px;padding:3px 12px;border-radius:999px;font-size:13.5px;font-weight:600;
  background:var(--badge);color:var(--badge-on)}
.of-tag svg{width:15px;height:15px}
.of-seg{margin:14px 0 0;font-size:24px;line-height:1.15;font-weight:620;letter-spacing:-.02em}
.of-seg .prod{display:block;font-size:15px;font-weight:500;letter-spacing:0;margin-top:2px}
.preco{margin:14px 0 0}
.pv{margin:0;display:flex;align-items:baseline;flex-wrap:wrap;gap:0 8px;line-height:1}
.pv .vz{font-size:17px;font-weight:550;letter-spacing:0}
.pv .vz.depois{font-size:15px}
.pv .num{display:inline-flex;align-items:baseline;letter-spacing:-.04em;font-variation-settings:'wdth' 80}
.pv .cur{font-size:20px;font-weight:600;margin-right:4px;letter-spacing:0;align-self:flex-start;margin-top:6px}
.pv .int{font-size:64px;font-weight:660}
.pv .dec{font-size:26px;font-weight:620}
.pj{margin:8px 0 0;font-size:15px;line-height:1.4}
.of-fatos{margin:16px 0 0;padding:12px 0 0;border-top:1px solid color-mix(in srgb, var(--pass1-on) 24%, transparent);
  display:grid;grid-template-columns:1fr 1fr;gap:10px 16px}
.of-fatos div{display:grid;gap:1px;min-width:0}
.of-fatos dt{font-size:13px}
.of-fatos dd{margin:0;font-size:17px;font-weight:600;overflow-wrap:anywhere}
.of-fatos .valid{margin:0;font-size:15px;opacity:1}
.of-pq{margin:14px 0 0;font-size:15px;line-height:1.42}
.of-pq b{font-weight:650}
/* D1: a economia (SÓ com a apólice lida) no cartão, logo abaixo do preço */
.of-eco{margin:14px 0 0;display:inline-flex;align-items:flex-start;gap:7px;padding:7px 12px 7px 9px;border-radius:12px;
  background:var(--pos-bg);color:var(--pos);font-size:15.5px;font-weight:620;line-height:1.3}
.of-eco svg{width:18px;height:18px;flex:none;margin-top:1px}
.of-ver{display:inline-flex;align-items:center;gap:6px;min-height:44px;margin-top:10px;font-size:15px;font-weight:600;
  color:inherit;text-underline-offset:3px}
.of-ver svg{width:18px;height:18px}

/* as 3 opções */
.venda section.s{padding-top:56px}
.venda .s>.sub{max-width:60ch}
.venda .navrow{max-width:none;margin:16px 0 0}
.vtrack{margin-top:6px}
/* position: o script mede `offsetLeft` dos cartões; relativo ao TRILHO (e não à página) o "lado a lado" é detectado */
.venda .track{position:relative;padding:10px 16px 28px;gap:12px}
.venda .slot{animation:none;grid-row:auto;display:flex}
.venda .slot::before{display:none}
.venda .pass{display:flex;flex-direction:column;grid-row:auto;grid-template-rows:none;transform:none;-webkit-mask:none;mask:none;
  cursor:auto;border-radius:22px;background:var(--surface);border:1px solid var(--line);padding:18px 18px 16px;
  box-shadow:0 12px 30px -24px rgb(var(--shadow-tint) / .5)}
.venda .pass::after{box-shadow:none}
.venda .pass[data-v="1"]{border:2px solid var(--p-text)}
.venda .spread .slot.on .pass::after{box-shadow:none}
.venda .spread .slot.on .pass{box-shadow:0 0 0 3px color-mix(in srgb, var(--p-text) 22%, transparent),0 12px 30px -24px rgb(var(--shadow-tint) / .5)}
.op-tag{align-self:flex-start;display:inline-flex;align-items:center;min-height:28px;padding:3px 11px;border-radius:999px;
  font-size:13.5px;font-weight:600;background:var(--surface-2);color:var(--ink-strong)}
.pass[data-v="1"] .op-tag{background:var(--p);color:var(--p-on)}
.op-seg{margin:12px 0 0;font-size:20px;font-weight:620;letter-spacing:-.015em;color:var(--ink-strong);line-height:1.2}
.op-seg .prod{display:block;font-size:14px;font-weight:500;letter-spacing:0;color:var(--ink-muted);margin-top:2px}
.op .preco{margin-top:12px;color:var(--ink-strong)}
.op .pv .int{font-size:44px}
.op .pv .dec{font-size:20px}
.op .pv .cur{font-size:17px;margin-top:4px}
.op .pv .vz{font-size:15px}
.op .pj{font-size:14px;color:var(--ink-muted);margin-top:6px}
/* D3: o cartão mais barato à vista com a parcela maior diz por quê */
.op-inv{margin:10px 0 0;padding:8px 10px;border-radius:10px;background:var(--surface-2);font-size:13.5px;line-height:1.38;color:var(--ink)}
.op-fq{margin:12px 0 0;padding:10px 0 0;border-top:1px dashed var(--line-strong);display:flex;justify-content:space-between;
  align-items:baseline;gap:10px;font-size:14px;color:var(--ink-muted)}
.op-fq b{font-size:17px;font-weight:600;color:var(--ink-strong)}
.op-pq{margin:12px 0 0}
.op-pq h3{margin:0 0 6px;font-size:14px;font-weight:600;color:var(--ink-strong)}
.op .covs{margin-top:12px}
.op .more summary{min-height:48px}
.op-pe{margin-top:auto;padding-top:16px}
.op-pe .want{width:100%}
.venda .cmp{margin-top:4px}

/* economia (só com a apólice) */
.eco{margin:28px 0 0;border-radius:20px;padding:18px 20px;background:var(--pos-bg);color:var(--ink-strong);
  border:1px solid color-mix(in srgb, var(--pos) 30%, transparent)}
.eco h2{margin:0;font-size:24px;line-height:1.15;font-weight:620;letter-spacing:-.02em;color:var(--pos)}
.eco-conta{margin:12px 0 0;display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:520px}
.eco-conta p{margin:0;display:grid;gap:2px;padding:10px 12px;border-radius:12px;background:var(--surface)}
.eco-conta span{font-size:13.5px;color:var(--ink-muted);line-height:1.3}
.eco-conta b{font-size:17px;font-weight:620;color:var(--ink-strong)}

/* por que fechar com a corretora */
/* D2: a grade se ajusta ao número de fatos (2 fatos nunca deixam meia linha vazia) */
.vfatos{margin:20px 0 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0 24px;border-top:1px solid var(--line)}
.vfato{padding:14px 0;border-bottom:1px solid var(--line);display:grid;gap:2px;min-width:0}
.vfato b{font-size:24px;line-height:1.1;font-weight:640;letter-spacing:-.02em;color:var(--ink-strong);display:flex;align-items:center;gap:6px;
  font-variation-settings:'wdth' 88;overflow-wrap:anywhere}
.vfato b svg{width:18px;height:18px;color:var(--a)}
.vfato span{font-size:13.5px;color:var(--ink-muted);line-height:1.3}
.difs{list-style:none;margin:20px 0 0;padding:0;display:grid;gap:10px}
.difs li{display:grid;grid-template-columns:20px 1fr;gap:10px;font-size:15.5px;line-height:1.4;color:var(--ink)}
.difs svg{width:20px;height:20px;color:var(--pos);margin-top:1px}
.papel{margin:20px 0 0;padding:16px 18px;border-radius:18px;background:var(--p-soft);color:var(--ink);font-size:15.5px;line-height:1.45;max-width:66ch}
.papel b{display:block;color:var(--ink-strong);font-weight:620;margin-bottom:2px;font-size:16.5px}
/* D2e: com pouco dado de marca, o papel ABRE o bloco (texto, não caixa de canto) */
.papel.lead{background:none;padding:0;margin-top:14px;font-size:17px;line-height:1.5;max-width:60ch}
.papel.lead b{display:inline;font-size:inherit;margin:0}
.vsobre{font-size:16.5px;color:var(--ink)}
.fonte{margin:10px 0 0;font-size:13px;color:var(--ink-muted)}

/* depois do sim */
.venda .steps p{margin-top:5px}
.venda .steps b{display:block;color:var(--ink-strong);font-weight:600}

/* D6: "Se acontecer" é um cartão compacto — a linha do tempo numerada é uma só (a do "depois do sim") */
.sin{margin:16px 0 0;display:grid;grid-template-columns:28px 1fr;gap:14px;padding:16px 18px;border-radius:18px;
  background:var(--surface);border:1px solid var(--line)}
.sin>svg{width:28px;height:28px;color:var(--p-text)}
.sin ul{margin:0;padding:0;list-style:none;display:grid;gap:8px}
.sin li{font-size:15px;line-height:1.42;color:var(--ink)}
/* D5: o lado esquerdo do hero no notebook (só ≥ 1024 px) */
.vlado{display:none}
.vhoje{display:flex;align-items:center;gap:14px;padding:14px 18px;border-radius:16px;background:var(--surface);border:1px solid var(--line)}
.vhoje div{display:grid;gap:1px}
.vhoje div span{font-size:13px;color:var(--ink-muted);line-height:1.3}
.vhoje b{font-size:23px;line-height:1.15;font-weight:640;color:var(--ink-strong);letter-spacing:-.015em}
.vhoje .on b{color:var(--pos)}
.vseta{display:grid;color:var(--ink-muted)}
.vseta svg{width:20px;height:20px}
.vfaixa{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.vfaixa li{display:grid;grid-template-columns:20px 1fr;gap:10px;font-size:15.5px;line-height:1.35;color:var(--ink)}
.vfaixa svg{width:20px;height:20px;color:var(--pos)}
.vmini{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px 16px;padding:14px 16px;border-radius:18px;
  background:var(--surface);border:1px solid var(--line)}
.vmini-t{grid-column:1/-1;font-size:13px;color:var(--ink-muted)}
.vmini .host-id{gap:12px}
.vmini .mono.big{width:44px;height:44px;border-radius:12px;font-size:17px}
.vmini .plate img{height:36px}
.vmini b{display:block;font-size:17px;font-weight:620;color:var(--ink-strong);line-height:1.2}
.vmini .host-id div span{display:block;font-size:13.5px;color:var(--ink-muted);line-height:1.3}
.vmini-wa{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 14px;border-radius:12px;border:1px solid var(--line-strong);
  font-size:14.5px;font-weight:600;text-decoration:none;color:var(--ink-strong);white-space:nowrap}
.vmini-wa svg{width:18px;height:18px}
/* item 12: sem a barra fixa, o fim não guarda o lugar dela */
.venda .endpad.curto{height:24px}

/* fecho */
.venda .fim .close{margin-top:18px;max-width:520px}
.nada{margin:10px 0 0;font-size:14.5px;color:var(--ink-muted)}
.semnum{margin:16px 0 0;padding:14px 16px;border-radius:14px;background:var(--surface-2);font-size:15.5px;color:var(--ink);max-width:60ch}
/* sem JavaScript a barra fica com a RECOMENDADA, com o nome escrito: nunca promete outra opção */
.no-js .venda .dock .close{display:flex}

@media (min-width:760px){
  .vhero{padding-top:34px}
  /* D5: o título respira (largura 92, sem colar as letras) */
  .vhero h1{font-size:46px;letter-spacing:-.02em;font-variation-settings:'wdth' 92}
}
@media (min-width:1024px){
  /* UM eixo só (laudo 131-B): tudo na mesma coluna de 1080 px, alinhado à esquerda */
  .venda .wrap{max-width:1080px}
  .vtop{max-width:1080px}
  .vhero{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:48px;align-items:center;padding-top:40px}
  .vhero h1{font-size:52px;max-width:none}
  .vhero .lede{font-size:18px;max-width:44ch}
  .venda .brand img{height:40px}
  .vlado{display:grid;gap:16px;margin-top:26px;max-width:480px}
  /* o que o lado esquerdo do hero já mostra no notebook não se repete lá embaixo */
  .venda .vhost,.venda .eco{display:none}
  /* D6: as duas seções do "depois" lado a lado */
  .vduas{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:48px;align-items:start}
  .oferta{margin-top:0;padding:26px 26px 22px}
  .vtrack{max-width:1080px;margin:6px auto 0;padding:0 var(--gutter)}
  .venda .track{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));grid-template-rows:none;grid-auto-flow:row;
    grid-auto-columns:auto;overflow:visible;scroll-snap-type:none;padding:10px 0 28px;gap:20px;column-gap:20px;perspective:none}
  .venda .navrow{display:none}
  .venda .s>h2{max-width:none}
}
@media (max-width:400px){
  /* item 9: no celular a barra não corta o nome da seguradora — a linha de baixo quebra em duas */
  .venda .close .t span{white-space:normal;font-size:13px;line-height:1.2}
}
@media (max-width:359px){.pv .int{font-size:54px}.eco-conta{grid-template-columns:1fr}}
@media print{
  .exemplo{border:1px solid #888}
  .oferta{background:#fff!important;color:#000;border:1.5px solid #000;box-shadow:none}
  .oferta::before{display:none}
  .of-tag,.pass[data-v="1"] .op-tag{border:1px solid #000;background:#fff;color:#000}
  .of-ver,.op-pe,.vlado{display:none!important}
  .venda .vhost,.venda .eco{display:block!important}
  .venda .pass{border:1px solid #888;box-shadow:none;margin-bottom:12pt;break-inside:avoid;padding:10pt}
  .eco{background:#fff;border:1px solid #000}
  .eco h2{color:#000}
  .papel{background:#fff;border:1px solid #888}
  .vhero{display:block}
  .vtrack{padding:0}
}
"""


# =====================================================================================================================
# a página
# =====================================================================================================================
def _as_outras(conta: Optional[dict]) -> str:
    """"Das outras 5, 4 só ofereceram produtos diferentes e 1 não deu preço." — o que o topo ("Cotamos em 16 — 11 com
    a mesma cobertura completa") não contou; cada seguradora em UM lugar e as partes somam o total (J-B3)."""
    if not conta:
        return ""
    d, nr = conta["diferentes"], conta["nr"]
    if d + nr == 1:
        return "A outra " + ("só ofereceu um produto diferente." if d else "não deu preço.")
    partes = []
    if d:
        partes.append(f"{d} só {'ofereceu um produto diferente' if d == 1 else 'ofereceram produtos diferentes'}")
    if nr:
        partes.append(f"{nr} não {'deu' if nr == 1 else 'deram'} preço")
    return f"Das outras {d + nr}, {' e '.join(partes)}." if partes else ""


def render_cotacao(modelo: dict) -> str:
    """O documento inteiro da página de VENDA, a partir do modelo do CONTRATO §5 + `venda` (corretor, marca, textos).
    Todo texto do modelo é escapado; campo ausente não aparece."""
    modelo = modelo if isinstance(modelo, dict) else {}
    venda = _venda(modelo)
    pagina_pad = _pagina_padrao()
    previa = previa_da_cotacao(modelo)
    ops = opcoes_da_venda(modelo)
    rec = ops[0] if ops else None
    anf = PH._anfitria(modelo)
    nome_anf = str(anf.get("nome") or "").strip()
    bem = AP.o_bem(modelo)
    cliente = modelo.get("cliente") if isinstance(modelo.get("cliente"), dict) else {}
    nome = str(cliente.get("primeiro_nome") or "").strip()
    digitos = PH._digitos_do_whatsapp(modelo)
    logo = PH._logo(anf)
    susep = _susep(anf)
    validade_curta = PH._data_curta(modelo.get("validade_ate"))
    validade = AP.data_br(modelo.get("validade_ate"))
    corretor = venda.get("corretor") if isinstance(venda.get("corretor"), dict) else {}
    corretor_nome = str(corretor.get("primeiro_nome") or "").strip()
    fala_com_o_corretor = bool(corretor_nome and digitos and digitos == str(corretor.get("whatsapp") or ""))
    com_quem = (f"com {corretor_nome}" if fala_com_o_corretor else (f"com a {nome_anf}" if nome_anf else ""))
    sobre_o_bem = f"do {bem['apelido']}" if bem["apelido"] else ""
    ola = f"Olá! Aqui é {nome}." if nome else "Olá!"
    a_vista = a_vista_na_frente(ops)             # D3: a parcela inverte a ordem → o número grande é o à vista
    eco = _economia(modelo, rec)

    def wa(texto: str) -> str:
        return f"https://wa.me/{digitos}?text={quote(texto, safe='')}" if digitos else ""

    def href_fechar(o: dict) -> str:
        return f"?{PH.PARAMETRO_DO_FECHAR}={quote(str(o['id']), safe='')}" if digitos else ""

    def rotulo(o: dict) -> str:
        return str(o.get("rotulo") or o.get("id") or "")

    # ---- 1. cabeçalho da marca
    if logo:
        marca = (f'<span class="brand"><span class="plate"><img src="{_e(logo)}" alt="{_e(nome_anf)}" height="36">'
                 f'</span></span>')
    elif nome_anf:
        marca = (f'<span class="brand"><span class="mono" aria-hidden="true">{_e(AP.monograma(nome_anf))}</span>'
                 f'<span class="brand-name">{_e(nome_anf)}</span></span>')
    else:
        marca = '<span class="brand"></span>'
    cred = ('<p class="cred"><span>Corretora de seguros</span> '
            + (f'<b>SUSEP nº {_e(susep)}</b>' if susep else "") + "</p>")

    # ---- 2. hero: a frase, o "sem custo e sem compromisso" e a recomendada com a PARCELA em destaque
    do_bem = f"do seu {bem['apelido']}" if bem["apelido"] else "do seu seguro"
    frase = f"a cotação {do_bem} está pronta"
    h1 = (f'{_e(nome)}, {_e(frase)}' if nome else _e(frase[:1].upper() + frase[1:]))
    conta = _conta(modelo)
    n_cotadas = conta["cotadas"] if conta else AP.numero_inteiro((modelo.get("resumo") or {}).get("seguradoras_cotadas"))
    if conta and conta["cotadas"] > 1 and conta["completas"] < conta["cotadas"]:
        # laudo de design 132-B, item 7: o N REAL (§4) — quantas cotamos E quantas têm a mesma cobertura; as outras
        # (produto diferente, sem preço) a frase das opções conta logo abaixo, e as partes somam o total (J-B3)
        lede = (f"Cotamos em {conta['cotadas']} seguradoras para você — {conta['completas']} com a mesma cobertura "
                "completa. Sem custo e sem compromisso.")
    elif n_cotadas and n_cotadas > 1:
        lede = f"Comparamos {n_cotadas} seguradoras para você — sem custo e sem compromisso."
    else:
        lede = "Cotamos o seu seguro sem custo e sem compromisso."
    oferta = ""
    if rec is not None:
        melhor = PH.e_a_melhor_do_ranking(modelo, rec)
        tag = "Nossa recomendação" if melhor else rotulo(rec)
        produto = AP.sem_seguradora(rec.get("produto"), rec.get("seguradora"))
        motivos = _motivos(rec)
        pq = ""
        if motivos:
            pq = (f'<p class="of-pq"><b>{"Por que recomendamos" if melhor else "Sobre esta opção"}:</b> '
                  f'{_e(AP.nbsp(motivos[0].rstrip(".")))}.</p>')
        fq = _franquia(rec)
        fatos = ""
        if fq or validade_curta:
            fatos = ('<dl class="of-fatos">'
                     + (f'<div><dt>Franquia</dt> <dd>{_e(fq)}</dd></div> ' if fq else "")
                     + (f'<div><dt>Validade</dt> <dd class="valid">Preço válido até {_e(validade_curta)}</dd></div>'
                        if validade_curta else "")
                     + "</dl>")
        # D1: o "uau" honesto (SÓ com a apólice lida) mora no cartão, logo abaixo do preço — o critério, no rodapé
        of_eco = (f'<p class="of-eco">{PH.ICO["check"]}<span>{_e(AP.brl(eco["menos"], False))} a menos por ano que o '
                  f'seu seguro atual</span></p>' if eco else "")
        ver = (f'<a class="of-ver" href="#opcoes">Ver as {len(ops)} opções{PH.ICO["chev"]}</a>' if len(ops) > 1 else "")
        oferta = (f'<article class="oferta" aria-labelledby="h-oferta">'
                  f'<span class="of-tag">{PH.ICO["check"] if melhor else ""}{_e(tag)}</span> '
                  f'<h2 class="of-seg" id="h-oferta">{_e(rec.get("seguradora") or "")}'
                  + (f' <span class="prod">{_e(produto)}</span>' if produto else "") + "</h2>"
                  + _bloco_do_preco(rec, "preco", a_vista=a_vista) + of_eco + fatos + pq + ver + "</article>")

    # ---- 2b. o lado esquerdo do hero no NOTEBOOK (D5: sem meia tela vazia): a conta de hoje × nova (só com a
    #          apólice), dois fatos e o mini-cartão de quem cuida. Abaixo de 1024 px não aparece (o celular já tem tudo
    #          isso na ordem da página); acima, os blocos que ele repete lá embaixo saem (`.vhost`, `.eco`)
    lado = []
    if eco and rec is not None:
        lado.append(f'<div class="vhoje"><div><span>Seu seguro atual</span><b>{_e(AP.brl(eco["hoje"], False))}</b>'
                    f'<span>por ano</span></div><span class="vseta" aria-hidden="true">{PH.ICO["right"]}</span>'
                    f'<div class="on"><span>Opção “{_e(rotulo(rec))}”</span><b>{_e(AP.brl(rec.get("premio_anual"), False))}'
                    f'</b><span>por ano, {A_VISTA}</span></div></div>')
    faixa = ["Nada é cobrado agora"]
    faixa.append(f"A {nome_anf} representa você diante da seguradora" if nome_anf
                 else "A corretora representa você diante da seguradora")
    lado.append('<ul class="vfaixa">' + "".join(f'<li>{PH.ICO["check"]}<span>{_e(x)}</span></li>' for x in faixa)
                + "</ul>")

    # ---- 3. as 3 opções (carrossel sem JS no celular; lado a lado no notebook) + comparar coberturas
    topo, resto, resto_iguais = AP.escolher_coberturas(ops) if ops else ([], [], True)
    n = len(ops)
    cartoes = []
    for i, o in enumerate(ops):
        if i == 0:
            mot = _motivos(o)[:3]
            titulo = "Por que recomendamos" if PH.e_a_melhor_do_ranking(modelo, o) else "Sobre esta opção"
            pq = (f'<div class="op-pq"><h3>{titulo}</h3><ul class="why">'
                  + "".join(f'<li>{PH.ICO["check"]}<span>{_e(AP.nbsp(m))}</span></li>' for m in mot)
                  + "</ul></div>") if mot else ""
        elif isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip():
            pq = (f'<div class="op-pq"><h3>Por que custa menos</h3><p class="expl">'
                  f'{_e(AP.nbsp(o["por_que_mais_barata"].strip()))}</p></div>')
        else:
            muda = [x for x in o.get("o_que_muda") or [] if isinstance(x, str) and x.strip()]
            fala_franquia = any("franquia" in x.lower() for x in muda)
            itens = [_e(AP.nbsp(x)) for x in muda + [m for m in _motivos(o)
                                                     if not (fala_franquia and "franquia" in m.lower())]][:4]
            # R6 (vale na venda também): o que esta opção TEM e a recomendada não tem, com o selo "a mais"
            itens += [_e(AP.nbsp(f'{c["nome"]}: {AP.valor_para_o_cliente(c.get("chave"), AP.valor_da_cobertura(c))}'))
                      + PH._pill("up", "a mais") for c in PH.so_nas_outras(ops, o)]
            pq = (f'<div class="op-pq"><h3>O que muda em relação {_e(PH._a_referencia(rec))}</h3><ul class="diffs">'
                  + "".join(f"<li>{x}</li>" for x in itens) + "</ul></div>") if itens else ""
        covs = "".join(PH._celula_cobertura(k, o, rec, "li", cliente=True) for k in topo)
        mais = ""
        lis = "".join(PH._celula_cobertura(k, o, rec, "li", cliente=True) for k in resto)
        if lis:
            n_resto = sum(1 for k in resto if AP.cobertura(o, k))
            mais = (f'<details class="more"><summary><span>Mais {n_resto} cobertura{"s" if n_resto > 1 else ""}'
                    + (", iguais nas três" if resto_iguais and n == 3 else ", iguais nas opções" if resto_iguais else "")
                    + f'</span>{PH.ICO["chev"]}</summary><ul class="covs">{lis}</ul></details>')
        produto = AP.sem_seguradora(o.get("produto"), o.get("seguradora"))
        fq = _franquia(o)
        inversao = _nota_da_inversao(o, rec, rotulo(rec)) if a_vista else ""
        aria = f"Opção {i + 1} de {n}: {rotulo(o)}, {o.get('seguradora') or ''}, {parcela_em_texto(o)}"
        pe = (f'<div class="op-pe"><a class="want" href="{_e(href_fechar(o))}" rel="nofollow">{PH.ICO["wa"]}'
              f'Quero esta</a></div>' if digitos else "")
        cartoes.append(
            f'<div class="slot" id="opt-{i}" data-i="{i}" role="tabpanel" aria-labelledby="tab-{i}">'
            f'<article class="pass op" data-v="{i + 1}" aria-label="{_e(aria)}">'
            f'<span class="op-tag">{_e(rotulo(o))}</span> '
            f'<p class="op-seg">{_e(o.get("seguradora") or "")}'
            + (f' <span class="prod">{_e(produto)}</span>' if produto else "") + "</p>"
            + _bloco_do_preco(o, "preco", a_vista=a_vista)
            + (f'<p class="op-inv">{_e(AP.nbsp(inversao))}</p>' if inversao else "")
            + (f'<p class="op-fq"><span>Franquia</span> <b>{_e(fq)}</b></p>' if fq else "")
            + pq + (f'<ul class="covs">{covs}</ul>' if covs else "") + mais + pe + "</article></div>")
    abas = "".join(f'<a class="tab" href="#opt-{i}" role="tab" id="tab-{i}" aria-controls="opt-{i}" '
                   f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else " tabindex=" + chr(34) + "-1" + chr(34)}>'
                   f'{_e(rotulo(o))}</a>' for i, o in enumerate(ops))
    navrow = ""
    if n > 1:
        navrow = (f'<div class="navrow"><div class="tabs" role="tablist" aria-label="Opções">'
                  f'<span class="tab-ind" id="tab-ind" aria-hidden="true"></span>{abas}</div>'
                  f'<div class="nav js-only"><button type="button" id="prev" aria-label="Opção anterior">{PH.ICO["left"]}</button>'
                  f'<span class="count" id="count" aria-live="polite">1 de {n}</span>'
                  f'<button type="button" id="next" aria-label="Próxima opção">{PH.ICO["right"]}</button></div></div>')
    # item 7 / D6: o topo já diz quantas cotamos e quantas são completas; aqui só as OUTRAS (as partes somam o total)
    frase_conta = _as_outras(conta) if conta and lede.startswith("Cotamos em") else ""
    titulo_ops = {1: "A opção que separamos", 2: "As duas opções que separamos"}.get(n, f"As {n} opções que separamos")
    opcoes_html = ""
    if ops:
        opcoes_html = (f'<div class="wrap"><section class="s" id="opcoes" aria-labelledby="h-op">'
                       f'<h2 id="h-op">{_e(titulo_ops)}</h2>'
                       + (f'<p class="sub">{_e(frase_conta)}</p>' if frase_conta else "")
                       + navrow + "</section></div>"
                       f'<div class="vtrack"><div class="track" id="track" tabindex="0" role="region" '
                       f'aria-roledescription="carrossel" aria-label="As {n} opções. Use as setas do teclado para trocar.">'
                       + "".join(cartoes) + "</div></div>"
                       + '<div class="wrap">' + PH._comparar(ops, cliente=True).replace("Comparar lado a lado",
                                                                                      "Comparar coberturas")
                       + "</div>")

    # ---- 4. economia: SÓ com a apólice atual — a CONTA (o número já está no cartão da oferta; o critério, no rodapé)
    eco_html = ""
    if eco:
        eco_html = (f'<section class="eco" aria-labelledby="h-eco"><h2 id="h-eco">'
                    f'{_e(AP.brl(eco["menos"], False))} a menos por ano que o seu seguro atual</h2>'
                    f'<div class="eco-conta"><p><span>Seu seguro atual</span> <b>{_e(AP.brl(eco["hoje"], False))} por ano</b>'
                    f'</p><p><span>Com a opção “{_e(rotulo(rec))}”</span> '
                    f'<b>{_e(AP.brl(rec.get("premio_anual"), False))} por ano</b></p></div></section>')

    # ---- 5. por que fechar com a corretora (só FATOS do banco; D2: a 1ª frase do que VENDE, sem a SUSEP — ela está no
    #         topo e no rodapé — e sem repetir quantas deram preço nesta cotação, que o topo já disse)
    fatos = []
    anos = _anos(anf, modelo)
    if anos:
        fatos.append(f'<div class="vfato"><b>{anos[0]}{AP.NB}{"ano" if anos[0] == 1 else "anos"}</b> '
                     f'<span>no mercado, desde {anos[1]}</span></div>')
    marca_v = venda.get("marca") if isinstance(venda.get("marca"), dict) else {}
    parceiras = AP.numero_inteiro(marca_v.get("seguradoras_parceiras"))
    if parceiras and parceiras > 1:
        fatos.append(f'<div class="vfato"><b>{parceiras} seguradoras</b> <span>parceiras da corretora</span></div>')
    g = _google(anf)
    if g:
        fatos.append(f'<div class="vfato"><b>{PH.ICO["star"]}{g[0]}</b> <span>no Google, {g[1]} avaliações</span></div>')
    fonte_g = ""
    gd = anf.get("google") if isinstance(anf.get("google"), dict) else {}
    if g and str(gd.get("fonte") or "").strip():
        fonte_g = f'<p class="fonte">Nota e avaliações: {_e(AP.aspas_tipograficas(gd["fonte"]))}.</p>'
    difs = _textos(venda.get("diferenciais"))
    sobre = _sobre(marca_v.get("sobre"))
    papel = ("<b>Quem representa você é a corretora.</b> "
             f"A {_e(nome_anf) if nome_anf else 'corretora'} compara as seguradoras, explica cada cobertura antes de você "
             "decidir e fica do seu lado diante da seguradora — na contratação e, principalmente, se você precisar "
             "acionar o seguro.")
    pq_html = ""
    if nome_anf:
        magro = len(fatos) < 2 and not difs          # D2e: com pouco dado, o PAPEL abre o bloco (não é caixa de canto)
        pq_html = (f'<section class="s" aria-labelledby="h-pq"><h2 id="h-pq">Por que fechar com a {_e(nome_anf)}</h2>'
                   + (f'<p class="sub vsobre">{_e(sobre)}</p>' if sobre else "")
                   + (f'<p class="papel lead">{papel}</p>' if magro else "")
                   + (f'<div class="vfatos">{"".join(fatos)}</div>' if fatos else "") + fonte_g
                   + ('<ul class="difs">' + "".join(f'<li>{PH.ICO["check"]}<span>{_e(AP.nbsp(d))}</span></li>'
                                                    for d in difs[:TETO_DE_DIFERENCIAIS]) + "</ul>" if difs else "")
                   + ("" if magro else f'<p class="papel">{papel}</p>') + "</section>")

    # ---- 6. quem vai cuidar de você: o corretor que cotou → senão a corretora
    cidade = str(anf.get("cidade") or "").strip()
    site = str(anf.get("site") or "").strip()
    site_ok = re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~/-]*)?", site or "") is not None
    host_html = ""
    if corretor_nome or nome_anf:
        if corretor_nome:
            id_visual = f'<span class="mono big" aria-hidden="true">{_e(AP.monograma(corretor_nome))}</span>'
            titulo = corretor_nome
            linha2 = f"fez a sua cotação{(' na ' + nome_anf) if nome_anf else ''}"
            texto = "Fala direto com quem preparou estas opções, do fechamento à apólice — e depois também."
        else:
            id_visual = (f'<span class="plate"><img src="{_e(logo)}" alt="" height="44"></span>' if logo
                         else f'<span class="mono big" aria-hidden="true">{_e(AP.monograma(nome_anf))}</span>')
            titulo = nome_anf
            linha2 = cidade
            texto = "A mesma equipe que preparou estas opções cuida do seu seguro depois do sim."
        rotulo_wa = f"Falar com {corretor_nome}" if fala_com_o_corretor else "WhatsApp"
        link_wa = wa(f"{ola} Vim pela cotação do seguro{(' ' + sobre_o_bem) if sobre_o_bem else ''}.")
        canais = ""
        if digitos or site_ok:
            canais = ('<div class="chan">'
                      + (f'<a href="{_e(link_wa)}" rel="noopener">{PH.ICO["wa"]}{_e(rotulo_wa)}</a>' if digitos else "")
                      + (f'<a href="https://{_e(site)}" rel="noopener">{PH.ICO["globe"]}{_e(site)}</a>' if site_ok else "")
                      + "</div>")
        host_html = (f'<section class="s vhost" aria-labelledby="h-host"><h2 id="h-host">Quem vai cuidar de você</h2>'
                     f'<div class="host"><div class="host-id">{id_visual}<div><h3>{_e(titulo)}</h3>'
                     + (f" <p>{_e(linha2)}</p>" if linha2 else "") + "</div></div>"
                     f'<p class="sub0">{_e(texto)}</p>' + canais + "</div></section>")
        # o mini-cartão do hero no notebook: o MESMO conteúdo (quem, o que fez, o WhatsApp)
        # (sem corretor, o monograma: o logo já está no topo, a dois palmos dali)
        mini_visual = (id_visual if corretor_nome
                       else f'<span class="mono big" aria-hidden="true">{_e(AP.monograma(nome_anf))}</span>')
        lado.append(f'<div class="vmini"><span class="vmini-t">Quem vai cuidar de você</span>'
                    f'<div class="host-id">{mini_visual}<div><b>{_e(titulo)}</b>'
                    + (f"<span>{_e(linha2)}</span>" if linha2 else "") + "</div></div>"
                    + (f'<a class="vmini-wa" href="{_e(link_wa)}" rel="noopener">{PH.ICO["wa"]}{_e(rotulo_wa)}</a>'
                       if digitos else "") + "</div>")

    # ---- 7. como funciona depois do sim — a ÚNICA linha do tempo numerada (D6)
    passos = _textos(venda.get("depois_do_sim")) or _textos(pagina_pad.get("depois_do_sim"))
    passos = [_substituir(p, corretora=nome_anf, validade=validade) for p in passos][:4]
    depois_html = ""
    if passos:
        itens = []
        for p in passos:
            titulo, sep, resto_p = p.partition(". ")
            corpo = (f"<b>{_e(titulo)}.</b>{_e(resto_p)}" if sep and resto_p else _e(p))
            itens.append(f"<li><p>{corpo}</p></li>")
        depois_html = (f'<section class="s" aria-labelledby="h-depois"><h2 id="h-depois">Como funciona depois do sim</h2>'
                       f'<ol class="steps">{"".join(itens)}</ol></section>')

    # ---- 8. se acontecer alguma coisa — um cartão compacto (não uma 2ª linha do tempo), com o NOME da corretora
    sinistro_l = modelo.get("sinistro") if isinstance(modelo.get("sinistro"), list) else anf.get("sinistro")
    passos_s = [PH._frase_do_cliente(s, nome_anf) for s in _textos(sinistro_l)]
    tem_assistencia = any(AP.cobertura(o, "assistencia") for o in ops)   # só afirma o que as opções TÊM
    sinistro = ""
    if passos_s:
        sinistro = (f'<section class="s" aria-labelledby="h-sin"><h2 id="h-sin">Se acontecer alguma coisa</h2>'
                    + (f'<p class="sub">{"O guincho e a assistência 24 h são da seguradora. " if tem_assistencia else ""}'
                       f'Quem cuida do seu caso com ela é a {_e(nome_anf)}, não um 0800.</p>' if nome_anf else "")
                    + f'<div class="sin">{PH.ICO["casco"]}<ul>'
                    + "".join(f"<li>{_e(AP.nbsp(s))}</li>" for s in passos_s) + "</ul></div></section>")
    duas = (f'<div class="vduas">{depois_html}{sinistro}</div>' if depois_html and sinistro
            else depois_html + sinistro)

    # ---- 9. perguntas antes de fechar
    faq_l = _perguntas(venda.get("faq")) or _perguntas(pagina_pad.get("faq"))
    faq = "".join(f'<details><summary>{_e(_substituir(f["p"], corretora=nome_anf, validade=validade))}'
                  f'{PH.ICO["chev"]}</summary><p>{_e(AP.nbsp(_substituir(f["r"], corretora=nome_anf, validade=validade)))}'
                  f'</p></details>' for f in faq_l)
    faq_html = (f'<section class="s" aria-labelledby="h-faq"><h2 id="h-faq">Perguntas que todo mundo faz antes de fechar</h2>'
                f'<div class="faq">{faq}</div></section>') if faq else ""

    # ---- 10. o fecho e a barra fixa
    def sub_de(o: dict) -> str:
        # a PARCELA primeiro: no celular a linha corta no fim (reticências) e o preço nunca pode sumir
        return ", ".join(x for x in (parcela_em_texto(o), str(o.get("seguradora") or "").strip()) if x)

    def aria_de(o: dict) -> str:
        return (f"Quero fechar: {rotulo(o)}, {o.get('seguradora') or ''}, {parcela_em_texto(o)}"
                + ((f", no WhatsApp {com_quem}" if com_quem else ", no WhatsApp") if digitos else ""))

    valido = f"Preços válidos até {validade}." if validade else ""
    dock = ""
    fim = ""
    if rec is not None and digitos:
        duvida = f"{ola} Tenho uma dúvida sobre a cotação do seguro{(' ' + sobre_o_bem) if sobre_o_bem else ''}."
        dock = (f'<div class="dock"><div class="dock-in">'
                f'<a class="ask" href="{_e(wa(duvida))}" rel="noopener">Tirar uma dúvida</a>'
                f'<a class="close" id="ab-fechar" href="{_e(href_fechar(rec))}" rel="nofollow" aria-label="{_e(aria_de(rec))}">'
                f'{PH.ICO["wa"]}<span class="t"><b>Quero fechar</b><span id="close-sub">{_e(sub_de(rec))}</span></span></a>'
                f'</div><p class="dock-note">Abre o WhatsApp{(" " + _e(com_quem)) if com_quem else ""}. '
                f'Nada é cobrado agora.</p></div>')
        # D6: a validade já está no cartão da oferta e no rodapé; "Nada é cobrado agora" está na barra, logo abaixo
        fim = (f'<section class="s fim" id="fechar" aria-labelledby="h-fim"><h2 id="h-fim">Pronto para fechar?</h2>'
               f'<p class="sub">Feche a opção “{_e(rotulo(rec))}” aqui ou escolha outra nos cartões acima.</p>'
               f'<a class="close fim-fechar" href="{_e(href_fechar(rec))}" rel="nofollow" aria-label="{_e(aria_de(rec))}">'
               f'{PH.ICO["wa"]}<span class="t"><b>Quero fechar</b><span class="fim-sub">'
               f'{_e(rotulo(rec) + ": " + sub_de(rec))}</span></span></a></section>')
    elif rec is not None:
        # D-131-44 (o mesmo da renovação): sem número nenhum a página publica SEM botão e diz o caminho de verdade
        fim = (f'<section class="s" id="fechar" aria-labelledby="h-fim"><h2 id="h-fim">Pronto para fechar?</h2>'
               f'<p class="semnum">Para fechar ou tirar uma dúvida, responda a mensagem em que recebeu este link.</p>'
               '<p class="nada">Nada é cobrado agora.</p></section>')

    # ---- 11. rodapé legal (o critério da economia mora aqui — D1)
    aviso = AP.aviso_legal(modelo.get("aviso_legal"), susep)
    metodo = ("Como comparamos: só entram lado a lado as ofertas com a mesma cobertura completa; as que cobrem menos "
              "dizem o que deixam de cobrir. A nossa nota, de 0 a 100, pesa preço, franquia e coberturas.")
    if eco:
        metodo += (f" A economia compara o prêmio líquido da sua apólice atual ({AP.brl(eco['hoje'], False)} por ano, "
                   f"lido no documento que você enviou, sem o IOF) com o preço {A_VISTA} da opção “{rotulo(rec)}”.")
    legal = ('<footer class="legal">' + (f'<p class="valid">{_e(valido)}</p>' if valido else "")
             + (f"<p>{_e(aviso)}</p>" if aviso else "") + f"<p>{_e(metodo)}</p></footer>")

    dados: dict = {"opcoes": [{"id": o["id"], "rotulo": o.get("rotulo"), "seguradora": o.get("seguradora"),
                               "sub": sub_de(o), "aria": aria_de(o)} for o in ops]}
    vence = re.match(r"^\d{4}-\d{2}-\d{2}$", str(modelo.get("validade_ate") or ""))
    if vence and digitos:                       # RT-8: preço vencido → "Pedir preço atualizado" (o script troca)
        dia = validade_curta
        pedir = (f"{ola} A cotação do seguro{(' ' + sobre_o_bem) if sobre_o_bem else ''} venceu em {validade}. "
                 "Pode atualizar o preço?")
        dados["vencido"] = {"ate": vence.group(0), "aviso": f"Preço vencido em {dia} — peça uma atualização",
                            "botao": "Pedir preço atualizado", "sub": f"a cotação venceu em {dia}", "url": wa(pedir)}

    exemplo = ('<div class="exemplo" role="note">Exemplo — dados fictícios</div>' if modelo.get("exemplo") is True else "")
    titulo_pagina = f"A cotação do seu seguro · {nome_anf}" if nome_anf else "A cotação do seu seguro"
    lado_html = f'<div class="vlado">{"".join(lado)}</div>' if lado else ""
    # item 12: sem a barra fixa, o fim da página não guarda os 150 px dela
    endpad = '<div class="endpad"></div>' if dock else '<div class="endpad curto"></div>'
    return f"""<!doctype html>
<html lang="pt-BR" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>{_e(titulo_pagina)}</title>
<meta name="description" content="{_e(previa['descricao'])}">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{_e(previa['titulo'])}">
<meta property="og:description" content="{_e(previa['descricao'])}">
{f'<meta property="og:site_name" content="{_e(nome_anf)}">' if nome_anf else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_e(previa['titulo'])}">
<meta name="twitter:description" content="{_e(previa['descricao'])}">
{PH.MARCADOR_DA_PREVIA}
<style>{CSS_DA_PROPOSTA}</style>
<style>{AP.css_do_tema(anf)}
:root{{--n:{max(n, 1)}}}</style>
<style>{CSS_DA_VENDA}</style>
</head>
<body class="venda">
{exemplo}
<header class="wrap vtop">{marca}{cred}</header>
<main>
<div class="wrap vhero">
<div class="vhero-txt"><h1>{h1}</h1>
<p class="lede">{_e(lede)}</p>{lado_html}</div>
{oferta}
</div>
{opcoes_html}
<div class="wrap">
{eco_html}
{pq_html}
{host_html}
{duas}
{faq_html}
{fim}
{legal}
{endpad}
</div>
</main>
{dock}
<script type="application/json" id="ab-dados">{PH._json_para_html(dados)}</script>
<script>{PH.SCRIPT_DA_PROPOSTA}</script>
</body>
</html>"""
