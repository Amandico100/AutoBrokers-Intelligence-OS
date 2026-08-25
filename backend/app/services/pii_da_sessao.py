# -*- coding: utf-8 -*-
"""O retrato da sessão de acionamento que uma PESSOA pode ler — SPEC-085 FASE 1.

> ## Este NÃO é o payload de restauração. Ele nunca substitui `output_summary`.

## Por que este módulo existe, e por que ele não é "o quinto mascarador"

`CLAUDE.md` §5 manda consolidar antes de duplicar, e a §F1.1(c) da SPEC cobra a
justificativa por escrito. 📊 Os quatro que existem foram lidos, e **nenhum
serve**, por motivos diferentes:

| onde | o que mascara | por que não serve aqui |
|---|---|---|
| `core/egress_guard.redact_headers` | cabeçalho HTTP | não é PII — é segredo em header |
| `whatsapp/numero_pareado.mascarar` | telefone → `5547*****463` | 🔴 usa `*`, que é alfabeto de `corridor_playbooks._CARACTERE_DE_MASCARA` |
| `billing_collection._mascarar_documento` | CPF/CNPJ → `...1234` | privado do módulo de cobrança, e só sabe documento |
| `atlas/templater` | TEXTO de conversa → `{VALOR}` | trabalha em texto corrido, não num dicionário tipado de slots |

🔴 **O que este módulo consolida é a DECISÃO, não o algoritmo.** Ele é o único
lugar que sabe *"o slot `titular_cpf` é documento, `eletrodomestico_opcao` não é
PII"*. O formato de documento é o **mesmo** de `_mascarar_documento` (`...1234`)
de propósito: o Founder já aceitou aquele nível de exposição para o corretor
distinguir duas pessoas numa lista, e inventar um segundo nível seria criar a
divergência que a §5 existe para impedir.

## 🔴 O ALFABETO, e ele é a armadilha da §F1.1(b)

`corridor_playbooks._CARACTERE_DE_MASCARA = "#*?•●"` é como o corredor reconhece
a máscara **da seguradora** — `AA#-###9` numa placa, `###.###.###-##` num CPF que
a URA devolve. Se a NOSSA máscara usar os mesmos caracteres, o corredor passa a
poder ler o próprio mascaramento como resposta da URA, e `bate_com_mascara`
compara lixo com lixo.

⚠️ Hoje isso é **estruturalmente impossível**: o retrato daqui mora em
`work_steps.output_redacted`, e quem restaura lê `output_summary`. Mas esta SPEC
inteira é sobre suposições estruturais que falham em silêncio — então o alfabeto
é escolhido para não colidir, e há um guarda que prova isso
(`test_o_formato_nao_colide_com_a_mascara_DA_SEGURADORA`).

## O que ele NÃO faz, e cada linha é uma decisão

**Não mascara escolha de menu.** `eletrodomestico_opcao = "3"` é a tecla que o
corredor apertou, não um dado de pessoa. 🔴 Apagar isso destrói a única pista de
**por onde ele andou** — e um retrato que esconde o caminho não serve para triar
travamento nenhum, que é a razão de a coluna existir.

**Não mascara o telefone da SEGURADORA.** `insurer_phone` é a linha de
assistência 24h, publicada pela seguradora e presente em `INSURER_CONTACT_*`.
Ela identifica uma empresa, não uma pessoa — e é o que diz *com quem* o corredor
estava falando.

**Não carrega o `transcript`.** Ele é conversa crua, e mascarar conversa é outro
problema (o do `atlas/templater`, com regra própria). Aqui fica só o total —
quem quer os bytes tem o Espelho em `messages`, lincado ao caso.

**É PURO.** Sem banco, sem rede, sem relógio. 📊 O `gate.yml` não roda
`pip install`; guarda que precise de dependência não roda em CI.
"""
from __future__ import annotations

import re
from typing import Any, Dict

# ---------------------------------------------------------------------------
# A CLASSIFICAÇÃO — por PEDAÇO DO NOME, não por lista fechada
# ---------------------------------------------------------------------------
# 🔴 Lista fechada envelhece: um corredor novo com `condutor_cpf` passaria
# direto. 📊 As chaves de hoje, lidas do banco em 24/08/2026:
#
#   titular_cpf · telefone_contato · endereco_numero · ponto_referencia ·
#   aparelho_marca · aparelho_modelo · problema_descricao · e os `*_opcao`
#
# ⚠️ E a regra é **fail-closed**: o que este módulo não reconhece como seguro
# vira `{TEXTO}`. Um campo novo desconhecido é mascarado até alguém decidir o
# contrário — o inverso deixaria PII passar por omissão, que é como ela passa.
_DOCUMENTO = ("cpf", "cnpj", "documento", "_rg", "rg_", "identidade")
_TELEFONE = ("telefone", "celular", "whatsapp", "fone", "phone")
_NOME = ("nome", "condutor", "titular", "responsavel", "segurado")
_PLACA = ("placa", "chassi", "renavam")

