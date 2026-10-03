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
from typing import Any, Optional, Type

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


# --------------------------------------------------------------------------- #
# O PAR DE COORDENADAS — SPEC-118 F3
# --------------------------------------------------------------------------- #
# 🔴 A coordenada NÃO se pergunta: ninguém sabe a própria latitude. Ela chega de
# UM TOQUE, pelo pin de localização do WhatsApp — e o produto já sabe lê-lo:
# 📊 `whatsapp/evolution_inbound.py` converte `locationMessage`/
# `liveLocationMessage` em texto para o agente desde 03/08/2026, com 6 casas
# decimais (≈ 11 cm) e tratando `(0, 0)` como AUSENTE de propósito.
#
# ⛔ `(0, 0)` é o default do protobuf, não um lugar: é o Golfo da Guiné. Uma
# coordenada zerada manda o guincho para o meio do oceano e a URA aceita calada.
#
# ⚠️ **Meio par não é par.** Latitude sem longitude não localiza nada, e o campo
# solto viajaria para a seguradora como se localizasse.
def par_de_coordenadas(latitude, longitude):
    """`(lat, lon)` normalizado, ou `None` — **delegado à fonte única**.

    🔴 SPEC-118 F4 · A conta mora em `corridor_playbooks.par_de_coordenadas`, e
    não aqui, porque a costura provou que ela tem TRÊS leitores: esta ferramenta
    (o agente passando o par), `inject_address_slots` (o par lido do pin) e o
    montador da resposta do formulário. Uma segunda cópia daria dois vereditos
    sobre a mesma coordenada, e a divergência só apareceria num guincho no lugar
    errado (CLAUDE.md §5: consolidar antes de duplicar).

    ⚠️ O nome fica: `_extract_slots` e `_run` o chamam, e trocá-los por um
    import inline em dois lugares só espalharia o acoplamento.
    """
    from app.services.corridor_playbooks import par_de_coordenadas as _fonte

    return _fonte(latitude, longitude)


def valor_de_slot_honesto(slot, valor):
    """O valor do slot de endereço normalizado, ou `None` — **mesma delegação**.

    🔴 26/09/2026 · A `GUARDA ANTI-INVENÇÃO` logo abaixo conferia TRÊS campos
    (telefone, placa, CPF), escrita depois do incidente de 10/07/2026. 📊 A F3/F4
    acrescentou SEIS campos que vão para a seguradora dentro do formulário da
    Porto — `local_rua`, `local_numero`, `local_bairro`, `local_cidade`,
    `local_uf`, `local_cep` — e nenhum entrou na lista, no mesmo commit em que o
    comentário acima dela explica por que ela existe. Medido: `estado="ZZ"`,
    `cep="0"`, `numero="nao sei"`, `cidade="48.5477"` e uma rua com quebra de
    linha dentro saíam todos com `ok=True`.

    ⚠️ A régua mora em `corridor_playbooks.valor_de_slot_honesto`, pelo mesmo
    motivo escrito em `par_de_coordenadas` logo acima: ela tem TRÊS leitores (o
    portão de coleta, o montador da resposta e esta ferramenta) e duas cópias
    divergiriam num dia.
    """
    from app.services.corridor_playbooks import valor_de_slot_honesto as _fonte

    return _fonte(slot, valor)


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


def _catalogo_de_subservicos() -> str:
    """📊 SPEC-084.2 C3 — O CONTRATO PASSA A SER GERADO.

    O texto anterior era escrito à mão e anunciava **9 dos 17** subserviços do
    produto. Ficavam invisíveis ao modelo: `socorro_mecanico`, `tecnico`,
    `bateria_nova`, `taxi`, `vidros`, `ar_condicionado`, `consulta_veterinaria`
    e `limpeza_caixa_dagua`.

    🔴 Trabalho que o contrato não nomeia é trabalho que o atendente não sabe
    pedir — e `socorro_mecanico` é rota AAA em duas seguradoras.
    """
    from app.services.corridor_playbooks import subservicos_por_linha
    por_linha = subservicos_por_linha()
    return " ".join(
        f"{ln.upper()}: {' | '.join(por_linha.get(ln, []))}."
        for ln in ("auto", "residencial") if por_linha.get(ln))


