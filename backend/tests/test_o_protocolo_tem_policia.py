# -*- coding: utf-8 -*-
"""🔴 O PROTOCOLO AAA tem de ser CONFERÍVEL, não só escrito.

📊 Auditoria de 30/08/2026, três lentes independentes sobre a v9. O achado que
gerou este arquivo:

> **"A conta do §3 foi executada ZERO de seis vezes — inclusive nas duas SPECs
> que rodaram o painel. Um passo obrigatório com 100% de descumprimento e sem
> gate não é regra: é decoração."**

E a causa raiz, de uma linha:

> **A §1 listava seis itens que o pacote do executor precisa carregar — e
> esquecia de si mesma.** Um prompt que obedecesse a §1 com perfeição entregava
> um pacote **sem o protocolo dentro**.

📊 A evidência é causal e limpa:

```
092 e 093            o prompt mandava LER o protocolo  →  o painel RODOU  2 de 2
087·090·086·089      o prompt NÃO mandava              →  não rodou       0 de 4
```

E o custo:

```
COM PAINEL    47 achados · 22 defeitos de PRODUTO   →  23,5 por SPEC
SEM PAINEL    19 achados ·  0 defeitos de produto   →   6,3 por SPEC
```

## 🔴 Por que ESTE arquivo, e não mais uma seção no protocolo

A v10 escreveu a regra em três lugares — `CLAUDE.md`, o §0.1 e o template do
relatório. **Escrever pela quarta vez não faria diferença**: o defeito nunca foi
falta de texto.

> **Regra sem portão é decoração. Este arquivo é o portão.**

⚠️ **E ele guarda o PROTOCOLO, não uma SPEC.** É meta de propósito: o protocolo
existe para achar defeito no produto, e nada existia para achar defeito nele.
"""
from __future__ import annotations

