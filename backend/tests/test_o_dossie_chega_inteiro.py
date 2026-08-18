# -*- coding: utf-8 -*-
"""O dossie de suporte humano chega INTEIRO, e legivel.

📊 MEDIDO em 18/08/2026, na foto do grupo TESTE SUPORTE HUMANO. O handoff
funcionou -- e o dossie chegou assim:

    [balao 1] 🔔 ATENDIMENTO PRECISA DE VOCE / ---- / 138847853768811 · 138847853768811
    [balao 2] O QUE ACONTECEU ...
    [balao 3] 👉 O QUE FAZER ...
    [balao 4] CONVERSA (ultimas 1) / 00:00 👤 celular Obrigado
    [balao 5] link

QUATRO defeitos numa foto so:

1. PICOTADO. `send_message` sempre passa por `split_whatsapp_balloons`, que
   parte a cada ~300 caracteres. Isso existe por um motivo BOM -- a atendente
   falando com o segurado tem de soar gente. Mas o dossie nao e conversa, e um
   DOCUMENTO. Cinco baloes destroem o que ele promete: a atendente rola a tela
   para juntar o caso na cabeca com o cliente esperando.

2. TRACO DE 22 nao cabia na largura do balao e quebrava em duas linhas --
   um traco longo seguido de um toco. Aparecem tres tocos na foto.

3. `138847853768811 · 138847853768811`. Sem `pushName`, o `user_name` nasce
   igual ao identificador e o dossie imprimia o MESMO numero duas vezes.

4. `00:00` num caso das 21h. `created_at[11:16]` entrega UTC cru. A atendente
   usa essa hora para saber ha quanto tempo o cliente espera; errar em 3 horas
   e pior que nao mostrar hora.
"""
from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:260] if extra else ""))


def carregar(rotulo, caminho):
    """Carrega o modulo SOZINHO -- `app.services.__init__` puxa o SDK da OpenAI."""
    spec = importlib.util.spec_from_file_location(rotulo, os.path.join(RAIZ, caminho))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BAL = carregar("bal_isolado", "app/services/whatsapp/balloons.py")

with open(os.path.join(RAIZ, "app/services/whatsapp_service.py"), encoding="utf-8") as _fh:
    _FONTE_WS = _fh.read()

# `whatsapp_service.py` importa o pacote inteiro no topo (zapi, registry...).
# `_fatiar_documento` e puro, entao executamos O TRECHO DO ARQUIVO -- nao uma
# copia escrita aqui, que ficaria verde mesmo com o arquivo errado.
WS: dict = {}
exec(_FONTE_WS[_FONTE_WS.index("_TETO_DE_UMA_MENSAGEM = "):
               _FONTE_WS.index("class WhatsappService:")], WS)  # noqa: S102
_fatiar_documento = WS["_fatiar_documento"]
_TETO = WS["_TETO_DE_UMA_MENSAGEM"]

# 📊 O dossie REAL da foto, reconstruido.
DOSSIE = "\n".join([
    "🔔 *ATENDIMENTO PRECISA DE VOCÊ*",
    "━━━━━━━━━━",
    "(47) 98808-7463",
    "",
    "*O QUE ACONTECEU*",
    "O cliente relatou um vazamento na conexão do tubo cromado com o vaso "
    "sanitário e enviou foto. Pediu para acionar a assistência residencial. "
    "A IA coletou os dados e não conseguiu concluir sozinha.",
    "",
    "*O QUE FALTA*",
    "⚠️ número da casa",
    "⚠️ período preferido",
    "",
    "*👉 O QUE FAZER*",
    "Confira o que o agente coletou e siga com o atendimento. Se estiver tudo "
    "certo, é só concluir.",
    "",
    "━━━━━━━━━━",
    "*CONVERSA* _(últimas 3)_",
    "21:31 Cliente  boa noite, tem um vazamento aqui em casa",
    "21:33 🤖 IA  Boa noite! Sinto muito. Pode me dizer o número da residência?",
    "21:39 👤 celular  Obrigado",
    "━━━━━━━━━━",
    "▶ https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host"
    "/dashboard/atendimentos/conversas?c=37aea1e6-9d9f-410c-a4a2-91f7a1bf550a",
    "_Ninguém assumiu ainda_",
])

# ==========================================================================
print("\n[1] O dossie vai em UMA mensagem")
# ==========================================================================

pedacos = _fatiar_documento(DOSSIE)
check("o dossie inteiro sai numa mensagem so", len(pedacos) == 1,
      f"saiu em {len(pedacos)} pedacos")
check("e nada dele se perde no caminho",
      bool(pedacos) and pedacos[0].strip() == DOSSIE.strip())

# 🔴 CONTROLE -- prova que o problema era REAL e que o caminho novo e diferente
# do antigo. Sem esta linha, um `_fatiar_documento` que devolvesse `[texto]`
# sempre passaria acima sem provar que consertou coisa alguma.
baloes = BAL.split_whatsapp_balloons(DOSSIE)
check("CONTROLE: o caminho ANTIGO (humanizacao) realmente picotava",
      len(baloes) >= 4,
      f"a humanizacao fez {len(baloes)} baloes -- se der 1, o defeito nunca existiu")

# ==========================================================================
print("\n[2] Documento GRANDE parte -- mas nunca no meio de uma linha")
# ==========================================================================
#
# O WhatsApp recusa acima de ~4096. Um dossie de 20 mensagens passa disso.
# Partir e o fracasso, nao o objetivo -- mas cortar uma linha ao meio seria
# pior que partir.

GIGANTE = "\n".join([f"21:{i:02d} Cliente  mensagem numero {i} " + "x" * 90
                     for i in range(60)])
