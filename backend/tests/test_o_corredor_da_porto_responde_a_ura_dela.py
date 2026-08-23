# -*- coding: utf-8 -*-
"""🔴 AS TELAS DA PORTO QUE O CORREDOR NÃO CONHECIA — SPEC-084.1, ONDA E.

📊 23/08/2026, medido nas cinco rotas de `porto × auto` com corpus. Onze telas
reais eram **órfãs funcionais**, e três delas decidem coisas caras:

```
bateria   "precisamos agendar a visita técnica de um prestador da Porto"
bateria   "Você quer seguir com o agendamento?"        Não = CANCELA tudo
bateria   "a solicitação de agendamento foi encerrada e a solicitação cancelada"
chaveiro  "E de qual serviço de chaveiro você precisa?"
chaveiro  "Caso você tenha uma chave reserva guardada em outro local..."
guincho   "Valmor, como eu posso te ajudar? 1 - JEEP, placa ... 2 - Outro"
guincho   o TÁXI encadeado: passageiros · mesmo endereço · para onde
tecnico   agendamento em três telas: data · período · faixa de horário
tecnico   "Entendi. O que você precisa? Recarga / Bateria nova / Troca"
```

🔴 **O padrão que a Porto revela, e que nenhuma outra revelou: o ESCOPO por
subserviço não acompanha o ENCADEAMENTO da URA.** O táxi é oferecido DEPOIS do
guincho, dentro da mesma sessão; o submenu de bateria leva a um agendamento de
TÉCNICO, e o resumo sai com *Serviço: Técnico*. Passos escopados só no nome do
subserviço ficavam órfãos na rota por onde a tela realmente chega.

⚠️ E uma resposta certa saiu na forma errada, pega pelo conferidor antes de
qualquer medição: o rótulo da lista é *"Abrir porta do veículo"*, e a descrição
*"ou porta mala, combustível ou baú"* é outra linha. Responder as duas juntas é
responder uma opção que não existe.

🔴 Este arquivo chama o MOTOR (§9.4). As telas são copiadas do corpus
versionado de `porto-auto`, palavra por palavra.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import importlib.util as _ilu  # noqa: E402


def _mod(nome, arquivo):
    sp = _ilu.spec_from_file_location(
        nome, os.path.join(RAIZ, "app", "services", arquivo))
    m = _ilu.module_from_spec(sp)
    sys.modules[nome] = m
    sp.loader.exec_module(m)
    return m


CP = _mod("app.services.corridor_playbooks", "corridor_playbooks.py")
IDS = _mod("app.services.insurer_dispatch_service", "insurer_dispatch_service.py")

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


PB = "porto-auto-whatsapp@v1"
Q = chr(10)

TELA_VISITA = ("Para solicitar a nova bateria, precisamos agendar a *visita "
               "técnica de um prestador da Porto*, que irá indicar a bateria "
               "mais adequada pro seu veículo.")
TELA_SEGUIR = ("Você quer seguir com o agendamento?" + Q + "Botão 1: Sim" + Q +
               "Botão 2: Não" + Q + "Botão 3: Voltar")
TELA_CANCELADA = ("Certo, Alvaro. A solicitação de agendamento foi encerrada "
                  "e a solicitação cancelada.")
TELA_CHAVEIRO_TIPO = ("Certo! E de qual serviço de chaveiro você precisa?" + Q +
                      "Abrir porta do veículo" + Q +
                      "ou porta mala, combustível ou baú" + Q +
                      "Não encontrei o assunto" + Q + "Voltar")
TELA_CHAVE_RESERVA = ("Tudo bem. Caso você tenha uma chave reserva guardada em "
                      "outro local, posso pedir para um prestador buscar e "
                      "levar até você. Gostaria desse serviço?" + Q +
                      "Botão 1: Sim" + Q + "Botão 2: Não" + Q + "Botão 3: Voltar")
TELA_MENU_VEIC = ("Valmor, como eu posso te ajudar?" + Q +
                  "*1* - JEEP, ano 2025, placa TB#-##44" + Q +
                  "*2* - FIAT, ano 2019, placa QQ#-##11" + Q +
                  "*3* - Outro veículo" + Q + "*4* - Mais assuntos")
TELA_TAXI_MESMO = ("O táxi deve ir para o mesmo endereço informado para o "
                   "guincho?" + Q + "Botão 1: Sim" + Q + "Botão 2: Não")
TELA_TAXI_SABE = ("Você já sabe aonde o Táxi deverá te levar?" + Q +
                  "Botão 1: Sim" + Q + "Botão 2: Não")
TELA_AGENDA_DATA = ("Por favor, informe para quando você quer agendar o "
                    "serviço. Siga o formato abaixo 👇 *dd/mm/aaaa* ou "
                    "*ddmmaaaa*")
TELA_AGENDA_PERIODO = ("Qual período você prefere?" + Q + "*1* - Manhã" + Q +
                       "*2* - Tarde" + Q + "*3* - Noite" + Q + "*4* - Voltar")
TELA_AGENDA_HORA = ("E qual horário?" + Q + "Entre 12h00 e 12h30" + Q +
                    "Entre 12h30 e 13h00" + Q + "Entre 13h00 e 13h30")
TELA_SUBMENU_BAT = ("Entendi. O que você precisa?" + Q + "Recarga de bateria" +
                    Q + "Bateria nova" + Q + "Troca de bateria" + Q +
                    "Na garantia" + Q + "Voltar")
TELA_IMPORTANTE = ("*Importante* - É necessário ter alguém maior de 18 anos "
                   "para acompanhar o serviço. - Se ninguém for encontrado, o "
                   "prestador aguardará por *até 15 minutos* no local.")

CASO = {
    "titular_cpf": "11122233344", "veiculo_placa": "QQQ1111",
    "titular_nome": "Cliente", "local_atual": "Rua X, 100, Florianópolis, SC",
    "local_destino": "Oficina Y, São José, SC",
    "problema_descricao": "o carro não anda", "quando": "agora",
    "telefone_contato": "48999998888", "pessoa_no_local": "Cliente",
}


def sessao(subservico, **extra):
    slots = dict(CASO)
    slots.update(extra)
    return IDS.new_dispatch_session(case_id="pt-t", company_id="co",
                                    playbook_ref=PB, subservice=subservico,
                                    slots=slots)


def responder(s, tela):
    antes = len([t for t in s.get("transcript") or []
                 if t.get("direction") == "out"])
    s = IDS.handle_insurer_message(s, tela)
    saidas = [t.get("text") for t in s.get("transcript") or []
              if t.get("direction") == "out"]
    return s, (saidas[antes:] or [None])[-1]


print("=" * 74)
print("[1] 🔴 BATERIA NOVA na Porto é VISITA AGENDADA, não socorro")
print("=" * 74)

s = IDS.start_dispatch(sessao("bateria", bateria_tipo_opcao="Bateria nova"))
s, r = responder(s, TELA_VISITA)
certo(r is None, "🔴 porto/auto/bateria: o aviso da visita técnica é AVISO — "
      "o corredor não responde por cima dele", f"respondeu {r!r}")

s, r = responder(s, TELA_SEGUIR)
certo(r == "Sim", "🔴 e o agendamento SEGUE — `Não` aqui cancela a "
      "solicitação inteira", f"respondeu {r!r}")

print()
print("=" * 74)
print("[2] 🔴 A URA CANCELOU — e isso não pode virar silêncio")
print("=" * 74)

s2 = IDS.start_dispatch(sessao("bateria"))
s2, r2 = responder(s2, TELA_CANCELADA)
certo(s2.get("state") == "needs_human"
      and "handoff" in str(s2.get("reason") or ""),
      "🔴 'a solicitação de agendamento foi encerrada e a solicitação "
      "cancelada' vira HANDOFF — o caso morreu e alguém precisa saber",
      f"state={s2.get('state')!r} reason={s2.get('reason')!r}")

# 🔴 CONTROLE: e a palavra `cancelada` sozinha NÃO derruba um atendimento vivo.
s3 = IDS.start_dispatch(sessao("bateria"))
s3, _ = responder(s3, TELA_IMPORTANTE)
certo(s3.get("state") != "needs_human",
      "🔴 CONTROLE: uma tela de aviso comum NÃO dispara handoff — o gatilho é "
      "a frase do cancelamento, não a palavra", f"state={s3.get('state')!r}")

print()
print("=" * 74)
print("[3] O CHAVEIRO: o rótulo é a PRIMEIRA linha da opção")
print("=" * 74)

s4 = IDS.start_dispatch(sessao("chaveiro",
                               problema_descricao="tranquei a chave dentro"))
s4, r4 = responder(s4, TELA_CHAVEIRO_TIPO)
certo(r4 == "Abrir porta do veículo",
      "🔴 responde o TÍTULO da linha — a descrição ('ou porta mala, "
      "combustível ou baú') é outra linha e a URA rejeitaria as duas juntas",
      f"respondeu {r4!r}")

s4, r4b = responder(s4, TELA_CHAVE_RESERVA)
certo(r4b == "Não",
      "🔴 e recusa TROCAR o serviço pedido por 'buscar sua chave reserva em "
      "outro lugar' — que depende de a chave existir", f"respondeu {r4b!r}")

print()
print("=" * 74)
print("[4] 🔴 A SAUDAÇÃO QUE É MENU DE VEÍCULO — escolhe pela PLACA")
print("=" * 74)

s5 = IDS.start_dispatch(sessao("guincho", veiculo_placa="QQQ1111"))
s5, r5 = responder(s5, TELA_MENU_VEIC)
certo(r5 == "2", "🔴 porto/auto/guincho: a placa QQQ1111 é a SEGUNDA da lista",
      f"respondeu {r5!r}")

# 🔴 CONTROLE: outra placa, outra tecla.
s6 = IDS.start_dispatch(sessao("guincho", veiculo_placa="TBC1244"))
s6, r6 = responder(s6, TELA_MENU_VEIC)
certo(r6 == "1", "🔴 CONTROLE: com a placa TBC1244 a resposta MUDA para 1",
      f"respondeu {r6!r}")

print()
print("=" * 74)
print("[5] 🔴 O TÁXI ENCADEADO acontece DENTRO da sessão de guincho")
print("=" * 74)

s7 = IDS.start_dispatch(sessao("guincho"))
s7, r7 = responder(s7, TELA_TAXI_MESMO)
certo(r7 == "Sim",
      "🔴 a tela do táxi é respondida na rota de GUINCHO — é onde ela "
      "acontece", f"respondeu {r7!r}")
s7, r7b = responder(s7, TELA_TAXI_SABE)
certo(r7b == "Sim", "🔴 e a segunda também", f"respondeu {r7b!r}")

# 🔴 CONTROLE: o escopo não virou peneira — VIDROS não vê tela de táxi.
certo(CP.match_ura_step(CP.get_playbook(PB), TELA_TAXI_MESMO,
                        subservice="vidros") is None,
      "🔴 CONTROLE: a rota de VIDROS continua sem ver a tela do táxi — o "
      "escopo cresceu onde a URA encadeia, não em todo lugar")

print()
print("=" * 74)
print("[6] O TÉCNICO: agendamento em três telas")
print("=" * 74)

for tela, rotulo in ((TELA_AGENDA_DATA, "data (dd/mm/aaaa)"),
                     (TELA_AGENDA_PERIODO, "período (1 Manhã 2 Tarde 3 Noite)"),
                     (TELA_AGENDA_HORA, "faixa de horário")):
    s8 = IDS.start_dispatch(sessao(
        "tecnico", data_agendamento="25/08/2026",
        periodo_agendamento_opcao="2", hora_agendamento="Entre 13h00 e 13h30"))
    s8, r8 = responder(s8, tela)
    certo(r8 is not None, f"🔴 porto/auto/tecnico responde: {rotulo}",
          f"respondeu {r8!r}")

# 🔴 E o submenu de BATERIA alcança a rota TÉCNICO, porque é por ele que ela
#    chega — mas `sem_chute` continua valendo: sem o dado, chama gente.
s9 = IDS.start_dispatch(sessao("tecnico"))
s9, r9 = responder(s9, TELA_SUBMENU_BAT)
certo(s9.get("state") == "needs_human"
      and "sem_chute" in str(s9.get("reason") or ""),
      "🔴 o submenu de bateria alcança `tecnico` — e sem o dado no caso ele "
      "CHAMA GENTE, porque recarga ≠ bateria nova ≠ na garantia",
      f"state={s9.get('state')!r} reason={s9.get('reason')!r}")

# 🔴 CONTROLE: com o dado, o mesmo passo responde.
s10 = IDS.start_dispatch(sessao("tecnico", bateria_tipo_opcao="Bateria nova"))
s10, r10 = responder(s10, TELA_SUBMENU_BAT)
certo(r10 == "Bateria nova",
      "🔴 CONTROLE: com `bateria_tipo_opcao` no caso, o mesmo passo responde",
      f"respondeu {r10!r}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
