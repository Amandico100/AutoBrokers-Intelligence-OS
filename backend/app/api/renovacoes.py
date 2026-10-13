"""SPEC-131-B · G2 — a API da aba Renovações (o lugar onde o comercial confere e envia).

    GET  /api/renovacoes?company_id=&user_id=&escopo=minhas|todas&estado=&ramo=&de=&ate=&seguradora=&q=
    GET  /api/renovacoes/{id}?company_id=&user_id=                o detalhe + a linha do tempo + "Abrir no Agger"
    POST /api/renovacoes/{id}/apresentacao   {company_id, user_id}          → {token, url} · estado `apresentada`
    POST /api/renovacoes/{id}/envio          {company_id, user_id, via?}    → {wa_me_url, texto} | {texto, sem_telefone}

🔴 Chave interna (o proxy Next é quem fala com isto); `company_id` e `user_id` vêm da SESSÃO no proxy, nunca do
   navegador. TODA leitura passa pelo repositório da 131-A (`RepositorioDeRenovacoes`, filtro `company_id` + a segunda
   trava) e as leituras do multicálculo levam `solicitante_company_id` (CLAUDE.md §7 — o backend é service role).
🔴 O estado só muda pela MÁQUINA (`RepositorioDeRenovacoes.transicionar`) e só por estas duas ações: publicar a
   apresentação (`calculada → apresentada`) e abrir o envio (`apresentada → enviada`). Nenhuma rota recebe um estado
   ou uma coluna de destino — arrastar um card não existe (mutação 4 da SPEC; o corpo com chave desconhecida é 400).
⛔ NENHUMA mensagem sai daqui: o envio devolve um `wa.me` que o NAVEGADOR de quem clicou abre (o WhatsApp do aparelho
   dele). O telefone do cliente é lido NA HORA na InfoCap da corretora (`/documento` → `codcli` → `/cliente`, sem
   cache) e só existe dentro do `wa_me_url` da resposta: nunca vai a log, a evento, a linha do banco (mutação 5).
⛔ Nome do cliente só o curto; documento só mascarado (o que a 131-A já grava). Nenhum nome de corretora (§13.9).
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.portal import _require_internal_key
from app.services.multicalculo import renovacao as R

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/renovacoes", tags=["Renovações"])

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: o que o corpo de um POST pode trazer — qualquer outra chave (um `estado`, uma `coluna`) é recusada: a tela não move
#: card nenhum, ela só pede as duas ações que a máquina conhece
CHAVES_DO_POST = frozenset({"company_id", "user_id", "via"})
VIAS_DO_ENVIO = ("whatsapp", "copiar")
ESCOPOS = ("minhas", "todas")

#: B1 do BLOCO 0 (não medido nos aparelhos): o texto que vai DENTRO do link ≤ 500 caracteres; a mensagem inteira vai
#: no "Copiar a mensagem", que fica SEMPRE ao lado
LIMITE_DO_TEXTO_NO_LINK = 500
#: a lista padrão: o que vence de 30 dias atrás em diante (a renovação vencida há mais tempo não é mais trabalho)
DIAS_PARA_TRAS_PADRAO = 30
#: os estados que a tela mostra — `substituida` é a linha velha de um endosso (a nova está na lista)
ESTADOS_VISIVEIS: Tuple[str, ...] = tuple(e for e in R.ESTADOS_LIGADOS + R.ESTADOS_RESERVADOS if e != "substituida")
#: o que se pode apresentar/enviar (a renovação já calculada)
ESTADOS_ENVIAVEIS: Tuple[str, ...] = ("calculada", "apresentada", "enviada")

# ---------------------------------------------------------------------------------------------------------------------
# O vocabulário da tela (a voz de quem trabalha, não a do banco)
# ---------------------------------------------------------------------------------------------------------------------
#: a COLUNA do quadro de cada estado (SPEC §4 · laudo de design §5). As quatro últimas a tela esconde até alguém chegar
#: lá; `substituida` não aparece. A coluna é DERIVADA do estado — nunca o contrário (sem arrastar).
COLUNA_DO_ESTADO: Dict[str, str] = {
    "listada": "vai_calcular", "pronta": "vai_calcular", "pendente": "vai_calcular", "calculando": "vai_calcular",
    "aguardando_agger": "vai_calcular", "falhou": "vai_calcular",
    "calculada": "calculada", "apresentada": "calculada",
    "enviada": "enviada", "vista": "enviada",
    "em_negociacao": "em_negociacao", "recalculo": "em_negociacao",
    "aceita": "fechada", "emissao_pendente": "fechada",
    "emitida": "emitida", "registrada": "emitida",
    "recusada": "perdida", "perdida": "perdida",
}
ROTULO_DO_ESTADO: Dict[str, str] = {
    "listada": "Na lista da madrugada", "pronta": "Vai calcular", "pendente": "Pendente",
    "calculando": "Calculando", "aguardando_agger": "Esperando o Agger", "falhou": "Não calculou",
    "calculada": "Calculada", "apresentada": "Apresentação pronta", "enviada": "Enviada", "vista": "Vista pelo cliente",
    "em_negociacao": "Em negociação", "recalculo": "Recalculando", "aceita": "Fechada", "emissao_pendente": "Emitindo",
    "emitida": "Emitida", "registrada": "Registrada", "recusada": "Recusada", "perdida": "Perdida",
    "substituida": "Substituída",
}
#: as opções da renovação na ordem da página (a "Sua renovação" em 1º — nunca "a melhor das N")
ORDEM_DAS_OPCOES: Tuple[str, ...] = ("anterior", "franquia_reduzida", "completa_mais", "padrao")
ROTULO_DA_OPCAO: Dict[str, str] = {"anterior": "Sua renovação", "franquia_reduzida": "Franquia menor",
                                   "completa_mais": "Mais completa", "padrao": "Cálculo padrão"}
ROTULO_DO_STATUS_DO_CALCULO: Dict[str, str] = {
    "na_fila": "na fila", "disparando": "começando", "calculando": "calculando", "fechado": "pronto",
    "falhou": "não calculou", "incerto": "confira no Agger", "cancelado": "cancelado", "expirado": "expirou",
}
#: os atalhos do topo da aba (cada um é um filtro; o número é a contagem do que ele mostra)
ATALHOS: Tuple[str, ...] = ("para_enviar_hoje", "precisa_de_voce", "vence_esta_semana", "enviadas")
#: o que ainda é TRABALHO (a renovação que não fechou nem se perdeu)
COLUNAS_EM_ABERTO: Tuple[str, ...] = ("vai_calcular", "calculada", "enviada", "em_negociacao")


def _db() -> Any:
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def _hoje() -> date:
    """O dia de HOJE no fuso do Brasil (a renovação vence num dia do calendário de quem trabalha)."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(R.FUSO_PADRAO)).date()


