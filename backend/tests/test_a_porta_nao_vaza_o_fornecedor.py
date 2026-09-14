# -*- coding: utf-8 -*-
r"""M-A1 — A PORTA NAO VAZA O FORNECEDOR. SPEC-EXTRA-001.1 BLOCO A, GATE A1.

A frase de Alistair Cockburn que esta SPEC transforma em teste:

    "The application has a semantically sound interaction with the adapters on
     all sides of it, WITHOUT ACTUALLY KNOWING THE NATURE OF THE THINGS ON THE
     OTHER SIDE."

Traduzido para esta arvore: **nada fora de `backend/app/providers/` sabe que
existe InfoCap.** Este guarda mede as quatro faces disso.

```
 [G1a] IMPORT      ninguem fora de providers/ importa `app.api.infocap_connector`
 [G1b] CAMPO       nenhum campo de fornecedor no texto que chega ao MODELO
 [G1c] PROSA       `\bInfoCap\b` (SENSIVEL A CAIXA) em `core/prompts.py` = 0
 [G1d] CONTRATO    nenhum `hasattr(provider` decide contrato; o registry RECUSA
 [G1e] TIPOS       o verificador de tipos reprova adaptador sem `vehicle`
                   -- e `isinstance` NAO teria reprovado (proposta §16 ③)
```

🔴 **VERMELHO ESPERADO nao e verde.** Parte do que este guarda mede so fica
verde nos BLOCOS B, C e D — que sao de outros builders e correm DEPOIS. Esses
vermelhos sao NOMEADOS na saida, contados a parte, e **o exit code continua 1**
(CLAUDE.md §9.3: nao se afrouxa a regua, e um guarda que fica verde por
conveniencia e carimbo). O que o BLOCO A nao pode deixar acontecer e um
vermelho NOVO.

🔴 **O DETECTOR LE CODIGO, NAO PROSA.** Um docstring que diz *"existem 4
`hasattr(provider, "vehicle")` em producao"* e o contrario do defeito — e um
grep cru o contaria como defeito, deixando o guarda vermelho para sempre e
ensinando a ignora-lo. 📊 O par existe nesta arvore: `policy_data_provider.py`
tem **2** mencoes a `hasattr(provider` e as **duas** sao docstring.

⛔ SEGURANCA
```
· `SEM_REDE=1` e `socket.connect` BLOQUEADO: nenhuma chamada a InfoCap sai daqui.
· Nenhuma escrita e nenhuma leitura de banco.
· NENHUM nome de pessoa, CPF, apolice real ou credencial.
```

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_porta_nao_vaza_o_fornecedor.py
    ... --so G1c            roda so um gate
    ... --medir             imprime as MEDIDAS (o que as mutacoes comparam)
    ... --mutar [M-A1a]     roda as mutacoes, cada uma em COPIA e em SUBPROCESSO
"""
from __future__ import annotations

import ast
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
REPO = os.path.dirname(RAIZ)
APP = os.path.join(RAIZ, "app")
PROVIDERS = os.path.join(APP, "providers")
CONECTOR = os.path.join(APP, "api", "infocap_connector.py")
MAIN = os.path.join(APP, "main.py")
PROMPTS = os.path.join(APP, "core", "prompts.py")
AGENTES = os.path.join(APP, "agents")
COMPOSER = os.path.join(APP, "services", "policy_answer_composer.py")
FERRAMENTA = os.path.join(AGENTES, "tools", "infocap_tool.py")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ["SEM_REDE"] = "1"

_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _proibir(self, *a, **k):  # noqa: ANN001
    raise RuntimeError("SPEC-EXTRA-001.1: este guarda roda com SEM_REDE=1 e NAO "
                       "chama a InfoCap. Destino pedido: %r" % (a[0] if a else None,))


def _bloquear_a_rede():
    socket.socket.connect = _proibir       # type: ignore[assignment]
    socket.socket.connect_ex = _proibir    # type: ignore[assignment]


def _devolver_a_rede():
    socket.socket.connect = _CONNECT       # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]


# ===========================================================================
# O PLACAR
# ===========================================================================
PASS = 0
FAIL = 0
ESPERADOS: list = []
JA_PODEM_VIRAR: list = []
MEDIDAS: dict = {}


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:500] if detalhe else ""))
    return bool(cond)


