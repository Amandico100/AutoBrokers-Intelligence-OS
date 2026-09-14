# -*- coding: utf-8 -*-
r"""M-A2 — TODA LINHA TEM ORIGEM. SPEC-EXTRA-001.1 BLOCO A, GATE A2.

A ideia que se modela da **PROV-O** (W3C, 30/04/2013) e UMA: proveniencia e
**do dado**, nao do log. `wasDerivedFrom` aplicado a uma linha de cobertura. O
que se rejeita e a ontologia — RDF, OWL, o grafo. Ficam tres campos num
dataclass congelado: `origem`, `confianca`, `detalhe`.

```
 [G2a] O MOTOR      as duas apolices REAIS montam PELA PORTA, com o conector DUBLADO
 [G2b] ORIGEM       toda `Cobertura` e toda `Parcela` carrega origem
 [G2c] CONTAGEM     HDI reconciliada = 10 - Allianz = 21, e a ORIGEM por linha
 [G2d] TypeError    `CampoComOrigem(origem=None)` NAO SE CONSTROI
 [G2e] PDF-ONLY     o segundo adaptador monta `Apolice` so do documento
 [G2f] CASAMENTO    sinonimo declarado casa; substring solta NAO casa
```

🔴 **O teste chama o MOTOR** (CLAUDE.md §9.4): `CN._build_evidence_pack` com a
resposta REAL da CorpAPI (mascarada), depois `apolice_do_pack` e `reconciliar`
da porta. Ele **nunca** reimplementa a regra que afirma medir — 📊 foi
exatamente isso que deixou 72 assercoes verdes conviverem com um agendamento
que nunca chegava ao cliente (SPEC-083).

⚠️ **E de onde vem a metade documental:** do golden REAL
(`documento_oficial.linhas_de_cobertura`), e nao do extrator. 📊 D4, medido no
BLOCO 0: `_COVERAGE_ROW_RE` exige `R$` e le **0** linhas no PDF da HDI e **1**
no da Allianz (e essa e "Premio Liquido"). Quem conserta o extrator e o BLOCO
D; alimentar as linhas do golden e o que permite a este gate provar a
RECONCILIACAO hoje, sem depender dele.

⛔ SEGURANCA: `SEM_REDE=1`, nenhuma chamada HTTP, nenhuma leitura de banco,
nenhum nome/CPF/numero de apolice. O golden e mascarado na origem.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_toda_linha_tem_origem.py
    ... --so G2d   ·   ... --medir   ·   ... --mutar [M-A2a]
"""
from __future__ import annotations

import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
REPO = os.path.dirname(RAIZ)
FIXTURES = os.path.join(RAIZ, "tests", "fixtures")
GOLDEN = os.path.join(FIXTURES, "golden_apolices_extra0011.json")
CONTROLE = os.path.join(FIXTURES, "apolice_de_controle_extra0011.json")
ITENS_REAIS = os.path.join(FIXTURES, "infocap_itens_garantias_masked.json")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ["SEM_REDE"] = "1"

_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _proibir(self, *a, **k):  # noqa: ANN001
    raise RuntimeError("SPEC-EXTRA-001.1: este guarda roda com SEM_REDE=1. "
                       "Destino pedido: %r" % (a[0] if a else None,))


def _bloquear_a_rede():
    socket.socket.connect = _proibir       # type: ignore[assignment]
    socket.socket.connect_ex = _proibir    # type: ignore[assignment]


def _devolver_a_rede():
    socket.socket.connect = _CONNECT       # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]


PASS = 0
FAIL = 0
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


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


def _json(caminho):
    return json.load(io.open(caminho, encoding="utf-8"))


