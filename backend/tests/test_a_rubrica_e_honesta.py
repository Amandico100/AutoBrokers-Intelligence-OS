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
    """A nota da rota-exemplo, com a tupla de mutacao REAL do repositorio.

    🔴 SPEC-089 BLOCO D — E ERA ESTA LINHA, sozinha, a causa do eixo E = 9.

    📊 O teste passava `mutacoes_ok=(3, 3)` a mao. O repositorio declara **12**
    mutacoes em `test_a_regua_nao_tem_furo.py`, e `rubrica.py:1004` zera o item
    de 6 pontos quando os dois numeros divergem — dizendo, corretamente,
    *"numero sem fonte (§12.1)"*.

    ⚠️ **A regua estava certa e o teste estava errado.** O item nunca foi
    quebrado: ele reprovava um numero inventado, que era o proprio teste que
    inventava. A SPEC lista SEIS hipoteses para essa causa; 📊 a causa e' uma
    linha.

    🔴 Agora a tupla vem de `_mutacoes_declaradas_no_repo()` — a mesma fonte
    que a regua confere. Duas listas que precisam concordar divergem (§5); com
    UMA fonte, nao ha' o que divergir.
    """
    n = RB._mutacoes_declaradas_no_repo()
    assert n, (
        "nao consegui LER o `MUTACOES` do repo — zero medido nao e zero nao "
        "medido, e sem esse numero o eixo E deste teste nao significa nada")
    return RB.medir(_rota(), mutacoes_ok=(n, n), **kw)


def _pontos(nota, nome_do_item: str) -> int:
    for i in nota.itens:
        if i.nome == nome_do_item:
            return i.pontos
    raise AssertionError(f"item nao encontrado: {nome_do_item}")


