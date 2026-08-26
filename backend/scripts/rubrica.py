"""A RUBRICA — os cinco eixos da SPEC-083 §3. Determinística, sem LLM.

```
A · EVIDÊNCIA    a rota foi percorrida até o fim?           20
B · COBERTURA    as telas viraram passos?                   35   ← o peso está aqui
C · SEGURANÇA    o freio casa tela REAL?                    26  (C7: +6)
D · CONHECIMENTO medido contra o acervo                     10
E · PROVA        mutação executada, não comentada           15
                                                         ─────
                                               PRONTIDÃO  100
```

> ## O PRINCÍPIO QUE GOVERNA A RUBRICA INTEIRA
> ## Ponto só se ganha contra o CORPUS. Declaração não vale ponto.

📊 Na v1, **75 dos 100 pontos** podiam ser obtidos escrevendo campos. O juiz achou
a receita: chamar `_auto_playbook` para uma seguradora nova, escrever um teste com
uma chamada ao motor e quatro comentários com a palavra CONTROLE — **49/100 sem
responder uma única tela real**.

🔴 **E o portão do eixo B (§3.8) existe porque a receita sobreviveu ao primeiro
conserto:** o juiz a refez com `alfa × auto × bateria` e ainda tirava 30–45, por
herança de família (C) e teste simbólico (E). **Nenhuma rota recebe pontos de A,
C, D ou E enquanto B < 8.**
"""

from __future__ import annotations

import ast
import io
import datetime as dt
import glob
import os
import collections
import re
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detector_do_eixo_e as DET   # noqa: E402
import regua_motor as M            # noqa: E402
import replay as RP                # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE_DO_CORREDOR = os.path.join(RAIZ, "app", "services", "corridor_playbooks.py")
PASTA_DE_TESTES = os.path.join(RAIZ, "tests")

# ── os estados que SAEM do denominador (§3.9) ────────────────────────────────
# 🔴 *"Item excluído NÃO é renormalizado. A nota é sempre sobre o denominador
#    real, e o excluído aparece explícito."*
#
# ⚠️ **E SÓ SAI QUEM NÃO SE APLICA.** SPEC-089 BLOCO A:
#
#     NÃO SE APLICA à rota ....... sai do denominador       ✅ legítimo
#     não medi porque não quis ... 🔴 FICA, valendo ZERO
#     não CONSEGUI medir ......... 🔴 FICA, valendo ZERO
#
# 📊 MEDIDO EM 26/08/2026, as 73 rotas, os dois modos:
#
#     sem `--com-espelho` .... 30 AAA · mediana 97,8% · 17 rotas em 100,0%
#     com `--com-espelho` .... 20 AAA · mediana 94,3% ·  9 rotas em 100,0%
#
#     🔴 27 de 43 rotas tiram nota MAIOR quando o item não é medido.
#     🔴 DEZ rotas eram AAA só por isso.
#
# ⛔ **A régua já conhecia esta regra e a aplicava num lugar só.** O item da
# mutação (eixo E) diz, quando não consegue ler o `MUTACOES` do repo:
# *"zero medido nao e zero nao medido"* — e vale **0 DENTRO do denominador**.
# `SEM_ESPELHO` fazia o contrário, no caminho PADRÃO da ferramenta.
SEM_FABRICA = "SEM_FABRICA"
ROTA_INDISTINGUIVEL = "ROTA_INDISTINGUIVEL"

#: 🔴 SPEC-089 BLOCO A — NÃO É MAIS MOTIVO DE EXCLUSÃO.
#:
#: ⚠️ O nome sobrevive como **rótulo da evidência**: quem lê a nota precisa
#: saber que os 4 pontos caíram por falta de medição, não por a rota ser ruim.
#: ⛔ Mas ele não vai mais para o campo `excluido`.
SEM_ESPELHO = "SEM_ESPELHO"


#: 🔴 SPEC-089 BLOCO B — OS ITENS QUE VIRARAM PORTAO, E POR QUE.
#:
#: 📊 MEDIDO EM 26/08/2026, item a item, nas 43 rotas com corpus:
#:
#:     NOVE itens nunca reprovaram nenhuma rota .... 44 de 106 pontos
#:     = 41,5% de cada nota era PRESENCA, nao qualidade
#:
#: ⚠️ A SPEC listava OITO (40 pontos). O nono é `transcrita no bloco do
#: subservico` (+4), que ela nao cita.
#:
#: 🔴 E oito deles tem a MESMA forma: eles conferem que uma MA PRATICA ESTA
#: AUSENTE — nenhuma constante decide pelo cliente, nenhuma ancora exige `*`,
#: o teste chama o motor. **Ausencia de defeito e PORTAO, nao PLACAR.**
#:
#: ⛔ Dar ponto por nao ter defeito e dar ponto por nada, e 43 de 43 rotas
#: ganhavam esses pontos identicos. Como PORTAO, eles continuam guardando —
#: e uma rota que abrir qualquer um deles **nao chega a AAA**.
#:
#: 📊 O EFEITO, medido com espelho:
#:
#:     antes   AAA 20 · quase 13 · parcial 9 · esqueleto 1   amplitude 46,2
#:     depois  AAA 12 · quase 18 · parcial 4 · esqueleto 8 · toco 1
#:                                                          amplitude 79,0
#:
#: 🔴 E o gate ③ da SPEC fecha: as NOVE rotas que tiravam 106/106 continuam
#: AAA em 62/62 — alfa/auto/guincho, allianz/auto/guincho,
#: allianz/residencial/encanador, azul/auto/guincho, hdi/auto/guincho,
#: porto/auto/guincho, yelum/auto/guincho, yelum/auto/socorro_mecanico e
#: yelum/residencial/encanador. **Separar nao e rebaixar todo mundo.**
#:
#: ⚠️ `>=85% deterministico` NAO esta aqui: o corte dele subiu para 100% e
#: ele passou a reprovar uma rota NOMEAVEL (hdi/residencial/eletricista,
#: 95,6%). Um item que separa fica no placar.
ITENS_DE_PORTAO = frozenset({
    "transcrita no bloco do subservico",
    "notes com contagem que RECONTA",
    "toda tecla _opcao tem origem (3 fontes)",
    "nenhuma constante decide pelo cliente",
    "nenhuma ancora exige `*` literal",
    "teste nomeia a rota, chama o motor, toca >=3 telas",
    "a mutacao fica vermelha (EXECUTADA)",
    ">=1 linha de CONTROLE",
})


class Item(NamedTuple):
    eixo: str
    nome: str
    pontos: int
    maximo: int
    evidencia: str
    excluido: Optional[str] = None    # motivo, quando sai do denominador

    @property
    def portao(self) -> bool:
        """🔴 SPEC-089 B — este item GUARDA, nao PONTUA. Ver `ITENS_DE_PORTAO`."""
        return self.nome in ITENS_DE_PORTAO

    @property
    def fechado(self) -> bool:
        """O portao esta fechado? (item cheio = nenhuma ma pratica presente)"""
        return self.pontos >= self.maximo

    @property
    def conta(self) -> bool:
        """Entra no PLACAR? ⛔ Portao nao entra: ele guarda, nao pontua."""
        return self.excluido is None and not self.portao


