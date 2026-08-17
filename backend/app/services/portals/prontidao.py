# -*- coding: utf-8 -*-
"""Portal Capability Score — SPEC-075 Bloco L (§21) e Bloco M (§22).

A pergunta
==========
> *"esta journey está pronta para rodar de verdade, no portal de verdade,
> no nome de um cliente de verdade?"*

Hoje essa pergunta é respondida por opinião: alguém rodou uma vez, deu certo, e
a partir daí "funciona". Este módulo troca a opinião por **gates medidos**: cada
`(portal_key, journey_key)` recebe um estado de release, um score de 0 a 100 e —
o que mais importa — uma resposta binária sobre poder ir ao ar.

Este NÃO é o Readiness Engine do lançamento
===========================================
`app/services/control_plane/prontidao.py` responde *"a plataforma/o release/a
corretora/o comercial estão prontos?"* (SPEC-062 §33). Assunto diferente, dono
diferente, fonte diferente. Aqui a pergunta é sobre **capacidade de portal**, e
a fonte é o registry de journeys + os testes + as evidências de canário.

Dois módulos, uma regra herdada — e ela é a mais importante das duas casas:

    o que não foi verificado conta como NÃO pronto, nunca como pronto.

Por isso os sinais são **tri-estado**: `True`, `False` e *ausente*. Ausente não é
`False` benigno: é "ninguém mediu", e um checklist que dá o benefício da dúvida
aprova exatamente aquilo em que não olhou.

Puro por obrigação, não por elegância
=====================================
Sem Supabase, sem rede, sem Playwright, sem I/O no import. Um portão que só pode
ser exercitado com infraestrutura de pé é um portão que ninguém testa — e um
portão não testado é decoração. `avaliar_journey()` é uma função de dois
dicionários para um dicionário; roda em qualquer máquina, em milissegundos.

De onde vêm os sinais
=====================
Deste módulo, de lugar nenhum: quem coleta é o script de report / o teste / a
evidência de canário, e passa o dicionário pronto. Isso é deliberado — se este
módulo fosse buscar os sinais, ele viraria mais um lugar que fala com o banco, e
o cálculo deixaria de ser conferível fora de produção.

📊 O registro tem hoje **14 journeys em 7 portais** (medido em 16/08/2026 com
`len(JOURNEYS)` / `{d.portal_key}` sobre `portal_worker.journeys`). É pouco para
manter uma tabela à mão e é muito para manter uma tabela à mão **certa**: a
matriz do §22 é gerada, e por isso não tem como divergir do código.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# 🔴 Import no topo, e de propósito. Este módulo não tem significado sem o
# registry: sem ele, a alternativa seria devolver uma matriz vazia — um
# documento afirmando que o sistema não sabe fazer nada, publicado com cara de
# verdade. Um `ImportError` alto e cedo é melhor que um documento mentindo
# baixinho. E o import não custa nada: `journeys/__init__` carrega os módulos de
# journey de forma tardia, então nem Playwright nem I/O entram aqui.
from portal_worker.journeys import (
    FORCA_DA_CLASSE,
    MATERIAL_SIDE_EFFECT,
    OPERACOES_CONHECIDAS,
    JourneyDefinition,
    journeys_do_portal,
    matriz_de_capacidades,
)

# --------------------------------------------------------------------------
# §21.1 — estados de release operacional
#
# A escada é ORDENADA e não se pula degrau: uma journey não chega a canário
# read-only sem dry-run verde, e não chega a dry-run sem fixture verde. O que
# cada degrau prova é diferente do que o anterior provou, então saltar um deles
# deixaria um buraco de prova exatamente no lugar em que alguém depois vai
# apontar dizendo "mas passou nos testes".
#
# Nenhuma tabela nova (§21.1): isto é DERIVADO de registry + testes + evidência.
# Se um dia for preciso persistir, é Change Addendum — não improviso de schema.
# --------------------------------------------------------------------------
DRAFT = "DRAFT"
FIXTURE_GREEN = "FIXTURE_GREEN"
DRY_RUN_GREEN = "DRY_RUN_GREEN"
CANARY_READONLY_GREEN = "CANARY_READONLY_GREEN"
CANARY_TRANSACTIONAL_GREEN = "CANARY_TRANSACTIONAL_GREEN"
LIVE_APPROVED = "LIVE_APPROVED"

ESTADOS: Tuple[str, ...] = (
    DRAFT,
    FIXTURE_GREEN,
    DRY_RUN_GREEN,
    CANARY_READONLY_GREEN,
    CANARY_TRANSACTIONAL_GREEN,
    LIVE_APPROVED,
)


def indice_do_estado(estado: Any) -> int:
    """Posição na escada; `-1` para valor que não é estado.

    Serve para comparar ("já passou de dry-run?") sem espalhar listas de string
    por aí. Valor desconhecido devolve `-1`, que é MENOR que `DRAFT` — desconhecido
    nunca vira "adiantado".
    """
    e = str(estado or "").strip()
    return ESTADOS.index(e) if e in ESTADOS else -1


# --------------------------------------------------------------------------
# Os sinais — o vocabulário FECHADO da medição
#
# 🔴 Chave desconhecida é ERRO, não é ignorada. A assimetria é o motivo: um erro
# de digitação num sinal de pontuação faz o score CAIR (direção segura), mas um
# erro de digitação num sinal de blocker faz o blocker sumir — `conta_verifikada`
# lido como ausente vira "não provado"... só que o inverso também acontece na
# vida real, quando alguém "conserta" o typo do lado errado. Vocabulário aberto
# é como uma prova de segurança vira silêncio. Ver `validar_sinais`.
#
# Todos vêm de gates que a SPEC nomeia. Sinal que a SPEC não pede não entra:
# medida inventada é a forma mais rápida de produzir um 100 que não significa
# nada (§21.4).
# --------------------------------------------------------------------------
SINAIS_CONHECIDOS: Dict[str, str] = {
    # fixtures e testes (§21.2 "fixtures + replay", §21.1 "testes")
    "fixtures": "quantas fixtures existem para esta journey (int)",
    "replay_verde": "o replay das fixtures passa",
    "casos_negativos": "quantos casos negativos/erro são exercitados (int)",
    "testes_verdes": "a suíte da journey está verde",
    # percepção (§21.2 "caminho determinístico/API/DOM", §39)
    "caminho_primario": "api | dom | adaptive | vision",
    # isolamento e identidade (§21.3 cross-tenant, conta não verificada)
    "isolamento_tenant_provado": "há teste com dois tenants provando isolamento",
    "conta_verificada": "a conta usada é conferida no login multi-account",
    # efeito e idempotência (§21.2, §21.3)
    "idempotencia_provada": "ação material repetida não duplica efeito",
    "retry_pos_commit_protegido": "não há retry cego depois do ponto de commit",
    # evidência (§21.2 "evidence + redaction", §21.3 fixture com segredo)
    "evidencia_gravada": "a execução grava evidência consultável",
    "evidencia_redigida": "a evidência passa por redação de segredo/PII",
    "fixture_sem_segredo": "as fixtures foram conferidas e não têm segredo",
    # recuperação (§21.2 "recovery/resume")
    "resume_testado": "retomar de onde parou foi exercitado",
    # observabilidade (§21.2, §26.1, §40.1)
    "metricas_emitidas": "a journey emite as métricas mínimas do §26.1",
    "performance_medida": "há medição de duração/custo por (operation, portal)",
    # canário (§21.2 "canário real medido", §21.1)
    "dry_run_verde": "rodou contra o portal real sem confirmar efeito",
    "canario_readonly_verde": "canário read-only real passou",
    "canario_transacional_verde": "canário transacional real, autorizado, passou",
    "ultimo_canario": "data ISO do último canário (str) — só documental",
    # autorização e lançamento (§21.3 autorização inexistente)
    "autorizacao_registrada": "capability + tool_definition + approval existem",
    "aprovacao_de_lancamento": "o Founder aprovou esta journey para live",
}


class SinalDesconhecido(ValueError):
    """Um sinal fora do vocabulário do §21. Ver o 🔴 em `SINAIS_CONHECIDOS`."""


def validar_sinais(sinais: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Devolve os sinais; levanta `SinalDesconhecido` se houver chave estranha.

    Falhar aqui é barulhento e chato, e é para ser: o silêncio alternativo é uma
    prova de segurança que ninguém percebeu que não estava sendo lida.
    """
    s = dict(sinais or {})
    estranhas = sorted(k for k in s if k not in SINAIS_CONHECIDOS)
    if estranhas:
        raise SinalDesconhecido(
            "sinal(is) fora do vocabulario da SPEC-075 §21: "
            + ", ".join(estranhas)
            + ". Sinal novo entra pela SPEC, nunca por chamada."
        )
    return s


