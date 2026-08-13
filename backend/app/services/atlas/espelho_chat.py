"""A ponte entre o que o Observador captura e o chat da corretora.

POR QUE ESTE MÓDULO EXISTE
==========================
📊 06/08/2026: a captura da AutoFleet gravava **124 mensagens por hora** em
`attendance_transcripts` — conversas reais de sinistro, em tempo real — e a tela
`Atendimentos → Conversas` da corretora dizia *"Nenhuma conversa ainda"*.

As duas coisas eram verdade. O acervo enchia; a mesa de trabalho ficava vazia.
Faltava a ponte: `observer_tap` consome o evento enquanto o agente de atendimento
está desligado, e era o pipeline consumido que criaria a conversa.

Este módulo é essa ponte, e nada além dela.

O QUE ELA NÃO FAZ — e cada linha disso é uma decisão do Founder
===============================================================
**Não dá voz ao Observador.** Não há caminho de envio aqui. O Observador observa
em silêncio, ligado a hora toda, e isso não muda.

**Não liga agente nenhum.** A conversa nasce e o agente continua desligado até
alguém clicar no botão. Quem decide se o agente fala é
`attendance_capture.attendance_agent_active`, lá no `observer_tap`, e esta ponte
não tem opinião sobre isso — ela grava e devolve.

**Não esconde histórico.** A janela desta ponte é larga (30 dias) e existe para
um caso só: o HISTORY_SYNC de um pareamento novo, que chega com meses de conversa
de uma vez. Quem enxuga a mesa de trabalho é a LISTA, com `JANELA_DA_LISTA_DIAS`.
Abrir uma conversa mostra o histórico inteiro — um sinistro que arrasta 45 dias
continua legível do começo.

A CHAVE — o ponto mais fácil de errar deste arquivo
====================================================
🔴 A conversa criada aqui tem de ser a **mesma** que o pipeline do agente
encontra no dia em que ele for ligado.

📊 `webhook.get_or_create_conversation` procura por
`company_id` + `user_id` + `channel` + `agent_id IS NULL`. Procurar por
`user_phone` — o caminho óbvio — criaria uma conversa que o pipeline não acharia,
e o mesmo cliente apareceria em duas: uma com o histórico do espelho, outra com o
do agente. O defeito só apareceria no dia do go-live, que é o dia mais caro
possível para descobrir qualquer coisa.

Por isso o usuário é resolvido pela **mesma** `integration_service.get_or_create_user`
e a busca usa os **mesmos** filtros. Há teste de convergência, e ele lê a linha
do `webhook.py` para avisar se ela mudar.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Quantos dias de conversa aparecem NA LISTA do chat. Decisão do Founder,
# 06/08/2026. É o que a atendente vê ao abrir a tela.
JANELA_DA_LISTA_DIAS = 7

# Até onde uma mensagem ainda merece entrar no chat. Larga de propósito: não é
# para esconder conversa (disso cuida a lista), é para o HISTORY_SYNC de um
# pareamento novo não despejar meses de histórico de uma vez só.
LIMITE_DE_RECENCIA_HORAS = 720.0  # 30 dias

# Quanto tempo uma resposta enviada pelo dashboard ainda pode "voltar" pelo
# webhook como `fromMe`. Curto: é o tempo de ida ao WhatsApp e volta, não uma
# janela de conveniência. Longo demais engoliria a atendente repetindo a mesma
# frase de propósito.
_JANELA_DE_ECO_SEGUNDOS = 120.0

# 🔴 O PORTÃO que decide se vale a pena PERGUNTAR pelo eco. Mais largo que a
# janela de comparação, de propósito.
#
# 📊 13/08/2026: a leitura das 40 últimas mensagens era feita para TODA mensagem
# — inclusive as 4.008 linhas antigas que o sync reprocessava a cada ciclo. Ela
# custou 771.313 chamadas devolvendo ~33 linhas de 290 B cada: a maior fatia
# isolada do Egress que restringiu a organização no Supabase.
#
# Mas eco só EXISTE por `_JANELA_DE_ECO_SEGUNDOS`. Uma mensagem de ontem não
# pode ser o eco de uma resposta enviada há dois minutos — logo a leitura nunca
# deveria ter acontecido para ela.
#
# 300s e não 120s: o `quando_iso` vem do relógio do WhatsApp, não do nosso. Um
# desvio de relógio de dois minutos faria o portão fechar na cara de um eco
# legítimo, e a atendente veria a própria frase duas vezes. A margem é grátis
# (mensagem ao vivo é caso raro) e a REGRA DE NEGÓCIO continua sendo 120s: o
# portão decide se pergunta, `_JANELA_DE_ECO_SEGUNDOS` decide a resposta.
_PORTAO_DE_ECO_SEGUNDOS = 300.0

# Quantas mensagens recentes bastam para reconhecer um eco. O eco é a resposta
# que a atendente acabou de enviar; se ela escreveu mais de 20 mensagens nos
# últimos 300 segundos, a 21ª não é eco de nada — é uma pessoa digitando.
_MENSAGENS_PARA_ECO = 20

# Tipos que valem uma conversa mesmo sem uma palavra escrita.
_TIPOS_SEM_TEXTO = ("audio", "image", "document", "video", "sticker")

# 🔴 O BANCO SÓ ACEITA DOIS TIPOS, e foi isso que deixou o chat em branco.
#
# 📊 06/08/2026: `messages_type_check` é
# `CHECK (type = ANY (ARRAY['text','voice']))`. A ponte gravava o tipo cru do
# WhatsApp — `audio`, `image`, `document` — e o banco recusava a linha inteira.
# Resultado medido: **51 conversas da AutoFleet com ZERO mensagens** e
# `{"erro:APIError": 2216}` no contador. A conversa nascia e a mensagem morria.
#
# O `msg_type` de verdade continua no `payload`, para o dia em que a mídia for
# tocável (P-119). O que muda aqui é só o que o CHECK aceita.
_TIPO_NO_BANCO = {"audio": "voice", "voice": "voice", "ptt": "voice"}


_ROTULO_DE_MIDIA = {
    "audio": "🎤 Áudio", "voice": "🎤 Áudio", "ptt": "🎤 Áudio",
    "image": "📷 Imagem", "video": "🎬 Vídeo",
    "document": "📄 Documento", "sticker": "😀 Figurinha",
}


def _rotulo_de_midia(msg_type: str) -> str:
    """O que a atendente lê quando a mensagem não tem texto.

    `[audio]` não é uma frase — é um resto de código vazando para a tela de
    quem trabalha. Ainda não dá para TOCAR a mídia (P-119), mas dá para dizer
    em português o que chegou.
    """
    return _ROTULO_DE_MIDIA.get(str(msg_type or "").strip().lower(), "📎 Anexo")


def _tipo_aceito(msg_type: str) -> str:
    """Traduz o tipo do WhatsApp para o que `messages.type` aceita.

    Áudio vira `voice`; todo o resto vira `text`. Não é perda de informação: o
    tipo original vai no `payload`, e o texto da mensagem já diz `[imagem]` ou
    `[documento]` para a atendente.
    """
    return _TIPO_NO_BANCO.get(str(msg_type or "").strip().lower(), "text")


def _digitos(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


_CHAVE_TOTAL = "espelho:chat"
_CHAVE_JANELA = "espelho:chat:{quando}"


def _janela_atual() -> str:
    """A janela de 10 minutos em que estamos. Alinhada ao relógio, de propósito:
    duas leituras seguidas caem na mesma janela e são comparáveis."""
    agora = datetime.now(timezone.utc)
    return f"{agora:%Y%m%d%H}{agora.minute // 10}"


async def contar(motivo: str, quantos: int = 1) -> None:
    """Conta o que aconteceu com o espelho. Agregado, nunca conteúdo.

    🔴 EXISTE PORQUE EU FIQUEI CEGO, e o preço foi alto.

    📊 06/08/2026: a ponte estava no ar (`espelho_no_chat=True` no /health),
    13.200 mensagens entraram no acervo em três horas, e **zero** conversas
    apareceram no chat. O `try/except` que protege a captura engolia o motivo,
    e a única forma de saber o que falhou seria ler o log do contêiner — que o
    Founder não tem por que abrir.

    Sem contador, "não apareceu" tem cinco explicações e nenhuma forma de
    escolher entre elas. Com contador, a resposta cabe numa linha do /health.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        # DUAS contagens, e a segunda é a que responde "parou?".
        #
        # 🔴 A primeira versão só tinha o acumulado. Uma auditoria independente
        # apontou o defeito: **um contador cumulativo sempre sobe**. Ao ver
        # `erro:APIError` subir de 2.216 para 4.059 eu li "o conserto falhou" —
        # quando podia ser erro de duas horas antes somado ao de agora. Sem
        # separar as duas coisas, eu não sabia em qual conserto duvidar, e isso
        # sozinho custou uma rodada.
        #
        # A janela de 10 minutos expira em 1 hora: ela responde "está errando
        # AGORA?", que é a única pergunta útil depois de um deploy.
        await r.hincrby(_CHAVE_TOTAL, motivo, int(quantos))
        janela = _CHAVE_JANELA.format(quando=_janela_atual())
        await r.hincrby(janela, motivo, int(quantos))
        await r.expire(janela, 3600)
    except Exception:  # noqa: BLE001 — contador nunca derruba o que ele mede
        pass


