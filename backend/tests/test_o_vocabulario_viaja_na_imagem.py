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

import ast
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
    # ⚠️ `encoding="utf-8"` explícito, e não o padrão da máquina: 📊 19/09/2026,
    # no Windows, `text=True` sozinho decodifica a saída em cp1252 e a linha
    # `catálogo AUSENTE` chega aqui como `catÃ¡logo AUSENTE`. Um guarda que
    # procura a frase que o motor escreveu ficaria vermelho pelo motivo errado
    # — e a tentação seguinte seria afrouxar a asserção para ASCII, que é
    # deixar de medir a mensagem real (CLAUDE.md §9.4: o dialeto da ferramenta
    # muda o que o padrão casa).
    r = subprocess.run([sys.executable, "-c", programa], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       cwd=copia, env=_ambiente_do_conteiner())
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

# ---------------------------------------------------------------------------
print("\n[6] 🔴 A-bis — os CATÁLOGOS SUSEP também viajam na imagem")
# SPEC-EXTRA-001.5.1, unidade A-bis (emenda E3). O MESMO defeito do vocabulário,
# um andar adiante e SEM 500 nenhum para denunciá-lo:
#
# 📊 19/09/2026, nesta mesma cópia, com o código de `2b26bab`:
#     WARNING [SES] mapa de seguradoras ausente (FileNotFoundError)
#     WARNING [SES] mapa de siglas ausente (FileNotFoundError)
#     WARNING [SES] mapa de ramos ausente (FileNotFoundError)
#     seguradoras=0 siglas=0 ramos=0
#     ITAU: UNKNOWN          <- devia ser `porto`
#
# `familia_de_acionamento` está no CAMINHO VIVO do acionamento
# (`infocap_tool.py:856` → `_linha_da_familia_de_acionamento`): com o mapa vazio,
# o corretor deixa de ler *"Itaú aciona pelo corredor da Porto"* e ninguém vê
# erro nenhum — nem 500, nem exceção, nem linha vermelha. Degrada em silêncio, e
# é por isso que este guarda não pergunta "importou?", pergunta o VALOR.
CATALOGOS = ("seguradora-coenti.json", "ramo-cogrupo.json")

PROGRAMA_DOS_CATALOGOS = (
    "import logging, sys\n"
    # O log vai para a SAÍDA PADRÃO de propósito, como no ELO acima: a linha
    # `[SES] catálogo AUSENTE` é a única denúncia que existe, e um guarda que
    # não a lê não prova que ela aparece quando tem de aparecer.
    "logging.basicConfig(stream=sys.stdout, level=logging.WARNING, force=True)\n"
    "from app.providers.susep_ses_provider import (familia_de_acionamento,\n"
    "    mapa_de_seguradoras, mapa_de_siglas, mapa_de_ramos)\n"
    "print('MAPAS: seguradoras=%d siglas=%d ramos=%d' % (len(mapa_de_seguradoras()),\n"
    "      len(mapa_de_siglas()), len(mapa_de_ramos())))\n"
    "print('ITAU:', familia_de_acionamento('itau'))\n"
)

for _nome in CATALOGOS:
    _v = subprocess.run(["git", "ls-files", "--", "backend/app/data/" + _nome],
                        capture_output=True, text=True, cwd=REPO)
    checar(bool((_v.stdout or "").strip()),
           "🔴 `git ls-files backend/app/data/%s` devolve o arquivo" % _nome,
           repr((_v.stdout or "").strip() or (_v.stderr or "")[-200:]))

