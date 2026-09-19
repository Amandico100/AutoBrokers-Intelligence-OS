# -*- coding: utf-8 -*-
r"""🔴 A FILA DIZ A VERDADE — contador, ordem e os três estados da tela.

SPEC-EXTRA-001.5.1 · FATIA 1 (unidade A: D2, D3, D4). Três mentiras que a tela
de curadoria contava, cada uma medida em 19/09/2026:

```
D3  o contador contava a PÁGINA   `len(fila_de_curadoria(limite=60))` = 60,
                                  com 73 linhas esperando. As outras 13 não
                                  existiam para quem lia a tela
D4  a fila não tinha ORDEM        sem `ORDER BY`, quais 13 ficam de fora do teto
                                  muda a cada abertura — uma linha pode nunca
                                  aparecer para ser revisada
D2  o erro virava vazio           `route.ts` não testava `r.ok`; o `catch`
                                  devolvia objeto sem `itens`; `fila.itens || []`
                                  fechava o circuito e a tela escrevia
                                  "Nada esperando revisão" para um 500
```

🔴 O GUARDA CHAMA O MOTOR (CLAUDE.md §9.4). O contador e a ordem são medidos
chamando `contar_fila` e `fila_de_curadoria` de verdade — contra o BANCO real e
contra um duplo que EMBARALHA. A leitura estática só entra onde o alvo é a FORMA
da declaração em TypeScript (§9.4, exceção), e cada uma vem com a mutação que a
deixa vermelha.
"""
from __future__ import annotations

import importlib.util
import os
import random
import re
import sys
import tempfile
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)

from app.services.knowledge import assistance_plans_base as B  # noqa: E402
from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _dsn():
    dsn = os.environ.get("SUPABASE_DB_URL")
    if dsn:
        return dsn
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(RAIZ, ".env"))
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("SUPABASE_DB_URL")


class BancoQueEmbaralha(BaseEmMemoria):
    """O duplo, com uma diferença: ele devolve as linhas em ordem ALEATÓRIA.

    🔴 É a única forma honesta de provar que o `ORDER BY` carrega peso. Um duplo
    que devolve sempre na ordem de inserção deixaria o guarda verde mesmo com a
    ordenação apagada do módulo — o carimbo que o CLAUDE.md §9.3 chama de pior
    que teste nenhum. O Postgres sem `ORDER BY` também não promete ordem: o
    duplo só torna visível o que o banco tem direito de fazer.
    """

    def __init__(self, semente: int = 0) -> None:
        super().__init__()
        self._sorteio = random.Random(semente)

    def table(self, nome: str):
        linhas = self.tabelas.setdefault(nome, [])
        self._sorteio.shuffle(linhas)
        return super().table(nome)


def _base_com(n_servicos: int, semente: int = 0) -> BancoQueEmbaralha:
    """`n` serviços `proposto`, espalhados por 5 planos de 3 seguradoras."""
    db = BancoQueEmbaralha(semente)
    planos = []
    for i, (seg, ramo) in enumerate(
        [("porto", "auto"), ("tokio", "auto"), ("hdi", "residencial"),
         ("mapfre", "residencial"), ("allianz", "auto")]):
        planos.append(db.plano(insurer_key=seg, ramo=ramo, produto="Produto %d" % i,
                               plano="Plano %d" % i, nivel=i + 1, curadoria="proposto"))
    for k in range(n_servicos):
        db.tabelas.setdefault("insurer_assistance_services", []).append({
            "id": str(uuid.uuid4()), "plano_id": planos[k % len(planos)],
            "servico": "servico_%03d" % k, "coberto": "sim", "curadoria": "proposto",
            "documento_id": "doc-cg-0001", "pagina": 24, "confianca": "alta",
        })
    return db


# ---------------------------------------------------------------------------
print("\n[1] o CONTADOR conta a BASE, não a página — contra o BANCO real")
DSN = _dsn()
if not DSN:
    print("  \U0001F7E1 PULADO: `SUPABASE_DB_URL` ausente do ambiente e de backend/.env.")
