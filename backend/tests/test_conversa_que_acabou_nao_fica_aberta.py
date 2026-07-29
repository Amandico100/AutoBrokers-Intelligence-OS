"""A conversa que acabou tem de ser marcada como acabada. SPEC-040.

O defeito
---------
A sessão só fechava quando chegava mensagem NOVA da mesma pessoa depois do
intervalo de duas horas — a lógica vive em `observer_intake`, no caminho de
entrada de mensagem. Se o segurado nunca escreve de novo, e é o que acontece
quando o atendimento resolveu, ninguém fecha nada.

`_load_undistilled_sync` só olha `status='closed'`. Então a conversa completa,
com o conhecimento dentro, fica invisível para o Destilador **para sempre**.

Medido em 29/07/2026 com dado real: 43 sessões da Resulta abertas, uma desde
**21/07** — oito dias — somando 423 mensagens paradas. Nenhuma era conversa com
seguradora, o que salvou o material que o Founder considera insubstituível. Mas
nada no sistema garantia isso: foi sorte.

Por que a varredura mora no Destilador
--------------------------------------
Ela poderia ser um serviço novo com agendamento próprio. Seria um motor paralelo
para uma consulta de duas linhas — CLAUDE.md §5. O Destilador já roda
periodicamente, já é quem precisa da sessão fechada, e já tem a trava de rodada
única. Fechar sessão vencida é pré-requisito do trabalho dele, não outro
trabalho.

E roda **mesmo com o teto de gasto em zero**: não chama modelo, e é exatamente o
que destrava material para quando houver crédito.

A margem
--------
Seis horas sem nenhuma mensagem — três vezes o intervalo de sessão. Fechar cedo
partiria uma conversa em duas e ensinaria conduta pela metade, que é pior que
esperar. Fechar tarde só atrasa.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.core", ("app", "core"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m
_banco = types.ModuleType("app.core.database")
_banco.get_supabase_client = lambda: None
sys.modules["app.core.database"] = _banco

_spec = importlib.util.spec_from_file_location(
    "app.services.attendance_distiller",
    os.path.join(RAIZ, "app", "services", "attendance_distiller.py"))
DIST = importlib.util.module_from_spec(_spec)
sys.modules["app.services.attendance_distiller"] = DIST
_spec.loader.exec_module(DIST)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ----------------------------------------------------- fake mínimo do Supabase
class _Consulta:
    def __init__(self, linhas, registro):
        self._linhas, self._reg = linhas, registro
        self._filtros = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filtros[("eq", col)] = val
        return self

    def lt(self, col, val):
        self._filtros[("lt", col)] = val
        return self

    def limit(self, *_a, **_k):
        return self

    def in_(self, col, vals):
        self._filtros[("in", col)] = list(vals)
        return self

    def update(self, patch):
        self._reg.setdefault("updates", []).append((patch, self._filtros))
        return self

    def execute(self):
        self._reg.setdefault("consultas", []).append(dict(self._filtros))
        linhas = [
            r for r in self._linhas
            if all((r.get(c) == v if k == "eq" else
                    str(r.get(c) or "") < str(v) if k == "lt" else True)
                   for (k, c), v in self._filtros.items())
        ]
        return type("R", (), {"data": linhas})()


class _Db:
    def __init__(self, linhas, registro):
        self._l, self._r = linhas, registro
        self.client = self

    def table(self, _nome):
        return _Consulta(self._l, self._r)


def teste_a_sessao_parada_e_fechada():
    print("\n[1] Seis horas sem mensagem: a conversa acabou")
    from datetime import datetime, timedelta, timezone

    agora = datetime.now(timezone.utc)
    linhas = [
        {"id": "oito-dias", "status": "open",
         "last_event_at": (agora - timedelta(days=8)).isoformat()},
        {"id": "ontem", "status": "open",
         "last_event_at": (agora - timedelta(hours=20)).isoformat()},
        {"id": "viva-agora", "status": "open",
         "last_event_at": (agora - timedelta(minutes=30)).isoformat()},
        {"id": "viva-3h", "status": "open",
         "last_event_at": (agora - timedelta(hours=3)).isoformat()},
        {"id": "ja-fechada", "status": "closed",
         "last_event_at": (agora - timedelta(days=2)).isoformat()},
    ]
    reg: dict = {}
    banco = sys.modules["app.core.database"]
    original = banco.get_supabase_client
    banco.get_supabase_client = lambda: _Db(linhas, reg)
    try:
        n = DIST._fechar_sessoes_vencidas_sync()
    finally:
        banco.get_supabase_client = original

    fechados = [i for patch, f in reg.get("updates", [])
                if patch.get("status") == "closed"
                for i in f.get(("in", "id"), [])]
    checar("oito-dias" in fechados, "a de oito dias fecha")
    checar("ontem" in fechados, "a de vinte horas também")
    checar("viva-agora" not in fechados,
           "a de meia hora NÃO fecha", "partiria a conversa em duas")
    checar("viva-3h" not in fechados,
           "a de três horas também não",
           "a margem é 6h, o triplo do intervalo de sessão")
    checar("ja-fechada" not in fechados, "e a já fechada não é tocada de novo")
    checar(n == 2, "devolve quantas fechou", f"devolveu {n}")


def teste_so_mexe_em_sessao_aberta():
    print("\n[2] A varredura filtra no banco, não na memória")
    from datetime import datetime, timedelta, timezone

    agora = datetime.now(timezone.utc)
    linhas = [{"id": "x", "status": "open",
               "last_event_at": (agora - timedelta(days=3)).isoformat()}]
    reg: dict = {}
    banco = sys.modules["app.core.database"]
    original = banco.get_supabase_client
    banco.get_supabase_client = lambda: _Db(linhas, reg)
    try:
        DIST._fechar_sessoes_vencidas_sync()
    finally:
        banco.get_supabase_client = original

    primeira = (reg.get("consultas") or [{}])[0]
    checar(primeira.get(("eq", "status")) == "open",
           "pede ao banco só as abertas",
           "trazer todas e filtrar aqui bateria no teto de 1.000 do PostgREST")
    checar ("last_event_at" in str(primeira),
            "e usa `last_event_at` como corte, no próprio banco")


def teste_roda_mesmo_com_o_teto_em_zero():
    print("\n[3] Travar o gasto não pode travar o fechamento")
    fonte = inspect.getsource(DIST.distill_once)
    i_fecha = fonte.find("_fechar_sessoes_vencidas_sync")
    i_teto = fonte.find("teto = _teto_de_gasto()")
    checar(i_fecha >= 0, "a rodada chama a varredura")
    checar(i_fecha < i_teto,
           "e chama ANTES de ler o teto",
           "depois de um `if teto <= 0: return` a varredura nunca rodaria, e o "
           "material ficaria invisível justamente enquanto se economiza")


def teste_nao_existe_motor_paralelo():
    print("\n[4] Sem serviço novo para uma consulta de duas linhas")
    # CLAUDE.md §5: consolidar antes de duplicar. A varredura é pré-requisito do
    # Destilador, então mora nele.
    import glob
    suspeitos = [os.path.basename(p) for p in
                 glob.glob(os.path.join(RAIZ, "app", "services", "*session*close*.py"))
                 + glob.glob(os.path.join(RAIZ, "app", "services", "*fecha*.py"))]
    checar(not suspeitos, "nenhum serviço novo foi criado", str(suspeitos))
    checar(hasattr(DIST, "_fechar_sessoes_vencidas_sync"),
           "a varredura vive no Destilador, que é quem precisa dela")


def main() -> int:
    print("=" * 70)
    print("A CONVERSA QUE ACABOU NÃO FICA ABERTA PARA SEMPRE")
    print("=" * 70)
    for teste in (teste_a_sessao_parada_e_fechada,
                  teste_so_mexe_em_sessao_aberta,
                  teste_roda_mesmo_com_o_teto_em_zero,
                  teste_nao_existe_motor_paralelo):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("CONVERSA ENCERRADA ENTRA NA FILA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
