"""Os três sistemas visuais das peças. SPEC-057 §Bloco C.

Não são três temas de cor. São três **posturas editoriais** — cada uma decide
grade, ritmo tipográfico, densidade e peso do número:

  AURORA    claro, editorial, respiro largo, título em serifa.
            Para executivo, pesquisa e o que vai ao cliente final.

  OBSIDIAN  escuro, luminoso, painel de vidro, gráfico que emite luz.
            Para briefing diário e leitura operacional em tela.

  MERIDIAN  claro, precisão, grade apertada, fio de cabelo, numeral tabular.
            Para financeiro, carteira e sinistro — onde o número manda.

A cor vem sempre da corretora; o sistema decide o que fazer com ela. É isso que
dá variedade sem perder coerência: três posturas × oito tipos de relatório ×
a marca de cada corretora.

Fontes
------
A CSP das peças compartilhadas bloqueia host externo, então nada de Google
Fonts na entrega. As pilhas abaixo usam o que já existe no sistema — em Mac cai
em New York e SF, em Windows em Segoe UI Variable. Renderiza excelente e sem
nenhum download, o que também elimina o salto de layout que fonte remota causa.
"""

from __future__ import annotations

SERIF = ("ui-serif, 'New York', 'Iowan Old Style', 'Palatino Linotype', "
         "'Book Antiqua', Palatino, Georgia, serif")
SANS = ("-apple-system, BlinkMacSystemFont, 'Segoe UI Variable Display', "
        "'Segoe UI', Inter, Roboto, system-ui, sans-serif")
MONO = ("ui-monospace, 'SF Mono', SFMono-Regular, 'Cascadia Mono', "
        "'Segoe UI Mono', Menlo, Consolas, monospace")

ESTILOS = ("aurora", "obsidian", "meridian")

TEMA_DO_ESTILO = {"aurora": "light", "obsidian": "dark", "meridian": "light"}


# ==========================================================================
# Base comum
# ==========================================================================

_BASE = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ab-canvas);color:var(--ab-ink-base);
  font-family:var(--ab-font-body);font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
  font-variant-numeric:tabular-nums;text-rendering:optimizeLegibility}
img{max-width:100%;height:auto;display:block}
a{color:var(--ab-primary-text)}
h1,h2,h3,h4{margin:0;font-weight:var(--ab-h-weight);letter-spacing:var(--ab-h-track);
  line-height:1.14;color:var(--ab-ink-strong);font-family:var(--ab-font-display)}
p{margin:0 0 1em}
p:last-child{margin-bottom:0}

/* Numeral tabular em tudo que é número. É o detalhe que faz uma coluna de
   valores parecer alinhada por um tipógrafo em vez de por acaso. */
.ab-num,.ab-kpi-value,.ab-rank-value,.ab-bar-value,.ab-axis,
.ab-table td,.ab-donut-value,.ab-ring-value,.ab-leg-val{
  font-variant-numeric:tabular-nums lining-nums;font-feature-settings:"tnum" 1,"lnum" 1}

.ab-doc{max-width:var(--ab-measure);margin:0 auto;padding:var(--ab-pad)}
.ab-block{margin:var(--ab-gap) 0}
.ab-block:first-child{margin-top:0}

/* ---- tipografia de seção ---- */
.ab-eyebrow{font-family:var(--ab-font-body);font-size:11px;font-weight:650;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ab-primary-text);
  margin:0 0 10px;display:flex;align-items:center;gap:9px}
.ab-eyebrow::before{content:"";width:18px;height:2px;border-radius:2px;
  background:var(--ab-accent-fill);flex:none}
.ab-h2{font-size:var(--ab-h2);margin:0 0 6px}
.ab-lede{font-size:17px;color:var(--ab-ink-muted);max-width:64ch;margin:0 0 22px}

/* ---- capa ----
   O logo da corretora vem primeiro e sozinho na linha. É a primeira coisa que
   o olho encontra, e é o que faz a peça parecer propriedade dela em vez de
   relatório de fornecedor com o nome do cliente no rodapé. */
