"""Os guardas do Bloco A da SPEC-083 — o corpus, a higiene e a tabela de ramo.

🔴 **Todo guarda aqui é provado NOS DOIS SENTIDOS** (CLAUDE.md §9.3):
*"um guarda que não tem como falhar não guarda nada"* — e o irmão dele,
*"um que nunca fica verde é bloqueio"*.

Cada teste que afirma `X está limpo` tem, ao lado, o teste que **suja X de
propósito e exige o vermelho**.

📊 O guarda que este arquivo substitui era `grep -cE '[0-9]{11}'`. Ele **não casa**
`+55 (47) 99627-4743` — a maior sequência de dígitos ali tem CINCO. Devolvia 0
com quatro telefones no arquivo.
"""

from __future__ import annotations

import json
import os
import re
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import higiene_do_corpus as H          # noqa: E402
import padroes_de_ramo as PR           # noqa: E402
import regua_motor as M                # noqa: E402
import zonas_do_acervo as Z            # noqa: E402

CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")


def _linhas_do_corpus():
    if not os.path.isdir(CORPUS):
        pytest.skip("corpus ainda não gerado")
    for nome in sorted(os.listdir(CORPUS)):
        if not nome.endswith(".jsonl"):
            continue
        with open(os.path.join(CORPUS, nome), encoding="utf-8") as fh:
            for i, linha in enumerate(fh, 1):
                if linha.strip():
                    yield nome, i, json.loads(linha)


# ═════════════════════════════════════════════════════════════════════════════
# 1 · A AUDITORIA DE PII — os dois sentidos
# ═════════════════════════════════════════════════════════════════════════════
def test_o_corpus_nao_vaza_pii():
    """O corpus gerado está limpo."""
    sujas = [(n, i, H.auditar_pii(d["text"]))
             for n, i, d in _linhas_do_corpus() if H.auditar_pii(d["text"])]
    assert not sujas, f"{len(sujas)} linhas sujas: {sujas[:5]}"


def test_CONTROLE_a_auditoria_de_pii_CONSEGUE_acusar():
    """🔴 CONTROLE — sem ele o teste acima é enfeite.

    📊 O `grep -cE '[0-9]{11}'` da v1 da SPEC devolvia 0 sobre estas quatro linhas.
    """
    devem_acusar = [
        "Registramos o telefone *+55 (47) 99627-4743* para contato.",
        "Anotei seu numero *(48) 99909-5995*. Esta correto?",
        "Por favor digite o CPF 030.111.222-95 do titular",
        "Envie para joao.silva@exemplo.com.br o comprovante",
        "Contate a Oficina Bruno Mecanica Ltda para retirar",
    ]
    for t in devem_acusar:
        assert H.auditar_pii(t), f"CONTROLE FALHOU: passou limpo -> {t!r}"


def test_CONTROLE_a_auditoria_de_pii_CONSEGUE_passar():
    """🔴 O outro sentido: *"um guarda que sempre acusa é bloqueio"*.

    ⚠️ A linha da HDI existe porque a regra de razão social **recusou 8 telas de
    chegada do prestador** na estreia — `*HDI SEGUROS S.A*` é o nome da PRÓPRIA
    seguradora. Era a SPEC-083 §6.4 acontecendo comigo.
    """
    devem_passar = [
        "Registramos o telefone *+{TELEFONE}* para contato.",
        "Por favor digite o CPF {CPF} do titular",
        "{NOME}, escolha a opcao desejada: Seguro Auto",
        "*HDI SEGUROS S.A*: o prestador chegou no local para te atender?",
        "Allianz Seguros S.A informa que sua assistencia foi aberta",
    ]
    for t in devem_passar:
        assert not H.auditar_pii(t), f"CONTROLE FALHOU: acusou -> {t!r} {H.auditar_pii(t)}"


def test_o_nome_solto_no_vocativo_e_acusado_quando_a_sessao_o_conhece():
    """📊 SPEC-083 Bloco A: *"um primeiro nome no início da tela passaria a
    auditoria inteira — e é exatamente o vazamento que
    `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` nomeia como o real."*"""
    assert H.auditar_pii("Rafael, escolha a opcao desejada",
                         nomes_da_sessao=["Rafael"])
    assert not H.auditar_pii("{NOME}, escolha a opcao desejada",
                             nomes_da_sessao=["Rafael"])


