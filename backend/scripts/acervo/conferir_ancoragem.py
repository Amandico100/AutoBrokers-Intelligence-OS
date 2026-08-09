#!/usr/bin/env python3
"""A carta aponta para o trecho que a sustenta? — conferência obrigatória do §7.

POR QUE ISTO EXISTE
===================
Toda carta destilada guarda um `unit_id_origem`: o endereço exato do trecho do
contrato de onde ela saiu. É por ele que o agente volta ao documento para
provar a afirmação — e é o que separa *"acho que a Porto não cobre"* de *"a
cláusula 4.4.2.d das Condições Gerais vigentes desde 01/07/2026 diz que não"*.

Um endereço errado é pior que endereço nenhum. A carta continua parecendo certa,
o agente cita com confiança, e quem for conferir não acha nada no lugar
indicado.

📊 O DEFEITO É REAL E FOI MEDIDO — 08/08/2026, LOTE 1
====================================================
O destilador do ramo condomínio rodou por conta própria uma auditoria de
sobreposição e achou **20 das suas 203 cartas** (9,9%) citando o pedaço VIZINHO
ao que continha a afirmação. Corrigiu antes de entregar.

A causa é o corte: o título do serviço fica num pedaço e o limite dele no
seguinte; a cobertura num, a exclusão no outro. Quem lê o pedaço inteiro vê a
regra completa e cita o começo — que é o pedaço errado.

**E o alerta no prompt não bastou.** Os seis destiladores receberam o aviso;
📊 mesmo assim a medição sinalizou 57 cartas de 1.121 em todos os ramos. O que
achou o defeito foi medir, não avisar (CLAUDE.md §9.2: medir vence deduzir).

O QUE ESTE SCRIPT FAZ — E O QUE ELE **NÃO** DECIDE
==================================================
Ele calcula, para cada carta, quanto do vocabulário dela aparece no corpo do
pedaço citado, e compara com os quatro pedaços vizinhos.

**Baixa sobreposição NÃO é prova de erro.** Uma carta boa é o contrato
reescrito em português de WhatsApp — a sobreposição cai justamente porque o
destilador fez o trabalho direito. Por isso a saída é uma LISTA PARA LEITURA
HUMANA (ou de subagente auditor), nunca uma reprovação automática.

O sinal forte é outro: **um vizinho ancorar melhor que o pedaço citado.** Aí a
hipótese "citou o vizinho" tem evidência, e o caso vai para julgamento.

⚠️ CAMINHO DENTRO DO CONTÊINER
==============================
Este script roda FORA do contêiner, na máquina que destilou — é lá que estão os
pacotes. Não toca em banco, índice nem rede.

USO
===
    python backend/scripts/acervo/conferir_ancoragem.py --pasta <dir>
    python backend/scripts/acervo/conferir_ancoragem.py --pasta <dir> --auditoria
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import difflib
import re
import sys
import unicodedata
from typing import Any, Dict, List, Optional, Set

# 🔴 O SINAL É DIFERENCIAL, NÃO ABSOLUTO — e isto foi MEDIDO, não escolhido.
#
# A primeira versão sinalizava por sobreposição baixa (< 30% do vocabulário da
# carta presente no pedaço citado). O auditor do lote 2 sugeriu trocar pelo
# diferencial — "sinalize quando um vizinho ancorar melhor que o citado" — e
# marcou a própria sugestão como 💭 inferência, pedindo que fosse medida antes
# de adotar. Foi.
#
# 📊 08/08/2026, contra os 10 erros que dois auditores confirmaram no LOTE 1:
#
#     critério                       acusou   pegou   falso alarme
#     limiar absoluto < 30%              34    6/10             28
#     diferencial + limiar absoluto      10    6/10              4
#     DIFERENCIAL PURO                   20   10/10             10
#
# ⚠️ **A comparação acima rodou sobre as 57 cartas que a primeira versão já
# tinha sinalizado, não sobre as 1.121.** Ela mede bem o poder de separação
# entre os três critérios, e NÃO mede quantas cartas cada um acusaria no acervo
# inteiro — o denominador é outro. Aplicado às 1.121, o diferencial puro aponta
# 36 (3,2%). Registro o viés porque um número medido sobre o subconjunto errado
# vira "achado do produto" se ninguém escrever de onde ele veio (CLAUDE.md
# §12.1).
#
# **O limiar absoluto perdia 4 dos 10.** Ele filtrava antes as cartas que têm
# boa sobreposição com o citado E um vizinho ainda melhor — que é justamente a
# lista alfabética partida, o defeito mais comum do lote.
#
# E os dois tipos de falha custam coisas MUITO diferentes: um falso alarme
# custa um auditor ler uma carta boa; um erro que passa vai para produção e
# manda o corretor abrir o contrato no lugar errado. Com 36 acusações em 1.121
# cartas, pagar leituras a mais para não perder 4 erros é barato.
MARGEM_DO_VIZINHO = 0.05
# 🔴 CÓPIA SE MEDE EM CARACTERES, NÃO EM PORCENTAGEM — e isto custou uma rodada.
#
# A primeira versão acusava por fração: bloco literal > 50% da carta. 📊 Ela
# marcou 6 cartas já publicadas, e as 6 eram legítimas — todas CURTAS:
#
#     108 chars  "O Porto Seguro Empresa se aplica somente a danos ocorridos
#                 e reclamados no Território Nacional."
#     100 chars  "No Allianz Vida em Grupo, não será distribuído Excedente
#                 Técnico em caso de cancelamento da apólice."
#
# **Quando a regra do contrato já é curta e direta, não existe como reescrever
# sem repetir as mesmas palavras.** A fração pune exatamente a carta que fez o
# trabalho certo — dizer a regra em uma linha.
#
# O sinal de cópia de verdade é o bloco literal LONGO em termos absolutos: um
# parágrafo inteiro do contrato transplantado. 📊 As 25 cartas mais longas da
# Allianz (até 1.630 caracteres, listas taxativas) têm no máximo **105** — bem
# abaixo do corte. Exigir as duas condições mantém o guarda e solta a carta
# curta.
# 📊 Recalibrado em 09/08/2026, no PME da Allianz. Com 0,50 o guarda acusou uma
# carta que CITA 252 caracteres de uma regra taxativa — "limitada a R$ 500,00
# por caixa registradora, guichê, caixa, atendente ou vendedor" — e acrescenta a
# leitura: "não adianta contratar um limite alto se o dinheiro fica na gaveta".
#
# **Parafrasear aquela enumeração mudaria o escopo.** Citar é o certo ali, e a
# carta ainda entrega 45% de trabalho próprio. O que separa citação de cópia não
# é o bloco existir — é ele ser QUASE TUDO. 📊 A cópia literal montada na prova
# de mutação mede 100%; esta mede 55%.
LIMIAR_DE_COPIA = 0.70
BLOCO_LITERAL_DE_COPIA = 250
VIZINHOS = (-2, -1, 1, 2)
# Guardado só para informar a leitura — não filtra mais nada.
LIMIAR_FRACO = 0.30


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto or "")).encode(
        "ascii", "ignore").decode().lower()


def _vocabulario(texto: str) -> Set[str]:
    """Palavras de 5+ letras, sem acento e em minúscula.

    Palavra curta (`de`, `que`, `não`) aparece em tudo e só faria o número
    subir sem dizer nada. O acento cai porque o PDF e a carta discordam sobre
    ele com frequência — `apólice` no contrato, `apolice` na carta.
    """
    return set(re.findall(r"[a-z]{5,}", _sem_acento(texto)))


def _carregar_pedacos(pasta: str) -> Dict[str, Dict[str, Any]]:
    pedacos: Dict[str, Dict[str, Any]] = {}
    for caminho in sorted(glob.glob(os.path.join(pasta, "*_pacote_*.jsonl"))):
        with open(caminho, encoding="utf-8") as arquivo:
            for linha in arquivo:
                if not linha.strip():
                    continue
                d = json.loads(linha)
                if d.get("unit_id"):
                    pedacos[d["unit_id"]] = d
    return pedacos


def _vizinho(pedacos: Dict[str, Dict[str, Any]], unit_id: str,
             passo: int) -> Optional[Dict[str, Any]]:
    if "#" not in unit_id:
        return None
    doc, indice = unit_id.rsplit("#", 1)
    try:
        return pedacos.get(f"{doc}#{int(indice) + passo:04d}")
    except ValueError:
        return None


def _ancora(pedaco: Dict[str, Any]) -> str:
    """O texto contra o qual a carta é medida: `caminho` + `corpo`.

    🔴 MEDIR SÓ O `corpo` ERA MEDIR A COISA ERRADA — achado em 08/08/2026 pelo
    auditor do lote 1, contra a minha própria medição.

    📊 24 dos 28 casos que eu sinalizei eram falso positivo (86%), e a maioria
    pelo mesmo motivo: **nas unidades de tabela o `corpo` é a célula de valor**
    (`"R$ 200,00"`) e o nome do serviço mora no `caminho` (`ELETRICISTA`,
    `PORTEIRO SUBSTITUTO`, `BOMBA DE ÁGUA`). A carta dizia serviço e valor, os
    dois certos, e a conta dava 0% de sobreposição.

    O mesmo vale para a frase partida entre título e corpo: `caminho` traz
    "3.3.3. A transferência… extingue o bônus. O bônus - por ser direito do
    segurado" e `corpo` traz "- não poderá ser transferido…". Lendo só a
    segunda metade, uma carta 100% ancorada media 15%.

    **Não** uso o campo `texto` do pedaço, que existe e junta os dois: ele traz
    também o cabeçalho injetado (seguradora, ramo, título, vigência), e toda
    carta nomeia a seguradora por obrigação da §10 — a palavra "Porto" casaria
    sempre e inflaria a conta de graça.
    """
    return f"{pedaco.get('caminho', '')} {pedaco.get('corpo', '')}"


def _cobertura(vocab_carta: Set[str], pedaco: Dict[str, Any]) -> float:
    if not vocab_carta:
        return 1.0
    return len(vocab_carta & _vocabulario(_ancora(pedaco))) / len(vocab_carta)


def _fracao_copiada(texto: str, pedaco: Dict[str, Any]) -> tuple:
    """Quanto da carta é um bloco LITERAL do pedaço.

    🔴 A carta é o contrato REESCRITO. Se ela for o contrato COPIADO, o
    namespace `cards` vira uma segunda cópia do `normative` — duas entradas
    disputando as mesmas vagas na busca, dizendo a mesma coisa com as mesmas
    palavras. A carta perde a razão de existir.

    Isto substitui o teto de tamanho que havia em `publicar_cartas.py`. 📊 Em
    09/08/2026 aquele teto reprovou 25 cartas da Allianz por terem mais de 900
    caracteres — e a medição mostrou que **nenhuma era cópia**: o maior bloco
    literal em comum foi de 105 caracteres (11%). Eram listas taxativas, longas
    porque a lista do contrato é longa, e cortá-las faria a carta mentir por
    omissão.

    **Tamanho não separa carta de cópia. Bloco literal separa.** E esta
    conferência só pode morar aqui: o publicador roda no servidor e não tem os
    pedaços; este script roda na máquina que destilou e tem.
    """
    a = " ".join(_sem_acento(texto).split())
    b = " ".join(_sem_acento(_ancora(pedaco)).split())
    if not a:
        return 0.0, 0
    m = difflib.SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    # Devolve (fração, tamanho em caracteres). As duas condições precisam bater
    # para acusar cópia — ver o comentário de `BLOCO_LITERAL_DE_COPIA`.
    return m.size / len(a), m.size


def main() -> int:
    ap = argparse.ArgumentParser(description="Confere a ancoragem das cartas destiladas")
    ap.add_argument("--pasta", required=True,
                    help="diretório com os *_pacote_*.jsonl e os *_CARTAS.jsonl")
    ap.add_argument("--auditoria", action="store_true",
                    help="grava AUDITORIA.json com os casos para um auditor ler")
    args = ap.parse_args()

    pedacos = _carregar_pedacos(args.pasta)
    if not pedacos:
        print(f"  X   nenhum *_pacote_*.jsonl em {args.pasta}")
        return 1
    print(f"  pedaços indexados: {len(pedacos)}")

    arquivos = sorted(glob.glob(os.path.join(args.pasta, "*_CARTAS.jsonl")))
    if not arquivos:
        print(f"  X   nenhum *_CARTAS.jsonl em {args.pasta}")
        return 1

    print()
    print(f"  {'ramo':<14} {'cartas':>7} {'órfãs':>7} {'sobrep.baixa':>13} {'SUSPEITAS':>10}")
    casos: List[Dict[str, Any]] = []
    orfas_total = 0
    copias_total = 0

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        ramo = nome.split("_")[0]
        total = orfas = fracas = suspeitas = copias = 0

        with open(caminho, encoding="utf-8") as arquivo:
            for numero, linha in enumerate(arquivo, 1):
                if not linha.strip():
                    continue
                total += 1
                carta = json.loads(linha)
                unit_id = carta.get("unit_id_origem")

                # 🔴 ÓRFÃ É O CASO GRAVE, e é diferente de ancoragem fraca: o
                # endereço não existe. Ou o destilador inventou, ou o documento
                # foi recortado depois. A carta não tem como ser conferida por
                # ninguém, nunca.
                if unit_id not in pedacos:
                    orfas += 1
                    print(f"    X  ÓRFÃ {nome}:{numero} → {unit_id!r}")
                    continue

                # 🔴 CÓPIA é defeito, não sinal — e sai com a órfã.
                copiado, bloco = _fracao_copiada(carta.get("texto", ""), pedacos[unit_id])
                if copiado > LIMIAR_DE_COPIA and bloco >= BLOCO_LITERAL_DE_COPIA:
                    copias += 1
                    print(f"    X  CÓPIA {nome}:{numero} — {copiado:.0%} da carta "
                          f"é um bloco literal de {bloco} caracteres")

                vocab = _vocabulario(carta.get("texto", ""))
                citado = _cobertura(vocab, pedacos[unit_id])
                if citado < LIMIAR_FRACO:
                    fracas += 1

                # 🔴 O TESTE É ESTE, e ele roda para TODA carta — inclusive as
                # que ancoram bem no citado. Filtrar por sobreposição baixa
                # antes perdia 4 dos 10 erros do LOTE 1: a lista alfabética
                # partida deixa muito vocabulário em comum com o cabeçalho, e
                # a carta passava direto pelo filtro com o endereço errado.
                melhor = None
                for passo in VIZINHOS:
                    v = _vizinho(pedacos, unit_id, passo)
                    if not v:
                        continue
                    cob = _cobertura(vocab, v)
                    if cob > citado + MARGEM_DO_VIZINHO and (
                            melhor is None or cob > melhor[1]):
                        melhor = (passo, cob, v)
                if not melhor:
                    continue
                suspeitas += 1

                casos.append({
                    "ramo": ramo, "arquivo": nome, "linha": numero,
                    "carta": carta.get("texto"), "faceta": carta.get("faceta"),
                    "unit_id_citado": unit_id, "cobertura_citado": round(citado, 2),
                    "vizinho_ancora_melhor": bool(melhor),
                    "caminho_citado": pedacos[unit_id].get("caminho", ""),
                    "corpo_citado": pedacos[unit_id].get("corpo", ""),
                    "vizinhos": {
                        f"{p:+d}": {"unit_id": v["unit_id"], "caminho": v.get("caminho", ""),
                         "corpo": v.get("corpo", "")}
                        for p in VIZINHOS
                        if (v := _vizinho(pedacos, unit_id, p)) is not None},
                })

        orfas_total += orfas
        copias_total += copias
        print(f"  {ramo:<14} {total:>7} {orfas:>7} {fracas:>13} {suspeitas:>10}")

    suspeitas_total = sum(1 for c in casos if c["vizinho_ancora_melhor"])
    print()
    print(f"  SUSPEITAS (um vizinho ancora melhor): {len(casos)}"
          f"   ← estas vão para o auditor")
    print(f"  ÓRFÃS                   : {orfas_total}   ← defeito: endereço não existe")
    print(f"  CÓPIAS                  : {copias_total}   ← defeito: a carta não reescreveu")

    if args.auditoria and casos:
        casos.sort(key=lambda c: (not c["vizinho_ancora_melhor"], c["cobertura_citado"]))
        destino = os.path.join(args.pasta, "AUDITORIA.json")
        with open(destino, "w", encoding="utf-8") as arquivo:
            json.dump(casos, arquivo, ensure_ascii=False, indent=1)
        print(f"\n  gravado: {destino}")
        print("  Mande um auditor Opus 5 julgar cada caso em `ok` / `mover` /")
        print("  `sem_lastro` — a decisão é de leitura, não deste script.")

    # 🔴 A saída só é 1 por ÓRFÃ. Ancoragem fraca não reprova nada: reprovar
    # por ela transformaria "escreveu em português simples" em defeito, que é
    # o oposto do que a SPEC-070 §10 pede.
    return 1 if (orfas_total or copias_total) else 0


if __name__ == "__main__":
    sys.exit(main())
