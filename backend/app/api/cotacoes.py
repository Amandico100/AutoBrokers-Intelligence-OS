"""SPEC-132-B · B3 — a API da aba Cotações do aplicativo "Cotação Rápida" (o lugar onde o corretor revê e envia).

    GET  /api/cotacoes?company_id=&user_id=&escopo=minhas|todas&estado=calculando|pronta|sem_resposta
         + cabeçalho `x-busca` (nome, placa ou CPF/CNPJ — 🔴 NUNCA na query string: a query vai ao log de acesso)
    GET  /api/cotacoes/{id}?company_id=&user_id=            o detalhe: as opções, em qual Agger saiu, "Abrir no Agger"
    POST /api/cotacoes/{id}/apresentacao  {company_id, user_id}         → {url, token}
    POST /api/cotacoes/{id}/envio         {company_id, user_id, via?}   → {texto, texto_curto, link, wa_me_url?,
                                                                           sem_telefone}

Uma cotação É um `multicalculo_pedidos` com `servico='cotacao'` (o `id` da rota é o do PEDIDO) + os cálculos e as ofertas
dele + o Work Run `cotacao.chat` (fatia B1) que guarda a conversa, o resumo do cliente e o link da apresentação. Nenhuma
tabela nova (SPEC §3).

🔴 Chave interna (o proxy Next é quem fala com isto); `company_id` e `user_id` vêm da SESSÃO no proxy, nunca do navegador.
   TODA leitura filtra `company_id` (pedido, work run) ou `solicitante_company_id` (cálculo, oferta) no BANCO e de novo
   aqui (`_e_da_corretora`) — o backend é service role e a RLS sem policy não protege (CLAUDE.md §7, mutação 6).
⛔ NENHUMA mensagem sai daqui: o envio devolve um `wa.me` que o NAVEGADOR de quem clicou abre (D-132B-05). O telefone do
   cliente é o que o CORRETOR informou no pedido (decifrado NA HORA, em memória) e só existe dentro do `wa_me_url` da
   resposta: nunca vai a log, a evento, a linha do banco. Nome só o primeiro; documento só mascarado. Nenhum nome de
   corretora (§13.9). As peças puras de envio, busca e "Abrir no Agger" são as da aba Renovações (uma regra só).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from fastapi import APIRouter, Header, HTTPException, Request

from app.api import renovacoes as REN
from app.api.portal import _require_internal_key
from app.services.multicalculo import renovacao as R

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cotacoes", tags=["Cotações"])

SERVICO = "cotacao"
#: o Work Run da cotação pedida no chat (fatia B1 — `work_runs.workflow_key`)
WORKFLOW = "cotacao.chat"
ESCOPOS = ("minhas", "todas")
ESTADOS = ("calculando", "pronta", "sem_resposta")
ROTULO_DO_ESTADO = {"calculando": "Calculando", "pronta": "Pronta", "sem_resposta": "Sem resposta"}
CHAVES_DO_POST = frozenset({"company_id", "user_id", "via"})
CABECALHO_DA_BUSCA = REN.CABECALHO_DA_BUSCA
#: 💭 a lista mostra as cotações dos últimos 90 dias (a mais velha não é mais trabalho), as mais novas primeiro
DIAS_PARA_TRAS = 90
TETO_DA_LISTA = 300
STATUS_EM_CURSO = ("na_fila", "disparando", "calculando")
RUN_QUE_FALHOU = ("failed", "cancelled", "expired")
#: as opções da cotação na ordem da página e o nome que o corretor usa (D-132B-06: "Completa, Econômica e Completa+")
ORDEM_DAS_OPCOES = ("padrao", "economica", "completa_mais", "minima")
ROTULO_DA_OPCAO = {"padrao": "Completa", "economica": "Econômica", "completa_mais": "Completa+", "minima": "Mínima"}
ROTULO_DO_STATUS = REN.ROTULO_DO_STATUS_DO_CALCULO

PEDIDOS = "multicalculo_pedidos"
CALCULOS = "multicalculo_calculos"
OFERTAS = "multicalculo_ofertas"
_COLS_PEDIDO = "id, company_id, ramo, opcoes, status, criado_em, servico, solicitante_user_id, cpf_hmac"
_COLS_CALCULO = ("id, pedido_id, solicitante_company_id, opcao, status, negocio_ref, conta_regra, conta_fallback, "
                 "conta_motivo, quadro_pronto_em, fechado_em, criado_em")
_COLS_OFERTA = ("id, calculo_id, pedido_id, solicitante_company_id, seguradora, pacote, premio_total, franquia_valor, "
                "parcelamentos")
_COLS_RUN = ("id, company_id, workflow_key, status, input_payload, result_payload, conversation_id, requester_user_id, "
             "requested_at, finished_at")


def _db() -> Any:
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _e_da_corretora(linha: Mapping[str, Any], coluna: str, cid: str) -> bool:
    """A SEGUNDA trava (a primeira é o `.eq` no banco): a linha é desta corretora? (mutação 6 da SPEC)"""
    return str(linha.get(coluna) or "").lower() == cid


def _texto(v: Any) -> Optional[str]:
    return v.strip() if isinstance(v, str) and v.strip() else None


def rotulo_do_ramo(ramo: Any) -> str:
    from app.api.servicos_da_corretora import RAMOS_DA_TELA

    return dict(RAMOS_DA_TELA).get(str(ramo or ""), "Seguro")


# ---------------------------------------------------------------------------------------------------------------------
# O Work Run `cotacao.chat` (fatia B1) — lido DEFENSIVAMENTE: o que faltar, a tela não mostra (nunca inventa)
# ---------------------------------------------------------------------------------------------------------------------
def _payloads(run: Optional[Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    run = run or {}
    ent = run.get("input_payload") if isinstance(run.get("input_payload"), Mapping) else {}
    res = run.get("result_payload") if isinstance(run.get("result_payload"), Mapping) else {}
    return dict(ent), dict(res)


def pedido_do_run(run: Mapping[str, Any]) -> Optional[str]:
    ent, res = _payloads(run)
    for d in (res, ent):
        v = _texto(d.get("pedido_id"))
        if v and REN._UUID.match(v):
            return v.lower()
    return None


def _link_valido(v: Any) -> Optional[str]:
    t = _texto(v)
    return t if t and re.match(r"^https?://", t) and "/r/" in t else None


def do_run(run: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """O que o Work Run sabe desta cotação: o cliente (primeiro nome), o documento MASCARADO, o risco ("Onix 2022"), o
    link da apresentação e a mensagem pronta. ⛔ Um documento com mais de 2 dígitos não é mascarado: some."""
    ent, res = _payloads(run)

    def pegar(*chaves: str) -> Optional[str]:
        for d in (res, ent):
            for k in chaves:
                v = _texto(d.get(k))
                if v:
                    return v
        return None

    apresentacao = res.get("apresentacao") if isinstance(res.get("apresentacao"), Mapping) else {}
    url = _link_valido(res.get("url")) or _link_valido(res.get("link")) or _link_valido(apresentacao.get("url"))
    doc = pegar("documento_mascarado")
    msg = res.get("mensagem") if isinstance(res.get("mensagem"), Mapping) else None
    return {
        "cliente": R.primeiro_nome(pegar("cliente_nome_curto", "cliente_primeiro_nome", "cliente")),
        "documento": doc if doc and sum(ch.isdigit() for ch in doc) <= 2 else None,
        "risco": pegar("risco", "veiculo_resumo", "veiculo"),
        "placa": pegar("placa"),
        "url": url,
        "token": _texto(res.get("token")) or _texto(apresentacao.get("token")),
        "modelo": res.get("modelo") if isinstance(res.get("modelo"), Mapping) else (
            res.get("resumo") if isinstance(res.get("resumo"), Mapping) else None),
        "mensagem": dict(msg) if msg and _texto(msg.get("texto")) else None,
        "conversa": bool((run or {}).get("conversation_id")),
        "status": (run or {}).get("status"),
    }


# ---------------------------------------------------------------------------------------------------------------------
# O pedido cifrado — decifrado SÓ em memória, só no servidor, e só o que a tela precisa (nunca o telefone na tela)
# ---------------------------------------------------------------------------------------------------------------------
def _decifrar(cifrado: str) -> Dict[str, Any]:
    """`PedidoDeCalculo.para_dict()` do pedido (o MESMO cofre do motor, `portal_vault`). ⛔ Nunca logar o retorno."""
    from app.services import portal_vault

    dados = json.loads(portal_vault.decrypt(cifrado))
    return dados if isinstance(dados, dict) else {}


def resumo_do_pedido(dados: Mapping[str, Any], ramo: Any) -> Dict[str, Optional[str]]:
    """Primeiro nome, documento mascarado, o risco ("Onix 2022", "Placa ABC1D23", ou o ramo) e a placa (a busca)."""
    seg = dados.get("segurado") if isinstance(dados.get("segurado"), Mapping) else {}
    vei = dados.get("veiculo") if isinstance(dados.get("veiculo"), Mapping) else {}
    modelo = _texto(vei.get("modelo")) or _texto(vei.get("fabricante"))
    ano = vei.get("ano_modelo") or vei.get("ano_fabricacao")
    placa = _texto(vei.get("placa"))
    if modelo:
        risco = f"{modelo} {ano}".strip() if ano else modelo
    elif placa:
        risco = f"Placa {placa}"
    else:
        risco = rotulo_do_ramo(ramo)
    return {"cliente": R.primeiro_nome(seg.get("nome")), "documento": R.mascarar_documento(seg.get("cpf_cnpj")),
            "risco": risco, "placa": placa}


def telefone_do_pedido(dados: Mapping[str, Any]) -> Optional[str]:
    """O WhatsApp do cliente que o CORRETOR informou no pedido, pela regra ÚNICA do produto (`numero_de_whatsapp`, o
    CHECK do banco). Sem número válido → None (a tela oferece só o "Copiar"). ⛔ Quem chama nunca loga."""
    seg = dados.get("segurado") if isinstance(dados.get("segurado"), Mapping) else {}
    return REN.numero_de_whatsapp({"telefone": seg.get("telefone")})


def _cifrados(db: Any, cid: str, ids: Sequence[str]) -> Dict[str, str]:
    saida: Dict[str, str] = {}
    for lote in REN._em_lotes(sorted(set(ids))):
        linhas = list(getattr(db.table(PEDIDOS).select("id, company_id, pedido_cifrado").eq("company_id", cid)
                              .in_("id", lote).execute(), "data", None) or [])
        for p in linhas:
            if _e_da_corretora(p, "company_id", cid) and p.get("pedido_cifrado"):
                saida[str(p["id"]).lower()] = str(p["pedido_cifrado"])
    return saida


def _dados_do_pedido(db: Any, cid: str, pid: str) -> Dict[str, Any]:
    cifrado = _cifrados(db, cid, [pid]).get(pid)
    if not cifrado:
        return {}
    try:
        return _decifrar(cifrado)
    except Exception as exc:  # noqa: BLE001 — ⛔ só o TIPO (a mensagem de uma exceção pode carregar o dado)
        logger.warning("[COTACOES] pedido ilegível: %s", type(exc).__name__)
        return {}


# ---------------------------------------------------------------------------------------------------------------------
# As leituras (sempre da corretora da sessão)
# ---------------------------------------------------------------------------------------------------------------------
def ler_pedidos(db: Any, cid: str, *, desde: str) -> Tuple[List[Dict[str, Any]], bool]:
    from app.leitura_completa import ler_paginado

    linhas, truncou = ler_paginado(
        lambda: db.table(PEDIDOS).select(_COLS_PEDIDO).eq("company_id", cid).eq("servico", SERVICO)
        .gte("criado_em", desde),
        chave_unica="id", rotulo="cotacoes.pedidos")
    return [p for p in linhas if _e_da_corretora(p, "company_id", cid) and p.get("servico") == SERVICO], truncou


def pedido_da_corretora(db: Any, cid: str, pid: str) -> Dict[str, Any]:
    linhas = list(getattr(db.table(PEDIDOS).select(_COLS_PEDIDO).eq("id", pid).eq("company_id", cid)
                          .eq("servico", SERVICO).limit(1).execute(), "data", None) or [])
    p = next((x for x in linhas if _e_da_corretora(x, "company_id", cid) and x.get("servico") == SERVICO), None)
    if p is None:
        raise HTTPException(status_code=404, detail="Esta cotação não existe nesta corretora.")
    return p


def calculos_e_ofertas(db: Any, cid: str, pids: Iterable[str]) -> Tuple[Dict[str, List[Dict[str, Any]]],
                                                                         Dict[str, List[Dict[str, Any]]]]:
    """Os cálculos e as ofertas, POR PEDIDO, filtrados pelo SOLICITANTE no banco e de novo aqui (paginados: o
    PostgREST corta em 1000 linhas)."""
    from app.leitura_completa import ler_paginado

    ids = sorted({str(p).lower() for p in pids if p})
    calcs: Dict[str, List[Dict[str, Any]]] = {}
    ofs: Dict[str, List[Dict[str, Any]]] = {}
    for lote in REN._em_lotes(ids):
        linhas, _ = ler_paginado(
            lambda lote=lote: db.table(CALCULOS).select(_COLS_CALCULO).in_("pedido_id", lote)
            .eq("solicitante_company_id", cid), chave_unica="id", rotulo="cotacoes.calculos")
        for c in linhas:
            if _e_da_corretora(c, "solicitante_company_id", cid):
                calcs.setdefault(str(c.get("pedido_id")).lower(), []).append(c)
        linhas, _ = ler_paginado(
            lambda lote=lote: db.table(OFERTAS).select(_COLS_OFERTA).in_("pedido_id", lote)
            .eq("solicitante_company_id", cid), chave_unica="id", rotulo="cotacoes.ofertas")
        for o in linhas:
            if _e_da_corretora(o, "solicitante_company_id", cid):
                ofs.setdefault(str(o.get("pedido_id")).lower(), []).append(o)
    return calcs, ofs


def runs_por_pedido(db: Any, cid: str, *, desde: Optional[str] = None,
                    pedido_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """O Work Run `cotacao.chat` MAIS RECENTE de cada pedido desta corretora."""
    from app.leitura_completa import ler_paginado

    def consulta():
        q = db.table("work_runs").select(_COLS_RUN).eq("company_id", cid).eq("workflow_key", WORKFLOW)
        return q.gte("requested_at", desde) if desde else q

    try:
        linhas, _ = ler_paginado(consulta, chave_unica="id", rotulo="cotacoes.runs")
    except Exception as exc:  # noqa: BLE001 — sem o run, a cotação aparece com o que o pedido sabe
        logger.warning("[COTACOES] work runs ilegíveis: %s", type(exc).__name__)
        return {}
    saida: Dict[str, Dict[str, Any]] = {}
    for run in sorted((r for r in linhas if _e_da_corretora(r, "company_id", cid)),
                      key=lambda r: str(r.get("requested_at") or "")):
        pid = pedido_do_run(run)
        if pid and (pedido_id is None or pid == pedido_id):
            saida[pid] = run      # o mais recente vence (ordem crescente)
    return saida


# ---------------------------------------------------------------------------------------------------------------------
# As peças puras (o teste as chama direto)
# ---------------------------------------------------------------------------------------------------------------------
def _config(db: Any, cid: str) -> Optional[Mapping[str, Any]]:
    try:
        from app.services.multicalculo import config as CFG

        return CFG.carregar(cid, db=db, servico=SERVICO)
    except Exception as exc:  # noqa: BLE001 — sem a config, o padrão do produto (só para reconhecer assinatura)
        logger.info("[COTACOES] config ilegível: %s", type(exc).__name__)
        return None


def ofertas_com_preco(ofertas: Sequence[Mapping[str, Any]], calculos: Sequence[Mapping[str, Any]],
                      cfg: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
    """As ofertas com prêmio, dos cálculos PRINCIPAIS (o recálculo `ajuste` fica de fora), sem os produtos de
    ASSINATURA (o `premio_total` deles não é anual — P-129B-06)."""
    from app.services.multicalculo import config as CFG

    cfg = cfg or CFG.mesclar(None, SERVICO)
    principais = {str(c.get("id")) for c in calculos if c.get("opcao") != "ajuste"}
    return [o for o in ofertas
            if str(o.get("calculo_id")) in principais and REN._num(o.get("premio_total"))
            and not CFG.e_produto_de_assinatura(o.get("seguradora"), o.get("pacote"), cfg)]


def estado_da_cotacao(pedido: Mapping[str, Any], calculos: Sequence[Mapping[str, Any]],
                      com_preco: Sequence[Mapping[str, Any]], run: Optional[Mapping[str, Any]] = None) -> str:
    """Calculando · Pronta · Sem resposta, só do que o banco diz. Pronta = já há preço E (o cálculo terminou, o quadro
    fechou ou o Work Run já respondeu na conversa). Sem resposta = tudo terminou e nenhuma seguradora deu preço."""
    principais = [c for c in calculos if c.get("opcao") != "ajuste"]
    em_curso = any(c.get("status") in STATUS_EM_CURSO for c in principais)
    info = do_run(run) if run else {}
    run_falhou = (run or {}).get("status") in RUN_QUE_FALHOU
    if com_preco and (not em_curso or any(c.get("quadro_pronto_em") for c in principais)
                      or (run or {}).get("status") == "completed" or info.get("url")):
        return "pronta"
    if em_curso and not run_falhou:
        return "calculando"
    if not principais and pedido.get("status") == "aberto" and not run_falhou:
        return "calculando"
    return "pronta" if com_preco else "sem_resposta"


def melhor_oferta(com_preco: Sequence[Mapping[str, Any]],
                  calculos: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """A de MENOR prêmio: seguradora, à vista, a parcela (a regra da comparação, `parcelas_de`) e a franquia."""
    if not com_preco:
        return None
    from app.services.multicalculo.comparacao import parcelas_de

    o = min(com_preco, key=lambda x: float(x["premio_total"]))
    opcao = next((c.get("opcao") for c in calculos if str(c.get("id")) == str(o.get("calculo_id"))), None)
    return {"seguradora": _texto(o.get("seguradora")), "a_vista": round(float(o["premio_total"]), 2),
            "parcela": parcelas_de(o), "franquia": REN._num(o.get("franquia_valor")),
            "opcao": ROTULO_DA_OPCAO.get(str(opcao or ""), None)}


def onde_calculou(calculos: Sequence[Mapping[str, Any]]) -> Dict[str, Optional[str]]:
    """Em qual Agger a cotação saiu (lido do cálculo, que guarda a decisão do `qual_agger`). A frase do motivo é a que
    o produto gravou (`conta_motivo`, sem PII)."""
    principais = [c for c in calculos if c.get("opcao") != "ajuste"]
    if not principais:
        return {"onde": None, "frase": None}
    if any(c.get("conta_regra") == "cotacao_da_corretora" or c.get("conta_fallback") for c in principais):
        motivo = next((_texto(c.get("conta_motivo")) for c in principais if _texto(c.get("conta_motivo"))), None)
        return {"onde": "corretora", "frase": motivo or "Calculada no Agger da corretora."}
    if any(c.get("conta_regra") == "cotacao_da_pessoa" for c in principais):
        return {"onde": "pessoa", "frase": "Calculada no Agger de quem pediu."}
    return {"onde": None, "frase": None}


def opcoes_da_cotacao(calculos: Sequence[Mapping[str, Any]], com_preco: Sequence[Mapping[str, Any]],
                      *, ramo: Any) -> List[Dict[str, Any]]:
    """Cada opção calculada (Completa, Econômica, Completa+): o menor preço, a parcela, a franquia, quantas seguradoras
    deram preço, o estado em palavras e o link direto ao Agger."""
    from app.services.multicalculo.comparacao import parcelas_de

    por_opcao: Dict[str, List[Mapping[str, Any]]] = {}
    for c in calculos:
        o = str(c.get("opcao") or "")
        if o and o != "ajuste":
            por_opcao.setdefault(o, []).append(c)
    ordem = [o for o in ORDEM_DAS_OPCOES if o in por_opcao] + sorted(o for o in por_opcao if o not in ORDEM_DAS_OPCOES)
    saida = []
    for opcao in ordem:
        calc = sorted(por_opcao[opcao], key=lambda c: str(c.get("criado_em") or ""))[-1]
        cid = str(calc.get("id") or "")
        validas = [o for o in com_preco if str(o.get("calculo_id") or "") == cid]
        menor = min(validas, key=lambda o: float(o["premio_total"])) if validas else None
        status = str(calc.get("status") or "")
        saida.append({
            "opcao": opcao, "rotulo": ROTULO_DA_OPCAO.get(opcao, opcao.replace("_", " ").capitalize()),
            "status": status, "status_rotulo": ROTULO_DO_STATUS.get(status, status.replace("_", " ")),
            "menor_preco": round(float(menor["premio_total"]), 2) if menor else None,
            "seguradora_do_menor": _texto(menor.get("seguradora")) if menor else None,
            "parcela_do_menor": parcelas_de(menor) if menor else None,
            "franquia_do_menor": REN._num(menor.get("franquia_valor")) if menor else None,
            "seguradoras": len({str(o.get("seguradora") or "").strip().lower() for o in validas}),
            "agger_url": REN.link_do_agger(ramo, calc.get("negocio_ref")),
        })
    return saida


def item_da_tela(pedido: Mapping[str, Any], *, calculos: Sequence[Mapping[str, Any]] = (),
                 ofertas: Sequence[Mapping[str, Any]] = (), run: Optional[Mapping[str, Any]] = None,
                 resumo: Optional[Mapping[str, Any]] = None, nomes: Optional[Mapping[str, str]] = None,
                 cfg: Optional[Mapping[str, Any]] = None, uid: Optional[str] = None) -> Dict[str, Any]:
    """Um pedido de cotação na forma da tela. O cliente vem do Work Run; sem ele, do resumo do pedido (já curto)."""
    nomes = nomes or {}
    info = do_run(run)
    resumo = resumo or {}
    com_preco = ofertas_com_preco(ofertas, calculos, cfg)
    estado = estado_da_cotacao(pedido, calculos, com_preco, run)
    quem = str(pedido.get("solicitante_user_id") or "").lower() or None
    return {
        "id": str(pedido.get("id")).lower(),
        "cliente": info.get("cliente") or resumo.get("cliente"),
        "documento": info.get("documento") or resumo.get("documento"),
        "risco": info.get("risco") or resumo.get("risco") or rotulo_do_ramo(pedido.get("ramo")),
        "placa": info.get("placa") or resumo.get("placa"),
        "ramo": pedido.get("ramo"),
        "ramo_rotulo": rotulo_do_ramo(pedido.get("ramo")),
        "quando": pedido.get("criado_em"),
        "quem_pediu": ({"user_id": quem, "nome": nomes.get(quem) or "Alguém da equipe", "sou_eu": quem == uid}
                       if quem else None),
        "estado": estado,
        "estado_rotulo": ROTULO_DO_ESTADO[estado],
        "seguradoras": len({str(o.get("seguradora") or "").strip().lower() for o in com_preco}),
        "melhor": melhor_oferta(com_preco, calculos),
        "conta": onde_calculou(calculos),
        "pode_enviar": estado == "pronta",
        "tem_apresentacao": bool(info.get("url")),
        "da_conversa": bool(info.get("conversa")),
    }


def proximo_passo(item: Mapping[str, Any]) -> str:
    estado = item.get("estado")
    if estado == "calculando":
        return "Calculando nas seguradoras. Costuma ficar pronta em 1 a 2 minutos."
    if estado == "pronta":
        return "Pronta: confira as opções e envie a apresentação ao cliente pelo seu WhatsApp."
    return "Nenhuma seguradora respondeu com preço. Confira no Agger ou peça a cotação de novo no chat."


def _casa_busca(item: Mapping[str, Any], pedido: Mapping[str, Any], q: str) -> bool:
    texto = REN._sem_acento(q.strip())
    if not texto:
        return True
    digitos = re.sub(r"\D", "", q)
    if len(digitos) in (11, 14):   # CPF/CNPJ inteiro: pelo HMAC (o banco nunca teve o documento em claro)
        try:
            return R.hmac_do_documento(digitos) == pedido.get("cpf_hmac")
        except Exception:  # noqa: BLE001 — sem a chave do HMAC, a busca por documento não casa nada (fail-closed)
            return False
    alvo = REN._sem_acento(" ".join(str(item.get(k) or "") for k in ("cliente", "risco", "placa")))
    return texto in alvo or texto.replace(" ", "") in alvo.replace(" ", "")


def montar_lista(db: Any, cid: str, uid: str, *, escopo: str = "minhas", estado: Optional[str] = None,
                 q: Optional[str] = None) -> Dict[str, Any]:
    desde = (_agora() - timedelta(days=DIAS_PARA_TRAS)).isoformat()
    pedidos, truncou = ler_pedidos(db, cid, desde=desde)
    tem_alguma = bool(pedidos)
    if escopo == "minhas":
        pedidos = [p for p in pedidos if str(p.get("solicitante_user_id") or "").lower() == uid]
    pedidos = sorted(pedidos, key=lambda p: str(p.get("criado_em") or ""), reverse=True)[:TETO_DA_LISTA]
    ids = [str(p["id"]).lower() for p in pedidos]
    calcs, ofs = calculos_e_ofertas(db, cid, ids)
    runs = runs_por_pedido(db, cid, desde=desde)
    # o que o Work Run não diz (o cliente ou a placa) sai do pedido, decifrado em memória — só o resumo curto fica
    sem_cliente = [i for i in ids if not (do_run(runs.get(i)).get("cliente") and do_run(runs.get(i)).get("placa"))]
    resumos: Dict[str, Dict[str, Any]] = {}
    if sem_cliente:
        for pid, cifrado in _cifrados(db, cid, sem_cliente).items():
            try:
                resumos[pid] = resumo_do_pedido(_decifrar(cifrado), next(
                    (p.get("ramo") for p in pedidos if str(p["id"]).lower() == pid), None))
            except Exception as exc:  # noqa: BLE001 — ⛔ só o tipo
                logger.warning("[COTACOES] resumo do pedido ilegível: %s", type(exc).__name__)
    nomes = REN._nomes_da_equipe(db, cid)
    cfg = _config(db, cid)
    estados = {e.strip() for e in (estado or "").split(",") if e.strip()}
    itens, contagens = [], {e: 0 for e in ESTADOS}
    for p in pedidos:
        pid = str(p["id"]).lower()
        item = item_da_tela(p, calculos=calcs.get(pid, []), ofertas=ofs.get(pid, []), run=runs.get(pid),
                            resumo=resumos.get(pid), nomes=nomes, cfg=cfg, uid=uid)
        if q and not _casa_busca(item, p, q):
            continue
        contagens[item["estado"]] += 1
        if estados and item["estado"] not in estados:
            continue
        itens.append(item)
    return {"itens": itens, "total": len(itens), "contagens": contagens, "escopo": escopo, "eu": uid,
            "tem_alguma": tem_alguma, "truncou": truncou, "dias": DIAS_PARA_TRAS}


def montar_detalhe(db: Any, cid: str, uid: str, pid: str) -> Dict[str, Any]:
    pedido = pedido_da_corretora(db, cid, pid)
    calcs, ofs = calculos_e_ofertas(db, cid, [pid])
    run = runs_por_pedido(db, cid, pedido_id=pid).get(pid)
    resumo = None
    if not do_run(run).get("cliente"):
        dados = _dados_do_pedido(db, cid, pid)
        resumo = resumo_do_pedido(dados, pedido.get("ramo")) if dados else None
    cfg = _config(db, cid)
    item = item_da_tela(pedido, calculos=calcs.get(pid, []), ofertas=ofs.get(pid, []), run=run, resumo=resumo,
                        nomes=REN._nomes_da_equipe(db, cid), cfg=cfg, uid=uid)
    com_preco = ofertas_com_preco(ofs.get(pid, []), calcs.get(pid, []), cfg)
    opcoes = opcoes_da_cotacao(calcs.get(pid, []), com_preco, ramo=pedido.get("ramo"))
    agger = next((o["agger_url"] for o in opcoes if o.get("agger_url")), None)
    return {**item, "opcoes": opcoes, "agger_url": agger, "proximo_passo": proximo_passo(item), "eu": uid}


# ---------------------------------------------------------------------------------------------------------------------
# As bordas: a apresentação e a mensagem (fatia B2, pelo CONTRATO da SPEC §5)
# ---------------------------------------------------------------------------------------------------------------------
async def _chamar(fn: Any, *args: Any, **kwargs: Any) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    r = await asyncio.to_thread(fn, *args, **kwargs)
    return await r if inspect.isawaitable(r) else r


def _erro_da_publicacao(exc: Exception) -> Optional[HTTPException]:
    from app.services.multicalculo import proposta as P

    if isinstance(exc, getattr(P, "PropostaImpossivel", ())):
        return HTTPException(status_code=409, detail="Ainda não dá para montar a apresentação desta cotação: nenhuma "
                                                     "opção tem preço. Confira no Agger.")
    if isinstance(exc, getattr(P, "LinkSemEndereco", ())):
        return HTTPException(status_code=503, detail="O endereço público do painel não está configurado: o link "
                                                     "da apresentação não teria para onde apontar.")
    return None


def runs_do_pedido(db: Any, cid: str, pid: str) -> List[Dict[str, Any]]:
    """TODOS os Work Runs `cotacao.chat` deste pedido desta corretora, do mais velho ao mais novo (o disparo e cada
    recálculo). Filtro `company_id` no banco e de novo aqui (CLAUDE.md §7)."""
    try:
        linhas = list(getattr(db.table("work_runs").select(_COLS_RUN).eq("company_id", cid).eq("workflow_key", WORKFLOW)
                              .eq("source_id", pid).execute(), "data", None) or [])
    except Exception as exc:  # noqa: BLE001 — sem os runs, a apresentação sai do pedido (sem apólice, sem recálculo)
        logger.warning("[COTACOES] runs do pedido ilegíveis: %s", type(exc).__name__)
        return []
    return sorted((r for r in linhas if _e_da_corretora(r, "company_id", cid) and pedido_do_run(r) == pid),
                  key=lambda r: str(r.get("requested_at") or ""))


def vista_da_apresentacao(pedido: Mapping[str, Any], runs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """🔴 Conserto RT B-3 + juiz P6: o que a apresentação deste pedido É — a MESMA página que a conversa entregou por
    último: quem PEDIU a cotação (`solicitante_user_id`, nunca quem clicou), a apólice lida, o primeiro nome do cliente e
    o recálculo da última resposta ENTREGUE. `publicar_cotacao` confere se quem pediu ainda é membro ativo (senão, a
    página vai para a corretora) e só reaproveita o link se a página seria idêntica E o link ainda vale."""
    entregues = [r for r in runs if (_payloads(r)[1].get("situacao") == "entregue")]
    base = entregues[-1] if entregues else (runs[-1] if runs else None)
    ent, _res = _payloads(base)
    apolice = ent.get("apolice_atual") if isinstance(ent.get("apolice_atual"), Mapping) else None
    return {"pessoa_user_id": _texto(pedido.get("solicitante_user_id")),
            "apolice_atual": dict(apolice) if apolice else None,
            "primeiro_nome": _texto(ent.get("cliente_nome_curto")),
            "ajuste_calculo_id": _texto(ent.get("ajuste_calculo_id")),
            "run": base}


async def publicar(db: Any, cid: str, pid: str, vista: Mapping[str, Any]) -> Dict[str, Any]:
    """`proposta.publicar_cotacao(company_id, pedido_id, *, pessoa_user_id, apolice_atual=None, db=None,
    primeiro_nome=None, ajuste_calculo_id=None) -> {token, url, artifact_id, resumo, modelo}` (contrato B2). Importada na
    hora: sem ela, a tela diz que a apresentação ainda não existe."""
    from app.services.multicalculo import proposta as P

    fn = getattr(P, "publicar_cotacao", None)
    if fn is None:
        raise HTTPException(status_code=503, detail="A apresentação da cotação ainda não está disponível. "
                                                    "Use o link que veio na conversa.")
    extra = {k: vista[k] for k in ("apolice_atual", "primeiro_nome", "ajuste_calculo_id") if vista.get(k)}
    try:
        r = await _chamar(fn, cid, pid, pessoa_user_id=vista.get("pessoa_user_id"), db=db, **extra)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        http = _erro_da_publicacao(exc)
        if http is None:
            logger.error("[COTACOES] apresentação falhou: %s", type(exc).__name__)
            raise HTTPException(status_code=502, detail="Não consegui preparar a apresentação agora. Tente de novo.")
        raise http
    if not isinstance(r, Mapping) or not _link_valido(r.get("url")):
        raise HTTPException(status_code=502, detail="Não consegui preparar a apresentação agora. Tente de novo.")
    return dict(r)


async def apresentacao(db: Any, cid: str, pid: str, pedido: Mapping[str, Any]) -> Dict[str, Any]:
    """🔴 Conserto RT B-3: SEMPRE pela `publicar_cotacao` (B2) — nunca o link guardado no run sem conferir. Ela devolve o
    MESMO link quando a página seria idêntica e o link ainda vale (nada é gravado); quem pediu saiu da corretora, o link
    venceu ou o recálculo mudou o preço → versão e link NOVOS. A mensagem pronta do run só vale se é deste link."""
    runs = await asyncio.to_thread(runs_do_pedido, db, cid, pid)
    vista = vista_da_apresentacao(pedido, runs)
    r = await publicar(db, cid, pid, vista)
    modelo = r.get("modelo") if isinstance(r.get("modelo"), Mapping) else r.get("resumo")
    pronta = do_run(vista["run"]).get("mensagem")
    return {"url": r["url"], "token": r.get("token"), "modelo": modelo if isinstance(modelo, Mapping) else None,
            "mensagem": pronta if pronta and r["url"] in str(pronta.get("texto") or "") else None,
            "reaproveitado": bool(r.get("reaproveitado"))}


async def mensagem(db: Any, cid: str, pid: str, ap: Dict[str, Any]) -> Dict[str, Any]:
    """A mensagem para o cliente: a que o Work Run já montou para ESTE link; senão `mensagem_de_cotacao(modelo, link)`
    (B2), com o modelo da página que acabou de ser conferida. ⛔ Nunca recebe o telefone."""
    pronta = ap.get("mensagem")
    if pronta and _texto(pronta.get("texto")) and ap["url"] in str(pronta.get("texto")):
        return {"texto": str(pronta["texto"]), "texto_curto": _texto(pronta.get("texto_curto")), "link": ap["url"]}
    from app.services.multicalculo import mensagem as MSG

    fn = getattr(MSG, "mensagem_de_cotacao", None)
    if fn is None:
        raise HTTPException(status_code=503, detail="A mensagem da cotação ainda não está disponível. Copie o link "
                                                    "da apresentação.")
    try:
        r = await _chamar(fn, dict(ap.get("modelo") or {}), ap["url"])
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("[COTACOES] mensagem impossível: %s", type(exc).__name__)
        raise HTTPException(status_code=409, detail="Não consegui montar a mensagem: a cotação não tem opção com "
                                                    "preço.")
    if not isinstance(r, Mapping) or not _texto(r.get("texto")):
        raise HTTPException(status_code=502, detail="Não consegui montar a mensagem agora. Tente de novo.")
    return {"texto": str(r["texto"]), "texto_curto": _texto(r.get("texto_curto")), "link": ap["url"]}


async def _corpo(request: Request) -> Dict[str, Any]:
    try:
        corpo = await request.json()
    except Exception:  # noqa: BLE001
        corpo = {}
    if not isinstance(corpo, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    estranhas = set(corpo) - CHAVES_DO_POST
    if estranhas:
        raise HTTPException(status_code=400, detail="campos que esta ação não recebe: " + ", ".join(sorted(estranhas)))
    return corpo


async def _pronta(db: Any, cid: str, uid: str, pid: str) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """O pedido (desta corretora) e o run — só se a cotação está PRONTA (há preço para mostrar)."""
    pedido = await asyncio.to_thread(pedido_da_corretora, db, cid, pid)
    calcs, ofs = await asyncio.to_thread(calculos_e_ofertas, db, cid, [pid])
    run = (await asyncio.to_thread(runs_por_pedido, db, cid, pedido_id=pid)).get(pid)
    cfg = await asyncio.to_thread(_config, db, cid)
    com_preco = ofertas_com_preco(ofs.get(pid, []), calcs.get(pid, []), cfg)
    if estado_da_cotacao(pedido, calcs.get(pid, []), com_preco, run) != "pronta":
        raise HTTPException(status_code=409, detail="Esta cotação ainda não está pronta: nenhuma seguradora "
                                                    "respondeu com preço.")
    return pedido, run


# ---------------------------------------------------------------------------------------------------------------------
# As rotas
# ---------------------------------------------------------------------------------------------------------------------
@router.get("")
async def listar_cotacoes(
    company_id: str,
    user_id: str,
    escopo: str = "minhas",
    estado: Optional[str] = None,
    x_busca: Optional[str] = Header(default=None, alias=CABECALHO_DA_BUSCA),
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """🔴 A busca é SÓ o cabeçalho `x-busca`; um `?q=` na query não é lido (a query vai ao log de acesso)."""
    _require_internal_key(x_key)
    cid, uid = REN._uuid(company_id, "company_id"), REN._uuid(user_id, "user_id")
    if escopo not in ESCOPOS:
        raise HTTPException(status_code=400, detail="escopo é minhas ou todas")
    if estado and not {e.strip() for e in estado.split(",") if e.strip()} <= set(ESTADOS):
        raise HTTPException(status_code=400, detail="estado é calculando, pronta ou sem_resposta")
    try:
        return await asyncio.to_thread(montar_lista, _db(), cid, uid, escopo=escopo, estado=estado,
                                       q=REN.busca_do_cabecalho(x_busca))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[COTACOES] lista falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Não consegui carregar as cotações agora.")


@router.get("/{pedido_id}")
async def detalhe_da_cotacao(
    pedido_id: str,
    company_id: str,
    user_id: str,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    cid, uid = REN._uuid(company_id, "company_id"), REN._uuid(user_id, "user_id")
    pid = REN._uuid(pedido_id, "pedido_id")
    try:
        return await asyncio.to_thread(montar_detalhe, _db(), cid, uid, pid)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[COTACOES] detalhe falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Não consegui abrir esta cotação agora.")


@router.post("/{pedido_id}/apresentacao")
async def apresentar_cotacao(
    pedido_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    corpo = await _corpo(request)
    cid, uid = REN._uuid(corpo.get("company_id"), "company_id"), REN._uuid(corpo.get("user_id"), "user_id")
    pid = REN._uuid(pedido_id, "pedido_id")
    db = _db()
    pedido, _run = await _pronta(db, cid, uid, pid)
    ap = await apresentacao(db, cid, pid, pedido)
    return {"url": ap["url"], "token": ap.get("token")}


@router.post("/{pedido_id}/envio")
async def enviar_cotacao(
    pedido_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """A mensagem pronta e — por WhatsApp — o `wa.me` do cliente. Quem ENVIA é a pessoa, no aparelho dela.
    `via=copiar` não lê telefone nenhum. ⛔ Nada é gravado: a cotação não tem máquina de estado de envio."""
    _require_internal_key(x_key)
    corpo = await _corpo(request)
    cid, uid = REN._uuid(corpo.get("company_id"), "company_id"), REN._uuid(corpo.get("user_id"), "user_id")
    pid = REN._uuid(pedido_id, "pedido_id")
    via = str(corpo.get("via") or "whatsapp")
    if via not in REN.VIAS_DO_ENVIO:
        raise HTTPException(status_code=400, detail="via é whatsapp ou copiar")
    db = _db()
    pedido, _run = await _pronta(db, cid, uid, pid)
    ap = await apresentacao(db, cid, pid, pedido)
    msg = await mensagem(db, cid, pid, ap)
    resposta: Dict[str, Any] = REN.textos_do_envio(msg)
    if via == "copiar":
        return {**resposta, "sem_telefone": None}
    dados = await asyncio.to_thread(_dados_do_pedido, db, cid, pid)
    numero = telefone_do_pedido(dados) if dados else None
    if not numero:
        # o corretor não informou um celular válido: nada foi aberto — ele copia a mensagem
        return {**resposta, "sem_telefone": True}
    return {**resposta, "wa_me_url": REN.url_do_wa_me(numero, resposta["texto_curto"]), "sem_telefone": False}
