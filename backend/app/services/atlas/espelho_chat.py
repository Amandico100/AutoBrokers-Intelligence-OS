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

from app.services.atlas.canais_observados import (
    NATUREZAS_QUE_NAO_SAO_CLIENTE,
    natureza_da_contraparte,
)

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
                  limite_horas: float = LIMITE_DE_RECENCIA_HORAS,
                  company_id: str = "") -> bool:
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

    # 🔴 O PORTÃO ACIMA EXISTIA E NUNCA DISPAROU — 15/08/2026.
    #
    # 📊 `e_seguradora` vem de `bool(linha.get("insurer_key"))`, e `insurer_key`
    # estava NULO em 100% das 150.734 linhas do acervo. `bool(None)` é False
    # sempre: a linha 254 tem teste, tem comentário, e nunca barrou uma
    # mensagem sequer neste caminho.
    #
    # 📊 O que passava por ela: 10,9% da mesa da Saionara e 6,8% da mesa da
    # Regina são robôs de seguradora — 714 e 652 mensagens que não são cliente
    # nenhum. A fila de espera da MAPFRE no meio de quem precisa dela.
    #
    # A pergunta certa não é "tem chave de seguradora?", é **"isto é gente?"**.
    # Uma conversa com a Localiza sobre carro reserva não tem `insurer_key` — e
    # não deve ter, porque a Localiza atende HDI e Tokio — mas também não é
    # cliente, e não pertence à mesa.
    #
    # ⚠️ Fail-open de propósito: `natureza_da_contraparte` devolve None tanto
    # para "é uma pessoa" quanto para "ainda não sabemos", e as duas continuam
    # na mesa. Mostrar uma conversa a mais custa um clique; esconder um cliente
    # de verdade custa o cliente.
    #
    # 🔴 O import é NO TOPO do módulo, e não aqui dentro com `try/except`.
    # Minha primeira versão embrulhou esta chamada num `except Exception: pass`
    # — que é PRECISAMENTE o defeito narrado no cabeçalho deste arquivo: um
    # ImportError engolido deixou o chat vazio 2.255 vezes com o /health
    # dizendo `espelho_no_chat: true`. Guarda que não consegue falhar não
    # guarda nada; se o catálogo sumir, é para quebrar alto.
    if natureza_da_contraparte(counterparty, company_id or "") in (
            NATUREZAS_QUE_NAO_SAO_CLIENTE):
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
#
# 🔴 `sem_telefone_ou_empresa` ENTROU AQUI EM 15/08/2026, e o motivo é que ele
# não é um erro: é uma RECUSA PERMANENTE.
#
# A elegibilidade (`deve_espelhar`) exige apenas `counterparty.strip()`
# não-vazio. A gravação (`_espelhar_com_desfecho`) exige `_digitos(...)`
# não-vazio. Uma contraparte sem nenhum dígito — `status@broadcast`, um JID
# `@lid` alfanumérico — passa na primeira e é recusada pela segunda, **sempre,
# com o mesmo resultado**. Estando fora desta lista, ela travaria o cursor
# daquela corretora para sempre: a passada seguinte lê a mesma linha, recebe a
# mesma recusa, e para no mesmo lugar. Uma corretora inteira parada por uma
# linha que nunca teve conserto possível.
#
# 📊 Medido em 15/08 antes de mexer: ZERO linhas sem dígito em 150.734, nas
# três corretoras. O gatilho não existe hoje — a guarda é para o dia em que
# existir, e ela custa uma palavra.
#
# ⚠️ `sem_usuario` e `conversa_nao_criada` continuam FORA de propósito: os dois
# significam "o banco não respondeu agora", e ultrapassá-los perde a mensagem.
DESFECHOS_DETERMINISTICOS = frozenset({
    "conversa_nova", "mensagem_nova", "ja_estava", "eco_do_dashboard",
    "filtrada", "sem_telefone_ou_empresa",
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
                .select("counterparty, direction, msg_type, text, message_id, "
                        "wa_timestamp, insurer_key")
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
        # 🔴 A MESMA ELEGIBILIDADE DA PONTE AO VIVO — acrescentada em 13/08/2026.
        #
        # Este backfill NÃO chamava `deve_espelhar`. Consequência: uma mensagem
        # que chegasse ao vivo valia 30 dias (`LIMITE_DE_RECENCIA_HORAS`) e a
        # MESMA mensagem, vinda do acervo, valia o `dias` desta chamada. Duas
        # regras para a mesma pergunta, escolhidas pelo caminho que a mensagem
        # tomou — e conversa de seguradora entrava aqui e não entrava lá.
        #
        # Agora é uma regra só, e é a documentada.
        if not deve_espelhar(
            counterparty=str(linha.get("counterparty") or ""),
            texto=str(linha.get("text") or ""),
            msg_type=str(linha.get("msg_type") or "text"),
            e_grupo=False,
            e_seguradora=bool(linha.get("insurer_key")),
            idade_horas=_idade_em_horas(quando),
            company_id=empresa,
        ):
            continue
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


def _idade_em_horas(quando_iso: str) -> float:
    """Há quantas horas esta mensagem foi ENVIADA. Sem data legível, trata como
    antiquíssima — o lado seguro é deixar de fora da mesa, nunca despejar."""
    try:
        quando = datetime.fromisoformat(str(quando_iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return float("inf")
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - quando).total_seconds() / 3600.0


def sync_ligado() -> bool:
    """O interruptor do recovery periódico. 🔴 DESLIGADO por padrão.

    📊 13/08/2026: este job consumiu sozinho a ordem dos 6,98 GB que
    restringiram a organização no Supabase, e não havia como desligá-lo sem
    derrubar o produto. `ESPELHO_SYNC_LIMITE=0` não servia — a paginação faz
    `max(1, ...)` e leria uma página do mesmo jeito.

    Padrão OFF e não ON, e a escolha é deliberada: no primeiro boot depois do
    Upgrade para Pro, dezenas de componentes que estão recebendo 402 voltam a
    funcionar ao mesmo tempo. Um sync que sobe ligado nesse instante é
    exatamente o que não pode acontecer. Ligar é um ato com data e medição.

    ⚠️ Enquanto estiver OFF, a rede de segurança do Espelho não roda. A ponte
    AO VIVO continua inteira: mensagem nova aparece no chat normalmente. O que
    fica desligado é só a recuperação do que a ponte perdeu — e para isso existe
    `POST /api/whatsapp-channel/espelho/trazer-conversas`, dirigido e medido.
    """
    return str(os.getenv("ESPELHO_SYNC_ENABLED", "0")).strip().lower() in (
        "1", "true", "yes", "on", "sim")


# Quanto o cursor fica ATRÁS do presente. 🔴 Não é folga de conforto.
#
# `created_at` tem `DEFAULT now()`, e `now()` no Postgres é o instante em que a
# TRANSAÇÃO COMEÇOU — não o do commit. Uma linha pode ser carimbada 10:00:00 e
# só ficar visível às 10:00:02. Se o cursor já tiver passado de 10:00:00, ela
# nunca mais é vista: perda silenciosa, exatamente o defeito que este cursor
# existe para evitar.
#
# 5 minutos é margem enorme sobre um INSERT de webhook (milissegundos) e não
# custa nada em latência percebida: a ponte AO VIVO já levou a mensagem ao chat
# no instante em que ela chegou. Quem espera estes 5 minutos é só a mensagem que
# a ponte perdeu — e antes ela esperava um ciclo inteiro de 10 minutos.
_ATRASO_DE_SEGURANCA_SEGUNDOS = 300.0

# Quantas linhas por corretora por passada. O que não couber vem na próxima:
# o cursor não anda além do que foi processado, então nada se perde.
_LOTE_DO_SYNC = 500

# Quantas vezes a MESMA linha é tentada antes de a passada desistir dela. Três
# é o número de um erro de conexão transitório: a primeira paga o descarte da
# conexão morta, a segunda já corre na nova. Acima disso não é mais rede — é
# defeito, e defeito tem de travar o cursor para aparecer.
_TENTATIVAS_POR_LINHA = 3


async def sincronizar_chats() -> dict:
    """Leva ao chat o que CHEGOU ao acervo desde a última passada. Incremental.

    POR QUE ISTO É AUTOMÁTICO, e não um comando
    ============================================
    O Founder, 06/08/2026: *"eu não sei como fazer isso. Onde é /app? Também
    não quero ter todo esse trabalho. Eu só quero as coisas funcionando."*

    Roda no agendador que já existe (`buffer_processor`), junto do heartbeat.
    Nenhum motor novo (CLAUDE.md §5).

    🔴 O QUE MUDOU EM 13/08/2026 — E POR QUE O COMENTÁRIO ANTIGO MENTIA
    ===================================================================
    Aqui dizia: *"É barato porque é incremental: a dedup por `message_id` faz a
    segunda passada não escrever nada."*

    A frase estava certa sobre ESCRITAS e errada sobre LEITURAS, e a diferença
    custou o produto inteiro. 📊 A implementação relia a janela de 7 dias do
    acervo a cada ciclo — 4.008 linhas — e chamava `espelhar_no_chat` para cada
    uma. `pg_stat_statements` de produção: **771.313 leituras de `messages` para
    5.681 mensagens escritas**. Da ordem dos 6,98 GB que restringiram a
    organização no Supabase Free; PostgREST, Storage e Auth passaram a responder
    402 e o portal-worker parou de enxergar `portal_jobs`.

    Deduplicar DEPOIS de ler não torna a leitura barata. Agora ele é incremental
    de verdade: um cursor durável por corretora, no relógio de INGESTÃO.

    AS GARANTIAS, e o que cada uma custa
    ====================================
    · **Nada se perde por erro.** O cursor só avança sobre o maior PREFIXO de
      linhas com desfecho determinístico. Uma falha de rede no meio da página
      trava o cursor ANTES dela, e ela volta na passada seguinte — para sempre,
      até dar um desfecho conhecido.
    · **Nada se perde por relógio.** O cursor é `created_at` (ingestão), nunca
      `wa_timestamp` (evento). 📊 99,89% das linhas `history_sync` chegam com
      mais de 15 min de atraso entre os dois; um cursor por `wa_timestamp` não
      as veria. Ver o cabeçalho da migration 20260813_01.
    · **Nada se perde por commit tardio.** `_ATRASO_DE_SEGURANCA_SEGUNDOS`.
    · **Nada é despejado.** `deve_espelhar` continua julgando por
      `wa_timestamp`: uma linha de 2024 que chega hoje é ENCONTRADA pelo cursor
      e RECUSADA pela elegibilidade. É o comportamento certo nas duas pontas.
    · **Nenhuma corretora nova varre o acervo.** Sem cursor = cria em `now()` e
      não lê nada. A recuperação inicial é ato deliberado.
    · **Nenhum tenant vê o outro.** O cursor é POR `company_id`, e a leitura
      filtra por `company_id`.
    """
    if not sync_ligado():
        await contar("sync_desligado")
        return {"ok": True, "desligado": True, "corretoras": 0, "levadas": 0}

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
    resumo = {"ok": True, "corretoras": 0, "lidas": 0, "levadas": 0,
              "ja_estavam": 0, "filtradas": 0, "travou_em": 0, "retentadas": 0}
    for linha in linhas:
        empresa = str(linha.get("company_id") or "").strip()
        if not empresa or empresa in vistas:
            continue
        vistas.add(empresa)
        resumo["corretoras"] += 1
        r = await _sincronizar_uma_corretora(empresa, cliente)
        for chave in ("lidas", "levadas", "ja_estavam", "filtradas",
                      "travou_em", "retentadas"):
            resumo[chave] += int(r.get(chave) or 0)

    # 📊 A LINHA QUE TORNA O DESPERDÍCIO VISÍVEL.
    #
    # O incidente foi possível porque nada respondia "quantas linhas eu li para
    # descobrir quantas novidades?". A resposta agora sai em toda passada:
    # 4.008 lidas para 3 novas é o sintoma que ninguém viu por sete dias.
    # Agregado, nunca conteúdo (CLAUDE.md §13.3).
    #
    # 📊 `retentadas` entrou em 15/08: sem ela, "499 lidas · 0 novas" não dizia
    # se o lote morreu numa falha de rede ou se realmente não havia novidade.
    # Duas causas opostas com a mesma cara — e a resposta custava um contador.
    logger.info(
        "[ESPELHO] sync: %s corretora(s) · %s lida(s) · %s nova(s) · "
        "%s já estavam · %s filtrada(s) · %s retentada(s) · %s travada(s) por erro",
        resumo["corretoras"], resumo["lidas"], resumo["levadas"],
        resumo["ja_estavam"], resumo["filtradas"], resumo["retentadas"],
        resumo["travou_em"])
    await contar("sync_ciclo")
    await contar("sync_linhas_lidas", resumo["lidas"])
    await contar("sync_mensagens_novas", resumo["levadas"])
    if resumo["retentadas"]:
        await contar("sync_linhas_retentadas", resumo["retentadas"])
    return resumo


async def _sincronizar_uma_corretora(empresa: str, cliente: Any) -> dict:
    """Uma passada incremental para UMA corretora. O coração da Alavanca B."""
    agora = datetime.now(timezone.utc)
    teto = (agora - timedelta(seconds=_ATRASO_DE_SEGURANCA_SEGUNDOS)).isoformat()

    def _ler_cursor() -> Optional[dict]:
        linhas = (cliente.table("espelho_sync_cursor")
                  .select("company_id, last_created_at, last_id")
                  .eq("company_id", empresa).limit(1).execute().data or [])
        return linhas[0] if linhas else None

    def _nascer_cursor() -> None:
        """🔴 Corretora sem cursor NÃO dispara varredura. Nasce no presente.

        📊 O acervo tem 105.275 linhas. Partir do começo dos tempos seria 26×
        o ciclo que causou o incidente — e aconteceria no minuto seguinte ao
        Founder pagar pelo Pro. Vale para a Amandus de hoje e para a quarta
        corretora que entrar daqui a três meses: a recuperação inicial é um ato
        deliberado, pelo endpoint `espelho/trazer-conversas`, com janela
        explícita e medição.
        """
        cliente.table("espelho_sync_cursor").insert({
            "company_id": empresa,
            "last_created_at": agora.isoformat(),
            "last_id": None,
        }).execute()

    try:
        cursor = await asyncio.to_thread(_ler_cursor)
    except Exception as erro:  # noqa: BLE001
        # Sem cursor legível não há passada segura. Não varrer é o lado certo
        # de errar: o acervo continua inteiro e a ponte ao vivo, funcionando.
        logger.warning("[ESPELHO] sync não leu o cursor de %s (%s)",
                       empresa, type(erro).__name__)
        await contar(f"cursor_erro:{type(erro).__name__}")
        return {}

    if cursor is None:
        try:
            await asyncio.to_thread(_nascer_cursor)
            await contar("cursor_nasceu")
            logger.info("[ESPELHO] corretora %s ganhou cursor em %s — "
                        "recuperação inicial é deliberada, não automática",
                        empresa, agora.isoformat())
        except Exception as erro:  # noqa: BLE001
            logger.warning("[ESPELHO] não consegui criar o cursor de %s (%s)",
                           empresa, type(erro).__name__)
        return {}

    desde = str(cursor.get("last_created_at") or "")
    ultimo_id = str(cursor.get("last_id") or "")

    def _ler_novidades() -> list:
        # `>=` e não `>`: linhas com o MESMO `created_at` do cursor e `id` maior
        # existem (inserção em lote). O desempate acontece em Python, logo
        # abaixo. Reler a própria linha do cursor custa uma linha por passada e
        # é idempotente — o índice único responde 23505.
        return (cliente.table("attendance_transcripts")
                .select("id, counterparty, direction, msg_type, text, "
                        "message_id, wa_timestamp, created_at, insurer_key")
                .eq("company_id", empresa)
                .gte("created_at", desde)
                .lt("created_at", teto)
                .order("created_at").order("id")
                .limit(_LOTE_DO_SYNC).execute().data or [])

    try:
        novidades = await asyncio.to_thread(_ler_novidades)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] sync não leu o acervo de %s (%s)",
                       empresa, type(erro).__name__)
        return {}

    # O desempate: descarta o que já ficou para trás dentro do mesmo segundo.
    if ultimo_id:
        novidades = [n for n in novidades
                     if not (str(n.get("created_at")) == desde
                             and str(n.get("id") or "") <= ultimo_id)]

    contagem = {"lidas": len(novidades), "levadas": 0, "ja_estavam": 0,
                "filtradas": 0, "travou_em": 0, "retentadas": 0}
    avancar_para: Optional[tuple] = None

    for item in novidades:
        quando = str(item.get("wa_timestamp") or "") or _agora_iso()
        contraparte = str(item.get("counterparty") or "")
        if not deve_espelhar(
            counterparty=contraparte,
            texto=str(item.get("text") or ""),
            msg_type=str(item.get("msg_type") or "text"),
            # 📊 O acervo não tem coluna de grupo: o filtro de borda do
            # `observer_tap` já barra grupo antes de gravar (conferido em
            # 13/08 — zero linhas com cara de grupo na janela). Seguradora tem
            # coluna, e é ela que responde aqui.
            e_grupo=False,
            e_seguradora=bool(item.get("insurer_key")),
            idade_horas=_idade_em_horas(quando),
            company_id=empresa,
        ):
            # 🔴 A ELEGIBILIDADE VOLTOU A SER A MESMA NOS DOIS CAMINHOS.
            # O backfill antigo NÃO chamava `deve_espelhar`: mensagem que chegava
            # ao vivo valia 30 dias e a MESMA mensagem, vinda do acervo, valia 7.
            # Duas regras para a mesma pergunta, decididas pelo caminho que a
            # mensagem tomou. Agora é uma só, e é a documentada.
            contagem["filtradas"] += 1
            avancar_para = (str(item.get("created_at")), str(item.get("id") or ""))
            continue

        # 🔴 O ERRO DE REDE LEVAVA O LOTE INTEIRO JUNTO — 15/08/2026.
        #
        # 📊 Medido no /health: a passada lia **499** linhas e avançava **~45**.
        # As outras 455 voltavam na passada seguinte, e na seguinte. O acervo da
        # Resulta drenava a 45 linhas/min: 28.180 pendentes = ~10 horas.
        #
        # A causa era um `RemoteProtocolError` (o Supabase fecha uma conexão do
        # pool que ficou parada; a primeira chamada depois disso morre e a
        # próxima funciona). Uma linha falhava e o `break` abaixo descartava o
        # trabalho das 455 seguintes — que já estavam LIDAS, ou seja, o Egress
        # já tinha sido pago. Pagar a leitura e jogar fora é exatamente o
        # desperdício que derrubou a conta em agosto, na versão pequena.
        #
        # A correção NÃO é ultrapassar a linha ruim: isso perderia mensagem, e é
        # o defeito que o cursor existe para impedir. É dar à linha as chances
        # que um erro transitório pede antes de desistir do lote.
        motivo = ""
        for tentativa in range(_TENTATIVAS_POR_LINHA):
            _conversa, motivo = await _espelhar_com_desfecho(
                company_id=empresa, counterparty=contraparte,
                texto=str(item.get("text") or ""),
                msg_type=str(item.get("msg_type") or "text"),
                direcao=str(item.get("direction") or "in"),
                message_id=str(item.get("message_id") or ""),
                quando_iso=quando, db=cliente)
            if motivo in DESFECHOS_DETERMINISTICOS:
                break
            if tentativa + 1 < _TENTATIVAS_POR_LINHA:
                # A espera é curta e cresce: 0,4s e 0,8s. O suficiente para uma
                # conexão nova nascer, pouco o bastante para não segurar a
                # passada. Reinserir é seguro — o índice único responde 23505 e
                # o desfecho vira `ja_estava`.
                contagem["retentadas"] += 1
                await asyncio.sleep(0.4 * (2 ** tentativa))

        if motivo not in DESFECHOS_DETERMINISTICOS:
            # 🔴 O CURSOR PARA AQUI, ANTES DESTA LINHA.
            #
            # Um `erro:APIError` de três segundos não pode virar uma mensagem
            # que nunca aparece no chat. Ela volta na próxima passada, e na
            # seguinte, até dar um desfecho que se possa ultrapassar. Um cursor
            # rápido que perde mensagem é pior que o problema que ele resolve.
            contagem["travou_em"] += 1
            logger.warning("[ESPELHO] cursor de %s parou numa linha com "
                           "desfecho '%s' — ela volta na próxima passada",
                           empresa, motivo)
            break

        if motivo in ("conversa_nova", "mensagem_nova"):
            contagem["levadas"] += 1
        elif motivo == "sem_telefone_ou_empresa":
            # ⚠️ Contar como `ja_estavam` seria o campo MENTINDO sobre o que
            # guarda (CLAUDE.md §12.1): esta linha não estava na mesa e nunca
            # vai estar. Ela é uma recusa — a mesma família de `filtrada`.
            contagem["filtradas"] += 1
        else:
            contagem["ja_estavam"] += 1
        avancar_para = (str(item.get("created_at")), str(item.get("id") or ""))

    if avancar_para:
        def _gravar_cursor() -> None:
            cliente.table("espelho_sync_cursor").update({
                "last_created_at": avancar_para[0],
                "last_id": avancar_para[1] or None,
                "updated_at": _agora_iso(),
            }).eq("company_id", empresa).execute()

        try:
            await asyncio.to_thread(_gravar_cursor)
        except Exception as erro:  # noqa: BLE001
            # Cursor não gravado = a próxima passada refaz este trecho. Caro,
            # nunca incorreto: tudo aqui é idempotente.
            logger.warning("[ESPELHO] não consegui gravar o cursor de %s (%s)",
                           empresa, type(erro).__name__)

    return contagem


__all__ = [
    "deve_espelhar", "espelhar_no_chat", "session_id_do_chat",
    "pausar_por_intervencao_humana", "trazer_conversas_ja_capturadas",
    "sincronizar_chats", "sync_ligado", "contar", "diagnostico",
    "JANELA_DA_LISTA_DIAS", "LIMITE_DE_RECENCIA_HORAS",
    "DESFECHOS_DETERMINISTICOS",
]
