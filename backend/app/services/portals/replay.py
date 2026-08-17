# -*- coding: utf-8 -*-
"""Fixtures e replay como contrato de onboarding — SPEC-075 Bloco J (§19).

Este módulo é **puro**: sem rede, sem Supabase, sem Playwright, sem I/O no
import. Ele existe para que uma journey possa ser provada sem o portal real, e
para que a prova valha alguma coisa.

O que ele faz
=============
    A) `ManifestoDeFixture` + `validar_manifesto()`  ..... §19.2
    B) `varredura_de_pii()`                          ..... §19.3
    C) `ReplayDeSessao`                              ..... §19.1
    D) `replay_read_only()` / `replay_com_efeito()`  ..... §19.4 e §19.5

O que ele NÃO é
===============
Não é um executor. Não existe, em nenhum caminho deste arquivo, uma linha que
faça uma requisição sair da máquina. `EfeitoMaterialRegistrado.executado` é
`False` por construção, e se um dia alguém precisar escrever `True` ali, o
replay virou executor e a SPEC-075 §44 foi violada — *"não ativar operação
material apenas porque fixture passou"*.

🔴 POR QUE O REPLAY DE EFEITO É A PARTE QUE IMPORTA
====================================================
Um replay que deixa passar um efeito **não previsto** é pior que não ter
replay: ele produz um relatório verde sobre uma journey que, em produção,
abriria um atendimento pago no nome de um segurado real. A confiança que ele
cria é a autorização que alguém vai usar para ligar operação material.

Por isso a interceptação aqui **não depende da cooperação da journey**. Não
basta ter uma porta educada (`efeito_material()`) e confiar que todo mundo bate
nela: qualquer `requisitar()` com verbo de escrita que a fixture não previu
estoura `EfeitoNaoPrevisto`. Uma interceptação que só funciona quando o código
colabora não protege de nada — protege só de quem já ia se comportar.

🔴 POR QUE O DETECTOR DE PII TEM DE ACHAR O QUE NÃO ESTÁ FORMATADO
===================================================================
CPF em corpo de API chega `"52998224725"`, não `"529.982.247-25"`. Um detector
que só acha o que está bonito não guarda nada e, pior, **parece** guardar: ele
nunca acusa, ninguém percebe que está quebrado, e a primeira vez que se descobre
é quando o CPF já está no Git. Todos os padrões daqui tratam as duas formas, e
o `mod-11` do CPF/CNPJ é o que separa "número com cara de documento" de
"documento que pertence a alguém".

O redator é o da casa — e o fallback é MAIS estrito
====================================================
A verificação de segredo por NOME DE CHAVE é do `portal_worker.redaction`, o
sanitizador único da casa (SPEC-073 Bloco H). Não há um segundo aqui.

O import é tolerante porque este módulo é importável de contexto que não tem
`portal_worker` no `sys.path` — ferramenta de fixture, script de factory, teste
de contrato do pacote `app`. **Mas o fallback endurece, não afrouxa**: sem o
redator da casa, a varredura entra em modo paranoico permanente e promove todo
achado `revisar` a `bloqueia`. A razão é a única que importa aqui: se afrouxar
fosse o comportamento, um `ImportError` silencioso viraria a maneira mais fácil
de aprovar uma fixture suja — e ninguém percebe um import que falhou em
silêncio. O caminho degradado tem de ser o caminho chato.

Uma divergência canônica que este módulo NÃO resolve sozinho
=============================================================
§16.1 lista `expected_state` como `success | business_blocked | needs_connection
| …`; o `contracts.py` já implementado usa `ok | portal_blocked | no_connection
| …`. São dois vocabulários para a mesma coisa. Aqui os dois são aceitos e
traduzidos por `EQUIVALENCIA_DE_ESTADO`, e os estados de §16.1 que não têm par
implementado (`auth_expired`, `rate_limited`, `portal_changed`,
`transient_failure`) traduzem para `""` em vez de ganharem um par inventado.
Escolher um dos dois vocabulários é decisão canônica, não de arquivo.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# ==========================================================================
# O redator único da casa — importado, nunca reescrito
# ==========================================================================
try:  # pragma: no cover - o caminho feliz é o único exercitado nos testes
    from portal_worker.redaction import (  # type: ignore
        chave_e_sensivel as _chave_e_sensivel_da_casa,
        digest as _digest_da_casa,
        shape_of as _shape_of_da_casa,
    )
    REDATOR_DISPONIVEL = True
    REDATOR_EM_USO = "portal_worker.redaction"
except Exception:  # noqa: BLE001 - qualquer falha de import cai no modo chato
    REDATOR_DISPONIVEL = False
    REDATOR_EM_USO = "fallback_estrito"

    # 🔴 O fallback é DELIBERADAMENTE curto e burro. Ele não tenta imitar o
    # redator: ele responde "sim" para mais coisas. Uma lista menor que
    # `CHAVES_SENSIVEIS` seria afrouxamento; o critério aqui é um substring
    # genérico que acusa até `codigo_de_acesso` e `x-qualquer-token`.
    _RADICAIS_DO_FALLBACK = (
        "auth", "cookie", "token", "senha", "password", "passwd", "secret",
        "credential", "apikey", "api_key", "api-key", "bearer", "jwt",
        "session", "sessao", "storage_state", "csrf", "xsrf", "assinatura",
        "signature", "pin",
    )

    def _chave_e_sensivel_da_casa(chave: Any) -> bool:  # type: ignore[misc]
        k = str(chave or "").strip().lower()
        return bool(k) and any(r in k for r in _RADICAIS_DO_FALLBACK)

    def _digest_da_casa(valor: str) -> str:  # type: ignore[misc]
        return hashlib.sha256(str(valor).encode("utf-8", "ignore")).hexdigest()[:8]

    def _shape_of_da_casa(valor: Any, **_kw: Any) -> Any:  # type: ignore[misc]
        return f"<{type(valor).__name__}>"


# ==========================================================================
# Vocabulário — importado do registry, nunca redefinido
# ==========================================================================
# 🔴 Duas listas de "o que é efeito material" divergem no primeiro dia em que
# alguém acrescenta um valor numa e esquece a outra. O `journeys/__init__` já é
# dono desse vocabulário (e ele próprio o toma do `guardrails`). Aqui é reuso.
try:  # pragma: no cover
    from portal_worker.journeys import (  # type: ignore
        MATERIAL_SIDE_EFFECT as _MATERIAL_SIDE_EFFECT,
        READ_ONLY as _READ_ONLY,
        REVERSIBLE_UI as _REVERSIBLE_UI,
    )
except Exception:  # noqa: BLE001
    _READ_ONLY = "read_only"
    _REVERSIBLE_UI = "reversible_ui"
    _MATERIAL_SIDE_EFFECT = "material_side_effect"


# ==========================================================================
# A) CONTRATO DE FIXTURE — §19.2
# ==========================================================================
EFEITO_READ = "read"
EFEITO_MATERIAL = "material"

# O manifesto é binário (`read` | `material`) porque é isso que §19.2 escreve.
# 🔴 `reversible_ui` traduz para `material`: entre as duas leituras possíveis de
# um valor intermediário, a que protege mais é a que vale (§9.2, "nunca relaxar
# proteção por divergência").
_ALIAS_DE_EFEITO: Dict[str, str] = {
    "read": EFEITO_READ,
    "read_only": EFEITO_READ,
    "readonly": EFEITO_READ,
    "leitura": EFEITO_READ,
    _READ_ONLY: EFEITO_READ,
    "material": EFEITO_MATERIAL,
    "material_side_effect": EFEITO_MATERIAL,
    "write": EFEITO_MATERIAL,
    "escrita": EFEITO_MATERIAL,
    "reversible_ui": EFEITO_MATERIAL,
    _REVERSIBLE_UI: EFEITO_MATERIAL,
    _MATERIAL_SIDE_EFFECT: EFEITO_MATERIAL,
}

# Fontes conhecidas. A lista é ADVISORY — uma fonte nova não deve travar uma
# fixture legítima —, com uma exceção que é regra dura logo abaixo.
FONTE_HAR_SANITIZADO = "founder_har_sanitized"
FONTE_PROFILER = "profiler_sanitized"
FONTE_SINTETICA = "synthetic"
FONTE_DOC = "portal_doc"

FONTES_CONHECIDAS: Tuple[str, ...] = (
    FONTE_HAR_SANITIZADO, FONTE_PROFILER, FONTE_SINTETICA, FONTE_DOC,
)

# Vocabulário de `expected_state` como §16.1 o escreve.
ESTADOS_DA_SPEC: Tuple[str, ...] = (
    "success", "needs_human", "business_blocked", "not_supported",
    "needs_connection", "auth_expired", "rate_limited", "portal_changed",
    "transient_failure", "maybe_committed", "failed",
)

# Tradução para o vocabulário IMPLEMENTADO em `contracts.py`. Só os pares de que
# se tem certeza. `""` significa "não existe equivalente hoje" — e é melhor
# devolver o vazio honesto do que inventar um mapeamento que vira verdade.
EQUIVALENCIA_DE_ESTADO: Dict[str, str] = {
    "success": "ok",
    "needs_human": "needs_human",
    "business_blocked": "portal_blocked",
    "not_supported": "not_supported",
    "needs_connection": "no_connection",
    "maybe_committed": "maybe_committed",
    "failed": "failed",
    "auth_expired": "",
    "rate_limited": "",
    "portal_changed": "",
    "transient_failure": "",
    # o outro lado da tabela, para quem já escreve no vocabulário implementado
    "ok": "ok",
    "nothing_to_do": "nothing_to_do",
    "portal_blocked": "portal_blocked",
    "no_connection": "no_connection",
    "not_authorized": "",
}

_RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?")

_CAMPOS_OBRIGATORIOS: Tuple[str, ...] = (
    "portal_key", "journey_key", "operation_key", "captured_at",
    "source", "pii", "secrets", "effect", "expected_state",
)


@dataclass
class ManifestoDeFixture:
    """O `manifest.json` de §19.2, com tipo.

    Não é decoração: é o que permite a um humano abrir uma pasta de fixture
    seis meses depois e responder *"isto foi medido ou foi inventado?"* sem
    reabrir o HAR — que, por §19.3, não está mais em lugar nenhum.
    """

    portal_key: str
    journey_key: str
    operation_key: str
    captured_at: str
    source: str
    pii: str = "removed"
    secrets: str = "removed"
    effect: str = EFEITO_READ
    expected_state: str = "success"
    case_key: str = ""
    notas: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)

    # -- leitura ----------------------------------------------------------
    @property
    def e_material(self) -> bool:
        return normalizar_efeito(self.effect) == EFEITO_MATERIAL

    @property
    def citavel_como_medicao(self) -> bool:
        """📊 ou 💭 — CLAUDE.md §12.1, aplicado à fixture.

        Fixture derivada de captura real sustenta um número medido. Fixture
        `synthetic` foi construída a partir do schema e **não** pode ser citada
        como medição em SPEC, relatório ou prompt. A pergunta é frequente e a
        resposta estava só na cabeça de quem escreveu o arquivo.
        """
        return str(self.source or "").strip().lower() in (
            FONTE_HAR_SANITIZADO, FONTE_PROFILER)

    @property
    def estado_no_vocabulario_implementado(self) -> str:
        """`expected_state` traduzido para o enum de `contracts.py`, ou `""`."""
        return EQUIVALENCIA_DE_ESTADO.get(
            str(self.expected_state or "").strip().lower(), "")

    @property
    def chave(self) -> str:
        base = f"{self.portal_key}.{self.journey_key}"
        return f"{base}.{self.case_key}" if self.case_key else base

    # -- conversão --------------------------------------------------------
    @classmethod
    def de_dict(cls, bruto: Any) -> "ManifestoDeFixture":
        """Constrói sem validar. Quem valida é `validar_manifesto()`.

        Separado de propósito: construir e julgar na mesma função obriga a
        levantar exceção para relatar problema, e um relatório de problemas é
        muito mais útil que a primeira exceção.
        """
        d = dict(bruto or {})
        conhecidos = set(_CAMPOS_OBRIGATORIOS) | {"case_key", "notas", "extras"}
        return cls(
            portal_key=str(d.get("portal_key") or ""),
            journey_key=str(d.get("journey_key") or ""),
            operation_key=str(d.get("operation_key") or ""),
            captured_at=str(d.get("captured_at") or ""),
            source=str(d.get("source") or ""),
            pii=str(d.get("pii") or ""),
            secrets=str(d.get("secrets") or ""),
            effect=str(d.get("effect") or ""),
            expected_state=str(d.get("expected_state") or ""),
            case_key=str(d.get("case_key") or ""),
            notas=str(d.get("notas") or ""),
            extras={k: v for k, v in d.items() if k not in conhecidos},
        )

    def para_dict(self) -> Dict[str, Any]:
        saida: Dict[str, Any] = {
            "portal_key": self.portal_key,
            "journey_key": self.journey_key,
            "operation_key": self.operation_key,
            "captured_at": self.captured_at,
            "source": self.source,
            "pii": self.pii,
            "secrets": self.secrets,
            "effect": self.effect,
            "expected_state": self.expected_state,
        }
        if self.case_key:
            saida["case_key"] = self.case_key
        if self.notas:
            saida["notas"] = self.notas
        saida.update(self.extras or {})
        return saida


def normalizar_efeito(valor: Any) -> str:
    """`read` ou `material`. Valor desconhecido vira `material`.

    🔴 O default do desconhecido é o lado protegido. Um `effect` com erro de
    digitação não pode fazer uma journey material ser replayada como leitura —
    seria exatamente o afrouxamento que §9.2 proíbe.
    """
    v = str(valor or "").strip().lower()
    return _ALIAS_DE_EFEITO.get(v, EFEITO_MATERIAL)


def validar_manifesto(bruto: Any) -> Tuple[bool, List[str]]:
    """`(ok, problemas)` — §19.2 e §19.3 conferidos juntos.

    Junta as duas conferências de propósito: um manifesto que declara
    `"pii": "removed"` e traz um CPF no próprio corpo é o caso mais comum de
    fixture suja, porque ninguém revisa o manifesto — ele "é só metadado".
    """
    problemas: List[str] = []

    if not isinstance(bruto, dict):
        return False, ["manifesto nao e um objeto JSON"]

    for campo in _CAMPOS_OBRIGATORIOS:
        if not str(bruto.get(campo) or "").strip():
            problemas.append(f"campo obrigatorio ausente ou vazio: `{campo}`")

    m = ManifestoDeFixture.de_dict(bruto)

    # §19.3 é categórico: não existe fixture com PII/segredo "presente".
    if str(m.pii).strip().lower() not in ("removed", "none", "n/a"):
        problemas.append(
            f"`pii` deve ser `removed` (veio `{m.pii}`): SPEC-075 §19.3 nao "
            "admite fixture com PII declarada")
    if str(m.secrets).strip().lower() not in ("removed", "none", "n/a"):
        problemas.append(
            f"`secrets` deve ser `removed` (veio `{m.secrets}`): §19.3 lista "
            "Authorization, Cookie, JWT e token_autorizacao como nunca-comitar")

    efeito_bruto = str(m.effect or "").strip().lower()
    if efeito_bruto and efeito_bruto not in _ALIAS_DE_EFEITO:
        problemas.append(
            f"`effect` desconhecido (`{m.effect}`): tratado como `material` "
            "por seguranca, mas escreva `read` ou `material`")

    estado = str(m.expected_state or "").strip().lower()
    if estado and estado not in EQUIVALENCIA_DE_ESTADO:
        problemas.append(
            f"`expected_state` fora do vocabulario (`{m.expected_state}`): "
            f"§16.1 admite {', '.join(ESTADOS_DA_SPEC)}")

    if m.captured_at and not _RE_DATA_ISO.match(m.captured_at.strip()):
        problemas.append(
            f"`captured_at` deve ser ISO `AAAA-MM-DD` (veio `{m.captured_at}`)")

    fonte = str(m.source or "").strip().lower()
    if fonte and fonte not in FONTES_CONHECIDAS:
        problemas.append(
            f"`source` desconhecida (`{m.source}`): as conhecidas sao "
            f"{', '.join(FONTES_CONHECIDAS)} — se for nova, registre-a")

    # O próprio manifesto passa pelo guarda.
    for achado in varredura_de_pii(bruto):
        if achado.bloqueia:
            problemas.append(f"PII/segredo no proprio manifesto — {achado}")

    return (not problemas), problemas


# ==========================================================================
# B) VARREDURA DE PII — §19.3
# ==========================================================================
SEVERIDADE_BLOQUEIA = "bloqueia"
SEVERIDADE_REVISAR = "revisar"


@dataclass(frozen=True)
class Achado:
    """Um pedaço de coisa que não pode entrar numa fixture.

    🔴 `amostra` NUNCA é o valor. Um relatório de vazamento que reimprime o
    vazamento cria a segunda cópia — e essa vai para o log de CI, que ninguém
    trata como dado sensível. O que o achado entrega é: onde está (`caminho`),
    o que parece ser (`tipo`), e uma impressão digital estável (`impressao`),
    que responde *"é o mesmo valor daquele outro campo?"* sem exibir nenhum.
    """

    tipo: str
    caminho: str
    severidade: str = SEVERIDADE_BLOQUEIA
    motivo: str = ""
    amostra: str = ""
    impressao: str = ""

    @property
    def bloqueia(self) -> bool:
        return self.severidade == SEVERIDADE_BLOQUEIA

    def __str__(self) -> str:
        return (f"[{self.severidade}] {self.tipo} em `{self.caminho}` "
                f"({self.amostra}) — {self.motivo}")


# Domínios que RFC 2606/6761 e o costume da casa reservam para exemplo. E-mail
# nesses domínios não é de ninguém, então não é PII.
DOMINIOS_DE_EXEMPLO: Tuple[str, ...] = (
    "example.com", "example.org", "example.net", "example.edu",
    "exemplo.com", "exemplo.com.br", "exemplo.br", "exemplo.org",
    "teste.com", "teste.com.br", "test.com", "localhost",
    "autobrokers.test", "email.com.br.invalid",
)
_SUFIXOS_DE_EXEMPLO: Tuple[str, ...] = (
    ".example", ".test", ".invalid", ".localhost", ".exemplo",
)

# Chaves que o redator da casa não conhece mas que, no contexto de FIXTURE,
# guardam segredo. Não é um segundo sanitizador: é o complemento declarado.
# `Token` puro, por exemplo, não casa nenhum item de `CHAVES_SENSIVEIS`
# (a lista tem `access_token`, `refresh_token`, `token_autorizacao`), e é
# exatamente o nome que o Maxpar usa para o token de sessão do atendimento.
CHAVES_EXTRA_DE_FIXTURE: Tuple[str, ...] = (
    "token", "senha", "cookie", "auth", "sessao", "session",
    "assinatura", "signature", "codigo_acesso", "codigoacesso", "pin",
)

VERBOS_MATERIAIS: Tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")

# --------------------------------------------------------------------------
# Padrões. A ordem é a regra: do mais específico ao mais genérico, e cada
# trecho já casado é CONSUMIDO, para o padrão seguinte não reclassificar o
# mesmo dado (senão um CNPJ de 14 dígitos vira "cartão" e o relatório manda
# consertar a coisa errada).
# --------------------------------------------------------------------------
_P_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}")
_P_ESQUEMA_AUTH = re.compile(r"(?i)\b(?:bearer|basic)\s+([A-Za-z0-9+/=._\-]{8,})")
_P_COOKIE_INLINE = re.compile(r"(?i)\b(?:set-)?cookie\s*[:=]\s*([^\s;]{6,})")
_P_SEGREDO_INLINE = re.compile(
    r"(?i)\b(?:senha|password|passwd|pwd|secret|api[_-]?key|token)"
    r"\s*[:=]\s*[\"']?([^\s,;\"'}\]]{4,})")
_P_CHAVE_DE_PROVEDOR = re.compile(
    r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}\b"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}\b"
    r"|\bxox[baprs]-[A-Za-z0-9-]{10,}\b"
    r"|\bAKIA[0-9A-Z]{16}\b")
# Blob longo: base64 ou hex de digest/sessão. 40 é o piso que separa "token"
# de "identificador de negócio comprido".
_P_BLOB = re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}\b")

# Chassi/VIN: 17 posições, sem I, O e Q (a norma as exclui justamente para não
# confundir com 1 e 0). Filtro extra em código: precisa ter letra E dígito.
_P_CHASSI = re.compile(r"(?<![A-Za-z0-9])[A-HJ-NPR-Za-hj-npr-z0-9]{17}(?![A-Za-z0-9])")
# CNPJ e CPF: com e SEM máscara. As âncoras `(?<!\d)`/`(?!\d)` impedem que um
# protocolo de 16 dígitos vire "CPF" por acidente de recorte.
_P_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")
_P_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
# Placa Mercosul (ABC1D23) e antiga (ABC-1234 / ABC1234).
_P_PLACA = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{3}[\s-]?\d[A-Za-z0-9]\d{2}(?![A-Za-z0-9])")
_P_EMAIL = re.compile(r"\b[\w.+-]+@([\w-]+(?:\.[\w-]+)+)\b")
_P_TELEFONE = re.compile(
    r"(?<!\d)(?:\+?55[\s-]?)?\(?(\d{2})\)?[\s.-]?(9?\d{4})[\s.-]?(\d{4})(?!\d)")
_P_CEP_MASCARADO = re.compile(r"(?<!\d)\d{5}-\d{3}(?!\d)")


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", str(texto))


def _cpf_valido(num: str) -> bool:
    """mod-11 do CPF.

    🔴 É este cálculo que dá o direito de NÃO acusar. Uma sequência de onze
    dígitos cujo verificador não fecha não é o CPF de ninguém — nunca foi
    emitida. Sem isso, o guarda acusaria todo número de onze dígitos, viraria
    ruído, e ruído acaba silenciado com um `# noqa` que também some com o
    achado verdadeiro.
    """
    d = _digitos(num)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for corte in (9, 10):
        soma = sum(int(d[i]) * ((corte + 1) - i) for i in range(corte))
        dv = (soma * 10) % 11
        dv = 0 if dv == 10 else dv
        if dv != int(d[corte]):
            return False
    return True


def _cnpj_valido(num: str) -> bool:
    """mod-11 do CNPJ, com os pesos 5..2 / 9..2 da Receita."""
    d = _digitos(num)
    if len(d) != 14 or len(set(d)) == 1:
        return False
    for pesos in ((5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                  (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)):
        corte = len(pesos)
        soma = sum(int(d[i]) * pesos[i] for i in range(corte))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if dv != int(d[corte]):
            return False
    return True


# Vocabulário de DECLARAÇÃO. 🔴 Achado real do smoke test: o campo `secrets`
# do próprio `manifest.json` casa `chave_e_sensivel` (o substring `secret`), e
# o valor obrigatório dele — `"removed"` — era acusado como "segredo literal".
# O manifesto virava a fixture mais suja do repositório por dizer que estava
# limpo. Uma palavra que só existe para DECLARAR ausência não é presença.
_PALAVRAS_DE_DECLARACAO: Tuple[str, ...] = (
    "removed", "removido", "none", "null", "n/a", "na", "absent", "ausente",
    "sanitized", "sanitizado", "redacted", "redigido", "masked", "mascarado",
    "false", "true", "sim", "nao", "yes", "no", "-",
)


def _e_placeholder(bruto: Any) -> bool:
    """O valor é um substituto sintético evidente?

    Reconhece o que a casa realmente escreve nas fixtures da SPEC-074:
    `Q***A91`, `9BW*******T004251`, `******999999999`, `<redacted:token>`,
    `00000000-0000-4000-8000-000000000000`, `111.111.111-11`.

    Não é adivinhação de "parece falso": é o conjunto de marcas que só aparecem
    quando alguém já mascarou de propósito.
    """
    s = str(bruto or "").strip()
    if not s:
        return True
    if s.lower() in _PALAVRAS_DE_DECLARACAO:
        return True
    if s.startswith("<") and s.endswith(">"):
        return True
    if "*" in s or "…" in s or "xxxx" in s.lower() or "XXXX" in s:
        return True
    nucleo = re.sub(r"[^0-9A-Za-z]", "", s)
    if not nucleo:
        return True
    # Um único caractere domina o valor (GUID zerado, 111.111.111-11).
    mais_comum = max(nucleo.lower().count(c) for c in set(nucleo.lower()))
    if mais_comum / len(nucleo) >= 0.75:
        return True
    if nucleo.isdigit() and (nucleo in "01234567890123456789"
                             or nucleo in "98765432109876543210"):
        return True
    return False


def _dominio_de_exemplo(dominio: str) -> bool:
    d = str(dominio or "").strip().lower().rstrip(".")
    if d in DOMINIOS_DE_EXEMPLO:
        return True
    if any(d.endswith("." + x) for x in DOMINIOS_DE_EXEMPLO):
        return True
    return any(d.endswith(sufixo) for sufixo in _SUFIXOS_DE_EXEMPLO)


def _telefone_plausivel(ddd: str, meio: str, fim: str) -> bool:
    """Filtra o que só *parece* telefone.

    DDD brasileiro vai de 11 a 99, e celular de 11 dígitos começa com 9 depois
    do DDD. Sem esse filtro, qualquer número de dez dígitos num JSON — código
    de produto, protocolo curto — viraria "telefone" e o relatório perderia
    credibilidade.
    """
    try:
        n = int(ddd)
    except (TypeError, ValueError):
        return False
    if not (11 <= n <= 99):
        return False
    if len(meio) == 5 and not meio.startswith("9"):
        return False
    return len(fim) == 4


def _amostra(tipo: str, bruto: str) -> str:
    """Rótulo seguro: tipo, tamanho e impressão. Nunca o conteúdo."""
    return f"<{tipo}:{len(str(bruto))}:{_digest_da_casa(str(bruto))}>"


def _achado(tipo: str, caminho: str, bruto: str, severidade: str,
            motivo: str) -> Achado:
    return Achado(tipo=tipo, caminho=caminho, severidade=severidade,
                  motivo=motivo, amostra=_amostra(tipo, bruto),
                  impressao=_digest_da_casa(str(bruto)))


def _achados_em_texto(texto: str, caminho: str, *,
                      somente_documentos: bool = False) -> List[Achado]:
    """Varre uma string, do padrão mais específico ao mais genérico.

    `somente_documentos=True` é o caso do valor NUMÉRICO: `{"cpf": 52998224725}`
    chega como int, e um int não tem como carregar um JWT — rodar os padrões de
    segredo sobre a representação decimal só produziria falso positivo.
    """
    s = str(texto or "")
    if not s:
        return []

    achados: List[Achado] = []
    consumidos: List[Tuple[int, int]] = []

    def _livre(ini: int, fim: int) -> bool:
        return not any(ini < f and i < fim for i, f in consumidos)

    def _rodar(padrao: "re.Pattern[str]", julgar: Callable[["re.Match[str]"], Optional[Achado]]) -> None:
        for m in padrao.finditer(s):
            if not _livre(m.start(), m.end()):
                continue
            veredito = julgar(m)
            consumidos.append((m.start(), m.end()))  # consome mesmo se absolvido
            if veredito is not None:
                achados.append(veredito)

    if not somente_documentos:
        _rodar(_P_JWT, lambda m: _achado(
            "jwt", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
            "JWT literal; §19.3 nomeia JWT como nunca-comitar"))
        _rodar(_P_CHAVE_DE_PROVEDOR, lambda m: _achado(
            "chave_de_provedor", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
            "formato de chave de API de provedor conhecido"))
        _rodar(_P_ESQUEMA_AUTH, lambda m: None if _e_placeholder(m.group(1)) else _achado(
            "autorizacao", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
            "cabecalho Authorization com credencial literal"))
        _rodar(_P_COOKIE_INLINE, lambda m: None if _e_placeholder(m.group(1)) else _achado(
            "cookie", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
            "Cookie/Set-Cookie com valor literal"))
        _rodar(_P_SEGREDO_INLINE, lambda m: None if _e_placeholder(m.group(1)) else _achado(
            "segredo", caminho, m.group(1), SEVERIDADE_BLOQUEIA,
            "senha/token escrito inline no texto"))

    _rodar(_P_CHASSI, lambda m: None if (
        _e_placeholder(m.group(0))
        or not re.search(r"[A-Za-z]", m.group(0))
        or not re.search(r"\d", m.group(0))
    ) else _achado(
        "chassi", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
        "17 posicoes no formato VIN; mascare como a casa ja faz "
        "(`9BW*******T004251`) — nao ha como provar que um chassi nao e real"))

    def _julgar_cnpj(m: "re.Match[str]") -> Optional[Achado]:
        bruto = m.group(0)
        if _e_placeholder(bruto):
            return None
        if _cnpj_valido(bruto):
            return _achado("cnpj", caminho, bruto, SEVERIDADE_BLOQUEIA,
                           "CNPJ com digito verificador VALIDO — existe")
        return _achado("cnpj", caminho, bruto, SEVERIDADE_REVISAR,
                       "formato de CNPJ com verificador invalido; "
                       "provavelmente sintetico, confirme")

    def _julgar_cpf(m: "re.Match[str]") -> Optional[Achado]:
        bruto = m.group(0)
        if _e_placeholder(bruto):
            return None
        if _cpf_valido(bruto):
            return _achado("cpf", caminho, bruto, SEVERIDADE_BLOQUEIA,
                           "CPF com digito verificador VALIDO — pertence a alguem")
        return _achado("cpf", caminho, bruto, SEVERIDADE_REVISAR,
                       "formato de CPF com verificador invalido; "
                       "provavelmente sintetico, confirme")

    _rodar(_P_CNPJ, _julgar_cnpj)
    _rodar(_P_CPF, _julgar_cpf)

    if not somente_documentos:
        _rodar(_P_PLACA, lambda m: None if _e_placeholder(m.group(0)) else _achado(
            "placa", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
            "placa Mercosul ou antiga sem mascara; a casa escreve `Q***A91`"))
        _rodar(_P_EMAIL, lambda m: None if _dominio_de_exemplo(m.group(1)) else _achado(
            "email", caminho, m.group(0), SEVERIDADE_BLOQUEIA,
            f"e-mail em dominio real (`{m.group(1)}`); use um de "
            "`DOMINIOS_DE_EXEMPLO`"))

    _rodar(_P_TELEFONE, lambda m: None if (
        _e_placeholder(m.group(0))
        or not _telefone_plausivel(m.group(1), m.group(2), m.group(3))
    ) else _achado(
        "telefone", caminho, m.group(0), SEVERIDADE_REVISAR,
        "telefone brasileiro plausivel; 0800 de seguradora e dominio, "
        "telefone de segurado nao entra"))

    # CEP: só na forma mascarada `NNNNN-NNN`. Oito dígitos crus são
    # indistinguiveis de qualquer codigo interno (o proprio
    # `CodigoAtendimento` do Maxpar tem oito) — acusar todos seria ruido.
    _rodar(_P_CEP_MASCARADO, lambda m: None if _e_placeholder(m.group(0)) else _achado(
        "cep", caminho, m.group(0), SEVERIDADE_REVISAR,
        "CEP completo; confira se e endereco de segurado"))

    if not somente_documentos:
        _rodar(_P_BLOB, lambda m: None if _e_placeholder(m.group(0)) else _achado(
            "token", caminho, m.group(0), SEVERIDADE_REVISAR,
            "cadeia longa com cara de token/hash de sessao"))

    return achados


def varredura_de_pii(texto_ou_dict: Any, *, paranoico: bool = False,
                     _caminho: str = "$", _prof: int = 0) -> List[Achado]:
    """O guarda de §19.3: o que NÃO pode entrar numa fixture.

    Detecta, no mínimo: CPF e CNPJ (com e sem máscara), placa Mercosul e
    antiga, chassi, e-mail fora de domínio de exemplo, telefone brasileiro, e
    qualquer coisa com cara de token, senha ou cookie.

    `paranoico=True` promove todo `revisar` a `bloqueia`. Sem o redator da casa
    (`REDATOR_DISPONIVEL is False`) o modo é forçado — ver o docstring do
    módulo: o caminho degradado tem de ser o chato.

    🔴 O detector precisa CONSEGUIR não acusar. Um guarda que acusa tudo é
    equivalente a um guarda que não acusa nada, porque o time aprende a passar
    por cima dele. É por isso que existem `_e_placeholder()`, `_cpf_valido()` e
    `DOMINIOS_DE_EXEMPLO`: eles são o que dá sentido ao alarme quando ele soa.
    """
    paranoico = paranoico or not REDATOR_DISPONIVEL
    achados = _varrer(texto_ou_dict, _caminho, _prof)

    if paranoico:
        achados = [
            a if a.bloqueia else Achado(
                tipo=a.tipo, caminho=a.caminho, severidade=SEVERIDADE_BLOQUEIA,
                motivo=a.motivo + " [modo paranoico]", amostra=a.amostra,
                impressao=a.impressao)
            for a in achados
        ]

    # Dedupe estável: o mesmo valor no mesmo caminho é um achado, não três.
    vistos: Dict[Tuple[str, str, str], Achado] = {}
    for a in achados:
        vistos.setdefault((a.tipo, a.caminho, a.impressao), a)
    return sorted(vistos.values(), key=lambda a: (a.caminho, a.tipo))


def _varrer(valor: Any, caminho: str, prof: int) -> List[Achado]:
    """Percorre a estrutura guardando o CAMINHO — sem ele o achado não conserta.

    Dizer "há um CPF na fixture" manda alguém ler quatrocentas linhas. Dizer
    "há um CPF em `$.atendimento.Segurado.Cpf`" é um `Ctrl-F`.
    """
    if prof > 12:  # estrutura patológica não derruba o guarda
        return []

    achados: List[Achado] = []

    if isinstance(valor, dict):
        for k, v in valor.items():
            sub = f"{caminho}.{k}"
            sensivel = (_chave_e_sensivel_da_casa(k)
                        or any(r in str(k).strip().lower()
                               for r in CHAVES_EXTRA_DE_FIXTURE))
            # 🔴 Booleano não carrega segredo — `{"password": true}` diz que o
            # campo EXISTE na tela, que é diagnóstico. A mesma decisão do
            # `redaction.py`, medida no canário P-186; repetir o erro aqui
            # apagaria o mesmo diagnóstico de novo.
            if sensivel and v not in (None, "") and not isinstance(v, bool):
                if not _e_placeholder(v):
                    achados.append(_achado(
                        "segredo", sub, v, SEVERIDADE_BLOQUEIA,
                        f"chave sensivel `{k}` com valor literal; §19.3 manda "
                        "substituir por `<redacted:...>` ou sintetico"))
            achados.extend(_varrer(v, sub, prof + 1))
        return achados

    if isinstance(valor, (list, tuple)):
        for i, v in enumerate(valor):
            achados.extend(_varrer(v, f"{caminho}[{i}]", prof + 1))
        return achados

    if isinstance(valor, bool) or valor is None:
        return achados

    if isinstance(valor, (int, float)):
        # CPF em JSON de API chega como número com frequência. Ignorar o int
        # seria deixar a porta da frente aberta e trancar a dos fundos.
        return _achados_em_texto(str(valor), caminho, somente_documentos=True)

    return _achados_em_texto(str(valor), caminho)


def bloqueantes(achados: Iterable[Achado]) -> List[Achado]:
    """Só o que impede a fixture de entrar. O resto é para o revisor humano."""
    return [a for a in achados if a.bloqueia]


def fixture_e_segura(alvo: Any, *, paranoico: bool = False) -> Tuple[bool, List[Achado]]:
    """`(pode_comitar, achados)` — o atalho que a Factory chama."""
    achados = varredura_de_pii(alvo, paranoico=paranoico)
    return (not bloqueantes(achados)), achados


# ==========================================================================
# C) REPLAY DE SESSÃO — §19.1
# ==========================================================================
class ErroDeReplay(RuntimeError):
    """Base. Carrega o `ResultadoDeReplay` parcial quando houver."""

    def __init__(self, mensagem: str, resultado: Any = None) -> None:
        super().__init__(mensagem)
        self.resultado = resultado


class ReplayDivergente(ErroDeReplay):
    """A journey pediu algo de LEITURA que a fixture não gravou."""


class EfeitoNaoPrevisto(ErroDeReplay):
    """🔴 A journey tentou um EFEITO que a fixture não previu.

    Esta é a exceção que justifica o módulo. Se ela virasse um aviso, o replay
    passaria verde sobre uma journey que, ligada, escreveria no portal uma coisa
    que ninguém revisou — e o verde seria lido como permissão para ligar
    operação material, que é justamente o que a SPEC-075 §44 proíbe.
    """


class FixtureInsegura(ErroDeReplay):
    """A fixture carrega PII/segredo, ou o manifesto contradiz o replay."""


ESGOTAR_ERRO = "erro"
ESGOTAR_SILENCIO = "silencio"


@dataclass
class InteracaoGravada:
    """Uma linha de `network.json` — §19.1.

    Para o caso material, os quatro campos de §19.5 estão aqui: `metodo` +
    `caminho` + `corpo_esperado` são a *request planejada*, `boundary` é a
    *fronteira detectada*, `resposta` é a *response observada e sanitizada*, e
    `efeito_esperado` é o *expected effect*.
    """

    metodo: str
    caminho: str
    status: int = 200
    resposta: Any = None
    # O que o cliente DEVERIA mandar. Comparação por SUBCONJUNTO: a journey
    # real manda campos a mais (token, código), e exigir igualdade exata
    # transformaria o guarda num gerador de falso negativo por manutenção.
    corpo_esperado: Optional[Dict[str, Any]] = None
    material: bool = False
    boundary: str = ""
    efeito_esperado: str = ""
    rotulo: str = ""

    @property
    def nome(self) -> str:
        return self.rotulo or f"{self.metodo.upper()} {self.caminho}"


@dataclass
class ChamadaObservada:
    """O que a journey realmente pediu. Gravado ANTES de qualquer veredito.

    🔴 A ordem importa: se a contagem fosse feita depois da validação, a chamada
    que estoura não apareceria no relatório — e o relatório da falha é o único
    lugar onde se descobre *qual* chamada foi a errada.
    """

    ordem: int
    metodo: str
    caminho: str
    casou: bool
    material: bool
    status: Optional[int] = None
    forma_do_corpo: Any = None
    impressao_do_corpo: str = ""


@dataclass
class EfeitoMaterialRegistrado:
    """A INTENÇÃO material — registrada, jamais executada. §19.5."""

    ordem: int
    operacao: str
    metodo: str
    caminho: str
    boundary: str = ""
    efeito_esperado: str = ""
    previsto: bool = True
    impressao_do_corpo: str = ""
    # 🔴 Constante por construção. Não existe caminho neste arquivo que atribua
    # `True`. Se um dia existir, este módulo deixou de ser replay.
    executado: bool = False


class ReplayDeSessao:
    """Sessão falsa que responde a partir de interações gravadas, CONTANDO.

    Substitui a sessão real da journey. Três coisas a distinguem de um mock
    qualquer:

    1. **Conta.** `total_de_chamadas`, `chamou(metodo, caminho)` e
       `nao_consumidas` transformam "a journey funcionou" em "a journey fez
       exatamente estas seis chamadas, nesta ordem".
    2. **Confere o corpo.** O `SessaoDeQuestionarioFalsa` da SPEC-074 guarda o
       que o cliente mandou (`self.enviados`) mas nunca o compara com nada. Um
       cliente que esquecesse de reenviar o acumulado passaria pelo teste
       inteiro. Aqui a comparação é ligada por padrão — CLAUDE.md §9.3: um
       guarda que não tem como falhar não guarda nada.
    3. **Não deixa efeito passar.** Ver `_responder`.

    Compatibilidade com o estilo da casa
    ------------------------------------
    `de_sequencia_de_questionario()` monta o replay direto das tuplas
    `(request_body, status, response_body)` de `maxpar_questionario.py`, e
    `proxima_pergunta()` tem a MESMA assinatura e o MESMO retorno de
    `SessaoDeQuestionarioFalsa` — inclusive `fim_do_questionario` no 204. As
    fixtures da SPEC-074 são o padrão ouro; quem se adapta é o harness.
    """

    def __init__(self, interacoes: Sequence[InteracaoGravada], *,
                 nome: str = "",
                 estrito: bool = True,
                 permitir_material: bool = False,
                 dry_run: bool = True,
                 conferir_corpo: bool = True,
                 ao_esgotar: str = ESGOTAR_ERRO) -> None:
        self.nome = nome
        self.interacoes: List[InteracaoGravada] = list(interacoes or [])
        self.estrito = bool(estrito)
        self.permitir_material = bool(permitir_material)
        self.dry_run = bool(dry_run)
        self.conferir_corpo = bool(conferir_corpo)
        self.ao_esgotar = ao_esgotar

        self.chamadas: List[ChamadaObservada] = []
        self.efeitos: List[EfeitoMaterialRegistrado] = []
        self.divergencias: List[str] = []
        self.parou_na_fronteira = False
        # Espelha `SessaoDeQuestionarioFalsa.enviados`, para quem já lia isso.
        self.enviados: List[Any] = []

        self._cursor = 0
        self._consumidas: set = set()

    # -- construção a partir do estilo da casa ----------------------------
    @classmethod
    def de_sequencia_de_questionario(
        cls,
        sequencia: Sequence[Tuple[Any, int, Any]],
        *,
        caminho: str = "/questionarios/perguntas",
        metodo: str = "POST",
        **kwargs: Any,
    ) -> "ReplayDeSessao":
        """Monta o replay das tuplas `(request, status, response)` da SPEC-074.

        O motor de perguntas do Maxpar é **stateless no servidor**: o cliente
        reenvia o acumulado inteiro a cada rodada e o 204 encerra. Por isso o
        `corpo_esperado` de cada interação é o request gravado — o replay não
        imita o protocolo, ele **é** o protocolo, com as respostas medidas.

        📊 `SEQUENCIA_YELUM` (documentada em `maxpar_questionario.py`, captura
        de 2026-08-15): 4 rodadas, entries 240/252/255/257, a última **204**.
        """
        interacoes = [
            InteracaoGravada(metodo=metodo, caminho=caminho, status=int(status),
                             resposta=resposta, corpo_esperado=(
                                 req if isinstance(req, dict) else None),
                             rotulo=f"pergunta#{i + 1}")
            for i, (req, status, resposta) in enumerate(sequencia or [])
        ]
        return cls(interacoes, **kwargs)

    # -- leitura -----------------------------------------------------------
    @property
    def total_de_chamadas(self) -> int:
        return len(self.chamadas)

    @property
    def nao_consumidas(self) -> List[str]:
        """Interações gravadas que a journey nunca pediu.

        Sinal de journey que parou cedo — e de fixture que descreve um caminho
        que o código não percorre mais.
        """
        return [it.nome for i, it in enumerate(self.interacoes)
                if i not in self._consumidas]

    def chamou(self, metodo: Optional[str] = None,
               caminho: Optional[str] = None) -> int:
        """Quantas vezes a journey pediu isto. Sem filtro, devolve o total."""
        alvo_m = (metodo or "").strip().upper()
        alvo_c = (caminho or "").strip()
        n = 0
        for c in self.chamadas:
            if alvo_m and c.metodo != alvo_m:
                continue
            if alvo_c and not _caminhos_casam(c.caminho, alvo_c):
                continue
            n += 1
        return n

    def resumo(self) -> Dict[str, Any]:
        return {
            "nome": self.nome,
            "chamadas": self.total_de_chamadas,
            "por_chamada": [f"{c.metodo} {c.caminho}" for c in self.chamadas],
            "efeitos_registrados": len(self.efeitos),
            "efeitos_executados": 0,  # invariante, ver `EfeitoMaterialRegistrado`
            "divergencias": list(self.divergencias),
            "nao_consumidas": self.nao_consumidas,
            "parou_na_fronteira": self.parou_na_fronteira,
        }

    # -- o núcleo ----------------------------------------------------------
    def _proxima(self, metodo: str, caminho: str) -> Optional[InteracaoGravada]:
        if self.estrito:
            if self._cursor < len(self.interacoes):
                it = self.interacoes[self._cursor]
                if it.metodo.upper() == metodo and _caminhos_casam(it.caminho, caminho):
                    self._consumidas.add(self._cursor)
                    self._cursor += 1
                    return it
            return None
        for i in range(len(self.interacoes)):
            if i in self._consumidas:
                continue
            it = self.interacoes[i]
            if it.metodo.upper() == metodo and _caminhos_casam(it.caminho, caminho):
                if i != self._cursor:
                    self.divergencias.append(
                        f"fora de ordem: `{it.nome}` era a posicao {i}, "
                        f"esperava-se a {self._cursor}")
                self._consumidas.add(i)
                self._cursor = i + 1
                return it
        return None

    def _conferir_corpo(self, it: InteracaoGravada, corpo: Any) -> None:
        """Comparação por subconjunto do que a fixture gravou como request.

        🔴 É aqui que se pega o cliente que parou de reenviar o acumulado. O
        motor de perguntas do Maxpar é stateless: se o corpo chega sem
        `PerguntasResposta`, o portal real recomeça o questionário do zero e o
        pedido sai com a resposta errada — trocando motorista por carona.
        """
        if not self.conferir_corpo or not isinstance(it.corpo_esperado, dict):
            return
        if not isinstance(corpo, dict):
            self.divergencias.append(
                f"{it.nome}: esperava um corpo com "
                f"{sorted(it.corpo_esperado)}, veio {type(corpo).__name__}")
            return
        for k, esperado in it.corpo_esperado.items():
            if k not in corpo:
                self.divergencias.append(f"{it.nome}: corpo sem `{k}`")
            elif corpo[k] != esperado:
                self.divergencias.append(
                    f"{it.nome}: `{k}` divergiu do request gravado")

    def _responder(self, metodo: str, caminho: str, corpo: Any = None,
                   *, operacao: str = "") -> Dict[str, Any]:
        """O caminho único. Toda porta desta classe passa por aqui.

        A sequência de decisão, e o porquê de cada degrau:

            1. registra a chamada     — o relatório precisa dela mesmo se estourar
            2. procura na fixture     — em ordem (estrito) ou por casamento
            3. nao achou + verbo de escrita  -> `EfeitoNaoPrevisto`
               nao achou + verbo de leitura  -> `ReplayDivergente`
            4. achou e e material     -> registra a INTENCAO; nunca executa
            5. confere o corpo        -> divergencias
            6. devolve a resposta gravada

        🔴 O degrau 3 é o que impede o falso verde. Um POST que a fixture não
        conhece é, por definição, um efeito que ninguém revisou — e o replay
        não tem como saber se ele é inofensivo. Tratar o desconhecido como
        escrita é a única leitura segura.
        """
        m = str(metodo or "GET").strip().upper()
        c = str(caminho or "").strip()

        it = self._proxima(m, c)
        material = bool(it.material) if it is not None else (m in VERBOS_MATERIAIS)

        obs = ChamadaObservada(
            ordem=len(self.chamadas) + 1, metodo=m, caminho=c,
            casou=it is not None, material=material,
            status=(it.status if it is not None else None),
            forma_do_corpo=_shape_of_da_casa(corpo) if corpo is not None else None,
            impressao_do_corpo=_impressao(corpo),
        )
        self.chamadas.append(obs)

        if it is None:
            if material:
                self.efeitos.append(EfeitoMaterialRegistrado(
                    ordem=obs.ordem, operacao=operacao or f"{m} {c}",
                    metodo=m, caminho=c, previsto=False,
                    impressao_do_corpo=obs.impressao_do_corpo))
                raise EfeitoNaoPrevisto(
                    f"efeito NAO previsto pela fixture: `{m} {c}` "
                    f"(chamada #{obs.ordem} de `{self.nome or 'replay'}`). "
                    "A fixture nao descreve esta escrita, entao o replay nao "
                    "tem como afirmar que ela e segura. SPEC-075 §19.5.")
            if self.ao_esgotar == ESGOTAR_SILENCIO:
                self.divergencias.append(f"sem interacao gravada para `{m} {c}`")
                return {"ok": False, "status": 0, "json": None,
                        "fim_do_questionario": False, "previsto": False}
            raise ReplayDivergente(
                f"a journey pediu `{m} {c}` (chamada #{obs.ordem}) e a fixture "
                f"nao gravou essa leitura. Gravadas e ainda nao usadas: "
                f"{self.nao_consumidas or '[]'}")

        self._conferir_corpo(it, corpo)

        if material:
            if not self.permitir_material:
                raise EfeitoNaoPrevisto(
                    f"replay READ-ONLY tocou uma interacao material "
                    f"(`{it.nome}`). §19.4 cobre GET/POST semanticamente de "
                    "leitura; efeito material se prova por `replay_com_efeito`.")
            self.efeitos.append(EfeitoMaterialRegistrado(
                ordem=obs.ordem, operacao=operacao or it.efeito_esperado or it.nome,
                metodo=m, caminho=c, boundary=it.boundary,
                efeito_esperado=it.efeito_esperado, previsto=True,
                impressao_do_corpo=obs.impressao_do_corpo))
            if self.dry_run:
                # §19.5: em dry-run o código tem de PARAR na fronteira. O
                # replay devolve a recusa, nunca a resposta observada — senão
                # o teste provaria o caminho que nao e o testado.
                self.parou_na_fronteira = True
                return {"ok": False, "status": 0, "json": None,
                        "parou_na_fronteira": True,
                        "boundary": it.boundary or "material_side_effect",
                        "efeito_esperado": it.efeito_esperado,
                        "motivo": "dry-run: efeito material nao executado"}

        return {"ok": int(it.status) < 400, "status": int(it.status),
                "json": it.resposta, "previsto": True,
                "fim_do_questionario": int(it.status) == 204}

    # -- as portas ---------------------------------------------------------
    def requisitar_sync(self, metodo: str, caminho: str,
                        corpo: Any = None, **_: Any) -> Dict[str, Any]:
        """Versão síncrona, para journey que não é `async`."""
        return self._responder(metodo, caminho, corpo)

    async def requisitar(self, metodo: str, caminho: str,
                         corpo: Any = None, **_: Any) -> Dict[str, Any]:
        """A porta normal de rede da sessão falsa."""
        return self._responder(metodo, caminho, corpo)

    async def efeito_material(self, *, operacao: str, metodo: str = "POST",
                              caminho: str = "", corpo: Any = None,
                              **_: Any) -> Dict[str, Any]:
        """A porta EDUCADA — quando a journey declara o que vai fazer.

        Ela existe para dar um `operacao` legível ao registro. Ela **não** é a
        proteção: `requisitar()` intercepta igual. Uma porta que só protege
        quem bate nela protege só quem já ia se comportar.
        """
        return self._responder(metodo, caminho or operacao, corpo,
                               operacao=operacao)

    async def proxima_pergunta(self, respostas: Any) -> Dict[str, Any]:
        """Assinatura e retorno idênticos a `SessaoDeQuestionarioFalsa`.

        O acumulado vai no corpo como o portal espera (`PerguntasResposta`),
        para que a conferência de corpo do item 2 da classe funcione sem que a
        fixture da SPEC-074 precise mudar uma linha.
        """
        self.enviados.append(list(respostas or []))
        it = (self.interacoes[self._cursor]
              if self._cursor < len(self.interacoes) else None)
        caminho = it.caminho if it is not None else "/questionarios/perguntas"
        metodo = it.metodo if it is not None else "POST"
        resposta = self._responder(metodo, caminho,
                                   {"PerguntasResposta": list(respostas or [])})
        resposta.setdefault("fim_do_questionario", resposta.get("status") == 204)
        return resposta


def _caminhos_casam(a: Any, b: Any) -> bool:
    """Tolerante a base URL, estrito no resto.

    `"/atendimentos"` casa `"https://portal/api/atendimentos"`, porque a fixture
    guarda o caminho e a journey monta a URL. O `"*"` é o coringa explícito.
    """
    x = str(a or "").strip()
    y = str(b or "").strip()
    if "*" in (x, y):
        return True
    if not x or not y:
        return False
    if x == y:
        return True
    xs, ys = x.rstrip("/"), y.rstrip("/")
    return xs.endswith(ys) or ys.endswith(xs)


def _impressao(corpo: Any) -> str:
    """Digest do corpo. O corpo em si nunca é guardado no relatório."""
    if corpo is None:
        return ""
    try:
        crua = json.dumps(corpo, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        crua = str(corpo)
    return hashlib.sha256(crua.encode("utf-8", "ignore")).hexdigest()[:12]


# ==========================================================================
# D) OS DOIS REPLAYS — §19.4 e §19.5
# ==========================================================================
@dataclass
class ResultadoDeReplay:
    """O veredito. `ok` só é `True` quando não sobrou nenhum problema."""

    ok: bool
    caso: str
    business_state: str = ""
    esperado: str = ""
    chamadas: int = 0
    efeitos: List[EfeitoMaterialRegistrado] = field(default_factory=list)
    problemas: List[str] = field(default_factory=list)
    divergencias: List[str] = field(default_factory=list)
    nao_consumidas: List[str] = field(default_factory=list)
    parou_na_fronteira: bool = False
    retorno: Any = None

    @property
    def efeitos_executados(self) -> int:
        """Invariante do módulo: sempre 0. Testável, e é para ser testado."""
        return sum(1 for e in self.efeitos if e.executado)

    def para_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "caso": self.caso,
            "business_state": self.business_state,
            "esperado": self.esperado,
            "chamadas": self.chamadas,
            "efeitos": [e.__dict__ for e in self.efeitos],
            "efeitos_executados": self.efeitos_executados,
            "problemas": list(self.problemas),
            "divergencias": list(self.divergencias),
            "nao_consumidas": list(self.nao_consumidas),
            "parou_na_fronteira": self.parou_na_fronteira,
        }


def _estado_do_retorno(retorno: Any) -> str:
    """Traduz o que a journey devolveu para o vocabulário de `expected_state`.

    `JourneyResult.status` continua sendo `done | needs_human | failed` por
    compatibilidade (§16.2) — a tradução mora aqui, não na journey.
    """
    if retorno is None:
        return ""
    estado = getattr(retorno, "business_state", None)
    if not estado and isinstance(retorno, dict):
        estado = retorno.get("business_state") or retorno.get("status")
    if not estado:
        estado = getattr(retorno, "status", None)
    s = str(estado or "").strip().lower()
    return {"done": "success", "ok": "success"}.get(s, s)


def _mesmo_estado(a: str, b: str) -> bool:
    """Compara aceitando os DOIS vocabulários (§16.1 e `contracts.py`)."""
    x, y = str(a or "").strip().lower(), str(b or "").strip().lower()
    if x == y:
        return True
    return bool(x) and bool(y) and (
        EQUIVALENCIA_DE_ESTADO.get(x, "\0") == EQUIVALENCIA_DE_ESTADO.get(y, "\1"))


async def _rodar_journey(journey: Callable[..., Any], sessao: ReplayDeSessao,
                         entrada: Optional[Dict[str, Any]]) -> Any:
    saida = journey(sessao, **(entrada or {}))
    if inspect.isawaitable(saida):
        saida = await saida  # type: ignore[assignment]
    return saida


def _preparar(manifesto: Any, interacoes: Sequence[InteracaoGravada],
              exigir: str) -> Tuple[ManifestoDeFixture, List[str]]:
    """Valida manifesto + fixture ANTES de rodar uma linha da journey.

    🔴 Rodar primeiro e conferir depois é o erro clássico: o replay que já
    executou não desfaz o que descobriu tarde demais que não devia ter feito.
    """
    m = (manifesto if isinstance(manifesto, ManifestoDeFixture)
         else ManifestoDeFixture.de_dict(manifesto))
    ok_manifesto, problemas = validar_manifesto(m.para_dict())

    efeito = normalizar_efeito(m.effect)
    if exigir == EFEITO_READ and efeito != EFEITO_READ:
        problemas.append(
            f"manifesto declara `effect={m.effect}` e este e o replay "
            "read-only (§19.4); use `replay_com_efeito`")
    if exigir == EFEITO_MATERIAL and efeito != EFEITO_MATERIAL:
        problemas.append(
            f"manifesto declara `effect={m.effect}` mas o replay de efeito "
            "(§19.5) foi pedido; corrija o manifesto — a classe de efeito nao "
            "e detalhe de metadado")

    if exigir == EFEITO_READ and any(it.material for it in interacoes):
        problemas.append(
            "fixture read-only contem interacao marcada `material=True`")
    if exigir == EFEITO_MATERIAL and not any(it.material for it in interacoes):
        problemas.append(
            "fixture de efeito nao marca NENHUMA interacao como `material=True`; "
            "sem fronteira declarada o replay nao prova nada")

    # A fixture inteira passa pelo guarda de §19.3.
    corpo_da_fixture = [
        {"metodo": it.metodo, "caminho": it.caminho, "resposta": it.resposta,
         "corpo_esperado": it.corpo_esperado}
        for it in interacoes
    ]
    for achado in bloqueantes(varredura_de_pii(corpo_da_fixture)):
        problemas.append(f"fixture suja — {achado}")

    del ok_manifesto  # a lista de problemas já é o veredito
    return m, problemas


async def replay_read_only(
    journey: Callable[..., Any],
    *,
    manifesto: Any,
    interacoes: Sequence[InteracaoGravada],
    entrada: Optional[Dict[str, Any]] = None,
    estrito: bool = True,
    estourar: bool = True,
) -> ResultadoDeReplay:
    """§19.4 — reproduz offline request/response sanitizados de leitura.

    Prova três coisas ao mesmo tempo: que a journey chega ao
    `expected_state` do manifesto, que ela faz **as** chamadas gravadas (nem a
    mais, nem a menos), e que ela não toca em nada material pelo caminho.

    `estourar=True` (padrão) repropaga `ErroDeReplay` com o
    `ResultadoDeReplay` parcial anexado em `erro.resultado`. Falha de replay
    tem de ser barulhenta; quem quiser inspecionar em vez de estourar passa
    `estourar=False`.
    """
    interacoes = list(interacoes or [])
    m, problemas = _preparar(manifesto, interacoes, EFEITO_READ)

    sessao = ReplayDeSessao(interacoes, nome=m.chave, estrito=estrito,
                            permitir_material=False, dry_run=True)

    if problemas:
        res = ResultadoDeReplay(ok=False, caso=m.chave, esperado=m.expected_state,
                                problemas=problemas)
        if estourar:
            raise FixtureInsegura("; ".join(problemas), resultado=res)
        return res

    return await _finalizar(journey, sessao, m, entrada, estourar,
                            exigir_fronteira=False)


async def replay_com_efeito(
    journey: Callable[..., Any],
    *,
    manifesto: Any,
    interacoes: Sequence[InteracaoGravada],
    entrada: Optional[Dict[str, Any]] = None,
    dry_run: bool = True,
    estrito: bool = True,
    estourar: bool = True,
) -> ResultadoDeReplay:
    """§19.5 — prova que a journey PARARIA na fronteira, sem reexecutar nada.

    Nunca "reexecuta" o POST material. A fixture descreve a request planejada,
    a fronteira detectada, a response observada e o efeito esperado; o replay
    confere que o código chega à fronteira, **registra a intenção** e para.

    Dois modos:

        dry_run=True  (padrao)  a fronteira devolve RECUSA. Prova o guard.
        dry_run=False           a fronteira devolve a response gravada, para
                                exercitar o pos-efeito (leitura de protocolo,
                                reconciliacao). Continua sem executar nada:
                                `efeitos_executados` e 0 nos dois modos.

    🔴 Efeito que a fixture não previu estoura `EfeitoNaoPrevisto`. É a razão
    de o modo `dry_run=False` poder existir sem virar um executor disfarçado:
    o conjunto do que pode acontecer é fechado pela fixture, não pelo código
    que está sendo testado.
    """
    interacoes = list(interacoes or [])
    m, problemas = _preparar(manifesto, interacoes, EFEITO_MATERIAL)

    sessao = ReplayDeSessao(interacoes, nome=m.chave, estrito=estrito,
                            permitir_material=True, dry_run=dry_run)

    if problemas:
        res = ResultadoDeReplay(ok=False, caso=m.chave, esperado=m.expected_state,
                                problemas=problemas)
        if estourar:
            raise FixtureInsegura("; ".join(problemas), resultado=res)
        return res

    return await _finalizar(journey, sessao, m, entrada, estourar,
                            exigir_fronteira=dry_run)


async def _finalizar(journey: Callable[..., Any], sessao: ReplayDeSessao,
                     m: ManifestoDeFixture, entrada: Optional[Dict[str, Any]],
                     estourar: bool, *, exigir_fronteira: bool) -> ResultadoDeReplay:
    """Roda, monta o veredito e — se pedido — estoura com ele anexado."""
    problemas: List[str] = []
    retorno: Any = None
    erro: Optional[ErroDeReplay] = None

    try:
        retorno = await _rodar_journey(journey, sessao, entrada)
    except ErroDeReplay as e:
        erro = e
        problemas.append(str(e))

    estado = _estado_do_retorno(retorno)
    if erro is None:
        if m.expected_state and estado and not _mesmo_estado(estado, m.expected_state):
            problemas.append(
                f"a journey terminou em `{estado}` e o manifesto espera "
                f"`{m.expected_state}`")
        if m.expected_state and not estado:
            problemas.append(
                "a journey nao devolveu estado legivel "
                "(`business_state` nem `status`)")

    if exigir_fronteira and erro is None and not sessao.parou_na_fronteira:
        problemas.append(
            "dry-run: a journey NUNCA chegou a fronteira material. §19.5 pede "
            "prova de que o codigo pararia/guardaria antes do efeito — nao "
            "chegar la nao e a mesma coisa que parar la")

    if sessao.nao_consumidas:
        problemas.append(
            f"interacoes gravadas e nunca pedidas: {sessao.nao_consumidas}")

    problemas.extend(sessao.divergencias)

    # Invariante, conferida e não presumida.
    executados = [e for e in sessao.efeitos if e.executado]
    if executados:  # pragma: no cover - impossivel por construcao
        problemas.append(
            f"🔴 {len(executados)} efeito(s) marcados como EXECUTADOS num "
            "replay: este modulo virou executor")

    res = ResultadoDeReplay(
        ok=not problemas, caso=m.chave, business_state=estado,
        esperado=m.expected_state, chamadas=sessao.total_de_chamadas,
        efeitos=list(sessao.efeitos), problemas=problemas,
        divergencias=list(sessao.divergencias),
        nao_consumidas=sessao.nao_consumidas,
        parou_na_fronteira=sessao.parou_na_fronteira, retorno=retorno)

    if erro is not None and estourar:
        erro.resultado = res
        raise erro
    return res


__all__ = [
    # contrato de fixture
    "ManifestoDeFixture", "validar_manifesto", "normalizar_efeito",
    "EFEITO_READ", "EFEITO_MATERIAL", "FONTES_CONHECIDAS", "FONTE_SINTETICA",
    "ESTADOS_DA_SPEC", "EQUIVALENCIA_DE_ESTADO",
    # guarda de PII
    "Achado", "varredura_de_pii", "bloqueantes", "fixture_e_segura",
    "SEVERIDADE_BLOQUEIA", "SEVERIDADE_REVISAR", "DOMINIOS_DE_EXEMPLO",
    "REDATOR_DISPONIVEL", "REDATOR_EM_USO",
    # replay
    "InteracaoGravada", "ChamadaObservada", "EfeitoMaterialRegistrado",
    "ReplayDeSessao", "ResultadoDeReplay",
    "replay_read_only", "replay_com_efeito",
    "ErroDeReplay", "ReplayDivergente", "EfeitoNaoPrevisto", "FixtureInsegura",
]
