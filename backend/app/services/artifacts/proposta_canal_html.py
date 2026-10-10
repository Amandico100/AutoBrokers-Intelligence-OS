"""A página do CANAL comparador — o link que o canal manda ao consumidor. SPEC-133-A · F3 · D-133A-09.

A marca do CANAL por fora (o símbolo e o nome que a config dá — D-MC-55/RT-10: o nome é CONFIGURAÇÃO, nunca constante
deste arquivo) e a corretora vencedora DENTRO, como um hotel dentro do comparador (D-130A1-08). A página da CARTEIRA
(`proposta_html.render_proposta`) não muda e nunca fala do canal; `templates._renderizar_proposta` escolhe esta só
quando `modelo["origem"] == "canal"`.

```
render_proposta_do_canal     modelo (CONTRATO §5, origem canal) -> str (o documento inteiro)
previa_do_canal              og:* e o PNG da prévia no canal — sem dado pessoal (nem nome, nem carro)
destino_do_fechar_do_canal   o wa.me de VOLTA À CONVERSA do canal (`canal.whatsapp` do modelo); sem número -> None
```

🔴 O que esta página NUNCA diz (D-130A1-15, Founder 07/10): quantas corretoras foram comparadas — nem em texto, nem
em quantidade de linhas — e nenhum nome de corretora perdedora. O duelo entre corretoras da carteira não entra.

O SCRIPT é o MESMO da carteira (`proposta_html.SCRIPT_DA_PROPOSTA`, o hash da CSP não muda e `service.py` fica
intocado). Esta página não tem o `#track` da carteira: o script só tira a classe `no-js` e sai. Tudo funciona sem ele —
os cartões são um carrossel de CSS (`.ops`, scroll-snap; lado a lado em grade a partir de 880 px — SPEC-133-A.1), o comparar e as dúvidas são `<details>`, o "Quero fechar" é um link comum (`?fechar=`), o
mesmo redirecionamento medido (`share.clicked`) da carteira.

As frases que a mensagem do canal também diz (a parcela em destaque, o tempo até o teto, "Corretoras de Nível 5", os
anos de mercado) vêm das MESMAS funções de `multicalculo/mensagem.py` — uma regra só para o balão e para a página.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import quote

from . import proposta_apresentacao as AP
from . import proposta_html as PH
from .proposta_estilo import _font_face

#: 💭 Os 5 itens do "Corretora Nível 5" — o RASCUNHO do programa (PRONTIDAO-DA-133-A §8, para o Founder lapidar;
#: D-130A1-04: a lista tem de estar escrita e pública antes de abrir ao público). O modelo pode trazer a própria lista
#: (`canal.selo_criterios`: [[título, detalhe], …]) — vence esta.
CRITERIOS_DO_NIVEL_5 = (
    ("Registro ativo na SUSEP", "conferido no cadastro e na consulta pública."),
    ("Cota em todas as seguradoras que aceitam o seu perfil", "o multicálculo prova, a cada pedido."),
    ("Responde na hora, 24 horas", "o agente da corretora atende; a pessoa da corretora assume no horário dela."),
    ("Acompanha o sinistro do aviso ao fim", "cada passo fica registrado."),
    ("Reputação pública conferida", "Google e Reclame Aqui lidos e respondidos — a nota aparece como está, sem filtro."),
)
#: a versão da lista acima (sobe quando o texto muda — o consumidor vê qual lista valia)
VERSAO_DOS_CRITERIOS = 1


# =====================================================================================================================
# o modelo -> o que a página lê
# =====================================================================================================================
def _msg():
    """`multicalculo/mensagem.py` — import TARDIO (como `AP.nome_do_canal`): `templates.py` é carregado sozinho por
    guardas do catálogo, e a carteira nunca precisa dele."""
    from app.services.multicalculo import mensagem
    return mensagem


def _com_preco(modelo: dict) -> list[dict]:
    """As opções na ORDEM do modelo, só as que têm id e preço (a 1ª é a do balão "Quem cobra menos?"). Até 4 (o Founder,
    10/10: "as 3 ou 4 opções" lado a lado — hoje a comparação entrega 2 a 3)."""
    return [o for o in PH._opcoes(modelo) if AP.dec(o.get("premio_anual")) is not None][:4]


def _nome_do_canal(modelo: dict) -> str:
    return AP.nome_do_canal(modelo)


def _digitos_do_canal(modelo: dict) -> Optional[str]:
    """O WhatsApp da CONVERSA do canal (`canal.whatsapp`: dígitos, `+55 …` ou `https://wa.me/…`). Nunca o da corretora:
    no canal o "Quero fechar" volta à conversa de onde a pessoa veio (D-133A-13)."""
    canal = (modelo or {}).get("canal") if isinstance((modelo or {}).get("canal"), dict) else {}
    bruto = str(canal.get("whatsapp") or "").strip()
    m = re.fullmatch(r"https://(?:wa\.me/|api\.whatsapp\.com/send\?phone=)\+?(\d{10,15})/?", bruto)
    dig = m.group(1) if m else re.sub(r"[\s()+.-]", "", bruto)
    return dig if re.fullmatch(r"\d{10,15}", dig or "") else None


def _parcela(o: dict) -> Optional[tuple[str, str]]:
    """("12x de", "R$ 345,82") — a MENOR parcela da oferta, pela mesma regra do balão (`mensagem._parcela_em_destaque`)."""
    t = _msg()._parcela_em_destaque(o)
    m = re.fullmatch(r"(\d+x de) \*(.+)\*", t or "")
    return (m.group(1), m.group(2)) if m else None


def _menor_parcela_do_cartao(o: dict) -> Optional[tuple[int, str, Optional[bool]]]:
    """(vezes, "R$ 412,02", sem_juros) — a MESMA menor parcela do balão (`_parcela`) e se ela tem juros, lido do
    parcelamento da oferta que a produziu (`parcela_menor`, `parcelas_sem_juros` ou `parcelas`). Sem como saber → None
    no terceiro campo (a página não afirma nem um nem outro). SPEC-133-A.1 F1."""
    pc = _parcela(o)
    if not pc:
        return None
    vezes = int(pc[0].split("x")[0])
    M = _msg()
    sj: Optional[bool] = None
    for chave in ("parcela_menor", "parcela_sem_juros_maior", "parcelas_sem_juros", "parcelas"):
        p = o.get(chave)
        if not isinstance(p, dict):
            continue
        try:
            igual = int(p.get("vezes")) == vezes and M._brl(float(p.get("valor"))) == pc[1]
        except (TypeError, ValueError):
            continue
        if not igual:
            continue
        if chave == "parcela_menor" and isinstance(p.get("sem_juros"), bool):
            sj = p["sem_juros"]
        elif chave in ("parcela_sem_juros_maior", "parcelas_sem_juros"):
            sj = True
        else:
            total, anual = AP.dec(p.get("total")), AP.dec(o.get("premio_anual"))
            if total is not None and anual is not None and anual > 0:   # a régua de `proposta._e_sem_juros`
                sj = float(total) - float(anual) <= max(1.0, float(anual) * 0.0025)
        if sj is not None:
            break
    return vezes, pc[1], sj


def _maior_sem_juros(o: dict) -> Optional[tuple[int, str]]:
    """(vezes, "R$ 841,12") — o MAIOR parcelamento sem juros que a seguradora mandou: `parcela_sem_juros_maior` (a
    régua do canal, que não confunde centavo de arredondamento com juros) e, num modelo de antes, `parcelas_sem_juros`.
    Sem ele → None (a linha some)."""
    p = o.get("parcela_sem_juros_maior") or o.get("parcelas_sem_juros")
    try:
        vezes, valor = int(p.get("vezes")), float(p.get("valor"))
    except (AttributeError, TypeError, ValueError):
        return None
    return (vezes, _msg()._brl(valor)) if vezes > 1 and valor > 0 else None


def _selo(modelo: dict) -> str:
    return str(PH._anfitria(modelo).get("selo") or "").strip()


def _nivel(selo: str) -> str:
    """"Corretora Nível 5" -> "Nível 5" (o nome do selo SEM a palavra "Corretora")."""
    m = re.match(r"^corretora\s+(.+)$", selo, re.I)
    return m.group(1).strip() if m else selo


def _susep(anf: dict) -> str:
    return re.sub(r"^\s*susep\b[\s:nº°.#-]*", "", str(anf.get("susep") or ""), flags=re.I).strip()


def _economia(modelo: dict) -> Optional[dict]:
    resumo = modelo.get("resumo") if isinstance(modelo.get("resumo"), dict) else {}
    eco = resumo.get("economia") if isinstance(resumo.get("economia"), dict) else None
    ate = AP.dec((eco or {}).get("ate"))
    if ate is None or AP.reais(ate) < 1:
        return None
    return eco


def _volume(modelo: dict) -> Optional[str]:
    """ "Fiz <b>188 cotações</b> entre Corretoras de Nível 5 e <b>19 seguradoras</b> em <b>1,5 minutos</b>." — a copy
    do Founder (D-130A1-15), com os números do modelo; linha sem dado some; NUNCA o número de corretoras."""
    M = _msg()
    resumo = modelo.get("resumo") if isinstance(modelo.get("resumo"), dict) else {}
    vol = resumo.get("volume_do_canal") if isinstance(resumo.get("volume_do_canal"), dict) else {}
    n, segs = M._n(vol.get("total")), M._n(resumo.get("seguradoras_consultadas"))
    if not n:
        return None
    entre = [x for x in (PH._e(M._entre_quem(modelo)) if M._entre_quem(modelo) else None,
                         f"<b>{segs} seguradora{'s' if segs != 1 else ''}</b>" if segs else None) if x]
    canal = modelo.get("canal") if isinstance(modelo.get("canal"), dict) else {}
    t = M._tempo_que_se_mostra(resumo.get("tempo_do_calculo_s"), {"canal": canal})
    return (f"Fiz <b>{n} {'cotação' if n == 1 else 'cotações'}</b>" + (f" entre {' e '.join(entre)}" if entre else "")
            + (f" em <b>{PH._e(t)}</b>" if t else "") + ".")


def previa_do_canal(modelo: dict) -> dict:
    """O que a prévia do link DO CANAL diz (og:* e o PNG). As mesmas chaves de `proposta_html.previa_do_modelo` (o PNG
    as lê) e mais `marca_do_canal`. 🔴 Sem dado pessoal: nem o primeiro nome, nem o carro, nem a placa — a prévia aparece
    na conversa para quem olhar a tela e viaja com quem encaminha."""
    base = PH.previa_do_modelo(modelo)
    nome = _nome_do_canal(modelo)
    ops = _com_preco(modelo)
    rec = ops[0] if ops else {}
    resumo = modelo.get("resumo") if isinstance(modelo.get("resumo"), dict) else {}
    vol = resumo.get("volume_do_canal") if isinstance(resumo.get("volume_do_canal"), dict) else {}
    M = _msg()
    n, segs = M._n(vol.get("total")), M._n(resumo.get("seguradoras_consultadas"))
    seg = str(rec.get("seguradora") or "").strip()
    preco = PH._brl(rec.get("premio_anual"))
    titulo = f"Descobrimos {nome} no seu seguro" + (f": {seg} por {preco} ao ano" if seg and preco else "")
    partes = []
    if n:
        partes.append(f"{n} {'cotação' if n == 1 else 'cotações'}"
                      + (f" em {segs} seguradora{'s' if segs != 1 else ''}" if segs else "") + ".")
    eco = _economia(modelo)
    if eco:
        partes.append(f"Economia de até {PH._brl(AP.reais(eco['ate'])).replace(',00', '')} por ano.")
    if base["validade"]:
        partes.append(f"Válida até {base['validade']}.")
    base.update({
        "titulo": titulo,
        "descricao": " ".join(partes) or "As opções que separamos para você.",
        "manchete": f"Descobrimos {nome} no seu seguro",
        "rotulo": "Quem cobra menos" if seg else base["rotulo"],
        "comparadas": None,
        "corretoras": None,
        "cotacoes": n,
        "seguradoras": segs,
        "canal": nome,
        "marca_do_canal": nome,
    })
    return base


# =====================================================================================================================
# a marca do canal (SVG inline, decorativo — o nome vai em texto ao lado)
# =====================================================================================================================
#: o rabo do "Q" (caixa 100×100). Medido sobre a imagem de referência do Founder (07/10): o anel grosso (raio externo
#: 42, interno ≈ 22) e o rabo diagonal que entra no furo e sai pela direita de baixo, com uma fresta entre os dois.
_RABO = "M50.4 47.6 L50.9 73.2 L60.1 87.1 L90.3 87.1 Z"


def simbolo(uid: str, classe: str = "q") -> str:
    """O "Q" do canal: o anel (cor `--ring`: marinho no claro, quase branco no escuro) e o rabo verde-limão. A fresta
    é uma MÁSCARA (não um traço da cor do fundo): o símbolo fica certo sobre qualquer fundo."""
    return (f'<svg class="{classe}" viewBox="0 0 100 100" aria-hidden="true" focusable="false">'
            f'<defs><mask id="{uid}" maskUnits="userSpaceOnUse" x="0" y="0" width="100" height="100">'
            f'<rect width="100" height="100" fill="#fff"/><path d="{_RABO}" fill="#000" stroke="#000" stroke-width="7" '
            f'stroke-linejoin="round"/></mask></defs>'
            f'<circle class="q-ring" cx="50" cy="50" r="31.8" fill="none" stroke-width="20.4" mask="url(#{uid})"/>'
            f'<path class="q-tail" d="{_RABO}" stroke-width="3.2" stroke-linejoin="round"/></svg>')


def _selo_do_programa(nivel: str) -> str:
    """O selo de certificação do programa (o "ISO" do Founder): anel duplo, o nível no centro."""
    num = re.search(r"(\d+)\s*$", nivel)
    centro = (f'<text x="60" y="80" text-anchor="middle" class="s5-num">{PH._e(num.group(1))}</text>' if num else
              '<path d="M42 62l12 12 24-26" fill="none" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" '
              'class="s5-ok"/>')
    palavra = PH._e((nivel[: num.start()] if num else "").strip().upper()[:10])
    return ('<svg class="s5" viewBox="0 0 120 120" aria-hidden="true" focusable="false">'
            '<circle cx="60" cy="60" r="57" class="s5-out"/><circle cx="60" cy="60" r="49" class="s5-in"/>'
            '<circle cx="60" cy="60" r="44" class="s5-line" fill="none" stroke-width="1.6" stroke-dasharray="2 3.2"/>'
            + (f'<text x="60" y="44" text-anchor="middle" class="s5-word">{palavra}</text>' if palavra else "")
            + centro + "</svg>")


# =====================================================================================================================
# o CSS da página do canal (tokens no :root, claro e escuro, mobile primeiro)
# =====================================================================================================================
_FONTE = _font_face()

CSS_DO_CANAL = _FONTE + r"""
:root{
  --navy:#1B3756;--lime:#D6F25C;--on-lime:#1B3756;
  --canvas:#F4F7F6;--surface:#FFFFFF;--surface-2:#EDF2F1;--ink-strong:#0F2236;--ink:#2A3A4A;--ink-muted:#526272;
  --line:#DCE3E7;--line-strong:#BFCAD2;--ring:#1B3756;--hero:#1B3756;--hero-on:#FFFFFF;--hero-muted:#C9D5E0;
  --pos:#0E7646;--pos-bg:#E2F3E9;--neg:#9B3A48;--neg-bg:#F8E8EB;--focus:#1B3756;--shadow:15 34 54;
  --font:'Instrument Sans',ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --canvas:#0B1520;--surface:#122030;--surface-2:#182A3C;--ink-strong:#F2F6F9;--ink:#D5DEE6;--ink-muted:#A2B3C2;
  --line:#22364A;--line-strong:#36516B;--ring:#E9EFF4;--hero:#183552;--hero-on:#FFFFFF;--hero-muted:#BCCCDB;
  --pos:#5DD39B;--pos-bg:#0D3122;--neg:#F0909C;--neg-bg:#3A1A20;--focus:#D6F25C;--shadow:0 0 0;color-scheme:dark}}
:root[data-theme="dark"]{
  --canvas:#0B1520;--surface:#122030;--surface-2:#182A3C;--ink-strong:#F2F6F9;--ink:#D5DEE6;--ink-muted:#A2B3C2;
  --line:#22364A;--line-strong:#36516B;--ring:#E9EFF4;--hero:#183552;--hero-on:#FFFFFF;--hero-muted:#BCCCDB;
  --pos:#5DD39B;--pos-bg:#0D3122;--neg:#F0909C;--neg-bg:#3A1A20;--focus:#D6F25C;--shadow:0 0 0;color-scheme:dark}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
html,body{overflow-x:clip}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:var(--font);font-size:16px;line-height:1.5;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
img{display:block;max-width:100%}
a{color:inherit}
h1,h2,h3,h4,p{margin:0}
:focus-visible{outline:3px solid var(--focus);outline-offset:3px;border-radius:8px}
summary{cursor:pointer;list-style:none}
summary::-webkit-details-marker{display:none}
summary svg{width:18px;height:18px;flex:none;transition:transform .2s}
details[open]>summary svg{transform:rotate(180deg)}
.wrap{max-width:1080px;margin:0 auto;padding-left:16px;padding-right:16px}
.q-ring{stroke:var(--ring)}.q-tail{fill:var(--lime);stroke:var(--lime)}

/* topo: a marca do canal */
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:14px;padding-bottom:6px}
.qcm{display:inline-flex;align-items:center;gap:9px;color:var(--ink-strong);text-decoration:none;min-height:44px}
.qcm .q{width:36px;height:36px;flex:none}
.qcm b{font-weight:700;font-size:19px;letter-spacing:-.025em;line-height:1.05}
.indep{font-size:12.5px;line-height:1.25;color:var(--ink-muted);text-align:right;max-width:13ch}

/* o resultado */
.hero{padding-top:10px;padding-bottom:6px;display:grid;gap:16px}
.hi{font-size:15px;color:var(--ink-muted);font-weight:500}
.hero h1{margin-top:2px;font-size:30px;line-height:1.06;font-weight:700;letter-spacing:-.03em;color:var(--ink-strong);
  font-variation-settings:'wdth' 90;text-wrap:balance}
.hero h1 .nm{background:linear-gradient(transparent 62%,var(--lime) 62%,var(--lime) 92%,transparent 92%);padding:0 2px;
  -webkit-box-decoration-break:clone;box-decoration-break:clone}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .hero h1 .nm{background:none;color:var(--lime)}}
