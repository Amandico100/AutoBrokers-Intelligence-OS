"""A RUBRICA — os cinco eixos da SPEC-083 §3. Determinística, sem LLM.

```
A · EVIDÊNCIA    a rota foi percorrida até o fim?           20
B · COBERTURA    as telas viraram passos?                   35   ← o peso está aqui
C · SEGURANÇA    o freio casa tela REAL?                    20
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

import datetime as dt
import glob
import os
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
SEM_FABRICA = "SEM_FABRICA"
SEM_ESPELHO = "SEM_ESPELHO"
ROTA_INDISTINGUIVEL = "ROTA_INDISTINGUIVEL"


class Item(NamedTuple):
    eixo: str
    nome: str
    pontos: int
    maximo: int
    evidencia: str
    excluido: Optional[str] = None    # motivo, quando sai do denominador

    @property
    def conta(self) -> bool:
        return self.excluido is None


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
        d: Dict[str, int] = {}
        for i in self.itens:
            if not i.conta:
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
        return f"{nome}({self.denominador})"


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
    transcrição. Os 10 de auto vêm de `_auto_playbook`, e o subserviço é uma
    atribuição de uma linha: **não existe "o bloco do subserviço"**. ~40 rotas
    perderiam 4 pontos por onde o código mora, não por qualidade → `SEM_FABRICA`.
    """
    with open(FONTE_DO_CORREDOR, encoding="utf-8") as fh:
        fonte = fh.read()
    padrao = re.compile(r'^\s*"' + re.escape(servico) + r'"\s*:\s*\{', re.M)
    m = padrao.search(fonte)
    if not m:
        return None
    fim = fonte.find("\n        },", m.end())
    inicio = fonte.rfind("\n\n", 0, m.start())
    return fonte[max(0, inicio):fim if fim > 0 else m.end() + 3000]


# ═════════════════════════════════════════════════════════════════════════════
# EIXO A — EVIDÊNCIA (20)
# ═════════════════════════════════════════════════════════════════════════════
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
    bloco = _fonte_do_bloco(rota.servico)
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

    # ── 8 · ≥85% determinístico ────────────────────────────────────────────
    d = r.determinismo
    pd = 0 if d is None else (8 if d >= 0.85 else 4 if d >= 0.70 else 0)
    itens.append(Item("B", ">=85% deterministico", pd, 8,
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
    sessao_falsa = {"capture": captura, "captures": captura, **captura}
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
    com_numero, reproduzem = 0, 0
    for p in passos:
        nota = p.get("notes") or ""
        m = re.search(r"(\d+)\s*ocorr", nota)
        if not m:
            continue
        com_numero += 1
        declarado = int(m.group(1))
        anc = p.get("anchor")
        if not anc:
            continue
        try:
            real = sum(1 for t in r.telas if re.search(anc, M._norm(t.texto), re.I))
        except re.error:
            continue
        if declarado and abs(real - declarado) <= 0.20 * declarado:
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
    exigidas: Set[str] = set()
    for p in pb.get("ura_steps") or []:
        for req in p.get("requires") or []:
            if req.endswith("_opcao"):
                exigidas.add(req)
    do_subservico = set((pb.get("subservices") or {}).get(rota.servico) or {})
    fonte = (os.path.join(RAIZ, "app", "services", "insurer_dispatch_service.py"))
    with open(fonte, encoding="utf-8") as fh:
        ids = fh.read()
    derivadas = {k for k in exigidas if re.search(r'["\']' + re.escape(k) + r'["\']', ids)}
    orfas = exigidas - do_subservico - derivadas - TECLAS_INLINE
    itens.append(Item("C", "toda tecla _opcao tem origem (3 fontes)",
                      6 if not orfas else 0, 6,
                      f"{len(exigidas)} teclas exigidas; sem origem: "
                      f"{sorted(orfas) or 'nenhuma'}"))

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
        itens.append(Item("D", "apelidos do jeito que o cliente fala",
                          0, 4, f"{len(apelidos)} apelidos declarados; "
                          f"sem acesso ao Espelho para conferir o uso real",
                          excluido=SEM_ESPELHO))
    else:
        itens.append(Item("D", "apelidos do jeito que o cliente fala",
                          4 if len(apelidos) >= 3 else 0, 4,
                          f"{len(apelidos)} apelidos: {apelidos[:6]}"))

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
    regras = sub.get("regras_para_o_cliente") or pb.get("regras_para_o_cliente")
    if not tem_fabrica:
        itens.append(Item("D", "regras_para_o_cliente casam o corpus", 0, 3,
                          "sem bloco literal onde declarar", excluido=SEM_FABRICA))
    else:
        casa = False
        trecho = ""
        bloco = _fonte_do_bloco(rota.servico) or ""
        corpus_norm = [M._norm(t.texto) for t in r.telas]
        # janela deslizante de >=40 caracteres — NUNCA o comentário inteiro
        for linha in bloco.splitlines():
            if "📊" not in linha:
                continue
            texto = M._norm(linha.split("📊", 1)[1])
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
    melhor = max(candidatos, key=lambda c: (c[1], c[2]), default=None)
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
    if pontos_b < 8:
        return Nota(rota, b, "NAO_RESPONDE", r)

    itens = (eixo_a(rota, r) + b + eixo_c(rota, r)
             + eixo_d(rota, r, tem_espelho=tem_espelho)
             + eixo_e(rota, r, mutacoes_ok=mutacoes_ok))
    return Nota(rota, itens, None, r)
