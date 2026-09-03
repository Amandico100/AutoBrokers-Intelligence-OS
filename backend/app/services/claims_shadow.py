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
    "claims.seguradora_respondeu": "A seguradora respondeu.",
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


#: 🔴 O regex ESTRITO da SPEC (§ BLOCO A), traduzido do dialeto do Postgres
#: (`\m…\M`) para o do Python (`\b…\b`) e para o texto JÁ NORMALIZADO.
#: ⛔ `terceiro` NÃO entra: 📊 §1.5 mediu que ele casa fora de contexto
#: ("o terceiro andar"), e o teto de 4.827 linhas veio dele e de `acidente`.
_RE_SINISTRO = re.compile(
    r"\b("
    r"sinistro|sinistros"
    r"|colisao|colidi|colidiu"
    r"|batida"
    r"|roubo|roubaram|roubado|roubada"
    r"|furto|furtaram|furtado|furtada"
    r"|acidente"
    r")\b"
)

#: 🔴 A REGRA DE PAR — e por que ela existe, com o número que a obrigou.
#:
#: 📊 A SPEC escreve o regex estrito acima E, no gate A①, manda a fixture
#: "bati o carro e preciso de guincho" ABRIR sombra. Os dois não podem estar certos:
#: nenhuma alternativa do regex estrito aparece nessa frase. O guarda
#: (`test_o_sinistro_deixa_rastro.py`, bloco [2]) é a prova escrita antes do código,
#: então ele é o contrato — e a frase precisa abrir.
#:
#: ⚠️ `bati` sozinho NÃO entra na lista de cima de propósito ("bati um papo", "bati a
#: meta"). O que abre é o PAR: a batida com um veículo ou um obstáculo por perto.
_RE_BATIDA_COM_ALVO = re.compile(
    r"\bbat(?:i|eu|emos|eram|endo)\b[^.!?\n]{0,40}?"
    r"\b(carro|moto|veiculo|caminhao|carreta|onibus|van|traseira|poste|muro|portao|"
    r"guard-rail|guardrail|arvore|bicicleta)\b"
)
_RE_ALVO_COM_BATIDA = re.compile(
    r"\b(carro|moto|veiculo|caminhao|carreta|onibus|van|bicicleta)\b[^.!?\n]{0,40}?"
    r"\bbat(?:i|eu|emos|eram|endo)\b"
)

CONFIANCA_ALTA = "alta"
CONFIANCA_MEDIA = "media"
MOTIVO_FICHA = "servico_sinistro"
MOTIVO_REGEX = "regex_segurado"


def detectar_sinistro(texto: Any,
                      ficha: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, Optional[str], Optional[str]]:
    """`(abre, confianca, motivo_enum)` — pura, e o motivo é QUAL REGRA casou.

    🔴 O motivo nunca é a frase. É o enum do vocabulário, e é ele que entra no
    `input_payload` da sombra (SPEC-093-B §2, BLOCO A ⑥).

    (a) `ficha_atendimento` já existente com `servico == 'sinistro'` → **ALTA**
    (b) o regex estrito sobre o texto normalizado do SEGURADO → **MÉDIA**

    ⛔ `infer_ramo_servico` NÃO é chamado: rodar o classificador do atendimento fora
    do atendimento mudaria a conduta, e esta SPEC é C0 (observa).
    """
    servico = ""
    if isinstance(ficha, dict):
        bruto = ficha.get("servico")
        if bruto is None and isinstance(ficha.get("ficha_atendimento"), dict):
            bruto = (ficha.get("ficha_atendimento") or {}).get("servico")
        servico = normalizar(bruto).strip()

    alvo = normalizar(texto)
    casou_regex = bool(_RE_SINISTRO.search(alvo)
                       or _RE_BATIDA_COM_ALVO.search(alvo)
                       or _RE_ALVO_COM_BATIDA.search(alvo))

    if servico == "sinistro":
        return True, CONFIANCA_ALTA, MOTIVO_FICHA
    if casou_regex:
        return True, CONFIANCA_MEDIA, MOTIVO_REGEX
    return False, None, None


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
_MEMORIA: "weakref.WeakKeyDictionary[Any, Dict[Tuple[str, str], str]]" = (
    weakref.WeakKeyDictionary())


def _memoria_do_cliente(cli: Any) -> Optional[Dict[Tuple[str, str], str]]:
    try:
        lembrada = _MEMORIA.get(cli)
        if lembrada is None:
            lembrada = {}
            _MEMORIA[cli] = lembrada
        return lembrada
    except TypeError:      # cliente sem weakref: segue sem memória, só com o banco
        return None


