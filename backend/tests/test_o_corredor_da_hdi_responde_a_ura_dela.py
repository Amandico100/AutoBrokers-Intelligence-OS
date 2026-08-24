# -*- coding: utf-8 -*-
"""🔴 AS TELAS DA HDI QUE O CORREDOR NÃO CONHECIA — SPEC-084.1, ONDA C.

📊 23/08/2026, medido nas cinco rotas de `hdi × auto`. Sete telas reais eram
**órfãs funcionais** — a URA perguntava e o corredor não tinha resposta:

```
guincho    "mais de um veículo para esta apólice"  1..18, PLACAS
guincho    "E para onde devemos te levar?"          o táxi depois do guincho
guincho    "Para quantos passageiros?"
guincho    "Possui bagagens?"
guincho    "Agora que você já sabe desta informação..."
chaveiro   "Deseja continuar o seu atendimento para a placa X?"
socorro    "Botão 1: Acompanhar andamento  Botão 2: Cancelar serviço"
```

🔴 **Duas delas são perigosas de responder errado, e por motivos opostos:**

- a de MAIS DE UM VEÍCULO tem até dezoito opções, todas placas. Responder "1"
  pega o carro de outra pessoa da mesma apólice — é o defeito que o teste
  Allianz de 12/07 já pegou uma vez;
- a da PLACA LEMBRADA abre a conversa oferecendo o veículo do **atendimento
  anterior**. O WhatsApp é o da CORRETORA, então esse veículo pode ser de outro
  segurado dela. Aceitar abre assistência na apólice errada.

⚠️ E duas **não têm resposta honesta**: o endereço para onde o táxi leva a
pessoa e quantas pessoas vão nele. São a mesma família das quatro perguntas da
decisão 2 do Founder — *"o default É o erro"* — e por isso vão a `sem_chute`,
que é `needs_human` com o motivo escrito, nunca palpite.

🔴 Este arquivo chama o MOTOR (§9.4). As telas são copiadas do corpus
versionado de `hdi-auto`, palavra por palavra.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# ⚠️ Import POR CAMINHO: `app.services.__init__` puxa `fastembed`, que não
#    existe neste ambiente — e o §9.4 proíbe contornar reimplementando.
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


PB = "hdi-auto-whatsapp@v1"

# ── telas REAIS do corpus `hdi-auto`, copiadas ──────────────────────────────
TELA_MULTI = (
    "Identificamos que há mais de um veículo para esta apólice, por favor, "
    "*digite o número* indicando o veículo para o qual você precisa de "
    "atendimento. Ex: 9\n\n1 - Placa AAA1111\n2 - Placa BBB2222\n"
    "3 - Placa CCC3333\n4 - Nenhuma das opções anteriores")
TELA_PLACA_LEMBRADA = (
    "Olá *Fulano - Corretora X*, seja bem-vindo(a) ao atendimento digital de "
    "*Assistência 24 horas da HDI Seguros!* \n\nDeseja continuar o seu "
    "atendimento para a placa *ZZZ9999*? \n\nPor favor, selecione abaixo, a "
    "opção de sua preferência.")
TELA_CPF = ("Para começar, informe *apenas um dos dados abaixo:* - CPF ou CNPJ "
            "do segurado - Placa do veículo")
TELA_PASSAGEIROS = "Para quantos passageiros?"
TELA_BAGAGENS = "Possui bagagens?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar"
TELA_CANCELAR = ("Por favor, selecione abaixo a opção de sua preferência:\n"
                 "Botão 1: Acompanhar andamento\nBotão 2: Cancelar serviço\n"
                 "Botão 3: Voltar")
TELA_TRANSPORTE = (
    "Você tem cobertura para *meio de transporte emergencial para retornar à "
    "sua residência ou continuar a viagem*. Lembrando que não é permitido o "
    "segurado seguir viagem dentro do guincho.\n\nSabendo disso, deseja "
    "solicitar o serviço de meio de transporte?\nBotão 1: Sim\nBotão 2: Não")
TELA_ROTA_CHAVEIRO = (
    "O que aconteceu com a chave?\nDentro do veículo\nChave está trancada "
    "dentro do veículo\nPerda\nPerdeu a chave\nQuebrou\nA chave quebrou")

CASO = {
    # 🔴 ATUALIZADO — SPEC-084.2 C4: o registro do SEGUNDO formulário nativo fez
    #    `hdi/auto/chaveiro` passar a bater nele, e o formulário exige
    #    `local_situacao`. Sem o slot, a rota trava — que é exatamente o
    #    defeito que o C4 tornou visível. A fixture segue o produto.
    "local_situacao": "Local Seguro",
    "titular_cpf": "11122233344", "veiculo_placa": "BBB2222",
    "titular_nome": "Cliente", "local_atual": "Rua X, 100, Florianópolis, SC",
    "local_destino": "Oficina Y, São José, SC",
    "problema_descricao": "o carro não anda, preciso de guincho",
    "quando": "agora", "telefone_contato": "48999998888",
    "pessoa_no_local": "Cliente",
}


def sessao(subservico="guincho", **extra):
    slots = dict(CASO)
    slots.update(extra)
    return IDS.new_dispatch_session(case_id="hdi-t", company_id="co",
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
print("[1] 🔴 MAIS DE UM VEÍCULO: a escolha é pela PLACA, nunca pela posição")
print("=" * 74)

s = IDS.start_dispatch(sessao())
s, r = responder(s, TELA_MULTI)
certo(r == "2", "🔴 hdi/auto/guincho: escolhe a opção da placa BBB2222 — a "
      "SEGUNDA da lista", f"respondeu {r!r}")

# 🔴 CONTROLE: outra placa, outra tecla. Sem esta metade, um "2" fixo passaria.
s2 = IDS.start_dispatch(sessao(veiculo_placa="CCC3333"))
s2, r2 = responder(s2, TELA_MULTI)
certo(r2 == "3", "🔴 CONTROLE: com a placa CCC3333 a resposta MUDA para 3 — "
      "não é constante disfarçada", f"respondeu {r2!r}")

print()
print("=" * 74)
print("[2] 🔴 A PLACA LEMBRADA é do atendimento ANTERIOR — re-identificar")
print("=" * 74)

s3 = IDS.start_dispatch(sessao("chaveiro"))
s3, r3 = responder(s3, TELA_PLACA_LEMBRADA)
certo(r3 == "Não", "🔴 hdi/auto/chaveiro: a primeira vez RECUSA a placa "
      "lembrada — ela pode ser de outro segurado da mesma corretora",
      f"respondeu {r3!r}")

# 🔴 CONTROLE: depois que o NOSSO CPF foi enviado, o cliente exibido é o nosso
#    e a mesma tela passa a ser respondida com "Sim". Se este lado falhasse, o
#    corredor ficaria preso recusando a própria identificação.
s3, _ = responder(s3, TELA_CPF)
s3, r3b = responder(s3, TELA_PLACA_LEMBRADA)
certo(r3b == "Sim", "🔴 CONTROLE: depois do nosso CPF, a MESMA tela vira Sim",
      f"respondeu {r3b!r}")

print()
print("=" * 74)
print("[3] 🔴 `sem_chute`: quantos passageiros NÃO se chuta")
print("=" * 74)

s4 = IDS.start_dispatch(sessao())
s4, r4 = responder(s4, TELA_PASSAGEIROS)
certo(s4.get("state") == "needs_human"
      and str(s4.get("reason") or "").startswith("sem_chute:"),
      "🔴 sem o dado no caso, o passo CHAMA GENTE — e o motivo fica escrito",
      f"state={s4.get('state')!r} reason={s4.get('reason')!r} resposta={r4!r}")
certo(r4 is None, "🔴 e NÃO responde nada à URA — chutar aqui deixa gente na "
      "estrada", f"respondeu {r4!r}")

# 🔴 CONTROLE: com o dado no caso, o MESMO passo responde. Sem esta metade, um
#    `needs_human` incondicional passaria igual.
s5 = IDS.start_dispatch(sessao(taxi_passageiros="3"))
s5, r5 = responder(s5, TELA_PASSAGEIROS)
certo(r5 == "3" and s5.get("state") != "needs_human",
      "🔴 CONTROLE: com `taxi_passageiros` no caso, o mesmo passo RESPONDE",
      f"respondeu {r5!r}, state={s5.get('state')!r}")

print()
print("=" * 74)
print("[4] 🔴 CANCELAR é decisão de gente")
print("=" * 74)

s6 = IDS.start_dispatch(sessao("socorro_mecanico"))
s6, r6 = responder(s6, TELA_CANCELAR)
certo(s6.get("state") == "needs_human"
      and "handoff" in str(s6.get("reason") or ""),
      "🔴 hdi/auto/socorro_mecanico: o menu Acompanhar/Cancelar vira HANDOFF",
      f"state={s6.get('state')!r} reason={s6.get('reason')!r}")

# 🔴 CONTROLE, e ele é o que impede o gatilho largo: a MESMA palavra
#    "cancelar" aparece no link de acompanhamento, e ali NÃO pode disparar.
#    📊 `cancelar servi[çc]o` solto casa 40 telas em 23 rotas.
LINK = ("Você pode acompanhar a chegada do nosso parceiro pelo link "
        "https://www.acompanha.net/abc caso deseje alterar ou cancelar o "
        "serviço acesse o mesmo link")
certo(CP.detect_handoff_trigger(CP.get_playbook(PB), LINK) is None,
      "🔴 CONTROLE: a palavra `cancelar` no LINK de acompanhamento NÃO "
      "dispara handoff — o gatilho é o par de botões, não a palavra",
      str(CP.detect_handoff_trigger(CP.get_playbook(PB), LINK)))

print()
print("=" * 74)
print("[5] O TÁXI DEPOIS DO GUINCHO — e ele não se abre sozinho")
print("=" * 74)

s7 = IDS.start_dispatch(sessao())
s7, r7 = responder(s7, TELA_TRANSPORTE)
certo(r7 == "Não",
      "🔴 quem não pediu carona não recebe um segundo serviço aberto no nome "
      "dele — o default é NÃO", f"respondeu {r7!r}")

# 🔴 CONTROLE: quem PEDIU recebe. O default não é uma recusa cega.
s8 = IDS.start_dispatch(sessao(
    problema_descricao="o carro quebrou e eu preciso de um táxi para voltar "
                       "para casa"))
s8, r8 = responder(s8, TELA_TRANSPORTE)
certo(r8 == "Sim", "🔴 CONTROLE: quem PEDIU carona no relato recebe Sim",
      f"respondeu {r8!r}")

s9 = IDS.start_dispatch(sessao())
s9, r9 = responder(s9, TELA_BAGAGENS)
certo(r9 == "Sim", "🔴 bagagens: Sim, porque o erro não é simétrico — carro "
      "que cabe mala atende quem não tem", f"respondeu {r9!r}")

print()
print("=" * 74)
print("[6] E o corredor da HDI continua respondendo o que já respondia")
print("=" * 74)

# 🔴 CONTROLE de não-regressão: uma tela conhecida ANTES desta onda.
s10 = IDS.start_dispatch(sessao("chaveiro",
                                problema_descricao="tranquei a chave dentro do carro"))
s10, r10 = responder(s10, TELA_ROTA_CHAVEIRO)
certo(r10 is not None,
      "🔴 CONTROLE: a tela do 'o que aconteceu com a chave' continua "
      "respondida — as telas novas não empurraram as antigas",
      f"respondeu {r10!r}")

print()
print("=" * 74)
print("[7] CADA ROTA DA HDI, NAS TELAS DELA — pneu, chaveiro e socorro")
print("=" * 74)

# 🔴 Uma rota só está coberta se o teste tocar as telas DELA. As de baixo são
#    copiadas do corpus de cada sessão, e o motor responde a cada uma.
PNEU = [
    ("Certo! Quantos pneus foram furados/danificados?@Botão 1: Apenas um "
     "pneu@Botão 2: Mais de um pneu@Botão 3: Voltar", True),
    ("Você possui um estepe?@Botão 1: Em condições@Botão 2: Sem "
     "condições@Botão 3: Não", True),
    ("Possui chave de roda e macaco em boas condições?@Botão 1: Sim@"
     "Botão 2: Não@Botão 3: Voltar", True),
    ("Você está em um lugar seguro?@Botão 1: Sim@Botão 2: Não@"
     "Botão 3: Voltar", True),
    # ⚠️ ESTA é AVISO, não pergunta: é a EXCLUSÃO de rodovia. Responder seria
    #    falar por cima da regra que o segurado precisa ouvir.
    ("*Lembrando*: Por questões de segurança não conseguimos enviar o serviço "
     "de troca de pneus para Rodovias e Marginais", False),
]
for tela, espera_resposta in PNEU:
    tela = tela.replace("@", "\n")
    # ⚠️ Os slots do galho de pneu vem do CASO. Sem eles o passo existe e casa,
    #    mas quem responde e o cerebro (`fallback_adaptive`) -- que nao roda
    #    aqui. O que este teste guarda e que o corredor SABE a tela e responde
    #    o que o caso diz; o caminho do cerebro tem guarda propria.
    sp = IDS.start_dispatch(sessao(
        "pneu", problema_descricao="furei o pneu",
        pneus_quantidade_opcao="Apenas um pneu", estepe_situacao="Em condições",
        ferramentas_no_veiculo="Sim", local_seguro="Sim"))
    sp, rp = responder(sp, tela)
    certo((rp is not None) == espera_resposta,
          ("🔴 hdi/auto/pneu responde: " if espera_resposta
           else "🔴 hdi/auto/pneu fica CALADO (é aviso): ")
          + " ".join(tela.split())[:52],
          f"respondeu {rp!r}")

CHAVEIRO = [
    "Para continuar, precisamos entender onde o veículo está parado. Essa "
    "informação é importante para sua segurança e para definirmos o tipo de "
    "atendimento.",
    "Fulano - Corretora X, agora preciso saber se o veículo está em uma "
    "rodovia?@@Por favor, responda selecionando uma das opções abaixo.@"
    "Botão 1: Sim@Botão 2: Não@Botão 3: Voltar",
]
for tela in CHAVEIRO:
    tela = tela.replace("@", "\n")
    sc = IDS.start_dispatch(sessao(
        "chaveiro", problema_descricao="tranquei a chave dentro do carro"))
    sc, rc = responder(sc, tela)
    # 🔴 ATUALIZADO na rodada dos juízes — SPEC-084.2, CLAUDE.md §9.3.
    #
    #    Depois do C4, uma destas telas é o SEGUNDO formulário nativo. O
    #    corredor a reconhece e MONTA a resposta — e para em
    #    `formulario_pronto_sem_flow_token`, porque 📊 o `flow_token` nunca
    #    chega: o botão da HDI/Yelum se chama `galaxy_message` e o parser não o
    #    reconhece (P-084-67, declarada e medida em 0 de 28.096 eventos).
    #
    # ⚠️ *"O corredor não soube responder"* e *"o corredor respondeu e o canal
    #    não levou"* são coisas OPOSTAS, e o guarda tem de distinguir: a
    #    primeira é defeito de corredor; a segunda é limite externo declarado.
    _resposta_pronta = str(sc.get("reason") or "").startswith(
        "formulario_pronto_")
    certo(sc.get("state") != "needs_human" or rc is not None
          or _resposta_pronta,
          "🔴 hdi/auto/chaveiro não trava em: " + " ".join(tela.split())[:48],
          f"state={sc.get('state')!r} reason={sc.get('reason')!r}")

TELA_PANE = (
    "Por favor, selecione a opção que condiz com a pane do veículo@"
    "Problemas elétricos@Selecione essa opção se está com problema nos "
    "fusíveis, reles, etc.@Luzes do painel@Vazamento@Superaquecimento@"
    "Problemas no motor").replace("@", "\n")
ss = IDS.start_dispatch(sessao(
    "socorro_mecanico",
    problema_descricao="o painel acendeu e acho que é problema elétrico"))
ss, rs = responder(ss, TELA_PANE)
certo(rs == "Problemas elétricos",
      "🔴 hdi/auto/socorro_mecanico: a pane vem do RELATO — e foi essa tecla "
      "que trouxe um MECÂNICO em vez de um guincho na sessão 71caf82f",
      f"respondeu {rs!r}")

# 🔴 CONTROLE: outro relato, outra tecla. Uma constante passaria no de cima.
ss2 = IDS.start_dispatch(sessao(
    "socorro_mecanico",
    problema_descricao="o carro está superaquecendo, saindo fumaça do capô"))
ss2, rs2 = responder(ss2, TELA_PANE)
certo(bool(rs2) and rs2 != rs,
      "🔴 CONTROLE: relato de superaquecimento dá tecla DIFERENTE",
      f"respondeu {rs2!r}, e o outro relato deu {rs!r}")

TELA_AVISO_BATERIA = (
    "Neste caso, enviaremos um prestador para realizar a *recarga da sua "
    "bateria*, permitindo assim, que o veículo siga viagem. Mas não se esqueça "
    "de buscar uma assistência especializada para avaliação e reparos "
    "definitivos.@@*Atenção:* Caso seja necessário a compra de uma nova "
    "bateria, o segurado será responsável pela negociação diretamente com o "
    "prestador de serviços.").replace("@", "\n")
ss3 = IDS.start_dispatch(sessao("socorro_mecanico"))
ss3, rs3 = responder(ss3, TELA_AVISO_BATERIA)
certo(rs3 is None,
      "🔴 o aviso da BATERIA NOVA é regra de DINHEIRO, e o corredor fica "
      "calado nele — quem tem de ouvir isso é o segurado, não a URA",
      f"respondeu {rs3!r}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
