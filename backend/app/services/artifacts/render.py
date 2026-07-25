"""Composição final da peça. SPEC-057 §Bloco C.

Recebe a marca congelada, a composição de blocos e o dado; devolve **um único
arquivo HTML** que se basta.

Autossuficiência não é preferência de estilo, é requisito. A mesma saída é
aberta na tela do corretor, virada em PDF, mandada por e-mail e enviada por
link para um cliente que nunca ouviu falar da AutoBrokers. Qualquer referência
externa quebraria em pelo menos um desses caminhos, e a CSP das peças
compartilhadas bloqueia host de fora por decisão de segurança.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any, Optional

from ..brand.system import build_design_system, to_css_variables
from . import blocks as bl
from . import styles as st

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro")


def _data_por_extenso(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _sistema_da_marca(brand: dict) -> dict:
    """Recupera o sistema de design de dentro do snapshot.

    O snapshot já traz o sistema pronto — reconstruí-lo aqui a cada render
    produziria peças diferentes se o algoritmo mudasse, e o artefato deixaria
    de ser um registro estável. Só recalcula quando o snapshot é antigo demais
    para ter o sistema dentro.
    """
    paleta = brand.get("palette") or {}
    if paleta.get("themes"):
        return paleta
    return build_design_system(paleta.get("primary"), paleta.get("accent"),
                               typography=brand.get("typography"))


def render_html(
    *,
    brand: dict,
    composition: list[dict],
    visual_style: str = "aurora",
    title: str = "Relatório",
    data_sources: Optional[list[dict]] = None,
    generated_at: Optional[datetime] = None,
    embed_fragment: bool = False,
) -> tuple[str, dict]:
    """Devolve `(html, diagnóstico)`.

    O diagnóstico carrega bloco desconhecido e bloco que falhou. Peça que sai
    incompleta em silêncio é o pior resultado possível: parece pronta.
    """
    estilo = visual_style if visual_style in st.ESTILOS else "aurora"
    sistema = _sistema_da_marca(brand)
    tema = st.tema_do_estilo(estilo)

    logo_url = None
    logo = brand.get("logo") or {}
    if isinstance(logo, dict):
        logo_url = logo.get("data_uri") or logo.get("public_url") or logo.get("storage_ref")
    elif isinstance(logo, str):
        logo_url = logo

    ctx: dict[str, Any] = {
        "brand": {
            "name": brand.get("name") or "Corretora",
            "legal_name": brand.get("legal_name"),
            "tagline": brand.get("tagline"),
            "logo_url": logo_url,
            "susep_code": brand.get("susep_code"),
            "contact": brand.get("contact") or {},
        },
        "data_sources": data_sources or [],
        "generated_label": _data_por_extenso(generated_at),
        "visual_style": estilo,
    }

    corpo = bl.render_blocks(composition, ctx)
    diagnostico = {
        "blocos": len(composition or []),
        "desconhecidos": ctx.get("_desconhecidos", []),
        "falhas": ctx.get("_falhas", []),
        "estilo": estilo,
        "tema": tema,
        "marca_padrao": bool(brand.get("is_fallback")),
    }

    if embed_fragment:
        return corpo, diagnostico

    variaveis = to_css_variables(sistema, tema)
    css = st.css_do_estilo(estilo)

    # `color-scheme` faz o navegador combinar barra de rolagem e controles com
    # o tema da peça. Sem isso, um relatório escuro aparece com scrollbar
    # branca e a ilusão de documento acabado se quebra num detalhe idiota.
    esquema = "dark" if tema == "dark" else "light"

    documento = f"""<!doctype html>
<html lang="pt-BR" data-style="{html.escape(estilo)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="{esquema}">
<meta name="robots" content="noindex,nofollow">
<title>{html.escape(title)}</title>
<style>
:root{{color-scheme:{esquema}}}
{variaveis}
{css}
</style>
</head>
<body>
<main class="ab-doc">
{corpo}
</main>
</body>
</html>"""

    return documento, diagnostico


def render_texto_whatsapp(*, title: str, verdict: str, kpis: list[dict],
                          link: Optional[str] = None, brand_name: str = "") -> str:
    """A mesma peça em texto curto, para mandar por WhatsApp.

    Não é o relatório resumido — é o gancho. Quem recebe decide em três linhas
    se abre o link, então entram o veredito e no máximo quatro números.
    """
    linhas = [f"*{title}*"]
    if verdict:
        linhas.append("")
        linhas.append(verdict)
    if kpis:
        linhas.append("")
        for k in kpis[:4]:
            delta = k.get("delta")
            marca = ""
            if delta is not None:
                seta = "▲" if delta > 0 else ("▼" if delta < 0 else "•")
                marca = f" {seta} {abs(float(delta)):.1f}%"
            linhas.append(f"• {k.get('label','')}: *{k.get('value','—')}*{marca}")
    if link:
        linhas.append("")
        linhas.append(f"Relatório completo: {link}")
    if brand_name:
        linhas.append("")
        linhas.append(f"_{brand_name}_")
    return "\n".join(linhas)
