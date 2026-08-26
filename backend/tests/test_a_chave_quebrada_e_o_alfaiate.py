# -*- coding: utf-8 -*-
"""A chave quebrada — e o Alfaiate volta a existir. SPEC-087, BLOCO B.

## 📊 O defeito, medido em 26/08/2026 COM LINHA DE CONTROLE

Mesmo registry, mesmo script — **só a chave muda**:

```
CHAVE DO SENTINELA   get_playbook     CONTROLE: ref real                get_playbook
allianz:todos        None             allianz-residencial-whatsapp@v1   dict
tokio:todos          None             tokio-auto-whatsapp@v1            dict
…                    10 de 10 None    …                                 10 de 10 dict
```

`route_sentinel` montava `f"{insurer_key}:{ramo}"`, e 📊 **100% das linhas de
`route_drift` têm `ramo='todos'`** → `allianz:todos`. O registry usa
`allianz-residencial-whatsapp@v1`.

## 🔴 Uma causa explica os três zeros de uma vez

```
simulator_passed  NULL em 16/16     o simulador nunca rodou
auto_applied      false em 16/16    passed=None é fail-closed
playbook_overlays 0 linhas          apply_auto_overlays nunca é alcançado
```

> ⛔ Ler esses zeros como *"o auto-publish é um risco vivo a desarmar"* é ler ao
> contrário: **eles são o atestado de óbito do Alfaiate.** Não sobra automação
> demais — falta a que existe funcionar.

## ⛔ Mas reanimar sem freio seria pior que o coma

Com a chave certa, `apply_auto_overlays` volta a **poder escrever no corredor**,
e o piloto começa na semana que vem. Então:

```
⛔ o auto-apply NASCE DESLIGADO, por variável, padrão DESLIGADO
🔴 o gate ④ LIGA a variável num teste e prova que o overlay É escrito
   ⚠️ sem isso, "0 overlays" passa por vacuidade
```

> **A arma foi consertada, descarregada, e o gatilho fica com o Founder.**

## ⚠️ E uma honestidade sobre o ambiente

📊 `ura_simulator` **não importa nesta máquina**: `ModuleNotFoundError: fastembed`.
A medição da SPEC (`simulate()` levantando `KeyError`) foi feita em outro
ambiente e **não é reproduzível aqui**. O que este arquivo prova é o defeito
**estrutural** — a chave contra o registry —, que é reproduzível e é a causa.
"""
from __future__ import annotations

import importlib.util as _u
import os
import sys
import types
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SENTINEL_PY = RAIZ / "app" / "services" / "atlas" / "route_sentinel.py"
TAILOR_PY = RAIZ / "app" / "services" / "playbook_tailor.py"


@contextmanager
def _com_o_pacote_app():
    nomes = ("app", "app.services", "app.services.atlas",
             "app.services.intelligence", "app.core")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        yield
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


def _carregar(rel: str, nome: str):
    spec = _u.spec_from_file_location(nome, str(RAIZ / rel))
    mod = _u.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


CP = _carregar("app/services/corridor_playbooks.py", "_cp_087b")

# 🔴 O REGISTRO REAL, NO CAMINHO DE IMPORT DE PRODUÇÃO.
#
# 📊 Medido nesta máquina: `from app.services.corridor_playbooks import _PLAYBOOKS`
# levanta `ModuleNotFoundError: fastembed` — a dependência não está instalada
# aqui, e o pacote `app.services` a arrasta.
#
# ⚠️ SEM ESTA INJEÇÃO O ARQUIVO INTEIRO PASSARIA POR IGNORÂNCIA: `_ref_do_registry`
# devolveria `""` para tudo, e um teste que espera `""` ficaria verde sem nunca
# exercitar a resolução. É a mesma armadilha do `ModuleNotFoundError` engolido
# que a SPEC-085 pagou.
#
# 🔴 `setdefault`, NÃO atribuição: na bateria inteira outro teste pode já ter
# carregado o módulo REAL com sucesso — e aí ele é melhor que a minha cópia.
# Sobrescrever daria duas instâncias do registry na mesma sessão, e a segunda
# apagaria qualquer estado que a primeira tivesse.
sys.modules.setdefault("app.services.corridor_playbooks", CP)

