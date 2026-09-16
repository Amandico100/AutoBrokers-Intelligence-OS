# -*- coding: utf-8 -*-
"""G-B1 · G-B2 — o número da própria corretora não é cliente.

O DEFEITO, MEDIDO
=================
📊 O conceito existia HOJE só como chave dentro do JSONB
`integrations.alert_target.internal_numbers`. Medido em 16/09/2026:

```
integrações com a lista preenchida ......  0    (nenhuma rota popula)
escritores da mesma coluna ..............  3, em formatos incompatíveis
    `whatsapp_channel.py:1124` faz `update({"alert_target": target})` e APAGA
    `observer_scope`, `observer_exclusions` e `internal_numbers` de uma vez
único leitor ............................  attendance_capture.py:109-117
efeito ..................................  DESCARTAR o evento — e só isso
```

**INFERÊNCIA:** um JSONB sem schema, com três escritores de forma diferente, um
deles destrutivo, e nenhuma tela, não é uma lista — é um lugar onde a
informação some.

O QUE ESTE GUARDA PROVA
=======================
G-B1  um número cadastrado produz **OS QUATRO EFEITOS**: 0 respostas · fora da
      Fila · guarda `False` · captura MARCADA (não descartada). 🔴 E um caso
      com telefone de MEMBRO mal formatado — com `+55`, sem `55`, com e sem
      nono dígito, com máscara — casa em todos.
G-B2  **duas corretoras:** o número da casa da corretora X NÃO cala a conversa
      igual na corretora Y.
G-B3  🔴 O casador do BFF (TypeScript) e o do motor (Python) dão o MESMO
      resultado sobre a MESMA tabela de casos. ⚠️ Um padrão medido com um motor
      e aplicado com outro é um padrão sobre outra coisa (CLAUDE.md §9.4).
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJETO = os.path.dirname(_RAIZ)
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core", "app.services",
             "app.services.atlas", "app.services.whatsapp", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = FAIL = 0


def certo(condicao, frase):
    global OK, FAIL
    if condicao:
        OK += 1
        print("  ✅", frase)
    else:
        FAIL += 1
        print("  ❌", frase)


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


from app.services.o_grupo_so_o_que_importa import (  # noqa: E402
    TIPO_PEDIDO_DE_AJUDA, e_numero_da_casa, numeros_da_casa, o_grupo_pode_saber,
)

EMPRESA_X = "11111111-1111-1111-1111-111111111111"
EMPRESA_Y = "22222222-2222-2222-2222-222222222222"
FIXO_DA_LOJA = "4733330001"          # DDD + 8 dígitos (fixo, sem nono)
CELULAR_DO_SOCIO = "47999990002"     # DDD + 9 + 8


class _Q:
    def __init__(self, banco, tabela):
        self.b, self.t, self.f = banco, tabela, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def in_(self, coluna, valores):
        self.f["__in__"] = (coluna, list(valores))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.b.escritas.append((self.t, linha))
        return self

    def execute(self):
        fonte = self.b.dados.get(self.t, [])
        def _casa(linha):
            for k, v in self.f.items():
                if k == "__in__":
                    coluna, valores = v
                    if str(linha.get(coluna)) not in [str(x) for x in valores]:
                        return False
                elif k in linha and str(linha.get(k)) != str(v):
                    return False
            return True
        return types.SimpleNamespace(data=[l for l in fonte if _casa(l)])


class Banco:
    def __init__(self, dados):
        self.dados, self.escritas = dados, []

    def table(self, nome):
        return _Q(self, nome)


print("=" * 70)
print("  G-B1 — OS QUATRO EFEITOS de um número cadastrado")
print("=" * 70)

banco = Banco({
    "company_internal_numbers": [
        {"company_id": EMPRESA_X, "phone": FIXO_DA_LOJA, "label": "fixo da loja"},
    ],
    "company_members": [{"company_id": EMPRESA_X, "user_id": "u-1", "status": "active"}],
    # ⚠️ 📊 `users_v2.phone` está preenchido em 872/872 — mas NADA prova o
    #    formato. Este membro tem o número com máscara e `+55`, como vem da tela.
    "users_v2": [{"id": "u-1", "phone": "+55 (47) 98888-0003"}],
    "conversations": [
        {"id": "conv-x", "company_id": EMPRESA_X, "user_phone": FIXO_DA_LOJA,
         "claimed_by": None, "claimed_by_name": None, "claimed_at": None},
        {"id": "conv-y", "company_id": EMPRESA_Y, "user_phone": FIXO_DA_LOJA,
         "claimed_by": None, "claimed_by_name": None, "claimed_at": None},
    ],
    "messages": [],
    "work_events": [],
})

casa = rodar(numeros_da_casa(banco, EMPRESA_X))
print("     📊 variantes carregadas:", sorted(casa))
certo(FIXO_DA_LOJA in casa, "o fixo cadastrado entra na lista")
certo("47988880003" in casa,
      "🔴 e o telefone do MEMBRO com `+55` e máscara entra normalizado")

# 🔴 EFEITO 3 — nunca vai ao grupo (a pergunta 2 da guarda).
pode, porque = rodar(o_grupo_pode_saber(
    banco, company_id=EMPRESA_X, conversation_id="conv-x", telefone=FIXO_DA_LOJA,
    tipo=TIPO_PEDIDO_DE_AJUDA))
certo(pode is False and "corretora" in porque,
      "EFEITO 3 — nunca vai ao grupo: %r" % porque[:50])

# 🔴 EFEITO 1 — nunca responde. O motor é `a_ia_deve_calar`, o portão único.
from app.services.o_fim_do_atendimento import (  # noqa: E402
    MOTIVO_NUMERO_DA_CASA, classe_do_silencio,
)

_mod_feed = sys.modules["app.services.o_fim_do_atendimento"]
_anotados = []
_orig_anotar = _mod_feed.anotar_silencio_no_feed


async def _anotar_falso(**kw):
    _anotados.append(kw.get("motivo"))


_mod_feed.anotar_silencio_no_feed = _anotar_falso
calar, motivo = rodar(_mod_feed.a_ia_deve_calar(
    banco, company_id=EMPRESA_X,
    conversa={"id": "conv-x", "user_phone": FIXO_DA_LOJA}))
certo(calar is True and motivo == MOTIVO_NUMERO_DA_CASA,
      "EFEITO 1 — nunca responde: o agente cala com o motivo em frase")
certo(classe_do_silencio(motivo) == "numero_da_casa",
      "🔴 e o silêncio tem CLASSE própria no feed — a Regina distingue "
      "'eu falei' de 'é o fixo da loja'")
certo(_anotados and _anotados[-1] == MOTIVO_NUMERO_DA_CASA,
      "e ele vira linha no feed, como todo silêncio")

# 🔴 CONTROLE: um segurado de verdade continua sendo atendido.
_anotados.clear()
calar, _ = rodar(_mod_feed.a_ia_deve_calar(
    banco, company_id=EMPRESA_X,
    conversa={"id": "conv-outra", "user_phone": "47912345678"}))
certo(calar is False,
      "🔴 CONTROLE: um segurado de verdade NÃO é calado — a lista não cala todo mundo")
_mod_feed.anotar_silencio_no_feed = _orig_anotar

# 🔴 EFEITO 4 — a captura é MARCADA, não descartada.
_captura = open(os.path.join(_RAIZ, "app", "services", "atlas",
                             "attendance_capture.py"), encoding="utf-8").read()
_corpo = _captura.split("async def capture_client_message", 1)[1]
certo('record["source"] = "live_interno"' in _corpo,
      "EFEITO 4 — a captura é MARCADA `live_interno` (o dado fica rotulado, "
      "não some)")
certo("e_numero_da_casa(" in _corpo and "numeros_da_casa(" in _corpo,
      "🔴 e usa a MESMA lista dos outros três efeitos — não uma segunda")
certo("return False" not in _corpo.split('record["source"] = "live_interno"')[0]
      .rsplit("SPEC-EXTRA-001.3", 1)[-1],
      "⛔ e NÃO descarta o evento no caminho da marcação")

# 🔴 EFEITO 2 — nunca entra na Fila.
_casos = open(os.path.join(_PROJETO, "lib", "atendimento", "casos.ts"),
              encoding="utf-8").read()
_carrega = "carregarNumerosDaCasa(supabase, companyId)"
certo(_carrega in _casos and "ehNumeroDaCasa(numerosDaCasa" in _casos,
      "EFEITO 2 — nunca entra na Fila: `projetarCasos` filtra as conversas")
# ⚠️ `find` e não `index`: com a mutação que apaga a chamada, `index` LEVANTA e
# o guarda morre em vez de reprovar. Um guarda que explode não diz o que está
# errado — e é a mutação que descobre isso.
certo(0 <= _casos.find(_carrega) < _casos.find("const conversaPorId"),
      "e filtra ANTES de montar o mapa de casos, não depois")

print()
print("=" * 70)
print("  G-B2 — DUAS CORRETORAS: X não cala Y")
print("=" * 70)

casa_y = rodar(numeros_da_casa(banco, EMPRESA_Y))
certo(casa_y == set(),
      "🔴 a corretora Y não herda nada da X: %s" % (sorted(casa_y) or "vazio"))

pode, _ = rodar(o_grupo_pode_saber(
    banco, company_id=EMPRESA_Y, conversation_id="conv-y", telefone=FIXO_DA_LOJA,
    tipo=TIPO_PEDIDO_DE_AJUDA))
certo(pode is True,
      "🔴 §7: o MESMO número, na corretora Y, continua sendo um caso normal "
      "(dois prédios podem ter o mesmo fixo)")

_mod_feed.anotar_silencio_no_feed = _anotar_falso
calar, _ = rodar(_mod_feed.a_ia_deve_calar(
    banco, company_id=EMPRESA_Y,
    conversa={"id": "conv-y", "user_phone": FIXO_DA_LOJA}))
certo(calar is False, "e o agente CONTINUA atendendo esse número na corretora Y")
_mod_feed.anotar_silencio_no_feed = _orig_anotar

_migration = open(os.path.join(_RAIZ, "supabase", "migrations",
                               "20260916_01_spec_extra001_3_company_internal_numbers.sql"),
                  encoding="utf-8").read()
certo("unique index" in _migration.lower()
      and "(company_id, phone)" in _migration,
      "🔴 e a garantia é estrutural: `unique (company_id, phone)`, nunca `unique (phone)`")
certo("enable row level security" in _migration.lower(),
      "RLS ligada — ainda que a proteção real seja o filtro no código (§7)")

print()
print("=" * 70)
print("  G-B3 — o casador do BFF e o do motor concordam")
print("=" * 70)

#: 🔴 A MESMA tabela de casos, rodada nos DOIS runtimes. ⚠️ CLAUDE.md §9.4: um
#: padrão medido com um motor e aplicado com outro é um padrão sobre outra
#: coisa. `projetarCasos` roda em Node e não pode chamar Python a cada abertura
#: do painel — então as duas implementações existem, e é ESTE bloco que impede
#: que elas divirjam em silêncio.
CASOS = [
    ("4733330001", ["4733330001"], True),                  # igual
    ("554733330001", ["4733330001"], True),                # com 55
    ("+55 (47) 3333-0001", ["4733330001"], True),          # com máscara
    ("47999990002", ["4799990002"], True),                 # com nono × sem nono
    ("4799990002", ["47999990002"], True),                 # sem nono × com nono
    ("47912345678", ["4733330001"], False),                # CONTROLE: outro número
    ("", ["4733330001"], False),                           # CONTROLE: vazio
    ("abc", ["4733330001"], False),                        # CONTROLE: lixo
    ("4733330001", [], False),                             # CONTROLE: lista vazia
]

py = [e_numero_da_casa({v for p in lista
                        for v in __import__(
                            "app.services.o_fim_do_atendimento", fromlist=["x"]
                        )._variantes_do_telefone(p)}, alvo)
      for alvo, lista, _ in CASOS]

_SCRIPT = r"""
const ts = require('typescript');
const fs = require('fs');
const fonte = fs.readFileSync(process.argv[2], 'utf8');
const js = ts.transpileModule(fonte, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2017}}).outputText;
const m = {exports:{}};
new Function('module','exports','require', js)(m, m.exports, require);
const casos = JSON.parse(process.argv[3]);
const out = casos.map(([alvo, lista]) => {
  const numeros = new Set();
  for (const p of lista) Array.from(m.exports.variantesDoTelefone(p)).forEach((v) => numeros.add(v));
  return m.exports.ehNumeroDaCasa(numeros, alvo);
});
console.log(JSON.stringify(out));
"""
_tmp = os.path.join(_RAIZ, "tests", "_casador_ts.js")
ts_ok, ts_res = False, []
try:
    with open(_tmp, "w", encoding="utf-8") as fh:
        fh.write(_SCRIPT)
    r = subprocess.run(
        ["node", _tmp,
         os.path.join(_PROJETO, "lib", "atendimento", "numeros-da-casa.ts"),
         json.dumps([[a, l] for a, l, _ in CASOS])],
        cwd=_PROJETO, capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        ts_res = json.loads(r.stdout.strip().splitlines()[-1])
        ts_ok = True
    else:
        print("     ⚠️ node indisponível:", (r.stderr or "")[-160:])
except Exception as exc:  # noqa: BLE001
    print("     ⚠️ node indisponível:", type(exc).__name__)
finally:
    try:
        os.remove(_tmp)
    except OSError:
        pass

esperado = [e for _a, _l, e in CASOS]
certo(py == esperado, "o casador Python acerta os %d casos" % len(CASOS))
if ts_ok:
    certo(ts_res == esperado, "o casador TypeScript acerta os mesmos %d casos" % len(CASOS))
    certo(ts_res == py,
          "🔴 e os DOIS dão exatamente o mesmo resultado — %s" % ts_res)
else:
    # ⛔ Sem `node` o guarda NÃO finge que mediu: ele reprova a dimensão.
    certo(False, "⛔ NÃO AVALIADA: `node` indisponível — a equivalência entre os "
                 "dois casadores não foi medida nesta rodada")

print()
print("=" * 70)
print("  %d assercoes verdes · %d vermelhas" % (OK, FAIL))
print("=" * 70)
sys.exit(1 if FAIL else 0)
