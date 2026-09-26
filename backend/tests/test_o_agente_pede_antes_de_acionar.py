# -*- coding: utf-8 -*-
"""O agente PEDE antes de acionar — e pede em português, uma coisa por vez.

SPEC-118, fatia F3 — o elo ⑤ do fio. A F2b ensinou o portão a somar os campos
obrigatórios do formulário nativo que ESTE subserviço abre; esta fatia é a outra
metade: **como se pede**, e para quem NÃO se pergunta.

📊 O DEFEITO, MEDIDO NO MOTOR REAL EM 26/09/2026, ANTES DESTA FATIA

    InsurerDispatchTool._run(porto/auto/guincho, endereço sem o número)
      → "Ainda faltam estes dados para acionar: local numero; local bairro."

Dois identificadores com o `_` trocado por espaço, no meio de uma frase em
português — e é esse texto que o agente repete ao segurado. É o defeito que a
SPEC-084.2 C5 já consertou uma vez (14 traduções à mão contra 58 no vocabulário
do produto) voltando por uma porta nova: os campos do formulário **não estavam
no vocabulário de ninguém**, porque até a F2b eles não eram cobrados.

## O QUE ESTE ARQUIVO AFIRMA — cada um com a linha de controle (CLAUDE.md §9.2)

```
1. CAMPO DO FORMULÁRIO AUSENTE   a sessão NÃO nasce `ready_to_send`, e a
                                 mensagem ao agente NOMEIA o campo com o rótulo
                                 que a seguradora usa na tela.
                                 🔴 CONTROLE: com o campo presente, NASCE.

2. ESCOLHA FECHADA FORA DA LISTA recusa + os títulos que a seguradora aceita,
                                 com a PERGUNTA da tela.
                                 🔴 CONTROLE 1: valor de dentro da lista passa.
                                 🔴 CONTROLE 2: o mesmo valor ruim numa tela que
                                 a seguradora NÃO mostra não é cobrado.

3. `sem_chute` (lat/long)        nunca vira pergunta ao segurado; quando a tela
                                 chega, o caso vai a uma pessoa com o motivo
                                 escrito e NADA é enviado.
                                 🔴 CONTROLE: campo normal ausente APARECE como
                                 pergunta.

4. ESCOPO                        subserviço que não abre aquele formulário não
                                 passa a ser cobrado por ele.
                                 🔴 CONTROLE: o que abre continua sendo cobrado.

5. O PIN DE LOCALIZAÇÃO          o par de coordenadas do pin do WhatsApp entra
                                 no acionamento, normalizado.
                                 🔴 CONTROLE: `(0,0)`, meio par e valor fora da
                                 faixa NÃO viajam, e o texto ensina a pedir o pin.
                                 📊 E fica medido o que falta para a Porto FECHAR:
                                 uma linha no mapa, no arquivo da F2b.

6. P-F2b-01                      cada seguradora ecoa o nome do PRÓPRIO
                                 formulário (um schema, dois ids).
                                 🔴 CONTROLE: os dois nomes são diferentes.
```

🔴 **Tudo aqui chama O MOTOR** — `InsurerDispatchTool._run`,
`new_dispatch_session`, `missing_slots_for_subservice`,
`_responder_formulario_nativo` — nunca um helper deste arquivo. Teste que chama
o regex guarda o regex (CLAUDE.md §9.4).

## ⚠️ O QUE ESTE ARQUIVO **NÃO** AFIRMA

📊 Medido em 26/09/2026, depois da última redação da F2b
(`corridor_playbooks.py:9983`): um formulário que tem **qualquer** chave
`sem_chute` é saltado INTEIRO pelo portão — *"este formulário não fecha nem com
o caso inteiro preenchido"*. Como `latitude`/`longitude` da Porto são
`sem_chute`, **os seis campos de endereço da Porto não são cobrados na coleta**:
`porto/auto/guincho` nasce `ready_to_send` e o caso vai a uma pessoa **na tela do
formulário**, com o motivo escrito.

Por isso a afirmação nº 1 se prova na família HDI/Yelum, onde o formulário fecha,
e a Porto é medida onde ela está: o handoff honesto da afirmação nº 3. Se a
decisão da F2b mudar (cobrar o endereço e ir a uma pessoa só pela coordenada),
este arquivo continua válido — e a Porto ganha a asserção nº 1 também.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: 📊 A família que tem formulário QUE FECHA: as 6 capturas com schema de
#: `observed_events` (1 hdi + 5 yelum), o registro `_FLOW_CONDICOES_VEICULO_V2`.
HDI_AUTO = "hdi-auto-whatsapp@v1"
YELUM_AUTO = "yelum-auto-whatsapp@v3"
PORTO_AUTO = "porto-auto-whatsapp@v1"
#: 📊 O formulário de endereço da Porto, captura de 21/09/2026 10:24 (F2a).
FLOW_PORTO_ENDERECO = "709854848132894"


def _carregar(dotted: str, rel: str):
    """Carrega pelo caminho, sem passar por `app.agents.__init__` (langgraph)."""
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location(dotted, RAIZ / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
DS = _carregar("app.services.insurer_dispatch_service",
               "app/services/insurer_dispatch_service.py")
TOOL = _carregar("app.agents.tools.insurer_dispatch_tool",
                 "app/agents/tools/insurer_dispatch_tool.py")

#: Um caso de guincho com tudo verdadeiro: CPF que fecha a conta, placa em
#: formato legal, celular real de Florianópolis (o `CASO_COMPLETO` do repo).
#: ⚠️ Nada aqui é de segurado real nem de corretora nenhuma (CLAUDE.md §13.9).
CASO_AUTO = {
    "titular_cpf": "52998224725",
    "veiculo_placa": "ABC1D23",
    "local_atual": "Rua Bocaiuva, 2468, Centro, Florianopolis - SC, 88015-530",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose - SC",
    "problema_descricao": "o carro nao liga",
    "telefone_contato": "48991234567",
    "pessoa_no_local": "quem esta com o veiculo",
    "local_seguro": "sim",
    "quando": "agora",
}
#: As três respostas do formulário da família HDI/Yelum, com os títulos LITERAIS
#: da tela (📊 `rb_EmGaragemOuEstacionamento`, `rb_NivelDaRua`,
#: `rb_InformacoesLocal` — captura de 18/07/2026).
FORMULARIO_RESPONDIDO = {
    "veiculo_em_garagem": "Sim",
    "veiculo_nivel_rua": "Nível da rua - com acesso livre",
    "local_situacao": "Local Seguro",
}

#: Um nome de campo solto dentro de uma frase — `local_numero`, `rb_NivelDaRua`.
#: 🔴 É o vazamento que a §12.1 chama de causa: o texto errado é sintoma.
_CHAVE_CRUA = re.compile(r"\b[a-z]{3,}(?:_[a-z]{2,}){1,}\b")


def _sessao(ref: str, sub: str, **troca) -> dict:
    slots = dict(CASO_AUTO)
    slots.update(troca)
    return DS.new_dispatch_session(case_id="guarda-f3", company_id="guarda-f3",
                                   playbook_ref=ref, subservice=sub, slots=slots)


def _acionar(ref_insurer: str, sub: str, **troca) -> dict:
    """A ferramenta como o runtime a chama. `_run` NUNCA envia nada."""
    kwargs = dict(CASO_AUTO)
    kwargs.update({"insurer_key": ref_insurer, "line_kind": "auto",
                   "subservice": sub, "dados_confirmados": True})
    kwargs.update(troca)
    return TOOL.InsurerDispatchTool(company_id="corretora-A")._run(**kwargs)


# ===========================================================================
# 1 · CAMPO OBRIGATÓRIO DO FORMULÁRIO AUSENTE → NÃO NASCE PRONTA
# ===========================================================================

def test_1_campo_do_formulario_ausente_NAO_nasce_ready_to_send():
    """📊 `local_situacao` é o slot de `rb_InformacoesLocal` — *"Qual é a
    situação do local onde você está?"*. Sem ele a resposta do formulário não
    fecha, e uma sessão que nasce pronta morre no meio com a URA rodando."""
    sessao = _sessao(HDI_AUTO, "guincho",
                     **{k: v for k, v in FORMULARIO_RESPONDIDO.items()
                        if k != "local_situacao"})
    assert sessao["state"] != "ready_to_send", (
        "a sessão nasceu pronta sem o campo que o formulário exige — é o defeito "
        "de 03/08/2026 com outra roupa: %r" % sessao["state"])
    assert "local_situacao" in sessao["missing_slots"], sessao["missing_slots"]


def test_1_CONTROLE_com_o_campo_presente_a_sessao_NASCE_pronta():
    """🔴 Sem esta linha, um portão que recusasse TUDO passaria no teste acima."""
    sessao = _sessao(HDI_AUTO, "guincho", **FORMULARIO_RESPONDIDO)
    assert sessao["state"] == "ready_to_send", (sessao["state"],
                                               sessao["missing_slots"])
    assert sessao["missing_slots"] == [], sessao["missing_slots"]


def test_1_a_mensagem_ao_agente_NOMEIA_o_campo_com_o_rotulo_da_seguradora():
    """A frase que o agente repete ao segurado. 📊 Antes desta fatia o ramo do
    formulário caía no fallback `s.replace("_", " ")` e devolvia "local
    situacao"; agora traz a pergunta da tela, entre aspas, ao lado da redação do
    produto."""
    r = _acionar("hdi", "guincho",
                 **{k: v for k, v in FORMULARIO_RESPONDIDO.items()
                    if k != "local_situacao"})
    assert r["status"] == "missing_data", r
    texto = r["content"]
    assert "Qual é a situação do local onde você está?" in texto, texto
    assert "uma informação por" in texto.lower(), (
        "o Founder pediu UMA informação por vez, e a instrução tem de estar no "
        "texto que o agente lê: %s" % texto)
    sobrando = [c for c in _CHAVE_CRUA.findall(texto)
                if c not in ("insurer_key", "line_kind")]
    assert not sobrando, (
        "nome de campo cru vazou na frase que o agente repete ao segurado: %r"
        % sobrando)


def test_1_a_lista_do_que_vem_pela_frente_e_LIDA_do_corredor():
    """`o_que_a_seguradora_vai_pedir` responde por subserviço, pelo motor.

    📊 E as duas seguradoras diferem, que é o ponto: a HDI abre formulário no
    guincho e pede três coisas mais; a Porto, no mesmo guincho, não pede
    nenhuma delas."""
    hdi = DS.o_que_a_seguradora_vai_pedir(HDI_AUTO, "guincho")
    porto = DS.o_que_a_seguradora_vai_pedir(PORTO_AUTO, "guincho")
    assert any("nível da rua" in p for p in hdi), hdi
    assert not any("nível da rua" in p for p in porto), porto
    # ⚠️ A pergunta vem com o rótulo DA TELA — prova de que foi lida, e não
    #    escrita à mão neste arquivo nem no arquivo da ferramenta.
    assert any("Em relação ao nível da rua, onde o veículo está?" in p
               for p in hdi), hdi
    # Rota que a seguradora não faz por este canal: não falta dado, falta
    # caminho — e a lista fica vazia em vez de inventar pergunta.
    assert DS.o_que_a_seguradora_vai_pedir(HDI_AUTO, "colisao") == []


# ===========================================================================
# 2 · ESCOLHA FECHADA: RECUSA COM AS OPÇÕES DA SEGURADORA
# ===========================================================================

def test_2_valor_fora_da_lista_e_recusado_COM_os_titulos_aceitos():
    """📊 `rb_NivelDaRua` escolhe o EQUIPAMENTO que vem (plataforma, asa delta,
    munck). Um valor que a tela não tem não pode virar o padrão — e a recusa
    precisa dizer QUAIS são as opções, senão o agente reenvia o mesmo valor e o
    portão bloqueia de novo, com o segurado esperando (achado do juiz 4)."""
    r = _acionar("hdi", "guincho", **{**FORMULARIO_RESPONDIDO,
                                      "veiculo_nivel_rua": "no meio da rua"})
    assert r["status"] == "missing_data", r
    assert r["missing"] == ["veiculo_nivel_rua"], r["missing"]
    texto = r["content"]
    for titulo in ("Subsolo", "Acima do nível da rua",
                   "Nível da rua - com restrição de acesso",
                   "Nível da rua - com acesso livre"):
        assert titulo in texto, (titulo, texto)
    assert "Em relação ao nível da rua, onde o veículo está?" in texto, texto
    assert "veiculo_nivel_rua" not in texto, (
        "o nome interno do campo chegou ao texto que o agente lê: %s" % texto)


def test_2_CONTROLE_valor_de_DENTRO_da_lista_passa():
    """🔴 Uma conferência que recusasse tudo passaria no teste acima."""
    r = _acionar("hdi", "guincho", **{**FORMULARIO_RESPONDIDO,
                                      "veiculo_nivel_rua": "Subsolo"})
    assert r["status"] == "ready_to_send", str(r)[:200]


def test_2_CONTROLE_tela_que_a_seguradora_NAO_mostra_nao_e_cobrada():
    """🔴 O achado do juiz 4 um nível abaixo — não "rota que não vê o
    formulário", mas CAMPO QUE A TELA NÃO PERGUNTA.

    📊 `rb_NivelDaRua` declara `visible_if: rb_EmGaragemOuEstacionamento == "1"`:
    a pergunta do nível da rua só existe para carro EM GARAGEM. Com
    `veiculo_em_garagem="Não"` ela não aparece — e cobrar resposta de tela que
    não aparece é interrogatório à toa. 📊 Medido em 26/09: das 73 rotas × 4
    estados de slot, são exatamente 2 as respostas que mudaram quando o laço
    duplicado de `new_dispatch_session` saiu, e são estas duas.
    """
    for ref in (HDI_AUTO, YELUM_AUTO):
        sessao = _sessao(ref, "guincho", **{**FORMULARIO_RESPONDIDO,
                                            "veiculo_em_garagem": "Não",
                                            "veiculo_nivel_rua": "no meio da rua"})
        assert "veiculo_nivel_rua" not in sessao["missing_slots"], (
            ref, sessao["missing_slots"])
        assert sessao["state"] == "ready_to_send", (ref, sessao["state"],
                                                   sessao["missing_slots"])


# ===========================================================================
# 3 · `sem_chute`: HANDOFF COM O MOTIVO ESCRITO, NUNCA INTERROGATÓRIO
# ===========================================================================

def test_3_coordenada_NUNCA_vira_pergunta_ao_segurado():
    """🔴 Ninguém sabe responder a própria latitude.

    📊 As 3 de 3 capturas da Porto trazem `latitude`/`longitude`, e o backend tem
    ZERO geocodificadores (`grep -rln "geocod|viacep|nominatim" backend/app` → 0).
    O mapa as declara `origem: sem_chute` — e a varredura abaixo é de TODAS as
    rotas de TODOS os corredores, não só da Porto.
    """
    perguntou = []
    for ref in PB.list_playbooks():
        pb = PB.get_playbook(ref) or {}
        for sub in (pb.get("subservices") or {}):
            for frase in DS.o_que_a_seguradora_vai_pedir(ref, sub):
                if re.search(r"latitude|longitude|coordenada", frase, re.I):
                    perguntou.append((ref, sub, frase))
    assert not perguntou, (
        "o produto pediria coordenada a um ser humano: %r" % perguntou[:3])


def test_3_CONTROLE_campo_normal_ausente_APARECE_como_pergunta():
    """🔴 Sem esta linha, uma lista sempre vazia passaria no teste acima."""
    hdi = DS.o_que_a_seguradora_vai_pedir(HDI_AUTO, "guincho")
    assert len(hdi) >= 8, hdi
    assert any("situação do local" in p or "lugar onde ele está" in p
               for p in hdi), hdi


def test_3_o_formulario_sem_fonte_vai_a_UMA_PESSOA_com_o_motivo_escrito():
    """A tela da Porto chega, a resposta não sai, e o motivo é NOMEADO.

    📊 Antes desta fatia o motivo era `formulario_incompleto:latitude,longitude`
    — a frase que a atendente lê é *"o formulário pede um dado que o caso não
    tem"*, e ela vai PROCURAR o dado. Não existe dado para procurar: o
    geocodificador é do Flow da seguradora. `sem_chute` é o motivo que o produto
    já usa para isto, e ele NOMEIA os campos no cartão do handoff.
    """
    sessao = _sessao(PORTO_AUTO, "guincho")
    sessao["state"] = "ura"
    sessao["flow_token"] = "token-de-teste"
    enviados: list = []
    saida = DS._responder_formulario_nativo(
        sessao, PB.get_playbook(PORTO_AUTO),
        "Para seguir, preencha o formulário com o endereço.",
        interactive={"kind": "flow", "flow": {"flow_id": FLOW_PORTO_ENDERECO}},
        flow_sender=lambda **k: enviados.append(k) or True)
    assert saida is not None, "a tela do formulário da Porto não foi reconhecida"
    assert saida["state"] == "needs_human", saida.get("state")
    assert str(saida.get("reason") or "").startswith("sem_chute:"), saida.get("reason")
    assert "latitude" in saida["reason"] and "longitude" in saida["reason"], saida["reason"]
    assert not enviados, (
        "⛔ alguma coisa foi enviada à seguradora com o formulário incompleto: %r"
        % enviados)
    # 🔴 Zero inventado é o Golfo da Guiné: a resposta não pode ter sido montada.
    assert (saida.get("flow_resposta") or {}).get("params") is None, saida.get("flow_resposta")
    frase = DS.motivo_em_portugues(saida["reason"])
    assert "não responde o que não sabe" in frase, frase
    assert "sem_chute" not in frase, frase


# ===========================================================================
# 4 · O ESCOPO — quem não vê a tela não é cobrado
# ===========================================================================

def test_4_subservico_que_nao_abre_o_formulario_nao_passa_a_ser_cobrado():
    """📊 O critério é o `subservicos_observados` do mapa (F2b), medido no corpus
    de telas reais: o formulário de CONDIÇÕES DO VEÍCULO só aparece em guincho;
    o de LOCAL aparece em guincho, chaveiro, pneu e socorro mecânico.

    🔴 `bateria` não abre nenhum dos dois — e cobrar dela o nível da rua seria o
    *"interrogatório à toa"* que o juiz 4 já reprovou.
    """
    vazio = {"slots": {}}
    pb = PB.get_playbook(HDI_AUTO)
    bateria = PB.missing_slots_for_subservice(pb, "bateria", dict(vazio["slots"]))
    guincho = PB.missing_slots_for_subservice(pb, "guincho", dict(vazio["slots"]))
    for campo in ("veiculo_em_garagem", "veiculo_nivel_rua", "local_situacao"):
        assert campo not in bateria, (campo, bateria)
        # 🔴 CONTROLE: quem VÊ a tela continua sendo cobrado — sem isto, um
        #    portão que parasse de cobrar formulário passaria neste teste.
        assert campo in guincho, (campo, guincho)


def test_4_a_confirmacao_do_AUTO_ja_diz_o_que_ainda_falta():
    """📊 O ramo `confirm_first` devolve ANTES do plano: em AUTO, a primeira
    chamada sempre manda confirmar, mesmo faltando seis dados. O segurado era
    interrompido duas vezes, e a segunda depois de já ter dito "pode acionar".
    A ordem não muda; a mensagem passa a levar o que falta junto."""
    r = TOOL.InsurerDispatchTool(company_id="corretora-A")._run(
        **{"insurer_key": "hdi", "line_kind": "auto", "subservice": "guincho",
           "titular_cpf": CASO_AUTO["titular_cpf"],
           "veiculo_placa": CASO_AUTO["veiculo_placa"]})
    assert r["status"] == "confirm_first", r
    assert "ainda FALTAM" in r["content"], r["content"][-400:]
    assert "situação do local" in r["content"], r["content"][-400:]
    # E continua proibindo afirmar acionamento — a linha que a SPEC-031 guarda.
    assert "PROIBIDO dizer ao cliente" in r["content"]


def test_5_o_pin_de_localizacao_chega_ao_acionamento_normalizado():
    """🔴 A coordenada não se pergunta: ela vem de UM TOQUE no WhatsApp.

    📊 O produto já converte o `locationMessage` em texto para o agente desde
    03/08/2026 (`whatsapp/evolution_inbound.py`), com 6 casas decimais:
    *"Localização compartilhada: -27.588016,-48.544253"*. O que faltava era o
    acionamento ter ONDE receber o par — e é uma pergunta em vez de seis
    (rua, número, bairro, cidade, estado, CEP), a que o segurado responde num
    acostamento.
    """
    _sub, slots = TOOL.InsurerDispatchTool(company_id="corretora-A")._extract_slots(
        dict(CASO_AUTO, subservice="guincho",
             local_latitude="-27,588016", local_longitude="-48,544253"))
    # ⚠️ Vírgula decimal é o que um teclado brasileiro produz; a seguradora
    #    recebe ponto. Normalizar numa fonte só vale para `_run` e `_arun`.
    assert slots["local_latitude"] == "-27.588016", slots.get("local_latitude")
    assert slots["local_longitude"] == "-48.544253", slots.get("local_longitude")
    r = _acionar("porto", "guincho", local_latitude="-27.588016",
                 local_longitude="-48.544253")
    assert r["status"] == "ready_to_send", str(r)[:200]


def test_5_CONTROLE_zero_e_meio_par_NAO_viajam_e_o_texto_pede_o_PIN():
    """⛔ `(0, 0)` é o default do protobuf, não um lugar: é o Golfo da Guiné — e a
    URA aceitaria calada. Meio par não localiza nada. Coordenada deduzida de
    endereço é invenção com cara de precisão.

    🔴 E a recusa tem de ENSINAR o caminho honesto: pedir o pin.
    """
    ferramenta = TOOL.InsurerDispatchTool(company_id="corretora-A")
    for lat, lon, apelido in (("0", "0", "zero"),
                              ("-27.588016", "", "meio par"),
                              ("-127.5", "-48.5", "fora da faixa do planeta")):
        r = _acionar("porto", "guincho", local_latitude=lat, local_longitude=lon)
        assert r["status"] == "missing_data", (apelido, str(r)[:160])
        assert "Localização" in r["content"] and "clipe" in r["content"], (
            apelido, r["content"][:200])
        _sub, slots = ferramenta._extract_slots(
            dict(CASO_AUTO, subservice="guincho",
                 local_latitude=lat, local_longitude=lon))
        assert "local_latitude" not in slots and "local_longitude" not in slots, (
            "⛔ coordenada desonesta entrou nos slots (%s): %r"
            % (apelido, {k: v for k, v in slots.items() if "lat" in k or "long" in k}))
    # 🔴 CONTROLE do controle: o par honesto continua entrando.
    _sub, bons = ferramenta._extract_slots(
        dict(CASO_AUTO, subservice="guincho",
             local_latitude="-27.588016", local_longitude="-48.544253"))
    assert bons.get("local_latitude") == "-27.588016", bons.get("local_latitude")


def test_5_o_MAPA_da_porto_ainda_declara_a_coordenada_SEM_FONTE__BLOQUEIO():
    """📊 O que falta para a Porto fechar, medido em 26/09/2026 — e é UMA LINHA,
    no arquivo da fatia F2b (`corridor_playbooks.py`), que esta fatia não toca.

    Hoje o mapa declara::

        "latitude":  {"origem": "sem_chute", ...}
        "longitude": {"origem": "sem_chute", ...}

    e `montar_resposta_de_flow` nunca lê slot nenhum para essa origem — então
    **mesmo com o par do pin nos slots** a resposta não fecha, e o caso vai a uma
    pessoa (é o que o teste nº 3 prova).

    🔴 Com a origem declarada (`{"origem": "slot", "slot": "local_latitude"}`), o
    formulário FECHA: é o que a segunda metade deste teste mede, sobre uma CÓPIA
    do mapa real — nada aqui é inventado.

    ⚠️ Quando a F2b (ou quem costurar) declarar a origem, **esta primeira
    asserção fica VERMELHA de propósito**: apague-a e mova a prova para o teste
    nº 5, que passa a exigir `ok=True` no mapa de verdade.
    """
    import copy

    flow = PB.get_playbook(PORTO_AUTO)["native_flows"][FLOW_PORTO_ENDERECO]
    obrigatorias = (flow.get("resposta") or {}).get("obrigatorias") or {}
    assert obrigatorias["latitude"]["origem"] == "sem_chute", (
        "🔴 o mapa passou a declarar a origem da latitude — apague esta asserção "
        "e exija `ok=True` no mapa REAL: %r" % obrigatorias["latitude"])

    slots_com_pin = dict(CASO_AUTO, local_latitude="-27.588016",
                         local_longitude="-48.544253")
    sessao = DS.new_dispatch_session(case_id="guarda-f3", company_id="guarda-f3",
                                     playbook_ref=PORTO_AUTO, subservice="guincho",
                                     slots=slots_com_pin)
    # No mapa REAL: não fecha, e o motivo é `sem_chute` (nunca zero, nunca chute).
    real = PB.montar_resposta_de_flow(flow, sessao["slots"],
                                      flow_id=FLOW_PORTO_ENDERECO)
    assert real["ok"] is False and real["missing"] == ["latitude", "longitude"], real
    # Na CÓPIA com a origem declarada: fecha, com as 10 chaves das 3 capturas.
    como_seria = copy.deepcopy(flow)
    como_seria["resposta"]["obrigatorias"]["latitude"] = {
        "origem": "slot", "slot": "local_latitude"}
    como_seria["resposta"]["obrigatorias"]["longitude"] = {
        "origem": "slot", "slot": "local_longitude"}
    fecha = PB.montar_resposta_de_flow(como_seria, sessao["slots"],
                                       flow_id=FLOW_PORTO_ENDERECO)
    assert fecha["ok"] is True, fecha["missing_detail"]
    assert set(fecha["params"]) == {
        "rua", "numero_residencia", "bairro", "cidade", "estado", "cep",
        "referencia", "label_endereco_completo", "latitude", "longitude"}, fecha["params"]
    assert fecha["params"]["latitude"] == "-27.588016", fecha["params"]


def test_6_P_F2b_01_cada_seguradora_ecoa_o_NOME_do_proprio_formulario():
    """📊 Um registro de schema, DOIS ids: `857030507196739` (HDI) e
    `3206000179602236` (Yelum) — e o nome real tem sufixo de versão diferente por
    id (`…_1783714513857` × `…_1783714477612`).

    Sem passar o `flow_id` à montagem, `_nome_do_flow` cai no caso *"schema
    compartilhado e ninguém disse qual id"* e devolve VAZIO: a moldura descarta a
    chave e **nenhuma das duas** recebe nome. 🔴 A P-F2b-01 é este argumento.
    """
    vistos = {}
    for ref, flow_id in ((HDI_AUTO, "857030507196739"),
                         (YELUM_AUTO, "3206000179602236")):
        sessao = _sessao(ref, "guincho", **FORMULARIO_RESPONDIDO)
        sessao["state"] = "ura"
        sessao["flow_token"] = "token-de-teste"
        sessao["flow_cta"] = "Informar condições"
        saida = DS._responder_formulario_nativo(
            sessao, PB.get_playbook(ref),
            "precisamos entender o local e as condicoes do veiculo",
            interactive={"kind": "flow", "flow": {"flow_id": flow_id}},
            flow_sender=lambda **k: True)
        moldura = DS._moldura_da_resposta(saida, saida["flow_resposta"])
        assert moldura["flow_id"] == flow_id, (ref, moldura)
        assert moldura.get("flow_name"), (
            "%s não ecoou nome de formulário nenhum — é a P-F2b-01: %r"
            % (ref, moldura))
        vistos[ref] = moldura["flow_name"]
    # 🔴 CONTROLE: os dois nomes são DIFERENTES. Sem esta linha, ecoar o nome da
    #    HDI para a Yelum — o defeito original — passaria no teste acima.
    assert vistos[HDI_AUTO] != vistos[YELUM_AUTO], vistos
    assert vistos[HDI_AUTO].endswith("_1783714513857"), vistos[HDI_AUTO]
    assert vistos[YELUM_AUTO].endswith("_1783714477612"), vistos[YELUM_AUTO]


def test_4_CONTROLE_a_confirmacao_completa_NAO_inventa_falta():
    """🔴 Sem esta linha, um aviso que aparecesse sempre passaria acima."""
    r = TOOL.InsurerDispatchTool(company_id="corretora-A")._run(
        **{**CASO_AUTO, **FORMULARIO_RESPONDIDO, "insurer_key": "hdi",
           "line_kind": "auto", "subservice": "guincho"})
    assert r["status"] == "confirm_first", r
    assert "ainda FALTAM" not in r["content"], r["content"][-300:]
    assert r.get("missing") == [], r.get("missing")
