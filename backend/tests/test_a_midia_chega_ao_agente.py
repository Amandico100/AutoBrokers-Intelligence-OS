# -*- coding: utf-8 -*-
"""A midia do segurado chega ao agente -- imagem, audio e documento.

OS DOIS DEFEITOS QUE ESTE ARQUIVO GUARDA, medidos em 17/08/2026 no primeiro
teste real de atendimento da Resulta.

1. A IMAGEM SUBIA E NINGUEM CONSEGUIA VER
   O arquivo estava no bucket (22:54:20, chat-media). A atendente respondeu
   "essa imagem nao chegou ate mim com conteudo visivel".
   Causa: chat-media / chat-docs / voice-messages sao buckets PRIVADOS
   (storage.buckets.public = false) e o codigo pedia `get_public_url()` --
   endereco bem-formado que responde 400. Tres caminhos morriam em silencio:
   o re-download em `process_image_for_vision`, o bloco de visao, e o proprio
   modelo (que recebe a imagem COMO URL, vision_service.py:107).

2. CADA MENSAGEM DO SEGURADO ERA GRAVADA DUAS VEZES
   22:32:47 origem='espelho' wa_id=A55384CB...
   22:32:57 origem=null      wa_id=null
   Dois escritores, ~10s de diferenca (o segundo e o pipeline, depois do
   buffer). O espelho deduplica por wa_message_id; o pipeline nao grava esse
   campo. O modelo LIA cada mensagem duas vezes -- foi isso que fez a
   atendente responder tres coisas de uma vez e perder o fio.
"""
from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBHOOK = os.path.join(RAIZ, "app", "api", "webhook.py")
OBSERVER = os.path.join(RAIZ, "app", "services", "atlas", "observer_intake.py")
VISION = os.path.join(RAIZ, "app", "services", "vision_service.py")

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:260] if extra else ""))


def ler(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def corpo(fonte, nome):
    """O codigo de uma funcao, SEM comentarios -- ast.unparse nao os preserva.

    Casar com o texto do arquivo pegaria os comentarios que EXPLICAM o defeito
    antigo, e o guarda ficaria verde citando a propria documentacao. Ja
    aconteceu quatro vezes nesta SPEC.
    """
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return ast.unparse(no)
    return ""


w = ler(WEBHOOK)
o = ler(OBSERVER)
v = ler(VISION)

# ==========================================================================
print("\n[1] A URL da midia ABRE -- bucket privado exige assinatura")
# ==========================================================================

check("existe um resolvedor unico de URL de midia", "_url_de_midia" in w)

helper = corpo(w, "_url_de_midia")
check("ele ASSINA a URL", "create_signed_url" in helper)
check("e le a chave que o Supabase devolve", "signedURL" in helper)

# Nenhum caminho de upload pode devolver public_url direto.
for fn in ("process_image_for_vision", "process_audio_for_storage", "_upload_media_bytes"):
    c = corpo(w, fn)
    if not c:
        continue
    check(f"{fn} usa o resolvedor, nao `get_public_url`",
          "get_public_url" not in c and ("_url_de_midia" in c or "storage" not in c),
          "bucket privado + get_public_url = URL que responde 400")

# 🔴 CONTROLE — as assercoes acima sao negativas ("nao contem"). Uma funcao
# vazia passaria em todas. Esta exige que o caminho da imagem EXISTA.
check("CONTROLE: o caminho da imagem realmente sobe e devolve uma URL",
      "create_signed_url" in helper and "_url_de_midia" in corpo(w, "process_image_for_vision"),
      "sem isto, o bloco [1] passaria sobre um arquivo vazio")

# O modelo recebe a imagem COMO URL — por isso ela tem de abrir de fora.
check("o modelo de visao recebe a imagem por URL (logo, ela precisa abrir)",
      '"image_url"' in v and "image_url" in corpo(v, "describe_image"))

# ==========================================================================
print("\n[2] UMA mensagem, UM escritor")
# ==========================================================================

ponte = corpo(o, "_espelhar_no_chat_da_corretora")
check("a ponte do espelho sabe se o agente esta ligado", "agente_ligado" in ponte)
# 🔴 REESCRITO: a versao anterior testava `"agente_ligado" in ponte and
# "fromMe" in ponte` e ficou VERDE com o guarda REMOVIDO -- porque `fromMe`
# aparece tambem na linha `direcao=`. Assercao passando pelo motivo errado,
# pela quinta vez nesta SPEC. Agora le a ARVORE: precisa existir um `if` que
# testa `agente_ligado` E `fromMe` e cujo corpo RETORNA.
def _cede_o_inbound(fonte: str) -> bool:
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if no.name != "_espelhar_no_chat_da_corretora":
            continue
        for x in ast.walk(no):
            if not isinstance(x, ast.If):
                continue
            teste = ast.unparse(x.test)
            if "agente_ligado" not in teste or "fromMe" not in teste:
                continue
            if any(isinstance(c, ast.Return) for c in x.body):
                return True
    return False


check("e o espelho CEDE o inbound quando ele esta ligado",
      _cede_o_inbound(o),
      "com o agente ligado quem grava o que entra e o pipeline")
_SEM_O_GUARDA = chr(10).join([
    "async def _espelhar_no_chat_da_corretora(a, agente_ligado=False):",
    "    if agente_ligado:",
    "        pass",
    "    return None",
])
check("CONTROLE: o detector NAO acha o guarda num codigo sem ele",
      not _cede_o_inbound(_SEM_O_GUARDA),
      "um detector que acha qualquer `if` nao prova nada")

tap = corpo(o, "observer_tap")
check("os chamadores repassam o estado real do agente",
      tap.count("agente_ligado=_agente_ligado") >= 2,
      f"achei {tap.count('agente_ligado=_agente_ligado')} de 2")

# 🔴 CONTROLE — o que SAI continua espelhado. Sem esta linha, um `return`
# incondicional no topo da ponte passaria em tudo acima e apagaria a fala da
# equipe pelo celular do painel.
check("CONTROLE: a ponte NAO devolve cedo sempre -- o `fromMe` ainda espelha",
      "espelhar_no_chat(" in ponte,
      "se a ponte nunca chama espelhar_no_chat, ela nao espelha mais nada")

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