def _uuid(valor: Any, nome: str) -> str:
    texto = str(valor or "").strip().lower()
    if not _UUID.match(texto):
        raise HTTPException(status_code=400, detail=f"{nome} precisa ser um uuid")
    return texto


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).lower()


def _num(v: Any) -> Optional[float]:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


# ---------------------------------------------------------------------------------------------------------------------
# As peças puras (o teste as chama direto)
# ---------------------------------------------------------------------------------------------------------------------
def rotulo_do_ramo(sigla: Any) -> Optional[str]:
    """`AUTO` → "Auto", `RESI` → "Residencial"… pelo agrupamento que o produto já tem (`familia_de_ramo`); a sigla
    desconhecida volta como veio (nunca se inventa um ramo)."""
    s = str(sigla or "").strip()
    if not s:
        return None
    try:
        from app.providers.policy_data_provider import NOME_DA_FAMILIA, familia_de_ramo

        fam = familia_de_ramo(s)
        nome = NOME_DA_FAMILIA.get(fam or "")
        if nome:
            return nome[:1].upper() + nome[1:]
    except Exception:  # noqa: BLE001
        pass
    return s.upper()


def precisa_de_voce(item: Mapping[str, Any]) -> bool:
    """O SELO (não é coluna): pendente ou falhou (o motivo diz por quê), ou sem ninguém da corretora para cuidar."""
    estado = str(item.get("estado") or "")
    if estado in ("pendente", "falhou"):
        return True
    em_aberto = COLUNA_DO_ESTADO.get(estado) in COLUNAS_EM_ABERTO
    return em_aberto and not item.get("dono_user_id") and not item.get("responsavel_user_id")


def link_do_agger(ramo_agger: Any, negocio_ref: Any) -> Optional[str]:
    """BLOCO 0 B4: `…/cotacao/<ramo>/resultados/<negocio_ref>` (a rota que o app do Agger declara). ⚠️ Que ele abre com a
    pessoa já logada não foi provado por clique — a tela diz "se pedir login, entre e volte"."""
    ref = str(negocio_ref or "").strip()
    if not ref:
        return None
    try:
        from portal_worker.multicalculo.agger_sessao import URL_BASE_AGGER
        from portal_worker.multicalculo.contrato import NOME_DO_RAMO
    except Exception:  # noqa: BLE001
        return None
    try:
        nome = NOME_DO_RAMO.get(int(ramo_agger))
    except (TypeError, ValueError):
        nome = None
    if not nome:
        return None
    return f"{URL_BASE_AGGER.rstrip('/')}/cotacao/{nome}/resultados/{quote(ref, safe='')}"


def resumo_dos_calculos(calculos: Sequence[Mapping[str, Any]], ofertas: Sequence[Mapping[str, Any]],
                        *, ramo_agger: Any = None) -> List[Dict[str, Any]]:
    """Os cálculos da renovação resumidos POR OPÇÃO, na ordem da página: o menor preço, quantas seguradoras deram
    preço, o estado do cálculo em palavras e o link direto ao Agger. `ajuste` (recálculo da negociação) fica de fora."""
    por_opcao: Dict[str, List[Mapping[str, Any]]] = {}
    for c in calculos:
        opcao = str(c.get("opcao") or "")
        if opcao and opcao != "ajuste":
            por_opcao.setdefault(opcao, []).append(c)
    ordem = [o for o in ORDEM_DAS_OPCOES if o in por_opcao] + sorted(o for o in por_opcao if o not in ORDEM_DAS_OPCOES)
    saida: List[Dict[str, Any]] = []
    for opcao in ordem:
        calc = sorted(por_opcao[opcao], key=lambda c: str(c.get("criado_em") or ""))[-1]   # o mais recente vale
        cid = str(calc.get("id") or "")
        validas = [o for o in ofertas if str(o.get("calculo_id") or "") == cid and _num(o.get("premio_total"))]
        menor = min(validas, key=lambda o: float(o["premio_total"])) if validas else None
        status = str(calc.get("status") or "")
        saida.append({
            "opcao": opcao,
            "rotulo": ROTULO_DA_OPCAO.get(opcao, opcao.replace("_", " ").capitalize()),
            "status": status,
            "status_rotulo": ROTULO_DO_STATUS_DO_CALCULO.get(status, status.replace("_", " ")),
            "menor_preco": round(float(menor["premio_total"]), 2) if menor else None,
            "seguradora_do_menor": (str(menor.get("seguradora") or "").strip() or None) if menor else None,
            "franquia_do_menor": _num(menor.get("franquia_valor")) if menor else None,
            "seguradoras": len({str(o.get("seguradora") or "").strip().lower() for o in validas}),
            "agger_url": link_do_agger(ramo_agger, calc.get("negocio_ref")),
        })
    return saida


