# -*- coding: utf-8 -*-
"""🔴 A TECLA CERTA NA FORMA ERRADA É UMA TECLA QUE NÃO EXISTE.

📊 23/08/2026, ONDA C. Duas derivações devolviam **número** para telas que não
têm número nenhum:

```
pane_detalhe_opcao      hdi + yelum   "5"  ->  a tela é LISTA: "Problemas no motor"
pneus_quantidade_opcao  hdi + yelum   "1"  ->  a tela é BOTÃO: "Apenas um pneu"
```

🔴 E o que a URA faz com isso está no próprio acervo:

> *"Não entendi. Lembre-se que, para responder, você precisa selecionar o botão
> indicando a opção escolhida."*

A sessão que recebeu essa tela (`697abd09`) terminou em *"vamos te encaminhar
para um de nossos analistas"*. **Formato errado não é resposta ruim: é
atendimento perdido** — e o corredor não percebe, porque para ele a tecla foi
enviada.

⚠️ E era invisível para todos os outros guardas: a derivação ACERTAVA a
decisão (era mesmo o motor, era mesmo um pneu só). Só a FORMA estava errada, e
nenhum item da régua olha para a forma.

🔴 Este guarda não confere as duas que já foram consertadas — ele confere
**todas**, e a cada derivação nova. É a diferença entre corrigir um caso e
fechar a porta da classe inteira.

⚠️ A convenção de cada seguradora é medida no PRÓPRIO corredor: se as respostas
constantes dele são majoritariamente números, ele é numerado; se são rótulos,
ele é de rótulo. Não há lista escrita à mão para divergir do código.
"""

from __future__ import annotations

import ast
import collections
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

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


def _forma(valor: str) -> str:
    return "numero" if re.fullmatch(r"\d+", str(valor).strip()) else "rotulo"


def convencao_do_corredor(pb) -> str:
    """Numerado ou de rótulo — medido nas respostas CONSTANTES do próprio."""
    num = rot = 0
    for p in pb.get("ura_steps") or []:
        r = str(p.get("reply") or "")
        if not r or "{" in r:
            continue
        (num, rot) = (num + 1, rot) if _forma(r) == "numero" else (num, rot + 1)
    return "numero" if num > rot else "rotulo"


CONV = {ref: convencao_do_corredor(pb) for ref, pb in CP._PLAYBOOKS.items()}


def valores_derivados():
    """`{slot: {valores literais que a derivação atribui}}`, lidos da FONTE.

    ⚠️ Lido do código, não de uma cópia: uma lista escrita à mão aqui seria a
    segunda verdade que diverge na próxima edição (§9.4).
    """
    # ⚠️ 🔴 POR AST, NAO POR REGEX DE LINHA. A primeira versao deste leitor
    #    usava `slots["x_opcao"] = (.+)` e lia so o RESTO DA LINHA — entao uma
    #    atribuicao quebrada em duas linhas
    #
    #        slots["pneus_quantidade_opcao"] = (
    #            "Mais de um pneu" if varios else "Apenas um pneu")
    #
    #    devolvia ZERO valores, e a tecla saia da auditoria em silencio.
    #    🔴 Um guarda que perde o caso por causa de uma quebra de linha e pior
    #       que guarda nenhum: ele da o VERDE. Foi assim que ele nasceu, e por
    #       isso a leitura agora e estrutural.
    caminho = os.path.join(RAIZ, "app", "services", "insurer_dispatch_service.py")
    arvore = ast.parse(open(caminho, encoding="utf-8").read())
    fora = collections.defaultdict(set)
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.FunctionDef)
                and no.name == "_derivar_teclas_do_caso"):
            continue
        for filho in ast.walk(no):
            if not isinstance(filho, ast.Assign):
                continue
            for alvo in filho.targets:
                if not (isinstance(alvo, ast.Subscript)
                        and isinstance(alvo.value, ast.Name)
                        and alvo.value.id == "slots"
                        and isinstance(alvo.slice, ast.Constant)
                        and str(alvo.slice.value).endswith("_opcao")):
                    continue
                for v in ast.walk(filho.value):
                    if (isinstance(v, ast.Constant)
                            and isinstance(v.value, str) and v.value):
                        fora[str(alvo.slice.value)].add(v.value)
    return fora


