# -*- coding: utf-8 -*-
"""O que o painel achou não volta — SPEC-092, as cinco lentes.

Cinco lentes cegas entre si julgaram o código desta SPEC. **As cinco
reprovaram.** Este arquivo é o que impede cada achado de voltar.

⚠️ Vários dos defeitos abaixo passaram pela suíte porque **os fixtures tinham a
forma errada** — deduzida em vez de medida. É o `CLAUDE.md` §9.2 contra quem
escreveu os testes, e a razão de cada guarda aqui usar a forma do FIO.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PARSER_PY = RAIZ / "app" / "services" / "whatsapp" / "evolution_inbound.py"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
ROTA_PY = RAIZ / "app" / "api" / "whatsapp_integrations.py"


def _carregar(nome: str, caminho: Path):
    nomes = ("app", "app.services", "app.services.whatsapp")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
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


P = _carregar("_painel_parser", PARSER_PY)
M = _carregar("_painel_motor", MOTOR_PY)

#: 📊 O texto que a seguradora escreve, e que a `prompt_anchor` lê.
TEXTO_DA_TELA = ("Para que a remoção do veículo ocorra sem imprevistos, precisamos "
                 "entender o local e as condições do veículo.")


def convite_do_fio(*, cta="Informar condições", options=None, contexto=None):
    """📊 A forma REAL: dois níveis, maiúsculas, `buttonParamsJSON`, corpo FORA."""
    botao = {"name": "galaxy_message", "buttonParamsJSON": json.dumps({
        "flow_id": "857030507196739", "flow_cta": cta,
        "flow_token": "00000000-0000-0000-0000-000000000000:55000:55000",
    })}
    botoes = [botao]
    if options:
        botoes = [{"name": "quick_reply",
                   "buttonParamsJson": json.dumps({"id": "b1", "display_text": o})}
                  for o in options] + botoes
    interno = {"NativeFlowMessage": {"buttons": botoes}}
    if contexto:
        interno.update(contexto)
    return {"interactiveMessage": {
        "body": {"text": TEXTO_DA_TELA},
        "InteractiveMessage": interno,
    }}


# ---------------------------------------------------------------------------
# LENTE DO ACERVO — o corpo da tela não pode sumir
# ---------------------------------------------------------------------------

def test_o_CORPO_da_tela_sobrevive_na_forma_do_fio():
    """🔴 `_sub` devolvia só o nível mais interno — e o corpo mora no de FORA.

    📊 Medido pelo painel: `3 de 3` casamentos de `prompt_anchor` viravam **0**.
    `detect_native_flow` existe exatamente para o caso *"o `flow_id` não
    chegou"*, e o defeito cortava essa rede.
    """
    texto, meta = P._interactive_from_message(convite_do_fio())
    assert meta["kind"] == "flow"
    assert "precisamos entender o local" in texto.lower(), (
        f"o texto da seguradora sumiu do renderizado: {texto!r}")


def test_a_ANCORA_do_playbook_ainda_casa_o_texto_renderizado():
    """A prova do que o guarda acima protege: com o corpo, a âncora casa."""
    import re

    texto, _ = P._interactive_from_message(convite_do_fio())
    ancora = r"precisamos entender o local e as condi[çc][õo]es do ve[íi]culo"
    assert re.search(ancora, texto, re.IGNORECASE | re.DOTALL), (
        "a `prompt_anchor` do schema não casa mais o texto — a rede de "
        "segurança do BLOCO C morreu em silêncio")


def test_CONTROLE_o_corpo_CONSEGUE_faltar():
    """§9.3 — prove que o teste acima mede o corpo, e não o marcador."""
    sem_corpo = convite_do_fio()
    sem_corpo["interactiveMessage"].pop("body")
    texto, _ = P._interactive_from_message(sem_corpo)
    assert "precisamos entender" not in texto.lower(), (
        "o texto apareceu sem haver corpo — o guarda mede outra coisa")


# ---------------------------------------------------------------------------
# LENTE DO ISOLAMENTO + RED TEAM — o cru não leva o que não é tela
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("grafia", ["contextInfo", "ContextInfo", "context_info"])
def test_o_contextInfo_cai_em_QUALQUER_grafia(grafia):
    """🔴 O corte era `kk != "contextInfo"`, comparação exata — dentro do arquivo
    cuja tese inteira é que a grafia das chaves varia.

    📊 Medido pelo painel, com controle: `ContextInfo` e `context_info` passavam.
    """
    payload = convite_do_fio(contexto={
        grafia: {"quotedMessage": {"conversation": "SEGREDO-DO-ATENDIMENTO"}}})
    _, meta = P._interactive_from_message(payload)
    assert "SEGREDO-DO-ATENDIMENTO" not in json.dumps(meta.get("cru"), ensure_ascii=False), (
        f"a grafia {grafia!r} levou a mensagem citada para o acervo durável")


def test_o_contextInfo_cai_TAMBEM_no_nivel_de_dentro():
    """🔴 O corte só olhava profundidade 1 — e a forma real tem um nível extra."""
    payload = convite_do_fio(contexto={
        "contextInfo": {"quotedMessage": {"conversation": "SEGREDO-FUNDO"}}})
    _, meta = P._interactive_from_message(payload)
    assert "SEGREDO-FUNDO" not in json.dumps(meta.get("cru"), ensure_ascii=False)


def test_CONTROLE_o_segredo_ESTAVA_no_payload():
    """§9.3 — sem isto, um `cru` sempre vazio passaria em tudo acima."""
    payload = convite_do_fio(contexto={
        "contextInfo": {"quotedMessage": {"conversation": "SEGREDO-FUNDO"}}})
    assert "SEGREDO-FUNDO" in json.dumps(payload, ensure_ascii=False)
    _, meta = P._interactive_from_message(payload)
    assert meta.get("cru"), "o cru veio vazio — o corte não prova nada"
    assert "galaxy_message" in json.dumps(meta["cru"], ensure_ascii=False).lower()


# 🔴 `flow_metadata` SAIU desta lista pelo segundo juiz, e a mudança é o
# conserto: cortando o objeto inteiro, ia junto o `flow_name` — o único rótulo
# legível do formulário, e segredo de ninguém. Ver
# `test_o_flow_name_SOBREVIVE_e_os_segredos_dele_NAO`.
@pytest.mark.parametrize("chave", ["mediaKey", "directPath", "fileEncSHA256",
                                   "www_proxy_secret", "flow_token_signature"])
def test_o_cru_NAO_leva_chave_de_descriptografia_nem_segredo(chave):
    """🔴 `mediaKey` é chave de descriptografia. E `flow_metadata` traz
    `www_proxy_secret` e `flow_token_signature` — **segredo, numa tabela
    durável**. `CLAUDE.md` §7: *nenhum segredo em log, blueprint, artifact ou RAG*.
    """
    payload = convite_do_fio()
    payload["interactiveMessage"]["header"] = {chave: "VALOR-SENSIVEL"}
    _, meta = P._interactive_from_message(payload)
    assert "VALOR-SENSIVEL" not in json.dumps(meta.get("cru"), ensure_ascii=False), (
        f"`{chave}` entrou no cru")


# ---------------------------------------------------------------------------
# RED TEAM — o parser não derruba a rota
# ---------------------------------------------------------------------------

def test_aninhamento_ABSURDO_nao_levanta():
    """🔴 `_sub` recursava sem teto. 📊 `json.loads` aceita 5.000 níveis, e
    `webhook.py:1246` chama o parser **sem `try/except`** — `RecursionError`
    virava 500 na rota e a mensagem da seguradora se perdia."""
    fundo: dict = {"nativeFlowMessage": {"buttons": []}}
    for _ in range(3000):
        fundo = {"interactiveMessage": fundo}
    P._interactive_from_message(fundo)  # não pode levantar


def test_Buttons_com_B_MAIUSCULO_e_lido():
    """🔴 A tolerância era assimétrica: `_sub` normalizava os invólucros e
    `nfm.get("buttons")` era `.get()` cru — a P-084-68 reabria **por uma letra**,
    na exata família de defeito que este arquivo documenta."""
    payload = convite_do_fio()
    nfm = payload["interactiveMessage"]["InteractiveMessage"].pop("NativeFlowMessage")
    payload["interactiveMessage"]["InteractiveMessage"]["NativeFlowMessage"] = {
        "Buttons": nfm["buttons"]}
    _, meta = P._interactive_from_message(payload)
    assert meta["kind"] == "flow", f"`Buttons` maiúsculo não foi lido: {meta['kind']!r}"


# ---------------------------------------------------------------------------
# LENTE DO SEGURADO — a guarda é por BOLHA, não por janela
# ---------------------------------------------------------------------------

INTER_DO_FORMULARIO = {"kind": "flow", "options": [],
                       "flow": {"flow_id": "857030507196739", "flow_token": "t",
                                "name": "galaxy_message", "cta": "Informar"}}


def test_a_bolha_SEGUINTE_da_rajada_NAO_dispara_o_formulario():
    """🔴 A resposta saía DUAS VEZES, e um aviso de fila matava o acionamento.

    📊 Medido pelo painel, com linha de controle contra o motor de `8b49fdb`:

        rajada [FORMULÁRIO, "você está na fila"] com o MESMO interactive
        ANTES  8b49fdb   RESPOSTAS ENVIADAS = 1
        DEPOIS (defeito)                     = 2

    `message_buffer_service.py:111` **preserva o `interactive` pela janela de
    debounce inteira, de propósito** — o comentário dele diz que a URA da HDI
    manda o formulário e, logo atrás, um aviso de fila. `webhook.py:507`
    repassa o mesmo `interactive` a cada bolha.
    """
    assert M.a_tela_e_formulario(
        "Você está na fila de atendimento, aguarde um instante.",
        INTER_DO_FORMULARIO) is False, (
        "a bolha de AVISO DE FILA foi tratada como formulário — é a resposta "
        "em dobro, e é o acionamento morrendo porque a URA disse 'aguarde'")


def test_a_bolha_QUE_E_o_formulario_dispara():
    """A metade positiva: a bolha que É o formulário continua disparando."""
    assert M.a_tela_e_formulario(
        f"{TEXTO_DA_TELA}\n[FORMULARIO NATIVO: Informar] (exige clique)",
        INTER_DO_FORMULARIO) is True


def test_a_tela_que_oferece_OUTRO_caminho_nao_e_sequestrada():
    """🔴 📊 **25 telas do corpus** mencionam formulário E casam passo de URA;
    **21** (9 azul + 12 porto) dizem *"Ou, se preferir, preencha o formulário
    abaixo"* — têm botão clicável **e** formulário.

    ⚠️ Porto e Azul são justamente as duas **sem schema nenhum**. Sequestrá-las
    trocaria 21 acionamentos que funcionam por 21 que param.
    """
    # 🔴 ASSERÇÃO MIGRADA pelo juiz de confirmação, e a mudança é o conserto.
    #
    # Ela exigia que `a_tela_e_formulario` recusasse pela só presença de
    # `options`. 📊 O juiz mediu que isso devolvia a P-084-68 para uma tela de
    # formulário **conhecida** que tivesse botão: ela voltava a ser respondida
    # por texto.
    #
    # ⚠️ A decisão mudou de casa para `_responder_formulario_nativo`, que é o
    # único lugar onde se sabe se o formulário é conhecido. Ver
    # `test_o_formulario_DESCONHECIDO_com_botao_clicavel_usa_o_BOTAO`.
    com_botao = dict(INTER_DO_FORMULARIO, options=[{"id": "1", "title": "Digitar"}])
    assert M.a_tela_e_formulario(
        "Ou, se preferir, preencha o formulário abaixo.\n[FORMULARIO NATIVO: x]",
        com_botao) is True, (
        "a guarda voltou a recusar pela só presença de `options` — e aí uma "
        "tela de formulário CONHECIDA com botão volta a ser respondida por "
        "texto, que é a P-084-68 de volta")


def test_o_simulador_SEM_interactive_continua_reconhecendo_pelo_marcador():
    """📊 `ura_simulator` e `replay` chamam sem `interactive`. Sem esta metade,
    a régua mediria um produto diferente do que roda em produção."""
    assert M.a_tela_e_formulario("[FORMULARIO NATIVO: x]", None) is True


# ---------------------------------------------------------------------------
# RED TEAM — o flow_id do convite é VETO
# ---------------------------------------------------------------------------

def _playbook():
    pb = _carregar("_painel_pb", RAIZ / "app" / "services" / "corridor_playbooks.py")
    return pb.YELUM_AUTO_WHATSAPP_V1


def test_flow_id_DESCONHECIDO_com_ancora_conhecida_e_RECUSADO():
    """🔴 O achado mais caro do red team, medido com linha de controle:

        BASE 8b49fdb    moldura flow_id=857030507196739   (id ERRADO → descartada)
        HEAD sem veto   moldura flow_id=9999999999999999  (id CERTO, campos ERRADOS)

    **Trocava "resposta descartada" por "resposta bem-endereçada e errada"** — e
    a segunda é pior: a seguradora aceita e o chamado abre com dado faltando.
    """
    sessao = {"state": "ura", "slots": {}, "transcript": []}
    saida = M._responder_formulario_nativo(
        sessao, _playbook(),
        f"{TEXTO_DA_TELA}\n[FORMULARIO NATIVO: Informar]",
        interactive={"kind": "flow", "options": [],
                     "flow": {"flow_id": "9999999999999999", "flow_token": "t",
                              "name": "galaxy_message", "cta": "Informar"}})
    assert saida is not None and saida["state"] == "needs_human", (
        "um formulário que ninguém conhece foi respondido porque a FRASE de "
        "abertura era conhecida")
    assert saida["reason"] == "formulario_nativo_desconhecido"


def test_CONTROLE_flow_id_CONHECIDO_com_a_mesma_ancora_NAO_e_recusado():
    """§9.3 — um veto que recusasse tudo passaria no teste acima e o produto
    nunca responderia formulário nenhum."""
    sessao = {"state": "ura", "slots": {}, "transcript": []}
    saida = M._responder_formulario_nativo(
        sessao, _playbook(),
        f"{TEXTO_DA_TELA}\n[FORMULARIO NATIVO: Informar]",
        interactive={"kind": "flow", "options": [],
                     "flow": {"flow_id": "3206000179602236", "flow_token": "t",
                              "name": "galaxy_message", "cta": "Informar"}})
    assert saida is not None
    assert saida.get("reason") != "formulario_nativo_desconhecido", (
        "o veto recusou um formulário que o playbook conhece")


def test_o_CTA_da_seguradora_NAO_escolhe_o_schema():
    """🔴 O BLOCO B anexa `[FORMULARIO NATIVO: {cta}]` ao texto, e `cta` é string
    da seguradora. O BLOCO D rodava `detect_native_flow` sobre esse texto.

    📊 Medido pelo red team, com controle: um CTA carregando a frase de abertura
    de OUTRO formulário levava a resposta de 2 campos para 4.
    """
    limpo = M._sem_o_marcador(
        "Onde o veículo está parado?\n"
        "[FORMULARIO NATIVO: precisamos entender o local e as condições do veículo] (x)")
    assert "condi" not in limpo.lower(), (
        f"o CTA da seguradora sobreviveu ao corte: {limpo!r}")
    assert "Onde o veículo está parado?" in limpo, (
        "o corte levou junto o texto da seguradora")


# ---------------------------------------------------------------------------
# LENTE DO SEGURADO — a frase não mente quando o envio falha
# ---------------------------------------------------------------------------

def test_a_frase_do_transcript_DISTINGUE_os_TRES_desfechos():
    """🔴 `[FORMULÁRIO NATIVO respondido]` era gravada **antes** da tentativa e
    ficava lá quando o envio estourava. O dossiê chegava assim a quem ia socorrer:

        Motivo: formulario_envio_falhou
        [corretora] [FORMULÁRIO NATIVO respondido: 5 campos]
    """
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    for frase in ("[FORMULÁRIO NATIVO respondido:",
                  "[FORMULÁRIO NATIVO montado e o envio FALHOU:",
                  "[FORMULÁRIO NATIVO pronto, NÃO enviado"):
        assert frase in fonte, f"sumiu o desfecho {frase!r}"
    # ⚠️ A âncora é a linha de CÓDIGO, não a frase: ela aparece antes, dentro do
    # comentário que conta esta história. Guarda estática que lê comentário
    # guarda o comentário — foi o defeito que a SPEC-085 já pagou uma vez.
    i_tentativa = fonte.index("enviado = None")
    i_frase = fonte.index('resumo = f"[FORMULÁRIO NATIVO respondido:')
    assert i_tentativa < i_frase, (
        "a frase voltou a ser escrita ANTES da tentativa — ela não pode "
        "descrever um desfecho que ainda não aconteceu")


# ---------------------------------------------------------------------------
# LENTE DO ISOLAMENTO — a rota de prova é POR CORRETORA
# ---------------------------------------------------------------------------

class _ConsultaEspia:
    """Um dublê que **REGISTRA** os filtros. 🔴 O anterior tinha
    `def eq(self,*a,**k): return self` — e o painel provou que apagar
    `.eq("is_active", True)` deixava TODOS os assertos verdes.

    Um guarda que não tem como falhar não guarda nada (`CLAUDE.md` §9.3).
    """

    def __init__(self, banco):
        self.b = banco

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.b.filtros.append((col, str(val)))
        return self

    def limit(self, n):
        self.b.teto = int(n)
        return self

    async def execute(self):
        linhas = [{"paired_phone_e164": n} for e, n in self.b.numeros
                  if ("company_id", e) in self.b.filtros]
        return type("R", (), {"data": linhas[: self.b.teto]})()


class BancoEspiao:
    def __init__(self, numeros):
        self.numeros = list(numeros)
        self.filtros: list = []
        self.teto = None

    @property
    def client(self):
        return self

    def table(self, nome):
        return _ConsultaEspia(self)


def _carregar_rota():
    fonte = ROTA_PY.read_text(encoding="utf-8")
    ini = fonte.index("_TETO_DE_NUMEROS_NOSSOS = 500")
    fim = fonte.index('@router.post("/prova-de-formulario")')
    mod = types.ModuleType("_painel_rota")
    mod.__dict__["Any"] = object
    mod.__dict__["AsyncSupabaseClient"] = object
    mod.__dict__["logger"] = type("L", (), {"error": lambda *a, **k: None,
                                            "warning": lambda *a, **k: None,
                                            "info": lambda *a, **k: None})()
    exec(compile(fonte[ini:fim], "<rota>", "exec"), mod.__dict__)
    return mod


R = _carregar_rota()

A, B = "empresa-A", "empresa-B"
NUMEROS = [(A, "5511900000001"), (B, "5547900000002")]


def _e_nosso(empresa, destino):
    banco = BancoEspiao(NUMEROS)
    r = asyncio.run(R._destino_e_nosso(banco, empresa, destino))
    return r, banco


def test_DOIS_TENANTS_a_corretora_A_nao_alcanca_o_aparelho_da_B():
    """🔴 O achado que reprovou o bloco: a lista de permissão era GLOBAL.

    Um usuário logado da Corretora A postava o número pareado da B, a lista
    aceitava porque *"é nosso"*, e o backend disparava do aparelho de A para o
    de B. `CLAUDE.md` §7: nenhum dado atravessa corretoras.
    """
    (permitido, _), _ = _e_nosso(A, "5547900000002")
    assert permitido is False, (
        "a corretora A alcançou o aparelho pareado da corretora B")


def test_CONTROLE_a_corretora_alcanca_o_PROPRIO_aparelho():
    """A metade positiva: uma trava que recusasse tudo deixaria toda corretora
    sem o diagnóstico do próprio canal, que é a razão de a rota existir."""
    (permitido, numero), _ = _e_nosso(A, "5511900000001")
    assert permitido is True
    assert numero == "5511900000001"


def test_o_FILTRO_de_tenant_e_MESMO_aplicado():
    """🔴 §9.3 — este é o guarda que o painel provou faltar.

    O dublê antigo tinha `def eq(self,*a,**k): return self`: apagar
    `.eq("is_active", True)` do produto deixava **todos** os assertos verdes.
    Este REGISTRA os filtros, então a ausência aparece.
    """
    _, banco = _e_nosso(A, "5511900000001")
    assert ("company_id", A) in banco.filtros, (
        "a consulta não filtrou por corretora — a lista de permissão voltou a "
        "ser global, e com ela o oráculo de pertencimento")
    assert ("is_active", "True") in banco.filtros, (
        "a consulta parou de exigir integração ativa")


def test_o_numero_que_VAI_AO_FIO_e_o_GRAVADO_e_nao_o_digitado():
    """🔴 A trava comparava normalizado e o produto enviava o cru. Bastava uma
    colisão de chave para a trava aprovar um número e o produto entregar noutro."""
    (permitido, numero), _ = _e_nosso(A, "+55 (11) 90000-0001")
    assert permitido is True
    assert numero == "5511900000001", (
        f"devolveu {numero!r} — tem de ser o valor GRAVADO, não o digitado")


@pytest.mark.parametrize("a,b", [
    ("5547933334444", "554733334444"),   # móvel × FIXO, mesmo DDD
    ("5512925550147", "12125550147"),    # BR × internacional
])
def test_numeros_DIFERENTES_NAO_colidem(a, b):
    """🔴 `DDD + 8 finais` colidia. 📊 Medido pelo painel nas duas formas.

    Numa lista de PERMISSÃO que autoriza envio real sem freio, colisão é
    autorização indevida.
    """
    assert R._chave_de_telefone(a) != R._chave_de_telefone(b), (
        f"{a} e {b} produzem a mesma chave")


def test_CONTROLE_o_MESMO_aparelho_em_grafias_diferentes_COLIDE_de_proposito():
    """§9.3 — uma chave que nunca colidisse recusaria o próprio dono."""
    assert (R._chave_de_telefone("5547999998888")
            == R._chave_de_telefone("+55 (47) 99999-8888")
            == R._chave_de_telefone("47999998888"))


# ---------------------------------------------------------------------------
# 🔴 O JUIZ DE CONFIRMAÇÃO — e aqui os guardas são COMPORTAMENTAIS
# ---------------------------------------------------------------------------
#
# O juiz mutou o produto trocando os dois ramos da frase de lugar — passando a
# dizer "respondido" quando o envio FALHA — e **8 de 8 asserções continuaram
# verdes**, porque liam o FONTE.
#
# > Guarda estático prova que a string existe; nunca que o produto a escolhe.
#
# ⛔ O `flow_sender` aqui é sempre um contador em memória. **Nada sai.**

def _motor_ao_vivo():
    """Uma cópia do motor com o portão de envio aberto — em MEMÓRIA.

    ⛔ `INSURER_DISPATCH_LIVE` não é tocado: o que muda é um atributo do módulo
    carregado por `importlib` neste processo, e o transporte é um dublê.
    """
    m = _carregar("_painel_motor_vivo", MOTOR_PY)
    m.dispatch_live_enabled = lambda: True
    return m


SLOTS_COMPLETOS = {"veiculo_em_garagem": "nao", "veiculo_situacoes": "nenhuma",
                   "local_situacao": "seguro", "ocupantes_particularidade": "nenhuma",
                   "veiculo_nivel_rua": "nivel da rua"}

TELA_FORM = TEXTO_DA_TELA + chr(10) + "[FORMULARIO NATIVO: Informar] (exige clique)"


def _sessao_viva():
    return {"state": "ura", "slots": dict(SLOTS_COMPLETOS), "subservice": "guincho",
            "case_id": "c", "transcript": [], "live": True,
            "playbook_ref": "hdi-auto-whatsapp@v1",
            "flow_token": "TOKEN-DA-SESSAO", "envelope_do_flow": "galaxy_message",
            "flow_id_ativo": "857030507196739"}


def _ultima_saida(sessao):
    saidas = [t for t in (sessao.get("transcript") or [])
              if t.get("direction") == "out"]
    return saidas[-1] if saidas else {}


def test_COMPORTAMENTAL_o_transcript_diz_FALHOU_quando_o_envio_falha():
    """🔴 O guarda que o juiz provou faltar. Este chama o MOTOR."""
    M2 = _motor_ao_vivo()
    ses = _sessao_viva()
    M2.handle_insurer_message(ses, TELA_FORM, interactive=INTER_DO_FORMULARIO,
                              flow_sender=lambda **k: False)
    texto = _ultima_saida(ses).get("text", "")
    assert "envio FALHOU" in texto, (
        "o transcript não disse que o envio falhou: " + repr(texto))
    assert "respondido" not in texto, (
        "o dossiê diz `respondido` para um formulário que estourou — é a "
        "contradição que chega a quem vai socorrer a pessoa")


def test_COMPORTAMENTAL_o_transcript_diz_RESPONDIDO_quando_da_certo():
    """A metade positiva: uma frase que dissesse sempre FALHOU passaria acima."""
    M2 = _motor_ao_vivo()
    ses = _sessao_viva()
    M2.handle_insurer_message(ses, TELA_FORM, interactive=INTER_DO_FORMULARIO,
                              flow_sender=lambda **k: True)
    texto = _ultima_saida(ses).get("text", "")
    assert "respondido" in texto and "FALHOU" not in texto, repr(texto)
    assert ses["state"] == "ura"


def test_COMPORTAMENTAL_B1_a_rajada_NAO_manda_a_resposta_duas_vezes():
    """🔴 O blocker que o juiz mediu, e que o guarda anterior não via.

    📊 Com linha de controle, rajada de duas bolhas com o MESMO `interactive`
    (que `message_buffer_service` preserva pela janela **de propósito**):

        bolha 2                                BASE  PRÉ-JUIZ  HEAD
        "Estamos verificando as informações…"    2       2       1

    ⚠️ A bolha *"você está na fila"* casa um passo `noop` e **retorna antes** da
    segunda chamada — por isso ela media 1 e o defeito parecia fechado. Este
    guarda usa uma bolha que **não** casa passo nenhum.
    """
    M2 = _motor_ao_vivo()
    ses = _sessao_viva()
    enviados = []

    def _transporte(**k):
        enviados.append(k)
        return True

    for bolha in (TELA_FORM, "Estamos verificando as informações, um instante."):
        M2.handle_insurer_message(ses, bolha, interactive=INTER_DO_FORMULARIO,
                                  flow_sender=_transporte)
    assert len(enviados) == 1, (
        "a resposta do formulário saiu %d vezes na mesma rajada — a segunda "
        "bolha carregou o `interactive` da janela" % len(enviados))


def test_CONTROLE_B1_a_bolha_do_formulario_MANDA_uma_vez():
    """§9.3 — um motor que nunca enviasse passaria no teste acima."""
    M2 = _motor_ao_vivo()
    ses = _sessao_viva()
    enviados = []

    def _transporte(**k):
        enviados.append(k)
        return True

    M2.handle_insurer_message(ses, TELA_FORM, interactive=INTER_DO_FORMULARIO,
                              flow_sender=_transporte)
    assert len(enviados) == 1, "a bolha do formulário não foi respondida"


def test_COMPORTAMENTAL_B3_envelope_ausente_NAO_e_envio_que_falhou():
    """🔴 O `raise` morava dentro do `try` do `formulario_envio_falhou`.

    O dossiê dizia *"pode ter chegado, não dá para saber"* sobre uma mensagem
    que **provadamente não saiu** — e quem tria decide diferente nos dois casos.
    """
    M2 = _motor_ao_vivo()
    ses = _sessao_viva()
    ses.pop("envelope_do_flow")
    # ⚠️ E o `interactive` também não pode trazer `name`: 📊
    # `registrar_formulario_nativo` reconstrói `envelope_do_flow` a partir
    # dele logo no começo do turno. Sem isto o teste mediria o ECO, não a
    # ausência — e ficaria verde com o defeito de pé.
    sem_envelope = {"kind": "flow", "options": [],
                    "flow": {"flow_id": "857030507196739",
                             "flow_token": "t", "cta": "Informar"}}
    enviados = []

    def _transporte(**k):
        enviados.append(k)
        return True

    M2.handle_insurer_message(ses, TELA_FORM, interactive=sem_envelope,
                              flow_sender=_transporte)
    assert not enviados, "chamou o transporte sem o envelope ecoado"
    assert ses["reason"] == "formulario_sem_envelope", repr(ses.get("reason"))
    assert "Nada saiu" in _ultima_saida(ses).get("text", "")


def test_a_familia_NOVA_tem_veredito_de_retomada_escrito():
    """⛔ Motivo não classificado cai no padrão silencioso — o defeito que a
    SPEC-085 existe para matar."""
    assert M._POLITICA_DE_RETOMADA.get("formulario_sem_envelope") == M.NAO_RETOMA


# ---------------------------------------------------------------------------
# 🔴 B2 — o segredo mora DENTRO da string JSON
# ---------------------------------------------------------------------------

def _com_segredo(metadata=True):
    params = {"flow_id": "857030507196739", "flow_cta": "Informar",
              "flow_token": "t:1:2"}
    if metadata:
        params["flow_metadata"] = {"flow_name": "Automóvel V2",
                                   "www_proxy_secret": "SEGREDO-DE-TERCEIRO",
                                   "flow_token_signature": "ASSINATURA"}
    return {"interactiveMessage": {
        "body": {"text": TEXTO_DA_TELA},
        "InteractiveMessage": {"NativeFlowMessage": {"buttons": [{
            "name": "galaxy_message", "buttonParamsJSON": json.dumps(params)}]}},
    }}


def test_B2_o_segredo_dentro_da_STRING_JSON_e_cortado():
    """🔴 O corte andava só por dicionário, e no fio `flow_metadata` viaja
    **dentro** do `buttonParamsJSON`, que é texto.

    📊 Medido pelo juiz no acervo de produção:

        www_proxy_secret dentro de string JSON ....... 4
        www_proxy_secret como chave jsonb ............ 0

    ⚠️ E o guarda anterior punha a chave num `header` — forma que **não ocorre
    no fio**. Fixture deduzido em vez de medido, dentro do conserto disso.
    """
    _, meta = P._interactive_from_message(_com_segredo())
    cru = json.dumps(meta.get("cru"), ensure_ascii=False)
    assert "SEGREDO-DE-TERCEIRO" not in cru, (
        "`www_proxy_secret` entrou no acervo durável")
    assert "ASSINATURA" not in cru, "`flow_token_signature` entrou no acervo"


def test_CONTROLE_B2_o_segredo_ESTAVA_la_e_o_RESTO_sobreviveu():
    """§9.3 — sem isto, um corte que apagasse tudo passaria acima."""
    payload = _com_segredo()
    assert "SEGREDO-DE-TERCEIRO" in json.dumps(payload, ensure_ascii=False)
    _, meta = P._interactive_from_message(payload)
    cru = json.dumps(meta.get("cru"), ensure_ascii=False)
    assert "857030507196739" in cru, "o corte levou junto o `flow_id`"
    assert "galaxy_message" in cru, "o corte levou junto o nome do envelope"
    assert meta["flow"]["flow_token"] == "t:1:2", (
        "o `flow_token` que a RESPOSTA precisa foi perdido na leitura")


# ---------------------------------------------------------------------------
# Os residuais que o juiz mediu
# ---------------------------------------------------------------------------

def test_o_formulario_DESCONHECIDO_com_botao_clicavel_usa_o_BOTAO():
    """📊 **21 telas** de azul/porto dizem *"Ou, se preferir, preencha o
    formulário abaixo"* — têm botão **e** formulário, e são as duas seguradoras
    **sem schema nenhum**. Mandá-las para `needs_human` trocaria 21 acionamentos
    que funcionam por 21 que param."""
    sessao = {"state": "ura", "slots": {}, "transcript": []}
    saida = M._responder_formulario_nativo(
        sessao, _playbook(),
        "Ou, se preferir, preencha o formulário abaixo.\n[FORMULARIO NATIVO: x]",
        interactive={"kind": "flow", "options": [{"id": "1", "title": "Digitar"}],
                     "flow": {"flow_id": "id-que-ninguem-conhece", "flow_token": "t",
                              "name": "galaxy_message", "cta": "x"}})
    assert saida is None, (
        "a tela com botão clicável foi para `needs_human` — o corredor tinha "
        "outro caminho e deixou de usá-lo")


def test_CONTROLE_sem_botao_o_desconhecido_CONTINUA_indo_para_gente():
    """§9.3 — a saída de emergência não pode virar a regra."""
    sessao = {"state": "ura", "slots": {}, "transcript": []}
    saida = M._responder_formulario_nativo(
        sessao, _playbook(), "[FORMULARIO NATIVO: x]",
        interactive={"kind": "flow", "options": [],
                     "flow": {"flow_id": "id-que-ninguem-conhece", "flow_token": "t",
                              "name": "galaxy_message", "cta": "x"}})
    assert saida is not None and saida["reason"] == "formulario_nativo_desconhecido"


def test_TRES_niveis_com_o_formulario_no_do_MEIO_e_lido():
    """📊 O juiz mediu que com três níveis o parser voltava a `buttons` — o
    sintoma exato da P-084-68. O fio tem dois; o laço não depende disso."""
    payload = {"interactiveMessage": {
        "body": {"text": TEXTO_DA_TELA},
        "InteractiveMessage": {
            "NativeFlowMessage": {"buttons": [{
                "name": "galaxy_message",
                "buttonParamsJSON": json.dumps({"flow_id": "857030507196739",
                                                "flow_token": "t", "flow_cta": "x"})}]},
            "interactiveMessage": {"algoMaisFundo": {"x": 1}},
        },
    }}
    _, meta = P._interactive_from_message(payload)
    assert meta["kind"] == "flow", "três níveis viraram " + repr(meta["kind"])


# ---------------------------------------------------------------------------
# 🔴 O SEGUNDO JUIZ — o veto que dois consertos meus tinham removido
# ---------------------------------------------------------------------------

def test_o_flow_name_SOBREVIVE_e_os_segredos_dele_NAO():
    """🔴 O corte era por CONTAINER e levava junto o rótulo do formulário.

    📊 Medido pelo segundo juiz: cortando `flow_metadata` inteiro, o `flow_name`
    — *"Automóvel - Informar endereço V2"* — sumia do acervo. Ele é o único
    rótulo legível do formulário e não é segredo de ninguém.

    ⚠️ Cortar por NOME é mais estreito que cortar por container. Os dois
    segredos continuam nomeados um a um.
    """
    payload = {"interactiveMessage": {
        "body": {"text": TEXTO_DA_TELA},
        "InteractiveMessage": {"NativeFlowMessage": {"buttons": [{
            "name": "galaxy_message",
            "buttonParamsJSON": json.dumps({
                "flow_id": "857030507196739", "flow_token": "t:1:2",
                "flow_metadata": {"flow_name": "Automóvel - Informar endereço V2",
                                  "flow_json_version": 703,
                                  "www_proxy_secret": "SEGREDO",
                                  "flow_token_signature": "ASSINATURA"}}),
        }]}},
    }}
    _, meta = P._interactive_from_message(payload)
    cru = json.dumps(meta.get("cru"), ensure_ascii=False)
    assert "Informar endereço V2" in cru, (
        "o `flow_name` sumiu do cru — o corte por container levou junto o "
        "único rótulo legível do formulário")
    assert "SEGREDO" not in cru and "ASSINATURA" not in cru, (
        "o segredo ficou: cortar por nome tem de alcançar os dois")


def test_o_VETO_pega_o_flow_id_que_veio_da_SESSAO():
    """🔴 O blocker do segundo juiz, e ele nasceu da SOMA de dois consertos meus.

    `registrar_formulario_nativo` grava `session["flow_id_ativo"]` **antes de
    qualquer veto**. A segunda chamada de `handle_insurer_message` passou a ser
    cega ao `interactive` (conserto do B1), então o veto contra o ARGUMENTO não
    podia rodar — e a moldura ecoava o id nunca conferido.

    📊 Medido, com linha de controle contra três commits::

        convite com flow_id que ninguém conhece + âncora conhecida
                        state        envios  flow_id ECOADO
        HEAD 88d2f31    ura             1    9999999999999999   ← errado
        dec2a74         needs_human     0    —
        BASE 8b49fdb    ura             1    857030507196739

    ⚠️ Vetar contra a SESSÃO fecha os dois caminhos, porque é dela que a moldura
    tira o id.
    """
    sessao = {"state": "ura", "slots": {}, "transcript": [],
              "flow_id_ativo": "9999999999999999", "flow_token": "t",
              "envelope_do_flow": "galaxy_message"}
    saida = M._responder_formulario_nativo(
        sessao, _playbook(), TEXTO_DA_TELA, interactive=None)
    assert saida is not None and saida["state"] == "needs_human", (
        "o id desconhecido que veio da SESSÃO foi respondido — é a resposta "
        "bem-endereçada e errada que o comentário da moldura diz impedir")
    assert saida["reason"] == "formulario_nativo_desconhecido"


def test_CONTROLE_o_veto_da_SESSAO_LIBERA_o_id_conhecido():
    """§9.3 — um veto que recusasse tudo pararia o produto inteiro."""
    sessao = {"state": "ura", "slots": dict(SLOTS_COMPLETOS), "transcript": [],
              "flow_id_ativo": "3206000179602236", "flow_token": "t",
              "envelope_do_flow": "galaxy_message"}
    saida = M._responder_formulario_nativo(
        sessao, _playbook(), TEXTO_DA_TELA, interactive=None)
    assert saida is not None
    assert saida.get("reason") != "formulario_nativo_desconhecido", (
        "o veto recusou um id que o playbook conhece")


def test_a_SESSAO_grava_o_flow_id_ativo():
    """🔴 O buraco que o segundo juiz mediu na bateria de mutação (MUT10).

    📊 Ele mutou `registrar_formulario_nativo` para parar de gravar
    `flow_id_ativo` e **191 testes continuaram verdes**. A metade "moldura"
    estava guardada; a metade "registro" não.

    ⚠️ Se ela quebrasse, **toda resposta à Yelum sairia com o id da HDI** — pelas
    palavras do próprio arquivo, *"o defeito mais silencioso desta SPEC"*,
    descartado sem erro e sem log.
    """
    sessao = {}
    M.registrar_formulario_nativo(sessao, {
        "kind": "flow",
        "flow": {"flow_id": "3206000179602236", "flow_token": "t:1:2",
                 "name": "galaxy_message", "cta": "Informar"}})
    assert sessao.get("flow_id_ativo") == "3206000179602236", (
        "a sessão parou de guardar o `flow_id` do convite — e é dele que a "
        "moldura tira o id que a seguradora confere")
    assert sessao.get("flow_token") == "t:1:2"
    assert sessao.get("envelope_do_flow") == "galaxy_message"