# 🔴 Identificador que CARREGA PII dentro. Vira cauda, não `{TEXTO}`: quem tria
# ainda precisa de um fio para puxar, e a cauda dá o mesmo nível de exposição
# que o telefone mascarado — nem mais, nem menos.
_IDENTIFICADOR_COM_PII = ("case_id",)

# Seguro por construção: escolha de menu e marcadores do próprio motor.
_SUFIXOS_SEGUROS = ("_opcao",)
# 🔴 `case_id` NÃO ESTÁ AQUI, E A RAZÃO CUSTOU UM VAZAMENTO MEU.
#
# Ele estava. 📊 O backfill das 12 etapas foi escrito, e a conferência no banco
# — feita sem trazer um único valor para a tela — devolveu:
#
#     case_id CONTÉM o telefone do cliente ....... 12 de 12
#     comprimento do case_id ..................... 15, sempre
#
# O `case_id` deste produto é montado **a partir do telefone do segurado**. Um
# campo com cara de identificador técnico carregando PII inteira dentro — que é
# o `CLAUDE.md` §12.1 na forma mais cara: *"se o nome de um campo mente sobre o
# que ele guarda, conserte o campo"*.
#
# ⚠️ E o retrato não perde nada com isso: quem tria correlaciona por
# `work_run_id` e `mirror_conversation_id`, que são ids de banco de verdade.
_CHAVES_SEGURAS = (
    "playbook_ref", "subservice", "state", "reason", "company_id",
    "insurer_phone", "insurer_key", "ramo", "servico", "retry_count",
    "sentinela_attempts", "mirror_idx", "mirror_conversation_id", "work_run_id",
    "created_at", "followup_at", "closing_at", "transcript_total", "live",
    "missing_slots", "step_counts", "silencios_seguidos",
    # 🔴 `confirmacoes` SAIU DAQUI — e ela estava errada desde a primeira linha.
    #
    # 📊 Ela guarda `tela` = os ÚLTIMOS 400 CARACTERES DA TELA DA URA e
    # `anchor` (120) — `corridor_playbooks.py:9519`. É texto corrido, e o
    # cabeçalho deste módulo diz, ele mesmo, que texto corrido é outro
    # problema. Medido em produção: 2 gêmeos com `confirmacoes`, 533 caracteres.
    #
    # ⚠️ A URA ECOA O QUE MANDAMOS. Uma tela de confirmação repete nome,
    # endereço e telefone de volta — e isso ia inteiro para uma coluna cujo
    # `COMMENT` promete "PII mascarada" e que a RLS nova expõe a `authenticated`.
    #
    # Ela vira `{DICT:n}`, como toda estrutura não declarada.
    # SPEC-085 B.2/B.3: `ausente` | `recusado` | `envio_falhou`. É um enum de
    # três valores e é o que diz à corretora o que fazer — cadastrar um destino
    # ou parar de compartilhar o que ela tem.
    # ⚠️ `suporte_indisponivel_motivo` fica de FORA de propósito: ele é texto
    # livre, e texto livre é mascarado por padrão (fail-closed).
    "suporte_indisponivel",
)

# 🔴 O alfabeto: NENHUM caractere de `corridor_playbooks._CARACTERE_DE_MASCARA`.
_RETICENCIA = "..."
_SO_DIGITOS = re.compile(r"\D+")


def _cauda(valor: Any, quantos: int = 4) -> str:
    """`529.982.247-25` → `...4725`. Mesmo formato de `_mascarar_documento`.

    Serve para CONFERIR, não para usar: quem tria precisa distinguir dois casos
    numa lista, e para isso bastam quatro dígitos.
    """
    digitos = _SO_DIGITOS.sub("", str(valor or ""))
    if len(digitos) < quantos:
        return _RETICENCIA
    return _RETICENCIA + digitos[-quantos:]


