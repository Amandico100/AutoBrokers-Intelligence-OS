# -*- coding: utf-8 -*-
"""Os quatro furos da rota validada — e todos contra o TEXTO REAL do acervo.

POR QUE ESTE ARQUIVO EXISTE
===========================
📊 Em 19/08/2026 o acionamento de maquina de lavar da Allianz residencial foi
ao ar com cliente real e chegou ao protocolo 52955490 em 5min55. Virou a regua
do produto.

A auditoria de 21/08 achou QUATRO furos dentro dessa mesma regua. Nenhum tinha
derrubado o atendimento — todos tinham sido cobertos por cima, pelo cerebro ou
pela atendente. Furo coberto e furo que ninguem ve.

🔴 A LICAO QUE ESTE ARQUIVO CARREGA
===================================
O teste da rota (`test_a_maquina_de_lavar_vai_ate_o_fim.py`, 72 assercoes
verdes) NAO pegou o furo do agendamento. Ele passava porque tem um helper
proprio que roda `re.search` DIRETO na ancora, sem passar pelo motor.

    **Teste de corredor tem de chamar o MOTOR.
      Teste que chama o regex nao guarda nada — guarda o regex.**

Aqui toda assercao passa por `match_ura_step`, `extract_capture_anchors` ou
`detect_finalize_anchor`. E todo texto de tela e copiado do banco, nao inventado.

OS QUATRO FUROS
===============
1. `numero_residencia` exigia "informe o numero da residencia" — 📊 frase com
   ZERO ocorrencias em 28.092 eventos. A URA escreve "me CONFIRME": 180
   mensagens, 72 sessoes, a mais recente e a propria sessao da regua.
2. O freio de finalizacao do residencial nao tinha `dados a seguir estao
   corretos` — 📊 154 mensagens / 64 sessoes passando pela conferencia sem freio.
   O `allianz-auto` tem essa ancora desde sempre.
3. `schedule_agendado` era declarado e o motor NUNCA o lia. 📊 A Clarissa
   recebeu "Sua assistencia foi aberta" sem data e sem periodo.
4. `\*dica:\*` exigia asterisco literal num texto que `_norm` ja limpou —
   ancora morta que deixava um gate VERMELHO em producao.
"""
from __future__ import annotations

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.services", "app.core"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

import importlib  # noqa: E402

CP = importlib.import_module("app.services.corridor_playbooks")

OK = 0
FAIL = 0


