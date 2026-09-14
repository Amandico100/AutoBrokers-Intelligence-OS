# -*- coding: utf-8 -*-
"""M-E1 -- A PERGUNTA SOBREVIVE AO BLOCO (SPEC-EXTRA-001.1, BLOCO E).

O DEFEITO QUE ESTE ARQUIVO GUARDA
------------------------------------------------------------------------------
> "ainda nao recebi uma pergunta sua"  -- o agente, DUAS vezes, nos DOIS
> maiores turnos do acervo (laudos I1/I2, 09 e 10/09/2026: 120 e 128 chunks de
> RAG; 135k e 163k tokens de entrada).

O ELO que este guarda mede
------------------------------------------------------------------------------
```
o agente RESPONDE A PERGUNTA mesmo no turno enorme
  PORQUE o bloco recuperado tem TETO DECLARADO (`montar_bloco_recuperado`)
  E PORQUE o que nao coube e DITO, com os numeros, dentro do proprio bloco
  E PORQUE a pergunta e REPETIDA DEPOIS do bloco -- o fim do contexto
  E PORQUE quem monta o `dynamic_context` de producao CHAMA essa funcao
     (o gate [G5]: sem ele, os quatro primeiros provariam uma funcao que
      ninguem usa -- CLAUDE.md 9.4)
```

A REFERENCIA EXTERNA (protocolo 7.3)
------------------------------------------------------------------------------
Liu et al., TACL 2023, "Lost in the Middle: How Language Models Use Long
Contexts" -- https://arxiv.org/abs/2307.03172 (reaberta em 14/09/2026):
*"Performance is often highest when relevant information occurs at the
beginning or end of the input context, and significantly degrades when models
must access relevant information in the middle of long contexts, even for
explicitly long-context models."*
MODELAMOS UM PONTO: **posicao**. A pergunta vai para o FIM.
REJEITAMOS: "contexto grande e ruim, corte o RAG" -- o paper mede posicao, nao
volume.

O TAMANHO DO TURNO SINTETICO, e por que ele e sintetico
------------------------------------------------------------------------------
📊 D3 do BLOCO 0 (14/09/2026): os dois turnos grandes **nao sao reconstruiveis
pelo banco** -- `payload.turn.stages` = [] nos dois, `usage` ausente, e nao ha
tabela de chunks no Postgres (o indice e o Qdrant). Os numeros 120/128 chunks e
135k/163k tokens vieram dos laudos sobre LOG.
Logo: o turno deste guarda e SINTETICO, com o tamanho DECLARADO daqueles
(>= 128 trechos e >= 600.000 chars), e o texto vem do ACERVO
(`tests/corpus/telas_reais/`, a referencia interna do protocolo 7.1), nunca da
imaginacao. 📊 o acervo tem 4.279 telas reais e 629.286 chars.
⛔ Nenhuma PII: o corpus ja nasce mascarado (ver `corpus/telas_reais/INDICE.md`).

AS MUTACOES -- por COPIA, em SUBPROCESSO, so com `--mutar`
------------------------------------------------------------------------------
    M1  a repeticao da pergunta some            -> [G1] vermelho
    M2  o teto vira `conteudo[:N]` silencioso   -> [G2] [G4] vermelho
    M3  o chamador de producao volta a concatenar o bloco cru
                                                -> [G5] vermelho
Um gate que NAO fica vermelho sob a sua mutacao e um carimbo, nao um guarda
(CLAUDE.md 9.3).

Rodar (a partir de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_pergunta_sobrevive_ao_bloco.py
    ... --so G2          so um gate
    ... --mutar          as tres mutacoes, cada uma em subprocesso
"""
from __future__ import annotations

import ast
import glob
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

PASS = 0
FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))
    return bool(cond)


def _ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return fh.read()


def _motor():
    """O MOTOR de producao -- nunca uma copia da regra (CLAUDE.md 9.4)."""
    return importlib.import_module("app.agents.graph")


# ==========================================================================
# O TURNO SINTETICO, montado do ACERVO
# ==========================================================================
PERGUNTA = "Qual e a cobertura de danos eletricos dessa apolice e qual a franquia?"


