"""A página da PROPOSTA — o artefato `proposal` servido pelo `/r/`. SPEC-130-A · U5.

F2a fez o ENCAIXE; a F2b (este corpo) veste o DESENHO APROVADO pelo Founder — a direção
"carteira" v4 (D-130A-11) com os 8 acabamentos medidos da 4ª rodada. O contrato com o resto do
produto NÃO mudou:

```
SCRIPT_DA_PROPOSTA   o ÚNICO script da página, inline, sempre o mesmo texto (ASCII)
HASH_DO_SCRIPT       'sha256-' + base64(sha256(SCRIPT)) — calculado DA CONSTANTE
render_proposta      modelo (CONTRATO §5) -> str (o documento inteiro)
previa_do_modelo     o que a prévia do link diz (og:* e o PNG) — sem dado pessoal
injetar_previa       a única costura feita na hora de servir (og:image é absoluta)
destino_do_fechar    o wa.me do "Quero fechar", montado do MODELO, nunca da query
```

Onde mora cada coisa: as DERIVAÇÕES (juros, arredondamento, etiquetas, régua, tema) em
`proposta_apresentacao.py`; o CSS e a fonte embutida em `proposta_estilo.py`; aqui, o HTML.

Por que o hash vem da constante (G16, D-130A-02)
------------------------------------------------
A CSP do `/r/` libera UM script, pelo hash. Se o hash fosse recalculado do HTML
GUARDADO, qualquer script que chegasse ao `artifact_renders` — um dado mal
escapado, uma linha adulterada — ganharia o próprio hash e a CSP o liberaria. O
hash do código só libera o script que o CÓDIGO escreveu; o resto morre no
navegador.

A página funciona SEM o script (D-130A-02): o carrossel é `scroll-snap` de CSS, as abas são
âncoras, o comparar e as dúvidas são `<details>`, e o "Quero fechar" é um link comum
(`?fechar=<opção>` na própria URL do link) que já vem do servidor com o texto curto. O script só
melhora: pontos da régua, teclado, o "Quero fechar" que acompanha o cartão visível, o realce do
comparar e o imprimir com tudo aberto.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from typing import Any, Optional
from urllib.parse import parse_qs, quote, urlsplit

from . import proposta_apresentacao as AP
from .proposta_estilo import CSS_DA_PROPOSTA

#: O parâmetro de query do "Quero fechar". O `route.ts` lê o MESMO nome.
#: 🔴 Na própria URL do link (`/r/<token>?fechar=<opção>`) e não numa pasta
#: `/r/<token>/fechar`: o HTML guardado não conhece o token (o link nasce DEPOIS
#: do render), e um href relativo `?fechar=…` resolve sobre a URL que o cliente
#: abriu — funciona sem JavaScript e sem costurar o token no HTML.
PARAMETRO_DO_FECHAR = "fechar"

#: Onde a prévia do link entra no `<head>`. Só o `render_proposta` escreve isto;
#: todo texto do modelo passa por `html.escape` (que troca `<`) e o JSON de dados
#: troca `<` por `\u003c` — então o marcador não aparece em nenhum outro lugar.
MARCADOR_DA_PREVIA = "<!--ab:previa-->"

#: As dimensões da imagem da prévia (WhatsApp/Facebook: 1,91:1).
PREVIA_LARGURA, PREVIA_ALTURA = 1200, 630

#: 🔴 O ÚNICO script da página. ASCII puro, sem `</script` dentro, e o MESMO
#: texto a cada render — é ele que vira o hash da CSP. Sem `onclick` inline (a
#: CSP o bloquearia): tudo por `addEventListener`.
SCRIPT_DA_PROPOSTA = """(function () {
  "use strict";
  /* Progressive enhancement only: the server already wrote the whole page. Without this script the
     cards scroll (CSS scroll-snap), the tabs are anchors and "Quero fechar" opens the recommended one. */
  var doc = document.documentElement;
  doc.classList.remove("no-js");
  var $ = function (s) { return document.querySelector(s); };
  var track = $("#track");
  if (!track) { return; }
  var DATA = {};
  try { DATA = JSON.parse(($("#ab-dados") || {}).textContent || "{}"); } catch (e) { DATA = {}; }
  var OPS = (DATA && DATA.opcoes) || [];
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var slots = Array.prototype.slice.call(track.querySelectorAll(".slot"));
  var passes = slots.map(function (s) { return s.querySelector(".pass"); });
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  var ind = $("#tab-ind"), cmp = $("#comparar"), count = $("#count"), prev = $("#prev"), next = $("#next");
  var close = $("#ab-fechar"), sub = $("#close-sub");
  var n = slots.length, active = -1, raf = 0;
  var PAD = parseFloat(getComputedStyle(track).scrollPaddingLeft) || 16;
  if (!n) { return; }

  function isSpread() { var l = slots[n - 1]; return l.offsetLeft + l.offsetWidth <= track.clientWidth + 1; }

  /* cards outside the viewport leave the Tab order */
  function setFocusable(i) {
    var spread = isSpread();
    slots.forEach(function (s, k) {
      s.querySelectorAll("summary, a, button, input").forEach(function (el) {
        if (k === i || spread) { el.removeAttribute("tabindex"); } else { el.setAttribute("tabindex", "-1"); }
      });
      s.classList.toggle("on", k === i && track.classList.contains("spread"));
    });
  }

  function setActive(i) {
    if (i === active) { return; }
    active = i;
    tabs.forEach(function (t, k) {
      t.setAttribute("aria-selected", k === i ? "true" : "false");
      if (k === i) { t.removeAttribute("tabindex"); } else { t.setAttribute("tabindex", "-1"); }
    });
    if (count) { count.textContent = (i + 1) + " de " + n; }
    if (prev) { prev.disabled = i === 0; }
    if (next) { next.disabled = i === n - 1; }
    if (cmp) { cmp.setAttribute("data-on", String(i)); }
    document.querySelectorAll(".regua [data-opt]").forEach(function (d) { d.classList.toggle("on", d.getAttribute("data-opt") === String(i)); });
    document.querySelectorAll(".regua [data-flag]").forEach(function (f) { f.classList.toggle("on", f.getAttribute("data-flag") === String(i)); });
    var o = OPS[i];
    if (o && close && o.id) {
      close.setAttribute("href", "?fechar=" + encodeURIComponent(o.id));
      if (o.aria) { close.setAttribute("aria-label", o.aria); }
      if (sub && o.sub) {
        sub.textContent = o.sub;
        sub.classList.remove("swap"); void sub.offsetWidth; sub.classList.add("swap");
      }
    }
    setFocusable(i);
  }

  function measure() {
    raf = 0;
    var spread = isSpread();
    track.classList.toggle("spread", spread);
    if (spread) {
      passes.forEach(function (p) { p.style.removeProperty("--d"); p.style.removeProperty("--ad"); });
      if (active < 0) { setActive(0); } else { setFocusable(active); }
      if (ind) { ind.style.setProperty("--pos", active); }
      return;
    }
    /* the focused card rests on the 16px margin (snap start; the last one snaps at the end) */
    var tr = track.getBoundingClientRect(), ref = tr.left + PAD, best = 0, bd = 1e9;
    var atEnd = track.scrollLeft >= track.scrollWidth - track.clientWidth - 2;
    slots.forEach(function (s, i) {
      var b = s.getBoundingClientRect(), d = (b.left - ref) / (b.width || 1);
      if (atEnd && i === n - 1) { d = 0; }
      var c = Math.max(-1.2, Math.min(1.2, d));
      if (!REDUCED && passes[i]) { passes[i].style.setProperty("--d", c.toFixed(3)); passes[i].style.setProperty("--ad", Math.abs(c).toFixed(3)); }
      if (Math.abs(d) < bd) { bd = Math.abs(d); best = i; }
    });
    var max = track.scrollWidth - track.clientWidth;
    if (ind) { ind.style.setProperty("--pos", max > 0 ? (track.scrollLeft / max * (n - 1)).toFixed(3) : 0); }
    setActive(best);
  }
  function queue() { if (!raf) { raf = window.requestAnimationFrame(measure); } }
  track.addEventListener("scroll", queue, { passive: true });
  window.addEventListener("resize", queue);

  function go(i) {
    i = Math.max(0, Math.min(n - 1, i));
    if (isSpread()) { setActive(i); measure(); return; }
    var s = slots[i];
    var left = i === n - 1 ? track.scrollWidth : s.offsetLeft - PAD;
    track.scrollTo({ left: left, behavior: REDUCED ? "auto" : "smooth" });
  }
  tabs.forEach(function (t, k) {
    t.addEventListener("click", function (ev) { ev.preventDefault(); go(k); });
    t.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        ev.preventDefault();
        var j = (k + (ev.key === "ArrowRight" ? 1 : -1) + n) % n;
        tabs[j].focus(); go(j);
      }
    });
  });
  if (prev) { prev.addEventListener("click", function () { go(active - 1); }); }
  if (next) { next.addEventListener("click", function () { go(active + 1); }); }
  track.addEventListener("keydown", function (ev) {
    var m = { ArrowRight: active + 1, ArrowLeft: active - 1, Home: 0, End: n - 1 };
    if (ev.key in m && ev.target === track) { ev.preventDefault(); go(m[ev.key]); }
  });
  slots.forEach(function (s, i) {
    s.addEventListener("click", function (ev) {
      if (i !== active && !ev.target.closest("a,summary,button,input")) { ev.preventDefault(); go(i); }
    });
  });

  /* drag with the mouse (fingers already scroll natively) */
  var down = null;
  track.addEventListener("pointerdown", function (ev) {
    if (ev.pointerType !== "mouse" || ev.target.closest("a,button,summary,input") || isSpread()) { return; }
    down = { x: ev.clientX, l: track.scrollLeft, from: active };
    track.style.scrollSnapType = "none";
  });
  window.addEventListener("pointermove", function (ev) { if (down) { track.scrollLeft = down.l - (ev.clientX - down.x); } });
  window.addEventListener("pointerup", function (ev) {
    if (!down) { return; }
    var dx = ev.clientX - down.x, from = down.from;
    down = null; track.style.scrollSnapType = "";
    go(Math.abs(dx) > 50 ? from + (dx < 0 ? 1 : -1) : from);
  });

  /* printing: every closed <details> opens, and closes again afterwards */
  var opened = [];
  window.addEventListener("beforeprint", function () {
    opened = Array.prototype.slice.call(document.querySelectorAll("details:not([open])"));
    opened.forEach(function (d) { d.open = true; });
  });
  window.addEventListener("afterprint", function () {
    opened.forEach(function (d) { d.open = false; });
    opened = [];
  });

  measure();
})();"""


def _hash_csp(texto: str) -> str:
    """`'sha256-<base64>'` sem as aspas — o formato que a CSP pede (MDN script-src)."""
    return "sha256-" + base64.b64encode(hashlib.sha256(texto.encode("utf-8")).digest()).decode("ascii")


#: 🔴 Calculado da CONSTANTE, no import. Nunca do HTML guardado (G16).
HASH_DO_SCRIPT = _hash_csp(SCRIPT_DA_PROPOSTA)


# =====================================================================================================================
# formatação
# =====================================================================================================================
def _brl(valor: Any) -> str:
    """`R$ 4.784,27` com espaço COMUM (para og:*, aria, mensagem). Não-número → ""."""
    return AP.brl(valor).replace(AP.NB, " ")


def _data_curta(iso: Any) -> str:
    """`2026-10-13` → `13/10`. Fora do formato → ""."""
    return AP.data_curta(iso)


def _e(texto: Any) -> str:
    return html.escape("" if texto is None else str(texto), quote=True)


def _json_para_html(dados: Any) -> str:
    """JSON dentro de `<script type="application/json">` sem fechar a tag.

    🔴 `</script>` num nome de seguradora fecharia o bloco e o resto viraria HTML
    executável. Trocar `<`, `>` e `&` pelos escapes `\\u` mantém o JSON idêntico
    para o `JSON.parse` e impossível de fechar a tag; U+2028/2029 também.
    """
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    return (texto.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


# =====================================================================================================================
# o modelo → o que a página e a prévia leem
# =====================================================================================================================
def _opcoes(modelo: dict) -> list[dict]:
    """As opções com `id` utilizável (texto curto, sem espaço). Sem id não há como fechar."""
    saida = []
    for o in (modelo or {}).get("opcoes") or []:
        if isinstance(o, dict) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(o.get("id") or "")):
            saida.append(o)
    return saida


def opcao_recomendada(modelo: dict) -> Optional[dict]:
    """A `recomendada` se houver; senão a primeira. Nenhuma → None."""
    ops = _opcoes(modelo)
    for o in ops:
        if o.get("id") == "recomendada":
            return o
    return ops[0] if ops else None


def _ordenadas(modelo: dict) -> list[dict]:
    """A recomendada PRIMEIRO (é o passe na cor da marca), depois as outras na ordem do modelo. Até 3."""
    ops = _opcoes(modelo)
    rec = opcao_recomendada(modelo)
    if rec is None:
        return []
    return ([rec] + [o for o in ops if o is not rec])[:3]


def _comparaveis(modelo: dict) -> Optional[int]:
    resumo = (modelo or {}).get("resumo") or {}
    n = AP.numero_inteiro(resumo.get("com_preco_comparavel"))
    if n is None or n < 1:
        rk = _ranking(modelo)
        n = len(rk) or None
    return n


def _ranking(modelo: dict) -> list[dict]:
    out = []
    for x in (modelo or {}).get("ranking") or []:
        if isinstance(x, dict) and str(x.get("seguradora") or "").strip() and AP.dec(x.get("premio_anual")) is not None:
            out.append(x)
    return out


def _anfitria(modelo: dict) -> dict:
    a = (modelo or {}).get("anfitria")
    return a if isinstance(a, dict) else {}


_LOGO_OK = re.compile(r"^data:image/(png|jpeg|webp|gif|svg\+xml);base64,[A-Za-z0-9+/=]+$")


def _logo(anfitria: dict) -> Optional[str]:
    """O logo embutido, só se a marca é CADASTRADA e o dado é mesmo uma imagem `data:` em base64."""
    url = str(anfitria.get("logo_data_url") or "")
    if anfitria.get("marca_cadastrada") is True and _LOGO_OK.match(url):
        return url
    return None


def previa_do_modelo(modelo: dict) -> dict:
    """O que a prévia do link diz — og:title/og:description e o PNG. D-MC-74.

    🔴 SÓ estes campos, e nenhum é pessoal: a opção recomendada (rótulo, seguradora,
    preço, franquia), quantas seguradoras/corretoras foram comparadas, a marca da
    anfitriã, a origem e a validade. O primeiro nome, o veículo, CPF e placa ficam
    FORA — a prévia aparece na conversa para qualquer um que olhe a tela, e é copiada
    por quem encaminha a mensagem.
    """
    modelo = modelo or {}
    rec = opcao_recomendada(modelo) or {}
    resumo = modelo.get("resumo") or {}
    anfitria = _anfitria(modelo)

    seguradora = str(rec.get("seguradora") or "").strip()
    preco = _brl(rec.get("premio_anual"))
    comparadas = AP.numero_inteiro(resumo.get("com_preco_comparavel"))
    if comparadas is None:
        comparadas = AP.numero_inteiro(resumo.get("seguradoras_cotadas"))
    if comparadas is not None and comparadas < 1:
        comparadas = None
    corretoras = AP.numero_inteiro(resumo.get("corretoras_comparadas"))
    if corretoras is not None and corretoras < 2:
        corretoras = None
    marca = str(anfitria.get("nome") or "").strip()
    validade = _data_curta(modelo.get("validade_ate"))
    fq = rec.get("franquia") if isinstance(rec.get("franquia"), dict) else {}
    e_auto = AP.o_bem(modelo)["e_veiculo"]

    if seguradora and preco:
        titulo = f"Sua proposta de seguro: {seguradora} por {preco} ao ano"
    else:
        titulo = "Sua proposta de seguro"
    partes = []
    if comparadas:
        s = "s" if comparadas > 1 else ""
        partes.append(f"{comparadas} seguradora{s} comparada{s}"
                      + (f" por {corretoras} corretoras." if corretoras else ", igual com igual."))
    if marca:
        partes.append(f"Preparada por {marca}.")
    if validade:
        partes.append(f"Válida até {validade}.")
    return {
        "titulo": titulo,
        "descricao": " ".join(partes) or "As opções que separei para você.",
        "manchete": f"Sua proposta de seguro{' auto' if e_auto else ''} está pronta",
        "seguradora": seguradora,
        "rotulo": str(rec.get("rotulo") or "").strip(),
        "preco": preco,
        "franquia_tipo": str(fq.get("tipo") or "").strip(),
        "franquia": _brl(fq.get("valor")),
        "comparadas": comparadas,
        "corretoras": corretoras,
        "canal": AP.nome_do_canal(modelo) if modelo.get("origem") == "canal" else "",
        "marca": marca,
        "logo": _logo(anfitria),
        "validade": validade,
    }


# =====================================================================================================================
# ícones (SVG inline, decorativos)
# =====================================================================================================================
def _P(d: str) -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true" focusable="false">{d}</svg>')


ICO = {
    "casco": _P('<path d="M12 3.2l7 2.8v5.1c0 4.4-2.9 7.9-7 9.7-4.1-1.8-7-5.3-7-9.7V6z"/><path d="M8.8 12.1l2.2 2.2 4.3-4.4"/>'),
    "terceiros": _P('<path d="M2.8 15.5l1.4-4.2c.3-.8 1-1.3 1.8-1.3h5.2c.8 0 1.5.5 1.8 1.3l1.4 4.2v2.3H2.8z"/><circle cx="5.6" cy="17.8" r=".9"/><circle cx="11.6" cy="17.8" r=".9"/><path d="M14.6 9.6l.6-1.8c.3-.8 1-1.3 1.8-1.3h2.2c.8 0 1.5.5 1.8 1.3l1.2 3.6v2.6h-4.6"/>'),
    "vidros": _P('<path d="M3.5 17.5l2.1-8.6C5.9 7.8 7 7 8.2 7h7.6c1.2 0 2.3.8 2.6 1.9l2.1 8.6z"/><path d="M10.2 9.8l-2.4 4.6M14.4 9.8l-1.4 2.6"/>'),
    "reserva": _P('<circle cx="8" cy="15.5" r="3.8"/><path d="M10.8 12.8L19.5 4M15.8 7.7l2.2 2.2M13.6 9.9l1.8 1.8"/>'),
    "assistencia": _P('<path d="M3 16.5V9.8L6 6h6.5v10.5"/><path d="M12.5 10.5h4l3.5 3.2v2.8h-2"/><circle cx="7" cy="17" r="1.8"/><circle cx="16.2" cy="17" r="1.8"/><path d="M3 12.5h9.5"/>'),
    "app": _P('<circle cx="12" cy="5.8" r="2.4"/><path d="M7 20.5v-4.8a5 5 0 0110 0v4.8"/><path d="M8.6 11.8l7.4 8.2"/>'),
    "morais": _P('<path d="M12 20s-7.2-4.4-7.2-10A4.1 4.1 0 0112 7.4 4.1 4.1 0 0119.2 10c0 5.6-7.2 10-7.2 10z"/>'),
    "check": _P('<path d="M5 12.5l4.2 4.2L19 7"/>'),
    "star": ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path d="M12 2.8l2.8 6 6.5.7-4.9 '
             '4.4 1.4 6.4L12 17l-5.8 3.3 1.4-6.4-4.9-4.4 6.5-.7z"/></svg>'),
    "wa": _P('<path d="M4.2 19.8l1.1-3.6A8 8 0 1112 20a8 8 0 01-3.9-1z"/><path d="M9.2 8.6c.2-.4.5-.5.8-.5h.5c.2 0 .4.1.5.4l.7 1.6c.1.2 0 .5-.1.6l-.5.6c.6 1.2 1.5 2 2.6 2.6l.6-.6c.2-.2.4-.2.6-.1l1.6.7c.3.1.4.3.4.5v.5c0 .3-.2.6-.5.8-.6.4-1.4.6-2.3.3-2.5-.8-4.4-2.7-5.2-5.2-.2-.7 0-1.5.3-2.2z"/>'),
    "left": _P('<path d="M15 5l-7 7 7 7"/>'),
    "right": _P('<path d="M9 5l7 7-7 7"/>'),
    "chev": _P('<path d="M6 9l6 6 6-6"/>'),
    "globe": _P('<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.6 2.8 2.6 14.2 0 17M12 3.5c-2.6 2.8-2.6 14.2 0 17"/>'),
    "scale": _P('<path d="M12 4v16M6 20h12M5 8h14"/><path d="M5 8l-2.5 6a3 3 0 005 0zM19 8l-2.5 6a3 3 0 005 0z"/>'),
    "cols": _P('<rect x="3.5" y="4.5" width="5" height="15" rx="1.5"/><rect x="9.5" y="4.5" width="5" height="15" rx="1.5"/><rect x="15.5" y="4.5" width="5" height="15" rx="1.5"/>'),
}
_SI = {
    "up": ('<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.3l2.3 2.3L9.5 3.6" fill="none" stroke="currentColor" '
           'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'),
    "down": ('<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 2.5v4.6M6 9.4v.1" fill="none" stroke="currentColor" '
             'stroke-width="1.9" stroke-linecap="round"/></svg>'),
}


def _pill(cls: str, txt: str) -> str:
    return f'<span class="selo {cls}">{_SI.get(cls, "")}{_e(txt)}</span>'


def _selo(kind: Optional[str]) -> str:
    return _pill("up" if kind == "melhor" else "down", kind) if kind else ""


# =====================================================================================================================
# peças da página
# =====================================================================================================================
def _preco_html(v: Any) -> str:
    s = AP.brl(v).replace("R$" + AP.NB, "")
    inteiro, _, cent = s.partition(",")
    return (f'<span class="cur">R$</span><span class="int">{_e(inteiro)}</span><span class="dec">,{_e(cent)}</span>'
            f'<span class="per">por ano</span>')


def _cabeca_parcelas(o: dict) -> str:
    pc = AP.parcelas(o)
    sj, cj = pc["sem_juros"], pc["com_juros"]
    if sj and cj:
        return (f"ou <strong>{sj[0]}x de {AP.brl(sj[1])}</strong> sem juros"
                f"<span class=tot>ou {cj[0]}x de {AP.brl(cj[1])} com juros · total {AP.brl(cj[2], False)}</span>")
    if sj:
        return f"ou <strong>{sj[0]}x de {AP.brl(sj[1])}</strong> sem juros"
    if cj:
        return f"ou <strong>{cj[0]}x de {AP.brl(cj[1])}</strong> com juros<span class=tot>total {AP.brl(cj[2], False)}</span>"
    return ""


def _celula_cobertura(k: str, o: dict, rec: dict, tag: str) -> str:
    c = AP.cobertura(o, k)
    if c is None:
        return '<div class="sec cov" aria-hidden="true"></div>' if tag == "div" else ""
    kind, nota = AP.comparar_cobertura(k, o, rec)
    extra = f'<span class="cx">{_e(AP.nbsp(nota))}</span>' if nota else ""
    corpo = (f'<span class="ci">{ICO.get(k, ICO["check"])}</span><span class="cn">{_e(AP.nbsp(c["nome"]))}{_selo(kind)}</span>'
             f'<span class="cv">{_e(AP.nbsp(AP.valor_da_cobertura(c)))}{extra}</span>')
    return f'<div class="sec cov">{corpo}</div>' if tag == "div" else f"<li>{corpo}</li>"


def _passe(o: dict, i: int, ops: list[dict], modelo: dict, topo: list[str], resto: list[str],
           resto_iguais: bool, href_fechar: str) -> str:
    rec, n, v = ops[0], len(ops), i + 1
    V = AP.voz(modelo)
    nc = _comparaveis(modelo)
    bem = AP.o_bem(modelo)
    rotulo = str(o.get("rotulo") or o.get("id"))

    if i == 0:
        motivos = [m for m in o.get("motivos") or [] if isinstance(m, str) and m.strip()]
        blk = (f'<h3>{_e(V["porque"])}</h3><ul class="why">'
               + "".join(f'<li>{ICO["check"]}<span>{_e(AP.nbsp(x))}</span></li>' for x in motivos) + "</ul>") if motivos else ""
    elif isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip():
        fora = f" Por isso fica fora da lista das {nc} com cobertura completa." if nc else ""
        blk = (f'<h3>Por que é mais barata</h3><p class="expl">{_e(AP.nbsp(o["por_que_mais_barata"].strip()))}{_e(fora)}</p>')
    else:
        muda = [x for x in o.get("o_que_muda") or [] if isinstance(x, str) and x.strip()]
        fala_franquia = any("franquia" in x.lower() for x in muda)
        itens = muda + [m for m in o.get("motivos") or [] if isinstance(m, str) and m.strip()
                        and not (fala_franquia and "franquia" in m.lower())]
        blk = ('<h3>O que muda em relação à recomendada</h3><ul class="diffs">'
               + "".join(f"<li>{_e(AP.nbsp(x))}</li>" for x in itens) + "</ul>") if itens else ""

    mais = ""
    lis = "".join(_celula_cobertura(k, o, rec, "li") for k in resto)
    if lis:
        n_resto = sum(1 for k in resto if AP.cobertura(o, k))
        mais = (f'<details class="more"><summary><span>Mais {n_resto} cobertura{"s" if n_resto > 1 else ""}'
                + (", iguais nas três" if resto_iguais and n == 3 else ", iguais nas opções" if resto_iguais else "")
                + f'</span>{ICO["chev"]}</summary><ul class="covs">{lis}</ul></details>')

    nota = AP.numero_inteiro(o.get("nota"))
    campo = (f'<span class="field"><span class="fl">{_e(V["nota"])}</span><span class="fv">{nota}<small>/100</small></span></span>'
             if nota is not None and 0 <= nota <= 100 else "")
    if i == 0 and n > 1:
        # a aba já diz "Recomendada" (< 1024 px): o selo diz OUTRA coisa, curta (cabe em 1 linha)
        alt = f"A melhor das {nc}" if modelo.get("origem") == "canal" and nc and nc > 1 else V["escolha"]
        badge = f'<span class="badge"><span class="b-alt">{_e(alt)}</span><span class="b-rot">{_e(rotulo)}</span></span>'
    else:
        badge = f'<span class="badge">{_e(rotulo)}</span>'
    produto = AP.sem_seguradora(o.get("produto"), o.get("seguradora"))
    preco = AP.brl(o.get("premio_anual"))
    validade = _data_curta(modelo.get("validade_ate"))
    fq = o.get("franquia") if isinstance(o.get("franquia"), dict) else {}
    fq_valor = AP.brl(fq.get("valor"))
    if fq_valor:
        tipo = str(fq.get("tipo") or "").strip().lower()
        dica = (f"Sua parte no conserto se o {bem['rotulo'] or 'carro'} bater." if bem["e_veiculo"]
                else "Sua parte no prejuízo, se precisar acionar o seguro.")
        franquia = (f'<div class="sec fq"><span class="lbl">Franquia{" " + _e(tipo) if tipo else ""}</span>'
                    f'<span class="val">{_e(fq_valor)}</span><span class="hint">{_e(dica)}</span></div>')
    else:
        franquia = '<div class="sec fq"></div>'
    aria = f"Opção {v} de {n}: {rotulo}, {o.get('seguradora') or ''}" + (f", {_brl(o.get('premio_anual'))} por ano" if preco else "")
    want = (f'<a class="want" href="{_e(href_fechar)}" rel="nofollow">{ICO["wa"]}Quero esta</a>' if href_fechar else "")
    return f'''<div class="slot" id="opt-{i}" data-i="{i}" role="tabpanel" aria-labelledby="tab-{i}">
<article class="pass" data-v="{v}" aria-label="{_e(aria)}">
<i class="notch l" aria-hidden="true"></i><i class="notch r" aria-hidden="true"></i>
<div class="pass-head">
<div class="ph-row">{badge}{campo}</div>
<p class="insurer">{_e(o.get("seguradora") or "")}{f' <span class="product">{_e(produto)}</span>' if produto else ""}</p>
{f'<p class="price">{_preco_html(o.get("premio_anual"))}</p>' if preco else ""}
{f'<p class="inst">{_cabeca_parcelas(o)}</p>' if _cabeca_parcelas(o) else ""}
{f'<p class="valid">Preço válido até {_e(validade)}</p>' if validade else ""}
</div>
{franquia}
<div class="sec blk">{blk}</div>
{"".join(_celula_cobertura(k, o, rec, "div") for k in topo)}
<div class="sec morewrap">{mais}</div>
<div class="sec foot">{want}</div>
</article></div>'''


def _mesma(o: dict, x: dict) -> bool:
    a, b = AP.dec(o.get("premio_anual")), AP.dec(x.get("premio_anual"))
    return (str(o.get("seguradora") or "").strip() == str(x.get("seguradora") or "").strip()
            and a is not None and b is not None and abs(a - b) < 1)


def _regua(modelo: dict, ops: list[dict]) -> str:
    rk = _ranking(modelo)
    nrk = len(rk)
    if nrk < 2:
        return ""
    econ = next((o for o in ops[1:] if isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip()
                 and AP.dec(o.get("premio_anual")) is not None and not any(_mesma(o, x) for x in rk)), None)
    eixo = AP.eixo_da_regua([x["premio_anual"] for x in rk] + ([econ["premio_anual"]] if econ else []))
    if eixo is None:
        return ""
    lo, hi = eixo["lo"], eixo["hi"]

    def pos(v: Any) -> float:
        return float((AP.dec(v) - lo) / (hi - lo) * 100)

    def opcao_de(x: dict) -> Optional[int]:
        return next((j for j, o in enumerate(ops) if _mesma(o, x)), None)

    colocados: list[tuple[float, int, Optional[int]]] = []
    pontos = []
    for x in sorted(rk, key=lambda x: opcao_de(x) is None):
        p, j, linha = pos(x["premio_anual"]), opcao_de(x), 0
        if j is None:
            while any(abs(p - q) < (4.4 if qj is not None else 3.0) and qr == linha for q, qr, qj in colocados):
                linha += 1
            if linha == 0 and any(abs(p - q) < 4.4 and qj is not None for q, qr, qj in colocados):
                linha = 1
        colocados.append((p, linha, j))
        cls = ("dot mine" + (" on" if j == 0 else "")) if j is not None else "dot"
        pontos.append(f'<span class="{cls}" style="left:{p:.2f}%;--r:{linha}"'
                      + (f' data-opt="{j}"' if j is not None else "") + "></span>")
    j_econ = ops.index(econ) if econ else None
    if econ:
        pontos.append(f'<span class="dot econ" style="left:{pos(econ["premio_anual"]):.2f}%" data-opt="{j_econ}"></span>')
    flags = ""
    for j, o in enumerate(ops):
        if not any(opcao_de(x) == j for x in rk) and o is not econ:
            continue
        p = pos(o["premio_anual"])
        lado = "l" if p < 18 else ("r" if p > 82 else "c")
        flags += (f'<span class="flag {lado}{" on" if j == 0 else ""}" data-flag="{j}" style="left:{p:.2f}%">'
                  f'{_e(o.get("seguradora") or "")} {_e(AP.brl(o["premio_anual"], False))}</span>')

    def ticks(lista: list[int], cls: str) -> str:
        out = []
        for k, t in enumerate(lista):
            extra = " first" if k == 0 else (" last" if k == len(lista) - 1 else "")
            out.append(f'<span class="tick{extra}" style="left:{(t - lo) / (hi - lo) * 100:.2f}%">{_e(AP.rotulo_do_tick(t))}</span>')
        return f'<span class="ticks {cls}" aria-hidden="true">{"".join(out)}</span>'

    legenda = ('<span><i class="lg on-l"></i>a que você está vendo</span><span><i class="lg mine-l"></i>as outras opções</span>'
               '<span><i class="lg dot-l"></i>as demais seguradoras com cobertura completa</span>'
               + ('<span><i class="lg econ-l"></i>Mais em conta (franquia normal, fora da lista)</span>' if econ else ""))
    mais_barato, mais_caro = min(rk, key=lambda x: AP.dec(x["premio_anual"])), max(rk, key=lambda x: AP.dec(x["premio_anual"]))
    aria = (f"Preço por ano das {nrk} seguradoras com cobertura completa, de {_brl(mais_barato['premio_anual'])} "
            f"a {_brl(mais_caro['premio_anual'])}."
            + (f" A {econ.get('rotulo') or 'opção mais em conta'}, com franquia normal, custa {_brl(econ['premio_anual'])}"
               " e fica fora dessa lista." if econ else ""))
    return (f'<figure class="regua"><figcaption><b>Onde cada opção cai</b> entre as {nrk} com cobertura completa '
            f'(preço por ano)</figcaption>\n<div class="rail" role="img" aria-label="{_e(aria)}">'
            f'{ticks(eixo["estreito"], "n")}{ticks(eixo["largo"], "w")}<span class="axis"></span>{"".join(pontos)}{flags}</div>\n'
            f'<div class="legend" aria-hidden="true">{legenda}</div></figure>')


def _comparar(ops: list[dict]) -> str:
    if len(ops) < 2:
        return ""
    rec = ops[0]
    linhas = []

    def linha(rotulo: str, celulas: Any, igual: bool = False, icone: str = "") -> None:
        if igual:
            linhas.append(f'<div class="row same"><h4>{icone}{_e(rotulo)}</h4><p class="eq">'
                          f'{"Igual nas três" if len(ops) == 3 else "Igual nas opções"}: <b>{celulas}</b></p></div>')
        else:
            linhas.append(f'<div class="row"><h4>{icone}{_e(rotulo)}</h4><div class="cols">'
                          + "".join(f'<div class="cell">{c}</div>' for c in celulas) + "</div></div>")

    def delta_preco(o: dict) -> str:
        if o is rec:
            return ""
        a, b = AP.dec(o.get("premio_anual")), AP.dec(rec.get("premio_anual"))
        if a is None or b is None:
            return ""
        d = a - b
        if AP.reais(d) >= 1:
            return _pill("down", "pior") + f'<span class="dt">{_e(AP.brl(d, False))} a mais por ano</span>'
        if AP.reais(d) <= -1:
            if isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip():
                return _pill("neutro", "cobre menos") + f'<span class="dt">{_e(AP.brl(-d, False))} a menos por ano</span>'
            return _pill("up", "melhor") + f'<span class="dt">{_e(AP.brl(-d, False))} a menos por ano</span>'
        return ""

    def fq(o: dict) -> tuple[Optional[Any], str]:
        f = o.get("franquia") if isinstance(o.get("franquia"), dict) else {}
        return AP.dec(f.get("valor")), str(f.get("tipo") or "").strip().lower()

    def delta_franquia(o: dict) -> str:
        if o is rec:
            return ""
        (a, _), (b, _) = fq(o), fq(rec)
        if a is None or b is None or b == 0:
            return ""
        d = a - b
        if AP.reais(d) >= 1:
            dobro = " (o dobro)" if abs(a / b - 2) < _TRES_CENTESIMOS else ""
            return _pill("down", "pior") + f'<span class="dt">{_e(AP.brl(d, False))} a mais{dobro}</span>'
        if AP.reais(d) <= -1:
            return _pill("up", "melhor") + f'<span class="dt">{_e(AP.brl(-d, False))} menor</span>'
        return ""

    linha("Preço por ano", [f'<b>{_e(AP.brl(o.get("premio_anual")))}</b>{delta_preco(o)}' for o in ops])

    def parc(o: dict) -> str:
        pc = AP.parcelas(o)
        sj, cj = pc["sem_juros"], pc["com_juros"]
        partes = []
        if sj:
            partes.append(f'{sj[0]}x de {_e(AP.brl(sj[1]))}<span class=sub>sem juros</span>')
        if cj:
            partes.append(f'{"ou " if sj else ""}{cj[0]}x de {_e(AP.brl(cj[1]))}<span class=sub>com juros: total '
                          f'{_e(AP.brl(cj[2], False))} ({_e(AP.brl(cj[3], False))} a mais)</span>')
        return "".join(partes)

    if any(parc(o) for o in ops):
        linha("Parcelas", [parc(o) for o in ops])
    if any(fq(o)[0] is not None for o in ops):
        linha("Franquia", [(f'<b>{_e(AP.brl(fq(o)[0]))}</b><span class="sub">{_e(fq(o)[1])}</span>{delta_franquia(o)}'
                            if fq(o)[0] is not None else "") for o in ops])
    if any(AP.numero_inteiro(o.get("nota")) is not None for o in ops):
        linha("Nota, de 0 a 100", [f'<b>{AP.numero_inteiro(o.get("nota"))}</b>' if AP.numero_inteiro(o.get("nota")) is not None
                                   else "" for o in ops])
    for c in rec.get("coberturas") or []:
        if not isinstance(c, dict) or AP.cobertura(rec, c.get("chave")) is None:
            continue
        k = c["chave"]
        cs = [AP.cobertura(o, k) for o in ops]
        vals = [AP.valor_da_cobertura(x) if x else "" for x in cs]
        if all(cs) and len({AP._chave_txt(v) for v in vals}) == 1:
            linha(AP.nbsp(c["nome"]), _e(AP.nbsp(vals[0])), igual=True, icone=ICO.get(k, ""))
        else:
            celulas = []
            for v, o in zip(vals, ops):
                kind, nota = AP.comparar_cobertura(k, o, rec)
                # o selo FECHA a célula: nunca entre o valor e a nota (laudo critico-g D7)
                celulas.append(_e(AP.nbsp(v)) + (f'<span class="cx">{_e(AP.nbsp(nota))}</span>' if nota else "") + _selo(kind))
            linha(AP.nbsp(c["nome"]), celulas, icone=ICO.get(k, ""))
    cab = "".join(f'<div class="mini" data-v="{i + 1}"><span>{_e(o.get("rotulo") or o.get("id"))}</span>'
                  f'<b>{_e(o.get("seguradora") or "")}</b></div>' for i, o in enumerate(ops))
    return f'''<details class="cmp" id="comparar" data-on="0">
<summary class="compare-btn">{ICO["cols"]}<span>Comparar lado a lado</span>{ICO["chev"]}</summary>
<div class="cmp-in">
<div class="cmp-tools"><label class="only"><input type="checkbox" id="only"><span>Mostrar só o que muda</span></label>
<p class="key">{_pill("up", "melhor")}{_pill("down", "pior")}em relação à recomendada</p></div>
<div class="cmp-grid">
<div class="cmp-head cols">{cab}</div>
{"".join(linhas)}</div>
</div></details>'''


_TRES_CENTESIMOS = AP.Decimal("0.03")


def _faq(modelo: dict, ops: list[dict]) -> str:
    """As dúvidas do modelo. "Dá para reduzir a franquia?" ganha os NÚMEROS desta proposta quando há uma
    opção com franquia menor (o rótulo de verdade, não um nome que talvez não exista no carrossel)."""
    rec = ops[0] if ops else {}
    fr = (rec.get("franquia") or {}).get("valor") if isinstance(rec.get("franquia"), dict) else None
    menor = None
    if AP.dec(fr) is not None:
        menor = next((o for o in ops[1:] if isinstance(o.get("franquia"), dict)
                      and AP.dec(o["franquia"].get("valor")) is not None
                      and AP.reais(AP.dec(fr) - AP.dec(o["franquia"]["valor"])) >= 1), None)
    out = []
    for f in modelo.get("faq") or []:
        if not isinstance(f, dict) or not str(f.get("p") or "").strip() or not str(f.get("r") or "").strip():
            continue
        r = str(f["r"])
        if str(f["p"]).startswith("Dá para reduzir a franquia") and menor and AP.dec(menor.get("premio_anual")) is not None \
                and AP.dec(rec.get("premio_anual")) is not None:
            dp = AP.dec(menor["premio_anual"]) - AP.dec(rec["premio_anual"])
            custo = (f"custa {AP.brl(dp, False)} a mais por ano" if AP.reais(dp) >= 1
                     else f"custa {AP.brl(-dp, False)} a menos por ano" if AP.reais(dp) <= -1 else "custa o mesmo")
            r = (f"Dá. Neste caso, a {menor.get('seguradora') or 'outra opção'} tem franquia "
                 f"{AP.brl(AP.dec(fr) - AP.dec(menor['franquia']['valor']), False)} menor e {custo}. "
                 f"Veja o cartão \u201c{menor.get('rotulo') or menor.get('id')}\u201d.")
        out.append(f'<details><summary>{_e(f["p"])}{ICO["chev"]}</summary><p>{_e(AP.nbsp(r))}</p></details>')
    return "".join(out)


# =====================================================================================================================
# a página
# =====================================================================================================================
def render_proposta(modelo: dict) -> str:
    """O documento inteiro da proposta, a partir do modelo do CONTRATO §5 (D-130A-11, "carteira" v4).

    Um arquivo: CSS inline (com a fonte embutida), o logo em `data:`, os dados num
    `<script type="application/json" id="ab-dados">` e o script inline IDÊNTICO a
    `SCRIPT_DA_PROPOSTA`. Todo texto do modelo é escapado. Campo ausente não aparece.
    """
    modelo = modelo if isinstance(modelo, dict) else {}
    previa = previa_do_modelo(modelo)
    ops = _ordenadas(modelo)
    rec = ops[0] if ops else None
    anf = _anfitria(modelo)
    nome_anf = str(anf.get("nome") or "").strip()
    V = AP.voz(modelo)
    resumo = modelo.get("resumo") if isinstance(modelo.get("resumo"), dict) else {}
    nc = _comparaveis(modelo)
    bem = AP.o_bem(modelo)
    nome = str((modelo.get("cliente") or {}).get("primeiro_nome") or "").strip() if isinstance(modelo.get("cliente"), dict) else ""
    canal = modelo.get("origem") == "canal"
    digitos = _digitos_do_whatsapp(modelo)
    logo = _logo(anf)
    sobre_o_bem = f"do {bem['apelido']}" if bem["apelido"] else "da proposta"

    def wa(texto: str) -> str:
        return f"https://wa.me/{digitos}?text={quote(texto, safe='')}" if digitos else ""

    def href_fechar(o: dict) -> str:
        return f"?{PARAMETRO_DO_FECHAR}={quote(str(o['id']), safe='')}" if digitos else ""

    # ---- topo
    if logo:
        marca = (f'<span class="brand"><span class="plate"><img src="{_e(logo)}" alt="{_e(nome_anf)}" height="30">'
                 f'</span></span>')
    elif nome_anf:
        marca = (f'<span class="brand"><span class="mono" aria-hidden="true">{_e(AP.monograma(nome_anf))}</span>'
                 f'<span class="brand-name">{_e(nome_anf)}</span></span>')
    else:
        marca = '<span class="brand"></span>'
    g = anf.get("google") if isinstance(anf.get("google"), dict) else None
    g_nota = AP.dec(g.get("nota")) if g else None
    g_n = AP.numero_inteiro(g.get("avaliacoes")) if g else None
    if g_nota is None or g_n is None or g_n < 1:
        g = None
    nota_g = f"{g_nota:.1f}".replace(".", ",") if g else ""
    confianca = (f'<span class="trust">{ICO["star"]}<span><strong>{nota_g}</strong> no Google<br>{g_n} avaliações</span></span>'
                 if g else "")
    selo_canal = (f'<p class="sealrow"><span class="seal">{ICO["scale"]}Comparação independente · '
                  f'{_e(AP.nome_do_canal(modelo))}</span></p>' if canal else "")

    # ---- título
    if rec is not None and AP.brl(rec.get("premio_anual")):
        das = f"a melhor das {nc}" if nc and nc > 1 else "a melhor opção"
        para = f" para o seu {_e(bem['apelido'])}" if bem["apelido"] else ""
        frase = f"{das}{para}: {_e(rec.get('seguradora') or '')}, {_e(AP.brl(rec.get('premio_anual'), False))} por ano."
        h1 = (f'<span class="hello">{_e(nome)}, </span>{frase}' if nome else frase[:1].upper() + frase[1:])
    else:
        h1 = "Sua proposta de seguro"
    cotadas = AP.numero_inteiro(resumo.get("seguradoras_cotadas"))
    lede = ", ".join(x for x in (bem["descricao"], bem["ano"]) if x)
    if cotadas:
        em = f"em {cotadas} seguradora{'s' if cotadas > 1 else ''}"
        lede = f"{lede}, cotado {em}" if lede else f"Cotado {em}"
    lede = f"{lede}." if lede else ""

    # ---- carrossel
    topo, resto, resto_iguais = AP.escolher_coberturas(ops) if ops else ([], [], True)
    passes = "".join(_passe(o, i, ops, modelo, topo, resto, resto_iguais, href_fechar(o)) for i, o in enumerate(ops))
    abas = "".join(f'<a class="tab" href="#opt-{i}" role="tab" id="tab-{i}" aria-controls="opt-{i}" '
                   f'aria-selected="{"true" if i == 0 else "false"}"{"" if i == 0 else " tabindex=\"-1\""}>'
                   f'{_e(o.get("rotulo") or o.get("id"))}</a>' for i, o in enumerate(ops))
    n = len(ops)

    # ---- todas as seguradoras
    rk = _ranking(modelo)

    def marca_da_opcao(x: dict) -> str:
        o = next((o for o in ops if _mesma(o, x)), None)
        return str(o.get("rotulo") or o.get("id")) if o else ""

    menor_rk = AP.dec(rk[0]["premio_anual"]) if rk else None
    itens_rk = []
    for i, x in enumerate(rk):
        tag = marca_da_opcao(x)
        fqx = AP.brl(x.get("franquia"), False)
        dif = AP.dec(x["premio_anual"]) - menor_rk
        meta2 = (f"o menor preço das {len(rk)}" if i == 0 else f"{AP.brl(dif, False)} a mais por ano")
        itens_rk.append(f'<li class="{"mine" if tag else ""}"><span class="n">{i + 1}</span><span class="nm">{_e(x["seguradora"])}'
                        f'{f"<span class=tag>{_e(tag)}</span>" if tag else ""}</span><span class="pr">{_e(AP.brl(x["premio_anual"]))}</span>'
                        f'<span class="meta"><span>{f"franquia {_e(fqx)}" if fqx else ""}</span><span>{_e(meta2)}</span></span></li>')
    econ = next((o for o in ops[1:] if isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip()
                 and not any(_mesma(o, x) for x in rk)), None)
    nota_econ = ""
    if econ:
        pq = econ["por_que_mais_barata"].strip()
        nota_econ = (f'<p class="note">A <b>{_e(econ.get("rotulo") or "")}</b> ({_e(econ.get("seguradora") or "")}, '
                     f'{_e(AP.brl(econ.get("premio_anual")))}) não está nesta lista: {_e(AP.nbsp(pq[:1].lower() + pq[1:]))}</p>')
    pdif = [x for x in modelo.get("produto_diferente") or [] if isinstance(x, dict) and str(x.get("seguradora") or "").strip()]
    nr = [x for x in modelo.get("nao_responderam") or [] if isinstance(x, dict) and str(x.get("seguradora") or "").strip()]
    conta = ""
    if cotadas and rk:
        conta = (f"Cotamos em {cotadas} seguradoras: {len(rk)} deram preço com a mesma cobertura completa"
                 + (f" e {len(nr)} não {'deu' if len(nr) == 1 else 'deram'} preço" if nr else "") + "."
                 + (f" Algumas também mandaram {len(pdif)} oferta{'s' if len(pdif) > 1 else ''} que cobre"
                    f"{'m' if len(pdif) > 1 else ''} menos, mostrada{'s' if len(pdif) > 1 else ''} à parte." if pdif else ""))
    pd_html = ""
    if pdif:
        pd_html = (f'<details class="line"><summary><span><b>{len(pdif)} oferta{"s" if len(pdif) > 1 else ""} '
                   f'cobre{"m" if len(pdif) > 1 else ""} menos</b> e por isso fica{"m" if len(pdif) > 1 else ""} fora da lista'
                   f'</span>{ICO["chev"]}</summary><ul>'
                   + "".join(f'<li><b>{_e(x["seguradora"])}'
                             + (f', {_e(AP.sem_seguradora(x.get("produto"), x["seguradora"]))}' if str(x.get("produto") or "").strip() else "")
                             + "</b>" + (f', {_e(AP.brl(x.get("premio_anual")))}' if AP.brl(x.get("premio_anual")) else "")
                             + (f': {_e(x.get("por_que_nao_compara"))}' if str(x.get("por_que_nao_compara") or "").strip() else "")
                             + "</li>" for x in pdif)
                   + "</ul></details>")
    nr_html = ("<p class=\"line-static\"><b>Não deram preço:</b> "
               + "; ".join(_e(x["seguradora"]) + (f' ({_e(x.get("motivo"))})' if str(x.get("motivo") or "").strip() else "")
                           for x in nr) + ".</p>") if nr else ""
    duelo = ""
    ec = [c for c in modelo.get("entre_corretoras") or [] if isinstance(c, dict) and AP.dec(c.get("melhor_completa")) is not None]
    if len(ec) >= 2:
        linhas_duelo = "".join(
            f'<div class="duel-row{" win" if c.get("vencedora") is True else ""}"><span>'
            f'{_e(c.get("corretora") if c.get("vencedora") is True else "Outra corretora parceira")}</span>'
            f'<b>{_e(AP.brl(c["melhor_completa"]))}</b></div>'
            for c in sorted(ec, key=lambda c: c.get("vencedora") is not True))
        quem = f"O {_e(AP.nome_do_canal(modelo))} comparou" if canal else "Comparamos"
        duelo = (f'<div class="duel"><p>{quem} {len(ec)} corretoras pelo melhor preço com cobertura completa:</p>'
                 f'{linhas_duelo}'
                 + (f'<p class="src">A {_e(nome_anf)} teve o menor e é quem vai atender você.</p>' if nome_anf else "")
                 + "</div>")

    # ---- anfitriã
    fatos = []
    if g:
        fatos.append(f'<div class="fact"><b>{ICO["star"]}{nota_g}</b><span>no Google, {g_n} avaliações</span></div>')
    desde = AP.numero_inteiro(anf.get("desde"))
    ano_ref = re.match(r"^(\d{4})", str(modelo.get("gerado_em") or ""))
    if desde and ano_ref and 0 < int(ano_ref.group(1)) - desde < 200:
        fatos.append(f'<div class="fact"><b>{int(ano_ref.group(1)) - desde}{AP.NB}anos</b><span>atendendo, desde {desde}</span></div>')
    susep = str(anf.get("susep") or "").strip()
    if susep:
        fatos.append(f'<div class="fact"><b>{_e(susep)}</b><span>registro na SUSEP</span></div>')
    cidade = str(anf.get("cidade") or "").strip()
    tagline = str(anf.get("tagline") or "").strip()
    ganhou = (f'<p class="sub0">Teve o menor preço com cobertura completa entre as {len(ec)} corretoras comparadas e '
              f'atende você pelo WhatsApp.</p>' if len(ec) >= 2 else "")
    o_que_e = ""
    if canal:
        nm = _e(AP.nome_do_canal(modelo))
        o_que_e = (f'<p class="what"><b>O que é o {nm}?</b>Um comparador independente: cota o seu seguro com corretoras '
                   f'parceiras e indica a que teve o menor preço com a mesma cobertura completa. Quem atende e cuida do '
                   f'seu seguro é a corretora.</p>')
    fonte_g = ""
    if g and str(g.get("fonte") or "").strip():
        fonte_g = f'<p class="src">Nota e avaliações: {_e(AP.aspas_tipograficas(g["fonte"]))}.</p>'
    site = str(anf.get("site") or "").strip()
    site_ok = re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~/-]*)?", site or "") is not None
    canais = ""
    if digitos or site_ok:
        canais = ('<div class="chan">'
                  + (f'<a href="{_e(wa(f"Olá! Aqui é {nome}. Vim pela proposta do seguro {sobre_o_bem}." if nome else f"Olá! Vim pela proposta do seguro {sobre_o_bem}."))}" '
                     f'rel="noopener">{ICO["wa"]}WhatsApp</a>' if digitos else "")
                  + (f'<a href="https://{_e(site)}" rel="noopener">{ICO["globe"]}{_e(site)}</a>' if site_ok else "")
                  + "</div>")
    anfitria_html = ""
    if nome_anf:
        id_visual = (f'<span class="plate"><img src="{_e(logo)}" alt="" height="44"></span>' if logo
                     else f'<span class="mono big" aria-hidden="true">{_e(AP.monograma(nome_anf))}</span>')
        anfitria_html = (f'<section class="s" aria-labelledby="h-host"><h2 id="h-host">Quem vai cuidar do seu seguro</h2>'
                         f'<div class="host"><div class="host-id">{id_visual}<div><h3>{_e(nome_anf)}</h3>'
                         + (f"<p>{_e(cidade)}</p>" if cidade else "") + "</div></div>"
                         + (f'<p class="sub0">{_e(tagline)}</p>' if tagline else "") + ganhou
                         + (f'<div class="facts">{"".join(fatos)}</div>' if fatos else "")
                         + fonte_g + o_que_e + canais + "</div></section>")

    sinistro_l = modelo.get("sinistro") if isinstance(modelo.get("sinistro"), list) else anf.get("sinistro")
    passos = [s for s in (sinistro_l or []) if isinstance(s, str) and s.strip()]
    sinistro = ""
    if passos:
        sinistro = (f'<section class="s" aria-labelledby="h-sin"><h2 id="h-sin">Se acontecer alguma coisa</h2>'
                    + (f'<p class="sub">Quem cuida é a {_e(nome_anf)}, não um 0800.</p>' if nome_anf else "")
                    + f'<ol class="steps">{"".join(f"<li><p>{_e(s)}</p></li>" for s in passos)}</ol></section>')
    faq = _faq(modelo, ops)
    faq_html = (f'<section class="s" aria-labelledby="h-faq"><h2 id="h-faq">Perguntas que todo mundo faz</h2>'
                f'<div class="faq">{faq}</div></section>') if faq else ""

    validade = AP.data_br(modelo.get("validade_ate"))
    aviso = AP.aviso_legal(modelo.get("aviso_legal"), susep)
    metodo = (f"Comparamos só as ofertas com a mesma cobertura completa; as que cobrem menos aparecem à parte. "
              f"{V['nota_longa']} pesa preço, franquia e coberturas.")
    legal = ('<footer class="legal">' + (f'<p class="valid">Preços válidos até {_e(validade)}.</p>' if validade else "")
             + f'<p>{_e((aviso + " " if aviso else "") + metodo)}</p></footer>')

    # ---- rodapé fixo (sem JS já vem com o texto curto do servidor)
    def sub_de(o: dict) -> str:
        return ", ".join(x for x in (str(o.get("seguradora") or "").strip(), AP.brl(o.get("premio_anual"))) if x)

    def aria_de(o: dict) -> str:
        return (f"Quero fechar: {o.get('seguradora') or o.get('rotulo') or ''}"
                + (f", {_brl(o.get('premio_anual'))} por ano" if _brl(o.get("premio_anual")) else "")
                + (f", no WhatsApp da {nome_anf}" if nome_anf else ", no WhatsApp"))

    dock = ""
    if rec is not None and digitos:
        duvida = (f"Olá! Aqui é {nome}. Tenho uma dúvida sobre a proposta do seguro {sobre_o_bem}." if nome
                  else f"Olá! Tenho uma dúvida sobre a proposta do seguro {sobre_o_bem}.")
        dock = (f'<div class="dock"><div class="dock-in">'
                f'<a class="ask" href="{_e(wa(duvida))}" rel="noopener">Tirar uma dúvida</a>'
                f'<a class="close" id="ab-fechar" href="{_e(href_fechar(rec))}" rel="nofollow" aria-label="{_e(aria_de(rec))}">'
                f'{ICO["wa"]}<span class="t"><b>Quero fechar</b><span id="close-sub">{_e(sub_de(rec))}</span></span></a>'
                f'</div><p class="dock-note">Abre a conversa{f" com a {_e(nome_anf)}" if nome_anf else ""} no WhatsApp. '
                f'Nada é cobrado agora.</p></div>')

    dados = {"opcoes": [{"id": o["id"], "rotulo": o.get("rotulo"), "seguradora": o.get("seguradora"),
                         "sub": sub_de(o), "aria": aria_de(o)} for o in ops]}

    titulo_pagina = f"Sua proposta de seguro · {nome_anf}" if nome_anf else "Sua proposta de seguro"
    navrow = ""
    if n > 1:
        navrow = (f'<div class="navrow"><div class="tabs" role="tablist" aria-label="Opções">'
                  f'<span class="tab-ind" id="tab-ind" aria-hidden="true"></span>{abas}</div>'
                  f'<div class="nav js-only"><button type="button" id="prev" aria-label="Opção anterior">{ICO["left"]}</button>'
                  f'<span class="count" id="count" aria-live="polite">1 de {n}</span>'
                  f'<button type="button" id="next" aria-label="Próxima opção">{ICO["right"]}</button></div></div>')
    rows = 5 + len(topo)
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
{MARCADOR_DA_PREVIA}
<style>{CSS_DA_PROPOSTA}</style>
<style>{AP.css_do_tema(anf)}
:root{{--n:{max(n, 1)}}}</style>
</head>
<body>
<header class="wrap top">{marca}{confianca}</header>
<main>
<div class="wrap hero">
{selo_canal}<h1>{h1}</h1>
{f'<p class="lede">{_e(lede)}</p>' if lede else ''}
{navrow}
</div>
<div class="widewrap"><div class="track" id="track" style="--rows:{rows}" tabindex="0" role="region" aria-roledescription="carrossel" aria-label="As {n} opções. Use as setas do teclado para trocar.">
{passes}
</div></div>
<div class="wrap">
{_regua(modelo, ops)}
{_comparar(ops)}
{f'''<section class="s" aria-labelledby="h-all"><h2 id="h-all">Todas as seguradoras que cotamos</h2>
{f'<p class="sub">{_e(conta)}</p>' if conta else ''}
{duelo}
<ol class="rank">{"".join(itens_rk)}</ol>
{nota_econ}
<div class="others">{pd_html}{nr_html}</div>
</section>''' if rk else ''}
{anfitria_html}
{sinistro}
{faq_html}
{legal}
<div class="endpad"></div>
</div>
</main>
{dock}
<script type="application/json" id="ab-dados">{_json_para_html(dados)}</script>
<script>{SCRIPT_DA_PROPOSTA}</script>
</body>
</html>"""


