"""A rubrica é honesta? — SPEC-083, Bloco C item 8.

> ## Cada ponto tem dono.

🔴 Sem estes testes, a nota pode ser *"um número bonito produzido por outra
coisa"*. Cada asserção aqui prova que **um item específico da rubrica responde
por um comportamento específico do corredor** — mexer no corredor move aquele
item, e só aquele.

📊 E a razão de existirem: na v1 da SPEC, o juiz achou a receita da rota vazia —
`_auto_playbook` para uma seguradora nova + um teste com uma chamada ao motor +
quatro comentários com a palavra CONTROLE = **49/100 sem responder uma tela
real**. Depois do primeiro conserto ele **refez a receita** com
`alfa × auto × bateria` e ainda tirava 30–45.
"""

from __future__ import annotations

import copy
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import detector_do_eixo_e as DET   # noqa: E402
import regua_motor as M            # noqa: E402
import replay as RP                # noqa: E402
import rubrica as RB               # noqa: E402

REGUA = ("allianz", "residencial", "maquina_de_lavar")


def _rota():
    r = M.rota_de(*REGUA)
    assert r is not None, "a rota de referencia sumiu do produto"
    return r


def _nota(**kw):
    return RB.medir(_rota(), mutacoes_ok=(3, 3), **kw)


def _pontos(nota, nome_do_item: str) -> int:
    for i in nota.itens:
        if i.nome == nome_do_item:
            return i.pontos
    raise AssertionError(f"item nao encontrado: {nome_do_item}")


# ═════════════════════════════════════════════════════════════════════════════
# 1 · A RÉGUA PONTUA — e o portão do eixo B não a barra
# ═════════════════════════════════════════════════════════════════════════════
def test_a_regua_pontua_e_nao_bate_no_portao():
    """📊 Medido em 21/08/2026: **64/96**.

    ⚠️ A SPEC-083 §4.1 estimava 💭 **73–84 sobre 100**. O número medido difere, e
    a causa está declarada, não escondida: `AMOSTRA: 1 de 140 sessões`. Com uma
    sessão só, os 2 pontos de *"≥2 sessões distintas"* e os 3 de *"o handoff casa
    tela real"* são perdidos **por amostragem**.

    🔴 *"Se ele não for 73, não conserte a rota para bater o número — conserte o
    número, e escreva por que ele difere."* — o Founder.

    O piso aqui é **≥55** (patamar `parcial`), não 73: é o que a medição sustenta.
    """
    n = _nota()
    assert n.estado is None, f"a regua caiu em {n.estado}"
    assert n.pontos >= 55, f"a regua caiu para {n.pontos}/{n.denominador}"
    assert n.denominador == 96, ("o denominador mudou; a nota passou a medir "
                                 "outra coisa e a comparacao historica quebrou")