class InsurerDispatchInput(BaseModel):
    subservice: str = Field(description=(
        "Subserviço, pelo NOME CANÔNICO. " + _catalogo_de_subservicos() + " "
        # 🔴 SPEC-084.2 C3 — a diferença que decide reboque × mecânico.
        "GUINCHO × SOCORRO MECÂNICO: se o carro precisa ser LEVADO a algum "
        "lugar, é `guincho` (e só ele pede `local_destino`). Se o segurado diz "
        "que o carro não pega, morreu, apagou, está falhando ou 'deu pane' e o "
        "reparo pode ser NO LOCAL, é `socorro_mecanico` — o mecânico vai até o "
        "veículo. Na dúvida, `socorro_mecanico`: a própria URA converte em "
        "reboque quando o reparo no local não resolve. "
        # 🔴 O único trabalho que existe nas duas linhas.
        "CHAVEIRO existe em AUTO e em RESIDENCIAL e NÃO se deduz: informe "
        "sempre `line_kind`, senão o acionamento vira handoff. "
        "Nem toda seguradora faz todos: sem corredor observado a ferramenta "
        "devolve handoff com o motivo escrito — nunca improvise. "

        # 🔴 SPEC-082: `maquina_de_lavar` e um subservico PROPRIO, e nao um
        # `eletrodomesticos` generico. Motivo medido: a URA pede a tecla do
        # aparelho numa lista de quinze, e o generico responde "15 - Outros".
        # Com o subservico especifico a tecla e `14`, e o chamado nasce com
        # o aparelho certo escrito nele.
        "Use `maquina_de_lavar` quando o segurado falar em maquina de lavar, "
        "lavadora, lava-roupas ou lava-e-seca. Para OUTRO eletrodomestico "
        # 🔴 JUIZ 4 · AQUI DIZIA "(… ar-condicionado) use `eletrodomesticos`",
        #    e o catálogo GERADO cinco linhas acima lista `ar_condicionado`
        #    como rota própria. **Não é contradição cosmética:**
        #
        # 📊 `ar_condicionado` responde `eletrodomestico_categoria_opcao="2"` e
        #    tem três telas próprias; `eletrodomesticos` responde `"1"` (Linha
        #    Branca) + `eletrodomestico_opcao="15"` (Outros). A nota do
        #    playbook é literal: *"1-Linha Branca 2-Ar Condicionado
        #    3-Geladeira/Freezer"*.
        #
        # ⚠️ Um modelo obediente apertava **1 e 15** numa URA cuja tela tem
        #    **2 = Ar Condicionado**. É o defeito que a SPEC-082 consertou para
        #    a máquina de lavar, reintroduzido por uma frase vencida.
        "(geladeira, fogao, micro-ondas) use `eletrodomesticos`. "
        "Para AR-CONDICIONADO use `ar_condicionado`, que é rota própria com "
        "tecla própria na URA."))
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
    # ══════════════════════════════════════════════════════════════════════
    # 🔴 O PIN DE LOCALIZAÇÃO — SPEC-118 F3
    # ══════════════════════════════════════════════════════════════════════
    #
    # 📊 O produto JÁ recebe o pin: `whatsapp/evolution_inbound.py` converte
    #    `locationMessage`/`liveLocationMessage` no texto que chega ao agente,
    #    em linhas separadas::
    #
    #        R. Rafael Bandeira, Centro
    #        Localização compartilhada: -27.588016,-48.544253
    #
    # 🔴 Faltava o acionamento ter ONDE recebê-la. Estes dois campos são esse
    #    lugar — e a instrução é pedir O PIN, não a coordenada: é uma pergunta
    #    em vez de seis (rua, número, bairro, cidade, estado, CEP), e é a que o
    #    segurado responde num acostamento, com o celular na mão.
    #
    # ⛔ Ausente continua sendo handoff com o motivo escrito. Nunca zero.
    local_latitude: Optional[str] = Field(default=None, description=(
        "[auto] Latitude do LOCAL onde o veículo está, em grau decimal "
        "(ex.: -27.588016). SÓ preencha com o número que veio do PIN DE "
        "LOCALIZAÇÃO que o cliente compartilhou no WhatsApp — a linha "
        "'Localização compartilhada: <lat>,<lon>' da conversa. ⛔ NUNCA invente, "
        "NUNCA converta um endereço em coordenada de cabeça e NUNCA mande zero. "
        "Se a seguradora precisa do local exato e não há pin, PEÇA O PIN ao "
        "cliente: 'toque no clipe 📎 e envie sua localização' — uma pergunta em "
        "vez de seis. Latitude sem longitude não serve: mande as duas ou nenhuma."))
    local_longitude: Optional[str] = Field(default=None, description=(
        "[auto] Longitude do LOCAL, em grau decimal (ex.: -48.544253), vinda do "
        "mesmo pin de localização da latitude. As duas juntas ou nenhuma."))
    # --- Comuns ---
    telefone_contato: Optional[str] = Field(default=None, description=(
        "Telefone de contato com DDD (somente dígitos). VAZIO = o telefone DESTA conversa de "
        "WhatsApp, que o sistema já tem e preenche sozinho — NÃO pergunte o telefone ao cliente; "
        "preencha só se ele der OUTRO número (quem vai receber o prestador é outra pessoa)."))
    problema_descricao: Optional[str] = Field(default=None, description="Descrição curta do problema relatado pelo cliente")
    dados_confirmados: Optional[bool] = Field(default=None, description=(
        "[auto e residencial] true SOMENTE depois de você MOSTRAR ao cliente na conversa os dados do "
        "acionamento (placa/veículo, local, destino, telefone — o que o serviço usa) e ele responder SIM. "
        "A ferramenta confere na conversa a sua pergunta e o sim dele: sem os dois, o acionamento não sai."))
    # 🔴 SPEC-126 U5 (D7 da 125, P-125-06): só o diário lê (`nodes.deducoes_do_turno`); o `_run`
    #    o descarta antes de qualquer uso — não vira slot do serviço nem da URA.
    slots_deduzidos: Optional[list[str]] = Field(default=None, description=(
        "Os NOMES dos campos acima que você DEDUZIU — o segurado não disse com essas palavras "
        "(ex.: ele escreveu 'BR-101' e você pôs via_ou_rodovia_opcao='rodovia'). Campo que ele disse "
        "ou confirmou NÃO entra. Não muda o acionamento: vai ao diário da corretora."))

    # ══════════════════════════════════════════════════════════════════════
    # 🔴 C1 · O QUE O PORTÃO EXIGE E O CONTRATO NÃO DECLARAVA
    # ══════════════════════════════════════════════════════════════════════
    #
    # 📊 SPEC-084.2, medido contra o motor real: as **19 rotas AAA** da
    #    SPEC-084.1 — as que respondem 100% das telas da URA, com 100% de
    #    determinismo — davam `missing_data` pelo caminho REAL da ferramenta.
    #    **Nenhuma acionava.**
    #
    #    ```
    #    com TUDO que a ferramenta consegue carregar   →  missing_data    🔴
    #    com os slots que ela NÃO carrega, em memória  →  ready_to_send   ✅
    #    ```
    #
    # ⚠️ O corredor estava CERTO. O bloqueio estava ANTES dele: a SPEC-084.1
    #    acrescentou slots a `required_slots` e não estendeu este schema. Um
    #    slot que o portão exige e o contrato não anuncia **não tem como
    #    chegar** — o atendente não tem onde escrever a resposta.
    #
    # 🔴 E a prova de que a pergunta é legítima já estava escrita:
    #    📊 **19 dos 22 slots já tinham redação em `_COMO_PERGUNTAR`.** O
    #    produto sabia perguntar e não sabia guardar.
    #
    # ⚠️ NÃO confie na saída de emergência: `nodes.py` chama `tool._arun(**args)`
    #    cru, sem Pydantic, então um campo não declarado *funcionaria* se o
    #    modelo adivinhasse o nome. Apostar um guincho real em adivinhação não
    #    é engenharia.
    #
    # 🔴 O guarda que impede a recorrência é
    #    `test_o_contrato_alcanca_o_portao` — ele compara as duas listas. Sem
    #    ele, a próxima SPEC que acrescentar um slot repete isto em silêncio.

    # --- Auto: comuns a TODO subserviço ---
    local_seguro: Optional[str] = Field(default=None, description=(
        "[auto] O veículo/pessoa está num lugar SEGURO para esperar? "
        "🔴 PERGUNTE, não presuma: esta resposta decide a PRIORIDADE do "
        "atendimento. Dizer 'sim' no escuro rebaixa quem está parado em "
        "acostamento, curva ou lugar perigoso. Ex.: 'sim, estou num posto' | "
        "'não, estou na faixa da esquerda'"))

    # --- Auto: pneu ---
    estepe_situacao: Optional[str] = Field(default=None, description=(
        "[auto pneu] O estepe está cheio e em condições de uso? Sem estepe "
        "utilizável a seguradora manda REBOQUE, não borracheiro — a resposta "
        "muda o serviço que sai."))
    ferramentas_no_veiculo: Optional[str] = Field(default=None, description=(
        "[auto pneu] Macaco e chave de roda estão no veículo?"))
    equipamentos_troca_opcao: Optional[str] = Field(default=None, description=(
        "[auto pneu] Tem macaco, chave de roda e estepe? (a URA pergunta os "
        "três juntos numa tela só)"))

    # ══════════════════════════════════════════════════════════════════════
    # 🔴 SPEC-118 F4 · O ENDEREÇO EM PARTES — PORQUE O FORMULÁRIO PEDE ASSIM
    # ══════════════════════════════════════════════════════════════════════
    #
    # 📊 ACHADO POR `test_o_contrato_alcanca_o_portao` NA MESMA FATIA, e é a
    #    classe de defeito que aquele guarda existe para pegar (SPEC-084.2 C1):
    #    **um slot que o portão exige e o contrato não anuncia não tem como ser
    #    preenchido.** Quando a coordenada da Porto ganhou fonte, o portão passou
    #    a cobrar os campos do formulário de endereço, e seis deles não tinham
    #    campo aqui:
    #
    #        local_rua · local_numero · local_bairro · local_cidade ·
    #        local_uf  · local_cep
    #
    #    O agente ouviria "ainda faltam: o bairro onde o carro está", perguntaria
    #    ao segurado, receberia a resposta e **não teria onde a guardar** — laço
    #    fechado, com o segurado respondendo a mesma pergunta para sempre.
    #
    # ⚠️ E ELES QUASE NUNCA SÃO PREENCHIDOS À MÃO, de propósito:
    #    `corridor_playbooks.inject_address_slots` decompõe `local_atual` sozinho
    #    (📊 um endereço completo rende cinco deles; o pin do WhatsApp rende os
    #    mesmos cinco mais a coordenada). Estes campos existem para o BURACO:
    #    quando o texto não tinha o número, ou o pin não trouxe o bairro, e a
    #    seguradora pede o campo separado.
    local_rua: Optional[str] = Field(default=None, description=(
        "[auto] Só quando a seguradora pede o endereço em PARTES e o texto de "
        "`local_atual` não deixou claro: o nome da RUA onde o veículo está, sem "
        "número. ⛔ Não deduza nem complete — se o cliente não disse, pergunte."))
    local_numero: Optional[str] = Field(default=None, description=(
        "[auto] O número mais próximo na rua onde o veículo está — do prédio, da "
        "casa, ou o km na rodovia. ⛔ Nunca invente um número: o guincho vai ao "
        "endereço que sair daqui."))
    local_bairro: Optional[str] = Field(default=None, description=(
        "[auto] O bairro onde o veículo está."))
    local_cidade: Optional[str] = Field(default=None, description=(
        "[auto] A cidade onde o veículo está."))
    local_uf: Optional[str] = Field(default=None, description=(
        "[auto] O estado (sigla de 2 letras) onde o veículo está."))
    local_cep: Optional[str] = Field(default=None, description=(
        "[auto] O CEP do lugar onde o veículo está. Se o cliente não souber, "
        "PEÇA O PIN de localização em vez de insistir no CEP: o pin resolve o "
        "endereço e a coordenada de uma vez."))
    local_complemento: Optional[str] = Field(default=None, description=(
        "[auto] Complemento do endereço, se houver (apartamento, bloco, quadra). "
        "Opcional na seguradora: quando não há, não preencha."))

    # --- Residencial: qual seguro ---
    # 🔴 Decisão do Founder, 17/09/2026: a tela "Qual seguro deseja utilizar?"
    # (residencial · condomínio · empresarial) é respondida pelo RAMO DA APÓLICE.
    # Quando a apólice foi localizada no sistema, o ramo chega sozinho
    # (`nodes.py`); o modelo só o informa quando a apólice NÃO foi localizada.
    ramo_da_apolice: Optional[str] = Field(default=None, description=(
        "[residencial] RAMO DA APÓLICE do caso: residencial | condominio | empresarial. "
        "Se a apólice foi localizada no sistema, NÃO preencha (o sistema já sabe). "
        "Se não foi, pergunte JUNTO com o pedido da apólice/CPF, na primeira conversa "
        "(ex.: 'o seguro é da sua casa/apartamento, do condomínio ou da empresa?'). "
        "Nunca faça uma pergunta separada sobre 'qual seguro deseja utilizar'."))
    qual_seguro_opcao: Optional[str] = Field(default=None, description=(
        "[residencial] NÃO pergunte e NÃO preencha: o motor responde esta tela "
        "pelo `ramo_da_apolice`."))
    tipo_imovel: Optional[str] = Field(default=None, description=(
        "[residencial] Casa, apartamento ou condomínio"))

    # --- Residencial: encanador / vazamento ---
    vazamento_local: Optional[str] = Field(default=None, description=(
        "[residencial encanador] Onde é o vazamento (ex.: 'embaixo da pia da "
        "cozinha', 'no cano do banheiro')"))
    agua_escorrendo: Optional[str] = Field(default=None, description=(
        "[residencial encanador] A água ainda está escorrendo agora?"))
    risco_confirmado_registro_fechado: Optional[str] = Field(default=None, description=(
        "[residencial encanador] O registro de água já foi fechado? "
        "🔴 Pergunte de verdade: com o registro aberto o dano cresce enquanto "
        "o prestador não chega."))
    encanador_tipo_opcao: Optional[str] = Field(default=None, description=(
        "[residencial encanador] O que está vazando, com as palavras do "
        "cliente (torneira, vaso, cano, caixa d'água...)"))
    encanador_instalacao_opcao: Optional[str] = Field(default=None, description=(
        # 🔴 SPEC-084.2, achado do JUIZ 1 (BLOCKER) · AQUI DIZIA "instalação
        #    nova NÃO é coberta", e isso é INVENÇÃO.
        #
        # 📊 O slot só existe em `porto/residencial/encanador`, e a tela que o
        #    origina é alcançada pela tecla *"5 - Instalações"* de um menu que a
        #    própria URA abre com *"listamos abaixo os SERVIÇOS DISPONÍVEIS
        #    para você"*. As três frases de "instalação não coberta" do corpus
        #    são de FIOS (eletricista), FECHADURAS (chaveiro) e LUMINÁRIA — e
        #    a da luminária diz *"realizada de forma particular"*, que é outra
        #    coisa. **Ambíguo não é negativo, e aqui foi escrito como
        #    negativo.**
        "[residencial encanador] É REPARO de algo que quebrou, ou INSTALAÇÃO "
        "nova? A cobertura de instalação VARIA por apólice — pergunte, e não "
        "prometa nem negue antes de a seguradora responder."))

    # --- Residencial: chaveiro ---
    chaveiro_necessidade_opcao: Optional[str] = Field(default=None, description=(
        "[residencial chaveiro] É abrir a porta, fazer a cópia, ou as duas "
        "coisas?"))
    chave_tipo_opcao: Optional[str] = Field(default=None, description=(
        "[residencial chaveiro] Tipo da chave: simples, tetra, as duas, ou "
        "eletrônica"))

    # --- Residencial: eletrodomésticos ---
    idade_aparelho_opcao: Optional[str] = Field(default=None, description=(
        "[residencial eletrodoméstico] Idade do aparelho. 🔴 A resposta decide "
        "COBERTURA: acima de 10 anos a seguradora recusa. Pergunte ANTES de "
        "dizer ao cliente que o conserto sai."))

    # --- Residencial: ar-condicionado ---
    ar_condicionado_tipo: Optional[str] = Field(default=None, description=(
        "[residencial ar-condicionado] De janela ou split"))
    ar_condicionado_btus: Optional[str] = Field(default=None, description=(
        "[residencial ar-condicionado] Potência em BTUs (9000, 12000...)"))

    # --- Residencial: limpeza de caixa d'água ---
    caixa_litros_opcao: Optional[str] = Field(default=None, description=(
        "[residencial limpeza de caixa d'água] Quantos litros tem a caixa"))
    caixas_dagua_quantidade_opcao: Optional[str] = Field(default=None, description=(
        "[residencial limpeza de caixa d'água] Quantas caixas há no imóvel"))

    # --- Residencial: consulta veterinária ---
    email_segurado: Optional[str] = Field(default=None, description=(
        "[residencial pet] E-mail do segurado — a clínica manda o "
        "encaminhamento por ele; sem e-mail o cliente não recebe a guia."))


    # ── E os que o guarda achou FORA das 19 rotas AAA ──────────────────────
    #
    # 🔴 O `test_o_contrato_alcanca_o_portao` foi escrito para impedir a
    #    recorrência — e acusou na estreia o que esta mesma edição tinha
    #    deixado passar. 📊 Consertar as 19 do gate deixava **16 slots órfãos**
    #    em rotas fora delas. Fechar só o que o gate mede é comprar o gate.
    #
    # ⚠️ `servico_texto` NÃO entra, e a distinção é medida: ele aparece como
    #    cobrado quando se pergunta ao portão com o caso vazio, e some quando
    #    se pergunta pelo caminho real — `new_dispatch_session` o injeta.
    #    Declará-lo faria a atendente perguntar ao segurado uma coisa que o
    #    motor já sabe.
    data_agendamento: Optional[str] = Field(default=None, description=(
        "[auto técnico/bateria nova] Dia e hora combinados para a visita "
        "agendada (ex.: '28/08 à tarde')"))
    pane_opcao: Optional[str] = Field(default=None, description=(
        "[auto] O que aconteceu com o carro: não liga | perdeu força | "
        "superaqueceu | pane elétrica | outro"))
    cambio_opcao: Optional[str] = Field(default=None, description=(
        "[auto] Câmbio manual ou automático — muda o equipamento do guincho"))
    alavanca_travada_opcao: Optional[str] = Field(default=None, description=(
        "[auto câmbio automático] A alavanca está travada? Um carro automático "
        "com alavanca travada não pode ser rebocado da mesma forma."))
    pneus_danificados_opcao: Optional[str] = Field(default=None, description=(
        "[auto pneu] Quantos pneus estão danificados. 🔴 Mais de um pneu "
        "geralmente vira REBOQUE — um estepe não resolve dois furos."))
    taxi_passageiros: Optional[str] = Field(default=None, description=(
        "[auto táxi] Quantas pessoas vão no táxi"))
    # SPEC-120 · D9 — o portão da porto cobra; sem campo aqui o guincho nunca aciona.
    taxi_apos_guincho: Optional[str] = Field(default=None, description=(
        "[porto guincho] Sim/Não: vai precisar de táxi depois do guincho?"))
    chaveiro_alvo_opcao: Optional[str] = Field(default=None, description=(
        "[residencial chaveiro] O que está trancado — porta principal, "
        "portão, quarto, cofre"))
    fechadura_tipo_opcao: Optional[str] = Field(default=None, description=(
        "[residencial chaveiro] Tipo da fechadura — simples, tetra, digital"))
    chaveiro_porta_opcao: Optional[str] = Field(default=None, description=(
        "[residencial chaveiro] Qual porta é o problema — a da rua, a de um "
        "cômodo, o portão. 🔴 Não presuma: a seguradora cobre a porta de "
        "acesso ao imóvel, e cômodo interno pode não estar coberto."))
    eletrodomestico_opcao: Optional[str] = Field(default=None, description=(
        "[residencial eletrodoméstico] Qual é o aparelho — geladeira, freezer, "
        "fogão, micro-ondas, máquina de lavar, secadora, lava-louças. A tecla "
        "que a URA recebe depende disto."))
    geladeira_medicacao_opcao: Optional[str] = Field(default=None, description=(
        "[residencial geladeira] Há MEDICAMENTO guardado na geladeira? "
        "🔴 PERGUNTE: a resposta muda a urgência do atendimento, e ninguém "
        "responde isso por outra pessoa."))
    pet_nome: Optional[str] = Field(default=None, description=(
        "[residencial pet] Nome do animal"))
    pet_raca: Optional[str] = Field(default=None, description=(
        "[residencial pet] Raça do animal"))
    pet_idade: Optional[str] = Field(default=None, description=(
        "[residencial pet] Idade do animal"))


    # --- Auto guincho: o que o FORMULÁRIO NATIVO da família HDI/Yelum exige ---
    #
    # 🔴 Mesmo defeito do C1, uma camada adiante: 📊 `montar_resposta_de_flow`
    #    exige três campos que `required_slots` não pedia E que este contrato
    #    não declarava. Slot não declarado é slot inalcançável — 📊 medido,
    #    `model_validate` DESCARTA o extra, e o modelo só vê o que o schema
    #    anuncia.
    veiculo_em_garagem: Optional[str] = Field(default=None, description=(
        "[auto guincho HDI/Yelum/Bradesco/Zurich] O carro está numa garagem/estacionamento, "
        "ou parado na rua? 🔴 PERGUNTE: responder 'não' sem saber faz a "
        "seguradora PULAR a pergunta que escolhe o tipo de guincho."))
    veiculo_nivel_rua: Optional[str] = Field(default=None, description=(
        # 🔴 Achado do JUIZ 4: esta descrição ensinava quatro redações e 📊 DUAS
        #    eram RECUSADAS pelo formulário — o hífen do título real
        #    (`Nível da rua - com restrição de acesso`) matava o casamento por
        #    substring. Um modelo obediente escrevia o que lhe foi ensinado e
        #    travava o acionamento. Agora são os títulos EXATOS da seguradora.
        "[auto guincho HDI/Yelum/Bradesco/Zurich] Só quando está em garagem. Use uma destas "
        "quatro, exatamente: 'Subsolo' | 'Acima do nível da rua' | 'Nível da "
        "rua - com restrição de acesso' | 'Nível da rua - com acesso livre'. "
        "🔴 Esta resposta escolhe o EQUIPAMENTO (plataforma, asa-delta, "
        "munck). Não deduza de 'rampa' — ela cabe em duas opções."))
    # 🔴 SPEC-121 F2 — o que a consultora da Porto pedia, perguntado ANTES
    #    (📊 porto 4830574a). Sem campo aqui o slot é inalcançável
    #    (`test_o_contrato_alcanca_o_portao`).
    # 🔴 SPEC-121 F4 — Allianz eletrodomésticos: o APARELHO vira a tecla da lista.
    eletrodomestico_aparelho: Optional[str] = Field(default=None, description=(
        "[residencial eletrodomésticos Allianz] Qual é o aparelho, com as palavras "
        "do segurado: 'geladeira', 'fogão', 'micro-ondas', 'lava-louças'… A tecla "
        "da seguradora sai daqui — nunca escreva número."))
    bateria_busca_centro_automotivo: Optional[str] = Field(default=None, description=(
        "[auto bateria Porto] Bateria NOVA/TROCA: AVISE antes que a bateria é "
        "paga pelo segurado (valor na visita, muda com a marca) e anote se ele "
        "aceita que o prestador busque a bateria no Centro Automotivo. Só "
        "recarga: 'recarga'."))
    # 🔴 SPEC-121 F4b/F5 — eletricista da família, a chave do carro e o CARRO RESERVA.
    eletricista_tipo_opcao: Optional[str] = Field(default=None, description=(
        "[residencial eletricista HDI/Yelum] 'falta de energia' (a casa toda, sem luz) ou 'problema elétrico' (tomada, disjuntor, chuveiro…). Falta de energia na RUA é da concessionária: não aciona."))
    eletricista_item_opcao: Optional[str] = Field(default=None, description=(
        '[residencial eletricista HDI/Yelum] O item: tomada | interruptor | lâmpada/bocal | reator | disjuntor/fusível | chuveiro | torneira elétrica. 🔴 Portão eletrônico NÃO é eletricista; raio/queda de energia que queimou algo é SINISTRO → request_human_agent.'))
    eletricista_comodo: Optional[str] = Field(default=None, description=(
        '[residencial eletricista HDI/Yelum] Em que cômodo é o problema (suíte, banheiro social, área externa, cozinha…).'))
    veiculo_trancado: Optional[str] = Field(default=None, description=(
        '[auto chaveiro Yelum/HDI] Sim/Não: o carro está trancado?'))
    apolice_numero: Optional[str] = Field(default=None, description=(
        '[carro reserva] Número da apólice, só dígitos — o da apólice consultada; pergunte só se não achar.'))
    carro_reserva_motivo: Optional[str] = Field(default=None, description=(
        "[carro reserva] Por que precisa: 'sinistro' (batida, carro na oficina) | 'pane' | 'reparo em outra seguradora' | 'troca de condutor'. 🔴 Só sinistro segue sozinho; os outros vão a uma pessoa."))
    sinistro_numero: Optional[str] = Field(default=None, description=(
        '[carro reserva] O NÚMERO do sinistro (só dígitos). 🔴 PERGUNTE ao segurado; sem número, uma pessoa da corretora o obtém — nunca invente.'))
    carro_reserva_condutor_nome: Optional[str] = Field(default=None, description=(
        '[carro reserva] Nome de quem vai RETIRAR o carro (pode não ser o segurado).'))
    carro_reserva_condutor_cpf: Optional[str] = Field(default=None, description=(
        '[carro reserva] CPF de quem vai retirar — o sistema envia só os dígitos.'))
    carro_reserva_cidade: Optional[str] = Field(default=None, description=(
        '[carro reserva] Cidade onde quer retirar o carro.'))
    carro_reserva_data_hora: Optional[str] = Field(default=None, description=(
        "[carro reserva] Data e horário desejados para a retirada (ex.: '08/10 às 15h')."))
    carro_reserva_telefone: Optional[str] = Field(default=None, description=(
        '[carro reserva] Celular com DDD de quem vai retirar.'))
    carro_reserva_cnh_e_cartao: Optional[str] = Field(default=None, description=(
        "[carro reserva] Sim/Não: quem retira tem CNH original e válida E cartão de crédito NO NOME DELE com limite para a pré-autorização? 🔴 Pergunte; nunca afirme por ele. 'Não' → uma pessoa."))
    carro_reserva_diarias: Optional[str] = Field(default=None, description=(
        '[carro reserva] Só se a apólice consultada disser o limite de diárias do carro reserva (número). NÃO pergunte ao segurado e NÃO prometa diárias: a seguradora confirma.'))
    # 🔴 SPEC-121 F4b — o que o teto do bloco tinha cortado, de volta.
    bateria_amperes: Optional[str] = Field(default=None, description=(
        "[auto bateria Porto] Quantos amperes tem a bateria, se o segurado souber "
        "(ex.: '60'). Não sabe? Escreva 'não sei' — o sistema usa 60 Ah."))
    fora_da_cidade_da_apolice: Optional[str] = Field(default=None, description=(
        "[auto bateria Porto] Sim/Não: o carro está fora da cidade da apólice? "
        "(a consultora da Porto pergunta)"))
    aparelho_fora_da_garantia: Optional[str] = Field(default=None, description=(
        "[residencial eletrodomésticos Allianz] O aparelho já saiu da garantia do "
        "fabricante? 'sim' | 'não'. Na garantia a assistência NÃO cobre — é com o "
        "fabricante: diga isso ao segurado antes de acionar."))
    local_situacao: Optional[str] = Field(default=None, description=(
        "[auto guincho HDI/Yelum] Como é o lugar: 'local seguro' | 'escuro ou "
        "mal iluminado' | 'pouca circulação de pessoas'. 🔴 Decide a "
        "PRIORIDADE do atendimento — dizer 'seguro' sem perguntar rebaixa quem "
        "está parado num lugar perigoso."))


    # ══════════════════════════════════════════════════════════════════════
    # 🔴 O BURACO DA REGRA DO SUFIXO — achado do JUIZ 4
    # ══════════════════════════════════════════════════════════════════════
    #
    # A regra *"o que o MOTOR preenche não se cobra do cliente"* isenta todo
    # slot terminado em `_opcao`. 📊 Medido: para **7 slots em 33 pares (rota ×
    # passo)** o motor NÃO preenche — e o portão, cego por essa regra, carimba
    # `ready_to_send`.
    #
    # 🔴 Três deles são `sem_chute`, que declara literalmente *"esta pergunta
    #    NÃO tem default honesto"*. As duas regras se contradiziam: uma diz que
    #    o motor preenche, a outra diz que não existe o que preencher.
    #
    # 📊 O estrago, medido rodando as telas REAIS do corpus pelo motor: cinco
    #    rotas AAA vão a `needs_human` numa tela que existe no acervo —
    #    `azul/bateria` e `porto/bateria` (o submenu recarga × bateria nova),
    #    `hdi/socorro_mecanico` e `yelum/socorro_mecanico` (a situação de
    #    risco) e `porto/guincho` (quantas pessoas no táxi).
    #
    # ⚠️ É a MESMA classe do C1, um andar acima: a sessão nascia
    #    `ready_to_send` — o produto prometia acionar — e travava no meio da
    #    conversa com a URA rodando. Declarar os três é o ramo (a) da mesma
    #    decisão: pergunta de verdade, sem default honesto, precisa de onde
    #    morar.
    #
    # 🔵 Os outros quatro NÃO entram, e a distinção é medida: dois são
    #    `fallback_adaptive` (o cérebro responde — é o desenho declarado) e
    #    dois são tecla de menu que o motor injeta a partir do subserviço.
    situacao_risco_opcao: Optional[str] = Field(default=None, description=(
        "[auto HDI/Yelum] O segurado está numa situação de risco? Responda com "
        "as palavras da própria URA: 'Via com pouca iluminação' | 'Via com "
        "pouco movimento' | 'Nenhuma das anteriores'. 🔴 PERGUNTE — esta "
        "resposta muda a PRIORIDADE do atendimento, e presumir 'nenhuma' "
        "rebaixa quem está parado num lugar perigoso."))
    bateria_tipo_opcao: Optional[str] = Field(default=None, description=(
        "[auto bateria] É RECARGA da bateria que está no carro, ou o segurado "
        "quer comprar uma BATERIA NOVA? 🔴 São serviços diferentes e a URA "
        "pergunta — recarga é assistência, bateria nova é venda."))
    taxi_passageiros_opcao: Optional[str] = Field(default=None, description=(
        "[auto guincho, só quando há táxi] Quantas pessoas vão no táxi. "
        "⚠️ Só pergunte se o segurado JÁ pediu o transporte — quem só quer o "
        "guincho não deve ouvir esta pergunta."))
    # 🔴 SPEC-123 (conserto da bateria, 01/10) — a MESMA classe dos três acima.
    #    O passo `acompanhar_qual_solicitacao` (yelum/hdi auto, F6) exige
    #    `assistencia_aberta_opcao`; o motor o injeta SÓ no guincho ("GUINCHO",
    #    📊 yelum 75400aad — a única evidência). 📊 Nos outros 9 pares
    #    (`test_o_contrato_alcanca_o_portao`, ex. hdi × auto × bateria) o passo
    #    exige, o motor NÃO injeta e o passo é `sem_chute` — exatamente
    #    `situacao_risco_opcao`. ⛔ Não se inventa o rótulo dos outros serviços
    #    (nenhuma tela vista) e não se restringe o passo ao guincho (o desenho é
    #    cair no sem_chute, não numa tela órfã). Carregar não é cobrar: o portão
    #    continua pulando `sem_chute`, ninguém é perguntado antes da hora.
    assistencia_aberta_opcao: Optional[str] = Field(default=None, description=(
        "[auto HDI/Yelum, só se a ferramenta pedir] A URA disse que a placa já tem "
        "uma assistência ABERTA nas últimas 72 h e lista as solicitações: o rótulo "
        "da que é DESTE caso, como a URA escreve (ex.: 'GUINCHO'). ⛔ Nunca escolha "
        "a solicitação de OUTRO serviço — nenhuma opção dessa tela abre serviço novo."))


    # ══════════════════════════════════════════════════════════════════════
    # 🔴 CARREGAR NÃO É COBRAR — a distinção que faltava ao C1
    # ══════════════════════════════════════════════════════════════════════
    #
    # O C1 tratou "o portão não deve cobrar isto" e "o contrato não precisa
    # declarar isto" como a mesma decisão. **São opostas.**
    #
    #   o PORTÃO não cobra  →  ninguém é interrogado à toa por um galho que
    #                          quase nunca é tomado
    #   o CONTRATO carrega  →  quando o galho É tomado, a resposta tem onde
    #                          morar
    #
    # 🔴 Sem a segunda metade, a tela chega, o passo pede o slot, e o
    #    acionamento morre em `needs_human` com a URA rodando — que é
    #    exatamente o defeito que esta SPEC veio consertar, um andar acima.
    #
    # ⚠️ O portão continua pulando `sem_chute`: declarar aqui **não** faz
    #    ninguém perguntar antes da hora.
    transporte_destino: Optional[str] = Field(default=None, description=(
        "[auto guincho, só quando há táxi] Para onde a PESSOA quer ser levada. "
        "🔴 Não confunda com `local_destino`, que é para onde vai o VEÍCULO — "
        "mandar o táxi para a oficina leva o segurado ao lugar errado. "
        "⚠️ Só pergunte se ele JÁ pediu o transporte."))
    via_ou_rodovia_opcao: Optional[str] = Field(default=None, description=(
        "[auto] O veículo está numa VIA LOCAL (rua de cidade) ou numa RODOVIA? "
        "⚠️ Em rodovia pedagiada, quem tira o carro da pista é a "
        "concessionária — a seguradora atende depois disso."))
    profissional_opcao: Optional[str] = Field(default=None, description=(
        "[residencial Allianz] Qual profissional a URA deve chamar, com o nome "
        "que ela usa no menu (ex.: 'Eletricista', 'Encanador', 'Chaveiro'). "
        "⚠️ Só quando o menu do serviço não decidir sozinho."))
    servico_opcao: Optional[str] = Field(default=None, description=(
        "[auto] A opção do menu de serviços, com o rótulo da própria URA. "
        "⚠️ O motor costuma derivar isto do subserviço — preencha só se a "
        "ferramenta pedir."))

    session_id: Optional[str] = Field(default=None, description="(injetado pelo runtime — NÃO preencher)")


