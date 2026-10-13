# -*- coding: utf-8 -*-
"""O CANÁRIO da madrugada da renovação — SPEC-131-A F4 (D-131-31 relógio injetado · D-131-35 corretora real).

    cd backend
    AUTOBROKERS_CANARIO=1 PYTHONIOENCODING=utf-8 python scripts/canario_madrugada_renovacao.py \
        --env <arquivo .env FORA do git> --corretora <uuid> --infocap <PREFIXO> [--max 5] [--saida <json fora do git>]

O que faz, no PROCESSO (nada de serviço é tocado; nenhum Work Run, nenhum tick):
  ① lê a lista REAL de `/renovacoes` da corretora (login da InfoCap do arquivo, EM PROCESSO — nenhuma
     `tenant_connections` é criada ou alterada) e escolhe ≤ `--max` itens: ≥ 2 AUTO, ≥ 1 não cotável, 1 RESI se houver,
     e o DIA injetado em que todos vencem em ≤ 10 dias
  ② roda os PASSOS REAIS do produto com esse dia: preparar (canario=True) → calcular → acompanhar → conferir
     (canario=True) → desvio → avisar — a fonte só é FILTRADA para os itens escolhidos (≤ 5)
  ③ mede por SELECT: completude, estados e motivos, `calculando` órfão, linhas em outra corretora, pedidos gravados,
     sessões/eventos do Agger, custo de modelo (`token_usage_logs`) no intervalo
  ④ LENTE DO DADO: a completude reconferida por um 3º caminho — um GET novo de `/renovacoes` por `urllib`, SEM o código
     do produto, × o SELECT direto nas tabelas × a linha de `renovacao_dias`

As TRAVAS do canário (no processo, nunca no produto):
  · ⛔ o aviso NÃO é publicado: `renovacao.registrar_aviso` é capturado (só contagens) — o briefing não tem marca de
    canário e a aba Entregas da corretora mostraria um aviso de ensaio como real
  · ⛔ nenhum pedido é gravado: `MulticalculoProvider._gravar` levanta. O portal-worker de PRODUÇÃO tem o motor ligado
    com o código anterior à 131-A (que não conhece `anterior`/`franquia_reduzida`) e não há mecanismo que garanta que
    só um motor local pegue os cálculos (a lease `robo_dono` é por conta e expira em 90 s; a fila é global)
  · a ficha do produto roda, mas SEM o PDF (`_maybe_attach_official_policy_document_evidence` devolve o pack): o
    leitor documental grava o documento no acervo da
    corretora (linha + bytes) e chama modelo. Sem o PDF, o `anterior` sai das coberturas do CADASTRO (o que faltar
    vale o preset, marcado "não conferido" — F2); o perfil do segurado vem da InfoCap (F5, `perfil_da_renovacao`)
⛔ Saída só com contagens, ramos, estados, motivos e hashes curtos — nenhum nome, documento, placa ou nº de apólice.

SPEC-131-A F5 — `--calcular` (≤ 2 AUTO; PORTAL_HEADLESS_MODE=classic nesta máquina): o CANÁRIO COM CÁLCULO.
  · a gravação do pedido é LIBERADA, mas cada cálculo nasce com `disponivel_em` = agora + 6 h (o `_reservar` do motor de
    PRODUÇÃO — fila global — só pega `disponivel_em <= agora`); o repositório é embrulhado NO PROCESSO, nada no produto
  · ESTE processo roda o motor REAL (`motor.Motor`) com `somente_pedidos` = os pedidos dele e `ignorar_espera=True` (o
    ponto de entrada "processar estes cálculos", F5) e um `dono` próprio — a prova por SELECT é que todo cálculo fechado
    tem ESTE dono; no fim, `encerrar()` (logout de toda sessão, o navegador fecha)
  · o desvio das 06:15 NÃO roda (abriria pedido novo que este motor não processaria); cálculo que sobrar na fila é
    cancelado pelo repositório do produto (nunca fica para o motor de produção pegar em 6 h)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ANTECEDENCIA = 10


def _h(valor: Any) -> str:
    return hashlib.sha256(str(valor).encode("utf-8")).hexdigest()[:10]


def _carregar_env(caminho: Path) -> None:
    raiz = BACKEND.parent.resolve()
    if raiz in caminho.resolve().parents:
        raise SystemExit("RECUSADO: o arquivo de segredos não pode estar dentro do repositório")
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, _, v = linha.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="canario_madrugada_renovacao")
    p.add_argument("--env", required=True)
    p.add_argument("--corretora", required=True, help="uuid da corretora do canário")
    p.add_argument("--infocap", required=True, help="prefixo das variáveis INFOCAP_<P>_LOGIN/_PASSWORD no arquivo")
    p.add_argument("--max", type=int, default=5)
    p.add_argument("--saida", default=None)
    p.add_argument("--calcular", action="store_true", help="F5: calcula de verdade (≤ 2 AUTO) só no motor DESTE processo")
    p.add_argument("--teto-min", type=int, default=25, help="F5: minutos que o motor do canário espera os cálculos")
    p.add_argument("--quantos", type=int, default=2, choices=(1, 2, 3), help="F6: quantos AUTO calcular (≤ 3)")
    return p


# ---------------------------------------------------------------------------------------------------------------------
# a escolha dos itens e do dia
# ---------------------------------------------------------------------------------------------------------------------
def _familia(sigla: str) -> Optional[str]:
    from app.providers.policy_data_provider import familia_de_ramo

    try:
        return familia_de_ramo(sigla)
    except Exception:  # noqa: BLE001
        return None


def escolher(linhas: List[Dict[str, Any]], hoje: date, maximo: int) -> Tuple[Optional[date], List[Dict[str, Any]]]:
    from app.services.multicalculo import renovacao as R
    from app.services.multicalculo.pedido import RAMO_DO_AGGER_POR_FAMILIA

    itens = []
    for cru in linhas:
        campos = R.linha_da_infocap({k: v for k, v in cru.items() if k not in ("cic", "cpf_cnpj")})
        if campos is None:
            continue
        fam = _familia(campos["ramo_sigla"] or "")
        itens.append({"cru": cru, "fim": R.data_de(campos["fimvig"]), "sigla": campos["ramo_sigla"] or "",
                      "cotavel": fam in RAMO_DO_AGGER_POR_FAMILIA, "fam": fam,
                      "ordem": _h(f"{campos['codfil']}:{campos['nosnum']}")})
    for k in range(0, 50):
        d = hoje + timedelta(days=k)
        janela = sorted((x for x in itens if d <= x["fim"] <= d + timedelta(days=ANTECEDENCIA)),
                        key=lambda x: (x["fim"], x["ordem"]))
        auto = [x for x in janela if x["fam"] == "auto"][:2]
        nao = [x for x in janela if not x["cotavel"]][:1]
        resi = [x for x in janela if x["fam"] == "resi"][:1]
        if len(auto) >= 2 and nao:
            escolha = (auto + nao + resi)[:maximo]
            return d, escolha
    return None, []


#: F5: o que o perfil precisa trazer para o AUTO fechar sem a ficha (a placa, aqui, vem do item da InfoCap). F6: o
#: combustível saiu da lista — a placa o supre (os 7 códigos da tela); o canário CONTA quantos vieram da InfoCap
PERFIL_QUE_FECHA = (("segurado", "cpf_cnpj"), ("segurado", "nascimento"), ("segurado", "cep"),
                    ("condutor", "tempo_habilitacao"), ("veiculo", "placa"))


def escolher_calculaveis(linhas: List[Dict[str, Any]], hoje: date, fonte: Any, cid: str, *, quantos: int = 2,
                         olhar: int = 15) -> Tuple[Optional[date], List[Dict[str, Any]], Dict[str, Any]]:
    """F5 (`--calcular`): ≤ `quantos` AUTO que vencem em ≤ 10 dias e cujo perfil FECHA (o `perfil_da_renovacao.montar`
    do produto, nos primeiros `olhar` candidatos pela ordem do hash) + 1 não cotável. Devolve também a CONTAGEM do que
    falta nos candidatos (só nomes de campo e quantos) — a cobertura real do perfil."""
    from app.services.multicalculo import perfil_da_renovacao as PR
    from app.services.multicalculo import renovacao as R
    from app.services.multicalculo.pedido import RAMO_DO_AGGER_POR_FAMILIA

    janela = []
    for cru in linhas:
        campos = R.linha_da_infocap({k: v for k, v in cru.items() if k not in ("cic", "cpf_cnpj")})
        if campos is None:
            continue
        fim = R.data_de(campos["fimvig"])
        if hoje <= fim <= hoje + timedelta(days=ANTECEDENCIA):
            fam = _familia(campos["ramo_sigla"] or "")
            janela.append({"cru": cru, "fim": fim, "sigla": campos["ramo_sigla"] or "", "fam": fam,
                           "cotavel": fam in RAMO_DO_AGGER_POR_FAMILIA, "campos": campos,
                           "ordem": _h(f"{campos['codfil']}:{campos['nosnum']}")})
    janela.sort(key=lambda x: x["ordem"])
    medida: Dict[str, Any] = {"olhados": 0, "fecham": 0, "falta": {}, "combustivel": {}}
    fecham = []
    for x in [y for y in janela if y["fam"] == "auto"][:olhar]:
        medida["olhados"] += 1
        try:
            perfil, _nao = PR.montar(cid, {**x["campos"], "ramo_sigla": "AUTO"}, None, None, fonte)
        except Exception as exc:  # noqa: BLE001
            medida["falta"][f"erro:{type(exc).__name__}"] = medida["falta"].get(f"erro:{type(exc).__name__}", 0) + 1
            continue
        faltam = [f"{g}.{c}" for g, c in PERFIL_QUE_FECHA if c not in (perfil.get(g) or {})]
        for n in faltam:
            medida["falta"][n] = medida["falta"].get(n, 0) + 1
        # F6: de onde vem o combustível (o rótulo da tela pela InfoCap, ou a placa)
        comb = (perfil.get("veiculo") or {}).get("combustivel") or "pela_placa"
        medida["combustivel"][comb] = medida["combustivel"].get(comb, 0) + 1
        if not faltam:
            medida["fecham"] += 1
            fecham.append((comb, x))
    # F6: ≥ 1 que NÃO é flex primeiro (a prova do conserto), depois a ordem do hash
    outros = [x for comb, x in fecham if comb != "flex"][:1]
    autos = outros + [x for _c, x in fecham if all(x is not o for o in outros)]
    autos = autos[:quantos]
    if not autos:
        return None, [], medida
    nao = [y for y in janela if not y["cotavel"]][:1]
    return hoje, autos + nao, medida


class FonteFiltrada:
    """A FonteInfocap REAL; `renovacoes_cruas` devolve a resposta REAL só com os itens do canário."""

    def __init__(self, fonte: Any, chaves: set):
        self._fonte, self._chaves = fonte, chaves
        self.leituras = 0

    def renovacoes_cruas(self, inicio, fim):
        from app.services.multicalculo import renovacao as R

        self.leituras += 1
        return [x for x in self._fonte.renovacoes_cruas(inicio, fim)
                if (R.codfil_de(x.get("codfil")), R.nosnum_de(x.get("nosnum"))) in self._chaves]

    def __getattr__(self, nome):
        return getattr(self._fonte, nome)


# ---------------------------------------------------------------------------------------------------------------------
# a LENTE DO DADO — um GET de /renovacoes SEM o código do produto
# ---------------------------------------------------------------------------------------------------------------------
def lente_renovacoes(base: str, login: str, senha: str, d: date, chaves: set) -> int:
    corpo = json.dumps({"email": login, "senha": senha, "aplicacao": 0}).encode("utf-8")
    req = urllib.request.Request(f"{base.rstrip('/')}/login", data=corpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    token = resp.get("token") or (resp.get("data") or {}).get("token") if isinstance(resp, dict) else None
    q = urllib.parse.urlencode({"dt_ini": d.strftime("%d/%m/%Y"),
                                "dt_fim": (d + timedelta(days=ANTECEDENCIA)).strftime("%d/%m/%Y"),
                                "qtd_pag": 5000, "pag": 1, "ordem": "nosnum", "orientacao": "asc", "texto": "",
                                "cancelado": "F", "resgates": "F"})
    req = urllib.request.Request(f"{base.rstrip('/')}/renovacoes?{q}", headers={"Authorization": str(token)})
    with urllib.request.urlopen(req, timeout=120) as r:
        bruto = json.loads(r.read())
    linhas = bruto.get("renovacoes") if isinstance(bruto, dict) else bruto
    vistos = set()
    for x in linhas or []:
        if str(x.get("tipdoc") or "A").upper() != "A" or str(x.get("cancelado") or "").upper() in ("T", "S"):
            continue
        n = str(x.get("nosnum")).removesuffix(".0")
        try:
            c = int(str(x.get("codfil")).strip())
        except ValueError:
            c = 1
        if (c, n) in chaves:
            vistos.add((c, n))
    return len(vistos)


# ---------------------------------------------------------------------------------------------------------------------
async def executar(args) -> Dict[str, Any]:
    from supabase import create_client

    from app.api import infocap_connector as IC
    from app.comercial.fonte_infocap import FonteInfocap
    from app.services.encryption_service import get_encryption_service
    from app.services.multicalculo import conferencia_da_renovacao as CONF
    from app.services.multicalculo import madrugada as M
    from app.services.multicalculo import porta as PORTA
    from app.services.multicalculo import renovacao as R

    cid = R._uuid(args.corretora)
    # a rota interna do detalhe exige a chave interna: no PROCESSO do canário ela é uma chave de uso único (a rota é
    # chamada como função, nunca por HTTP) — nenhum segredo do servidor é lido nem copiado
    os.environ.setdefault("BACKEND_INTERNAL_API_KEY", hashlib.sha256(os.urandom(32)).hexdigest())
    supa = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    db = SimpleNamespace(client=supa, table=supa.table)
    base = os.environ["INFOCAP_BASE_URL"]
    login = os.environ[f"INFOCAP_{args.infocap}_LOGIN"]
    senha = os.environ[f"INFOCAP_{args.infocap}_PASSWORD"]
    t0 = datetime.now(timezone.utc)
    rel: Dict[str, Any] = {"inicio_utc": t0.isoformat(timespec="seconds"), "corretora_hash": _h(cid)}

    # ① a lista real e a escolha
    fonte_real = FonteInfocap(login, senha, base_url=base, rotulo=f"canario-{_h(cid)}")
    hoje = date.today()
    t = time.monotonic()
    linhas = await asyncio.to_thread(fonte_real.renovacoes_cruas, hoje, hoje + timedelta(days=60))
    rel["t_lista_s"] = round(time.monotonic() - t, 1)
    if args.calcular:
        dia, escolha, rel["perfil_dos_candidatos"] = await asyncio.to_thread(
            escolher_calculaveis, linhas, hoje, fonte_real, cid, quantos=args.quantos)
    else:
        dia, escolha = escolher(linhas, hoje, args.max)
    if dia is None:
        rel["recusa"] = "nenhum dia com ≥ 2 AUTO e ≥ 1 não cotável em ≤ 10 dias"
        return rel
    chaves = {(R.codfil_de(x["cru"].get("codfil")), R.nosnum_de(x["cru"].get("nosnum"))) for x in escolha}
    rel.update({"lista_60d": len(linhas), "dia_injetado": dia.isoformat(),
                "escolhidos": [{"h": x["ordem"], "ramo": x["sigla"], "cotavel": x["cotavel"],
                                "vence_em_dias": (x["fim"] - dia).days} for x in escolha]})
    fonte = FonteFiltrada(fonte_real, chaves)

    # as travas do canário (no processo)
    avisos: List[Dict[str, Any]] = []

    def aviso_capturado(_db, company_id, *, dia, assunto, texto, user_id=None, severidade="info", valores=None, **_k):
        avisos.append({"assunto": assunto, "para": "pessoa" if user_id else "corretora", "severidade": severidade,
                       "valores": dict(valores or {}), "tamanho": len(texto),
                       "texto": texto if args.calcular else None})   # `madrugada._texto`: contagens e motivos
        return None

    async def abrir(_db, company_id):
        if R._uuid(company_id) != cid:
            raise RuntimeError("canário: só a corretora do canário")
        return fonte

    original_resolver = IC._resolve_infocap_connection
    cifrado = get_encryption_service().encrypt(json.dumps({"username": login, "password": senha}))

    async def conexao_em_processo(dbx, *, company_id, requested_connection_id=None):
        if str(company_id) != cid:
            return await original_resolver(dbx, company_id=company_id, requested_connection_id=requested_connection_id)
        return {"selected_connection": {"id": f"canario-{_h(cid)}", "company_id": cid,
                                        "connection_config": {"base_url": base}, "encrypted_secret_ref": cifrado},
                "status": "probe_ready", "summary": {}}

    async def sem_pdf(*, pack, **_k):
        # a ficha do PRODUTO (`madrugada.ficha_da_apolice`: chave interna, cliente assíncrono, um detalhe só) roda
        # inteira; só a leitura do PDF fica de fora (grava o documento no acervo da corretora e chama modelo)
        return pack

    def gravacao_proibida(*_a, **_k):
        raise RuntimeError("canario_sem_pedido: o motor de produção está ligado com o código anterior")

    IC._resolve_infocap_connection = conexao_em_processo
    M.abrir_fonte = abrir
    CONF._abrir_fonte = abrir
    IC._maybe_attach_official_policy_document_evidence = sem_pdf
    R.registrar_aviso = aviso_capturado
    meus_pedidos: set = set()
    if not args.calcular:
        PORTA.MulticalculoProvider._gravar = gravacao_proibida
    else:
        from app.services.multicalculo.repositorio import RepositorioMulticalculo

        gravar_do_produto = RepositorioMulticalculo.gravar_pedido
        espera = timedelta(hours=6)

        def gravar_com_espera(self, pedido, calculos):
            if str(pedido.get("company_id")) != cid or len(meus_pedidos) >= args.quantos:
                raise RuntimeError("canario: só ≤ --quantos pedidos, só da corretora do canário")
            futuro = (datetime.now(timezone.utc) + espera).isoformat()
            calculos = [{**c, "disponivel_em": futuro} for c in calculos]     # a fila GLOBAL não o vê por 6 h
            linha, gravados = gravar_do_produto(self, pedido, calculos)
            meus_pedidos.add(str(linha["id"]))
            return linha, gravados

        RepositorioMulticalculo.gravar_pedido = gravar_com_espera

    contas_antes = _contas(supa, cid)
    passos: Dict[str, Any] = {}
    dono_do_motor = f"canario-f5-{_h(cid)}-{os.getpid()}:mc"
    rel["dono_do_motor"] = dono_do_motor
    sequencia = [("preparar", lambda: M.preparar_dia(db, cid, dia, canario=True)),
                 ("calcular", lambda: M.calcular_dia(db, cid, dia))]
    if args.calcular:
        sequencia.append(("motor_do_canario", lambda: motor_do_canario(supa, meus_pedidos, dono_do_motor,
                                                                         teto_s=60 * args.teto_min)))
    sequencia += [("acompanhar", lambda: asyncio.to_thread(M.acompanhar, db, cid, por="canario.acompanhar")),
                  ("conferir", lambda: CONF.conferir_dia(db, cid, dia, canario=True))]
    if not args.calcular:
        sequencia.append(("desvio", lambda: M.desvio_dia(db, cid, dia)))
    sequencia.append(("avisar", lambda: asyncio.to_thread(M.avisar_dia, db, cid, dia)))
    for nome, fn in sequencia:
        t = time.monotonic()
        try:
            r = await fn()
            passos[nome] = {"t_s": round(time.monotonic() - t, 1), "resultado": r}
        except Exception as exc:  # noqa: BLE001
            passos[nome] = {"t_s": round(time.monotonic() - t, 1), "erro": type(exc).__name__}
    rel["passos"] = passos
    rel["avisos_capturados"] = avisos
    if args.calcular:
        rel["calculo"] = medir_o_calculo(supa, cid, meus_pedidos, dono_do_motor)

    # ③ a medida por SELECT
    t1 = datetime.now(timezone.utc)
    itens = [x for x in (supa.table("renovacoes").select("id, company_id, ramo_sigla, estado, motivo, canario, "
                                                         "pedido_id, fimvig, calcular_em")
                         .eq("company_id", cid).eq("canario", True).execute().data or [])]
    ids = [x["id"] for x in itens]
    evs = supa.table("renovacao_eventos").select("renovacao_id, para, motivo, dados").eq("company_id", cid) \
        .in_("renovacao_id", ids or ["00000000-0000-0000-0000-000000000000"]).execute().data or []
    fora = supa.table("renovacoes").select("id", count="exact").neq("company_id", cid).execute().count
    peds = supa.table("multicalculo_pedidos").select("id", count="exact").eq("company_id", cid) \
        .gte("criado_em", t0.isoformat()).execute().count
    peds_renov = supa.table("multicalculo_pedidos").select("id", count="exact") \
        .in_("renovacao_id", ids or ["00000000-0000-0000-0000-000000000000"]).execute().count
    ev_mc = supa.table("multicalculo_eventos").select("id", count="exact").eq("company_id", cid) \
        .gte("criado_em", t0.isoformat()).execute().count
    tokens = supa.table("token_usage_logs").select("id, total_cost_usd").eq("company_id", cid).gte("created_at", t0.isoformat()) \
        .lte("created_at", t1.isoformat()).execute().data or []
    dia_linha = supa.table("renovacao_dias").select("*").eq("company_id", cid).eq("dia", dia.isoformat()) \
        .execute().data or []
    calculadas = sum(1 for x in itens if x["estado"] in R.ESTADOS_CALCULADOS)
    pend = [x for x in itens if x["estado"] == "pendente" and x.get("motivo")]
    esperadas_tabela = [x for x in itens if dia.isoformat() <= str(x["fimvig"]) <=
                        (dia + timedelta(days=ANTECEDENCIA)).isoformat() and x["estado"] != "substituida"]
    faltando_por_item = {}
    for e in evs:
        f = (e.get("dados") or {}).get("faltando")
        if f:
            faltando_por_item[e["renovacao_id"]] = len(f)
    rel["medida"] = {
        "itens_canario": len(itens), "estados": R.contar(itens),
        "motivos": sorted({str(x.get("motivo")) for x in pend}),
        "pendentes_com_motivo": len(pend), "calculadas": calculadas,
        "calculando_orfao": sum(1 for x in itens if x["estado"] in R.ESTADOS_EM_VOO),
        "eventos": len(evs), "itens_com_campos_faltando": len(faltando_por_item),
        "campos_faltando_por_item": sorted(faltando_por_item.values()),
        "renovacoes_em_outras_corretoras": fora, "pedidos_gravados_no_intervalo": peds,
        "pedidos_com_renovacao_id": peds_renov, "eventos_do_motor_no_intervalo": ev_mc,
        "contas_do_agger_antes_depois_iguais": contas_antes == _contas(supa, cid),
        "token_usage_logs_no_intervalo": len(tokens),
        "custo_usd_no_intervalo": round(sum(float(x.get("total_cost_usd") or 0) for x in tokens), 6),
        "renovacao_dias": {k: (dia_linha[0] if dia_linha else {}).get(k) for k in
                           ("estado", "esperadas", "calculadas", "pendentes", "falharam", "faltaram",
                            "completude_pct", "cotaveis", "calculadas_de_cotaveis_pct")},
        "renovacao_dias_canario": ((dia_linha[0] if dia_linha else {}).get("detalhes") or {}).get("canario"),
    }
    # ④ a LENTE: 3 caminhos para a mesma completude
    esperadas_lente = await asyncio.to_thread(lente_renovacoes, base, login, senha, dia, chaves)
    feitas = calculadas + len([x for x in pend if x in esperadas_tabela])
    rel["lente"] = {"esperadas_get_direto": esperadas_lente, "esperadas_select": len(esperadas_tabela),
                    "esperadas_renovacao_dias": rel["medida"]["renovacao_dias"]["esperadas"],
                    "completude_select_pct": round(100.0 * feitas / esperadas_lente, 2) if esperadas_lente else None,
                    "completude_renovacao_dias_pct": rel["medida"]["renovacao_dias"]["completude_pct"]}
    rel["leituras_da_fonte_filtrada"] = fonte.leituras
    rel["fim_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return rel


TERMINAIS = ("fechado", "falhou", "incerto", "cancelado", "expirado")


async def motor_do_canario(supa, pedidos: set, dono: str, *, teto_s: int) -> Dict[str, Any]:
    """O motor REAL (`portal_worker.multicalculo.motor.Motor`) só para os pedidos DESTE processo, ignorando a espera
    que os esconde da fila global (F5: `ignorar_espera`). Volta a volta até todo cálculo fechar (ou o teto) e SEMPRE
    `encerrar()` — logout de toda sessão e o navegador fechado."""
    from portal_worker.multicalculo import motor as MOT

    if not pedidos:
        return {"voltas": 0, "grupos": 0, "motivo": "nenhum pedido gravado"}
    m = MOT.Motor(supa, somente_pedidos=set(pedidos), ignorar_espera=True, dono=dono, canario=False)
    voltas = grupos = 0
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < teto_s:
            grupos += await m.uma_volta(esperar=True)
            voltas += 1
            calcs = supa.table("multicalculo_calculos").select("status").in_("pedido_id", sorted(pedidos)) \
                .execute().data or []
            if calcs and all(c["status"] in TERMINAIS for c in calcs):
                break
            await asyncio.sleep(5)
    finally:
        await m.encerrar()
    sobra = supa.table("multicalculo_calculos").select("id, pedido_id, solicitante_company_id") \
        .in_("pedido_id", sorted(pedidos)).eq("status", "na_fila").execute().data or []
    cancelados = 0
    if sobra:
        from app.services.multicalculo.repositorio import RepositorioMulticalculo

        repo = RepositorioMulticalculo(supa)
        for pid in sorted({x["pedido_id"] for x in sobra}):
            sol = next(x["solicitante_company_id"] for x in sobra if x["pedido_id"] == pid)
            cancelados += repo.cancelar(company_id=sol, pedido_id=pid)
    return {"voltas": voltas, "grupos": grupos, "t_s": round(time.monotonic() - t0, 1),
            "sobra_na_fila_cancelada": cancelados}


def _t(valor: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00")) if valor else None
    except ValueError:
        return None


def medir_o_calculo(supa, cid: str, pedidos: set, dono: str) -> Dict[str, Any]:
    """A prova por SELECT: quem fechou cada cálculo (o `dono`), A3 (as opções no MESMO negócio), ofertas por opção,
    tempo por pedido, o estado do item. ⛔ Só contagens, estados, opções e hashes."""
    ids = sorted(pedidos) or ["00000000-0000-0000-0000-000000000000"]
    peds = supa.table("multicalculo_pedidos").select("id, company_id, servico, politica_de_sessao, renovacao_id, "
                                                     "criado_em, status").in_("id", ids).execute().data or []
    calcs = supa.table("multicalculo_calculos").select(
        "id, pedido_id, company_id, opcao, status, dono, account_id, tentativas, negocio_ref, versao, disponivel_em, "
        "disparado_em, primeira_oferta_em, fechado_em, erro, prioridade").in_("pedido_id", ids).execute().data or []
    cids = [c["id"] for c in calcs] or ["00000000-0000-0000-0000-000000000000"]
    ofertas = supa.table("multicalculo_ofertas").select("calculo_id, premio_total").in_("calculo_id", cids) \
        .execute().data or []
    eventos = supa.table("multicalculo_eventos").select("calculo_id, tipo").in_("calculo_id", cids).execute().data or []
    saida: Dict[str, Any] = {"pedidos": len(peds), "calculos": len(calcs),
                             "donos_dos_calculos": sorted({str(c.get("dono")) for c in calcs}),
                             "todos_deste_motor": bool(calcs) and all(c.get("dono") == dono for c in calcs),
                             "outro_dono": sum(1 for c in calcs if c.get("dono") not in (None, dono)),
                             "tentativas": sorted({int(c.get("tentativas") or 0) for c in calcs}),
                             "contas_usadas": sorted({_h(c.get("account_id")) for c in calcs if c.get("account_id")}),
                             "prioridades": sorted({c.get("prioridade") for c in calcs}),
                             "eventos_do_motor": len(eventos),
                             "tipos_de_evento": sorted({str(e.get("tipo")) for e in eventos}), "por_pedido": []}
    for p in peds:
        meus = [c for c in calcs if c["pedido_id"] == p["id"]]
        inicio = min((_t(c.get("disparado_em")) for c in meus if c.get("disparado_em")), default=None)
        fim = max((_t(c.get("fechado_em")) for c in meus if c.get("fechado_em")), default=None)
        item = (supa.table("renovacoes").select("estado, motivo").eq("company_id", cid)
                .eq("id", p["renovacao_id"]).execute().data or [{}])[0] if p.get("renovacao_id") else {}
        saida["por_pedido"].append({
            "pedido": _h(p["id"]), "servico": p.get("servico"), "politica": p.get("politica_de_sessao"),
            "status_do_pedido": p.get("status"),
            "opcoes": {c["opcao"]: {"status": c["status"],
                                    "ofertas": sum(1 for o in ofertas if o["calculo_id"] == c["id"]),
                                    "versao": c.get("versao"), "erro": (c.get("erro") or "")[:120] or None}
                       for c in meus},
            "negocios_distintos": len({c.get("negocio_ref") for c in meus if c.get("negocio_ref")}),
            "A3_mesmo_negocio_e_fechadas": bool(meus) and len({c.get("negocio_ref") for c in meus}) == 1
            and all(c["status"] == "fechado" for c in meus),
            "espera_no_futuro_na_gravacao": all(_t(c.get("disponivel_em")) and _t(p.get("criado_em"))
                                                and _t(c["disponivel_em"]) > _t(p["criado_em"]) + timedelta(hours=5)
                                                for c in meus),
            "tempo_s": round((fim - inicio).total_seconds(), 1) if inicio and fim else None,
            "item": {"estado": item.get("estado"), "motivo": item.get("motivo")}})
    return saida


def _contas(supa, cid: str) -> List[Tuple]:
    linhas = supa.table("portal_accounts").select("id, robo_estado, robo_dono, robo_batida_em, robo_ocupada_ate") \
        .eq("company_id", cid).eq("portal_key", "agger").execute().data or []
    return sorted((_h(x["id"]), x.get("robo_estado"), x.get("robo_dono"), x.get("robo_batida_em"),
                   x.get("robo_ocupada_ate")) for x in linhas)


def main(argv: Optional[List[str]] = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001
            pass
    args = _parser().parse_args(argv)
    if os.environ.get("AUTOBROKERS_CANARIO") != "1":
        print("RECUSADO: o canário exige AUTOBROKERS_CANARIO=1 no processo")
        return 2
    _carregar_env(Path(args.env))
    rel = asyncio.run(executar(args))
    texto = json.dumps(rel, ensure_ascii=False, indent=1, default=str)
    if args.saida:
        destino = Path(args.saida)
        if BACKEND.parent.resolve() in destino.resolve().parents:
            print("RECUSADO: a saída do canário não fica dentro do repositório")
            return 2
        destino.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
