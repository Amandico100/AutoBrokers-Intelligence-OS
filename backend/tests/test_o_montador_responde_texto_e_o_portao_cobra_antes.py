# -*- coding: utf-8 -*-
"""O montador responde TEXTO, o portão cobra ANTES, e a Tokio entrega a uma pessoa.

SPEC-118, fatia F2b — a fatia da LÓGICA. A F2a deixou o mapa da Porto pronto e
MEDIU que ele não respondia nada; este arquivo guarda os quatro consertos e,
principalmente, **as linhas de controle que dão direito a chamá-los de
conserto** (CLAUDE.md §9.2).

```
1. TEXTO           componente sem `options` recebe o valor do caso como texto.
                   🔴 CONTROLE: componente COM `options` continua recusando
                   valor fora da lista — é ela que impede o robô de decidir
                   pelo segurado (§9.5)
2. O PORTÃO        os campos obrigatórios do formulário que ESTE subserviço
                   abre entram no que falta ANTES de acionar.
                   🔴 CONTROLE: subserviço que não vê a tela não é cobrado
                   (o achado do juiz 4: "bloquear rota que não vê a tela é
                   interrogatório à toa")
3. TOKIO           a tela do LINK entrega o caso a uma pessoa.
                   🔴 CONTROLE: tela da Tokio SEM link não vira handoff
4. O NOME          a Yelum recebe o nome do formulário DA YELUM
```

## 🔴 O QUE ESTE ARQUIVO AFIRMA E O QUE ELE NEGA

📊 Medido em 26/09/2026, com o motor real, depois desta fatia::

    montar_resposta_de_flow(<mapa da Porto>, <slots da captura>)
      → ok=False, missing=['latitude', 'longitude'], motivo='sem_chute'

**Os sete campos de texto saíram de `missing`** — era isso que faltava. O que
sobra são as duas coordenadas que o próprio Flow da Porto geocodifica e que nós
não temos de onde tirar (📊 0 geocodificadores no backend). Elas continuam
`sem_chute`: a resposta NÃO sai e o caso vai a uma pessoa com o motivo escrito.
⛔ Zero inventado põe o guincho no Golfo da Guiné.

⚠️ Por isso este arquivo **não** afirma que o formulário da Porto está
resolvido. Ele afirma que o corredor deixou de mentir sobre o motivo: antes eram
sete campos "valor_nao_reconhecido" (que acusa o endereço do segurado de estar
errado), agora são duas coordenadas que ninguém tem.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"
FIXTURE = RAIZ / "tests" / "fixtures" / "formulario_porto_21_09.json"
CORPUS = RAIZ / "tests" / "corpus" / "telas_reais"


def _carregar(nome: str, caminho: Path):
    """Carrega o módulo pelo caminho, sem passar pelo `app/__init__` pesado."""
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in anteriores if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


PB = _carregar("_spec118b_pb", PLAYBOOKS_PY)

CAPTURA = json.loads(FIXTURE.read_text(encoding="utf-8"))

REF_PORTO = "porto-auto-whatsapp@v1"
REF_TOKIO = "tokio-auto-whatsapp@v1"
FLOW_PORTO_ENDERECO = "709854848132894"
#: 📊 O MESMO formulário da família, com o id que cada seguradora publica.
FLOW_HDI = "857030507196739"
FLOW_YELUM = "3206000179602236"
#: 📊 O segundo formulário da família (2 telas), usado pelos dois.
FLOW_LOCAL_E_OCUPANTES = "2887131368288279"

#: Os slots do caso, no vocabulário do corredor, tirados da captura de 21/09.
SLOTS_DA_CAPTURA = dict(CAPTURA["slots_do_corredor_equivalentes"])

#: 📊 As duas chaves que o Flow da Porto geocodifica e que nós não temos.
SEM_FONTE = ["latitude", "longitude"]


def _porto():
    pb = PB.get_playbook(REF_PORTO)
    assert pb, f"o corredor {REF_PORTO} sumiu"
    return pb


def _flow_porto():
    flow = PB.native_flow(_porto(), FLOW_PORTO_ENDERECO)
    assert flow, "o mapa do formulário da Porto sumiu (fatia F2a)"
    return flow


def _telas_do_corpus(arquivo: str):
    """As telas REAIS do acervo (§7.1 — `tests/corpus/telas_reais`).

    🔴 Nenhum texto de seguradora neste arquivo é escrito à mão: ele é LIDO do
    corpus, que é a referência interna declarada pelo protocolo. O corpus já sai
    mascarado (`{NOME}`, `{CPF}`, `{CAMINHO}`), então nada de PII entra aqui."""
    caminho = CORPUS / arquivo
    assert caminho.exists(), f"o corpus {arquivo} sumiu"
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()
            if l.strip()]


# ===========================================================================
# 1. O MONTADOR RESPONDE CAMPO DE TEXTO
# ===========================================================================

def test_o_montador_responde_os_campos_de_TEXTO_da_porto():
    """🔴 Este teste SUBSTITUI `test_o_montador_AINDA_nao_sabe_responder_campo_de_TEXTO`.

    A garantia antiga ("não se declare pronto cedo") continua inteira, agora
    pelo outro lado: o que falta é NOMEADO, e é exatamente o que não temos.

    📊 Antes desta fatia: `missing` tinha os 7 campos de texto, motivo
    `valor_nao_reconhecido`. Depois: `missing` tem as 2 coordenadas, motivo
    `sem_chute`."""
    montado = PB.montar_resposta_de_flow(_flow_porto(), dict(SLOTS_DA_CAPTURA))
    assert montado["missing"] == SEM_FONTE, (
        f"o que falta mudou: {montado['missing']} — se um campo de TEXTO voltou "
        f"para cá, o passthrough parou de funcionar")
    # 🔴 O MOTIVO MIGROU EM 26/09 (F4): a coordenada ganhou fonte — o PIN — e
    #    passou a faltar como qualquer outro dado, com o slot NOMEADO. A garantia
    #    é a mesma ("não se declare pronto cedo"), e agora o motivo diz para onde
    #    a atendente vai: pedir o pin, em vez de procurar um dado que não existe.
    assert {d["motivo"] for d in montado["missing_detail"]} == {"sem_valor"}, (
        f"motivos={[d['motivo'] for d in montado['missing_detail']]} — "
        "`sem_chute` de volta significa que a coordenada perdeu a fonte do pin")
    assert {d["slot"] for d in montado["missing_detail"]} == {
        "local_latitude", "local_longitude"}, montado["missing_detail"]
    # 🔴 E A PROVA POSITIVA DO TEXTO: a chave DERIVADA só existe se os cinco
    #    componentes de texto tiverem resolvido valor.
    #    📊 molde medido em 3 de 3 capturas:
    #       "{rua}, {numero_residencia}, {bairro}, {cidade} - {estado}"
    assert "label_endereco_completo" not in montado["missing"], (
        "a chave derivada do endereço não se montou — algum dos cinco campos de "
        "texto não resolveu valor, e o molde ficou sem peça")
    # A resposta continua NÃO saindo pela metade.
    assert montado["ok"] is False and montado["params"] is None


def test_CONTROLE_o_valor_do_caso_e_o_que_preenche_o_campo_de_texto():
    """§9.3 — prove que o `missing` curto acima é mérito do VALOR, não de o
    montador ter passado a ignorar campo de texto.

    Um fator varia: tira-se `local_rua` do caso. Se o campo de texto estivesse
    sendo ignorado, nada mudaria."""
    slots = dict(SLOTS_DA_CAPTURA)
    slots.pop("local_rua")
    montado = PB.montar_resposta_de_flow(_flow_porto(), slots)
    assert "rua" in montado["missing"], (
        "sem o slot do logradouro o montador seguiu aprovando o campo — ele "
        "deixou de ler o valor do caso")
    detalhe = next(d for d in montado["missing_detail"] if d["campo"] == "rua")
    assert detalhe["motivo"] == "sem_valor", (
        f"a ausência virou {detalhe['motivo']!r}; `valor_nao_reconhecido` aqui "
        f"seria o defeito de antes desta fatia")
    assert detalhe.get("slot") == "local_rua", (
        "o detalhe não diz QUAL slot do caso falta — é isso que o portão e o "
        "agente leem para pedir a informação certa")


def test_CONTROLE_escolha_fechada_continua_recusando_valor_fora_da_lista():
    """🔴 A linha de controle que impede o conserto de virar afrouxamento.

    O passthrough de texto valia para componente SEM `options`. Componente COM
    `options` é o que escolhe o EQUIPAMENTO (plataforma, asa delta, munck) e a
    PRIORIDADE do caso: ali um valor fora da lista continua sendo
    `valor_nao_reconhecido`, nunca o texto cru (CLAUDE.md §9.5)."""
    familia = PB.native_flow(PB.get_playbook("hdi-auto-whatsapp@v1"), FLOW_HDI)
    assert familia, "o mapa da família HDI/Yelum sumiu"
    montado = PB.montar_resposta_de_flow(familia, {
        # 📊 "garagem" é apelido declarado → "1", e é o que faz a tela do NÍVEL
        #    aparecer (`visible_if` do próprio schema). Com "na rua" o formulário
        #    não mostra o campo, e o teste não mediria nada.
        "veiculo_em_garagem": "garagem",
        "veiculo_nivel_rua": "num lugar qualquer",   # 🔴 fora da lista
        "local_situacao": "Local Seguro",
    })
    detalhes = {d["campo"]: d for d in montado["missing_detail"]}
    assert "rb_NivelDaRua" in detalhes, (
        "o campo que escolhe o equipamento aceitou um valor que a seguradora "
        "não publicou — o passthrough de texto vazou para a escolha fechada")
    assert detalhes["rb_NivelDaRua"]["motivo"] == "valor_nao_reconhecido"
    assert montado["params"] is None


def test_CONTROLE_com_a_coordenada_declarada_a_resposta_da_porto_sai_INTEIRA():
    """🔴 O controle que prova que só a coordenada está no caminho — e mostra o
    CORPO que a Porto consome.

    📊 §9.2: varia-se UM fator (as duas chaves `sem_chute`) sobre uma CÓPIA do
    mapa REAL. Se a resposta então sai com as 11 chaves medidas no acervo, o
    resto do montador está inteiro e o bloqueio de hoje é a fonte da
    coordenada, e mais nada.

    ⛔ A cópia é obrigatória: mexer no mapa vivo faria o produto mandar resposta
    sem coordenada. O que este teste mede é o montador, não a política."""
    copia = copy.deepcopy(_flow_porto())
    for chave in SEM_FONTE:
        copia["resposta"]["obrigatorias"].pop(chave)
    montado = PB.montar_resposta_de_flow(copia, dict(SLOTS_DA_CAPTURA))
    assert montado["ok"] is True, f"ainda falta: {montado['missing_detail']}"
    esperadas = (set(CAPTURA["chaves_da_resposta"]["presentes_em_3_de_3"])
                 - set(SEM_FONTE)
                 | set(CAPTURA["chaves_da_resposta"]["presentes_em_2_de_3"]))
    assert set(montado["params"]) == esperadas, (
        f"o corpo não é o do acervo: sobrou "
        f"{sorted(set(montado['params']) - esperadas)} · faltou "
        f"{sorted(esperadas - set(montado['params']))}")
    # 📊 As chaves que NÃO são componente da tela, e de onde saem:
    assert montado["params"]["cep"] == SLOTS_DA_CAPTURA["local_cep"]
    assert montado["params"]["referencia"] == SLOTS_DA_CAPTURA["ponto_referencia"]
    assert montado["params"]["label_endereco_completo"] == (
        CAPTURA["answers_mascarado"]["label_endereco_completo"]), (
        "o molde do endereço completo divergiu do medido em 3 de 3 capturas")
    # ⛔ E nenhum nome de COMPONENTE escapa para o corpo: a Porto consome as
    #    chaves de primeiro nível, não a lista de telas.
    assert "location" not in montado["params"]
    assert "ponto_referencia" not in montado["params"]


def test_a_coordenada_AUSENTE_e_HANDOFF_COM_MOTIVO_nunca_zero():
    """⛔ O defeito irreversível: lat/long 0 é o Golfo da Guiné, e a URA aceita
    calada. Responder com zero abre o chamado no meio do Atlântico.

    🔴 MIGROU EM 26/09/2026 (SPEC-118 F4). A mensagem de falha antiga dizia o
    que fazer: *"se apareceu uma FONTE real, escreva a medição dela no mapa e
    migre este teste (§9.3)"*. Apareceu — o PIN — e as duas asserções que
    morreram foram `motivo == "sem_chute"` e `not d["slot"]`.

    ⚠️ **A garantia não era sobre o nome do motivo.** Era: sem a coordenada a
    resposta NÃO SAI, e o caso vai a uma pessoa com o que falta escrito. Isso
    continua palavra por palavra — e ganhou a metade que fecha a porta de
    verdade: o par DESONESTO (zero, meio par, fora de faixa) também não sai, e é
    o motor do produto que o recusa."""
    montado = PB.montar_resposta_de_flow(_flow_porto(), dict(SLOTS_DA_CAPTURA))
    assert montado["ok"] is False and montado["params"] is None
    for d in montado["missing_detail"]:
        assert d["campo"] in SEM_FONTE
        assert d["motivo"] == "sem_valor", d
        assert d.get("valor_recebido") in (None, ""), (
            f"a coordenada chegou com valor {d.get('valor_recebido')!r} e ainda "
            f"assim foi recusada — isso é `valor_nao_reconhecido` disfarçado")
        # 🔴 AGORA ELA TEM SLOT, E É ISSO QUE A TORNA PEDÍVEL: é por este nome
        #    que o portão cobra e que o agente ensina o segurado a mandar o pin.
        #    ⛔ E NÃO é "interrogar por uma latitude": `_COMO_PERGUNTAR` traduz os
        #    dois slots na MESMA frase, que ensina o clipe, e
        #    `test_o_fio_do_acionamento_atravessa_o_formulario` prova que nenhuma
        #    frase dita ao segurado contém a palavra "latitude".
        assert d["slot"] in ("local_latitude", "local_longitude"), d

    # 🔴 O PAR DESONESTO TAMBÉM NÃO VIAJA — pelo motor, nunca por leitura.
    for lat, lon, apelido in (("0", "0", "o Golfo da Guine"),
                              ("0.0000001", "0", "zero com maquiagem"),
                              ("-27.588016", "", "meio par"),
                              ("abc", "def", "texto no lugar do numero")):
        slots = dict(SLOTS_DA_CAPTURA, local_latitude=lat, local_longitude=lon)
        PB.inject_address_slots(slots)
        sobrou = {k: v for k, v in slots.items() if "itude" in k}
        assert not sobrou, f"⛔ {apelido} sobreviveu ao portao: {sobrou}"
        ruim = PB.montar_resposta_de_flow(_flow_porto(), slots)
        assert ruim["ok"] is False and ruim["params"] is None, ruim["params"]

    # 🔴 CONTROLE: o par HONESTO do pin FECHA a resposta. Sem esta linha, um
    #    portão que apagasse tudo passaria em todas as asserções acima.
    bom = dict(SLOTS_DA_CAPTURA, local_latitude="-27.588016",
               local_longitude="-48.544253")
    PB.inject_address_slots(bom)
    fecha = PB.montar_resposta_de_flow(_flow_porto(), bom)
    assert fecha["ok"] is True, fecha["missing_detail"]
    assert fecha["params"]["latitude"] == "-27.588016", fecha["params"]


# ===========================================================================
# 2. O PORTÃO COBRA ANTES — E SÓ DE QUEM VÊ A TELA
# ===========================================================================
#
# 📊 O CRITÉRIO de "este subserviço abre este formulário" é o acervo, e está
#    declarado em `subservicos_observados` dentro de cada mapa. Medido no corpus
#    de telas reais (o mesmo que a régua usa), 26/09/2026:
#
#      porto/auto   o convite "[FORMULARIO NATIVO: Preencher]" aparece em 2
#                   sessões, as DUAS de `guincho` (28/05 e 14/09/2026)
#      hdi/yelum    `detect_native_flow` casa em guincho (7 telas), e o
#                   formulário de 2 telas também em chaveiro, pneu e
#                   socorro_mecanico
#
# ⚠️ E o critério NÃO é `slot in required_slots`: era essa circularidade que
#    fazia o campo do formulário nunca ser cobrado (SPEC-118 §2.3).

DO_FORMULARIO_DA_PORTO = ["local_rua", "local_numero", "local_bairro",
                          "local_cidade", "local_uf", "local_cep",
                          "ponto_referencia"]


def test_o_portao_cobra_os_campos_do_formulario_QUE_TEM_COMO_SER_RESPONDIDO():
    """🔴 O elo 3 da SPEC — e a trava que o impede de virar interrogatório.

    Sem o portão, a sessão nasce `ready_to_send`, a URA roda ~25 telas, o
    formulário chega e o caso morre no último portão, com o segurado esperando.

    ⚠️ Mas a pergunta só existe se a RESPOSTA puder sair. 📊 O formulário da Porto
    tem duas chaves obrigatórias `sem_chute`: ele termina em `needs_human` com ou
    sem o CEP. Cobrar o CEP antes seria acrescentar duas perguntas e mandar o caso
    a uma pessoa do mesmo jeito — o erro do juiz 4 com outra roupa.

    🔴 Este teste prova o MECANISMO, na CÓPIA do mapa em que a coordenada tem
    fonte — que é o estado em que o portão precisa funcionar. E o teste seguinte
    prova que, no mapa REAL de hoje, ele não pergunta nada."""
    copia = copy.deepcopy(_porto())
    flow = copia["native_flows"][FLOW_PORTO_ENDERECO] = copy.deepcopy(_flow_porto())
    for chave in SEM_FONTE:
        flow["resposta"]["obrigatorias"].pop(chave)
    faltando = PB.missing_slots_for_subservice(copia, "guincho", {})
    ausentes = [s for s in DO_FORMULARIO_DA_PORTO if s not in faltando]
    assert not ausentes, (
        f"o portão não cobra {ausentes} — são campos OBRIGATÓRIOS do formulário "
        f"que a Porto abre no guincho, e sem eles a resposta não sai")


def test_formulario_que_NAO_FECHA_nao_gera_pergunta_nenhuma():
    """⛔ A trava contra o interrogatório à toa — 🔴 MIGRADA EM 26/09/2026 (F4).

    A afirmação antiga era sobre o mapa REAL da Porto: *"enquanto a coordenada
    não tiver fonte, o portão fica calado"*. 📊 Ela tinha DOIS motivos escritos,
    e a F4 matou os dois:

    ```
    (1) as duas chaves eram `sem_chute`         -> agora vêm do PIN
    (2) os `local_*` não tinham redação em PT   -> têm, em `_COMO_PERGUNTAR`
    ```

    ⚠️ **O MECANISMO continua vivo, e é ele que este teste guarda.** Qualquer
    formulário com uma chave obrigatória SEM FONTE continua sendo saltado pelo
    portão — perguntar não muda o desfecho dele. Prova-se numa CÓPIA que
    reintroduz o defeito histórico, que é o que torna este guarda um guarda e não
    um carimbo (CLAUDE.md §9.5).
    """
    copia = copy.deepcopy(_porto())
    flow = copia["native_flows"][FLOW_PORTO_ENDERECO] = copy.deepcopy(_flow_porto())
    flow["resposta"]["obrigatorias"]["latitude"] = {
        "origem": "sem_chute", "motivo": "o defeito historico, reintroduzido"}
    faltando = PB.missing_slots_for_subservice(copia, "guincho", {})
    intrusos = [x for x in DO_FORMULARIO_DA_PORTO if x in faltando]
    assert not intrusos, (
        f"o portão passou a cobrar {intrusos} de um formulário que NÃO FECHA "
        f"(latitude sem fonte) — seriam perguntas a mais e o caso iria para uma "
        f"pessoa do mesmo jeito")

    # 🔴 E O ESTADO DE HOJE, MEDIDO: no mapa REAL o portão COBRA — é o elo 3 da
    #    SPEC finalmente fechado — e cobra em português.
    real = PB.missing_slots_for_subservice(_porto(), "guincho", {})
    ausentes = [x for x in DO_FORMULARIO_DA_PORTO if x not in real]
    assert not ausentes, (
        f"o portão parou de cobrar {ausentes} no mapa REAL — o caso voltaria a "
        f"morrer na tela do formulário, depois de ~25 telas de URA")
    assert "local_latitude" in real and "local_longitude" in real, real
    from app.services.corridor_playbooks import _COMO_PERGUNTAR
    sem_redacao = [x for x in real if not _COMO_PERGUNTAR.get(x)]
    assert not sem_redacao, (
        f"o portão cobra {sem_redacao} e o produto não sabe pedir em português — "
        f"o agente diria o identificador a uma pessoa de verdade (§12.1)")

    # 🔴 CONTROLE: com o PIN e o endereço na mão, o portão cobra ZERO. É a
    #    medição que sustenta a decisão desta fatia — UM TOQUE, não seis
    #    perguntas. Sem esta linha, "cobrar sempre" passaria acima.
    com_pin = dict(SLOTS_DA_CAPTURA, local_latitude="-27.588016",
                   local_longitude="-48.544253")
    ainda = [x for x in DO_FORMULARIO_DA_PORTO
             if x in PB.missing_slots_for_subservice(_porto(), "guincho", com_pin)]
    assert not ainda, (
        f"o portão cobra {ainda} de um caso que já tem o endereço inteiro — é o "
        f"interrogatório à toa que a trava existe para evitar")


def test_CONTROLE_o_portao_NAO_cobra_de_quem_nao_ve_a_tela():
    """🔴 Sem esta asserção, "cobrar tudo" passaria — e seria o defeito que o
    juiz 4 já pegou (`insurer_dispatch_service.py:1445`): *"um
    `veiculo_nivel_rua` mal preenchido bloqueava 10 rotas, e oito delas nunca
    abrem aquele formulário"*.

    📊 `local_cep` e `ponto_referencia` não são exigidos por passo de URA nem
    por `required_slots` em nenhum destes subserviços — se aparecerem, vieram do
    formulário que eles NÃO abrem.

    ⚠️ A cobrança roda sobre a CÓPIA em que a coordenada tem fonte: é o único
    estado em que o portão cobra algo, e portanto o único em que "não cobrar de
    quem não vê a tela" pode ser medido."""
    copia = copy.deepcopy(_porto())
    flow = copia["native_flows"][FLOW_PORTO_ENDERECO] = copy.deepcopy(_flow_porto())
    for chave in SEM_FONTE:
        flow["resposta"]["obrigatorias"].pop(chave)
    for subservico in ("bateria", "chaveiro", "pneu", "tecnico"):
        faltando = PB.missing_slots_for_subservice(copia, subservico, {})
        assert "local_cep" not in faltando, (
            f"porto/{subservico} passou a ser interrogado sobre o CEP por causa "
            f"de um formulário que o acervo só mostra no guincho")
        assert "ponto_referencia" not in faltando, (
            f"porto/{subservico} passou a ser interrogado sobre ponto de "
            f"referência por um formulário que ele não vê")