.ab-cover{padding-bottom:var(--ab-gap);border-bottom:1px solid var(--ab-border-hairline)}
.ab-cover-top{display:flex;align-items:center;justify-content:space-between;
  gap:20px;margin-bottom:var(--ab-cover-gap,54px);min-height:38px}
.ab-cover-logo{height:var(--ab-logo-h,42px);width:auto;max-width:230px;object-fit:contain}
.ab-cover-wordmark{font-family:var(--ab-font-display);font-size:19px;font-weight:650;
  letter-spacing:-.02em;color:var(--ab-ink-strong)}
.ab-cover-period{font-size:12px;font-weight:600;letter-spacing:.07em;
  text-transform:uppercase;color:var(--ab-ink-faint);padding:6px 13px;
  border:1px solid var(--ab-border-hairline);border-radius:999px;white-space:nowrap}
.ab-cover-main{max-width:min(100%,22ch + 28ch)}
.ab-cover-title{font-size:var(--ab-cover-size);line-height:1.04;
  letter-spacing:var(--ab-cover-track);margin:0 0 14px;max-width:19ch}
.ab-cover-sub{font-size:clamp(16px,1.7vw,19px);color:var(--ab-ink-muted);
  max-width:56ch;margin:0}
.ab-cover-verdict{margin:22px 0 0;font-size:clamp(15px,1.5vw,17px);
  color:var(--ab-ink-base);max-width:62ch;padding-left:16px;
  border-left:2px solid var(--ab-accent-fill)}
.ab-cover-figure{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  margin-top:38px;padding-top:26px;border-top:1px solid var(--ab-border-hairline)}
.ab-cover-figure-label{font-size:12px;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ab-ink-faint);width:100%}
.ab-cover-figure-value{font-family:var(--ab-font-display);
  font-size:clamp(40px,6vw,66px);font-weight:var(--ab-kpi-weight);line-height:1;
  letter-spacing:-.035em;color:var(--ab-ink-strong)}

/* ---- prosa ---- */
.ab-prose{max-width:70ch}
.ab-prose p{font-size:16.5px;line-height:1.72;color:var(--ab-ink-base)}
.ab-prose code{background:var(--ab-surface-2);padding:1px 6px;border-radius:5px;
  font-family:var(--ab-font-mono);font-size:.9em}

/* ---- superfícies ---- */
.ab-card{background:var(--ab-surface);border-radius:var(--ab-radius);
  border:var(--ab-card-border);box-shadow:var(--ab-shadow);padding:var(--ab-card-pad)}

/* ---- KPI ---- */
.ab-kpis{display:grid;gap:var(--ab-grid-gap);
  grid-template-columns:repeat(auto-fit,minmax(196px,1fr))}
.ab-kpi{background:var(--ab-surface);border-radius:var(--ab-radius);
  border:var(--ab-card-border);box-shadow:var(--ab-shadow);
  padding:20px 20px 16px;position:relative;overflow:hidden}
.ab-kpi::after{content:"";position:absolute;inset:0 auto 0 0;width:3px;
  background:var(--kpi-accent,var(--ab-primary-fill));opacity:var(--ab-kpi-rail,1)}
.ab-kpi-label{font-size:12px;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;color:var(--ab-ink-faint);margin:0 0 10px}
.ab-kpi-value{font-family:var(--ab-font-display);font-size:var(--ab-kpi-size);
  font-weight:var(--ab-kpi-weight);line-height:1;letter-spacing:-.025em;
  color:var(--ab-ink-strong);display:block}
.ab-kpi-unit{font-size:.5em;font-weight:500;color:var(--ab-ink-muted);margin-left:3px}
.ab-kpi-foot{display:flex;align-items:center;justify-content:space-between;
  gap:10px;margin-top:12px;min-height:22px}
.ab-delta{display:inline-flex;align-items:center;gap:5px;font-size:13px;
  font-weight:650;padding:3px 9px;border-radius:999px;white-space:nowrap}