# =====================================================================================================================
# a costura da hora de servir — og:image é ABSOLUTA e depende do link
# =====================================================================================================================
def injetar_previa(documento: str, *, url_da_imagem: str, url_da_pagina: str) -> str:
    """Põe og:image/og:url/twitter:image no lugar do marcador. Só o 1º, só no `<head>`.

    🔴 Por que na hora de servir: a og:image tem de ser ABSOLUTA (o robô do
    WhatsApp não resolve caminho relativo) e contém o TOKEN — que só existe
    depois do render (criar → render → publicar → compartilhar). Um link novo da
    mesma versão ganha a própria imagem sem tocar no render guardado.

    Os bytes do SCRIPT não são tocados: o hash da CSP continua o da constante.
    """
    if not documento or not url_da_imagem:
        return documento
    pos = documento.find(MARCADOR_DA_PREVIA)
    fim_head = documento.find("</head>")
    if pos < 0 or fim_head < 0 or pos > fim_head:
        return documento
    img, pag = _e(url_da_imagem), _e(url_da_pagina)
    metas = (f'<meta property="og:image" content="{img}">\n'
             f'<meta property="og:image:type" content="image/png">\n'
             f'<meta property="og:image:width" content="{PREVIA_LARGURA}">\n'
             f'<meta property="og:image:height" content="{PREVIA_ALTURA}">\n'
             + (f'<meta property="og:url" content="{pag}">\n' if url_da_pagina else "")
             + f'<meta name="twitter:image" content="{img}">')
    return documento[:pos] + metas + documento[pos + len(MARCADOR_DA_PREVIA):]