async def sombra_da_conversa(db: Any, company_id: Any,
                             conversation_id: Any) -> Optional[str]:
    """O `work_run_id` da sombra desta conversa, ou `None`. 🔴 Sempre com `company_id`.

    ⛔ Sem `company_id` no filtro, o SELECT devolveria a sombra da outra corretora —
    o backend roda com service role e a RLS não segura nada (CLAUDE.md §7).
    """
    empresa = str(company_id or "").strip()
    conversa = str(conversation_id or "").strip()
    if not empresa or not conversa:
        return None

    cli = _cliente(db)
    lembrada = _memoria_do_cliente(cli)
    if lembrada is not None and (empresa, conversa) in lembrada:
        return lembrada[(empresa, conversa)]

    try:
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
    if not linhas:
        return None
    run_id = str((linhas[0] or {}).get("id") or "")
    if not run_id:
        return None
    if lembrada is not None:
        lembrada[(empresa, conversa)] = run_id
    return run_id


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

    cli = _cliente(db)
    lembrada = _memoria_do_cliente(cli)
    if lembrada is not None and (empresa, conversa) in lembrada:
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
    if lembrada is not None:
        lembrada[(empresa, conversa)] = run_id

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
def _valor_limpo(chave: str, valor: Any, limite: int) -> Optional[Any]:
    """Um valor pronto para o `payload_redacted`, ou `None` para descartar a chave.

    ⚠️ Valor longo é texto disfarçado de enum. Ele é DESCARTADO, não truncado:
    truncar guardaria metade da frase do segurado, que é exatamente o que a §2 proíbe.
    """
    if valor is None:
        return None
    if chave in tuple(vocabulario().get("inteiros") or ("dias",)):
        try:
            return int(valor)
        except Exception:  # noqa: BLE001
            return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor
    limpo = str(valor)
    if not limpo or len(limpo) > limite:
        return None
    return limpo


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

    🔴 O `actor_type` sai do VOCABULÁRIO, não de quem chama: 📊 o CHECK do banco
    recusa qualquer outro valor e `_evento` engole a recusa (`dispatch_router.py:578`)
    — um ator errado vira um evento que nunca aconteceu, sem erro nenhum.
    """
    decl = _declaracao(event_type)
    if not decl:
        logger.warning("[SOMBRA] evento '%s' fora do vocabulário — nada gravado",
                       str(event_type)[:60])
        return False

    empresa = str(company_id or "").strip()
    if not empresa:
        return False

    ator = str(actor_type or decl.get("ator") or "system")
    if ator not in ATORES_DO_CHECK:
        ator = str(decl.get("ator") or "system")
    if ator not in ATORES_DO_CHECK:
        ator = "system"

    run_id = str(work_run_id or "").strip()
    if not run_id:
        run_id = str(await sombra_da_conversa(db, empresa, conversation_id) or "")
    if not run_id:
        return False

    declaradas = tuple(decl.get("payload") or ())
    bruto = {k: v for k, v in (payload or {}).items()
             if k in declaradas and v is not None}

    gravidade = str(severity or "info")
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
        for chave in declaradas:
            if chave not in bruto:
                continue
            valor = _valor_limpo(chave, bruto[chave], limite)
            if valor is not None:
                redigido[chave] = valor

    linha = {
        "company_id": empresa,                      # 🔴 §7
        "work_run_id": run_id,
        "event_type": str(event_type),
        "actor_type": ator,
        "severity": gravidade,
        "message_human": TEMPLATES.get(str(event_type), OUTCOME_TITLE),
        "payload_redacted": redigido,
    }
    cli = _cliente(db)
    try:
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


#: Os cinco motivos pelos quais pilotos de claims travam (referência ⑤ Sprout.ai),
#: virados em contador. ⚠️ Cada um só é citável ao lado de `total` — número sem
#: denominador não é fato (CLAUDE.md §12.1).
def contadores_de(trajetorias: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Os cinco contadores da referência ⑤, com o denominador junto."""
    lista = [t for t in (trajetorias or ()) if isinstance(t, dict)]
    total = len(lista)
    contas = {
        "total": total,
        "sem_documento": 0,
        "espera_de_seguradora_sem_retorno": 0,
        "com_nota_da_atendente": 0,
        "com_retomada_do_humano": 0,
        "encerrados_sem_desfecho": 0,
    }
    for trajetoria in lista:
        eventos = [str(e) for e in (trajetoria.get("eventos") or ())]
        desfechos = trajetoria.get("desfechos") or ()
        if "claims.documento_recebido" not in eventos:
            contas["sem_documento"] += 1
        if ("claims.espera_aberta" in eventos
                and "claims.espera_satisfeita" not in eventos):
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
    return contas