def test_a_orfa_que_a_spec_nomeia_foi_MAPEADA_e_o_replay_ainda_acha_orfas():
    """📊 A SPEC-083 §4.2 nomeia UMA órfã funcional — e ela **deixou de ser órfã**.

    ⚠️ **ESTE TESTE MUDOU DE FORMA DUAS VEZES, E AS DUAS PELO §9.3.**

    **Primeira vez:** exigia `len(orfas_funcionais) == 1`, que era verdade num
    corpus de UMA sessão. Com o teto de 5 por rota (P-083-1) viraram quatro
    sessões e 15 órfãs, e o `1` passou a guardar uma verdade vencida.
    A lição migrou para: *a órfã que a SPEC NOMEIA continua órfã — se sumir sem
    passo, a medida afrouxou.*

    **Segunda vez (22/08/2026):** o BLOCO 3 **escreveu o passo**
    (`agendamento_para_confirma`), e a tela

    ```
    "Agendamento para: *Sexta-feira {DATA}*, *período da manhã das 09:00 às
     13:00*  Podemos continuar ? *1 -* ..."
    ```

    passou a ser RESPONDIDA. O teste ficou vermelho — e ficou certo em ficar:
    ele acusou uma mudança de fato, que é exatamente o que ele existe para
    fazer.

    🔴 **A lição migra de novo, e agora ela tem DUAS metades, porque a antiga
    fazia as duas ao mesmo tempo:**

    ```
    1. a tela que a SPEC nomeia agora TEM PASSO      <- o ganho, provado
    2. e o replay CONTINUA achando órfãs             <- a medida não afrouxou
    ```

    Sem a metade 2, mapear tudo faria o teste passar por vacuidade — e um teste
    que fica verde quando não há nada para medir não guarda nada.
    """
    r = RP.replay(_rota())

    # ---- metade 1: a tela que a SPEC nomeia foi MAPEADA -----------------
    ainda_orfa = [t for t in r.orfas_funcionais
                  if "agendamento para" in M._norm(t.texto)
                  and "podemos continuar" in M._norm(t.texto)]
    assert not ainda_orfa, (
        "a orfa que a SPEC-083 §4.2 nomeia VOLTOU a ser orfa -- o passo "
        "`agendamento_para_confirma` do BLOCO 3 parou de casar. "
        f"texto: {ainda_orfa[0].texto[:80] if ainda_orfa else ''}")

    # 🔴 E o CONTROLE POSITIVO: ela nao sumiu do corpus; ela e RESPONDIDA.
    #    Sem isto, apagar a sessao do corpus faria a metade 1 passar.
    pb = M.get_playbook(_rota().ref)
    tela = ("Agendamento para: *Sexta-feira 05/09/2025*, *periodo da manha das "
            "09:00 as 13:00*\n\nPodemos continuar ? *1 -* Sim *2 -* Voltar")
    passo = M.match_ura_step(pb, tela, subservice="encanador")
    assert passo and passo.get("step") == "agendamento_para_confirma", (
        "a tela da SPEC nao e respondida pelo passo que o BLOCO 3 escreveu -- "
        f"casou: {(passo or {}).get('step')}")

    # ---- metade 2: o replay CONTINUA achando orfas ----------------------
    # ⚠️ Sem esta linha, mapear TUDO faria a metade 1 passar por vacuidade.
    assert r.orfas_funcionais, (
        "o replay nao acha NENHUMA orfa funcional. Ou o corredor ficou perfeito "
        "-- e ai esta assercao precisa ser reescrita com a prova disso -- ou a "
        "MEDIDA AFROUXOU e ninguem viu.")


def test_o_determinismo_da_regua_nao_cai():
    """📊 A rota de referência acerta **80,8%** das telas que pedem algo.

    ⚠️ O piso é 70% — o mesmo corte que o portão do eixo B usa para decidir se o
    corredor *fala* aquela URA. Abaixo disso a rota deixou de conversar, e isso
    é regressão, não amostra.
    """
    d = RP.replay(_rota()).determinismo
    assert d is not None and d >= 0.70, f"determinismo caiu para {d}"


# ═════════════════════════════════════════════════════════════════════════════
# 2 · CADA PONTO TEM DONO — as mutações da rubrica
#
# 🔴 As três provam que a nota não é *"um número bonito produzido por outra
#    coisa"*: mexer numa peça move **aquele** item, e o total cai **exatamente**
#    o que aquele item vale.
# ═════════════════════════════════════════════════════════════════════════════
def test_zerar_regras_para_o_cliente_faz_D_cair_EXATAMENTE_3():
    """⚠️ **Esta mutação nasceu errada e a medição a corrigiu.**

    A primeira versão zerava `subservices[rota]["regras_para_o_cliente"]` e a
    nota **não se movia**. Medido:

    ```
    📊 playbooks com `regras_para_o_cliente` no NIVEL PLAYBOOK : 1 de 14
    📊 subservicos com regras PROPRIAS                         : 0 de 62
    ```

    🔴 **O campo não existe em subserviço nenhum do produto.** Zerá-lo ali era
    apagar algo que não estava lá.

    ⚠️ E o que isso significa para a rubrica, declarado em vez de escondido: as
    **6 rotas** de `allianz-residencial` dividem **uma** declaração. O item tem
    dono — o playbook —, mas o dono é compartilhado. É a assimetria que a
    SPEC-083 §3.5 nomeia e trata com `SEM_FABRICA`: *"13 corredores perdem 6 dos
    10 pontos do eixo D por uma razão ARQUITETURAL, não de qualidade"*.
    """
    rota = _rota()
    pb = M.get_playbook(rota.ref)
    assert not (pb["subservices"][rota.servico] or {}).get("regras_para_o_cliente"), \
        ("o campo passou a existir no subservico -- a mutacao precisa mudar de "
         "lugar, e a heranca declarada acima deixou de valer")
    guardado = copy.deepcopy(pb.get("regras_para_o_cliente"))
    antes = _nota()
    try:
        pb["regras_para_o_cliente"] = []
        depois = _nota()
    finally:
        pb["regras_para_o_cliente"] = guardado
    assert antes.por_eixo()["D"][0] - depois.por_eixo()["D"][0] == 3, \
        (antes.por_eixo()["D"], depois.por_eixo()["D"])


