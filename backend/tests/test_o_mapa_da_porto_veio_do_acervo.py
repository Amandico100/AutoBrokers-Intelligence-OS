# -*- coding: utf-8 -*-
"""O mapa do formulário da Porto veio do ACERVO — SPEC-118, fatia F2a.

📊 **O defeito que este arquivo impede** é o que o próprio corredor da Porto
fazia até 26/09/2026: o formulário nativo chegava com `flow_id`
`709854848132894`, nenhum playbook o conhecia, e o acionamento virava
`needs_human` **no último portão antes do protocolo** — depois de a URA já ter
respondido tudo.

Mas o defeito PIOR não é esse; é o que se abre ao consertá-lo. São quatro, e
cada teste aqui fecha um:

```
1. mapa INVENTADO          um schema sem procedência tem cara de medição e
                           responde ids que a seguradora nunca publicou
2. PESQUISA respondida      a Porto abre DOIS flows; o segundo é satisfação.
                           Respondê-lo é mentir à seguradora sobre um atendimento
3. flow DESCONHECIDO        um id que ninguém mapeou não pode ser chutado
4. RESPOSTA PELA METADE     a Porto consome 10 chaves; mandar 7 é abrir o
                           chamado sem o endereço inteiro
```

## 🔴 O QUE ESTE ARQUIVO **NÃO** AFIRMA (e é metade do valor dele)

📊 Medido em 26/09/2026, com o motor real — ANTES da fatia da lógica (F2b):

```
montar_resposta_de_flow(<mapa da Porto>, <slots do caso>)
  → ok=False, missing=[rua, numero_residencia, complemento, bairro,
                       cidade, estado, ponto_referencia]   motivo: valor_nao_reconhecido
```

O montador resolvia valor **só por lista de opções** (`_resolver_opcao_de_flow`);
um componente de TEXTO com valor real caía em `valor_nao_reconhecido`.

🔴 **A F2b ensinou o montador, no mesmo dia**, e a medição virou:

```
  → ok=False, missing=['latitude', 'longitude']            motivo: sem_chute
```

⚠️ **A afirmação deste arquivo continua a mesma, e é a que importa: o mapa da
Porto, sozinho, NÃO responde.** O que mudou é o motivo — de "o valor do caso não
serve" (que era falso) para "faltam as duas coordenadas que o Flow da Porto
geocodifica e que nós não temos de onde tirar". `test_o_montador_JA_responde_
texto_e_o_que_falta_e_a_COORDENADA` guarda isso, e a prova positiva do texto está
em `test_o_montador_responde_texto_e_o_portao_cobra_antes.py` (§9.3: quando o
fato muda, o teste muda com ele, e a lição migra em vez de morrer).
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
FIXTURE = RAIZ / "tests" / "fixtures" / "formulario_porto_21_09.json"


def _carregar(nome: str, caminho: Path):
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


PB = _carregar("_spec118_pb", PLAYBOOKS_PY)
M = _carregar("_spec118_motor", MOTOR_PY)

#: 📊 Os dois flows REAIS da Porto, medidos em `observed_events` (26/09/2026).
FLOW_ENDERECO = "709854848132894"
FLOW_PESQUISA = "1263063458275481"
#: Um id que nenhuma seguradora publicou — a LINHA DE CONTROLE.
FLOW_INVENTADO = "9999999999999999"

REF_PORTO = "porto-auto-whatsapp@v1"

CAPTURA = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _porto():
    pb = PB.get_playbook(REF_PORTO)
    assert pb, f"o corredor {REF_PORTO} sumiu"
    return pb


# ---------------------------------------------------------------------------
# 1. O MAPA EXISTE, E É O DO FLOW DO ACERVO
# ---------------------------------------------------------------------------

def test_o_motor_devolve_o_mapa_da_porto_pelo_flow_id_do_acervo():
    """O que a seguradora manda é o `flow_id`; é por ele que o mapa se acha.

    📊 6 de 6 convites da Porto trazem `interactive.flow.flow_id` — por isso
    este é o canal de detecção dela, e não a âncora de texto."""
    flow = PB.native_flow(_porto(), FLOW_ENDERECO)
    assert flow, ("o corredor da Porto não conhece o formulário de endereço — "
                  "todo acionamento de auto que o abrir para no último portão")
    assert flow["flow_id"] == FLOW_ENDERECO
    assert flow["flow_name"] == CAPTURA["flow"]["flow_name"], (
        "o nome do formulário divergiu da captura; ele é ECOADO para a "
        "seguradora em `wa_flow_response_params`")
    assert flow["envelope"] == CAPTURA["envelope"]["name"] == "galaxy_message", (
        "o envelope se ECOA da captura ('galaxy_message'), nunca se adivinha")


def test_os_campos_e_os_rotulos_sao_os_da_CAPTURA_nao_de_uma_tela_parecida():
    """§9.4 — o texto da tela vem do acervo, não da imaginação.

    Cada componente do mapa tem de existir na captura, com o MESMO rótulo. Um
    campo a mais aqui é um campo inventado; um a menos é um campo que a Porto
    pede e o produto nunca vai mandar."""
    flow = PB.native_flow(_porto(), FLOW_ENDERECO)
    do_mapa = {str(c["name"]): str(c.get("label") or "")
               for _t, c in PB._flow_components(flow)}
    do_acervo = {str(f["name"]): str(f.get("label") or "")
                 for f in CAPTURA["fields_do_acervo"]}
    assert set(do_mapa) == set(do_acervo), (
        f"campos que só existem no mapa: {sorted(set(do_mapa) - set(do_acervo))} · "
        f"campos do acervo que o mapa esqueceu: {sorted(set(do_acervo) - set(do_mapa))}")
    for nome, rotulo in do_acervo.items():
        assert do_mapa[nome] == rotulo, (
            f"o rótulo de {nome} foi reescrito: {do_mapa[nome]!r} != {rotulo!r}")


def test_a_porto_NAO_declara_ancora_de_texto_e_o_motivo_e_medido():
    """📊 A frase que abre o formulário é "Selecione o botão:" — e ela aparece em
    **37** mensagens da Porto, das quais só **6** são o convite.

    Uma `prompt_anchor` com essa frase levaria 31 telas (84%) ao caminho do
    formulário, inclusive telas que hoje um passo de URA responde — e chegaria à
    régua das 73 rotas por `scripts/replay.py` (`detect_native_flow`).

    ⚠️ A verificação é sobre a FORMA da declaração (§9.4, exceção), e logo
    abaixo o MOTOR confirma o efeito: nenhuma âncora, nenhuma detecção por texto.
    """
    flow = PB.native_flow(_porto(), FLOW_ENDERECO)
    assert not flow.get("prompt_anchor"), (
        "o mapa da Porto declarou âncora de texto — meça antes: "
        "`select count(*) ... where text ~* 'selecione o bot[aã]o'` deu 37, "
        "com 6 convites")
    for texto in ("Selecione o botão:",
                  "Selecione o botão:\n[FORMULARIO NATIVO: Preencher]"):
        assert PB.detect_native_flow(_porto(), texto) is None, (
            f"o motor achou formulário no texto {texto!r} — é a tela de QUALQUER "
            "botão da Porto")


def test_CONTROLE_a_deteccao_por_texto_CONSEGUE_funcionar():
    """§9.3 — prove que o `None` acima é da Porto, e não do motor quebrado.

    A família HDI/Yelum declara `prompt_anchor` de propósito (📊 lá o marcador
    aparecia 0 vezes em 28.096 eventos: a âncora era o único canal). Se este
    teste ficar vermelho, `detect_native_flow` parou de funcionar e o teste
    acima virou carimbo."""
    hdi = PB.get_playbook("hdi-auto-whatsapp@v1")
    achado = PB.detect_native_flow(
        hdi, "Para que a remoção do veículo ocorra sem imprevistos, precisamos "
             "entender o local e as condições do veículo.")
    assert achado is not None and achado.get("flow_id"), (
        "`detect_native_flow` não acha mais nem o formulário da família HDI — "
        "o teste da Porto acima deixou de provar qualquer coisa")


# ---------------------------------------------------------------------------
# 2. A PESQUISA DE SATISFAÇÃO NÃO É RESPONDÍVEL
# ---------------------------------------------------------------------------

def test_o_flow_de_PESQUISA_da_porto_nao_e_respondivel():
    """⛔ Responder um questionário de satisfação achando que é o formulário do
    chamado é mentir à seguradora sobre um atendimento.

    📊 E o risco é concreto, medido em 26/09/2026:

        montar_resposta_de_flow({"screens": []}, {}) → ok=True, params={}

    Um registro sem componentes sai APROVADO com resposta vazia. Por isso a
    pesquisa **não entra em `native_flows`**: o que garante que a resposta nunca
    é montada é `native_flow` devolver `None` para ela.
    """
    assert PB.native_flow(_porto(), FLOW_PESQUISA) is None, (
        "a pesquisa de satisfação entrou em `native_flows` — o produto pode "
        "montar uma resposta vazia e mandá-la à Porto")
    declarado = (_porto().get("flows_nao_respondiveis") or {}).get(FLOW_PESQUISA)
    assert declarado, ("o flow da pesquisa não está declarado como "
                       "não-respondível; sem isso ele volta a ser 'desconhecido' "
                       "e o caso vira trabalho para uma pessoa")
    assert declarado.get("motivo") == "pesquisa_de_satisfacao"
    assert declarado.get("tratamento") == "noop", (
        "pesquisa não é handoff: é para ignorar, como já se ignora no texto")
    assert declarado.get("observed"), "declaração sem procedência"


def test_a_pesquisa_e_COERENTE_com_o_que_o_motor_ja_faz_por_texto():
    """🔴 Não se reimplementa `_SURVEY_NOOP_RE` — confere-se que a MESMA frase do
    convite da pesquisa é a que o motor já reconhece quando ela chega como texto.

    📊 O texto dos 8 convites é "A sua opinião é muito importante! Clique no
    botão abaixo e avalie."
    """
    frase = "A sua opinião é muito importante! Clique no botão abaixo e avalie."
    assert re.search(M._SURVEY_NOOP_RE, M._norm_text(frase), re.IGNORECASE), (
        "a frase do convite de pesquisa da Porto não casa `_SURVEY_NOOP_RE` — "
        "a declaração do mapa e o motor deixaram de falar da mesma coisa")
    assert not re.search(M._SURVEY_NOOP_RE, M._norm_text("Selecione o botão:"),
                         re.IGNORECASE), (
        "🔴 CONTROLE: o convite do FORMULÁRIO casou a regra de pesquisa — o "
        "produto ignoraria justamente a tela que precisa responder")


# ---------------------------------------------------------------------------
# 3. 🔴 A LINHA DE CONTROLE — O QUE NÃO SE CONHECE, NÃO SE CHUTA
# ---------------------------------------------------------------------------

def test_CONTROLE_um_flow_id_desconhecido_devolve_NADA_e_o_corredor_nao_chuta():
    """🔴 Sem esta asserção o arquivo não prova nada: um motor que devolvesse o
    mapa da Porto para QUALQUER id passaria em todos os testes acima.

    E a segunda metade é o efeito no produto: id desconhecido não escorrega
    calado, vira `needs_human` **com o motivo gravado**."""
    assert PB.native_flow(_porto(), FLOW_INVENTADO) is None, (
        "um `flow_id` que ninguém publicou devolveu schema — o produto acabou "
        "de responder um formulário que não conhece")
    assert PB.native_flow(_porto(), "") is None
    assert PB.native_flow(_porto(), None) is None

    sessao = {"state": "ura", "slots": {}}
    saida = M._responder_formulario_nativo(
        sessao, _porto(), "[FORMULARIO NATIVO: Preencher]",
        interactive={"kind": "flow",
                     "flow": {"flow_id": FLOW_INVENTADO, "flow_token": "t:1:2",
                              "name": "galaxy_message", "cta": "Preencher"}})
    assert saida is not None, "o formulário desconhecido escorregou como se não fosse um"
    assert saida["state"] == "needs_human", f"estado={saida['state']!r}"
    assert saida["reason"] == "formulario_nativo_desconhecido", (
        f"motivo={saida.get('reason')!r}")


def test_CONTROLE_o_flow_CONHECIDO_da_porto_chega_ao_montador():
    """§9.3 — prove que a recusa acima é sobre o id, e não sobre tudo.

    Com o id REAL, o corredor deixa de dizer "desconhecido": ele tenta montar a
    resposta. 📊 Hoje ele para em `formulario_incompleto` (o montador não sabe
    texto); o que este teste guarda é que o caminho mudou de classe — de "não
    sei o que é isto" para "sei o que é, e falta dado"."""
    sessao = {"state": "ura", "slots": dict(CAPTURA["slots_do_corredor_equivalentes"])}
    saida = M._responder_formulario_nativo(
        sessao, _porto(), "[FORMULARIO NATIVO: Preencher]",
        interactive={"kind": "flow",
                     "flow": {"flow_id": FLOW_ENDERECO, "flow_token": "t:1:2",
                              "name": "galaxy_message", "cta": "Preencher"}})
    assert saida is not None
    assert str(saida.get("reason") or "") != "formulario_nativo_desconhecido", (
        "o formulário da Porto continua desconhecido para o corredor — o mapa "
        "não está ligado ao playbook")
    assert (saida.get("flow_resposta") or {}).get("flow_id") == FLOW_ENDERECO, (
        "a montagem não registrou o formulário que respondeu")


