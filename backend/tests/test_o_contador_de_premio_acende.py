# -*- coding: utf-8 -*-
r"""M-A3 — O CONTADOR DE PREMIO ACENDE. SPEC-EXTRA-001.1 BLOCO A, GATE A3.

```
Σ premio(cobertura do sistema de gestao)  ≠  premio_liquido  ->  cadastro_incompleto
```

📊 **Teria acendido nas duas apolices do caso de referencia**, e ninguem teria
precisado descobrir por leitura que faltava cobertura:

```
HDI residencial      R$    70,29  x  R$    306,60   ->  R$   236,31 faltando, 77%
Allianz condominio   R$ 17.973,02  x  R$ 24.960,60   ->  R$ 6.987,58 faltando, 28%
```

🔴 **E a LINHA DE CONTROLE e o que da direito a conclusao** (CLAUDE.md §9.2).
📊 O BLOCO 0 mediu que a Allianz **nao serve** de controle — o contador acende
nela tambem (divergencia D5, decisao D-E0011-03). Por isso existe
`apolice_de_controle_extra0011.json`: SINTETICA, com a soma batendo ao centavo.
Sem ela, `Sinal("cadastro_incompleto")` poderia estar aceso por um `return
True` e o gate continuaria verde.

```
 [G3a] ACENDE        HDI e Allianz, com a diferenca em R$ e em %
 [G3b] CONTROLE      a apolice sintetica cuja soma BATE -> sinal APAGADO
 [G3c] TOLERANCIA    o par R$ 0,05 (apagado) x R$ 0,06 (aceso)
 [G3d] FORMA_PAG     a forma vem das PARCELAS; o cabecalho vira sinal
 [G3e] DIVERGENCIA   franquia 550 x 600 -- as DUAS ficam, e o PDF vence
 [G3f] SOBREVIVE     o sinal continua aceso DEPOIS da reconciliacao
```

⚠️ O gate importa o harness de `test_toda_linha_tem_origem.py` — o mesmo
montador, a mesma resposta real, o mesmo motor. Duas copias do montador
divergiriam, e e o defeito nº 1 deste projeto.

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem PII.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_contador_de_premio_acende.py
    ... --so G3c   ·   ... --medir   ·   ... --mutar [M-A3a]
"""
from __future__ import annotations

import importlib.util
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

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTES = os.path.join(RAIZ, "tests")
FIXTURES = os.path.join(TESTES, "fixtures")
GOLDEN = os.path.join(FIXTURES, "golden_apolices_extra0011.json")
CONTROLE = os.path.join(FIXTURES, "apolice_de_controle_extra0011.json")
HARNESS = os.path.join(TESTES, "test_toda_linha_tem_origem.py")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ["SEM_REDE"] = "1"

_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _proibir(self, *a, **k):  # noqa: ANN001
    raise RuntimeError("SPEC-EXTRA-001.1: SEM_REDE=1. Destino: %r" % (a[0] if a else None,))


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


# 🔴 UM montador, nao dois. O harness do M-A2 e importado, nunca copiado.
_spec = importlib.util.spec_from_file_location("_0011_harness", HARNESS)
H = importlib.util.module_from_spec(_spec)   # type: ignore[arg-type]
sys.modules["_0011_harness"] = H
_spec.loader.exec_module(H)                  # type: ignore[union-attr]


def _json(caminho):
    return json.load(io.open(caminho, encoding="utf-8"))


def _sinal(apolice, codigo):
    return apolice.sinal(codigo)


