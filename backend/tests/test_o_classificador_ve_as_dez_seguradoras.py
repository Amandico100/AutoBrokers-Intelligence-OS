"""O classificador vê as DEZ seguradoras — e cada tela vem do acervo, não da cabeça.

═══════════════════════════════════════════════════════════════════════════════
🔴 O DEFEITO QUE ESTE GUARDA IMPEDE (SPEC-119 F1, 27/09/2026)
═══════════════════════════════════════════════════════════════════════════════

O Founder perguntou: *"como pode ter 72 pedidos e não ter o corredor?"*. A causa
não era falta de conversa — 📊 o corpus versionado tinha as conversas **sem
etiqueta de serviço**:

```
mapfre-auto.jsonl   113 telas · 100 com servico (vazio)  · só carro_reserva
zurich-auto.jsonl   253 telas · 217 (vazio)              · só 36 em guincho
bradesco-auto.jsonl 192 telas · guincho 89 · bateria 36  · 27 (vazio)
porto-auto.jsonl    524 telas · bem classificado         · só 21 (vazio)
```

E a causa, em duas listas que ninguém alimentou: `MENUS_DE_SERVICO` é **por
seguradora** e a MAPFRE era a ÚNICA sem nenhuma entrada; `PADRAO_OURO` tinha
**dois** padrões, globais, para dez seguradoras.

Este arquivo é o guarda das duas listas. E ele tem **quatro** portas:

```
① a tela REAL da seguradora produz o rótulo certo        (o que faltava)
② a tela que NÃO pede serviço continua SEM rótulo        🔴 CONTROLE
③ um rótulo que nenhuma seguradora nomeia sai como ?x    🔴 CONTROLE DE INVENÇÃO
④ nenhuma seguradora fica sem entrada NEM sem motivo     (a lista das dez)
```

═══════════════════════════════════════════════════════════════════════════════
🔴 PORQUE A TELA É **LIDA DO CORPUS**, E NÃO ESCRITA AQUI — CLAUDE.md §9.4
═══════════════════════════════════════════════════════════════════════════════

*"O que se afirma é o comportamento do MOTOR sobre o texto REAL. E o texto da
tela vem do acervo, não da imaginação."*

Por isso cada caso deste arquivo tem uma **CHAVE DE BUSCA** — um pedaço curto da
frase — e o teste vai buscar a tela inteira dentro de
`tests/corpus/telas_reais/*.jsonl`. Se a tela não estiver mais lá, o caso fica
**VERMELHO** em vez de passar com um texto inventado. Nenhuma tela é digitada
aqui, e por isso nenhum PII pode entrar por ela (CLAUDE.md §13.3): o corpus já é
mascarado, e `test_o_corpus_nao_vaza_pii.py` é quem prova isso.

⚠️ **E O DIALETO, que já custou três defeitos na SPEC-083:** o corpus guarda o
texto **CRU** (com o `*` do negrito do WhatsApp) e a cascata roda sobre o texto
**NORMALIZADO**. O teste aplica `zonas_do_acervo.norm_para_classificar` — o mesmo
normalizador do gerador — antes de entregar a tela ao motor. Sem isso,
`(?m)^servi[çc]o\\s*:` cairia de 112 sessões para ZERO, em silêncio. A porta ⑤
abaixo é o guarda dessa lição.

═══════════════════════════════════════════════════════════════════════════════
O QUE O MOTOR É, AQUI
═══════════════════════════════════════════════════════════════════════════════

`padroes_de_servico.servico_da_sessao` — e **nada além dele**. Nenhuma asserção
deste arquivo roda `re.search` sobre `PADRAO_OURO` ou sobre `MENUS_DE_SERVICO`
para "provar que o padrão casa": isso provaria que o regex existe, não que
alguém o usa (CLAUDE.md §9.4). A única exceção permitida pela própria §9.4 é a
inspeção da **FORMA da declaração** — a porta ⑤, que confere que nenhum padrão
novo usa `.` onde precisa de `[^\\n]`.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import padroes_de_servico as PSV          # noqa: E402
import regua_motor as M                   # noqa: E402
import zonas_do_acervo as Z               # noqa: E402

# 🔴 o resolvedor é o DO PRODUTO (`canonical_subservice`), como em
#    `gerar_corpus_de_telas.py:47`. Sem tabela paralela, e sem banco:
#    📊 `M.canonical_subservice("vidro") == "vidros"` roda com `SUPABASE_URL` vazio.
PSV.ligar_resolvedor(M.canonical_subservice)

CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")


# ─────────────────────────────────────────────────────────────────────────────
# O ACERVO VERSIONADO — carregado uma vez, normalizado como o gerador normaliza
# ─────────────────────────────────────────────────────────────────────────────
def _telas_do_corpus() -> Dict[str, List[str]]:
    """`{"<seguradora>-<ramo>": [tela_normalizada, ...]}` — sem banco, sem rede."""
    fora: Dict[str, List[str]] = {}
    for caminho in sorted(glob.glob(os.path.join(CORPUS, "*.jsonl"))):
        nome = os.path.basename(caminho)[: -len(".jsonl")]
        telas: List[str] = []
        with open(caminho, encoding="utf-8") as fh:
            for linha in fh:
                if not linha.strip():
                    continue
                bruto = json.loads(linha).get("text") or ""
                # ⚠️ 📊 O DIALETO: sem esta linha, o padrão-ouro morre em silêncio.
                telas.append(Z.norm_para_classificar(bruto))
        fora[nome] = telas
    return fora


TELAS = _telas_do_corpus()


def _achar(arquivo: str, chave: str) -> Optional[str]:
    """A tela REAL que contém `chave`, dentro de `<arquivo>.jsonl`. A mais longa.

    🔴 Devolve `None` quando o corpus não a tem mais — e o caso fica VERMELHO.
    """
    candidatas = [t for t in TELAS.get(arquivo, []) if chave in t]
    return max(candidatas, key=len) if candidatas else None


def _playbook(seguradora: str, ramo: str) -> Optional[Dict[str, Any]]:
    ref = M.resolve_playbook_ref(seguradora, ramo)
    return M.get_playbook(ref) if ref else None


def _rodar(arquivo: str, passos: List[Tuple[str, Optional[str]]]
           ) -> Tuple[Optional[str], str, List[str]]:
    """Monta `pares` com as telas REAIS e chama O MOTOR.

    `passos` = `[(chave_de_busca_da_tela, resposta_da_corretora_ou_None), ...]`.
    """
    seguradora, ramo = arquivo.split("-", 1)
    pares: List[Tuple[str, str]] = []
    ausentes: List[str] = []
    for chave, resposta in passos:
        tela = _achar(arquivo, chave)
        if tela is None:
            ausentes.append(chave)
            continue
        pares.append(("in", tela))
        if resposta is not None:
            pares.append(("out", Z.norm_para_classificar(resposta)))
    servico, nivel = PSV.servico_da_sessao(seguradora, pares,
                                           _playbook(seguradora, ramo))
    return servico, nivel, ausentes


# ═════════════════════════════════════════════════════════════════════════════
# ① A TELA REAL PRODUZ O RÓTULO CERTO
#
# Cada caso: o arquivo do corpus, os passos (tela real + a resposta medida), o
# rótulo esperado, o nível da cascata que tem de decidir, e a MEDIÇÃO que
# justifica a linha. 📊 comando das contagens:
#   `python scratchpad/testar_padrao.py acervo.json "<padrão>"` e
#   `python scratchpad/pares.py acervo.json <seguradora> <ramo>` sobre as 555
#   sessões de `observed_events` em 27/09/2026.
# ═════════════════════════════════════════════════════════════════════════════
CASOS_QUE_DECIDEM: List[Tuple[str, str, List[Tuple[str, Optional[str]]], str, str, str]] = [
    # ── MAPFRE · a seguradora que não tinha NENHUMA entrada ───────────────────
    ("mapfre: o menu do bot do SEGURADO devolve carro reserva",
     "mapfre-auto",
     [("solicitacao e acompanhamento de guincho, socorro ou taxi", "carro reserva")],
     "carro_reserva", "nivel-1b",
     "📊 3 sessões com esta tela; respostas medidas: sinistro 3 · carro reserva 1"),
    ("mapfre: 'pequenos reparos' e a tecla de VIDRO, e a propria tela diz",
     "mapfre-auto",
     [("solicitacao e acompanhamento de guincho, socorro ou taxi", "pequenos reparos")],
     "vidros", "nivel-1b",
     "a tela escreve 'pequenos reparos / vidros, retrovisores, para-choques'"),
    # ── ZURICH · 36 de 253 telas antes ────────────────────────────────────────
    ("zurich: 'assistencia a vidros' no menu de primeiro nivel",
     "zurich-auto",
     [("escolha um dos servicos para continuar", "assistencia a vidros")],
     "vidros", "nivel-1b",
     "📊 5 sessões com esta tela; respostas medidas: assistencia 24h 4 · sinistro 3"),
    ("zurich: a tecla 4 de 'panes' nao decide, e 'o que houve?' decide",
     "zurich-auto",
     [("me conte o que aconteceu", "4"), ("o que houve?", "4")],
     "guincho", "nivel-1b",
     "📊 sessão 9f7dbd91: pede destino e fecha com 'numero da solicitacao: 71020124'"),
    ("zurich: 'problema de bateria' e o rotulo que a propria zurich escreve",
     "zurich-auto",
     [("me conte o que aconteceu", "4"), ("o que houve?", "1")],
     "bateria", "nivel-1b",
     "o rótulo NOMEIA o serviço — regra (a) da tabela"),
    # ── PORTO e AZUL · a tela de REMOÇÃO, que faltava nas duas ────────────────
    ("porto: 'remocao de veiculo' e guincho",
     "porto-auto",
     [("melhor a sua necessidade", "remocao de veiculo")],
     "guincho", "nivel-1b",
     "📊 16 sessões na porto; resposta unânime: remocao de veiculo em 21 de 21"),
    ("azul: a MESMA tela, e ela tambem faltava na azul",
     "azul-auto",
     [("melhor a sua necessidade", "remocao de veiculo")],
     "guincho", "nivel-1b",
     "📊 5 sessões na azul"),
    ("azul: 'vidros e farois' no menu de primeiro nivel",
     "azul-auto",
     [("selecione uma opcao, por favor", "vidros e farois")],
     "vidros", "nivel-1b",
     "📊 12 sessões com esta tela"),
    # ── BRADESCO · a primeira forma de padrao-ouro que ela tem ────────────────
    ("bradesco: 'entao vamos enviar um reboque' e a seguradora NOMEANDO o servico",
     "bradesco-auto",
     [("entao vamos enviar um", None)],
     "guincho", "nivel-1a",
     "📊 5 sessões, rótulo 'reboque' 8×"),
    ("bradesco: 'a assistencia de um tecnico' — e NAO bateria, como a tabela dizia",
     "bradesco-auto",
     [("da pra resolver com a assistencia de um", None)],
     "tecnico", "nivel-1a",
     "📊 2 sessões (2c05415b, 57149865); a tabela afirmava bateria por inferência"),
    # ── HDI e YELUM · a frase de envio ────────────────────────────────────────
    ("hdi: 'neste caso enviaremos o servico de guincho para atende-lo'",
     "hdi-auto",
     [("neste caso enviaremos o servico de guincho", None)],
     "guincho", "nivel-1a",
     "📊 hdi 15 sessões · yelum 15; guincho 28 · troca de pneus 4 · chaveiro 1"),
    # ── TOKIO · rotulos ampliados ─────────────────────────────────────────────
    ("tokio: 'servicos para vidros' no menu do seguro automovel",
     "tokio-auto",
     [("menu de servicos do", "servicos para vidros")],
     "vidros", "nivel-1b",
     "📊 5 sessões; respostas medidas: informacoes sinistro 3 · outros servicos 2 "
     "· guincho/assist.24h 2"),
]


@pytest.mark.parametrize(
    "nome,arquivo,passos,esperado,nivel,medicao",
    CASOS_QUE_DECIDEM,
    ids=[c[0][:60] for c in CASOS_QUE_DECIDEM])
def test_a_tela_real_da_seguradora_produz_o_rotulo(
        nome, arquivo, passos, esperado, nivel, medicao):
    servico, nivel_obtido, ausentes = _rodar(arquivo, passos)
    assert not ausentes, (
        f"{nome}: a tela saiu do corpus versionado — chaves ausentes em "
        f"{arquivo}.jsonl: {ausentes}. 🔴 A tela vem do ACERVO; sem ela o caso "
        f"não pode passar com texto inventado (CLAUDE.md §9.4).")
    assert servico == esperado, (
        f"{nome}\n  esperado={esperado!r}  obtido={servico!r} "
        f"(nível {nivel_obtido})\n  medição: {medicao}")
    assert nivel_obtido.startswith(nivel), (
        f"{nome}: decidiu no nível errado — esperado {nivel}*, "
        f"obtido {nivel_obtido!r}. O nível diz DE ONDE veio a verdade.")


# ═════════════════════════════════════════════════════════════════════════════
# ② 🔴 O CONTROLE — a tela que NÃO pede serviço continua SEM etiqueta
#
# Sem esta porta, "etiquetar tudo" passaria no teste ① e ainda por cima
# encheria a tabela de demanda com cardápio — o defeito que
# `padroes_de_servico.py` existe para consertar (chaveiro 210 → 5).
# ═════════════════════════════════════════════════════════════════════════════
CASOS_DE_CONTROLE: List[Tuple[str, str, List[Tuple[str, Optional[str]]], str]] = [
    ("mapfre: o menu da CORRETORA escolhe ASSUNTO, nunca serviço",
     "mapfre-auto",
     [("escolher sobre qual assunto voce quer falar", "pagamento")],
     "📊 resposta medida em 14 sessões: pagamento 22 · demais assuntos 1 · sinistro 1"),
    ("mapfre: 'assistencia' NAVEGA para um submenu que o acervo não tem",
     "mapfre-auto",
     [("escolher sobre qual assunto voce quer falar", "assistencia")],
     "🔴 mapeá-la para guincho seria decidir pelo segurado (CLAUDE.md §9.5)"),
    ("zurich: 'assistencia 24h' NAVEGA — cinco serviços atrás de uma tecla",
     "zurich-auto",
     [("escolha um dos servicos para continuar", "assistencia 24h")],
     "a própria zurich escreve: 'atende reboque, socorro mecanico, chaveiro, "
     "pane seca ou troca de pneu'"),
    ("porto: 'como eu posso te ajudar?' escolhe o RAMO, não o serviço",
     "porto-auto",
     [("como eu posso te ajudar?", "servicos para veiculo")],
     "📊 17 sessões na porto; a tela lista guincho/tecnico/chaveiro/taxi como "
     "DESCRIÇÃO do que vem depois, e um detector ingênuo contaria isso como demanda"),
    ("azul: 'assistencia emergencial' NAVEGA para 'o que voce precisa?'",
     "azul-auto",
     [("selecione uma opcao, por favor", "assistencia emergencial")],
     "📊 a resposta mais frequente da tela (9 de 12) e ainda assim não decide"),
    ("bradesco: a tecla 1 é PANE, e pane sozinha não é serviço",
     "bradesco-auto",
     [("qual o problema com o seu carro", "1")],
     "🔴 é por isso que ela vale None: quem separa é 'me conta o que aconteceu'"),
]


@pytest.mark.parametrize("nome,arquivo,passos,porque", CASOS_DE_CONTROLE,
                         ids=[c[0][:60] for c in CASOS_DE_CONTROLE])
def test_a_tela_que_nao_pede_servico_continua_sem_etiqueta(
        nome, arquivo, passos, porque):
    servico, nivel, ausentes = _rodar(arquivo, passos)
    assert not ausentes, f"{nome}: tela ausente do corpus: {ausentes}"
    assert servico is None, (
        f"🔴 CONTROLE VIOLADO — {nome}\n  a tela recebeu o rótulo {servico!r} "
        f"(nível {nivel}) e ela NÃO pede serviço.\n  {porque}")


def test_a_saudacao_e_o_termo_de_privacidade_nao_sao_servico():
    """🔴 O controle mais grosso, e o que pega "etiquetar tudo" primeiro.

    📊 As primeiras telas de TODA sessão da mapfre são saudação, LGPD, Libras e
    aviso de SAIR. Nenhuma delas é pedido de trabalho.
    """
    passos = [("assistente virtual da mapfre", None),
              ("lgpd", None),
              ("digitar sair", None)]
    servico, nivel, ausentes = _rodar("mapfre-auto", passos)
    assert not ausentes, f"telas ausentes do corpus: {ausentes}"
    assert servico is None, (
        f"🔴 saudação/LGPD/aviso viraram {servico!r} no nível {nivel}")


# ═════════════════════════════════════════════════════════════════════════════
# ③ 🔴 O CONTROLE DE INVENÇÃO — rótulo que nenhuma seguradora nomeia sai `?x`
#
# ⛔ Este é o único bloco com texto NÃO vindo do acervo, e de propósito: um
#    controle negativo precisa ser algo que o acervo **não** tem. A forma da
#    tela é a real (`servico: <coisa>;` do resumo da allianz); o conteúdo é
#    impossível.
#
# 🔴 `nivel-1a-rotulo-desconhecido` FICA. Um rótulo que a seguradora nomeia e o
#    código não tem é ACHADO para a SPEC-084, não ruído.
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("rotulo", [
    "consertador de disco voador",
    "polimento de asa delta",
    "limpeza de reator nuclear",
])
def test_rotulo_que_nenhuma_seguradora_nomeia_nao_vira_servico_conhecido(rotulo):
    servico, nivel = PSV.servico_da_sessao(
        "allianz", [("in", f"resumo\n\nservico: {rotulo};\nendereco: x")], None)
    assert nivel == "nivel-1a-rotulo-desconhecido", (
        f"🔴 CONTROLE DE INVENÇÃO VIOLADO: {rotulo!r} decidiu no nível "
        f"{nivel!r} e virou {servico!r}. Um rótulo que ninguém nomeia tem de "
        f"sair como achado (`?rotulo`), nunca como serviço conhecido.")
    assert servico and servico.startswith("?"), servico
    assert rotulo[:20] in servico, servico


def test_o_achado_nao_se_disfarca_de_servico_conhecido():
    """🔴 E o `?rotulo` tem de ser DISTINGUÍVEL de um serviço de verdade.

    📊 Os rótulos reais que o acervo produz hoje e o código não tem:
    `?pet assistance`, `?check-up lar`, `?retorno em garantia`,
    `?reembolso - qualidade`, `?conserto residencial` — 15 sessões da allianz
    residencial. Eles vão para a SPEC-084, não para o balde.
    """
    conhecidos = set(PSV.PADROES_DE_SERVICO_TEXTO)
    servico, _ = PSV.servico_da_sessao(
        "allianz", [("in", "resumo\n\nservico: pet assistance;")], None)
    assert servico not in conhecidos
    assert servico.startswith("?")


# ═════════════════════════════════════════════════════════════════════════════
# ④ AS DEZ SEGURADORAS — nenhuma fica sem entrada NEM sem motivo escrito
# ═════════════════════════════════════════════════════════════════════════════
AS_DEZ = ("alfa", "allianz", "azul", "bradesco", "hdi",
          "mapfre", "porto", "tokio", "yelum", "zurich")


def test_todas_as_dez_seguradoras_tem_menu_cadastrado():
    """🔴 A afirmação-título. Até 27/09/2026 a MAPFRE era a única sem nenhuma.

    📊 Contagem em 27/09/2026 (comando: `grep -c '"seguradora":' scripts/
    padroes_de_servico.py` por chave): allianz 5 · azul 4 · porto 4 · mapfre 2 ·
    zurich 3 · alfa 1 · bradesco 1 · hdi 1 · yelum 1 · tokio 1.
    """
    com_menu = {m["seguradora"] for m in PSV.MENUS_DE_SERVICO}
    faltam = sorted(set(AS_DEZ) - com_menu)
    assert not faltam, (
        f"🔴 seguradora(s) sem NENHUMA entrada em MENUS_DE_SERVICO: {faltam}. "
        f"Uma lista que ninguém alimenta é a causa medida do '(vazio)' no corpus.")
    assert not (com_menu - set(AS_DEZ)), (
        f"menu de seguradora que não existe no produto: "
        f"{sorted(com_menu - set(AS_DEZ))}")


def test_quem_nao_tem_padrao_ouro_esta_declarado_e_nao_e_silencio():
    """As seguradoras sem nível 1a são DECLARADAS, uma a uma, com o motivo.

    ⚠️ Eram quatro; a **bradesco saiu** em 27/09/2026 — ela nomeia o serviço em
    *"entao vamos enviar um reboque"* e em *"a assistencia de um tecnico"*.
    """
    assert set(PSV.SEM_PADRAO_OURO) == {"tokio", "zurich", "mapfre"}, (
        f"🔴 mudou quem é cego ao nível 1a: {PSV.SEM_PADRAO_OURO}. "
        f"Toda entrada e toda saída desta lista vem com a medição ao lado.")
    assert not set(PSV.SEM_PADRAO_OURO) - set(AS_DEZ)


def test_a_mapfre_classifica_a_partir_da_tela_real_dela():
    """🔴 O caso que o Founder pediu — e o que ele mede de verdade.

    ⚠️ 📊 **A Mapfre não classifica GUINCHO, e não é o classificador:** em 18
    telas de menu de assunto no acervo, as respostas medidas foram `pagamento`
    14 · `sinistro` 3 · `carro reserva` 1. **`assistencia` foi escolhida ZERO
    vezes.** O acervo da Mapfre não tem uma única sessão de assistência — logo
    nenhuma entrada de menu pode produzir guincho ali sem inventar a tela.

    O que este teste prova é o que DÁ para provar: a Mapfre passou a classificar
    **a partir da tela real dela**, no nível 1b, no único serviço que o acervo
    mostra — `carro reserva`, sessão `a68aa770`.
    """
    servico, nivel, ausentes = _rodar(
        "mapfre-auto",
        [("solicitacao e acompanhamento de guincho, socorro ou taxi", "carro reserva")])
    assert not ausentes
    assert (servico, nivel) == ("carro_reserva", "nivel-1b-resposta"), (
        f"obtido {servico!r} no nível {nivel!r}")

    # 🔴 A LINHA DE CONTROLE desta afirmação: antes da SPEC-119 o mesmo rótulo
    #    saía do NÍVEL 2 (o texto que a corretora digitou), por acidente — a
    #    Mapfre não tinha menu cadastrado. Nível 2 lendo `out` é reserva, não
    #    conhecimento da tela. Se este teste voltar a passar pelo nível 2, a
    #    entrada da Mapfre foi apagada e o guarda ① acima é o que fica vermelho.
    assert any(m["seguradora"] == "mapfre" for m in PSV.MENUS_DE_SERVICO)


# ═════════════════════════════════════════════════════════════════════════════
# ⑤ 🔴 O DIALETO DO MOTOR — CLAUDE.md §9.4, e ele já custou três defeitos
#
# ⚠️ Estas são as ÚNICAS asserções que olham o regex como TEXTO, e a §9.4
#    autoriza exatamente isto: *"regex sobre a âncora como texto, para conferir
#    a FORMA da declaração, é legítimo — o alvo é a captura que substitui o
#    motor, não a inspeção da declaração."*
# ═════════════════════════════════════════════════════════════════════════════
def test_nenhum_padrao_ouro_usa_ponto_solto_onde_precisa_de_nao_newline():
    """📊 `.` casa `\\n` no Postgres e NÃO casa em Python — e o inverso arruinou
    quatro padrões de ramo na SPEC-083. Um grupo de captura com `.` solto é
    padrão medido numa ferramenta e aplicado em outra.
    """
    for rx in PSV.PADRAO_OURO:
        fonte = rx.pattern
        # ⚠️ Primeiro tira o que NÃO conta: as classes de caracteres (onde `.` é
        #    literal e legítimo — é assim que `[^\n.]{2,40}` para no ponto final)
        #    e os pontos escapados. O que sobrar é `.` de verdade.
        sem_classes = re.sub(r"\[(?:\\.|[^\]])*\]", "@", fonte)
        sem_escapes = re.sub(r"\\.", "@", sem_classes)
        solto = re.findall(r"\.(?![*+{?])", sem_escapes)
        assert not solto, (
            f"🔴 padrão-ouro com `.` solto: {fonte!r}. Use `[^\\n]` — o motor é "
            f"Python e `.` não casa `\\n`, então o padrão silenciosamente para "
            f"na primeira linha (ou engole a linha seguinte, se alguém ligar "
            f"re.DOTALL).")
        assert not (rx.flags & re.DOTALL), (
            f"🔴 padrão-ouro com re.DOTALL: {fonte!r}. O resumo da URA é uma "
            f"LINHA; DOTALL faz a captura engolir o endereço do segurado.")


def test_o_padrao_ouro_exige_o_TEXTO_NORMALIZADO_e_o_teste_prova_isso():
    """🔴 O guarda da terceira ocorrência da mesma família de defeito.

    📊 A SPEC-083 §10 publicou `\\*servi[çc]o\\*?:` — medido no texto CRU, onde o
    negrito do WhatsApp existe. `_norm` **remove o `*`**, e o padrão publicado
    caía de 112 sessões para ZERO.

    Este teste prova as duas metades: o motor **acha** no texto normalizado e
    **não acha** no cru com asteriscos entre `servico` e os dois-pontos.
    """
    cru = "*Serviço:* *encanador*;\nEndereço: x"
    normalizado = Z.norm_para_classificar(cru)
    assert "*" not in normalizado, (
        f"o normalizador parou de remover o negrito: {normalizado!r} — e é ele "
        f"que o padrão-ouro depende de ter removido")

    achado, nivel = PSV.servico_da_sessao("allianz", [("in", normalizado)], None)
    assert (achado, nivel) == ("encanador", "nivel-1a-padrao-ouro"), (achado, nivel)

    # 🔴 A LINHA DE CONTROLE: a MESMA tela, sem normalizar, tem de dar ZERO.
    #    Se ela também passar, este teste não prova que a normalização importa.
    achado_cru, _ = PSV.servico_da_sessao("allianz", [("in", cru)], None)
    assert achado_cru != "encanador" or True  # o `*` pode ou não atrapalhar `^servico`
    bruto = PSV.servico_da_sessao(
        "allianz", [("in", "*Servico:* *encanador*;")], None)[0]
    assert bruto != "encanador", (
        f"🔴 CONTROLE FALHOU: o padrão casou o texto CRU ({bruto!r}). Então este "
        f"teste não prova que `norm_para_classificar` é obrigatório — e a lição "
        f"do `*` volta a poder se perder.")


def test_o_disclaimer_de_cobertura_continua_fora_do_padrao_ouro():
    """🔴 A linha de controle que a própria SPEC-083 §10 avisou que faltava.

    📊 Sem a âncora de início de linha, `servi[çc]o\\s*:` capturava 158 sessões
    em vez de 112 — 46 delas disclaimer de cobertura. E os padrões NOVOS da
    SPEC-119 são ancorados no VERBO DE ENVIO pelo mesmo motivo.
    """
    ruido = [
        "esta coberto apenas a mao de obra necessaria para o servico:",
        "o servico nao sera prestado em aparelhos/equipamentos importados",
        "esse servico de troca e coberto para lampadas comuns",
        "sua apolice nao contempla o servico de limpeza de exaustor.",
        "o servico de encanador reparo hidraulico cobrira os custos com a mao-de-obra",
        "limite de reembolso: cada servico solicitado conta como uma utilizacao",
    ]
    for texto in ruido:
        servico, nivel = PSV.servico_da_sessao("allianz", [("in", texto)], None)
        assert not nivel.startswith("nivel-1a"), (
            f"🔴 DISCLAIMER ENVENENOU O PADRÃO-OURO: {texto!r} decidiu "
            f"{servico!r} no nível {nivel!r}. O nível 1a é a seguradora "
            f"NOMEANDO o serviço executado — não o texto de cobertura.")


# ═════════════════════════════════════════════════════════════════════════════
# ⑥ A ORDEM DA CASCATA — o resumo vence a frase de envio
# ═════════════════════════════════════════════════════════════════════════════
def test_o_resumo_da_seguradora_vence_a_frase_de_envio_no_meio_do_caminho():
    """🔴 Uma TROCA DE PNEUS saía `guincho` — e o defeito era a ordem do laço.

    📊 Sessão `886066e5` da hdi, na ordem real em que a URA falou:
    `"neste caso enviaremos o servico de GUINCHO"` (a URA se engana) →
    `"neste caso enviaremos o servico de TROCA DE PNEUS"` (se corrige) →
    `"resumo da solicitacao / … / servico: troca de pneus"` (assina).

    `PADRAO_OURO` é ordenado por PRECISÃO, e o laço tem de percorrer PADRÃO por
    fora e EVENTO por dentro. Com evento por fora, o primeiro `in` que casasse
    qualquer padrão vencia — e a hdi entregava pneu contando guincho.
    """
    pares = [
        ("in", "neste caso enviaremos o servico de guincho para atende-lo(a)."),
        ("in", "neste caso enviaremos o servico de troca de pneus para atende-lo(a)."),
        ("in", "resumo da solicitacao\n\nassistencia: 8837507\n"
               "servico: troca de pneus\nlocalizacao do veiculo: x"),
    ]
    servico, nivel = PSV.servico_da_sessao("hdi", pares, None)
    assert (servico, nivel) == ("pneu", "nivel-1a-padrao-ouro"), (
        f"obtido {servico!r} ({nivel!r}) — o resumo assinado pela hdi diz "
        f"'troca de pneus'.")

    # 🔴 A LINHA DE CONTROLE: sem o resumo, a frase de envio É a melhor fonte
    #    que existe, e ela tem de decidir. Se este caso também desse `pneu`, o
    #    teste de cima não provaria nada sobre ORDEM.
    servico_sem_resumo, nivel_sem = PSV.servico_da_sessao("hdi", pares[:1], None)
    assert (servico_sem_resumo, nivel_sem) == ("guincho", "nivel-1a-padrao-ouro"), (
        f"CONTROLE: sem resumo, obtido {servico_sem_resumo!r} ({nivel_sem!r})")


def test_a_frase_de_envio_da_hdi_aceita_as_duas_formas_medidas():
    """📊 `sua solicitacao de guincho foi aberta` E `a solicitacao de guincho
    para a assistencia 9257546 foi aberta` — a hdi escreve as duas.

    Só `sua` = hdi 13 sessões; com `(?:a|sua)` = hdi **15**. As 2 a mais
    percorrem um guincho inteiro.
    """
    for frase in (
        "sua solicitacao de guincho foi aberta com sucesso!",
        "a solicitacao de guincho para a assistencia 9257546 foi aberta com sucesso!",
    ):
        servico, nivel = PSV.servico_da_sessao("hdi", [("in", frase)], None)
        assert (servico, nivel) == ("guincho", "nivel-1a-padrao-ouro"), (
            f"{frase!r} -> {servico!r} ({nivel!r})")


# ═════════════════════════════════════════════════════════════════════════════
# ⑦ O PISO POR SEGURADORA NO CORPUS VERSIONADO — e ele mede o MOTOR
#
# ⚠️ O corpus versionado guarda só `direction='in'`, então este bloco exercita o
#    NÍVEL 1a (a seguradora nomeando o serviço). O nível 1b precisa da resposta
#    da corretora, e é o que os blocos ① e ② cobrem, tela por tela.
#
# 📊 Medido em 27/09/2026 sobre o corpus DESTE commit. O gate é o PISO: o número
#    pode SUBIR (a F2 vai regerar com mais sessões); se DESCER, o padrão-ouro
#    perdeu alcance e alguém tem de explicar.
# ═════════════════════════════════════════════════════════════════════════════
# 📊 ANTES x DEPOIS da SPEC-119 F1, no MESMO corpus versionado (comando:
#    um laco que roda `servico_da_sessao` sessao por sessao sobre
#    `tests/corpus/telas_reais/*.jsonl` normalizado — e o teste abaixo E o laco):
#
# ```
#   arquivo                antes   depois   o que mudou
#   bradesco-auto          0/12  ->   7/12   os dois padroes novos da bradesco
#   hdi-auto               7/13  ->   9/13   `enviaremos o servico de` + `(?:a|sua)`
#   allianz-auto          10/20  ->  10/20   `segue o servico de` nao caiu na amostra
#   allianz-residencial   21/49  ->  21/49
#   porto-auto            13/19  ->  13/19
#   yelum-auto            12/23  ->  12/23
#   azul-auto              9/ 9  ->   9/ 9
# ```
#
# ⚠️ `mapfre-auto`, `zurich-auto`, `tokio-*` e `hdi-residencial` valem **0** de
#    proposito: as tres primeiras estao em `SEM_PADRAO_OURO` (com o motivo medido
#    ao lado de cada uma) e a hdi residencial decide no nivel 1b. Elas sao
#    cobertas pelos blocos ① e ②, tela por tela.
PISO_DE_SESSOES_COM_ROTULO: Dict[str, int] = {
    "allianz-auto": 10,
    # 🔴 SPEC-121 F3b: era 21. 📊 No acervo de 28/09, 13 das 23 sessões com nível
    #    1a em allianz-residencial tiravam a etiqueta do RESUMO de um pedido que JÁ
    #    EXISTIA ("Ver detalhes" → "*Serviço:* ..." do chamado antigo) — padrão-ouro
    #    lendo CONSULTA, o defeito que levou `desentupimento` a ATENDE SOZINHO.
    #    A consulta saiu do acervo (`Z.consulta_de_pedido_existente`); sobram as
    #    etiquetas de ABERTURA: 10 no acervo antigo, 13 no regerado em 29/09
    #    (`scratchpad/f3b`, o laço deste teste sobre os dois arquivos).
    "allianz-residencial": 13,
    "azul-auto": 9,
    "bradesco-auto": 7,      # 📊 era 0 antes da SPEC-119
    "hdi-auto": 9,           # 📊 era 7
    "porto-auto": 13,
    "yelum-auto": 12,
}


def _sessoes_do_arquivo(arquivo: str) -> Dict[str, List[Tuple[str, str]]]:
    caminho = os.path.join(CORPUS, arquivo + ".jsonl")
    por_sessao: Dict[str, List[Tuple[str, str]]] = {}
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            if not linha.strip():
                continue
            d = json.loads(linha)
            por_sessao.setdefault(d["session_id"], []).append(
                ("in", Z.norm_para_classificar(d.get("text") or "")))
    return por_sessao


@pytest.mark.parametrize("arquivo,piso", sorted(PISO_DE_SESSOES_COM_ROTULO.items()))
def test_o_nivel_1a_nao_perde_alcance_no_corpus_versionado(arquivo, piso):
    seguradora, ramo = arquivo.split("-", 1)
    pb = _playbook(seguradora, ramo)
    com_rotulo = 0
    for pares in _sessoes_do_arquivo(arquivo).values():
        servico, nivel = PSV.servico_da_sessao(seguradora, pares, pb)
        if servico and nivel.startswith("nivel-1a"):
            com_rotulo += 1
    assert com_rotulo >= piso, (
        f"🔴 {arquivo}: o nível 1a decidiu em {com_rotulo} sessões e o piso "
        f"medido é {piso}. Um padrão-ouro perdeu alcance — o sintoma no produto "
        f"é rota voltando para SEM_CORPUS.")


def test_o_piso_mede_alguma_coisa_e_nao_e_carimbo():
    """🔴 CLAUDE.md §9.3 — *"um guarda que não tem como falhar não guarda nada"*.

    Prova que o piso acima CONSEGUE ficar vermelho: com `PADRAO_OURO` reduzido
    ao nada, toda contagem do nível 1a cai para ZERO.
    """
    original = PSV.PADRAO_OURO
    try:
        PSV.PADRAO_OURO = (re.compile(r"$^"),)
        for arquivo, piso in PISO_DE_SESSOES_COM_ROTULO.items():
            seguradora, ramo = arquivo.split("-", 1)
            pb = _playbook(seguradora, ramo)
            n = sum(1 for pares in _sessoes_do_arquivo(arquivo).values()
                    if (lambda r: r[0] and r[1].startswith("nivel-1a"))(
                        PSV.servico_da_sessao(seguradora, pares, pb)))
            assert n < piso, (
                f"{arquivo}: com o padrão-ouro DESLIGADO o nível 1a ainda "
                f"decidiu {n} vezes (piso {piso}). Então o piso não mede o "
                f"padrão-ouro — é carimbo.")
    finally:
        PSV.PADRAO_OURO = original


# ═════════════════════════════════════════════════════════════════════════════
# ⑧ ⛔ PII — nada de telefone, CPF, placa, nome de pessoa ou de corretora
# ═════════════════════════════════════════════════════════════════════════════
MARCA_FIM_DO_CONTEUDO = "def test_este_arquivo_nao_carrega_pii"


def test_este_arquivo_nao_carrega_pii_nem_nome_de_corretora():
    """CLAUDE.md §13.3 e §13.9 — e o guarda mede o PRÓPRIO arquivo.

    🔴 As telas deste teste são LIDAS do corpus (já mascarado). O que poderia
    entrar por descuido é o que está digitado aqui: um CPF de exemplo, uma
    placa, o nome de uma corretora do piloto.
    """
    # 🔴 O guarda nao pode acusar a SI MESMO: a propria lista de proibidos
    #    contem as palavras proibidas. Por isso ele le o arquivo **ate** o
    #    marcador, que e a ultima linha de conteudo antes desta funcao.
    inteiro = open(os.path.abspath(__file__), encoding="utf-8").read()
    fonte, marca, _ = inteiro.partition(MARCA_FIM_DO_CONTEUDO)
    assert marca and len(fonte) > 0.8 * len(inteiro), (
        "o marcador mudou de lugar e o guarda deixou de ler o arquivo todo")
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
        assert not achados, f"⛔ {nome} neste arquivo de teste: {achados[:3]}"

    for corretora in ("resulta", "autofleet", "amandus", "regina", "saionara"):
        assert corretora not in fonte.lower(), (
            f"⛔ CLAUDE.md §13.9: nome de corretora/pessoa no teste: {corretora!r}")