def test_CONTROLE_a_coordenada_NUNCA_vira_pergunta_em_rota_nenhuma():
    """⛔ Campo `sem_chute` é handoff com motivo, nunca interrogatório.

    A varredura é de TODAS as rotas de todos os corredores: uma latitude na
    lista do que falta faria o agente pedir uma coordenada ao segurado."""
    achados = []
    for ref in PB.list_playbooks():
        pb = PB.get_playbook(ref) or {}
        for sub in (pb.get("subservices") or {}):
            faltando = PB.missing_slots_for_subservice(pb, sub, {}) or []
            for proibido in ("latitude", "longitude", "label_endereco_completo",
                             "referencia"):
                if proibido in faltando:
                    achados.append(f"{ref}/{sub}: {proibido}")
    assert not achados, ("o portão virou interrogatório de chave derivada ou "
                         "sem fonte: " + " · ".join(achados))


def test_CONTROLE_o_portao_continua_devolvendo_o_sentinela_de_subservico():
    """§9.3 — o conserto não pode ter afogado o caminho de handoff. `vidros` na
    Allianz não existe por este canal, e o portão diz isso com o SENTINELA, não
    com uma lista de campos."""
    allianz = PB.get_playbook("allianz-auto-whatsapp@v1")
    assert PB.missing_slots_for_subservice(allianz, "vidros", {}) == [
        PB.SUBSERVICO_INVALIDO]