def item_da_tela(linha: Mapping[str, Any], *, calculos: Sequence[Mapping[str, Any]] = (),
                 ofertas: Sequence[Mapping[str, Any]] = (), nomes: Optional[Mapping[str, str]] = None,
                 hoje: Optional[date] = None) -> Dict[str, Any]:
    """Uma linha de `renovacoes` na forma da tela. Só o que a 131-A já grava: nome CURTO, documento MASCARADO."""
    hoje = hoje or _hoje()
    nomes = nomes or {}
    estado = str(linha.get("estado") or "")
    fim = R.data_de(linha.get("fimvig"))
    dias = (fim - hoje).days if fim else None
    resumo = resumo_dos_calculos(calculos, ofertas, ramo_agger=linha.get("ramo_agger"))
    principal = next((c for c in resumo if c["menor_preco"]), None)
    atual = _num(linha.get("premio_atual"))
    novo = principal["menor_preco"] if principal else None
    variacao = round((novo - atual) / atual * 100, 1) if (novo and atual) else None
    resp_id = str(linha.get("responsavel_user_id") or linha.get("dono_user_id") or "").lower() or None
    coluna = COLUNA_DO_ESTADO.get(estado)
    motivo = linha.get("motivo")
    item = {
        "id": str(linha.get("id")),
        "cliente": linha.get("cliente_nome_curto") or None,
        "documento": linha.get("documento_mascarado") or None,
        "ramo": linha.get("ramo_sigla") or None,
        "ramo_rotulo": rotulo_do_ramo(linha.get("ramo_sigla")),
        "vence_em": fim.isoformat() if fim else None,
        "dias_para_vencer": dias,
        "seguradora_atual": linha.get("seguradora_atual") or None,
        "seguradora_nova": principal["seguradora_do_menor"] if principal else None,
        "premio_atual": atual,
        "premio_novo": novo,
        "variacao_pct": variacao,
        "responsavel": ({"user_id": resp_id, "nome": nomes.get(resp_id) or "Alguém da equipe"} if resp_id else None),
        "dono_user_id": (str(linha.get("dono_user_id")).lower() if linha.get("dono_user_id") else None),
        "estado": estado,
        "estado_rotulo": ROTULO_DO_ESTADO.get(estado, estado.replace("_", " ")),
        "coluna": coluna,
        "precisa_de_voce": precisa_de_voce(linha),
        "motivo": motivo or None,
        "motivo_frase": R.frase_do_motivo(motivo) if motivo else None,
        "calculos": resumo,
        "pode_enviar": estado in ESTADOS_ENVIAVEIS,
        "atualizado_em": linha.get("atualizado_em"),
        "versao": linha.get("versao"),
    }
    atalhos = []
    if estado in ("calculada", "apresentada"):
        atalhos.append("para_enviar_hoje")
    if item["precisa_de_voce"]:
        atalhos.append("precisa_de_voce")
    if dias is not None and 0 <= dias <= 7 and coluna in COLUNAS_EM_ABERTO:
        atalhos.append("vence_esta_semana")
    if coluna == "enviada":
        atalhos.append("enviadas")
    item["atalhos"] = atalhos
    return item


def proximo_passo(item: Mapping[str, Any], linha: Mapping[str, Any]) -> str:
    """O que fazer agora com esta renovação, numa frase (o cabeçalho do detalhe)."""
    estado = str(item.get("estado") or "")
    if estado in ("pendente", "falhou"):
        return f"Precisa de você: {item.get('motivo_frase') or 'confira no Agger'}."
    if estado in ("listada", "pronta"):
        quando = R.data_de(linha.get("calcular_em"))
        return (f"Vai calcular na madrugada de {quando.strftime('%d/%m')}." if quando
                else "Vai calcular numa das próximas madrugadas.")
    if estado in ("calculando", "aguardando_agger"):
        return "Calculando no Agger agora. Fica pronto antes das 7h."
    if estado == "calculada":
        return "Confira os cálculos e envie ao cliente pelo WhatsApp."
    if estado == "apresentada":
        return "A apresentação está pronta: envie ao cliente pelo WhatsApp."
    if estado in ("enviada", "vista"):
        return "Enviada. Agora é esperar a resposta do cliente."
    return str(item.get("estado_rotulo") or "")


