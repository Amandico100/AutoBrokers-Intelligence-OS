"""Um vocabulário só para o estado do canal de WhatsApp.

O problema
----------
Havia três vocabulários para a mesma coisa, e ninguém tinha percebido:

    pareamento escreve ....  "connecting" / "connected"
    webhook escreve .......  "open" / "close" / "connecting"   (vocabulário do Evolution)
    telas leem ............  "connected"

Resultado, medido em 28/07/2026 com a Resulta já pareada e funcionando: o
Evolution Go dizia `connected: true`, o banco dizia `"connecting"`, e a tela do
Admin mostrava **`unknown`**.

Nada quebrou — o card do dashboard lê o estado ao vivo e mostrou "Conectado"
corretamente. Mas o Admin lê o banco, e ficou mentindo.

É a mesma família do `master` × `master_admin` que trancou o Founder fora do
próprio Admin: igualdade de string entre vocabulários que ninguém unificou.

A regra
-------
Este arquivo é o **único** tradutor. Quem grava `channel_status` passa por aqui;
quem lê compara com as constantes daqui. Um estado desconhecido vira
`DESCONHECIDO` de propósito, e não `"connected"` — inventar conexão que não se
confirmou é pior que admitir que não se sabe.

O segundo problema, um vocabulário depois
-----------------------------------------
Unificar as palavras não bastou. 📊 Medido em 03/08/2026 no banco de produção
(``SELECT id, purpose, is_active, channel_status, last_seen_at,
now() - last_seen_at FROM integrations``):

    observer   6c9c55e2…  connected    último sinal 29/07 18:49   4 dias
    observer   04b5cdbc…  connected    último sinal 29/07 18:48   4 dias
    observer   3aa75902…  connecting   último sinal 28/07 13:39   5 dias

Três canais ativos afirmando um estado que ninguém confirma há quatro ou cinco
dias — e um deles preso em "Conectando…", que promete um progresso que não
existe. **Nenhum vigia desmente.** É a mesma classe do `work_run` em `queued`
sem lease: o registro sobrevive ao fato que ele descrevia.

E a causa é mais simples do que parece: **nada renovava `last_seen_at`**. A
coluna só é escrita quando chega um `connection.update` do Evolution
(``webhook.py`` e ``observer_intake.py``) ou no pareamento. Evento de transição
não chega em canal parado — logo o silêncio era indistinguível da saúde.

Por isso o heartbeat abaixo **confirma antes de contestar**: ele pergunta ao
provedor e, quando a resposta vem, grava `last_seen_at`. Só aí a idade da coluna
vira evidência, e "ninguém confirmou isto há 15 minutos" passa a significar
alguma coisa. O nome da coluna deixa de mentir: `last_seen_at` é quando o canal
foi visto de verdade, não quando ele resolveu falar.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

CONECTADO = "connected"
CONECTANDO = "connecting"
DESCONECTADO = "disconnected"
APOSENTADO = "retired"
DESCONHECIDO = "unknown"

# Todo jeito que já vimos cada estado ser escrito — pelo Evolution v2, pelo GO,
# pelo pareamento e pelas telas. A lista cresce quando aparecer um novo; o que
# não pode é cada leitor conhecer um pedaço dela.
_TRADUCAO = {
    # conectado
    "open": CONECTADO, "connected": CONECTADO, "online": CONECTADO,
    "loggedin": CONECTADO, "logged_in": CONECTADO,
    # conectando
    "connecting": CONECTANDO, "pairing": CONECTANDO, "qr": CONECTANDO,
    "qrcode": CONECTANDO, "syncing": CONECTANDO,
    # desconectado
    "close": DESCONECTADO, "closed": DESCONECTADO, "disconnected": DESCONECTADO,
    "logout": DESCONECTADO, "logged_out": DESCONECTADO, "offline": DESCONECTADO,
    "qr_expired": DESCONECTADO, "timeout": DESCONECTADO,
    # aposentado
    "retired": APOSENTADO, "archived": APOSENTADO, "deleted": APOSENTADO,
}


def normalizar_estado(bruto: object) -> str:
    """Traduz qualquer forma conhecida para o vocabulário único."""
    chave = str(bruto or "").strip().lower().replace("-", "_")
    return _TRADUCAO.get(chave, DESCONHECIDO)


def esta_conectado(bruto: object) -> bool:
    """A única pergunta que a maioria das telas faz.

    Devolve `True` só quando o estado é reconhecidamente conectado. Estado
    desconhecido é `False`: uma tela que mostra "Conectado" sem confirmação faz
    o corretor achar que os segurados estão sendo atendidos quando não estão.
    """
    return normalizar_estado(bruto) == CONECTADO


def rotulo_humano(bruto: object) -> str:
    """O que aparece para uma pessoa — nunca a palavra crua do protocolo."""
    return {
        CONECTADO: "Conectado",
        CONECTANDO: "Conectando…",
        DESCONECTADO: "Desconectado",
        APOSENTADO: "Aposentado",
    }.get(normalizar_estado(bruto), "Estado desconhecido")


# ===========================================================================
# HEARTBEAT — o vigia que desmente o canal (SPEC-063 Bloco V)
# ===========================================================================
#
# Mora AQUI, e não num módulo novo, porque este arquivo já é o dono declarado
# do estado do canal. Contestar o estado é a outra metade de traduzi-lo: quem
# define o vocabulário é quem tem de dizer quando a palavra deixou de valer.
# O agendador é o APScheduler que já existe (`app/tasks/buffer_processor.py`);
# nenhum motor novo foi criado (CLAUDE.md §5).
#
# POR QUE 15 MINUTOS
# ------------------
# O heartbeat roda a cada 5 min e o limite de obsolescência é 15 — três
# ciclos. Um ciclo perdido é ruído normal (deploy, reinício do Evolution,
# soluço de rede); três seguidos são um padrão. E 15 minutos é curto o
# bastante para que o corretor que caiu às 9h não passe a manhã inteira
# acreditando que está atendendo. Os dois números são ajustáveis por ambiente
# (`CHANNEL_HEARTBEAT_INTERVAL_MINUTES`, `CHANNEL_HEARTBEAT_STALE_MINUTES`)
# porque o certo aqui depende do provedor, não de uma verdade universal.
#
# O QUE ELE NÃO FAZ, DE PROPÓSITO
# -------------------------------
# Não manda WhatsApp. O aviso ao corretor já tem dono (`alerts.py`, pelo
# caminho do webhook) e disparar mensagem de dentro de um laço de 5 em 5
# minutos é a receita mais curta para o corretor silenciar os avisos. O que
# ele faz é **gravar a verdade** — e a verdade gravada acorda sozinha os
# vigias que já existem: `esta_conectado()` para as telas, o detector
# `conexoes.conexao_degradada` da SPEC-059 para o briefing, e a Caixa do Admin
# via `alerta_de_plataforma` (incidente com chave estável, um por canal, não um
# por varredura).

LIMITE_OBSOLETO_MINUTOS = 15
TIMEOUT_SONDA_SEGUNDOS = 8.0

# Só o Evolution GO tem sonda de estado implementada aqui. Marcar um provedor
# que não sabemos perguntar seria transformar a nossa ignorância em acusação.
PROVEDORES_SONDAVEIS = ("evolution-go",)

# Estados que AFIRMAM que está tudo bem. São os únicos que vale a pena
# contestar: quem já diz `disconnected` não está mentindo, está esperando.
ESTADOS_QUE_AFIRMAM = (CONECTADO, CONECTANDO)


def _env_int(nome: str, padrao: int, minimo: int = 1) -> int:
    try:
        return max(minimo, int(os.getenv(nome, str(padrao))))
    except (TypeError, ValueError):
        return padrao


def heartbeat_ligado() -> bool:
    """Interruptor de emergência. Ligado por padrão — um vigia desligado por
    default é um vigia que ninguém liga."""
    return str(os.getenv("CHANNEL_HEARTBEAT_ENABLED", "1")).strip().lower() not in (
        "0", "false", "no", "off",
    )


def limite_obsoleto_minutos() -> int:
    return _env_int("CHANNEL_HEARTBEAT_STALE_MINUTES", LIMITE_OBSOLETO_MINUTOS)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def ler_instante(bruto: object) -> Optional[datetime]:
    """Lê o `last_seen_at` em qualquer forma que o PostgREST devolva.

    Já vimos ``2026-07-29T18:49:02.368809+00:00``, ``…+00`` (offset de duas
    casas), ``…Z`` e o valor cru sem fuso. Data que não se consegue ler devolve
    ``None`` — e ``None`` conta como "nunca vi", que é o lado seguro.
    """
    if isinstance(bruto, datetime):
        return bruto if bruto.tzinfo else bruto.replace(tzinfo=timezone.utc)
    texto = str(bruto or "").strip()
    if not texto:
        return None
    texto = texto.replace("Z", "+00:00").replace("z", "+00:00")
    if re.search(r"[+-]\d{2}$", texto):
        texto += ":00"
    try:
        instante = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)


def idade_em_minutos(last_seen_at: object, agora: Optional[datetime] = None) -> Optional[float]:
    """Há quantos minutos alguém confirmou este canal. ``None`` = nunca."""
    visto = ler_instante(last_seen_at)
    if visto is None:
        return None
    return ((agora or _agora()) - visto).total_seconds() / 60.0


def esta_obsoleto(last_seen_at: object, agora: Optional[datetime] = None,
                  limite_minutos: Optional[int] = None) -> bool:
    """O estado gravado ainda é evidência, ou já é lembrança?"""
    idade = idade_em_minutos(last_seen_at, agora)
    if idade is None:
        return True  # nunca confirmado é o caso mais obsoleto que existe
    return idade > float(limite_minutos if limite_minutos is not None
                         else limite_obsoleto_minutos())


def estado_da_sonda(payload: object) -> str:
    """Traduz a resposta de ``GET /instance/status`` do Evolution GO.

    Mesma leitura de `whatsapp_channel._go_status_payload` — `LoggedIn` é a
    sessão do WhatsApp de pé; `Connected` sozinho é só o websocket, ou seja,
    ainda conectando.
    """
    corpo = payload if isinstance(payload, dict) else {}
    dados = corpo.get("data") if isinstance(corpo.get("data"), dict) else corpo
    logado = bool(dados.get("LoggedIn") or dados.get("loggedIn"))
    websocket = bool(dados.get("Connected") or dados.get("connected"))
    return normalizar_estado("open" if logado else ("connecting" if websocket else "close"))


def decidir_heartbeat(*, estado_atual: object, last_seen_at: object,
                      resposta_da_sonda: Optional[str] = None,
                      agora: Optional[datetime] = None,
                      limite_minutos: Optional[int] = None) -> dict:
    """O núcleo, puro: dado o que o banco diz e o que a sonda respondeu, o que
    passa a valer.

    Devolve ``{novo_estado, tocar_last_seen, alarmar, motivo}``. ``novo_estado``
    ``None`` significa *não mexa* — silêncio é uma decisão legítima e a mais
    comum das quatro.

    As três regras que este código existe para sustentar:

    1. **Resposta do provedor vence tudo.** Ela é a confirmação, e por isso
       renova `last_seen_at` mesmo quando o estado não muda — é essa renovação
       que faz a idade da coluna significar alguma coisa.
    2. **Sem resposta e ainda fresco: não invente.** Uma sonda que falhou não
       é um canal que caiu.
    3. **Sem resposta e obsoleto: pare de afirmar.** Vira `unknown`, não
       `disconnected` — não confirmamos queda nenhuma, só perdemos o direito de
       dizer "Conectado". Afirmar queda que não se mediu é o mesmo pecado do
       outro lado.
    """
    atual = normalizar_estado(estado_atual)

    if resposta_da_sonda is not None:
        novo = normalizar_estado(resposta_da_sonda)
        return {
            "novo_estado": novo,
            "tocar_last_seen": True,
            "alarmar": novo != CONECTADO and atual in ESTADOS_QUE_AFIRMAM,
            "motivo": "sonda_respondeu",
        }

    if not esta_obsoleto(last_seen_at, agora, limite_minutos):
        return {"novo_estado": None, "tocar_last_seen": False,
                "alarmar": False, "motivo": "ainda_fresco"}

    if atual not in ESTADOS_QUE_AFIRMAM:
        # Já está dizendo `disconnected`/`retired`/`unknown`. Não há mentira a
        # desfazer, e re-alarmar todo ciclo é como se aprende a ignorar alarme.
        return {"novo_estado": None, "tocar_last_seen": False,
                "alarmar": False, "motivo": "obsoleto_porem_honesto"}

    return {"novo_estado": DESCONHECIDO, "tocar_last_seen": False,
            "alarmar": True, "motivo": "obsoleto_sem_confirmacao"}


# ---------------------------------------------------------------------------
# O RECONECTOR — "conecta uma vez e fica conectado"
# ---------------------------------------------------------------------------
# 📊 Auditado em 04/08/2026: `CONNECT_ON_STARTUP=false` no Evolution Go, e
# NADA no sistema chama `/instance/connect` fora do pareamento.
#
#     grep "instance/connect" backend/app  ->  3 lugares, os TRÊS de pareamento
#
# Consequência medida: **todo restart do provedor derruba todos os canais, e
# nada os religa.** O botão "Gerar QR code" virou, sem ninguém decidir isso, o
# único reconector do produto — e é por isso que "clico em gerar QR e ele pareia
# sozinho": o whatsmeow reusa a sessão que já existe e conecta sem QR nenhum.
#
# 📊 E o preço foi medido: `observed_events` teve evento em **4 horas de 168**
# numa janela de 7 dias. Os canais passaram a semana desligados e ninguém soube.
#
# Reconectar NÃO é reparear. A sessão do WhatsApp continua registrada no
# provedor; o que caiu foi o socket. Por isso este caminho nunca gera QR: gerar
# QR quando a sessão existe é a única forma de PIORAR o problema.
TENTATIVA_INICIAL_S = 30
TETO_DE_ESPERA_S = 30 * 60
# Quando reconectamos cada instância pela última vez, e quantas vezes seguidas
# falhamos. Memória de processo, de propósito: o scheduler é um só, e um
# reconector que persistisse estado precisaria de outra tabela para fazer
# exatamente o que um dicionário faz.
_ULTIMA_RECONEXAO: Dict[str, tuple] = {}


def espera_do_backoff(tentativas: int) -> int:
    """PURO: quantos segundos esperar antes da próxima tentativa.

    Dobra a cada falha e para de dobrar no teto. Um canal que o provedor recusa
    não pode virar uma batida de porta a cada cinco minutos, para sempre.
    """
    if tentativas <= 0:
        return 0
    espera = TENTATIVA_INICIAL_S * (2 ** (tentativas - 1))
    return int(min(espera, TETO_DE_ESPERA_S))


def deve_reconectar(estado_sondado: Optional[str], estado_anterior: Optional[str]) -> bool:
    """PURO: este canal merece uma tentativa de reconexão agora?

    SIM quando a sonda diz que ele NÃO está de pé **e** ele já esteve — porque
    só então existe sessão registrada para reusar.

    NÃO quando a sonda não respondeu (`None`): não saber não é saber que caiu, e
    reconectar no escuro é o começo de um laço.

    NÃO quando nunca esteve conectado: ali não há sessão, e `/instance/connect`
    geraria um QR que ninguém vai ler.
    """
    if estado_sondado is None:
        return False
    if normalizar_estado(estado_sondado) in ESTADOS_QUE_AFIRMAM:
        return False
    return normalizar_estado(estado_anterior) in ESTADOS_QUE_AFIRMAM


# ---------------------------------------------------------------------------
# O ALARME DE ENTREGA — "conectado" não é o mesmo que "chegando"
# ---------------------------------------------------------------------------
# 📊 06/08/2026, e é a razão exata deste bloco existir:
#
#     AutoFleet  channel_status='connected'  ·  último observed_event 44 h atrás
#     Resulta    channel_status='connected'  ·  último observed_event 68 h atrás
#
# O painel dizia "Conectado" e estava certo sobre o cabo. O socket estava vivo —
# 📊 provado no mesmo dia com `GET /user/privacy` respondendo 200 em 0,3 s
# contra o WhatsApp da corretora. O que faltava era o webhook: o reconector
# religava o canal sem URL de entrega, e o provedor despachava para lugar nenhum.
#
# Ninguém descobriu por três dias. Não por descuido: **não havia o que olhar.**
# O heartbeat media o cabo, e o cabo estava bom.
#
# Este alarme mede a OUTRA ponta. Ele não pergunta "o canal está de pé?", e sim
# "a corretora que diz estar conectada gravou alguma conversa recentemente?".
# É a única pergunta cuja resposta negativa descreve o prejuízo real: o produto
# sem matéria-prima.
#
# Silencioso quando o canal já se declara caído: ali a queda JÁ está sendo dita
# por outro alarme, e repetir a mesma notícia com outro nome é como se ensina
# alguém a ignorar as duas.
LIMITE_SEM_ENTREGA_HORAS = 6


def decidir_alarme_de_entrega(
    *, estado_do_canal: object, ultima_entrega: object,
    agora: Optional[datetime] = None, limite_horas: Optional[float] = None,
) -> dict:
    """PURO: esta corretora está conectada e muda? Devolve ``{alarmar, motivo, horas}``.

    Três regras, e cada uma existe por um jeito diferente de errar:

    1. **Só alarma quem AFIRMA estar de pé.** Canal `disconnected` já tem o seu
       alarme; dois cartões para a mesma notícia treinam a pessoa a fechar os
       dois sem ler.
    2. **Nunca ter entregue conta como silêncio.** `None` não é "acabou de
       parear" — é uma corretora que se diz conectada e nunca gravou nada, que é
       o pior caso, não um caso a ignorar. Quem acabou de parear ainda não
       aparece aqui porque a linha nasce `connecting`, e `connecting` não afirma.
    3. **A conta é em horas, não em ciclos.** O heartbeat roda de 5 em 5 minutos;
       alarmar por ciclo daria 12 avisos por hora do mesmo problema.
    """
    momento = agora or _agora()
    limite = float(limite_horas if limite_horas is not None else LIMITE_SEM_ENTREGA_HORAS)

    if normalizar_estado(estado_do_canal) != CONECTADO:
        return {"alarmar": False, "motivo": "canal_nao_afirma_conexao", "horas": None}

    idade = idade_em_minutos(ultima_entrega, momento)
    if idade is None:
        # Conectado e sem uma linha sequer no acervo. Ver regra 2.
        return {"alarmar": True, "motivo": "conectado_e_nunca_entregou", "horas": None}

    horas = idade / 60.0
    if horas < limite:
        return {"alarmar": False, "motivo": "entregou_recentemente", "horas": horas}
    return {"alarmar": True, "motivo": "conectado_e_mudo", "horas": horas}


# O ACERVO SÃO DUAS TABELAS, E OLHAR SÓ UMA FAZ O ALARME MENTIR.
#
# 📊 06/08/2026 23:43 UTC, projeto de produção:
#
#     tabela                   AutoFleet          Amandus
#     observed_events          04/08 20:34        nunca
#     attendance_transcripts   06/08 22:08        06/08 21:31
#
# A borda separa por interlocutor: conversa com SEGURADORA vai para
# `observed_events`; conversa com SEGURADO vai para `attendance_transcripts`.
# Uma corretora pode passar dias sem falar com seguradora e atender segurado o
# dia inteiro — e nesse dia ela está capturando perfeitamente.
#
# Lendo só `observed_events`, este alarme dispararia AGORA nas duas corretoras
# conectadas: "conectado_e_mudo" na AutoFleet (51h) e "conectado_e_nunca_
# entregou" na Amandus. Ambos falsos.
#
# E o custo do falso positivo é maior do que parece: é a própria docstring de
# `decidir_alarme_de_entrega` que diz que dois cartões para a mesma notícia
# treinam a pessoa a fechar os dois sem ler. Um alarme que grita todo dia sem
# motivo ensina exatamente isso — e estará gritando no dia em que for verdade.
_ACERVOS_DE_CAPTURA = ("observed_events", "attendance_transcripts")


async def _ultima_entrega_por_corretora(
    db: Any = None, empresas: Optional[set] = None,
) -> Dict[str, Any]:
    """Quando cada corretora gravou a última conversa, em QUALQUER acervo.

    A leitura é do ACERVO, não de `integrations`: `last_seen_at` mede a sonda, e
    a sonda foi exatamente o que ficou verde enquanto nada chegava.

    Devolve a data MAIS RECENTE entre as duas tabelas: capturar de um lado só
    já é capturar, e o silêncio que interessa é o silêncio dos dois.

    🔴 UMA CONSULTA POR CORRETORA, e não uma varredura das N linhas mais novas.
    ==========================================================================
    A versão anterior lia `.limit(2000)` das duas tabelas e agrupava no Python.
    Parecia econômico e tinha um buraco: o PostgREST tem um teto de linhas por
    resposta que **vence o `.limit()` pedido** — 📊 06/08/2026, o backfill do
    espelho pediu 1.500 e recebeu 1.000, e ficou meses de conversa para trás.

    Aplicado aqui, o buraco é pior que perder linhas: uma corretora movimentada
    empurra as outras para fora das 1.000 mais recentes. A corretora que sumiu
    da leitura vira `ultima_entrega=None` — que este alarme lê como "conectado
    e NUNCA entregou". O alarme dispararia mais alto justamente onde há MAIS
    tráfego, que é o contrário do que ele existe para dizer.

    `limit(1)` por corretora e por tabela não tem teto que morda: são 2 idas ao
    banco por corretora a cada cinco minutos, e a resposta é sempre exata.
    """
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    alvos = {str(e) for e in (empresas or set()) if str(e or "").strip()}
    if not alvos:
        # Sem corretoras não há o que perguntar. Devolver {} aqui é seguro: o
        # chamador só consulta este mapa por company_id que ele mesmo trouxe.
        return {}

    def _ler(tabela: str, empresa: str) -> list:
        return (cliente.table(tabela)
                .select("company_id, created_at")
                .eq("company_id", empresa)
                .order("created_at", desc=True)
                .limit(1).execute().data or [])

    ultima: Dict[str, Any] = {}
    for empresa in alvos:
        for tabela in _ACERVOS_DE_CAPTURA:
            try:
                linhas = await asyncio.to_thread(_ler, tabela, empresa)
            except Exception as erro:  # noqa: BLE001
                # Um acervo ilegível não pode fazer o outro sumir: se
                # `observed_events` cair, a captura de segurados continua
                # contando como entrega.
                logger.warning("[ENTREGA] não consegui ler %s (%s)",
                               tabela, type(erro).__name__)
                continue
            if not linhas:
                continue
            quando = linhas[0].get("created_at")
            anterior = ultima.get(empresa)
            if anterior is None or _mais_recente(quando, anterior):
                ultima[empresa] = quando
    return ultima


def _mais_recente(candidato: object, atual: object) -> bool:
    """`candidato` é mais novo que `atual`? Compara datas, não texto.

    Comparar ISO como string funciona por acidente enquanto as duas tiverem o
    mesmo fuso e a mesma quantidade de casas decimais. `+00:00` e `Z` são o
    mesmo instante e ordenam diferente como texto — e as duas formas aparecem
    no banco. Comparar como data é o que não depende de sorte.
    """
    novo, velho = _quando(candidato), _quando(atual)
    if novo is None:
        return False
    if velho is None:
        return True
    return novo > velho


def _quando(valor: object) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    if not valor:
        return None
    try:
        lido = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return lido if lido.tzinfo else lido.replace(tzinfo=timezone.utc)


async def _alarme_de_entrega_padrao(integracao: dict, decisao: dict) -> None:
    from app.services.whatsapp.alerts import alerta_de_plataforma

    if decisao["horas"] is None:
        quanto = "e nunca gravou uma conversa"
    else:
        quanto = f"e não grava uma conversa há {decisao['horas']:.0f} horas"
    await alerta_de_plataforma(
        "WhatsApp conectado, mas nada está sendo capturado",
        (f"O canal desta corretora aparece como Conectado {quanto}. "
         "O socket pode estar de pé e a ENTREGA desligada — foi o que aconteceu "
         "em 06/08/2026, quando o canal religou sem endereço de webhook e duas "
         "corretoras passaram dias sem capturar com o painel verde. "
         "Confira o campo `webhook` da instância no provedor: vazio significa "
         "que as mensagens estão sendo despachadas para lugar nenhum."),
        # Chave estável por canal: um cartão que continua aberto, não 288 por dia.
        chave=f"canal:sem_entrega:{integracao.get('id')}",
        severidade="sev2",
        company_id=str(integracao.get("company_id") or "") or None,
    )


async def _gravar_credencial_de_webhook(
    integracao: dict, hash_novo: str, prefixo_novo: str, *, db: Any = None
) -> bool:
    """Grava o hash do webhook rotacionado. ``False`` = não grave, não religue.

    Devolve booleano porque o chamador tem de PARAR quando isto falha: mandar ao
    provedor uma URL cujo hash não está no banco troca um canal mudo por um canal
    que entrega para uma porta que recusa. Falhar em silêncio aqui seria repetir,
    de outra forma, o defeito que esta função existe para consertar.

    O filtro carrega `company_id` junto do `id` por obrigação da CLAUDE.md §7: o
    backend usa service role, então RLS não protege contra um filtro torto no
    código — o filtro certo é o único guarda que existe.
    """
    linha_id = integracao.get("id")
    if not linha_id:
        logger.error("[RECONECTOR] integração sem id — credencial de webhook não gravada")
        return False
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _gravar() -> None:
        consulta = (cliente.table("integrations")
                    .update({"webhook_token_hash": hash_novo,
                             "webhook_token_prefix": prefixo_novo})
                    .eq("id", linha_id))
        if integracao.get("company_id"):
            consulta = consulta.eq("company_id", integracao["company_id"])
        consulta.execute()

    try:
        await asyncio.to_thread(_gravar)
        return True
    except Exception as erro:  # noqa: BLE001
        logger.error("[RECONECTOR] não gravei a credencial de webhook de %s (%s) — não vou religar",
                     integracao.get("instance_id"), type(erro).__name__)
        return False


async def _reconectar_evolution_go(integracao: dict, agora: datetime) -> Optional[str]:
    """Pede ao provedor que religue o socket. Nunca gera QR. Nunca levanta.

    ⚠️ RELIGAR INCLUI DIZER PARA ONDE ENTREGAR — ver `corpo_do_connect`.

    Até 06/08/2026 esta função mandava só ``{"immediate": True}``, e o `Connect`
    do Evolution Go gravava `Webhook = ""` por cima. O canal voltava mudo: 📊 três
    das quatro instâncias com ``webhook=''``, e a captura das duas corretoras
    parada há 42 h e 67 h com o painel dizendo "Conectado".

    O token de webhook **não é recuperável**: o banco guarda só o `sha256`
    (`new_webhook_credentials` — o plaintext nunca é gravado). Então religar é
    necessariamente **rotacionar**: token novo, hash novo gravado, URL nova
    entregue ao provedor, tudo na mesma tentativa. A ordem importa e está
    invertida de propósito — grava-se o hash ANTES de mandar a URL, porque um
    webhook que chega antes do hash é um evento que a borda recusa; o contrário
    é uma janela de milissegundos em que o provedor ainda usa a URL velha, que
    ainda funciona.
    """
    # A escada de espera é conferida ANTES de qualquer import: a chamada que só
    # vai devolver "espere" não deve pagar por carregar o módulo de segredos.
    chave = str(integracao.get("instance_id") or integracao.get("id") or "")
    tentativas, ultima = _ULTIMA_RECONEXAO.get(chave, (0, None))
    if ultima is not None and (agora - ultima).total_seconds() < espera_do_backoff(tentativas):
        return "aguardando_backoff"

    import httpx

    from app.services.whatsapp.integration_secrets import decrypt_integration_secret

    base = str(integracao.get("base_url") or os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    token = decrypt_integration_secret(integracao.get("token")) or ""
    if not (base and token):
        _ULTIMA_RECONEXAO[chave] = (tentativas + 1, agora)
        return None

    # Sem endereço público não há URL de entrega, e um connect sem URL APAGA a
    # que está lá. Aqui, não fazer nada é estritamente melhor que religar.
    publico = str(os.getenv("PUBLIC_BACKEND_URL") or "").strip().rstrip("/")
    if not publico:
        logger.error(
            "[RECONECTOR] PUBLIC_BACKEND_URL ausente — canal %s NÃO religado de propósito: "
            "um connect sem webhookUrl apagaria a entrega do canal",
            integracao.get("instance_id"))
        _ULTIMA_RECONEXAO[chave] = (tentativas + 1, agora)
        return None

    # Importado só AQUI, depois de todas as recusas: quem já decidiu que não vai
    # religar não deve pagar por carregar módulo — a mesma razão que mantém o
    # backoff acima de qualquer import.
    from app.services.whatsapp.channel_security import (
        build_webhook_url,
        corpo_do_connect,
        new_webhook_credentials,
    )

    webhook_token, webhook_hash, webhook_prefix = new_webhook_credentials()
    if not await _gravar_credencial_de_webhook(integracao, webhook_hash, webhook_prefix):
        _ULTIMA_RECONEXAO[chave] = (tentativas + 1, agora)
        return None

    _ULTIMA_RECONEXAO[chave] = (tentativas + 1, agora)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SONDA_SEGUNDOS) as cliente:
            resposta = await cliente.post(
                f"{base}/instance/connect",
                headers={"apikey": token},
                json=corpo_do_connect(
                    build_webhook_url(publico, "evolution-go", webhook_token)),
            )
        if resposta.status_code < 400:
            _ULTIMA_RECONEXAO[chave] = (0, agora)   # deu certo: zera a escada
            # O prefixo, nunca o token (CLAUDE.md §13.3).
            logger.info("[RECONECTOR] canal %s religado sem QR · webhook %s…",
                        integracao.get("instance_id"), webhook_prefix)
            return "reconectado"
        logger.warning("[RECONECTOR] %s recusou religar (HTTP %s) — próxima em %ss",
                       integracao.get("instance_id"), resposta.status_code,
                       espera_do_backoff(tentativas + 1))
        return "recusado"
    except Exception as erro:  # noqa: BLE001
        logger.warning("[RECONECTOR] %s falhou (%s)", integracao.get("instance_id"),
                       type(erro).__name__)
        return "erro"


async def _gravar_telefone_pareado(integracao: dict, corpo: object, db: Any = None) -> bool:
    """Grava QUAL telefone está pareado, quando a sonda o revela.

    Só grava quando o provedor DIZ o número. Silêncio da sonda nunca apaga o
    que já está lá — a mesma regra de `numero_pareado.dados_de_pareamento`:
    um refresh mudo não pode desfazer o que o pareamento provou.

    Idempotente: se o telefone gravado já é este, não escreve. Um `UPDATE` a
    cada cinco minutos por corretora seria escrita à toa num caminho quente.
    """
    from app.services.whatsapp.numero_pareado import identidade_pareada, mascarar

    linha_id = integracao.get("id")
    if not linha_id:
        return False
    jid, telefone = identidade_pareada(corpo if isinstance(corpo, dict) else {})
    if not jid or not telefone:
        return False
    if str(integracao.get("paired_phone_e164") or "") == telefone:
        return False

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _gravar() -> None:
        consulta = (cliente.table("integrations").update({
            "paired_jid": jid, "paired_phone_e164": telefone,
            "paired_at": _agora().isoformat(),
        }).eq("id", linha_id))
        # Filtro por corretora junto do id: service role ignora RLS (§7).
        if integracao.get("company_id"):
            consulta = consulta.eq("company_id", integracao["company_id"])
        consulta.execute()

    try:
        await asyncio.to_thread(_gravar)
        # Mascarado sempre — é a linha de trabalho de uma pessoa real (§13.3).
        logger.info("[HEARTBEAT] telefone pareado gravado: %s", mascarar(telefone))
        return True
    except Exception as erro:  # noqa: BLE001 — nunca derruba a sonda
        logger.warning("[HEARTBEAT] não gravei o telefone pareado (%s)", type(erro).__name__)
        return False


async def _sondar_evolution_go(integracao: dict) -> Optional[str]:
    """Pergunta ao provedor. ``None`` = não consegui saber (não é veredito).

    HTTP 401/404 (instância fantasma no provedor) também devolve ``None`` de
    propósito: diz que a NOSSA configuração está torta, não que o WhatsApp do
    corretor caiu. O código volta no motivo, para o incidente contar a história
    certa. O token nunca aparece em log — só a sua ausência.
    """
    import httpx

    from app.services.whatsapp.integration_secrets import decrypt_integration_secret

    base = str(integracao.get("base_url") or os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    if not base:
        logger.warning("[HEARTBEAT] integração %s sem base_url e sem EVOLUTION_GO_BASE_URL",
                       integracao.get("id"))
        return None
    token = decrypt_integration_secret(integracao.get("token")) or ""
    if not token:
        logger.warning("[HEARTBEAT] integração %s sem token utilizável", integracao.get("id"))
        return None

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SONDA_SEGUNDOS) as cliente:
            resposta = await cliente.get(f"{base}/instance/status",
                                         headers={"apikey": token})
        if resposta.status_code >= 400:
            logger.warning("[HEARTBEAT] %s respondeu HTTP %s — não é veredito sobre o canal",
                           integracao.get("id"), resposta.status_code)
            return None
        corpo = resposta.json() if resposta.content else {}
        # QUEM está pareado — gravado aqui porque aqui é o único caminho que
        # passa por TODAS as corretoras, a cada cinco minutos.
        #
        # 📊 06/08/2026: a Amandus pareou pelo QR e ficou `connected` com
        # `paired_phone_e164 = null`. O telefone só era gravado no fluxo do
        # orquestrador (`_mark_connected`), e um QR escaneado conclui pelo
        # WEBHOOK — que grava o estado e não o telefone. Resultado: o número
        # aparecia na AutoFleet (onde o orquestrador rodou) e não na Amandus.
        #
        # A pergunta do Founder foi exatamente essa: *"fez tudo global ou só
        # para uma corretora?"*. Estava global no código e furado no caminho.
        await _gravar_telefone_pareado(integracao, corpo)
        return estado_da_sonda(corpo)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[HEARTBEAT] sonda de %s falhou (%s)",
                       integracao.get("id"), type(erro).__name__)
        return None


async def _alarme_padrao(integracao: dict, decisao: dict, idade: Optional[float]) -> None:
    """Incidente na Caixa do Admin, com chave estável por canal.

    Chave estável = um cartão que continua aberto, não 288 cartões por dia.
    """
    from app.services.whatsapp.alerts import alerta_de_plataforma

    identificacao = f"{integracao.get('provider') or 'canal'} · {integracao.get('purpose') or 'geral'}"
    quanto = f"{idade / 60.0:.1f}h" if idade else "tempo desconhecido"
    await alerta_de_plataforma(
        f"Canal de WhatsApp sem confirmação ({identificacao})",
        (f"O canal {identificacao} da corretora afirmava "
         f"'{rotulo_humano(integracao.get('channel_status'))}' e ninguém confirmou esse "
         f"estado há {quanto}. O estado gravado passou a '{decisao['novo_estado']}' — "
         "a tela deixa de prometer atendimento que pode não estar acontecendo. "
         "Verifique o pareamento em Personalização → Corretora → WhatsApp."),
        chave=f"canal:sem_confirmacao:{integracao.get('id')}",
        severidade="sev2",
        company_id=str(integracao.get("company_id") or "") or None,
    )


async def verificar_canais(
    *,
    db: Any = None,
    sonda: Optional[Callable[[dict], Awaitable[Optional[str]]]] = None,
    alarme: Optional[Callable[..., Awaitable[None]]] = None,
    reconector: Optional[Callable[..., Awaitable[Optional[str]]]] = None,
    alarme_de_entrega: Optional[Callable[..., Awaitable[None]]] = None,
    agora: Optional[datetime] = None,
) -> dict:
    """A varredura. Roda no APScheduler existente; nunca levanta exceção.

    As QUATRO costuras (`db`, `sonda`, `alarme`, `reconector`) são injetáveis
    pelo mesmo motivo que o motor de acionamento injeta o `sender`: dá para
    provar a decisão inteira sem rede e sem banco — e teste que não roda não
    protege ninguém.

    O `reconector` nasceu costurado em 04/08/2026, e a razão é um erro meu: eu o
    tinha chamado direto, sem costura, e os testes do heartbeat — que rodam com
    sonda de mentira — passaram a bater num import de runtime. Uma peça nova que
    quebra o jeito de testar as antigas está errada mesmo que funcione.
    """
    if not heartbeat_ligado():
        return {"ok": False, "motivo": "desligado", "verificados": 0}

    momento = agora or _agora()
    limite = limite_obsoleto_minutos()
    sondar = sonda or _sondar_evolution_go
    alarmar_com = alarme or _alarme_padrao
    religar = reconector or _reconectar_evolution_go

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    resumo = {"ok": True, "verificados": 0, "confirmados": 0, "contestados": 0,
              "inalterados": 0, "alarmes": 0, "erros": 0, "limite_minutos": limite,
              "mudos": 0}

    alarmar_entrega = alarme_de_entrega or _alarme_de_entrega_padrao

    try:
        def _ler() -> list:
            return (cliente.table("integrations")
                    # `paired_phone_e164` entra para o gravador do telefone
                    # poder comparar antes de escrever. Sem ele, seria um
                    # UPDATE por corretora a cada cinco minutos, para sempre.
                    .select("id, company_id, provider, purpose, instance_id, token, "
                            "base_url, channel_status, last_seen_at, paired_phone_e164")
                    .eq("is_active", True)
                    .in_("provider", list(PROVEDORES_SONDAVEIS))
                    .limit(500).execute().data or [])

        linhas = await asyncio.to_thread(_ler)
    except Exception as erro:  # noqa: BLE001
        logger.error("[HEARTBEAT] não consegui ler integrations (%s)", type(erro).__name__)
        return {"ok": False, "motivo": type(erro).__name__, "verificados": 0}

    # Quando cada corretora gravou a última conversa. Lido UMA vez, depois de
    # saber QUAIS corretoras entram no ciclo — ver a nota em
    # `_ultima_entrega_por_corretora` sobre por que a lista é obrigatória.
    ultima_entrega = await _ultima_entrega_por_corretora(
        db, empresas={str(l.get("company_id") or "") for l in linhas})

    for linha in linhas:
        resumo["verificados"] += 1
        try:
            resposta = await sondar(linha)
            idade = idade_em_minutos(linha.get("last_seen_at"), momento)
            decisao = decidir_heartbeat(
                estado_atual=linha.get("channel_status"),
                last_seen_at=linha.get("last_seen_at"),
                resposta_da_sonda=resposta,
                agora=momento,
                limite_minutos=limite,
            )

            # O canal caiu e já esteve de pé: religa o socket antes de gravar o
            # estado. Não é reparear — a sessão continua registrada no provedor,
            # e por isso nenhum QR é gerado. Sem isto, o único reconector do
            # produto é um humano clicando em "Gerar QR code".
            if deve_reconectar(resposta, linha.get("channel_status")):
                # Try próprio, e ele importa: **religar é um bônus; gravar a
                # verdade é a obrigação.** Se a reconexão falhar, o heartbeat
                # segue e registra que o canal caiu — que é o serviço que ele
                # prestava antes de existir reconector nenhum. Uma peça nova não
                # pode sequestrar a função da peça antiga quando dá errado.
                try:
                    efeito = await religar(linha, momento)
                except Exception as erro:  # noqa: BLE001
                    logger.warning("[RECONECTOR] tentativa falhou (%s) — o heartbeat segue",
                                   type(erro).__name__)
                    efeito = None
                if efeito == "reconectado":
                    resumo["reconectados"] = resumo.get("reconectados", 0) + 1
                    # Reconsulta: se voltou, não faz sentido gravar "caiu".
                    try:
                        resposta = await sondar(linha) or resposta
                    except Exception:  # noqa: BLE001
                        pass
                    decisao = decidir_heartbeat(
                        estado_atual=linha.get("channel_status"),
                        last_seen_at=linha.get("last_seen_at"),
                        resposta_da_sonda=resposta,
                        agora=momento,
                        limite_minutos=limite,
                    )

            # A OUTRA PONTA: o canal está de pé, mas está CHEGANDO alguma coisa?
            #
            # Roda antes do `continue` de propósito. O caso que este alarme
            # existe para pegar é justamente o canal que não muda de estado —
            # verde, confirmado, inalterado, ciclo após ciclo, e mudo. Se a
            # checagem viesse depois, ela nunca rodaria para quem mais precisa.
            estado_final = decisao["novo_estado"] or linha.get("channel_status")
            entrega = decidir_alarme_de_entrega(
                estado_do_canal=estado_final,
                ultima_entrega=ultima_entrega.get(str(linha.get("company_id") or "")),
                agora=momento,
            )
            if entrega["alarmar"]:
                resumo["mudos"] += 1
                logger.error(
                    "[ENTREGA] canal %s (%s) diz CONECTADO e não grava conversa — motivo=%s horas=%s",
                    linha.get("id"), linha.get("purpose"), entrega["motivo"],
                    f"{entrega['horas']:.0f}" if entrega["horas"] is not None else "nunca")
                try:
                    await alarmar_entrega(linha, entrega)
                except Exception as erro:  # noqa: BLE001
                    # Um alarme que falha não pode derrubar o heartbeat: a
                    # obrigação dele continua sendo gravar a verdade do canal.
                    logger.error("[ENTREGA] alarme não registrado (%s)", type(erro).__name__)

            if decisao["novo_estado"] is None:
                resumo["inalterados"] += 1
                continue

            campos: dict = {"channel_status": decisao["novo_estado"]}
            if decisao["tocar_last_seen"]:
                campos["last_seen_at"] = momento.isoformat()

            def _gravar(campos=campos, linha=linha) -> None:
                consulta = cliente.table("integrations").update(campos).eq("id", linha["id"])
                if linha.get("company_id"):
                    consulta = consulta.eq("company_id", linha["company_id"])
                consulta.execute()

            await asyncio.to_thread(_gravar)

            if decisao["motivo"] == "sonda_respondeu":
                resumo["confirmados"] += 1
            else:
                resumo["contestados"] += 1

            if decisao["alarmar"]:
                resumo["alarmes"] += 1
                logger.error(
                    "[HEARTBEAT] canal %s (%s) afirmava '%s' e virou '%s' — motivo=%s idade=%s min",
                    linha.get("id"), linha.get("purpose"), linha.get("channel_status"),
                    decisao["novo_estado"], decisao["motivo"],
                    f"{idade:.0f}" if idade is not None else "nunca visto",
                )
                try:
                    await alarmar_com(linha, decisao, idade)
                except Exception as erro:  # noqa: BLE001
                    logger.error("[HEARTBEAT] alarme não registrado (%s)", type(erro).__name__)
        except Exception as erro:  # noqa: BLE001
            resumo["erros"] += 1
            logger.error("[HEARTBEAT] falha ao verificar %s (%s)",
                         linha.get("id"), type(erro).__name__)

    nivel = logger.error if (resumo["alarmes"] or resumo["erros"] or resumo["mudos"]) else logger.info
    nivel("[HEARTBEAT] %s canais · %s confirmados · %s contestados · %s alarmes · %s mudos · %s erros",
          resumo["verificados"], resumo["confirmados"], resumo["contestados"],
          resumo["alarmes"], resumo["mudos"], resumo["erros"])
    return resumo