# ---------------------------------------------------------------------------
# 4. A RESPOSTA — as chaves que a Porto consome, e o que ainda falta
# ---------------------------------------------------------------------------

def test_a_resposta_declarada_tem_as_10_chaves_de_3_em_3_capturas():
    """📊 `answers` do acervo (`observer_intake._parse_native_form`) são as chaves
    de PRIMEIRO NÍVEL do `paramsJSON` — é isso que a Porto consome, e não a lista
    de componentes.

    Dez chaves aparecem nas 3 de 3 capturas e `complemento` em 2 de 3. O mapa
    declara a origem de CADA uma: campo do formulário, slot do caso, derivada,
    ou `sem_chute`."""
    flow = PB.native_flow(_porto(), FLOW_ENDERECO)
    resposta = flow.get("resposta") or {}
    obrig = resposta.get("obrigatorias") or {}
    opc = resposta.get("opcionais") or {}
    assert set(obrig) == set(CAPTURA["chaves_da_resposta"]["presentes_em_3_de_3"]), (
        f"declaradas={sorted(obrig)} · medidas em 3 de 3="
        f"{sorted(CAPTURA['chaves_da_resposta']['presentes_em_3_de_3'])}")
    assert set(opc) == set(CAPTURA["chaves_da_resposta"]["presentes_em_2_de_3"])
    for chave, decl in {**obrig, **opc}.items():
        assert decl.get("origem") in ("campo", "slot", "derivado", "sem_chute"), (
            f"a chave {chave} não diz DE ONDE sai: {decl!r}")
        if decl["origem"] == "campo":
            nomes = {str(c["name"]) for _t, c in PB._flow_components(flow)}
            assert decl["campo"] in nomes, (
                f"{chave} aponta para o campo {decl['campo']!r}, que não existe na tela")