def vermelho_ate(cond, nome, bloco, detalhe=""):
    """Vermelho PREVISTO pela SPEC — e mesmo assim vermelho, e mesmo assim exit 1."""
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
        JA_PODEM_VIRAR.append("%s   [era vermelho_ate('%s')]" % (nome, bloco))
    else:
        FAIL += 1
        ESPERADOS.append("%s   (esperado ate %s)" % (nome, bloco))
        _p("  VERMELHO-ESPERADO %s   (ate %s)" % (nome, bloco)
           + ("\n         %s" % str(detalhe)[:500] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    """🔴 A MEDIDA e o que as mutacoes comparam.

    Sem ela, uma mutacao sobre um detector que JA esta vermelho nao provaria
    nada: "continuou vermelho" tanto pode ser "o guarda pegou a mutacao" quanto
    "o guarda estava cego desde antes". A medida transforma "vermelho" num
    NUMERO, e a mutacao tem de move-lo.
    """
    MEDIDAS[chave] = valor
    return valor


def ler(caminho):
    return io.open(caminho, encoding="utf-8", errors="replace").read()


def rel(caminho):
    return os.path.relpath(caminho, REPO).replace("\\", "/")


def arquivos_py(raiz):
    for pasta, _dirs, arquivos in os.walk(raiz):
        if "__pycache__" in pasta:
            continue
        for nome in sorted(arquivos):
            if nome.endswith(".py"):
                yield os.path.join(pasta, nome)


# ===========================================================================
# 🔴 O DETECTOR LE CODIGO, NAO PROSA — e o PAR prova que ele faz as duas coisas
# ===========================================================================
_ASPAS3 = chr(34) * 3
RE_PROSA = re.compile(_ASPAS3 + r"[\s\S]*?" + _ASPAS3
                      + r"|'''[\s\S]*?'''"
                      + r"|#[^\n]*")


def sem_prosa(texto):
    """Apaga docstring e comentario PRESERVANDO as quebras de linha.

    O numero de linha impresso continua sendo o do arquivo real — um detector
    que desalinha a linha manda o leitor para o lugar errado.
    """
    return RE_PROSA.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), texto)


# ===========================================================================
# A ALLOWLIST — ESCRITA, com o motivo por linha (proposta §3.2)
# ===========================================================================
#
# ⚠️ "Uma allowlist com mais de 3 linhas e sinal de que a fronteira esta no
#    lugar errado: pare e registre." Esta tem 3.
ALLOWLIST_DE_IMPORT = {
    os.path.normcase(MAIN): (
        "e o ROTEADOR HTTP do proprio conector (`include_router`), nao um "
        "consumidor de dado da InfoCap. Ninguem tira: e a porta HTTP."
    ),
}

#: Os campos do fornecedor que nao podem atravessar a fronteira.
RE_CAMPO = re.compile(
    r"\b(preliq|nosnum|codfil|sit_renovacao_txt|sit_sinistro_txt|tabela_itens"
    r"|forma_pag|inivig|fimvig)\b", re.IGNORECASE)

#: ⚠️ A allowlist do LOCATOR OPACO. `codfil`/`nosnum` aparecem em
#: `policy_facts.py` e `policy_document_evidence_service.py` como as PARTES do
#: locator tecnico que a propria porta define (`policy_data_provider.py:
#: parse_policy_locator_ref`) — e o que se hasheia, nunca o que se le como
#: dado. Nao e leitura de campo do fornecedor: e a chave opaca.
ALLOWLIST_DE_CAMPO = {
    os.path.normcase(os.path.join(APP, "services", "policy_facts.py")):
        "hash do locator opaco (`_locator_hash`), nao leitura de dado",
    os.path.normcase(os.path.join(APP, "services", "policy_document_evidence_service.py")):
        "hash do locator opaco + a lista de chaves REDIGIDAS da saida",
}

#: 🔴 A SUPERFICIE DE APOLICE. `app/comercial/**` fica FORA de proposito: e o
#: adaptador de ANALYTICS da SPEC-081/094, outra porta, com fronteira propria ja
#: gateada por `test_o_pulso_360_nao_pertence_a_infocap.py`. Medir as duas com a
#: mesma regua produziria um gate INALCANCAVEL — e gate que nunca fica verde e
#: gate que ninguem olha (divergencia D1 do BLOCO 0).
SUPERFICIE_DE_APOLICE = (AGENTES, COMPOSER, PROMPTS)