with _com_o_pacote_app():
    SENT = _carregar("app/services/atlas/route_sentinel.py", "_sent_087b")
    TAILOR = _carregar("app/services/playbook_tailor.py", "_tailor_087b")


def test_o_ARNES_esta_de_pe_antes_de_qualquer_assercao():
    """🔴 A prova de que os testes abaixo medem alguma coisa.

    Se o registry não estiver no caminho de import, `_ref_do_registry` devolve
    `""` para tudo — e metade deste arquivo ficaria verde por ignorância.
    """
    assert len(CP._PLAYBOOKS) >= 14, (
        f"o registry carregou {len(CP._PLAYBOOKS)} playbooks — esperava 14+")

    # ⚠️ O QUE IMPORTA NÃO É A IDENTIDADE DO OBJETO.
    #
    # 📊 Medido: na bateria inteira, outro teste carrega o módulo REAL antes
    # deste, e `sys.modules[...] is CP` fica falso — mas o registry está lá e
    # funciona. A primeira versão desta linha reprovava por isso, e reprovar
    # quando ninguém errou ensina a ignorar o guarda.
    no_caminho = sys.modules.get("app.services.corridor_playbooks")
    assert no_caminho is not None, (
        "o registry não está no caminho de import — `_ref_do_registry` "
        "devolveria `\"\"` para tudo e este arquivo inteiro passaria por "
        "ignorância")
    assert len(getattr(no_caminho, "_PLAYBOOKS", {})) >= 14, (
        "o que está no caminho de import não é um registry completo")

    # e a resolução REALMENTE alcança o registry
    assert SENT._ref_do_registry("allianz", "auto"), (
        "o resolvedor não enxerga o registry — todo teste de chave deste arquivo "
        "estaria passando por ignorância")

SEGURADORAS = ["allianz", "porto", "yelum", "hdi", "azul",
               "zurich", "tokio", "bradesco", "mapfre", "alfa"]


# ===========================================================================
# ① a chave RESOLVE — para os 10 mapas ativos
# ===========================================================================

def test_GATE_1_a_chave_resolve_para_TODAS_as_seguradoras():
    """📊 10 de 10, contra `f"{insurer}:{ramo}"` que dava None em 10 de 10."""
    faltando = []
    for seg in SEGURADORAS:
        ref = SENT._ref_do_registry(seg, "todos")
        if not ref or CP.get_playbook(ref) is None:
            faltando.append(seg)
    assert not faltando, (
        f"a chave não resolve para {faltando} — o Alfaiate continua morto ali")


def test_GATE_1b_CONTROLE_a_chave_ANTIGA_nao_resolvia_nenhuma():
    """§9.3 — a prova de que o conserto conserta alguma coisa.

    🔴 Sem esta linha, o gate ① passaria mesmo que a chave antiga já
    funcionasse — e o bloco inteiro seria decorativo.
    """
    resolviam = [s for s in SEGURADORAS if CP.get_playbook(f"{s}:todos") is not None]
    assert resolviam == [], (
        f"a chave antiga resolvia para {resolviam} — a medição que justifica "
        "este bloco está errada")


def test_a_chave_sai_do_REGISTRY_e_nao_de_uma_convencao_montada():
    """⚠️ `CLAUDE.md` §5 — duas formas de nomear a mesma coisa divergem, e foi
    divergindo que o Alfaiate morreu."""
    fonte = SENTINEL_PY.read_text(encoding="utf-8")
    assert 'playbook_ref = f"{insurer_key}:{ramo}"' not in fonte, (
        "a chave montada à mão voltou")
    # ✅ A LIÇÃO MIGROU. A chave deixou de ser UMA e passou a ser a LISTA das
    # refs da seguradora — 📊 100% dos mapas `active` têm `ramo='todos'`, que é o
    # mapa MESCLADO, e medir o corredor de auto contra tela residencial grava um
    # `simulator_passed=false` que PARECE medição.
    assert "refs = _refs_do_registry(insurer_key, ramo)" in fonte
    # ⚠️ JANELA FECHADA pelo fim da função, e não pelo fim do arquivo: o import
    # podia migrar para qualquer função posterior e o guarda continuaria verde.
    i = fonte.index("def _ref_do_registry(")
    corpo = fonte[i:fonte.index(chr(10) + "def ", i + 10)]
    assert "from app.services.corridor_playbooks import _PLAYBOOKS" in corpo, (
        "o resolvedor parou de ler o registry — passou a adivinhar o nome")


