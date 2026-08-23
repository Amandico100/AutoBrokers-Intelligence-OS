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
    # (arquivo, texto_de, texto_para, rotulo_da_assercao_que_deve_cair)

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
# 🔴 CONTROLE: e o exame ainda REPROVA -- a rota nao ganha os 2 de graca.
certo(_it_c16.pontos < 2,
      "🔴 CONTROLE: e ele AINDA acusa -- notes sub-declaradas seguem vermelhas",
      f"{_it_c16.pontos}/2: {_it_c16.evidencia}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