# ===========================================================================
# [G3a] ACENDE — as duas apolices reais
# ===========================================================================
def gate_G3a():
    _p("\n[G3a] ACENDE -- HDI e Allianz, com a diferenca em R$ e em %")
    esperado = {
        "hdi_residencial": (Decimal("236.31"), Decimal("77.07"), Decimal("70.29")),
        "allianz_condominio": (Decimal("6987.58"), Decimal("27.99"), Decimal("17973.02")),
    }
    for apelido, (dif, pct, soma) in esperado.items():
        apolice, _ = H.pela_porta(apelido)
        sinal = _sinal(apolice, "cadastro_incompleto")
        medir("sinal_%s" % apelido, 1 if sinal else 0)
        if not check("[G3a] %s: `cadastro_incompleto` ACESO" % apelido, sinal is not None,
                     [s.codigo for s in apolice.sinais]):
            continue
        check("[G3a] %s: a diferenca e R$ %s (soma R$ %s x liquido)"
              % (apelido, dif, soma),
              sinal.detalhe["diferenca_reais"] == dif
              and sinal.detalhe["soma_das_coberturas"] == soma,
              sinal.detalhe)
        check("[G3a] %s: e o percentual e %s%%" % (apelido, pct),
              sinal.detalhe["diferenca_pct"] == pct, sinal.detalhe["diferenca_pct"])
        check("[G3a] %s: o sinal diz a TOLERANCIA que usou (nao um numero magico)"
              % apelido,
              sinal.detalhe.get("tolerancia_reais") == Decimal("0.05"), sinal.detalhe)


# ===========================================================================
# [G3b] CONTROLE — a apolice sintetica cuja soma BATE
# ===========================================================================
def _apolice_de_controle(premio_liquido=None):
    """A fixture sintetica, montada PELO MESMO caminho das reais."""
    dados = _json(CONTROLE)
    dados = json.loads(json.dumps(dados))   # copia: o gate mexe no premio
    if premio_liquido is not None:
        dados["cadastro_sistema_de_gestao"]["premio_liquido"] = premio_liquido
    apolice, _ = H.pela_porta("controle", com_documento=False, golden=dados)
    return apolice


def gate_G3b():
    _p("\n[G3b] CONTROLE -- a apolice sintetica cuja soma BATE")
    apolice = _apolice_de_controle()
    sinal = _sinal(apolice, "cadastro_incompleto")
    medir("sinal_controle", 1 if sinal else 0)
    check("[G3b] 🔴 a soma das 6 coberturas bate com o premio liquido (R$ 117,27) "
          "-> `cadastro_incompleto` APAGADO",
          sinal is None, sinal.detalhe if sinal else None)
    check("[G3b] e o controle NAO e vazio: ele tem as 6 coberturas "
          "(um detector so fica apagado por ter o que somar)",
          len(apolice.coberturas) == 6, len(apolice.coberturas))
    check("[G3b] 🔴 PAR-CONTROLE do cabecalho: aqui cabecalho e parcelas "
          "CONCORDAM (Boleto x Boleto) -> `cabecalho_divergente` APAGADO",
          _sinal(apolice, "cabecalho_divergente") is None,
          [s.codigo for s in apolice.sinais])


# ===========================================================================
# [G3c] TOLERANCIA — o par R$ 0,05 x R$ 0,06
# ===========================================================================
def gate_G3c():
    _p("\n[G3c] TOLERANCIA -- o par R$ 0,05 (apagado) x R$ 0,06 (aceso)")
    limiar = _json(CONTROLE)["limiar"]
    dentro = _apolice_de_controle(limiar["dentro_da_tolerancia"]["premio_liquido"])
    fora = _apolice_de_controle(limiar["fora_da_tolerancia"]["premio_liquido"])
    medir("sinal_no_limiar_dentro", 1 if _sinal(dentro, "cadastro_incompleto") else 0)
    medir("sinal_no_limiar_fora", 1 if _sinal(fora, "cadastro_incompleto") else 0)
    check("[G3c] diferenca de R$ 0,05 (exatamente a tolerancia) -> APAGADO",
          _sinal(dentro, "cadastro_incompleto") is None,
          _sinal(dentro, "cadastro_incompleto"))
    check("[G3c] 🔴 diferenca de R$ 0,06 (um centavo alem) -> ACESO. "
          "E este par que impede a tolerancia de virar enfeite.",
          _sinal(fora, "cadastro_incompleto") is not None)

    from app.providers.policy_data_provider import TOLERANCIA_DE_PREMIO  # noqa: PLC0415
    check("[G3c] a tolerancia esta DECLARADA no codigo e e pequena (R$ 0,05)",
          TOLERANCIA_DE_PREMIO == Decimal("0.05"), TOLERANCIA_DE_PREMIO)


