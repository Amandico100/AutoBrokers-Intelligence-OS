# -*- coding: utf-8 -*-
"""SPEC-123 · AJUSTE W (pós-confirmação) — as pendências P-N2 e P-N1 do laudo de confirmação.

W1 (P-N2, NO AR) — o conserto Y tinha ampliado `claims_shadow.detectar_sinistro`, o detector do PRODUTO
   que o webhook usa para o resumo de sinistros da corretora (`claims_shadow_digest`). O texto da URA
   gravado como `role=user` ("3 - Danos elétricos", "Caso tenha ocorrido uma batida, digite 2"…) virava
   sinistro FALSO. Agora o detector do produto é EXATAMENTE o de 3200228 e o vocabulário novo vale SÓ na
   segunda chance do atendimento (`human_handoff.sinistro_so_na_segunda_chance`), onde errar é chamar
   uma pessoa um pouco antes.
W2 (P-N1, só com `on`) — a pergunta ao segurado é SEMPRE a composta pelo código (pergunta da tela /
   frase do produto para o slot + opções filtradas). O texto livre do modelo nunca vai ao segurado: vai
   só ao diário, como "o modelo propôs".

Tudo pelo MOTOR: `detectar_sinistro`, `por_que_vai_direto_a_pessoa`, `decidir_destravamento`, o
`destravar` inteiro com o diário na borda (CLAUDE.md §9.4). Dublê só na borda (modelo, banco do diário).
🔴 MUTAÇÕES (uma vez, por cópia): W1 → recolocar o vocabulário em `claims_shadow` → os testes dos MENUS
VERMELHOS · W2 → `_pergunta_composta` volta a aceitar o texto do modelo → os testes W2 VERMELHOS.
⛔ Nenhum dado pessoal: telas mascaradas do acervo; nenhuma mensagem sai.
"""
from __future__ import annotations

import pytest

from tests.test_spec123_conserto_x import (
    CPF, PLACA, REF_HDI, REF_YELUM, TELA_LOCAL, TELA_PLACA, decidir, perguntar, sessao,
)
from tests.test_spec123_destravador_fio import (  # noqa: F401 — `dt`, `amb`, `_fio_fixo` são fixtures
    EMPRESA_A, TELA_SERVICOS, R, _Injetado, _fio_fixo, amb, destravar, dt, js, sessao_travada,
)
from app.services import destravador as DT


# =============================================================================
# W1 · o detector do PRODUTO não lê menu de URA como sinistro
# =============================================================================
#: 📊 laudo de confirmação da SPEC-123, P-N2: o texto de URA gravado como `role=user` que o detector
#: ampliado do conserto Y marcava como sinistro no resumo da corretora.
MENUS_DA_URA = ["3 - Danos elétricos",
                "Caso tenha ocorrido uma batida, digite 2",
                "houve uma colisão? 1-Sim",
                "Assistência para danos elétricos, digite 4"]

#: as falas do SEGURADO do red team (`rt-scripts/f7.py`) — todas vão DIRETO a uma pessoa
FALAS_DO_SEGURADO_F7 = [
    "segurado quer falar com uma pessoa", "cliente pediu atendente humano",
    "cliente prefere falar com alguem da corretora", "segurado pediu para falar com o corretor",
    "quer conversar com um humano de verdade", "cliente insiste em falar com gente",
    "segurado relata que bateu o carro", "bati o carro no poste", "colidiu na traseira",
    "roubaram o carro", "furtaram a moto", "alagou a casa toda", "incendio na cozinha",
    "danos eletricos na geladeira", "caiu um raio e queimou a TV", "a enchente levou o carro",
    "vendaval destelhou a casa", "quebrou o vidro do carro em batida", "pegou fogo no motor",
    "curto circuito queimou o portao",
]
#: CONTROLE — continuam com a segunda chance (o motivo ao lado)
CONTROLES = ["a bateria do carro arriou",                     # bateria ≠ bati
             "fiz um raio-x do joelho",                       # raio-x ≠ raio
             "quanto custa a cobertura de danos elétricos?",  # venda
             "duvida do segurado", "precisa de orientacao"]


