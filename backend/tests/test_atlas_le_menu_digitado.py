"""O Tecelão enxerga a URA de TEXTO — não só a de botão. SPEC-038.

O que foi medido em 28/07/2026
------------------------------
Com o histórico da Resulta já importado, o mapa da Allianz mostrava:

    930 telas capturadas
    170 com opções detectadas     ← 760 telas cegas
    592 opções, 27 percorridas    ← 4% de cobertura
  1.899 arestas

Mil e oitocentas arestas com vinte e sete opções cobertas é uma contradição: o
sistema SABIA que depois da tela A veio a tela B, e não sabia que foi porque
alguém digitou "2".

A leitura do Founder estava certa
---------------------------------
> "NÃO É POSSÍVEL QUE EM MILHARES DE ATENDIMENTOS AS PESSOAS PEÇAM SÓ A MESMA
>  COISA DE RESIDENCIAL. TALVEZ O AGENTE ESTEJA CEGO."

Estava. Três defeitos somados, todos no mesmo lugar:

**1. O negrito do WhatsApp escondia o número.** A Allianz manda
`*1 -* Automóvel, Moto ou Caminhão` — asterisco ANTES do dígito. O regex de
menu numerado esperava o dígito logo após a quebra de linha e não casava nada.

**2. O rótulo perdia o número.** Onde o parser casava, ele guardava só o texto
("Residência, Condomínio ou Empresa") e jogava fora o "2". Mas a atendente
digita **"2"** — e "2" nunca casa com "Residência…".

**3. O menu de ramo caía por 8 caracteres.** A heurística de linhas curtas
aceitava até 48; `*1 - Residencial:* Para sua casa ou apartamento individual`
tem 56. Justamente a tela que escolhe Residencial, Condomínio ou Empresarial —
a mais importante para a Resulta — ficava com ZERO opções.

Estes casos usam o texto REAL capturado do WhatsApp da Allianz.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)),
               ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


C = carregar("app.services.cartographer")
W = carregar("app.services.atlas.weaver")

# Texto REAL, copiado de `observed_events` da Allianz.
MENU_PRINCIPAL = (
    "Olá! Sou a *assistente virtual da Allianz*. \n"
    "Você precisa de Assistência 24h para qual seguro?\n\n"
    "*1 -* Automóvel, Moto ou Caminhão\n"
    "*2 -* Residência, Condomínio ou Empresa\n"
    "*3 -* Vida ou Acidentes Pessoais\n"
    "*4 -* Viagem\n"
    "*5 -* Outros assuntos do seguro")

SUBMENU_RAMO = (
    "Qual seguro deseja utilizar?\n\n"
    "*1 - Residencial:* Para sua casa ou apartamento individual\n"
    "*2 - Condomínio:* Para áreas comuns e estrutura do condomínio\n"
    "*3 - Empresarial:* Para proteger seu negócio")

TELA_DE_DICAS = (
    "Tenho algumas dicas importantes para conseguir te atender da melhor forma!\n\n"
    "- Escolha a opção desejada digitando o número;\n"
    "- Ainda não consigo entender fotos, vídeos ou áudios;\n"
    "- Digite SAIR em qualquer momento caso queira finalizar nossa conversa.")

PERGUNTA_ABERTA = "Digite o *CNPJ* do titular ou pressione 9 para voltar."


def teste_menu_com_negrito_e_lido():
    print("\n[1] O negrito do WhatsApp não esconde mais o menu")
    ops = C.parse_options(MENU_PRINCIPAL)
    checar(len(ops) == 5, "as 5 opções do menu principal aparecem",
           f"achou {len(ops)}: {ops}")
    checar(any("Automóvel" in o for o in ops), "e o texto do rótulo vem junto")


def teste_o_menu_de_ramo_da_resulta():
    print("\n[2] O menu que escolhe Residencial/Condomínio/Empresarial")
    # Esta é A tela da Resulta. Ela ficava com ZERO opções por 8 caracteres.
    ops = C.parse_options(SUBMENU_RAMO)
    checar(len(ops) == 3, "as 3 opções aparecem", f"achou {len(ops)}: {ops}")
    for esperado in ("Residencial", "Condomínio", "Empresarial"):
        checar(any(esperado in o for o in ops), f"'{esperado}' está lá")
    # E o rótulo é o que se ESCOLHE, sem a explicação colada.
    checar(all(len(o) < 40 for o in ops),
           "o rótulo é a escolha, não a explicação inteira", str(ops))


def teste_o_numero_fica_no_rotulo():
    print("\n[3] O número da opção não é jogado fora")
    ops = C.parse_options(MENU_PRINCIPAL)
    checar(all(C.numero_da_opcao(o) for o in ops),
           "toda opção numerada sabe o próprio número",
           str([(o, C.numero_da_opcao(o)) for o in ops[:2]]))
    checar(C.numero_da_opcao(ops[1]) == "2",
           "a segunda opção é a '2'", str(ops[1]))


def teste_o_que_nao_e_menu_continua_nao_sendo():
    print("\n[4] Tela que não é menu não vira menu")
    # Opção que não existe vira lacuna eterna: a cobertura nunca fecha porque
    # ninguém pode escolher o que não é escolha.
    checar(C.parse_options(TELA_DE_DICAS) == [],
           "a tela de dicas (lista com '-') não tem opções",
           str(C.parse_options(TELA_DE_DICAS)))
    checar(C.parse_options(PERGUNTA_ABERTA) == [],
           "a pergunta aberta não tem opções",
           str(C.parse_options(PERGUNTA_ABERTA)))


def teste_digitar_o_numero_percorre_a_opcao():
    print("\n[5] Digitar '2' percorre a opção 2")
    ops = C.parse_options(MENU_PRINCIPAL)
    op2 = [o for o in ops if C.numero_da_opcao(o) == "2"][0]
    op3 = [o for o in ops if C.numero_da_opcao(o) == "3"][0]

    checar(W.labels_match(op2, "2"), "a opção 2 casa com o que foi digitado")
    checar(not W.labels_match(op3, "2"),
           "e a opção 3 NÃO casa",
           "sem isso, uma escolha marcaria a rota errada como percorrida")


def teste_resposta_que_nao_e_escolha_de_menu():
    print("\n[6] CPF e endereço não são escolha de menu")
    # A conversa real tem `out` com "81.578.783/0001-97" logo depois de uma
    # tela. Tratar isso como clique inventaria rota.
    ops = C.parse_options(MENU_PRINCIPAL)
    for resposta in ("81.578.783/0001-97", "02414523921", "Rua das Flores 190"):
        casou = any(W.labels_match(o, resposta) for o in ops)
        checar(not casou, f"'{resposta[:20]}' não vira escolha de menu")


def teste_clique_de_botao_continua_funcionando():
    print("\n[7] O que já funcionava não quebrou")
    # Seguradoras com lista/botão do WhatsApp mandam o rótulo inteiro de volta.
    checar(W.labels_match("Guincho", "Guincho"), "clique idêntico casa")
    checar(W.labels_match("Assistência 24h", "assistencia 24h"),
           "e o casamento continua tolerante a acento e caixa")
    ops = C.parse_options("Escolha:\nBotão 1: Guincho\nBotão 2: Chaveiro")
    checar(len(ops) == 2, "botões da Evolution continuam sendo lidos", str(ops))



# ---------------------------------------------------------------------------
# Lista/botão do WhatsApp: a estrutura manda, não o texto renderizado
# ---------------------------------------------------------------------------
T = carregar("app.services.atlas.templater")

# Estrutura REAL, copiada de `observed_events.interactive` da Porto.
LISTA_PORTO = {
    "kind": "list",
    "options": [
        {"title": "Abertura de sinistro",
         "description": "Batida ou acidente com envolvimento de terceiros"},
        {"title": "Acompanhar um processo",
         "description": "Informações sobre as atualizações do sinistro"},
        {"title": "Carro reserva",
         "description": "Solicitar, prorrogar ou dúvidas com as locações"},
        {"title": "Voltar", "description": ""},
    ],
    "button_label": "Opções",
}
RENDER_PORTO = ("O que você gostaria de fazer?\n"
                "Abertura de sinistro\n"
                "Batida ou acidente com envolvimento de terceiros\n"
                "Acompanhar um processo\n"
                "Informações sobre as atualizações do sinistro\n"
                "Carro reserva\n"
                "Solicitar, prorrogar ou dúvidas com as locações\n"
                "Voltar")


def teste_lista_usa_a_estrutura_e_nao_o_render():
    print("\n[8] Lista do WhatsApp: os títulos vêm da estrutura")
    # No texto renderizado, título e descrição são linhas alternadas sem marca
    # nenhuma. Adivinhar qual é qual fez a Porto ficar com 859 "opções" em 353
    # telas — as descrições viraram opções, e opção que não existe nunca é
    # percorrida: cada uma virava lacuna permanente na cobertura.
    no = T.screen_node(RENDER_PORTO, LISTA_PORTO)
    rotulos = [o["label"] for o in no["options"]]
    checar(len(rotulos) == 4, "as 4 opções reais aparecem", f"{len(rotulos)}: {rotulos}")
    checar("Abertura de sinistro" in rotulos, "o título é a opção")
    for descricao in ("Batida ou acidente com envolvimento de terceiros",
                      "Informações sobre as atualizações do sinistro"):
        checar(descricao not in rotulos,
               f"a descrição não virou opção: {descricao[:34]}...")


def teste_sem_estrutura_ainda_le_o_texto():
    print("\n[9] URA de texto puro continua sendo lida")
    # A Allianz não usa lista: se a estrutura faltar, o texto ainda tem de ser
    # interpretado, senão o conserto de hoje se perderia.
    no = T.screen_node(MENU_PRINCIPAL, None)
    checar(len(no["options"]) == 5, "5 opções do texto puro",
           str([o["label"] for o in no["options"]]))


def teste_a_URA_acaba_quando_entra_gente():
    print("\n[10] A conversa com o especialista não é rota")
    checar(bool(C._HUMANO_RE.search(
        "Vou transferir seu caso para um especialista. Para agilizar, "
        "ele já tem acesso a todo histórico da nossa conversa")),
        "a frase real da Allianz é reconhecida como passagem para humano",
        "233 ocorrências nas conversas da Resulta, e o padrão não pegava")
    for tela_da_ura in ("Por favor, confirme o endereço para atendimento:",
                        "Assistência 24 horas, permanece à disposição.",
                        "Mais um momento por favor."):
        checar(not C._HUMANO_RE.search(tela_da_ura),
               f"'{tela_da_ura[:38]}...' continua sendo tela da URA")

    fonte = open(os.path.join(RAIZ, "app", "services", "atlas", "weaver.py"),
                 encoding="utf-8").read()
    checar('nodes[nid][chave]' in fonte,
           "o Tecelão registra de que lado do handoff a tela apareceu")
    checar('node["fase"] = "humano" if e_humana else "ura"' in fonte,
           "e a fase é decidida no cálculo, não carimbada na hora",
           "carimbar durante a sessão contaminou 782 telas em 28/07/2026")
    checar('"nodes_ura"' in fonte and '"nodes_humano"' in fonte,
           "e as duas contagens aparecem separadas",
           "senão fica a pergunta: por que 900 telas se a URA tem 50?")


def teste_comprovante_nao_e_menu():
    print("\n[11] Comprovante não é menu")
    # Medido em 28/07/2026 sobre as telas reais: 260 "opções" inventadas em 54
    # telas, todas com a forma `Rótulo: valor`. Opção que não existe nunca é
    # percorrida — é lacuna permanente na cobertura, e o Founder ia olhar um
    # número baixo achando que faltava conversa, quando faltava só verdade.
    reais = {
        "Yelum, comprovante":
            "Sua solicitação foi registrada!\nAssistência: 8923467\nServiço: Encanador",
        "Porto, agendamento":
            "Tudo certo!\nAgendamento: 28/01/2026, entre 10h00 e 12h00\nServiço: Eletricista",
        "Zurich, boleto":
            "Segue o resumo:\nBoleto: 8\nData do pagamento mensal: 03\n"
            "Quantidade de parcelas restantes: 3",
    }
    for nome, tela in reais.items():
        rotulos = [o["label"] for o in T.screen_node(tela)["options"]]
        checar(rotulos == [], f"{nome}: nenhuma opção inventada", str(rotulos))


def teste_nome_de_pessoa_nao_vira_rotulo():
    print("\n[12] O mapa é global — nome de gente não entra nele")
    # Uma tela da HDI trazia um histórico colado dentro da mensagem. As linhas
    # viravam "opções", e o nome de uma pessoa real ia parar num rótulo de um
    # mapa que é conhecimento compartilhado entre TODAS as corretoras.
    colado = ("Segue o histórico:\n"
              "10:56 - ALINE FERNANDA DIAS MELDOLA: Isso que estou questionando\n"
              "10:57 - ALINE FERNANDA DIAS MELDOLA: Ok")
    no = T.screen_node(colado)
    checar(no["options"] == [], "o histórico colado não vira menu",
           str([o["label"] for o in no["options"]]))
    checar(all("ALINE" not in o["label"] for o in no["options"]),
           "e nenhum rótulo carrega o nome da pessoa")


def teste_protocolos_diferentes_sao_a_mesma_tela():
    print("\n[13] Cada protocolo não é uma tela nova")
    # 18 nós na Yelum e 10 na Porto eram a MESMA tela com números diferentes.
    # Mapa inchado é mapa que ninguém lê, e cada cópia divide a contagem de
    # quantas vezes aquela tela realmente apareceu.
    a = T.screen_node("Sua solicitação foi registrada!\nAssistência: 8923467")
    b = T.screen_node("Sua solicitação foi registrada!\nAssistência: 9124710")
    checar(a["hash"] == b["hash"], "dois protocolos = uma tela só")
    # O que importa é o NÚMERO não ficar, não qual placeholder entrou no lugar.
    # Este teste afirmava `{VALOR}` e ficou vermelho em 30/07/2026 quando uma
    # regra nova passou a mascarar o protocolo mais cedo, como `{NUMERO}` — a
    # proteção intacta, o rótulo diferente. Teste que afirma detalhe de
    # implementação quebra quando a implementação melhora.
    checar("8923467" not in a["text"] and "{" in a["text"],
           "e o número do protocolo não fica guardado", a["text"][:70])


MENU_CURTO = "Qual seguro?\n*1 -* Auto\n*2 -* Casa"


def _ev(direcao: str, hora: str, texto: str) -> dict:
    return {"session_id": "s1", "direction": direcao, "wa_timestamp": hora,
            "msg_type": "text", "text": texto}


def teste_tela_nao_aponta_para_si_mesma():
    print("\n[14] Metade das setas não levava a lugar nenhum")
    # Medido nos mapas gravados em 28/07/2026: 840 das 1.899 arestas da Allianz
    # (44%), 284 das 576 da Porto (49%), 40 das 58 da Tokio (69%) saíam de uma
    # tela e voltavam para ela mesma. Vinham das cópias do histórico.
    #
    # E o destino da aresta sequencial é eleito por maioria: o voto da tela em
    # si mesma chegava a VENCER o destino real, e a seta passava a apontar de
    # volta para a própria tela. Rota errada, não só rota inútil.
    brutos = [_ev("in", "10:00:00", MENU_CURTO)] * 3 + \
             [_ev("out", "10:00:30", "2"), _ev("in", "10:01:00", "Qual o CEP?")]
    unicos = W._sem_copias(brutos)
    checar(len(unicos) == 3, "três cópias da mesma tela viram uma",
           f"{len(brutos)} lidas, {len(unicos)} únicas")

    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, unicos)
    para_si = [e for e in acc["edges"].values() if e["src"] == e["to"]]
    checar(not para_si, "nenhuma seta aponta para a própria tela", str(para_si))
    checar(any(not e["inferred"] for e in acc["edges"].values()),
           "e a escolha real virou aresta confirmada")


def teste_a_escolha_nao_se_perde_junto():
    print("\n[15] Jogar fora a seta inútil não pode jogar fora a escolha")
    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, [_ev("in", "10:00:00", MENU_CURTO),
                          _ev("in", "10:00:01", MENU_CURTO),
                          _ev("out", "10:00:30", "2"),
                          _ev("in", "10:01:00", "Qual o CEP?")])
    confirmadas = [e["label"] for e in acc["edges"].values() if not e["inferred"]]
    checar(confirmadas, "a escolha '2' sobreviveu como aresta confirmada",
           str([(e["label"], e["inferred"]) for e in acc["edges"].values()]))


def teste_voltar_ao_mesmo_menu_e_rota_de_verdade():
    print("\n[16] Digitar errado e voltar ao mesmo menu É rota")
    # Aqui a tela aponta para ela mesma DE PROPÓSITO, e o agente precisa saber:
    # é o caminho do erro. Só a volta sem escolha capturada é que não ensina.
    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, [_ev("in", "10:00:00", MENU_CURTO),
                          _ev("out", "10:00:10", "9"),
                          _ev("in", "10:00:20", MENU_CURTO)])
    para_si = [e for e in acc["edges"].values() if e["src"] == e["to"]]
    checar(len(para_si) == 1, "a volta por escolha real continua no mapa",
           str([(e["label"], e["src"] == e["to"]) for e in acc["edges"].values()]))


HANDOFF = ("Vou transferir seu caso para um especialista. Para agilizar, "
           "ele já tem acesso a todo histórico da nossa conversa")


def teste_o_menu_nunca_e_carimbado_de_conversa_humana():
    print("\n[17] Uma tela com menu é da URA, sempre")
    # UMA SESSÃO É UMA JANELA DE DUAS HORAS. O cliente é transferido para o
    # especialista e depois VOLTA a falar com a URA na mesma janela.
    #
    # A primeira versão da marca de fase carimbava `fase="humano"` na hora, e o
    # carimbo ficava no nó para sempre. Bastou isso acontecer uma vez para o
    # menu principal da Allianz virar "conversa humana" — e tela marcada assim
    # é PULADA no cálculo de rotas.
    #
    # Medido nos mapas de 28/07/2026: 782 das 919 telas carimbadas, incluindo
    # 56 telas COM MENU. O Canvas ficou sem nenhuma rota depois da raiz, tudo
    # laranja, com 94 opções percorridas que ninguém via.
    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, [
        _ev("in", "10:00:00", MENU_CURTO), _ev("out", "10:00:10", "1"),
        _ev("in", "10:00:20", "Qual o CEP?"), _ev("out", "10:00:30", "88000-000"),
        _ev("in", "10:01:00", HANDOFF),
        _ev("in", "10:05:00", "Boa tarde! Precisa de escada?"),
        # ainda dentro da janela de 2h, outro atendimento comeca
        _ev("in", "11:00:00", MENU_CURTO), _ev("out", "11:00:10", "2"),
        _ev("in", "11:00:20", "Qual o CEP?")])
    W.compute_coverage(acc)

    menu = [n for n in acc["nodes"].values() if "Qual seguro" in n["text"]][0]
    checar(menu.get("fase") == "ura", "o menu continua sendo da URA",
           f"ficou {menu.get('fase')}")
    checar(all(o.get("confidence") for o in menu["options"]),
           "e suas opções foram AVALIADAS",
           "confidence nulo = a tela foi pulada e nenhuma rota sai dela")
    checar([o for o in menu["options"] if o.get("leads_to")],
           "com destino gravado — é isto que o Canvas desenha")

    fala = [n for n in acc["nodes"].values() if "Boa tarde" in n["text"]][0]
    checar(fala.get("fase") == "humano",
           "a fala solta do especialista continua fora da conta",
           "ela não tem menu e nunca apareceu antes do handoff")

    cep = [n for n in acc["nodes"].values() if "CEP" in n["text"]][0]
    checar(cep.get("fase") == "ura",
           "e uma tela vista ANTES do handoff não vira humana depois",
           "era assim que a contaminação se espalhava")


def teste_a_regra_de_fase_esta_no_calculo_e_nao_no_carimbo():
    print("\n[18] A fase é decidida no fim, com o quadro inteiro")
    fonte = open(os.path.join(RAIZ, "app", "services", "atlas", "weaver.py"),
                 encoding="utf-8").read()
    checar('nodes[nid]["fase"] = "humano"' not in fonte,
           "o Tecelão não carimba a fase durante a sessão",
           "carimbar na hora é o que contaminou 782 telas")
    checar("pos_handoff" in fonte and "pre_handoff" in fonte,
           "ele apenas CONTA de que lado do handoff a tela apareceu")
    checar('not node.get("options")' in fonte,
           "e tela com menu nunca é fase humana")


def teste_voltar_e_sair_nao_sao_lacuna():
    print("\n[19] Voltar e Sair não são rota a descobrir")
    # Medido nos mapas de 28/07/2026: "voltar" aparece 222 vezes em 5
    # seguradoras e 190 contavam como lacuna; "sair" 73 vezes, 71 lacunas.
    # Ninguém clica em "Voltar" num atendimento real — e se clicasse não
    # ensinaria nada. A lacuna nunca fecha e afunda a cobertura para sempre.
    for rotulo, esperado in (("3 - Voltar", "voltar"), ("4 - Sair", "sair"),
                             ("Encerrar atendimento", "sair"),
                             ("Menu principal", "menu")):
        checar(C.acao_conhecida(rotulo) == esperado,
               f"'{rotulo}' tem comportamento conhecido: {esperado}",
               str(C.acao_conhecida(rotulo)))

    # A escolha de horário é pior: o rótulo MUDA todo dia, então o mapa de
    # amanhã inventa lacunas novas que ninguém jamais percorre.
    for rotulo in ("{DATA} (quarta-feira)", "entre 10h00 e 12h00",
                   "2 - {DATA} (sexta-feira)"):
        checar(C.acao_conhecida(rotulo) == "horario",
               f"'{rotulo}' é escolha de horário")


def teste_o_que_parece_navegacao_e_nao_e():
    print("\n[20] O que parece navegação e não é continua sendo lacuna")
    # Marcar demais é pior que marcar de menos: esconde rota que falta mapear,
    # e o Founder deixaria de pedir o atendimento que a descobriria.
    for rotulo in ("Cancelar serviço", "Mais opções", "Outro assunto",
                   "1 - Automóvel, Moto ou Caminhão", "Sim", "Não",
                   "Voltar ao trabalho", "Sair de casa", "Não encontrei o assunto"):
        checar(C.acao_conhecida(rotulo) is None,
               f"'{rotulo}' continua sendo rota de verdade",
               str(C.acao_conhecida(rotulo)))


def teste_a_cobertura_conta_o_conhecido_como_fechado():
    print("\n[21] E a cobertura para de contar isso como buraco")
    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, [
        _ev("in", "10:00:00", "Escolha:\n*1 -* Guincho\n*2 -* Voltar\n*3 -* Sair"),
        _ev("out", "10:00:10", "1"),
        _ev("in", "10:00:20", "Qual o CEP?")])
    W.compute_coverage(acc)
    menu = [n for n in acc["nodes"].values() if "Escolha" in n["text"]][0]
    por_rotulo = {o["label"]: o for o in menu["options"]}
    checar(por_rotulo["1 - Guincho"]["confidence"] in ("seen_once", "confirmed"),
           "a opção real percorrida continua percorrida")
    for rot in ("2 - Voltar", "3 - Sair"):
        checar(por_rotulo[rot]["confidence"] == "navegacao",
               f"'{rot}' vira comportamento conhecido, não lacuna")
        checar(por_rotulo[rot].get("acao") in ("voltar", "sair"),
               f"e o agente recebe o que '{rot}' faz")
    checar(acc["coverage"]["pct"] == 100,
           "cobertura fecha em 100% — não havia buraco nenhum ali",
           str(acc["coverage"]))


def main() -> int:
    print("=" * 70)
    print("O TECELÃO ENXERGA A URA DE TEXTO, NÃO SÓ A DE BOTÃO")
    print("=" * 70)
    for teste in (teste_menu_com_negrito_e_lido,
                  teste_o_menu_de_ramo_da_resulta,
                  teste_o_numero_fica_no_rotulo,
                  teste_o_que_nao_e_menu_continua_nao_sendo,
                  teste_digitar_o_numero_percorre_a_opcao,
                  teste_resposta_que_nao_e_escolha_de_menu,
                  teste_clique_de_botao_continua_funcionando,
                  teste_lista_usa_a_estrutura_e_nao_o_render,
                  teste_sem_estrutura_ainda_le_o_texto,
                  teste_a_URA_acaba_quando_entra_gente,
                  teste_comprovante_nao_e_menu,
                  teste_nome_de_pessoa_nao_vira_rotulo,
                  teste_protocolos_diferentes_sao_a_mesma_tela,
                  teste_tela_nao_aponta_para_si_mesma,
                  teste_a_escolha_nao_se_perde_junto,
                  teste_voltar_ao_mesmo_menu_e_rota_de_verdade,
                  teste_o_menu_nunca_e_carimbado_de_conversa_humana,
                  teste_a_regra_de_fase_esta_no_calculo_e_nao_no_carimbo,
                  teste_voltar_e_sair_nao_sao_lacuna,
                  teste_o_que_parece_navegacao_e_nao_e,
                  teste_a_cobertura_conta_o_conhecido_como_fechado):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("NENHUM ATENDIMENTO SE PERDE POR CAUSA DO FORMATO DA SEGURADORA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
