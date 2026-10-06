"""O CSS da página da proposta — o desenho "carteira" v4 aprovado (D-130A-11) + os 8 acabamentos medidos
da 4ª rodada (laudos critico-g/critico-h). SPEC-130-A · U5 (F2b).

A FONTE vai embutida (`data:`): a CSP do `/r/` é `font-src 'self' data:` e `default-src 'none'` — uma
folha do Google Fonts seria bloqueada (e daria erro no console). Instrument Sans, SIL OFL 1.1
(`fontes/OFL.txt`), corte latino variável (peso 400–700, largura 75–100 %), 📊 57.332 bytes.
Sem o arquivo, a página cai na fonte do sistema (nada quebra).

Os acabamentos, cada um no lugar onde mora:

```
régua           os rótulos vêm em DOIS conjuntos (estreito < 600 px, largo ≥ 600 px), escolhidos no servidor
                pela largura medida dos glifos (proposta_apresentacao.eixo_da_regua) — nunca se atropelam
"Quero esta"    largura do cartão, padding-inline 18 px, ≥ 50 px de altura (o texto não encosta na borda)
rodapé          fundo sólido (97 % com desfoque só onde há desfoque; 100 % sem); a nota em largura normal
cartões         esticados à altura do trilho, alinhados pelo TOPO; o pé desce (`margin-top:auto`): o vazio
                vira respiro DENTRO do cartão e os três "Quero esta" ficam na mesma linha
"Recomendada"   uma vez na 1ª tela: a aba diz a opção; o selo do cartão 1 diz "Nossa escolha" (< 1024 px)
comparar        o cabeçalho GRUDA: `overflow-x: clip` (não `hidden`, que fazia do body um rolador e
                matava o sticky) e nenhuma regra mais específica devolvendo `position: relative`
selo            no fim da linha do RÓTULO da cobertura, nunca entre duas linhas de texto
último cartão   `scroll-snap-align: end` + 16 px à direita: sem os ~50 px mortos
```
"""

from __future__ import annotations

import base64
from pathlib import Path

PASTA_DAS_FONTES = Path(__file__).resolve().parent / "fontes"
FONTE_WEB = PASTA_DAS_FONTES / "instrument-sans-latin.woff2"


def _font_face() -> str:
    try:
        dados = FONTE_WEB.read_bytes()
    except OSError:
        return ""
    b64 = base64.b64encode(dados).decode("ascii")
    return ("@font-face{font-family:'Instrument Sans';font-style:normal;font-weight:400 700;font-stretch:75% 100%;"
            f"font-display:swap;src:url(data:font/woff2;base64,{b64}) format('woff2')}}\n")