async def diagnostico() -> dict:
    """O que o espelho fez — sempre e AGORA.

    `agora` é a resposta para "o conserto pegou?". `total` é o histórico desde o
    primeiro boot, e ele **sempre sobe** — foi lê-lo como se fosse o presente
    que me fez concluir errado depois de um deploy.
    """
    def _ler(bruto) -> dict:
        return {(k.decode() if isinstance(k, bytes) else str(k)):
                int(v.decode() if isinstance(v, bytes) else v)
                for k, v in (bruto or {}).items()}

    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        agora = _ler(await r.hgetall(_CHAVE_JANELA.format(quando=_janela_atual())))
        return {
            "agora": agora or {"sem_atividade_nesta_janela": 0},
            "total_desde_o_boot": _ler(await r.hgetall(_CHAVE_TOTAL)),
        }
    except Exception:  # noqa: BLE001
        return {}


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_id_do_chat(company_id: str, telefone: str) -> str:
    """A MESMA sessão que o pipeline do agente monta (`webhook.py:491`).

    📊 Lá: ``f"whatsapp:{payload.phone}:{company_id}:{agent_suffix}"``, com
    ``agent_suffix = "default"`` quando a integração não tem agente vinculado —
    que é o caso das três linhas de observer em produção (`agent_id = null`).

    Só dígitos, porque o mesmo número chega ora ``+55 (47) 9995-6540``, ora
    ``554799956540``. Um hífen de diferença criaria uma segunda conversa para o
    mesmo cliente, e ninguém desconfiaria de um hífen.
    """
    return f"whatsapp:{_digitos(telefone)}:{company_id}:default"


