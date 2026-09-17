"""A ficha do atendimento — o que o sistema já sabe, e que não pode esquecer.

O defeito que esta peça desfaz
------------------------------
📊 `grep -niE "\\bfase|phase|etapa|stage|slot" backend/app/agents/*.py` → **ZERO**.

O `AgentState` carrega mensagens, empresa, usuário, sessão, prompts e métricas.
E **nenhum campo** de fase, de dado já confirmado, ou de objetivo do atendimento.

A memória do que já foi perguntado **é a janela de contexto**: 60 mensagens.
Passou disso, o que o cliente respondeu no começo some, e o único remédio no
código é o prompt mandando *"RELEIA a conversa"*. O próprio comentário do
`langchain_service` registra que isso **já quebrou em produção** com janela
menor: o agente repediu o CPF do mesmo cliente.

E a tool de acionamento obriga o modelo a **re-declarar 15+ campos a cada
chamada**, reconstruídos do texto. Perdeu a janela, perdeu a coleta.

Num sinistro real — que passa de 60 mensagens com facilidade — isso significa
pedir de novo o CPF de alguém que acabou de bater o carro.

O laço que fecha
----------------
```
o modelo declara os slots na tool  →  a ficha GRAVA
                                          ↓
        o turno seguinte MOSTRA de volta  →  o modelo não repergunta
```

Duas propriedades que este módulo não abre mão:

**Nunca esquece um dado confirmado.** Merge é sempre aditivo: valor novo só
sobrescreve valor antigo se o novo não for vazio. Um turno em que o modelo
omite um campo não pode apagar o que o cliente já disse.

**A fase é DERIVADA, nunca declarada pelo modelo.** Ela é função do que existe
na ficha. Modelo não decide em que ponto o atendimento está — ele só informa o
que descobriu. Deixar o modelo escrever a fase seria deixá-lo dizer "já
acionei" sem ter acionado.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# As fases, na ordem em que um atendimento anda. Nomes em português porque
# aparecem na tela do corretor.
FASE_INTAKE = "intake"                  # chegou, ainda não se sabe o que é
FASE_IDENTIFICACAO = "identificacao"    # sabe-se o que é; falta saber quem é
FASE_COLETA = "coleta"                  # identificado; faltam dados do serviço
FASE_PRONTO = "pronto_para_acionar"     # tem tudo — pode acionar
FASE_ACIONADO = "acionado"              # a seguradora foi acionada
FASE_ACOMPANHANDO = "acompanhando"      # há protocolo; espera-se o prestador
FASE_COM_HUMANO = "com_humano"          # devolvido a uma pessoa
FASE_RESOLVIDO = "resolvido"            # acabou, com motivo escrito

ORDEM_DAS_FASES: List[str] = [
    FASE_INTAKE, FASE_IDENTIFICACAO, FASE_COLETA, FASE_PRONTO,
    FASE_ACIONADO, FASE_ACOMPANHANDO, FASE_COM_HUMANO, FASE_RESOLVIDO,
]

# Rótulos legíveis para o bloco que vai ao modelo. Chave técnica não ajuda o
# modelo a conversar: "titular_cpf" vira "CPF do titular".
#
# Esta tabela é o ÚNICO vocabulário de rótulo do atendimento. O motor de
# acionamento a importa (`insurer_dispatch_service._rotulo`) em vez de manter a
# sua — duas tabelas de rótulo divergem no dia em que alguém renomear um slot
# num lado só, e aí a mesma pergunta aparece com dois nomes para o mesmo
# corretor.
ROTULOS = {
    "titular_cpf": "CPF do titular",
    "titular_nome": "nome do titular",
    "telefone_contato": "telefone de contato",
    "veiculo_placa": "placa do veículo",
    "local_atual": "onde o veículo está",
    "local_destino": "para onde levar",
    "endereco_numero": "número do endereço",
    "problema_descricao": "o que aconteceu",
    "periodo_preferido": "período preferido",
    "risco_confirmado_sem_fumaca": "confirmação de que não há fumaça/faísca",
    "aparelho_marca_modelo": "marca e modelo do aparelho",
    "aparelho_idade": "idade do aparelho",
    # --- auto: o que as URAs pedem, e o que o formulário nativo exige --------
    "veiculo_cor": "cor do veículo",
    "veiculo_descricao": "modelo do veículo",
    "pessoa_no_local": "quem está com o veículo",
    "quando": "agora ou agendado",
    "rodovia": "se está em rodovia",
    "ponto_referencia": "ponto de referência",
    "local_cep": "CEP de onde o veículo está",
    "local_rua": "rua onde o veículo está",
    "local_numero": "número do local",
    "local_bairro": "bairro do local",
    "local_cidade": "cidade do local",
    "local_uf": "estado (UF) do local",
    "destino_cep": "CEP do destino",
    "destino_rua": "rua do destino",
    "destino_numero": "número do destino",
    "destino_bairro": "bairro do destino",
    "destino_cidade": "cidade do destino",
    "destino_uf": "estado (UF) do destino",
    # Os quatro do formulário nativo da família HDI/Yelum. Sem eles o
    # acionamento vai até a última tela e para — que é 📊 o que aconteceu nos 4
    # acionamentos mais recentes dessa família.
    "veiculo_em_garagem": "se o veículo está em garagem/estacionamento",
    "veiculo_nivel_rua": "em que nível o veículo está (subsolo, rua, acima)",
    "veiculo_situacoes": "condições do veículo (rebaixado, blindado, travado…)",
    "local_situacao": "como é o local (seguro, escuro, pouco movimento)",
    "ocupantes_particularidade": "se há criança, idoso ou PcD no local",
    # ------------------------------------------------------------------ #
    # 🔴 O QUE OS CORREDORES EXIGEM E O VOCABULÁRIO NÃO CONHECIA
    # ------------------------------------------------------------------ #
    #
    # 📊 14/09/2026, medido pelo MOTOR (`slots_do_atendimento()` sobre
    # `corridor_playbooks._PLAYBOOKS`): os 14 playbooks exigem **54**
    # `required_slots` distintos, e **37** não tinham rótulo aqui. Entre eles
    # `agua_escorrendo` — o slot que o encanador de 10/09 respondeu e ouviu a
    # mesma pergunta pela terceira vez.
    #
    # ⚠️ A redação é a do CLIENTE, não a da URA, e sai de
    # `corridor_playbooks._COMO_PERGUNTAR` (a mesma frase, em forma de rótulo).
    # ⛔ Slot de corredor sem rótulo aqui deixa `test_todo_slot_do_corredor_
    #    tem_ficha` VERMELHO — é a trava que impede as duas listas de divergir
    #    outra vez.
    "agua_escorrendo": "se a água ainda está escorrendo",
    "vazamento_local": "onde é o vazamento",
    "risco_confirmado_registro_fechado": "se o registro de água já foi fechado",
    "tipo_imovel": "se é casa, apartamento ou condomínio",
    # 🔴 Decisão do Founder (17/09): é o RAMO DA APÓLICE, perguntado JUNTO com a
    #    apólice — e só quando o sistema não a localizou. Nunca uma pergunta à parte.
    "qual_seguro_opcao": ("o ramo da apólice: se o seguro é da casa/apartamento, do "
                          "condomínio ou da empresa (junto com a apólice)"),
    "caixas_dagua_quantidade_opcao": "quantas caixas d’água precisam do serviço",
    "caixa_litros_opcao": "quantos litros tem cada caixa d’água",
    "chaveiro_necessidade_opcao": "se é abrir a porta, fazer a cópia, ou as duas",
    "chaveiro_alvo_opcao": "se é a porta da casa, o portão ou um cômodo",
    "chaveiro_porta_opcao": "se a porta é a principal ou uma interna",
    "chave_tipo_opcao": "o tipo da chave (simples, tetra, as duas ou eletrônica)",
    "fechadura_tipo_opcao": "que tipo de fechadura é",
    "encanador_tipo_opcao": "o que está vazando, com as palavras dele",
    "encanador_instalacao_opcao": "se é reparo do que quebrou ou instalação nova",
    "eletrodomestico_opcao": "qual é o aparelho (geladeira, fogão, máquina de lavar…)",
    "geladeira_medicacao_opcao": "se a geladeira guarda medicamento",
    "aparelho_marca": "a marca do aparelho",
    "aparelho_modelo": "o modelo ou a descrição do aparelho",
    "idade_aparelho_opcao": "a idade do aparelho (mais de 10 anos a seguradora recusa)",
    "ar_condicionado_tipo": "se o ar é de janela ou split",
    "ar_condicionado_btus": "a potência do ar em BTUs",
    "data_agendamento": "para que dia ele quer o agendamento",
    "email_segurado": "o e-mail do segurado",
    "pet_nome": "o nome do animal",
    "pet_raca": "a raça do animal",
    "pet_idade": "a idade do animal",
    "titular_nascimento": "a data de nascimento do titular",
    "local_seguro": "se ele está num lugar seguro para esperar",
    "estepe_situacao": "se o estepe está cheio e em condições de uso",
    "ferramentas_no_veiculo": "se macaco e chave de roda estão no carro",
    "equipamentos_troca_opcao": "se tem macaco, chave de roda e estepe",
    "pneus_danificados_opcao": "quantos pneus estão danificados",
    "pane_opcao": "o que o carro fez, com as palavras dele",
    "cambio_opcao": "se o câmbio é manual ou automático",
    "alavanca_travada_opcao": "se a alavanca do câmbio está travada",
    "bateria_tipo_opcao": "se é recarga ou bateria nova",
    "taxi_passageiros": "quantas pessoas vão no táxi",
}

#: Campos que a tool declara e que **não são dado do cliente** — lista fechada,
#: e cada um com o motivo escrito.
#:
#: 🔴 `dados_confirmados` é a marca de que o modelo MOSTROU os dados ao cliente
#: e ele confirmou (`insurer_dispatch_tool.py:254`). Deixá-lo virar slot faria
#: a ficha guardar `dados_confirmados: True` como se fosse uma resposta do
#: segurado, e o bloco do prompt diria ao modelo "não pergunte de novo" sobre
#: um campo de controle. Ele já tem destino próprio: vira `apolice_confirmada`.
CAMPOS_DE_CONTROLE = frozenset({
    "dados_confirmados",
})

# ---- de onde veio cada confirmação ---------------------------------------- #
#
# 💭 Um dado que veio do cadastro pode precisar de confirmação; um dado que o
# segurado disse **não pode ser perguntado de novo, nunca**. Sem origem, o
# modelo trata os dois igual — e foi assim que ele pediu confirmação de placa
# que a InfoCap já tinha resolvido.
ORIGEM_CLIENTE = "cliente"
ORIGEM_SISTEMA_DE_GESTAO = "sistema_de_gestao"
ORIGEM_CORREDOR = "corredor"
ORIGEM_DESCONHECIDA = "desconhecida"

_VAZIOS = ("", "none", "null", "nao informado", "não informado", "n/a", "-")


def _tem_valor(v: Any) -> bool:
    """Um slot só conta como confirmado se tiver conteúdo de verdade.

    O modelo às vezes preenche com `"não informado"` para não deixar o campo em
    branco. Aceitar isso como confirmado faria a ficha declarar completo um
    atendimento que não está — e o acionamento sairia sem o dado.
    """
    if v is None or isinstance(v, bool):
        return bool(v) if isinstance(v, bool) else False
    s = str(v).strip()
    return bool(s) and s.lower() not in _VAZIOS


# ---- a identidade da THREAD (SPEC-EXTRA-001.2 §8.3) ----------------------- #
#
# 🔴 **O defeito, medido:** em 10/09/2026 o agente abriu um caso chamando o
# cliente pelo nome de OUTRA pessoa, de 22 dias atrás. A thread do WhatsApp é
# por TELEFONE e nunca reinicia — a ficha é aditiva de propósito (é o conserto
# da pergunta repetida), e a ficha aditiva carrega o nome para sempre.
#
# ⛔ **Sem coluna nova e sem tabela nova** (CLAUDE.md §5): a identidade mora
# dentro da ficha, que já é uma coluna JSON.
#
#   {"assunto_id": …, "titular_nome": …, "apresentado_em": …,
#    "nome_da_apresentacao": …}
#
# 🔴 E o nome do segurado entra no prompt **só** daqui. É o que impede o nome
# de 22 dias atrás de reaparecer.

#: Os slots que PERTENCEM ao assunto, não ao telefone. ⚠️ O nome do titular é o
#: único hoje: placa, CPF e apólice são do contrato, e o contrato não muda
#: porque um caso fechou. 📊 Um `titular_nome` de 22 dias atrás num sinistro
#: novo é a diferença entre "sr. Fulano" e o nome de quem realmente escreveu.
SLOTS_DA_IDENTIDADE = frozenset({"titular_nome"})


def identidade_vazia() -> Dict[str, Any]:
    # 🔴 `apresentacao_pendente_*` é a INTENÇÃO do turno (J5, 14/09/2026):
    # o bloco do prompt pediu a apresentação, mas ela só vira `apresentado_em`
    # depois de o `send_message` confirmar que a mensagem SAIU. ⚠️ São dois
    # campos de TEXTO, e não um dicionário, porque `identidade_de` e `fundir`
    # tratam a identidade como mapa de strings — um dicionário aqui seria
    # silenciosamente convertido em `str(...)` e voltaria ilegível.
    return {"assunto_id": "", "titular_nome": "", "apresentado_em": "",
            "nome_da_apresentacao": "",
            "apresentacao_pendente_em": "", "apresentacao_pendente_nome": ""}


def identidade_de(ficha: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A identidade desta thread, sempre completa. **PURA.**"""
    base = identidade_vazia()
    bruta = (ficha or {}).get("identidade")
    if isinstance(bruta, dict):
        for chave in base:
            if bruta.get(chave):
                base[chave] = str(bruta[chave])
    return base


