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
    build_portal_params,
    chave_de_idempotencia,
    descricao_da_tool,
    format_result,
    frase_de_pedido_ja_existente,
    resumo_da_tela_desconhecida,
    slug_da_seguradora,
)

logger = logging.getLogger(__name__)

POLL_TIMEOUT_S = 150
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
        description=("Respostas das perguntas especificas ja coletadas na conversa, e tambem "
                     "cidade_para_o_servico. A propria ferramenta diz QUAIS chaves usar quando "
                     "faltar alguma (ela devolve a pergunta pronta com o formato da resposta). "
                     "Exemplos: cidade_para_o_servico, onde_realizar_o_servico, aceita_reparo, "
                     "pelicula, lado_motorista_ou_carona, porta_dianteira_ou_traseira, "
                     "posicao_do_trincado, tamanho_do_trincado, pecas_lataria (LISTA). "
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

    async def _envio_liberado(self, cpf: str = "") -> bool:
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
        try:
            from portal_worker.journeys import cpf_hash_de, motivo_para_barrar

            from app.services.atlas.attendance_capture import attendance_agent_active
            from app.services.insurer_dispatch_service import acionamento_liberado

            # 🔴 A TERCEIRA CONDICAO — 18/08/2026.
            #
            # As duas de cima ("agente ligado" + "freio de emergencia solto")
            # sao as MESMAS do corredor de WhatsApp. Era esse o defeito: soltar
            # o freio para testar um eletricista armava o portal de vidros no
            # mesmo segundo, sem ninguem pedir. Nao existia jeito de liberar um
            # sem liberar o outro.
            #
            # `PORTAL_EFEITO_MATERIAL_LIBERADO` e o interruptor que faltava. E
            # e por CLASSE DE EFEITO, nao por portal: barrar "vidros" pelo nome
            # deixaria a proxima journey material nascer solta.
            # 🔴 P0-6 — AQUI O JOB AINDA NAO EXISTE, entao a chave e o CPF.
            #
            # Este e o ponto de CRIACAO: `job:<uuid>` so existe depois do
            # insert. Por isso a allowlist aceita as duas formas, e este lado
            # usa `cpf:<hash>` — o mesmo hash que o worker recalcula do
            # `params`, pela MESMA funcao, para os dois nunca discordarem.
            barrado = motivo_para_barrar("vidros_lanternas", "abrir_atendimento",
                                         cpf_hash=cpf_hash_de(cpf))
            if barrado:
                logger.info("[PortalAction] pedido para no 80%% — %s", barrado)
                return False

            return acionamento_liberado(await attendance_agent_active(self.company_id))
        except Exception as exc:  # noqa: BLE001
            logger.error("[PortalAction] nao foi possivel confirmar o interruptor do agente "
                         "(%s) — o pedido para no 80%%", type(exc).__name__)
            return False

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
                 .select("id, status, evidence, error, created_at, work_run_id")
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
        alvo = " ".join(str(x) for x in (
            getattr(exc, "code", ""), getattr(exc, "message", ""),
            getattr(exc, "details", ""), exc)).lower()
        return "23505" in alvo or "duplicate key" in alvo or "unique constraint" in alvo

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
        """Leva o run ao desfecho que o portal decidiu. Best-effort, sempre.

        🔴 O número do atendimento fica GUARDADO no run (`result_payload`), e
        não só na conversa: 📊 hoje o protocolo mora em `portal_jobs.evidence`,
        que ninguém varre por corretora — a Ficha lê `work_runs`.

        ⛔ Sem `UPDATE` solto: quem transiciona é `WorkRunService`, que já sabe
        gravar o evento na linha do tempo junto. Escrever o update à mão aqui
        seria a segunda mão escrevendo na mesma tabela.
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
            if status == "done" or numero:
                # 🔴 Número lido = o trabalho DEU resultado, mesmo que o job
                # tenha terminado `needs_human`. Marcar como falha um pedido que
                # existe na seguradora é a pior linha possível num relatório.
                svc.concluir(run_id, self.company_id,
                             (f"Atendimento {numero} aberto na seguradora" if numero
                              else "Acionamento concluído no portal"),
                             resultado)
                return
            svc.marcar_progresso(run_id, self.company_id,
                                 str(ev.get("stage") or "parou_no_portal"), 60)
            svc.falhar(run_id, self.company_id,
                       "portal_sem_desfecho",
                       "O portal parou antes de gerar o número do atendimento — "
                       "a equipe conclui na mão.",
                       retryable=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalAction] work_run nao atualizado (%s)", type(exc).__name__)

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
            self._client().table("portal_jobs").update({
                "evidence": {**ev, "tela_cega_registrada": True},
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
                # Pedido terminado (done/needs_human): a resposta ja existe, e
                # abrir outro seria o segundo atendimento. Sai antes de gastar
                # qualquer consulta a mais.
                return {"content": frase_de_pedido_ja_existente(existente)}

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
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            await asyncio.sleep(POLL_EVERY_S)
            try:
                r = self._client().table("portal_jobs").select("status, evidence, error").eq("id", job_id).limit(1).execute()
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
                    }).eq("id", job_id).execute()
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
        # Estourou os 150s. Aqui morava o defeito: a tool dizia "enfileirei, o
        # worker nao processou" e o agente chamava de novo — criando o segundo
        # atendimento. Quem se anexou a um job em curso recebe a verdade do que
        # aconteceu (nada foi enfileirado nesta chamada) e a instrucao de nao repetir.
        if reaproveitado:
            return {"content": frase_de_pedido_ja_existente({"status": "queued"})}
        return {"content": format_result({"status": "queued"})}

    def _run(self, **flat) -> dict:
        return {"content": "portal_action deve ser executada de forma assincrona."}
