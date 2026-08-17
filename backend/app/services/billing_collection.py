"""SPEC-023 P4 - rotina global de cobranca de boletos.

Este modulo NAO e um worker novo. Ele e uma especializacao do motor existente de
rotinas: enfileira portal_jobs, consolida evidencias e devolve o relatorio para
o routine_engine entregar pelo canal da rotina.

SPEC-063 Bloco C — a rajada que este arquivo produzia
=====================================================
`_send_test_messages` percorria ate `max_boletos_por_execucao` itens (limite
50) e, para cada um, enviava DUAS mensagens: o texto e o boleto em PDF. 📊
50 x 2 = 100 mensagens seguidas, sem uma unica pausa, saindo do WhatsApp da
corretora. Um numero novo que faz isso e banido — e quem perde o canal e a
corretora, nao a plataforma.

Agora cada item pergunta ao governador (`platform_outbound`) antes de sair.

**O governador conta APROXIMACOES, nao mensagens.** Texto + boleto para o mesmo
segurado sao um unico ato de fala: quem recebe ve uma conversa, nao duas
abordagens. Espacar o PDF em 6 minutos do texto que o anuncia seria pior que
nao espacar — deixaria o segurado esperando um anexo que ele acabou de ler que
viria "abaixo". Entao o par sai junto, e o governador cobra o intervalo antes do
PROXIMO segurado.

Quando o governador manda esperar, a rotina espera de verdade (`asyncio.sleep`,
que nao congela o event loop — a licao do Bloco H) ate um orcamento de tempo.
Estourado o orcamento, ou fechada a janela, ela **para e relata**: os itens nao
enviados nao entram em `billing_sent_log`, e por isso a proxima execucao os
pega de onde parou. Nao ha fila nova nem estado novo — o anti-duplicacao que ja
existia e o que torna "parar no meio" seguro.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

BILLING_KIND = "billing_collection"
# Quanto tempo uma execucao da rotina aceita ficar esperando o governador
# liberar o proximo slot. Uma hora cabe ~9 aproximacoes espacadas em 4–8 min;
# alem disso e melhor terminar o relatorio e continuar na proxima execucao do
# que segurar uma rotina viva por meio dia.
GOVERNOR_WAIT_BUDGET_S = 3600

# Carencia antes de cobrar. Boleto pago nao baixa na hora: cobrar quem pagou
# ontem queima a corretora com o proprio cliente. A journey ja aplica isso na
# janela de busca; aqui e a segunda rede, porque um portal novo pode ignorar o
# filtro de data e devolver a parcela de ontem assim mesmo.
HORAS_MINIMAS_ATRASO = 48


def _portais_que_sei_varrer() -> List[str]:
    """Os portais com journey de cobranca — a lista vem do REGISTRO, nao daqui.

    Antes esta constante era `["allianz_corretor"]` fixo, e ela decidia sozinha
    o que a rotina varria: uma seguradora nova podia ter journey, credencial e
    tela, e ainda assim nunca ser visitada. Agora quem responde e o registro de
    journeys, que e o unico lugar que SABE o que o worker consegue fazer.

    Fallback só existe porque o backend (smith-api) e o portal-worker sao dois
    serviços: se o pacote do worker nao estiver no PYTHONPATH deste processo, a
    rotina segue com o que ja era provado em vez de varrer nada.
    """
    try:
        from portal_worker.journeys import portais_com_cobranca

        return list(portais_com_cobranca())
    except Exception:  # noqa: BLE001
        return ["allianz_corretor", "hdi_corretor"]


DEFAULT_PORTAL_KEYS = _portais_que_sei_varrer()
# Mensagem PADRÃO TRAVADA (definida pelo founder 2026-07-11). Sem negrito/itálico,
# com espaçamento entre as linhas. É a que aparece (read-only) no campo do
# auxiliar no dashboard. Só o time pode editar até liberação.
DEFAULT_MESSAGE_TEMPLATE = (
    "Olá {primeiro_nome},\n\n"
    "Aqui é a {nome_atendente}, da {nome_corretora}, tudo bem?\n\n"
    "A Seguradora {nome_seguradora} informou que a parcela {numero_parcela} "
    "do seguro do {item_segurado} ainda está pendente.\n\n"
    "Desta forma, a seguradora gerou um novo boleto para pagamento pra você "
    "não ficar sem cobertura, ok!?\n\n"
    "Qualquer dúvida estou à disposição.\n\n"
    "Segue o boleto abaixo.\n"
    "Apólice: {numero_apolice}"
)
# Parcela em atraso SEM boleto (debito automatico ou cartao recusado).
#
# Nao existe boleto para mandar, e gerar um exige "Alteracoes Financeiras" no
# portal — que escreve no contrato do segurado, e por isso e proibido ao robo.
#
# DECISAO DO FOUNDER (12/08/2026): o robo **nao fala com o segurado** nesse
# caso. Quem fala e a atendente humana, depois de converter no portal.
#
# A versao anterior mandava uma mensagem dizendo "ja avisei nossa equipe e
# alguem vai falar com voce". Duas coisas erradas nela:
#   1. o sistema prometia, em nome de uma pessoa, um contato que a pessoa ainda
#      nao sabia que tinha de fazer;
#   2. se a atendente demorasse, quem ficou mal foi a corretora — por uma frase
#      que ninguem escreveu.
#
# Entao: entra na lista de TAREFAS da equipe, e sai da fila de envio. O segurado
# so recebe mensagem quando um humano decidir manda-la.
TERMINAL_JOB_STATUSES = {"done", "needs_human", "failed"}
TEST_LINK_TTL_SECONDS = 7 * 24 * 60 * 60


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "sim"}


def _int_clamped(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return default


def _primeiro_nome(full_name: Any) -> str:
    """Primeiro nome do segurado, capitalizado (MONICA BONELLI... -> Monica).
    Pula prefixos de tratamento se vierem no cadastro (Sra., Sr., Dr.)."""
    tokens = [t for t in str(full_name or "").replace(".", " ").split() if t]
    skip = {"sr", "sra", "dr", "dra", "sto", "sta"}
    for tok in tokens:
        if tok.lower().strip(".") in skip:
            continue
        return tok.capitalize()
    return "cliente"


# A frase que a journey escreve quando a SEGURADORA nao emite boleto para
# aquela forma de pagamento (debito automatico, cartao). Contrato de texto entre
# a journey e este servico — por isso mora numa constante, e nao espalhada.
MARCA_REGRA_DA_SEGURADORA = "nao emite 2a via de boleto"


def sem_boleto_por_regra(item: Dict[str, Any]) -> bool:
    """A seguradora nao emite boleto para esta parcela?

    Le o motivo que a journey escreveu — nao adivinha pela ausencia do boleto.
    A diferenca decide o que acontece com o segurado:

        regra da seguradora  ->  TAREFA para a atendente. O robo nao fala.
        falha nossa          ->  fica no relatorio como defeito a investigar.

    Confundir os dois faria o robo abrir tarefa para a equipe toda vez que um
    download quebrasse — e a equipe pararia de ler a lista.
    """
    return MARCA_REGRA_DA_SEGURADORA in _norm_txt(item.get("sem_boleto_motivo"))


# Nome antigo, mantido enquanto houver chamador. Debito automatico e um dos
# casos, nao o unico: o Credito recusado cai exatamente aqui tambem.
sem_boleto_por_debito = sem_boleto_por_regra


def _norm_txt(value: Any) -> str:
    import unicodedata

    texto = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(texto.split())


def tarefas_para_a_equipe(items: List[Dict[str, Any]], cfg: Optional[Dict[str, Any]] = None
                          ) -> List[Dict[str, Any]]:
    """O que precisa de gente: converter para boleto no portal e falar com o segurado.

    Nao cria tabela nova. A tarefa vive no relatorio da rotina e no aviso ao
    canal de suporte humano — que sao os dois lugares onde a corretora ja olha.

    Carrega TUDO que a atendente precisa para decidir sem abrir outro sistema:
    telefone, seguradora, ramo, apolice, parcela, vencimento, valor e o motivo.
    Faltar o telefone aqui era o que obrigava a pessoa a ir atras da informacao
    — justamente o trabalho que o aviso existe para poupar.
    """
    cfg = cfg or {}
    out: List[Dict[str, Any]] = []
    for i in items or []:
        if not sem_boleto_por_regra(i):
            continue
        motivo = str(i.get("sem_boleto_motivo") or "")
        # "pagamento em debito - a HDI nao emite..." -> "Débito automático recusado"
        forma = motivo.split("-")[0].replace("pagamento em", "").strip() or "forma de pagamento"
        out.append({
            "portal": i.get("portal"),
            "cliente_nome": i.get("cliente_nome"),
            "whatsapp": i.get("whatsapp"),
            "nome_seguradora": _portal_insurer_name(i, cfg),
            "item_segurado": _insured_item_name(i),
            "apolice_susep": i.get("apolice_susep") or i.get("documento"),
            "parcela": i.get("parcela"),
            "vencimento": i.get("vencimento"),
            "valor": i.get("valor"),
            "motivo": f"{forma.capitalize()} recusado",
            "observacao": i.get("observacao") or "",
            "acao": "Converter para boleto no portal e enviar ao segurado",
        })
    return out


async def avisar_suporte_humano(client, company_id: str, texto: str, rotulo: str) -> bool:
    """Manda o aviso para o grupo de suporte humano DESTA corretora.

    O agente nunca sabe o nome do grupo. Ele diz "avise o suporte desta
    corretora" e o sistema resolve em `human_support_destinations` — assim mil
    corretoras tem mil destinos e zero codigo especifico, e trocar de grupo e
    mexer num campo de tela.

    Sem destino cadastrado NAO e erro: o aviso ja esta no relatorio da rotina,
    e o relatorio diz que faltou destino. Falhar aqui derrubaria a colheita
    inteira por causa de um campo em branco.
    """
    try:
        def _destino():
            res = (client.table("human_support_destinations")
                   .select("destination_type, destination_ref, is_primary, priority_order")
                   .eq("company_id", str(company_id)).eq("is_active", True)
                   .order("is_primary", desc=True).order("priority_order")
                   .limit(1).execute())
            return (res.data or [None])[0]

        destino = await asyncio.to_thread(_destino)
        if not destino or not destino.get("destination_ref"):
            return False

        integration = await asyncio.to_thread(_find_whatsapp_integration, client, str(company_id))
        if not integration:
            return False

        from app.services.whatsapp_service import get_whatsapp_service

        ok = await asyncio.to_thread(
            get_whatsapp_service().send_message,
            str(destino["destination_ref"]), texto, integration)
        return bool(ok)
    except Exception:  # noqa: BLE001
        # Aviso e efeito colateral da colheita, nao a colheita. Perder o aviso
        # e ruim; derrubar o job por causa dele e pior.
        return False


def _vencimento_iso(item: Dict[str, Any]) -> str:
    """Vencimento como aaaa-mm-dd, venha ele dd/mm/aaaa (Allianz) ou já ISO (HDI).

    Uma data em dois formatos ordenada como TEXTO poe 09/08/2026 antes de
    10/07/2026 — a divida mais nova na frente da mais velha. Normalizar aqui e o
    que faz a fila de entrega significar alguma coisa.
    """
    texto = str(item.get("vencimento") or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        return texto
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{2,4})\b", texto)
    if not m:
        return ""
    dia, mes, ano = m.groups()
    if len(ano) == 2:
        ano = f"20{ano}"
    return f"{ano}-{mes}-{dia}"


def vencido_ha_mais_de(item: Dict[str, Any], horas: int = HORAS_MINIMAS_ATRASO,
                       hoje: Optional[str] = None) -> bool:
    """A carencia, aplicada de novo do lado de ca.

    A journey ja pede ao portal so o que venceu ha mais de N horas. Esta e a
    segunda rede: portal novo pode ignorar o filtro de data e devolver a parcela
    de ontem assim mesmo, e quem paga o preco de cobrar cedo demais e a
    corretora, na frente do cliente dela.

    Sem data de vencimento legivel -> NAO envia. Nao saber ha quanto tempo
    venceu nunca pode virar permissao para cobrar.
    """
    venc = _vencimento_iso(item)
    if not venc:
        return False
    corte = (datetime.now(timezone.utc) - timedelta(hours=int(horas))).strftime("%Y-%m-%d")
    return venc <= corte


def ordenar_para_entrega(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A fila: divida mais VELHA primeiro.

    Nao e detalhe de estilo. Quando o teto de vazao interrompe a rodada no item
    7 de 20, os 13 que sobram voltam amanha — e a ordem decide quem esperou. A
    parcela mais antiga e a mais perto do cancelamento da apolice, entao e ela
    que sai primeiro. Empate desempata por portal e recibo, para a fila ser
    igual em duas execucoes seguidas (retomada previsivel).
    """
    return sorted(
        items,
        key=lambda i: (_vencimento_iso(i) or "9999-12-31",
                       str(i.get("portal") or ""),
                       str(i.get("recibo") or "")),
    )


