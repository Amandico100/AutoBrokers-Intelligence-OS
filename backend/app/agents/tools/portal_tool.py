"""SPEC-020 P3 + SPEC-025 — portal_action: o cerebro Smith aciona um portal (vidros).

Cerebro unico: o AGENTE decide (a partir da conversa com o segurado) e chama esta
tool; o portal-worker EXECUTA e volta com o resultado. SPEC-025: os FATOS da
apolice (placa, veiculo, chassi, endereco, seguradora) sao buscados AQUI, na
InfoCap (/itens + /cliente_cpf), server-side — o LLM NUNCA fornece placa/local
(era isso que fazia o agente inventar ABC1D23/Sao Paulo). O LLM so passa o que e
julgamento: CPF (da conversa), qual apolice (se varias), data do dano e o relato.

P-90 — QUEM DECIDE SE O PEDIDO NASCE DE VERDADE E O INTERRUPTOR DO AGENTE.
Ate 04/08/2026 esta tool tinha `confirm=False` CRAVADO em `portal_params`, e
nenhum caminho do repositorio conseguia liga-lo: o acionamento percorria o
formulario inteiro e parava no 80% para sempre (📊 9 dos 39 jobs terminaram
exatamente ali). Agora `confirm` e o resultado de UMA regra, escrita num lugar
so (`insurer_dispatch_service.acionamento_liberado`): o agente de atendimento
da corretora esta ligado E o freio de emergencia esta solto. Agente desligado
continua parando no 80% — que e exatamente o comportamento de antes, e por isso
ligar o agente e a unica coisa que muda o desfecho. Gate PORTAL_REAL_ENABLED
(no worker) continua governando se o worker sequer pega o job.

Identidade do solicitante (multi-tenant): PERFIL DE ACIONAMENTO da corretora
(companies), nunca do segurado nem inventado. Logica pura em portal_params.py.

BLOCO 7.2 — UM PEDIDO, UM ATENDIMENTO.
📊 O `Nº do atendimento` nasce no passo 7 do portal, ANTES do fim do fluxo: uma
segunda execucao nao corrige a primeira, cria um SEGUNDO atendimento na
seguradora — e isso nao se desfaz. 📊 Sem guarda, 39 jobs `abrir_atendimento`
viraram 5 pedidos distintos (um deles repetido 30 vezes). Agora o `_arun`
calcula a impressao digital do PEDIDO (`chave_de_idempotencia`), procura um job
vivo com ela, e ou se anexa ao que ja roda ou devolve o resultado do que ja
terminou. A corrida de dois inserts simultaneos e decidida pelo indice unico
parcial `idx_portal_jobs_pedido_vivo` e cai no mesmo caminho, nunca num erro.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .portal_params import (
    ESTAGIOS_QUE_O_SEGURADO_RESPONDE,
    ESTAGIOS_TECNICOS,
    JOURNEY_CONTINUAR,
    PREFERENCIA_VISTORIA,
    acao_esperada,
    build_portal_params,
    chave_de_idempotencia,
    continuacao_possivel,
    descricao_da_tool,
    format_result,
    frase_de_pedido_ja_existente,
    mapear_escolha_de_agenda,
    montar_job_de_continuacao,
    numero_do_pedido,
    respostas_da_chamada,
    resumo_da_tela_desconhecida,
    slug_da_seguradora,
)

logger = logging.getLogger(__name__)

POLL_TIMEOUT_S = 150

#: 🔴 JUIZ B1 (conserto da 001.10.1) — o que o agente ouve quando a tool não
#: consegue LER o estado atual do pedido. Fail-closed: nada vai à seguradora.
NAO_CONSEGUI_CONFERIR = (
    "Nao consegui conferir agora o estado do pedido que ja existe na seguradora, "
    "entao NAO mandei nada a ela (para nao repetir nem desfazer nada). O pedido "
    "continua aberto com o mesmo numero. Tente de novo em instantes; se "
    "persistir, acione um humano.")
POLL_EVERY_S = 5

# SPEC-065 7.2 — o mesmo conjunto do indice unico parcial
# `idx_portal_jobs_pedido_vivo`: a chave vale enquanto o pedido esta vivo, e
# `failed` e a unica valvula de escape (acionamento que precisa ser refeito
# depois de corrigido o CPF, a apolice ou a InfoCap).
STATUS_MORTO = "failed"
STATUS_EM_CURSO = ("queued", "running")

#: SPEC-EXTRA-001.10 P-PILOTO-02 — o mesmo `outcome_type` do acionamento por
#: WhatsApp, de proposito: para a corretora, "abrir assistencia" e UM resultado
#: de negocio; o caminho (corredor x portal) e detalhe de execucao, e
#: `runtime_kind` o distingue. Um outcome novo faria a Fila ter duas colunas
#: para a mesma coisa.
#: ⛔ No MODULO, nao como atributo de classe: `BaseTool` e um modelo pydantic e
#: todo atributo sem anotacao vira campo (ou erro) nele.
OUTCOME_ACIONAMENTO = "acionamento_assistencia"
WORKFLOW_PORTAL = "acionamento.portal_vidros"
RUNTIME_PORTAL = "portal"


def _tem_prova_de_efeito(evidence) -> bool:
    """Existe prova de que o pedido nasceu na seguradora?

    A autoridade é `portal_worker.guardrails.tem_prova_de_efeito` — a mesma que
    o worker e o dashboard usam. Uma segunda definição de "houve efeito" seria
    exatamente o motor paralelo que a CLAUDE.md §5 proíbe.

    O fallback existe porque este módulo roda no `smith-api`, e um import que
    falhe não pode virar "não houve efeito" — a resposta cara é liberar o
    segundo pedido. Então o fallback repete só a parte que não pode errar:
    protocolo presente, ou fase que não seja explicitamente inofensiva.
    """
    if not isinstance(evidence, dict):
        return False
    try:
        from portal_worker.guardrails import tem_prova_de_efeito

        return bool(tem_prova_de_efeito(evidence))
    except Exception:  # noqa: BLE001
        if str(evidence.get("protocolo") or "").strip():
            return True
        estado = evidence.get("vidros_estado")
        if isinstance(estado, dict) and estado.get("existe_algo_na_seguradora"):
            return True
        efeito = evidence.get("critical_effect")
        if isinstance(efeito, dict):
            return str(efeito.get("phase") or "") in ("armed", "submitted",
                                                      "confirmed", "unknown")
        return False



class PortalActionInput(BaseModel):
    cpf_cnpj: str = Field(description="CPF/CNPJ do segurado (titular da apolice) — da conversa")
    data_dano: str = Field(description="Data do dano DD/MM/AAAA")
    policy_number: Optional[str] = Field(
        default=None,
        description="Numero da apolice AUTO escolhida (SO quando o cliente tiver mais de uma apolice auto ativa)")
    peca: Optional[str] = Field(default=None, description="Peca danificada (ex: 'vidro de porta', 'parabrisa', 'retrovisor') — voce decide pela conversa")
    como_ocorreu: Optional[str] = Field(default=None, description="Como ocorreu o dano (ex: 'encontrou o veiculo danificado', 'pedra na estrada')")
    onde_ocorreu: Optional[str] = Field(default=None, description="Onde ocorreu (ex: 'urbano', 'rodoviario')")
    descricao: Optional[str] = Field(default=None, description="Descricao livre do ocorrido (min 30 caracteres)")
    placa_informada: Optional[str] = Field(
        default=None,
        description="APENAS se a ferramenta pediu a placa (apolice sem placa na InfoCap) e o CLIENTE informou. NUNCA deduza/invente.")
    # SPEC-065 7.5 — o campo que faltava para as respostas do 80% CHEGAREM ao
    # portal. `build_portal_params` ja lia `flat["especificos"]` e
    # `vidros_lanternas.abrir_atendimento` ja lia `params["especificos"]`: o
    # caminho inteiro existia e era interrompido aqui, no schema, que descartava
    # o que o agente tinha coletado. 📊 As perguntas do 80% sao a ultima tela
    # antes do pedido — chegar la sem elas e ter feito todo o percurso a toa.
    especificos: Optional[dict] = Field(
        default=None,
        # 🔴 SPEC-EXTRA-001.10.1 — `onde_realizar_o_servico` SAIU (domicílio fora,
        # D-E001101-05); entraram as preferências e a escolha da agenda, que é
        # como o segurado CONTINUA um pedido já aberto.
        description=("Respostas das perguntas especificas ja coletadas na conversa, e tambem "
                     "cidade_para_o_servico. A propria ferramenta diz QUAIS chaves usar quando "
                     "faltar alguma (ela devolve a pergunta pronta com o formato da resposta). "
                     "Exemplos: cidade_para_o_servico, aceita_reparo, "
                     "pelicula, lado_motorista_ou_carona, porta_dianteira_ou_traseira, "
                     "posicao_do_trincado, tamanho_do_trincado, pecas_lataria (LISTA), "
                     "preferencia_agenda (a partir de que dia e manha/tarde, com as palavras "
                     "dele), preferencia_vistoria ('link' ou 'loja'), e escolha_agenda "
                     "({loja: numero da lista, dia: DD/MM, horario: HH:MM}) quando o pedido "
                     "ja aberto mostrou a agenda. "
                     "Use 'nao sabe' SO se o segurado realmente nao souber — nunca para "
                     "agilizar: o portal precisa disso para pedir a peca certa."))
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NAO preencher)")


class PortalActionTool(BaseTool):
    name: str = "portal_action"
    # 🔴 SPEC-EXTRA-001.10 P0-5 — A DESCRICAO E GERADA, NAO ESCRITA.
    #
    # 📊 Ate 20/09/2026 este texto era a TERCEIRA opiniao sobre o que o portal
    # pede: o prompt dizia 3 coisas, `TRANSPORTAVEIS` recusava por 6, e aqui
    # havia uma lista a mao. Agora ele e uma projecao de `TRANSPORTAVEIS` + as
    # familias — acrescentar um campo que trava muda este texto no mesmo commit.
    description: str = descricao_da_tool()
    args_schema: Type[BaseModel] = PortalActionInput
    company_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.supabase_client = supabase_client

    def _client(self):
        return getattr(self.supabase_client, "client", self.supabase_client)

    def _attendance_agent_id(self) -> Optional[str]:
        """Resolve o agente ATENDENTE (role attendance) da corretora — MESMA regra do
        caminho de resposta do WhatsApp (whatsapp_channel). A integracao e vinculada a
        ESSE agente; sem o agent_id, o lookup e ESTRITO e volta None (era o bug do
        heads-up sumido)."""
        try:
            res = self._client().table("agents").select("id").eq(
                "company_id", self.company_id).eq("agent_role", "attendance").eq(
                "is_active", True).limit(1).execute()
            if res.data:
                return str(res.data[0]["id"])
            res2 = self._client().table("agents").select("id").eq(
                "company_id", self.company_id).eq("agent_role", "attendance").limit(1).execute()
            return str(res2.data[0]["id"]) if res2.data else None
        except Exception:  # noqa: BLE001
            return None

    def _notify(self, session_id: str, text: str, agent_id: Optional[str] = None) -> None:
        """Manda uma mensagem AGORA pro segurado (via WhatsApp da corretora), pra ele
        nunca ficar no silencio enquanto o portal roda (~1 min). Best-effort, mas
        agora CONFIAVEL: resolve o agente atendente antes do lookup da integracao.

        `agent_id` entra por parametro (SPEC-065 7.2) porque o `_arun` ja o
        resolveu para gravar no job — resolver de novo seria a mesma consulta
        duas vezes. Sem parametro, o comportamento e o de antes."""
        try:
            parts = str(session_id or "").split(":")
            if len(parts) < 3 or parts[0] != "whatsapp":
                return  # so notifica em sessao real de WhatsApp
            phone = "".join(ch for ch in parts[1] if ch.isdigit())
            if not phone:
                return
            from app.services.integration_service import get_integration_service
            from app.services.whatsapp_service import get_whatsapp_service

            svc = get_integration_service()
            agent_id = agent_id or self._attendance_agent_id()
            integration = svc.get_whatsapp_integration(self.company_id, agent_id)
            if not integration:  # ultimo recurso: qualquer integracao ativa sem agente
                integration = svc.get_whatsapp_integration(self.company_id)
            if not integration:
                return
            get_whatsapp_service().send_message(phone, text, integration)
        except Exception:  # noqa: BLE001
            pass

    async def _envio_liberado(self, cpf: str = "",
                              journey: str = "abrir_atendimento") -> bool:
        """P-90 — este acionamento pode CONCLUIR o pedido na seguradora?

        Uma pergunta, duas condicoes, e as duas moram fora daqui de proposito:
        `attendance_agent_active` (o interruptor que o Founder clica) e
        `acionamento_liberado` (a regra, compartilhada com o corredor de
        WhatsApp). Reescrever a regra aqui criaria duas verdades sobre a mesma
        coisa — e no dia em que uma mudasse, a outra continuaria valendo em
        silencio.

        Fail-closed em qualquer imprevisto: nao conseguir CONFIRMAR que o agente
        esta ligado nunca pode virar permissao para abrir pedido. O pior caso do
        `False` e um acionamento que para no 80%, como sempre parou; o pior caso
        do `True` e um atendimento aberto de verdade na seguradora, que nao se
        desfaz (o Nº nasce no passo 7, antes do fim do fluxo).
        """
        # 🔴 SPEC-EXTRA-001.10.1 — a regra mora em `envio_liberado` (módulo): o
        # vigia também a lê. As três condições continuam as mesmas: agente
        # ligado + freio de emergência solto (as do corredor de WhatsApp) +
        # `PORTAL_EFEITO_MATERIAL_LIBERADO`/allowlist do canário por CLASSE DE
        # EFEITO (18/08/2026, P0-6), com `cpf:<hash>` porque aqui o job ainda
        # não existe.
        return await envio_liberado(self.company_id, cpf, journey)

    def _load_profile(self) -> dict:
        """Solicitante = identidade da CORRETORA (multi-tenant). REUSA os 'Dados da
        Corretora' (primary_contact_*/cnpj); acionamento_profile e override opcional."""
        profile = {}
        try:
            res = self._client().table("companies").select(
                "company_name, legal_name, primary_contact_name, primary_contact_email, "
                "primary_contact_phone, cnpj, acionamento_profile"
            ).eq("id", self.company_id).limit(1).execute()
            if res.data:
                row = res.data[0]
                ov = row.get("acionamento_profile") or {}
                profile = {
                    "nome": ov.get("nome") or row.get("primary_contact_name") or row.get("legal_name") or row.get("company_name"),
                    "email": ov.get("email") or row.get("primary_contact_email"),
                    "telefone": ov.get("telefone") or row.get("primary_contact_phone"),
                    "cpf_cnpj": ov.get("cpf_cnpj") or row.get("cnpj"),
                }
        except Exception:  # noqa: BLE001
            pass
        return profile

    def _buscar_pedido_vivo(self, chave: str) -> Optional[dict]:
        """SPEC-065 7.2 — este PEDIDO ja tem job vivo?

        Filtra por corretora SEMPRE (CLAUDE.md §7): a chave ja embute a
        corretora, mas guarda que depende do formato de uma string nao e guarda.

        'Vivo' = tudo menos `failed`, exatamente o predicado do indice unico
        parcial `idx_portal_jobs_pedido_vivo`. Se a leitura e o indice
        discordarem, o insert estoura 23505 num caminho que a leitura jurava
        estar livre — e o guarda vira um erro de atendimento.

        Falha de leitura devolve None de proposito: o insert seguinte ainda tem
        o indice unico como segunda rede. Melhor tentar e ser barrado pelo banco
        do que travar o acionamento porque uma consulta caiu."""
        if not chave:
            return None
        try:
            # 🔴 SPEC-074 — defesa em profundidade: `failed` deixou de ser prova
            # de que nada aconteceu.
            #
            # A premissa da SPEC-065 §7.2 era que `failed` só acontecia ANTES de
            # qualquer escrita. Com efeito material dentro da journey, um job
            # pode terminar `failed` COM o protocolo dentro do evidence. Se a
            # leitura confiar só no status, o pedido some do dedup e o próximo
            # `portal_action` abre o segundo atendimento, pago, no nome do mesmo
            # segurado.
            #
            # O `worker.py` já grava `needs_human` nesse caso — esta é a segunda
            # rede, para jobs gravados por versões anteriores e para qualquer
            # outro caminho que ainda escreva `failed`. Por isso a consulta traz
            # TODOS os status e a exclusão passa a ser feita aqui, olhando a
            # evidência em vez do rótulo.
            r = (self._client().table("portal_jobs")
                 .select(_COLUNAS_DO_PEDIDO)
                 .eq("company_id", self.company_id)
                 .eq("idempotency_key", chave)
                 .order("created_at", desc=True)
                 .limit(5).execute())
            for linha in (r.data or []):
                job = dict(linha)
                if str(job.get("status")) != STATUS_MORTO:
                    return job
                if _tem_prova_de_efeito(job.get("evidence")):
                    # `failed` com prova de efeito é um pedido VIVO disfarçado.
                    job["_ressuscitado_por_evidencia"] = True
                    return job
            return None
        except Exception:  # noqa: BLE001
            logger.warning("[PortalAction] busca de pedido vivo indisponivel — seguindo para o insert")
            return None

    @staticmethod
    def _e_chave_duplicada(exc: Exception) -> bool:
        """23505 = unique_violation do Postgres.

        A corrida existe de verdade: duas chamadas de `portal_action` no mesmo
        segundo passam as duas pela leitura, acham nada, e chegam juntas no
        insert. O banco decide qual vence. A perdedora NAO pode estourar o
        atendimento — ela cai no caminho de quem achou um existente, que e a
        verdade do que aconteceu."""
        return e_chave_duplicada(exc)

    # ======================================================================
    # P-PILOTO-02 — O ACIONAMENTO PELO PORTAL APARECE NA FILA E NA FICHA
    # ======================================================================
    #
    # 📊 Medido em 08/09/2026 e reconfirmado em 20/09: `portal_jobs` tem as
    # colunas `work_run_id`, `agent_id` e `operation_key` e as três ficavam
    # vazias; `lib/atendimento/casos.ts` lê cinco tabelas e nenhuma delas é
    # `portal_jobs`. Efeito: um acionamento de vidros acontecia, custava
    # dinheiro ao segurado e **não existia** para quem olha o produto.
    #
    # ⛔ Nenhum escritor novo (CLAUDE.md §5): quem grava é
    # `work.runs.criar_registro_sem_fila`, o helper que o `dispatch_router` já
    # usa — e pela mesma razão dele (o outbox marcaria como `failed` um trabalho
    # que o Smith Worker não executa; quem executa aqui é o portal-worker).
    #
    # ⚠️ **Falhar aqui NUNCA derruba o acionamento.** O espelho é relatório; o
    # pedido é o serviço do segurado. Perder o espelho é recuperável por
    # backfill; perder o acionamento não é.

    async def _conversa_provada(self, db, session_id: str) -> Optional[str]:
        """De qual conversa este acionamento nasceu — ou `None`.

        🔴 O filtro por corretora é a proteção real (CLAUDE.md §7 — o backend
        roda com service role). E a dúvida grava NULO: perder a ligação de um
        run legítimo é recuperável; gravar a ligação errada produz um relatório
        confiante e falso.

        ⚠️ Não reaproveita `dispatch_router._conversa_provada_da_sessao` porque
        aquela prova por `session["mirror_conversation_id"]`, uma chave que só
        existe dentro do corredor de WhatsApp. Aqui a prova é por
        `conversations.session_id`, que é o mesmo texto que o job já guarda. A
        REGRA é a mesma (filtrar corretora, NULO na dúvida); o que muda é por
        onde se prova.
        """
        sessao = str(session_id or "").strip()
        if not sessao or not self.company_id:
            return None
        try:
            # ⚠️ `_talvez_await` em vez de `await` seco: este módulo roda tanto
            # com o cliente async (produção) quanto com o síncrono (dublês dos
            # guardas). É a MESMA razão, e a MESMA função, que `work.runs` usa —
            # escrever aqui uma segunda versão do "aguarda se for aguardável"
            # seria a cópia que aquele helper existe para não ter.
            from app.services.work.runs import _talvez_await

            achado = await _talvez_await(
                getattr(db, "client", db).table("conversations")
                .select("id")
                .eq("company_id", self.company_id)
                .eq("session_id", sessao)
                .limit(1).execute())
            linhas = getattr(achado, "data", None) or []
            return str(linhas[0]["id"]) if linhas else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalAction] conversa nao provada (%s) — o run nasce "
                           "com conversation_id NULO", type(exc).__name__)
            return None

    async def _garantir_work_run(self, *, chave: str, session_id: str,
                                 params: dict, agent_id: Optional[str]) -> Optional[str]:
        """O espelho durável deste acionamento. `None` = não deu, e segue assim mesmo."""
        try:
            from app.core.database import create_async_supabase_client
            from app.services.work.runs import criar_registro_sem_fila

            db = await create_async_supabase_client()
            if db is None:
                return None
            peca = str((params.get("dano") or {}).get("peca") or "vidros").strip()
            registro = await criar_registro_sem_fila(
                db,
                company_id=self.company_id,
                workflow_key=WORKFLOW_PORTAL,
                outcome_type=OUTCOME_ACIONAMENTO,
                outcome_title=f"Acionamento de vidros — {peca}"[:180],
                source_type="portal",
                source_id=None,
                conversation_id=await self._conversa_provada(db, session_id),
                runtime_kind=RUNTIME_PORTAL,
                status="running",
                # Alto por definição: do outro lado está a seguradora de
                # verdade, e o número do atendimento nasce antes do fim do fluxo.
                risk_level="high",
                idempotency_key=chave or f"portal:{session_id or 'sem-sessao'}",
                input_payload={
                    "placa": str(params.get("placa") or ""),
                    "peca": peca,
                    "data_dano": str(params.get("data_dano") or ""),
                    "seguradora": str(params.get("insurer_name") or ""),
                    # ⛔ Nada de CPF, telefone, e-mail ou endereço aqui: o
                    # payload do run é lido por tela de operação e por
                    # relatório. O que identifica o pedido é placa + data.
                },
                current_step_key="abrindo_no_portal",
                progress_percent=10,
                requester_agent_id=agent_id,
            )
            return str(registro["id"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalAction] work_run nao criado (%s) — o acionamento "
                           "segue; so o espelho durável falta", type(exc).__name__)
            return None

    async def _fechar_work_run(self, run_id: str, job: dict) -> None:
        """Leva o run ao desfecho que o portal decidiu — a regra é `fechar_work_run`
        (módulo), a MESMA que o vigia usa quando é ele quem entrega."""
        fechar_work_run(self.company_id, run_id, job)

    # ======================================================================
    # P-PILOTO-08 — tela desconhecida no portal entra na FILA DE APRENDIZADO
    # ======================================================================
    async def _aprender_com_a_tela_cega(self, job_id: str, job: dict) -> None:
        """Uma linha em `tela_cega` por job, e só quando o portal disse algo novo.

        📊 A fila existe desde a SPEC-087 e só o corredor de URA a alimentava; o
        portal gravava `debug_dom` num jsonb que ninguém varre (P-PILOTO-08).

        ⚠️ UMA vez por job — a marca vai no próprio `evidence`. Sem ela, o Vigia
        varre o mesmo job a cada minuto e a fila de aprendizado vira ruído em um
        dia, que é exatamente o que a dedupe da SPEC-087 existe para impedir.
        """
        try:
            ev = (job or {}).get("evidence") or {}
            resumo = resumo_da_tela_desconhecida(ev)
            if not resumo or ev.get("tela_cega_registrada"):
                return
            from app.services.tela_cega import registrar_tela_cega

            await registrar_tela_cega(
                company_id=self.company_id,
                insurer_key=slug_da_seguradora((job or {}).get("params") or {}),
                ramo="vidros",
                playbook_ref=f"portal:vidros_lanternas:{resumo['onde']}",
                texto=resumo["texto"],
            )
            # 🔴 JUIZ B1: o `evidence` que este metodo tem em maos foi LIDO
            # ANTES de o agente responder — e o Vigia grava `entregue_ao_agente`
            # nesse meio-tempo. Regravar o dicionario velho APAGAVA a marca, e
            # 📊 o Vigia entao mandava uma SEGUNDA mensagem ao segurado sobre um
            # atendimento que ele ja tinha recebido.
            #
            # A releitura e curta e resolve: funde-se a marca no dicionario ATUAL
            # do banco, nunca no que sobrou na memoria desta chamada.
            atual = dict(ev)
            try:
                lido = (self._client().table("portal_jobs").select("evidence")
                        .eq("id", job_id).eq("company_id", self.company_id)
                        .limit(1).execute())
                linhas = getattr(lido, "data", None) or []
                if linhas and isinstance(linhas[0].get("evidence"), dict):
                    atual = dict(linhas[0]["evidence"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("[PortalAction] evidence nao relida (%s); "
                               "preservando as marcas conhecidas", type(exc).__name__)
            for marca in ("entregue_ao_agente", "entregue_em", "hitl",
                          "critical_effect", "protocolo"):
                if marca in ev and marca not in atual:
                    atual[marca] = ev[marca]
            self._client().table("portal_jobs").update({
                "evidence": {**atual, "tela_cega_registrada": True},
            }).eq("id", job_id).eq("company_id", self.company_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalAction] fila de aprendizado nao recebeu (%s)",
                           type(exc).__name__)

    async def _fetch_infocap(self, cpf: str, policy_number: Optional[str]) -> dict:
        """SPEC-025: fatos reais da apolice AUTO (placa/veiculo/endereco) via porta
        PolicyDataProvider (InfoCap /itens + /cliente_cpf). Nunca inventa; nunca
        derruba o atendimento (fail-safe -> provider_unavailable)."""
        try:
            import os

            from app.core.database import create_async_supabase_client
            from app.providers.policy_data_provider import get_policy_data_provider

            key = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
            provider = get_policy_data_provider("infocap")
            # 🔴 SPEC-EXTRA-001.1 §5.1.1: `hasattr` nao e contrato — o registry e.
            if provider is None or not key:
                return {"ok": False, "status": "provider_unavailable"}
            db = await create_async_supabase_client()
            return await provider.vehicle(
                company_id=self.company_id, document=cpf,
                policy_number=policy_number, db=db, internal_key=key,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PortalAction] InfoCap vehicle lookup falhou: {type(e).__name__}")
            return {"ok": False, "status": "provider_error"}

    async def _arun(self, **flat) -> dict:
        session_id = str(flat.pop("session_id", "") or "")
        cpf = str(flat.get("cpf_cnpj") or "").strip()
        if not cpf:
            return {"content": "Preciso do CPF/CNPJ do segurado (da conversa) para acionar."}

        # 1) FATOS da apolice — InfoCap server-side (o LLM nao fornece placa/local).
        info = await self._fetch_infocap(cpf, str(flat.get("policy_number") or "").strip() or None)
        status = str(info.get("status") or "")
        if status == "multiple_auto_policies":
            opts = info.get("options") or []
            linhas = "; ".join(
                f"{o.get('numapo')} — {o.get('seguradora')} ({o.get('veiculo') or 'veiculo?'} placa {o.get('placa') or '?'})"
                for o in opts[:5]
            )
            return {"content": f"O cliente tem mais de uma apolice AUTO ativa. Pergunte QUAL e chame de novo "
                               f"com policy_number. Opcoes: {linhas}"}
        if status == "no_auto_policy":
            return {"content": "Nao encontrei apolice AUTO para este CPF na InfoCap. Confirme com o cliente "
                               "se o seguro do carro e por esta corretora (ou se o CPF esta certo)."}
        if not info.get("ok"):
            return {"content": "A InfoCap nao respondeu agora (nao consegui buscar os dados da apolice). "
                               "Tente de novo em instantes; se persistir, acione um humano."}

        # 2) params = fatos (InfoCap) + julgamento (LLM) + solicitante (corretora)
        #
        # P-90 — e o interruptor do agente, que vira `params['confirm']`. E o
        # UNICO lugar do fluxo em que "abrir o pedido de verdade" se decide.
        enviar = await self._envio_liberado(cpf)
        params, err = build_portal_params(flat, self._load_profile(), info,
                                          enviar_de_verdade=enviar)
        if err:
            return {"content": err}
        logger.info("[PortalAction] confirm=%s (agente de atendimento %s)",
                    enviar, "LIGADO" if enviar else "desligado ou freio armado")

        # 3) SPEC-065 7.2 — este pedido ja existe? O protocolo da seguradora nasce
        # no passo 7, ANTES do fim do fluxo: reexecutar nao corrige, cria um
        # SEGUNDO atendimento. 📊 39 jobs para 5 pedidos distintos e o que
        # acontecia sem este bloco.
        chave = chave_de_idempotencia(params, self.company_id)
        # 🔴 ACHADO DO BLOCO 0 — `_idempotency_key` era LIDA E NUNCA ESCRITA.
        #
        # 📊 `portal_worker/journeys/vidros_apifirst.py:231` lê
        # `params["_idempotency_key"]` e, medido em 20/09/2026, nenhum lugar do
        # repositório a gravava. Efeito: a proteção contra o POST repetido
        # DENTRO da journey (a que impede o segundo `POST /atendimentos` quando
        # o worker reexecuta o mesmo job) nascia sempre vazia — a rede existia e
        # estava desligada.
        #
        # ⚠️ É a MESMA chave do dedup de job, de propósito: as duas protegem o
        # mesmo fato (um pedido por veículo, peça e data). Uma segunda chave
        # seria um segundo conceito de "mesmo pedido", e o dia em que elas
        # divergissem ninguém saberia qual valia.
        if chave:
            params["_idempotency_key"] = chave
        job_id: Optional[str] = None
        reaproveitado = False

        existente = self._buscar_pedido_vivo(chave)
        if existente:
            if str(existente.get("status")) in STATUS_EM_CURSO:
                # Anexa-se ao que ja roda em vez de criar outro. O segurado ja
                # recebeu o ack na primeira chamada — repeti-lo seria dizer duas
                # vezes que estamos comecando algo que ja comecou.
                job_id, reaproveitado = str(existente.get("id")), True
                logger.info("[PortalAction] pedido ja em andamento — anexando ao job existente")
            else:
                # Pedido terminado (done/needs_human): abrir outro seria o
                # segundo atendimento. 🔴 SPEC-EXTRA-001.10.1 — mas ele pode
                # CONTINUAR: se a journey guardou a sessão e esta chamada traz o
                # que o pedido espera, o MESMO pedido segue. Senão, a frase de
                # sempre, honesta.
                return await self._continuar_ou_explicar(
                    existente=existente, params=params, pedido_key=chave,
                    session_id=session_id, cpf=cpf)

        if not existente:
            # 🔴 RED B4 (conserto da 001.10.1) — a PEÇA REESCRITA não abre outro
            # pedido. 📊 O red team mediu: "vidro de porta" parou em
            # `peca_ambigua`, o modelo chamou de novo com "vidro da porta
            # traseira esquerda" no campo de cima, a chave (que embute a peça)
            # mudou e nasceu um 2º `POST /atendimentos` — um segundo atendimento
            # real no nome do segurado. A proteção era só a frase do prompt.
            irmao = self._pedido_irmao_esperando_resposta(params, chave)
            if irmao is not None:
                abertura_irma, params_irmaos, chave_irma = irmao
                ignorada = str(params_irmaos.pop("_peca_reescrita_ignorada", "") or "")
                resposta = await self._continuar_ou_explicar(
                    existente=abertura_irma, params=params_irmaos,
                    pedido_key=chave_irma, session_id=session_id, cpf=cpf,
                    anotacao=({"peca_reescrita_ignorada": ignorada} if ignorada else None))
                return {"content": (
                    "[para voce, agente] Esta chamada tem a MESMA placa, o MESMO CPF e a "
                    "MESMA data do dano de um pedido que ja existe e esta PARADO "
                    "esperando uma resposta do segurado — tratei esta chamada como a "
                    "RESPOSTA desse pedido e NAO abri outro atendimento. Se for OUTRA "
                    "peca de verdade, conclua este pedido primeiro.\n\n"
                    + str((resposta or {}).get("content") or ""))}

        # O agente atendente e resolvido uma vez so: ele vai para o job (para quem
        # responder depois saber por qual integracao falar) e para o `_notify`.
        agent_id = self._attendance_agent_id() if not reaproveitado else None

        # 🔴 P-PILOTO-02 — o espelho durável nasce ANTES do job, e por isso o
        # `work_run_id` já entra na linha do `portal_jobs` em vez de precisar de
        # um segundo UPDATE que pode não acontecer. O run é idempotente pela
        # MESMA chave do pedido: duas chamadas não criam dois espelhos.
        #
        # ⚠️ Run sem job é aceitável (aparece como acionamento que não concluiu);
        # job sem run é o que o produto já tinha e é o defeito.
        # Quem se anexou a um job em curso herda o espelho DELE — criar outro
        # aqui daria dois runs para um pedido, que é o defeito na outra direção.
        work_run_id = str((existente or {}).get("work_run_id") or "") or None
        if not reaproveitado:
            work_run_id = await self._garantir_work_run(
                chave=chave, session_id=session_id, params=params, agent_id=agent_id)
            if work_run_id:
                params["_work_run_id"] = work_run_id
            if session_id:
                params["_conversation_id"] = session_id

        # 4) Enfileira o job para o portal-worker — so quando nao havia um vivo.
        if not reaproveitado:
            try:
                _linha = {
                    "company_id": self.company_id,
                    "portal_key": "vidros_lanternas",
                    "journey": "abrir_atendimento",
                    "params": params,
                    "status": "queued",
                    "idempotency_key": chave or None,  # "" nunca vai para o banco
                    "session_id": session_id or None,  # o caminho de volta a conversa
                    "agent_id": agent_id,
                    # 🔴 A coluna existe desde a SPEC-075 e nunca teve escritor
                    # (📊 P-PILOTO-02, 08/09/2026). É ela que liga o acionamento
                    # de vidros à Fila e à Ficha.
                    "work_run_id": work_run_id,
                }
                # 🔴 SPEC-075 Bloco D — `operation_key` entra sem poder derrubar
                # o acionamento. A coluna é nova; o smith-api sobe com a imagem
                # nova antes de a migration rodar. E o `except` logo abaixo só
                # sabe tratar violação de chave única: qualquer outro erro vira
                # "Nao consegui enfileirar o acionamento" para um segurado com o
                # carro parado. Então a tentativa com a coluna é isolada aqui.
                try:
                    ins = self._client().table("portal_jobs").insert(
                        {**_linha, "operation_key": "assistance.glass.request"}
                    ).execute()
                except Exception as _e_col:  # noqa: BLE001
                    if self._e_chave_duplicada(_e_col):
                        raise
                    logger.warning(
                        "[PortalAction] insert com operation_key falhou (%s); "
                        "repetindo sem a coluna — a migration da SPEC-075 "
                        "provavelmente ainda nao rodou", type(_e_col).__name__)
                    ins = self._client().table("portal_jobs").insert(_linha).execute()
                job_id = ins.data[0]["id"] if ins.data else None
            except Exception as e:  # noqa: BLE001
                if not self._e_chave_duplicada(e):
                    logger.error(f"[PortalAction] enfileirar falhou: {type(e).__name__}")
                    return {"content": f"Nao consegui enfileirar o acionamento ({type(e).__name__})."}
                # Perdeu a corrida: outra chamada criou o pedido entre a leitura e
                # o insert. Isso nao e erro — e o guarda funcionando.
                logger.info("[PortalAction] corrida perdida (23505) — o pedido ja tinha sido criado")
                concorrente = self._buscar_pedido_vivo(chave)
                if not concorrente:
                    return {"content": frase_de_pedido_ja_existente({"status": "queued"})}
                if str(concorrente.get("status")) not in STATUS_EM_CURSO:
                    return {"content": frase_de_pedido_ja_existente(concorrente)}
                job_id, reaproveitado = str(concorrente.get("id")), True

        # Ack IMEDIATO pro segurado: nunca deixa ele no silencio enquanto o portal
        # roda. So quando o job nasceu AGORA — quem se anexou a um job em curso ja
        # mandou este recado na primeira chamada, e repeti-lo diria duas vezes que
        # estamos comecando algo que ja comecou.
        if not reaproveitado:
            veic = (params.get("segurado") or {}).get("veiculo") or "seu veiculo"
            self._notify(
                session_id,
                f"Perfeito! 🙌 Ja vou acionar a seguradora pra abrir seu atendimento de vidros "
                f"({veic}, placa {params.get('placa')}). Isso leva mais ou menos 1 minutinho — "
                "ja volto aqui com a confirmacao, ta? 🙂",
                agent_id,
            )

        if not job_id:
            return {"content": "Nao consegui enfileirar o acionamento (o banco nao devolveu o job)."}

        # 5) Aguarda o worker terminar (o segurado esta na conversa). asyncio.sleep:
        # NAO bloqueia o event loop (o time.sleep antigo travava o atendente inteiro).
        # Quando `reaproveitado`, o poll acompanha o job que JA existia — e por isso
        # que uma segunda chamada nao precisa de um segundo job para responder.
        resposta = await self._aguardar(str(job_id), work_run_id, params)
        if resposta is not None:
            return resposta
        # Estourou os 150s. Aqui morava o defeito: a tool dizia "enfileirei, o
        # worker nao processou" e o agente chamava de novo — criando o segundo
        # atendimento. Quem se anexou a um job em curso recebe a verdade do que
        # aconteceu (nada foi enfileirado nesta chamada) e a instrucao de nao repetir.
        if reaproveitado:
            return {"content": frase_de_pedido_ja_existente({"status": "queued"})}
        return {"content": format_result({"status": "queued"})}

    async def _aguardar(self, job_id: str, work_run_id: Optional[str],
                        params: dict) -> Optional[dict]:
        """O poll de 150 s: a resposta pronta, ou `None` se o relógio estourou.

        🔴 SPEC-EXTRA-001.10.1 — virou método porque a CONTINUAÇÃO espera do
        mesmo jeito que a abertura: mesma marca `entregue_ao_agente` (que cala
        o vigia), mesmo fechamento do run, mesma fila de aprendizado. Dois laços
        de espera seriam duas regras sobre quando o segurado já soube.
        """
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            await asyncio.sleep(POLL_EVERY_S)
            try:
                r = (self._client().table("portal_jobs").select("status, evidence, error")
                     .eq("id", job_id).eq("company_id", self.company_id)
                     .limit(1).execute())
                job = r.data[0] if r.data else {}
            except Exception:  # noqa: BLE001
                continue
            if str(job.get("status")) in ("done", "needs_human", "failed"):
                # SPEC-065 — a MARCA que cala o Vigia do Portal.
                #
                # Daqui o resultado vai para o agente, que conta ao segurado. O
                # `vigia_do_portal` varre o que terminou e ninguem entregou; sem
                # esta marca ele reavisaria TODO acionamento bem-sucedido, e o
                # segurado receberia duas versoes da mesma coisa sem saber qual
                # vale. Duplicar aviso e pior que nao avisar.
                #
                # Marcar aqui e nao pelo relogio e proposital: relogio erra
                # quando o processo reinicia; a marca so existe se a entrega
                # aconteceu de fato.
                try:
                    self._client().table("portal_jobs").update({
                        "evidence": {**(job.get("evidence") or {}), "entregue_ao_agente": True},
                    }).eq("id", job_id).eq("company_id", self.company_id).execute()
                except Exception:  # noqa: BLE001
                    pass  # falhar a marca nao pode derrubar a resposta ao segurado

                # 🔴 O DESFECHO CHEGOU: o espelho durável fecha e a tela nova,
                # se houver, entra na fila de aprendizado. As duas coisas são
                # best-effort por dentro — nenhuma delas pode ficar entre o
                # segurado e a resposta dele.
                if work_run_id:
                    await self._fechar_work_run(work_run_id, job)
                # ⚠️ `params` entra por fora: 📊 o poll acima seleciona só
                # `status, evidence, error` — o job que volta do banco NÃO tem
                # `params`, e é de lá que sai o nome da seguradora para a fila
                # de aprendizado. Sem esta linha toda tela nova entrava na fila
                # como `desconhecida`, e a fila deixaria de separar por portal.
                await self._aprender_com_a_tela_cega(str(job_id), {**job, "params": params})
                return {"content": format_result(job)}
        return None

    # ======================================================================
    # 🔴 SPEC-EXTRA-001.10.1 C1 — O PEDIDO TERMINADO PODE CONTINUAR
    # ======================================================================
    async def _continuar_ou_explicar(self, *, existente: dict, params: dict,
                                     pedido_key: str, session_id: str, cpf: str,
                                     anotacao: Optional[dict] = None) -> dict:
        """O pedido desta chamada já terminou (done/needs_human). Continua, ou explica.

        Continua quando as DUAS coisas são verdade:
          1. a journey provou que dá (`evidence.continuacao.possivel is True`) —
             na ÚLTIMA continuação do pedido, não na evidence velha da abertura;
          2. esta chamada traz o que o pedido espera (`acao_esperada`).
        ⛔ NUNCA um segundo `abrir_atendimento`: o que sai daqui é um job
        `continuar_atendimento`, com chave própria de continuação (G7).
        """
        cliente = self._client()
        atual = buscar_ultimo_estado_do_pedido(cliente, self.company_id, existente, pedido_key)
        if atual is None:
            # 🔴 JUIZ B1 — fail-closed: sem saber o estado ATUAL do pedido, nada
            # vai à seguradora (a evidence da abertura pode estar vencida).
            return {"content": NAO_CONSEGUI_CONFERIR}
        work_run_id = str(existente.get("work_run_id") or atual.get("work_run_id") or "") or None
        if atual is not existente and str(atual.get("status")) in STATUS_EM_CURSO:
            # Uma continuação deste pedido já está rodando: acompanha a ELA.
            resposta = await self._aguardar(str(atual.get("id")), work_run_id, params)
            return resposta or {"content": frase_de_pedido_ja_existente({"status": "queued"})}

        ev = atual.get("evidence") if isinstance(atual.get("evidence"), dict) else {}
        esp = params.get("especificos") if isinstance(params.get("especificos"), dict) else {}
        operacao, slot = acao_esperada(ev)
        escolha, respostas = None, None

        if not continuacao_possivel(ev):
            resposta_nova = bool(esp.get("escolha_agenda") or esp.get(PREFERENCIA_VISTORIA)
                                 or (slot and respostas_da_chamada(params, atual.get("params") or {}, slot)))
            return {"content": frase_de_pedido_ja_existente(atual, resposta_nova=resposta_nova)}

        if operacao == "agendar":
            bruto = esp.get("escolha_agenda")
            if not bruto:
                return {"content": self._ainda_esperando(atual)}
            desf = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else {}
            escolha, erro = mapear_escolha_de_agenda(bruto, desf)
            if erro:
                return {"content": (
                    "A escolha que voce mandou NAO casa com a lista que o segurado viu "
                    f"({erro}). NAO agendei nada. Confirme com ele o NUMERO da loja, o dia "
                    "(DD/MM) e um horario que esteja na lista, e chame de novo.\n\n"
                    + format_result(atual))}
        elif operacao == "responder":
            respostas = respostas_da_chamada(params, atual.get("params") or {}, slot)
            if not respostas:
                return {"content": self._ainda_esperando(atual)}
        elif operacao == "vistoria":
            pref = str(esp.get(PREFERENCIA_VISTORIA) or "").strip()
            if not pref:
                return {"content": self._ainda_esperando(atual)}
            respostas = {PREFERENCIA_VISTORIA: pref}
        else:
            # "reler" é do vigia (parada técnica, sem nada a perguntar); ação
            # desconhecida não se adivinha.
            return {"content": frase_de_pedido_ja_existente(atual)}

        confirm = await self._envio_liberado(cpf, JOURNEY_CONTINUAR)
        linha = montar_job_de_continuacao(
            company_id=self.company_id, job_origem=atual, operacao=operacao,
            pedido_key=pedido_key,
            protocolo=numero_do_pedido(existente.get("evidence")) or pedido_key,
            confirm=confirm, escolha=escolha, respostas=respostas,
            # 🔴 RED B3 (conserto da 001.10.1): a tentativa é sobre o ESTADO
            # ATUAL do pedido — o job que ela continua entra na chave. A mesma
            # resposta 2× com uma continuação EM CURSO segue sendo 1 job (G7:
            # ela é achada ANTES, por `STATUS_EM_CURSO`, e a corrida de dois
            # inserts cai no índice único com a MESMA chave). Depois de uma
            # parada SEM efeito (ex.: a agenda não respondeu), a mesma escolha
            # ganha tentativa nova em vez de ficar presa para sempre.
            extra=str(atual.get("id") or ""))
        if session_id:
            linha["params"]["_conversation_id"] = session_id
            linha["session_id"] = linha.get("session_id") or session_id
        if work_run_id:
            linha["work_run_id"] = work_run_id
            linha["params"]["_work_run_id"] = work_run_id
        if anotacao:
            # CB2: o que a tool IGNOROU desta chamada fica escrito no job (o
            # worker preserva a evidence inicial) — nunca na chave.
            linha["evidence"] = {**dict(linha.get("evidence") or {}), **anotacao}
        job_id, ja = enfileirar_continuacao(cliente, linha)
        if ja is not None:
            # A MESMA resposta já virou continuação (G7): um job só.
            if str(ja.get("status")) in STATUS_EM_CURSO and ja.get("id"):
                resposta = await self._aguardar(str(ja["id"]), work_run_id, params)
                return resposta or {"content": frase_de_pedido_ja_existente({"status": "queued"})}
            return {"content": frase_de_pedido_ja_existente(ja)}
        if not job_id:
            return {"content": ("Nao consegui levar a resposta do segurado a seguradora agora. "
                                "O pedido continua aberto com o mesmo numero; tente de novo em "
                                "instantes e, se persistir, acione um humano.")}
        self._notify(
            session_id,
            ("Perfeito! 🙌 Já estou confirmando esse horário com a seguradora — "
             "te respondo aqui em instantes." if operacao == "agendar" else
             "Perfeito! 🙌 Já estou levando a sua resposta para a seguradora — "
             "te respondo aqui em instantes."),
            linha.get("agent_id"),
        )
        resposta = await self._aguardar(job_id, work_run_id, params)
        return resposta or {"content": format_result({"status": "queued"})}

    def _pedido_irmao_esperando_resposta(self, params: dict, chave: str):
        """RED B4 — `(abertura, params_ajustados, chave_dela)` ou `None`.

        O IRMÃO é um pedido da MESMA corretora, com a MESMA placa, o MESMO CPF e
        a MESMA data do dano, e outra chave (a peça foi reescrita), cujo estado
        ATUAL (a última continuação, ou a abertura) pode continuar e espera
        `responder:<slot>` — ou `agendar`, SÓ quando a chamada traz
        `especificos.escolha_agenda` (CB2; a peça reescrita é ignorada e fica
        anotada). Aí esta chamada é a RESPOSTA dele: a peça nova vai
        em `especificos.peca` (o slot que `respostas_da_chamada` lê) e o campo
        de cima volta a ser o do pedido — nunca um segundo `POST /atendimentos`.

        🔴 CLAUDE.md §7: `company_id` no filtro E de novo na linha. Leitura que
        falha segue o comportamento de `_buscar_pedido_vivo` (fail-open, log):
        o guarda não pode ser o motivo de um atendimento legítimo não abrir.
        """
        import copy as _copy

        from .portal_params import normalizar_data, normalizar_placa

        placa = str(params.get("placa") or "").strip()
        if not (self.company_id and placa and chave):
            return None
        data = normalizar_data(params.get("data_dano"))
        cpf = "".join(ch for ch in str(params.get("cpf_cnpj") or "") if ch.isdigit())
        cliente = self._client()
        try:
            r = (cliente.table("portal_jobs")
                 .select(_COLUNAS_DO_PEDIDO + ", idempotency_key")
                 .eq("company_id", self.company_id)
                 .eq("journey", "abrir_atendimento")
                 .eq("params->>placa", placa)
                 .order("created_at", desc=True)
                 .limit(10).execute())
            linhas = [dict(x) for x in (getattr(r, "data", None) or [])]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalAction] busca do pedido irmao indisponivel (%s)",
                           type(exc).__name__)
            return None
        for job in linhas:
            if str(job.get("company_id") or "") != str(self.company_id):
                continue          # a segunda rede: linha de outra casa não conta
            chave_dela = str(job.get("idempotency_key")
                             or (job.get("params") or {}).get("_idempotency_key") or "")
            if not chave_dela or chave_dela == chave:
                continue
            p_dela = job.get("params") if isinstance(job.get("params"), dict) else {}
            if normalizar_placa(p_dela.get("placa")) != normalizar_placa(placa):
                continue
            if not data or normalizar_data(p_dela.get("data_dano")) != data:
                continue
            cpf_dela = "".join(ch for ch in str(p_dela.get("cpf_cnpj") or "") if ch.isdigit())
            if not cpf or cpf_dela != cpf:
                continue
            if str(job.get("status")) == STATUS_MORTO and not _tem_prova_de_efeito(job.get("evidence")):
                continue
            atual = buscar_ultimo_estado_do_pedido(cliente, self.company_id, job, chave_dela)
            if atual is None:
                continue
            ev = atual.get("evidence") if isinstance(atual.get("evidence"), dict) else {}
            operacao, _slot = acao_esperada(ev)
            if not continuacao_possivel(ev):
                continue
            esp_nova = params.get("especificos") if isinstance(params.get("especificos"), dict) else {}
            # 🔴 CONFIRMAÇÃO CB2 (retomada 1): o irmão que espera `agendar` também
            # recebe a chamada — MAS só quando ela traz `escolha_agenda`. Com a
            # escolha, a chamada é inequivocamente a RESPOSTA dele (📊 red A6.2 /
            # c2 D1: 1º pedido em agenda + peça reescrita + escolha => 2º POST
            # /atendimentos). Sem a escolha, peça diferente continua sendo pedido
            # NOVO: é o caso legítimo do 2º vidro, que o guarda não sabe separar.
            eh_agenda = operacao == "agendar" and bool(esp_nova.get("escolha_agenda"))
            if not (operacao == "responder" or eh_agenda):
                continue
            novo = _copy.deepcopy(params)
            esp = dict(novo.get("especificos") or {})
            peca_nova = str((novo.get("dano") or {}).get("peca") or "").strip()
            if eh_agenda:
                # A peça reescrita NÃO entra na chave nem na resposta: fica
                # registrada na evidence da continuação (quem lê é a equipe).
                novo["_peca_reescrita_ignorada"] = peca_nova
            elif peca_nova and not str(esp.get("peca") or "").strip():
                esp["peca"] = peca_nova
            novo["especificos"] = esp
            novo["dano"] = {**dict(novo.get("dano") or {}),
                            "peca": (p_dela.get("dano") or {}).get("peca")}
            novo["_idempotency_key"] = chave_dela
            return job, novo, chave_dela
        return None

    @staticmethod
    def _ainda_esperando(job: dict) -> str:
        """O pedido pode continuar, mas esta chamada não trouxe o que ele espera."""
        return ("O pedido ja esta aberto e PARADO esperando uma resposta do segurado — "
                "esta chamada nao trouxe essa resposta, entao NAO mandei nada a "
                "seguradora.\n\n" + format_result(job))

    def _run(self, **flat) -> dict:
        return {"content": "portal_action deve ser executada de forma assincrona."}


