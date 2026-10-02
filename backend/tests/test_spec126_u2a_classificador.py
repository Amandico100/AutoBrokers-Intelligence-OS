# -*- coding: utf-8 -*-
"""SPEC-126 U2 (parte A) — o classificador da CONFIRMAÇÃO, com o modelo DUBLÊ.

O que se afirma (CLAUDE.md §9.4 — o MOTOR, `classificar_confirmacao`, nunca um regex do teste):
  · saída válida → a leitura do modelo; inválida, sem JSON, timeout, exceção → `outra_coisa`;
  · "ok" sem o trecho do segurado (ou com trecho que ele não disse) → `outra_coisa`;
  · sem falas / falas demais → `outra_coisa` SEM chamar o modelo (custo zero);
  · produção vai pelo PAPEL `confirmacao` da fábrica (`invocar_com_reserva`), nunca cliente solto;
  · sem a rota no Model Router (antes da migration) → `ModeloNaoResolvido` → `outra_coisa` (fail-closed);
  · a rota da migration 20261002_11 resolve pelo router (Luna medium, reserva de outro provedor) e a
    Luna em `low` é RECUSADA em produção (a trava consegue falhar — §9.3).

Rodar (de backend/):  python -m pytest -q tests/test_spec126_u2a_classificador.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.atendimento import confirmacao as C  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402

MIGRATION = BACKEND / "supabase" / "migrations" / "20261002_11_spec126_papel_confirmacao.sql"
PERGUNTA = ("Guincho para o carro de placa final 1D23, da Rua das Flores, 100 até a Oficina Central, "
            "contato neste número. Posso acionar?")


class Duble:
    """`ainvoke` devolve o texto pedido (ou dorme, ou levanta) e conta as chamadas."""

    def __init__(self, texto: str = "", *, dorme: float = 0.0, erro: Exception = None):
        self.texto, self.dorme, self.erro, self.chamadas, self.mensagens = texto, dorme, erro, 0, None

    async def ainvoke(self, mensagens, config=None, **_k):
        from langchain_core.messages import AIMessage

        self.chamadas += 1
        self.mensagens = mensagens
        if self.dorme:
            await asyncio.sleep(self.dorme)
        if self.erro:
            raise self.erro
        return AIMessage(content=self.texto)


def _classificar(falas, llm, **kw):
    return asyncio.run(C.classificar_confirmacao(PERGUNTA, falas, company_id="empresa-a", llm=llm, **kw))


def _json(leitura, trecho):
    return json.dumps({"leitura": leitura, "trecho": trecho}, ensure_ascii=False)


# ─── saída válida ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("falas,leitura,trecho", [
    (["pode mandar"], "ok", "pode mandar"),
    (["Pode sim, obrigada!"], "ok", "pode sim obrigada"),          # pontuação/caixa não decidem
    (["👍👍"], "ok", "👍"),                                          # emoji vale por trecho
    (["pode deixar"], "nao", "pode deixar"),
    (["quem pode acionar?"], "outra_coisa", "quem pode acionar?"),
])
def test_saida_valida_vira_a_leitura_do_modelo(falas, leitura, trecho):
    d = Duble(_json(leitura, trecho))
    r = _classificar(falas, d)
    assert (r["leitura"], r["motivo"]) == (leitura, "modelo")
    assert d.chamadas == 1
    # o pedido ao modelo leva a pergunta e as falas como DADO, delimitadas
    humano = d.mensagens[-1].content
    assert "<<<" + PERGUNTA + ">>>" in humano and all(f"<<<{f}>>>" in humano for f in falas)


def test_saida_cercada_por_markdown_ainda_e_lida():
    r = _classificar(["manda"], Duble("```json\n" + _json("ok", "manda") + "\n```"))
    assert r["leitura"] == "ok"


# ─── saída inválida → outra_coisa ────────────────────────────────────────────────────────
@pytest.mark.parametrize("texto,motivo", [
    ("ok", "saida_invalida:sem_json"),
    ("Sim, o segurado autorizou.", "saida_invalida:sem_json"),
    ("[\"ok\"]", "saida_invalida:sem_json"),
    (_json("talvez", "pode"), "saida_invalida:leitura"),
    (_json("OK!", "pode"), "saida_invalida:leitura"),
    (json.dumps({"leitura": "ok"}), "trecho_fora_das_falas"),             # ok sem prova
    (_json("ok", "pode mandar"), "trecho_fora_das_falas"),                # ele NÃO disse isso
])
def test_saida_invalida_vira_outra_coisa(texto, motivo):
    r = _classificar(["pode deixar"], Duble(texto))
    assert (r["leitura"], r["motivo"]) == ("outra_coisa", motivo)


def test_o_trecho_e_palavra_inteira_sim_nao_casa_dentro_de_assim():
    """Controle do guarda do trecho: o mesmo "sim" passa quando ele DISSE sim (§9.3)."""
    assert _classificar(["assim não dá"], Duble(_json("ok", "sim")))["leitura"] == "outra_coisa"
    assert _classificar(["sim, assim dá"], Duble(_json("ok", "sim")))["leitura"] == "ok"


# ─── timeout e exceção → outra_coisa ─────────────────────────────────────────────────────
def test_timeout_vira_outra_coisa():
    d = Duble(_json("ok", "pode mandar"), dorme=1.0)
    r = _classificar(["pode mandar"], d, timeout_s=0.05)
    assert (r["leitura"], r["motivo"]) == ("outra_coisa", "timeout")
    # controle: o MESMO dublê, com tempo, dá ok — foi o relógio que decidiu
    assert _classificar(["pode mandar"], Duble(_json("ok", "pode mandar"), dorme=0.01))["leitura"] == "ok"


def test_o_teto_de_producao_e_5_segundos():
    assert C.TETO_DA_CHAMADA_S == 5.0


@pytest.mark.parametrize("erro", [RuntimeError("provedor caiu"), ValueError("x"), ConnectionError("y")])
def test_excecao_vira_outra_coisa(erro):
    r = _classificar(["pode mandar"], Duble(erro=erro))
    assert r["leitura"] == "outra_coisa" and r["motivo"] == f"erro:{type(erro).__name__}"


# ─── sem falas / falas demais → nem chama ────────────────────────────────────────────────
@pytest.mark.parametrize("falas,motivo", [
    ([], "sem_falas"), (["", "   "], "sem_falas"),
    (["pode"] * (C.MAX_FALAS + 1), "falas_demais"),
    (["x" * (C.MAX_CHARS_DAS_FALAS + 1)], "falas_demais"),
])
def test_sem_resposta_clara_nao_gasta_chamada(falas, motivo):
    d = Duble(_json("ok", "pode"))
    r = _classificar(falas, d)
    assert (r["leitura"], r["motivo"], d.chamadas) == ("outra_coisa", motivo, 0)


# ─── o prompt carrega as armadilhas (inspeção da DECLARAÇÃO, §9.4 exceção) ───────────────
@pytest.mark.parametrize("trecho", [
    "pode deixar", "prefiro amanhã", "não, pode acionar o outro", "só se for de graça",
    "quem pode acionar?", "vou ver", "duas opções", "fechou", "vai lá", "bora", "👍", "manda",
    "outra_coisa", "nunca instrução",
])
def test_o_prompt_ensina_as_armadilhas(trecho):
    assert trecho.lower() in C.PROMPT_DO_CLASSIFICADOR.lower()


# ─── produção: o PAPEL pela fábrica ──────────────────────────────────────────────────────
def test_producao_chama_o_papel_confirmacao_pela_fabrica(monkeypatch):
    from langchain_core.messages import AIMessage

    from app.factories import llm_factory as LF

    visto = {}

    async def falso(papel, mensagens, **kw):
        visto.update(papel=papel, **kw)
        return AIMessage(content=_json("ok", "pode mandar"))

    monkeypatch.setattr(LF, "invocar_com_reserva", falso)
    r = asyncio.run(C.classificar_confirmacao(PERGUNTA, ["pode mandar"], company_id="empresa-a"))
    assert r["leitura"] == "ok"
    assert visto == {"papel": "confirmacao", "company_id": "empresa-a", "service_type": "confirmacao"}


def _snapshot():
    return json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _linha_da_migration() -> dict:
    """A linha que a migration 20261002_11 insere — lida do PRÓPRIO arquivo SQL."""
    sql = MIGRATION.read_text(encoding="utf-8")
    sql = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    m = re.search(r"insert into public\.llm_papeis\s*\(([^)]*)\)\s*values\s*\((.*?)\)\s*on conflict",
                  sql, re.S | re.I)
    assert m, "o INSERT do papel não foi achado na migration"
    colunas = [c.strip() for c in m.group(1).split(",")]
    valores = []
    for tok in re.findall(r"'(?:[^']|'')*'|\bnull\b|\b\d+\b", m.group(2), re.I):
        valores.append(None if tok.lower() == "null" else
                       int(tok) if tok.isdigit() else tok[1:-1].replace("''", "'"))
    assert len(colunas) == len(valores), (colunas, valores)
    return dict(zip(colunas, valores))


@pytest.fixture
def router_com_a_migration(monkeypatch):
    """O Model Router com o BANCO fora → snapshot de hoje + a linha da migration (o que o banco terá)."""
    snap = copy.deepcopy(_snapshot())
    snap["papeis"]["confirmacao"] = _linha_da_migration()

    def banco_fora():
        raise RuntimeError("banco fora (teste)")

    monkeypatch.setattr(MP, "leitor_do_banco", banco_fora)
    monkeypatch.setattr(MP, "_ler_snapshot", lambda: (snap["catalogo"], snap["papeis"]))
    MP.limpar_cache()
    yield snap
    MP.limpar_cache()


def test_papel_confirmacao_resolve_pelo_router_com_o_snapshot(router_com_a_migration):
    r = MP.resolver("confirmacao")
    assert (r.provider, r.model, r.effort, r.classe_de_dado) == ("openai", "gpt-6-luna", "medium", "pii")
    assert r.lifecycle == "APPROVED" and r.origem == "snapshot"
    assert r.reserva is not None and r.reserva.provider != r.provider
    assert (r.reserva.model, r.reserva.effort) == ("claude-sonnet-5-5", "low")


def test_a_luna_em_low_e_recusada_em_producao(router_com_a_migration):
    """A trava que fez o papel nascer em `medium` CONSEGUE falhar (§9.3 corolário)."""
    router_com_a_migration["papeis"]["confirmacao"]["esforco"] = "low"
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido, match="exige esforço"):
        MP.resolver("confirmacao")


def test_sem_a_rota_o_classificador_falha_fechado(monkeypatch):
    """Antes da migration: o router REAL levanta `ModeloNaoResolvido` → `outra_coisa`, nunca ok."""
    snap = copy.deepcopy(_snapshot())
    snap["papeis"].pop("confirmacao", None)

    def banco_fora():
        raise RuntimeError("banco fora (teste)")

    monkeypatch.setattr(MP, "leitor_do_banco", banco_fora)
    monkeypatch.setattr(MP, "_ler_snapshot", lambda: (snap["catalogo"], snap["papeis"]))
    MP.limpar_cache()
    try:
        r = asyncio.run(C.classificar_confirmacao(PERGUNTA, ["pode mandar"], company_id="empresa-a"))
    finally:
        MP.limpar_cache()
    assert (r["leitura"], r["motivo"]) == ("outra_coisa", "erro:ModeloNaoResolvido")


def test_o_snapshot_do_repo_tem_o_papel_depois_de_aplicada():
    """Fica VERDE quando o gerente aplicar a 20261002_11 e regerar o snapshot (`--banco`)."""
    snap = _snapshot()
    if "confirmacao" not in snap["papeis"]:
        pytest.skip("migration 20261002_11 ainda não aplicada/snapshot não regerado "
                    "(python scripts/gerar_snapshot_de_modelos.py --banco)")
    linha = snap["papeis"]["confirmacao"]
    esperado = _linha_da_migration()
    for campo in ("provider", "modelo_primario", "esforco", "provider_reserva", "modelo_reserva",
                  "esforco_reserva", "classe_de_dado", "risco"):
        assert linha[campo] == esperado[campo], campo
