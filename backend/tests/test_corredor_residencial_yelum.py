"""O residencial da YELUM — e as seis telas em que copiar a HDI teria emudecido.

Por que este corredor, e por que agora
--------------------------------------
📊 04/08/2026, `observed_events` no banco de produção `dcajcvlzcjbmyapmklil`,
contagem por `insurer_key`::

    sinal                                        yelum   hdi
    eventos totais                                3.026  2.074
    "Identifiquei ... a placa" (desambiguação)       23      8
    encanador                                        44     28
    eletricista                                      39     27
    chaveiro                                         46     33
    "utilizações"                                     0      4

A Yelum tinha MAIS evidência residencial do que a HDI tinha quando o corredor
dela foi escrito — e não tinha corredor. São 6 sessões residenciais completas,
três delas 100% pelo bot até o protocolo (8981006 · 9124710 · 9666474).

A armadilha: HDI e Yelum são o MESMO bot white-label
-----------------------------------------------------
Mesmo produto, mesmo `flow_id` no corredor de auto, telas com o mesmo desenho.
A tentação era copiar `HDI_RESIDENCIAL_WHATSAPP_V1` e trocar o `insurer_key`.

**A medição desautorizou a cópia.** Rodando cada regex da família/HDI contra a
mensagem literal da Yelum, SEIS âncoras não casam::

    passo                âncora HDI/família              a Yelum escreve
    identificacao        "informe somente o *CPF ou      "informe o *CPF ou CNPJ*
                          CNPJ* do titular"               que deseja atendimento"
    informar_nome        "informe O SEU nome ou como"    "Me informe SEU *nome* ou como"
    perfil               "em qual dessas opções você     "escolha a opção que melhor
                          se enquadra"                    te representa"
    confirma_endereco    "você confirma O endereço"      "Você confirma ESTE endereço?"
    nome_pessoa_local    "qual é o nome da pessoa que    "nome da pessoa responsável por
                          está no local"                  acompanhar o técnico no local"
    servico_ja_aberto    "localizamos O SERVIÇO DE X"    "localizamos ALGUMAS ASSISTÊNCIAS"

Uma delas é a PRIMEIRA tela do atendimento. Um corredor copiado emudeceria na
porta de entrada — e o caso do segurado morreria em "aguardando".

E o menu tem outro rótulo
-------------------------
📊 A Yelum chama eletrodoméstico de **"Linha branca"**::

    "Qual é o serviço que você precisa solicitar?
     Encanador / Desentupimento / Eletricista / Chaveiro /
     Linha branca / Ar condicionado / Voltar"

Responder "Eletrodoméstico" (o rótulo da HDI) aperta uma tecla que não existe.

O que este corredor NÃO promete
-------------------------------
📊 `utilizações`: ZERO ocorrências na Yelum. O passo `utilizacoes_restantes`, o
gatilho "não possui mais utilizações" e os guardrails de limite por apólice
ficam de FORA. Quem cobre a lacuna não é uma lista de frases: é
`unknown_step_policy: pause_and_handoff`. Corredor que promete passo sem
evidência é o defeito que criou os `corridor_runs` abandonados — e o caso [Y6]
testa que a promessa NÃO foi feita.

E o protocolo, que nenhum corredor da família capturava
-------------------------------------------------------
📊 30 mensagens de HDI, Yelum e Allianz trazem `*Assistência:* 9666474` — o
`*Resumo da solicitação*`, a última mensagem do acionamento. `_ANCORA_DE_PROTOCOLO`
não casava NENHUMA: as alternativas exigiam "número DA assistência" ou "PARA A
assistência", e a etiqueta sozinha não estava prevista. Rodando o motor de
verdade, `captured` voltava `{}` — o corredor abria o serviço, via o número na
tela e encerrava sem ele. O caso [Y7] mede isso, com controle.
"""

from __future__ import annotations

import importlib.util
import os
import re
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

# ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — o FREIO DE FINALIZAÇÃO
# deixou de ser o padrão. Ele existia porque o Founder testava no próprio
# celular; a decisão dele foi que a única trava passa a ser o agente desligado,
# e `DISPATCH_FINALIZE_MODE` nasce em `live`.
#
# O caso [Y5] deste arquivo prova que a tela do ponto de não-retorno PARA o
# motor — e isso continua sendo verdade e continua valendo a pena provar. O que
# muda é que agora o ensaio é ARMADO de propósito, em vez de herdado. Um teste
# que dependia de um padrão parou de testar no instante em que o padrão mudou.
os.environ["DISPATCH_FINALIZE_MODE"] = "test"

