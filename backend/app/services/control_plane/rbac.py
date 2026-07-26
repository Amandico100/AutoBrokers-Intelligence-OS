"""RBAC administrativo. SPEC-061 §8.

O que este módulo decide
------------------------
Uma pergunta só, e ela é sempre feita no **servidor**:

    esta pessoa pode fazer esta ação agora?

Hoje o Portal Admin responde isso com um bit — `master` ou não. Quem entra vê
39 telas e pode acionar 114 rotas de API. Não é que as regras da §8.5 estejam
mal implementadas: elas **não têm onde ser escritas**. Frases como

    "o financeiro não acessa conteúdo sensível de corretora"
    "o auditor é somente leitura"
    "o suporte não altera cobrança"

não são expressáveis com um booleano.

Por que a matriz é CÓDIGO e o vínculo é DADO
--------------------------------------------
A lista de permissions é uma constante do produto: ela muda quando uma tela
nova nasce, no mesmo deploy que a criou. Mantida em tabela, criaria um estado
em que o código cobra uma permission que o banco não conhece — e a tela some
sem ninguém entender por quê.

Quem tem qual papel, e até quando, é operacional: muda numa terça à tarde, sem
deploy. Por isso `platform_admin_role_bindings` é tabela e a matriz abaixo é
código.

Fail-closed
-----------
Permission desconhecida é **negada**. Papel desconhecido não concede nada.
Sem vínculo ativo, nada é concedido. Em cada bifurcação deste arquivo, a
resposta na dúvida é *não* — o oposto do que a SPEC-055 faz com sinais, e pelo
motivo inverso: aqui o custo do falso positivo é alguém agir sobre a corretora
sem poder para isso.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# §8.3 — as permissions
# ---------------------------------------------------------------------------
#
# Agrupadas por assunto para leitura humana. A tupla achatada é a autoridade:
# uma permission que não estiver aqui é negada, mesmo que um papel a cite.

PERMISSIONS: tuple[str, ...] = (
    "admin.overview.read", "admin.inbox.read", "admin.inbox.manage",
    "companies.read", "companies.manage", "companies.suspend",
    "companies.support_access",
    "users.read", "users.manage",
    "work_runs.read", "work_runs.retry", "work_runs.cancel",
    "approvals.read", "approvals.decide",
    "agents.read", "agents.manage",
    "skills.read", "skills.publish", "skills.rollback",
    "tools.read", "tools.manage",
    "mcps.read", "mcps.manage",
    "connections.read", "connections.manage", "connections.rotate",
    "artifacts.read", "artifacts.revoke",
    "auxiliaries.read", "auxiliaries.publish",
    "routines.read", "routines.manage",
    "intelligence.read", "intelligence.manage",
    "research.read", "research.manage",
    "knowledge.read", "knowledge.curate", "knowledge.publish",
    "memory.metadata.read", "memory.sensitive.read",
    "finance.read", "finance.manage",
    "security.read", "security.manage",
    "releases.read", "releases.rollout", "releases.rollback",
    "audit.read", "legal.manage", "system.manage",
)

CONJUNTO_DE_PERMISSIONS = frozenset(PERMISSIONS)

# Leitura pura — o piso de qualquer papel administrativo. Separado porque a
# maioria dos papéis o herda inteiro, e repetir a lista dez vezes é como as
# matrizes de permissão divergem com o tempo.
_LEITURA_BASICA = (
    "admin.overview.read", "admin.inbox.read",
    "companies.read", "users.read", "work_runs.read", "approvals.read",
    "agents.read", "skills.read", "tools.read", "mcps.read",
    "connections.read", "artifacts.read", "auxiliaries.read", "routines.read",
    "intelligence.read", "research.read", "knowledge.read",
    "memory.metadata.read", "security.read", "releases.read",
)


# ---------------------------------------------------------------------------
# §8.1 e §8.5 — a matriz
# ---------------------------------------------------------------------------
#
# Cada papel carrega o motivo pelo qual ele NÃO tem alguma coisa. Essa é a
# parte que costuma se perder: seis meses depois ninguém lembra se a ausência
# foi decisão ou esquecimento, e alguém "conserta" concedendo.

PAPEIS: dict[str, dict[str, Any]] = {
    "platform_owner": {
        "nome": "Dono da plataforma",
        "descricao": "Pode tudo. É o papel do Founder.",
        # Único papel com `system.manage` e `legal.manage`.
        "permissions": set(PERMISSIONS),
    },
    "platform_admin": {
        "nome": "Administrador",
        "descricao": "Opera a plataforma inteira, menos o que é do dono.",
        "permissions": set(PERMISSIONS) - {
            # Configuração de sistema e jurídico ficam com o dono: são as duas
            # que mudam as regras do jogo para todas as corretoras de uma vez.
            "system.manage", "legal.manage",
            # §8.5: conteúdo sensível de memória exige justificativa e papel
            # próprio, não vem de graça com "ser admin".
            "memory.sensitive.read",
        },
    },
    "platform_operations": {
        "nome": "Operações",
        "descricao": "Faz o trabalho voltar a andar: reprocessa, cancela, "
                     "acompanha conexões e rotinas.",
        "permissions": set(_LEITURA_BASICA) | {
            "work_runs.retry", "work_runs.cancel",
            "approvals.decide",
            "routines.manage", "auxiliaries.publish",
            "connections.manage",
            "intelligence.manage", "research.manage",
            "admin.inbox.manage",
        },
        # Sem `finance.*`: quem desbloqueia trabalho não deveria poder mexer em
        # cobrança. Sem `connections.rotate`: girar segredo é ação de segurança.
    },
    "platform_support": {
        "nome": "Suporte",
        "descricao": "Ajuda uma corretora específica, por tempo determinado.",
        "permissions": set(_LEITURA_BASICA) | {
            "companies.support_access",
            "admin.inbox.manage",
            "work_runs.retry",
        },
        # §8.5: "suporte não altera billing". Sem `finance.*`, sem
        # `companies.manage`, sem `companies.suspend`.
    },
    "platform_finance": {
        "nome": "Financeiro",
        "descricao": "Cuida de planos, créditos, custo e cobrança.",
        "permissions": {
            "admin.overview.read", "companies.read", "users.read",
            "work_runs.read", "finance.read", "finance.manage",
            "audit.read",
        },
        # §8.5: "financeiro não acessa conteúdo tenant sensível". Por isso não
        # há `knowledge.read`, `intelligence.read`, `artifacts.read` nem
        # `memory.*` aqui — nem em leitura.
    },
    "platform_security": {
        "nome": "Segurança",
        "descricao": "Investiga incidente, gira segredo, responde a risco.",
        "permissions": set(_LEITURA_BASICA) | {
            "security.manage", "connections.rotate", "audit.read",
            "companies.suspend",
        },
        # §8.5: "security não vê conteúdo de conversas sem justificativa" —
        # `memory.sensitive.read` sai daqui e passa por override nominal, com
        # prazo e motivo escrito.
    },
    "platform_curator": {
        "nome": "Curadoria de conhecimento",
        "descricao": "Decide o que entra no cérebro das corretoras.",
        "permissions": {
            "admin.overview.read", "companies.read",
            "knowledge.read", "knowledge.curate", "knowledge.publish",
            "research.read", "artifacts.read",
        },
        # §8.5: "curador não acessa secrets". Sem `connections.*`.
    },
    "platform_release_manager": {
        "nome": "Gestão de versões",
        "descricao": "Publica e reverte Skills, tools e releases.",
        "permissions": set(_LEITURA_BASICA) | {
            "skills.publish", "skills.rollback",
            "tools.manage", "mcps.manage",
            "releases.rollout", "releases.rollback",
            "auxiliaries.publish",
        },
    },
    "platform_auditor": {
        "nome": "Auditoria",
        "descricao": "Lê tudo o que precisa auditar. Não muda nada.",
        # §8.5: "auditor é read-only". A ausência de qualquer verbo de escrita
        # aqui é a regra inteira — e é verificada por teste, porque uma
        # permission de escrita que caia neste conjunto por descuido não
        # produziria erro visível: produziria um auditor que age.
        "permissions": set(_LEITURA_BASICA) | {"audit.read", "finance.read"},
    },
    "platform_viewer": {
        "nome": "Leitura",
        "descricao": "Acompanha sem agir.",
        "permissions": {
            "admin.overview.read", "admin.inbox.read",
            "companies.read", "work_runs.read",
        },
    },
}

# §8.2 — o papel histórico. Um único bit vira o papel mais alto porque é o que
# ele significava na prática; a granularidade vem da atribuição dos papéis
# novos, não de rebaixar quem já opera hoje e quebrar o Admin.
PAPEL_LEGADO = {"master": "platform_owner"}

# Ações que exigem confirmação recente de identidade — §7.4. São as que mudam
# a vida da corretora, mexem em segredo ou em dinheiro.
EXIGEM_STEP_UP = frozenset({
    "companies.suspend", "connections.rotate", "finance.manage",
    "memory.sensitive.read", "releases.rollback", "system.manage",
    "legal.manage", "security.manage",
})

# Risco declarado por permission — vai para `admin_audit_events.risk_tier`, e é
# o que faz o CHECK do banco exigir motivo escrito nas críticas.
RISCO: dict[str, str] = {
    "companies.suspend": "critical",
    "system.manage": "critical",
    "legal.manage": "critical",
    "connections.rotate": "critical",
    "memory.sensitive.read": "critical",
    "finance.manage": "high",
    "releases.rollback": "high",
    "releases.rollout": "high",
    "security.manage": "high",
    "skills.publish": "high",
    "skills.rollback": "high",
    "companies.manage": "high",
    "companies.support_access": "high",
    "artifacts.revoke": "medium",
    "approvals.decide": "medium",
    "work_runs.cancel": "medium",
    "work_runs.retry": "medium",
    "knowledge.publish": "medium",
    "auxiliaries.publish": "medium",
    "tools.manage": "medium",
    "mcps.manage": "medium",
    "connections.manage": "medium",
    "routines.manage": "medium",
    "users.manage": "medium",
}


def risco_de(permission_key: str) -> str:
    """Nível de risco. Desconhecida vira `low` porque não concede nada."""
    return RISCO.get(permission_key, "low")


def exige_step_up(permission_key: str) -> bool:
    return permission_key in EXIGEM_STEP_UP


def permissions_do_papel(role_key: str) -> frozenset[str]:
    """Papel desconhecido não concede nada — fail-closed."""
    papel = PAPEIS.get(role_key)
    if not papel:
        logger.warning("[RBAC] papel desconhecido: %s", role_key)
        return frozenset()
    return frozenset(papel["permissions"])


# ---------------------------------------------------------------------------
# Decisão
# ---------------------------------------------------------------------------


@dataclass
class Decisao:
    """O veredito, com o porquê. §8.4: a API devolve 403 estável."""

    permitido: bool
    permission_key: str
    motivo: str
    papeis: list[str] = field(default_factory=list)
    risco: str = "low"
    exige_step_up: bool = False
    origem: str = "role"  # role | override | negado

    def como_403(self) -> dict:
        """Corpo estável do 403 — sem revelar a matriz a quem não pode ver."""
        return {"ok": False, "error": "forbidden",
                "permission": self.permission_key, "motivo": self.motivo}


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _vigente(linha: dict, agora: datetime) -> bool:
    """Vínculo válido AGORA: ativo, começado e não vencido.

    A expiração é conferida aqui e não só por varredura: uma varredura que
    atrase dez minutos deixaria dez minutos de acesso que já deveria ter
    acabado — e é exatamente nesses minutos que um acesso esquecido é usado.
    """
    if str(linha.get("status") or "") != "active":
        return False
    try:
        inicio = linha.get("starts_at")
        if inicio and datetime.fromisoformat(
                str(inicio).replace("Z", "+00:00")) > agora:
            return False
        fim = linha.get("expires_at")
        if fim and datetime.fromisoformat(
                str(fim).replace("Z", "+00:00")) <= agora:
            return False
    except Exception:  # noqa: BLE001
        # Data ilegível é tratada como vencida. Na dúvida sobre autorização,
        # negar — o contrário abriria acesso por erro de formatação.
        return False
    return True


def decidir(*, permission_key: str, papeis: list[str],
            overrides: Optional[list[dict]] = None,
            agora: Optional[datetime] = None) -> Decisao:
    """A decisão pura. Sem banco, sem rede — testável linha a linha.

    Ordem: **deny vence sempre**. Um `deny` explícito é uma remoção deliberada
    de poder de alguém que já o tinha; se um papel pudesse anulá-lo, o override
    não serviria para nada — e é justamente ele o instrumento de conter alguém
    no meio de um incidente.
    """
    agora = agora or _agora()
    risco = risco_de(permission_key)
    step_up = exige_step_up(permission_key)

    if permission_key not in CONJUNTO_DE_PERMISSIONS:
        return Decisao(False, permission_key,
                       "permissão desconhecida", papeis, risco, step_up,
                       origem="negado")

    vigentes = [o for o in (overrides or [])
                if str(o.get("permission_key") or "") == permission_key
                and _vigente({**o, "status": "active"}, agora)]

    if any(str(o.get("effect")) == "deny" for o in vigentes):
        return Decisao(False, permission_key,
                       "acesso removido por decisão nominal", papeis, risco,
                       step_up, origem="override")

    concedidas: set[str] = set()
    for r in papeis:
        concedidas |= permissions_do_papel(r)

    if permission_key in concedidas:
        return Decisao(True, permission_key, "concedida pelo papel", papeis,
                       risco, step_up, origem="role")

    if any(str(o.get("effect")) == "allow" for o in vigentes):
        return Decisao(True, permission_key,
                       "concedida por exceção nominal com prazo", papeis,
                       risco, step_up, origem="override")

    return Decisao(False, permission_key,
                   "seu papel não inclui esta ação", papeis, risco, step_up,
                   origem="negado")


# ---------------------------------------------------------------------------
# Leitura do vínculo
# ---------------------------------------------------------------------------


class AutoridadeAdministrativa:
    """Lê papéis e overrides vigentes de uma pessoa."""

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def papeis(self, user_id: str, *,
               papel_legado: Optional[str] = None) -> list[str]:
        """Papéis vigentes. Falha de leitura devolve lista vazia.

        Devolver vazio numa falha é deliberado: um erro de banco não pode
        conceder acesso. O Admin fica inacessível por alguns segundos — que é
        um problema visível, e portanto consertável.
        """
        agora = _agora()
        encontrados: list[str] = []
        try:
            linhas = (self.db.table("platform_admin_role_bindings")
                      .select("role_key, status, starts_at, expires_at")
                      .eq("user_id", str(user_id))
                      .eq("status", "active").execute()).data or []
            encontrados = [str(l["role_key"]) for l in linhas
                           if _vigente(l, agora)]
        except Exception as exc:  # noqa: BLE001
            logger.error("[RBAC] leitura de papéis falhou: %s", type(exc).__name__)
            return []

        # §8.2 — quem já era `master` continua operando enquanto os papéis
        # novos não são atribuídos. Sem isto, aplicar esta SPEC deixaria o
        # Founder de fora do próprio Admin.
        if not encontrados and papel_legado:
            mapeado = PAPEL_LEGADO.get(str(papel_legado).strip().lower())
            if mapeado:
                return [mapeado]
        return encontrados

    def overrides(self, user_id: str) -> list[dict]:
        agora_iso = _agora().isoformat()
        try:
            return (self.db.table("platform_admin_permission_overrides")
                    .select("permission_key, effect, scope, starts_at, expires_at")
                    .eq("user_id", str(user_id))
                    .gt("expires_at", agora_iso).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[RBAC] leitura de overrides falhou: %s", type(exc).__name__)
            return []

    def pode(self, user_id: str, permission_key: str, *,
             papel_legado: Optional[str] = None) -> Decisao:
        papeis = self.papeis(user_id, papel_legado=papel_legado)
        if not papeis:
            return Decisao(False, permission_key,
                           "sem papel administrativo ativo", [],
                           risco_de(permission_key),
                           exige_step_up(permission_key), origem="negado")
        return decidir(permission_key=permission_key, papeis=papeis,
                       overrides=self.overrides(user_id))

    def menu(self, user_id: str, *,
             papel_legado: Optional[str] = None) -> frozenset[str]:
        """§8.4: "menu é derivado das permissions".

        O menu não é segurança — esconder botão é conveniência. Mas mostrar um
        item que devolve 403 ao ser clicado ensina o operador a duvidar da tela
        inteira, e uma tela em que não se confia deixa de ser usada.
        """
        papeis = self.papeis(user_id, papel_legado=papel_legado)
        if not papeis:
            return frozenset()
        concedidas: set[str] = set()
        for r in papeis:
            concedidas |= permissions_do_papel(r)
        for o in self.overrides(user_id):
            chave = str(o.get("permission_key") or "")
            if str(o.get("effect")) == "allow":
                concedidas.add(chave)
            else:
                concedidas.discard(chave)
        return frozenset(c for c in concedidas if c in CONJUNTO_DE_PERMISSIONS)