def titular_do_prompt(ficha: Optional[Dict[str, Any]] = None) -> str:
    """O nome com que o agente trata o segurado NESTE assunto — ou `""`.

    ⛔ Nunca de memória, nunca de RAG, nunca do histórico (§8.3).
    """
    return identidade_de(ficha).get("titular_nome") or ""


def ficha_vazia() -> Dict[str, Any]:
    return {
        "fase": FASE_INTAKE,
        "ramo": "", "servico": "", "seguradora": "",
        "confirmados": {},
        "apolice_confirmada": False,
        "acionamento": {},
        "atualizada_em": None,
        "historico": [],
        "identidade": identidade_vazia(),
    }


def derivar_fase(ficha: Dict[str, Any], obrigatorios: Optional[List[str]] = None) -> str:
    """A fase é consequência do que se sabe — não uma opinião do modelo.

    Ordem de precedência de cima para baixo: um caso resolvido não volta a ser
    coleta porque o cliente mandou mais uma mensagem; um caso com humano não
    volta a ser automático sozinho.
    """
    if ficha.get("resolvido_em"):
        return FASE_RESOLVIDO
    if ficha.get("fase") == FASE_COM_HUMANO:
        return FASE_COM_HUMANO

    acion = ficha.get("acionamento") or {}
    if acion.get("protocolo"):
        return FASE_ACOMPANHANDO
    if acion.get("enviado_em"):
        return FASE_ACIONADO

    confirmados = ficha.get("confirmados") or {}
    # `valor_de` porque a confirmação pode vir embrulhada com a origem; sem ele
    # um `{"valor": "", …}` contaria como preenchido e a fase pularia para
    # "pronto para acionar" com o campo vazio.
    faltando = [s for s in (obrigatorios or [])
                if not _tem_valor(valor_de(confirmados.get(s)))]

    if obrigatorios and not faltando and ficha.get("apolice_confirmada"):
        return FASE_PRONTO
    if confirmados or ficha.get("servico"):
        return FASE_COLETA
    if ficha.get("ramo"):
        return FASE_IDENTIFICACAO
    return FASE_INTAKE


