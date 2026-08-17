"""
Serviço de Integração - Gerencia integrações (WhatsApp, etc) e usuários lead
"""

import hashlib
import logging
from typing import Dict, Optional

import httpx

# Tenacity for retry logic on transient failures
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from supabase import Client

from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

logger = logging.getLogger(__name__)

# Retry decorator for DB operations that may fail under load
db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException, ConnectionError, Exception)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


class IntegrationService:
    """Serviço para gerenciar integrações e identificação de usuários"""

    def __init__(self, supabase_client: Client):
        """
        Inicializa o serviço de integração

        Args:
            supabase_client: Cliente Supabase
        """
        self.supabase = supabase_client
        logger.info("Integration service initialized")

    def get_integration_by_phone(self, connected_phone: str) -> Optional[Dict]:
        """
        Busca integração pelo número conectado (connectedPhone)

        Args:
            connected_phone: Número conectado na Z-API (ex: 554499999999)

        Returns:
            Dict com dados da integração (company_id, token, instance_id, base_url) ou None
        """
        try:
            # 🧪 DRY_RUN MODE: Retorna integração fake para testes
            if settings.DRY_RUN:
                # DRY_RUN: busca integração real no banco mas não envia via Z-API
                # Isso garante que company_id e agent_id existam de verdade
                logger.info(f"[INTEGRATION] 🧪 DRY_RUN: Looking up real integration for ...{str(connected_phone)[-4:]}")
                try:
                    @db_retry
                    def _fetch_dry_run():
                        return (
                            self.supabase.table("integrations")
                            .select("*")
                            .eq("identifier", connected_phone)
                            .eq("is_active", True)
                            .limit(1)
                            .execute()
                        )
                    response = _fetch_dry_run()
                    if response.data and len(response.data) > 0:
                        integration = response.data[0]
                        # Sobrescreve token/instance pra não enviar mensagem real
                        integration["instance_id"] = "dry-run-instance"
                        integration["token"] = "dry-run-token"
                        logger.info(f"[INTEGRATION] 🧪 DRY_RUN: Found real integration for company {integration.get('company_id')}")
                        return integration
                    else:
                        logger.warning(f"[INTEGRATION] 🧪 DRY_RUN: No integration found for ...{str(connected_phone)[-4:]}")
                        return None
                except Exception as e:
                    logger.error(f"[INTEGRATION] 🧪 DRY_RUN: Error fetching integration: {e}")
                    return None

            logger.info(
                f"[INTEGRATION] Looking for integration with phone ...{str(connected_phone)[-4:]}"
            )

            # Wrap query in retry for transient failures under load
            @db_retry
            def _fetch_integration():
                return (
                    self.supabase.table("integrations")
                    .select("*")
                    .eq("identifier", connected_phone)
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

            response = _fetch_integration()

            if not response.data or len(response.data) == 0:
                logger.warning(
                    f"[INTEGRATION] No active integration found for ...{str(connected_phone)[-4:]}"
                )
                return None

            integration = response.data[0]
            logger.info(
                f"[INTEGRATION] Found integration for company {integration.get('company_id')}"
            )

            # 39A4.1: descriptografa token/client_token em memória (nunca loga valores).
            return prepare_integration_for_runtime(integration)

        except Exception as e:
            logger.error(f"[INTEGRATION] Error fetching integration: {str(e)}")
            return None

    def get_integration_by_webhook_token(self, token: str) -> Optional[Dict]:
        """SPEC-017 P1.2: resolve integração pelo HASH do token de webhook.

        Fail-closed: erro de banco propaga (o webhook responde 401/500, nunca
        processa sem tenant confirmado). Nunca loga o token cru.
        """
        from app.services.whatsapp.channel_security import webhook_token_hash

        token_hash = webhook_token_hash(token)

        @db_retry
        def _fetch_by_hash():
            return (
                self.supabase.table("integrations")
                .select("*")
                .eq("webhook_token_hash", token_hash)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )

        response = _fetch_by_hash()
        if not response.data:
            return None
        return prepare_integration_for_runtime(response.data[0])

    def get_integration_by_id(self, integration_id: str) -> Optional[Dict]:
        """SPEC-017 P1.2: resolve integração por id (rotas de token/buffer)."""
        try:
            @db_retry
            def _fetch_by_id():
                return (
                    self.supabase.table("integrations")
                    .select("*")
                    .eq("id", str(integration_id))
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

            response = _fetch_by_id()
            if not response.data:
                return None
            return prepare_integration_for_runtime(response.data[0])
        except Exception as e:  # noqa: BLE001
            logger.error(f"[INTEGRATION] Error fetching by id: {type(e).__name__}")
            return None

    # SPEC-063 Bloco D — PROIBIÇÃO, não prioridade.
    #
    # O Observador é o número que a corretora pareia para o sistema ESCUTAR as
    # conversas reais dela. Ele é mudo por construção: o módulo de captura não
    # importa nenhum cliente de envio.
    #
    # Mas os seletores de canal de SAÍDA nunca olharam `purpose`. Onde havia
    # ordenação, o observador ficava por último — e "por último" vira "o
    # escolhido" quando é o único ativo. 📊 Em 02/08/2026 Amandus e AutoFleet
    # tinham EXATAMENTE isso: só o observador ativo.
    #
    # Cobrança, follow-up e alerta sairiam pelo número que existe para ficar
    # calado. O segurado receberia mensagem de um número que nunca falou com
    # ele, e a corretora perderia o silêncio que pediu ao parear.
    #
    # Última prioridade não protege. Só a proibição protege.
    PROPOSITOS_QUE_NUNCA_ENVIAM = frozenset({"observer"})

    # SPEC-078 Bloco B — a coluna que transforma o envio numa DECISÃO da corretora.
    #
    # 🔴 POR QUE ESTA COLUNA EXISTE, e por que ela NÃO desfaz a SPEC-063 D.
    #
    # 📊 Medido em 17/08/2026: o dashboard pareia o WhatsApp da corretora com
    # `purpose='observer'` (`app/api/dashboard/whatsapp-channel/route.ts`), e
    # `observer` está na proibição acima. Consequência prática: **o número que a
    # corretora pareou literalmente não conseguia enviar o boleto.** Era essa a
    # causa de o Auxiliar de Cobrança nunca ter fechado o ciclo.
    #
    # Releia o motivo da proibição, dez linhas acima: ele fala de **surpresa** —
    # "o segurado receberia mensagem de um número que nunca falou com ele, e a
    # corretora perderia o silêncio que pediu ao parear". Não fala de envio.
    #
    # Aqui não há surpresa: a corretora clica num botão que descreve exatamente
    # o que vai sair por ali. O que continua proibido — e continua proibido POR
    # OMISSÃO, que é a parte que importa — é o sistema escolher sozinho.
    #
    # Desenhos considerados:
    #   • segunda linha `purpose='auxiliary'` para o mesmo número .... nota 45
    #     📊 `integrations_provider_identifier_key UNIQUE (provider, identifier)`
    #     e `identifier` é o NOME DA INSTÂNCIA. Duas linhas exigiriam o mesmo
    #     identifier (é a mesma instância) e bateriam na unique; derivar um novo
    #     seria gravar o nome de uma instância que não existe no Evolution.
    #   • afrouxar a proibição do observer ........................... nota 8
    #     é desfazer a SPEC-063 D. Não.
    #   • opt-in explícito por número (este) ......................... nota 88
    #     uma linha, uma verdade, proibição continua padrão, e quem decide é a
    #     corretora.
    COLUNA_AUTORIZACAO_AUXILIAR = "permite_envio_de_auxiliar"

    # Os dois usos que existem para um canal de saída. `plataforma` é tudo o que
    # o produto manda por conta própria (alerta do Vigia, follow-up, sugestão) e
    # segue exatamente como sempre foi. `auxiliar` é trabalho que a corretora
    # instalou e ligou — cobrança, relatório — e só ele enxerga a autorização.
    ENVIO_DE_PLATAFORMA = "plataforma"
    ENVIO_DE_AUXILIAR = "auxiliar"

    @classmethod
    def pode_enviar(cls, integracao: Optional[Dict], *,
                    para: str = ENVIO_DE_PLATAFORMA) -> bool:
        """Esta integração pode ser canal de SAÍDA — para QUAL uso?

        `para` é keyword-only e tem default. Isso não é estilo: é o que garante
        que **todo chamador que existia antes da SPEC-078 continua com o
        comportamento antigo, sem ser editado**. Omitir o argumento é pedir o
        regime de plataforma, onde o observador segue proibido, autorizado ou
        não. Afrouxar por omissão seria o defeito exato que a SPEC-063 D
        corrigiu — e é a asserção mais importante de
        `scripts/canal-auxiliary-nao-contamina-atendimento.test.mjs`.
        """
        if not integracao:
            return False
        purpose = str(integracao.get("purpose") or "").strip().lower()
        if purpose not in cls.PROPOSITOS_QUE_NUNCA_ENVIAM:
            return True
        # Daqui para baixo, a integração é um observador.
        if str(para or "").strip().lower() != cls.ENVIO_DE_AUXILIAR:
            return False
        # `is True` de propósito, e não um `bool(...)`: coluna ausente (banco sem
        # a migration), `None`, `"false"` ou `0` têm de cair para o lado do
        # silêncio. Só o booleano verdadeiro que a corretora gravou autoriza.
        return integracao.get(cls.COLUNA_AUTORIZACAO_AUXILIAR) is True

    def get_platform_whatsapp_integration(self, company_id: str):
        """Integração p/ envios DE PLATAFORMA (alertas do Vigia, follow-ups,
        sugestões, relatório de sábado) — escopo da CORRETORA, não de um agente.

        BUG 14/07: a busca sem agent_id exigia integração com agent_id NULL;
        corretoras com integração vinculada a agente (caso Resulta/Even) ficavam
        SEM canal de alerta — o Vigia falhava em silêncio. Aqui: tenta a global
        (agent_id NULL) e, se não houver, usa a integração ativa da corretora.

        🔴 SPEC-078 B — esta função **não** passa `para="auxiliar"`, e a omissão
        é a decisão. Alerta do Vigia, follow-up e sugestão são o produto falando
        por conta própria: é exatamente a "surpresa" que a SPEC-063 D proíbe. A
        autorização que a corretora dá é para o trabalho que ELA instalou e
        ligou (cobrança, relatório), não para tudo. Um teste guarda esta linha:
        `scripts/canal-auxiliary-nao-contamina-atendimento.test.mjs`.
        """
        integ = self.get_whatsapp_integration(company_id)
        if integ and self.pode_enviar(integ):
            return integ
        if integ:
            logger.warning("[BUSCA INTEGRAÇÃO] a integração encontrada para %s é "
                           "'%s' — proibida como canal de saída (SPEC-063 D)",
                           company_id, integ.get("purpose"))
        try:
            res = (
                self.supabase.table("integrations")
                .select("*")
                .eq("company_id", company_id)
                .eq("is_active", True)
                .execute()
            )
            valid = [i for i in (res.data or [])
                     if str(i.get("provider", "")).lower().strip() in (
                         "z-api", "evolution", "evolution-api", "evolution-go",
                         "wppconnect", "whatsapp", "whatsapp-cloud", "meta")
                     and self.pode_enviar(i)]
            if not valid:
                logger.warning("[BUSCA INTEGRAÇÃO] corretora %s NAO tem canal de saida "
                               "elegivel (o observador nao conta). Nada sera enviado — "
                               "e isso e melhor que enviar pelo numero que deve calar.",
                               company_id)
            if valid:
                from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

                logger.info(f"[BUSCA INTEGRAÇÃO] plataforma: usando integração ativa da corretora {company_id}")
                return prepare_integration_for_runtime(valid[0])
        except Exception as e:  # noqa: BLE001
            logger.error(f"[BUSCA INTEGRAÇÃO] plataforma falhou: {type(e).__name__}")
        return None

    def get_whatsapp_integration(
        self, company_id: str, agent_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Busca integração EXATA de WhatsApp (Provider Agnostic).
        REGRA CRÍTICA: NÃO EXISTE FALLBACK.
        Se o agente tem um ID, TEM que usar a integração desse ID.
        """
        try:
            # Lista de provedores aceitos
            VALID_PROVIDERS = [
                "z-api",
                "evolution",
                "evolution-api",
                "evolution-go",  # SPEC-034: canal oficial migrando p/ Evolution GO
                "wppconnect",
                "whatsapp",
                "whatsapp-cloud",
                "meta",
            ]

            logger.info(
                f"[BUSCA INTEGRAÇÃO] ESTRITA. Company: {company_id} | Agent: {agent_id}"
            )

            # 1. Busca TODAS as integrações ativas da empresa (with retry)
            @db_retry
            def _fetch_integrations():
                return (
                    self.supabase.table("integrations")
                    .select("*")
                    .eq("company_id", company_id)
                    .eq("is_active", True)
                    .execute()
                )

            query = _fetch_integrations()
            integrations = query.data or []

            if not integrations:
                logger.error(
                    f"[BUSCA INTEGRAÇÃO] ❌ Nenhuma integração ativa na empresa {company_id}"
                )
                return None

            # 2. Filtragem ESTRITA (Sem Fallback)
            matching_integration = None

            for integ in integrations:
                # Normaliza provider
                provider_db = str(integ.get("provider", "")).lower().strip()
                if provider_db not in VALID_PROVIDERS:
                    continue

                db_agent_id = integ.get("agent_id")

                # CASO 1: Foi solicitado um Agente Específico
                if agent_id:
                    # A comparação TEM que ser exata.
                    if str(db_agent_id) == str(agent_id):
                        matching_integration = integ
                        break  # Achou a exata!

                # CASO 2: A requisição veio SEM agente (ex: disparo manual sem contexto)
                # Nesse caso, e SÓ nesse caso, procuramos uma integração que também não tenha agente (global real)
                # OU abortamos se a regra for "tudo tem que ter agente"
                elif db_agent_id is None:
                    matching_integration = integ
                    break

            # 3. Resultado Final
            if matching_integration:
                logger.info(
                    f"[BUSCA INTEGRAÇÃO] ✅ SUCESSO. ID: ...{str(matching_integration.get('identifier'))[-4:]} | Agent: {matching_integration['agent_id']}"
                )
                # 39A4.1: descriptografa token/client_token em memória (nunca loga valores).
                return prepare_integration_for_runtime(matching_integration)

            # Se chegou aqui, é ERRO. Nada de tentar "o que tiver".
            logger.error(
                f"[BUSCA INTEGRAÇÃO] ❌ FALHA CRÍTICA. Não existe integração vinculada EXATAMENTE ao Agente {agent_id}. O envio será abortado para evitar cruzar conversas."
            )

            # Log de diagnóstico para ajudar a arrumar o banco
            if agent_id:
                logger.info("--- DIAGNÓSTICO (O que tem no banco) ---")
                for i in integrations:
                    p = i.get("provider")
                    a = i.get("agent_id")
                    logger.info(
                        f" -> Provider: {p} | Agent ID: {a} (Match? {str(a) == str(agent_id)})"
                    )

            return None

        except Exception as e:
            logger.error(f"[BUSCA INTEGRAÇÃO] Erro crítico: {e}", exc_info=True)
            return None

    def _maybe_update_user_name(
        self,
        user_id: str,
        name: Optional[str],
        current_first: Optional[str],
        current_last: Optional[str],
    ) -> None:
        """Helper to update user name if current name is generic/empty"""
        if name and (
            not current_first
            or current_first in ["WhatsApp", "Usuário"]
            or (current_last in ["User", "Desconhecido"])
        ):
            try:
                name_parts = name.strip().split(maxsplit=1)
                update_data = {
                    "first_name": name_parts[0],
                    "last_name": name_parts[1] if len(name_parts) > 1 else "",
                }

                self.supabase.table("users_v2").update(update_data).eq(
                    "id", user_id
                ).execute()
                logger.info(f"[INTEGRATION] Updated user {user_id} name")
            except Exception as e:
                logger.warning(f"[INTEGRATION] Failed to update user name: {e}")

    def get_or_create_user(
        self, phone: str, company_id: str, name: Optional[str] = None
    ) -> str:
        """
        Busca usuário por telefone ou cria novo com status 'lead'

        Args:
            phone: Número de telefone do usuário (ex: 5544988888888)
            company_id: ID da empresa
            name: Nome do usuário (opcional, vindo do WhatsApp)

        Returns:
            user_id do usuário (existente ou criado)

        Raises:
        """
        logger.info(f"[INTEGRATION] Checking user: phone=...{str(phone)[-4:]}")
        # logger.info(f"[INTEGRATION] Looking for user with phone...")

        # Email único por telefone + empresa (evita conflitos entre empresas)
        generated_email = f"{phone}_{company_id}@whatsapp.smith.ai"

        # 1. Tentar encontrar usuário por PHONE + COMPANY (mais rápido se tiver índice)
        try:
            response = (
                self.supabase.table("users_v2")
                .select("id, first_name, last_name")
                .eq("phone", phone)
                .eq("company_id", company_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                user_id = response.data[0]["id"]
                current_first = response.data[0].get("first_name")
                current_last = response.data[0].get("last_name")
                (
                    f"{current_first} {current_last}".strip()
                    if current_first or current_last
                    else None
                )
                logger.info(
                    f"[INTEGRATION] Found existing user by phone+company: {user_id}"
                )

                # Atualizar nome se necessário
                self._maybe_update_user_name(user_id, name, current_first, current_last)
                return user_id

        except Exception as e:
            logger.warning(f"[INTEGRATION] Error searching user by phone: {e}")

        # 2. Tentar encontrar usuário por EMAIL (fallback - email já inclui company_id)
        try:
            response = (
                self.supabase.table("users_v2")
                .select("id, first_name, last_name")
                .eq("email", generated_email)
                .execute()
            )

            if response.data and len(response.data) > 0:
                user_id = response.data[0]["id"]
                current_first = response.data[0].get("first_name")
                current_last = response.data[0].get("last_name")
                logger.info(f"[INTEGRATION] Found existing user by email: {user_id}")

                # Atualizar nome se necessário
                self._maybe_update_user_name(user_id, name, current_first, current_last)
                return user_id

        except Exception as e:
            logger.warning(f"[INTEGRATION] Error searching user by email: {e}")

        # 3. Se não encontrou por phone nem email, cria novo lead
        logger.info("[INTEGRATION] User not found. Creating new lead...")
        logger.info(f"[INTEGRATION] Creating new lead user for phone ...{str(phone)[-4:]}")

        # Determinar first_name e last_name a partir do nome fornecido
        if name:
            name_parts = name.strip().split(maxsplit=1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else "User"
        else:
            first_name = "Usuário"
            last_name = "WhatsApp"

        # Dados do novo usuário - email e CPF únicos por telefone + empresa
        user_data = {
            "email": generated_email,  # {phone}_{company_id}@whatsapp.smith.ai
            "phone": phone,
            "company_id": company_id,
            "status": "lead",
            "first_name": first_name,
            "last_name": last_name,
            "cpf": hashlib.md5(f"{phone}_{company_id}".encode()).hexdigest()[
                :14
            ],  # Hash único (14 chars max)
            "birth_date": "2000-01-01",
            "terms_accepted_at": "now()",
            "privacy_policy_accepted_at": "now()",
        }

        try:
            # IMPORTANTE: No SDK Python do Supabase, .insert() já retorna os dados
            response = self.supabase.table("users_v2").insert(user_data).execute()

            if response.data and len(response.data) > 0:
                new_id = response.data[0]["id"]
                full_name = f"{first_name} {last_name}".strip()
                logger.info(
                    f"[INTEGRATION] Created new lead user: {new_id} "
                    f"(email masked, phone: ...{str(phone)[-4:]}, name: {full_name})"
                )
                return new_id
            else:
                logger.error("[INTEGRATION] CRITICAL: Insert successful but no data returned")
                raise Exception("Insert successful but no data returned from Supabase")

        except Exception as e:
            logger.error(f"[INTEGRATION] Error creating user: {str(e)}")
            raise Exception(f"Failed to get or create user: {str(e)}") from e


# Singleton factory
_integration_service: Optional[IntegrationService] = None


def get_integration_service(supabase_client: Client = None) -> IntegrationService:
    """
    Retorna instância singleton do IntegrationService

    Args:
        supabase_client: Cliente Supabase (obrigatório na primeira chamada)

    Returns:
        IntegrationService instance
    """
    global _integration_service

    if _integration_service is None:
        if supabase_client is None:
            raise ValueError(
                "supabase_client is required to initialize IntegrationService"
            )
        _integration_service = IntegrationService(supabase_client)

    return _integration_service