# ===========================================================================
# [G3d] FORMA_PAG — das PARCELAS, nunca do cabecalho
# ===========================================================================
def gate_G3d():
    _p("\n[G3d] FORMA_PAG -- a forma vem das PARCELAS; o cabecalho vira sinal")
    hdi, _ = H.pela_porta("hdi_residencial")
    sinal = _sinal(hdi, "cabecalho_divergente")
    medir("cabecalho_divergente_hdi", 1 if sinal else 0)
    check("[G3d] HDI: `cabecalho_divergente` ACESO (📊 cabecalho 'Boleto Bancario' "
          "x 4 parcelas 'Cartao de Credito')", sinal is not None,
          [s.codigo for s in hdi.sinais])
    if sinal:
        check("[G3d] e o sinal mostra OS DOIS lados (nao so 'discordam')",
              sinal.detalhe.get("no_cabecalho") and sinal.detalhe.get("nas_parcelas"),
              sinal.detalhe)
    check("[G3d] 🔴 a forma de pagamento da apolice e 'Cartao de Credito' -- "
          "o que o segurado realmente paga",
          hdi.forma_de_pagamento == "Cartão de Crédito", hdi.forma_de_pagamento)
    check("[G3d] e TODAS as 4 parcelas dizem cartao, com origem `sistema_de_gestao`",
          len(hdi.parcelas) == 4
          and all(p.forma_de_pagamento.valor == "Cartão de Crédito" for p in hdi.parcelas)
          and all(p.forma_de_pagamento.origem == "sistema_de_gestao" for p in hdi.parcelas),
          [(p.numero, p.forma_de_pagamento.valor) for p in hdi.parcelas])

    # 🔴 O PAR: a Allianz CONCORDA (cabecalho e 6 parcelas dizem boleto).
    allianz, _ = H.pela_porta("allianz_condominio")
    check("[G3d] PAR: na Allianz o cabecalho e as 6 parcelas CONCORDAM (boleto) "
          "-> sinal APAGADO",
          _sinal(allianz, "cabecalho_divergente") is None,
          [s.codigo for s in allianz.sinais])


# ===========================================================================
# [G3e] DIVERGENCIA — as duas ficam, e o documento vence
# ===========================================================================
def gate_G3e():
    _p("\n[G3e] DIVERGENCIA -- franquia 550 x 600: as DUAS ficam")
    hdi, _ = H.pela_porta("hdi_residencial")
    danos = next((c for c in hdi.coberturas if "Danos" in c.rotulo), None)
    check("[G3e] a cobertura de Danos Eletricos existe na apolice reconciliada",
          danos is not None, [c.rotulo for c in hdi.coberturas])
    if danos is None:
        return
    franquia = next((d for d in danos.divergencias if d.campo == "franquia"), None)
    medir("divergencia_de_franquia", 1 if franquia else 0)
    check("[G3e] ha `Divergencia` de FRANQUIA em Danos Eletricos",
          franquia is not None, [d.campo for d in danos.divergencias])
    if franquia:
        check("[G3e] 🔴 e as DUAS aparecem: 550 (sistema de gestao) e 600 (documento)",
              "550" in str(franquia.valor_sistema_de_gestao)
              and "600" in str(franquia.valor_documento_oficial),
              (franquia.valor_sistema_de_gestao, franquia.valor_documento_oficial))
        check("[G3e] o valor ENTREGUE e o do documento, com a origem escrita",
              danos.franquia.origem == "documento_oficial"
              and "600" in str(danos.franquia.valor), danos.franquia)
        check("[G3e] e a divergencia vira FRASE legivel para o corretor",
              "600" in franquia.como_frase() and "550" in franquia.como_frase(),
              franquia.como_frase())

    premio = next((d for d in danos.divergencias if d.campo.startswith("pr")), None)
    check("[G3e] o premio tambem diverge (📊 19,17 x 17,25) e a MESMA cobertura "
          "carrega as DUAS divergencias",
          premio is not None and len(danos.divergencias) >= 2,
          [d.campo for d in danos.divergencias])

    # 🔴 O PAR DA TOLERANCIA sobre a divergencia: 📊 Allianz Danos Eletricos
    #    4.803,67 x 4.803,68 -> um centavo -> NAO e divergencia.
    allianz, _ = H.pela_porta("allianz_condominio")
    danos_a = next((c for c in allianz.coberturas if c.rotulo == "Danos Elétricos"), None)
    medir("divergencias_allianz_danos", len(danos_a.divergencias) if danos_a else -1)
    check("[G3e] 🔴 PAR: Allianz Danos Eletricos (4.803,67 x 4.803,68) fica SEM "
          "divergencia -- um centavo de arredondamento nao e discordancia",
          danos_a is not None and not danos_a.divergencias,
          [d.campo for d in (danos_a.divergencias if danos_a else ())])

    # ⚠️ E o que NAO e arredondamento continua aparecendo, na mesma apolice.
    assist = next((c for c in allianz.coberturas if "24h" in c.rotulo), None)
    check("[G3e] PAR-B: na MESMA apolice, `Assistencia 24h` (0,00 no cadastro x "
          "R$ 23,88 no documento) DIVERGE -- a tolerancia nao apagou o que importa",
          assist is not None and any(d.campo.startswith("pr") for d in assist.divergencias),
          [d.campo for d in (assist.divergencias if assist else ())])