def _telas_do_acervo():
    textos = []
    for arquivo in sorted(glob.glob(os.path.join(
            RAIZ, "tests", "corpus", "telas_reais", "*.jsonl"))):
        for linha in io.open(arquivo, encoding="utf-8"):
            try:
                registro = json.loads(linha)
            except ValueError:
                continue
            texto = (registro.get("text") or "").strip()
            if texto:
                textos.append(texto)
    return textos


def conteudo_recuperado(n_trechos, chars_por_trecho):
    """Reproduz a FORMA do que `smart_search` devolve em `content`.

    📊 `app/services/search_service.py:963,985` (lido em 14/09/2026): cada
    trecho e `"[<doc> | Score: X (banda)]:\\n<conteudo>"` e a juncao e
    `"\\n\\n---\\n\\n".join(content_parts)`. 🔴 Montar o corpus com OUTRA forma
    provaria o corte sobre um texto que a producao nunca ve.
    """
    telas = _telas_do_acervo()
    assert telas, "acervo de telas reais vazio -- corpus ausente"
    trechos = []
    cursor = 0
    for i in range(n_trechos):
        corpo = []
        tamanho = 0
        while tamanho < chars_por_trecho:
            tela = telas[cursor % len(telas)]
            cursor += 1
            corpo.append(tela)
            tamanho += len(tela) + 1
        trechos.append("[Manual de coberturas %03d | Score: 0.71 (Alta)]:\n%s"
                       % (i + 1, "\n".join(corpo)))
    return SEPARADOR().join(trechos), trechos


def SEPARADOR():
    return _motor().SEPARADOR_DE_TRECHOS


# ==========================================================================
# G1 -- A PERGUNTA VEM DEPOIS DO BLOCO
# ==========================================================================
def gate_G1():
    print("\n[G1] a pergunta aparece DEPOIS do fim do bloco recuperado")
    graph = _motor()
    conteudo, trechos = conteudo_recuperado(128, 4800)
    check("[G1] o turno sintetico tem o tamanho DECLARADO dos dois piores "
          "(>=128 trechos, >=600.000 chars)",
          len(trechos) >= 128 and len(conteudo) >= 600000,
          "trechos=%d chars=%d" % (len(trechos), len(conteudo)))

    texto, meta = graph.montar_bloco_recuperado(conteudo, PERGUNTA)

    fim = texto.find("=== FIM DO CONTEXTO RECUPERADO ===")
    pos_pergunta = texto.rfind(PERGUNTA)
    check("[G1] o marcador de fim do bloco existe", fim >= 0)
    check("[G1] a pergunta do usuario esta no texto", pos_pergunta >= 0)
    check("[G1] a pergunta vem DEPOIS do fim do bloco (o FIM do contexto)",
          fim >= 0 and pos_pergunta > fim,
          "fim=%d pergunta=%d" % (fim, pos_pergunta))
    check("[G1] e ela vem rotulada, para o modelo saber o que e",
          "PERGUNTA ATUAL DO USUÁRIO" in texto)
    # CONTROLE: a pergunta nao e so um eco no meio do bloco.
    antes_do_fim = texto[:fim] if fim >= 0 else texto
    check("[G1] CONTROLE: a repeticao NAO esta dentro do bloco",
          PERGUNTA not in antes_do_fim)

    # CONTROLE do controle: sem pergunta, nao se inventa rotulo nenhum.
    texto_sem, _ = graph.montar_bloco_recuperado(conteudo, "")
    check("[G1] CONTROLE: sem pergunta, nenhum rotulo de pergunta e inventado",
          "PERGUNTA ATUAL DO USUÁRIO" not in texto_sem)