:root[data-theme="dark"] .hero h1 .nm{background:none;color:var(--lime)}
.carro{margin-top:8px;font-size:14px;color:var(--ink-muted)}
.vol{margin-top:12px;font-size:16.5px;line-height:1.4;color:var(--ink)}
.vol b{color:var(--ink-strong);font-weight:700}
.eco{margin-top:14px;padding:14px 16px;border-radius:16px;background:var(--lime);color:var(--on-lime)}
.eco .l{display:block;font-size:15px;font-weight:600}
.eco .v{display:flex;align-items:baseline;gap:8px;margin-top:2px}
.eco b{font-size:38px;line-height:1.05;font-weight:700;letter-spacing:-.03em;font-variation-settings:'wdth' 90}
.eco .v span{font-size:16px;font-weight:600}
.eco small{display:block;font-size:13px;line-height:1.35;font-weight:500;margin-top:6px}

/* o vencedor */
.win{position:relative;background:var(--hero);color:var(--hero-on);border-radius:22px;padding:20px 18px 18px;
  box-shadow:0 18px 40px -22px rgb(var(--shadow)/.55)}
.win-tag{display:inline-flex;align-items:center;gap:6px;background:var(--lime);color:var(--on-lime);font-weight:700;
  font-size:13px;letter-spacing:.02em;text-transform:uppercase;border-radius:999px;padding:4px 11px}
