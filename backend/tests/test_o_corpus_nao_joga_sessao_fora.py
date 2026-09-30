"""O corpus não joga sessão fora — e o que ele deixa fora está ESCRITO.

═══════════════════════════════════════════════════════════════════════════════
🔴 O DEFEITO QUE ESTE GUARDA IMPEDE (SPEC-119 F2, 27/09/2026)
═══════════════════════════════════════════════════════════════════════════════

O teto de 5 sessões por rota era um teto **TOTAL**, e a cota das sessões que
chegaram ao fim competia com ele. 📊 Medido no acervo de 27/09/2026, com o
classificador da F1:

```
201 sessões ficaram fora do corpus pelo teto — e 36 delas TINHAM DESFECHO.
```

🔴 **A sessão COM DESFECHO é a que prova que a rota chega ao fim** — o item de 12
pontos da régua. Descartá-la por teto é medir a rota errado e mandar para coleta
uma rota cujo acervo já estava cheio.

A regra passou a ser:

```
sessão COM DESFECHO   entra SEMPRE. `TETO_DE_DESFECHO = None`
sessão SEM desfecho   entra por diversidade até a rota ter PISO_POR_ROTA
```

═══════════════════════════════════════════════════════════════════════════════
AS QUATRO PORTAS, e a LINHA DE CONTROLE de cada uma (CLAUDE.md §9.2 e §9.3)
═══════════════════════════════════════════════════════════════════════════════

```
① nenhuma sessão COM DESFECHO fica fora         🔴 CONTROLE: com `teto_de_desfecho`
                                                   de volta em 5, UMA fica fora
② sessão SEM desfecho acima do piso fica FORA   🔴 é o controle que impede
                                                   "aceitar tudo" de passar
③ o corpus continua MASCARADO                   🔴 CONTROLE: o auditor CONSEGUE
                                                   acusar telefone, CPF e PLACA
④ o INDICE.md declara, por seguradora, quantas  🔴 CONTROLE: o próprio índice
   entraram e POR QUE as que ficaram fora          declara ZERO "c/ desfecho FORA"
   ficaram
```

═══════════════════════════════════════════════════════════════════════════════
🔴 POR QUE AS SESSÕES SÃO LIDAS DO CORPUS, E NÃO ESCRITAS AQUI — CLAUDE.md §9.4
═══════════════════════════════════════════════════════════════════════════════

*"O que se afirma é o comportamento do MOTOR sobre o texto REAL."*

As candidatas que chegam a `escolher_sessoes` são montadas a partir dos `.jsonl`
versionados: `session_id`, `wa_timestamp`, as telas e o `servico` vêm do arquivo,
e o **desfecho é decidido por `gerar_corpus_de_telas.sessao_chegou_ao_fim`**, o
mesmo motor que o gerador usa. Nenhuma sessão, tela ou etiqueta é inventada aqui,
e nenhum texto de tela é digitado — por isso nenhum PII pode entrar por este
arquivo (CLAUDE.md §13.3).

⚠️ E o guarda roda **SEM BANCO**: é essa a razão de o corpus ser versionado
(a docstring do gerador, §6.6). O único acesso é a leitura dos `.jsonl` e do
`INDICE.md`.
"""

from __future__ import annotations

import collections
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import gerar_corpus_de_telas as G      # noqa: E402
import higiene_do_corpus as H          # noqa: E402
import regua_motor as M                # noqa: E402

CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")
INDICE = os.path.join(CORPUS, "INDICE.md")

# 🔴 A PLACA — o padrão vem do MASCARADOR DO PRODUTO, nunca de uma cópia local.
#    `auditar_pii` confere telefone, CPF, CNPJ, e-mail e razão social, mas **não**
#    confere placa; quem mascara placa é `templatize`. Sem esta linha, "placa" na
#    lista do gate seria promessa sem guarda.
from app.services.atlas.templater import _PII_PATTERNS  # noqa: E402

RX_PLACA = next(rx for rx, alvo in _PII_PATTERNS if alvo == "{PLACA}")


# ─────────────────────────────────────────────────────────────────────────────
# O acervo do teste: as candidatas RECONSTRUÍDAS do corpus versionado
# ─────────────────────────────────────────────────────────────────────────────
def _arquivos() -> List[str]:
    if not os.path.isdir(CORPUS):
        pytest.skip("corpus ainda não gerado")
    return [n for n in sorted(os.listdir(CORPUS)) if n.endswith(".jsonl")]


