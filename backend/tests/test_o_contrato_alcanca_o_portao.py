# -*- coding: utf-8 -*-
r"""🔴 O dado que o portão exige TEM COMO CHEGAR até ele?

A régua da SPEC-084.1 responde *"o corredor sabe responder a URA?"*. 📊 Ela deu
**19 rotas AAA**, com 100% das telas respondidas e 100% de determinismo.

⚠️ **E nenhuma acionava.** O bloqueio estava ANTES do corredor:

```
com TUDO que a ferramenta consegue carregar   →  missing_data    🔴  0 de 19
com os slots que ela NÃO carrega, em memória  →  ready_to_send   ✅  19 de 19
```

A SPEC-084.1 acrescentou slots a `required_slots` e não estendeu o schema da
ferramenta. **Um slot que o portão exige e o contrato não anuncia não tem como
chegar** — o atendente não tem onde escrever a resposta, por mais que a
pergunta já esteja redigida em `_COMO_PERGUNTAR` (📊 19 dos 22 estavam).

⚠️ E não vale a saída de emergência: `nodes.py` chama `tool._arun(**args)` cru,
sem Pydantic. Um campo não declarado *funcionaria* se o modelo adivinhasse o
nome — mas o modelo só vê o schema, e 📊 `model_validate` **descarta** o extra.
Apostar um guincho real em adivinhação não é engenharia.

🔴 **Este guarda é a razão de o defeito não voltar.** Ele compara as duas
listas — o que o portão cobra e o que o contrato declara — em TODAS as rotas.
Sem ele, a próxima SPEC que acrescentar um slot repete isto em silêncio, e a
régua continua dando AAA para rota que não aciona.
"""
from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, RAIZ)

import regua_motor as M     # noqa: E402  (M.CP é corridor_playbooks já carregado)

CP = M.CP


