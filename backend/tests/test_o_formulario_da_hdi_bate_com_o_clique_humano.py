# -*- coding: utf-8 -*-
"""SPEC-119 F4 · BATERIA 3 — o formulário da HDI/Yelum, SIMULADO fora do WhatsApp,
comparado byte a byte com o CLIQUE HUMANO que a seguradora aceitou.

## 🔴 A PERGUNTA QUE SÓ ESTE ARQUIVO FAZ

Os treze guardas de formulário que já existem provam que o produto **monta** a
resposta e **tem** por onde mandá-la. Nenhum deles pergunta o que o segurado
precisa que seja verdade:

> **o que o nosso produto manda é a MESMA COISA que a pessoa mandou no dia em que
> a seguradora aceitou e abriu o protocolo?**

📊 A referência é a captura de **18/07/2026 21:51:52Z**, HDI, sessão `3dc92fcf`,
lida em `observed_events.interactive.extra.paramsJSON` (msg_type `flow_reply`,
`go_type = native_flow_response`). É o clique de uma PESSOA no formulário nativo,
e ele traz, nesta ordem:

```
rb_EmGaragemOuEstacionamento  "1"
rb_NivelDaRua                 "4"
ckb_SituacoesVeiculo          ["nenhuma_opcoes"]
rb_InformacoesLocal           "6"
rb_Ocupantes                  "1"
flow_token                    <uuid>:<msisdn da seguradora>:<msisdn nosso>   (63 chars)
wa_flow_response_params       {title, flow_id, flow_name, response_message}
   title              "Informar condições"
   flow_id            "857030507196739"
   flow_name          "Automóvel - Detalhes do atendimento (veículo, local e
                       ocupantes) V2 [Redução de perguntas]"      ← SEM sufixo
   response_message   4.854 caracteres de eco das telas
```

⛔ **O `flow_token` real NÃO ENTRA neste arquivo**: ele contém dois telefones
(CLAUDE.md §13.9). Entra a FORMA dele, e um token sintético. O que se prova sobre
o token é que o produto o **ECOA**, nunca o constrói — e isso se prova com um
valor qualquer, desde que o valor que sai seja o mesmo que entrou.

## O QUE É REAL, O QUE É DUBLÊ

```
REAL   corridor_playbooks (schema, native_flow, montar_resposta_de_flow)
REAL   insurer_dispatch_service (new_dispatch_session → handle_insurer_message)
REAL   evolution_go (montar_nfm_reply → corpo_do_flow_reply →
                     send_native_flow_response → a rota escolhida)
REAL   a TELA que abre o formulário: vem de tests/corpus/telas_reais/hdi-auto.jsonl,
       escolhida pelo MOTOR (`detect_native_flow`), nunca digitada aqui (§9.4)
DUBLÊ  só `EvolutionGoProvider._post` — a borda de REDE, e nada além dela
```

⛔ **Nada sai para seguradora nenhuma.** O único ponto que tocaria a rede é
`_post`, e ele é substituído por uma lista.

## AS LINHAS DE CONTROLE (CLAUDE.md §9.2) — três, e cada uma pega o que as outras não pegam

```
A  falta um campo required SEM padrão (`local_situacao`) → ZERO bytes no fio,
   `formulario_incompleto:rb_InformacoesLocal` escrito
B  o convite vem SEM o nome do envelope        → `formulario_sem_envelope`,
   ZERO bytes no fio (o produto não chuta "flow" nem "galaxy_message")
C  o mesmo caso com um valor que o formulário NÃO oferece (`rb_NivelDaRua="9"`)
   → `valor_nao_reconhecido`, e o padrão NÃO cobre — é o que impede o
   rebaixamento silencioso da CLAUDE.md §9.5
```

## 🔴 O QUE ESTE ARQUIVO ACHOU, E NÃO CONSERTOU

📊 O produto e o clique humano batem em **5 de 5** respostas e em `title` e
`flow_id`. Divergem em **UM** campo: `wa_flow_response_params.flow_name`.

```
o humano mandou  "…V2 [Redução de perguntas]"
o produto manda  "…V2 [Redução de perguntas]_v2_1783714513857"
```

⚠️ E o comentário de `corridor_playbooks.py` (bloco `flow_name_observado_por_id`,
SPEC-118 F2a) diz o CONTRÁRIO: *"O mapa declara o nome SEM sufixo (…) ou seja, o
produto devolve à seguradora um nome que não é o que ela mandou"*. 📊 Medido em
27/09/2026, `montar_resposta_de_flow(...)["flow_name"]` devolve o nome **COM**
sufixo — `_nome_do_flow` prefere `flow_name_observado_por_id[flow_id]`. A
conclusão do comentário continua certa (o produto não devolve o que o humano
devolveu); o mecanismo descrito está invertido.

⛔ **Não se conserta aqui**, e o motivo é o piso do protocolo §3.2: mudar este
campo muda um BYTE que sai para a seguradora, e 📊 o acervo **não** decide qual
forma ela valida — a captura de 18/07 (flow `857030507196739`) traz o nome SEM
sufixo, e a de 07/08 (flow `2887131368288279`) traz COM. Duas capturas de clique
humano, duas formas. É a P-118-04, e o teste 5 abaixo **fixa a divergência
medida** para que ela não passe a existir sem que ninguém veja.

## O QUE CONTINUA SEM PROVA — escrito, porque não se afirma o que não se mediu

🔴 **NENHUMA seguradora recebeu, até hoje, uma resposta de formulário NOSSA.**
Continua verdade em 27/09/2026. A prova de 26/09 (HTTP 200,
`Type: "InteractiveResponseMessage"`) foi entre **dois números nossos**: ela prova
o TRANSPORTE, não a ACEITAÇÃO. O que este arquivo acrescenta é que o CONTEÚDO é
igual ao do clique que a HDI aceitou — o que é o máximo que se prova sem uma
seguradora do outro lado.

    cd backend && python -m pytest tests/test_o_formulario_da_hdi_bate_com_o_clique_humano.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
PROVIDER_PY = RAIZ / "app" / "services" / "whatsapp" / "providers" / "evolution_go.py"
CORPUS = RAIZ / "tests" / "corpus" / "telas_reais" / "hdi-auto.jsonl"


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
GO = _carregar("_spec119_b3_go", PROVIDER_PY)

REF_HDI = "hdi-auto-whatsapp@v1"
SUB = "guincho"
#: 📊 O formulário V2 da família HDI/Yelum, id que a **HDI** publica.
FLOW_V2 = "857030507196739"
#: 📊 O envelope LEGADO da Meta, ECOADO da captura de 18/07. Nunca escolhido.
ENVELOPE = "galaxy_message"
#: 📊 O rótulo do botão que abriu o formulário, na captura (`flow_cta` do convite
#: → `wa_flow_response_params.title` da resposta).
CTA = "Informar condições"

#: ⛔ Números NOSSOS, de teste. Nenhum telefone de pessoa entra aqui (§13.9).
NUMERO_DA_SEGURADORA = "5500000000000"
#: A FORMA do `flow_token` real: `<uuid>:<msisdn da seguradora>:<msisdn nosso>`.
#: 📊 O real tem 63 caracteres e três partes; este tem a mesma forma e nada de
#: ninguém. O que se prova é o ECO, e para isso o valor é indiferente — desde que
#: o que sai seja idêntico ao que entrou.
TOKEN_SINTETICO = "00000000-0000-4000-8000-000000000001:5500000000000:5500000000001"

# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O CLIQUE HUMANO — a referência. 18/07/2026 21:51:52Z, HDI, sessão 3dc92fcf.
# ═════════════════════════════════════════════════════════════════════════════
#
# Transcrito de `observed_events.interactive.extra.paramsJSON`. ⛔ Sem o
# `flow_token` (dois telefones) e sem `response_message` (4.854 caracteres de eco
# das telas, que o produto não manda — ver `_moldura_da_resposta`).
CLIQUE_HUMANO_RESPOSTAS = {
    "rb_EmGaragemOuEstacionamento": "1",
    "rb_NivelDaRua": "4",
    "ckb_SituacoesVeiculo": ["nenhuma_opcoes"],
    "rb_InformacoesLocal": "6",
    "rb_Ocupantes": "1",
}
CLIQUE_HUMANO_MOLDURA = {
    "title": CTA,
    "flow_id": FLOW_V2,
    "flow_name": ("Automóvel - Detalhes do atendimento (veículo, local e "
                  "ocupantes) V2 [Redução de perguntas]"),
}
#: 📊 E a ORDEM das chaves, como o humano mandou. Ela entra na comparação porque
#: `paramsJSON` é um JSON gerado, e uma troca de ordem é uma mudança de byte —
#: não muda o significado, mas muda o que se pode afirmar sobre "igual".
CLIQUE_HUMANO_ORDEM = ["rb_EmGaragemOuEstacionamento", "rb_NivelDaRua",
                       "ckb_SituacoesVeiculo", "rb_InformacoesLocal", "rb_Ocupantes"]

#: Os SLOTS do caso que produzem as respostas acima. 🔴 Três; os outros dois
#: campos têm padrão declarado no schema (`ckb_SituacoesVeiculo` e `rb_Ocupantes`).
#: 📊 `montar_resposta_de_flow(...)["defaults_used"]` = esses dois, medido.
SLOTS_DO_CLIQUE = {
    "veiculo_em_garagem": "1",      # Sim
    "veiculo_nivel_rua": "4",       # Nível da rua - com acesso livre
    "local_situacao": "6",          # Local Seguro
}

#: Um caso de guincho completo, com dados que fecham a conta e NADA de ninguém.
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
    **SLOTS_DO_CLIQUE,
}


# ═════════════════════════════════════════════════════════════════════════════
# A TELA VEM DO ACERVO, ESCOLHIDA PELO MOTOR (CLAUDE.md §9.4)
# ═════════════════════════════════════════════════════════════════════════════
def _telas_do_acervo() -> list:
    return [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def _tela_que_abre_o_formulario_v2() -> str:
    """A tela REAL da HDI que `detect_native_flow` classifica como o flow V2.

    🔴 Quem escolhe é o motor. Se a âncora mudar, a tela muda com ela; se
    NENHUMA tela do acervo casar, o teste ACUSA em vez de inventar uma frase que
    a HDI nunca escreveu. 📊 Em 27/09/2026 são 2 telas de `guincho`
    (sessões bb5b0f11 e 68f511d9).
    """
    pb = PB.get_playbook(REF_HDI)
    for t in _telas_do_acervo():
        flow = PB.detect_native_flow(pb, str(t.get("text") or ""))
        if flow and str(flow.get("flow_id")) == FLOW_V2:
            return str(t["text"])
    raise AssertionError(
        f"nenhuma tela real da HDI casa o formulário {FLOW_V2} — o acervo tem "
        f"{len(_telas_do_acervo())} telas e a âncora deixou de casar")


def _interativa_do_convite(*, com_envelope: bool = True) -> dict:
    """Os metadados do convite, na forma em que o webhook os entrega."""
    flow = {"flow_id": FLOW_V2, "flow_token": TOKEN_SINTETICO, "cta": CTA}
    if com_envelope:
        flow["name"] = ENVELOPE
    return {"kind": "flow", "flow": flow}


def _provider_com_a_borda_dublada():
    """O provider REAL com **só** o `_post` dublado.

    Tudo o que decide CONTEÚDO — rota, envelope, embrulho, achatamento do
    `paramsJSON`, `version` — continua sendo o código que roda no ar.
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