def _provado(sinais: Dict[str, Any], chave: str) -> bool:
    """`True` só quando o sinal diz explicitamente que sim.

    Ausente e `False` dão o mesmo resultado — não provado — mas por razões
    diferentes, e a diferença aparece na frase, não no cálculo.
    """
    return sinais.get(chave) is True


def _quantos(sinais: Dict[str, Any], chave: str) -> int:
    try:
        return max(0, int(sinais.get(chave) or 0))
    except (TypeError, ValueError):
        return 0


def _e_material(d: JourneyDefinition) -> bool:
    return str(getattr(d, "effect_class", "")) == MATERIAL_SIDE_EFFECT


def _efeito_conhecido(d: JourneyDefinition) -> bool:
    return str(getattr(d, "effect_class", "")) in FORCA_DA_CLASSE


# --------------------------------------------------------------------------
# §21.3 — hard blockers
#
# 🔴 ISTO É O CORAÇÃO DO MÓDULO. Um blocker NÃO SUBTRAI PONTOS. Ele anula.
#
# Por que subtrair seria errado — três motivos, e cada um sozinho já bastaria:
#
#   1. Subtração implica que as dimensões são FUNGÍVEIS: que 15 pontos de
#      evidência bem redigida compram de volta a possibilidade de vazar dado de
#      uma corretora para outra. Não compram. Ninguém aceitaria a frase "o
#      cross-tenant é possível, mas as fixtures estão ótimas" — e no entanto é
#      exatamente isso que um score de 80 comunicaria.
#
#   2. Subtração coloca "proibido" e "inacabado" na MESMA RÉGUA. Uma journey em
#      DRAFT tem 10 pontos porque falta trabalho; uma journey com blocker de
#      segurança teria 80 porque falta *uma* coisa. Ordenar por score colocaria
#      a perigosa em cima da inofensiva, e a lista viraria uma fila de
#      prioridade que recomenda subir a errada.
#
#   3. Subtração é NEGOCIÁVEL, e é assim que ela morre: no dia em que faltarem
#      3 pontos para a meta, alguém ajusta o peso. Zero não tem peso para
#      ajustar. A única forma de tirar o zero é remover o blocker — que é
#      precisamente o trabalho que a régua deveria estar cobrando.
#
# A lista é FECHADA: são os oito do §21.3. Blocker novo entra pela SPEC. Uma
# régua em que qualquer um acrescenta motivo de reprovação também é uma régua em
# que qualquer um remove.
# --------------------------------------------------------------------------
BLOCKER_CROSS_TENANT = "cross_tenant_possible"
BLOCKER_EFFECT_CLASS_UNKNOWN = "effect_class_unknown"
BLOCKER_IDEMPOTENCY_MISSING = "idempotency_missing"
BLOCKER_SECRET_IN_FIXTURE = "secret_in_fixture"
BLOCKER_ACCOUNT_NOT_VERIFIED = "account_not_verified"
BLOCKER_BLIND_RETRY_AFTER_COMMIT = "blind_retry_after_commit"
BLOCKER_AUTHORIZATION_MISSING = "authorization_missing"
BLOCKER_UNMEASURED_HIGH_RISK = "unmeasured_high_risk_action"