def _carregar(dotted: str, rel: str):
    """Importa de `app/` sem passar pelo `__init__` do pacote.

    ⚠️ `app.agents.__init__` puxa `langgraph` e `app.services.__init__` puxa
    `fastembed` — dependências de runtime ausentes no ambiente de teste.
    """
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(RAIZ, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


TOOL = _carregar("app.agents.tools.insurer_dispatch_tool",
                 "app/agents/tools/insurer_dispatch_tool.py")

CAMPOS = set(TOOL.InsurerDispatchInput.model_fields)

OK = FAIL = 0


def certo(cond, nome, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {nome}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {nome}" + (f"\n        {detalhe}" if detalhe else ""))


def cobrados_de(rota):
    """O que o PORTÃO ainda cobra depois de o motor preencher o que sabe.

    🔴 Pelo caminho REAL — `new_dispatch_session` —, não por
    `missing_slots_for_subservice({})`. A diferença não é estilo, é medida:
    📊 `servico_texto` aparece como cobrado na consulta crua em 9 rotas da
    porto, e **some** pelo caminho real, porque `new_dispatch_session` o
    injeta. Declará-lo no contrato faria a atendente perguntar ao segurado uma
    coisa que o motor já sabe.

    ⚠️ Foi assim que a primeira redação deste guarda acusou 8 órfãos, dos quais
    1 era invenção do próprio guarda. Medir pelo caminho que o produto usa é o
    que separa achado de ruído.
    """
    ses = M.IDS.new_dispatch_session(
        case_id="guarda", company_id="guarda",
        playbook_ref=rota.ref, subservice=rota.servico, slots={})
    falta = [s for s in (ses.get("missing_slots") or [])
             if s != CP.SUBSERVICO_INVALIDO]

    # ══════════════════════════════════════════════════════════════════════
    # 🔴 E O QUE O PORTÃO **DEIXOU DE COBRAR** — achado do JUIZ 4
    # ══════════════════════════════════════════════════════════════════════
    #
    # A primeira redação deste guarda definia a população como os
    # `missing_slots` do portão — **exatamente o conjunto que esta mesma SPEC
    # estreitou**. Um guarda circular: ele media a régua que o C1 encolheu, e
    # por isso ficava verde enquanto cinco rotas AAA iam a `needs_human` numa
    # tela que está no corpus.
    #
    # 📊 O que faltava: `situacao_risco_opcao`, `bateria_tipo_opcao` e
    #    `taxi_passageiros_opcao` — slots que um PASSO exige, o motor NÃO
    #    injeta, e a regra do sufixo `_opcao` isentava. As duas regras se
    #    contradiziam: uma diz *"o motor preenche"*, `sem_chute` diz *"não
    #    existe default honesto"*.
    #
    # ⚠️ A pergunta certa não é *"o que o portão cobra?"* — é **"o que o
    #    CORREDOR vai precisar quando a tela chegar?"**. Quem responde isso são
    #    os `requires` dos passos, menos o que o motor de fato injeta.
    tem = {k for k, v in (ses.get("slots") or {}).items() if str(v or "").strip()}
    alvo = CP.canonical_subservice(rota.servico)
    pb = CP.get_playbook(rota.ref) or {}
    for passo in pb.get("ura_steps") or []:
        # `fallback_adaptive` fica de fora: ali o cérebro responde, e é o
        # desenho declarado. O que entra é o que TRAVA.
        if passo.get("fallback_adaptive") or passo.get("noop"):
            continue
        only = passo.get("only_subservices")
        if only and alvo not in [str(x).lower() for x in only]:
            continue
        for campo in passo.get("requires") or []:
            if campo not in tem and campo not in falta:
                falta.append(campo)
    return falta


print("=" * 74)
print("[1] TODO SLOT QUE O PORTÃO COBRA TEM CAMPO NO CONTRATO")
print("=" * 74)

rotas = list(M.rotas())
certo(len(rotas) >= 60, "\U0001F4CA o inventário de rotas está carregado",
      f"{len(rotas)} rotas")

orfaos = {}
for rota in rotas:
    for slot in cobrados_de(rota):
        if slot not in CAMPOS:
            orfaos.setdefault(slot, []).append(str(rota))

certo(not orfaos,
      "\U0001F534 nenhum slot cobrado ficou sem campo no contrato",
      "; ".join(f"{s} (x{len(r)}, ex.: {r[0]})"
                for s, r in sorted(orfaos.items(), key=lambda kv: -len(kv[1]))[:8]))

print()
print("=" * 74)
print("[2] \U0001F534 O CONTROLE: a comparação CONSEGUE apontar alguém")
print("=" * 74)
print("     um guarda que não tem como ficar vermelho não guarda nada (§9.3)")

# 🔴 Sem esta metade, apagar `cobrados_de` faria o [1] passar para sempre: uma
#    lista vazia nunca tem órfão. O controle prova que a população existe E que
#    a comparação sabe reprovar.
todos_cobrados = {s for r in rotas for s in cobrados_de(r)}
certo(len(todos_cobrados) >= 20,
      "\U0001F4CA a população varrida não está vazia",
      f"{len(todos_cobrados)} slots distintos cobrados em {len(rotas)} rotas")

certo(bool(todos_cobrados - {"__nao_existe_no_contrato__"}),
      "   e ela é comparável com o contrato")

_falso = {s for s in todos_cobrados if s not in (CAMPOS - {"titular_cpf"})}
certo("titular_cpf" in _falso,
      "\U0001F534 CONTROLE: tirando `titular_cpf` do contrato, a comparação "
      "ACUSA — logo ela sabe reprovar",
      f"acusou: {sorted(_falso)[:5]}")

# 🔴 CONTROLE DA METADE NOVA — achado do JUIZ 4.
#
#    O controle acima usa `titular_cpf`, que vem da metade VELHA da
#    população (os `missing_slots` do portão). 📊 Apagando a varredura dos
#    `requires`, o item [1] passa, o [2] passa e AQUELE controle continua
#    vermelho do mesmo jeito — ou seja, **a metade que este guarda ganhou
#    não tinha como falhar.**
#
# ⚠️ `situacao_risco_opcao` só existe na população NOVA: o portão não o
#    cobra (é `sem_chute`), e ele aparece porque um PASSO o exige.
_so_da_varredura_nova = set()
for _r in rotas:
    _ses_c = M.IDS.new_dispatch_session(
        case_id="c", company_id="c", playbook_ref=_r.ref,
        subservice=_r.servico, slots={})
    _velha = {x for x in (_ses_c.get("missing_slots") or [])
              if x != CP.SUBSERVICO_INVALIDO}
    _so_da_varredura_nova |= set(cobrados_de(_r)) - _velha

certo("situacao_risco_opcao" in _so_da_varredura_nova,
      "\U0001F534 CONTROLE: a varredura dos `requires` produz slot que o "
      "portão NÃO cobra — a metade nova do guarda tem como falhar",
      f"só da metade nova: {sorted(_so_da_varredura_nova)[:6]}")
certo(all(x in CAMPOS for x in _so_da_varredura_nova),
      "   e TODOS eles têm campo no contrato — a metade nova está coberta",
      str(sorted(x for x in _so_da_varredura_nova if x not in CAMPOS)))

print()
print("=" * 74)
print("[3] E O CONTRATO NÃO CARREGA CAMPO QUE NINGUÉM COBRA")
print("=" * 74)
print("     campo declarado e nunca exigido faz a atendente perguntar à toa")

# ⚠️ Nem todo campo do contrato é cobrado pelo portão, e isso é legítimo:
#    `titular_nascimento` só a Mapfre pede, `dados_confirmados` é conferência da
#    própria ferramenta, `session_id` é injetado pelo runtime. O que este item
#    guarda é que a lista de exceções seja NOMEADA — e não cresça calada.
_NAO_SE_COBRA_NO_PORTAO = {
    "session_id",           # injetado pelo runtime
    "subservice",           # é a pergunta, não a resposta
    "insurer_key", "line_kind",
    "dados_confirmados",    # conferência da ferramenta, não slot de URA
    "aparelho_marca", "aparelho_modelo",   # a URA pergunta em telas separadas
    # ⚠️ `ponto_referencia` é CORTESIA, não requisito: nenhuma URA o exige, e
    #    ele serve ao motorista do guincho achar a casa. Declarado e não
    #    cobrado é o certo aqui — o errado seria o inverso.
    "ponto_referencia",
    # ⚠️ `titular_nascimento` só a Mapfre pede, e ela o pede DENTRO da URA, não
    #    no portão.
    "titular_nascimento",
    # ⚠️ `quando` tem DEFAULT HONESTO no motor — 📊 medido,
    #    `new_dispatch_session` injeta `"agora"` (insurer_dispatch_service:1048),
    #    e por isso ele nunca aparece em `missing_slots`. Continua declarado no
    #    contrato de propósito: é como o atendente AGENDA em vez de acionar
    #    agora. Default honesto e sobrescrevível é o desenho certo — o errado
    #    seria default honesto e inalcançável.
    "quando",
    # ⚠️ SPEC-EXTRA-001.4 — `ramo_da_apolice` é METACAMPO: ele PREENCHE
    #    `qual_seguro_opcao` (decisão do Founder, 17/09). O portão cobra a tecla;
    #    o ramo é como ela chega sem pergunta extra.
    "ramo_da_apolice",
}
sobrando = sorted(CAMPOS - todos_cobrados - _NAO_SE_COBRA_NO_PORTAO)
certo(not sobrando,
      "todo campo do contrato é cobrado por alguma rota, ou está nomeado "
      "como exceção",
      f"declarados e nunca exigidos: {sobrando}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
raise SystemExit(1 if FAIL else 0)