# ═════════════════════════════════════════════════════════════════════════════
# 2 · O CORPUS É SÓ TELA DE URA
# ═════════════════════════════════════════════════════════════════════════════
def test_o_corpus_e_so_direction_in():
    """SPEC-083 §6.3. ⚠️ 📊 Este guarda **passa com 100% num corpus 29% humano** —
    ele mede a DIREÇÃO e o problema é o EMISSOR. Por isso existe o próximo."""
    for n, i, d in _linhas_do_corpus():
        assert d.get("direction") in (None, "in"), f"{n}:{i}"


def test_o_corpus_nao_tem_falas_de_gente():
    """🔴 O guarda que o de cima não é (SPEC-084 §2.5.2, exigência ②).

    Ancorado em `^…$`, NUNCA em prefixo. 📊 Razão medida: o padrão em prefixo
    rejeitava `"certo! por favor digite o *cpf*…"` — **a tela do CPF da Allianz,
    78 sessões**, que é o nó de maior retorno do acervo. O guarda da v2 nunca
    ficava vermelho; o da v3 nunca ficaria verde.
    """
    fala_de_gente = re.compile(
        r"^(ok|certo|perfeito|um momento|mais um momento|com quem falo|"
        r"ajudo em algo mais|bom dia tudo bem)[!.,?]?$")
    achados = [(n, i, d["text"][:40]) for n, i, d in _linhas_do_corpus()
               if fala_de_gente.match(M._norm(d["text"]).strip())]
    assert not achados, f"fala humana no corpus: {achados[:5]}"


def test_CONTROLE_o_guarda_de_fala_humana_CONSEGUE_acusar():
    """🔴 A prova nos dois sentidos que a SPEC-084 §2.5.2 exige no item ③."""
    fala_de_gente = re.compile(
        r"^(ok|certo|perfeito|um momento|mais um momento|com quem falo|"
        r"ajudo em algo mais|bom dia tudo bem)[!.,?]?$")
    # semeado: tem de ficar VERMELHO
    for t in ["ok", "Certo.", "um momento", "Com quem falo?"]:
        assert fala_de_gente.match(M._norm(t).strip()), f"nao acusou: {t!r}"
    # a tela do CPF da Allianz: tem de ficar VERDE
    cpf = "Certo! Por favor digite o *CPF* ou *CNPJ* do(a) titular da apolice"
    assert not fala_de_gente.match(M._norm(cpf).strip()), \
        "o guarda rejeitou a tela do CPF da Allianz (78 sessoes) -- e o BLOCO 0 nunca fecharia"


# ═════════════════════════════════════════════════════════════════════════════
# 3 · A HIGIENE — a exceção da senha (CA-062)
# ═════════════════════════════════════════════════════════════════════════════
TELA_27 = ("O telefone registrado nesse atendimento para contato e o que estamos "
           "falando agora:\n+55 (47) 99627-4743.\n\nSua senha sera os 4 ultimos "
           "digitos desse telefone *4743*")


def test_a_ancora_de_senha_sobrevive_ao_mascaramento():
    """🔴 CA-062. 📊 O JUIZ 2 mediu que a primeira versão desta exceção era
    **INERTE**: `subn(count=1)` trocava o `{TELEFONE}` do topo, não o `{SEGREDO}`
    do fim, e o verificador revertia — a exceção existia no comentário e não no
    comportamento.
    """
    pb = M.get_playbook("allianz-residencial-whatsapp@v1")
    senha_crua = M.extract_capture_anchors(pb, TELA_27).get("password")
    assert senha_crua, "a tela de referencia deixou de capturar senha"
    limpo, flags = H.higienizar(pb, TELA_27, set())
    assert flags["senha_preservada"], "a excecao da §6.4 nao rodou"
    assert M.extract_capture_anchors(pb, limpo).get("password") == senha_crua


