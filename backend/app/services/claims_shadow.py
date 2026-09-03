# -*- coding: utf-8 -*-
"""A sombra do sinistro — SPEC-093-B, BLOCO A (detector + abertura) e BLOCO B (o ledger).

O que este módulo é
-------------------
O atendimento de hoje é feito por gente, no WhatsApp, e não deixa rastro estruturado
(📊 SPEC-093-B §1.1–§1.4: nenhuma tabela de "caso", `attendance_sessions.servico` NULL
em 12.616 de 12.616, `work_events` com ator humano = 0 em 35.705). Este módulo abre um
**Work Run de sombra** por conversa que fala de sinistro e transforma cada gesto que
JÁ acontece num evento do vocabulário — para que o trabalho humano vire dataset.

⛔ **A sombra OBSERVA.** Ela não envia mensagem, não liga agente, não muda um turno do
atendimento e nunca levanta exceção para quem a chama. Toda função de I/O daqui
devolve `None`/`False` em vez de estourar: o atendimento é mais importante que o rastro.

⛔ **ZERO texto livre.** `input_payload` e `payload_redacted` só recebem chaves
declaradas em `lib/atendimento/claims-shadow-vocab.json`, com valores de enum, contagem,
tipo de documento ou timestamp. Nada do que o segurado escreveu entra aqui
(SPEC-093-B §2 · referência ⑦ GDPR Art. 5(1)(c), minimização por construção).
`message_human` vem de TEMPLATE fixo — nunca de interpolação de texto do segurado.

Por que o vocabulário mora em `lib/` e não aqui
-----------------------------------------------
📊 O Next não importa nada de `backend/`. O mesmo arquivo é lido pelo Python por
caminho a partir da raiz do repo e pelo Next via `@/` — o precedente é
`lib/admin/portao-do-prompt.contract.json`. **Um vocabulário em dois arquivos são dois
vocabulários**, e o guarda compara o sha256 dos dois lados.

⚠️ Os TEMPLATES de `message_human` ficam aqui, em Python, e **não** no JSON: o
vocabulário está congelado (sha256 conferido pelos dois stacks) e acrescentar chave a
ele quebraria o gate B⑤ do guarda.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import io
import json
import logging
import os
import re
import unicodedata
import weakref
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# O VOCABULÁRIO — lido UMA vez por processo, do arquivo único da raiz do repo
# ---------------------------------------------------------------------------
_AQUI = os.path.dirname(os.path.abspath(__file__))            # backend/app/services
_RAIZ_DO_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_AQUI)))
CAMINHO_DO_VOCABULARIO = os.path.join(
    _RAIZ_DO_REPO, "lib", "atendimento", "claims-shadow-vocab.json")

WORKFLOW_KEY = "claims.shadow"
OUTCOME_TYPE = "claims.shadow"
OUTCOME_TITLE = "Sombra de sinistro"
RUNTIME_KIND = "sombra"
PREFIXO_DA_CHAVE = "claims.shadow:"

#: 📊 O CHECK real de `work_events.actor_type`, transcrito em
#: `dispatch_router.ATORES_VALIDOS` (:562). ⛔ `human` NÃO está aqui: escrever esse
#: valor é um INSERT que o Postgres recusa — e a recusa some sem erro.
ATORES_DO_CHECK = ("system", "worker", "user", "agent", "admin", "provider")

_VOCABULARIO: Optional[Dict[str, Any]] = None


def vocabulario() -> Dict[str, Any]:
    """O vocabulário congelado da §5. Cache de módulo: uma leitura por processo.

    ⛔ Nunca levanta: sem o arquivo, devolve `{}` e todo escritor vira no-op — a
    sombra deixa de gravar antes de gravar errado.
    """
    global _VOCABULARIO
    if _VOCABULARIO is None:
        try:
            with io.open(CAMINHO_DO_VOCABULARIO, encoding="utf-8") as arquivo:
                _VOCABULARIO = json.load(arquivo)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[SOMBRA] vocabulário não lido (%s) — a sombra não grava",
                           type(erro).__name__)
            _VOCABULARIO = {}
    return _VOCABULARIO


def _declaracao(event_type: str) -> Optional[Dict[str, Any]]:
    return ((vocabulario().get("eventos") or {}).get(str(event_type)))


def _limite_de_valor() -> int:
    try:
        return int(vocabulario().get("limite_de_valor_em_chars") or 64)
    except Exception:  # noqa: BLE001
        return 64


#: `message_human` por evento. 🔴 Frase FIXA, sem interpolação: é a única forma de
#: garantir que nenhum texto do segurado atravesse para a linha do tempo.
TEMPLATES = {
    "claims.sombra_aberta": "Sombra de sinistro aberta a partir do atendimento.",
    "claims.handoff_pedido": "O robô pediu para entregar o atendimento a uma pessoa.",
    "claims.humano_assumiu": "Uma atendente assumiu o atendimento.",
    "claims.humano_devolveu": "Uma atendente devolveu o atendimento.",
    "claims.humano_respondeu": "Uma atendente respondeu ao segurado.",
    "claims.nota_registrada": "Uma anotação da atendente foi registrada.",
    "claims.documento_recebido": "O segurado enviou um arquivo.",
    # ⛔ `claims.seguradora_respondeu` SAIU na v2 do vocabulário. 📊 03/09/2026: zero
    # escritores nos dois stacks. Um template para um evento que ninguém grava é uma
    # promessa que o leitor do digest passa a procurar (P-093B-SEGURADORA).
    "claims.espera_aberta": "Uma espera foi aberta.",
    "claims.espera_satisfeita": "A espera foi satisfeita.",
    "claims.encerrado": "O atendimento de sinistro foi encerrado.",
}


# ===========================================================================
# BLOCO A ① — A DETECÇÃO. Função PURA: sem banco, sem rede, sem log de texto.
# ===========================================================================
def normalizar(texto: Any) -> str:
    """Minúsculas e sem acento. 🔴 O padrão abaixo é escrito PARA ESTE texto.

    ⚠️ CLAUDE.md §9.4, corolário do dialeto: um padrão medido sobre texto CRU e
    aplicado sobre texto NORMALIZADO é um padrão sobre outra coisa. `colis[ãa]o`
    nunca casaria aqui, porque depois do `unicodedata` não existe `ã` no alvo — por
    isso a alternativa escrita é `colisao`, em ASCII.
    """
    cru = str(texto or "")
    sem_acento = unicodedata.normalize("NFKD", cru)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


#: 🔴 A PALAVRA QUE ABRE SOZINHA — e ela é UMA SÓ.
#:
#: 📊 O red team desta rodada mediu o detector anterior: de 14 frases NÃO-sinistro,
#: **12 abriam sombra**; sobre o acervo, **16,4% de TODAS as conversas** abririam, e
#: **15% das aberturas tinham palavra de VENDA na mesma mensagem**. A causa era a
#: lista de SUBSTANTIVOS (`roubo`, `furto`, `colisao`, `batida`, `acidente`): eles
#: nomeiam o RISCO tanto quanto o EVENTO — e é do risco que se fala ao VENDER seguro.
#:
#: ⚠️ Escrito para o texto JÁ NORMALIZADO (CLAUDE.md §9.4, dialeto): depois do
#: `unicodedata` não existe `ã` no alvo, e `\m…\M` do Postgres é `\b…\b` aqui.
_RE_SINISTRO = re.compile(r"\b(sinistro|sinistros)\b")

#: 🔴 O VERBO DE OCORRÊNCIA — o que separa "aconteceu comigo" de "quero cobertura
#: para isso". ⛔ Substantivo de dano NÃO abre sozinho; quem abre é o verbo.
#:
#: 📊 Cada exclusão tem a frase do red team que a motivou:
#:   "meu pai teve um acidente vascular cerebral" → por isso `tive um acidente`,
#:                                                  e NUNCA `teve` nem `acidente` solto
#:   "por acidente mandei a foto errada"          → `acidente` solto não abre
#:   "a batida do motor esta estranha"            → `batida` solta não abre
#:   "que roubo esse preco do seguro"             → `roubo` solto não abre
#:   "quanto custa a cobertura de colisao?"       → `colisao` solta não abre
#:
#: ⚠️ `pegou fogo` fica FORA do grupo com `\b(…)\b` de propósito: o `\b` final cairia
#: no meio da expressão de duas palavras. Ele é alternativa própria.
_RE_OCORRENCIA = re.compile(
    r"\b("
    r"colidi|colidiu|colidimos|colidiram"
    r"|roubaram|furtaram|levaram"
    r"|capotei|capotou|capotamos"
    r"|arrombaram"
    r"|abalroa\w*"
    r"|sofri"
    r"|tive um acidente"
    r"|fui assaltad\w*"
    r"|foi (?:roubad|furtad|batid|abalroad|arrombad)\w*"
    r"|aconteceu um acidente"
    r"|bateram no meu"
    r")\b|pegou fogo"
)

#: 🔴 O VERBO DE ABERTURA — "abrir/acionar/comunicar/registrar/dar entrada" + sinistro.
#: 📊 Juiz de confirmação, 03/09: "abri um sinistro e queria saber o preço da franquia" era
#: vetado pela tranca de venda. Quem já abriu, ou quer abrir, não está cotando.
_RE_ABERTURA = re.compile(r"\b(abr[iu]\w*|acion\w+|comunic\w+|registr\w+|dar entrada|aviso de)\b")

#: 🔴 A PALAVRA DE VENDA — a tranca que vale sobre TODAS as outras regras.
#:
#: 📊 "quero fazer uma cotação de sinistro" contém a palavra mais forte do detector
#: E é uma venda. Sem esta tranca, o corretor que orça abre sombra de sinistro.
#:
#: ⚠️ `[çc]` e `[ãa]` casam o texto normalizado E o cru — o MESMO padrão serve aos
#: dois dialetos, que é o que a §9.4 manda provar antes de confiar num padrão.
_RE_VENDA = re.compile(
    r"cota[çc][ãa]o|cotar|or[çc]amento|contratar|pre[çc]o|quanto custa"
    r"|cobertura|proposta|simula[çc][ãa]o"
)

#: 🔴 A REGRA DE PAR de `bati` — e por que ela é MAIS ESTRITA que as outras.
#:
#: 📊 `bat*` é o verbo mais ambíguo do atendimento ("bati um papo", "bati a meta").
#: A frase do red team que fechou a porta foi *"bati na porta do carro dele pra
#: chamar"*: ela tem o verbo E o alvo veicular, e não é sinistro nenhum — por isso
#: `porta` e `chamar` EXCLUEM.
#:
#: ⚠️ A fixture `FRASE_SINISTRO` do guarda ("bati o carro e preciso de guincho")
#: abre por AQUI — é o par, e nunca a lista de substantivos, que a faz abrir.
_RE_BATIDA = re.compile(r"\bbat(?:i|eu|emos|eram|endo)\b")
_RE_ALVO_VEICULAR = re.compile(r"\b(carro|moto|veiculo|caminhao|van)\b")
_RE_PORTA = re.compile(r"\b(porta|chamar)\b")

CONFIANCA_ALTA = "alta"
CONFIANCA_MEDIA = "media"
MOTIVO_FICHA = "servico_sinistro"
MOTIVO_REGEX = "regex_segurado"
MOTIVO_OCORRENCIA = "regex_ocorrencia"


def tem_palavra_de_venda(texto: Any) -> bool:
    """A mensagem fala em COMPRAR seguro? ⛔ Vence qualquer outra regra do detector.

    Pública e pura de propósito: é a metade do detector que o red team mediu, e um
    guarda precisa poder chamá-la sozinha.
    """
    return bool(_RE_VENDA.search(normalizar(texto)))


def _bati_com_alvo(alvo: str) -> bool:
    """`bat*` + alvo veicular, e sem `porta`/`chamar` na mesma mensagem."""
    if not _RE_BATIDA.search(alvo):
        return False
    if _RE_PORTA.search(alvo):
        return False
    return bool(_RE_ALVO_VEICULAR.search(alvo))


def detectar_sinistro(texto: Any,
                      ficha: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, Optional[str], Optional[str]]:
    """`(abre, confianca, motivo_enum)` — pura, e o motivo é QUAL REGRA casou.

    🔴 O motivo nunca é a frase. É o enum do vocabulário, e é ele que entra no
    `input_payload` da sombra (SPEC-093-B §2, BLOCO A ⑥).

    As três regras, nesta ordem:

    (a) `ficha_atendimento` com `servico == 'sinistro'`  → ALTA  · `servico_sinistro`
    (b) a palavra `sinistro` no texto do segurado        → MÉDIA · `regex_segurado`
    (c) um VERBO DE OCORRÊNCIA no texto do segurado      → MÉDIA · `regex_ocorrencia`

    ⛔ E a tranca sobre (b) e (c): **palavra de VENDA na mesma mensagem fecha a
    porta**. 📊 15% das aberturas medidas pelo red team tinham uma.

    ⚠️ A ficha (a) NÃO passa pela tranca de venda: ela é a declaração do próprio
    atendimento de que o serviço é sinistro, e vale mais que a redação da mensagem.

    ⛔ `infer_ramo_servico` NÃO é chamado: rodar o classificador do atendimento fora
    do atendimento mudaria a conduta, e esta SPEC é C0 (observa).
    """
    servico = ""
    if isinstance(ficha, dict):
        bruto = ficha.get("servico")
        if bruto is None and isinstance(ficha.get("ficha_atendimento"), dict):
            bruto = (ficha.get("ficha_atendimento") or {}).get("servico")
        servico = normalizar(bruto).strip()

    if servico == "sinistro":
        return True, CONFIANCA_ALTA, MOTIVO_FICHA

    alvo = normalizar(texto)
    if not alvo.strip():
        return False, None, None

    # 🔴 A ORDEM decide o recall. Juiz de confirmação (03/09/2026): com a tranca de
    # venda ANTES de tudo, "bati o carro, minha apólice tem cobertura?" não abria —
    # 📊 488 de 3.786 mensagens com `sinistro` carregam palavra de venda na mesma
    # frase (~9,5% das sessões). Um VERBO DE OCORRÊNCIA em 1ª pessoa é evidência
    # mais forte do que a palavra "cobertura" ao lado: ele vence a tranca.
    if _RE_OCORRENCIA.search(alvo) or _bati_com_alvo(alvo):
        return True, CONFIANCA_MEDIA, MOTIVO_OCORRENCIA

    if _RE_SINISTRO.search(alvo):
        # "quero fazer uma cotação de sinistro" é venda; "abri um sinistro e queria
        # saber o preço da franquia" é sinistro. O que separa é o verbo de ABERTURA.
        if _RE_VENDA.search(alvo) and not _RE_ABERTURA.search(alvo):
            return False, None, None
        return True, CONFIANCA_MEDIA, MOTIVO_REGEX
    return False, None, None


#: 🔴 A FORMA DE UM PROTOCOLO — seis dígitos ou mais, e o Python diz o MESMO que o Next.
#:
#: 📊 O red team achou dois `tem_numero` com significados diferentes gravados na mesma
#: coluna: o Next usa `/\d{6,}/` (`lib/atendimento/claims-shadow.ts`,
#: `anotacaoTemNumero`) e o Python usava `\d` — QUALQUER dígito. "vou ligar às 9h"
#: virava `tem_numero=true` no lado Python e `false` no lado Next, e o digest somava
#: os dois como se fossem o mesmo fato.
#:
#: ⛔ Um booleano com dois significados é pior que um booleano ausente: ele responde,
#: e responde a pergunta errada (CLAUDE.md §12.1).
_RE_NUMERO_DE_PROTOCOLO = re.compile(r"\d{6,}")


def tem_numero(texto: Any) -> bool:
    """A anotação traz um NÚMERO DE PROTOCOLO? ⛔ Não "traz algum dígito".

    🔴 Pura, pública e com a mesma regra do `anotacaoTemNumero` do Next. Um dos dois
    lados escrevendo `\\d` e o outro `\\d{6,}` é duas colunas com um nome só.

    ⚠️ O booleano é tudo o que entra no ledger. O número em si fica no Espelho, que é
    onde texto de conversa mora — `payload_redacted` tem esse nome por um motivo.
    """
    return bool(_RE_NUMERO_DE_PROTOCOLO.search(str(texto or "")))


# ---------------------------------------------------------------------------
# O TIPO DO ARQUIVO — enum, nunca o conteúdo
# ---------------------------------------------------------------------------
#: `_detect_document_type` (📊 `attendance_media.py:242`) devolve o vocabulário DELE.
#: Esta tabela o traduz para o vocabulário da sombra; o que não traduz vira
#: `desconhecido`, que é a verdade, e não `outro`, que seria um palpite.
_DE_ATTENDANCE_MEDIA = {
    "claim_report": "boletim_ocorrencia",
    "identity_document": "cnh",
    "invoice_or_receipt": "orcamento",
    "policy_document": "outro",
    "property_document": "outro",
    "general_attachment": "desconhecido",
}


def tipo_de_documento(pista: Any) -> str:
    """O enum `tipo_documento` a partir da legenda/descrição — nunca do arquivo.

    ⛔ Devolve sempre um valor do enum. Sem pista utilizável, `desconhecido`.
    """
    bruto = str(pista or "").strip()
    if not bruto:
        return "desconhecido"
    try:
        from app.api.attendance_media import _detect_document_type
    except Exception:  # noqa: BLE001
        return "desconhecido"
    try:
        return _DE_ATTENDANCE_MEDIA.get(_detect_document_type(bruto), "desconhecido")
    except Exception:  # noqa: BLE001
        return "desconhecido"


# ===========================================================================
# A CAMADA DE I/O — nada aqui levanta exceção para o atendimento
# ===========================================================================
def _cliente(db: Any) -> Any:
    return getattr(db, "client", db)


async def _executar(fabrica) -> Any:
    """Dispara a consulta e devolve a resposta, sirva ela cliente síncrono ou async.

    📊 Os dois estilos existem no código vivo: `webhook.py` usa
    `asyncio.to_thread(lambda: …execute())` (o cliente do Supabase é síncrono) e o
    `dispatch_router` faz `await …execute()`. Uma versão só, em vez de duas — que é
    o que este helper existe para impedir.
    """
    resposta = await asyncio.to_thread(fabrica)
    if inspect.isawaitable(resposta):
        resposta = await resposta
    return resposta


#: 🔴 A MEMÓRIA DE PROCESSO, e por que ela é POR CLIENTE e não global.
#:
#: A idempotência da sombra tem DUAS camadas, e elas pegam coisas diferentes:
#:   · no banco, o par `(company_id, idempotency_key)` — é ela que vale entre
#:     processos, e quem a aplica é `criar_registro_sem_fila`;
#:   · aqui, a lembrança de qual conversa já tem sombra NESTE cliente — ela poupa
#:     um SELECT por mensagem no caminho quente do webhook.
#:
#: ⚠️ A chave é o CLIENTE, nunca `(empresa, conversa)` num dicionário global: dois
#: clientes são dois bancos, e uma memória global faria a segunda conexão herdar a
#: verdade da primeira. `WeakKeyDictionary` para que fechar o cliente esvazie a
#: memória sozinho.
#:
#: 🔴 E ELA LEMBRA A AUSÊNCIA — foi o buraco que o red team mediu.
#:
#: 📊 A memória só guardava sombra ENCONTRADA. O caso comum é o contrário: a conversa
#: que **não** é de sinistro nunca entrava na memória, então cada mensagem dela
#: repetia o mesmo SELECT em `work_runs` — no caminho quente do webhook, uma consulta
#: por mensagem para receber sempre a mesma resposta vazia. `None` guardado significa
#: *"perguntei, não existe"*; chave ausente significa *"nunca perguntei"*, e as duas
#: coisas precisavam ser distinguíveis.
#:
#: 🔴 E LEMBRAR SEM TETO É VAZAR. Um processo de webhook vive dias e vê dezenas de
#: milhares de conversas; um `dict` que só cresce é `weakref` nenhum resolve, porque
#: quem segura a memória é o CLIENTE, que também vive para sempre. `OrderedDict` com
#: teto, descartando o mais VELHO (FIFO): a conversa de ontem não é a que vai chegar
#: no próximo webhook.
TETO_DA_MEMORIA = 5000

_MEMORIA: "weakref.WeakKeyDictionary[Any, Any]" = weakref.WeakKeyDictionary()
_MEMORIA_DA_FICHA: "weakref.WeakKeyDictionary[Any, Any]" = weakref.WeakKeyDictionary()


def _memoria(qual: Any, cli: Any) -> Optional[Any]:
    """A tabelinha deste cliente, ou `None` quando o cliente não aceita `weakref`."""
    try:
        lembrada = qual.get(cli)
        if lembrada is None:
            lembrada = OrderedDict()
            qual[cli] = lembrada
        return lembrada
    except TypeError:      # cliente sem weakref: segue sem memória, só com o banco
        return None


def _memoria_do_cliente(cli: Any) -> Optional[Any]:
    return _memoria(_MEMORIA, cli)


def _lembrar(lembrada: Optional[Any], chave: Any, valor: Any) -> None:
    """Guarda com teto FIFO. ⛔ Nunca levanta: memória é otimização, não contrato."""
    if lembrada is None:
        return
    try:
        lembrada.pop(chave, None)
        lembrada[chave] = valor
        while len(lembrada) > TETO_DA_MEMORIA:
            lembrada.popitem(last=False)      # o mais VELHO sai primeiro
    except Exception:  # noqa: BLE001
        pass


async def sombra_da_conversa(db: Any, company_id: Any,
                             conversation_id: Any) -> Optional[str]:
    """O `work_run_id` da sombra desta conversa, ou `None`. 🔴 Sempre com `company_id`.

    ⛔ Sem `company_id` no filtro, o SELECT devolveria a sombra da outra corretora —
    o backend roda com service role e a RLS não segura nada (CLAUDE.md §7).

    ⚠️ A resposta NEGATIVA também é lembrada (ver `_MEMORIA`): a conversa que não é
    de sinistro é a maioria, e era ela que pagava um SELECT por mensagem.
    """
    empresa = str(company_id or "").strip()
    conversa = str(conversation_id or "").strip()
    if not empresa or not conversa:
        return None

    # 🔴 `_cliente` DENTRO do try: `getattr(db, "client")` é um atributo qualquer, e
    # num cliente que abre conexão preguiçosa ele LEVANTA. Fora do try, a sombra
    # derrubaria o atendimento pela única linha que ela jurou nunca derrubar.
    try:
        cli = _cliente(db)
        lembrada = _memoria_do_cliente(cli)
        if lembrada is not None and (empresa, conversa) in lembrada:
            return lembrada[(empresa, conversa)]

        resposta = await _executar(
            lambda: cli.table("work_runs").select("id")
            .eq("company_id", empresa)                 # 🔴 §7
            .eq("conversation_id", conversa)
            .eq("workflow_key", WORKFLOW_KEY)
            .limit(1).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[SOMBRA] não consultei a sombra (%s)", type(erro).__name__)
        return None

    linhas = getattr(resposta, "data", None) or []
    run_id = str((linhas[0] or {}).get("id") or "") if linhas else ""
    # ⚠️ `None` guardado é "perguntei e não existe" — e é o que poupa o SELECT
    # repetido. ⛔ Falha de consulta NÃO é lembrada: ela sai pelo `except` acima,
    # antes daqui, porque lembrar um erro como se fosse resposta é a pior das duas.
    _lembrar(_memoria_do_cliente(cli), (empresa, conversa), run_id or None)
    return run_id or None


async def ficha_da_conversa(db: Any, company_id: Any,
                            conversation_id: Any) -> Optional[Dict[str, Any]]:
    """A `ficha_atendimento` da conversa, ou `None`. ⛔ UMA consulta indexada, e a
    ausência fica lembrada.

    🔴 Mora aqui, e não no `webhook.py`, por dois motivos. O primeiro é §5: a leitura
    é do detector, e detector é isto. O segundo é medido — 📊 §1.2 da SPEC: a ficha
    tem conteúdo em **1 de 679** conversas, porque o grafo não roda em produção. Ou
    seja: 678 de 679 mensagens pagavam um SELECT para receber `None`, e pagavam de
    novo na mensagem seguinte. A ausência lembrada é o conserto.

    ⚠️ Lembrar a ausência tem um custo aceito e escrito: se o grafo voltar a gravar
    ficha no meio de uma conversa, este processo continuará vendo a ausência até o
    teto FIFO descartar a entrada. Aceitável porque a sombra abre UMA vez por
    conversa, e a confiança é decidida na abertura.
    """
    empresa = str(company_id or "").strip()
    conversa = str(conversation_id or "").strip()
    if not empresa or not conversa:
        return None
    try:
        cli = _cliente(db)
        lembrada = _memoria(_MEMORIA_DA_FICHA, cli)
        if lembrada is not None and (empresa, conversa) in lembrada:
            return lembrada[(empresa, conversa)]

        resposta = await _executar(
            lambda: cli.table("conversations").select("ficha_atendimento")
            .eq("company_id", empresa)                 # 🔴 §7
            .eq("id", conversa)
            .limit(1).execute())
    except Exception as erro:  # noqa: BLE001
        logger.debug("[SOMBRA] ficha não lida (%s)", type(erro).__name__)
        return None

    linhas = getattr(resposta, "data", None) or []
    ficha = (linhas[0] or {}).get("ficha_atendimento") if linhas else None
    if not isinstance(ficha, dict):
        ficha = None
    _lembrar(_memoria(_MEMORIA_DA_FICHA, cli), (empresa, conversa), ficha)
    return ficha


async def abrir_sombra(db: Any, *, company_id: Any, conversation_id: Any,
                       confianca: str = CONFIANCA_MEDIA,
                       motivo: str = MOTIVO_REGEX,
                       ramo: Optional[str] = None,
                       seguradora_slug: Optional[str] = None) -> Optional[str]:
    """Abre UMA sombra por conversa e devolve o `work_run_id`. Nunca levanta.

    🔴 **Não** por `WorkRunService.criar` nem pelo RPC `work_run_create`: 📊 nenhum
    dos dois aceita `conversation_id`, e o RPC enfileira no outbox — o Smith worker
    pegaria um run sem handler e o marcaria `failed`. O caminho é o helper
    compartilhado `criar_registro_sem_fila`, o mesmo que o acionamento usa
    (consolidar, não duplicar — CLAUDE.md §5).

    🔴 `input_payload` só tem enum e slug. `motivo` é qual regra casou, nunca a frase.
    """
    empresa = str(company_id or "").strip()
    conversa = str(conversation_id or "").strip()
    if not empresa or not conversa:
        return None

    # ⛔ **Só a lembrança POSITIVA vale como atalho aqui.** Desde que `_MEMORIA`
    # guarda também a AUSÊNCIA, um `None` lembrado significa *"não havia sombra"* — e
    # ler isso como resposta faria `abrir_sombra` DESISTIR de abrir exatamente na
    # conversa em que o detector acabou de dizer que é sinistro. O `sombra_da_conversa`
    # que roda dentro de `criar_registro_sem_fila`/idempotência continua sendo a
    # autoridade sobre "já existe".
    try:
        cli = _cliente(db)
        lembrada = _memoria_do_cliente(cli)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[SOMBRA] cliente indisponível (%s)", type(erro).__name__)
        return None
    if lembrada is not None and lembrada.get((empresa, conversa)):
        return lembrada[(empresa, conversa)]

    entrada = {
        "confianca": str(confianca or CONFIANCA_MEDIA),
        "motivo": str(motivo or MOTIVO_REGEX),
        "ramo": str(ramo) if ramo else None,
        "seguradora_slug": str(seguradora_slug) if seguradora_slug else None,
    }
    try:
        from app.services.work.runs import criar_registro_sem_fila

        registro = await criar_registro_sem_fila(
            db,
            company_id=empresa,
            workflow_key=WORKFLOW_KEY,
            outcome_type=OUTCOME_TYPE,
            outcome_title=OUTCOME_TITLE,
            source_type="chat",            # 📊 CHECK ck_work_runs_source; não há "sombra"
            source_id=conversa,
            conversation_id=conversa,
            runtime_kind=RUNTIME_KIND,     # o que distingue o caminho é ESTE campo
            status="running",
            risk_level="low",
            idempotency_key=PREFIXO_DA_CHAVE + conversa,
            input_payload=entrada,
        )
    except Exception as erro:  # noqa: BLE001
        # ⛔ A sombra NUNCA derruba o atendimento (BLOCO A ⑤).
        logger.warning("[SOMBRA] não abri a sombra (%s)", type(erro).__name__)
        return None

    run_id = str((registro or {}).get("id") or "")
    if not run_id:
        return None
    _lembrar(lembrada, (empresa, conversa), run_id)

    if not (registro or {}).get("reused"):
        await registrar_evento(db, company_id=empresa, conversation_id=conversa,
                               event_type="claims.sombra_aberta", payload=entrada,
                               work_run_id=run_id)
        logger.info("[SOMBRA] aberta confianca=%s motivo=%s", entrada["confianca"],
                    entrada["motivo"])
    return run_id


# ---------------------------------------------------------------------------
# BLOCO B — O LEDGER
# ---------------------------------------------------------------------------
#: 🔴 A FORMA DE SLUG — a MESMA do TS (`claims-shadow.ts`, `FORMA_DE_SLUG`), e agora
#: declarada no vocabulário (`forma_de_slug`), que é o único arquivo que os dois leem.
#:
#: 📊 O red team achou o buraco: o TS validava enum, inteiro, booleano e slug; o
#: Python só media o TAMANHO. `"o cliente bateu o carro"` tem 23 chars e passava pelo
#: lado Python — o mesmo payload que o lado Next recusa. Duas regras para uma coluna.
_FORMA_DE_SLUG_PADRAO = r"[a-z0-9][a-z0-9_.-]*"

#: 📊 O CHECK de `work_events.severity`. Um valor fora dele é um INSERT recusado que
#: some sem erro — o mesmo defeito de `actor_type='human'`, na coluna do lado.
SEVERIDADES = ("debug", "info", "warning", "error", "critical")

#: Quando um valor é descartado, POR QUÊ. Só `enum` sobe a severidade do evento: um
#: valor fora do enum é um escritor errado, e isso precisa aparecer.
RECUSA_ENUM = "enum"
RECUSA_FORMA = "forma"


def _forma_de_slug() -> "re.Pattern[str]":
    bruto = str(vocabulario().get("forma_de_slug") or "").strip()
    # ⚠️ O vocabulário escreve a forma ANCORADA (`^…$`, como o TS); aqui ela é usada
    # com `fullmatch`, então as âncoras saem — deixá-las duplicaria a âncora e o
    # padrão passaria a recusar tudo, em silêncio.
    if bruto.startswith("^") and bruto.endswith("$"):
        bruto = bruto[1:-1]
    try:
        return re.compile(bruto or _FORMA_DE_SLUG_PADRAO)
    except re.error:
        return re.compile(_FORMA_DE_SLUG_PADRAO)


def _valor_limpo(chave: str, valor: Any,
                 limite: int) -> Tuple[Optional[Any], str]:
    """`(valor_pronto, recusa)` para o `payload_redacted`. `recusa=""` quando passou.

    As três regras, na ordem, e cada uma pega o que as outras não pegam:

    (a) 🔴 **chave com ENUM no vocabulário** → o valor tem de estar no enum. Fora
        dele, a chave é DESCARTADA e o evento sobe para `severity='warning'`:
        um enum inventado não é um detalhe perdido, é um escritor errado.
    (b) chave sem enum → `bool` e `int` passam; `str` só se casar a FORMA DE SLUG e
        couber no limite.
    (c) o resto é descartado.

    ⚠️ Valor longo é texto disfarçado de enum. Ele é DESCARTADO, não truncado:
    truncar guardaria metade da frase do segurado, que é exatamente o que a §2 proíbe.
    """
    if valor is None:
        return None, RECUSA_FORMA

    enumerado = (vocabulario().get("enums") or {}).get(chave)
    if enumerado:
        # ⛔ `str(valor)` e não `isinstance(valor, str)`: um enum que chega como
        # número ainda pode estar certo, e recusá-lo pelo TIPO esconderia o acerto.
        texto = valor if isinstance(valor, str) else str(valor)
        return (texto, "") if texto in tuple(enumerado) else (None, RECUSA_ENUM)

    if chave in tuple(vocabulario().get("inteiros") or ("dias",)):
        # ⛔ `bool` é subclasse de `int` em Python: sem esta linha, `True` viraria `1`
        # num campo declarado inteiro, e o digest somaria booleanos.
        if isinstance(valor, bool):
            return None, RECUSA_FORMA
        try:
            # 🔴 CLAMP EM ZERO. `dias` é uma DURAÇÃO, e duração negativa não existe.
            # 📊 `o_fim_do_atendimento._dias_entre` calcula `satisfeito_em - created_at`
            # com dois relógios que podem discordar: um `-1` gravado aqui viraria uma
            # média negativa no digest, e "a seguradora respondeu antes de ser
            # perguntada" é um número que ninguém sabe ler.
            return max(0, int(valor)), ""
        except Exception:  # noqa: BLE001
            return None, RECUSA_FORMA

    if isinstance(valor, bool):
        return valor, ""
    if isinstance(valor, int):
        return valor, ""

    if not isinstance(valor, str):
        # ⛔ `float`, `list`, `dict` não têm forma declarada. Antes o `float` passava
        # por ser `(int, float)`, e um `dict` virava `str(dict)` — texto livre com
        # chaves, exatamente o que a §2 proíbe.
        return None, RECUSA_FORMA
    if not valor or len(valor) > limite:
        return None, RECUSA_FORMA
    if not _forma_de_slug().fullmatch(valor):
        return None, RECUSA_FORMA
    return valor, ""


async def registrar_evento(db: Any, *, company_id: Any, conversation_id: Any = None,
                           event_type: str, payload: Optional[Dict[str, Any]] = None,
                           actor_type: Optional[str] = None,
                           severity: str = "info",
                           work_run_id: Optional[str] = None) -> bool:
    """Grava UMA linha em `work_events` para um gesto da sombra. Nunca levanta.

    🔴 **Evento fora do vocabulário não grava** — e loga. Um `event_type` inventado
    entraria no banco sem ninguém saber ler, e o digest o contaria como variante.

    🔴 **Sem sombra na conversa, não escreve.** Nada de sombra retroativa nesta SPEC
    (BLOCO B ③): o gesto de uma conversa que nunca foi de sinistro não vira rastro.

    🔴 O `actor_type` sai do VOCABULÁRIO, **SEMPRE**, e nunca de quem chama: 📊 o
    CHECK do banco recusa qualquer outro valor e `_evento` engole a recusa
    (`dispatch_router.py:578`) — um ator errado vira um evento que nunca aconteceu,
    sem erro nenhum. ⚠️ Antes o parâmetro `actor_type` VENCIA o vocabulário quando
    estivesse no CHECK: um chamador podia gravar `claims.humano_assumiu` com
    `actor_type='system'`, e a linha do tempo passava a dizer que a máquina assumiu
    o caso. O parâmetro continua na assinatura (compatibilidade) e é IGNORADO — com
    log, porque um `except` mudo é uma flag que mente com outro nome.
    """
    decl = _declaracao(event_type)
    if not decl:
        logger.warning("[SOMBRA] evento '%s' fora do vocabulário — nada gravado",
                       str(event_type)[:60])
        return False

    empresa = str(company_id or "").strip()
    if not empresa:
        return False

    ator = str(decl.get("ator") or "")
    if ator not in ATORES_DO_CHECK:
        logger.warning("[SOMBRA] ator %r de '%s' fora do CHECK — nada gravado",
                       ator, str(event_type)[:60])
        return False
    if actor_type and str(actor_type) != ator:
        logger.info("[SOMBRA] actor_type=%r ignorado: '%s' é do ator %r pelo vocabulário",
                    str(actor_type)[:20], str(event_type)[:60], ator)

    run_id = str(work_run_id or "").strip()
    if not run_id:
        run_id = str(await sombra_da_conversa(db, empresa, conversation_id) or "")
    if not run_id:
        return False

    declaradas = tuple(decl.get("payload") or ())
    bruto = {k: v for k, v in (payload or {}).items()
             if k in declaradas and v is not None}

    # 🔴 `severity` também é CHECK do banco. Um valor fora dele é o mesmo INSERT
    # recusado em silêncio do `actor_type` — e o chamador acha que gravou.
    gravidade = str(severity or "info")
    if gravidade not in SEVERIDADES:
        logger.warning("[SOMBRA] severity %r fora de %s — usando 'info'",
                       gravidade[:20], SEVERIDADES)
        gravidade = "info"
    # 🔴 O REDATOR CANÔNICO ANTES DA COERÇÃO, e a ordem importa.
    # 📊 `contem_pii` recebe `str` (`redaction_service.py:264`); passar dict é
    # `TypeError`. E rodá-lo DEPOIS de coagir `tem_numero` para bool esconderia um
    # CPF por acidente de tipo, em vez de recusá-lo por regra.
    try:
        from app.services.intelligence.redaction_service import contem_pii

        sujo = bool(contem_pii(json.dumps(bruto, ensure_ascii=False, default=str)))
    except Exception:  # noqa: BLE001
        sujo = False

    if sujo:
        # A sombra prefere perder detalhe a vazar (SPEC-093-B BLOCO B).
        redigido: Dict[str, Any] = {}
        gravidade = "warning"
        logger.warning("[SOMBRA] payload de '%s' acusado pelo redator — gravado vazio",
                       event_type)
    else:
        limite = _limite_de_valor()
        redigido = {}
        fora_do_enum = []
        for chave in declaradas:
            if chave not in bruto:
                continue
            valor, recusa = _valor_limpo(chave, bruto[chave], limite)
            if recusa == RECUSA_ENUM:
                fora_do_enum.append(chave)
            elif valor is not None:
                redigido[chave] = valor
        if fora_do_enum:
            # ⚠️ A chave some do payload E o evento sobe para `warning`. Descartar em
            # silêncio deixaria o digest agrupando por uma chave ausente sem que
            # ninguém soubesse que um escritor está mandando enum inventado.
            gravidade = "warning"
            logger.warning("[SOMBRA] '%s': %s fora do enum — chave(s) descartada(s)",
                           event_type, sorted(fora_do_enum))

    linha = {
        "company_id": empresa,                      # 🔴 §7
        "work_run_id": run_id,
        "event_type": str(event_type),
        "actor_type": ator,
        "severity": gravidade,
        "message_human": TEMPLATES.get(str(event_type), OUTCOME_TITLE),
        "payload_redacted": redigido,
    }
    try:
        # 🔴 `_cliente` DENTRO do try, como nas outras duas funções de I/O: um
        # `db.client` que levanta derrubaria o atendimento pela linha que menos
        # importa dele (BLOCO A ⑤).
        cli = _cliente(db)
        await _executar(lambda: cli.table("work_events").insert(linha).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[SOMBRA] evento '%s' não registrado (%s)",
                       event_type, type(erro).__name__)
        return False
    return True


async def registrar_gesto(db: Any, *, company_id: Any, conversation_id: Any,
                          event_type: str,
                          payload: Optional[Dict[str, Any]] = None) -> bool:
    """`registrar_evento` embrulhado para os pontos de chamada do atendimento.

    ⛔ Existe para que nenhum chamador precise de `try/except` próprio: os gestos do
    BLOCO B moram dentro de funções que NÃO podem cair por causa do rastro.
    """
    try:
        return await registrar_evento(db, company_id=company_id,
                                      conversation_id=conversation_id,
                                      event_type=event_type, payload=payload)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[SOMBRA] gesto '%s' não registrado (%s)",
                       str(event_type)[:60], type(erro).__name__)
        return False


# ===========================================================================
# AS FUNÇÕES PURAS DE AGRUPAMENTO — a matéria-prima do digest (BLOCO C)
# ===========================================================================
#
# ⚠️ Elas moram AQUI, e não em `intelligence/workflows.py`, por dois motivos
# medidos: o guarda (`test_o_sinistro_deixa_rastro.py:169-175`) as importa deste
# módulo num único `from … import`, e são puras — não tocam banco, não têm nada do
# runtime de workflow. O BLOCO C as importa daqui em vez de reescrevê-las
# (CLAUDE.md §5: consolidar, não duplicar).
def assinatura_da_variante(eventos: Iterable[str]) -> str:
    """A assinatura ORDENADA de uma trajetória (referência ② Celonis).

    🔴 `sha256` e não `hash()`: o `hash()` de `str` é salgado por processo, então a
    mesma trajetória daria chaves diferentes a cada reinício — e o dedupe do sinal
    duplicaria o sinal toda vez que o worker subisse.

    ⛔ **A ordem faz a variante.** Ordenar a sequência aqui apagaria a diferença
    entre "o humano assumiu e então o documento chegou" e o contrário, que são dois
    processos diferentes.
    """
    corrente = "|".join(str(e) for e in (eventos or ()))
    return hashlib.sha256(corrente.encode("utf-8")).hexdigest()[:32]


def variantes_de(trajetorias: Iterable[Dict[str, Any]],
                 limiar: int = 3) -> List[Dict[str, Any]]:
    """Agrupa trajetórias em variantes por `(corretora, ramo, seguradora, sequência)`.

    Só as variantes com `N >= limiar` saem — abaixo dele não há sinal, há anedota.
    """
    grupos: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for trajetoria in (trajetorias or ()):
        if not isinstance(trajetoria, dict):
            continue
        eventos = list(trajetoria.get("eventos") or ())
        if not eventos:
            continue
        empresa = str(trajetoria.get("company_id") or "")
        ramo = str(trajetoria.get("ramo") or "desconhecido")
        seguradora = str(trajetoria.get("seguradora_slug") or "desconhecida")
        assinatura = assinatura_da_variante(eventos)
        chave = (empresa, ramo, seguradora, assinatura)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                "assinatura": assinatura,
                "company_id": empresa,
                "ramo": ramo,
                "seguradora_slug": seguradora,
                "eventos": eventos,
                "n": 0,
                "work_run_ids": [],
                "dedupe_key": "claims_shadow:%s:%s:%s:%s" % (
                    empresa, ramo, seguradora, assinatura),
            }
        grupo["n"] += 1
        run_id = str(trajetoria.get("work_run_id") or "")
        if run_id:
            grupo["work_run_ids"].append(run_id)

    minimo = int(limiar or 1)
    fora = [g for g in grupos.values() if g["n"] >= minimo]
    fora.sort(key=lambda g: (-g["n"], g["assinatura"]))
    return fora


#: O `kind` de espera que a CNSP 496/2026 rege — e o único que o contador de
#: seguradora tem o direito de contar.
KIND_SEGURADORA = "esperando_seguradora"

#: 🔴 O que entra em `nao_instrumentado` quando não há NENHUMA espera de seguradora
#: no corpus. ⚠️ Estes são NOMES DE MEDIÇÃO, não de contador: o mesmo par apaga o
#: número da espera e o do prazo, porque o prazo se calcula a partir da espera.
NAO_INSTRUMENTADO_SEGURADORA = ("espera_seguradora", "prazos")


#: Os cinco motivos pelos quais pilotos de claims travam (referência ⑤ Sprout.ai),
#: virados em contador. ⚠️ Cada um só é citável ao lado de `total` — número sem
#: denominador não é fato (CLAUDE.md §12.1).
def contadores_de(trajetorias: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Os cinco contadores da referência ⑤, com o denominador junto.

    🔴 **O CONTADOR DE SEGURADORA NÃO CONTA ESPERA DE CLIENTE.**

    📊 O red team mediu o defeito: o contador se chamava
    `espera_de_seguradora_sem_retorno` e olhava só para os `event_type`
    (`claims.espera_aberta` sem `claims.espera_satisfeita`). Mas o `kind` da espera
    mora no PAYLOAD, e os três kinds existentes são `esperando_cliente`,
    `esperando_seguradora` e `esperando_humano`. Uma conversa esperando o SEGURADO
    mandar a foto era contada como seguradora que não respondeu — e é esse o número
    que o Founder leria como "a seguradora está travando meus casos".

    🔴 **E ZERO MEDIDO NÃO É ZERO.** 📊 Em 03/09/2026, `esperando_seguradora` tem
    ZERO escritores no código vivo (P-093B-SEGURADORA). Sem nenhuma espera desse
    kind no corpus, o contador sai `None` e `nao_instrumentado` diz o porquê — em
    vez de um `0/N` que se lê como "nenhum caso travou na seguradora" quando a
    verdade é "ninguém mediu" (SPEC-088 §4).
    """
    lista = [t for t in (trajetorias or ()) if isinstance(t, dict)]
    total = len(lista)
    contas: Dict[str, Any] = {
        "total": total,
        "sem_documento": 0,
        "espera_de_seguradora_sem_retorno": 0,
        "com_nota_da_atendente": 0,
        "com_retomada_do_humano": 0,
        "encerrados_sem_desfecho": 0,
        "nao_instrumentado": [],
    }
    viu_espera_de_seguradora = False
    for trajetoria in lista:
        eventos = [str(e) for e in (trajetoria.get("eventos") or ())]
        desfechos = trajetoria.get("desfechos") or ()
        if "claims.documento_recebido" not in eventos:
            contas["sem_documento"] += 1
        # ⛔ A espera com `kind`, e nunca o `event_type` sozinho.
        pendente = False
        for espera in (trajetoria.get("esperas") or ()):
            if not isinstance(espera, dict):
                continue
            if str(espera.get("kind") or "") != KIND_SEGURADORA:
                continue
            viu_espera_de_seguradora = True
            if not espera.get("satisfeita_em") and not espera.get("satisfeito_em"):
                pendente = True
        if pendente:
            contas["espera_de_seguradora_sem_retorno"] += 1
        if "claims.nota_registrada" in eventos:
            contas["com_nota_da_atendente"] += 1
        if "claims.humano_assumiu" in eventos:
            contas["com_retomada_do_humano"] += 1
        # ⚠️ "encerrado sem desfecho" inclui o encerramento que não declarou desfecho
        # nenhum: 📊 é o caso do piloto (a atendente fecha a conversa e ninguém diz
        # como o sinistro terminou). Chamar isso de "desfecho conhecido" por omissão
        # inflaria o contador que mais interessa ao Founder.
        conhecidos = {str(d) for d in desfechos} - {"desconhecido", ""}
        if "claims.encerrado" in eventos and not conhecidos:
            contas["encerrados_sem_desfecho"] += 1

    if not viu_espera_de_seguradora:
        # 🔴 `None`, e NUNCA `0`: o zero seria um número medido onde não houve
        # medição — e é exatamente o que o §12.1 chama de defeito de revisão.
        contas["espera_de_seguradora_sem_retorno"] = None
        contas["prazo_regulatorio"] = None
        contas["nao_instrumentado"] = list(NAO_INSTRUMENTADO_SEGURADORA)
    return contas
