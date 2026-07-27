"""SPEC-062 §14 — o Release Manifest e o Evidence Pack.

A pergunta que isto responde
----------------------------
> *"O que exatamente foi para produção, e com que prova?"*

Hoje a resposta mora na memória de quem implantou. Daqui a três semanas, quando
alguma coisa quebrar, "o que mudou?" é a primeira pergunta — e ela não tem
resposta consultável.

O que o manifesto contém
------------------------
Só fato verificável no momento da geração:

    commit, branch, árvore limpa ou suja
    o gate de conduta rodado AGORA, com o resultado real
    os datasets de eval existentes e seus cortes
    as migrations presentes no repositório
    a versão de Python

O que ele deliberadamente NÃO contém
------------------------------------
**Nenhum segredo.** Nem valor, nem prefixo, nem os quatro últimos caracteres.
Um manifesto é feito para ser colado em ticket, anexado em e-mail e guardado
por anos — é o pior lugar possível para um pedaço de chave. Presença e ausência
bastam para diagnosticar.

E **nenhuma nota inventada**: se o gate não rodou, o campo diz que não rodou.
Um manifesto que preenche lacuna com otimismo é pior que não ter manifesto,
porque alguém vai confiar nele.

Uso
---
    python scripts/release_manifest.py            # imprime
    python scripts/release_manifest.py --gravar   # + grava em release_candidates
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Variáveis cuja PRESENÇA importa para diagnóstico. O valor nunca é lido.
CONFIGURACOES_OBSERVADAS = (
    "SUPABASE_URL", "REDIS_URL", "QDRANT_HOST", "MINIO_ENDPOINT",
    "EVOLUTION_GO_BASE_URL", "WHATSAPP_CHANNEL_PROVIDER",
    "BILLING_ENFORCEMENT", "COMMERCIAL_GO_LIVE_AT",
    "CARTOGRAPHER_MODE", "TOOL_GATEWAY_MODE", "BUILD_BRANCH",
)


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                           text=True, timeout=10)
        return (r.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _rodar_gate() -> dict:
    """Roda o pacote de conduta e lê o resultado REAL da saída."""
    caminho = os.path.join(RAIZ, "tests", "broker_outcome_regression_pack.py")
    if not os.path.exists(caminho):
        return {"rodou": False, "motivo": "pacote de conduta não encontrado"}
    try:
        r = subprocess.run([sys.executable, caminho], cwd=RAIZ,
                           capture_output=True, text=True, timeout=900)
    except Exception as exc:  # noqa: BLE001
        return {"rodou": False, "motivo": f"falhou ao executar: {type(exc).__name__}"}

    saida = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"passaram=(\d+)\s+falhas_obrigatorias=(\d+).*?total=(\d+)", saida)
    if not m:
        # Sem número legível, o honesto é dizer que não sabe — não chutar.
        return {"rodou": True, "verde": r.returncode == 0,
                "motivo": "saída sem contagem legível",
                "codigo_de_saida": r.returncode}
    return {
        "rodou": True,
        "verde": r.returncode == 0 and int(m.group(2)) == 0,
        "passaram": int(m.group(1)),
        "falhas_obrigatorias": int(m.group(2)),
        "total": int(m.group(3)),
        "codigo_de_saida": r.returncode,
    }


def _datasets_de_eval() -> dict:
    try:
        sys.path.insert(0, RAIZ)
        from app.core.database import get_supabase_client  # noqa: PLC0415
        from app.services.evals.runner import CORTE_POR_RISCO  # noqa: PLC0415

        db = get_supabase_client()
        raw = getattr(db, "client", db)
        ds = raw.table("eval_datasets").select("slug, dominio, risco, is_active") \
            .eq("is_active", True).execute().data or []
        return {"disponivel": True,
                "conjuntos": [{**d, "corte": CORTE_POR_RISCO.get(d.get("risco"), 0.90)}
                              for d in ds]}
    except Exception as exc:  # noqa: BLE001
        return {"disponivel": False, "motivo": type(exc).__name__}


def montar() -> dict:
    sujo = _git("status", "--porcelain")
    migrations = sorted(
        f for f in os.listdir(os.path.join(RAIZ, "supabase", "migrations"))
        if f.endswith(".sql")
    ) if os.path.isdir(os.path.join(RAIZ, "supabase", "migrations")) else []

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "codigo": {
            "commit": _git("rev-parse", "--short", "HEAD"),
            "commit_completo": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "assunto": _git("log", "-1", "--format=%s"),
            # Árvore suja significa que o que está rodando NÃO é o que o commit
            # diz. É a diferença entre um manifesto e uma ficção.
            "arvore_limpa": not bool(sujo),
            "arquivos_nao_commitados": len(sujo.splitlines()) if sujo else 0,
        },
        "gate_de_conduta": _rodar_gate(),
        "evals": _datasets_de_eval(),
        "migrations_no_repositorio": {
            "quantidade": len(migrations),
            "ultimas": migrations[-5:],
        },
        # Presença e ausência. Nunca o valor, nem parte dele.
        "configuracao": {
            nome: ("presente" if os.getenv(nome) else "ausente")
            for nome in CONFIGURACOES_OBSERVADAS
        },
        "runtime": {"python": sys.version.split()[0]},
    }


def gravar(manifesto: dict) -> str:
    try:
        sys.path.insert(0, RAIZ)
        from app.core.database import get_supabase_client  # noqa: PLC0415

        db = get_supabase_client()
        raw = getattr(db, "client", db)
        commit = manifesto["codigo"]["commit_completo"]
        if not commit:
            return "sem commit — nada gravado"
        existente = raw.table("release_candidates").select("id") \
            .eq("commit_sha", commit).limit(1).execute().data or []
        if existente:
            raw.table("release_candidates").update(
                {"manifesto": manifesto}).eq("id", existente[0]["id"]).execute()
            return f"atualizado: {commit[:8]}"
        raw.table("release_candidates").insert({
            "commit_sha": commit,
            "branch": manifesto["codigo"]["branch"],
            "manifesto": manifesto,
            "status": "aberto",
        }).execute()
        return f"registrado: {commit[:8]}"
    except Exception as exc:  # noqa: BLE001
        return f"não gravado ({type(exc).__name__})"


def main() -> int:
    m = montar()
    print(json.dumps(m, ensure_ascii=False, indent=2))
    if "--gravar" in sys.argv:
        print("\n" + gravar(m), file=sys.stderr)
    gate = m.get("gate_de_conduta") or {}
    # O código de saída reflete a verdade do gate: um manifesto que sai 0 com o
    # gate vermelho seria exatamente o otimismo que este arquivo evita.
    return 0 if gate.get("verde") else 1


if __name__ == "__main__":
    sys.exit(main())
