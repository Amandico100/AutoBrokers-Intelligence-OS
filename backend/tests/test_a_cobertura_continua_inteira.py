# -*- coding: utf-8 -*-
r"""M-C2 — A COBERTURA CONTINUA INTEIRA. SPEC-EXTRA-001.1 BLOCO C.

🔴 **Este guarda existe por causa de UMA armadilha, e ela cabe em duas linhas:**

```
infocap_tool.py  regra 1b   "…coberturas_item_a_item, LISTE TODAS…"   <- FICA
infocap_tool.py  regra 3    "…opcoes_de_apolice, liste TODAS…"        <- SAIU
```

As duas dizem *"liste TODAS"*. Uma manda listar **coberturas** (certo, commit
`bf963b0`); a outra mandava listar **apólices** (errado, é o defeito que a
EXTRA-001.1 conserta). **Um executor que aplicasse "tirar 'liste TODAS' do
briefing" ao pé da letra reintroduziria o 6 de 10.** Este guarda fica vermelho
quando isso acontece.

```
 [GC2a] AS 10       HDI pelo MOTOR, com o PDF -> 10 linhas de cobertura, cada uma com ORIGEM
 [GC2b] AS DUAS     franquia 550 x 600 -> as DUAS na resposta · o cadastro incompleto em PROSA
 [GC2c] AS 21       Allianz condominio pelo MOTOR, com o PDF -> 21 linhas
 [GC2d] O PAR       sem PDF -> 6 e 15, todas com origem `cadastro do sistema de gestao`
 [GC2e] A REGRA 1b  o texto de `:465` presente, byte a byte, no briefing do corretor
```

📊 **Os numeros vem do GOLDEN medido no BLOCO 0** (14/09/2026, pela porta, sobre
as duas apolices reais da corretora piloto): HDI **6 no cadastro x 10 no PDF**
(Σ R$ 306,60 = `premio_liquido`); Allianz condominio **15 x 21** (Σ R$ 24.960,60).

⚠️ **O elo que ainda falta, declarado:** o extrator documental de hoje produz
**0** `coverage_row` na HDI e **1** na Allianz (divergencia D4 do BLOCO 0 — a
tabela da HDI nao tem `R$`). Quem o ensina a ler os dois layouts reais e o
**BLOCO D**. Aqui as linhas do PDF sao injetadas no pack como `evidence_items`
**na forma exata que o extrator vai produzir** — e dai em diante **tudo e
motor**: `apolice_documental_do_pack`, `reconciliar` e `_build_llm_briefing` sao
os de producao. 🔴 Isto prova a reconciliacao **sem depender do BLOCO D**, e nao
substitui o teste ponta a ponta que ele deve.

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem PII (o golden nao tem nome, CPF,
numero de apolice nem referencia tecnica).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_cobertura_continua_inteira.py
    ... --so GC2c   ·   ... --medir   ·   ... --mutar [M-C2b]
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
FIXTURES = os.path.join(TESTES, "fixtures")
GOLDEN = os.path.join(FIXTURES, "golden_apolices_extra0011.json")
HARNESS = os.path.join(TESTES, "test_toda_linha_tem_origem.py")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")

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
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)   # type: ignore[union-attr]
    return mod


# 🔴 UM montador do golden, nao dois: `documento_cru` e `itens_crus` sao os do
#    M-A2, e e por eles que o `/documento` e o `/itens` chegam ao motor de
#    producao `_build_evidence_pack`.
_HA = _carregar("_harness_ma2", HARNESS)


def golden():
    with io.open(GOLDEN, encoding="utf-8") as fh:
        return json.load(fh)["apolices"]


def _evidencia_documental(dados):
    """As linhas do PDF do golden na FORMA que o extrator do BLOCO D vai produzir.

    ⚠️ 📊 Hoje `_COVERAGE_ROW_RE` devolve **0** linhas na HDI e **1** na Allianz
    (divergencia D4). Esta funcao NAO conserta o extrator — ela entrega ao motor
    de producao (`apolice_documental_do_pack`) exatamente o `evidence_item` que
    ele ja sabe ler, para que a RECONCILIACAO possa ser medida antes do BLOCO D.
    """
    doc = dados.get("documento_oficial") or {}
    franquias = doc.get("franquia_por_rotulo") or {}
    itens = []
    for linha in doc.get("linhas_de_cobertura") or []:
        itens.append({
            "page_number": 1,
            "evidence_type": "coverage",
            "structured": {
                "kind": "coverage_row",
                "label": linha["rotulo"],
                "lmi": linha.get("lmi"),
                "premium": linha.get("premio"),
                "participation": linha.get("franquia_texto") or franquias.get(linha["rotulo"]),
            },
        })
    return {"evidence_items": itens, "page_count": doc.get("paginas"),
            "extraction_mode": doc.get("parser")}


def pack_do_golden(apelido, *, com_documento=True):
    """O `policy_evidence_pack` de PRODUCAO, montado a partir do golden real."""
    from app.api import infocap_connector as CN

    dados = golden()[apelido]
    documento_cru = _HA.documento_cru(dados)
    itens_crus = _HA.itens_crus(apelido, dados)
    pack = CN._build_evidence_pack(documento_cru, None, None, True,
                                   envelope={"documento": [documento_cru]}, items=itens_crus)
    if com_documento:
        pack["official_policy_document_evidence"] = _evidencia_documental(dados)
    return pack, dados


def briefing_do_golden(apelido, *, com_documento=True, client_facing=False,
                       pergunta="quais sao as coberturas dessa apolice?"):
    """O BRIEFING que chega ao modelo — pelo motor inteiro, sem atalho.

    `_build_evidence_pack` -> `compose_policy_answer_with_meta` ->
    `_build_llm_briefing`. Nada e reimplementado aqui (CLAUDE.md §9.4).
    """
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool
    from app.services.policy_answer_composer import compose_policy_answer_with_meta

    pack, dados = pack_do_golden(apelido, com_documento=com_documento)
    resultado = {
        "ok": True,
        "status": "found",
        "selected": {
            # ⛔ SINTETICO, o mesmo que o harness do M-A2 usa. O numero real da
            #    apolice nunca entra num arquivo de teste (nem no golden).
            "policy_number": "900000000000001",
            "insurer_key": dados["seguradora_abrev"],
            "product": dados["ramo_abrev"],
            "valid_from": dados["vigencia"]["inicio"],
            "valid_to": dados["vigencia"]["fim"],
            "policy_status": dados["status_cru_do_fornecedor"],
        },
        "policy_evidence_pack": pack,
        "auto_selected_reason": "única apólice vigente do cliente",
    }
    meta = compose_policy_answer_with_meta(question=pergunta, result=resultado)
    return InfocapPolicyLookupTool._build_llm_briefing(
        resultado, meta, pergunta, client_facing=client_facing), pack, dados


def linhas_de_cobertura(briefing):
    """As linhas `- <rotulo> …` do bloco `coberturas_item_a_item` do briefing."""
    texto = str(briefing or "")
    inicio = texto.find("coberturas_item_a_item")
    if inicio < 0:
        return []
    corpo = texto[inicio:].split("\n")[1:]
    linhas = []
    for linha in corpo:
        if linha.startswith("- "):
            linhas.append(linha)
        elif linha.startswith("    · "):
            continue          # a divergencia e filha da linha anterior
        else:
            break
    return linhas


# ===========================================================================
# [GC2a] AS 10 — a HDI inteira, com a ORIGEM escrita em cada linha
# ===========================================================================
def gate_GC2a():
    _p("\n[GC2a] AS 10 -- HDI residencial pelo MOTOR, com o documento oficial")
    briefing, pack, _ = briefing_do_golden("hdi_residencial")

    do_cadastro = len(pack.get("coverage_sections") or [])
    linhas = linhas_de_cobertura(briefing)
    medir("hdi_coberturas_no_cadastro", do_cadastro)
    medir("hdi_linhas_no_briefing", len(linhas))

    check("[GC2a] 📊 o cadastro do sistema de gestao traz 6 (era essa a resposta de ontem)",
          do_cadastro == 6, do_cadastro)
    check("[GC2a] 🔴 e o briefing entrega 10 — as 6 + as 4 que so o documento tem",
          len(linhas) == 10, [l[:60] for l in linhas])
    check("[GC2a] o cabecalho anuncia as 10 e manda LISTAR TODAS",
          "coberturas_item_a_item (10 contratadas" in briefing
          and "LISTE TODAS na resposta" in briefing,
          briefing[briefing.find("coberturas_item_a_item"):][:220])
    check("[GC2a] 🔴 TODA linha carrega a origem escrita ao lado",
          linhas and all(" — origem: " in l for l in linhas),
          [l for l in linhas if " — origem: " not in l])
    check("[GC2a] e a origem e dita em portugues, nunca o nome do fornecedor",
          all(("cadastro do sistema de gestao" in l) or ("documento oficial da apolice" in l)
              for l in linhas)
          and "InfoCap" not in briefing,
          [l for l in linhas
           if "cadastro do sistema de gestao" not in l and "documento oficial da apolice" not in l])

    # 🔴 As 4 que o cadastro NAO tinha — e a de R$ 125,94 e a que paga o
    #    chaveiro/eletricista que o atendente promete ao segurado.
    so_do_documento = ("Ruptura de Tubulacoes", "Vendaval",
                       "Clausula Especifica de Valor Novo", "Coberturas de Assistencias Essenciais")
    faltando = [r for r in so_do_documento if r not in briefing]
    check("[GC2a] 🔴 as 4 linhas que so o documento tem chegam ao modelo",
          not faltando, faltando)
    assistencia = [l for l in linhas if "Assistencias Essenciais" in l]
    check("[GC2a] 'Assistencias Essenciais' vem com origem DOCUMENTO e o premio do PDF",
          len(assistencia) == 1
          and "documento oficial da apolice" in assistencia[0]
          and "R$ 125,94" in assistencia[0],
          assistencia)
    check("[GC2a] o premio liquido da apolice continua na mesa (R$ 306,60)",
          "R$ 306,60" in briefing, briefing[:1500])


# ===========================================================================
# [GC2b] AS DUAS — a divergencia aparece inteira, e o cadastro se declara
# ===========================================================================
def gate_GC2b():
    _p("\n[GC2b] AS DUAS -- franquia 550 x 600, e o cadastro incompleto em PROSA")
    briefing, _, _ = briefing_do_golden("hdi_residencial")

    danos = [l for l in linhas_de_cobertura(briefing) if "Danos Eletricos" in l]
    check("[GC2b] a cobertura de Danos Eletricos esta no briefing", len(danos) == 1, danos)
    trecho = briefing[briefing.find("Danos Eletricos"):][:600] if danos else ""
    check("[GC2b] 🔴 as DUAS franquias aparecem — 600,00 (documento) e 550,00 (cadastro)",
          "600,00" in trecho and "550,00" in trecho, trecho[:400])
    check("[GC2b] e a divergencia e DITA, com as duas fontes nomeadas",
          "as duas fontes discordam" in trecho
          and "o documento oficial diz" in trecho and "o sistema de gestão diz" in trecho,
          trecho[:400])
    check("[GC2b] ⛔ e o briefing NAO escolhe por conta do corretor",
          "nao escolha por conta" in briefing, briefing[-1500:])

    # 📊 O sinal do BLOCO A vira uma frase que o corretor LE — nao um codigo.
    check("[GC2b] 🔴 o cadastro incompleto vira PROSA: 6 das 10, R$ 236,31 (77,07%)",
          "aviso_sobre_o_cadastro:" in briefing
          and "6 das 10 coberturas" in briefing
          and "R$ 236,31" in briefing and "77.07" in briefing,
          briefing[briefing.find("aviso_sobre_o_cadastro"):][:400])

    # 📊 §8.3: a forma de pagamento vem DAS PARCELAS (cartao), nunca do cabecalho
    #    (boleto) — e a divergencia do cabecalho e dita, nao escondida.
    check("[GC2b] forma de pagamento lida das PARCELAS (Cartão de Crédito)",
          "forma_de_pagamento: Cartão de Crédito (lida das PARCELAS)" in briefing,
          briefing[briefing.find("forma_de_pagamento"):][:260])
    check("[GC2b] e o cabecalho que diz outra coisa e DECLARADO, nao apagado",
          "o cabecalho do cadastro diz Boleto Bancário" in briefing,
          briefing[briefing.find("forma_de_pagamento"):][:260])


# ===========================================================================
# [GC2c] AS 21 — a Allianz condominio
# ===========================================================================
def gate_GC2c():
    _p("\n[GC2c] AS 21 -- Allianz condominio pelo MOTOR, com o documento oficial")
    briefing, pack, _ = briefing_do_golden("allianz_condominio")

    do_cadastro = len(pack.get("coverage_sections") or [])
    linhas = linhas_de_cobertura(briefing)
    medir("allianz_coberturas_no_cadastro", do_cadastro)
    medir("allianz_linhas_no_briefing", len(linhas))

    check("[GC2c] 📊 o cadastro traz 15 (o numero do commit bf963b0)", do_cadastro == 15, do_cadastro)
    check("[GC2c] 🔴 e o briefing entrega 21 — as 6 que so o documento tem entram",
          len(linhas) == 21, [l[:50] for l in linhas])
    check("[GC2c] TODA linha carrega origem",
          linhas and all(" — origem: " in l for l in linhas),
          [l for l in linhas if " — origem: " not in l])
    so_do_documento = ("Alagamento", "Perda/Pagamento Aluguel", "RC Guarda Veículos",
                       "Roubo de Bens de Condôminos", "Ruptura de Tanques", "Gastos com Defesa")
    faltando = [r for r in so_do_documento if r not in briefing]
    check("[GC2c] 🔴 as 6 linhas que so o documento tem chegam ao modelo", not faltando, faltando)
    check("[GC2c] e o cadastro incompleto se declara (15 das 21, R$ 6.987,58)",
          "15 das 21 coberturas" in briefing and "R$ 6.987,58" in briefing,
          briefing[briefing.find("aviso_sobre_o_cadastro"):][:400])


# ===========================================================================
# [GC2d] O PAR DE CONTROLE — sem documento, 6 e 15, e a origem muda
# ===========================================================================
def gate_GC2d():
    _p("\n[GC2d] O PAR -- sem o documento oficial: 6 e 15, todas do CADASTRO")
    #
    # 🔴 Este e o par que da direito a conclusao (CLAUDE.md §9.5): a mesma
    # apolice, o mesmo motor, o mesmo briefing — e a UNICA coisa que muda e o
    # documento. Sem ele, "10" tanto poderia ser a reconciliacao quanto um
    # numero fixo em qualquer lugar do caminho.
    esperado = {"hdi_residencial": 6, "allianz_condominio": 15}
    for apelido, quantas in esperado.items():
        briefing, pack, _ = briefing_do_golden(apelido, com_documento=False)
        linhas = linhas_de_cobertura(briefing)
        medir("%s_linhas_sem_documento" % apelido.split("_")[0], len(linhas))
        check("[GC2d] %s sem PDF: %d linhas (as do cadastro, nenhuma a menos)"
              % (apelido, quantas), len(linhas) == quantas, [l[:50] for l in linhas])
        check("[GC2d] %s sem PDF: TODA linha diz `cadastro do sistema de gestao`" % apelido,
              linhas and all("origem: cadastro do sistema de gestao" in l for l in linhas),
              [l for l in linhas if "origem: cadastro do sistema de gestao" not in l])
        check("[GC2d] %s sem PDF: nenhuma linha se diz do documento" % apelido,
              not any("documento oficial da apolice" in l for l in linhas),
              [l for l in linhas if "documento oficial da apolice" in l])
        # ⚠️ E o contador de premio CONTINUA aceso: o cadastro esta incompleto
        #    tenha ou nao documento — o sinal e sobre o CADASTRO.
        check("[GC2d] %s sem PDF: o cadastro incompleto continua declarado" % apelido,
              "aviso_sobre_o_cadastro:" in briefing,
              briefing[:900])


# ===========================================================================
# [GC2e] A REGRA 1b — a armadilha da §7.2, medida byte a byte
# ===========================================================================
_REGRA_1B = ("1b. Se houver coberturas_item_a_item, LISTE TODAS (nenhuma de fora), cada uma com "
             "limite, franquia e premio — de preferencia numa tabela. Nunca resuma para "
             "'uma cobertura' quando o bloco traz varias.")


def gate_GC2e():
    _p("\n[GC2e] A REGRA 1b -- ela FICA, byte a byte (a armadilha da §7.2)")
    briefing, _, _ = briefing_do_golden("hdi_residencial")

    check("[GC2e] 🔴 a regra 1b esta no briefing do corretor, byte a byte (bf963b0)",
          _REGRA_1B in briefing, briefing[-1600:])
    check("[GC2e] e a regra que SAIU e a das APOLICES, nao a das coberturas",
          "Se houver opcoes_de_apolice" not in briefing
          and "NUNCA liste apolices" in briefing,
          briefing[-1600:])
    # 🔴 O PAR que prova que as duas nao se confundem: as palavras sao as mesmas,
    #    os objetos sao opostos. Uma diz COBERTURA; a outra dizia APOLICE.
    check("[GC2e] PAR: 'LISTE TODAS' fala de COBERTURA; nenhuma ordem de listar APOLICE",
          "LISTE TODAS (nenhuma de fora)" in briefing
          and "liste TODAS com os numeros exatos" not in briefing,
          briefing[-1600:])

    # A regra vale para o corretor; a conversa com o SEGURADO nao e relatorio.
    briefing_cliente, _, _ = briefing_do_golden("hdi_residencial", client_facing=True)
    check("[GC2e] PAR: no bloco do SEGURADO a regra de relatorio nao entra",
          "LISTE TODAS (nenhuma de fora)" not in briefing_cliente
          and "NAO despeje este bloco" in briefing_cliente,
          briefing_cliente[-900:])
    check("[GC2e] mas as 10 coberturas continuam no bloco do segurado (o dado nao muda)",
          len(linhas_de_cobertura(briefing_cliente)) == 10,
          [l[:50] for l in linhas_de_cobertura(briefing_cliente)])


GATES = {
    "GC2a": gate_GC2a,
    "GC2b": gate_GC2b,
    "GC2c": gate_GC2c,
    "GC2d": gate_GC2d,
    "GC2e": gate_GC2e,
}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
MUTACOES = [
    # 🔴 M-C2b: a mutacao que a proposta §10 nomeia — APAGAR a regra 1b. E o
    #    gesto que um executor apressado faria ao ler "tirar 'liste TODAS' do
    #    briefing", e ele reintroduz o 6 de 10 do commit anterior a `bf963b0`.
    ("M-C2b", "app/agents/tools/infocap_tool.py",
     '            "1b. Se houver coberturas_item_a_item, LISTE TODAS (nenhuma de fora), '
     'cada uma com limite, franquia e premio — de preferencia numa tabela. Nunca resuma '
     "para 'uma cobertura' quando o bloco traz varias.\",\n",
     "",
     "GC2e"),
    # M-C2f: o corte das coberturas volta a ser pequeno demais -> as 10 nao chegam.
    #        📊 `[:60]` e o teto do briefing; `[:5]` deixaria 5 de 10 de fora em
    #        SILENCIO, que e exatamente a forma do defeito original.
    ("M-C2f", "app/agents/tools/infocap_tool.py",
     'for cobertura in (getattr(apolice, "coberturas", ()) or ())[:60]:',
     'for cobertura in (getattr(apolice, "coberturas", ()) or ())[:5]:',
     "GC2a"),
    # M-C2g: o briefing volta a ler `coverage_sections` cru, sem reconciliar ->
    #        6 linhas e nenhuma origem. E o defeito medido no diagnostico de 12/09.
    ("M-C2g", "app/agents/tools/infocap_tool.py",
     "                apolice = apolice_reconciliada_do_pack(pack)",
     "                apolice = None",
     "GC2a"),
    # M-C2h: a divergencia para de ser dita -> a franquia do cadastro some, e o
    #        corretor liga para a seguradora com o numero errado.
    ("M-C2h", "app/agents/tools/infocap_tool.py",
     "        for divergencia in cobertura.divergencias:",
     "        for divergencia in ():",
     "GC2b"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011c2").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
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
        _p("  M-C2 -- A COBERTURA CONTINUA INTEIRA  (SPEC-EXTRA-001.1 BLOCO C)")
        _p("=" * 78)
    _HA._bloquear_a_rede()
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
        _HA._devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_a_cobertura_continua_inteira():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