# ===========================================================================
# 3. A TOKIO ENTREGA A UMA PESSOA — DEPOIS DE FAZER A PRIMEIRA PARTE
# ===========================================================================
#
# 📊 Decisão do Founder, 26/09/2026: *"o acionamento da Tokio aparece um link e
#    vai direto para um link da seguradora… vc deve fazer o acionamento da Tokio
#    ser HANDOFF para um humano acionar. Deve fazer a primeira parte e
#    transferir para um humano fazer o acionamento."*
#
# 📊 E a ordem medida no acervo (sessões `ca52ff75` 11/08 e `d99a47a1` 08/01),
#    tela a tela: CPF → "Consegui identificar seu Seguro!" → protocolo de
#    ATENDIMENTO → menu de serviços → **o LINK**. O handoff dispara na última,
#    ou seja DEPOIS de a apólice estar identificada. Um handoff antes disso
#    seria pior que o estado de hoje.

def _telas_tokio_com_link():
    """As telas REAIS da Tokio que entregam o link da assistência."""
    telas = [l for l in _telas_do_corpus("tokio-auto.jsonl")
             if "abaixo para solicitar" in (l.get("text") or "").lower()
             and "autoatendimento.tokiomarine" in (l.get("text") or "")]
    assert len(telas) >= 3, f"o acervo da Tokio mudou: {len(telas)} telas de link"
    return telas