def _classificar(chave: str) -> str:
    """`documento` · `telefone` · `nome` · `placa` · `seguro` · `texto`."""
    k = str(chave or "").lower()

    # 🔴 A ORDEM É O CONSERTO, E ELA CUSTOU DOIS VAZAMENTOS MEUS.
    #
    # A primeira versão testava "é seguro?" antes de "é PII?", e o `case_id`
    # atravessou com o telefone dentro. Eu consertei aquele caso pondo UM nome
    # antes da lista segura — e **não generalizei**. O juiz do isolamento
    # mediu o que sobrou:
    #
    #     "telefone_adicionar_opcao": "47999887766"      <- CRU
    #     "titular_cpf_opcao":        "529.982.247-25"   <- CRU
    #     "nome_do_condutor_opcao":   "Joao da Silva"    <- CRU
    #
    # 📊 E `telefone_adicionar_opcao` não é hipótese: é slot REAL, presente em
    # 12 das 12 etapas duráveis. O sufixo `_opcao` vencia todo marcador de PII.
    #
    # ⚠️ **Marcador de PII vem PRIMEIRO. Sempre.** Um `titular_confirmou_opcao`
    # (sim/não) passa a ser mascarado sem precisar — e isso é o preço certo:
    # mascarar demais custa uma pista; mascarar de menos custa um CPF.
    for marca in _DOCUMENTO:
        if marca in k:
            return "documento"
    for marca in _TELEFONE:
        if marca in k:
            return "telefone"
    for marca in _PLACA:
        if marca in k:
            return "placa"
    for marca in _NOME:
        if marca in k:
            return "nome"
    # Identificador que carrega PII dentro (o `case_id` é montado a partir do
    # telefone do segurado). Também antes da lista segura, pelo mesmo motivo.
    if k in _IDENTIFICADOR_COM_PII:
        return "documento"
    if k in _CHAVES_SEGURAS or k.endswith(_SUFIXOS_SEGUROS):
        return "seguro"
    return "texto"


def mascarar_valor(chave: str, valor: Any) -> Any:
    """PURA. O valor de um campo, na forma que uma pessoa pode ler."""
    if valor is None or valor == "" or isinstance(valor, bool):
        return valor
    tipo = _classificar(chave)
    if tipo == "seguro":
        return valor
    if isinstance(valor, (int, float)):
        return valor if tipo == "seguro" else _cauda(valor)
    if tipo in ("documento", "telefone"):
        return _cauda(valor)
    if tipo == "placa":
        return "{PLACA}"
    if tipo == "nome":
        return "{NOME}"
    # ⚠️ FAIL-CLOSED: desconhecido é tratado como texto de pessoa. O tamanho
    # fica porque "vazio" e "duas linhas de descrição" contam histórias
    # diferentes para quem tria — e tamanho não identifica ninguém.
    return "{TEXTO:%d}" % len(str(valor))


def mascarar_slots(slots: Any) -> Dict[str, Any]:
    """PURA. O dicionário de slots do corredor, campo a campo."""
    if not isinstance(slots, dict):
        return {}
    return {k: mascarar_valor(k, v) for k, v in slots.items()}


def retrato_para_humano(session: Any) -> Dict[str, Any]:
    """PURA. O que vai para `work_steps.output_redacted`.

    🔴 NUNCA para `output_summary`. Ver o cabeçalho deste módulo, e o
    `COMMENT ON COLUMN` que a migration da FASE 0 deixou no schema.
    """
    if not isinstance(session, dict):
        return {}
    retrato: Dict[str, Any] = {}
    for chave, valor in session.items():
        if chave == "slots":
            retrato["slots"] = mascarar_slots(valor)
        elif chave == "transcript":
            # Conversa crua não entra. O total, sim: um travamento com 2 turnos
            # e um com 40 pedem investigações diferentes.
            retrato["transcript_total"] = len(valor or [])
        elif chave == "captured":
            retrato["captured"] = mascarar_slots(valor)
        elif _classificar(chave) == "seguro":
            # 🔴 A ORDEM AQUI É O CONSERTO DE UM DEFEITO MEU, e ele só apareceu
            # ao OLHAR a saída — nenhum teste o pegava.
            #
            # O ramo de estrutura abaixo vinha primeiro, e engolia `missing_slots`
            # (uma LISTA que está entre as chaves seguras) num `{LIST:1}`.
            # 📊 `missing_slots` é a informação mais útil que existe para triar
            # um travamento: diz QUAIS slots faltaram, e são nomes de campo, não
            # valores. Perdê-lo esvazia o retrato exatamente onde ele serve.
            #
            # ⚠️ `_CHAVES_SEGURAS` é curada à mão de propósito: quem acrescentar
            # uma chave aqui está declarando que ela nunca carrega valor de
            # pessoa. É a única porta por onde estrutura passa inteira.
            retrato[chave] = valor
        elif isinstance(valor, (dict, list)):
            # Estrutura desconhecida não é inspecionada campo a campo: só o
            # formato. Descer nela às cegas é como PII volta a passar.
            retrato[chave] = f"{{{type(valor).__name__.upper()}:{len(valor)}}}"
        else:
            retrato[chave] = mascarar_valor(chave, valor)
    return retrato