def _simular(monkeypatch, *, slots: dict, com_envelope: bool = True) -> dict:
    """A simulação completa, fora do WhatsApp. Devolve o diário."""
    monkeypatch.setenv("INSURER_DISPATCH_LIVE", "true")
    diario: dict = {"para_a_ura": []}
    sessao = DS.new_dispatch_session(
        case_id="b3-hdi", company_id="b3-hdi", playbook_ref=REF_HDI,
        subservice=SUB, slots=dict(slots))
    diario["estado_ao_nascer"] = sessao["state"]
    diario["falta_ao_nascer"] = list(sessao.get("missing_slots") or [])
    if sessao["state"] != "ready_to_send":
        # 🔴 O PORTÃO DE COLETA PEGOU ANTES DA URA — e isto é o produto certo,
        # não um caminho de erro. 📊 Medido em 27/09/2026: os três campos do
        # formulário V2 já são `required_slots` da rota, então o caso sem
        # `local_situacao` **nem chega a abrir a conversa com a seguradora**.
        # O diário registra o estado no mesmo nome, para que a linha de controle
        # afirme "needs_human + zero bytes" sem saber POR QUAL das duas portas.
        diario["desfecho"] = "portao"
        diario["estado"] = sessao["state"]
        diario["motivo"] = f"portao:{','.join(diario['falta_ao_nascer'])}"
        diario["postados"] = []
        diario["sessao"] = sessao
        diario["montado"] = None
        return diario

    sessao["live"] = True
    sessao = DS.start_dispatch(sessao, sender=diario["para_a_ura"].append)
    provider, postados = _provider_com_a_borda_dublada()

    def _flow_sender(**kwargs):
        """O adaptador do webhook, literal (`api/webhook.py`)."""
        r = provider.send_native_flow_response(NUMERO_DA_SEGURADORA, **kwargs)
        return bool(getattr(r, "ok", False))

    DS.handle_insurer_message(
        sessao, _tela_que_abre_o_formulario_v2(),
        sender=diario["para_a_ura"].append,
        interactive=_interativa_do_convite(com_envelope=com_envelope),
        flow_sender=_flow_sender)

    diario["estado"] = sessao.get("state")
    diario["motivo"] = str(sessao.get("reason") or "")
    diario["postados"] = postados
    diario["montado"] = sessao.get("flow_resposta")
    diario["sessao"] = sessao
    return diario