def test_a_tela_do_link_da_tokio_entrega_o_caso_a_uma_pessoa():
    """🔴 O ELO (protocolo §0.3): não basta a âncora casar em `handoff_triggers`
    — ela tem de CHEGAR. No motor, `match_ura_step` é consultado ANTES de
    `detect_handoff_trigger`: enquanto existia um passo `noop` casando esta
    mesma tela, o handoff era inalcançável e o caso ficava em `ura` até o
    watchdog (📊 abandono, nunca uma pessoa)."""
    for tela in _telas_tokio_com_link():
        texto = tela["text"]
        assert PB.match_ura_step(_tokio(), texto) is None, (
            f"um passo de URA voltou a casar a tela do link da Tokio "
            f"({tela['session_id'][:8]}) — ele PRECEDE o handoff no motor, e o "
            f"caso volta a morrer calado")
        gatilho = PB.detect_handoff_trigger(_tokio(), texto)
        assert gatilho, (
            f"a tela que entrega o link (sessão {tela['session_id'][:8]}, "
            f"{tela['wa_timestamp'][:10]}) não vira handoff — o acionamento da "
            f"Tokio continua sem ninguém para fazê-lo")


def test_o_link_da_tokio_e_CAPTURADO_para_a_pessoa_que_vai_acionar():
    """Handoff sem o link seria mandar alguém adivinhar o endereço. Quem colhe é
    `extract_capture_anchors` (`tracking_link`) — e é o MOTOR que se pergunta."""
    for tela in _telas_tokio_com_link():
        colhido = PB.extract_capture_anchors(_tokio(), tela["text"])
        assert colhido.get("tracking_link"), (
            f"o link não foi capturado na tela de {tela['wa_timestamp'][:10]} — "
            f"a pessoa recebe o caso sem o endereço do autoatendimento")