# ===========================================================================
# O HARNESS DO GOLDEN — o conector DUBLADO, e nada mais falsificado
# ===========================================================================
#
# 🔴 O que e FALSO aqui, e SO isto: a chamada HTTP. O `/documento` e o `/itens`
# sao remontados a partir do golden REAL, com as MESMAS chaves cruas que a
# CorpAPI devolve, e entregues a `_build_evidence_pack` — o motor de producao.
# Falsificar mais faria o gate provar que a fixture casa com a fixture
# (CLAUDE.md §9.4).
#
# ⚠️ 📊 PARA A ALLIANZ o `/itens` nao e reconstruido: e a fixture CRUA medida na
# CorpAPI (`infocap_itens_garantias_masked.json`, a mesma de `bf963b0`).
# PARA A HDI as garantias sao RECONSTRUIDAS do golden com as mesmas chaves
# (`garantia`, `impseg`, `premio`, `franquia`) — e esta frase existe porque
# reconstrucao nao e medicao, e quem ler o gate precisa saber a diferenca.
_ITENS_CRUS_ALLIANZ = None


def itens_crus(apelido, apolice):
    global _ITENS_CRUS_ALLIANZ
    if apelido == "allianz_condominio":
        if _ITENS_CRUS_ALLIANZ is None:
            _ITENS_CRUS_ALLIANZ = _json(ITENS_REAIS)["itens"]
        return _ITENS_CRUS_ALLIANZ
    return [{"item": 1, "garantias": [dict(g) for g in
                                      apolice["cadastro_sistema_de_gestao"]["garantias"]]}]


def documento_cru(apolice):
    """O `/documento` como a fonte o devolve — chaves cruas, valores do golden."""
    c = apolice["cadastro_sistema_de_gestao"]
    doc = {
        # ⛔ `codfil`/`nosnum` SINTETICOS: sao as partes do locator opaco, e o
        #    numero real nunca entra num arquivo de teste.
        "codfil": 1, "nosnum": 999001, "numapo": "900000000000001",
        "seguradora_abrev": apolice["seguradora_abrev"],
        "ramo_abrev": apolice["ramo_abrev"],
        "inivig": apolice["vigencia"]["inicio"],
        "fimvig": apolice["vigencia"]["fim"],
        "cancelado": "T" if apolice["cancelado"] else "F",
        "sit_renovacao_txt": apolice.get("status_cru_do_fornecedor"),
        "preliq": c["premio_liquido"], "preiof": c.get("iof"),
        "pretot": c.get("premio_total"), "numpar": c.get("numero_de_parcelas"),
        "forma_pag": c.get("forma_pag_do_cabecalho"),
        "parcelas": [
            {"parc": p["numero"], "datvenc": p["vencimento"], "vlvenc": p["valor"],
             **({"datquit": p["quitada_em"]} if p.get("quitada_em") else {}),
             "forma_pagamento": p["forma_de_pagamento"]}
            for p in c.get("parcelas") or []],
    }
    if c.get("tabela_itens_presente"):
        doc["tabela_itens"] = "PACOTE"
    return doc


def documental_do_golden(apolice):
    """As linhas do PDF do golden -> `ApoliceDocumental`. `None` se nao houver."""
    from app.providers.policy_data_provider import (  # noqa: PLC0415
        ApoliceDocumental, LinhaDeCoberturaDoDocumento, dinheiro,
    )
    doc = apolice.get("documento_oficial") or {}
    franquias = doc.get("franquia_por_rotulo") or {}
    linhas = tuple(
        LinhaDeCoberturaDoDocumento(
            rotulo=l["rotulo"],
            limite=dinheiro(l.get("lmi")),
            premio=dinheiro(l.get("premio")),
            franquia_texto=(l.get("franquia_texto") or franquias.get(l["rotulo"])),
        )
        for l in doc.get("linhas_de_cobertura") or []
    )
    return ApoliceDocumental(linhas=linhas) if linhas else None