REF = "yelum-residencial-whatsapp@v1"

# ---------------------------------------------------------------------------
# As telas, como a Yelum as escreve. Copiadas de `observed_events` (04/08/2026),
# incluindo asteriscos de negrito e emoji dos botões — é assim que chegam.
# ---------------------------------------------------------------------------
URA = {
    "abertura": "Olá, seja bem-vindo ao atendimento digital de *Assistência 24 horas* da *Yelum Seguradora!*",
    "menu_auto_ou_resid": ("Você gostaria de solicitar serviços ou acompanhar serviços de assistência "
                           "para seu *automóvel* ou *residência*?\n\nSelecione abaixo a opção de sua "
                           "preferência.\nBotão 1: 🚗 Automóvel\nBotão 2: 🏠 Residência"),
    "desambiguacao": ("Identifiquei em seu cadastro a placa AXI0132.\nDeseja continuar com o "
                      "atendimento para o veículo ou atendimento residencial?\n"
                      "Botão 1: Automóvel\nBotão 2: Residencial"),
    # A redação que a âncora da HDI NÃO pegava — e é a primeira tela do fluxo.
    "cpf_nova": ("Para prosseguirmos vou precisar de alguns dados para melhor atendê-lo. Por favor "
                 "informe o *CPF ou CNPJ* que deseja atendimento.\n\nExemplo: *12345678900*"),
    "cpf_classica": ("Para começar, me informe somente o *CPF ou CNPJ* do títular da apólice.\n\n"
                     "*Exemplo*: 123.456.789-00"),
    "nome": "Me informe seu *nome* ou como *gostaria de ser chamado*.",
    "perfil": ("Por favor, escolha a opção que melhor te representa:\nBotão 1: Sou segurado(a)\n"
               "Botão 2: Sou corretor(a)\nBotão 3: Outro"),
    "pessoa_no_local": "Saionara você é a pessoa que está local para acompanhar o serviço?\nBotão 1: Sim\nBotão 2: Não",
    "nome_pessoa": "Saionara - Resulta, qual é o nome da pessoa responsável por acompanhar o técnico no local?",
    "nome_pessoa2": "Por favor, informe o nome da pessoa que estará na residência para receber o técnico.",
    "telefone": ("Por gentileza me informe o *número de celular* com DDD da pessoa que está no local, "
                 "seguindo de 9 dígitos do telefone:"),
    "telefone_confirma": "O número de telefone 48991883451 está correto?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar",
    "endereco_apolice": ("Para esse CPF informado localizamos o seguinte endereço:\n\n*Rua:* Professor "
                         "Antônio Pereira Gutierrez\n*Numero:* 112\n*Bairro:* Santa Mônica"),
    "confirma_endereco": "Você confirma este endereço?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar",
    "casa_ou_cond": "Sua residência é uma casa individual ou está localizada em um condomínio?\nBotão 1: Casa\nBotão 2: Condomínio",
    "casa_ou_cond2": ("Para continuarmos, você poderia confirmar se sua residência é uma casa ou fica "
                      "em um condomínio/prédio?\nBotão 1: Casa\nBotão 2: Condomínio/prédio"),
    "referencia": ("Agora, preciso que você me informe pelo menos uma referência.\n\n"
                   "*Ex: Próximo ao Banco Z ou Em frente ao Supermercado Y*"),
    "menu_servico": ("Saionara - Resulta, estamos prontos para seguir com o seu atendimento.\n\n"
                     "Qual é o serviço que você precisa solicitar?\nEncanador\nSelecione para conserto "
                     "de vazamentos como torneiras, sifões, etc\nDesentupimento\nSelecione se precisa de "
                     "um desentupimento\nEletricista\nSelecione se precisa de um reparo elétrico\n"
                     "Chaveiro\nSelecione se está com problemas na fechadura da entrada principal\n"
                     "Linha branca\nSelecione esta opção se tem algum eletrodoméstico com defeito\n"
                     "Ar condicionado\nSelecione esta opção para conserto e limpeza de ar condicionado\nVoltar"),
    "menu_servico2": ("Qual o serviço que você precisa?\nEncanador\nSelecione esta opção se está com um "
                      "vazamento aparente\nDesentupimento\nEletricista\nChaveiro\nLinha branca\n"
                      "Ar condicionado\nVoltar"),
    "ja_aberto": ("Para esse CPF localizamos o serviço de *CHAVEIRO RESIDENCIAL*. Deseja acompanhar?\n"
                  "Botão 1: Acompanhar\nBotão 2: Novo serviço\nBotão 3: Voltar"),
    "ja_aberto2": ("Para esse CPF localizamos algumas assistências.\nDeseja acompanhar?\n"
                   "Botão 1: Acompanhar\nBotão 2: Novo serviço\nBotão 3: Voltar"),
    "recado_encanador": ("*Para continuar com a sua solicitação temos um recado:*\n\nReparos emergenciais "
                         "em virtude de vazamento (aparente) em tubulações em PVC de 1 a 4 polegadas"),
    "vazamento": ("Qual desses itens está com vazamento?\nTorneira\nTorneira elétrica\nSifão\nChuveiro\n"
                  "Válvulas de descarga\nRegistro\nMais opções\nVoltar"),
    "comodo": "Em qual cômodo?\nBotão 1: Cozinha\nBotão 2: Banheiro\nBotão 3: Lavanderia",
    "agora_ou_agendar": ("Você precisa do atendimento agora ou prefere agendar para outro momento?\n"
                         "Botão 1: Agora\nBotão 2: Agendar\nBotão 3: Voltar"),
    "resumo": ("*Resumo da solicitação*\n\n*Assistência:* 9666474\n*Telefone:* 48991072089\n"
               "*Serviço:* Encanador\n*Endereço:* Rua Professor Antônio Pereira Gutierrez - 112 - "
               "Santa Mônica - Florianópolis - SC\n*Solicitação:* Emergencial"),
    "senha": ("A senha para a visita técnica corresponde aos *4 últimos dígitos* do número de celular "
              "informado da pessoa que estará no local ou do *WhatsApp utilizado para solicitar a "
              "assistência.* Essa senha deve ser repassada ao técnico assim que ele chegar."),
    "transfere": ("*Saionara - Resulta*, por ser um item essencial, vou te transferir para que um de "
                  "nossos analistas de continuidade ao atendimento."),
    "satisfacao": ("O quão satisfeito você está com o atendimento do Whatsapp?\n\nConsiderando "
                   "*5 muito bom e 1 muito ruim*.\n1\n2\n3\n4\n5"),
}

