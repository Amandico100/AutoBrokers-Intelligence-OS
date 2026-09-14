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
import functools
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

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


# 🔴 A REGRA DO TELEFONE É UMA SÓ, e ela mora em `app.telefone_br`
# (P-097-TELEFONE-BR-DUPLICADO). Este arquivo NÃO reescreve o nono dígito nem a
# normalização: ele importa.
#
# ⚠️ O `except` não é uma segunda regra. `_digits` acima é literalmente "só os
# dígitos" — a mesma normalização, que já estava aqui desde a SPEC-023 — e o
# fallback existe por um motivo medido: `test_a_sessao_caida_volta_e_o_aviso…`
# carrega este módulo com um pacote `app` SINTÉTICO (`__path__ = []`), onde
# nenhum submódulo resolve. Sem ele, um guarda verde ficaria vermelho por causa
# do carregador do próprio guarda, e não por causa do produto.
try:
    from app.telefone_br import so_digitos
except Exception:  # noqa: BLE001
    so_digitos = _digits


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


async def avisar_suporte_humano(client, company_id: str, texto: str, rotulo: str,
                                *, suprimir: bool = False) -> bool:
    """Manda o aviso para o grupo de suporte humano DESTA corretora.

    🔴 `suprimir=True` — SPEC-EXTRA-001 §0.3. O canário roda num tenant REAL, e
    📊 a Resulta tem um grupo de WhatsApp de verdade em
    `human_support_destinations` (`…@g.us`). Um teste autorizado entre dois
    telefones do Founder não pode mandar "3 parcelas em atraso" para o grupo de
    trabalho da corretora — o item é sintético, e o aviso seria uma informação
    falsa numa conversa de gente. Keyword-only e com default `False`: os três
    chamadores continuam com o comportamento de hoje quando não há canário.

    O agente nunca sabe o nome do grupo. Ele diz "avise o suporte desta
    corretora" e o sistema resolve em `human_support_destinations` — assim mil
    corretoras tem mil destinos e zero codigo especifico, e trocar de grupo e
    mexer num campo de tela.

    Sem destino cadastrado NAO e erro: o aviso ja esta no relatorio da rotina,
    e o relatorio diz que faltou destino. Falhar aqui derrubaria a colheita
    inteira por causa de um campo em branco.
    """
    if suprimir:
        logger.info("[COBRANCA] aviso ao grupo humano SUPRIMIDO (canario): %s", rotulo)
        return False
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
                     boletos: Optional[Iterable[Dict[str, Any]]] = None,
                     modo_teste: bool = False) -> tuple:
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
        elif not modo_teste and not _digits(item.get("whatsapp")):
            # 🔴 EM MODO TESTE O TELEFONE DO SEGURADO NAO E USADO.
            #
            # 📊 Medido em 17/08/2026: a Allianz e a HDI devolveram 5
            # inadimplentes com 5 boletos baixados, e TRES foram retidos por
            # "sem telefone" — um telefone que, em modo teste, o codigo nem
            # consulta. `_send_test_messages` manda tudo para `test_number`
            # (`billing_collection.py:869`), que e o unico destino possivel
            # naquele modo.
            #
            # Ou seja: o teste do Founder foi de 5 boletos para 2 por causa de
            # uma regra que so faz sentido no envio REAL. A busca do telefone
            # na InfoCap e assunto da SPEC-079, quando a mensagem passar a ir
            # para o segurado. Ate la, ela nao pode reduzir o que se testa.
            retidos.append({**item, "retido_por": f"sem telefone ({item.get('contact_status') or 'nao encontrado'})"})
        elif com_arquivo is not None and str(item.get("recibo") or "").strip() not in com_arquivo:
            retidos.append({**item, "retido_por":
                            "o boleto NAO foi baixado — tarefa para a equipe, o segurado "
                            "NAO recebe mensagem sem o arquivo"})
        else:
            fila.append(item)
    return ordenar_para_entrega(fila), retidos


# ==========================================================================
# SPEC-EXTRA-001.6 · B1.2 — UMA MENSAGEM POR SEGURADO, N BOLETOS
# ==========================================================================
#
# 📊 Medido em 13/09/2026 sobre o acervo das execuções de 10 e 11/09 (os dois
# dias trouxeram os MESMOS 7 itens): 4 dos 7 têm o MESMO CNPJ, a mesma
# seguradora e o mesmo vencimento. A atendente recebeu QUATRO abordagens para a
# mesma pessoa. 6 dos 7 itens trazem documento (86%); a HDI devolve `""` por
# desenho, e é para ela que existe o fallback por nome.
#
# 🔴 DUAS CHAVES, E ELAS SÃO DIFERENTES DE PROPÓSITO. A confusão entre as duas é
# o que produziria "o segurado sem CPF nunca é limitado" (ou o contrário: o
# mesmo segurado cobrado em duas seguradoras no mesmo dia). Uma regra por
# pergunta: `segurado_chave` responde QUEM; `chave_do_grupo` responde
# QUEM + ONDE, que é o que cabe numa MESMA mensagem.


def segurado_chave(item: Dict[str, Any]) -> str:
    """QUEM é o segurado — independente de seguradora. É o que vai para o ledger.

    🔴 O nome da coluna é `segurado_chave`, e NÃO `cpf_cnpj`, porque o valor nem
    sempre É um documento (CLAUDE.md §12.1: campo cujo nome mente reinfecta todo
    leitor seguinte). O prefixo diz de onde a identidade veio, e é isso que a
    mensagem de retenção mostra para a pessoa poder discordar.

    ⚠️ Sem documento, a identidade é o NOME normalizado. Isso pode unir dois
    homônimos reais e segurar uma cobrança legítima por N dias — e é o erro que
    se escolhe: não cobrar alguém por uma semana é recuperável; cobrar duas
    vezes o mesmo segurado é o defeito que esta SPEC existe para fechar. A
    retenção diz `por NOME` e a pessoa libera pela tela se discordar.
    """
    doc = so_digitos((item or {}).get("cpf_cnpj"))
    if doc:
        return f"doc:{doc}"
    nome = _norm_txt(_first_text((item or {}).get("cliente_nome"),
                                 (item or {}).get("nome_segurado"),
                                 (item or {}).get("client_name")))
    if nome:
        return f"nome:{nome}"
    return f"recibo:{str((item or {}).get('recibo') or '').strip()}"


def chave_do_grupo(item: Dict[str, Any]) -> str:
    """QUEM + ONDE — é o que decide o que cabe numa MESMA mensagem.

    🔴 Inclui o portal, porque o texto nomeia a seguradora ("A Seguradora {x}
    informou") e um grupo com duas seguradoras exigiria uma mensagem que
    ninguém escreveu e o Founder não aprovou (B1.5).
    ⚠️ E o mesmo segurado em DUAS seguradoras não recebe duas mensagens no mesmo
    dia: quem impede é a janela de N dias, que usa `segurado_chave` — SEM o
    portal.
    🔴 E inclui o `company_id` quando o item o carrega, na FRENTE, como no índice
    do banco (CLAUDE.md §7): dois tenants na mesma lista nunca produzem um grupo
    misto, nem quando o CPF é o mesmo (o mesmo segurado pode ser cliente de duas
    corretoras). Nos itens que o worker devolve hoje a chave vem vazia, e aí a
    forma é exatamente `segurado_chave|portal`.
    """
    empresa = str((item or {}).get("company_id") or "").strip().lower()
    portal = str((item or {}).get("portal") or "").strip().lower()
    return f"{empresa}|{segurado_chave(item)}|{portal}" if empresa else f"{segurado_chave(item)}|{portal}"


