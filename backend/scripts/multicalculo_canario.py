# -*- coding: utf-8 -*-
"""O CANÁRIO do multicálculo — SPEC-129-B U6 (o gerente roda AO VIVO, fora do horário da pessoa dona do login).

    cd backend
    AUTOBROKERS_CANARIO=1 MULTICALCULO_HMAC_KEY=… SUPABASE_URL=… SUPABASE_SERVICE_ROLE_KEY=… PORTAL_VAULT_KEY=… \
      .venv/Scripts/python.exe scripts/multicalculo_canario.py \
        --canal <uuid> --corretora <uuid> --corretora <uuid> --perfil <arquivo.json FORA do git> \
        [--ajuste franquia=normal] [--matar-depois-do-checkpoint] [--teto 8]

O que faz, no PROCESSO (navegador local; o motor do serviço não é tocado):
  ① porta.calcular pelo CANAL, origem `teste`, 2 corretoras × padrão+econômica  ② o motor real (Chromium local)
  ③ [--matar-depois-do-checkpoint] espera o checkpoint (4 × `calculando`) e o 1º evento, DERRUBA o motor (o desligar
     do serviço: grupos cancelados, logout) e religa outro depois da lease vencer; imprime os calcularV2 antes/depois
  ④ recalcula a PADRÃO da 1ª corretora com o ajuste  ⑤ imprime os eventos SEM dado pessoal (seguradora, família,
     prêmio) e os tempos  ⑥ isolamento por SELECT  ⑦ varre TODAS as colunas de texto das 5 tabelas procurando
     senha|loginws|senhaws|token|authorization|https?://  ⑧ SEMPRE (finally): logout, contas `teste` -> `pausado` e
     senha apagada.
⛔ O perfil (o pedido com os dados da apólice autorizada) NUNCA é impresso. Renovação ao vivo: não roda aqui (declarado).
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

TABELAS = ("multicalculo_pedidos", "multicalculo_calculos", "multicalculo_ofertas", "multicalculo_eventos",
           "multicalculo_adesoes")
PROIBIDO = re.compile(r"senha|loginws|senhaws|token|authorization|https?://", re.I)
TERMINAIS = ("fechado", "falhou", "incerto", "cancelado", "expirado")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="multicalculo_canario", description="O canário do multicálculo (SPEC-129-B U6).")
    p.add_argument("--canal", required=True)
    p.add_argument("--corretora", required=True, action="append", help="2 vezes: as duas corretoras")
    p.add_argument("--perfil", required=True, help="JSON local FORA do git com o pedido ({grupo: {campo: valor}})")
    p.add_argument("--ajuste", default="franquia=normal", help="tipo=valor (ex.: franquia=normal)")
    p.add_argument("--matar-depois-do-checkpoint", action="store_true")
    p.add_argument("--teto", type=int, default=8, help="teto de cálculos desta execução")
    p.add_argument("--quadro-s", type=int, default=60)
    p.add_argument("--url-base", default=None, help=argparse.SUPPRESS)   # só o teste (o Agger dublê)
    return p


def _ajuste(texto: str) -> Dict[str, Any]:
    tipo, _, valor = str(texto).partition("=")
    if not tipo or not valor:
        raise SystemExit("--ajuste no formato tipo=valor (ex.: franquia=normal)")
    return {"tipo": tipo.strip(), "valor": valor.strip()}


def _fora_do_git(caminho: Path) -> bool:
    raiz = BACKEND.parent.resolve()
    try:
        caminho.resolve().relative_to(raiz)
        return False
    except ValueError:
        return True


class _Contador:
    """O robô REAL com um contador de POSTs (`disparar`/`recalcular` = 1 `calcularV2` cada, no máximo)."""

    def __init__(self, intervalo_s: Optional[float] = None):
        from portal_worker.multicalculo import agger_robo as R

        self.n = 0
        self.mod = SimpleNamespace(**{k: getattr(R, k) for k in dir(R) if not k.startswith("__")})
        for nome in ("disparar", "recalcular"):
            setattr(self.mod, nome, self._contando(getattr(R, nome)))
        if intervalo_s is not None:
            self.mod.acompanhar = functools.partial(R.acompanhar, intervalo_s=intervalo_s)

    def _contando(self, fn):
        async def f(*a, **k):
            self.n += 1
            return await fn(*a, **k)
        return f


async def executar(args, *, supa, escrever: Callable[[str], Any] = print, abrir_navegador=None,
                   agora_do_religado: Optional[Callable[[], datetime]] = None, esperar_lease_s: Optional[float] = None,
                   upload=None, intervalo_s: Optional[float] = None) -> int:
    """O canário inteiro. As bordas são injetáveis só para o teste do script (banco e Agger dublês)."""
    from app.services.multicalculo import MulticalculoProvider, NaoEncontrado, PedidoDeCalculo
    from app.services.multicalculo.repositorio import RepositorioMulticalculo
    from portal_worker.multicalculo import motor as MOT
    from portal_worker.multicalculo import robos as ROB
    from portal_worker.multicalculo.agger_sessao import URL_BASE_AGGER, Sessoes

    if os.environ.get("AUTOBROKERS_CANARIO") != "1":
        escrever("RECUSADO: o canário exige AUTOBROKERS_CANARIO=1 no processo")
        return 2
    corretoras = [str(c).strip().lower() for c in args.corretora]
    if len(corretoras) != 2 or len(set(corretoras)) != 2:
        escrever("RECUSADO: passe --corretora DUAS vezes, com corretoras diferentes")
        return 2
    perfil_path = Path(args.perfil)
    if not perfil_path.is_file() or not _fora_do_git(perfil_path):
        escrever("RECUSADO: --perfil precisa ser um arquivo local FORA do repositório (tem dado pessoal)")
        return 2
    planejados = 2 * 2 + 1
    if planejados > int(args.teto):
        escrever(f"RECUSADO: o canário faz {planejados} cálculos e o --teto é {args.teto}")
        return 2
    os.environ["MULTICALCULO_MOTOR_LIGADO"] = "true"     # SÓ neste processo (o serviço não é tocado)
    ajuste = _ajuste(args.ajuste)
    perfil = json.loads(perfil_path.read_text(encoding="utf-8"))
    pedido = PedidoDeCalculo.de_dict(perfil.get("pedido", perfil))
    perfil = None  # noqa: F841 — o dado do perfil só vive dentro do pedido (repr sem valores)
    escrever(f"pedido: {pedido!r}")

    url_base = args.url_base or URL_BASE_AGGER
    def _letra(company_id: Any) -> str:
        """A corretora como A/B (a ordem do --corretora): o nome nunca sai na tela."""
        cid = str(company_id).strip().lower()
        return "AB"[corretoras.index(cid)] if cid in corretoras else "?"

    def _dt(c: Dict[str, Any], a: str, b: str) -> str:
        ta, tb = MOT._ts(c.get(a)), MOT._ts(c.get(b))
        return f"{(tb - ta).total_seconds():.0f}s" if ta and tb else "-"

    contas = []
    for c in corretoras:
        contas += [x for x in ROB.candidatos(supa, c)]
    escrever("robôs: " + " · ".join(f"{x['id']} ({x['robo_estado']})" for x in contas))
    porta = MulticalculoProvider(RepositorioMulticalculo(supa))
    contador = _Contador(intervalo_s)
    navegadores: List[Any] = []
    motores: List[Any] = []
    # conserto 129-B (juiz P10): os motores do canário servem SÓ o pedido que ELE criou — nunca a fila inteira
    meus_pedidos: set = set()
    pw = None
    rc = 1

    async def novo_motor(nome: str, agora=None):
        nonlocal pw
        if abrir_navegador is not None:
            nav = await abrir_navegador()
        else:
            from playwright.async_api import async_playwright

            from portal_worker.worker import _launch_kwargs

            if pw is None:
                pw = await async_playwright().start()
            nav = await pw.chromium.launch(**_launch_kwargs())
        navegadores.append(nav)
        kw = {"upload": upload} if upload is not None else {}
        m = MOT.Motor(supa, sessoes=Sessoes(nav, url_base=url_base), robo=contador.mod, canario=True,
                      dono=f"canario:{socket.gethostname()}:{os.getpid()}:{nome}", agora=agora,
                      somente_pedidos=meus_pedidos, **kw)
        motores.append(m)
        return m

    def linhas(tabela: str, **filtro) -> List[Dict[str, Any]]:
        q = supa.table(tabela).select("*")
        for k, v in filtro.items():
            q = q.eq(k, v)
        return list(q.execute().data or [])

    async def ate_terminar(m, pedido_id: str, limite_s: float = 600) -> None:
        t0 = time.time()
        while time.time() - t0 < limite_s:
            await m.uma_volta()
            if all(c["status"] in TERMINAIS for c in linhas("multicalculo_calculos", pedido_id=pedido_id)):
                return
            await asyncio.sleep(2)
        escrever("⚠️ o pedido não terminou no limite")

    try:
        aberto = await porta.calcular(company_id=args.canal, pedido=pedido, corretoras=corretoras,
                                      origem="teste", quadro_s=int(args.quadro_s))
        pedido = None   # noqa: F841
        meus_pedidos.add(aberto.pedido_id)
        escrever(f"pedido {aberto.pedido_id}: {len(aberto.calculos)} cálculos na fila")
        m1 = await novo_motor("m1")
        if args.matar_depois_do_checkpoint:
            await m1.uma_volta(esperar=False)
            t0 = time.time()
            while time.time() - t0 < 300:
                cs = linhas("multicalculo_calculos", pedido_id=aberto.pedido_id)
                evs = linhas("multicalculo_eventos", pedido_id=aberto.pedido_id)
                if cs and all(c["status"] == "calculando" for c in cs) and evs:
                    break
                if cs and all(c["status"] in TERMINAIS for c in cs):
                    break
                await asyncio.sleep(0.2)
            antes = contador.n
            n_ev = len(linhas("multicalculo_eventos", pedido_id=aberto.pedido_id))
            escrever(f"MORTE depois do checkpoint: calcularV2 = {antes} · eventos gravados = {n_ev}")
            await m1.encerrar()                          # o desligar do serviço (junta 8): grupos parados + logout
            espera = (MOT.LEASE_VENCE_S + 2) if esperar_lease_s is None else esperar_lease_s
            escrever(f"esperando a lease vencer ({espera:.0f} s) para religar")
            await asyncio.sleep(espera)
            m2 = await novo_motor("m2", agora=agora_do_religado)
            await ate_terminar(m2, aberto.pedido_id)
            escrever(f"RETOMADA: calcularV2 antes = {antes} · depois = {contador.n} (+{contador.n - antes})")
            ativo = m2
        else:
            await ate_terminar(m1, aberto.pedido_id)
            ativo = m1

        # ④ o recálculo da PADRÃO da 1ª corretora
        calcs = linhas("multicalculo_calculos", pedido_id=aberto.pedido_id)
        pad = next((c for c in calcs if c["company_id"] == corretoras[0] and c["opcao"] == "padrao"), None)
        if pad and pad.get("negocio_ref"):
            novo = await porta.recalcular(company_id=args.canal, calculo_id=pad["id"], ajuste=ajuste)
            await ate_terminar(ativo, aberto.pedido_id)
            aj = linhas("multicalculo_calculos", id=novo["id"])[0]
            escrever(f"RECÁLCULO {ajuste['tipo']}: {aj['status']} · versão base {pad['versao']} -> nova {aj['versao']}"
                     + (f" · {aj['erro']}" if aj.get("erro") else ""))
        else:
            escrever("RECÁLCULO: não rodou (a padrão da 1ª corretora não tem negócio)")

        # ⑤ os eventos, sem dado pessoal, e os tempos
        andamento = await porta.consultar(company_id=args.canal, pedido_id=aberto.pedido_id)
        for e in andamento.eventos:
            premio = next((o["premio_total"] for o in andamento.ofertas if o.get("id") == e.get("oferta_id")), None)
            escrever(f"  evento {e['id']:>5} · {e['tipo']:<20} · {e.get('seguradora') or '-':<24} · "
                     f"{e.get('familia') or '-':<13} · {premio if premio is not None else '-'}")
        for c in linhas("multicalculo_calculos", pedido_id=aberto.pedido_id):
            def seg(a, b):
                ta, tb = c.get(a), c.get(b)
                if not ta or not tb:
                    return "-"
                return f"{(MOT._ts(tb) - MOT._ts(ta)).total_seconds():.0f}s"
            escrever(f"  cálculo {c['opcao']:<9} corretora {_letra(c['company_id'])} · {c['status']:<9} · 1º evento "
                     f"{seg('disparado_em', 'primeira_oferta_em')} · quadro {seg('disparado_em', 'quadro_pronto_em')}"
                     f" · fechado {seg('disparado_em', 'fechado_em')} · tentativas {c.get('tentativas')}")
        escrever(f"ofertas: {len(andamento.ofertas)} · comissão vista pelo canal: "
                 f"{sum(1 for o in andamento.ofertas if o.get('comissao_percentual') is not None)} (esperado 0)")

        # ⑥ isolamento por SELECT
        ofs = linhas("multicalculo_ofertas", pedido_id=aberto.pedido_id)
        fora = [o for o in ofs if o["company_id"] not in corretoras or o["solicitante_company_id"] != args.canal]
        escrever(f"isolamento: ofertas {len(ofs)} · fora das 2 corretoras ou de outro solicitante = {len(fora)}")
        for c in corretoras:
            try:
                await porta.consultar(company_id=c, pedido_id=aberto.pedido_id)
                escrever(f"  ⚠️ a corretora {c[:8]} LEU o pedido do canal")
            except NaoEncontrado:
                escrever(f"  a corretora {c[:8]} não lê o pedido do canal ✅")

        # ⑦ a varredura de TODAS as colunas de texto das 5 tabelas
        achados = 0
        for t in TABELAS:
            for r in supa.table(t).select("*").execute().data or []:
                for k, v in r.items():
                    texto = v if isinstance(v, str) else (json.dumps(v, ensure_ascii=False)
                                                          if isinstance(v, (dict, list)) else None)
                    if texto and PROIBIDO.search(texto):
                        achados += 1
                        escrever(f"  ⚠️ {t}.{k} (linha {r.get('id')}) casou o padrão proibido")
        escrever(f"varredura senha|loginws|senhaws|token|authorization|url nas 5 tabelas: {achados}")
        rc = 0 if not achados and not fora else 1

        # ⑨ o RESUMO por cálculo (conserto 129-B, canário 05/10): opção · corretora A/B (nunca o nome) · status ·
        # ofertas · seguradoras com oferta · tempo até a 1ª oferta e até o quadro. Sem dado pessoal.
        escrever("RESUMO (opção · corretora · status · ofertas · seguradoras com oferta · 1ª oferta · quadro):")
        for c in sorted(linhas("multicalculo_calculos", pedido_id=aberto.pedido_id),
                        key=lambda x: (_letra(x["company_id"]), str(x.get("criado_em") or ""))):
            ofs_c = [o for o in ofs if o.get("calculo_id") == c["id"]] or linhas("multicalculo_ofertas",
                                                                                calculo_id=c["id"])
            segs = {o.get("seguradora_codigo") if o.get("seguradora_codigo") is not None else o.get("seguradora")
                    for o in ofs_c}
            escrever(f"  {c['opcao']:<9} · {_letra(c['company_id'])} · {c['status']:<9} · ofertas {len(ofs_c):>3} · "
                     f"seguradoras {len(segs):>2} · 1ª oferta {_dt(c, 'disparado_em', 'primeira_oferta_em')} · "
                     f"quadro {_dt(c, 'disparado_em', 'quadro_pronto_em')}")
    finally:
        # ⑧ SEMPRE: logout, contas `teste` -> pausado e senha apagada
        for m in motores:
            try:
                await m.encerrar()
            except Exception as e:  # noqa: BLE001
                escrever(f"⚠️ desligar um motor falhou ({type(e).__name__})")
        for nav in navegadores:
            try:
                await nav.close()
            except Exception:  # noqa: BLE001
                pass
        if pw is not None:
            await pw.stop()
        for conta in contas:
            if conta.get("robo_estado") == ROB.TESTE:
                (supa.table("portal_accounts").update({"robo_estado": ROB.PAUSADO, "secret_encrypted": None})
                 .eq("id", conta["id"]).eq("company_id", conta["company_id"]).execute())
                escrever(f"conta de teste {conta['id']}: pausada e senha apagada")
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    # 📊 05/10 21:27: o console Windows (cp1252) derrubou o canário com UnicodeEncodeError no meio da execução — a
    # saída nunca derruba o canário: o que não cabe na tabela do console vira "?" (como `comando_robo.main`)
    for _fluxo in (sys.stdout, sys.stderr):
        try:
            _fluxo.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001 — fluxo substituído (testes, pipes)
            pass
    args = _parser().parse_args(argv)
    if os.environ.get("AUTOBROKERS_CANARIO") != "1":
        print("RECUSADO: o canário exige AUTOBROKERS_CANARIO=1 no processo")
        return 2
    from portal_worker.worker import _supabase

    return asyncio.run(executar(args, supa=_supabase()))


if __name__ == "__main__":
    sys.exit(main())
