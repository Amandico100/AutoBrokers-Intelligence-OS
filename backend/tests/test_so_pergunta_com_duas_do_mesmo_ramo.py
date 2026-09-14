# -*- coding: utf-8 -*-
r"""M-B2 — SO PERGUNTA COM DUAS DO MESMO RAMO. SPEC-EXTRA-001.1 BLOCO B, GATE B2.

```
1 auto vigente + 1 residencial vigente  ->  NAO pergunta (com ramo)
2 auto vigentes                         ->  PERGUNTA
```

🔴 **O par de controle e o que da direito a conclusao** (CLAUDE.md §9.5): as
duas listas tem a MESMA superficie — duas apolices, as duas vigentes, o mesmo
status cru da fonte — e o veredito e OPOSTO. Sem o par, "pergunta menos" tanto
pode ser a regra certa quanto um `return "found"` no lugar errado.

📊 O acervo de 09-11/09/2026 mediu **7 de 7** perguntas do chat respondidas com
*"qual delas?"* e **zero** respondidas com a unica vigente.

```
 [GB2a] O PAR       1 auto + 1 resi -> found com ramo · ambiguous sem ramo
                    2 auto          -> ambiguous, as duas VIGENTES
 [GB2b] FILTRADAS   2 auto + 1 resi VENCIDA -> 2 opcoes, nunca 3
 [GB2c] SEM VIGENTE 0 vigentes -> a frase da §6.2, com a ULTIMA (fim mais recente)
 [GB2d] O PORQUE    `auto_selected_reason` em 100% dos `found`, e legivel
 [GB2e] O STATUS    `policy_status = "ativo"` numa vencida nao a torna opcao
```

⚠️ O teste chama o MOTOR: `escolher_apolice` da porta, sobre listas montadas
por `InfoCapProvider.listar_apolices` (o montador e importado do M-B1 — um so,
nunca dois).

🔴 A regua de lingua e a que JA existe: `problemas_de_lingua` de
`test_o_caso_se_explica_sozinho.py`. Ela nao e reimplementada aqui. Uma clausula
dela — *"nao termina numa proxima acao COM DONO"* — e desligada COM MOTIVO
ESCRITO: ela foi escrita para CARTAS ao segurado, e `auto_selected_reason` e um
fragmento explicativo dentro de um briefing, nao uma carta. As demais (sem
`snake_case`, sem `chave@versao`, sem lingua de apolice) valem inteiras.

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem PII.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_so_pergunta_com_duas_do_mesmo_ramo.py
    ... --so GB2c   ·   ... --medir   ·   ... --mutar [M-B2a]
"""
from __future__ import annotations

import importlib.util
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
HARNESS = os.path.join(TESTES, "test_vencida_nunca_vira_opcao.py")
REGUA = os.path.join(TESTES, "test_o_caso_se_explica_sozinho.py")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

HOJE = date(2026, 9, 14)

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


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)   # type: ignore[union-attr]
    return mod


# 🔴 UM montador, nao dois: o do M-B1 monta a resposta do conector e chama o
#    provider REAL. Duas copias divergiriam, e e o defeito nº 1 deste projeto.
_H = _carregar("_harness_mb1", HARNESS)
_H._bloquear_a_rede()

listar = _H.listar
casos_sinteticos = _H.casos_sinteticos
listagens_reais = _H.listagens_reais


def escolher(caso, *, ramo=None):
    """O MOTOR da escolha: lista INTEIRA -> `escolher_apolice` da porta."""
    from app.providers.policy_data_provider import escolher_apolice
    from app.services.policy_answer_composer import humanize_insurer, humanize_product

    lista = listar(caso, incluir_vencidas=True)
    return escolher_apolice(lista, ramo=ramo, hoje=HOJE,
                            humanizar_seguradora=humanize_insurer,
                            humanizar_ramo=humanize_product)


# ===========================================================================
# A REGUA DE LINGUA — importada, nunca reimplementada
# ===========================================================================
_CLAUSULA_DE_CARTA = "nao termina numa proxima acao COM DONO"


def problemas_no_motivo(texto):
    """`problemas_de_lingua` do guarda da 097, menos a clausula de CARTA.

    ⚠️ `_ACAO_COM_DONO` exige que o texto termine numa proxima acao ("quer que
    eu...", "me diz..."). Isso e regra de CARTA ao segurado. `auto_selected_reason`
    e um fragmento dentro do briefing — exigir dele uma proxima acao produziria
    uma frase pior, nao melhor. As outras clausulas valem inteiras.
    """
    regua = _carregar("_regua_de_lingua", REGUA)
    return [p for p in regua.problemas_de_lingua(texto) if _CLAUSULA_DE_CARTA not in p]