BLOCKERS_CONHECIDOS: Tuple[str, ...] = (
    BLOCKER_CROSS_TENANT,
    BLOCKER_EFFECT_CLASS_UNKNOWN,
    BLOCKER_IDEMPOTENCY_MISSING,
    BLOCKER_SECRET_IN_FIXTURE,
    BLOCKER_ACCOUNT_NOT_VERIFIED,
    BLOCKER_BLIND_RETRY_AFTER_COMMIT,
    BLOCKER_AUTHORIZATION_MISSING,
    BLOCKER_UNMEASURED_HIGH_RISK,
)


def blockers_de(definicao: JourneyDefinition,
                sinais: Dict[str, Any]) -> List[Dict[str, str]]:
    """Os hard blockers do §21.3 presentes nesta journey, em ordem estável.

    Cada item é `{"codigo", "frase"}`. Lista vazia = nenhum impedimento
    conhecido — o que **não** quer dizer "pronta": pronta é `live_eligible`.

    Alguns blockers só fazem sentido em certos contextos, e aplicá-los fora do
    contexto produziria uma acusação falsa (dizer "fixture com segredo" onde não
    existe fixture ensina o leitor a ignorar a coluna):

        idempotência / retry pós-commit / ação de alto risco → só MATERIAL
        conta não verificada                                 → só `requires_account`
        segredo em fixture                                   → só se há fixture
    """
    material = _e_material(definicao)
    fora: List[Dict[str, str]] = []

    if not _provado(sinais, "isolamento_tenant_provado"):
        fora.append({
            "codigo": BLOCKER_CROSS_TENANT,
            "frase": "sem prova de isolamento entre dois tenants reais — "
                     "cross-tenant continua possível ate alguem provar que nao e",
        })

    if not _efeito_conhecido(definicao):
        fora.append({
            "codigo": BLOCKER_EFFECT_CLASS_UNKNOWN,
            "frase": f"effect_class `{getattr(definicao, 'effect_class', '')}` nao "
                     "e um valor conhecido — nao sabemos o que esta journey faz "
                     "no mundo",
        })

    if material and not _provado(sinais, "idempotencia_provada"):
        fora.append({
            "codigo": BLOCKER_IDEMPOTENCY_MISSING,
            "frase": "acao material sem idempotencia provada — a mesma chamada "
                     "duas vezes pode criar dois efeitos no nome do segurado",
        })

    if _quantos(sinais, "fixtures") > 0 and not _provado(sinais, "fixture_sem_segredo"):
        fora.append({
            "codigo": BLOCKER_SECRET_IN_FIXTURE,
            "frase": "as fixtures nao foram conferidas contra segredo — fixture "
                     "vai para o repositorio e o repositorio nao esquece",
        })

    if getattr(definicao, "requires_account", True) and not _provado(sinais, "conta_verificada"):
        fora.append({
            "codigo": BLOCKER_ACCOUNT_NOT_VERIFIED,
            "frase": "a conta usada no login nao e conferida — matriz e filial "
                     "da mesma corretora trocariam de carteira sem ninguem ver",
        })

    if material and not _provado(sinais, "retry_pos_commit_protegido"):
        fora.append({
            "codigo": BLOCKER_BLIND_RETRY_AFTER_COMMIT,
            "frase": "retry cego depois do ponto de commit — repetir uma etapa "
                     "ja efetivada e como se duplica efeito externo",
        })

    if not _provado(sinais, "autorizacao_registrada"):
        fora.append({
            "codigo": BLOCKER_AUTHORIZATION_MISSING,
            "frase": "sem capability/tool_definition/approval registrados — "
                     "executar seria agir sem que ninguem tenha autorizado",
        })

    if material and not _provado(sinais, "canario_transacional_verde"):
        fora.append({
            "codigo": BLOCKER_UNMEASURED_HIGH_RISK,
            "frase": "acao de alto risco nunca medida em canario transacional "
                     "autorizado — fixture verde nao e prova de mundo real",
        })

    return fora


