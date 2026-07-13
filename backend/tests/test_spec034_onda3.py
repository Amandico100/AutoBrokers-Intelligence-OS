"""SPEC-034 Onda 3 - Garimpo v1 + RAG global opt-in + fiacao.

Rodar: python backend/tests/test_spec034_onda3.py

- GARIMPO (camada deterministica, custo zero): extrai desejos/dores/pedidos/
  churn/elogio das mensagens do USUARIO; ignora assistant; dedup; 1 por msg;
- fiacao: task diaria no scheduler; espelhos de seguradora (dispatch:) fora;
- RAG global: flag KNOWLEDGE_GLOBAL_SEARCH plugada no ponto unico da busca.
"""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


for name in ("app", "app.services", "app.core"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

gar = _load("app.services.broker_insights", "app/services/broker_insights.py")


def run():
    print("== SPEC-034 Onda 3 - Garimpo + RAG global ==\n")

    msgs = [
        {"role": "user", "content": "Bom dia! Tudo bem?"},
        {"role": "user", "content": "Eu queria muito um jeito de renovar as apolices em lote, faria diferenca"},
        {"role": "assistant", "content": "eu queria poder ajudar com isso"},
        {"role": "user", "content": "Tenho muita dificuldade com o relatorio de comissoes, toma muito tempo todo mes"},
        {"role": "user", "content": "voces poderiam colocar um lembrete de vencimento pros clientes?"},
        {"role": "user", "content": "se continuar assim vou cancelar a assinatura"},
        {"role": "user", "content": "o atendimento de voces me ajudou muito, parabens!"},
        {"role": "user", "content": "ok"},
    ]
    found = gar.extract_candidates(msgs)
    kinds = [f["kind"] for f in found]
    check("garimpo: 5 insights das msgs do usuario", len(found) == 5, kinds)
    check("garimpo: desejo detectado", "desejo" in kinds)
    check("garimpo: dor detectada", "dor" in kinds)
    check("garimpo: pedido de feature detectado", "pedido_feature" in kinds)
    check("garimpo: risco de churn detectado (prioridade sobre dor)", "risco_churn" in kinds)
    check("garimpo: elogio detectado", "elogio" in kinds)
    check("garimpo: mensagens do assistant NAO geram insight",
          all("poder ajudar" not in f["quote"] for f in found))
    check("garimpo: quote carrega o contexto do gatilho",
          any("renovar as apolices em lote" in f["quote"] for f in found))
    dup = gar.extract_candidates([msgs[1], msgs[1]])
    check("garimpo: dedup na propria extracao", len(dup) == 1, len(dup))
    check("garimpo: msg curta ignorada", gar.extract_candidates([{"role": "user", "content": "eu queria"}]) == [])

    src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("garimpo: task registrada no scheduler", "garimpo_check" in src and "check_garimpo" in src)
    gar_src = (ROOT / "app/services/broker_insights.py").read_text(encoding="utf-8")
    check("garimpo: espelhos de seguradora (dispatch:) excluidos", 'startswith("dispatch:")' in gar_src)

    search_src = (ROOT / "app/services/search_service.py").read_text(encoding="utf-8")
    check("rag global: flag KNOWLEDGE_GLOBAL_SEARCH no ponto unico da busca",
          "KNOWLEDGE_GLOBAL_SEARCH" in search_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