class Nota(NamedTuple):
    rota: Any
    itens: List[Item]
    estado: Optional[str]             # NAO_RESPONDE · SEM_CORPUS · None
    replay: Optional[RP.Replay]

    @property
    def pontos(self) -> int:
        return sum(i.pontos for i in self.itens if i.conta)

    @property
    def denominador(self) -> int:
        return sum(i.maximo for i in self.itens if i.conta)

    @property
    def fora(self) -> Dict[str, int]:
        """O que SAIU do denominador, por MOTIVO de exclusao.

        🔴 SPEC-089 BLOCO B — **portao nao entra aqui**, e o guarda pegou.

        ⚠️ Este laco era `if not i.conta`, e `conta` passou a devolver `False`
        tambem para os portoes. Resultado: `fora` virou
        `{None: 36, "SEM_FABRICA": 7}` — uma chave `None` que nao e motivo de
        nada, somando 36 pontos a uma tabela que quem le interpreta como
        *"itens que nao se aplicam a esta rota"*.

        ⛔ **Sair do denominador e ser portao sao coisas diferentes:**

            fora     .... o item NAO SE APLICA a rota (SEM_FABRICA, ...)
            portao   .... o item se aplica, GUARDA, e nao pontua
        """
        d: Dict[str, int] = {}
        for i in self.itens:
            if i.excluido is not None:
                d[i.excluido] = d.get(i.excluido, 0) + i.maximo
        return d

    @property
    def fracao(self) -> float:
        return self.pontos / self.denominador if self.denominador else 0.0

    def por_eixo(self) -> Dict[str, Tuple[int, int]]:
        d: Dict[str, List[int]] = {}
        for i in self.itens:
            if not i.conta:
                continue
            a = d.setdefault(i.eixo, [0, 0])
            a[0] += i.pontos
            a[1] += i.maximo
        return {k: (v[0], v[1]) for k, v in d.items()}

    @property
    def portoes(self) -> List[Item]:
        """Os itens que GUARDAM — SPEC-089 BLOCO B.

        ⚠️ Um portao EXCLUIDO (`SEM_FABRICA`) nao guarda nada: a rota nao tem
        onde ter a ma pratica. Ele sai dos dois lados.
        """
        return [i for i in self.itens if i.portao and i.excluido is None]

    @property
    def portoes_abertos(self) -> List[Item]:
        """🔴 Os que a rota NAO fechou. Cada um bloqueia o AAA."""
        return [i for i in self.portoes if not i.fechado]

    @property
    def patamar(self) -> str:
        """🔴 O patamar CARREGA o denominador: `AAA(90)`, `quase(100)`.

        Sem isso, `86/90 = 95,6%` vira AAA e `94/100 = 94%` não vira — e a rota de
        auto foi **dispensada** de `regras_para_o_cliente`, de
        `expectativa_do_desfecho` e da transcrição. "AAA" passaria a significar
        coisas diferentes na mesma tabela.
        """
        if self.estado:
            return self.estado
        p = 100 * self.fracao
        nome = ("AAA" if p >= 95 else "quase" if p >= 80 else "parcial" if p >= 55
                else "esqueleto" if p >= 25 else "toco")
        # =================================================================
        # 🔴 SPEC-089 BLOCO B — PORTAO ABERTO NAO CHEGA A AAA
        # =================================================================
        #
        # ⚠️ Um portao guarda a AUSENCIA de uma ma pratica: uma constante
        # decidindo pelo cliente, uma ancora que exige `*`, um teste que nao
        # chama o motor. **Nenhuma dessas coisas se compensa com pontos.**
        #
        # ⛔ Antes elas valiam 44 pontos que 43 de 43 rotas ganhavam — o item
        # nao separava nada e ainda inflava a nota. Agora ele nao pontua e
        # BLOQUEIA: a rota fica em `quase`, com o portao nomeado ao lado.
        abertos = self.portoes_abertos
        if abertos and nome == "AAA":
            nome = "quase"
        marca = f"!{len(abertos)}" if abertos else ""
        return f"{nome}({self.denominador}){marca}"


# ═════════════════════════════════════════════════════════════════════════════
# A MARCA DA ROTA — três níveis, e por que não pode ser só o `_opcao` (§3.2)
# ═════════════════════════════════════════════════════════════════════════════
def marca_da_rota(pb: Dict[str, Any], servico: str) -> Tuple[Optional[str], str]:
    """Como se sabe que ESTA rota foi percorrida, e não a vizinha do mesmo menu.

    🔴 *"Menu que LISTA o serviço não é prova de que o serviço foi PERCORRIDO."*
    📊 As quatro rotas da alfa aparecem exatamente nas mesmas 5 sessões — porque a
    tela de menu lista os quatro de uma vez. Uma sessão de guincho que chegou ao
    protocolo daria 12 pontos às quatro, inclusive às três nunca percorridas.

    Três níveis, nesta ordem:
      1. a chave `<x>_opcao` do `subservices` cujo par (chave, valor) é ÚNICO
      2. o valor de `subservice_menu_map[rota]`, se único no playbook
      3. um passo com `only_subservices` que cite a rota

    🔴 **Por que três, e não só o `_opcao`:** 📊 `_AUTO_SUBSERVICES` **não tem
    nenhuma chave `_opcao`** — os 10 corredores de auto recebem a tecla em
    `subservice_menu_map`, chave separada. Exigir o `_opcao` tornaria o item
    insatisfazível para as **40 rotas de auto**, e o eixo A cairia para 4/20
    **por onde o código mora**.
    """
    subs = pb.get("subservices") or {}
    meu = subs.get(servico) or {}

    # ── nível 1 · a chave `_opcao` única ────────────────────────────────────
    for chave, valor in meu.items():
        if not chave.endswith("_opcao"):
            continue
        iguais = [s for s, d in subs.items() if (d or {}).get(chave) == valor]
        if len(iguais) == 1:
            return f"{chave}={valor}", "nivel-1-opcao"

    # ── nível 2 · `subservice_menu_map`, RENDERIZADO ────────────────────────
    # 🔴 Não basta olhar o `requires`: 📊 os passos de auto declaram
    #    `"reply": "{servico_opcao}"` com `"requires": ["servico_opcao"]` — **o
    #    mesmo nome de slot para as quatro rotas**. A marca está no VALOR.
    menu = pb.get("subservice_menu_map") or {}
    if servico in menu:
        valor = menu[servico]
        iguais = [s for s, v in menu.items() if v == valor]
        if len(iguais) == 1:
            return f"menu={valor}", "nivel-2-menu"

    # ── nível 3 · um passo com `only_subservices` que cite a rota ───────────
    for p in pb.get("ura_steps") or []:
        so = p.get("only_subservices") or []
        if servico in so and len(so) == 1:
            return f"only_subservices={p.get('step')}", "nivel-3-only"

    # ⚠️ 📊 São 8 rotas em que a marca não existe: mapfre mapeia os quatro
    #    serviços para "Assistência 24H"; bradesco dá "1" para guincho E bateria;
    #    zurich dá "4" para guincho E bateria. O item SAI DO DENOMINADOR — nunca 0.
    return None, ROTA_INDISTINGUIVEL


def _fonte_do_bloco(servico: str) -> Optional[str]:
    """O trecho de `corridor_playbooks.py` onde o subserviço é declarado.

    ⚠️ 📊 Os 4 corredores residenciais são dicts literais — há onde escrever a
    transcrição. Os 10 de auto são one-liners dentro de `_AUTO_SUBSERVICES`.

    🔴 C14 — A JANELA ESTAVA VAZANDO, e vazava de dois jeitos ao mesmo tempo.

    A versão anterior recortava do **último parágrafo em branco ANTES** do
    bloco até o primeiro `\n        },` (oito espaços fixos). Medido em
    23/08/2026:

    ```
    _fonte_do_bloco("bateria")  ->  14.704 chars
    _fonte_do_bloco("guincho")  ->  14.704 chars   <- A MESMA JANELA
    _fonte_do_bloco("eletricista") -> 42.322 chars
    ```

    Os one-liners de auto têm 4 espaços de recuo: o `\n        },` nunca casa,
    e a janela corre até o próximo fechamento de 8 espaços, muito abaixo. Uma
    citação escrita em qualquer ponto desses 14,7 KB creditava **as quatro
    rotas de auto de uma vez**.

    🔴 E o começo era pior que o fim: depender do último parágrafo em branco
    faz a janela desta rota depender do CÓDIGO DA ROTA VIZINHA. 📊 Foi assim
    que `maquina_de_lavar` caiu de 106 para 102 quando o `eletricista` — o
    bloco de cima — ganhou linhas em branco entre as frases das regras.

    ⚠️ **O docstring anterior prometia `SEM_FABRICA` para as ~40 rotas de auto
    e o código não fazia isso** — a regex casa o one-liner. Era §9.3 na forma
    pura: documento a dizer uma coisa, código a fazer outra. Agora o bloco de
    auto é uma janela pequena e honesta: quem quiser os 4 pontos escreve a
    citação DENTRO dele, e ela vale só para ele.
    """
    with open(FONTE_DO_CORREDOR, encoding="utf-8") as fh:
        fonte = fh.read()
    padrao = re.compile(r'^(\s*)"' + re.escape(servico) + r'"\s*:\s*\{', re.M)
    m = padrao.search(fonte)
    if not m:
        return None
    recuo = m.group(1)
    # 🔴 O fim é o fechamento NO MESMO RECUO — é o que delimita ESTE dict.
    #    E o one-liner fecha na própria linha: `"bateria": {"required_slots": …},`
    fim_da_linha = fonte.find("\n", m.start())
    linha = fonte[m.start():fim_da_linha if fim_da_linha > 0 else len(fonte)]
    if linha.rstrip().endswith("},") and linha.count("{") == linha.count("}"):
        # ⚠️ One-liner: a janela é a linha, mais os COMENTÁRIOS colados acima —
        #    é onde a citação cabe sem inventar estrutura. Colados: a primeira
        #    linha que não for comentário fecha a janela para cima.
        ini = m.start()
        while True:
            anterior = fonte.rfind("\n", 0, ini - 1)
            trecho = fonte[anterior + 1:ini]
            if not trecho.strip().startswith("#"):
                break
            ini = anterior + 1
            if ini <= 0:
                break
        return fonte[ini:fim_da_linha if fim_da_linha > 0 else len(fonte)]

    fecha = fonte.find("\n" + recuo + "},", m.end())
    if fecha < 0:
        return None
    # ⚠️ E os comentários colados ACIMA da chave entram na janela: é onde os
    #    blocos residenciais já escrevem o cabeçalho, e tirá-los agora
    #    derrubaria rotas por motivo estrutural. Mas só os COLADOS — uma linha
    #    em branco fecha a janela, e é isso que impede o vazamento do vizinho.
    ini = m.start()
    while True:
        anterior = fonte.rfind("\n", 0, ini - 1)
        if anterior < 0:
            break
        trecho = fonte[anterior + 1:ini]
        if not trecho.strip().startswith("#"):
            break
        ini = anterior + 1
    return fonte[ini:fecha + len(recuo) + 3]