# Caso sintético (nada real).
CASO_RESID = {
    "titular_cpf": "11122233344",
    "titular_nome": "Fulano de Tal",
    "telefone_contato": "48991234567",
    "problema_descricao": "vazamento embaixo da pia da cozinha",
    "vazamento_local": "Torneira",
    "agua_escorrendo": "sim, pinga sem parar",
    "risco_confirmado_registro_fechado": "sim, o registro foi fechado",
    "pessoa_no_local": "Fulano de Tal",
}


def _pb():
    return PB.get_playbook(REF)


def _saidas(sessao: dict) -> list:
    return [t["text"] for t in sessao["transcript"] if t["direction"] == "out"]


def _sessao(subservico: str = "encanador"):
    return DS.start_dispatch(DS.new_dispatch_session(
        case_id="y1", company_id="co", playbook_ref=REF,
        subservice=subservico, slots=CASO_RESID))


# ===========================================================================


def teste_o_corredor_existe_e_resolve():
    print("\n[Y1] Yelum/residencial resolve o corredor novo")
    checar(PB.resolve_playbook_ref("Yelum", "residencial") == REF,
           "Yelum + residencial resolve", str(PB.resolve_playbook_ref("Yelum", "residencial")))
    checar(PB.resolve_playbook_ref("Liberty Seguros", "residencial") == REF,
           "e o nome antigo (Liberty) chega no mesmo corredor",
           "Yelum e ex-Liberty; a apolice velha ainda diz Liberty")
    checar(PB.resolve_playbook_ref("Yelum", "auto") == "yelum-auto-whatsapp@v3",
           "e o AUTO da Yelum continua no corredor dele, intacto",
           str(PB.resolve_playbook_ref("Yelum", "auto")))

    pbk = _pb()
    checar(sorted(pbk["subservices"]) == ["chaveiro", "desentupimento", "eletricista",
                                          "eletrodomesticos", "encanador"],
           "os cinco subservicos do menu real, e so eles", str(sorted(pbk["subservices"])))
    checar(pbk["insurer_contact_ref"] == "yelum_assistencia_24h",
           "e aponta para o contato da Yelum, nao para o da HDI",
           str(pbk["insurer_contact_ref"]))