def test_remover_o_freio_faz_C_cair_EXATAMENTE_8():
    """📊 O freio vale 8 porque é a última porta antes de mandar um prestador a
    um endereço. A ausência dele no residencial deixou 65 sessões passarem."""
    rota = _rota()
    pb = M.get_playbook(rota.ref)
    guardado = list(pb.get("finalize_anchors") or [])
    antes = _nota()
    try:
        pb["finalize_anchors"] = [r"ZZ_NUNCA_CASA_ZZ"]
        depois = _nota()
    finally:
        pb["finalize_anchors"] = guardado
    assert antes.por_eixo()["C"][0] - depois.por_eixo()["C"][0] == 8, \
        (antes.por_eixo()["C"], depois.por_eixo()["C"])


def test_o_eixo_E_cai_para_o_SEGUNDO_melhor_arquivo_nao_para_zero():
    """🔴 A regra por-arquivo (§3.6): a nota da rota é a do **MELHOR** arquivo.

    📊 A v1 zerava a régua e travava o próprio gate: um arquivo desqualificado
    derrubava a rota inteira mesmo havendo outro, bom, cobrindo-a.
    """
    n = _nota()
    assert n.por_eixo()["E"][0] == 15, "o eixo E deixou de fechar"
    # o arquivo que a SPEC nomeia como o exemplar do defeito hoje QUALIFICA
    caminho = os.path.join(RAIZ, "tests", "test_a_maquina_de_lavar_vai_ate_o_fim.py")
    assert DET.qualifica(caminho), \
        "o teste da maquina de lavar voltou a chamar regex em vez do motor"


# ═════════════════════════════════════════════════════════════════════════════
# 3 · OS ESTADOS SÃO DIFERENTES — e confundi-los custa caro
# ═════════════════════════════════════════════════════════════════════════════
def test_SEM_CORPUS_e_NAO_RESPONDE_sao_estados_OPOSTOS():
    """🔴 *"São estados opostos, com ações opostas."*

    `SEM_CORPUS` é trabalho de **coleta**; `NAO_RESPONDE` é trabalho de
    **escrever passos**. 📊 Fundir os dois faria a SPEC-084 mandar para coleta
    rotas cujo acervo está cheio — o erro que a v1 cometeu com 13 rotas.
    """
    notas = [RB.medir(r, mutacoes_ok=(3, 3)) for r in M.rotas()]
    sem_corpus = [n for n in notas if n.estado == "SEM_CORPUS"]
    nao_responde = [n for n in notas if n.estado == "NAO_RESPONDE"]
    assert sem_corpus and nao_responde, \
        "a rubrica deixou de distinguir os dois estados"
    # 🔴 e o que os separa é MEDIDO, não declarado:
    for n in sem_corpus:
        assert not n.replay.telas, f"{n.rota} e SEM_CORPUS com telas no corpus"
    for n in nao_responde:
        assert n.replay.telas, f"{n.rota} e NAO_RESPONDE sem corpus nenhum"


def test_o_portao_do_eixo_B_zera_A_C_D_E():
    """🔴 §3.8 — *"Nenhuma rota recebe pontos de A, C, D ou E enquanto B < 8."*

    📊 O portão existe porque a receita da rota vazia sobrevivia ao primeiro
    conserto: `alfa × auto × bateria` tirava 30–45 por herança de família (C) e
    teste simbólico (E), **sem responder uma tela**.
    """
    barradas = [n for n in (RB.medir(r, mutacoes_ok=(3, 3)) for r in M.rotas())
                if n.estado == "NAO_RESPONDE"]
    assert barradas, "nenhuma rota barrada -- o portao virou enfeite"
    for n in barradas:
        assert all(i.eixo == "B" for i in n.itens), \
            f"{n.rota} foi barrada e mesmo assim ganhou pontos fora do eixo B"


