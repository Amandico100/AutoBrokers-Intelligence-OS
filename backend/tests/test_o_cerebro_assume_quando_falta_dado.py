# -*- coding: utf-8 -*-
"""Tela CONHECIDA com dado faltando: o cerebro pensa, em vez de o caso morrer.

O DEFEITO, MEDIDO
=================
📊 19/08/2026. O travamento do acionamento NAO acontecia na tela desconhecida
-- essa sempre teve cerebro. Acontecia na tela CONHECIDA:

    elif not rendered["ok"]:
        session["state"] = "needs_human"      # na hora, sem tentar nada

E `needs_human` esta dentro de `_TERMINAL_STATES` do Vigia, cuja primeira
linha e `if state in _TERMINAL_STATES: return None`. Ou seja: **ninguem
tentava de novo, nunca.** O cerebro ficava a tres linhas de distancia e nao
era consultado.

📊 A marca que permitia o contrario, `fallback_adaptive`, existia em 29 de
~250 passos -- e em **0 de 29** no `allianz-residencial`. Foi o que produziu
os 2min22 e o clique manual do Founder em 18/08: a tela `o_que_aconteceu`
exigia `problema_eletrico_opcao`, nada preenchia, e o motor parou de vez.

A REGRA NOVA
============
    tela REVERSIVEL  (menu, pedido de dado)   -> o cerebro assume
    tela IRREVERSIVEL (confirmar, abrir)      -> para, como antes

O discriminador e `pergunta_de_decisao`, que JA era a autoridade do produto
sobre "esta tela abre servico de verdade". Nao ha criterio novo (CLAUDE.md §5).

🔴 O TESTE MAIS IMPORTANTE DESTE ARQUIVO E O 2. Um guarda que so provasse
"agora o cerebro assume" estaria comemorando ter tirado o freio. O que
precisa ser provado e que ele assume no menu E CONTINUA PARANDO na
confirmacao.
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

IDS = importlib.import_module("app.services.insurer_dispatch_service")
CP = importlib.import_module("app.services.corridor_playbooks")

OK = 0
FAIL = 0


def certo(condicao, rotulo):
    global OK, FAIL
    if condicao:
        OK += 1
        print(f"  ok   {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}")


PB = "allianz-residencial-whatsapp@v1"


def sessao_com(slots, subservico="eletricista"):
    """Uma sessao de verdade, do motor de verdade."""
    s = IDS.new_dispatch_session(
        case_id="caso-1", company_id="emp-1", playbook_ref=PB,
        subservice=subservico, slots=dict(slots))
    s["state"] = "ura"
    return s


def passo_que_exige(nome_do_slot):
    """Acha um passo REAL do corredor que exija este slot, e devolve o texto
    de tela que casa a ancora dele.

    🔴 Nao invento tela: pego a ancora do proprio playbook e construo uma
    string que ela case. Inventar o texto provaria so que eu sei escrever
    regex.
    """
    pb = CP._PLAYBOOKS[PB]
    for p in pb["ura_steps"]:
        if nome_do_slot in (p.get("requires") or []):
            return p
    return None


print()
print("=" * 70)
print("  0. O TERRENO — o defeito descrito existe mesmo neste corredor")
print("=" * 70)

pb = CP._PLAYBOOKS[PB]
com_marca = [p for p in pb["ura_steps"] if p.get("fallback_adaptive")]
com_requires = [p for p in pb["ura_steps"] if p.get("requires")]
certo(len(com_requires) > 0,
      f"o corredor TEM passos que exigem slot ({len(com_requires)} de "
      f"{len(pb['ura_steps'])})")
certo(len(com_marca) == 0,
      f"e NENHUM deles tem `fallback_adaptive` ({len(com_marca)}) — "
      "logo, antes, TODO slot faltante aqui era morte instantanea")

print()
print("=" * 70)
print("  1. MENU (reversivel) sem o dado -> o cerebro assume, NAO morre")
print("=" * 70)

alvo = passo_que_exige("problema_eletrico_opcao")
certo(alvo is not None, "achei um passo real que exige `problema_eletrico_opcao`")

# Slots do caso SEM a tecla que o passo exige, e sem nada que a derive.
s = sessao_com({"titular_cpf": "03009596995", "titular_nome": "CLARISSA",
                "telefone_contato": "48991071877", "endereco_numero": "112"})
s["slots"].pop("problema_eletrico_opcao", None)
s["slots"]["problema_descricao"] = ""     # sem texto: o derivador nao tem o que ler
s["slots"].pop("problema_relato", None)

# a tela real que casa a ancora daquele passo
# 🔴 A TELA REAL do travamento de 18/08. A ancora do passo
# `o_que_aconteceu` e literalmente `o que aconteceu\?`.
tela_menu = ("O que aconteceu? | "
             "1 - Casa inteira ou parcial sem energia | "
             "2 - Curto circuito ou mau funcionamento das tomadas")
casou = CP.match_ura_step(pb, tela_menu, subservice="eletricista")
certo(casou is not None,
      "CONTROLE: a tela de teste REALMENTE casa um passo do corredor "
      "(senao o teste mediria a tela desconhecida, que nunca foi o problema)")

antes_estado = s["state"]
r = IDS.handle_insurer_message(s, tela_menu)
certo(antes_estado == "ura", "CONTROLE: a sessao entrou em `ura`")
certo(r.get("state") != "needs_human",
      "🔴 tela de MENU sem o dado NAO vira needs_human")
certo(not str(r.get("reason") or "").startswith("missing_slots"),
      "e o motivo NAO e missing_slots")

# 🔴 A CONSEQUENCIA QUE IMPORTA, e a resposta a pergunta do Founder
# ("o agente precisa saber que esta travado"): o caso cai num estado que o
# VIGIA reprocessa. Antes caia em `needs_human`, que e terminal — e terminal
# quer dizer que ninguem tenta de novo, nunca.
import re as _re  # noqa: E402

_src_vigia = open(os.path.join(_RAIZ, "app", "tasks", "dispatch_watchdog.py"),
                  encoding="utf-8").read()
_m = _re.search(r"_TERMINAL_STATES = \{(.*?)\}", _src_vigia, _re.S)
TERMINAIS = {x.strip().strip('"') for x in _m.group(1).replace("\n", " ").split(",")
             if x.strip()}
certo("needs_human" in TERMINAIS,
      "CONTROLE: `needs_human` E terminal para o Vigia "
      "(por isso o caso morria ali)")
certo(r.get("state") not in TERMINAIS,
      f"🔴 o caso ficou em {r.get('state')!r}, que NAO e terminal — "
      "o Vigia volta nele")
certo(r.get("ultimo_passo_sem_dado", {}).get("step") == "o_que_aconteceu",
      "e o caso carrega ONDE empacou — é assim que o agente 'sabe' "
      "que travou")
certo("sem energia" in str(r.get("ultimo_passo_sem_dado", {}).get("notes") or ""),
      "com as opcoes reais da tela, que o corredor ja conhecia")

print()
print("=" * 70)
print("  2. 🔴 CONFIRMACAO (irreversivel) sem o dado -> CONTINUA PARANDO")
print("=" * 70)

# Uma tela que `pergunta_de_decisao` reconhece como irreversivel.
tela_decisao = None
for padrao_tela in ("Podemos confirmar o atendimento?",
                    "Posso confirmar a abertura do chamado?",
                    "Confirma a abertura do servico?"):
    if IDS.pergunta_de_decisao(pb, padrao_tela):
        tela_decisao = padrao_tela
        break
certo(tela_decisao is not None,
      f"CONTROLE: achei uma tela que o produto RECONHECE como irreversivel "
      f"({tela_decisao!r})")
certo(not IDS.pergunta_de_decisao(pb, tela_menu),
      "🔴 CONTROLE CRUZADO: e a tela de MENU do teste 1 NAO e reconhecida "
      "como irreversivel (os dois testes medem coisas diferentes)")


# Agora: um passo que casa a tela de decisao E exige um slot que falta.
# Monta-se um playbook derivado do real, com UM passo a mais — assim a
# irreversibilidade vem do produto e so o passo e do teste.
pb_teste = dict(pb)
pb_teste["ura_steps"] = [{
    "step": "confirmar_com_dado_faltando",
    "anchor": r"podemos confirmar o atendimento",
    "reply": "{um_slot_que_nao_existe}",
    "requires": ["um_slot_que_nao_existe"],
}] + list(pb["ura_steps"])
CP._PLAYBOOKS["corredor-de-teste@v1"] = pb_teste

s2 = sessao_com({"titular_cpf": "03009596995"})
s2["playbook_ref"] = "corredor-de-teste@v1"
s2["state"] = "ura"
r2 = IDS.handle_insurer_message(s2, tela_decisao)
certo(r2.get("state") == "needs_human",
      "🔴 tela de CONFIRMACAO sem o dado PARA — o freio nao foi removido")
certo(str(r2.get("reason") or "").startswith("missing_slots"),
      "e o motivo diz missing_slots")
certo(r2.get("parou_em_decisao"),
      "e registra QUAL padrao de decisao segurou o caso "
      f"({r2.get('parou_em_decisao')!r})")

print()
print("=" * 70)
print("  3. O CEREBRO RECEBE O QUE FALTOU — nao so a tela crua")
print("=" * 70)

s3 = sessao_com({"titular_cpf": "03009596995"})
s3["ultimo_passo_sem_dado"] = {"step": "menu_do_problema",
                              "faltou": ["problema_eletrico_opcao"],
                              "notes": "1-Falta de energia 2-Curto circuito"}
prompt = IDS.build_human_phase_messages(s3, "Selecione o problema:")
alvo_txt = prompt["user"]
certo("ONDE O AUTOMÁTICO EMPACOU" in alvo_txt,
      "🔴 o prompt diz ao cerebro que o automatico empacou")
certo("menu_do_problema" in alvo_txt, "e diz QUAL tela era")
certo("problema_eletrico_opcao" in alvo_txt, "e diz QUAL dado faltou")
certo("1-Falta de energia" in alvo_txt,
      "e entrega as opcoes que o corredor ja conhecia daquela tela")

# CONTROLE: sem empaque, o bloco NAO aparece. Senao o teste acima estaria
# medindo um texto fixo que existe sempre.
s4 = sessao_com({"titular_cpf": "03009596995"})
s4.pop("ultimo_passo_sem_dado", None)
prompt4 = IDS.build_human_phase_messages(s4, "Selecione o problema:")
certo("ONDE O AUTOMÁTICO EMPACOU" not in prompt4["user"],
      "CONTROLE: sem empaque o bloco NAO entra no prompt "
      "(logo o teste acima mediu o dado, nao um texto fixo)")

print()
print("=" * 70)
print("  4. RESOLVIDO O EMPAQUE, A MARCA SOME")
print("=" * 70)

s5 = sessao_com({"titular_cpf": "03009596995"})
s5["ultimo_passo_sem_dado"] = {"step": "x", "faltou": ["y"], "notes": ""}
s5["falta_para_a_ura"] = {"rotulo": "y"}
s5["state"] = "human_phase"
certo("ultimo_passo_sem_dado" in s5, "CONTROLE: a marca estava la antes")
s5 = IDS.reply_human_phase(s5, "2")
certo("ultimo_passo_sem_dado" not in s5,
      "🔴 respondida a fase humana, a marca do empaque some")
certo("falta_para_a_ura" not in s5, "e o que faltava para a URA tambem")

print()
print("=" * 70)
print("  5. O QUE JA FUNCIONAVA CONTINUA FUNCIONANDO")
print("=" * 70)

# Passo com TODOS os dados: responde deterministicamente, sem cerebro nenhum.
s6 = sessao_com({"titular_cpf": "03009596995", "titular_nome": "CLARISSA",
                 "telefone_contato": "48991071877", "endereco_numero": "112",
                 "problema_descricao": "curto circuito na tomada"})
tela_cpf = "Por favor, informe o CPF do titular da apolice"
r6 = IDS.handle_insurer_message(s6, tela_cpf)
respondeu = [t for t in (r6.get("transcript") or []) if t.get("direction") == "out"]
certo(r6.get("state") != "needs_human",
      "tela com o dado presente NAO trava")
certo(bool(respondeu) and "03009596995" in str(respondeu[-1].get("text") or ""),
      "🔴 e responde o CPF do caso, deterministicamente — "
      "o caminho rapido continua rapido")
certo("ultimo_passo_sem_dado" not in r6,
      "e nao marca empaque nenhum, porque nao houve")

print()
print("=" * 70)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 70)
sys.exit(1 if FAIL else 0)