def eixo_a(rota, r: RP.Replay) -> List[Item]:
    pb = M.get_playbook(rota.ref)
    itens: List[Item] = []

    marca, nivel = marca_da_rota(pb, rota.servico)
    # ── 12 · a ROTA foi percorrida até o fim ────────────────────────────────
    if marca is None:
        itens.append(Item("A", "a ROTA foi percorrida ate o fim", 0, 12,
                          "a URA nao distingue este servico do vizinho no menu",
                          excluido=ROTA_INDISTINGUIVEL))
    else:
        # 🔴 pelo MOTOR, nunca por regex do script. `extract_capture_anchors`
        #    devolve o GRUPO CAPTURADO — é o que distingue o protocolo de verdade
        #    do artigo "os" seguido de dígitos (§3.2).
        com_protocolo = [t for t in r.telas
                         if M.extract_capture_anchors(pb, t.texto).get("protocol")]
        sessoes_fim = {t.session_id for t in com_protocolo}
        # e a sessão tem de trazer a MARCA DA ROTA
        sessoes_da_rota = {t.session_id for t in r.telas if t.classe == RP.RESPONDIDA}
        boas = sessoes_fim & sessoes_da_rota
        itens.append(Item("A", "a ROTA foi percorrida ate o fim", 12 if boas else 0, 12,
                          (f"{len(boas)} sessao(oes) com protocolo E marca da rota "
                           f"({nivel}: {marca}): {' '.join(sorted(boas)) or '-'}")))

    # ── 4 · a transcrição no bloco do subserviço ───────────────────────────
    # 🔴 C17: o endereço é DA ROTA, não do serviço. Ver `_transcricao_da_rota`.
    bloco = _transcricao_da_rota(rota)
    if bloco is None:
        itens.append(Item("A", "transcrita no bloco do subservico", 0, 4,
                          "o subservico vem de `_auto_playbook`, nao ha bloco onde escrever",
                          excluido=SEM_FABRICA))
    else:
        achadas = re.findall(r"sess[ãa]o\s+([0-9a-f]{8})", bloco)
        no_corpus = [s for s in achadas if any(t.session_id == s for t in r.telas)]
        itens.append(Item("A", "transcrita no bloco do subservico",
                          4 if no_corpus else 0, 4,
                          f"sessoes citadas no bloco: {achadas or '(nenhuma)'} | "
                          f"presentes no corpus: {no_corpus or '(nenhuma)'}"))

    # ── 2 · ≥2 sessões distintas da rota ───────────────────────────────────
    itens.append(Item("A", ">=2 sessoes distintas", 2 if r.sessoes_no_corpus >= 2 else 0, 2,
                      f"{r.sessoes_no_corpus} sessoes no corpus"))

    # ── 2 · a mais recente tem <180 dias ───────────────────────────────────
    ts = max((t.wa_timestamp for t in r.telas), default="")
    dias = None
    if ts:
        try:
            d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            dias = (dt.datetime.now(dt.timezone.utc) - d).days
        except ValueError:
            dias = None
    itens.append(Item("A", "a mais recente tem <180 dias",
                      2 if (dias is not None and dias < 180) else 0, 2,
                      f"mais recente: {ts[:10] or '-'} ({dias} dias)"))
    return itens


# ═════════════════════════════════════════════════════════════════════════════
# EIXO B — COBERTURA (35). O peso está aqui: é a única medida que reproduziu.
# ═════════════════════════════════════════════════════════════════════════════
def _transcricao_da_rota(rota) -> Optional[str]:
    """Onde ESTA rota pode escrever a própria transcrição.

    🔴 C17 — 26 ROTAS NÃO TINHAM ONDE ESCREVER.

    `_fonte_do_bloco` é indexado por SERVIÇO, e serviço não identifica rota.
    📊 Medido em 23/08/2026, nas 41 rotas que têm telas:

    ```
     8  ganham o item
    22  o bloco tem citação, mas de OUTRA rota
     4  o bloco não tem citação nenhuma
     7  SEM_FABRICA
    ```

    As 22 são o caso interessante. `hdi/auto/guincho` lê o mesmo one-liner de
    `_AUTO_SUBSERVICES["guincho"]` que `allianz/auto/guincho` — e lá está
    escrita a sessão `dc6c0345`, que é da allianz. O item faz a coisa certa e
    não credita a hdi (a sessão tem de estar no corpus DA ROTA). Mas então a
    hdi não tem lugar nenhum: escrever a sessão dela naquele comentário seria
    empilhar dez transcrições de dez seguradoras antes de uma linha de código.

    🔴 E `chaveiro` é pior: o primeiro `"chaveiro": {` do arquivo é o do
    corredor RESIDENCIAL da Allianz. `hdi/auto/chaveiro`,
    `porto/residencial/chaveiro` e `yelum/residencial/chaveiro` liam todos o
    bloco de um corredor que não é o delas.

    A rota passa a ter um endereço próprio: um comentário aberto por

        # ROTA <seguradora>/<ramo>/<serviço>

    e a janela é o bloco de comentário CONTÍGUO a partir dele — a primeira
    linha que não for comentário fecha, como no C14.

    ⚠️ Isto NÃO afrouxa o item: a prova continua sendo a mesma, e é a que
    importa — a sessão citada tem de estar no corpus DESTA rota. O marcador só
    diz ONDE procurar. Quem escrever o marcador e citar sessão alheia continua
    com zero.

    📊 E o conserto sozinho não move nota nenhuma: no commit em que entra não
    existe um único marcador escrito. Ele abre a porta; atravessá-la é
    trabalho de corredor, uma rota por vez.
    """
    with open(FONTE_DO_CORREDOR, encoding="utf-8") as fh:
        fonte = fh.read()
    alvo = f"{rota.seguradora}/{rota.ramo}/{rota.servico}"
    padrao = re.compile(r"^([ \t]*)#[^\n]*\bROTA\s+" + re.escape(alvo) + r"\b",
                        re.M)
    m = padrao.search(fonte)
    if not m:
        # ⚠️ Sem marcador, vale o bloco do subserviço — é onde os corredores
        #    residenciais já escrevem, e tirá-los agora seria queda estrutural.
        return _fonte_do_bloco(rota.servico)
    # 🔴 A JANELA FECHA NA PRIMEIRA LINHA QUE NAO FOR COMENTARIO —
    #    **inclusive a linha EM BRANCO**, e e a mesma regra do C14.
    #
    # ⚠️ A primeira versao deste laco deixava a linha em branco passar, e o
    #    efeito apareceu no primeiro bloco com cinco marcadores seguidos:
    #    a janela de `porto/auto/bateria` engolia as sessoes citadas nos
    #    marcadores de chaveiro, tecnico e vidros. 📊 Medido: o item listava
    #    `[c470d13d, e3b1561f, d0d64bfc, e5318468, b1ff65f2]` para UMA rota.
    #    🔴 O C14 nasceu consertando exatamente isto -- a janela de uma rota
    #    nao pode depender do paragrafo da vizinha -- e o C17 repetiu o erro
    #    do outro lado do arquivo.
    fim = m.start()
    while True:
        prox = fonte.find("\n", fim)
        if prox < 0:
            fim = len(fonte)
            break
        linha = fonte[fim:prox]
        if not linha.lstrip().startswith("#"):
            break
        fim = prox + 1
    return fonte[m.start():fim]


