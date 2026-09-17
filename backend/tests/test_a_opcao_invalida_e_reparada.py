# -*- coding: utf-8 -*-
"""🔴 GB-1 + GB-2 + GB-3 (SPEC-EXTRA-001.4) · "OPÇÃO INVÁLIDA" É REPARADA PELO MOTOR.

📊 10/09/2026, sessão Allianz `432614de`: depois de uma palavra num menu numerado,
a URA mandou "Opção inválida." e "Vamos tentar novamente." — em duas bolhas, SEM
repetir o menu. Só o Sentinela podia agir, e ele gastou as 2 tentativas da SESSÃO
inteira às 14:14; o resto do atendimento correu sem rede.

GB-1  o motor repara uma vez por tela, com o dígito do menu PENDENTE, sem gastar
      tentativa do Sentinela — e nunca reenvia um dígito recusado.
GB-2  o Sentinela conta tentativas POR TELA, com teto de SESSÃO (`_sentinela_recover`).
GB-3  o Cérebro recebe a resposta recusada e as opções numeradas no prompt.

⛔ Nada sai da máquina: o LLM, o WhatsApp, o dossiê e o feed são dublês.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import insurer_dispatch_service as D  # noqa: E402
from app.tasks import dispatch_watchdog as W  # noqa: E402

OK = FAIL = 0
CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")
REF = "allianz-residencial-whatsapp@v1"
PB = CP.get_playbook(REF)


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def telas(nome):
    with open(os.path.join(CORPUS, f"{nome}.jsonl"), encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh]


RES = [t["text"] for t in telas("allianz-residencial")]
SESSAO_1009 = [t["text"] for t in telas("allianz-auto") if t["session_id"].startswith("432614de")]
RECUSA = next((t for t in SESSAO_1009 if t == "Opção inválida."), "")
DE_NOVO = next((t for t in SESSAO_1009 if t == "Vamos tentar novamente."), "")
# o subserviço da sessão decide que passos existem: no ELETRICISTA, o menu de
# eletrodoméstico não tem passo — quem responde é o Cérebro (o caminho a provar).
SUB = "eletricista"
ELETRO = next((t for t in RES if t.startswith("Qual eletrodoméstico precisa de conserto")
               and CP.match_ura_step(PB, t, subservice=SUB) is None), "")
SEM_MENU = next((t for t in RES if not D.opcoes_numeradas(t) and CP.match_ura_step(PB, t, subservice=SUB) is None
                 and not D.detectar_recusa_de_menu(t) and len(t) > 40), "")


def sessao():
    s = D.new_dispatch_session(
        case_id="gb", company_id="co-gb", playbook_ref=REF, subservice=SUB,
        slots={"titular_cpf": "11122233344", "endereco_numero": "100", "telefone_contato": "48999998888",
               "problema_descricao": "geladeira parou", "periodo_preferido": "tarde",
               "qual_seguro_opcao": "1", "idade_aparelho_opcao": "1", "aparelho_marca": "x"})
    s["state"] = "ura"
    return s


def saidas(s):
    return [t for t in s["transcript"] if t["direction"] == "out"]


print("=" * 74)
print("[0] as telas vêm do acervo")
print("=" * 74)
checar(RECUSA and DE_NOVO, "📊 a recusa de 10/09 está no corpus, pelo ID da sessão, em duas bolhas")
checar(ELETRO and len(D.opcoes_numeradas(ELETRO)) >= 2,
       "📊 o menu numerado de eletrodoméstico não casa passo nenhum — quem responde é o Cérebro")
checar(bool(SEM_MENU), "📊 e há tela real sem menu numerado, para a linha de controle")

print()
print("=" * 74)
print("[1] GB-1 · a palavra recusada vira o dígito — uma vez, sem gastar o Sentinela")
print("=" * 74)
s = D.handle_insurer_message(sessao(), ELETRO)
checar(s["state"] == "human_phase" and not saidas(s), "o menu sem passo vai ao Cérebro, calado")
s = D.reply_human_phase(s, "Linha Branca")          # o Cérebro respondeu com a PALAVRA
pend = s.get("menu_pendente") or {}
checar(pend.get("nossa_resposta") == "Linha Branca" and len(pend.get("opcoes") or []) >= 2,
       "a saída grava o menu que ela respondeu (`menu_pendente`)", f"{pend}")
antes = s.get("sentinela_attempts")
s = D.handle_insurer_message(s, RECUSA)
out = saidas(s)
checar(out[-1]["text"] == "1" and out[-1].get("step") == "reparo_opcao_invalida",
       "🔴 'Opção inválida.' → o motor reenvia '1' (Linha Branca), sem Sentinela",
       f"saídas {[o['text'] for o in out]}")
checar((out[-1].get("tecla") or {}).get("origem") == "menu_lido",
       "   e o transcript diz: menu_lido, reparando 'Linha Branca'", f"{out[-1].get('tecla')}")
checar(s.get("sentinela_attempts") == antes, "🔴 o reparo NÃO consome tentativa do Sentinela",
       f"{antes} -> {s.get('sentinela_attempts')}")
n = len(saidas(s))
s = D.handle_insurer_message(s, DE_NOVO)
checar(len(saidas(s)) == n, "a segunda bolha ('Vamos tentar novamente.') não gera outra resposta")
s = D.handle_insurer_message(s, RECUSA)
checar(len(saidas(s)) == n,
       "🔴 ③ a URA recusou também o dígito: ele NUNCA é reenviado", f"{[o['text'] for o in saidas(s)]}")
checar((s.get("ultima_resposta_recusada") or {}).get("nossa_resposta") == "1",
       "   e a recusa fica registrada para o Cérebro", f"{s.get('ultima_resposta_recusada')}")

print()
print("=" * 74)
print("[2] GB-3 · o Cérebro sabe que foi recusado, e vê os números")
print("=" * 74)
prompt = D.build_human_phase_messages(s, RECUSA)["user"]
checar("RECUSADA" in prompt and "`1`" in prompt,
       "🔴 o prompt diz qual resposta foi recusada (ultima_resposta_recusada)")
checar("1 - Linha Branca" in prompt and "responda SÓ com o NÚMERO" in prompt,
       "🔴 e traz as opções do menu pendente, pedindo o NÚMERO (tela_com_menu_pendente)")
limpo = D.build_human_phase_messages(sessao(), SEM_MENU)["user"]
checar("RECUSADA" not in limpo and "OPÇÕES NUMERADAS" not in limpo,
       "CONTROLE: sem recusa e sem menu, o prompt não inventa o bloco")

print()
print("=" * 74)
print("[3] GB-1 · ④ uma vez por tela · ② sem menu pendente não há reparo")
print("=" * 74)
s = D.handle_insurer_message(sessao(), ELETRO)
s = D.reply_human_phase(s, "Linha Branca")
s = D.handle_insurer_message(s, RECUSA)                       # 1º reparo
s = D.handle_insurer_message(s, ELETRO)                       # a URA repete o MESMO menu
s = D.reply_human_phase(s, "Linha Branca")                    # e o Cérebro repete a palavra
s = D.handle_insurer_message(s, RECUSA)
checar([o["text"] for o in saidas(s)] == ["Linha Branca", "1", "Linha Branca"],
       "🔴 ④ a mesma tela não é reparada duas vezes", f"{[o['text'] for o in saidas(s)]}")
s = D.handle_insurer_message(sessao(), SEM_MENU)
s = D.reply_human_phase(s, "alguma resposta")
s = D.handle_insurer_message(s, RECUSA)
checar([o["text"] for o in saidas(s)] == ["alguma resposta"] and not s.get("menu_pendente"),
       "🔴 CONTROLE ②: a resposta era a uma tela SEM menu numerado — nada é reparado")

print()
print("=" * 74)
print("[4] a âncora de recusa é a MEDIDA — e não pega encerramento nem menu")
print("=" * 74)
todas = [t["text"] for n in ("allianz-auto", "allianz-residencial", "porto-auto", "azul-auto",
                             "mapfre-auto", "hdi-auto", "bradesco-auto") for t in telas(n)]
recusas = {t for t in todas if D.detectar_recusa_de_menu(t)}
checar(RECUSA in recusas and len(recusas) >= 3, f"📊 {len(recusas)} redações de recusa do acervo são reconhecidas")
fecha = [t for t in todas if "encerrar a conversa" in t.lower()]
checar(fecha and not any(D.detectar_recusa_de_menu(t) for t in fecha),
       "🔴 CONTROLE: 'não consegui entender e vou precisar encerrar a conversa' NÃO é recusa reparável",
       f"{len(fecha)} telas de encerramento")
menus = [t for t in todas if "selecione uma das op" in t.lower() and "entendi" not in t.lower()]
checar(menus and not any(D.detectar_recusa_de_menu(t) for t in menus),
       "CONTROLE: menu que pede para 'selecionar uma das opções' não é recusa", f"{len(menus)} menus")

print()
print("=" * 74)
print("[5] GB-2 · o Sentinela conta POR TELA, com teto de SESSÃO")
print("=" * 74)


class _Wa:
    def __init__(self):
        self.envios = []

    def send_message(self, telefone, texto, integracao):
        self.envios.append(texto)


async def _um(*_a, **_k):
    return "1"


async def _nao(*_a, **_k):
    return False


async def _nada(*_a, **_k):
    return None


W._adaptive_reply = _um
W._entregar_dossie_com_marcador = _nao
W._avisar_o_segurado = _nao
try:
    import app.services.activity_log as _AL  # noqa: E402
    _AL.log_activity = _nada
except Exception:  # noqa: BLE001 — sem o módulo, o `except` do Sentinela cobre
    pass

MENUS = []
for t in RES:
    if len(D.opcoes_numeradas(t)) >= 2 and t not in MENUS:
        MENUS.append(t)
checar(len(MENUS) >= W.MAX_TENTATIVAS_NA_SESSAO + 1,
       f"📊 o acervo tem {len(MENUS)} menus numerados distintos para a prova")


def _nova():
    return {"company_id": "co-gb2", "playbook_ref": REF, "state": "ura", "transcript": [],
            "slots": {}, "case_id": "gb2"}


def _chega(s, tela):
    s["transcript"].append({"direction": "in", "text": tela,
                            "at": datetime.now(timezone.utc).isoformat()})


def _sentinela(s):
    return asyncio.run(W._sentinela_recover("co-gb2", "5500000000000", s, _Wa(), object()))


s = _nova()
r = []
for tela in (MENUS[0], MENUS[0], MENUS[1]):
    _chega(s, tela)
    r.append(_sentinela(s))
checar(r == ["recovered", "recovered", "recovered"],
       "🔴 duas tentativas na tela A NÃO deixam a tela B sem rede", f"{r}")
_chega(s, MENUS[1])
r.append(_sentinela(s))
_chega(s, MENUS[1])
r.append(_sentinela(s))
checar(r[3:] == ["recovered", "handoff"] and s["state"] == "needs_human",
       "🔴 a 3ª tentativa na MESMA tela vai a uma pessoa", f"{r} · {s.get('state')}")
checar(sorted(s.get("tentativas_por_tela", {}).values()) == [2, 2],
       "   e a contagem é por tela", f"{s.get('tentativas_por_tela')}")

s = _nova()
r = []
for tela in MENUS[:W.MAX_TENTATIVAS_NA_SESSAO + 1]:
    _chega(s, tela)
    r.append(_sentinela(s))
checar(r[:-1] == ["recovered"] * W.MAX_TENTATIVAS_NA_SESSAO and r[-1] == "handoff",
       f"🔴 teto de SESSÃO: telas novas não renovam a rede para sempre ({W.MAX_TENTATIVAS_NA_SESSAO})",
       f"{r}")
checar(W.MAX_TENTATIVAS_POR_TELA < W.MAX_TENTATIVAS_NA_SESSAO,
       "o teto por tela é menor que o da sessão")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