def teste_o_rotulo_do_menu_e_o_da_yelum():
    print("\n[Y2] 'Linha branca' — o rotulo que a HDI nao usa")
    pbk, hdi = _pb(), PB.get_playbook("hdi-residencial-whatsapp@v1")
    checar(pbk["subservices"]["eletrodomesticos"]["tipo_servico_opcao"] == "Linha branca",
           "eletrodomestico entra pela tecla 'Linha branca'",
           str(pbk["subservices"]["eletrodomesticos"]["tipo_servico_opcao"]))
    checar(hdi["subservices"]["eletrodomesticos"]["tipo_servico_opcao"] == "Eletrodoméstico",
           "e a HDI continua com 'Eletrodoméstico' — sao telas diferentes")
    checar(pbk["subservices"]["eletrodomesticos"]["tipo_servico_opcao"]
           != hdi["subservices"]["eletrodomesticos"]["tipo_servico_opcao"],
           "os dois corredores DIVERGEM aqui de proposito",
           "se algum dia ficarem iguais, alguem copiou um no outro sem medir")

    # A chave continua canonica: o vocabulario do produto nao se parte em dois.
    checar(PB.canonical_subservice("linha branca") in ("eletrodomesticos", "linha branca"),
           "e a chave do produto continua sendo 'eletrodomesticos'",
           "o rotulo e da seguradora; a chave e do produto")

    # A tecla chega ao motor, respondendo o menu REAL.
    s = _sessao("eletrodomesticos")
    s = DS.handle_insurer_message(s, URA["menu_servico"])
    checar(_saidas(s)[-1:] == ["Linha branca"],
           "e no menu real a resposta e 'Linha branca'", str(_saidas(s)[-1:]))


def teste_as_seis_ancoras_que_a_copia_teria_perdido():
    print("\n[Y3] As SEIS telas em que copiar a HDI teria emudecido o corredor")
    yelum, hdi = _pb(), PB.get_playbook("hdi-residencial-whatsapp@v1")

    # Cada par: (tela real da Yelum, passo esperado). O corredor da HDI é o
    # CONTROLE — ele tem de FALHAR nestas telas, senão não havia o que consertar.
    casos = [
        (URA["cpf_nova"], "identificacao_dado", "a primeira tela do atendimento"),
        (URA["nome"], "informar_nome", "'Me informe SEU nome', sem o 'o seu'"),
        (URA["perfil"], "perfil", "'escolha a opcao que melhor te representa'"),
        (URA["confirma_endereco"], "confirma_endereco", "'confirma ESTE endereco', nao 'O endereco'"),
        (URA["nome_pessoa"], "nome_pessoa_local", "'responsavel por acompanhar o TECNICO'"),
        (URA["ja_aberto2"], "servico_ja_aberto", "'localizamos ALGUMAS ASSISTENCIAS'"),
    ]
    for texto, passo_esperado, porque in casos:
        p = PB.match_ura_step(yelum, texto, subservice="encanador")
        checar(p is not None and p.get("step") == passo_esperado,
               f"Yelum casa '{passo_esperado}' — {porque}",
               str(p and p.get("step")))

    # O CONTROLE. Se a HDI casasse estas telas, a copia teria funcionado e este
    # arquivo inteiro estaria guardando uma diferenca que nao existe (§9.3).
    perdidas = [t for t, _, _ in casos
                if PB.match_ura_step(hdi, t, subservice="encanador") is None]
    checar(len(perdidas) == len(casos),
           f"e o corredor da HDI NAO casa nenhuma das {len(casos)} — a copia emudeceria",
           f"a HDI casou {len(casos) - len(perdidas)} delas: a diferenca medida encolheu")

    # E o inverso: onde as duas familias escrevem igual, a ancora e REUSADA.
    for texto, passo in ((URA["telefone"], "telefone_local"),
                         (URA["telefone_confirma"], "telefone_confirma"),
                         (URA["desambiguacao"], "desambiguacao_veiculo_ou_residencial"),
                         (URA["menu_servico"], "menu_servico_residencial")):
        p = PB.match_ura_step(yelum, texto, subservice="encanador")
        checar(p is not None and p.get("step") == passo,
               f"reuso honesto: '{passo}' casa nos dois (mesmo bot, mesma frase)",
               str(p and p.get("step")))