def donos(slot):
    """Os corredores que EXIGEM esta tecla."""
    return {ref for ref, pb in CP._PLAYBOOKS.items()
            for p in (pb.get("ura_steps") or [])
            if slot in (p.get("requires") or [])
            or str(p.get("reply") or "") == "{" + slot + "}"}


def conflitos(valores):
    fora = []
    for slot, vals in sorted(valores.items()):
        formas = {_forma(v) for v in vals}
        ds = donos(slot)
        if not ds:
            continue
        for ref in sorted(ds):
            if CONV[ref] not in formas:
                fora.append((slot, ref, sorted(formas), CONV[ref], sorted(vals)[:3]))
    return fora


VALORES = valores_derivados()

print("=" * 74)
print("[1] A AUDITORIA TEM MATÉRIA — e ela é grande o bastante para valer")
print("=" * 74)

certo(len(VALORES) >= 15,
      "📊 a derivação preenche teclas suficientes para a auditoria valer",
      f"{len(VALORES)} teclas: {sorted(VALORES)[:6]}...")
certo(len({c for c in CONV.values()}) == 2,
      "📊 e o produto TEM as duas convenções — senão a pergunta seria vazia",
      f"{collections.Counter(CONV.values())}")

print()
print("=" * 74)
print("[2] 🔴 NENHUMA TECLA DERIVADA SAI NA FORMA ERRADA")
print("=" * 74)

RUINS = conflitos(VALORES)
for slot, ref, formas, conv, exemplos in RUINS:
    print(f"        🔴 {slot} -> {formas} mas `{ref}` é de {conv}: {exemplos}")
certo(not RUINS,
      "🔴 toda tecla derivada sai na forma que a seguradora dona entende",
      f"{len(RUINS)} conflito(s)")

# 🔴 As duas que motivaram este guarda, nomeadas — para que um conserto que as
#    desfaça caia com o nome delas, e não numa contagem genérica.
for slot, esperado in (("pane_detalhe_opcao", "Problemas no motor"),
                       ("pneus_quantidade_opcao", "Apenas um pneu")):
    certo(esperado in VALORES.get(slot, set()),
          f"🔴 `{slot}` responde pelo RÓTULO — a tela não tem número",
          f"valores: {sorted(VALORES.get(slot, set()))[:4]}")

print()
print("=" * 74)
print("[3] 🔴 O CONTROLE: esta auditoria CONSEGUE acusar")
print("=" * 74)
print("     (um guarda que não tem como falhar não guarda nada — §9.3)")

# 🔴 Injeta um conflito FABRICADO: `pane_detalhe_opcao` valendo "5" num
#    corredor de rótulo. Se a auditoria não acusar isto, ela não acusaria o
#    defeito real — e o verde de cima não valeria nada.
FALSO = {k: set(v) for k, v in VALORES.items()}
FALSO["pane_detalhe_opcao"] = {"5"}
acusa = conflitos(FALSO)
certo(any(c[0] == "pane_detalhe_opcao" for c in acusa),
      "🔴 CONTROLE: com o número de volta, a auditoria ACUSA",
      f"acusou {[c[0] for c in acusa]}")

# 🔴 CONTROLE DO CONTROLE: e ela NÃO acusa o corredor numerado, que está certo.
FALSO2 = {k: set(v) for k, v in VALORES.items()}
FALSO2["problema_eletrico_opcao"] = {"1"}
certo(not any(c[0] == "problema_eletrico_opcao" for c in conflitos(FALSO2)),
      "🔴 CONTROLE: e o número CONTINUA certo onde a URA é numerada — a "
      "auditoria não é uma cruzada contra números")

