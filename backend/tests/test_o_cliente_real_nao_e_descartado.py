# -*- coding: utf-8 -*-
"""O cliente real deixa de ser descartado em silêncio — SPEC-093, BLOCO B.

📊 **O problema, medido:** `ATTENDANT_INBOUND_ALLOWLIST` tinha **um** número em
produção, e [webhook.py:524](../app/api/webhook.py#L524) descarta **antes** do
`get_or_create_user` de `:529`.

> ⛔ **Nem o Espelho aprende.** O cliente escreve, e para o produto ele **nunca
> escreveu.**

## 🔴 E o item 1 do BLOCO B saiu, porque já estava feito

📊 Medido no aquecimento, executando a função real:

```
allowlist VAZIA    → telefone qualquer passa?   True
allowlist None     → True
allowlist 1 número → False
```

`if not entries: return True` já existia, e a docstring já dizia. **Esvaziar a
variável é 🧑 ação do Founder, não código.** O que o bloco entrega é o resto:
tornar o filtro **observável** e devolver ao alarme de deriva o destino próprio.

## ⚠️ E os dois blocos colidiam

📊 `route_sentinel._founder_alert_number` montava o destino do alerta de deriva
com `os.getenv("ATTENDANT_INBOUND_ALLOWLIST").split(",")[0]`.

> 🔴 Esvaziar a allowlist — que é o objetivo do bloco — **apagaria em silêncio o
> alarme que avisa quando um corredor sai do lugar**, no exato dia em que
> corredores começam a atender cliente real.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SEG_PY = RAIZ / "app" / "services" / "whatsapp" / "channel_security.py"
SENT_PY = RAIZ / "app" / "services" / "atlas" / "route_sentinel.py"
MAIN_PY = RAIZ / "app" / "main.py"
WEBHOOK_PY = RAIZ / "app" / "api" / "webhook.py"


def _carregar(nome: str, caminho: Path, pacotes=("app", "app.services",
                                                 "app.services.whatsapp")):
    injetados = [n for n in pacotes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in pacotes}
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


SEG = _carregar("_spec093_seg", SEG_PY)

#: 💭 Sintéticos. Nenhum telefone real entra num arquivo de teste.
NOSSO = "5511900000001"
QUALQUER = "5547988887777"


@pytest.fixture(autouse=True)
def _zera_contador():
    SEG._DESCARTADOS_PELA_ALLOWLIST["total"] = 0
    yield


# ---------------------------------------------------------------------------
# ① e ② — quem passa, quem é barrado, e o barrado é CONTADO
# ---------------------------------------------------------------------------

def test_GATE_1_allowlist_vazia_deixa_qualquer_telefone_passar(monkeypatch):
    """⛔ Gate ①. É o estado que produção quer, e ele já funcionava — este
    guarda existe para que continue funcionando."""
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", "")
    assert SEG.attendant_inbound_allowed(QUALQUER) is True
    assert SEG.descartes_da_allowlist() == 0, "contou um descarte que não houve"


def test_GATE_2_com_um_numero_o_resto_e_descartado_E_CONTADO(monkeypatch):
    """⛔ Gate ②. 🔴 O `E CONTADO` é a metade nova.

    📊 Hoje o descarte é um `return` mudo. Se a allowlist ficar mal configurada
    no dia do piloto, o sintoma é *"ninguém escreveu"* — **indistinguível de um
    dia fraco.**
    """
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", NOSSO)
    assert SEG.attendant_inbound_allowed(NOSSO) is True
    assert SEG.descartes_da_allowlist() == 0

    assert SEG.attendant_inbound_allowed(QUALQUER) is False
    assert SEG.descartes_da_allowlist() == 1, "o descarte não foi contado"
    SEG.attendant_inbound_allowed(QUALQUER)
    assert SEG.descartes_da_allowlist() == 2, "o contador não acumula"


def test_CONTROLE_o_contador_NAO_sobe_para_quem_passa(monkeypatch):
    """§9.3 — um contador que subisse sempre passaria no teste acima e diria
    que a allowlist barra todo mundo, inclusive quem ela deixa entrar."""
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", NOSSO)
    for _ in range(5):
        SEG.attendant_inbound_allowed(NOSSO)
    assert SEG.descartes_da_allowlist() == 0


def test_o_nono_digito_continua_casando(monkeypatch):
    """📊 O WhatsApp entrega `5547XXXXXXXX` para contas antigas e
    `55479XXXXXXXX` para novas. Uma allowlist que erre por grafia barra o
    próprio dono — e quem for barrado vai afrouxá-la, não corrigi-la."""
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", "5547999998888")
    assert SEG.attendant_inbound_allowed("554799998888") is True
    assert SEG.attendant_inbound_allowed("5547999998888") is True
    assert SEG.descartes_da_allowlist() == 0


# ---------------------------------------------------------------------------
# ③ — o contador sobe sem que telefone nenhum apareça
# ---------------------------------------------------------------------------

def test_GATE_3_o_telefone_NAO_aparece_em_log_nem_no_contador(monkeypatch, caplog):
    """⛔ Gate ③. `CLAUDE.md` §13.3 — presença, nunca conteúdo."""
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", NOSSO)
    with caplog.at_level(logging.DEBUG):
        SEG.attendant_inbound_allowed(QUALQUER)
    tudo = " ".join(r.getMessage() for r in caplog.records)
    assert QUALQUER not in tudo, "o telefone barrado apareceu em log"
    assert QUALQUER[-8:] not in tudo, "o final do telefone apareceu em log"
    assert SEG.descartes_da_allowlist() == 1

    # e o contador é um NÚMERO, nunca uma lista de quem foi barrado
    assert isinstance(SEG._DESCARTADOS_PELA_ALLOWLIST["total"], int)
    assert set(SEG._DESCARTADOS_PELA_ALLOWLIST) == {"total"}, (
        "o contador virou coleção — guardar QUEM foi barrado é guardar telefone")


def test_o_descarte_do_webhook_tambem_nao_imprime_telefone():
    """A outra ponta: a linha que descarta, no `webhook.py`."""
    fonte = WEBHOOK_PY.read_text(encoding="utf-8")
    i = fonte.index("inbound fora da ATTENDANT_INBOUND_ALLOWLIST")
    linha = fonte[fonte.rindex("\n", 0, i) + 1:fonte.index("\n", i)]
    for proibido in ("payload.phone", "{phone", "%s", "+ phone"):
        assert proibido not in linha, (
            f"a linha de descarte passou a imprimir `{proibido}`: {linha.strip()}")


# ---------------------------------------------------------------------------
# ④ — o /health diz que ela existe, sem revelar um dígito
# ---------------------------------------------------------------------------

def test_GATE_4_o_health_diz_ATIVA_e_TAMANHO_sem_um_digito(monkeypatch):
    """⛔ Gate ④."""
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", "")
    assert SEG.allowlist_ativa() is False
    assert SEG.allowlist_tamanho() == 0

    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", NOSSO + "," + QUALQUER)
    assert SEG.allowlist_ativa() is True
    assert SEG.allowlist_tamanho() == 2, "o tamanho não bate"


def test_o_health_NAO_expoe_a_lista():
    """🔴 O sinal é presença e tamanho. Um `/health` que devolvesse a lista
    publicaria telefone de gente numa rota de diagnóstico."""
    fonte = MAIN_PY.read_text(encoding="utf-8")
    i = fonte.index('sinais["allowlist_ativa"]')
    trecho = fonte[i:i + 600]
    assert 'sinais["allowlist_numeros"]' not in fonte
    assert "ATTENDANT_INBOUND_ALLOWLIST" not in trecho, (
        "o /health passou a ler a variável direto — leia pelas funções, que "
        "devolvem presença e tamanho")
    for chave in ("allowlist_ativa", "allowlist_tamanho", "allowlist_descartes"):
        assert f'sinais["{chave}"]' in fonte, f"sumiu o sinal `{chave}`"


# ---------------------------------------------------------------------------
# ⓪ — 🔴 O ALERTA DE DERIVA SOBREVIVE À ALLOWLIST VAZIA
# ---------------------------------------------------------------------------

def _sentinela():
    return _carregar("_spec093_sent", SENT_PY,
                     pacotes=("app", "app.services", "app.services.atlas"))


def test_GATE_0_allowlist_vazia_e_o_alerta_AINDA_chega(monkeypatch):
    """⛔ Gate ⓪, e ele é o que impede o BLOCO B de apagar um alarme.

    📊 `_founder_alert_number` montava o destino com o primeiro item da
    allowlist. Esvaziá-la — que é o objetivo deste bloco — devolvia `""`:
    alerta para ninguém. E há **14 linhas de `route_drift` de 25/08**, todas
    `structural`/`escalated` com `needs_founder=true`.
    """
    S = _sentinela()
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", "")
    monkeypatch.setenv("ATLAS_ALERTA_DESTINO", NOSSO)
    assert S._founder_alert_number() == NOSSO, (
        "com a allowlist vazia o alerta de deriva ficou sem destino")


def test_o_destino_PROPRIO_vence_a_heranca(monkeypatch):
    """Duas responsabilidades numa variável é o defeito; usá-la para as duas é
    o sintoma. A variável própria vence sempre."""
    S = _sentinela()
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", QUALQUER)
    monkeypatch.setenv("ATLAS_ALERTA_DESTINO", NOSSO)
    assert S._founder_alert_number() == NOSSO


def test_a_HERANCA_continua_funcionando_e_AVISA(monkeypatch, caplog):
    """⚠️ A herança fica de propósito: tirá-la hoje quebraria o alerta AGORA,
    porque `ATLAS_ALERTA_DESTINO` ainda não está no ambiente.

    🔴 Mas ela avisa — para que o dia em que a allowlist esvaziar o log **diga**
    que o alerta ficou sem destino, em vez de o alarme simplesmente parar.
    """
    S = _sentinela()
    monkeypatch.delenv("ATLAS_ALERTA_DESTINO", raising=False)
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", NOSSO)
    with caplog.at_level(logging.WARNING):
        assert S._founder_alert_number() == NOSSO
    assert any("heran" in r.getMessage().lower() for r in caplog.records), (
        "a herança passou a ser silenciosa — e aí ninguém descobre que o "
        "destino do alerta depende da allowlist")


def test_SEM_NENHUM_dos_dois_o_produto_GRITA(monkeypatch, caplog):
    """🔴 O pior caso tem de ser o mais barulhento: alarme sem destino é
    alarme que não existe, e isso não pode ser descoberto depois."""
    S = _sentinela()
    monkeypatch.delenv("ATLAS_ALERTA_DESTINO", raising=False)
    monkeypatch.setenv("ATTENDANT_INBOUND_ALLOWLIST", "")
    with caplog.at_level(logging.ERROR):
        assert S._founder_alert_number() == ""
    assert any("SEM DESTINO" in r.getMessage() for r in caplog.records), (
        "o alerta ficou sem destino em silêncio")
