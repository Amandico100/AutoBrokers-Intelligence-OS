# -*- coding: utf-8 -*-
"""🔴 AS QUATRO PERGUNTAS SEM DEFAULT — SPEC-084.1, decisão 2 do Founder.

> ## "NÃO EXISTE DEFAULT HONESTO PARA ESTAS QUATRO. O default É o erro.
> ## Cliente não respondeu → handoff, nunca chute."

Esta é a **exceção da E4**. A regra geral do motor é boa e foi medida: numa
tela reversível o cérebro assume, porque o silêncio custou 2min22 e um clique
manual em 18/08. Mas quatro perguntas não são reversíveis **na vida do
segurado**, ainda que a tela seja:

```
situacao_risco      afirmar que ele NÃO está em via escura, sem ele ter dito
via_ou_rodovia      "via local" para quem está na rodovia manda o guincho
                    a um lugar onde ele não pode entrar
bateria_tipo        recarga ≠ bateria nova ≠ troca ≠ na garantia
taxi_passageiros    cinco pessoas ficam na estrada
```

⚠️ **E o teste que importa não é o que prova que a derivação acerta.** É o
CONTROLE NEGATIVO: relato que não diz nada tem de deixar o slot **VAZIO**, e o
passo tem de virar `needs_human`. Um guarda que só testasse os acertos passaria
igual com um `else` devolvendo a primeira opção.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# ⚠️ Import POR CAMINHO, como os outros guardas: `app.services.__init__`
#    puxa `fastembed`, que nao existe neste ambiente. E o §9.4 exige que o
#    teste chame o MOTOR, nunca uma copia -- entao nao da para contornar
#    reimplementando.
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


def derivar(**campos):
    slots = dict(campos)
    IDS._derivar_teclas_do_caso(slots)
    return slots


# =============================================================================
print("=" * 74)
print("[1] AS QUATRO DERIVAM DO RELATO — regra 2: deriva primeiro")
print("=" * 74)

CASOS = [
    ("via_ou_rodovia_opcao", "Rodovia",
     dict(local_atual="parado no acostamento da BR-101, km 212")),
    ("via_ou_rodovia_opcao", "Via local",
     dict(local_atual="na rua Bento Gonçalves, em frente ao 340")),
    ("situacao_risco_opcao", "Via com pouca iluminação",
     dict(problema_descricao="furei o pneu e a rua está escura, sem poste")),
    ("situacao_risco_opcao", "Via com pouco movimento",
     dict(problema_descricao="o carro morreu num lugar ermo, não passa ninguém")),
    ("situacao_risco_opcao", "Nenhuma das anteriores",
     dict(local_atual="estou no estacionamento do shopping, bem iluminado")),
    ("bateria_tipo_opcao", "Bateria nova",
     dict(subservico="bateria_nova")),
    ("bateria_tipo_opcao", "Na garantia",
     dict(problema_descricao="a bateria está na garantia ainda, comprei em março")),
    ("bateria_tipo_opcao", "Recarga de bateria",
     dict(problema_descricao="preciso de uma chupeta, o carro não pega")),
    ("taxi_passageiros_opcao", "Mais de 4",
     dict(problema_descricao="somos 5 pessoas no carro")),
    ("taxi_passageiros_opcao", "1 a 4",
     dict(problema_descricao="estou sozinho aqui")),
]
for slot, esperado, campos in CASOS:
    obtido = derivar(**campos).get(slot)
    certo(obtido == esperado, f"{slot} -> {esperado!r}",
          f"veio {obtido!r} de {list(campos.values())[0][:52]!r}")

# =============================================================================
print()
print("=" * 74)
print("[2] 🔴 O CONTROLE NEGATIVO: sem relato, o slot fica VAZIO")
print("=" * 74)
print("     (é aqui que um `else` escondido seria pego)")

MUDO = derivar(problema_descricao="o carro não liga", local_atual="")
for slot in ("via_ou_rodovia_opcao", "situacao_risco_opcao",
             "bateria_tipo_opcao", "taxi_passageiros_opcao"):
    certo(not str(MUDO.get(slot) or "").strip(),
          f"🔴 {slot} continua VAZIO — o relato não respondeu",
          f"veio {MUDO.get(slot)!r}, e isso é um default inventado")

# 🔴 E o contraste que dá direito à conclusão: as SETE do `quando` TÊM default,
#    e o mesmo relato mudo as preenche. Se esta metade falhasse, o teste acima
#    estaria provando apenas que a derivação inteira não roda.
for slot, esperado in (("quando_agora_opcao", "Agora"),
                       ("menu_quando_opcao", "Tenho urgência"),
                       ("agendamento_dia_opcao", "Hoje")):
    certo(MUDO.get(slot) == esperado,
          f"🔴 CONTRASTE: {slot} TEM default e o MESMO relato mudo o preenche",
          f"veio {MUDO.get(slot)!r}")

# =============================================================================
print()
print("=" * 74)
print("[3] A ORDEM das sete do `quando` — 'hoje mais tarde' contém 'hoje'")
print("=" * 74)

ORDEM = [
    ("agora, o carro parou na rua", "Agora", "Tenho urgência", "Hoje"),
    ("pode ser hoje mais tarde", "Agora", "Tenho urgência", "Hoje"),
    ("amanhã de manhã", "Agendar", "Agendar data e hora", "Amanhã"),
    ("depois de amanhã", "Agendar", "Agendar data e hora", "Outro Dia"),
    ("quero agendar para sexta", "Agendar", "Agendar data e hora", "Outro Dia"),
]
for texto, a, b, c in ORDEM:
    d = derivar(quando=texto)
    certo((d.get("quando_agora_opcao"), d.get("menu_quando_opcao"),
           d.get("agendamento_dia_opcao")) == (a, b, c),
          f"{texto!r} -> {a} / {b} / {c}",
          f"veio {d.get('quando_agora_opcao')!r} / "
          f"{d.get('menu_quando_opcao')!r} / {d.get('agendamento_dia_opcao')!r}")

# =============================================================================
print()
print("=" * 74)
print("[4] 🔴 `sem_chute`: o passo com slot vazio vira HANDOFF, não palpite")
print("=" * 74)

MARCADOS = [(p.get("step"), ref)
            for ref, pb in CP._PLAYBOOKS.items()
            for p in (pb.get("ura_steps") or []) if p.get("sem_chute")]
certo(len(MARCADOS) >= 5,
      "📊 os passos das quatro perguntas estão marcados `sem_chute`",
      f"{len(MARCADOS)}: {sorted({p for p, _ in MARCADOS})}")

# 🔴 A trava tem de estar ANTES do ramo em que o cérebro assume. Se ela ficasse
#    depois, `fallback_adaptive` ou a tela reversível venceriam e o palpite
#    voltaria — sem que nenhuma asserção de conteúdo notasse.
FONTE = open(os.path.join(RAIZ, "app", "services",
                          "insurer_dispatch_service.py"),
             encoding="utf-8").read()
i_trava = FONTE.find('if step.get("sem_chute"):')
i_cerebro = FONTE.find('if step.get("fallback_adaptive") or not decisao:')
certo(0 < i_trava < i_cerebro,
      "🔴 a trava `sem_chute` vem ANTES do ramo em que o cérebro assume",
      f"trava em {i_trava}, cérebro em {i_cerebro}")

# 🔴 E o cérebro NÃO pode ser consultado nesse caminho.
trecho = FONTE[i_trava:i_cerebro]
certo("falta_para_a_ura" not in trecho,
      "🔴 o caminho `sem_chute` NÃO alimenta o cérebro — seria o mesmo "
      "default com um parágrafo de justificativa")
certo('"needs_human"' in trecho and "return session" in trecho,
      "🔴 e ele para em `needs_human`, com o motivo gravado")

# =============================================================================
print()
print("=" * 74)
print("[5] REGRA 1: pergunta só o que AQUELA rota precisa")
print("=" * 74)

pb_porto = CP.get_playbook("porto-auto-whatsapp@v1")
bat = [p for p in pb_porto["ura_steps"] if p.get("step") == "bateria_submenu"]
# ⚠️ 🔴 A LISTA EXATA VENCEU EM 23/08/2026, E A LIÇÃO MIGROU (§9.3).
#
# Esta asserção exigia `== {"bateria", "bateria_nova"}`. 📊 A medição da ONDA E
# mostrou que a MESMA tela aparece na rota `tecnico` da Porto: escolher
# "Bateria nova" leva a *"vou te ajudar com o agendamento de um TÉCNICO"*, e o
# resumo sai com *Serviço:* Técnico (sessão e5318468, protocolo
# 1-124279107688). Com o escopo de duas, a tela ficava ÓRFÃ na rota por onde
# ela chega.
#
# 🔴 A regra 1 nunca foi "duas rotas": é **pergunta só o que AQUELA rota
#    precisa**. O que a guarda tem de provar é que o escopo EXCLUI quem nunca
#    vê a tela — e é isso que as duas asserções seguintes fazem, chamando o
#    MOTOR. Uma lista literal aqui só engessava a medição.
_escopo_bat = set(bat[0].get("only_subservices") or []) if bat else set()
certo(bool(bat) and _escopo_bat and not (_escopo_bat & {"guincho", "vidros", "pneu"}),
      "🔴 `bateria_submenu` NÃO alcança rotas que nunca veem a tela",
      f"only_subservices={sorted(_escopo_bat)}")

TELA_BAT = "Entendi. O que você precisa? Recarga de bateria Bateria nova Troca de bateria Na garantia Voltar"
certo(CP.match_ura_step(pb_porto, TELA_BAT, subservice="guincho") is None,
      "🔴 e um GUINCHO não é perguntado sobre bateria",
      str(CP.match_ura_step(pb_porto, TELA_BAT, subservice="guincho")))
certo(CP.match_ura_step(pb_porto, TELA_BAT, subservice="bateria") is not None,
      "🔴 CONTROLE: mas a rota de BATERIA continua vendo a tela — o escopo "
      "não apagou o passo")

# =============================================================================
print()
print("=" * 74)
print("[6] REGRA 3: uma mensagem só, na língua do cliente")
print("=" * 74)

for slot in ("situacao_risco_opcao", "via_ou_rodovia_opcao",
             "bateria_tipo_opcao", "taxi_passageiros_opcao"):
    texto = CP._COMO_PERGUNTAR.get(slot) or ""
    certo(len(texto) > 25 and slot.replace("_", " ") not in texto,
          f"`{slot}` tem redação de CLIENTE, não o nome do campo",
          f"{texto[:70]!r}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