# ===========================================================================
# [G3f] SOBREVIVE — o sinal e sobre o CADASTRO
# ===========================================================================
def gate_G3f():
    _p("\n[G3f] SOBREVIVE -- o sinal continua aceso DEPOIS da reconciliacao")
    sem_doc, _ = H.pela_porta("hdi_residencial", com_documento=False)
    com_doc, _ = H.pela_porta("hdi_residencial")
    check("[G3f] antes da reconciliacao: ACESO (6 coberturas)",
          _sinal(sem_doc, "cadastro_incompleto") is not None
          and len(sem_doc.coberturas) == 6)
    check("[G3f] 🔴 depois da reconciliacao: a apolice fica INTEIRA (10 coberturas) "
          "e o sinal CONTINUA ACESO -- ele e sobre o CADASTRO, nao sobre a resposta",
          _sinal(com_doc, "cadastro_incompleto") is not None
          and len(com_doc.coberturas) == 10,
          (len(com_doc.coberturas), [s.codigo for s in com_doc.sinais]))
    antes = _sinal(sem_doc, "cadastro_incompleto").detalhe["diferenca_reais"]
    depois = _sinal(com_doc, "cadastro_incompleto").detalhe["diferenca_reais"]
    check("[G3f] e a diferenca nao muda com a reconciliacao (R$ %s)" % antes,
          antes == depois, (antes, depois))

    # 🔴 `reconciliar` e PURO: mesma entrada, mesma saida, sem I/O.
    from app.providers.policy_data_provider import reconciliar  # noqa: PLC0415
    dados = _json(GOLDEN)["apolices"]["hdi_residencial"]
    documental = H.documental_do_golden(dados)
    uma = reconciliar(sem_doc, documental)
    outra = reconciliar(sem_doc, documental)
    check("[G3f] `reconciliar` e PURO: duas chamadas dao o mesmo resultado",
          [c.rotulo for c in uma.coberturas] == [c.rotulo for c in outra.coberturas]
          and uma.coberturas == outra.coberturas)
    check("[G3f] e ele nao muda a entrada (a `Apolice` e congelada)",
          len(sem_doc.coberturas) == 6, len(sem_doc.coberturas))

    # 🔴 IDEMPOTENTE, e e este par que prova que o contador soma SO o CADASTRO.
    #    Reconciliar de novo a apolice JA reconciliada: as 10 coberturas somam
    #    exatamente o premio liquido (📊 R$ 306,60 = preliq), entao um contador
    #    que somasse TODAS as origens apagaria o sinal — e a apolice com 77% do
    #    premio faltando no cadastro passaria por completa.
    duas_vezes = reconciliar(uma, documental)
    acesos = [s for s in duas_vezes.sinais if s.codigo == "cadastro_incompleto"]
    check("[G3f] 🔴 reconciliar DUAS vezes: o sinal continua ACESO e aparece UMA "
          "vez so (o contador soma so o CADASTRO, nao a apolice inteira)",
          len(acesos) == 1 and acesos[0].detalhe["diferenca_reais"] == antes,
          [(s.codigo, s.detalhe.get("diferenca_reais")) for s in duas_vezes.sinais])
    check("[G3f] e a segunda passada nao duplica coberturas",
          len(duas_vezes.coberturas) == len(uma.coberturas) == 10,
          (len(uma.coberturas), len(duas_vezes.coberturas)))