def fundir(ficha: Dict[str, Any], novidades: Dict[str, Any],
           obrigatorios: Optional[List[str]] = None) -> Dict[str, Any]:
    """Junta o que o turno descobriu ao que já se sabia. **Sempre aditivo.**

    Um turno em que o modelo não repete um campo NÃO pode apagar o que o cliente
    já respondeu — é literalmente o defeito que estamos consertando. Valor novo
    só entra se tiver conteúdo.
    """
    nova = dict(ficha or ficha_vazia())
    nova.setdefault("confirmados", {})
    nova.setdefault("historico", [])
    fase_antes = nova.get("fase")

    # 🔴 A ÚNICA EXCEÇÃO À ADITIVIDADE — e ela existe por um defeito medido.
    #
    # 📊 10/09/2026: o agente chamou o cliente pelo nome de outra pessoa, de 22
    # dias atrás. A ficha aditiva é o conserto da pergunta repetida; ela é
    # TAMBÉM o que carrega o nome errado para sempre. ⚠️ Quando o ASSUNTO muda
    # (o motor do reencontro é quem sabe: `o_fim_do_atendimento._ASSUNTO_NOVO`),
    # a identidade é **REESCRITA, nunca herdada** — e os slots que pertencem ao
    # assunto (não ao telefone) saem junto. ⛔ Sem a segunda metade, o nome
    # antigo voltaria por `confirmados` e o conserto seria de fachada.
    nova_ident = novidades.get("identidade")
    if isinstance(nova_ident, dict) and nova_ident:
        antes = identidade_de(nova)
        depois = {**identidade_vazia(), **{k: str(v or "")
                                           for k, v in nova_ident.items()
                                           if k in identidade_vazia()}}
        if depois.get("assunto_id") and depois["assunto_id"] != antes.get("assunto_id"):
            nova["identidade"] = depois
            nova["confirmados"] = {k: v for k, v in (nova["confirmados"] or {}).items()
                                   if k not in SLOTS_DA_IDENTIDADE}
        else:
            # Mesmo assunto: a identidade se completa (o nome que o cliente
            # acabou de dizer, a hora em que a apresentação aconteceu).
            nova["identidade"] = {**antes, **{k: v for k, v in depois.items() if v}}

    for campo in ("ramo", "servico", "seguradora"):
        if _tem_valor(novidades.get(campo)):
            nova[campo] = str(novidades[campo]).strip().lower()

    for chave, valor in (novidades.get("confirmados") or {}).items():
        if _tem_valor(valor):
            nova["confirmados"][chave] = valor

    # O nome que o segurado disse NESTE assunto é a identidade dele aqui. ⚠️ O
    # espelho é de mão única: `confirmados` alimenta a identidade, nunca o
    # contrário — senão o nome apagado no assunto novo voltaria pela porta dos
    # fundos.
    _titular = valor_de((nova.get("confirmados") or {}).get("titular_nome"))
    if _tem_valor(_titular):
        nova["identidade"] = {**identidade_de(nova),
                              "titular_nome": str(_titular).strip()}

    if novidades.get("apolice_confirmada") is True:
        nova["apolice_confirmada"] = True          # confirmação não se desfaz sozinha
    if novidades.get("acionamento"):
        nova["acionamento"] = {**(nova.get("acionamento") or {}),
                               **(novidades["acionamento"] or {})}
    if novidades.get("fase") == FASE_COM_HUMANO:
        nova["fase"] = FASE_COM_HUMANO
    if novidades.get("resolvido_em"):
        nova["resolvido_em"] = novidades["resolvido_em"]
        nova["resolucao_motivo"] = novidades.get("resolucao_motivo") or ""

    nova["fase"] = derivar_fase(nova, obrigatorios)
    nova["atualizada_em"] = datetime.now(timezone.utc).isoformat()

    if nova["fase"] != fase_antes:
        # O histórico é curto de propósito: serve para explicar o caso a um
        # humano, não para virar log de auditoria (esse é o `agent_activities`).
        nova["historico"] = (nova["historico"] + [{
            "fase": nova["fase"], "em": nova["atualizada_em"],
        }])[-12:]
    return nova


