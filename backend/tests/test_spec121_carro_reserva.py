# -*- coding: utf-8 -*-
"""🔴 SPEC-121 F5 · CARRO RESERVA — pelo MOTOR, com as telas REAIS (G7).

Fixture: `tests/fixtures/spec121_carro_reserva_telas.json` — só as telas da URA
(`direction=in`), mascaradas por `higiene_do_corpus.higienizar` (📊 `observed_events`,
29/09/2026: 10 sessões Yelum, 2 Tokio, 2 Azul; tirada a consulta de STATUS f984d8f0 e
2 telas com dígitos ou apresentação de pessoa). Nenhum dado pessoal: os slots são fictícios.

G7  as sessões Yelum do canal A que chegaram a "em análise" passam PELO MOTOR até o FIM
    CONTROLES: sem nº de sinistro → pessoa · sem cartão → pessoa · fora do horário →
    pessoa · motivo pane / reparo em outra → pessoa · CPF formatado sai só com dígitos
"""
from __future__ import annotations

import datetime as dt
import json
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


SESSOES = json.load(open(os.path.join(RAIZ, "tests", "fixtures", "spec121_carro_reserva_telas.json"),
                         encoding="utf-8"))
CASO = {"titular_cpf": "11122233344", "telefone_contato": "48999998888",
        "problema_descricao": "batida, o carro está na oficina", "veiculo_placa": "QQQ1A11",
        "apolice_numero": "1234567", "carro_reserva_motivo": "sinistro", "sinistro_numero": "12345678",
        "carro_reserva_condutor_nome": "Pessoa Teste", "carro_reserva_condutor_cpf": "111.222.333-44",
        "carro_reserva_cidade": "Cidade Teste", "carro_reserva_data_hora": "08/10 às 15h",
        "carro_reserva_telefone": "(48) 99999-8888", "carro_reserva_cnh_e_cartao": "sim, tem os dois"}
YL = CP.resolve_playbook_ref("yelum", "auto")
TERCA_10H = dt.datetime(2026, 9, 29, 10, 0)
ENV_OK = {"INSURER_CONTACT_YELUM_CARRO_RESERVA": "5500000000000"}


def replay(sessao, **troca):
    ref = CP.resolve_playbook_ref(sessao["seguradora"], "auto")
    s = IDS.new_dispatch_session(case_id="t121cr", company_id="co", playbook_ref=ref,
                                 subservice="carro_reserva", slots={**CASO, **troca})
    s["state"] = "ura"
    saidas = []
    for t in sessao["telas"]:
        if s.get("state") not in ("ura", "human_phase"):
            break
        n0 = len([x for x in s.get("transcript") or [] if x.get("direction") == "out"])
        s = IDS.handle_insurer_message(s, t["texto"])
        saidas += [x.get("text") for x in (s.get("transcript") or [])
                   if x.get("direction") == "out"][n0:]
    return s, saidas


def sessao(sid):
    return next(x for x in SESSOES if x["sessao"] == sid)


print("=" * 74)
print("[G7] 🔴 YELUM canal A: as sessões reais que chegaram a 'em análise', pelo MOTOR")
print("=" * 74)
FIM_A = ["0e9eace2", "870ab018", "19187f08", "4d5bd779", "77a1cbaf"]
for sid in FIM_A:
    s, saidas = replay(sessao(sid))
    certo(s.get("state") == "encaminhado" and "3 horas úteis" in str(
        (s.get("referral") or {}).get("client_message")),
        f"{sid}: chega ao FIM ('em análise') e o segurado ouve '3 horas úteis'",
        f"state={s.get('state')!r} reason={s.get('reason')!r}")
    certo("11122233344" in saidas and "111.222.333-44" not in saidas,
          f"{sid}: 🔴 o CPF de quem retira sai SÓ com dígitos", str([x for x in saidas if x][:3]))
    certo("15" in saidas, f"{sid}: diárias = 15 (default justificado) sem limite no caso")
s, saidas = replay(sessao("77a1cbaf"), carro_reserva_diarias="30")
certo("30" in saidas and "15" not in saidas, "CR4: o limite do PLANO vence o default quando o caso o traz")

