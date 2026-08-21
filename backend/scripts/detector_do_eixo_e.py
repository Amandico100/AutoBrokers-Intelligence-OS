"""O detector do eixo E — *"o teste chama o MOTOR, ou chama o regex?"*

═══════════════════════════════════════════════════════════════════════════════
🔴 A CAUSA RAIZ QUE A SPEC-083 §1.3 DIAGNOSTICA
═══════════════════════════════════════════════════════════════════════════════

A rota da máquina de lavar tinha **72 asserções verdes** e o agendamento nunca
chegava ao cliente.

```bash
grep -cE 'CP\\.(match_ura_step|extract_capture_anchors|detect_finalize_anchor)' \\
     backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py
→ 0
```

**Zero chamadas ao motor em 401 linhas.** São dois desvios:

```
linha  64  passo_de(...)          REIMPLEMENTA `match_ura_step`
linha 295  _captura(chave, texto)  roda `re.search` direto sobre `capture_anchors`
```

> ## Teste que chama o regex não guarda o corredor — guarda o regex.

═══════════════════════════════════════════════════════════════════════════════
🔴 E POR QUE UM DETECTOR LITERAL NÃO SERVE
═══════════════════════════════════════════════════════════════════════════════

`Call.args[0]` comparado com `playbook["capture_anchors"][...]` **não alcança**.
📊 Os dois casos reais do repositório passam a âncora por **variável
intermediária**, e um deles usa `.get("anchor")`, que nem é subscrito:

```python
PASSOS = PB["ura_steps"]                    # linha 61
    anc = p.get("anchor")                   # linha 67
    re.search(anc, CP._norm(texto), ...)    # linha 68  → args[0] = Name('anc')

ANC = PB["capture_anchors"]                 # linha 280
    _re3.search(ANC[chave], ...)            # linha 296  → args[0] = Subscript(Name('ANC'))
```

**Um detector literal devolveria ZERO desqualificações no arquivo que a SPEC
nomeia como o exemplar do defeito. Fecharia o furo dizendo que fechou.**

Daí o TAINT LOCAL: uma semente se propaga por atribuição, subscrito e `for`.
"""

from __future__ import annotations

import ast
import os
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

# As chaves que, lidas de um dict, são ÂNCORA DE PLAYBOOK.
_CHAVES_DE_ANCORA = {
    "capture_anchors", "finalize_anchors", "handoff_triggers", "ura_steps",
    "anchor", "subservices", "native_flows",
}

# As funções do MOTOR. Chamar qualquer uma no mesmo `def` absolve o bloco.
FUNCOES_DO_MOTOR = {
    "match_ura_step", "extract_capture_anchors", "detect_finalize_anchor",
    "detect_handoff_trigger", "canonical_subservice", "missing_slots_for_subservice",
    "render_reply", "auto_subservice_menu_value", "subservice_supported",
    "detect_referral_step", "detect_native_flow", "render_opening_message",
    "conferir_confirmacao", "client_summary_from_capture",
    "_tela_pede_alguma_coisa", "tela_pede_alguma_coisa", "new_dispatch_session",
}

_BUSCA = {"search", "match", "fullmatch", "findall", "finditer", "sub", "subn"}


class Desqualificacao(NamedTuple):
    arquivo: str
    funcao: str
    linha: int
    expressao: str
    motivo: str


def _nome_da_chave(no: ast.AST) -> Optional[str]:
    """`x["anchor"]` -> `'anchor'` · `x.get("anchor")` -> `'anchor'`."""
    if isinstance(no, ast.Subscript):
        s = no.slice
        if isinstance(s, ast.Constant) and isinstance(s.value, str):
            return s.value
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
            and no.func.attr == "get" and no.args:
        a = no.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return a.value
    return None


class _Taint(ast.NodeVisitor):
    """Propaga a mancha `é âncora de playbook` dentro de um módulo.

    Três regras, e cada uma existe por um caso real:
      · `PASSOS = PB["ura_steps"]`        nome atribuído a semente vira semente
      · `for p in PASSOS`                 alvo de `for` sobre semente vira semente
      · `ANC[chave]` · `p.get("anchor")`  subscrito/atributo de semente vira semente
    """

    def __init__(self) -> None:
        self.sementes: Set[str] = set()

    # ── a semente nasce aqui ────────────────────────────────────────────────
    def e_semente(self, no: ast.AST) -> bool:
        chave = _nome_da_chave(no)
        if chave in _CHAVES_DE_ANCORA:
            return True
        # subscrito/atributo DE uma semente também é semente:  ANC[chave]
        if isinstance(no, ast.Subscript):
            return self.e_semente(no.value)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
                and no.func.attr == "get":
            return self.e_semente(no.func.value)
        if isinstance(no, ast.Attribute):
            return self.e_semente(no.value)
        if isinstance(no, ast.Name):
            return no.id in self.sementes
        # `PB["ura_steps"][3]` — o índice numérico não some com a mancha
        if isinstance(no, ast.Index):          # py<3.9
            return self.e_semente(no.value)    # pragma: no cover
        return False

    def visit_Assign(self, no: ast.Assign) -> None:
        if self.e_semente(no.value):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name):
                    self.sementes.add(alvo.id)
        self.generic_visit(no)

    def visit_AnnAssign(self, no: ast.AnnAssign) -> None:
        if no.value is not None and self.e_semente(no.value) \
                and isinstance(no.target, ast.Name):
            self.sementes.add(no.target.id)
        self.generic_visit(no)

    def visit_For(self, no: ast.For) -> None:
        if self.e_semente(no.iter) and isinstance(no.target, ast.Name):
            self.sementes.add(no.target.id)
        self.generic_visit(no)

    def visit_comprehension(self, no: ast.comprehension) -> None:  # pragma: no cover
        if self.e_semente(no.iter) and isinstance(no.target, ast.Name):
            self.sementes.add(no.target.id)