@pytest.mark.parametrize("menu", MENUS_DA_URA)
def test_W1_o_menu_da_URA_nao_e_sinistro_no_detector_do_produto(menu):
    from app.services.claims_shadow import detectar_sinistro

    assert detectar_sinistro(menu) == (False, None, None), menu


def test_W1_CONTROLE_os_dois_detectores_CONSEGUEM_discordar_sobre_os_menus():
    """§9.3 (corolário): o guarda acima só guarda se o vocabulário estiver fora do produto. O sinal da
    segunda chance É forte o bastante para casar os quatro menus — então o `False` acima vem de o
    vocabulário NÃO estar no detector do produto, e não de as frases serem inofensivas."""
    from app.agents.tools.human_handoff import sinistro_so_na_segunda_chance

    assert all(sinistro_so_na_segunda_chance(m) for m in MENUS_DA_URA)


def test_W1_CONTROLE_o_detector_do_produto_continua_abrindo_o_sinistro_de_antes():
    from app.services.claims_shadow import detectar_sinistro

    for fala in ("bati o carro e preciso de guincho", "roubaram o carro", "pegou fogo no motor",
                 "abri um sinistro e queria saber o preço da franquia"):
        assert detectar_sinistro(fala)[0], fala


def _decide(motivo, fala):
    import app.agents.tools.human_handoff as H

    return H.por_que_vai_direto_a_pessoa(motivo, caso={"last_message_preview": "ok, obrigado",
                                                       "mensagens": [fala]})


@pytest.mark.parametrize("fala", FALAS_DO_SEGURADO_F7)
def test_W1_a_fala_do_segurado_do_red_team_vai_DIRETO_a_pessoa(fala):
    assert _decide("duvida do segurado", fala) != "", fala      # nas falas do segurado
    assert _decide(fala, "ok, obrigado") != "", fala            # e no motivo do handoff


@pytest.mark.parametrize("fala", CONTROLES)
def test_W1_CONTROLE_a_fala_comum_continua_com_a_segunda_chance(fala):
    assert _decide("duvida do segurado", fala) == "", fala


def test_W1_o_vocabulario_do_residencial_vale_SO_na_segunda_chance():
    """A mesma frase: o produto (resumo de sinistros) NÃO abre; a segunda chance vai a uma pessoa."""
    from app.services.claims_shadow import detectar_sinistro

    for fala in ("danos eletricos na geladeira", "alagou a casa toda", "caiu um raio e queimou a TV"):
        assert not detectar_sinistro(fala)[0], fala
        assert _decide("duvida do segurado", fala) == "é sinistro, e sinistro sempre vai para uma pessoa"


# =============================================================================
# W2 · o texto do MODELO nunca vai ao segurado
# =============================================================================
#: 📊 laudo P-N1: o conferente antigo deixava passar as três (3ª pessoa, navegação, segurado)
TEXTOS_DO_MODELO = ["Ele esta no local agora?", "Clique em Continuar para seguir?",
                    "O veiculo do segurado esta na garagem?"]


@pytest.mark.parametrize("texto", TEXTOS_DO_MODELO + ["Qual é a placa do seu carro?"])
@pytest.mark.parametrize("ref,tela", [(REF_HDI, TELA_PLACA), (REF_YELUM, TELA_LOCAL)])
def test_W2_a_pergunta_ao_segurado_e_sempre_a_composta_pelo_codigo(texto, ref, tela):
    s = sessao(ref, "guincho", slots={"veiculo_placa": PLACA, "titular_cpf": CPF})
    d = decidir(perguntar(texto), s, tela)
    assert d.acao == "PERGUNTAR_AO_SEGURADO", d
    assert d.valor == DT._pergunta_composta(tela, DT.opcoes_de_conteudo(tela), s), d.valor
    for pedaco in ("Ele esta", "Clique", "do segurado", "Qual é a placa do seu carro"):
        assert pedaco not in d.valor, d.valor
    frase = R.pergunta_para_o_segurado(s, "x", pergunta=d.valor)
    assert texto not in frase, frase
    # o que o modelo propôs fica no diário — e só lá
    assert d.valor_do_modelo == texto
    assert f"o modelo propôs: “{texto}”" in DT.motivo_no_diario(d)


