# -*- coding: utf-8 -*-
r"""🔴 Toda rota chega ao SEU corredor — mesmo sem `line_kind`.

📊 SPEC-084.2 C3. A ferramenta deduzia a linha do serviço com uma lista literal
de cinco strings escrita à mão:

```python
line = "auto" if subservice in ("guincho","bateria","pneu","pane_seca","vidros") else ""
```

Ela nunca soube dos QUATRO subserviços de auto que nasceram depois dela —
`socorro_mecanico`, `tecnico`, `bateria_nova`, `taxi`. Conhecia `pane_seca`, que
é APELIDO e não é rota. E comparava a string **crua**, sem canonicalizar.

🔴 O estrago, medido: **5 rotas resolviam o corredor da linha ERRADA**, duas
delas AAA. `socorro_mecanico` na HDI caía no corredor RESIDENCIAL, e o produto
dizia ao segurado *"a hdi não atende 'socorro_mecanico' por este canal"* — uma
frase falsa sobre uma rota 86/88. A ferramenta não mentia sobre a HDI: mentia
sobre qual porta da HDI ela tinha batido.

⚠️ E o pior caso era `chave`, apelido de `chaveiro`. Ele devia cair no ramo do
handoff — e como aquele ramo também comparava a string crua, o guarda do
chaveiro era **contornado**. O incidente que o comentário dizia impedir
acontecia por baixo dele.

**Este guarda deriva a população de `M.rotas()`**, então o denominador cresce
sozinho com cada corredor novo. Uma lista fixa de 73 aqui repetiria o defeito
que o guarda existe para pegar.
"""
from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, RAIZ)