def test_CONTROLE_tela_da_tokio_SEM_link_nao_vira_handoff():
    """🔴 Sem este controle, um gatilho largo mandaria a Tokio inteira para uma
    pessoa — inclusive a tela do CPF, que é a PRIMEIRA PARTE que o corredor
    continua fazendo sozinho."""
    telas = [l for l in _telas_do_corpus("tokio-auto.jsonl")
             if "http" not in (l.get("text") or "").lower()]
    assert len(telas) >= 20, f"amostra pequena demais: {len(telas)}"
    viraram = [(l["text"][:60], PB.detect_handoff_trigger(_tokio(), l["text"]))
               for l in telas]
    pelo_meu = [t for t, gatilho in viraram
                if gatilho == PB._TOKIO_HANDOFF_DO_ACIONAMENTO]
    assert not pelo_meu, ("tela da Tokio SEM link casou o gatilho do link: " +
                          " · ".join(repr(t) for t in pelo_meu))
    # 🔴 E O QUE SOBRA FICA DECLARADO, porque medir é melhor que não ver.
    #    📊 26/09/2026: 3 telas SEM link viram handoff pelo gatilho `acidente`,
    #    que é PRÉ-EXISTENTE e vem da lista-base de `_auto_playbook`. O texto é
    #    publicidade ("Clique no botão abaixo para acessar mais serviços... Conte
    #    com a proteção…"), e nas 3 a URA segue conversando depois. É a mesma
    #    classe do gatilho `sinistro` cru que a SPEC-084 tirou daqui — fica como
    #    achado da F2b, não como conserto: mexer nele muda 13 corredores.
    outros = sorted({g for _t, g in viraram if g})
    assert outros in ([], ["acidente"]), (
        f"a lista de gatilhos da Tokio mudou de comportamento no acervo: {outros}")
    # E a primeira parte continua sendo trabalho do corredor:
    cpf = [l for l in telas if "cpf/cnpj" in (l.get("text") or "").lower()]
    assert cpf, "o acervo da Tokio perdeu a tela de CPF"
    for tela in cpf:
        passo = PB.match_ura_step(_tokio(), tela["text"])
        assert passo and passo.get("step") == "pedir_cpf", (
            f"o corredor deixou de identificar a apólice: {passo}")


