# -*- coding: utf-8 -*-
"""A tela que o corredor não conhece vira FILA — SPEC-087, BLOCO A.

## 📊 A razão, medida em 26/08/2026

Rodando `match_ura_step` sobre o corpus versionado de telas reais, com o
casamento **mais generoso possível** (14 playbooks × 76 subserviços) — então o
número é **piso, não teto**:

```
1.696 telas distintas em 10 seguradoras
  378 CEGAS ................ 22,3%
   27 delas são MENU (≥2 opções numeradas) — a URA pergunta e ninguém sabe

zurich  auto        135/207  65,2%   🔴 a pior medida
yelum   auto         55/195  28,2%
allianz residencial  45/195  23,1%
```

> **Uma em cada quatro telas que a seguradora manda, o corredor não conhece.
> Hoje o segurado espera e ninguém fica sabendo.**

## 🔴 Não é tabela de log — é fila de trabalho

Cada linha é uma tela que alguém vai transformar em passo. E **a dedupe é o que
a torna útil**: a mesma tela chega dezenas de vezes, e sem ela a fila vira ruído
em um dia. 📊 É o contador que ordena: a tela vista 40 vezes vale mais que a
vista uma.

## ⛔ O texto vem MASCARADO da origem

Ver o BLOCO C. Escrever cru e mascarar depois é criar o vazamento e tapá-lo —
e o backfill de máscara é sempre pior que a máscara na origem.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: ≥ 2 opções numeradas distintas. 🔴 São os que mais doem: a URA **pergunta**,
#: o corredor não sabe responder, e o acionamento para ali.
#:
#: ⚠️ `set()` nos números: uma tela que repete "1 -" duas vezes por quebra de
#: linha não é menu de dois itens.
_OPCAO_NUMERADA = re.compile(r"(?m)^\s*\*?\s*(\d{1,2})\s*\*?\s*[-–.)•]")

#: O teto do que se guarda. ⚠️ Não é performance: é que uma tela de 4 KB na fila
#: é ilegível para quem vai transformá-la em passo.
_TETO_DO_TEXTO = 1200


def e_menu(texto: str) -> bool:
    """PURO. A tela oferece escolha numerada?"""
    return len(set(_OPCAO_NUMERADA.findall(str(texto or "")))) >= 2


def hash_da_tela(texto: str) -> str:
    """PURO. A chave da dedupe — md5 do texto **normalizado**.

    🔴 NORMALIZADO, e não cru. O mesmo menu com um espaço a mais, ou com o nome
    do segurado trocado, é a MESMA tela — e uma chave sobre o texto cru faria a
    fila crescer para sempre sem nunca deduplicar nada.

    ⚠️ Usa o `_norm` do próprio casador (`corridor_playbooks`), e não uma
    normalização paralela: se as duas divergirem, a dedupe passa a agrupar
    telas que o casador considera diferentes — e a fila mente.
    """
    try:
        from app.services.corridor_playbooks import _norm

        base = _norm(str(texto or ""))
    except Exception:  # noqa: BLE001
        # ⚠️ Degradação honesta: sem o casador, normaliza o mínimo. A dedupe
        # fica pior, nunca ausente.
        base = str(texto or "").lower()

    # 🔴 E O ESPAÇO EM BRANCO COLAPSA — uma divergência DELIBERADA do casador.
    #
    # 📊 Medido: `_norm` tira acento, negrito e caixa, mas **não** colapsa
    # espaço. Para o CASADOR isso está certo — a âncora é regex, e ali o espaço
    # a mais importa.
    #
    # ⚠️ Para a FILA, não. Quem lê esta fila é uma pessoa que vai transformar a
    # tela em passo, e o mesmo menu com uma quebra de linha diferente é **o
    # mesmo trabalho**. Sem colapsar, a fila fragmenta e o contador — que é o
    # que ordena a prioridade — passa a subestimar a dor.
    #
    # 🔴 A divergência é registrada aqui de propósito: se algum dia a fila
    # precisar casar 1-para-1 com o casador, é esta linha que muda.
    base = " ".join(base.split())
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def linha_da_fila(*, company_id: str, insurer_key: str, ramo: str,
                  playbook_ref: Optional[str], texto: str) -> Dict[str, Any]:
    """PURO. A linha que vai para a fila — já mascarada.

    Separada do IO de propósito: dá para percorrer as famílias de tela sem
    banco, sem Redis e sem rede.
    """
    from app.services.intelligence.redaction_service import redigir

    return {
        "company_id": str(company_id),
        "insurer_key": str(insurer_key or "").lower().strip(),
        "ramo": str(ramo or "todos").lower().strip() or "todos",
        "playbook_ref": str(playbook_ref or "") or None,
        # ⛔ MASCARADO NA ORIGEM — BLOCO C.
        "texto_mascarado": redigir(str(texto or ""))[:_TETO_DO_TEXTO],
        "hash_normalizado": hash_da_tela(texto),
        "e_menu": e_menu(texto),
    }


async def registrar_tela_cega(*, company_id: str, insurer_key: str,
                              ramo: str = "todos",
                              playbook_ref: Optional[str] = None,
                              texto: str) -> bool:
    """A tela que nenhum passo casou entra na fila. `False` = não entrou.

    ## ⚠️ Best-effort, e a direção do erro importa

    🔴 Falhar aqui **nunca** pode derrubar o acionamento: o segurado está do
    outro lado esperando, e um registro a menos é um problema; um acionamento
    morto por causa de um `INSERT` é um problema maior.

    ⛔ Mas sai no log, porque uma fila que não recebe é a mesma coisa que não
    existir — e o piloto começa em dias.

    ## 🔴 A dedupe

    Segunda vez que a mesma tela chega → **incrementa o contador**, não cria
    linha. A chave é `(company_id, insurer_key, ramo, hash)`, e o UNIQUE do
    banco é o guarda de verdade: o `select` antes é o caminho rápido, e duas
    réplicas do webhook rodando juntas passam pelas duas.
    """
    if not company_id or not str(texto or "").strip():
        return False

    linha = linha_da_fila(company_id=company_id, insurer_key=insurer_key,
                          ramo=ramo, playbook_ref=playbook_ref, texto=texto)
    try:
        from app.core.database import create_async_supabase_client

        db = await create_async_supabase_client()
        if db is None:
            return False

        # ⚠️ O FILTRO POR CORRETORA EM TODA LEITURA (`CLAUDE.md` §7). O backend
        # usa service role: a RLS não protege contra um filtro esquecido aqui.
        existe = await (db.client.table("tela_cega").select("id, visto_quantas_vezes")
                        .eq("company_id", linha["company_id"])
                        .eq("insurer_key", linha["insurer_key"])
                        .eq("ramo", linha["ramo"])
                        .eq("hash_normalizado", linha["hash_normalizado"])
                        .limit(1).execute())
        achadas = getattr(existe, "data", None) or []
        if achadas:
            from datetime import datetime, timezone

            await (db.client.table("tela_cega")
                   .update({"visto_quantas_vezes":
                            int(achadas[0].get("visto_quantas_vezes") or 1) + 1,
                            "visto_em": datetime.now(timezone.utc).isoformat()})
                   .eq("id", achadas[0]["id"])
                   .eq("company_id", linha["company_id"]).execute())
            return True

        try:
            await db.client.table("tela_cega").insert(linha).execute()
        except Exception as e:  # noqa: BLE001
            texto_do_erro = str(e).lower()
            if ("duplicate" in texto_do_erro or "23505" in texto_do_erro
                    or "unique" in texto_do_erro):
                # 🔴 A CORRIDA. Duas réplicas viram a mesma tela ao mesmo tempo e
                # as duas acharam a fila vazia. O UNIQUE decidiu; quem perdeu
                # incrementa.
                return await _incrementar(db, linha)
            raise
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("[TELA CEGA] a tela de %s/%s NÃO entrou na fila (%s) — "
                     "ninguém vai saber que o corredor não a conhece",
                     linha["insurer_key"], linha["ramo"], type(e).__name__)
        return False


async def _incrementar(db, linha: Dict[str, Any]) -> bool:
    """Relê e soma — o desfecho certo de uma corrida perdida."""
    try:
        r = await (db.client.table("tela_cega").select("id, visto_quantas_vezes")
                   .eq("company_id", linha["company_id"])
                   .eq("insurer_key", linha["insurer_key"])
                   .eq("ramo", linha["ramo"])
                   .eq("hash_normalizado", linha["hash_normalizado"])
                   .limit(1).execute())
        achadas = getattr(r, "data", None) or []
        if not achadas:
            return False
        await (db.client.table("tela_cega")
               .update({"visto_quantas_vezes":
                        int(achadas[0].get("visto_quantas_vezes") or 1) + 1})
               .eq("id", achadas[0]["id"])
               .eq("company_id", linha["company_id"]).execute())
        return True
    except Exception:  # noqa: BLE001
        return False