import regua_motor as M     # noqa: E402
CP = M.CP


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(RAIZ, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


TOOL = _carregar("app.agents.tools.insurer_dispatch_tool",
                 "app/agents/tools/insurer_dispatch_tool.py")

OK = FAIL = 0


def certo(cond, nome, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {nome}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {nome}" + (f"\n        {detalhe}" if detalhe else ""))


def resolver(subservice, seguradora):
    """Pelo caminho REAL da ferramenta, sem `line_kind` — como o LLM chama."""
    ferramenta = TOOL.InsurerDispatchTool(company_id="guarda", case_id="guarda")
    ref, _ = ferramenta._resolve_playbook_ref(
        {"subservice": subservice, "insurer_key": seguradora})
    return ref


print("=" * 74)
print("[1] SEM `line_kind`, CADA ROTA CHEGA AO PRÓPRIO CORREDOR")
print("=" * 74)

rotas = list(M.rotas())
erradas, handoffs = [], []
for rota in rotas:
    ref = resolver(rota.servico, rota.seguradora)
    if ref is None:
        handoffs.append(rota)
    elif ref != rota.ref:
        erradas.append(f"{rota} → {ref}")

certo(len(rotas) >= 60, "\U0001F4CA o inventário de rotas está carregado",
      f"{len(rotas)} rotas")
certo(not erradas,
      "\U0001F534 nenhuma rota resolve o corredor de OUTRA linha",
      "; ".join(erradas[:6]))

print()
print("=" * 74)
print("[2] E O AMBÍGUO CONTINUA VIRANDO HANDOFF — o guarda não afrouxou")
print("=" * 74)

# 🔴 `chaveiro` existe nas duas linhas. Deduzir mandaria um chaveiro de CARRO
#    ao menu residencial, que pede o número da casa a quem está no acostamento.
certo(all(r.servico == "chaveiro" for r in handoffs),
      "só `chaveiro` cai em handoff por ambiguidade",
      str(sorted({r.servico for r in handoffs})))
certo(len(handoffs) == len([r for r in rotas if r.servico == "chaveiro"]),
      "\U0001F4CA e TODAS as rotas de chaveiro caem — nem uma a mais, nem uma a menos",
      f"{len(handoffs)} handoffs")

print()
print("=" * 74)
print("[3] O APELIDO CHEGA AO CORREDOR — inclusive o que contornava o guarda")
print("=" * 74)

# 📊 A lista à mão comparava a string crua, e 26 apelidos de auto não chegavam.
for apelido, esperado in (("reboque", "auto"), ("remocao", "auto"),
                          ("pane", "auto"), ("pane seca", "auto"),
                          ("carga", "auto"), ("estepe", "auto"),
                          ("parabrisa", "auto"), ("socorro mecanico", "auto"),
                          ("linha branca", "residencial")):
    linha, ambiguo = CP.linha_do_subservico(apelido)
    certo(linha == esperado and not ambiguo,
          f"`{apelido}` → {esperado}", f"deu ({linha!r}, ambiguo={ambiguo})")

# 🔴 O caso que mais custava: `chave` contornava o ramo do handoff.
linha_chave, ambiguo_chave = CP.linha_do_subservico("chave")
certo(ambiguo_chave and not linha_chave,
      "\U0001F534 `chave` cai no handoff, como `chaveiro` — o guarda deixou de "
      "ser contornável por apelido",
      f"deu ({linha_chave!r}, ambiguo={ambiguo_chave})")

print()
print("=" * 74)
print("[4] \U0001F534 O CONTROLE: a derivação CONSEGUE reprovar")
print("=" * 74)
print("     um guarda que não tem como ficar vermelho não guarda nada (§9.3)")

# 🔴 Muta os DADOS, não o código: `socorro_mecanico` ganha um galho residencial
#    e passa a ser ambíguo. As três rotas dele TÊM de deixar de resolver.
_pb_resid = CP.get_playbook("hdi-residencial-whatsapp@v1")
_subs = _pb_resid.get("subservices") or {}
_backup = dict(_subs)
try:
    _subs["socorro_mecanico"] = {"required_slots": []}
    CP._LINHAS_POR_SUBSERVICO.setdefault("socorro_mecanico", set()).add("residencial")
    _agora = [r for r in rotas if r.servico == "socorro_mecanico"
              and resolver(r.servico, r.seguradora) is None]
    certo(len(_agora) >= 2,
          "\U0001F534 CONTROLE: com `socorro_mecanico` nas duas linhas, as rotas "
          "dele viram handoff — a derivação lê os DADOS, não uma lista",
          f"viraram handoff: {len(_agora)}")
finally:
    CP._LINHAS_POR_SUBSERVICO["socorro_mecanico"].discard("residencial")
    _subs.clear()
    _subs.update(_backup)

# 🔴 E volta ao que era — sem esta linha, o vermelho acima poderia ser mérito
#    de qualquer coisa.
certo(resolver("socorro_mecanico", "hdi") == "hdi-auto-whatsapp@v1",
      "   — e restaurado, `socorro_mecanico` volta ao corredor de auto",
      str(resolver("socorro_mecanico", "hdi")))

print()
print("=" * 74)
print("[5] A LISTA À MÃO NÃO VOLTA")
print("=" * 74)

fonte = open(os.path.join(RAIZ, "app/agents/tools/insurer_dispatch_tool.py"),
             encoding="utf-8").read()

# ⚠️ Só as linhas de CÓDIGO. O comentário que conta a história cita
#    `"pane_seca"` de propósito — apagar a citação apagaria a explicação de por
#    que a lista era um resumo mal copiado. 📊 A primeira redação deste guarda
#    contava as duas e reprovava o próprio comentário que ela pede que exista.
codigo = [l for l in fonte.splitlines()
          if l.strip() and not l.lstrip().startswith("#")]
codigo = "\n".join(codigo)

# 🔴 `pane_seca` era o dedo-duro: um APELIDO dentro de uma lista de ROTAS.
#    Qualquer lista à mão nova provavelmente o traz de volta.
certo('"pane_seca"' not in codigo,
      "\U0001F534 a string `\"pane_seca\"` não existe mais como CÓDIGO na "
      "ferramenta — qualquer lista à mão nova a traria de volta",
      f"{codigo.count(chr(34) + 'pane_seca' + chr(34))} ocorrências em código")

certo('"guincho", "bateria", "pneu")' not in codigo,
      "   e a tripla escrita à mão também não")

# 🔴 CONTROLE: a busca CONSEGUE achar. Sem isto, um erro de leitura de arquivo
#    faria as duas linhas acima passarem com a fonte vazia.
certo("linha_do_subservico" in codigo,
      "   CONTROLE: e a busca acha o que ESTÁ lá — a derivação é chamada",
      f"{len(codigo)} chars de código lidos")

print()
print("=" * 74)
print("[6] O CONTRATO PUBLICA TODOS OS SUBSERVIÇOS QUE EXISTEM")
print("=" * 74)

desc = TOOL.InsurerDispatchInput.model_fields["subservice"].description
faltando = [s for s in CP._LINHAS_POR_SUBSERVICO if s not in desc]
certo(not faltando,
      "\U0001F534 todo subserviço do produto está nomeado no contrato",
      f"invisíveis ao modelo: {faltando}")
certo("socorro_mecanico" in desc and "GUINCHO × SOCORRO MECÂNICO" in desc,
      "   e o contrato ensina a diferença entre guincho e socorro mecânico")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
raise SystemExit(1 if FAIL else 0)