def test_W2_O_FIO_destravar_inteiro_o_segurado_recebe_a_do_codigo_e_o_diario_guarda_a_do_modelo(dt):
    """`destravar` → o modelo (DUBLÊ na borda) pede para perguntar com texto em 3ª pessoa → a POLÍTICA
    → o diário (DUBLÊ na borda). A pergunta que sai é a da tela; a do modelo está na linha do diário."""
    s = sessao_travada()
    um = _Injetado(js(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO",
                      valor="Ele esta no local agora?", nota=90, motivo="falta o servico"))
    d = destravar(EMPRESA_A, s, TELA_SERVICOS, llm=DT.ModeloInjetado(um, "openai", "modelo-a"))
    assert d.acao == "PERGUNTAR_AO_SEGURADO", d
    assert "Ele esta" not in d.valor and "A seguradora está perguntando" in d.valor, d.valor
    [linha] = dt.diario.linhas
    assert "Ele esta" not in linha["valor"], linha["valor"]
    assert "o modelo propôs: “Ele esta no local agora?”" in linha["motivo"], linha["motivo"]
    assert len(linha["motivo"]) <= 300


def test_W2_CONTROLE_sem_proposta_de_pergunta_o_diario_nao_inventa_uma():
    d = DT.Destravamento(classe="nunca_sozinho", acao="PESSOA", motivo="m", proibicao="p", acao_do_modelo="RESPONDER",
                         valor_do_modelo="Encanador")
    assert DT.motivo_no_diario(d) == "m [p]"
    longo = DT.Destravamento(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO", motivo="x" * 400,
                             acao_do_modelo="PERGUNTAR_AO_SEGURADO", valor_do_modelo="Qual?")
    m = DT.motivo_no_diario(longo)
    assert len(m) == 300 and m.endswith("[o modelo propôs: “Qual?”]"), m


# =============================================================================
# W2b · a pergunta COMPOSTA leva a PERGUNTA da tela — nunca o menu cru
# =============================================================================
#: 📊 o defeito (Porto, 01/10): a tela sem "?" numa linha só virava, cortada aos 200 caracteres,
#: `A seguradora está perguntando: "Escolha a opção que melhor te atende: Para você Seguros e
#: serviços… Voltar Escolha a opção… Segur" — pode me responder?`. A tela é a REAL do acervo
#: (`cer-A-porto-019`, a mesma da costura do PONTO A); a forma numa linha só é a do defeito.
import json as _json
import re as _re
from pathlib import Path as _Path

_CORPUS = _Path(__file__).parent / "corpus" / "bancada" / "cerebro"


def _casos(arquivo: str):
    return [_json.loads(l) for l in (_CORPUS / arquivo).read_text(encoding="utf-8").splitlines() if l.strip()]


TELA_PORTO_MENU = next(c for c in _casos("casos.jsonl") if c["chave"] == "cer-A-porto-019")["entrada"]["tela"]
TELA_PORTO_MENU_NUMA_LINHA = " ".join(TELA_PORTO_MENU.split())
#: as telas REAIS (mascaradas) que chegam ao PERGUNTAR — direto ou pelo DEDUZIR rebaixado — no
#: `casos_d.jsonl` da bancada: 📊 56 telas de 10 seguradoras (01/10; a contagem é o teste abaixo).
TELAS_DO_PERGUNTAR = [(c["chave"], c["entrada"]["tela"], c["entrada"]["sessao"])
                      for c in _casos("casos_d.jsonl")
                      if c["oraculo"]["destravador"]["classe_esperada"] in ("perguntar_ao_segurado", "deduzir")]