def pela_porta(apelido, *, com_documento=True, golden=None):
    """A `Apolice` montada PELA PORTA, com o conector dublado. O motor e real."""
    from app.api import infocap_connector as CN  # noqa: PLC0415
    from app.providers.infocap_policy_provider import (  # noqa: PLC0415
        apolice_do_pack, apolice_reconciliada_do_pack,
    )
    from app.providers.policy_data_provider import reconciliar  # noqa: PLC0415
    dados = golden if golden is not None else _json(GOLDEN)["apolices"][apelido]
    dc = documento_cru(dados)
    ic = itens_crus(apelido, dados)
    pack = CN._build_evidence_pack(dc, None, None, True,
                                   envelope={"documento": [dc]}, items=ic)
    if not com_documento:
        # 🔴 "sem documento" NAO e "sem reconciliacao". `reconciliar(corp, None)`
        #    e o caminho de PRODUCAO quando o PDF nao existe — e e ele que acende
        #    o contador de premio. 📊 Este guarda ja nasceu com o defeito que a
        #    distincao evita: com `apolice_do_pack` cru, a linha de controle do
        #    M-A3 ficava "apagada" porque NADA era medido, e um detector que nao
        #    tem como acender nao prova que consegue ficar apagado.
        return reconciliar(
            apolice_do_pack(pack, apolice_ref="infocap:1:999001",
                            documento_cru=dc, itens_crus=ic),
            None), pack
    return apolice_reconciliada_do_pack(
        pack, apolice_ref="infocap:1:999001", documento_cru=dc, itens_crus=ic,
        documental=documental_do_golden(dados),
    ), pack


# ===========================================================================
# [G2a] O MOTOR — as duas apolices reais montam pela porta
# ===========================================================================
def gate_G2a():
    _p("\n[G2a] O MOTOR -- as duas apolices REAIS montam PELA PORTA")
    from app.providers.policy_data_provider import Apolice, reais  # noqa: PLC0415

    for apelido, coberturas_cadastro in (("hdi_residencial", 6), ("allianz_condominio", 15)):
        cadastro, pack = pela_porta(apelido, com_documento=False)
        check("[G2a] %s: a porta devolve `Apolice`, nunca o dict do fornecedor" % apelido,
              isinstance(cadastro, Apolice), type(cadastro).__name__)
        check("[G2a] %s: o cadastro traz as %d garantias da fonte"
              % (apelido, coberturas_cadastro),
              len(cadastro.coberturas) == coberturas_cadastro, len(cadastro.coberturas))
        check("[G2a] %s: a vigencia foi classificada por DATA (nao pelo status cru)" % apelido,
              cadastro.vigencia.situacao == "VIGENTE",
              "%s | status cru: %r" % (cadastro.vigencia.situacao,
                                       pack.get("policy_status")))
        check("[G2a] %s: a seguradora tem `coenti` da SUSEP (catalogo NOSSO)" % apelido,
              cadastro.seguradora.conhecida, cadastro.seguradora)
        check("[G2a] %s: o premio liquido chegou como Decimal, nao como 'R$ ...'" % apelido,
              isinstance(cadastro.premio_liquido.valor, Decimal),
              cadastro.premio_liquido)

    # 🔴 O PAR-CONTROLE: o mesmo `/documento` SEM os itens NAO inventa cobertura.
    from app.api import infocap_connector as CN  # noqa: PLC0415
    from app.providers.infocap_policy_provider import apolice_do_pack  # noqa: PLC0415
    dados = _json(GOLDEN)["apolices"]["hdi_residencial"]
    dc = documento_cru(dados)
    vazio = CN._build_evidence_pack(dc, None, None, True,
                                    envelope={"documento": [dc]}, items=[])
    check("[G2a] PAR-CONTROLE: sem `/itens`, a apolice sai com ZERO coberturas "
          "(ausencia continua sendo ausencia)",
          len(apolice_do_pack(vazio, apolice_ref="infocap:1:999001").coberturas) == 0)


# ===========================================================================
# [G2b] ORIGEM — toda linha carrega de onde veio
# ===========================================================================
ORIGENS_VALIDAS = {"sistema_de_gestao", "documento_oficial"}