# ==========================================================================
# 🔴 SPEC-EXTRA-001.10.1 — o que a tool e o VIGIA compartilham (um escritor só)
# ==========================================================================
# Moram DEPOIS da classe de propósito: o guarda de ordem de
# `test_o_portal_nao_abre_duas_vezes_o_mesmo_pedido` lê este arquivo em ordem de
# texto para provar que o `_arun` calcula a chave e busca o pedido vivo ANTES do
# seu insert — e o insert da continuação não é o da abertura.
def e_chave_duplicada(exc: Exception) -> bool:
    """23505 = unique_violation do Postgres (ver `PortalActionTool._e_chave_duplicada`)."""
    alvo = " ".join(str(x) for x in (
        getattr(exc, "code", ""), getattr(exc, "message", ""),
        getattr(exc, "details", ""), exc)).lower()
    return "23505" in alvo or "duplicate key" in alvo or "unique constraint" in alvo


async def envio_liberado(company_id: str, cpf: str = "",
                         journey: str = "abrir_atendimento") -> bool:
    """P-90 — este job pode produzir EFEITO na seguradora? UMA regra, dois leitores.

    🔴 SPEC-EXTRA-001.10.1: saiu do método para o módulo porque agora há dois
    chamadores — a tool (abertura e continuação) e o vigia (releitura). Duas
    cópias de "agente ligado + freio solto + allowlist" seriam duas verdades
    sobre a mesma trava, e no dia em que uma mudasse a outra valeria calada.

    `journey` entra no freio porque a continuação é journey PRÓPRIA: a
    allowlist do canário e a classe de efeito são lidas para ELA.

    Fail-closed em qualquer imprevisto (ver `_envio_liberado`).
    """
    try:
        from portal_worker.journeys import cpf_hash_de, motivo_para_barrar

        from app.services.atlas.attendance_capture import attendance_agent_active
        from app.services.insurer_dispatch_service import acionamento_liberado

        barrado = motivo_para_barrar("vidros_lanternas", journey,
                                     cpf_hash=cpf_hash_de(cpf))
        if barrado:
            logger.info("[PortalAction] %s para no 80%% — %s", journey, barrado)
            return False
        return acionamento_liberado(await attendance_agent_active(company_id))
    except Exception as exc:  # noqa: BLE001
        logger.error("[PortalAction] nao foi possivel confirmar o interruptor do agente "
                     "(%s) — o pedido para no 80%%", type(exc).__name__)
        return False


