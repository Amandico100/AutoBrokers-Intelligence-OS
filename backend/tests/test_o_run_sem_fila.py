"""O run que nasce SEM fila — SPEC-093-B BLOCO 0-bis ②.

O acionamento era o único lugar do produto que sabia gravar um `work_run` com
`conversation_id` e sem enfileirar no outbox. A sombra do sinistro precisa
exatamente do mesmo INSERT, e CLAUDE.md §5 proíbe a segunda cópia — então ele
foi extraído para `app.services.work.runs.criar_registro_sem_fila`.

O que este guarda prova é o que o banco cobra e o que o produto perderia:

  ① `conversation_id` sai gravado — sem ele não se reconstrói *"o cliente
     escreveu X, o robô abriu o chamado, travou na tela Y"*
  ② `thread_id` é DERIVADO — `ck_work_runs_thread_format` exige
     `'work:' || company_id || ':' || id`, e um chamador que o montasse à mão
     erraria mais cedo ou mais tarde
  ③ NADA vai para `work_queue_outbox` — é o motivo inteiro de o helper existir:
     o Smith Worker não tem handler para este trabalho e o marcaria `failed`
     enquanto ele está VIVO
  ④ dois pedidos com a mesma `idempotency_key` são UM run
  ⑤ e a idempotência é do PAR `(company_id, idempotency_key)` — a mesma chave
     em duas corretoras são dois trabalhos (CLAUDE.md §7)
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
RUNS_PY = RAIZ / "app" / "services" / "work" / "runs.py"
ROTEADOR_PY = RAIZ / "app" / "services" / "dispatch_router.py"

# ⚠️ Carregado pelo CAMINHO, não por `from app.services...`: importar o pacote
# `app` arrasta `app/core/config.py`, que exige SUPABASE_KEY, OPENAI_API_KEY e
# mais quatro segredos. Um guarda que só roda com o `.env` da máquina do lado
# não é guarda. `runs.py` só importa biblioteca padrão — cabe sozinho.
_spec = importlib.util.spec_from_file_location("runs_sem_fila_sob_teste", RUNS_PY)
_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runs)
criar_registro_sem_fila = _runs.criar_registro_sem_fila


# =============================================================================
# Um banco de mentira que ANOTA TUDO — inclusive o que não devia acontecer
# =============================================================================

class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self._filtros: dict = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, coluna, valor):
        self._filtros[coluna] = valor
        return self

    def limit(self, _n):
        return self

    def insert(self, linha):
        self.banco.escritas.append((self.tabela, dict(linha)))
        self.banco.linhas.setdefault(self.tabela, []).append(dict(linha))
        self._acao = "insert"
        return self

    async def execute(self):
        if getattr(self, "_acao", "") == "insert":
            return _Resposta([])
        self.banco.leituras.append((self.tabela, dict(self._filtros)))
        achados = [
            l for l in self.banco.linhas.get(self.tabela, [])
            if all(str(l.get(c)) == str(v) for c, v in self._filtros.items())
        ]
        return _Resposta(achados)


class BancoFalso:
    """`.client` devolve a si mesmo — é a forma que o dispatch_router usa."""

    def __init__(self):
        self.linhas: dict = {}
        self.escritas: list = []
        self.leituras: list = []

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self, nome)


PEDIDO = dict(
    company_id="11111111-1111-1111-1111-111111111111",
    workflow_key="claims.shadow",
    outcome_type="claims.shadow",
    outcome_title="Sombra de sinistro",
    source_type="chat",
    source_id="22222222-2222-2222-2222-222222222222",
    conversation_id="22222222-2222-2222-2222-222222222222",
    runtime_kind="sombra",
    status="running",
    risk_level="low",
    idempotency_key="claims.shadow:22222222-2222-2222-2222-222222222222",
    input_payload={"confianca": "media", "motivo": "regex_sinistro"},
)


def _criar(banco, **troca):
    return asyncio.run(criar_registro_sem_fila(banco, **{**PEDIDO, **troca}))


# =============================================================================
# ① a conversa fica gravada · ② o thread_id é derivado
# =============================================================================

def test_o_run_nasce_com_a_conversa_e_com_o_thread_derivado():
    banco = BancoFalso()
    linha = _criar(banco)

    assert linha["conversation_id"] == PEDIDO["conversation_id"], (
        "o run nasceu sem a conversa — é a coluna que a SPEC-090 abriu e a "
        "093-B usa para o digest")
    assert linha["thread_id"] == f"work:{PEDIDO['company_id']}:{linha['id']}", (
        "thread_id fora do formato do CHECK `ck_work_runs_thread_format` — o "
        "INSERT seria RECUSADO pelo Postgres")
    assert linha["reused"] is False


def test_CONTROLE_o_thread_id_NAO_e_uma_constante():
    """🔴 O guarda acima só vale se duas criações puderem diferir."""
    banco = BancoFalso()
    um = _criar(banco)
    dois = _criar(banco, idempotency_key="claims.shadow:outra-conversa")
    assert um["thread_id"] != dois["thread_id"], (
        "os dois runs saíram com o mesmo thread_id — o teste acima estaria "
        "comparando duas constantes iguais e não guardaria nada")
    assert um["id"] != dois["id"]


# =============================================================================
# ③ o que NÃO acontece: a fila
# =============================================================================

def test_nada_e_enfileirado_no_outbox():
    banco = BancoFalso()
    _criar(banco)

    tabelas = {t for t, _ in banco.escritas}
    assert tabelas == {"work_runs"}, (
        f"o helper escreveu em {sorted(tabelas)}. Uma linha em "
        "`work_queue_outbox` faria o Smith Worker pegar um run sem handler e "
        "marcá-lo `failed` — o espelho durável passaria a MENTIR")


def test_o_dispatch_router_NAO_tem_mais_o_INSERT_literal():
    """Gate ④ — consolidar, não duplicar (CLAUDE.md §5)."""
    fonte = ROTEADOR_PY.read_text(encoding="utf-8")
    assert '.table("work_runs").insert(' not in fonte, (
        "o INSERT voltou a morar no roteador — são duas cópias do mesmo "
        "caminho, e a segunda é a que envelhece sozinha")
    assert "criar_registro_sem_fila" in fonte, (
        "o roteador não chama o helper — a extração ficou pela metade")


# =============================================================================
# ④⑤ idempotência: uma sombra por conversa, uma por CORRETORA
# =============================================================================

def test_a_segunda_chamada_devolve_o_MESMO_run():
    banco = BancoFalso()
    primeiro = _criar(banco)
    segundo = _criar(banco)

    assert segundo["id"] == primeiro["id"]
    assert segundo["reused"] is True, (
        "o helper não avisou que reaproveitou — quem chama emitiria "
        "`run.created` de novo numa linha do tempo que já tinha um")
    assert len(banco.linhas["work_runs"]) == 1, (
        "duas linhas para a mesma chave — a sombra duplicaria a cada mensagem")


def test_a_mesma_chave_em_OUTRA_corretora_e_outro_run():
    """🔴 CLAUDE.md §7: o backend roda com service role. O filtro no código é a
    proteção real, e um SELECT só por `idempotency_key` devolveria o run da
    casa vizinha."""
    banco = BancoFalso()
    resulta = _criar(banco)
    autofleet = _criar(banco, company_id="33333333-3333-3333-3333-333333333333")

    assert autofleet["reused"] is False
    assert autofleet["id"] != resulta["id"]
    assert len(banco.linhas["work_runs"]) == 2
    for leitura in banco.leituras:
        assert "company_id" in leitura[1], (
            "houve um SELECT de idempotência SEM company_id — é assim que um "
            "run atravessa a fronteira do tenant")


# =============================================================================
# o que o banco cobra e um `None` estragaria
# =============================================================================

def test_correlation_id_e_progress_percent_nao_saem_como_NULO():
    """📊 Medido em 03/09/2026 no schema (`information_schema.columns`):
    `correlation_id` é NOT NULL com default `gen_random_uuid()` e
    `progress_percent` é NOT NULL com default `0`. Mandar `None` não é "deixar
    o default" — é um INSERT RECUSADO."""
    banco = BancoFalso()
    linha = _criar(banco)
    assert "correlation_id" not in linha
    assert "progress_percent" not in linha

    outra = _criar(banco, idempotency_key="k2", correlation_id="c-1",
                   progress_percent=15)
    assert outra["correlation_id"] == "c-1"
    assert outra["progress_percent"] == 15


def test_a_fase_e_o_progresso_do_acionamento_atravessam():
    banco = BancoFalso()
    linha = _criar(banco, current_step_key="ura", progress_percent=45,
                   runtime_kind="acionamento", risk_level="high")
    assert linha["current_step_key"] == "ura"
    assert linha["progress_percent"] == 45
    assert linha["runtime_kind"] == "acionamento"
    assert linha["input_fingerprint"], "o fingerprint da entrada é NOT NULL"


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