def _params_enviados(diario: dict) -> dict:
    assert diario["postados"], (
        f"nenhum byte foi ao fio — estado={diario.get('estado')} "
        f"motivo={diario.get('motivo')}")
    return json.loads(diario["postados"][-1]["corpo"]["paramsJSON"])


# ═════════════════════════════════════════════════════════════════════════════
# 1 · O TRANSPORTE — rota, envelope, embrulho, versão
# ═════════════════════════════════════════════════════════════════════════════
def test_a_resposta_vai_pela_rota_provada_com_o_embrulho(monkeypatch):
    d = _simular(monkeypatch, slots=CASO)
    assert d["estado"] == "ura", f"o formulário não fechou: {d['motivo']}"
    assert len(d["postados"]) == 1, f"{len(d['postados'])} envios — um formulário, um envio"
    posto = d["postados"][0]

    assert posto["rota"] == GO.ROTA_DE_FLOW_REPLY_PROVADA == "/send/interactiveResponse"
    corpo = posto["corpo"]
    # 🔴 O embrulho é a diferença medida entre 200 e 479 (26/09/2026, com linha
    #    de controle: sem ele → 479; com ele → 200).
    assert corpo["wrapInDocumentWithCaption"] is True, (
        "o embrulho DocumentWithCaptionMessage saiu do corpo — é ELE, e mais "
        "nada, a diferença entre HTTP 200 e o 479 do WhatsApp")
    assert corpo["name"] == ENVELOPE == "galaxy_message", (
        "o envelope deixou de ser o LEGADO ecoado da captura — com o rótulo "
        "atual da Meta a família HDI/Yelum descarta a resposta em silêncio")
    assert corpo["version"] == GO.VERSION_DA_RESPOSTA_DE_FLOW == 3
    assert corpo["number"] == NUMERO_DA_SEGURADORA


