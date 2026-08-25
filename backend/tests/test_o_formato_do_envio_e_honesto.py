# -*- coding: utf-8 -*-
"""O que sai no fio é o que a captura mostra — SPEC-092, BLOCO D.3.

🔴 **A prova de 03/08 mediu que o WhatsApp ACEITA. Não mediu que os campos estão
certos.** São coisas diferentes, e a SPEC-092 §3.1.1 nomeia duas suspeitas.
📊 Medi as duas, e **uma delas era uma armadilha**.

## `version` — a SPEC está certa, e agora tem número

```
o código mandava            version = 1     (💭 "o fork do Baileys usa 1")
as 4 capturas live yelum    version = 3     (03, 07, 17 e 19/08, 4 de 4)
```

⚠️ E trocar isto **não põe em risco a prova de 03/08**: a rodada 1 daquele dia
variou `version` entre cinco formas e as cinco deram o mesmo 479. *"Fator que
não muda o resultado não é a causa"* corta para os dois lados — ele também não
é a causa do 200.

## 🔴 `format` — a SPEC manda consertar o que NÃO CHEGA AO FIO

📊 Seguindo o campo até o fim, em 25/08/2026:

```
1. montar_nfm_reply põe  body.format = "EXTENSIONS"  no dicionário waE2E
2. send_native_flow_response ACHATA esse dicionário e manda ao GO só
      {number, name, paramsJSON, wrapInDocumentWithCaption, version?, body?}
   ← `format` fica para trás AQUI
3. e o patch 0005 do GO fixa em código
      Format: waE2E.InteractiveResponseMessage_Body_DEFAULT.Enum()
```

> **Trocar `"EXTENSIONS"` por `"1"` no Python não muda um byte do que sai — e o
> teste ficaria verde.** É a classe de defeito que esta SPEC existe para matar,
> aparecendo dentro do próprio conserto dela.

📊 E o nome estava certo o tempo todo: a captura mostra `body.format = 1`, que é
o valor numérico de `EXTENSIONS` no enum do protobuf. **Quem manda o valor
errado é o GO**, com `DEFAULT` (0). O conserto de verdade é um patch 0007 e
exige rebuild de imagem — está na CAIXA DO FOUNDER.

## O que este arquivo guarda

> **O contrato do fio é uma lista fechada de chaves.** Campo novo que alguém
> ache que está mandando, e não está, quebra aqui.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROVIDER_PY = RAIZ / "app" / "services" / "whatsapp" / "providers" / "evolution_go.py"
PATCH_GO = (RAIZ.parent / "infra" / "evolution-go-autobrokers" / "patches"
            / "0005-send-interactive-response.patch")


def _carregar():
    nomes = ("app", "app.services", "app.services.whatsapp",
             "app.services.whatsapp.providers")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location("_spec092_go", str(PROVIDER_PY))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


G = _carregar()

#: 📊 A lista FECHADA do que a rota do GO recebe. Medida no achatador
#: (`send_native_flow_response`) e conferida contra o `InteractiveResponseStruct`
#: do patch 0005.
CHAVES_DO_FIO = {"number", "name", "paramsJSON", "wrapInDocumentWithCaption",
                 "version", "body"}


def _corpo_enviado(**extra):
    """O corpo REAL que iria para o GO, sem rede."""
    capturado = {}

    class _Falso:
        def _post(self, rota, corpo):
            capturado["rota"] = rota
            capturado["corpo"] = corpo
            return G.SendResult(ok=True)

    p = object.__new__(G.EvolutionGoProvider)
    p._post = _Falso()._post
    kwargs = dict(flow_token="tok:1:2", params={"rb_X": "1"},
                  nome_do_envelope="galaxy_message")
    kwargs.update(extra)
    p.send_native_flow_response("5500000000000", **kwargs)
    return capturado


# ---------------------------------------------------------------------------
# 1. O `version` — o conserto que É conserto
# ---------------------------------------------------------------------------

def test_o_version_e_o_MEDIDO_e_nao_o_chutado():
    assert G.VERSION_DA_RESPOSTA_DE_FLOW == 3, (
        "📊 as 4 capturas `live` da Yelum trazem version=3. Se este número "
        "mudou, mude a MEDIÇÃO junto — e diga onde ela foi feita")
    montado = G.montar_nfm_reply(flow_token="t", params={"a": "1"},
                                 nome_do_envelope="galaxy_message")
    v = montado["interactiveResponseMessage"]["nativeFlowResponseMessage"]["version"]
    assert v == 3, f"o padrão de `montar_nfm_reply` continua {v!r}"


def test_o_version_CHEGA_ao_corpo_que_vai_para_o_GO():
    """🔴 A metade positiva: este campo **atravessa**, ao contrário do `format`.

    Sem esta asserção, o teste do `format` abaixo passaria num mundo em que
    NENHUM campo atravessa — e não provaria nada sobre o `format`.
    """
    corpo = _corpo_enviado()["corpo"]
    assert corpo.get("version") == 3, (
        f"o `version` não chegou ao corpo do GO: {corpo.get('version')!r}")


# ---------------------------------------------------------------------------
# 2. O `format` — o conserto que NÃO seria conserto
# ---------------------------------------------------------------------------

def test_o_format_NAO_chega_ao_fio_e_isso_esta_ESCRITO():
    """⛔ O guarda que impede o conserto de mentira.

    A §D.3 da SPEC manda trocar o valor de `format`. Quem trocar vai ver teste
    verde e nada mudando no fio. Este teste explica por que, na mensagem de
    falha, para quem estiver lendo às três da manhã.
    """
    corpo = _corpo_enviado()["corpo"]
    assert "format" not in corpo, (
        "🔴 `format` passou a ir no corpo do GO. Se foi de propósito, o patch "
        "0007 do GO precisa LER esse campo — hoje ele fixa "
        "`InteractiveResponseMessage_Body_DEFAULT` em código, e o valor novo "
        "seria ignorado em silêncio. Atualize os dois lados, ou nenhum.")
    montado = G.montar_nfm_reply(flow_token="t", params={"a": "1"},
                                 nome_do_envelope="galaxy_message")
    assert montado["interactiveResponseMessage"]["body"]["format"] == "EXTENSIONS", (
        "o waE2E deixou de descrever o formato correto — 📊 a captura real "
        "traz `body.format = 1`, que É `EXTENSIONS` no enum do protobuf")


def test_o_GO_ainda_fixa_o_format_em_codigo():
    """📊 A outra metade da medição, lida na fonte do patch.

    ⚠️ Este guarda fica VERMELHO no dia em que alguém consertar o GO — e é o
    que se quer: nesse dia, a história acima muda e tem de ser reescrita, em
    vez de continuar afirmando algo que deixou de ser verdade (`CLAUDE.md` §9.3).
    """
    if not PATCH_GO.exists():
        import pytest

        pytest.skip("patch 0005 fora da árvore")
    fonte = PATCH_GO.read_text(encoding="utf-8", errors="ignore")
    assert "InteractiveResponseMessage_Body_DEFAULT" in fonte, (
        "o GO parou de fixar `DEFAULT`. Se ele passou a LER o campo, o Python "
        "tem de mandá-lo — e este arquivo inteiro precisa ser reescrito com a "
        "medição nova")


# ---------------------------------------------------------------------------
# 3. O CONTRATO DO FIO — lista fechada
# ---------------------------------------------------------------------------

def test_o_corpo_do_GO_tem_a_lista_FECHADA_de_chaves():
    """🔴 Campo novo no corpo é mudança de contrato com um binário que roda
    noutra imagem. Ele não pode entrar em silêncio."""
    corpo = _corpo_enviado()["corpo"]
    sobrando = set(corpo) - CHAVES_DO_FIO
    assert not sobrando, (
        f"chave(s) nova(s) no corpo do GO: {sorted(sobrando)}. O GO só lê o que "
        "o `InteractiveResponseStruct` do patch declara; o resto é ignorado em "
        "silêncio, que é a pior forma de campo novo")
    for obrigatoria in ("number", "name", "paramsJSON", "wrapInDocumentWithCaption"):
        assert obrigatoria in corpo, f"sumiu `{obrigatoria}` do corpo"


def test_o_embrulho_CONTINUA_ligado():
    """📊 É a diferença entre 200 e 479, medida com linha de controle em
    03/08/2026. Sem ele o WhatsApp recusa a mensagem inteira — em silêncio para
    o cliente, com um número para nós."""
    corpo = _corpo_enviado()["corpo"]
    assert corpo.get("wrapInDocumentWithCaption") is True, (
        "o embrulho `DocumentWithCaption` saiu — a prova de 03/08 mostrou que "
        "sem ele são 479 em todas as formas testadas")


def test_o_paramsJSON_viaja_como_TEXTO_e_nao_e_reserializado():
    """🔴 Re-serializar reordena chaves e reescreve acentos. O `paramsJSON`
    é montado UMA vez e viaja byte a byte."""
    corpo = _corpo_enviado(params={"ckb_X": ["a"], "rb_Y": "1"})["corpo"]
    pj = corpo["paramsJSON"]
    assert isinstance(pj, str), f"`paramsJSON` virou {type(pj).__name__}"
    assert json.loads(pj)["rb_Y"] == "1"


def test_CONTROLE_o_corpo_CONSEGUE_variar():
    """§9.3 — prove que `_corpo_enviado` reflete a entrada. Um dublê que
    devolvesse sempre o mesmo dicionário passaria em tudo acima."""
    a = _corpo_enviado(flow_token="tok:A")["corpo"]["paramsJSON"]
    b = _corpo_enviado(flow_token="tok:B")["corpo"]["paramsJSON"]
    assert a != b, "o corpo não muda com a entrada — o dublê não mede nada"