# =====================================================================================================================
# o "Quero fechar" — destino montado no SERVIDOR, a partir do modelo
# =====================================================================================================================
_TEXTO_MAXIMO = 500


def _digitos_do_whatsapp(modelo: dict) -> Optional[str]:
    """O número da corretora, de `cta.whatsapp_url` (wa.me / api.whatsapp.com) ou de `anfitria.whatsapp`."""
    cta = (modelo or {}).get("cta") or {}
    url = str(cta.get("whatsapp_url") or "").strip() if isinstance(cta, dict) else ""
    candidatos = []
    if url:
        try:
            p = urlsplit(url)
        except ValueError:
            p = None
        if p is not None and p.scheme == "https":
            host = (p.hostname or "").lower()
            if host == "wa.me":
                candidatos.append(p.path.strip("/"))
            elif host == "api.whatsapp.com" and p.path.rstrip("/") == "/send":
                candidatos.append((parse_qs(p.query).get("phone") or [""])[0])
    candidatos.append(re.sub(r"\D", "", str(_anfitria(modelo).get("whatsapp") or "")))
    for c in candidatos:
        if re.fullmatch(r"\d{10,15}", c or ""):
            return c
    return None


def _texto_do_fechar(modelo: dict, o: dict) -> str:
    """A mensagem que o cliente manda ao tocar "Quero fechar" (desenho aprovado): a opção, o preço, as
    parcelas COM o nome dos juros, a franquia e a validade — a corretora já sabe o que fechar."""
    cliente = modelo.get("cliente") if isinstance(modelo.get("cliente"), dict) else {}
    nome = str(cliente.get("primeiro_nome") or "").strip()
    bem = AP.o_bem(modelo)
    rotulo = str(o.get("rotulo") or o.get("id"))
    seg = str(o.get("seguradora") or "").strip()
    produto = AP.sem_seguradora(o.get("produto"), seg)
    partes = ["Olá!"]
    if nome:
        partes.append(f"Aqui é {nome}.")
    do_bem = f" do {bem['apelido']}" if bem["apelido"] else ""
    frase = f'Quero fechar o seguro{do_bem} na opção "{rotulo}"'
    oferta = " ".join(x for x in (seg, produto) if x)
    detalhes = []
    if _brl(o.get("premio_anual")):
        detalhes.append(f"{_brl(o.get('premio_anual'))} por ano")
    parc = AP.parcelas_em_texto(o)
    if parc:
        detalhes[-1:] = [(detalhes[-1] + f" ({parc})") if detalhes else parc]
    fq = o.get("franquia") if isinstance(o.get("franquia"), dict) else {}
    if _brl(fq.get("valor")):
        detalhes.append(f"franquia de {_brl(fq.get('valor'))}")
    frase += (f": {oferta}" if oferta else "") + (", " + ", ".join(detalhes) if detalhes else "") + "."
    partes.append(frase)
    validade = AP.data_br(modelo.get("validade_ate"))
    if validade:
        partes.append(f"A proposta vale até {validade}.")
    return " ".join(partes)