def test_latitude_e_longitude_vem_do_PIN_e_NUNCA_de_um_valor_fixo():
    """🔴 ESTE TESTE MIGROU EM 26/09/2026 (SPEC-118 F4) — CLAUDE.md §9.3.

    Ele exigia `origem: "sem_chute"` nas duas coordenadas, e a mensagem de falha
    dizia o que fazer quando o fato mudasse: *"se apareceu uma fonte real,
    ótimo: escreva a medição dela aqui"*. **Apareceu**, e não é geocodificador:

    📊 é o PIN do WhatsApp. `whatsapp/evolution_inbound.py:720` converte
    `locationMessage` em texto desde 03/08/2026 com 6 casas decimais, e
    `corridor_playbooks.coordenada_do_pin` lê a linha rotulada dele.

    ⚠️ **A GARANTIA É A MESMA, e ela nunca foi sobre a palavra `sem_chute`:** a
    coordenada não pode sair de um valor FIXO nem de uma dedução de endereço. Um
    zero "para completar a resposta" põe o chamado no Golfo da Guiné e a URA
    aceita calada. Agora a mesma coisa se afirma pelo outro lado — a origem é um
    SLOT, o slot vem do pin, e o par desonesto é apagado antes de chegar aqui.
    """
    resposta = (PB.native_flow(_porto(), FLOW_ENDERECO).get("resposta") or {})
    for chave, slot in (("latitude", "local_latitude"),
                        ("longitude", "local_longitude")):
        decl = (resposta.get("obrigatorias") or {}).get(chave) or {}
        assert decl.get("origem") == "slot", (
            f"{chave} tem origem {decl.get('origem')!r}. As origens aceitáveis "
            "são duas e só duas: `slot` (o par do pin, conferido por "
            "`par_de_coordenadas`) ou `sem_chute` (sem fonte → handoff com "
            "motivo). Qualquer outra é o chute que este teste existe para barrar")
        assert decl.get("slot") == slot, decl
        assert "default" not in decl and "valor" not in decl, (
            f"{chave} ganhou valor fixo no mapa: {decl!r}")
    # 🔴 E O MOTOR NÃO ACEITA O ZERO, que é a metade que importa da lição antiga.
    #    📊 Medido com `inject_address_slots`, o portão por onde TODO acionamento
    #    passa (`new_dispatch_session`): `(0,0)`, meio par e fora de faixa são
    #    APAGADOS dos slots, e o formulário cai em `sem_valor` → uma pessoa.
    from_capture = dict(CAPTURA["slots_do_corredor_equivalentes"])
    for lat, lon, apelido in (("0", "0", "o Golfo da Guiné"),
                              ("-27.588016", "", "meio par"),
                              ("-95.0", "-48.5", "fora da faixa do planeta")):
        slots = dict(from_capture, local_latitude=lat, local_longitude=lon)
        PB.inject_address_slots(slots)
        montado = PB.montar_resposta_de_flow(
            PB.native_flow(_porto(), FLOW_ENDERECO), slots)
        assert montado["ok"] is False and montado["params"] is None, (
            f"⛔ {apelido} atravessou o motor: {montado['params']!r}")
    # E o motor não pode inventá-las por outro caminho: nenhum componente da
    # tela se chama latitude/longitude, então nem um `default` de componente as
    # produziria.
    nomes = {str(c["name"]) for _t, c in
             PB._flow_components(PB.native_flow(_porto(), FLOW_ENDERECO))}
    assert not nomes & {"latitude", "longitude"}, (
        "apareceu um componente de coordenada na tela — a captura não tem")