# ===========================================================================
# [GB2a] O PAR — mesma superficie, veredito oposto
# ===========================================================================
def gate_GB2a():
    _p("\n[GB2a] O PAR -- 1 auto + 1 resi NAO pergunta; 2 auto PERGUNTA")
    casos = casos_sinteticos()

    um_de_cada = casos["uma_auto_uma_resi"]
    duas_auto = casos["duas_auto_vigentes"]
    check("[GB2a] as duas listas tem a MESMA superficie: 2 apolices, 2 vigentes",
          len(um_de_cada["apolices"]) == len(duas_auto["apolices"]) == 2
          and len(listar(um_de_cada).itens) == len(listar(duas_auto).itens) == 2,
          (len(listar(um_de_cada).itens), len(listar(duas_auto).itens)))

    com_ramo = escolher(um_de_cada, ramo="auto")
    check("[GB2a] 1 auto + 1 resi, pedido de AUTO -> `found` (nao pergunta)",
          com_ramo.status == "found", com_ramo.status)
    check("[GB2a] e a escolhida e a de AUTO, nao a residencial",
          com_ramo.apolice is not None and com_ramo.apolice.ramo.abreviatura == "AUTO",
          com_ramo.apolice.ramo.abreviatura if com_ramo.apolice else None)
    com_resi = escolher(um_de_cada, ramo="resi")
    check("[GB2a] PAR: o mesmo cliente, pedido RESIDENCIAL -> a residencial",
          com_resi.status == "found" and com_resi.apolice is not None
          and com_resi.apolice.ramo.abreviatura == "RESI",
          (com_resi.status, com_resi.apolice.ramo.abreviatura if com_resi.apolice else None))

    sem_ramo = escolher(um_de_cada, ramo=None)
    check("[GB2a] 1 auto + 1 resi SEM ramo nenhum -> pergunta UMA vez",
          sem_ramo.status == "ambiguous_policy" and len(sem_ramo.opcoes) == 2,
          (sem_ramo.status, len(sem_ramo.opcoes)))

    duas = escolher(duas_auto, ramo="auto")
    check("[GB2a] 🔴 2 auto vigentes -> `ambiguous_policy` com 2 opcoes",
          duas.status == "ambiguous_policy" and len(duas.opcoes) == 2,
          (duas.status, len(duas.opcoes)))
    check("[GB2a] e as duas opcoes estao VIGENTES",
          all(o.vigencia.situacao == "VIGENTE" for o in duas.opcoes),
          [o.vigencia.situacao for o in duas.opcoes])
    medir("opcoes_quando_2_do_mesmo_ramo", len(duas.opcoes))

    # O pedido de AUTO num cliente que so tem residencial: responde, e DIZ.
    so_resi = escolher(casos["so_resi_vigente"], ramo="auto")
    check("[GB2a] pedido de AUTO com so 1 residencial vigente -> `found`, nao lista",
          so_resi.status == "found", so_resi.status)
    check("[GB2a] e o motivo DIZ que nao ha apolice vigente de auto",
          "auto" in (so_resi.auto_selected_reason or "").lower()
          and "não há" in (so_resi.auto_selected_reason or "").lower(),
          so_resi.auto_selected_reason)


# ===========================================================================
# [GB2b] FILTRADAS — vencida nunca entra na lista de opcoes
# ===========================================================================
def gate_GB2b():
    _p("\n[GB2b] FILTRADAS -- 2 auto vigentes + 1 resi VENCIDA -> 2 opcoes, nunca 3")
    caso = casos_sinteticos()["duas_auto_mais_uma_resi_vencida"]
    inteira = listar(caso, incluir_vencidas=True)
    check("[GB2b] a lista crua tem as 3 (o filtro e da escolha, nao da fonte)",
          len(inteira.itens) == 3, len(inteira.itens))
    escolha = escolher(caso, ramo=None)
    medir("opcoes_com_uma_vencida_no_meio", len(escolha.opcoes))
    check("[GB2b] 🔴 a escolha oferece 2 opcoes, nao 3",
          escolha.status == "ambiguous_policy" and len(escolha.opcoes) == 2,
          (escolha.status, len(escolha.opcoes)))
    check("[GB2b] nenhuma opcao esta VENCIDA ou CANCELADA",
          all(o.vigencia.situacao not in ("VENCIDA", "CANCELADA") for o in escolha.opcoes),
          [o.vigencia.situacao for o in escolha.opcoes])
    check("[GB2b] e a vencida entra no historico_oculto",
          escolha.historico_oculto == 1, escolha.historico_oculto)

    # As 3 listagens REAIS: nenhuma opcao vencida em nenhuma delas.
    vencidas_oferecidas = 0
    for nome, real in sorted(listagens_reais().items()):
        e = escolher(real, ramo=None)
        vencidas_oferecidas += sum(
            1 for o in e.opcoes if o.vigencia.situacao in ("VENCIDA", "CANCELADA"))
        check("[GB2b] %s: a escolha resolve em `found` (1 vigente)" % nome,
              e.status == "found", (e.status, len(e.opcoes)))
    medir("vencidas_oferecidas_como_opcao_no_acervo_real", vencidas_oferecidas)
    check("[GB2b] 📊 zero vencidas oferecidas como opcao nas 3 listagens reais",
          vencidas_oferecidas == 0, vencidas_oferecidas)


