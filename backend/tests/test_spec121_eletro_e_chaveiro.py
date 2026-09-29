# -*- coding: utf-8 -*-
"""🔴 SPEC-121 F4 · ELETRODOMÉSTICOS, CHAVEIRO, RECUSA E GARAGEM — pelo MOTOR.

Telas do acervo (BLOCO 0 §8, `observed_events` 29/09/2026), sem dado pessoal:
  (a) allianz: o aparelho do segurado vira a TECLA da tela (antes: "1" e "15" fixos)
  (b) hdi chaveiro: a bolha de cobertura com a palavra "sinistro" não passa o caso
  (c) allianz: as frases de RECUSA passam o caso com o motivo `recusa_de_cobertura`
  (d) yelum bateria: `local_situacao` é cobrado antes
  (e) D7: bradesco e zurich respondem a garagem pelo CASO
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import insurer_dispatch_service as IDS  # noqa: E402

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


def sessao(ref, sub, **slots):
    base = {"titular_cpf": "11122233344", "telefone_contato": "48999998888",
            "endereco_numero": "100", "problema_descricao": "parou", "pessoa_no_local": "Cliente",
            "veiculo_placa": "QQQ1111", "local_atual": "Rua X, 100, Florianópolis, SC"}
    base.update(slots)
    s = IDS.new_dispatch_session(case_id="t121", company_id="co", playbook_ref=ref,
                                 subservice=sub, slots=base)
    s["state"] = "ura"
    return s


def responder(s, tela):
    antes = len([t for t in s.get("transcript") or [] if t.get("direction") == "out"])
    s = IDS.handle_insurer_message(s, tela)
    saidas = [t.get("text") for t in s.get("transcript") or [] if t.get("direction") == "out"]
    return s, (saidas[antes:] or [None])[-1]


AL = "allianz-residencial-whatsapp@v1"
CATEGORIA = ("Qual eletrodoméstico precisa de conserto ?" + Q + Q + "*1 -* Linha Branca (Microondas; "
             "Fogão; Forno; Cooktop; Frigobar; Adega; Filtro de água; Lavadora de louças; Coifa e "
             "exaustor de ar; Máquina de Lavar e secar roupas)" + Q + "*2 -* Ar Condicionado" + Q +
             "*3 -* Geladeira, Freezer e outros" + Q + "*4 -* Voltar")
LISTA = ("Selecione o eletrodoméstico que precisa de conserto ?" + Q + Q + Q.join(
    f"*{i} -* {r}" for i, r in enumerate(
        ["Geladeira", "Freezer", "Frigobar", "Adega", "Micro-ondas", "Fogão", "Forno", "Cooktop",
         "Filtro/Purificador de água", "Lavadora de louças", "Coifa/depurador de ar",
         "Exaustor de ar", "Secadora de roupas", "Máquina de Lavar roupas", "Outros"], 1)))

print("=" * 74)
print("[a] 🔴 allianz: o APARELHO do segurado vira a tecla — nunca '15' fixo")
print("=" * 74)
for aparelho, cat, lst in (("fogão", "1", "6"), ("micro-ondas", "1", "5"), ("lava-louças", "1", "10"),
                           ("secadora", "1", "13"), ("geladeira", "3", None), ("televisão", "3", None)):
    s, r1 = responder(sessao(AL, "eletrodomesticos", eletrodomestico_aparelho=aparelho), CATEGORIA)
    certo(r1 == cat, f"{aparelho!r}: categoria → {cat!r}", f"respondeu {r1!r} state={s.get('state')}")
    if lst:
        s, r2 = responder(s, LISTA)
        certo(r2 == lst, f"{aparelho!r}: lista → {lst!r}", f"respondeu {r2!r} state={s.get('state')}")
s, r = responder(sessao(AL, "eletrodomesticos", eletrodomestico_aparelho="televisão"), LISTA)
certo(r == "15", "aparelho que a lista não nomeia → a tecla 'Outros' DA TELA", f"respondeu {r!r}")
s, r = responder(sessao(AL, "maquina_de_lavar", eletrodomestico_categoria_opcao="1",
                        eletrodomestico_opcao="14"), LISTA)
certo(r == "14", "🔴 CONTROLE: `maquina_de_lavar` continua com a tecla da ROTA (14)", f"respondeu {r!r}")
falta = CP.missing_slots_for_subservice(AL, "eletrodomesticos", {})
certo(all(x in falta for x in ("eletrodomestico_aparelho",)),
      "o portão cobra o aparelho ANTES de acionar", str(falta))

print()
print("=" * 74)
print("[b] hdi chaveiro: a bolha de cobertura não é relato de sinistro")
print("=" * 74)
HDI = "hdi-residencial-whatsapp@v1"
BOLHA = ("Garante os custos com mão de obra, quando for impossível o acesso ao interior da residência "
         "segurada, em virtude de problemas com as chaves ou fechadura: quebra, perda, emperramento, ou "
         "ainda em decorrência de sinistro devidamente coberto pela apólice de seguro (arrombamento, "
         "roubo ou furto). A Seguradora providenciará o envio de um chaveiro. Este serviço está limitado "
         "a portas ou portões principais para acesso ao interior da residência do Segurado.")
s, r = responder(sessao(HDI, "chaveiro", chaveiro_porta_opcao="Porta principal"), BOLHA)
certo(s.get("state") != "needs_human" and r is None, "a bolha é aviso: nada sai e ninguém é chamado",
      f"state={s.get('state')!r} reason={s.get('reason')!r} r={r!r}")
PORTA = ("Em qual destas opções está localizado o problema?" + Q + "Botão 1: Porta interna" + Q +
         "Botão 2: Porta principal" + Q + "Botão 3: Voltar")
st = CP.match_ura_step(CP.get_playbook(HDI), PORTA, subservice="chaveiro")
certo((st or {}).get("reply") == "{chaveiro_porta_opcao}" and "chaveiro_porta_opcao" in
      CP.missing_slots_for_subservice(HDI, "chaveiro", {}),
      "'Porta interna / Porta principal' sai do SEGURADO (cobrado antes de acionar)", str(st))
certo(CP.detect_handoff_trigger(CP.get_playbook(HDI), "Houve um sinistro no imóvel?") is not None,
      "🔴 CONTROLE: 'sinistro' fora da bolha continua passando o caso")

print()
print("=" * 74)
print("[c] 🔴 allianz: a RECUSA de cobertura passa o caso, com o motivo dela")
print("=" * 74)
for frase in ("Sua apólice não contempla o serviço desejado.",
              "Infelizmente, não cobrimos conserto de eletrodomésticos no seu plano ESSENCIAL.",
              "Cláusula de Assistência Não Contratada",
              "Não cobrimos esse serviço dentro da sua apólice infelizmente.",
              "A apólice não contempla desentupimento de chuveiro",
              "Sem cobertura, infelizmente. Se quiser posso indicar um prestador para que siga particular?"):
    s, r = responder(sessao(AL, "encanador"), frase)
    certo(s.get("state") == "needs_human" and str(s.get("reason")).startswith("recusa_de_cobertura:"),
          f"{frase[:52]!r}", f"state={s.get('state')!r} reason={s.get('reason')!r}")
frase = IDS.motivo_em_portugues("recusa_de_cobertura:x")
certo("não cobre" in frase.lower() and "_" not in frase, "o motivo sai em português", frase)
s, r = responder(sessao(AL, "encanador"), "Sua solicitação está coberta pela apólice.")
certo(s.get("state") != "needs_human" or not str(s.get("reason")).startswith("recusa"),
      "🔴 CONTROLE: 'coberta pela apólice' não é recusa", f"reason={s.get('reason')!r}")

print()
print("=" * 74)
print("[d] yelum bateria: o LOCAL é cobrado antes")
print("=" * 74)
certo("local_situacao" in CP.missing_slots_for_subservice(CP.resolve_playbook_ref("yelum", "auto"), "bateria", {}),
      "`local_situacao` entra no portão da bateria da Yelum")

print()
print("=" * 74)
print("[e] 🔴 D7: bradesco e zurich respondem a garagem pelo CASO")
print("=" * 74)
BR = ("Certo, então vamos enviar um reboque. Me diz: o veículo está em garagem subsolo?" + Q +
      "Botão 1: Sim" + Q + "Botão 2: Não")
ZU = "O veículo está em garagem subsolo ou elevada?" + Q + Q + "*1* - Sim" + Q + "*2* - Não"
for ref, tela, sub_sim, sub_nao in (("bradesco-auto-whatsapp@v1", BR, "Sim", "Não"),
                                   ("zurich-auto-whatsapp@v1", ZU, "1", "2")):
    s, r = responder(sessao(ref, "guincho", veiculo_em_garagem="sim, no prédio",
                            veiculo_nivel_rua="Subsolo"), tela)
    certo(r == sub_sim, f"{ref.split('-')[0]}: carro no SUBSOLO → {sub_sim!r}", f"respondeu {r!r}")
    s, r = responder(sessao(ref, "guincho", veiculo_em_garagem="não, está na rua",
                            veiculo_nivel_rua="não está em garagem"), tela)
    certo(r == sub_nao, f"{ref.split('-')[0]}: carro na RUA → {sub_nao!r}", f"respondeu {r!r}")
    certo("veiculo_nivel_rua" in CP.missing_slots_for_subservice(ref, "guincho", {}),
          f"{ref.split('-')[0]}: a garagem é PERGUNTADA antes de acionar")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