# ==========================================================================
# G2 -- O TETO, E O EXCEDENTE DITO COM OS NUMEROS CERTOS
# ==========================================================================
def gate_G2():
    print("\n[G2] o bloco cabe no teto e o excedente e DITO, com os numeros")
    graph = _motor()
    teto = graph.TETO_DO_CONTEXTO_RECUPERADO_CHARS
    check("[G2] o teto e um numero declarado, nao um literal solto",
          isinstance(teto, int) and teto > 0, "teto=%r" % (teto,))

    conteudo, trechos = conteudo_recuperado(128, 4800)
    texto, meta = graph.montar_bloco_recuperado(conteudo, PERGUNTA)

    check("[G2] o bloco cabe no teto",
          meta["chars_depois"] <= teto,
          "depois=%d teto=%d" % (meta["chars_depois"], teto))
    check("[G2] a meta conta os trechos RECUPERADOS e os que ENTRARAM",
          meta["trechos_recuperados"] == len(trechos)
          and 0 < meta["trechos_no_bloco"] < len(trechos),
          "meta=%r" % (meta,))

    de_fora = meta["trechos_recuperados"] - meta["trechos_no_bloco"]
    frase = ("(mostrando os %d trechos mais relevantes de %d — os outros %d "
             "ficaram de fora por TAMANHO, nao por irrelevancia)"
             % (meta["trechos_no_bloco"], meta["trechos_recuperados"], de_fora))
    check("[G2] o excedente e DITO, com os TRES numeros certos",
          frase in texto, "esperado: %r" % frase[:120])

    # 🔴 O QUE IMPEDE O CORTE SILENCIOSO: o texto nunca pode ser um prefixo
    # cru do conteudo. Se alguem trocar a funcao por `conteudo[:N]`, o corpo
    # entra sem a frase acima -- e este par de asercoes fica vermelho.
    check("[G2] o corte NAO e silencioso: o bloco declara que houve corte",
          "ficaram de fora" in texto)
    check("[G2] o ultimo trecho do conteudo NAO entrou (houve corte de fato)",
          trechos[-1] not in texto)


# ==========================================================================
# G3 -- O PAR DE CONTROLE: turno pequeno nao sofre nada
# ==========================================================================
def gate_G3():
    print("\n[G3] PAR DE CONTROLE: com 3 trechos nao ha corte nem frase de excedente")
    graph = _motor()
    conteudo, trechos = conteudo_recuperado(3, 900)
    texto, meta = graph.montar_bloco_recuperado(conteudo, PERGUNTA)

    check("[G3] os 3 trechos entraram inteiros",
          meta["trechos_no_bloco"] == 3 and meta["trechos_recuperados"] == 3,
          "meta=%r" % (meta,))
    check("[G3] nenhum char se perdeu",
          meta["chars_depois"] == meta["chars_antes"],
          "antes=%d depois=%d" % (meta["chars_antes"], meta["chars_depois"]))
    check("[G3] NENHUMA frase de excedente aparece",
          "ficaram de fora" not in texto)
    for i, trecho in enumerate(trechos):
        check("[G3] o trecho %d esta inteiro no bloco" % (i + 1), trecho in texto)
    # e a pergunta continua no fim -- o par nao afrouxa a regra principal
    check("[G3] a pergunta continua DEPOIS do bloco tambem no caso pequeno",
          texto.rfind(PERGUNTA) > texto.find("=== FIM DO CONTEXTO RECUPERADO ==="))

    # CONTROLE 2: conteudo vazio nao vira bloco nenhum.
    vazio, meta_vazio = graph.montar_bloco_recuperado("", PERGUNTA)
    check("[G3] CONTROLE: sem conteudo recuperado, nao ha bloco",
          vazio == "" and meta_vazio["trechos_recuperados"] == 0,
          "%r %r" % (vazio[:40], meta_vazio))