def test_CONTROLE_a_excecao_da_senha_nao_devolve_telefone_comum():
    """🔴 O outro sentido: a exceção não pode virar um buraco de PII."""
    pb = M.get_playbook("allianz-residencial-whatsapp@v1")
    comum = "Registramos o telefone *+55 (47) 99627-4743* para contato."
    limpo, flags = H.higienizar(pb, comum, set())
    assert not flags["senha_preservada"]
    assert "99627" not in limpo and "4743" not in limpo, f"vazou: {limpo}"


def test_o_telefone_do_topo_continua_mascarado_na_tela_da_senha():
    """📊 A exceção preserva os 4 dígitos da SENHA e mais nada."""
    pb = M.get_playbook("allianz-residencial-whatsapp@v1")
    limpo, _ = H.higienizar(pb, TELA_27, set())
    assert "{TELEFONE}" in limpo
    assert "99627" not in limpo


# ═════════════════════════════════════════════════════════════════════════════
# 4 · O DISCRIMINADOR DE VOCATIVO — e o CONTROLE que prova que ele não come português
# ═════════════════════════════════════════════════════════════════════════════
def test_o_vocativo_estrutural_nao_come_portugues():
    """🔴 O CONTROLE que dá direito à regra.

    📊 O `templater.py` registra três frases reais destruídas por uma regra
    lexical de vocativo: *"Roubo, furto e incêndio…"*, *"Agora, me informe o
    CEP…"*, *"Elogios, reclamações…"*. **Nenhuma lista de palavras cobre o
    português.** A trava aqui é ESTRUTURAL: um nome varia sobre o mesmo
    esqueleto; um abridor de frase é sempre a mesma palavra.
    """
    lingua = ["Roubo, furto e incendio tem franquia propria e voce paga",
              "Agora, me informe o CEP do local do atendimento por favor",
              "Elogios, reclamacoes e informacoes de como proceder aqui",
              "Certo, agora preciso da placa do veiculo para continuar"]
    dado = ["Rafael, escolha a opcao desejada: seguro auto servico residencia",
            "Marisa, escolha a opcao desejada: seguro auto servico residencia",
            "Carla, escolha a opcao desejada: seguro auto servico residencia"]
    esq_dado, _ = H.levantar_vocativos(lingua + dado)
    for t in lingua:
        limpo, _ = H._mascarar_vocativo(t, esq_dado), None
        assert limpo[0] == t, f"comeu portugues: {t!r} -> {limpo[0]!r}"
    for t in dado:
        limpo, houve = H._mascarar_vocativo(t, esq_dado)
        assert houve and limpo.startswith("{NOME}"), f"nao mascarou: {t!r}"


# ═════════════════════════════════════════════════════════════════════════════
# 5 · A TABELA DE RAMO
# ═════════════════════════════════════════════════════════════════════════════
def test_o_dicionario_de_ramo_nao_tem_chave_duplicada():
    """🔴 Python descarta chave repetida **em silêncio** — sem erro, sem aviso.
    📊 Este assert disparou na estreia e pegou um contador errado."""
    assert len(PR.PADROES_DE_RAMO) == PR.CHAVES_ESCRITAS_PADROES_DE_RAMO
    assert len(PR.RESPOSTAS_DE_RAMO) == PR.CHAVES_ESCRITAS_RESPOSTAS_DE_RAMO


def test_a_tabela_de_ramo_exige_dotall():
    """🔴 O guarda que impede a cópia de um padrão multilinha para uma âncora.

    📊 Quatro alternativas caem de 37/26/4/3 sessões para **ZERO** sem
    `re.DOTALL`. O motor do produto compila as âncoras dele **sem** a flag —
    quem copiar uma destas para um `ura_step` ganha o `numero_residencia` de volta.
    """
    tela = M._norm("Qual seguro deseja utilizar?\n\n*1 - Residencial:* para sua casa")
    p = r"qual seguro deseja utilizar\?.{0,40}resid[ea]ncial"
    assert re.search(p, tela) is None, \
        "sem DOTALL este padrao passou a casar -- o teste perdeu o sentido"
    assert re.search(p, tela, re.DOTALL) is not None, \
        "com DOTALL o padrao tem de casar; se nao casa, a tabela quebrou"