def _n(s):
    from app.services.insurer_dispatch_service import _norm_text

    return " ".join(_norm_text(str(s or "")).split())


def _rotulos(tela):
    """Os rótulos do menu pelos PARSERS do produto (`opcoes_numeradas`, `_rotulos_da_tela`)."""
    from app.services import insurer_dispatch_service as IDS

    r = {_n(x).strip(" .:") for x in IDS._rotulos_da_tela(tela)}
    r |= {_n(x).strip(" .:") for _d, x in IDS.opcoes_numeradas(tela)}
    return {x for x in r if len(x) >= 3}


def _prosa(tela, rotulos):
    """O texto da tela fora das linhas de opção — onde a seguradora CITA uma opção na pergunta
    ("…numa via local ou rodovia?")."""
    return " ".join(_n(l) for l in tela.replace("*", "").splitlines()
                    if not _re.match(r"^\s*(?:Bot[ãa]o\s*\d|\d{1,2}\s*[-–.)])", l)
                    and _n(l).strip(" .:") not in rotulos)


def _defeitos_da_pergunta(tela_original: str, q: str) -> list:
    """O que a pergunta extraída NÃO pode ter (a régua do W2b)."""
    fora = []
    if not q:
        return ["vazia"]
    rotulos = _rotulos(tela_original)
    prosa = _prosa(tela_original, rotulos)
    if "*" in q or _re.search(r"(?:^|\s)_|_(?:\s|$)", q):
        fora.append("markdown")
    if len(q) > DT._TETO_DA_PERGUNTA + 1:
        fora.append(f"longa:{len(q)}")
    if _re.search(r"Bot[ãa]o\s*\d|(?:^|\s)\d{1,2}\s*[-–)]\s", q):
        fora.append("marca_de_menu")
    if _re.search(r"\b(?:voltar|sair|menu|encerrar)\b", _n(q)):
        fora.append("navegacao")
    for r in rotulos:
        if _re.search(rf"(?<!\w){_re.escape(r)}(?!\w)", _n(q)) and r not in prosa:
            fora.append(f"rotulo_dentro:{r[:24]}")
    base = _n(q.rstrip("…")).strip()
    m = _re.search(_re.escape(base) + r"(\w?)", _n(tela_original.replace("*", "").replace("_", " ")))
    if not m:
        fora.append("nao_e_da_tela")
    elif m.group(1):
        fora.append("cortada_no_meio_da_palavra")
    return fora


def test_W2b_o_acervo_do_PERGUNTAR_tem_15_telas_de_6_seguradoras_ou_mais():
    seguradoras = {chave.split("-")[3] for chave, _t, _s in TELAS_DO_PERGUNTAR}
    assert len(TELAS_DO_PERGUNTAR) >= 15 and len(seguradoras) >= 6, (len(TELAS_DO_PERGUNTAR), seguradoras)


@pytest.mark.parametrize("forma", ["como_chega", "numa_linha_so"])
@pytest.mark.parametrize("chave,tela,sessao_do_caso", TELAS_DO_PERGUNTAR + [
    ("cer-A-porto-019", TELA_PORTO_MENU, {"playbook_ref": "porto-auto-whatsapp@v1"})],
    ids=[c for c, _t, _s in TELAS_DO_PERGUNTAR] + ["cer-A-porto-019"])
