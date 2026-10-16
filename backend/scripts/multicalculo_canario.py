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

SPEC-129-D (V3) — `--ramo 91`: UMA cotação de VIDA INDIVIDUAL de TESTE pelo MESMO porta → motor → robô, na conta da
corretora (o `--corretora` uma vez, o uuid — CLAUDE.md §13.9: nenhum nome de corretora no script), numa conta escolhida
(`--conta <uuid do portal_accounts>`, opcional; sem ela, o rodízio do motor):

    AUTOBROKERS_CANARIO=1 … .venv/Scripts/python.exe scripts/multicalculo_canario.py --ramo 91 \
        --corretora <uuid> [--conta <uuid>] [--comissao 10]

  o pedido é o do BLOCO 0 (embutido, NADA de pessoa real): "TESTE AUTOBROKERS", CPF GERADO com dígito válido (semente
  fixa), 10/05/1985, M, casado(a), CEP 89201-000, não fumante, renda 8.000, sem esporte radical, "Analista de sistemas",
  capital de Morte 100.000, só a opção "padrão" (= 1 calcularV2) e a comissão de vida EXPLÍCITA (📊 as contas têm
  `percComissaoVida` 0 — sem ela nenhuma seguradora entra; é um TESTE, declarado). Imprime só: as seguradoras que
  entraram e as que saíram (com o motivo), as ofertas lidas (seguradora, prêmio, capital), as recusas, as trocas de token
  e o logout. ⛔ Nunca emissão; nada ao cliente; a chave MULTICALCULO_VIDA_LIGADO é ligada SÓ neste processo.
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
    # SPEC-129-D: os três deixam de ser `required` no PARSER (a vida não usa canal nem perfil); o auto os exige em
    # `executar` — a mesma recusa, com rc 2
    p.add_argument("--canal", help="auto: o uuid do canal")
    p.add_argument("--corretora", action="append",
                   help="auto: 2 vezes (as duas corretoras) · vida (--ramo 91): 1 vez, a corretora dona do Agger")
    p.add_argument("--perfil", help="auto: JSON local FORA do git com o pedido ({grupo: {campo: valor}})")
    p.add_argument("--ramo", type=int, choices=(31, 91), default=31,
                   help="31 = o canário do auto (o de sempre) · 91 = 1 cotação de VIDA de teste (SPEC-129-D)")
    p.add_argument("--conta", default=None, help="vida: o uuid da conta do Agger (portal_accounts) que calcula")
    p.add_argument("--comissao", type=float, default=10.0,
                   help="vida: a comissão de vida EXPLÍCITA do teste (em %%; as contas têm percComissaoVida 0)")
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
    if not args.canal or not args.corretora or not args.perfil:
        escrever("RECUSADO: o canário do auto exige --canal, --corretora (2 vezes) e --perfil")
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


# ======================================================================================================================
# SPEC-129-D (V3) — o canário da VIDA INDIVIDUAL (ramo 91): 1 cotação de TESTE pelo mesmo porta → motor → robô
# ======================================================================================================================
#: a semente do CPF de teste (📊 BLOCO 0 M6: "CPF GERADO com dígito válido — semente fixa, não é de pessoa conhecida")
SEMENTE_DO_CPF = 1291016


def cpf_de_teste(semente: int = SEMENTE_DO_CPF) -> str:
    """Um CPF GERADO (9 dígitos de uma semente fixa + os 2 verificadores pela regra da Receita) — de ninguém."""
    import random

    rng = random.Random(semente)
    while True:
        base = [rng.randint(0, 9) for _ in range(9)]
        if len(set(base)) > 1:
            break
    for peso in (10, 11):
        soma = sum(d * (peso - i) for i, d in enumerate(base))
        resto = (soma * 10) % 11
        base.append(0 if resto == 10 else resto)
    return "".join(map(str, base))


def pedido_de_teste_da_vida(*, comissao: float, hoje=None) -> Dict[str, Any]:
    """O pedido de VIDA do BLOCO 0 (dados de TESTE) — o dict que `PedidoDeCalculo.de_dict(..., ramo=91)` aceita."""
    from datetime import date as _date

    hoje = hoje or _date.today()
    return {
        "segurado": {"cpf": cpf_de_teste(), "nome": "TESTE AUTOBROKERS", "data_nascimento": "1985-05-10",
                     "sexo": "Masculino", "estado_civil": "Casado(a)", "cep": "89201000",
                     "profissao_texto": "Analista de sistemas"},
        "vida": {"capital_morte": 100000, "fumante": False, "renda_mensal": 8000, "esporte_radical": False,
                 "vigencia_inicio": (hoje + timedelta(days=1)).isoformat(), "origem": "cotacao"},
        "comissao_desconto": {"comissao_percentual": float(comissao)},
    }