def test_o_montador_JA_responde_texto_e_o_que_falta_e_a_COORDENADA():
    """🔴 ESTE TESTE MIGROU EM 26/09/2026 (SPEC-118 F2b) — e a lição migrou com
    ele, em vez de morrer (`CLAUDE.md` §9.3).

    O que ele afirmava, medido e verdadeiro até a fatia da lógica existir::

        montar_resposta_de_flow(<mapa da Porto>, <slots da captura>)
          → ok=False, missing=[rua, numero_residencia, complemento, bairro,
                               cidade, estado, ponto_referencia]
          motivo: valor_nao_reconhecido   (o montador só sabia LISTA DE OPÇÕES)

    📊 O que ele afirma agora, medido com o mesmo comando::

        → ok=False, missing=['latitude', 'longitude']   motivo: sem_chute

    **Os sete campos de texto saíram.** O que sobra são as duas coordenadas que o
    Flow da Porto geocodifica sozinho e que nós não temos de onde tirar (📊 0
    geocodificadores no backend) — `sem_chute`, handoff com o motivo escrito,
    ⛔ nunca zero inventado.

    ⚠️ A GARANTIA É A MESMA de antes: **o mapa da Porto, sozinho, ainda não
    responde**, e este arquivo continua dizendo isso em voz alta em vez de deixar
    alguém acreditar que o formulário está resolvido. O que mudou é que agora o
    motivo é honesto: `valor_nao_reconhecido` acusava o endereço do segurado de
    estar errado, quando o errado era o motor.

    🔴 A prova POSITIVA do texto (o corpo inteiro, com as 9 chaves que sobram)
    está em `test_o_montador_responde_texto_e_o_portao_cobra_antes.py`, com a
    linha de controle que tira as duas coordenadas de uma CÓPIA do mapa.
    """
    flow = PB.native_flow(_porto(), FLOW_ENDERECO)
    montado = PB.montar_resposta_de_flow(
        flow, dict(CAPTURA["slots_do_corredor_equivalentes"]))
    assert montado["ok"] is False and montado["params"] is None, (
        "a resposta da Porto saiu sem latitude/longitude — ou apareceu uma FONTE "
        "real para elas (então escreva a medição no mapa e migre este teste), ou "
        "alguém completou a resposta com um número inventado")
    assert montado["missing"] == ["latitude", "longitude"], (
        f"o que falta mudou: {montado['missing']} — um campo de TEXTO de volta "
        f"aqui significa que o passthrough do montador parou de funcionar")
    motivos = {d["motivo"] for d in montado["missing_detail"]}
    # 🔴 O MOTIVO MIGROU DE NOVO EM 26/09 (F4), e a lição foi COM ele.
    #    `valor_nao_reconhecido` → `sem_chute` → `sem_valor`, e cada degrau é uma
    #    frase diferente para a atendente:
    #      · `valor_nao_reconhecido`  "o endereço do segurado não serve"   (era FALSO)
    #      · `sem_chute`              "não há dado no mundo para buscar"   (era verdade)
    #      · `sem_valor`              "falta um dado, e há onde buscá-lo"  (é o pin)
    #    ⚠️ A garantia não muda: o mapa da Porto, com o CASO SEM O PIN, ainda não
    #    responde — e diz por quê, nomeando o slot que a pessoa tem de pedir.
    assert motivos == {"sem_valor"}, (
        f"o motivo da recusa mudou: {motivos} — `valor_nao_reconhecido` é o "
        "defeito de antes da F2b (o motor não sabia ler texto); `sem_chute` "
        "significa que a coordenada perdeu a fonte que o pin lhe deu na F4")
    assert {d.get("slot") for d in montado["missing_detail"]} == {
        "local_latitude", "local_longitude"}, (
        "a falta deixou de NOMEAR o slot do caso — é ele que o portão cobra e "
        "que o agente pede, e sem ele quem lê o dossiê não sabe o que buscar: "
        f"{montado['missing_detail']}")


