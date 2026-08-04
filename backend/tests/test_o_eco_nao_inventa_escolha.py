# -*- coding: utf-8 -*-
"""O rotulador por eco não pode inventar "Voltar" — nem chamar palpite de fato.

Por que este arquivo existe
---------------------------
O Tecelão tem um atalho barato para as URAs de menu digitado: quando a escolha
do humano não chega como evento, ele olha se a tela SEGUINTE repetiu alguma
opção da tela anterior. "Certo! Para quando precisa do *chaveiro*?" depois de
um menu com "7 - Chaveiro" é uma pista boa.

Só que o atalho estava cego de um jeito específico. Ele exigia 4 letras no
rótulo para evitar ruído — e numa URA de botão `Sim` / `Não` / `Voltar` isso
descarta "sim" e "nao", que são as duas escolhas reais. Sobrava "voltar". E
"voltar" aparece no texto do destino porque a tela seguinte TAMBÉM tem um botão
Voltar. Resultado: o eco achava exatamente um casamento, declarava a ambiguidade
resolvida, e gravava a aresta.

📊 Medido em 04/08/2026 nos 10 mapas `observed` de produção: **47** arestas
rotuladas por eco, **35** delas (74%) com Voltar/Sair/menu. No mapa da HDI:

    "O veículo é elétrico ou híbrido?"  --Voltar (5x)-->  "O veículo é rebaixado?"
    "Houve vítimas no local?"           --Voltar (6x)-->  "A polícia foi acionada?"

📊 O que o humano de fato respondeu na primeira: 14 cliques sem rótulo e 4
"Não". Zero "Voltar".

E o pior não era o rótulo errado: a aresta nascia `inferred=False`. Um palpite
entrava no mapa com a mesma cara de uma escolha que alguém clicou. Quem lê o
mapa — hoje o painel, amanhã o agente que aciona a seguradora — não tinha como
separar as duas coisas. O mapa mentia com cara de verdade.

Hoje isso é arma carregada e não disparada: `get_active_map` filtra
`status='active'` e o banco não tem nenhum mapa `active`. No dia em que alguém
promover um mapa, o agente começa a clicar em "Voltar" no meio do acionamento.

Cada guarda aqui vem com um CONTROLE
------------------------------------
Guarda que só sabe dizer "não" não guarda nada: ele passaria igual se o eco
estivesse desligado. Por isso todo caso proibido tem ao lado um caso permitido,
com a mesma forma, que PRECISA ser rotulado. É o que dá direito de dizer que a
regra separa as duas coisas em vez de recusar tudo.

Os textos são reais, copiados de `observed_events`/`ura_maps` de produção.
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


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


carregar("app.services.ura_map_service")
C = carregar("app.services.cartographer")
T = carregar("app.services.atlas.templater")
W = carregar("app.services.atlas.weaver")


# ── ferramentas ───────────────────────────────────────────────────────────────

def _ev(direcao: str, hora: str, texto: str, interativo=None) -> dict:
    return {"session_id": "s1", "direction": direcao, "wa_timestamp": hora,
            "msg_type": "text", "text": texto, "interactive": interativo}


def duas_telas(origem: str, destino: str, vezes: int = 1) -> dict:
    """Um mapa com UMA aresta sequencial origem→destino, do jeito que o Tecelão
    a cria quando o clique não foi capturado. As telas passam pelo parser de
    verdade (`screen_node`) — testar o eco contra um parser de mentira testaria
    a mentira."""
    a, b = T.screen_node(origem), T.screen_node(destino)
    return {"nodes": {a["hash"]: {**a, "samples": vezes},
                      b["hash"]: {**b, "samples": vezes}},
            "edges": {f"{a['hash']}|→": {
                "src": a["hash"], "label": "→", "to": b["hash"], "count": vezes,
                "inferred": True, "order": 1, "dests": {b["hash"]: vezes}}}}


def rotulo_do_eco(mapa: dict):
    """Roda o rotulador e devolve (rótulo, inferred) da aresta que ele criou —
    ou (None, None) se ele não mexeu."""
    W.label_inferred_edges(mapa)
    for aresta in mapa["edges"].values():
        if aresta.get("echo"):
            return aresta.get("label"), aresta.get("inferred")
    return None, None


# ── telas REAIS de produção ───────────────────────────────────────────────────

HDI_ELETRICO = "O veículo é elétrico ou híbrido?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar"
HDI_REBAIXADO = "O veículo é rebaixado?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar"
HDI_VITIMAS = "Houve vítimas no local?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar"
HDI_POLICIA = "A polícia foi acionada?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar"

ALLIANZ_MENU = ("O que você precisa?\n\n"
                "*1 -* Guincho para pane mecânica\n"
                "*2 -* Borracheiro / troca de pneu\n"
                "*7 -* Chaveiro")
ALLIANZ_ECO = "Certo! Para quando precisa do *chaveiro*?\n\n*1 -* Agora\n*2 -* Quero agendar\n*9 -* Voltar"

BRADESCO_DIA = ("Pra qual dia você prefere fazer o agendamento?\n"
                "Botão 1: Hoje\nBotão 2: Amanhã\nBotão 3: Outro Dia")
BRADESCO_HORARIO = ("E qual o melhor horário?\n\nMe diga no formato de 24h, por favor.\n\n"
                    "Exemplos:\n*06:00* para manhã\n*18:00* para tarde.")

PORTO_CPF_INVALIDO = ("Desculpe, não entendi a sua resposta. Por favor, digite um "
                      "*CPF ou CNPJ válido*, conforme exemplos abaixo\n\n"
                      "*123.456.789-00*\n*12.345.678/0001-90*")
PORTO_PEDE_CPF = "Para continuar com seu atendimento, por favor, digite o seu *CPF ou CNPJ*."

PORTO_DIGITE_VOLTAR = "Se quiser mudar de opção, digite voltar."
PORTO_CONFIRMA = ("Entendi! Lembre-se de que o serviço será realizado somente se as peças "
                  "solicitadas estiverem no local na data do retorno.\n\n"
                  "Posso continuar com o agendamento?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar")


# ── 1. o caso que faltava ─────────────────────────────────────────────────────

def teste_ura_de_botao_nao_ganha_rota_para_voltar():
    print("\n[1] Sim/Não/Voltar: o destino também tem Voltar — e isso não é eco")
    for origem, destino, apelido in ((HDI_ELETRICO, HDI_REBAIXADO, "elétrico→rebaixado"),
                                     (HDI_VITIMAS, HDI_POLICIA, "vítimas→polícia")):
        rot, _inf = rotulo_do_eco(duas_telas(origem, destino, vezes=5))
        checar(rot != "Voltar", f"{apelido}: o rótulo NÃO é 'Voltar'",
               f"rotulou {rot!r} — foi assim que 35 rotas falsas entraram nos mapas")
        checar(rot is None, f"{apelido}: e a aresta continua sem rótulo",
               f"rotulou {rot!r}; a escolha real (Sim/Não) o eco não tem como saber")


def teste_o_palpite_continua_sendo_palpite():
    print("\n[2] Eco não zera `inferred` — palpite não vira escolha capturada")
    rot, inferido = rotulo_do_eco(duas_telas(ALLIANZ_MENU, ALLIANZ_ECO))
    checar(rot == "7 - Chaveiro", "o eco legítimo da Allianz continua sendo lido",
           f"rotulou {rot!r}")
    checar(inferido is True, "e a aresta nasce `inferred=True`",
           f"inferred={inferido!r} — um rótulo adivinhado com cara de clique real")

    # CONTROLE: prove que `inferred` CONSEGUE ser False. Um guarda que compara
    # duas coisas precisa mostrar que elas podem ser diferentes (§9.3), senão
    # ele passaria igual se o campo estivesse morto em True.
    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, [
        _ev("in", "1", ALLIANZ_MENU),
        _ev("out", "2", "Chaveiro", {"kind": "button_reply", "title": "Chaveiro"}),
        _ev("in", "3", ALLIANZ_ECO)])
    capturadas = [e for e in acc["edges"].values() if e.get("inferred") is False]
    checar(capturadas, "CONTROLE: com clique capturado, `inferred` é False",
           str([(e["label"], e["inferred"]) for e in acc["edges"].values()]))


# ── 2. cada guarda com o seu controle ─────────────────────────────────────────

def teste_navegacao_conhecida_nunca_vira_escolha():
    print("\n[3] Guarda 1 — palavra de navegação não é escolha")
    # 📊 Esta é a única regra que pega os dois casos da Porto em que a palavra
    # "voltar" está na PROSA do destino, não no menu dele: a tela seguinte é
    # literalmente "Se quiser mudar de opção, digite voltar.". A regra da prosa
    # não alcança; a lista de navegação, sim.
    rot, _ = rotulo_do_eco(duas_telas(PORTO_CONFIRMA, PORTO_DIGITE_VOLTAR))
    checar(rot is None, "'digite voltar' no texto do destino não rotula nada",
           f"rotulou {rot!r}")

    # CONTROLE: a mesma forma — destino sem menu, ecoando uma opção na prosa —
    # com uma opção que NÃO é navegação. Tem de rotular.
    rot, _ = rotulo_do_eco(duas_telas(
        "É reparo ou instalação?\nBotão 1: Reparo\nBotão 2: Instalação\nBotão 3: Voltar",
        "A *instalação de luminária ou lustre* é realizada pela Porto Serviço."))
    checar(rot == "Instalação", "CONTROLE: eco de verdade na prosa continua sendo lido",
           f"rotulou {rot!r}")


def teste_opcao_repetida_no_menu_do_destino_nao_e_eco():
    print("\n[4] Guarda 2 — palavra que só aparece no MENU do destino não é eco")
    # Uma opção de navegação que a lista do Cartógrafo NÃO conhece: "Alterar
    # dados". É o caso que só a regra da prosa pega — e é por ele que ela existe,
    # já que a lista de palavras conhecidas é fechada e envelhece.
    rot, _ = rotulo_do_eco(duas_telas(
        "Deseja continuar?\nBotão 1: Prosseguir\nBotão 2: Alterar dados",
        "Confirme o endereço de atendimento.\nBotão 1: Confirmar\nBotão 2: Alterar dados"))
    checar(C.acao_conhecida("Alterar dados") is None,
           "'Alterar dados' não está na lista de navegação conhecida",
           "se estivesse, este caso não provaria nada sobre a regra da prosa")
    checar(rot is None, "opção repetida no menu do destino não rotula",
           f"rotulou {rot!r} — botão repetido não é a tela ecoando a escolha")

    # CONTROLE: a MESMA palavra, agora na prosa do destino em vez de no menu.
    rot, _ = rotulo_do_eco(duas_telas(
        "Deseja continuar?\nBotão 1: Prosseguir\nBotão 2: Alterar dados",
        "Certo, vamos alterar dados do seu cadastro.\nBotão 1: Confirmar"))
    checar(rot == "Alterar dados", "CONTROLE: a mesma palavra NA PROSA rotula",
           f"rotulou {rot!r} — sem isto a regra recusaria tudo e pareceria certa")


def teste_eco_nao_casa_no_meio_de_palavra():
    print("\n[5] Guarda 3 — 'para manhã' não é 'Amanhã'")
    # 📊 Caso real do mapa da Bradesco em 04/08/2026. A normalização antiga
    # apagava o espaço: "para manhã" virava `paramanha`, que contém `amanha`.
    # A aresta foi gravada como se a pessoa tivesse escolhido *Amanhã*.
    rot, _ = rotulo_do_eco(duas_telas(BRADESCO_DIA, BRADESCO_HORARIO))
    checar(rot is None, "'*06:00* para manhã' não vira a escolha 'Amanhã'",
           f"rotulou {rot!r}")

    # CONTROLE: quando o destino diz "amanhã" DE VERDADE, tem de rotular.
    rot, _ = rotulo_do_eco(duas_telas(
        BRADESCO_DIA, "Certo! Vou agendar para amanhã. Posso confirmar?"))
    checar(rot == "Amanhã", "CONTROLE: 'agendar para amanhã' rotula 'Amanhã'",
           f"rotulou {rot!r}")


def teste_valor_mascarado_nao_e_opcao_de_menu():
    print("\n[6] Guarda 4 — {CNPJ} não é escolha de menu")
    # 📊 Duas arestas assim nos mapas de produção. A tela de erro da Porto traz
    # exemplos de CPF/CNPJ, o leitor de opções capturou o exemplo como se fosse
    # escolha, e o eco casou `{CNPJ}` com a palavra "CNPJ" da pergunta seguinte.
    origem = T.screen_node(PORTO_CPF_INVALIDO)
    checar([o["label"] for o in origem["options"]] == ["{CNPJ}"],
           "a tela de erro da Porto realmente oferece '{CNPJ}' como opção",
           "se o parser mudar e não oferecer mais, este teste perde o objeto")
    rot, _ = rotulo_do_eco(duas_telas(PORTO_CPF_INVALIDO, PORTO_PEDE_CPF))
    checar(rot is None, "valor mascarado não vira rota", f"rotulou {rot!r}")

    checar(W._so_placeholder("{CNPJ}") and W._so_placeholder("*{CPF}*"),
           "e a regra reconhece o rótulo que é só máscara")
    checar(not W._so_placeholder("Veículo {PLACA}"),
           "CONTROLE: rótulo com palavra de verdade não é descartado",
           "descartar 'Veículo {PLACA}' apagaria rota real")


# ── 3. os outros dois consertos ───────────────────────────────────────────────

def teste_paths_guarda_as_sessoes_mais_recentes():
    print("\n[7] `paths` guarda as 12 MAIS RECENTES, e a mais nova por último")
    # 📊 Era o contrário. `del paths[:-12]` guarda as 12 ÚLTIMAS ANEXADAS, e o
    # laço do Tecelão é recência-primeiro: sobravam as 12 mais ANTIGAS. No mapa
    # da Allianz, caminhos de 28/07/2025 a 17/09/2025 com sessão mais nova em
    # 04/08/2026 — onze meses de atraso.
    acc = {"root": None, "nodes": {}, "edges": {}}
    for dia in range(13, 0, -1):  # recência-primeiro, como `weave_insurer`
        W.weave_session(acc, [_ev("in", "1", "Escolha:\n*1 -* Guincho\n*2 -* Chaveiro"),
                              _ev("out", "2", "1"),
                              _ev("in", "3", f"Certo, dia {dia}. Qual o CEP?")],
                        session_at=f"2026-08-{dia:02d}T10:00:00Z")
    datas = [p["at"] for p in acc["paths"]]
    checar(len(datas) == 12, "guarda 12 caminhos", str(len(datas)))
    checar("2026-08-01T10:00:00Z" not in datas,
           "a sessão mais ANTIGA das 13 ficou de fora", str(datas[:2]))
    checar(datas[-1] == "2026-08-13T10:00:00Z",
           "e `paths[-1]` é a MAIS RECENTE", str(datas[-1]))
    # `route_sentinel._script_from_observed` lê `paths[-1]` chamando-o de
    # "transcript observado mais recente". Era a conversa mais antiga de todas
    # que virava script do Simulador do Alfaiate.
    fonte = open(os.path.join(RAIZ, "app", "services", "atlas", "route_sentinel.py"),
                 encoding="utf-8").read()
    checar("paths[-1]" in fonte,
           "e o Alfaiate continua lendo `paths[-1]` — agora é a certa",
           "se ele mudar de índice, a ordem de `paths` precisa mudar junto")

    # CONTROLE: com 12 sessões ou menos, nada é descartado — inclusive a mais
    # antiga. Sem isto, o teste acima passaria com uma lista sempre vazia.
    acc2 = {"root": None, "nodes": {}, "edges": {}}
    for dia in range(12, 0, -1):
        W.weave_session(acc2, [_ev("in", "1", "Escolha:\n*1 -* Guincho\n*2 -* Chaveiro"),
                               _ev("out", "2", "1"),
                               _ev("in", "3", f"Certo, dia {dia}. Qual o CEP?")],
                        session_at=f"2026-08-{dia:02d}T10:00:00Z")
    checar("2026-08-01T10:00:00Z" in [p["at"] for p in acc2["paths"]],
           "CONTROLE: cabendo todas, a mais antiga FICA",
           str([p["at"] for p in acc2["paths"]]))


ESPERA_PORTO = "Aguarde um momento 🙂"
SAUDACAO = "Olá! Sou a assistente virtual. O que você precisa?\nBotão 1: Guincho\nBotão 2: Chaveiro"


def _sessao_comecando_em(tela: str) -> list:
    return [_ev("in", "1", tela), _ev("in", "2", "Qual o CEP do local?")]


def teste_tela_de_espera_nao_e_raiz():
    print("\n[8] 'Aguarde um momento 🙂' não é a porta de entrada da URA")
    # 📊 Era a raiz do mapa da Porto em 04/08/2026: 93 aparições, mas só 10 das
    # 149 sessões começam nela — e 57 arestas apontam PARA ela. Venceu porque é
    # a única candidata que não fragmenta: as aberturas de verdade trazem o nome
    # do cliente no meio da frase e viram um nó por nome.
    acc = {"root": None, "nodes": {}, "edges": {}}
    for _ in range(3):
        W.weave_session(acc, _sessao_comecando_em(ESPERA_PORTO))
    for _ in range(2):
        W.weave_session(acc, _sessao_comecando_em(SAUDACAO))
    W.compute_coverage(acc)
    raiz = acc["nodes"][acc["root"]]["text"]
    checar("Aguarde" not in raiz, "a tela de espera perde a eleição mesmo com MAIS aberturas",
           f"raiz ficou {raiz[:50]!r}")
    checar("assistente virtual" in raiz, "e a saudação com menu ganha", raiz[:50])

    # CONTROLE 1: se a espera for a ÚNICA candidata, ela é eleita — a regra
    # tira da urna, não apaga o mapa.
    so_espera = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(so_espera, _sessao_comecando_em(ESPERA_PORTO))
    W.compute_coverage(so_espera)
    checar("Aguarde" in so_espera["nodes"][so_espera["root"]]["text"],
           "CONTROLE: sem outra candidata, a espera volta a ser raiz",
           "senão o mapa ficaria sem raiz nenhuma")

    # CONTROLE 2: a regra é estreita de propósito — tela que pede paciência mas
    # OFERECE menu continua sendo entrada legítima.
    checar(W._tela_de_espera({"text": ESPERA_PORTO, "options": []}),
           "a tela de espera pura é reconhecida")
    checar(not W._tela_de_espera(
        {"text": "Aguarde um momento. Enquanto isso, escolha:",
         "options": [{"label": "Guincho"}]}),
        "CONTROLE: tela com menu NUNCA é tratada como espera")
    checar(not W._tela_de_espera({"text": SAUDACAO, "options": [{"label": "Guincho"}]}),
           "e a saudação também não")


def teste_a_contagem_de_aberturas_fica_no_mapa():
    print("\n[9] A eleição da raiz fica auditável")
    # `_starts` é apagado antes de salvar. Quem auditasse o mapa depois não
    # tinha como saber por que aquela tela foi eleita — foi exatamente a
    # pergunta que ninguém conseguiu responder sobre a Porto sem reprocessar.
    acc = {"root": None, "nodes": {}, "edges": {}}
    for _ in range(3):
        W.weave_session(acc, _sessao_comecando_em(SAUDACAO))
    W.compute_coverage(acc)
    checar(acc["nodes"][acc["root"]].get("starts") == 3,
           "o nó guarda quantas sessões começaram nele",
           str(acc["nodes"][acc["root"]].get("starts")))
    outros = [n for nid, n in acc["nodes"].items() if nid != acc["root"]]
    checar(all(not n.get("starts") for n in outros),
           "CONTROLE: e quem não abre sessão nenhuma não recebe a marca",
           str([(n["text"][:20], n.get("starts")) for n in outros]))


# ── 4. o que o conserto NÃO pode ter levado junto ─────────────────────────────

def teste_o_eco_legitimo_continua_vivo():
    print("\n[10] O eco continua servindo para o que ele existe")
    # Se o conserto tivesse desligado o eco, tudo acima passaria — e o Tecelão
    # perderia as rotas de menu digitado que só ele resolve.
    casos = (
        (ALLIANZ_MENU, ALLIANZ_ECO, "7 - Chaveiro"),
        ("Quantas caixas d’água precisam do serviço?\n\n"
         "*1 -* 01 (uma) unidade\n*2 -* 02 (duas) unidades",
         "Será disponibilizado mão de obra para limpeza e higienização da caixa "
         "d’água, limitada a 02 (duas) unidades de até 2.500 litros cada.",
         "2 - 02 (duas) unidades"),
        ("Para esse CPF localizamos algumas assistências.\nDeseja acompanhar?\n"
         "Botão 1: Acompanhar\nBotão 2: Novo serviço\nBotão 3: Voltar",
         "Selecione o serviço que você deseja acompanhar:\nENCANADOR\nENCANADOR",
         "Acompanhar"),
        ("Agora, preciso que selecione abaixo a opção que corresponde com o seu problema:\n"
         "Botão 1: Falta de energia\nBotão 2: Problema elétrico",
         "Selecione abaixo qual é o problema elétrico:\nTomadas\nInterruptores\nLâmpadas",
         "Problema elétrico"),
    )
    for origem, destino, esperado in casos:
        rot, inferido = rotulo_do_eco(duas_telas(origem, destino))
        checar(rot == esperado, f"eco legítimo: {esperado!r}", f"rotulou {rot!r}")
        checar(inferido is True, f"e {esperado!r} continua marcado como palpite",
               f"inferred={inferido!r}")


def teste_a_opcao_deduzida_se_declara_deduzida():
    print("\n[11] Quem lê o mapa consegue separar palpite de fato")
    acc = {"root": None, "nodes": {}, "edges": {}}
    W.weave_session(acc, [_ev("in", "1", ALLIANZ_MENU), _ev("in", "2", ALLIANZ_ECO)])
    W.label_inferred_edges(acc)
    W.compute_coverage(acc)
    opcoes = {o["label"]: o for n in acc["nodes"].values() for o in n["options"]}
    chaveiro = opcoes.get("7 - Chaveiro")
    checar(chaveiro and chaveiro.get("confidence") == "echo",
           "a opção deduzida pelo eco é marcada `confidence='echo'`",
           str(chaveiro))
    guincho = opcoes.get("1 - Guincho para pane mecânica")
    checar(guincho and guincho.get("confidence") == "gap",
           "CONTROLE: e a que ninguém percorreu continua lacuna",
           str(guincho))


def main() -> int:
    print("=" * 70)
    print("O ECO É PISTA, NÃO TESTEMUNHA")
    print("=" * 70)
    for teste in (teste_ura_de_botao_nao_ganha_rota_para_voltar,
                  teste_o_palpite_continua_sendo_palpite,
                  teste_navegacao_conhecida_nunca_vira_escolha,
                  teste_opcao_repetida_no_menu_do_destino_nao_e_eco,
                  teste_eco_nao_casa_no_meio_de_palavra,
                  teste_valor_mascarado_nao_e_opcao_de_menu,
                  teste_paths_guarda_as_sessoes_mais_recentes,
                  teste_tela_de_espera_nao_e_raiz,
                  teste_a_contagem_de_aberturas_fica_no_mapa,
                  teste_o_eco_legitimo_continua_vivo,
                  teste_a_opcao_deduzida_se_declara_deduzida):
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
    print("O MAPA DIZ O QUE SABE, E DIZ COMO SABE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