async def executar_vida(args, *, supa, escrever: Callable[[str], Any] = print, abrir_navegador=None,
                        upload=None, intervalo_s: Optional[float] = None) -> int:
    """O canário de VIDA. As bordas (banco, navegador, upload) são injetáveis só para o teste do script."""
    from app.services.multicalculo import MulticalculoProvider, PedidoDeCalculo
    from app.services.multicalculo.repositorio import RepositorioMulticalculo
    from portal_worker.multicalculo import contrato as K
    from portal_worker.multicalculo import motor as MOT
    from portal_worker.multicalculo import robos as ROB
    from portal_worker.multicalculo.agger_sessao import URL_BASE_AGGER, Sessoes

    if os.environ.get("AUTOBROKERS_CANARIO") != "1":
        escrever("RECUSADO: o canário exige AUTOBROKERS_CANARIO=1 no processo")
        return 2
    if args.canal or args.perfil:
        escrever("RECUSADO: a vida usa o pedido de TESTE embutido (sem --canal e sem --perfil)")
        return 2
    if len(args.corretora or []) != 1:
        escrever("RECUSADO: na vida, passe --corretora UMA vez (o uuid da corretora dona do Agger)")
        return 2
    if int(args.teto) < 1:
        escrever(f"RECUSADO: o canário de vida faz 1 cálculo e o --teto é {args.teto}")
        return 2
    if not (0 < float(args.comissao) <= 100):
        escrever("RECUSADO: --comissao entre 0 e 100 (a de vida das contas é 0: sem ela nenhuma seguradora entra)")
        return 2
    corretora = str(args.corretora[0]).strip().lower()
    os.environ["MULTICALCULO_MOTOR_LIGADO"] = "true"     # SÓ neste processo (o serviço não é tocado)
    os.environ["MULTICALCULO_VIDA_LIGADO"] = "1"         # idem: a chave da vida (D-129D-09) segue desligada no serviço
    pedido = PedidoDeCalculo.de_dict(pedido_de_teste_da_vida(comissao=args.comissao), ramo=K.RAMO_VIDA)
    escrever(f"pedido de TESTE: {pedido!r}")

    contas = list(ROB.candidatos(supa, corretora))
    conta = str(args.conta).strip().lower() if args.conta else None
    if conta is not None and conta not in {str(c["id"]).lower() for c in contas}:
        escrever("RECUSADO: --conta não é uma conta do Agger desta corretora (rodízio global/teste)")
        return 2
    escrever("robôs: " + " · ".join(f"{x['id']} ({x['robo_estado']}, {x.get('uso')})" for x in contas))
    porta = MulticalculoProvider(RepositorioMulticalculo(supa))
    contador = _Contador(intervalo_s)
    sessoes_abertas: List[Any] = []
    navegadores: List[Any] = []
    motores: List[Any] = []
    meus_pedidos: set = set()
    pw = None
    rc = 1

    class _SessoesContadas(Sessoes):
        """As sessões REAIS, guardadas para contar no fim as trocas de token e o logout (a guarda conta)."""

        async def obter(self, *a, **k):
            s = await super().obter(*a, **k)
            if s not in sessoes_abertas:
                sessoes_abertas.append(s)
            return s

    def linhas(tabela: str, **filtro) -> List[Dict[str, Any]]:
        q = supa.table(tabela).select("*")
        for k, v in filtro.items():
            q = q.eq(k, v)
        return list(q.execute().data or [])

    try:
        aberto = await porta.calcular(company_id=corretora, pedido=pedido, origem="teste", opcoes=("padrao",),
                                      quadro_s=int(args.quadro_s))
        pedido = None   # noqa: F841
        meus_pedidos.add(aberto.pedido_id)
        if conta is not None:
            (supa.table("multicalculo_calculos")
             .update({"conta_exigida_id": conta, "conta_regra": "canario_vida",
                      "conta_motivo": "o canário de vida escolheu a conta (--conta)"})
             .eq("pedido_id", aberto.pedido_id).eq("company_id", corretora).eq("status", "na_fila").execute())
        escrever(f"pedido {aberto.pedido_id}: {len(aberto.calculos)} cálculo(s) na fila"
                 + (f" · conta {conta}" if conta else " · conta: o rodízio do motor"))
        if abrir_navegador is not None:
            nav = await abrir_navegador()
        else:
            from playwright.async_api import async_playwright

            from portal_worker.worker import _launch_kwargs

            pw = await async_playwright().start()
            nav = await pw.chromium.launch(**_launch_kwargs())
        navegadores.append(nav)
        kw = {"upload": upload} if upload is not None else {}
        m = MOT.Motor(supa, sessoes=_SessoesContadas(nav, url_base=args.url_base or URL_BASE_AGGER),
                      robo=contador.mod, canario=True, dono=f"canario-vida:{socket.gethostname()}:{os.getpid()}",
                      somente_pedidos=meus_pedidos, **kw)
        motores.append(m)
        t0 = time.time()
        terminou = False
        while time.time() - t0 < 600:
            await m.uma_volta()
            if all(c["status"] in TERMINAIS for c in linhas("multicalculo_calculos", pedido_id=aberto.pedido_id)):
                terminou = True
                break
            await asyncio.sleep(2)
        if not terminou:
            escrever("⚠️ o pedido não terminou no limite")
        await m.encerrar()                              # logout pela tela (a sessão sai; o motor não fica de pé)
        motores.remove(m)

        calcs = linhas("multicalculo_calculos", pedido_id=aberto.pedido_id)
        evs = linhas("multicalculo_eventos", pedido_id=aberto.pedido_id)
        ofs = linhas("multicalculo_ofertas", pedido_id=aberto.pedido_id)
        for c in calcs:
            escrever(f"cálculo {c['opcao']} · {c['status']} · conta {c.get('account_id')}"
                     + (f" · {c['erro']}" if c.get("erro") else ""))
        sairam = [e for e in evs if e.get("tipo") == K.SEM_ATIVIDADE_COMPATIVEL]
        entraram = sorted({(e.get("seguradora_codigo"), e.get("seguradora")) for e in evs
                           if e.get("tipo") not in (K.SEM_ATIVIDADE_COMPATIVEL, K.CONJUNTO_FECHADO)
                           and e.get("seguradora_codigo") is not None}, key=lambda x: x[0])
        escrever(f"ENTRARAM no cálculo ({len(entraram)}): "
                 + (" · ".join(f"{cod} {nome or '-'}" for cod, nome in entraram) or "nenhuma"))
        escrever(f"SAÍRAM antes do cálculo ({len(sairam)}):")
        for e in sorted(sairam, key=lambda x: x.get("seguradora_codigo") or 0):
            escrever(f"  {e.get('seguradora_codigo')} {e.get('seguradora') or '-'} · {e.get('motivo') or '-'}")
        escrever(f"OFERTAS lidas ({len(ofs)}):")
        for o in sorted(ofs, key=lambda x: float(x.get("premio_total") or 0)):
            capital = (o.get("coberturas") or {}).get("isAppMorte")
            escrever(f"  {o.get('seguradora_codigo')} {o.get('seguradora') or '-'} · prêmio {o.get('premio_total')} · "
                     f"capital {capital if capital is not None else '-'} · pacote {o.get('pacote') or '-'}")
        recusas = [e for e in evs if e.get("tipo") == K.SEGURADORA_RECUSOU]
        escrever(f"RECUSAS ({len(recusas)}):")
        for e in sorted(recusas, key=lambda x: x.get("seguradora_codigo") or 0):
            escrever(f"  {e.get('seguradora_codigo')} {e.get('seguradora') or '-'} · {e.get('familia') or '-'} · "
                     f"{e.get('motivo') or '-'}")
        for s in sessoes_abertas:
            n = s.contagem_de_escritas()
            escrever(f"SESSÃO: logins {n.get('login')} · trocas de token (login/pdocs) {n.get('pdocs')} · calcularV2 "
                     f"{n.get('calcularV2')} · logout {n.get('logout')} · barradas pela guarda {n.get('barradas')}")
        if not sessoes_abertas:
            escrever("SESSÃO: nenhuma (o login não aconteceu)")
        escrever(f"calcularV2 pelo robô: {contador.n} (esperado 1)")
        # a varredura: nada de senha/token/url, e nada do pedido de teste (CPF, renda) nas linhas DESTE pedido
        achados = 0
        proibido = re.compile(PROIBIDO.pattern + "|" + cpf_de_teste() + r"|fumante|rendaMensal", re.I)
        for t, rs in (("multicalculo_calculos", calcs), ("multicalculo_eventos", evs), ("multicalculo_ofertas", ofs),
                      ("multicalculo_pedidos", linhas("multicalculo_pedidos", id=aberto.pedido_id))):
            for r in rs:
                for k, v in r.items():
                    if k == "pedido_cifrado":
                        continue
                    texto = v if isinstance(v, str) else (json.dumps(v, ensure_ascii=False)
                                                          if isinstance(v, (dict, list)) else None)
                    if texto and proibido.search(texto):
                        achados += 1
                        escrever(f"  ⚠️ {t}.{k} casou o padrão proibido")
        escrever(f"varredura (senha|token|url|o CPF de teste|fumante|renda) nas linhas do pedido: {achados}")
        rc = 0 if not achados and contador.n <= 1 else 1
    finally:
        for m in motores:
            try:
                await m.encerrar()
            except Exception as e:  # noqa: BLE001
                escrever(f"⚠️ desligar o motor falhou ({type(e).__name__})")
        for nav in navegadores:
            try:
                await nav.close()
            except Exception:  # noqa: BLE001
                pass
        if pw is not None:
            await pw.stop()
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

    if args.ramo == 91:
        return asyncio.run(executar_vida(args, supa=_supabase()))
    return asyncio.run(executar(args, supa=_supabase()))


if __name__ == "__main__":
    sys.exit(main())
