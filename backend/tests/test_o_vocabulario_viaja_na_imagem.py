# -*- coding: utf-8 -*-
r"""🔴 O VOCABULÁRIO VIAJA NA IMAGEM — o guarda mais importante da EXTRA-001.5.1.

SPEC-EXTRA-001.5.1 · FATIA 1 (unidade A, D1). CLAUDE.md §9.1, na forma que esta
SPEC acrescenta:

```
"build verde não é prova de que a aplicação sobe"   <- o que a §9.1 já dizia
"teste verde na ÁRVORE não é prova de que roda no CONTÊINER"   <- o que faltava
```

O QUE ACONTECEU, E POR QUE NINGUÉM VIU
======================================
📊 18–19/09/2026, contra a API implantada: `GET /api/assistance-plans/cobertura`
→ **200**; `GET /api/assistance-plans/fila?limite=3` → **500** em 1,4 s.

A causa é uma só: o vocabulário de serviços morava em
`docs/canon/providers/susep/servicos-de-assistencia.json`, e o `backend/Dockerfile`
é `WORKDIR /app` + `COPY . .` **executado de dentro de `backend/`** — a pasta
`docs/` **não entra na imagem**. Os três candidatos do resolvedor antigo
(`AUTOBROKERS_REPO_ROOT`, subir a árvore até achar `docs/canon`, `parents[4]`)
estavam **todos fora da imagem**.

🔴 E o efeito grave não foi o 500: foi o SILÊNCIO. `servico_canonico` é a porta
que reconhece a pergunta de cobertura (`cobertura_e_assistencia.py:499`); ela
levantava `VocabularioNaoEncontrado`, o compositor captura tudo
(`policy_answer_composer.py:576`, `except Exception`) e loga
`Skill de cobertura indisponível` — **a Skill inteira estava desligada em
produção, e o caminho antigo respondia como se nada houvesse**. O juiz e a
confirmação da 001.5 rodaram na árvore de desenvolvimento, onde `docs/` existe.

O QUE ESTE GUARDA FAZ
=====================
```
[1] o arquivo está VERSIONADO no pacote, e nenhum `.dockerignore` o exclui
[2] o resolvedor escolhe o arquivo DE DENTRO do pacote, na árvore normal
[3] numa cópia que reproduz a imagem (só `backend/app`, sem `docs/`, sem `.env`),
    um subprocesso com env MÍNIMO responde `carro_reserva`
[4] CONTROLE — a MESMA cópia com o JSON do pacote apagado: `VocabularioNaoEncontrado`
[5] 🔴 O ELO: na cópia, `compose_policy_answer_with_meta` devolve veredito de
    cobertura; CONTROLE: sem o JSON, devolve `None` (era o estado de produção)
[6] vocabulário SEM serviços é instalação incompleta, e grita
```

⚠️ **Env mínimo, valores de mentira.** `app/services/__init__.py` importa o
pacote inteiro, e `app/core/config.py` exige seis variáveis sem padrão
(`grep -n "^    [A-Z_]*: str$" app/core/config.py`): `SUPABASE_URL`,
`SUPABASE_KEY`, `OPENAI_API_KEY`, `ENCRYPTION_KEY`, `MINIO_ROOT_USER`,
`MINIO_ROOT_PASSWORD`. O subprocesso recebe **dummies declarados aqui** e um
ambiente montado do zero — nunca `os.environ`, que poderia carregar os reais de
um `.env` já lido. Sem isso o subprocesso falharia no `pydantic` ANTES de chegar
ao vocabulário, e o guarda ficaria vermelho pelo motivo errado.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)

from app.services.knowledge import assistance_plans_base as B  # noqa: E402

OK = FAIL = 0

#: O caminho do vocabulário DENTRO do pacote — o que entra no `COPY . .`.
NO_PACOTE = os.path.join("app", "data", "servicos-de-assistencia.json")

#: ⛔ Mentiras declaradas. Nenhuma tem relação com valor real de produção.
ENV_DE_MENTIRA = {
    "SUPABASE_URL": "https://exemplo.invalido",
    "SUPABASE_KEY": "chave-de-mentira",
    "OPENAI_API_KEY": "chave-de-mentira",
    "ENCRYPTION_KEY": "chave-de-mentira",
    "MINIO_ROOT_USER": "mentira",
    "MINIO_ROOT_PASSWORD": "mentira",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _fechar() -> int:
    print()
    print("=" * 74)
    print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
    print("=" * 74)
    return 1 if FAIL else 0


def _ambiente_do_conteiner() -> dict:
    """Um ambiente montado do ZERO. ⛔ `os.environ` não entra."""
    fora = dict(ENV_DE_MENTIRA)
    # Só o que o interpretador precisa para subir no Windows/Linux.
    # ⚠️ `APPDATA` não é conveniência: no Windows o *user site-packages* mora em
    # `%APPDATA%\Python\PythonXY\site-packages`, e sem ele o subprocesso perde
    # pacotes instalados ali (📊 19/09/2026: `ModuleNotFoundError: No module
    # named 'PIL'`, vindo de `fastembed`) — o guarda ficaria vermelho pelo
    # motivo errado, que é o defeito que o §9.3 do CLAUDE.md manda evitar.
    for nome in ("PATH", "SystemRoot", "SYSTEMROOT", "COMSPEC", "PATHEXT",
                 "TEMP", "TMP", "APPDATA", "LOCALAPPDATA", "USERPROFILE",
                 "HOME", "LANG"):
        valor = os.environ.get(nome)
        if valor:
            fora[nome] = valor
    return fora


def _rodar_na_copia(copia: str, programa: str) -> str:
    r = subprocess.run([sys.executable, "-c", programa], capture_output=True,
                       text=True, cwd=copia, env=_ambiente_do_conteiner())
    saida = (r.stdout or "").strip()
    if not saida:
        saida = "SEM STDOUT | " + (r.stderr or "")[-1200:]
    return saida


# ---------------------------------------------------------------------------
print("\n[1] o vocabulário está VERSIONADO dentro do pacote, e nada o exclui")
versionado = subprocess.run(
    ["git", "ls-files", "--", "backend/" + NO_PACOTE.replace(os.sep, "/")],
    capture_output=True, text=True, cwd=REPO)
checar(bool((versionado.stdout or "").strip()),
       "🔴 `git ls-files backend/app/data/servicos-de-assistencia.json` devolve o arquivo",
       repr((versionado.stdout or "").strip() or (versionado.stderr or "")[-200:]))

# ⚠️ Não existe `.dockerignore` hoje (📊 19/09/2026, `ls backend/.dockerignore`
# e `ls .dockerignore`: ausentes nos dois). O guarda não exige que exista — exige
# que, SE existir, ele não apague o vocabulário da imagem. Um `.dockerignore`
# criado amanhã com `*.json` ou `app/data` desligaria o produto de novo, em
# silêncio, e sem esta linha ninguém saberia por quê.
_ignores = [os.path.join(RAIZ, ".dockerignore"), os.path.join(REPO, ".dockerignore")]
_padroes_proibidos = ("*.json", "**/*.json", "app/data", "app/data/", "data/",
                      "app/data/*", "servicos-de-assistencia.json")
_achados = []
for caminho in _ignores:
    if not os.path.isfile(caminho):
        continue
    with open(caminho, "r", encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            limpa = linha.strip()
            if limpa and not limpa.startswith("#") and limpa in _padroes_proibidos:
                _achados.append((os.path.basename(caminho), limpa))
checar(not _achados,
       "nenhum `.dockerignore` exclui o vocabulário do pacote"
       + (" (não há `.dockerignore` no repositório)" if not any(
           os.path.isfile(c) for c in _ignores) else ""),
       repr(_achados))

# ---------------------------------------------------------------------------
print("\n[2] o resolvedor escolhe o arquivo DE DENTRO do pacote")
escolhido = B.caminho_do_vocabulario()
checar(os.path.normcase(str(escolhido)).endswith(os.path.normcase(NO_PACOTE)),
       "🔴 na árvore normal, `caminho_do_vocabulario()` aponta para `app/data/`",
       str(escolhido))
checar(len(B.servicos_declarados()) > 0 and B.servico_canonico("tem carro reserva?") == "carro_reserva",
       "o motor lê esse arquivo e reconhece 'tem carro reserva?' → `carro_reserva`",
       repr(B.servico_canonico("tem carro reserva?")))

# ---------------------------------------------------------------------------
print("\n[3] a CÓPIA que reproduz a imagem: só `backend/app`, sem `docs/`, sem `.env`")
_copia = tempfile.mkdtemp(prefix="imagem_do_backend_")
try:
    shutil.copytree(os.path.join(RAIZ, "app"), os.path.join(_copia, "app"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    checar(not os.path.isdir(os.path.join(_copia, "docs"))
           and not os.path.isfile(os.path.join(_copia, ".env")),
           "a cópia NÃO tem `docs/` nem `.env` — é o que a imagem tem",
           repr(sorted(os.listdir(_copia))))

    PROGRAMA_DO_SERVICO = (
        "from app.services.knowledge.assistance_plans_base import servico_canonico\n"
        "print('SERVICO:', servico_canonico('tem carro reserva?'))\n"
    )
    saida = _rodar_na_copia(_copia, PROGRAMA_DO_SERVICO)
    checar(saida.splitlines()[-1].strip() == "SERVICO: carro_reserva",
           "🔴 numa árvore SEM `docs/`, a porta da Skill RESPONDE `carro_reserva`",
           saida[-400:])

    # 🔴 O ELO (protocolo §0.3) — B chega em A. A afirmação da SPEC é
    #    "o produto responde 'ainda não sabemos' a tudo PORQUE a Skill nem roda".
    #    Aqui se mede o trecho que ninguém mediu: o compositor, na árvore do
    #    contêiner, com a pergunta real.
    #    ⚠️ A seguradora é SINTÉTICA de propósito: a Skill recusa seguradora fora
    #    do censo ANTES de qualquer consulta ao banco, então este cheque não toca
    #    rede nenhuma. O que ele prova é que a PORTA abriu — `servico` reconhecido
    #    e veredito emitido —, não o conteúdo da base.
    PROGRAMA_DO_ELO = (
        "import json, logging, sys\n"
        # ⚠️ O log vai para a SAÍDA PADRÃO de propósito: a linha
        # `Skill de cobertura indisponível` é a única pista que produção deixou
        # do produto desligado, e um guarda que não a lê não prova que ela some.
        "logging.basicConfig(stream=sys.stdout, level=logging.WARNING, force=True)\n"
        "from app.services.policy_answer_composer import compose_policy_answer_with_meta\n"
        "pack = {'line_kind_detected': 'residencial',"
        " 'product_detected': 'Residencial Total',"
        " 'insurer_detected': 'seguradora_sintetica_de_teste', 'coverages': []}\n"
        "res = {'status': 'found',"
        " 'selected': {'insurer_key': 'seguradora_sintetica_de_teste',"
        " 'product': 'Residencial Total', 'valid_from': '2024-03-01'},"
        " 'policy_evidence_pack': pack}\n"
        "meta = compose_policy_answer_with_meta(question='tem carro reserva?', result=res)\n"
        "c = meta.get('cobertura')\n"
        "print('COBERTURA:', json.dumps(c, ensure_ascii=False, default=str) if c else 'None')\n"
    )
    saida_elo = _rodar_na_copia(_copia, PROGRAMA_DO_ELO)
    ultima = saida_elo.splitlines()[-1].strip()
    veredito = None
    if ultima.startswith("COBERTURA: {"):
        try:
            veredito = json.loads(ultima[len("COBERTURA: "):])
        except Exception:  # noqa: BLE001
            veredito = None
    checar(veredito is not None and veredito.get("servico") == "carro_reserva",
           "🔴 O ELO: na árvore do contêiner, o compositor devolve VEREDITO "
           "(antes do conserto vinha `None`, com a exceção engolida)",
           ultima[:300])
    checar("Skill de cobertura indispon" not in saida_elo,
           "e o log NÃO traz mais `Skill de cobertura indisponível`",
           saida_elo[-300:])

    print("\n[4] 🔴 CONTROLE — a MESMA cópia, sem o JSON do pacote")
    alvo = os.path.join(_copia, NO_PACOTE)
    if not os.path.isfile(alvo):
        # Antes do conserto o arquivo nem existe: o CONTROLE não tem o que
        # apagar, e dizer isso é mais honesto que estourar um `FileNotFoundError`
        # que ninguém liga ao motivo.
        checar(False, "🔴 CONTROLE: sem o JSON no pacote, o subprocesso QUEBRA",
               "o vocabulário ainda NÃO está em `app/data/` — não há o que apagar")
        raise SystemExit(_fechar())
    guardado = alvo + ".guardado"
    shutil.copy2(alvo, guardado)   # restaura por CÓPIA (protocolo §10)
    os.remove(alvo)
    saida_sem = _rodar_na_copia(_copia, PROGRAMA_DO_SERVICO)
    checar("VocabularioNaoEncontrado" in saida_sem and "SERVICO:" not in saida_sem,
           "🔴 CONTROLE: sem o JSON no pacote, o subprocesso QUEBRA com "
           "`VocabularioNaoEncontrado` — este guarda CONSEGUE ficar vermelho",
           saida_sem[-400:])
    checar("servicos-de-assistencia.json" in saida_sem
           and (os.sep in saida_sem or "/" in saida_sem),
           "e o erro NOMEIA os caminhos procurados (não obriga a refazer "
           "`parents[n]` de cabeça)",
           saida_sem[-300:])

    saida_elo_sem = _rodar_na_copia(_copia, PROGRAMA_DO_ELO)
    checar(saida_elo_sem.splitlines()[-1].strip() == "COBERTURA: None",
           "🔴 CONTROLE DO ELO: sem o JSON, o compositor volta a devolver `None` "
           "— era exatamente isto que produção fazia, sem erro visível",
           saida_elo_sem[-300:])
    checar("Skill de cobertura indisponível" in saida_elo_sem
           or "Skill de cobertura indispon" in saida_elo_sem,
           "e o único sinal disso no log é a linha `Skill de cobertura indisponível`",
           saida_elo_sem[-300:])

    shutil.copy2(guardado, alvo)
finally:
    shutil.rmtree(_copia, ignore_errors=True)

# ---------------------------------------------------------------------------
print("\n[5] vocabulário SEM serviços é instalação incompleta — e grita")
# ⚠️ Por que esta linha existe: `docs/canon/providers/susep/servicos-de-assistencia.json`
# deixou de ser dado e virou PONTEIRO (5 linhas dizendo onde o arquivo mora).
# Se um dia o resolvedor escolher o ponteiro, `servicos` vem vazio — e um
# vocabulário vazio faria `servico_canonico` devolver `None` para TUDO, que é
# exatamente o silêncio que esta SPEC existe para matar.
_vazio = tempfile.mkdtemp(prefix="vocab_vazio_")
try:
    falso = os.path.join(_vazio, "servicos-de-assistencia.json")
    with open(falso, "w", encoding="utf-8") as fh:
        json.dump({"_mudou_de_lugar": "backend/app/data/servicos-de-assistencia.json"}, fh)
    try:
        B._VOCABULARIO = None
        os.environ["AUTOBROKERS_REPO_ROOT"] = "nao-usado"
        antes = B._candidatos_do_vocabulario
        B._candidatos_do_vocabulario = lambda: [__import__("pathlib").Path(falso)]
        try:
            B.vocabulario_de_servicos()
            recusou = False
            detalhe = "carregou o ponteiro como se fosse vocabulário"
        except B.VocabularioNaoEncontrado as exc:
            recusou, detalhe = True, str(exc)[:200]
        finally:
            B._candidatos_do_vocabulario = antes
            os.environ.pop("AUTOBROKERS_REPO_ROOT", None)
            B._VOCABULARIO = None
    finally:
        pass
    checar(recusou,
           "🔴 um arquivo sem a chave `servicos` é RECUSADO com "
           "`VocabularioNaoEncontrado` — nunca carregado vazio em silêncio",
           detalhe)
    # 🔴 CONTROLE: o mesmo caminho, com serviços de verdade, CARREGA.
    with open(falso, "w", encoding="utf-8") as fh:
        json.dump({"servicos": {"guincho": {"tipo": "assistencia", "sinonimos": ["reboque"]}}}, fh)
    B._VOCABULARIO = None
    antes = B._candidatos_do_vocabulario
    B._candidatos_do_vocabulario = lambda: [__import__("pathlib").Path(falso)]
    try:
        carregou = "guincho" in (B.vocabulario_de_servicos().get("servicos") or {})
    finally:
        B._candidatos_do_vocabulario = antes
        B._VOCABULARIO = None
    checar(carregou,
           "🔴 CONTROLE: o MESMO caminho, com `servicos` de verdade, CARREGA — "
           "a recusa acima é pelo conteúdo, não pelo caminho")
finally:
    shutil.rmtree(_vazio, ignore_errors=True)

sys.exit(_fechar())