def numero_de_whatsapp(cliente: Mapping[str, Any]) -> Optional[str]:
    """O número do cadastro do cliente (`/cliente`) em dígitos E.164 do Brasil (`55` + DDD + número), o CELULAR
    primeiro. Formas lidas (as que o produto já lê, `infocap_connector._client_phone`): `telefones[]` com `{ddd,
    numero}` (ou texto), `telefone`, `contatos[]`. Nada válido → None. ⛔ Quem chama nunca loga o que volta."""
    candidatos: List[str] = []

    def juntar(v: Any) -> None:
        if isinstance(v, Mapping):
            numero = v.get("numero") or v.get("telefone") or v.get("celular") or v.get("fone")
            if numero:
                candidatos.append(f"{v.get('ddd') or ''}{numero}")
        elif isinstance(v, (str, int)):
            candidatos.append(str(v))

    for chave in ("telefones", "contatos"):
        lista = cliente.get(chave)
        for v in (lista if isinstance(lista, list) else []):
            juntar(v)
    juntar(cliente.get("celular"))
    juntar(cliente.get("telefone"))
    validos: List[str] = []
    for bruto in candidatos:
        d = re.sub(r"\D", "", bruto).lstrip("0")
        if len(d) in (10, 11):
            d = "55" + d
        if len(d) in (12, 13) and d.startswith("55") and d not in validos:
            validos.append(d)
    celular = next((d for d in validos if len(d) == 13 and d[4] == "9"), None)
    return celular or (validos[0] if validos else None)


def url_do_wa_me(numero: str, texto: str) -> str:
    return f"https://wa.me/{numero}?text={quote(texto, safe='')}"


# ---------------------------------------------------------------------------------------------------------------------
# As leituras (sempre da corretora da sessão)
# ---------------------------------------------------------------------------------------------------------------------
def _em_lotes(ids: Sequence[str], n: int = 50) -> Iterable[List[str]]:
    for i in range(0, len(ids), n):
        yield list(ids[i:i + n])


def calculos_e_ofertas(db: Any, cid: str, pedido_ids: Iterable[str]) -> Tuple[Dict[str, List[Dict[str, Any]]],
                                                                                  Dict[str, List[Dict[str, Any]]]]:
    """Os cálculos e as ofertas dos pedidos da renovação, POR PEDIDO, filtrados pelo SOLICITANTE (a corretora da sessão)
    no banco e de novo aqui. Lidos em lotes e paginados (o PostgREST corta em 1000 linhas)."""
    from app.leitura_completa import ler_paginado
    from app.services.multicalculo.repositorio import CALCULOS, OFERTAS

    ids = sorted({str(p).lower() for p in pedido_ids if p})
    calcs: Dict[str, List[Dict[str, Any]]] = {}
    ofs: Dict[str, List[Dict[str, Any]]] = {}
    for lote in _em_lotes(ids):
        linhas, _ = ler_paginado(
            lambda lote=lote: db.table(CALCULOS).select("id, pedido_id, solicitante_company_id, opcao, status, "
                                                        "negocio_ref, versao, criado_em")
            .in_("pedido_id", lote).eq("solicitante_company_id", cid),
            chave_unica="id", rotulo="renovacoes.calculos")
        for c in linhas:
            if str(c.get("solicitante_company_id") or "").lower() == cid:
                calcs.setdefault(str(c.get("pedido_id")).lower(), []).append(c)
        linhas, _ = ler_paginado(
            lambda lote=lote: db.table(OFERTAS).select("id, calculo_id, pedido_id, solicitante_company_id, seguradora, "
                                                       "premio_total, franquia_valor")
            .in_("pedido_id", lote).eq("solicitante_company_id", cid),
            chave_unica="id", rotulo="renovacoes.ofertas")
        for o in linhas:
            if str(o.get("solicitante_company_id") or "").lower() == cid:
                ofs.setdefault(str(o.get("pedido_id")).lower(), []).append(o)
    return calcs, ofs


def _nomes_da_equipe(db: Any, cid: str) -> Dict[str, str]:
    try:
        from app.services.sistema_de_gestao import dono as DONO

        return {m["user_id"]: m["nome"] for m in DONO.membros_ativos(db, cid)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOVACOES] equipe ilegível: %s", type(exc).__name__)
        return {}


def aplicativo_ligado(db: Any, cid: str) -> bool:
    """A corretora tem o aplicativo de Renovação LIGADO (a madrugada só roda assim — 131-A)?"""
    try:
        linhas = list(getattr(db.table("tenant_auxiliaries").select("company_id, slug, status")
                              .eq("company_id", cid).eq("slug", "renovacao").limit(1).execute(), "data", None) or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOVACOES] estado do aplicativo ilegível: %s", type(exc).__name__)
        return False
    return any(str(x.get("company_id", "")).lower() == cid and x.get("status") == "active" for x in linhas)


def _casa_busca(linha: Mapping[str, Any], q: str) -> bool:
    texto = _sem_acento(q.strip())
    if not texto:
        return True
    digitos = re.sub(r"\D", "", q)
    if len(digitos) in (11, 14):   # o CPF/CNPJ inteiro: compara pelo HMAC (o banco nunca teve o documento em claro)
        try:
            return R.hmac_do_documento(digitos) == linha.get("documento_hmac")
        except Exception:  # noqa: BLE001 — sem a chave do HMAC, a busca por documento não casa nada (fail-closed)
            return False
    return texto in _sem_acento(str(linha.get("cliente_nome_curto") or ""))


