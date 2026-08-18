"""Ferramenta de acionamento de seguradora para o ATENDENTE (SPEC-017 P5).

Papel attendance usa esta tool quando o levantamento estiver completo:
- valida elegibilidade operacional (slots mínimos do playbook);
- monta o PLANO exato do acionamento;
- devolve briefing para o atendente informar o cliente com honestidade
  ("estou acionando" só quando for real; em simulação, registra pendência).

P-90 (04/08/2026) — O QUE SEGURA O ENVIO REAL É UMA COISA SÓ.
Era o gate S17-6 (`INSURER_DISPATCH_LIVE`, fechado por padrão), criado quando o
Founder testava no próprio celular. Decisão dele, dita duas vezes: a trava passa
a ser `agents.is_active` do agente de atendimento — "tudo pronto e funcionando,
mas o agente tem que continuar desligado; só pode funcionar se clicar em LIGAR
AGENTE". Com o agente desligado esta tool prepara o plano e NÃO envia nada, que
é exatamente o que ela fazia com o gate fechado. Resta um freio de emergência
por env (`ACIONAMENTO_FREIO_DE_EMERGENCIA`), solto por padrão, que fecha este
corredor e o do portal de vidros de uma vez.

Playbook v1: allianz-residencial-whatsapp@v1 (eletricista, chaveiro, encanador,
eletrodomésticos).
"""

import logging
import re
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# A FAMÍLIA QUE TEM PORTAL — a fronteira entre "handoff" e "outro caminho"
# --------------------------------------------------------------------------- #
# 📊 Medido em 04/08/2026: `vidros` cai em `subservico_invalido` em 10 dos 13
# corredores de WhatsApp. Só Azul, Porto e Zurich atendem vidros por lá.
#
# E o portal público (abraseuatendimento.com.br) atende dezenas de seguradoras
# — e cobre mais que vidro: a tela da Porto diz literalmente "Vidros,
# faróis/lanternas (E retrovisores)". Por isso esta lista é MAIS LARGA que o
# `_canonizar` do corredor, que só conhece vidro/parabrisa/retrovisor.
#
# Ela é deliberadamente ESTREITA em outra direção: um item aqui dentro faz o
# sistema oferecer o portal em vez de um humano. Colocar aqui algo que o portal
# não conserta troca um handoff honesto por uma promessa vazia — o que é pior.
# Por isso nada de "amassado", "pintura", "lataria", "roda", "pneu": a Porto
# oferece roda/pneu, mas 📊 Yelum e Tokio não, e o mapa não foi medido.
_FAMILIA_COM_PORTAL = (
    "vidro", "parabrisa", "para-brisa", "para brisa", "windshield",
    "retrovisor", "espelho", "farol", "farolete", "farolim", "lanterna",
    "vigia", "insulfilm", "pelicula",
)


def _e_familia_de_vidros(subservico: Optional[str]) -> bool:
    """PURO: este trabalho tem portal? Decide handoff × portal quando o corredor
    de WhatsApp da seguradora não atende.

    Sinistro (colisão, roubo, incêndio) JAMAIS entra aqui — ele é handoff
    sempre, e é a regra que mais importa do produto inteiro.
    """
    t = (subservico or "").strip().lower()
    if not t:
        return False
    return any(p in t for p in _FAMILIA_COM_PORTAL)


# --------------------------------------------------------------------------- #
# O QUE É DADO DE VERDADE — conferência determinística, fora do alcance do LLM
# --------------------------------------------------------------------------- #
# O incidente de 2026-07-10 ("placa e telefone inventados foram parar na
# seguradora") gerou um guarda que conferia só o telefone, e o conferia mal.
# Estas três funções são o guarda de verdade. Todas seguem a mesma regra: só
# reprovam o que É comprovadamente inválido, nunca o que apenas parece estranho.
# Reprovar dado verdadeiro é o defeito que faz alguém desligar o guarda.

# DDDs em uso no Brasil. A lista existe porque `00` e `10` não são DDD, e um
# telefone com DDD inexistente é invenção com cara de número.
_DDD_BR = frozenset({
    11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35,
    37, 38, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64,
    65, 66, 67, 68, 69, 71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88,
    89, 91, 92, 93, 94, 95, 96, 97, 98, 99,
})

# Antiga (ABC1234) e Mercosul (ABC1D23) no MESMO padrão: a 5ª posição é o único
# ponto em que elas divergem, e ali cabe letra ou dígito.
_PLACA_BR = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")