# ==========================================================================
# G4 -- O TETO NUNCA CORTA UM TRECHO PELA METADE
# ==========================================================================
def gate_G4():
    print("\n[G4] o corte e por TRECHO INTEIRO -- nunca no meio de um")
    graph = _motor()
    sep = graph.SEPARADOR_DE_TRECHOS

    # Tetos variados, inclusive nos limiares exatos entre trechos.
    conteudo, trechos = conteudo_recuperado(40, 1000)
    tamanhos = [len(t) for t in trechos]
    limiar2 = tamanhos[0] + len(sep) + tamanhos[1]          # exatamente 2 trechos
    for teto in (1, 500, limiar2 - 1, limiar2, limiar2 + 1, 5000, 20000, 10 ** 9):
        texto, meta = graph.montar_bloco_recuperado(conteudo, PERGUNTA, teto=teto)
        corpo = texto.split("=== 📚 CONTEXTO RECUPERADO DA BASE DE CONHECIMENTO ===\n", 1)[-1]
        corpo = corpo.split("\n=== FIM DO CONTEXTO RECUPERADO ===", 1)[0]
        entraram = meta["trechos_no_bloco"]
        inteiros = all(t in corpo for t in trechos[:entraram])
        check("[G4] teto=%d: os %d trechos que entraram estao INTEIROS"
              % (teto, entraram), inteiros)
        check("[G4] teto=%d: o trecho seguinte NAO entrou nem pela metade" % teto,
              entraram >= len(trechos) or trechos[entraram][:200] not in corpo)
        check("[G4] teto=%d: pelo menos UM trecho entra (bloco vazio seria pior)"
              % teto, entraram >= 1, "meta=%r" % (meta,))

    # 🔴 O caso patologico: UM trecho sozinho maior que o teto.
    unico, _ = conteudo_recuperado(1, 5000)
    texto, meta = graph.montar_bloco_recuperado(unico, PERGUNTA, teto=10)
    check("[G4] trecho unico maior que o teto entra INTEIRO (nunca pela metade)",
          meta["trechos_no_bloco"] == 1 and unico in texto,
          "meta=%r" % (meta,))
    check("[G4] CONTROLE: teto gigante nao corta nada",
          graph.montar_bloco_recuperado(conteudo, PERGUNTA, teto=10 ** 9)[1]
          ["trechos_no_bloco"] == len(trechos))


# ==========================================================================
# G5 -- QUEM MONTA O PROMPT DE PRODUCAO CHAMA ESTE MOTOR
#
# 🔴 CLAUDE.md 9.4: sem este gate, G1..G4 provariam uma funcao que ninguem usa.
# O alvo e o `_build_initial_state` de `app/agents/graph.py` -- por AST, nao por
# string solta: o que se afirma e que a CHAMADA esta la, e que o bloco cru nao
# voltou por tras dela.
# ==========================================================================
def gate_G5():
    print("\n[G5] o `dynamic_context` de PRODUCAO e montado por este motor")
    fonte = _ler(os.path.join(RAIZ, "app", "agents", "graph.py"))
    arvore = ast.parse(fonte)

    alvo = None
    for no in ast.walk(arvore):
        if isinstance(no, (ast.AsyncFunctionDef, ast.FunctionDef)) \
                and no.name == "_build_initial_state":
            alvo = no
            break
    if not check("[G5] `_build_initial_state` existe em graph.py", alvo is not None):
        return

    chamadas = [n for n in ast.walk(alvo)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "montar_bloco_recuperado"]
    check("[G5] ele CHAMA `montar_bloco_recuperado` (e nao concatena sozinho)",
          len(chamadas) == 1, "chamadas=%d" % len(chamadas))

    corpo_da_funcao = ast.get_source_segment(fonte, alvo) or ""
    literais_do_marcador = corpo_da_funcao.count(
        "=== 📚 CONTEXTO RECUPERADO DA BASE DE CONHECIMENTO ===")
    check("[G5] o marcador do bloco NAO e escrito dentro do chamador "
          "(so o motor o escreve)", literais_do_marcador == 0,
          "ocorrencias no corpo de _build_initial_state: %d" % literais_do_marcador)

    # CONTROLE: o motor existe e e IMPORTAVEL -- um gate de AST que passasse
    # sobre um arquivo que nao importa nao provaria nada.
    graph = _motor()
    check("[G5] CONTROLE: o motor e importavel e exporta as duas pecas",
          callable(getattr(graph, "montar_bloco_recuperado", None))
          and isinstance(getattr(graph, "TETO_DO_CONTEXTO_RECUPERADO_CHARS", None), int))

    # 🔴 E o rastro chega ao turno: a meta e posta no estado devolvido.
    check("[G5] a medida do bloco entra no estado (`rag_bloco`) para o "
          "`payload.turn`", '"rag_bloco": rag_bloco_meta' in fonte)
    check("[G5] e sai no evento `final` do projetor (`rag_chunks`/`rag_chars`)",
          "rag_chunks=(_meta_rag" in fonte and "rag_chars=(" in fonte)