def _filtrar(linhas: List[Dict[str, Any]], *, uid: str, escopo: str, estado: Optional[str], ramo: Optional[str],
             de: Optional[str], ate: Optional[str], seguradora: Optional[str], q: Optional[str]) -> List[Dict[str, Any]]:
    saida = []
    estados = {e.strip() for e in (estado or "").split(",") if e.strip()}
    ramo_alvo = _sem_acento(ramo or "")
    seg_alvo = _sem_acento(seguradora or "")
    for x in linhas:
        if escopo == "minhas" and uid not in (str(x.get("dono_user_id") or "").lower(),
                                              str(x.get("responsavel_user_id") or "").lower()):
            continue
        if estados and str(x.get("estado")) not in estados and COLUNA_DO_ESTADO.get(str(x.get("estado"))) not in estados:
            continue
        if ramo_alvo and ramo_alvo not in (_sem_acento(str(x.get("ramo_sigla") or "")),
                                           _sem_acento(rotulo_do_ramo(x.get("ramo_sigla")) or "")):
            continue
        if seg_alvo and _sem_acento(str(x.get("seguradora_atual") or "")) != seg_alvo:
            continue
        fim = str(R.data_de(x.get("fimvig")) or "")
        if de and fim < de:
            continue
        if ate and fim > ate:
            continue
        if q and not _casa_busca(x, q):
            continue
        saida.append(x)
    return saida


def montar_lista(db: Any, cid: str, uid: str, *, escopo: str = "minhas", estado: Optional[str] = None,
                 ramo: Optional[str] = None, de: Optional[str] = None, ate: Optional[str] = None,
                 seguradora: Optional[str] = None, q: Optional[str] = None) -> Dict[str, Any]:
    hoje = _hoje()
    if not de and not ate:
        de = (hoje - timedelta(days=DIAS_PARA_TRAS_PADRAO)).isoformat()
    repo = R.RepositorioDeRenovacoes(db)
    todas = repo.listar(cid, estados=ESTADOS_VISIVEIS)
    do_escopo = _filtrar(todas, uid=uid, escopo=escopo, estado=None, ramo=None, de=None, ate=None, seguradora=None,
                         q=None)
    linhas = _filtrar(do_escopo, uid=uid, escopo=escopo, estado=estado, ramo=ramo, de=de, ate=ate,
                      seguradora=seguradora, q=q)
    calcs, ofs = calculos_e_ofertas(db, cid, [x.get("pedido_id") for x in linhas])
    nomes = _nomes_da_equipe(db, cid)
    itens = []
    for x in linhas:
        pid = str(x.get("pedido_id") or "").lower()
        itens.append(item_da_tela(x, calculos=calcs.get(pid, []), ofertas=ofs.get(pid, []), nomes=nomes, hoje=hoje))
    itens.sort(key=lambda i: (i["vence_em"] or "9999", _sem_acento(i["cliente"] or "")))
    ramos: Dict[str, str] = {}
    for x in do_escopo:
        if x.get("ramo_sigla"):
            ramos.setdefault(str(x["ramo_sigla"]), rotulo_do_ramo(x["ramo_sigla"]) or str(x["ramo_sigla"]))
    return {
        "itens": itens,
        "total": len(itens),
        "contagens": {a: sum(1 for i in itens if a in i["atalhos"]) for a in ATALHOS},
        "escopo": escopo,
        "eu": uid,
        "hoje": hoje.isoformat(),
        "ligado": aplicativo_ligado(db, cid),
        "tem_alguma": bool(todas),
        "seguradoras": sorted({str(x["seguradora_atual"]) for x in do_escopo if x.get("seguradora_atual")},
                              key=_sem_acento),
        "ramos": [{"id": k, "rotulo": v} for k, v in sorted(ramos.items(), key=lambda kv: _sem_acento(kv[1]))],
    }


def _por_de_evento(por: Any, nomes: Mapping[str, str]) -> str:
    p = str(por or "").strip().lower()
    if p in nomes:
        return nomes[p]
    return "Alguém da equipe" if _UUID.match(p) else "O aplicativo"


def _frase_do_evento(ev: Mapping[str, Any], quem: str) -> str:
    para = str(ev.get("para") or "")
    motivo = ev.get("motivo")
    if para == "enviada" or motivo == "aberto_para_envio":
        via = (ev.get("dados") or {}).get("via") if isinstance(ev.get("dados"), Mapping) else None
        return (f"{quem} copiou a mensagem para enviar" if via == "copiar"
                else f"{quem} abriu o WhatsApp para enviar")
    if para == "apresentada":
        return f"{quem} preparou a apresentação"
    if para in ("pendente", "falhou"):
        return f"{ROTULO_DO_ESTADO[para]}: {R.frase_do_motivo(motivo)}" if motivo else ROTULO_DO_ESTADO[para]
    if para == "listada":
        return "Entrou na lista da madrugada"
    return ROTULO_DO_ESTADO.get(para, para.replace("_", " "))


def montar_detalhe(db: Any, cid: str, uid: str, rid: str) -> Dict[str, Any]:
    repo = R.RepositorioDeRenovacoes(db)
    linha = repo.por_id(cid, rid)
    pid = str(linha.get("pedido_id") or "").lower()
    calcs, ofs = calculos_e_ofertas(db, cid, [pid] if pid else [])
    nomes = _nomes_da_equipe(db, cid)
    item = item_da_tela(linha, calculos=calcs.get(pid, []), ofertas=ofs.get(pid, []), nomes=nomes)
    eventos = []
    for ev in repo.eventos(cid, rid):
        quem = _por_de_evento(ev.get("por"), nomes)
        eventos.append({"quando": ev.get("criado_em"), "para": ev.get("para"), "frase": _frase_do_evento(ev, quem)})
    agger = next((c["agger_url"] for c in item["calculos"] if c.get("agger_url")), None)
    return {**item, "eventos": list(reversed(eventos)), "proximo_passo": proximo_passo(item, linha),
            "agger_url": agger, "eu": uid}