def test_a_resposta_nunca_sai_pela_metade():
    """🔴 A regra que vale HOJE e depois: ou a resposta sai inteira, ou não sai.

    📊 Uma resposta com 7 das 10 chaves abriria o chamado com o endereço
    incompleto — e a Porto aceitaria. `params=None` quando `ok=False` é o que
    impede isso, e vale para qualquer conjunto de slots."""
    flow = PB.native_flow(_porto(), FLOW_ENDERECO)
    for slots in ({},
                  {"local_rua": "R. Exemplo Um"},
                  dict(CAPTURA["slots_do_corredor_equivalentes"])):
        montado = PB.montar_resposta_de_flow(flow, slots)
        if montado["ok"]:
            esperadas = set(
                CAPTURA["chaves_da_resposta"]["presentes_em_3_de_3"])
            assert esperadas <= set(montado["params"] or {}), (
                f"a resposta saiu APROVADA sem as chaves "
                f"{sorted(esperadas - set(montado['params'] or {}))}")
        else:
            assert montado["params"] is None, (
                f"resposta parcial existe: {montado['params']!r}")


# ---------------------------------------------------------------------------
# 5. 🔴 PROCEDÊNCIA OBRIGATÓRIA, POR MÁQUINA — NÃO POR CONVENÇÃO
# ---------------------------------------------------------------------------

