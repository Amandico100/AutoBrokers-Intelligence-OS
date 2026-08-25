# -*- coding: utf-8 -*-
"""O desfecho não apaga o travamento da Fila — SPEC-085, juiz de confirmação.

🔴 **ESTE ARQUIVO NASCEU DE UM CONSERTO QUE VIROU DEFEITO**, e é o motivo de
ele ser comportamental em vez de leitura de fonte.

O painel tirou uma escrita sem filtro de `unblock_state` da reconciliação,
escrevendo que ela *"pisaria em `assumido_por_humano`"*. **No mesmo diff, pôs
uma escrita sem filtro da mesma coluna em `_encerrar_work_run`.** O guarda que
o painel deixou conferia uma STRING no fonte, e string não tem como enxergar
uma escrita nova a duzentas linhas de distância.

📊 O juiz de confirmação mediu, com o dublê de banco:

    1) checkpoint needs_human ....... unblock_state='travado'
    2) atendente clica ASSUMIR ...... unblock_state='assumido_por_humano'
    3) supersede (clear_active) ..... unblock_state='abandonado'
       >>> a Fila filtra unblock_state='travado' -> aparece? False

**Dois gatilhos vivos, os dois normais:**

- `insurer_closed` — *"a URA derrubou a conversa"*, a causa mais comum de
  travamento — chama `clear_active_dispatch` no mesmo turno do `needs_human`;
- `stale` inclui `needs_human`, então uma sessão travada é velha **na hora**:
  o segurado B pedindo chaveiro na mesma seguradora arquiva o caso do segurado A.

E `abandonado` é o verbo do HUMANO: é o que o botão *arquivar* grava, e
`test_arquivar_exige_motivo_escrito` exige motivo escrito porque *"arquivar é
dizer 'ninguém vai continuar isto'"*. A máquina arquivava sem motivo nenhum.

## 🔴 O QUE ESTE ARQUIVO GUARDA, EM UMA FRASE

> **Nenhum caminho automático tira da Fila um caso que ainda precisa de gente.**

Os guardas de análise estática dos outros arquivos continuam valendo — mas
nenhum deles conseguiria ficar vermelho aqui, e este consegue.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ROUTER_PY = RAIZ / "app" / "services" / "dispatch_router.py"


# ---------------------------------------------------------------------------
# O DUBLÊ — só os verbos que este caminho usa, e o `in_` com a regra do NULL
# ---------------------------------------------------------------------------

class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.b, self.t = banco, tabela
        self.op = None
        self.campos = None
        self.linhas = None
        self.filtros = []

    def select(self, *a, **k):
        self.op = "select"
        return self

    def insert(self, linhas):
        self.op = "insert"
        self.linhas = linhas if isinstance(linhas, list) else [linhas]
        return self

    def update(self, campos):
        self.op = "update"
        self.campos = campos
        return self

    def eq(self, col, val):
        self.filtros.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self.filtros.append(("in", col, [str(v) for v in vals]))
        return self

    def is_(self, col, val):
        self.filtros.append(("is", col, str(val)))
        return self

    def or_(self, expressao):
        self.filtros.append(("or", None, str(expressao)))
        return self

    def limit(self, n):
        return self

    def order(self, *a, **k):
        return self

    def _casa(self, linha) -> bool:
        for tipo, col, val in self.filtros:
            if tipo == "eq" and str(linha.get(col)) != str(val):
                return False
            if tipo == "in":
                # 🔴 `IN` NÃO CASA NULO — no Postgres e aqui. É por isso que
                # `_fechar_travamento` só alcança quem já tem marca: o
                # acionamento que foi bem termina com `unblock_state IS NULL` e
                # o `IN` passa ao largo dele.
                if linha.get(col) is None:
                    return False
                if str(linha.get(col)) not in val:
                    return False
            if tipo == "is":
                nulo = linha.get(col) is None
                if val == "null" and not nulo:
                    return False
                if val != "null" and nulo:
                    return False
        return True

    async def execute(self):
        tabela = self.b.dados.setdefault(self.t, [])
        if self.op == "insert":
            gravadas = []
            for l in self.linhas:
                linha = dict(l)
                linha.setdefault("id", f"id-{len(tabela)}-{self.t}")
                tabela.append(linha)
                gravadas.append(dict(linha))
            return _Resposta(gravadas)
        alvo = [l for l in tabela if self._casa(l)]
        if self.op == "update":
            for l in alvo:
                l.update(self.campos)
        return _Resposta([dict(l) for l in alvo])


class BancoFalso:
    def __init__(self):
        self.dados: dict = {}

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self, nome)


def _carregar_router():
    """Mesmo atalho de `test_o_travamento_vira_linha` — e ele DESFAZ o que injeta."""
    injetados = [n for n in ("app", "app.services") if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location(
            "_spec085_desfecho_router", str(ROUTER_PY))
        router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(router)
        return router
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


ROUTER = _carregar_router()

#: O filtro EXATO da Fila do BLOCO E (`acionamentos-travados/route.ts`, default
#: `estado=travado`). Se o caso não tem este valor, ninguém o vê.
NA_FILA = "travado"


def _banco_com(run_id: str, estado):
    b = BancoFalso()
    b.dados["work_runs"] = [{
        "id": run_id, "company_id": "c-resulta", "status": "waiting_input",
        "unblock_state": estado, "error_code": "needs_human:missing_slots",
    }]
    b.dados["work_events"] = []
    return b


def _linha(banco, run_id):
    return next(l for l in banco.dados["work_runs"] if l["id"] == run_id)


@contextmanager
def _com_o_pacote_app():
    """`app`/`app.services` de volta em `sys.modules` **durante a chamada**.

    🔴 SEM ISTO O ARQUIVO INTEIRO PASSAVA POR IGNORÂNCIA, e foi medido:
    `_progresso_da_fase` chama `_motor()`, que importa
    `app.services.insurer_dispatch_service`. O carregador acima desfaz os stubs
    no `finally` (de propósito, para não quebrar outros arquivos da sessão), o
    import levantava `ModuleNotFoundError`, e o `try/except` de
    `_encerrar_work_run` engolia::

        ERROR [ACIONAMENTO DURAVEL] run run-A nao foi encerrado (ModuleNotFoundError)
        RESULTADO: travado   <- "passou", e o UPDATE nunca rodou

    ⚠️ O verde vinha de o código **não chegar ao banco**. É a forma mais cara de
    teste falso: ele fica verde justamente quando o produto está quebrado.
    """
    nomes = ("app", "app.services")
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


async def _encerrar(banco, run_id, fase, motivo="supersede", status=None):
    """Chama a função REAL, com o banco trocado pelo dublê.

    ⚠️ `_encerrar_work_run` pega o banco sozinha (`await _db()`), então o dublê
    entra por aí — passá-lo como argumento seria testar uma assinatura que não
    existe.

    🔴 E ELA **PROVA QUE CHEGOU AO BANCO** antes de devolver. Ver
    `_com_o_pacote_app`: sem essa prova, todo teste de proibição deste arquivo
    fica verde quando o caminho morre antes do `UPDATE`.
    """
    async def _db_falso():
        return banco

    antes = dict(_linha(banco, run_id))
    original = ROUTER._db
    ROUTER._db = _db_falso
    try:
        with _com_o_pacote_app():
            await ROUTER._encerrar_work_run(
                "c-resulta", {"work_run_id": run_id, "state": fase},
                motivo=motivo, status=status)
    finally:
        ROUTER._db = original

    depois = _linha(banco, run_id)
    assert depois.get("finished_at") and depois.get("result_summary"), (
        "`_encerrar_work_run` não chegou ao UPDATE — o `try/except` dela engoliu "
        "alguma coisa. QUALQUER asserção de proibição deste arquivo seria verde "
        f"por ignorância. antes={antes.get('status')!r} depois={depois.get('status')!r}")


# ---------------------------------------------------------------------------
# 1. O DEFEITO MEDIDO — supersede não pode arquivar quem espera gente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("fase,motivo", [
    ("needs_human", "supersede: novo acionamento na mesma seguradora"),
    ("needs_human", "insurer_closed: a URA derrubou a conversa"),
])
async def test_o_supersede_NAO_tira_o_travamento_da_fila(fase, motivo):
    """🔴 O cenário concreto, com nome e ordem.

    Corretora Resulta, URA da Allianz. O segurado A trava por `missing_slots` e
    aparece na Fila. Minutos depois o segurado B pede chaveiro **na mesma
    seguradora**: `start_live_dispatch` → supersede → `clear_active_dispatch`.

    Se o desfecho apagar a marca de A, **ninguém nunca mais é chamado** — e não
    há erro nenhum, o caso simplesmente some da tela.
    """
    banco = _banco_com("run-A", "travado")
    await _encerrar(banco, "run-A", fase, motivo)
    assert _linha(banco, "run-A")["unblock_state"] == NA_FILA, (
        "o desfecho automático tirou da Fila um caso que ainda precisa de "
        "gente — é o defeito que esta SPEC existe para impedir, por dentro")


@pytest.mark.asyncio
async def test_a_maquina_NUNCA_grava_abandonado():
    """`abandonado` é o verbo do HUMANO, e ele custa um motivo escrito.

    `test_arquivar_exige_motivo_escrito` obriga quem clica em *arquivar* a
    escrever por quê, porque *"arquivar é dizer 'ninguém vai continuar isto'.
    Sem motivo, o caso some e ninguém sabe por quê"*. Máquina que arquiva
    sozinha faz exatamente isso, sem o motivo.
    """
    for fase in ("needs_human", "ura", "human_phase", "", None):
        banco = _banco_com("run-X", "travado")
        await _encerrar(banco, "run-X", fase, "qualquer motivo")
        assert _linha(banco, "run-X")["unblock_state"] != "abandonado", (
            f"o desfecho da fase {fase!r} arquivou o caso sozinho")


@pytest.mark.asyncio
async def test_o_desfecho_NAO_pisa_em_quem_assumiu():
    """A pessoa clicou em ASSUMIR. O nome dela não pode ser apagado por varredura."""
    banco = _banco_com("run-M", "assumido_por_humano")
    _linha(banco, "run-M")["unblock_owner"] = "u-maria"
    for fase, status in (("needs_human", None), ("captured", None),
                         ("monitoring", "completed")):
        await _encerrar(banco, "run-M", fase, "desfecho qualquer", status=status)
        assert _linha(banco, "run-M")["unblock_state"] == "assumido_por_humano", (
            f"a fase {fase!r} apagou o estado de quem assumiu o caso")
        assert _linha(banco, "run-M")["unblock_owner"] == "u-maria"


# ---------------------------------------------------------------------------
# 2. OS CONTROLES — §9.3: prove que ele CONSEGUE ficar diferente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_CONTROLE_POSITIVO_o_desfecho_BOM_fecha_o_travamento():
    """Sem este, os três testes acima passariam com `_fechar_travamento`
    apagada do código — bastaria nunca escrever nada. Um guarda que só proíbe
    não prova que a peça faz alguma coisa."""
    for antes in ("travado", "retomado_pelo_robo"):
        banco = _banco_com("run-B", antes)
        await _encerrar(banco, "run-B", "monitoring", "acionamento concluído",
                        status="completed")
        assert _linha(banco, "run-B")["unblock_state"] == "resolvido", (
            f"um travamento em {antes!r} que TERMINOU BEM continuou na Fila — "
            "a Fila vira aterro e a corretora aprende a ignorar a tela")


@pytest.mark.asyncio
async def test_CONTROLE_o_acionamento_QUE_FOI_BEM_termina_em_NULL():
    """A propriedade que `decidir_travamento` declara por escrito: *acionamento
    que vai bem termina com `unblock_state IS NULL`*.

    🔴 Ela é o que faz a coluna significar alguma coisa. A primeira versão do
    conserto gravava `resolvido` em TODO run bem-sucedido — 📊 medido pelo juiz
    (`monitoring`: `None` → `'resolvido'`) —, e aí `?estado=all` passaria a
    listar todo acionamento que deu certo desde sempre.
    """
    banco = _banco_com("run-OK", None)
    await _encerrar(banco, "run-OK", "monitoring", "acionamento concluído",
                    status="completed")
    assert _linha(banco, "run-OK")["unblock_state"] is None, (
        "um acionamento que nunca travou saiu marcado — a coluna deixou de "
        "distinguir travamento de acionamento normal")


@pytest.mark.asyncio
async def test_CONTROLE_o_dublê_CONSEGUE_gravar_a_coluna():
    """§9.3 — prove que o alvo é alcançável.

    Se o dublê não aplicasse `update` nesta tabela, TODOS os testes de proibição
    acima passariam por ignorância, e o arquivo inteiro seria decorativo.
    """
    banco = _banco_com("run-C", "travado")
    await (banco.client.table("work_runs")
           .update({"unblock_state": "abandonado"}).eq("id", "run-C").execute())
    assert _linha(banco, "run-C")["unblock_state"] == "abandonado", (
        "o dublê não grava a coluna — as proibições deste arquivo não provam nada")