else:
    try:
        import psycopg
    except ImportError:
        psycopg = None
    if psycopg is None:
        print("  \U0001F7E1 PULADO: `psycopg` (v3) não instalado.")
    else:
        with psycopg.connect(DSN, autocommit=True, prepare_threshold=None) as c, c.cursor() as cur:
            cur.execute("select count(*) from insurer_assistance_services "
                        "where curadoria = 'proposto'")
            no_sql = int(cur.fetchone()[0])
            cur.execute("select count(*) from insurer_assistance_services "
                        "where curadoria = 'rascunho'")
            rascunho_sql = int(cur.fetchone()[0])
        # ⚠️ O número NÃO é fixado no teste: ele é medido agora, pelo SQL, e
        # comparado com o que o módulo diz. 📊 19/09/2026 os dois davam 73.
        # Fixar "73" faria o guarda ficar vermelho no dia em que alguém
        # publicasse uma linha — punindo o trabalho certo.
        do_modulo = B.contar_fila()
        checar(do_modulo == no_sql,
               f"🔴 `contar_fila()` = o `count(*)` do banco ({no_sql} agora)",
               f"modulo={do_modulo} sql={no_sql}")
        # 🔴 CONTROLE: o contador CONSEGUE devolver outro número — senão a
        #    linha de cima passaria com uma função que devolve sempre o mesmo.
        checar(B.contar_fila(curadorias=("rascunho",)) == rascunho_sql
               and rascunho_sql != no_sql,
               f"🔴 CONTROLE: `curadorias=('rascunho',)` dá OUTRO número ({rascunho_sql})",
               f"modulo={B.contar_fila(curadorias=('rascunho',))} sql={rascunho_sql}")
        if no_sql > 3:
            pagina = B.fila_de_curadoria(limite=3)
            checar(len(pagina) == 3 and do_modulo != len(pagina),
                   "🔴 o contador (%d) NÃO é o tamanho da página (%d) — era esta "
                   "igualdade que fazia a tela dizer 60 com 73 esperando"
                   % (do_modulo, len(pagina)),
                   f"pagina={len(pagina)}")
            # 🔴 A ORDEM É ESTÁVEL NO BANCO REAL, não só no duplo.
            a = [l["id"] for l in B.fila_de_curadoria(limite=25)]
            b = [l["id"] for l in B.fila_de_curadoria(limite=25)]
            checar(a == b and len(a) > 0,
                   "duas chamadas seguidas ao BANCO REAL devolvem a MESMA ordem",
                   f"{len(a)} linhas; iguais={a == b}")

print("\n[2] o contador não pagina — 200 linhas, teto de 60")
db = _base_com(200, semente=1)
checar(B.contar_fila(db=db) == 200,
       "🔴 `contar_fila` vê as 200, sem `limit` nenhum",
       str(B.contar_fila(db=db)))
checar(len(B.fila_de_curadoria(limite=60, db=db)) == 60,
       "🔴 e `fila_de_curadoria(limite=60)` traz 60 — os dois números são "
       "DIFERENTES de propósito, e é o par que a tela mostra ('60 de 200')",
       str(len(B.fila_de_curadoria(limite=60, db=db))))

print("\n[3] a ORDEM sobrevive a um banco que embaralha")
db = _base_com(200, semente=2)
p1 = [l["id"] for l in B.fila_de_curadoria(limite=60, db=db)]
p2 = [l["id"] for l in B.fila_de_curadoria(limite=60, db=db)]
p3 = [l["id"] for l in B.fila_de_curadoria(limite=60, db=db)]
checar(p1 == p2 == p3 and len(p1) == 60,
       "🔴 três aberturas seguidas dão a MESMA página, na MESMA ordem, mesmo "
       "com o transporte devolvendo tudo embaralhado",
       f"iguais={p1 == p2 == p3}")
chaves = [(l["insurer_key"], l["ramo"], l["produto"], l["plano"], l["servico"])
          for l in B.fila_de_curadoria(limite=60, db=db)]
checar(chaves == sorted(chaves),
       "e a leitura sai agrupada por seguradora → ramo → produto → plano → serviço",
       str(chaves[:3]))

print("\n[4] 🔴 A MUTAÇÃO — sem o `ORDER BY`, o guarda acima fica VERMELHO")
# A mutação roda numa CÓPIA do módulo (protocolo §10), nunca no arquivo vivo.
fonte = open(os.path.join(RAIZ, "app", "services", "knowledge",
                          "assistance_plans_base.py"), "r", encoding="utf-8").read()
mutada = re.sub(r'\n\s*\.order\("(plano_id|servico|id)"\)', "", fonte)
checar(mutada != fonte and '.order("plano_id")' not in mutada,
       "a mutação de fato APAGA o `ORDER BY` da cópia (senão ela não prova nada)",
       f"tamanho {len(fonte)} -> {len(mutada)}")
_pasta = tempfile.mkdtemp(prefix="sem_order_by_")
try:
    caminho = os.path.join(_pasta, "apb_mutado.py")
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(mutada)
    spec = importlib.util.spec_from_file_location("apb_mutado", caminho)
    M = importlib.util.module_from_spec(spec)
    sys.modules["apb_mutado"] = M
    spec.loader.exec_module(M)
    db = _base_com(200, semente=3)
    q1 = [l["id"] for l in M.fila_de_curadoria(limite=60, db=db)]
    q2 = [l["id"] for l in M.fila_de_curadoria(limite=60, db=db)]
    checar(q1 != q2,
           "🔴 na cópia SEM `ORDER BY`, duas aberturas trazem páginas "
           "DIFERENTES — o guarda [3] consegue ficar vermelho",
           f"iguais={q1 == q2} (comuns: {len(set(q1) & set(q2))}/60)")