def _slots_dos_corredores() -> set:
    """Todo `required_slots` declarado pelos playbooks — lido do MOTOR.

    ⛔ Não é regex sobre o fonte de `corridor_playbooks`. Metade dos
    subserviços só existe depois que o módulo importa (`_ativar_subservico`,
    `_resid_slots`, o overlay que acrescenta `tipo_imovel`): ler o arquivo
    veria uma lista menor do que a que roda. 📊 14/09/2026 — pelo motor: **54**
    slots distintos; por AST do fonte: 20. CLAUDE.md §9.4.

    Falha de importação devolve conjunto vazio: sem corredor, a ficha continua
    valendo pelo `ROTULOS`, e o atendimento não cai por causa do vocabulário.
    """
    try:
        from app.services.corridor_playbooks import _PLAYBOOKS
    except Exception as exc:  # noqa: BLE001
        logger.warning("[FICHA] corredores indisponíveis (%s) — vocabulário só "
                       "com ROTULOS", type(exc).__name__)
        return set()

    saida: set = set()
    for playbook in _PLAYBOOKS.values():
        for cfg in (playbook.get("subservices") or {}).values():
            saida.update(str(s) for s in (cfg.get("required_slots") or []))
    return saida


def slots_do_atendimento() -> frozenset:
    """Todo slot que o produto pode coletar do segurado. DERIVADO, nunca à mão.

        ROTULOS  ∪  os `required_slots` de todos os corredores
        menos    CAMPOS_DE_CONTROLE

    🔴 Era uma **tupla literal de 15 nomes** em `nodes._SLOTS_DA_FICHA`, ao lado
    de um `ROTULOS` de 35 e de corredores que exigiam outros 37. Duas listas
    escritas à mão divergem no dia em que alguém acrescenta um slot num lado só
    — e já tinham divergido: `agua_escorrendo` não estava em nenhuma das duas, e
    o segurado ouviu a mesma pergunta três vezes.
    """
    base = set(ROTULOS) | _slots_dos_corredores()
    return frozenset(base - CAMPOS_DE_CONTROLE)


