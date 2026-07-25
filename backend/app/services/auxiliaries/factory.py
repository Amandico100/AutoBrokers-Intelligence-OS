"""Auxiliary & Routine Factory. SPEC-058 §5 e §9.

O erro que este serviço existe para impedir
-------------------------------------------
Um corretor diz *"queria que alguém acompanhasse os boletos vencendo"*. A
resposta fácil é criar um Agent. A resposta certa quase nunca é.

Criar Agent para tudo produz: um prompt novo por corretora, custo de contexto
que ninguém mediu, comportamento que diverge entre tenants, e nada disso
reaproveitável. A SPEC-058 §5.3 chama isso de **inflação de Agents** e proíbe.

A árvore de decisão (§5.2)
--------------------------
    já dá para executar uma vez?              → Work Run único
    é só recorrência de uma Skill existente?  → Rotina ligada à Skill
    exige identidade, configuração, histórico? → Auxiliar instalado
    exige várias fases e um caso que anda?    → workflow
    existe executor determinístico melhor?    → executor especializado
    exige raciocínio aberto recorrente?       → Agent-backed  ← último recurso
    falta capacidade?                          → registra o gap e explica

Resolver antes de criar (§9.3)
------------------------------
Antes de propor qualquer coisa nova, procura o que já existe: template
publicado, Skill do Registry, Auxiliar já instalado, Rotina já criada.
Um sistema que cria em vez de reusar acumula duplicata até ninguém saber qual
das três rotinas de cobrança é a que vale.

E o pedido que não dá para atender não morre na conversa: vira `capability_gap`
com contador. A mesma dor pedida por dez corretoras é o sinal de roadmap mais
forte que existe — e hoje ele se perde.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Padrões de trabalho da SPEC-058 §5.1, do mais barato ao mais caro.
ONE_SHOT = "one_shot_work_run"
ROTINA = "saved_routine"
AUXILIAR = "installed_auxiliary"
WORKFLOW = "workflow_instance"
EXECUTOR = "specialized_executor"
AGENT = "agent_backed_auxiliary"

CUSTO_RELATIVO = {ONE_SHOT: 1, ROTINA: 2, EXECUTOR: 2, AUXILIAR: 3, WORKFLOW: 4, AGENT: 5}


# --------------------------------------------------------------------------
# Redação
# --------------------------------------------------------------------------

_PII = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[CNPJ]"),
    (re.compile(r"\b[A-Z]{3}-?\d[A-Z\d]\d{2}\b"), "[PLACA]"),
    (re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"), "[EMAIL]"),
    (re.compile(r"(?:\+?55\s*)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}"), "[TELEFONE]"),
    (re.compile(r"\bap[óo]lice\s+(?:n[º°.]?\s*)?[\w.\-/]{4,}", re.I), "apólice [NUMERO]"),
]


def redigir(texto: str) -> str:
    """Remove PII antes de o pedido virar dado de roadmap.

    O funil de demanda é lido por gente da **plataforma**, não da corretora.
    Um pedido citando o CPF de um segurado não pode atravessar essa fronteira —
    e ninguém percebe que atravessou até ser tarde.
    """
    saida = texto or ""
    for padrao, marca in _PII:
        saida = padrao.sub(marca, saida)
    return saida.strip()[:2000]


_PARADA = {
    "que", "para", "com", "uma", "dos", "das", "por", "nos", "nas", "aos",
    "meu", "minha", "seus", "suas", "eles", "elas", "isso", "esse", "essa",
    "quero", "queria", "gostaria", "preciso", "poderia", "pode", "podia",
    "alguem", "alguém", "fosse", "seja", "ser", "esta", "está", "estao",
    "todo", "toda", "todos", "todas", "cada", "favor", "obrigado", "sobre",
}

# Depois destas palavras vem um nome próprio. É a forma mais confiável de
# achar nome sem lista de nomes — e lista de nomes erra em toda cultura.
_ANTES_DE_NOME = {"cliente", "segurado", "segurada", "sr", "sra", "senhor",
                  "senhora", "dona", "dr", "dra", "empresa", "corretora"}

# Sufixos de flexão do português, do mais longo para o mais curto. Não é um
# stemmer completo — é o suficiente para colapsar conjugação e plural, que é o
# que separa "acompanhasse", "acompanhar" e "acompanhe".
_SUFIXOS = (
    "aríamos", "eríamos", "iríamos", "assemos", "êssemos", "íssemos",
    "aremos", "eremos", "iremos", "ariam", "eriam", "iriam", "assem", "essem",
    "issem", "ando", "endo", "indo", "aram", "eram", "iram", "arão", "erão",
    "asse", "esse", "isse", "ação", "ções", "ares", "eres", "ires",
    "amos", "emos", "imos", "aria", "eria", "iria", "ados", "idos", "adas",
    "idas", "ada", "ado", "ida", "ido", "ava", "iam", "eis", "ais", "ar",
    "er", "ir", "am", "em", "os", "as", "es", "e", "a", "o", "s",
)


def _radical(palavra: str) -> str:
    """Reduz a palavra ao radical. Conservador: nunca corta abaixo de 4 letras.

    Cortar demais faria "boleto" e "bolo" colidirem, e uma assinatura que
    agrupa demais é tão inútil quanto uma que não agrupa.
    """
    for suf in _SUFIXOS:
        if palavra.endswith(suf) and len(palavra) - len(suf) >= 4:
            return palavra[: -len(suf)]
    return palavra


def fingerprint(texto: str) -> str:
    """Assinatura do PEDIDO, não do texto.

    Duas normalizações, e ambas descobertas quebrando o teste com frases reais:

    1. **Radical.** "acompanhasse", "acompanhar" e "acompanhe" são o mesmo
       verbo; "vencidos" e "venceram" são o mesmo estado. Sem reduzir ao
       radical, a mesma dor pedida de três jeitos vira três itens de backlog.

    2. **Nome próprio.** "cobrar o cliente João" e "cobrar o cliente Maria" são
       o mesmo pedido. Sem descartar o nome, cada cliente da carteira viraria
       uma "necessidade de produto" distinta — e o funil de demanda vira ruído
       exatamente quando começa a receber volume.
    """
    t = redigir(texto).lower()
    t = re.sub(r"[^\wàáâãéêíóôõúç\s]", " ", t)

    palavras = t.split()
    tokens: set[str] = set()
    pular_proxima = False
    for p in palavras:
        if pular_proxima:
            pular_proxima = False
            continue
        if p in _ANTES_DE_NOME:
            pular_proxima = True
            tokens.add(_radical(p))
            continue
        if len(p) > 2 and p not in _PARADA:
            tokens.add(_radical(p))

    return hashlib.sha256(" ".join(sorted(tokens)).encode("utf-8")).hexdigest()[:32]


# --------------------------------------------------------------------------
# Classificação
# --------------------------------------------------------------------------

_RECORRENCIA = (
    "todo dia", "todos os dias", "diariamente", "toda semana", "semanalmente",
    "todo mês", "todo mes", "mensalmente", "sempre que", "toda vez que",
    "de tempos em tempos", "periodicamente", "me avise quando", "me avisa quando",
    "acompanh", "monitor", "fique de olho", "todo dia de manhã",
)
_UMA_VEZ = (
    "agora", "hoje", "me faz", "me faça", "gera", "gere", "monta", "monte",
    "quero ver", "me mostra", "me mostre", "preciso de um", "só dessa vez",
)
_FASES = (
    "depois", "em seguida", "primeiro", "só então", "quando terminar",
    "aprovação", "aprovacao", "aprovar antes", "etapa", "fluxo", "acompanhar até",
)
_IDENTIDADE = (
    "responsável por", "responsavel por", "cuide de", "cuidar de",
    "toma conta", "tomar conta", "assistente de", "gerente de", "encarregado",
)


@dataclass
class Decisao:
    padrao: str
    motivo: str
    confianca: float = 0.5
    reusa: Optional[dict] = None          # o que já existe e serve
    gaps: list[dict] = field(default_factory=list)
    mensagem_humana: str = ""

    @property
    def cria_algo(self) -> bool:
        return self.reusa is None and not self.gaps


def classificar_padrao(texto: str, *, tem_skill: bool = False) -> Decisao:
    """Árvore de decisão da §5.2. Léxica, barata e explicável.

    Ordem importa: a árvore é percorrida do padrão mais barato para o mais
    caro, e para no primeiro que serve. Perguntar "precisa de Agent?" primeiro
    é como se acaba criando Agent para tudo.
    """
    t = (texto or "").lower()

    recorrente = any(p in t for p in _RECORRENCIA)
    fases = any(p in t for p in _FASES)
    identidade = any(p in t for p in _IDENTIDADE)
    uma_vez = any(p in t for p in _UMA_VEZ)

    # 1. Uma vez só — o mais barato que resolve.
    if uma_vez and not recorrente:
        return Decisao(ONE_SHOT, "pedido pontual, sem recorrência", 0.8,
                       mensagem_humana="Faço isso agora mesmo, sem precisar configurar nada.")

    # 2. Várias fases com um caso que anda até o fim.
    if fases and recorrente:
        return Decisao(WORKFLOW, "há fases e dependência entre etapas", 0.7,
                       mensagem_humana="Isso tem etapas que dependem umas das outras — "
                                       "vou montar como um fluxo que acompanha o caso até o fim.")

    # 3. Recorrência simples de algo que já sabemos fazer.
    if recorrente and not identidade:
        return Decisao(ROTINA,
                       "recorrência de um trabalho conhecido" if tem_skill
                       else "recorrência, mas ainda sem Skill publicada que atenda",
                       0.75 if tem_skill else 0.5,
                       mensagem_humana="Dá para deixar isso rodando sozinho numa agenda.")

    # 4. Identidade persistente: várias responsabilidades, configuração própria.
    if identidade or (recorrente and fases):
        return Decisao(AUXILIAR, "responsabilidade contínua com configuração própria", 0.7,
                       mensagem_humana="Isso merece um Auxiliar instalado — um trabalhador "
                                       "que você abre, configura e acompanha.")

    # 5. Nada disso ficou claro. NÃO se assume Agent: assume-se o mais barato e
    #    pergunta-se. Adivinhar para cima cria estrutura que ninguém pediu.
    return Decisao(ONE_SHOT, "intenção não ficou clara — assumindo o mais simples", 0.3,
                   mensagem_humana="Posso fazer isso agora uma vez. Se você quiser que "
                                   "passe a acontecer sozinho, me diga com que frequência.")


# --------------------------------------------------------------------------
# Serviço
# --------------------------------------------------------------------------

class AuxiliaryFactory:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    def _agora(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Resolver antes de criar (§9.3)
    # ------------------------------------------------------------------

    def procurar_existente(self, company_id: str, texto: str) -> Optional[dict]:
        """O que já existe e resolve isto?

        Ordem: instalação do próprio tenant primeiro (é o que ele já conhece),
        depois template publicado, depois Skill do Registry. Propor instalar algo
        que a corretora já tem instalado é o jeito mais rápido de parecer burro.
        """
        alvo = (texto or "").lower()
        palavras = {p for p in re.findall(r"\w{4,}", alvo)}
        if not palavras:
            return None

        try:
            instalados = (self.db.table("tenant_auxiliaries")
                          .select("id, slug, name, status, template_id")
                          .eq("company_id", company_id).execute()).data or []
            for a in instalados:
                nome = f"{a.get('name','')} {a.get('slug','')}".lower()
                if sum(1 for p in palavras if p in nome) >= 2:
                    return {"tipo": "tenant_auxiliary", "id": a["id"],
                            "nome": a.get("name"), "status": a.get("status"),
                            "acao": "ja_instalado"}

            rotinas = (self.db.table("routines")
                       .select("id, name, is_active").eq("company_id", company_id)
                       .execute()).data or []
            for r in rotinas:
                nome = (r.get("name") or "").lower()
                if sum(1 for p in palavras if p in nome) >= 2:
                    return {"tipo": "routine", "id": r["id"], "nome": r.get("name"),
                            "status": "ativa" if r.get("is_active") else "pausada",
                            "acao": "ja_existe"}

            templates = (self.db.table("auxiliary_templates")
                         .select("id, slug, name, short_description, status")
                         .eq("is_active", True).execute()).data or []
            for t in templates:
                blob = f"{t.get('name','')} {t.get('slug','')} {t.get('short_description','')}".lower()
                if sum(1 for p in palavras if p in blob) >= 2:
                    return {"tipo": "template", "id": t["id"], "nome": t.get("name"),
                            "acao": "instalar"}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] busca por existente falhou: %s", type(exc).__name__)
        return None

    def skill_que_atende(self, texto: str, agent_role: str = "core",
                         company_id: Optional[str] = None) -> Optional[dict]:
        """Usa o Skill Registry da SPEC-056 — não uma segunda busca de Skills."""
        try:
            from ..skills.registry import SkillRegistry

            reg = SkillRegistry(self.db)
            candidatos = reg.indice(agent_role=agent_role, company_id=company_id)
            if not candidatos:
                return None
            top = reg.shortlist(candidatos, texto, limite=1)
            if top and top[0].confidence > 0:
                return {"skill_key": top[0].skill_key, "release_id": top[0].release_id,
                        "nome": top[0].name, "confianca": top[0].confidence}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] registry indisponivel: %s", type(exc).__name__)
        return None

    # ------------------------------------------------------------------
    # Fluxo principal
    # ------------------------------------------------------------------

    def avaliar(self, *, company_id: str, texto: str, user_id: Optional[str] = None,
                source: str = "chat", agent_role: str = "core") -> dict:
        """Recebe um pedido e devolve o que fazer — sem criar nada ainda.

        Separar avaliar de executar é deliberado: o corretor precisa ver a
        proposta antes. Sistema que cria Auxiliar no meio de uma conversa
        produz coisas que ninguém pediu e ninguém sabe desligar.
        """
        skill = self.skill_que_atende(texto, agent_role, company_id)
        decisao = classificar_padrao(texto, tem_skill=bool(skill))
        existente = self.procurar_existente(company_id, texto)
        if existente:
            decisao.reusa = existente
            decisao.mensagem_humana = _mensagem_de_reuso(existente)

        pedido = self.registrar_pedido(
            company_id=company_id, texto=texto, user_id=user_id, source=source,
            decisao=decisao, skill=skill, existente=existente)

        return {
            "request_id": pedido.get("id"),
            "padrao": decisao.padrao,
            "motivo": decisao.motivo,
            "confianca": decisao.confianca,
            "reusa": existente,
            "skill": skill,
            "custo_relativo": CUSTO_RELATIVO.get(decisao.padrao, 3),
            "mensagem_humana": decisao.mensagem_humana,
        }

    def registrar_pedido(self, *, company_id: str, texto: str,
                         user_id: Optional[str], source: str, decisao: Decisao,
                         skill: Optional[dict], existente: Optional[dict]) -> dict:
        """Grava o pedido no funil. Sempre — inclusive o que foi atendido."""
        registro = {
            "company_id": company_id, "user_id": user_id, "source": source,
            "request_text_redacted": redigir(texto),
            "request_fingerprint": fingerprint(texto),
            "requested_outcome": redigir(texto)[:300],
            "classified_work_pattern": decisao.padrao,
            "status": "matched" if existente else "classified",
            "matched_template_id": existente.get("id") if (existente or {}).get("tipo") == "template" else None,
            "matched_skill_release_id": (skill or {}).get("release_id"),
        }
        try:
            r = (self.db.table("auxiliary_requests").insert(registro).execute()).data
            return (r or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] pedido nao registrado: %s", type(exc).__name__)
            return {}

    # ------------------------------------------------------------------
    # Lacunas
    # ------------------------------------------------------------------

    def registrar_lacuna(self, *, gap_type: str, descricao: str,
                         company_id: Optional[str] = None,
                         capability_key: Optional[str] = None,
                         provider: Optional[str] = None,
                         request_id: Optional[str] = None) -> dict:
        """Uma lacuna, contador incrementado. Nunca uma linha por ocorrência.

        A mesma falta pedida cem vezes é UMA lacuna com peso cem. Cem linhas
        de backlog idênticas não são prioridade, são ruído.
        """
        fp = hashlib.sha256(
            f"{gap_type}|{capability_key or ''}|{provider or ''}|"
            f"{fingerprint(descricao)}".encode("utf-8")).hexdigest()[:32]

        try:
            atual = (self.db.table("capability_gaps")
                     .select("id, frequency_count").eq("fingerprint", fp)
                     .limit(1).execute()).data
            if atual:
                linha = atual[0]
                self.db.table("capability_gaps").update({
                    "frequency_count": int(linha.get("frequency_count") or 1) + 1,
                    "last_seen_at": self._agora(),
                }).eq("id", linha["id"]).execute()
                return {"id": linha["id"], "novo": False,
                        "frequency_count": int(linha.get("frequency_count") or 1) + 1}

            novo = (self.db.table("capability_gaps").insert({
                "company_id": company_id, "auxiliary_request_id": request_id,
                "gap_type": gap_type, "capability_key": capability_key,
                "provider": provider, "description_redacted": redigir(descricao),
                "fingerprint": fp, "status": "open",
            }).execute()).data
            return {"id": (novo or [{}])[0].get("id"), "novo": True, "frequency_count": 1}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] lacuna nao registrada: %s", type(exc).__name__)
            return {}

    def lacunas_por_prioridade(self, limite: int = 40) -> list[dict]:
        """O que mais gente pediu e ainda não fazemos. É roadmap com evidência."""
        try:
            r = (self.db.table("capability_gaps")
                 .select("id, gap_type, capability_key, provider, description_redacted, "
                         "frequency_count, first_seen_at, last_seen_at, status")
                 .eq("status", "open").order("frequency_count", desc=True)
                 .limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def evento(self, *, event_type: str, company_id: Optional[str] = None,
               tenant_auxiliary_id: Optional[str] = None,
               template_id: Optional[str] = None, actor_kind: str = "system",
               actor_id: Optional[str] = None, detail: Optional[dict] = None) -> None:
        try:
            self.db.table("auxiliary_events").insert({
                "company_id": company_id, "tenant_auxiliary_id": tenant_auxiliary_id,
                "template_id": template_id, "event_type": event_type,
                "actor_kind": actor_kind, "actor_id": actor_id,
                "detail": detail or {},
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] evento nao gravado: %s", type(exc).__name__)


def _mensagem_de_reuso(existente: dict) -> str:
    tipo, nome = existente.get("tipo"), existente.get("nome") or "isso"
    if tipo == "tenant_auxiliary":
        estado = existente.get("status")
        if estado and estado not in ("active", "ativo"):
            return (f"Você já tem o **{nome}** instalado, mas ele está {estado}. "
                    f"Quer que eu reative em vez de instalar outro?")
        return (f"Você já tem o **{nome}** instalado e ele faz isso. "
                f"Quer que eu ajuste a configuração dele?")
    if tipo == "routine":
        return (f"Já existe a rotina **{nome}** ({existente.get('status')}) fazendo isso. "
                f"Prefere ajustar essa a criar outra?")
    return f"Existe o **{nome}** pronto no catálogo. Posso instalar para você agora."
