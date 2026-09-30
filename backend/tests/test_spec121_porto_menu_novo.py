# -*- coding: utf-8 -*-
"""🔴 SPEC-121 F2 · A PORTO AUTO VOLTA A PASSAR DO PRIMEIRO MENU — pelo MOTOR.

📊 29/09/2026, BLOCO 0 (`observed_events`, 33.628 eventos): a Porto auto ganhou
menus novos entre o menu raiz e o "De que atendimento você precisa?". Nenhum
passo os casava, e o gatilho `sinistro` — que só estava LISTADO como opção —
passava o caso para uma pessoa ANTES do serviço, em qualquer serviço:

    910b6295 (14/09) e 9e043112 (29/09)   "Você quer falar sobre qual assunto?"
    ba772444 (16/03)                       "Sobre o que você deseja falar?"
    4830574a (19/06)                       "Escolha sobre o que você quer falar:"
                                           "O que você precisa sobre *Seguro Auto*?"
    todas                                  "Por favor, selecione o veículo."

🔴 Este arquivo chama o MOTOR (`handle_insurer_message`, `detect_handoff_trigger`)
sobre o texto REAL das telas (CLAUDE.md §9.4). O simulador lê o acervo versionado,
onde 9e043112 não está — por isso este teste é próprio (G3).

⛔ Nenhum dado pessoal: o nome da tela vira "Cliente", a marca do carro fica, a
placa é fictícia e vai com a MESMA máscara que a Porto usa (`R####81`).
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import insurer_dispatch_service as IDS  # noqa: E402

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


REF = "porto-auto-whatsapp@v1"
PB = CP.get_playbook(REF)
Q = chr(10)

# ---- as telas, na ordem da sessão 9e043112 (29/09), texto do acervo ----------
TELA_TITULAR = "Eu estou falando com Cliente?" + Q + "Botão 1: Sim" + Q + "Botão 2: Não"
TELA_CPF = "Para continuar com seu atendimento, por favor, digite o seu *CPF ou CNPJ*."
TELA_RAIZ = ("Cliente, escolha a opção desejada:" + Q + "SOS auto ou casa" + Q +
             "Solicitar ou acompanhar assistência emergencial" + Q + "Seguro Auto" + Q +
             "Serviço para residência" + Q + "Sinistro de terceiro" + Q +
             "Avisar ou acompanhar" + Q + "Contrate a Porto" + Q +
             "Confira nossos produtos e serviços" + Q + "Outros produtos" + Q +
             "Informar outro CPF/CNPJ")
TELA_ASSUNTO = ("Você quer falar sobre qual assunto?" + Q + "Assistência" + Q +
                "Consultar apólice" + Q + "Informações e cobertura da apólice" + Q +
                "Sinistro" + Q + "Avisar ou acompanhar sinistro de segurado ou terceiro" + Q +
                "Assuntos financeiros" + Q + "Voltar")
TELA_AGUARDE = "Aguarde um momento 🙂"
TELA_VEICULO = ("Por favor, selecione o veículo." + Q + "Veículo 1" + Q +
                "VOLKSWAGEN - Ano 2020 - Placa R####81" + Q + "Outro veículo" + Q + "Voltar")
TELA_ATENDIMENTO = ("De que atendimento você precisa?" + Q + "Novo serviço" + Q +
                    "Acompanhar um serviço" + Q + "Cancelar serviço" + Q +
                    "Consultar extrato" + Q + "Seguro e apólice" + Q +
                    "Assistência Mercosul" + Q + "Não encontrei o assunto" + Q + "Voltar")
TELA_SERVICO = ("O que você precisa?" + Q + "Guincho (reboque)" + Q + "Bateria" + Q +
                "Chaveiro para veículo" + Q + "Técnico" + Q + "Táxi" + Q +
                "Não encontrei o assunto" + Q + "Voltar")
# ---- as variantes (ba772444, 4830574a, e o formato antigo da lista de veículos)
TELA_DESEJA_FALAR = ("Sobre o que você deseja falar?" + Q + "Assistência" + Q +
                     "Assistência para casa e carro" + Q + "Consultar apólice" + Q +
                     "Informações e cobertura da apólice" + Q + "Sinistro" + Q +
                     "Avisar ou acompanhar sinistro auto e residência" + Q +
                     "Assuntos financeiros" + Q + "Vidros e faróis")
TELA_PERSONALIZADO = ("Escolha sobre o que você quer falar:" + Q + "Cartão de Crédito" + Q +
                      "Seguro Auto" + Q + "Seguro Residência" + Q + "Seguro Saúde" + Q +
                      "Seguro Odonto" + Q + "Seguro de Vida" + Q + "Outros assuntos" + Q +
                      "Informar outro CPF/CNPJ")
TELA_SOBRE_AUTO = "O que você precisa sobre *Seguro Auto*?" + Q + "Assistência" + Q + "Sinistro" + Q + "Voltar"
TELA_VEICULO_ANTIGA = ("Por favor, selecione o veículo:" + Q + "KIA" + Q +
                       "placa R####81 | ano 2021" + Q + "Outro veículo" + Q + "Voltar")
# ---- D11: a consultora (4830574a) e o aviso que NÃO é a consultora (f4838bb3)
TELA_CONSULTORA = ("Olá! 😊 Aqui é a Cliente. Sou consultora de relacionamento e darei "
                   "continuidade ao seu atendimento. Como posso te ajudar?")
TELA_PERSONALIZADO_AVISO = (
    "Identifiquei aqui no sistema que você faz parte do nosso grupo de clientes com "
    "atendimento personalizado, porém seu consultor de relacionamento atende de "
    "*segunda à sexta, das 9h às 18h*. Mas seguiremos com seu atendimento de forma automática.")
# ---- CONTROLE: telas em que "sinistro" é o ASSUNTO, não uma opção (acervo porto)
TELAS_DE_SINISTRO = [
    "O guincho seria por pane ou sinistro ?",
    "Digite o *número do sinistro* que você quer consultar. Insira apenas os números, por favor.",
    "Atualmente, este sinistro está em andamento. Mas você pode seguir com a sua solicitação acessando o link 👇",
    ("Vamos ver se ainda consigo te ajudar por aqui. Você gostaria de falar sobre serviços "
     "relacionados a um *sinistro que já foi avisado*?" + Q + "Botão 1: Sim" + Q +
     "Botão 2: Não" + Q + "Botão 3: Voltar"),
    ("Cliente, vou te mostrar as opções para falar sobre sinistro de outro veículo neste canal." +
     Q + "Consultar outro CPF/CNPJ" + Q + "Sinistro de terceiros" + Q + "Outro produto"),
]

PLACA_DO_CASO = "RQX1B81"   # fictícia; casa a máscara R####81
CASO = {
    "titular_cpf": "11122233344", "veiculo_placa": PLACA_DO_CASO,
    "titular_nome": "Cliente", "local_atual": "Rua X, 100, Florianópolis, SC",
    "problema_descricao": "a bateria arriou", "quando": "agora",
    "telefone_contato": "48999998888", "pessoa_no_local": "Cliente",
    "bateria_tipo_opcao": "Recarga de bateria",
}


def sessao(subservico="bateria", **extra):
    slots = dict(CASO)
    slots.update(extra)
    return IDS.start_dispatch(IDS.new_dispatch_session(
        case_id="pt121", company_id="co", playbook_ref=REF, subservice=subservico, slots=slots))


def responder(s, tela):
    antes = len([t for t in s.get("transcript") or [] if t.get("direction") == "out"])
    s = IDS.handle_insurer_message(s, tela)
    saidas = [t.get("text") for t in s.get("transcript") or [] if t.get("direction") == "out"]
    return s, (saidas[antes:] or [None])[-1]


print("=" * 74)
print("[1] 🔴 O FIO: a sessão de 29/09 inteira até o serviço, pelo MOTOR")
print("=" * 74)
s = sessao("bateria")
esperado = [
    (TELA_TITULAR, "Não"), (TELA_CPF, "11122233344"), (TELA_RAIZ, "Seguro Auto"),
    (TELA_ASSUNTO, "Assistência"), (TELA_AGUARDE, None), (TELA_VEICULO, "Veículo 1"),
    (TELA_ATENDIMENTO, "Novo serviço"), (TELA_SERVICO, "Bateria"),
]
for tela, quero in esperado:
    s, r = responder(s, tela)
    certo(r == quero and s.get("state") not in ("needs_human",),
          f"{tela.splitlines()[0][:48]!r} → {quero!r}",
          f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")

print()
print("=" * 74)
print("[2] as variantes do menu, cada uma pelo motor")
print("=" * 74)
for tela, quero in ((TELA_DESEJA_FALAR, "Assistência"), (TELA_PERSONALIZADO, "Seguro Auto"),
                    (TELA_SOBRE_AUTO, "Assistência"), (TELA_VEICULO_ANTIGA, "KIA")):
    s, r = responder(sessao("guincho"), tela)
    certo(r == quero and s.get("state") != "needs_human",
          f"{tela.splitlines()[0][:48]!r} → {quero!r}",
          f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")

print()
print("=" * 74)
print("[3] 🔴 o veículo sai da PLACA do caso — e sem placa que bata, NUNCA chuta")
print("=" * 74)
s, r = responder(sessao("guincho", veiculo_placa="QQQ1111"), TELA_VEICULO)
certo(r is None and s.get("state") == "needs_human",
      "placa que NÃO bate com a da lista → uma pessoa escolhe (nunca 'Veículo 1' por posição)",
      f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")
certo("veiculo_placa" not in str(s.get("reason") or ""),
      "o motivo não diz que falta a PLACA (a placa existe; o que falta é o veículo na lista)",
      f"reason={s.get('reason')!r}")
DOIS = TELA_VEICULO.replace("Outro veículo", "Veículo 2" + Q + "FIAT - Ano 2019 - Placa R####81" + Q + "Outro veículo")
s, r = responder(sessao("guincho"), DOIS)
certo(r is None and s.get("state") == "needs_human",
      "DUAS opções casam a máscara → ambíguo → uma pessoa",
      f"respondeu {r!r} · state={s.get('state')!r}")
certo(CP.render_reply({**CP.match_ura_step(PB, TELA_VEICULO), }, CASO).get("reply") == "Veículo 1",
      "render_reply puro (motor, sem sessão) devolve o RÓTULO — a Porto rejeita número")

print()
print("=" * 74)
print("[4] 🔴 'Sinistro' como OPÇÃO de menu não passa o caso — como ASSUNTO, passa")
print("=" * 74)
for tela in (TELA_ASSUNTO, TELA_SOBRE_AUTO, TELA_DESEJA_FALAR, TELA_RAIZ):
    certo(CP.detect_handoff_trigger(PB, tela) is None,
          f"gatilho NÃO dispara em {tela.splitlines()[0][:44]!r}",
          f"disparou {CP.detect_handoff_trigger(PB, tela)!r}")
for tela in TELAS_DE_SINISTRO:
    certo(CP.detect_handoff_trigger(PB, tela) == r"sinistro",
          f"🔴 CONTROLE: sinistro como assunto ainda dispara: {tela[:50]!r}",
          f"disparou {CP.detect_handoff_trigger(PB, tela)!r}")
s, r = responder(sessao("guincho"), TELAS_DE_SINISTRO[0])
certo(s.get("state") == "needs_human" and str(s.get("reason") or "").startswith("handoff_trigger:"),
      "🔴 CONTROLE pelo motor: 'pane ou sinistro?' vai a uma pessoa",
      f"state={s.get('state')!r} reason={s.get('reason')!r}")

def na_ura(subservico="bateria", **extra):
    """A sessão JÁ na URA — o caso de guincho do teste não tem destino/endereço
    completos e ficaria em `preparing`; aqui só se afirma a TELA."""
    s = sessao(subservico, **extra)
    s["state"] = "ura"
    return s


# 🔴 CONSERTO ÚNICO (red team P1) — A IRMÃ PRECISA SER GUARDADA. 📊 Pelo motor sobre
#    o acervo porto, 10 telas do FLUXO DE SINISTRO só vão a uma pessoa POR CAUSA da
#    irmã (menu com `Sinistro` entre as opções e SEM a assistência ao lado). Três
#    delas, texto do acervo (`porto-auto.jsonl`, nome mascarado):
TELAS_DO_FLUXO_DE_SINISTRO = [
    ("51b2ed32", "O que você quer fazer agora?" + Q + "Botão 1: Acompanhar sinistro" + Q +
     "Botão 2: Falar com a Porto"),
    ("51b2ed32", "Antes de transferir sua conversa para um especialista, por favor, escolha um assunto:" +
     Q + "Dúvidas sobre orçamento" + Q + "Informações sobre peças" + Q + "Lucros cessantes" + Q +
     "Vistoria" + Q + "Reagendamento ou complemento" + Q + "Mais sobre sinistro" + Q + "Voltar"),
    ("ca755794", "O que você gostaria de fazer?" + Q + "Contrate a Porto" + Q +
     "Confira nossos produtos e serviços" + Q + "Sinistro Auto" + Q +
     "Abertura e acompanhamento de sinistro exclusivo para terceiros" + Q +
     "Informar outro CPF/CNPJ" + Q + "Voltar"),
]
for sid, tela in TELAS_DO_FLUXO_DE_SINISTRO:
    certo(CP.detect_handoff_trigger(PB, tela) == r"sinistro",
          f"🔴 [P1] {sid}: menu do FLUXO DE SINISTRO (sem a irmã) ainda dispara: {tela.splitlines()[0][:40]!r}",
          f"disparou {CP.detect_handoff_trigger(PB, tela)!r}")
    s, r = responder(na_ura("guincho"), tela)
    certo(r is None and s.get("state") == "needs_human",
          f"   e pelo MOTOR vai a uma pessoa ({sid})",
          f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")

# 🔴 CONSERTO ÚNICO (red team P2) — a MESMA tela, NUMERADA. 📊 porto-auto 51b2ed32,
#    0c1e8e3e, b1ff65f2, e5318468 (assistência). O passo `menu_atendimento` já a
#    respondia; agora o GATILHO também sabe que o `*4* - Sinistro` é opção.
TELA_ATENDIMENTO_NUMERADA = Q.join([
    "De que atendimento você precisa?", "", "*1* - Novo serviço", "*2* - Acompanhar um serviço",
    "*3* - Cancelar serviço agendado", "*4* - Sinistro", "*5* - Consultar extrato",
    "*6* - Seguro e apólice", "*7* - Ajuda com o App da Porto", "*8* - Mercosul", "*9* - Voltar"])
certo(CP.detect_handoff_trigger(PB, TELA_ATENDIMENTO_NUMERADA) is None,
      "[P2] o gatilho NÃO dispara na forma NUMERADA ('*4* - Sinistro' é opção)",
      f"disparou {CP.detect_handoff_trigger(PB, TELA_ATENDIMENTO_NUMERADA)!r}")
for sub in ("guincho", "tecnico", "vidros"):
    s, r = responder(na_ura(sub), TELA_ATENDIMENTO_NUMERADA)
    certo(r == "Novo serviço" and s.get("state") != "needs_human",
          f"   e pelo MOTOR ({sub}) responde 'Novo serviço'", f"respondeu {r!r} · state={s.get('state')!r}")
TELA_NUMERADA_SEM_IRMA = Q.join(["O que você precisa?", "", "*1* - Guincho ou outros serviços",
                                 "*2* - Informações sobre pagamento", "*3* - Sinistro de Veículos",
                                 "*4* - Voltar"])
certo(CP.detect_handoff_trigger(PB, TELA_NUMERADA_SEM_IRMA) == r"sinistro",
      "🔴 CONTROLE [P2]: menu numerado SEM a irmã (📊 ca755794) continua disparando",
      f"disparou {CP.detect_handoff_trigger(PB, TELA_NUMERADA_SEM_IRMA)!r}")

print()
print("=" * 74)
print("[4b] 🔴 juiz P3: 'você tem um serviço aberto' — nunca abrir DUPLICADO")
print("=" * 74)
# 📊 observed_events: UMA ocorrência (193c5ad6+1, 09/06/2026), texto do acervo.
ABERTO = ("Segurado(a), você tem um serviço aberto 👇" + Q + Q +
          "1-{NUMERO}-GUINCHO PESADO, previsto para {DATA}, às 15h56" + Q + Q +
          "Você quer falar sobre ele?" + Q + "Botão 1: Sim" + Q + "Botão 2: Não")
s, r = responder(na_ura("guincho", servico_texto="Guincho (reboque)"), ABERTO)
certo(r is None and s.get("state") == "needs_human",
      "guincho pedido + GUINCHO aberto → uma pessoa (pode ser o MESMO: nunca duplicar)",
      f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")
s, r = responder(na_ura("bateria", servico_texto="Bateria"), ABERTO)
certo(r == "Não" and s.get("state") != "needs_human",
      "bateria pedida + GUINCHO aberto → 'Não' (abre o que o cliente pediu HOJE)",
      f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")
ILEGIVEL = ABERTO.replace("GUINCHO PESADO", "SERVIÇO")
s, r = responder(na_ura("bateria", servico_texto="Bateria"), ILEGIVEL)
certo(r is None and s.get("state") == "needs_human",
      "🔴 CONTROLE: tipo do serviço aberto ilegível → uma pessoa (nunca chute)",
      f"respondeu {r!r} · state={s.get('state')!r}")
RECLAMACAO = Q.join(["Certo. Sobre o que você quer falar?", "Informações do serviço",
                     "Serviço não realizado", "Problema no atendimento", "Elogio ou sugestão",
                     "Não encontrei o assunto", "Voltar"])
s, r = responder(na_ura("guincho"), RECLAMACAO)
certo(r is None and s.get("state") == "needs_human",
      "o menu de ACOMPANHAMENTO/reclamação do serviço aberto → uma pessoa",
      f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")
DICA = ("Antes de continuar, uma dica 👇" + Q + Q + "Ao solicitar algum serviço, é necessário "
        "confirmar as informações da apólice que será acionada.")
s, r = responder(na_ura("guincho"), DICA)
certo(r is None and s.get("state") not in ("needs_human",), "a 'dica' é aviso: nada se responde",
      f"respondeu {r!r} · state={s.get('state')!r}")
EXPLIQUE = "Certo! Me explique em poucas palavras o que você precisa." + Q + Q + "Por exemplo: *agendar um guincho*."
s, r = responder(na_ura("bateria"), EXPLIQUE)
certo(r == CASO["problema_descricao"], "'me explique em poucas palavras' → o relato do CASO",
      f"respondeu {r!r} · state={s.get('state')!r}")

print()
print("=" * 74)
print("[5] 🔴 D11: a consultora da Porto assume → uma pessoa da corretora, com motivo")
print("=" * 74)
s, r = responder(sessao("bateria"), TELA_CONSULTORA)
certo(r is None and s.get("state") == "needs_human"
      and str(s.get("reason") or "").startswith("consultora_da_seguradora:"),
      "a apresentação da consultora passa o caso, com o motivo próprio",
      f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")
frase = IDS.motivo_em_portugues(s.get("reason") or "")
certo("consultora" in frase and "_" not in frase,
      "o motivo chega em português à atendente", f"frase={frase!r}")
s, r = responder(sessao("bateria"), TELA_PERSONALIZADO_AVISO)
certo(s.get("state") != "needs_human" and r is None,
      "🔴 CONTROLE: 'seu consultor de relacionamento atende de segunda a sexta' NÃO é a consultora "
      "(f4838bb3 seguiu no robô até o protocolo)",
      f"respondeu {r!r} · state={s.get('state')!r} reason={s.get('reason')!r}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