.win h2{margin-top:12px;font-size:21px;line-height:1.2;font-weight:600;letter-spacing:-.015em;text-wrap:balance}
.win h2 b{font-weight:700}
.win .logo{position:absolute;top:16px;right:16px;background:#fff;border-radius:10px;padding:5px 8px}
.win .logo img{height:26px;width:auto;max-width:110px;object-fit:contain}
.parc{margin-top:14px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.parc .x{font-size:17px;color:var(--hero-muted);font-weight:500}
.parc b{font-size:44px;line-height:1;font-weight:700;letter-spacing:-.035em;font-variation-settings:'wdth' 88}
.ano{margin-top:6px;font-size:15px;color:var(--hero-muted)}
.ano strong{color:var(--hero-on);font-weight:600}
.cta{display:flex;align-items:center;justify-content:center;gap:9px;min-height:52px;margin-top:16px;padding:10px 18px;
  border-radius:14px;background:var(--lime);color:var(--on-lime);font-weight:700;font-size:17px;text-decoration:none}
.cta svg{width:20px;height:20px;flex:none}
.cta .t{display:flex;flex-direction:column;line-height:1.15;text-align:left}
.cta .t small{font-weight:500;font-size:13px}
.win .valid{margin-top:10px;font-size:13px;color:var(--hero-muted);text-align:center}

/* seções */
.s{margin-top:34px}
.s>h2{font-size:23px;line-height:1.15;font-weight:700;letter-spacing:-.02em;color:var(--ink-strong);text-wrap:balance}
.s>.sub{margin-top:6px;font-size:15px;color:var(--ink-muted);max-width:62ch}

/* as opções — SPEC-133-A.1 (Founder 10/10): LADO A LADO em carrossel. No celular arrasta para o lado (scroll-snap de
   CSS, sem script) e o próximo cartão aparece na borda; do computador (≥ 880 px) os cartões ficam lado a lado em grade */
.ops{margin:14px -16px 0;display:flex;gap:12px;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x mandatory;
  scroll-padding-inline:16px;padding:4px 16px 14px;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.ops::-webkit-scrollbar{display:none}
.ops:focus-visible{outline:2px solid var(--focus);outline-offset:-2px;border-radius:18px}
.ops>.op{flex:0 0 min(320px, calc(100% - 52px));scroll-snap-align:start;scroll-snap-stop:always}
.ops>.op:last-child{scroll-snap-align:end}
.ops.um>.op{flex-basis:100%}
.arraste{margin-top:10px;font-size:13.5px;color:var(--ink-muted);display:flex;align-items:center;gap:6px}
.arraste svg{width:16px;height:16px;flex:none}
.op{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px;display:flex;flex-direction:column;gap:10px}
.op.rec{border:2px solid var(--navy);box-shadow:0 10px 28px -18px rgb(var(--shadow)/.6)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .op.rec{border-color:var(--lime)}}
:root[data-theme="dark"] .op.rec{border-color:var(--lime)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .op.rec .badge{background:var(--lime);color:var(--on-lime)}}
:root[data-theme="dark"] .op.rec .badge{background:var(--lime);color:var(--on-lime)}
.op-h{display:flex;align-items:center;justify-content:space-between;gap:10px}
.badge{display:inline-block;font-size:13px;font-weight:700;border-radius:999px;padding:3px 10px;background:var(--surface-2);color:var(--ink-strong)}
.op.rec .badge{background:var(--navy);color:#fff}
.nota{font-size:13px;color:var(--ink-muted);white-space:nowrap}
.nota b{font-size:20px;color:var(--ink-strong);font-weight:700}
.seg{font-size:19px;font-weight:700;color:var(--ink-strong);line-height:1.2}
.seg span{display:block;font-size:14px;font-weight:500;color:var(--ink-muted)}
.op-p{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.op-p .x{font-size:15px;color:var(--ink-muted)}
.op-p b{font-size:28px;line-height:1.05;font-weight:700;color:var(--ink-strong);letter-spacing:-.025em}
.op-p .j{font-size:13px;font-weight:600;color:var(--ink-muted)}
.op-a{font-size:14.5px;color:var(--ink-muted)}
.op-a strong{color:var(--ink-strong);font-weight:600}
.meter{height:6px;border-radius:99px;background:var(--surface-2);overflow:hidden}
.meter i{display:block;height:100%;border-radius:99px;background:var(--navy)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .meter i{background:var(--lime)}}
:root[data-theme="dark"] .meter i{background:var(--lime)}
.mh{font-size:12.5px;color:var(--ink-muted);margin-top:-4px}
.why{margin:0;padding:0;list-style:none;display:grid;gap:6px;font-size:14.5px}
.why li{display:flex;gap:8px;align-items:flex-start}
.why svg{width:17px;height:17px;flex:none;margin-top:2px;color:var(--pos)}
.muda{margin:0;padding:0 0 0 18px;font-size:14.5px;color:var(--ink);display:grid;gap:4px}
.muda li::marker{color:var(--ink-muted)}
.menos{font-size:14.5px;border-radius:12px;background:var(--neg-bg);color:var(--ink);padding:10px 12px}
.menos b{display:block;color:var(--neg);font-size:13px;text-transform:uppercase;letter-spacing:.03em;margin-bottom:2px}
.covs summary{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:14.5px;font-weight:600;
  color:var(--ink-strong);min-height:44px;border-top:1px solid var(--line)}
.covs ul{margin:0 0 4px;padding:0;list-style:none;display:grid;gap:8px;font-size:14px}
.covs li{display:grid;grid-template-columns:20px 1fr;gap:2px 8px}
.covs li svg{width:18px;height:18px;color:var(--ink-muted);grid-row:span 2}
.covs .cn{color:var(--ink-muted);font-size:13px}
.covs .cv{color:var(--ink-strong);overflow-wrap:anywhere}
.covs .tg{font-size:12px;font-weight:600;margin-left:6px;white-space:nowrap}
.tg.up{color:var(--pos)}.tg.down{color:var(--neg)}
.want{margin-top:auto;display:flex;align-items:center;justify-content:center;gap:8px;min-height:50px;padding:10px 18px;
  border-radius:13px;border:1.5px solid var(--navy);color:var(--navy);font-weight:700;text-decoration:none;font-size:16px}
.op.rec .want{background:var(--navy);color:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .want{border-color:var(--lime);color:var(--lime)}
  :root:not([data-theme="light"]) .op.rec .want{background:var(--lime);color:var(--on-lime)}}
:root[data-theme="dark"] .want{border-color:var(--lime);color:var(--lime)}
:root[data-theme="dark"] .op.rec .want{background:var(--lime);color:var(--on-lime)}
.want svg{width:19px;height:19px}

/* comparar lado a lado */
.cmp{margin-top:12px;background:var(--surface);border:1px solid var(--line);border-radius:16px}
.cmp>summary{display:flex;align-items:center;gap:10px;padding:12px 16px;min-height:52px;font-weight:700;color:var(--ink-strong)}
.cmp>summary span{flex:1}
.cmp-in{padding:0 12px 12px}
.cmp-row{border-top:1px solid var(--line);padding:9px 2px}
.cmp-row h4{font-size:12.5px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.03em}
.cmp-cells{display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:8px;margin-top:3px;font-size:14px;color:var(--ink-strong)}
.cmp-cells>div{overflow-wrap:anywhere}
.cmp-head .cmp-cells>div{font-weight:700}
.cmp-head .cmp-cells small{display:block;font-weight:500;color:var(--ink-muted);font-size:12.5px}

/* a corretora */
.host{margin-top:14px;background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:18px}
.host-id{display:flex;align-items:center;gap:14px}
.plate{background:#fff;border-radius:12px;padding:6px 10px;border:1px solid var(--line);flex:none}
.plate img{height:34px;width:auto;max-width:112px;object-fit:contain}
.mono{width:52px;height:52px;border-radius:14px;background:var(--navy);color:#fff;display:grid;place-items:center;font-weight:700;font-size:19px;flex:none}
.host h3{font-size:20px;line-height:1.2;color:var(--ink-strong);font-weight:700}
.host-id p{font-size:14px;color:var(--ink-muted)}
.n5ok{margin-top:14px;display:inline-flex;align-items:center;gap:8px;font-weight:700;color:var(--ink-strong);font-size:15.5px;
  background:var(--pos-bg);border-radius:999px;padding:5px 13px 5px 6px}
.n5ok svg{width:22px;height:22px;flex:none}
.n5ok .ck{fill:var(--pos)}
.facts{margin:14px 0 0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.facts li{background:var(--surface-2);border-radius:12px;padding:10px 12px;display:flex;flex-direction:column;gap:1px;min-width:0}
.facts b{font-size:18px;color:var(--ink-strong);font-weight:700;display:flex;align-items:center;gap:5px;overflow-wrap:anywhere}
.facts b svg{width:16px;height:16px;color:#C98A00;flex:none}
.facts span{font-size:13px;color:var(--ink-muted)}
.facts a{color:var(--ink-strong);font-weight:700;font-size:15px;overflow-wrap:anywhere;text-underline-offset:3px}
.src{margin-top:10px;font-size:12.5px;color:var(--ink-muted)}
.what{margin-top:12px;font-size:14px;color:var(--ink)}

/* o selo do programa */
.n5{margin-top:34px;border-radius:22px;padding:22px 18px;background:var(--surface);border:1px solid var(--line);
  display:grid;gap:14px;justify-items:start}
.s5{width:104px;height:104px}
.s5-out{fill:var(--navy)}.s5-in{fill:var(--navy);stroke:var(--lime);stroke-width:3}.s5-line{stroke:var(--lime)}
.s5-word{fill:var(--lime);font:700 12px var(--font);letter-spacing:2px}
.s5-num{fill:#fff;font:700 44px var(--font)}.s5-ok{stroke:#fff}
.n5 h2{font-size:23px;line-height:1.15;font-weight:700;letter-spacing:-.02em;color:var(--ink-strong)}
.n5 .sub{margin-top:6px;font-size:15px;color:var(--ink-muted)}
.n5 ol{margin:0;padding:0;list-style:none;display:grid;gap:10px;counter-reset:n}
.n5 li{counter-increment:n;display:grid;grid-template-columns:30px 1fr;gap:10px;font-size:15px;align-items:start}
.n5 li::before{content:counter(n);width:30px;height:30px;border-radius:50%;display:grid;place-items:center;
  background:var(--lime);color:var(--on-lime);font-weight:700;font-size:14px}
.n5 li b{color:var(--ink-strong);font-weight:700}
.n5-v{font-size:12.5px;color:var(--ink-muted)}

/* melhor preço por seguradora */
.rank{margin:14px 0 0;padding:0;list-style:none;background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.rank li{display:grid;grid-template-columns:28px 1fr auto;gap:2px 10px;align-items:baseline;padding:11px 14px;border-top:1px solid var(--line)}
.rank li:first-child{border-top:0}
.rank .n{font-size:13px;color:var(--ink-muted);font-weight:600}
.rank .nm{font-weight:600;color:var(--ink-strong);min-width:0;overflow-wrap:anywhere}
.rank .pr{font-weight:700;color:var(--ink-strong);white-space:nowrap}
.rank .meta{grid-column:2/4;font-size:13px;color:var(--ink-muted)}
.rank li.top{background:var(--pos-bg)}
.rank .tag{display:inline-block;margin-left:8px;font-size:12px;font-weight:700;color:var(--pos);white-space:nowrap}
.note{margin-top:10px;font-size:14px;color:var(--ink-muted)}
.others{margin-top:10px;display:grid;gap:8px}
.line{background:var(--surface);border:1px solid var(--line);border-radius:14px}
.line>summary{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px;min-height:48px;font-size:14.5px}
.line ul{margin:0;padding:0 14px 12px 32px;font-size:14px;display:grid;gap:6px}
.line-static{font-size:14px;color:var(--ink-muted)}

/* dúvidas, sinistro, rodapé */
.faq{margin-top:12px;background:var(--surface);border:1px solid var(--line);border-radius:16px}
.faq details+details{border-top:1px solid var(--line)}
.faq summary{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;min-height:52px;
  font-weight:600;color:var(--ink-strong);font-size:15.5px}
.faq p{padding:0 16px 14px;font-size:15px}
.steps{margin:14px 0 0;padding:0;list-style:none;display:grid;gap:10px;counter-reset:p}
.steps li{counter-increment:p;display:grid;grid-template-columns:30px 1fr;gap:10px;align-items:center;font-size:15px}
.steps li::before{content:counter(p);width:30px;height:30px;border-radius:50%;display:grid;place-items:center;
  border:1.5px solid var(--line-strong);font-weight:700;font-size:14px;color:var(--ink-strong)}
.fim{background:var(--hero);color:var(--hero-on);border-radius:22px;padding:22px 18px}
.fim>h2{color:var(--hero-on)}
.fim>.sub{color:var(--hero-muted)}
.ask{display:block;margin-top:12px;text-align:center;color:var(--hero-on);font-weight:600;font-size:15px;min-height:44px;line-height:44px}
.legal{margin-top:30px;padding-top:14px;border-top:1px solid var(--line);font-size:12.5px;color:var(--ink-muted);display:grid;gap:6px}
.legal .valid{font-weight:600;color:var(--ink)}
.endpad{height:96px}
.dock{position:fixed;left:0;right:0;bottom:0;z-index:20;background:var(--canvas);border-top:1px solid var(--line);
  padding:10px 16px calc(10px + env(safe-area-inset-bottom))}
.dock .cta{margin:0 auto;max-width:520px;background:var(--navy);color:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .dock .cta{background:var(--lime);color:var(--on-lime)}}
:root[data-theme="dark"] .dock .cta{background:var(--lime);color:var(--on-lime)}

@media (min-width:640px){
  .hero h1{font-size:40px}
  .facts{grid-template-columns:repeat(4,minmax(0,1fr))}
  .n5{grid-template-columns:120px 1fr;column-gap:24px;align-items:start;padding:28px}
  .n5 .s5{width:120px;height:120px;grid-row:span 3}
}
@media (min-width:880px){
  .ops{display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));overflow:visible;margin:14px 0 0;padding:0}
  .ops>.op{flex:none}
  .arraste{display:none}
}
@media (min-width:960px){
  .hero{grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);gap:32px;align-items:center;padding-top:22px}
  .hero h1{font-size:48px}
  .win{padding:26px 24px 22px}
  .dock{display:none}
  .endpad{height:24px}
}
@media (prefers-reduced-motion:no-preference){.op,.win{animation:sobe .45s ease-out both}
  @keyframes sobe{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}}
@media print{.dock,.cta,.want,.arraste{display:none!important}.endpad{height:0}body{background:#fff}
  .ops{display:block;overflow:visible;margin:14px 0 0;padding:0}.ops>.op{margin-bottom:12px;break-inside:avoid}}
"""


# =====================================================================================================================
# peças
# =====================================================================================================================
def _cartao(o: dict, i: int, rec: dict, barata: Optional[dict], modelo: dict, href: str) -> str:
    rotulo = str(o.get("rotulo") or o.get("id"))
    produto = AP.sem_seguradora(o.get("produto"), o.get("seguradora"))
    nota = AP.numero_inteiro(o.get("nota"))
    nota_html = (f'<span class="nota" title="nota do comparador, de 0 a 100"><b>{nota}</b>/100</span>'
                 if nota is not None and 0 <= nota <= 100 else "")
    preco = PH._e(AP.brl(o.get("premio_anual")))
    # SPEC-133-A.1 (Founder 10/10, só o QCM — D-133A1-01), NESTA ORDEM: (a) a MENOR parcela da oferta no topo, (b) o
    # preço à vista, (c) o MAIOR parcelamento SEM juros que a seguradora mandou. Só dado da oferta; linha sem dado some;
    # (c) some quando é a mesma parcela de (a) — aí (a) já diz "sem juros". Revoga, no canal, o "anual na frente".
    menor, sem_juros = _menor_parcela_do_cartao(o), _maior_sem_juros(o)
    if menor:
        vezes, valor, sj = menor
        juros = {True: "sem juros", False: "com juros"}.get(sj)
        cabeca = (f'<p class="op-p op-menor"><span class="x">{vezes}x de</span><b>{PH._e(AP.nbsp(valor))}</b>'
                  + (f'<span class="j">{juros}</span>' if juros else "") + "</p>"
                  f'<p class="op-a op-vista"><strong>{preco}</strong> à vista</p>')
        if sem_juros and (sem_juros[0], sem_juros[1]) != (vezes, valor):
            cabeca += (f'<p class="op-a op-sj">ou <strong>{sem_juros[0]}x sem juros</strong> de '
                       f'{PH._e(AP.nbsp(sem_juros[1]))}</p>')
    else:
        cabeca = f'<p class="op-p op-vista"><b>{preco}</b><span class="x">à vista</span></p>'
    fq = o.get("franquia") if isinstance(o.get("franquia"), dict) else {}
    if AP.brl(fq.get("valor")):
        tipo = str(fq.get("tipo") or "").strip().lower()
        cabeca += f'<p class="op-a">Franquia{" " + PH._e(tipo) if tipo else ""}: <strong>{PH._e(AP.brl(fq["valor"], False))}</strong></p>'
    medidor = (f'<div class="meter" role="img" aria-label="nota {nota} de 100"><i style="width:{nota}%"></i></div>'
               if nota is not None and 0 <= nota <= 100 else "")
    corpo = ""
    if barata is not None and o is barata:
        pq = str(o.get("por_que_mais_barata") or "").strip()
        itens = [str(x).strip().rstrip(".") for x in o.get("o_que_muda") or []
                 if str(x).strip() and not str(x).startswith("R$") and not str(x).startswith("Seguradora ")]
        texto = pq or (", ".join(i[:1].lower() + i[1:] for i in itens).capitalize() + "." if itens else "")
        if texto:
            corpo = f'<div class="menos"><b>O que deixa de cobrir</b>{PH._e(AP.nbsp(texto))}</div>'
    else:
        motivos = [m for m in (o.get("motivos") or []) if isinstance(m, str) and m.strip()]
        # o que MUDA em relação à 1ª é neutro (ponto, não "✓": "R$ 1.830 a mais" não é vantagem); a linha
        # "Seguradora X (na opção …)" repete o que o cartão já diz
        muda = [x for x in (o.get("o_que_muda") or []) if isinstance(x, str) and x.strip()
                and not x.strip().startswith("Seguradora ")] if o is not rec else []
        if muda:
            corpo += ('<ul class="muda">' + "".join(f"<li>{PH._e(AP.nbsp(m))}</li>" for m in muda[:3]) + "</ul>")
        if motivos:
            corpo += ('<ul class="why">' + "".join(f'<li>{PH.ICO["check"]}<span>{PH._e(AP.nbsp(m))}</span></li>'
                                                   for m in motivos[:2 if muda else 3]) + "</ul>")
    covs = []
    for c in o.get("coberturas") or []:
        if not isinstance(c, dict) or AP.cobertura(o, c.get("chave")) is None:
            continue
        kind, _nota = AP.comparar_cobertura(c["chave"], o, rec)
        tag = (f'<span class="tg {"up" if kind == "melhor" else "down"}">{PH._e(kind)}</span>' if kind else "")
        covs.append(f'<li>{PH.ICO.get(c["chave"], PH.ICO["check"])}<span class="cn">{PH._e(AP.nbsp(c["nome"]))}</span>'
                    f'<span class="cv">{PH._e(AP.nbsp(AP.valor_da_cobertura(c)))}{tag}</span></li>')
    detalhes = (f'<details class="covs"><summary><span>Ver as {len(covs)} coberturas</span>{PH.ICO["chev"]}</summary>'
                f'<ul>{"".join(covs)}</ul></details>' if covs else "")
    want = (f'<a class="want" href="{PH._e(href)}" rel="nofollow">{PH.ICO["wa"]}Quero esta</a>' if href else "")
    aria = f"Opção {i + 1}: {rotulo}, {o.get('seguradora') or ''}, {PH._brl(o.get('premio_anual'))} por ano"
    return (f'<article class="op{" rec" if o is rec else ""}" data-opcao="{PH._e(o["id"])}" aria-label="{PH._e(aria)}">'
            f'<div class="op-h"><span class="badge">{PH._e(rotulo)}</span>{nota_html}</div>'
            f'<p class="seg">{PH._e(o.get("seguradora") or "")}{f"<span>{PH._e(produto)}</span>" if produto else ""}</p>'
            f'{cabeca}{medidor}{corpo}{detalhes}{want}</article>')


def _comparar(ops: list[dict]) -> str:
    if len(ops) < 2:
        return ""
    rec = ops[0]
    linhas = []

    def linha(rotulo: str, celulas: list[str], cls: str = "") -> None:
        linhas.append(f'<div class="cmp-row{cls}"><h4>{PH._e(rotulo)}</h4><div class="cmp-cells">'
                      + "".join(f"<div>{c}</div>" for c in celulas) + "</div></div>")

    linhas.append('<div class="cmp-row cmp-head"><div class="cmp-cells">'
                  + "".join(f'<div>{PH._e(o.get("seguradora") or "")}<small>{PH._e(o.get("rotulo") or o.get("id"))}</small></div>'
                            for o in ops) + "</div></div>")
    linha("Preço por ano", [PH._e(AP.brl(o.get("premio_anual"))) for o in ops])
    pcs = [_parcela(o) for o in ops]
    if any(pcs):
        linha("Menor parcela", [PH._e(f"{p[0]} {p[1]}") if p else "" for p in pcs])
    fqs = [(o.get("franquia") or {}) if isinstance(o.get("franquia"), dict) else {} for o in ops]
    if any(AP.brl(f.get("valor")) for f in fqs):
        linha("Franquia", [PH._e(AP.brl(f.get("valor"), False)) for f in fqs])
    notas = [AP.numero_inteiro(o.get("nota")) for o in ops]
    if any(n is not None for n in notas):
        linha("Nota, de 0 a 100", [str(n) if n is not None else "" for n in notas])
    for c in rec.get("coberturas") or []:
        if not isinstance(c, dict) or AP.cobertura(rec, c.get("chave")) is None:
            continue
        cs = [AP.cobertura(o, c["chave"]) for o in ops]
        linha(AP.nbsp(c["nome"]), [PH._e(AP.nbsp(AP.valor_da_cobertura(x))) if x else "—" for x in cs])
    return (f'<details class="cmp"><summary>{PH.ICO["cols"]}<span>Comparar lado a lado</span>{PH.ICO["chev"]}</summary>'
            f'<div class="cmp-in">{"".join(linhas)}</div></details>')


# =====================================================================================================================
# a página
# =====================================================================================================================
def render_proposta_do_canal(modelo: dict) -> str:
    """O documento inteiro da página do canal. Só dado do modelo; linha sem dado some; todo texto escapado."""
    modelo = modelo if isinstance(modelo, dict) else {}
    M = _msg()
    nome_canal = _nome_do_canal(modelo)
    previa = previa_do_canal(modelo)
    ops = _com_preco(modelo)
    rec = ops[0] if ops else None
    barata = M._mais_em_conta({"opcoes": ops}) if ops else None
    anf = PH._anfitria(modelo)
    nome_anf = str(anf.get("nome") or "").strip()
    logo = PH._logo(anf)
    bem = AP.o_bem(modelo)
    cliente = modelo.get("cliente") if isinstance(modelo.get("cliente"), dict) else {}
    nome = str(cliente.get("primeiro_nome") or "").strip()
    digitos = _digitos_do_canal(modelo)
    selo = _selo(modelo)
    validade = PH._data_curta(modelo.get("validade_ate"))
    sobre_o_bem = f"do {bem['apelido']}" if bem["apelido"] else "da cotação"

    def wa(texto: str) -> str:
        return f"https://wa.me/{digitos}?text={quote(texto, safe='')}" if digitos else ""

    def href_fechar(o: dict) -> str:
        return f"?{PH.PARAMETRO_DO_FECHAR}={quote(str(o['id']), safe='')}" if digitos else ""

    # ---- topo
    topo = (f'<header class="wrap top"><span class="qcm">{simbolo("qcm-m1")}<b>{PH._e(nome_canal)}</b></span>'
            f'<span class="indep">Comparador independente</span></header>')

    # ---- o resultado
    if bem["apelido"]:
        onde = f"no seguro do seu {PH._e(bem['apelido'])}"
    else:
        onde = "no seu seguro auto" if bem["e_veiculo"] else "no seu seguro"
    h1 = f'Descobrimos <span class="nm">{PH._e(nome_canal)}</span> {onde}'
    carro = ", ".join(x for x in (bem["descricao"], bem["ano"]) if x)
    vol = _volume(modelo)
    eco = _economia(modelo)
    eco_html = ""
    if eco:
        de, para = AP.dec(eco.get("de")), AP.dec(eco.get("para"))
        base = ""
        if eco.get("contra") == "atual" and de is not None:
            base = f"Comparado com o que você paga hoje: {AP.brl(de, False)} por ano."
        elif eco.get("contra") == "maior" and de is not None and para is not None:
            base = f"Do maior ao menor preço que encontramos: de {AP.brl(de, False)} para {AP.brl(para, False)} por ano."
        eco_html = (f'<p class="eco"><span class="l">Você deve economizar até</span><span class="v">'
                    f'<b>{PH._e(AP.brl(eco["ate"], False))}</b><span>por ano</span></span>'
                    f'{f"<small>{PH._e(base)}</small>" if base else ""}</p>')
    hero_txt = (f'<div class="hero-txt">{f"<p class=hi>Prontinho, {PH._e(nome)}!</p>" if nome else ""}<h1>{h1}</h1>'
                + (f'<p class="carro lede">{PH._e(carro)}</p>' if carro else "")
                + (f'<p class="vol">{vol}</p>' if vol else "") + eco_html + "</div>")

    win = ""
    if rec is not None:
        seg = str(rec.get("seguradora") or "").strip()
        quem = (f'<b>{PH._e(M._de_quem(nome_anf))}</b> com <b>{PH._e(seg)}</b>' if nome_anf else f"<b>{PH._e(seg)}</b>")
        pc = _parcela(rec)
        preco = AP.brl(rec.get("premio_anual"))
        if pc:
            valor = (f'<p class="parc"><span class="x">{PH._e(pc[0])}</span><b>{PH._e(AP.nbsp(pc[1]))}</b></p>'
                     f'<p class="ano">ou <strong>{PH._e(preco)}</strong> por ano</p>')
        else:
            valor = f'<p class="parc"><b>{PH._e(preco)}</b><span class="x">por ano</span></p>'
        sub = " · ".join(x for x in (seg, f"{pc[0]} {pc[1]}" if pc else PH._brl(rec.get("premio_anual"))) if x)
        cta = (f'<a class="cta" href="{PH._e(href_fechar(rec))}" rel="nofollow" aria-label="{PH._e("Quero fechar: " + sub)}">'
               f'{PH.ICO["wa"]}<span class="t">Quero fechar<small>volta para a nossa conversa</small></span></a>'
               if digitos else "")
        win = (f'<section class="win" aria-labelledby="h-win">'
               + (f'<span class="logo"><img src="{PH._e(logo)}" alt="" height="26"></span>' if logo else "")
               + f'<p class="win-tag">Quem cobra menos</p><h2 id="h-win">{quem}</h2>{valor}{cta}'
               + (f'<p class="valid">Preço válido até {PH._e(validade)}</p>' if validade else "") + "</section>")
    hero = f'<div class="wrap hero">{hero_txt}{win}</div>'

    # ---- as opções
    opcoes = ""
    if ops:
        cartoes = "".join(_cartao(o, i, rec, barata, modelo, href_fechar(o)) for i, o in enumerate(ops))
        opcoes = (f'<section class="s" aria-labelledby="h-ops"><h2 id="h-ops">'
                  f'{"As opções que separamos" if len(ops) > 1 else "A opção que separamos"}</h2>'
                  f'<p class="sub">A mesma comparação, lado a lado. A nota vai de 0 a 100 e pesa preço, franquia e coberturas.</p>'
                  f'<div class="ops{" um" if len(ops) == 1 else ""}" style="--n:{len(ops)}" tabindex="0" role="region" '
                  f'aria-roledescription="carrossel" aria-label="{PH._e(f"As {len(ops)} opções, lado a lado" if len(ops) > 1 else "A opção")}">'
                  f'{cartoes}</div>'
                  + (f'<p class="arraste">{PH.ICO["right"]}Arraste para o lado para ver as outras opções</p>'
                     if len(ops) > 1 else "")
                  + f'<div style="--n:{len(ops)}">{_comparar(ops)}</div></section>')

    # ---- a corretora
    corretora = ""
    if nome_anf:
        id_visual = (f'<span class="plate"><img src="{PH._e(logo)}" alt="" height="40"></span>' if logo
                     else f'<span class="mono" aria-hidden="true">{PH._e(AP.monograma(nome_anf))}</span>')
        cidade = str(anf.get("cidade") or "").strip()
        fatos = []
        g = anf.get("google") if isinstance(anf.get("google"), dict) else None
        g_nota = AP.dec(g.get("nota")) if g else None
        g_n = AP.numero_inteiro(g.get("avaliacoes")) if g else None
        if g_nota is not None and g_n and g_n > 0:
            fatos.append(f'<li><b>{PH.ICO["star"]}{f"{g_nota:.1f}".replace(".", ",")}</b>'
                         f'<span>no Google · {g_n} {"avaliações" if g_n != 1 else "avaliação"}</span></li>')
        else:
            g = None
        susep = _susep(anf)
        if susep:
            fatos.append(f'<li><b>{PH._e(susep)}</b><span>registro na SUSEP</span></li>')
        anos = M._anos(modelo, anf.get("desde"))
        if anos:
            n_anos = re.match(r"^(\d+)", anos).group(1)
            fatos.append(f'<li><b>{n_anos}{AP.NB}{"anos" if n_anos != "1" else "ano"}</b><span>de mercado</span></li>')
        site = str(anf.get("site") or "").strip()
        if re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~/-]*)?", site or ""):
            fatos.append(f'<li><a href="https://{PH._e(site)}" rel="noopener">{PH._e(site)}</a><span>site da corretora</span></li>')
        fonte_g = (f'<p class="src">Nota e avaliações: {PH._e(AP.aspas_tipograficas(g["fonte"]))}.</p>'
                   if g and str(g.get("fonte") or "").strip() else "")
        n5ok = (f'<p class="n5ok"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle class="ck" cx="12" cy="12" r="11"/>'
                f'<path d="M7 12.4l3.3 3.3L17.2 8.8" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" '
                f'stroke-linejoin="round"/></svg>{PH._e(selo)}</p>' if selo else "")
        corretora = (f'<section class="s" aria-labelledby="h-host"><h2 id="h-host">Quem é a corretora que cobra menos?</h2>'
                     f'<div class="host"><div class="host-id">{id_visual}<div><h3>{PH._e(nome_anf)}</h3>'
                     + (f"<p>{PH._e(cidade)}</p>" if cidade else "") + f"</div></div>{n5ok}"
                     + (f'<ul class="facts">{"".join(fatos)}</ul>' if fatos else "") + fonte_g
                     + f'<p class="what">Quem atende e cuida do seu seguro é a corretora. O {PH._e(nome_canal)} só compara '
                       f'e indica quem cobrou menos com a mesma cobertura completa.</p></div></section>')

    # ---- o selo do programa (só com o selo ligado na anfitriã)
    n5 = ""
    if selo:
        nivel = _nivel(selo)
        canal = modelo.get("canal") if isinstance(modelo.get("canal"), dict) else {}
        crit = canal.get("selo_criterios")
        lista = ([(str(a), str(b)) for a, b in crit if str(a).strip()] if isinstance(crit, list)
                 and all(isinstance(x, (list, tuple)) and len(x) == 2 for x in crit) and crit else CRITERIOS_DO_NIVEL_5)
        itens = "".join(f"<li><span><b>{PH._e(a)}</b>: {PH._e(b)}</span></li>" for a, b in lista)
        n5 = (f'<section class="n5" aria-labelledby="h-n5">{_selo_do_programa(nivel)}'
              f'<div><h2 id="h-n5">Só cotamos com Corretoras {PH._e(nivel)}</h2>'
              f'<p class="sub">O selo é do programa {PH._e(nome_canal)}, não do tamanho da corretora: qualquer corretora pode '
              f'ser {PH._e(nivel)}, desde que cumpra os {len(lista)} itens — e cada um é conferido.</p></div>'
              f'<ol>{itens}</ol><p class="n5-v">Lista do programa {PH._e(selo)} · versão '
              f'{VERSAO_DOS_CRITERIOS if lista is CRITERIOS_DO_NIVEL_5 else PH._e(str(canal.get("selo_versao") or "do modelo"))}</p>'
              f'</section>')

    # ---- melhor preço por seguradora (o ranking da corretora que cobra menos; nenhum nome de corretora por linha)
    rk = PH._ranking(modelo)
    ranking = ""
    if rk:
        menor = min(AP.dec(x["premio_anual"]) for x in rk)
        itens_rk = []
        for i, x in enumerate(sorted(rk, key=lambda x: AP.dec(x["premio_anual"]))):
            fqx = AP.brl(x.get("franquia"), False)
            dif = AP.dec(x["premio_anual"]) - menor
            meta = " · ".join(y for y in (f"franquia {fqx}" if fqx else "",
                                          f"{AP.brl(dif, False)} a mais por ano" if AP.reais(dif) >= 1 else "") if y)
            itens_rk.append(f'<li class="{"top" if i == 0 else ""}"><span class="n">{i + 1}</span><span class="nm">'
                            f'{PH._e(x["seguradora"])}{"<span class=tag>o menor preço</span>" if i == 0 else ""}</span>'
                            f'<span class="pr">{PH._e(AP.brl(x["premio_anual"]))}</span>'
                            + (f'<span class="meta">{PH._e(meta)}</span>' if meta else "") + "</li>")
        conta_num = PH._conta_do_resumo(modelo)
        pdif = [x for x in modelo.get("produto_diferente") or [] if isinstance(x, dict) and str(x.get("seguradora") or "").strip()]
        nr = [x for x in modelo.get("nao_responderam") or [] if isinstance(x, dict) and str(x.get("seguradora") or "").strip()]
        conta = PH._frase_da_conta(conta_num, len(pdif))
        if conta and nome_anf:     # o ranking é o da corretora que cobra menos: a frase diz de quem é
            conta = conta.replace(
                " seguradoras: ", f" seguradoras pela {nome_anf}: ", 1).replace(" seguradora: ", f" seguradora pela {nome_anf}: ", 1)
        econ = next((o for o in ops[1:] if isinstance(o.get("por_que_mais_barata"), str) and o["por_que_mais_barata"].strip()
                     and not any(PH._mesma(o, x) for x in rk)), None)
        nota_econ = ""
        if econ:
            pq = econ["por_que_mais_barata"].strip()
            nota_econ = (f'<p class="note">A <b>{PH._e(econ.get("rotulo") or "")}</b> ({PH._e(econ.get("seguradora") or "")}, '
                         f'{PH._e(AP.brl(econ.get("premio_anual")))}) não está nesta lista: '
                         f'{PH._e(AP.nbsp(pq[:1].lower() + pq[1:]))}</p>')
        pd_html = ""
        if pdif:
            k = len(pdif)
            pd_html = (f'<details class="line"><summary><span><b>{k} oferta{"s" if k > 1 else ""} '
                       f'cobre{"m" if k > 1 else ""} menos</b> e fica{"m" if k > 1 else ""} fora da lista</span>{PH.ICO["chev"]}'
                       f'</summary><ul>'
                       + "".join(f'<li><b>{PH._e(x["seguradora"])}'
                                 + (f', {PH._e(AP.sem_seguradora(x.get("produto"), x["seguradora"]))}'
                                    if str(x.get("produto") or "").strip() else "")
                                 + "</b>" + (f', {PH._e(AP.brl(x.get("premio_anual")))}' if AP.brl(x.get("premio_anual")) else "")
                                 + (f': {PH._e(x.get("por_que_nao_compara"))}' if str(x.get("por_que_nao_compara") or "").strip() else "")
                                 + "</li>" for x in pdif) + "</ul></details>")
        nr_html = ('<p class="line-static"><b>Não deram preço:</b> '
                   + "; ".join(PH._e(x["seguradora"]) + (f' ({PH._e(x.get("motivo"))})' if str(x.get("motivo") or "").strip() else "")
                               for x in nr) + ".</p>") if nr else ""
        ranking = (f'<section class="s" aria-labelledby="h-all"><h2 id="h-all">Melhor preço por seguradora</h2>'
                   + (f'<p class="sub">{PH._e(conta)}</p>' if conta else "")
                   + f'<ol class="rank">{"".join(itens_rk)}</ol>{nota_econ}'
                   + (f'<div class="others">{pd_html}{nr_html}</div>' if pd_html or nr_html else "") + "</section>")

    # ---- dúvidas, sinistro
    faq = PH._faq(modelo, ops)
    faq_html = (f'<section class="s" aria-labelledby="h-faq"><h2 id="h-faq">Perguntas que todo mundo faz</h2>'
                f'<div class="faq">{faq}</div></section>') if faq else ""
    sinistro_l = modelo.get("sinistro") if isinstance(modelo.get("sinistro"), list) else []
    passos = [s for s in sinistro_l if isinstance(s, str) and s.strip()]
    sinistro = ""
    if passos:
        titulo = f"Se bater o {PH._e(bem['rotulo'] or 'carro')}" if bem["e_veiculo"] else "Se acontecer alguma coisa"
        sinistro = (f'<section class="s" aria-labelledby="h-sin"><h2 id="h-sin">{titulo}</h2>'
                    + (f'<p class="sub">Quem cuida é a {PH._e(nome_anf)}, do aviso ao fim.</p>' if nome_anf else "")
                    + f'<ol class="steps">{"".join(f"<li><p>{PH._e(s)}</p></li>" for s in passos)}</ol></section>')

    # ---- o fecho
    fim = ""
    if rec is not None and digitos:
        duvida = (f"Olá! Aqui é {nome}. Tenho uma dúvida sobre a cotação do seguro {sobre_o_bem}." if nome
                  else f"Olá! Tenho uma dúvida sobre a cotação do seguro {sobre_o_bem}.")
        fim = (f'<section class="s fim" aria-labelledby="h-fim"><h2 id="h-fim">Quer fechar esse preço?</h2>'
               f'<p class="sub">Toque em “Quero fechar” e a conversa continua com o {PH._e(nome_canal)}, de onde você veio. '
               f'Nada é cobrado agora.</p>'
               f'<a class="cta" href="{PH._e(href_fechar(rec))}" rel="nofollow">{PH.ICO["wa"]}<span class="t">Quero fechar'
               f'<small>{PH._e(str(rec.get("rotulo") or rec.get("id")) + " · " + PH._brl(rec.get("premio_anual")) + " por ano")}'
               f'</small></span></a><a class="ask" href="{PH._e(wa(duvida))}" rel="noopener">Tirar uma dúvida</a></section>')

    validade_longa = AP.data_br(modelo.get("validade_ate"))
    aviso = AP.aviso_legal(modelo.get("aviso_legal"), _susep(anf))
    legal = ('<footer class="legal">' + (f'<p class="valid">Preços válidos até {PH._e(validade_longa)}.</p>' if validade_longa else "")
             + (f"<p>{PH._e(aviso)}</p>" if aviso else "")
             + f'<p>Comparamos só as ofertas com a mesma cobertura completa; as que cobrem menos aparecem à parte. '
               f'{PH._e(AP.voz(modelo)["nota_longa"])} pesa preço, franquia e coberturas.</p>'
             + f'<p>Comparação independente · {PH._e(nome_canal)}</p></footer>')

    dock = ""
    if rec is not None and digitos:
        pc = _parcela(rec)
        dock = (f'<div class="dock"><a class="cta" id="ab-fechar" href="{PH._e(href_fechar(rec))}" rel="nofollow">'
                f'{PH.ICO["wa"]}<span class="t">Quero fechar<small>'
                f'{PH._e(" · ".join(x for x in (str(rec.get("seguradora") or ""), f"{pc[0]} {pc[1]}" if pc else PH._brl(rec.get("premio_anual"))) if x))}'
                f'</small></span></a></div>')

    dados = {"opcoes": [{"id": o["id"], "rotulo": o.get("rotulo"), "seguradora": o.get("seguradora")} for o in ops]}
    titulo_pagina = f"{nome_canal} no seu seguro"
    return f"""<!doctype html>
<html lang="pt-BR" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="color-scheme" content="light dark">
<title>{PH._e(titulo_pagina)}</title>
<meta name="description" content="{PH._e(previa['descricao'])}">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{PH._e(previa['titulo'])}">
<meta property="og:description" content="{PH._e(previa['descricao'])}">
<meta property="og:site_name" content="{PH._e(nome_canal)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{PH._e(previa['titulo'])}">
<meta name="twitter:description" content="{PH._e(previa['descricao'])}">
{PH.MARCADOR_DA_PREVIA}
<style>{CSS_DO_CANAL}</style>
</head>
<body>
{topo}
<main>
{hero}
<div class="wrap">
{opcoes}
{corretora}
{n5}
{ranking}
{faq_html}
{sinistro}
{fim}
{legal}
<div class="endpad"></div>
</div>
</main>
{dock}
<script type="application/json" id="ab-dados">{PH._json_para_html(dados)}</script>
<script>{PH.SCRIPT_DA_PROPOSTA}</script>
</body>
</html>"""


# =====================================================================================================================
# o "Quero fechar" do canal — de volta à CONVERSA do canal, montado do modelo
# =====================================================================================================================
def destino_do_fechar_do_canal(modelo: dict, opcao: Any) -> Optional[dict]:
    """`{destino, opcao, rotulo, seguradora}` para uma opção QUE EXISTE; senão None. O destino é SEMPRE
    `https://wa.me/<canal.whatsapp>?text=<texto>` — a conversa do canal (D-133A-13), nunca a da corretora, nunca uma
    URL da query. O texto: `cta.texto_por_opcao` (leva a referência do pedido) ou o do desenho aprovado."""
    if not isinstance(opcao, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", opcao):
        return None
    escolhida = next((o for o in PH._opcoes(modelo) if o.get("id") == opcao), None)
    digitos = _digitos_do_canal(modelo)
    if escolhida is None or not digitos:
        return None
    cta = (modelo or {}).get("cta") or {}
    textos = cta.get("texto_por_opcao") if isinstance(cta, dict) else None
    texto = textos.get(opcao) if isinstance(textos, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        texto = PH._texto_do_fechar(modelo or {}, escolhida)
    texto = texto.strip()[:PH._TEXTO_MAXIMO]
    return {"destino": f"https://wa.me/{digitos}?text={quote(texto, safe='')}", "opcao": opcao,
            "rotulo": escolhida.get("rotulo"), "seguradora": escolhida.get("seguradora")}