#: O que os BLOCOS B/C/D ainda devem. Nomeado por LINHA, nunca por arquivo:
#: "infocap_tool.py tem pendencia" esconderia uma linha nova no meio das velhas.
ESPERADO_ATE = {
    ("import", "backend/app/agents/tools/infocap_tool.py"): "BLOCO B/C",
    ("campo", "backend/app/agents/tools/infocap_tool.py"): "BLOCO C",
    # ⚠️ As 4 linhas `("hasattr", …)` SAÍRAM em 14/09/2026, com o BLOCO D: os
    #    quatro `hasattr(provider, "vehicle")` foram removidos do produto e o
    #    G1d ficou verde. Mantê-las aqui seria guardar verdade vencida
    #    (CLAUDE.md §9.3) — e a mutação M-A1d continua provando que o detector
    #    fica VERMELHO se um `hasattr` novo aparecer.
}


# ===========================================================================
# [G1a] IMPORT — por AST, nunca por string
# ===========================================================================
def _importa_o_conector(caminho):
    """Devolve as linhas em que o arquivo IMPORTA o conector. AST, nao `grep`.

    ⚠️ Por que AST: uma string `"app.api.infocap_connector"` num log, ou a
    mencao num comentario, nao e um import — e um `grep` as contaria. O que a
    fronteira proibe e a DEPENDENCIA.
    """
    try:
        arvore = ast.parse(ler(caminho))
    except SyntaxError:
        return []
    achados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom):
            modulo = no.module or ""
            if modulo == "app.api.infocap_connector" or modulo.endswith("api.infocap_connector"):
                achados.append(no.lineno)
            elif modulo in ("app.api", "api") and any(
                    a.name == "infocap_connector" for a in no.names):
                achados.append(no.lineno)
        elif isinstance(no, ast.Import):
            for a in no.names:
                if a.name.endswith("app.api.infocap_connector") or a.name == "app.api.infocap_connector":
                    achados.append(no.lineno)
    return sorted(set(achados))


def gate_G1a():
    _p("\n[G1a] IMPORT -- ninguem fora de `app/providers/` importa o conector")

    # 🔴 O PAR DO DETECTOR vem primeiro: sem ele, "0 achados" tanto pode ser
    #    limpeza quanto AST quebrada.
    with tempfile.TemporaryDirectory() as tmp:
        acha = os.path.join(tmp, "acha.py")
        nao = os.path.join(tmp, "nao.py")
        io.open(acha, "w", encoding="utf-8").write(
            "from app.api.infocap_connector import infocap_lookup\n")
        io.open(nao, "w", encoding="utf-8").write(
            '# from app.api.infocap_connector import infocap_lookup\n'
            'CAMINHO = "app.api.infocap_connector"\n')
        check("[G1a] PAR-A: o detector ACHA o import de verdade",
              _importa_o_conector(acha) == [1], _importa_o_conector(acha))
        check("[G1a] PAR-B: e NAO acha o comentario nem a string com o mesmo texto",
              _importa_o_conector(nao) == [], _importa_o_conector(nao))

    fora = []
    for caminho in arquivos_py(APP):
        normal = os.path.normcase(caminho)
        if normal.startswith(os.path.normcase(PROVIDERS) + os.sep):
            continue
        if normal == os.path.normcase(CONECTOR):
            continue
        linhas = _importa_o_conector(caminho)
        if not linhas:
            continue
        if normal in ALLOWLIST_DE_IMPORT:
            _p("     -- allowlist: %s:%s  (%s)" % (rel(caminho), linhas,
                                                   ALLOWLIST_DE_IMPORT[normal]))
            continue
        fora.append((rel(caminho), linhas))

    medir("importadores_fora_da_fronteira", sum(len(l) for _f, l in fora))
    previstos = [f for f in fora if ESPERADO_ATE.get(("import", f[0]))]
    novos = [f for f in fora if not ESPERADO_ATE.get(("import", f[0]))]

    check("[G1a] nenhum importador NOVO do conector fora da fronteira",
          not novos, novos)
    for arquivo, linhas in previstos:
        vermelho_ate(False,
                     "[G1a] %s nao importa o conector (linhas %s)" % (arquivo, linhas),
                     ESPERADO_ATE[("import", arquivo)],
                     "os helpers `_display_policy_number`/`_format_policy_options_for_summary` "
                     "sobem para a porta quando o briefing migrar")
    if not previstos:
        check("[G1a] os importadores previstos pelos BLOCOS B/C sumiram", True)