def _opcoes_recusadas(playbook_ref, subservice, kwargs, faltando):
    """Dos slots que faltam, quais têm valor PRESENTE e não reconhecido.

    🔴 Devolve `{slot: [titulos aceitos]}` — só para campo de escolha fechada
    do formulário nativo, que é onde a seguradora publicou a lista. Campo de
    texto livre não entra: ali não há lista para oferecer.
    """
    from app.services.corridor_playbooks import (
        get_playbook, _flow_components, _resolver_opcao_de_flow)
    pb = get_playbook(playbook_ref) or {}
    fora = {}
    for flow in (pb.get("native_flows") or {}).values():
        for _tela, comp in _flow_components(flow):
            slot = str(comp.get("slot") or "")
            if slot not in (faltando or []):
                continue
            valor = kwargs.get(slot)
            if not str(valor or "").strip():
                continue          # ausente: a outra mensagem serve
            if _resolver_opcao_de_flow(comp, valor) is not None:
                continue
            titulos = [str(o.get("title") or "") for o in comp.get("options") or []
                       if str(o.get("title") or "").strip()]
            if titulos:
                fora[slot] = titulos
    return fora



# ══════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-125 CONSERTO ÚNICO · Y1 (juiz B1) — T8 EM CÓDIGO: O "SIM" DO SEGURADO
# ══════════════════════════════════════════════════════════════════════════
#
# 📊 O defeito: a ÚNICA barreira do acionamento era `dados_confirmados`, e quem
# escreve esse campo é o MODELO — no mesmo turno em que os dados chegaram, se ele
# quiser. O residencial nem passava por ela. A linha de base da SPEC-125 mediu
# acionamento no turno do CPF, antes de qualquer "sim" (C2 t2, C3 t1, C13 t1). T8 é
# MANTER, e acionar é o único efeito IRREVERSÍVEL do atendimento: sai do prédio.
#
# A prova vem da CONVERSA DURÁVEL (`messages`, pela fonte única
# `historico_da_conversa`, com a corretora no filtro): o que a corretora PERGUNTOU
# ao segurado num turno ANTERIOR (a fala já gravada) e o que ELE respondeu depois.
# O modelo não escreve nessa tabela — o campo do modelo vira a AFIRMAÇÃO, e a
# conversa, a PROVA. Os dois são exigidos, nas duas linhas (auto e residencial).
#
# ⛔ Fail-closed: conversa não lida = sem prova = não aciona (o pior caso do
# "não" é uma confirmação a mais; o do "sim" é um guincho que não se desfaz).

#: A última pergunta da corretora é de CONFIRMAÇÃO? (texto sem acento, minúsculo)
#: 🔴 SPEC-125 CONSERTO Z1 (C4 da RODADA FINAL) — `\bconfirm\w*` solto casava "posso
#:    CONFIRMAR COM A EQUIPE se quiser" (uma oferta, 54 min antes, sobre carro reserva).
#:    "confirmar com …" é o AGENTE checando com outra pessoa: nunca pede o ok do segurado.
#: 🔴 N1 do laudo de confirmação — "Quer que eu acione …?", "Aciono?", "Seguimos?" pedem o ok
#:    e eram recusadas. ⚠️ "acionar"/"sigo" SOLTOS continuam não contando ("para eu acionar,
#:    me passa o CPF?" é pergunta de DADO): só a forma que PERGUNTA ("aciono?", "quer que eu
#:    acione") — e a pergunta inteira ainda precisa repetir o pedido (`_cita_o_pedido`).
#: 🔴 AJUSTE ZN · Z-N4 — "Quer que eu CONFIRME SE a apólice cobre guincho?" é o agente
#:    oferecendo CHECAR outra coisa (cobertura), não pedindo o ok do acionamento: "confirm… se"
#:    e "(quer) que eu confirme" não contam. constante_justificada: a forma "confirma que é
#:    o carro de placa…?" ainda conta como pergunta — quem a barra é a régua de ELEMENTOS
#:    (`confirmacao_comprovada`: pergunta fraca precisa repetir ≥ 2 partes do pedido).
_RX_PERGUNTA_DE_CONFIRMACAO = re.compile(
    r"(?<!\bque\seu\s)(?<!\bque\s)\bconfirm(?:a|as|e|em|ar|amos|ando|ado|ados|ada|adas)\b"
    r"(?!\s+(?:com|se)\b)|"
    r"\bposso\s+(?:acionar|chamar|pedir|solicitar|abrir|seguir|mandar|"
    r"enviar|registrar|prosseguir)\b|\bpodemos\s+(?:acionar|seguir|prosseguir|pedir|solicitar)\b|"
    r"\b(?:quer|queres|prefere|deseja)\s+que\s+(?:eu\s+)?(?:ja\s+)?(?:acione|chame|peca|solicite|"
    r"mande|abra|siga|prossiga|registre)\b|"
    r"\b(?:aciono|sigo|seguimos|prossigo|prosseguimos|solicito|peco|mando)\s*(?:agora\s*)?\?|"
    r"\b(?:sigo|seguimos|prossigo|prosseguimos|posso\s+seguir)\s+com\s+(?:a|o)\s+(?:abertura|"
    r"acionamento|pedido|chamado|solicitacao)\b[^.!]*\?|"
    r"\bpode\s+ser\b|\b(?:esta|estao|ta|tao|tudo|estiver)\s+(?:certo|certos|certa|correto|"
    r"corretos|correta|ok)\b|\bcorret[oa]s?\s*\?|\bisso\s+mesmo\b")

#: 🔴 Z-N4 — a pergunta FORTE pede o ok de ACIONAR (o verbo do acionamento: "posso acionar?",
#:    "quer que eu acione…", "aciono?", "seguimos?", "sigo com o pedido?"). Basta ela repetir UMA
#:    parte do pedido. A fraca ("confirma…?", "está certo?", "pode ser?") precisa de DUAS
#:    (serviço + lugar, serviço + placa…): "Confirma que é o carro de placa final 1D23?" pede o
#:    ok da PLACA, não do guincho.
_RX_PEDIDO_DE_OK_PARA_ACIONAR = re.compile(
    r"\bposso\s+(?:acionar|chamar|pedir|solicitar|abrir|seguir|mandar|"
    r"enviar|registrar|prosseguir)\b|\bpodemos\s+(?:acionar|seguir|prosseguir|pedir|solicitar)\b|"
    r"\b(?:quer|queres|prefere|deseja)\s+que\s+(?:eu\s+)?(?:ja\s+)?(?:acione|chame|peca|solicite|"
    r"mande|abra|siga|prossiga|registre)\b|"
    r"\b(?:aciono|sigo|seguimos|prossigo|prosseguimos|solicito|peco|mando)\s*(?:agora\s*)?\?|"
    r"\b(?:sigo|seguimos|prossigo|prosseguimos|posso\s+seguir)\s+com\s+(?:a|o)\s+(?:abertura|"
    r"acionamento|pedido|chamado|solicitacao)\b[^.!]*\?|"
    # o resumo que ANUNCIA o acionamento e pede o ok (📊 C2 t2 da RODADA FINAL: "Vou solicitar
    # socorro mecânico agora… Está tudo certo? Responda 'sim' para eu seguir.") — só conta
    # porque a fala já passou por `_RX_PERGUNTA_DE_CONFIRMACAO`
    r"\bvou\s+(?:ja\s+)?(?:acionar|solicitar|pedir|chamar|abrir|registrar|mandar|enviar)\b|"
    r"\b(?:para|pra)\s+(?:que\s+)?eu\s+(?:acionar|solicitar|pedir|chamar|seguir|prosseguir|"
    r"acione|solicite|peca|chame|siga|prossiga)\b")

#: O segurado DISSE SIM? (as primeiras palavras de uma ORAÇÃO; texto sem acento)
#: 🔴 SPEC-126 U2 (parte B) — a lista CRESCE só pelo que a bancada do "ok" PROVOU inequívoco
#:    (gabarito = ok E o classificador leu ok nas k=3; 📊 `RESULTADOS/spec126_u2a_confirmacao_
#:    luna_k3.json`, corpus sha e0a4b30b40064e64). constante_justificada, frase a frase:
#:    · `fechou`/`fexou` — conf-015 ("fechou"), conf-016 ("Fechou!"), conf-017 ("fexou"): 3/3 ok cada;
#:    · `vai la` — conf-018 ("vai lá"), conf-019 ("vai la"), conf-020 ("Vai lá, obrigado"): 3/3 ok cada;
#:    · `ok+` (okk, okkk) — conf-026 ("okk"): 3/3 ok. O "ok" de uma pergunta de DUAS opções continua
#:      NÃO valendo (`_pergunta_de_duas_opcoes`; conf-090..093, gabarito outra_coisa).
#:    Como o portão é regex E classificador, uma palavra fora desta lista RECUSA mesmo com o modelo
#:    dizendo ok — e é o lado seguro do T8 (uma confirmação a mais).
_RX_SIM_DO_SEGURADO = re.compile(
    r"^\W*(?:\w+\W+){0,2}?(?:sim|s|ss|sss|isso|exato|exatamente|correto|certo|certinho|"
    r"confirmo|confirmado|confirmada|confirma|pode|ok+|okay|okey|blz|beleza|positivo|claro|"
    r"perfeito|manda|mande|bora|aham|uhum|yes|fechado|combinado|ta\s+certo|ta\s+bom|"
    r"esta\s+certo|esta\s+correto|tudo\s+certo|isso\s+mesmo|aciona|acione|segue|siga|"
    r"fechou|fexou|vai\s+la)\b"
    # 🔴 SPEC-126 CONSERTO Y (RT-P1): 👌 SAIU — é "ok" para uns e "beleza, entendi" para outros
    #    (conf-158, gabarito outra_coisa escrito antes). 👍 e ✅ ficam: o Founder listou o 👍 (D5)
    #    e o ✅ é o rótulo do botão "✅ Pode acionar". constante_justificada: errar para cá custa
    #    UMA confirmação a mais; para lá, um guincho que não se desfaz (T8).
    r"|^\W*[\U0001F44D✅]"
    # N1: o segurado irritado depois de uma confirmação repetida — "já falei que sim"
    r"|\bja\s+(?:falei|disse|confirmei|respondi)\s+(?:que\s+)?(?:sim|pode|isso)\b")

#: Uma ORAÇÃO que é só o "não" (ou um "está errado") — "não" + vírgula + "pode mandar" é o
#: "não" de OUTRA pergunta ("alguém se machucou?") seguido do sim (N1 do laudo).
_RX_NAO_DO_SEGURADO = re.compile(
    r"^\W*(?:(?:ah|ai|opa|eita|ops|epa|xi|hum+|hmm+)\W+)?(?:nao|n|negativo|errado|errada|nunca)\W*$|"
    r"^\W*nao\s+(?:pode|quero|precisa|manda|e\s+(?:isso|esse|essa))\b")
#: a oração que é SÓ o "não" (com a interjeição: "ah não", "opa, não") — 🔴 CONSERTO Y: ANTES do sim
#: é o "não" de outra pergunta (N1: "Não, ninguém se machucou. Pode mandar"); DEPOIS do sim é a
#: RETIRADA ("sim. ah não, era pro carro da minha esposa" — conf-160).
_RX_NAO_SOZINHO = re.compile(r"\W*(?:(?:ah|ai|opa|eita|ops|epa|xi|hum+|hmm+)\W+)?(?:nao|n|negativo|nunca)\W*")
#: 🔴 SPEC-126 CONSERTO Y (juiz B1) — a NEGAÇÃO POSPOSTA do português falado: "manda não", "pode
#:    mandar não", "aciona não" (conf-142..144, conf-162). Só pesa na oração que, sem ela, seria o SIM.
#:    constante_justificada: "manda não" é recusa em todo o Brasil; errar para cá é UMA confirmação a mais.
_RX_NEGACAO_POSPOSTA = re.compile(r"\s(?:nao|n)\W*$")

#: 🔴 Z1 — a OBJEÇÃO ou o ADIAMENTO, em qualquer ponto da fala: "ta bom, DEPOIS eu peço"
#:    (o "sim" do C4), "vou ver", "sim, MAS o destino é outro", "ok — NA VERDADE a rua é Y".
#: constante_justificada: o pior caso de errar para cá é UMA confirmação a mais; o de errar
#:    para lá é um guincho que não se desfaz (T8). "mas rápido/por favor" não é objeção.
#: 🔴 SPEC-125 AJUSTE ZN · Z-N1 do laudo de confirmação nº 2 — o complemento NEUTRO não pesa:
#:    "Sim, vou esperar aqui na frente", "Sim, o endereço NÃO mudou", "sim, depois ME PASSA a
#:    previsão" e "Sim, amanhã de manhã" (no residencial agendado, a data É a resposta) eram
#:    recusados. constante_justificada, palavra a palavra:
#:    · "vou esperar" saiu: é ele dizendo ONDE espera o prestador, não adiando o pedido
#:      ("espera"/"pera" imperativos continuam — é o "segura aí");
#:    · "mudou/mudei" só sem "não/nada" antes ("não mudou" CONFIRMA o dado);
#:    · "depois" só quando o adiado é ELE ("depois eu peço", "depois vejo", "depois" sozinho):
#:      "depois ME/NOS passa/manda/avisa" é pedido ao agente (`_RX_DEPOIS_PARA_O_AGENTE`);
#:    · "amanhã/hoje à tarde…" ficam em `_RX_QUANDO_DO_SEGURADO`: só é adiamento se a
#:      pergunta NÃO disse esse mesmo quando (`_resposta_do_segurado(…, pergunta)`);
#:    · "mas" só é objeção quando a oração depois dele MEXE no pedido (`_RX_MAS_QUE_MEXE`):
#:      "sim, mas o destino é outro"/"mas não é guincho"/"mas leva pra concessionária"
#:      recusam; "sim, mas o carro é automático" é informação e passa.
#: 🔴 SPEC-126 U2 (parte B) — onde a regex dizia SIM errado (📊 juiz final da 125 pend. 5 e 6;
#:    laudo do BLOCO 0 item 9; a bancada do "ok": 19/74 falso ok da regex sozinha). constante_
#:    justificada, cada uma com o caso do corpus que a regex aceitava:
#:    · `pode deixar` — é "não precisa" (conf-068..071: "pode deixar", "Pode deixar, obrigado",
#:      "pode deixar q eu resolvo", "PODE DEIXAR"); o "pode" do começo lia como sim;
#:    · CONDIÇÃO — "só se for…", "desde que…", "se não for cobrar" (conf-079 "só se for de graça, pode
#:      acionar", conf-081 "pode, se não for cobrar nada"): o sim condicionado não é o ok do pedido;
#:    · "o/a/pro/pelo OUTRO" — o pedido é OUTRO, não este (conf-075 "não, pode acionar o outro",
#:      conf-076 "…o outro carro", conf-078 "não esse não, pode acionar o outro");
#:    · a DÚVIDA ("acho que sim") fica em `_RX_DUVIDA`. ⚠️ CONSERTO Y (§9.3, a lição migra): ela
#:      deixou de valer só "por oração" — dúvida em QUALQUER oração derruba o sim ("não sei, pode",
#:      conf-157); "pode mandar. seguro? acho que sim" pede uma confirmação a mais.
_RX_OBJECAO_DO_SEGURADO = re.compile(
    r"\b(?:mais\s+tarde|outra\s+hora|vou\s+(?:ver|pensar|decidir|olhar)|"
    r"vejo\s+(?:isso|depois)|deixa\s+(?:pra|para|que)|fica\s+(?:pra|para)\s+depois|"
    r"agora\s+nao|ainda\s+nao|espera|espere|pera|"
    r"calma|cancela\w*|desist\w*|errad[oa]s?|corrig\w*|na\s+verdade|so\s+que|porem|"
    r"(?:e|eh|era)\s+outr[oa]|outro\s+(?:endereco|lugar|local|destino|numero|telefone)|"
    r"outra\s+(?:rua|placa|cidade|oficina)|"
    r"pod[ei]\s+deix\w*|"
    r"(?:so|somente|apenas)\s+se|desde\s+que|contanto\s+que|"
    r"se\s+(?:nao\s+)?(?:for|tiver|custar|cobrar|pagar)|"
    r"(?:o|a|os|as|pro|pra|pros|pras|pelo|pela|no|na|do|da)\s+outr[oa]s?)\b"
    r"|(?<!\bnao\s)(?<!\bnada\s)\b(?:mudou|mudei)\b")

#: "depois" que é ELE adiando — salvo "depois (você) me/nos passa/manda/avisa…" (pedido ao agente).
_RX_DEPOIS_DO_SEGURADO = re.compile(r"\bdepois\b(?!\s+(?:voce\s+|vc\s+|ce\s+)?(?:me|nos)\b)")

#: o QUANDO dito pelo segurado — adiamento, salvo se a pergunta disse o mesmo quando.
#: 🔴 CONSERTO Y: a HORA ("às 18h", "18:30") também é um quando (conf-148 "depois das 18h", e
#:    "pode acionar às 18h" acionava). Se a pergunta disse a mesma hora (o residencial agendado), vale.
_RX_QUANDO_DO_SEGURADO = re.compile(
    r"\b(?:depois\s+de\s+amanha|amanha|hoje\s+(?:a\s+)?(?:tarde|noite)|semana\s+que\s+vem|"
    r"(?:na\s+)?segunda|(?:na\s+)?terca|(?:na\s+)?quarta|(?:na\s+)?quinta|(?:na\s+)?sexta|"
    r"(?:no\s+)?sabado|(?:no\s+)?domingo|\d{1,2}\s*(?:h|hs|hrs|horas?)|\d{1,2}:\d{2})\b")