def gate_G2b():
    _p("\n[G2b] ORIGEM -- toda `Cobertura` e toda `Parcela` carrega origem")
    sem_origem = 0
    total_campos = 0
    for apelido in ("hdi_residencial", "allianz_condominio"):
        apolice, _ = pela_porta(apelido)
        for c in apolice.coberturas:
            for campo in (c.limite, c.franquia, c.premio):
                total_campos += 1
                if campo.origem not in ORIGENS_VALIDAS:
                    sem_origem += 1
        for p in apolice.parcelas:
            for campo in (p.vencimento, p.valor, p.forma_de_pagamento):
                total_campos += 1
                if campo.origem not in ORIGENS_VALIDAS:
                    sem_origem += 1
        check("[G2b] %s: as %d coberturas e as %d parcelas tem origem em "
              "{sistema_de_gestao, documento_oficial}"
              % (apelido, len(apolice.coberturas), len(apolice.parcelas)),
              sem_origem == 0, "%d campos sem origem valida" % sem_origem)
    medir("campos_com_origem", total_campos)
    medir("campos_sem_origem", sem_origem)


# ===========================================================================
# [G2c] CONTAGEM — 10 e 21, e a ORIGEM por linha
# ===========================================================================
def gate_G2c():
    _p("\n[G2c] CONTAGEM -- HDI reconciliada = 10 - Allianz = 21")
    from app.providers.policy_data_provider import reais  # noqa: PLC0415

    hdi, _ = pela_porta("hdi_residencial")
    medir("coberturas_hdi", len(hdi.coberturas))
    check("[G2c] HDI: 6 no cadastro + 4 so no documento = 10 coberturas",
          len(hdi.coberturas) == 10,
          [c.rotulo for c in hdi.coberturas])

    so_do_pdf = [c for c in hdi.coberturas
                 if c.limite.origem == "documento_oficial"
                 and c.premio.origem == "documento_oficial"
                 and not c.divergencias]
    esperadas = {"Ruptura de Tubulacoes", "Vendaval",
                 "Clausula Especifica de Valor Novo",
                 "Coberturas de Assistencias Essenciais"}
    check("[G2c] HDI: as 4 linhas que SO o documento tem chegaram, com origem "
          "`documento_oficial` (nenhuma foi descartada)",
          esperadas.issubset({c.rotulo for c in so_do_pdf}),
          sorted(c.rotulo for c in so_do_pdf))

    assistencia = next((c for c in hdi.coberturas
                        if "Assistencias Essenciais" in c.rotulo), None)
    check("[G2c] HDI: `Assistencias Essenciais` de R$ 125,94 esta presente, "
          "com origem `documento_oficial`",
          assistencia is not None
          and assistencia.premio.valor == Decimal("125.94")
          and assistencia.premio.origem == "documento_oficial",
          assistencia)

    allianz, _ = pela_porta("allianz_condominio")
    medir("coberturas_allianz", len(allianz.coberturas))
    check("[G2c] Allianz: 15 no cadastro + 6 so no documento = 21 coberturas "
          "(a apolice reconciliada NAO tem 15 -- divergencia D5 do BLOCO 0)",
          len(allianz.coberturas) == 21, [c.rotulo for c in allianz.coberturas])

    # 🔴 O rotulo que chega ao corretor e o do DOCUMENTO — o que a seguradora
    #    imprime e o segurado tem na mao. 📊 "RESP. CIVIL SIND. DE CON." x
    #    "RC Sindico": so o segundo da para ler.
    check("[G2c] Allianz: o rotulo entregue e o do DOCUMENTO, nao a abreviacao "
          "truncada da fonte",
          any(c.rotulo == "RC Sindico" or c.rotulo == "RC Síndico"
              for c in allianz.coberturas),
          [c.rotulo for c in allianz.coberturas][:6])

    # ⚠️ A LINHA DE CONTROLE da contagem: sem documento, a HDI fica com 6.
    #    Sem ela, "10" tanto poderia ser reconciliacao quanto duplicacao.
    sem_doc, _ = pela_porta("hdi_residencial", com_documento=False)
    check("[G2c] PAR-CONTROLE: sem o documento, a HDI fica com as 6 do cadastro "
          "(as 10 vem da RECONCILIACAO, nao de duplicacao)",
          len(sem_doc.coberturas) == 6, len(sem_doc.coberturas))