GATES = {"G3a": gate_G3a, "G3b": gate_G3b, "G3c": gate_G3c,
         "G3d": gate_G3d, "G3e": gate_G3e, "G3f": gate_G3f}


# ===========================================================================
# AS MUTACOES
# ===========================================================================
MUTACOES = [
    # M-A3a: a mutacao da proposta §10 — a tolerancia vira infinita.
    ("M-A3a", "app/providers/policy_data_provider.py",
     'TOLERANCIA_DE_PREMIO = Decimal("0.05")',
     'TOLERANCIA_DE_PREMIO = Decimal("Infinity")',
     "G3a"),
    # M-A3b: o contador some -> nada acende, nem na HDI com 77% faltando.
    ("M-A3b", "app/providers/policy_data_provider.py",
     "    sinal_premio = _contador_de_premio(corp)",
     "    sinal_premio = None",
     "G3a"),
    # M-A3c: o `forma_pag` do CABECALHO vence a forma das PARCELAS -> o segurado
    #        le "boleto" para uma apolice com 4 parcelas no cartao.
    ("M-A3c", "app/providers/infocap_policy_provider.py",
     '            forma_de_pagamento=_campo(bruta.get("payment_method"), SISTEMA_DE_GESTAO,\n'
     '                                      provider_field=campos.get("payment_method")),',
     '            forma_de_pagamento=_campo(\n'
     '                (pack.get("premium_summary") or {}).get("payment_method"),\n'
     '                SISTEMA_DE_GESTAO, provider_field="forma_pag"),',
     "G3d"),
    # M-A3d: a divergencia de franquia e resolvida em SILENCIO pelo documento —
    #        o corretor deixa de saber que o cadastro diz outro numero.
    ("M-A3d", "app/providers/policy_data_provider.py",
     "        if de_corp is not None and do_pdf is not None and de_corp != do_pdf:",
     "        if False:",
     "G3e"),
    # M-A3e: a BORDA da tolerancia. `<=` vira `<`, e a diferenca de exatamente
    #        R$ 0,05 -- a tolerancia DECLARADA -- passa a acender. E a metade do
    #        par que nenhum outro guarda cobre: M-A3a prova que a tolerancia
    #        grande demais apaga tudo; esta prova que a borda e onde se disse
    #        que ela esta.
    ("M-A3e", "app/providers/policy_data_provider.py",
     "    if abs(diferenca) <= TOLERANCIA_DE_PREMIO:",
     "    if abs(diferenca) < TOLERANCIA_DE_PREMIO:",
     "G3c"),
    # M-A3f: o sinal recalculado deixa de substituir o anterior -> reconciliar
    #        duas vezes acende `cadastro_incompleto` em DUPLICATA.
    ("M-A3f", "app/providers/policy_data_provider.py",
     '        sinais = [s for s in sinais if s.codigo != "cadastro_incompleto"]' + chr(10),
     "",
     "G3f"),
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
        caminho = os.path.join(RAIZ, relativo)
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011").name
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
        _p("  M-A3 -- O CONTADOR DE PREMIO ACENDE  (SPEC-EXTRA-001.1 BLOCO A)")
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


def test_o_contador_de_premio_acende():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