_COLUNAS_DO_PEDIDO = ("id, company_id, status, journey, params, evidence, error, "
                      "created_at, work_run_id, session_id, agent_id")


def buscar_ultimo_estado_do_pedido(cliente, company_id: str, abertura: dict,
                                   pedido_key: str) -> dict:
    """O job que carrega o ESTADO ATUAL do pedido: a última continuação viva, ou
    a própria abertura.

    🔴 SPEC-EXTRA-001.10.1 — sem isto, a segunda resposta do segurado seria lida
    contra a evidence VELHA da abertura (a agenda de ontem, a sessão de antes),
    e a continuação sairia com a escolha certa sobre a lista errada.

    🔴 CLAUDE.md §7 — SEMPRE `company_id` no filtro, e de novo na linha que
    volta: o backend roda com service role, e a chave do pedido embutir a
    corretora não é guarda (guarda que depende do formato de uma string não é
    guarda). `failed` sem prova de efeito é pulado — o mesmo predicado do
    índice único `idx_portal_jobs_pedido_vivo`.

    🔴 JUIZ B1 (conserto da 001.10.1) — FAIL-CLOSED: leitura que falha devolve
    `None` ("não sei"), NUNCA a abertura. 📊 O juiz mediu o caminho: SELECT
    caiu → a tool lia a evidence VELHA da abertura (`possivel=True`, etapa
    agendar) → um job `agendar` nascia sobre um pedido JÁ agendado. Quem chama
    diz ao agente que não conseguiu conferir e pede para tentar de novo.
    """
    if not (company_id and pedido_key):
        return abertura
    try:
        r = (cliente.table("portal_jobs").select(_COLUNAS_DO_PEDIDO)
             .eq("company_id", company_id)
             .eq("journey", JOURNEY_CONTINUAR)
             .eq("params->>_pedido_key", pedido_key)
             .order("created_at", desc=True)
             .limit(10).execute())
        for linha in (getattr(r, "data", None) or []):
            job = dict(linha)
            if str(job.get("company_id") or company_id) != str(company_id):
                continue          # a segunda rede: linha de outra casa não conta
            if str(job.get("status")) != STATUS_MORTO or _tem_prova_de_efeito(job.get("evidence")):
                return job
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PortalAction] ultima continuacao indisponivel (%s) — "
                       "nada sera enviado (fail-closed)", type(exc).__name__)
        return None
    return abertura


