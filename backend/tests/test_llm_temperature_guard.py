"""Regressao: quem RECUSA sampling (API 400 'temperature is deprecated for this
model') nunca recebe temperature/top_p/top_k.

SPEC-116 F2 (EVIDENCIAS/03 F5 + CLAUDE.md §9.3/§9.4): a versao anterior deste
guarda RECRIAVA a regra por prefixo de nome e AFIRMAVA "claude-opus-4-8 AINDA
recebe temperature" — verdade vencida (Opus 4.7/4.8 dao 400) guardada por um
teste que nao chamava o motor. Agora a regra mora no CATALOGO
(`capacidades.sampling_ok`) e o guarda chama a FABRICA real e le o PAYLOAD
que sairia ao provedor (nenhuma rede: chave falsa, so `_get_request_payload`).

LINHA DE CONTROLE: modelos com `sampling_ok=true` (Haiku 4.5, gpt-4o) TEM de
receber temperature — prova que o guarda consegue ver a diferenca.

Rodar de backend/: `python tests/test_llm_temperature_guard.py`."""
import copy
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
os.environ["SEM_REDE"] = "1"


class _BancoMudo:
    class _Consulta:
        data: list = []

        def __getattr__(self, _nome):
            return lambda *a, **k: self

        def execute(self):
            return self

    client = None

    def table(self, _nome):
        return self._Consulta()


import app.core.database as _db  # noqa: E402
import app.services.usage_service as _uso  # noqa: E402

# 🔴 (conserto único): este guarda roda no IMPORT (script). Ele troca dublês
# globais — e agora DEVOLVE os de antes no fim, para não vazar para o módulo
# seguinte da mesma sessão do pytest (📊 derrubava `test_o_modelo_tem_relogio`).
_ANTES_DB = (_db.get_supabase_client, _uso.get_supabase_client)
_db.get_supabase_client = lambda: _BancoMudo()
_uso.get_supabase_client = _db.get_supabase_client

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import LLMFactory  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))
_cat, _pap = copy.deepcopy(SNAP["catalogo"]), copy.deepcopy(SNAP["papeis"])
_ANTES_LEITOR = MP.leitor_do_banco
MP.leitor_do_banco = lambda: (_cat, _pap)
MP.limpar_cache()

CHAVE_FALSA = "sk-teste-chave-falsa-nao-existe"
_pass = 0
_fail = 0


def check(name, cond, detalhe=""):
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  ok  {name}")
    else:
        _fail += 1
        print(f"  XX  {name}  {detalhe}")


def _sampling_no_payload(provider: str, modelo: str) -> set:
    """Chaves de sampling no payload FINAL (inclusive dentro de extra_body)."""
    r = MP.resolver("brand_capture", override={"provider": provider, "model": modelo})
    try:
        llm = LLMFactory.create_llm({}, {"llm_temperature": 0.3}, api_key=CHAVE_FALSA,
                                    modelo_resolvido=r)
        p = llm._get_request_payload([("human", "oi")])
    except Exception as exc:  # noqa: BLE001 — a lib recusou localmente: também é "recebeu"
        return {f"ERRO:{type(exc).__name__}"}
    achadas = {k for k in ("temperature", "top_p", "top_k") if k in p}
    achadas |= {f"extra_body.{k}" for k in ("temperature", "top_p", "top_k")
                if k in (p.get("extra_body") or {})}
    return achadas


RECUSAM = [("anthropic", "claude-sonnet-5"), ("anthropic", "claude-opus-5"),
           ("anthropic", "claude-opus-5-5"), ("anthropic", "claude-fable-5-1"),
           ("anthropic", "claude-opus-4-7"), ("anthropic", "claude-opus-4-8"),
           ("openai", "gpt-6-sol"), ("openai", "gpt-5.6-terra")]
ACEITAM = [("anthropic", "claude-haiku-4-5-20251001"), ("openai", "gpt-4o")]

for prov, modelo in RECUSAM:
    assert _cat[modelo]["capacidades"].get("sampling_ok") is False, modelo
    achadas = _sampling_no_payload(prov, modelo)
    check(f"{modelo} (sampling_ok=false no catalogo) NAO recebe sampling", not achadas, achadas)

for prov, modelo in ACEITAM:
    achadas = _sampling_no_payload(prov, modelo)
    check(f"CONTROLE: {modelo} (sampling_ok=true) RECEBE temperature", "temperature" in achadas,
          achadas)

MP.leitor_do_banco = _ANTES_LEITOR
_db.get_supabase_client, _uso.get_supabase_client = _ANTES_DB
MP.limpar_cache()

print(f"\n== Resumo: {_pass} passaram, {_fail} falharam ==")
if _fail:
    raise SystemExit(1)
