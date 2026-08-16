"""Corrigir o TEXTO de uma carta não pode destruir a PROVA dela.

O DEFEITO — P-176, achado pelo juiz crítico do BLOCO 0 da SPEC-072
===================================================================
`corrigir.py` troca uma carta errada por uma certa. O `select` dele pedia cinco
colunas e nenhuma delas carregava procedência, e disso saíam **dois danos com
gravidades diferentes** — a distinção importa e por isso o teste anda nas duas:

🟢 **O menor.** Sem `pii_check` no select, o
`marca = {**(c.get("pii_check") or {}), …}` espalhava um dict SEMPRE VAZIO, e o
`update` substituía a coluna inteira por duas chaves. Morriam `faceta`, `origem`
e `reindexado_em`. É menor porque essa carta está sendo **aposentada** no mesmo
update: perde-se o rastro de auditoria de quem já saiu do índice.

🔴 **O grave.** A carta **substituta** nascia sem `source_unit_id`. O lastro é o
produto (`attendance_distiller.py:639-652`): sem ele, *"a cláusula 4.4.2.d das
Condições Gerais vigentes desde 01/07/2026 diz que não cobre"* vira *"acho que
não cobre"*. E ela entraria em `publicar_lote_sync` com `documento_publico=False`
— **o caso exato que o BLOCO 0 fechou**, reaberto por outra porta.

> **O conserto de conteúdo destruía a prova. E ninguém desconfiaria: a carta
> nova está mais certa que a velha.**

⚠️ SÃO TRÊS COLUNAS DE PROCEDÊNCIA, NÃO UMA
============================================
`20260808_03_spec070_a_carta_sabe_de_que_contrato_saiu.sql:154-159` criou a FK
composta `knowledge_cards_procedencia_coerente_fk (source_version_id,
source_document_id)`. Propagar só o `unit_id` daria uma carta com **endereço e
sem documento** — coerente na aparência, incoerente no schema.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
=====================================
Cada caso tem um par que difere em **um fator só**:

    original COM procedência  ×  original SEM procedência  → a nova não inventa
    `pii_check` no select     ×  o select de ontem          → a marca é apagada

MUTAÇÃO (CLAUDE.md §9.3)
=========================
`teste_a_mutacao_derruba_o_guarda` reconstrói a linha que o `select` ANTIGO
devolvia e prova que os guardas **reprovam** com ela.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ─────────────────────────────────────────────────────────────────────────────
# O banco é um dublê que REGISTRA. O que se testa é o que `corrigir.py` grava.
# ─────────────────────────────────────────────────────────────────────────────
class _Consulta:
    def __init__(self, tabela, registro, linha_devolvida):
        self._t = tabela
        self._reg = registro
        self._linha = linha_devolvida
        self._op = None
        self._dados = None

    def select(self, colunas):
        self._op = "select"
        self._reg.append(("select", colunas))
        return self

    def update(self, dados):
        self._op = "update"
        self._dados = dados
        return self

    def upsert(self, dados, **kw):
        self._op = "upsert"
        self._reg.append(("upsert", dados[0] if isinstance(dados, list) else dados))
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._op == "update":
            self._reg.append(("update", self._dados))
        return types.SimpleNamespace(
            data=[dict(self._linha)] if self._op == "select" and self._linha else [])


class _Banco:
    def __init__(self, linha):
        self.registro: list = []
        self._linha = linha

    def table(self, nome):
        return _Consulta(nome, self.registro, self._linha)


def _rodar(linha_do_banco: dict) -> list:
    """Roda `corrigir.py --aplicar` contra um banco de mentira. Devolve o registro."""
    banco = _Banco(linha_do_banco)

    sup = types.ModuleType("supabase")
    sup.create_client = lambda url, key: banco
    sys.modules["supabase"] = sup

    os.environ.setdefault("SUPABASE_URL", "https://teste.local")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "chave-de-mentira")

    argv, cwd = sys.argv[:], os.getcwd()
    sys.argv = ["corrigir.py", "--aplicar"]
    sys.modules.pop("corrigir", None)
    try:
        os.chdir(os.path.join(RAIZ, "scripts", "destilacao_max"))
        caminho = os.path.join(RAIZ, "scripts", "destilacao_max", "corrigir.py")
        spec = importlib.util.spec_from_file_location("corrigir", caminho)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["corrigir"] = mod
        spec.loader.exec_module(mod)
        mod.main()
    finally:
        sys.argv = argv
        os.chdir(cwd)
    return banco.registro


def _upserts(reg):
    return [d for op, d in reg if op == "upsert"]


def _updates(reg):
    return [d for op, d in reg if op == "update"]


UNIT = "norm-d24fa589-e261-48c6-bfee-983097b15873-v2#0031"
DOC = "11111111-1111-1111-1111-111111111111"
VER = "22222222-2222-2222-2222-222222222222"

COMPLETA = {
    "id": "07886e88-6d28-48dd-a120-f9b4979aeebd",
    "card_text": "A franquia de impacto de veiculos e um percentual fixo de 20%.",
    "ramo": "residencial", "insurer_key": "porto", "status": "published",
    "pii_check": {"deterministic": True, "origem": "acervo", "faceta": "franquia",
                  "reindexado_em": "2026-08-10"},
    "source_unit_id": UNIT, "source_document_id": DOC, "source_version_id": VER,
}

# O que o `select` de ONTEM devolvia — cinco colunas, nenhuma de procedência.
DE_ONTEM = {k: COMPLETA[k] for k in ("id", "card_text", "ramo", "insurer_key", "status")}


# ═════════════════════════════════════════════════════════════════════════════
def teste_a_substituta_herda_a_procedencia() -> None:
    print("\n[1] a carta corrigida herda o caminho de volta ao contrato")
    reg = _rodar(COMPLETA)
    ups = _upserts(reg)
    checar(bool(ups), "alguma carta nova foi inserida", f"{len(ups)} upserts")
    nova = ups[0] if ups else {}

    checar(nova.get("source_unit_id") == UNIT,
           "a substituta leva source_unit_id", f"veio {nova.get('source_unit_id')!r}")
    checar(nova.get("source_document_id") == DOC,
           "e source_document_id — a FK composta exige as duas")
    checar(nova.get("source_version_id") == VER, "e source_version_id")
    checar((nova.get("pii_check") or {}).get("faceta") == "franquia",
           "e a faceta, que mora em pii_check",
           f"veio {(nova.get('pii_check') or {}).get('faceta')!r}")
    checar((nova.get("pii_check") or {}).get("corrige") == COMPLETA["id"],
           "sem perder a marca de que ela corrige alguém")
    checar("origem" not in (nova.get("pii_check") or {}),
           "e NÃO herda `origem`: ela veio desta correção, não daquela rodada")


def teste_a_aposentada_nao_perde_as_marcas() -> None:
    print("\n[2] a carta que sai mantém o rastro de auditoria")
    upd = _updates(_rodar(COMPLETA))
    checar(bool(upd), "houve update", f"{len(upd)} updates")
    marca = (upd[0] if upd else {}).get("pii_check") or {}

    checar((upd[0] if upd else {}).get("status") == "superseded",
           "ela é aposentada, não apagada")
    checar(marca.get("faceta") == "franquia", "a faceta sobrevive ao update",
           f"pii_check={marca}")
    checar(marca.get("origem") == "acervo", "e `origem` também")
    checar(marca.get("reindexado_em") == "2026-08-10",
           "e `reindexado_em` — a memória que o deploy não apaga")
    checar(marca.get("superseded_por") and marca.get("motivo"),
           "e as marcas novas entram POR CIMA, sem substituir o dict")


def teste_controle_sem_procedencia_nao_se_inventa_uma() -> None:
    """LINHA DE CONTROLE: um fator só — a original não tem procedência."""
    print("\n[3] CONTROLE — carta de conversa: a nova não inventa procedência")
    sem = {**COMPLETA, "source_unit_id": None, "source_document_id": None,
           "source_version_id": None,
           "pii_check": {"deterministic": True, "por": "destilador"}}
    ups = _upserts(_rodar(sem))
    nova = ups[0] if ups else {}
    checar(bool(ups), "a carta nova é inserida do mesmo jeito")
    for col in ("source_unit_id", "source_document_id", "source_version_id"):
        checar(col not in nova, f"CONTROLE: `{col}` fica AUSENTE, não None",
               f"veio {nova.get(col)!r}")
    checar("faceta" not in (nova.get("pii_check") or {}),
           "CONTROLE: sem faceta na origem, sem faceta no destino")
    checar((nova.get("pii_check") or {}).get("corrige") == COMPLETA["id"],
           "CONTROLE: e o resto do pii_check continua sendo escrito "
           "(mudou UM fator só)")


def teste_a_mutacao_derruba_o_guarda() -> None:
    """MUTAÇÃO: a linha que o `select` de ontem devolvia tem de REPROVAR."""
    print("\n[4] MUTAÇÃO — o select de ontem tem de falhar")
    reg = _rodar(DE_ONTEM)
    nova = (_upserts(reg) or [{}])[0]
    marca = (_updates(reg) or [{}])[0].get("pii_check") or {}

    checar("source_unit_id" not in nova,
           "com o select antigo a substituta nasce SEM lastro — o guarda falha")
    checar("faceta" not in (nova.get("pii_check") or {}),
           "e sem faceta")
    checar("faceta" not in marca and "reindexado_em" not in marca,
           "e o update da aposentada APAGA as marcas antigas",
           f"pii_check={marca}")
    checar(marca.get("superseded_por") is not None,
           "(o update acontece — o dano é o que ele leva junto, não que falhe)")


def teste_o_select_pede_as_colunas() -> None:
    print("\n[5] o select de corrigir.py pede procedência e pii_check")
    with open(os.path.join(RAIZ, "scripts", "destilacao_max", "corrigir.py"),
              encoding="utf-8") as arquivo:
        fonte = arquivo.read()
    corpo = fonte.split("def main")[-1]
    import re
    sel = re.search(r'\.select\(\s*((?:"[^"]*"\s*)+)\)', corpo)
    cols = sel.group(1) if sel else ""
    checar(bool(sel), "o select é localizável")
    for col in ("pii_check", "source_unit_id", "source_document_id",
                "source_version_id"):
        checar(col in cols, f"pede `{col}`", f"select={cols[:110]!r}")


def main() -> int:
    print(__doc__.split("\n")[0])
    print("=" * 70)
    teste_a_substituta_herda_a_procedencia()
    teste_a_aposentada_nao_perde_as_marcas()
    teste_controle_sem_procedencia_nao_se_inventa_uma()
    teste_a_mutacao_derruba_o_guarda()
    teste_o_select_pede_as_colunas()

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("TUDO VERDE — corrigir o texto não destrói a prova.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