finally:
    sys.modules.pop("apb_mutado", None)
    import shutil

    shutil.rmtree(_pasta, ignore_errors=True)

# ---------------------------------------------------------------------------
# ⚠️ Daqui para baixo a leitura é ESTÁTICA, e é legítima (CLAUDE.md §9.4,
# exceção): o alvo é a FORMA da declaração em TypeScript — "existe o teste de
# `r.ok`?", "o `catch` devolve `itens`?" —, não o comportamento de um motor
# Python. Cada afirmação vem com a MUTAÇÃO que a deixa vermelha.
print("\n[5] o `route.ts` testa `r.ok`, e NUNCA devolve `itens` de mentira")
ROTA = os.path.join(REPO, "app", "api", "dashboard", "knowledge", "planos", "route.ts")
rota = open(ROTA, "r", encoding="utf-8").read()
codigo = "\n".join(l for l in rota.splitlines() if not l.strip().startswith("//"))
checar("if (!r.ok)" in codigo,
       "🔴 `route.ts` testa `r.ok` antes de ler o corpo", ROTA)
checar("itens" not in codigo,
       "🔴 `route.ts` NÃO fabrica `itens` em lugar nenhum — quem não conseguiu "
       "falar com o backend devolve `{ok:false}`, e a tela decide o que dizer",
       [l for l in codigo.splitlines() if "itens" in l][:3])
# 🔴 CONTROLE: a varredura CONSEGUE acusar.
_mutada = codigo.replace("return { ok: false, error: 'indisponivel' };",
                         "return { ok: false, itens: [] };")
checar("itens" in _mutada,
       "🔴 CONTROLE: com `{ok:false, itens:[]}` no `catch`, a varredura FICA VERMELHA")
_sem_ok = codigo.replace("if (!r.ok)", "if (false)")
checar("if (!r.ok)" not in _sem_ok,
       "🔴 CONTROLE 2: tirando o `r.ok`, a varredura acima FICA VERMELHA")

print("\n[6] a tela tem TRÊS estados, e o vazio é o ÚLTIMO deles")
TELA = os.path.join(REPO, "app", "dashboard", "personalizacao", "conhecimento",
                    "FilaDeCuradoria.tsx")
bruta = open(TELA, "r", encoding="utf-8").read()
# ⚠️ As linhas de comentário saem ANTES da medição. 📊 A primeira versão deste
# guarda ficou vermelha porque achou "Nada esperando revisão" no cabeçalho que
# EXPLICA os três estados — comentário casando como se fosse código é a mesma
# armadilha do CLAUDE.md §9.4 (prosa não é chamada).
tela = "\n".join(l for l in bruta.splitlines() if not l.strip().startswith("//"))
for texto in ("Não consegui carregar a fila agora", "Nada esperando revisão",
              "Esperando sua revisão", "mostrando ", "Tentar de novo"):
    checar(texto in tela, f"a tela tem o texto {texto!r}")
i_erro = tela.find("fila?.ok !== true")
i_vazio_if = tela.find("if (!itens.length)")
i_vazio_txt = tela.find("Nada esperando revisão")
checar(0 < i_erro < i_vazio_if < i_vazio_txt,
       "🔴 'Nada esperando revisão' só é alcançável DEPOIS do `fila?.ok !== true` "
       "e dentro do `if (!itens.length)` — erro nunca cai no estado vazio",
       f"ok={i_erro} if_vazio={i_vazio_if} texto={i_vazio_txt}")
# 🔴 CONTROLE: sem a porta do erro, a ordem quebra e esta linha fica vermelha.
_sem_porta = tela.replace("fila?.ok !== true", "false /* porta removida */")
checar(_sem_porta.find("fila?.ok !== true") == -1,
       "🔴 CONTROLE: removida a porta do erro, a checagem de ordem acima "
       "perde a âncora e FICA VERMELHA")
checar("Array.isArray(fila?.itens)" in tela and "itens || []" not in tela,
       "🔴 e o `|| []` que fundia erro com vazio NÃO existe mais na tela",
       [l for l in tela.splitlines() if "itens || []" in l][:2])

print("\n[7] o botão cinza EXPLICA (D9)")
checar("Só dá para aprovar depois de ler a página" in tela,
       "o botão desabilitado por falta da página diz POR QUÊ")
checar("motivoDaFonte" in tela and "fonte_ausente" in tela,
       "e o motivo vem traduzido do código que o backend manda "
       "(`motivo_da_fonte`), em português, sem nome de tabela")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