# ═════════════════════════════════════════════════════════════════════════════
# 2 · 🔴 O CORAÇÃO — as respostas são as MESMAS do clique humano
# ═════════════════════════════════════════════════════════════════════════════
def test_as_respostas_batem_com_o_clique_humano(monkeypatch):
    enviado = _params_enviados(_simular(monkeypatch, slots=CASO))
    respostas = {k: v for k, v in enviado.items()
                 if k not in ("flow_token", "wa_flow_response_params")}

    assert respostas == CLIQUE_HUMANO_RESPOSTAS, (
        "o que o produto responde DIVERGE do clique humano de 18/07/2026 que a "
        f"HDI aceitou.\n  produto: {respostas}\n  humano : {CLIQUE_HUMANO_RESPOSTAS}")
    assert list(respostas) == CLIQUE_HUMANO_ORDEM, (
        f"a ORDEM das chaves mudou: {list(respostas)} ≠ {CLIQUE_HUMANO_ORDEM}")

    # E o tipo importa: `ckb_SituacoesVeiculo` é LISTA no clique humano. Uma
    # string "nenhuma_opcoes" seria outro byte, e um CheckboxGroup que recebe
    # string é a classe de erro que o WhatsApp descarta sem dizer nada.
    assert isinstance(respostas["ckb_SituacoesVeiculo"], list)