def boletos_que_deram_certo(boletos: Optional[Iterable[Dict[str, Any]]]) -> set:
    """Os recibos que TEM arquivo no bucket. Nem todo boleto tentado virou PDF."""
    out = set()
    for b in boletos or []:
        if isinstance(b, dict) and b.get("ok") and str(b.get("storage_path") or "").strip():
            recibo = str(b.get("recibo") or "").strip()
            if recibo:
                out.add(recibo)
    return out


def fila_de_cobranca(items: List[Dict[str, Any]], *, horas: int = HORAS_MINIMAS_ATRASO,
                     boletos: Optional[Iterable[Dict[str, Any]]] = None) -> tuple:
    """Separa quem pode ser cobrado de quem nao pode, e diz POR QUE nao pode.

    Devolve `(fila_ordenada, retidos)`. Nada some: o que nao entra na fila entra
    no relatorio com motivo. Um inadimplente que desaparece sem explicacao e
    pior que um que nao foi cobrado — porque ninguem vai atras do que nao viu.

    `boletos` — o teste que faltava
    -------------------------------
    📊 Descoberto em 12/08/2026, na primeira rodada de producao da Tokio: de 4
    downloads, 3 deram PDF e 1 devolveu `ok: false`. Esse item **continuava
    entrando na fila** — porque a unica porta que existia era
    `sem_boleto_por_regra`, que so pega quem a SEGURADORA recusa por regra, nao
    quem falhou na hora de baixar.

    O segurado receberia a mensagem que termina em "Segue o boleto abaixo" com
    anexo nenhum. E o comentario da propria funcao ja avisava desse desfecho —
    so que o guarda cobria um caminho e o outro nao.

    Vale para TODAS as seguradoras, nao so a Tokio. Sem a lista de boletos o
    comportamento e o de antes (compatibilidade); com ela, o item vira tarefa
    humana com o motivo escrito.
    """
    com_arquivo = boletos_que_deram_certo(boletos) if boletos is not None else None
    fila: List[Dict[str, Any]] = []
    retidos: List[Dict[str, Any]] = []
    for item in items or []:
        if sem_boleto_por_regra(item):
            # DECISAO DO FOUNDER (12/08/2026): sem boleto, o robo NAO fala com o
            # segurado. Vai para a lista da equipe, e um humano decide o que
            # dizer. Manter na fila faria o robo mandar a mensagem padrao —
            # aquela que termina em "Segue o boleto abaixo" — sem anexo nenhum.
            retidos.append({**item, "retido_por":
                            "sem boleto (regra da seguradora) — tarefa para a equipe, "
                            "o segurado NAO recebe mensagem do sistema"})
        elif not _vencimento_iso(item):
            retidos.append({**item, "retido_por": "sem data de vencimento legivel"})
        elif not vencido_ha_mais_de(item, horas):
            retidos.append({**item, "retido_por": f"vencido ha menos de {horas}h (carencia)"})
        elif not _digits(item.get("whatsapp")):
            retidos.append({**item, "retido_por": f"sem telefone ({item.get('contact_status') or 'nao encontrado'})"})
        elif com_arquivo is not None and str(item.get("recibo") or "").strip() not in com_arquivo:
            retidos.append({**item, "retido_por":
                            "o boleto NAO foi baixado — tarefa para a equipe, o segurado "
                            "NAO recebe mensagem sem o arquivo"})
        else:
            fila.append(item)
    return ordenar_para_entrega(fila), retidos


