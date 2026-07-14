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
        r = httpx.post(f"{base}/login", json={
            "email": login, "senha": password, "aplicacao": int(application or 0)}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("token") if isinstance(data, dict) else None
    except Exception as e:  # noqa: BLE001
        print(f"  [!] login InfoCap falhou ({login}): {type(e).__name__}")
        return None


def infocap_policies(base: str, token: str, cpf: str) -> list[dict]:
    """CorpAPI real: /cliente_cpf -> {cliente:[...]}; /cliente_ligacoes -> {documentos:{documentos:[...]}}."""
    import httpx
    from datetime import datetime

    headers = {"Authorization": token, "Content-Type": "application/json"}
    try:
        r = httpx.get(f"{base}/cliente_cpf", params={"cpf_cnpj": cpf, "codfil": 1}, headers=headers, timeout=30)
        if r.status_code >= 400:
            return []
        records = (r.json() or {}).get("cliente") or []
        if not records:
            return []
        codigo = records[0].get("codigo")
        nome = str(records[0].get("nome") or "")
        if not codigo:
            return []
        r2 = httpx.get(f"{base}/cliente_ligacoes", params={"codigo": codigo}, headers=headers, timeout=30)
        if r2.status_code >= 400:
            return []
        docs = (((r2.json() or {}).get("documentos") or {}).get("documentos")) or []
        out = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if str(doc.get("cancelado") or "F") == "T" or str(doc.get("tipdoc") or "A") != "A":
                continue
            fim = str(doc.get("fimvig") or "")
            try:
                if datetime.strptime(fim, "%d/%m/%Y") < datetime.now():
                    continue
            except Exception:
                pass
            doc["_nome_cliente"] = nome
            out.append(doc)
        return out
    except Exception:  # noqa: BLE001
        return []


SEG_MAP = {"ALLI": "allianz", "ZURI": "zurich", "PORT": "porto", "AZUL": "azul",
           "BRAD": "bradesco", "TOKI": "tokio", "TOKM": "tokio", "YELU": "yelum",
           "LIBE": "yelum", "MAPF": "mapfre", "HDI": "hdi", "HDIS": "hdi",
           "ALFA": "alfa", "SULA": "sulamerica", "SUHA": "suhai", "SOMP": "sompo",
           "ITAU": "itau", "MITS": "mitsui", "SURA": "sura", "UNIM": "unimed"}
RAMO_MAP = {"AUTO": "auto", "RESI": "residencial", "VIND": "vida", "VIDA": "vida",
            "EMPR": "empresarial", "COND": "condominio", "FROT": "frota",
            "SAUD": "saude", "RCIV": "rc", "VIAG": "viagem"}


def doc_detail(base: str, token: str, nosnum, codfil=1) -> dict:
    import httpx

    try:
        r = httpx.get(f"{base}/documento", params={"nosnum": nosnum, "codfil": codfil},
                      headers={"Authorization": token}, timeout=30)
        if r.status_code < 400:
            d = r.json()
            return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        pass
    return {}


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
        import re as _re
        import time as _time
        for idx, c in enumerate(candidates):
            if idx and idx % 20 == 0:
                print(f"  ... {idx}/{len(candidates)} CPFs; {len(dataset)} combos")
            pols = infocap_policies(base, token, c["cpf"])
            _time.sleep(0.2)
            for pdoc in pols:
                seg_raw = str(pdoc.get("seguradora") or "").strip().upper()
                ramo_raw = str(pdoc.get("ramo") or "").strip().upper()
                insurer = SEG_MAP.get(seg_raw, seg_raw.lower())
                ramo = RAMO_MAP.get(ramo_raw, ramo_raw.lower())
                key = f"{insurer}|{ramo}"
                if insurer and ramo and key not in dataset:
                    detail = doc_detail(base, token, pdoc.get("nosnum"), pdoc.get("codfil") or 1)
                    flat = json.dumps(detail, ensure_ascii=False).lower() if detail else ""
                    placa_m = _re.search('\"placa\"[ ]*:[ ]*\"([a-z0-9-]{6,8})\"', flat)
                    cep_m = _re.search('\"cep\"[ ]*:[ ]*\"?([0-9]{5}-?[0-9]{3})\"?', flat)
                    dataset[key] = {
                        "seguradora": insurer, "seguradora_codigo": seg_raw,
                        "ramo": ramo, "ramo_codigo": ramo_raw,
                        "cpf": c["cpf"], "nome": str(pdoc.get("cliente") or pdoc.get("_nome_cliente") or ""),
                        "placa": (placa_m.group(1).upper() if placa_m else ""),
                        "cep": (cep_m.group(1) if cep_m else ""),
                        "apolice": str(pdoc.get("numapo") or ""),
                        "vigencia_fim": str(pdoc.get("fimvig") or ""),
                        "conta": name,
                    }
                    print(f"  [+] {insurer} x {ramo} ({seg_raw}/{ramo_raw}): {c['cpf'][:3]}*** placa={dataset[key]['placa'] or '-'}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"dataset": list(dataset.values()),
                                          "candidates": candidates}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] {len(dataset)} combinações seguradora×ramo em {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