# ═════════════════════════════════════════════════════════════════════════════
# 1 · A RÉGUA PONTUA — e o portão do eixo B não a barra
# ═════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
# 🔴 QUARENTENA — P-226, e a dívida é da SPEC-089, não desta.
# ---------------------------------------------------------------------------
# 📊 Medido em 24/08/2026: cinco asserções deste arquivo estão VERMELHAS, e
# ninguém sabia — `pytest tests/` abortava a sessão inteira antes de chegar
# aqui, o meta-guarda o exclui de propósito (ele tem `def test_`), e o
# `broker_outcome_regression_pack` não o cita. **Guarda vermelho e invisível.**
#
#   :72   assert 102 == 96          "o denominador mudou; a nota passou a
#                                    medir outra coisa"
#   :133  assert []                 "o replay não acha NENHUMA órfã funcional.
#                                    Ou o corredor ficou perfeito — e aí esta
#                                    asserção precisa ser reescrita com a prova
#                                    disso — ou a MEDIDA AFROUXOU e ninguém viu"
#   :199  "o subserviço já tem regra própria — a mutação precisa mudar de lugar"
#   :253  assert 9 == 15            "o eixo E deixou de fechar"
#   :371  assert 102 == (100 - 4)
#
# 🔴 A RÉGUA ESTÁ DEVOLVENDO 102 NUMA ESCALA DE 100, e parou de achar órfã.
# Uma régua assim **aprova o que deveria reprovar** — e o que ela aprova é uma
# rota que chega em segurado. É BLOCKER, e o Founder já cravou: **é da
# SPEC-089**, não da 085. Consertar aqui seria mexer na régua durante a
# execução que ela vai medir.
#
# ⚠️ `strict=True` corta dos dois lados: uma delas que volte a passar QUEBRA a
# suíte, obrigando a tirá-la daqui. Quarentena que não esvazia vira aterro
# (`PROTOCOLO-AUTOBROKERS-AAA` §1).
# 🔴 SPEC-089 BLOCO D — A QUARENTENA ESVAZIOU, E NENHUMA SAIU TROCANDO O
#    NUMERO ESPERADO POR OUTRO. Cada uma saiu pela CAUSA:
#
#   :72  `denominador == 96`   -> 📊 102 nunca foi a NOTA, e' o DENOMINADOR.
#                                 O enunciado do P-226 estava errado. Agora
#                                 crava a PROPRIEDADE (soma dos maximos) e o
#                                 numero de hoje com a causa ao lado.
#   :133 `orfas_funcionais`    -> 🔴 exigia que o produto continuasse
#                                 IMPERFEITO. Virou o inverso: se existir,
#                                 e' NOMEADA — e hoje sao zero.
#   :199 `not guardado_sub`    -> 📊 o subservico GANHOU regra propria. A
#                                 precondicao venceu e nunca foi necessaria.
#   :253 `eixo E == 15`        -> 📊 UMA linha: o teste passava (3,3) e o
#                                 repo declara 12. A regua estava CERTA.
#   :371 `item excluido`       -> o BLOCO A desta SPEC o quebrou, e ele
#                                 estava certo em quebrar. A licao migrou.
#
# ⚠️ A marca fica declarada e VAZIA de proposito: quem precisar por um teste
# em quarentena de novo usa esta, e o `strict=True` obriga a esvaziar.
# **Quarentena que nao esvazia vira aterro** (`PROTOCOLO-AUTOBROKERS-AAA` §1).
QUARENTENA_SPEC089 = pytest.mark.xfail(
    strict=True,
    reason="vazia — as cinco sairam pela causa na SPEC-089 BLOCO D",
)

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

    # =====================================================================
    # 🔴 SPEC-089 BLOCO D — O ENUNCIADO ESTAVA ERRADO, NAO A REGUA
    # =====================================================================
    #
    # A assercao era `n.denominador == 96` com a frase *"a nota passou a medir
    # outra coisa"*. 📊 E o diagnostico do P-226 dizia *"a regua devolve
    # 102/100"* — 🔴 **102 nunca foi a NOTA. E' o DENOMINADOR**, e um
    # denominador maior que 100 nao e' defeito: e' a soma dos maximos dos itens
    # que esta rota disputa.
    #
    # ⚠️ E o denominador MUDOU DE VERDADE nesta SPEC, no BLOCO A: `SEM_ESPELHO`
    # deixou de sair, e a rota passou a disputar 4 pontos a mais.
    #
    # ⛔ Entao a assercao para de cravar um NUMERO e passa a cravar a
    # PROPRIEDADE que ela sempre quis proteger: **o denominador e' a soma dos
    # maximos que contam, e a nota nunca e' reescalada para 100.**
    soma = sum(i.maximo for i in n.itens if i.conta)
    assert n.denominador == soma, (
        f"o denominador ({n.denominador}) nao e a soma dos maximos que contam "
        f"({soma}) — a nota passou a medir outra coisa")
    assert n.denominador != 100 or soma == 100, (
        "o denominador virou 100 redondo — desconfie de reescala")

    # 🔴 E O NUMERO DE HOJE, COM DATA E CAUSA (§12.1). Ele nao e' um alvo:
    #    e' um marco. Se mudar, quem mudar escreve por que — como esta aqui.
    #
    #    📊 26/08/2026: 106 = 102 + os 4 pontos dos apelidos, que o BLOCO A
    #    trouxe de volta para dentro do denominador.
    assert n.denominador == 106, (
        f"o denominador e' {n.denominador} e nao 106. Se foi de proposito, "
        "troque o numero AQUI e escreva a causa ao lado — foi assim que este "
        "teste saiu da quarentena da SPEC-089")


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

    # ---- metade 2: a MEDIDA nao afrouxou --------------------------------
    #
    # =====================================================================
    # 🔴 SPEC-089 BLOCO D — ERA UM TESTE QUE SO' PASSAVA ENQUANTO HOUVESSE
    #    DEFEITO, e essa e' a forma mais perigosa das cinco
    # =====================================================================
    #
    # A assercao era `assert r.orfas_funcionais` — *"o replay CONTINUA achando
    # orfas"*. Ela existia por um bom motivo (sem ela, mapear TUDO faria a
    # metade 1 passar por vacuidade), e mesmo assim estava errada:
    #
    # ⛔ **Ela exigia que o produto continuasse imperfeito para ficar verde.**
    # 📊 As orfas funcionais desta rota sao ZERO hoje — o corredor melhorou, e
    # o guarda transformou a melhora em vermelho.
    #
    # 🔴 A licao MIGRA, e o inverso e' o que ela sempre quis dizer:
    #
    #     antes:  "ainda EXISTE orfa"      -> exige defeito
    #     agora:  "se existir, e' NOMEADA"  -> exige VISIBILIDADE
    #
    # ⚠️ E a vacuidade da metade 1 continua fechada, por outro caminho: o
    # `assert passo` acima nomeia a tela E o passo. Um mapeamento que engolisse
    # tudo casaria a tela com o passo ERRADO, e aquela assercao morde.
    for orfa in r.orfas_funcionais:
        assert " ".join(str(orfa.texto).split())[:40], (
            "o replay achou uma orfa funcional SEM TEXTO — ela nao da' para "
            "nomear, e uma orfa que ninguem consegue nomear e' invisivel")
    # 🔴 E O NUMERO DE HOJE, com data (§12.1): zero. Se subir, alguem
    #    afrouxou a medida OU o corredor piorou — e as duas pedem investigacao.
    assert len(r.orfas_funcionais) == 0, (
        f"o replay achou {len(r.orfas_funcionais)} orfa(s) funcional(is) onde "
        f"em 26/08/2026 havia ZERO. Ou a MEDIDA AFROUXOU, ou o corredor "
        f"piorou: {[' '.join(str(o.texto).split())[:60] for o in r.orfas_funcionais[:3]]}")


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
def test_a_regra_do_SUBSERVICO_move_D_e_a_do_corredor_NAO():
    """🔴 O C4 mudou o DONO deste item, e a mutação mudou de lugar com ele.

    ⚠️ **Esta mutação nasceu errada DUAS vezes, e a medição corrigiu as duas.**

    **1ª:** zerava `subservices[rota]["regras_para_o_cliente"]` e a nota não se
    movia — 📊 o campo não existia em subserviço nenhum do produto (0 de 62).

    **2ª:** passou a zerar o campo no NÍVEL PLAYBOOK, e funcionava — porque a
    régua tinha `sub.get(...) **or** pb.get(...)`. 📊 Esse fallback creditava a
    regra do CORREDOR a **9 rotas**, das quais **0** tinham regra própria.
    O item promete *"regras_para_o_cliente casam o corpus"* e media *"existe
    alguma regra em algum lugar deste corredor"*.

    🔴 O C4 tirou o fallback. Agora zerar o playbook **não move nada** — e isso
    é o CERTO, não uma regressão. A lição migra para a forma que prova a
    leitura nova:

    ```
    regra no SUBSERVIÇO, com frase REAL do corpus  ->  +3   (o item tem dono)
    regra no SUBSERVIÇO, com frase INVENTADA       ->   0   (o C5: a prova
                                                             sai da REGRA, não
                                                             de um comentário)
    regra só no CORREDOR                           ->   0   (o C4)
    ```

    ⚠️ A segunda linha é o que separa este teste de um carimbo. Sem ela,
    qualquer texto passaria e o item voltaria a medir presença, não conteúdo.
    """
    rota = _rota()
    pb = M.get_playbook(rota.ref)
    sub = pb["subservices"][rota.servico]

    # 📊 Frase LITERAL do corpus desta rota — a mesma que a régua já reconhece
    #    hoje no nível playbook. Se ela deixar de casar, este teste avisa.
    REAL = ("Seguro Automotivo com serviços residenciais e assistência 24 horas "
            "para a sua casa")
    INVENTADA = ("Esta regra foi escrita agora e nao existe em tela nenhuma do "
                 "acervo, e por isso NAO pode valer ponto nenhum na rubrica.")

    guardado_sub = copy.deepcopy(sub.get("regras_para_o_cliente"))
    guardado_pb = copy.deepcopy(pb.get("regras_para_o_cliente"))

    # =====================================================================
    # 🔴 SPEC-089 BLOCO D — A PRECONDICAO VENCEU, E O TESTE MELHORA SEM ELA
    # =====================================================================
    #
    # A linha era `assert not guardado_sub` — *"o subservico ja tem regra
    # propria, a mutacao precisa mudar de lugar"*. 📊 E o subservico GANHOU
    # regra propria: a rota melhorou, e a precondicao virou falsa.
    #
    # ⚠️ **Mas a precondicao nunca foi necessaria.** O corpo do teste ja'
    # remove a regra do subservico (`sub.pop`) e restaura no `finally` — ele
    # funciona tendo ou nao tendo regra propria antes. A linha so' escolhia
    # uma rota-exemplo, e o exemplo mudou de estado.
    #
    # 🔴 O que ela protegia de verdade — *"a mutacao esta' no lugar certo"* —
    # passa a ser afirmado direto: as duas gavetas EXISTEM para serem mutadas.
    assert isinstance(sub, dict) and isinstance(pb, dict), (
        "o subservico ou o corredor nao sao dicionarios — a mutacao nao tem "
        "onde mexer, e o teste passaria sem testar nada")

    try:
        # ── o C4: com regra SÓ no corredor, a rota NÃO pontua ────────────
        sub.pop("regras_para_o_cliente", None)
        so_corredor = _nota().por_eixo()["D"][0]

        # ── o C4, outro lado: regra PRÓPRIA com frase real SOBE 3 ────────
        sub["regras_para_o_cliente"] = [REAL]
        com_regra_real = _nota().por_eixo()["D"][0]

        # ── o C5: regra PRÓPRIA com frase inventada NÃO sobe ─────────────
        sub["regras_para_o_cliente"] = [INVENTADA]
        com_regra_falsa = _nota().por_eixo()["D"][0]
    finally:
        if guardado_sub:
            sub["regras_para_o_cliente"] = guardado_sub
        else:
            sub.pop("regras_para_o_cliente", None)
        pb["regras_para_o_cliente"] = guardado_pb

    assert com_regra_real - so_corredor == 3, (
        "🔴 C4: regra PROPRIA com frase real do corpus tem de valer +3. "
        f"so_corredor={so_corredor} com_regra_real={com_regra_real}")
    assert com_regra_falsa == so_corredor, (
        "🔴 C5: regra INVENTADA nao pode valer ponto -- a prova sai da REGRA, "
        f"nao de um comentario. so_corredor={so_corredor} "
        f"com_regra_falsa={com_regra_falsa}")


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

    ⚠️ **ESTE TESTE DEPENDIA DE A PRODUÇÃO ESTAR QUEBRADA — §9.3, 22/08/2026.**

    A versão anterior exigia `sem_corpus and nao_responde`: ela só passava
    enquanto existisse, no produto, **alguma rota muda**. 📊 A SPEC-084 fechou
    as duas últimas, `NAO_RESPONDE` foi a **zero**, e o guarda caiu — *por ter
    dado certo*.

    > 🔴 Um guarda que depende de a produção estar quebrada para de guardar no
    > instante em que ela é consertada.

    **A lição migra para onde ela é estável:** o que precisa ser provado é que
    a rubrica **sabe distinguir** os dois estados, e isso se prova com um caso
    CONSTRUÍDO — não com o acidente de haver uma rota ruim no ar.
    """
    notas = [RB.medir(r, mutacoes_ok=(3, 3)) for r in M.rotas()]
    sem_corpus = [n for n in notas if n.estado == "SEM_CORPUS"]

    # ── o que ainda é fato da produção ───────────────────────────────────
    assert sem_corpus, "nenhuma rota SEM_CORPUS -- o estado sumiu da rubrica"
    for n in sem_corpus:
        assert not n.replay.telas, f"{n.rota} e SEM_CORPUS com telas no corpus"

    # ── 🔴 E O QUE SEPARA OS DOIS, PROVADO POR CONSTRUÇÃO ────────────────
    #
    # Pego uma rota que HOJE responde e desligo o corredor dela. Se a rubrica
    # continuar chamando isso de `SEM_CORPUS`, ela fundiu os estados — e a
    # SPEC-084 voltaria a mandar para coleta um acervo cheio.
    rota = _rota()
    pb = M.get_playbook(rota.ref)
    guardado = list(pb.get("ura_steps") or [])
    try:
        pb["ura_steps"] = []
        muda = RB.medir(rota, mutacoes_ok=(3, 3))
    finally:
        pb["ura_steps"] = guardado

    assert muda.estado == "NAO_RESPONDE", (
        "🔴 uma rota COM corpus e SEM passos tem de ser NAO_RESPONDE, nunca "
        f"SEM_CORPUS -- a rubrica devolveu {muda.estado!r}")
    assert muda.replay.telas, (
        "o caso construido perdeu o corpus -- a prova deixou de valer")

    # 🔴 CONTROLE: a MESMA rota, intacta, NAO e nenhum dos dois estados.
    #    Sem esta linha, um bug que devolvesse NAO_RESPONDE para tudo passaria.
    intacta = RB.medir(rota, mutacoes_ok=(3, 3))
    assert intacta.estado not in ("NAO_RESPONDE", "SEM_CORPUS"), (
        f"CONTROLE: a rota intacta virou {intacta.estado!r}")


def test_o_portao_do_eixo_B_zera_A_C_D_E():
    """🔴 §3.8 — *"Nenhuma rota recebe pontos de A, C, D ou E enquanto B < 8."*

    📊 O portão existe porque a receita da rota vazia sobrevivia ao primeiro
    conserto: `alfa × auto × bateria` tirava 30–45 por herança de família (C) e
    teste simbólico (E), **sem responder uma tela**.

    ⚠️ **MESMA MIGRAÇÃO DO TESTE ACIMA, E PELA MESMA RAZÃO.** A versão anterior
    procurava uma rota barrada ENTRE AS 73 e falhava com *"o portão virou
    enfeite"* quando não achava nenhuma. 📊 Depois da SPEC-084 não há mais
    nenhuma — e o portão não virou enfeite: **ele ficou sem clientes.**

    🔴 A diferença importa: *"não há rota barrada"* e *"o portão não barra"* são
    coisas opostas, e a versão anterior não sabia distingui-las.
    """
    # 🔴 O portão é provado onde ele age: numa rota que TEM corpus e cujo
    #    corredor foi desligado. É o mesmo caso construído acima.
    rota = _rota()
    pb = M.get_playbook(rota.ref)
    guardado = list(pb.get("ura_steps") or [])
    try:
        pb["ura_steps"] = []
        barrada = RB.medir(rota, mutacoes_ok=(3, 3))
    finally:
        pb["ura_steps"] = guardado

    assert barrada.estado == "NAO_RESPONDE", (
        f"o portao nao barrou uma rota sem passo nenhum: {barrada.estado!r}")
    assert all(i.eixo == "B" for i in barrada.itens), (
        "🔴 a rota foi barrada e MESMO ASSIM ganhou pontos fora do eixo B: "
        f"{sorted({i.eixo for i in barrada.itens})}")

    # 🔴 CONTROLE: e a rota intacta CONTINUA ganhando pontos fora do B.
    #    Sem isto, um portao que barrasse TODA rota passaria neste teste.
    intacta = RB.medir(rota, mutacoes_ok=(3, 3))
    assert {i.eixo for i in intacta.itens} - {"B"}, (
        "CONTROLE: a rota intacta so tem itens do eixo B -- o portao esta "
        "barrando quem nao devia")


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

    # =====================================================================
    # 🔴 SPEC-089 BLOCO A QUEBROU ESTE TESTE — E ELE ESTA CERTO EM QUEBRAR
    # =====================================================================
    #
    # A assercao era `assert n.fora` com a frase *"o SEM_ESPELHO deixou de
    # existir?"*. 📊 Ele deixou de EXCLUIR, de proposito: nao conseguir medir
    # vale ZERO, nao vale nada.
    #
    # ⚠️ §9.3 — *"quando um fato muda, o teste muda com ele, e a licao MIGRA
    # em vez de morrer"*. A licao aqui e' a regra de exclusao, e ela agora tem
    # dois lados:
    #
    #     SEM_FABRICA / ROTA_INDISTINGUIVEL  -> NAO SE APLICA -> sai   ✅
    #     SEM_ESPELHO                        -> nao foi medido -> FICA 🔴
    #
    # 🔴 O lado que FICA e' o que esta SPEC acrescentou, e e' o que impede a
    # nota de subir quando o instrumento nao mede.
    assert RB.SEM_ESPELHO not in n.fora, (
        "o `SEM_ESPELHO` voltou a SAIR do denominador — a nota volta a subir "
        "por medir menos, que e' o defeito inteiro da SPEC-089 BLOCO A")

    # 🔴 E o item CONTINUA existindo, valendo zero e dizendo por que.
    apelidos = [i for i in n.itens if i.nome.startswith("apelidos")]
    assert len(apelidos) == 1 and apelidos[0].conta, (
        "o item dos apelidos sumiu ou voltou a ser excluido")
    assert apelidos[0].pontos == 0 and RB.SEM_ESPELHO in apelidos[0].evidencia, (
        "o item nao diz POR QUE valeu zero — quem le a nota precisa distinguir "
        f"'a rota e ruim' de 'ninguem mediu': {apelidos[0].evidencia[:90]}")

    # ── e a REGRA DE EXCLUSAO continua de pe' para quem NAO SE APLICA ─────
    #
    # ⚠️ CONTROLE: sem esta metade, um conserto que apagasse a exclusao INTEIRA
    #    passaria — e ai um item que nao se aplica a rota passaria a puni-la.
    fabricada = n._replace(itens=list(n.itens) + [
        RB.Item("D", "item que NAO SE APLICA", 0, 7, "-",
                excluido=RB.SEM_FABRICA)])
    assert fabricada.fora == {RB.SEM_FABRICA: 7}
    assert fabricada.denominador == n.denominador, (
        "um item que NAO SE APLICA entrou no denominador — a rota passa a ser "
        "punida por nao ter algo que ela nunca deveria ter")

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
