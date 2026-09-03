# -*- coding: utf-8 -*-
"""🔴 O PROTOCOLO AAA tem de ser CONFERÍVEL, não só escrito.

v11 (03/09/2026). A v10 deste guarda tinha 20 asserções e TODAS olhavam para o
texto do protocolo. 📊 0 de 9 relatórios de execução tinham EXECUTION CARD, 0 de 7
SPECs convertidas tinham uma URL externa, e 4 de 10 pacotes não carregavam o
protocolo — e o guarda estava verde. Ele conferia o ledger, não o objeto.

Blocos [1]–[6]: o protocolo, o CLAUDE.md e o template (o texto).
Blocos [7]–[9]: os RELATÓRIOS, as SPECs e os PACOTES (o objeto).
Cada bloco novo tem LINHA DE CONTROLE: um artefato falso que TEM de reprovar, e
um que TEM de passar. Sem isso o casador que aceita tudo passaria por vacuidade.

> **Regra sem portão é decoração. Este arquivo é o portão.**
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(RAIZ)
CANON = os.path.join(REPO, "docs", "canon")
PROTO = os.path.join(CANON, "PROTOCOLO-AUTOBROKERS-AAA.md")
CLAUDE = os.path.join(REPO, "CLAUDE.md")
TEMPLATE = os.path.join(CANON, "reports", "SPEC-EXECUTION-REPORT-TEMPLATE.md")
RELATORIOS = os.path.join(CANON, "reports")
SPECS = os.path.join(CANON, "specs")
PACOTES = os.path.join(CANON, "pacotes")

# 🔴 A partir de qual SPEC os blocos [7] e [8] valem. As anteriores foram executadas
# antes de o card e a §7.3 existirem: cobrá-las seria acusar inocente.
PRIMEIRA_SPEC_SOB_V11 = 88
# 📊 executadas em 25–26/08/2026, antes de o card existir (git log dos relatórios).
# Têm número maior que 88 e NÃO estão sob a v11. Cobrá-las seria acusar inocente.
EXECUTADAS_ANTES_DA_V11 = {89, 90, 92, 93}

LINHAS_DO_CARD = [
    "OUTCOME", "RISCO", "SUPERFÍCIE", "PISO", "UNIDADES", "COESÃO",
    "PARALELISMO", "TIME", "REFERÊNCIA", "GATES", "O ELO", "FAIXA DE RELÓGIO",
]

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


def linhas_do_card_ausentes(trecho):
    """🔴 Ancorado no INÍCIO da linha. `"O ELO" in card` aprovava um card sem a
    linha, porque a linha seguinte dizia "MEDIU O ELO" — mutação de 03/09 pegou."""
    return [l for l in LINHAS_DO_CARD
            if not re.search(r"^\s*%s\b" % re.escape(l), trecho, re.M)]


def numero_da_spec(nome):
    m = re.search(r"SPEC-0?(\d{2,3})", os.path.basename(nome))
    return int(m.group(1)) if m else None


def urls_externas(texto):
    return set(u.rstrip(").,]") for u in re.findall(r"https?://[^\s)>\]]+", texto))


# ---------------------------------------------------------------------------
def bloco_1_o_protocolo_se_carrega():
    print("\n[1] O PROTOCOLO SE CARREGA -- a causa raiz de 4 SPECs sem painel")
    p = ler(PROTO)
    i = p.find("## 1.")
    fim = p.find("## 2.", i)
    dieta = p[i:fim] if i != -1 and fim != -1 else ""
    certo(bool(dieta), "a §1 (a DIETA) existe")
    itens = [l for l in dieta.split("\n") if l.strip().startswith(("🔴 ESTE", "+ "))]
    certo(bool(itens) and "ESTE PROTOCOLO" in itens[0],
          "o pacote carrega O PRÓPRIO PROTOCOLO, e ele é o PRIMEIRO item",
          "a lista antiga tinha seis itens e esquecia de si mesma")
    certo("PACOTE, nunca o canon" in dieta or "pacote, nunca o canon" in dieta.lower(),
          "a §1 diz: pacote, nunca o canon")
    certo("test_o_protocolo_tem_policia.py" in p,
          "o protocolo nomeia o próprio guarda (§0.1)")


def bloco_2_o_portao_existe_em_tres_lugares():
    print("\n[2] O PORTAO EXISTE -- e em mais de um lugar")
    p = ler(PROTO)
    certo("EXECUTION CARD" in p, "o protocolo define o EXECUTION CARD (§0.2)")
    certo("EXECUTION CARD" in ler(CLAUDE), "o CLAUDE.md exige o card")
    certo("EXECUTION CARD" in ler(TEMPLATE), "o template do relatorio pede o card")

    # 🔴 Só DENTRO do bloco do card: o título da seção aprovaria a linha que falta.
    card = ""
    i = p.find("## 0.2")
    fim = p.find("## 0.3", i) if i >= 0 else -1
    if i >= 0 and fim > i:
        partes = p[i:fim].split("```")
        if len(partes) >= 3:
            card = partes[-2]
    certo(len(card) > 200, "achei o bloco do EXECUTION CARD (%d chars)" % len(card))
    faltam = linhas_do_card_ausentes(card)
    certo(not faltam, "o card tem TODAS as linhas obrigatorias -- DENTRO do bloco, no inicio da linha",
          "faltam: " + ", ".join(faltam))
    certo("NÍVEL" in card and "## 3.1" in p,
          "o card declara o NÍVEL e a §3.1 o define")


def bloco_3_a_referencia_tem_caminho():
    print("\n[3] A REFERENCIA APONTA PARA ARQUIVO QUE EXISTE")
    p = ler(PROTO)
    i = p.find("### 7.1")
    fim = p.find("### 7.2", i)
    tabela = p[i:fim] if i >= 0 and fim > i else ""
    certo(bool(tabela), "a §7.1 existe")
    caminhos = re.findall(r"`((?:docs|backend|CLAUDE)[^`]*?\.(?:md|py|ts|tsx))`", tabela)
    caminhos += re.findall(r"`(backend/tests/corpus/[^`]+)`", tabela)
    certo(len(caminhos) >= 4,
          "a tabela cita pelo menos 4 artefatos por caminho (achei %d)" % len(caminhos))
    faltando = [c for c in caminhos if not os.path.exists(os.path.join(REPO, c.split(" ")[0]))]
    certo(not faltando, "TODOS os caminhos citados existem no disco",
          "ponteiro pendurado: " + ", ".join(faltando))
    certo("O que NÃO temos" in tabela, "o que NAO temos esta declarado, nao fingido")
    certo("### 7.3" in p and "3 a 7 referências externas" in p,
          "a §7.3 existe e exige 3 a 7 referencias externas")


def bloco_4_o_documento_nao_virou_diario():
    print("\n[4] O DOCUMENTO NORMATIVO NAO PODE VIRAR DIARIO")
    p = ler(PROTO)
    datas = len(re.findall(r"\d{2}/\d{2}/20\d\d", p))
    certo(datas <= 6, "o protocolo tem %d datas (teto: 6)" % datas,
          "acima disso ele voltou a ser diario -- mova para o EVIDENCIAS.md")
    nucleo = p[:p.find("## 6. O JUIZ")] if "## 6. O JUIZ" in p else p
    kb_n = len(nucleo.encode("utf-8")) / 1024
    kb_t = len(p.encode("utf-8")) / 1024
    certo(kb_n <= 11, "o nucleo (§0 a §5) tem %.1f KB (teto: 11)" % kb_n)
    certo(kb_t <= 22, "o documento inteiro tem %.1f KB (teto: 22)" % kb_t,
          "a v10 tinha 40,6 KB e a §1 dela dizia que a dieta era o maior custo")
    linhas = p.count("\n")
    certo(linhas <= 520, "o protocolo tem %d linhas (teto: 520)" % linhas)


def bloco_5_toda_secao_citada_existe():
    print("\n[5] TODA § CITADA EXISTE -- referencia morta e pior que nenhuma")
    p = ler(PROTO)
    existem = set()
    for m in re.finditer(r"^#{2,3}\s+[^\d\n]*?(\d+(?:\.\d+)?)[\.\s]", p, re.M):
        existem.add(m.group(1))
    sem_outras = re.sub(r"`?CLAUDE\.md`?[^\n]{0,60}?§\d+(?:\.\d+)?", "", p)
    sem_outras = re.sub(r"§\d+(?:\.\d+)?\s*(?:do|no|da)\s+`?CLAUDE", "", sem_outras)
    citadas = set()
    for m in re.finditer(r"§(\d+(?:\.\d+)?)(?:\s*[–-]\s*§?(\d+(?:\.\d+)?))?", sem_outras):
        citadas.add(m.group(1))
        if m.group(2):
            citadas.add(m.group(2))
    orfas = sorted(citadas - existem)
    certo(not orfas, "nenhuma § orfa no protocolo",
          "citadas e inexistentes: " + ", ".join("§" + o for o in orfas))
    t = ler(TEMPLATE)
    t_sem = re.sub(r"`?CLAUDE\.md`?[^\n]{0,60}?§\d+(?:\.\d+)?", "", t)
    orfas_t = sorted(set(re.findall(r"§(\d+\.\d+)", t_sem)) - existem)
    certo(not orfas_t, "nenhuma § orfa no template do relatorio",
          "o template aponta para " + ", ".join("§" + o for o in orfas_t))


def bloco_6_CONTROLE():
    print("\n[6] LINHA DE CONTROLE -- este guarda consegue ficar vermelho?")
    certo(os.path.exists(PROTO) and os.path.exists(CLAUDE) and os.path.exists(TEMPLATE),
          "os tres arquivos que este guarda le EXISTEM")
    p = ler(PROTO)
    certo(len(p) > 5000, "o protocolo tem conteudo (%d chars)" % len(p))
    certo("PACOTE_INEXISTENTE_XYZ" not in p, "e o casador NAO acha o que nao esta la")


# ---------------------------------------------------------------------------
# Os blocos que olham para o OBJETO, não para o texto

def conferir_relatorio(texto):
    """Devolve a lista de defeitos de um relatório de execução sob a v11."""
    defeitos = []
    if "EXECUTION CARD" not in texto:
        defeitos.append("sem EXECUTION CARD")
    else:
        i = texto.find("EXECUTION CARD")
        trecho = texto[i:i + 3000]
        faltam = linhas_do_card_ausentes(trecho)
        if faltam:
            defeitos.append("card sem: " + ", ".join(faltam))
    if not re.search(r"FAIXA DE REL[ÓO]GIO", texto):
        defeitos.append("sem FAIXA DE RELÓGIO")
    if not re.search(r"(?i)bateria", texto) or not re.search(r"(?i)rodadas?", texto):
        defeitos.append("sem a contagem da bateria (rodadas)")
    if not re.search(r"(?i)refer[êe]ncia", texto):
        defeitos.append("sem REFERÊNCIA")
    if "📊" not in texto:
        defeitos.append("nenhum número marcado 📊")
    if not re.search(r"(?i)nota[^\n]{0,40}\d{1,3}\s*/\s*100", texto):
        defeitos.append("sem a nota 0–100 da execução")
    return defeitos


def conferir_spec(texto):
    """Devolve a lista de defeitos de uma SPEC convertida sob a v11."""
    defeitos = []
    if not re.search(r"O QUE O ESTADO DA ARTE FAZ", texto):
        defeitos.append("sem a seção 'O QUE O ESTADO DA ARTE FAZ' (§7.3)")
    n = len(urls_externas(texto))
    if n < 3:
        defeitos.append("só %d URL(s) externa(s); a §7.3 exige 3" % n)
    if "BLOCO 0" not in texto:
        defeitos.append("sem BLOCO 0 (remedir antes de codar)")
    if "O QUE SAIU" not in texto:
        defeitos.append("sem a seção 'O QUE SAIU' (CLAUDE.md §11)")
    if "📊" not in texto:
        defeitos.append("nenhum número marcado 📊")
    if not re.search(r"(?i)muta[çc][ãa]o", texto):
        defeitos.append("nenhuma MUTAÇÃO declarada para os gates")
    return defeitos


def conferir_pacote(texto, executa):
    defeitos = []
    if "PROTOCOLO-AUTOBROKERS-AAA" not in texto:
        defeitos.append("não carrega o protocolo")
    else:
        i = texto.find("PROTOCOLO-AUTOBROKERS-AAA")
        if re.search(r"(?i)inteiro", texto[i:i + 160]):
            defeitos.append("manda ler o protocolo INTEIRO — viola a §1")
    if executa and "EXECUTION CARD" not in texto:
        defeitos.append("executa e não carrega o EXECUTION CARD")
    if "NENHUMA mensagem sai" not in texto and "NENHUMA MENSAGEM SAI" not in texto:
        defeitos.append("sem a trava 'NENHUMA mensagem sai'")
    return defeitos


def bloco_7_os_relatorios():
    print("\n[7] OS RELATORIOS -- o card, a faixa e a bateria no OBJETO, nao no texto")
    alvos = sorted(glob.glob(os.path.join(RELATORIOS, "SPEC-*-EXECUTION-REPORT.md")))
    sob = [a for a in alvos
           if (numero_da_spec(a) or 0) >= PRIMEIRA_SPEC_SOB_V11
           and numero_da_spec(a) not in EXECUTADAS_ANTES_DA_V11]
    for a in sob:
        d = conferir_relatorio(ler(a))
        certo(not d, "%s passa" % os.path.basename(a), " · ".join(d))
    if not sob:
        print("  --    nenhum relatorio >= SPEC-%03d ainda; o casador e provado abaixo"
              % PRIMEIRA_SPEC_SOB_V11)
    # 🔴 CONTROLE: um relatório falso SEM card TEM de reprovar, e um COM tudo TEM de passar
    ruim = "# Relatório\n## 1. Resumo\nfoi tudo bem, os testes passaram.\n"
    certo(bool(conferir_relatorio(ruim)), "CONTROLE: relatorio sem card REPROVA")
    bom = ("## 0.0 EXECUTION CARD\n" + "\n".join(l + " ... x" for l in LINHAS_DO_CARD)
           + "\nFAIXA DE RELÓGIO 1–2h\n📊 bateria: 3 rodadas inteiras\nREFERÊNCIA: x\n"
           "nota da execução: 94/100\n")
    certo(not conferir_relatorio(bom), "CONTROLE: relatorio completo PASSA",
          " · ".join(conferir_relatorio(bom)))
    certo("EXECUTION CARD" in ler(TEMPLATE) and re.search(r"FAIXA DE REL[ÓO]GIO", ler(TEMPLATE)),
          "o template ja traz card e faixa: quem o segue passa no bloco [7]")


def bloco_8_as_specs():
    print("\n[8] AS SPECs -- a pesquisa entra, ou a SPEC nao fecha")
    alvos = sorted(glob.glob(os.path.join(SPECS, "SPEC-*.md")))
    sob = []
    for a in alvos:
        n = numero_da_spec(a)
        if n is not None and n >= PRIMEIRA_SPEC_SOB_V11:
            t = ler(a)
            # só as escritas sob a v11 — as de 02/09 (v1) serão refeitas, nao acusadas
            if re.search(r"(?i)protocolo[^\n]{0,20}v11", t):
                sob.append((a, t))
    for a, t in sob:
        d = conferir_spec(t)
        certo(not d, "%s passa" % os.path.basename(a), " · ".join(d))
    if not sob:
        print("  --    nenhuma SPEC declara 'protocolo v11' ainda; o casador e provado abaixo")
    ruim = "# SPEC-999\n## BLOCO 0\nmedimos 📊 tudo.\n## O QUE SAIU\nnada\nmutação: x\n"
    d = conferir_spec(ruim)
    certo(bool(d) and any("URL" in x for x in d), "CONTROLE: SPEC sem URL externa REPROVA")
    bom = (ruim + "## O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS\n"
           "https://a.example/x https://b.example/y https://c.example/z\n")
    certo(not conferir_spec(bom), "CONTROLE: SPEC com a §7.3 e 3 URLs PASSA",
          " · ".join(conferir_spec(bom)))


def bloco_9_os_pacotes():
    print("\n[9] OS PACOTES -- o que o subagente recebe carrega o protocolo")
    vivos = sorted(glob.glob(os.path.join(PACOTES, "PACOTE-*.md")))
    certo(len(vivos) >= 5, "existem pelo menos 5 pacotes-modelo em docs/canon/pacotes/ (achei %d)" % len(vivos))
    for a in vivos:
        nome = os.path.basename(a)
        executa = "BUILDER" in nome or "AQUECIMENTO" in nome
        d = conferir_pacote(ler(a), executa)
        certo(not d, "%s passa" % nome, " · ".join(d))
    # os prompts antigos: ou estao marcados HISTORICO, ou obedecem
    antigos = sorted(glob.glob(os.path.join(CANON, "PROMPT-DE-EXECUCAO-*.md"))
                     + glob.glob(os.path.join(CANON, "PROMPT-DE-AQUECIMENTO-*.md")))
    for a in antigos:
        t = ler(a)
        if "HISTÓRICO: anterior à v11" in t:
            continue
        d = conferir_pacote(t, "EXECUCAO" in a)
        certo(not d, "%s (vivo) passa" % os.path.basename(a), " · ".join(d))
    ruim = "Você é o builder. Leia CLAUDE.md e execute.\n"
    certo(bool(conferir_pacote(ruim, True)), "CONTROLE: pacote sem protocolo REPROVA")
    ruim2 = "Leia docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md inteiro. EXECUTION CARD. NENHUMA mensagem sai."
    certo(any("INTEIRO" in x for x in conferir_pacote(ruim2, True)),
          "CONTROLE: pacote que manda ler o protocolo INTEIRO REPROVA")
    bom = "Leia docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md §0–§3, §5, §7.3. EXECUTION CARD. NENHUMA mensagem sai."
    certo(not conferir_pacote(bom, True), "CONTROLE: pacote correto PASSA")


def main() -> int:
    bloco_1_o_protocolo_se_carrega()
    bloco_2_o_portao_existe_em_tres_lugares()
    bloco_3_a_referencia_tem_caminho()
    bloco_4_o_documento_nao_virou_diario()
    bloco_5_toda_secao_citada_existe()
    bloco_6_CONTROLE()
    bloco_7_os_relatorios()
    bloco_8_as_specs()
    bloco_9_os_pacotes()
    print("\n  %d ok, %d falhas" % (OK, FAIL))
    return 1 if FAIL else 0


def test_o_protocolo_tem_policia():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
