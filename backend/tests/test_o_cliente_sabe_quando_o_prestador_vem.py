# -*- coding: utf-8 -*-
"""🔴 O DESFECHO É O NÚMERO **E** O QUANDO — P-084-7 e P-084-8.

> ## O segurado recebia o protocolo e não sabia quando o prestador vinha.

E isso é a única coisa que ele quer saber. Duas coisas separadas estavam
erradas ao mesmo tempo, e as duas passavam despercebidas porque a régua só
perguntava "a âncora casou?".

```
P-084-8   a PORTO agenda por JANELA ("no dia 25/08, entre 13h e 14h") e
          `capture_anchors.schedule` exige a data COLADA em "para". 5 telas
          residenciais e 1 auto — TODAS a última mensagem útil do acionamento.

P-084-7   a régua chamava de 🟠 ANCORA_SUSPEITA o que era MÁSCARA DE CORPUS.
          Cinco rotas, e três delas mandavam para COLETA um acervo cheio.
```

⚠️ **Os dois testes daqui rodam pelo MOTOR** (`extract_capture_anchors`), nunca
pelo regex direto — é o corolário do §9.4 do CLAUDE.md, escrito depois que
`schedule_agendado` passou num teste que chamava o regex e nunca o motor.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M          # noqa: E402  (instala o shim de `app`)
import medir_rota as MR          # noqa: E402

_verdes: list = []
_vermelhas: list = []


def check(nome: str, ok: bool, detalhe: object = "") -> None:
    if ok:
        _verdes.append(nome)
        print(f"  [ok] {nome}")
    else:
        _vermelhas.append(nome)
        print(f"  [FALHOU] {nome}  {detalhe}")


PA = M.get_playbook("porto-auto-whatsapp@v1")
PR = M.get_playbook("porto-residencial-whatsapp@v1")

print("=" * 74)
print("[1] P-084-8 — a PORTO entrega o QUANDO, e nao so o protocolo")
print("=" * 74)

# 📊 As redações medidas no acervo. As três primeiras davam `{}` antes de hoje.
JANELAS = [
    ("residencial, dia + faixa",
     PR, "Pronto! Tudo certo com o seu agendamento. O prestador deve chegar ao seu "
         "endereco no dia 25/08/2026, entre 13h00 e 14h00.",
     {"day": "25/08/2026", "from": "13h00", "to": "14h00"}),
    ("residencial, 'previsto para ser realizado'",
     PR, "O servico esta previsto para ser realizado no dia 25/08/2026, entre "
         "14h00 e 14h30.",
     {"day": "25/08/2026", "from": "14h00", "to": "14h30"}),
    ("o RESUMO, com 'Agendamento:'",
     PR, "Confira o resumo da sua solicitacao *Agendamento*: 25/08/2026, entre "
         "13h00 e 14h00",
     {"day": "25/08/2026", "from": "13h00", "to": "14h00"}),
    ("auto, 'hoje' + faixa",
     PA, "O prestador deve chegar ao seu endereco *hoje*, entre 18h00 e 20h00.",
     {"day": "hoje", "from": "18h00", "to": "20h00"}),
]
for nome, pb, tela, esperado in JANELAS:
    got = M.extract_capture_anchors(pb, tela).get("schedule")
    check(f"pelo MOTOR: {nome}", got == esperado, got)

# 🔴 O CONTROLE QUE DA DIREITO A CONCLUSAO: a tela de URGENCIA nao tem "entre",
#    e o `eta` continua sendo dela. Se a ancora nova roubasse esta, ela estaria
#    trocando "em ate 60 minutos" por uma janela que ninguem prometeu.
urgente = "O servico esta previsto para ser realizado *hoje*, em ate 60 minutos."
cap = M.extract_capture_anchors(PA, urgente)
check("CONTROLE: a tela de URGENCIA nao vira janela", cap.get("schedule") is None,
      cap.get("schedule"))
check("CONTROLE: e o `eta` continua sendo dela", cap.get("eta_minutes") == "60",
      cap.get("eta_minutes"))

# ⚠️ E a chave TEM LEITOR. Declarar sem ler e o defeito que este arquivo ja
#    pagou tres vezes (`TETO_DE_INDEFINIDO`, `schedule_agendado`,
#    `ticket_de_entrada`). A prova: a chave existe E o motor devolve valor.
check("a chave `schedule_porto` esta declarada nos DOIS corredores da porto",
      "schedule_porto" in PA["capture_anchors"]
      and "schedule_porto" in PR["capture_anchors"])
check("🔴 e ela TEM LEITOR (o motor devolve, nao so declara)",
      M.extract_capture_anchors(PR, JANELAS[0][2]).get("schedule") is not None)

print()
print("=" * 74)
print("[2] P-084-7 — mascara de corpus NAO e defeito de ancora")
print("=" * 74)

# 📊 As formas reais, uma por seguradora afetada.
MASCARADAS = [
    ("azul/porto", "Aqui esta seu protocolo de atendimento 👇\n\n1-{NUMERO}"),
    ("tokio", "Seu protocolo de atendimento e {CEP}."),
    ("mapfre", "O numero de protocolo para este atendimento e: {CARTAO}"),
]
for nome, tela in MASCARADAS:
    check(f"a frase do desfecho e reconhecida como MASCARADA ({nome})",
          bool(MR._RX_DESFECHO_MASCARADO.search(M._norm(tela))), tela[:48])

# 🔴 CONTROLE NEGATIVO: uma tela QUALQUER com marcador nao vira desfecho.
#    Sem esta linha, a regra poderia estar casando `{` em qualquer lugar.
NAO_SAO = [
    "Digite o endereco completo do local, desta forma: {ENDERECO}",
    "O numero de telefone {TELEFONE} esta correto?",
    "Ola {NOME} - {CORRETORA}, vou iniciar seu atendimento!",
]
for tela in NAO_SAO:
    check(f"CONTROLE: NAO e desfecho — {tela[:40]}",
          not MR._RX_DESFECHO_MASCARADO.search(M._norm(tela)))

# 🔴 E o controle que prova que a regra MUDOU alguma coisa: com o numero de
#    verdade no lugar do marcador, quem responde e a ancora de PROTOCOLO, nao a
#    de mascarado. As duas nao competem — elas se excluem.
real = "Aqui esta seu protocolo de atendimento 👇 1-128312189741"
check("🔴 com o numero REAL, quem captura e `protocol`",
      bool(M.extract_capture_anchors(M.get_playbook("azul-auto-whatsapp@v1"), real)
           .get("protocol")),
      M.extract_capture_anchors(M.get_playbook("azul-auto-whatsapp@v1"), real))

print()
print("=" * 74)
print(f"  {len(_verdes)} assercoes verdes - {len(_vermelhas)} vermelhas")
print("=" * 74)
sys.exit(1 if _vermelhas else 0)