CSS_DA_PROPOSTA = _font_face() + r"""
/* Fallback neutro antes do tema; o tema real vem do cadastro da corretora (segundo <style>). */
:root{
  --canvas:#F7F8F9;--surface:#FFFFFF;--surface-2:#EEF1F3;--elevated:#FFFFFF;
  --ink-strong:#15191D;--ink:#2C3238;--ink-muted:#5A626A;--line:#E0E4E7;--line-strong:#C3C9CE;
  --p:#2E3740;--p-on:#FFFFFF;--p-soft:#E9EDF0;--p-text:#2E3740;--a:#2E3740;--pos:#00824F;--neg:#B24B58;
  --pass1:#2E3740;--pass1-on:#fff;--pass2:#E6EAED;--pass2-on:#15191D;--pass3:#F4F6F8;--pass3-on:#15191D;--badge:#fff;--badge-on:#000;
  --shadow-tint:15 19 23;--gutter:16px;--seam:226px;--cta:#2E3740;--cta-on:#fff;--pos-bg:#E6F3EC;--neg-bg:#F7E9EB;
  --font:'Instrument Sans',ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;scroll-padding-top:12px}
/* clip (e não hidden): hidden faz do body um rolador e o cabeçalho do comparar deixa de grudar */
html,body{overflow-x:clip}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:var(--font);font-size:16px;line-height:1.5;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
img{display:block;max-width:100%}
a{color:inherit}
button{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--p-text);outline-offset:3px;border-radius:8px}
.wrap{max-width:720px;margin:0 auto;padding-left:var(--gutter);padding-right:var(--gutter)}
.no-js .js-only{display:none!important}
summary{cursor:pointer;list-style:none}
summary::-webkit-details-marker{display:none}
details[open]>summary>svg:last-child{transform:rotate(180deg)}
summary>svg:last-child{transition:transform .2s}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

/* topo */
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:12px;padding-bottom:2px}
.brand{display:flex;align-items:center;gap:10px;min-height:44px;min-width:0}
.brand img{height:30px;width:auto}
.plate{display:block;border-radius:12px;padding:6px 0}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .plate{background:#fff;padding:6px 10px}}
:root[data-theme="dark"] .plate{background:#fff;padding:6px 10px}
.mono{width:40px;height:40px;border-radius:11px;background:var(--p);color:var(--p-on);display:grid;place-items:center;font-weight:650;font-size:15px;font-variation-settings:'wdth' 90;flex:none}
.mono.big{width:56px;height:56px;border-radius:15px;font-size:20px}
.brand-name{font-weight:600;font-size:17px;color:var(--ink-strong);letter-spacing:-.01em}
.trust{display:inline-flex;align-items:center;gap:6px;font-size:13.5px;color:var(--ink-muted);text-align:right;line-height:1.25;flex:none}
.trust strong{color:var(--ink-strong);font-weight:600}
.trust svg{width:15px;height:15px;color:var(--a);flex:none}
.sealrow{margin:0 0 6px}
.seal{white-space:nowrap;display:inline-flex;align-items:center;gap:6px;font-size:13px;line-height:1.25;color:var(--ink);border:1px solid var(--line-strong);border-radius:999px;padding:3px 11px 3px 9px;background:var(--surface)}
.seal svg{width:14px;height:14px;flex:none}

.hero{padding-top:6px}
.hero h1 .hello{color:var(--ink-muted);font-weight:500}
.hero h1{margin:0;font-size:29px;line-height:1.04;font-weight:600;letter-spacing:-.025em;color:var(--ink-strong);font-variation-settings:'wdth' 88;text-wrap:balance}
.lede{margin:8px 0 0;font-size:15px;color:var(--ink-muted);max-width:46ch}

/* régua: só as completas (N pontos = o N do texto) */
.regua{margin:4px 0 22px}
.regua figcaption{font-size:14px;color:var(--ink-muted);margin:0 0 6px}
.regua figcaption b{color:var(--ink-strong);font-weight:600}
.rail{position:relative;height:68px;margin:0 10px}
.axis{position:absolute;left:0;right:0;top:40px;height:1px;background:var(--line-strong)}
.ticks{position:absolute;inset:0;pointer-events:none}
.ticks.w{display:none}
@media (min-width:600px){.ticks.n{display:none}.ticks.w{display:block}}
.tick{position:absolute;top:53px;transform:translateX(-50%);font-size:13px;color:var(--ink-muted);white-space:nowrap;line-height:1;font-variation-settings:'wdth' 100}
.tick.first{transform:none}.tick.last{transform:translateX(-100%)}
.dot{position:absolute;top:calc(40px - 4.5px - var(--r, 0) * 11px);width:9px;height:9px;margin-left:-4.5px;border-radius:50%;
  border:1.5px solid var(--ink-muted);background:var(--canvas)}
.dot.mine{width:12px;height:12px;margin-left:-6px;top:calc(40px - 6px - var(--r, 0) * 11px);border:0;background:var(--p-text);box-shadow:0 0 0 2px var(--canvas)}
.dot.econ{width:11px;height:11px;margin-left:-5.5px;top:34.5px;border-radius:2px;transform:rotate(45deg);border:1.5px solid var(--ink-muted);background:var(--canvas);box-shadow:0 0 0 2px var(--canvas)}
.dot.on{box-shadow:0 0 0 2px var(--canvas),0 0 0 4.5px var(--p-text)}
.dot.econ.on{background:var(--ink-muted);box-shadow:0 0 0 2px var(--canvas),0 0 0 3.5px var(--ink-muted)}
.flag{position:absolute;top:0;transform:translateX(-50%);font-size:13px;font-weight:600;color:var(--ink-strong);white-space:nowrap;line-height:1;
  padding:5px 8px;border-radius:8px;background:var(--surface);border:1px solid var(--line-strong);opacity:0;transition:opacity .2s}
.flag.l{transform:translateX(-12px)} .flag.r{transform:translateX(calc(-100% + 12px))}
.flag.on{opacity:1}
.legend{display:flex;flex-wrap:wrap;gap:4px 16px;margin:4px 0 0;font-size:13px;color:var(--ink-muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.lg{display:inline-block;width:10px;height:10px;border-radius:50%;flex:none}
.dot-l{border:1.5px solid var(--ink-muted)} .mine-l{background:var(--p-text)} .econ-l{border:1.5px solid var(--ink-muted);border-radius:2px;transform:rotate(45deg)}
.on-l{background:var(--p-text);box-shadow:0 0 0 2px var(--canvas),0 0 0 3.5px var(--p-text)}

/* linha de navegação + abas */
.navrow{display:flex;align-items:center;gap:10px;margin-top:12px}
.navrow .tabs{flex:1;margin:0}
.nav{display:none;align-items:center;gap:2px;flex:none}
@media (min-width:768px){.nav{display:flex}}
.nav button{width:44px;height:44px;border-radius:50%;border:1px solid var(--line);background:var(--surface);cursor:pointer;display:grid;place-items:center;color:var(--ink-strong)}
.nav button:disabled{opacity:.4;cursor:default}
.nav svg{width:18px;height:18px}
.count{min-width:46px;text-align:center;font-size:14px;color:var(--ink-muted)}
.tabs{position:relative;display:flex;margin:0;padding:3px;border-radius:14px;background:var(--surface-2);border:1px solid var(--line)}
.tab-ind{position:absolute;top:3px;bottom:3px;left:3px;width:calc((100% - 6px) / var(--n, 3));border-radius:11px;background:var(--elevated);
  box-shadow:0 1px 2px rgb(var(--shadow-tint) / .14),0 3px 10px rgb(var(--shadow-tint) / .08);transform:translateX(calc(var(--pos, 0) * 100%));pointer-events:none}
.tab{position:relative;flex:1 1 0;display:grid;place-items:center;text-align:center;border-radius:11px;padding:4px 6px;min-height:44px;
  font-size:14px;line-height:1.15;font-weight:500;color:var(--ink-muted);text-decoration:none;transition:color .2s}
.tab[aria-selected="true"]{color:var(--ink-strong);font-weight:600}

/* ---------- a carteira ---------- */
/* stretch: todos os cartões com a altura do trilho, alinhados pelo topo; o pé desce para a mesma linha */
.track{display:flex;align-items:stretch;gap:4px;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x mandatory;
  --card-w:min(380px, calc(100vw - 60px));scroll-padding-inline:16px;
  padding:10px 16px 40px 16px;scrollbar-width:none;perspective:1400px}
.track::-webkit-scrollbar{display:none}
.track:focus-visible{outline-offset:-3px;border-radius:24px}
.slot{position:relative;flex:0 0 var(--card-w);display:flex;scroll-snap-align:start;scroll-snap-stop:always;isolation:isolate;
  animation:deal .6s cubic-bezier(.2,.75,.2,1) both}
.slot:last-child{scroll-snap-align:end}
.slot:nth-child(2){animation-delay:.07s} .slot:nth-child(3){animation-delay:.14s}
/* só transform: o preço nunca fica transparente esperando a animação */
@keyframes deal{from{transform:translateX(34px)}to{transform:none}}
/* Sombra ambiente: SÓ na metade de baixo do cartão. O furo do picote nunca recebe sombra. */
.slot::before{content:"";position:absolute;z-index:-1;left:20px;right:20px;top:52%;bottom:0;border-radius:40px;
  background:rgb(var(--shadow-tint) / .15);filter:blur(14px);transform:translateY(12px);pointer-events:none}
.slot:first-child::before{background:rgb(var(--shadow-tint) / .22)}
.pass{--d:0;--ad:0;position:relative;flex:1;min-width:0;display:flex;flex-direction:column;border-radius:22px;background:var(--surface);overflow:hidden;cursor:grab;
  /* escala a partir do TOPO: os vizinhos recuam sem descer, e o topo dos três fica na mesma linha */
  transform-origin:50% 0;
  transform:translateX(calc(var(--d) * -10px)) rotateY(calc(var(--d) * -12deg)) scale(calc(1 - var(--ad) * .05));
  -webkit-mask:radial-gradient(circle 12px at 0 var(--seam),#0000 98%,#000) left/51% 100% no-repeat,
               radial-gradient(circle 12px at 100% var(--seam),#0000 98%,#000) right/51% 100% no-repeat;
          mask:radial-gradient(circle 12px at 0 var(--seam),#0000 98%,#000) left/51% 100% no-repeat,
               radial-gradient(circle 12px at 100% var(--seam),#0000 98%,#000) right/51% 100% no-repeat;
}
.pass:active{cursor:grabbing}
.notch{position:absolute;z-index:4;top:calc(var(--seam) - 13px);width:26px;height:26px;border-radius:50%;pointer-events:none;
  box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--ink-strong) 16%, transparent)}
.notch.l{left:-13px} .notch.r{right:-13px}
.pass::after{content:"";position:absolute;inset:0;border-radius:inherit;box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--ink-strong) 11%, transparent);pointer-events:none;z-index:3}
.pass[data-v="1"]::after{box-shadow:inset 0 0 0 1.5px color-mix(in srgb, var(--ink-strong) 22%, transparent)}
.pass-head{position:relative;height:var(--seam);padding:16px 18px 14px;background:var(--bg);color:var(--on);display:flex;flex-direction:column;isolation:isolate;
  box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--on) 8%, transparent)}
.pass-head::after{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(130% 90% at calc(18% - var(--d) * 70%) -10%, rgb(255 255 255 / .18), rgb(255 255 255 / 0) 58%)}
.pass[data-v="1"]{--bg:var(--pass1);--on:var(--pass1-on)}
.pass[data-v="2"]{--bg:var(--pass2);--on:var(--pass2-on)}
.pass[data-v="3"]{--bg:var(--pass3);--on:var(--pass3-on)}
.ph-row{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.badge{display:inline-flex;align-items:center;min-height:28px;padding:3px 11px;border-radius:999px;font-size:13.5px;font-weight:600;line-height:1.15;
  background:color-mix(in srgb, var(--on) 10%, transparent);color:var(--on);max-width:62%}
.pass[data-v="1"] .badge{background:var(--badge);color:var(--badge-on)}
/* a aba já nomeia a opção (< 1024 px): o selo do 1º cartão diz OUTRA coisa; sem abas (≥ 1024), o rótulo */
.badge .b-rot{display:none}
@media (min-width:1024px){.badge .b-alt{display:none}.badge .b-rot{display:inline}}
.field{display:grid;justify-items:end;line-height:1;color:var(--on);flex:none}
.fl{font-size:13px;opacity:.82}
.fv{font-size:26px;font-weight:650;letter-spacing:-.02em;font-variation-settings:'wdth' 85;margin-top:3px}
.fv small{font-size:14px;font-weight:550;opacity:.78;margin-left:1px;letter-spacing:0}
.insurer{margin:10px 0 0;font-size:23px;font-weight:600;letter-spacing:-.02em;line-height:1.15}
.product{font-size:14.5px;font-weight:500;letter-spacing:0;opacity:.8;margin-left:4px}
.price{margin:auto 0 0;display:flex;align-items:baseline;flex-wrap:wrap;line-height:1;letter-spacing:-.035em;font-variation-settings:'wdth' 82}
.price .cur{font-size:19px;font-weight:550;margin-right:4px;letter-spacing:0;align-self:flex-start;margin-top:5px}
.price .int{font-size:50px;font-weight:650}
.price .dec{font-size:23px;font-weight:600}
.price .per{font-size:14.5px;font-weight:500;letter-spacing:0;margin-left:7px;opacity:.85;font-variation-settings:'wdth' 100}
.inst{margin:7px 0 0;font-size:14px;opacity:.9;line-height:1.35}
.valid{margin:6px 0 0;font-size:13px;opacity:.82}
.inst .tot{display:block;font-size:13.5px;opacity:.78;margin-top:1px}
.inst strong{font-weight:600}

.sec{margin:0 12px;padding:14px 6px 0;color:var(--ink);min-width:0}
.sec.fq{border-top:1.5px dashed var(--line-strong)}
.sec.foot{margin-top:auto;padding-top:16px;padding-bottom:16px}
.want{display:flex;align-items:center;justify-content:center;gap:8px;min-height:50px;padding:0 18px;border-radius:12px;border:1.5px solid var(--p-text);
  color:var(--p-text);font-size:15px;font-weight:600;text-decoration:none;white-space:nowrap}
.want svg{width:19px;height:19px;flex:none}
.cx{display:block;font-size:13px;color:var(--ink-muted);margin-top:1px}
.sec.cov{display:grid;grid-template-columns:22px 1fr;column-gap:10px;align-content:start;padding:7px 6px 7px;border-top:1px solid var(--line)}
.sec.blk+.sec.cov{margin-top:12px}
.sec.morewrap{padding-top:0;border-top:1px solid var(--line)}
.sec.morewrap:empty{border-top:0}
.sec.morewrap .more{border-top:0;margin-top:0}
.fq{display:grid;grid-template-columns:1fr auto;gap:0 12px;align-items:baseline}
.fq .lbl{font-size:14px;color:var(--ink-muted)}
.fq .val{font-size:19px;font-weight:600;color:var(--ink-strong);letter-spacing:-.01em}
.fq .hint{grid-column:1/-1;font-size:13px;color:var(--ink-muted);line-height:1.35}
.blk h3{margin:0 0 6px;font-size:14px;font-weight:600;color:var(--ink-strong)}
.why,.diffs{margin:0;padding:0;list-style:none;display:grid;gap:5px;font-size:14px;line-height:1.38}
.why li{display:grid;grid-template-columns:17px 1fr;gap:8px}
.why svg{width:17px;height:17px;color:var(--pos);margin-top:1px}
.diffs li{display:grid;grid-template-columns:12px 1fr;gap:6px}
.diffs li::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--ink-muted);margin-top:7.5px}
.expl{margin:0;font-size:14px;line-height:1.4}
.covs{margin:0;padding:0;list-style:none;display:grid}
.covs li{display:grid;grid-template-columns:22px 1fr;column-gap:10px;padding:6px 0;border-top:1px solid var(--line)}
.ci{grid-row:1/3;color:var(--p-text);padding-top:1px}
.ci svg{width:20px;height:20px;display:block}
.cn{font-size:14px;font-weight:550;color:var(--ink-strong);line-height:1.3}
.cv{font-size:13.5px;color:var(--ink-muted);line-height:1.35}
.selo{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:999px;font-size:13px;font-weight:600;line-height:1.45;
  background:var(--surface-2);color:var(--ink);white-space:nowrap;vertical-align:1px}
.selo.up{background:var(--pos-bg);color:var(--pos)}
.selo.down{background:var(--neg-bg);color:var(--neg)}
.selo.neutro{background:var(--surface-2);color:var(--ink)}
.selo svg{width:11px;height:11px;margin-right:3px;vertical-align:-1px}
.more summary{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:48px;font-size:14px;font-weight:550;color:var(--p-text)}
.more summary svg{width:18px;height:18px}
.more .covs li:first-child{border-top:1px solid var(--line);padding-top:7px}

/* comparar lado a lado (details nativo: funciona sem JS) */
.cmp{margin:0;--band:color-mix(in srgb, var(--p-soft) 75%, transparent)}
.compare-btn{display:flex;align-items:center;gap:10px;min-height:52px;padding:0 16px;border-radius:14px;border:1px solid var(--line-strong);background:var(--surface);
  font-size:15.5px;font-weight:600;color:var(--ink-strong)}
.compare-btn svg{width:19px;height:19px;flex:none}
.compare-btn span{flex:1}
.cmp[open] .compare-btn{border-radius:14px 14px 0 0;border-bottom-color:var(--line)}
.cmp-in{border:1px solid var(--line-strong);border-top:0;border-radius:0 0 14px 14px;background:var(--surface);padding:6px 14px 10px}
.cmp-tools{display:grid;gap:4px;padding:4px 0 8px;border-bottom:1px solid var(--line)}
.only{display:flex;align-items:center;gap:10px;min-height:44px;font-size:14.5px;color:var(--ink);cursor:pointer}
.only input{width:22px;height:22px;accent-color:var(--p);margin:0}
.key{margin:0;font-size:13px;color:var(--ink-muted);line-height:1.6}
.key .selo{margin:0 4px 0 0}
.cols{display:grid;grid-template-columns:repeat(var(--n, 3),minmax(0,1fr));gap:8px}
.cmp-grid{position:relative}
.cmp-grid>.row{position:relative}
.cmp-grid>.cmp-head{position:sticky;top:0;z-index:2;background:var(--surface);padding:10px 0}
.mini{border-radius:10px;padding:7px 8px;min-height:58px;align-content:start;background:var(--bg);color:var(--on);display:grid;gap:1px;box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--on) 10%, transparent)}
.mini span{font-size:13px;opacity:.85;line-height:1.2}
.mini b{font-size:15px;font-weight:600;line-height:1.15;overflow-wrap:anywhere}
.mini[data-v="1"]{--bg:var(--pass1);--on:var(--pass1-on)} .mini[data-v="2"]{--bg:var(--pass2);--on:var(--pass2-on)} .mini[data-v="3"]{--bg:var(--pass3);--on:var(--pass3-on)}
.row{padding:11px 0;border-top:1px solid var(--line)}
.row h4{margin:0 0 6px;font-size:13.5px;font-weight:550;color:var(--ink-muted);display:flex;align-items:center;gap:6px}
.row h4 svg{width:16px;height:16px;flex:none}
.cell{font-size:14px;line-height:1.35;color:var(--ink-strong);overflow-wrap:break-word;min-width:0}
.cell b{font-weight:600;font-size:15px}
.cell .sub{display:block;font-size:13px;color:var(--ink-muted)}
.cell .selo{display:table;margin:5px 0 0}
.cell .dt{display:block;font-size:13px;color:var(--ink);margin-top:2px}
.eq{margin:0;font-size:14px;color:var(--ink-muted)}
.eq b{color:var(--ink-strong);font-weight:550}
.cmp:has(#only:checked) .row.same{display:none}
.cmp .row .cols{align-items:stretch}
.cmp[data-on="0"] .row .cols>:nth-child(1),.cmp[data-on="1"] .row .cols>:nth-child(2),.cmp[data-on="2"] .row .cols>:nth-child(3){background:var(--band);box-shadow:0 0 0 5px var(--band);border-radius:1px}
.cmp[data-on="0"] .cmp-head>:nth-child(1),.cmp[data-on="1"] .cmp-head>:nth-child(2),.cmp[data-on="2"] .cmp-head>:nth-child(3){outline:2px solid var(--p-text);outline-offset:2px}

/* seções calmas */
section.s{padding:48px 0 0}
.s h2{margin:0;font-size:24px;line-height:1.15;font-weight:600;letter-spacing:-.02em;color:var(--ink-strong);font-variation-settings:'wdth' 92;text-wrap:balance}
.s .sub{margin:6px 0 0;font-size:15px;color:var(--ink-muted);max-width:52ch}
.sub0{margin:0;font-size:15px;color:var(--ink-muted)}
.duel{margin:16px 0 0;border:1px solid var(--line);border-radius:16px;background:var(--surface);padding:12px 16px;display:grid;gap:6px}
.duel p{margin:0;font-size:14px;color:var(--ink-muted)}
.duel-row{display:flex;justify-content:space-between;gap:12px;font-size:15.5px;color:var(--ink)}
.duel-row b{font-weight:600;color:var(--ink-strong)}
.duel-row.win span{font-weight:600;color:var(--ink-strong)}
.rank{list-style:none;margin:16px 0 0;padding:0;border-top:1px solid var(--line)}
.rank li{display:grid;grid-template-columns:24px 1fr auto;gap:1px 10px;padding:10px 8px;border-bottom:1px solid var(--line);align-items:baseline}
.rank .n{font-size:13px;color:var(--ink-muted)}
.rank .nm{font-size:15.5px;font-weight:550;color:var(--ink-strong);display:flex;align-items:center;gap:8px;flex-wrap:nowrap;min-width:0}
.rank .pr{font-size:15.5px;font-weight:600;color:var(--ink-strong);text-align:right;white-space:nowrap}
.rank .meta{grid-column:2/4;display:flex;justify-content:space-between;gap:10px;font-size:13px;color:var(--ink-muted)}
.rank li.mine{background:linear-gradient(90deg, var(--p-soft), transparent 90%)}
.tag{white-space:nowrap;font-size:13px;font-weight:600;padding:1px 8px;border-radius:999px;background:var(--surface);border:1px solid var(--line-strong);color:var(--ink)}
.note{margin:12px 0 0;font-size:14px;color:var(--ink-muted);line-height:1.45}
.note b{color:var(--ink-strong);font-weight:600}
.others{margin:14px 0 0;display:grid;gap:6px}
.line{border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.line summary{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:48px;padding:6px 14px;font-size:14px;color:var(--ink-muted);line-height:1.35}
.line summary b{color:var(--ink-strong);font-weight:600}
.line summary svg{width:18px;height:18px;flex:none}
.line ul{margin:0;padding:0 14px 12px;list-style:none;display:grid;gap:6px}
.line li{font-size:14px;color:var(--ink-muted);line-height:1.4}
.line li b{color:var(--ink);font-weight:550}
.line-static{margin:4px 0 0;font-size:14px;color:var(--ink-muted);padding:0 2px}
.line-static b{color:var(--ink-strong);font-weight:600}

.host{margin:16px 0 0;border-radius:22px;background:var(--surface);border:1px solid var(--line);padding:20px;display:grid;gap:16px}
.host-id{display:flex;align-items:center;gap:14px;min-width:0}
.host-id img{height:44px;width:auto}
.host-id h3{margin:0;font-size:19px;font-weight:600;color:var(--ink-strong);letter-spacing:-.01em}
.host-id p{margin:2px 0 0;font-size:14px;color:var(--ink-muted)}
.facts{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.fact{padding:12px 0;display:grid;gap:2px;min-width:0}
.fact+.fact{border-left:1px solid var(--line);padding-left:14px}
.fact:nth-child(3){grid-column:1/-1;border-left:0;padding-left:0;border-top:1px solid var(--line)}
.fact b{font-size:20px;font-weight:600;color:var(--ink-strong);display:flex;align-items:center;gap:4px}
.fact b svg{width:16px;height:16px;color:var(--a)}
.fact span{font-size:13px;color:var(--ink-muted);line-height:1.3}
.src{font-size:13px;color:var(--ink-muted);margin:0}
.what{margin:0;padding:12px 14px;border-radius:14px;background:var(--surface-2);font-size:14px;line-height:1.45;color:var(--ink)}
.what b{display:block;color:var(--ink-strong);font-weight:600;margin-bottom:2px}
.chan{display:flex;gap:8px;flex-wrap:wrap}
.chan a{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 14px;border-radius:12px;border:1px solid var(--line-strong);font-size:14.5px;font-weight:550;text-decoration:none;color:var(--ink-strong)}
.chan svg{width:18px;height:18px}
.steps{list-style:none;margin:18px 0 0;padding:0;counter-reset:st;display:grid}
.steps li{counter-increment:st;display:grid;grid-template-columns:34px 1fr;gap:14px;position:relative;padding-bottom:18px}
.steps li::before{content:counter(st);width:34px;height:34px;border-radius:50%;border:1.5px solid var(--p-text);color:var(--p-text);display:grid;place-items:center;font-weight:600;font-size:15px;background:var(--canvas);z-index:1}
.steps li:not(:last-child)::after{content:"";position:absolute;left:16.25px;top:34px;bottom:0;width:1.5px;background:var(--line-strong)}
.steps p{margin:5px 0 0;font-size:15.5px;color:var(--ink)}
.faq{margin:14px 0 0;border-top:1px solid var(--line)}
.faq details{border-bottom:1px solid var(--line)}
.faq summary{display:flex;justify-content:space-between;align-items:center;gap:12px;min-height:56px;padding:10px 0;font-size:16px;font-weight:550;color:var(--ink-strong)}
.faq summary svg{width:18px;height:18px;flex:none;color:var(--ink-muted)}
.faq details p{margin:0 0 16px;font-size:15px;color:var(--ink-muted);max-width:60ch}
.legal{margin:48px 0 0;padding:20px 0 0;border-top:1px solid var(--line);font-size:13.5px;color:var(--ink-muted);display:grid;gap:8px}
.legal p{margin:0;max-width:64ch}
.legal .valid{font-size:15px;color:var(--ink-strong);font-weight:550;opacity:1}
.endpad{height:150px}

/* rodapé fixo: fundo SÓLIDO (o conteúdo de trás nunca aparece entre os botões) */
.dock{position:fixed;left:0;right:0;bottom:0;z-index:20;padding:9px 12px calc(8px + env(safe-area-inset-bottom));
  background:var(--canvas);border-top:1px solid var(--line)}
@supports ((-webkit-backdrop-filter:blur(1px)) or (backdrop-filter:blur(1px))){
  .dock{background:color-mix(in srgb, var(--canvas) 97%, transparent);backdrop-filter:saturate(1.4) blur(16px);-webkit-backdrop-filter:saturate(1.4) blur(16px)}
}
.dock-in{max-width:720px;margin:0 auto;display:flex;gap:8px}
.ask{flex:none;display:grid;place-items:center;min-height:52px;padding:0 13px;border-radius:16px;border:1px solid var(--line-strong);background:var(--surface);
  font-size:14.5px;font-weight:550;text-decoration:none;color:var(--ink-strong);white-space:nowrap}
.close{flex:1;display:flex;align-items:center;gap:10px;min-height:52px;padding:5px 14px;border-radius:16px;background:var(--cta);color:var(--cta-on);text-decoration:none;min-width:0;
  box-shadow:0 1px 0 rgb(255 255 255 / .12) inset,0 8px 18px -8px var(--cta)}
.dock-note{max-width:720px;margin:5px auto 0;font-size:13px;line-height:1.3;color:var(--ink-muted);text-align:center;text-wrap:balance}
.close svg{width:22px;height:22px;flex:none}
.close .t{display:grid;min-width:0;line-height:1.2}
.close .t b{font-size:16.5px;font-weight:650}
.close .t span{font-size:13.5px;opacity:.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.close .t span.swap{animation:swap .35s ease}
@keyframes swap{from{opacity:0;transform:translateY(4px)}to{opacity:.9;transform:none}}

@media (min-width:760px){
  :root{--gutter:28px}
  .hero{padding-top:30px;text-align:center}
  .hero h1{font-size:56px;max-width:16ch;margin-left:auto;margin-right:auto}
  .lede{font-size:17px;margin-left:auto;margin-right:auto}
  .navrow{max-width:640px;margin-left:auto;margin-right:auto}
  .legend{justify-content:center}
  .track{--card-w:360px;column-gap:20px}
  .s h2{font-size:30px}
  .top{max-width:1200px}
}
@media (min-width:1024px){
  /* os três juntos: aqui sim as linhas se alinham entre os cartões (subgrid) */
  .hero.wrap{max-width:1200px}
  .hero h1{font-size:44px;max-width:27em}
  .lede{max-width:60ch;text-wrap:balance}
  .navrow{display:none}
  .widewrap{max-width:1200px;margin:0 auto}
  .track{display:grid;grid-auto-flow:column;grid-template-rows:repeat(var(--rows, 9),auto);column-gap:24px;
    --card-w:calc((min(100vw, 1200px) - 56px - 48px) / 3);grid-auto-columns:var(--card-w);
    padding:18px calc((100% - var(--n, 3) * var(--card-w) - (var(--n, 3) - 1) * 24px) / 2) 64px;scroll-snap-type:none}
  .slot{grid-row:1 / span var(--rows, 9);display:grid;grid-template-rows:subgrid}
  .pass{display:grid;grid-template-rows:subgrid;grid-row:1 / -1}
  .sec.foot{align-self:end}
}
.spread .pass{transform:none}
.spread .slot:not(.on){cursor:pointer}
/* o ativo NÃO sobe: ganha borda da cor da marca, seguindo o picote */
.spread .slot.on .pass::after{box-shadow:inset 0 0 0 2px var(--p-text)}
.spread .slot.on .notch{box-shadow:inset 0 0 0 2px var(--p-text)}
@media (prefers-reduced-motion:reduce){
  .pass{transform:none!important}
  .slot,.close .t span.swap{animation:none}
  *{transition:none!important;scroll-behavior:auto!important}
}

/* impressão (D-130A-07: o PDF é o "imprimir" do navegador): papel branco, tinta preta, cartões empilhados */
@media print{
  :root{--canvas:#fff;--surface:#fff;--surface-2:#f2f2f2;--ink-strong:#000;--ink:#111;--ink-muted:#333;--line:#bbb;--line-strong:#888;
    --pass1:#fff;--pass1-on:#000;--pass2:#fff;--pass2-on:#000;--pass3:#fff;--pass3-on:#000;--badge:#fff;--badge-on:#000;--p-text:#000;--band:transparent}
  html,body{background:#fff;color:#000;overflow:visible}
  .dock,.navrow,.nav,.endpad,.flag,.compare-btn svg,.chan{display:none!important}
  .hero{padding-top:0;text-align:left}
  .hero h1{font-size:24pt;max-width:none}
  .widewrap,.wrap{max-width:none;padding:0}
  .track{display:block!important;overflow:visible;padding:0;perspective:none}
  .slot{display:block;margin:0 0 12pt;break-inside:avoid;animation:none}
  .slot::before,.notch,.pass-head::after{display:none}
  .pass{display:block!important;transform:none!important;-webkit-mask:none;mask:none;border:1px solid #888;border-radius:10px;overflow:visible}
  .pass::after{display:none}
  .pass-head{height:auto;background:none!important;color:#000;box-shadow:none;border-bottom:1px dashed #888}
  .price{margin-top:6pt}
  .badge{border:1px solid #000}
  .sec.foot{display:none}
  .regua,.cmp,section.s,.host,.legal{break-inside:avoid-page}
  .cmp-grid>.cmp-head{position:static}
  .s h2{font-size:15pt}
  a{text-decoration:none}
  .tabs{display:none}
}
"""