print()
print("=" * 74)
print("[CONTROLES] o que vai a uma PESSOA — pelo motor e pelo portão de antes")
print("=" * 74)
s, _ = replay(sessao("c0c3c694"), carro_reserva_motivo="sinistro")
certo(s.get("state") == "needs_human" and str(s.get("reason")).startswith("exige_documento:"),
      "canal B, ramo 'Reparo outra Seguradora': o PDF obrigatório → pessoa, com motivo",
      f"{s.get('state')!r} {s.get('reason')!r}")
s, _ = replay(sessao("20d9d87c"))
certo(s.get("state") == "needs_human" and str(s.get("reason")).startswith("fora_do_horario:"),
      "'nenhum especialista disponível… 09h às 17h' (a sessão das 20h) → pessoa, com motivo",
      f"{s.get('state')!r} {s.get('reason')!r}")
s, _ = replay(sessao("77a1cbaf"), carro_reserva_motivo="pane mecânica")
certo(s.get("state") == "needs_human", "motivo PANE: o motor não responde o motivo (sem_chute)",
      f"{s.get('state')!r} {s.get('reason')!r}")

A = CP.antes_de_acionar
certo(A(YL, "carro_reserva", CASO, agora=TERCA_10H, env=ENV_OK) is None,
      "CONTROLE: caso completo, terça 10h, canal configurado → segue")
certo(A(YL, "carro_reserva", {**CASO, "sinistro_numero": ""}, agora=TERCA_10H, env=ENV_OK) is None
      and "sinistro_numero" in CP.missing_slots_for_subservice(YL, "carro_reserva", {}),
      "CONTROLE: nº do sinistro VAZIO → o portão cobra (o agente pergunta), não pessoa")
for troca, codigo in (({"sinistro_numero": "não tenho"}, "carro_reserva_sem_numero_do_processo"),
                      ({"carro_reserva_cnh_e_cartao": "não tenho cartão"}, "carro_reserva_sem_cartao"),
                      ({"carro_reserva_motivo": "pane mecânica"}, "carro_reserva_motivo"),
                      ({"carro_reserva_motivo": "reparo em outra seguradora"}, "carro_reserva_motivo")):
    r = A(YL, "carro_reserva", {**CASO, **troca}, agora=TERCA_10H, env=ENV_OK) or {}
    certo(r.get("codigo") == codigo and r.get("ao_segurado"), f"{troca} → {codigo}", str(r))
for quando, rot in ((dt.datetime(2026, 9, 29, 20, 0), "terça 20h"),
                    (dt.datetime(2026, 10, 3, 10, 0), "sábado 10h")):
    r = A(YL, "carro_reserva", CASO, agora=quando, env=ENV_OK) or {}
    certo(r.get("codigo") == "carro_reserva_fora_do_horario", f"CR5: {rot} → não aciona", str(r))
r = A(YL, "carro_reserva", CASO, agora=TERCA_10H, env={}) or {}
certo(r.get("codigo") == "carro_reserva_canal_desligado",
      "🔴 sem o número do canal 'Segurado e Terceiros' configurado → pessoa (nunca o da assistência)")
for cia in ("allianz", "hdi", "porto", "zurich", "bradesco", "mapfre"):
    ref = CP.resolve_playbook_ref(cia, "auto")
    r = A(ref, "carro_reserva", CASO, agora=TERCA_10H, env=ENV_OK) or {}
    certo(r.get("codigo") == "carro_reserva_por_desenho", f"CR9: {cia} → pessoa por desenho")

print()
print("=" * 74)
print("[B1] 🔴 o MOTIVO não diz 'sinistro' — e leva o CÓDIGO que o handoff lê (red team B1)")
print("=" * 74)
# Todos os motivos que `antes_de_acionar` escreve de VERDADE (motor, não lista à mão):
# as 6 seguradoras por desenho (Zurich por SINISTRO e por PANE), e cada portão da Yelum.
from app.services.claims_shadow import detectar_sinistro  # noqa: E402
PEDIDOS = [(CP.resolve_playbook_ref(c, "auto"), m, dict(CASO, carro_reserva_motivo=m), {}, TERCA_10H)
           for c in ("allianz", "hdi", "porto", "zurich", "bradesco", "mapfre")
           for m in ("sinistro", "pane mecânica")]
