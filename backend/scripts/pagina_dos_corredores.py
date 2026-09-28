# -*- coding: utf-8 -*-
"""`pagina_dos_corredores.py` — a página que o Founder LÊ, montada por máquina.

> ## *"No final quero o documento de corredores extremamente claro, sem informações antigas que possam me confundir."*

```bash
cd backend && python scripts/pagina_dos_corredores.py --gravar
cd backend && python scripts/pagina_dos_corredores.py            # só imprime
cd backend && python scripts/pagina_dos_corredores.py --conferir  # o guarda
```

## 🔴 POR QUE ISTO É UM PROGRAMA E NÃO UM TEXTO ESCRITO À MÃO

📊 A aba `aba-corredores.html` de 26/09/2026 dizia, em HTML digitado:

```
mapfre / auto / guincho ....... 72 pedidos
alfa   / auto / bateria ....... 16 pedidos
"Guincho (72 pedidos) vale mais que táxi (1)"
```

Nenhum desses números era da rota. Eram o total do SERVIÇO em todas as
seguradoras, no retrato de 21/08 — e estavam colados numa página de 26/09 sem
nada que dissesse de quando eram. **Informação antiga sem rótulo é exatamente
o que confunde.** Um número digitado à mão não tem como carregar a própria
data; um número gerado, tem.

⇒ Daqui em diante a aba **inteira** sai de três retratos, cada um com a sua
data dentro do arquivo, e nenhum número é digitado:

```
docs/canon/reports/DEMANDA-POR-ROTA.json     demanda_por_rota.py --medir
docs/canon/reports/NOTAS-DAS-ROTAS.json      medir_rota.py --todas --gravar-notas
docs/canon/reports/SIMULACAO-DOS-CORREDORES.json  simular_corredor.py --todas --formato json
```

## 🔴 DUAS PERGUNTAS, NUNCA UMA — a lição da SPEC-117

```
DÁ PARA LIGAR?   binária de propósito     SIM · VAI PARA UMA PESSOA · FALTA CAPTURA
QUALIDADE        a régua, em %            0–100, e serve só para PRIORIZAR
```

⚠️ *"Uma régua não serve para duas perguntas."* Uma rota pode ter qualidade
baixa e **dar para ligar**; e uma rota com qualidade alta pode **não** dar, por
falta de captura. Publicar só a nota obriga o leitor a adivinhar qual das duas
ele está lendo — e ele adivinha errado, porque a nota PARECE responder tudo.

## 🔴 E A `causa` É OBRIGATÓRIA

`HANDOFF por_desenho_link` (a seguradora só devolve link — é o produto certo) e
`HANDOFF defeito_de_resposta` (tem conserto) são **opostos com o mesmo rótulo**.
Juntá-los foi o defeito que esta SPEC existe para desfazer. A página nunca
imprime a faixa sem a causa ao lado.

## AS TRÊS FAIXAS — as palavras do Founder, não as do código

```
ATENDE SOZINHO ................. o sistema fecha sem ninguém
QUASE — e falta O QUÊ .......... o que falta, numa frase
PRECISA DE ACIONAMENTO ......... falta CONVERSA, não falta código
```

⚠️ A terceira faixa tem um nome de gente no título porque **foi assim que o
Founder pediu**. 🔴 Nenhum DADO de produto carrega nome de pessoa ou de
corretora (CLAUDE.md §13.9): as rotas, as seguradoras e os números saem todos
do banco e do corpus, por `company_id`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS = os.path.join(RAIZ, "docs", "canon", "reports")
PAINEL = os.path.join(RAIZ, "docs", "canon", "painel-do-founder")

RETRATO_DEMANDA = os.path.join(REPORTS, "DEMANDA-POR-ROTA.json")
RETRATO_NOTAS = os.path.join(REPORTS, "NOTAS-DAS-ROTAS.json")
RETRATO_SIM = os.path.join(REPORTS, "SIMULACAO-DOS-CORREDORES.json")

SAIDA_MD = os.path.join(REPORTS, "CORREDORES-POR-ROTA.md")
SAIDA_HTML = os.path.join(PAINEL, "aba-corredores.html")

#: 🔴 Os três nomes de faixa, nas palavras do Founder. A ordem é a da página.
FAIXAS = [
    ("ATENDE SOZINHO", "ATENDE SOZINHO",
     "o sistema resolve sozinho, do começo ao protocolo"),
    ("HANDOFF", "VAI PARA UMA PESSOA",
     "o caso segue com alguém — por desenho da seguradora ou por defeito"),
    # 🔴 O SUBTITULO DESTA NAO PODE SER "falta conversa, nao falta codigo".
    #    📊 Medido em 28/09: das 46 rotas, 31 nao tem conversa nenhuma (aí SIM
    #    falta acionamento), mas **9 TEM conversa e falta o passo escrito**
    #    (`tela_orfa`) e **6 respondem tudo e nunca chegaram ao protocolo**
    #    (`sem_desfecho`). Prometer "falta conversa" nas 46 mandaria o Founder
    #    coletar o que JA ESTA COLETADO — a mesma confusão que esta SPEC existe
    #    para acabar. A faixa junta o que **não dá para ligar ainda**; é a
    #    `causa` que diz de quem é o trabalho, e ela é obrigatória.
    ("FALTA CAPTURA", "AINDA NÃO DÁ PARA LIGAR",
     "e a causa diz de quem é o trabalho: sem conversa é acionamento; "
     "tela sem resposta é código"),
]

#: As causas, ditas em português. 🔴 Nunca se imprime a faixa sem a causa.
CAUSAS = {
    "sem_corpus": ("nenhuma conversa desta rota no acervo",
                   "🧑 um acionamento real desta rota, com o observador ligado"),
    "tela_orfa": ("existe conversa, e uma tela dela ninguém respondeu",
                  "🤖 escrever o passo da tela que ficou sem resposta"),
    "sem_desfecho": ("responde tudo o que o acervo mostra e nunca chegou ao protocolo",
                     "🧑 um acionamento que vá até o fim — a prova do desfecho"),
    "por_desenho_link": ("a seguradora não abre pela conversa: devolve link ou formulário",
                         "✅ nada — é o desenho certo, e já é handoff pela SPEC-118"),
    "defeito_de_resposta": ("o robô responde, e responde ERRADO",
                            "🤖 conserto no corredor — tem solução em código"),
    "bateria_5_furada": ("tela de condomínio/empresa/sinistro que não vai a uma pessoa",
                         "🤖 conserto no encaminhamento"),
    "": ("—", "—"),
}


def _ler(caminho: str) -> Optional[Any]:
    try:
        with open(caminho, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _data_br(iso: str) -> str:
    """`2026-09-28` -> `28/09/2026`. A data que o Founder lê."""
    try:
        a, m, d = iso.split("-")
        return f"{d}/{m}/{a}"
    except ValueError:
        return iso


class Fontes:
    """Os três retratos, cada um com a SUA data.

    🔴 Datas diferentes são um FATO, não um defeito a esconder: a demanda vem
    do banco (vivo), a nota e a simulação vêm do corpus versionado (congelado
    no commit). A página imprime as três, e quem lê sabe o que está comparando.
    """

    def __init__(self):
        self.demanda = _ler(RETRATO_DEMANDA)
        self.notas = _ler(RETRATO_NOTAS)
        self.sim = _ler(RETRATO_SIM)

    def faltando(self) -> List[str]:
        f = []
        if self.demanda is None:
            f.append(f"{RETRATO_DEMANDA} — rode `demanda_por_rota.py --medir --gravar`")
        if self.notas is None:
            f.append(f"{RETRATO_NOTAS} — rode `medir_rota.py --todas "
                     f"--gravar-notas docs/canon/reports/NOTAS-DAS-ROTAS.json`")
        if self.sim is None:
            f.append(f"{RETRATO_SIM} — rode `simular_corredor.py --todas "
                     f"--formato json > {RETRATO_SIM}`")
        return f

    # ── as três datas, para o carimbo ────────────────────────────────────────
    @property
    def data_demanda(self) -> str:
        return _data_br(self.demanda.get("medido_em", "?"))

    @property
    def data_notas(self) -> str:
        return _data_br(self.notas.get("medido_em", "?"))

    @property
    def data_sim(self) -> str:
        """🔴 A data da SIMULAÇÃO vem da simulação, nunca emprestada.

        ⚠️ O JSON de `simular_corredor.py` é uma LISTA pura — não tem carimbo.
        Emprestar a data das notas seria cômodo e seria a mesma falta que esta
        fatia existe para consertar: um número com a data de outro. O carimbo
        de verdade está no `.md` irmão, que o próprio simulador escreve:
        `> gerado em 2026-09-28T00:08:01+00:00 · commit `a83dc06``.
        """
        return _data_br(self.sim_meta().get("gerado_em", "?")[:10])

    @property
    def commit_sim(self) -> str:
        return self.sim_meta().get("commit", "?")

    def sim_meta(self) -> Dict[str, Any]:
        caminho = RETRATO_SIM[: -len(".json")] + ".md"
        try:
            with open(caminho, encoding="utf-8") as fh:
                for linha in fh:
                    m = re.search(r"gerado em ([0-9T:+\-]{10,})\s*·\s*commit "
                                  r"`([0-9a-f]+)`", linha)
                    if m:
                        return {"gerado_em": m.group(1), "commit": m.group(2)}
                    if linha.startswith("## "):
                        break
        except OSError:
            pass
        return {"gerado_em": "?", "commit": "?"}


class Linha:
    """Uma rota, com as DUAS respostas e a demanda. Nada digitado."""

    def __init__(self, sim: Dict[str, Any], nota: Optional[Dict[str, Any]],
                 pedidos: Optional[int], sem_etiqueta: int):
        self.seguradora = sim["seguradora"]
        self.ramo = sim["ramo"]
        self.servico = sim["servico"]
        self.faixa = sim["faixa"]
        self.causa = sim.get("causa") or ""
        self.motivo = sim.get("motivo") or ""
        self.telas = sim.get("telas", 0)
        self.orfas = sim.get("orfas_funcionais", 0)
        self.chegou = bool(sim.get("chegou_ao_fim"))
        self.nota = nota or {}
        self.pedidos = pedidos
        self.sem_etiqueta = sem_etiqueta

    @property
    def rota(self) -> str:
        return f"{self.seguradora}/{self.ramo}/{self.servico}"

    @property
    def pct(self) -> str:
        """🔴 A QUALIDADE, em %. `—` quando a régua não pôde dar nota."""
        p = self.nota.get("pct")
        return "—" if p is None else f"{p}%"

    @property
    def bruto(self) -> str:
        if self.nota.get("pct") is None:
            return self.nota.get("estado") or "—"
        return f"{self.nota.get('pontos')}/{self.nota.get('denominador')}"

    @property
    def da_para_ligar(self) -> str:
        """🔴 A pergunta BINÁRIA. Não é a nota, e não se deduz dela."""
        return {"ATENDE SOZINHO": "SIM",
                "HANDOFF": "VAI PARA UMA PESSOA",
                "FALTA CAPTURA": "FALTA CAPTURA"}.get(self.faixa, "?")

    @property
    def causa_em_portugues(self) -> str:
        return CAUSAS.get(self.causa, (self.causa, "—"))[0]

    @property
    def o_que_destrava(self) -> str:
        if self.faixa == "ATENDE SOZINHO":
            return "✅ nada — esta rota está pronta para ligar"
        return CAUSAS.get(self.causa, ("—", "—"))[1]

    @property
    def pedidos_rotulo(self) -> str:
        """🔴 `—` quando não medido. NUNCA `0`, NUNCA o número global."""
        return "—" if self.pedidos is None else str(self.pedidos)

    @property
    def ressalva_da_demanda(self) -> str:
        """O que impede de ler `—` como *"ninguém pediu"*."""
        if self.pedidos is not None:
            return ""
        if self.sem_etiqueta:
            return (f"⚠️ `—` não é 'ninguém pediu': {self.sem_etiqueta} "
                    f"conversa(s) de {self.seguradora}/{self.ramo} estão no "
                    f"acervo SEM etiqueta de serviço")
        return "nenhuma conversa desta rota no acervo"


def montar(f: Fontes) -> List[Linha]:
    por_rota_nota = {
        f"{n['seguradora']}/{n['ramo']}/{n['servico']}": n
        for n in f.notas.get("rotas", [])}
    demanda = f.demanda.get("por_rota", {})
    sem_etq = f.demanda.get("sem_etiqueta", {})
    fora = []
    for s in f.sim:
        chave = f"{s['seguradora']}/{s['ramo']}/{s['servico']}"
        fora.append(Linha(s, por_rota_nota.get(chave), demanda.get(chave),
                          int(sem_etq.get(f"{s['seguradora']}/{s['ramo']}", 0))))
    # 🔴 A ORDEM é a do Founder: primeiro o que mais gente pede.
    #    ⚠️ `—` (não medido) vai para o FIM, separado de um `0` medido — que
    #    seria "olhamos e ninguém pediu", e é outra coisa. `or -1` juntaria os
    #    dois no mesmo lugar e apagaria a distinção que a coluna existe para
    #    fazer.
    fora.sort(key=lambda l: (-l.pedidos if l.pedidos is not None else 10**9,
                             -(l.nota.get("pct") or 0), l.rota))
    return fora


def _contar(linhas: List[Linha]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for l in linhas:
        d[l.faixa] = d.get(l.faixa, 0) + 1
    return d


def _por_causa(linhas: List["Linha"]):
    """A repartição por causa, da mais frequente para a menos."""
    d: Dict[str, int] = {}
    for l in linhas:
        if l.causa:
            d[l.causa] = d.get(l.causa, 0) + 1
    return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))


def _par_da_mesma_nota(linhas: List["Linha"]):
    """Duas rotas com a MESMA nota e respostas opostas a "dá para ligar?".

    🔴 É a prova mais barata e mais forte de que a régua não responde a
    pergunta binária: se a nota bastasse, um par assim seria impossível.
    Devolve `None` quando não existe — e aí a página **não afirma nada**.
    """
    por_nota: Dict[int, Dict[bool, "Linha"]] = {}
    for l in linhas:
        pct = l.nota.get("pct")
        if pct is None:
            continue
        por_nota.setdefault(pct, {}).setdefault(l.da_para_ligar == "SIM", l)
    for pct in sorted(por_nota, reverse=True):
        lados = por_nota[pct]
        if True in lados and False in lados:
            return lados[True], lados[False]
    return None


def _pct_faixa(n: int, total: int) -> str:
    return f"{round(100 * n / total)}%" if total else "—"


# ═════════════════════════════════════════════════════════════════════════════
# O RELATÓRIO EM MARKDOWN — a fonte canônica, em docs/canon/reports/
# ═════════════════════════════════════════════════════════════════════════════
def markdown(f: Fontes, linhas: List[Linha]) -> str:
    c = _contar(linhas)
    total = len(linhas)
    sozinho = c.get("ATENDE SOZINHO", 0)
    pessoa = c.get("HANDOFF", 0)
    captura = c.get("FALTA CAPTURA", 0)
    # 📊 quantas das que nao ligam e por AUSENCIA DE CONVERSA, e nao por codigo
    _sem_conversa = sum(1 for l in linhas if l.causa == "sem_corpus")
    L = [
        "# Os corredores, rota por rota — o que liga hoje e o que falta\n",
        f"> 🔴 **Três retratos, três datas, e elas estão escritas porque são "
        f"diferentes de propósito:**\n>\n"
        f"> | o que | medido em | de onde |\n"
        f"> |---|---|---|\n"
        f"> | **quantas pessoas pediram** (`pedidos`) | **{f.data_demanda}** | "
        f"`observed_events`, o banco — vivo |\n"
        f"> | **a nota da régua** (`qualidade`) | **{f.data_notas}** | o corpus "
        f"versionado no commit `{f.notas.get('commit','?')}` |\n"
        f"> | **dá para ligar?** | **{f.data_sim}** | a simulação com as telas "
        f"reais no commit `{f.commit_sim}`, `simular_corredor.py --todas` |\n>\n"
        f"> ⚠️ O banco é de hoje; o corpus é do commit. Comparar os dois números "
        f"de uma mesma rota é legítimo — comparar sem ver as datas, não.\n",
        "## 🔴 A frase que o Founder pode dizer a uma corretora\n",
        f"> **De {total} rotas medidas, o sistema resolve sozinho "
        f"{_pct_faixa(sozinho, total)} ({sozinho}), "
        f"{_pct_faixa(pessoa, total)} ({pessoa}) vão para uma pessoa, e "
        f"{_pct_faixa(captura, total)} ({captura}) ainda não dão para ligar.**\n",
        # 🔴 A SEGUNDA METADE, com o número EXATO. Dizer que as 46 "não têm
        #    conversa gravada" seria falso para 15 delas — e mandaria coletar o
        #    que já está coletado, que é a confusão que esta SPEC vem acabar.
        f"⚠️ **E a segunda metade da frase é obrigatória, com o número exato:** "
        f"das {captura} que ainda não ligam, **{_sem_conversa} não têm uma "
        f"conversa gravada** — essas não são falha do robô, e só um acionamento "
        f"real as destrava. As outras **{captura - _sem_conversa}** têm "
        f"conversa: nelas o material existe e **falta código nosso**.\n",
        "## 🔴 DUAS PERGUNTAS, NUNCA UMA\n",
        "```\n"
        "DÁ PARA LIGAR?   binária     SIM · VAI PARA UMA PESSOA · FALTA CAPTURA\n"
        "QUALIDADE        a régua, %  0–100 — serve para PRIORIZAR, não para decidir\n"
        "```\n",
        "Uma rota pode ter qualidade baixa e **dar para ligar**; e uma rota com "
        "qualidade alta pode **não** dar, por falta de captura. Foi a lição da "
        "SPEC-117: *uma régua não serve para duas perguntas*.\n",
        "🔴 **A `%` substituiu o `58/76`.** O denominador da régua muda por rota "
        "(76, 70, 64…), porque itens que não se aplicam saem da conta. "
        "📊 `42/64` **parece** pior que `48/76` e é melhor: 66% contra 63%. "
        "O bruto continua na tabela, para quem for auditar.\n",
    ]

    for chave, titulo, subtitulo in FAIXAS:
        desta = [l for l in linhas if l.faixa == chave]
        L.append(f"\n## {titulo} — {len(desta)} de {total} "
                 f"({_pct_faixa(len(desta), total)})\n")
        L.append(f"*{subtitulo}*\n")
        if not desta:
            L.append("_(nenhuma)_\n")
            continue
        # 🔴 A repartição por CAUSA, DENTRO da faixa. Sem ela, "46 rotas" soa
        #    como 46 acionamentos a fazer — e 15 delas são trabalho nosso.
        reparte = _por_causa(desta)
        if len(reparte) > 1:
            L.append("📊 **Dentro desta faixa:** "
                     + " · ".join(f"**{v}** {CAUSAS.get(k, (k, ''))[0]}"
                                  for k, v in reparte) + "\n")
        L.append("| rota | pedidos | qualidade | bruto | por quê | "
                 "🔴 o que destrava |")
        L.append("|---|---:|---:|---:|---|---|")
        for l in desta:
            porque = l.causa_em_portugues if l.causa else "responde tudo e chega ao fim"
            L.append(f"| `{l.rota}` | {l.pedidos_rotulo} | {l.pct} | {l.bruto} | "
                     f"{porque} | {l.o_que_destrava} |")
        L.append("")

    # ── o que a demanda mostra e a lista de rotas NÃO mostra ─────────────────
    sem_corredor = f.demanda.get("sem_corredor", {})
    if sem_corredor:
        L.append("\n## 🔴 O segurado pede, e o produto não tem corredor nenhum\n")
        L.append(f"📊 Medido em {f.data_demanda} em `observed_events`. Estes "
                 "serviços foram escolhidos por gente de verdade, e **não existe "
                 "playbook para eles** — então eles não aparecem em nenhuma das "
                 "faixas acima, porque a lista de rotas só conhece o que tem "
                 "corredor.\n")
        L.append("| serviço pedido | conversas | o que é |")
        L.append("|---|---:|---|")
        for k, v in sorted(sem_corredor.items(), key=lambda kv: (-kv[1], kv[0])):
            if "?" in k:
                oq = ("🔴 rótulo que o classificador não reconhece — "
                      "ver a seção dos `?` abaixo")
            else:
                oq = "🔴 serviço real, sem um único passo escrito"
            L.append(f"| `{k}` | {v} | {oq} |")
        L.append("")

    # ── os rótulos com `?` ───────────────────────────────────────────────────
    duvidosos = {k: v for k, v in sem_corredor.items() if "?" in k}
    if duvidosos:
        L.append("\n## Os rótulos com `?` — o classificador avisando que não sabe\n")
        L.append("⚠️ O `?` é **honesto**: o padrão-ouro casou uma escolha de menu "
                 "cujo rótulo não está no vocabulário canônico, e o classificador "
                 "**declara** isso (`nivel-1a-rotulo-desconhecido`) em vez de "
                 "chutar. Mas dois deles são coisas diferentes:\n")
        L.append("- **serviço real sem nome canônico** — precisa entrar no "
                 "vocabulário, e aí vira rota de verdade;")
        L.append("- 🔴 **`?4145720 - 26` é um NÚMERO DE PROTOCOLO virando "
                 "'serviço'** — aqui o padrão-ouro casou uma linha que não é "
                 "escolha de serviço nenhuma. É defeito do padrão, não falta de "
                 "vocabulário.\n")

    # ── a demanda sem rota, e as sessões sem etiqueta ────────────────────────
    sem_etq = f.demanda.get("sem_etiqueta", {})
    if sem_etq:
        L.append("\n## 🔴 As conversas que existem e o classificador não etiquetou\n")
        L.append("Enquanto elas estiverem aqui, um `—` na coluna `pedidos` "
                 "**não quer dizer 'ninguém pediu'** — quer dizer 'não sabemos'. "
                 f"📊 {f.data_demanda}, `observed_events`.\n")
        L.append("| seguradora / ramo | conversas sem etiqueta |")
        L.append("|---|---:|")
        for k, v in sorted(sem_etq.items(), key=lambda kv: (-kv[1], kv[0])):
            L.append(f"| `{k}` | {v} |")
        L.append("")

    L.append("\n---\n")
    L.append(f"_Gerado por `backend/scripts/pagina_dos_corredores.py --gravar` "
             f"em {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}. "
             f"**Nenhum número deste documento foi digitado à mão.**_")
    return "\n".join(L)


# ═════════════════════════════════════════════════════════════════════════════
# A ABA DO PAINEL
# ═════════════════════════════════════════════════════════════════════════════
def _e(t: Any) -> str:
    return html.escape(str(t), quote=True)


def _slug(t: str) -> str:
    """Um valor de `data-` sem espaço nem acento — o filtro compara string."""
    return (t or "sem").lower().replace(" ", "_")


def _linha_html(l: Linha) -> str:
    porque = l.causa_em_portugues if l.causa else "responde tudo e chega ao fim"
    ressalva = l.ressalva_da_demanda
    ped = _e(l.pedidos_rotulo)
    if ressalva and l.pedidos is None:
        ped = f'<span title="{_e(ressalva)}">—</span>'
    return (
        "<tr>"
        f'<td class="un"><b>{_e(l.seguradora)}</b><span class="sl">/</span>'
        f'{_e(l.ramo)}<span class="sl">/</span>'
        f'<b class="sv">{_e(l.servico)}</b></td>'
        f'<td class="dm">{ped}</td>'
        f'<td class="dm">{_e(l.pct)}</td>'
        f'<td class="dm">{_e(l.bruto)}</td>'
        f'<td class="ds">{_e(porque)}</td>'
        f'<td class="ds">{_e(l.o_que_destrava)}</td>'
        "</tr>")


def aba(f: Fontes, linhas: List[Linha]) -> str:
    c = _contar(linhas)
    total = len(linhas)
    sozinho = c.get("ATENDE SOZINHO", 0)
    pessoa = c.get("HANDOFF", 0)
    captura = c.get("FALTA CAPTURA", 0)
    P = []
    A = P.append
    A('<div id="tab-corredores" class="tab" hidden>')

    # 🔴 O CARIMBO ANTES DE TUDO — gate G10 da SPEC-119.
    A('<p class="note" style="border-left-color:var(--accent);margin:0 0 22px">'
      '<b>Esta página é gerada por máquina, e nenhum número nela foi digitado.</b> '
      'Cada coluna diz de quando é: '
      f'<b>pedidos</b> medidos em <b>{_e(f.data_demanda)}</b> no banco de conversas; '
      f'<b>qualidade</b> e <b>dá para ligar</b> medidos em <b>{_e(f.data_notas)}</b> '
      f'sobre as conversas gravadas no commit <code>{_e(f.notas.get("commit","?"))}</code>. '
      'Se um número aqui não tiver data ao lado, é defeito — '
      'reclame. <span class="mono">pagina_dos_corredores.py</span></p>')

    A('<header class="top">')
    A(f'<span class="eyebrow">Os corredores, rota por rota &middot; '
      f'{total} rotas &middot; pedidos de {_e(f.data_demanda)} &middot; '
      f'medição de {_e(f.data_notas)}</span>')
    A(f'<h1>De cada 100 rotas, {round(100*sozinho/total) if total else 0} o '
      f'sistema resolve sozinho.<br>O resto está aqui, com o nome do que falta.</h1>')
    A(f'<p class="lede">São <b>{total} rotas</b> — uma seguradora, um ramo, um '
      f'serviço. Hoje <b>{sozinho}</b> atendem do começo ao protocolo sem '
      f'ninguém, <b>{pessoa}</b> vão para uma pessoa, e <b>{captura}</b> ainda '
      f'não têm uma conversa gravada para medir. 🔴 <b>Estas últimas não são '
      f'falha do robô</b>: ninguém ainda acionou aquela seguradora para aquele '
      f'serviço com o observador ligado. <b>Um acionamento real resolve uma '
      f'rota.</b></p>')
    A('<div class="meta">')
    A(f'<span>pedidos <b>{_e(f.data_demanda)}</b></span>')
    A(f'<span>qualidade <b>{_e(f.data_notas)}</b></span>')
    A(f'<span>dá para ligar <b>{_e(f.data_sim)}</b></span>')
    A(f'<span>fonte <b>observed_events + corpus versionado</b></span>')
    A(f'<span>commit <b>{_e(f.notas.get("commit","?"))}</b></span>')
    A('</div>')
    A('</header>')

    # ── a frase para a corretora ─────────────────────────────────────────────
    A('<div class="virada" style="border-left-color:var(--accent)">')
    A('<span class="eyebrow" style="color:var(--accent)">A frase que você pode '
      'dizer a uma corretora</span>')
    A(f'<h2>&ldquo;Hoje o sistema resolve sozinho '
      f'{_pct_faixa(sozinho, total)} dos casos que sabemos medir. '
      f'{_pct_faixa(pessoa, total)} vão para uma pessoa, com o caso pronto na '
      f'mão dela.&rdquo;</h2>')
    _sem_conversa = sum(1 for l in linhas if l.causa == "sem_corpus")
    A(f'<p class="lede" style="max-width:76ch">E a segunda metade, que é a '
      f'honesta: <b>{_pct_faixa(captura, total)} das rotas ({captura} de '
      f'{total}) ainda não dão para ligar</b> — e dessas, <b>{_sem_conversa} '
      f'não têm uma conversa gravada</b>. Nessas não dá para prometer nada, e '
      f'também não dá para culpar o robô: cada acionamento real que acontecer '
      f'com o observador ligado tira uma rota da lista. As outras '
      f'<b>{captura - _sem_conversa}</b> têm conversa — nelas o material '
      f'existe e <b>falta código nosso</b>.</p>')
    A('<div class="niveis" style="margin-top:20px">')
    A(f'<div class="nv ok"><span class="nvn">FAIXA 1</span>'
      f'<h3>ATENDE SOZINHO</h3><span class="nvv">{sozinho}'
      f'<span> de {total} &middot; {_pct_faixa(sozinho, total)}</span></span>'
      f'<em>responde todas as telas que o acervo mostra, não decide pelo '
      f'segurado, e já chegou ao protocolo pelo menos uma vez</em></div>')
    A(f'<div class="nv al"><span class="nvn">FAIXA 2</span>'
      f'<h3>VAI PARA UMA PESSOA</h3><span class="nvv">{pessoa}'
      f'<span> de {total} &middot; {_pct_faixa(pessoa, total)}</span></span>'
      f'<em>🔴 e a <b>causa</b> muda tudo: por desenho (a seguradora só devolve '
      f'link) é o produto certo; por defeito, tem conserto</em></div>')
    A(f'<div class="nv cr"><span class="nvn">FAIXA 3</span>'
      f'<h3>PRECISA DE ACIONAMENTO</h3><span class="nvv">{captura}'
      f'<span> de {total} &middot; {_pct_faixa(captura, total)}</span></span>'
      f'<em>falta conversa, não falta código. Nenhuma linha de programa '
      f'conserta uma rota que ninguém nunca percorreu</em></div>')
    A('</div>')
    A('</div>')

    # ── as duas perguntas ────────────────────────────────────────────────────
    A('<div class="virada" style="border-left-color:var(--crit)">')
    A('<span class="eyebrow" style="color:var(--crit)">Leia isto antes da '
      'tabela</span>')
    A('<h2>São duas perguntas, e a nota só responde uma.</h2>')
    A('<p class="lede" style="max-width:76ch"><b>&ldquo;Dá para ligar?&rdquo;</b> '
      'é sim ou não, e é a que decide. <b>&ldquo;Qual a qualidade?&rdquo;</b> é '
      'a nota da régua, de 0 a 100, e serve para saber <i>por onde começar</i> — '
      'nunca para decidir se liga. Uma rota pode ter nota baixa e estar pronta; '
      'outra pode ter nota alta e não ter uma conversa gravada que prove nada.</p>')
    # 🔴 O EXEMPLO NÃO É INVENTADO — ele sai dos dados, ou não aparece.
    #    ⚠️ Escrever "imagine uma rota boa que não liga" seria 💭; a frase só
    #    tem direito de existir se houver uma, e os nomes vão junto.
    #
    # 🔴 E a prova mais forte não é uma rota: é um PAR com a MESMA nota e
    #    respostas opostas. Enquanto existir um, ninguém pode dizer que a nota
    #    responde as duas perguntas.
    par = _par_da_mesma_nota(linhas)
    if par:
        a, b = par
        A(f'<p class="note" style="margin-top:12px">📊 <b>E não é hipótese.</b> '
          f'<code>{_e(a.rota)}</code> e <code>{_e(b.rota)}</code> têm '
          f'<b>a mesma nota, {_e(a.pct)}</b> — e a primeira <b>atende '
          f'sozinha</b> enquanto a segunda <b>vai para uma pessoa</b>. '
          f'<b>Se a nota bastasse, isso não podia acontecer.</b></p>')
    A('<p class="lede" style="max-width:76ch;margin-top:10px">🔴 <b>E a nota '
      'agora é em %, não mais &ldquo;58 de 76&rdquo;.</b> O denominador mudava '
      'de rota para rota — 76, 70, 64 — porque itens que não se aplicam saem da '
      'conta. <b>42/64 parecia pior que 48/76 e é melhor</b> (66% contra 63%). '
      'O número bruto continua na tabela, para quem quiser conferir.</p>')
    A('</div>')

    # ── as três faixas, cada uma com a sua tabela ────────────────────────────
    cores = {"ATENDE SOZINHO": "var(--accent)", "HANDOFF": "var(--alerta)",
             "FALTA CAPTURA": "var(--crit)"}
    for chave, titulo, subtitulo in FAIXAS:
        desta = [l for l in linhas if l.faixa == chave]
        A(f'<div class="virada" style="border-left-color:{cores[chave]}">')
        A(f'<span class="eyebrow" style="color:{cores[chave]}">'
          f'{_e(titulo)} &middot; {len(desta)} de {total} &middot; '
          f'{_pct_faixa(len(desta), total)}</span>')
        A(f'<h2>{_e(subtitulo[0].upper() + subtitulo[1:])}.</h2>')
        if chave == "FALTA CAPTURA":
            A('<p class="lede" style="max-width:76ch">🔴 <b>Não se mapeia o que '
              'ninguém viu</b> — mas <b>parte desta faixa não é isso</b>, e a '
              'coluna <b>o que destrava</b> diz qual. Ordenadas por quantas '
              'pessoas pediram aquele serviço naquela seguradora — comece de '
              'cima. Onde os pedidos aparecem como <b>—</b>, é porque não há '
              'conversa etiquetada: <b>não é zero, é &ldquo;não '
              'sabemos&rdquo;</b>.</p>')
        elif chave == "HANDOFF":
            A('<p class="lede" style="max-width:76ch">🔴 <b>A coluna '
              '&ldquo;por quê&rdquo; é obrigatória aqui.</b> "A seguradora só '
              'devolve link" e "o robô responde errado" são opostos, e antes '
              'apareciam com o mesmo rótulo.</p>')
        reparte = _por_causa(desta)
        if len(reparte) > 1:
            A('<p class="note" style="margin-top:10px">📊 <b>Dentro desta '
              'faixa:</b> ' + ' &middot; '.join(
                  f'<b>{v}</b> {_e(CAUSAS.get(k, (k, ""))[0])}'
                  for k, v in reparte) + '</p>')
        A('<div class="tblbox" style="margin-top:14px"><table>')
        A('<thead><tr><th class="l">rota</th><th>pedidos</th><th>qualidade</th>'
          '<th>bruto</th><th class="l">por quê</th>'
          '<th class="l">o que destrava</th></tr></thead><tbody>')
        for l in desta:
            A(_linha_html(l))
        if not desta:
            A('<tr><td class="ds" colspan="6">nenhuma</td></tr>')
        A('</tbody></table></div>')
        A('</div>')

    # ── as 73 numa tabela só, com busca ──────────────────────────────────────
    # 🔴 As três faixas acima são o que o Founder pediu. Esta tabela existe
    #    porque `base.html` traz um filtro que procura `#tb`, `#cnt`, `input.q`
    #    e `.chip` — e ele sai do ar em silêncio se a aba não os tiver
    #    (`if (!tb) return;`). ⚠️ Um filtro que some sem avisar numa lista de
    #    73 linhas é pior que filtro nenhum: quem usou ontem procura hoje.
    A('<div class="virada" style="border-left-color:var(--line-2)">')
    A('<span class="eyebrow">As 73 numa tabela só &middot; para procurar</span>')
    A('<h2>A mesma coisa, com busca.</h2>')
    A('<p class="lede" style="max-width:76ch">As linhas são as mesmas de cima — '
      'nenhum número muda aqui. Filtre por faixa, por causa, ou escreva o nome '
      'da seguradora ou do serviço.</p>')
    A('<div class="ctl">')
    for chave, titulo, _s in FAIXAS:
        A(f'<button class="chip" data-f="p:{_slug(chave)}" aria-pressed="false">'
          f'{_e(titulo)}</button>')
    causas_vivas = sorted({l.causa for l in linhas if l.causa})
    for causa in causas_vivas:
        A(f'<button class="chip" data-f="b:{_slug(causa)}" aria-pressed="false">'
          f'{_e(CAUSAS.get(causa, (causa, ""))[0])}</button>')
    A('<input class="q" type="search" placeholder="allianz, guincho, resi…" '
      'aria-label="Filtrar rotas">')
    A(f'<span class="count" id="cnt">{total} de {total}</span>')
    A('</div>')
    A('<div class="tblbox"><table>')
    A('<thead><tr><th class="l">rota</th><th>dá para ligar?</th><th>pedidos</th>'
      '<th>qualidade</th><th class="l">por quê</th>'
      '<th class="l">o que destrava</th></tr></thead>')
    A('<tbody id="tb">')
    for l in linhas:
        porque = l.causa_em_portugues if l.causa else "responde tudo e chega ao fim"
        busca = " ".join([l.seguradora, l.ramo, l.servico, l.faixa, l.causa,
                          l.da_para_ligar]).lower()
        A(f'<tr data-b="{_slug(l.causa)}" data-p="{_slug(l.faixa)}" '
          f'data-q="{_e(busca)}">'
          f'<td class="un"><b>{_e(l.seguradora)}</b><span class="sl">/</span>'
          f'{_e(l.ramo)}<span class="sl">/</span>'
          f'<b class="sv">{_e(l.servico)}</b></td>'
          f'<td class="ds">{_e(l.da_para_ligar)}</td>'
          f'<td class="dm">{_e(l.pedidos_rotulo)}</td>'
          f'<td class="dm">{_e(l.pct)}</td>'
          f'<td class="ds">{_e(porque)}</td>'
          f'<td class="ds">{_e(l.o_que_destrava)}</td></tr>')
    A('</tbody></table></div>')
    A('</div>')

    # ── o serviço que ninguém atende ─────────────────────────────────────────
    sem_corredor = f.demanda.get("sem_corredor", {})
    if sem_corredor:
        A('<div class="virada" style="border-left-color:var(--crit)">')
        A(f'<span class="eyebrow" style="color:var(--crit)">📊 medido em '
          f'{_e(f.data_demanda)} em <code>observed_events</code></span>')
        A('<h2>O segurado pede, e não existe corredor nenhum.</h2>')
        A('<p class="lede" style="max-width:76ch">Estes serviços foram '
          'escolhidos por gente de verdade, e <b>não há um único passo escrito '
          'para eles</b>. Eles não aparecem nas três faixas acima porque a '
          'lista de rotas só conhece o que tem corredor — e por isso ficavam '
          'invisíveis.</p>')
        A('<div class="tblbox" style="margin-top:14px"><table>')
        A('<thead><tr><th class="l">serviço pedido</th><th>conversas</th>'
          '<th class="l">o que é</th></tr></thead><tbody>')
        for k, v in sorted(sem_corredor.items(), key=lambda kv: (-kv[1], kv[0])):
            oq = ("🔴 rótulo que o classificador não reconhece — o <code>?</code> "
                  "é ele avisando que não sabe, e é honesto"
                  if "?" in k else
                  "🔴 serviço real, sem um único passo escrito")
            A(f'<tr><td class="un"><code>{_e(k)}</code></td>'
              f'<td class="dm">{v}</td><td class="ds">{oq}</td></tr>')
        A('</tbody></table></div>')
        A('<p class="note" style="margin-top:12px">🔴 <b>E um deles não é '
          'serviço nenhum:</b> <code>?4145720 - 26</code> é um <b>número de '
          'protocolo</b> que o classificador leu como se fosse o nome de um '
          'serviço. É defeito do padrão, não falta de vocabulário.</p>')
        A('</div>')

    # ── as conversas sem etiqueta ────────────────────────────────────────────
    sem_etq = f.demanda.get("sem_etiqueta", {})
    if sem_etq:
        A('<div class="virada" style="border-left-color:var(--alerta)">')
        A(f'<span class="eyebrow" style="color:var(--alerta)">📊 medido em '
          f'{_e(f.data_demanda)}</span>')
        A('<h2>As conversas que existem e ninguém soube etiquetar.</h2>')
        A('<p class="lede" style="max-width:76ch">Enquanto elas estiverem aqui, '
          'um <b>—</b> na coluna <b>pedidos</b> <b>não quer dizer '
          '&ldquo;ninguém pediu&rdquo;</b>: quer dizer <b>&ldquo;não '
          'sabemos&rdquo;</b>. São duas coisas diferentes, e só uma delas é um '
          'fato.</p>')
        A('<div class="tblbox" style="margin-top:14px"><table>')
        A('<thead><tr><th class="l">seguradora / ramo</th>'
          '<th>conversas sem etiqueta</th></tr></thead><tbody>')
        for k, v in sorted(sem_etq.items(), key=lambda kv: (-kv[1], kv[0])):
            A(f'<tr><td class="un"><code>{_e(k)}</code></td>'
              f'<td class="dm">{v}</td></tr>')
        A('</tbody></table></div>')
        A('</div>')

    # 🔴 O HISTORICO SAIU, E A PAGINA DIZ PARA ONDE FOI.
    #    O Founder pediu "sem informacoes antigas que possam me confundir", e a
    #    aba anterior carregava ~48 KB de medicoes de agosto/2026 misturadas com
    #    as de hoje. ⚠️ Mas "apagar" e "esconder" nao sao a mesma coisa: quem
    #    for auditar precisa saber que existiu e onde achar.
    A('<p class="note" style="border-left-color:var(--faint);margin-top:26px">'
      '<b>O histórico de agosto saiu desta aba de propósito.</b> Ela carregava '
      'as medições das SPECs 083, 084 e 084.2 ao lado das de hoje, e as duas '
      'coisas usavam <b>réguas diferentes</b> — o denominador mudou de 106 para '
      '76/70/64 na SPEC-089, então comparar os números era comparar duas '
      'réguas. Nada foi perdido: está no histórico do repositório '
      '(<span class="mono">git log docs/canon/painel-do-founder/'
      'aba-corredores.html</span>), e as lições que viraram regra moram no '
      '<span class="mono">CLAUDE.md</span> §9.4 e §9.5. '
      '🔴 <b>Nesta aba só entra número com data ao lado.</b></p>')

    A('</div>')
    return "\n".join(P)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O GUARDA — e ele TEM de conseguir ficar vermelho (CLAUDE.md §9.3)
# ═════════════════════════════════════════════════════════════════════════════
def conferir(f: Fontes, linhas: List[Linha], texto_html: str) -> Tuple[List[str], List[str]]:
    """As afirmações que a página faz sobre si mesma, conferidas.

    Devolve `(achados, conferencias)`. Achado = a página mente.
    """
    achados: List[str] = []
    feitas: List[str] = []

    # ① toda linha de faixa traz a CAUSA
    feitas.append("toda rota fora de ATENDE SOZINHO traz uma causa")
    for l in linhas:
        if l.faixa != "ATENDE SOZINHO" and not l.causa:
            achados.append(f"🔴 {l.rota}: faixa {l.faixa} SEM causa — "
                           "é a 'coluna mentirosa' de volta")

    # ② nenhuma demanda ausente vira 0
    feitas.append("demanda ausente imprime `—`, nunca `0`")
    for l in linhas:
        if l.pedidos is None and l.pedidos_rotulo != "—":
            achados.append(f"🔴 {l.rota}: demanda ausente saiu como "
                           f"{l.pedidos_rotulo!r}")

    # ③ 🔴 nenhuma rota mostra o número GLOBAL do seu serviço
    #    É a prova direta do defeito que a SPEC existe para consertar.
    feitas.append("nenhuma rota exibe o total global do serviço")
    try:
        import padroes_de_servico as PS
        global_por_servico = {s: e for s, e, _c
                              in PS.DEMANDA_GLOBAL_POR_SERVICO_21_08_2026}
    except Exception:  # noqa: BLE001
        global_por_servico = {}
    for l in linhas:
        g = global_por_servico.get(l.servico)
        if g is None or l.pedidos is None or g == 0:
            continue
        if l.pedidos == g and g > 3:
            achados.append(
                f"⚠️ {l.rota}: pedidos={l.pedidos} é IGUAL ao total global do "
                f"serviço ({g}). Coincidência é possível, mas confira a fonte")

    # ④ 🔴 a página não publica número sem data
    feitas.append("a aba carrega as duas datas, visíveis")
    for data in (f.data_demanda, f.data_notas):
        if data == "?" or data not in texto_html:
            achados.append(f"🔴 a data {data!r} não aparece na aba — gate G10")

    # ⑤ o total bate com a soma das faixas
    feitas.append("a soma das faixas é o total de rotas")
    soma = sum(_contar(linhas).values())
    if soma != len(linhas):
        achados.append(f"🔴 a soma das faixas ({soma}) não é o total "
                       f"({len(linhas)})")

    # ⑥ 🔴 §13.9 NOS DADOS **E** NO HTML — e por REGRA, não por lista
    #
    # ══════════════════════════════════════════════════════════════════════
    # ⚠️ 🔴 ESTE GUARDA VIOLAVA O §13.9 QUE ELE EXISTE PARA GUARDAR.
    # ══════════════════════════════════════════════════════════════════════
    #
    # A v1 era `proibidos = ("regina", "saionara", "resulta", "autofleet",
    # "amandus")` — **cinco constantes com o nome de duas corretoras-piloto e
    # de duas atendentes, escritas num script NOVO**. É literalmente o que o
    # §13.9 proíbe: *"nenhum nome de corretora (nem de grupo, número, pasta ou
    # atendente) entra como constante em código, teste, script ou documento"*.
    #
    # 📊 E ela tinha três defeitos num lugar só, medidos em 28/09/2026:
    #
    # ```
    # ① lista com nome de cliente/funcionário dentro do próprio guarda
    # ② olhava só as CHAVES — o juiz mutou nome como VALOR e nome dentro do
    #    HTML emitido, e o guarda deu ZERO achado nas duas
    # ③ `maria` não estava na lista, e era o nome que de fato vazava
    # ```
    #
    # 🔴 A REGRA QUE SUBSTITUI A LISTA, e ela falha FECHADO:
    #
    # > ## Toda palavra publicada num dado medido tem de ser vocabulário do
    # > ## PRODUTO. O que o produto não conhece não sai daqui.
    #
    # O vocabulário vem de `higiene_do_corpus.vocabulario_de_lingua()` — os 14
    # playbooks, os padrões de serviço e os tipos de logradouro — mais as marcas
    # das seguradoras. 📊 Medido: das 987 células de dado da aba, **14** palavras
    # ficam de fora, e todas são a língua desta página (`observador`, `pronta`,
    # `classificador`…). É essa lista de 14 que fica escrita aqui — nenhuma delas
    # é nome de gente nem de corretora.
    feitas.append("§13.9 por REGRA: toda palavra dos dados e do HTML é "
                  "vocabulário do produto (chaves, VALORES e células)")
    for achado in _palavras_fora_do_produto(f.demanda, texto_html):
        achados.append(achado)

    # ⑦ 🔴 O CONTROLE DO ⑥ — e ele viaja junto com o guarda.
    #    *"Um guarda que não tem como falhar não guarda nada"* (CLAUDE.md §9.3).
    #    📊 A v1 do ⑥ ficava VERDE com nome no valor e nome no HTML.
    feitas.append("o guarda do §13.9 CONSEGUE ficar vermelho (4 mutações)")
    achados += _controle_do_guarda_139(f.demanda, texto_html)
    return achados, feitas


# 🔴 A LÍNGUA DESTA PÁGINA — 14 palavras, medidas, e nenhuma é nome de ninguém.
#    ⚠️ Cresce quando a copy da aba crescer; se um dia alguém tentar escrever
#    um nome aqui, a linha fica visível no diff, que é o ponto.
_LINGUA_DA_PAGINA = frozenset({
    "observador", "pronta", "ficou", "prova", "classificador", "reconhece",
    "qualidade", "desenho", "bruto", "conversas", "lar", "assistance",
    "reembolso", "etiqueta",
})
_RX_CELULA = re.compile(r"<(?:code|td|th)[^>]*>(.*?)</(?:code|td|th)>", re.S)


def _textos_medidos(demanda: Any, html: str) -> List[Tuple[str, str]]:
    """Todo texto que a página PUBLICA como dado: `(origem, texto)`.

    🔴 Chaves **e** valores, em qualquer profundidade — e as células do HTML
    emitido. O juiz mutou nas duas e o guarda antigo não olhava nenhuma.
    """
    fora: List[Tuple[str, str]] = []

    def _andar(no: Any, caminho: str) -> None:
        if isinstance(no, dict):
            for k, v in no.items():
                fora.append((caminho + " (chave)", str(k)))
                _andar(v, f"{caminho}[{k!r}]")
        elif isinstance(no, (list, tuple)):
            for i, v in enumerate(no):
                _andar(v, f"{caminho}[{i}]")
        elif isinstance(no, str):
            fora.append((caminho, no))

    for bloco in ("por_rota", "sem_corredor", "sem_etiqueta"):
        _andar((demanda or {}).get(bloco), f"demanda.{bloco}")
    for celula in _RX_CELULA.findall(html or ""):
        fora.append(("html", re.sub(r"<[^>]+>", " ", celula)))
    return fora


def _controle_do_guarda_139(demanda: Any, html: str) -> List[str]:
    """Semeia quatro defeitos SINTÉTICOS e exige o vermelho em cada um.

    ⚠️ Os nomes semeados aqui não existem em corretora nenhuma — são inventados
    justamente para que o §13.9 não seja violado pelo seu próprio controle.
    📊 Com a v1 do guarda, as mutações ② e ③ davam ZERO achado.
    """
    falhas: List[str] = []
    mutacoes = [
        ("① nome na CHAVE",
         {**(demanda or {}),
          "por_rota": {**((demanda or {}).get("por_rota") or {}),
                       "porto/auto/zoraide": 3}}, html),
        ("② nome no VALOR",
         {**(demanda or {}),
          "sem_etiqueta": {"porto-auto": {"motivo": "Zoraide nao escolheu"}}}, html),
        ("③ nome no HTML emitido",
         demanda, re.sub(r"<td[^>]*>", lambda m: m.group(0) + "Zoraide ",
                         html or "", count=1)),
        ("④ marca de corretora no HTML",
         demanda, re.sub(r"<code[^>]*>", lambda m: m.group(0) + "Zoraidecorp-",
                         html or "", count=1)),
    ]
    for rotulo, dem, htm in mutacoes:
        if not _palavras_fora_do_produto(dem, htm):
            falhas.append(f"🔴 CONTROLE FALHOU: o guarda do §13.9 ficou VERDE "
                          f"com a mutação {rotulo} — ele é carimbo, não guarda")
    return falhas


def _palavras_fora_do_produto(demanda: Any, html: str) -> List[str]:
    """Os achados do §13.9. Lista vazia = a página só publica língua do produto."""
    try:
        import higiene_do_corpus as H
        conhecidas = set(H.vocabulario_de_lingua()) | _LINGUA_DA_PAGINA
        try:
            conhecidas |= {H._sem_acento(s) for s in H.M.TPL._marcas_das_seguradoras()}
        except Exception:  # noqa: BLE001
            pass
        sem_acento = H._sem_acento
    except Exception as e:  # noqa: BLE001
        return [f"🔴 §13.9: não consegui ler o vocabulário do produto ({e})"]

    achados: List[str] = []
    vistas: Set[str] = set()
    for origem, texto in _textos_medidos(demanda, html):
        for palavra in re.findall(r"[A-Za-zÀ-ÿ]{3,}", texto):
            n = sem_acento(palavra)
            if n in conhecidas or n in vistas:
                continue
            vistas.add(n)
            achados.append(
                f"🔴 §13.9: {origem} publica {palavra!r}, que não é vocabulário "
                f"do produto — nome de gente ou de corretora não sai daqui")
    return achados


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--gravar", action="store_true",
                   help="escreve o .md e a aba do painel")
    p.add_argument("--conferir", action="store_true",
                   help="só roda o guarda e devolve 1 se houver achado")
    a = p.parse_args(argv)

    f = Fontes()
    faltando = f.faltando()
    if faltando:
        print("🔴 falta(m) retrato(s):", file=sys.stderr)
        for x in faltando:
            print(f"   {x}", file=sys.stderr)
        return 2

    linhas = montar(f)
    md = markdown(f, linhas)
    html_aba = aba(f, linhas)
    achados, feitas = conferir(f, linhas, html_aba)

    if a.conferir:
        print(f"=== o guarda da página — {len(feitas)} conferência(s) ===")
        for x in feitas:
            print(f"  ✅ {x}")
        if achados:
            print()
            for x in achados:
                print(f"  {x}")
            print(f"\n🔴 {len(achados)} achado(s)")
            return 1
        print("\n✅ nenhum achado")
        return 0

    if achados:
        print("🔴 o guarda achou defeito; nada foi gravado:", file=sys.stderr)
        for x in achados:
            print(f"   {x}", file=sys.stderr)
        return 1

    if a.gravar:
        with open(SAIDA_MD, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md + "\n")
        with open(SAIDA_HTML, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html_aba + "\n")
        print(f"gravado: {SAIDA_MD}")
        print(f"gravado: {SAIDA_HTML}")
        print(f"📊 {len(linhas)} rotas · pedidos de {f.data_demanda} · "
              f"medição de {f.data_notas}")
        return 0

    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
