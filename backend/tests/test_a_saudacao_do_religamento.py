# -*- coding: utf-8 -*-
"""A saudação do religamento — SPEC-093, BLOCO D.

> 🔴 **Decisão do Founder, 25/08:** ao religar, o agente **saúda e pergunta**.
> Não retoma, não age, não presume.

📊 **O tamanho da coisa, medido:** o robô teve **4 conversas de WhatsApp em toda
a história do produto** — 21.901 das 23.028 mensagens são Espelho de conversa
**humana**.

> **A primeira vez que isto rodar será a maior coisa que este produto já mandou
> sozinho.**

Por isso este arquivo guarda, antes de tudo, as três recusas — e o gate ⑥, que
é a linha de controle: **agente ligado o tempo todo → ZERO saudações.** Sem ele,
um bug que saúde sempre passa como sucesso.

## ⛔ E nada aqui manda mensagem

Todo envio passa por um dublê. `send_to_client_guarded` é chamado com o que o
produto chamaria — e o dublê só anota. Nenhuma linha deste arquivo alcança o
Evolution, o Redis ou o banco de produção.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SERVICO_PY = RAIZ / "app" / "services" / "saudacao_do_religamento.py"
LOJA_TS = RAIZ.parent / "lib" / "admin" / "tenant-agent-store.ts"
TRANSICAO_TS = RAIZ.parent / "lib" / "admin" / "toggle-transicao.ts"
MJS_TOGGLE = RAIZ.parent / "scripts" / "spec093-toggle.test.mjs"


def _carregar():
    """Carrega o serviço sem arrastar o pacote `app` inteiro."""
    injetados = [n for n in ("app", "app.services") if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location(
            "_spec093_saudacao", str(SERVICO_PY))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


S = _carregar()
AGORA = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)


def _ha(horas: float) -> str:
    return (AGORA - timedelta(hours=horas)).isoformat()


def _rodar(coro):
    return asyncio.run(coro)


# ===========================================================================
# O DUBLÊ — conversas, mensagens, saudações já enviadas, e o envio
# ===========================================================================

class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, b, t):
        self.b, self.t, self.op, self.linhas, self.campos = b, t, None, None, None
        self.filtros = []

    def select(self, *a, **k):
        self.op = "select"
        return self

    def insert(self, l):
        self.op, self.linhas = "insert", l if isinstance(l, list) else [l]
        return self

    def update(self, c):
        self.op, self.campos = "update", c
        return self

    def eq(self, c, v):
        self.filtros.append(("eq", c, v))
        return self

    def gte(self, c, v):
        self.filtros.append(("gte", c, v))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def _casa(self, l):
        for tipo, c, v in self.filtros:
            if tipo == "eq" and str(l.get(c)) != str(v):
                return False
            if tipo == "gte" and str(l.get(c) or "") < str(v):
                return False
        return True

    async def execute(self):
        tab = self.b.dados.setdefault(self.t, [])
        if self.op == "insert":
            for l in self.linhas:
                chave = (l.get("company_id"), l.get("conversation_id"),
                         l.get("inbound_message_id"))
                # 🔴 O UNIQUE do banco, no dublê. Sem ele o teste de
                # idempotência ficaria verde por o dublê ser permissivo.
                if any((x.get("company_id"), x.get("conversation_id"),
                        x.get("inbound_message_id")) == chave for x in tab):
                    raise RuntimeError(
                        'duplicate key value violates unique constraint '
                        '"uq_saudacoes_enviadas_chave" (23505)')
                tab.append(dict(l))
            return _R(list(self.linhas))
        alvo = [l for l in tab if self._casa(l)]
        if self.op == "update":
            for l in alvo:
                l.update(self.campos)
        # `messages` sai do mais novo para o mais velho (o serviço pede desc)
        if self.t == "messages":
            alvo = sorted(alvo, key=lambda l: str(l.get("created_at") or ""),
                          reverse=True)
        return _R([dict(l) for l in alvo])


class Banco:
    def __init__(self):
        self.dados = {"conversations": [], "messages": [], "saudacoes_enviadas": [],
                      "agents": []}

    @property
    def client(self):
        return self

    def table(self, n):
        return _Q(self, n)


class Correio:
    """O dublê do envio. ⛔ Nada sai daqui."""

    def __init__(self, resposta=None):
        self.enviadas = []
        self.resposta = resposta or {"ok": True, "queued": False}

    async def __call__(self, company_id, phone, text, kind="other", summary="",
                       *, temperatura="fria", **k):
        self.enviadas.append({"company_id": company_id, "phone": phone,
                              "text": text, "kind": kind,
                              "temperatura": temperatura})
        return dict(self.resposta)


def _montar(conversas, banco=None):
    b = banco or Banco()
    for c in conversas:
        b.dados["conversations"].append({
            "id": c["id"], "company_id": c.get("company_id", "c-resulta"),
            "status": c.get("status", "open"),
            "claimed_by": c.get("claimed_by"), "claimed_by_name": c.get("claimed_by_name"),
            "user_name": c.get("user_name", "Maria Silva"),
            "user_phone": c.get("user_phone", "5511900000000"),
            "last_message_at": c.get("ultima", _ha(2)), "channel": "whatsapp",
        })
        b.dados["messages"].append({
            "id": c.get("msg_id", f"m-{c['id']}"), "conversation_id": c["id"],
            "role": "user", "created_at": c.get("ultima", _ha(2)),
        })
        if c.get("respondida_por_assistant"):
            b.dados["messages"].append({
                "id": f"a-{c['id']}", "conversation_id": c["id"], "role": "assistant",
                "created_at": (datetime.fromisoformat(c.get("ultima", _ha(2)))
                               + timedelta(minutes=5)).isoformat(),
            })
    return b


def _com_banco(banco, correio=None):
    """Troca `_db` e o envio pelos dublês, e devolve tudo no fim."""
    class _Ctx:
        def __enter__(self):
            self.db = S._db

            async def _banco():
                # 🔴 ASYNC porque o `_db` do serviço é async. 📊 Um dublê
                # síncrono aqui devolveria um objeto que não é o banco, e o
                # `await` no serviço estouraria — ou pior, `.execute()` viraria
                # coroutine nunca aguardada: um SELECT que nunca acontece.
                return banco

            S._db = _banco
            if correio is not None:
                mod = types.ModuleType("app.services.platform_outbound")
                mod.FRIA = "fria"
                mod.QUENTE = "quente"
                mod.send_to_client_guarded = correio
                self.antes = sys.modules.get("app.services.platform_outbound")
                self.app = [n for n in ("app", "app.services") if n not in sys.modules]
                for n in self.app:
                    m = types.ModuleType(n)
                    m.__path__ = [str(RAIZ / Path(*n.split(".")))]
                    sys.modules[n] = m
                sys.modules["app.services.platform_outbound"] = mod
            return self

        def __exit__(self, *a):
            S._db = self.db
            if correio is not None:
                if self.antes is None:
                    sys.modules.pop("app.services.platform_outbound", None)
                else:
                    sys.modules["app.services.platform_outbound"] = self.antes
                for n in self.app:
                    sys.modules.pop(n, None)
            return False
    return _Ctx()


# ===========================================================================
# ① 3 mensagens de 2h → 3 saudações, pelo caminho FRIO
# ===========================================================================

def test_GATE_1_tres_mensagens_de_2h_tres_saudacoes_pelo_caminho_FRIO():
    b = _montar([{"id": f"conv-{i}", "ultima": _ha(2)} for i in (1, 2, 3)])
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))

    assert r["enviadas"] == 3, f"esperava 3 saudações, veio {r}"
    assert len(correio.enviadas) == 3
    # 🔴 O CAMINHO. `platform_outbound` já tem teto de 12/h, 20/dia, janela
    # 08–20 e domingo bloqueado — a saudação sai por ele, e não por código novo.
    assert {e["temperatura"] for e in correio.enviadas} == {"fria"}, (
        "a saudação saiu QUENTE — ela pularia o governador inteiro, que é "
        "exatamente o que faria as 'cinquenta às 8h'")
    assert {e["kind"] for e in correio.enviadas} == {"saudacao_religamento"}


def test_a_saudacao_SAUDA_E_PERGUNTA_e_nao_retoma():
    """*"saúda e pergunta. Não retoma, não age, não presume."*"""
    recente = S.texto_da_saudacao("recente", nome="Maria Silva")
    demorada = S.texto_da_saudacao("demorada", nome="Maria Silva")
    assert recente.startswith("Oi Maria!")
    assert "?" in recente, "a saudação não PERGUNTA"
    assert "Desculpe a demora" in demorada and "Desculpe a demora" not in recente, (
        "as duas faixas mandam a mesma coisa — a demora não está nomeada")
    # sem nome não vira "Oi !"
    assert S.texto_da_saudacao("recente").startswith("Oi!")


# ===========================================================================
# ② mensagem de 30h → NÃO envia, vai para a fila
# ===========================================================================

@pytest.mark.parametrize("horas,envia,faixa", [
    (0.5, True, "recente"), (11.9, True, "recente"),
    (12.1, True, "demorada"), (23.9, True, "demorada"),
    (24.1, False, "velha"), (30.0, False, "velha"), (7 * 24, False, "velha"),
])
def test_GATE_2_as_tres_faixas_de_idade(horas, envia, faixa):
    """📊 Acima de 24h a janela da Meta já exige template — a regra de produto e
    a regra do canal dão a mesma resposta. E 📊 181 das 234 têm mais de 7 dias:
    ali a saudação é exumação, não recuperação."""
    d = S.decidir_saudacao({"ultima_inbound_em": _ha(horas)}, agora=AGORA)
    assert d["envia"] is envia, f"{horas}h decidiu {d}"
    assert d["faixa"] == faixa


def test_GATE_2b_a_velha_nao_chega_ao_correio():
    b = _montar([{"id": "conv-velha", "ultima": _ha(30)}])
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
    assert correio.enviadas == [], "uma conversa de 30h recebeu mensagem"
    assert r["enviadas"] == 0
    assert b.dados["saudacoes_enviadas"] == [], (
        "a conversa velha consumiu a chave de idempotência sem ser enviada")


# ===========================================================================
# ③ 🔴 desligar/ligar duas vezes → 1 saudação (a chave é a MENSAGEM)
# ===========================================================================

def test_GATE_3_desligar_e_ligar_duas_vezes_UMA_saudacao():
    """🔴 A chave é a mensagem, não o clique.

    Chavear no evento de toggle mandaria duas saudações para a mesma pessoa.
    """
    b = _montar([{"id": "conv-1", "ultima": _ha(2), "msg_id": "msg-abc"}])
    correio = Correio()
    with _com_banco(b, correio):
        r1 = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
        r2 = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))

    assert r1["enviadas"] == 1
    assert r2["enviadas"] == 0 and r2["ja_saudadas"] == 0, (
        f"o segundo religamento mandou de novo: {r2}")
    assert len(correio.enviadas) == 1, (
        f"a mesma pessoa recebeu {len(correio.enviadas)} saudações")
    assert len(b.dados["saudacoes_enviadas"]) == 1


def test_GATE_3b_mensagem_NOVA_do_cliente_gera_chave_NOVA():
    """§9.3 — prove que as duas coisas CONSEGUEM ser diferentes.

    🔴 Sem esta linha, um bug que nunca envia passaria no gate ③ acima.
    """
    b = _montar([{"id": "conv-1", "ultima": _ha(2), "msg_id": "msg-abc"}])
    correio = Correio()
    with _com_banco(b, correio):
        _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
        # o cliente escreve de novo, e ninguém respondeu
        b.dados["messages"].append({"id": "msg-xyz", "conversation_id": "conv-1",
                                    "role": "user", "created_at": _ha(1)})
        b.dados["conversations"][0]["last_message_at"] = _ha(1)
        r2 = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))

    assert r2["enviadas"] == 1, f"mensagem nova não gerou saudação nova: {r2}"
    assert len(correio.enviadas) == 2


def test_a_reserva_vem_ANTES_do_envio():
    """⚠️ Morrer no meio deixa uma saudação que não sai — nunca duas que saem.

    Mandar a mesma mensagem duas vezes para um segurado é o dano sem desfazer.
    """
    b = _montar([{"id": "conv-1", "ultima": _ha(2)}])
    vistos = []

    class CorreioQueOlha(Correio):
        async def __call__(self, *a, **k):
            vistos.append(len(b.dados["saudacoes_enviadas"]))
            return await Correio.__call__(self, *a, **k)

    with _com_banco(b, CorreioQueOlha()):
        _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
    assert vistos == [1], (
        "a chave foi gravada DEPOIS do envio — uma queda no meio manda duas")


def test_enfileirada_pelo_governador_TAMBEM_consome_a_chave():
    """⚠️ `queued=True` é sucesso: o governador aceitou e a fila entrega.

    Devolver a reserva aqui mandaria a segunda quando a primeira está a caminho.
    """
    b = _montar([{"id": "conv-1", "ultima": _ha(2)}])
    correio = Correio(resposta={"ok": True, "queued": True, "reason": "governador"})
    with _com_banco(b, correio):
        r1 = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
        r2 = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
    assert r1["enfileiradas"] == 1 and r1["enviadas"] == 0
    assert len(correio.enviadas) == 1, "a enfileirada foi mandada duas vezes"
    assert r2["enviadas"] == 0


# ===========================================================================
# ④ conversa com `claimed_by` → NÃO envia   ·   ⑤ `assistant` posterior
# ===========================================================================

@pytest.mark.parametrize("conversa,motivo", [
    ({"claimed_by": "u-1"}, "reivindicada_por_pessoa"),
    ({"claimed_by_name": "Regina"}, "reivindicada_por_pessoa"),
    ({"status": "HUMAN_REQUESTED"}, "handoff_humano"),
    ({"status": "human_requested"}, "handoff_humano"),
    ({"ja_respondida": True}, "ja_respondida"),
])
def test_GATE_4_e_5_as_tres_proibicoes(conversa, motivo):
    """🔴 As três vêm ANTES da idade: uma conversa reivindicada não é saudada
    **nem quando é recente**."""
    d = S.decidir_saudacao({**conversa, "ultima_inbound_em": _ha(1)}, agora=AGORA)
    assert d["envia"] is False and d["motivo"] == motivo, d


def test_GATE_5b_resposta_HUMANA_pelo_celular_ja_conta_como_respondida():
    """📊 As linhas do Espelho chegam como `role='assistant'`.

    ⚠️ Não é acidente feliz — é a razão de a checagem ser por PAPEL e não por
    autor: a atendente respondendo do celular dela fecha a conversa igual.
    """
    b = _montar([{"id": "conv-1", "ultima": _ha(3),
                  "respondida_por_assistant": True}])
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
    assert correio.enviadas == [], "saudou quem já tinha sido respondido"
    assert r["enviadas"] == 0


def test_CONTROLE_a_mesma_conversa_SEM_a_proibicao_seria_saudada():
    """§9.3 — prove que a proibição é o que barra, e não o cenário inteiro."""
    b = _montar([{"id": "conv-1", "ultima": _ha(3)}])
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
    assert r["enviadas"] == 1, (
        "sem proibição nenhuma a conversa também não foi saudada — os testes "
        "④ e ⑤ estariam passando pelo motivo errado")


# ===========================================================================
# ⑥ 🔴 A LINHA DE CONTROLE OBRIGATÓRIA — agente ligado o tempo todo
# ===========================================================================

def test_GATE_6_CONTROLE_agente_ligado_o_tempo_todo_ZERO_saudacoes():
    """🔴 **Obrigatório.** Sem ele, um bug que saúde sempre passa como sucesso.

    Um clique de `ligar` num agente que **já estava ligado** não é religamento:
    não muda coluna nenhuma, não limpa `desligado_em`, e não dispara rodada.
    """
    assert "export function decidirTransicaoDoToggle" in TRANSICAO_TS.read_text(
        encoding="utf-8")
    loja = LOJA_TS.read_text(encoding="utf-8")
    assert "decidirTransicaoDoToggle" in loja, (
        "a loja parou de usar a decisão pura — a lógica voltou para dentro do "
        "handler, onde o gate em `node` não a alcança")

    # e a decisão pura, do lado de cá, tem a mesma forma
    assert "if (transicao.desligou) campos.desligado_em" in loja
    assert "if (transicao.religou) campos.desligado_em = null;" in loja
    # 🔴 o clique que não muda nada NÃO toca na coluna
    i = loja.index("const campos: Record<string, unknown> = {")
    trecho = loja[i:loja.index("const { error } = await supabase.from('agents')", i)]
    assert trecho.count("desligado_em") == 2, (
        "`desligado_em` é escrito fora das duas transições — apertar `desligar` "
        "duas vezes rejuvenesceria o desligamento, e conversas passadas de 24h "
        "voltariam a parecer recentes")


def test_GATE_6b_o_toggle_sem_transicao_nao_religa():
    """A decisão pura, executada em `node` de verdade.

    🔴 O `.mjs` roda A PARTIR DAQUI porque 📊 já aconteceu neste repositório
    de um `scripts/*.test.mjs` existir e **ninguém executá-lo** — não no
    `gate.yml`, não no `package.json`, em nenhum pytest. O `gate.yml` roda
    `python -m pytest tests/ -q`; então é daqui que ele passa a rodar.

    ⚠️ E `toggle-transicao.ts` **não tem import nenhum** de propósito: 📊 `node`
    não resolve o alias `@/` de `tenant-agent-store.ts`, e um gate que
    precisasse dele seria um gate que ninguém roda.
    """
    r = _rodar_mjs(MJS_TOGGLE)
    assert r.returncode == 0, (r.stdout or "")[-2000:] + (r.stderr or "")[-500:]
    assert "0 falharam" in (r.stdout or ""), (r.stdout or "")[-600:]


def test_CONTROLE_o_executor_do_mjs_CONSEGUE_ver_vermelho():
    """§9.3 — um executor que nunca vê falha não é executor."""
    falso = MJS_TOGGLE.parent / "_controle_toggle_falha.test.mjs"
    linhas = [
        "let p=0,f=0;",
        "function assert(n,c){if(c){p++}else{f++;console.log('  x '+n)}}",
        "assert('esta asserção é falsa DE PROPÓSITO', false);",
        "console.log(`== Resumo: ${p} passaram, ${f} falharam ==`);",
        "process.exit(f ? 1 : 0);",
    ]
    falso.write_text(chr(10).join(linhas), encoding="utf-8")
    try:
        r = _rodar_mjs(falso)
        assert r.returncode != 0, (
            "o executor devolveu 0 para um teste que FALHA — ele não consegue "
            "ver vermelho, e portanto não guarda nada")
        assert "1 falharam" in (r.stdout or "")
    finally:
        falso.unlink(missing_ok=True)

def _rodar_mjs(caminho: Path):
    import os
    import shutil
    import subprocess

    exe = shutil.which("node")
    if exe is None:
        pytest.skip("node ausente neste ambiente")
    return subprocess.run(
        [exe, str(caminho)], cwd=str(RAIZ.parent), capture_output=True, text=True,
        timeout=90, encoding="utf-8", errors="replace",
        env={**os.environ, "NODE_OPTIONS": ""})


# ===========================================================================
# ⑦ 40 conversas elegíveis → o governador segura, não dispara 40
# ===========================================================================

def test_GATE_7_quarenta_elegiveis_o_governador_SEGURA():
    """🔴 O limitador já existe. Não construa outro (`CLAUDE.md` §5).

    📊 `platform_outbound`: teto 12/h e 20/dia, espaçamento sorteado 241–479 s,
    janela 08:00–20:00, domingo bloqueado, parada de emergência por corretora.
    """
    b = _montar([{"id": f"conv-{i}", "ultima": _ha(2)} for i in range(40)])
    # o governador aceita 12 e enfileira o resto — é o que ele faz de verdade
    entregues = {"n": 0}

    class Governado(Correio):
        async def __call__(self, *a, **k):
            entregues["n"] += 1
            self.resposta = ({"ok": True, "queued": False} if entregues["n"] <= 12
                             else {"ok": True, "queued": True, "reason": "governador"})
            return await Correio.__call__(self, *a, **k)

    correio = Governado()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))

    assert r["enviadas"] == 12, f"o governador não segurou: {r}"
    assert r["enfileiradas"] == 28
    assert {e["temperatura"] for e in correio.enviadas} == {"fria"}


def test_o_servico_NAO_constroi_limitador_proprio():
    """⛔ `CLAUDE.md` §5 — consolidar e migrar antes de duplicar."""
    fonte = SERVICO_PY.read_text(encoding="utf-8")
    for proibido in ("_TETO_HORA", "_TETO_DIA", "sleep(", "asyncio.sleep",
                     "randint", "_JANELA_ABRE", "_INTERVALO"):
        assert proibido not in fonte, (
            f"`{proibido}` apareceu no serviço — um segundo limitador ao lado "
            "do que já existe é exatamente a proibição estrutural do §5")
    assert "send_to_client_guarded" in fonte and "FRIA" in fonte


# ===========================================================================
# ⑧ dois tenants: a saudação de um não vaza para o outro
# ===========================================================================

def test_GATE_8_a_saudacao_de_uma_corretora_nao_vaza_para_a_outra():
    b = _montar([{"id": "conv-r", "ultima": _ha(2), "company_id": "c-resulta"}])
    _montar([{"id": "conv-a", "ultima": _ha(2), "company_id": "c-autofleet",
              "user_phone": "5511911111111"}], banco=b)
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))

    assert r["enviadas"] == 1
    assert [e["company_id"] for e in correio.enviadas] == ["c-resulta"]
    assert all(e["phone"] != "5511911111111" for e in correio.enviadas), (
        "o telefone da AutoFleet recebeu a saudação da Resulta")
    assert [l["company_id"] for l in b.dados["saudacoes_enviadas"]] == ["c-resulta"]


def test_CONTROLE_a_outra_corretora_CONSEGUE_ser_saudada():
    """§9.3 — prove que as duas conseguem ser diferentes."""
    b = _montar([{"id": "conv-r", "ultima": _ha(2), "company_id": "c-resulta"}])
    _montar([{"id": "conv-a", "ultima": _ha(2), "company_id": "c-autofleet"}], banco=b)
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-autofleet", confirmado=True, agora=AGORA))
    assert r["enviadas"] == 1
    assert [e["company_id"] for e in correio.enviadas] == ["c-autofleet"]


# ===========================================================================
# D.5 — a prévia, no primeiro religar
# ===========================================================================

def test_D5_o_primeiro_religamento_NAO_envia_sem_confirmacao():
    """📊 O robô teve **4 conversas** em toda a história do produto.

    ⚠️ Uma tela é o guarda mais barato que existe.
    """
    b = _montar([{"id": f"conv-{i}", "ultima": _ha(2)} for i in range(3)])
    correio = Correio()
    with _com_banco(b, correio):
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=False, agora=AGORA))

    assert correio.enviadas == [], "o primeiro religamento mandou sem confirmar"
    assert r["ok"] is False and r["motivo"] == "confirmacao_necessaria"
    assert r["previa"]["total"] == 3
    assert len(r["previa"]["conversas"]) == 3
    assert r["previa"]["primeiro_religamento"] is True


def test_D5_o_SEGUNDO_religamento_nao_pede_confirmacao_de_novo():
    b = _montar([{"id": "conv-1", "ultima": _ha(2)}])
    correio = Correio()
    with _com_banco(b, correio):
        _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
        b.dados["messages"].append({"id": "msg-2", "conversation_id": "conv-1",
                                    "role": "user", "created_at": _ha(1)})
        r = _rodar(S.enviar_saudacoes("c-resulta", confirmado=False, agora=AGORA))
    assert r.get("motivo") != "confirmacao_necessaria", r
    assert r["enviadas"] == 1


def test_D5_a_previa_NAO_mostra_telefone_nem_nome_inteiro():
    """⛔ `CLAUDE.md` §13.3 — presença, nunca conteúdo."""
    b = _montar([{"id": "conv-1", "ultima": _ha(2), "user_name": "Maria Silva Souza",
                  "user_phone": "5511987654321"}])
    with _com_banco(b):
        p = _rodar(S.previa("c-resulta", agora=AGORA))
    despejo = repr(p)
    assert "5511987654321" not in despejo, "o telefone inteiro foi para a tela"
    assert "Silva" not in despejo and "Souza" not in despejo, (
        "o sobrenome foi para a tela")
    assert p["conversas"][0]["quem"] == "Maria ····4321"


# ===========================================================================
# FALHA FECHADA — não conseguir ler o que já foi enviado NÃO é permissão
# ===========================================================================

def test_anti_duplicata_ilegivel_NAO_vira_permissao_para_enviar():
    """🔴 Um `set()` vazio no lugar do erro mandaria tudo de novo."""
    b = _montar([{"id": "conv-1", "ultima": _ha(2)}])

    class BancoQuebrado(Banco):
        def table(self, n):
            if n == "saudacoes_enviadas":
                raise RuntimeError("PostgREST fora")
            return Banco.table(self, n)

    quebrado = BancoQuebrado()
    quebrado.dados = b.dados
    correio = Correio()
    with _com_banco(quebrado, correio):
        with pytest.raises(RuntimeError):
            _rodar(S.enviar_saudacoes("c-resulta", confirmado=True, agora=AGORA))
    assert correio.enviadas == [], "mandou mesmo sem saber o que já tinha sido enviado"


def test_relogio_adiantado_nao_vira_conversa_demorada():
    """Uma mensagem com data no futuro não pode virar 'faz 13h'."""
    d = S.decidir_saudacao(
        {"ultima_inbound_em": (AGORA + timedelta(hours=5)).isoformat()}, agora=AGORA)
    assert d["envia"] is True and d["faixa"] == "recente"


def test_sem_mensagem_do_cliente_nao_ha_o_que_saudar():
    assert S.decidir_saudacao({}, agora=AGORA)["motivo"] == "sem_mensagem_do_cliente"
    assert S.decidir_saudacao({"ultima_inbound_em": "lixo"},
                              agora=AGORA)["motivo"] == "sem_mensagem_do_cliente"


# ===========================================================================
# A PORTA — e por que o envio é POST
# ===========================================================================

ROTA_PY = RAIZ / "app" / "api" / "saudacao_religamento.py"


def test_a_previa_e_GET_e_o_envio_e_POST():
    """🔴 Um verbo que um prefetch de navegador dispara não pode ser o que
    manda mensagem. 📊 O robô teve 4 conversas em toda a história do produto."""
    fonte = ROTA_PY.read_text(encoding="utf-8")
    assert '@router.get("/api/saudacao-religamento/previa")' in fonte
    assert '@router.post("/api/saudacao-religamento/enviar")' in fonte
    assert '@router.get("/api/saudacao-religamento/enviar")' not in fonte


def test_o_confirmado_vem_do_CORPO_e_so_True_literal_vale():
    """⛔ Link com `?confirmado=true` é compartilhável, colável e clicável por
    engano. E `"false"` é uma string VERDADEIRA em Python — que é exatamente
    o que um formulário manda."""
    fonte = ROTA_PY.read_text(encoding="utf-8")
    assert 'confirmado = payload.get("confirmado") is True' in fonte, (
        "o `confirmado` deixou de exigir `True` literal — uma string 'false' "
        "passaria a autorizar o envio")
    assert "confirmado: bool" not in fonte, (
        "`confirmado` virou parâmetro de query — dá para mandar por link")


def test_a_porta_exige_a_chave_interna():
    fonte = ROTA_PY.read_text(encoding="utf-8")
    assert fonte.count("_require_internal_key(x_autobrokers_internal_key)") == 2, (
        "algum endpoint da saudação ficou sem a chave interna")


def test_o_router_esta_REGISTRADO():
    """§9.3 — 📊 um `.test.mjs` sem executor já aconteceu aqui. Uma rota sem
    `include_router` é a mesma família: existe e ninguém alcança."""
    main = (RAIZ / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.api.saudacao_religamento import router" in main
    assert "app.include_router(saudacao_religamento_router" in main