def teste_a_desambiguacao_separa_os_dois_ramos():
    print("\n[Y4] A tela que separa carro de casa — 23 ocorrencias na Yelum")
    resid = PB.match_ura_step(_pb(), URA["desambiguacao"])
    auto = PB.match_ura_step(PB.get_playbook("yelum-auto-whatsapp@v3"), URA["desambiguacao"])
    checar(resid is not None and resid["reply"] == "Residencial",
           "o corredor RESIDENCIAL responde Residencial", str(resid and resid.get("reply")))
    checar(auto is not None and auto["reply"] == "Automóvel",
           "e o de AUTO responde Automovel na MESMA tela",
           "errar aqui atende o carro de quem pediu encanador")

    # E o menu de entrada, que na Yelum tem emoji no rotulo.
    s = _sessao()
    s = DS.handle_insurer_message(s, URA["menu_auto_ou_resid"])
    checar(_saidas(s)[-1:] == ["🏠 Residência"],
           "no menu de entrada, responde o rotulo COM emoji", str(_saidas(s)[-1:]))


def teste_um_acionamento_de_encanador_de_ponta_a_ponta():
    print("\n[Y5] Um encanador inteiro, nas telas reais da sessao 9666474")
    s = DS.new_dispatch_session(case_id="y2", company_id="co", playbook_ref=REF,
                                subservice="encanador", slots=CASO_RESID)
    checar(s["state"] == "ready_to_send", "o caso monta a sessao", str(s.get("missing_slots")))
    s = DS.start_dispatch(s)

    # Saudacao e informativos NAO se respondem.
    for chave in ("abertura", "endereco_apolice", "satisfacao"):
        antes = len(_saidas(s))
        s = DS.handle_insurer_message(s, URA[chave])
        checar(len(_saidas(s)) == antes, f"'{chave}' e informativo: nao recebe resposta",
               f"respondeu {_saidas(s)[-1:]}")

    for chave, esperado in (("cpf_nova", CASO_RESID["titular_cpf"]),
                            ("nome", "Atendimento"),
                            ("perfil", "Sou corretor(a)"),
                            ("pessoa_no_local", "Não"),
                            ("nome_pessoa", CASO_RESID["pessoa_no_local"]),
                            ("telefone", CASO_RESID["telefone_contato"]),
                            ("telefone_confirma", "Sim"),
                            ("confirma_endereco", "Sim"),
                            ("menu_servico", "Encanador"),
                            ("ja_aberto", "Novo serviço")):
        s = DS.handle_insurer_message(s, URA[chave])
        checar(_saidas(s)[-1:] == [esperado], f"'{chave}' -> {esperado!r}", str(_saidas(s)[-1:]))

    # O detalhe do vazamento e do TRABALHO, e cai no slot que ja existia.
    s = DS.handle_insurer_message(s, URA["vazamento"])
    checar(_saidas(s)[-1:] == ["Torneira"],
           "e o item do vazamento sai do slot `vazamento_local`", str(_saidas(s)[-1:]))

    # O PONTO DE NAO-RETORNO: responder ABRE o servico na hora.
    checar(PB.detect_finalize_anchor(_pb(), URA["agora_ou_agendar"]) is not None,
           "'agora ou prefere agendar' e freio de finalizacao",
           "e a tela que ABRE o servico: em teste, o freio cancela antes")
    s2 = _sessao()
    s2 = DS.handle_insurer_message(s2, URA["agora_ou_agendar"])
    checar(s2["state"] in ("test_aborted", "needs_human", "awaiting_approval"),
           "e o motor PARA nela em vez de responder", f"{s2['state']} / {s2.get('reason')}")