def enfileirar_continuacao(cliente, linha: dict):
    """O ÚNICO escritor de job de continuação (tool e vigia). `(job_id, existente)`.

    `existente` != None = a MESMA continuação já existe viva (a mesma resposta
    dada duas vezes — G7): quem chamou se anexa a ela em vez de criar outra.
    A corrida de dois inserts é decidida pelo índice único parcial
    `idx_portal_jobs_pedido_vivo (company_id, idempotency_key)` e cai no mesmo
    caminho, nunca num erro.
    """
    empresa = str(linha.get("company_id") or "")
    chave = linha.get("idempotency_key")

    def _viva():
        if not chave:
            return None
        r = (cliente.table("portal_jobs")
             .select("id, company_id, status, evidence, error, work_run_id")
             .eq("company_id", empresa).eq("idempotency_key", chave)
             .order("created_at", desc=True).limit(5).execute())
        for j in (getattr(r, "data", None) or []):
            if str(j.get("status")) != STATUS_MORTO:
                return dict(j)
        return None

    try:
        ja = _viva()
        if ja:
            return None, ja
    except Exception as exc:  # noqa: BLE001
        # 🔴 JUIZ P4 (conserto da 001.10.1) — FAIL-CLOSED, coerente com
        # `buscar_ultimo_estado_do_pedido`: sem conseguir ler, não se enfileira.
        # O índice único só protege a MESMA chave; uma leitura cega que segue
        # para o INSERT é uma escrita no portal decidida sem olhar o estado.
        logger.warning("[PortalAction] leitura da continuacao falhou (%s) — nada "
                       "enfileirado (fail-closed)", type(exc).__name__)
        return None, None
    try:
        ins = cliente.table("portal_jobs").insert(linha).execute()
        dados = getattr(ins, "data", None) or []
        return (str(dados[0]["id"]) if dados else None), None
    except Exception as exc:  # noqa: BLE001
        if not e_chave_duplicada(exc):
            logger.error("[PortalAction] continuacao nao enfileirada (%s)", type(exc).__name__)
            return None, None
        logger.info("[PortalAction] continuacao ja existia (23505) — anexando")
        try:
            return None, (_viva() or {"status": "queued"})
        except Exception:  # noqa: BLE001
            return None, {"status": "queued"}