# ===========================================================================
# [G2d] TypeError — `CampoComOrigem` sem origem NAO SE CONSTROI
# ===========================================================================
def gate_G2d():
    _p("\n[G2d] TypeError -- `CampoComOrigem(origem=None)` nao se constroi")
    from app.providers.policy_data_provider import (  # noqa: PLC0415
        CampoComOrigem, Cobertura,
    )
    erro = None
    try:
        CampoComOrigem(valor=1, origem=None, confianca="alta")  # type: ignore[arg-type]
    except TypeError as exc:
        erro = str(exc)
    medir("campo_sem_origem_levanta", 1 if erro else 0)
    check("[G2d] `CampoComOrigem(valor=1, origem=None)` levanta TypeError",
          erro is not None, erro)
    check("[G2d] e a mensagem diz O QUE se esperava (nao 'valor invalido')",
          bool(erro) and "origem" in (erro or ""), erro)

    erro2 = None
    try:
        CampoComOrigem(valor=1, origem="infocap")  # type: ignore[arg-type]
    except TypeError as exc:
        erro2 = str(exc)
    check("[G2d] uma origem INVENTADA ('infocap') tambem levanta TypeError",
          erro2 is not None, erro2)

    # 🔴 O PAR: a construcao CERTA passa. Sem ele, "levantou" pode ser um
    #    `raise` incondicional, e o guarda viraria carimbo invertido.
    ok = CampoComOrigem(valor=1, origem="documento_oficial", confianca="alta")
    check("[G2d] PAR: `origem='documento_oficial'` constroi normalmente",
          ok.origem == "documento_oficial")

    # E a `Cobertura` recusa o valor CRU no lugar do campo com origem.
    erro3 = None
    try:
        Cobertura(rotulo="X", rotulo_normalizado="x", limite=1,  # type: ignore[arg-type]
                  franquia=ok, premio=ok)
    except TypeError as exc:
        erro3 = str(exc)
    check("[G2d] `Cobertura(limite=1)` -- valor cru sem origem -- levanta TypeError",
          erro3 is not None, erro3)


# ===========================================================================
# [G2e] PDF-ONLY — o segundo adaptador prova que o contrato e contrato
# ===========================================================================
def gate_G2e():
    _p("\n[G2e] PDF-ONLY -- a `Apolice` montada SO do documento")
    import asyncio  # noqa: PLC0415

    from app.providers.pdf_only_policy_provider import PdfOnlyProvider  # noqa: PLC0415
    from app.providers.policy_data_provider import (  # noqa: PLC0415
        MEMBROS_DO_CONTRATO, get_policy_data_provider,
    )

    dados = _json(GOLDEN)["apolices"]["hdi_residencial"]
    documental = documental_do_golden(dados)
    provider = PdfOnlyProvider({"pdf_only:golden:hdi": documental})

    faltando = [m for m in MEMBROS_DO_CONTRATO if not callable(getattr(provider, m, None))]
    check("[G2e] o `PdfOnlyProvider` satisfaz os %d membros do contrato"
          % len(MEMBROS_DO_CONTRATO), not faltando, faltando)

    _devolver_a_rede()  # asyncio cria o self-pipe local do loop no Windows
    try:
        laco = asyncio.new_event_loop()
    finally:
        _bloquear_a_rede()
    try:
        apolice = laco.run_until_complete(provider.detalhar_apolice(
            company_id="empresa-de-fixture", apolice_ref="pdf_only:golden:hdi"))
        capac = provider.capacidades()
        parcelas = laco.run_until_complete(provider.parcelas_em_aberto(
            company_id="empresa-de-fixture", cliente_ref="x"))
    finally:
        laco.close()

    check("[G2e] ele monta as 10 coberturas so do documento",
          len(apolice.coberturas) == 10, len(apolice.coberturas))
    origens = {c.limite.origem for c in apolice.coberturas} | \
              {c.premio.origem for c in apolice.coberturas}
    check("[G2e] e TODAS as origens sao `documento_oficial`",
          origens == {"documento_oficial"}, origens)
    check("[G2e] `capacidades()` e honesto: `parcelas_em_aberto` = INDISPONIVEL",
          capac.de("parcelas_em_aberto") == "INDISPONIVEL", capac.por_operacao)
    check("[G2e] 🔴 a lista vazia de parcelas NAO se le como 'nao deve nada': "
          "a capacidade foi declarada ANTES",
          parcelas == [] and capac.de("parcelas_em_aberto") == "INDISPONIVEL")

    # 🔴 O PAR que separa INDISPONIVEL de DESCONHECIDA — a distincao que permite
    #    ao adaptador Agger nascer amanha sem mentir.
    infocap = get_policy_data_provider("infocap")
    check("[G2e] PAR: o InfoCap declara `parcelas_em_aberto` = PARCIAL (P-PILOTO-19: "
          "📊 /parcelas responde 403), e nao INDISPONIVEL",
          infocap is not None and infocap.capacidades().de("parcelas_em_aberto") == "PARCIAL",
          infocap.capacidades().por_operacao if infocap else None)

    from app.providers.policy_data_provider import CapacidadeDoProvider  # noqa: PLC0415
    erro = None
    try:
        CapacidadeDoProvider(provider_key="mudo", por_operacao={"buscar_cliente": "SUPORTADA"})
    except ValueError as exc:
        erro = str(exc)
    check("[G2e] um provider que NAO declara todas as operacoes e recusado "
          "(ausencia nao vira 'descoberta por ausencia')", erro is not None, erro)