.ab-delta[data-dir="up"]{color:var(--ab-positive-text);background:var(--ab-positive-soft)}
.ab-delta[data-dir="down"]{color:var(--ab-negative-text);background:var(--ab-negative-soft)}
.ab-delta[data-dir="flat"]{color:var(--ab-ink-muted);background:var(--ab-surface-2)}
.ab-delta svg{width:11px;height:11px;flex:none}
.ab-kpi-since{font-size:12px;color:var(--ab-ink-faint)}

/* ---- veredito ---- */
.ab-verdict{border-radius:var(--ab-radius);padding:26px 30px;
  background:var(--ab-primary-soft);border-left:3px solid var(--ab-primary-fill)}
.ab-verdict-text{font-family:var(--ab-font-display);font-size:var(--ab-verdict-size);
  line-height:1.3;letter-spacing:-.02em;color:var(--ab-ink-strong);margin:0}
.ab-verdict-note{margin:14px 0 0;font-size:14px;color:var(--ab-ink-muted)}

/* ---- gráficos ---- */
.ab-chart{width:100%;height:auto;display:block;overflow:visible}
.ab-grid{stroke:var(--ab-grid);stroke-width:1;shape-rendering:crispEdges}
.ab-axis{fill:var(--ab-ink-faint);font-size:11px;font-family:var(--ab-font-body)}
.ab-bar-value{fill:var(--ab-ink-muted);font-size:11px;font-weight:600;
  font-family:var(--ab-font-body)}
.ab-bridge{stroke:var(--ab-ink-faint);stroke-width:1;stroke-dasharray:2 3;opacity:.6}
.ab-nodata{display:flex;align-items:center;justify-content:center;gap:10px;
  min-height:150px;color:var(--ab-ink-faint);font-size:14px;border-radius:var(--ab-radius);
  border:1px dashed var(--ab-border-hairline);background:var(--ab-surface-2)}

.ab-legend{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:9px}
.ab-legend--row{display:flex;flex-wrap:wrap;gap:8px 20px;justify-content:center}
.ab-legend li{display:flex;align-items:center;gap:9px;font-size:13px}
.ab-legend i{width:10px;height:10px;border-radius:3px;flex:none}
.ab-leg-name{color:var(--ab-ink-base)}
.ab-leg-val{margin-left:auto;font-weight:650;color:var(--ab-ink-strong);
  display:flex;gap:8px;align-items:baseline}
.ab-leg-val em{font-style:normal;font-weight:500;color:var(--ab-ink-faint);font-size:12px}

.ab-donut{display:flex;gap:30px;align-items:center;flex-wrap:wrap}
.ab-donut svg{flex:none;width:220px}
.ab-donut .ab-legend{flex:1;min-width:210px;margin:0}
.ab-donut-value{fill:var(--ab-ink-strong);font-size:23px;font-weight:700;
  font-family:var(--ab-font-display)}
.ab-donut-label{fill:var(--ab-ink-faint);font-size:11px;
  font-family:var(--ab-font-body);letter-spacing:.06em;text-transform:uppercase}

.ab-ring{display:flex;flex-direction:column;align-items:center;gap:9px}
.ab-ring svg{width:116px}
.ab-ring-value{fill:var(--ab-ink-strong);font-size:21px;font-weight:700;
  font-family:var(--ab-font-display)}
.ab-ring-label{font-size:12px;color:var(--ab-ink-faint);text-align:center}

/* ---- ranking ---- */
.ab-rank{display:grid;gap:3px}
.ab-rank-row{display:grid;grid-template-columns:26px minmax(96px,1.5fr) 3fr auto;
  gap:14px;align-items:center;padding:9px 10px;border-radius:9px;
  transition:background .18s ease}