#: 🔴 SPEC-126 CONSERTO Y (juiz B1) — o ADIAMENTO RELATIVO: "pode mandar daqui 1 hora", "em meia
#:    hora", "quando eu chegar lá", "assim que a gente sair" (conf-145, 146, 164). constante_justificada:
#:    só o "quando" com EU/A GENTE é adiamento dele ("quando chegar me avisa" é o prestador chegando —
#:    controle conf-174); "daqui" só seguido de TEMPO ("tô a 2 km daqui" — controle conf-175).
_RX_ADIAMENTO_RELATIVO = re.compile(
    r"\bdaqui\s+(?:a\s+)?(?:pouco|pouquinho|um\s+pouco|uns?|umas?|meia|alguns|algumas|\d+|uma?|"
    r"duas?|dois|tres|quatro|cinco|dez|quinze|vinte|trinta|quarenta)\b|"
    r"\bem\s+(?:uns?\s+|umas?\s+)?(?:\d+|uma?|meia|duas?|dois|tres|quatro|cinco|dez|quinze|vinte|"
    r"trinta|quarenta)\s*(?:min\w*|h|hs|hrs|horas?)\b|"
    r"\b(?:quando|assim\s+que|logo\s+que|depois\s+que|so\s+quando)\s+(?:eu|a\s+gente|nos)\b|"
    r"\bmais\s+pra\s+frente\b")

#: 🔴 SPEC-126 CONSERTO Y (juiz B1 · RT-P1) — a RETIRADA: o pedido deixou de existir. "pode mandar, já
#:    resolvi" (conf-149), "esquece" (conf-150), "o carro pegou" (conf-152/153), "já resolveu aqui"
#:    (conf-166), "deixa quieto" (conf-163). constante_justificada: só vale SEM negação nas 3 palavras
#:    antes ("o carro NÃO pegou", "NÃO consegui resolver" — controles conf-170/171 — são o problema,
#:    não a retirada); "pegou fogo" é emergência, nunca retirada.
_RX_RETIRADA_DO_SEGURADO = re.compile(
    r"\besquec\w*|\bdeixa\s+quieto\b|\bja\s+(?:resolv\w*|consegui\w*|deu\s+certo)|"
    r"\bresolv(?:i|eu|emos|ido)\b|\bconsegui\s+(?:resolver|arrumar|consertar|ligar|sozinh\w*)|"
    r"\bpegou\b(?!\s+fogo)|\bfuncionou\b|"
    r"\b(?:o\s+carro|a\s+moto|o\s+veiculo|ele|ela)\s+(?:ja\s+)?(?:ligou|voltou|deu\s+partida)\b|"
    r"\bnao\s+precis\w*\s+mais\b(?!\s+nada)|\bja\s+nao\s+precis\w*|\bdispens\w*")
_NEGACOES_DA_RETIRADA = frozenset({"nao", "n", "nem", "ainda", "nunca"})


def _retirou_o_pedido(plano: str) -> bool:
    """A fala (já `_plano`) RETIRA o pedido ("já resolvi", "esquece", "o carro pegou")? **PURA.**"""
    for m in _RX_RETIRADA_DO_SEGURADO.finditer(plano or ""):
        antes = re.findall(r"\w+", plano[:m.start()])[-3:]
        if not _NEGACOES_DA_RETIRADA.intersection(antes):
            return True
    return False

#: o "mas" que é intensificador ("mas rápido", "mas pode") nunca é objeção…
_RX_MAS_INTENSIFICADOR = re.compile(
    r"\bmas\s+(?:rapido|logo|depressa|por\s+favor|urgente|vem|venha|manda|pode|corre)\b")
#: …e o resto só é quando a oração depois dele MEXE no pedido: nega, corrige, troca o lugar,
#: o destino, a placa, o contato, condiciona (custo, "tem que") ou pergunta.
_RX_MAS_QUE_MEXE = re.compile(
    r"\bmas\b[^.;!\n]*?(?:\b(?:nao|n|nunca|outr[oa]s?|errad\w*|diferente\w*|troc\w*|mud\w*|corrig\w*|"
    r"quero|prefiro|preciso|precisa|gostaria|queria|melhor|so|ainda|antes|primeiro|leva\w*|"
    r"rua|avenida|av|oficina|endereco|destino|local|lugar|placa|numero|cep|bairro|telefone|"
    r"contato|tem\s+(?:que|de)|pag\w*|cust\w*|cobr\w*|valor|preco|franquia|gratis|"
    r"agora|depois|amanha|hoje|cancel\w*|desist\w*|espera\w*)\b|\?)")

#: 🔴 Z1 — a pergunta de confirmação repete O PEDIDO (o serviço, a placa, o lugar). O
#:    vocabulário de cada trabalho é o dos corredores (`canonical_subservice`) + como a
#:    atendente o escreve. constante_justificada: "posso confirmar com a equipe se quiser"
#:    (C4) não cita trabalho nenhum — e é isso que a separa do resumo do acionamento.
_PALAVRAS_DO_SERVICO = {
    "guincho": ("guincho", "reboque", "remocao", "socorro", "mecanic", "pane"),
    "bateria": ("bateria", "carga", "socorro", "pane"),
    "pneu": ("pneu", "estepe", "borrach"),
    "chaveiro": ("chaveiro", "chave", "trancad", "abrir a porta"),
    "vidros": ("vidro", "para-brisa", "parabrisa", "retrovisor", "farol", "lanterna"),
    "eletricista": ("eletricist", "eletric", "tomada", "disjuntor", "fiacao"),
    "encanador": ("encanador", "vazamento", "hidraulic", "cano", "torneira", "registro"),
    "desentupimento": ("desentup", "entupi"),
    "eletrodomesticos": ("eletrodomestic", "geladeira", "maquina", "lavadora", "fogao",
                         "microondas", "tecnico"),
    "maquina_de_lavar": ("maquina", "lavadora", "lava e seca", "tecnico"),
}
#: as palavras que nomeiam O ACIONAMENTO de qualquer trabalho ("a assistência", "o prestador")
_PALAVRAS_DE_QUALQUER_ACIONAMENTO = ("assistencia", "prestador", "acionamento", "socorro")
#: constante_justificada: palavras de lugar que NÃO identificam o lugar (aparecem em toda frase)
_PALAVRAS_DE_LUGAR_VAZIAS = frozenset({
    "avenida", "numero", "bairro", "cidade", "estado", "frente", "perto", "proximo", "proxima",
    "casa", "minha", "local", "lugar", "agora", "aqui", "esquina", "centro",
    # Z-N4: com a régua das DUAS partes, o lugar passou a contar palavras de 4 letras ("Rua
    # SETE 100", "Sao JOSE") e o número da casa — e estas de 4 letras não identificam nada
    "para", "pela", "pelo", "onde", "esta", "fica", "lado", "logo", "meio", "dentro"})

#: 🔴 Z1 — o agente ANUNCIOU um acionamento depois da pergunta: aquela confirmação foi GASTA.
#:    📊 C8: "Confirma: guincho da Rua Sete…?" → "sim" → "Pedido registrado na seguradora,
#:    protocolo …" → 63 min depois, "cadê o guincho?": a regra velha aceitava o sim gasto.
_RX_ACIONAMENTO_ANUNCIADO = re.compile(
    r"\bprotocolo\b|\b(?:foi|foram|esta|estao|ja)\s+(?:\w+\s+)?(?:acionad|solicitad|registrad|"
    r"abert|pedid)\w*|\bprestador\s+(?:foi\s+)?designad\w*|\bacionei\b|\bsolicitei\b|"
    r"\b(?:pedido|acionamento|chamado|solicitacao)\s+(?:de\s+\w+\s+)?(?:foi\s+)?(?:registrad|"
    r"acionad|abert|solicitad)\w*")


def _plano(texto) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def _termos_do_pedido(pedido: Optional[dict]) -> tuple:
    """`(palavras do serviço, pedaços de lugar, placa)` do pedido. Sem pedido: o
    vocabulário de TODOS os serviços (a bancada antiga, quem não sabe o pedido)."""
    from app.services.corridor_playbooks import canonical_subservice

    p = pedido or {}
    sub = str(p.get("subservice") or "").strip().lower()
    if not sub:
        servico = {w for ws in _PALAVRAS_DO_SERVICO.values() for w in ws}
    else:
        canon = canonical_subservice(sub)
        servico = set(_PALAVRAS_DO_SERVICO.get(canon) or ())
        servico |= {t for t in re.split(r"[_\s]+", _plano(canon) + " " + _plano(sub)) if len(t) >= 4}
    servico |= set(_PALAVRAS_DE_QUALQUER_ACIONAMENTO)
    lugar = set()
    for campo in ("local_atual", "local_destino", "local_rua", "local_bairro", "endereco_numero"):
        # 📊 C8: "Confirma: guincho da Rua Sete 100 para a Rua Nove 20?" — com 5+ letras o
        #    lugar sumia ("sete", "nove") e a pergunta contava UMA parte; o número da casa conta
        for t in re.findall(r"[a-z]{4,}|(?<!\d)\d{2,}(?!\d)", _plano(p.get(campo))):
            if t not in _PALAVRAS_DE_LUGAR_VAZIAS:
                lugar.add(t)
    placa = re.sub(r"[^a-z0-9]", "", _plano(p.get("veiculo_placa")))
    return servico, lugar, placa


def _partes_do_pedido_citadas(texto: str, pedido: Optional[dict]) -> int:
    """QUANTAS partes do pedido (serviço · lugar · placa) a fala do agente repete. **PURA.**"""
    plano = _plano(texto)
    servico, lugar, placa = _termos_do_pedido(pedido)
    n = 0
    if any(re.search(r"\b" + re.escape(w), plano) for w in servico):
        n += 1
    if lugar and any(re.search(r"\b%s\b" % re.escape(t), plano) for t in lugar):
        n += 1
    # a placa (ou o final dela, que é como a atendente a mostra: "placa final 2F90")
    alnum = re.sub(r"[^a-z0-9]", "", plano)
    if len(placa) >= 7 and placa[-4:] in alnum:
        n += 1
    return n


def _cita_o_pedido(texto: str, pedido: Optional[dict]) -> bool:
    """A fala do agente REPETE o pedido (o serviço, o lugar ou a placa)? **PURA.**"""
    return _partes_do_pedido_citadas(texto, pedido) >= 1


def _objecao_ou_adiamento(plano: str, pergunta: str = "") -> bool:
    """A fala (já `_plano`) OBJETA ao pedido ou ADIA o próprio acionamento? **PURA.**

    Z-N1: o complemento neutro não pesa — ver a constante_justificada de
    `_RX_OBJECAO_DO_SEGURADO`. `pergunta` (já `_plano`) é a confirmação a que ele responde:
    o QUANDO que ela mesma disse ("…amanhã de manhã. Confirma?") repetido é a resposta.
    """
    if _RX_OBJECAO_DO_SEGURADO.search(plano) or _RX_DEPOIS_DO_SEGURADO.search(plano):
        return True
    # 🔴 CONSERTO Y: o adiamento relativo, a retirada, e o "pode deixar" partido pela pontuação
    #    ("Pode. Deixa", "pode... deixar" — conf-161; e em dois balões, quando a rede lê as falas JUNTAS)
    if _RX_ADIAMENTO_RELATIVO.search(plano) or _retirou_o_pedido(plano):
        return True
    if re.search(r"\bpod[ei]\s+deix\w*", re.sub(r"[^\w\s]+", " ", plano)):
        return True
    for m in _RX_QUANDO_DO_SEGURADO.finditer(plano):
        if not re.search(r"\b%s\b" % re.escape(m.group(0)), pergunta or ""):
            return True
    sem_intensificador = _RX_MAS_INTENSIFICADOR.sub(" ", plano)
    return bool(_RX_MAS_QUE_MEXE.search(sem_intensificador))


#: SPEC-125 (rodada pós-conserto Z, 📊 C3 t2): "sou eu que tô com o carro pode acionar" — a
#: autorização vem no FIM da oração, sem vírgula, e o sim do começo não a via ("outro" → a
#: ferramenta recusou e a conversa acabou sem acionar). Só o verbo de autorizar o acionamento
#: no fim da oração conta; a objeção/adiamento continua vencendo (`_objecao_ou_adiamento` antes).
_RX_AUTORIZA_NO_FIM = re.compile(
    r"\b(?:pode|podem)\s+(?:acionar|mandar|chamar|pedir|enviar|seguir|solicitar)\W*$")

#: 🔴 JUIZ FINAL 125 — o "pode" depois de NEGAÇÃO, DÚVIDA ou PERGUNTA não autoriza nada.
#: 📊 "a seguradora disse que não pode acionar", "não sei se pode acionar", "você não pode
#:    acionar", "quem pode acionar?" saíam SIM — e o guincho não se desfaz (T8).
#: constante_justificada: errar para cá custa UMA confirmação a mais ("se quiser pode mandar").
_RX_PODE_QUE_NAO_AUTORIZA = re.compile(
    r"\b(?:nao|n|nem|ninguem|nunca|jamais|quem|como|onde|quando|sera|se|sei|so|somente|"
    r"apenas|pergunt\w*)\b.*\bpodem?\b")  # "já DISSE que pode" é o sim irritado (N1)

#: 🔴 SPEC-126 U2 (parte B) · a DÚVIDA não é o sim: "acho que sim", "acredito que sim" (conf-129,
#:    conf-130 — gabarito outra_coisa, escrito antes; o classificador leu outra_coisa nas k=3). A ORAÇÃO
#:    com dúvida não conta como sim (nem como não). constante_justificada: o sim de quem não tem certeza
#:    não autoriza um guincho que não se desfaz — e o portão combinado já o recusava pelo classificador.
#: 🔴 CONSERTO Y (RT-P1): "não sei, pode" (conf-157) — o "não sei" é dúvida, e a dúvida em QUALQUER
#:    oração da resposta deixa de ser o sim (a lição do U2-B migra: ela não apagava o sim de outra
#:    oração; agora apaga — "pode mandar. seguro? acho que sim" pede UMA confirmação a mais, o lado
#:    seguro do T8).
_RX_DUVIDA = re.compile(r"\b(?:acho|acredito|creio|imagino)\s+que\b|\btalvez\b|\bsei\s+la\b|"
                        r"\bnao\s+sei\b(?!\s+(?:o|a|os|as)\s+(?:numero|nome|endereco|cep|bairro|rua)\b)")

#: 🔴 SPEC-126 U2 (parte B) · a pergunta de DUAS opções — "Posso acionar AGORA ou prefere AMANHÃ?".
#:    📊 laudo do BLOCO 0 item 9 / fora do escopo 6: "ok" (e "ok, prefiro amanhã") a ela ACIONAVA —
#:    conf-083..085 e conf-090..093 da bancada. Ali o "ok"/"sim"/"beleza" sozinho não escolhe nada.
#:    constante_justificada: só conta como duas opções o "ou" que oferece ADIAR ou ESPERAR (ou o
#:    "agora ou …"): "está certo ou quer mudar algo?" continua uma pergunta de UMA opção.
_RX_PERGUNTA_DE_DUAS_OPCOES = re.compile(
    r"\bagora\s+ou\b|\bou\s+(?:(?:voce|vc)\s+)?(?:prefere|preferir|preferiria|deseja|acha\s+melhor|"
    r"melhor|seria|fica|deixa|deixamos|espera|esperamos|aguard\w*|agend\w*|amanha|depois|"
    r"mais\s+tarde|outro\s+dia|outra\s+hora|outro\s+horario|quer\s+(?:deixar|esperar|agendar|"
    r"marcar|que\s+(?:eu\s+)?(?:espere|aguarde|agende|marque|deixe)))\b")
#: …e a ESCOLHA de acionar agora, que é o ok dela. constante_justificada: conf-053 ("agora"),
#:    conf-054 ("Agora, por favor"), conf-055 ("pode ser agora"), conf-056 ("agora mesmo!") — gabarito
#:    ok e o classificador leu ok nas k=3 (📊 spec126_u2a_confirmacao_luna_k3.json). O verbo de acionar
#:    ("pode acionar", "manda") também escolhe a 1ª opção; "pode" sozinho não.
_RX_ESCOLHEU_AGORA = re.compile(
    r"\b(?:agora|agorinha|ja|imediatamente|o\s+quanto\s+antes|o\s+mais\s+rapido)\b|"
    r"\b(?:pode|podem)\s+(?:acionar|mandar|chamar|pedir|enviar|solicitar|seguir)\b|"
    r"^\W*(?:aciona|acione|manda|mande)\b")
#: a outra opção nomeada na fala ("prefiro", "melhor amanhã") — nunca o ok
_RX_ESCOLHEU_A_OUTRA = re.compile(r"\b(?:prefir\w*|prefer\w*|melhor)\b")


def _trecho_da_pergunta(pergunta_plana: str) -> str:
    """A ÚLTIMA frase interrogativa da fala do agente (já `_plano`). **PURA.**"""
    p = str(pergunta_plana or "")
    fim = p.rfind("?")
    if fim < 0:
        return p
    return re.split(r"[.!\n]", p[:fim])[-1]


def _pergunta_de_duas_opcoes(pergunta_plana: str) -> bool:
    """A pergunta oferece acionar AGORA **ou** adiar/esperar? **PURA.**"""
    return bool(_RX_PERGUNTA_DE_DUAS_OPCOES.search(_trecho_da_pergunta(pergunta_plana)))


#: 🔴 SPEC-126 U2 (parte B) · o "sim" que TROCA o serviço. 📊 rodada Luna da U1 (C4 t1): "Pode acionar
#:    sim, preciso de um guincho pra levar na oficina" depois do resumo de SOCORRO MECÂNICO → o portão
#:    aceitou e acionou o serviço ERRADO. O nome de serviço que o segurado diz junto do sim tem de ser
#:    o do pedido. constante_justificada: só NOMES de serviço (como o segurado os diz), nunca sintoma
#:    ("vazamento", "não liga") — sintoma não troca o pedido.
_SERVICO_DITO = {
    "guincho": r"guinch\w*|reboqu\w*|rebocar",
    "mecanico": r"mecanic\w*",
    "chaveiro": r"chaveir\w*",
    "pneu": r"pneus?|estepe|borracheir\w*",
    "bateria": r"bateria|chupeta",
    "vidros": r"vidros?|vidraceir\w*|para\W?brisas?",
    "eletricista": r"eletricist\w*",
    "encanador": r"encanador\w*",
    "desentupimento": r"desentup\w*",
    "transporte": r"taxi|carro\s+reserva",
}
_RX_SERVICO_DITO = {k: re.compile(r"\b(?:%s)\b" % v) for k, v in _SERVICO_DITO.items()}
#: constante_justificada: o GUINCHO leva o carro AO mecânico ("leva no meu mecânico") — citar o
#:    mecânico junto do guincho é o destino, não outro serviço. O contrário (guincho no resumo de
#:    socorro mecânico) É a troca do C4.
_SERVICO_DITO_TOLERADO = {"guincho": {"mecanico"}}


