# -*- coding: utf-8 -*-
"""O transporte do formulário nativo — a verdade MEDIDA, fixada como asserção.

SPEC-118, fatia F1. Este arquivo existe por causa de um erro que quase desligou
o único transporte de formulário que o produto tem — e o erro foi de LEITURA.

## 📊 A medição que manda aqui — 26/09/2026, 17:24 (-03), em produção

```
POST /api/whatsapp-integrations/prova-de-formulario   (o botão "Provar envio")
  → HTTP 200 · {"success": true, "vencedora": "embrulho DocumentWithCaption"}
      tentativa 1 — CONTROLE, sem o embrulho ... HTTP 500 "server returned error 479"
      tentativa 2 — com o embrulho ............. HTTP 200
      servidor devolveu Type: "InteractiveResponseMessage",
      ID 3EB02C9B1BFC57E46E3136, destino 5547****4743 (número NOSSO)
```

Três fatos saem daí, e este arquivo guarda os três:

1. **A rota `/send/interactiveResponse` EXISTE e FUNCIONA** na imagem que está
   no ar.
2. **O embrulho `DocumentWithCaptionMessage` é obrigatório** — é ele, e mais
   nada, a diferença entre 200 e 479. A tentativa 1 é a linha de CONTROLE que dá
   direito a essa conclusão (CLAUDE.md §9.2).
3. **O envelope é `galaxy_message`**, ecoado da captura, nunca inventado.

## ⛔ E a armadilha, que é o motivo principal deste guarda existir

📊 O `GET /swagger/doc.json` do MESMO serviço lista **88 rotas**, 12 de `/send`,
e **nenhuma** com `interactive` no caminho — porque o patch 0005 abriu a rota sem
anotação de swagger.

> 🔴 **O catálogo é incompleto. Ausência nele não é ausência na imagem.**

Uma conferência de capacidade contra esse catálogo devolveria `False` para uma
rota viva e desligaria o transporte por conta própria — com a aparência de
prudência e a autoridade de um número. Foi exatamente o que a proposta da SPEC
descreveu como conserto, e o que o COMANDO desmentiu (protocolo §0.4).

⚠️ Por isso o teste 2 abaixo é uma afirmação positiva sobre uma ausência: a rota
NÃO está na lista do catálogo **e** o transporte diz SIM. Quem reintroduzir a
sonda pelo catálogo quebra aqui.

## O que este arquivo NÃO guarda

Que a seguradora aceita a resposta. Isso não foi medido, não se mede sem uma
seguradora do outro lado, e nenhum teste local pode afirmá-lo.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROVIDER_PY = RAIZ / "app" / "services" / "whatsapp" / "providers" / "evolution_go.py"
ROTA_DA_PROVA_PY = RAIZ / "app" / "api" / "whatsapp_integrations.py"


def _carregar():
    """O provider REAL, sem subir os `__init__` da stack de IA.

    O que roda em produção é este arquivo, linha por linha. O que se evita é
    carregar meio produto para conferir um dicionário.
    """
    nomes = ("app", "app.services", "app.services.whatsapp",
             "app.services.whatsapp.providers")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location("_spec118_go", str(PROVIDER_PY))
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

#: 📊 26/09/2026 — a rota que voltou HTTP 200 com o ID 3EB02C9B1BFC57E46E3136.
ROTA_MEDIDA_NO_AR = "/send/interactiveResponse"

#: 📊 O envelope da captura real (18/07/2026, família HDI) e o mesmo da Porto
#: de 21/09/2026: o legado `galaxy_message`. Ecoa-se; não se escolhe.
ENVELOPE_DA_CAPTURA = "galaxy_message"


def _provider_espiao():
    """Um provider real com a BORDA DE HTTP dublada — nada alcança a rede."""
    capturado: dict = {}

    p = object.__new__(G.EvolutionGoProvider)
    p._base_url = "http://nao-usado.invalido"  # noqa: SLF001
    p._token = "t"  # noqa: SLF001

    def _post(rota, corpo):
        capturado["rota"] = rota
        capturado["corpo"] = corpo
        return G.SendResult(ok=True)

    p._post = _post  # noqa: SLF001
    return p, capturado


def _enviar(**extra):
    """O que o motor colocaria no fio, pelo caminho REAL de envio."""
    p, capturado = _provider_espiao()
    kwargs = dict(flow_token="uuid:5500000000000:5500000000001",
                  params={"rb_prova": "1"},
                  nome_do_envelope=ENVELOPE_DA_CAPTURA)
    kwargs.update(extra)
    resultado = p.send_native_flow_response("5500000000000", **kwargs)
    capturado["resultado"] = resultado
    return capturado


# ---------------------------------------------------------------------------
# 1. A ROTA — a que o motor usa é a que foi provada no ar
# ---------------------------------------------------------------------------

def test_a_rota_do_fio_e_a_PROVADA_no_ar():
    """📊 26/09/2026: esta rota devolveu HTTP 200 e o servidor respondeu
    `Type: "InteractiveResponseMessage"` (ID 3EB02C9B1BFC57E46E3136)."""
    assert G.ROTA_DE_FLOW_REPLY_PROVADA == ROTA_MEDIDA_NO_AR, (
        f"a constante da rota virou {G.ROTA_DE_FLOW_REPLY_PROVADA!r}. A rota "
        f"MEDIDA no ar em 26/09/2026 é {ROTA_MEDIDA_NO_AR!r} — se o fork mudou "
        "de caminho, a medição nova vem junto com o valor novo")
    assert G.rota_de_flow_reply({}) == ROTA_MEDIDA_NO_AR, (
        "sem variável de ambiente, o padrão deixou de ser a rota provada")
    # E o motor de envio bate NELA — não numa constante que ninguém usa.
    assert _enviar()["rota"] == ROTA_MEDIDA_NO_AR


# ---------------------------------------------------------------------------
# 2. 🔴 O CATÁLOGO NÃO É A CAPACIDADE — o guarda contra o conserto errado
# ---------------------------------------------------------------------------

def test_o_catalogo_do_swagger_NAO_decide_se_a_rota_existe():
    """⛔ A rota **não está** na lista publicada pelo swagger, e **funciona**.

    📊 As duas metades, medidas no mesmo dia (26/09/2026): o `doc.json` traz 88
    rotas, 12 de `/send`, zero com `interactive`; e a rota respondeu HTTP 200.
    Quem transformar essa ausência em `False` desliga o transporte do produto.
    """
    assert ROTA_MEDIDA_NO_AR not in G.ROTAS_DE_ENVIO_MEDIDAS, (
        "🔴 a rota apareceu na lista do catálogo. Se o patch 0005 ganhou "
        "anotação de swagger, ÓTIMO — mas atualize esta medição junto, senão o "
        "teste abaixo perde o sentido que ele tem hoje")
    p, _ = _provider_espiao()
    assert p.flow_reply_supported() is True, (
        "🔴 `flow_reply_supported()` passou a dizer NÃO com a rota padrão no "
        "lugar. Se alguém acrescentou conferência contra `ROTAS_DE_ENVIO_MEDIDAS` "
        "ou contra o `swagger/doc.json`: essa conferência está ERRADA — 📊 a rota "
        "não está no catálogo e responde 200 (26/09/2026, ID "
        "3EB02C9B1BFC57E46E3136). Desligar o único transporte por leitura de "
        "catálogo é o defeito, não o conserto")


def test_flow_reply_supported_NAO_faz_sonda_de_rede(monkeypatch):
    """⛔ Nenhuma requisição na decisão de "este canal envia formulário?".

    Uma sonda no caminho quente custaria latência em todo acionamento e, pior,
    mediria a coisa errada (o teste acima diz por quê). Aqui a ausência de rede
    deixa de ser promessa de docstring e passa a ser afirmação executável.
    """
    chamadas: list = []

    def _explode(*a, **k):
        chamadas.append(a[:1])
        raise AssertionError("sonda de rede em flow_reply_supported()")

    monkeypatch.setattr(G.requests, "get", _explode)
    monkeypatch.setattr(G.requests, "post", _explode)

    p, _ = _provider_espiao()
    assert p.flow_reply_supported() is True
    assert chamadas == [], f"tocou na rede: {chamadas}"


def test_CONTROLE_com_off_o_transporte_diz_NAO(monkeypatch):
    """🔴 A LINHA DE CONTROLE do teste acima (CLAUDE.md §9.2/§9.3).

    Sem ela, um `flow_reply_supported()` que devolvesse `True` fixo — de novo a
    mentira que esta fatia veio consertar — passaria em tudo. Ela prova que a
    função CONSEGUE dizer não.
    """
    p, _ = _provider_espiao()
    for palavra in ("off", "0", "none", "desligado"):
        monkeypatch.setenv(G.ENV_ROTA_FLOW_REPLY, palavra)
        assert p.flow_reply_supported() is False, (
            f"'{palavra}' deixou de DESLIGAR o envio de formulário — e ele é a "
            "única forma de fechar a porta sem esperar um deploy")


def test_off_recusa_sem_TOCAR_na_rede(monkeypatch):
    """Desligado significa: nenhuma requisição, e o motivo escrito.

    Chutar `/send/text` com o JSON dentro entregaria à seguradora uma parede de
    texto no lugar do formulário — e a URA encerra sozinha. Pausar e chamar uma
    pessoa é pior que atender e muito melhor que queimar a janela.
    """
    tocou: list = []

    def _explode(*a, **k):
        tocou.append(a[:1])
        raise AssertionError("requisição HTTP numa recusa que deveria ser local")

    monkeypatch.setattr(G.requests, "post", _explode)
    monkeypatch.setenv(G.ENV_ROTA_FLOW_REPLY, "off")

    # ⚠️ Sem dublê de `_post` de propósito: é o `_post` de VERDADE que está
    # armado para explodir. Se a recusa não acontecer antes dele, o teste acusa.
    p = object.__new__(G.EvolutionGoProvider)
    p._base_url = "http://nao-usado.invalido"  # noqa: SLF001
    p._token = "t"  # noqa: SLF001
    r = p.send_native_flow_response(
        "5500000000000", flow_token="uuid:1:2", params={"rb_X": "1"},
        nome_do_envelope=ENVELOPE_DA_CAPTURA)

    assert getattr(r, "ok", None) is False
    assert getattr(r, "error", "") == "evolution_go_sem_rota_de_flow_reply", (
        f"o motivo da recusa mudou de nome: {getattr(r, 'error', None)!r}. "
        "`insurer_dispatch_service` traduz essa string para o humano — trocá-la "
        "sem trocar lá deixa o caso parado com motivo em branco")
    assert tocou == [], f"a recusa tocou na rede: {tocou}"


# ---------------------------------------------------------------------------
# 3. 🔴 O EMBRULHO — a diferença entre 200 e 479
# ---------------------------------------------------------------------------

def test_o_embrulho_e_OBRIGATORIO_no_corpo_do_fio():
    """📊 Medido DUAS vezes, com 54 dias de distância e a mesma linha de controle.

    ```
    03/08/2026  6 formas · 5 sem embrulho → 479 · 1 com embrulho → 200
    26/09/2026  tentativa 1 sem embrulho  → 479 · tentativa 2 com ele → 200
    ```

    ⚠️ E a recusa é **silenciosa para o segurado**: o WhatsApp descarta a
    mensagem inteira, e do lado dele parece que o atendimento simplesmente
    parou. Só nós vemos o número.
    """
    corpo = _enviar()["corpo"]
    assert corpo.get("wrapInDocumentWithCaption") is True, (
        "🔴 o embrulho `DocumentWithCaptionMessage` saiu do corpo. 📊 Sem ele "
        "TODAS as formas medidas voltaram 479 (03/08 e 26/09/2026): nenhuma "
        "resposta de formulário chega, e o segurado só vê o atendimento parar")
    # E o mesmo pela função PURA, que é quem decide — e é o que o `/health`
    # publica em `formulario_embrulho_viaja`.
    puro = G.corpo_do_flow_reply(
        to="5500000000000", flow_token="uuid:1:2", params={"rb_X": "1"},
        nome_do_envelope=ENVELOPE_DA_CAPTURA)
    assert puro.get("wrapInDocumentWithCaption") is True


def test_a_prova_do_ar_mantem_a_LINHA_DE_CONTROLE():
    """🔴 A prova que mede o canal só vale com a primeira tentativa SEM embrulho.

    📊 É dela que vem o 479 de controle de 26/09/2026. Se alguém "otimizar" a
    bateria começando pela forma que funciona, a rota continua devolvendo 200 —
    e deixa de PROVAR qualquer coisa, porque não há mais com o que comparar
    (CLAUDE.md §9.2: *sem linha de controle, um acerto se credita ao lugar
    errado*).

    ⚠️ O alvo aqui é a FORMA da declaração (a lista de tentativas), não o
    comportamento de um motor — é o caso que a exceção do CLAUDE.md §9.4 cobre.
    """
    arvore = ast.parse(ROTA_DA_PROVA_PY.read_text(encoding="utf-8"))
    tentativas = None
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "tentativas" for t in no.targets):
            tentativas = ast.literal_eval(no.value)
            break

    assert tentativas, (
        "a bateria `tentativas` da rota de prova desapareceu de "
        f"{ROTA_DA_PROVA_PY.name} — sem ela não há prova de canal nenhuma, e "
        "`flow_reply_supported()` fica sendo a única coisa a olhar (e ela NÃO "
        "mede o canal, de propósito)")
    assert tentativas[0].get("embrulho") is False, (
        "🔴 a primeira tentativa deixou de ser o CONTROLE sem embrulho. Ela "
        "existe para FALHAR com 479; sem isso o 200 da tentativa seguinte não "
        "prova que o embrulho é a causa")
    assert tentativas[1].get("embrulho") is True, (
        "a segunda tentativa deixou de ser a forma vencedora medida "
        "('embrulho DocumentWithCaption', HTTP 200 em 03/08 e 26/09/2026)")


# ---------------------------------------------------------------------------
# 4. O ENVELOPE — se ecoa, não se escolhe
# ---------------------------------------------------------------------------

def test_o_envelope_se_ECOA_e_nao_tem_padrao():
    """Escolher entre `flow` e `galaxy_message` por regra seria apostar — e a
    aposta errada faz a seguradora descartar a resposta em silêncio, gastando a
    única janela antes de a URA encerrar."""
    assert _enviar()["corpo"]["name"] == ENVELOPE_DA_CAPTURA
    # 🔴 A prova de que ECOA em vez de fixar: outro nome atravessa igual.
    assert _enviar(nome_do_envelope="flow")["corpo"]["name"] == "flow", (
        "o envelope parou de ecoar — se ele virou constante, a família que usa "
        "o outro nome passa a receber resposta descartada em silêncio")
    for vazio in ("", None, "   "):
        try:
            G.montar_nfm_reply(flow_token="t", params={"a": "1"},
                               nome_do_envelope=vazio)  # type: ignore[arg-type]
        except ValueError:
            continue
        raise AssertionError(
            f"envelope {vazio!r} foi aceito — um padrão escondido aqui é um "
            "palpite atrás de uma assinatura amigável")


def test_CONTROLE_o_duble_REFLETE_a_entrada():
    """§9.3 — um dublê que devolvesse sempre o mesmo dicionário passaria em tudo
    acima sem medir nada."""
    a = _enviar(flow_token="uuid:A")["corpo"]["paramsJSON"]
    b = _enviar(flow_token="uuid:B")["corpo"]["paramsJSON"]
    assert a != b, "o corpo não muda com a entrada — o dublê não mede nada"