# ---------------------------------------------------------------------------------------------------------------------
# As bordas: a apresentação e a mensagem (G4, pelo contrato) e a InfoCap da corretora
# ---------------------------------------------------------------------------------------------------------------------
async def _chamar(fn: Any, *args: Any, **kwargs: Any) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    r = await asyncio.to_thread(fn, *args, **kwargs)
    return await r if inspect.isawaitable(r) else r


def quem_clica(db: Any, cid: str, uid: str) -> Dict[str, Any]:
    """A `pessoa` do contrato da G4: {user_id, primeiro_nome} de QUEM clicou — o nome só se ela é membro DESTA
    corretora (`proposta.pessoa_de`, filtro company_id). Sem nome legível, só o id (a mensagem sai sem "Aqui é…")."""
    from app.services.multicalculo import proposta as P

    try:
        return dict(P.pessoa_de(db, cid, uid))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOVACOES] nome de quem clicou ilegível: %s", type(exc).__name__)
        return {"user_id": uid}


def _erro_da_publicacao(exc: Exception) -> Optional[HTTPException]:
    from app.services.multicalculo import proposta as P

    if isinstance(exc, P.PropostaImpossivel):
        return HTTPException(status_code=409, detail="Ainda não dá para montar a apresentação desta renovação: "
                                                     "falta um cálculo com preço. Confira no Agger.")
    if isinstance(exc, P.LinkSemEndereco):
        return HTTPException(status_code=503, detail="O endereço público do painel não está configurado: o link "
                                                     "da apresentação não teria para onde apontar.")
    return None


async def publicar(db: Any, cid: str, rid: str, pessoa: Mapping[str, Any]) -> Dict[str, Any]:
    """`proposta.publicar_renovacao(company_id, renovacao_id, *, pessoa, db) -> {token, url, artifact_id, versao,
    validade_ate, modelo}` (contrato da SPEC §5, G4) — ASYNC, com o MESMO banco da sessão. Ela NÃO muda o estado
    (quem faz `apresentada` é esta API)."""
    from app.services.multicalculo import proposta as P

    try:
        r = await _chamar(P.publicar_renovacao, cid, rid, pessoa=dict(pessoa), db=db)
    except Exception as exc:  # noqa: BLE001
        http = _erro_da_publicacao(exc)
        if http is None:
            raise
        raise http
    if not isinstance(r, Mapping) or not r.get("url"):
        raise HTTPException(status_code=502, detail="Não consegui preparar a apresentação agora. Tente de novo.")
    return dict(r)


#: um link que vence antes disto não é reaproveitado no envio (o cliente abriria um link morto)
FOLGA_DO_LINK_REAPROVEITADO = timedelta(days=2)