# ===========================================================================
# [GB2c] SEM VIGENTE — a frase da §6.2
# ===========================================================================
def gate_GB2c():
    _p("\n[GB2c] SEM VIGENTE -- a resposta NAO e 'nao encontrei' (§6.2)")
    caso = casos_sinteticos()["sem_vigente_tres_vencidas"]
    escolha = escolher(caso, ramo=None)
    check("[GB2c] 0 vigentes + 3 vencidas -> status `sem_vigente`",
          escolha.status == "sem_vigente", escolha.status)
    check("[GB2c] nenhuma opcao e oferecida (vencida nunca vira opcao)",
          escolha.opcoes == (), [o.apolice_ref for o in escolha.opcoes])
    ultima = escolha.ultima_vigente
    check("[GB2c] 🔴 `ultima_vigente` e a de FIM mais recente (14/08/2026), "
          "nao a primeira da lista",
          ultima is not None and ultima.vigencia.fim == date(2026, 8, 14),
          ultima.vigencia.fim if ultima else None)
    frase = escolha.frase_sem_vigente or ""
    check("[GB2c] a frase traz a DATA em que a ultima valeu", "14/08/2026" in frase, frase)
    check("[GB2c] a frase traz o nome HUMANO da seguradora (Allianz, nao ALLI)",
          "Allianz" in frase, frase)
    check("[GB2c] a frase diz que hoje nao ha vigente e OFERECE o historico",
          "nenhuma apólice vigente" in frase and "histórico" in frase, frase)
    check("[GB2c] ⛔ e ela NAO diz 'nao encontrei'",
          "não encontrei" not in frase.lower() and "nao encontrei" not in frase.lower(), frase)
    medir("frase_sem_vigente_tem_data_e_seguradora", int("14/08/2026" in frase and "Allianz" in frase))


# ===========================================================================
# [GB2d] O PORQUE — `auto_selected_reason` em 100% dos `found`
# ===========================================================================
def gate_GB2d():
    _p("\n[GB2d] O PORQUE -- a escolha DIZ por que esta certa (CLAUDE.md §9.5)")
    casos = dict(casos_sinteticos())
    casos.update(listagens_reais())
    achados = 0
    total = 0
    problemas = []
    for nome, caso in sorted(casos.items()):
        if nome.startswith("_"):
            continue
        for ramo in (None, "auto", "resi"):
            escolha = escolher(caso, ramo=ramo)
            if escolha.status != "found":
                continue
            total += 1
            motivo = (escolha.auto_selected_reason or "").strip()
            if motivo:
                achados += 1
            else:
                problemas.append(("sem motivo", nome, ramo))
                continue
            ruim = problemas_no_motivo(motivo)
            if ruim:
                problemas.append((nome, ramo, motivo, ruim[:3]))
    medir("found_com_motivo", "%d/%d" % (achados, total))
    check("[GB2d] 🔴 `auto_selected_reason` presente em 100%% dos `found` (%d de %d)"
          % (achados, total), total > 0 and achados == total, problemas[:4])
    check("[GB2d] e todos passam na regua de lingua que JA existe",
          not problemas, problemas[:4])

    # O PAR DA REGUA: ela CONSEGUE reprovar. Sem isto, "0 problemas" tanto pode
    # ser texto bom quanto detector quebrado (CLAUDE.md §9.3).
    check("[GB2d] PAR-REGUA: a regua reprova `ramo_canonico@3` (snake_case + versao)",
          bool(problemas_no_motivo("apolice escolhida por ramo_canonico@3")),
          problemas_no_motivo("apolice escolhida por ramo_canonico@3"))
    check("[GB2d] PAR-REGUA: e APROVA a frase humana que o produto escreve",
          not problemas_no_motivo("única apólice vigente de auto; 2 apólices antigas ocultadas"),
          problemas_no_motivo("única apólice vigente de auto; 2 apólices antigas ocultadas"))

    # O motivo conta o historico INTEIRO, truncamento incluido.
    empresa = escolher(listagens_reais()["empresa_11_apolices"], ramo=None)
    check("[GB2d] 📊 o motivo da empresa 11/10 diz 10 ocultadas, nao 9 "
          "(a 11a, que a fonte truncou, conta)",
          "10 apólices antigas" in (empresa.auto_selected_reason or ""),
          empresa.auto_selected_reason)