_CHAVES_DA_PROCEDENCIA = ("source", "insurer_key", "msg_type", "wa_timestamp")


def _sem_procedencia(flow: dict) -> list:
    """As chaves de `observed` que faltam. Forma da declaração (§9.4, exceção)."""
    obs = flow.get("observed") or {}
    return [k for k in _CHAVES_DA_PROCEDENCIA if not str(obs.get(k) or "").strip()]


def test_TODO_mapa_de_formulario_tem_o_bloco_observed():
    """🔴 *"Mapa sem procedência é invenção com cara de medição."*

    Esta asserção fica VERMELHA se alguém apagar o `observed` de qualquer mapa,
    em qualquer corredor — inclusive dos que já existiam."""
    faltando = []
    for ref in PB.list_playbooks():
        pb = PB.get_playbook(ref) or {}
        for flow_id, flow in (pb.get("native_flows") or {}).items():
            sem = _sem_procedencia(flow)
            if sem:
                faltando.append(f"{ref}/{flow_id}: falta {sem}")
    assert not faltando, "mapa sem procedência: " + " · ".join(faltando)
    # E a pesquisa também: declaração de "não responder" sem procedência é
    # opinião, não medição.
    for flow_id, decl in (_porto().get("flows_nao_respondiveis") or {}).items():
        assert _sem_procedencia(decl) == [], (
            f"a declaração de {flow_id} não diz de onde veio")