print()
print("=" * 74)
print("[4] E o MOTOR devolve mesmo o que a auditoria leu na fonte")
print("=" * 74)

# 🔴 §9.4: a auditoria acima lê a FONTE. Esta parte chama a função.
for relato, slot, esperado in (
        ("furei um pneu na br-101", "pneus_quantidade_opcao", "Apenas um pneu"),
        ("furei dois pneus no buraco", "pneus_quantidade_opcao", "Mais de um pneu"),
        ("o motor está falhando e batendo pino", "pane_detalhe_opcao",
         "Problemas no motor"),
        ("o carro parou e eu não sei o que é", "pane_detalhe_opcao", "Não sei")):
    d = {"problema_descricao": relato}
    IDS._derivar_teclas_do_caso(d)
    certo(d.get(slot) == esperado, f"{slot} <- {relato[:34]!r} = {esperado!r}",
          f"veio {d.get(slot)!r}")

# 🔴 CONTROLE: a MESMA decisão, na forma NUMÉRICA, para quem é numerado.
d = {"problema_descricao": "furei dois pneus no buraco"}
IDS._derivar_teclas_do_caso(d)
certo(d.get("pneus_furados_opcao") == "2",
      "🔴 CONTROLE: a alfa/allianz recebem a MESMA decisão em NÚMERO — a "
      "decisão é uma só, o que muda é a forma", f"veio {d.get('pneus_furados_opcao')!r}")

print()
print("=" * 74)
print("[5] 🔴 GA-1 (EXTRA-001.4) · O LAÇO INVERTIDO: toda tecla EXIGIDA tem origem")
print("=" * 74)
# 📊 O laço de cima parte das teclas DERIVADAS — ausência de tecla não é forma
#    errada, é forma nenhuma, e ele não a via: `qual_seguro_opcao` mandou
#    "residência" ao menu da Allianz em 10/09 com este guarda verde. Aqui o laço
#    parte dos PASSOS, corredor por corredor.
#
# ⚠️ As teclas que só a ATENDENTE preenche ficam declaradas, com o motivo. A
#    cobertura delas em runtime é `resolver_tecla`: palavra vira dígito lendo a
#    tela, e vazio vai ao Cérebro com as opções (ou a uma pessoa, se decide o
#    ramo). Tecla nova sem origem e fora da lista = VERMELHO, com o nome dela.
_ATENDENTE = ("coletada pela atendente; a camada 1 converte a palavra lendo a tela "
              "e, vazia, a tela vai ao Cérebro com as opções numeradas")
DA_ATENDENTE = {
    ("zurich-auto", "alavanca_travada_opcao"): _ATENDENTE,
    ("zurich-auto", "cambio_opcao"): _ATENDENTE,
    ("zurich-auto", "pane_opcao"): _ATENDENTE,
    ("zurich-auto", "pneus_danificados_opcao"): _ATENDENTE,
    ("mapfre-auto", "assunto_opcao"): _ATENDENTE,
    ("allianz-residencial", "caixa_litros_opcao"): _ATENDENTE,
    ("allianz-residencial", "caixas_dagua_quantidade_opcao"): _ATENDENTE,
    ("allianz-residencial", "chave_tipo_opcao"): "required_slots do chaveiro: " + _ATENDENTE,
    ("allianz-residencial", "chaveiro_necessidade_opcao"): "required_slots do chaveiro: " + _ATENDENTE,
    ("allianz-residencial", "endereco_opcao"): _ATENDENTE,
    ("allianz-residencial", "idade_aparelho_opcao"): "required_slots do eletrodoméstico: " + _ATENDENTE,
    ("porto-residencial", "chaveiro_alvo_opcao"): _ATENDENTE,
    ("porto-residencial", "encanador_instalacao_opcao"): _ATENDENTE,
    ("porto-residencial", "encanador_tipo_opcao"): _ATENDENTE,
    ("porto-residencial", "fechadura_tipo_opcao"): _ATENDENTE,
    ("porto-residencial", "horario_opcao"): "lista de horários da URA: " + _ATENDENTE,
    ("azul-auto", "periodo_opcao"): _ATENDENTE,
    ("alfa-auto", "equipamentos_troca_opcao"): _ATENDENTE,
    ("allianz-auto", "equipamentos_troca_opcao"): _ATENDENTE,
}
for _ref in ("hdi-residencial", "yelum-residencial"):
    for _slot in ("chaveiro_porta_opcao", "eletrodomestico_opcao", "geladeira_medicacao_opcao"):
        DA_ATENDENTE[(_ref, _slot)] = _ATENDENTE
