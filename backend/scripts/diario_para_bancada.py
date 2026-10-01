"""SPEC-123 F4 — o "errado" do diário vira CASO PENDENTE da bancada do cérebro.

Lê em `diario_de_decisoes` as decisões que a corretora marcou como ERRADAS e que ainda
não viraram caso (`virou_caso_em is null`), monta cada uma no formato de
`tests/corpus/bancada/cerebro/casos.jsonl` e grava em
`tests/corpus/bancada/cerebro/pendentes.jsonl` — 🔴 NUNCA em `casos.jsonl`:
`bancada.carregar_casos` só lê `casos.jsonl`, e um caso só entra lá depois que uma
pessoa revisa o gabarito (o "o certo era…" é texto livre da corretora; ele vira
`oraculo.cerebro.aceitas` e precisa ser normalizado para a ação/opção da tela).
Depois carimba `virou_caso_em`/`caso_chave` na linha do diário.

    cd backend
    python scripts/diario_para_bancada.py --company-id <uuid>            # ensaio: só mostra
    python scripts/diario_para_bancada.py --company-id <uuid> --aplicar  # grava e carimba
    python scripts/diario_para_bancada.py --todas --aplicar              # o master: todas as corretoras

🔴 Sem dado de pessoa: tela, valor e "o certo era" passam de novo pelo mascarador do
produto (`acao_do_cerebro.higienizar_para_o_rastro`) e por uma última rede de números
longos. A varredura `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` lê
`pendentes.jsonl` (ela varre todo `*.jsonl` do corpus) e tem de continuar verde.
🔴 Nenhum nome de corretora: o caso leva o tenant FICTÍCIO "A" (CLAUDE.md §13.9).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

PENDENTES = Path(RAIZ) / "tests" / "corpus" / "bancada" / "cerebro" / "pendentes.jsonl"
TABELA = "diario_de_decisoes"
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
#: A última rede: qualquer sequência numérica longa (7+ caracteres, com ou sem ponto/traço/barra)
#: vira `{NUMERO}` — processo, sinistro, protocolo, documento que o mascarador não reconheceu.
#: Menu (1–2 dígitos), número da casa e minutos ficam.
_NUMERO_LONGO = re.compile(r"(?<![\w{])\d[\d.\-/]{5,}\d(?![\w}])")


def _limpo(texto: Any) -> str:
    from app.services.acao_do_cerebro import higienizar_para_o_rastro

    return _NUMERO_LONGO.sub("{NUMERO}", higienizar_para_o_rastro(str(texto or ""), None))


def chave_do_caso(linha: Dict[str, Any]) -> str:
    seg = re.sub(r"[^a-z0-9]", "", str(linha.get("seguradora") or "").lower())[:20] or "seguradora"
    return f"cer-D-{seg}-{str(linha['id'])[:8]}"


def montar_caso(linha: Dict[str, Any]) -> Dict[str, Any]:
    """Uma linha "errado" do diário → um caso no formato de `cerebro/casos.jsonl`."""
    o_certo = _limpo(" ".join(str(linha.get("o_certo_era") or "").split()))
    return {
        "chave": chave_do_caso(linha),
        "versao": 1,
        "papel": "cerebro",
        "nivel": "N1",
        # DEDUZIR e o NUNCA errados são os que custam caro: entram no subconjunto crítico.
        "critico": str(linha.get("classe") or "") in ("deduzir", "nunca_sozinho"),
        "tenant": "A",
        "entrada": {
            "tela": _limpo(linha.get("tela_mascarada")),
            "seguradora": str(linha.get("seguradora") or ""),
            "sessao": {"playbook_ref": str(linha.get("rota") or ""),
                       "subservice": str(linha.get("servico") or ""),
                       "slots": {}, "captured": {}, "transcript": []},
        },
        "ferramentas_disponiveis": [],
        "efeitos_permitidos": [],
        "efeitos_proibidos": [],
        "oraculo": {"cerebro": {
            "grupo": "DIARIO",
            # 🔴 o gabarito é o que a CORRETORA disse. Pendente de revisão: antes de ir para
            #    casos.jsonl, uma pessoa normaliza para a ação/opção da tela (RESPONDER + tecla…).
            "aceitas": [o_certo],
            "o_certo_era": o_certo,
            "o_agente_fez": {"classe": str(linha.get("classe") or ""),
                             "acao": str(linha.get("acao") or ""),
                             "valor": _limpo(linha.get("valor_mascarado")),
                             "nota": linha.get("nota")},
            "sugere_regra": bool(linha.get("sugere_regra")),
            "pendente_de_revisao": True,
        }},
        "falhas_injetadas": [],
        "orcamento_turnos": None,
        "origem": f"diario {linha['id']}",
    }


def _chaves_ja_gravadas(destino: Path) -> set:
    if not destino.exists():
        return set()
    chaves = set()
    for l in destino.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                chaves.add(json.loads(l).get("chave"))
            except ValueError:
                continue
    return chaves


def exportar(db: Any, *, company_id: Optional[str] = None, todas: bool = False,
             aplicar: bool = False, destino: Path = PENDENTES) -> Dict[str, Any]:
    """Lê os errados sem caso, grava os casos pendentes e carimba o diário. Devolve o placar."""
    if destino.name == "casos.jsonl":
        raise ValueError("o diário NUNCA escreve em casos.jsonl — só em pendentes.jsonl")
    if not todas and not (company_id and _UUID.match(str(company_id))):
        raise ValueError("diga de qual corretora (--company-id) ou use --todas (master)")
    q = (db.client.table(TABELA)
         .select("id, company_id, seguradora, ramo, rota, servico, classe, acao, nota, "
                 "tela_mascarada, valor_mascarado, o_certo_era, sugere_regra, veredito, virou_caso_em")
         .eq("veredito", "errado")
         .is_("virou_caso_em", "null"))
    if not todas:
        q = q.eq("company_id", str(company_id))      # 🔴 filtro no código (CLAUDE.md §7)
    linhas: List[Dict[str, Any]] = q.order("created_at", desc=False).limit(500).execute().data or []

    ja = _chaves_ja_gravadas(destino)
    novos = [c for c in (montar_caso(l) for l in linhas) if c["chave"] not in ja]
    placar = {"errados_sem_caso": len(linhas), "casos_novos": len(novos),
              "ja_no_arquivo": len(linhas) - len(novos), "aplicado": aplicar, "destino": str(destino)}
    if not aplicar:
        return placar

    if novos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("a", encoding="utf-8", newline="\n") as f:
            for c in novos:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    agora = datetime.now(timezone.utc).isoformat()
    carimbadas = 0
    for l in linhas:
        r = (db.client.table(TABELA)
             .update({"virou_caso_em": agora, "caso_chave": chave_do_caso(l)})
             .eq("id", str(l["id"]))
             .eq("company_id", str(l["company_id"]))
             .is_("virou_caso_em", "null").execute())
        carimbadas += len(r.data or [])
    placar["carimbadas"] = carimbadas
    return placar


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alvo = ap.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--company-id", help="a corretora (uuid)")
    alvo.add_argument("--todas", action="store_true", help="todas as corretoras (master)")
    ap.add_argument("--aplicar", action="store_true", help="grava pendentes.jsonl e carimba o diário")
    a = ap.parse_args(argv)

    from app.core.database import get_supabase_client

    placar = exportar(get_supabase_client(), company_id=a.company_id, todas=a.todas, aplicar=a.aplicar)
    print(json.dumps(placar, ensure_ascii=False, indent=2))
    if not a.aplicar:
        print("ENSAIO — nada foi gravado. Rode de novo com --aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
