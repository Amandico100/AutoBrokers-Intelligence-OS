# -*- coding: utf-8 -*-
"""🔴 SPEC-121 F4b · ELETRICISTA DA FAMÍLIA HDI/YELUM, D10 (PORTÃO/RAIO) E A CHAVE — pelo MOTOR.

Telas: as da URA irmã (📊 yelum 315f0681 — o caminho de eletricista que fechou) e as da
chave (📊 yelum-auto, 3 + 2 telas). Sem dado pessoal: os slots são fictícios.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import corridor_playbooks as CP  # noqa: E402

OK = FAIL = 0
Q = chr(10)


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def resposta(ref, sub, tela, **slots):
    st = CP.match_ura_step(CP.get_playbook(ref), tela, subservice=sub)
    if not st:
        return None, None
    return st.get("step"), CP.render_reply(st, slots).get("reply")


TIPO = ("Agora, preciso que selecione abaixo a opção que corresponde com o seu problema:" + Q +
        "Botão 1: Falta de energia" + Q + "Botão 2: Problema elétrico")
ITEM = Q.join(["Selecione abaixo qual é o problema elétrico:", "Tomadas", "Interruptores", "Lâmpadas",
               "Reatores queimados", "Disjuntores/fusíveis", "Chuveiro",
               "Para troca de chuveiros ou resistências (não blindados)", "Torneira elétrica", "Voltar"])
COMODO = "{NOME} em qual ambiente está o chuveiro" + Q + "Botão 1: Suíte" + Q + "Botão 2: Banheiro social" + Q + "Botão 3: Área externa"

print("=" * 74)
print("[a] 🔴 HDI e YELUM eletricista: o caminho da URA irmã, do CASO")
print("=" * 74)
for cia in ("hdi", "yelum"):
    ref = CP.resolve_playbook_ref(cia, "residencial")
    passo, r = resposta(ref, "eletricista", TIPO, eletricista_tipo_opcao="problema elétrico no chuveiro")
    certo(r == "Problema elétrico", f"{cia}: tipo → 'Problema elétrico'", f"{passo} {r!r}")
    passo, r = resposta(ref, "eletricista", TIPO, eletricista_tipo_opcao="a casa inteira está sem luz")
    certo(r == "Falta de energia", f"{cia}: 'casa sem luz' → 'Falta de energia'", f"{passo} {r!r}")
    passo, r = resposta(ref, "eletricista", ITEM, eletricista_item_opcao="a tomada da sala queimou")
    certo(r == "Tomadas", f"{cia}: item → 'Tomadas' (rótulo da lista)", f"{passo} {r!r}")
    passo, r = resposta(ref, "eletricista", ITEM, eletricista_item_opcao="o disjuntor fica caindo")
    certo(r and r.startswith("Disjuntores"), f"{cia}: disjuntor → 'Disjuntores/fusíveis'", f"{r!r}")
    passo, r = resposta(ref, "eletricista", COMODO, eletricista_comodo="suíte")
    certo(r == "Suíte", f"{cia}: cômodo → 'Suíte'", f"{passo} {r!r}")
    falta = CP.missing_slots_for_subservice(ref, "eletricista", {})
    certo(all(s in falta for s in ("eletricista_tipo_opcao", "eletricista_item_opcao",
                                    "eletricista_comodo", "data_agendamento")),
          f"{cia}: o portão cobra tipo, item, cômodo e data ANTES", str(falta))
    passo, r = resposta(ref, "eletricista", ITEM, eletricista_item_opcao="não sei dizer")
    certo(r is None, f"🔴 CONTROLE {cia}: item que a lista não tem → sem chute", f"{r!r}")
passo, r = resposta(CP.resolve_playbook_ref("hdi", "residencial"), "encanador", COMODO, eletricista_comodo="suíte")
certo(passo != "eletricista_comodo", "🔴 CONTROLE: o passo do cômodo do eletricista não responde o encanador", str(passo))

print()
print("=" * 74)
print("[b] 🔴 D10: portão não é eletricista; raio é sinistro; falta de luz na rua")
print("=" * 74)
REF = CP.resolve_playbook_ref("hdi", "residencial")
for relato, codigo in (("o motor do portão eletrônico parou", "portao_nao_e_eletricista"),
                       ("caiu um raio e queimou o motor do portão", "sinistro_danos_eletricos"),
                       ("teve queda de energia e a geladeira queimou", "sinistro_danos_eletricos")):
    r = CP.antes_de_acionar(REF, "eletricista", {"problema_descricao": relato}) or {}
    certo(r.get("codigo") == codigo and r.get("ao_segurado"), f"{relato!r} → {codigo}", str(r))
r = CP.antes_de_acionar(REF, "eletricista", {"problema_descricao": "sem luz",
                                               "eletricista_tipo_opcao": "falta luz na rua toda"}) or {}
certo(r.get("codigo") == "falta_de_energia_na_rua", "falta de energia NA RUA → concessionária", str(r))
certo(CP.antes_de_acionar(REF, "eletricista", {"problema_descricao": "tomada da cozinha dando curto"}) is None,
      "🔴 CONTROLE: curto na tomada É eletricista (segue)")
# 🔴 CONSERTO ÚNICO (juiz P4 · red P6): a PALAVRA não é o OBJETO. 💭 relatos
#    ilustrativos (📊 0 no acervo de `messages`, medido pelo red team) — o que se
#    afirma é o comportamento do MOTOR (`antes_de_acionar`) sobre cada um.
for relato, codigo in (("o portão eletrônico não abre", "portao_nao_e_eletricista"),
                       ("não consigo abrir o portão, o motor não responde", "portao_nao_e_eletricista"),
                       ("o controle do portão parou", "portao_nao_e_eletricista"),
                       ("o portão automático travou no meio", "portao_nao_e_eletricista"),
                       ("uma descarga elétrica queimou a TV", "sinistro_danos_eletricos"),
                       ("teve um pico de energia e queimou a geladeira", "sinistro_danos_eletricos"),
                       ("caiu um raio perto de casa", "sinistro_danos_eletricos")):
    r = CP.antes_de_acionar(REF, "eletricista", {"problema_descricao": relato}) or {}
    certo(r.get("codigo") == codigo, f"{relato!r} → {codigo}", str(r))
for relato in ("a lâmpada do portão queimou", "a tomada perto do portão não funciona",
               "a luz da garagem ao lado do portão pisca", "a válvula de descarga está vazando",
               "teve um pico de energia e o disjuntor desarmou", "deu um surto e caiu o disjuntor"):
    r = CP.antes_de_acionar(REF, "eletricista", {"problema_descricao": relato})
    certo(r is None, f"🔴 CONTROLE: {relato!r} É eletricista (segue, não vai a pessoa)", str(r))
r = CP.antes_de_acionar(REF, "eletricista", {"problema_descricao": "caiu um raio e queimou o motor do portão"}) or {}
certo(CP.CODIGOS_ANTES_DE_ACIONAR.get(r.get("codigo")) == "sinistro"
      and __import__("app.services.claims_shadow", fromlist=["x"]).detectar_sinistro(r.get("motivo"))[0],
      "🔴 CONTROLE B1: raio continua SINISTRO — no código E na palavra do motivo (D10)", str(r))

print()
print("=" * 74)
print("[c] yelum/hdi auto chaveiro: a chave e o carro trancado, do CASO")
print("=" * 74)
CHAVE = Q.join(["O que aconteceu com a chave?", "Dentro do veículo", "Chave está trancada dentro do veículo",
                "Perda", "Perdeu a chave", "Quebrou", "A chave quebrou", "Outros", "Voltar", "Sair",
                "Encerra esse atendimento"])
TRANC = "O veículo está trancado?" + Q + "Botão 1: Sim" + Q + "Botão 2: Não" + Q + "Botão 3: Voltar"
for cia in ("yelum", "hdi"):
    ref = CP.resolve_playbook_ref(cia, "auto")
    for dito, rot in (("trancada dentro do veículo", "Dentro do veículo"), ("perdi a chave", "Perda"),
                      ("a chave quebrou", "Quebrou")):
        _p, r = resposta(ref, "chaveiro", CHAVE, chave_problema=dito)
        certo(r == rot, f"{cia}: {dito!r} → {rot!r}", f"{r!r}")
    _p, r = resposta(ref, "chaveiro", TRANC, veiculo_trancado="sim, trancado")
    certo(r == "Sim", f"{cia}: 'O veículo está trancado?' → do caso", f"{r!r}")
    certo("veiculo_trancado" in CP.missing_slots_for_subservice(ref, "chaveiro", {}),
          f"{cia}: o portão cobra se o carro está trancado")
yl = CP.get_playbook(CP.resolve_playbook_ref("yelum", "auto"))
st = CP.match_ura_step(yl, "O veículo está em uma garagem?" + Q + "Botão 1: Sim" + Q + "Botão 2: Não",
                       subservice="chaveiro")
certo((st or {}).get("step") == "garagem_do_caso",
      "a chave que VIRA guincho (📊 56bd78f7): a garagem sai do caso, não do passo fixo", str((st or {}).get("step")))

print()
print("=" * 74)
print(f"  {OK} verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