def _familia_do_pedido(pedido: Optional[dict]) -> Optional[str]:
    """A família (chave de `_SERVICO_DITO`) do serviço do PEDIDO, lida do próprio nome do
    subserviço ("troca_de_pneu" → pneu, "socorro_mecanico" → mecanico). **PURA.**"""
    sub = str((pedido or {}).get("subservice") or "").strip().lower()
    if not sub:
        return None
    try:
        from app.services.corridor_playbooks import canonical_subservice

        nomes = {sub, canonical_subservice(sub) or sub}
    except Exception:  # noqa: BLE001 — a regra nunca derruba o portão
        nomes = {sub}
    texto = " ".join(_plano(n).replace("_", " ") for n in nomes)
    for familia, rx in _RX_SERVICO_DITO.items():
        if rx.search(texto):
            return familia
    return None


def servico_trocado(respostas, pedido: Optional[dict]) -> bool:
    """As falas do segurado NOMEIAM serviço, e NENHUM deles é o do pedido? **PURA.**

    Sem pedido (ou sem serviço nomeado nas falas) → `False`: quem decide é o resto do portão.
    Nomear o do pedido junto de outro ("pode mandar o guincho, a bateria arriou") não é troca."""
    if not pedido or not str(pedido.get("subservice") or "").strip():
        return False
    ditos = {f for t in (respostas or []) for f, rx in _RX_SERVICO_DITO.items() if rx.search(_plano(t))}
    if not ditos:
        return False
    familia = _familia_do_pedido(pedido)
    aceitos = ({familia} | _SERVICO_DITO_TOLERADO.get(familia, set())) if familia else set()
    return not (ditos & aceitos)


def _resposta_do_segurado(texto: str, pergunta: str = "") -> str:
    """`"sim"` · `"nao"` · `"outro"` — UMA fala do segurado. **PURA.**

    A fala vira ORAÇÕES (vírgula, ponto, quebra): "Não, ninguém se machucou. Pode mandar"
    é o "não" de outra pergunta e o SIM desta (N1). Objeção ao pedido ou adiamento do
    próprio acionamento, em qualquer ponto, vence o sim ("ta bom, depois eu peço" do C4;
    "sim, mas o destino é outro"); o complemento neutro não (Z-N1: "Sim, vou esperar aqui").
    """
    plano = _plano(texto)
    if not plano:
        return "outro"
    if _objecao_ou_adiamento(plano, _plano(pergunta)):
        return "nao"
    if _pergunta_de_duas_opcoes(_plano(pergunta)):
        # SPEC-126 U2 (parte B): a pergunta de DUAS opções só aceita a ESCOLHA de acionar agora.
        # A outra opção nomeada ("prefiro…", "melhor…") é o não; o "ok"/"sim"/"beleza" sozinho não
        # escolhe nada (outro — o agente pergunta de novo); a escolha dita em PERGUNTA também não.
        if ((_RX_ESCOLHEU_A_OUTRA.search(plano) or _RX_QUANDO_DO_SEGURADO.search(plano))
                and not re.search(r"\bagora\b", plano)):
            return "nao"
        if re.match(r"^\W*(?:nao|n|negativo)\b", plano):
            return "nao"
        escolheu = (_RX_ESCOLHEU_AGORA.search(plano) and not _RX_PODE_QUE_NAO_AUTORIZA.search(plano)
                    and not plano.rstrip().endswith("?"))
        return "sim" if escolheu else "outro"
    # 🔴 SPEC-126 CONSERTO Y (juiz B1 · RT-P1) — A ÚLTIMA PALAVRA VALE. As orações são lidas EM
    #    ORDEM, cada uma com o seu fim ("?" = pergunta). Depois do sim, o "não" sozinho é RETIRADA
    #    ("sim. ah não…"), e a pergunta derruba o sim ("sim, quanto custa?" — conf-155: ele quer saber
    #    antes; o agente responde e confirma de novo). ANTES do sim, o "não" sozinho continua sendo o
    #    de outra pergunta (N1). A oração do sim com o "não" no FIM é recusa ("manda não"). A dúvida em
    #    qualquer oração não é o sim ("não sei, pode").
    pedacos = re.split(r"([,.;:!?\n…]+|\s+[-–—]\s+)", plano)
    oracoes = []
    for k in range(0, len(pedacos), 2):
        o = pedacos[k].strip()
        fim = pedacos[k + 1] if k + 1 < len(pedacos) else ""
        if o:
            oracoes.append((o, "?" in fim))
    nao_antes = forte = sim = duvida = pergunta_depois = False
    for o, e_pergunta in oracoes:
        if _RX_DUVIDA.search(o):
            duvida = True
            continue
        if _RX_NAO_DO_SEGURADO.search(o):
            # "não" sozinho na oração ANTES do sim é o de OUTRA pergunta; DEPOIS, a retirada;
            # "não pode"/"não quero"/"não é isso" é recusa, venha o que vier.
            if _RX_NAO_SOZINHO.fullmatch(o) and not sim:
                nao_antes = True
            else:
                forte = True
            continue
        if ((_RX_SIM_DO_SEGURADO.search(o) or _RX_AUTORIZA_NO_FIM.search(o))
                and not _RX_PODE_QUE_NAO_AUTORIZA.search(o)):
            if _RX_NEGACAO_POSPOSTA.search(o):
                forte = True                 # "manda não", "pode mandar não"
            elif e_pergunta:
                pergunta_depois = pergunta_depois or sim   # "sim?" não é o sim; nem o depois dele
            else:
                sim = True
            continue
        if e_pergunta and sim:
            pergunta_depois = True           # "sim, quanto custa?"
    if forte:
        return "nao"
    if duvida or pergunta_depois:
        return "outro"
    if sim:
        return "sim"
    return "nao" if nao_antes else "outro"


def _instante(valor: Any):
    """`datetime` com fuso (UTC se vier sem) de um datetime/ISO; `None` se ilegível. **PURA.**"""
    from datetime import datetime, timezone

    if valor is None or valor == "":
        return None
    try:
        dt = valor if isinstance(valor, datetime) else datetime.fromisoformat(
            str(valor).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def confirmacao_comprovada(falas, pedido: Optional[dict] = None, *, acionado_em: Any = None) -> dict:
    """O segurado CONFIRMOU o acionamento? **PURA** — a REDE (regex) do portão.

    🔴 SPEC-126 U2 (parte B): sozinha ela NÃO aciona mais nada — o portão é
    `portao_da_confirmacao` (esta rede E o classificador). Quem a chama direto é a régua da
    bancada de conversa (`acionou_sem_confirmar`) e a bancada do "ok" (a coluna `regex`).
    Com sim, devolve também `pergunta` e `respostas` — o que o classificador vai ler.

    `falas`: `[(quem, texto)]` do assunto, da mais antiga para a mais nova, COM as
    do turno de agora; `quem` ∈ segurado · agente · equipe. `pedido`: os argumentos
    do acionamento que se quer fazer (o serviço, o lugar, a placa) — sem ele, vale o
    vocabulário de qualquer serviço.

    🔴 SPEC-125 CONSERTO Z1 (📊 C4 da RODADA FINAL, 2/2: aceitou "posso confirmar com
    a equipe se quiser", de 54 min antes e de outro assunto, e "ta bom, depois eu peço"):
    ```
    a ÚLTIMA pergunta da corretora (fala com "?" ou "confirm…") é a de CONFIRMAÇÃO
      DESTE acionamento — pede o ok E repete o pedido (serviço, lugar ou placa);
    nenhuma fala do agente DEPOIS dela anuncia um acionamento (a confirmação não foi gasta);
    as falas do segurado depois dela, lidas JUNTAS, têm um SIM de verdade e nenhum NÃO
      (objeção ao pedido ou adiamento do próprio acionamento).
    ```
    🔴 AJUSTE ZN (laudo de confirmação nº 2): Z-N1 complemento neutro não pesa ("Sim, vou
    esperar aqui", "Sim, amanhã de manhã" quando a pergunta disse amanhã); Z-N3 o dado que
    faltava + "pode mandar" em dois balões vale; Z-N4 a pergunta sem o verbo de acionar
    ("confirma que é a placa…?") precisa repetir DUAS partes do pedido.
    Devolve `{"comprovada": bool, "motivo": str}`.

    🔴 SPEC-126 CONSERTO Y (RT-B3) — a confirmação se GASTA pelo FATO, não pela prosa: `acionado_em`
    é o instante (UTC) do último acionamento que SAIU desta conversa, lido do estado DURÁVEL (a ficha,
    `acionamento.enviado_em`/`enfileirado_em` — `InsurerDispatchTool._acionamento_desta_conversa`). A
    pergunta de confirmação que não é POSTERIOR a ele já foi usada → `{"gasta": True}`. As falas podem
    vir como `(quem, texto, quando)`; sem o `quando` da pergunta e com um acionamento feito, conta como
    gasta (o lado seguro do T8: uma confirmação a mais).
    """
    lista = []
    for f in (falas or []):
        f = tuple(f)
        lista.append((str(f[0] or ""), str(f[1] or ""), f[2] if len(f) > 2 else None))
    acionado_em = _instante(acionado_em) if acionado_em is not None else None
    ultima = None
    for i in range(len(lista) - 1, -1, -1):
        quem, texto, _q = lista[i]
        if quem in ("agente", "equipe") and ("?" in texto or "confirm" in _plano(texto)):
            ultima = i
            break
    if ultima is None:
        return {"comprovada": False, "motivo": "nenhuma pergunta da corretora na conversa"}
    pergunta = lista[ultima][1]
    if not _RX_PERGUNTA_DE_CONFIRMACAO.search(_plano(pergunta)):
        return {"comprovada": False,
                "motivo": "a última pergunta ao segurado não foi a de confirmação"}
    partes = _partes_do_pedido_citadas(pergunta, pedido)
    if partes < 1:
        return {"comprovada": False,
                "motivo": "a última pergunta não repete o pedido (serviço, lugar ou placa) — "
                          "não é a confirmação deste acionamento"}
    # Z-N4: sem o verbo de acionar ("posso acionar?"), a pergunta precisa repetir DUAS partes
    #       (ou todas as que o pedido tem, se ele só traz o serviço)
    _s, _lugar, _placa = _termos_do_pedido(pedido)
    exigidas = min(2, 1 + bool(_lugar) + (len(_placa) >= 7))
    if partes < exigidas and not _RX_PEDIDO_DE_OK_PARA_ACIONAR.search(_plano(pergunta)):
        return {"comprovada": False,
                "motivo": "a última pergunta pede o ok de UMA parte (a placa, a cobertura), não "
                          "do acionamento — falta o resumo ou o \"posso acionar?\""}
    # 🔴 CONSERTO Y (RT-B3): o FATO durável gasta a confirmação — um acionamento que saiu desta
    #    conversa DEPOIS da pergunta (ou sem como provar que a pergunta é posterior a ele).
    if acionado_em is not None:
        q_em = _instante(lista[ultima][2])
        if q_em is None or q_em <= acionado_em:
            return {"comprovada": False, "gasta": True,
                    "motivo": "a confirmação já foi usada: um acionamento desta conversa saiu "
                              "depois dela"}
    depois = lista[ultima + 1:]
    # (cinto) a prosa do agente que anuncia o acionamento também gasta — nunca é a única trava
    if any(q in ("agente", "equipe") and _RX_ACIONAMENTO_ANUNCIADO.search(_plano(t))
           for q, t, _q in depois):
        return {"comprovada": False,
                "motivo": "a confirmação já foi usada num acionamento anterior"}
    respostas = [t for q, t, _q in depois if q == "segurado" and t.strip()]
    if not respostas:
        return {"comprovada": False,
                "motivo": "o segurado ainda não respondeu à confirmação"}
    leituras = [_resposta_do_segurado(r, pergunta) for r in respostas]
    if "nao" in leituras:
        return {"comprovada": False, "motivo": "o segurado não disse sim"}
    # Z-N3: as falas dele depois da pergunta são lidas JUNTAS ("Oficina do Zé" + "pode
    # mandar" em dois balões): o dado que faltava não apaga o sim que veio em seguida.
    if "sim" not in leituras:
        return {"comprovada": False,
                "motivo": "a resposta seguinte do segurado não foi o sim"}
    # 🔴 CONSERTO Y (RT-P1) — A RAJADA: as falas JUNTAS também têm de dizer sim, e a ÚLTIMA palavra
    #    vale: ["pode", "deixar"] é "pode deixar"; ["pode mandar", "esquece"], ["sim", "o carro
    #    pegou"] retiram; ["sim", "vai ter custo?"] pergunta antes de acionar (conf-150..156).
    juntas = _resposta_do_segurado("\n".join(respostas), pergunta)
    if juntas != "sim":
        return {"comprovada": False,
                "motivo": ("o segurado não disse sim" if juntas == "nao" else
                           "depois do sim o segurado perguntou ou ficou em dúvida — responda e "
                           "confirme de novo")}
    # SPEC-126 U2 (parte B): o sim que pede OUTRO serviço não é o ok DESTE pedido (📊 C4 t1 da U1)
    if servico_trocado(respostas, pedido):
        return {"comprovada": False,
                "motivo": "o segurado pediu outro serviço junto do sim — refaça o resumo com o que "
                          "ele pediu e confirme de novo"}
    # `pergunta` e `respostas` vão ao CLASSIFICADOR (`portao_da_confirmacao`): ele lê as MESMAS falas
    return {"comprovada": True, "motivo": "confirmado pelo segurado depois da pergunta",
            "pergunta": pergunta, "respostas": respostas}


def decisao_do_portao(rede: dict, classificacao: Optional[dict]) -> dict:
    """🔴 SPEC-126 §3.1 (2) — o PORTÃO decide: aciona só se a REGEX (`confirmacao_comprovada`) E o
    CLASSIFICADOR (`app.atendimento.confirmacao`) disserem ok. **PURA** — a regra única que a
    ferramenta e a bancada do "ok" usam (uma regra, dois consumidores; CLAUDE.md §9.4).

    `classificacao`: `{"leitura", "motivo", …}` do classificador, ou `None` (não foi chamado)."""
    leitura = str((classificacao or {}).get("leitura") or "")
    if not (rede or {}).get("comprovada"):
        return {"comprovada": False, "motivo": str((rede or {}).get("motivo") or ""),
                "camada": "regex", "leitura": leitura or None}
    if leitura != "ok":
        return {"comprovada": False, "camada": "classificador", "leitura": leitura or None,
                "motivo": "o classificador não leu um ok claro (%s · %s) — peça a confirmação de novo"
                          % (leitura or "sem leitura", (classificacao or {}).get("motivo") or "?")}
    return {"comprovada": True, "camada": "regex+classificador", "leitura": "ok",
            "motivo": "confirmado pelo segurado depois da pergunta (regex e classificador)"}


async def portao_da_confirmacao(falas, pedido: Optional[dict] = None, *, company_id: str,
                                llm: Any = None, acionado_em: Any = None) -> dict:
    """🔴 SPEC-126 U2 (parte B) — O PORTÃO do acionamento: regex E classificador. **Nunca levanta.**

    A regex (`confirmacao_comprovada`) é a REDE e roda primeiro, de graça: ela acha a pergunta de
    confirmação DESTE pedido e as falas do segurado depois dela. Só se ela disser sim, o
    classificador lê AS MESMAS falas — UMA chamada por tentativa de acionamento, nunca por turno
    (quem chama é o `_arun` da ferramenta, já com o agente ligado). Classificador fora do ar,
    passou do teto (`TETO_DA_CHAMADA_S`), saída inválida ou `outra_coisa`/`nao` → NÃO aciona: o
    `confirm_first` volta com a linha pronta e o agente pede de novo (o lado seguro do T8).

    `llm`: só a bancada e os testes injetam o modelo; produção usa o papel `confirmacao` do Model
    Router (`classificar_confirmacao` → `invocar_com_reserva`)."""
    rede = confirmacao_comprovada(falas, pedido, acionado_em=acionado_em)
    if not rede.get("comprovada"):
        return {**decisao_do_portao(rede, None), **({"gasta": True} if rede.get("gasta") else {})}
    try:
        from app.atendimento.confirmacao import classificar_confirmacao

        classificacao = await classificar_confirmacao(
            rede.get("pergunta") or "", rede.get("respostas") or [],
            company_id=str(company_id or "") or None, llm=llm)
    except Exception as erro:  # noqa: BLE001 — `classificar_confirmacao` não levanta; cinto e suspensório
        classificacao = {"leitura": "outra_coisa", "motivo": f"erro:{type(erro).__name__}"}
    decisao = decisao_do_portao(rede, classificacao)
    if not decisao["comprovada"]:
        logger.warning("[InsurerDispatch] a regex leu sim e o classificador não (%s) — NADA acionado",
                       decisao.get("motivo"))
    return decisao


async def prova_da_confirmacao(db, *, company_id: str, session_id: str,
                               pedido: Optional[dict] = None, llm: Any = None,
                               acionado_em: Any = None) -> dict:
    """A prova do "sim", lida da conversa DURÁVEL, pelo PORTÃO (regex E classificador —
    `portao_da_confirmacao`). **Nunca levanta**; no escuro, sem prova.

    🔴 CONSERTO Y (RT-B3): as falas vão COM o instante (`Fala.quando`) e `acionado_em` (o último
    acionamento desta conversa, da ficha) gasta a pergunta que não é posterior a ele."""
    try:
        from app.agents.historico_da_conversa import historico_do_atendimento

        hist = await historico_do_atendimento(
            db, company_id=str(company_id or ""), session_id=str(session_id or ""),
            turno_corrente=False)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[InsurerDispatch] conversa não lida para a confirmação (%s)",
                       type(erro).__name__)
        return {"comprovada": False, "motivo": "conversa indisponível"}
    if not getattr(hist, "lida", False):
        return {"comprovada": False,
                "motivo": "conversa indisponível (%s)" % (getattr(hist, "erro", "") or "?")}
    return await portao_da_confirmacao(
        [(f.quem, f.texto, getattr(f, "quando", None)) for f in hist.falas], pedido,
        company_id=str(company_id or ""), llm=llm, acionado_em=acionado_em)