def test_CONTROLE_o_gatilho_da_tokio_nao_vazou_para_a_lista_das_outras():
    """🔴 `_auto_playbook` entrega a TODO corredor uma lista-base de
    `handoff_triggers`. Um `+=` na lista compartilhada daria o gatilho do link da
    Tokio a treze seguradoras de uma vez — e mandaria para uma pessoa telas que
    os outros corredores respondem sozinhos."""
    do_tokio = [p for p in (_tokio().get("handoff_triggers") or [])
                if "24h" in str(p)]
    assert do_tokio, "o gatilho do link da Tokio não está declarado no corredor dela"
    for ref in PB.list_playbooks():
        if ref == REF_TOKIO:
            continue
        outros = (PB.get_playbook(ref) or {}).get("handoff_triggers") or []
        vazou = [p for p in do_tokio if p in outros]
        assert not vazou, f"{ref} herdou o gatilho da Tokio: {vazou}"


def _tokio():
    pb = PB.get_playbook(REF_TOKIO)
    assert pb, f"o corredor {REF_TOKIO} sumiu"
    return pb


# ===========================================================================
# 4. O NOME DO FORMULÁRIO É O DA SEGURADORA, NÃO O DO IRMÃO DE FAMÍLIA
# ===========================================================================

def test_o_nome_do_formulario_e_o_da_SEGURADORA_que_publicou_o_id():
    """📊 Os nomes reais têm sufixo por id (medido em `flow_reply`):

        857030507196739   …[Redução de perguntas]_v2_1783714513857   (hdi)
        3206000179602236  …[Redução de perguntas]_v2_1783714477612   (yelum)

    Um registro, dois ids: `montar_resposta_de_flow` devolvia SEMPRE o nome sem
    sufixo — e `_moldura_da_resposta` o ecoa para a seguradora. A Yelum recebia
    o nome do formulário da HDI."""
    familia = PB.native_flow(PB.get_playbook("hdi-auto-whatsapp@v1"), FLOW_HDI)
    nome_hdi = PB.montar_resposta_de_flow(familia, {}, flow_id=FLOW_HDI)["flow_name"]
    nome_yelum = PB.montar_resposta_de_flow(familia, {}, flow_id=FLOW_YELUM)["flow_name"]
    assert nome_hdi.endswith("_v2_1783714513857"), nome_hdi
    assert nome_yelum.endswith("_v2_1783714477612"), nome_yelum
    assert nome_hdi != nome_yelum, (
        "🔴 os dois ids devolveram o MESMO nome — é o defeito inteiro de volta")


