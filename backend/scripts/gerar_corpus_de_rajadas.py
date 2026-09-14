# -*- coding: utf-8 -*-
"""Gera `backend/tests/corpus/rajadas_reais.jsonl` — TRAÇOS, nunca texto.

SPEC-EXTRA-001.2 §13.

🔴 **A tensão que este script resolve.** A janela precisa de CONTEÚDO para
classificar; o repositório não pode ter conteúdo de conversa de segurado. A
saída é separar a função que LÊ TEXTO da que DECIDE:

    tracos_da_mensagem(texto) ──► Tracos ──► janela_de_espera(Tracos) ──► segundos
          ↑ roda AQUI, sobre o acervo            ↑ roda no CI, sobre o corpus
          ↑ imprime só CONTAGENS                 ↑ o corpus guarda só os Tracos

⛔ **Nenhum campo de texto. Nenhum telefone. Nenhum hash. Nenhuma data
absoluta.** `company` vira `"A"`/`"B"`, nunca o UUID.

🔴 **O relógio.** Rajada se mede por `attendance_transcripts.wa_timestamp` —
NUNCA por `messages.created_at`, que é `DEFAULT now()`, o instante em que o
espelho gravou. 📊 Um HISTORY_SYNC grava meses de conversa em segundos e tudo
vira "rajada": +39,2% de falsos positivos (§0.3). Quando o banco está
disponível, a segunda LINHA DE CONTROLE roda a mesma consulta pelos dois
relógios e exige números DIFERENTES — iguais significam que o `wa_timestamp`
não foi usado.

Read-only: este script não escreve uma linha no banco.

Uso (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python scripts/gerar_corpus_de_rajadas.py \
        --de-arquivo <export.json> [--saida tests/corpus/rajadas_reais.jsonl]
    PYTHONIOENCODING=utf-8 python scripts/gerar_corpus_de_rajadas.py   # via banco
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

# 🔴 O MOTOR, e não uma cópia dele (CLAUDE.md §9.4). Se `tracos_da_mensagem`
# mudar, o corpus muda com ela — que é exatamente o que se quer.
from app.services.message_buffer_service import (  # noqa: E402
    TETO_DA_RAJADA_SEGUNDOS,
    janela_de_espera,
    tracos_da_mensagem,
)

SAIDA_PADRAO = os.path.join(RAIZ, "tests", "corpus", "rajadas_reais.jsonl")

#: Blocos de resposta: duas falas nossas separadas por MAIS que isto são dois
#: turnos. 📊 O produto manda balões da mesma resposta com 0,7 s entre eles
#: (`whatsapp_service._dormir(0.7)`), e a demora mediana entre a rajada e a
#: resposta é de 67 s — 15 s separa os dois mundos com folga dos dois lados.
SEGUNDOS_ENTRE_BLOCOS_DE_RESPOSTA = 15

#: Faixas de intervalo que o corpus tem de cobrir (§13).
FAIXAS = ((0, 3), (3, 8), (8, 18), (18, 25), (25, 10 ** 9))


def faixa_de(segundos: float) -> str:
    for ini, fim in FAIXAS:
        if ini <= segundos < fim:
            return ">25s" if ini == 25 else f"{ini}-{fim}s"
    return ">25s"


# =========================================================================== #
# LEITURA — arquivo de export (com texto) ou banco. Nenhum dos dois é gravado.
# =========================================================================== #
def rajadas_do_arquivo(caminho: str) -> list:
    """Lê o export real. ⛔ O arquivo vive FORA do repositório, e continua lá."""
    with io.open(caminho, encoding="utf-8") as fh:
        bruto = json.load(fh)
    return list(bruto or [])


def rajadas_do_banco(limite: int = 600) -> list:
    """`attendance_transcripts.wa_timestamp` — nunca `messages.created_at`."""
    url = os.getenv("SUPABASE_DB_URL") or ""
    if not url:
        raise SystemExit(
            "sem SUPABASE_DB_URL no ambiente — use --de-arquivo <export.json>")
    import psycopg  # import tardio: o caminho do arquivo não precisa dele

    consulta = """
        WITH t AS (
          SELECT company_id, conversation_id, direction, content, message_type,
                 wa_timestamp,
                 LAG(wa_timestamp) OVER (PARTITION BY company_id, conversation_id
                                         ORDER BY wa_timestamp) AS anterior
            FROM attendance_transcripts
           WHERE direction = 'in' AND wa_timestamp IS NOT NULL
        )
        SELECT company_id, conversation_id, content, message_type, wa_timestamp,
               EXTRACT(EPOCH FROM (wa_timestamp - anterior)) AS gap
          FROM t ORDER BY company_id, conversation_id, wa_timestamp
         LIMIT %s
    """
    with psycopg.connect(url) as conexao:
        with conexao.cursor() as cur:
            cur.execute(consulta, (limite * 8,))
            linhas = cur.fetchall()

    # Agrupa em rajadas: quebra quando o intervalo passa de 60 s.
    rajadas, atual, chave_atual = [], [], None
    for company, conversa, texto, tipo, _ts, gap in linhas:
        chave = (company, conversa)
        if chave != chave_atual or (gap is not None and float(gap) > 60):
            if len(atual) >= 2:
                rajadas.append({"company": chave_atual[0], "itens": atual,
                                "n": len(atual), "resposta": None})
            atual, chave_atual = [], chave
        atual.append({"t": str(tipo or "text"), "x": texto or "",
                      "gap": float(gap or 0)})
    if len(atual) >= 2 and chave_atual:
        rajadas.append({"company": chave_atual[0], "itens": atual,
                        "n": len(atual), "resposta": None})
    return rajadas


# =========================================================================== #
# CONVERSÃO — o texto entra aqui e NÃO sai
# =========================================================================== #
_TIPOS = {"text", "image", "audio", "document", "video", "sticker"}


def tracos_da_rajada(rajada: dict, apelido: str, ident: str) -> dict:
    itens = []
    for pos, item in enumerate(rajada.get("itens") or []):
        tipo = str(item.get("t") or "text").strip().lower()
        if tipo not in _TIPOS:
            tipo = "text"
        t = tracos_da_mensagem(item.get("x"), tipo=tipo)
        itens.append({
            "tipo": t.tipo,
            "n_chars": t.n_chars,
            "pont_final": t.termina_em_pontuacao_final,
            "conectivo": t.termina_em_conectivo,
            "dado_curto": t.dado_curto,
            # 🔴 O primeiro item não tem intervalo DENTRO da rajada: o `gap`
            # dele é a distância até a mensagem ANTERIOR, que é outra conversa.
            "intervalo_ms": 0 if pos == 0 else int(float(item.get("gap") or 0) * 1000),
        })
    return {
        "id": ident,
        "company": apelido,
        "itens": itens,
        "turnos_hoje": blocos_de_resposta(rajada.get("resposta")),
        "turnos_esperados": turnos_previstos(itens),
    }


def blocos_de_resposta(resposta) -> int:
    """Quantos TURNOS a rajada recebeu hoje. 2+ = fragmentou."""
    if not resposta:
        return 0
    blocos = 1
    for item in list(resposta)[1:]:
        if float(item.get("gap") or 0) > SEGUNDOS_ENTRE_BLOCOS_DE_RESPOSTA:
            blocos += 1
    return blocos


# =========================================================================== #
# ESCOLHA — 20 a 30 rajadas ESTRATIFICADAS (§13)
# =========================================================================== #
def turnos_previstos(itens: list) -> int:
    """Quantos turnos a janela desta SPEC faria com esta rajada.

    ⚠️ É a EXPECTATIVA que vai no corpus, derivada da regra declarada. Quem a
    prova é o guarda, rodando o MOTOR de verdade (`should_process` sobre um
    Redis dublê, com o relógio dublado) e exigindo este mesmo número. Se o
    motor divergir da regra, é o motor que está errado — e é isso que se quer
    descobrir.
    """
    if not itens:
        return 0
    turnos, desde_o_inicio = 1, 0.0
    for pos in range(len(itens) - 1):
        gap = itens[pos + 1]["intervalo_ms"] / 1000.0
        espera = janela_de_espera(_tracos_do_item(itens[pos]))
        # O teto conta desde a PRIMEIRA mensagem do turno; a janela, desde a
        # última. O que vier primeiro fecha.
        if gap >= min(espera, max(0.0, TETO_DA_RAJADA_SEGUNDOS - desde_o_inicio)):
            turnos += 1
            desde_o_inicio = 0.0
        else:
            desde_o_inicio += gap
    return turnos


def escolher(convertidas: list, teto: int = 30) -> list:
    """Cobre tamanhos 2/3/4/5+, as cinco faixas de intervalo, mídia, dado curto
    e as duas corretoras — e ⛔ não completa com rajada inventada se não houver.

    🔴 A régua da SPEC é `turnos_hoje` = 2+ e `turnos_esperados` = 1: a rajada
    que HOJE vira duas respostas e que a janela une numa só. Mas ⛔ nem toda
    rajada PODE virar um turno: um intervalo interno de 40 s estoura o teto de
    25 s **de propósito** (é a constante da Meta). Essas entram assim mesmo,
    com o `turnos_esperados` que a regra prevê — esconder o limite seria
    prometer o que a janela não faz.
    """
    faltando_faixa = {f"{a}-{b}s" if a != 25 else ">25s" for a, b in FAIXAS}
    faltando_tam = {"2", "3", "4", "5+"}
    faltando_com = {"A", "B"}
    midia = curtos = 0
    escolhidas, vistos = [], set()

    def marca(r):
        tam = str(len(r["itens"])) if len(r["itens"]) < 5 else "5+"
        faltando_tam.discard(tam)
        faltando_com.discard(r["company"])
        for item in r["itens"][1:]:
            faltando_faixa.discard(faixa_de(item["intervalo_ms"] / 1000.0))

    def considerar(r, obrigatorio=False):
        nonlocal midia, curtos
        if r["id"] in vistos or len(escolhidas) >= teto:
            return
        tem_midia = any(i["tipo"] != "text" for i in r["itens"])
        tem_curto = any(i["dado_curto"] for i in r["itens"])
        tam = str(len(r["itens"])) if len(r["itens"]) < 5 else "5+"
        faixas_novas = {faixa_de(i["intervalo_ms"] / 1000.0) for i in r["itens"][1:]}
        util = obrigatorio or (
            (faixas_novas & faltando_faixa) or (tam in faltando_tam)
            or (r["company"] in faltando_com) or (tem_midia and midia < 4)
            or (tem_curto and curtos < 4))
        if not util:
            return
        escolhidas.append(r)
        vistos.add(r["id"])
        midia += 1 if tem_midia else 0
        curtos += 1 if tem_curto else 0
        marca(r)

    # A que fragmentou HOJE vem primeiro; entre iguais, a mais longa.
    ordenadas = sorted(convertidas,
                       key=lambda r: (-r["turnos_hoje"], -len(r["itens"])))
    um_turno = [r for r in ordenadas if r["turnos_esperados"] == 1]
    # 🔴 Entre as que a janela NÃO une, primeiro as que têm um intervalo REAL
    # acima de 25 s: é a faixa que §13 exige no corpus, e é o caso em que o
    # teto está certo e a segunda resposta é a resposta honesta.
    varios = sorted(
        (r for r in ordenadas if r["turnos_esperados"] != 1),
        key=lambda r: (0 if any(i["intervalo_ms"] > 25_000 for i in r["itens"][1:])
                       else 1, -r["turnos_hoje"]))

    for r in um_turno:
        considerar(r)
    # 🔴 O teto de 25 s tem de aparecer no corpus: 3 rajadas que a janela NÃO
    # une, e que dizem por quê no próprio número.
    # As duas faixas longas SÓ existem em rajadas que a janela não une (um
    # intervalo de 20 s já fecha qualquer frase). Elas entram pela cobertura,
    # não pela sorte da ordenação.
    for faixa_alvo in (">25s", "18-25s"):
        for r in varios:
            if faixa_alvo not in faltando_faixa:
                break
            if any(faixa_de(i["intervalo_ms"] / 1000.0) == faixa_alvo
                   for i in r["itens"][1:]):
                considerar(r, obrigatorio=True)
    for r in varios[:2]:
        considerar(r, obrigatorio=True)
    for r in um_turno:
        if len(escolhidas) >= 20:
            break
        considerar(r, obrigatorio=True)
    return escolhidas


# =========================================================================== #
# CONTAGENS — o que o relatório cola. ⛔ Números, nunca frases.
# =========================================================================== #
def contar(convertidas: list, titulo: str) -> dict:
    itens = [i for r in convertidas for i in r["itens"]]
    texto = [i for i in itens if i["tipo"] == "text"]
    classes = Counter()
    por_classe_faixa = defaultdict(Counter)
    for r in convertidas:
        for pos, item in enumerate(r["itens"]):
            if pos + 1 >= len(r["itens"]):
                continue  # o último item não tem "intervalo seguinte"
            t = tracos_da_mensagem("", tipo=item["tipo"])
            classe = (
                "dado_curto" if item["dado_curto"]
                else "frase_completa" if (item["pont_final"] and not item["conectivo"])
                else "midia_sem_legenda" if (item["tipo"] != "text" and not item["n_chars"])
                else "frase_inacabada")
            classes[classe] += 1
            seguinte = r["itens"][pos + 1]["intervalo_ms"] / 1000.0
            por_classe_faixa[classe][faixa_de(seguinte)] += 1
            del t

    print(f"\n=== CONTAGENS · {titulo} ===")
    print(f"  rajadas: {len(convertidas)}   itens: {len(itens)}   "
          f"itens de texto: {len(texto)}")
    print(f"  tamanhos: {dict(sorted(Counter(len(r['itens']) for r in convertidas).items()))}")
    print(f"  corretoras: {dict(Counter(r['company'] for r in convertidas))}")
    print(f"  tipos: {dict(Counter(i['tipo'] for i in itens))}")
    print(f"  terminam em pontuação final: {sum(1 for i in texto if i['pont_final'])}"
          f" / {len(texto)}")
    print(f"  terminam em conectivo:       {sum(1 for i in texto if i['conectivo'])}"
          f" / {len(texto)}")
    print(f"  dado curto:                  {sum(1 for i in texto if i['dado_curto'])}"
          f" / {len(texto)}")
    print(f"  turnos esperados pela janela: "
          f"{dict(sorted(Counter(r['turnos_esperados'] for r in convertidas).items()))}")
    print(f"  hoje 2+ turnos E a janela une em 1: "
          f"{sum(1 for r in convertidas if r['turnos_hoje'] >= 2 and r['turnos_esperados'] == 1)}")
    print(f"  fragmentaram hoje (2+ turnos): "
          f"{sum(1 for r in convertidas if r['turnos_hoje'] >= 2)} / {len(convertidas)}")
    print("\n  📊 CLASSE DO ITEM × FAIXA DO INTERVALO SEGUINTE "
          "(é isto que calibra 3 · 8 · 18):")
    cabecalho = ["0-3s", "3-8s", "8-18s", "18-25s", ">25s"]
    print("    %-20s %s" % ("classe", "  ".join("%7s" % c for c in cabecalho)))
    for classe in ("dado_curto", "frase_completa", "frase_inacabada",
                   "midia_sem_legenda"):
        linha = por_classe_faixa.get(classe) or Counter()
        total = sum(linha.values()) or 1
        print("    %-20s %s   (n=%d)" % (
            classe,
            "  ".join("%6.1f%%" % (100.0 * linha.get(c, 0) / total) for c in cabecalho),
            sum(linha.values())))

    # =================================================================== #
    # AS DUAS LINHAS DE CONTROLE (CLAUDE.md §9.2)
    # =================================================================== #
    soma = sum(i["n_chars"] for i in itens)
    print("\n  [CONTROLE 1] Σ n_chars = %d — se fosse 0, a extração não rodou "
          "e todos os traços seriam falsos" % soma)
    if soma <= 0:
        raise SystemExit("CONTROLE 1 VERMELHO: nenhum caractere foi lido")

    # A janela do motor sobre o ÚLTIMO item de cada rajada — e o CONTROLE que
    # dá direito à conclusão: a janela fixa de 8 s tem de dar OUTRO número.
    def turnos_com(janela_fixa=None):
        fragmentadas = 0
        for r in convertidas:
            for pos, item in enumerate(r["itens"][:-1]):
                seguinte = r["itens"][pos + 1]["intervalo_ms"] / 1000.0
                if janela_fixa is not None:
                    espera = janela_fixa
                else:
                    t = _tracos_do_item(item)
                    espera = janela_de_espera(t)
                if seguinte >= min(espera, TETO_DA_RAJADA_SEGUNDOS):
                    fragmentadas += 1
                    break
        return fragmentadas

    adaptativa, fixa8 = turnos_com(), turnos_com(8)
    print("  [CONTROLE 2] rajadas que FRAGMENTARIAM: janela adaptativa %d · "
          "janela fixa de 8 s %d — os dois números precisam CONSEGUIR ser "
          "diferentes" % (adaptativa, fixa8))
    return {"rajadas": len(convertidas), "adaptativa": adaptativa, "fixa8": fixa8}


def _tracos_do_item(item: dict):
    """Os traços gravados no corpus, de volta ao tipo do motor."""
    from app.services.message_buffer_service import Tracos

    return Tracos(n_chars=item["n_chars"],
                  termina_em_pontuacao_final=item["pont_final"],
                  termina_em_conectivo=item["conectivo"],
                  dado_curto=item["dado_curto"], tipo=item["tipo"])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--de-arquivo", default="",
                   help="export JSON com texto (fora do repositório)")
    p.add_argument("--saida", default=SAIDA_PADRAO)
    p.add_argument("--teto", type=int, default=30)
    args = p.parse_args()

    brutas = (rajadas_do_arquivo(args.de_arquivo) if args.de_arquivo
              else rajadas_do_banco())
    print("rajadas lidas: %d" % len(brutas))

    # ⛔ O UUID da corretora NÃO entra no arquivo: vira "A"/"B" pela ORDEM de
    # aparição, que é estável dentro de uma geração e não identifica ninguém.
    apelidos, proximo = {}, iter("ABCDEFGH")
    convertidas = []
    for pos, r in enumerate(brutas):
        chave = str(r.get("company") or "")
        if chave not in apelidos:
            apelidos[chave] = next(proximo)
        convertidas.append(tracos_da_rajada(r, apelidos[chave], "r%03d" % (pos + 1)))

    contar(convertidas, "ACERVO INTEIRO (%d rajadas)" % len(convertidas))

    escolhidas = escolher(convertidas, teto=args.teto)
    for pos, r in enumerate(escolhidas):
        r["id"] = "r%02d" % (pos + 1)
    resumo = contar(escolhidas, "CORPUS VERSIONADO (%d rajadas)" % len(escolhidas))

    os.makedirs(os.path.dirname(args.saida), exist_ok=True)
    with io.open(args.saida, "w", encoding="utf-8", newline="\n") as fh:
        for r in escolhidas:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print("\ngravado: %s (%d rajadas)" % (args.saida, len(escolhidas)))

    if len(escolhidas) < 20:
        print("⚠️ MENOS de 20 rajadas: o acervo não tinha. ⛔ NÃO se completa "
              "com rajada inventada — o número real vai para o relatório.")
    return 0 if resumo["rajadas"] else 1


if __name__ == "__main__":
    sys.exit(main())