def deve_espelhar(*, counterparty: str, texto: str, msg_type: str,
                  e_grupo: bool, e_seguradora: bool, idade_horas: float,
                  limite_horas: float = LIMITE_DE_RECENCIA_HORAS) -> bool:
    """Esta mensagem capturada merece uma conversa no chat da corretora? PURO.

    O chat é a mesa de trabalho da corretora; o acervo
    (`attendance_transcripts`) é outra coisa e guarda tudo — inclusive
    seguradora, grupo e conversa de meses atrás.

    ⚠️ A janela daqui NÃO é a que a atendente vê. Mensagem ao vivo tem idade ~0
    e passa sempre. Quem esconde conversa velha da mesa é a LISTA, com
    `JANELA_DA_LISTA_DIAS`. Esta existe para o HISTORY_SYNC de um pareamento
    novo, que chegaria com meses de história de uma vez.

    Áudio sem texto passa de propósito: a atendente precisa VER que chegou algo.
    Uma conversa que aparece vazia é melhor que uma que não aparece.
    """
    if not str(counterparty or "").strip():
        return False
    if e_grupo or e_seguradora:
        return False
    if float(idade_horas) > float(limite_horas):
        return False
    return bool(str(texto or "").strip()) or str(msg_type or "") in _TIPOS_SEM_TEXTO


async def espelhar_no_chat(*, company_id: str, counterparty: str, texto: str,
                           msg_type: str, direcao: str, message_id: str,
                           quando_iso: str, nome: Optional[str] = None,
                           db: Any = None) -> Optional[str]:
    """Põe a mensagem capturada no chat da corretora. Devolve o id da conversa.

    ⚠️ Esta função NÃO faz o agente falar. Quem faz o agente responder é o
    pipeline do webhook, e o `observer_tap` continua consumindo o evento
    enquanto o agente está desligado. Aqui só se grava o que aconteceu.

    Idempotente por `message_id`: a resposta enviada pelo dashboard vai ao
    WhatsApp e **volta** como `fromMe`. Sem esta guarda, cada resposta apareceria
    duas vezes no chat de quem acabou de escrevê-la.

    🔴 O CONTRATO DESTA FUNÇÃO NÃO MUDA — ela devolve ``Optional[str]``, como
    sempre devolveu. Quem precisa saber POR QUE (o cursor incremental do
    `sincronizar_chats`, que não pode avançar sobre erro) chama
    `_espelhar_com_desfecho`. São dois chamadores com necessidades diferentes,
    e trocar o tipo de retorno desta aqui quebraria `observer_intake` e
    `webhook.py` em silêncio.
    """
    conversa, _motivo = await _espelhar_com_desfecho(
        company_id=company_id, counterparty=counterparty, texto=texto,
        msg_type=msg_type, direcao=direcao, message_id=message_id,
        quando_iso=quando_iso, nome=nome, db=db)
    return conversa


# Os desfechos que o cursor pode ultrapassar com segurança: todos significam
# "esta linha foi resolvida e não há mais nada a fazer com ela". Qualquer
# outro — inclusive `erro:*` — trava o avanço do cursor antes dela.
DESFECHOS_DETERMINISTICOS = frozenset({
    "conversa_nova", "mensagem_nova", "ja_estava", "eco_do_dashboard",
    "filtrada",
})


