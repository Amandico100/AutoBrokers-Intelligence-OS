"""A página da PROPOSTA — o artefato `proposal` servido pelo `/r/`. SPEC-130-A · U5 (F2a: a INFRA).

🔴 O que esta fatia entrega é o ENCAIXE, não o desenho. O corpo do HTML/CSS e o
texto do script são PROVISÓRIOS: a F2b troca os dois pelo desenho que o Founder
aprovar (D0). O que NÃO muda na F2b, e é o contrato com o resto do produto:

```
SCRIPT_DA_PROPOSTA   o ÚNICO script da página, inline, sempre o mesmo texto
HASH_DO_SCRIPT       'sha256-' + base64(sha256(SCRIPT)) — calculado DA CONSTANTE
render_proposta      modelo (CONTRATO §5) -> str (o documento inteiro)
previa_do_modelo     o que a prévia do link diz (og:* e o PNG) — sem dado pessoal
injetar_previa       a única costura feita na hora de servir (og:image é absoluta)
destino_do_fechar    o wa.me do "Quero fechar", montado do MODELO, nunca da query
```

Por que o hash vem da constante (G16, D-130A-02)
------------------------------------------------
A CSP do `/r/` libera UM script, pelo hash. Se o hash fosse recalculado do HTML
GUARDADO, qualquer script que chegasse ao `artifact_renders` — um dado mal
escapado, uma linha adulterada — ganharia o próprio hash e a CSP o liberaria. O
hash do código só libera o script que o CÓDIGO escreveu; o resto morre no
navegador.

A página funciona SEM o script (D-130A-02): o "Quero fechar" é um link comum
(`?fechar=<opção>` na própria URL do link) e a escolha da opção só MELHORA com JS.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from typing import Any, Optional
from urllib.parse import parse_qs, quote, urlsplit

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
#: texto a cada render — é ele que vira o hash da CSP. PROVISÓRIO (F2b troca o
#: texto; o mecanismo fica). Ele só melhora: marca a opção escolhida e faz o
#: "Quero fechar" acompanhá-la. Sem `onclick` inline (a CSP o bloquearia).
SCRIPT_DA_PROPOSTA = """(function () {
  "use strict";
  var fonte = document.getElementById("ab-dados");
  if (!fonte) { return; }
  var dados;
  try { dados = JSON.parse(fonte.textContent || "{}"); } catch (e) { return; }
  var opcoes = (dados && dados.opcoes) || [];
  var fechar = document.getElementById("ab-fechar");
  function existe(id) {
    for (var i = 0; i < opcoes.length; i++) { if (opcoes[i].id === id) { return true; } }
    return false;
  }
  function escolher(id) {
    if (!existe(id)) { return; }
    if (fechar) { fechar.setAttribute("href", "?fechar=" + encodeURIComponent(id)); }
    var itens = document.querySelectorAll("[data-opcao]");
    for (var j = 0; j < itens.length; j++) {
      itens[j].setAttribute("aria-current", itens[j].getAttribute("data-opcao") === id ? "true" : "false");
    }
  }
  function alvo(ev) {
    var t = ev.target;
    return t && t.closest ? t.closest("[data-opcao]") : null;
  }
  document.addEventListener("click", function (ev) {
    var a = alvo(ev);
    if (a) { escolher(a.getAttribute("data-opcao")); }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" && ev.key !== " ") { return; }
    var a = alvo(ev);
    if (a) { ev.preventDefault(); escolher(a.getAttribute("data-opcao")); }
  });
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
    """`R$ 4.784,27`. Valor que não é número → "" (ausente não aparece; nunca "—" inventado)."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return ""
    if v != v or v in (float("inf"), float("-inf")):
        return ""
    inteiro, _, centavos = f"{v:,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _data_curta(iso: Any) -> str:
    """`2026-10-13` → `13/10`. Fora do formato → ""."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}/{m.group(2)}" if m else ""


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


def previa_do_modelo(modelo: dict) -> dict:
    """O que a prévia do link diz — og:title/og:description e o PNG. D-MC-74.

    🔴 SÓ estes campos, e nenhum é pessoal: a seguradora e o preço da recomendada,
    quantas seguradoras foram comparadas, a marca da anfitriã e a validade. O
    primeiro nome, o veículo, CPF e placa ficam FORA — a prévia aparece na conversa
    para qualquer um que olhe a tela, e é copiada por quem encaminha a mensagem.
    """
    modelo = modelo or {}
    rec = opcao_recomendada(modelo) or {}
    resumo = modelo.get("resumo") or {}
    anfitria = modelo.get("anfitria") or {}

    seguradora = str(rec.get("seguradora") or "").strip()
    preco = _brl(rec.get("premio_anual"))
    comparadas = resumo.get("com_preco_comparavel")
    if not isinstance(comparadas, int) or isinstance(comparadas, bool):
        comparadas = resumo.get("seguradoras_cotadas")
    if not isinstance(comparadas, int) or isinstance(comparadas, bool) or comparadas < 1:
        comparadas = None
    marca = str(anfitria.get("nome") or "").strip()
    validade = _data_curta(modelo.get("validade_ate"))

    if seguradora and preco:
        titulo = f"Sua cotação de seguro: {seguradora} por {preco} ao ano"
    else:
        titulo = "Sua cotação de seguro"
    partes = []
    if comparadas:
        partes.append(f"{comparadas} seguradora{'s' if comparadas > 1 else ''} comparada"
                      f"{'s' if comparadas > 1 else ''}, igual com igual.")
    if marca:
        partes.append(f"Preparada por {marca}.")
    if validade:
        partes.append(f"Válida até {validade}.")
    return {
        "titulo": titulo,
        "descricao": " ".join(partes) or "As opções que separei para você.",
        "seguradora": seguradora,
        "preco": preco,
        "comparadas": comparadas,
        "marca": marca,
        "validade": validade,
    }


# =====================================================================================================================
# a página (PROVISÓRIA — a F2b troca o corpo e o CSS)
# =====================================================================================================================
_CSS_PROVISORIO = """
:root{color-scheme:light dark}
body{margin:0;font:400 16px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  background:#f7f8fa;color:#14181d}
main{max-width:40rem;margin:0 auto;padding:1.5rem 1rem 6rem}
h1{font-size:1.35rem;line-height:1.25;margin:0 0 1rem}
ol{list-style:none;margin:0;padding:0;display:grid;gap:.75rem}
li{background:#fff;border:1px solid #dfe3e8;border-radius:.75rem;padding:1rem}
li[aria-current=true]{border-color:#14181d}
.p{font-variant-numeric:tabular-nums;font-weight:600}
.f{position:fixed;left:1rem;right:1rem;bottom:1rem;display:block;text-align:center;padding:1rem;
  border-radius:.75rem;background:#14181d;color:#fff;text-decoration:none;font-weight:600}
.a{color:#5b6570;font-size:.85rem}
@media (prefers-color-scheme:dark){body{background:#0e1114;color:#e8ecef}li{background:#161a1e;border-color:#2a3036}
  li[aria-current=true]{border-color:#e8ecef}.f{background:#e8ecef;color:#0e1114}.a{color:#9aa4ad}}
@media print{.f{display:none}}
"""


def render_proposta(modelo: dict) -> str:
    """O documento inteiro da proposta, a partir do modelo do CONTRATO §5. PROVISÓRIO.

    Estrutura mínima que a F2b herda: o `<head>` com a prévia (og:*/twitter:*) e o
    marcador onde a og:image entra na hora de servir · as opções numa lista
    (`data-opcao`) · o "Quero fechar" (`#ab-fechar`, `?fechar=<opção>`) · os dados
    num `<script type="application/json" id="ab-dados">` · o script inline,
    IDÊNTICO a `SCRIPT_DA_PROPOSTA`. Todo texto do modelo é escapado.
    """
    modelo = modelo or {}
    previa = previa_do_modelo(modelo)
    ops = _opcoes(modelo)
    rec = opcao_recomendada(modelo)
    marca = previa["marca"]

    itens = []
    for o in ops:
        preco = _brl(o.get("premio_anual"))
        linha = " · ".join(p for p in (
            f"<strong>{_e(o.get('rotulo') or o.get('id'))}</strong>",
            _e(o.get("seguradora")) if o.get("seguradora") else "",
            f'<span class="p">{_e(preco)} por ano</span>' if preco else "",
        ) if p)
        atual = "true" if rec is not None and o is rec else "false"
        itens.append(f'<li data-opcao="{_e(o["id"])}" tabindex="0" aria-current="{atual}">{linha}</li>')

    fechar = ""
    if rec is not None:
        fechar = (f'<a id="ab-fechar" class="f" rel="nofollow" '
                  f'href="?{PARAMETRO_DO_FECHAR}={_e(quote(str(rec["id"]), safe=""))}">Quero fechar</a>')

    validade = _data_curta(modelo.get("validade_ate"))
    dados = {"opcoes": [{"id": o["id"], "rotulo": o.get("rotulo"), "seguradora": o.get("seguradora")}
                        for o in ops]}
    titulo_pagina = f"Sua cotação de seguro · {marca}" if marca else "Sua cotação de seguro"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>{_e(titulo_pagina)}</title>
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{_e(previa['titulo'])}">
<meta property="og:description" content="{_e(previa['descricao'])}">
{f'<meta property="og:site_name" content="{_e(marca)}">' if marca else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_e(previa['titulo'])}">
<meta name="twitter:description" content="{_e(previa['descricao'])}">
{MARCADOR_DA_PREVIA}
<style>{_CSS_PROVISORIO}</style>
</head>
<body>
<main>
<h1>{_e(previa['titulo'])}</h1>
<ol>
{chr(10).join(itens)}
</ol>
{f'<p class="a">Válida até {_e(validade)}.</p>' if validade else ''}
{f'<p class="a">{_e(modelo.get("aviso_legal"))}</p>' if modelo.get("aviso_legal") else ''}
{fechar}
</main>
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
    url = str(cta.get("whatsapp_url") or "").strip()
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
    candidatos.append(re.sub(r"\D", "", str(((modelo or {}).get("anfitria") or {}).get("whatsapp") or "")))
    for c in candidatos:
        if re.fullmatch(r"\d{10,15}", c or ""):
            return c
    return None


def destino_do_fechar(modelo: dict, opcao: Any) -> Optional[dict]:
    """`{destino, opcao, rotulo, seguradora}` para uma opção QUE EXISTE no modelo; senão None.

    🔴 Nunca um redirecionamento aberto: a função não recebe URL nenhuma. O
    destino é SEMPRE `https://wa.me/<dígitos da corretora>?text=<texto>`, com os
    dígitos e o texto tirados do MODELO guardado. A query só escolhe ENTRE as
    opções que o servidor já conhece.
    """
    if not isinstance(opcao, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", opcao):
        return None
    escolhida = next((o for o in _opcoes(modelo) if o.get("id") == opcao), None)
    if escolhida is None:
        return None
    digitos = _digitos_do_whatsapp(modelo)
    if not digitos:
        return None
    textos = ((modelo or {}).get("cta") or {}).get("texto_por_opcao") or {}
    texto = textos.get(opcao) if isinstance(textos, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        rotulo = str(escolhida.get("rotulo") or opcao)
        seg = str(escolhida.get("seguradora") or "").strip()
        texto = f"Olá! Quero fechar a opção {rotulo}{f' ({seg})' if seg else ''}."
    texto = texto.strip()[:_TEXTO_MAXIMO]
    return {
        "destino": f"https://wa.me/{digitos}?text={quote(texto, safe='')}",
        "opcao": opcao,
        "rotulo": escolhida.get("rotulo"),
        "seguradora": escolhida.get("seguradora"),
    }