def teste_o_que_o_corredor_se_recusa_a_prometer():
    print("\n[Y6] O limite de utilizacoes NAO foi observado — e nao foi declarado")
    yelum, hdi = _pb(), PB.get_playbook("hdi-residencial-whatsapp@v1")
    passos = [p.get("step") for p in yelum["ura_steps"]]

    checar("utilizacoes_restantes" not in passos,
           "nao existe passo de 'utilizacoes restantes' na Yelum",
           "📊 zero ocorrencias de 'utilizacoes' em 3.026 eventos da Yelum")
    checar("utilizacoes_restantes" in [p.get("step") for p in hdi["ura_steps"]],
           "e a HDI TEM esse passo — a diferenca e medida, nao esquecimento",
           "se a HDI perder o passo, este caso vira verdade vencida (§9.3)")
    checar(PB.detect_handoff_trigger(yelum, "Ela nao possui mais utilizacoes de encanador") is None,
           "e o gatilho de limite esgotado nao foi copiado para a Yelum")
    checar(PB.detect_handoff_trigger(hdi, "Ela não possui mais utilizações de encanador") is not None,
           "enquanto na HDI ele existe e dispara")

    # 🔴 ESTA ASSERCAO MUDOU EM 19/08/2026 — e a licao migrou com ela.
    #
    # Ela afirmava `unknown_step_policy == "pause_and_handoff"`. 📊 Medido:
    # essa chave estava declarada em 14 corredores e **nenhuma linha de codigo
    # a lia** (`grep -rn unknown_step_policy app/` so achava as declaracoes).
    # Era configuracao decorativa, e este teste a abencoava — dando a quem
    # lesse a impressao de uma protecao que nao existia.
    #
    # A protecao REAL contra "responder as cegas" e outra, e essa existe:
    # `finalize_anchors` alimenta `pergunta_de_decisao`, que segura o motor em
    # toda tela que ABRE SERVICO. Tela reversivel o cerebro resolve; tela
    # irreversivel para. E isso que se afirma agora.
    checar(len(yelum.get("finalize_anchors") or []) > 0,
           "o corredor declara finalize_anchors — a protecao que o produto LE",
           "sem elas, `pergunta_de_decisao` nao teria como segurar este corredor")
    _decisao = PB.detect_finalize_anchor(
        yelum, "Podemos confirmar a abertura do atendimento?")
    checar(bool(_decisao),
           "e uma tela de CONFIRMACAO e reconhecida como irreversivel")
    checar(not PB.detect_finalize_anchor(yelum, "Qual o servico que voce precisa?"),
           "CONTROLE: e um MENU nao e — senao o discriminador diria 'sim' "
           "para tudo e a afirmacao acima nao mediria nada")
    desconhecida = "Segurada tem somente 2 utilizacoes de encanador nessa apolice"
    checar(PB.match_ura_step(yelum, desconhecida, subservice="encanador") is None,
           "a tela de limite nao casa passo nenhum — e por isso o caso pausa",
           "declarar um passo aqui seria prometer uma tela que nunca vimos")

    # E a lacuna esta ESCRITA, nao so ausente.
    guardrails = " ".join(yelum.get("coverage_guardrails") or [])
    checar("YELUM isso NÃO foi observado" in guardrails or "NÃO foi observado" in guardrails,
           "e a ausencia esta escrita nos guardrails, com o que a destrava",
           "o que fica pendente vai anotado (CLAUDE.md §11.1)")

    # Nada de formulario nativo: sem schema residencial capturado, o corredor
    # pausa em vez de improvisar (o de AUTO ja tem schema, este nao).
    checar(not yelum.get("native_flows"),
           "nao declara `native_flows`: nenhum formulario residencial foi capturado")
    checar(PB.detect_handoff_trigger(yelum, "[FORMULARIO NATIVO] preencha os dados") is not None,
           "e por isso o gatilho de formulario nativo FICA aqui",
           "no corredor de AUTO ele saiu porque o schema e o canal existem")

    # As instrucoes ao cliente sao MEDIDAS na Yelum (a HDI declara lista vazia).
    inst = " ".join(yelum.get("client_instructions") or [])
    checar("4 ÚLTIMOS DÍGITOS" in inst and "MAIOR DE 18 ANOS" in inst,
           "as duas instrucoes ao cliente vem do texto real da Yelum")
    checar(hdi.get("client_instructions") == [],
           "e a HDI segue com lista VAZIA — la elas nao foram observadas",
           "copiar as da Allianz para a HDI seria inventar; aqui elas foram medidas")