def test_sem_saber_o_id_o_produto_NAO_ecoa_o_nome_do_irmao():
    """💭 Entre ecoar o nome errado e não ecoar, não ecoar.

    ⚠️ E a moldura já descarta chave vazia
    (`_moldura_da_resposta`: `{k: v for k, v in moldura.items() if v}`), então
    string vazia aqui significa *"o campo não sai"*, não *"sai vazio"*."""
    familia = PB.native_flow(PB.get_playbook("yelum-auto-whatsapp@v3"), FLOW_YELUM)
    montado = PB.montar_resposta_de_flow(familia, {})
    assert montado["flow_name"] == "", (
        f"sem o id, o produto ecoou {montado['flow_name']!r} — um nome que "
        f"pertence a UMA das duas seguradoras, e talvez não à que está do outro "
        f"lado")


def test_CONTROLE_quem_tem_um_id_so_continua_ecoando_o_nome_medido():
    """§9.3 — prove que o silêncio acima é da AMBIGUIDADE, não do montador.

    A Porto tem um id e um nome, medidos na mesma captura: o nome sai."""
    montado = PB.montar_resposta_de_flow(_flow_porto(), dict(SLOTS_DA_CAPTURA))
    assert montado["flow_name"] == CAPTURA["flow"]["flow_name"], (
        f"o nome do formulário da Porto mudou: {montado['flow_name']!r}")
    assert montado["flow_id"] == FLOW_PORTO_ENDERECO