async def _espelhar_com_desfecho(*, company_id: str, counterparty: str, texto: str,
                                 msg_type: str, direcao: str, message_id: str,
                                 quando_iso: str, nome: Optional[str] = None,
                                 db: Any = None) -> tuple:
    """O mesmo trabalho, devolvendo ``(conversation_id, motivo)``.

    O `motivo` já existia — ele ia para o contador e era jogado fora. O cursor
    incremental precisa dele para responder uma pergunta que o `None` não
    responde: *"esta linha ficou de fora porque não devia entrar, ou porque o
    banco caiu?"* Avançar sobre a segunda perderia a mensagem para sempre.
    """
    telefone = _digitos(counterparty)
    empresa = str(company_id or "").strip()
    if not telefone or not empresa:
        return None, "sem_telefone_ou_empresa"

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _pode_haver_eco() -> bool:
        """Vale a pena PERGUNTAR pelo eco? Puro, e responde quase sempre `False`.

        🔴 É este portão que derruba a conta do Egress. Eco só pode existir para
        mensagem que a corretora enviou, com texto, e recém-chegada — porque a
        janela de comparação tem `_JANELA_DE_ECO_SEGUNDOS`. Para todo o resto
        (mensagem do cliente, mídia sem texto, e TODA linha vinda do acervo) a
        resposta é `False` e nenhuma leitura acontece.
        """
        if direcao != "out" or not str(texto or "").strip():
            return False
        try:
            nascida = datetime.fromisoformat(str(quando_iso).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            # Sem data legível, pergunta. Errar para o lado de VERIFICAR custa
            # uma leitura pequena; errar para o outro mostra a frase em dobro
            # para quem acabou de escrevê-la.
            return True
        if nascida.tzinfo is None:
            nascida = nascida.replace(tzinfo=timezone.utc)
        idade = (datetime.now(timezone.utc) - nascida).total_seconds()
        return idade <= _PORTAO_DE_ECO_SEGUNDOS

    def _eco_do_dashboard(conversa_id: str) -> bool:
        """Esta mensagem é o eco da que o dashboard acabou de enviar?

        A resposta escrita no chat vai ao WhatsApp e **volta** pelo webhook como
        `fromMe`. Sem esta guarda, cada resposta apareceria duas vezes no chat de
        quem acabou de escrevê-la.

        O caminho óbvio seria comparar o `message_id` do WhatsApp. 📊 Ele não
        está disponível: `POST /api/webhook/send-message` devolve `{"status":
        "sent"}` porque `whatsapp_service.send_message` devolve um booleano.
        Fazer o id subir por essa cadeia mexeria num caminho quente usado por
        muita coisa — risco maior que o defeito.

        Então a comparação é: mesma conversa, mesmo texto, marcado como vindo do
        dashboard, nos últimos `_JANELA_DE_ECO_SEGUNDOS`. Restrita a mensagens
        `origem='dashboard'` de propósito — assim uma atendente que digita a
        mesma palavra duas vezes NO CELULAR não perde a segunda.

        🔴 A LEITURA MUDOU EM 13/08/2026, E O FILTRO É POR `created_at`.
        Antes: as 40 últimas mensagens da conversa, para TODA mensagem. 📊 Custo
        medido: 771.313 chamadas × ~33 linhas × 290 B — a maior fatia isolada do
        Egress que restringiu o Supabase. Agora: só as dos últimos
        `_PORTAO_DE_ECO_SEGUNDOS`, e só quando `_pode_haver_eco()` deixa passar.
        Devolve tipicamente ZERO linhas.

        `created_at` é coluna comum, servida por `idx_messages_by_conversation
        (conversation_id, created_at)`, que já existe. Nenhum filtro JSON entra
        na consulta: a marca `origem` continua sendo lida EM PYTHON, sobre as
        poucas linhas carregadas — exatamente como antes.
        """
        texto_limpo = str(texto or "").strip()
        desde = (datetime.now(timezone.utc)
                 - timedelta(seconds=_PORTAO_DE_ECO_SEGUNDOS)).isoformat()
        recentes = (cliente.table("messages")
                    .select("id, content, created_at, payload")
                    .eq("conversation_id", conversa_id)
                    .gte("created_at", desde)
                    .order("created_at", desc=True)
                    .limit(_MENSAGENS_PARA_ECO).execute().data or [])
        for m in recentes:
            # A marca de origem é lida EM PYTHON, sobre linhas já carregadas.
            # Filtrar `payload->>origem` no banco foi o que cegou o espelho —
            # ver o comentário grande em `_trabalho`.
            if (m.get("payload") or {}).get("origem") != "dashboard":
                continue
            if str(m.get("content") or "").strip() != texto_limpo:
                continue
            quando = m.get("created_at")
            if quando is None:
                return True
            try:
                nascida = datetime.fromisoformat(str(quando).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return True
            if nascida.tzinfo is None:
                nascida = nascida.replace(tzinfo=timezone.utc)
            idade = (datetime.now(timezone.utc) - nascida).total_seconds()
            if 0 <= idade <= _JANELA_DE_ECO_SEGUNDOS:
                return True
        return False

    def _trabalho() -> tuple:
        """Devolve ``(conversation_id, motivo)``. O motivo vai para o contador.

        A CONVERSA É RESOLVIDA PRIMEIRO, e a dedup acontece por último.

        📊 Nota factual sobre 06/08/2026, para não repetir uma atribuição que
        nunca foi medida: a implementação daquele dia deduplicava ANTES de
        resolver a conversa, usando um filtro JSON no PostgREST
        (``.eq("payload->>wa_message_id", ...)``). O mesmo período apresentou
        também 2.255 `ImportError` (P-121) e 4.059 `APIError` por escrita em
        colunas inexistentes (`topic`, `extension`). **A causa isolada daquela
        falha não foi medida** — três defeitos foram trocados juntos, e os
        contadores nomeiam dois deles.

        O desenho atual abandona essa leitura prévia por um motivo próprio e
        medido, que não depende de resolver aquela arqueologia: `insert-first` +
        índice ÚNICO é estruturalmente mais simples e elimina a consulta
        inteira. Ver o comentário grande no passo 3.
        """
        # 🔴 É uma FÁBRICA, não um objeto de módulo.
        #
        # 📊 A primeira versão fazia `from ... import integration_service`, e
        # aquele nome NÃO EXISTE no módulo: `integration_service.py:498` exporta
        # `get_integration_service(client)`. Resultado medido em 06/08/2026:
        # **2.255 ImportError** e zero conversas no chat, com o /health dizendo
        # `espelho_no_chat: true` — porque o código existia; só não corria.
        #
        # O teste não pegou porque eu DUBLEI este módulo com a forma que eu
        # imaginava. Um dublê valida a sua suposição, não a realidade — por isso
        # agora há um guarda que lê a assinatura real do arquivo.
        from app.services.integration_service import get_integration_service

        # 1) o MESMO usuário e a MESMA chave que o pipeline do agente usa.
        #    ⚠️ A ordem é (phone, company_id, name) — conferida na assinatura
        #    real em `integration_service.py:370`. Trocar os dois primeiros
        #    criaria usuários com o id da empresa como telefone, em silêncio.
        usuario = get_integration_service(cliente).get_or_create_user(
            phone=telefone, company_id=empresa, name=nome)
        if not usuario:
            return None, "sem_usuario"

        linhas = (cliente.table("conversations").select("id, status")
                  .eq("company_id", empresa).eq("user_id", usuario)
                  .eq("channel", "whatsapp").is_("agent_id", "null")
                  .limit(1).execute().data or [])
        nasceu = not linhas
        if linhas:
            conversa_id = linhas[0]["id"]
        else:
            nova = (cliente.table("conversations").insert({
                "company_id": empresa, "channel": "whatsapp",
                "user_id": usuario, "agent_id": None,
                "user_phone": telefone,
                # 🔴 O NÚMERO INTEIRO, e não os quatro últimos dígitos.
                #
                # Founder, 06/08/2026: *"esses dados não são públicos. São da
                # corretora e não tem problema aparecer o número completo dentro
                # do dashboard para a corretora. Não entendo por que vocês fazem
                # isso sempre se piora a visualização."*
                #
                # Ele tem razão, e a distinção é a que importa em LGPD: mascarar
                # protege quem NÃO deveria ver. A corretora é a controladora
                # deste dado — é o cliente dela, no WhatsApp dela. Esconder ali
                # não protege ninguém; só impede a atendente de reconhecer quem
                # está falando.
                #
                # O que continua mascarado é outra coisa: telefone em LOG, em
                # resposta de API do admin, em relatório (CLAUDE.md §13.3).
                "user_name": nome or telefone,
                "session_id": session_id_do_chat(empresa, telefone),
                # 'open', nunca HUMAN_REQUESTED: aquele estado significa "uma
                # pessoa PEDIU para assumir" e alimenta o vigia de handoff.
                # Uma conversa espelhada não pediu nada.
                "status": "open", "status_color": "green",
                "agent_name": "Espelho", "unread_count": 0,
                "last_message_at": quando_iso,
            }).execute().data or [])
            if not nova:
                return None, "conversa_nao_criada"
            conversa_id = nova[0]["id"]

        # 2) é o eco da resposta que o próprio dashboard mandou? Então ela já
        #    está no chat, escrita por quem a digitou.
        #
        # ⚠️ Esta é a ÚNICA leitura de `messages` que sobrou, e ela quase nunca
        # acontece: `_pode_haver_eco()` a barra para tudo que não seja uma
        # mensagem de saída, com texto, recém-chegada.
        if _pode_haver_eco() and _eco_do_dashboard(conversa_id):
            return conversa_id, "eco_do_dashboard"

        # 3) a mensagem — TENTA GRAVAR, e deixa o banco responder se ela já
        #    estava lá.
        #
        # 🔴 A PERGUNTA "esta mensagem já está no chat?" DEIXOU DE SER UMA
        # LEITURA — 13/08/2026.
        #
        # Antes havia um atalho em Python sobre as 40 últimas mensagens, e o
        # próprio comentário admitia que era só atalho: a garantia sempre foi o
        # índice único parcial `messages_espelho_sem_duplicata_uidx` (migration
        # 20260806_02), que não tem janela.
        #
        # 📊 O atalho custou 771.313 leituras para produzir 5.681 mensagens —
        # 136 leituras por escrita, e a maior fatia isolada dos 6,98 GB que
        # restringiram a organização no Supabase. Um atalho que custa mais que
        # o caminho não é atalho.
        #
        # Agora a garantia responde sozinha: insere, e se o índice disser 23505,
        # a mensagem já estava. Zero leitura no caminho comum, e a dedup passa a
        # ser exatamente tão forte quanto o Postgres — nunca mais tão fraca
        # quanto uma janela de 40 linhas.
        try:
            _inserir_mensagem(cliente, conversa_id)
        except Exception as erro:  # noqa: BLE001
            # 23505 = o índice único disse "esta mensagem já está aqui". Isso é
            # o sistema funcionando, não uma falha: contar como erro faria o
            # /health gritar por um acerto.
            if "23505" in str(erro) or "duplicate key" in str(erro).lower():
                return conversa_id, "ja_estava"
            raise

        cliente.table("conversations").update({
            "last_message_preview": (texto or _rotulo_de_midia(msg_type))[:100],
            "last_message_at": quando_iso,
        }).eq("id", conversa_id).eq("company_id", empresa).execute()
        return conversa_id, ("conversa_nova" if nasceu else "mensagem_nova")

    def _inserir_mensagem(cliente: Any, conversa_id: str) -> None:
        cliente.table("messages").insert({
            "conversation_id": conversa_id,
            # É assim que o chat sabe de que lado desenhar o balão: o cliente
            # é 'user'; a corretora (pessoa ou agente) é 'assistant'.
            "role": "user" if direcao == "in" else "assistant",
            "content": texto or _rotulo_de_midia(msg_type),
            # `messages_type_check` só aceita 'text' e 'voice' — ver `_tipo_aceito`.
            "type": _tipo_aceito(msg_type),
            # 🔴 `topic` e `extension` foram REMOVIDOS daqui em 06/08/2026.
            #
            # Elas não existem em `public.messages`. Eu as vi num
            # `information_schema.columns WHERE table_name='messages'` **sem
            # filtro de schema**, e o Supabase tem `realtime.messages` além da
            # nossa: o resultado misturava as colunas das duas. O `id`
            # aparecendo em duplicidade era o aviso, e eu passei por cima.
            #
            # 📊 O preço: 4.059 APIError e toda conversa aberta com o painel
            # vazio, porque a conversa nascia e a mensagem era recusada.
            #
            # `payload` ficou — mas como coluna DE VERDADE, criada pela
            # migration 20260806_01. Ela carrega o `wa_message_id`, sem o qual
            # não há como deduplicar a reentrega do WhatsApp.
            "payload": {"wa_message_id": message_id, "origem": "espelho",
                        "direcao": direcao,
                        # O tipo de VERDADE fica aqui, para o dia em que a
                        # mídia for tocável no chat (P-119).
                        "wa_type": str(msg_type or "text")},
        }).execute()

    try:
        conversa_id, motivo = await asyncio.to_thread(_trabalho)
        await contar(motivo)
        return conversa_id, motivo
    except Exception as erro:  # noqa: BLE001
        # O espelho é um bônus; a CAPTURA é a obrigação, e ela já aconteceu
        # antes desta chamada. Falhar aqui não pode perder conversa nenhuma.
        #
        # Mas o MOTIVO não se perde mais: vai para o contador, e do contador
        # para o /health. 📊 Foi por não ter isto que 13.200 mensagens entraram
        # e ninguém conseguiu dizer por que o chat continuava vazio.
        #
        # 🔴 E agora o motivo tem um segundo leitor: o cursor incremental. Um
        # `erro:*` NÃO está em `DESFECHOS_DETERMINISTICOS`, então o cursor para
        # antes desta linha e volta nela na próxima passada. Sem isso, uma queda
        # de rede de três segundos apagaria uma mensagem do chat para sempre.
        motivo = f"erro:{type(erro).__name__}"
        await contar(motivo)
        logger.warning("[ESPELHO] não consegui espelhar no chat (%s)", type(erro).__name__)
        return None, motivo


async def pausar_por_intervencao_humana(*, company_id: str, counterparty: str,
                                        quem: str = "Atendente pelo celular",
                                        db: Any = None) -> bool:
    """Uma pessoa respondeu: o agente cala NESTA conversa, e só nesta.

    Decisão do Founder, 06/08/2026:

        "Ele precisa parar a conversar com aquele cliente naquele número, mas
         ele deve continuar ligado e fazendo o trabalho dele nas outras
         conversas. Ele só para totalmente se o agente for desligado no botão."

    Por isso o UPDATE é por LINHA de conversa e **nunca** toca `agents.is_active`.
    Duas pessoas respondendo o mesmo cliente é o defeito que isto evita; um
    agente mudo na corretora inteira seria um defeito maior.

    `closed` fica de fora: conversa encerrada não ressuscita porque alguém
    mandou uma mensagem solta para o mesmo número.

    Devolve ``True`` quando alguma conversa foi pausada. Nunca levanta — se a
    pausa falhar, a captura e o espelho já aconteceram, e o pior caso é o
    agente responder junto uma vez, não o produto cair.
    """
    telefone = _digitos(counterparty)
    empresa = str(company_id or "").strip()
    if not telefone or not empresa:
        return False

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _trabalho() -> bool:
        resposta = (cliente.table("conversations").update({
            "status": "HUMAN_REQUESTED",
            "claimed_by_name": quem,
            "claimed_at": _agora_iso(),
        }).eq("company_id", empresa).eq("channel", "whatsapp")
          .eq("user_phone", telefone).neq("status", "closed").execute())
        return bool(getattr(resposta, "data", None))

    try:
        pausou = await asyncio.to_thread(_trabalho)
        if pausou:
            # Sem o telefone no log: é a linha de trabalho de uma pessoa real
            # e a de um segurado (CLAUDE.md §13.3). Qual corretora basta.
            logger.info("[ESPELHO] intervenção humana pausou o agente numa conversa de %s",
                        empresa)
        return pausou
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] não consegui pausar a conversa (%s)", type(erro).__name__)
        return False


async def trazer_conversas_ja_capturadas(
    *, company_id: str, dias: int = JANELA_DA_LISTA_DIAS, limite: int = 3000,
    db: Any = None
) -> dict:
    """Leva ao chat o que o Observador JÁ capturou. Uma vez, sob demanda.

    POR QUE ISTO EXISTE
    ===================
    A ponte só age quando chega mensagem nova. 📊 Em 06/08/2026, no dia em que
    ela subiu, a AutoFleet tinha **32.128 mensagens capturadas em 7 dias** e o
    chat abriu vazio — porque a última mensagem tinha entrado 22 minutos antes
    do deploy. A corretora estaria olhando uma tela vazia sobre um acervo cheio,
    esperando um cliente escrever.

    Não é motor paralelo: é a MESMA `espelhar_no_chat`, chamada em lote a partir
    do acervo em vez do webhook. E é idempotente pelo `message_id`, então rodar
    duas vezes não duplica nada.

    `dias=2` por padrão porque a mesa de trabalho é do que está aberto agora;
    quem quiser a semana inteira pede `dias=7`. `limite` existe para a chamada
    não virar uma varredura de 32 mil linhas sem ninguém ter pedido isso.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return {"ok": False, "motivo": "company_id_obrigatorio"}

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    desde = (datetime.now(timezone.utc) - timedelta(days=max(1, int(dias)))).isoformat()

    def _ler_pagina_do_acervo(inicio: int, fim: int) -> list:
        return (cliente.table("attendance_transcripts")
                .select("counterparty, direction, msg_type, text, message_id, wa_timestamp")
                .eq("company_id", empresa)
                # 🔴 `wa_timestamp` (quando a mensagem FOI ENVIADA), nunca
                # `created_at` (quando ela foi GRAVADA). São coisas diferentes e
                # confundi-las quase encheu o chat de conversa morta.
                #
                # 📊 06/08/2026, Amandus: um pareamento novo trouxe o histórico
                # inteiro pelo HISTORY_SYNC. Todas as linhas ficaram com
                # `created_at` de hoje — e `wa_timestamp` de até **maio de
                # 2025**. Filtrando por `created_at`, a janela de "2 dias"
                # pegava 34.072 mensagens de quinze meses. Filtrando por
                # `wa_timestamp`, pega 127.
                #
                # A mesa de trabalho é do que está aberto agora. O histórico
                # continua inteiro no acervo e no Espelho do admin.
                .gte("wa_timestamp", desde)
                # 🔴 MAIS RECENTES PRIMEIRO — e o motivo é um defeito medido.
                #
                # 📊 06/08/2026: com `desc=False` + `limit`, o banco devolvia as
                # 1.500 mensagens MAIS ANTIGAS da janela. O chat da AutoFleet
                # parou em **04/08** e os dias 05 e 06 — os que interessavam —
                # nunca chegaram. O limite não cortava o fim da fila; cortava o
                # começo dela.
                #
                # A ordem de LEITURA e a ordem de EXIBIÇÃO são coisas
                # diferentes: aqui se lê do mais novo para trás, e a inversão
                # abaixo devolve a ordem da conversa.
                .order("wa_timestamp", desc=True)
                # 🔴 DESEMPATE OBRIGATÓRIO PARA PAGINAR.
                #
                # `wa_timestamp` tem resolução de SEGUNDO e mensagens empatam
                # nele o tempo todo (uma pessoa manda três seguidas). Sem um
                # segundo critério, a ordem dos empatados pode mudar entre uma
                # página e a próxima — e aí a mesma linha aparece duas vezes
                # enquanto outra nunca aparece. `message_id` é único, então a
                # ordem passa a ser total e a paginação, estável.
                .order("message_id", desc=True)
                .range(inicio, fim).execute().data or [])

    # 🔴 O `.limit()` PEDIA 1.500 E O SERVIDOR DEVOLVIA 1.000.
    #
    # 📊 06/08/2026 23:52 UTC, AutoFleet: a janela de 7 dias tem **1.570**
    # linhas no acervo e o chat tinha **exatamente 1.000** mensagens — parado,
    # sem crescer, com 19 conversas abertas e vazias na lista. Todas as 19 eram
    # as de atividade mais ANTIGA da janela (03 e 04/08): o corte por
    # `wa_timestamp desc` deixava justamente elas de fora.
    #
    # O número redondo era a pista. O PostgREST tem um teto de linhas por
    # resposta (`db-max-rows`) e ele VENCE o `.limit()` que se pede: pedir 1.500
    # não é erro, é só ignorado. O código então "lia" 1.000 linhas, achava que
    # tinha lido a janela inteira, e repetia as MESMAS 1.000 a cada 10 minutos —
    # para sempre. As outras 570 nunca teriam vez.
    #
    # A correção não é aumentar o número: qualquer número volta a ser pequeno
    # quando a corretora crescer. É PAGINAR e parar quando a página vier curta —
    # que é a única forma de "acabou" que não depende de adivinhar o teto.
    _TAMANHO_DA_PAGINA = 1000
    paginas = max(1, -(-int(limite) // _TAMANHO_DA_PAGINA))  # teto da divisão

    linhas: list = []
    for pagina in range(paginas):
        inicio = pagina * _TAMANHO_DA_PAGINA
        try:
            lote = await asyncio.to_thread(
                _ler_pagina_do_acervo, inicio, inicio + _TAMANHO_DA_PAGINA - 1)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[ESPELHO] backfill não leu o acervo (%s)", type(erro).__name__)
            if linhas:
                break  # o que já veio ainda vale; espelhar meia janela > nenhuma
            return {"ok": False, "motivo": type(erro).__name__}
        linhas.extend(lote)
        # Página curta = acabou. Não depende de saber qual é o teto do servidor.
        if len(lote) < _TAMANHO_DA_PAGINA:
            break

    # Lidas do mais novo para trás (ver `_ler_pagina_do_acervo`); gravadas na ordem da conversa.
    # Sem esta inversão, o chat mostraria a resposta antes da pergunta.
    linhas = list(reversed(linhas))

    levadas = 0
    for linha in linhas:
        quando = str(linha.get("wa_timestamp") or "") or _agora_iso()
        conversa = await espelhar_no_chat(
            company_id=empresa,
            counterparty=str(linha.get("counterparty") or ""),
            texto=str(linha.get("text") or ""),
            msg_type=str(linha.get("msg_type") or "text"),
            direcao=str(linha.get("direction") or "in"),
            message_id=str(linha.get("message_id") or ""),
            quando_iso=quando, db=db)
        if conversa:
            levadas += 1

    logger.info("[ESPELHO] backfill de %s: %s linhas lidas, %s levadas ao chat",
                empresa, len(linhas), levadas)
    return {"ok": True, "lidas": len(linhas), "levadas": levadas, "dias": dias}


async def sincronizar_chats() -> dict:
    """Varre as corretoras ativas e leva ao chat o que ainda não chegou lá.

    POR QUE ISTO É AUTOMÁTICO, e não um comando
    ============================================
    O Founder, 06/08/2026: *"eu não sei como fazer isso. Onde é /app? Também
    não quero ter todo esse trabalho. Eu só quero as coisas funcionando."*

    Ele está certo, e a versão anterior — um comando de console — era um
    conserto que exigia da pessoa errada o trabalho errado. Um produto que
    precisa de alguém abrir terminal para mostrar as conversas do dia não está
    pronto; está esperando ajuda.

    Roda no agendador que já existe (`buffer_processor`), junto do heartbeat.
    Nenhum motor novo (CLAUDE.md §5).

    É barato porque é incremental: a dedup por `message_id` faz a segunda
    passada não escrever nada. E é a rede que pega o que a ponte ao vivo perdeu
    — mensagem que chegou durante um deploy, erro momentâneo do banco, ou o
    acervo que já estava lá antes de a ponte existir.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _corretoras() -> list:
        return (cliente.table("integrations").select("company_id")
                .eq("provider", "evolution-go").eq("is_active", True)
                .limit(200).execute().data or [])

    try:
        linhas = await asyncio.to_thread(_corretoras)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] sync não leu as corretoras (%s)", type(erro).__name__)
        return {"ok": False, "motivo": type(erro).__name__}

    vistas: set = set()
    resumo = {"ok": True, "corretoras": 0, "levadas": 0}
    for linha in linhas:
        empresa = str(linha.get("company_id") or "").strip()
        if not empresa or empresa in vistas:
            continue
        vistas.add(empresa)
        resumo["corretoras"] += 1
        # Janela curta: a passada é frequente, e o que interessa é o que a
        # ponte ao vivo pode ter perdido agora há pouco. O acervo antigo já
        # entrou na primeira passada depois do deploy.
        # A MESMA janela que a lista do chat mostra. Dois números diferentes
        # para a mesma ideia seriam duas coisas para lembrar e uma para errar:
        # a mesa de trabalho mostra 7 dias, então o sync leva 7 dias.
        r = await trazer_conversas_ja_capturadas(
            company_id=empresa,
            dias=int(os.getenv("ESPELHO_SYNC_DIAS", str(JANELA_DA_LISTA_DIAS))),
            # 📊 A janela de 7 dias da AutoFleet tem 1.570 linhas (06/08/2026).
            # 6.000 dá quase 4× de folga sobre a maior corretora de hoje, e o
            # custo real é baixo: quem já está no chat sai pela dedup sem
            # escrita. O teto existe para o dia em que uma corretora tiver um
            # volume que não cabe num ciclo do agendador — não para o normal.
            limite=int(os.getenv("ESPELHO_SYNC_LIMITE", "6000")), db=db)
        resumo["levadas"] += int(r.get("levadas") or 0)

    logger.info("[ESPELHO] sync: %s corretoras, %s mensagens levadas ao chat",
                resumo["corretoras"], resumo["levadas"])
    return resumo


__all__ = [
    "deve_espelhar", "espelhar_no_chat", "session_id_do_chat",
    "pausar_por_intervencao_humana", "trazer_conversas_ja_capturadas",
    "sincronizar_chats", "contar", "diagnostico",
    "JANELA_DA_LISTA_DIAS", "LIMITE_DE_RECENCIA_HORAS",
]