_CORREDORES_DO_PASSO: Optional[Dict[Tuple[str, str], set]] = None


def corredores_do_passo() -> Dict[Tuple[str, str], set]:
    """`{(nome_do_passo, ancora): {(seguradora, ramo), ...}}` — quem CARREGA.

    🔴 C16 — O FILTRO DE FAMÍLIA APAGAVA O EXAME INTEIRO, E O ITEM DAVA ZERO
    POR VACUIDADE.

    A v3 deste item resolvia o passo compartilhado **excluindo-o**:
    `passos = [p for p in passos if _familia[step] <= 1]`. A intenção estava
    certa — *"um passo compartilhado não tem um número verdadeiro por
    corredor"* — mas o remédio apagava a pergunta em vez de respondê-la.

    📊 Medido em 23/08/2026, em `allianz/auto`: dos ~60 passos do corredor,
    **1 sobrevivia ao filtro**, e ele não tem número. Com `com_numero == 0`,
    a linha do `pn` cai no `else` e a rota leva **0 de 2** — por não ter nada
    que pudesse ser conferido. As quatro rotas de auto da Allianz, as quatro
    da alfa e mais 20 estavam nessa situação: um item que ninguém pode ganhar,
    exatamente o defeito que o C10 nomeou e que voltou por outra porta.

    ⚠️ E o efeito colateral é pior que o zero: qualquer executor que quisesse
    o ponto teria de **duplicar o passo** por corredor — a §5 do CLAUDE.md ao
    contrário, com a régua pagando por isso.

    🔴 A resposta certa já estava escrita uma linha acima, e só precisava de
    mais um passo: *"a note descreve um PASSO, e o passo é do corredor"*. Se
    o passo vive em N corredores, a contagem dele é a dos N — a mesma frase,
    levada até o fim.
    """
    global _CORREDORES_DO_PASSO
    if _CORREDORES_DO_PASSO is None:
        mapa: Dict[Tuple[str, str], set] = collections.defaultdict(set)
        for rt in M.rotas():
            _pb = M.get_playbook(rt.ref)
            if not _pb:
                continue
            for _p in _pb.get("ura_steps") or []:
                if _p.get("anchor"):
                    mapa[(str(_p.get("step") or ""), _p["anchor"])].add(
                        (rt.seguradora, rt.ramo))
        _CORREDORES_DO_PASSO = mapa
    return _CORREDORES_DO_PASSO


_CORPUS_DO_CORREDOR: Dict[Tuple[str, str], List[str]] = {}


def _corpus_de(seguradora: str, ramo: str) -> List[str]:
    chave = (seguradora, ramo)
    if chave not in _CORPUS_DO_CORREDOR:
        _CORPUS_DO_CORREDOR[chave] = [l["text"] for l in
                                      RP.carregar_corpus(seguradora, ramo)]
    return _CORPUS_DO_CORREDOR[chave]


