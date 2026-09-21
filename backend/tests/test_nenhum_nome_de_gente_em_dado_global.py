# -*- coding: utf-8 -*-
r"""N1–N5 — NENHUM NOME DE GENTE DENTRO DE DADO GLOBAL DE PRODUTO.
SPEC-EXTRA-001.8, FATIA 3 (P-E00151-09).

🔴 **O defeito.** 📊 `corridor_playbooks.py:4319` guardava, no campo `notes` de
um passo do corredor residencial, o NOME PRÓPRIO de uma atendente de uma das
corretoras do piloto — copiado da tela medida da URA, que ecoa o nome de quem
opera o canal.

⚠️ `notes` **não é comentário**. Ele é dado, e viaja para dentro do prompt:

```
corridor_playbooks.get_playbook(ref)["ura_steps"][i]["notes"]
   -> insurer_dispatch_service.build_human_phase_messages   (guia do fluxo, :3864)
   -> insurer_dispatch_service, "ONDE O AUTOMÁTICO EMPACOU"  (:3984)
```

E o playbook é **global**: a mesma estrutura serve TODAS as corretoras
(CLAUDE.md §13.9). O nome de uma funcionária de uma delas podia reaparecer numa
resposta gerada para outra.

⛔ **A lista de nomes proibidos não pode morar em claro no repositório** — seria
recriar o vazamento dentro do guarda. Aqui ficam os `sha256` do token
normalizado (minúsculas, sem acento), e a comparação é TOKEN A TOKEN.

Como a lista foi produzida (📊 21/09/2026, de dentro de `backend/`):

```
python -c "import hashlib,unicodedata;t=unicodedata.normalize('NFKD',NOME.lower());\
print(hashlib.sha256(''.join(c for c in t if not unicodedata.combining(c)).encode()).hexdigest())"
```

E o que impede a lista de ser lixo: **N4**. Ele prova que ela reconhece um nome
que ainda existe de verdade no repositório (nas fixtures de teste, que esta
fatia NÃO limpa — P-E00151-09-FIXTURES).

⛔ SEGURANÇA: zero rede, zero banco, zero LLM. Nenhum nome próprio em claro.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_nenhum_nome_de_gente_em_dado_global.py
    ... --so N2   ·   ... --mutar
    python -m pytest tests/test_nenhum_nome_de_gente_em_dado_global.py -q -p no:cacheprovider
"""
from __future__ import annotations

import copy
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

RAIZ = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, RAIZ)

# ---------------------------------------------------------------------------
# A LISTA — só hashes. 📊 Quatro nomes próprios de pessoa medidos em
# `backend/app` e `backend/scripts` em 21/09/2026 (`grep -rn -i <nome>`):
# duas atendentes do piloto e dois nomes que aparecem no material de
# mascaramento de PII. Nenhum deles tem razão para existir em dado global.
# ---------------------------------------------------------------------------
NOMES_PROIBIDOS = {
    "d9873adeb7d30852f8142ad13aad44c8a1db2e7bb95076ab8acdaa4744c1aee0",
    "bd84dc633654d437de72ce67276ae9f9bd702392f7701cef86743dc571fb015a",
    "83e78bb33a170b81326af1f1d89dd2955347b3aa451b3ba59293516691f7fb0b",
    "c83b66c7d22ad758dbb727191e0501616734201e4a9274698e5d1e7ef45c3006",
}

#: 🔴 O SENTINELA. Nome SINTÉTICO, em claro de propósito: é com ele que a
#: mutação reintroduz "um nome" no `notes` do fonte. O nome de verdade não pode
#: ser escrito aqui (era o defeito), então quem faz o papel dele é este — e o
#: mecanismo exercitado é exatamente o mesmo: token → normaliza → sha256 → lista.
SENTINELA = "Nomesentinela"