def test_o_RAMO_declarado_nao_e_trocado_por_outro():
    """⚠️ Um ramo que não tem playbook devolve `""` — não o playbook de OUTRO
    ramo. Medir o corredor errado é pior que não medir."""
    assert SENT._ref_do_registry("zurich", "residencial") == "", (
        "a zurich residencial (que não existe) foi trocada pela auto")
    # CONTROLE: o ramo que existe resolve
    assert SENT._ref_do_registry("zurich", "auto") == "zurich-auto-whatsapp@v1"
    assert SENT._ref_do_registry("allianz", "residencial") == (
        "allianz-residencial-whatsapp@v1")


def test_ramo_TODOS_prefere_auto_e_e_medido():
    """📊 `ramo='todos'` não é ramo: é a ausência dele. Vale o de maior tráfego."""
    assert SENT._ref_do_registry("allianz", "todos") == "allianz-auto-whatsapp@v1"
    assert SENT._ref_do_registry("hdi", "todos") == "hdi-auto-whatsapp@v1"


def test_seguradora_sem_playbook_devolve_VAZIO():
    """⛔ Inventar uma ref faria o simulador medir outro corredor."""
    assert SENT._ref_do_registry("seguradora_que_nao_existe", "auto") == ""
    assert SENT._ref_do_registry("", "auto") == ""
    # 🔴 E COM `ramo='todos'` TAMBÉM — que é o caminho REAL.
    #
    # ⚠️ A primeira versão só testava `ramo='auto'`, e por isso ficou VERDE sob a
    # mutação que inventava `f"{seg}-auto-whatsapp@v1"` no ramo `todos`. 📊 100%
    # das linhas de `route_drift` têm `ramo='todos'`: era exatamente o caminho
    # que passa em produção que estava sem guarda.
    assert SENT._ref_do_registry("seguradora_que_nao_existe", "todos") == "", (
        "uma seguradora sem playbook ganhou uma ref INVENTADA — o simulador "
        "mediria um corredor que não existe e gravaria o resultado")
    assert SENT._ref_do_registry("", "todos") == ""
    # CONTROLE: uma que EXISTE resolve no mesmo caminho
    assert SENT._ref_do_registry("mapfre", "todos") == "mapfre-auto-whatsapp@v1"


def test_o_SENTINELA_nao_roda_o_alfaiate_sem_ref():
    """E a ausência sai no log — um Alfaiate que não roda em silêncio é o
    defeito que este bloco existe para matar."""
    fonte = SENTINEL_PY.read_text(encoding="utf-8")
    i = fonte.index("refs = _refs_do_registry(insurer_key, ramo)")
    trecho = fonte[i:i + 900]
    assert "if not playbook_ref:" in trecho
    assert "logger.warning" in trecho
    assert "raise LookupError" in trecho, (
        "sem ref, o código seguia para `_alfaiate_with_gate` com string vazia")


# ===========================================================================
# ③ 🔴 o auto-apply está DESLIGADO   ·   ④ 🔴 e a LINHA DE CONTROLE
# ===========================================================================

def _classes_com_um_auto():
    return {"auto": [{"tela": "Aguarde, estamos localizando o seu cadastro.",
                      "acao": "overlay noop"}],
            "approval": [], "never": []}


