"""
Agent Config API - Endpoints para configurar o agente LLM de cada empresa
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, validator

from app.core.auth import require_internal_key
from app.core import get_supabase_client
from app.services.encryption_service import get_encryption_service
from app.services.portao_do_prompt import (
    PERSONALIZACAO_MINIMA_CHARS,
    conferir_prompt_gravado,
    problemas_da_escrita_de_prompt,
)
from app.factories import model_policy as MP

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# 🔴 SPEC-098 U4.a/R7 — A CHAVE DO BFF (o buraco que este arquivo era)
# =============================================================================
#
# 📊 Medido em 06/09/2026, ao vivo, contra o smith-api em produção:
#
#     GET …/api/sanitization/jobs?company_id=<uuid falso>   → 200
#     GET …/api/mcp/servers?company_id=<uuid falso>         → 200
#
# 📊 E `grep -c 'Depends(\|_require_internal_key\|_autorizar'` neste arquivo,
# antes desta linha existir: **0**. O `company_id` chegava de fora e era usado
# como se fosse credencial.
#
# ⚠️ O comentário que existia aqui — *"company_id is provided by the Next.js
# proxy after session validation"* — descrevia uma INTENÇÃO. Nada verificava que
# o chamador era o proxy. Comentário não é guarda; `Depends` é.
#
# 🔴 ORDEM DE IMPLANTAÇÃO (R7): **smith-web primeiro, smith-api depois.** A web
# passa a MANDAR `X-Internal-Key`; a api passa a EXIGIR. Na ordem inversa, o
# painel fica 401 até a web subir.



# =============================================================================
# 🔴 SPEC-116 U10 — A TELA ESCOLHE NO CATÁLOGO, E SÓ NELE
# =============================================================================
#
# 📊 Antes (EVIDENCIAS/01 §d, fontes #1–#3): a lista que a tela oferecia era
# `LLM_MODEL_OPTIONS` escrita à mão no TSX ("Dezembro 2025", sem Claude 5), o
# dropdown de visão oferecia o Claude 3.5 Sonnet de 20240620 (RETIRADO da API) e
# esta validação consultava uma TERCEIRA lista (`SUPPORTED_PROVIDERS` de
# langchain_service.py). Três catálogos, nenhum deles o governado.
#
# Agora os três leem UM: `model_policy.catalogo()` (= `llm_pricing` expandido,
# com o snapshot versionado quando o banco não responde). Regras de ESCOLHA:
#
#     APPROVED · CANDIDATE     → pode ser escolhido
#     DEPRECATED               → só permanece se JÁ está gravado (aparece como
#                                "legado"); nunca é escolha nova (D-116-11)
#     BLOCKED · HISTORICAL     → nunca
#     fora do catálogo         → nunca
#
# E o papel do agente manda: para o chat principal e o atendimento, o modelo é o
# da ROTA do papel (`llm_papeis`, D-116-03) — a tela mostra o efetivo, não
# oferece um seletor que não decide nada.

LIFECYCLES_ESCOLHIVEIS = ("APPROVED", "CANDIDATE")

#: como o ciclo de vida aparece para gente (a tela nunca mostra o código cru)
ROTULO_DO_CICLO = {
    "APPROVED": "aprovado",
    "CANDIDATE": "em avaliação",
    "DEPRECATED": "legado — em saída",
    "BLOCKED": "bloqueado",
    "HISTORICAL": "retirado",
}

NOME_DO_PROVEDOR = {
    "openai": "OpenAI (GPT)",
    "anthropic": "Anthropic (Claude)",
    "google": "Google (Gemini)",
    "openrouter": "OpenRouter (laboratório)",
    "xai": "xAI (Grok) — laboratório",
    "xiaomi": "Xiaomi (MiMo) — laboratório",
    "deepseek": "DeepSeek — laboratório",
    "zai": "Z.ai (GLM) — laboratório",
    "cohere": "Cohere",
    "groq": "Groq",
    "mistral": "Mistral",
}

#: a FUNÇÃO do agente (coluna `agent_role`) → o PAPEL que a rota conhece.
#: Não é uma segunda regra: é `model_policy.papel_do_agente` aplicado às
#: funções que existem, para a tela não precisar reimplementá-lo.
FUNCOES_DO_AGENTE = ("core", "attendance", "subagent")


class ModeloRecusado(ValueError):
    """Escolha de modelo que o catálogo não permite — a mensagem é para gente."""


def validar_modelo_escolhido(
    provider: Optional[str], model: Optional[str], gravado_atual: Optional[str] = None,
    *, tipo: str = "chat",
) -> None:
    """Recusa, com mensagem humana, o modelo que não pode ser ESCOLHIDO.

    `gravado_atual` é o que já está na linha: um DEPRECATED que já está lá pode
    ser mantido (a tela o mostra como legado), mas não pode ser escolhido de novo.
    """
    if not model:
        raise ModeloRecusado("Escolha um modelo da lista.")
    linha = MP.catalogo().get(model)
    if linha is None:
        raise ModeloRecusado(
            f"O modelo '{model}' não está no catálogo de modelos aprovados da plataforma "
            "e não pode ser usado. Escolha um da lista.")
    prov = linha.get("provider")
    if provider and provider != prov:
        raise ModeloRecusado(f"O modelo '{model}' é do provedor '{prov}', não de '{provider}'.")
    if tipo and linha.get("tipo") not in (None, tipo):
        raise ModeloRecusado(f"O modelo '{model}' não serve para esta função.")
    ciclo = linha.get("lifecycle")
    if ciclo in LIFECYCLES_ESCOLHIVEIS:
        return
    if ciclo == "DEPRECATED" and gravado_atual and model == gravado_atual:
        return  # legado que já estava gravado: mantém, não oferece
    sucessor = linha.get("substituido_por")
    dica = f" Use '{sucessor}' ou outro modelo aprovado." if sucessor else " Escolha um modelo aprovado."
    if ciclo == "DEPRECATED":
        raise ModeloRecusado(
            f"O modelo '{model}' está em saída (legado) e não pode ser escolhido para configurações novas.{dica}")
    raise ModeloRecusado(
        f"O modelo '{model}' foi {ROTULO_DO_CICLO.get(ciclo, 'bloqueado')} pela plataforma e não pode ser usado.{dica}")


def _exibicao_do_catalogo() -> Dict[str, dict]:
    """Nome de exibição e preço por modelo — só para MOSTRAR, nunca para decidir.

    Lê o mesmo `llm_pricing` (o catálogo); sem banco, o snapshot gerado dele.
    """
    colunas = "model_name,display_name,input_price_per_million,output_price_per_million"
    try:
        dados = get_supabase_client().client.table("llm_pricing").select(colunas).execute().data or []
        if dados:
            return {r["model_name"]: r for r in dados}
    except Exception as e:  # noqa: BLE001 — só exibição
        logger.warning("[agent_config] exibição do catálogo sem banco (%s): usando snapshot", type(e).__name__)
    try:
        import json

        doc = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return dict(doc.get("catalogo") or {})
    except Exception:  # noqa: BLE001
        return {}


def _modelo_para_tela(nome: str, linha: dict, exib: dict) -> dict:
    ciclo = linha.get("lifecycle")
    e = exib.get(nome) or {}
    return {
        "id": nome,
        "display_name": e.get("display_name") or nome,
        "provider": linha.get("provider"),
        "tipo": linha.get("tipo"),
        "lifecycle": ciclo,
        "lifecycle_rotulo": ROTULO_DO_CICLO.get(ciclo, "desconhecido"),
        "escolhivel": ciclo in LIFECYCLES_ESCOLHIVEIS,
        "legado": ciclo == "DEPRECATED",
        "classes_de_dado": sorted(linha.get("classes_de_dado") or []),
        "preco_entrada_por_milhao": e.get("input_price_per_million"),
        "preco_saida_por_milhao": e.get("output_price_per_million"),
        "substituido_por": linha.get("substituido_por"),
        "sem_temperatura": (linha.get("capacidades") or {}).get("sampling_ok") is False,
        "niveis_de_esforco": (linha.get("capacidades") or {}).get("niveis_de_esforco"),
    }


def modelos_da_tela(tipo: str = "chat") -> List[dict]:
    """O catálogo que a tela lista: nunca BLOCKED/HISTORICAL; DEPRECATED como legado."""
    exib = _exibicao_do_catalogo()
    out = []
    for nome, linha in sorted(MP.catalogo().items()):
        if linha.get("lifecycle") not in MP.LIFECYCLES_USAVEIS:
            continue
        if tipo and linha.get("tipo") != tipo:
            continue
        out.append(_modelo_para_tela(nome, linha, exib))
    return out


def rotas_da_tela() -> dict:
    """O modelo EFETIVO de cada papel, pelo MESMO resolvedor que a fábrica usa."""
    exib = _exibicao_do_catalogo()
    papeis: Dict[str, dict] = {}
    for papel in MP.papeis_conhecidos():
        try:
            r = MP.resolver(papel)
        except MP.ModeloNaoResolvido as e:
            papeis[papel] = {"papel": papel, "erro": str(e)}
            continue
        papeis[papel] = {
            "papel": papel,
            "provider": r.provider,
            "model": r.model,
            "display_name": (exib.get(r.model) or {}).get("display_name") or r.model,
            "effort": r.effort,
            "lifecycle": r.lifecycle,
            "lifecycle_rotulo": ROTULO_DO_CICLO.get(r.lifecycle, "desconhecido"),
            "sem_temperatura": (r.capacidades or {}).get("sampling_ok") is False,
            "reserva": ({"provider": r.reserva.provider, "model": r.reserva.model}
                        if r.reserva else None),
            "origem": r.origem,
            "versao_da_rota": r.versao_da_rota,
        }
    return {
        "papeis": papeis,
        "papel_por_funcao": {f: MP.papel_do_agente(f) for f in FUNCOES_DO_AGENTE},
        # o que decide cada função: sem funcao cadastrada = chat principal
        "papel_sem_funcao": MP.papel_do_agente(None),
    }


# ===== MODELS =====


class ModeloDoCatalogo(BaseModel):
    """Um modelo do catálogo governado, como a tela o mostra."""

    id: str
    display_name: str
    provider: Optional[str] = None
    tipo: Optional[str] = None
    lifecycle: Optional[str] = None
    lifecycle_rotulo: str = ""
    escolhivel: bool = False
    legado: bool = False
    classes_de_dado: List[str] = Field(default_factory=list)
    preco_entrada_por_milhao: Optional[float] = None
    preco_saida_por_milhao: Optional[float] = None
    substituido_por: Optional[str] = None
    sem_temperatura: bool = False
    niveis_de_esforco: Optional[List[str]] = None


class ProviderInfo(BaseModel):
    """Informações sobre um provider"""

    name: str = Field(..., description="Nome do provider (openai, anthropic, google)")
    display_name: str = Field(..., description="Nome para exibir na UI")
    models_count: int = Field(..., description="Número de modelos que podem ser ESCOLHIDOS")
    # SPEC-116 U10 — acrescentado (o formato antigo continua válido)
    modelos: List[ModeloDoCatalogo] = Field(
        default_factory=list, description="Modelos do catálogo (sem retirados/bloqueados)")


class AgentConfigRequest(BaseModel):
    """Request para salvar configuração do agente"""

    llm_provider: str = Field(..., description="Provider do LLM")
    llm_model: str = Field(..., description="Modelo do LLM")
    llm_api_key: str = Field(..., description="API Key do provider")
    llm_temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperatura (0.0 a 2.0)"
    )
    # 🔴 8192, e não 2000 (SPEC-EXTRA-001.1, BLOCO E · P-PILOTO-17).
    # 📊 09/09/2026: 10 de 95 chamadas do chat da Resulta bateram o teto do
    # banco EXATO e a resposta chegou cortada no meio de uma palavra. O piso de
    # `llm_factory.piso_de_saida` conserta o COMPORTAMENTO; este default
    # conserta o DADO — a corretora que salvar a configuração sem mexer no
    # campo grava 8192, não 2000 (CLAUDE.md §12.1: o número errado reinfecta
    # todo leitor seguinte).
    llm_max_tokens: int = Field(
        default=8192, ge=100, le=100000, description="Máximo de tokens"
    )
    llm_top_p: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Top P (0.0 a 1.0)"
    )
    llm_top_k: int = Field(default=40, ge=1, le=100, description="Top K (1 a 100)")
    llm_frequency_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency Penalty (-2.0 a 2.0)"
    )
    llm_presence_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence Penalty (-2.0 a 2.0)"
    )
    agent_system_prompt: Optional[str] = Field(
        None, description="System prompt customizado"
    )
    agent_enabled: bool = Field(default=True, description="Habilitar agente")
    use_langchain: bool = Field(
        default=True, description="Usar LangChain (true) ou N8N (false)"
    )
    allow_web_search: bool = Field(
        default=True, description="Permitir busca na web via Tavily"
    )
    allow_vision: bool = Field(
        default=False, description="Permitir análise de imagens"
    )
    vision_model: Optional[str] = Field(
        None, description="Legado: a leitura de imagem segue a rota do papel 'visao' (SPEC-116)"
    )
    vision_api_key: Optional[str] = Field(
        None, description="API Key para visão (separada da conversação)"
    )

    @validator("llm_provider")
    def validate_provider(cls, v):
        # SPEC-116 U10: a lista de provedores é a do Model Router, não a de
        # langchain_service. O MODELO é conferido no endpoint, contra o catálogo
        # e contra o que já está gravado (um legado gravado pode permanecer).
        if v not in MP.PROVEDORES_CONHECIDOS:
            raise ValueError(f"O provedor '{v}' não é conhecido pela plataforma.")
        return v


class AgentConfigResponse(BaseModel):
    """Response da configuração do agente"""

    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: float = 0.7
    # 🔴 8192 — mesma razão do request acima (SPEC-EXTRA-001.1, BLOCO E).
    llm_max_tokens: int = 8192
    llm_top_p: float = 1.0
    llm_top_k: int = 40
    llm_frequency_penalty: float = 0.0
    llm_presence_penalty: float = 0.0
    agent_system_prompt: Optional[str] = None
    agent_enabled: bool = False
    use_langchain: bool = False
    allow_web_search: bool = True
    allow_vision: bool = False  # VISION
    vision_model: Optional[str] = None  # VISION: modelo escolhido
    has_vision_api_key: bool = Field(
        default=False, description="Indica se tem API key de visão configurada"
    )
    # Não retornar API keys por segurança
    has_api_key: bool = Field(
        default=False, description="Indica se tem API key configurada"
    )


class TestConnectionRequest(BaseModel):
    """Request para testar conexão com LLM"""

    llm_provider: str
    llm_model: str
    llm_api_key: str


class TestConnectionResponse(BaseModel):
    """Response do teste de conexão"""

    success: bool
    message: str
    model_info: Optional[Dict[str, Any]] = None


# ===== ENDPOINTS =====


@router.get("/providers", response_model=List[ProviderInfo])
async def list_providers():
    """
    Lista os provedores do CATÁLOGO governado, cada um com os seus modelos de
    conversa (SPEC-116 U10). `models_count` conta só os que podem ser escolhidos.
    Retirados e bloqueados não aparecem; legados aparecem marcados.
    """
    por_provedor: Dict[str, List[dict]] = {}
    for m in modelos_da_tela("chat"):
        por_provedor.setdefault(m["provider"], []).append(m)

    providers = []
    for provider_name in sorted(por_provedor):
        modelos = por_provedor[provider_name]
        providers.append(
            ProviderInfo(
                name=provider_name,
                display_name=NOME_DO_PROVEDOR.get(provider_name, provider_name.title()),
                models_count=sum(1 for m in modelos if m["escolhivel"]),
                modelos=[ModeloDoCatalogo(**m) for m in modelos],
            )
        )
    return providers


@router.get("/models/{provider}", response_model=List[str])
async def list_models(provider: str):
    """
    Modelos de conversa que podem ser ESCOLHIDOS para um provedor — do catálogo
    governado (SPEC-116 U10), inclusive o OpenRouter (laboratório, D-116-06):
    só entra o que o catálogo cadastrou com ciclo de vida.
    """
    if provider not in MP.PROVEDORES_CONHECIDOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provedor '{provider}' não é conhecido pela plataforma",
        )
    return [m["id"] for m in modelos_da_tela("chat")
            if m["provider"] == provider and m["escolhivel"]]


@router.get("/rotas")
async def list_rotas():
    """
    O modelo EFETIVO de cada papel (chat principal, atendimento, visão, memória…),
    resolvido pelo mesmo Model Router que a fábrica usa. A tela mostra isto no
    lugar de um seletor para os papéis cuja rota decide (SPEC-116 U10, D-116-03).
    """
    return rotas_da_tela()


@router.get("/config/{company_id}", response_model=AgentConfigResponse,
            dependencies=[Depends(require_internal_key)])
async def get_agent_config(company_id: str):
    """
    Busca configuração atual do agente para uma empresa
    """
    try:
        supabase = get_supabase_client()
        company = supabase.get_company(company_id)

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {company_id} not found",
            )

        # Garantir valores default para campos que podem ser NULL
        temperature = company.get("llm_temperature")
        temperature = float(temperature) if temperature is not None else 0.7

        top_p = company.get("llm_top_p")
        top_p = float(top_p) if top_p is not None else 1.0

        frequency_penalty = company.get("llm_frequency_penalty")
        frequency_penalty = (
            float(frequency_penalty) if frequency_penalty is not None else 0.0
        )

        presence_penalty = company.get("llm_presence_penalty")
        presence_penalty = (
            float(presence_penalty) if presence_penalty is not None else 0.0
        )

        max_tokens = company.get("llm_max_tokens")
        # 🔴 8192 — o fallback da TELA da corretora (SPEC-EXTRA-001.1, BLOCO E).
        # ⚠️ Quando a coluna TEM valor, é o valor da coluna que aparece: esta
        # tela mostra o que está gravado, e é por isso que a migration
        # `20260914_06` existe. Consertar só a tela esconderia o dado errado.
        max_tokens = int(max_tokens) if max_tokens is not None else 8192

        top_k = company.get("llm_top_k")
        top_k = int(top_k) if top_k is not None else 40

        # Retornar config (sem API keys por segurança)
        return AgentConfigResponse(
            llm_provider=company.get("llm_provider"),
            llm_model=company.get("llm_model"),
            llm_temperature=temperature,
            llm_max_tokens=max_tokens,
            llm_top_p=top_p,
            llm_top_k=top_k,
            llm_frequency_penalty=frequency_penalty,
            llm_presence_penalty=presence_penalty,
            agent_system_prompt=company.get("agent_system_prompt"),
            agent_enabled=company.get("agent_enabled", False),
            use_langchain=company.get("use_langchain", False),
            allow_web_search=company.get("allow_web_search", True),
            allow_vision=company.get("allow_vision", False),
            vision_model=company.get("vision_model"),  # VISION
            has_vision_api_key=bool(company.get("vision_api_key")),
            has_api_key=bool(company.get("llm_api_key")),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch config: {str(e)}",
        ) from e


@router.put("/config/{company_id}", dependencies=[Depends(require_internal_key)])
async def save_agent_config(company_id: str, config: AgentConfigRequest):
    """
    Salva configuração do agente para uma empresa
    """
    try:
        supabase = get_supabase_client()

        # Validar que empresa existe
        company = supabase.get_company(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {company_id} not found",
            )

        # SPEC-116 U10 — o modelo é conferido contra o CATÁLOGO governado, com
        # o que já está gravado ao lado (um legado gravado pode permanecer; um
        # retirado, nunca). Recusa com a frase para gente, não com stack trace.
        try:
            validar_modelo_escolhido(
                config.llm_provider, config.llm_model, gravado_atual=company.get("llm_model"))
            if config.vision_model and config.vision_model != company.get("vision_model"):
                validar_modelo_escolhido(None, config.vision_model)
        except ModeloRecusado as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        # Preparar dados para atualizar
        update_data = {
            "llm_provider": config.llm_provider,
            "llm_model": config.llm_model,
            "llm_temperature": config.llm_temperature,
            "llm_max_tokens": config.llm_max_tokens,
            "llm_top_p": config.llm_top_p,
            "llm_top_k": config.llm_top_k,
            "llm_frequency_penalty": config.llm_frequency_penalty,
            "llm_presence_penalty": config.llm_presence_penalty,
            "agent_enabled": config.agent_enabled,
            "use_langchain": config.use_langchain,
            "allow_web_search": config.allow_web_search,
            "allow_vision": config.allow_vision,
            "vision_model": config.vision_model,  # VISION
        }

        # P-38 — A CAMADA LEGADA TAMBÉM EMUDECE, e é lida pelo runtime:
        # `backend/app/agents/nodes.py:438` monta o prompt base a partir de
        # `company_config.get("agent_system_prompt")`, e
        # `backend/app/services/prompt_effective_service.py:111` a exibe como
        # camada 2. Ela é a MESMA coluna de nome, em outra tabela.
        #
        # Havia DOIS jeitos de emudecer aqui, e o segundo era invisível:
        #
        #   a) mandar "" — string vazia por cima de um prompt que funcionava;
        #   b) OMITIR o campo — `agent_system_prompt` é Optional e o dicionário
        #      o incluía SEMPRE. Um PUT que só trocasse o modelo gravava NULL
        #      na coluna, e a empresa perdia a instrução sem ninguém pedir.
        #
        # (a) é recusado com nome próprio. (b) deixa de existir: chave ausente
        # é ausência, e ausência preserva o que está lá.
        if config.agent_system_prompt is not None:
            problemas = problemas_da_escrita_de_prompt(
                config.agent_system_prompt, minimo_chars=PERSONALIZACAO_MINIMA_CHARS
            )
            if problemas:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"prompt_invalido: {','.join(problemas)}",
                )
            update_data["agent_system_prompt"] = config.agent_system_prompt

        # Criptografar API key SOMENTE se for diferente de "UNCHANGED"
        if config.llm_api_key and config.llm_api_key != "UNCHANGED":
            encryption_service = get_encryption_service()
            encrypted_key = encryption_service.encrypt(config.llm_api_key)
            update_data["llm_api_key"] = encrypted_key
            logger.info(f"Updating LLM API key for company {company_id}")
        else:
            logger.info(f"Keeping existing LLM API key for company {company_id}")

        # Criptografar Vision API key SOMENTE se for diferente de "UNCHANGED"
        if config.vision_api_key and config.vision_api_key != "UNCHANGED":
            encryption_service = get_encryption_service()
            encrypted_vision_key = encryption_service.encrypt(config.vision_api_key)
            update_data["vision_api_key"] = encrypted_vision_key
            logger.info(f"Updating Vision API key for company {company_id}")
        else:
            logger.info(f"Keeping existing Vision API key for company {company_id}")

        result = (
            supabase.client.table("companies")
            .update(update_data)
            .eq("id", company_id)
            .execute()
        )

        if not result.data:
            raise Exception("Failed to update company config")

        # A releitura, quando o prompt foi tocado. "Gravei" é fato lido de
        # volta, não requisição enviada — e o que voltar mudo é DESLIGADO
        # (`agent_enabled=false`), nunca deixado ativo e sem instrução.
        if "agent_system_prompt" in update_data:
            conferido = conferir_prompt_gravado(
                supabase.client, company_id, company_id,
                "agent_config.save_agent_config", tabela="companies",
            )
            if not conferido.ok:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=conferido.reason or "prompt_vazio_apos_escrita",
                )

        logger.info(
            f"Agent config saved for company {company_id}: provider={config.llm_provider}, model={config.llm_model}"
        )

        return {
            "success": True,
            "message": "Agent configuration saved successfully",
            "company_id": company_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving agent config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save config: {str(e)}",
        ) from e


@router.post("/test/{company_id}", response_model=TestConnectionResponse,
             dependencies=[Depends(require_internal_key)])
async def test_llm_connection(company_id: str, test_request: TestConnectionRequest):
    """
    Testa conexão com o LLM antes de salvar
    """
    try:
        provider = test_request.llm_provider
        model = test_request.llm_model
        api_key = test_request.llm_api_key

        logger.info(f"Testing connection: provider={provider}, model={model}")

        # Criar LLM temporário para teste
        test_message = "Hello, this is a test. Reply with 'OK' if you receive this."

        if provider == "openai":
            llm = ChatOpenAI(
                model=model, temperature=0.7, max_tokens=50, openai_api_key=api_key
            )
        elif provider == "anthropic":
            llm = ChatAnthropic(
                model=model, temperature=0.7, max_tokens=50, anthropic_api_key=api_key
            )
        elif provider == "google":
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=0.7,
                max_output_tokens=50,
                google_api_key=api_key,
            )
        elif provider == "openrouter":
            from app.core.config import settings
            openrouter_key = settings.OPENROUTER_API_KEY
            if not openrouter_key:
                return TestConnectionResponse(
                    success=False,
                    message="OPENROUTER_API_KEY não configurada no .env do backend",
                    model_info=None,
                )
            llm = ChatOpenAI(
                model=model,
                temperature=0.7,
                max_tokens=50,
                api_key=openrouter_key,
                base_url=settings.OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": settings.FRONTEND_URL,
                    "X-Title": "AutoBrokers",
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {provider}",
            )

        # Testar com mensagem simples
        from langchain_core.messages import HumanMessage

        response = llm.invoke([HumanMessage(content=test_message)])

        logger.info(f"Test successful for {provider}/{model}")

        return TestConnectionResponse(
            success=True,
            message=f"Successfully connected to {provider} ({model})",
            model_info={
                "provider": provider,
                "model": model,
                "test_response": response.content[:100],  # Primeiros 100 chars
            },
        )

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return TestConnectionResponse(
            success=False, message=f"Connection failed: {str(e)}", model_info=None
        )
