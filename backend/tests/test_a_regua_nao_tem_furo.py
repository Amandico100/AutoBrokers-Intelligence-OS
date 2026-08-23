# -*- coding: utf-8 -*-
r"""Os quatro furos da rota validada — e todos contra o TEXTO REAL do acervo.

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
# 🔴 MUTACOES — SPEC-083 §3.6, Bloco C item 7.
#
# A v1 da SPEC dava 3 pontos por um COMENTARIO dizendo que a mutacao ficou
# vermelha. **Comentario nao fica vermelho.**
#
# Cada linha abaixo e um dos quatro furos que este arquivo conserta, escrito ao
# contrario: o texto que RECRIA o furo, e o rotulo da assercao que TEM de cair
# quando ele volta. `medir_rota.py --verificar-mutacoes` aplica, roda, exige o
# vermelho, e restaura POR COPIA (nunca `git checkout` -- ele apaga trabalho nao
# commitado, e `git diff --quiet` nem ve arquivo untracked) conferindo por HASH.
#
# 🔴 Mutacao declarada que NAO produz vermelho vale ZERO e vira linha no
#    relatorio. E a diferenca entre um guarda e um enfeite.
# ===========================================================================
MUTACOES = [
    # FURO 6 (C6) - A TELA DO FORMULARIO NATIVO ERA ORFA INOCUA.
    #
    # 📊 23/08/2026: 5 telas em 2 rotas disparavam `detect_native_flow` e
    #    saiam do denominador. As duas tiravam AAA(106) 102/106 com a tela que
    #    TRAVA o acionamento fora da conta -- a regua PREMIANDO o buraco.
    #
    # A mutacao devolve o replay cego. `hdi/auto/guincho` volta de 82/106 para
    # 102/106, e o guarda tem de cair.
    ("scripts/replay.py",
     "        flow = M.detect_native_flow(pb, texto)",
     "        flow = None  # DESLIGADO PELA MUTACAO",
     "o formulario nativo NAO e uma tela inocua"),

    # (arquivo, texto_de, texto_para, rotulo_da_assercao_que_deve_cair)

    # FURO 20 (C20) - a escolha pela placa nao casava a tela REAL.
    # A mutacao devolve a regex antiga, que exige o digito colado no hifen.
    # 📊 A tela da allianz e a da porto voltam a nao casar, e a funcao devolve
    #    string vazia -- que e como o defeito se escondia.
    ("app/services/corridor_playbooks.py",
     r'            r"\*?(\d+)\*?\s*[-\u2013]\s*[^\n]*?\*?placa\*?\s+\*?([A-Z0-9#\-]+)",',
     r'            r"(\d+)\s*-\s*[^\n]*?placa\s+([A-Z0-9#\-]+)",  # DESLIGADO PELA MUTACAO',
     "🔴 a escolha pela placa casa a tela REAL, com o numero em negrito"),

    # FURO 19 (C19) - o protocolo com PREFIXO morria na mascara.
    # A mutacao tira a tentativa que absorve o pedaco ja presente no texto.
    # 📊 O protocolo da porto volta a virar `1-{NUMERO}` e a captura morre.
    ("scripts/higiene_do_corpus.py",
     "            if sobra and valor.startswith(sobra.group(0)):",
     "            if False:  # DESLIGADO PELA MUTACAO",
     "🔴 o protocolo com prefixo sobrevive a mascara"),

    # FURO 18 (C18) - o arquivo com MAIS TELAS vencia o com CONTROLE.
    # A mutacao devolve a ordem antiga: telas primeiro, controle so no
    # desempate. 📊 `hdi/auto/chaveiro` volta a escolher um arquivo sem
    # nenhuma linha de CONTROLE e perde os 3 pontos.
    ("scripts/rubrica.py",
     "melhor = max(candidatos, key=lambda c: (c[1] >= 3, c[2], c[1]), default=None)",
     "melhor = max(candidatos, key=lambda c: (c[1], c[2]), default=None)  # MUTACAO",
     "🔴 a rota recebe o CONTROLE do guarda que foi escrito para ela"),

    # FURO 17 (C17) - a rota nao tinha ONDE escrever a propria transcricao.
    # A mutacao volta a ler o bloco do SERVICO, que e compartilhado por ate
    # onze seguradoras. 📊 `hdi/auto/guincho` volta a ler a sessao da ALLIANZ
    # e perde os 4 pontos.
    ("scripts/rubrica.py",
     "    bloco = _transcricao_da_rota(rota)",
     "    bloco = _fonte_do_bloco(rota.servico)  # DESLIGADO PELA MUTACAO",
     "🔴 a rota tem endereco proprio para a transcricao"),

    # FURO 16 (C16) - O PASSO COMPARTILHADO ERA APAGADO DO EXAME.
    # A mutacao reinstala exatamente a v3: se o passo aparece em mais de um
    # playbook, a `note` dele e lida como vazia. 📊 `allianz/auto` volta a
    # `com_numero == 0` e o item volta a dar zero por vacuidade.
    ("scripts/rubrica.py",
     '        nota = p.get("notes") or ""',
     '        nota = ("" if sum(1 for _b in M.CP._PLAYBOOKS.values()'
     '             for _q in (_b.get("ura_steps") or [])'
     '             if _q.get("step") == p.get("step")) > 1'
     '             else (p.get("notes") or ""))  # DESLIGADO PELA MUTACAO',
     "🔴 o passo compartilhado continua no exame das notes"),

    # FURO 8 (C8) - A REGUA PUNIA O HANDOFF CORRETO.
    # 📊 22/08/2026: 28 telas em 6 rotas disparavam
    #    `detect_handoff_trigger` e eram contadas como ORFA FUNCIONAL --
    #    *"o defeito"*. Quem apagasse os gatilhos GANHAVA ponto.
    ("scripts/replay.py",
     "elif M.detect_handoff_trigger(pb, texto):",
     "elif False:  # DESLIGADO PELA MUTACAO",
     "🔴 o replay sabe que HANDOFF nao e orfa"),

    # FURO 7 (C7) - A REGRA QUE SO EXISTIA NO DOCUMENTO.
    # 📊 22/08/2026: `grep -c constante_justificada scripts/rubrica.py` -> 0.
    #    A regua nunca leu o campo. Uma rota com 12 constantes decidindo pelo
    #    cliente tirava 95/100. 🔴 Desligar a leitura tem de derrubar o item.
    ("scripts/rubrica.py",
     "decidem = CR.constantes_sem_justificativa(pb, rota.servico, textos_do_corredor)",
     "decidem = []  # DESLIGADO PELA MUTACAO",
     "🔴 a regua LE `constante_justificada` -- nao so o documento"),

    # FURO 1 — a ancora que nunca casou. 📊 "informe o numero da residencia"
    # tem ZERO ocorrencias em 28.096 eventos; a URA escreve "me CONFIRME".
    ("app/services/corridor_playbooks.py",
     r'"anchor": r"(?:informe|confirme) o n[úu]mero da resid[êe]ncia"',
     r'"anchor": r"informe o n[úu]mero da resid[êe]ncia"',
     "🔴 'me CONFIRME o número da residência' casa o passo"),

    # FURO 2 — o freio da conferencia. 📊 156 mensagens / 65 sessoes passaram
    # pela conferencia sem verificacao nenhuma. O allianz-auto ja tinha a ancora.
    ("app/services/corridor_playbooks.py",
     '        r"dados a seguir est[ãa]o corretos",',
     '        r"ZZ_ANCORA_DESLIGADA_PELA_MUTACAO_ZZ",',
     "🔴 'dados a seguir estão corretos' ARMA o freio no residencial"),

    # FURO 3 — a declaracao que o motor nao lia. 📊 `schedule_agendado` existia
    # no corredor e `extract_capture_anchors` lia cinco chaves, nunca aquela.
    # A cliente recebeu "Prontinho! Sua assistencia foi aberta" SEM data e SEM
    # periodo. Mutar a chave e recriar exatamente esse estado.
    ("app/services/corridor_playbooks.py",
     '"schedule_agendado": (',
     '"schedule_agendado_DESLIGADO": (',
     "🔴 a tela real de 19/08 16:39 devolve `schedule` pelo MOTOR"),

    # FURO 3, SEGUNDA METADE — C2. 📊 `client_summary_from_capture` capturava o
    # periodo e nao o entregava: lia from/day/at, nunca `periodo`. Desligar o
    # ramo recria exatamente a mensagem que a cliente recebeu em 19/08 --
    # protocolo e dia, sem o periodo.
    ("app/services/insurer_dispatch_service.py",
     'elif schedule and schedule.get("periodo"):',
     'elif schedule and schedule.get("ZZ_PERIODO_DESLIGADO_PELA_MUTACAO"):',
     "🔴 o cliente recebe o PERÍODO — a metade que faltava"),
]


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
# ===========================================================================
# 🔴 O FURO Nº 3 TINHA UMA SEGUNDA METADE, E ELA FICOU ABERTA — C2, 22/08/2026
# ===========================================================================
#
# O bloco acima prova que `extract_capture_anchors` **CAPTURA** o período. Isso
# consertou metade do furo.
#
# 📊 A outra metade: `client_summary_from_capture` lia `schedule["from"]`,
#    `["day"]` e `["at"]` — e **nunca** `["periodo"]`. A captura chegava
#    completa e a mensagem ao cliente saía sem o período:
#
#      captura   {'schedule': {'day': 'terca-feira, 06/01/2026',
#                              'periodo': 'tarde das 13:00 as 18:00'}}
#      cliente   "Sua assistência foi agendada para o dia terca-feira,
#                 06/01/2026."
#                                                   ^ e o período morria aqui
#
# 🔴 Capturar sem entregar não é entregar. A cliente de 19/08 recebeu o
#    protocolo e **não soube quando o técnico vinha** — que é a única coisa que
#    ela queria saber.
# ⚠️ O motor pesado nao carrega com o shim leve deste arquivo (fastembed).
#    Carregado por caminho, como `regua_motor` faz -- e o teste continua
#    chamando o MOTOR, nunca uma copia da funcao (CLAUDE.md §9.4).
import importlib.util as _ilu  # noqa: E402
_sp_ids = _ilu.spec_from_file_location(
    "app.services.insurer_dispatch_service",
    os.path.join(_RAIZ, "app", "services", "insurer_dispatch_service.py"))
IDS = _ilu.module_from_spec(_sp_ids)
sys.modules[_sp_ids.name] = IDS
_sp_ids.loader.exec_module(IDS)

RESUMO_PERIODO = IDS.client_summary_from_capture({
    "captured": {"protocol": "52955490",
                 "schedule": {"day": "terca-feira, 06/01/2026",
                              "periodo": "tarde das 13:00 as 18:00"}},
    "playbook_ref": "allianz-residencial-whatsapp@v1",
}) or ""
certo("52955490" in RESUMO_PERIODO,
      "🔴 o cliente recebe o PROTOCOLO", RESUMO_PERIODO[:60])
certo("06/01/2026" in RESUMO_PERIODO,
      "🔴 o cliente recebe o DIA", RESUMO_PERIODO[:60])
certo("tarde das 13:00" in RESUMO_PERIODO,
      "🔴 o cliente recebe o PERÍODO — a metade que faltava",
      RESUMO_PERIODO.split(chr(10))[0])

# 🔴 E OS CONTROLES QUE IMPEDEM O RAMO NOVO DE ROUBAR OS OUTROS.
#    A ordem vai do mais específico ao menos: from/to · periodo · at · day.
#    Pôr `periodo` no lugar errado o tornaria inalcançável — que é o defeito de
#    hoje escrito de outro jeito.
_JANELA = IDS.client_summary_from_capture({
    "captured": {"protocol": "1",
                 "schedule": {"day": "25/08/2026", "from": "13h00", "to": "14h00"}},
    "playbook_ref": "allianz-residencial-whatsapp@v1"}) or ""
certo("entre 13h00 e 14h00" in _JANELA,
      "🔴 CONTROLE: a janela FECHADA (from/to) continua vencendo o periodo",
      _JANELA.split(chr(10))[0])
_SO_DIA = IDS.client_summary_from_capture({
    "captured": {"protocol": "1", "schedule": {"day": "25/08/2026"}},
    "playbook_ref": "allianz-residencial-whatsapp@v1"}) or ""
certo("25/08/2026" in _SO_DIA and "período" not in _SO_DIA,
      "🔴 CONTROLE: schedule SEM periodo nao inventa periodo",
      _SO_DIA.split(chr(10))[0])


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


# =============================================================================
# 🔴 C7 - A REGUA LE `constante_justificada`, NAO SO O DOCUMENTO
# =============================================================================
#
# 📊 22/08/2026: `grep -c constante_justificada scripts/rubrica.py` -> **0**.
#    A regua consultava `conferir_respostas` so para a ORIGEM DO SLOT. A regra
#    B -- o corredor afirmando um fato sobre o segurado -- nao valia ponto.
#    Uma rota com 12 constantes decidindo por conta propria tirava 95/100.
#
# 🔴 **Uma regra que so existe no documento nao e regra. E intencao.**
#
# ⚠️ O guarda precisa das DUAS metades, senao ele passa por vacuidade: uma
#    rota SUJA que zera o item, e uma LIMPA que o recebe. So a segunda provaria
#    apenas que o item existe; so a primeira, apenas que ele sabe reprovar.
print()
print("=" * 74)
print("[C7] a regua LE a justificativa da constante")
print("=" * 74)

import importlib.util as _ilu
_e = _ilu.spec_from_file_location(
    "_rb_c7", os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "scripts", "rubrica.py"))
_RB = _ilu.module_from_spec(_e)
sys.modules["_rb_c7"] = _RB
_e.loader.exec_module(_RB)


def _item_c7(seg, ramo, serv):
    for r in _RB.M.rotas():
        if (r.seguradora, r.ramo, r.servico) == (seg, ramo, serv):
            for it in _RB.eixo_c(r, _RB.RP.replay(r)):
                if "constante decide" in it.nome:
                    return it
    return None


# ⚠️ ESTA ASSERCAO MIGROU, e o motivo e o §9.3 do CLAUDE.md.
#
#    A 1a versao media `hdi/auto/guincho`, que naquele dia tinha
#    `situacao_risco` e `quando_agora` respondendo pelo cliente. 📊 Horas
#    depois, a decisao 2 do Founder converteu as quatro em pergunta e as sete
#    do `quando` em derivacao -- e **nao sobrou UMA rota suja no produto**.
#
#    🔴 Um guarda que dependesse de existir defeito no codigo morre no dia
#    em que o defeito e consertado. A pergunta que ele protege continua viva:
#    *"a regua ZERA o item quando a constante decide sem justificativa?"*
#    Entao o caso passa a ser CONSTRUIDO: tira-se a justificativa de um passo
#    que decide, mede-se, e devolve-se.
_REF = "allianz-residencial-whatsapp@v1"
_PASSO = "menu_tipo_seguro"
_pb_c7 = _RB.M.get_playbook(_REF)
_alvo_c7 = [p for p in _pb_c7["ura_steps"] if p.get("step") == _PASSO][0]
_guardada = _alvo_c7.pop("constante_justificada", None)
certo(_guardada is not None,
      f"📊 o passo `{_PASSO}` TEM justificativa hoje (senao o teste e vacuo)")
try:
    _suja = _item_c7("allianz", "residencial", "maquina_de_lavar")
finally:
    if _guardada is not None:
        _alvo_c7["constante_justificada"] = _guardada

_limpa = _item_c7("allianz", "residencial", "maquina_de_lavar")

certo(_suja is not None and _suja.pontos == 0,
      "🔴 a regua LE `constante_justificada` -- nao so o documento",
      f"sem a justificativa de `{_PASSO}` o item deu "
      f"{_suja.pontos if _suja else '?'} pontos")
certo(_limpa is not None and _limpa.pontos == _limpa.maximo,
      "🔴 CONTROLE: devolvida a justificativa, a MESMA rota recebe os 6 -- "
      "o item nao reprova todo mundo, e a restauracao funcionou",
      f"{(_limpa.pontos if _limpa else '?')}/{(_limpa.maximo if _limpa else '?')}")


# =============================================================================
# 🔴 C8 - O REPLAY SABE QUE HANDOFF NAO E ORFA
# =============================================================================
#
# 📊 28 telas em 6 rotas disparavam gatilho de handoff e contavam como
#    ORFA FUNCIONAL, que a rubrica chama de *"o defeito"*. 🔴 O incentivo
#    era invertido: apagar os gatilhos GANHAVA ponto, e o corredor passaria a
#    conduzir calado fluxos que exigem uma pessoa.
#
# ⚠️ As provas de fundo estao em `test_o_handoff_nao_e_um_buraco.py`. Esta
#    aqui existe porque a mutacao precisa de uma assercao NESTE arquivo -- e o
#    guarda que a mutacao derruba tem de ser o guarda que a regua conta.
print()
print("=" * 74)
print("[C8] o replay sabe que HANDOFF nao e orfa")
print("=" * 74)

import replay as _RPc8
_com_handoff = 0
_rota_c8 = None
for _r in _RB.M.rotas():
    if not _RB.M.get_playbook(_r.ref):
        continue
    _rp = _RPc8.replay(_r)
    if _rp.handoffs:
        _com_handoff += _rp.handoffs
        _rota_c8 = _rota_c8 or _r

certo(_com_handoff >= 10,
      "🔴 o replay sabe que HANDOFF nao e orfa",
      f"{_com_handoff} telas classificadas HANDOFF (esperado >=10)")
certo(_rota_c8 is not None and _RPc8.replay(_rota_c8).pedem_algo ==
      _RPc8.replay(_rota_c8).respondidas +
      len(_RPc8.replay(_rota_c8).orfas_funcionais),
      "🔴 CONTROLE: e o handoff nao entrou no denominador nem no numerador")


# =============================================================================
# 🔴 C16 - O PASSO COMPARTILHADO CONTINUA NO EXAME DAS `notes`
# =============================================================================
#
# 📊 A v3 do item excluia do exame todo passo presente em mais de um playbook.
#    Em `allianz/auto`, dos ~60 passos do corredor **1 sobrevivia**, e ele nao
#    tem numero: `com_numero == 0` e a rota levava 0 de 2 -- por nao ter nada
#    que pudesse ser conferido. 28 rotas estavam assim.
#
# ⚠️ E o incentivo era pior que o zero: para ganhar o ponto era preciso
#    DUPLICAR o passo por corredor -- a §5 do CLAUDE.md ao contrario.
#
# ⚠️ As provas de fundo estao em `test_o_passo_compartilhado_ainda_e_conferido.py`.
#    Esta aqui existe porque a mutacao precisa de uma assercao NESTE arquivo.
print()
print("=" * 74)
print("[C16] o passo compartilhado continua no exame das notes")
print("=" * 74)

_rota_c16 = [_r for _r in _RB.M.rotas()
             if (_r.seguradora, _r.ramo, _r.servico) == ("allianz", "auto", "guincho")][0]
_it_c16 = [_i for _i in _RB.eixo_b(_rota_c16, _RPc8.replay(_rota_c16))
           if "notes" in _i.nome][0]
_m_c16 = _re.search(r"(\d+) de (\d+) notes", _it_c16.evidencia)
certo(_m_c16 is not None and int(_m_c16.group(2)) >= 1,
      "🔴 o passo compartilhado continua no exame das notes",
      f"com_numero=0 -> o item daria 0 de 2 e ninguem poderia evitar "
      f"| {_it_c16.evidencia}")
# ⚠️ 🔴 O CONTROLE ANTERIOR VENCEU NO MESMO DIA EM QUE NASCEU (§9.3).
#
# Ele dizia `_it_c16.pontos < 2` -- *"a rota nao ganha os 2 de graca"*. Era
# verdade enquanto as notes de `allianz/auto` estavam sub-declaradas; virou
# mentira uma hora depois, quando elas foram recontadas na populacao certa e a
# rota chegou a 2/2. **Um controle que depende de um defeito continuar aberto
# nao e controle: e refem.**
#
# 🔴 O controle certo nao pergunta se ALGUEM esta vermelho -- pergunta se o
#    item CONSEGUE ficar vermelho. Entao ele quebra a note de proposito, chama
#    a REGUA (nao uma copia da regra), confere o vermelho e restaura.
_alvo_c16 = next(p for p in _RB.M.get_playbook(_rota_c16.ref)["ura_steps"]
                 if p.get("step") == "desfecho_protocolo_alfa")
_nota_c16 = _alvo_c16["notes"]
_alvo_c16["notes"] = "📊 1 tela / 1 sessão."          # sub-declarada de proposito
_quebrado_c16 = [_i for _i in _RB.eixo_b(_rota_c16, _RPc8.replay(_rota_c16))
                 if "notes" in _i.nome][0]
_alvo_c16["notes"] = _nota_c16                        # e devolvida antes de julgar
_restaurado_c16 = [_i for _i in _RB.eixo_b(_rota_c16, _RPc8.replay(_rota_c16))
                   if "notes" in _i.nome][0]

certo(_quebrado_c16.pontos < _it_c16.pontos,
      "🔴 CONTROLE: uma note SUB-DECLARADA derruba o item -- ele consegue "
      "ficar vermelho",
      f"com a note quebrada: {_quebrado_c16.pontos}/2 ({_quebrado_c16.evidencia})")
certo(_restaurado_c16.pontos == _it_c16.pontos,
      "🔴 CONTROLE: e a note foi RESTAURADA -- o guarda nao deixa lixo para tras",
      f"{_restaurado_c16.pontos}/2 vs {_it_c16.pontos}/2")



# =============================================================================
# 🔴 C17 - CADA ROTA TEM ONDE ESCREVER A PROPRIA TRANSCRICAO
# =============================================================================
#
# 📊 `_fonte_do_bloco` e indexado por SERVICO, e servico nao identifica rota:
#    `hdi/auto/guincho` lia o mesmo one-liner de `_AUTO_SUBSERVICES["guincho"]`
#    que `allianz/auto/guincho`, onde esta escrita uma sessao DA ALLIANZ. O
#    item fazia a coisa certa e nao creditava a hdi -- mas a hdi nao tinha
#    lugar nenhum. 📊 Das 41 rotas com telas, **22 liam citacao de outra rota**.
#
# ⚠️ A prova NAO mudou: a sessao citada continua tendo de estar no corpus DESTA
#    rota. O marcador so diz ONDE procurar.
print()
print("=" * 74)
print("[C17] cada rota tem endereco proprio para a transcricao")
print("=" * 74)

_rota_c17 = [_r for _r in _RB.M.rotas()
             if (_r.seguradora, _r.ramo, _r.servico) == ("hdi", "auto", "guincho")][0]
_it_c17 = [_i for _i in _RB.eixo_a(_rota_c17, _RPc8.replay(_rota_c17))
           if "transcrita" in _i.nome][0]
certo(_it_c17.pontos == _it_c17.maximo,
      "🔴 a rota tem endereco proprio para a transcricao",
      f"{_it_c17.pontos}/{_it_c17.maximo}: {_it_c17.evidencia}")

# 🔴 CONTROLE: e a prova continua sendo a SESSAO. Um marcador que cite sessao
#    de outra rota nao vale nada -- senao o C17 teria virado um afrouxamento.
_bloco_c17 = _RB._transcricao_da_rota(_rota_c17)
certo(_bloco_c17 is not None and "ROTA hdi/auto/guincho" in _bloco_c17,
      "🔴 CONTROLE: a janela lida e a do MARCADOR desta rota, nao a do vizinho",
      (_bloco_c17 or "")[:70])
_rota_c17b = [_r for _r in _RB.M.rotas()
              if (_r.seguradora, _r.ramo, _r.servico) == ("allianz", "auto", "guincho")][0]
certo(_RB._transcricao_da_rota(_rota_c17b) != _bloco_c17,
      "🔴 CONTROLE: e a MESMA rota de guincho em outra seguradora le OUTRA "
      "janela — se fossem a mesma, uma citacao pagaria as duas")

# =============================================================================
# 🔴 C18 - O ARQUIVO COM MAIS TELAS VENCIA O COM CONTROLE
# =============================================================================
#
# 📊 `hdi/auto/chaveiro`: `test_o_atlas_conta_certo.py` (10 telas, 0 controles)
#    vencia `test_o_corredor_da_hdi_responde_a_ura_dela.py` (3 telas, 14
#    controles), e a rota levava 0 de 3 em CONTROLE havendo um guarda escrito
#    para ela. O ponto nao faltava: era procurado no arquivo errado.
print()
print("=" * 74)
print("[C18] entre arquivos que ja cobrem, ganha o que tambem GUARDA")
print("=" * 74)

_rota_c18 = [_r for _r in _RB.M.rotas()
             if (_r.seguradora, _r.ramo, _r.servico) == ("hdi", "auto", "chaveiro")][0]
_itens_c18 = _RB.eixo_e(_rota_c18, _RPc8.replay(_rota_c18))
_cob = [_i for _i in _itens_c18 if "toca >=3 telas" in _i.nome][0]
_ctl = [_i for _i in _itens_c18 if "CONTROLE" in _i.nome][0]
certo(_ctl.pontos == _ctl.maximo,
      "🔴 a rota recebe o CONTROLE do guarda que foi escrito para ela",
      f"{_ctl.pontos}/{_ctl.maximo}: {_ctl.evidencia}")
# 🔴 CONTROLE: e a COBERTURA nao foi afrouxada no caminho.
certo(_cob.pontos == _cob.maximo,
      "🔴 CONTROLE: e a cobertura continua provada — o criterio de telas nao "
      "foi rebaixado", f"{_cob.pontos}/{_cob.maximo}: {_cob.evidencia}")



# =============================================================================
# 🔴 C19 - O PROTOCOLO COM PREFIXO MORRIA NA MASCARA
# =============================================================================
#
# 📊 O protocolo da PORTO tem prefixo -- `1-408029004672` -- e a regra de
#    digitos do mascarador so mordia o rabo dele:
#
#      cru        "Aqui esta seu protocolo de atendimento 1-408029004672"
#      mascarado  "Aqui esta seu protocolo de atendimento 1-{NUMERO}"
#
#    A reinjecao trocava o marcador pelo valor INTEIRO e produzia `1-1-4080...`,
#    que o motor recusava -- com razao. O protocolo morria, e com ele os 12
#    pontos de "a ROTA foi percorrida ate o fim" e os 5 de "protocolo + dia +
#    periodo", nas CINCO rotas de porto/auto e nas de porto/residencial.
#
# ⚠️ A allianz e a hdi passavam porque o protocolo delas e so digitos: o
#    marcador cobre o valor inteiro. O defeito so existia em quem usa prefixo,
#    e sumia do radar exatamente por isso.
print()
print("=" * 74)
print("[C19] o protocolo com PREFIXO sobrevive a mascara")
print("=" * 74)

import higiene_do_corpus as _H  # noqa: E402

_CRU_PORTO = "Aqui está seu protocolo de atendimento 👇 1-408029004672"
_pb_porto = _RB.M.get_playbook("porto-auto-whatsapp@v1")
_limpo = _H.higienizar(_pb_porto, _CRU_PORTO, set())[0]
certo(_RB.M.extract_capture_anchors(_pb_porto, _limpo).get("protocol")
      == "1-408029004672",
      "🔴 o protocolo com prefixo sobrevive a mascara",
      f"sobrou: {_limpo!r}")

# 🔴 CONTROLE 1: e o mascarador NAO virou peneira -- telefone e CPF continuam
#    apagados na MESMA passagem.
_SUJO = ("Aqui está seu protocolo 👇 1-408029004672. Meu telefone e "
         "(47) 90000-0000 e o CPF 529.982.247-25")
_lsujo = _H.higienizar(_pb_porto, _SUJO, set())[0]
certo(not _H.auditar_pii(_lsujo) and "99627" not in _lsujo
      and "529.982" not in _lsujo,
      "🔴 CONTROLE: telefone e CPF continuam apagados na mesma tela",
      f"sobrou: {_lsujo!r}")

# 🔴 CONTROLE 2: e o corpus VERSIONADO ja carrega o protocolo -- senao o
#    conserto estaria no codigo e nao no que a regua le.
_tel_porto = [l["text"] for l in _RPc8.carregar_corpus("porto", "auto")]
certo(any(_re.search(r"protocolo de atendimento[^\d]{0,6}\d-\d{6,}", t)
          for t in _tel_porto),
      "🔴 CONTROLE: o corpus de porto/auto tem o protocolo em claro",
      f"{len(_tel_porto)} telas")



# =============================================================================
# 🔴 C20 - A ESCOLHA PELA PLACA NAO CASAVA A TELA REAL
# =============================================================================
#
# 📊 `pick_option_by_plate` exigia `(\d+)\s*-` -- digito colado no hifen. A URA
#    da Allianz e da Porto manda o numero EM NEGRITO:
#
#      "*1* - X1, placa AA#-###1   *2* - Outro veiculo   *0* - Sair"
#
#    Com o `*` no meio, nada casava: a funcao devolvia '' nas telas reais das
#    DUAS seguradoras, e so acertava a string do docstring, escrita a mao sem
#    asteriscos.
#
# ⚠️ §9.5 na forma pura: **casar o texto do teste nao e responder a tela**. O
#    comentario do passo dizia "'1' fixo pegou o carro ERRADO numa apolice com
#    2 veiculos" -- a licao estava escrita, o guarda existia, e ele nao
#    alcancava a tela que a URA manda.
print()
print("=" * 74)
print("[C20] a escolha pela placa casa a tela REAL, com o numero em negrito")
print("=" * 74)

_TELA_ALLIANZ = ("Por favor, confirme o veículo para atendimento: "
                 "*1* - X1, placa AA#-###1 *2* - Outro veículo *0* - Sair")
_TELA_PORTO = ("Fulano, como eu posso te ajudar? "
               "*1* - JEEP, ano 2025, placa BB#-##44 "
               "*2* - FIAT, ano 2019, placa QQ#-##11 *3* - Outro veículo")

certo(_RB.M.CP.pick_option_by_plate(_TELA_ALLIANZ, "AAA1231") == "1",
      "🔴 a escolha pela placa casa a tela REAL, com o numero em negrito",
      f"devolveu {_RB.M.CP.pick_option_by_plate(_TELA_ALLIANZ, 'AAA1231')!r}")

# 🔴 CONTROLE 1: com DOIS veiculos, a placa decide QUAL -- e a resposta muda.
certo(_RB.M.CP.pick_option_by_plate(_TELA_PORTO, "QQQ1111") == "2"
      and _RB.M.CP.pick_option_by_plate(_TELA_PORTO, "BBB1244") == "1",
      "🔴 CONTROLE: com dois veiculos na tela, cada placa da uma tecla",
      f"{_RB.M.CP.pick_option_by_plate(_TELA_PORTO, 'QQQ1111')!r} / "
      f"{_RB.M.CP.pick_option_by_plate(_TELA_PORTO, 'BBB1244')!r}")

# 🔴 CONTROLE 2: e placa que NAO esta na tela continua sem resposta -- a
#    funcao nao pode chutar veiculo, que e o defeito que ela existe para
#    impedir.
certo(_RB.M.CP.pick_option_by_plate(_TELA_PORTO, "ZZZ9999") == "",
      "🔴 CONTROLE: placa que nao esta na tela NAO escolhe nada",
      f"devolveu {_RB.M.CP.pick_option_by_plate(_TELA_PORTO, 'ZZZ9999')!r}")

print()
print("=" * 74)
print("[C6] a tela do FORMULARIO NATIVO nao e uma tela inocua")
print("=" * 74)

# 🔴 O quarto ponto cego da familia C8/C9/P-084-30 -- e o unico que erra para
#    o lado do PREMIO. O replay nunca chamava `detect_native_flow`, entao a
#    tela que TRAVA o acionamento saia do denominador como orfa inocua, e o
#    item "zero orfas funcionais" dava 20/20 a duas rotas que nao respondem o
#    formulario.
import replay as _RPF                                            # noqa: E402

_com_flow = {}
for _rota_f in _RB.M.rotas():
    _rp_f = _RPF.replay(_rota_f)
    if _rp_f.formularios:
        _com_flow[str(_rota_f)] = _rp_f

# ATUALIZADO -- SPEC-084.2 C4: o registro do segundo formulario da familia
#    revelou tres rotas a mais que ja batiam nele.
certo(len(_com_flow) >= 5,
      "📊 cinco rotas ou mais tem formulario nativo no corpus",
      str(sorted(_com_flow)))

_telas_flow = [t for rp in _com_flow.values() for t in rp.telas
               if str(t.passo or "").startswith("flow")]
certo(_telas_flow and all(t.classe != _RPF.ORFA_INOCUA for t in _telas_flow),
      "o formulario nativo NAO e uma tela inocua",
      f"classes: {[t.classe for t in _telas_flow]}")

# 🔴 CONTROLE: as rotas CONTINUAM tendo orfas inocuas de verdade -- a classe
#    nao sumiu, so deixou de abrigar o formulario. Sem esta metade, apagar a
#    classe inteira passaria verde.
certo(sum(rp.orfas_inocuas for rp in _com_flow.values()) > 0,
      "🔴 CONTROLE: a classe ORFA_INOCUA continua existindo nas mesmas rotas",
      str({k: v.orfas_inocuas for k, v in _com_flow.items()}))

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