# ═════════════════════════════════════════════════════════════════════════════
# 4 · O ITEM EXCLUÍDO NÃO É RENORMALIZADO (§3.9)
# ═════════════════════════════════════════════════════════════════════════════
def test_item_excluido_sai_do_denominador_e_aparece_explicito():
    """🔴 *"A nota é sempre sobre o denominador real, e o excluído aparece."*

    E o patamar **carrega** o denominador: `AAA(90)`, `quase(100)`. Sem isso,
    `86/90 = 95,6%` viraria AAA e `94/100 = 94%` não — e "AAA" passaria a
    significar coisas diferentes na mesma tabela.
    """
    n = _nota()
    assert n.fora, "nenhum item excluido -- o SEM_ESPELHO deixou de existir?"
    assert n.denominador == 100 - sum(n.fora.values())
    assert f"({n.denominador})" in n.patamar, \
        f"o patamar nao carrega o denominador: {n.patamar}"


def test_a_nota_nao_e_reescalada_para_100():
    """🔴 *"Nunca reescalar a EXIBIÇÃO para /100."* 61/86 = 71% pareceria melhor
    que uma rota que ganhou 65 de 100 disputando tudo."""
    import medir_rota as MR
    n = _nota()
    saida = MR.imprimir_nota(n, detalhado=False)
    assert f"{n.pontos}/{n.denominador}" in saida
    assert f"{n.pontos}/100" not in saida or n.denominador == 100


# ═════════════════════════════════════════════════════════════════════════════
# 5 · O DETECTOR DO EIXO E — os três controles nomeados na §3.6
#
# 🔴 *"Se os dois primeiros passarem, o detector está cego. Este controle é o que
#    dá direito a confiar na nota."*
# ═════════════════════════════════════════════════════════════════════════════
def test_o_detector_do_eixo_E_pega_regex_atras_de_variavel():
    """📊 Os dois casos reais passam a âncora por **variável intermediária**, e um
    usa `.get("anchor")`. Um detector literal devolveria ZERO desqualificações no
    arquivo que a SPEC nomeia como o exemplar do defeito.
    """
    import tempfile
    fonte = '''
import re
PB = {"ura_steps": [], "capture_anchors": {}}
PASSOS = PB["ura_steps"]
ANC = PB["capture_anchors"]

def passo_de(texto):
    for p in PASSOS:
        anc = p.get("anchor")
        if anc and re.search(anc, texto):
            return p

def _captura(chave, texto):
    return re.search(ANC[chave], texto)
'''
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "test_falso.py")
        open(p, "w", encoding="utf-8").write(fonte)
        achados = DET.analisar_modulo(p)
    funcoes = {a.funcao for a in achados}
    assert funcoes == {"passo_de", "_captura"}, \
        f"o taint nao propagou: {funcoes}"


def test_CONTROLE_o_detector_NAO_desqualifica_ancora_em_args_1():
    """🔴 §3.6 regra 4: *"a agulha virou palheiro, e o regex inspeciona a FORMA
    da declaração"* — legítimo, e declarado como exceção na §9.4 do CLAUDE.md."""
    import tempfile
    fonte = '''
import re
PB = {"ura_steps": [{"anchor": "x"}]}

def confere_forma():
    for p in PB["ura_steps"]:
        # o regex procura `\\*` DENTRO da ancora: a ancora e o PALHEIRO
        if re.search(r"\\\\\\*", p["anchor"]):
            return p
'''
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "test_forma.py")
        open(p, "w", encoding="utf-8").write(fonte)
        assert DET.analisar_modulo(p) == [], \
            "o detector desqualificou inspecao de FORMA -- regra 4 quebrada"


def test_o_arquivo_da_regua_qualifica_e_o_defeituoso_qualificou_depois_do_conserto():
    """🔴 A prova nos DOIS sentidos que a §3.6 exige.

    📊 `test_a_maquina_de_lavar_vai_ate_o_fim.py` era DESQUALIFICADO (2
    ocorrências: `passo_de:68` e `_captura:296`) e QUALIFICA depois do conserto
    do Bloco C item 5.
    """
    for nome in ("test_a_regua_nao_tem_furo.py",
                 "test_a_maquina_de_lavar_vai_ate_o_fim.py"):
        p = os.path.join(RAIZ, "tests", nome)
        assert DET.qualifica(p), f"{nome} desqualificado: {DET.analisar(p)}"