GATES = {"G1": gate_G1, "G2": gate_G2, "G3": gate_G3, "G4": gate_G4, "G5": gate_G5}


# ==========================================================================
# AS MUTACOES -- (id, arquivo, de, para, gate)
# ==========================================================================
MUTACOES = [
    ("M1", "app/agents/graph.py",
     '        partes.append(\n'
     '            "\\n\\nPERGUNTA ATUAL DO USUÁRIO (repetida porque o bloco acima é "\n'
     '            "longo):\\n%s" % pergunta.strip())',
     '        pass',
     "G1"),
    ("M2", "app/agents/graph.py",
     '    escolhidos = []\n'
     '    tamanho = 0\n'
     '    for trecho in trechos:\n'
     '        custo = len(trecho) + (len(SEPARADOR_DE_TRECHOS) if escolhidos else 0)\n'
     '        if escolhidos and tamanho + custo > teto:\n'
     '            break\n'
     '        escolhidos.append(trecho)\n'
     '        tamanho += custo\n'
     '\n'
     '    corpo = SEPARADOR_DE_TRECHOS.join(escolhidos)\n'
     '    de_fora = total - len(escolhidos)',
     '    corpo = conteudo[:teto]\n'
     '    escolhidos = trechos\n'
     '    de_fora = 0',
     "G2"),
    ("M3", "app/agents/graph.py",
     '        _bloco_rag, rag_bloco_meta = montar_bloco_recuperado(\n'
     '            rag_prefetch_content, user_message)\n'
     '        dynamic_context += _bloco_rag',
     '        dynamic_context += (\n'
     '            "\\n\\n=== 📚 CONTEXTO RECUPERADO DA BASE DE CONHECIMENTO ===\\n"\n'
     '            + rag_prefetch_content\n'
     '            + "\\n=== FIM DO CONTEXTO RECUPERADO ===\\n")',
     "G5"),
]


def rodar_mutacoes(filtro=None):
    print("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO; a arvore parada")
    vermelhas = verdes = 0
    for mid, rel, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, rel)
        original = _ler(caminho)
        if de not in original:
            check("%s: o trecho a mutar EXISTE em %s" % (mid, rel), False,
                  "ancora ausente: %r" % de[:80])
            verdes += 1
            continue
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak").name
        shutil.copyfile(caminho, backup)
        try:
            with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
                fh.write(original.replace(de, para, 1))
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--so", gate],
                cwd=RAIZ, capture_output=True, text=True, timeout=600,
                env={**os.environ, "PYTHONIOENCODING": "utf-8",
                     "PYTHONDONTWRITEBYTECODE": "1"})
            falhas = [l.strip() for l in (r.stdout or "").splitlines()
                      if "[FALHOU]" in l]
            if r.returncode != 0 and falhas:
                vermelhas += 1
                print("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:160]))
            else:
                verdes += 1
                print("  [FALHOU] %s NAO deixou %s vermelho (rc=%s)\n%s"
                      % (mid, gate, r.returncode, (r.stdout or r.stderr)[-1500:]))
        finally:
            shutil.copyfile(backup, caminho)   # 🔴 restaura por COPIA, nunca git checkout
            os.unlink(backup)
            assert _ler(caminho) == original, "restauracao falhou em " + rel
    print("\n  PLACAR DAS MUTACOES: %d vermelhas · %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M") else None
        sys.exit(0 if rodar_mutacoes(filtro) else 1)
    so = args[args.index("--so") + 1] if "--so" in args else None
    print("=" * 74)
    print("  M-E1 -- A PERGUNTA SOBREVIVE AO BLOCO (SPEC-EXTRA-001.1 BLOCO E)")
    print("=" * 74)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            check("%s roda sem excecao" % gid, False,
                  "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()[-700:]))
    print("\n" + "=" * 74)
    print("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
    print("=" * 74)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