# ═════════════════════════════════════════════════════════════════════════════
# 3 · O `flow_token` é ECOADO, nunca construído
# ═════════════════════════════════════════════════════════════════════════════
def test_o_flow_token_e_ecoado_e_o_corredor_nao_o_produz(monkeypatch):
    d = _simular(monkeypatch, slots=CASO)
    enviado = _params_enviados(d)
    assert enviado["flow_token"] == TOKEN_SINTETICO, (
        "o token que saiu não é o que entrou no convite — o produto passou a "
        "CONSTRUIR uma credencial de sessão")

    # 🔴 E o corredor, que é PURO, não produz o token: quem o injeta é o
    #    transporte, na hora do envio.
    montado = d["montado"] or {}
    assert "flow_token" not in (montado.get("params") or {}), (
        "⛔ o corredor passou a produzir o `flow_token` — ele é credencial de "
        "sessão e não é dado do caso")

    # ⛔ E ele nunca aparece no transcript (é o que autoriza responder em nome
    #    da corretora).
    trilha = json.dumps(d["sessao"].get("transcript") or [], ensure_ascii=False)
    assert TOKEN_SINTETICO not in trilha, "o token vazou para o transcript"


# ═════════════════════════════════════════════════════════════════════════════
# 4 · A MOLDURA — `title` e `flow_id` ecoados do convite
# ═════════════════════════════════════════════════════════════════════════════
def test_a_moldura_ecoa_o_titulo_e_o_id_do_convite(monkeypatch):
    moldura = _params_enviados(_simular(monkeypatch, slots=CASO))["wa_flow_response_params"]
    assert moldura["title"] == CLIQUE_HUMANO_MOLDURA["title"], (
        "o `title` deixou de ecoar o `flow_cta` do convite")
    # 🔴 O id é POR SEGURADORA (o mesmo formulário tem outro id na Yelum).
    #    Ecoar o do convite é o que impede responder à Yelum com o id da HDI.
    assert moldura["flow_id"] == FLOW_V2 == CLIQUE_HUMANO_MOLDURA["flow_id"]
    # `response_message` continua FORA, de propósito (4.854 chars não medidos).
    assert "response_message" not in moldura


