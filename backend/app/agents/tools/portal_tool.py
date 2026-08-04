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
    format_result,
    frase_de_pedido_ja_existente,
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
        description=("Respostas das perguntas especificas do 80%, quando ja coletadas na conversa. "
                     "Chaves: pelicula, porta_dianteira_ou_traseira, lado_motorista_ou_carona, "
                     "posicao_do_trincado, tamanho_do_trincado. Use 'nao sabe' SO se o segurado "
                     "realmente nao souber — nunca para agilizar: o portal precisa disso para "
                     "pedir o vidro certo."))
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NAO preencher)")


class PortalActionTool(BaseTool):
    name: str = "portal_action"
    description: str = (
        "Abre o atendimento de VIDROS/farois/lanternas/retrovisores no portal da seguradora. "
        # SPEC-065 7.5 — a frase antiga pedia TRES coisas ("CPF, data do dano e o relato") para
        # um portal que pergunta CINCO, e "o relato do que aconteceu" era satisfeito por "quebrou
        # o vidro", que nao nomeia peca nenhuma. 📊 33 dos 39 acionamentos pararam no meio, e o
        # motivo mais caro era sempre o mesmo: descobrir dentro do portal o que faltava.
        # Depois que o portal abre, cada dado que falta custa o atendimento inteiro.
        "Use SO quando voce ja tiver, da conversa: CPF do titular, data do dano, QUAL PECA quebrou "
        "(para-brisa / vidro de porta / vidro de janela / vigia / retrovisor / farol / lanterna — "
        "'quebrou o vidro' NAO serve, nao diz qual), COMO aconteceu, ONDE (cidade ou rodovia) e, se "
        "for vidro de porta ou para-brisa, as respostas especificas: tem pelicula (insulfilm)? porta "
        "dianteira ou traseira? lado do motorista ou do carona? posicao e tamanho do trincado? "
        "Pergunte tudo ANTES de chamar. A ferramenta busca SOZINHA os dados reais da apolice (placa, veiculo, endereco, "
        "seguradora) na InfoCap — NAO peca placa/CEP/endereco ao cliente. Se houver mais de uma apolice AUTO "
        "ativa, ela devolve as opcoes para voce perguntar qual. Ela avisa o cliente que esta abrindo e volta "
        "com o resultado. NAO finaliza sozinha o pedido."
    )
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

    async def _envio_liberado(self) -> bool:
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
            from app.services.atlas.attendance_capture import attendance_agent_active
            from app.services.insurer_dispatch_service import acionamento_liberado

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
            r = (self._client().table("portal_jobs")
                 .select("id, status, evidence, error, created_at")
                 .eq("company_id", self.company_id)
                 .eq("idempotency_key", chave)
                 .neq("status", STATUS_MORTO)
                 .order("created_at", desc=True)
                 .limit(1).execute())
            return dict(r.data[0]) if r.data else None
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
            if provider is None or not hasattr(provider, "vehicle") or not key:
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
        enviar = await self._envio_liberado()
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

        # 4) Enfileira o job para o portal-worker — so quando nao havia um vivo.
        if not reaproveitado:
            try:
                ins = self._client().table("portal_jobs").insert({
                    "company_id": self.company_id,
                    "portal_key": "vidros_lanternas",
                    "journey": "abrir_atendimento",
                    "params": params,
                    "status": "queued",
                    "idempotency_key": chave or None,  # "" nunca vai para o banco
                    "session_id": session_id or None,  # o caminho de volta a conversa
                    "agent_id": agent_id,
                }).execute()
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