#: 🔴 SPEC-125 CONSERTO Z2/Z3 — a confirmação é UMA linha de resumo + o ok, com o que JÁ se
#:    sabe. 📊 RODADA FINAL: o texto antigo mandava confirmar "o telefone de contato" e o
#:    número da conversa não chegava a ninguém — C2, C3 e C11 responderam "não consigo ver o
#:    número deste WhatsApp" e pediram o telefone; C11 pediu o CPF de novo (2/2); o 1º
#:    acionamento caiu do turno 1,09 para o 4,33.
REGRA_DO_RESUMO_DE_CONFIRMACAO = (
    "Mande ao cliente UMA linha com o resumo do pedido e peça o ok — ex.: \"Guincho para o "
    "carro de placa final 1D23, da Rua X, 100 até a oficina Y, contato neste número "
    "(final <os 4 últimos>). Posso acionar?\" — e ESPERE o \"sim\". NÃO pergunte o que já se sabe: o "
    "telefone DESTA conversa já é o contato (só pergunte outro se ele disser que quem vai "
    "receber é outra pessoa), e CPF, placa, veículo e endereço que estão na ficha, na apólice, "
    "no bloco \"o que já sabemos\" ou na conversa entram no resumo, não viram pergunta. Pergunte "
    "só o que NINGUÉM disse ainda, junto no mesmo resumo. Se ele corrigir um dado, use o "
    "corrigido.")


def telefone_da_conversa(session_id: Any) -> str:
    """O telefone da conversa de WhatsApp (`whatsapp:{telefone}:{empresa}:{agente}`), com
    DDD e sem o país — `""` fora do WhatsApp ou se não for telefone válido. **PURA.**"""
    partes = str(session_id or "").split(":")
    if len(partes) < 3 or partes[0] != "whatsapp":
        return ""
    d = _digitos(partes[1])
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    return d if telefone_br_valido(d) else ""


def com_o_telefone_da_conversa(kwargs: dict) -> dict:
    """🔴 Z2 — `telefone_contato` vazio vira o telefone DESTA conversa (o mesmo que o
    `_arun` já usa como o telefone do cliente). O modelo nunca escreve este valor: vem da
    sessão, que o `tool_node` injeta do estado. O que o segurado disser vence."""
    if str((kwargs or {}).get("telefone_contato") or "").strip():
        return kwargs
    fone = telefone_da_conversa((kwargs or {}).get("session_id"))
    return {**kwargs, "telefone_contato": fone} if fone else kwargs


#: 🔴 SPEC-126 U1 · O ELO DO C13 — o nome do serviço na LINHA PRONTA (como a atendente o diz).
#:    Fora da lista, o nome do corredor com espaço no lugar do "_".
_NOME_DO_SERVICO_NA_LINHA = {
    "socorro_mecanico": "socorro mecânico", "troca_de_pneu": "troca de pneu", "pneu": "troca de pneu",
    "bateria": "socorro de bateria", "taxi": "táxi", "maquina_de_lavar": "conserto da máquina de lavar",
    "eletrodomesticos": "conserto do eletrodoméstico",
}
#: Delimitadores da linha pronta no texto ao modelo — o fiscal de `nodes` a reencontra por eles.
LINHA_PRONTA_ABRE, LINHA_PRONTA_FECHA = "«", "»"


def _limpo(valor: Any) -> str:
    return re.sub(r"\s+", " ", str(valor or "")).strip().strip(".,;:-–— ")


#: 📊 rodada Luna da U1 (C4 t1): `local_atual="na garagem"` saía "socorro mecânico em na garagem" — a
#:    preposição que o modelo já escreveu sai antes de a linha pôr a dela.
_PREPOSICAO_INICIAL = re.compile(r"^(?:em|no|na|nos|nas|à|a|o|para|pra|até|ate|do|da|de)\s+", re.IGNORECASE)


def _lugar(valor: Any) -> str:
    return _PREPOSICAO_INICIAL.sub("", _PREPOSICAO_INICIAL.sub("", _limpo(valor)))   # "para a oficina"


def o_que_falta_para_a_linha(pedido: Optional[dict]) -> list:
    """O que o pedido ainda NÃO tem para virar a linha de confirmação. **PURA.**

    Sem o LOCAL não há o que confirmar (o resumo sem lugar é o pedido de ok de um guincho que
    não se sabe aonde vai); o GUINCHO leva o carro, então sem DESTINO também não."""
    p = pedido or {}
    falta = []
    if not _limpo(p.get("local_atual")):
        falta.append("o local onde está (rua e número, rodovia e km, ou um ponto de referência)")
    sub = str(p.get("subservice") or "").strip().lower()
    canon = ""
    if sub:
        try:
            from app.services.corridor_playbooks import canonical_subservice

            canon = canonical_subservice(sub) or sub
        except Exception:  # noqa: BLE001 — a linha nunca derruba o retorno
            canon = sub
    if canon == "guincho" and not _limpo(p.get("local_destino")):
        falta.append("para onde o carro vai (a oficina ou o endereço de destino)")
    return falta


def linha_de_confirmacao(pedido: Optional[dict], *, de_outra_pessoa: bool = False) -> str:
    """🔴 SPEC-126 U1 — a LINHA PRONTA do resumo, montada pelo CÓDIGO com os argumentos do
    pedido. **PURA.** `""` quando falta o que confirmar (`o_que_falta_para_a_linha`).

    📊 U0 da SPEC-126 (`reports/SPEC-126-LINHA-DE-BASE.md` §3): o C13 do Sol recebeu o
    `confirm_first` 2/2 com o texto "monte o resumo" e nenhuma linha montada — e numa das
    duas a conversa terminou com uma pessoa e nada acionado. A linha daqui é a pergunta que o
    PORTÃO (`confirmacao_comprovada`) aceita: o verbo forte ("posso acionar?") e o serviço, o
    lugar e o final da placa do PRÓPRIO pedido.
    ⛔ Nunca o CPF; a placa e o telefone só pelo FINAL (T19). Só entra o que o pedido tem —
    sem placa ou sem destino, a linha não inventa nem pergunta por eles.
    🔴 SPEC-126 U2-B (D1): `de_outra_pessoa` — quem fala é o PARENTE (a apólice é do titular,
    `policy_context.de_outra_pessoa`): a placa é dado da apólice e SAI da linha, nem o final."""
    p = pedido or {}
    if o_que_falta_para_a_linha(p):
        return ""
    sub = str(p.get("subservice") or "").strip().lower()
    try:
        from app.services.corridor_playbooks import canonical_subservice

        canon = canonical_subservice(sub) or sub
    except Exception:  # noqa: BLE001
        canon = sub
    servico = _NOME_DO_SERVICO_NA_LINHA.get(canon) or canon.replace("_", " ") or "assistência"
    local, destino = _lugar(p.get("local_atual")), _lugar(p.get("local_destino"))
    partes = [f"{servico} saindo de {local} até {destino}" if destino else f"{servico} em {local}"]
    placa = re.sub(r"[^A-Za-z0-9]", "", str(p.get("veiculo_placa") or "")).upper()
    if len(placa) >= 7 and not de_outra_pessoa:
        partes.append(f"placa final {placa[-4:]}")
    fone = _digitos(p.get("telefone_contato")) or telefone_da_conversa(p.get("session_id"))
    if len(fone) >= 8:
        partes.append(("contato neste número (final %s)"
                       if fone == telefone_da_conversa(p.get("session_id"))
                       else "contato no telefone final %s") % fone[-4:])
    return "Confirma: " + ", ".join(partes) + " — posso acionar?"


def instrucao_da_linha_pronta(pedido: Optional[dict], *, de_outra_pessoa: bool = False) -> str:
    """O trecho do `confirm_first` que entrega a linha ao modelo (ou diz o que falta). **PURA.**"""
    linha = linha_de_confirmacao(pedido, de_outra_pessoa=de_outra_pessoa)
    if linha:
        return ("LINHA PRONTA (montada pelo sistema com os dados deste pedido) — ENVIE ao cliente "
                f"exatamente esta linha, sem reescrever e sem perguntar de novo o que está nela: "
                f"{LINHA_PRONTA_ABRE}{linha}{LINHA_PRONTA_FECHA}. Antes dela cabe no máximo UMA frase "
                "curta (segurança ou acolhimento); nunca anuncie o acionamento antes do sim. ")
    falta = o_que_falta_para_a_linha(pedido) if pedido else []
    if falta:
        return ("Ainda falta " + " e ".join(falta) + ": pergunte SÓ isso, numa mensagem, e chame de "
                "novo — a ferramenta devolve a linha pronta do resumo. ")
    return ""


def com_a_linha_de_quem_fala(resposta: dict, pedido: Optional[dict], de_outra_pessoa: bool) -> dict:
    """🔴 SPEC-126 U2-B (D1) — o `confirm_first` do `_run` (síncrono, sem a ficha) com a linha de
    QUEM FALA: com o parente, a linha pronta sem a placa troca a do titular no campo e no texto.
    **PURA**; não muta o recebido. Sem a marca (ou sem linha), devolve como veio."""
    if not de_outra_pessoa or not isinstance(resposta, dict) or not resposta.get("linha_pronta"):
        return resposta
    antiga = str(resposta["linha_pronta"])
    nova = linha_de_confirmacao(pedido, de_outra_pessoa=True)
    return {**resposta, "linha_pronta": nova,
            "content": str(resposta.get("content") or "").replace(antiga, nova)}


#: 🔴 SPEC-126 §3.1 (1) — os BOTÕES de resposta rápida da confirmação: `(id, rótulo)`. DESLIGADOS:
#:    `interactive=False` em todo provedor até a prova em aparelho real (🧑 Founder). O toque chega
#:    ao turno como o TEXTO do rótulo (`evolution_inbound._text_from_message` → `rotulo or ident`) e
#:    passa pelo MESMO portão (regex E classificador) — o id não pula nada. "✏️ Corrigir algo" cai na
#:    objeção (`corrig\w*`) e nunca aciona.
BOTOES_DA_CONFIRMACAO = (("confirmacao_ok", "✅ Pode acionar"),
                         ("confirmacao_corrigir", "✏️ Corrigir algo"))


def pedido_de_confirmacao(motivo: str = "", *, ja_confirmou: bool = False,
                          pedido: Optional[dict] = None, de_outra_pessoa: bool = False) -> dict:
    """O retorno quando o acionamento ainda não tem o "sim" do segurado — a forma do
    `confirm_first` de sempre (o agente já sabe o que fazer com ele).

    🔴 SPEC-126 U1: com o `pedido` (os argumentos da chamada), o retorno traz a LINHA PRONTA
    do resumo (`linha_de_confirmacao`) e o texto manda ENVIÁ-LA — o modelo não monta mais o
    resumo sozinho. A linha vai também no campo `linha_pronta`."""
    linha = (linha_de_confirmacao(pedido, de_outra_pessoa=de_outra_pessoa)
             if (pedido and not ja_confirmou) else "")
    if ja_confirmou:
        texto = ("O cliente JÁ confirmou os dados na conversa — não pergunte de novo. Chame "
                 "esta ferramenta de novo AGORA, com os mesmos dados e dados_confirmados=true. "
                 "NADA foi acionado ainda: não diga ao cliente que foi.")
    else:
        texto = ("ANTES de acionar: a conversa ainda não tem o resumo DESTE pedido seguido do "
                 "\"sim\" do cliente. "
                 + (instrucao_da_linha_pronta(pedido, de_outra_pessoa=de_outra_pessoa) if pedido else "")
                 + REGRA_DO_RESUMO_DE_CONFIRMACAO + " Só depois do sim "
                 "chame de novo com dados_confirmados=true — no MESMO turno em que ele disser "
                 "sim. ATENÇÃO: NADA foi acionado ainda — é PROIBIDO dizer ao cliente que a "
                 "seguradora foi acionada/contatada.")
    return {"status": "confirm_first", "missing": [], "confirmacao_comprovada": False,
            "motivo_interno": motivo, "content": texto, "linha_pronta": linha}


def mesmo_servico(a: Any, b: Any) -> bool:
    """Os dois subserviços são O MESMO trabalho? (o canônico dos corredores; senão a família do
    nome). Vazio de um lado → `False`. **PURA.**"""
    a, b = str(a or "").strip().lower(), str(b or "").strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    try:
        from app.services.corridor_playbooks import canonical_subservice

        if (canonical_subservice(a) or a) == (canonical_subservice(b) or b):
            return True
    except Exception:  # noqa: BLE001 — a regra nunca derruba a ferramenta
        pass
    fa, fb = _familia_do_pedido({"subservice": a}), _familia_do_pedido({"subservice": b})
    return bool(fa) and fa == fb