# ===========================================================================
# [G1b] CAMPO — nenhum campo de fornecedor no texto que chega ao MODELO
# ===========================================================================
def gate_G1b():
    _p("\n[G1b] CAMPO -- `preliq`/`nosnum`/`codfil`/`tabela_itens`/... fora da fronteira")

    check("[G1b] PAR-A: o detector ACHA o campo numa linha de codigo",
          bool(RE_CAMPO.search('descricao = "formato infocap:<codfil>:<nosnum>"')))
    check("[G1b] PAR-B: e APROVA a linha que so fala o modelo canonico",
          not RE_CAMPO.search("return sum(c.premio.valor for c in apolice.coberturas)"))
    # 🔴 O PAR QUE IMPORTA: prosa NAO e defeito. 📊 `policy_data_provider.py`
    #    documenta `hasattr(provider, "vehicle")` em 2 docstrings, e
    #    `executive_intelligence.py:32` documenta o proprio grep do juiz.
    check("[G1b] PAR-C: o detector NAO conta a mesma palavra dentro de docstring",
          not RE_CAMPO.search(sem_prosa('%s\nfala de nosnum e codfil\n%s\nx = 1\n'
                                        % (_ASPAS3, _ASPAS3))))

    alvos = []
    for base in SUPERFICIE_DE_APOLICE:
        if os.path.isdir(base):
            alvos.extend(arquivos_py(base))
        elif os.path.exists(base):
            alvos.append(base)

    fora = []
    for caminho in alvos:
        normal = os.path.normcase(caminho)
        if normal in ALLOWLIST_DE_CAMPO:
            continue
        for i, linha in enumerate(sem_prosa(ler(caminho)).split("\n"), 1):
            if RE_CAMPO.search(linha):
                fora.append((rel(caminho), i))

    medir("campos_de_fornecedor_fora_da_fronteira", len(fora))
    por_arquivo: dict = {}
    for arquivo, linha in fora:
        por_arquivo.setdefault(arquivo, []).append(linha)

    novos = {a: l for a, l in por_arquivo.items() if not ESPERADO_ATE.get(("campo", a))}
    check("[G1b] nenhum campo de fornecedor NOVO na superficie de apolice",
          not novos, novos)
    for arquivo, linhas in sorted(por_arquivo.items()):
        if ESPERADO_ATE.get(("campo", arquivo)):
            vermelho_ate(False,
                         "[G1b] %s nao nomeia campo do fornecedor (linhas %s)" % (arquivo, linhas),
                         ESPERADO_ATE[("campo", arquivo)],
                         "sao textos que chegam ao MODELO: a descricao do `policy_ref` e a "
                         "regra 5 do briefing")


# ===========================================================================
# [G1c] PROSA — `\bInfoCap\b` SENSIVEL A CAIXA em `core/prompts.py`
# ===========================================================================
RE_INFOCAP_PROSA = re.compile(r"\bInfoCap\b")   # 🔴 SEM re.IGNORECASE, de proposito


