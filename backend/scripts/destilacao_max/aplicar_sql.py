"""O que o subagente escreveu -> SQL idempotente, idêntico ao caminho de produção.

Este script não inventa regra nenhuma. Ele espelha `_store_card_sync` linha por
linha, de propósito:

  * `card_hash` = md5 do texto em minúsculas  → a mesma carta nunca duplica
  * tamanho pela régua de `curadoria_cartas`  → o mesmo corte (40–1800)
  * `status` por `curadoria_cartas.veredito_de_pii` — rejeita IDENTIFICADOR,
    mascara heurística; o que é gravado é sempre o texto mascarado
  * `insurer_key` em minúsculas, vazio vira NULL

Se alguma dessas regras mudar em produção, ela precisa mudar aqui no mesmo
commit. É o preço de escrever por fora — e é por isso que o script é curto e
declara isso em voz alta em vez de esconder.

A carta entra como `pending_review`, NÃO como `published`. Quem publica é o
publicador automático que já roda em `distill_once`: ele gera o embedding e
manda para o Qdrant com vetor denso e esparso. Não existe segundo publicador.

Uso
---
    python aplicar_sql.py destilado.jsonl > aplicar.sql

Entrada: uma linha JSON por sessão, no formato que o subagente produz:
    {"id": "...", "tipo": "...", "ramo": "auto", "servico": "sinistro",
     "seguradora": "hdi", "resumo_conduta": [...], "perguntas_na_ordem": [...],
     "fatos_reutilizaveis": [...], "score": 8, "flags": [...]}
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mascarar import _carregar_servico  # noqa: E402

_CURADORIA = _carregar_servico("curadoria_cartas")
assunto_da_carta = _CURADORIA.assunto_da_carta
seguradora_do_fato = _CURADORIA.seguradora_do_fato
# Régua de tamanho e veredito de PII: os MESMOS de `aplicar.py` e do destilador,
# importados de `curadoria_cartas` — ver o bloco de lá. Aqui havia `15`/`400`
# escritos à mão e um `templatize(t) == t`, que é o eixo errado (15/08/2026).
fora_do_tamanho = _CURADORIA.fora_do_tamanho
veredito_de_pii = _CURADORIA.veredito_de_pii

# O Windows redireciona `>` na codepage ANSI (cp1252), não em UTF-8. Sem esta
# linha, "apólice" e "ocorrência" saem corrompidos no arquivo .sql e entram
# corrompidos no banco — em silêncio, porque o SQL continua válido.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# A MARCA DA CAMPANHA VEM DO `aplicar.py`, e não de uma constante daqui.
#
# Esta linha era `MARCA = "destilacao_max_29_07_2026"`, igualzinha à do
# `aplicar.py` — e o mesmo defeito: 📊 as 1.941 cartas de 04/08/2026 saíram
# carimbadas com a data de 29/07. Duas cópias congeladas do mesmo valor errado
# não é um defeito com duas faces; é o defeito duas vezes. A resposta a "qual é
# a marca de hoje" passa a ter um dono só (CLAUDE.md §5).
from aplicar import marca_de_hoje  # noqa: E402

MARCA = marca_de_hoje()


def _citar(txt: str) -> str:
    """Texto -> literal SQL com aspas em dólar, sem chance de escapar errado.

    Carta de seguro tem apóstrofo ("apólice do cliente'"), acento e aspas. Um
    `replace("'", "''")` funciona até o dia em que não funciona, e o estrago é
    SQL executando o que não devia. O delimitador é escolhido para não existir
    dentro do texto.
    """
    tag = "c"
    while f"${tag}$" in txt:
        tag += "x"
    return f"${tag}${txt}${tag}$"


def main() -> int:
    global MARCA
    argumentos = sys.argv[1:]
    if "--marca" in argumentos:
        i = argumentos.index("--marca")
        if i + 1 >= len(argumentos) or not argumentos[i + 1].strip():
            print("--marca exige um valor", file=sys.stderr)
            return 2
        MARCA = argumentos[i + 1].strip()
        # A bandeira sai da lista para que o arquivo continue sendo "o que
        # sobrou", em qualquer ordem. `sys.argv[1]` fixo trataria
        # `--marca x lote.jsonl` como um arquivo chamado `--marca`.
        del argumentos[i:i + 2]
    if not argumentos:
        print("uso: aplicar_sql.py destilado.jsonl [--marca <marcador>]",
              file=sys.stderr)
        return 2
    entrada = argumentos[0]

    sessoes = cartas = puladas = descartadas = 0
    vistas: set = set()
    print("-- Gerado por scripts/destilacao_max/aplicar_sql.py")
    print(f"-- marca desta campanha: {MARCA}")
    print("BEGIN;")

    with open(entrada, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                d = json.loads(linha)
            except json.JSONDecodeError:
                puladas += 1
                continue
            sid = str(d.get("id") or "").strip()
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", sid):
                puladas += 1
                continue

            distilled = {
                "tipo": d.get("tipo"), "ramo": d.get("ramo"),
                "servico": d.get("servico"), "seguradora": d.get("seguradora"),
                "resumo_conduta": d.get("resumo_conduta") or [],
                "perguntas_na_ordem": d.get("perguntas_na_ordem") or [],
                "score": d.get("score"), "flags": d.get("flags") or [],
                "at": None, "por": MARCA,
            }
            j = _citar(json.dumps(distilled, ensure_ascii=False))
            # `||` preserva o `marker` e o `source` que já estavam no resumo, e
            # `summary->'distilled' is null` faz a linha ser inofensiva se rodar
            # duas vezes — nunca sobrescreve destilação existente.
            print(f"UPDATE attendance_sessions SET summary = coalesce(summary,'{{}}'::jsonb) "
                  f"|| jsonb_build_object('distilled', {j}::jsonb) "
                  f"WHERE id = '{sid}' AND summary->'distilled' IS NULL;")
            sessoes += 1

            ramo = str(d.get("ramo") or "outro")
            # A seguradora da SESSÃO é candidata, não veredito — quem decide é
            # `seguradora_do_fato`, pelo texto de cada fato, exatamente como no
            # destilador e no `aplicar.py`. Antes daqui saía a companhia da
            # conversa carimbada nos oito fatos.
            candidata = str(d.get("seguradora") or "")
            for fato in (d.get("fatos_reutilizaveis") or [])[:8]:
                bruto = " ".join(str(fato or "").split())
                # 🔴 O DESCARTE CONTA E DIZ O QUE PERDEU — 15/08/2026. Era um
                # `continue` mudo com `15`/`400` escritos à mão, e foi assim que
                # 📊 23 das 1.527 cartas da leva sumiram sem rastro nenhum.
                motivo = fora_do_tamanho(bruto)
                if motivo:
                    print(f"[aplicar_sql] DESCARTADO por tamanho — {motivo} "
                          f"sessao={sid[:8]} ramo={ramo}: {bruto[:90]}...",
                          file=sys.stderr)
                    descartadas += 1
                    continue
                # O que vai para a tabela é o MASCARADO, e a rejeição é por
                # identificador — não por "o mascarador encostaria". Ver
                # `curadoria_cartas.veredito_de_pii`.
                texto, achados = veredito_de_pii(bruto)
                h = hashlib.md5(texto.lower().encode("utf-8")).hexdigest()
                if h in vistas:
                    continue
                vistas.add(h)
                limpo = not achados
                status = "rejected_pii" if achados else "pending_review"
                seg, prestadora = seguradora_do_fato(texto, candidata)
                seg_sql = f"'{seg}'" if seg and re.fullmatch(r"[a-z0-9_-]{2,40}", seg) else "NULL"
                extra = (f", \"prestadora\": \"{prestadora}\""
                         if prestadora and re.fullmatch(r"[a-z0-9_-]{2,40}", prestadora) else "")
                if achados:
                    extra += ", \"pii_achada\": [%s]" % ", ".join(
                        f'"{a}"' for a in achados)
                if texto != bruto:
                    extra += ", \"mascarado\": true"
                print(f"INSERT INTO knowledge_cards "
                      f"(card_hash, card_text, category, ramo, insurer_key, status, pii_check) "
                      f"VALUES ('{h}', {_citar(texto)}, {_citar(assunto_da_carta(texto))}, "
                      f"{_citar(ramo)}, {seg_sql}, '{status}', "
                      f"'{{\"deterministic\": {str(limpo).lower()}, \"llm_instructed\": true, "
                      f"\"por\": \"{MARCA}\"{extra}}}'::jsonb) "
                      f"ON CONFLICT (card_hash) DO NOTHING;")
                cartas += 1

    print("COMMIT;")
    print(f"[aplicar_sql] {sessoes} sessões · {cartas} cartas · {puladas} linhas inválidas"
          f" · {descartadas} descartadas por tamanho",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