def ja_acionado(pedido: Optional[dict], em: Any = None, *, de_outra_pessoa: bool = False) -> dict:
    """🔴 SPEC-126 CONSERTO Y (RT-B3) — o retorno IDEMPOTENTE: este serviço JÁ SAIU nesta conversa
    (a ficha durável diz quando) e não há pergunta + ok NOVOS depois dele. Nada é enviado, nada
    entra na fila. Se o cliente pedir, com todas as letras, um SEGUNDO serviço igual, o caminho é a
    linha pronta + um ok novo — a ferramenta só aciona de novo com os dois DEPOIS do primeiro."""
    from datetime import datetime, timezone

    servico = str((pedido or {}).get("subservice") or "este serviço").replace("_", " ")
    quando = ""
    instante = _instante(em)
    if instante is not None:
        minutos = max(0, int((datetime.now(timezone.utc) - instante).total_seconds() // 60))
        quando = (" há %d min" % minutos if minutos < 120 else
                  " há %d h" % (minutos // 60) if minutos < 48 * 60 else " há %d dias" % (minutos // 1440))
    linha = linha_de_confirmacao(pedido, de_outra_pessoa=de_outra_pessoa) if pedido else ""
    texto = ("[JÁ PEDIDO NESTA CONVERSA — NADA FOI ENVIADO DE NOVO] O pedido de %s desta conversa já "
             "foi para a seguradora%s. NÃO chame esta ferramenta de novo para ele e NÃO peça outra "
             "confirmação: diga ao cliente que o pedido já está com a seguradora e que você avisa "
             "quando o protocolo/previsão chegar. Só se o cliente pedir, com todas as letras, um "
             "SEGUNDO %s (outro problema, outro lugar, outro veículo), mande o resumo novo e espere "
             "um novo \"sim\"%s." % (servico, quando, servico,
                                     (": \"%s\"" % linha) if linha else ""))
    return {"status": "already_dispatched", "missing": [], "confirmacao_comprovada": False,
            "content": texto, "linha_pronta": linha}


class InsurerDispatchTool(BaseTool):
    name: str = "insurer_dispatch"
    description: str = (
        "Prepara/aciona a assistência na seguradora pelo WhatsApp quando o levantamento estiver completo E a "
        "apólice tiver assistência confirmada. Cobre AUTO (guincho/bateria/pneu/chaveiro) e residencial "
        "(eletricista/chaveiro/encanador/eletrodomésticos). Para AUTO informe insurer_key (da InfoCap) e "
        "line_kind='auto'. Retorna o plano do acionamento ou os dados que ainda faltam. NUNCA diga ao cliente "
        "que acionou se o retorno indicar simulação/teste. Em modo TESTE o fluxo é executado por completo e "
        "CANCELADO na confirmação final (nada é aberto); corredor validado em modo LIVE completa ponta a ponta. "
        # ══════════════════════════════════════════════════════════════════
        # 🔴 SPEC-118 F3 · O QUE VEM PELA FRENTE SE PERGUNTA NA CONVERSA
        # ══════════════════════════════════════════════════════════════════
        #
        # Cada seguradora pede coisas diferentes, e algumas pedem por FORMULÁRIO
        # (o aplicativo que abre dentro da conversa do WhatsApp) — endereço
        # quebrado em rua, número, bairro, cidade, estado, CEP; em que nível da
        # rua o carro está. 📊 Esses campos só passaram a ser cobrados ANTES do
        # acionamento na SPEC-118; até então a sessão nascia pronta e o caso
        # morria no último portão, com a URA já rodando.
        #
        # ⚠️ A descrição não LISTA os campos de cada seguradora de propósito:
        # lista escrita aqui envelhece calada (CLAUDE.md §9.3) e são 73 rotas. A
        # lista certa, por seguradora e por serviço, é a que a própria ferramenta
        # devolve — em português, na hora, lida do corredor.
        "🔴 CHAME ESTA FERRAMENTA CEDO, ainda durante o levantamento, mesmo sem "
        "tudo em mãos: cada seguradora pede um conjunto diferente de dados, e "
        "algumas pedem por FORMULÁRIO dentro da conversa do WhatsApp (endereço "
        "em rua/número/bairro/cidade/estado/CEP, por exemplo). O retorno "
        "`missing_data` traz, em português, exatamente o que ESTA seguradora vai "
        # 🔴 SPEC-125 D3 · T11 — era "UMA informação por vez" (SPEC-118, 26/09),
        #    contra "bloco de até 4" no prompt e "de uma vez só, até 12" na
        #    conduta. A regra de como perguntar é UMA, e mora no prompt; aqui
        #    fica a parte que só a ferramenta sabe: veja antes se já foi dito.
        "pedir NESTE serviço — antes de perguntar, veja se a conversa, a ficha ou "
        "a apólice já respondem; pergunte ao cliente só o que a conversa ainda não "
        "respondeu (o que for independente vai junto, numa mensagem) e chame de "
        "novo. NÃO invente o que falta e NÃO "
        "pergunte coordenada, latitude ou longitude a ninguém. "
        # 🔴 O pin resolve com um toque o que seis perguntas não resolvem — e o
        #    produto JÁ lê o `locationMessage` do WhatsApp (evolution_inbound.py).
        "Quando a seguradora precisar do LOCAL EXATO, peça o PIN DE LOCALIZAÇÃO: "
        "'toque no clipe 📎, escolha Localização e me envie'. O que o cliente "
        "mandar chega na conversa como 'Localização compartilhada: <lat>,<lon>' — "
        "passe os dois números em `local_latitude` e `local_longitude`, "
        "exatamente como vieram, e nunca zero."
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
        from app.services.corridor_playbooks import (
            canonical_subservice as _canon, linha_do_subservico as _linha)

        line = str(kwargs.get("line_kind") or "").strip().lower()
        subservice = _canon(kwargs.get("subservice") or "")
        if not line:
            # ══════════════════════════════════════════════════════════════
            # 🔴 SPEC-084.2 C3 · AQUI HAVIA UMA LISTA ESCRITA À MÃO
            # ══════════════════════════════════════════════════════════════
            #
            # `("guincho","bateria","pneu","pane_seca","vidros")` decidia a
            # linha. Ela não conhecia `socorro_mecanico`, `tecnico`,
            # `bateria_nova` nem `taxi` — quatro subserviços de auto que
            # nasceram depois dela. Conhecia `pane_seca`, que é APELIDO e não
            # é rota. E comparava a string CRUA, então 📊 **26 apelidos**
            # (`reboque`, `pane`, `parabrisa`, `carro nao liga`…) também não
            # eram reconhecidos.
            #
            # 🔴 O estrago medido: **5 rotas resolviam o corredor da linha
            #    ERRADA**, duas delas AAA. `socorro_mecanico` na HDI ia para o
            #    corredor RESIDENCIAL, e o produto respondia *"a hdi não atende
            #    'socorro_mecanico' por este canal"* — falso, sobre uma rota
            #    86/88.
            #
            # ⚠️ E `chave` era o pior caso: apelido de `chaveiro`, ele deveria
            #    cair no ramo do handoff logo abaixo — e como AQUELE ramo
            #    também comparava a string crua, o guarda do chaveiro era
            #    CONTORNADO. O incidente que o comentário antigo dizia estar
            #    impedindo acontecia por baixo dele.
            #
            # 🔴 `linha_do_subservico` DERIVA a resposta dos playbooks, que já
            #    declaram `line_kind` e `subservices`. Não há segunda lista
            #    para divergir da primeira.
            line, ambiguo = _linha(subservice)
            if ambiguo:
                # O trabalho existe nas DUAS linhas — 📊 hoje só `chaveiro`:
                # chaveiro do carro e chaveiro da casa. Ambíguo não se deduz,
                # pergunta-se, e a pergunta é `line_kind`. Um chaveiro de CARRO
                # mandado ao menu residencial pediria o número da casa a quem
                # está parado no acostamento.
                #
                # 📊 CONTROLE do conserto: as 14 rotas de chaveiro continuam
                #    caindo aqui — nem uma a mais, nem uma a menos.
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
        # 🔴 O ramo viaja como FAMÍLIA (`resi`/`cond`/`empr`), pela autoridade do
        #    produto. O que não se reconhece não vira tecla: sai do caso, e a tela
        #    vai a uma pessoa em vez de receber um chute.
        if "ramo_da_apolice" in slots:
            from app.providers.policy_data_provider import familia_de_ramo

            familia = familia_de_ramo(slots["ramo_da_apolice"])
            if familia:
                slots["ramo_da_apolice"] = familia
            else:
                slots.pop("ramo_da_apolice")
        # 🔴 A COORDENADA SE NORMALIZA AQUI, E NÃO NO `_run` — SPEC-118 F3.
        #
        # ⚠️ `_arun` (o caminho LIVE, que cria a sessão de verdade) chama
        # `_extract_slots` **de novo**, com os kwargs crus: normalizar só no `_run`
        # deixaria o caminho real com o valor como o modelo escreveu. Aqui vale
        # para os dois, e é o mesmo par que o guarda do `_run` recusa quando não
        # fecha — uma regra, dois consumidores.
        if "local_latitude" in slots or "local_longitude" in slots:
            par = par_de_coordenadas(slots.get("local_latitude"),
                                     slots.get("local_longitude"))
            if par:
                slots["local_latitude"], slots["local_longitude"] = par
            else:
                slots.pop("local_latitude", None)
                slots.pop("local_longitude", None)
        return subservice, slots

    def _run(self, **kwargs) -> dict:
        """Valida e monta o plano. NUNCA envia nada — o envio real (gate aberto)
        acontece só no _arun. Honestidade: sem envio, sem alegar acionamento."""
        kwargs.pop("slots_deduzidos", None)   # SPEC-126 U5: só o diário lê (nodes.deducoes_do_turno)
        from app.services.corridor_playbooks import SUBSERVICO_INVALIDO
        from app.services.insurer_dispatch_service import build_dry_run_plan

        kwargs = com_o_telefone_da_conversa(kwargs)   # 🔴 Z2: o telefone desta conversa
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
                f"'sem corredor para {quem}'. "
                # 🔴 SPEC-085, painel: NÃO prometa a pessoa ANTES da ferramenta.
                # A instrução antiga mandava dizer "um atendente da corretora vai
                # assumir" — sem consultar destino de suporte, e ANTES de o
                # handoff ter dado certo. É a promessa de agosto com outra roupa,
                # e o fiscal não a pegava (o regex exigia sujeito e verbo que
                # esta frase não tem; corrigido no mesmo painel).
                # Quem autoriza a frase é o CARIMBO que a ferramenta devolve.
                "Diga ao cliente SÓ o que a ferramenta devolver: com HANDOFF_OK, "
                "que a equipe foi avisada; sem ele, que o pedido ficou registrado "
                "e você segue com ele. Nunca prometa uma pessoa antes do carimbo. "
                "Os dados que ele já deu ficam registrados de qualquer forma.")}

        # GUARDA ANTI-INVENÇÃO (incidente 2026-07-10: placa e telefone inventados
        # foram parar na seguradora). Determinístico, fora do alcance do LLM.
        #
        # 📊 03/08/2026: o comentário citava PLACA e o código conferia SÓ telefone.
        # `placa='1'` e `placa='nao sei'` chegavam a `ready_to_send` — a placa
        # errada abre chamado para o carro de outra pessoa. E o guarda de telefone
        # (`(\d)\1{4,}`) reprovava `48999990000`, que é um celular REAL de
        # Florianópolis e é o `CASO_COMPLETO` dos testes deste próprio repositório.
        # Guarda que reprova o verdadeiro ensina a desligar o guarda.
        #
        # 🔴 E OS SEIS CAMPOS DE ENDEREÇO ENTRARAM NA LISTA — 26/09/2026.
        #
        # 📊 Medido no montador real, antes deste conserto: `estado="ZZ"`,
        # `cep="0"`, `numero_residencia="nao sei"`, `cidade="48.5477"` e uma rua
        # com uma QUEBRA DE LINHA dentro fechavam o formulário da Porto com
        # `ok=True` e viajavam
        # para a seguradora. O único caso que travava era o campo VAZIO — ou
        # seja: conferia-se a AUSÊNCIA do valor, nunca o valor.
        #
        # ⚠️ A frase de cada um ensina o agente a DESCOBRIR o dado, nunca a
        # adivinhá-lo — é a mesma forma dos três de cima, e é o que separa esta
        # guarda de um "tente de novo".
        # 🔴 SPEC-121 F4b/F5 — o que vai a uma PESSOA antes de o corredor abrir
        #    (portão ≠ eletricista, raio = sinistro, carro reserva sem nº/cartão/horário/
        #    canal, seguradora sem caminho). Um lugar só: `antes_de_acionar`.
        # 🔴 CONSERTO ÚNICO (red team B1) — o motivo vai com o CÓDIGO na frente
        #    (`motivo_com_codigo`), e o handoff lê o código (`ler_codigo_antes_de_acionar`)
        #    em vez de reclassificar a frase por palavra. `tipo_do_aviso` e `reason`
        #    também saem no retorno, para quem lê a ferramenta sem o modelo no meio.
        from app.services.corridor_playbooks import (
            CODIGOS_ANTES_DE_ACIONAR, antes_de_acionar, motivo_com_codigo,
        )
        _pessoa = antes_de_acionar(playbook_ref, subservice, slots)
        if _pessoa:
            _reason = motivo_com_codigo(_pessoa)
            return {"status": "pessoa_antes_de_acionar", "handoff_necessario": True,
                    "codigo": _pessoa["codigo"],
                    "tipo_do_aviso": CODIGOS_ANTES_DE_ACIONAR.get(_pessoa["codigo"],
                                                                  "pedido_de_ajuda"),
                    "reason": _reason, "missing": [], "content": (
                        "NÃO acione a seguradora. Chame `request_human_agent` agora, com o "
                        f"`reason` EXATAMENTE assim, inteiro e com a marca entre colchetes: "
                        f"'{_reason}', e `codigo`='{_pessoa['codigo']}'. Ao segurado, diga com as suas "
                        f"palavras: \"{_pessoa['ao_segurado']}\" — e, sem o carimbo "
                        "HANDOFF_OK, diga só que o pedido ficou registrado. Nunca prometa "
                        "carro, prazo, diárias ou protocolo.")}

        is_auto = "auto" in str(playbook_ref)
        for campo, valor, ok, comojá in (
            ("telefone_contato", kwargs.get("telefone_contato"), telefone_br_valido,
             "o telefone REAL de quem estará com o veículo (com DDD)"),
            ("veiculo_placa", kwargs.get("veiculo_placa"), placa_br_valida,
             "a placa REAL do veículo (formato ABC1D23 ou ABC1234) — confirme na apólice, "
             "na InfoCap ou com o cliente"),
            ("titular_cpf", kwargs.get("titular_cpf"), documento_br_valido,
             "o CPF (ou CNPJ) REAL do titular da apólice"),
            ("local_uf", kwargs.get("local_uf"),
             lambda v: valor_de_slot_honesto("local_uf", v) is not None,
             "a sigla de DUAS LETRAS do estado onde o veículo está (SC, SP, RS…) — "
             "se você não tem certeza, NÃO escreva nada neste campo"),
            ("local_cep", kwargs.get("local_cep"),
             lambda v: valor_de_slot_honesto("local_cep", v) is not None,
             "o CEP com OITO dígitos (00000-000) do lugar onde o veículo está — "
             "peça ao cliente ou deixe o campo vazio"),
            ("local_numero", kwargs.get("local_numero"),
             lambda v: valor_de_slot_honesto("local_numero", v) is not None,
             "o NÚMERO do imóvel (só dígitos, ou 's/n' quando não há número) — "
             "'nao sei' não é um número, e a seguradora o aceitaria calada"),
            ("local_rua", kwargs.get("local_rua"),
             lambda v: valor_de_slot_honesto("local_rua", v) is not None,
             "o nome da RUA onde o veículo está, numa linha só"),
            ("local_bairro", kwargs.get("local_bairro"),
             lambda v: valor_de_slot_honesto("local_bairro", v) is not None,
             "o nome do BAIRRO onde o veículo está, numa linha só"),
            ("local_cidade", kwargs.get("local_cidade"),
             lambda v: valor_de_slot_honesto("local_cidade", v) is not None,
             "o nome da CIDADE onde o veículo está — um número não é uma cidade"),
        ):
            if str(valor or "").strip() and not ok(valor):
                return {"status": "missing_data", "missing": [campo], "content": (
                    f"O valor informado em `{campo}` não é válido — não passa na conferência "
                    "determinística de formato. NÃO envie isso à seguradora e NÃO tente adivinhar: "
                    f"descubra {comojá}. Se o cliente não souber, chame `request_human_agent`.")}

        # ══════════════════════════════════════════════════════════════════
        # 🔴 A COORDENADA É PAR, OU NÃO É — SPEC-118 F3
        # ══════════════════════════════════════════════════════════════════
        #
        # ⛔ Zero é o Golfo da Guiné, meio par não localiza nada, e coordenada
        # deduzida de endereço é invenção com cara de precisão. Os três saem
        # daqui com a frase que manda pedir o PIN — a pergunta que o segurado
        # responde com um toque.
        _bruto_lat = str(kwargs.get("local_latitude") or "").strip()
        _bruto_lon = str(kwargs.get("local_longitude") or "").strip()
        if _bruto_lat or _bruto_lon:
            _par = par_de_coordenadas(_bruto_lat, _bruto_lon)
            if not _par:
                slots.pop("local_latitude", None)
                slots.pop("local_longitude", None)
                return {"status": "missing_data",
                        "missing": ["local_latitude", "local_longitude"],
                        "content": (
                            "A localização exata que você passou não é um par de coordenadas "
                            "honesto (ou falta uma das duas, ou está fora da faixa, ou é zero — "
                            "e zero fica no meio do oceano). NÃO tente adivinhar a coordenada a "
                            "partir do endereço. PEÇA O PIN ao cliente, com estas palavras: "
                            "'para o guincho te achar rápido, toque no clipe 📎 aqui no WhatsApp, "
                            "escolha Localização e me envie'. Quando ele enviar, use os dois "
                            "números da linha 'Localização compartilhada' exatamente como vieram.")}
            slots["local_latitude"], slots["local_longitude"] = _par
        if is_auto and not kwargs.get("dados_confirmados"):
            placa = str(kwargs.get("veiculo_placa") or "—")
            # ══════════════════════════════════════════════════════════════
            # 🔴 SPEC-118 F3 · A CONFIRMAÇÃO DEIXA DE ESCONDER O QUE FALTA
            # ══════════════════════════════════════════════════════════════
            #
            # 📊 Este ramo devolve ANTES de `build_dry_run_plan` — então, em AUTO,
            # a PRIMEIRA chamada sempre diz "confirme com o cliente", mesmo quando
            # ainda faltam seis dados. O agente confirma, chama de novo, e só aí
            # descobre o que falta: o segurado é interrompido **duas vezes**, e a
            # segunda depois de ter dito "sim, pode acionar".
            #
            # ⚠️ A ORDEM NÃO MUDA (a confirmação é o ponto irreversível e continua
            # sendo a próxima coisa a fazer). O que muda é que a mesma mensagem já
            # carrega o que ainda vai ser pedido — quem pergunta é o mesmo turno
            # de conversa. 🔴 E quem responde "o que falta" é o MOTOR
            # (`missing_slots_for_subservice`, via o mesmo tradutor da coleta):
            # esta linha não recalcula nada.
            _falta: list = []
            _ainda: list = []
            try:
                from app.services.corridor_playbooks import (
                    SUBSERVICO_INVALIDO as _SI, missing_slots_for_subservice)
                from app.services.insurer_dispatch_service import (
                    como_pedir_ao_segurado)
                _falta = list(missing_slots_for_subservice(
                    playbook_ref, subservice, slots) or [])
                if _SI in _falta:
                    _falta = []   # não falta dado, falta caminho — o ramo lá embaixo trata
                _ainda = como_pedir_ao_segurado(playbook_ref, _falta)
            except Exception:  # noqa: BLE001 — a confirmação nunca cai por causa do aviso
                _falta, _ainda = [], []
            _e_falta = (
                " E ainda FALTAM estes dados, que esta seguradora vai pedir: "
                + "; ".join(_ainda)
                + ". Colete-os no MESMO turno da confirmação — só o que a conversa "
                  "ainda não respondeu, juntos na mesma mensagem — e não invente "
                  "nenhum deles."
            ) if _ainda else ""
            # 🔴 Z2 — o que JÁ se sabe vai no resumo (com o valor), e não vira pergunta.
            _sabido = "; ".join(x for x in (
                f"placa {placa}" if placa != "—" else "",
                f"local: {kwargs.get('local_atual')}" if str(kwargs.get("local_atual") or "").strip() else "",
                f"destino: {kwargs.get('local_destino')}" if str(kwargs.get("local_destino") or "").strip() else "",
                (("contato: o telefone desta conversa (final %s)"
                  if _digitos(kwargs.get("telefone_contato")) == telefone_da_conversa(kwargs.get("session_id"))
                  else "contato: o telefone final %s")
                 % _digitos(kwargs.get("telefone_contato"))[-4:])
                if str(kwargs.get("telefone_contato") or "").strip() else "",
            ) if x)
            # 🔴 SPEC-126 U1 — a LINHA PRONTA vem montada pelo código (o elo do C13); sem o
            #    que confirmar (local/destino), o texto diz o que falta perguntar.
            return {"status": "confirm_first", "missing": _falta,
                    "linha_pronta": linha_de_confirmacao(kwargs), "content": (
                "ANTES de acionar, confirme com o cliente NA CONVERSA. "
                + instrucao_da_linha_pronta(kwargs)
                + (f"O que JÁ se sabe (vai no resumo, não vira pergunta): {_sabido}. " if _sabido else "")
                + REGRA_DO_RESUMO_DE_CONFIRMACAO + " Depois chame de novo com "
                "dados_confirmados=true. ATENÇÃO: NADA foi acionado ainda — é PROIBIDO dizer ao cliente "
                "que a seguradora foi acionada/contatada. Só afirme acionamento quando ESTA ferramenta "
                "retornar status 'dispatched'. Assim que o cliente confirmar, chame de novo IMEDIATAMENTE "
                "(na mesma resposta), não deixe para depois." + _e_falta)}

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
                            # 🔴 SPEC-084.2, JUIZ 1 · "a seguradora nao atende X" e uma afirmacao
                            #    sobre a APOLICE DE TERCEIRO, e o produto nao sabe
                            #    isso. 📊 Medido: a Azul lista "Taxi" em SETE telas do
                            #    acervo e `subservice_supported` diz False -- porque
                            #    NAO TEMOS CORREDOR MAPEADO, que e outra coisa. A
                            #    primeira frase e verdade sobre o produto; a segunda e
                            #    falsa sobre a seguradora.
                            f"Não temos corredor mapeado para '{trabalho}' na {quem} — "
                            "e sinistro (colisão, roubo, incêndio) NUNCA se abre por aqui. "
                            "NÃO peça mais nenhum dado ao cliente por causa disto: não falta dado, "
                            "falta caminho. NÃO tente acionar por outro corredor e NÃO invente protocolo. "
                            "Chame `request_human_agent` agora, com o motivo "
                            f"'{quem} não tem corredor para {trabalho}'. "
                            # 🔴 SPEC-085, painel — mesma correção do ramo acima.
                            "Diga ao cliente SÓ o que a ferramenta devolver: com "
                            "HANDOFF_OK, que a equipe foi avisada; sem ele, que o "
                            "pedido ficou registrado e você segue com ele. Nunca "
                            "prometa uma pessoa antes do carimbo. O que ele já "
                            "contou fica registrado de qualquer forma.")}
            if plan.get("missing_slots"):
                # ══════════════════════════════════════════════════════════
                # 🔴 SPEC-084.2 C5 · AQUI HAVIA UMA SEGUNDA FONTE DE VERDADE
                # ══════════════════════════════════════════════════════════
                #
                # Um dicionário `friendly` escrito à mão traduzia os slots que
                # faltam para português. 📊 Medido em 23/08/2026: **14 chaves
                # aqui contra 58 em `_COMO_PERGUNTAR`**, e `friendly.get(s, s)`
                # devolvia a CHAVE CRUA para 40 dos slots que o portão cobra.
                #
                # 🔴 O que a atendente lia, numa rota de máquina de lavar:
                #    *"Ainda faltam estes dados: número da residência; telefone
                #    de contato; descrição do problema; aparelho_marca;
                #    aparelho_modelo; período preferido; idade_aparelho_opcao."*
                #    Três identificadores no meio de uma frase em português —
                #    e é esse texto que ela repete ao cliente.
                #
                # ⚠️ Uma fonte só: mudou o corredor, mudou o que a ferramenta
                #    diz, no mesmo commit. `_COMO_PERGUNTAR` é onde o produto
                #    já escreve como se pergunta cada coisa.
                #
                # ══════════════════════════════════════════════════════════
                # 🔴 SPEC-118 F3 · E O `else` DAQUELA LINHA AINDA VAZAVA CHAVE
                # ══════════════════════════════════════════════════════════
                #
                # Era `_COMO_PERGUNTAR.get(s, s.replace("_", " "))`. O fallback
                # não é chave crua, é chave com o `_` trocado por espaço — e para
                # os campos do FORMULÁRIO nativo, que a F2b passou a cobrar, é o
                # único ramo que roda: 📊 medido em 26/09/2026 no caminho da Porto
                # com o endereço sem número, `_run` devolvia literalmente
                # *"Ainda faltam estes dados para acionar: local numero; local
                # bairro."* — o defeito de 23/08 com roupa nova.
                #
                # 🔴 `como_pedir_ao_segurado` é o tradutor único: tenta o
                #    vocabulário do produto, depois o RÓTULO QUE A SEGURADORA USA
                #    na tela do formulário (lido pelo motor, nunca escrito à mão)
                #    e, por último, a peneira que nunca devolve `_`.
                from app.services.insurer_dispatch_service import (
                    como_pedir_ao_segurado)
                faltam = como_pedir_ao_segurado(playbook_ref, plan["missing_slots"])

                # 🔴 JUIZ 4 · VALOR RECUSADO NÃO É DADO AUSENTE.
                #
                #    O portão passou a conferir o VALOR em campo de escolha
                #    fechada. Mas a mensagem era a mesma dos dois casos, e ela
                #    diz *"pergunte SOMENTE o que nunca foi informado"* — e o
                #    dado FOI informado. 📊 O resultado é um laço fechado: o
                #    portão bloqueia, o texto não diz por quê, o atendente
                #    reenvia o mesmo valor, o portão bloqueia de novo — com o
                #    segurado esperando.
                #
                # ⚠️ Quando a seguradora publicou a lista de opções, o produto
                #    tem como dizer QUAIS são. Dizer é o conserto.
                _opcoes_de = _opcoes_recusadas(playbook_ref, subservice,
                                               kwargs, plan["missing_slots"])
                if _opcoes_de:
                    # 🔴 SPEC-118 F3 · A PERGUNTA É A DA TELA, NÃO O NOME DO SLOT.
                    #
                    #    Aqui saía `veiculo_nivel_rua: Subsolo | Acima do nível
                    #    da rua | …` — o nome interno do campo colado nos títulos
                    #    da seguradora. Quem lê é o agente, que vai perguntar ao
                    #    segurado: ⚠️ ele precisa da PERGUNTA da tela (*"Em
                    #    relação ao nível da rua, onde o veículo está?"*), que
                    #    está no mesmo schema de onde os títulos saíram.
                    from app.services.corridor_playbooks import _COMO_PERGUNTAR
                    from app.services.insurer_dispatch_service import (
                        rotulos_do_formulario_por_slot)
                    _rotulos = rotulos_do_formulario_por_slot(playbook_ref)
                    return {
                        "status": "missing_data",
                        "missing": list(_opcoes_de),
                        "content": (
                            "O valor informado não é uma das opções que a "
                            "seguradora aceita nesta tela. Use EXATAMENTE uma "
                            "destas: "
                            + " · ".join(
                                f"{_rotulos.get(c) or _COMO_PERGUNTAR.get(c) or c}: "
                                f"{' | '.join(v)}"
                                for c, v in _opcoes_de.items())
                            + ". NÃO invente outra redação — a URA só aceita a "
                            "opção literal. E NÃO escolha por ele quando a opção "
                            "mudar o serviço que vem: pergunte ao cliente com as "
                            "palavras da tela e use a resposta dele."),
                    }
                return {
                    "status": "missing_data",
                    "missing": plan["missing_slots"],
                    "content": (
                        # 🔴 SPEC-118 F3 · O QUE MUDOU NESTA FRASE, E POR QUÊ.
                        #
                        #    `faltam` agora é português de gente até para os
                        #    campos do formulário nativo, e a frase diz de ONDE
                        #    vem a exigência — *"a seguradora abre um formulário
                        #    dentro da conversa e ele pede isto"*. 📊 Sem essa
                        #    metade, o agente recebia uma lista de campos de
                        #    endereço sem entender por que o CEP virou
                        #    obrigatório numa seguradora e não na outra, e o
                        #    caminho fácil dele é inventar ou desistir.
                        "Ainda faltam estes dados para acionar, na ordem em que "
                        "esta seguradora pede: " + "; ".join(faltam) + ". "
                        "ANTES de perguntar ao cliente, PROCURE cada um na CONVERSA e na sua ficha "
                        "(CPF, endereço e telefone quase sempre JÁ foram ditos) e chame de novo com eles. "
                        # 🔴 SPEC-125 D3 · T11 — era "um de cada vez … UMA informação
                        #    por vez, nunca a lista inteira", contra o "bloco de até 4"
                        #    do prompt e o "de uma vez só" da conduta. A LIÇÃO do
                        #    GOLD-ELEC-005 (não interrogar) migra e fica guardada: o
                        #    guarda agora afirma "SOMENTE o que nunca foi informado" e
                        #    "nunca um interrogatório" (CLAUDE.md §9.3).
                        "Pergunte ao cliente SOMENTE o que nunca foi informado, com naturalidade — "
                        "o que for independente vai junto numa mensagem, o que depende de outra "
                        "resposta vem depois; nunca um interrogatório — e chame de novo assim que "
                        "ele responder. "
                        "Parte desta lista é o que a seguradora vai pedir num FORMULÁRIO dentro da "
                        "conversa dela (por isso ela quer o endereço quebrado em rua, número, bairro, "
                        "cidade, estado e CEP): coletar agora evita parar no meio do acionamento, com "
                        "o cliente esperando. NÃO invente nenhum destes valores."
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
        # 📊 SPEC-084.2 C3 — era `("guincho","bateria","pneu")`, TERCEIRA
        # cópia da mesma lista, e esta decide se o produto busca placa, veículo
        # e titular na InfoCap. Medido: sem `line_kind`,
        # `zurich/socorro_mecanico`, `azul/tecnico`, `porto/vidros` e
        # `zurich/vidros` NÃO buscavam a placa — e chegavam a `ready_to_send`
        # assim mesmo, com o atendente empurrado a pedir a placa ao segurado.
        # 🔴 É literalmente o incidente de 11/07/2026 que o docstring desta
        #    função descreve, de volta por uma lista desatualizada.
        from app.services.corridor_playbooks import linha_do_subservico as _linha_ic
        is_auto = (
            str(kwargs.get("line_kind") or "").lower() == "auto"
            or _linha_ic(kwargs.get("subservice"))[0] == "auto"
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
            # 🔴 SPEC-EXTRA-001.1 §5.1.1: `hasattr` nao e contrato — o registry e.
            if provider is None or not key:
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

    async def _apolice_de_outra_pessoa(self, kwargs: dict) -> bool:
        """🔴 SPEC-126 U2-B (D1) — quem fala é o PARENTE (a apólice do caso é do titular)?

        A marca é a da U3-B (`policy_context.de_outra_pessoa`), lida da ficha DURÁVEL desta
        conversa (`attendance_ficha.carregar`, com a corretora no filtro) pela leitura única
        `attendance_ficha.apolice_de_outra_pessoa`. Sem banco, sem sessão ou leitura falha →
        `False` (o mesmo padrão do leitor da U3-B: quem corta o DADO é a consulta). **Nunca levanta.**"""
        client = getattr(self.supabase_client, "client", self.supabase_client)
        sessao = str((kwargs or {}).get("session_id") or "")
        if client is None or not sessao:
            return False
        try:
            from app.services.attendance_ficha import apolice_de_outra_pessoa, carregar

            return bool(apolice_de_outra_pessoa(ficha=await carregar(client, self.company_id, sessao)))
        except Exception as erro:  # noqa: BLE001
            logger.warning("[InsurerDispatch] marca de terceiro não lida (%s)", type(erro).__name__)
            return False

    async def _prova_da_confirmacao(self, kwargs: dict, acionado_em: Any = None) -> dict:
        """A prova do "sim" nesta conversa — `company_id` da ferramenta, `session_id`
        do ESTADO (injetado pelo `tool_node`; nunca da LLM)."""
        client = getattr(self.supabase_client, "client", self.supabase_client)
        if client is None:
            return {"comprovada": False, "motivo": "sem banco"}
        return await prova_da_confirmacao(client, company_id=self.company_id,
                                          session_id=str(kwargs.get("session_id") or ""),
                                          pedido=kwargs, acionado_em=acionado_em)

    async def _acionamento_desta_conversa(self, kwargs: dict) -> Optional[dict]:
        """🔴 SPEC-126 CONSERTO Y (RT-B3) — o último acionamento que SAIU (ou entrou na fila) desta
        conversa, lido do estado DURÁVEL: a ficha (`attendance_ficha.carregar`, corretora no filtro),
        `acionamento.enviado_em`/`enfileirado_em` + `servico`. `{"em": datetime, "servico": str}` ou
        `None`. Nunca a memória do processo, nunca a prosa do modelo. **Nunca levanta.**"""
        client = getattr(self.supabase_client, "client", self.supabase_client)
        sessao = str((kwargs or {}).get("session_id") or "")
        if client is None or not sessao:
            return None
        try:
            from app.services.attendance_ficha import carregar

            acion = (await carregar(client, self.company_id, sessao)).get("acionamento") or {}
        except Exception as erro:  # noqa: BLE001
            logger.warning("[InsurerDispatch] acionamento anterior não lido (%s)", type(erro).__name__)
            return None
        if not isinstance(acion, dict):
            return None
        instantes = [i for i in (_instante(acion.get("enviado_em")), _instante(acion.get("enfileirado_em")))
                     if i is not None]
        if not instantes:
            return None
        return {"em": max(instantes), "servico": str(acion.get("servico") or "")}

    async def _marcar_o_acionamento(self, kwargs: dict, chave: str, subservice: str,
                                    insurer_key: str) -> None:
        """🔴 SPEC-126 CONSERTO Y (RT-B3 · juiz pendência 1) — o FATO vai para a ficha DURÁVEL no
        instante em que o efeito aconteceu, pelo escritor ÚNICO (`attendance_ficha.gravar` →
        `fundir`, aditivo): `acionamento.enviado_em` (saiu) ou `enfileirado_em` (fila da seguradora),
        com o serviço e a seguradora. É ele que gasta a confirmação (`confirmacao_comprovada`), que
        torna a 2ª chamada idempotente e que faz a R9/`_e_pos_acionamento` reconhecer o caso acionado
        ANTES do protocolo. Escrito AQUI, ao lado do efeito, vale para todo chamador (o `tool_node`, a
        mesma mensagem reprocessada, duas chamadas no mesmo turno). **Nunca levanta.**"""
        client = getattr(self.supabase_client, "client", self.supabase_client)
        sessao = str((kwargs or {}).get("session_id") or "")
        if client is None or not sessao:
            return
        try:
            from datetime import datetime, timezone

            from app.services.attendance_ficha import gravar

            await gravar(client, self.company_id, sessao, {"acionamento": {
                chave: datetime.now(timezone.utc).isoformat(),
                "servico": str(subservice or ""), "seguradora": str(insurer_key or "")}})
        except Exception as erro:  # noqa: BLE001 — o efeito já aconteceu; a marca nunca o desfaz
            logger.error("[InsurerDispatch] acionamento NÃO marcado na ficha (%s)", type(erro).__name__)

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

        kwargs = dict(kwargs)
        kwargs.pop("slots_deduzidos", None)   # SPEC-126 U5: só o diário lê (nodes.deducoes_do_turno)
        kwargs = com_o_telefone_da_conversa(await self._resolve_vehicle_facts(kwargs))
        # 🔴 SPEC-126 U2-B (D1): com o PARENTE falando, a linha pronta sai sem a placa e o texto do
        #    acionamento sem o nome da seguradora (dados da apólice do titular)
        de_outra_pessoa = await self._apolice_de_outra_pessoa(kwargs)
        base = com_a_linha_de_quem_fala(self._run(**kwargs), kwargs, de_outra_pessoa)
        if base.get("status") != "ready_to_send" or not dispatch_live_enabled():
            return base
        if not await self._acionamento_liberado():
            # Nada sai. O conteúdo devolvido é o MESMO plano em simulação que a
            # tool sempre devolveu com o gate fechado — o agente desligado não
            # muda o texto, muda o mundo: nenhuma mensagem chega à seguradora.
            logger.info("[InsurerDispatch] agente de atendimento desligado (ou freio "
                        "armado) — plano preparado, NADA enviado")
            return base

        # 🔴 SPEC-125 Y1 (juiz B1) — o último portão antes de SAIR DO PRÉDIO: a
        #    afirmação do modelo (`dados_confirmados`) E a prova na conversa (a pergunta
        #    de confirmação num turno anterior + o "sim" do segurado depois dela).
        # 🔴 SPEC-126 U2 (parte B) — a prova é a do PORTÃO: regex E classificador, UMA chamada
        #    de modelo por tentativa de acionamento (só quando a regex já disse sim).
        # 🔴 SPEC-126 CONSERTO Y (RT-B3) — o acionamento que JÁ SAIU desta conversa (estado durável)
        #    gasta a confirmação que veio antes dele; o MESMO serviço sem pergunta e ok NOVOS devolve
        #    "já acionado" (nada sai, nada entra na fila) — nunca um 2º guincho com o mesmo "sim".
        anterior = await self._acionamento_desta_conversa(kwargs)
        if anterior is not None:
            prova = await self._prova_da_confirmacao(kwargs, acionado_em=anterior["em"])
        else:
            prova = await self._prova_da_confirmacao(kwargs)
        if not (kwargs.get("dados_confirmados") is True and prova.get("comprovada")):
            logger.warning("[InsurerDispatch] acionamento SEM confirmação comprovada "
                           "(campo=%s · %s) — NADA enviado",
                           kwargs.get("dados_confirmados"), prova.get("motivo"))
            if anterior is not None and mesmo_servico(anterior.get("servico"), kwargs.get("subservice")):
                return ja_acionado(kwargs, anterior["em"], de_outra_pessoa=de_outra_pessoa)
            return pedido_de_confirmacao(str(prova.get("motivo") or ""),
                                         ja_confirmou=bool(prova.get("comprovada")),
                                         pedido=kwargs,  # SPEC-126 U1: a linha pronta
                                         de_outra_pessoa=de_outra_pessoa)

        from app.services.corridor_playbooks import insurer_contact_env_var, resolve_insurer_contact

        playbook_ref, insurer_key = self._resolve_playbook_ref(kwargs)
        # 📊 SPEC-084.2 C3 — QUARTA cópia da mesma lista.
        # ⚠️ Hoje INERTE: `resolve_insurer_contact` recebe `line_kind` e o
        #    descarta (`insurer_contact_env_var` monta
        #    `INSURER_CONTACT_{KEY}_ASSISTENCIA`, sem a linha). Ficava certo
        #    por acidente. Derivar agora impede que ela passe a errar no dia em
        #    que o parâmetro voltar a ter função — e a falha seria a pior:
        #    a mensagem de um `socorro_mecanico` saindo pelo WhatsApp
        #    RESIDENCIAL da seguradora.
        from app.services.corridor_playbooks import linha_do_subservico as _linha_ct
        line = ("auto" if str(kwargs.get("line_kind") or "").lower() == "auto"
                else (_linha_ct(kwargs.get("subservice"))[0] or "residencial"))
        digits = lambda s: "".join(ch for ch in str(s or "") if ch.isdigit())  # noqa: E731
        insurer_phone = resolve_insurer_contact(insurer_key or "allianz", line_kind=line)
        # 🔴 SPEC-121 F5 — subserviço com CANAL PRÓPRIO (carro reserva da Yelum) nunca
        #    sai pelo número da assistência. `antes_de_acionar` já barrou o env vazio.
        from app.services.corridor_playbooks import contato_do_subservico
        _var_canal, _num_canal = contato_do_subservico(playbook_ref, kwargs.get("subservice"))
        if _var_canal:
            insurer_phone = _num_canal
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
                # 🔴 SPEC-126 CONSERTO Y (RT-B3): a sessão VIVA no número da seguradora é DESTE
                #    cliente e DESTE serviço → é o acionamento que já saiu (duas chamadas no mesmo
                #    turno, a mesma mensagem processada duas vezes ao mesmo tempo). Não entra na fila.
                viva = result.get("session") if isinstance(result.get("session"), dict) else {}
                if (viva and digits(viva.get("client_phone")) == client_phone
                        and mesmo_servico(viva.get("subservice"), subservice)):
                    logger.warning("[InsurerDispatch] a sessão viva já é deste cliente e serviço — "
                                   "NADA enviado, nada enfileirado")
                    return ja_acionado(kwargs, None, de_outra_pessoa=de_outra_pessoa)
                # FILA multi-cliente: número da seguradora ocupado com OUTRO
                # acionamento → entra na fila e inicia SOZINHO quando liberar.
                try:
                    from app.services.dispatch_router import enqueue_dispatch

                    position = await enqueue_dispatch(self.company_id, insurer_phone, {
                        "case_id": self.case_id or f"wa-{client_phone}",
                        "playbook_ref": playbook_ref, "subservice": subservice,
                        "slots": slots, "client_phone": client_phone,
                    })
                    await self._marcar_o_acionamento(kwargs, "enfileirado_em", subservice,
                                                     insurer_key or "")
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

        # 🔴 SPEC-126 CONSERTO Y — SAIU: o fato vai para a ficha durável antes de qualquer outra coisa
        await self._marcar_o_acionamento(kwargs, "enviado_em", subservice, insurer_key or "")
        insurer_label = (insurer_key or "a seguradora").upper()
        # 🔴 SPEC-126 U2-B (D1): a seguradora é dado da apólice do TITULAR — o parente não a ouve
        da_assistencia = "da seguradora" if de_outra_pessoa else f"da {insurer_label}"
        if finalize_live_for(playbook_ref):
            content = (
                "[ACIONAMENTO REAL INICIADO]\n"
                # 🔴 SPEC-125 Y2: o fiscal da honestidade ancora a frase no SERVIÇO
                #    que saiu (`honestidade_do_handoff.servicos_acionados`).
                f"SERVIÇO ACIONADO: {subservice or '-'}\n"
                f"A conversa com a assistência {da_assistencia} foi aberta pelo WhatsApp da corretora. "
                "A URA será respondida automaticamente com os dados coletados e o cliente será avisado "
                "assim que o protocolo/agendamento sair.\n"
                "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o acionamento FOI iniciado e que você retorna "
                "com o protocolo em instantes. NÃO invente protocolo/senha/prazo — eles chegam sozinhos."
            )
        else:
            content = (
                "[ACIONAMENTO EM MODO TESTE INICIADO]\n"
                f"A conversa com a assistência {da_assistencia} foi aberta pelo WhatsApp da corretora. "
                "O fluxo será executado até a confirmação final e CANCELADO antes de abrir o serviço "
                "(nenhum prestador será acionado).\n"
                "INSTRUÇÃO AO ATENDENTE: diga que o pedido está sendo processado. NÃO afirme que o serviço "
                "foi aberto nem invente protocolo — este acionamento é um teste e será cancelado no final."
            )
        return {"status": "dispatched", "content": content}
