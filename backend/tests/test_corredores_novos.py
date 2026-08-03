"""Os corredores que faltavam — e os três que eu me recusei a escrever.

Tudo aqui nasce de uma leitura de `ura_maps` com status='observed' no banco de
produção em 03/08/2026. Os rótulos abaixo estão copiados como a seguradora os
escreve no WhatsApp, e é por isso que este arquivo pode afirmar o que afirma:
nenhum passo de URA foi deduzido, e onde a evidência acabou, o corredor não
existe.

C.1 · Vidros existe em TRÊS seguradoras, com dois desfechos diferentes
---------------------------------------------------------------------
Vidro era a maior lacuna do acervo: o produto sabe conversar sobre vidro, tem o
telefone e tem o portal do prestador — e não tinha corredor. Ao ler os menos
reais, apareceu uma coisa que o modelo de corredor não previa: **nem todo
corredor abre chamado.**

📊 Azul — vidro é TECLA, e o fluxo segue normal até o protocolo:

    "O que você precisa?
     *1* - Guincho (reboque)
     *2* - Bateria
     *3* - Troca de pneu
     *4* - Chaveiro para o veículo
     *5* - Conserto ou troca de vidro, retrovi[sor]..."

📊 Porto — vidro é item de LISTA, e o fluxo TERMINA num formulário:

    "O que você precisa?
     Guincho (reboque) / Bateria / Troca de pneu / Conserto de vidro
     (Inclui retrovisor, farol ou lanterna) / Chaveiro para o veículo / Táxi"

    "Certo. Para conserto ou reparo de vidro, retrovisor, farol ou lanterna,
     é necessário *preencher o formulário* de sinistro de vidros abaixo"
    "https://porto.vc/reparovidros"
    "Não se preocupe, esse acionamento *para vidros* não irá afetar a sua
     classe de bônus."

📊 Zurich — vidro é item de LISTA e é INFORMATIVO:

    "Você deseja acionar qual serviço? Acionar seguro / Assistência {VALOR} /
     Assistência a vidros / Voltar ao menu"
    "*Assistência a vidros*: encontre informações sobre como pedir o reparo ou
     a troca de vidros, para-brisa, faróis e retrovi[sores]"

Daí o campo `outcome`: `abre` (Azul) e `encaminha` (Porto, Zurich). Encaminhar
não é falhar — é o desfecho correto naquela seguradora, e um corredor que espera
protocolo onde a seguradora nunca emite protocolo morre em "monitorando".

📊 E vidro NÃO tem evidência no menu de assistência de allianz, tokio, mapfre,
yelum, hdi, alfa e bradesco. Nessas sete, `vidros` não é declarado: o sistema
cai em handoff. É a diferença entre "não sei" e um palpite — e um palpite aqui
aperta uma tecla que não existe na tela da seguradora.

C.2 · Pane seca não virou subserviço, e essa é a entrega
-------------------------------------------------------
📊 Nenhuma das dez seguradoras tem opção própria de pane seca:

    Allianz e Alfa .... "*3* - Guincho para *pane mecânica*"
    Zurich ............ "assistência 24h ... reboque, socorro mecânico,
                         chaveiro, pane seca ou troca de pneu"
    Bradesco/HDI/Yelum  "Pane ou Defeito", genérico

Declarar `pane_seca` obrigaria a inventar a tecla que ele aperta. Então pane
seca é APELIDO de guincho, e o classificador que o Atlas já usa
(`infer_ramo_servico`, que devolve "pane_seca") atravessa até o corredor certo
sem um segundo classificador para divergir com o tempo.

C.3 · Residencial saiu da Allianz
---------------------------------
📊 HDI, o residencial mais bem observado do acervo:

    "Identifiquei em seu cadastro a placa {PLACA}. Deseja continuar com o
     atendimento para o veículo ou atendimento residencial?
     Botão 1: Automóvel  Botão 2: Residencial"

    "Qual é o serviço que você precisa solicitar?
     Encanador — Selecione para conserto de vazamentos como torneiras, sifões
     Desentupimento — Selecione esta opção se precisa de um desentupimento
     Eletricista / Chaveiro / Eletrodoméstico"

    "Para esse CPF localizamos o serviço de *ENCANADOR*. Deseja acompanhar?
     Botão 1: Acompanhar  Botão 2: Novo serviço  Botão 3: Voltar"

    "Ela não possui mais utilizações de encanador"
    "Segurada tem somente 2 utilizações de encanador nessa apólice"

A mesma tela ("Identifiquei em seu cadastro a placa") é respondida com
*Automóvel* pelo corredor de auto e com *Residencial* por este. É o passo que
separa os dois ramos: errar nele atende o carro de quem pediu encanador.

E o limite de utilizações é guardrail de verdade: esgotado, não existe
acionamento — é handoff com o motivo escrito.

📊 Porto residencial: a rota existe, os subserviços são genéricos.

    "Qual tipo de atendimento você precisa? Serviços para veículo /
     Serviços para residência / Consultar apólice / Voltar"
    "Serviços para residência — Assistência de elétrica, hidráulica e conserto
     de elet[rodomésticos]"
    "Parece que as apólices no CNPJ informado não tem cobertura para serviços
     residenciais. Nestes casos é possível realizar a assistência de forma
     particular."

Nenhum submenu de subserviço foi observado — então este corredor NÃO declara
rótulo de menu por subserviço. Ele chega até a rota residencial e para. E
apólice sem cobertura residencial não vira acionamento: vira handoff, porque
serviço particular é conversa comercial, e ela é de gente.

C.4 · O encanador da Allianz ganhou as perguntas do problema dele
----------------------------------------------------------------
O eletricista pergunta se há fumaça antes de acionar. O encanador existia com os
slots genéricos: nem onde é o vazamento, nem se a água está escorrendo, nem se o
registro foi fechado. Mesma espinha, mesma opção de URA, perguntas do trabalho
certo — guardrail que existe só num corredor não é guardrail, é coincidência.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


for _nome in ("app", "app.services", "app.services.atlas"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(BACKEND, rel))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
DS = _carregar("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
TPL = _carregar("app.services.atlas.templater", "app/services/atlas/templater.py")


# ---------------------------------------------------------------------------
# As frases da URA, como a seguradora escreve (📊 ura_maps observed, 03/08/2026)
# ---------------------------------------------------------------------------
URA = {
    "azul_menu": ("O que você precisa? *1* - Guincho (reboque) *2* - Bateria *3* - Troca de pneu "
                  "*4* - Chaveiro para o veículo *5* - Conserto ou troca de vidro, retrovisor, "
                  "farol ou lanterna"),
    "porto_menu": ("O que você precisa? Guincho (reboque) Bateria Troca de pneu Conserto de vidro "
                   "(Inclui retrovisor, farol ou lanterna) Chaveiro para o veículo Táxi"),
    "porto_formulario": ("Certo. Para conserto ou reparo de vidro, retrovisor, farol ou lanterna, "
                         "é necessário *preencher o formulário* de sinistro de vidros abaixo"),
    "porto_link": "https://porto.vc/reparovidros",
    "porto_bonus": "Não se preocupe, esse acionamento *para vidros* não irá afetar a sua classe de bônus.",
    "zurich_menu": ("Você deseja acionar qual serviço? Acionar seguro Assistência 24h "
                    "Assistência a vidros Voltar ao menu"),
    "zurich_info": ("*Assistência a vidros*: encontre informações sobre como pedir o reparo ou a "
                    "troca de vidros, para-brisa, faróis e retrovisores"),
    "hdi_desambiguacao": ("Identifiquei em seu cadastro a placa ABC1D23. Deseja continuar com o "
                          "atendimento para o veículo ou atendimento residencial? "
                          "Botão 1: Automóvel Botão 2: Residencial"),
    "hdi_menu_resid": ("Qual é o serviço que você precisa solicitar? "
                       "Encanador - Selecione para conserto de vazamentos como torneiras, sifões, etc "
                       "Desentupimento - Selecione esta opção se precisa de um desentupimento residencial "
                       "Eletricista Chaveiro Eletrodoméstico"),
    "hdi_acompanhar": ("Para esse CPF localizamos o serviço de *ENCANADOR*. Deseja acompanhar? "
                       "Botão 1: Acompanhar Botão 2: Novo serviço Botão 3: Voltar"),
    "hdi_sem_utilizacoes": "Ela não possui mais utilizações de encanador",
    "hdi_utilizacoes_restantes": "Segurada tem somente 2 utilizações de encanador nessa apólice",
    "porto_tipo_atendimento": ("Qual tipo de atendimento você precisa? Serviços para veículo "
                               "Serviços para residência Consultar apólice Voltar"),
    "porto_sem_cobertura": ("Parece que as apólices no CNPJ informado não tem cobertura para "
                            "serviços residenciais. Nestes casos é possível realizar a assistência "
                            "de forma particular."),
}

# Caso sintético (nada real). Vidro não tem local_atual/local_destino de propósito.
CASO_VIDROS = {
    "titular_cpf": "11122233344",
    "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23",
    "problema_descricao": "trinca de 20cm no para-brisa, lado do motorista",
    "quando": "03/08/2026",
    "telefone_contato": "48991234567",
}
CASO_AUTO = {
    **CASO_VIDROS,
    "local_atual": "Rua das Flores, 100, Centro, Florianopolis SC",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose SC",
    "pessoa_no_local": "Fulano de Tal",
}
CASO_RESID = {
    "titular_cpf": "11122233344",
    "titular_nome": "Fulano de Tal",
    "telefone_contato": "48991234567",
    "problema_descricao": "vazamento embaixo da pia da cozinha",
    "vazamento_local": "pia da cozinha",
    "agua_escorrendo": "sim, pinga sem parar",
    "risco_confirmado_registro_fechado": "sim, o registro foi fechado",
}

AUTO_TODAS = ("allianz", "porto", "hdi", "yelum", "tokio", "alfa", "azul",
              "bradesco", "mapfre", "zurich")
COM_VIDROS = {"azul": "5", "porto": "Conserto de vidro", "zurich": "Assistência a vidros"}
SEM_VIDROS = [i for i in AUTO_TODAS if i not in COM_VIDROS]


def _pb_auto(insurer: str) -> dict:
    return PB.get_playbook(PB.resolve_playbook_ref(insurer, "auto"))


def _saidas(sessao: dict) -> list:
    return [t["text"] for t in sessao["transcript"] if t["direction"] == "out"]


# ===========================================================================


def teste_vidros_so_existe_onde_foi_visto():
    print("\n[C1] Vidros existe nas TRES que foram observadas — e em mais nenhuma")
    for insurer, valor in COM_VIDROS.items():
        pbk = _pb_auto(insurer)
        checar(PB.subservice_supported(pbk, "vidros"), f"{insurer}: oferece vidros")
        checar(PB.auto_subservice_menu_value(pbk, "vidros") == valor,
               f"{insurer}: responde o menu com o rotulo/tecla observado",
               repr(PB.auto_subservice_menu_value(pbk, "vidros")))

    for insurer in SEM_VIDROS:
        pbk = _pb_auto(insurer)
        checar(not PB.subservice_supported(pbk, "vidros"),
               f"{insurer}: NAO oferece vidros (sem evidencia de menu)")
        checar(PB.auto_subservice_menu_value(pbk, "vidros") == "",
               f"{insurer}: e nao tem tecla nenhuma para chutar",
               repr(PB.auto_subservice_menu_value(pbk, "vidros")))
        checar(PB.missing_slots_for_subservice(pbk, "vidros", CASO_VIDROS) == ["subservico_invalido"],
               f"{insurer}: mesmo com o caso COMPLETO, o pedido nao vira acionamento",
               "e subservico_invalido e o que o motor transforma em handoff")
        sessao = DS.new_dispatch_session(case_id="v", company_id="co",
                                         playbook_ref=PB.resolve_playbook_ref(insurer, "auto"),
                                         subservice="vidros", slots=CASO_VIDROS)
        checar(sessao["state"] != "ready_to_send" and "subservico_invalido" in sessao["missing_slots"],
               f"{insurer}: a sessao NUNCA fica pronta para enviar", str(sessao.get("missing_slots")))

    checar(PB.canonical_subservice("vidro") == "vidros"
           and PB.canonical_subservice("para-brisa") == "vidros",
           "o cliente pode dizer 'vidro' ou 'para-brisa' — o corredor e o mesmo")
    checar(PB.subservice_supported(_pb_auto("azul"), "para-brisa"),
           "e o apelido chega ao subservico de verdade, nao a um vazio")


def teste_vidros_nao_pede_reboque():
    print("\n[C2] Vidro nao e reboque: nao se pergunta onde o carro esta nem para onde levar")
    azul = _pb_auto("azul")
    faltam = PB.missing_slots_for_subservice(azul, "vidros", {})
    checar(faltam == ["titular_cpf", "veiculo_placa", "problema_descricao", "quando", "telefone_contato"],
           "os slots de vidros sao CPF, placa, dano, data e telefone — nessa ordem", str(faltam))
    checar("local_atual" not in faltam and "local_destino" not in faltam,
           "sem local_atual e sem local_destino",
           "sao os dois campos que so fazem sentido quando alguem reboca o carro")
    guincho = PB.missing_slots_for_subservice(azul, "guincho", {})
    checar("local_atual" in guincho and "local_destino" in guincho,
           "e o guincho continua exigindo os dois — a derivacao nao borrou as rotas")
    sessao = DS.new_dispatch_session(case_id="v1", company_id="co",
                                     playbook_ref="azul-auto-whatsapp@v1",
                                     subservice="vidros", slots=CASO_VIDROS)
    checar(sessao["state"] == "ready_to_send",
           "com CPF, placa, dano e data o acionamento de vidro fica PRONTO",
           str(sessao.get("missing_slots")))


def teste_o_desfecho_esta_declarado_por_seguradora():
    print("\n[C3] Cada seguradora declara COMO o corredor de vidros termina")
    azul, porto, zurich = _pb_auto("azul"), _pb_auto("porto"), _pb_auto("zurich")
    checar(PB.subservice_outcome(azul, "vidros") == PB.OUTCOME_ABRE,
           "Azul ABRE: vidro e tecla no menu e o fluxo segue ate o protocolo",
           PB.subservice_outcome(azul, "vidros"))
    checar(PB.subservice_outcome(porto, "vidros") == PB.OUTCOME_ENCAMINHA,
           "Porto ENCAMINHA: o fluxo termina num formulario", PB.subservice_outcome(porto, "vidros"))
    checar(PB.subservice_outcome(zurich, "vidros") == PB.OUTCOME_ENCAMINHA,
           "Zurich ENCAMINHA: o fluxo entrega orientacao", PB.subservice_outcome(zurich, "vidros"))
    checar(PB.subservice_outcome(azul, "guincho") == PB.OUTCOME_ABRE,
           "e o padrao de todo o resto continua sendo ABRIR")
    checar(PB.subservice_outcome(_pb_auto("allianz"), "vidros") == "",
           "seguradora sem o subservico nao tem desfecho nenhum — nao ha o que declarar")

    ref_porto = PB.subservice_referral(porto, "vidros")
    checar(ref_porto.get("kind") == "formulario"
           and ref_porto.get("closes_as") == "resolvido_por_encaminhamento",
           "o encaminhamento da Porto se declara formulario e diz como o caso encerra")
    checar("classe de bônus" in ref_porto.get("client_message", ""),
           "e leva ao segurado o que a propria URA diz sobre a classe de bonus",
           "e a frase que tira o medo de acionar vidro")
    checar("NESTA conversa" in ref_porto.get("client_message", ""),
           "mandando usar o link que a seguradora enviou, nunca um de memoria")
    checar("http" not in ref_porto.get("client_message", ""),
           "e a URL NAO esta escrita no texto ao cliente",
           "link de seguradora muda; link decorado no codigo vira link morto na mao do segurado")
    checar(PB.subservice_referral(zurich, "vidros").get("kind") == "orientacao",
           "a Zurich se declara orientacao — que e outra coisa, e o texto ao cliente muda")
    checar(PB.subservice_referral(azul, "vidros") == {},
           "quem ABRE nao tem encaminhamento declarado")


def teste_as_frases_reais_da_ura_de_vidros_casam():
    print("\n[C4] Os rotulos REAIS da URA batem com o corredor (chamada de funcao, nao grep)")
    # AZUL: menu numerado -> tecla 5
    s = DS.start_dispatch(DS.new_dispatch_session(
        case_id="az", company_id="co", playbook_ref="azul-auto-whatsapp@v1",
        subservice="vidros", slots=CASO_VIDROS))
    s = DS.handle_insurer_message(s, URA["azul_menu"])
    checar(_saidas(s)[-1:] == ["5"], "Azul: o menu real de 5 opcoes e respondido com 5",
           str(_saidas(s)[-1:]))

    # PORTO: menu por rotulo -> "Conserto de vidro"
    sp = DS.start_dispatch(DS.new_dispatch_session(
        case_id="po", company_id="co", playbook_ref="porto-auto-whatsapp@v1",
        subservice="vidros", slots=CASO_VIDROS))
    sp = DS.handle_insurer_message(sp, URA["porto_menu"])
    checar(_saidas(sp)[-1:] == ["Conserto de vidro"],
           "Porto: a lista real e respondida com o rotulo completo", str(_saidas(sp)[-1:]))

    # PORTO: a mensagem do formulario NAO e respondida — e e reconhecida como encaminhamento
    antes = len(_saidas(sp))
    sp = DS.handle_insurer_message(sp, URA["porto_formulario"])
    checar(len(_saidas(sp)) == antes,
           "Porto: a mensagem do formulario NAO recebe resposta",
           "responder qualquer coisa aqui empurraria a URA para um passo que nao existe")
    checar(sp["state"] not in ("needs_human", "test_aborted"),
           "e ela tambem nao vira handoff nem freio — o corredor sabe o que e", str(sp.get("reason")))
    passo = PB.detect_referral_step(_pb_auto("porto"), URA["porto_formulario"])
    checar(passo is not None and passo.get("step") == "vidros_formulario",
           "e o motor reconhece o passo de ENCAMINHAMENTO pelo texto real",
           str(passo and passo.get("step")))
    checar(PB.detect_finalize_anchor(_pb_auto("porto"), URA["porto_formulario"]) is None,
           "encaminhar nao e confirmar: o freio de finalizacao nao dispara aqui")
    sp = DS.handle_insurer_message(sp, URA["porto_link"])
    checar(sp.get("captured", {}).get("tracking_link") == URA["porto_link"],
           "o link do formulario e CAPTURADO da mensagem da seguradora, nao escrito no codigo",
           str(sp.get("captured")))

    # ZURICH: so o corredor de vidros responde o menu 'acionar qual servico'
    sz = DS.start_dispatch(DS.new_dispatch_session(
        case_id="zu", company_id="co", playbook_ref="zurich-auto-whatsapp@v1",
        subservice="vidros", slots=CASO_VIDROS))
    sz = DS.handle_insurer_message(sz, URA["zurich_menu"])
    checar(_saidas(sz)[-1:] == ["Assistência a vidros"],
           "Zurich: o menu real e respondido com o rotulo de vidros", str(_saidas(sz)[-1:]))
    passo_guincho = PB.match_ura_step(_pb_auto("zurich"), URA["zurich_menu"], subservice="guincho")
    checar(passo_guincho is None or passo_guincho.get("step") != "menu_acionar_servico_vidros",
           "e um caso de GUINCHO nao responde esse menu",
           "o rotulo dos outros servicos varia com a apolice — chutar seria apertar a tecla errada")
    antes_z = len(_saidas(sz))
    sz = DS.handle_insurer_message(sz, URA["zurich_info"])
    checar(len(_saidas(sz)) == antes_z, "Zurich: o texto informativo de vidros nao e respondido")
    passo_z = PB.detect_referral_step(_pb_auto("zurich"), URA["zurich_info"])
    checar(passo_z is not None and passo_z.get("step") == "vidros_orientacao",
           "e e reconhecido como encaminhamento", str(passo_z and passo_z.get("step")))


def teste_pane_seca_entra_pelo_guincho():
    print("\n[C5] Pane seca NAO virou subservico — virou caminho para o guincho")
    for insurer in AUTO_TODAS:
        pbk = _pb_auto(insurer)
        checar("pane_seca" not in (pbk.get("subservices") or {}),
               f"{insurer}: nao existe subservico 'pane_seca' inventado")
    checar(all(PB.canonical_subservice(x) == "guincho"
               for x in ("pane seca", "pane_seca", "PANE SECA", "combustivel", "sem combustivel")),
           "todas as formas de dizer pane seca chegam em guincho")

    allianz = _pb_auto("allianz")
    checar(PB.missing_slots_for_subservice(allianz, "pane_seca", {})
           == PB.missing_slots_for_subservice(allianz, "guincho", {}),
           "e pedem exatamente os dados do guincho — nem um a mais, nem um a menos")
    checar(PB.auto_subservice_menu_value(allianz, "pane_seca") == "3"
           and PB.auto_subservice_menu_value(_pb_auto("porto"), "pane seca") == "Guincho (reboque)",
           "e apertam a tecla do guincho: '3' na Allianz, o rotulo na Porto",
           f"{PB.auto_subservice_menu_value(allianz, 'pane_seca')} / "
           f"{PB.auto_subservice_menu_value(_pb_auto('porto'), 'pane seca')}")

    s = DS.new_dispatch_session(case_id="ps", company_id="co",
                                playbook_ref="allianz-auto-whatsapp@v1",
                                subservice="pane_seca", slots=CASO_AUTO)
    checar(s["state"] == "ready_to_send" and s["slots"].get("servico_opcao") == "3",
           "um caso de pane seca monta a sessao do guincho, pronta para enviar",
           f"{s['state']} / {s['slots'].get('servico_opcao')}")

    # A ponta que fecha o circuito: o classificador que o Atlas ja usa.
    ramo, servico = TPL.infer_ramo_servico([], "acabou o combustivel na estrada, o carro parou")
    checar((ramo, servico) == ("auto", "pane_seca"),
           "o classificador do Atlas continua devolvendo 'pane_seca'", f"{ramo}/{servico}")
    checar(PB.canonical_subservice(servico) == "guincho",
           "e o que ele devolve chega ao guincho sem um segundo classificador no meio",
           "era exatamente aqui que o caso morria: 'pane_seca' nao existia em lugar nenhum")


def teste_residencial_da_hdi():
    print("\n[C6] HDI residencial — o mais bem observado do acervo")
    ref = PB.resolve_playbook_ref("HDI", "residencial")
    checar(ref == "hdi-residencial-whatsapp@v1", "HDI/residencial resolve o corredor novo", str(ref))
    pbk = PB.get_playbook(ref)
    checar(sorted(pbk["subservices"]) == ["chaveiro", "desentupimento", "eletricista",
                                          "eletrodomesticos", "encanador"],
           "os cinco subservicos da lista real, e so eles", str(sorted(pbk["subservices"])))

    # O passo que separa os dois ramos: MESMA tela, respostas opostas.
    passo_resid = PB.match_ura_step(pbk, URA["hdi_desambiguacao"])
    passo_auto = PB.match_ura_step(_pb_auto("hdi"), URA["hdi_desambiguacao"])
    checar(passo_resid is not None and passo_resid["reply"] == "Residencial",
           "na tela 'veiculo ou residencial?', este corredor responde Residencial",
           str(passo_resid and passo_resid.get("reply")))
    checar(passo_auto is not None and passo_auto["reply"] == "Automóvel",
           "e o corredor de AUTO responde Automovel na MESMA tela",
           str(passo_auto and passo_auto.get("reply")))

    s = DS.new_dispatch_session(case_id="h1", company_id="co", playbook_ref=ref,
                                subservice="encanador", slots=CASO_RESID)
    checar(s["state"] == "ready_to_send", "o caso de encanador monta a sessao", str(s.get("missing_slots")))
    s = DS.start_dispatch(s)
    s = DS.handle_insurer_message(s, URA["hdi_desambiguacao"])
    checar(_saidas(s)[-1:] == ["Residencial"], "e responde Residencial de verdade", str(_saidas(s)[-1:]))
    s = DS.handle_insurer_message(s, URA["hdi_menu_resid"])
    checar(_saidas(s)[-1:] == ["Encanador"],
           "no menu real de servicos, escolhe o rotulo Encanador", str(_saidas(s)[-1:]))
    s = DS.handle_insurer_message(s, URA["hdi_acompanhar"])
    checar(_saidas(s)[-1:] == ["Novo serviço"],
           "e diante de um chamado ja aberto, pede NOVO servico",
           "o cliente ligou hoje por um problema de hoje; acompanhar o antigo e outro trabalho")

    # O limite de utilizacoes: um informa, o outro impede.
    antes = len(_saidas(s))
    s = DS.handle_insurer_message(s, URA["hdi_utilizacoes_restantes"])
    checar(len(_saidas(s)) == antes and s["state"] not in ("needs_human", "test_aborted"),
           "'tem somente 2 utilizacoes' e informativo: nao se responde e nao se para",
           str(s.get("reason")))
    checar(PB.detect_handoff_trigger(pbk, URA["hdi_sem_utilizacoes"]) is not None,
           "'nao possui mais utilizacoes' PARA o acionamento",
           "apolice sem utilizacao nao tem o que acionar — insistir so queima o tempo do segurado")
    s2 = DS.start_dispatch(DS.new_dispatch_session(
        case_id="h2", company_id="co", playbook_ref=ref, subservice="encanador", slots=CASO_RESID))
    s2 = DS.handle_insurer_message(s2, URA["hdi_sem_utilizacoes"])
    checar(s2["state"] == "needs_human", "e o motor devolve o caso ao humano de verdade",
           f"{s2['state']} / {s2.get('reason')}")
    checar(len(pbk.get("coverage_guardrails") or []) >= 2,
           "o limite por apolice fica escrito como guardrail, nao so no comentario")


def teste_residencial_da_porto():
    print("\n[C7] Porto residencial — a rota existe, os subservicos sao genericos")
    ref = PB.resolve_playbook_ref("Porto Seguro", "residencial")
    checar(ref == "porto-residencial-whatsapp@v1", "Porto/residencial resolve o corredor novo", str(ref))
    pbk = PB.get_playbook(ref)
    checar(sorted(pbk["subservices"]) == ["eletricista", "eletrodomesticos", "encanador"],
           "tres subservicos, nas chaves canonicas do produto", str(sorted(pbk["subservices"])))
    checar(PB.canonical_subservice("hidraulica") == "encanador"
           and PB.canonical_subservice("eletrica") == "eletricista",
           "as palavras da Porto ('hidraulica', 'eletrica') traduzem para as canonicas",
           "senao o mesmo trabalho teria dois nomes e o acervo se partiria em dois")
    checar(not (pbk.get("subservice_menu_map") or {}),
           "e NAO ha rotulo de menu por subservico — nenhum submenu foi observado",
           "declarar um rotulo aqui seria adivinhar a tecla")

    s = DS.start_dispatch(DS.new_dispatch_session(
        case_id="p1", company_id="co", playbook_ref=ref, subservice="encanador", slots=CASO_RESID))
    s = DS.handle_insurer_message(s, URA["porto_tipo_atendimento"])
    checar(_saidas(s)[-1:] == ["Serviços para residência"],
           "na lista real de tipo de atendimento, escolhe a rota residencial", str(_saidas(s)[-1:]))

    s = DS.handle_insurer_message(s, URA["porto_sem_cobertura"])
    checar(s["state"] == "needs_human",
           "apolice sem cobertura residencial NAO vira acionamento",
           "a URA oferece 'assistencia de forma particular' — isso e conversa comercial, e e de gente")

    checar(PB.resolve_playbook_ref("Itau", "residencial") is None,
           "e o Itau NAO herda este corredor",
           "a carteira de AUTO do Itau roda na Porto; residencial ele vende em nome proprio")
    checar(PB.resolve_playbook_ref("Itau", "auto") == "porto-auto-whatsapp@v1",
           "enquanto o auto do Itau continua indo para a Porto — a distincao e por carteira")


def teste_o_encanador_da_allianz_pergunta_do_vazamento():
    print("\n[C8] O encanador da Allianz ganhou as perguntas do problema dele")
    pbk = PB.get_playbook("allianz-residencial-whatsapp@v1")
    faltam = PB.missing_slots_for_subservice(pbk, "encanador", {})
    for slot in ("vazamento_local", "agua_escorrendo", "risco_confirmado_registro_fechado"):
        checar(slot in faltam, f"o encanador exige {slot}")
    checar(pbk["subservices"]["encanador"]["tipo_servico_opcao"]
           == pbk["subservices"]["eletricista"]["tipo_servico_opcao"],
           "e entra pela MESMA opcao de URA do eletricista — a espinha foi copiada, nao reinventada")

    # A trava de risco, com o caso quase completo.
    quase = {k: v for k, v in CASO_RESID.items() if k != "risco_confirmado_registro_fechado"}
    quase["endereco_numero"] = "1678"
    quase["periodo_preferido"] = "tarde"
    checar(PB.missing_slots_for_subservice(pbk, "encanador", quase) == ["risco_confirmado_registro_fechado"],
           "sem saber se o registro foi fechado, o encanador nao e acionado",
           "e a pergunta que separa 'pinga a torneira' de 'esta alagando'")

    eletricista = PB.missing_slots_for_subservice(pbk, "eletricista", {})
    checar(eletricista == ["titular_cpf", "endereco_numero", "telefone_contato",
                           "problema_descricao", "periodo_preferido", "risco_confirmado_sem_fumaca"],
           "e o eletricista continua com a lista dele, intacta", str(eletricista))
    checar("risco_confirmado_sem_fumaca" in
           PB.missing_slots_for_subservice(PB.get_playbook("hdi-residencial-whatsapp@v1"),
                                           "eletricista", {}),
           "o guardrail de risco eletrico tambem vale na HDI",
           "pergunta do TRABALHO, nao da seguradora — senao e coincidencia, nao guardrail")


def main() -> int:
    print("=" * 68)
    print("CORREDORES NOVOS — VIDROS, PANE SECA, RESIDENCIAL HDI/PORTO, ENCANADOR")
    print("=" * 68)
    for t in (teste_vidros_so_existe_onde_foi_visto,
              teste_vidros_nao_pede_reboque,
              teste_o_desfecho_esta_declarado_por_seguradora,
              teste_as_frases_reais_da_ura_de_vidros_casam,
              teste_pane_seca_entra_pelo_guincho,
              teste_residencial_da_hdi,
              teste_residencial_da_porto,
              teste_o_encanador_da_allianz_pergunta_do_vazamento):
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
    print("OS CORREDORES NOVOS SO DIZEM O QUE FOI VISTO — E PARAM ONDE A EVIDENCIA PARA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