# ===========================================================================
# 5. A AZUL — NÃO MAPEADA, E `pneu` É HANDOFF, PELO MOTOR
# ===========================================================================

def test_a_azul_continua_sem_mapa_e_o_pneu_dela_e_handoff_pelo_motor():
    """A F2a escreveu o motivo; aqui o MOTOR confirma o efeito.

    📊 `azul/auto/pneu`: o menu migrou em 07/04/2026 e "Troca de pneu" saiu da
    tela. Sem rótulo observado, não se declara tecla — `subservice_supported`
    devolve False e o caso vai a uma pessoa. ⛔ Escolher "a primeira opção"
    mandaria o segurado para o serviço errado (CLAUDE.md §9.5)."""
    azul = PB.get_playbook("azul-auto-whatsapp@v1") or {}
    assert not (azul.get("native_flows") or {}), (
        "a Azul ganhou mapa de formulário sem captura — invenção com cara de "
        "medição (P-118-01)")
    assert PB.subservice_supported(azul, "pneu") is False, (
        "azul/auto/pneu passou a ser 'suportado': se apareceu o RÓTULO no menu "
        "vivo, escreva a medição; se foi uma tecla escolhida no escuro, é o "
        "defeito que este teste barra")
    assert PB.auto_subservice_menu_value(azul, "pneu") == "", (
        "apareceu tecla de menu para o pneu da Azul — o menu vivo não tem "
        "'Troca de pneu' (📊 8 msgs, 07/04 a 28/07/2026)")
    # 🔴 CONTROLE: a mesma pergunta numa rota que a Azul ATENDE.
    assert PB.subservice_supported(azul, "guincho") is True, (
        "nem o guincho da Azul é suportado — então a asserção acima não prova "
        "nada sobre o pneu")
    assert PB.auto_subservice_menu_value(azul, "guincho") == "Guincho (reboque)"


def test_todo_mapa_de_formulario_declara_de_quem_e_a_tela():
    """🔴 O portão novo só cobra quem tem `subservicos_observados`. Um mapa sem a
    declaração é um mapa que o portão IGNORA em silêncio — então a declaração é
    obrigatória, e com procedência."""
    sem = []
    for ref in PB.list_playbooks():
        pb = PB.get_playbook(ref) or {}
        for flow_id, flow in (pb.get("native_flows") or {}).items():
            obs = flow.get("subservicos_observados")
            if not obs:
                sem.append(f"{ref}/{flow_id}")
                continue
            for subservico, evidencia in obs.items():
                assert subservico in (pb.get("subservices") or {}), (
                    f"{ref}/{flow_id} declara o subserviço {subservico!r}, que "
                    f"não existe neste corredor")
                assert "📊" in str(evidencia), (
                    f"{ref}/{flow_id}/{subservico} não diz de onde veio")
    assert not sem, ("mapa de formulário sem `subservicos_observados` — o portão "
                     "não cobra nada dele: " + " · ".join(sem))