def destino_do_fechar(modelo: dict, opcao: Any) -> Optional[dict]:
    """`{destino, opcao, rotulo, seguradora}` para uma opção QUE EXISTE no modelo; senão None.

    🔴 Nunca um redirecionamento aberto: a função não recebe URL nenhuma. O
    destino é SEMPRE `https://wa.me/<dígitos da corretora>?text=<texto>`, com os
    dígitos e o texto tirados do MODELO guardado. A query só escolhe ENTRE as
    opções que o servidor já conhece. O texto: `cta.texto_por_opcao` quando o
    modelo traz; senão o do desenho aprovado (`_texto_do_fechar`).
    """
    if not isinstance(opcao, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", opcao):
        return None
    escolhida = next((o for o in _opcoes(modelo) if o.get("id") == opcao), None)
    if escolhida is None:
        return None
    digitos = _digitos_do_whatsapp(modelo)
    if not digitos:
        return None
    cta = (modelo or {}).get("cta") or {}
    textos = cta.get("texto_por_opcao") if isinstance(cta, dict) else None
    texto = textos.get(opcao) if isinstance(textos, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        texto = _texto_do_fechar(modelo or {}, escolhida)
    texto = texto.strip()[:_TEXTO_MAXIMO]
    return {
        "destino": f"https://wa.me/{digitos}?text={quote(texto, safe='')}",
        "opcao": opcao,
        "rotulo": escolhida.get("rotulo"),
        "seguradora": escolhida.get("seguradora"),
    }
