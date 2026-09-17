# -*- coding: utf-8 -*-
"""🔴 P-E0013-08 · OS NÚMEROS DA CASA NÃO ATRAVESSAM CORRETORAS — dois tenants REAIS.

A pendência dizia, literalmente: *"o isolamento entre duas corretoras foi LIDO,
não provado contra dois tenants reais"*. Os guardas da EXTRA-001.3 provavam a
regra com `"empresa-a"` e `"empresa-b"` — dois textos inventados. Este prova com
**dois `company_id` que existem na tabela `companies`**, lidos do banco.

```
G1  os dois ids são REAIS, distintos, e o teste sabe dizer quantos existem
G2  um número cadastrado em X NÃO é "da casa" em Y — e a consulta que o busca
    leva `company_id` no filtro (CLAUDE.md §7: a RLS não protege service role)
G3  `o_grupo_pode_saber`, com a MESMA conversa-molde, decide independente em X e Y
G4  a rota do painel nunca aceita `company_id` do corpo — nem no GET, nem no
    POST, nem no DELETE
```

⛔ **NADA DE PII.** O teste lê só `id` e CONTAGENS. Nenhum telefone, nome, CPF
ou apólice entra no código, na saída ou na falha. O telefone usado é fictício.
⛔ **SÓ LEITURA.** Nenhuma linha é escrita em `company_internal_numbers`: a
tabela do banco é lida para contar, e a prova de comportamento roda contra a
função REAL com um dublê de banco que respeita `company_id`.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

import regua_motor as M  # noqa: E402

from app.services import o_grupo_so_o_que_importa as G  # noqa: E402

OK = FAIL = 0
#: 💭 Fictício, e nunca cadastrado: o dublê é quem diz de quem ele é.
FONE_DA_CASA = "5547999990001"
FONE_DE_FORA = "5548988887777"


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def rodar(c):
    return asyncio.run(c)


# ---- Redis mudo: o cache nunca responde por outra corretora ------------------
async def _sem_redis():
    raise RuntimeError("sem redis no teste")


import app.core.redis as _core_redis  # noqa: E402

_core_redis.get_async_redis_client = _sem_redis

print("=" * 74)
print("[G1] DOIS company_id REAIS, lidos do banco")
print("=" * 74)
if not M.tem_banco():
    print("  ⚠️ sem credencial de banco aqui — G1..G3 não rodam com tenants reais.")
    print("  🔴 E isso NÃO é um passe: sem banco não há prova, e a P-E0013-08")
    print("     continua aberta. Rode com SUPABASE_URL/SUPABASE_KEY presentes.")
    sys.exit(2)

cli = M.supabase()
empresas = [str(c["id"]) for c in cli.table("companies").select("id").limit(500).execute().data]
checar(len(empresas) >= 2,
       f"📊 a tabela `companies` tem {len(empresas)} corretoras — dá para comparar duas",
       str(len(empresas)))
X, Y = empresas[0], empresas[1]
checar(X != Y and len(X) == 36 and len(Y) == 36,
       "🔴 os dois ids são distintos e têm forma de uuid (não são rótulos inventados)")
_linhas = cli.table("company_internal_numbers").select("company_id").limit(2000).execute().data
checar(isinstance(_linhas, list),
       f"📊 `company_internal_numbers` responde e tem {len(_linhas)} linhas hoje "
       f"({len({str(l['company_id']) for l in _linhas})} corretoras)")

print()
print("=" * 74)
print("[G2] UM NÚMERO DE X NÃO É 'DA CASA' EM Y — pela função REAL")
print("=" * 74)
# 🔴 O dublê é do BANCO, não da regra: `numeros_da_casa` e `e_numero_da_casa`
#    são as do produto. O dublê só devolve o que a consulta PEDIU — e por isso
#    ele consegue ficar vermelho se o filtro sumir do código.
CONSULTAS = []


class _Consulta:
    def __init__(self, tabela):
        self.tabela, self.eqs, self.ins = tabela, {}, {}

    def select(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def eq(self, campo, valor):
        self.eqs[campo] = valor
        return self

    def in_(self, campo, valores):
        self.ins[campo] = list(valores)
        return self

    def execute(self):
        CONSULTAS.append({"tabela": self.tabela, "eqs": dict(self.eqs)})
        if self.tabela == "company_internal_numbers":
            # A linha existe SÓ na corretora X. Um filtro ausente devolveria
            # o número para as duas — que é exatamente o defeito procurado.
            dados = ([{"phone": FONE_DA_CASA}]
                     if str(self.eqs.get("company_id") or "") == X else [])
            return types.SimpleNamespace(data=dados)
        return types.SimpleNamespace(data=[])


class _Banco:
    class client:  # noqa: N801
        @staticmethod
        def table(nome):
            return _Consulta(nome)


BANCO = _Banco()
casa_x = rodar(G.numeros_da_casa(BANCO, X))
casa_y = rodar(G.numeros_da_casa(BANCO, Y))
checar(G.e_numero_da_casa(casa_x, FONE_DA_CASA),
       "o número cadastrado em X É da casa em X (o controle positivo)")
checar(not G.e_numero_da_casa(casa_y, FONE_DA_CASA),
       "🔴 e o MESMO número NÃO é da casa em Y", f"{len(casa_y)} variantes em Y")
checar(not G.e_numero_da_casa(casa_x, FONE_DE_FORA),
       "🔴 CONTROLE: um número de fora não é da casa nem em X")
_da_tabela = [c for c in CONSULTAS if c["tabela"] == "company_internal_numbers"]
checar(_da_tabela and all("company_id" in c["eqs"] for c in _da_tabela),
       "🔴 CLAUDE.md §7: TODA consulta a `company_internal_numbers` leva "
       "`company_id` no filtro do CÓDIGO (a RLS não protege service role)",
       str(_da_tabela))
checar({str(c["eqs"]["company_id"]) for c in _da_tabela} == {X, Y},
       "e cada uma levou a corretora DELA — nenhuma leu pela outra")

print()
print("=" * 74)
print("[G3] A MESMA CONVERSA-MOLDE, DUAS CORRETORAS, RESULTADOS INDEPENDENTES")
print("=" * 74)
_real_numeros = G.numeros_da_casa


async def _numeros(db, company_id):
    return await _real_numeros(BANCO, company_id)


G.numeros_da_casa = _numeros
pode_x, porque_x = rodar(G.o_grupo_pode_saber(
    BANCO, company_id=X, tipo=G.TIPO_PEDIDO_DE_AJUDA, telefone=FONE_DA_CASA))
pode_y, porque_y = rodar(G.o_grupo_pode_saber(
    BANCO, company_id=Y, tipo=G.TIPO_PEDIDO_DE_AJUDA, telefone=FONE_DA_CASA))
checar(not pode_x and porque_x == "é um número da própria corretora",
       "🔴 em X, o aviso CALA: é um número da casa dela", porque_x)
checar(pode_y,
       "🔴 e em Y o MESMO aviso PASSA — a lista de X não cala a conversa de Y",
       f"{pode_y} / {porque_y}")
# 🔴 CONTROLE: a guarda não é um "cala sempre" nem um "passa sempre".
pode_x2, _ = rodar(G.o_grupo_pode_saber(
    BANCO, company_id=X, tipo=G.TIPO_PEDIDO_DE_AJUDA, telefone=FONE_DE_FORA))
checar(pode_x2, "🔴 CONTROLE: em X, um número de FORA da casa passa")
pode_x3, _ = rodar(G.o_grupo_pode_saber(
    BANCO, company_id="", tipo=G.TIPO_PEDIDO_DE_AJUDA, telefone=FONE_DE_FORA))
checar(not pode_x3, "🔴 sem corretora não há isolamento possível: a guarda recusa")
G.numeros_da_casa = _real_numeros

print()
print("=" * 74)
print("[G4] A ROTA DO PAINEL NUNCA ACEITA `company_id` DE FORA")
print("=" * 74)
# ⚠️ LIMITE NOMEADO: a rota é TypeScript e não há harness de TS aqui, então
#    esta prova é ESTRUTURAL — sobre o texto da rota, não sobre a execução dela.
#    Ela pega o defeito que interessa (a corretora vinda do corpo) e não pega um
#    erro de runtime do Next. Fica dito.
ROTA = os.path.join(os.path.dirname(RAIZ), "app", "api", "dashboard",
                    "internal-numbers", "route.ts")
fonte = open(ROTA, encoding="utf-8").read()
checar(bool(fonte), "a rota existe no caminho da 001.3", ROTA)
_corpo = re.findall(r"body\s*as\s*any\)\.company_id|body\.company_id|companyId:\s*\(?body",
                    fonte)
checar(not _corpo, "🔴 a rota NUNCA lê `company_id` do corpo da requisição", str(_corpo))
_tabela = [linha for linha in fonte.splitlines() if "from(TABELA)" in linha]
checar(len(_tabela) == 3,
       f"📊 a rota toca `company_internal_numbers` em {len(_tabela)} lugares "
       "(GET, POST, DELETE)", str(len(_tabela)))
for verbo, marca in (("GET", "auth.ctx.companyId"), ("POST", "porteiro.companyId"),
                     ("DELETE", "porteiro.companyId")):
    bloco = fonte.split(f"export async function {verbo}", 1)[1].split("export async function")[0]
    checar("from(TABELA)" in bloco and marca in bloco,
           f"🔴 o {verbo} filtra/grava por `{marca}` — a corretora da SESSÃO")
# 🔴 CONTROLE do guarda: ele CONSEGUE ficar vermelho (CLAUDE.md §9.3).
_mutada = fonte.replace("company_id: porteiro.companyId",
                        "company_id: (body as any).company_id")
_achou = re.findall(r"body\s*as\s*any\)\.company_id", _mutada)
checar(bool(_achou),
       "🔴 CONTROLE: com a corretora vinda do corpo, o guarda acima FICA VERMELHO")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