def ultima_apresentacao(db: Any, cid: str, linha: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """A apresentação JÁ publicada desta renovação (`proposta_ref` = o token do `/r/`), para o envio mandar o MESMO
    link que o comercial conferiu — sem versão nova a cada clique. Só vale se o link é DESTA corretora, não foi
    revogado, não vence nos próximos dias e a versão é uma página de RENOVAÇÃO (`modelo["renovacao"]`). Qualquer
    dúvida → None (quem chama republica). Devolve {token, url, versao, artifact_id, modelo}."""
    token = str(linha.get("proposta_ref") or "").strip()
    if not token or linha.get("estado") not in ("apresentada", "enviada"):
        return None
    try:
        from app.services.multicalculo import proposta as P

        shares = list(getattr(db.table("artifact_shares")
                              .select("company_id, artifact_id, artifact_version_id, expires_at, revoked_at")
                              .eq("token", token).eq("company_id", cid).limit(1).execute(), "data", None) or [])
        s = next((x for x in shares if str(x.get("company_id") or "").lower() == cid), None)
        if s is None or s.get("revoked_at"):
            return None
        vence = datetime.fromisoformat(str(s.get("expires_at")).replace("Z", "+00:00"))
        if vence <= datetime.now(vence.tzinfo) + FOLGA_DO_LINK_REAPROVEITADO:
            return None
        versoes = list(getattr(db.table("artifact_versions").select("id, company_id, version, payload")
                               .eq("id", s["artifact_version_id"]).eq("company_id", cid).limit(1).execute(),
                               "data", None) or [])
        v = next((x for x in versoes if str(x.get("company_id") or "").lower() == cid), None)
        modelo = (v or {}).get("payload")
        if not isinstance(modelo, Mapping) or not isinstance(modelo.get("renovacao"), Mapping) \
                or not modelo.get("opcoes"):
            return None
        return {"token": token, "url": f"{P._base_do_link(None)}/r/{token}", "versao": int(v.get("version") or 1),
                "artifact_id": str(s.get("artifact_id")), "modelo": dict(modelo)}
    except Exception as exc:  # noqa: BLE001 — na dúvida, republica (nunca um link morto ao cliente)
        logger.info("[RENOVACOES] a apresentação anterior não serve: %s", type(exc).__name__)
        return None


def _config_da_renovacao(db: Any, cid: str) -> Optional[Mapping[str, Any]]:
    try:
        from app.services.multicalculo import config as CFG

        return CFG.carregar(cid, db=db, servico="renovacao")
    except Exception as exc:  # noqa: BLE001 — a mensagem usa o padrão do produto
        logger.info("[RENOVACOES] config ilegível para a mensagem: %s", type(exc).__name__)
        return None


async def mensagem(db: Any, cid: str, renovacao: Mapping[str, Any], proposta: Mapping[str, Any],
                   pessoa: Mapping[str, Any]) -> Dict[str, Any]:
    """`mensagem.mensagem_de_renovacao(renovacao, {url, modelo}, *, pessoa={primeiro_nome}) -> {texto, texto_curto,
    link}` (G4). ⛔ Nunca recebe o telefone: o `wa.me/<cliente>` é esta API que monta, na hora."""
    from app.services.multicalculo import mensagem as MSG

    kw: Dict[str, Any] = {"pessoa": {"primeiro_nome": pessoa.get("primeiro_nome")}}
    cfg = await asyncio.to_thread(_config_da_renovacao, db, cid)
    if cfg is not None:
        kw["config"] = cfg
    try:
        r = await _chamar(MSG.mensagem_de_renovacao, dict(renovacao),
                          {"url": proposta.get("url"), "modelo": proposta.get("modelo") or {}}, **kw)
    except ValueError as exc:
        logger.warning("[RENOVACOES] mensagem impossível: %s", type(exc).__name__)
        raise HTTPException(status_code=409, detail="Não consegui montar a mensagem: a apresentação não tem opção "
                                                    "com preço.")
    if not isinstance(r, Mapping) or not str(r.get("texto") or "").strip():
        raise HTTPException(status_code=502, detail="Não consegui montar a mensagem agora. Tente de novo.")
    return dict(r)


async def abrir_fonte(db: Any, cid: str) -> Any:
    """A InfoCap DESTA corretora pelo caminho canônico (`dono.abrir_fonte`, nunca por nome — §13.9)."""
    from app.services.sistema_de_gestao import dono as DONO

    return await DONO.abrir_fonte(db, cid)


async def telefone_do_cliente(db: Any, cid: str, renovacao: Mapping[str, Any]) -> Optional[str]:
    """O WhatsApp do cliente, lido AGORA: `/documento` (o `codcli` da apólice) → `/cliente` (o cadastro, SEM cache —
    `cliente_cru` não guarda no Redis). Volta só para quem chamou; nunca é logado nem gravado. Falhou → None."""
    try:
        fonte = await abrir_fonte(db, cid)
        codfil, nosnum = R.codfil_de(renovacao.get("codfil")), R.nosnum_de(renovacao.get("nosnum"))
        doc = await asyncio.to_thread(fonte.documento_cru, codfil, nosnum)
        codcli = (doc or {}).get("codcli")
        if not codcli:
            return None
        cliente = await asyncio.to_thread(fonte.cliente_cru, codfil, codcli)
        return numero_de_whatsapp(cliente or {})
    except Exception as exc:  # noqa: BLE001 — ⛔ só o TIPO do erro: a mensagem de uma exceção pode carregar o dado
        logger.warning("[RENOVACOES] telefone do cliente ilegível agora: %s", type(exc).__name__)
        return None


# ---------------------------------------------------------------------------------------------------------------------
# As escritas — SÓ pela máquina da 131-A
# ---------------------------------------------------------------------------------------------------------------------
def _erro_da_maquina(exc: Exception) -> HTTPException:
    if isinstance(exc, R.NaoEncontrada):
        return HTTPException(status_code=404, detail="Esta renovação não existe nesta corretora.")
    if isinstance(exc, R.ConcorrenciaPerdida):
        return HTTPException(status_code=409, detail="Outra pessoa mexeu nesta renovação agora. Abra de novo.")
    return HTTPException(status_code=409, detail="Esta renovação mudou de estado. Abra de novo para ver como está.")


def _apresentar(db: Any, cid: str, rid: str, uid: str, token: Optional[str]) -> Dict[str, Any]:
    """`calculada → apresentada` (com a referência da página). Já apresentada ou enviada: nada muda."""
    repo = R.RepositorioDeRenovacoes(db)
    linha = repo.por_id(cid, rid)
    if linha.get("estado") != "calculada":
        return linha
    campos = {"proposta_ref": token} if token and linha.get("proposta_ref") != token else None
    return repo.transicionar(cid, rid, "apresentada", por=uid, campos=campos)


def _registrar_envio(db: Any, cid: str, rid: str, uid: str, *, via: str, proposta: Mapping[str, Any]) -> Dict[str, Any]:
    """O evento `aberto_para_envio` (quem, versão, por onde — ⛔ SEM telefone) e `apresentada → enviada`. Uma renovação
    já enviada que se abre de novo ganha só o evento (a máquina não tem `enviada → enviada`)."""
    repo = R.RepositorioDeRenovacoes(db)
    linha = repo.por_id(cid, rid)
    dados = {"evento": "aberto_para_envio", "via": via, "por_user_id": uid, "versao": linha.get("versao"),
             "proposta_versao": proposta.get("versao")}
    if linha.get("estado") == "enviada":
        repo._evento(cid, rid, "enviada", "enviada", uid, "aberto_para_envio", dados)   # a escrita da própria máquina
        return linha
    return repo.transicionar(cid, rid, "enviada", por=uid, motivo="aberto_para_envio", dados=dados)


async def _corpo(request: Request) -> Dict[str, Any]:
    try:
        corpo = await request.json()
    except Exception:  # noqa: BLE001
        corpo = {}
    if not isinstance(corpo, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    estranhas = set(corpo) - CHAVES_DO_POST
    if estranhas:
        # ⛔ mutação 4: nenhuma rota recebe um estado ou uma coluna de destino
        raise HTTPException(status_code=400, detail="campos que esta ação não recebe: " + ", ".join(sorted(estranhas)))
    return corpo


# ---------------------------------------------------------------------------------------------------------------------
# As rotas
# ---------------------------------------------------------------------------------------------------------------------
@router.get("")
async def listar_renovacoes(
    company_id: str,
    user_id: str,
    escopo: str = "minhas",
    estado: Optional[str] = None,
    ramo: Optional[str] = None,
    de: Optional[str] = None,
    ate: Optional[str] = None,
    seguradora: Optional[str] = None,
    q: Optional[str] = None,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    if escopo not in ESCOPOS:
        raise HTTPException(status_code=400, detail="escopo é minhas ou todas")
    for nome, valor in (("de", de), ("ate", ate)):
        if valor and not _DATA.match(valor):
            raise HTTPException(status_code=400, detail=f"{nome} é uma data AAAA-MM-DD")
    try:
        return await asyncio.to_thread(montar_lista, _db(), cid, uid, escopo=escopo, estado=estado, ramo=ramo, de=de,
                                       ate=ate, seguradora=seguradora, q=(q or "")[:80] or None)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[RENOVACOES] lista falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Não consegui carregar as renovações agora.")


@router.get("/{renovacao_id}")
async def detalhe_da_renovacao(
    renovacao_id: str,
    company_id: str,
    user_id: str,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    try:
        return await asyncio.to_thread(montar_detalhe, _db(), cid, uid, rid)
    except R.NaoEncontrada as exc:
        raise _erro_da_maquina(exc)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[RENOVACOES] detalhe falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Não consegui abrir esta renovação agora.")


@router.post("/{renovacao_id}/apresentacao")
async def apresentar_renovacao(
    renovacao_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    corpo = await _corpo(request)
    cid, uid = _uuid(corpo.get("company_id"), "company_id"), _uuid(corpo.get("user_id"), "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    db = _db()
    try:
        linha = await asyncio.to_thread(R.RepositorioDeRenovacoes(db).por_id, cid, rid)
        if linha.get("estado") not in ESTADOS_ENVIAVEIS:
            raise HTTPException(status_code=409, detail="Esta renovação ainda não foi calculada.")
        proposta = await asyncio.to_thread(ultima_apresentacao, db, cid, linha)
        if proposta is None:
            pessoa = await asyncio.to_thread(quem_clica, db, cid, uid)
            proposta = await publicar(db, cid, rid, pessoa)
        linha = await asyncio.to_thread(_apresentar, db, cid, rid, uid, proposta.get("token"))
    except (R.NaoEncontrada, R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
        raise _erro_da_maquina(exc)
    return {"token": proposta.get("token"), "url": proposta.get("url"), "versao": proposta.get("versao"),
            "estado": linha.get("estado")}


@router.post("/{renovacao_id}/envio")
async def enviar_renovacao(
    renovacao_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """Prepara o envio: a apresentação publicada, a mensagem pronta e — por WhatsApp — o `wa.me` do cliente. Quem
    ENVIA é a pessoa, no aparelho dela. `via=copiar` (o botão "Copiar a mensagem") não lê telefone nenhum."""
    _require_internal_key(x_key)
    corpo = await _corpo(request)
    cid, uid = _uuid(corpo.get("company_id"), "company_id"), _uuid(corpo.get("user_id"), "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    via = str(corpo.get("via") or "whatsapp")
    if via not in VIAS_DO_ENVIO:
        raise HTTPException(status_code=400, detail="via é whatsapp ou copiar")
    db = _db()
    try:
        linha = await asyncio.to_thread(R.RepositorioDeRenovacoes(db).por_id, cid, rid)
        if linha.get("estado") not in ESTADOS_ENVIAVEIS:
            raise HTTPException(status_code=409, detail="Esta renovação ainda não foi calculada.")
        pessoa = await asyncio.to_thread(quem_clica, db, cid, uid)
        # a ÚLTIMA apresentação publicada (o link que o comercial conferiu); sem ela, ou vencendo, publica agora
        proposta = await asyncio.to_thread(ultima_apresentacao, db, cid, linha)
        if proposta is None:
            proposta = await publicar(db, cid, rid, pessoa)
        linha = await asyncio.to_thread(_apresentar, db, cid, rid, uid, proposta.get("token"))
        msg = await mensagem(db, cid, linha, proposta, pessoa)
        completo = str(msg["texto"])
        no_link = completo if len(completo) <= LIMITE_DO_TEXTO_NO_LINK else str(msg.get("texto_curto") or completo)
        resposta: Dict[str, Any] = {"texto": no_link, "texto_completo": completo, "link": msg.get("link")}
        if via == "whatsapp":
            numero = await telefone_do_cliente(db, cid, linha)
            if not numero:
                # sem telefone: nada foi aberto — a pessoa copia a mensagem (e o "copiar" registra o envio)
                return {**resposta, "sem_telefone": True, "estado": linha.get("estado")}
            resposta["wa_me_url"] = url_do_wa_me(numero, no_link)
        linha = await asyncio.to_thread(_registrar_envio, db, cid, rid, uid, via=via, proposta=proposta)
    except (R.NaoEncontrada, R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
        raise _erro_da_maquina(exc)
    return {**resposta, "sem_telefone": False if via == "whatsapp" else None, "estado": linha.get("estado")}