def teste_o_protocolo_agora_e_capturado():
    print("\n[Y7] O protocolo do resumo — 30 mensagens que ninguem capturava")
    # A regra, direto: a ancora compartilhada por TODOS os corredores.
    m = re.search(PB._ANCORA_DE_PROTOCOLO, URA["resumo"], re.I | re.S)
    checar(m is not None and m.group(1) == "9666474",
           "'*Assistência:* 9666474' e capturado", str(m and m.group(1)))

    for nome, texto, esperado in (
        ("hdi auto", "*Resumo da solicitação*\n\n*Placa:* AZH0926\n*Assistência:* 9662631", "9662631"),
        ("allianz", "Assistência: 52339760", "52339760"),
        ("hdi finaliza", "Assistência:  9662631  \nFinalizamos o atendimento.", "9662631"),
    ):
        mm = re.search(PB._ANCORA_DE_PROTOCOLO, texto, re.I | re.S)
        checar(mm is not None and mm.group(1) == esperado,
               f"e o mesmo formato de {nome} tambem", str(mm and mm.group(1)))

    # CONTROLE — a ancora tem de RECUSAR o nome do servico, que aparece na
    # saudacao de TODA sessao da familia. Sem isto, o corredor capturaria "24"
    # como protocolo na primeira mensagem.
    for falso in ("Olá, seja bem-vindo ao atendimento digital de *Assistência 24 horas* da *Yelum Seguradora!*",
                  "Assistência 24 horas"):
        checar(re.search(PB._ANCORA_DE_PROTOCOLO, falso, re.I | re.S) is None,
               f"e NAO captura {falso[:34]!r}...",
               "'Assistencia 24 horas' nao tem dois-pontos — e o que separa "
               "a etiqueta do nome do servico")

    # E o motor, de verdade: a sessao termina COM o numero.
    s = _sessao()
    s = DS.handle_insurer_message(s, URA["resumo"])
    checar(s.get("captured", {}).get("protocol") == "9666474",
           "e o motor guarda o protocolo na sessao", str(s.get("captured")))

    # O CONTROLE da ancora: a versao de ANTES nao capturava nada disso.
    ANTES = (r"(?:protocolo(?:\s+de\s+atendimento)?|"
             r"n[úu]mero\s+da\s+(?:sua\s+)?(?:ordem|os|solicita[çc][ãa]o|assist[êe]ncia)|"
             r"para a assist[êe]ncia|sobre sua assist[êe]ncia|o\.?s\.?)"
             r"[^\d]{0,24}(\d[\d-]{4,18}\d)")
    checar(re.search(ANTES, URA["resumo"], re.I | re.S) is None,
           "a ancora de ANTES nao capturava o resumo — era esse o defeito",
           "se este caso ficar vermelho, o conserto nao mudou nada (§9.3)")
    checar(re.search(ANTES, "Seu protocolo de atendimento e 1234567.", re.I) is not None,
           "e ela funcionava para 'protocolo' — os dois lados conseguem ser diferentes")


def teste_o_corredor_da_hdi_continua_inteiro():
    print("\n[Y8] O corredor da HDI nao foi tocado")
    hdi = PB.get_playbook("hdi-residencial-whatsapp@v1")
    checar(sorted(hdi["subservices"]) == ["chaveiro", "desentupimento", "eletricista",
                                          "eletrodomesticos", "encanador"],
           "a HDI segue com os cinco subservicos dela")
    s = DS.start_dispatch(DS.new_dispatch_session(
        case_id="h9", company_id="co", playbook_ref="hdi-residencial-whatsapp@v1",
        subservice="encanador", slots=CASO_RESID))
    s = DS.handle_insurer_message(s, URA["desambiguacao"])
    checar(_saidas(s)[-1:] == ["Residencial"], "e continua respondendo Residencial na desambiguacao",
           str(_saidas(s)[-1:]))
    checar(len(PB.list_playbooks()) == 14,
           f"o acervo tem 14 corredores ({len(PB.list_playbooks())})",
           "eram 13 antes da Yelum residencial")


def main() -> int:
    print("=" * 74)
    print("YELUM RESIDENCIAL — MESMO BOT, OUTRA REDACAO")
    print("=" * 74)
    for t in (teste_o_corredor_existe_e_resolve,
              teste_o_rotulo_do_menu_e_o_da_yelum,
              teste_as_seis_ancoras_que_a_copia_teria_perdido,
              teste_a_desambiguacao_separa_os_dois_ramos,
              teste_um_acionamento_de_encanador_de_ponta_a_ponta,
              teste_o_que_o_corredor_se_recusa_a_prometer,
              teste_o_protocolo_agora_e_capturado,
              teste_o_corredor_da_hdi_continua_inteiro):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CORREDOR DA YELUM FALA A LINGUA DA YELUM — E PARA ONDE A EVIDENCIA PARA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