def test_CONTROLE_a_falta_de_procedencia_CONSEGUE_ser_vista():
    """§9.3 — um guarda que não tem como falhar não guarda nada.

    Duas formas de apagar a procedência, e as duas têm de ser detectadas: o
    bloco inteiro ausente, e uma chave esvaziada."""
    assert _sem_procedencia({"flow_id": "x"}) == list(_CHAVES_DA_PROCEDENCIA), (
        "um mapa SEM `observed` passou pela conferência")
    real = PB.native_flow(_porto(), FLOW_ENDERECO)
    mutilado = dict(real)
    mutilado["observed"] = {**(real["observed"]), "wa_timestamp": ""}
    assert _sem_procedencia(mutilado) == ["wa_timestamp"], (
        "esvaziar a data da captura passou pela conferência")
    assert _sem_procedencia(real) == [], (
        "o mapa REAL da Porto foi reprovado pela própria conferência")


# ---------------------------------------------------------------------------
# 6. A AZUL FICA DECLARADA NÃO MAPEADA — COM O MOTIVO ESCRITO
# ---------------------------------------------------------------------------

def test_a_azul_esta_declarada_NAO_MAPEADA_com_o_motivo():
    """📊 azul: 0 convites, 0 schemas, 10 respostas vazias (26/09/2026).

    ⛔ Inventar o mapa da Azul copiando o da Porto seria a pior forma do defeito
    que este arquivo combate. O que vale é o motivo escrito e o roteiro de
    captura — e um guarda que impeça o mapa de nascer sem material."""
    azul = PB.get_playbook("azul-auto-whatsapp@v1") or {}
    assert not (azul.get("native_flows") or {}), (
        "a Azul ganhou mapa de formulário. Se houve captura, ótimo: o `observed` "
        "tem de apontar a linha, e este teste migra (CLAUDE.md §9.3). Se foi "
        "copiado da Porto, é invenção com cara de medição")
    fonte = PLAYBOOKS_PY.read_text(encoding="utf-8")
    assert "A AZUL NÃO ESTÁ MAPEADA" in fonte, (
        "o motivo saiu do código; sem ele a ausência vira folclore")
    assert "_AZUL_AUTO_SEM_MAPA_DE_FORMULARIO" in fonte