def _chama_o_motor(corpo: ast.AST) -> bool:
    for n in ast.walk(corpo):
        if isinstance(n, ast.Call):
            f = n.func
            nome = f.attr if isinstance(f, ast.Attribute) else \
                (f.id if isinstance(f, ast.Name) else None)
            if nome in FUNCOES_DO_MOTOR:
                return True
    return False


def analisar_modulo(caminho: str) -> List[Desqualificacao]:
    """Devolve as desqualificações de UM arquivo."""
    try:
        with open(caminho, encoding="utf-8") as fh:
            fonte = fh.read()
        arvore = ast.parse(fonte)
    except (OSError, SyntaxError):
        return []

    taint = _Taint()
    # duas passadas: a mancha pode nascer no módulo e ser usada numa função
    taint.visit(arvore)
    taint.visit(arvore)

    fora: List[Desqualificacao] = []
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _chama_o_motor(no):
            continue          # 🔴 chamou o motor no mesmo `def` → absolvido
        for c in ast.walk(no):
            if not isinstance(c, ast.Call):
                continue
            f = c.func
            if not (isinstance(f, ast.Attribute) and f.attr in _BUSCA):
                continue
            if not c.args:
                continue
            # 🔴 REGRA 4: `args[1]` NÃO desqualifica. A agulha virou palheiro —
            #    o regex ali inspeciona a FORMA da declaração, o que é legítimo
            #    (§3.6: *"o alvo é a captura que substitui o motor, não a
            #    inspeção da declaração"*).
            if taint.e_semente(c.args[0]):
                fora.append(Desqualificacao(
                    os.path.basename(caminho), no.name, c.lineno,
                    ast.unparse(c.args[0])[:60],
                    "regex sobre ancora de playbook, sem chamar o motor no mesmo def"))
    return fora


def _importados_de_tests(caminho: str) -> List[str]:
    """⚠️ A varredura cobre o arquivo **E todo módulo que ele importe de
    `backend/tests/`**. Um helper em `conftest.py` é o esconderijo óbvio da
    próxima geração deste defeito — 📊 foi um helper local que criou os dois
    atuais."""
    pasta = os.path.dirname(os.path.abspath(caminho))
    try:
        arvore = ast.parse(open(caminho, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return []
    nomes: Set[str] = set()
    for n in ast.walk(arvore):
        if isinstance(n, ast.Import):
            nomes.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            nomes.add(n.module.split(".")[0])
    fora = []
    for nome in nomes:
        p = os.path.join(pasta, nome + ".py")
        if os.path.exists(p):
            fora.append(p)
    conf = os.path.join(pasta, "conftest.py")
    if os.path.exists(conf) and conf not in fora:
        fora.append(conf)
    return fora


def analisar(caminho: str) -> List[Desqualificacao]:
    """O arquivo mais tudo que ele importa de `backend/tests/`."""
    fora = analisar_modulo(caminho)
    for extra in _importados_de_tests(caminho):
        fora.extend(analisar_modulo(extra))
    return fora


def qualifica(caminho: str) -> bool:
    """O arquivo pode pontuar no eixo E?"""
    return not analisar(caminho)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O CONTROLE OBRIGATÓRIO — sem ele o eixo E é decorativo (§3.6)
#
#   `passo_de`   em test_a_maquina_de_lavar_vai_ate_o_fim.py  → DESQUALIFICA
#   `_captura`   no mesmo arquivo                             → DESQUALIFICA
#   test_a_regua_nao_tem_furo.py, âncora em args[1]           → NÃO desqualifica
#
# 🔴 Se os dois primeiros passarem, o detector está CEGO. Este controle é o que
#    dá direito a confiar na nota.
# ═════════════════════════════════════════════════════════════════════════════
CONTROLE = (
    ("test_a_maquina_de_lavar_vai_ate_o_fim.py", "passo_de", True),
    ("test_a_maquina_de_lavar_vai_ate_o_fim.py", "_captura", True),
    ("test_a_regua_nao_tem_furo.py", None, False),
)
