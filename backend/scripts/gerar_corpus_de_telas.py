"""O corpus de telas reais — SPEC-083 §6 e Bloco A.

```
backend/tests/corpus/telas_reais/<seguradora>-<ramo>.jsonl
backend/tests/corpus/telas_reais/INDICE.md
```

**Por que versionado, e não consultado no teste** (§6.6):
1. o teste roda **sem banco** — em CI e na máquina de quem escreve corredor
2. o corpus é **prova datada**: se a URA mudar, ele continua sendo o que
   justificou aquele passo
3. o gate não depende de rede

🔴 **A decisão multi-tenant, registrada** (§6.2): o corpus é **global por
seguradora+ramo**. `company_id` fica como metadado de proveniência e o replay o
ignora. Decisão do Founder: *"a seguradora faz a MESMA pergunta para todas as
corretoras. O que muda entre elas são os DADOS."* Coerente com
`O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`.

Uso:
    python backend/scripts/gerar_corpus_de_telas.py --todas [--dry-run]
    python backend/scripts/gerar_corpus_de_telas.py --seguradora allianz
    python backend/scripts/gerar_corpus_de_telas.py --auditar-pii
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import higiene_do_corpus as H          # noqa: E402
import padroes_de_ramo as PR           # noqa: E402
import padroes_de_servico as PSV       # noqa: E402
import regua_motor as M                # noqa: E402
import zonas_do_acervo as Z            # noqa: E402

# 🔴 o resolvedor de nomes de subservico e o DO PRODUTO, injetado aqui
#    para nao criar import circular nem tabela paralela.
PSV.ligar_resolvedor(M.canonical_subservice)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "tests", "corpus", "telas_reais")

# =============================================================================
# 🔴 P-083-1 - O TETO E POR **ROTA**, NAO POR (seguradora, ramo).
# =============================================================================
#
# Decisao do Founder, 21/08/2026, pelo metodo de nota:
#
# ```
#   manter 5 por (seguradora, ramo)          30   46 rotas sem amostra, e elas
#                                                 PARECEM ruins. Mede errado.
#   5 por ROTA (seguradora x ramo x servico) 90   a unidade de medida da regua
#                                                 E a rota. O corpus segue a
#                                                 unidade de medida.
#   sem teto                                 45   544 sessoes em git, irrevisavel
# ```
#
# 📊 **O numero que a decisao existe para produzir:** a regua mediu, com o teto
# antigo, **4 rotas pontuando · 12 SEM_CORPUS · 46 NAO_RESPONDE**. A causa nao
# era qualidade de corredor - era amostra: 5 sessoes nao cobrem 4 a 6 servicos.
#
# > ## "46 corredores a reescrever" e "46 rotas sem amostra" sao trabalhos OPOSTOS.
# > ## A diferenca sai de uma regeracao, nao de opiniao.
#
# ⚠️ E capar por rota **nao inventa sessao**: o crescimento e limitado pelo que
# existe. 📊 `guincho` tem 65 escolhas em 10 seguradoras (~6 por rota - o corpus
# enche); `chaveiro` tem 12 em 10 (~1 por rota - e essas ficam honestamente
# magras, o que e a informacao certa).
#
# =============================================================================
# 🔴 SPEC-119 F2 · 27/09/2026 — O TETO DEIXA DE SER TETO E PASSA A SER PISO.
# =============================================================================
#
# ⛔ O defeito que este bloco conserta: o teto de 5 **por rota** era um teto
#    TOTAL, e a cota de desfecho competia com ele. Sessao COM DESFECHO caia fora.
#
# 📊 Medido em 27/09/2026 no acervo inteiro, com o classificador da F1
#    (`python scripts/gerar_corpus_de_telas.py --todas --dry-run`, somando os
#    avisos com `grep -o "AVISO: [0-9]* sessao"`): **201 sessoes fora do corpus**
#    em 16 rotas. 🔴 E delas, **36 tinham DESFECHO**.
#
# 📊 As opcoes, medidas pelo MESMO `escolher_sessoes`, variando UM fator por vez
#    e com LINHA DE CONTROLE (CLAUDE.md §9.2) — `scratchpad/medir_teto.py`:
#
# ```
#   E CONTROLE: teto 5 total (HOJE)   linhas 4479  KB 1439  ses 204  fora 201  c/desfecho fora 36
#   A teto 10 total                   linhas 5897  KB 1885  ses 270  fora 135  c/desfecho fora 13
#   B teto 15 total                   linhas 6793  KB 2167  ses 317  fora  88  c/desfecho fora  3
#   C sem teto                        linhas 7930  KB 2518  ses 405  fora   0  c/desfecho fora  0
#                                     ⛔ yelum-auto 504 KB -- ESTOURA o TETO_DE_BYTES
#   D desfecho ilimitado + piso 5     linhas 6032  KB 1913  ses 240  fora 165  c/desfecho fora  0
#   D' desfecho ilimitado + piso 8    linhas 6355  KB 2022  ses 268  fora 137  c/desfecho fora  0
# ```
#
# 🔴 **A LINHA DE CONTROLE deu direito a conclusao:** a opcao E reproduziu, linha
#    por linha e arquivo por arquivo, a geracao de ANTES da mudanca (4479 linhas,
#    15 arquivos, ZERO diferencas). Entao a diferenca das outras e do fator que
#    mudou, e de mais nada.
#
# 🔴 A DECISAO, pelo metodo de nota (CLAUDE.md §12.2 item 4):
#
# ```
#   A  teto 10 fixo ................  55  ainda descarta 13 sessoes COM DESFECHO.
#                                         Nao resolve a regra; so a adia.
#   B  teto 15 fixo ................  62  ainda descarta 3. Mesmo defeito, +51% de bytes.
#   C  sem teto ....................  70  zero descarte, e garante a regra por construcao.
#                                         Mas +75% de bytes (1439 -> 2518 KB) e
#                                         `yelum-auto.jsonl` ESTOURA o TETO_DE_BYTES
#                                         (504 KB > 500 KB). Corpus irrevisavel em diff
#                                         (a nota 45 de 21/08 sobre "544 sessoes em git"
#                                         continua valendo).
#   D  desfecho ILIMITADO + piso 5 ..  92  ZERO sessao com desfecho descartada (a regra que
#      de diversidade                     nao se negocia), +33% de bytes, nenhum arquivo
#                                         estourando o teto (maior: yelum-auto 401 KB), e as
#                                         165 que ficam fora sao TODAS sem desfecho -- o que
#                                         sai e o que NAO prova que a rota chega ao fim.
#   D' desfecho ilimitado + piso 8 ..  80  mesma garantia, +41% de bytes, ZERO desfecho a
#                                         mais (o piso so muda quem NAO tem desfecho).
# ```
#
# 🔴 **ESCOLHIDA: D.** A regra que a SPEC-119 F2 nao negocia e *"sessao COM
#    DESFECHO nunca e descartada por teto"* — ela e a que prova que a rota chega
#    ao fim (o item de 12 pontos da regua). O piso de 5 continua existindo para
#    as SEM desfecho, que e onde o teto sempre fez sentido: diversidade.
#
# 📊 **O CUSTO DE TEMPO NA SUITE, medido** (o corpus e lido por testes que rodam
#    SEM banco; arquivo grande deixa a suite lenta). Melhor de 3, mesma maquina:
#
# ```
#   auditar(corpus) -- o percurso puro do corpus    4.470 -> 6.048 linhas (+35%)
#                                                   0,206 s -> 0,274 s   (+0,068 s)
#   replay.carregar_corpus() x 73 rotas             26.434 -> 35.166 linhas lidas
#                                                   0,204 s -> 0,257 s   (+0,053 s)
#   pytest tests/test_o_corpus_nao_vaza_pii.py      13,13 s -> 10,34 s
#   pytest tests/test_a_tela_cega_vira_fila.py       3,73 s ->  3,02 s
# ```
#
# 🔴 O relogio do pytest e DOMINADO pelo import (ele caiu com o corpus MAIOR).
#    O numero que responde a pergunta e o percurso puro: **+0,07 s para +35% de
#    linhas**. Corpus 35% maior custa DECIMOS DE SEGUNDO na suite.
#
# ⚠️ `test_a_regua_nao_tem_furo.py` NAO foi cronometrado: ele MUTA
#    `app/services/corridor_playbooks.py` (P-118-14) e a fatia F3 escreve nesse
#    arquivo agora. O proxy acima e `replay.carregar_corpus`, que e a funcao pela
#    qual a regua le o corpus — e ela e chamada uma vez por rota.
PISO_POR_ROTA = 5

# 🔴 `None` = sessao COM DESFECHO **nunca** sai por teto. Um inteiro aqui
#    reintroduz o defeito de proposito — e e assim que a mutacao do guarda
#    `test_o_corpus_nao_joga_sessao_fora.py` prova que ele CONSEGUE ficar
#    vermelho (CLAUDE.md §9.3).
TETO_DE_DESFECHO: Optional[int] = None

TETO_DE_BYTES_POR_ARQUIVO = 500 * 1024

# 🔴 REGRA DE ESCOPO - decisao do Founder, 21/08/2026:
#    *"Nesse momento, condominio e outros ramos que nao sejam auto e residencial
#    nao entram em corredores. Apenas AUTO e RESIDENCIAL. Tudo que for outro ramo
#    e que for SINISTRO deve ser feito o HANDOFF para o suporte humano."*
#
# ⚠️ 📊 O que sai: `tokio-condominio` (2 sessoes) e `tokio-residencial` (4 sessoes,
#    e nao ha playbook). Vao para PENDENCIAS.md com dono do Founder.
RAMOS_EM_ESCOPO = ("auto", "residencial")

# 🔴 O FILTRO ② DA SPEC-084 §2.5.2 — a fala humana que a fronteira não pega.
#
# A `FRONTEIRAS` corta a partir do anúncio de transferência. Sobra a fala humana
# que aparece ANTES dela, ou em sessão sem transferência nenhuma.
#
# ⚠️ **ANCORADO EM `^…$`, NUNCA EM PREFIXO** — e essa palavra custou uma versão
# inteira da SPEC-084. 📊 O padrão em prefixo rejeitava:
#
# ```
#   "certo! por favor digite o *cpf* ou *cnpj* do(a) titular da apolice..."   78 ses
#   "certo, neste caso qual e o nome da pessoa que esta no local?"            40 ses
#   "ok, agora selecione o endereco onde esta o veiculo..."                   19 ses
#                                                    ... 267 telas distintas
# ```
#
# 🔴 **A primeira é a tela do CPF da Allianz — o nó de maior retorno do acervo.**
#    O guarda da v2 nunca ficava vermelho; o da v3 nunca ficaria verde.
#
# 📊 E o alvo verdadeiro sobrevive ao aperto: `"ok"` sozinho e `"um momento"`
#    sozinho somam **63 sessões** — humano, e ainda pegos pelo `^…$`.
#
# ⚠️ Este filtro NASCEU de um guarda vermelho: `test_o_corpus_nao_tem_falas_de_gente`
#    acusou 1 linha (`"ok"` em `allianz-residencial`) numa geração em que o
#    gerador ainda não o aplicava. **O teste conferia o corpus e nada o produzia.**
import re as _re  # noqa: E402
FALA_DE_GENTE = _re.compile(
    r"^(ok|certo|perfeito|prontinho|um momento|mais um momento|com quem falo|"
    r"ajudo em algo mais|mais alguma duvida|bom dia tudo bem|obrigad[oa])[!.,?]?$")


# ─────────────────────────────────────────────────────────────────────────────
# `sessao_chegou_ao_fim` — o `DECIDE:` #1 da SPEC-083 §2.4, e NADA MAIS.
#
# 🔴 Ele NASCE AQUI, no Bloco A, e o Bloco C o IMPORTA. A versão anterior da SPEC
#    mandava escolher *"a mais recente COM DESFECHO"* no Bloco A e definia
#    "desfecho" no Bloco C — uma circularidade no mesmo lugar de onde a antiga
#    saiu.
# ─────────────────────────────────────────────────────────────────────────────
def sessao_chegou_ao_fim(playbook: Dict[str, Any], telas: List[str]) -> bool:
    """A sessão chegou ao protocolo? — pelo MOTOR, nunca por regex do script.

    `DECIDE:` ≥1 tela em que `extract_capture_anchors` devolve `protocol`,
    **ou** `detect_finalize_anchor` casou e a sessão seguiu ≥1 tela depois.

    🔴 Exige o MOTOR e não a presença do padrão. 📊 Razão medida: a
    `_ANCORA_DE_PROTOCOLO` tem o ramo `o\\.?s\\.?`, que casa o **artigo "os"**
    seguido de dígitos. Em yelum, 31 das 38 sessões "com protocolo" casam **só**
    pelos ramos largos. `extract_capture_anchors` devolve o grupo capturado, que
    é o que distingue os dois.
    """
    for i, tela in enumerate(telas):
        if M.extract_capture_anchors(playbook, tela).get("protocol"):
            return True
        if M.detect_finalize_anchor(playbook, tela) and i < len(telas) - 1:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 SPEC-119 F2 · POR QUE A SESSÃO CONTINUA SEM ETIQUETA DE SERVIÇO
#
# *"Sem etiqueta" com motivo é medição; sem motivo é buraco.*
#
# ⚠️ Uma sessão sem etiqueta **entra no corpus assim mesmo** (as telas de tronco
#    valem para todas as rotas). O que falta é o nome do serviço — e faltar por
#    TRANSFERÊNCIA HUMANA, por LINK ou por o cliente ter escolhido PAGAMENTO são
#    três coisas com consequências opostas para o Founder:
#
# ```
#   transferência humana  a URA nunca soube o serviço. Nada a classificar.
#   LINK                  a seguradora não executa serviço por aqui (SPEC-118).
#   assunto que não é     o cliente pediu outra coisa. Não é cegueira de
#   assistência           classificador — é o que o acervo tem.
#   menu nunca apareceu   a sessão morreu antes do cardápio (inatividade).
#   rótulo DESCONHECIDO   🔴 ESTE é achado: a seguradora tem uma tecla que a
#                         tabela não conhece. Vai para a F1/PENDENCIAS.
# ```
#
# 🔴 O CONTROLE desta função está no guarda `test_o_corpus_nao_joga_sessao_fora`:
#    toda sessão que ela rotula como *"escolheu no menu um assunto que a tabela
#    marca None"* tem de ter `PSV.servico_da_sessao(...) == (None, ...)` — o
#    motor confirma a leitura, ela não fala sozinha (CLAUDE.md §9.4).
# ─────────────────────────────────────────────────────────────────────────────
RX_LINK = _re.compile(r"https?://|\bwa\.me\b|\blink\b", _re.IGNORECASE)

MOTIVO_FUGA = "FUGA documentada (o menu de serviço vira transferência humana)"
MOTIVO_TRANSFERIU = "transferência humana ANTES de a URA nomear o serviço"
MOTIVO_LINK = "a URA entregou LINK — nunca nomeou serviço executado"
MOTIVO_SEM_MENU = "a URA nunca mostrou menu de serviço nesta sessão"
MOTIVO_ASSUNTO = "escolheu no menu um assunto que a tabela marca None: %s"
MOTIVO_DESCONHECIDO = "🔴 respondeu ao menu com um rótulo DESCONHECIDO: %s"


def _rotulo_respondido(seguradora: str,
                       pares: List[Tuple[str, str]]) -> Optional[Tuple[str, bool]]:
    """`(rótulo respondido, a tabela conhece esse rótulo?)` — ou `None`.

    ⚠️ Lê as MESMAS tabelas do NÍVEL 1b de `padroes_de_servico` e para no
    PRIMEIRO menu que casou, como ele. Não decide serviço: quem decide é
    `servico_da_sessao`, e o guarda confere que os dois concordam.
    """
    for menu in PSV.MENUS_DE_SERVICO:
        if menu.get("seguradora") != seguradora:
            continue
        rx = _re.compile(menu["tela"], _re.DOTALL | _re.IGNORECASE)
        for i, (direcao, texto) in enumerate(pares):
            if direcao != "in" or not rx.search(texto):
                continue
            for direcao2, resposta in pares[i + 1:]:
                if direcao2 != "out":
                    continue
                r = PSV._norm_rotulo(resposta)
                if not r:
                    continue
                conhecido = (r in (menu.get("teclas") or {})
                             or any(PSV._norm_rotulo(k) == r
                                    for k in (menu.get("rotulos") or {})))
                return r, conhecido
            break
    return None


def motivo_sem_etiqueta(seguradora: str,
                        pares: List[Tuple[str, str]],
                        telas: List[str],
                        eventos: List[Dict[str, Any]]) -> str:
    """🔴 O motivo MEDIDO de a sessão não ter serviço. Nunca adjetivo."""
    fuga = PSV.CAMINHO_DE_FUGA.get(seguradora)
    if fuga:
        rx = _re.compile(fuga["tela"], _re.DOTALL | _re.IGNORECASE)
        for i, (direcao, texto) in enumerate(pares):
            if direcao != "in" or not rx.search(texto):
                continue
            for direcao2, resposta in pares[i + 1:]:
                if direcao2 != "out":
                    continue
                if PSV._norm_rotulo(resposta) == fuga["tecla"]:
                    return MOTIVO_FUGA
                break
            break
    respondido = _rotulo_respondido(seguradora, pares)
    if respondido:
        rotulo, conhecido = respondido
        return ((MOTIVO_ASSUNTO if conhecido else MOTIVO_DESCONHECIDO)
                % ("`%s`" % rotulo[:30]))
    if Z.sessao_tem_fronteira(seguradora, eventos):
        return MOTIVO_TRANSFERIU
    if any(RX_LINK.search(t) for t in telas):
        return MOTIVO_LINK
    return MOTIVO_SEM_MENU


# ─────────────────────────────────────────────────────────────────────────────
# A ESCOLHA DAS SESSÕES — sem ambiguidade, e determinística.
# ─────────────────────────────────────────────────────────────────────────────
def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def escolher_sessoes(
    candidatas: List[Tuple[Any, str, Set[str], bool, Optional[str]]],
    piso_por_rota: int = PISO_POR_ROTA,
    *,
    teto_de_desfecho: Optional[int] = TETO_DE_DESFECHO,
) -> Tuple[List[Any], List[str]]:
    """`[(sid, wa_ts, telas_norm, chegou_ao_fim, servico)]` -> `(escolhidas, notas)`.

    🔴 **A COTA E POR ROTA** (P-083-1). Cada servico presente no acervo daquele
    `(seguradora, ramo)` tem cota propria.

    🔴 **E DESDE A SPEC-119 F2 A COTA E UM PISO, NAO UM TETO** (ver o bloco de
    decisao no topo do arquivo):

    ```
    sessao COM DESFECHO   entra SEMPRE. Nunca sai por teto -- e ela que prova
                          que a rota chega ao fim (o item de 12 pontos da regua)
    sessao SEM desfecho   entra por DIVERSIDADE ate a rota ter `piso_por_rota`
                          sessoes. O que passar disso fica fora, e o INDICE diz
    ```

    ⚠️ `teto_de_desfecho` existe **so** para reintroduzir o defeito historico num
    guarda (`teto_de_desfecho=5` = o comportamento de antes de 27/09/2026).
    Em producao ele e `None`, que e o valor por omissao.

    Dentro da cota de cada servico, a ordem e a da SPEC-083 §8 passo 4:

    ```
    1. as que CHEGARAM AO FIM, mais recentes primeiro
    2. o resto: guloso por JACCARD, escolhendo a de MENOR similaridade maxima
    3. empate -> a mais recente vence (deterministico, NUNCA sorteio)
    ```

    ⚠️ O efeito colateral que a ferramenta DECLARA em vez de esconder: o eixo A #1
    pergunta se alguma sessao do corpus teve desfecho, e a selecao GARANTE que
    sim. Nao e errado - e a sessao certa a guardar - mas a saida diz isso, para
    ninguem ler como descoberta independente.

    ⚠️ As sessoes **sem servico determinado** (tronco: Termo, CPF, endereco) tem
    cota propria - elas valem para **todas** as rotas daquele ramo, e sao as que a
    SPEC-084 §2.4 chama de *"as que pagam por todas"*.

    📊 **CONTROLE:** rodar duas vezes tem de dar o MESMO conjunto.
    """
    notas: List[str] = []
    escolhidas: List[Any] = []

    por_servico: Dict[Optional[str], List] = collections.defaultdict(list)
    for c in candidatas:
        por_servico[c[4]].append(c)

    for servico in sorted(por_servico, key=lambda x: (x is None, str(x))):
        grupo = sorted(por_servico[servico], key=lambda c: (c[1], str(c[0])), reverse=True)
        cota: List[Any] = []
        vistas: Dict[Any, Set[str]] = {}
        rot = servico or "(tronco)"

        for sid, _ts, telas, fim, _s in grupo:
            if not fim:
                continue
            # 🔴 SPEC-119 F2: sem `teto_de_desfecho`, TODA sessao com desfecho
            #    entra. O `if` abaixo so existe para o guarda reintroduzir o
            #    defeito e ficar vermelho.
            if teto_de_desfecho is not None and len(cota) >= teto_de_desfecho:
                continue
            cota.append(sid)
            vistas[sid] = telas
            notas.append("[%s] COM DESFECHO -> %s" % (rot, str(sid)[:8]))

        restantes = [c for c in grupo if c[0] not in cota]
        while restantes and len(cota) < piso_por_rota:
            melhor, melhor_sim = None, 2.0
            for c in restantes:
                sim = max((_jaccard(c[2], v) for v in vistas.values()), default=0.0)
                if sim < melhor_sim:
                    melhor_sim, melhor = sim, c
            if melhor is None:
                break
            cota.append(melhor[0])
            vistas[melhor[0]] = melhor[2]
            restantes.remove(melhor)
            notas.append("[%s] diversidade (jaccard %.2f) -> %s"
                         % (rot, melhor_sim, str(melhor[0])[:8]))

        # 🔴 O QUE FICOU FORA, SEPARADO POR DESFECHO — porque as duas coisas tem
        #    consequencias opostas. "Sem desfecho fora" e economia de bytes;
        #    "COM desfecho fora" e a rota perdendo a prova de que chega ao fim.
        fora = [c for c in grupo if c[0] not in cota]
        fora_com_desfecho = [c for c in fora if c[3]]
        fora_sem_desfecho = len(fora) - len(fora_com_desfecho)
        if fora_sem_desfecho:
            notas.append("[%s] AVISO: %d sessao(oes) SEM desfecho fora do corpus "
                         "pelo piso de %d por rota"
                         % (rot, fora_sem_desfecho, piso_por_rota))
        for c in fora_com_desfecho:
            notas.append("[%s] 🔴 ALARME: COM DESFECHO **FORA** pelo teto de %s -> %s"
                         % (rot, teto_de_desfecho, str(c[0])[:8]))
        escolhidas.extend(cota)

    return escolhidas, notas


# ─────────────────────────────────────────────────────────────────────────────
# A GERAÇÃO
# ─────────────────────────────────────────────────────────────────────────────
def _commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001
        return "?"


def carregar_acervo(seguradoras: Iterable[str]) -> Dict[str, Dict[Any, List[Dict[str, Any]]]]:
    acervo: Dict[str, Dict[Any, List[Dict[str, Any]]]] = {}
    for seg in seguradoras:
        por_sessao: Dict[Any, List[Dict[str, Any]]] = collections.defaultdict(list)
        for e in M.eventos_observados(seguradora=seg):
            por_sessao[e.get("session_id")].append(e)
        acervo[seg] = dict(por_sessao)
    return acervo


def gerar(seguradoras: List[str], *, dry_run: bool = False,
          piso_por_rota: int = PISO_POR_ROTA,
          teto_de_desfecho: Optional[int] = TETO_DE_DESFECHO) -> Dict[str, Any]:
    """Roda os 6 passos do Bloco A e devolve o relatório.

    ⚠️ `piso_por_rota` e `teto_de_desfecho` existem para MEDIR as opcoes de teto
    (o bloco de decisao no topo) e para a mutacao do guarda. A producao usa os
    valores por omissao.
    """
    # 🔴 O CONTROLE VEM PRIMEIRO. Sem ele, tudo o que vier depois é inválido.
    marcas = M.controle_do_mascarador()

    acervo = carregar_acervo(seguradoras)
    rel: Dict[str, Any] = {
        "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _commit(),
        "marcas_de_corretora": marcas,
        "arquivos": {}, "recusadas": [], "avisos": [], "por_seguradora": {},
        "sem_etiqueta": {}, "com_etiqueta": {},
    }

    # PASSO 3 (levantado antes, porque NÃO é decisão local à tela — §CA-064):
    # a lista de esqueletos cujo vocativo é DADO.
    #
    # 🔴 SEMPRE sobre o ACERVO INTEIRO, nunca sobre o recorte de `--seguradora`.
    #    ⚠️ Achado na primeira execução: com `--seguradora allianz` o levantamento
    #    devolveu **0 esqueletos**, porque as 7 famílias de vocativo vivem em
    #    porto, azul, hdi e yelum. Rodar por seguradora produziria um
    #    mascaramento DIFERENTE de rodar `--todas` — e o corpus deixaria de ser
    #    reprodutível, que é o CONTROLE do passo 4 (*"rodar duas vezes tem de dar
    #    o MESMO conjunto"*). O custo é uma leitura a mais do acervo; o benefício
    #    é a máscara não depender de quem chamou o script.
    acervo_para_vocativo = (acervo if set(seguradoras) == set(M.seguradoras())
                            else carregar_acervo(M.seguradoras()))
    todos_os_textos = [e.get("text") or ""
                       for ses in acervo_para_vocativo.values()
                       for evs in ses.values() for e in evs
                       if e.get("direction") == "in"]
    esq_dado, esq_duvidoso = H.levantar_vocativos(todos_os_textos)
    rel["vocativos"] = {"dado": len(esq_dado), "duvidoso": len(esq_duvidoso)}

    for seg, sessoes in acervo.items():
        pb_por_ramo = {}
        for ramo in PR.ramos_de(seg):
            ref = M.resolve_playbook_ref(seg, ramo)
            pb_por_ramo[ramo] = M.get_playbook(ref) if ref else None

        por_ramo: Dict[str, List[Tuple[Any, str, Set[str], bool, Optional[str], List[Dict]]]] = \
            collections.defaultdict(list)
        contagem = collections.Counter()

        for sid, eventos in sessoes.items():
            if not Z._tem_sessao(sid):
                contagem["ORFAO_sessao"] += 1
                continue
            ordenados = sorted(eventos, key=lambda x: x.get("wa_timestamp") or "")

            pares = [(e.get("direction"), Z.norm_para_classificar(e.get("text") or ""))
                     for e in ordenados]

            # PASSO 0 · o RAMO, pela cascata de dois níveis
            ramo, nivel = PR.classificar_ramo(seg, pares)
            contagem[f"ramo:{ramo}"] += 1
            contagem[f"nivel:{nivel.split(':')[0]}"] += 1
            # 🔴 Os três estados que NÃO viram corpus, e são coisas diferentes:
            #    `indefinido`   a sessão não decidiu (quase toda curta)
            #    `ambos`        colisão -> algum padrão cita cardápio (PADRAO_DE_CARDAPIO)
            #    `sem_escolha`  a sessão é longa e legítima, mas NÃO É DE ASSISTÊNCIA
            #                   (📊 cartão de crédito, sinistro RE, contratação)
            # 🔴 REGRA DE ESCOPO DO FOUNDER, 21/08/2026:
            #    *"Condominio e outros ramos que nao sejam auto e residencial NAO
            #    entram em corredores neste momento. Tudo que for outro ramo, e
            #    tudo que for SINISTRO, deve ser HANDOFF para o suporte humano."*
            #
            # ⚠️ O corpus do ramo fora de escopo NAO e gerado - mas a contagem
            #    dele VAI para o relatorio, porque PENDENCIAS.md precisa saber
            #    quantas sessoes ficaram de fora e de que ramo.
            if ramo not in RAMOS_EM_ESCOPO and ramo not in ("indefinido", "ambos", "sem_escolha"):
                contagem["FORA_DE_ESCOPO:" + ramo] += 1
                continue
            if ramo in ("indefinido", "ambos", "sem_escolha"):
                if ramo == "ambos":
                    rel["avisos"].append(
                        f"PADRAO_DE_CARDAPIO {seg}/{str(sid)[:8]}: {nivel}")
                continue

            # 🔴 QUEM É O SEGURADO DESTA SESSÃO — levantado ANTES de mascarar.
            #    O vocativo revela o nome; o resto da conversa o repete fora da
            #    posição de vocativo, onde nenhuma regra de FORMA o alcança.
            nomes_desta_sessao = H.nomes_no_vocativo(
                e.get("text") or "" for e in ordenados if e.get("direction") == "in")

            # PASSO 1 · só `direction='in'`, e só `zona='URA'`
            linhas: List[Dict[str, Any]] = []
            vistos: Set[str] = set()
            for e, zona, _motivo in Z.zonas(ordenados, seg):
                if e.get("direction") != "in":
                    continue
                contagem[f"zona:{zona}"] += 1
                if zona != "URA":
                    continue
                bruto = Z.limpar_invisiveis(e.get("text") or "")
                if not bruto.strip():
                    continue
                n = M._norm(bruto)

                # PASSO 1b · a direção invertida (defeito de ingestão)
                if Z.direcao_invertida(n):
                    contagem["DIRECAO_INVERTIDA"] += 1
                    continue

                # PASSO 1c · o filtro ② — fala humana que a fronteira não pegou
                if FALA_DE_GENTE.match(n.strip()):
                    contagem["FALA_DE_GENTE"] += 1
                    continue

                # PASSO 2 · dedup por (session_id, _norm(text)). 🔴 O timestamp
                #           NÃO entra: 📊 metade dos eventos de uma sessão é
                #           repetição do mesmo texto, e a tokio tem 36,3% de
                #           duplicata exata.
                if n in vistos:
                    contagem["dedup"] += 1
                    continue
                vistos.add(n)

                # PASSO 3 · mascarar (§6.4 + CA-062 + CA-064 + SPEC-119 §1)
                pb = pb_por_ramo.get(ramo)
                limpo, marcas_ap = H.higienizar(pb or {}, bruto, esq_dado,
                                                nomes_da_sessao=nomes_desta_sessao)
                if marcas_ap["senha_preservada"]:
                    contagem["senha_preservada"] += 1
                if marcas_ap["vocativo_mascarado"]:
                    contagem["vocativo_mascarado"] += 1
                if marcas_ap["nome_da_sessao_mascarado"]:
                    contagem["nome_da_sessao_mascarado"] += 1

                # 🔴 O AUDITOR RECEBE OS NOMES — SPEC-119 CONSERTO A, 28/09/2026.
                #    📊 `auditar_pii` TEM o parâmetro `nomes_da_sessao` desde a
                #    SPEC-083, e a docstring dele diz por quê; os dois chamadores
                #    o ignoravam. O guarda existia e não era chamado.
                sujeira = H.auditar_pii(limpo, nomes_da_sessao=nomes_desta_sessao)
                if sujeira:
                    # 🔴 RECUSAR só o que sobrar sujo depois da máscara — e a
                    #    recusa vai para o INDICE.md com sessão e motivo.
                    #    *"some do arquivo, não do registro."*
                    rel["recusadas"].append(
                        {"seguradora": seg, "ramo": ramo, "session_id": str(sid)[:8],
                         "motivo": ",".join(sorted({s.split(":")[0] for s in sujeira}))})
                    contagem["RECUSADA"] += 1
                    continue

                linhas.append({
                    "session_id": str(sid)[:8],
                    "wa_timestamp": e.get("wa_timestamp"),
                    "company_id": str(e.get("company_id") or "")[:8],
                    "text": limpo,
                })

            if not linhas:
                continue

            # 🔴 QUAL SERVICO esta sessao percorreu -- pela cascata de tres
            #    niveis (padrao-ouro -> resposta ao cardapio -> texto do `out`).
            #    Sem isto o replay roda o corpus INTEIRO de (seguradora, ramo)
            #    contra UMA rota, e as telas do eletricista viram orfas da maquina
            #    de lavar: 📊 20 orfas onde a SPEC-083 §4.1 espera 1.
            servico, nivel_srv = PSV.servico_da_sessao(seg, pares, pb_por_ramo.get(ramo))
            for l in linhas:
                l["servico"] = servico
                l["servico_nivel"] = nivel_srv
            contagem[f"servico:{nivel_srv.split('-')[0] if servico else 'indefinido'}"] += 1
            pb = pb_por_ramo.get(ramo)
            fim = sessao_chegou_ao_fim(pb, [l["text"] for l in linhas]) if pb else False
            # 🔴 SPEC-119 F2 · o MOTIVO de a sessão não ter etiqueta, MEDIDO.
            chave_sem = f"{seg}-{ramo}"
            if servico:
                rel["com_etiqueta"][chave_sem] = (
                    rel["com_etiqueta"].get(chave_sem, 0) + 1)
            else:
                motivo = motivo_sem_etiqueta(
                    seg, pares, [l["text"] for l in linhas], ordenados)
                alvo = rel["sem_etiqueta"].setdefault(chave_sem, {})
                d = alvo.setdefault(motivo, {"sessoes": [], "com_desfecho": 0})
                d["sessoes"].append(str(sid)[:8])
                d["com_desfecho"] += 1 if fim else 0
            por_ramo[ramo].append(
                (sid, max(l["wa_timestamp"] or "" for l in linhas),
                 {l["text"] for l in linhas}, fim, servico, linhas))

        rel["por_seguradora"][seg] = dict(contagem)

        # PASSO 4 · a escolha, e PASSO 5 · gravar
        for ramo, candidatas in por_ramo.items():
            pb = pb_por_ramo.get(ramo)
            n_servicos = len((pb or {}).get("subservices") or {})
            escolhidas, notas = escolher_sessoes(
                [(c[0], c[1], c[2], c[3], c[4]) for c in candidatas],
                piso_por_rota, teto_de_desfecho=teto_de_desfecho)
            mapa = {c[0]: c[5] for c in candidatas}
            linhas = [l for sid in escolhidas for l in mapa[sid]]
            linhas.sort(key=lambda l: (l["wa_timestamp"] or "", l["session_id"]))

            nome = f"{seg}-{ramo}.jsonl"
            corpo = "\n".join(json.dumps(l, ensure_ascii=False) for l in linhas) + "\n"
            rel["arquivos"][nome] = {
                "linhas": len(linhas), "bytes": len(corpo.encode("utf-8")),
                "sessoes_no_corpus": [str(s)[:8] for s in escolhidas],
                "sessoes_candidatas": len(candidatas),
                "piso": piso_por_rota, "subservices": n_servicos,
                "chegou_ao_fim": sum(1 for c in candidatas if c[3]),
                # 🔴 SPEC-119 F2: o numero que o guarda le. Sessao COM DESFECHO
                #    fora do corpus e o defeito, e ele fica ESCRITO no INDICE.
                "com_desfecho_fora": sum(
                    1 for c in candidatas
                    if c[3] and str(c[0])[:8] not in {str(s)[:8] for s in escolhidas}),
                "notas_da_selecao": notas,
            }
            if len(corpo.encode("utf-8")) > TETO_DE_BYTES_POR_ARQUIVO:
                rel["avisos"].append(f"TETO_DE_BYTES estourado em {nome}")
            if not dry_run:
                os.makedirs(DESTINO, exist_ok=True)
                with open(os.path.join(DESTINO, nome), "w", encoding="utf-8") as fh:
                    fh.write(corpo)
    return rel


def escrever_indice(rel: Dict[str, Any]) -> str:
    """`INDICE.md` — 🔴 o que SAI do corpus fica registrado. Nunca silêncio."""
    L: List[str] = []
    L.append("# Corpus de telas reais — ÍNDICE\n")
    L.append(f"> Gerado em **{rel['gerado_em']}** · commit `{rel['commit']}`")
    L.append(f"> 📊 `marcas_de_corretora()` = **{rel['marcas_de_corretora']}** "
             f"(o CONTROLE da SPEC-084 §2.5.1.3 — se fosse 0, a geração teria "
             f"rodado sem banco e o corpus **não estaria mascarado**)\n")
    L.append("🔴 Este arquivo existe porque a SPEC-083 §7 proíbe pular em "
             "silêncio: *\"truncar calado lê-se como 'cobrimos tudo'\"*.\n")
    L.append("## Os arquivos\n")
    L.append("| arquivo | linhas | KB | sessões no corpus | candidatas | piso | subserviços "
             "| c/ desfecho | 🔴 c/ desfecho FORA |")
    L.append("|---|---:|---:|---|---:|---:|---:|---:|---:|")
    for nome, d in sorted(rel["arquivos"].items()):
        L.append(f"| `{nome}` | {d['linhas']} | {d['bytes']/1024:.0f} | "
                 f"{' '.join(d['sessoes_no_corpus'])} | {d['sessoes_candidatas']} | "
                 f"{d['piso']} | {d['subservices']} | {d['chegou_ao_fim']} | "
                 f"{d['com_desfecho_fora']} |")
    L.append("\n## Por que cada sessão entrou\n")
    for nome, d in sorted(rel["arquivos"].items()):
        L.append(f"**`{nome}`**")
        for n in d["notas_da_selecao"]:
            L.append(f"- {n}")
        L.append("")
    # =========================================================================
    # 🔴 SPEC-119 F2 · O QUE CONTINUA SEM ETIQUETA, E POR QUE
    # =========================================================================
    L.append("\n## 🔴 O que continua SEM ETIQUETA de serviço — e o MOTIVO\n")
    L.append("> *\"Sem etiqueta\" com motivo é medição; sem motivo é buraco.* "
             "A sessão SEM etiqueta **entra no corpus assim mesmo** (as telas de "
             "tronco valem para todas as rotas do ramo) — o que falta é o NOME "
             "do serviço.\n")
    L.append("> ⚠️ Cada linha vem de `motivo_sem_etiqueta()`, no gerador. "
             "O guarda `test_o_corpus_nao_joga_sessao_fora.py` confere contra "
             "`PSV.servico_da_sessao` que a leitura concorda com o motor.\n")
    L.append("| seguradora-ramo | com etiqueta | sem etiqueta | motivo | sessões | c/ desfecho |")
    L.append("|---|---:|---:|---|---|---:|")
    for chave in sorted(rel["sem_etiqueta"]):
        motivos = rel["sem_etiqueta"][chave]
        total_sem = sum(len(d["sessoes"]) for d in motivos.values())
        com = rel["com_etiqueta"].get(chave, 0)
        primeiro = True
        for motivo, d in sorted(motivos.items(), key=lambda kv: -len(kv[1]["sessoes"])):
            L.append("| %s | %s | %s | %s | %s | %d |" % (
                ("`%s`" % chave) if primeiro else "",
                com if primeiro else "", total_sem if primeiro else "",
                motivo, " ".join("`%s`" % x for x in d["sessoes"][:6])
                + (" +%d" % (len(d["sessoes"]) - 6) if len(d["sessoes"]) > 6 else ""),
                d["com_desfecho"]))
            primeiro = False
    for chave in sorted(rel["com_etiqueta"]):
        if chave not in rel["sem_etiqueta"]:
            L.append("| `%s` | %d | 0 | ✅ nenhuma sessão sem etiqueta | — | 0 |"
                     % (chave, rel["com_etiqueta"][chave]))
    L.append("\n## Linhas RECUSADAS — sujeira que sobrou depois da máscara\n")
    if rel["recusadas"]:
        L.append("| seguradora | ramo | sessão | motivo |")
        L.append("|---|---|---|---|")
        for r in rel["recusadas"]:
            L.append(f"| {r['seguradora']} | {r['ramo']} | `{r['session_id']}` | {r['motivo']} |")
    else:
        L.append("_nenhuma_")
    L.append("\n## Contagens por seguradora\n")
    L.append("| seguradora | " + " | ".join(
        sorted({k for d in rel["por_seguradora"].values() for k in d})) + " |")
    chaves = sorted({k for d in rel["por_seguradora"].values() for k in d})
    L.append("|---" * (len(chaves) + 1) + "|")
    for seg, d in sorted(rel["por_seguradora"].items()):
        L.append(f"| {seg} | " + " | ".join(str(d.get(k, 0)) for k in chaves) + " |")
    if rel["avisos"]:
        L.append("\n## Avisos\n")
        for a in rel["avisos"]:
            L.append(f"- {a}")
    # 🔴 O RÓTULO TEM DE DIZER O QUE O NÚMERO É — SPEC-119 CONSERTO A.
    #    Desde a inversão, `dado` é a UNIÃO de dois mecanismos diferentes
    #    (≥3 cabeças distintas · esqueleto onde alguma cabeça já se provou
    #    nome). Chamar a soma de "≥3 cabeças" seria um nome que mente (§12.1).
    L.append(f"\n## Vocativos\n\n📊 esqueletos tratados como DADO (≥3 cabeças "
             f"distintas **ou** esqueleto onde alguma cabeça já se provou "
             f"nome): **{rel['vocativos']['dado']}** · com exatamente 2 cabeças "
             f"(= `NOME_DUVIDOSO`, **não** mascarado por este mecanismo, fica "
             f"para leitura humana): **{rel['vocativos']['duvidoso']}**\n")
    L.append("\n> ⚠️ Estes dois números são o mecanismo ESTRUTURAL, que hoje é "
             "**reforço**. Quem mascara a maior parte é a regra invertida: "
             "*mascara a menos que prove que é língua*, e ela não passa por "
             "esqueleto nenhum — ver `higiene_do_corpus.e_lingua`.\n")
    return "\n".join(L) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Gera o corpus de telas reais (SPEC-083 Bloco A)")
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--seguradora")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auditar-pii", action="store_true")
    a = ap.parse_args(argv)

    if a.auditar_pii:
        return auditar(DESTINO)

    segs = [a.seguradora] if a.seguradora else M.seguradoras()
    rel = gerar(segs, dry_run=a.dry_run)
    if not a.dry_run:
        os.makedirs(DESTINO, exist_ok=True)
        with open(os.path.join(DESTINO, "INDICE.md"), "w", encoding="utf-8") as fh:
            fh.write(escrever_indice(rel))
    print(escrever_indice(rel))
    return 0


def auditar(destino: str) -> int:
    """🔴 O VERIFY que CONSEGUE falhar (SPEC-083 Bloco A).

    A v1 da SPEC usava `grep -cE '[0-9]{11}'`. Ele **não casa**
    `+55 (47) 90000-0000` — a maior sequência de dígitos ali tem CINCO.
    Devolvia 0 com quatro telefones no arquivo.

    🔴 E ELE LÊ O ARQUIVO DUAS VEZES — SPEC-119 CONSERTO A, 28/09/2026.

    A primeira leitura levanta, POR SESSÃO, os nomes que algum vocativo
    sobrevivente revelou; a segunda audita cada linha COM esses nomes. Sem as
    duas passadas, `nomes_da_sessao` nunca chega aqui — e era assim que
    📊 `6048 linhas, 0 sujas, exit 0` convivia com 86 linhas de nome em claro.
    """
    total = sujas = 0
    achados: List[str] = []
    arquivos = [n for n in sorted(os.listdir(destino)) if n.endswith(".jsonl")]

    # passada 1 — quem é o segurado de cada sessão, segundo o que sobrou
    por_sessao: Dict[str, List[str]] = collections.defaultdict(list)
    for nome in arquivos:
        for linha in open(os.path.join(destino, nome), encoding="utf-8"):
            if linha.strip():
                d = json.loads(linha)
                por_sessao[str(d.get("session_id"))].append(d.get("text") or "")
    nomes_por_sessao = {sid: H.nomes_no_vocativo(ts)
                        for sid, ts in por_sessao.items()}

    # passada 2 — a auditoria, agora com o nome sendo olhado
    for nome in arquivos:
        for i, linha in enumerate(open(os.path.join(destino, nome), encoding="utf-8"), 1):
            if not linha.strip():
                continue
            total += 1
            d = json.loads(linha)
            if d.get("direction") not in (None, "in"):
                achados.append(f"{nome}:{i} DIRECAO != in")
                sujas += 1
                continue
            s = H.auditar_pii(
                d.get("text") or "",
                nomes_da_sessao=nomes_por_sessao.get(str(d.get("session_id")), set()))
            if s:
                sujas += 1
                achados.append(f"{nome}:{i} {d['session_id']} -> {','.join(s[:3])}")
    print(f"auditoria de PII: {total} linhas, {sujas} sujas")
    for a in achados[:40]:
        print("  " + a)
    return 1 if sujas else 0


if __name__ == "__main__":
    raise SystemExit(main())
