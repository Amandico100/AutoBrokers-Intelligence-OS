# -*- coding: utf-8 -*-
"""O FIO INTEIRO — do que falta coletar até o protocolo de volta, com o formulário no meio.

SPEC-118, fatia F4 · **A COSTURA**. As fatias anteriores consertaram um elo cada:
a F1 fixou o transporte, a F2 escreveu o mapa da Porto, a F2b ensinou o montador
a responder texto e o portão a cobrar antes, a F3 fez o agente pedir em
português. Nenhuma delas atravessou o fio **inteiro** — e é atravessando que se
descobre que duas peças certas não se encaixam.

## 📊 O ESTADO MEDIDO ANTES DESTA FATIA — 26/09/2026, motor real

```
new_dispatch_session(porto-auto-whatsapp@v1, guincho, <caso completo + pin>)
  → state='ready_to_send'    missing_slots=[]
montar_resposta_de_flow(<mapa REAL da Porto>, <os slots dessa sessão>)
  → ok=False   missing=['latitude', 'longitude']   motivo='sem_chute'
```

🔴 **A sessão nascia PRONTA e o formulário não fechava.** O produto atravessava
~25 telas de URA, a tela do formulário chegava, e o caso ia a uma pessoa **no
último portão antes do protocolo** — com a coordenada do pin do WhatsApp já
dentro da conversa, medida em 6 casas decimais, e ninguém com autorização para
usá-la. Os dois lados estavam certos; o fio, roto.

## O QUE ESTE ARQUIVO ATRAVESSA — os elos ⑤ a ⑭ da §1 da SPEC

```
⑤  o que falta para acionar      corridor_playbooks.missing_slots_for_subservice
⑥  o agente coleta na conversa   insurer_dispatch_service.como_pedir_ao_segurado
⑦  a sessão nasce pronta         insurer_dispatch_service.new_dispatch_session
⑧  a mensagem sai                insurer_dispatch_service.start_dispatch
⑨  a URA responde                corridor_playbooks.match_ura_step (telas REAIS)
⑩  chega o FORMULÁRIO            corridor_playbooks.native_flow(flow_id)
⑪  monta a resposta              corridor_playbooks.montar_resposta_de_flow
                                 evolution_go.montar_nfm_reply
⑫  a resposta SAI                evolution_go.send_native_flow_response
                                 POST /send/interactiveResponse
⑬  a URA segue até o desfecho    o estado volta a `ura`, não a `needs_human`
⑭  o protocolo volta             corridor_playbooks.extract_capture_anchors
```

🔴 **Tudo chama O MOTOR.** O único dublê é `EvolutionGoProvider._post` — a borda
de HTTP, e só ela: o corpo que viaja é montado pelo caminho de produção inteiro
(`send_native_flow_response` → `corpo_do_flow_reply` → `montar_nfm_reply`).
Nenhum helper deste arquivo reimplementa regra de produto (CLAUDE.md §9.4).

⚠️ **E o texto das telas vem do ACERVO**, nunca da imaginação: as telas são
escolhidas de `tests/corpus/telas_reais/porto-auto.jsonl` **pelo próprio motor**
(`match_ura_step`), e o convite do formulário é o de 14/09/2026,
*"Selecione o botão:"* + `[FORMULARIO NATIVO: Preencher]`, com o `flow_id`
`709854848132894` da captura de 21/09/2026
(`tests/fixtures/formulario_porto_21_09.json`).

## 🔴 A LINHA DE CONTROLE — sem ela este arquivo não prova nada

A MESMA travessia, com o MESMO código, **sem a coordenada do pin**, termina em
`needs_human` com o motivo escrito e **zero** bytes no fio. Um teste que só sabe
passar credita o acerto ao lugar errado (CLAUDE.md §9.2).

## O que este arquivo NÃO afirma

Que a Porto **aceita** a resposta. Isso não se mede sem uma seguradora do outro
lado (P-118-04), e nenhum teste local pode afirmá-lo. O que se afirma é que o
produto monta a resposta inteira, pela rota provada no ar, com o embrulho que a
prova de 26/09/2026 mostrou ser a diferença entre 200 e 479.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
PROVIDER_PY = RAIZ / "app" / "services" / "whatsapp" / "providers" / "evolution_go.py"
CORPUS = RAIZ / "tests" / "corpus" / "telas_reais" / "porto-auto.jsonl"
FIXTURE = RAIZ / "tests" / "fixtures" / "formulario_porto_21_09.json"


def _carregar(nome: str, caminho: Path):
    """O arquivo REAL de produção, sem subir os `__init__` da stack de IA."""
    nomes = ("app", "app.services", "app.services.whatsapp",
             "app.services.whatsapp.providers")
    anteriores = {n: sys.modules.get(n) for n in nomes}
    injetados = [n for n in nomes if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


PB = _carregar("app.services.corridor_playbooks", PLAYBOOKS_PY)
DS = _carregar("app.services.insurer_dispatch_service", MOTOR_PY)
GO = _carregar("_spec118_f4_go", PROVIDER_PY)

REF_PORTO = "porto-auto-whatsapp@v1"
SUB = "guincho"
#: 📊 O formulário de endereço da Porto — captura de 21/09/2026 10:24.
FLOW_ENDERECO = "709854848132894"
#: 📊 O envelope LEGADO, ecoado da captura (14 convites da Porto). Nunca escolhido.
ENVELOPE = "galaxy_message"
#: 📊 A coordenada que o pin do WhatsApp entrega, com as 6 casas de
#: `_texto_de_localizacao` (≈ 11 cm). Centro de Florianópolis; nada de ninguém.
PIN_LAT = "-27.588016"
PIN_LON = "-48.544253"
#: Um número NOSSO, de teste. ⛔ Nenhum telefone de pessoa entra aqui.
NUMERO_DA_SEGURADORA = "5500000000000"

CAPTURA = json.loads(FIXTURE.read_text(encoding="utf-8"))

#: Um caso de guincho com tudo verdadeiro e NADA de ninguém: CPF que fecha a
#: conta, placa em formato legal, celular real de Florianópolis. O endereço é o
#: mascarado da própria captura (⚠️ CLAUDE.md §13.9 e a regra de PII).
CASO = {
    "titular_cpf": "52998224725",
    "veiculo_placa": "ABC1D23",
    "local_atual": "R. Exemplo Um, 0, Centro, Florianopolis - SC, 88000-000",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose - SC",
    "problema_descricao": "o carro nao liga",
    "telefone_contato": "48991234567",
    "pessoa_no_local": "quem esta com o veiculo",
    "local_seguro": "sim",
    "quando": "agora",
    "local_complemento": CAPTURA["slots_do_corredor_equivalentes"]["local_complemento"],
    "ponto_referencia": CAPTURA["slots_do_corredor_equivalentes"]["ponto_referencia"],
}

#: Um nome de campo solto no meio de uma frase (`local_bairro`, `rb_NivelDaRua`).
_CHAVE_CRUA = re.compile(r"\b[a-z]{3,}(?:_[a-z]{2,}){1,}\b")


# ===========================================================================
# AS TELAS — escolhidas do ACERVO pelo PRÓPRIO MOTOR
# ===========================================================================

def _telas_do_acervo():
    return [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def _tela(step: str) -> str:
    """A primeira tela REAL da Porto que `match_ura_step` classifica como `step`.

    🔴 Quem escolhe é o motor, não este arquivo: se a âncora do passo mudar, a
    tela muda com ela — e se nenhuma tela do acervo casar, o teste ACUSA em vez
    de inventar uma frase que a Porto nunca escreveu (CLAUDE.md §9.4).
    """
    pb = PB.get_playbook(REF_PORTO)
    for t in _telas_do_acervo():
        achado = PB.match_ura_step(pb, t["text"], SUB)
        if achado and str(achado.get("step")) == step:
            return str(t["text"])
    raise AssertionError(
        f"nenhuma tela real da Porto casa o passo {step!r} — o acervo tem "
        f"{len(_telas_do_acervo())} telas e a âncora deixou de casar")


#: 📊 O convite REAL do formulário de endereço da Porto, no serviço `guincho`:
#: `Selecione o botão:` + o marcador `[FORMULARIO NATIVO: Preencher]` que
#: `evolution_inbound` anexa à bolha que É o formulário. Duas ocorrências no
#: acervo (28/05/2026 e 14/09/2026), e o CTA é o mesmo `cta_do_convite` da
#: captura de 21/09.
_MARCADOR_DO_CONVITE = "[FORMULARIO NATIVO: Preencher]"


def _convite_do_formulario() -> str:
    """⚠️ A tela SEM o marcador também existe no acervo (o `Selecione o botão:`
    seco), e `a_tela_e_formulario` a trata — corretamente — como tela comum: o
    marcador é POR BOLHA. Escolher pela âncora do passo pegaria a errada, e o
    fio pareceria fechado sem nunca ter passado pelo formulário.
    """
    for t in _telas_do_acervo():
        if _MARCADOR_DO_CONVITE in str(t["text"]):
            return str(t["text"])
    raise AssertionError(
        "o convite do formulário de endereço da Porto saiu do acervo de "
        f"{len(_telas_do_acervo())} telas")


def _interativa_do_convite() -> dict:
    """Os metadados da interativa, na forma em que o webhook os entrega.

    📊 6 de 6 convites da Porto trazem `interactive.flow.flow_id`; o
    `flow_token` chega JUNTO e não volta mais (por isso o motor o guarda antes
    de qualquer decisão)."""
    return {
        "kind": "flow",
        "flow": {
            "flow_id": FLOW_ENDERECO,
            "flow_token": f"uuid:{NUMERO_DA_SEGURADORA}:5500000000001",
            "name": ENVELOPE,
            "cta": CAPTURA["envelope"]["cta_do_convite"],
        },
    }


# ===========================================================================
# A TRAVESSIA — uma função, dois casos (com pin e sem), o mesmo código
# ===========================================================================

def _provider_com_a_borda_dublada():
    """O provider REAL de produção com **só** o `_post` dublado.

    Tudo o que decide CONTEÚDO — rota, envelope, embrulho, achatamento do
    `paramsJSON` — continua sendo o código que roda no ar.
    """
    postados: list = []
    p = object.__new__(GO.EvolutionGoProvider)
    p._base_url = "http://nao-usado.invalido"   # noqa: SLF001
    p._token = "t"                              # noqa: SLF001

    def _post(rota, corpo):
        postados.append({"rota": rota, "corpo": corpo})
        return GO.SendResult(ok=True)

    p._post = _post                             # noqa: SLF001
    return p, postados


#: As telas que a URA da Porto manda ANTES do formulário, na ordem do acervo.
#: 📊 Cada uma é um passo que `match_ura_step` reconhece — nenhuma é inventada.
TELAS_ANTES_DO_FORMULARIO = ("confirma_titular", "pedir_cpf", "menu_servico",
                             "no_local")


def _atravessar(*, com_pin: bool) -> dict:
    """O fio do elo ⑤ ao ⑭, com o motor real. Devolve o DIÁRIO da travessia."""
    slots = dict(CASO)
    if com_pin:
        slots["local_latitude"] = PIN_LAT
        slots["local_longitude"] = PIN_LON

    diario: dict = {"telas": [], "saidas_para_a_ura": []}

    # ⑤ + ⑦ — o portão e o nascimento da sessão
    sessao = DS.new_dispatch_session(
        case_id="fio-f4", company_id="fio-f4", playbook_ref=REF_PORTO,
        subservice=SUB, slots=slots)
    diario["estado_ao_nascer"] = sessao["state"]
    diario["falta_ao_nascer"] = list(sessao.get("missing_slots") or [])
    # ⑥ — o que o agente pediria, em português
    diario["como_pediria"] = DS.como_pedir_ao_segurado(
        REF_PORTO, diario["falta_ao_nascer"])
    if sessao["state"] != "ready_to_send":
        diario["desfecho"] = "nao_acionou"
        diario["motivo"] = f"portao:{','.join(diario['falta_ao_nascer'])}"
        return diario

    # ⑧ — a mensagem de abertura sai
    sessao["live"] = True
    sessao = DS.start_dispatch(sessao, sender=lambda t: diario[
        "saidas_para_a_ura"].append(t))
    diario["estado_apos_abrir"] = sessao["state"]

    provider, postados = _provider_com_a_borda_dublada()

    def _flow_sender(**kwargs):
        """O adaptador do webhook, literal (`api/webhook.py:1087`)."""
        r = provider.send_native_flow_response(NUMERO_DA_SEGURADORA, **kwargs)
        return bool(getattr(r, "ok", False))

    def _turno(texto: str, interactive=None):
        antes = len([t for t in sessao.get("transcript") or []
                     if t.get("direction") == "out"])
        DS.handle_insurer_message(
            sessao, texto,
            sender=lambda t: diario["saidas_para_a_ura"].append(t),
            interactive=interactive, flow_sender=_flow_sender)
        depois = [t for t in sessao.get("transcript") or []
                  if t.get("direction") == "out"]
        diario["telas"].append({
            "tela": texto[:70].replace("\n", " | "),
            "estado": sessao.get("state"),
            "respondeu": len(depois) > antes,
            "resposta": (depois[-1].get("text") if len(depois) > antes else None),
        })

    # ⑨ — a URA responde, sobre telas REAIS
    for passo in TELAS_ANTES_DO_FORMULARIO:
        _turno(_tela(passo))
    diario["estado_antes_do_formulario"] = sessao.get("state")

    # ⑩ + ⑪ + ⑫ — o formulário chega, a resposta é montada e vai ao fio
    _turno(_convite_do_formulario(), interactive=_interativa_do_convite())
    diario["estado_apos_o_formulario"] = sessao.get("state")
    diario["motivo"] = str(sessao.get("reason") or "")
    diario["postados"] = postados
    diario["resposta_montada"] = sessao.get("flow_resposta")

    if sessao.get("state") != "ura":
        diario["desfecho"] = "handoff_no_formulario"
        return diario

    # ⑬ + ⑭ — a URA segue, e o protocolo volta
    _turno(_tela("protocolo_recebido"))
    diario["capturado"] = dict(sessao.get("captured") or {})
    diario["desfecho"] = "protocolo"
    diario["sessao"] = sessao
    return diario


@pytest.fixture()
def fio_ligado(monkeypatch):
    """O ambiente em que a resposta PODE sair — e nada além dele.

    ⚠️ `INSURER_DISPATCH_LIVE` e o freio de emergência são os dois portões em
    série do motor. Abri-los **neste processo** é o que faz o teste exercitar o
    caminho de envio; ⛔ nada aqui toca ambiente de produção, e `_post` está
    dublado, então nenhum byte alcança a rede.
    """
    monkeypatch.setenv("INSURER_DISPATCH_LIVE", "true")
    monkeypatch.delenv("ACIONAMENTO_FREIO_DE_EMERGENCIA", raising=False)
    monkeypatch.setenv("DISPATCH_FINALIZE_MODE", "test")
    monkeypatch.setenv("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", REF_PORTO)
    # ⛔ A rede, fechada com barulho: qualquer requisição vira falha de teste.
    def _explode(*a, **k):
        raise AssertionError("⛔ o teste do fio tocou a REDE: %r" % (a[:1],))
    monkeypatch.setattr(GO.requests, "post", _explode)
    monkeypatch.setattr(GO.requests, "get", _explode)
    yield


# ===========================================================================
# 1 · O FIO FECHA — do que falta ao protocolo, com o formulário no meio
# ===========================================================================

def test_o_fio_atravessa_o_formulario_da_porto_ate_o_protocolo(fio_ligado):
    """🔴 A afirmação-título desta fatia, elo a elo.

    📊 Antes da costura este teste falhava em `estado_apos_o_formulario`:
    `needs_human` com `reason='sem_chute:latitude,longitude'` — a sessão nascia
    pronta, a URA rodava, e o caso morria no último portão.
    """
    d = _atravessar(com_pin=True)

    # ⑤ + ⑦ — com o pin e o endereço na mão, nada falta
    assert d["estado_ao_nascer"] == "ready_to_send", (
        "a sessão não nasceu pronta: falta %r — o agente teria de pedir %r"
        % (d["falta_ao_nascer"], d["como_pediria"]))
    # ⑧ — a abertura saiu
    assert d["saidas_para_a_ura"], "nenhuma mensagem de abertura foi ao fio"
    # ⑨ — a URA foi respondida em TODAS as telas reais
    sem_resposta = [t["tela"] for t in d["telas"][:len(TELAS_ANTES_DO_FORMULARIO)]
                    if not t["respondeu"]]
    assert not sem_resposta, f"telas reais que ficaram sem resposta: {sem_resposta}"
    # ⑩ + ⑪ + ⑫ — o formulário foi respondido e o corpo foi ao fio
    assert d["estado_apos_o_formulario"] == "ura", (
        "🔴 O FIO CONTINUA ROTO NO FORMULÁRIO: estado=%r motivo=%r · o que "
        "faltou montar: %r"
        % (d["estado_apos_o_formulario"], d["motivo"],
           [x.get("campo") for x in
            ((d.get("resposta_montada") or {}).get("missing_detail") or [])]))
    assert len(d["postados"]) == 1, (
        "a resposta do formulário não foi ao fio exatamente uma vez: %d"
        % len(d["postados"]))
    # ⑬ + ⑭ — a URA seguiu e o protocolo voltou, pela âncora do corredor
    assert d["desfecho"] == "protocolo", d.get("motivo")
    assert d["capturado"].get("protocol"), (
        "o protocolo da Porto não foi capturado da tela real: %r" % d["capturado"])
    assert re.fullmatch(r"[\d-]{6,}", d["capturado"]["protocol"]), d["capturado"]


def test_o_corpo_que_vai_ao_fio_tem_as_DEZ_chaves_da_captura(fio_ligado):
    """📊 A Porto consome 10 chaves de primeiro nível (3 de 3 capturas).

    Mandar 7 é abrir o chamado sem o endereço inteiro — e a lista é a da
    captura, não a dos componentes de tela (elas diferem em 9 nomes).
    """
    d = _atravessar(com_pin=True)
    assert d["postados"], "nada foi ao fio: %r" % d.get("motivo")
    corpo = d["postados"][0]["corpo"]

    # A rota e o embrulho — o que a prova de 26/09/2026 mediu no ar
    assert d["postados"][0]["rota"] == GO.ROTA_DE_FLOW_REPLY_PROVADA
    assert corpo.get("wrapInDocumentWithCaption") is True, (
        "⛔ o embrulho saiu do corpo — 📊 é ele a diferença entre HTTP 200 e o "
        "erro 479 (medido em 03/08 e reconfirmado em 26/09/2026)")
    assert corpo["name"] == ENVELOPE, corpo["name"]

    params = json.loads(corpo["paramsJSON"])
    esperadas = set(CAPTURA["chaves_da_resposta"]["presentes_em_3_de_3"])
    assert set(params) >= esperadas, (
        "faltaram chaves que a Porto recebe em 3 de 3 capturas: %r"
        % sorted(esperadas - set(params)))
    # 🔴 A coordenada é a DO PIN, com as 6 casas — nunca zero, nunca arredondada.
    assert params["latitude"] == PIN_LAT, params.get("latitude")
    assert params["longitude"] == PIN_LON, params.get("longitude")
    assert params["cep"] == "88000-000", params.get("cep")
    # E o label derivado obedece o molde medido nas 3 capturas.
    assert params["label_endereco_completo"] == (
        f"{params['rua']}, {params['numero_residencia']}, {params['bairro']}, "
        f"{params['cidade']} - {params['estado']}"), params["label_endereco_completo"]
    # ⛔ O token é credencial: ele é do transporte, e não sai no `paramsJSON`.
    assert "flow_token" not in params, params


# ===========================================================================
# 2 · 🔴 A LINHA DE CONTROLE — sem a coordenada, ninguém é enganado
# ===========================================================================

def test_CONTROLE_sem_a_coordenada_do_pin_o_caso_vai_a_UMA_PESSOA(fio_ligado):
    """A MESMA travessia, sem o pin: handoff com motivo, e ZERO bytes no fio.

    🔴 É esta linha que dá direito à conclusão do teste acima (CLAUDE.md §9.2):
    o fator que mudou foi a coordenada, e mais nada.

    ⛔ E o desfecho errado aqui seria pior que o handoff: latitude `0` é o
    default do protobuf, não um lugar — o Golfo da Guiné. A URA aceitaria calada
    e o guincho sairia para o meio do Atlântico.
    """
    d = _atravessar(com_pin=False)

    assert d["desfecho"] != "protocolo", (
        "⛔ o fio fechou SEM a coordenada — alguém inventou um valor: %r"
        % (d.get("postados") or d.get("resposta_montada")))
    assert not (d.get("postados") or []), (
        "⛔ alguma coisa foi enviada à seguradora sem a coordenada: %r"
        % d["postados"])

    # A recusa é NOMEADA, e o nome diz o que fazer com ela.
    motivo = str(d.get("motivo") or "")
    assert motivo, "recusou em silêncio: nenhum motivo escrito"
    frase = DS.motivo_em_portugues(re.sub(r"^portao:", "", motivo))
    assert frase and not _CHAVE_CRUA.search(frase), (
        "o motivo que uma PESSOA vai ler traz chave crua: %r" % frase)
    # E nada de resposta parcial montada — `params` fica None ou não existe.
    assert (d.get("resposta_montada") or {}).get("params") in (None, {}), (
        "⛔ uma resposta parcial foi montada: %r" % d["resposta_montada"])


def test_CONTROLE_a_coordenada_ZERADA_nao_fecha_o_formulario(fio_ligado):
    """⛔ `(0,0)` é o default do protobuf, não a Ilha Nula — e `0` num campo
    obrigatório tem a MESMA forma de um valor legítimo.

    📊 A recusa é do motor do produto (`par_de_coordenadas`), a mesma que o
    agente usa: se ela falhar aqui, falha no acionamento real.
    """
    for lat, lon, apelido in (("0", "0", "o Golfo da Guiné"),
                              (PIN_LAT, "", "meio par"),
                              ("-127.5", PIN_LON, "fora da faixa do planeta")):
        slots = dict(CASO, local_latitude=lat, local_longitude=lon)
        sessao = DS.new_dispatch_session(
            case_id="fio-f4-zero", company_id="fio-f4-zero",
            playbook_ref=REF_PORTO, subservice=SUB, slots=slots)
        flow = PB.native_flow(PB.get_playbook(REF_PORTO), FLOW_ENDERECO)
        montado = PB.montar_resposta_de_flow(flow, sessao["slots"],
                                            flow_id=FLOW_ENDERECO)
        assert montado["ok"] is False, (
            f"⛔ {apelido} fechou o formulário da Porto: {montado['params']!r}")
        assert montado["params"] is None, montado["params"]


# ===========================================================================
# 3 · O ELO ⑥ — o que o agente PEDE, quando o pin não veio
# ===========================================================================

def test_o_que_o_agente_pede_na_conversa_e_PORTUGUES_e_ensina_o_PIN(fio_ligado):
    """🔴 Ninguém sabe responder a própria latitude — mas todo mundo sabe mandar
    o pin.

    📊 Antes desta costura, `local_cep` e os `local_*` não tinham redação em
    `_COMO_PERGUNTAR` (medido em 26/09/2026): o agente pediria literalmente
    *"local_bairro"* a uma pessoa de verdade. A cobrança só pode existir com a
    frase que se diz a gente.
    """
    faltando = _atravessar(com_pin=False)["falta_ao_nascer"]
    assert faltando, (
        "o portão não cobrou NADA sem a coordenada — o caso morreria na tela do "
        "formulário, que é justamente o que esta SPEC conserta")
    frases = DS.como_pedir_ao_segurado(REF_PORTO, faltando)
    assert len(frases) == len(faltando), (frases, faltando)
    cruas = [f for f in frases if _CHAVE_CRUA.search(f)]
    assert not cruas, f"o agente pediria um identificador a uma pessoa: {cruas}"
    # 🔴 E a pergunta da coordenada ENSINA o caminho honesto: o pin, não o número.
    da_coordenada = [f for f in frases
                     if "localiza" in f.lower() or "clipe" in f.lower()]
    assert da_coordenada, (
        "a coordenada é cobrada e NINGUÉM ensina a mandar o pin: %r" % frases)
    for f in da_coordenada:
        assert not re.search(r"latitude|longitude|coordenada", f, re.I), (
            "⛔ o produto pediria uma coordenada a um ser humano: %r" % f)


def test_CONTROLE_com_o_pin_o_portao_nao_pede_NADA(fio_ligado):
    """🔴 Sem esta linha, um portão que cobrasse sempre passaria acima.

    📊 É a medição que sustenta a decisão desta fatia: **um toque** no clipe do
    WhatsApp preenche o endereço (`inject_address_slots` lê a primeira linha) e a
    coordenada (a linha rotulada do pin) — e as seis perguntas de endereço
    deixam de existir.
    """
    d = _atravessar(com_pin=True)
    assert d["falta_ao_nascer"] == [], d["falta_ao_nascer"]
    assert DS.como_pedir_ao_segurado(REF_PORTO, d["falta_ao_nascer"]) == []


# ===========================================================================
# 4 · O ELO ⑫ — a rede nunca é tocada, e o fio é o do ar
# ===========================================================================

def test_a_travessia_inteira_NAO_toca_a_rede(fio_ligado):
    """⛔ Um teste de fio que alcança a internet não é teste: é acionamento.

    O `fio_ligado` arma `requests.post`/`get` para EXPLODIR, e `_post` é o único
    dublê. Se o motor tentasse sair por qualquer outro caminho, o teste acusa.
    """
    d = _atravessar(com_pin=True)
    assert d["desfecho"] == "protocolo", d.get("motivo")
    assert os.getenv("INSURER_DISPATCH_LIVE") == "true"
    assert len(d["postados"]) == 1