def eixo_b(rota, r: RP.Replay) -> List[Item]:
    pb = M.get_playbook(rota.ref)
    itens: List[Item] = []

    # ── 20 · zero órfãs funcionais ─────────────────────────────────────────
    n = len(r.orfas_funcionais)
    pts = 20 if n == 0 else 10 if n == 1 else 4 if n == 2 else 0
    exemplo = (" ".join(r.orfas_funcionais[0].texto.split())[:70]
               if r.orfas_funcionais else "-")
    itens.append(Item("B", "zero orfas funcionais", pts, 20,
                      f"{n} orfa(s) funcional(is). {r.amostra}. primeira: {exemplo}"))

    # ── 8 · 100% determinístico ────────────────────────────────────────────
    #
    # ═════════════════════════════════════════════════════════════════════
    # 🔴 SPEC-089 BLOCO B — O CORTE ERA 85% E O PIOR ALUNO TEM 95,6%
    # ═════════════════════════════════════════════════════════════════════
    #
    # 📊 MEDIDO EM 26/08/2026, as 43 rotas com corpus:
    #
    #     minimo ....... 95,6%   (hdi/residencial/eletricista)
    #     mediana ...... 100,0%
    #     em 100,0% .... 42 de 43
    #
    #     corte  85%  ->  reprova  0 de 43     🔴 8 pontos de graca
    #     corte  96%  ->  reprova  1 de 43
    #     corte 100%  ->  reprova  1 de 43
    #
    # ⚠️ O item nao separava porque o corte estava **10,6 pontos abaixo do
    # pior aluno** — nao porque a propriedade seja irrelevante.
    #
    # 🔴 E o corte novo e 100%, nao 96%: **deterministico e' deterministico.**
    # 95,6% quer dizer que 4,4% das telas nao foram decididas pelo motor — e
    # sao justamente essas que o segurado ve quando o corredor erra.
    #
    # ⚠️ E a escada continua: 4 pontos em >=85% reconhece o meio do caminho.
    # ⛔ Zerar tudo abaixo de 100% seria trocar um item que nao reprova por
    # um que reprova igual, e nenhum dos dois separa.
    d = r.determinismo
    pd = 0 if d is None else (8 if d >= 0.9999 else 4 if d >= 0.85 else 0)
    itens.append(Item("B", "100% deterministico", pd, 8,
                      "sem denominador" if d is None else
                      f"{100*d:.0f}% ({r.respondidas} de {r.pedem_algo} telas que pedem algo)"))

    # ── 5 · o cliente recebe protocolo + dia + período ─────────────────────
    # 🔴 É literalmente a segunda metade da definição de rota AAA — *"e o segurado
    #    sabe o número do chamado, o dia e o período"* — e é o furo nº3 da §1.2.
    #    📊 Uma rota podia tirar 100 e mandar "Prontinho! Sua assistência foi
    #    aberta" sem data e sem período: exatamente o que a cliente recebeu.
    #
    # 🔴 O sinal é a CAPTURA, não `expectativa_do_desfecho`. 📊 Aquele campo existe
    #    em 1 de 14 playbooks: 56 rotas nunca diriam "agendado" e os 5 pontos
    #    virariam grátis. `schedule` é auto-consistente.
    captura: Dict[str, Any] = {}
    for t in r.telas:
        captura.update(M.extract_capture_anchors(pb, t.texto))
    # ======================================================================
    # 🔴 C1 — A RÉGUA MONTAVA A CHAVE ERRADA, E O ITEM DAVA 0 EM 73 DE 73
    # ======================================================================
    #
    # 📊 Medido em 22/08/2026, com a captura real da rota de referência:
    #
    #   session['capture']   -> None      <- o que a régua montava
    #   session['captures']  -> None      <- e a segunda tentativa dela
    #   session['captured']  -> "Prontinho! ✅ Sua assistência foi agendada
    #                            para o dia terca-feira, 06/01/2026..."
    #
    # `client_summary_from_capture` lê `session.get("captured")`
    # (`insurer_dispatch_service.py:2378`). As duas chaves que a régua montava
    # não existem para ele — e `captured.get("protocol")` num dicionário vazio
    # é falsy, então a função devolvia `None` **sempre**.
    #
    # 🔴 O item não media rota nenhuma: media um bug da própria régua. E ele
    #    ficou escondido porque `resumo = ... or ""` transformava o `None` em
    #    string vazia, e "vazio" parece "a rota não entrega" — não "eu não
    #    perguntei direito".
    #
    # ⚠️ `**captura` continua na base para o caso de algum consumidor futuro
    #    ler as chaves soltas; o que muda é que agora existe a chave CERTA.
    sessao_falsa = {"captured": captura,
                    "capture": captura, "captures": captura, **captura}
    try:
        resumo = M.client_summary_from_capture(sessao_falsa) or ""
    except Exception as e:                       # noqa: BLE001
        resumo = f"<erro: {e}>"
    prot = captura.get("protocol")
    sched = captura.get("schedule") or {}
    tem_prot = bool(prot) and str(prot) in resumo
    precisa_data = bool(sched)
    tem_data = (not precisa_data) or (
        str(sched.get("day", "")).lower()[:8] in resumo.lower()
        and any(str(sched.get(k, "")).lower()[:5] in resumo.lower()
                for k in ("periodo", "from", "at") if sched.get(k)))
    itens.append(Item("B", "o cliente recebe protocolo + dia + periodo",
                      5 if (tem_prot and tem_data) else 0, 5,
                      f"capturado: protocol={prot} schedule={sched or '-'} | "
                      f"no resumo ao cliente: protocolo={tem_prot} data/periodo={tem_data}"))

    # ── 2 · `notes` com contagem que RECONTA contra o corpus ───────────────
    # 📊 A regra anterior exigia o prefixo `📊 <seguradora>:`. Das 176 `notes` do
    #    produto, NENHUMA tem esse formato. Era o defeito espelhado do
    #    `_COMO_PERGUNTAR`: aquele não tinha como falhar; este, como passar.
    passos = [p for p in (pb.get("ura_steps") or [])
              if not p.get("only_subservices") or rota.servico in p["only_subservices"]]
    # ⚠️ 🔴 O PASSO COMPARTILHADO FICA — o que muda e ONDE ele e recontado.
    #
    #    📊 `avisos_informativos_familia` vive em alfa E allianz. A note dele
    #    dizia "5 telas" -- verdade num corredor -- e a v2 do item acusava de
    #    mentira uma nota certa. A v3 consertou isso EXCLUINDO o passo, e assim
    #    apagou 59 dos 60 passos de `allianz/auto`: com nada a conferir, o item
    #    dava 0 de 2 por vacuidade. Ver `corredores_do_passo`.
    #
    #    Agora a note de um passo compartilhado declara a contagem DOS
    #    CORREDORES QUE O CARREGAM, e e recontada na mesma populacao.
    com_numero, reproduzem = 0, 0
    for p in passos:
        nota = p.get("notes") or ""
        # ⚠️ A PRIMEIRA afirmacao medida da note, e a unidade colada nela.
        #    📊 `r"(\d+)\s*ocorr"` solto pegava numero de OUTRA frase:
        #    porto/residencial `menu_raiz` diz *"13 msgs / 8 sessoes ...
        #    SINGULAR, 8 de 8 ocorrencias"* -- o `8 ocorr` fala do ROTULO ser
        #    singular, nao da contagem do passo, que e 13. A regua acusava a
        #    note de "a parte maior que o todo" por ler a frase errada.
        m = re.search(r"(\d+)\s*(?:msgs?|telas?|ocorr\w*)", nota)
        if not m:
            continue
        com_numero += 1
        declarado = int(m.group(1))
        anc = p.get("anchor")
        if not anc:
            continue
        # ==============================================================
        # 🔴 C10 — O ITEM ERA IMPOSSIVEL: 0/2 EM 73 DE 73
        # ==============================================================
        #
        # 📊 Medido em 22/08/2026: **nenhuma das 73 rotas** ganhava um ponto
        #    sequer aqui. Um item que ninguem pode ganhar nao mede nada -- ele
        #    so tampa toda rota em 100/102, em silencio. Mesmo formato do C1.
        #
        # A causa: as duas pontas contavam populacoes DIFERENTES.
        #    o numero da `note`  <- medido no ACERVO (28.096 eventos)
        #    o recount da regua  <- feito no CORPUS versionado (781 telas
        #                           no residencial da Allianz), e ainda
        #                           filtrado pela ROTA (102 telas)
        #
        # 📊 `menu_tipo_servico` declara 64; a rota ve 4 e o corredor ve 32.
        #    Nenhuma tolerancia de +-20% fecha isso, **e nao deveria**: os
        #    numeros das notes estao CERTOS, so nao sao do corpus.
        #
        # 🔴 A PERGUNTA REPRODUZIVEL, e ela pode falhar:
        #    **o corpus e AMOSTRA do acervo, entao a contagem dele nunca pode
        #    EXCEDER o numero declarado** -- e a ancora tem de achar ao menos
        #    uma tela, senao a note descreve algo que nao existe mais.
        #
        # 📊 E o criterio ja acusou um defeito real:
        #    `porto/residencial menu_raiz` declara 8 e o corpus tem 13.
        #    A parte maior que o todo.
        #
        # ⚠️ Reconta no corpus dos CORREDORES QUE CARREGAM O PASSO, nao no da
        #    rota: a `note` descreve um PASSO. Se ele vive em alfa e allianz,
        #    o numero dele e o das duas -- e e por isso que a populacao aqui
        #    nao e mais um corredor so (C16).
        try:
            _corpus = [t for _ck in corredores_do_passo()[(str(p.get("step") or ""), anc)]
                       for t in _corpus_de(*_ck)] or _corpus_de(rota.seguradora, rota.ramo)
            # 🔴 TELAS DISTINTAS, e a unidade e a que a PROPRIA note usa.
            #    📊 A note escreve `N telas / M sessoes`. Contar OCORRENCIAS
            #    comparava o N com o M e acusava 12 notes CERTAS de mentir:
            #       cnpj_condominio  "1 tela / 5 sessoes"  -> 5 ocorrencias
            #       link_por_sms     "1 tela / 10 sessoes" -> 10 ocorrencias
            #    Com telas distintas, **20 das 21 recontam** -- e a 21a era
            #    defeito de verdade. Mesmo erro de unidade que a base do E13
            #    cometeu no mesmo dia (rota x tela em vez de linha de corpus).
            real = len({M._norm(t) for t in _corpus
                        if re.search(anc, M._norm(t), re.I)})
        except re.error:
            continue
        if declarado and 1 <= real <= declarado:
            reproduzem += 1
    pn = 2 if (com_numero and reproduzem == com_numero) else (1 if reproduzem else 0)
    itens.append(Item("B", "notes com contagem que RECONTA", pn, 2,
                      f"{reproduzem} de {com_numero} notes com numero reproduzem "
                      f"(+-20%) contra o corpus; {len(passos)} passos na rota"))
    return itens


# ═════════════════════════════════════════════════════════════════════════════
# EIXO C — SEGURANÇA (20). Quando errar dói, o corredor para?
# ═════════════════════════════════════════════════════════════════════════════
# 🔴 As teclas têm TRÊS origens, não duas. 📊 `telefone_adicionar_opcao` é exigido
#    pelo passo `confirmar_telefone`, NÃO está no subserviço e NÃO está em
#    `_derivar_teclas_do_caso`: nasce inline em `new_dispatch_session`.
#    Com duas fontes, **a própria régua reprovaria**.
TECLAS_INLINE = {"telefone_adicionar_opcao"}


