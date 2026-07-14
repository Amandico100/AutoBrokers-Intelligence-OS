# -*- coding: utf-8 -*-
"""Monta o DATASET DE APÓLICES DE TESTE do Cartógrafo (autorização do founder 14/07).

Pipeline (100% determinístico — zero LLM):
1. Varre as conversas reais do intake (resulta/ + autofleet/) e extrai CPFs
   (regex) + nomes/seguradoras próximos;
2. Consulta a InfoCap (api.corpnuvem.com, credenciais CORP_INFOCAP_* do env)
   para validar apólice VIGENTE de cada CPF e descobrir seguradora/ramo/placa;
3. Escolhe 1 exemplo por seguradora × ramo e grava
   backend/data/cartographer_test_data.json (o runner lê daqui).

Rodar (na máquina com envs ou passando-os):
  python backend/scripts/build_cartographer_dataset.py \
    --intake "C:/.../AUTOBROKERS_RESULTA_INTAKE" --out backend/data/cartographer_test_data.json

Privacidade: o arquivo de saída fica FORA do git (adicionar ao .gitignore) —
contém CPFs reais de clientes; uso interno de teste apenas.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

CPF_RE = re.compile(r"\b(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})[-.\s]?(\d{2})\b")
INSURERS = ["allianz", "alfa", "azul", "bradesco", "hdi", "itau", "mapfre",
            "porto", "tokio", "yelum", "zurich", "sura", "sulamerica", "suhai", "sompo", "liberty"]


def valid_cpf(digits: str) -> bool:
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(digits[i]) * ((n + 1) - i) for i in range(n))
        d = (s * 10) % 11 % 10
        if d != int(digits[n]):
            return False
    return True


def scan_intake(root: Path) -> list[dict]:
    """CPFs + contexto (seguradora citada perto) das conversas exportadas."""
    found: dict[str, dict] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in (".txt", ".md", ".csv", ".json"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text.lower()
        for m in CPF_RE.finditer(text):
            cpf = "".join(m.groups())
            if not valid_cpf(cpf) or cpf in found:
                continue
            window = low[max(0, m.start() - 400): m.end() + 400]
            insurers = [i for i in INSURERS if i in window]
            found[cpf] = {"cpf": cpf, "fonte": str(path.name), "seguradoras_citadas": insurers}
    return list(found.values())


def infocap_login(base: str, login: str, password: str, application: str) -> str | None:
    import httpx

    try:
        r = httpx.post(f"{base}/api/v1/login", json={
            "login": login, "password": password, "application": int(application or 0)}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("token") or data.get("access_token") or (data.get("data") or {}).get("token")
    except Exception as e:  # noqa: BLE001
        print(f"  [!] login InfoCap falhou ({login}): {type(e).__name__}")
        return None


def infocap_policies(base: str, token: str, cpf: str) -> list[dict]:
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    for path in (f"/api/v1/clientes/{cpf}/apolices", f"/api/v1/apolices?cpf={cpf}",
                 f"/api/v1/policies?document={cpf}"):
        try:
            r = httpx.get(f"{base}{path}", headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get("data") or data.get("items") or []
                if items:
                    return items
        except Exception:  # noqa: BLE001
            continue
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intake", required=True)
    ap.add_argument("--out", default="backend/data/cartographer_test_data.json")
    ap.add_argument("--skip-infocap", action="store_true",
                    help="só varre as conversas (etapa 1) e lista os CPFs achados")
    args = ap.parse_args()

    root = Path(args.intake)
    if not root.exists():
        print(f"[X] intake não existe: {root}")
        return 1
    print(f"== Varrendo conversas em {root} ==")
    candidates = scan_intake(root)
    print(f"  {len(candidates)} CPFs válidos únicos encontrados")
    for c in candidates[:20]:
        print(f"  - {c['cpf'][:3]}***{c['cpf'][-2:]}  ({c['fonte']}; cita: {', '.join(c['seguradoras_citadas']) or '—'})")

    if args.skip_infocap:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"candidates": candidates}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] candidatos salvos em {args.out} (rode sem --skip-infocap para completar)")
        return 0

    base = os.getenv("CORP_INFOCAP_RESULTA_BASE_URL", "https://api.corpnuvem.com")
    accounts = [
        ("resulta", os.getenv("CORP_INFOCAP_RESULTA_LOGIN"), os.getenv("CORP_INFOCAP_RESULTA_PASSWORD"),
         os.getenv("CORP_INFOCAP_RESULTA_APPLICATION", "0")),
        ("autofleet", os.getenv("CORP_INFOCAP_AUTOFLEET_LOGIN"), os.getenv("CORP_INFOCAP_AUTOFLEET_PASSWORD"),
         os.getenv("CORP_INFOCAP_AUTOFLEET_APPLICATION", "0")),
    ]
    dataset: dict[str, dict] = {}
    for name, login, pwd, app_id in accounts:
        if not login:
            print(f"  [!] sem credencial {name} no env — pulando")
            continue
        token = infocap_login(base, login, pwd or "", app_id)
        if not token:
            continue
        print(f"== Consultando InfoCap ({name}) ==")
        for c in candidates:
            pols = infocap_policies(base, token, c["cpf"])
            for p in pols:
                insurer = str(p.get("seguradora") or p.get("insurer") or "").strip().lower()
                ramo = str(p.get("ramo") or p.get("produto") or p.get("line") or "").strip().lower()
                key = f"{insurer}|{ramo}"
                if insurer and ramo and key not in dataset:
                    dataset[key] = {
                        "seguradora": insurer, "ramo": ramo, "cpf": c["cpf"],
                        "nome": p.get("segurado") or p.get("nome") or "",
                        "placa": p.get("placa") or "", "cep": p.get("cep") or "",
                        "apolice": p.get("numero") or p.get("apolice") or "",
                        "vigencia_fim": p.get("vigencia_fim") or p.get("valid_to") or "",
                        "conta": name,
                    }
                    print(f"  [+] {insurer} × {ramo}: CPF {c['cpf'][:3]}***")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"dataset": list(dataset.values()),
                                          "candidates": candidates}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] {len(dataset)} combinações seguradora×ramo em {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