def test_todas_as_regex_da_tabela_de_ramo_compilam():
    for nome, d in (("PADROES_DE_RAMO", PR.PADROES_DE_RAMO),
                    ("RESPOSTAS_DE_RAMO", PR.RESPOSTAS_DE_RAMO),
                    ("TELAS_DE_CARDAPIO", PR.TELAS_DE_CARDAPIO)):
        for k, p in d.items():
            re.compile(p, re.DOTALL)   # levanta re.error se quebrar


def test_a_sessao_da_regua_classifica_como_residencial_pelo_nivel_2():
    """🔴 O CONTROLE nomeado na SPEC-083 §8, e ele já falhou uma vez.

    📊 `7ac3c101` tem **29 eventos `in` e ZERO `out`**. Se a saída disser
    "nível 1", a regra leu um `out` que não existe. E se disser `indefinido`,
    a SPEC falhou no Bloco A **medindo a si mesma**.
    """
    if not M.tem_banco():
        pytest.skip("sem banco")
    eventos = [e for e in M.eventos_observados(seguradora="allianz")
               if str(e.get("session_id") or "").startswith("7ac3c101")]
    assert eventos, "a sessao da regua sumiu do acervo"
    pares = [(e["direction"], Z.norm_para_classificar(e.get("text") or ""))
             for e in sorted(eventos, key=lambda x: x["wa_timestamp"])]
    assert not any(d == "out" for d, _ in pares), "a sessao ganhou `out`; o controle mudou"
    ramo, nivel = PR.classificar_ramo("allianz", pares)
    assert (ramo, nivel) == ("residencial", "nivel-2-texto"), (ramo, nivel)


# ═════════════════════════════════════════════════════════════════════════════
# 6 · A ZONA
# ═════════════════════════════════════════════════════════════════════════════
def test_fronteira_e_nao_fronteira_nao_se_cruzam():
    """🔴 SPEC-084 §2.5.1.4. Padrão que casa os dois não entra na tabela.

    *"Um guarda sem controle negativo não distingue 'transferiu' de 'não
    conseguiu transferir'."*
    """
    assert Z.cruzamento_fronteira_x_nao_fronteira() == []


def test_CONTROLE_o_cruzamento_CONSEGUE_acusar():
    Z.FRONTEIRAS["_teste"] = [r"vou direcionar voce para nosso menu"]
    Z.NAO_E_FRONTEIRA["_teste"] = [r"vou direcionar voce para nosso menu"]
    Z._CACHE.clear()
    try:
        assert Z.cruzamento_fronteira_x_nao_fronteira(), "o cruzamento e enfeite"
    finally:
        del Z.FRONTEIRAS["_teste"], Z.NAO_E_FRONTEIRA["_teste"]
        Z._CACHE.clear()


def test_o_robo_que_se_apresenta_nao_conta_como_humano():
    """🔴 O controle negativo da pista do Founder.

    📊 Sem ele, `meu nome é|me chamo|sou a` marca **88% das sessões da allianz**,
    84% da azul e 89% da alfa — porque o robô também se apresenta, e mais que a
    gente.
    """
    robo = M._norm("Ola! Eu sou a Laiz, assistente virtual da Zurich")
    gente = M._norm("Ola, meu nome e Gabriela e irei realizar seu atendimento")
    assert not Z.tem_apresentacao_humana("zurich", robo)
    assert Z.tem_apresentacao_humana("hdi", gente)


def test_o_sou_do_vocativo_nao_casa_dentro_de_outra_palavra():
    """📊 Achado por medição: `sou (o|a)` sem `\\b` casa DENTRO de
    `avi[sou o s]eu sinistro`, e `botao 1: sou o segurado` é rótulo de MENU."""
    for falso in ["se voce ja avisou o seu sinistro, aguarde",
                  "voce e o segurado ou o terceiro? botao 1: sou o segurado"]:
        assert not Z.tem_apresentacao_humana("yelum", M._norm(falso)), falso


def test_os_invisiveis_saem_antes_do_norm():
    """📊 `combustí<U+00AD>vel` (soft hyphen) faz `combust[ií]vel` FALHAR, e a
    perda vira só um número menor. 🔴 O `_norm` do motor NÃO os remove — e não se
    toca nele nesta SPEC. A limpeza acontece antes."""
    t = "combustí­vel acabou"
    assert not re.search("combustivel", M._norm(t))
    assert re.search("combustivel", Z.norm_para_classificar(t))