# ===========================================================================
# [GB2e] O STATUS — `"ativo"` numa vencida nao a torna opcao
# ===========================================================================
def gate_GB2e():
    _p("\n[GB2e] O STATUS -- o `policy_status` do fornecedor nao decide")
    caso = casos_sinteticos()["uma_vencida_marcada_ativa"]
    escolha = escolher(caso, ramo=None)
    check("[GB2e] a vencida marcada 'ativo' NAO vira opcao -> `found` na outra",
          escolha.status == "found", (escolha.status, len(escolha.opcoes)))
    check("[GB2e] e a escolhida e a que esta VIGENTE por DATA",
          escolha.apolice is not None and escolha.apolice.apolice_ref == "infocap:1:N2",
          escolha.apolice.apolice_ref if escolha.apolice else None)

    # O par: o mesmo cliente com a vencida VIGENTE viraria ambiguidade legitima.
    par = {
        "documents_count": 2, "status": "ambiguous_policy",
        "apolices": [
            dict(caso["apolices"][0], inicio="01/01/2026", fim="01/01/2027"),
            caso["apolices"][1],
        ],
    }
    escolha_par = escolher(par, ramo=None)
    check("[GB2e] PAR: se a MESMA apolice estivesse vigente, viraria ambiguidade",
          escolha_par.status == "ambiguous_policy" and len(escolha_par.opcoes) == 2,
          (escolha_par.status, len(escolha_par.opcoes)))


GATES = {
    "GB2a": gate_GB2a,
    "GB2b": gate_GB2b,
    "GB2c": gate_GB2c,
    "GB2d": gate_GB2d,
    "GB2e": gate_GB2e,
}


MUTACOES = [
    # M-B2a: ramo DIFERENTE contado como ambiguidade -> 1 auto + 1 resi com
    #        pedido de auto volta a perguntar, que e o defeito de 09-11/09.
    ("M-B2a", "app/providers/policy_data_provider.py",
     "        if do_ramo:\n            candidatas = do_ramo",
     "        if do_ramo:\n            candidatas = elegiveis",
     "GB2a"),
    # M-B2b: a vencida volta a ser opcao -> 3 opcoes onde deviam ser 2.
    ("M-B2b", "app/providers/policy_data_provider.py",
     "    elegiveis = tuple(a for a in itens if a.vigencia.situacao not in SITUACOES_OCULTAS)",
     "    elegiveis = tuple(itens)",
     "GB2b"),
    # M-B2c: `auto_selected_reason` vazio -> a escolha deixa de dizer por que, e
    #        o corretor volta a nao ter como contestar a apolice escolhida.
    ("M-B2c", "app/providers/policy_data_provider.py",
     "            auto_selected_reason=_motivo_da_escolha(\n"
     "                escolhida, elegiveis=elegiveis, ocultas=ocultas,\n"
     "                historico_oculto=historico_oculto, familia_pedida=familia_pedida,\n"
     "                humanizar_seguradora=humanizar_seguradora, humanizar_ramo=humanizar_ramo,\n"
     "            ),",
     "            auto_selected_reason=None,",
     "GB2d"),
    # M-B2d: `ultima_vigente` passa a ser a PRIMEIRA vencida da lista em vez da
    #        de fim mais recente -> a frase da §6.2 cita a apolice errada.
    ("M-B2d", "app/providers/policy_data_provider.py",
     "        ultima = max(vencidas, key=lambda a: a.vigencia.fim) if vencidas else None",
     "        ultima = vencidas[0] if vencidas else None",
     "GB2c"),
    # M-B2e: o historico do motivo volta a contar so as vencidas VISTAS -> a
    #        empresa de 11 apolices diz 9 quando sao 10.
    ("M-B2e", "app/providers/policy_data_provider.py",
     "    if historico_oculto <= 0:\n        return base",
     "    historico_oculto = len(vencidas) + len(canceladas)\n    if historico_oculto <= 0:\n        return base",
     "GB2d"),
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
        _p("  M-B2 -- SO PERGUNTA COM DUAS DO MESMO RAMO  (SPEC-EXTRA-001.1 BLOCO B)")
        _p("=" * 78)
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
        _H._devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_so_pergunta_com_duas_do_mesmo_ramo():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