_copia2 = tempfile.mkdtemp(prefix="imagem_com_catalogos_")
try:
    shutil.copytree(os.path.join(RAIZ, "app"), os.path.join(_copia2, "app"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    saida_cat = _rodar_na_copia(_copia2, PROGRAMA_DOS_CATALOGOS)
    linhas_cat = [l.strip() for l in saida_cat.splitlines()]
    mapas = next((l for l in linhas_cat if l.startswith("MAPAS:")), "")
    numeros = {}
    for parte in mapas.replace("MAPAS:", "").split():
        if "=" in parte:
            chave, valor = parte.split("=", 1)
            numeros[chave] = int(valor) if valor.isdigit() else -1
    checar(all(numeros.get(c, 0) > 0 for c in ("seguradoras", "siglas", "ramos")),
           "🔴 na cópia SEM `docs/`, os TRÊS mapas SES têm entradas > 0 "
           "(antes: seguradoras=0 siglas=0 ramos=0)",
           mapas or saida_cat[-300:])
    checar(any(l == "ITAU: porto" for l in linhas_cat),
           "🔴 O ELO do A-bis: `familia_de_acionamento('itau')` → `porto` na "
           "árvore do contêiner (antes devolvia `UNKNOWN`, sem erro nenhum)",
           (linhas_cat[-1] if linhas_cat else "")[:200])
    checar("[SES]" not in saida_cat,
           "e NENHUMA linha `[SES] … ausente` sobra no log",
           saida_cat[-300:])

    print("\n[7] 🔴 CONTROLE do A-bis — o catálogo apagado do pacote")
    # ⚠️ Mutado na CÓPIA e restaurado por CÓPIA (protocolo §10). A árvore de
    # trabalho não é tocada em momento nenhum deste bloco.
    _alvo2 = os.path.join(_copia2, "app", "data", "seguradora-coenti.json")
    _guardado2 = _alvo2 + ".guardado"
    checar(os.path.isfile(_alvo2),
           "o catálogo de seguradoras está na cópia (há o que apagar)", _alvo2)
    if os.path.isfile(_alvo2):
        shutil.copy2(_alvo2, _guardado2)
        os.remove(_alvo2)
        saida_sem_cat = _rodar_na_copia(_copia2, PROGRAMA_DOS_CATALOGOS)
        checar("ITAU: UNKNOWN" in saida_sem_cat,
               "🔴 CONTROLE: sem o JSON no pacote, `itau` volta a `UNKNOWN` — "
               "este guarda CONSEGUE ficar vermelho",
               saida_sem_cat[-300:])
        checar("catálogo AUSENTE" in saida_sem_cat and "ERROR" in saida_sem_cat,
               "🔴 e a falta GRITA em ERROR nomeando a seção — era `WARNING` com "
               "mapa vazio, que é como isso durou sem ninguém ver",
               saida_sem_cat[-400:])
        shutil.copy2(_guardado2, _alvo2)

    print("\n[8] o PONTEIRO de `docs/` nunca é carregado como catálogo")
    # A mesma porta que o [5] fecha para o vocabulário: se um dia o resolvedor
    # pegar o ponteiro, a seção vem vazia — e vazio tem de gritar, nunca virar
    # um silencioso "nenhuma seguradora casou".
    _ponteiro = os.path.join(_copia2, "ponteiro.json")
    with open(_ponteiro, "w", encoding="utf-8") as fh:
        json.dump({"_mora_agora_em": "backend/app/data/seguradora-coenti.json"}, fh)
    _prog_ponteiro = (
        "import logging, sys\n"
        "logging.basicConfig(stream=sys.stdout, level=logging.WARNING, force=True)\n"
        "from app.providers import susep_ses_provider as S\n"
        "print('SECAO:', len(S._secao_do_catalogo(%r, 'seguradoras')))\n" % _ponteiro
    )
    saida_ponteiro = _rodar_na_copia(_copia2, _prog_ponteiro)
    checar("SECAO: 0" in saida_ponteiro and "SEM DADO" in saida_ponteiro,
           "🔴 um ponteiro (arquivo sem a seção) é recusado com ERROR `catálogo "
           "SEM DADO` — nunca carregado vazio em silêncio",
           saida_ponteiro[-300:])
    _prog_controle = (
        "from app.providers import susep_ses_provider as S\n"
        "print('SECAO:', len(S._secao_do_catalogo(S.CAMINHO_DO_MAPA, 'seguradoras')))\n"
    )
    saida_controle = _rodar_na_copia(_copia2, _prog_controle)
    checar("SECAO:" in saida_controle and "SECAO: 0" not in saida_controle,
           "🔴 CONTROLE: o MESMO leitor, no catálogo de verdade, CARREGA — a "
           "recusa acima é pelo CONTEÚDO, não pelo leitor",
           saida_controle[-200:])
finally:
    shutil.rmtree(_copia2, ignore_errors=True)

# ---------------------------------------------------------------------------
print("\n[9] 🔴 A-ter — o CENSO DO PROVIDER também viaja na imagem")
# SPEC-EXTRA-001.5.1, unidade A-ter. A TERCEIRA reincidência do mesmo defeito na
# mesma SPEC, e a mais silenciosa das três:
#
# 📊 19/09/2026, nesta mesma cópia, com o código de `b1b9038`:
#     DIR: <tmp>\docs\canon\providers      ISDIR: False
#     ILEGIVEL: ''                          <- nem fail-closed: vazio
#     CAPS: 0                               <- na árvore: 19
#
# `carregar_manifesto("infocap")` devolvia um manifesto VAZIO, e manifesto vazio
# responde `UNKNOWN` a TODA capacidade, com a evidência "capacidade fora do
# censo: não verificada" — indistinguível, para quem lê o relatório do Pulso
# 360, de "medimos e não sabemos". Sem 500, sem exceção, sem linha vermelha.
CENSO = ("infocap-capability-manifest.json", "infocap-schema-fingerprints.json",
         "producer-roles.resulta.json")

PROGRAMA_DO_CENSO = (
    "import logging, os, sys\n"
    "logging.basicConfig(stream=sys.stdout, level=logging.WARNING, force=True)\n"
    "from app.comercial import manifesto\n"
    "from app.agents.tools import executive_intelligence as EI\n"
    "manifesto.esquecer_censo()\n"
    "m = manifesto.carregar_manifesto('infocap')\n"
    "print('DIR_EXISTE:', os.path.isdir(manifesto.DIRETORIO_DO_CENSO))\n"
    "print('CAPS:', len(m.capacidades))\n"
    "print('FINGERPRINTS:', len(m.fingerprints_do_censo))\n"
    "print('MAPA_EXISTE:', os.path.isfile(EI._arquivo_de_papeis('resulta')))\n"
)

for _nome in CENSO:
    _v = subprocess.run(
        ["git", "ls-files", "--", "backend/app/data/providers/infocap/" + _nome],
        capture_output=True, text=True, cwd=REPO)
    checar(bool((_v.stdout or "").strip()),
           "🔴 `git ls-files backend/app/data/providers/infocap/%s` devolve o "
           "arquivo" % _nome,
           repr((_v.stdout or "").strip() or (_v.stderr or "")[-200:]))

_copia3 = tempfile.mkdtemp(prefix="imagem_com_censo_")
try:
    shutil.copytree(os.path.join(RAIZ, "app"), os.path.join(_copia3, "app"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    saida_censo = _rodar_na_copia(_copia3, PROGRAMA_DO_CENSO)
    linhas_censo = [l.strip() for l in saida_censo.splitlines()]

    def _numero(prefixo):
        for l in linhas_censo:
            if l.startswith(prefixo):
                bruto = l[len(prefixo):].strip()
                return int(bruto) if bruto.isdigit() else -1
        return -1

    checar("DIR_EXISTE: True" in linhas_censo,
           "🔴 na cópia SEM `docs/`, o diretório do censo EXISTE "
           "(antes: `ISDIR: False`)", saida_censo[-300:])
    checar(_numero("CAPS:") == 19,
           "🔴 O ELO do A-ter: `carregar_manifesto('infocap')` devolve 19 "
           "capacidades na árvore do contêiner (antes devolvia 0, em silêncio)",
           saida_censo[-300:])
    checar(_numero("FINGERPRINTS:") > 0,
           "e os fingerprints de rota também chegam — é deles que sai o drift",
           saida_censo[-300:])
    checar("MAPA_EXISTE: True" in linhas_censo,
           "🔴 e o mapa de produtor (`producer-roles.resulta.json`) é ENCONTRADO "
           "pelo resolvedor — antes o caminho nem existia", saida_censo[-300:])
    checar("[CENSO]" not in saida_censo,
           "e NENHUMA linha `[CENSO] … AUSENTE` sobra no log", saida_censo[-300:])

    print("\n[9b] 🔴 CONTROLE do A-ter — o censo apagado do pacote")
    # ⚠️ Mutado na CÓPIA e restaurado por cópia (protocolo §10).
    _alvo3 = os.path.join(_copia3, "app", "data", "providers", "infocap",
                          "infocap-capability-manifest.json")
    checar(os.path.isfile(_alvo3),
           "o manifesto do censo está na cópia (há o que apagar)", _alvo3)
    if os.path.isfile(_alvo3):
        _guardado3 = _alvo3 + ".guardado"
        shutil.copy2(_alvo3, _guardado3)
        os.remove(_alvo3)
        saida_sem_censo = _rodar_na_copia(_copia3, PROGRAMA_DO_CENSO)
        checar("CAPS: 0" in saida_sem_censo,
               "🔴 CONTROLE: sem o JSON no pacote, as capacidades voltam a ZERO "
               "— este guarda CONSEGUE ficar vermelho", saida_sem_censo[-300:])
        checar("arquivo AUSENTE" in saida_sem_censo and "ERROR" in saida_sem_censo,
               "🔴 e a falta GRITA em ERROR nomeando o arquivo — era um "
               "`return {}` mudo, que é como isso durou sem ninguém ver",
               saida_sem_censo[-400:])
        shutil.copy2(_guardado3, _alvo3)

    print("\n[9c] o PONTEIRO de `docs/` nunca é carregado como censo")
    _ponteiro3 = os.path.join(_copia3, "censo_ponteiro.json")
    with open(_ponteiro3, "w", encoding="utf-8") as fh:
        json.dump({"_mora_agora_em": "backend/app/data/providers/infocap/"}, fh)
    _prog_ponteiro3 = (
        "import logging, sys\n"
        "logging.basicConfig(stream=sys.stdout, level=logging.WARNING, force=True)\n"
        "from app.comercial import manifesto\n"
        "d = manifesto._ler_json(%r, secao='capabilities')\n"
        "print('SECAO:', len(d.get('capabilities') or {}))\n" % _ponteiro3
    )
    saida_p3 = _rodar_na_copia(_copia3, _prog_ponteiro3)
    checar("SECAO: 0" in saida_p3 and "SEM DADO" in saida_p3,
           "🔴 um ponteiro (arquivo sem `capabilities`) é recusado com ERROR "
           "`arquivo SEM DADO` — nunca carregado vazio em silêncio",
           saida_p3[-300:])
    _prog_controle3 = (
        "from app.comercial import manifesto\n"
        "c = manifesto.caminho_do_censo('infocap', 'infocap-capability-manifest.json')\n"
        "d = manifesto._ler_json(c, secao='capabilities')\n"
        "print('SECAO:', len(d.get('capabilities') or {}))\n"
    )
    saida_c3 = _rodar_na_copia(_copia3, _prog_controle3)
    checar("SECAO:" in saida_c3 and "SECAO: 0" not in saida_c3,
           "🔴 CONTROLE: o MESMO leitor, no censo de verdade, CARREGA — a "
           "recusa acima é pelo CONTEÚDO, não pelo leitor", saida_c3[-200:])
finally:
    shutil.rmtree(_copia3, ignore_errors=True)

# ---------------------------------------------------------------------------
print("\n[10] 🔴 O GUARDA GENÉRICO — para que não exista uma QUARTA reincidência")
# 📊 Três vezes na MESMA SPEC, e sempre o mesmo defeito: dado de RUNTIME morando
# em `docs/`, que não entra na imagem.
#
#     fatia 1   `servicos-de-assistencia.json`   a Skill de cobertura desligada
#     fatia 2   os catálogos SUSEP               `familia_de_acionamento` -> UNKNOWN
#     fatia 3   o censo do provider              19 capacidades -> 0
#
# Os blocos [1]-[9] guardam esses TRÊS arquivos pelo nome. Este guarda a FORMA:
# qualquer código de `backend/app/` que **construa ou abra** um caminho com
# `docs/canon`, ou que suba a árvore para fora de `backend/` (`parents[>=3]`,
# `dirname` aninhado 4+ vezes), tem de estar na lista de exceções NOMEADA abaixo.
#
# ⚠️ A leitura é por AST, não por `grep`: comentário e docstring **não contam**,
# só CHAMADA — e a chamada tem de ser de construção de caminho
# (`os.path.join`, `Path`, `open`, `json.load`, `read_text`/`read_bytes`).
# 📊 Sem esse recorte, o varredor acusava dois falsos positivos
# (`comercial/metricas/promover.py:134` e `services/work/metric_proposal.py:323`),
# que citam `docs/canon` dentro de uma MENSAGEM de erro — texto, não caminho.
#
# 🔴 A lista abaixo é de EXCEÇÕES JUSTIFICADAS, e as três são a MESMA: o dado
# mora no pacote e o `docs/` ficou como SEGUNDO lugar, para uma árvore antiga.
EXCECOES_DO_DOCS = {
    "app/services/knowledge/assistance_plans_base.py":
        "fatia 1: o vocabulário mora em `app/data/`; `docs/` é o 2º candidato",
    "app/providers/susep_ses_provider.py":
        "fatia 2: os catálogos SUSEP moram em `app/data/`; `docs/` é o 2º lugar",
    "app/comercial/manifesto.py":
        "fatia 3 (A-ter): o censo mora em `app/data/providers/`; `docs/` é o 2º",
}
_CONSTRUTORES_DE_CAMINHO = {"join", "Path", "open", "load", "read_text", "read_bytes"}


def _nome_do_call(no):
    alvo = no.func
    if isinstance(alvo, ast.Attribute):
        return alvo.attr
    if isinstance(alvo, ast.Name):
        return alvo.id
    return ""


def _varrer_o_pacote():
    """`{arquivo relativo: [(motivo, linha)]}` — só CHAMADAS, nunca texto."""
    fora = {}
    base = os.path.join(RAIZ, "app")
    for pasta, _dirs, arquivos in os.walk(base):
        if "__pycache__" in pasta:
            continue
        for nome in arquivos:
            if not nome.endswith(".py"):
                continue
            caminho = os.path.join(pasta, nome)
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            try:
                with open(caminho, encoding="utf-8") as fh:
                    arvore = ast.parse(fh.read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for no in ast.walk(arvore):
                if isinstance(no, ast.Call):
                    chamada = _nome_do_call(no)
                    if chamada in _CONSTRUTORES_DE_CAMINHO:
                        textos = [a.value.lower() for a in ast.walk(no)
                                  if isinstance(a, ast.Constant)
                                  and isinstance(a.value, str)]
                        if (("docs" in textos and "canon" in textos)
                                or any("docs/canon" in t or "docs\\canon" in t
                                       for t in textos)):
                            fora.setdefault(rel, []).append(("docs/canon", no.lineno))
                    if chamada == "dirname":
                        profundidade, atual = 1, no
                        while (atual.args and isinstance(atual.args[0], ast.Call)
                               and _nome_do_call(atual.args[0]) == "dirname"):
                            profundidade += 1
                            atual = atual.args[0]
                        if profundidade >= 4:
                            fora.setdefault(rel, []).append(
                                ("dirname x%d" % profundidade, no.lineno))
                if (isinstance(no, ast.Subscript)
                        and isinstance(no.value, ast.Attribute)
                        and no.value.attr == "parents"):
                    indice = no.slice
                    if (isinstance(indice, ast.Constant)
                            and isinstance(indice.value, int) and indice.value >= 3):
                        fora.setdefault(rel, []).append(
                            ("parents[%d]" % indice.value, no.lineno))
    return fora


_fora_da_imagem = _varrer_o_pacote()
_nao_declarados = {k: v for k, v in _fora_da_imagem.items()
                   if k not in EXCECOES_DO_DOCS}
checar(not _nao_declarados,
       "🔴 nenhum código de `backend/app/` sai do pacote para buscar dado sem "
       "estar na lista de exceções (%d na lista)" % len(EXCECOES_DO_DOCS),
       repr(sorted(_nao_declarados.items()))[:600])
checar(len(_fora_da_imagem) == len(EXCECOES_DO_DOCS),
       "🔴 CONTROLE: o varredor ACHA os %d fallbacks conhecidos — ele não "
       "passou por vácuo" % len(EXCECOES_DO_DOCS),
       repr(sorted(_fora_da_imagem)))
_orfas = [k for k in EXCECOES_DO_DOCS if k not in _fora_da_imagem]
checar(not _orfas,
       "e nenhuma exceção sobrou na lista depois que o código mudou — "
       "exceção órfã ensina a confiar numa lista vencida", repr(_orfas))

sys.exit(_fechar())
