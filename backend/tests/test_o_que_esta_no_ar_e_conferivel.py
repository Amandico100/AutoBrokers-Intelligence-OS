# -*- coding: utf-8 -*-
"""P-189 — a digital do código precisa CONSEGUIR divergir.

Um marcador de versão que nunca muda é pior que marcador nenhum: ele dá a
sensação de conferência sem conferir nada. Então aqui não basta provar que a
função devolve uma string — é preciso provar que ela **muda** quando o código
muda, e que **não muda** quando só o fim de linha muda.

Esse segundo par é o que impede o alarme falso diário: o repositório é editado
no Windows (CRLF) e roda em contêiner Linux (LF). Se a digital dependesse dos
bytes crus, ela divergiria sempre — e um alarme que sempre toca é um alarme que
ninguém escuta.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location(
    "portal_worker_impressao", ROOT / "portal_worker" / "impressao.py")
IMP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(IMP)

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:200] if extra else ""))


def _arvore(base: Path, arquivos: dict) -> Path:
    for rel, conteudo in arquivos.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(conteudo)
    return base


BASE = {
    "a.py": b"def f():\n    return 1\n",
    "sub/b.py": b"X = 2\n",
}

tmp = Path(tempfile.mkdtemp(prefix="impressao_"))
try:
    # ======================================================================
    print("\n[1] a digital e estavel para o MESMO codigo")
    # ======================================================================
    d1 = _arvore(tmp / "um", dict(BASE))
    d2 = _arvore(tmp / "dois", dict(BASE))
    h1, n1 = IMP.impressao_do_diretorio(d1)
    h2, n2 = IMP.impressao_do_diretorio(d2)
    check("1: duas copias identicas dao a MESMA digital", h1 == h2, (h1, h2))
    check("1: e contam os mesmos 2 arquivos", n1 == n2 == 2, (n1, n2))
    check("1: a digital tem 16 hex", len(h1) == 16 and all(
        c in "0123456789abcdef" for c in h1), h1)

    # ======================================================================
    print("\n[2] CONTEUDO diferente -> digital diferente")
    # ======================================================================
    d3 = _arvore(tmp / "tres", {**BASE, "a.py": b"def f():\n    return 2\n"})
    h3, _ = IMP.impressao_do_diretorio(d3)
    check("2: um byte de logica muda a digital", h3 != h1, (h1, h3))

    # ======================================================================
    print("\n[3] NOME diferente -> digital diferente, mesmo com bytes iguais")
    # ======================================================================
    # Renomear um modulo muda o que o processo consegue importar. Se a digital
    # ignorasse o caminho, uma journey renomeada passaria por 'sem mudanca'.
    d4 = _arvore(tmp / "quatro", {"a.py": BASE["a.py"], "sub/c.py": BASE["sub/b.py"]})
    h4, _ = IMP.impressao_do_diretorio(d4)
    check("3: renomear b.py para c.py muda a digital", h4 != h1, (h1, h4))

    # ======================================================================
    print("\n[4] arquivo A MAIS -> digital diferente")
    # ======================================================================
    d5 = _arvore(tmp / "cinco", {**BASE, "sub/novo.py": b"Y = 3\n"})
    h5, n5 = IMP.impressao_do_diretorio(d5)
    check("4: um modulo novo muda a digital", h5 != h1, (h1, h5))
    check("4: e a contagem sobe para 3", n5 == 3, n5)

    # ======================================================================
    print("\n[5] CRLF vs LF -> MESMA digital (o alarme falso que nao pode tocar)")
    # ======================================================================
    d6 = _arvore(tmp / "seis", {k: v.replace(b"\n", b"\r\n") for k, v in BASE.items()})
    h6, _ = IMP.impressao_do_diretorio(d6)
    check("5: o mesmo codigo em CRLF da a MESMA digital que em LF", h6 == h1,
          (h1, h6))
    check("5 CONTROLE: e os bytes eram MESMO diferentes",
          (d6 / "a.py").read_bytes() != (d1 / "a.py").read_bytes())

    # ======================================================================
    print("\n[6] __pycache__ nao entra (senao a digital muda ao rodar)")
    # ======================================================================
    d7 = _arvore(tmp / "sete", {**BASE, "__pycache__/a.cpython-314.py": b"lixo\n"})
    h7, n7 = IMP.impressao_do_diretorio(d7)
    check("6: cache compilado nao muda a digital", h7 == h1, (h1, h7))
    check("6: nem entra na contagem", n7 == 2, n7)

    # ======================================================================
    print("\n[7] nunca levanta, e o /health nao quebra por causa dela")
    # ======================================================================
    inexistente = tmp / "nao_existe_este_caminho"
    try:
        hv, nv = IMP.impressao_do_diretorio(inexistente)
        check("7: diretorio inexistente devolve digital de arvore vazia",
              isinstance(hv, str) and nv == 0, (hv, nv))
    except Exception as e:  # noqa: BLE001
        check("7: diretorio inexistente devolve digital de arvore vazia",
              False, f"{type(e).__name__}: {e}")

    d_vazio = tmp / "vazio"
    d_vazio.mkdir()
    hz, nz = IMP.impressao_do_diretorio(d_vazio)
    check("7 CONTROLE: arvore vazia difere de arvore com codigo", hz != h1)

    # ======================================================================
    print("\n[8] o processo real responde, e bate com o disco")
    # ======================================================================
    hp, np_ = IMP.impressao_do_processo()
    hd, nd = IMP.impressao_do_diretorio(ROOT / "portal_worker")
    check("8: impressao_do_processo bate com a do diretorio", hp == hd, (hp, hd))
    check("8: e conta o mesmo tanto de arquivos", np_ == nd and nd > 10, (np_, nd))
    check("8: a segunda chamada usa cache (mesmo valor)",
          IMP.impressao_do_processo() == (hp, np_))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 64)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 64)
sys.exit(1 if FAIL else 0)