def eixo_c(rota, r: RP.Replay) -> List[Item]:
    pb = M.get_playbook(rota.ref)
    itens: List[Item] = []

    # ── 8 · o freio casa ≥1 tela REAL do corpus ────────────────────────────
    # 📊 Vale 8 porque é a última porta antes de mandar um prestador a um
    #    endereço. A ausência dele no residencial deixou 65 sessões passarem pela
    #    conferência sem verificação nenhuma.
    freio = [t for t in r.telas if M.detect_finalize_anchor(pb, t.texto)]
    itens.append(Item("C", "o freio casa >=1 tela REAL", 8 if freio else 0, 8,
                      f"{len(freio)} tela(s) armam o freio. {r.amostra}"))

    # ── 6 · toda tecla `_opcao` tem origem nas TRÊS fontes ─────────────────
    # 📊 Vale 6 porque tecla errada NÃO trava — abre o chamado errado. `14` é
    #    máquina de lavar; `10` é lava-louças; `13` é secadora. O erro só aparece
    #    quando o técnico chega.
    # ======================================================================
    # 🔴 C3 — A RÉGUA REIMPLEMENTAVA A ORIGEM, E DIVERGIA NOS DOIS SENTIDOS
    # ======================================================================
    #
    # É o MOTOR PARALELO que o CLAUDE.md §5 proíbe, dentro da régua. E ele
    # errava para os dois lados AO MESMO TEMPO:
    #
    #   FROUXA   `re.search('"chave"', fonte_inteira)` aceitava a chave citada
    #            em QUALQUER lugar do arquivo — inclusive num COMENTÁRIO
    #   ESTRITA  não conhecia `required_slots` (coleta) nem
    #            `_slots_com_padrao_do_motor` — duas das quatro origens que o
    #            produto usa, e que a própria §E4 desta SPEC lista
    #
    # E havia um terceiro erro, mais simples: `exigidas` juntava as `requires`
    # de TODOS os passos do corredor, inclusive os de outros ofícios. Uma rota
    # de `eletricista` era cobrada pela tecla do `chaveiro`.
    #
    # 📊 Medido na rota de referência: as 5 "teclas órfãs" TÊM origem, e quem
    #    sabe é o produto —
    #      caixa_litros_opcao ............. ['coleta']
    #      caixas_dagua_quantidade_opcao .. ['coleta']
    #      idade_aparelho_opcao ........... ['coleta']
    #      profissional_opcao ............. ['constante-por-subservico']
    #      qual_seguro_opcao .............. ['coleta']
    #
    # 📊 E o efeito de cada metade, medido nas 41 rotas com corpus:
    #      régua de hoje ............. 9/41 zeram o item
    #      + só o filtro ............ 25/41
    #      + só origens_do_slot ..... 23/41
    #      + os dois ................ 36/41   <- os dois juntos, e é o certo
    #
    # 🔴 O conserto NÃO é escrever um filtro melhor: é PARAR DE REIMPLEMENTAR e
    #    perguntar ao produto, que já responde isso em `conferir_respostas`.
    import conferir_respostas as CR
    _derivados = CR._slots_derivados()
    exigidas: Set[str] = set()
    for p in pb.get("ura_steps") or []:
        # ⚠️ SÓ os passos que ESTA rota percorre. Cobrar de `eletricista` a
        #    tecla do `chaveiro` é medir a rota errada.
        if p.get("only_subservices") and rota.servico not in p["only_subservices"]:
            continue
        for req in p.get("requires") or []:
            if req.endswith("_opcao"):
                exigidas.add(req)
    orfas = {k for k in exigidas
             if not CR.origens_do_slot(pb, k, _derivados)} - TECLAS_INLINE
    itens.append(Item("C", "toda tecla _opcao tem origem (3 fontes)",
                      6 if not orfas else 0, 6,
                      f"{len(exigidas)} teclas exigidas; sem origem: "
                      f"{sorted(orfas) or 'nenhuma'}"))

    # ── 6 · C7 · nenhuma CONSTANTE decide pelo cliente sem justificativa ───
    # ======================================================================
    # 🔴 C7 — "DECLARADO E NUNCA LIDO", O DEFEITO QUE ESTE REPO JA PAGOU 3x
    # ======================================================================
    #
    # 📊 Medido em 22/08/2026: `grep -c constante_justificada rubrica.py` -> **0**.
    #    A regua consultava `conferir_respostas` SO para a origem do slot. A
    #    regra B -- o corredor afirmando um fato sobre o segurado -- nao valia
    #    ponto nenhum. Uma rota com 12 constantes decidindo por conta propria
    #    tirava 95/100.
    #
    # 🔴 **Uma regra que so existe no documento nao e regra. E intencao.**
    #    Mesmo defeito de `TETO_DE_INDEFINIDO`, `schedule_agendado` e
    #    `ticket_de_entrada`.
    #
    # **Por que 6, e nao outro numero:** e o mesmo peso e o MESMO MODO DE FALHA
    # do item vizinho de origem de tecla -- *"tecla errada NAO trava: abre o
    # chamado errado, e o erro so aparece quando o tecnico chega"*.
    # `situacao_risco -> "Nenhuma das anteriores"` falha exatamente assim.
    #
    # ⚠️ A pergunta e a MESMA `decide_pelo_cliente()` da varredura, chamada --
    #    nao reescrita. Reimplementa-la aqui seria o C3 pela terceira vez.
    textos_do_corredor = [l["text"] for l in
                          RP.carregar_corpus(rota.seguradora, rota.ramo)]
    decidem = CR.constantes_sem_justificativa(pb, rota.servico, textos_do_corredor)
    itens.append(Item("C", "nenhuma constante decide pelo cliente",
                      6 if not decidem else 0, 6,
                      f"{len(decidem)} constante(s) decidem sem justificativa: "
                      + (", ".join(f"{p}->{r}" for p, r, _ in decidem) or "nenhuma")))

    # ── 3 · o handoff casa ≥1 tela REAL ────────────────────────────────────
    hand = [t for t in r.telas if M.detect_handoff_trigger(pb, t.texto)]
    itens.append(Item("C", "o handoff casa >=1 tela REAL", 3 if hand else 0, 3,
                      f"{len(hand)} tela(s) disparam handoff. "
                      f"gatilhos: {pb.get('handoff_triggers') or '-'}"))

    # ── 3 · nenhuma âncora exige `*` literal ───────────────────────────────
    # 📊 `\*dica:\*` exigia asterisco literal num texto que `_norm` já removeu —
    #    âncora morta desde 17/08 que deixou um gate VERMELHO em produção.
    #    ⚠️ Isto é regex sobre a âncora COMO TEXTO, para conferir a FORMA da
    #    declaração — legítimo, e declarado como exceção na §9.4 do CLAUDE.md.
    literal = re.compile(r"\\\*(?!\?)")
    mortas = [p.get("step") for p in pb.get("ura_steps") or []
              if p.get("anchor") and literal.search(p["anchor"])]
    itens.append(Item("C", "nenhuma ancora exige `*` literal",
                      3 if not mortas else 0, 3,
                      f"ancoras com `\\*` obrigatorio: {mortas or 'nenhuma'}"))
    return itens