.ab-rank-row:hover{background:var(--ab-surface-2)}
.ab-rank-row.is-lead .ab-rank-label{font-weight:650;color:var(--ab-ink-strong)}
.ab-rank-pos{font-size:12px;color:var(--ab-ink-faint);font-weight:650;text-align:right}
.ab-rank-label{font-size:14px;color:var(--ab-ink-base);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.ab-rank-track{height:9px;border-radius:999px;background:var(--ab-surface-2);
  overflow:hidden;min-width:60px}
.ab-rank-fill{display:block;height:100%;border-radius:999px;width:var(--w)}
.ab-rank-value{font-size:14px;font-weight:650;color:var(--ab-ink-strong);
  text-align:right;white-space:nowrap;display:flex;flex-direction:column;align-items:flex-end}
.ab-rank-note{font-size:11px;font-weight:500;color:var(--ab-ink-faint)}

/* ---- funil ---- */
.ab-funnel{display:grid;gap:14px}
.ab-funnel-head{display:flex;justify-content:space-between;align-items:baseline;
  gap:14px;margin-bottom:7px}
.ab-funnel-head span{font-size:14px;color:var(--ab-ink-base)}
.ab-funnel-head strong{font-size:17px;color:var(--ab-ink-strong);font-weight:650}
.ab-funnel-bar{height:34px;border-radius:8px;background:var(--ab-surface-2);overflow:hidden}
.ab-funnel-bar span{display:block;height:100%;width:var(--w);border-radius:8px}
.ab-funnel-conv{display:inline-flex;gap:9px;align-items:baseline;margin-top:7px;
  font-size:12px;color:var(--ab-ink-faint)}
.ab-funnel-conv em{font-style:normal;color:var(--ab-negative-text);font-weight:600}

/* ---- tabela ---- */
.ab-table-wrap{overflow-x:auto;border-radius:var(--ab-radius);
  border:1px solid var(--ab-border-hairline)}
.ab-table{width:100%;border-collapse:collapse;font-size:14px;min-width:520px}
.ab-table th{text-align:left;font-size:11px;font-weight:650;letter-spacing:.07em;
  text-transform:uppercase;color:var(--ab-ink-faint);padding:12px 16px;
  background:var(--ab-surface-2);border-bottom:1px solid var(--ab-border-hairline);
  white-space:nowrap;position:sticky;top:0}
.ab-table td{padding:12px 16px;border-bottom:1px solid var(--ab-border-hairline);
  color:var(--ab-ink-base)}
.ab-table tr:last-child td{border-bottom:0}
.ab-table tbody tr:hover td{background:var(--ab-surface-2)}
.ab-table .num{text-align:right;font-weight:600;color:var(--ab-ink-strong)}
.ab-table tfoot td{font-weight:700;color:var(--ab-ink-strong);
  background:var(--ab-surface-2);border-top:2px solid var(--ab-border-strong)}
.ab-pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;
  font-weight:600;white-space:nowrap}

/* ---- destaque ---- */
.ab-callout{display:flex;gap:16px;padding:20px 22px;border-radius:var(--ab-radius);
  background:var(--ab-surface-2);border-left:3px solid var(--ab-primary-fill)}
.ab-callout[data-tone="warning"]{background:var(--ab-warning-soft);
  border-left-color:var(--ab-warning-fill)}
.ab-callout[data-tone="negative"]{background:var(--ab-negative-soft);
  border-left-color:var(--ab-negative-fill)}
.ab-callout[data-tone="positive"]{background:var(--ab-positive-soft);
  border-left-color:var(--ab-positive-fill)}
.ab-callout-icon{flex:none;width:22px;height:22px;color:var(--ab-primary-text)}
.ab-callout h4{font-size:15px;margin:0 0 5px;font-family:var(--ab-font-body);font-weight:700}
.ab-callout p{font-size:14px;color:var(--ab-ink-muted);margin:0}

/* ---- plano de ação ---- */
.ab-actions{display:grid;gap:11px;counter-reset:acao}
.ab-action{display:grid;grid-template-columns:30px 1fr auto;gap:16px;
  align-items:start;padding:17px 19px;background:var(--ab-surface);
  border:var(--ab-card-border);border-radius:var(--ab-radius);box-shadow:var(--ab-shadow)}
.ab-action::before{counter-increment:acao;content:counter(acao);
  width:26px;height:26px;border-radius:50%;background:var(--ab-primary-fill);
  color:var(--ab-primary-on);font-size:12px;font-weight:700;display:flex;
  align-items:center;justify-content:center;font-variant-numeric:normal}