def certo(condicao, rotulo, detalhe=""):
    global OK, FAIL
    if condicao:
        OK += 1
        print(f"  ok   {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


PB = CP._PLAYBOOKS["allianz-residencial-whatsapp@v1"]

# ===========================================================================
# TEXTO REAL, COPIADO DO BANCO. Nenhuma linha aqui foi escrita por mim.
# Query: select text from observed_events where insurer_key='allianz' …
# ===========================================================================
TELA_NUMERO_HOJE = "Agora, me confirme o número da residência."          # 180x / 72 sessões
TELA_NUMERO_ANTIGA = "Por favor, informe o número da residência"          # a redação anterior
TELA_CONFERENCIA = ("Antes de prosseguirmos, poderia me confirmar se os dados "
                    "a seguir estão corretos, por gentileza?")            # 154x / 64 sessões
TELA_AGENDAMENTO = ("Agendamento para: *Quinta-feira 20/08/2026*, *período da "
                    "tarde das 13:00 às 18:00* Podemos continuar ? *1 -* Sim "
                    "*2 -* Não, quero remarcar")                          # 19/08 16:39:07
TELA_AGENDAMENTO_2 = ("Agendamento para: *Terça-feira 03/03/2026*, *período da "
                      "tarde das 13:00 às 18:00* Podemos continuar ?")
TELA_QUANDO = ("*Quando:* Quarta-feira, 31/12/2025  *Periodo:* manha das "
               "09:00 as 13:00  ")
TELA_PROTOCOLO = "O número de protocolo é *52955490*"                     # 19/08 16:41:22
TELA_SENHA = "Sua senha será os 4 últimos dígitos desse telefone *4743*"  # 19/08 16:41:24
TELA_MENU = "Qual o serviço que você precisa?"
TELA_CONFIRMA = "Podemos confirmar o atendimento?"

print()
print("=" * 74)
print("  1. A ÂNCORA QUE NUNCA CASOU — e a antiga continua casando")
print("=" * 74)

p_hoje = CP.match_ura_step(PB, TELA_NUMERO_HOJE, subservice="maquina_de_lavar")
certo(p_hoje is not None and p_hoje.get("step") == "numero_residencia",
      "🔴 'me CONFIRME o número da residência' casa o passo",
      f"casou: {(p_hoje or {}).get('step')}")

p_antiga = CP.match_ura_step(PB, TELA_NUMERO_ANTIGA, subservice="maquina_de_lavar")
certo(p_antiga is not None and p_antiga.get("step") == "numero_residencia",
      "🔴 CONTROLE: e a redação ANTIGA ('informe') NÃO parou de casar",
      "ampliar âncora é seguro; TROCAR é o que quebra sem ninguém ver")

# CONTROLE DO CONTROLE: o passo não virou um casa-tudo.
certo(CP.match_ura_step(PB, "Qual é o número do seu CPF?",
                        subservice="maquina_de_lavar") is not p_hoje
      or CP.match_ura_step(PB, "Qual é o número do seu CPF?",
                           subservice="maquina_de_lavar") is None
      or (CP.match_ura_step(PB, "Qual é o número do seu CPF?",
                            subservice="maquina_de_lavar") or {}).get("step")
      != "numero_residencia",
      "CONTROLE: e ela não virou um casa-tudo (outra tela com 'número' não casa)")

print()
print("=" * 74)
print("  2. O FREIO DA CONFERÊNCIA — 64 sessões passavam sem ele")
print("=" * 74)

certo(bool(CP.detect_finalize_anchor(PB, TELA_CONFERENCIA)),
      "🔴 'dados a seguir estão corretos' ARMA o freio no residencial",
      "é a âncora que o allianz-auto tem desde sempre e o residencial não tinha")
certo(bool(CP.detect_finalize_anchor(PB, TELA_CONFIRMA)),
      "CONTROLE: e a âncora que já existia continua armando")
certo(not CP.detect_finalize_anchor(PB, TELA_MENU),
      "🔴 CONTROLE: e um MENU comum NÃO arma o freio",
      "se armasse em tudo, o corredor pararia em toda tela e o teste acima "
      "não mediria nada")

# As duas famílias da mesma seguradora não podem divergir de novo.
AUTO = CP._PLAYBOOKS["allianz-auto-whatsapp@v1"]
so_no_auto = [a for a in (AUTO.get("finalize_anchors") or [])
              if a not in (PB.get("finalize_anchors") or [])]
certo(not [a for a in so_no_auto if "dados a seguir" in a],
      "e a âncora não é mais exclusiva do auto",
      f"ainda só no auto: {so_no_auto}")

print()
print("=" * 74)
print("  3. O AGENDAMENTO CHEGA AO CLIENTE — pelo MOTOR, não pelo regex")
print("=" * 74)

cap = CP.extract_capture_anchors(PB, TELA_AGENDAMENTO)
certo("schedule" in cap,
      "🔴 a tela real de 19/08 16:39 devolve `schedule` pelo MOTOR",
      f"devolveu: {cap}")
certo(cap.get("schedule", {}).get("day", "").startswith("quinta"),
      f"com o DIA ({cap.get('schedule', {}).get('day')!r})")
certo("tarde" in cap.get("schedule", {}).get("periodo", ""),
      f"e o PERÍODO ({cap.get('schedule', {}).get('periodo')!r})")

for rotulo, tela in (("2ª redação", TELA_AGENDAMENTO_2), ("3ª redação", TELA_QUANDO)):
    certo("schedule" in CP.extract_capture_anchors(PB, tela),
          f"e a {rotulo} do acervo também",
          f"devolveu: {CP.extract_capture_anchors(PB, tela)}")

# CONTROLE: o motor não inventa agendamento onde não há.
certo("schedule" not in CP.extract_capture_anchors(PB, TELA_MENU),
      "🔴 CONTROLE: tela sem agendamento NÃO produz `schedule`",
      "sem isto, um extrator que devolvesse sempre passaria em tudo acima")

# CONTROLE: o que já funcionava continua.
certo(CP.extract_capture_anchors(PB, TELA_PROTOCOLO).get("protocol") == "52955490",
      "CONTROLE: o protocolo continua sendo capturado")
certo(CP.extract_capture_anchors(PB, TELA_SENHA).get("password") == "4743",
      "CONTROLE: e a senha também")

# 🔴 A prova de que o defeito era REAL: antes, o motor devolvia {} para a tela
# de 19/08. Se alguém remover a leitura de `schedule_agendado`, esta linha cai.
certo(len(cap) >= 1 and cap.get("schedule"),
      "🔴 e é o MOTOR que devolve — não um `re.search` do teste",
      "foi exatamente esse o ponto cego que deixou 72 asserções verdes "
      "sobre um agendamento que nunca chegava ao cliente")

print()
print("=" * 74)
print("  4. NENHUMA ÂNCORA EXIGE ASTERISCO — `_norm` já o removeu")
print("=" * 74)

import re as _re  # noqa: E402

exigem = []
for ref, pb in sorted(CP._PLAYBOOKS.items()):
    for passo in pb.get("ura_steps") or []:
        a = str(passo.get("anchor") or "")
        # `\*` sem `?` logo depois = asterisco OBRIGATÓRIO
        if _re.search(r"\\\*(?!\?)", a):
            exigem.append((ref, passo.get("step")))

certo(not exigem,
      "🔴 nenhuma âncora exige `*` literal — `_norm` o remove antes de comparar",
      f"exigiriam: {exigem[:4]}")

# CONTROLE: o detector CONSEGUE achar. Sem isto, ele poderia estar cego.
certo(bool(_re.search(r"\\\*(?!\?)", r"vale lembrar|\*dica:\*|fim")),
      "CONTROLE: o detector acha um `\\*` obrigatório quando existe")
certo(not _re.search(r"\\\*(?!\?)", r"informe \*?o n[úu]mero"),
      "CONTROLE: e NÃO acusa o `\\*?` opcional, que é o jeito certo")

print()
print("=" * 74)
print("  5. O CAMINHO INTEIRO DA RÉGUA CONTINUA DE PÉ")
print("=" * 74)

# As telas do acionamento validado, na ordem, pelo motor.
CAMINHO = [
    ("Informe o tipo de serviço", "menu_tipo_servico"),
    ("Qual eletrodoméstico precisa de conserto", "menu_categoria_eletrodomestico"),
    ("Selecione o eletrodoméstico que precisa de conserto", "menu_aparelho"),
    ("Qual a marca ?", "aparelho_marca"),
    ("E o modelo completo?", "aparelho_modelo"),
    ("Escolha qual data deseja agendar", "escolher_data_agendamento"),
]
for tela, esperado in CAMINHO:
    p = CP.match_ura_step(PB, tela, subservice="maquina_de_lavar")
    certo(p is not None and p.get("step") == esperado,
          f"{esperado}", f"casou: {(p or {}).get('step')}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