# ═════════════════════════════════════════════════════════════════════════════
# EIXO D — CONHECIMENTO (10)
# ═════════════════════════════════════════════════════════════════════════════
def eixo_d(rota, r: RP.Replay, *, tem_espelho: bool = False) -> List[Item]:
    pb = M.get_playbook(rota.ref)
    itens: List[Item] = []

    # ── 4 · os apelidos vêm do ESPELHO, não do corpus ──────────────────────
    # 🔴 O corpus só guarda `direction='in'` — as telas da URA. As palavras do
    #    SEGURADO não estão lá; vivem no Espelho (`conversations`/`messages`).
    #    📊 E o falso positivo que a regra antiga produzia: "lavadora" marca 23
    #    vezes no corpus da Allianz porque a URA escreve "Lavadora de louças" no
    #    menu Linha Branca — **outro eletrodoméstico**.
    apelidos = [k for k, v in (M.CP._SUBSERVICE_ALIASES or {}).items()
                if v == rota.servico]
    if not tem_espelho:
        # ══════════════════════════════════════════════════════════════════
        # 🔴 SPEC-089 BLOCO A — ZERO, E DENTRO DO DENOMINADOR
        # ══════════════════════════════════════════════════════════════════
        #
        # 📊 Este `excluido=SEM_ESPELHO` era o caminho PADRÃO da ferramenta:
        # `--todas` sem a flag. E ele fazia a nota SUBIR por medir menos —
        # 📊 27 de 43 rotas, e DEZ delas viravam AAA só por isso.
        #
        #     allianz/auto/bateria   sem: 102/102 = 100,00% AAA(102)
        #                            com: 102/106 =  96,23% AAA(106)
        #
        # ⛔ **`AAA(102)` deixa de existir.** Duas notas com o mesmo número e
        # denominadores diferentes são duas coisas diferentes, e hoje elas se
        # pareciam. A única AAA possível passa a ser a que mediu.
        #
        # ⚠️ E a evidência DIZ o motivo — quem lê precisa distinguir "a rota é
        # ruim" de "ninguém mediu esta parte".
        itens.append(Item("D", "apelidos do jeito que o cliente fala",
                          0, 4, f"{SEM_ESPELHO}: {len(apelidos)} apelidos "
                          f"declarados e NENHUM conferido — rode com "
                          f"`--com-espelho`. Zero NAO MEDIDO vale zero, "
                          f"nao vale nada (SPEC-089 A)"))
    else:
        # ==================================================================
        # 🔴 C6 — E AQUI O ITEM PASSOU A CONFERIR, EM VEZ DE CONTAR
        # ==================================================================
        #
        # ⚠️ A versao anterior deste ramo dava 4 pontos por
        # `len(apelidos) >= 3` — ou seja, **por existirem tres strings no
        # codigo**. Ligar a flag sem mudar isto teria dado os 4 pontos a 35
        # rotas sem que ninguem conferisse uma palavra de cliente: seria o
        # afrouxamento que a §2.2 proibe, disfarcado de ferramenta nova.
        #
        # A E8 pede DUAS provas, e as duas rodam aqui:
        #   1. cada apelido CONFERIDO no Espelho, com a contagem
        #   2. 🔴 o CONTROLE NEGATIVO: o apelido nao pode casar o nome de
        #      OUTRO servico do mesmo menu (`lavadora` x "Lavadora de loucas")
        conferidos = M.apelidos_conferidos(rota.servico, apelidos)
        vivos = {a: n for a, n in conferidos.items() if n > 0}
        colisoes = {a: c for a in apelidos
                    if (c := M.apelido_colide(a, rota.servico, pb))}
        ok = len(vivos) >= 3 and not colisoes
        detalhe = (f"{len(apelidos)} declarados, {len(vivos)} CONFERIDOS no "
                   f"Espelho: {sorted(vivos.items(), key=lambda kv: -kv[1])[:4]}")
        if colisoes:
            detalhe += f" | 🔴 COLIDEM com outro servico: {colisoes}"
        itens.append(Item("D", "apelidos do jeito que o cliente fala",
                          4 if ok else 0, 4, detalhe))

    # ── 3 · `expectativa_do_desfecho` ──────────────────────────────────────
    sub = (pb.get("subservices") or {}).get(rota.servico) or {}
    exp = sub.get("expectativa_do_desfecho") or pb.get("expectativa_do_desfecho")
    tem_fabrica = _fonte_do_bloco(rota.servico) is not None
    if not tem_fabrica:
        itens.append(Item("D", "expectativa_do_desfecho existe", 0, 3,
                          "sem bloco literal onde declarar", excluido=SEM_FABRICA))
    else:
        itens.append(Item("D", "expectativa_do_desfecho existe", 3 if exp else 0, 3,
                          f"{str(exp)[:70] if exp else '(ausente)'}"))

    # ── 3 · `regras_para_o_cliente` com trecho que CASA o corpus ───────────
    # ======================================================================
    # 🔴 C4 — O FALLBACK CREDITAVA A REGRA DO CORREDOR A TODA ROTA DELE
    # ======================================================================
    #
    # `sub.get(...) or pb.get(...)`: bastava UMA regra escrita no nível do
    # corredor para que TODAS as rotas dele marcassem o ponto.
    #
    # 📊 Medido: **9 rotas recebiam o crédito · 2 têm regra própria.**
    #    O item diz "regras_para_o_cliente casam o corpus" — e o que ele passou
    #    a medir foi "existe alguma regra em algum lugar deste corredor".
    #
    # ⚠️ ESTE CONSERTO SUBTRAI, DE PROPÓSITO: 7 rotas perdem 3 pontos porque
    #    paravam de receber crédito indevido. **Queda declarada é aprovação.**
    #    Uma régua que só sobe não é régua.
    #
    # 🔴 E ele NÃO afrouxa nem endurece a regra: a regra sempre foi "a rota tem
    #    a sua regra". O que mudou é que agora ela é lida onde estava escrita.
    regras = sub.get("regras_para_o_cliente")
    if not tem_fabrica:
        itens.append(Item("D", "regras_para_o_cliente casam o corpus", 0, 3,
                          "sem bloco literal onde declarar", excluido=SEM_FABRICA))
    else:
        # ==================================================================
        # 🔴 C5 — PROCURAVA A PROVA NO COMENTÁRIO, NÃO NA REGRA
        # ==================================================================
        #
        # A janela de 40 caracteres era buscada em QUALQUER linha do bloco que
        # tivesse `📊` — ou seja, em qualquer COMENTÁRIO. 📊 Efeito medido: uma
        # `regras_para_o_cliente` **inventada** tirava 3/3, desde que existisse
        # em algum lugar do bloco um comentário citando o corpus.
        #
        # 🔴 O item promete "regras_para_o_cliente casam o corpus". Ele media
        #    "algum comentário deste bloco casa o corpus" — e as duas coisas só
        #    coincidem por acaso.
        #
        # A prova tem de sair de DENTRO do que a atendente vai ler.
        casa = False
        trecho = ""
        corpus_norm = [M._norm(t.texto) for t in r.telas]

        def _textos(v):
            """As frases de `regras_para_o_cliente`, seja lista, dict ou str."""
            if isinstance(v, str):
                return [v]
            if isinstance(v, (list, tuple)):
                return [x for i in v for x in _textos(i)]
            if isinstance(v, dict):
                return [x for i in v.values() for x in _textos(i)]
            return []

        # janela deslizante de >=40 caracteres — NUNCA a frase inteira, e NUNCA
        # um comentário: só o texto que vai ao cliente.
        for frase in _textos(regras):
            texto = M._norm(frase)
            for i in range(0, max(1, len(texto) - 40)):
                jan = texto[i:i + 40]
                if len(jan) >= 40 and any(jan in c for c in corpus_norm):
                    casa, trecho = True, jan
                    break
            if casa:
                break
        itens.append(Item("D", "regras_para_o_cliente casam o corpus",
                          3 if (regras and casa) else 0, 3,
                          f"regras={'sim' if regras else 'nao'}; "
                          f"trecho de >=40 char que casa o corpus: "
                          f"{repr(trecho) if casa else 'nenhum'}"))
    return itens