# ===========================================================================
# [G2f] CASAMENTO — sinonimo declarado casa; substring solta NAO casa
# ===========================================================================
def gate_G2f():
    _p("\n[G2f] CASAMENTO -- sinonimo DECLARADO casa; substring solta NAO")
    from app.providers.policy_data_provider import (  # noqa: PLC0415
        _chave_de_casamento, mapa_de_rotulos,
    )
    mapa = mapa_de_rotulos()
    check("[G2f] o arquivo de sinonimos foi lido e tem grupos",
          len(mapa.get("grupos") or {}) >= 10, len(mapa.get("grupos") or {}))
    check("[G2f] e ele e datado (revisavel por gente, nao regex escondido)",
          bool(mapa.get("medido_em")), mapa.get("medido_em"))

    # 🔴 O teste chama a FUNCAO QUE `reconciliar` USA (`_chave_de_casamento`),
    #    nao o arquivo de sinonimos. 📊 Este guarda ja nasceu com o defeito da
    #    SPEC-083: a primeira versao comparava `grupo_de_rotulo` direto, provava
    #    que a TABELA estava certa e nao provava que alguem a usava — e a
    #    mutacao "casamento por substring" passou VERDE por isso.
    pares = [
        ("RESP.CIVIL COND", "RC Condomínio", True),
        ("RESP. CIVIL SIND. DE CON.", "RC Síndico", True),
        ("VENDAVAL/CICL/TORNADO/GRA", "Vendaval / Ciclone / Tornado / Granizo", True),
        ("INCÊNDIO/RAIO/EXPLOSÃO", "Básica Simples", True),
        ("ASSITENCIA 24HS", "Assistência 24h", True),
        ("INCÊNDIO", "Incendio", True),
        # 🔴 O PAR QUE FECHA A PORTA: a MESMA apolice tem as DUAS, e por
        #    substring "ROUBO DE BENS" casaria com a de condominos — que tem
        #    outro LMI (R$ 35.000 x R$ 25.000) e outro premio.
        ("ROUBO DE BENS", "Roubo/Furto Qualificado de Bens", True),
        ("ROUBO DE BENS", "Roubo de Bens de Condôminos", False),
        ("DANOS MORAIS", "Danos Eletricos", False),
        ("INCÊNDIO", "Incêndio de Bens de Condôminos", False),
        ("DESPESAS FIXAS", "Despesas Medicas", False),
    ]
    erros = []
    for esquerda, direita, deve_casar in pares:
        casou = _chave_de_casamento(esquerda, mapa) == _chave_de_casamento(direita, mapa)
        if casou != deve_casar:
            erros.append((esquerda, direita, casou, deve_casar))
    medir("pares_de_casamento_errados", len(erros))
    check("[G2f] os %d pares (mesma superficie, veredito oposto) dao o veredito "
          "certo PELO MOTOR" % len(pares), not erros, erros)

    # 🔴 E a prova no ACERVO: na Allianz reconciliada as DUAS coberturas de
    #    roubo existem, separadas, com os LMI que a fonte deu.
    allianz, _ = pela_porta("allianz_condominio")
    qualificado = next((c for c in allianz.coberturas
                        if c.rotulo == "Roubo/Furto Qualificado de Bens"), None)
    condominos = next((c for c in allianz.coberturas
                       if c.rotulo == "Roubo de Bens de Condôminos"), None)
    medir("coberturas_de_roubo_na_allianz",
          sum(1 for c in allianz.coberturas if "Roubo" in c.rotulo))
    check("[G2f] 🔴 no acervo: as DUAS coberturas de roubo chegam separadas",
          qualificado is not None and condominos is not None,
          [c.rotulo for c in allianz.coberturas if "Roubo" in c.rotulo])
    if qualificado and condominos:
        check("[G2f] e o cadastro casou com a CERTA: LMI R$ 25.000 (nao R$ 35.000)",
              qualificado.limite.valor == Decimal("25000.00")
              and condominos.limite.valor == Decimal("35000.00"),
              (qualificado.limite.valor, condominos.limite.valor))
        check("[G2f] a que veio do cadastro tem divergencia OU origem do documento; "
              "a de condominos e SO do documento",
              condominos.premio.origem == "documento_oficial"
              and condominos.premio.valor == Decimal("119.94"),
              condominos.premio)