.ab-action h4{font-size:15px;margin:0 0 4px;font-family:var(--ab-font-body);font-weight:650}
.ab-action p{font-size:13.5px;color:var(--ab-ink-muted);margin:0}
.ab-action-meta{display:flex;flex-direction:column;align-items:flex-end;gap:5px;
  font-size:12px;color:var(--ab-ink-faint);white-space:nowrap}

/* ---- procedência ---- */
.ab-sources{font-size:12.5px;color:var(--ab-ink-faint);border-top:1px solid
  var(--ab-border-hairline);padding-top:16px}
.ab-sources h4{font-size:11px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ab-ink-faint);margin:0 0 11px;font-family:var(--ab-font-body);font-weight:650}
.ab-sources ul{list-style:none;margin:0;padding:0;display:grid;gap:7px}
.ab-sources li{display:flex;gap:11px;align-items:baseline}
.ab-sources b{font-weight:600;color:var(--ab-ink-muted);font-size:12.5px}
.ab-sources time{margin-left:auto;font-variant-numeric:tabular-nums}

/* ---- grade ---- */
.ab-split{display:grid;gap:var(--ab-grid-gap);grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
.ab-split--sidebar{grid-template-columns:minmax(0,1.85fr) minmax(230px,1fr)}
@media (max-width:760px){.ab-split--sidebar{grid-template-columns:1fr}}

/* ---- rodapé ---- */
.ab-foot{margin-top:56px;padding-top:26px;border-top:1px solid var(--ab-border-hairline);
  display:flex;gap:20px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.ab-foot-brand{display:flex;align-items:center;gap:13px}
.ab-foot-brand img{height:26px;width:auto;opacity:.85}
.ab-foot-name{font-size:13px;font-weight:650;color:var(--ab-ink-muted)}
.ab-foot-meta{font-size:11.5px;color:var(--ab-ink-faint);text-align:right;line-height:1.5}
.ab-powered{font-size:10.5px;color:var(--ab-ink-faint);opacity:.7;letter-spacing:.03em}

/* ---- movimento ---- */
@media (prefers-reduced-motion:no-preference){
  .ab-reveal{opacity:0;transform:translateY(14px);
    animation:abIn .62s cubic-bezier(.22,.68,.32,1) forwards;
    animation-delay:calc(var(--i,0)*70ms)}
  @keyframes abIn{to{opacity:1;transform:none}}
  .ab-line{stroke-dasharray:2400;stroke-dashoffset:2400;
    animation:abDraw 1.5s cubic-bezier(.4,0,.2,1) .25s forwards}
  @keyframes abDraw{to{stroke-dashoffset:0}}
  .ab-dot{opacity:0;animation:abFade .5s ease 1.5s forwards}
  @keyframes abFade{to{opacity:1}}
  .ab-arc{animation:abArc 1.1s cubic-bezier(.3,.7,.3,1) .2s backwards}
  @keyframes abArc{from{stroke-dasharray:0 9999}}
  .ab-bar{transform-origin:center bottom;animation:abBar .68s cubic-bezier(.3,.8,.3,1) backwards;
    animation-delay:calc(.15s + var(--i,0)*40ms)}
  @keyframes abBar{from{transform:scaleY(0)}}
  .ab-rank-fill{animation:abGrow .82s cubic-bezier(.25,.8,.3,1) backwards;animation-delay:.2s}
  @keyframes abGrow{from{width:0}}
  .ab-funnel-bar span{animation:abGrow .82s cubic-bezier(.25,.8,.3,1) backwards;animation-delay:.2s}
}

/* ---- impressão ---- */
@page{size:A4;margin:15mm 14mm 17mm}
@media print{
  /* Animação no papel não existe: o que ela faz é imprimir o estado inicial,
     ou seja, elemento invisível e gráfico pela metade. */
  *,*::before,*::after{animation:none!important;transition:none!important}
  .ab-reveal{opacity:1!important;transform:none!important}
  .ab-line{stroke-dashoffset:0!important;stroke-dasharray:none!important}
  .ab-dot{opacity:1!important}
  body{background:#fff!important;font-size:10.5pt}
  .ab-doc{max-width:none;padding:0}
  .ab-card,.ab-kpi,.ab-action{box-shadow:none!important;
    border:1px solid rgba(0,0,0,.14)!important;break-inside:avoid}
  .ab-block{break-inside:avoid;margin:14pt 0}
  .ab-cover{break-after:page;min-height:auto}
  h1,h2,h3,.ab-eyebrow{break-after:avoid}
  .ab-table{break-inside:auto;font-size:9pt}
  .ab-table tr{break-inside:avoid}
  .ab-table th{position:static}
  .ab-nodata{border:1px solid rgba(0,0,0,.2)}
  .ab-no-print{display:none!important}
  a[href]::after{content:""}
}
"""


# ==========================================================================
# Os três sistemas
# ==========================================================================

_AURORA = """
:root{
  --ab-font-display:__SERIF__; --ab-font-body:__SANS__; --ab-font-mono:__MONO__;
  --ab-measure:1080px; --ab-pad:56px 40px 72px; --ab-gap:52px; --ab-grid-gap:20px;
  --ab-radius:16px; --ab-card-pad:28px; --ab-card-border:0;
  --ab-shadow:0 1px 2px rgba(16,24,40,.04),0 12px 32px -12px rgba(16,24,40,.10);
  --ab-h2:clamp(25px,3vw,33px); --ab-h-weight:600; --ab-h-track:-.028em;
  --ab-kpi-size:clamp(34px,4.2vw,44px); --ab-kpi-weight:600; --ab-kpi-rail:0;
  --ab-verdict-size:clamp(21px,2.6vw,27px);
  --ab-cover-size:clamp(40px,6.2vw,68px); --ab-cover-track:-.038em;
  --ab-cover-gap:64px; --ab-logo-h:46px;
}
/* Véu de luz na cor da marca. Muito sutil de propósito: percebe-se o clima,
   não o gradiente. Gradiente que se nota vira decoração e envelhece. */
body{background:
  radial-gradient(120% 78% at 8% -12%, var(--ab-primary-soft) 0%, transparent 58%),
  radial-gradient(94% 62% at 108% 4%, var(--ab-accent-soft) 0%, transparent 52%),
  var(--ab-canvas);
  background-attachment:fixed}
.ab-kpi{padding:24px 24px 20px}
.ab-kpi::after{display:none}
.ab-card,.ab-kpi{border:1px solid color-mix(in oklab,var(--ab-border-hairline) 62%,transparent)}
.ab-verdict{background:linear-gradient(100deg,var(--ab-primary-soft),transparent 78%);
  padding:32px 36px}
.ab-h2{font-size:var(--ab-h2)}
@media print{body{background:#fff!important}}
"""

_OBSIDIAN = """
:root{
  --ab-font-display:__SANS__; --ab-font-body:__SANS__; --ab-font-mono:__MONO__;
  --ab-measure:1140px; --ab-pad:44px 32px 64px; --ab-gap:44px; --ab-grid-gap:16px;
  --ab-radius:14px; --ab-card-pad:24px;
  --ab-card-border:1px solid color-mix(in oklab,var(--ab-ink-strong) 9%,transparent);
  --ab-shadow:0 1px 0 color-mix(in oklab,var(--ab-ink-strong) 5%,transparent) inset,
              0 20px 44px -22px rgba(0,0,0,.85);
  --ab-h2:clamp(23px,2.7vw,30px); --ab-h-weight:640; --ab-h-track:-.024em;
  --ab-kpi-size:clamp(31px,3.9vw,41px); --ab-kpi-weight:660; --ab-kpi-rail:1;
  --ab-verdict-size:clamp(20px,2.4vw,25px);
  --ab-cover-size:clamp(35px,5.2vw,56px); --ab-cover-track:-.032em;
  --ab-cover-gap:48px; --ab-logo-h:40px;
}
body{background:
  radial-gradient(96% 60% at 50% -18%, var(--ab-primary-soft) 0%, transparent 62%),
  var(--ab-canvas);background-attachment:fixed}
/* Painel de vidro: a superfície não é opaca, é o fundo filtrado. É o que dá a
   sensação de profundidade sem usar sombra pesada, que em tema escuro só suja. */
.ab-card,.ab-kpi,.ab-action{
  background:color-mix(in oklab,var(--ab-surface) 82%,transparent);
  backdrop-filter:blur(18px) saturate(1.25);
  -webkit-backdrop-filter:blur(18px) saturate(1.25)}
.ab-kpi{position:relative}
.ab-kpi::before{content:"";position:absolute;inset:-1px -1px auto -1px;height:1px;
  background:linear-gradient(90deg,transparent,
    color-mix(in oklab,var(--ab-primary-fill) 55%,transparent),transparent)}
/* Brilho no gráfico: dado que emite luz é a assinatura do escuro luminoso. */
.ab-chart .ab-line{filter:drop-shadow(0 0 7px color-mix(in oklab,currentColor 40%,transparent))}
.ab-chart .ab-arc{filter:drop-shadow(0 0 5px color-mix(in oklab,currentColor 34%,transparent))}
.ab-verdict{background:linear-gradient(100deg,
  color-mix(in oklab,var(--ab-primary-fill) 14%,transparent),transparent 76%)}
.ab-rank-track,.ab-funnel-bar{background:color-mix(in oklab,var(--ab-ink-strong) 7%,transparent)}
@media print{
  body{background:#fff!important;color:#111!important}
  .ab-card,.ab-kpi,.ab-action{backdrop-filter:none!important;background:#fff!important}
  .ab-chart .ab-line,.ab-chart .ab-arc{filter:none!important}
}
"""

_MERIDIAN = """
:root{
  --ab-font-display:__SANS__; --ab-font-body:__SANS__; --ab-font-mono:__MONO__;
  --ab-measure:1180px; --ab-pad:40px 32px 60px; --ab-gap:38px; --ab-grid-gap:14px;
  --ab-radius:8px; --ab-card-pad:20px;
  --ab-card-border:1px solid var(--ab-border-hairline);
  --ab-shadow:none;
  --ab-h2:clamp(20px,2.2vw,26px); --ab-h-weight:640; --ab-h-track:-.018em;
  --ab-kpi-size:clamp(27px,3.2vw,35px); --ab-kpi-weight:660; --ab-kpi-rail:1;
  --ab-verdict-size:clamp(18px,2vw,22px);
  --ab-cover-size:clamp(29px,3.9vw,43px); --ab-cover-track:-.024em;
  --ab-cover-gap:34px; --ab-logo-h:34px;
}
/* Precisão significa fio de cabelo e densidade. Sem sombra, sem raio grande:
   o que organiza é a régua, não o relevo. */
.ab-kpi{padding:16px 18px 14px}
.ab-kpi-label{font-size:11px;margin-bottom:8px}
.ab-kpi-value{letter-spacing:-.02em}
.ab-kpi::after{width:2px}
.ab-table{font-size:13px}
.ab-table th,.ab-table td{padding:9px 14px}
.ab-table td.num,.ab-kpi-value,.ab-rank-value{font-family:var(--ab-font-mono);
  font-size:.96em;letter-spacing:-.01em}
.ab-verdict{border-radius:8px;padding:20px 24px;background:var(--ab-surface-2)}
.ab-block{margin:var(--ab-gap) 0}
.ab-rank-row{padding:6px 8px;border-radius:5px}
.ab-card{border-radius:8px}
"""

_POR_ESTILO = {"aurora": _AURORA, "obsidian": _OBSIDIAN, "meridian": _MERIDIAN}


def css_do_estilo(estilo: str = "aurora") -> str:
    """CSS completo de um sistema visual, já com as pilhas de fonte."""
    base = _POR_ESTILO.get(estilo, _AURORA)
    # Substituição por token, não `%`: CSS é cheio de por-cento (100%, 50%) e o
    # formatador do Python tentaria ler cada um como especificador.
    return ((_BASE + base)
            .replace("__SERIF__", SERIF)
            .replace("__SANS__", SANS)
            .replace("__MONO__", MONO))


def tema_do_estilo(estilo: str) -> str:
    """Qual tema de cor (claro/escuro) cada sistema usa."""
    return TEMA_DO_ESTILO.get(estilo, "light")