for _ref in ("azul-auto", "hdi-auto", "hdi-residencial", "porto-auto",
             "porto-residencial", "yelum-auto", "yelum-residencial"):
    DA_ATENDENTE[(_ref, "veiculo_opcao")] = ("a lista de veículos da apólice; " + _ATENDENTE)


def inline_do_motor():
    """As teclas que `new_dispatch_session` preenche por conta própria (AST)."""
    arvore = ast.parse(open(os.path.join(RAIZ, "app", "services",
                                         "insurer_dispatch_service.py"), encoding="utf-8").read())
    fora = set()
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.FunctionDef) and no.name == "new_dispatch_session"):
            continue
        for f in ast.walk(no):
            alvo = None
            if isinstance(f, ast.Assign):
                for t in f.targets:
                    if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                            and t.value.id == "merged_slots" and isinstance(t.slice, ast.Constant)):
                        alvo = t.slice.value
            elif (isinstance(f, ast.Call) and isinstance(f.func, ast.Attribute)
                  and f.func.attr == "setdefault" and isinstance(f.func.value, ast.Name)
                  and f.func.value.id == "merged_slots" and f.args
                  and isinstance(f.args[0], ast.Constant)):
                alvo = f.args[0].value
            if alvo and str(alvo).endswith("_opcao"):
                fora.add(str(alvo))
    return fora


def sem_origem(derivados, inline, declaradas):
    fora = []
    for ref, pb in sorted(CP._PLAYBOOKS.items()):
        curto = ref.split("-whatsapp")[0]
        const = {k for sub in (pb.get("subservices") or {}).values() if isinstance(sub, dict)
                 for k, v in sub.items() if k.endswith("_opcao") and v}
        for p in pb.get("ura_steps") or []:
            exig = set(re.findall(r"\{(\w+_opcao)\}", str(p.get("reply") or "")))
            exig |= {r for r in (p.get("requires") or []) if r.endswith("_opcao")}
            for slot in sorted(exig):
                if (slot in derivados or slot in inline or slot in const
                        or (curto, slot) in declaradas):
                    continue
                fora.append((curto, p.get("step"), slot))
    return fora


INLINE = inline_do_motor()
certo(INLINE == {"servico_opcao", "telefone_adicionar_opcao", "qual_seguro_opcao"},
      "📊 o motor preenche por conta própria exatamente as duas teclas inline + a do "
      "RAMO DA APÓLICE (decisão do Founder, 17/09)",
      f"{sorted(INLINE)}")
ORFAS = sem_origem(set(VALORES), INLINE, DA_ATENDENTE)
for ref, passo, slot in ORFAS[:8]:
    print(f"        🔴 {ref} · passo `{passo}` exige `{slot}` e nada o preenche")
certo(not ORFAS, "🔴 toda tecla exigida por um passo tem origem (derivação · inline · "
      "subserviço · atendente declarada)", f"{len(ORFAS)} passo(s) sem origem")