class _Banco:
    def __init__(self):
        self.overlays = []

    @property
    def client(self):
        return self

    def table(self, n):
        return self

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, l):
        self._op, self._linha = "insert", l
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def execute(self):
        class _R:
            def __init__(s, d):
                s.data = d
        if getattr(self, "_op", "") == "insert":
            self.overlays.append(self._linha)
            return _R([self._linha])
        return _R([])


def _rodar_apply(ligado: bool):
    import asyncio

    banco = _Banco()
    mod = types.ModuleType("app.core.database")
    mod.get_supabase_client = lambda: banco
    antes_env = os.environ.get("ALFAIATE_AUTO_APPLY")
    antes_mod = sys.modules.get("app.core.database")
    if ligado:
        os.environ["ALFAIATE_AUTO_APPLY"] = "true"
    else:
        os.environ.pop("ALFAIATE_AUTO_APPLY", None)
    sys.modules["app.core.database"] = mod
    try:
        with _com_o_pacote_app():
            n = asyncio.run(TAILOR.apply_auto_overlays(
                "allianz-auto-whatsapp@v1", _classes_com_um_auto()))
    finally:
        if antes_env is None:
            os.environ.pop("ALFAIATE_AUTO_APPLY", None)
        else:
            os.environ["ALFAIATE_AUTO_APPLY"] = antes_env
        if antes_mod is None:
            sys.modules.pop("app.core.database", None)
        else:
            sys.modules["app.core.database"] = antes_mod
    return n, banco.overlays


def test_GATE_3_o_auto_apply_esta_DESLIGADO_e_NAO_escreve():
    """⛔ Com a chave consertada, este caminho volta a poder escrever no
    corredor — e o piloto começa na semana que vem."""
    n, overlays = _rodar_apply(ligado=False)
    assert n == 0, f"gravou {n} overlay(s) com o auto-apply desligado"
    assert overlays == [], "escreveu no corredor com o gatilho travado"


def test_GATE_4_CONTROLE_ligando_a_variavel_o_overlay_E_escrito():
    """🔴 **A linha de controle que a SPEC exige, e ela é obrigatória.**

    ⚠️ Sem ela, o gate ③ ("0 overlays") passa por **vacuidade**: um caminho
    quebrado não escreve nada, e ninguém sabe se ele funcionaria.

    > **A arma está descarregada — mas ela dispara quando o Founder carregar.**
    """
    n, overlays = _rodar_apply(ligado=True)
    assert n == 1, (
        f"com a variável LIGADA o overlay não foi escrito ({n}) — o caminho está "
        "quebrado, e o gate ③ estava passando por vacuidade")
    assert len(overlays) == 1
    linha = overlays[0]
    assert linha["playbook_ref"] == "allianz-auto-whatsapp@v1"
    assert linha["kind"] == "noop"
    assert linha["anchor"], "o overlay foi escrito sem âncora"
    # ⛔ e a âncora sai MASCARADA — o BLOCO C, aplicado aqui também
    assert "\\[" not in linha["anchor"] or "[CPF]" not in linha["anchor"]


def test_o_valor_da_variavel_e_uma_LISTA_FECHADA():
    """📊 `bool("false")` é `True` — foi assim que a SPEC-093 quase ligou um
    agente de atendimento com `PATCH {"is_active": "false"}`."""
    antes = os.environ.get("ALFAIATE_AUTO_APPLY")
    try:
        for valor, esperado in (("true", True), ("1", True), ("sim", True),
                                ("on", True), ("TRUE", True),
                                ("false", False), ("0", False), ("no", False),
                                ("", False), ("talvez", False)):
            os.environ["ALFAIATE_AUTO_APPLY"] = valor
            assert TAILOR.auto_apply_ligado() is esperado, (
                f"`{valor}` foi lido como {not esperado}")
        os.environ.pop("ALFAIATE_AUTO_APPLY", None)
        assert TAILOR.auto_apply_ligado() is False, (
            "variável AUSENTE ligou o auto-apply — o padrão tem de ser desligado")
    finally:
        if antes is None:
            os.environ.pop("ALFAIATE_AUTO_APPLY", None)
        else:
            os.environ["ALFAIATE_AUTO_APPLY"] = antes