PASS = 0
FAIL = 0


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        print(texto.encode("ascii", "replace").decode("ascii"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:900] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O VARREDOR
# ===========================================================================
_TOKEN = re.compile(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ]+")


def normalizar(token: str) -> str:
    t = unicodedata.normalize("NFKD", token.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def impressao(token: str) -> str:
    return hashlib.sha256(normalizar(token).encode()).hexdigest()


def proibidos_no_texto(texto: str, lista) -> list:
    """Os tokens do texto cuja impressão está na lista. Nunca devolve o token."""
    achados = []
    for token in _TOKEN.split(str(texto)):
        if len(token) < 3:
            continue
        if impressao(token) in lista:
            achados.append(impressao(token)[:12])
    return achados


def textos_do_playbook(objeto, caminho="") -> list:
    """Todo texto que um playbook carrega, com o caminho até ele.

    🔴 TUDO, não só `notes`: âncora, resposta, instrução ao cliente, gatilho de
    handoff, molde de mensagem. Um nome próprio não tem lugar em nenhum deles —
    e se um dia precisar ter (texto REAL de tela de seguradora, não de
    funcionário de corretora), a exceção vai ter de ser escrita aqui, ao lado
    da razão. É a mesma regra de `ABERTAS_COM_RAZAO` no varredor de rotas.
    """
    saida = []
    if isinstance(objeto, str):
        saida.append((caminho, objeto))
    elif isinstance(objeto, dict):
        for chave, valor in objeto.items():
            saida.extend(textos_do_playbook(valor, "%s.%s" % (caminho, chave)))
    elif isinstance(objeto, (list, tuple)):
        for i, valor in enumerate(objeto):
            saida.extend(textos_do_playbook(valor, "%s[%d]" % (caminho, i)))
    return saida


def varrer(playbooks: dict, lista) -> list:
    """Os achados: (playbook, caminho, prefixos de hash). Nunca o nome."""
    achados = []
    for ref, pb in playbooks.items():
        for caminho, texto in textos_do_playbook(pb, ref):
            marcas = proibidos_no_texto(texto, lista)
            if marcas:
                achados.append((ref, caminho, marcas))
    return achados


# ===========================================================================
# O MOTOR — os playbooks pelos acessores REAIS do produto
# ===========================================================================
import app.services.corridor_playbooks as CP  # noqa: E402


def carregar():
    return {ref: CP.get_playbook(ref) for ref in CP.list_playbooks()}


# ===========================================================================
# N1 — o motor carrega mesmo (sem isto, tudo abaixo é varrer o vazio)
# ===========================================================================

def n1():
    _p("\n[N1] o MOTOR entrega os playbooks — o varredor não está lendo o vazio")
    pbs = carregar()
    check("N1.1 `list_playbooks()` devolve corredores", len(pbs) >= 10, len(pbs))
    check("N1.2 e nenhum deles veio vazio",
          all(isinstance(p, dict) and p for p in pbs.values()),
          [r for r, p in pbs.items() if not p])
    textos = [t for pb in pbs.values() for _c, t in textos_do_playbook(pb)]
    check("N1.3 o varredor enxerga os campos textuais (>= 2000 pedaços)",
          len(textos) >= 2000, len(textos))
    tem_notes = [c for pb in pbs.values() for c, _t in textos_do_playbook(pb)
                 if c.endswith(".notes")]
    check("N1.4 e entre eles estão os `notes`, que entram no prompt",
          len(tem_notes) >= 100, len(tem_notes))


# ===========================================================================
# N2 — ZERO nomes próprios nos playbooks
# ===========================================================================

def n2():
    _p("\n[N2] nenhum nome de gente nos dados globais de corredor")
    achados = varrer(carregar(), NOMES_PROIBIDOS | {impressao(SENTINELA)})
    check("N2.1 ZERO nomes próprios em qualquer campo textual dos playbooks",
          achados == [],
          "; ".join("%s%s -> %s" % (r, c, m) for r, c, m in achados[:8]))


# ===========================================================================
# N3 — A LINHA DE CONTROLE: o guarda CONSEGUE ficar vermelho
# ===========================================================================

def n3():
    _p("\n[N3] CONTROLE — o guarda acusa um nome injetado numa CÓPIA EM MEMÓRIA")
    pbs = copy.deepcopy(carregar())
    ref = sorted(pbs)[0]
    passos = pbs[ref].get("ura_steps") or []
    check("N3.0 o corredor escolhido tem passos para contaminar", bool(passos), ref)
    if not passos:
        return
    passos[0]["notes"] = "%s você é a pessoa que está no local?" % SENTINELA

    achados = varrer(pbs, NOMES_PROIBIDOS | {impressao(SENTINELA)})
    check("N3.1 o varredor ACUSA o nome-sentinela injetado", len(achados) == 1, achados)
    check("N3.2 e aponta o campo exato",
          bool(achados) and achados[0][1].endswith(".notes"), achados)
    # 🔴 O PAR: o mesmo texto, com a lista SEM o sentinela, não acusa nada —
    #    senão o guarda estaria acusando qualquer palavra.
    check("N3.3 e com a lista sem o sentinela ele NÃO acusa (não é carimbo)",
          varrer(pbs, NOMES_PROIBIDOS) == [], varrer(pbs, NOMES_PROIBIDOS))
    # 🔴 E a cópia é cópia: o motor de verdade continua limpo.
    check("N3.4 a contaminação ficou na cópia (o motor real segue limpo)",
          varrer(carregar(), NOMES_PROIBIDOS | {impressao(SENTINELA)}) == [])


# ===========================================================================
# N4 — O ELO: a lista de hashes reconhece um nome que EXISTE no repositório
# ===========================================================================
#
# ⚠️ Sem isto, `NOMES_PROIBIDOS` poderia ser quatro hashes de nada, e N2 ficaria
# verde para sempre. As fixtures de teste AINDA carregam o nome (esta fatia não
# as limpa — P-E00151-09-FIXTURES), então elas servem de âncora viva.
#
# 🔴 QUANDO AS FIXTURES FOREM LIMPAS, este gate fica vermelho DE PROPÓSITO: é o
# sinal de que a pendência fechou e a âncora tem de mudar de lugar (CLAUDE.md
# §9.3 — a lição migra, não morre).
FIXTURE_ANCORA = "tests/test_corredor_residencial_yelum.py"


def n4():
    _p("\n[N4] a lista reconhece um nome REAL — ela não é quatro hashes de nada")
    caminho = os.path.join(RAIZ, FIXTURE_ANCORA)
    check("N4.0 a fixture-âncora existe", os.path.exists(caminho), caminho)
    if not os.path.exists(caminho):
        return
    texto = io.open(caminho, encoding="utf-8").read()
    marcas = proibidos_no_texto(texto, NOMES_PROIBIDOS)
    check("N4.1 pelo menos um nome da lista é encontrado na fixture-âncora "
          "(se ficou vermelho, as fixtures foram limpas: mova a âncora)",
          bool(marcas), "0 casamentos em %s" % FIXTURE_ANCORA)
    # CONTROLE: palavras comuns do produto NÃO caem na lista.
    check("N4.2 CONTROLE: `atendente`, `corretora`, `segurado` não estão na lista",
          proibidos_no_texto("atendente corretora segurado guincho", NOMES_PROIBIDOS) == [])


# ===========================================================================
# N5 — O FIO: o `notes` do passo medido CHEGA ao prompt, e chega limpo
# ===========================================================================

def n5():
    _p("\n[N5] o FIO — `notes` -> prompt interno, com o MOTOR real")
    import app.services.insurer_dispatch_service as D

    # ⚠️ São QUATRO passos `pessoa_no_local` (📊 auto e residencial de duas
    #    seguradoras) e DOIS deles têm `notes` vazio. Pegar "o primeiro" fazia
    #    `"" in prompt` — uma afirmação que não pode falhar. O gate roda em
    #    TODOS os que têm `notes`, e conta quantos foram.
    alvos = [(ref, passo)
             for ref in CP.list_playbooks()
             for passo in (CP.get_playbook(ref) or {}).get("ura_steps") or []
             if passo.get("step") == "pessoa_no_local"
             and str(passo.get("notes") or "").strip()]
    check("N5.0 há passo `pessoa_no_local` COM `notes` (>=1) para atravessar",
          len(alvos) >= 1, len(alvos))
    if not alvos:
        return

    for ref, passo in alvos:
        sessao = {
            "playbook_ref": ref,
            "slots": {"telefone_contato": "5500000000000"},
            "captured": {},
            "ultimo_passo_sem_dado": {
                "step": passo["step"],
                "faltou": ["pessoa_no_local"],
                "notes": str(passo.get("notes") or ""),
            },
        }
        prompt = D.build_human_phase_messages(sessao, "Tela qualquer da URA")
        inteiro = prompt["system"] + "\n" + prompt["user"]
        nota = str(passo.get("notes") or "")

        check("N5.1 [%s] o `notes` do passo CHEGA ao prompt (o elo A<-B)" % ref,
              len(nota) >= 20 and nota[:40] in inteiro, inteiro[-1000:])
        check("N5.2 [%s] e o prompt inteiro não carrega nome próprio nenhum" % ref,
              proibidos_no_texto(inteiro, NOMES_PROIBIDOS | {impressao(SENTINELA)}) == [],
              proibidos_no_texto(inteiro, NOMES_PROIBIDOS | {impressao(SENTINELA)}))
        check("N5.3 [%s] CONTROLE: o prompt não veio vazio" % ref,
              len(inteiro) > 500, len(inteiro))


GATES = {"N1": n1, "N2": n2, "N3": n3, "N4": n4, "N5": n5}


# ===========================================================================
# AS MUTAÇÕES — por CÓPIA. A árvore precisa estar parada.
# ===========================================================================
PB = "app/services/corridor_playbooks.py"

MUTACOES = [
    # M-183-N1 — reintroduz UM NOME no `notes` que entra no prompt.
    #            ⚠️ O nome de verdade não pode ser escrito no repositório (era o
    #            defeito); quem faz o papel dele é o SENTINELA, pelo mesmo funil.
    ("M-183-N1", [
        (PB, '"notes": "📊 \'NOME DE QUEM OPERA O CANAL, você é a pessoa que está local "',
         '"notes": "📊 \'%s, você é a pessoa que está local "' % SENTINELA),
    ], "N2"),
    # M-183-N2 — o varredor deixa de olhar `notes` (só olharia âncora e resposta)
    ("M-183-N2", [
        (PB, '"notes": "📊 \'NOME DE QUEM OPERA O CANAL, você é a pessoa que está local "',
         '"notes": "📊 \'%s, você é a pessoa que está local "' % SENTINELA),
    ], "N5"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        cwd=RAIZ, capture_output=True, text=True, timeout=1800,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8",
             "PYTHONDONTWRITEBYTECODE": "1"})


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, edicoes, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        alvos, faltou = [], None
        for relativo, de, para in edicoes:
            caminho = os.path.normpath(os.path.join(RAIZ, relativo))
            original = io.open(caminho, encoding="utf-8").read()
            if de not in original:
                faltou = relativo
                break
            alvos.append((caminho, original, de, para, relativo))
        if faltou:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, faltou))
            verdes += 1
            continue
        base = _rodar(gate)
        backups = []
        for caminho, _o, _d, _pa, _r in alvos:
            b = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0183n").name
            shutil.copyfile(caminho, b)
            backups.append(b)
        try:
            for caminho, original, de, para, _r in alvos:
                io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                    original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:220]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode,
                      (r.stdout or r.stderr)[-900:]))
        finally:
            for (caminho, original, _d, _pa, relativo), b in zip(alvos, backups):
                shutil.copyfile(b, caminho)
                os.unlink(b)
                assert io.open(caminho, encoding="utf-8").read() == original, \
                    "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  N1-N5 -- NENHUM NOME DE GENTE EM DADO GLOBAL DE PRODUTO")
        _p("  (SPEC-EXTRA-001.8, FATIA 3 -- P-E00151-09)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc,
                                  traceback.format_exc()[-1500:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_nenhum_nome_de_gente_em_dado_global():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