partes = _fatiar_documento(GIGANTE)
check("um dossie gigante e partido", len(partes) > 1, f"{len(partes)} pedacos")
check("cada pedaco cabe numa mensagem",
      all(len(x) <= _TETO for x in partes),
      [len(x) for x in partes])
check("nenhuma linha foi cortada ao meio",
      [l for l in "\n".join(partes).splitlines() if l.strip()]
      == [l for l in GIGANTE.splitlines() if l.strip()])

check("CONTROLE: uma linha unica maior que o teto ainda sai (nao trava)",
      len(_fatiar_documento("y" * 9000)) == 3)
check("CONTROLE: texto vazio nao vira mensagem vazia",
      _fatiar_documento("   ") == [])

# ==========================================================================
print("\n[3] O dossie usa o caminho de documento, nao o de conversa")
# ==========================================================================

with open(os.path.join(RAIZ, "app/agents/tools/human_handoff.py"), encoding="utf-8") as fh:
    fonte_h = fh.read()
# 🔴 LE A ARVORE, nao o texto. A versao anterior era
# `"bloco_unico=True" in fonte_h` e ficou VERDE com a chamada mutada -- porque
# a string aparece tambem no COMENTARIO que explica o conserto. Sexta assercao
# desta SPEC a passar pelo motivo errado. Agora exige uma chamada real a
# `send_message` dentro de `_avisar_suporte` com esse argumento em True.
def _pede_bloco_unico(fonte: str) -> bool:
    import ast

    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if no.name != "_avisar_suporte":
            continue
        for x in ast.walk(no):
            if not isinstance(x, ast.Call):
                continue
            if getattr(x.func, "attr", "") != "send_message":
                continue
            for kw in x.keywords:
                if kw.arg == "bloco_unico" and getattr(kw.value, "value", None) is True:
                    return True
    return False


check("`_avisar_suporte` pede bloco unico na CHAMADA", _pede_bloco_unico(fonte_h))
_SEM_O_ARGUMENTO = chr(10).join([
    "async def _avisar_suporte(self):",
    "    # bloco_unico=True",
    "    return svc.send_message(destino, texto, integ)",
])
check("CONTROLE: o detector nao acha bloco unico onde ha so o comentario",
      not _pede_bloco_unico(_SEM_O_ARGUMENTO),
      "um detector que casa comentario nao prova nada")
check("e `send_message` sabe o que fazer com isso", "bloco_unico" in _FONTE_WS)

# 🔴 CONTROLE -- a humanizacao continua LIGADA para quem fala com o segurado.
# Se o conserto tivesse simplesmente desligado os baloes para todo mundo, a
# atendente voltaria a mandar textao e as assercoes acima nao notariam.
# (A humanizacao quebra em PARAGRAFO, nao no meio de um. Um paragrafo unico de
# 330 caracteres sai inteiro de proposito -- descobri isso escrevendo este
# controle errado da primeira vez. A atendente escreve em paragrafos.)
RESPOSTA_DA_ATENDENTE = (chr(10) * 2).join([
    "Boa noite! Sinto muito pelo transtorno com o vazamento. Vou acionar a "
    "assistencia residencial agora mesmo para voce.",
    "Antes disso preciso confirmar duas coisas rapidas: qual o numero da "
    "residencia, e qual o melhor periodo para o profissional ir ate ai?",
    "Assim que eu tiver esses dois dados eu abro o chamado e te passo o "
    "retorno por aqui mesmo.",
])
check("CONTROLE: a atendente falando com o segurado AINDA quebra em baloes",
      len(BAL.split_whatsapp_balloons(RESPOSTA_DA_ATENDENTE)) >= 2,
      "se virou 1, a humanizacao morreu junto com o conserto")

# ==========================================================================
print("\n[4] Os tres defeitos visiveis da foto")
# ==========================================================================
#
# `human_handoff.py` importa langchain, que a maquina de teste nao tem. As
# funcoes abaixo sao PURAS -- executamos o trecho do arquivo, e nao uma copia
# escrita aqui. Copia ficaria verde com o arquivo errado.

ns: dict = {}
trecho = fonte_h[fonte_h.index('_TRACO = "'):fonte_h.index("def _linha_da_conversa")]
exec("from datetime import datetime, timedelta, timezone\n" + trecho, ns)  # noqa: S102

check("o traco tem 10 caracteres, nao 22", len(ns["_TRACO"]) == 10, len(ns["_TRACO"]))
check("CONTROLE: e ainda E um traco (nao virou string vazia)",
      set(ns["_TRACO"]) == {"━"})

hora = ns["_hora_de_brasilia"]
check("21:39 UTC vira 18:39 em Brasilia", hora("2026-08-18T21:39:00Z") == "18:39",
      hora("2026-08-18T21:39:00Z"))
check("00:39 UTC vira 21:39 do dia ANTERIOR -- o caso da foto",
      hora("2026-08-18T00:39:00+00:00") == "21:39",
      hora("2026-08-18T00:39:00+00:00"))
check("CONTROLE: lixo nao explode, devolve --:--", hora("nao e uma data") == "--:--")
check("CONTROLE: vazio devolve --:--", hora(None) == "--:--")

check("o dossie apaga o nome quando ele e so o proprio numero",
      "so_digitos == quem" in fonte_h)


def _quem(nome: str) -> str:
    """A mesma regra do dossie, para exercitar os tres casos."""
    so_digitos = "".join(ch for ch in nome if ch.isdigit())
    return "" if nome and so_digitos == nome else nome


check("nome que e so o proprio numero some", _quem("138847853768811") == "")
check("CONTROLE: nome de gente continua aparecendo", _quem("Amandus") == "Amandus")
check("CONTROLE: nome com numero no meio continua aparecendo",
      _quem("Oficina 24h") == "Oficina 24h")

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