def test_a_recusa_do_auto_apply_sai_como_INFO_e_nao_alerta():
    """⚠️ Este é o estado NORMAL. Um alerta a cada drift ensinaria todo mundo a
    ignorar o log — e é o log que vai contar se o Alfaiate voltou a viver."""
    fonte = TAILOR_PY.read_text(encoding="utf-8")
    i = fonte.index("if not auto_apply_ligado():")
    trecho = fonte[i:i + 500]
    assert "logger.info" in trecho
    assert "logger.warning" not in trecho and "logger.error" not in trecho


# ===========================================================================
# ⑤ dois tenants
# ===========================================================================

def test_GATE_5_o_alfaiate_nao_tem_como_atravessar_corretoras():
    """✅ `route_drift` e `playbook_overlays` são GLOBAIS de propósito — o Atlas
    é um só, e é decisão registrada.

    🔴 O que este gate guarda é que a **carga** não atravessa: o BLOCO C mascara
    tudo o que entra nessas tabelas, e a âncora do overlay sai mascarada também.
    """
    fonte = TAILOR_PY.read_text(encoding="utf-8")
    assert "ancora_permissiva(text)" in fonte, (
        "a âncora do overlay voltou a ser o texto CRU de uma corretora numa "
        "tabela que todas leem")
    assert "_mascarar(t)" in fonte, "a nota do overlay voltou a ser crua"

    # e o resolvedor de chave não recebe nem usa `company_id` — a chave é global
    # de propósito, e este teste registra isso em vez de deixar como acidente.
    corpo = SENTINEL_PY.read_text(encoding="utf-8")
    i = corpo.index("def _ref_do_registry(")
    assert "company_id" not in corpo[i:i + 2000], (
        "o resolvedor de chave ganhou `company_id` — o Atlas é UM SÓ, e uma "
        "chave por corretora criaria dez mapas onde há um")


def test_ramo_TODOS_mede_TODOS_os_corredores_da_seguradora():
    """🔴 **O achado do red team, e ele derrubava a entrega do BLOCO B.**

    📊 100% dos mapas `active` de `ura_maps` têm `ramo='todos'` — e `todos` não é
    ramo: é o mapa **MESCLADO** da seguradora inteira. Escolher UM ref para ele
    faz o Simulador medir o corredor de AUTO contra um script que contém telas
    RESIDENCIAIS, e gravar um `simulator_passed=false` que **parece medição**.

    ⚠️ Seria o mesmo sintoma que o BLOCO B existe para consertar — os três zeros
    —, só que por outra causa. Atinge as quatro seguradoras com dois ramos:
    allianz, porto, yelum e hdi.
    """
    for seg in ("allianz", "porto", "yelum", "hdi"):
        refs = SENT._refs_do_registry(seg, "todos")
        assert len(refs) >= 2, (
            f"{seg} tem dois ramos e a medição usaria {len(refs)} corredor(es) — "
            "o número diria respeito ao corredor errado")
        assert all(CP.get_playbook(r) is not None for r in refs)

    # ⚠️ E com ramo DECLARADO, é um só — não se mede o que não foi perguntado.
    assert SENT._refs_do_registry("allianz", "residencial") == [
        "allianz-residencial-whatsapp@v1"]
    # 🔴 CONTROLE: seguradora de um ramo só continua com um.
    assert SENT._refs_do_registry("zurich", "todos") == ["zurich-auto-whatsapp@v1"]
    assert SENT._refs_do_registry("nao_existe", "todos") == []


def test_o_veredito_de_CADA_corredor_vai_para_o_detail():
    """📊 A medição que o BLOCO B existe para produzir precisa dizer de QUEM ela
    fala — senão `simulator_passed` é um booleano sem sujeito."""
    fonte = SENTINEL_PY.read_text(encoding="utf-8")
    assert '"vereditos_por_corredor"' in fonte
    assert "for ref in refs:" in fonte, (
        "voltou a medir um corredor só para o mapa mesclado")