def valor_de(confirmado: Any) -> Any:
    """O valor de uma confirmação, venha ela na forma nova ou na antiga.

    A forma nova é `{"valor": …, "origem": …, "em": …}`. A antiga é o valor
    cru. ⚠️ Toda leitura passa por aqui: uma ficha gravada ontem não pode
    aparecer para a URA como `{'valor': 'ABC1D23', …}`.
    """
    if isinstance(confirmado, dict) and "valor" in confirmado:
        return confirmado.get("valor")
    return confirmado


def origem_de(confirmado: Any) -> str:
    """Quem confirmou. Ficha antiga não mente: devolve `desconhecida`."""
    if isinstance(confirmado, dict) and confirmado.get("origem"):
        return str(confirmado["origem"])
    return ORIGEM_DESCONHECIDA


def confirmacao(valor: Any, origem: str = ORIGEM_CLIENTE) -> Dict[str, Any]:
    """Monta a confirmação com origem e carimbo de hora."""
    return {"valor": valor, "origem": str(origem or ORIGEM_DESCONHECIDA),
            "em": datetime.now(timezone.utc).isoformat()}


def rotulo(slot: str) -> str:
    """O nome humano do slot. Slot sem rótulo devolve o próprio nome — nunca
    um nome bonito inventado, que esconderia um campo que ninguém batizou."""
    return ROTULOS.get(str(slot or ""), str(slot or ""))