def _linhas(nome: str) -> List[Dict[str, Any]]:
    with open(os.path.join(CORPUS, nome), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def _candidatas(nome: str) -> List[Tuple[Any, str, Set[str], bool, Optional[str]]]:
    """`(sid, wa_ts, telas, chegou_ao_fim, servico)` — a MESMA tupla do gerador.

    🔴 `chegou_ao_fim` sai de `G.sessao_chegou_ao_fim`, o motor. O teste não sabe
    o que é desfecho, e não deve saber.
    """
    seg, ramo = nome[:-len(".jsonl")].split("-", 1)
    ref = M.resolve_playbook_ref(seg, ramo)
    pb = M.get_playbook(ref) if ref else None
    por_sessao: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for d in _linhas(nome):
        por_sessao[d["session_id"]].append(d)
    saida = []
    for sid, ls in por_sessao.items():
        telas = [l["text"] for l in ls]
        saida.append((
            sid,
            max(l.get("wa_timestamp") or "" for l in ls),
            set(telas),
            G.sessao_chegou_ao_fim(pb, telas) if pb else False,
            ls[0].get("servico"),
        ))
    return saida


def _com_desfecho_por_arquivo() -> List[Tuple[str, list]]:
    """Só os arquivos cujo playbook consegue decidir desfecho. Os outros não
    dizem nada sobre esta regra, e um teste que os incluísse passaria de graça.
    """
    fora = []
    for nome in _arquivos():
        cand = _candidatas(nome)
        if any(c[3] for c in cand):
            fora.append((nome, cand))
    return fora


def test_o_acervo_do_teste_tem_do_que_falar():
    """🔴 O anti-carimbo: se nenhuma sessão do corpus tiver desfecho, todas as
    asserções da porta ① passam vazias. Este teste mede o denominador."""
    arquivos = _com_desfecho_por_arquivo()
    assert len(arquivos) >= 8, (
        "só %d arquivo(s) com sessão de desfecho — o corpus não sustenta o guarda"
        % len(arquivos))
    total = sum(sum(1 for c in cand if c[3]) for _n, cand in arquivos)
    assert total >= 40, "só %d sessões com desfecho no corpus inteiro" % total


# ═════════════════════════════════════════════════════════════════════════════
# ① NENHUMA SESSÃO COM DESFECHO FICA FORA — pelo MOTOR, com o teto de produção
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("nome", [n for n, _c in _com_desfecho_por_arquivo()])
def test_nenhuma_sessao_com_desfecho_fica_fora_do_corpus(nome):
    """🔴 A regra que não se negocia (SPEC-119 F2).

    ⚠️ MUTAÇÃO que prova que este guarda CONSEGUE ficar vermelho: baixe
    `TETO_DE_DESFECHO` de `None` para `5` em `gerar_corpus_de_telas.py`.
    """
    cand = dict((c[0], c) for c in _candidatas(nome))
    escolhidas, _notas = G.escolher_sessoes(list(cand.values()))
    esquecidas = [sid for sid, c in cand.items() if c[3] and sid not in set(escolhidas)]
    assert not esquecidas, (
        "%s: %d sessao(oes) COM DESFECHO ficaram FORA do corpus: %s — "
        "é ela que prova que a rota chega ao fim (SPEC-119 F2)"
        % (nome, len(esquecidas), esquecidas))


def test_CONTROLE_o_teto_de_desfecho_CONSEGUE_descartar():
    """🔴 CONTROLE do ① — prove que os dois lados CONSEGUEM ser diferentes.

    Com `teto_de_desfecho=1` a MESMA chamada, sobre as MESMAS sessões, tem de
    descartar sessão com desfecho. Sem este controle, o teste acima passaria
    igual num `escolher_sessoes` que aceitasse tudo.
    """
    candidatos = [(n, c) for n, c in _com_desfecho_por_arquivo()
                  if sum(1 for x in c if x[3]) >= 2]
    assert candidatos, "nenhum arquivo com ≥2 sessões de desfecho — controle cego"
    nome, cand = candidatos[0]
    escolhidas, notas = G.escolher_sessoes(cand, 1, teto_de_desfecho=1)
    fora = [c[0] for c in cand if c[3] and c[0] not in set(escolhidas)]
    assert fora, ("CONTROLE FALHOU em %s: com teto_de_desfecho=1 NENHUMA sessão "
                  "com desfecho foi descartada — o guarda ① não mede nada" % nome)
    assert any("ALARME" in n for n in notas), (
        "CONTROLE FALHOU: o descarte aconteceu em SILÊNCIO, sem ALARME nas notas")


# ═════════════════════════════════════════════════════════════════════════════
# ② A SESSÃO SEM DESFECHO ACIMA DO PISO CONTINUA FORA
# ═════════════════════════════════════════════════════════════════════════════
def test_sessao_SEM_desfecho_acima_do_piso_continua_fora():
    """🔴 A linha de controle que impede "aceitar tudo" de passar.

    Com `piso_por_rota=1`, cada rota fica com as suas sessões de desfecho **mais
    até `PISO_DE_DIVERSIDADE`** por diversidade (era "mais UMA" até a SPEC-121
    F3b, que passou a guardar a prova do que falta). Tudo o que sobrar de SEM desfecho tem de ficar fora —
    e o INDICE tem de dizer quantas.
    """
    achou_alguem_fora = False
    for nome, cand in _com_desfecho_por_arquivo():
        escolhidas, notas = G.escolher_sessoes(cand, 1)
        dentro = set(escolhidas)
        # a regra de cima continua valendo
        assert not [c[0] for c in cand if c[3] and c[0] not in dentro], (
            "%s: o piso baixo não pode expulsar sessão COM DESFECHO" % nome)
        fora_sem = [c[0] for c in cand if not c[3] and c[0] not in dentro]
        if fora_sem:
            achou_alguem_fora = True
            assert any("SEM desfecho fora do corpus" in n for n in notas), (
                "%s: %d sessão(ões) sem desfecho saíram em SILÊNCIO — a SPEC-083 "
                "§7 proíbe truncar calado" % (nome, len(fora_sem)))
    assert achou_alguem_fora, (
        "com piso 1 NENHUMA sessão sem desfecho ficou fora — ou o corpus é "
        "magro demais, ou `escolher_sessoes` deixou de capar. Nos dois casos "
        "o guarda ① passaria de graça")


def test_o_piso_de_producao_e_um_PISO_e_nao_um_teto():
    """🔴 O nome não mente: com o valor de produção, rota com muito desfecho
    ULTRAPASSA o piso — é isso que distingue um piso de um teto."""
    ultrapassou = []
    for nome, cand in _com_desfecho_por_arquivo():
        escolhidas, _n = G.escolher_sessoes(cand)
        por_servico = collections.Counter(
            c[4] for c in cand if c[0] in set(escolhidas))
        for servico, n in por_servico.items():
            if n > G.PISO_POR_ROTA:
                ultrapassou.append((nome, servico, n))
    assert ultrapassou, (
        "nenhuma rota passou de %d sessões — `PISO_POR_ROTA` está funcionando "
        "como TETO, e a SPEC-119 F2 não foi aplicada" % G.PISO_POR_ROTA)
    assert G.TETO_DE_DESFECHO is None, (
        "TETO_DE_DESFECHO = %r. Em produção ele é None: sessão com desfecho não "
        "sai por teto (SPEC-119 F2)" % (G.TETO_DE_DESFECHO,))


# ═════════════════════════════════════════════════════════════════════════════
# ③ O CORPUS CONTINUA MASCARADO — telefone, CPF e PLACA
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("nome", _arquivos())
def test_o_corpus_continua_mascarado(nome):
    """🔴 Nenhum telefone inteiro, CPF, CNPJ, e-mail ou razão social no `.jsonl`."""
    # 🔴 `nomes_da_sessao` — SPEC-119 CONSERTO A, 28/09/2026.
    #    📊 Este chamador ignorava o parâmetro que a própria docstring de
    #    `auditar_pii` diz existir "porque um primeiro nome solto não casa
    #    nenhum padrão lexical". Com ele, o guarda que devolvia `0 sujas` sobre
    #    86 linhas de nome em claro devolve 134.
    linhas = list(_linhas(nome))
    por_sessao = {}
    for d in linhas:
        por_sessao.setdefault(str(d.get("session_id")), []).append(d.get("text") or "")
    nomes = {sid: H.nomes_no_vocativo(ts) for sid, ts in por_sessao.items()}

    def _pii(d):
        return H.auditar_pii(d.get("text") or "",
                             nomes_da_sessao=nomes.get(str(d.get("session_id")), set()))

    sujas = [(i, _pii(d)) for i, d in enumerate(linhas, 1) if _pii(d)]
    assert not sujas, "%s: %d linha(s) com PII: %s" % (nome, len(sujas), sujas[:3])


@pytest.mark.parametrize("nome", _arquivos())
def test_nenhuma_placa_sobreviveu_no_corpus(nome):
    """🔴 A PLACA, que `auditar_pii` NÃO confere — só `templatize` a mascara.

    Este é o guarda que faltava: o corpus cresceu 35% nesta fatia, e crescer é
    exatamente quando uma placa entra sem ninguém ver.
    """
    achados = [(i, RX_PLACA.search(d.get("text") or "").group(0))
               for i, d in enumerate(_linhas(nome), 1)
               if RX_PLACA.search(d.get("text") or "")]
    assert not achados, "%s: placa no corpus: %s" % (nome, achados[:5])


def test_CONTROLE_o_auditor_e_a_placa_CONSEGUEM_acusar():
    """🔴 CONTROLE do ③ — se estes cinco passassem limpos, ③ seria carimbo.

    ⚠️ Os valores são SINTÉTICOS, escolhidos por FORMA. Nenhum vem do acervo, e
    é por isso que eles podem estar escritos aqui (CLAUDE.md §13.3).
    """
    for t in ["ligamos para +55 (47) 90000-0000 e ninguem atendeu",
              "digite o CPF 030.111.222-95 do titular",
              "mande para ninguem@exemplo.com.br o comprovante"]:
        assert H.auditar_pii(t), "CONTROLE FALHOU: auditor passou limpo -> %r" % t

    # 🔴 O NOME — a quinta forma, e a que DE FATO vazou. SPEC-119 CONSERTO A.
    #
    # 📊 Este controle provava telefone, CPF, e-mail e placa; nenhuma delas era
    # a que estava no acervo. 86 linhas com primeiro nome de segurado em claro
    # atravessaram a SPEC-083, a SPEC-117 e a SPEC-119 com o controle VERDE —
    # *"um guarda que não tem como falhar não guarda nada"* (CLAUDE.md §9.3).
    #
    # ⚠️ Os nomes abaixo são SINTÉTICOS (nenhum vem do acervo) e cobrem as
    # quatro formas medidas: solto, dentro de negrito, depois de um abridor de
    # fala, e nome COMPLETO com sobrenome.
    for t in ["Zoraide, o telefone informado nao e valido",
              "*Zoraide*, agora definiremos o endereco para onde o veiculo vai",
              "Certo, Zoraide. A solicitacao de agendamento foi encerrada",
              "Ola ZORAIDE BENEVIDES DA CUNHA, como foi o servico de REBOQUE?"]:
        assert H.auditar_pii(t), "CONTROLE FALHOU: nome passou limpo -> %r" % t

    # e o outro sentido: o guarda do nome NÃO pode comer língua de serviço
    for t in ["Certo! Por favor digite o *CPF* ou *CNPJ* do(a) titular da apolice",
              "Roubo, furto e incendio tem franquia propria",
              "Agora, informe apenas o nome do logradouro (rua, avenida, etc.)",
              "Elogios, reclamacoes e informacoes de como proceder",
              "{NOME}, escolha a opcao desejada: Seguro Auto"]:
        assert not H.auditar_pii(t), (
            "CONTROLE FALHOU: o guarda do nome comeu portugues -> %r  %s"
            % (t, H.auditar_pii(t)))
    for t in ["a placa ABC1D23 esta correta?", "confirme a placa abc1d23"]:
        assert RX_PLACA.search(t), "CONTROLE FALHOU: placa passou limpa -> %r" % t
    # e o que NÃO é placa continua não sendo — o achado de 10/08/2026
    assert not RX_PLACA.search("periodo das 8h00 as 18h00"), (
        "CONTROLE FALHOU: 'das 8h00' voltou a virar placa")


# ═════════════════════════════════════════════════════════════════════════════
# ④ O INDICE.md DECLARA QUANTAS ENTRARAM E POR QUE AS DE FORA FICARAM
# ═════════════════════════════════════════════════════════════════════════════
def _indice() -> str:
    if not os.path.exists(INDICE):
        pytest.skip("INDICE.md ainda não gerado")
    return open(INDICE, encoding="utf-8").read()


def test_o_indice_declara_cada_arquivo_com_quantas_sessoes_entraram():
    txt = _indice()
    for nome in _arquivos():
        if nome == "tokio-condominio.jsonl":
            continue   # fora de escopo (RAMOS_EM_ESCOPO) — não é regerado
        assert "`%s`" % nome in txt, "%s não está declarado no INDICE.md" % nome


def test_o_indice_nao_tem_sessao_com_desfecho_fora():
    """🔴 O número do produto, lido do próprio índice: ZERO ALARME."""
    txt = _indice()
    assert "ALARME" not in txt, (
        "o INDICE.md tem ALARME de sessão COM DESFECHO fora do corpus — "
        "regenere com `TETO_DE_DESFECHO = None`")
    linhas = [l for l in txt.splitlines() if re.match(r"\| `[a-z]+-[a-z]+\.jsonl`", l)]
    assert linhas, "a tabela de arquivos do INDICE.md desapareceu"
    for l in linhas:
        colunas = [c.strip() for c in l.strip("|").split("|")]
        assert colunas[-1] == "0", (
            "coluna 'c/ desfecho FORA' não é 0 nesta linha do INDICE.md: %s" % l)


def test_o_indice_diz_POR_QUE_cada_seguradora_continua_sem_etiqueta():
    """🔴 *"Sem etiqueta" com motivo é medição; sem motivo é buraco.*"""
    txt = _indice()
    assert "SEM ETIQUETA" in txt, "o INDICE.md não tem a seção de sem-etiqueta"
    bloco = txt.split("SEM ETIQUETA", 1)[1].split("## Linhas RECUSADAS", 1)[0]
    declarados = {m.group(1) for m in
                  (re.match(r"\| `([a-z]+-[a-z]+)`", l) for l in bloco.splitlines())
                  if m}
    for nome in _arquivos():
        chave = nome[:-len(".jsonl")]
        if chave == "tokio-condominio":
            continue
        assert chave in declarados, (
            "%s não aparece na tabela de SEM ETIQUETA do INDICE.md — não se sabe "
            "quantas sessões dela entraram com etiqueta nem por que as outras não"
            % chave)


def test_todo_motivo_do_indice_e_um_motivo_que_o_gerador_SABE_produzir():
    """🔴 CONTROLE contra motivo escrito à mão no índice: cada motivo listado
    tem de ser uma das constantes `MOTIVO_*` do gerador."""
    bloco = _indice().split("SEM ETIQUETA", 1)[1].split("## Linhas RECUSADAS", 1)[0]
    # 🔴 SPEC-121 F3/F3b: exploração, consulta de pedido existente e aparelho
    #    pedido pelo menu do eletricista são motivos que o gerador SABE produzir
    #    desde 29/09 — faltavam aqui, e o índice regerado os escreve.
    conhecidos = [G.MOTIVO_FUGA, G.MOTIVO_TRANSFERIU, G.MOTIVO_LINK,
                  G.MOTIVO_SEM_MENU, G.MOTIVO_EXPLORACAO, G.MOTIVO_CONSULTA,
                  G.MOTIVO_APARELHO,
                  G.MOTIVO_ASSUNTO.split("%s")[0].strip(),
                  G.MOTIVO_DESCONHECIDO.split("%s")[0].strip(),
                  "nenhuma sessão sem etiqueta"]
    vistos = 0
    for l in bloco.splitlines():
        if not l.startswith("|") or "---" in l or "seguradora-ramo" in l:
            continue
        col = [c.strip() for c in l.strip("|").split("|")]
        if len(col) < 4 or not col[3]:
            continue
        vistos += 1
        assert any(c in col[3] for c in conhecidos), (
            "motivo desconhecido no INDICE.md (não sai de nenhuma constante "
            "MOTIVO_* do gerador): %r" % col[3])
    assert vistos >= 15, "só %d motivos lidos do INDICE.md — leitura cega" % vistos


def test_a_sessao_declarada_SEM_ETIQUETA_esta_SEM_ETIQUETA_no_corpus():
    """🔴 O elo (protocolo §0.3): o motivo é medição sobre a sessão, e o corpus é
    onde o MOTOR gravou o veredito. As duas fontes têm de concordar.

    Sem isto, `motivo_sem_etiqueta` poderia estar descrevendo outra sessão — duas
    medições certas e nenhuma ligação.

    📊 Medido em 27/09/2026 no corpus regerado: o INDICE lista **98** sessões sem
    etiqueta e **41** delas estão no corpus (as outras 57 ficaram fora pelo piso,
    e sobre essas não há linha a conferir). O piso de 40 abaixo é esse número.
    """
    bloco = _indice().split("SEM ETIQUETA", 1)[1].split("## Linhas RECUSADAS", 1)[0]
    servico_por_sessao: Dict[str, Set[Optional[str]]] = collections.defaultdict(set)
    for nome in _arquivos():
        for d in _linhas(nome):
            servico_por_sessao[d["session_id"]].add(d.get("servico"))
    conferidas = 0
    for l in bloco.splitlines():
        if not l.startswith("|") or "---" in l:
            continue
        col = [c.strip() for c in l.strip("|").split("|")]
        if len(col) < 5:
            continue
        # 🔴 SPEC-121 F3b · o id de ATENDIMENTO (`8ad1d251+1`) também é conferido.
        #    Desde a F3 a sessão é partida em atendimentos (o robô recomeça), e o
        #    padrão antigo `[0-9a-f]{8}` pulava todo id com `+k` — a contagem caiu
        #    de 41 para 39 sem nenhuma sessão ter deixado de concordar. Baixar o
        #    piso seria aceitar a cegueira; a lição migra para o padrão.
        for sid in re.findall(r"`([0-9a-f]{8}(?:\+\d+)?)`", col[4]):
            if sid not in servico_por_sessao:
                continue   # sessão fora do corpus pelo piso — nada a conferir
            conferidas += 1
            assert servico_por_sessao[sid] == {None}, (
                "o INDICE diz que `%s` está SEM ETIQUETA, e no corpus ela tem "
                "servico=%r" % (sid, sorted(
                    x for x in servico_por_sessao[sid] if x is not None)))
    assert conferidas >= 40, (
        "só %d sessões conferidas contra o corpus — o elo não foi medido "
        "(em 27/09/2026 eram 41)" % conferidas)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O guarda do próprio arquivo — CLAUDE.md §13.3 e §13.9
# ═════════════════════════════════════════════════════════════════════════════
MARCA_FIM_DO_CONTEUDO = "def test_este_arquivo_nao_carrega_pii"

# 🔴 Os três sintéticos do CONTROLE são a ÚNICA PII-forma legítima aqui, e cada um
#    está nomeado: um guarda que ignorasse "qualquer coisa perto de CONTROLE"
#    deixaria passar um CPF real na linha de baixo.
SINTETICOS_DO_CONTROLE = ("030.111.222-95", "+55 (47) 90000-0000",
                          "ninguem@exemplo.com.br", "ABC1D23", "abc1d23")


def test_este_arquivo_nao_carrega_pii_nem_nome_de_corretora():
    """CLAUDE.md §13.3 e §13.9 — e o guarda mede o PRÓPRIO arquivo.

    🔴 As telas deste teste são LIDAS do corpus (já mascarado). O que poderia
    entrar por descuido é o que está digitado aqui.

    ⚠️ Ele lê o arquivo **até** o marcador: a própria lista de proibidos contém
    as palavras proibidas, e sem isso o guarda acusaria a si mesmo.
    """
    inteiro = open(os.path.abspath(__file__), encoding="utf-8").read()
    fonte, marca, _ = inteiro.partition(MARCA_FIM_DO_CONTEUDO)
    assert marca and len(fonte) > 0.8 * len(inteiro), (
        "o marcador mudou de lugar e o guarda deixou de ler o arquivo todo")
    for sintetico in SINTETICOS_DO_CONTROLE:
        fonte = fonte.replace(sintetico, "{SINTETICO}")
    proibido = {
        "CPF com pontuação": r"\d{3}\.\d{3}\.\d{3}-\d{2}",
        "CNPJ": r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",
        "telefone com DDD": r"\(?\d{2}\)?\s?9?\d{4}[-\s]\d{4}",
        "placa Mercosul": r"\b[a-z]{3}\d[a-z]\d{2}\b",
        "placa antiga": r"\b[a-z]{3}[-\s]?\d{4}\b",
        "e-mail": r"[\w.]+@[\w.]+\.\w{2,}",
    }
    for nome, padrao in proibido.items():
        achados = re.findall(padrao, fonte, re.IGNORECASE)
        assert not achados, "⛔ %s neste arquivo de teste: %s" % (nome, achados[:3])
    for corretora in ("resulta", "autofleet", "amandus", "regina", "saionara"):
        assert corretora not in fonte.lower(), (
            "⛔ CLAUDE.md §13.9: nome de corretora/pessoa no teste: %r" % corretora)
