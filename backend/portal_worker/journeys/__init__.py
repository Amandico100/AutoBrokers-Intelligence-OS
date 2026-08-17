"""Contrato das journeys do portal-worker (SPEC-020 · enriquecido pela SPEC-075).

Journey = função async `run(page, params, evidence) -> JourneyResult`, código
versionado por portal. O worker só executa a journey determinística; a DECISÃO
de negócio fica no Smith (cérebro único, regra inviolável).

O registro é um MAPA, não um if/elif
====================================
Ele já foi uma cadeia de `if key == ...` com 4 entradas. Para 4 servia; para os
17 portais da tabela `portals` seriam ~34 blocos, e cada seguradora nova tocaria
o mesmo trecho — conflito de merge garantido e um lugar a mais para esquecer.

O mapa preserva o que motivava o if/elif: **o import continua tardio.** Só o
módulo da journey pedida é carregado, e o worker não puxa Playwright à toa.

Por que o mapa mora aqui, no código, e NÃO numa tabela
------------------------------------------------------
Uma linha de banco apontando para um símbolo Python permitiria o banco nomear
uma função que **não existe na imagem que está no ar** — e o portal-worker é um
serviço separado no EasyPanel, que desalinha de banco por desenho. Seria a
falha da CLAUDE.md §9.1 na veia: tudo verde, e o serviço devolvendo erro em
produção. Mapa no mesmo commit da journey nunca desalinha.

CAPACIDADE, não trabalho
------------------------
O nome depois do ponto é o que o robô SABE FAZER naquele portal, não para que
estamos usando. `cobranca_sweep` é herança da SPEC-023 e continua valendo por
compatibilidade; journeys novas nascem com nome de capacidade
(`listar_parcelas_em_atraso`), porque o mesmo portal vai servir renovação,
cotação e relatório depois — e um nome de trabalho num lugar de capacidade é
como a bagunça volta.

SPEC-075 — o registro passa a DIZER o que cada journey é
=========================================================
Continua **um** registry: `JOURNEYS`. O que muda é o valor. Ele era
`(módulo, função)` e passa a ser uma `JourneyDefinition`, que responde três
perguntas que ninguém conseguia fazer ao código:

    que OPERAÇÃO DE NEGÓCIO isto implementa?   → `business_operation`
    isto CRIA COISA no mundo?                  → `effect_class`
    dá para retomar de onde parou?             → `supports_resume`

🔴 `JourneyDefinition` **se comporta como a tupla antiga**: `__iter__`,
`__getitem__` e `__len__` estão implementados. Qualquer código que faça
`modulo, funcao = JOURNEYS[chave]` continua funcionando byte por byte. Isso não
é elegância — é a única forma de enriquecer o registro sem criar o
`journey_registry_v2` que a SPEC-075 §9.1 proíbe.

E `effect_class` NÃO é uma segunda autoridade comercial
--------------------------------------------------------
Quem autoriza continua sendo `capabilities` + `tool_definitions` + Tool Gateway
+ approval. O campo aqui existe por **um** motivo de segurança, escrito na
SPEC-075 §9.2: uma execução legada que chegue ao Portal Worker por fora do
Gateway não pode fingir que uma journey material é read-only. Ver
`conflito_de_efeito()`: divergência sempre resolve para a proteção MAIS FORTE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Awaitable, Callable, Dict, Iterator, List, Optional, Tuple

VALID_STATUS = ("done", "needs_human", "failed")


@dataclass
class JourneyResult:
    status: str  # done | needs_human | failed
    captured: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    message: str = ""


# --------------------------------------------------------------------------
# Classes de efeito — importadas de `guardrails`, NÃO redefinidas aqui.
#
# 🔴 Duas listas de "o que é efeito material" divergem no primeiro dia em que
# alguém acrescenta um valor numa e esquece a outra — e a que estiver errada
# vai ser a que decide se um clique acontece. A SPEC-073 já é dona deste
# vocabulário; aqui ele é apenas reusado.
# --------------------------------------------------------------------------
READ_ONLY = "read_only"
REVERSIBLE_UI = "reversible_ui"
MATERIAL_SIDE_EFFECT = "material_side_effect"

# Ordem de FORÇA de proteção. Índice maior = mais protegido.
FORCA_DA_CLASSE: Tuple[str, ...] = (READ_ONLY, REVERSIBLE_UI, MATERIAL_SIDE_EFFECT)


def _classes_do_guardrails() -> Tuple[str, ...]:
    """As classes segundo a SPEC-073, se o módulo estiver disponível.

    O `journeys/__init__` é importado por código que não carrega o runtime
    inteiro (a API do smith-api lê `portais_com_cobranca`). Por isso o import é
    tardio e tolerante — mas o teste de contrato prova que os dois vocabulários
    são o MESMO conjunto, então a tolerância nunca esconde divergência.
    """
    try:
        from portal_worker.guardrails import CLASSES_VALIDAS

        return tuple(CLASSES_VALIDAS)
    except Exception:  # noqa: BLE001
        return FORCA_DA_CLASSE


def classe_mais_forte(a: Any, b: Any) -> str:
    """Entre duas classes de efeito, a que protege MAIS.

    SPEC-075 §9.2: divergência entre o que a Tool diz e o que a Journey diz
    nunca relaxa proteção. Valor desconhecido é tratado como o mais forte —
    não saber o que uma ação faz é motivo para protegê-la, não para liberá-la.
    """
    def idx(v: Any) -> int:
        s = str(v or "").strip().lower()
        return FORCA_DA_CLASSE.index(s) if s in FORCA_DA_CLASSE else len(FORCA_DA_CLASSE)

    vencedor = max(idx(a), idx(b))
    if vencedor >= len(FORCA_DA_CLASSE):
        return MATERIAL_SIDE_EFFECT
    return FORCA_DA_CLASSE[vencedor]


def conflito_de_efeito(classe_da_tool: Any, classe_da_journey: Any) -> Tuple[bool, str]:
    """`(reprova, motivo)` — o portão da SPEC-075 §9.2.

    A regra tem dois lados e eles NÃO são simétricos:

        Tool diz READ  + Journey diz MATERIAL  → conflito, FAIL CLOSED
        Tool diz MATERIAL + Journey diz READ   → segue, com a proteção forte

    O primeiro caso é o perigoso: alguém autorizou uma leitura e receberia uma
    escrita. Recusar é a única resposta. O segundo é apenas uma Tool cautelosa
    demais, e cautela a mais nunca causou dano.
    """
    t = classe_mais_forte(classe_da_tool, classe_da_tool)
    j = classe_mais_forte(classe_da_journey, classe_da_journey)
    if FORCA_DA_CLASSE.index(j) > FORCA_DA_CLASSE.index(t):
        return True, (f"a tool foi autorizada como `{t}` mas a journey e `{j}`: "
                      "executar entregaria um efeito que ninguem autorizou")
    return False, ""


# --------------------------------------------------------------------------
# Operações de negócio — o nome ESTÁVEL do que o trabalho produz
#
# 🔴 A operação é o que sobrevive à troca de portal. `billing.overdue.list` vale
# para Allianz, HDI, MAPFRE, Tokio, Yelum e Zurich, que implementam a MESMA
# coisa por seis telas diferentes. É por isso que uma seguradora nova não cria
# Auxiliar novo, nem Tool nova: ela só acrescenta um portal que já sabe fazer
# uma operação conhecida.
#
# Nome no formato `dominio.substantivo.verbo`. Não inventar operação para
# journey que ainda não existe (SPEC-075 §9.3).
# --------------------------------------------------------------------------
OP_BILLING_OVERDUE_LIST = "billing.overdue.list"
OP_PORTAL_LOGIN_CHECK = "portal.login.check"
OP_ASSISTANCE_GLASS_REQUEST = "assistance.glass.request"

OPERACOES_CONHECIDAS: Tuple[str, ...] = (
    OP_BILLING_OVERDUE_LIST,
    OP_PORTAL_LOGIN_CHECK,
    OP_ASSISTANCE_GLASS_REQUEST,
)


@dataclass(frozen=True)
class JourneyDefinition:
    """O que o registro sabe sobre uma journey.

    Compatível com a tupla `(módulo, função)` que este mapa devolvia antes —
    ver `__iter__`/`__getitem__`/`__len__` no fim da classe.
    """

    portal_key: str
    journey_key: str
    business_operation: str
    module: str
    function: str
    contract_version: str = "1"
    effect_class: str = READ_ONLY
    requires_account: bool = True
    supports_resume: bool = False
    supports_discovery: bool = True
    description: str = ""

    @property
    def chave(self) -> str:
        return f"{self.portal_key}.{self.journey_key}"

    @property
    def e_material(self) -> bool:
        return self.effect_class == MATERIAL_SIDE_EFFECT

    # -- compatibilidade com o formato antigo, byte por byte ---------------
    def __iter__(self) -> Iterator[str]:
        return iter((self.module, self.function))

    def __getitem__(self, i):
        return (self.module, self.function)[i]

    def __len__(self) -> int:
        return 2


def _cobranca(portal_key: str, module: str) -> Dict[str, JourneyDefinition]:
    """As duas journeys que todo portal de corretora tem, escritas uma vez.

    Seis portais × duas journeys, com os mesmos metadados, seria doze linhas
    onde uma diverge sem ninguém ver. `login_check` e `cobranca_sweep` são o
    par que define "portal de corretora conectado" — quem tiver um sem o outro
    é um caso especial, e caso especial se escreve à mão, fora daqui.
    """
    return {
        f"{portal_key}.login_check": JourneyDefinition(
            portal_key=portal_key, journey_key="login_check",
            business_operation=OP_PORTAL_LOGIN_CHECK,
            module=module, function="login_check",
            effect_class=READ_ONLY,
            description="confere se a credencial da corretora ainda entra"),
        f"{portal_key}.cobranca_sweep": JourneyDefinition(
            portal_key=portal_key, journey_key="cobranca_sweep",
            business_operation=OP_BILLING_OVERDUE_LIST,
            module=module, function="cobranca_sweep",
            effect_class=READ_ONLY,
            description="lista as parcelas vencidas da carteira"),
    }


# portal_key.journey -> JourneyDefinition. UMA linha por capacidade.
JOURNEYS: Dict[str, JourneyDefinition] = {
    **_cobranca("allianz_corretor", "portal_worker.journeys.allianz_corretor"),
    **_cobranca("hdi_corretor", "portal_worker.journeys.hdi_corretor"),
    **_cobranca("tokiomarine_corretor", "portal_worker.journeys.tokio_corretor"),
    **_cobranca("yelum_corretor", "portal_worker.journeys.yelum_corretor"),
    **_cobranca("mapfre_corretor", "portal_worker.journeys.mapfre_corretor"),
    **_cobranca("zurich_corretor", "portal_worker.journeys.zurich_corretor"),
    "vidros_lanternas.login_check": JourneyDefinition(
        portal_key="vidros_lanternas", journey_key="login_check",
        business_operation=OP_PORTAL_LOGIN_CHECK,
        module="portal_worker.journeys.vidros_lanternas", function="login_check",
        effect_class=READ_ONLY,
        description="confere se a credencial do portal de vidros ainda entra"),
    "vidros_lanternas.abrir_atendimento": JourneyDefinition(
        portal_key="vidros_lanternas", journey_key="abrir_atendimento",
        business_operation=OP_ASSISTANCE_GLASS_REQUEST,
        module="portal_worker.journeys.vidros_lanternas",
        function="abrir_atendimento",
        # 🔴 MATERIAL. Esta journey cria um atendimento PAGO no nome de um
        # segurado real. Ela vai até a tela de confirmação sem `confirm=True`,
        # mas a classe descreve o que a journey PODE fazer, não o que ela faz
        # numa chamada específica — senão a proteção dependeria do parâmetro
        # que ela deveria proteger.
        effect_class=MATERIAL_SIDE_EFFECT,
        supports_resume=True,
        description="abre atendimento de vidro/lanterna no portal Maxpar"),
}

# A journey que o Auxiliar de Cobrança pede a cada portal.
JOURNEY_COBRANCA = "cobranca_sweep"


# --------------------------------------------------------------------------
# Introspecção — funções PURAS sobre o registro (SPEC-075 §9.4)
# --------------------------------------------------------------------------
def get_definition(portal_key: str, journey: str) -> Optional[JourneyDefinition]:
    """A definição, sem importar o módulo. Não custa nada e não puxa Playwright."""
    return JOURNEYS.get(f"{str(portal_key or '').strip()}.{str(journey or '').strip()}")


def get_journey(portal_key: str, journey: str) -> Optional[Callable[..., Awaitable["JourneyResult"]]]:
    """Resolve a journey por 'portal_key.journey' (import tardio: só carrega o
    módulo pedido, para não puxar Playwright quando não precisa)."""
    alvo = get_definition(portal_key, journey)
    if not alvo:
        return None
    try:
        return getattr(import_module(alvo.module), alvo.function)
    except (ImportError, AttributeError):
        # Mapa aponta para código que não existe nesta imagem. Devolver None faz
        # o worker gravar 'journey desconhecida' com o nome no erro — diagnóstico
        # legível — em vez de derrubar o processo inteiro do poll.
        return None


def journeys_do_portal(portal_key: str) -> List[JourneyDefinition]:
    """Tudo que sabemos fazer num portal, em ordem estável."""
    p = str(portal_key or "").strip()
    return sorted((d for d in JOURNEYS.values() if d.portal_key == p),
                  key=lambda d: d.journey_key)


def portais_com_operacao(business_operation: str) -> List[str]:
    """Quais portais implementam esta operação de negócio, em ordem estável.

    Esta é a pergunta que o Work OS faz. Ele não sabe o nome de journey nenhuma
    — ele sabe o resultado que quer.
    """
    op = str(business_operation or "").strip()
    return sorted({d.portal_key for d in JOURNEYS.values()
                   if d.business_operation == op})


def suporta(portal_key: str, business_operation: str) -> bool:
    return str(portal_key or "").strip() in portais_com_operacao(business_operation)


def journey_para_operacao(portal_key: str,
                          business_operation: str) -> Optional[JourneyDefinition]:
    """A journey que implementa esta operação NESTE portal.

    Devolve `None` quando não há — e `None` aqui vira `not_supported` no
    Gateway, nunca um chute em outra journey do mesmo portal.

    Quando houver mais de uma candidata, vence a de `journey_key` menor, por
    ordem estável. Hoje não há empate; o teste de contrato prova isso, e vai
    reprovar no dia em que houver — que é quando alguém precisa decidir de
    verdade, em vez de descobrir por acaso em produção.
    """
    p = str(portal_key or "").strip()
    op = str(business_operation or "").strip()
    cand = sorted((d for d in JOURNEYS.values()
                   if d.portal_key == p and d.business_operation == op),
                  key=lambda d: d.journey_key)
    return cand[0] if cand else None


def operacoes_registradas() -> List[str]:
    """Todas as operações que o registro implementa de fato, em ordem estável."""
    return sorted({d.business_operation for d in JOURNEYS.values()})


def matriz_de_capacidades() -> Dict[str, Dict[str, Any]]:
    """`{operação: {portais: [...], effect_class: ..., journeys: [...]}}`.

    É a fonte da documentação gerada (SPEC-075 §22) e da tela de admin. Sai do
    código, então **não tem como divergir do código**.
    """
    saida: Dict[str, Dict[str, Any]] = {}
    for d in sorted(JOURNEYS.values(), key=lambda x: (x.business_operation, x.chave)):
        bloco = saida.setdefault(d.business_operation, {
            "portais": [], "journeys": [], "effect_class": READ_ONLY})
        bloco["portais"].append(d.portal_key)
        bloco["journeys"].append(d.chave)
        bloco["effect_class"] = classe_mais_forte(bloco["effect_class"], d.effect_class)
    for bloco in saida.values():
        bloco["portais"] = sorted(set(bloco["portais"]))
    return saida


# --------------------------------------------------------------------------
# Compatibilidade — o contrato externo do Cobrador NÃO muda
# --------------------------------------------------------------------------
def portais_com_cobranca() -> List[str]:
    """Portais que o Cobrador SABE varrer, em ordem estável.

    É a fonte única para o serviço e para a tela: portal conectado que não está
    aqui não é varrido em silêncio — ele aparece no relatório como *ainda não
    automatizado*. Seguradora não cai por esquecimento; cai por estar escrito.

    SPEC-075 §9.4: passou a ser derivada de `portais_com_operacao`, mas o
    resultado é o MESMO. A lista continua vindo de `JOURNEYS`; o que mudou é
    que a pergunta agora é sobre a operação de negócio, não sobre o sufixo de
    uma string. `JOURNEY_COBRANCA` segue exportada e usada no teste de
    equivalência, que prova que as duas formas de perguntar dão a mesma lista.
    """
    return portais_com_operacao(OP_BILLING_OVERDUE_LIST)


def tem_cobranca(portal_key: str) -> bool:
    return suporta(portal_key, OP_BILLING_OVERDUE_LIST)