def agrupar_por_segurado(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Devolve GRUPOS, na ordem da dívida mais velha de cada grupo.

    Cada grupo: `{"chave_do_grupo", "segurado_chave", "cliente_nome", "portal",
    "company_id", "parcelas": [item, ...]}`.

    A ordem entre grupos é a de `ordenar_para_entrega` aplicada à parcela mais
    VELHA de cada grupo — a fila continua significando o que significava: quem
    está mais perto do cancelamento sai primeiro. Dentro do grupo, as parcelas
    também saem pela mesma régua.
    """
    grupos: Dict[str, Dict[str, Any]] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        chave = chave_do_grupo(item)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = {
                "chave_do_grupo": chave,
                "segurado_chave": segurado_chave(item),
                "cliente_nome": _first_text(item.get("cliente_nome"), item.get("nome_segurado"),
                                            default="cliente"),
                "portal": str(item.get("portal") or "").strip(),
                "company_id": str(item.get("company_id") or "").strip(),
                "parcelas": [],
            }
            grupos[chave] = grupo
        grupo["parcelas"].append(item)
    for grupo in grupos.values():
        grupo["parcelas"] = ordenar_para_entrega(grupo["parcelas"])
    # A ordem entre grupos é decidida pelo MOTOR da fila, não por uma segunda
    # régua escrita aqui: a parcela mais velha de cada grupo passa por
    # `ordenar_para_entrega`, e a posição dela é a posição do grupo.
    mais_velhas = ordenar_para_entrega([g["parcelas"][0] for g in grupos.values() if g["parcelas"]])
    posicao = {chave_do_grupo(item): n for n, item in enumerate(mais_velhas)}
    return sorted(grupos.values(), key=lambda g: posicao.get(g["chave_do_grupo"], 9999))


def lista_de_parcelas(numeros: Iterable[Any]) -> str:
    """`["2/6","3/6","4/6"]` → `"2/6, 3/6 e 4/6"`. Vírgula, e "e" antes da última."""
    limpos: List[str] = []
    for numero in numeros or []:
        texto = str(numero or "").strip()
        if texto and texto not in limpos:
            limpos.append(texto)
    if not limpos:
        return ""
    if len(limpos) == 1:
        return limpos[0]
    return ", ".join(limpos[:-1]) + " e " + limpos[-1]


def _sem_repetir(valores: Iterable[Any]) -> List[str]:
    fora: List[str] = []
    for valor in valores or []:
        texto = str(valor or "").strip()
        if texto and texto not in fora:
            fora.append(texto)
    return fora


# ==========================================================================
# SPEC-EXTRA-001 · U1 — AS QUATRO MODALIDADES QUE TÊM MOTOR
# ==========================================================================
#
# 🔴 `approval` e `live` NÃO são modalidades: são configuração antiga.
#
# 📊 Medido em 07/09/2026: `send_billing_whatsapp` só aparece em
# `_create_approval_request` (`:793`) — nenhum consumidor jamais executou um
# pedido de aprovação de cobrança; e o ramo `live` (`:1734-1743`) termina em
# duas frases de blocker, sem chamar porta nenhuma. Ou seja: as duas
# "modalidades" existiam na tela e não existiam no produto.
#
# ⛔ E elas NÃO são promovidas automaticamente. Mapear `live` → `cliente` seria
# ligar o envio ao segurado numa corretora que nunca escolheu isso — a decisão
# tem de ser tomada por gente, na tela, uma vez. Por isso o normalize devolve
# `retido_legado`: nada sai, e o relatório diz o que fazer.
MODOS_COM_MOTOR = ("test", "none", "equipe", "cliente")
MODOS_REAIS = ("equipe", "cliente")
MODOS_LEGADOS = ("approval", "live")
MODO_RETIDO = "retido_legado"

#: SPEC-EXTRA-001.6 B1.3 · D-PILOTO-18 (13/09): N = 7 (nota 85 × 3 dias 60 ×
#: 14 dias 70). Na tela, ajustável por corretora — o ritmo de cobrança é decisão
#: de negócio dela, não do motor.
DIAS_ENTRE_COBRANCAS_PADRAO = 7
CHAVE_DIAS_ENTRE_COBRANCAS = "dias_entre_cobrancas_do_mesmo_segurado"


def normalize_billing_config(config: Optional[Dict[str, Any]], delivery: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw = config if isinstance(config, dict) else {}
    delivery = delivery if isinstance(delivery, dict) else {}
    portals = _as_list(raw.get("portal_keys") or raw.get("selected_portals")) or DEFAULT_PORTAL_KEYS[:]
    send_mode_original = str(raw.get("send_mode") or "test").strip().lower()
    send_mode = send_mode_original
    retido_motivo = ""
    # 🔴 O telefone da EQUIPE vem por `telefone_br`, a regra única do produto
    # (P-097-TELEFONE-BR-DUPLICADO) — importado no topo deste arquivo.
    team_number = so_digitos(raw.get("team_number"))
    # 🔴 `_truthy`, nunca `bool(...)`: `bool("false") is True`. A rota Next grava
    #    booleano, mas esta checagem existe justamente para a config gravada por
    #    outro caminho — e "false" como texto não pode ligar o envio ao segurado
    #    (red team da EXTRA-001, 07/09).
    confirmacao_cliente = _truthy(raw.get("confirmacao_cliente"))

    if send_mode in MODOS_LEGADOS:
        send_mode = MODO_RETIDO
        retido_motivo = ("configuração antiga: escolha Encaminhar para minha equipe "
                         "ou Enviar ao cliente")
    elif send_mode not in MODOS_COM_MOTOR:
        send_mode = "test"
    elif send_mode == "equipe" and len(team_number) < 10:
        # Sem para QUEM encaminhar, `equipe` não é uma modalidade — é uma
        # mensagem sem destino. Reter é a única resposta honesta.
        send_mode = MODO_RETIDO
        retido_motivo = ("modo Encaminhar para minha equipe sem o WhatsApp da equipe: "
                         "informe o número na tela do Auxiliar")
    elif send_mode == "cliente" and not confirmacao_cliente:
        # A tela pede a confirmação explícita antes de salvar. O motor a exige
        # de novo, porque a config pode ter sido gravada por outro caminho — e
        # "o segurado recebe direto" nunca pode valer por omissão.
        send_mode = MODO_RETIDO
        retido_motivo = ("modo Enviar ao cliente sem a confirmação da corretora: "
                         "confirme na tela do Auxiliar antes de ligar")
    elif send_mode in MODOS_REAIS and not str(
            raw.get("attendant_name") or raw.get("nome_atendente") or "").strip():
        # SPEC-EXTRA-001.6 P0.4 — RETER, não default. 📊 A frase que o Founder leu
        # em 10/09 — "Aqui é a nossa equipe, da Resulta" — foi reproduzida
        # literalmente pelo motor em 13/09 com `attendant_name=''`. O default
        # "nossa equipe" (abaixo) continua valendo para `test`/`none`, onde o
        # destino é a própria corretora e nada vaza; num modo real ele é o
        # segurado lendo que ninguém assina.
        send_mode = MODO_RETIDO
        retido_motivo = ("sem o nome de quem assina a mensagem: preencha 'Quem assina "
                         "a mensagem' na tela do Auxiliar — o segurado não pode receber "
                         "'Aqui é a nossa equipe'")

    test_number = _digits(raw.get("test_number") or delivery.get("number") or "")
    return {
        **raw,
        "kind": BILLING_KIND,
        "portal_keys": portals,
        "approval_required": bool(raw.get("approval_required", True)),
        "send_mode": send_mode,
        "send_mode_original": send_mode_original,
        "retido_motivo": retido_motivo,
        "team_number": team_number,
        "confirmacao_cliente": confirmacao_cliente,
        # ⛔ Só o script de canário grava isto. A tela NUNCA o expõe.
        "canario": bool(raw.get("canario")),
        "test_number": test_number,
        "message_template": str(raw.get("message_template") or DEFAULT_MESSAGE_TEMPLATE).strip() or DEFAULT_MESSAGE_TEMPLATE,
        "attendant_name": _first_text(raw.get("attendant_name"), raw.get("nome_atendente"), default="nossa equipe"),
        "brokerage_name": _first_text(raw.get("brokerage_name"), raw.get("nome_corretora"), default="sua corretora"),
        "insurer_name": _first_text(raw.get("insurer_name"), raw.get("nome_seguradora"), default="ALLIANZ"),
        "max_boletos_por_execucao": _int_clamped(raw.get("max_boletos_por_execucao") or raw.get("max_boletos"), 10, 1, 50),
        # SPEC-EXTRA-001.6 B1.3 — quantos dias entre duas cobranças do MESMO
        # segurado. Clamp 1–30: 0 desligaria a regra por descuido de digitação
        # (e "0 dias" é exatamente o defeito de 10–11/09), e mais de um mês
        # deixaria de ser ritmo de cobrança para ser esquecimento.
        CHAVE_DIAS_ENTRE_COBRANCAS: _int_clamped(
            raw.get(CHAVE_DIAS_ENTRE_COBRANCAS), DIAS_ENTRE_COBRANCAS_PADRAO, 1, 30),
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


# O que o GRUPO HUMANO da corretora lê quando um portal responde mas não
# entrega a lista de parcelas.
#
# ⚠️ 18/08/2026: três estágios diferentes recebiam a MESMA frase — "não
# consegui ler a lista de parcelas". Naquele dia a Allianz caiu por SESSÃO
# MORTA (o portal devolveu o navegador ao provedor de identidade e nenhuma tela
# renderizou); o grupo leu "não consegui ler a lista" e o Founder foi investigar
# leitura de tabela. É o defeito do CLAUDE.md §12.1: o rótulo mentiu sobre o que
# aconteceu, e o leitor seguinte gastou o tempo dele no lugar errado.
#
# Regra desta tabela: uma frase por estágio, todas diferentes entre si, todas em
# português de gente — quem lê é atendimento de corretora, não quem escreveu o
# worker. Estágio que não estiver aqui NÃO gera aviso (não inventamos frase para
# um estado que ninguém descreveu).
O_QUE_HOUVE_POR_ESTAGIO = {
    "lista_nao_lida": "abri a tela de cobrança, mas não consegui entender a tabela de parcelas",
    "sem_linhas_extraiveis": "abri a tela de cobrança e ela não trouxe nenhuma parcela que eu conseguisse aproveitar",
    "inadimplentes_nao_localizado": "entrei no portal, mas não achei a tela de parcelas em atraso",
    "sessao_caiu_no_portal": "o portal encerrou minha sessão e me mandou de volta para a tela de entrada; tentei entrar de novo e ainda assim não cheguei nas parcelas",
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


# ==========================================================================
# SPEC-EXTRA-001.6 · B1.5 — A COPY DO PLURAL
# ==========================================================================
#
# 💭 ILUSTRATIVA enquanto o Founder não emendar (proposta §B1.5, caixa do
# Founder). O que NÃO é ilustrativo: **N = 1 continua byte a byte o template de
# hoje**, que é travado desde 11/07/2026, e o guarda G7 prova isso comparando
# com `build_customer_message`.
#
# 🔴 A transformação é do TEMPLATE PADRÃO, frase por frase — não uma segunda
# mensagem escrita ao lado. Se a corretora personalizou o template, não há como
# saber quais frases estão no singular sem reescrever o texto dela: nesse caso a
# mensagem é a de sempre, com a LISTA de parcelas no lugar de `{numero_parcela}`.
# Inventar plural no texto de outra pessoa é pior que repetir o singular.
_PLURAL_DO_PADRAO = (
    ("que a parcela {numero_parcela}", "que as parcelas {numero_parcela}"),
    ("ainda está pendente", "ainda estão pendentes"),
    ("gerou um novo boleto para pagamento", "gerou novos boletos para pagamento"),
    ("Segue o boleto abaixo.", "Seguem os boletos abaixo."),
)


def mensagem_do_grupo(grupo: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> str:
    """O texto ÚNICO que vai ao segurado por todas as parcelas do grupo."""
    parcelas = list((grupo or {}).get("parcelas") or [])
    cfg = cfg or {}
    template = str(cfg.get("message_template") or DEFAULT_MESSAGE_TEMPLATE)
    if len(parcelas) <= 1:
        # ⛔ Caminho INTOCADO: uma parcela é a mensagem de hoje, letra por letra.
        return build_customer_message(parcelas[0] if parcelas else {}, template, cfg)

    numeros = lista_de_parcelas(_first_text(p.get("numero_parcela"), p.get("parcela"))
                                for p in parcelas)
    apolices = _sem_repetir(_first_text(p.get("numero_apolice"), p.get("apolice_susep"),
                                       p.get("apolice")) for p in parcelas)
    bens = _sem_repetir(_insured_item_name(p) for p in parcelas)
    base = dict(parcelas[0])
    base["numero_parcela"] = numeros
    base["parcela"] = numeros
    if apolices:
        base["numero_apolice"] = ", ".join(apolices)
        base["apolice"] = base["numero_apolice"]

    if template.strip() != DEFAULT_MESSAGE_TEMPLATE.strip():
        # Template da corretora: singular, com a lista. E vai registrado.
        return build_customer_message(base, template, cfg)

    texto = template
    if len(bens) > 1:
        # "do seguro do seus seguros" não é português. Quando os bens são
        # diferentes, a frase deixa de ser "do seguro do X".
        texto = texto.replace("do seguro do {item_segurado}", "de {item_segurado}")
        base["item_segurado"] = "seus seguros"
    for antes, depois in _PLURAL_DO_PADRAO:
        texto = texto.replace(antes, depois)
    if len(apolices) > 1:
        texto = texto.replace("Apólice: {numero_apolice}", "Apólices: {numero_apolice}")
    return build_customer_message(base, texto, cfg)


def _client(supabase):
    return getattr(supabase, "client", supabase)


def _portal_account(client, company_id: str, portal_key: str) -> Optional[Dict[str, Any]]:
    res = (
        client.table("portal_accounts")
        # `updated_at` entra por causa do breaker (B3.1/B3.3): `fora_do_ar` é um
        # estado com PRAZO, e sem a hora em que ele foi escrito não há como saber
        # se o prazo já passou — o circuito ficaria aberto para sempre.
        .select("id, portal_key, account_label, username, health, updated_at")
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


#: As DUAS jornadas que esta rotina enfileira. Mesma fila (`portal_jobs`), mesmo
#: worker, mesma tabela de sessão — só a jornada muda (CLAUDE.md §5: nada de
#: scheduler, fila ou motor novo para o canário de login).
JORNADA_DA_VARREDURA = "cobranca_sweep"
JORNADA_DO_CANARIO = "login_check"
#: `priority` menor = mais urgente (SPEC-075, `nice(1)`; default da coluna = 100).
#: O canário é curto e a varredura depende dele: ele entra na frente.
PRIORIDADE_DO_CANARIO = 50


def _enqueue_job(client, routine: Dict[str, Any], portal_key: str, account: Dict[str, Any],
                 cfg: Dict[str, Any], *, journey: str = JORNADA_DA_VARREDURA) -> Optional[str]:
    e_canario = str(journey or "") == JORNADA_DO_CANARIO
    linha = {
        "company_id": str(routine["company_id"]),
        "portal_key": portal_key,
        "journey": "cobranca_sweep" if not e_canario else JORNADA_DO_CANARIO,
        "account_id": account.get("id"),
        # ⛔ O canário SÓ ENTRA E SAI: nada de `download_boletos`, nada de
        # `max_boletos`. Ele responde uma pergunta — "a credencial ainda entra?"
        # — e qualquer parâmetro de varredura aqui viraria trabalho de portal que
        # ninguém pediu.
        "params": ({"source": "routine_engine",
                    "routine_id": str(routine.get("id") or "")} if e_canario else {
            "max_boletos": cfg["max_boletos_por_execucao"],
            "download_boletos": True,
            "require_downloads": True,
            "source": "routine_engine",
            "routine_id": str(routine.get("id") or ""),
        }),
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
    #
    # O canário viaja pelo mesmo caminho: `priority` é coluna da mesma SPEC-075,
    # então ela entra no MESMO dicionário opcional — se o banco recusar uma,
    # recusa as duas, e o retry sem elas continua enfileirando o job.
    extras = ({"priority": PRIORIDADE_DO_CANARIO} if e_canario
              else {"operation_key": "billing.overdue.list"})
    ins = None
    try:
        ins = client.table("portal_jobs").insert({**linha, **extras}).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "[billing] insert com as colunas da SPEC-075 falhou (%s); repetindo "
            "sem elas — a migration provavelmente ainda nao rodou",
            type(e).__name__)
        ins = client.table("portal_jobs").insert(linha).execute()

    job_id = str(ins.data[0]["id"]) if ins and ins.data else None

    # SPEC-075 Bloco U — sombra. O caminho legado JÁ executou (o insert acima);
    # isto só registra o que a ponte teria escolhido. Nunca cria job, nunca
    # chama portal, e um erro aqui não pode custar a varredura.
    # ⚠️ A sombra observa a VARREDURA (a operação `billing.overdue.list`). O
    # canário de login não é uma operação de negócio da ponte — registrá-lo ali
    # faria a matriz de capacidade contar uma operação que não existe.
    if job_id and not e_canario:
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
    """A simulação de UMA parcela. ⛔ Saída byte a byte igual à de sempre."""
    return _mensagem_de_teste({"parcelas": [item]}, cfg, [(item, boleto, boleto_url)])


def _mensagem_de_teste(grupo: Dict[str, Any], cfg: Dict[str, Any],
                       anexos: List[tuple]) -> str:
    """A simulação de um GRUPO: o texto do segurado + uma linha por boleto.

    🔴 O modo teste agrupa pelo MESMO motor do modo real (B1.2). Se ele não
    agrupasse, o Founder ensaiaria uma coisa e a atendente receberia outra — que
    foi exatamente o defeito de 10/09, quando o mesmo CNPJ produziu 4 abordagens.
    """
    lines = [
        "[TESTE AutoBrokers - Auxiliar de Cobranca]",
        mensagem_do_grupo(grupo, cfg),
    ]
    for item, boleto, boleto_url in anexos or []:
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


def _record_sent(client, company_id: str, item: Dict[str, Any], send_mode: str, doc_sent: bool) -> bool:
    """Grava que ESTE recibo já foi entregue. Devolve se gravou de verdade.

    🔴 Esta função tinha `except Exception: pass`. É exatamente o desenho que
    produz "acha que registrou e não registrou": a entrega segue, ninguém vê
    nada, e amanhã o mesmo segurado recebe o mesmo boleto — porque a linha que
    impediria isso nunca chegou ao banco. A falha agora aparece no log e volta
    como `False` para quem chamou escrever no relatório. O que ela continua NÃO
    fazendo é derrubar a entrega: o boleto já saiu, e fingir que não saiu seria
    pior.
    """
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
                # SPEC-EXTRA-001.6 B1.3 — DE QUEM é esta parcela. É o que a
                # janela de N dias lê depois, inclusive no modo teste (é lá que
                # o Founder ensaia o que a atendente vai receber).
                "segurado_chave": segurado_chave(item),
            },
            on_conflict="company_id,recibo,send_mode",
        ).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        # Sem PII no log: nem recibo, nem nome, nem company_id.
        logger.error("[COBRANCA] falhei ao registrar entrega em billing_sent_log: %s: %s",
                     type(exc).__name__, str(exc)[:200])
        return False


# A dedup de entrega mora aqui, num lugar só, com nome — e não espalhada em
# `if send_mode == ...` pelo caminho de entrega.
#
# 🔴 INVERTIDA EM 13/09/2026 (SPEC-EXTRA-001.6 B1.1; CLAUDE.md §9.3).
#
# A decisão de 17/08/2026 (nota 88) era: "em teste não deduplica, porque em
# teste o destino é a própria corretora e o que se quer é REPETIR". 📊 O que ela
# produziu, medido em 13/09: a rotina da Resulta rodou em 10 e em 11/09 e mandou
# os MESMOS 7 boletos nos dois dias — e a tela de Pendências ficava vazia e
# correta ao mesmo tempo, porque nada era registrado. Um padrão que só pode
# errar de um lado não é um padrão, é um defeito com data.
#
# O padrão passa a ser DEDUPLICAR, nos quatro modos. Quem quer repetir num dia
# de demonstração LIGA a flag — e a flag ⛔ nunca toca modo real: lá repetir é
# uma segunda cobrança ao segurado, e isso não é assunto de variável de ambiente.
FLAG_DEDUP_TESTE_DESLIGADA = "BILLING_DEDUP_TEST_DISABLED"


def dedup_de_envio_ativa(send_mode: Any, env: Optional[Dict[str, str]] = None) -> bool:
    """A dedup vale SEMPRE. Só o modo `test` consegue desligá-la, e só pela flag."""
    modo = str(send_mode or "").strip().lower()
    if modo != "test":
        return True                       # ⛔ a flag NUNCA toca um modo real
    fonte = env if env is not None else os.environ
    return not _truthy(fonte.get(FLAG_DEDUP_TESTE_DESLIGADA))


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
    # A DEDUP DE ENTREGA — as duas metades da mesma regra, no mesmo lugar:
    # ler `billing_sent_log` antes de enfileirar, gravar depois de entregar.
    # Quem decide se ela vale neste modo e `dedup_de_envio_ativa` (a nota 88 de
    # 17/08/2026 esta escrita la). Mexer numa metade sem a outra deixa a tabela
    # crescendo com linhas que ninguem consulta, ou a regra existindo so no
    # papel — que foi o estado em que estas duas funcoes ficaram ate 19/08.
    send_mode = str(cfg.get("send_mode") or "test").strip().lower()
    dedup = dedup_de_envio_ativa(send_mode)
    already: set = (
        await asyncio.to_thread(_already_sent_recibos, client, company_id, send_mode)
        if dedup else set()
    )
    by_recibo = _boletos_by_recibo(boletos)
    sent: List[Dict[str, Any]] = []
    skipped = 0
    orcamento_s = float(GOVERNOR_WAIT_BUDGET_S)
    # 🔴 B1.3 — A JANELA DE N DIAS TAMBÉM VALE AQUI, lendo o ledger do modo
    # `test`. O modo teste existe para o Founder ver o que a atendente vai
    # receber; um ensaio que repete o que o real não repetiria ensaia outra
    # coisa. ⚠️ Ela segue a mesma chave da dedup: com a flag de demonstração
    # ligada, nada limita — é o dia em que se quer repetir de propósito.
    dias_da_janela = int(cfg.get(CHAVE_DIAS_ENTRE_COBRANCAS) or DIAS_ENTRE_COBRANCAS_PADRAO)
    recentes: Dict[str, str] = {}
    if dedup:
        try:
            recentes = await asyncio.to_thread(
                _segurados_cobrados_recentemente, client, company_id,
                dias_da_janela, send_mode)
        except Exception as exc:  # noqa: BLE001
            # ⚠️ AQUI, E SÓ AQUI, A FALHA DE LEITURA NÃO PARA A ENTREGA — e a
            # diferença para o modo real é o DESTINO. 📊 19/08/2026, guarda
            # `test_a_sessao_caida_volta_e_o_aviso_diz_a_verdade`: "banco fora do
            # ar: a entrega acontece assim mesmo". Em `test` quem recebe é o
            # número da própria corretora, e o pior desfecho de um ledger
            # ilegível é a corretora ver a mesma simulação duas vezes. No modo
            # real o pior desfecho é o SEGURADO ser cobrado duas vezes — e lá
            # nada sai (R04). A dedup por recibo continua valendo.
            blockers.append(f"modo teste: nao consegui ler quem ja foi cobrado nos "
                            f"ultimos {dias_da_janela} dias ({type(exc).__name__}) — "
                            f"a simulacao seguiu sem a regra de {dias_da_janela} dias")

    # 🔴 B1.2 — o modo teste agrupa pelo MESMO motor do modo real.
    a_enviar = agrupar_por_segurado(items)
    for indice, grupo in enumerate(a_enviar):
        parcelas = list(grupo.get("parcelas") or [])
        novas = [p for p in parcelas
                 if not (str(p.get("recibo") or "").strip() in already)]
        skipped += len(parcelas) - len(novas)
        if not novas:
            continue
        cobrado_em = recentes.get(str(grupo.get("segurado_chave") or ""))
        if cobrado_em:
            blockers.append(
                f"{len(novas)} parcela(s) ({_portal_insurer_name(novas[0], cfg)}) nao "
                f"simuladas: {_motivo_da_janela(cobrado_em, str(grupo.get('segurado_chave') or ''), dias_da_janela)}")
            continue

        # SPEC-063 Bloco C — o portao de vazao, UMA vez por segurado.
        # 🔴 O destino aqui e SEMPRE o `test_number` da propria corretora — um
        # numero so, dela. O espacamento de 4-8 min protege contra falar com
        # muitos numeros DIFERENTES; esse risco nao existe neste caminho.
        # Ver `_INTERVALO_TESTE_MIN_S` em `platform_outbound`.
        liberado, motivo, esperou = await _esperar_o_governador(
            company_id, orcamento_s, para_numero_de_teste=True)
        orcamento_s -= esperou
        if not liberado:
            pendentes = sum(len(g.get("parcelas") or []) for g in a_enviar[indice:])
            blockers.append(
                f"governador de envio: parei em {len(sent)} envio(s) — {motivo}. "
                f"{pendentes} item(ns) ficaram para a proxima execucao (nao foram "
                f"marcados como enviados, entao nao se perdem)")
            break

        # Os anexos do grupo: um por parcela, na ordem da fila.
        anexos: List[tuple] = []
        for parcela in novas:
            boleto = by_recibo.get(str(parcela.get("recibo") or "").strip())
            url = await asyncio.to_thread(
                _signed_boleto_url, client, boleto.get("storage_path") if boleto else "")
            anexos.append((parcela, boleto, url))
        text = _mensagem_de_teste({**grupo, "parcelas": novas}, cfg, anexos)
        entradas = [{
            "cliente_nome": parcela.get("cliente_nome"),
            "recibo": parcela.get("recibo"),
            "to_last4": number[-4:],
            "boleto_link": bool(url),
            "ok": False,
        } for parcela, _b, url in anexos]
        ok = False
        try:
            # SPEC-EXTRA-001.6 P0.1 — a simulação é DOCUMENTO: vai inteira, como o
            # que a atendente vai receber em `equipe`. 📊 13/09: 520 ch → 3 balões.
            ok = bool(await asyncio.to_thread(
                functools.partial(get_whatsapp_service().send_message,
                                  number, text, integration, bloco_unico=True)))
        except Exception as e:  # noqa: BLE001
            for entry in entradas:
                entry["error"] = type(e).__name__
            # 🔴 `type(e).__name__` virava a palavra "Exception" — o relatorio
            # dizia que falhou e nao dizia por que. O texto da excecao carrega
            # o status HTTP do provedor (ver `whatsapp_service.send_message`).
            # Quem le o relatorio nao tem acesso ao log do conteiner; se o
            # motivo nao vier aqui, ele nao existe para essa pessoa.
            _motivo = str(e).strip() or type(e).__name__
            blockers.append(f"modo teste: falha ao enviar simulacao para ...{number[-4:]} — {_motivo[:220]}")
        for entry in entradas:
            entry["ok"] = ok

        # Boleto como DOCUMENTO PDF (decisão de produto 2026-07-10): o cliente
        # recebe o arquivo, não um link que expira. Link assinado é só fallback.
        # 🔴 UM PDF POR PARCELA, todos depois do texto único que os anuncia.
        for entry, (parcela, _boleto, boleto_url) in zip(entradas, anexos):
            if not (ok and boleto_url):
                continue
            doc_ok = await asyncio.to_thread(
                get_whatsapp_service().send_document,
                number,
                boleto_url,
                boleto_document_name(parcela),
                integration,
            )
            entry["document_sent"] = bool(doc_ok)
            if doc_ok:
                # SPEC-EXTRA-001.6 P0.5 — o PDF é contado como componente, igual
                # ao caminho real (`_entregar_agora`): uma linha `billing_doc`.
                await _registrar_documento_no_governador(company_id, number, parcela)
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

        if ok:
            for entry, (parcela, _boleto, _url) in zip(entradas, anexos):
                # A OUTRA METADE DA DEDUP: so entra em `billing_sent_log` quem
                # realmente recebeu. E o que torna "parar no meio" seguro — quem nao
                # saiu hoje nao foi marcado, e volta amanha de onde parou.
                if dedup:
                    gravou = await asyncio.to_thread(
                        _record_sent, client, company_id, parcela, send_mode,
                        bool(entry.get("document_sent")))
                    entry["registrado"] = bool(gravou)
                    if not gravou:
                        # 🔴 Registro que falha em silencio = mesmo boleto amanha.
                        # Quem le o relatorio nao tem acesso ao log do conteiner.
                        recibo_key = str(parcela.get("recibo") or "").strip()
                        blockers.append(
                            f"entrega feita mas NAO registrada em billing_sent_log "
                            f"(recibo ...{recibo_key[-4:] or '?'}): este boleto pode sair de novo na proxima execucao")
            # O registro de VAZAO (`platform_sends`, logo abaixo) e outra coisa:
            # ele conta mensagens para os tetos, e uma mensagem de teste ocupa
            # o canal exatamente como qualquer outra.
            #
            # O contador de vazao vive em `platform_sends`, e ele so conta o
            # que foi registrado. Sem esta linha o governador espacaria as
            # mensagens e continuaria achando que o dia esta zerado — o teto
            # diario nunca fecharia.
            #
            # ⚠️ UMA linha por MENSAGEM (o grupo), não por parcela: é uma
            # abordagem só, e contar quatro faria o governador achar que o canal
            # falou quatro vezes com a mesma pessoa.
            await _registrar_no_governador(company_id, number, novas[0], cfg)
        sent.extend(entradas)
    if skipped:
        blockers.append(f"anti-duplicacao: {skipped} boleto(s) ja enviados anteriormente foram pulados (nao reenviamos o mesmo)")
    return sent


async def _esperar_o_governador(company_id: str, orcamento_s: float, *,
                                para_numero_de_teste: bool = False) -> tuple:
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
            veredito = await governar_envio(
                str(company_id), para_numero_de_teste=para_numero_de_teste)
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


async def _registrar_documento_no_governador(company_id: str, number: str,
                                             item: Dict[str, Any]) -> None:
    """Anota o PDF em `platform_sends` — SPEC-EXTRA-001.6 P0.5.

    📊 10–11/09/2026: 7 linhas/dia gravadas, ≈28 mensagens recebidas pelo canal.
    O PDF era metade da diferença e não era contado em lugar nenhum.
    """
    try:
        from app.services.platform_outbound import (KIND_DO_DOCUMENTO_DA_COBRANCA,
                                                    record_platform_send)

        await record_platform_send(str(company_id), number, KIND_DO_DOCUMENTO_DA_COBRANCA,
                                   f"boleto anexado ({boleto_document_name(item)})"[:120])
    except Exception:  # noqa: BLE001
        pass


# ==========================================================================
# SPEC-EXTRA-001 · U1 — OS MODOS REAIS: `equipe` e `cliente`
# ==========================================================================
#
# 🔴 NENHUM MOTOR NOVO (CLAUDE.md §5). Este bloco não tem fila, scheduler,
# sender nem ledger próprio:
#
#     o ledger    É `billing_sent_log`, a tabela que já existia
#     a porta     É `platform_outbound.send_to_client_guarded`, a que já existia
#     o freio     É o governador de vazão, o que já existia
#     o registro  É `log_activity` → `agent_activities`, o painel que já existe
#     o retentador É a PRÓXIMA EXECUÇÃO DA ROTINA — e é por isso que a SPEC
#                 recusou uma fila durável: a rotina já volta amanhã, e uma fila
#                 ao lado dela seria um segundo relógio para o mesmo trabalho.
#
# O que é novo é a ORDEM: **reservar antes de enviar**. É o padrão outbox lido
# na fonte (AWS, "Transactional outbox"): a intenção é gravada antes do efeito,
# e o consumidor é idempotente. Gravar depois — que é o que a tabela fazia — é
# como o mesmo boleto sai duas vezes quando um processo morre no meio.


#: `contact_status` que autorizam falar com o SEGURADO. Lista de permissão, e
#: curta: 📊 `infocap_connector.py:1183` devolve `found` quando a apólice foi
#: localizada; todo o resto (`not_found`, `provider_error`, `auth_error`,
#: `source_limited`, `policy_number_ambiguous`) é "não sei quem é este
#: telefone". Cobrar sem saber de quem é o número é o pior desfecho possível
#: desta SPEC — pior que não cobrar.
CONTATOS_ACEITOS = ("found", "ok")

#: Estados que admitem uma nova tentativa. ⛔ `incerto`, `entregue_equipe`,
#: `aceito_pelo_canal`, `suprimido`, `contestado` e `reservado` NUNCA entram:
#: efeito possível não é efeito ausente, e preferência do cliente não se desfaz
#: por retomada automática (WhatsApp Business Policy).
ESTADOS_RECLAMAVEIS = ("falhou", "adiado", "liberado", "parcial")

#: O que a porta responde → o estado que fica no ledger quando ela nem chegou a
#: enviar. `adiado` é reclamável amanhã; `falhou` também. A diferença é o que a
#: pessoa lê na tela: "a vazão não abriu" e "não consegui" não são a mesma notícia.
# O MOTIVO que a corretora lê (painel 07/09, lente produto+DADO P3): o token da
# porta (`conexao_trocada`, `fora_da_allowlist`…) é para quem investiga; quem
# lê Atividades e o relatório é atendimento de corretora.
MOTIVO_EM_PORTUGUES = {
    "governador": "fora da janela ou do limite de envios do dia — tenta na próxima execução",
    "cliente_em_atendimento": "o cliente estava em atendimento — tenta na próxima execução",
    "sem_canal": "a corretora não tem WhatsApp autorizado para o Auxiliar",
    "conexao_trocada": "a conexão de WhatsApp mudou desde o início da execução — nada saiu por segurança",
    "agente_desligado": "o agente de atendimento está desligado",
    "fora_da_allowlist": "número não autorizado no teste",
    "erro_envio": "o WhatsApp não aceitou a mensagem",
    "recusado": "quem pediu o envio não tem mais vínculo com a corretora",
}

_ESTADO_POR_RECUSA = {
    "governador": "adiado",
    "cliente_em_atendimento": "adiado",
    "sem_canal": "falhou",
    "conexao_trocada": "falhou",
    "agente_desligado": "falhou",
    "fora_da_allowlist": "falhou",
    "erro_envio": "falhou",
}


async def _incidente(company_id: str, titulo: str, detalhe: str = "") -> None:
    """Toda falha material vira uma linha em ATIVIDADES, no painel que já existe.

    ⛔ Sem PII: nem telefone, nem CPF, nem nome de segurado, nem apólice. O que
    identifica o caso para quem lê é a seguradora e os últimos dígitos do
    recibo — e é o bastante para achar a linha na lista de Pendências.
    """
    try:
        from app.services.activity_log import log_activity

        await log_activity(str(company_id), "cobranca", titulo[:180], detalhe[:400])
    except Exception:  # noqa: BLE001
        # O incidente é o registro da falha, não a falha. Perder o registro é
        # ruim; derrubar a cobrança por causa dele é pior.
        logger.warning("[COBRANCA] incidente nao registrado: %s", titulo[:80])


def _whatsapp_legivel(numero: Any) -> str:
    """`5547999998888` → `+55 47 99999-8888`. Para a atendente LER e digitar.

    ⚠️ Só aparece na NOTA INTERNA, que vai para a própria corretora — nunca em
    log, relatório de execução, artifact ou prompt.
    """
    d = so_digitos(numero)
    if not d:
        return "não informado"
    if d.startswith("55") and len(d) in (12, 13):
        ddd, resto = d[2:4], d[4:]
        meio = resto[:-4] if len(resto) > 4 else resto
        return f"+55 {ddd} {meio}-{resto[-4:]}"
    return d


def _nota_interna_para_a_equipe(item: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """A mensagem que a ATENDENTE lê — separada da que ela vai encaminhar.

    🔴 Ela é uma mensagem PRÓPRIA, e não um prefixo do texto do cliente. Um
    cabeçalho colado no texto final obriga a pessoa a editar antes de
    encaminhar — e o que ela encaminha editando às pressas é o que o segurado
    lê. Duas mensagens: uma para trabalhar, outra para repassar inteira.
    """
    valor = item.get("valor")
    valor_txt = (f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                 if isinstance(valor, (int, float)) else str(valor or "não informado"))
    return "\n".join([
        "📋 COBRANÇA · para encaminhar",
        "",
        f"Cliente: {_first_text(item.get('cliente_nome'), item.get('nome_segurado'), default='cliente')}",
        f"Seguradora: {_portal_insurer_name(item, cfg)}",
        f"Parcela: {_first_text(item.get('numero_parcela'), item.get('parcela'), default='?')}",
        f"Vencimento: {item.get('vencimento') or '?'}",
        f"Valor: {valor_txt}",
        f"WhatsApp do cliente: {_whatsapp_legivel(item.get('whatsapp'))}",
        "",
        "👇 a mensagem abaixo e o PDF são para encaminhar ao cliente, inteiros.",
        "Quando encaminhar, marque no painel (Auxiliares → Cobrança → Pendências).",
    ])


def _nota_interna_do_grupo(grupo: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """A nota da atendente quando o segurado tem N parcelas na mesma seguradora.

    ⛔ N = 1 devolve a nota de hoje, byte a byte. Com N > 1 ela LISTA as parcelas:
    a atendente precisa conferir quantos anexos são, e uma nota que diz "Parcela:
    3/12" com quatro PDFs embaixo é uma nota que mente sobre o pacote.
    """
    parcelas = list((grupo or {}).get("parcelas") or [])
    if len(parcelas) <= 1:
        return _nota_interna_para_a_equipe(parcelas[0] if parcelas else {}, cfg)
    base = parcelas[0]
    linhas = [
        "📋 COBRANÇA · para encaminhar",
        "",
        f"Cliente: {_first_text(base.get('cliente_nome'), base.get('nome_segurado'), default='cliente')}",
        f"Seguradora: {_portal_insurer_name(base, cfg)}",
        f"{len(parcelas)} parcelas em atraso, {len(parcelas)} boletos em anexo:",
    ]
    for parcela in parcelas:
        valor = parcela.get("valor")
        valor_txt = (f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                     if isinstance(valor, (int, float)) else str(valor or "não informado"))
        linhas.append(
            f"- parcela {_first_text(parcela.get('numero_parcela'), parcela.get('parcela'), default='?')}"
            f" · apólice {_first_text(parcela.get('numero_apolice'), parcela.get('apolice_susep'), default='?')}"
            f" · vence {parcela.get('vencimento') or '?'} · {valor_txt}")
    linhas += [
        f"WhatsApp do cliente: {_whatsapp_legivel(base.get('whatsapp'))}",
        "",
        "👇 a mensagem abaixo e os PDFs são para encaminhar ao cliente, inteiros.",
        "Quando encaminhar, marque no painel (Auxiliares → Cobrança → Pendências).",
    ]
    return "\n".join(linhas)


def _pacote_humano(item: Dict[str, Any], cfg: Dict[str, Any],
                   boleto: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """O que sai: a nota da equipe, o texto final e o documento.

    🔴 `texto_final` é `build_customer_message` PURO — sem prefixo, sem sufixo,
    sem instrução, sem a palavra "simulação". 📊 R03: o modo teste envolve o
    texto em `[TESTE AutoBrokers…]` e numa frase de rodapé (`:888-905`), e é
    assim que ele tem de continuar. Reusar aquela composição num modo real
    entregaria ao segurado uma mensagem que diz que é teste — ou obrigaria a
    atendente a apagar duas linhas antes de encaminhar.
    """
    return {
        "nota_interna": _nota_interna_para_a_equipe(item, cfg),
        "texto_final": build_customer_message(item, cfg["message_template"], cfg),
        "documento": _documento_do_boleto(item, boleto),
    }


def _documento_do_boleto(item: Dict[str, Any],
                         boleto: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """O anexo de UMA parcela: bucket, caminho e o nome que o cliente vê (sem PII)."""
    caminho = str((boleto or {}).get("storage_path") or "").strip().lstrip("/")
    if not caminho:
        return None
    return {"bucket": PORTAL_EVIDENCE_BUCKET, "path": caminho,
            "filename": boleto_document_name(item)}


def _obrigacoes_reais(client, company_id: str) -> Dict[str, Dict[str, Any]]:
    """O que esta corretora JÁ cobrou de verdade, por `(seguradora, recibo)`.

    🔴 **Leitor próprio dos modos reais** — `_already_sent_recibos` continua
    servindo só ao modo `test`, com a chave antiga e o `except → set()` dele.
    Aqui a regra é oposta: esta função **levanta**. 📊 R04: falha de leitura
    devolvendo lista vazia significa "nunca cobrei ninguém" — e a resposta a
    isso seria cobrar todo mundo de novo. Quem chama trata a exceção como
    "não envia nada hoje".
    """
    res = (client.table("billing_sent_log")
           .select("id, portal_key, recibo, status, text_ok, doc_ok, modalidade, "
                   "encaminhado_ao_cliente_em, updated_at")
           .eq("company_id", str(company_id))          # 🔴 CLAUDE.md §7
           .eq("send_mode", "real")
           .execute())
    fora: Dict[str, Dict[str, Any]] = {}
    for linha in (res.data or []):
        chave = f"{str(linha.get('portal_key') or '').strip()}|{str(linha.get('recibo') or '').strip()}"
        fora[chave] = dict(linha)
    return fora


#: SPEC-EXTRA-001.6 B1.3 — estados que CONTAM como "este segurado já foi
#: cobrado". ⛔ `falhou`, `adiado`, `suprimido` e `reservado` NÃO contam: ninguém
#: recebeu nada, e segurar a cobrança por causa deles seria não cobrar por um
#: erro nosso. `incerto` CONTA: efeito possível não é efeito ausente, e o preço
#: de errar para esse lado é uma semana de espera, não uma segunda cobrança.
ESTADOS_QUE_CONTAM_COMO_COBRADO = ("aceito_pelo_canal", "entregue_equipe",
                                   "parcial", "incerto")


def _quando_saiu(linha: Dict[str, Any]) -> str:
    """A data que a janela usa. `sent_at` primeiro; `updated_at` como segunda.

    🔴 A ordem importa e o fallback não é folga: a linha `incerto` nasce de uma
    exceção DEPOIS do envio, e ela **não tem** `sent_at` (a porta só o grava
    quando o provedor respondeu). Filtrar a janela por `sent_at` no SQL deixaria
    de fora justamente a cobrança que pode ter chegado ao segurado — por isso a
    janela é recortada aqui, em Python, sobre as linhas da corretora.
    """
    return str(linha.get("sent_at") or linha.get("updated_at")
               or linha.get("reserved_at") or linha.get("created_at") or "")


def _segurados_cobrados_recentemente(client, company_id: str, dias: int,
                                     send_mode: str = "real") -> Dict[str, str]:
    """`{segurado_chave: data_iso}` dos segurados já cobrados na janela de N dias.

    🔴 A leitura é por `segurado_chave` — SEM o portal. É isso que faz a janela
    valer ENTRE seguradoras, que é a pergunta que ela responde: "já falei com
    esta pessoa esta semana?".
    🔴 Falha de leitura LEVANTA — nunca devolve vazio. Vazio significaria "não
    cobrei ninguém", e a resposta a isso seria cobrar todo mundo de novo (R04 da
    EXTRA-001; é a mesma disciplina de `_obrigacoes_reais`).
    ⚠️ `send_mode` é parâmetro porque a janela vale nos DOIS mundos: no modo real
    ela lê as cobranças reais; no modo `test`, as de teste — o Founder ensaia o
    que a atendente vai receber, e um ensaio que repete o que o real não repetiria
    ensaia outra coisa (foi o defeito de 10/09).
    """
    janela = max(1, int(dias or DIAS_ENTRE_COBRANCAS_PADRAO))
    corte = datetime.now(timezone.utc) - timedelta(days=janela)
    res = (client.table("billing_sent_log")
           .select("segurado_chave, status, sent_at, updated_at, reserved_at, created_at")
           .eq("company_id", str(company_id))          # 🔴 CLAUDE.md §7
           .eq("send_mode", str(send_mode))
           .in_("status", list(ESTADOS_QUE_CONTAM_COMO_COBRADO))
           .execute())
    fora: Dict[str, str] = {}
    for linha in (res.data or []):
        chave = str((linha or {}).get("segurado_chave") or "").strip()
        if not chave:
            # Linha antiga, de antes da coluna existir. Ela não diz de quem é, e
            # inventar um dono seria pior que não limitar: fica de fora, e o que
            # protege a parcela continua sendo a reserva atômica.
            continue
        quando = _quando_saiu(linha)
        momento = _para_datetime(quando)
        if momento is None or momento < corte:
            continue
        anterior = fora.get(chave)
        if anterior is None or quando > anterior:
            fora[chave] = quando
    return fora


def _para_datetime(valor: Any) -> Optional[datetime]:
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        momento = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def _motivo_da_janela(cobrado_em: Any, chave: str, dias: int) -> str:
    """A frase que a pessoa lê — com a DATA e a ORIGEM da identidade.

    🔴 A origem é produto, não detalhe: quando a identidade vem do NOME (porque a
    seguradora não devolveu o documento), duas pessoas homônimas podem ter sido
    unidas — e a única forma de alguém DISCORDAR é a frase dizer de onde a
    identidade veio e o que fazer a respeito.
    """
    momento = _para_datetime(cobrado_em)
    quando = momento.strftime("%d/%m") if momento else "?"
    volta = (momento + timedelta(days=int(dias))).strftime("%d/%m") if momento else "?"
    if str(chave or "").startswith("doc:"):
        return (f"este segurado já foi cobrado em {quando} (regra de 1 cobrança a cada "
                f"{dias} dias, identificado por CPF/CNPJ) — volta em {volta}")
    return (f"este segurado já foi cobrado em {quando} (regra de 1 cobrança a cada "
            f"{dias} dias, identificado por NOME, porque a seguradora não devolveu o "
            f"documento) — volta em {volta}; se não for a mesma pessoa, libere pela tela")


def _reservar_obrigacao(client, *, company_id: str, portal_key: str, recibo: str,
                        modalidade: str, to_phone: str, to_last4: str,
                        cliente_nome: str, apolice_susep: str,
                        routine_id: Optional[str], work_run_id: Optional[str],
                        integration_id: Optional[str], canario: bool,
                        segurado: str = "") -> Dict[str, Any]:
    """A reserva atômica, pela função do banco. Levanta se o banco recusar.

    ⚠️ RPC, e não `upsert(ignore_duplicates=True)`: a identidade da obrigação é
    um índice único PARCIAL (`WHERE send_mode='real'`), e o `ON CONFLICT` de um
    índice parcial exige repetir o predicado — que o PostgREST não expressa. O
    upsert mandaria `ON CONFLICT (cols) DO NOTHING` sem o `WHERE` e receberia
    **42P10**. Ver o cabeçalho da migration 20260907_01.

    🔴 `p_segurado_chave` é o 13º argumento, e a função de 13 argumentos é uma
    SOBRECARGA sem default (migration `20260914_01`): com default, uma chamada de
    12 casaria com as duas e o Postgres devolveria 42725 (ambiguous function
    call) — em produção, na hora de reservar, com o boleto na mão. Enquanto essa
    migration não estiver aplicada, esta chamada levanta e a parcela NÃO sai:
    é o que a Implantação 2 exige na ordem certa (proposta §15.1).
    """
    res = client.rpc("billing_reservar_obrigacao", {
        "p_company_id": str(company_id),
        "p_portal_key": str(portal_key),
        "p_recibo": str(recibo),
        "p_modalidade": str(modalidade),
        "p_to_phone": str(to_phone or "") or None,
        "p_to_last4": str(to_last4 or "") or None,
        "p_cliente_nome": str(cliente_nome or "") or None,
        "p_apolice_susep": str(apolice_susep or "") or None,
        "p_routine_id": str(routine_id) if routine_id else None,
        "p_work_run_id": str(work_run_id) if work_run_id else None,
        "p_integration_id": str(integration_id) if integration_id else None,
        "p_canario": bool(canario),
        "p_segurado_chave": str(segurado or "") or None,
    }).execute()
    linhas = res.data or []
    return dict(linhas[0]) if linhas else {"id": None, "ganhou": False, "status": None}


def _reclamar_obrigacao(client, *, ledger_id: str, company_id: str,
                        de_status: List[str]) -> bool:
    """Reclama uma obrigação que ficou num estado que admite nova tentativa."""
    res = client.rpc("billing_reclamar_obrigacao", {
        "p_id": str(ledger_id),
        "p_company_id": str(company_id),
        "p_de_status": list(de_status),
    }).execute()
    dados = res.data
    if isinstance(dados, list):
        dados = dados[0] if dados else False
    if isinstance(dados, dict):
        dados = dados.get("billing_reclamar_obrigacao")
    return bool(dados)


def _marcar_estado(client, company_id: str, ledger_id: str, **campos: Any) -> None:
    """Escreve o estado na linha do ledger, sempre com o dono na cláusula."""
    campos.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
    (client.table("billing_sent_log").update(campos)
     .eq("company_id", str(company_id))              # 🔴 CLAUDE.md §7
     .eq("id", str(ledger_id)).execute())


async def _entregar_cobranca_real(client, routine: Dict[str, Any],
                                  fila: List[Dict[str, Any]],
                                  boletos: List[Dict[str, Any]],
                                  cfg: Dict[str, Any], blockers: List[str],
                                  *, work_run_id: Optional[str] = None,
                                  ) -> List[Dict[str, Any]]:
    """`equipe` e `cliente`: reserva, envia pela porta única, marca o estado.

    A ordem é a do dano, e cada passo tem um desfecho escrito:

        1. fixa a CONEXÃO uma vez        sem canal  → nada sai, incidente
        2. lê o que já foi cobrado       falhou     → nada sai, incidente (R04)
        3. por item: pré-condições       faltou     → retido, com motivo
        4.           RESERVA (RPC)       perdeu     → não envia; talvez reclame
        5.           porta de saída      recusou    → adiado/falhou no ledger
        6.           marca o estado      levantou   → `incerto`, nunca retry
    """
    company_id = str(routine.get("company_id") or "")
    modalidade = str(cfg.get("send_mode") or "")
    canario = bool(cfg.get("canario"))
    entregas: List[Dict[str, Any]] = []

    if modalidade not in MODOS_REAIS:
        return entregas

    # 1) A CONEXÃO, FIXADA UMA VEZ. `_find_whatsapp_integration` já é o único
    #    lugar que pede `para="auxiliar"` (SPEC-078 B) — e continua sendo.
    integration = await asyncio.to_thread(_find_whatsapp_integration, client, company_id)
    if not integration:
        blockers.append("cobranca: a corretora nao tem canal de WhatsApp autorizado "
                        "para o Auxiliar — nenhuma mensagem saiu")
        await _incidente(company_id, "Cobrança sem canal de WhatsApp",
                         "Nenhuma conexão ativa desta corretora está autorizada a "
                         "enviar como Auxiliar. Nada foi enviado.")
        return entregas
    integration_id = str(integration.get("id") or "")

    # 2) O QUE JÁ FOI COBRADO. Falha de leitura NÃO vira lista vazia (R04/G09).
    try:
        ja_cobrado = await asyncio.to_thread(_obrigacoes_reais, client, company_id)
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"cobranca: nao consegui ler o historico de cobrancas "
                        f"({type(exc).__name__}) — NADA foi enviado, para nao "
                        f"cobrar duas vezes a mesma parcela")
        await _incidente(company_id, "Cobrança não executada: histórico ilegível",
                         "Não deu para ler quem já foi cobrado. Preferi não enviar "
                         "nada a arriscar cobrar a mesma parcela duas vezes.")
        return entregas

    by_recibo = _boletos_by_recibo(boletos)
    orcamento_s = float(GOVERNOR_WAIT_BUDGET_S)
    routine_id = str(routine.get("id") or "") or None

    # 2.b) QUEM JÁ FOI COBRADO ESTA SEMANA — a janela de N dias (B1.3).
    #      🔴 Mesma disciplina do passo 2: falha de leitura NÃO vira "ninguém foi
    #      cobrado". Ler errado aqui e cobrar de novo é o defeito que esta SPEC
    #      existe para fechar.
    dias_da_janela = int(cfg.get(CHAVE_DIAS_ENTRE_COBRANCAS) or DIAS_ENTRE_COBRANCAS_PADRAO)
    try:
        recentes = await asyncio.to_thread(
            _segurados_cobrados_recentemente, client, company_id, dias_da_janela)
    except Exception as exc:  # noqa: BLE001
        blockers.append(f"cobranca: nao consegui ler quem ja foi cobrado nos ultimos "
                        f"{dias_da_janela} dias ({type(exc).__name__}) — NADA foi enviado, "
                        f"para nao cobrar o mesmo segurado duas vezes")
        await _incidente(company_id, "Cobrança não executada: janela de cobrança ilegível",
                         "Não deu para ler quem foi cobrado nos últimos dias. Preferi não "
                         "enviar nada a arriscar falar duas vezes com o mesmo segurado.")
        return entregas

    # 🔴 B1.2 — A FILA VIRA GRUPOS. Um grupo é UM segurado numa seguradora, e ele
    # recebe UMA abordagem: 1 nota interna + 1 texto + N boletos. A RESERVA
    # continua por PARCELA (§3.1): agrupar é decisão de ENTREGA; reservar é
    # decisão de OBRIGAÇÃO, e é ela que garante que a parcela sai uma vez só.
    for indice, grupo in enumerate(agrupar_por_segurado(fila)):
        parcelas = list(grupo.get("parcelas") or [])
        seguradora = _portal_insurer_name(parcelas[0] if parcelas else {}, cfg)
        chave_do_segurado = str(grupo.get("segurado_chave") or "")

        # 3) A JANELA DE N DIAS, por SEGURADO — antes de reservar qualquer coisa.
        #    ⚠️ Nada some: o grupo retido aparece no relatório com a frase que a
        #    pessoa lê, e cada parcela dele entra nas entregas como `retido`
        #    (CLAUDE.md §11.1).
        cobrado_em = recentes.get(chave_do_segurado)
        if cobrado_em:
            motivo_janela = _motivo_da_janela(cobrado_em, chave_do_segurado, dias_da_janela)
            blockers.append(f"{len(parcelas)} parcela(s) ({seguradora}) nao cobradas: "
                            f"{motivo_janela}")
            for item in parcelas:
                entregas.append({"cliente_nome": item.get("cliente_nome"),
                                 "recibo": str(item.get("recibo") or ""),
                                 "portal": str(item.get("portal") or ""), "ok": False,
                                 "status": "retido", "motivo": motivo_janela})
            continue

        # 4) PRÉ-CONDIÇÕES, PARCELA POR PARCELA — cada uma com o motivo que a
        #    pessoa vai ler. Uma parcela que não passa sai do grupo; o grupo
        #    segue com as outras.
        vivas: List[Dict[str, Any]] = []
        for item in parcelas:
            portal_key = str(item.get("portal") or "").strip()
            recibo = str(item.get("recibo") or "").strip()
            rotulo = f"...{recibo[-4:]}" if recibo else "?"
            if not portal_key or not recibo:
                blockers.append("1 parcela sem seguradora ou sem recibo identificado: "
                                "nao cobrada (nao da para garantir que ela e unica)")
                await _incidente(company_id, "Parcela sem identificação",
                                 "Uma parcela veio sem seguradora ou sem recibo. Sem isso "
                                 "não dá para garantir que ela só será cobrada uma vez.")
                continue
            boleto = by_recibo.get(recibo)
            documento = _documento_do_boleto(item, boleto)
            if not documento:
                blockers.append(f"parcela {rotulo} ({seguradora}): o boleto nao esta no "
                                f"cofre — nao cobrada")
                continue
            if modalidade == "equipe":
                destino = so_digitos(cfg.get("team_number"))
            else:
                destino = so_digitos(item.get("whatsapp"))
                contato = str(item.get("contact_status") or "").strip().lower()
                if contato not in CONTATOS_ACEITOS:
                    blockers.append(f"parcela {rotulo} ({seguradora}): o telefone do cliente "
                                    f"nao esta confirmado ({contato or 'sem status'}) — nao cobrada")
                    continue
            if len(destino) < 10:
                blockers.append(f"parcela {rotulo} ({seguradora}): destino invalido — nao cobrada")
                continue
            vivas.append({"item": item, "portal_key": portal_key, "recibo": recibo,
                          "rotulo": rotulo, "documento": documento, "destino": destino})
        if not vivas:
            continue

        # ⚠️ UM destino por mensagem. Duas parcelas do mesmo segurado com
        #    telefones diferentes não cabem na mesma abordagem — e escolher um
        #    dos dois em silêncio seria mandar o boleto para o número errado.
        destino = vivas[0]["destino"]
        for viva in [v for v in vivas if v["destino"] != destino]:
            blockers.append(f"parcela {viva['rotulo']} ({seguradora}): o telefone desta "
                            f"parcela e diferente do da primeira parcela do mesmo segurado "
                            f"— nao cobrada nesta mensagem")
        vivas = [v for v in vivas if v["destino"] == destino]

        # 5) AS RESERVAS — uma por PARCELA, TODAS antes do primeiro efeito do
        #    grupo. Perdeu a reserva de uma parcela → essa parcela sai do grupo;
        #    perdeu todas → o grupo inteiro não sai.
        #
        #    🔴 A leitura do passo 2 é um retrato; a reserva é a decisão. Entre
        #    uma e outra cabe a execução da outra máquina.
        reservadas: List[Dict[str, Any]] = []
        for viva in vivas:
            item, recibo, rotulo = viva["item"], viva["recibo"], viva["rotulo"]
            portal_key = viva["portal_key"]
            anterior = ja_cobrado.get(f"{portal_key}|{recibo}") or {}
            estado_anterior = str(anterior.get("status") or "")
            try:
                reserva = await asyncio.to_thread(
                    _reservar_obrigacao, client, company_id=company_id,
                    portal_key=portal_key, recibo=recibo, modalidade=modalidade,
                    to_phone=destino, to_last4=destino[-4:],
                    cliente_nome=str(item.get("cliente_nome") or ""),
                    apolice_susep=str(item.get("apolice_susep") or ""),
                    routine_id=routine_id, work_run_id=work_run_id,
                    integration_id=integration_id, canario=canario,
                    segurado=chave_do_segurado)
            except Exception as exc:  # noqa: BLE001
                blockers.append(f"parcela {rotulo} ({seguradora}): nao consegui reservar a "
                                f"cobranca ({type(exc).__name__}) — NAO enviei")
                await _incidente(company_id, "Cobrança não reservada",
                                 f"A parcela {rotulo} da {seguradora} não pôde ser reservada. "
                                 f"Nada foi enviado para ela.")
                continue

            if str(reserva.get("status") or "") == "colisao_recibo":
                # 🔴 O recibo bateu na constraint ANTIGA `(company_id, recibo,
                #    send_mode)` porque OUTRA seguradora já tem uma obrigação com
                #    o mesmo número. Não é "já cobrado": é um cliente que o robô
                #    não consegue distinguir com segurança. RETÉM, com incidente,
                #    e a equipe cobra (aquecimento EXTRA-001, achado 8a). Vem ANTES
                #    da checagem do id: desde a 20260907_02 a função devolve id NULL
                #    neste ramo, para o id da OUTRA parcela nunca viajar.
                await _incidente(
                    company_id, "Cobrança retida: recibo igual ao de outra seguradora",
                    f"{seguradora} · recibo ...{recibo[-4:]} — a equipe precisa cobrar esta parcela")
                blockers.append(
                    f"parcela {rotulo} ({seguradora}): NAO cobrada — o numero do recibo e igual "
                    f"ao de outra seguradora ja cobrada; tarefa para a equipe")
                entregas.append({"cliente_nome": item.get("cliente_nome"), "recibo": recibo,
                                 "portal": portal_key, "ok": False, "status": "retido",
                                 "status_anterior": "colisao_recibo", "motivo": "colisao de recibo"})
                continue

            ledger_id = str(reserva.get("id") or "")
            if not ledger_id:
                blockers.append(f"parcela {rotulo} ({seguradora}): a reserva nao devolveu "
                                f"identificador — NAO enviei")
                continue

            somente_documento = False
            if not reserva.get("ganhou"):
                estado = str(reserva.get("status") or estado_anterior or "")
                if estado not in ESTADOS_RECLAMAVEIS:
                    # 🔴 E ELA APARECE. Uma parcela que não sai porque já está em
                    #    outro estado tem de ser LEGÍVEL no relatório — inclusive a
                    #    reserva órfã que ficou de um processo que morreu (`reservado`)
                    #    e a `incerto`, que ninguém vai reclamar automaticamente.
                    #    Sumir em silêncio é o que faz ninguém ir atrás (G19).
                    blockers.append(
                        f"parcela {rotulo} ({seguradora}): nao cobrada agora — "
                        f"{NOME_HUMANO_DO_ESTADO.get(estado, estado)} "
                        f"(estado no ledger: {estado})")
                    entregas.append({"cliente_nome": item.get("cliente_nome"), "recibo": recibo,
                                     "portal": portal_key, "ok": False, "status": "ja cobrado",
                                     "status_anterior": estado, "motivo": "ja cobrado"})
                    continue
                reclamou = await asyncio.to_thread(
                    _reclamar_obrigacao, client, ledger_id=ledger_id,
                    company_id=company_id, de_status=list(ESTADOS_RECLAMAVEIS))
                if not reclamou:
                    entregas.append({"cliente_nome": item.get("cliente_nome"), "recibo": recibo,
                                     "portal": portal_key, "ok": False, "status": estado,
                                     "motivo": "outra execucao pegou primeiro"})
                    continue
                # 🔴 `parcial` = o TEXTO já chegou; só o PDF faltou. Reenviar o texto
                #    seria uma segunda abordagem ao mesmo cliente pela mesma parcela.
                somente_documento = (estado == "parcial" and bool(anterior.get("text_ok")))

            reservadas.append({**viva, "ledger_id": ledger_id,
                               "somente_documento": somente_documento})

        if not reservadas:
            continue

        # 6) A PORTA ÚNICA. Nada aqui chama `send_*` diretamente.
        from app.services.platform_outbound import send_to_client_guarded

        anunciadas = [r for r in reservadas if not r["somente_documento"]]
        reparos = [r for r in reservadas if r["somente_documento"]]
        kind_do_texto = "billing_equipe" if modalidade == "equipe" else "billing_cliente"

        if modalidade == "equipe" and anunciadas:
            # A nota interna é uma mensagem à parte, e falhar nela não impede o
            # pacote — mas vira pendência: a atendente receberia texto e PDFs sem
            # saber de quem são. UMA por grupo, listando as N parcelas.
            nota = await _com_orcamento_do_governador(
                lambda: send_to_client_guarded(
                    company_id, destino,
                    _nota_interna_do_grupo({**grupo, "parcelas": [r["item"] for r in anunciadas]}, cfg),
                    kind="billing_equipe_nota",
                    summary=f"nota interna da cobranca ({seguradora})",
                    work_run_id=work_run_id, integration_id=integration_id,
                    autorizacao_de_auxiliar=True, enfileirar=False,
                    destino_interno=True, canario=canario),
                orcamento_s)
            orcamento_s = nota["orcamento"]
            if not (nota["res"] or {}).get("ok"):
                blockers.append(f"{len(anunciadas)} parcela(s) ({seguradora}): a nota interna "
                                f"para a equipe nao saiu "
                                f"({(nota['res'] or {}).get('reason') or 'sem motivo'})")

        # 🔴 UM texto por GRUPO, e ele é o das parcelas ANUNCIADAS agora. As que
        #    são reparo de `parcial` já tiveram o texto delas entregue antes —
        #    repeti-lo seria uma segunda abordagem pela mesma parcela.
        texto_do_grupo = (mensagem_do_grupo(
            {**grupo, "parcelas": [r["item"] for r in anunciadas]}, cfg) if anunciadas else "")
        # A sequência de chamadas à porta: o texto viaja com o PRIMEIRO PDF, e
        # cada PDF restante vai numa chamada de texto vazio — o caminho que
        # `_entregar_agora` já aceita para reparar um `parcial`.
        sequencia: List[tuple] = []
        for posicao, reservada in enumerate(anunciadas):
            sequencia.append((reservada, texto_do_grupo if posicao == 0 else "", True))
        for reservada in reparos:
            sequencia.append((reservada, "", False))

        texto_do_grupo_saiu = True
        parou_no_governador = False
        for reservada, texto, e_anunciada in sequencia:
            rotulo, recibo = reservada["rotulo"], reservada["recibo"]
            if e_anunciada and not texto_do_grupo_saiu:
                # O texto que anunciava esta parcela não saiu. Mandar só o PDF
                # seria um arquivo solto, de origem desconhecida para quem recebe.
                try:
                    await asyncio.to_thread(_marcar_estado, client, company_id,
                                            reservada["ledger_id"], status="adiado",
                                            last_error="o texto do grupo nao saiu")
                except Exception:  # noqa: BLE001
                    logger.error("[COBRANCA] nao consegui marcar adiado no ledger")
                entregas.append({"cliente_nome": reservada["item"].get("cliente_nome"),
                                 "recibo": recibo, "portal": reservada["portal_key"],
                                 "ok": False, "status": "adiado",
                                 "motivo": "o texto do grupo nao saiu",
                                 "ledger_id": reservada["ledger_id"], "modalidade": modalidade})
                continue

            chamada = await _com_orcamento_do_governador(
                lambda: send_to_client_guarded(
                    company_id, destino, texto,
                    kind=kind_do_texto,
                    summary=f"cobranca da parcela ({seguradora})",
                    work_run_id=work_run_id, integration_id=integration_id,
                    autorizacao_de_auxiliar=True,
                    documento=reservada["documento"], enfileirar=False,
                    destino_interno=(modalidade == "equipe"),
                    ledger_ref={"table": "billing_sent_log", "id": reservada["ledger_id"]},
                    canario=canario),
                orcamento_s)
            orcamento_s = chamada["orcamento"]
            res = chamada["res"] or {}

            entrada: Dict[str, Any] = {
                "cliente_nome": reservada["item"].get("cliente_nome"), "recibo": recibo,
                "portal": reservada["portal_key"], "to_last4": destino[-4:],
                "ok": bool(res.get("ok")), "doc_ok": res.get("doc_ok"),
                "ledger_id": reservada["ledger_id"], "modalidade": modalidade,
            }

            # 7) O ESTADO. Quem enviou já marcou; quem não enviou marca aqui.
            if res.get("ok"):
                entrada["status"] = str(res.get("status") or "aceito_pelo_canal")
                if e_anunciada and not str(texto or "").strip():
                    # 🔴 O TEXTO DESTA PARCELA SAIU — no texto do grupo, que
                    #    nomeia todas as parcelas anunciadas. A porta não pode
                    #    saber disso (ela recebeu texto vazio), e sem esta linha o
                    #    ledger diria que o componente texto nunca foi entregue.
                    try:
                        await asyncio.to_thread(_marcar_estado, client, company_id,
                                                reservada["ledger_id"], text_ok=True)
                    except Exception:  # noqa: BLE001
                        logger.error("[COBRANCA] nao consegui marcar text_ok no ledger")
                if res.get("ledger") == "falhou":
                    # 🔴 O efeito ACONTECEU e o registro não. `incerto` é a única
                    #    resposta honesta — e ele nunca é reclamado automaticamente.
                    entrada["status"] = "incerto"
                    try:
                        await asyncio.to_thread(_marcar_estado, client, company_id,
                                                reservada["ledger_id"],
                                                status="incerto",
                                                last_error="registro pos-envio falhou")
                    except Exception:  # noqa: BLE001
                        await _incidente(company_id, "Cobrança enviada sem registro completo",
                                         f"A parcela {rotulo} da {seguradora} foi enviada, mas o "
                                         f"registro do resultado falhou. NÃO reenvie sem conferir.")
                    blockers.append(f"parcela {rotulo} ({seguradora}): enviada, mas o registro "
                                    f"do resultado falhou — marcada como INCERTA, nao sera reenviada")
                elif entrada["status"] == "parcial":
                    blockers.append(f"parcela {rotulo} ({seguradora}): o texto saiu e o PDF nao "
                                    f"— pendente na lista da cobranca")
                    await _incidente(company_id, "Cobrança sem o boleto anexado",
                                     f"A parcela {rotulo} da {seguradora} saiu sem o PDF. "
                                     f"A lista de Pendências mostra a linha para reenviar o anexo.")
            else:
                motivo = str(res.get("reason") or "erro_envio")
                # ⚠️ Quando a PORTA já disse em que estado a linha ficou, é o dela
                #    que vale: só ela sabe se o efeito era possível (`incerto`).
                #    O mapa abaixo cobre as recusas que nem chegaram ao canal.
                estado = str(res.get("status") or "") or _ESTADO_POR_RECUSA.get(motivo, "falhou")
                entrada["status"] = estado
                entrada["motivo"] = motivo
                if not res.get("status"):
                    try:
                        await asyncio.to_thread(_marcar_estado, client, company_id,
                                                reservada["ledger_id"],
                                                status=estado, last_error=motivo[:200])
                    except Exception:  # noqa: BLE001
                        logger.error("[COBRANCA] nao consegui marcar %s no ledger", estado)
                motivo_humano = MOTIVO_EM_PORTUGUES.get(motivo, motivo)
                blockers.append(f"parcela {rotulo} ({seguradora}): nao enviada — {motivo_humano}")
                if estado == "falhou":
                    await _incidente(company_id, "Cobrança não enviada",
                                     f"A parcela {rotulo} da {seguradora} não saiu: {motivo_humano}. "
                                     f"Ela aparece na lista de Pendências.")
                if str(texto or "").strip():
                    # Era o texto do grupo: sem ele, os PDFs das outras parcelas
                    # anunciadas também não saem.
                    texto_do_grupo_saiu = False
                if motivo == "governador" and orcamento_s <= 0:
                    parou_no_governador = True

            entregas.append(entrada)
            if parou_no_governador:
                break

        if parou_no_governador:
            pendentes = max(0, len(fila) - len(entregas))
            blockers.append(
                f"governador de envio: parei em {len(entregas)} item(ns) — "
                f"{pendentes} ficaram para a proxima execucao (estao como 'adiado' "
                f"no ledger e serao retomados de la)")
            break

    return entregas


async def _com_orcamento_do_governador(chamar, orcamento_s: float) -> Dict[str, Any]:
    """Chama a porta; se o GOVERNADOR mandar esperar e couber no orçamento, espera.

    ⚠️ Esperar e tentar de novo é seguro porque `governar_envio` só consome o
    slot quando LIBERA (`_tentar_gate` é um `SET NX EX`). Uma recusa não gasta
    espaçamento de ninguém, então a segunda pergunta não é uma segunda reserva.

    ⚠️ `asyncio.sleep`, nunca `time.sleep`: congelar o event loop por seis
    minutos derrubaria o atendimento de TODAS as corretoras (a lição do Bloco H).
    """
    restante = float(orcamento_s)
    while True:
        res = await chamar()
        if res.get("ok") or str(res.get("reason") or "") != "governador":
            return {"res": res, "orcamento": restante}
        espera = float(res.get("esperar_s") or 0)
        if espera <= 0 or espera > restante:
            return {"res": res, "orcamento": 0.0}
        await asyncio.sleep(espera)
        restante -= espera


def _contagem_dos_estados(entregas: List[Dict[str, Any]]) -> Dict[str, int]:
    """Quantas ficaram em cada estado. É o que o relatório e a peça imprimem."""
    fora: Dict[str, int] = {}
    for entrada in entregas or []:
        estado = str(entrada.get("status") or "")
        if estado:
            fora[estado] = fora.get(estado, 0) + 1
    return fora


#: Como cada estado se chama para quem não escreveu o código.
NOME_HUMANO_DO_ESTADO = {
    "aceito_pelo_canal": "aceitas pelo WhatsApp",
    "entregue_equipe": "entregues à equipe",
    "parcial": "sem o boleto anexado",
    "incerto": "incertas (enviadas, registro falhou)",
    "falhou": "não enviadas",
    "adiado": "adiadas para a próxima execução",
    "liberado": "liberadas para reenvio",
    "suprimido": "o cliente pediu para não receber",
    "contestado": "o cliente contestou",
    "reservado": "reservadas e sem desfecho",
    "ja cobrado": "já cobradas antes",
}


# ==========================================================================
# SPEC-EXTRA-001.6 B4.2 — O SEGUNDO LEITOR DA FILA DE TELAS DESCONHECIDAS
# ==========================================================================
#
# O primeiro leitor é o card do portal na Central de Agentes
# (`app/core/central_de_agentes.telas_desconhecidas`). Este é o segundo, e ele
# existe porque os dois respondem perguntas diferentes:
#
#     o card ............. "o que estou deixando de entender, no acumulado?"
#     esta linha ......... "apareceu HOJE alguma tela que nunca apareceu antes?"
#
# 🔴 A segunda é a que chega a tempo. Uma tela nova é como um portal muda sem
# avisar; descobri-la no dia custa uma leitura, descobri-la no acumulado de 30
# dias custa a cobrança daquele portal enquanto ninguém olhar o card.
#
# ⛔ Nenhuma tabela nova (P-264, CLAUDE.md §5): a "fila" é a lista de jobs que a
# própria execução já tem em mãos, comparada com os hashes que o banco já viu.
TETO_DE_HASHES_ANTERIORES = 500
TAMANHO_DA_AMOSTRA_DE_TELA_NO_RELATORIO = 80


def _amostra_de_tela_do_relatorio(texto: Any) -> str:
    """O pedaço da tela que vai para o relatório — redigido, uma linha só.

    Se o redator não estiver disponível, a amostra sai VAZIA: um relatório sem a
    frase da tela continua útil; um relatório com o CPF do corretor não.
    """
    bruto = " ".join(str(texto or "").split())
    if not bruto:
        return ""
    try:
        from portal_worker.redaction import redigir_texto

        bruto = redigir_texto(bruto)
    except Exception:  # noqa: BLE001
        return ""
    return bruto[:TAMANHO_DA_AMOSTRA_DE_TELA_NO_RELATORIO]


def telas_novas_do_dia(client, company_id: Any, jobs: List[Dict[str, Any]],
                       agora: Optional[datetime] = None
                       ) -> Tuple[List[Dict[str, Any]], str]:
    """As telas que esta execução viu e que o banco NUNCA tinha visto antes de hoje.

    Devolve `(linhas, motivo_do_erro)`. 🔴 O erro volta ESCRITO em vez de virar
    lista vazia: sem ele, "nenhuma tela nova" e "não consegui olhar" viram a
    mesma linha no relatório — e a segunda é a que precisa de gente.

    ⚠️ A leitura filtra por `company_id` no código (CLAUDE.md §7): o backend usa
    service role, e a tela de uma corretora não é notícia para outra.
    """
    agora = agora or datetime.now(timezone.utc)
    vistas: Dict[str, Dict[str, Any]] = {}
    for job in (jobs or []):
        if not isinstance(job, dict):
            continue
        evidencia = job.get("evidence")
        tela = evidencia.get("tela") if isinstance(evidencia, dict) else None
        if not isinstance(tela, dict):
            continue
        assinatura = str(tela.get("hash") or "").strip()
        if not assinatura:
            continue
        linha = vistas.setdefault(assinatura, {
            "hash": assinatura, "portal": str(job.get("portal_key") or "?"),
            "vezes": 0, "amostra": "", "prova": str(tela.get("prova") or "")})
        linha["vezes"] += 1
        if not linha["amostra"]:
            linha["amostra"] = _amostra_de_tela_do_relatorio(tela.get("texto"))
    if not vistas:
        return [], ""

    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        res = (client.table("portal_jobs")
               .select("hash:evidence->tela->>hash")
               .eq("company_id", str(company_id))
               .in_("status", ["needs_human", "failed"])
               .lt("finished_at", inicio_do_dia)
               .limit(TETO_DE_HASHES_ANTERIORES)
               .execute())
        conhecidos = {str((r or {}).get("hash") or "") for r in (res.data or [])}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COBRANCA] historico de telas nao lido: %s", type(exc).__name__)
        return [], type(exc).__name__
    return [linha for assinatura, linha in sorted(vistas.items())
            if assinatura not in conhecidos], ""


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
    estados: Optional[Dict[str, int]] = None,
    aviso_ao_grupo: str = "",
    # 🔴 B4.2 — as telas que apareceram HOJE pela primeira vez, e o motivo de a
    # conferência não ter sido possível. Os dois vazios = ninguém perguntou, e a
    # seção inteira some (é assim que os chamadores antigos continuam idênticos).
    telas_novas: Optional[List[Dict[str, Any]]] = None,
    telas_erro: str = "",
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
    # SPEC-EXTRA-001 — as contagens dos modos REAIS, reconciliáveis com a fila.
    # 🔴 Uma linha por estado, com o nome que a pessoa entende. "3 enviadas" não
    # é uma contagem honesta quando uma delas saiu sem o boleto.
    if cfg.get("send_mode") in MODOS_REAIS and estados:
        rotulo = ("encaminhadas para a equipe" if cfg.get("send_mode") == "equipe"
                  else "enviadas ao cliente")
        lines.append(f"Modo {cfg.get('send_mode')} ({rotulo}):")
        for estado, quantos in sorted(estados.items()):
            lines.append(f"- {quantos} {NOME_HUMANO_DO_ESTADO.get(estado, estado)}")
    if cfg.get("send_mode") == MODO_RETIDO:
        lines.append(f"NADA FOI ENVIADO — {cfg.get('retido_motivo') or 'configuracao antiga'}.")
    if aviso_ao_grupo:
        lines.append(f"Aviso ao grupo humano: {aviso_ao_grupo}.")
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
    # 🔴 B4.2 — UMA linha por tela que apareceu HOJE pela primeira vez. Ela é o
    # segundo leitor da fila de telas desconhecidas, e é o que chega a tempo:
    # 📊 a Allianz gastou ≈100 s/dia por 25 dias produzindo a MESMA tela de
    # "Acesso negado" sem que nenhuma linha em lugar nenhum a mencionasse.
    for tela in (telas_novas or [])[:5]:
        amostra = str(tela.get("amostra") or "").strip() or "(sem texto legivel)"
        lines.append('tela nova hoje no portal %s: "%s" (vista %d×)'
                     % (tela.get("portal") or "?", amostra, int(tela.get("vezes") or 1)))
    if telas_erro:
        # ⚠️ "nenhuma tela nova" e "nao consegui olhar" NAO podem virar a mesma
        # linha. O silencio aqui seria uma afirmacao falsa.
        lines.append("Nao consegui conferir se apareceu tela nova nos portais (%s)." % telas_erro)
    if items:
        lines.append("Clientes encontrados:")
        for item in items[:20]:
            valor = item.get("valor")
            valor_txt = f"R$ {valor:.2f}" if isinstance(valor, (int, float)) else str(valor or "valor nao informado")
            # 🔴 B4.4: documento e telefone saem MASCARADOS daqui. Este texto vira
            # `routine_runs.output_full` — e 📊 7 de 49 execuções já estão gravadas
            # com o CPF do segurado em claro por causa desta linha (13/09/2026).
            # Os 4 últimos dígitos bastam para a atendente distinguir dois
            # homônimos; para DISCAR ela usa a nota interna.
            doc = _mascarar_documento(item.get("cpf_cnpj")) or "?"
            phone = (_mascarar_telefone(item.get("whatsapp"))
                     or f"sem telefone ({item.get('contact_status') or 'n/a'})")
            lines.append(
                f"- {item.get('cliente_nome') or 'Cliente'} | CPF/CNPJ {doc} | "
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


def _mascarar_telefone(valor: Any) -> str:
    """`5547999998888` → `...8888`. Serve para CONFERIR, não para discar.

    🔴 SPEC-EXTRA-001.6 B4.4. 📊 Medido em 13/09/2026: 7 de 49 execuções da
    cobrança têm CPF/CNPJ em claro em `routine_runs.output_full`, e o telefone
    saía inteiro na mesma linha (`select count(*) from routine_runs r join
    routines t on t.id=r.routine_id where t.config->>'kind'='billing_collection'
    and r.output_full like '%CPF/CNPJ%'`). O relatório integral é legível por
    qualquer sessão autenticada da corretora — é o lugar errado para o número do
    segurado.

    ⛔ Quem PRECISA do número inteiro é a atendente, e ela o recebe na nota
    interna (`_whatsapp_legivel`), que vai para o WhatsApp dela e não fica
    gravada em lugar nenhum. Três níveis de exposição, de propósito.
    """
    d = _digits(valor)
    return f"...{d[-4:]}" if len(d) >= 4 else ""


def compor_peca_da_cobranca(
    *,
    # A hora em que a varredura dos portais começou — a data do DADO. Quem não
    # a souber passa None, e a peça sai "gerada em", nunca "dados lidos em".
    inicio_da_varredura: Optional[datetime] = None,
    routine: Dict[str, Any],
    cfg: Dict[str, Any],
    items: List[Dict[str, Any]],
    boletos: List[Dict[str, Any]],
    fila: List[Dict[str, Any]],
    retidos: List[Dict[str, Any]],
    tarefas: List[Dict[str, Any]],
    blockers: List[str],
    test_sends: List[Dict[str, Any]],
    estados: Optional[Dict[str, int]] = None,
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
    elif modo == MODO_RETIDO:
        blocos.append({"block": "callout", "props": {
            "tone": "warning", "title": "Configuração antiga",
            "text": (str(cfg.get("retido_motivo") or "")
                     or "Escolha uma modalidade na tela do Auxiliar.")
                    + " Nada foi enviado nesta execução.",
        }})
    elif modo in MODOS_REAIS and estados:
        # 🔴 A peça repete as MESMAS contagens do relatório — ela não conta nada
        # por conta própria. Duas contagens da mesma execução divergindo é o que
        # o corretor descobre comparando as duas na frente de alguém.
        blocos.append({"block": "kpis", "props": {
            "title": ("O que foi encaminhado à equipe" if modo == "equipe"
                      else "O que foi enviado ao cliente"),
            "items": [{"label": NOME_HUMANO_DO_ESTADO.get(estado, estado),
                       "value": str(quantos)}
                      for estado, quantos in sorted(estados.items())],
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
                                blocos: List[Dict[str, Any]],
                                inicio_da_varredura: Optional[datetime] = None,
                                work_run_id: Optional[str] = None) -> Optional[str]:
    """Cria, renderiza e publica a peça. Devolve o id, ou None.

    🔴 CONSERTO MEDIDO (SPEC-EXTRA-001 U1, fora do escopo original): esta função
    usava `inicio_da_varredura` **sem recebê-lo** — era um nome livre, e a
    chamada levantava `NameError` sempre. O `except` do chamador engolia tudo e
    escrevia `[COBRANCA] peca nao gerada: NameError` no log do contêiner, onde
    ninguém olha. Ou seja: desde a SPEC-095 B.2 a peça da Cobrança **nunca foi
    publicada**, e o sintoma era invisível de fora. Agora ele é um parâmetro.

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
        # `work_run_id`: quando a rotina roda pela PONTE (`WORK_RUNS_ROUTINE_BRIDGE`,
        # `workflows.bridge_rotina`), o run existe e agora viaja até aqui
        # (P-098-RUN-NOS-JOBS, parcial). Quando ela roda in-process, continua
        # `None` — e inventar um Work Run só para preencher a coluna seria o
        # segundo motor que a SPEC-078 e o CLAUDE.md §5 proíbem.
        work_run_id=work_run_id or None,
        # 🔴 SPEC-095 · B.1: a identidade da peça de Cobrança já era o id da
        # rotina — 📊 preenchida em 5/5 execuções, os únicos `subject_ref.id`
        # não vazios de todo o banco (5/136). Ganhou só o `produtor`, que é o
        # que a lista imprime como "de quem é" quando o mapa de tipos não
        # conhece o template (📊 25,7% das peças abriam sem produtor).
        subject_ref={"kind": "routine", "id": str(routine.get("id") or ""),
                     "label": str(routine.get("name") or "Cobrança Feita"),
                     "produtor": "cobranca-feita"},
        # A hora em que a varredura dos portais COMEÇOU — a data do DADO, e não
        # a da escrita (§1.9: `data_as_of` era `now()` em 136/136 versões; 📊
        # 04/09/2026 o red team pegou esta linha gravando `now()` de novo).
        # Sem ela, NULL — e a tela não afirma frescor.
        data_as_of=inicio_da_varredura,
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
        # Pela RPC, e não por `.schema("storage").table("objects")`: 📊
        # `storage` não está entre os schemas expostos pelo PostgREST, e a
        # leitura direta devolveria 404 — a purga passaria a "não achar nada"
        # em silêncio, que é a pior forma de uma retenção falhar.
        #
        # `empresa` existe porque o caminho começa pelo dono
        # (`{company_id}/{portal_key}/{job_id}/…`): dá para ligar a purga para
        # uma corretora e não para todas.
        res = client.rpc("portal_evidence_vencidas",
                         {"dias": max(prazo, 1), "empresa": company_id}).execute()
        alvos = [str(o.get("name") or "") for o in (res.data or []) if o.get("name")]
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