def fechar_work_run(company_id: str, run_id: str, job: dict) -> None:
    """Leva o run ao desfecho que o portal decidiu. Best-effort, sempre.

    🔴 O número do atendimento fica GUARDADO no run (`result_payload`), e
    não só na conversa: 📊 hoje o protocolo mora em `portal_jobs.evidence`,
    que ninguém varre por corretora — a Ficha lê `work_runs`.

    ⛔ Sem `UPDATE` solto: quem transiciona é `WorkRunService`, que já sabe
    gravar o evento na linha do tempo junto.

    🔴 SPEC-EXTRA-001.10.1 — é função de MÓDULO porque o vigia também fecha
    (a releitura que ele dispara não tem tool esperando), e a continuação
    atualiza o MESMO run do pedido: um pedido, um run.
    """
    if not run_id:
        return
    try:
        from app.core.database import get_supabase_client
        from app.services.work.runs import WorkRunService

        svc = WorkRunService(get_supabase_client())
        ev = (job or {}).get("evidence") or {}
        desfecho = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else {}
        estado = ev.get("vidros_estado") if isinstance(ev.get("vidros_estado"), dict) else {}
        numero = str(desfecho.get("codigo_atendimento")
                     or estado.get("codigo_atendimento")
                     or ev.get("protocolo") or "").strip()
        resultado = {
            "numero_do_atendimento": numero,
            "desfecho": str(desfecho.get("tipo") or "") or None,
            "franquias": desfecho.get("franquias") or [],
            "link_area_segurado": str(desfecho.get("link_area_segurado") or "") or None,
        }
        status = str((job or {}).get("status") or "")
        stage = str(ev.get("stage") or "").strip().lower()
        tipo_do_desfecho = str(desfecho.get("tipo") or "").strip().lower()
        pode_continuar = continuacao_possivel(ev)

        # 🔴 SPEC-EXTRA-001.10.1 — AGENDADO conclui, e o agendamento fica no run.
        ag = desfecho.get("agendamento") if isinstance(desfecho.get("agendamento"), dict) else {}
        if status == "done" and tipo_do_desfecho == "agendado" and ag.get("confirmado_pelo_portal") is True:
            resultado["agendamento"] = {k: str(ag.get(k) or "") for k in
                                        ("loja", "endereco", "data", "horario")}
            svc.concluir(run_id, company_id,
                         (f"Atendimento {numero} agendado: {ag.get('data') or ''} "
                          f"{ag.get('horario') or ''} — {ag.get('loja') or 'loja'}").strip(),
                         resultado)
            return
        # 🔴 A ESPERA DO SEGURADO NÃO É FALHA. Com a continuação possível, o
        # pedido fica ABERTO em progresso: quem o leva adiante é a próxima
        # resposta dele, e a Fila mostra "aguardando o segurado", não "falhou".
        if pode_continuar and (
                (status == "done" and tipo_do_desfecho in ("agenda", "vistoria",
                                                           "vistoria_opcional",
                                                           "decidir_vistoria"))
                or (status in ("needs_human", "failed")
                    and stage in ESTAGIOS_QUE_O_SEGURADO_RESPONDE + ESTAGIOS_TECNICOS
                    + ("horario_indisponivel",))):
            svc.marcar_progresso(run_id, company_id,
                                 ("aguardando_escolha_do_segurado"
                                  if tipo_do_desfecho == "agenda" and status == "done"
                                  else (stage or "aguardando_resposta_do_segurado")), 80)
            return
        # 🔴 JUIZ B4 (e): `completed` so com o job `done`.
        # 🔴 B-N2: `agenda` e `vistoria` SEM continuação terminam `done` e AINDA
        # PRECISAM DA EQUIPE — concluir o run aqui fazia a Fila mostrar
        # "concluido" e ninguem ia atras.
        if status == "done" and tipo_do_desfecho in ("agenda", "vistoria"):
            svc.marcar_progresso(run_id, company_id, tipo_do_desfecho, 80)
            svc.falhar(run_id, company_id,
                       "portal_aguarda_a_equipe",
                       (f"O atendimento {numero} EXISTE na seguradora e o portal "
                        f"pediu {'agendamento com a loja' if tipo_do_desfecho == 'agenda' else 'vistoria'}. "
                        "NÃO reexecute: a equipe conclui no portal por esse número."),
                       retryable=False)
            return
        if status == "done" and tipo_do_desfecho != "agendado":
            # 🔴 Número lido = o trabalho DEU resultado. Marcar como falha um
            # pedido que existe na seguradora é a pior linha num relatório.
            svc.concluir(run_id, company_id,
                         (f"Atendimento {numero} aberto na seguradora" if numero
                          else "Acionamento concluído no portal"),
                         resultado)
            return
        svc.marcar_progresso(run_id, company_id, stage or "parou_no_portal", 60)
        # O pedido EXISTE e parou: a equipe precisa ver isso na Fila. A
        # mensagem carrega o numero, que é por onde ela retoma no portal.
        if numero:
            svc.falhar(run_id, company_id,
                       "portal_parou_com_pedido_aberto",
                       (f"O atendimento {numero} EXISTE na seguradora e parou em "
                        f"`{stage or ('agendamento_nao_confirmado' if tipo_do_desfecho == 'agendado' else 'etapa desconhecida')}`. NÃO "
                        "reexecute: a equipe conclui no portal por esse número."),
                       retryable=False)
            return
        svc.falhar(run_id, company_id,
                   "portal_sem_desfecho",
                   "O portal parou antes de gerar o número do atendimento — "
                   "a equipe conclui na mão.",
                   retryable=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PortalAction] work_run nao atualizado (%s)", type(exc).__name__)


