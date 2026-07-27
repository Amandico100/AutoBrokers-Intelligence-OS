"""SPEC-062 §13 — o Eval Run e o gate que decide.

O que o gate de conduta NÃO responde
------------------------------------
O `broker_outcome_regression_pack` prova **conduta**: o código faz o que deve,
e a resposta é sim ou não. Ele não prova **qualidade**: se a resposta continua
boa. São perguntas diferentes.

Conduta é binária e não tem meio-termo — ou o Observador está mudo, ou não
está. Qualidade é comparativa: a nota de hoje só significa alguma coisa ao lado
da de ontem, na MESMA versão do dataset. É por isso que versão existe.

Como o gate decide (§13)
------------------------
Não é uma nota única para tudo. O corte vem do RISCO do domínio:

    critico   1.00   nada passa com falha. Vazamento, cross-tenant, silêncio
                     do Observador. Um caso reprovado reprova o run.
    alto      0.95
    medio     0.90
    baixo     0.80

Um dataset crítico com 99% é reprovado — e deve ser. Noventa e nove por cento
de silêncio significa que um segurado recebeu resposta de robô.

O peso do caso entra na nota, mas **não** salva o crítico: peso distribui
importância dentro do domínio, não compra exceção.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .evaluators import julgar

logger = logging.getLogger(__name__)

# §13 — o corte por risco do domínio.
CORTE_POR_RISCO = {
    "critico": 1.00,
    "alto": 0.95,
    "medio": 0.90,
    "baixo": 0.80,
}


def commit_atual() -> Optional[str]:
    """O commit que está rodando. Sem ele, uma queda de nota não tem causa."""
    if os.getenv("BUILD_COMMIT"):
        return os.getenv("BUILD_COMMIT")
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


class ExecutorDeAvaliacao:
    """Roda uma versão de dataset e registra a prova.

    O `alvo` é uma função `(entrada) -> saida`. Quem chama decide o que está
    sendo avaliado — o chat, uma skill, o tecelão do Atlas. O executor não sabe
    e não precisa saber: ele compara saída com contrato.
    """

    def __init__(self, supabase_client: Any = None):
        raw = supabase_client or self._cliente_padrao()
        self.db = getattr(raw, "client", raw) if raw else None

    @staticmethod
    def _cliente_padrao() -> Any:
        try:
            from ...core.database import get_supabase_client

            return get_supabase_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Evals] sem banco: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------
    def executar(self, *, dataset_slug: str, alvo: Callable[[Any], Any],
                 versao: Optional[int] = None, modelo: Optional[str] = None,
                 provedor: Optional[str] = None,
                 gatilho: str = "manual",
                 persistir: bool = True) -> dict:
        dataset, version, casos = self._carregar(dataset_slug, versao)
        if not dataset:
            return {"ok": False, "erro": f"dataset '{dataset_slug}' não encontrado"}
        if not casos:
            # Dataset vazio devolvendo nota 1.0 seria um gate verde que não
            # provou nada — a pior espécie de verde.
            return {"ok": False, "erro": (
                f"o dataset '{dataset_slug}' não tem nenhum caso. Um gate que "
                "passa sem caso não prova nada.")}

        risco = str(dataset.get("risco") or "medio")
        corte = CORTE_POR_RISCO.get(risco, 0.90)

        run_id = self._abrir_run(version, modelo, provedor, gatilho,
                                 len(casos)) if persistir else None

        resultados: list[dict] = []
        peso_total = 0.0
        peso_ok = 0.0
        reprovou_critico = False

        for caso in casos:
            peso = float(caso.get("peso") or 1)
            peso_total += peso
            entrada = caso.get("entrada")
            esperado = caso.get("expected") or {}

            inicio = time.perf_counter()
            try:
                saida = alvo(entrada)
                erro_alvo = None
            except Exception as exc:  # noqa: BLE001
                saida, erro_alvo = None, f"{type(exc).__name__}: {exc}"
            duracao = int((time.perf_counter() - inicio) * 1000)

            if erro_alvo is not None:
                vereditos = [{"evaluator_slug": "execucao", "passou": False,
                              "nota": 0.0,
                              "motivo": f"O alvo falhou ao responder — {erro_alvo}"}]
            else:
                vereditos = julgar(saida, esperado, entrada)

            passou_caso = all(v["passou"] for v in vereditos)
            if passou_caso:
                peso_ok += peso
            elif risco == "critico":
                reprovou_critico = True

            for v in vereditos:
                v["duracao_ms"] = duracao
                v["case_id"] = caso.get("id")
                v["chave"] = caso.get("chave")
            resultados.extend(vereditos)

            if run_id:
                self._gravar(run_id, caso.get("id"), vereditos, duracao)

        nota = round(peso_ok / peso_total, 4) if peso_total else 0.0
        # O crítico é uma trava separada e não uma nota alta: 0,99 num domínio
        # crítico é um segurado que recebeu o que não devia.
        passou = (nota >= corte) and not reprovou_critico

        if run_id:
            self._fechar_run(run_id, passou, nota,
                             sum(1 for c in casos
                                 if all(v["passou"] for v in resultados
                                        if v.get("case_id") == c.get("id"))))

        falhas = [v for v in resultados if not v["passou"]]
        return {
            "ok": True,
            "run_id": run_id,
            "dataset": dataset_slug,
            "risco": risco,
            "versao": version.get("versao") if version else None,
            "commit": commit_atual(),
            "total_casos": len(casos),
            "nota": nota,
            "corte": corte,
            "passou": passou,
            "reprovou_por_caso_critico": reprovou_critico,
            "falhas": [{"chave": f.get("chave"), "juiz": f["evaluator_slug"],
                        "motivo": f["motivo"]} for f in falhas],
            "frase": self._frase(dataset_slug, risco, nota, corte, passou,
                                 len(falhas), reprovou_critico),
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _frase(slug: str, risco: str, nota: float, corte: float,
               passou: bool, falhas: int, critico: bool) -> str:
        if passou:
            return (f"'{slug}' passou com {nota:.0%} (mínimo {corte:.0%} para "
                    f"risco {risco}).")
        if critico:
            return (f"'{slug}' é de risco CRÍTICO e teve {falhas} falha(s). "
                    "Em domínio crítico não existe nota parcial: um caso "
                    "reprovado reprova o conjunto.")
        return (f"'{slug}' ficou em {nota:.0%} e o mínimo para risco {risco} é "
                f"{corte:.0%}. {falhas} caso(s) falharam.")

    # ------------------------------------------------------------------
    def _carregar(self, slug: str, versao: Optional[int]):
        if not self.db:
            return None, None, []
        try:
            ds = (self.db.table("eval_datasets").select("*")
                  .eq("slug", slug).eq("is_active", True).limit(1).execute().data or [])
            if not ds:
                return None, None, []
            dataset = ds[0]

            q = (self.db.table("eval_dataset_versions").select("*")
                 .eq("dataset_id", dataset["id"]))
            if versao is not None:
                q = q.eq("versao", int(versao))
            versoes = q.order("versao", desc=True).limit(1).execute().data or []
            if not versoes:
                return dataset, None, []
            version = versoes[0]

            casos = (self.db.table("eval_cases").select("*")
                     .eq("version_id", version["id"]).execute().data or [])
            return dataset, version, casos
        except Exception as exc:  # noqa: BLE001
            logger.error("[Evals] carga falhou: %s", type(exc).__name__)
            return None, None, []

    def _abrir_run(self, version, modelo, provedor, gatilho, total) -> Optional[str]:
        if not (self.db and version):
            return None
        try:
            r = self.db.table("eval_runs").insert({
                "version_id": version["id"],
                "commit_sha": commit_atual(),
                "modelo": modelo, "provedor": provedor,
                "gatilho": gatilho, "status": "running", "total": total,
            }).execute()
            return (r.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Evals] run não aberto: %s", type(exc).__name__)
            return None

    def _gravar(self, run_id, case_id, vereditos, duracao) -> None:
        if not (self.db and run_id and case_id):
            return
        try:
            self.db.table("eval_case_results").insert([{
                "run_id": run_id, "case_id": case_id,
                "evaluator_slug": v["evaluator_slug"], "passou": v["passou"],
                "nota": v["nota"], "motivo": v["motivo"], "duracao_ms": duracao,
            } for v in vereditos]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Evals] resultado não gravado: %s", type(exc).__name__)

    def _fechar_run(self, run_id, passou, nota, passaram) -> None:
        if not (self.db and run_id):
            return
        try:
            self.db.table("eval_runs").update({
                "status": "passed" if passou else "failed",
                "nota": nota, "passaram": passaram,
                "terminado_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", run_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Evals] run não fechado: %s", type(exc).__name__)