def _blocker_do_job(job: Dict[str, Any]) -> str:
    """O que o relatório diz sobre um portal que NÃO terminou `done`.

    SPEC-EXTRA-001.6 P0.2 — o motivo do portal aparece, inclusive no `failed`.

    🔴 `evidence.message` PRIMEIRO, e `error` como segunda opção. 📊 13/09/2026:
    `error` é NULL em 100% dos jobs de cobrança da história — o worker o limpa
    ao finalizar (`portal_worker/worker.py:944`) — e `evidence.message` está
    preenchido em 100% deles. A Mapfre já escrevia *"a MAPFRE recusou a
    credencial (autenticacao invalida)"* e a linha do relatório lia `error`.
    Manter `error` como fallback preserva o caso do requeue.
    """
    status = str((job or {}).get("status") or "")
    portal = (job or {}).get("portal_key")
    motivo = ((job or {}).get("evidence") or {}).get("message") or (job or {}).get("error")
    if status == "needs_human":
        return f"portal {portal}: precisa de humano ({motivo or 'revisao'})"
    if status in {"failed", "timeout"}:
        return f"portal {portal}: {status} — {motivo or 'sem motivo registrado'}"
    return ""


# ==========================================================================
# SPEC-EXTRA-001.6 · B3.1 — O CANÁRIO DE LOGIN, SEM SCHEDULER NOVO
# ==========================================================================
#
# 📊 Medido em 13/09/2026: `login_check` existe nas 6 journeys
# (`portal_worker/journeys/__init__.py`) e NINGUÉM o enfileirava — este arquivo
# escrevia `"journey": "cobranca_sweep"` fixo. A Allianz gastou ≈100 s por dia,
# por 25 dias, para produzir a mesma linha de erro.
#
# 🔴 NENHUM MOTOR NOVO (CLAUDE.md §5): a rotina já é diária, então "canário
# diário" e "prólogo da rotina" são o MESMO relógio. Sem scheduler, sem fila,
# sem watchdog — o mesmo `portal_jobs`, o mesmo worker, uma jornada diferente. E
# o veredito é de minutos antes, não de ontem.
#
#: Quanto tempo o `fora_do_ar` mantém o circuito ABERTO (padrão Circuit Breaker
#: da Microsoft, §13 E3 da proposta). 💭 6 h. Clamp 1–72: abaixo de 1 h o breaker
#: não protege nada, e acima de 3 dias ele vira esquecimento.
PORTAL_BREAKER_HORAS_PADRAO = 6
#: Quanto a rotina espera o canário de cada portal. 💭 120 s (o login leva ≈100 s).
BILLING_LOGIN_CHECK_TETO_S_PADRAO = 120
#: O vocabulário de `portal_accounts.health` — contrato com o portal-worker, que
#: é quem ESCREVE (`portal_worker/worker.py`: `SAUDE_CREDENCIAL_RECUSADA`,
#: `SAUDE_FORA_DO_AR`, `VOCABULARIO_DE_SAUDE`). `unknown` é o meio-aberto do
#: padrão: tenta UMA vez, e a tentativa é o próprio canário.
#:
#: 🔴 UMA lista, UM lugar: o vocabulário de saúde mora em `portal_worker.worker`
#: (quem o ESCREVE). Importa-se de lá, na mesma direção que
#: `_portais_que_sei_varrer` já usa. O fallback literal existe só para o caso em
#: que o pacote do worker não está no PYTHONPATH deste processo — e o guarda
#: G10 prova que os dois valores batem com os do worker quando ele importa.
try:
    from portal_worker.worker import SAUDE_CREDENCIAL_RECUSADA, SAUDE_FORA_DO_AR
