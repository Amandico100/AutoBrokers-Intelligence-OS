# -*- coding: utf-8 -*-
"""🔴 GA-2 + GA-3 (SPEC-EXTRA-001.4) · MENU NUMERADO RECEBE NÚMERO — PELO MOTOR, NA TELA REAL.

📊 10/09/2026, sessão Allianz `432614de`: o menu "Qual seguro deseja utilizar?
*1 - Residencial:* … *2 - Condomínio:* … *3 - Empresarial:* …" recebeu
"residência", e a URA respondeu "Opção inválida." duas vezes. O passo interpolava
o slot CRU (`render_reply`), e nada convertia a palavra no dígito.

GA-2 afirma o comportamento do MOTOR (`handle_insurer_message`) sobre as telas do
acervo — a sessão de 10/09 é lida PELO ID. GA-3 afirma o dialeto do parser: a
regex `_NUMERADA` sozinha acha ZERO opções no texto cru (o negrito vem antes do
dígito) e `parse_options` acha TRÊS — o corredor tem de usar o segundo. E o ramo
de PALPITE do parser (listas nuas) nunca vira menu numerado.

⚠️ A sessão de 10/09 está em `allianz-auto.jsonl`, não no residencial: o
classificador de ramo leu o "1" digitado pela atendente como resposta ao cardápio
(pendência registrada no relatório). O texto é o mesmo e é lido pelo ID.
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import cartographer as C  # noqa: E402
from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import insurer_dispatch_service as D  # noqa: E402

OK = FAIL = 0
CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")
REF = "allianz-residencial-whatsapp@v1"


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


SESSAO_1009 = [t["text"] for t in telas("allianz-auto") if t["session_id"].startswith("432614de")]
MENU_1009 = next((t for t in SESSAO_1009 if t.startswith("Qual seguro deseja utilizar?")), "")

SLOTS = {"titular_cpf": "11122233344", "endereco_numero": "100", "telefone_contato": "48999998888",
         "problema_descricao": "tomadas sem energia", "periodo_preferido": "tarde",
         "risco_confirmado_sem_fumaca": "sim"}


def sessao(**extra):
    s = D.new_dispatch_session(case_id="ga2", company_id="co-ga2", playbook_ref=REF,
                               subservice="eletricista", slots={**SLOTS, **extra})
    s["state"] = "ura"
    return s


def saidas(s):
    return [t for t in s["transcript"] if t["direction"] == "out"]


print("=" * 74)
print("[0] o acervo tem a sessão de 10/09, pelo ID")
print("=" * 74)
checar(len(SESSAO_1009) >= 5 and MENU_1009,
       "📊 a sessão `432614de` está no corpus, com o menu do ramo",
       f"{len(SESSAO_1009)} telas")
checar("Opção inválida." in SESSAO_1009 and "Vamos tentar novamente." in SESSAO_1009,
       "📊 e com a recusa real, em duas bolhas, SEM repetir o menu")

print()
print("=" * 74)
print("[1] GA-3 · o parser lê o texto certo, e o palpite fica fora")
print("=" * 74)
checar(len(list(C._NUMERADA.finditer(MENU_1009))) == 0,
       "🔴 a regex `_NUMERADA` sozinha, no texto CRU, acha ZERO opções (o `*` vem antes do dígito)")
checar(len(C.parse_options(MENU_1009)) == 3,
       "🔴 `parse_options` acha TRÊS — ele tira o negrito antes", f"{C.parse_options(MENU_1009)}")
checar(D.opcoes_numeradas(MENU_1009) == [("1", "Residencial"), ("2", "Condomínio"), ("3", "Empresarial")],
       "o corredor lê o menu pelo parser do Atlas", f"{D.opcoes_numeradas(MENU_1009)}")
PROSA = next((t["text"] for t in telas("porto-auto")
              if t["text"].startswith("Como eu posso te ajudar?")
              and len(C.parse_options(t["text"])) >= 2), "")
checar(PROSA and not any(C.numero_da_opcao(x) for x in C.parse_options(PROSA)),
       "📊 CONTROLE: o PALPITE do parser acha rótulos numa tela de lista da porto")
checar(PROSA and D.opcoes_numeradas(PROSA) == [],
       "🔴 e o corredor NÃO a trata como menu numerado — a palavra da porto sai inteira")

print()
print("=" * 74)
print("[2] GA-2 · o motor responde o NÚMERO ao menu real de 10/09")
print("=" * 74)
for valor, digito, rotulo in (("residência", "1", "Residencial"),
                              ("Condomínio", "2", "Condomínio"),
                              ("empresarial", "3", "Empresarial")):
    s = D.handle_insurer_message(sessao(qual_seguro_opcao=valor), MENU_1009)
    out = saidas(s)
    checar(out and out[-1]["text"] == digito and s["state"] == "ura",
           f"🔴 {valor!r} (a palavra da atendente) sai como {digito!r}",
           f"saiu {[o['text'] for o in out]} · estado {s['state']}")
    tecla = (out[-1].get("tecla") if out else None) or {}
    checar(tecla.get("origem") == "menu_lido" and tecla.get("rotulo") == rotulo,
           f"   e o transcript diz de onde veio: menu_lido · {rotulo}", f"{tecla}")

# o dígito que já é dígito sai como está (a derivação/o subserviço mandam)
s = D.handle_insurer_message(sessao(qual_seguro_opcao="2"), MENU_1009)
checar([o["text"] for o in saidas(s)] == ["2"], "tecla que já é dígito sai como está")

print()
print("=" * 74)
print("[3] GA-2 · o que NÃO sai — e para onde vai")
print("=" * 74)
s = D.handle_insurer_message(sessao(), MENU_1009)
checar(not saidas(s) and s["state"] == "needs_human" and s["reason"] == "ramo_indeterminado",
       "🔴 ramo vazio: NADA sai, e a tela vai a uma pessoa (`ramo_indeterminado`)",
       f"estado {s['state']} · motivo {s.get('reason')} · saiu {[o['text'] for o in saidas(s)]}")
checar("ramo_indeterminado" in D._MOTIVOS_EM_PORTUGUES
       and "tecla_ambigua" in D._MOTIVOS_EM_PORTUGUES,
       "e o dossiê diz o motivo em português")
s = D.handle_insurer_message(sessao(qual_seguro_opcao="casa de praia"), MENU_1009)
checar(not saidas(s) and s.get("reason") == "ramo_indeterminado",
       "🔴 palavra que não é opção, no RAMO: nada sai, pessoa decide", f"{s.get('reason')}")
s = D.handle_insurer_message(sessao(qual_seguro_opcao="residencial condominio"), MENU_1009)
checar(not saidas(s) and s.get("reason") == "tecla_ambigua",
       "🔴 palavra que casa DUAS opções: nada sai (`tecla_ambigua`)", f"{s.get('reason')}")

# tecla de NAVEGAÇÃO vazia numa tela reversível: o Cérebro assume, com as opções (D-E0014-01)
pb = CP.get_playbook(REF)
PASSO_IDADE = next(p for p in pb["ura_steps"] if p.get("reply") == "{idade_aparelho_opcao}")
TELA_IDADE = next((t["text"] for t in telas("allianz-residencial")
                   if (CP.match_ura_step(pb, t["text"], subservice="eletrodomesticos") or {}).get("step")
                   == PASSO_IDADE["step"]), "")
checar(TELA_IDADE and len(D.opcoes_numeradas(TELA_IDADE)) >= 2,
       "📊 o acervo tem a tela real do passo que pede `idade_aparelho_opcao`")
s = sessao(qual_seguro_opcao="1")
s["subservice"] = "eletrodomesticos"
s = D.handle_insurer_message(s, TELA_IDADE)
checar(not saidas(s) and s["state"] == "human_phase"
       and (s.get("falta_para_a_ura") or {}).get("slot") == "idade_aparelho_opcao",
       "🔴 tecla vazia numa tela reversível: nada sai às cegas, e o Cérebro é chamado com o nome dela",
       f"estado {s['state']} · falta {s.get('falta_para_a_ura')} · saiu {[o['text'] for o in saidas(s)]}")
prompt = D.build_human_phase_messages(s, TELA_IDADE)["user"]
checar("responda SÓ com o NÚMERO" in prompt and all(f"{d} - " in prompt for d, _ in D.opcoes_numeradas(TELA_IDADE)),
       "   e o prompt do Cérebro traz as opções NUMERADAS da tela")

print()
print("=" * 74)
print("[4] CONTROLE · tela sem número: a palavra sai inteira (é a porto)")
print("=" * 74)
pbp = CP.get_playbook("porto-auto-whatsapp@v1")
TELA_QUANDO = next((t["text"] for t in telas("porto-auto")
                    if (CP.match_ura_step(pbp, t["text"]) or {}).get("step") == "menu_quando"), "")
sp = D.new_dispatch_session(case_id="ga2p", company_id="co-ga2", playbook_ref="porto-auto-whatsapp@v1",
                            subservice="guincho", slots={"menu_quando_opcao": "Agora"})
sp["state"] = "ura"
sp = D.handle_insurer_message(sp, TELA_QUANDO)
checar(TELA_QUANDO and [o["text"] for o in saidas(sp)] == ["Agora"],
       "🔴 CONTROLE: na lista da porto, a palavra sai INTEIRA — a camada 1 só age em menu numerado",
       f"saiu {[o['text'] for o in saidas(sp)]} · estado {sp['state']}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