PEDIDOS += [(YL, k, {**CASO, **t}, e, q) for k, t, e, q in (
    ("sem nº", {"sinistro_numero": "não tenho"}, ENV_OK, TERCA_10H),
    ("sem cartão", {"carro_reserva_cnh_e_cartao": "não"}, ENV_OK, TERCA_10H),
    ("pane", {"carro_reserva_motivo": "pane depois do sinistro, bati o carro"}, ENV_OK, TERCA_10H),
    ("20h", {}, ENV_OK, dt.datetime(2026, 9, 29, 20, 0)),
    ("canal", {}, {}, TERCA_10H))]
vistos = set()
for ref, rot, slots, env, quando in PEDIDOS:
    r = A(ref, "carro_reserva", slots, agora=quando, env=env) or {}
    vistos.add(r.get("codigo"))
    reason = CP.motivo_com_codigo(r) if r else ""
    certo(r and not detectar_sinistro(r["motivo"])[0] and not detectar_sinistro(reason)[0],
          f"{ref.split('-')[0]}/{rot}: {r.get('codigo')} → o detector de sinistro NÃO casa o motivo",
          f"motivo={r.get('motivo')!r}")
    cod, limpo = CP.ler_codigo_antes_de_acionar(reason)
    certo(cod == r.get("codigo") and limpo == r.get("motivo")
          and CP.CODIGOS_ANTES_DE_ACIONAR.get(cod) == "pedido_de_ajuda"
          and "[" not in limpo and "_" not in limpo,
          f"   o código volta do reason e o tipo é pedido_de_ajuda ({cod})", f"{cod!r} {limpo!r}")
certo(vistos >= {"carro_reserva_por_desenho", "carro_reserva_sem_numero_do_processo",
                 "carro_reserva_sem_cartao", "carro_reserva_motivo",
                 "carro_reserva_fora_do_horario", "carro_reserva_canal_desligado"},
      "os SEIS códigos de carro reserva foram exercitados pelo motor", str(sorted(vistos)))
r = A(YL, "carro_reserva", CASO, agora=TERCA_10H, env={}) or {}
certo("INSURER_CONTACT" not in r.get("motivo", "") and "Yelum" in r.get("motivo", ""),
      "red P4: o motivo do canal desligado fala em língua de gente (sem o nome da variável)",
      r.get("motivo"))
certo(CP.ler_codigo_antes_de_acionar("[antes_de_acionar:inventado] x") == (None, "[antes_de_acionar:inventado] x")
      and CP.ler_codigo_antes_de_acionar("cliente pediu pessoa") == (None, "cliente pediu pessoa"),
      "🔴 CONTROLE: código fora da tabela e motivo comum NÃO são reconhecidos (texto intacto)")

print()
print("=" * 74)
print("[CR8] TOKIO e AZUL: o LINK da seguradora, capturado da conversa")
print("=" * 74)
for sid in ("c1a67b4a", "9ec91e2b", "868eb8cb"):
    s, _ = replay(sessao(sid))
    ref = dict(s.get("referral") or {})
    certo(s.get("state") == "encaminhado" and ref.get("link", "").startswith("http")
          and "CNH" in str(ref.get("client_message")),
          f"{sid}: encaminhado com o link e a lista do que levar",
          f"{s.get('state')!r} {s.get('reason')!r} link={ref.get('link')!r}")
st = CP.detect_referral_step(CP.get_playbook(CP.resolve_playbook_ref("azul", "auto")),
                             "Fale com um dos nossos especialistas, clicando no link abaixo", "guincho")
certo(st is None, "🔴 CONTROLE: o encaminhamento do carro reserva NÃO vale num guincho da Azul")

print()
print("=" * 74)
print(f"  {OK} verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