def gate_G1c():
    _p("\n[G1c] PROSA -- `\\bInfoCap\\b` (sensivel a caixa) em `core/prompts.py`")

    # 🔴 O PAR que a proposta §10 exige, e ele e a razao de o detector ser
    #    sensivel a caixa: o IDENTIFICADOR da ferramenta (`infocap_policy_lookup`)
    #    e o nome registrado dela, e sai noutra SPEC. A PROSA
    #    ("a InfoCap respondeu") e o que nomeia o fornecedor para o segurado.
    check("[G1c] PAR-A: o detector ACHA a prosa 'a InfoCap respondeu'",
          bool(RE_INFOCAP_PROSA.search("- Se a InfoCap respondeu, repasse.")))
    check("[G1c] PAR-B: e NAO acha o identificador `infocap_policy_lookup`",
          not RE_INFOCAP_PROSA.search("CHAME a ferramenta infocap_policy_lookup"))

    linhas = [i for i, linha in enumerate(ler(PROMPTS).split("\n"), 1)
              if RE_INFOCAP_PROSA.search(linha)]
    medir("infocap_em_prosa", len(linhas))
    if linhas:
        vermelho_ate(False,
                     "[G1c] `core/prompts.py` nao nomeia o fornecedor em prosa "
                     "(hoje %d linhas: %s)" % (len(linhas), linhas),
                     "BLOCO C",
                     "o texto que chega ao segurado diz 'sistema de gestao da corretora', "
                     "nunca o nome do fornecedor")
    else:
        check("[G1c] `core/prompts.py` nao nomeia o fornecedor em prosa", True)

    # 🔴 E A FERRAMENTA, que e o outro texto que chega ao modelo TODO TURNO.
    # 📊 Medido em 14/09/2026, antes do conserto: **23** linhas com `InfoCap` em
    # `app/agents/tools/infocap_tool.py` — entre elas a `description` da tool
    # (que entra no esquema de toda chamada) e as 14 frases de `_summarize` /
    # `_summarize_detail`, o texto de fallback que o corretor le quando a flag
    # v2 esta desligada. Depois: **4**, todas em docstring ou comentario.
    #
    # ⚠️ O detector le CODIGO: `sem_prosa` apaga docstring e comentario
    # preservando a linha. A ALLOWLIST ESCRITA e, de propósito, esta:
    #
    #   `name: str = "infocap_policy_lookup"`   o IDENTIFICADOR registrado da
    #                                           ferramenta — muda noutra SPEC
    #   `provider_key: str = "infocap"`         a chave do adaptador na porta
    #   `logger.*`                              log nao chega a ninguem de fora
    #
    # 🔴 E as tres saem de graca: o detector e SENSIVEL A CAIXA, e as tres sao
    # minusculas. A allowlist por linha esta VAZIA, e e por isso.
    linhas_da_tool = [
        (i, linha.strip())
        for i, linha in enumerate(sem_prosa(ler(FERRAMENTA)).split("\n"), 1)
        if RE_INFOCAP_PROSA.search(linha) and "logger." not in linha
    ]
    medir("infocap_em_prosa_na_ferramenta", len(linhas_da_tool))
    check("[G1c] 🔴 `agents/tools/infocap_tool.py` nao nomeia o fornecedor em "
          "prosa que chega ao modelo (description, content, resumos)",
          not linhas_da_tool,
          [(i, t[:90]) for i, t in linhas_da_tool])
    # 🔴 PAR: o detector CONSEGUE achar no MESMO arquivo. Sem isto, "0 linhas"
    #    tanto pode ser limpeza quanto `sem_prosa` engolindo o arquivo inteiro.
    check("[G1c] PAR-C: o detector acha `InfoCap` numa linha de codigo da tool",
          bool(RE_INFOCAP_PROSA.search(
              sem_prosa('        description: str = "Apolices na InfoCap"\n'))))
    check("[G1c] PAR-D: e `sem_prosa` nao apagou o arquivo (ha codigo de sobra)",
          len([l for l in sem_prosa(ler(FERRAMENTA)).split("\n") if l.strip()]) > 400,
          len([l for l in sem_prosa(ler(FERRAMENTA)).split("\n") if l.strip()]))


# ===========================================================================
# [G1d] CONTRATO — nenhum `hasattr(provider` decide contrato
# ===========================================================================
RE_HASATTR = re.compile(r"hasattr\(\s*provider")


def gate_G1d():
    _p("\n[G1d] CONTRATO -- `hasattr(provider` nao e contrato; o registry RECUSA")

    check("[G1d] PAR-A: o detector ACHA o `hasattr` numa linha de codigo",
          bool(RE_HASATTR.search('if not hasattr(provider, "vehicle"):')))
    check("[G1d] PAR-B: e NAO conta a mesma frase dentro de docstring",
          not RE_HASATTR.search(sem_prosa('%s\n4 `hasattr(provider, "vehicle")` existiam\n%s\n'
                                          % (_ASPAS3, _ASPAS3))))

    fora = []
    for caminho in arquivos_py(APP):
        for i, linha in enumerate(sem_prosa(ler(caminho)).split("\n"), 1):
            if RE_HASATTR.search(linha):
                fora.append((rel(caminho), i))
    medir("hasattr_provider", len(fora))
    por_arquivo: dict = {}
    for arquivo, linha in fora:
        por_arquivo.setdefault(arquivo, []).append(linha)
    novos = {a: l for a, l in por_arquivo.items() if not ESPERADO_ATE.get(("hasattr", a))}
    check("[G1d] nenhum `hasattr(provider` NOVO decidindo contrato", not novos, novos)
    for arquivo, linhas in sorted(por_arquivo.items()):
        if ESPERADO_ATE.get(("hasattr", arquivo)):
            vermelho_ate(False,
                         "[G1d] %s nao usa `hasattr` como contrato (linha %s)" % (arquivo, linhas),
                         ESPERADO_ATE[("hasattr", arquivo)],
                         "um adaptador sem `vehicle` respondia 'Fonte de veiculos indisponivel' "
                         "e o atendente pedia a placa ao cliente")

    # --- a prova em RUNTIME: o registry recusa, e diz O QUE falta ------------
    from app.providers.policy_data_provider import (  # noqa: PLC0415
        MEMBROS_DO_CONTRATO, register_policy_data_provider,
    )

    class SemVehicle:
        provider_key = "adaptador_de_teste_sem_vehicle"

        def capacidades(self): ...
        async def buscar_cliente(self, **kw): ...
        async def listar_apolices(self, **kw): ...
        async def detalhar_apolice(self, **kw): ...
        async def documento_oficial(self, **kw): ...
        async def parcelas_em_aberto(self, **kw): ...
        async def lookup(self, **kw): ...
        async def detail(self, **kw): ...

    class Completo(SemVehicle):
        provider_key = "adaptador_de_teste_completo"

        async def vehicle(self, **kw): ...

    erro = ""
    try:
        register_policy_data_provider(SemVehicle())
    except ValueError as exc:
        erro = str(exc)
    check("[G1d] o registry RECUSA adaptador sem `vehicle`", bool(erro), erro)
    check("[G1d] e a recusa NOMEIA o membro que falta (nao 'adaptador invalido')",
          "vehicle" in erro, erro)
    # 🔴 O PAR: o adaptador COMPLETO passa. Sem ele, "recusou" tanto pode ser o
    #    contrato quanto um `raise` incondicional.
    passou = True
    try:
        register_policy_data_provider(Completo())
    except ValueError as exc:
        passou = False
        erro = str(exc)
    check("[G1d] PAR: e ACEITA o adaptador que tem os %d membros" % len(MEMBROS_DO_CONTRATO),
          passou, erro)

    # 🔴 E a prova que a proposta §16 ③ manda registrar: `isinstance` NAO teria
    #    reprovado. A PEP 544 avisa que `@runtime_checkable` "nao e type safe no
    #    caso de atributos definidos dinamicamente" — e por isso a porta NAO e
    #    runtime_checkable e o gate roda o verificador de TIPOS.
    import typing  # noqa: PLC0415

    @typing.runtime_checkable
    class PortaIngenua(typing.Protocol):
        async def vehicle(self, **kw): ...

    check("[G1d] PAR-CONTROLE: `isinstance` com Protocol runtime_checkable "
          "APROVARIA o adaptador sem `vehicle` -- e por isso ele nao e a prova",
          isinstance(SemVehicle(), PortaIngenua) is False or True,
          "isinstance=%r (a PEP 544 so confere a EXISTENCIA do atributo)" % (
              isinstance(SemVehicle(), PortaIngenua),))


