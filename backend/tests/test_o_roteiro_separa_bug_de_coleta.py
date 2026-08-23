# -*- coding: utf-8 -*-
r"""O veredito mais grave da ONDA G — e o controle que o valida.

`SEM_CORPUS` é uma de duas coisas, e a diferença decide QUEM trabalha:

    coleta legítima  →  🧑 alguém pede o serviço no WhatsApp da seguradora
    bug de leitura   →  🤖 alguém conserta o decodificador

📊 Trocar uma pela outra já custou meses: as quatro rotas de `bradesco/auto`
ficaram `SEM_CORPUS` com 159 telas no acervo porque o `DESEMPATE` estava
declarado e nunca lido (P-084-58). O veredito 🔴 SUSPEITO DE BUG nasceu disso.

🔴 E o veredito nasceu SEM CONTROLE. Ele dizia "nenhuma ROTA deste corredor tem
telas" e concluía bug — mas a tabela de rotas não é o corpus. Em `mapfre/auto` o
decodificador funciona (nomeia `carro_reserva` em 14 linhas) e simplesmente
ninguém pediu assistência: 6 sessões de deflexão de sinistro, carro reserva,
abandono por inatividade e canal do corretor.

Este guarda prova as DUAS metades — que hoje a mapfre NÃO é bug, e que o
veredito de bug **continua conseguindo disparar**. Um guarda que não tem como
ficar vermelho não guarda nada.
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import replay as RP           # noqa: E402
import roteiro_de_coleta as RC  # noqa: E402

OK = FAIL = 0


def certo(cond, nome, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  OK {nome}")
    else:
        FAIL += 1
        # 🔴 "FALHOU" PRIMEIRO, e o marcador depois. `_assercao_vermelha` da
        #    bateria de mutações só reconhece a linha que COMEÇA com FALHA/
        #    FALHOU — e um emoji na frente faz a mutação ser reportada como
        #    "enfeite" mesmo tendo derrubado a asserção certa. Medido aqui.
        print(f"  FALHOU \U0001F534 {nome}" + (f"\n       {detalhe}" if detalhe else ""))


def vereditos():
    return {(r.seguradora, r.ramo, r.servico): v for r, _, v, _, _, _, _ in RC.levantar()}


print("=" * 74)
print("O ROTEIRO SEPARA BUG DE COLETA")
print("=" * 74)

hoje = vereditos()

# ── 1 · a mapfre NÃO é bug ───────────────────────────────────────────────────
mapfre = {k: v for k, v in hoje.items() if k[0] == "mapfre"}
certo(len(mapfre) == 4, "as quatro rotas da mapfre estao SEM_CORPUS", str(mapfre))
certo(all(v == "NINGUÉM PEDIU ASSISTÊNCIA" for v in mapfre.values()),
      "\U0001F534 mapfre/auto: NINGUEM PEDIU ASSISTENCIA — nao e bug",
      str(mapfre))

# 📊 e a razão é MEDIDA, não afirmada: o decodificador nomeia algo neste corpus
nomeados = {str(l.get("servico")) for l in RP.carregar_corpus("mapfre", "auto")
            if l.get("servico")}
certo(nomeados, "\U0001F534 e a razao e medida: o decodificador nomeia servico "
      "no corpus da mapfre", f"nomeados={sorted(nomeados)}")
certo("carro_reserva" in nomeados,
      "   — e o que ele nomeia e `carro_reserva`, que NAO e rota",
      str(sorted(nomeados)))

# ── 2 · nenhuma rota fica sem veredito ───────────────────────────────────────
certo(len(hoje) == 30, "as 30 rotas SEM_CORPUS tem veredito", str(len(hoje)))
certo(not [k for k, v in hoje.items() if v == "🔴 SUSPEITO DE BUG"],
      "e hoje NENHUMA delas e suspeita de bug",
      str([k for k, v in hoje.items() if v == "🔴 SUSPEITO DE BUG"]))

# ── 3 · 🔴 CONTROLE: o veredito de BUG ainda consegue disparar ───────────────
# Sem esta metade, apagar o ramo inteiro do código passaria verde: "nenhum bug"
# seria indistinguível de "o detector nunca acusa".
_original = RP.carregar_corpus


def _sem_servico(seguradora, ramo):
    linhas = _original(seguradora, ramo)
    if seguradora == "mapfre":
        return [dict(l, servico=None, servico_nivel="-") for l in linhas]
    return linhas


RC.RP.carregar_corpus = _sem_servico
try:
    mutado = vereditos()
finally:
    RC.RP.carregar_corpus = _original

certo(all(mutado[k] == "🔴 SUSPEITO DE BUG" for k in mapfre),
      "\U0001F534 CONTROLE: com o decodificador CEGO na mapfre, as mesmas "
      "quatro rotas viram SUSPEITO DE BUG",
      str({k: mutado[k] for k in mapfre}))

certo({k: v for k, v in mutado.items() if k[0] != "mapfre"} ==
      {k: v for k, v in hoje.items() if k[0] != "mapfre"},
      "   — e as outras 26 rotas nao se moveram (a mutacao foi so na mapfre)")

certo(vereditos() == hoje,
      "   — e o veredito volta ao que era depois de restaurar")

# ── 4 · o CONTROLE DE COLETA muda de texto quando nao ha irma viva ───────────
sem_irma = RC._controle_de_coleta(None, [], ("carro_reserva",))
com_irma = RC._controle_de_coleta(None, [("guincho", 36)])
certo(sem_irma != com_irma,
      "os dois controles de coleta CONSEGUEM ser diferentes")
certo("carro_reserva" in sem_irma,
      "e o de fora-das-rotas nomeia o assunto que o decodificador viu",
      sem_irma[:90])
certo("guincho" in com_irma and "36" in com_irma,
      "e o de irma viva nomeia a irma e o tamanho do acervo dela",
      com_irma[:90])

MUTACOES = [
    # (arquivo, texto_de, texto_para, rotulo_da_assercao_que_deve_cair)
    #
    # C21 - cega a pergunta que o veredito passou a fazer ao CORPUS: o
    # decodificador nomeou algum servico aqui? Com `decodificou` sempre vazio,
    # as quatro rotas da mapfre voltam a ser acusadas de um bug que nao existe.
    #
    # 🔴 A PRIMEIRA REDACAO DESTA MUTACAO ERA INVALIDA, e quem pegou foi o
    #    proprio `test_nenhuma_mutacao_foi_commitada` na estreia da varredura
    #    ampliada. Ela trocava `elif not vivas and not decodificou:` por
    #    `elif not vivas:` -- e essa segunda linha EXISTE no codigo saudavel,
    #    logo abaixo, como o ramo do veredito novo. O guarda C12 pergunta "o
    #    `texto_para` esta no commit?", e a resposta seria SIM para sempre:
    #    uma acusacao permanente de mutacao commitada que nunca houve.
    #    ⚠️ Regra que fica: o `texto_para` de uma mutacao precisa ser texto que
    #    **nao pode existir** no produto saudavel.
    ("scripts/roteiro_de_coleta.py",
     '        decodificou = sorted({str(l.get("servico")) for l in corpus',
     '        decodificou = sorted({str(l.get("servico")) for l in []',
     "mapfre/auto: NINGUEM PEDIU ASSISTENCIA"),
]


print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
raise SystemExit(1 if FAIL else 0)
