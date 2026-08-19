# -*- coding: utf-8 -*-
"""Um passo de UMA rota nao pode ser cobrado das OUTRAS.

O DEFEITO, MEDIDO
=================
📊 18/08/2026 o corredor residencial da Allianz ganhou nove passos novos para
conserto de eletrodomestico (`menu_aparelho`, `aparelho_marca`,
`aparelho_modelo`, `escolher_data_agendamento`...). Nenhum deles declarou
`only_subservices`.

📊 19/08/2026, medido: `missing_slots_for_subservice(pb, "eletricista", caso)`
devolvia

    ['periodo_preferido', 'risco_confirmado_sem_fumaca',
     'aparelho_marca', 'aparelho_modelo']

Um chamado de ELETRICISTA sendo cobrado pela marca e pelo modelo de um
eletrodomestico. Dados que aquele caso nunca vai ter -> `missing_data` ->
**acionamento bloqueado**. E o `build_dry_run_plan` do mesmo caso listava
`[PENDENTE: aparelho_marca]`, que e a promessa de uma resposta em branco na
URA da seguradora.

O golden do eletricista caiu de 75 asserçoes para 60 verdes e 15 vermelhas —
e ninguem viu, porque o guarda da maquina de lavar (72 verdes) so olhava a
rota da maquina de lavar.

A CAUSA
=======
`missing_slots_for_subservice` percorre TODOS os `ura_steps` recolhendo
`requires`, e so pula os que declaram `only_subservices` de outra rota. Passo
sem esse filtro vale para todo mundo. O filtro existia; os passos novos e que
nao o usavam.

O QUE ESTE GUARDA FAZ
=====================
Ele nao confere UM corredor: confere a INVARIANTE, em todos. Para cada
playbook e cada par de subservicos, um caso preenchido com o que a rota A
exige nao pode ficar preso pedindo dado que so a rota B usa.

🔴 Guarda generico de proposito. O especifico ("a maquina de lavar funciona")
ja existia e passou verde durante todo o defeito, porque media so o lado que
estava certo.
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
IDS = importlib.import_module("app.services.insurer_dispatch_service")

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


# Um caso "generico" — o que QUALQUER acionamento tem. Os slots especificos de
# cada rota entram depois, vindos do proprio `required_slots` dela.
BASE = {
    "titular_cpf": "52998224725",
    "titular_nome": "FULANO DE TAL",
    "telefone_contato": "48991234567",
    "endereco_numero": "112",
    "problema_descricao": "descricao do problema relatado pelo cliente",
    "periodo_preferido": "tarde",
}


def caso_completo_da_rota(pb, rota):
    """Preenche TUDO que a rota declara exigir. Se depois disso ainda faltar
    algo, o que falta veio de OUTRA rota — que e exatamente o defeito."""
    caso = dict(BASE)
    sub = (pb.get("subservices") or {}).get(rota) or {}
    for slot in sub.get("required_slots") or []:
        caso.setdefault(slot, "preenchido")
        if not str(caso.get(slot) or "").strip():
            caso[slot] = "preenchido"
    return caso


print()
print("=" * 74)
print("  1. A INVARIANTE, EM TODOS OS CORREDORES")
print("=" * 74)

# 🔴 A INVARIANTE CERTA NAO E "nao pode faltar nada".
#
# A primeira versao deste guarda afirmava que, preenchido o `required_slots`
# da rota, nada mais podia faltar. 📊 Ela acusou `pessoa_no_local` em azul-auto
# e hdi-auto — e isso NAO e vazamento: o proprio codigo cobra `requires` dos
# passos ALEM do `required_slots`, de proposito, desde 03/08/2026 ("o efeito
# nao era uma recusa honesta, era uma MENTIRA: a sessao nascia ready_to_send e
# o corredor travava no meio"). O guarda estava medindo um defeito que e
# feature.
#
# O que de fato nao pode acontecer e mais estreito: a rota A ser cobrada por
# um slot que SO existe em passo de outra rota. Isso e o borrao.
def slots_legitimos_da_rota(pb, rota):
    """Tudo que ESTA rota tem direito de exigir: o `required_slots` dela mais
    os `requires` dos passos que se aplicam a ela."""
    sub = (pb.get("subservices") or {}).get(rota) or {}
    legit = set(sub.get("required_slots") or [])
    alvo = str(rota).lower()
    for passo in pb.get("ura_steps") or []:
        only = passo.get("only_subservices")
        if only and alvo not in [str(x).lower() for x in only]:
            continue
        legit.update(passo.get("requires") or [])
    return legit


borroes = []
pares = 0
for ref, pb in sorted(CP._PLAYBOOKS.items()):
    rotas = sorted((pb.get("subservices") or {}).keys())
    if len(rotas) < 2:
        continue
    for rota in rotas:
        pares += 1
        caso = caso_completo_da_rota(pb, rota)
        falta = set(CP.missing_slots_for_subservice(pb, rota, caso))
        falta.discard(CP.SUBSERVICO_INVALIDO)
        intrusos = falta - slots_legitimos_da_rota(pb, rota)
        if intrusos:
            borroes.append((ref, rota, sorted(intrusos)))

certo(pares > 10,
      f"CONTROLE: o guarda percorreu rotas de verdade ({pares} rota(s) em "
      f"{len(CP._PLAYBOOKS)} corredores)",
      "com poucas rotas, o verde abaixo nao significaria nada")

certo(not borroes,
      "nenhuma rota e cobrada por slot que so existe em passo de OUTRA rota",
      "borrando: " + "; ".join(f"{r}/{s} -> {f}" for r, s, f in borroes[:6]))

# 🔴 E AGORA A ASSERCAO NAO-CIRCULAR, que e a que realmente guarda.
#
# A de cima deriva "o que a rota pode exigir" do proprio `only_subservices` —
# entao um passo que ESQUECEU o filtro parece legitimo para todas as rotas, e
# ela passa verde. 📊 Provado por mutacao: removido o filtro de `aparelho_marca`,
# a assercao acima continuou VERDE e so as concretas (blocos 2 e 3) ficaram
# vermelhas. Guarda que nao consegue falhar nao guarda.
#
# Esta olha de outro angulo, sem consultar o campo em questao: se um slot e
# obrigatorio em ALGUMAS rotas mas nao em TODAS, ele e especifico — e o passo
# que o exige tem de dizer de quem ele e. Slot que todas as rotas pedem (CPF,
# telefone, endereco) e comum e nao precisa de filtro.
#
# 📊 A primeira versao desta assercao exigia "exatamente UMA rota", e por isso
# NAO ficou vermelha na mutacao: `aparelho_marca` e obrigatorio em DUAS rotas
# (eletrodomesticos e maquina_de_lavar), nao em uma. Um a mais que a condicao
# esperava, e o guarda ficou cego. A mutacao mostrou; a leitura nao mostraria.
sem_filtro = []
for ref, pb in sorted(CP._PLAYBOOKS.items()):
    subs = pb.get("subservices") or {}
    if len(subs) < 2:
        continue
    todas = set(subs.keys())
    donos = {}
    for rota, sub in subs.items():
        for slot in sub.get("required_slots") or []:
            donos.setdefault(slot, set()).add(rota)
    # especifico = pedido por algumas rotas, mas nao por todas
    especificos = {s: sorted(r) for s, r in donos.items() if r and r != todas}
    for passo in pb.get("ura_steps") or []:
        # 🔴 As MESMAS tres isencoes que `missing_slots_for_subservice` aplica.
        # `fallback_adaptive` entra aqui porque o motor ja o pula: naquele
        # passo a falta e prevista e o cerebro responde. Um guarda que fosse
        # mais rigido que o motor acusaria defeito onde nao ha — e aprender a
        # ignorar guarda e pior que nao ter guarda.
        if (passo.get("only_subservices") or passo.get("noop")
                or passo.get("fallback_adaptive")):
            continue
        for slot in passo.get("requires") or []:
            if slot in especificos:
                sem_filtro.append((ref, passo.get("step"), slot, especificos[slot]))

certo(not sem_filtro,
      "🔴 passo que exige slot de rota ESPECIFICA declara `only_subservices`",
      "sem filtro: " + "; ".join(
          f"`{p}` exige {s} (so as rotas {r} pedem) em {ref}"
          for ref, p, s, r in sem_filtro[:5]))

print()
print("=" * 74)
print("  2. O CASO EXATO QUE QUEBROU — eletricista da Allianz residencial")
print("=" * 74)

PB = CP._PLAYBOOKS["allianz-residencial-whatsapp@v1"]
caso_eletrico = dict(BASE, problema_descricao="tomadas da cozinha sem energia",
                     risco_confirmado_sem_fumaca="sim")
falta_eletrico = CP.missing_slots_for_subservice(PB, "eletricista", caso_eletrico)

certo("aparelho_marca" not in falta_eletrico and "aparelho_modelo" not in falta_eletrico,
      "🔴 eletricista NAO e cobrado por marca/modelo de eletrodomestico",
      f"faltou: {falta_eletrico}")
certo(not falta_eletrico,
      "e com o caso completo nao falta mais nada",
      f"faltou: {falta_eletrico}")

# CONTROLE: a rota de eletrodomestico CONTINUA cobrando o que e dela. Sem
# isto, um filtro que simplesmente desligasse todas as exigencias passaria
# no teste acima sem guardar coisa nenhuma.
falta_aparelho = CP.missing_slots_for_subservice(PB, "maquina_de_lavar", caso_eletrico)
certo("aparelho_marca" in falta_aparelho,
      "🔴 CONTROLE: e a maquina de lavar CONTINUA exigindo a marca",
      f"faltou: {falta_aparelho}")

print()
print("=" * 74)
print("  3. O PLANO NAO PROMETE RESPOSTA EM BRANCO")
print("=" * 74)

plano = IDS.build_dry_run_plan("allianz-residencial-whatsapp@v1", "eletricista",
                               caso_eletrico)
certo(plano.get("ok") is True, "o plano do eletricista e montado",
      str(plano.get("error")))
pendentes = [p["step"] for p in plano.get("steps") or [] if "[PENDENTE:" in p["reply"]]
certo(not pendentes,
      "🔴 nenhum passo do plano sai com lacuna",
      f"sairiam em branco na URA: {pendentes}")

passos_do_plano = {p["step"] for p in plano.get("steps") or []}
certo("aparelho_marca" not in passos_do_plano,
      "e o plano do eletricista nem lista os passos de eletrodomestico")

# CONTROLE: o plano da maquina de lavar LISTA esses passos. Se nao listasse,
# o teste acima estaria medindo um plano vazio.
caso_lavar = caso_completo_da_rota(PB, "maquina_de_lavar")
plano_lavar = IDS.build_dry_run_plan("allianz-residencial-whatsapp@v1",
                                     "maquina_de_lavar", caso_lavar)
passos_lavar = {p["step"] for p in plano_lavar.get("steps") or []}
certo("aparelho_marca" in passos_lavar,
      "🔴 CONTROLE: mas o plano da MAQUINA DE LAVAR lista, sim",
      f"passos: {sorted(passos_lavar)}")
certo("o_que_aconteceu" not in passos_lavar,
      "e nao lista o passo que so o eletricista responde",
      "o filtro corta nos DOIS sentidos, nao so num")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