# ═════════════════════════════════════════════════════════════════════════════
# EIXO E — PROVA (15). Se alguém quebrar isto amanhã, algo fica vermelho?
# ═════════════════════════════════════════════════════════════════════════════
def _mutacoes_declaradas_no_repo() -> int:
    """Quantas mutações o arquivo da régua DECLARA — por `ast`, sem executar.

    ⚠️ Ler por `ast` e não importar é deliberado: importar o arquivo de teste
    executa as asserções dele (é o que `VM._carregar_mutacoes` faz, apesar do
    que o docstring dele diz), e a régua não pode rodar a suíte para se medir.
    """
    caminho = os.path.join(M.RAIZ_BACKEND, "tests", "test_a_regua_nao_tem_furo.py")
    try:
        arvore = ast.parse(io.open(caminho, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return 0
    for no in arvore.body:
        alvos = no.targets if isinstance(no, ast.Assign) else []
        if not any(isinstance(a, ast.Name) and a.id == "MUTACOES" for a in alvos):
            continue
        try:
            valor = ast.literal_eval(no.value)
        except (ValueError, TypeError, SyntaxError):
            return 0
        return len([x for x in valor
                    if isinstance(x, (list, tuple)) and len(x) == 4])
    return 0


def eixo_e(rota, r: RP.Replay, *, mutacoes_ok: Optional[Tuple[int, int]] = None) -> List[Item]:
    """🔴 Avaliado POR ARQUIVO, e a nota da rota é a do MELHOR arquivo que a nomeia.

    📊 A regra por-arquivo existe porque a v1 zerava a régua e travava o próprio
    gate: um arquivo desqualificado derrubava a rota inteira mesmo havendo outro,
    bom, cobrindo-a.
    """
    corpus_norm = {M._norm(t.texto) for t in r.telas}
    candidatos = []
    for caminho in sorted(glob.glob(os.path.join(PASTA_DE_TESTES, "test_*.py"))):
        with open(caminho, encoding="utf-8") as fh:
            fonte = fh.read()
        if rota.servico not in fonte and rota.seguradora not in fonte:
            continue
        if not DET.qualifica(caminho):
            candidatos.append((caminho, -1, 0, "DESQUALIFICADO (regex sobre ancora, sem motor)"))
            continue
        # 🔴 ≥3 telas do CORPUS, comparadas por `_norm`. Teste que chama o motor
        #    sobre texto INVENTADO prova o motor, não a rota — é a mesma lição do
        #    `numero_residencia`: âncora escrita de cabeça, ZERO ocorrências.
        literais = re.findall(r'"([^"\n]{25,})"|\'([^\'\n]{25,})\'', fonte)
        tocadas = sum(1 for a, b in literais
                      if any(M._norm(a or b) in c or c in M._norm(a or b)
                             for c in corpus_norm))
        controles = len(re.findall(r"CONTROLE", fonte))
        candidatos.append((caminho, tocadas, controles, ""))

    itens: List[Item] = []
    # ══════════════════════════════════════════════════════════════════════
    # 🔴 C18 — O ARQUIVO COM MAIS TELAS VENCIA O COM CONTROLE
    # ══════════════════════════════════════════════════════════════════════
    #
    # Os dois itens do eixo E saem do MESMO arquivo — e a escolha era por
    # `(telas_tocadas, controles)`, nessa ordem. Uma tela a mais decidia tudo.
    #
    # 📊 Medido em 23/08/2026, `hdi/auto/chaveiro`:
    #
    # ```
    #   test_o_atlas_conta_certo.py .................. 10 telas ·  0 controles
    #   test_o_corredor_da_hdi_responde_a_ura_dela.py   3 telas · 14 controles
    # ```
    #
    # 🔴 O primeiro vencia, e a rota levava **0 de 3 em CONTROLE** — havendo um
    #    guarda escrito para ela, com quatorze linhas de controle, chamando o
    #    motor nas telas dela. O ponto não estava faltando: estava sendo
    #    procurado no arquivo errado.
    #
    # ⚠️ A ordenação nova NÃO afrouxa a cobertura: o primeiro critério é
    #    `telas >= 3`, que é o próprio limiar do item. Nenhum arquivo abaixo
    #    dele passa na frente. Entre os que já provaram cobertura, ganha o que
    #    também GUARDA — e a cobertura segue como desempate final.
    #
    # 📊 Efeito medido nas 73: **4 rotas ganham 3 pontos, nenhuma perde**
    #    (hdi chaveiro · hdi pneu · hdi socorro_mecanico · yelum guincho).
    melhor = max(candidatos, key=lambda c: (c[1] >= 3, c[2], c[1]), default=None)
    if melhor is None or melhor[1] < 0:
        nomes = [os.path.basename(c[0]) for c in candidatos]
        itens.append(Item("E", "teste nomeia a rota, chama o motor, toca >=3 telas", 0, 6,
                          f"nenhum arquivo qualificado. candidatos: {nomes or 'nenhum'}"))
        itens.append(Item("E", ">=1 linha de CONTROLE", 0, 3, "-"))
    else:
        caminho, tocadas, controles, _ = melhor
        itens.append(Item("E", "teste nomeia a rota, chama o motor, toca >=3 telas",
                          6 if tocadas >= 3 else 0, 6,
                          f"{os.path.basename(caminho)}: {tocadas} telas do corpus tocadas"))
        itens.append(Item("E", ">=1 linha de CONTROLE", 3 if controles else 0, 3,
                          f"{controles} mencoes a CONTROLE em {os.path.basename(caminho)}"))

    # ── 6 · a mutação fica vermelha QUANDO EXECUTADA ───────────────────────
    if mutacoes_ok is None:
        itens.append(Item("E", "a mutacao fica vermelha (EXECUTADA)", 0, 6,
                          "nao rodado (use --verificar-mutacoes)"))
    else:
        boas, total = mutacoes_ok
        # ══════════════════════════════════════════════════════════════════
        # 🔴 SPEC-084.2 · A TUPLA PRECISA BATER COM O QUE O REPO DECLARA
        # ══════════════════════════════════════════════════════════════════
        #
        # 📊 Achado por um subagente em 23/08/2026: a régua vinha sendo medida
        #    com `mutacoes_ok=(12,12)` passado à mão, enquanto
        #    `test_a_regua_nao_tem_furo` declarava **11** mutações. O item vale
        #    6 pontos em TODAS as rotas, e ninguém conferia o número.
        #
        # ⚠️ O item nunca leu o valor — só `boas == total` —, então a nota não
        #    mudava. Mas um número afirmado sem fonte, num item de 6 pontos,
        #    é exatamente o que a §12.1 proíbe: **quem lê o relatório acredita
        #    no número, não na aritmética.**
        #
        # 🔴 Agora a tupla é CONFERIDA contra o `MUTACOES` do arquivo, por
        #    `ast` (sem executar nada). Divergiu, o item cai e diz por quê —
        #    em vez de dar 6 pontos calado.
        declaradas = _mutacoes_declaradas_no_repo()
        # 🔴 FAIL-CLOSED — achado do JUIZ 0.
        #
        #    A primeira redação era `if declaradas and total != declaradas`. Um
        #    `cwd` errado, um rename ou um `SyntaxError` fazia `declaradas`
        #    valer 0, o `and` curto-circuitava, e o item devolvia **6 pontos em
        #    todas as rotas** afirmando um número inventado — com a frase exata
        #    que a §12.1 proíbe.
        #
        # ⚠️ **Zero MEDIDO e zero NÃO MEDIDO não são a mesma coisa** — é a
        #    mesma lição que o `medir_rota.py` documenta sobre o `cwd`. Não
        #    conseguir ler vale ZERO, e diz que não conseguiu.
        if not declaradas:
            itens.append(Item("E", "a mutacao fica vermelha (EXECUTADA)", 0, 6,
                              "nao consegui LER o `MUTACOES` do arquivo da "
                              "regua — zero medido nao e zero nao medido"))
        elif total != declaradas:
            itens.append(Item("E", "a mutacao fica vermelha (EXECUTADA)", 0, 6,
                              f"a tupla diz {total} mutacoes e o repo declara "
                              f"{declaradas} — numero sem fonte (§12.1)"))
        else:
            itens.append(Item("E", "a mutacao fica vermelha (EXECUTADA)",
                              6 if (total and boas == total) else 0, 6,
                              f"{boas} de {total} mutacoes executadas e vermelhas"))
    return itens


# ═════════════════════════════════════════════════════════════════════════════
# A NOTA
# ═════════════════════════════════════════════════════════════════════════════
def medir(rota, *, sessoes_no_acervo: Optional[int] = None,
          tem_espelho: bool = False,
          mutacoes_ok: Optional[Tuple[int, int]] = None) -> Nota:
    r = RP.replay(rota, sessoes_no_acervo=sessoes_no_acervo)

    # 🔴 SEM_CORPUS e NAO_RESPONDE são estados OPOSTOS, com ações OPOSTAS.
    #    *"Fundir os dois faria a 084 reescrever corredores que já funcionam."*
    if not r.telas:
        return Nota(rota, [], "SEM_CORPUS", r)

    b = eixo_b(rota, r)
    pontos_b = sum(i.pontos for i in b if i.conta)

    # ── O PORTÃO DO EIXO B (§3.8) ──────────────────────────────────────────
    # 🔴 *"Nenhuma rota recebe pontos de A, C, D ou E enquanto B < 8."*
    #    ⚠️ 8 não é arbitrário: é a faixa de ">=3 órfãs funcionais" (0 de cobertura)
    #    somada a menos de 70% de determinismo. Uma rota abaixo disso não conversa
    #    com aquela URA.
    # ⚠️ **A LEITURA LITERAL DESSE `8` ESTAVA ERRADA, E A MEDIÇÃO MOSTROU.**
    #
    # 📊 Medido depois que o corpus passou a ser por rota (P-083-1):
    #
    # ```
    #   allianz x residencial x maquina_de_lavar
    #     63 respondidas · 15 orfas funcionais · determinismo 80,8%
    #     B = 0 (orfas) + 4 (determinismo) + 0 + 0 = 4   ->   NAO_RESPONDE
    # ```
    #
    # 🔴 **Uma rota que responde 63 telas e acerta 80,8% CONVERSA com aquela URA.**
    #    O item de órfãs é tudo-ou-nada (`>=3 -> 0`), e essa escala foi desenhada
    #    para um corpus de ~30 telas. Com 100+ telas por rota, `>=3 órfãs` é quase
    #    garantido — e o portão passou a barrar justamente as rotas com **MAIS**
    #    evidência.
    #
    # > ## O portão existe para pegar "o corredor não fala esta língua", não "o corpus cresceu".
    #
    # O corte passa a ser o que a §3.8 **diz que ele significa**, com as duas
    # condições valendo JUNTAS, como no texto: `>=3 órfãs` **E** `< 70%`.
    d = r.determinismo
    nao_conversa = len(r.orfas_funcionais) >= 3 and (d is None or d < 0.70)
    if nao_conversa or pontos_b == 0:
        return Nota(rota, b, "NAO_RESPONDE", r)

    itens = (eixo_a(rota, r) + b + eixo_c(rota, r)
             + eixo_d(rota, r, tem_espelho=tem_espelho)
             + eixo_e(rota, r, mutacoes_ok=mutacoes_ok))
    return Nota(rota, itens, None, r)
