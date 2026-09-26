# -*- coding: utf-8 -*-
"""SPEC-117 · O PolicyContext — a ÚNICA autoridade que monta o contexto da apólice.

Este módulo é **PURO**: sem banco, sem rede, sem `async`, sem escrita em disco.
Ele recebe o dicionário que a ferramenta `infocap_policy_lookup` devolve em
`result["data"]` e devolve o fato da apólice já reduzido à **lista branca** da
SPEC-117 §2 — o que pode atravessar o caso, ser gravado na ficha durável e, em
parte, ser mostrado ao modelo.

🔴 **A PORTA — o defeito que esta SPEC conserta.**
A porta antiga (`nodes.py:423-425`, 📊 medida em 26/09/2026) exigia
`client_document` **ou** `client_name` **crus**. No papel `attendance` o conector
devolve `client_name_masked` / `client_document_masked` e nunca os crus
(`infocap_connector._canonical_customer_identity`, `unmasked=False`), então a
porta devolvia `None` e o atendimento no WhatsApp esquecia a apólice que acabara
de encontrar. A porta nova é:

```
há ao menos UMA apólice com número humano válido
   E o cliente está identificado de ALGUMA forma:
       client_ref (codfil:codigo, sem máscara nos dois papéis)
       OU identidade crua      (só o papel core recebe)
       OU identidade mascarada (o papel do segurado recebe)
```

⛔ **Nunca no contexto:** nome, CPF/CNPJ (nem mascarado), telefone, e-mail,
endereço, placa, `policy_locator` cru, `policy_locator_ref` cru, `product` cru.
**Exceção única e explícita:** `document` e `name` crus **apenas** no papel
`core`, e só quando o `data` já os trouxe — o Chat Principal opera com dado cru
e `nodes._policy_context_tool_args` depende deles hoje. No papel `attendance`
eles **não existem** (OWASP LLM02 · LGPD · SPEC-117 §2, decisão D7).

🔴 **AS CHAVES LEGADAS SÃO DERIVADAS, E O ESCRITOR É ÚNICO.**
`policy_numbers`, `selected_policy_number`, `selected_policy_ramo`, `source`,
`document` e `name` são **derivadas** pelo mesmo construtor
(`construir_policy_context`), num **único lugar**, e existem apenas por
**compatibilidade** com os leitores que já existem em `nodes.py` (📊 linhas 1342,
1830, 1996, 2024 e `_policy_context_tool_args` na 377 — HEAD `ca8ad24`,
26/09/2026). O **campo canônico é o novo**: `apolices[]`, `selecionada`,
`cliente_ref`, `origem_por_campo`, `evidencia`. Quem for escrever leitor novo lê
o campo novo. ⛔ Não existe, e não pode existir, uma segunda função que monte as
chaves legadas (CLAUDE.md §5 — consolidar, nunca duplicar).

🔴 **`cliente_ref` é PSEUDÔNIMO, não hash nu** (decisão D3, nota 85 · ENISA,
`Pseudonymisation techniques and best practices`): HMAC-SHA256 com chave de
plataforma, material `f"{company_id}:{codfil}:{codigo}"`, hex truncado em 24.
O `company_id` entra **dentro** do material — é isso que faz o mesmo
`codfil:codigo` em duas corretoras dar pseudônimos diferentes (SPEC-117 G9).
⛔ `sha256(codigo)` sem chave está proibido: `codigo` é curto e sequencial
(📊 `"7788"` no corpus da bancada) e cai por força bruta em segundos.
⛔ A chave nunca aparece em log, exceção, retorno ou artifact.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.providers.policy_data_provider import (
    NOME_DA_FAMILIA,
    familia_de_ramo,
    normalizar_numero_humano,
    numero_humano_valido,
)
from app.services.policy_facts import _locator_hash

logger = logging.getLogger(__name__)

#: expand-first: um leitor que encontrar uma versão que não conhece trata como
#: ausência de sinal, nunca como erro.
VERSAO = 1

#: a fonte do fato — o mesmo valor que a chave legada `source` já carregava.
FONTE = "infocap_customer_catalog"

#: os papéis que recebem identidade CRUA. Espelha `infocap_tool._unmasked`
#: (📊 `infocap_tool.py:425-426`: `self.agent_role in ("", "core")`).
PAPEIS_COM_IDENTIDADE_CRUA = ("", "core")

#: 🔴 A chave do HMAC, na ordem de tentativa. `POLICY_CONTEXT_HMAC_KEY` é a
#: dedicada; `ENCRYPTION_KEY` é a chave de plataforma que **já existe** e é
#: obrigatória no runtime (`app/core/config.py:38`), lida aqui por
#: `os.getenv` para não arrastar a validação do `Settings` para um módulo puro.
CHAVES_DE_ENV_DO_HMAC = ("POLICY_CONTEXT_HMAC_KEY", "ENCRYPTION_KEY")

#: ⚠️ Último recurso, quando NENHUMA das duas está no ambiente: uma constante de
#: derivação fixa. Ela mantém o pseudônimo **estável** (o merge e a ficha
#: continuam funcionando) e mantém o isolamento por tenant (o `company_id` está
#: no material), mas **não é segredo** — quem tiver o código reconstrói o
#: pseudônimo a partir de `company_id:codfil:codigo`. 🔴 Risco registrado no
#: relatório da SPEC-117: em produção as duas variáveis existem; se um dia não
#: existirem, o `cliente_ref` deixa de ser resistente a força bruta.
DERIVACAO_SEM_CHAVE_DE_PLATAFORMA = "autobrokers:policy_context:v1:sem-chave-de-plataforma"

#: quem disse o quê — decide o empate entre o sistema de gestão e o palpite do
#: modelo (SPEC-117 §2 · D-PILOTO-11 de 17/09/2026).
ORIGEM_SISTEMA = "sistema_de_gestao"
ORIGEM_CLIENTE = "cliente"
#: 🔴 A terceira origem da §2, que só ganhou escritor no conserto único da
#: SPEC-117 (blocker B3): quem escolheu a apólice foi o SERVIÇO pedido — o
#: corredor —, não a fonte nem o segurado. Ela existe para que a ficha diga
#: **por que** aquela apólice é a do caso quando o cliente tem duas vigentes de
#: ramos diferentes e pede um encanador.
ORIGEM_CORREDOR = "corredor"

#: os campos cujo valor vem do sistema de gestão em todo contexto recém-nascido.
_CAMPOS_DO_SISTEMA = ("numapo", "ramo", "seguradora", "vigencia")

# --------------------------------------------------------------------------- #
# 🔴 A LISTA BRANCA DO QUE É DURÁVEL (SPEC-117 §2 · conserto único, blocker B1)
# --------------------------------------------------------------------------- #
#
# 📊 26/09/2026, medido pelo motor (`tool_node` real, papel `core`):
#
#     [core] PII na ficha durável: ['CPF','nome:Cliente','nome:Teste','nome:Sintetico']
#     [attendance] PII na ficha durável: nenhum
#
# A exceção do papel `core` (identidade CRUA em `document`/`name`, mais abaixo)
# é legítima **para o turno**: o Chat Principal já opera com dado cru e
# `nodes._policy_context_tool_args` depende dela. Ela nunca foi legítima para o
# que FICA GRAVADO — `attendance_ficha.novidades_da_apolice` punha o contexto
# INTEIRO em `conversations.ficha_atendimento`, que o painel do Founder lê, e
# 📊 0 de 79 fichas de `core` tinham conteúdo: o primeiro byte que esta SPEC
# escreveria lá era o CPF.
#
# 🔴 O corte é no lugar que ESCREVE, e é uma lista de PERMISSÃO, não de
# proibição — é o mesmo princípio de `infocap_tool._doc_para_o_publico`
# (📊 `infocap_tool.py:429`: *"o corte é aqui, no lugar que escreve, e não numa
# instrução que o modelo pode ignorar"*). Campo novo no contexto não vaza por
# omissão: ele simplesmente não é gravado até alguém escrevê-lo aqui.
CAMPOS_DURAVEIS = (
    "versao", "company_id", "cliente_ref", "apolices", "selecionada",
    "selecionada_pela_fonte", "origem_por_campo", "evidencia",
    # as chaves LEGADAS que os leitores de `nodes.py` ainda consomem
    "policy_numbers", "source", "selected_policy_number", "selected_policy_ramo",
)

#: e o que de CADA apólice é durável — a mesma lista branca de `_resumo_da_apolice`.
CAMPOS_DURAVEIS_DA_APOLICE = (
    "chave", "numapo", "ramo", "seguradora", "vigencia_inicio", "vigencia_fim",
    "vigente", "expirada", "cancelada",
)


def contexto_para_o_duravel(contexto: Optional[dict]) -> Optional[dict]:
    """O contexto reduzido ao que pode ser GRAVADO (SPEC-117 §2 · B1).

    🔴 Vale em **qualquer** papel: `document` e `name` crus são exceção só para
    o que o modelo vê no turno, nunca para o que fica em coluna durável.
    ⛔ Não muta o recebido.
    """
    if not isinstance(contexto, dict):
        return None
    saida: Dict[str, Any] = {}
    for campo in CAMPOS_DURAVEIS:
        if campo not in contexto:
            continue
        valor = contexto[campo]
        if campo == "apolices":
            valor = [
                {k: a[k] for k in CAMPOS_DURAVEIS_DA_APOLICE if k in a}
                for a in valor or []
                if isinstance(a, dict)
            ]
        elif isinstance(valor, dict):
            valor = dict(valor)
        elif isinstance(valor, list):
            valor = list(valor)
        saida[campo] = valor
    return saida


# --------------------------------------------------------------------------- #
# A chave do HMAC
# --------------------------------------------------------------------------- #
def _chave_pelas_configuracoes() -> str:
    """A chave pelo caminho que o RESTO do produto usa — `app.core.config`.

    🔴 SPEC-117, conserto único (blocker B8). 📊 Medido em 26/09/2026:
    `app/core/config.py:173` declara `env_file = ".env"`, e o pydantic lê o
    ARQUIVO — ele **não** popula `os.environ`. Uma chave que existe no `.env`
    era invisível para `os.getenv`, e o `cliente_ref` caía por força bruta em
    📊 **0,1 s / 7.789 tentativas** sem que nada avisasse.

    ⚠️ Import TARDIO, dentro da função, como o resto do código já faz: o módulo
    continua puro e o `Settings()` (que levanta quando a chave obrigatória
    falta) nunca é arrastado para o import deste arquivo.
    ⛔ Devolve `""` em qualquer falha — e nunca loga o valor.
    """
    try:
        from app.core.config import settings

        for nome in CHAVES_DE_ENV_DO_HMAC:
            valor = str(getattr(settings, nome, "") or "").strip()
            if valor:
                return valor
    except Exception:  # noqa: BLE001 — sem configuração o pseudônimo não para
        return ""
    return ""


def _segredo_do_hmac() -> tuple[bytes, bool]:
    """Devolve `(segredo, tem_chave_de_plataforma)`.

    ⛔ Nunca devolve, loga ou levanta exceção com o valor da chave. O segundo
    elemento diz apenas **presença/ausência** (CLAUDE.md §13.3).

    A ordem é: variável de ambiente de verdade → `app.core.config` (o `.env`) →
    a derivação sem segredo. A do ambiente vem primeiro porque é ela que um
    operador usa para ROTACIONAR a chave sem reescrever o arquivo.
    """
    for nome in CHAVES_DE_ENV_DO_HMAC:
        valor = str(os.getenv(nome) or "").strip()
        if valor:
            return valor.encode("utf-8"), True
    das_configuracoes = _chave_pelas_configuracoes()
    if das_configuracoes:
        return das_configuracoes.encode("utf-8"), True
    return DERIVACAO_SEM_CHAVE_DE_PLATAFORMA.encode("utf-8"), False


#: ⚠️ O aviso sai UMA vez por processo. Um `logger.error` por pseudônimo seria
#: um alarme por turno de atendimento — e alarme que grita sempre é desligado.
_JA_AVISOU_DA_CHAVE = [False]


def _avisar_se_a_chave_faltar() -> None:
    """🔴 O CHAMADOR de `chave_de_plataforma_presente()` (pendência 3 do juiz).

    Sem este aviso ninguém saberia que o `cliente_ref` deixou de ser resistente
    a força bruta: o produto continua funcionando, e é justamente por isso que o
    defeito é silencioso (CLAUDE.md §9.5).
    ⛔ Presença/ausência, nunca o valor (CLAUDE.md §13.3).
    """
    if _JA_AVISOU_DA_CHAVE[0] or chave_de_plataforma_presente():
        return
    _JA_AVISOU_DA_CHAVE[0] = True
    logger.error(
        "[APOLICE] nem POLICY_CONTEXT_HMAC_KEY nem ENCRYPTION_KEY estao "
        "presentes (ambiente ou .env): o cliente_ref vira derivacao SEM "
        "segredo e deixa de resistir a forca bruta — SPEC-117 D3"
    )


def _pseudonimo(material: str) -> str:
    _avisar_se_a_chave_faltar()
    segredo, _tem_chave = _segredo_do_hmac()
    return hmac.new(segredo, material.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def chave_de_plataforma_presente() -> bool:
    """Presença/ausência da chave do HMAC — para diagnóstico, nunca o valor."""
    return _segredo_do_hmac()[1]


# --------------------------------------------------------------------------- #
# cliente_ref — a identidade OPACA do cliente, isolada por tenant
# --------------------------------------------------------------------------- #
def cliente_ref(company_id: str, client_ref: Optional[Dict[str, Any]]) -> Optional[str]:
    """HMAC-SHA256 de `company_id:codfil:codigo`, hex truncado em 24.

    `None` quando falta o `company_id` ou quando a fonte não devolveu nem
    `codigo` nem `codfil`. ⚠️ `None` significa *"não sei quem é"* — e um contexto
    sem `cliente_ref` **nunca** conta como "mesmo cliente" (ver `mesmo_cliente`):
    é melhor perder a seleção anterior do que herdar a apólice de outra pessoa
    (CLAUDE.md §9.5 — o erro silencioso é o que chega ao segurado).
    """
    tenant = str(company_id or "").strip()
    if not tenant or not isinstance(client_ref, dict):
        return None
    codigo = str(client_ref.get("codigo") or "").strip()
    codfil = str(client_ref.get("codfil") or "").strip()
    if not codigo and not codfil:
        return None
    return _pseudonimo(f"{tenant}:{codfil}:{codigo}")


# --------------------------------------------------------------------------- #
# chave_da_apolice — a identidade TÉCNICA estável
# --------------------------------------------------------------------------- #
def chave_da_apolice(apolice_sanitizada: Dict[str, Any]) -> Optional[str]:
    """A chave técnica e estável de UMA apólice sanitizada.

    Preferência 1 — o hash do locator, pela função que já existe
    (`policy_facts._locator_hash`: `sha256("infocap:<codfil>:<nosnum>")[:24]`).
    Preferência 2 — 📊 o corpus da bancada traz `policy_locator = None`; sem
    locator a chave é `"h:" + sha256(numero_humano_normalizado)[:22]`.

    ⛔ A chave **nunca** é o locator cru, e nunca carrega `nosnum` nem `codfil`
    em claro — é ela que vai para a ficha durável e para o `selecionada`.
    """
    if not isinstance(apolice_sanitizada, dict):
        return None
    do_locator = _locator_hash(apolice_sanitizada)
    if do_locator:
        return do_locator
    numero = _numero_humano(apolice_sanitizada)
    if not numero:
        return None
    normalizado = normalizar_numero_humano(numero)
    if not normalizado:
        return None
    return "h:" + hashlib.sha256(normalizado.encode("utf-8")).hexdigest()[:22]


def _numero_humano(apolice_sanitizada: Dict[str, Any]) -> Optional[str]:
    """O número que se diz em voz alta, ou `None`. Usa a régua ÚNICA do projeto.

    ⛔ Não existe segunda régua de número válido: `numero_humano_valido` mora em
    `app/providers/policy_data_provider.py` e é ela que decide (CLAUDE.md §5).
    """
    for chave in ("policy_number", "numapo"):
        bruto = str(apolice_sanitizada.get(chave) or "").strip()
        if bruto and numero_humano_valido(bruto):
            return bruto
    return None


# --------------------------------------------------------------------------- #
# O construtor — a ÚNICA autoridade
# --------------------------------------------------------------------------- #
def _e_papel_com_identidade_crua(papel: Any) -> bool:
    return str(papel or "").strip().lower() in PAPEIS_COM_IDENTIDADE_CRUA


#: 🔴 Os dois sinais de CANCELAMENTO que a fonte usa — e são dois de verdade.
#: 📊 26/09/2026: `infocap_connector._sanitize_policy:890` emite `cancelled`
#: (bool) **e** `policy_status = "cancelado"`; `_sanitize_match:925` emite
#: `policy_status` e **NÃO** emite `cancelled` (medido: as chaves do
#: `_sanitize_match` real são `[... 'policy_status', 'product']`). Ler só
#: `cancelled` fazia uma apólice CANCELADA virar a apólice do caso no shape do
#: `_sanitize_match`, sem nada travar.
#:
#: ⚠️ A comparação é por PREFIXO, e a razão está aqui porque esta linha DECIDE
#: entre conteúdos (CLAUDE.md §9.5): `policy_status` é texto livre da fonte
#: (`_first_str` sobre `sit_acompanhamento_txt`/`situacao`/…), então
#: `"CANCELADO PELO CLIENTE"` tem de contar. ⛔ Já `"renovacao cancelada"` NÃO
#: conta — ali quem foi cancelada é a renovação, não a apólice, e tratar as duas
#: como iguais cancelaria contrato válido.
_PREFIXO_DE_CANCELAMENTO = "cancel"


def _cancelada(apolice_sanitizada: Dict[str, Any]) -> bool:
    """Cancelada por QUALQUER um dos dois sinais da fonte."""
    if apolice_sanitizada.get("cancelled"):
        return True
    status = str(apolice_sanitizada.get("policy_status") or "").strip().lower()
    return status.startswith(_PREFIXO_DE_CANCELAMENTO)


def _resumo_da_apolice(apolice_sanitizada: Dict[str, Any], chave: str) -> Dict[str, Any]:
    """A LISTA BRANCA de UMA apólice (SPEC-117 §2) — e nada além dela.

    ⚠️ Esta função é a única que decide o que de uma apólice atravessa. O guarda
    de PII do `test_o_policy_context_e_puro.py` a monkeypatcha de propósito para
    provar que a varredura recursiva **consegue** ficar vermelha (CLAUDE.md §9.3).

    🔴 SPEC-117, conserto único (blocker B5) — `vigente` exige TRÊS coisas:
    ```
    a fonte disse que está ativa (`active_now is True`)
      E a vigência tem FIM conhecido          ← sem data de fim é "NÃO SEI"
      E não está expirada (`expired is not True`)
      E não está cancelada por nenhum dos dois sinais
    ```
    📊 O defeito que a segunda cláusula fecha: `fimvig` ausente → o conector
    devolve `active_now=None, expired=None` → `expirada=False` → o produto
    **afirmava vigência** sobre um contrato que ele não sabia se estava valendo.
    É a mesma regra de `familia_de_ramo`, cujo `None` significa *"não sei"* e
    **nunca** *"não é"*.

    ⚠️ 26/09/2026: `vigente=False` aqui significa *"não sei / não vale"* e trava
    o que o produto AFIRMA e o que ele escolhe SOZINHO — **não** impede a
    apólice de ser a apólice do caso quando a FONTE a aponta. As duas réguas
    estão no bloco acima de `_selecionavel`.
    """
    cancelada = _cancelada(apolice_sanitizada)
    expirada = apolice_sanitizada.get("expired") is True
    fim_conhecido = bool(str(apolice_sanitizada.get("valid_to") or "").strip())
    vigente = (
        apolice_sanitizada.get("active_now") is True
        and fim_conhecido
        and not expirada
        and not cancelada
    )
    return {
        "chave": chave,
        # D2 · P0 de 25/06: o número humano é visível — é o que o segurado ouve.
        "numapo": _numero_humano(apolice_sanitizada),
        # categoria, não dado pessoal: o `product` CRU não sai daqui (17/09/2026).
        "ramo": familia_de_ramo(apolice_sanitizada.get("product")),
        "seguradora": str(apolice_sanitizada.get("insurer_key") or "").strip() or None,
        "vigencia_inicio": str(apolice_sanitizada.get("valid_from") or "").strip() or None,
        "vigencia_fim": str(apolice_sanitizada.get("valid_to") or "").strip() or None,
        "vigente": vigente,
        "expirada": expirada,
        "cancelada": cancelada,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 DUAS PERGUNTAS DIFERENTES, DUAS RÉGUAS — 26/09/2026 (SPEC-117, triagem da
#    bateria). Confundi-las é o defeito, e ele já apareceu nos dois sentidos.
# ═══════════════════════════════════════════════════════════════════════════════
#
#   "esta apólice ESTÁ VIGENTE"   → afirmação sobre COBERTURA. É o que o produto
#                                   DIZ ao segurado e o que autoriza o produto a
#                                   escolher SOZINHO. Exige fim de vigência
#                                   CONHECIDO (`vigente is True`, o aperto do
#                                   conserto B5, MANTIDO). Régua:
#                                   `_vigencia_afirmada` / `apolices_vigentes`.
#
#   "esta é a apólice DO CASO"    → qual CONTRATO estamos tratando neste
#                                   atendimento. Outra pergunta: basta que não
#                                   esteja vencida nem cancelada. Régua:
#                                   `_selecionavel`.
#
# 📊 Por que a distinção existe (medido em 26/09/2026): com `_selecionavel =
#    vigente is True`, o `data` no formato de `_sanitize_match`
#    (`{"policy_number": "1234567890", "numapo": "1234567890"}`, sem vigência —
#    pendência P-S117-11) fazia `_escolha_inicial` devolver NADA **mesmo com
#    `status: "found"` e a apólice apontada pela fonte em `selected`**:
#       `test_spec016_policy_intelligence` → "captura: selected_policy_number
#       preenchido" com `'selecionada': None`  (1 asserção)
#       `test_spec016_1_answer_quality`    → as 3 asserções D6 do contexto que
#       nasce com a apólice escolhida e a preserva
#    Ou seja: o produto PERDIA a apólice que o sistema de gestão já tinha
#    apontado — exatamente o defeito que esta SPEC existe para consertar.
#
# ⛔ O que NÃO se afrouxa: vencida e cancelada continuam fora (R5/R6 do red
#    team), `apolices_vigentes` continua devolvendo só `vigente is True`, e a
#    escolha AUTOMÁTICA por "única vigente" continua exigindo vigência
#    conhecida — sem data, o produto não escolhe sozinho; ele só aceita a que a
#    FONTE apontou.
def _selecionavel(resumo: Dict[str, Any]) -> bool:
    """🔴 Pode esta apólice ser a apólice DO CASO? (SPEC-117 G5)

    **Não cancelada E não expirada.** Vigência desconhecida NÃO impede: "não
    sei até quando vale" não é "não é este o contrato". Quem decide o que o
    produto AFIRMA sobre cobertura é `_vigencia_afirmada`, não esta função.

    ⛔ Vencida e cancelada nunca — nem sendo a única, nem a mais recente, nem
    quando a própria fonte as marcou como `selected` (R5/R6).
    """
    return not resumo.get("cancelada") and not resumo.get("expirada")


def _vigencia_afirmada(resumo: Dict[str, Any]) -> bool:
    """🔴 O produto SABE que esta apólice está vigente? (conserto B5, mantido)

    `True` só com fim de vigência conhecido e a fonte afirmando `active_now`
    (ver `_resumo_da_apolice`). É a régua de tudo que o produto **afirma** e de
    tudo que ele **escolhe sozinho**. ⛔ Nunca use `_selecionavel` para isso.
    """
    return resumo.get("vigente") is True


def _candidatas(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    matches = data.get("matches")
    if isinstance(matches, list):
        brutas = [m for m in matches if isinstance(m, dict)]
        if brutas:
            return brutas
    unica = _apolice_escolhida_pela_fonte(data)
    return [unica] if isinstance(unica, dict) else []


def _apolice_escolhida_pela_fonte(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for chave in ("selected", "policy"):
        valor = data.get(chave)
        if isinstance(valor, dict):
            return valor
    return None


def _cliente_identificado(data: Dict[str, Any]) -> bool:
    """A PORTA de identidade: `client_ref` **OU** crua **OU** mascarada.

    ⛔ Nunca "há CPF em claro" — era exatamente isso que fechava a porta no
    WhatsApp (📊 `nodes.py:423-425`, 26/09/2026).
    """
    ref = data.get("client_ref")
    if isinstance(ref, dict) and any(str(v or "").strip() for v in ref.values()):
        return True
    for chave in (
        "client_document",
        "client_name",
        "client_document_masked",
        "client_name_masked",
    ):
        if str(data.get(chave) or "").strip():
            return True
    return False


def construir_policy_context(
    data: dict, *, company_id: str, papel: str = "attendance"
) -> Optional[dict]:
    """Monta o contexto da apólice a partir do `data` da ferramenta.

    `None` quando não há apólice com número humano válido, quando o cliente não
    está identificado de nenhuma forma, ou quando falta o `company_id` — sem
    tenant não há contexto que se possa amarrar a uma corretora (CLAUDE.md §7).
    """
    if not isinstance(data, dict):
        return None
    tenant = str(company_id or "").strip()
    if not tenant:
        return None
    if not _cliente_identificado(data):
        return None

    apolices: List[Dict[str, Any]] = []
    chaves_vistas: set[str] = set()
    for bruta in _candidatas(data):
        if not _numero_humano(bruta):
            continue
        chave = chave_da_apolice(bruta)
        if not chave or chave in chaves_vistas:
            continue
        chaves_vistas.add(chave)
        apolices.append(_resumo_da_apolice(bruta, chave))
    if not apolices:
        return None

    contexto: Dict[str, Any] = {
        "versao": VERSAO,
        "company_id": tenant,
        "cliente_ref": cliente_ref(tenant, data.get("client_ref")),
        "apolices": apolices,
        "selecionada": None,
        "origem_por_campo": {campo: ORIGEM_SISTEMA for campo in _CAMPOS_DO_SISTEMA},
        "evidencia": {
            "fonte": FONTE,
            "consultado_em": datetime.now(timezone.utc).isoformat(),
        },
    }

    escolhida, pela_fonte = _escolha_inicial(data, apolices)
    if escolhida:
        contexto["selecionada"] = escolhida
        contexto["origem_por_campo"]["selecionada"] = ORIGEM_SISTEMA
        # 🔴 SPEC-117, conserto único (B6): "a FONTE apontou esta" e "sobrou só
        #    esta na lista" são as duas do sistema de gestão — e decidem coisas
        #    OPOSTAS numa fusão. Ver `fundir`.
        contexto["selecionada_pela_fonte"] = pela_fonte

    _derivar_chaves_legadas(contexto, data=data, papel=papel)
    return contexto


def _escolha_inicial(data: Dict[str, Any],
                     apolices: List[Dict[str, Any]]) -> tuple[Optional[str], bool]:
    """A seleção automática — e só ela. Devolve `(chave, escolhida_pela_fonte)`.

    1. a fonte já escolheu (`selected`, com `status` "found" ou ausente) e a
       escolhida é selecionável (não vencida, não cancelada) → é ela, e
       `pela_fonte=True`. 🔴 Aqui vigência DESCONHECIDA passa: quem aponta é o
       sistema de gestão, e recusar seria perder a apólice do caso por falta de
       um campo que a fonte não mandou;
    2. existe exatamente UMA apólice de vigência AFIRMADA → é ela, sem
       perguntar, e `pela_fonte=False` — ninguém a APONTOU, ela só foi a que
       sobrou. 🔴 Este ramo exige `_vigencia_afirmada`, não `_selecionavel`:
       sem saber até quando vale, o produto **não escolhe sozinho**;
    3. caso contrário `(None, False)` — duas vigentes (do mesmo ramo ou de ramos
       diferentes) exigem desambiguação, e quem escolhe pelo ramo é o PEDIDO
       (`apolices_vigentes(contexto, ramo=…)`), nunca o construtor.

    🔴 A diferença entre 1 e 2 parece cosmética e não é: numa fusão, "a fonte
    apontou esta outra" é informação nova e legítima, enquanto "sobrou esta"
    seria trocar a apólice do caso porque a antiga venceu — o escorregão
    silencioso do B6.
    """
    por_chave = {a["chave"]: a for a in apolices}

    status = str(data.get("status") or "").strip().lower()
    if status in ("", "found"):
        da_fonte = _apolice_escolhida_pela_fonte(data)
        if isinstance(da_fonte, dict):
            chave = chave_da_apolice(da_fonte)
            resumo = por_chave.get(chave or "")
            if resumo and _selecionavel(resumo):
                return resumo["chave"], True

    # 🔴 `_vigencia_afirmada`, e NÃO `_selecionavel`: escolher sozinho é uma
    #    AFIRMAÇÃO do produto ("esta é a sua apólice, e ela vale"), e afirmação
    #    exige vigência conhecida (conserto B5). Uma apólice sem data de fim só
    #    se torna a apólice do caso se a FONTE a apontar (ramo 1 acima) ou se
    #    alguém escolher (`escolher_apolice`).
    vigentes = [a for a in apolices if _vigencia_afirmada(a)]
    if len(vigentes) == 1:
        return vigentes[0]["chave"], False
    return None, False


def _derivar_chaves_legadas(
    contexto: Dict[str, Any], *, data: Dict[str, Any], papel: str
) -> None:
    """🔴 As chaves LEGADAS, num único lugar (ver o docstring do módulo).

    Derivadas de `apolices`/`selecionada`; existem por compatibilidade com os
    leitores atuais de `nodes.py`. ⛔ Nenhuma outra função as monta.
    """
    numeros = sorted({a["numapo"] for a in contexto["apolices"] if a.get("numapo")})
    contexto["policy_numbers"] = numeros
    contexto["source"] = FONTE

    selecionada = apolice_selecionada(contexto)
    if selecionada:
        if selecionada.get("numapo"):
            contexto["selected_policy_number"] = selecionada["numapo"]
        if selecionada.get("ramo"):
            contexto["selected_policy_ramo"] = selecionada["ramo"]

    # ⛔ A ÚNICA exceção da lista branca: identidade crua, só no papel `core`, e
    #    só quando o `data` já a trouxe (o papel mascarado nunca a tem).
    if _e_papel_com_identidade_crua(papel):
        documento = str(data.get("client_document") or "").strip()
        nome = str(data.get("client_name") or "").strip()
        if documento:
            contexto["document"] = documento
        if nome:
            contexto["name"] = nome


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #
def apolice_selecionada(contexto: Optional[dict]) -> Optional[dict]:
    """A apólice do caso, ou `None`. LEITURA ÚNICA — ninguém varre a lista."""
    if not isinstance(contexto, dict):
        return None
    chave = str(contexto.get("selecionada") or "").strip()
    if not chave:
        return None
    for apolice in contexto.get("apolices") or []:
        if isinstance(apolice, dict) and apolice.get("chave") == chave:
            return apolice
    return None


def apolices_vigentes(contexto: Optional[dict], ramo: Optional[str] = None) -> List[dict]:
    """As apólices VIGENTES, opcionalmente de um ramo.

    O `ramo` aceita a família (`"resi"`) ou o nome humano (`"residencial"`) — a
    normalização é a de `familia_de_ramo`, a mesma régua do resto do projeto.
    """
    if not isinstance(contexto, dict):
        return []
    vigentes = [
        a
        for a in contexto.get("apolices") or []
        if isinstance(a, dict) and a.get("vigente")
    ]
    pedido = str(ramo or "").strip()
    if not pedido:
        return vigentes
    familia = familia_de_ramo(pedido) or pedido.lower()
    return [a for a in vigentes if a.get("ramo") == familia]


def nome_humano_do_ramo(ramo: Optional[str]) -> Optional[str]:
    """`"resi"` → `"residencial"`. 💭 copy; usa o dicionário único do projeto."""
    chave = str(ramo or "").strip().lower()
    if not chave:
        return None
    return NOME_DA_FAMILIA.get(chave, chave)


# --------------------------------------------------------------------------- #
# Escolha e fusão
# --------------------------------------------------------------------------- #
def _com_selecionada(contexto: Dict[str, Any], chave: str, origem: str) -> Dict[str, Any]:
    """Um contexto NOVO com a seleção trocada. ⛔ Não muta o recebido."""
    novo: Dict[str, Any] = dict(contexto)
    novo["apolices"] = [dict(a) for a in contexto.get("apolices") or [] if isinstance(a, dict)]
    novo["origem_por_campo"] = dict(contexto.get("origem_por_campo") or {})
    novo["evidencia"] = dict(contexto.get("evidencia") or {})
    novo["selecionada"] = chave
    novo["origem_por_campo"]["selecionada"] = origem
    # 🔴 B6: uma escolha explícita (o segurado, o corredor, ou a preservação da
    #    escolha anterior) NÃO é "a fonte apontou nesta consulta".
    novo["selecionada_pela_fonte"] = False
    novo.pop("selected_policy_number", None)
    novo.pop("selected_policy_ramo", None)
    escolhida = apolice_selecionada(novo)
    if escolhida:
        if escolhida.get("numapo"):
            novo["selected_policy_number"] = escolhida["numapo"]
        if escolhida.get("ramo"):
            novo["selected_policy_ramo"] = escolhida["ramo"]
    return novo


def escolher_apolice(contexto: dict, chave: str,
                     origem: str = ORIGEM_CLIENTE) -> dict:
    """Alguém escolheu uma apólice para este caso. Devolve contexto NOVO.

    `ValueError` quando a chave não está no contexto ou quando a apólice não é
    selecionável — 🔴 vencida ou cancelada nunca é a apólice do caso
    (SPEC-117 G5). ⚠️ Vigência DESCONHECIDA é aceita: ver o bloco "duas
    perguntas diferentes, duas réguas" acima de `_selecionavel` (26/09/2026).
    Escolher é dizer *"o caso é sobre este contrato"*, não *"este contrato está
    coberto"* — e recusar aqui fazia o produto perder a apólice que o sistema de
    gestão já tinha apontado.

    O `origem` diz QUEM escolheu, e é isso que a ficha grava em
    `origem_por_campo["selecionada"]`: `ORIGEM_CLIENTE` (o segurado escolheu),
    `ORIGEM_CORREDOR` (o SERVIÇO pedido escolheu — o encanador só pode sair na
    residencial) ou `ORIGEM_SISTEMA` (a fonte já vinha escolhida).
    """
    if not isinstance(contexto, dict):
        raise ValueError("contexto de apolice ausente: nao ha o que escolher")
    procurada = str(chave or "").strip()
    if not procurada:
        raise ValueError("chave de apolice vazia: informe a chave tecnica da apolice")
    for apolice in contexto.get("apolices") or []:
        if not isinstance(apolice, dict) or apolice.get("chave") != procurada:
            continue
        # 🔴 A régua é `_selecionavel`, uma só; as duas mensagens abaixo só
        #    EXPLICAM o "não" dela. ⛔ Não existe um terceiro `if` aqui: com
        #    `_selecionavel` = não cancelada E não expirada, ele seria código
        #    morto (protocolo §0.3), e código morto mente sobre a regra.
        if not _selecionavel(apolice):
            if apolice.get("cancelada"):
                raise ValueError(
                    "a apolice %s esta CANCELADA e nao pode ser a apolice do caso"
                    % (apolice.get("numapo") or procurada)
                )
            raise ValueError(
                "a apolice %s esta VENCIDA e nao pode ser a apolice do caso"
                % (apolice.get("numapo") or procurada)
            )
        return _com_selecionada(contexto, procurada, origem)
    raise ValueError(
        "a chave %r nao corresponde a nenhuma apolice deste contexto "
        "(a chave e tecnica e opaca, nunca o numero humano da apolice)" % (procurada,)
    )


def mesmo_cliente(anterior: Optional[dict], novo: Optional[dict]) -> bool:
    """"É a mesma pessoa?" — sobre identidade OPACA, nunca sobre nome ou CPF.

    Exige o MESMO `company_id` **e** o mesmo `cliente_ref`. Sem `cliente_ref`
    (a fonte não devolveu `codigo`/`codfil`) a resposta é `False`: não se herda
    apólice de quem não se sabe se é a mesma pessoa.
    """
    if not isinstance(anterior, dict) or not isinstance(novo, dict):
        return False
    tenant_a = str(anterior.get("company_id") or "").strip()
    tenant_b = str(novo.get("company_id") or "").strip()
    if not tenant_a or tenant_a != tenant_b:
        return False
    ref_a = str(anterior.get("cliente_ref") or "").strip()
    ref_b = str(novo.get("cliente_ref") or "").strip()
    return bool(ref_a) and ref_a == ref_b


def fundir(anterior: Optional[dict], novo: Optional[dict]) -> Optional[dict]:
    """A regra da SPEC-016.1 D6, agora sobre identidade opaca.

    · `novo` ausente → devolve o `anterior` **intacto**: uma consulta que não
      trouxe nada não apaga a apólice do caso.
    · `company_id` diferente → devolve o `novo`. ⛔ Nunca mistura apólices de
      corretoras diferentes (CLAUDE.md §7).
    · cliente diferente → o `novo` substitui o contexto inteiro.
    · MESMO cliente, consulta sem seleção → preserva a apólice selecionada se
      ela ainda está na lista nova **e** continua selecionável.
    """
    if not isinstance(novo, dict):
        return anterior if isinstance(anterior, dict) else None
    if not isinstance(anterior, dict):
        return novo
    if str(anterior.get("company_id") or "").strip() != str(novo.get("company_id") or "").strip():
        return novo
    if not mesmo_cliente(anterior, novo):
        return novo

    chave_anterior = str(anterior.get("selecionada") or "").strip()
    if not chave_anterior:
        return novo
    for apolice in novo.get("apolices") or []:
        if not isinstance(apolice, dict) or apolice.get("chave") != chave_anterior:
            continue
        if not _selecionavel(apolice):
            break
        origem = str(
            (anterior.get("origem_por_campo") or {}).get("selecionada") or ORIGEM_SISTEMA
        )
        return _com_selecionada(novo, chave_anterior, origem)

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔴 SPEC-117, conserto único (blocker B6) — AQUI A APÓLICE DO CASO CAIU.
    # ═══════════════════════════════════════════════════════════════════════════
    # A escolhida venceu, foi cancelada ou saiu da lista da consulta nova. Duas
    # saídas, e só uma delas é honesta:
    #
    #   · a FONTE apontou outra nesta consulta  → é informação nova: vale ela;
    #   · a nova "sobrou" como única vigente    → ninguém escolheu. 📊 Medido:
    #         anterior.selecionada -> 'A-0001' (auto)
    #         depois de A-0001 vencer     : selecionada='R-0002'  (resi!)
    #         depois de A-0001 desaparecer: selecionada='R-0002'
    #     e o acionamento seguinte sairia com o ramo e a seguradora de OUTRO
    #     contrato, sem avisar ninguém (CLAUDE.md §9.5).
    #
    # ⛔ Nunca escorregar para outra sozinho. Quando o produto deixa de saber, ele
    # volta a NÃO saber — e quem não sabe pergunta.
    if novo.get("selecionada") and novo.get("selecionada_pela_fonte") is True:
        return novo
    if not novo.get("selecionada"):
        return novo
    return _sem_selecao(
        novo, "a apolice do caso deixou de ser elegivel ou saiu da lista")


def _sem_selecao(contexto: Dict[str, Any], motivo: str) -> Dict[str, Any]:
    """🔴 O caso volta a NÃO ter apólice escolhida (SPEC-117, conserto único B6).

    📊 O defeito, medido pelo red team em 26/09/2026:
    ```
    anterior.selecionada -> 'A-0001' (auto)
    depois de A-0001 vencer     : selecionada='R-0002'   (a resi, de outro ramo)
    depois de A-0001 desaparecer: selecionada='R-0002'
    ```
    O `fundir` recusava corretamente herdar a vencida — e devolvia o `novo`,
    cuja auto-escolha *"única vigente"* fixava **outro contrato, de outro
    ramo**, sem avisar ninguém. O acionamento seguinte saía com o ramo e a
    seguradora dessa outra apólice.

    ⛔ Escorregar para outra apólice sozinho é decidir pelo segurado. Quando a
    escolhida deixa de valer, o produto volta a **não saber** — e quem não sabe
    pergunta. A lista continua inteira no contexto; só a escolha cai.
    """
    logger.info("[APOLICE] %s: o caso volta a NAO ter apolice escolhida", motivo)
    limpo: Dict[str, Any] = dict(contexto)
    limpo["apolices"] = [dict(a) for a in contexto.get("apolices") or []
                         if isinstance(a, dict)]
    limpo["origem_por_campo"] = {
        k: v for k, v in (contexto.get("origem_por_campo") or {}).items()
        if k != "selecionada"
    }
    limpo["evidencia"] = dict(contexto.get("evidencia") or {})
    limpo["selecionada"] = None
    limpo["selecionada_pela_fonte"] = False
    limpo.pop("selected_policy_number", None)
    limpo.pop("selected_policy_ramo", None)
    return limpo