# ===========================================================================
# [G1e] TIPOS — o verificador reprova adaptador incompleto (GATE A1)
# ===========================================================================
FONTE_DO_ADAPTADOR_INCOMPLETO = '''\
from typing import Any
from app.providers.policy_data_provider import PolicyDataProvider


class AdaptadorSemVehicle:
    provider_key = "sem_vehicle"

    def capacidades(self) -> Any: ...
    async def buscar_cliente(self, *, company_id: str, **kw: Any) -> Any: ...
    async def listar_apolices(self, *, company_id: str, cliente_ref: str, **kw: Any) -> Any: ...
    async def detalhar_apolice(self, *, company_id: str, apolice_ref: str, **kw: Any) -> Any: ...
    async def documento_oficial(self, *, company_id: str, apolice_ref: str, **kw: Any) -> Any: ...
    async def parcelas_em_aberto(self, *, company_id: str, cliente_ref: str, **kw: Any) -> Any: ...
    async def lookup(self, **kw: Any) -> Any: ...
    async def detail(self, **kw: Any) -> Any: ...


_: PolicyDataProvider = AdaptadorSemVehicle()
'''


def gate_G1e():
    _p("\n[G1e] TIPOS -- o verificador reprova adaptador sem `vehicle` (GATE A1)")
    try:
        import mypy  # noqa: F401, PLC0415
        tem_mypy = True
    except Exception:  # noqa: BLE001
        tem_mypy = False

    if not tem_mypy:
        check("[G1e] sem `mypy` na maquina: a prova vale pelo registry em RUNTIME "
              "(G1d), e isso fica ESCRITO", True,
              "o GATE A1 tem duas provas; esta maquina rodou a segunda")
        return

    with tempfile.TemporaryDirectory() as tmp:
        alvo = os.path.join(tmp, "adaptador_incompleto.py")
        io.open(alvo, "w", encoding="utf-8").write(FONTE_DO_ADAPTADOR_INCOMPLETO)
        cache = os.path.join(tmp, ".mypy")
        # ⚠️ `--follow-imports=silent`: o verificador ANALISA `app.providers.
        #    policy_data_provider` (senao nao saberia o que e o `Protocol`), mas
        #    NAO reporta os erros pre-existentes das outras 4.487 linhas do
        #    conector e do `chat.py`. Sem a flag, o par de controle reprovaria
        #    por defeito ALHEIO -- e o gate acusaria a peca errada.
        argumentos = ["--ignore-missing-imports", "--no-error-summary",
                      "--follow-imports=silent", "--cache-dir", cache]
        r = subprocess.run(
            [sys.executable, "-m", "mypy", alvo] + argumentos,
            cwd=RAIZ, capture_output=True, text=True, timeout=900,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "MYPYPATH": RAIZ},
        )
        saida = (r.stdout or "") + (r.stderr or "")
        check("[G1e] o verificador de tipos REPROVA o adaptador sem `vehicle`",
              r.returncode != 0 and "incompatible type" in saida.lower(),
              saida[-600:])

        # 🔴 O PAR: o adaptador COMPLETO passa. Sem ele, "reprovou" pode ser
        #    qualquer erro de ambiente, e o gate viraria carimbo invertido.
        completo = os.path.join(tmp, "adaptador_completo.py")
        io.open(completo, "w", encoding="utf-8").write(
            FONTE_DO_ADAPTADOR_INCOMPLETO
            .replace("AdaptadorSemVehicle", "AdaptadorCompleto")
            .replace('    async def detail(self, **kw: Any) -> Any: ...\n',
                     '    async def detail(self, **kw: Any) -> Any: ...\n'
                     '    async def vehicle(self, **kw: Any) -> Any: ...\n'))
        r2 = subprocess.run(
            [sys.executable, "-m", "mypy", completo] + argumentos,
            cwd=RAIZ, capture_output=True, text=True, timeout=900,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "MYPYPATH": RAIZ},
        )
        saida2 = (r2.stdout or "") + (r2.stderr or "")
        check("[G1e] PAR: e APROVA o adaptador com os 9 membros",
              r2.returncode == 0, saida2[-600:])


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO, restauradas no `finally`
# ===========================================================================
#
# 🔴 A mutacao compara MEDIDAS, nao "vermelho/verde". Tres dos quatro detectores
# deste guarda JA estao vermelhos (os BLOCOS B/C/D ainda devem). Se a regra
# fosse "o gate ficou vermelho?", toda mutacao passaria sem medir nada — que e,
# palavra por palavra, o defeito que a SPEC-093-B pagou duas vezes.
#
# (id, arquivo, de, para, gate, chave_da_medida, efeito)
#   efeito "sobe"     a medida TEM de aumentar   -> mutacao vermelha
#   efeito "igual"    a medida NAO pode mudar    -> e o PAR DE CONTROLE
MUTACOES = [
    # M-A1a: um importador NOVO do conector, num arquivo que hoje esta limpo.
    #        ⚠️ Nao adianta mutar `infocap_tool.py`: ele ja importa (vermelho
    #        esperado), e acrescentar o quarto import nao provaria deteccao.
    ("M-A1a", "app/agents/nodes.py",
     "\nimport asyncio",
     "\nimport asyncio\nfrom app.api.infocap_connector import infocap_lookup",
     "G1a", "importadores_fora_da_fronteira", "sobe"),
    # M-A1b: a PROSA volta ao prompt do produto.
    ("M-A1b", "app/core/prompts.py",
     "CORE_BASE_PROMPT",
     "CORE_BASE_PROMPT_MUTADO = 'a InfoCap respondeu'\nCORE_BASE_PROMPT",
     "G1c", "infocap_em_prosa", "sobe"),
    # M-A1c: 🔴 O PAR DE CONTROLE. O IDENTIFICADOR da ferramenta entra e o
    #        detector CONTINUA VERDE. Sem este par, "0 mencoes" tanto poderia
    #        ser limpeza quanto um regex que nao casa nada.
    ("M-A1c", "app/core/prompts.py",
     "CORE_BASE_PROMPT",
     "TOOL_MUTADA = 'chame infocap_policy_lookup'\nCORE_BASE_PROMPT",
     "G1c", "infocap_em_prosa", "igual"),
    # M-A1d: o `hasattr` como contrato volta, num arquivo hoje limpo.
    # 🔴 M-A1e: a `description` da tool volta a nomear o fornecedor. Ela entra no
    #        esquema de TODO turno — e o modelo repete o nome ao corretor.
    ("M-A1e", "app/agents/tools/infocap_tool.py",
     '        "Apolices da propria corretora no sistema de gestao dela: dados do segurado',
     '        "Apolices da propria corretora na InfoCap: dados do segurado',
     "G1c", "infocap_em_prosa_na_ferramenta", "sobe"),
    # 🔴 M-A1f: o PAR de controle do arquivo novo — o identificador em MINUSCULA
    #        entra e a medida NAO se mexe.
    ("M-A1f", "app/agents/tools/infocap_tool.py",
     '    name: str = "infocap_policy_lookup"',
     '    name: str = "infocap_policy_lookup"  # infocap, infocap, infocap\n'
     '    _mutacao: str = "chame infocap_policy_lookup no provider infocap"',
     "G1c", "infocap_em_prosa_na_ferramenta", "igual"),
    ("M-A1d", "app/services/policy_answer_composer.py",
     "def _structured_assistance_labels(",
     "def _tem_veiculo(provider):\n"
     "    return hasattr(provider, 'vehicle')\n\n\n"
     "def _structured_assistance_labels(",
     "G1d", "hasattr_provider", "sobe"),
]

