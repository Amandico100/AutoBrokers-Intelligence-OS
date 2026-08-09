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
import re
import sys
import unicodedata
from typing import Any, Dict, List, Optional, Set

# 📊 Calibrado no LOTE 1. Abaixo de 30% do vocabulário da carta presente no
# pedaço citado, vale olhar. Não é um veredito — ver o docstring.
LIMIAR_FRACO = 0.30
# E o vizinho só é suspeito se ancorar SENSIVELMENTE melhor. Sem esta margem,
# qualquer vizinho um pouco maior viraria acusação.
MARGEM_DO_VIZINHO = 0.15
VIZINHOS = (-2, -1, 1, 2)


def _vocabulario(texto: str) -> Set[str]:
    """Palavras de 5+ letras, sem acento e em minúscula.

    Palavra curta (`de`, `que`, `não`) aparece em tudo e só faria o número
    subir sem dizer nada. O acento cai porque o PDF e a carta discordam sobre
    ele com frequência — `apólice` no contrato, `apolice` na carta.
    """
    limpo = unicodedata.normalize("NFKD", str(texto or "")).encode(
        "ascii", "ignore").decode()
    return set(re.findall(r"[a-z]{5,}", limpo.lower()))


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
    print(f"  {'ramo':<14} {'cartas':>7} {'órfãs':>7} {'fracas':>7} {'vizinho+':>9}")
    casos: List[Dict[str, Any]] = []
    orfas_total = 0

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        ramo = nome.split("_")[0]
        total = orfas = fracas = suspeitas = 0

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

                vocab = _vocabulario(carta.get("texto", ""))
                citado = _cobertura(vocab, pedacos[unit_id])
                if citado >= LIMIAR_FRACO:
                    continue
                fracas += 1

                melhor = None
                for passo in VIZINHOS:
                    v = _vizinho(pedacos, unit_id, passo)
                    if not v:
                        continue
                    cob = _cobertura(vocab, v)
                    if cob > citado + MARGEM_DO_VIZINHO and (
                            melhor is None or cob > melhor[1]):
                        melhor = (passo, cob, v)
                if melhor:
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
        print(f"  {ramo:<14} {total:>7} {orfas:>7} {fracas:>7} {suspeitas:>9}")

    suspeitas_total = sum(1 for c in casos if c["vizinho_ancora_melhor"])
    print()
    print(f"  cartas para leitura     : {len(casos)}")
    print(f"  destas, com vizinho melhor: {suspeitas_total}   ← o sinal forte")
    print(f"  ÓRFÃS                   : {orfas_total}   ← estas são defeito, não sinal")

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
    return 1 if orfas_total else 0


if __name__ == "__main__":
    sys.exit(main())