def normalize_billing_config(config: Optional[Dict[str, Any]], delivery: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw = config if isinstance(config, dict) else {}
    delivery = delivery if isinstance(delivery, dict) else {}
    portals = _as_list(raw.get("portal_keys") or raw.get("selected_portals")) or DEFAULT_PORTAL_KEYS[:]
    send_mode = str(raw.get("send_mode") or "test").strip().lower()
    if send_mode not in {"test", "approval", "live", "none"}:
        send_mode = "test"
    test_number = _digits(raw.get("test_number") or delivery.get("number") or "")
    return {
        **raw,
        "kind": BILLING_KIND,
        "portal_keys": portals,
        "approval_required": bool(raw.get("approval_required", True)),
        "send_mode": send_mode,
        "test_number": test_number,
        "message_template": str(raw.get("message_template") or DEFAULT_MESSAGE_TEMPLATE).strip() or DEFAULT_MESSAGE_TEMPLATE,
        "attendant_name": _first_text(raw.get("attendant_name"), raw.get("nome_atendente"), default="nossa equipe"),
        "brokerage_name": _first_text(raw.get("brokerage_name"), raw.get("nome_corretora"), default="sua corretora"),
        "insurer_name": _first_text(raw.get("insurer_name"), raw.get("nome_seguradora"), default="ALLIANZ"),
        "max_boletos_por_execucao": _int_clamped(raw.get("max_boletos_por_execucao") or raw.get("max_boletos"), 10, 1, 50),
        "poll_timeout_seconds": _int_clamped(raw.get("poll_timeout_seconds"), 360, 30, 1800),
        "management_provider": str(raw.get("management_provider") or "infocap").strip().lower() or "infocap",
    }


def selected_portal_keys(config: Optional[Dict[str, Any]]) -> List[str]:
    return _as_list((config or {}).get("portal_keys")) or DEFAULT_PORTAL_KEYS[:]


def is_billing_routine(routine: Dict[str, Any]) -> bool:
    config = routine.get("config") if isinstance(routine, dict) else {}
    return isinstance(config, dict) and str(config.get("kind") or "").strip().lower() == BILLING_KIND


def customer_send_allowed(config: Dict[str, Any], env: Optional[Dict[str, str]] = None) -> bool:
    env = env if env is not None else os.environ
    cfg = normalize_billing_config(config)
    if cfg.get("send_mode") != "live":
        return False
    if cfg.get("approval_required"):
        return False
    return _truthy(env.get("BILLING_CUSTOMER_SEND_ENABLED"))


def test_send_number(config: Dict[str, Any], delivery: Optional[Dict[str, Any]] = None) -> str:
    cfg = normalize_billing_config(config, delivery)
    number = str(cfg.get("test_number") or "")
    if cfg.get("send_mode") != "test":
        return ""
    return number if len(number) >= 10 else ""


# Nome que o SEGURADO le na mensagem, por portal. Antes era um `if` unico para
# a Allianz — e qualquer seguradora nova viraria a palavra "seguradora" na
# mensagem ao cliente, o que parece defeito de sistema para quem recebe.
#
# A tabela mora aqui, e nao no banco, porque e TEXTO DE MENSAGEM: precisa ser
# revisavel em code review junto com o template, e nao mudar por baixo de uma
# corretora sem ninguem ver.
NOME_DA_SEGURADORA = {
    "allianz_corretor": "ALLIANZ",
    "hdi_corretor": "HDI SEGUROS",
    "porto_corretor": "PORTO SEGURO",
    "yelum_corretor": "YELUM",
    "tokiomarine_corretor": "TOKIO MARINE",
    "bradesco_corretor": "BRADESCO SEGUROS",
    "mapfre_corretor": "MAPFRE",
    "azul_corretor": "AZUL SEGUROS",
    "alfa_corretor": "ALFA SEGURADORA",
    "sulamerica_corretor": "SULAMERICA",
    "sompo_corretor": "SOMPO SEGUROS",
    "suhai_corretor": "SUHAI",
    "sura_corretor": "SURA",
    "zurich_corretor": "ZURICH",
    "segurosunimed_corretor": "SEGUROS UNIMED",
}


def _portal_insurer_name(item: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    explicit = _first_text(item.get("nome_seguradora"), item.get("seguradora"), item.get("insurer_name"))
    if explicit:
        return explicit
    portal = str(item.get("portal") or "").strip().lower()
    if portal in NOME_DA_SEGURADORA:
        return NOME_DA_SEGURADORA[portal]
    if portal.endswith("_corretor"):
        # Portal novo sem entrada: melhor o nome derivado da chave do que a
        # palavra generica. `sancor_corretor` -> "SANCOR" ainda e reconhecivel.
        return portal[: -len("_corretor")].replace("_", " ").upper()
    return _first_text(cfg.get("insurer_name"), default="seguradora")


def _insured_item_name(item: Dict[str, Any]) -> str:
    vehicle = item.get("vehicle") if isinstance(item.get("vehicle"), dict) else {}
    policy = item.get("policy") if isinstance(item.get("policy"), dict) else {}
    return _first_text(
        item.get("item_segurado"),
        item.get("veiculo"),
        vehicle.get("veiculo") if vehicle else "",
        item.get("bem"),
        item.get("risco"),
        item.get("ramo"),
        policy.get("ramo") if policy else "",
        item.get("modalidade"),
        default="seguro",
    )


class _MessageData(dict):
    def __missing__(self, key: str) -> str:
        return ""


def build_customer_message(item: Dict[str, Any], template: str, config: Optional[Dict[str, Any]] = None) -> str:
    cfg = normalize_billing_config(config or {})
    valor = item.get("valor")
    valor_txt = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(valor, (int, float)) else str(valor or "")
    segurado = _first_text(item.get("nome_segurado"), item.get("cliente_nome"), item.get("client_name"), default="cliente")
    apolice = _first_text(item.get("numero_apolice"), item.get("apolice_susep"), item.get("apolice"))
    parcela = _first_text(item.get("numero_parcela"), item.get("parcela"))
    primeiro_nome = _primeiro_nome(segurado)
    data = {
        "cliente_nome": segurado,
        "nome_segurado": segurado,
        "primeiro_nome": primeiro_nome,
        "nome_atendente": _first_text(cfg.get("attendant_name"), default="nossa equipe"),
        "nome_corretora": _first_text(cfg.get("brokerage_name"), default="sua corretora"),
        "nome_seguradora": _portal_insurer_name(item, cfg),
        "numero_parcela": parcela,
        "item_segurado": _insured_item_name(item),
        "numero_apolice": apolice,
        "vencimento": item.get("vencimento") or "",
        "valor": valor_txt,
        "apolice": apolice,
        "recibo": item.get("recibo") or "",
        "portal": item.get("portal") or "",
    }
    try:
        return template.format_map(_MessageData(data))
    except Exception:  # noqa: BLE001
        return DEFAULT_MESSAGE_TEMPLATE.format_map(_MessageData(data))


def _client(supabase):
    return getattr(supabase, "client", supabase)


def _portal_account(client, company_id: str, portal_key: str) -> Optional[Dict[str, Any]]:
    res = (
        client.table("portal_accounts")
        .select("id, portal_key, account_label, username, health")
        .eq("company_id", company_id)
        .eq("portal_key", portal_key)
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return dict(rows[0]) if rows else None


def _company_name(client, company_id: str) -> str:
    try:
        res = client.table("companies").select("company_name").eq("id", company_id).limit(1).execute()
        rows = res.data or []
        return str((rows[0] or {}).get("company_name") or "").strip() if rows else ""
    except Exception:  # noqa: BLE001
        return ""


def _enqueue_job(client, routine: Dict[str, Any], portal_key: str, account: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[str]:
    linha = {
        "company_id": str(routine["company_id"]),
        "portal_key": portal_key,
        "journey": "cobranca_sweep",
        "account_id": account.get("id"),
        "params": {
            "max_boletos": cfg["max_boletos_por_execucao"],
            "download_boletos": True,
            "require_downloads": True,
            "source": "routine_engine",
            "routine_id": str(routine.get("id") or ""),
        },
        "status": "queued",
    }

    # 🔴 SPEC-075 Bloco D — a linhagem entra SEM poder derrubar a cobrança.
    #
    # `operation_key` é coluna nova. O `smith-api` sobe com a imagem nova
    # assim que o deploy roda; a migration é aplicada por outra mão, em outro
    # momento. Entre os dois instantes, um insert que exige a coluna falha —
    # e o que falha aqui não é um recurso novo, é a varredura de cobrança
    # inteira da corretora.
    #
    # Por isso: tenta com, e se o banco recusar, repete sem. É o mesmo
    # raciocínio do `_candidatos_da_fila` no worker, e é o que "expand-first"
    # significa do lado do código, não só do lado do schema.
    ins = None
    try:
        ins = client.table("portal_jobs").insert(
            {**linha, "operation_key": "billing.overdue.list"}).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "[billing] insert com operation_key falhou (%s); repetindo sem a "
            "coluna — a migration da SPEC-075 provavelmente ainda nao rodou",
            type(e).__name__)
        ins = client.table("portal_jobs").insert(linha).execute()

    job_id = str(ins.data[0]["id"]) if ins and ins.data else None

    # SPEC-075 Bloco U — sombra. O caminho legado JÁ executou (o insert acima);
    # isto só registra o que a ponte teria escolhido. Nunca cria job, nunca
    # chama portal, e um erro aqui não pode custar a varredura.
    if job_id:
        try:
            from app.services.portals.sombra import observar, sombra_ligada

            if sombra_ligada():
                observar(client, job_id=job_id,
                         company_id=str(routine["company_id"]),
                         operation_key="billing.overdue.list",
                         portal_key_hint=portal_key,
                         portal_key_legado=portal_key,
                         journey_legada="cobranca_sweep")
        except Exception:  # noqa: BLE001
            pass
    return job_id


async def _poll_job(client, job_id: str, timeout_seconds: int) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: Dict[str, Any] = {"id": job_id, "status": "queued"}
    while time.monotonic() < deadline:
        res = (
            client.table("portal_jobs")
            .select("id, portal_key, journey, status, evidence, error, screenshots, finished_at")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        if res.data:
            last = dict(res.data[0])
            if str(last.get("status")) in TERMINAL_JOB_STATUSES:
                return last
        await asyncio.sleep(5)
    return {**last, "status": "timeout", "error": "portal_job nao terminou dentro do tempo limite"}


def _extract_items(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = job.get("evidence") if isinstance(job, dict) else {}
    if not isinstance(evidence, dict):
        return []
    items = evidence.get("inadimplentes")
    if not isinstance(items, list):
        captured = evidence.get("captured") if isinstance(evidence.get("captured"), dict) else {}
        items = captured.get("inadimplentes") if isinstance(captured, dict) else []
    out = []
    for item in items or []:
        if isinstance(item, dict):
            out.append({**item, "portal_job_id": job.get("id"), "portal": item.get("portal") or job.get("portal_key")})
    return out


def _extract_boletos(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = job.get("evidence") if isinstance(job, dict) else {}
    if not isinstance(evidence, dict):
        return []
    boletos = evidence.get("boletos")
    if not isinstance(boletos, list):
        return []
    return [b for b in boletos if isinstance(b, dict)]


async def _resolve_customer_phone(
    company_id: str,
    cpf_cnpj: str,
    provider_key: str,
    item: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    doc = _digits(cpf_cnpj)
    if len(doc) not in (11, 14):
        return {"phone": "", "status": "missing_document"}
    try:
        from app.core.database import create_async_supabase_client
        from app.providers.policy_data_provider import get_policy_data_provider

        internal_key = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
        provider = get_policy_data_provider(provider_key)
        if provider is None or not internal_key:
            return {"phone": "", "status": "provider_unavailable"}
        db = await create_async_supabase_client()
        result = await provider.lookup(
            company_id=company_id,
            document=doc,
            db=db,
            internal_key=internal_key,
            unmasked=True,
        )
        out = {"phone": _digits((result or {}).get("client_phone")), "status": (result or {}).get("status") or "unknown", "source": provider_key}
        vehicle_lookup = getattr(provider, "vehicle", None)
        policy_number = str((item or {}).get("apolice_susep") or (item or {}).get("apolice") or "").strip()
        if callable(vehicle_lookup):
            try:
                vehicle_result = await vehicle_lookup(
                    company_id=company_id,
                    document=doc,
                    policy_number=policy_number or None,
                    db=db,
                    internal_key=internal_key,
                )
                if isinstance(vehicle_result, dict) and vehicle_result.get("ok"):
                    vehicle = vehicle_result.get("vehicle") if isinstance(vehicle_result.get("vehicle"), dict) else {}
                    policy = vehicle_result.get("policy") if isinstance(vehicle_result.get("policy"), dict) else {}
                    client = vehicle_result.get("client") if isinstance(vehicle_result.get("client"), dict) else {}
                    if vehicle.get("veiculo"):
                        out["item_segurado"] = str(vehicle.get("veiculo") or "").strip()
                        out["vehicle"] = vehicle
                    insurer = policy.get("seguradora_abrev") or policy.get("seguradora")
                    if insurer:
                        out["seguradora"] = str(insurer).strip()
                    if client.get("telefone") and not out["phone"]:
                        out["phone"] = _digits(client.get("telefone"))
                    if client.get("nome"):
                        out["cliente_nome"] = str(client.get("nome") or "").strip()
            except Exception:  # noqa: BLE001
                pass
        return out
    except Exception as e:  # noqa: BLE001
        return {"phone": "", "status": f"provider_error:{type(e).__name__}"}


async def _attach_contacts(company_id: str, items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for item in items:
        contact = await _resolve_customer_phone(company_id, str(item.get("cpf_cnpj") or ""), cfg["management_provider"], item)
        merged = {**item, "whatsapp": contact.get("phone") or "", "contact_status": contact.get("status")}
        for field in ("item_segurado", "vehicle", "seguradora", "cliente_nome"):
            if contact.get(field) and not merged.get(field):
                merged[field] = contact.get(field)
        enriched.append(merged)
    return enriched


def _safe_items_for_payload(items: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    safe = []
    for item in items:
        safe.append({
            "portal": item.get("portal"),
            "portal_job_id": item.get("portal_job_id"),
            "cliente_nome": item.get("cliente_nome"),
            "cpf_cnpj": item.get("cpf_cnpj"),
            "whatsapp": item.get("whatsapp"),
            "contact_status": item.get("contact_status"),
            "apolice_susep": item.get("apolice_susep"),
            "recibo": item.get("recibo"),
            "vencimento": item.get("vencimento"),
            "valor": item.get("valor"),
            "parcela": item.get("parcela"),
            "item_segurado": _insured_item_name(item),
            "message": build_customer_message(item, cfg["message_template"], cfg),
        })
    return safe


def _create_approval_request(client, routine: Dict[str, Any], items: List[Dict[str, Any]], boletos: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Optional[str]:
    if not items:
        return None
    try:
        ins = client.table("approval_requests").insert({
            "company_id": str(routine["company_id"]),
            "subject_type": "billing_collection",
            "subject_id": str(routine.get("id") or ""),
            "action_type": "send_billing_whatsapp",
            "status": "pending",
            "risk_level": "high",
            "preview": {
                "routine_name": routine.get("name"),
                "items_count": len(items),
                "boletos_count": len([b for b in boletos if b.get("ok")]),
                "send_mode": cfg.get("send_mode"),
                "approval_required": cfg.get("approval_required"),
            },
            "request_payload": {
                "routine_id": str(routine.get("id") or ""),
                "portal_keys": cfg.get("portal_keys"),
                "items": _safe_items_for_payload(items, cfg),
                "boletos": boletos,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "requested_by_user_id": routine.get("created_by"),
        }).execute()
        return str(ins.data[0]["id"]) if ins.data else None
    except Exception:  # noqa: BLE001
        return None


def _find_whatsapp_integration(client, company_id: str) -> Optional[Dict[str, Any]]:
    res = (
        client.table("integrations")
        .select("*")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .execute()
    )
    # SPEC-063 Bloco D — o observador sai da lista ANTES da ordenação.
    #
    # Antes: rank = {"auxiliary": 0, "attendance": 1} e todo o resto valia 2 —
    # inclusive `observer`. Com `return rows[0] if rows else None`, a corretora
    # que só tem o observador ativo mandava COBRANÇA pelo número que existe
    # para ficar calado. 📊 Amandus e AutoFleet estavam exatamente assim.
    #
    # 🔴 SPEC-078 B — este é o ÚNICO lugar (até aqui) que pede `para="auxiliar"`.
    #
    # A cobrança é trabalho que a corretora instalou, nomeou e ligou. Se ela
    # ainda por cima autorizou o número pareado a ser o canal de saída
    # (`permite_envio_de_auxiliar`), o observador entra na lista — e SÓ nesse
    # caso. Sem a autorização, `pode_enviar` devolve False como sempre devolveu,
    # e a corretora continua sem canal: 📊 em 17/08/2026 as duas únicas
    # integrações ativas do banco são `observer`, e nenhuma está autorizada.
    #
    # O observador continua em ÚLTIMO na ordenação (cai no `2` do `rank.get`):
    # existindo um número de Auxiliar de verdade ou o de atendimento, é por ele
    # que a cobrança sai. A autorização abre uma porta de emergência, não vira
    # a primeira escolha.
    from app.services.integration_service import IntegrationService

    rows = [dict(r) for r in (res.data or [])
            if IntegrationService.pode_enviar(r, para=IntegrationService.ENVIO_DE_AUXILIAR)]
    rank = {"auxiliary": 0, "attendance": 1}
    # `.strip().lower()` porque `purpose` é texto livre — 📊 não existe CHECK
    # nesta coluna (medido em 17/08/2026 em `pg_constraint`). Um `"Auxiliary "`
    # gravado à mão cairia no fallback 2 e perderia a preferência em silêncio.
    rows.sort(key=lambda r: rank.get(str(r.get("purpose") or "").strip().lower(), 2))
    return rows[0] if rows else None


def _signed_boleto_url(client, storage_path: Any) -> str:
    path = str(storage_path or "").strip().lstrip("/")
    if not path:
        return ""
    try:
        res = client.storage.from_("portal-evidence").create_signed_url(path, TEST_LINK_TTL_SECONDS)
        if isinstance(res, dict):
            return str(res.get("signedURL") or res.get("signedUrl") or res.get("signed_url") or "")
        data = getattr(res, "data", None)
        if isinstance(data, dict):
            return str(data.get("signedURL") or data.get("signedUrl") or data.get("signed_url") or "")
    except Exception:  # noqa: BLE001
        return ""
    return ""


def _boletos_by_recibo(boletos: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for boleto in boletos:
        recibo = str(boleto.get("recibo") or "").strip()
        if recibo and recibo not in out:
            out[recibo] = boleto
    return out


def boleto_document_name(item: Dict[str, Any]) -> str:
    """Nome do arquivo que o cliente vê no WhatsApp. SEM PII (nome/CPF)."""
    recibo = _digits((item or {}).get("recibo"))
    return f"boleto-{recibo}.pdf" if recibo else "boleto.pdf"


def _format_test_message(item: Dict[str, Any], cfg: Dict[str, Any], boleto: Optional[Dict[str, Any]], boleto_url: str) -> str:
    lines = [
        "[TESTE AutoBrokers - Auxiliar de Cobranca]",
        build_customer_message(item, cfg["message_template"], cfg),
    ]
    if sem_boleto_por_regra(item):
        # Rede de seguranca: itens assim sao RETIDOS antes de chegar aqui. Se um
        # dia chegar, a simulacao diz a verdade em vez de prometer um anexo.
        lines.append("Boleto: nao existe (regra da seguradora). Este segurado NAO "
                     "deveria receber mensagem do robo — tarefa da equipe.")
    elif boleto_url:
        lines.append("Boleto: enviado como documento PDF em seguida.")
    elif boleto:
        lines.append(f"Boleto: nao anexado nesta simulacao ({boleto.get('reason') or 'sem link disponivel'}).")
    else:
        lines.append("Boleto: nao baixado nesta execucao de teste.")
    lines.append("Esta mensagem foi enviada somente para o numero de teste configurado, nao para o cliente real.")
    return "\n\n".join(lines)


def _already_sent_recibos(client, company_id: str, send_mode: str) -> set:
    """Recibos já enviados neste modo — para NÃO reenviar o mesmo boleto em dias
    seguintes (regra do founder). Cada parcela em atraso (recibo) é enviada 1x."""
    try:
        res = (
            client.table("billing_sent_log")
            .select("recibo")
            .eq("company_id", company_id)
            .eq("send_mode", send_mode)
            .execute()
        )
        return {str((r or {}).get("recibo") or "").strip() for r in (res.data or [])}
    except Exception:  # noqa: BLE001
        return set()


def _record_sent(client, company_id: str, item: Dict[str, Any], send_mode: str, doc_sent: bool) -> None:
    try:
        client.table("billing_sent_log").upsert(
            {
                "company_id": company_id,
                "recibo": str(item.get("recibo") or "").strip(),
                "portal_key": str(item.get("portal") or ""),
                "apolice_susep": str(item.get("apolice_susep") or ""),
                "cliente_nome": str(item.get("cliente_nome") or ""),
                "send_mode": send_mode,
                "doc_sent": bool(doc_sent),
            },
            on_conflict="company_id,recibo,send_mode",
        ).execute()
    except Exception:  # noqa: BLE001
        pass


async def _send_test_messages(
    client,
    routine: Dict[str, Any],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    blockers: List[str],
) -> List[Dict[str, Any]]:
    """Entrega a cobranca de CADA inadimplente elegivel, na ordem da fila.

    SPEC-069 — o teto de download nao e teto de envio
    =================================================
    Esta funcao percorria `items[:max_boletos_por_execucao]`. Os dois numeros
    tem nomes parecidos e significados diferentes: `max_boletos` limita quantos
    PDFs o worker baixa do portal numa entrada; quantas MENSAGENS saem quem
    limita e o governador de vazao, que conhece o teto do canal.

    Com os dois grudados, uma corretora com 12 atrasados e `max_boletos=10`
    perdia 2 inadimplentes **em silencio** — sem blocker, sem linha no relatorio,
    sem nada. Eles simplesmente nao existiam. Agora a fila inteira e percorrida,
    e quem nao couber HOJE aparece no relatorio e volta amanha de onde parou.

    O que torna "parar no meio" seguro e o `billing_sent_log`: so entra nele
    quem realmente recebeu. Nao ha fila nova nem estado novo para manter.
    """
    number = test_send_number(cfg, routine.get("delivery"))
    if not number or not items:
        return []
    integration = await asyncio.to_thread(_find_whatsapp_integration, client, str(routine["company_id"]))
    if not integration:
        blockers.append("modo teste: corretora sem canal WhatsApp ativo para enviar a simulacao")
        return []

    from app.services.whatsapp_service import get_whatsapp_service

    company_id = str(routine["company_id"])
    already = await asyncio.to_thread(_already_sent_recibos, client, company_id, "test")
    by_recibo = _boletos_by_recibo(boletos)
    sent: List[Dict[str, Any]] = []
    skipped = 0
    orcamento_s = float(GOVERNOR_WAIT_BUDGET_S)
    a_enviar = ordenar_para_entrega(items)
    for indice, item in enumerate(a_enviar):
        recibo_key = str(item.get("recibo") or "").strip()
        if recibo_key and recibo_key in already:
            skipped += 1
            continue

        # SPEC-063 Bloco C — o portao de vazao, UMA vez por segurado.
        liberado, motivo, esperou = await _esperar_o_governador(company_id, orcamento_s)
        orcamento_s -= esperou
        if not liberado:
            pendentes = len(a_enviar) - indice
            blockers.append(
                f"governador de envio: parei em {len(sent)} envio(s) — {motivo}. "
                f"{pendentes} item(ns) ficaram para a proxima execucao (nao foram "
                f"marcados como enviados, entao nao se perdem)")
            break

        boleto = by_recibo.get(recibo_key)
        boleto_url = await asyncio.to_thread(_signed_boleto_url, client, boleto.get("storage_path") if boleto else "")
        text = _format_test_message(item, cfg, boleto, boleto_url)
        entry = {
            "cliente_nome": item.get("cliente_nome"),
            "recibo": item.get("recibo"),
            "to_last4": number[-4:],
            "boleto_link": bool(boleto_url),
            "ok": False,
        }
        try:
            ok = await asyncio.to_thread(get_whatsapp_service().send_message, number, text, integration)
            entry["ok"] = bool(ok)
        except Exception as e:  # noqa: BLE001
            entry["error"] = type(e).__name__
            blockers.append(f"modo teste: falha ao enviar simulacao para ...{number[-4:]} ({type(e).__name__})")
        # Boleto como DOCUMENTO PDF (decisão de produto 2026-07-10): o cliente
        # recebe o arquivo, não um link que expira. Link assinado é só fallback.
        if entry["ok"] and boleto_url:
            doc_ok = await asyncio.to_thread(
                get_whatsapp_service().send_document,
                number,
                boleto_url,
                boleto_document_name(item),
                integration,
            )
            entry["document_sent"] = bool(doc_ok)
            if not doc_ok:
                try:
                    link_ok = await asyncio.to_thread(
                        get_whatsapp_service().send_message,
                        number,
                        f"(fallback de teste) Boleto por link temporario: {boleto_url}",
                        integration,
                    )
                    entry["link_fallback"] = bool(link_ok)
                except Exception:  # noqa: BLE001
                    entry["link_fallback"] = False
                blockers.append("modo teste: envio do PDF como documento falhou; usei link temporario como fallback")
        if entry["ok"]:
            await asyncio.to_thread(_record_sent, client, company_id, item, "test", bool(entry.get("document_sent")))
            # O contador de vazao vive em `platform_sends`, e ele so conta o
            # que foi registrado. Sem esta linha o governador espacaria as
            # mensagens e continuaria achando que o dia esta zerado — o teto
            # diario nunca fecharia.
            await _registrar_no_governador(company_id, number, item, cfg)
        sent.append(entry)
    if skipped:
        blockers.append(f"anti-duplicacao: {skipped} boleto(s) ja enviados anteriormente foram pulados (nao reenviamos o mesmo)")
    return sent


async def _esperar_o_governador(company_id: str, orcamento_s: float) -> tuple:
    """Pergunta ao governador se pode enviar. `(liberado, motivo, esperou_s)`.

    Tres respostas possiveis:

    * **libera** — o slot ja foi reservado; envie agora.
    * **manda esperar pouco** (espacamento, dentro do orcamento) — dorme e
      pergunta de novo. `asyncio.sleep`, nao `time.sleep`: congelar o event
      loop por 6 minutos derrubaria o atendimento de TODAS as corretoras.
    * **manda esperar muito** (janela fechada, domingo, teto do dia, freio
      puxado) — nao adianta dormir. A rotina para e relata.

    Falha ao CARREGAR o governador nao libera o envio. Era exatamente assim que
    a rajada de 100 mensagens saia: sem ninguem para dizer nao.
    """
    try:
        from app.services.platform_outbound import governar_envio
    except Exception as e:  # noqa: BLE001
        return False, f"governador indisponivel ({type(e).__name__}) — nada sai sem freio", 0.0

    esperou = 0.0
    while True:
        try:
            veredito = await governar_envio(str(company_id))
        except Exception as e:  # noqa: BLE001
            return False, f"governador nao respondeu ({type(e).__name__})", esperou
        if veredito.pode:
            return True, veredito.motivo, esperou
        espera = float(veredito.esperar_s or 0)
        if espera <= 0 or espera > (orcamento_s - esperou):
            return False, veredito.motivo, esperou
        await asyncio.sleep(espera)
        esperou += espera


async def _registrar_no_governador(company_id: str, number: str,
                                   item: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Anota o envio em `platform_sends` — a fonte duravel dos tetos."""
    try:
        from app.services.platform_outbound import record_platform_send

        parcela = _first_text(item.get("numero_parcela"), item.get("parcela"), default="?")
        seguradora = _portal_insurer_name(item, cfg)
        await record_platform_send(str(company_id), number, "billing",
                                   f"cobranca da parcela {parcela} ({seguradora})")
    except Exception:  # noqa: BLE001
        # Best-effort: perder o registro nao pode derrubar a rotina. Mas ele
        # subestima o contador, e subestimar teto e o lado perigoso — por isso
        # o espacamento (que vive no Redis, nao aqui) continua valendo.
        pass


def _format_report(
    *,
    routine: Dict[str, Any],
    cfg: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    blockers: List[str],
    approval_id: Optional[str],
    test_sends: List[Dict[str, Any]],
    fila: Optional[List[Dict[str, Any]]] = None,
    retidos: Optional[List[Dict[str, Any]]] = None,
) -> str:
    ok_boletos = [b for b in boletos if b.get("ok")]
    ok_test_sends = [s for s in test_sends if s.get("ok")]
    fila = fila if fila is not None else items
    retidos = retidos or []
    # Quem estava na fila e nao recebeu hoje: teto de vazao, janela fechada ou
    # ja cobrado antes. Volta na proxima execucao — mas so aparece se a gente
    # contar, e por isso a conta esta aqui e nao na cabeca de ninguem.
    pendentes = max(0, len(fila) - len(test_sends))
    lines = [
        f"Auxiliar de Cobranca - {routine.get('name') or 'Cobranca de boletos'}",
        f"Portais varridos: {', '.join(cfg.get('portal_keys') or [])}",
        f"Jobs: {len(jobs)} | inadimplentes: {len(items)} | boletos baixados: {len(ok_boletos)}",
        f"Podem ser cobrados: {len(fila)} | retidos: {len(retidos)} | "
        f"aguardando proxima execucao: {pendentes}",
    ]
    if approval_id:
        lines.append(f"Aprovacao pendente criada: {approval_id}")
    if cfg.get("send_mode") == "test":
        if ok_test_sends:
            last4 = str(ok_test_sends[0].get("to_last4") or "????")
            docs_sent = sum(1 for s in test_sends if s.get("document_sent"))
            lines.append(f"Modo teste ativo: {len(ok_test_sends)} simulacao(oes) enviada(s) para ...{last4}. Nenhum cliente real recebeu mensagem.")
            if docs_sent:
                lines.append(f"Boletos anexados como PDF: {docs_sent}.")
        else:
            lines.append("Modo teste ativo: nenhum cliente real recebeu mensagem.")
    # TAREFAS PARA GENTE. O robo avisa o segurado, mas quem converte debito em
    # boleto e a atendente — o botao que faz isso escreve no contrato e o robo
    # nao o toca. Sem esta secao, a conversao nunca acontece e o segurado fica
    # esperando o contato que foi prometido na mensagem.
    # As tarefas saem de ITEMS (a colheita inteira), nao da fila: quem nao tem
    # boleto foi RETIDO justamente para nao receber mensagem do robo, entao ele
    # nao esta na fila — e e exatamente ele que precisa de gente.
    tarefas = tarefas_para_a_equipe(items)
    if tarefas:
        lines.append(f"PRECISA DE VOCE - {len(tarefas)} parcela(s) em atraso SEM boleto:")
        for t in tarefas[:10]:
            lines.append(
                f"- {t.get('cliente_nome') or 'Cliente'} | apolice {t.get('apolice') or '?'} | "
                f"parcela {t.get('parcela') or '?'} | vcto {t.get('vencimento') or '?'} "
                f"-> converter no portal e falar com o segurado")
        lines.append("  (o robo NAO mandou mensagem para estes; quem fala e voce)")

    if blockers:
        lines.append("Bloqueios/avisos:")
        lines.extend([f"- {b}" for b in blockers[:10]])
    if items:
        lines.append("Clientes encontrados:")
        for item in items[:20]:
            valor = item.get("valor")
            valor_txt = f"R$ {valor:.2f}" if isinstance(valor, (int, float)) else str(valor or "valor nao informado")
            phone = item.get("whatsapp") or f"sem telefone ({item.get('contact_status') or 'n/a'})"
            lines.append(
                f"- {item.get('cliente_nome') or 'Cliente'} | CPF/CNPJ {item.get('cpf_cnpj') or '?'} | "
                f"vcto {item.get('vencimento') or '?'} | {valor_txt} | WhatsApp: {phone}"
            )
    else:
        lines.append("Nenhum inadimplente consolidado nesta execucao.")
    return "\n".join(lines)[:4000]


# ==========================================================================
# SPEC-078 F.5 — o trabalho da cobrança vira um Artifact de primeira classe
# ==========================================================================
#
# 📊 MEDIDO EM 17/08/2026, antes de escrever esta seção:
#
#     ocorrências de "artifact" neste arquivo        0
#     work_runs com source_type='routine'            0
#     artifacts produzidos pelo Checklist das 6h    36  (kind='report')
#
# O Checklist das 6h produz peça desde julho; a Cobrança — que varre portal de
# seguradora, baixa boleto e monta fila de atendimento — devolvia uma STRING.
# String não se abre, não se guarda com marca da corretora, não se manda para
# ninguém e some do histórico junto com a linha de `routine_runs`.
#
# 🔴 NENHUM PUBLISHER NOVO (CLAUDE.md §5). O caminho é o mesmo do Checklist,
# lido em `intelligence/workflows.py:131-157`:
#
#     ArtifactService.criar(...) → renderizar(version_id) → publicar(version_id)
#
# `criar` aceita `work_run_id=None`, então F.5 NÃO exige criar Work Run — que
# seria o segundo motor que a SPEC proíbe.
#
# ⚠️ O QUE ESTA PEÇA NÃO CARREGA, E POR QUÊ
#
# Sem CPF/CNPJ e sem telefone. Um artifact pode virar `artifact_shares` — link
# público com validade de 30 dias — e documento com CPF atrás de um token de
# URL é vazamento com prazo, não entrega. O relatório integral, com os dois,
# fica em `routine_runs.output_full` (F.4), atrás de sessão e de
# `.eq('company_id')`. Duas peças, dois níveis de exposição, de propósito.


def _mascarar_documento(valor: Any) -> str:
    """CPF/CNPJ reduzido aos últimos dígitos. Serve para conferir, não para usar.

    O corretor precisa distinguir dois "João Silva" na mesma lista; para isso
    bastam quatro dígitos. O documento inteiro só existe no relatório integral.
    """
    d = _digits(valor)
    return f"...{d[-4:]}" if len(d) >= 4 else ""


def compor_peca_da_cobranca(
    *,
    routine: Dict[str, Any],
    cfg: Dict[str, Any],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    fila: List[Dict[str, Any]],
    retidos: List[Dict[str, Any]],
    tarefas: List[Dict[str, Any]],
    blockers: List[str],
    test_sends: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Execução da cobrança → blocos do Artifact Hub. Pura, e não recalcula nada.

    Todo número aqui já foi contado por `execute_billing_collection_routine`. Se
    esta função contasse qualquer coisa por conta própria, a peça poderia
    divergir do relatório de texto da mesma execução — e o corretor descobriria
    isso comparando os dois na frente de alguém.
    """
    portais = [NOME_DA_SEGURADORA.get(p, p) for p in (cfg.get("portal_keys") or [])]
    ok_boletos = [b for b in boletos if b.get("ok")]
    enviados = [s for s in test_sends if s.get("ok")]
    pendentes = max(0, len(fila) - len(test_sends))
    hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    blocos: List[Dict[str, Any]] = [{
        "block": "cover",
        "props": {
            "eyebrow": "Cobrança",
            "title": str(routine.get("name") or "Cobrança de boletos atrasados"),
            "period": hoje,
            "verdict": (
                f"{len(items)} parcela(s) em atraso na varredura de "
                f"{', '.join(portais) or 'nenhum portal'}."),
            "headline_label": "precisam de uma pessoa",
            "headline_value": str(len(tarefas)),
        },
    }]

    indicadores = [
        {"label": "Inadimplentes", "value": str(len(items))},
        {"label": "Boletos baixados", "value": str(len(ok_boletos))},
        {"label": "Podem ser cobrados", "value": str(len(fila))},
        {"label": "Retidos", "value": str(len(retidos))},
        {"label": "Aguardando a próxima", "value": str(pendentes)},
    ]
    if tarefas:
        # Primeiro cartão: é o único número que não se resolve sozinho amanhã.
        indicadores.insert(0, {"label": "Precisa de você", "value": str(len(tarefas))})
    blocos.append({"block": "kpis", "props": {"title": "A varredura de hoje",
                                              "items": indicadores}})

    modo = str(cfg.get("send_mode") or "none")
    if modo == "test":
        blocos.append({"block": "callout", "props": {
            "tone": "info", "title": "Modo teste",
            "text": (f"{len(enviados)} simulação(ões) enviada(s) para o número de "
                     f"teste. Nenhum cliente real recebeu mensagem."),
        }})
    elif modo == "none":
        blocos.append({"block": "callout", "props": {
            "tone": "info", "title": "Somente relatório",
            "text": "Nenhuma mensagem foi enviada ao cliente nesta execução.",
        }})

    if tarefas:
        blocos.append({"block": "actions", "props": {
            "eyebrow": "Precisa de você",
            "title": "Parcelas em atraso SEM boleto",
            "items": [{
                "title": str(t.get("cliente_nome") or "Cliente"),
                "detail": (f"apólice {t.get('apolice') or '?'} · parcela "
                           f"{t.get('parcela') or '?'} — converter no portal e "
                           f"falar com o segurado"),
                "due": str(t.get("vencimento") or ""),
                "impact": "o robô não falou com este",
            } for t in tarefas[:8]],
        }})

    if items:
        blocos.append({"block": "table", "props": {
            "eyebrow": "Carteira",
            "title": "Inadimplentes encontrados",
            "columns": [
                {"key": "cliente", "label": "Cliente"},
                {"key": "doc", "label": "CPF/CNPJ"},
                {"key": "seguradora", "label": "Seguradora"},
                {"key": "vencimento", "label": "Vencimento"},
                {"key": "valor", "label": "Valor", "align": "right", "format": "currency"},
                {"key": "situacao", "label": "Situação", "pill": True},
            ],
            # 🔴 `doc` é MASCARADO. Ver o comentário do bloco desta seção.
            "rows": [{
                "cliente": str(i.get("cliente_nome") or "Cliente"),
                "doc": _mascarar_documento(i.get("cpf_cnpj")),
                "seguradora": _portal_insurer_name(i, cfg),
                "vencimento": str(i.get("vencimento") or "?"),
                "valor": i.get("valor"),
                "situacao": str(i.get("retido_por") or "na fila de cobrança"),
                "situacao_tone": "warning" if i.get("retido_por") else "positive",
            } for i in (retidos + fila)[:40]],
        }})

    if blockers:
        blocos.append({"block": "prose", "props": {
            "eyebrow": "Transparência",
            "title": "O que não saiu, e por quê",
            # Portal que ficou de fora tem de aparecer: a corretora que lê
            # "3 portais varridos" sem saber que o quarto falhou acha que a
            # carteira está em dia.
            "text": "\n".join(f"- {b}" for b in blockers[:12]),
        }})

    blocos.append({"block": "sources", "props": {"items": [
        {"label": "Portais de seguradora",
         "detail": ", ".join(portais) or "nenhum",
         "as_of_label": hoje},
        {"label": "Contatos",
         "detail": f"sistema de gestão ({cfg.get('management_provider') or 'n/d'})",
         "as_of_label": hoje},
    ]}})
    blocos.append({"block": "footer", "props": {
        "disclaimer": "Documento interno. Não contém CPF/CNPJ nem telefone de segurado.",
    }})
    return blocos


def _gerar_artefato_da_cobranca(supabase, company_id: str, routine: Dict[str, Any],
                                titulo: str, subtitulo: str, resumo: str,
                                payload: Dict[str, Any],
                                blocos: List[Dict[str, Any]]) -> Optional[str]:
    """Cria, renderiza e publica a peça. Devolve o id, ou None.

    Roda em thread porque `ArtifactService` é síncrono — é o mesmo cliente
    Supabase bloqueante que o resto deste arquivo já usa via `asyncio.to_thread`.
    """
    from app.services.artifacts.service import ArtifactService

    servico = ArtifactService(supabase)
    r = servico.criar(
        company_id=company_id,
        title=titulo,
        template_key="financial.billing_collection",
        payload=payload,
        composition=blocos,
        subtitle=subtitulo,
        summary=resumo,
        kind="report",
        origin="routine",
        # `work_run_id=None`: a cobrança não roda dentro de um Work Run hoje
        # (📊 zero `work_runs` com source_type='routine'). O Hub aceita, e
        # inventar um Work Run só para preencher a coluna seria o segundo motor
        # que a SPEC-078 e o CLAUDE.md §5 proíbem.
        work_run_id=None,
        subject_ref={"kind": "routine", "id": str(routine.get("id") or "")},
    )
    versao = (r.get("version") or {}).get("id")
    if versao:
        servico.renderizar(company_id=company_id, version_id=versao)
        servico.publicar(company_id=company_id, version_id=versao)
    return ((r.get("artifact") or {}).get("id")) or None


# ==========================================================================
# SPEC-078 F.7 — os boletos guardados ganham prazo (escrito e DESLIGADO)
# ==========================================================================
#
# 📊 MEDIDO EM 17/08/2026 em `storage.objects`:
#
#     portal-evidence   62 objetos · 5977 kB · mais antigo 11/07/2026
#                       5 com mais de 30 dias · 0 com mais de 60 · 0 com 90
#
# São boletos de terceiros — dado financeiro de segurado — guardados desde
# julho sem NENHUMA rotina de descarte. `20260708_01` criou o bucket privado e
# parou ali: privado resolve quem lê, não resolve por quanto tempo existe.
#
# 🔴 ESTA SPEC NÃO APAGA NADA (§15). A purga nasce escrita e DESLIGADA. Ligar é
# decisão do Founder, com o prazo definido por ele — registrado em
# PENDENCIAS.md com dono 🧑. É a regra do CLAUDE.md §11.1: deixar pronto e
# desligado é aceitável; deixar pronto e não anotado, não.
#
# A política, escrita para caber numa decisão de uma linha:
#
#     O QUE      PDFs de boleto e evidências de portal em `portal-evidence`
#     CAMINHO    {company_id}/{portal_key}/{job_id}/boleto-*.pdf
#     PARA QUÊ   provar ao segurado o que foi cobrado e anexar o boleto
#     PRAZO      PORTAL_EVIDENCE_RETENTION_DAYS, padrão 90 dias
#     POR QUÊ 90 o boleto vence em ~30 e a discussão sobre uma cobrança morre
#                em ~60; 90 dá folga sem virar arquivo morto
#     LIGADO?    NÃO — PORTAL_EVIDENCE_PURGE_ENABLED começa em false

PORTAL_EVIDENCE_BUCKET = "portal-evidence"
PORTAL_EVIDENCE_RETENTION_DAYS = int(os.getenv("PORTAL_EVIDENCE_RETENTION_DAYS", "90"))


def evidence_purge_enabled(env: Optional[Dict[str, str]] = None) -> bool:
    """A purga só roda se alguém a LIGAR. Ausência de variável é 'não'.

    Lista de permissão, não de proibição: uma variável escrita errada
    ('sim', 'True ', '1x') deixa a purga desligada. Errar para o lado de não
    apagar boleto de segurado é grátis; errar para o outro não tem volta.
    """
    fonte = env if env is not None else os.environ
    return str(fonte.get("PORTAL_EVIDENCE_PURGE_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}


def contar_evidencias_por_idade(supabase, dias: Optional[int] = None) -> List[Dict[str, Any]]:
    """Quantos boletos cada corretora tem guardados, e quantos passaram do prazo.

    SOMENTE LEITURA. Chama `public.portal_evidence_por_idade(dias)` (migration
    20260817_04), que agrupa pela primeira pasta do caminho — que é o
    `company_id`. Uma política de retenção que não sabe de quem é o arquivo não
    é política, é faxina.
    """
    prazo = int(dias if dias is not None else PORTAL_EVIDENCE_RETENTION_DAYS)
    client = _client(supabase)
    try:
        res = client.rpc("portal_evidence_por_idade", {"dias": prazo}).execute()
        return list(res.data or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("[EVIDENCE] contagem por idade indisponivel: %s", type(e).__name__)
        return []


def purgar_evidencias_antigas(supabase, *, dias: Optional[int] = None,
                              company_id: Optional[str] = None,
                              dry_run: bool = True) -> Dict[str, Any]:
    """Apaga do bucket os objetos mais velhos que o prazo. NASCE DESLIGADA.

    Três travas, e as três precisam ceder ao mesmo tempo:

        1. `PORTAL_EVIDENCE_PURGE_ENABLED` ligado (padrão: desligado)
        2. `dry_run=False` explícito (padrão: True — só conta)
        3. prazo positivo

    Sem as três, a função devolve o que APAGARIA e não toca em nada. É a mesma
    forma do §11.1: pronto e desligado.
    """
    prazo = int(dias if dias is not None else PORTAL_EVIDENCE_RETENTION_DAYS)
    client = _client(supabase)
    ligada = evidence_purge_enabled()
    corte = (datetime.now(timezone.utc) - timedelta(days=max(prazo, 1))).isoformat()

    resultado: Dict[str, Any] = {
        "bucket": PORTAL_EVIDENCE_BUCKET, "prazo_dias": prazo, "corte": corte,
        "habilitada": ligada, "dry_run": dry_run or not ligada,
        "candidatos": 0, "apagados": 0, "alvos": [],
    }

    try:
        q = (client.table("objects").schema("storage")
             .select("name, created_at")
             .eq("bucket_id", PORTAL_EVIDENCE_BUCKET)
             .lt("created_at", corte))
        if company_id:
            # O caminho começa pelo dono. Purgar por corretora é o que permite
            # ligar isto para uma e não para todas.
            q = q.like("name", f"{company_id}/%")
        alvos = [str(o.get("name") or "") for o in ((q.execute()).data or []) if o.get("name")]
    except Exception as e:  # noqa: BLE001
        logger.warning("[EVIDENCE] nao consegui listar candidatos: %s", type(e).__name__)
        return resultado

    resultado["candidatos"] = len(alvos)
    resultado["alvos"] = alvos[:20]

    if not ligada or dry_run or not alvos:
        # O caminho normal HOJE. Nada é apagado, e o número fica registrado.
        logger.info("[EVIDENCE] purga NAO executada (habilitada=%s, dry_run=%s): "
                    "%s objeto(s) passariam do prazo de %s dias",
                    ligada, dry_run, len(alvos), prazo)
        return resultado

    try:
        client.storage.from_(PORTAL_EVIDENCE_BUCKET).remove(alvos)
        resultado["apagados"] = len(alvos)
        logger.info("[EVIDENCE] purga executada: %s objeto(s) apagados (>%s dias)",
                    len(alvos), prazo)
    except Exception as e:  # noqa: BLE001
        logger.error("[EVIDENCE] purga falhou: %s", type(e).__name__)
    return resultado


async def execute_billing_collection_routine(supabase, routine: Dict[str, Any]) -> str:
    client = _client(supabase)
    company_id = str(routine.get("company_id") or "")
    cfg = normalize_billing_config(routine.get("config"), routine.get("delivery"))
    if cfg.get("brokerage_name") == "sua corretora" and company_id:
        name = await asyncio.to_thread(_company_name, client, company_id)
        if name:
            cfg["brokerage_name"] = name
    blockers: List[str] = []
    job_ids: List[str] = []

    # NENHUMA SEGURADORA CAI EM SILENCIO.
    #
    # Um portal pode ficar de fora por tres motivos, e os tres viram linha no
    # relatorio. O que nao pode e sumir: a corretora que ve "3 portais varridos"
    # sem saber que o quarto nao rodou acha que a carteira dela esta em dia.
    sei_varrer = set(_portais_que_sei_varrer())
    for portal_key in selected_portal_keys(cfg):
        try:
            if portal_key not in sei_varrer:
                blockers.append(
                    f"portal {portal_key}: selecionado, mas ainda NAO tem automacao de cobranca "
                    f"— nenhum inadimplente deste portal entrou nesta execucao")
                continue
            account = await asyncio.to_thread(_portal_account, client, company_id, portal_key)
            if not account:
                blockers.append(
                    f"portal {portal_key}: sem credencial conectada "
                    f"— cadastre em Personalizacao > Conectores > Portais")
                continue
            job_id = await asyncio.to_thread(_enqueue_job, client, routine, portal_key, account, cfg)
            if job_id:
                job_ids.append(job_id)
            else:
                blockers.append(f"portal {portal_key}: falha ao enfileirar job")
        except Exception as e:  # noqa: BLE001
            blockers.append(f"portal {portal_key}: {type(e).__name__}")

    jobs: List[Dict[str, Any]] = []
    for job_id in job_ids:
        jobs.append(await _poll_job(client, job_id, int(cfg["poll_timeout_seconds"])))

    for job in jobs:
        status = str(job.get("status") or "")
        if status == "needs_human":
            blockers.append(f"portal {job.get('portal_key')}: precisa de humano ({(job.get('evidence') or {}).get('message') or 'revisao'})")
        if status in {"failed", "timeout"}:
            blockers.append(f"portal {job.get('portal_key')}: {status} {job.get('error') or ''}".strip())

    items: List[Dict[str, Any]] = []
    boletos: List[Dict[str, Any]] = []
    for job in jobs:
        items.extend(_extract_items(job))
        boletos.extend(_extract_boletos(job))

    items = await _attach_contacts(company_id, items, cfg) if items else []

    # A FILA. Colher e uma coisa; poder cobrar e outra. Aqui os inadimplentes
    # viram (a) fila ordenada do mais velho para o mais novo e (b) retidos, cada
    # um com o motivo escrito. O relatorio mostra os dois — quem foi cobrado e
    # quem nao foi, e por que.
    fila, retidos = fila_de_cobranca(
        items,
        horas=int(cfg.get("horas_minimas_atraso") or HORAS_MINIMAS_ATRASO),
        boletos=boletos,  # sem o arquivo no bucket, o segurado nao recebe nada
    )
    for motivo, quantos in sorted(
        {r.get("retido_por", "?"): sum(1 for x in retidos if x.get("retido_por") == r.get("retido_por"))
         for r in retidos}.items()
    ):
        blockers.append(f"{quantos} inadimplente(s) nao cobrado(s): {motivo}")

    approval_id = None
    wants_approval = cfg.get("send_mode") == "approval" or (cfg.get("send_mode") == "live" and cfg.get("approval_required"))
    if fila and wants_approval:
        approval_id = await asyncio.to_thread(_create_approval_request, client, routine, fila, boletos, cfg)
        if not approval_id:
            blockers.append("nao consegui criar pedido de aprovacao")
    test_sends = await _send_test_messages(client, routine, fila, boletos, cfg, blockers) if fila else []

    # OS AVISOS AO GRUPO HUMANO. Saem depois da entrega, porque o resumo precisa
    # saber quantos sairam. Nenhum deles fala com segurado.
    from app.services import billing_avisos as avisos

    nome_corretora = str(cfg.get("brokerage_name") or "Corretora")
    tarefas = tarefas_para_a_equipe(items, cfg)
    if tarefas:
        enviado = await avisar_suporte_humano(
            client, company_id, avisos.aviso_de_tarefas(nome_corretora, tarefas), "tarefas")
        if not enviado:
            blockers.append(
                f"{len(tarefas)} tarefa(s) para a equipe NAO foram avisadas no WhatsApp "
                f"— a corretora nao tem grupo de suporte cadastrado (veja abaixo)")

    # O guarda: portal que respondeu mas nao deixou ler. Vai para a EQUIPE,
    # nunca para o segurado — ele nao tem o que fazer com essa informacao.
    for job in jobs:
        estagio = str(((job.get("evidence") or {}).get("captured") or {}).get("stage")
                      or (job.get("evidence") or {}).get("stage") or "")
        if estagio in ("lista_nao_lida", "sem_linhas_extraiveis", "inadimplentes_nao_localizado"):
            await avisar_suporte_humano(
                client, company_id,
                avisos.aviso_de_portal(
                    nome_corretora,
                    NOME_DA_SEGURADORA.get(str(job.get("portal_key") or ""), str(job.get("portal_key") or "")),
                    "nao consegui ler a lista de parcelas"),
                "portal")

    sem_telefone = [r for r in retidos if "sem telefone" in str(r.get("retido_por") or "")]
    await avisar_suporte_humano(
        client, company_id,
        avisos.aviso_de_resumo(
            nome_corretora,
            seguradoras=[NOME_DA_SEGURADORA.get(p, p) for p in (cfg.get("portal_keys") or [])],
            enviados=len([s for s in test_sends if s.get("ok")]),
            pendentes=max(0, len(fila) - len(test_sends)),
            tarefas=len(tarefas),
            sem_telefone=sem_telefone),
        "resumo")
    if items and cfg.get("send_mode") == "approval":
        blockers.append("modo aprovacao: mensagens aguardam aprovacao antes de qualquer envio ao cliente")
    elif items and cfg.get("send_mode") == "none":
        blockers.append("modo somente relatorio: nenhuma mensagem sera enviada ao cliente")
    elif items and cfg.get("send_mode") == "live" and not customer_send_allowed(cfg):
        blockers.append("envio ao cliente bloqueado por configuracao/gate de seguranca")
    elif items and cfg.get("send_mode") == "live":
        # SPEC-045 + SPEC-063 Bloco C: quando o envio live for homologado, ele
        # DEVE sair por app.services.platform_outbound.send_to_client_guarded
        # — que hoje ja carrega as tres guardas de uma vez: fila de cortesia
        # (nao atropela atendimento), governador de vazao (espacamento, tetos,
        # janela, freio) e registro em platform_sends. Nunca por send_message
        # direto: e o send_message direto que ignora as tres.
        blockers.append("envio direto ao cliente permanece desativado nesta fase de homologacao")

    # SPEC-078 F.5 — a execução vira Artifact ANTES de devolver o texto.
    #
    # Em `try` mudo de propósito: o relatório de texto é o que o routine_engine
    # entrega e o que o corretor recebe no WhatsApp. Se o Artifact Hub estiver
    # fora do ar, a cobrança do dia não pode deixar de ser entregue por causa da
    # peça bonita. É a mesma decisão que o Checklist das 6h já toma
    # (`workflows.py:123` — "peça não gerada", warning, segue).
    try:
        # `tarefas` já foi contado acima, para o aviso ao grupo humano. Contar de
        # novo abriria a porta para a peça e o relatório discordarem sobre
        # quantas pessoas precisam ser chamadas.
        artifact_id = await asyncio.to_thread(
            _gerar_artefato_da_cobranca,
            supabase,
            company_id,
            routine,
            f"Cobrança de {datetime.now(timezone.utc).strftime('%d/%m/%Y')}",
            ", ".join(NOME_DA_SEGURADORA.get(p, p) for p in (cfg.get("portal_keys") or [])),
            (f"{len(items)} parcela(s) em atraso · {len(fila)} na fila · "
             f"{len(tarefas)} precisam de uma pessoa"),
            # ⚠️ O payload é a MESMA lista mascarada que já vai para o pedido de
            # aprovação, menos o documento. `_safe_items_for_payload` guarda
            # `cpf_cnpj` e `whatsapp` inteiros — e o payload de um artifact é
            # legível por qualquer leitor do artefato, inclusive por um link
            # compartilhado. Aqui só entram contagens e nomes.
            {
                "portals": list(cfg.get("portal_keys") or []),
                "found": len(items), "queue": len(fila), "held": len(retidos),
                "human_tasks": len(tarefas), "blockers": blockers[:12],
                "send_mode": cfg.get("send_mode"),
            },
            compor_peca_da_cobranca(
                routine=routine, cfg=cfg, items=items, boletos=boletos,
                fila=fila, retidos=retidos, tarefas=tarefas,
                blockers=blockers, test_sends=test_sends),
        )
        if artifact_id:
            logger.info("[COBRANCA] peca publicada no Artifact Hub: %s", artifact_id)
    except Exception as exc:  # noqa: BLE001
        # Sem PII no log — nem o nome da corretora. Só o tipo do erro.
        logger.warning("[COBRANCA] peca nao gerada: %s", type(exc).__name__)

    return _format_report(
        routine=routine,
        cfg=cfg,
        jobs=jobs,
        items=items,
        boletos=boletos,
        blockers=blockers,
        approval_id=approval_id,
        test_sends=test_sends,
        fila=fila,
        retidos=retidos,
    )
