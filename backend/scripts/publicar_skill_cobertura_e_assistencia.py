# -*- coding: utf-8 -*-
"""Registra a release `insurance.cobertura_e_assistencia` no Skill Registry.

SPEC-EXTRA-001.5 §6. Rodar de dentro de `backend/`:

    python scripts/publicar_skill_cobertura_e_assistencia.py            # só mostra
    python scripts/publicar_skill_cobertura_e_assistencia.py --aplicar  # grava

🔴 POR QUE ISTO NÃO É O CAMINHO DE EXECUÇÃO — E MESMO ASSIM EXISTE
===================================================================
📊 17/09/2026: 20 skills e 21 releases `published`, e o cutover
(`gateway_cutover.py:153`) lê `TOOL_GATEWAY_MODE`, que tem default `off` e
**não está no `.env`**. O chat resolve tools LangChain, não releases. Ou seja:
uma release registrada hoje **não é chamada por ninguém**.

A Skill roda como MÓDULO (`app/services/skills/cobertura_e_assistencia.py`),
pelo caminho vivo (`policy_answer_composer`). Esta release é o **registro** do
procedimento — o que o Control Plane lista, o que o Admin audita, e o que o
gateway vai resolver no dia em que ligar. Registrá-la agora custa uma linha e
evita que, naquele dia, alguém escreva uma SEGUNDA implementação por não achar
a primeira (CLAUDE.md §5).

⛔ Escrita pelo escritor que JÁ EXISTE (`SkillRegistry`/tabelas `skills`,
`skill_releases`). Nenhuma migration. Idempotente por `content_hash`: rodar
duas vezes não cria release nova.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(".env")

SKILL_KEY = "insurance.cobertura_e_assistencia"
VERSION = "1.0.0"

INSTRUCAO = """\
# Cobertura e assistência — o que o plano DELE cobre

Responda "tem carro reserva?", "cobre granizo?", "quantos km de guincho?" com
UM destes estados, e nunca com outra coisa:

| estado | quando |
|---|---|
| `coberto` | a linha publicada da condição geral diz `sim` |
| `nao_coberto` | a linha publicada diz `nao` |
| `condicionado` | diz `condicionado`, e a condição vai junto |
| `nao_contratado` | o plano dele não inclui, e um plano superior publicado inclui |
| `nao_sabemos_ainda` | não há linha publicada, OU o plano não foi identificado |

E um sexto, que NÃO é estado da base: `fonte_indisponivel` — a apólice não
carregou, a busca falhou. Isto é FALHA e tem texto próprio.

## As regras que não se negociam

1. **Toda frase que diz "não" carrega documento e página.** Um "não cobre" sem
   lastro custa ao segurado um acionamento a que ele tinha direito.
2. **"Não sabemos ainda" é acerto.** Nunca o transforme em "não cobre" nem em
   "sim" — diga que a condição geral dessa seguradora ainda não está na base e
   ofereça confirmar com a seguradora.
3. **O plano vem da apólice.** Plano não identificado é `nao_sabemos_ainda`,
   nunca "o plano padrão da seguradora".
4. **O gancho de plano superior não vende:** não diz preço, não promete que a
   seguradora aceita, e passa o caso para a atendente do card Equipe.
"""


def _manifesto() -> dict:
    """No molde do manifesto de `insurance.policy_lookup` (📊 lido em 17/09)."""
    from app.services.knowledge import assistance_plans_base as BASE

    vocab = BASE.vocabulario_de_servicos().get("servicos", {})
    gatilhos = sorted(
        str(item.get("pergunta_tipica")).strip()
        for item in vocab.values()
        if item.get("pergunta_tipica")
    )
    return {
        "slug": SKILL_KEY,
        "version": VERSION,
        "category": "insurance",
        # 🔴 os gatilhos são as `pergunta_tipica` do VOCABULÁRIO versionado —
        # não uma segunda lista escrita à mão, que divergiria dele na primeira
        # vez que alguém acrescentasse um serviço.
        "triggers": gatilhos,
        "verification": ["fonte_citada", "escopo_do_tenant_respeitado"],
        "capability_pack": "pack.insurance.policy_lookup",
    }


def _hash(manifesto: dict, instrucao: str) -> str:
    corpo = json.dumps(manifesto, ensure_ascii=False, sort_keys=True) + "\n" + instrucao
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    manifesto = _manifesto()
    content_hash = _hash(manifesto, INSTRUCAO)

    print("=" * 78)
    print(f"Skill: {SKILL_KEY} {VERSION}")
    print(f"content_hash: {content_hash}")
    print(f"triggers ({len(manifesto['triggers'])}): {manifesto['triggers'][:3]} ...")
    print(f"modo: {'APLICAR' if aplicar else 'só mostrar (passe --aplicar para gravar)'}")
    print("=" * 78)

    from app.core.database import get_supabase_client

    db = get_supabase_client().client

    ja = (db.table("skill_releases").select("id, version, status")
          .eq("content_hash", content_hash).limit(1).execute()).data or []
    if ja:
        print(f"\n✅ já existe (content_hash): release {ja[0]['id']} "
              f"{ja[0]['version']} status={ja[0]['status']} — nada a fazer")
        return 0
    if not aplicar:
        print("\n(nada gravado)")
        return 0

    skills = (db.table("skills").select("id").eq("skill_key", SKILL_KEY)
              .limit(1).execute()).data or []
    if skills:
        skill_id = skills[0]["id"]
        print(f"\nskill já existe: {skill_id}")
    else:
        skill_id = (db.table("skills").insert({
            "skill_key": SKILL_KEY,
            "name": "Cobertura e Assistencia",
            "description": ("Responde o que o plano de assistencia/cobertura da "
                            "apolice cobre, com documento e pagina, ou diz que "
                            "ainda nao sabe. Nunca diz 'nao' sem lastro."),
            "category": "insurance",
            "owner": "operational",
            "visibility": "internal",
            "business_domain": "insurance",
            "is_active": True,
        }).execute()).data[0]["id"]
        print(f"\nskill criada: {skill_id}")

    release = (db.table("skill_releases").insert({
        "skill_id": skill_id,
        "version": VERSION,
        "status": "draft",
        "manifest": manifesto,
        "instruction_markdown": INSTRUCAO,
        "content_hash": content_hash,
        "is_default": False,
    }).execute()).data[0]
    print(f"release criada: {release['id']}")

    from app.services.skills.registry import SkillRegistry

    ok = SkillRegistry(db).publicar(release["id"])
    print(f"publicar(): {ok}")

    # a tool de apólice que esta Skill exige — a que JÁ existe
    db.table("skill_tool_requirements").insert({
        "skill_release_id": release["id"],
        "tool_key": "insurance.policy_lookup",
        "requirement": "required",
        "max_calls": 5,
        "ordinal": 1,
    }).execute()
    print("tool_requirement: insurance.policy_lookup (required)")

    linhas = (db.table("skill_releases").select("version, status, is_default")
              .eq("id", release["id"]).execute()).data
    print(f"\nVERIFY: {SKILL_KEY} -> {linhas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
