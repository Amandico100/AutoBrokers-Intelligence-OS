# -*- coding: utf-8 -*-
"""SPEC-123 F1b — os guardas de FORMA da ligação do destravador (só leem o fonte; nada importa o `app`).

① O papel `destravador`/`destravador_segunda` é chamado SÓ de `destravador.py` (F1a), pelo helper da
  reserva — o análogo do guarda da SPEC-116 para a rota `dispatch` (`test_spec116_reserva_p0.py`, que
  continua intacto). O roteador e o Sentinela chamam `destravar(...)`, nunca o modelo.
② Os dois pontos de trava passam pelo destravador (a ligação existe no fonte, não só no teste).
③ CONTROLE (§9.3): um chamador plantado deixa o guarda VERMELHO.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROUTER_PY = BACKEND / "app" / "services" / "dispatch_router.py"
VIGIA_PY = BACKEND / "app" / "tasks" / "dispatch_watchdog.py"

#: Quem chama o MODELO do destravador: pelo helper, direto (`create_llm`/`papel=`) ou por apelido.
_PAPEL_DO_DESTRAVADOR = re.compile(
    r"""invocar_com_reserva\(\s*(?:papel\s*=\s*)?["']destravador(?:_segunda)?["']"""
    r"""|create_llm\([^)]*["']destravador(?:_segunda)?["']"""
    r"""|papel\s*=\s*["']destravador(?:_segunda)?["']"""
    r"""|^\s*PAPEL\w*\s*(?::\s*\w+\s*)?=\s*["']destravador(?:_segunda)?["']""", re.S | re.M)
#: Quem pode chamar o modelo do destravador, com o porquê: `destravador.py` decide (F1a, o
#: contrato da SPEC-123) · `bancada.py` MEDE o mesmo papel no corpus (F2, D4: a bancada escolhe o
#: modelo pelo número) — mede e não envia nada. Fora daqui, ninguém.
# 🔴 SPEC-127 P5 (§9.3 — a lição MIGRA): `bancada_portal.py` mede o papel no gabarito do portal com o modelo INJETADO,
#    o diário vira dublê e nada é enviado — a mesma razão de `bancada.py`. O CONTROLE abaixo continua vermelho para um
#    chamador plantado fora destes três.
DONOS_DO_PAPEL = {"destravador.py", "bancada.py", "bancada_portal.py"}


def _fontes_do_app() -> dict:
    return {p.name: p.read_text(encoding="utf-8") for p in (BACKEND / "app").rglob("*.py")}


def _quem_chama_o_papel(fontes: dict) -> list:
    return sorted(n for n, src in fontes.items() if _PAPEL_DO_DESTRAVADOR.search(src))


def test_so_o_destravador_chama_o_modelo_do_destravador():
    quem = _quem_chama_o_papel(_fontes_do_app())
    assert set(quem) <= DONOS_DO_PAPEL, quem
    for pontos in ("dispatch_router.py", "dispatch_watchdog.py", "webhook.py"):
        assert pontos not in quem, f"{pontos} chama o MODELO do destravador em vez de `destravar`"


@pytest.mark.parametrize("novo", [
    'r = await invocar_com_reserva(\n    "destravador", msgs, company_id=cid)\n',
    'llm = create_llm(papel="destravador_segunda", company_id=cid)\n',
    'PAPEL_X = "destravador"\n',
])
def test_CONTROLE_um_chamador_plantado_no_roteador_deixa_o_guarda_vermelho(novo):
    fontes = _fontes_do_app()
    fontes["dispatch_router.py"] = fontes["dispatch_router.py"] + "\n" + novo
    quem = _quem_chama_o_papel(fontes)
    assert "dispatch_router.py" in quem and not set(quem) <= DONOS_DO_PAPEL


def test_os_pontos_de_trava_passam_pelo_destravador():
    roteador = ROUTER_PY.read_text(encoding="utf-8")
    vigia = VIGIA_PY.read_text(encoding="utf-8")
    # a ligação é pela interface do contrato, com import TARDIO (o módulo é da F1a)
    assert "from app.services.destravador import destravar" in roteador
    assert "from app.services.destravador import modo_do_destravador" in roteador
    assert "from app.services.destravador import agendar_em_sombra" in roteador
    corpo = roteador.split("async def try_route_insurer_inbound", 1)[1]
    assert corpo.count("pedir_ao_destravador(") >= 1, "o PONTO B sumiu do roteador"
    assert "_turno_do_destravador(" in corpo, "o PONTO A sumiu do roteador"
    assert vigia.count("_destravar_no_sentinela(") >= 3, "um dos pontos do Sentinela sumiu"
    assert "_tentativa_do_destravador(" in vigia
    # ⛔ os dois arquivos NUNCA enviam o que o destravador decidiu por fora dos efetores de hoje
    miolo = roteador.split("# 🔴 SPEC-123 F1b — O DESTRAVADOR NOS PONTOS DE TRAVA", 1)[1].split(
        "async def try_route_insurer_inbound", 1)[0]
    assert "send_message" not in miolo and "enviar_ao_grupo" not in miolo