except Exception:  # noqa: BLE001
    SAUDE_CREDENCIAL_RECUSADA, SAUDE_FORA_DO_AR = "credencial_recusada", "fora_do_ar"
HEALTH_DE_BREAKER_ABERTO = (SAUDE_CREDENCIAL_RECUSADA, SAUDE_FORA_DO_AR)


def portal_breaker_horas(env: Optional[Dict[str, str]] = None) -> int:
    fonte = env if env is not None else os.environ
    return _int_clamped(fonte.get("PORTAL_BREAKER_HORAS"), PORTAL_BREAKER_HORAS_PADRAO, 1, 72)


def login_check_teto_s(env: Optional[Dict[str, str]] = None) -> int:
    fonte = env if env is not None else os.environ
    return _int_clamped(fonte.get("BILLING_LOGIN_CHECK_TETO_S"),
                        BILLING_LOGIN_CHECK_TETO_S_PADRAO, 30, 600)


def _breaker_aberto(portal_key: str, account: Dict[str, Any], horas: int) -> str:
    """A frase do relatório quando o circuito está ABERTO. `""` = pode tentar.

    ⛔ `credencial_recusada` **só fecha por gesto humano**: salvar a senha nova
    põe `health='unknown'` (`app/api/portal.py`), e aí a execução seguinte testa
    uma vez. Tentar de novo sozinho é bater na porta trancada — e, em portal de
    seguradora, é como se bloqueia a conta da corretora.
    """
    health = str((account or {}).get("health") or "").strip().lower()
    if health == SAUDE_CREDENCIAL_RECUSADA:
        return (f"portal {portal_key}: senha recusada pelo portal — atualize a senha em "
                f"Personalizacao > Conectores > Portais (o robo nao tenta de novo ate isso)")
    if health == SAUDE_FORA_DO_AR:
        desde = _para_datetime((account or {}).get("updated_at"))
        if desde is None:
            # Sem a hora, não dá para saber se o prazo passou. O breaker de um
            # estado sem data seria eterno: melhor tentar uma vez.
            return ""
        idade = (datetime.now(timezone.utc) - desde).total_seconds() / 3600.0
        if idade < horas:
            falta = max(1, int(round(horas - idade)))
            return (f"portal {portal_key}: fora do ar desde {desde.strftime('%d/%m %H:%M')} "
                    f"— tento de novo em {falta} h")
    return ""