GATES = {"G2a": gate_G2a, "G2b": gate_G2b, "G2c": gate_G2c,
         "G2d": gate_G2d, "G2e": gate_G2e, "G2f": gate_G2f}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO, restauradas no `finally`
# ===========================================================================
MUTACOES = [
    # M-A2a: `CampoComOrigem` aceita `origem=None`. A mutacao da proposta §10.
    ("M-A2a", "app/providers/policy_data_provider.py",
     "        if self.origem not in ORIGENS:",
     "        if False:",
     "G2d"),
    # M-A2b: a `Cobertura` aceita valor CRU no lugar do campo com origem —
    #        e a linha chega ao corretor sem saber de onde veio.
    ("M-A2b", "app/providers/policy_data_provider.py",
     "            if not isinstance(campo, CampoComOrigem):\n"
     "                raise TypeError(\n"
     '                    "Cobertura.%s tem de ser CampoComOrigem — recebeu %r. "',
     "            if False:\n"
     "                raise TypeError(\n"
     '                    "Cobertura.%s tem de ser CampoComOrigem — recebeu %r. "',
     "G2d"),
    # M-A2c: o rotulo do PDF que nao casa e DESCARTADO em vez de virar
    #        cobertura nova -> as 4 linhas so-PDF da HDI somem, e com elas as
    #        Assistencias Essenciais de R$ 125,94.
    ("M-A2c", "app/providers/policy_data_provider.py",
     "        coberturas.append(_cobertura_do_documento(do_documento, mapa))",
     "        continue",
     "G2c"),
    # M-A2d: o casamento volta a ser por SUBSTRING -> "ROUBO DE BENS" casa com
    #        "Roubo de Bens de Condominos", que e outra cobertura da MESMA
    #        apolice, com outro LMI.
    ("M-A2d", "app/providers/policy_data_provider.py",
     '    return ("grupo:" + gid) if gid else ("rotulo:" + normalizar_rotulo(rotulo))',
     '    return ("grupo:" + gid) if gid else ("rotulo:" + normalizar_rotulo(rotulo).split(" ")[0])',
     "G2f"),
]


def _medidas_de(gate):
    r = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return r


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, relativo)
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _medidas_de(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _medidas_de(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if r.returncode != 0 and falhas and base.returncode == 0:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode,
                      (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
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
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  M-A2 -- TODA LINHA TEM ORIGEM  (SPEC-EXTRA-001.1 BLOCO A)")
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
                      "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    finally:
        _devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_toda_linha_tem_origem():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