# --------------------------------------------------------------------------
# §21.2 — score 0–100
#
# Os pesos são os da tabela da SPEC, sem tempero. Cada dimensão é TUDO OU NADA:
# a SPEC dá o peso do conjunto e não dá sub-pesos, então repartir "10" em "6 de
# fixture + 4 de replay" seria inventar um número e depois cita-lo como se
# tivesse sido decidido. Meio ponto imaginado hoje é o numero que alguem cita
# como medido daqui a seis meses (CLAUDE.md §12.1).
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Dimensao:
    chave: str
    pontos: int
    titulo: str
    regra: Callable[[JourneyDefinition, Dict[str, Any]], bool]
    falta: str


def _dim_contrato(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Está no registry, com operação de negócio conhecida e contrato versionado.

    Não depende de sinal: é o próprio registro respondendo. Uma journey que só o
    código conhece não pode ser pedida pelo Work OS — ele pergunta por operação
    de negócio, nunca por nome de função.
    """
    return (
        str(getattr(d, "business_operation", "")) in OPERACOES_CONHECIDAS
        and bool(str(getattr(d, "contract_version", "") or "").strip())
        and _efeito_conhecido(d)
    )


def _dim_fixtures(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Existe fixture E o replay dela passa. Fixture que ninguém reexecuta é anexo."""
    return _quantos(s, "fixtures") > 0 and _provado(s, "replay_verde")


def _dim_caminho(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """O caminho primário é determinístico: `api` ou `dom` (§39).

    `adaptive` e `vision` não pontuam aqui — não porque sejam proibidos, mas
    porque são fallback. Uma journey cujo caminho principal é o modelo olhando a
    tela não tem caminho determinístico; tem um palpite bem informado.
    """
    return str(s.get("caminho_primario") or "").strip().lower() in ("api", "dom")


def _dim_negativos(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Erro e recusa foram exercitados. Só caminho feliz não é teste, é demo."""
    return _quantos(s, "casos_negativos") > 0


def _dim_tenant(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Isolamento provado; e, quando o portal pede conta, a conta é conferida."""
    if not _provado(s, "isolamento_tenant_provado"):
        return False
    return _provado(s, "conta_verificada") or not getattr(d, "requires_account", True)


def _dim_efeito(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Classe de efeito conhecida; se material, idempotência e retry protegidos.

    Journey read-only leva os 15 pontos sem provar idempotência — e isso não é
    generosidade: não há efeito para repetir. Exigir prova de algo inexistente
    ensinaria a marcar sinal só para preencher, que é como um checklist deixa de
    medir e passa a ser preenchido.
    """
    if not _efeito_conhecido(d):
        return False
    if not _e_material(d):
        return True
    return _provado(s, "idempotencia_provada") and _provado(s, "retry_pos_commit_protegido")


def _dim_evidencia(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Grava evidência, redige o que é sensível, e a fixture está limpa."""
    limpa = _quantos(s, "fixtures") == 0 or _provado(s, "fixture_sem_segredo")
    return _provado(s, "evidencia_gravada") and _provado(s, "evidencia_redigida") and limpa


def _dim_resume(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Retomada exercitada — obrigatória para material e para quem declara `supports_resume`.

    Journey material que não sabe retomar deixa o pior estado que existe: o
    `maybe_committed` do §26.1 — parou no meio e ninguém sabe se o efeito saiu.
    Por isso `supports_resume=False` numa journey material não isenta: reprova.
    """
    if not (getattr(d, "supports_resume", False) or _e_material(d)):
        return True
    return _provado(s, "resume_testado")


def _dim_observabilidade(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Métricas mínimas do §26.1 e duração/custo medidos (§40.1)."""
    return _provado(s, "metricas_emitidas") and _provado(s, "performance_medida")


def _dim_canario(d: JourneyDefinition, s: Dict[str, Any]) -> bool:
    """Canário real: transacional se a journey é material, read-only se não é.

    Read-only não precisa de canário transacional porque não há transação — e
    exigi-lo empurraria alguém a rodar uma escrita só para preencher a coluna.
    """
    if _e_material(d):
        return _provado(s, "canario_transacional_verde")
    return _provado(s, "canario_readonly_verde")


DIMENSOES: Tuple[Dimensao, ...] = (
    Dimensao("contrato_registry", 10, "contrato + registry", _dim_contrato,
             "a journey nao esta declarada com operacao de negocio e contrato versionado"),
    Dimensao("fixtures_replay", 15, "fixtures + replay", _dim_fixtures,
             "sem fixture com replay verde"),
    Dimensao("caminho_deterministico", 10, "caminho deterministico/API/DOM", _dim_caminho,
             "o caminho primario nao e `api` nem `dom`"),
    Dimensao("casos_negativos", 10, "casos negativos e erros", _dim_negativos,
             "nenhum caso negativo exercitado"),
    Dimensao("tenant_identidade", 10, "tenant/account identity", _dim_tenant,
             "isolamento de tenant ou identidade de conta sem prova"),
    Dimensao("efeito_idempotencia", 15, "side effect + idempotencia", _dim_efeito,
             "efeito material sem idempotencia/retry protegidos"),
    Dimensao("evidencia_redacao", 10, "evidence + redaction", _dim_evidencia,
             "evidencia ausente, nao redigida ou fixture nao conferida"),
    Dimensao("recovery_resume", 5, "recovery/resume", _dim_resume,
             "retomada nao exercitada numa journey que precisa retomar"),
    Dimensao("observabilidade", 5, "observabilidade/performance", _dim_observabilidade,
             "sem metricas minimas ou sem medicao de performance"),
    Dimensao("canario_real", 10, "canario real medido", _dim_canario,
             "nenhum canario real da classe certa foi medido"),
)

# Guarda de soma: a tabela do §21.2 fecha em 100. Se alguém acrescentar uma
# dimensão sem tirar de outra, o "score de 0 a 100" passa a ir a 110 e todo
# número já publicado vira incomparável. Falhar no import é o barato.
#
# É `raise`, não `assert`: `python -O` remove `assert` e a guarda sumiria
# exatamente em produção, que é onde o número errado teria plateia.
_TOTAL = sum(d.pontos for d in DIMENSOES)
if _TOTAL != 100:  # pragma: no cover - guarda de construção
    raise RuntimeError(
        f"os pesos do §21.2 somam {_TOTAL} e deveriam somar 100")


def pontuar(definicao: JourneyDefinition,
            sinais: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    """`(score_bruto, detalhe_por_dimensao)` — a MEDIÇÃO, antes dos blockers.

    🔴 Este número não é o score operacional. Ele é o que foi medido; o que vale
    para decidir sai de `avaliar_journey`, que zera isto na presença de blocker.
    Nunca exponha `score_bruto` sozinho numa tela: 95 sem o "e está bloqueada"
    ao lado é a frase mais perigosa que este módulo consegue produzir.
    """
    detalhe: List[Dict[str, Any]] = []
    total = 0
    for dim in DIMENSOES:
        ok = bool(dim.regra(definicao, sinais))
        total += dim.pontos if ok else 0
        detalhe.append({
            "chave": dim.chave,
            "titulo": dim.titulo,
            "pontos_possiveis": dim.pontos,
            "pontos": dim.pontos if ok else 0,
            "atendida": ok,
            "frase": dim.titulo if ok else dim.falta,
        })
    return total, detalhe


# --------------------------------------------------------------------------
# §21.1 — a escada, degrau por degrau
# --------------------------------------------------------------------------
def estado_de_release(definicao: JourneyDefinition,
                      sinais: Dict[str, Any],
                      *, tem_blocker: Optional[bool] = None) -> str:
    """O degrau mais alto **contíguo** que os sinais sustentam.

    Contíguo é a palavra: a escada para no primeiro degrau que falha, mesmo que
    o de cima tenha sinal verde. Um canário read-only que passou sem que as
    fixtures existam não é uma journey adiantada — é uma journey que rodou em
    produção sem rede de proteção, e chamá-la de `CANARY_READONLY_GREEN` daria
    ao acidente o nome de progresso.

    `CANARY_TRANSACTIONAL_GREEN` não é alcançável por journey read-only: não há
    transação a fazer. Para ela, o degrau abaixo de `LIVE_APPROVED` é o canário
    read-only, e é o suficiente.

    🔴 `LIVE_APPROVED` exige aprovação **e** ausência de blocker. Um estado que
    diga "live" com blocker aberto seria a mesma mentira do score alto, só que
    escrita por extenso.
    """
    material = _e_material(definicao)
    bloqueada = blockers_de(definicao, sinais) if tem_blocker is None else bool(tem_blocker)
    if not isinstance(bloqueada, bool):
        bloqueada = bool(bloqueada)

    degraus: List[Tuple[str, bool]] = [
        (FIXTURE_GREEN, (_quantos(sinais, "fixtures") > 0
                         and _provado(sinais, "replay_verde")
                         and _provado(sinais, "testes_verdes"))),
        (DRY_RUN_GREEN, _provado(sinais, "dry_run_verde")),
        (CANARY_READONLY_GREEN, _provado(sinais, "canario_readonly_verde")),
        (CANARY_TRANSACTIONAL_GREEN,
         material and _provado(sinais, "canario_transacional_verde")),
        (LIVE_APPROVED, _provado(sinais, "aprovacao_de_lancamento") and not bloqueada),
    ]

    atual = DRAFT
    for nome, alcancado in degraus:
        if nome == CANARY_TRANSACTIONAL_GREEN and not material:
            # Degrau que não se aplica não interrompe a escada — ele é pulado,
            # e a journey read-only segue do canário read-only direto para live.
            continue
        if not alcancado:
            break
        atual = nome
    return atual


# --------------------------------------------------------------------------
# A função que o resto do mundo chama
# --------------------------------------------------------------------------
def avaliar_journey(definicao: JourneyDefinition,
                    sinais: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Avalia uma journey. Pura: dois dicionários entram, um dicionário sai.

    Sem I/O, sem Supabase, sem rede — de propósito (ver o cabeçalho do módulo).

    O que sai, e por que são DOIS números:

        score_bruto   o que foi medido nas dez dimensões do §21.2
        score         o que vale operacionalmente: 0 quando há hard blocker
        live_eligible a unica resposta que autoriza alguma coisa
        blocker       o primeiro hard blocker, no formato do exemplo do §21.3
        blockers      todos eles — consertar um de cada vez custa uma rodada
                      de descoberta por vez

    O §21.3 imprime `score = 95 / live_eligible = false`. Mantemos o 95 visível
    como `score_bruto`, porque é uma medição verdadeira e jogar fora medição é
    perder informação de trabalho. Mas o campo que as telas, relatórios e
    ordenações leem chama-se `score`, e ele é **0** — ver o bloco 🔴 do §21.3
    acima para os três motivos de não subtrair.

    Sobre o 100 (§21.4): `score == 100` significa *"todos os gates definidos
    foram medidos e passaram"*. Não significa que a journey nunca falha. O
    portal externo continua podendo cair, mudar de HTML e recusar login no meio
    da tarde. O sistema excelente não é o que promete um mundo externo
    infalível — é o que falha com segurança, diagnóstico e retomada.
    """
    s = validar_sinais(sinais)
    bloqueios = blockers_de(definicao, s)
    bruto, dimensoes = pontuar(definicao, s)

    # 🔴 A anulação. Uma linha, e é a razão de existir do módulo.
    score = 0 if bloqueios else bruto

    estado = estado_de_release(definicao, s, tem_blocker=bool(bloqueios))
    live = (not bloqueios) and estado == LIVE_APPROVED

    if bloqueios:
        motivo = (f"{len(bloqueios)} hard blocker(s) do §21.3 — score medido "
                  f"{bruto}/100 anulado para 0; nao pode rodar em live")
    elif live:
        motivo = (f"{score}/100 nos gates definidos, aprovada para live. "
                  "'100' quer dizer que tudo que definimos medir passou, "
                  "nao que o portal externo nunca cai (§21.4)")
    else:
        faltando = [d["frase"] for d in dimensoes if not d["atendida"]]
        motivo = (f"sem blocker, {score}/100, estado {estado}: "
                  + ("; ".join(faltando) if faltando
                     else "falta a aprovacao de lancamento"))

    return {
        "chave": definicao.chave,
        "portal_key": definicao.portal_key,
        "journey_key": definicao.journey_key,
        "business_operation": definicao.business_operation,
        "effect_class": definicao.effect_class,
        "requires_account": bool(getattr(definicao, "requires_account", True)),
        "supports_resume": bool(getattr(definicao, "supports_resume", False)),
        "caminho_primario": str(s.get("caminho_primario") or "desconhecido"),
        "fixtures": _quantos(s, "fixtures"),
        "casos_negativos": _quantos(s, "casos_negativos"),
        "estado": estado,
        "score": score,
        "score_bruto": bruto,
        "dimensoes": dimensoes,
        "blockers": bloqueios,
        "blocker": bloqueios[0]["codigo"] if bloqueios else None,
        "live_eligible": live,
        "ultimo_canario": (str(s["ultimo_canario"])
                           if s.get("ultimo_canario") else None),
        "motivo": motivo,
        "faltam": [d["frase"] for d in dimensoes if not d["atendida"]],
    }


# --------------------------------------------------------------------------
# §22 — a matriz gerada
#
# Uma tabela mantida à mão sobre o que 14 journeys sabem fazer é uma segunda
# verdade: ela nasce certa e envelhece errada, e o dia em que ela mente é o dia
# em que alguem confia nela para decidir. Esta sai do registry, então não tem
# como divergir dele.
# --------------------------------------------------------------------------
CABECALHO_GERADO = (
    "> **GERADO — NÃO EDITAR MANUALMENTE**  \n"
    "> fonte: registry + test manifests + canary evidence"
)

# §22.1, na ordem que a SPEC lista.
COLUNAS: Tuple[str, ...] = (
    "portal",
    "journey",
    "business operation",
    "effect class",
    "requires account",
    "supports resume",
    "API-first / DOM / adaptive / vision",
    "fixture count",
    "negative cases",
    "readiness state",
    "score",
    "last canary",
    "live eligible",
    "blocking reason",
)


def matriz_linhas(sinais_por_chave: Optional[Dict[str, Dict[str, Any]]] = None
                  ) -> List[Dict[str, Any]]:
    """Uma avaliação por journey, agrupada por operação de negócio.

    A ordem vem de `matriz_de_capacidades()` — operação, depois portal, depois
    journey — e não de uma lista escrita aqui. Ordem estável importa mais do que
    parece: um documento gerado que embaralha linhas produz diff ilegível, e
    diff ilegível é como uma mudança de verdade passa despercebida na revisão.

    Serve tanto ao `.md` quanto ao `.json` do §22 — os dois arquivos saem da
    mesma linha, então não há como um dizer uma coisa e o outro outra.
    """
    sinais = dict(sinais_por_chave or {})
    linhas: List[Dict[str, Any]] = []
    for operacao, bloco in sorted(matriz_de_capacidades().items()):
        for portal_key in bloco.get("portais", []):
            for definicao in journeys_do_portal(portal_key):
                if definicao.business_operation != operacao:
                    continue
                avaliacao = avaliar_journey(definicao, sinais.get(definicao.chave))
                avaliacao["operacao"] = operacao
                linhas.append(avaliacao)
    return linhas


def _celula(valor: Any) -> str:
    """Texto de célula — o `|` vira `\\|` para não partir a tabela em duas."""
    return str("—" if valor in (None, "") else valor).replace("|", "\\|")


def _sim_nao(valor: Any) -> str:
    return "sim" if valor else "nao"


def matriz_markdown(sinais_por_chave: Optional[Dict[str, Dict[str, Any]]] = None,
                    *, gerado_em: Optional[str] = None) -> str:
    """O `docs/generated/portal-capability-matrix.md` do §22, como string.

    Devolve texto e não escreve arquivo: escrever é trabalho do script que
    gera, e manter o I/O fora daqui é o que permite testar o documento inteiro
    sem tocar em disco.

    `gerado_em` é opcional e vem de fora. Carimbar `datetime.now()` aqui faria o
    arquivo mudar a cada execução mesmo sem nenhuma mudança de conteúdo, e um
    documento que sempre aparece no diff é um documento que ninguém mais lê no
    diff.
    """
    linhas = matriz_linhas(sinais_por_chave)

    fora: List[str] = ["# Portal Capability Matrix", "", CABECALHO_GERADO]
    if gerado_em:
        fora.append(f"> gerado em: {gerado_em}")
    fora += [
        "",
        "Uma linha por `(portal, journey)`. `score` já é o score **operacional**: "
        "hard blocker do §21.3 não desconta pontos, ele **anula** — uma journey "
        "bloqueada aparece com 0 e a medição bruta fica em `score_bruto`, no JSON.",
        "",
        "| " + " | ".join(COLUNAS) + " |",
        "|" + "|".join(["---"] * len(COLUNAS)) + "|",
    ]

    for a in linhas:
        fora.append("| " + " | ".join([
            _celula(a["portal_key"]),
            _celula(a["journey_key"]),
            _celula(a["business_operation"]),
            _celula(a["effect_class"]),
            _sim_nao(a["requires_account"]),
            _sim_nao(a["supports_resume"]),
            _celula(a["caminho_primario"]),
            _celula(a["fixtures"]),
            _celula(a["casos_negativos"]),
            _celula(a["estado"]),
            _celula(a["score"]),
            _celula(a["ultimo_canario"]),
            _sim_nao(a["live_eligible"]),
            _celula(a["blocker"]),
        ]) + " |")

    elegiveis = sum(1 for a in linhas if a["live_eligible"])
    bloqueadas = sum(1 for a in linhas if a["blockers"])
    fora += [
        "",
        f"{len(linhas)} journey(s) · {elegiveis} elegivel(is) a live · "
        f"{bloqueadas} com hard blocker aberto.",
        "",
        "**Sobre o 100 (§21.4).** Score 100 significa que *todos os gates que "
        "definimos medir foram medidos e passaram*. Não significa que a journey "
        "nunca falha: o portal externo continua podendo cair, mudar de HTML ou "
        "recusar login. O sistema excelente é o que falha com segurança, "
        "diagnóstico e retomada — não o que promete um mundo externo infalível.",
        "",
    ]
    return "\n".join(fora)