async def _canario_de_login(client, routine: Dict[str, Any], cfg: Dict[str, Any],
                            blockers: List[str],
                            jobs_vistos: Optional[List[Dict[str, Any]]] = None
                            ) -> Dict[str, Dict[str, Any]]:
    """Enfileira um `login_check` por portal e devolve SÓ os que entraram.

    Devolve `{portal_key: account}`. Quem não está no dicionário não vira
    `cobranca_sweep` — e o motivo já está escrito no relatório, em português.
    """
    company_id = str(routine.get("company_id") or "")
    sei_varrer = set(_portais_que_sei_varrer())
    horas = portal_breaker_horas()
    contas: Dict[str, Dict[str, Any]] = {}
    jobs: Dict[str, str] = {}
    # ⚠️ A lista sai para uma variável de propósito: `for portal_key in
    # selected_portal_keys(cfg):` é a ÂNCORA do guarda da data do dado
    # (`test_o_relatorio_abre_pelo_achado`, [B2]), que confere que o carimbo da
    # varredura vem ANTES do laço dos portais. Duas cópias literais daquela linha
    # fariam o `find` dele achar a primeira e medir outra coisa.
    portais_selecionados = selected_portal_keys(cfg)
    for portal_key in portais_selecionados:
        if portal_key not in sei_varrer:
            # O laço da varredura já escreve a linha deste caso. Uma segunda
            # cópia da mesma frase só duplicaria o relatório.
            continue
        try:
            account = await asyncio.to_thread(_portal_account, client, company_id, portal_key)
        except Exception as e:  # noqa: BLE001
            blockers.append(f"portal {portal_key}: nao consegui ler a credencial "
                            f"({type(e).__name__}) — nao varri este portal")
            continue
        if not account:
            blockers.append(
                f"portal {portal_key}: sem credencial conectada "
                f"— cadastre em Personalizacao > Conectores > Portais")
            continue
        fechado = _breaker_aberto(portal_key, account, horas)
        if fechado:
            blockers.append(fechado)
            continue
        try:
            job_id = await asyncio.to_thread(_enqueue_job, client, routine, portal_key,
                                             account, cfg, journey=JORNADA_DO_CANARIO)
        except Exception as e:  # noqa: BLE001
            job_id = None
            logger.warning("[billing] canario de login nao enfileirado: %s", type(e).__name__)
        if not job_id:
            blockers.append(f"portal {portal_key}: falha ao enfileirar o teste de entrada "
                            f"(login) — nao varri este portal")
            continue
        jobs[portal_key] = job_id
        contas[portal_key] = account

    if not jobs:
        return contas

    # Em PARALELO: seis logins em série seriam dez minutos antes de a primeira
    # varredura começar.
    teto = login_check_teto_s()
    resultados = await asyncio.gather(
        *[_poll_job(client, job_id, teto) for job_id in jobs.values()],
        return_exceptions=True)
    for portal_key, resultado in zip(list(jobs.keys()), resultados):
        # 🔴 B4.2 — o desfecho do canário entra na lista de jobs da execução. É no
        # LOGIN que a tela desconhecida mora: 📊 as duas telas não-`done` de
        # 10–11/09 da Allianz e da Mapfre são telas de login ("Acesso negado",
        # "Autenticação inválida!"). Sem esta linha, a fila de telas novas do dia
        # olharia só a varredura — que nem chega a rodar quando o login falha.
        if isinstance(resultado, dict) and jobs_vistos is not None:
            jobs_vistos.append({**resultado, "portal_key": resultado.get("portal_key") or portal_key})
        if isinstance(resultado, BaseException):
            blockers.append(f"portal {portal_key}: o teste de entrada nao respondeu "
                            f"({type(resultado).__name__}) — nao varri este portal")
            contas.pop(portal_key, None)
            continue
        if str((resultado or {}).get("status") or "") == "done":
            continue
        # 🔴 O motivo vem de `_blocker_do_job` — o texto REAL que o portal deu
        #    (P0.2). Sem ele a linha diria "falhou" e mais nada.
        linha = _blocker_do_job({**(resultado or {}),
                                 "portal_key": (resultado or {}).get("portal_key") or portal_key})
        blockers.append((linha or f"portal {portal_key}: o teste de entrada nao terminou")
                        + " — nao varri este portal nesta execucao")
        contas.pop(portal_key, None)
    return contas


