# -*- coding: utf-8 -*-
"""O acionamento para de travar: o formulário, o relógio e a pergunta repetida.

Três defeitos medidos em 03/08/2026, os três no mesmo caminho — o que fala com
a seguradora enquanto o segurado espera na beira da estrada.

T.1 · O formulário nativo: o corredor sabia a resposta e não sabia entregá-la
------------------------------------------------------------------------------
📊 `observed_events` (banco de produção, 03/08/2026): a frase que abre o
formulário da família HDI/Yelum — *"precisamos entender o local e as condições
do veículo"* — aparece **4 vezes**: hdi 18/06, hdi 15/07, hdi 18/07 e yelum
18/07. São os **4 acionamentos mais recentes** da família, e **todos param
nela**. Nenhum chegou ao protocolo.

`montar_resposta_de_flow` já reconstrói, byte a byte, o `paramsJSON` que um
humano enviou em 18/07. O que faltava era o transporte. Agora foi medido:

📊 `curl {GO}/swagger/doc.json` (03/08/2026, HTTP 200, 495.536 bytes,
`info.title="Evolution GO"`, `version="1.0"`) → **88 rotas**, das quais **12 de
envio**: text, media, button, list, carousel, contact, link, location, poll,
sticker, status/text, status/media.

**Nenhuma envia RESPOSTA de interativa.** Não há `/send/interactive`, não há
`/send/flow`, não há rota de waE2E cru. As doze ORIGINAM mensagem; responder um
flow é outro tipo de mensagem (`interactiveResponseMessage.
nativeFlowResponseMessage`), e nenhum handler do GO o produz.

Então este arquivo prova o que dá para provar sem o número pareado — detectar,
montar, recusar o incompleto, guardar o token da sessão, construir o corpo
waE2E exato — e prova também que, **sem rota provada, nada sai**. O gatilho de
handoff do corredor continua armado; o que mudou é que o humano recebe a
resposta pronta em vez de um "não consegui".

E um erro achado no caminho: `send_list_reply` mandava o `row_id` no campo `id`
do `/send/text`. 📊 No swagger, `TextStruct.id` é o id **da mensagem** que se
está criando (irmão de `quoted.messageId`) — não a linha escolhida. Aquilo
enviava texto comum com um id forjado. Nada no repositório chamava o método; o
engano nunca chegou a produção.

T.2 · Perguntar o CEP custava minutos, com o CEP na ficha desde o começo
------------------------------------------------------------------------
Uma tela sem passo mapeado tinha UM caminho: pausa → Vigia (varredura de 20s) →
Sentinela → Cérebro (LLM forte, rede). **São minutos.** E a URA da HDI encerra a
conversa sozinha em 12 minutos — está escrito na tela de boas-vindas dela.

Gastar minutos para responder *"qual o CEP?"* não é lento: é perder o
acionamento por um dado que já estava na ficha na primeira mensagem.

A camada nova responde DADO na hora, da ficha, sem rede. E recusa DECISÃO
sempre — confirmar, agendar, escolher serviço. Errar num dado custa um dado
errado; errar numa decisão **abre serviço no nome do segurado**.

T.3 · O acionamento descobria no meio que faltava um dado
----------------------------------------------------------
`required_slots` do subserviço nunca soube dos campos do formulário nativo. 📊 O
formulário exige *"em relação ao nível da rua, onde o veículo está?"* — a
resposta escolhe o EQUIPAMENTO enviado (plataforma, asa delta, munck) — e esse
dado não estava em lista nenhuma. Descobrir isso na última tela, com a URA
esperando, é o que os 4 acionamentos acima viveram.

`tudo_que_sera_pedido` junta as três fontes (subserviço + passos de URA +
formulário) para a coleta com o cliente acontecer **uma vez só**.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(str(RAIZ), *p), encoding="utf-8") as fh:
        return fh.read()


for _nome in ("app", "app.services", "app.services.whatsapp",
              "app.services.whatsapp.providers"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, BACKEND / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
FICHA = _carregar("app.services.attendance_ficha", "app/services/attendance_ficha.py")
MOTOR = _carregar("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
INBOUND = _carregar("app.services.whatsapp.evolution_inbound",
                    "app/services/whatsapp/evolution_inbound.py")

HDI_AUTO = "hdi-auto-whatsapp@v1"
FLOW_ID = "857030507196739"

# 📊 A mensagem REAL que abre o formulário, como o parser de interativas a
# entrega (corpo + marcador). É nela que os 4 acionamentos pararam.
TELA_DO_FORMULARIO = (
    "Para que a remoção do veículo ocorra sem imprevistos, precisamos entender "
    "o local e as condições do veículo.\n"
    "[FORMULARIO NATIVO: Detalhes do atendimento] (exige clique — não aceita texto)"
)

# Os metadados que vêm junto — `flow_token` é da SESSÃO e some com ela.
# 📊 O formato do token é o observado em produção (`abc:<numero>:<numero>`).
INTERATIVA_DO_FORMULARIO = {
    "kind": "flow",
    "flow": {"name": "flow", "cta": "Detalhes do atendimento",
             "flow_id": FLOW_ID, "flow_token": "abc:551155020700:5547996274743"},
    "options": [],
}

CASO_COMPLETO = {
    "titular_cpf": "11122233344",
    "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23",
    "veiculo_cor": "prata",
    "local_atual": "Rua Abelardo Luz, 342, Balneario, Florianopolis - SC, 88075-542",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose SC",
    "problema_descricao": "carro nao liga, provavel pane no motor",
    "telefone_contato": "48999990000",
    # O que o formulário nativo exige, e que `required_slots` nunca soube pedir.
    "veiculo_em_garagem": "sim",
    "veiculo_nivel_rua": "acesso livre",
    "local_situacao": "Local Seguro",
}


def _sessao(slots=None, live=True, estado="ura"):
    """Uma sessão de acionamento em curso, sem tocar em Redis nem banco."""
    os.environ["INSURER_DISPATCH_LIVE"] = "true" if live else "false"
    os.environ["DISPATCH_FINALIZE_MODE"] = "test"
    os.environ.pop("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", None)
    sessao = MOTOR.new_dispatch_session(
        case_id="caso-1", company_id="co-teste", playbook_ref=HDI_AUTO,
        subservice="guincho", slots=dict(slots if slots is not None else CASO_COMPLETO),
    )
    sessao["state"] = estado
    sessao["client_phone"] = "5548999990000"
    return sessao


# ---------------------------------------------------------------------------


def teste_o_transporte_do_formulario_nao_foi_inventado():
    print("\n[T1] O Evolution GO NÃO tem rota de resposta de flow — e isso está escrito")
    for _dotted, _rel in (
        ("app.services.whatsapp.exceptions", "app/services/whatsapp/exceptions.py"),
        ("app.services.whatsapp.evolution_go_events", "app/services/whatsapp/evolution_go_events.py"),
        ("app.services.whatsapp.models", "app/services/whatsapp/models.py"),
        ("app.services.whatsapp.providers.base", "app/services/whatsapp/providers/base.py"),
    ):
        if _dotted not in sys.modules or not hasattr(sys.modules[_dotted], "__file__"):
            _carregar(_dotted, _rel)
    GO = _carregar("app.services.whatsapp.providers.evolution_go",
                   "app/services/whatsapp/providers/evolution_go.py")

    rotas = GO.rotas_de_envio_medidas()
    checar(len(rotas) == 12, "as 12 rotas de envio do swagger estão registradas como DADO",
           f"{len(rotas)}: {rotas}")
    checar(not [r for r in rotas if "interactive" in r or "flow" in r or "raw" in r],
           "e NENHUMA delas responde interativa",
           "é a afirmação inteira desta tarefa; se um dia aparecer uma, este teste avisa")
    checar("/send/text" in rotas and "/send/list" in rotas,
           "as conhecidas continuam lá (a lista é transcrição, não opinião)")

    # 📊 As 12 acima continuam sendo as rotas de ORIGEM do upstream, e nenhuma
    # delas responde interativa — a afirmação de cima segue de pé.
    #
    # A DÉCIMA TERCEIRA é nossa: `/send/interactiveResponse`, aberta pelo patch
    # 0005 do fork e provada no ar em 03/08/2026 (mensagem aceita entre dois
    # números nossos, com o embrulho DocumentWithCaption). Por isso este bloco
    # deixou de exigir vazio: exigir vazio depois que a rota existe seria
    # guardar uma verdade vencida.
    ambiente_limpo = {k: v for k, v in os.environ.items() if k != GO.ENV_ROTA_FLOW_REPLY}
    checar(GO.rota_de_flow_reply(ambiente_limpo) == "/send/interactiveResponse",
           "sem variável de ambiente, `rota_de_flow_reply` usa a rota PROVADA",
           "ela não é palpite: foi medida no ar, e o palpite continua proibido")
    checar(GO.rota_de_flow_reply({GO.ENV_ROTA_FLOW_REPLY: "send/flowreply"}) == "/send/flowreply",
           "e uma rota declarada é aceita já normalizada (a barra entra sozinha)")
    checar(GO.rota_de_flow_reply({GO.ENV_ROTA_FLOW_REPLY: "off"}) == "",
           "e existe como DESLIGAR sem esperar por um deploy")

    # O corpo waE2E: PURO, provável offline. A forma não foi deduzida — 📊 é a
    # dos eventos reais de `flow_reply` do acervo do Observador.
    corpo = GO.montar_nfm_reply(flow_token="tok-abc", nome_do_envelope="galaxy_message",
                                params={"rb_InformacoesLocal": "6"})
    interativa = corpo["interactiveResponseMessage"]
    nfm = interativa["nativeFlowResponseMessage"]
    checar(nfm["name"] == "galaxy_message" and "paramsJSON" in nfm,
           "o corpo é interactiveResponseMessage → nativeFlowResponseMessage")
    checar(nfm["name"] != "Detalhes",
           "o envelope NAO usa o nome do formulário",
           "📊 o clique humano de 18/07 traz name='galaxy_message'; usar o "
           "flow_name faria a seguradora descartar a resposta em silêncio")
    params = json.loads(nfm["paramsJSON"])
    checar(params.get("flow_token") == "tok-abc",
           "o flow_token entra AQUI — e só aqui",
           "o corredor monta o caso; o token é transporte e muda a cada conversa")
    checar(params.get("rb_InformacoesLocal") == "6",
           "as respostas viajam achatadas ao lado do token, como no clique real")
    checar(interativa["body"]["text"] == "Formulario enviado",
           "com o mesmo corpo de bolha que o WhatsApp mostra")

    # A IDENTIDADE do formulário — é ela que diz QUAL formulário está sendo
    # respondido. Faltava, e sem ela a seguradora não sabe a que se refere.
    com_id = GO.montar_nfm_reply(
        flow_token="tok-abc", nome_do_envelope="galaxy_message",
        params={"rb_InformacoesLocal": "6"},
        flow_response_params={"flow_id": "857030507196739", "title": "Informar condições"})
    p_id = json.loads(com_id["interactiveResponseMessage"]["nativeFlowResponseMessage"]["paramsJSON"])
    checar(p_id.get("wa_flow_response_params", {}).get("flow_id") == "857030507196739",
           "a identidade do formulário viaja em wa_flow_response_params",
           "📊 o clique real de 18/07 a carrega; sem ela, faltava metade")
    checar(p_id.get("flow_token") == "tok-abc" and p_id.get("rb_InformacoesLocal") == "6",
           "e ela não empurra o token nem as respostas para fora")

    for rotulo, kwargs in (
        ("sem token", {"flow_token": "", "nome_do_envelope": "galaxy_message",
                       "params": {"a": "1"}}),
        ("sem respostas", {"flow_token": "t", "nome_do_envelope": "galaxy_message",
                           "params": {}}),
        # O nome do envelope é ECOADO da captura. Sem padrão, de propósito:
        # um default aqui seria um palpite escondido atrás de uma assinatura
        # amigável, e o palpite errado é descartado em silêncio.
        ("sem o nome do envelope", {"flow_token": "t", "nome_do_envelope": "",
                                    "params": {"a": "1"}}),
    ):
        try:
            GO.montar_nfm_reply(**kwargs)
            checar(False, f"montar_nfm_reply recusa {rotulo}", "montou assim mesmo")
        except ValueError:
            checar(True, f"montar_nfm_reply recusa {rotulo}")

    # E o provider RECUSA sem tocar na rede. `_post` é trocado por uma armadilha:
    # se o envio tentar sair, o teste falha em vez de bater no host de produção.
    provider = GO.EvolutionGoProvider.__new__(GO.EvolutionGoProvider)
    provider._base_url, provider._token, provider._instance_id = "http://naovai", "t", "i"
    tentativas: list = []

    def _armadilha(path, payload):  # noqa: ANN001 — se o envio sair, o teste vê
        tentativas.append(path)
        return GO.SendResult(ok=False, error="ROTA_CHUTADA")

    provider._post = _armadilha  # noqa: SLF001
    # 📊 ATUALIZADO em 03/08/2026. Este bloco guardava a verdade da véspera:
    # "ter o schema do formulário não é ter o canal". Estava certo — e deixou de
    # valer no dia em que o canal passou a existir e foi PROVADO no ar (patch
    # 0005, mensagem aceita entre dois números nossos com o embrulho certo).
    #
    # A lição não morreu, só mudou de lugar: a recusa continua tendo de ser
    # limpa, e agora se testa DESLIGANDO a rota de propósito. Um teste que
    # afirma "não existe canal" depois que ele existe não protege nada —
    # ensina a ignorar teste.
    os.environ[GO.ENV_ROTA_FLOW_REPLY] = "off"
    try:
        r = provider.send_native_flow_response("5548", flow_token="tok", nome_do_envelope="galaxy_message",
                                               params={"a": "1"})
        checar(r.ok is False and r.error == "evolution_go_sem_rota_de_flow_reply",
               "com a rota DESLIGADA, o envio recusa com o motivo escrito", str(r.error))
        checar(tentativas == [],
               "e NÃO faz requisição nenhuma",
               "chutar /send/text com o JSON dentro entregaria uma parede de texto "
               "à URA — e ela encerra em 12 minutos")
        checar(provider.flow_reply_supported() is False,
               "e `flow_reply_supported()` diz não enquanto estiver desligada")
    finally:
        os.environ.pop(GO.ENV_ROTA_FLOW_REPLY, None)

    checar(provider.flow_reply_supported() is True,
           "e diz SIM por padrão — a rota existe e foi provada no ar")

    # O erro achado no caminho: o `id` do /send/text é o id DA MENSAGEM.
    enviados: list = []
    provider.send_text = lambda to, text: enviados.append((to, text)) or "ok"
    provider.send_list_reply("5548", "row_9", "Automóvel")
    checar(enviados == [("5548", "Automóvel")],
           "responder lista = digitar o RÓTULO (o row_id não viaja mais)",
           "`TextStruct.id` é o id da mensagem, não a linha escolhida — "
           "mandá-lo ali forjava um id e não selecionava nada")
    fonte = _ler("backend", "app", "services", "whatsapp", "providers", "evolution_go.py")
    checar('"id": row_id' not in fonte and '"id": button_id' not in fonte,
           "e o campo forjado sumiu do arquivo")


def teste_o_formulario_completo_e_montado_e_o_incompleto_recusado():
    print("\n[T2] Formulário nativo: monta o completo, RECUSA o incompleto")
    enviados: list = []

    def transporte(flow_token, nome_do_envelope, params, flow_response_params=None):
        enviados.append({"token": flow_token, "name": nome_do_envelope, "params": params})
        return True

    # --- caso completo, com transporte provado -----------------------------
    sessao = _sessao()
    sessao = MOTOR.handle_insurer_message(
        sessao, TELA_DO_FORMULARIO, sender=lambda t: None,
        interactive=INTERATIVA_DO_FORMULARIO, flow_sender=transporte)
    checar(sessao["state"] == "ura",
           "com caso completo e transporte, o acionamento SEGUE (não vira needs_human)",
           f"{sessao['state']} / {sessao.get('reason')}")
    checar(len(enviados) == 1, "a resposta do formulário foi entregue ao transporte",
           str(enviados))
    checar(enviados and enviados[0]["params"] == {
        "rb_EmGaragemOuEstacionamento": "1", "rb_NivelDaRua": "4",
        "ckb_SituacoesVeiculo": ["nenhuma_opcoes"], "rb_InformacoesLocal": "6",
        "rb_Ocupantes": "1"},
        "e é o paramsJSON que o humano enviou em 18/07/2026, id por id",
        str(enviados[0]["params"] if enviados else None))
    checar(enviados and enviados[0]["token"] == INTERATIVA_DO_FORMULARIO["flow"]["flow_token"],
           "com o flow_token que chegou NESTA conversa")
    saidas = [t for t in sessao["transcript"] if t.get("direction") == "out"]
    checar(any(t.get("step") == "formulario_nativo" for t in saidas),
           "o espelho registra que um formulário foi respondido")

    # --- caso completo, SEM transporte: pausa com a resposta pronta ---------
    sessao2 = _sessao()
    sessao2 = MOTOR.handle_insurer_message(
        sessao2, TELA_DO_FORMULARIO, sender=lambda t: None,
        interactive=INTERATIVA_DO_FORMULARIO, flow_sender=None)
    checar(sessao2["state"] == "needs_human"
           and sessao2.get("reason") == "formulario_pronto_sem_transporte",
           "sem rota provada, PAUSA — e o motivo diz exatamente o que falta",
           f"{sessao2['state']} / {sessao2.get('reason')}")
    checar((sessao2.get("flow_resposta") or {}).get("ok") is True,
           "mas a resposta fica montada na sessão")
    dossie = MOTOR.build_handoff_dossier(sessao2, sessao2.get("reason") or "")
    checar("RESPOSTA PRONTA" in dossie and "rb_NivelDaRua: 4" in dossie,
           "e o dossiê entrega ao humano o que marcar, campo por campo",
           "ele clica em 10 segundos em vez de reentrevistar o segurado")

    # --- caso incompleto: recusa, e nomeia o que falta ----------------------
    incompleto = dict(CASO_COMPLETO)
    incompleto.pop("local_situacao")          # muda a PRIORIDADE do atendimento
    incompleto.pop("veiculo_nivel_rua")       # escolhe o EQUIPAMENTO enviado
    sessao3 = _sessao(incompleto)
    sessao3 = MOTOR.handle_insurer_message(
        sessao3, TELA_DO_FORMULARIO, sender=lambda t: None,
        interactive=INTERATIVA_DO_FORMULARIO, flow_sender=transporte)
    checar(sessao3["state"] == "needs_human"
           and str(sessao3.get("reason") or "").startswith("formulario_incompleto:"),
           "faltando dado obrigatório, RECUSA", str(sessao3.get("reason")))
    checar(len(enviados) == 1,
           "e NADA foi enviado — não existe resposta parcial",
           "formulário meio preenchido despacha o equipamento errado")
    checar((sessao3.get("flow_resposta") or {}).get("params") is None,
           "a resposta parcial nem sequer é construída")
    faltando = sessao3.get("missing_slots") or []
    checar("rb_NivelDaRua" in faltando and "rb_InformacoesLocal" in faltando,
           "os campos que faltam vêm nomeados", str(faltando))
    dossie3 = MOTOR.build_handoff_dossier(sessao3, sessao3.get("reason") or "")
    checar("Em relação ao nível da rua" in dossie3 and "Subsolo" in dossie3,
           "e o dossiê traz a PERGUNTA da seguradora com as opções DELA",
           "o humano pergunta com as palavras certas")


def teste_o_token_da_sessao_nao_vira_linha_de_banco():
    print("\n[T3] O flow_token é da sessão — e não atravessa para o banco")
    sessao = _sessao()
    MOTOR.registrar_formulario_nativo(sessao, INTERATIVA_DO_FORMULARIO)
    checar(sessao.get("flow_token") == INTERATIVA_DO_FORMULARIO["flow"]["flow_token"],
           "o token fica na sessão quando a mensagem de flow chega")
    checar(sessao.get("flow_id_ativo") == FLOW_ID, "junto do flow_id")

    retrato = MOTOR.snapshot_duravel(sessao)
    checar("flow_token" not in retrato,
           "e o checkpoint durável do Work Run NÃO o leva",
           "o nome é o que o protege: `_CHAVES_PROIBIDAS` corta toda chave com "
           "'token' — aninhá-lo furaria esse corte em silêncio")
    checar("flow_token" not in json.dumps(retrato, ensure_ascii=False, default=str),
           "nem escondido dentro de outro campo do retrato")

    # E o parser entrega o token por uma porta com nome, não por um get solto.
    dados = INBOUND.dados_do_formulario_nativo({"interactive": INTERATIVA_DO_FORMULARIO})
    checar(dados and dados["flow_token"] == INTERATIVA_DO_FORMULARIO["flow"]["flow_token"]
           and dados["flow_id"] == FLOW_ID,
           "`dados_do_formulario_nativo` devolve id e token do inbound normalizado")
    checar(INBOUND.dados_do_formulario_nativo({"interactive": {"kind": "buttons"}}) is None,
           "e devolve None quando a mensagem não é formulário")

    cru = {"event": "messages.upsert", "data": {"key": {"remoteJid": "554199@s.whatsapp.net"},
           "message": {"interactiveMessage": {
               "body": {"text": "precisamos entender o local"},
               "nativeFlowMessage": {"buttons": [{"name": "flow", "buttonParamsJson": json.dumps(
                   {"flow_cta": "Detalhes", "flow_id": 857030507196739, "flow_token": "tk-9"})}]}}}}}
    do_cru = INBOUND.dados_do_formulario_nativo(cru)
    checar(do_cru and do_cru["flow_token"] == "tk-9" and do_cru["flow_id"] == "857030507196739",
           "também lê o payload cru — inclusive com flow_id NUMÉRICO",
           "id numérico virando string vazia faria o schema nunca ser achado")


def teste_o_formulario_nao_contamina_as_telas_seguintes():
    print("\n[T4] Responder o formulário não transforma a URA inteira em formulário")
    enviados: list = []
    sessao = _sessao()
    sessao = MOTOR.handle_insurer_message(
        sessao, TELA_DO_FORMULARIO, sender=lambda t: None,
        interactive=INTERATIVA_DO_FORMULARIO,
        flow_sender=lambda **kw: enviados.append(kw) or True)
    checar(len(enviados) == 1 and sessao["state"] == "ura", "o formulário foi respondido")

    textos: list = []
    sessao = MOTOR.handle_insurer_message(
        sessao, "Qual a cor do veículo?", sender=textos.append)
    checar(len(enviados) == 1,
           "a tela SEGUINTE não vira outro envio de formulário",
           "a decisão é por MENSAGEM; resolver pelo que a sessão lembra faria o "
           "motor responder formulário a cada tela que viesse depois")
    checar(textos == ["prata"], "ela é respondida como a tela de texto que é", str(textos))


def teste_o_banco_responde_dado_da_ficha_na_hora():
    print("\n[T5] Pergunta de DADO: resposta imediata, da ficha, sem LLM")
    telas = (
        ("Para seguirmos, informe o CEP do local onde o veículo está.", "88075-542", "cep"),
        ("Qual o número de telefone com DDD para contato?", "48999990000", "telefone"),
        ("Qual a cor do veículo?", "prata", "cor"),
        ("Qual o endereço de destino do reboque?",
         "Oficina Central, Rua B, 50, Sao Jose SC", "destino"),
    )
    for tela, esperado, campo in telas:
        enviados: list = []
        sessao = _sessao()
        antes = len(sessao.get("transcript") or [])
        sessao = MOTOR.handle_insurer_message(sessao, tela, sender=enviados.append)
        checar(enviados == [esperado], f"'{tela[:38]}…' → responde {campo} na hora",
               f"enviou {enviados}")
        checar(sessao["state"] == "ura",
               f"  e a sessão NÃO cai na fase humana por causa de {campo}",
               "cair ali é 20s de varredura + Sentinela + LLM, numa URA que "
               "encerra em 12 minutos")
        saidas = [t for t in sessao["transcript"][antes:] if t.get("direction") == "out"]
        checar(any(str(t.get("step") or "").startswith("ficha:") for t in saidas),
               f"  e o espelho registra a origem da resposta ({campo})")

    # A ficha do atendimento alimenta o banco pelo MESMO vocabulário.
    ficha = FICHA.fundir(FICHA.ficha_vazia(), {"confirmados": {
        "local_cep": "88010-000", "telefone_contato": "48988887777"}})
    dados = FICHA.dados_conhecidos(ficha)
    r = MOTOR.responder_da_ficha(PB.get_playbook(HDI_AUTO), "Informe o CEP, por favor.", dados)
    checar(r["ok"] and r["resposta"] == "88010-000",
           "e o banco lê a FICHA do atendimento, não só os slots do acionamento",
           str(r))
    # O caso em curso vence a ficha antiga (o corretor corrigiu o endereço).
    dados2 = FICHA.dados_conhecidos(ficha, {"local_cep": "88075-542"})
    r2 = MOTOR.responder_da_ficha(PB.get_playbook(HDI_AUTO), "Informe o CEP, por favor.", dados2)
    checar(r2["ok"] and r2["resposta"] == "88075-542",
           "com o dado do acionamento em curso por cima do que a ficha guardou")


def teste_o_banco_recusa_toda_tela_de_decisao():
    print("\n[T6] Pergunta de DECISÃO: o banco NUNCA responde")
    playbook = PB.get_playbook(HDI_AUTO)
    # Os slots do acionamento REAL — com CEP, telefone e cor dentro. É contra um
    # caso COMPLETO que a recusa vale: recusar por falta de dado não prova nada.
    dados = _sessao()["slots"]
    checar(str(dados.get("local_cep") or "") == "88075-542",
           "(o caso usado nesta prova tem o CEP dentro)", str(dados.get("local_cep")))
    decisoes = (
        ("Podemos confirmar a abertura do serviço?", "confirmação final"),
        ("Você quer o atendimento para agora ou prefere agendar para outro momento?",
         "o ponto de não-retorno da família HDI"),
        ("Qual serviço você deseja abrir? 1 - Guincho 2 - Bateria", "escolha de serviço"),
        ("Deseja agendar para amanhã?", "agendamento"),
        ("Confirme o CEP 88075-542, está correto?",
         "confirmação DISFARÇADA de pergunta de dado"),
    )
    for tela, rotulo in decisoes:
        r = MOTOR.responder_da_ficha(playbook, tela, dados)
        checar(r["ok"] is False and r["motivo"] == "decisao",
               f"recusa: {rotulo}", f"{tela[:40]}… → {r}")

    checar(MOTOR.pergunta_de_decisao(playbook,
           "Você precisa do atendimento agora ou prefere agendar?").startswith("finalize_anchor:"),
           "e a recusa lê os `finalize_anchors` DO CORREDOR, não uma cópia",
           "âncora nova de finalização passa a proteger o banco no mesmo commit")

    # A prova que importa: o FREIO continua na frente de tudo. Em modo teste, a
    # confirmação final aborta — o banco não abriu uma segunda porta em volta dele.
    enviados: list = []
    sessao = _sessao()
    sessao = MOTOR.handle_insurer_message(
        sessao, "Podemos confirmar a abertura do serviço?", sender=enviados.append)
    checar(sessao["state"] == "test_aborted",
           "no fluxo inteiro, a confirmação final ainda CANCELA em modo teste",
           f"{sessao['state']} / {sessao.get('reason')}")
    checar(enviados == ["Sair"], "com o cancelamento educado do corredor", str(enviados))


def teste_sem_o_dado_ele_nao_inventa():
    print("\n[T7] Dado que não está na ficha: não se inventa, cai no caminho antigo")
    sem_cep = {k: v for k, v in CASO_COMPLETO.items() if k != "local_atual"}
    sem_cep["local_atual"] = "perto do posto Ipiranga"   # sem CEP dedutível
    enviados: list = []
    sessao = _sessao(sem_cep)
    sessao = MOTOR.handle_insurer_message(
        sessao, "Para seguirmos, informe o CEP do local onde o veículo está.",
        sender=enviados.append)
    checar(enviados == [],
           "sem CEP na ficha, NADA é enviado",
           "um CEP aproximado manda o guincho para outro bairro")
    checar(sessao["state"] == "human_phase",
           "a sessão segue o caminho antigo (fase humana → Cérebro)",
           f"{sessao['state']}")
    checar((sessao.get("falta_para_a_ura") or {}).get("slot") == "local_cep",
           "e fica escrito O QUE a seguradora pediu e não temos", str(sessao.get("falta_para_a_ura")))
    checar("CEP" in MOTOR.build_handoff_dossier(sessao, "teste"),
           "o humano lê isso no dossiê, com o nome humano do campo")

    playbook = PB.get_playbook(HDI_AUTO)
    r = MOTOR.responder_da_ficha(playbook, "Qual a cor do veículo?", {"veiculo_placa": "ABC1D23"})
    checar(r["ok"] is False and r["motivo"] == "sem_dado_na_ficha" and r["slot"] == "veiculo_cor",
           "pergunta reconhecida + dado ausente = `sem_dado_na_ficha`", str(r))
    checar(MOTOR.responder_da_ficha(playbook, "Prestador a caminho, faltam 30 minutos.",
                                    CASO_COMPLETO)["motivo"] == "nao_e_pergunta",
           "aviso informativo não é pergunta — e responder a ele confundiria a URA")
    checar(MOTOR.responder_da_ficha(playbook, "Qual a marca do capacete?",
                                    CASO_COMPLETO)["motivo"] == "nao_reconhecida",
           "pergunta fora do banco segue para o Cérebro, como antes")

    # "não informado" na ficha NÃO é dado — senão viraria resposta à seguradora.
    ficha = FICHA.fundir(FICHA.ficha_vazia(), {"confirmados": {"veiculo_cor": "não informado"}})
    checar("veiculo_cor" not in FICHA.dados_conhecidos(ficha),
           "e 'não informado' na ficha continua sendo ausência, não valor")


def teste_o_corredor_declara_tudo_antes_de_comecar():
    print("\n[T8] O que será pedido é declarado ANTES — inclusive o do formulário")
    plano = MOTOR.tudo_que_sera_pedido("HDI", "auto", "guincho")
    checar(plano["ok"] and plano["playbook_ref"] == HDI_AUTO,
           "resolve o corredor pela seguradora + ramo", str(plano.get("erro")))

    slots = plano["slots"]
    for obrigatorio in ("titular_cpf", "veiculo_placa", "local_atual", "local_destino",
                        "problema_descricao", "telefone_contato"):
        checar(obrigatorio in slots, f"pede {obrigatorio} (subserviço)", str(slots))

    # A fonte que faltava: os campos do formulário nativo. 📊 Nenhum deles está
    # em `required_slots` — e é neles que os 4 acionamentos recentes pararam.
    do_formulario = [i for i in plano["obrigatorios"] if i["origem"] == "formulario_nativo"]
    nomes = {i["slot"] for i in do_formulario}
    checar({"veiculo_em_garagem", "veiculo_nivel_rua", "local_situacao"} <= nomes,
           "pede também o que o FORMULÁRIO exige", str(sorted(nomes)))
    for campo in ("veiculo_nivel_rua", "local_situacao"):
        checar(campo not in (PB.get_playbook(HDI_AUTO)["subservices"]["guincho"]["required_slots"]),
               f"  e {campo} NÃO estava em required_slots",
               "descobrir isso na última tela é perder o acionamento")

    nivel = next(i for i in do_formulario if i["slot"] == "veiculo_nivel_rua")
    checar(nivel["pergunta"] == "Em relação ao nível da rua, onde o veículo está?",
           "cada item traz a pergunta com as palavras da seguradora", str(nivel["pergunta"]))
    checar("Subsolo" in nivel["opcoes"] and "Acima do nível da rua" in nivel["opcoes"],
           "e as opções exatas dela", str(nivel["opcoes"]))
    checar(all(i.get("rotulo") for i in plano["obrigatorios"]),
           "todo item tem rótulo humano (o vocabulário único da ficha)")

    padrao = {i["slot"] for i in plano["com_padrao"]}
    checar({"quando", "ponto_referencia", "rodovia", "roda_travada"} <= padrao,
           "o que o motor preenche sozinho NÃO é perguntado ao cliente", str(sorted(padrao)))
    checar(not (padrao & set(slots)),
           "  (e por isso nenhum deles aparece na lista de coleta)",
           str(sorted(padrao & set(slots))))

    checar(MOTOR.tudo_que_sera_pedido("HDI", "auto", "reboque_espacial")["erro"]
           == "subservico_invalido",
           "subserviço que a seguradora não faz devolve o erro, não uma lista vazia")
    checar(MOTOR.tudo_que_sera_pedido("Seguradora Inexistente", "auto", "guincho")["erro"]
           == "corredor_inexistente",
           "seguradora sem corredor também")


def teste_o_portao_de_envio_real_nao_afrouxou():
    """ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3.

    Este caso afirmava duas coisas que eram verdade e deixaram de ser:
    `dispatch_live_enabled` exigia a flag explícita, e o freio de finalização
    nascia em `test`. Decisão do Founder, dita duas vezes: a única trava passa a
    ser `agents.is_active` do agente de atendimento — "tudo pronto e
    funcionando, mas o agente tem que continuar desligado".

    E ele afirmava isso lendo o TEXTO da fonte, que é a forma mais frágil de
    guardar um portão: casava a receita, não o resultado. Agora ele exercita o
    portão de verdade, nos dois sentidos, com CONTROLE — porque um portão que
    só sabe dizer "não" passa em qualquer asserção de "não".
    """
    print("\n[T9] O portão continua fechável — e agora é exercitado, não lido")
    fonte = _ler("backend", "app", "services", "insurer_dispatch_service.py")

    _antes = {k: os.environ.get(k) for k in ("INSURER_DISPATCH_LIVE",
                                             "DISPATCH_FINALIZE_MODE",
                                             MOTOR.FREIO_DE_EMERGENCIA)}
    try:
        for k in _antes:
            os.environ.pop(k, None)
        # CONTROLE — sem nada armado, os dois nascem ABERTOS. É o que muda em
        # relação a ontem, e é o que dá direito às três asserções seguintes.
        checar(MOTOR.dispatch_live_enabled() is True,
               "CONTROLE: sem nada armado, o envio real nasce ABERTO",
               "quem segura agora é o agente desligado, não a ausência de um env")
        checar(MOTOR.finalize_live_for("hdi-auto-whatsapp@v1") is True,
               "CONTROLE: e o freio de finalização nasce SOLTO")

        os.environ["INSURER_DISPATCH_LIVE"] = "false"
        checar(MOTOR.dispatch_live_enabled() is False,
               "um `false` escrito por um operador continua fechando o envio",
               "ignorar o que alguém escreveu com a própria mão é discordar em silêncio")
        os.environ.pop("INSURER_DISPATCH_LIVE", None)

        os.environ["DISPATCH_FINALIZE_MODE"] = "test"
        checar(MOTOR.finalize_live_for("hdi-auto-whatsapp@v1") is False,
               "e `DISPATCH_FINALIZE_MODE=test` continua devolvendo o ensaio")
        os.environ.pop("DISPATCH_FINALIZE_MODE", None)

        os.environ[MOTOR.FREIO_DE_EMERGENCIA] = "true"
        checar(MOTOR.dispatch_live_enabled() is False
               and MOTOR.finalize_live_for("hdi-auto-whatsapp@v1") is False,
               "e o freio de emergência fecha os DOIS de uma linha só",
               "é o que existe para o dia em que for preciso parar sem deploy")
    finally:
        for k, v in _antes.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    checar('return bool(session.get("finalize_approved")) or finalize_live_for(' in fonte,
           "`_finalize_allowed` inalterado")

    # Prova funcional: com o portão FECHADO, o transporte do formulário nunca é
    # chamado — nem com caso completo, nem com transporte disponível.
    enviados: list = []
    sessao = _sessao(live=False)
    sessao = MOTOR.handle_insurer_message(
        sessao, TELA_DO_FORMULARIO, sender=lambda t: None,
        interactive=INTERATIVA_DO_FORMULARIO,
        flow_sender=lambda **kw: enviados.append(kw) or True)
    checar(enviados == [],
           "INSURER_DISPATCH_LIVE desligado: o formulário NÃO sai",
           "dry-run tem de valer também para a tela de app")
    saida = [t for t in sessao["transcript"] if t.get("step") == "formulario_nativo"]
    checar(saida and saida[0].get("dry_run") is True,
           "e o transcript marca o passo como simulado")

    # E o banco de respostas respeita o mesmo portão (ele emite por `_emit`).
    enviados2: list = []
    sessao2 = _sessao(live=False)
    MOTOR.handle_insurer_message(sessao2, "Qual a cor do veículo?", sender=enviados2.append)
    checar(enviados2 == [],
           "o banco de respostas também não envia com o portão fechado",
           "ele emite pelo MESMO `_emit` de todo o resto — nenhum caminho paralelo")


def main() -> int:
    print("=" * 68)
    print("O ACIONAMENTO NAO TRAVA — FORMULARIO, RELOGIO E PERGUNTA REPETIDA")
    print("=" * 68)
    for t in (teste_o_transporte_do_formulario_nao_foi_inventado,
              teste_o_formulario_completo_e_montado_e_o_incompleto_recusado,
              teste_o_token_da_sessao_nao_vira_linha_de_banco,
              teste_o_formulario_nao_contamina_as_telas_seguintes,
              teste_o_banco_responde_dado_da_ficha_na_hora,
              teste_o_banco_recusa_toda_tela_de_decisao,
              teste_sem_o_dado_ele_nao_inventa,
              teste_o_corredor_declara_tudo_antes_de_comecar,
              teste_o_portao_de_envio_real_nao_afrouxou):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O FORMULARIO E MONTADO, O DADO SAI NA HORA E A DECISAO CONTINUA SENDO NOSSA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