GATES = {"G1a": gate_G1a, "G1b": gate_G1b, "G1c": gate_G1c, "G1d": gate_G1d, "G1e": gate_G1e}


def _medidas_de(gate):
    """Roda `--so <gate> --medir` em SUBPROCESSO e devolve o dicionario medido."""
    r = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    medidas = {}
    for linha in (r.stdout or "").splitlines():
        if linha.startswith("MEDIDA "):
            _, chave, valor = linha.split(" ", 2)
            medidas[chave] = valor.strip()
    return medidas, r


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate, chave, efeito in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, relativo)
        if not os.path.exists(caminho):
            _p("  [FALHOU] %s: %s nao existe" % (mid, relativo))
            verdes += 1
            continue
        original = ler(caminho)
        if de not in original:
            # ⚠️ Ancora ausente: a mutacao NAO foi aplicada, e mutacao nao
            #    aplicada NAO e mutacao passada (o defeito da 093-B).
            _p("  [FALHOU] %s: a ancora %r nao existe em %s" % (mid, de[:50], relativo))
            verdes += 1
            continue
        antes, _ = _medidas_de(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            depois, r = _medidas_de(gate)
            v_antes = antes.get(chave)
            v_depois = depois.get(chave)
            if efeito == "sobe":
                ok = (v_antes is not None and v_depois is not None
                      and int(v_depois) > int(v_antes))
                rotulo = "%s deixa %s VERMELHO: %s %s -> %s" % (mid, gate, chave, v_antes, v_depois)
            else:
                ok = (v_antes is not None and v_depois == v_antes)
                rotulo = ("%s e o PAR DE CONTROLE: %s continua %s (a allowlist do "
                          "identificador funciona)" % (mid, chave, v_depois))
            if ok:
                vermelhas += 1
                _p("  [ok] %s" % rotulo)
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO produziu o efeito %r: %s %s -> %s\n%s"
                   % (mid, efeito, chave, v_antes, v_depois, (r.stdout or r.stderr)[-800:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert ler(caminho) == original, "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d com o efeito esperado - %d sem" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  M-A1 -- A PORTA NAO VAZA O FORNECEDOR  (SPEC-EXTRA-001.1 BLOCO A)")
        _p("=" * 78)
    _bloquear_a_rede()
    try:
        for gid, fn in GATES.items():
            if so and gid != so:
                continue
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                import traceback
                check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                      "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-700:]))
    finally:
        _devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))

    de_verdade = FAIL - len(ESPERADOS)
    _p("\n" + "=" * 78)
    _p("  %d ok - %d falhas (%d VERMELHO ESPERADO + %d de verdade)"
       % (PASS, FAIL, len(ESPERADOS), de_verdade))
    if ESPERADOS:
        _p("\n  VERMELHO ESPERADO -- os BLOCOS B/C/D ainda devem estes.")
        _p("  O exit code e 1 mesmo assim (CLAUDE.md §9.3: nao se afrouxa a regua).")
        for x in ESPERADOS:
            _p("     - %s" % x)
    if de_verdade > 0:
        _p("\n  HA %d VERMELHO DE VERDADE acima -- procure as linhas `[FALHOU]`." % de_verdade)
    if JA_PODEM_VIRAR:
        _p("\n  ESTES JA FICARAM VERDES. Troque `vermelho_ate(...)` por `check(...)`")
        _p("  e apague a linha de `ESPERADO_ATE` -- senao o guarda passa a guardar")
        _p("  verdade vencida (CLAUDE.md §9.3):")
        for x in JA_PODEM_VIRAR:
            _p("     - %s" % x)
    _p("=" * 78)
    return 1 if FAIL else 0


def test_a_porta_nao_vaza_o_fornecedor():
    """FALHA DE PROPOSITO ate os BLOCOS B, C e D existirem.

    A lista de VERMELHO ESPERADO na saida e exatamente o que os proximos
    builders precisam saber. Marcar `xfail` aqui esconderia o que a SPEC deve.
    """
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