# ═════════════════════════════════════════════════════════════════════════════
# 5 · 🔴 A DIVERGÊNCIA MEDIDA — fixada para não mudar sem que se veja
# ═════════════════════════════════════════════════════════════════════════════
def test_o_flow_name_divergE_do_clique_humano_e_isso_esta_medido(monkeypatch):
    """📊 O ÚNICO campo em que o produto e o clique humano não batem.

    ⛔ Não se conserta aqui (piso §3.2: muda um byte que sai para seguradora), e
    o acervo NÃO decide: 18/07 (flow 857030507196739) traz o nome SEM sufixo;
    07/08 (flow 2887131368288279) traz COM. Duas capturas humanas, duas formas.

    🔴 Este teste NÃO abençoa a divergência: ele a FIXA. No dia em que alguém
    mudar o eco — para um lado ou para o outro —, este teste fica vermelho e a
    mudança tem de ser declarada, com a medição, em vez de passar calada.
    """
    moldura = _params_enviados(_simular(monkeypatch, slots=CASO))["wa_flow_response_params"]
    humano = CLIQUE_HUMANO_MOLDURA["flow_name"]
    nosso = moldura["flow_name"]
    assert nosso.startswith(humano), (
        f"o `flow_name` deixou de conter o nome que o humano mandou:\n"
        f"  humano: {humano!r}\n  nosso : {nosso!r}")
    sufixo = nosso[len(humano):]
    assert sufixo == "_v2_1783714513857", (
        "📊 A DIVERGÊNCIA MEDIDA MUDOU. Em 27/09/2026 o produto acrescentava "
        f"{'_v2_1783714513857'!r} ao nome que o humano mandou, e o acervo não "
        f"decide qual forma a seguradora valida (P-118-04). Agora ele "
        f"acrescenta {sufixo!r}. Se isto foi de propósito, a mudança precisa "
        "vir com a medição da seguradora ao lado — não com um teste ajustado.")


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 AS LINHAS DE CONTROLE — sem elas nada acima prova nada (CLAUDE.md §9.2)
# ═════════════════════════════════════════════════════════════════════════════
def test_controle_a_falta_um_campo_sem_padrao_e_nada_vai_ao_fio(monkeypatch):
    """A `local_situacao` decide a PRIORIDADE do atendimento e não tem padrão.

    📊 E O PORTÃO PEGA ANTES DA URA — medido em 27/09/2026, não suposto. Os três
    campos do formulário V2 (`veiculo_em_garagem`, `veiculo_nivel_rua`,
    `local_situacao`) já são `required_slots` da rota `hdi/auto/guincho`, então o
    caso incompleto **nem abre a conversa com a seguradora**: `state=preparing`,
    `missing_slots=['local_situacao']`, zero bytes no fio.
    """
    sem_local = {k: v for k, v in CASO.items() if k != "local_situacao"}
    d = _simular(monkeypatch, slots=sem_local)
    assert d["postados"] == [], (
        "🔴 um formulário MEIO preenchido foi ao fio — é o defeito que manda o "
        "equipamento errado, e ele é pior que handoff nenhum")
    assert d["desfecho"] == "portao", (
        f"o portão deixou de cobrar `local_situacao` antes da URA: {d}")
    assert d["falta_ao_nascer"] == ["local_situacao"], d["falta_ao_nascer"]