# 🔴 A LIÇÃO MIGRA (CLAUDE.md §9.3): na fatia 1 a tecla do 10/09 ganhou derivação
#    pelo RELATO; em 17/09 o Founder decidiu que ela vem do RAMO DA APÓLICE. O que
#    se afirma agora é a origem nova — e que o relato deixou de decidir o ramo.
certo("qual_seguro_opcao" in INLINE and "qual_seguro_opcao" not in VALORES,
      "🔴 `qual_seguro_opcao` — a tecla do 10/09 — tem origem: o ramo da apólice, "
      "e NÃO o relato", f"inline={'qual_seguro_opcao' in INLINE} derivada={'qual_seguro_opcao' in VALORES}")
# 🔴 CONTROLE: o laço CONSEGUE acusar — sem a derivação do eletricista, ele nomeia.
_sem_eletrico = {k: v for k, v in VALORES.items() if k != "problema_eletrico_opcao"}
_acusa = sem_origem(set(_sem_eletrico), INLINE, DA_ATENDENTE)
certo(any(s == "problema_eletrico_opcao" for _, _, s in _acusa),
      "🔴 CONTROLE: sem a derivação de `problema_eletrico_opcao`, o laço a NOMEIA",
      f"acusou {sorted({s for _, _, s in _acusa})[:4]}")
# ⚠️ E a declaração não pode envelhecer: tecla declarada que ganhou origem sai da lista.
_velhas = sorted(k for k in DA_ATENDENTE if k[1] in VALORES or k[1] in INLINE)
certo(not _velhas, "a lista da atendente não declara tecla que já tem derivação", f"{_velhas}")

# 🔴 E A ORIGEM NOVA, PELO MOTOR (§9.4) — decisão do Founder, 17/09/2026: o ramo
#    da apólice vira a tecla LENDO A TELA REAL do corpus; o relato não decide nada.
_TELA_QUAL_SEGURO = next(
    json.loads(l)["text"] for l in open(os.path.join(RAIZ, "tests", "corpus", "telas_reais",
                                                     "allianz-residencial.jsonl"), encoding="utf-8")
    if "3 - empresarial" in CP._norm(json.loads(l)["text"])
    and "qual seguro deseja utilizar" in CP._norm(json.loads(l)["text"]))
_PB_RES = CP.get_playbook("allianz-residencial-whatsapp@v1")
_PASSO = next(p for p in _PB_RES["ura_steps"] if p.get("step") == "menu_qual_seguro_tres_opcoes")
for ramo, palavra, esperado in (
        ("resi", "", "1"), ("cond", "", "2"), ("empr", "", "3"),
        ("condomínio", "", "2"),            # o que o modelo escreve vira a família
        ("apartamento", "", "1"),           # o nome humano que o agente pergunta (juiz, P4)
        ("loja", "", "3"),
        ("cond", "residência", "2"),        # 🔴 a apólice VENCE a palavra da atendente
        ("auto", "", ""),                   # ramo que não é desta tela: nada sai
        ("", "", "")):                      # sem ramo: a tela vai a uma pessoa
    s = IDS.new_dispatch_session(
        case_id="ga1", company_id="c", playbook_ref="allianz-residencial-whatsapp@v1",
        subservice="encanador", slots={k: v for k, v in (("ramo_da_apolice", ramo),
                                                         ("qual_seguro_opcao", palavra)) if v})
    tecla = IDS.resolver_tecla(_PB_RES, _PASSO, s, _TELA_QUAL_SEGURO)
    certo(tecla["valor"] == esperado and (esperado or tecla["reason"] == "ramo_indeterminado"),
          f"ramo {ramo!r} + palavra {palavra!r} → tecla {esperado or 'nenhuma (pessoa)'!r}",
          f"veio {tecla['valor']!r} {tecla['origem']} {tecla['reason']}")
# 🔴 CONTROLE: o relato que a fatia 1 lia ("minha casa") não preenche mais a tecla.
d = {"problema_descricao": "vazamento no banheiro da minha casa"}
IDS._derivar_teclas_do_caso(d)
certo(not d.get("qual_seguro_opcao"), "🔴 CONTROLE: o relato não decide o ramo da apólice",
      f"veio {d.get('qual_seguro_opcao')!r}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