def dados_conhecidos(ficha: Optional[Dict[str, Any]] = None,
                     extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Tudo que o sistema JÁ SABE deste atendimento, achatado, sem vazio.

    É a fonte do banco de respostas determinístico
    (`insurer_dispatch_service.responder_da_ficha`): quando a URA pergunta o CEP
    e o CEP está aqui, a resposta sai na hora — sem varredura de 20s, sem
    Sentinela, sem LLM. A URA da HDI encerra sozinha em 12 minutos; um dado que
    já está na ficha desde o começo não pode custar minutos para sair.

    Duas propriedades, e as duas são o motivo de a função existir:

    **Ausente é ausente.** Chave sem valor de verdade (`_tem_valor`) não entra.
    O banco de respostas só sabe recusar o que não recebe — se um "não
    informado" entrasse aqui como se fosse dado, ele seria RESPONDIDO à
    seguradora como se fosse verdade.

    **O caso vence a ficha.** `extras` (os slots do acionamento em curso) entra
    por cima: se o corretor corrigiu o endereço ao abrir o acionamento, é o
    endereço corrigido que vai para a URA, não o que a ficha guardou antes.

    🔴 **E o valor é desembrulhado aqui.** Desde a SPEC-EXTRA-001.2 uma
    confirmação pode ser `{"valor": …, "origem": …}`. Sem `valor_de`, a URA da
    seguradora receberia `{'valor': 'ABC1D23', 'origem': 'cliente'}` como se
    fosse a placa — um dado errado dito à seguradora, não um bug de tela.
    """
    saida: Dict[str, Any] = {}
    for fonte in ((ficha or {}).get("confirmados") or {}, extras or {}):
        for chave, bruto in fonte.items():
            valor = valor_de(bruto)
            if _tem_valor(valor):
                saida[str(chave)] = valor if isinstance(valor, (list, tuple)) else str(valor).strip()
    return saida


def bloco_para_o_prompt(ficha: Dict[str, Any],
                        obrigatorios: Optional[List[str]] = None) -> str:
    """O que o modelo vê no começo do turno. Curto, e sem enfeite.

    Não repetimos a conversa — ela já está no histórico. Repetimos só o que o
    histórico pode ter perdido: o que foi CONFIRMADO e o que ainda FALTA.
    """
    if not ficha or ficha.get("fase") in (None, FASE_INTAKE):
        if not (ficha or {}).get("confirmados"):
            return ""

    confirmados = ficha.get("confirmados") or {}
    linhas = ["=== 📋 FICHA DESTE ATENDIMENTO (já apurado) ==="]

    cabeca = " · ".join(x for x in (ficha.get("ramo"), ficha.get("servico"),
                                    ficha.get("seguradora")) if x)
    if cabeca:
        linhas.append(f"Caso: {cabeca}")
    linhas.append(f"Fase: {ficha.get('fase')}")

    # 🔴 A ORIGEM SEPARA AS DUAS LISTAS — e é a diferença entre um dado que não
    # pode ser perguntado outra vez e um que pode ser lido de volta em uma
    # frase. O que veio do sistema de gestão (placa, veículo, nome da apólice)
    # o atendente CONFIRMA; o que o segurado disse, ele NÃO repete.
    do_cliente = [(k, v) for k, v in confirmados.items()
                  if origem_de(v) != ORIGEM_SISTEMA_DE_GESTAO]
    do_sistema = [(k, v) for k, v in confirmados.items()
                  if origem_de(v) == ORIGEM_SISTEMA_DE_GESTAO]

    if do_cliente:
        linhas.append("JÁ CONFIRMADO com o cliente — **não pergunte de novo**:")
        for chave, bruto in do_cliente:
            linhas.append(f"  · {ROTULOS.get(chave, chave)}: {valor_de(bruto)}")
    if do_sistema:
        linhas.append("Veio do sistema de gestão — pode confirmar com uma "
                      "frase, sem perguntar do zero:")
        for chave, bruto in do_sistema:
            linhas.append(f"  · {ROTULOS.get(chave, chave)}: {valor_de(bruto)}")

    faltando = [s for s in (obrigatorios or [])
                if not _tem_valor(valor_de(confirmados.get(s)))]
    if faltando:
        linhas.append("AINDA FALTA para poder acionar:")
        for s in faltando:
            linhas.append(f"  · {ROTULOS.get(s, s)}")

    acion = ficha.get("acionamento") or {}
    if acion.get("protocolo"):
        linhas.append(f"Protocolo já obtido: {acion['protocolo']} — "
                      "acompanhe, não acione de novo.")

    linhas.append("Se um dado acima estiver errado, o cliente vai corrigir. "
                  "Até lá, trate como verdade e siga do ponto em que parou.")
    return "\n".join(linhas)


# --------------------------------------------------------------------- #
# O guarda de pergunta repetida — puro, e sobre o texto do PRODUTO
# --------------------------------------------------------------------- #
#
# 📊 10/09/2026: a ficha já tinha `agua_escorrendo` respondido pelo segurado
# ("não, fechei o registro") e a atendente perguntou a mesma coisa pela
# TERCEIRA vez. O bloco existia, era injetado — e estava vazio para aquele
# slot, porque o escritor não o conhecia (§0.3 da SPEC-EXTRA-001.2).
#
# 🔴 **AS ÂNCORAS MORAM EM `app/resources/`, NÃO EM `tests/`** (J9,
# 14/09/2026). Elas nasceram como fixture, e o produto as lia de
# `backend/tests/fixtures/` — um diretório que existe na árvore de trabalho e
# não tem nenhuma promessa de existir na imagem que roda. ⛔ Produto que lê de
# `tests/` é produto que funciona até alguém enxugar a imagem, e aí o fiscal da
# pergunta repetida se desliga SOZINHO e em silêncio (o `except` abaixo).
# ⚠️ O `Dockerfile` copia `app/` inteiro (`COPY . .`), e não há `.dockerignore`
# — conferido em 14/09/2026. Os testes leem do MESMO arquivo: uma cópia seria
# uma segunda verdade.
#
# ⚠️ As âncoras vêm de `app/resources/ancoras_de_pergunta_por_slot.json`:
# arquivo DECLARADO e revisável, gerado do motor dos corredores mais as formas
# escritas, cada uma carregando o texto do produto de onde saiu. Slot sem forma
# declarada fica em `sem_ancora` — e o guarda G7 imprime quantos são. ⛔ Âncora
# nunca vem da imaginação (CLAUDE.md §9.4).
_ANCORAS_ARQUIVO = "ancoras_de_pergunta_por_slot.json"
_ANCORAS_CACHE: Optional[Dict[str, Any]] = None


def _ler_ancoras() -> Dict[str, Any]:
    import json
    import os

    # `app/services/attendance_ficha.py` -> `app/` -> `app/resources/`.
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho = os.path.join(app_dir, "resources", _ANCORAS_ARQUIVO)
    try:
        with open(caminho, encoding="utf-8") as fh:
            dados = json.load(fh)
        slots = dados.get("slots") or {}
        saida = {k: v for k, v in slots.items() if isinstance(v, list) and v}
        logger.info("[FICHA] âncoras de pergunta: %d slots com forma declarada, "
                    "%d sem", len(saida), len(slots) - len(saida))
        return saida
    except Exception as exc:  # noqa: BLE001
        # Sem o arquivo o fiscal fica cego — e diz isso alto. Nunca derruba o
        # turno: a resposta ao segurado vale mais que a régua de estilo.
        logger.error("[FICHA] âncoras de pergunta não carregaram (%s) — o fiscal "
                     "de pergunta repetida fica DESLIGADO", type(exc).__name__)
        return {}


def ancoras_de_pergunta() -> Dict[str, Any]:
    """As formas com que o agente pergunta cada slot. Lido uma vez por processo."""
    global _ANCORAS_CACHE
    if _ANCORAS_CACHE is None:
        _ANCORAS_CACHE = _ler_ancoras()
    return _ANCORAS_CACHE


def _slots_do_corredor(corredor: str) -> Optional[set]:
    """Os slots que ESTE corredor pode exigir — ou `None` se não o conhecemos.

    Serve para não acusar repetição com a âncora de outro ofício: *"qual a
    marca do aparelho"* é pergunta de eletrodoméstico, e não tem o que fazer
    numa conversa de encanador (CLAUDE.md §9.5, pergunta C).
    """
    nome = str(corredor or "").strip().lower()
    if not nome:
        return None
    try:
        from app.services.corridor_playbooks import _PLAYBOOKS, canonical_subservice
        alvo = canonical_subservice(nome) or nome
        saida: set = set()
        for playbook in _PLAYBOOKS.values():
            for sub, cfg in (playbook.get("subservices") or {}).items():
                if str(sub).lower() == alvo:
                    saida.update(str(s) for s in (cfg.get("required_slots") or []))
        return saida or None
    except Exception:  # noqa: BLE001
        return None


def slots_reperguntados(resposta: str, ficha: Dict[str, Any], *,
                        corredor: str = "") -> List[str]:
    """Quais slots JÁ CONFIRMADOS PELO CLIENTE a resposta volta a perguntar. PURA.

    ⚠️ **O dialeto é o do motor** (CLAUDE.md §9.4): as âncoras dos corredores
    foram escritas para `corridor_playbooks._norm` — sem acento, sem o `*` do
    negrito — e aplicadas com `IGNORECASE|DOTALL`, exatamente como
    `match_ura_step` as aplica. Rodá-las sobre o texto cru perderia metade do
    acervo, em silêncio.

    Só acusa o que tem origem `cliente`: o que veio do sistema de gestão **pode**
    ser confirmado numa frase — e cobrar isso como defeito ensinaria o modelo a
    acionar com dado que ninguém conferiu.
    """
    import re

    texto = str(resposta or "")
    confirmados = (ficha or {}).get("confirmados") or {}
    if not texto.strip() or not confirmados:
        return []
    try:
        from app.services.corridor_playbooks import _norm
    except Exception:  # noqa: BLE001
        return []

    alvo = _norm(texto)
    escopo = _slots_do_corredor(corredor)
    mapa = ancoras_de_pergunta()

    achados: List[str] = []
    for slot, bruto in confirmados.items():
        if origem_de(bruto) != ORIGEM_CLIENTE or not _tem_valor(valor_de(bruto)):
            continue
        if escopo is not None and slot not in escopo:
            continue
        for entrada in (mapa.get(slot) or []):
            padrao = (entrada or {}).get("padrao")
            if not padrao:
                continue
            try:
                if re.search(padrao, alvo, re.IGNORECASE | re.DOTALL):
                    achados.append(slot)
                    break
            except re.error:
                continue
    return achados


# --------------------------------------------------------------------- #
# I/O — sempre com company_id (CLAUDE.md §7)
# --------------------------------------------------------------------- #

async def carregar(supabase, company_id: str, session_id: str) -> Dict[str, Any]:
    """Lê a ficha da conversa. Falha de leitura devolve ficha vazia.

    Ficha vazia faz o agente perguntar de novo — chato, mas correto. Inventar
    dado que não foi lido seria pior: o acionamento sairia com informação que
    ninguém confirmou.
    """
    import asyncio

    if not company_id or not session_id:
        return ficha_vazia()
    try:
        def _q():
            return (supabase.table("conversations")
                    .select("ficha_atendimento")
                    .eq("company_id", str(company_id))
                    .eq("session_id", str(session_id))
                    .limit(1).execute())

        res = await asyncio.to_thread(_q)
        if res.data and isinstance(res.data[0].get("ficha_atendimento"), dict):
            base = ficha_vazia()
            base.update(res.data[0]["ficha_atendimento"])
            return base
    except Exception as exc:  # noqa: BLE001
        logger.warning("[FICHA] leitura falhou (%s) — seguindo sem ficha",
                       type(exc).__name__)
    return ficha_vazia()


async def gravar(supabase, company_id: str, session_id: str,
                 novidades: Dict[str, Any],
                 obrigatorios: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Funde e grava. Nunca derruba o turno: a resposta ao cliente vale mais."""
    import asyncio

    if not company_id or not session_id or not novidades:
        return None
    try:
        atual = await carregar(supabase, company_id, session_id)
        nova = fundir(atual, novidades, obrigatorios)

        def _u():
            dados: Dict[str, Any] = {"ficha_atendimento": nova}
            if nova.get("resolvido_em"):
                dados["resolvido_em"] = nova["resolvido_em"]
                dados["resolucao_motivo"] = nova.get("resolucao_motivo") or ""
            return (supabase.table("conversations").update(dados)
                    .eq("company_id", str(company_id))
                    .eq("session_id", str(session_id)).execute())

        await asyncio.to_thread(_u)
        logger.info("[FICHA] empresa=%s fase=%s confirmados=%d",
                    company_id, nova.get("fase"), len(nova.get("confirmados") or {}))
        return nova
    except Exception as exc:  # noqa: BLE001
        logger.error("[FICHA] gravação falhou (%s) — o atendimento segue, mas "
                     "este turno não deixou memória", type(exc).__name__)
        return None