def _digitos(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _digito_verificador(numeros, pesos) -> int:
    resto = sum(n * p for n, p in zip(numeros, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(valor) -> bool:
    """CPF pelo DÍGITO VERIFICADOR, não pelo comprimento.

    `12345678901` tem onze dígitos e não é CPF de ninguém. Um CPF errado não
    atrasa o atendimento: ele abre o chamado na apólice de outra pessoa.
    """
    d = [int(c) for c in _digitos(valor)]
    if len(d) != 11 or len(set(d)) == 1:  # 111.111.111-11 fecha a conta e não existe
        return False
    return (d[9] == _digito_verificador(d[:9], range(10, 1, -1))
            and d[10] == _digito_verificador(d[:10], range(11, 1, -1)))


def cnpj_valido(valor) -> bool:
    """CNPJ pelo dígito verificador. Existe porque o titular pode ser PESSOA
    JURÍDICA — condomínio e empresa são carteira inteira no residencial, e as
    URAs pedem "CPF ou CNPJ". Reprovar um CNPJ verdadeiro travaria o corredor."""
    d = [int(c) for c in _digitos(valor)]
    if len(d) != 14 or len(set(d)) == 1:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return (d[12] == _digito_verificador(d[:12], pesos1)
            and d[13] == _digito_verificador(d[:13], [6] + pesos1))


def documento_br_valido(valor) -> bool:
    """O que o campo `titular_cpf` de fato aceita: CPF **ou** CNPJ."""
    return cpf_valido(valor) or cnpj_valido(valor)


def placa_br_valida(valor) -> bool:
    """Placa nos dois formatos legais. Separador e caixa não importam."""
    return bool(_PLACA_BR.match(re.sub(r"[^A-Za-z0-9]", "", str(valor or "")).upper()))


def telefone_br_valido(valor) -> bool:
    """Telefone brasileiro pelas regras que a ANATEL de fato impõe.

    Substitui `(\\d)\\1{4,}` — "cinco dígitos repetidos" — que reprovava
    `48999990000`: um celular real de Florianópolis, e o número do
    `CASO_COMPLETO` dos testes deste repositório. Cinco repetições cabem num
    número verdadeiro; DDD inexistente e celular sem o 9 inicial, não.
    """
    d = _digitos(valor)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]  # código do país
    if len(d) not in (10, 11) or len(set(d)) == 1:
        return False
    if int(d[:2]) not in _DDD_BR:
        return False
    assinante = d[2:]
    if len(d) == 11 and assinante[0] != "9":
        return False   # celular tem 9 dígitos começando em 9 desde 2016
    if len(d) == 10 and assinante[0] not in "2345":
        return False   # fixo começa em 2-5
    # Sete repetições seguidas não sobrevivem a um número real; cinco sim.
    return not re.search(r"(\d)\1{6,}", d)


class InsurerDispatchInput(BaseModel):
    subservice: str = Field(description=(
        "Subserviço. Residencial: eletricista | chaveiro | encanador | "
        "desentupimento | maquina_de_lavar | eletrodomesticos. "
        # 🔴 SPEC-082: `maquina_de_lavar` e um subservico PROPRIO, e nao um
        # `eletrodomesticos` generico. Motivo medido: a URA pede a tecla do
        # aparelho numa lista de quinze, e o generico responde "15 - Outros".
        # Com o subservico especifico a tecla e `14`, e o chamado nasce com
        # o aparelho certo escrito nele.
        "Use `maquina_de_lavar` quando o segurado falar em maquina de lavar, "
        "lavadora, lava-roupas ou lava-e-seca. Para OUTRO eletrodomestico "
        "(geladeira, fogao, micro-ondas, ar-condicionado) use `eletrodomesticos`. "
        "AUTO: guincho | bateria | pneu | chaveiro."))
    insurer_key: Optional[str] = Field(default=None, description=(
        "Seguradora da apólice (allianz | porto | hdi | yelum | tokio | alfa | azul | bradesco | mapfre | zurich). "
        "ATENÇÃO: apólice Liberty = use 'yelum' (a Liberty foi rebatizada para Yelum — MESMA seguradora, MESMO corredor). "
        "Itaú = 'porto'. Descubra pela InfoCap. OBRIGATÓRIO SEMPRE: sem seguradora não há acionamento — vira handoff humano. Nunca assuma uma seguradora que o cliente não disse."))
    titular_nascimento: Optional[str] = Field(default=None, description=(
        "[auto Mapfre] Data de nascimento do titular (dd/mm/aaaa) — a Mapfre valida identidade com ela"))
    line_kind: Optional[str] = Field(default=None, description="Linha: auto | residencial. Para carro use 'auto'.")
    titular_cpf: Optional[str] = Field(default=None, description="CPF do titular da apólice (somente dígitos)")
    # --- Residencial ---
    # 🔴 SPEC-082 — a URA pergunta marca e modelo em telas SEPARADAS:
    # "Qual a marca ?" e depois "E o modelo completo?". Um campo so, com os
    # dois juntos, responderia a primeira tela com o texto da segunda.
    #
    # 📊 Respostas reais da sessao que gerou o protocolo 51022010:
    #   marca  -> "Eletrolux"
    #   modelo -> "Turbo capacidade 15kg"   (nao precisa ser exato)
    aparelho_marca: Optional[str] = Field(default=None, description=(
        "[eletrodomestico] Marca do aparelho (Brastemp, Electrolux, Consul...). "
        "Pergunte ao segurado; ele nao precisa saber o modelo exato."))
    aparelho_modelo: Optional[str] = Field(default=None, description=(
        "[eletrodomestico] Modelo ou descricao do aparelho (ex.: 'Turbo 15kg'). "
        "Aproximado serve — a seguradora aceita descricao livre."))
    endereco_numero: Optional[str] = Field(default=None, description="[residencial] Número da residência do endereço da apólice")
    periodo_preferido: Optional[str] = Field(default=None, description="[residencial] Período: manha | tarde")
    risco_confirmado_sem_fumaca: Optional[str] = Field(default=None, description="[residencial elétrica] 'sim' se NÃO há fumaça/faísca/cheiro de queimado")
    aparelho_marca_modelo: Optional[str] = Field(default=None, description="[residencial eletrodomésticos] marca e modelo")
    aparelho_idade: Optional[str] = Field(default=None, description="[residencial eletrodomésticos] idade aproximada")
    # --- Auto ---
    veiculo_placa: Optional[str] = Field(default=None, description="[auto] Placa (a InfoCap resolve; NÃO invente)")
    local_atual: Optional[str] = Field(default=None, description="[auto] Onde o veículo está agora (endereço/CEP + referência)")
    local_destino: Optional[str] = Field(default=None, description="[auto guincho] Para onde levar o veículo")
    pessoa_no_local: Optional[str] = Field(default=None, description="[auto] Nome de quem está com o veículo no local")
    quando: Optional[str] = Field(default=None, description="[auto] 'agora' (urgência) ou uma data para agendar")
    ponto_referencia: Optional[str] = Field(default=None, description="[auto] Ponto de referência do local (ou 'não tem')")
    # --- Comuns ---
    telefone_contato: Optional[str] = Field(default=None, description="Telefone de contato com DDD (somente dígitos)")
    problema_descricao: Optional[str] = Field(default=None, description="Descrição curta do problema relatado pelo cliente")
    dados_confirmados: Optional[bool] = Field(default=None, description=(
        "[auto] true SOMENTE depois de você MOSTRAR ao cliente na conversa a placa, o veículo, o local, o destino "
        "e o telefone, e ele CONFIRMAR explicitamente. Sem essa confirmação o acionamento não sai."))
    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NÃO preencher)")


class InsurerDispatchTool(BaseTool):
    name: str = "insurer_dispatch"
    description: str = (
        "Prepara/aciona a assistência na seguradora pelo WhatsApp quando o levantamento estiver completo E a "
        "apólice tiver assistência confirmada. Cobre AUTO (guincho/bateria/pneu/chaveiro) e residencial "
        "(eletricista/chaveiro/encanador/eletrodomésticos). Para AUTO informe insurer_key (da InfoCap) e "
        "line_kind='auto'. Retorna o plano do acionamento ou os dados que ainda faltam. NUNCA diga ao cliente "
        "que acionou se o retorno indicar simulação/teste. Em modo TESTE o fluxo é executado por completo e "
        "CANCELADO na confirmação final (nada é aberto); corredor validado em modo LIVE completa ponta a ponta."
    )
    args_schema: Type[BaseModel] = InsurerDispatchInput

    company_id: str = ""
    case_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, case_id: str = "", supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.case_id = str(case_id or "")
        self.supabase_client = supabase_client

    # Mantido só para quem ainda referencia o nome; NÃO é mais fallback de
    # resolução — ver `_resolve_playbook_ref`. Um "default" de corredor mandava
    # o segurado de uma seguradora para o WhatsApp de outra.
    _PLAYBOOK_REF = "allianz-residencial-whatsapp@v1"

    def _resolve_playbook_ref(self, kwargs: dict) -> tuple:
        """Resolve (playbook_ref, insurer_key). **Sem corredor = sem acionamento.**

        Aqui existia, na última linha, ``return self._PLAYBOOK_REF, "allianz"`` —
        um fallback para o corredor RESIDENCIAL DA ALLIANZ sempre que a linha não
        fosse auto e a seguradora não tivesse corredor próprio.

        Duas coisas quebravam ao mesmo tempo, e a segunda é a grave:

        1. o **roteiro** era o da Allianz — passos de URA, âncoras e freios de
           uma seguradora aplicados à conversa de outra;
        2. e `insurer_key` voltava como ``"allianz"``, então o telefone de
           destino era resolvido como Allianz. **A mensagem do segurado da Porto
           iria para o WhatsApp da Allianz.**

        O ramo que trata a ausência de corredor já existia logo abaixo, e está
        certo — *"não tenho corredor… acione um atendente humano"*. Ele só era
        **inalcançável**, porque este fallback garantia que `playbook_ref` nunca
        fosse vazio.

        A regra do Founder, 03/08/2026: *"tudo que não tiver corredor e
        sinistros, na parte de acionamento vira handoff"*. É o que passa a
        acontecer — e handoff com motivo escrito, não silêncio.

        Devolver ``(None, insurer)`` preserva o nome da seguradora que o cliente
        pediu, para o handoff poder dizer de quem se trata.
        """
        from app.services.corridor_playbooks import resolve_playbook_ref

        insurer = str(kwargs.get("insurer_key") or "").strip()
        line = str(kwargs.get("line_kind") or "").strip().lower()
        subservice = str(kwargs.get("subservice") or "").strip().lower()
        if not line:
            # `chaveiro` NÃO entra aqui de propósito: ele existe nos dois lados —
            # chaveiro do carro e chaveiro da casa. Enquanto só a Allianz tinha
            # corredor residencial, deduzir era quase inofensivo. Com HDI e Porto
            # residenciais no ar, um chaveiro de CARRO sem `line_kind` iria para
            # o menu residencial e pediria o número da casa a quem está parado no
            # acostamento.
            #
            # Ambíguo não se deduz: pergunta-se.
            line = "auto" if subservice in ("guincho", "bateria", "pneu",
                                            "pane_seca", "vidros") else ""
            if not line and subservice in ("chaveiro",):
                return None, insurer

        # Sem seguradora não há para onde mandar. Adivinhar o destino é pior que
        # não acionar: a conversa de um segurado iria para outra empresa.
        if not insurer:
            return None, ""

        if line == "auto":
            return resolve_playbook_ref(insurer, "auto"), insurer

        # Residencial, ou linha não declarada: tenta residencial e, se não
        # houver, tenta auto — mas SEMPRE da seguradora pedida, nunca de outra.
        return (resolve_playbook_ref(insurer, "residencial")
                or resolve_playbook_ref(insurer, "auto")), insurer

    def _attendance_agent_id(self) -> Optional[str]:
        """Resolve o agente ATENDENTE (role attendance) — a integracao WhatsApp e
        vinculada a ele; sem o agent_id o lookup e ESTRITO e volta None (mesmo bug
        do heads-up de vidros). Best-effort."""
        client = getattr(self.supabase_client, "client", self.supabase_client)
        if client is None:
            return None
        try:
            res = client.table("agents").select("id").eq(
                "company_id", self.company_id).eq("agent_role", "attendance").eq(
                "is_active", True).limit(1).execute()
            if res.data:
                return str(res.data[0]["id"])
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _extract_slots(kwargs: dict) -> tuple:
        subservice = str(kwargs.get("subservice") or "").strip().lower()
        slots = {
            k: v for k, v in kwargs.items()
            if k not in ("subservice", "session_id", "insurer_key", "line_kind", "dados_confirmados")
            and v not in (None, "")
        }
        return subservice, slots

    def _run(self, **kwargs) -> dict:
        """Valida e monta o plano. NUNCA envia nada — o envio real (gate aberto)
        acontece só no _arun. Honestidade: sem envio, sem alegar acionamento."""
        from app.services.corridor_playbooks import SUBSERVICO_INVALIDO
        from app.services.insurer_dispatch_service import build_dry_run_plan

        subservice, slots = self._extract_slots(kwargs)
        playbook_ref, insurer_key = self._resolve_playbook_ref(kwargs)
        if not playbook_ref:
            quem = insurer_key or "essa seguradora"
            # SPEC-065 — este ramo é o MAIOR dos dois, e por isso o desvio
            # precisa estar aqui também.
            #
            # 📊 Existem 13 corredores de WhatsApp. O portal de vidros atende
            # DEZENAS de seguradoras. Ou seja: a maioria das seguradoras nem
            # chega na checagem de subserviço lá embaixo — ela para AQUI, por
            # não ter corredor nenhum. Um segurado da HDI, da Mapfre ou da
            # Bradesco com o vidro quebrado era mandado para um humano nesta
            # linha, sem que ninguém tivesse perguntado ao portal.
            #
            # Sinistro continua handoff. Só a família com portal desvia.
            if _e_familia_de_vidros(subservice):
                return {"status": "use_portal", "handoff_necessario": False, "content": (
                    f"Não existe corredor de WhatsApp para {quem}, MAS O PORTAL OFICIAL "
                    "DE VIDROS ATENDE DEZENAS DE SEGURADORAS — provavelmente esta. NÃO "
                    "chame `request_human_agent` e NÃO diga ao cliente que não dá. Chame "
                    "`portal_action` agora, com o CPF do titular, a data do dano e o relato. "
                    "Se o portal não atender esta seguradora, ELE avisa — e só aí é handoff.")}
            return {"status": "sem_corredor", "handoff_necessario": True, "content": (
                f"Não existe corredor de acionamento para {quem} neste serviço. "
                "NÃO tente acionar por outro caminho e NÃO invente protocolo. "
                "Chame `request_human_agent` agora, com o motivo "
                f"'sem corredor para {quem}', e diga ao cliente que um atendente "
                "da corretora vai assumir — os dados que ele já deu ficam registrados.")}

        # GUARDA ANTI-INVENÇÃO (incidente 2026-07-10: placa e telefone inventados
        # foram parar na seguradora). Determinístico, fora do alcance do LLM.
        #
        # 📊 03/08/2026: o comentário citava PLACA e o código conferia SÓ telefone.
        # `placa='1'` e `placa='nao sei'` chegavam a `ready_to_send` — a placa
        # errada abre chamado para o carro de outra pessoa. E o guarda de telefone
        # (`(\d)\1{4,}`) reprovava `48999990000`, que é um celular REAL de
        # Florianópolis e é o `CASO_COMPLETO` dos testes deste próprio repositório.
        # Guarda que reprova o verdadeiro ensina a desligar o guarda.
        is_auto = "auto" in str(playbook_ref)
        for campo, valor, ok, comojá in (
            ("telefone_contato", kwargs.get("telefone_contato"), telefone_br_valido,
             "o telefone REAL de quem estará com o veículo (com DDD)"),
            ("veiculo_placa", kwargs.get("veiculo_placa"), placa_br_valida,
             "a placa REAL do veículo (formato ABC1D23 ou ABC1234) — confirme na apólice, "
             "na InfoCap ou com o cliente"),
            ("titular_cpf", kwargs.get("titular_cpf"), documento_br_valido,
             "o CPF (ou CNPJ) REAL do titular da apólice"),
        ):
            if str(valor or "").strip() and not ok(valor):
                return {"status": "missing_data", "missing": [campo], "content": (
                    f"O valor informado em `{campo}` não é válido — não passa na conferência "
                    "determinística de formato. NÃO envie isso à seguradora e NÃO tente adivinhar: "
                    f"descubra {comojá}. Se o cliente não souber, chame `request_human_agent`.")}
        if is_auto and not kwargs.get("dados_confirmados"):
            placa = str(kwargs.get("veiculo_placa") or "—")
            return {"status": "confirm_first", "content": (
                "ANTES de acionar, CONFIRME com o cliente NA CONVERSA (mensagem única): "
                f"placa {placa}, o que houve, local atual, destino e telefone de contato. "
                "Se o cliente corrigir qualquer dado, use o valor corrigido. Depois chame de novo com "
                "dados_confirmados=true. ATENÇÃO: NADA foi acionado ainda — é PROIBIDO dizer ao cliente "
                "que a seguradora foi acionada/contatada. Só afirme acionamento quando ESTA ferramenta "
                "retornar status 'dispatched'. Assim que o cliente confirmar, chame de novo IMEDIATAMENTE "
                "(na mesma resposta), não deixe para depois.")}

        plan = build_dry_run_plan(playbook_ref, subservice, slots)

        if not plan.get("ok"):
            # SENTINELA, NÃO CAMPO.
            #
            # `subservico_invalido` diz "esta seguradora não faz este trabalho
            # por este canal" — é irmão de `sem_corredor`, e a resposta certa é a
            # mesma: handoff. Traduzi-lo em `missing_data` mandava o LLM perguntar
            # ao cliente um dado que não existe; o cliente respondia qualquer
            # coisa, o slot continuava faltando, e o laço nunca terminava.
            #
            # 📊 03/08/2026, varrendo `_PLAYBOOKS` com
            # `missing_slots_for_subservice(pb, sub, {})`: `colisao`, `roubo` e
            # `incendio` — os TRÊS sinistros — caem aqui em **13 de 13**
            # corredores, e `vidros` em 10. O caminho mais grave do produto era
            # o que perguntava ao segurado o nome de um campo inexistente.
            if SUBSERVICO_INVALIDO in (plan.get("missing_slots") or []):
                trabalho = subservice or "esse serviço"
                quem = insurer_key or "essa seguradora"

                # SPEC-065 — "sem corredor" não é o mesmo que "sem caminho".
                #
                # 📊 Medido em 04/08/2026 varrendo os 13 corredores: `vidros`
                # cai aqui em **10 deles**. Só Azul, Porto e Zurich têm vidros
                # no WhatsApp da seguradora.
                #
                # E o portal público de vidros atende DEZENAS de seguradoras —
                # Yelum, Tokio, HDI, Allianz, Bradesco, Mapfre, Itaú, Mitsui…
                # (📊 o dropdown de abraseuatendimento.com.br começa em ALFA,
                # ALIRO, ALLIANZ, AXA, AZUL e segue).
                #
                # Ou seja: em 10 de 13 seguradoras, um segurado que dizia
                # "quebrei o vidro" era mandado para um humano — enquanto
                # existia um caminho automático servindo justamente ela. O
                # produto entregava handoff onde tinha serviço.
                #
                # Sinistro continua handoff SEMPRE, sem exceção. O que muda é
                # só a família de vidros, que é a que tem portal.
                if _e_familia_de_vidros(subservice):
                    return {"status": "use_portal", "handoff_necessario": False,
                            "missing": [], "content": (
                                f"A {quem} não faz '{trabalho}' pelo WhatsApp de assistência, "
                                "MAS ISSO NÃO É UM BECO: o portal oficial de vidros atende esta "
                                "seguradora. NÃO chame `request_human_agent` e NÃO diga ao cliente "
                                "que não dá. Chame a ferramenta `portal_action` agora, com o CPF do "
                                "titular, a data do dano e o relato do que aconteceu. Se o portal "
                                "não atender esta seguradora, ELE vai te dizer — e só aí é handoff.")}

                return {"status": "sem_corredor", "handoff_necessario": True,
                        "missing": [], "content": (
                            f"A {quem} não atende '{trabalho}' por este canal de assistência — "
                            "e sinistro (colisão, roubo, incêndio) NUNCA se abre por aqui. "
                            "NÃO peça mais nenhum dado ao cliente por causa disto: não falta dado, "
                            "falta caminho. NÃO tente acionar por outro corredor e NÃO invente protocolo. "
                            "Chame `request_human_agent` agora, com o motivo "
                            f"'{quem} não tem corredor para {trabalho}', e diga ao cliente que um "
                            "atendente da corretora vai assumir — o que ele já contou fica registrado.")}
            if plan.get("missing_slots"):
                friendly = {
                    "titular_cpf": "CPF do titular",
                    "endereco_numero": "número da residência",
                    "telefone_contato": "telefone de contato",
                    "problema_descricao": "descrição do problema",
                    "periodo_preferido": "período preferido (manhã ou tarde)",
                    "risco_confirmado_sem_fumaca": "confirmação de que NÃO há fumaça/faísca/cheiro de queimado",
                    "aparelho_marca_modelo": "marca e modelo do aparelho",
                    "aparelho_idade": "idade aproximada do aparelho",
                    "veiculo_placa": "placa do veículo (a InfoCap costuma ter — confirme)",
                    "titular_nascimento": "data de nascimento do titular (a Mapfre exige para validar)",
                    "local_atual": "onde o veículo está agora (endereço com referência)",
                    "local_destino": "para onde levar o veículo (destino do guincho)",
                    "quando": "quando precisa (agora ou uma data para agendar)",
                    "pessoa_no_local": "quem vai estar com o veículo no local",
                }
                faltam = [friendly.get(s, s) for s in plan["missing_slots"]]
                return {
                    "status": "missing_data",
                    "missing": plan["missing_slots"],
                    "content": (
                        "Ainda faltam estes dados para acionar: " + "; ".join(faltam) + ". "
                        "ANTES de perguntar ao cliente, PROCURE cada um na CONVERSA e na sua ficha "
                        "(CPF, endereço e telefone quase sempre JÁ foram ditos) e chame de novo com eles. "
                        "Pergunte ao cliente SOMENTE o que nunca foi informado — um de cada vez, com naturalidade."
                    ),
                }
            return {"status": "error", "content": f"Não foi possível preparar o acionamento ({plan.get('error')}). Acione um atendente humano."}

        lines = [
            "[ACIONAMENTO PREPARADO EM SIMULAÇÃO (NADA foi enviado à seguradora)]",
            f"Subserviço: {plan['subservice']} · Playbook: {plan['playbook_ref']}",
            "Sequência que será enviada à seguradora:",
        ]
        for step in plan["steps"]:
            lines.append(f"  {step['step']}: {step['reply']}")
        lines.append(plan["note"])
        lines.append(
            "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o pedido está registrado e será acionado em instantes; "
            "NÃO afirme que a seguradora já foi acionada nem invente protocolo/prazo."
        )
        return {"status": "ready_to_send", "content": "\n".join(lines), "plan": plan}

    async def _resolve_vehicle_facts(self, kwargs: dict) -> dict:
        """FATOS da apólice vêm da FONTE, não do cliente (incidente 2026-07-11:
        o atendente pedia a placa ao segurado). Para AUTO, resolve placa/veículo/
        titular server-side via porta provider.vehicle (a mesma do portal de
        vidros). Best-effort: falha nunca derruba o acionamento."""
        is_auto = (
            str(kwargs.get("line_kind") or "").lower() == "auto"
            or str(kwargs.get("subservice") or "").lower() in ("guincho", "bateria", "pneu")
        )
        cpf = "".join(ch for ch in str(kwargs.get("titular_cpf") or "") if ch.isdigit())
        precisa = not str(kwargs.get("veiculo_placa") or "").strip() or not str(kwargs.get("titular_nome") or "").strip()
        if not (is_auto and cpf and precisa):
            return kwargs
        try:
            import os as _os

            from app.core.database import create_async_supabase_client
            from app.providers.policy_data_provider import get_policy_data_provider

            key = _os.getenv("BACKEND_INTERNAL_API_KEY") or _os.getenv("ADMIN_API_KEY")
            provider = get_policy_data_provider("infocap")
            if provider is None or not hasattr(provider, "vehicle") or not key:
                return kwargs
            db = await create_async_supabase_client()
            info = await provider.vehicle(
                company_id=self.company_id, document=cpf, policy_number=None,
                db=db, internal_key=key,
            )
            if info.get("ok"):
                veh = info.get("vehicle") or {}
                cli = info.get("client") or {}
                if veh.get("placa") and not str(kwargs.get("veiculo_placa") or "").strip():
                    kwargs["veiculo_placa"] = str(veh["placa"]).strip().upper()
                if veh.get("veiculo") and not str(kwargs.get("veiculo_descricao") or "").strip():
                    kwargs["veiculo_descricao"] = str(veh["veiculo"]).strip()
                nome = cli.get("nome") or cli.get("name")
                if nome and not str(kwargs.get("titular_nome") or "").strip():
                    kwargs["titular_nome"] = str(nome).strip()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[InsurerDispatch] vehicle facts indisponíveis: {type(e).__name__}")
        return kwargs

    async def _acionamento_liberado(self) -> bool:
        """P-90 — esta corretora pode acionar a seguradora DE VERDADE agora?

        A regra mora em `acionamento_liberado` e vale igual para o portal de
        vidros: agente de atendimento LIGADO **e** freio de emergência solto.

        Esta checagem é cinto E suspensório, de propósito. `InsurerDispatchTool`
        já só existe para um agente `attendance` ATIVO — 📊 `graph.py` só a anexa
        quando `_agent_role == "attendance"`, `_get_raw_agent` filtra
        `is_active=True`, e o webhook já parou antes em `attendance_agent_active`.
        Mas essas três travas moram longe daqui e nenhuma delas pode ser provada
        por um teste desta ferramenta. Um guarda que ninguém consegue exercitar é
        um guarda que ninguém percebe quando some.

        Fail-closed: erro de leitura vira dry-run, nunca envio.
        """
        try:
            from app.services.atlas.attendance_capture import attendance_agent_active
            from app.services.insurer_dispatch_service import acionamento_liberado

            return acionamento_liberado(await attendance_agent_active(self.company_id))
        except Exception as exc:  # noqa: BLE001
            logger.error("[InsurerDispatch] não foi possível confirmar o interruptor do "
                         "agente (%s) — mantendo simulação", type(exc).__name__)
            return False

    async def _arun(self, **kwargs) -> dict:
        """Caminho LIVE: com o agente de atendimento LIGADO, cria a sessão real,
        envia a abertura à seguradora pela integração da corretora e ativa o
        roteador. Qualquer pré-condição faltando → resposta honesta SEM envio.

        P-90 (04/08/2026) — o que segura aqui deixou de ser o env `INSURER_
        DISPATCH_LIVE` e passou a ser o interruptor que o Founder clica. As duas
        perguntas são feitas nesta ordem porque a barata vem primeiro: o ambiente
        (`dispatch_live_enabled`, hoje aberto por padrão, fechado pelo freio de
        emergência) e só então o banco (`attendance_agent_active`).
        """
        import os

        from app.services.insurer_dispatch_service import dispatch_live_enabled

        kwargs = await self._resolve_vehicle_facts(dict(kwargs))
        base = self._run(**kwargs)
        if base.get("status") != "ready_to_send" or not dispatch_live_enabled():
            return base
        if not await self._acionamento_liberado():
            # Nada sai. O conteúdo devolvido é o MESMO plano em simulação que a
            # tool sempre devolveu com o gate fechado — o agente desligado não
            # muda o texto, muda o mundo: nenhuma mensagem chega à seguradora.
            logger.info("[InsurerDispatch] agente de atendimento desligado (ou freio "
                        "armado) — plano preparado, NADA enviado")
            return base

        from app.services.corridor_playbooks import insurer_contact_env_var, resolve_insurer_contact

        playbook_ref, insurer_key = self._resolve_playbook_ref(kwargs)
        line = "auto" if str(kwargs.get("line_kind") or "").lower() == "auto" or str(kwargs.get("subservice") or "").lower() in ("guincho", "bateria", "pneu") else "residencial"
        digits = lambda s: "".join(ch for ch in str(s or "") if ch.isdigit())  # noqa: E731
        insurer_phone = resolve_insurer_contact(insurer_key or "allianz", line_kind=line)
        if not insurer_phone:
            base["content"] += (
                f"\nAVISO INTERNO: gate LIVE aberto mas o contato da seguradora não está configurado "
                f"({insurer_contact_env_var(insurer_key or 'allianz', line)}) — NADA foi enviado. Não afirme acionamento."
            )
            return base

        # Telefone do cliente vem da sessão WhatsApp (whatsapp:{phone}:{company}:{agent}).
        session_ref = str(kwargs.get("session_id") or "")
        parts = session_ref.split(":")
        client_phone = digits(parts[1]) if len(parts) >= 3 and parts[0] == "whatsapp" else ""
        if not client_phone:
            base["content"] += (
                "\nAVISO INTERNO: acionamento REAL só é iniciado na conversa de WhatsApp do cliente "
                "(telefone da sessão indisponível) — NADA foi enviado. Não afirme acionamento."
            )
            return base

        try:
            from app.services.integration_service import get_integration_service
            from app.services.whatsapp_service import get_whatsapp_service

            svc = get_integration_service()
            integration = svc.get_whatsapp_integration(self.company_id, self._attendance_agent_id())
            if not integration:  # fallback: integracao ativa sem agente
                integration = svc.get_whatsapp_integration(self.company_id)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InsurerDispatch] integração indisponível: {type(e).__name__}")
            integration = None
        if not integration:
            base["content"] += (
                "\nAVISO INTERNO: canal WhatsApp da corretora indisponível — NADA foi enviado. "
                "Não afirme acionamento."
            )
            return base

        wa = get_whatsapp_service()

        def _sender(text: str) -> None:
            wa.send_message(insurer_phone, text, integration)

        from app.services.dispatch_router import start_live_dispatch

        subservice, slots = self._extract_slots(kwargs)
        result = await start_live_dispatch(
            company_id=self.company_id,
            case_id=self.case_id or f"wa-{client_phone}",
            playbook_ref=playbook_ref,
            subservice=subservice,
            slots=slots,
            client_phone=client_phone,
            insurer_phone=insurer_phone,
            sender=_sender,
        )
        if not result.get("ok"):
            if result.get("error") == "dispatch_already_active":
                # FILA multi-cliente: número da seguradora ocupado com OUTRO
                # acionamento → entra na fila e inicia SOZINHO quando liberar.
                try:
                    from app.services.dispatch_router import enqueue_dispatch

                    position = await enqueue_dispatch(self.company_id, insurer_phone, {
                        "case_id": self.case_id or f"wa-{client_phone}",
                        "playbook_ref": playbook_ref, "subservice": subservice,
                        "slots": slots, "client_phone": client_phone,
                    })
                    return {
                        "status": "queued",
                        "content": (
                            f"[NA FILA DA SEGURADORA — posição {position}] Há outro acionamento em andamento "
                            "com esta seguradora agora. Este pedido entrou na FILA e inicia AUTOMATICAMENTE "
                            "quando o canal liberar (o cliente será avisado na hora). "
                            "INSTRUÇÃO AO ATENDENTE: diga que o pedido está registrado e que o acionamento "
                            "começa em alguns minutos — NÃO diga que já foi acionado."
                        ),
                    }
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[InsurerDispatch] enqueue falhou: {type(e).__name__}")
                return {
                    "status": "already_active",
                    "content": (
                        "Já existe um acionamento EM ANDAMENTO com a seguradora para esta corretora. "
                        "NÃO abra outro. Informe ao cliente que o acionamento está em andamento e que "
                        "você avisa assim que a seguradora confirmar."
                    ),
                }
            base["content"] += "\nAVISO INTERNO: não foi possível iniciar o acionamento real — NADA foi enviado."
            return base

        from app.services.insurer_dispatch_service import finalize_live_for

        insurer_label = (insurer_key or "a seguradora").upper()
        if finalize_live_for(playbook_ref):
            content = (
                "[ACIONAMENTO REAL INICIADO]\n"
                f"A conversa com a assistência da {insurer_label} foi aberta pelo WhatsApp da corretora. "
                "A URA será respondida automaticamente com os dados coletados e o cliente será avisado "
                "assim que o protocolo/agendamento sair.\n"
                "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o acionamento FOI iniciado e que você retorna "
                "com o protocolo em instantes. NÃO invente protocolo/senha/prazo — eles chegam sozinhos."
            )
        else:
            content = (
                "[ACIONAMENTO EM MODO TESTE INICIADO]\n"
                f"A conversa com a assistência da {insurer_label} foi aberta pelo WhatsApp da corretora. "
                "O fluxo será executado até a confirmação final e CANCELADO antes de abrir o serviço "
                "(nenhum prestador será acionado).\n"
                "INSTRUÇÃO AO ATENDENTE: diga que o pedido está sendo processado. NÃO afirme que o serviço "
                "foi aberto nem invente protocolo — este acionamento é um teste e será cancelado no final."
            )
        return {"status": "dispatched", "content": content}