def test_controle_a2_o_ramo_do_formulario_incompleto_ANDA(monkeypatch):
    """🔴 O ramo `formulario_incompleto` existe e RESPONDE — exercitado.

    ⚠️ O teste de cima prova que o portão pega primeiro, e por isso este ramo do
    motor fica INALCANÇÁVEL nesta rota. Declaração sem consumidor exercitado é o
    defeito da CLAUDE.md §9.4 pelo outro lado: aqui a sessão é empurrada PARA
    ALÉM do portão de propósito (é o que um `required_slots` mais curto, ou uma
    rota nova, produziria) e o que se afirma é o comportamento do motor.
    """
    monkeypatch.setenv("INSURER_DISPATCH_LIVE", "true")
    sessao = DS.new_dispatch_session(
        case_id="b3-a2", company_id="b3-a2", playbook_ref=REF_HDI,
        subservice=SUB, slots=dict(CASO))
    assert sessao["state"] == "ready_to_send"
    sessao["live"] = True
    sessao = DS.start_dispatch(sessao, sender=lambda _t: None)
    # 🔴 o slot sai DEPOIS do portão — é a única forma de chegar ao ramo
    sessao["slots"].pop("local_situacao", None)

    provider, postados = _provider_com_a_borda_dublada()
    DS.handle_insurer_message(
        sessao, _tela_que_abre_o_formulario_v2(), sender=lambda _t: None,
        interactive=_interativa_do_convite(),
        flow_sender=lambda **kw: bool(getattr(
            provider.send_native_flow_response(NUMERO_DA_SEGURADORA, **kw), "ok", False)))

    assert postados == [], "🔴 resposta PARCIAL foi ao fio"
    assert sessao["state"] == "needs_human"
    assert str(sessao.get("reason") or "").startswith("formulario_incompleto:"), sessao.get("reason")
    assert "rb_InformacoesLocal" in str(sessao.get("reason")), sessao.get("reason")


def test_controle_b_sem_o_envelope_ecoado_nada_vai_ao_fio(monkeypatch):
    """Convite sem `name`: o produto NÃO chuta o envelope."""
    d = _simular(monkeypatch, slots=CASO, com_envelope=False)
    assert d["postados"] == [], (
        "🔴 o produto chutou o nome do envelope — e um envelope errado faz a "
        "seguradora descartar a resposta em silêncio, queimando a janela")
    assert d["estado"] == "needs_human"
    assert d["motivo"] == "formulario_sem_envelope", d["motivo"]


def test_controle_c_valor_fora_das_opcoes_nao_cai_no_padrao(monkeypatch):
    """🔴 O rebaixamento silencioso da CLAUDE.md §9.5, no formulário.

    `rb_NivelDaRua` escolhe o EQUIPAMENTO (plataforma, asa delta, munck). Um
    valor que o formulário não oferece tem de PARAR o caso — nunca virar o
    padrão, e nunca virar "4" porque é o mais comum.
    """
    torto = {**CASO, "veiculo_nivel_rua": "9"}
    d = _simular(monkeypatch, slots=torto)
    assert d["postados"] == [], (
        "🔴 um valor que o formulário NÃO oferece foi ao fio — o equipamento "
        "errado chega ao segurado e nada trava")
    # 📊 27/09/2026: o portão recusa o valor torto ANTES da URA, pelo mesmo
    # `valor_de_slot_honesto` — `missing_slots=['veiculo_nivel_rua']`.
    assert d["desfecho"] == "portao", d
    assert d["falta_ao_nascer"] == ["veiculo_nivel_rua"], d["falta_ao_nascer"]
    # E o MOTOR do formulário, chamado direto, diz POR QUE recusa.
    montado = PB.montar_resposta_de_flow(
        PB.native_flow(PB.get_playbook(REF_HDI), FLOW_V2), torto, flow_id=FLOW_V2)
    motivos = {d_["campo"]: d_["motivo"] for d_ in montado["missing_detail"]}
    assert motivos.get("rb_NivelDaRua") == "valor_nao_reconhecido", motivos
    assert montado["params"] is None, "resposta PARCIAL montada — não existe meia resposta"


def test_controle_d_o_caso_certo_e_o_caso_torto_conseguem_diferir(monkeypatch):
    """O corolário da §9.3: prove que os dois lados CONSEGUEM ser diferentes."""
    certo = _simular(monkeypatch, slots=CASO)
    torto = _simular(monkeypatch, slots={**CASO, "veiculo_nivel_rua": "9"})
    assert len(certo["postados"]) == 1 and torto["postados"] == []
    assert certo["estado"] != torto["estado"], (
        f"os dois lados deram o MESMO estado ({certo['estado']}) — um guarda que "
        "não consegue distinguir os dois casos não guarda nada (§9.3)")
    assert certo.get("desfecho") != torto.get("desfecho")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