import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(os.path.dirname(RAIZ), "docs", "canon")
PROTO = os.path.join(CANON, "PROTOCOLO-AUTOBROKERS-AAA.md")
CLAUDE = os.path.join(os.path.dirname(RAIZ), "CLAUDE.md")
TEMPLATE = os.path.join(CANON, "reports", "SPEC-EXECUTION-REPORT-TEMPLATE.md")
RELATORIOS = os.path.join(CANON, "reports")

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok    %s" % rotulo)
    else:
        FAIL += 1
        print("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))


def ler(p):
    return io.open(p, encoding="utf-8").read()


# ---------------------------------------------------------------------------
def bloco_1_o_protocolo_se_carrega():
    print("\n[1] O PROTOCOLO SE CARREGA -- a causa raiz de 4 SPECs sem painel")
    p = ler(PROTO)

    # o pacote da §1 tem de listar o proprio protocolo, e como PRIMEIRO item
    i = p.find("O AGENTE RECEBE UM PACOTE")
    pacote = p[i:i + 900] if i != -1 else ""
    certo(i != -1, "a §1 declara o pacote")
    certo("ESTE PROTOCOLO" in pacote,
          "o pacote carrega O PRÓPRIO PROTOCOLO",
          "e a causa raiz: a lista tinha seis itens e esquecia de si mesma")

    # e ele tem de ser o primeiro, senao um pacote truncado o perde
    linhas = [l for l in pacote.split("\n") if l.strip().startswith(("+", "🔴 ESTE"))]
    certo(bool(linhas) and "ESTE PROTOCOLO" in linhas[0],
          "e ele e o PRIMEIRO item da lista",
          "um pacote cortado no meio nao pode perder justamente o protocolo")


def bloco_2_o_portao_existe_em_tres_lugares():
    print("\n[2] O PORTAO EXISTE -- e em mais de um lugar")
    certo("EXECUTION CARD" in ler(PROTO), "o protocolo define o EXECUTION CARD (§0.2)")
    certo("EXECUTION CARD" in ler(CLAUDE),
          "o CLAUDE.md exige o card",
          "e o CLAUDE.md que toda sessao carrega primeiro")
    certo("EXECUTION CARD" in ler(TEMPLATE),
          "o template do relatorio pede o card",
          "sem ele, ninguem percebe que a conta nao foi feita")

    # 🔴 E o card tem LINHAS. Conferir so a string "EXECUTION CARD" deixa
    #    passar um card sem metade dos campos -- foi assim que a linha do ELO
    #    nasceu em 02/09 e ficou em ZERO de dois pacotes no mesmo commit.
    p = ler(PROTO)

    # 🔴 So DENTRO do bloco do card. Procurar no documento inteiro faz o
    #    titulo da secao aprovar a linha que falta -- foi o que aconteceu na
    #    primeira versao deste bloco, e a linha de controle pegou.
    # 🔴 A cerca do CARD, nao a primeira cerca depois do titulo. Um bloco
    #    cercado inserido entre o titulo e o card sequestrava as tres assercoes
    #    abaixo -- provado por mutacao em 02/09: engodo com as 12 palavras passa
    #    e o card real fica sem seis linhas, tudo verde.
    card = ""
    i = p.find("## 0.2")
    fim = p.find("## 0.3", i) if i >= 0 else -1
    if i >= 0 and fim > i:
        trecho = p[i:fim]
        # a ULTIMA cerca aberta antes da 0.3 e a do card
        partes = trecho.split("```")
        if len(partes) >= 3:
            card = partes[-2]

    certo(len(card) > 200, "achei o bloco do EXECUTION CARD (%d chars)" % len(card),
          "sem ele tudo abaixo passa por vacuidade")

    faltando = [c for c in ("OUTCOME", "RISCO", "SUPERF", "PISO", "UNIDADES",
                            "COES", "PARALELISMO", "TIME", "REFER", "GATES",
                            "O ELO", "FAIXA")
                if c not in card]
    certo(not faltando,
          "o card tem TODAS as linhas obrigatorias -- DENTRO do bloco",
          "faltam: " + " · ".join(faltando))

    certo("O ELO" in card and "§0.3" in p,
          "a linha do ELO esta no CARD e a secao 0.3 existe",
          "🔴 linha de card sem secao e decoracao -- a §0.2 diz que passo "
          "obrigatorio sem gate nao e regra")


def bloco_3_a_referencia_tem_caminho():
    print("\n[3] A REFERENCIA APONTA PARA ARQUIVO QUE EXISTE")
    p = ler(PROTO)
    i = p.find("AS REFERÊNCIAS DO AUTOBROKERS")
    certo(i != -1, "a §7.1 existe")
    tabela = p[i:i + 3000]

    # todo caminho citado na tabela tem de existir no disco
    caminhos = re.findall(r"`(backend/[^`]+?\.(?:py|md)|docs/canon/[^`]+?\.md)`", tabela)
    caminhos = [c for c in caminhos if not c.endswith("/")]
    certo(len(caminhos) >= 4,
          "a tabela cita pelo menos 4 artefatos por caminho (achei %d)" % len(caminhos))

    faltando = [c for c in caminhos
                if not os.path.exists(os.path.join(os.path.dirname(RAIZ), c))]
    certo(not faltando,
          "TODOS os caminhos citados existem no disco",
          "ponteiro pendurado: " + ", ".join(faltando))

    # 🔴 e o que NAO existe tem de estar declarado como inexistente
    certo("não existe arquivo OpenAPI" in tabela or "não existe" in tabela,
          "o que NAO temos esta declarado, nao fingido",
          "a §7 antiga prometia OpenAPI, SLO e OWASP -- nenhum existe")


def bloco_4_o_documento_nao_virou_diario():
    print("\n[4] O DOCUMENTO NORMATIVO NAO PODE VIRAR DIARIO")
    p = ler(PROTO)
    # 📊 37% do documento era log datado antes de 30/08. O teto e generoso: o
    # protocolo PODE citar uma data para lastrear uma regra. O que ele nao pode
    # e virar um diario que se corrige a si mesmo em ciclos de horas.
    datas = len(re.findall(r"\d{2}/\d{2}/20\d\d", p))
    certo(datas <= 12,
          "o protocolo tem %d datas (teto: 12)" % datas,
          "acima disso ele voltou a ser diario -- mova para o EVIDENCIAS.md")

    nucleo = p[:p.find("## 6. O JUIZ")] if "## 6. O JUIZ" in p else p
    kb = len(nucleo) / 1024
    certo(kb <= 20,
          "o nucleo (§0 a §5) tem %.1f KB (teto: 20)" % kb,
          "e o que TODO agente carrega. Passou disso, a §1 esta sendo violada "
          "pelo proprio protocolo")


def bloco_5_toda_secao_citada_existe():
    print("\n[5] TODA § CITADA EXISTE -- referencia morta e pior que nenhuma")
    p = ler(PROTO)
    existem = set()
    for m in re.finditer(r"^#{2,3}\s+.*?(\d+(?:\.\d+)?)[\.\s]", p, re.M):
        existem.add(m.group(1))
    # 🔴 Só as § DESTE documento. Uma citação precedida de `CLAUDE.md` aponta
    # para OUTRO arquivo e é legítima — `CLAUDE.md` §9.1, §9.3, §12.1 existem
    # lá, não aqui.
    #
    # ⚠️ Este refinamento nasceu do próprio guarda: minutos depois de existir,
    # ele acusou `§12.1` como órfã. A citação estava certa (é do `CLAUDE.md`);
    # quem estava cego era ele. Um guarda que acusa inocente ensina a ignorá-lo
    # — e aí ele para de guardar o culpado também.
    sem_outras = re.sub(r"`?CLAUDE\.md`?[^\n]{0,40}?§\d+(?:\.\d+)?", "", p)
    citadas = set(re.findall(r"§(\d+(?:\.\d+)?)", sem_outras))
    orfas = sorted(citadas - existem)
    certo(not orfas,
          "nenhuma § orfa no protocolo",
          "citadas e inexistentes: " + ", ".join("§" + o for o in orfas))

    # o template tambem: 📊 ele apontava para §2.4 e §2.5, mortas desde a v9
    t = ler(TEMPLATE)
    orfas_t = sorted(set(re.findall(r"§(\d+\.\d+)", t)) - existem)
    certo(not orfas_t,
          "nenhuma § orfa no template do relatorio",
          "o template apontava para " + ", ".join("§" + o for o in orfas_t))


def bloco_6_CONTROLE():
    print("\n[6] LINHA DE CONTROLE -- este guarda consegue ficar vermelho?")
    # 🔴 Sem isto, um erro nos caminhos faria os cinco blocos passarem por
    # vacuidade -- que e exatamente a doenca que este arquivo existe para matar.
    certo(os.path.exists(PROTO) and os.path.exists(CLAUDE)
          and os.path.exists(TEMPLATE),
          "os tres arquivos que este guarda le EXISTEM",
          "se um sumiu, tudo acima passou lendo string vazia")

    p = ler(PROTO)
    certo(len(p) > 5000, "o protocolo tem conteudo (%d chars)" % len(p))
    certo("PACOTE_INEXISTENTE_XYZ" not in p,
          "e o casador NAO acha o que nao esta la",
          "um casador que casa com tudo aprova qualquer coisa")


def main() -> int:
    bloco_1_o_protocolo_se_carrega()
    bloco_2_o_portao_existe_em_tres_lugares()
    bloco_3_a_referencia_tem_caminho()
    bloco_4_o_documento_nao_virou_diario()
    bloco_5_toda_secao_citada_existe()
    bloco_6_CONTROLE()
    print("\n  %d ok, %d falhas" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
