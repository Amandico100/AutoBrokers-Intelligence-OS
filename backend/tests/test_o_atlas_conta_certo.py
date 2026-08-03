# -*- coding: utf-8 -*-
"""O Atlas para de contar o que não é rota.

O mapa da HDI declarava **440 telas**. A URA real tem umas dezenas de menus. A
cobertura declarada era 36% e não significava nada, porque o denominador estava
cheio de coisa que ninguém pode percorrer.

📊 Tudo medido em 03/08/2026 no projeto Supabase `dcajcvlzcjbmyapmklil`, sobre
`observed_events` (1.965 eventos, 38 sessões da HDI) e sobre o `ura_maps`
observado da HDI (440 nós, `coverage.pct = 36`).

A · O detector de fase humana era cego
--------------------------------------
Das **23** formas distintas com que a HDI anuncia que vai passar a conversa
para uma pessoa, `_HUMANO_RE` reconhecia **3** — 📊 3 ocorrências de 61. A
frase canônica da seguradora,

    "Para seguir com o seu atendimento será necessário falar com um de nossos
     especialistas. Por favor, aguarde."

passava batida porque o padrão esperava ``aguarde.{0,30}especialista`` e a HDI
INVERTE A ORDEM. Consequência: "Bom dia, desculpa a demora", "imagina",
"Olá, meu nome é Camila Rossi e irei realizar seu atendimento" — conversa livre
de analista — entraram no Atlas como tela de URA.

E o conserto tem uma armadilha embutida. A tela de BOAS-VINDAS da HDI, primeira
mensagem de toda sessão, diz:

    "Ao final da abertura, após a pesquisa de satisfação, caso seja necessário,
     você pode falar com um de nossos analistas digitando 'falar com atendente'."

Alargar o padrão sem freio marcaria a PRIMEIRA tela de toda sessão como
handoff, e a URA inteira viraria "conversa" — o estrago de 28/07/2026 na
Allianz (782 de 919 telas carimbadas como humano) chegando pela porta oposta.
Por isso a pergunta é feita frase a frase, e a oferta condicional não conta.

B · Não-rota contava como lacuna
--------------------------------
📊 Casos reais no mapa da HDI, cada um virando buraco que nunca fecha:

    "Seguimos à disposição. … HDI / Certeza que te deixa seguro"
        → menu de 2 opções. É o RODAPÉ DE ASSINATURA.
    "so para confirmar / Localização do Cliente / Localização de Destino"
        → menu de 2 opções. É o HUMANO digitando.
    "5 - Ótimo … 1 - Péssimo"  e a escala nua  "1 / 2 / 3 / 4 / 5"
        → 15 opções em 3 telas. É PESQUISA DE SATISFAÇÃO.
    "17 - Placa 0KM0000" / "18 - Nenhuma das opções anteriores"
        → lista dos veículos DAQUELE segurado.
    "Manhã (08h às 12h)" / "Tarde (13h às 18h)"
        → faixa de horário; qualquer uma leva à mesma confirmação.
    "Responder novamente"
        → navegação, irmã do "Voltar".

O resultado
-----------
📊 Recalculado em SQL sobre o mapa gravado, com a fórmula de `compute_coverage`
reproduzida linha a linha (a réplica devolve 82/225 = 36%, idêntico ao gravado):

    universo    225 → 209      (−16 pares que não eram rota)
    percorrido   82 →  85      (+3 que já se sabia percorrer)
    cobertura    36% → 41%

**Nada foi apagado.** O nó continua no mapa com o texto e o motivo
(`fase="humano"` ou `nao_rota="pesquisa_de_satisfacao"`). O que ele deixa de
ter é opção — e sem opção ele sai dos DOIS lados da fração.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)),
               ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def carregar(nome: str):
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


carregar("app.services.ura_map_service")
C = carregar("app.services.cartographer")
T = carregar("app.services.atlas.templater")
carregar("app.services.atlas.mensagem")
W = carregar("app.services.atlas.weaver")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


# ───────────────────────────────────────────────────────────────────────────
# As frases REAIS. Copiadas de `observed_events` da HDI, com a contagem medida.
# Nenhuma foi inventada, nem "limpa": o typo "antedimento" é deles.
# ───────────────────────────────────────────────────────────────────────────
TRANSFERENCIA = [
    (7, "Para seguir com o seu atendimento será necessário falar com um de "
        "nossos especialistas. Por favor, aguarde."),
    (12, "Você está na fila para atendimento, por favor, aguarde até que um de "
         "nossos colaboradores esteja disponível."),
    (10, "Você está na fila para atendimento. Por favor aguarde até que um de "
         "nossos analistas esteja disponível. O tempo médio de espera é de 31 "
         "minutos."),
    (8, "Sua conversa foi encerrada pelo atendente."),
    (4, "Estamos com alta demanda de serviços, o tempo de espera para "
        "acionamento do seu atendimento pode ser maior que o normal. Por favor "
        "aguarde até que um de nossos colaboradores esteja disponível . Se "
        "desejar sair da espera digite //sair"),
    (2, "Um dos nossos analistas dará continuidade no seu atendimento. Aguarde "
        "enquanto te transfiro."),
    (2, "Você foi transferido para fila de antedimento de outra habilidade. Por "
        "favor, aguarde até que um de nossos colaboradores responda."),
    (1, "Olá, meu nome é Camila Rossi e irei realizar seu atendimento."),
    (1, "Boa tarde, meu nome é Bianca e darei continuidade ao seu atendimento, "
        "como eu posso ajudar ?"),
    (1, "Para continuar sua solicitação vou te transferir para um de nossos "
        "analistas, aguarde um momento por favor."),
    (1, "Por favor aguarde enquanto te transfiro para um dos nossos analistas."),
    (1, "Devido as condições gerais de sua apólice, vou precisar te transferir "
        "para um de nossos analista. Por favor, aguarde um momento"),
    (1, "Entendi! Vamos te direcionar para um de nossos especialistas. Por "
        "favor, aguarde alguns instantes"),
    (1, "Maria, parece que você deseja o cancelamento de sua assistência. "
        "Identificamos que este processo não poderá ser feito através de nossa "
        "conversa e, por isso, será necessário a ajuda de um de nossos "
        "analistas. Por favor, aguarde."),
    (1, "Maria, parece que você deseja trocar o endereço para onde devemos "
        "enviar o veículo. Será necessário a análise de nossos especialistas, "
        "por favor, aguarde."),
    (1, "Maria Regina - Autofleet Seguros, parece que você nos forneceu uma "
        "resposta diferente do que perguntamos. Para te ajudar, vamos te "
        "encaminhar para um de nossos analistas. Por favor, aguarde."),
    (1, "O endereço não foi localizado em seu cadastro, mas não se preocupe, "
        "vou te transferir para um de nossos analista. Aguarde um momento, por "
        "favor."),
    (1, "SAionara,\r\nnão se preocupe que em instantes, um de nossos analistas "
        "vai seguir com seu atendimento."),
    (1, "Ok, esse canal é apenas para acompanhamento, irei transferir para "
        "setor de abertura"),
    (1, "Vou transferir para o setor de abertura. Um momento"),
    (1, "Recebemos sua mensagem. Por favor, aguarde alguns instantes enquanto "
        "procuramos um atendente."),
    (1, "No momento, toda nossa equipe está em atendimento, aguarde um instante "
        "que já iremos te atender."),
    (1, "Agora, você é o 02° da fila para ser atendido."),
]

# A URA CONTINUA. Nenhuma destas pode ser lida como handoff — e a primeira é a
# mais perigosa de todas: é a tela de abertura de TODA sessão da HDI.
A_URA_CONTINUA = [
    "Olá! Eu sou a assistente virtual da Assistência 24 horas!\n"
    "Vi que você está precisando de um atendimento para o seu automóvel. Por "
    "aqui consigo te ajudar com os serviços de guincho, socorro mecânico ou "
    "chaveiro.\n\nAo final da abertura, após a pesquisa de satisfação, caso "
    "seja necessário, você pode falar com um de nossos analistas digitando "
    '"falar com atendente".\n\nPara dar início ao seu atendimento digite a '
    "placa do veículo.\nExemplo: *ABC1234* ou *ABC1A23*",
    "Entendemos que você gostaria de falar com um atendente. Mas fique "
    "tranquilo(a), nosso atendimento pelo WhatsApp é rápido, seguro e "
    "eficiente. Continue por aqui e vamos solicitar sua assistência com "
    "agilidade!",
    "Sobre sua assistência 9257546, nossa equipe está procurando um prestador "
    "para atender o serviço de GUINCHO.",
    "Tudo bem, por favor, aguarde enquanto entramos em contato com o "
    "prestador.\nLogo lhe retornaremos",
    "Estamos com um alto volume de atendimentos, por favor aguarde",
    "Aguarde um momento, por favor.",
    "Por favor, confirme o endereço para atendimento:",
    "Assistência 24 horas, permanece à disposição.",
    "Mais um momento por favor.",
]

# Telas do mapa da HDI (e das irmãs) que NÃO são rota.
SLOGAN = ("Seguimos à disposição.\n\nFique tranquilo. Se precisar de mais "
          "alguma ajuda, estaremos prontos para atendê-lo!\n\nHDI\n"
          "Certeza que te deixa seguro")
HUMANO_DIGITANDO = ("so para confirmar \nLocalização do Cliente\n"
                    "Endereço: {VALOR}\n\nLocalização de Destino\n"
                    "Endereço: {VALOR}\nReferências:  Primo's car")
PESQUISA_ROTULADA = ("A sua opinião é muito importante. O que achou do "
                     "atendimento prestado pelo nosso analista?\n5 - Ótimo\n"
                     "4 - Bom\n3 - Neutro\n2 - Ruim\n1 - Péssimo")
PESQUISA_ESCALA_NUA = ("O quão satisfeito você está com este atendimento?\n\n"
                       "Considerando *5 muito bom e 1 muito ruim*.\n1\n2\n3\n4\n5")
PESQUISA_MAPFRE = ("Com base na sua experiência recente neste canal, *qual o "
                   "seu grau de satisfação com o atendimento recebido*?\n"
                   "Muito bom\nBom\nIndiferente\nRuim\nMuito ruim")
LISTA_DE_VEICULOS = ("Identificamos que há mais de um veículo para esta "
                     "apólice, por favor, *digite o número* indicando o "
                     "veículo para o qual você precisa de atendimento. Ex: 9\n\n"
                     "1 - Placa {PLACA}\n2 - Placa {PLACA}\n"
                     "17 - Placa 0KM0000\n18 - Nenhuma das opções anteriores")

# Menus REAIS. Nenhum pode perder uma única opção — apagar rota de verdade é
# pior que a lacuna eterna que estamos consertando.
MENUS_REAIS = {
    "cor do veículo (linhas nuas, sem '?')": (
        "Para facilitar a sua localização, poderia me informar a cor do veículo "
        "de placa *{PLACA}*\nBranco\nPrata/Cinza\nPreto\nVermelho\nOutros\nVoltar", 6),
    "carroceria": (
        "Qual o tipo da carroceria?\nBaú\nBaú frigorífico\nSider\n"
        "Carga seca (aberta)\nBasculante\nTanque\nPoliguindaste\n"
        "Plataforma (guincho)\nMunk\nVoltar", 10),
    "particularidades dos ocupantes": (
        "Por favor, me informe os ocupantes tem alguma das particularidades "
        "listadas abaixo.\nCriança\nIdoso\nGestante\nPessoa com deficiência\n"
        "Cirurgia recente\nNenhuma das anteriores\nVoltar", 7),
    "período do agendamento": (
        "Qual o melhor período?\nBotão 1: Manhã (08h às 12h)\n"
        "Botão 2: Tarde (13h às 18h)\nBotão 3: Voltar", 3),
    "não entendi (Voltar / Responder novamente)": (
        "Não entendi. Lembre-se que, para responder, você precisa selecionar o "
        "botão indicando a opção escolhida.\n\nSelecione *'voltar'* se quiser "
        "retornar para a pergunta anterior ou *'responder novamente'* se quiser "
        "seguir de onde paramos.\nBotão 1: Voltar\nBotão 2: Responder novamente", 2),
    "Zurich: pesquisa pendente É ROTA": (
        "Olá! Você ainda está por aí?\n\nVi que concluiu um de nossos serviços "
        "mas ainda não respondeu nossa pesquisa.\n\nO que acha de fazer isso "
        "agora?\nBotão 1: Sim\nBotão 2: Não", 2),
    "Mapfre: 'satisfatório?' É ROTA": (
        "O acompanhamento da sua solicitação está sendo satisfatório?\n"
        "Botão 1: Sim\nBotão 2: Não", 2),
    "Yelum: 'Responder pesquisa' É ROTA": (
        "Maria, identifiquei que a pesquisa do último atendimento não foi "
        "respondida. Você gostaria de seguir para um novo atendimento ou "
        "responder?\nBotão 1: Responder pesquisa\nBotão 2: Novo atendimento\n"
        "Botão 3: Acompanhar andamento", 3),
    "Allianz: menu digitado com negrito": (
        "Escolha a opção desejada digitando o número:\n"
        "*1 -* Automóvel, Moto ou Caminhão\n*2 -* Residência, Condomínio ou Empresa", 2),
}


def teste_as_23_frases_de_transferencia_da_hdi():
    print("\n[A1] As 23 formas reais de dizer 'agora é gente' são reconhecidas")
    cegas = [(n, t) for n, t in TRANSFERENCIA if not C.entrou_humano(t)]
    perdidas = sum(n for n, _ in cegas)
    checar(not cegas,
           f"as {len(TRANSFERENCIA)} formas medidas na HDI são detectadas",
           f"{len(cegas)} cegas, {perdidas} ocorrências perdidas: "
           + " | ".join(t[:60] for _, t in cegas[:4]))
    checar(C.entrou_humano(
        "Para seguir com o seu atendimento será necessário falar com um de "
        "nossos especialistas. Por favor, aguarde."),
        "a frase CANÔNICA da HDI é reconhecida",
        "medido: 7 ocorrências; passava batida porque o padrão esperava "
        "'aguarde…especialista' e a HDI inverte a ordem")
    for exigida in ("Você está na fila para atendimento, por favor, aguarde até "
                    "que um de nossos colaboradores esteja disponível.",
                    "Sua conversa foi encerrada pelo atendente.",
                    "Olá, meu nome é Camila Rossi e irei realizar seu atendimento."):
        checar(C.entrou_humano(exigida), f"'{exigida[:44]}…'")


def teste_a_oferta_condicional_nao_e_handoff():
    print("\n[A2] Oferecer um analista não é entregar a conversa a um")
    for tela in A_URA_CONTINUA:
        checar(not C.entrou_humano(tela),
               f"a URA continua: '{tela[:46]}…'")
    boas_vindas = A_URA_CONTINUA[0]
    checar(bool(C._HUMANO_RE.search(boas_vindas)),
           "o padrão CRU casa a tela de boas-vindas (por isso o freio existe)",
           "ela diz 'você pode falar com um de nossos analistas'")
    checar(not C.entrou_humano(boas_vindas),
           "e o freio de oferta condicional a absolve",
           "sem ele, a PRIMEIRA tela de toda sessão da HDI viraria handoff e a "
           "URA inteira viraria conversa")
    # A frase da Allianz que motivou o padrão original não pode ter se perdido.
    checar(C.entrou_humano(
        "Vou transferir seu caso para um especialista. Para agilizar, ele já "
        "tem acesso a todo histórico da nossa conversa"),
        "a frase da Allianz (233 ocorrências medidas) continua reconhecida")


def teste_o_slogan_nao_e_menu():
    print("\n[B1] Rodapé de assinatura não é menu de duas opções")
    ops = C.parse_options(SLOGAN)
    checar(ops == [], "o slogan da HDI não produz opção nenhuma",
           f"produziu {ops}")
    checar("HDI" not in " ".join(ops) and "Certeza" not in " ".join(ops),
           "'HDI' e 'Certeza que te deixa seguro' não viram rota")
    checar(C.parse_options(HUMANO_DIGITANDO) == [],
           "e a mensagem digitada pelo analista também não",
           "'so para confirmar / Localização do Cliente / Localização de "
           "Destino' virava menu de 2 opções")
    # A regra é 'sem convite não é menu' — e ela precisa ser essa, não uma
    # lista de frases da HDI, senão a próxima seguradora reabre o buraco.
    checar(C.parse_options("Segue os documentos pendentes para analie.\n\n"
                           "Orçamentos detalhados de reparo dos danos\n"
                           "Laudo técnico atestando a causa e extensão dos danos") == [],
           "lista de documentos (Porto) também para de virar menu")


def teste_a_pesquisa_de_satisfacao_nao_conta():
    print("\n[B2] Pesquisa de satisfação não é rota — em nenhum formato")
    for nome, tela in (("rotulada 5-Ótimo…1-Péssimo", PESQUISA_ROTULADA),
                       ("escala nua 1 2 3 4 5", PESQUISA_ESCALA_NUA),
                       ("por palavras (Mapfre)", PESQUISA_MAPFRE)):
        ops = C.parse_options(tela)
        checar(ops == [], f"{nome}: nenhuma opção extraída", f"produziu {ops}")
        checar(C.nao_e_rota(tela) == "pesquisa_de_satisfacao",
               f"{nome}: marcada com o motivo",
               "o nó fica no mapa; o que sai é a opção")

    print("\n[B3] Mas 'pesquisa' na frase não basta para condenar a tela")
    for nome, (tela, esperado) in MENUS_REAIS.items():
        if "É ROTA" not in nome:
            continue
        checar(C.nao_e_rota(tela) is None, f"{nome}: continua sendo rota")
        checar(len(C.parse_options(tela)) == esperado,
               f"{nome}: mantém as {esperado} opções",
               str(C.parse_options(tela)))


def teste_lista_do_cliente_e_faixa_de_horario():
    print("\n[B4] Lista gerada pelo cliente e faixa de horário")
    checar(C.parse_options(LISTA_DE_VEICULOS) == [],
           "a lista de veículos daquele segurado não vira menu",
           "'17 - Placa 0KM0000' e '18 - Nenhuma das opções anteriores' eram "
           "lacunas que nunca fechariam")
    checar(C.nao_e_rota(LISTA_DE_VEICULOS) == "lista_do_cliente",
           "e fica marcada com o motivo")
    # ...sem condenar "Nenhuma das anteriores" em menu de verdade.
    checar("Nenhuma das anteriores" in C.parse_options(
        MENUS_REAIS["particularidades dos ocupantes"][0]),
        "'Nenhuma das anteriores' continua sendo opção em menu real",
        "é por isso que a regra é de TELA, não de rótulo")

    for rotulo, acao in (("Manhã (08h às 12h)", "horario"),
                         ("Tarde (13h às 18h)", "horario"),
                         ("Entre 18h00 e 20h00", "horario"),
                         ("Responder novamente", "voltar"),
                         ("Voltar", "voltar"),
                         ("Sair", "sair")):
        checar(C.acao_conhecida(rotulo) == acao,
               f"'{rotulo}' vira {acao}", f"deu {C.acao_conhecida(rotulo)}")
    for rotulo in ("Guincho", "Chaveiro", "Nenhuma das anteriores",
                   "Cancelar serviço", "Novo serviço"):
        checar(C.acao_conhecida(rotulo) is None,
               f"'{rotulo}' continua sendo rota a descobrir")


def teste_nenhum_menu_real_perde_opcao():
    print("\n[B5] Nenhum menu real perde uma única opção")
    for nome, (tela, esperado) in MENUS_REAIS.items():
        ops = C.parse_options(tela)
        checar(len(ops) == esperado, f"{nome}: {esperado} opções",
               f"deu {len(ops)}: {ops}")


def _evento(direcao, texto, ts, interactive=None):
    return {"direction": direcao, "text": texto, "interactive": interactive,
            "wa_timestamp": str(ts), "created_at": f"2026-08-03T00:00:{ts:02d}Z"}


def teste_a_cobertura_conta_so_o_que_e_rota():
    print("\n[C] A fração inteira, tecida de ponta a ponta")
    menu = MENUS_REAIS["carroceria"][0]
    eventos = [
        _evento("in", A_URA_CONTINUA[0], 1),          # boas-vindas (NÃO é handoff)
        _evento("in", menu, 2),
        _evento("out", "Baú", 3),                     # uma escolha real
        _evento("in", "Certo! Vou seguir com Baú.", 4),
        _evento("in", TRANSFERENCIA[0][1], 5),        # aqui entra gente
        _evento("in", "Bom dia, desculpa a demora", 6),
        _evento("in", "imagina", 7),
        _evento("in", PESQUISA_ROTULADA, 8),
    ]
    mapa = W.weave_session({"root": None, "nodes": {}, "edges": {}}, eventos,
                           session_at="2026-08-03T00:00:00Z")
    W.compute_coverage(mapa)
    nos = list(mapa["nodes"].values())

    por_texto = {n["text"][:30]: n for n in nos}
    boas = next(n for n in nos if n["text"].startswith("Olá! Eu sou a assistente"))
    checar(boas.get("kind") != "handoff_humano",
           "a tela de boas-vindas NÃO é o handoff",
           "se fosse, tudo depois dela viraria conversa")
    checar(int(boas.get("pre_handoff") or 0) == 1,
           "e ela é contada do lado da URA")

    anuncio = next(n for n in nos if n["text"].startswith("Para seguir com o seu"))
    checar(anuncio.get("kind") == "handoff_humano",
           "a tela que anuncia a transferência é o fim da rota")

    fala = next(n for n in nos if n["text"].startswith("Bom dia, desculpa"))
    checar(fala.get("fase") == "humano",
           "'Bom dia, desculpa a demora' é fase humana, não tela de URA")
    checar(fala["text"] in [n["text"] for n in nos],
           "e CONTINUA no mapa — reclassificada, não apagada",
           "apagar destruiria a evidência de como o especialista conduz")

    pesquisa = next(n for n in nos if n["text"].startswith("A sua opinião"))
    checar(pesquisa.get("nao_rota") == "pesquisa_de_satisfacao",
           "a pesquisa fica no mapa marcada com o motivo")
    checar(not pesquisa.get("options"),
           "e sem opção nenhuma para contar",
           "eram 5 notas; ninguém dá todas, e a que faltou nunca fecha")

    cob = mapa["coverage"]
    checar(cob["options_total"] == 10,
           "o denominador é só o menu de verdade (10 opções)",
           f"deu {cob['options_total']}")
    checar(cob["options_covered"] >= 2,
           "o numerador traz o percorrido + o já conhecido (Baú, Voltar)",
           f"deu {cob['options_covered']}")
    checar(cob["nodes_humano"] >= 2,
           "as telas de conversa aparecem contadas à parte",
           f"nodes_humano={cob.get('nodes_humano')}")
    checar(cob.get("nodes_nao_rota") == 1,
           "e a não-rota também tem contagem própria",
           f"nodes_nao_rota={cob.get('nodes_nao_rota')}")
    checar(cob["nodes"] == len(nos),
           "e o total de nós continua sendo TODOS os nós",
           "reclassificar não pode encolher o registro")


def teste_a_formula_esta_escrita_onde_ela_mora():
    print("\n[D] A fórmula nova está escrita no código que a executa")
    weaver = _ler("app", "services", "atlas", "weaver.py")
    checar("A FÓRMULA DA COBERTURA" in weaver,
           "o denominador novo está documentado em compute_coverage",
           "número que ninguém sabe explicar volta a mentir na próxima leitura")
    checar('node.get("nao_rota")' in weaver,
           "e compute_coverage lê a marca de não-rota",
           "as opções também podem vir da estrutura `interactive`, que não "
           "passa por parse_options")
    checar("entrou_humano" in weaver and "_HUMANO_RE.search" not in weaver,
           "o Tecelão pergunta a `entrou_humano`, não ao regex cru")
    carto = _ler("app", "services", "cartographer.py")
    checar("_HUMANO_HIPOTETICO" in carto,
           "e o freio da oferta condicional existe no Cartógrafo")


def main() -> int:
    print("=" * 70)
    print("O ATLAS CONTA CERTO — SO ROTA ENTRA NA FRACAO")
    print("=" * 70)
    for t in (teste_as_23_frases_de_transferencia_da_hdi,
              teste_a_oferta_condicional_nao_e_handoff,
              teste_o_slogan_nao_e_menu,
              teste_a_pesquisa_de_satisfacao_nao_conta,
              teste_lista_do_cliente_e_faixa_de_horario,
              teste_nenhum_menu_real_perde_opcao,
              teste_a_cobertura_conta_so_o_que_e_rota,
              teste_a_formula_esta_escrita_onde_ela_mora):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O MAPA GUARDA TUDO. A CONTA SO INCLUI O QUE DA PARA PERCORRER.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
