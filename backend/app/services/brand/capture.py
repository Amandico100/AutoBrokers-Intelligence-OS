"""Captura da identidade da corretora. SPEC-057 §Bloco A.

Orquestra: fontes declaradas → busca → sinais → logo → paleta → sistema de
design → procedência campo a campo → versão.

Três regras que não se negociam
-------------------------------
1. **O logo manda na cor.** Ficou provado no primeiro site real testado: o CSS
   da Resulta devolve `#f78da7`, `#cf2e2e`, `#ff6900`, `#fcb900` — a paleta
   padrão do editor do WordPress, sem uma única cor da marca. O logo devolve
   `#1D5579` e `#EE7501`, que são a marca. CSS entra como confirmação, nunca
   como origem.

2. **Edição humana nunca é sobrescrita.** Recaptura respeita `human_edited`.
   Automação que desfaz decisão do dono não é automação, é perda de controle.

3. **Todo campo carrega de onde veio e com que confiança.** É o que permite ao
   corretor conferir em vez de aceitar mágica.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from .color import cores_css_confiaveis as _cores_css_confiaveis, parse_color
from .extract import analisar_logo
from .jeito_de_atender import (
    ESCOLHAS as ESCOLHAS_DO_JEITO,
    LISTAS as LISTAS_DO_JEITO,
    render as render_jeito,
    render_corretora,
    validar as validar_jeito,
    vazio as jeito_vazio,
)
from .system import FALLBACK_ACENTO, FALLBACK_PRIMARIA, build_design_system
from .web import SinaisWeb, baixar_binario, coletar

logger = logging.getLogger(__name__)

CAMPOS_TEXTO = (
    "display_name", "legal_name", "tagline", "mission", "about_md",
    "service_area", "susep_code",
)

# ==========================================================================
# SPEC-098 · O SITE É LIDO (U1) e O JEITO DE ATENDER (U2)
# ==========================================================================

#: R12 "custo com nome": toda chamada de modelo desta SPEC tem `service_type`
#: próprio. Sem ele a leitura do site cairia em "chat" (`llm_factory.py:82`,
#: `service_type = "chat" if company_id else "plataforma"`) e somaria ao custo
#: de ATENDIMENTO da corretora um gasto que nunca foi atendimento.
SERVICE_TYPE_MARCA = "brand_capture"

#: E4 — teto de ENTRADA da leitura. UMA chamada por captura, nunca uma por
#: campo. `texto_md` já vem cortado em 24.000 por fonte (`web.py:227`); o corte
#: é "site primeiro, redes depois", porque foi o site que respondeu na vida
#: inteira do produto (📊 `brand_sources`: website 200 ×3, instagram 429 ×3).
TETO_ENTRADA_LEITURA = 40_000

#: ≤3 frases de ≤120 caracteres sustentam cada proposta de jeito (U1.1).
TETO_EVIDENCIA = (3, 120)

#: 🔴 O VOCABULÁRIO DA PROCEDÊNCIA É O DO BANCO, E ELE TEM CHECK.
#:
#: 📊 MEDIDO em 06/09/2026 no banco vivo (`pg_constraint` sobre
#: `brand_field_provenance`): `brand_field_provenance_source_kind_check` aceita
#: exatamente website · instagram · linkedin · google_business · facebook ·
#: logo_pixels · inferred · default · human. **`proposto` e `leitura_do_site`
#: NÃO estão lá** — gravar qualquer um dos dois levanta 23514 e derruba a
#: captura inteira.
#:
#: Então o código fala a NOSSA língua ("leitura_do_site" viaja dentro do
#: `CampoProposto`, e é o que a tela precisa distinguir) e traduz na porta do
#: banco. `inferred` é honesto: o modelo INFERIU do texto do site. Quando a
#: migration acrescentar `proposto` ao CHECK, muda-se esta linha e mais nada.
LEITURA_DO_SITE = "leitura_do_site"
_PROCEDENCIA_NO_BANCO = {LEITURA_DO_SITE: "inferred"}

#: R10/R11 — a fonte tem nome de gente na tela, nunca chave de código.
#: 📊 `BrandIdentityClient.tsx:251` mostrava `google_business` ao corretor.
KIND_HUMANO = {
    "website": "site",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
    "google_business": "perfil do Google",
}

_REDES_QUE_BLOQUEIAM = ("instagram", "linkedin", "facebook")

FRASE_REDE_BLOQUEIA = ("a rede bloqueia a leitura automática — cole a bio "
                       "ou os posts fixados")
FRASE_FIRECRAWL_402 = ("o serviço de leitura profunda está sem crédito; "
                       "lemos o site diretamente")
FRASE_EGRESSO = "endereço fora dos que você declarou"
FRASE_TIMEOUT = "o site demorou demais"
FRASE_GENERICA = "não foi possível ler este endereço"


def frase_humana_da_fonte(kind: str, *, http_status: Optional[int] = None,
                          erro: Optional[str] = None) -> str:
    """O motivo em PORTUGUÊS. Nenhuma chave de código atravessa daqui (R10).

    📊 O defeito medido: `brand_sources.error` guardava `HTTP 429` e
    `EgressBlockedError`, e a tela os mostrava crus. "429" não diz à dona da
    corretora o que ela pode FAZER; "cole a bio" diz.
    """
    tecnico = (erro or "")
    if "Egress" in tecnico:
        return FRASE_EGRESSO
    if "Timeout" in tecnico or "timeout" in tecnico.lower():
        return FRASE_TIMEOUT
    if http_status == 429:
        if kind in _REDES_QUE_BLOQUEIAM:
            return FRASE_REDE_BLOQUEIA
        return "o site recusou tantas leituras seguidas — tente de novo em alguns minutos"
    if http_status in (401, 403):
        if kind in _REDES_QUE_BLOQUEIAM:
            return FRASE_REDE_BLOQUEIA
        return "a página exige login para ser lida"
    if http_status == 404:
        return "esse endereço não existe mais"
    if http_status and http_status >= 500:
        return "o site respondeu com erro"
    return FRASE_GENERICA


def frase_humana_do_firecrawl(motivo: Optional[str]) -> Optional[str]:
    """O 402 deixa de ser engolido (U1.2/E14).

    📊 `web.py:395-396` descartava `r.erro` e devolvia `None`: crédito esgotado
    e site fora do ar chegavam à corretora com a mesma cara. O único consumidor
    que tratava 402 direito era `insurance_corpus.py:1381-1417`.
    """
    if not motivo:
        return None
    if "402" in str(motivo):
        return FRASE_FIRECRAWL_402
    return None


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_url(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    try:
        p = urlparse(u)
        return u if p.hostname else None
    except Exception:  # noqa: BLE001
        return None


@dataclass
class CampoProposto:
    """Um valor candidato, com sua origem. A origem viaja junto do valor."""

    valor: Any
    source_kind: str
    source_detail: str = ""
    confidence: float = 0.5
    source_id: Optional[str] = None


@dataclass
class ResultadoCaptura:
    profile_id: str
    campos: dict[str, CampoProposto] = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)
    completeness: float = 0.0
    status: str = "captured"
    erro: Optional[str] = None
    avisos: list[str] = field(default_factory=list)
    #: SPEC-098 — de quem e esta captura. A leitura por modelo precisa saber
    #: para quem lancar o custo (R12), e a proposta de jeito, para quem gravar.
    company_id: str = ""
    #: O Jeito de atender PROPOSTO pela leitura (R2: proposto, nunca publicado).
    jeito_proposto: Optional[dict] = None
    jeito_evidencia: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# A saida do modelo e TIPADA. Texto livre de LLM nao entra no banco.
# --------------------------------------------------------------------------
#
# 🔴 Sem contrato, um modelo que devolve prosa em vez de JSON grava prosa na
# coluna `mission` e ninguem percebe ate a peca sair com um paragrafo de
# desculpas no lugar da missao. `extra="ignore"` porque campo A MAIS do modelo
# e ruido, nao erro; campo com TIPO errado e erro e derruba a proposta inteira.

class ServicoLido(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: Optional[str] = None
    audience: Optional[str] = None


class JeitoLido(BaseModel):
    """O jeito como o MODELO o propoe. `validar()` e quem manda depois."""

    model_config = ConfigDict(extra="ignore")
    saudacao: Optional[str] = None
    tratamento: Optional[str] = None
    emoji: Optional[str] = None
    formalidade: Optional[str] = None
    explicacao: Optional[str] = None
    principios: list[str] = Field(default_factory=list)
    termos_preferidos: list[str] = Field(default_factory=list)
    evitar: list[str] = Field(default_factory=list)
    evidencia: list[str] = Field(default_factory=list)


class LeituraDoSite(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mission: Optional[str] = None
    about_md: Optional[str] = None
    tagline: Optional[str] = None
    service_area: Optional[str] = None
    susep_code: Optional[str] = None
    founded_year: Optional[int] = None
    differentiators: list[str] = Field(default_factory=list)
    services: list[ServicoLido] = Field(default_factory=list)
    insurers: list[str] = Field(default_factory=list)
    tone_proposto: Optional[JeitoLido] = None


_RE_SUSEP = re.compile(r"^\d{2}\.\d{6}(-?\d)?$|^\d{6,10}$")


def _susep_confiavel(candidato: Optional[str], texto: str) -> Optional[str]:
    """SUSEP so passa com a PALAVRA perto do numero (U1.1).

    Um numero de 6 a 10 digitos solto num site e CEP, telefone, CNPJ truncado ou
    contador de visitas. O que o distingue e a vizinhanca: a palavra "SUSEP" a
    no maximo 40 caracteres. Sem ela o campo fica NULL — que e a verdade.
    """
    if not candidato:
        return None
    limpo = str(candidato).strip()
    if not _RE_SUSEP.match(limpo):
        return None
    nu = re.sub(r"\D", "", limpo)
    alvo = texto or ""
    for m in re.finditer(r"SUSEP", alvo, re.I):
        janela = alvo[max(0, m.start() - 40): m.end() + 40]
        if nu and nu in re.sub(r"\D", "", janela):
            return limpo
    return None


def _texto_da_resposta(bruto: Any) -> str:
    """O TEXTO da resposta — nao a repr da lista de blocos.

    Quando o modelo PENSA, o LangChain devolve `content` como LISTA de blocos, e
    `str()` numa lista devolve a repr dela; o leitor de JSON entao procura `{`
    dentro de uma string que comeca por `[{'type': 'thinking'...`. E o mesmo
    defeito que `attendance_distiller._texto_da_resposta` ja pagou.
    """
    conteudo = getattr(bruto, "content", bruto)
    if isinstance(conteudo, list):
        partes = []
        for bloco in conteudo:
            if isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(str(bloco.get("text") or ""))
            elif isinstance(bloco, str):
                partes.append(bloco)
        return "\n".join(partes).strip()
    return str(conteudo or "").strip()


def _json_do_texto(texto: str) -> dict:
    """O objeto JSON dentro da resposta.

    Levanta quando nao ha — e levantar e o comportamento certo: proposta que
    nao se entende nao vira gravacao.
    """
    s = (texto or "").strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[4:] if s.lower().startswith("json") else s
    inicio, fim = s.find("{"), s.rfind("}")
    if inicio < 0 or fim <= inicio:
        raise ValueError("a resposta do modelo nao tem objeto JSON")
    lido = json.loads(s[inicio:fim + 1])
    if not isinstance(lido, dict):
        raise ValueError("a resposta do modelo nao e um objeto")
    return lido


def _texto_para_leitura(sinais_por_fonte: dict) -> str:
    """Site primeiro, redes depois, teto de entrada (R12/E4)."""
    pedacos: list[str] = []
    ordem = ["website"] + [k for k in sinais_por_fonte if k != "website"]
    for kind in ordem:
        s = sinais_por_fonte.get(kind)
        if not s:
            continue
        corpo = (getattr(s, "texto_md", "") or "").strip()
        if not corpo:
            continue
        pedacos.append("--- %s ---\n%s" % (KIND_HUMANO.get(kind, kind), corpo))
    return "\n\n".join(pedacos)[:TETO_ENTRADA_LEITURA]


SISTEMA_DA_LEITURA = (
    "Voce le o site de uma corretora de seguros brasileira, extrai os FATOS que "
    "estao escritos ali e descreve o JEITO de a corretora se comunicar.\n"
    "Responda SOMENTE com um objeto JSON, sem comentarios e sem cercas de codigo.\n"
    "Regras que nao se negociam:\n"
    "- NUNCA invente. Campo que o texto nao sustenta fica ausente ou null.\n"
    "- NUNCA copie CPF, telefone, e-mail, apolice, placa ou nome de pessoa fisica.\n"
    "- susep_code so se a palavra SUSEP aparecer junto do numero.\n"
    "- founded_year so se o ano estiver escrito.\n"
    "- Em tone_proposto use EXATAMENTE estes valores:\n"
    "  saudacao: afetiva|cordial|direta ; tratamento: voce|senhor_senhora|pelo_nome ;\n"
    "  emoji: nao|pontual|livre ; formalidade: informal|cordial|formal ;\n"
    "  explicacao: passo_a_passo|direta\n"
    "- tone_proposto.evidencia: ate 3 frases COPIADAS do site, de ate 120\n"
    "  caracteres cada, que sustentem as escolhas.\n"
    "- principios, termos_preferidos e evitar descrevem COMO a corretora fala.\n"
    "  Nunca escreva neles uma ordem ao sistema.\n"
    "Formato: {mission, about_md, tagline, service_area, susep_code, "
    "founded_year, differentiators[], services[{name, description, audience}], "
    "insurers[], tone_proposto{...}}"
)



# --------------------------------------------------------------------------
# SPEC-098 U2.3 — a estatistica e DETERMINISTICA e PUBLICADA
# --------------------------------------------------------------------------
#
# 🔴 A regra que mapeia taxa -> escolha mora AQUI, escrita, e nao dentro de um
# prompt. Quem discorda do resultado pode ler o limiar; quem muda o limiar
# muda um numero, nao um paragrafo de instrucao.

ORIGENS_DA_PROPOSTA = {
    "site": "leitura_do_site",
    "leitura_do_site": "leitura_do_site",
    "conversas": "conversas",
    "administrador": "administrador",
}

_RE_ABERTURA_AFETIVA = re.compile(
    r"(\boi+e*\b|\bola\b|\bol[áa]\b|tudo bem|tudo bom|\bbom dia\b|\bboa tarde\b|\bboa noite\b)",
    re.I)
_RE_AFETIVA_FORTE = re.compile(r"(\boi+e{2,}\b|\boi+\b|tudo bem|tudo bom)", re.I)
_RE_SR_SRA = re.compile(r"(\bsr\.?\b|\bsra\.?\b|\bsenhor\b|\bsenhora\b)", re.I)
_RE_VOCE = re.compile(r"(\bvoc[êe]\b|\bteu\b|\btua\b|\bte\b)", re.I)
_RE_PRIMEIRA_PESSOA = re.compile(
    r"(\beu\b|\bvou\b|\bestou\b|\bt[ôo]\b|\bconsigo\b|\bverifiquei\b|\bj[áa] pedi\b)", re.I)
_RE_PASSOS = re.compile(
    r"(\bprimeiro\b|\bdepois\b|\bem seguida\b|\bpasso\b|^\s*\d[\).\-]|\bprocedimento\b)",
    re.I | re.M)
_RE_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF☀-➿⬀-⯿️❤]")


def _taxa(quantos: int, total: int) -> float:
    return round(quantos / total, 3) if total else 0.0


def medir_taxas(mensagens: list, aberturas: Optional[list] = None) -> dict:
    """As medidas do acervo. Numeros, nao impressoes.

    🔴 SAUDACAO SE MEDE NA ABERTURA, NAO NA MENSAGEM.
    📊 06/09/2026, Resulta, 295 mensagens de 56 conversas: medida sobre TUDO, a
    taxa afetiva deu 0,105 — abaixo do limiar — e a regra devolveu "cordial"
    para a corretora que a SPEC-098 §1.2 mediu abrindo com "Oieee boa tarde".
    O denominador estava errado: so a PRIMEIRA mensagem de cada conversa e uma
    saudacao; as outras 5 de cada 6 diluiam a conta.
    `aberturas=None` cai de volta em tudo — para quem so tem uma lista solta.
    """
    total = len(mensagens)
    if not total:
        return {}
    abre = list(aberturas) if aberturas else list(mensagens)
    n_abre = len(abre) or total
    comprimentos = [len(m) for m in mensagens]
    return {
        "mensagens": total,
        "conversas": len(abre),
        "saudacao": _taxa(sum(1 for m in abre if _RE_ABERTURA_AFETIVA.search(m)), n_abre),
        "afetiva": _taxa(sum(1 for m in abre if _RE_AFETIVA_FORTE.search(m)), n_abre),
        "senhor_senhora": _taxa(sum(1 for m in mensagens if _RE_SR_SRA.search(m)), total),
        "voce": _taxa(sum(1 for m in mensagens if _RE_VOCE.search(m)), total),
        "emoji": _taxa(sum(1 for m in mensagens if _RE_EMOJI.search(m)), total),
        # 🔴 PRESENCA E DENSIDADE SAO PERGUNTAS DIFERENTES, e so a segunda
        # separa "pontual" de "a vontade". Um acervo em que TODA mensagem tem
        # UM emoji e o retrato do uso pontual, nao do uso livre — medir so a
        # fracao de mensagens com emoji chamaria os dois de "livre".
        "emoji_por_mensagem": round(
            sum(len(_RE_EMOJI.findall(m)) for m in mensagens) / total, 2),
        "primeira_pessoa": _taxa(sum(1 for m in mensagens if _RE_PRIMEIRA_PESSOA.search(m)), total),
        "passos": _taxa(sum(1 for m in mensagens if _RE_PASSOS.search(m)), total),
        "tamanho_medio": round(sum(comprimentos) / total, 1),
    }


#: Os limiares. Cada um e um numero que se pode discutir — e nenhum e default
#: da casa: sem acervo nao sai escolha nenhuma (R2, estado inicial vazio).
LIMIARES = {
    "afetiva": 0.30,
    "sem_saudacao": 0.10,
    "senhor_senhora": 0.15,
    "emoji_nenhum": 0.05,
    #: emoji POR MENSAGEM (densidade), nao fracao de mensagens — ver `medir_taxas`
    "emoji_livre": 2.0,
    "emoji_informal": 0.30,
    "passos": 0.15,
    "tamanho_passo_a_passo": 180.0,
}


def escolhas_das_taxas(taxas: dict) -> dict:
    """taxa -> escolha da R3, pela regra escrita acima. Sem acervo, sem escolha."""
    if not taxas:
        return {}
    t = taxas
    escolhas = {}

    if t.get("afetiva", 0) >= LIMIARES["afetiva"]:
        escolhas["saudacao"] = "afetiva"
    elif t.get("saudacao", 0) < LIMIARES["sem_saudacao"]:
        escolhas["saudacao"] = "direta"
    else:
        escolhas["saudacao"] = "cordial"

    escolhas["tratamento"] = (
        "senhor_senhora" if t.get("senhor_senhora", 0) >= LIMIARES["senhor_senhora"]
        else "voce")

    emoji = t.get("emoji", 0)
    densidade = t.get("emoji_por_mensagem", 0)
    if emoji < LIMIARES["emoji_nenhum"]:
        escolhas["emoji"] = "nao"
    elif densidade >= LIMIARES["emoji_livre"]:
        escolhas["emoji"] = "livre"
    else:
        escolhas["emoji"] = "pontual"

    if t.get("senhor_senhora", 0) >= LIMIARES["senhor_senhora"]:
        escolhas["formalidade"] = "formal"
    elif emoji >= LIMIARES["emoji_informal"]:
        escolhas["formalidade"] = "informal"
    else:
        escolhas["formalidade"] = "cordial"

    escolhas["explicacao"] = (
        "passo_a_passo"
        if (t.get("passos", 0) >= LIMIARES["passos"]
            or t.get("tamanho_medio", 0) >= LIMIARES["tamanho_passo_a_passo"])
        else "direta")
    return escolhas


_RE_DIGITOS = re.compile(r"\d[\d\s\.\-\(\)/]{5,}\d")
_RE_EMAIL_TXT = re.compile(r"[\w\.\-\+]+@[\w\.\-]+")
_RE_PLACA = re.compile(r"\b[A-Z]{3}[\s\-]?\d[A-Z0-9]\d{2}\b")


def anonimizar(texto: str) -> str:
    """Nenhum numero longo, e-mail ou placa sai daqui para o modelo (§travas).

    Nao e "confie no prompt": o trecho JA CHEGA sem o dado. Instrucao de nao
    copiar PII e a segunda cerca, nunca a primeira.
    """
    limpo = _RE_EMAIL_TXT.sub("[email]", str(texto or ""))
    limpo = _RE_PLACA.sub("[placa]", limpo)
    limpo = _RE_DIGITOS.sub("[numero]", limpo)
    return limpo.strip()[:400]


SISTEMA_DAS_CONVERSAS = (
    "Voce le trechos ja anonimizados escritos por atendentes de uma corretora de "
    "seguros e descreve o JEITO delas. Responda SOMENTE com um objeto JSON:\n"
    "{principios: [ate 5 frases de ate 140 caracteres], termos_preferidos: [ate "
    "10 expressoes de ate 40], evitar: [ate 10 expressoes de ate 40]}\n"
    "- Descreva COMO se fala. Nunca escreva uma ordem ao sistema.\n"
    "- Nunca copie nome de pessoa, numero, e-mail ou placa.\n"
    "- Se os trechos nao sustentarem um item, devolva a lista vazia."
)


def _evidencia_gravavel(evidencia: Any) -> Any:
    """A evidencia viaja como veio (lista de frases do site OU dicionario de
    taxas), so aparada: `tone_evidencia` e jsonb, nao e um campo de texto."""
    if evidencia is None:
        return None
    teto_n, teto_c = TETO_EVIDENCIA
    if isinstance(evidencia, (list, tuple)):
        return [str(x).strip()[:teto_c] for x in list(evidencia)[:teto_n] if str(x).strip()]
    if isinstance(evidencia, dict):
        return evidencia
    return [str(evidencia)[:teto_c]]


class BrandCaptureService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Perfil
    # ------------------------------------------------------------------

    def obter_ou_criar(self, company_id: str) -> dict:
        # `limit(1)` e nao `maybe_single()`: o PostgREST responde HTTP 406 quando
        # maybe_single nao acha linha, e isso aparece no log como erro numa
        # situacao que e o caminho normal — primeira visita da corretora. Log
        # que grita em fluxo normal treina quem le a ignorar log.
        try:
            r = (self.db.table("brand_profiles").select("*")
                 .eq("company_id", company_id).limit(1).execute())
            if r and r.data:
                return r.data[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] leitura de perfil falhou: %s", type(exc).__name__)
        novo = (self.db.table("brand_profiles")
                .insert({"company_id": company_id}).execute()).data
        return novo[0] if novo else {}

    def _protegidos(self, profile_id: str) -> set[str]:
        """Campos que o humano editou — recaptura não encosta."""
        r = (self.db.table("brand_field_provenance")
             .select("field_path").eq("brand_profile_id", profile_id)
             .eq("human_edited", True).execute())
        return {x["field_path"] for x in (r.data or [])}

    # ------------------------------------------------------------------
    # Captura
    # ------------------------------------------------------------------

    async def capturar(self, company_id: str, *, run_id: Optional[str] = None,
                       forcar: bool = False) -> ResultadoCaptura:
        perfil = self.obter_ou_criar(company_id)
        pid = perfil["id"]

        urls = {
            "website": _norm_url(perfil.get("website_url")),
            "instagram": _norm_url(perfil.get("instagram_url")),
            "linkedin": _norm_url(perfil.get("linkedin_url")),
            "google_business": _norm_url(perfil.get("google_business_url")),
            "facebook": _norm_url(perfil.get("facebook_url")),
        }
        declaradas = [u for u in urls.values() if u]
        if not declaradas:
            return ResultadoCaptura(pid, company_id=str(company_id), status="empty",
                                    erro="nenhuma fonte declarada — informe ao menos o site")

        self.db.table("brand_profiles").update({
            "capture_status": "capturing", "capture_run_id": run_id,
            "capture_error": None, "updated_at": _agora(),
        }).eq("id", pid).execute()

        resultado = ResultadoCaptura(pid, company_id=str(company_id))
        protegidos = set() if forcar else self._protegidos(pid)
        sinais_por_fonte: dict[str, SinaisWeb] = {}

        # ---- 1. buscar cada fonte declarada -------------------------------
        for kind, url in urls.items():
            if not url:
                continue
            inicio = time.monotonic()
            try:
                sinais = await coletar(url, allowlist=declaradas,
                                       supabase=self.db, company_id=company_id)
                ok = bool(sinais.http_status and sinais.http_status < 400)
                fonte = {
                    "company_id": company_id, "brand_profile_id": pid, "kind": kind,
                    "url": url, "status": "fetched" if ok else "failed",
                    "http_status": sinais.http_status,
                    "fetched_at": _agora(),
                    "duration_ms": int((time.monotonic() - inicio) * 1000),
                    "extract": sinais.as_extract(),
                    "content_hash": hashlib.sha256(
                        (sinais.texto_md or "").encode("utf-8")).hexdigest()[:32],
                }
                if ok:
                    sinais_por_fonte[kind] = sinais
                else:
                    # SPEC-098 R10: o que fica GRAVADO ja e a frase humana. Se a
                    # traducao morasse so na tela, o proximo leitor de
                    # `brand_sources.error` (relatorio, suporte, artefato)
                    # voltaria a ver "HTTP 429".
                    frase = frase_humana_da_fonte(kind, http_status=sinais.http_status)
                    fonte["error"] = frase
                    fonte["error_tecnico"] = f"HTTP {sinais.http_status}"
                    resultado.avisos.append(
                        f"{KIND_HUMANO.get(kind, kind)}: {frase}")
            except Exception as exc:  # noqa: BLE001
                frase = frase_humana_da_fonte(kind, erro=type(exc).__name__)
                fonte = {
                    "company_id": company_id, "brand_profile_id": pid, "kind": kind,
                    "url": url, "status": "blocked" if "Egress" in type(exc).__name__ else "failed",
                    "error": frase,
                    "error_tecnico": type(exc).__name__,
                    "duration_ms": int((time.monotonic() - inicio) * 1000),
                    "fetched_at": _agora(), "extract": {},
                }
                resultado.avisos.append(f"{KIND_HUMANO.get(kind, kind)}: {frase}")

            # `error_tecnico` viaja no resultado (para o log e para o suporte),
            # mas NAO e coluna de `brand_sources` — inserir chave inexistente
            # e PGRST204 e derruba a captura inteira.
            tecnico = fonte.pop("error_tecnico", None)
            gravada = (self.db.table("brand_sources").insert(fonte).execute()).data
            if tecnico:
                fonte["error_tecnico"] = tecnico
            if gravada:
                fonte["id"] = gravada[0]["id"]
            resultado.sources.append(fonte)

        site = sinais_por_fonte.get("website")
        id_do_site = next((f.get("id") for f in resultado.sources
                           if f["kind"] == "website"), None)

        # ---- 2. texto ------------------------------------------------------
        if site:
            self._propor_texto(resultado, site, id_do_site)

            # 🔴 U1.2/E14 — o 402 do Firecrawl deixa de ser engolido. Ele nao e
            # falha: o site foi lido direto. Mas a corretora precisa saber por
            # que as redes nao entraram, e o Founder por que o credito acabou.
            frase_fc = frase_humana_do_firecrawl(getattr(site, "motivo_firecrawl", None))
            if frase_fc:
                resultado.avisos.append(frase_fc)

        # ---- 2.b O SITE E LIDO (SPEC-098 U1.1) -----------------------------
        # 📊 Ate 06/09/2026 `capture.py` tinha ZERO chamadas de LLM: o texto do
        # site ja estava em memoria (`SinaisWeb.texto_md`) e servia so para
        # calcular um hash. Sete colunas nunca eram propostas, e a propria
        # migration que as criou dizia que sem `tone` "ele escreve como
        # AutoBrokers, nao como a corretora".
        await self._propor_por_leitura(resultado, sinais_por_fonte, id_do_site)

        # ---- 3. logo e cor -------------------------------------------------
        await self._propor_visual(resultado, company_id, pid, site, declaradas, id_do_site)

        # ---- 4. gravar respeitando o que é humano --------------------------
        aplicados = self._aplicar(company_id, pid, resultado, protegidos)
        # O mesmo dado alimenta o cadastro da empresa. Fazer o corretor digitar
        # CNPJ e endereço duas vezes é pedir para ter duas verdades diferentes.
        self._completar_cadastro(company_id, site)
        resultado.completeness = self._completude(company_id, pid)

        # R2 — a leitura PROPOE; a corretora PUBLICA. O jeito lido do site vai
        # para `tone_proposto` e o `tone` ativo nao e tocado por captura nenhuma.
        if resultado.jeito_proposto:
            try:
                self.propor_jeito(company_id, resultado.jeito_proposto,
                                  origem="site",
                                  evidencia=resultado.jeito_evidencia)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[brand] jeito proposto nao gravado: %s",
                               type(exc).__name__)
                resultado.avisos.append(
                    "li o jeito de atender no site, mas nao consegui guardar a proposta")

        status = "captured" if aplicados else "partial"
        if not sinais_por_fonte:
            status = "failed"
        # R10 — `capture_error` e frase de gente. O erro da leitura vem primeiro
        # porque e o que explica campos que a corretora esperava ver preenchidos.
        motivos = ([resultado.erro] if resultado.erro else []) + resultado.avisos
        self.db.table("brand_profiles").update({
            "capture_status": status, "captured_at": _agora(),
            "completeness": resultado.completeness,
            "capture_error": "; ".join(motivos[:3]) or None,
            "updated_at": _agora(),
        }).eq("id", pid).execute()
        resultado.status = status

        self._versionar(company_id, pid, "capture", sorted(aplicados))
        return resultado

    # ------------------------------------------------------------------
    # Propostas
    # ------------------------------------------------------------------

    def _propor_texto(self, res: ResultadoCaptura, s: SinaisWeb, sid: Optional[str]) -> None:
        def por(campo: str, valor, conf: float, detalhe: str = "") -> None:
            if valor:
                res.campos[campo] = CampoProposto(
                    valor, "website", detalhe or s.url, conf, sid)

        por("display_name", s.nome or _nome_do_titulo(s.titulo), 0.85 if s.nome else 0.55,
            "og:site_name / JSON-LD" if s.nome else "<title>")
        por("legal_name", s.legal_name, 0.90, "JSON-LD legalName")

        # `og:title` costuma ser título de SEO, não slogan. Só vira tagline se
        # parecer frase de marca: curta e sem separador de SEO.
        if s.tagline and len(s.tagline) < 90 and "|" not in s.tagline:
            por("tagline", s.tagline, 0.60, "og:title")
        elif s.descricao:
            frase = s.descricao.split(".")[0].strip()
            if 18 < len(frase) < 130:
                por("tagline", frase, 0.45, "meta description (1ª frase)")

        por("about_md", s.descricao, 0.70, "meta description")

        if s.servicos:
            res.campos["services"] = CampoProposto(
                [{"name": n, "source": "site"} for n in s.servicos],
                "website", "vocabulário de ramos no texto do site", 0.75, sid)

        contato = {}
        if s.telefones:
            contato["phones"] = s.telefones[:6]
        if s.emails:
            contato["emails"] = s.emails[:4]
        if s.endereco:
            contato["address"] = {k: v for k, v in s.endereco.items() if v}
        if s.sociais.get("whatsapp"):
            contato["whatsapp"] = s.sociais["whatsapp"]
        if contato:
            res.campos["contact"] = CampoProposto(contato, "website", s.url, 0.80, sid)

        if s.endereco.get("cidade"):
            uf = s.endereco.get("uf") or ""
            por("service_area", f"{s.endereco['cidade']}{' - ' + uf if uf else ''}",
                0.70, "JSON-LD address")

        for rede in ("instagram", "linkedin", "facebook"):
            if s.sociais.get(rede):
                res.campos[f"{rede}_url"] = CampoProposto(
                    s.sociais[rede], "website", "link no rodapé/cabeçalho", 0.85, sid)

    async def _propor_visual(self, res: ResultadoCaptura, company_id: str, pid: str,
                             s: Optional[SinaisWeb], allowlist: list[str],
                             sid: Optional[str]) -> None:
        """Baixa candidatos a logo, mede a tinta e monta o sistema de design."""
        analise = None
        origem_logo = ""
        asset_id = None

        candidatos: list[str] = []
        if s:
            candidatos = list(dict.fromkeys(s.logo_urls + s.icon_urls[:2]
                                            + ([s.og_image] if s.og_image else [])))

        for url in candidatos[:5]:
            try:
                dados, mime = await baixar_binario(url, allowlist=allowlist + [url])
            except Exception as exc:  # noqa: BLE001
                res.avisos.append(f"logo {type(exc).__name__}")
                continue
            if not dados:
                continue
            a = analisar_logo(dados, mime)
            if not a or not a.ink_colors:
                continue

            gravado = (self.db.table("brand_assets").upsert({
                "company_id": company_id,
                "kind": "logo_primary" if a.primary and not analise else "symbol",
                "storage_ref": url,          # SPEC-057 B: reescrito ao subir p/ storage
                "mime_type": mime.split(";")[0] or None,
                "byte_size": len(dados), "width": a.width, "height": a.height,
                "has_transparency": a.has_transparency,
                "ink_colors": [c.as_dict() for c in a.ink_colors],
                "source_url": url, "source_kind": "website",
                "confidence": a.confidence, "is_current": analise is None,
            }, on_conflict="company_id,kind").execute()).data
            res.assets.append({"url": url, "confidence": a.confidence,
                               "cores": [c.hex for c in a.ink_colors[:3]]})
            if analise is None and a.confidence >= 0.4:
                analise, origem_logo = a, url
                asset_id = gravado[0]["id"] if gravado else None

        # --- decidir a cor ---------------------------------------------------
        primaria = acento = None
        conf = 0.30
        detalhe = "padrão da casa (nenhuma fonte de cor confiável)"
        origem = "default"

        if analise and analise.primary:
            primaria, acento = analise.primary, analise.accent
            conf, origem = analise.confidence, "logo_pixels"
            detalhe = f"área de tinta do logo ({origem_logo})"
        elif s and s.theme_color and parse_color(s.theme_color):
            # Declarada pelo dono para a barra do navegador. Sinal médio: é
            # escolha consciente, mas muitos temas preenchem sozinhos.
            primaria, conf, origem = s.theme_color, 0.55, "website"
            detalhe = "<meta name=theme-color>"
        else:
            css = _cores_css_confiaveis(s.cores_css if s else [])
            if css:
                primaria, conf, origem = css[0], 0.35, "website"
                acento = css[1] if len(css) > 1 else None
                detalhe = "variável CSS de marca (sinal fraco)"
                res.avisos.append(
                    "cor vinda do CSS — confira: temas prontos costumam trazer "
                    "a paleta do editor, não a da marca")

        if not primaria:
            primaria, acento = FALLBACK_PRIMARIA, FALLBACK_ACENTO

        tipografia = {}
        if s and s.fontes:
            fam = s.fontes[0]
            tipografia = {"body": f"'{fam}', system-ui, sans-serif",
                          "display": f"'{fam}', Georgia, serif", "source": "google fonts do site"}

        sistema = build_design_system(primaria, acento, typography=tipografia or None)

        res.campos["palette"] = CampoProposto(
            {"primary": sistema["primary"], "accent": sistema["accent"],
             "scales": sistema["scales"], "themes": sistema["themes"],
             "audit": sistema["audit"], "origin": origem},
            origem, detalhe, conf, sid)

        if tipografia:
            res.campos["typography"] = CampoProposto(
                sistema["typography"], "website",
                f"Google Fonts declarada no site ({s.fontes[0]})", 0.75, sid)
        else:
            res.campos["typography"] = CampoProposto(
                sistema["typography"], "default", "tipografia padrão da casa", 0.30, sid)

        if asset_id:
            res.campos["logo_asset_id"] = CampoProposto(
                asset_id, "website", origem_logo, analise.confidence if analise else 0.4, sid)

    # ------------------------------------------------------------------
    # Gravação
    # ------------------------------------------------------------------

    def _aplicar(self, company_id: str, pid: str, res: ResultadoCaptura,
                 protegidos: set[str]) -> set[str]:
        patch: dict[str, Any] = {}
        aplicados: set[str] = set()

        for campo, proposto in res.campos.items():
            if campo in protegidos:
                continue
            # 🔴 D21/U1.4 — PROCEDENCIA SO DE CAMPO COM VALOR.
            # 📊 Medido em 06/09/2026: duas das 14 procedencias da unica marca
            # publicada (`susep_code`, `service_area`) apontavam para colunas
            # NULL. A tela dizia "informado pelo corretor" ao lado de um campo
            # vazio: uma origem para um valor que nao existe e mentira, e ela
            # some da tela sozinha assim que o campo deixa de ser gravado.
            if _valor_vazio(proposto.valor):
                continue
            patch[campo] = proposto.valor
            aplicados.add(campo)

            self.db.table("brand_field_provenance").upsert({
                "company_id": company_id, "brand_profile_id": pid,
                "field_path": campo, "source_id": proposto.source_id,
                "source_kind": _PROCEDENCIA_NO_BANCO.get(
                    proposto.source_kind, proposto.source_kind),
                "source_detail": proposto.source_detail[:500],
                "confidence": round(min(max(proposto.confidence, 0.0), 1.0), 2),
                "human_edited": False, "captured_at": _agora(),
            }, on_conflict="brand_profile_id,field_path").execute()

        if patch:
            patch["updated_at"] = _agora()
            self.db.table("brand_profiles").update(patch).eq("id", pid).execute()
        return aplicados

    def _completar_cadastro(self, company_id: str, s: Optional[SinaisWeb]) -> list[str]:
        """Preenche `companies` com o que o site revelou — **só o que está vazio**.

        A regra de só-preencher-vazio não é cautela: o cadastro é o que o
        corretor conferiu e assinou. Um telefone extraído de rodapé de site
        sobrescrevendo o telefone que ele digitou seria trocar dado verificado
        por dado inferido, e ninguém perceberia até um cliente ligar no número
        errado.
        """
        if not s:
            return []

        atual = (self.db.table("companies").select(
            "company_name, legal_name, cnpj, primary_contact_phone, "
            "primary_contact_email, cep, street, number, neighborhood, city, state"
        ).eq("id", company_id).maybe_single().execute()).data or {}

        end = s.endereco or {}
        candidatos = {
            "company_name": s.nome or _nome_do_titulo(s.titulo),
            "legal_name": s.legal_name,
            "cnpj": s.cnpj,
            "primary_contact_phone": (s.telefones or [None])[0],
            "primary_contact_email": (s.emails or [None])[0],
            "cep": end.get("cep"),
            "street": end.get("logradouro"),
            "neighborhood": end.get("bairro"),
            "city": end.get("cidade"),
            "state": end.get("uf"),
        }

        patch = {k: v for k, v in candidatos.items()
                 if v and not (atual.get(k) or "").strip()}
        if not patch:
            return []

        try:
            self.db.table("companies").update(patch).eq("id", company_id).execute()
            logger.info("[brand] cadastro complementado: %s", sorted(patch))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] cadastro nao complementado: %s", type(exc).__name__)
            return []
        return sorted(patch.keys())

    def _completude(self, company_id: str, pid: str) -> float:
        """Quanto da identidade está de pé. Vira barra de progresso e gate.

        Peso por impacto na peça entregue: sem logo e sem cor, toda saída fica
        genérica — então esses dois valem mais que o resto somado.
        """
        p = (self.db.table("brand_profiles").select("*").eq("id", pid)
             .maybe_single().execute()).data or {}
        pesos = {
            "logo_asset_id": 0.26,
            "palette": 0.24,
            "display_name": 0.10,
            "about_md": 0.09,
            "services": 0.09,
            "contact": 0.08,
            "tagline": 0.06,
            "typography": 0.05,
            "website_url": 0.03,
        }
        total = 0.0
        for campo, peso in pesos.items():
            v = p.get(campo)
            if campo == "palette":
                if isinstance(v, dict) and v.get("primary"):
                    total += peso
            elif isinstance(v, (list, dict)):
                if v:
                    total += peso
            elif v:
                total += peso
        return round(min(total, 1.0), 2)

    def _versionar(self, company_id: str, pid: str, motivo: str,
                   campos: list[str]) -> None:
        atual = (self.db.table("brand_profiles").select("*").eq("id", pid)
                 .maybe_single().execute()).data or {}
        r = (self.db.table("brand_profile_versions").select("version")
             .eq("brand_profile_id", pid).order("version", desc=True)
             .limit(1).execute())
        proxima = ((r.data or [{}])[0].get("version") or 0) + 1
        try:
            self.db.table("brand_profile_versions").insert({
                "company_id": company_id, "brand_profile_id": pid,
                "version": proxima, "snapshot": atual, "reason": motivo,
                "changed_fields": campos,
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] versao nao gravada: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Edição humana
    # ------------------------------------------------------------------

    def editar(self, company_id: str, campos: dict[str, Any],
               user_id: Optional[str] = None) -> dict:
        """Grava edição do corretor e marca os campos como protegidos."""
        perfil = self.obter_ou_criar(company_id)
        pid = perfil["id"]

        patch = {k: v for k, v in campos.items() if k not in ("id", "company_id")}
        if "palette" in patch and isinstance(patch["palette"], dict):
            # Cor escolhida à mão também precisa de sistema completo e de
            # contraste conferido — senão a edição manual vira o caminho fácil
            # para gerar peça ilegível.
            sistema = build_design_system(
                patch["palette"].get("primary"), patch["palette"].get("accent"),
                typography=patch.get("typography") or perfil.get("typography"))
            patch["palette"] = {
                "primary": sistema["primary"], "accent": sistema["accent"],
                "scales": sistema["scales"], "themes": sistema["themes"],
                "audit": sistema["audit"], "origin": "human",
            }

        patch["updated_at"] = _agora()
        patch["updated_by"] = user_id
        if perfil.get("capture_status") == "empty":
            patch["capture_status"] = "manual"
        self.db.table("brand_profiles").update(patch).eq("id", pid).execute()

        agora = _agora()
        for campo in patch:
            if campo in ("updated_at", "updated_by", "capture_status"):
                continue
            self.db.table("brand_field_provenance").upsert({
                "company_id": company_id, "brand_profile_id": pid,
                "field_path": campo, "source_kind": "human",
                "source_detail": "editado no painel da corretora",
                "confidence": 1.0, "human_edited": True,
                "human_edited_at": agora, "human_edited_by": user_id,
                "captured_at": agora,
            }, on_conflict="brand_profile_id,field_path").execute()

        completude = self._completude(company_id, pid)
        self.db.table("brand_profiles").update(
            {"completeness": completude}).eq("id", pid).execute()
        self._versionar(company_id, pid, "human_edit", sorted(patch.keys()))

        return (self.db.table("brand_profiles").select("*").eq("id", pid)
                .maybe_single().execute()).data or {}

    # ==================================================================
    # SPEC-098 U1.1 — O SITE E LIDO
    # ==================================================================

    def _llm_de_marca(self, company_id: str):
        """O modelo da leitura de marca, com o custo no nome certo (R12).

        SPEC-116 U8: o modelo e o da ROTA `brand_capture` (`llm_papeis`);
        `BRAND_CAPTURE_PROVIDER/_MODEL` ficam IGNORADOS. A chave e a do
        provedor resolvido (a fabrica escolhe). `service_type="brand_capture"`
        continua — sem ele o gasto entraria no ledger como conversa.
        """
        try:
            from app.factories.llm_factory import LLMFactory

            return LLMFactory.create_llm(
                company_config={}, agent_data={},
                company_id=str(company_id) if company_id else None,
                agent_id=None,
                service_type=SERVICE_TYPE_MARCA,
                papel="brand_capture",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] modelo de leitura indisponivel: %s",
                           type(exc).__name__)
            return None

    async def _propor_por_leitura(self, resultado: ResultadoCaptura,
                                  sinais_por_fonte: dict, sid: Optional[str],
                                  *, llm=None) -> Optional[dict]:
        """UMA chamada de modelo sobre o texto ja baixado. SPEC-098 U1.1/R12.

        ⚠️ O dublê de teste precisa expor `ainvoke` (esta funcao roda dentro da
        captura, que e async). A irma que le CONVERSAS usa `invoke` — sao dois
        caminhos com relogios diferentes, e o dublê tem de ser o do caminho.

        🔴 Controle escrito no proprio codigo: resposta que nao vira
        `LeituraDoSite` NAO grava campo nenhum e deixa `resultado.erro` em
        portugues. "O modelo falhou" nunca pode virar "a corretora nao tem
        missao".
        """
        texto = _texto_para_leitura(sinais_por_fonte)
        if not texto.strip():
            return None

        modelo = llm if llm is not None else self._llm_de_marca(resultado.company_id)
        if modelo is None:
            resultado.avisos.append(
                "nao consegui ler o conteudo do site desta vez — os dados "
                "visuais foram capturados normalmente")
            return None

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            bruto = await modelo.ainvoke([
                SystemMessage(content=SISTEMA_DA_LEITURA),
                HumanMessage(content=texto),
            ])
            lido = LeituraDoSite.model_validate(_json_do_texto(_texto_da_resposta(bruto)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] leitura do site falhou: %s", type(exc).__name__)
            resultado.erro = ("nao consegui entender o conteudo do site — "
                              "nada foi alterado na identidade")
            return None

        detalhe = "proposto pela leitura do site"

        def por(campo: str, valor: Any, conf: float = 0.60) -> None:
            if _valor_vazio(valor):
                return
            resultado.campos[campo] = CampoProposto(
                valor, LEITURA_DO_SITE, detalhe, conf, sid)

        por("mission", (lido.mission or "").strip())
        por("about_md", (lido.about_md or "").strip(), 0.55)
        por("tagline", (lido.tagline or "").strip(), 0.55)
        por("service_area", (lido.service_area or "").strip(), 0.60)
        por("differentiators", [d.strip() for d in lido.differentiators if d and d.strip()][:8])
        por("insurers", [i.strip() for i in lido.insurers if i and i.strip()][:20], 0.55)

        servicos = []
        for item in lido.services[:24]:
            nome = (item.name or "").strip()
            if not nome:
                continue
            linha = {"name": nome, "source": "leitura_do_site"}
            if item.description:
                linha["description"] = item.description.strip()[:220]
            if item.audience:
                linha["audience"] = item.audience.strip()[:120]
            servicos.append(linha)
        por("services", servicos, 0.65)

        ano = lido.founded_year
        if isinstance(ano, int) and 1800 < ano <= datetime.now(timezone.utc).year:
            por("founded_year", ano, 0.70)

        susep = _susep_confiavel(lido.susep_code, texto)
        if susep:
            por("susep_code", susep, 0.80)
        elif lido.susep_code:
            resultado.avisos.append(
                "encontrei um numero que poderia ser o registro SUSEP, mas nao "
                "consegui confirmar no texto do site — confira e preencha a mao")

        # O JEITO nao entra em `campos`: ele nao e Facts (R1) e nao vira `tone`
        # por captura (R2). Fica na proposta, e a corretora aprova.
        if lido.tone_proposto is not None:
            try:
                jeito = validar_jeito(lido.tone_proposto.model_dump())
            except ValueError as exc:
                logger.info("[brand] jeito lido fora do enum: %s", exc)
                jeito = {}
            if not jeito_vazio(jeito):
                resultado.jeito_proposto = jeito
                teto_n, teto_c = TETO_EVIDENCIA
                resultado.jeito_evidencia = [
                    str(f).strip()[:teto_c]
                    for f in (lido.tone_proposto.evidencia or [])[:teto_n]
                    if str(f).strip()
                ]

        return {"campos": sorted(resultado.campos.keys()),
                "jeito": bool(resultado.jeito_proposto)}

    # ==================================================================
    # SPEC-098 U2.2 — O JEITO DE ATENDER: propor e aprovar
    # ==================================================================

    def propor_jeito(self, company_id: str, jeito: Any, origem: str,
                     evidencia: Any = None) -> dict:
        """Grava UMA proposta. 🔴 NUNCA toca em `tone` (R2).

        A separacao nao e burocracia: o jeito chega ao SEGURADO pelo prompt do
        agente. Publicar em silencio o que um modelo inferiu de um site seria
        colocar palavras na boca da corretora sem ela ter lido.
        """
        validado = validar_jeito(jeito)
        if jeito_vazio(validado):
            raise ValueError("a proposta esta vazia — nada a guardar")

        origem_norm = ORIGENS_DA_PROPOSTA.get(str(origem or "").strip())
        if not origem_norm:
            raise ValueError(
                "origem invalida: use site, conversas ou administrador")

        perfil = self.obter_ou_criar(company_id)
        pid = perfil["id"]

        # ⚠️ O patch e EXPLICITO e curto de proposito. Um `update(**tudo)` aqui
        # deixaria a mutacao M3 (gravar direto em `tone`) passar despercebida.
        self.db.table("brand_profiles").update({
            "tone_proposto": validado,
            "tone_proposto_origem": origem_norm,
            "tone_proposto_em": _agora(),
            "tone_evidencia": _evidencia_gravavel(evidencia),
            "updated_at": _agora(),
        }).eq("id", pid).execute()

        return {"ok": True, "jeito": validado, "origem": origem_norm,
                "evidencia": _evidencia_gravavel(evidencia)}

    def aprovar_jeito(self, company_id: str, user_id: Optional[str] = None,
                      ajustes: Optional[dict] = None) -> dict:
        """A corretora PUBLICA: a proposta vira `tone`, versionada (R2).

        A autorizacao de quem pode fazer isto e do BFF (`requireCompanyMember
        ({write:true})`): aqui dentro so se confere a chave interna, como em
        todas as rotas deste router. Confiar que o chamador validou e como se
        perde isolamento — por isso a rota do Next e que exige o papel.
        """
        perfil = self.obter_ou_criar(company_id)
        pid = perfil["id"]

        base = perfil.get("tone_proposto") or {}
        if ajustes:
            base = {**(base if isinstance(base, dict) else {}), **ajustes}
        validado = validar_jeito(base)
        if jeito_vazio(validado):
            raise ValueError("nao ha proposta para aprovar")

        self.db.table("brand_profiles").update({
            "tone": validado,
            "tone_proposto": None,
            "tone_proposto_origem": None,
            "tone_proposto_em": None,
            "updated_at": _agora(),
            "updated_by": user_id,
        }).eq("id", pid).execute()

        # A aprovacao E edicao humana: recaptura nenhuma sobrescreve o jeito.
        agora = _agora()
        try:
            self.db.table("brand_field_provenance").upsert({
                "company_id": company_id, "brand_profile_id": pid,
                "field_path": "tone", "source_kind": "human",
                "source_detail": "jeito de atender aprovado no painel da corretora",
                "confidence": 1.0, "human_edited": True,
                "human_edited_at": agora, "human_edited_by": user_id,
                "captured_at": agora,
            }, on_conflict="brand_profile_id,field_path").execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] procedencia do jeito nao gravada: %s",
                           type(exc).__name__)

        # 🔴 DEPOIS do update: `_versionar` fotografa a linha COMO ELA ESTA. Antes,
        # a versao guardaria o jeito ANTIGO com o nome do novo.
        self._versionar(company_id, pid, "human_edit", ["tone"])  # o CHECK de brand_profile_versions.reason so aceita capture|human_edit|recapture|revert|seed (canario vivo 06/09); a aprovacao pela administradora E uma edicao humana, e changed_fields=["tone"] a distingue
        return {"ok": True, "tone": validado}

    # ==================================================================
    # SPEC-098 U2.3 — o jeito que nasce das CONVERSAS REAIS
    # ==================================================================

    def _corpus_de_atendimento(self, company_id: str,
                               amostra: int) -> tuple[list, list, int, int]:
        """As saidas HUMANAS da corretora no WhatsApp, ja filtradas pela R11.

        ⚠️ `messages` nao tem `channel` nem `company_id` (📊 06/09/2026): os dois
        vem de `conversations`. Ler `messages` sozinha traria mensagem de outra
        corretora — e o filtro por corretora no codigo e a unica cerca que
        existe aqui (CLAUDE.md §7: `policies=0` nestas tabelas).
        """
        # Import local de proposito: `pos_acionamento` puxa o mundo do
        # atendimento, e `capture.py` e importada por `app.main` pela rota de
        # marca. Um import de topo aqui custaria esse mundo em TODA subida.
        from app.atendimento.pos_acionamento import e_atendimento_de_seguro

        conversas = (self.db.table("conversations")
                     .select("id")
                     .eq("company_id", company_id)
                     .eq("channel", "whatsapp")
                     .order("created_at", desc=True)
                     .limit(600).execute()).data or []
        ids = [str(c["id"]) for c in conversas]
        if not ids:
            return [], [], 0, 0

        linhas: list[dict] = []
        # PostgREST tem teto de tamanho de URL: o `in` vai em blocos.
        for i in range(0, len(ids), 60):
            bloco = ids[i:i + 60]
            r = (self.db.table("messages")
                 .select("conversation_id, content, created_at")
                 .in_("conversation_id", bloco)
                 .eq("role", "assistant")
                 .eq("payload->>origem", "espelho")
                 .order("created_at", desc=True)
                 .limit(amostra).execute())
            linhas.extend(r.data or [])
            if len(linhas) >= amostra:
                break

        por_conversa: dict[str, list[tuple]] = {}
        for m in linhas[:amostra]:
            texto = str(m.get("content") or "").strip()
            if texto:
                por_conversa.setdefault(str(m.get("conversation_id")), []).append(
                    (str(m.get("created_at") or ""), texto))

        mantidas: list[str] = []
        aberturas: list[str] = []
        lidas = descartadas = 0
        for _cid, pares in por_conversa.items():
            # 🔴 A CONSULTA VEM EM ORDEM DECRESCENTE. A "abertura" e a mensagem
            # mais ANTIGA da conversa; pegar a primeira da lista mediria a
            # DESPEDIDA e chamaria isso de saudacao.
            textos = [t for _dt, t in sorted(pares, key=lambda x: x[0])]
            lidas += 1
            # R11 (097.1) — conversa pessoal ou entre colegas NUNCA vira jeito de
            # atender, e e CONTADA. 📊 O acervo tem as duas coisas: um filho com
            # "kkkkk" e um convite para o fim de semana.
            if not e_atendimento_de_seguro({"mensagens": textos}):
                descartadas += 1
                continue
            mantidas.extend(textos)
            aberturas.append(textos[0])
        return mantidas, aberturas, lidas, descartadas

    def propor_jeito_das_conversas(self, company_id: str, amostra: int = 300,
                                   *, llm=None) -> dict:
        """O jeito que a corretora JA TEM, medido no que ela escreveu.

        ⚠️ O dublê de teste aqui expoe `invoke` (sincrono): esta funcao roda em
        script e em rota sincrona, e a chamada de modelo e OPCIONAL — com
        `llm=None` sai so a estatistica, que e deterministica e publicada em
        `escolhas_das_taxas`.

        📊 O que sustenta a regra: Resulta abre afetiva, com emoji e em primeira
        pessoa; AutoFleet trata por Sr/Sra, sem emoji, explicando procedimento.
        As duas sao a mesma empresa-mae e o mesmo produto — o que difere e o
        acervo, e e por isso que o jeito NAO pode ser um padrao da casa.
        """
        mantidas, aberturas, lidas, descartadas = self._corpus_de_atendimento(
            company_id, amostra)
        if not mantidas:
            return {"ok": False,
                    "motivo": "ainda nao ha conversas suficientes para aprender",
                    "lidas": lidas, "descartadas": descartadas}

        taxas = medir_taxas(mantidas, aberturas)
        jeito = validar_jeito(escolhas_das_taxas(taxas))

        if llm is not None:
            listas = self._listas_por_modelo(mantidas, llm)
            if listas:
                jeito = validar_jeito({**jeito, **listas})

        evidencia = {
            "taxas": taxas,
            "resumo": ("lidas %d conversas, descartadas %d por serem pessoais"
                       % (lidas, descartadas)),
            "mensagens": len(mantidas),
        }
        return {"ok": True, "jeito": jeito, "evidencia": evidencia,
                "lidas": lidas, "descartadas": descartadas}

    def _listas_por_modelo(self, mantidas: list[str], llm) -> dict:
        """Principios/termos/evitar a partir de ate 60 trechos ANONIMIZADOS."""
        trechos = [anonimizar(t) for t in mantidas[:60]]
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            bruto = llm.invoke([
                SystemMessage(content=SISTEMA_DAS_CONVERSAS),
                HumanMessage(content="\n---\n".join(trechos)[:TETO_ENTRADA_LEITURA]),
            ])
            lido = _json_do_texto(_texto_da_resposta(bruto))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] leitura das conversas falhou: %s",
                           type(exc).__name__)
            return {}
        return {k: lido.get(k) or []
                for k in ("principios", "termos_preferidos", "evitar")
                if lido.get(k)}

    # ==================================================================
    # SPEC-098 U3 — os blocos que o agente recebe
    # ==================================================================

    def render_blocos_do_prompt(self, company_id: str) -> tuple[str, str]:
        """`(A CORRETORA, O JEITO)` prontos para `build_composite_prompt`.

        🔴 `except -> ("", "")`: o prompt NUNCA morre por falha de marca. Um
        agente que fala como AutoBrokers e um defeito; um agente que nao
        responde porque `brand_profiles` esta fora do ar e uma queda.
        """
        try:
            perfil = (self.db.table("brand_profiles")
                      .select("display_name, services, insurers, service_area, "
                              "founded_year, tone")
                      .eq("company_id", company_id).limit(1).execute()).data or []
            perfil = perfil[0] if perfil else {}
            empresa = (self.db.table("companies")
                       .select("company_name, legal_name")
                       .eq("id", company_id).limit(1).execute()).data or []
            empresa = empresa[0] if empresa else {}

            facts = render_corretora(empresa, perfil)
            try:
                jeito = render_jeito(validar_jeito(perfil.get("tone") or {}))
            except Exception:  # noqa: BLE001 — jeito guardado invalido nao cala o agente
                jeito = ""
            return facts, jeito
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] blocos do prompt indisponiveis: %s",
                           type(exc).__name__)
            return "", ""

    # ------------------------------------------------------------------
    # Leitura para uso nas peças
    # ------------------------------------------------------------------

    def snapshot_para_artefato(self, company_id: str) -> dict:
        """A marca no formato que o renderizador congela dentro da versão.

        Sempre devolve algo utilizável: sem perfil, a peça sai com a identidade
        padrão em vez de sair quebrada. O que ela nunca faz é sair sem marca
        nenhuma — o `CHECK` do banco recusaria publicar.
        """
        p = (self.db.table("brand_profiles").select("*")
             .eq("company_id", company_id).maybe_single().execute()).data
        if not p or not (p.get("palette") or {}).get("primary"):
            sistema = build_design_system(FALLBACK_PRIMARIA, FALLBACK_ACENTO)
            nome = (p or {}).get("display_name") or "Corretora"
            return {"name": nome, "palette": sistema, "logo": None,
                    "visual_style": "aurora", "is_fallback": True}

        logo = None
        if p.get("logo_asset_id"):
            a = (self.db.table("brand_assets")
                 .select("storage_ref, width, height, has_transparency, mime_type")
                 .eq("id", p["logo_asset_id"]).maybe_single().execute()).data
            if a:
                logo = a

        # SPEC-098 U1.3 — a peca carrega a VOZ, nao so a cor.
        # 📊 Ate 06/09/2026 esta funcao entregava 11 chaves e nenhuma delas
        # dizia uma palavra sobre quem a corretora e ou como ela fala: a unica
        # saida da identidade para pecas saia sem missao, sem ramos, sem
        # seguradoras e sem jeito.
        try:
            jeito = render_jeito(validar_jeito(p.get("tone") or {}))
        except Exception:  # noqa: BLE001 — jeito invalido nao quebra a peca
            jeito = ""

        return {
            "name": p.get("display_name") or "Corretora",
            "legal_name": p.get("legal_name"),
            "tagline": p.get("tagline"),
            "palette": p.get("palette") or {},
            "typography": p.get("typography") or {},
            "logo": logo,
            "contact": p.get("contact") or {},
            "visual_style": p.get("visual_style") or "aurora",
            "susep_code": p.get("susep_code"),
            "captured_at": p.get("captured_at"),
            "mission": p.get("mission"),
            "services": p.get("services") or [],
            "insurers": p.get("insurers") or [],
            "service_area": p.get("service_area"),
            "founded_year": p.get("founded_year"),
            "jeito": jeito,
            "is_fallback": False,
        }


# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------

def _valor_vazio(valor: Any) -> bool:
    """Mede CONTEUDO, nao presenca — o mesmo criterio de `jeito_de_atender.vazio`.

    `""`, `[]`, `{}` e `None` sao a mesma coisa para a tela: campo em branco. O
    que nao pode acontecer e uma procedencia nascer ao lado de qualquer um deles.
    """
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, tuple, dict, set)):
        return len(valor) == 0
    return False


def _nome_do_titulo(titulo: Optional[str]) -> Optional[str]:
    """`<title>` de site costuma ser 'Frase de SEO | Nome'. O nome fica no fim."""
    if not titulo:
        return None
    partes = [p.strip() for p in re.split(r"[|\-–—·]", titulo) if p.strip()]
    if not partes:
        return None
    return min(partes[-1:] + partes[:1], key=len)[:120]


