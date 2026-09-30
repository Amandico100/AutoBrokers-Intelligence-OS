"""SPEC-121 F3 · as etiquetas dizem a verdade — pelo MOTOR, sobre a tela REAL.

Cada regra nova do classificador (`scripts/padroes_de_servico.py`) é provada
chamando `servico_da_sessao` — o mesmo que o gerador do acervo chama — sobre as
telas que estão no acervo versionado (`tests/corpus/telas_reais/`, já
mascaradas), com as respostas que a corretora deu (📊 lidas em
`observed_events` em 29/09/2026; só rótulos de botão e textos curtos sem dado
pessoal). CLAUDE.md §9.4: o texto vem do acervo, nunca da imaginação.

🔴 Toda regra tem a sua LINHA DE CONTROLE (CLAUDE.md §9.2): a MESMA sessão com
UM fator a menos, e a etiqueta de antes volta. É isso que prova que o mérito é
do fator, e de mais nada.

```
regra                         sessão real        antes              depois
recarga de bateria (yelum)    86769bd5           socorro_mecanico   bateria
tela da chave (yelum)         56bd78f7           guincho            chaveiro
o aparelho pelo eletricista  834cc238           eletricista        (sem etiqueta) F3b
exploração (hdi)              13379965           eletricista        (sem etiqueta)
geladeira no texto (allianz)  213af941           (sem etiqueta)     eletrodomesticos
rótulo genérico (allianz)     b2946306+b2bf40e7  ?conserto resid.   maquina_de_lavar
```
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Optional, Tuple

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(AQUI), "scripts")
sys.path.insert(0, SCRIPTS)

import regua_motor as M                 # noqa: E402
import padroes_de_servico as PSV        # noqa: E402
import zonas_do_acervo as Z             # noqa: E402
import gerar_corpus_de_telas as G       # noqa: E402

PSV.ligar_resolvedor(M.canonical_subservice)

CORPUS = os.path.join(AQUI, "corpus", "telas_reais")


def _telas(arquivo: str, sid: str) -> List[str]:
    """As telas `in` de UMA sessão do acervo versionado, em ordem."""
    caminho = os.path.join(CORPUS, arquivo)
    if not os.path.exists(caminho):
        pytest.skip("acervo versionado ausente")
    ls = [json.loads(l) for l in open(caminho, encoding="utf-8") if l.strip()]
    ls = [l for l in ls if l["session_id"] == sid]
    ls.sort(key=lambda l: l.get("wa_timestamp") or "")
    assert ls, "a sessão %s sumiu de %s — o teste perdeu o texto real" % (sid, arquivo)
    return [l["text"] for l in ls]


def _tela_do_acervo(arquivo: str, padrao: str) -> str:
    """A primeira tela do acervo (qualquer sessão) que casa `padrao` — para telas
    de TRONCO, que são iguais em dezenas de sessões."""
    caminho = os.path.join(CORPUS, arquivo)
    if not os.path.exists(caminho):
        pytest.skip("acervo versionado ausente")
    for l in open(caminho, encoding="utf-8"):
        if l.strip():
            t = json.loads(l)["text"]
            if re.search(padrao, t, re.IGNORECASE):
                return t
    raise AssertionError("nenhuma tela %r em %s" % (padrao, arquivo))


def _depois(telas: List[str], padrao: str) -> Tuple[List[str], str, List[str]]:
    """Parte as telas na PRIMEIRA que casa `padrao`: (antes, ela, depois)."""
    for i, t in enumerate(telas):
        if re.search(padrao, t, re.IGNORECASE):
            return telas[:i], t, telas[i + 1:]
    raise AssertionError("tela %r não está na sessão" % padrao)


def _pares(seq) -> List[Tuple[str, str]]:
    return [(d, Z.norm_para_classificar(t)) for d, t in seq]


def _pb(seg: str, ramo: str):
    return M.get_playbook(M.resolve_playbook_ref(seg, ramo))


def _servico(seg: str, ramo: str, seq) -> Tuple[Optional[str], str]:
    return PSV.servico_da_sessao(seg, _pares(seq), _pb(seg, ramo))


# ─────────────────────────────────────────────────────────────────────────────
# 1 · RECARGA DE BATERIA — a Yelum assina "Socorro Mecânico"; o pedido é bateria
# ─────────────────────────────────────────────────────────────────────────────
def _sessao_da_recarga(resposta: str):
    telas = _telas("yelum-auto.jsonl", "86769bd5")
    antes, menu, depois = _depois(telas, r"pode me dizer o que aconteceu")
    return ([("in", t) for t in antes] + [("in", menu), ("out", resposta)]
            + [("in", t) for t in depois])


def test_recarga_de_bateria_da_yelum_e_bateria():
    seq = _sessao_da_recarga("Recarga de bateria")
    # a própria tela real assina Socorro Mecânico — é isso que a regra vence
    assert any("Socorro Mec" in t for d, t in seq if d == "in")
    assert _servico("yelum", "auto", seq) == ("bateria", "nivel-0-pedido")


def test_CONTROLE_a_mesma_sessao_com_pane_continua_pela_assinatura():
    """UM fator muda (a resposta): a assinatura da seguradora volta a decidir."""
    assert _servico("yelum", "auto", _sessao_da_recarga("Pane ou Defeito")) == (
        "socorro_mecanico", "nivel-1a-padrao-ouro")


def test_CONTROLE_um_guincho_de_pane_real_nao_muda():
    telas = _telas("yelum-auto.jsonl", "0a1a616e")
    antes, menu, depois = _depois(telas, r"pode me dizer o que aconteceu")
    seq = ([("in", t) for t in antes] + [("in", menu), ("out", "Pane ou Defeito")]
           + [("in", t) for t in depois])
    assert _servico("yelum", "auto", seq)[0] == "guincho"


# ─────────────────────────────────────────────────────────────────────────────
# 2 · A TELA DA CHAVE — a Yelum converte em guincho; o pedido é chaveiro
# ─────────────────────────────────────────────────────────────────────────────
def test_sessao_com_a_tela_da_chave_e_chaveiro_mesmo_terminando_em_guincho():
    telas = _telas("yelum-auto.jsonl", "56bd78f7")
    assert any(re.search(r"\*Servi[çc]o:\* Guincho", t) for t in telas), (
        "a sessão real termina num GUINCHO — é o que torna a regra necessária")
    antes, menu, depois = _depois(telas, r"pode me dizer o que aconteceu")
    seq = ([("in", t) for t in antes] + [("in", menu), ("out", "Problema com a chave")]
           + [("in", t) for t in depois])
    assert _servico("yelum", "auto", seq) == ("chaveiro", "nivel-0-pedido")


def test_CONTROLE_sem_a_tela_da_chave_a_mesma_sessao_e_guincho():
    telas = [t for t in _telas("yelum-auto.jsonl", "56bd78f7")
             if not re.search(r"o que aconteceu com a chave", t, re.IGNORECASE)]
    assert _servico("yelum", "auto", [("in", t) for t in telas])[0] == "guincho"


# ─────────────────────────────────────────────────────────────────────────────
# 3 · O APARELHO VENCE O PROFISSIONAL — hdi 834cc238, fogão pedido como eletricista
# ─────────────────────────────────────────────────────────────────────────────
def _sessao_do_fogao(com_o_fogao: bool):
    telas = _telas("hdi-residencial.jsonl", "834cc238")
    antes, menu, depois = _depois(telas, r"qual o servi[çc]o que voc[êe] precisa")
    seq = ([("in", t) for t in antes] + [("in", menu), ("out", "Eletricista")]
           + [("in", t) for t in depois])
    if com_o_fogao:
        # 📊 a frase real da corretora ao analista, observed_events 29/09
        seq.append(("out", "ao conserto do fogao"))
    return seq


def test_o_fogao_pedido_pelo_menu_do_eletricista_fica_sem_etiqueta():
    """🔴 SPEC-121 F3b: nem `eletricista` (o pedido é um fogão) nem
    `eletrodomesticos` (as telas são do caminho do ELETRICISTA, que o corredor
    de eletrodoméstico nunca vê — 📊 3 órfãs falsas na régua da F3). A F3
    etiquetava `eletrodomesticos`; a lição migra: o aparelho continua vencendo
    o menu, e o que ele decide agora é tirar a etiqueta (decisão do gerente,
    nota 65 × 55)."""
    assert _servico("hdi", "residencial", _sessao_do_fogao(True)) == (
        None, "nivel-1b-resposta+aparelho")


def test_o_motivo_do_aparelho_pelo_eletricista_e_escrito_no_indice():
    pares = _pares(_sessao_do_fogao(True))
    nivel = _servico("hdi", "residencial", _sessao_do_fogao(True))[1]
    assert G.motivo_sem_etiqueta("hdi", pares, [], [], nivel=nivel) == G.MOTIVO_APARELHO
    # CONTROLE: o mesmo nível sem o sufixo não dá esse motivo
    assert G.motivo_sem_etiqueta("hdi", pares, [], [], nivel="nivel-1b-resposta")         != G.MOTIVO_APARELHO


def test_CONTROLE_sem_o_aparelho_a_mesma_sessao_continua_eletricista():
    assert _servico("hdi", "residencial", _sessao_do_fogao(False)) == (
        "eletricista", "nivel-1b-resposta")


# ─────────────────────────────────────────────────────────────────────────────
# 4 · EXPLORAÇÃO — hdi 13379965: três serviços no mesmo menu e SAIR
# ─────────────────────────────────────────────────────────────────────────────
def _sessao_da_exploracao(com_sair: bool):
    telas = _telas("hdi-residencial.jsonl", "13379965")
    menu = next(t for t in telas if re.search(r"qual [ée] o servi[çc]o que voc[êe] precisa", t,
                                              re.IGNORECASE))
    vaz1, vaz2 = [t for t in telas if re.search(r"qual desses itens est[áa] com vazamento", t,
                                                 re.IGNORECASE)][:2]
    reparo = next(t for t in telas if re.search(r"qual desses itens precisa de reparo", t,
                                                re.IGNORECASE))
    # 📊 as respostas reais, na ordem, observed_events 29/09
    seq = [("in", menu), ("out", "Eletricista"), ("out", "voltar"),
           ("in", menu), ("out", "Encanador"), ("in", vaz1), ("out", "Mais opções"),
           ("in", vaz2), ("out", "Voltar"), ("in", menu), ("out", "Linha branca"),
           ("in", reparo), ("out", "Voltar")]
    if com_sair:
        seq.append(("out", "SAIR"))
    return seq


def test_exploracao_de_tres_servicos_e_sair_fica_sem_etiqueta():
    assert _servico("hdi", "residencial", _sessao_da_exploracao(True)) == (
        None, "nivel-1b-exploracao")


def test_CONTROLE_sem_o_sair_a_primeira_escolha_decide():
    assert _servico("hdi", "residencial", _sessao_da_exploracao(False)) == (
        "eletricista", "nivel-1b-resposta")


def test_o_motivo_da_exploracao_e_escrito_no_indice():
    pares = _pares(_sessao_da_exploracao(True))
    assert G.motivo_sem_etiqueta("hdi", pares, [], []) == G.MOTIVO_EXPLORACAO


# ─────────────────────────────────────────────────────────────────────────────
# 5 · A GELADEIRA NO TEXTO — allianz 213af941 (fuga: 3 → 7 → especialista)
# ─────────────────────────────────────────────────────────────────────────────
def _caminho_da_fuga():
    """O caminho REAL de 213af941 (📊 observed_events 29/09): tipo de serviço →
    `3` → "qual desses serviços" → `7` → transferência. As telas são de tronco e
    vêm do acervo (a sessão em si não entra no acervo de hoje: sem desfecho na
    zona da URA e acima do piso)."""
    tipo = _tela_do_acervo("allianz-residencial.jsonl", r"vamos l[áa]! informe o tipo de servi")
    outros = _tela_do_acervo("allianz-residencial.jsonl", r"qual desses servi[çc]os, voc[êe] precisa")
    fronteira = _tela_do_acervo("allianz-residencial.jsonl", r"vou transferir seu caso para um especialista")
    return [("in", tipo), ("out", "3"), ("in", outros), ("out", "7"), ("in", fronteira)]


def test_geladeira_nomeada_pela_corretora_e_eletrodomestico():
    # 📊 a frase real da corretora ao especialista, 213af941
    seq = _caminho_da_fuga() + [("out", "COnserto da geladeira")]
    assert _servico("allianz", "residencial", seq) == ("eletrodomesticos", "nivel-2-texto")


def test_CONTROLE_sem_a_geladeira_a_sessao_de_fuga_continua_sem_etiqueta():
    assert _servico("allianz", "residencial", _caminho_da_fuga())[0] is None


# ─────────────────────────────────────────────────────────────────────────────
# 6 · "CONSERTO RESIDENCIAL" — o nome do PACOTE não decide; o item decide
# ─────────────────────────────────────────────────────────────────────────────
# 📊 O resumo de `b2946306` (acervo de 29/09, mascarado; protocolo FICTÍCIO).
# 🔴 SPEC-121 F3b: ele é o RESUMO de um pedido que JÁ EXISTIA ("Ver detalhes"), e
#    consulta saiu do acervo (`Z.consulta_de_pedido_existente`). O texto fica
#    escrito aqui — e as 8 ocorrências dele no acervo de 29/09 eram TODAS de
#    consulta (`scratchpad/f3b/protelas.py`). A regra do rótulo genérico
#    continua valendo para o classificador; no acervo de hoje, a consulta nem
#    chega até ele.
RESUMO_GENERICO = ("*RESUMO*\n\n*Protocolo 50000003\n*Serviço:* *CONSERTO RESIDENCIAL*;\n"
                   "*Endereço:* {ENDERECO}\n*Tipo solicitação:* Agendado\n"
                   "*Agendamento para:* Sexta-feira, {DATA}\n*Período:* 13:00 às 18:00 (tarde)")


def _resumo_generico() -> str:
    return RESUMO_GENERICO


def test_conserto_residencial_sem_item_continua_achado_declarado():
    """📊 29/09: as 5 sessões com este resumo NÃO nomeiam o item em lugar nenhum
    (`scratchpad/f3` · busca por aparelho/serviço em `in` e `out`). Sem item, o
    rótulo volta como "?conserto residencial" — achado, não silêncio."""
    seq = [("in", _resumo_generico())]
    assert _servico("allianz", "residencial", seq) == (
        "?conserto residencial", "nivel-1a-rotulo-desconhecido")


def test_conserto_residencial_se_resolve_pelo_item_de_um_resumo_posterior():
    item = next(t for t in _telas("allianz-residencial.jsonl", "7ac3c101")
                if re.search(r"(?m)^\*?Problema:?\*?.*m[áa]quina de lavar", t, re.IGNORECASE)
                or re.search(r"Servi[çc]o:\*? *\*?conserto de eletrodom", t, re.IGNORECASE))
    # o GENÉRICO vem primeiro no tempo — antes da F3 era ele que decidia
    seq = [("in", _resumo_generico()), ("in", item)]
    assert _servico("allianz", "residencial", seq)[0] == "maquina_de_lavar"


# ─────────────────────────────────────────────────────────────────────────────
# 7 · TELA VAZIA NÃO DERRUBA A MEDIÇÃO DO FIM (investigação eletro, "riscos")
# ─────────────────────────────────────────────────────────────────────────────
def test_tela_vazia_nao_derruba_sessao_chegou_ao_fim():
    pb = _pb("yelum", "auto")
    telas = _telas("yelum-auto.jsonl", "86769bd5")
    assert G.sessao_chegou_ao_fim(pb, ["", "   "] + telas) is True
    assert G.sessao_chegou_ao_fim(pb, ["", "\n"]) is False


def test_CONTROLE_o_motor_ainda_lanca_com_tela_vazia():
    """Se este controle ficar vermelho, o motor passou a se proteger sozinho e a
    guarda do script pode sair — é verdade que migra (CLAUDE.md §9.3)."""
    with pytest.raises(IndexError):
        M.extract_capture_anchors(_pb("yelum", "auto"), "")


# ─────────────────────────────────────────────────────────────────────────────
# 8 · A APRESENTAÇÃO DA FUNCIONÁRIA DA SEGURADORA É MASCARADA (P-120-12)
# ─────────────────────────────────────────────────────────────────────────────
import higiene_do_corpus as H           # noqa: E402

# 📊 as FORMAS reais (acervo de 28/09: porto 4830574a, yelum 9e562ae5/c0c3c694),
#    com um nome FICTÍCIO no lugar do nome real — o teste não carrega pessoa.
APRESENTACOES_DE_PESSOA = [
    "Olá! 😊 Aqui é a Fulana. Sou consultora de relacionamento da Porto.",
    "Olá!  Meu nome é *_Beltrana_* e vou iniciar seu atendimento.",
]
# 📊 as FORMAS reais do ROBÔ (hdi 2bdccc04, zurich 4118ba36, mapfre f6f2ec11)
APRESENTACOES_DO_ROBO = [
    "Olá, {NOME}, sou a Hana, assistente virtual da HDI Seguros.",
    "Tudo bem? Eu sou a Laiz, assistente virtual da Zurich.",
    "Olá, aqui é a Maite, assistente virtual da *MAPFRE*.",
]


@pytest.mark.parametrize("tela", APRESENTACOES_DE_PESSOA)
def test_a_apresentacao_da_pessoa_sai_mascarada_e_o_guarda_ve(tela):
    assert H.auditar_pii(tela), "o guarda não viu o nome na apresentação"
    limpo, marcas = H.higienizar({}, tela)
    assert marcas["apresentacao_mascarada"] and "{NOME}" in limpo
    assert not [a for a in H.auditar_pii(limpo) if a.startswith("NOME_NA_APRESENTACAO")]


@pytest.mark.parametrize("tela", APRESENTACOES_DO_ROBO)
def test_CONTROLE_a_persona_do_robo_nao_e_pessoa(tela):
    limpo, marcas = H.higienizar({}, tela)
    assert not marcas["apresentacao_mascarada"]
    assert not [a for a in H.auditar_pii(limpo) if a.startswith("NOME_NA_APRESENTACAO")]


# ─────────────────────────────────────────────────────────────────────────────
# 9 · O ENDEREÇO QUE O `templatize` DEIXAVA PELA METADE
# ─────────────────────────────────────────────────────────────────────────────
# 📊 as FORMAS reais do resíduo (acervo de 28/09: 50 linhas em 50 sessões —
#    allianz, bradesco, hdi, porto, yelum), com letras e números FICTÍCIOS.
ENDERECOS_COM_SOBRA = [
    "*1 -* AV #### ##XXXX DE # #####, 123 - ####XXXXX#### - SC",
    "*1 -* R. {ENDERECO}ES Xxxxx###, 456 - Xxxxx {NUM} BL A - ####XXXXX#### - SC",
    "*3 -* AV ### ######TT Xxxxx 12# #### ###,  - ####Xxxxx#### - SC",
    "Rua {ENDERECO} - Xxxxxx, Xxxxx Xxxxx - SP",
    "*Endereço:* R. {ENDERECO} - Xxxxxx - SC",
    "*1 -* R. {ENDERECO}XXXXX#### - SC",
]
# 📊 as telas REAIS que citam logradouro sem ser endereço de ninguém
NAO_SAO_ENDERECO = [
    "Informe o nome do logradouro (rua, avenida, rodovia, etc.)  _(Ex. Avenida Brasil)_.",
    "Nesse caso vou precisar que me informe o *endereço completo*, seguindo o exemplo: "
    "Rua xxx, numero xx, bairro xxxx, cidade xxxx, estado xx.*",
    "Valor da franquia: R$ 150,00 - SC",
]


@pytest.mark.parametrize("tela", ENDERECOS_COM_SOBRA)
def test_a_sobra_do_endereco_sai_mascarada_e_o_guarda_ve(tela):
    """A forma é a que SAI do `templatize` — é sobre ela que a regra age."""
    assert [a for a in H.auditar_pii(tela) if a.startswith("ENDERECO_POSTAL")]
    limpo, houve = H._mascarar_endereco(tela)
    assert houve and not re.search(r"\d{2,}|BL A|Xxx|XXX", limpo)
    assert not [a for a in H.auditar_pii(limpo) if a.startswith("ENDERECO_POSTAL")]
    # e a PORTA ÚNICA (`higienizar`) aplica a regra — não basta a função existir
    pela_porta, _m = H.higienizar({}, tela)
    assert not [a for a in H.auditar_pii(pela_porta) if a.startswith("ENDERECO_POSTAL")]


@pytest.mark.parametrize("tela", NAO_SAO_ENDERECO)
def test_CONTROLE_tela_que_cita_logradouro_fica_intacta(tela):
    assert H._mascarar_endereco(tela) == (tela, False)