async def execute_billing_collection_routine(supabase, routine: Dict[str, Any], *,
                                             work_run_id: Optional[str] = None) -> str:
    """A execução da rotina de cobrança.

    ⚠️ `work_run_id` é keyword-only e opcional: quando a rotina roda pela ponte
    (`WORK_RUNS_ROUTINE_BRIDGE=1` → `workflows.bridge_rotina`), o run existe e
    passa a viajar até o ledger, a porta de saída e a peça. Quando ela roda
    in-process — o caminho de hoje — continua `None`, e nada muda.
    """
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
    # SPEC-095 B.2 — a data do DADO é a hora em que a leitura dos portais COMEÇA.
    # 📊 04/09/2026, red team: a peça gravava `datetime.now()` no ato de
    # publicar e a tela dizia "Dados lidos em" sobre o carimbo da escrita — o
    # §1.9 reentrando pelo único publicador que a SPEC tratou como certo. Quem
    # sabe a hora da varredura é esta função, e ela a passa adiante.
    inicio_da_varredura = datetime.now(timezone.utc)
    sei_varrer = set(_portais_que_sei_varrer())
    # 🔴 B3.1 — O CANÁRIO PRIMEIRO. Um `login_check` por portal ANTES de qualquer
    # varredura: quem não entra hoje não gasta 100 s de navegador para descobrir
    # isso no meio do caminho, e a corretora lê o motivo no relatório.
    jobs_do_canario: List[Dict[str, Any]] = []
    aprovados_pelo_canario = await _canario_de_login(client, routine, cfg, blockers,
                                                     jobs_do_canario)
    for portal_key in selected_portal_keys(cfg):
        try:
            if portal_key not in sei_varrer:
                blockers.append(
                    f"portal {portal_key}: selecionado, mas ainda NAO tem automacao de cobranca "
                    f"— nenhum inadimplente deste portal entrou nesta execucao")
                continue
            account = aprovados_pelo_canario.get(portal_key)
            if account is None:
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
        linha = _blocker_do_job(job)
        if linha:
            blockers.append(linha)

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
        # Em teste o destino e SEMPRE o `test_number`; o telefone do segurado
        # nao entra na conta. Ver o comentario em `fila_de_cobranca`.
        modo_teste=(str(cfg.get("send_mode") or "") == "test"),
    )
    for motivo, quantos in sorted(
        {r.get("retido_por", "?"): sum(1 for x in retidos if x.get("retido_por") == r.get("retido_por"))
         for r in retidos}.items()
    ):
        blockers.append(f"{quantos} inadimplente(s) nao cobrado(s): {motivo}")

    # ======================================================================
    # SPEC-EXTRA-001 — O DESPACHO POR MODALIDADE, num lugar só
    # ======================================================================
    #
    # 📊 Antes, a decisão do que fazer com a fila estava espalhada: uma chamada
    # incondicional a `_send_test_messages` aqui e uma cadeia de `elif` de
    # blockers 40 linhas abaixo, DEPOIS de a entrega já ter acontecido. Duas
    # metades da mesma decisão em dois lugares é como `live` conseguiu existir
    # na tela por semanas sem existir no produto.
    approval_id = None
    modo = str(cfg.get("send_mode") or "")
    entregas: List[Dict[str, Any]] = []
    if not fila:
        pass
    elif modo == "test":
        # ⛔ INTACTO. O modo teste de 17/08/2026 é o CONTROLE desta SPEC.
        entregas = await _send_test_messages(client, routine, fila, boletos, cfg, blockers)
    elif modo in MODOS_REAIS:
        entregas = await _entregar_cobranca_real(
            client, routine, fila, boletos, cfg, blockers, work_run_id=work_run_id)
    elif modo == MODO_RETIDO:
        blockers.append(
            f"{cfg.get('retido_motivo') or 'configuracao antiga'} — "
            f"nenhuma mensagem saiu nesta execucao "
            f"(modo gravado: {cfg.get('send_mode_original')})")
    elif modo == "none":
        blockers.append("modo somente relatorio: nenhuma mensagem sera enviada ao cliente")
    test_sends = entregas
    estados = _contagem_dos_estados(entregas) if modo in MODOS_REAIS else {}

    # OS AVISOS AO GRUPO HUMANO. Saem depois da entrega, porque o resumo precisa
    # saber quantos sairam. Nenhum deles fala com segurado.
    from app.services import billing_avisos as avisos

    nome_corretora = str(cfg.get("brokerage_name") or "Corretora")
    # ⛔ SPEC-EXTRA-001 §0.3 — no canário o grupo real da corretora fica FORA.
    #    As três chamadas passam a mesma decisão; deixar uma sem `suprimir=`
    #    mandaria um aviso sobre parcelas sintéticas para gente de verdade.
    suprimir_aviso = bool(cfg.get("canario"))
    aviso_ao_grupo = "suprimido (canario)" if suprimir_aviso else "sem novidade"
    tarefas = tarefas_para_a_equipe(items, cfg)
    if tarefas:
        enviado = await avisar_suporte_humano(
            client, company_id, avisos.aviso_de_tarefas(nome_corretora, tarefas), "tarefas",
            suprimir=suprimir_aviso)
        aviso_ao_grupo = ("suprimido (canario)" if suprimir_aviso
                          else ("enviado" if enviado else "falhou ou sem destino cadastrado"))
        if not enviado and not suprimir_aviso:
            blockers.append(
                f"{len(tarefas)} tarefa(s) para a equipe NAO foram avisadas no WhatsApp "
                f"— a corretora nao tem grupo de suporte cadastrado (veja abaixo)")

    # O guarda: portal que respondeu mas nao deixou ler. Vai para a EQUIPE,
    # nunca para o segurado — ele nao tem o que fazer com essa informacao.
    for job in jobs:
        estagio = str(((job.get("evidence") or {}).get("captured") or {}).get("stage")
                      or (job.get("evidence") or {}).get("stage") or "")
        o_que_houve = O_QUE_HOUVE_POR_ESTAGIO.get(estagio)
        if o_que_houve:
            await avisar_suporte_humano(
                client, company_id,
                avisos.aviso_de_portal(
                    nome_corretora,
                    NOME_DA_SEGURADORA.get(str(job.get("portal_key") or ""), str(job.get("portal_key") or "")),
                    o_que_houve),
                "portal", suprimir=suprimir_aviso)

    sem_telefone = [r for r in retidos if "sem telefone" in str(r.get("retido_por") or "")]
    await avisar_suporte_humano(
        client, company_id,
        avisos.aviso_de_resumo(
            nome_corretora,
            seguradoras=[NOME_DA_SEGURADORA.get(p, p) for p in (cfg.get("portal_keys") or [])],
            enviados=len([s for s in test_sends if s.get("ok")]),
            pendentes=max(0, len(fila) - len(test_sends)),
            tarefas=len(tarefas),
            sem_telefone=sem_telefone,
            # 🔴 O grupo lê "entregue à EQUIPE" no modo equipe — nunca "enviado"
            #    sem dizer a quem (painel 07/09, lente produto+DADO P2).
            modalidade=str(cfg.get("send_mode") or "test")),
        "resumo", suprimir=suprimir_aviso)
    # ⚠️ A cadeia de `elif` que ficava AQUI — a que explicava `approval` e
    # `live` depois de a entrega já ter acontecido — subiu para o despacho por
    # modalidade, junto com a decisão que ela descrevia. Ver o bloco
    # "O DESPACHO POR MODALIDADE" acima.

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
                "estados": estados,
            },
            compor_peca_da_cobranca(
                routine=routine, cfg=cfg, items=items, boletos=boletos,
                fila=fila, retidos=retidos, tarefas=tarefas,
                blockers=blockers, test_sends=test_sends, estados=estados,
                inicio_da_varredura=inicio_da_varredura),
            inicio_da_varredura,
            work_run_id,
        )
        if artifact_id:
            logger.info("[COBRANCA] peca publicada no Artifact Hub: %s", artifact_id)
    except Exception as exc:  # noqa: BLE001
        # Sem PII no log — nem o nome da corretora. Só o tipo do erro.
        logger.warning("[COBRANCA] peca nao gerada: %s", type(exc).__name__)

    # 🔴 B4.2: a fila de telas desconhecidas ganha o seu segundo leitor aqui.
    # Ela NUNCA pode derrubar a execução da cobrança — o relatório é o produto,
    # e esta linha é um extra dentro dele.
    try:
        # ⚠️ `client`, não `supabase`: quem tem `.table()` é o postgrest de dentro
        # do wrapper (`_client`, `:858`). Passar o wrapper faria a leitura levantar
        # AttributeError toda execução, e o relatório diria "não consegui
        # conferir" para sempre — falha silenciosa e permanente.
        telas_novas, telas_erro = telas_novas_do_dia(
            client, company_id, jobs_do_canario + jobs)
    except Exception as exc:  # noqa: BLE001
        telas_novas, telas_erro = [], type(exc).__name__

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
        estados=estados,
        aviso_ao_grupo=aviso_ao_grupo,
        telas_novas=telas_novas,
        telas_erro=telas_erro,
    )