def test_W2b_a_pergunta_composta_e_a_pergunta_da_tela_sem_o_menu(chave, tela, sessao_do_caso, forma):
    """Pelo MOTOR (`_pergunta_composta`, `opcoes_de_conteudo`) sobre a tela REAL: a frase da seguradora
    dentro das aspas não tem rótulo de opção, navegação, `*` nem termina cortada no meio da palavra —
    como a tela chega E numa linha só (a forma do defeito)."""
    entrada = tela if forma == "como_chega" else " ".join(tela.split())
    s = {"playbook_ref": sessao_do_caso.get("playbook_ref", ""), "subservice": sessao_do_caso.get("subservice", "")}
    composta = DT._pergunta_composta(entrada, DT.opcoes_de_conteudo(entrada), s)
    citada = _re.search(r"“([^”]*)”", composta)
    q = citada.group(1) if citada else ""
    assert q == DT._pergunta_da_tela(entrada), composta
    assert _defeitos_da_pergunta(tela, q) == [], (chave, forma, q)
    assert len(composta) <= 400 and "Voltar" not in composta, composta


#: As perguntas exatas — o que o segurado lê entre aspas (📊 telas reais mascaradas do acervo).
PERGUNTAS_ESPERADAS = {
    "des-D-sem_chute-hdi-011": "Agora, preciso que selecione abaixo a opção que corresponde com o seu problema",
    "des-D-sem_chute-bradesco-008": "Seu veículo se encontra em uma via local ou rodovia?",
    "des-D-sem_chute-porto-015": "Por favor, selecione o veículo.",
    "des-D-sem_chute-porto-014": "São quantos passageiros?",
    "des-D-cerebro-yelum-065": "Selecione abaixo para qual Seguradora deseja atendimento",
    "des-D-cerebro-azul-049": "Digite então um complemento.",
    "des-D-cerebro-yelum-045": "Qual o horário inicial permitido para entrada do prestador no condominio.",
    "des-D-ramo_indeterminado-allianz-004": "Você precisa de Assistência 24h para qual seguro?",
}


@pytest.mark.parametrize("chave", sorted(PERGUNTAS_ESPERADAS))
def test_W2b_a_pergunta_exata_de_telas_reais(chave):
    tela = next(t for c, t, _s in TELAS_DO_PERGUNTAR if c == chave)
    assert DT._pergunta_da_tela(tela) == PERGUNTAS_ESPERADAS[chave]


@pytest.mark.parametrize("tela", [TELA_PORTO_MENU, TELA_PORTO_MENU_NUMA_LINHA], ids=["como_chega", "numa_linha_so"])
def test_W2b_o_exemplo_da_PORTO_nao_copia_mais_o_menu(tela):
    s = {"playbook_ref": "porto-auto-whatsapp@v1"}
    composta = DT._pergunta_composta(tela, DT.opcoes_de_conteudo(tela), s)
    assert "“Escolha a opção que melhor te atende”" in composta, composta
    for pedaco in ("Para você", "Seguros e serviços", "Para empresas", "Voltar", "Segur”", ":”"):
        assert pedaco not in composta, (pedaco, composta)


def test_W2b_o_FIO_ao_segurado_chega_a_pergunta_e_as_opcoes_uma_por_linha():
    """A política (`decidir_destravamento`) → `pergunta_para_o_segurado` do roteador (o texto que SAI):
    a pergunta da tela entre aspas e as opções de CONTEÚDO separadas, numeradas, uma por linha."""
    s = sessao(REF_HDI, "guincho", slots={"veiculo_placa": PLACA, "titular_cpf": CPF})
    tela = next(t for c, t, _s in TELAS_DO_PERGUNTAR if c == "des-D-cerebro-hdi-061")
    d = decidir(perguntar("Ele prefere de manhã?"), s, tela)
    assert d.acao == "PERGUNTAR_AO_SEGURADO", d
    texto = R.pergunta_para_o_segurado(s, "x", opcoes=d.opcoes, pergunta=d.valor)
    assert "“Qual o melhor período?”" in texto and "Ele prefere" not in texto, texto
    linhas = texto.split("\n")
    assert linhas[-2:] == ["1 - Manhã (08h às 12h)", "2 - Tarde (13h às 18h)"], linhas
    assert "Voltar" not in texto, texto
