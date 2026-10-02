# -*- coding: utf-8 -*-
"""SPEC-125 S3 · D2 — quem é o segurado, pelo TELEFONE, na MESMA corretora.

> *"Chamar o cliente pelo nome da outra conversa se for o mesmo número na mesma
> corretora; o CPF já está na conversa — só confirmar."* — Founder, 01/10/2026.

O que existe (📊 BLOCO 0 §4, SELECT de 01/10/2026):

```
a InfoCap NÃO busca por telefone   só CPF/CNPJ, nome, nº de apólice (infocap_connector.py:986-1036)
nenhuma tabela de apólice com telefone   (information_schema.tables)
UMA conversa por telefone por corretora  1.080 conversas WA, só 2 telefones com 2+ na mesma
   → "conversa anterior" = a parte ANTERIOR da MESMA conversa (session_id, webhook.py:1260)
72 telefones aparecem em 2 corretoras    → company_id no filtro E conferido no código (§7)
```

Então a fonte é a própria conversa desta corretora: o último CPF que o
SEGURADO disse, o nome que ele disse (ou o do contato), a apólice que a ficha já
guardou e o resumo do caso anterior. O resultado é o que o agente CONFIRMA em
uma linha — nunca afirma, nunca pergunta do zero.

⛔ Não grava nada. O CPF vive só no retorno e no bloco do turno — a ficha
durável não o recebe daqui (SPEC-117 §2 / D7: *"nunca no contexto: nome,
CPF/CNPJ…"*, cabeçalho de `app/services/policy_context.py`).
⛔ Não chama a InfoCap: com o CPF, quem consulta é a ferramenta que já existe
(`infocap_policy_lookup`, com cache durável), quando o modelo decidir.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Mensagens lidas da conversa quando o chamador não entrega o histórico. É o
#: teto de UMA resposta do PostgREST (`o_fim_do_atendimento._LEITURA_LARGA_DA_JANELA`).
#: 📊 mensagens por conversa WA: p90 90 / máx 2.834 (BLOCO 0 §3) — 1.000 cobre
#: o p99 com folga; acima disso o CPF dito há mais de 1.000 mensagens não vem.
TETO_DE_MENSAGENS = 1000

#: Teto do bloco do prompt (ordem do gerente: ≤ 600 caracteres).
TETO_DO_BLOCO = 600

# ---- CPF / CNPJ dito pelo segurado (régua estrita do BLOCO 0 §4) ---------- #
_CPF_FORMATADO = re.compile(r"(?<!\d)(\d{3}\.\d{3}\.\d{3}-\d{2})(?!\d)")
_CNPJ_FORMATADO = re.compile(r"(?<!\d)(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})(?!\d)")
_DOC_APOS_A_PALAVRA = re.compile(r"\b(?:cpf|cnpj)\b\D{0,20}?((?:\d[\s.\-/]?){11,14})", re.IGNORECASE)
_ONZE_DIGITOS = re.compile(r"(?<!\d)(\d{11})(?!\d)")

# ---- o nome que o segurado disse ------------------------------------------ #
#: 🔴 Conserto X3 (juiz B3): o nome dito COMO NOME — "meu nome é X", "me chamo X".
#: É a única régua que pode decidir alguma coisa (o corte de terceiro da S8a).
_NOME_COMO_NOME = re.compile(
    r"\b(?:meu nome (?:é|e|eh)|me chamo)\s*:?\s+([A-Za-zÀ-ÿ]{2,})", re.IGNORECASE)
#: As formas fracas — só para o "nome provável" do bloco (que manda CONFIRMAR), e só com
#: MAIÚSCULA: "aqui é o seguinte", "aqui é a portaria", "aqui é a minha mãe" não são nome
#: (📊 juiz B3: viravam "Seguinte", "Portaria", "Minha"). "Sou o João" com S maiúsculo
#: também vale (RT P12).
_NOME_FRACO = re.compile(
    r"\b(?:[Aa]qui (?:é|e|eh) (?:o|a)|[Qq]uem fala (?:é|e|eh)(?: o| a)?|[Ss]ou (?:o|a))\s+"
    r"([A-ZÀ-Ý][a-zà-ÿ]{1,})")
#: Palavras que a régua de nome casaria e não são nome de gente.
_NAO_E_NOME = frozenset({
    "segurado", "segurada", "cliente", "titular", "dono", "dona", "proprietario",
    "proprietário", "filho", "filha", "esposo", "esposa", "marido", "mulher", "mae",
    "mãe", "pai", "irmao", "irmão", "irma", "irmã", "responsavel", "responsável",
    "motorista", "condutor", "corretor", "corretora", "sindico", "síndico", "mesmo",
    "mesma", "que", "quem", "seu", "sua", "seguinte", "problema", "minha", "meu",
    "carro", "casa", "portaria", "porteiro", "zelador", "pessoal", "gente", "empresa",
    "escritorio", "escritório", "recepcao", "recepção", "oficina", "mecanico", "mecânico",
    "guincho", "loja", "administracao", "administração", "proprio", "próprio", "propria",
    "própria", "outro", "outra", "dela", "dele", "nome",
})

#: constante_justificada: apelido → as iniciais dos nomes de que ele costuma vir (X3: "me
#: chamo Zé" com titular J*** não é outra pessoa). Só os apelidos que NÃO começam pela
#: inicial do nome — os outros ("Rafa", "Gabi") já batem pela inicial. "Júnior", "Neto" e
#: "Filho" são sufixo de qualquer nome (`*`: batem com qualquer titular).
_APELIDOS = {
    "ze": "j", "zezinho": "j", "zeca": "j", "juca": "j", "pepe": "j",
    "chico": "f", "chica": "f", "chiquinho": "f", "chiquinha": "f", "paco": "f", "quico": "f",
    "kiko": "fh", "nando": "f", "nanda": "f", "lipe": "f", "fafa": "f",
    "beto": "rahl", "betinho": "rahl", "betao": "rahl",
    "tiao": "s", "bastiao": "s",
    "dudu": "e", "duda": "em", "guto": "ag", "toninho": "a", "tonho": "a", "toni": "a", "tony": "a",
    "nico": "an", "neca": "m", "lili": "aeil", "malu": "m", "manu": "em", "mila": "cm",
    "tata": "ot", "dede": "a", "didi": "a", "caca": "c", "bia": "b", "gil": "g", "nene": "m",
    "junior": "*", "neto": "*", "filho": "*",
}


def _sem_acento(texto: Any) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def nome_bate_com_as_iniciais(nome: Any, iniciais: Any) -> bool:
    """O nome dito pode ser do titular cujas iniciais são `iniciais`? **PURA.**

    Tolerante de propósito (X3): QUALQUER inicial do nome do titular vale (quem é
    chamado pelo nome do meio continua sendo o titular) e os apelidos comuns. Sem
    iniciais ou sem nome → não há o que contradizer.
    """
    ini = {_sem_acento(i)[:1] for i in (iniciais or []) if str(i or "").strip()}
    n = _sem_acento(nome).strip()
    if not ini or not n:
        return True
    if n[:1] in ini:
        return True
    possiveis = _APELIDOS.get(n, "")
    return possiveis == "*" or bool(set(possiveis) & ini)


def _so_digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _documento_valido(digitos: str) -> bool:
    """CPF/CNPJ pelo DÍGITO VERIFICADOR — a régua que já existe (CLAUDE.md §5).

    ⛔ Sem a régua, nenhum documento: um número de 11 dígitos que não fecha a
    conta pode ser telefone, protocolo ou renavam, e reaproveitá-lo como CPF
    abriria o caso na apólice de outra pessoa.
    """
    try:
        from app.agents.tools.insurer_dispatch_tool import documento_br_valido
    except Exception as exc:  # noqa: BLE001
        logger.warning("[QUEM] régua de documento indisponível (%s)", type(exc).__name__)
        return False
    return bool(documento_br_valido(digitos))


#: constante_justificada: as palavras com que o segurado DIZ que um número é
#: telefone. Só elas tornam um número de 11 dígitos com DV de CPF válido
#: ambíguo de verdade (SPEC-125 · S8b).
_PALAVRA_DE_TELEFONE = re.compile(
    r"\b(?:celular|cel|telefone|tel|fone|zap|whats(?:app)?|wpp|contato)\b", re.IGNORECASE)
_JANELA_DO_ROTULO = 30


def _dito_como_telefone(s: str, inicio: int, fim: int, corte_antes: str = r"[\d\n]") -> bool:
    """O segurado disse que ESTE número é celular/telefone/zap? — **PURA**.

    🔴 SPEC-125 · S8b. Antes a régua era a CARA do número (DDD + 9): 📊 a S4
    mediu `52998224725` — CPF de DV válido — descartado por ter o 3º dígito 9.
    O DV decide se é CPF; só o RÓTULO dito pelo segurado o desfaz.

    ⚠️ Rótulo de OUTRO número não conta: antes, só o trecho depois do último
    dígito; depois, só se nenhum número vier em seguida ("52998224725, celular
    11987654321" — o "celular" é do segundo).
    """
    antes = re.split(corte_antes, s[max(0, inicio - _JANELA_DO_ROTULO):inicio])[-1]
    if _PALAVRA_DE_TELEFONE.search(antes):
        return True
    depois = s[fim:fim + _JANELA_DO_ROTULO]
    corte = re.search(r"[\d\n]", depois)
    if corte and depois[corte.start()].isdigit():
        return False
    return bool(_PALAVRA_DE_TELEFONE.search(depois[:corte.start()] if corte else depois))


def documentos_ditos(texto: Any) -> List[str]:
    """Os CPF/CNPJ (só dígitos, válidos) que aparecem num texto, na ordem. **PURA.**

    11 dígitos SOLTOS: o dígito verificador decide (abaixo); com DV válido só
    não é CPF o número que o segurado DISSE ser telefone (`_dito_como_telefone`).
    """
    s = str(texto or "")
    achados: List[tuple] = []
    for regra in (_CPF_FORMATADO, _CNPJ_FORMATADO, _DOC_APOS_A_PALAVRA):
        for m in regra.finditer(s):
            achados.append((m.start(), _so_digitos(m.group(1))))
    for m in _ONZE_DIGITOS.finditer(s):
        if not _dito_como_telefone(s, m.start(), m.end()):
            achados.append((m.start(), m.group(1)))
    saida: List[str] = []
    for _pos, dig in sorted(achados):
        if len(dig) in (11, 14) and dig not in saida and _documento_valido(dig):
            saida.append(dig)
    return saida


def _nome_valido(nome: str) -> str:
    nome = str(nome or "").strip()
    if not nome or nome.lower() in _NAO_E_NOME or _sem_acento(nome) in _NAO_E_NOME:
        return ""
    return nome[:1].upper() + nome[1:].lower()


def nome_dito_como_nome(texto: Any) -> str:
    """O nome que o segurado disse COMO NOME ("meu nome é", "me chamo"), ou `""`. **PURA.**

    🔴 X3: é a ÚNICA régua de nome que o corte de terceiro (S8a) usa.
    """
    for m in _NOME_COMO_NOME.finditer(str(texto or "")):
        nome = _nome_valido(m.group(1))
        if nome:
            return nome
    return ""


def nome_dito(texto: Any) -> str:
    """O primeiro nome que o segurado DISSE ser o dele, ou `""`. **PURA.**

    O nome dito como nome vence; as formas fracas ("Aqui é o João", "Sou a Ana") só
    com maiúscula e fora da lista de não-nomes. Serve ao "nome provável" do bloco, que
    manda CONFIRMAR antes de usar.
    """
    forte = nome_dito_como_nome(texto)
    if forte:
        return forte
    for m in _NOME_FRACO.finditer(str(texto or "")):
        nome = _nome_valido(m.group(1))
        if nome:
            return nome
    return ""


def primeiro_nome_do_contato(user_name: Any) -> str:
    """O primeiro nome do contato do WhatsApp — `""` se for número ou sem letra.

    📊 `conversations.user_name`: nome em 610, número em 470 (BLOCO 0 §4).
    """
    for parte in str(user_name or "").split():
        limpo = re.sub(r"[^A-Za-zÀ-ÿ]", "", parte)
        if len(limpo) >= 2 and limpo.lower() not in _NAO_E_NOME:
            return limpo[:1].upper() + limpo[1:].lower()
        if limpo:
            return ""
    return ""


def mascarar_documento(digitos: str) -> str:
    """`...4725` — a decisão de máscara que JÁ existe (`pii_da_sessao`, §5)."""
    try:
        from app.services.pii_da_sessao import mascarar_valor

        return str(mascarar_valor("titular_cpf", digitos))
    except Exception:  # noqa: BLE001
        return "..." + digitos[-4:]


def _quando(valor: Any) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(valor or "").replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _do_segurado(m: Any) -> bool:
    return isinstance(m, dict) and str(m.get("role") or "").strip().lower() in ("user", "human", "cliente")


def _em_ordem(historico: Any) -> List[Dict[str, Any]]:
    """Mais antiga primeiro. Linha sem data fica na posição em que veio."""
    linhas = [m for m in (historico or []) if isinstance(m, dict)]
    if all(_quando(m.get("created_at")) for m in linhas):
        linhas.sort(key=lambda m: _quando(m.get("created_at")))
    return linhas


def _inicio_do_assunto_atual(linhas: List[Dict[str, Any]], n_dias: int) -> int:
    """Índice da 1ª mensagem do assunto ATUAL: depois do último silêncio > N dias.

    É a mesma régua do reencontro (`o_fim_do_atendimento.janela_de_silencio_dias`,
    T21 — a regra dos 7 dias). `0` = não houve reencontro.
    """
    inicio = 0
    for i in range(1, len(linhas)):
        a, b = _quando(linhas[i - 1].get("created_at")), _quando(linhas[i].get("created_at"))
        if a and b and n_dias > 0 and (b - a).total_seconds() > n_dias * 86400:
            inicio = i
    return inicio


def identidade_vazia() -> Dict[str, Any]:
    return {"nome": "", "nome_origem": "", "cpf": "", "cpf_mascarado": "", "cpf_final": "",
            "cpfs_distintos": 0, "cpf_de_assunto_anterior": False, "apolice": "",
            "caso_anterior": "", "perguntar_cpf": True}


# ---- 🔴 Conserto X2 · de QUEM é o documento (RT B2 · juiz B2) --------------- #
def _de_outra_pessoa(doc: str, falas: List[str]) -> bool:
    """A conversa atribui `doc` a OUTRA pessoa ("o cpf dela", "da minha mãe")? **PURA.**

    A régua é a do corte de terceiro (`infocap_tool.de_quem_e_a_apolice`, S8a) — nunca
    uma segunda (§5). ⛔ Sem a régua, o documento NÃO é oferecido: o agente pergunta
    (o pior caso é uma pergunta a mais; o outro lado é a apólice da mãe).
    """
    try:
        from app.agents.tools.infocap_tool import de_quem_e_a_apolice

        return bool(de_quem_e_a_apolice(doc, falas).get("terceiro"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[QUEM] régua de terceiro indisponível (%s)", type(exc).__name__)
        return True


def documentos_proprios(falas: Any) -> List[str]:
    """Os CPF/CNPJ que o segurado disse COMO SEUS nas `falas` — na ordem. **PURA.**

    Fica de fora todo documento que a conversa atribui a outra pessoa (X2). Usado pelo
    fiscal da pergunta repetida (`nodes._documentos_ja_ditos`) sobre as falas do turno.
    """
    textos = [str(f or "") for f in (falas or []) if str(f or "").strip()]
    vistos: List[str] = []
    for t in textos:
        for d in documentos_ditos(t):
            if d not in vistos:
                vistos.append(d)
    return [d for d in vistos if not _de_outra_pessoa(d, textos)]


def _assuntos(linhas: List[Dict[str, Any]], n_dias: int) -> List[int]:
    """O índice de início de CADA assunto (silêncio > N dias abre um novo). **PURA.**"""
    inicios = [0]
    for i in range(1, len(linhas)):
        a, b = _quando(linhas[i - 1].get("created_at")), _quando(linhas[i].get("created_at"))
        if a and b and n_dias > 0 and (b - a).total_seconds() > n_dias * 86400:
            inicios.append(i)
    return inicios


#: "sim" do segurado à pergunta de confirmação do documento ("é o CPF final 4725?").
_SIM = re.compile(r"^\W*(?:sim|s|ss|isso|exato|exatamente|correto|certo|confirmo|confirmado|positivo|"
                  r"pode|ok|okay|perfeito|esse mesmo|e esse|eh esse|e sim|eh sim|e o meu|eh o meu|"
                  r"e isso|eh isso|esse|este|isso mesmo|uhum|aham|beleza|blz)\b")
_NAO = re.compile(r"\bn[aã]o\b|\bnegativo\b|\boutro\b|\berrado\b")
#: 🔴 SPEC-126 U3-B (📊 U1 C11): "Sou eu sim" à pergunta "falo com o titular do CPF final
#: 4725?" NÃO era confirmação — `_SIM` só olha o COMEÇO da fala ("sou" não é "sim") — e o
#: agente pedia de novo o CPF que já estava na conversa. A fala INTEIRA tem de ser a
#: confirmação ("sou eu", "sou eu sim", "sim, sou eu", "eu mesmo", "é ele mesmo"): "sou eu
#: que tô com o carro do meu pai" continua NÃO confirmando o CPF (do pai).
_SOU_EU = re.compile(
    r"^\W*(?:(?:sim|isso|e|eh)\W+)?(?:sou eu|eu mesm[oa]|e eu|eh eu|(?:e|eh) (?:ele|ela) mesm[oa]|"
    r"(?:o|a) propri[oa])(?:\W+(?:sim|mesm[oa]|msm|isso))?\W*$")


def _confirmou_agora(linhas: List[Dict[str, Any]], inicio: int, doc: str) -> bool:
    """No assunto ATUAL, NÓS perguntamos pelo final deste documento e ELE disse "sim"? **PURA.**

    🔴 X2: só depois disso o CPF de um assunto anterior entra INTEIRO no prompt.
    🔴 SPEC-126 U3-B: o "sim" que fala de OUTRA pessoa ("sim, sou eu que tô com o carro do
    meu pai") não confirma — a régua é a do corte de terceiro (`_de_outra_pessoa`), não uma
    segunda.
    """
    final = doc[-4:]
    for i in range(max(inicio, 1), len(linhas)):
        m = linhas[i]
        if not _do_segurado(m):
            continue
        anterior = linhas[i - 1]
        if _do_segurado(anterior) or final not in str(anterior.get("content") or ""):
            continue
        fala = _sem_acento(m.get("content")).strip()
        if _NAO.search(fala):
            continue
        if (_SIM.search(fala) or _SOU_EU.search(fala)) and not _cita_outra_pessoa(
                doc, str(m.get("content") or ""), fala):
            return True
    return False


def _cita_outra_pessoa(doc: str, fala_crua: str, fala: str) -> bool:
    """A resposta fala de OUTRA pessoa ("sim, sou eu que tô com o carro DO MEU PAI")? **PURA.**

    O vocabulário de "dono que não é quem fala" é o do corte de terceiro
    (`infocap_tool._DONO_OUTRO`) e a régua inteira dele (`_de_outra_pessoa`) — nunca uma
    terceira lista (§5). ⛔ Sem a régua, cita: o pior caso é perguntar o CPF de novo."""
    try:
        from app.agents.tools.infocap_tool import _DONO_OUTRO
    except Exception:  # noqa: BLE001
        return True
    return bool(re.search(r"\b" + _DONO_OUTRO + r"\b", fala)) or _de_outra_pessoa(doc, [fala_crua])


def montar(*, historico: Any, user_name: Any = "", ficha: Optional[Dict[str, Any]] = None,
           resumos: Optional[List[Dict[str, Any]]] = None, n_dias: int = 7) -> Dict[str, Any]:
    """O que já sabemos — a partir do que JÁ foi lido desta corretora. **PURA.**

    ⛔ Quem chama garante que `historico`, `ficha` e `resumos` são da MESMA
    corretora (é o que `quem_e_o_segurado` faz, com filtro e cinto).

    🔴 Conserto X2: (1) só entra o documento que o segurado disse como SEU — o que a
    conversa atribuiu a outra pessoa, em QUALQUER assunto, nunca é oferecido; (2) o de
    um assunto ANTERIOR sai só com o FINAL (`cpf` vazio) até ele confirmar no assunto
    atual — telefone pode ser compartilhado (D2).
    """
    saida = identidade_vazia()
    linhas = _em_ordem(historico)
    inicios = _assuntos(linhas, n_dias)
    inicio = inicios[-1]

    def _assunto_de(i: int) -> int:
        return max(k for k, ini in enumerate(inicios) if ini <= i)

    falas_por_assunto: Dict[int, List[str]] = {}
    docs: List[tuple] = []   # (indice, digitos) — só o que o SEGURADO escreveu
    nome = ""
    for i, m in enumerate(linhas):
        if not _do_segurado(m):
            continue
        falas_por_assunto.setdefault(_assunto_de(i), []).append(str(m.get("content") or ""))
        for d in documentos_ditos(m.get("content")):
            docs.append((i, d))
        nome = nome_dito(m.get("content")) or nome
    de_outro = {d for i, d in docs if _de_outra_pessoa(d, falas_por_assunto.get(_assunto_de(i), []))}
    docs = [(i, d) for i, d in docs if d not in de_outro]
    if docs:
        indice, ultimo = docs[-1]
        anterior = indice < inicio and not _confirmou_agora(linhas, inicio, ultimo)
        saida.update(cpf="" if anterior else ultimo, cpf_mascarado=mascarar_documento(ultimo),
                     cpf_final=ultimo[-4:], cpfs_distintos=len({d for _i, d in docs}),
                     cpf_de_assunto_anterior=indice < inicio, perguntar_cpf=False)
    if nome:
        saida.update(nome=nome, nome_origem="dito pelo segurado")
    elif primeiro_nome_do_contato(user_name):
        saida.update(nome=primeiro_nome_do_contato(user_name), nome_origem="contato do WhatsApp")

    saida["apolice"] = _apolice_da_ficha(ficha)
    if inicio > 0:
        saida["caso_anterior"] = _caso_anterior(linhas[:inicio], resumos,
                                                antes_de=_quando(linhas[inicio].get("created_at")))
    return saida


def _apolice_da_ficha(ficha: Optional[Dict[str, Any]]) -> str:
    """A apólice que a ficha DESTE caso já guardou (cache da consulta por CPF).

    ⛔ Pela leitura única (`attendance_ficha.apolice_do_caso`), nunca varrendo
    `apolices[]`. No assunto novo a ficha já a apagou (SPEC-117 §7) — e é certo:
    com o CPF, o modelo reconsulta.
    """
    if not isinstance(ficha, dict):
        return ""
    try:
        from app.services.attendance_ficha import (ORIGEM_SISTEMA_DE_GESTAO, apolice_de_outra_pessoa,
                                                   apolice_do_caso, origem_de, valor_de)
        from app.services.policy_context import nome_humano_do_ramo
    except Exception:  # noqa: BLE001
        return ""
    # 🔴 SPEC-126 U3-B (D1): a apólice do TITULAR, com o parente falando, não volta ao prompt
    #    por este bloco — o da ficha (`attendance_ficha._bloco_da_apolice`) já diz o que vale.
    if apolice_de_outra_pessoa(ficha=ficha):
        return ""
    ap = apolice_do_caso(ficha=ficha) or {}
    partes = [str(ap.get("numapo") or "").strip(), nome_humano_do_ramo(ap.get("ramo")) or "",
              str(ap.get("seguradora") or "").strip().title()]
    if ap.get("vigencia_fim"):
        partes.append(("vigente até " if ap.get("vigente") else "vigência até ") + str(ap["vigencia_fim"]))
    veiculo = (ficha.get("confirmados") or {}).get("veiculo_descricao")
    if veiculo and origem_de(veiculo) == ORIGEM_SISTEMA_DE_GESTAO and ap:
        partes.append(str(valor_de(veiculo)))
    return " · ".join(p for p in partes if p) if ap else ""


def _caso_anterior(anteriores: List[Dict[str, Any]], resumos: Optional[List[Dict[str, Any]]],
                   antes_de: Optional[datetime] = None) -> str:
    """O resumo do assunto anterior — o do banco, ou a 1ª fala dele. Sem documento.

    Só vale resumo escrito ANTES do assunto atual começar: o resumo de hoje é
    deste caso, não do anterior.
    """
    quando = _quando((anteriores[-1] if anteriores else {}).get("created_at"))
    texto = ""
    for r in resumos or []:
        feito = _quando((r or {}).get("created_at")) if isinstance(r, dict) else None
        if antes_de and feito and feito >= antes_de:
            continue
        if isinstance(r, dict) and str(r.get("summary") or "").strip():
            texto = str(r["summary"])
            break
    if not texto:
        primeira = next((m for m in anteriores if _do_segurado(m) and str(m.get("content") or "").strip()), {})
        texto = str(primeira.get("content") or "")
    texto = re.sub(r"\d[\d.\-/ ]{6,}\d", "[número]", " ".join(texto.split()))[:160]
    if not texto:
        return ""
    return (f"em {quando.strftime('%d/%m/%Y')}: " if quando else "") + texto


# --------------------------------------------------------------------------- #
# I/O — company_id em TODA leitura, no filtro E conferido no código (§7)
# --------------------------------------------------------------------------- #
def _da_corretora(linhas: Any, empresa: str) -> List[Dict[str, Any]]:
    """🔴 O CINTO: linha de outra corretora nunca passa, mesmo que o filtro do
    banco falhe. 📊 72 telefones aparecem em 2 corretoras (BLOCO 0 §4)."""
    return [x for x in (linhas or []) if isinstance(x, dict)
            and str(x.get("company_id") or "") == empresa]


def formas_do_telefone(fone: Any) -> List[str]:
    """Todas as grafias do número como `conversations.user_phone` as guarda. **PURA.**

    🔴 📊 01/10/2026 (`select length(digitos), left(digitos,2)='55', count(*) from
    conversations where channel='whatsapp' group by 1,2`): **905 de 1.081**
    conversas guardam o número COM o `55` (815 com 12 dígitos + 89 com 13 + 1).
    `o_fim_do_atendimento._variantes_do_telefone` TIRA o `55` — sozinha, ela não
    acha 84 % das conversas (a 1ª medição deste motor sobre o banco real achou
    CPF em 3 de 1.081). Aqui entram as variantes COM e SEM o `55`, e o número cru.
    """
    from app.services.o_fim_do_atendimento import _variantes_do_telefone

    cru = _so_digitos(fone)
    base = _variantes_do_telefone(cru) or set()
    return sorted({cru, *base, *("55" + v for v in base)} - {""})


async def _conversa_do_telefone(db, empresa: str, fone: str) -> Dict[str, Any]:
    from app.services.o_fim_do_atendimento import _cliente, _executar

    formas = formas_do_telefone(fone)
    achado = await _executar(_cliente(db).table("conversations")
                             .select("id, company_id, user_id, user_name, session_id, ficha_atendimento, updated_at")
                             .eq("company_id", empresa)            # 🔴 §7
                             .eq("channel", "whatsapp")
                             .in_("user_phone", formas)
                             .order("updated_at", desc=True)
                             .limit(5))
    linhas = _da_corretora(getattr(achado, "data", None), empresa)
    linhas.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return linhas[0] if linhas else {}


async def _resumos(db, empresa: str, conversa: Dict[str, Any]) -> List[Dict[str, Any]]:
    from app.services.o_fim_do_atendimento import _cliente, _executar

    consulta = (_cliente(db).table("session_summaries")
                .select("company_id, summary, created_at")
                .eq("company_id", empresa))                          # 🔴 §7
    if conversa.get("user_id"):
        consulta = consulta.eq("user_id", str(conversa["user_id"]))
    elif conversa.get("session_id"):
        consulta = consulta.eq("session_id", str(conversa["session_id"]))
    else:
        return []
    achado = await _executar(consulta.order("created_at", desc=True).limit(3))
    return _da_corretora(getattr(achado, "data", None), empresa)


async def quem_e_o_segurado(company_id: str, telefone: str, historico: Any = None,
                            *, db: Any = None, n_dias: Optional[int] = None) -> Dict[str, Any]:
    """`{nome, nome_origem, cpf, cpf_mascarado, cpfs_distintos, cpf_de_assunto_anterior,
    apolice, caso_anterior, perguntar_cpf}` deste telefone NESTA corretora.

    `historico` (opcional): as mensagens desta conversa (`role`, `content`,
    `created_at`), já da MESMA corretora — a fonte única da S2. Sem ele, lê de
    `messages` pela conversa achada com `company_id`. **Nunca levanta**: no
    escuro devolve a identidade vazia, e o agente pergunta como sempre.
    """
    vazio = identidade_vazia()
    empresa = str(company_id or "").strip()
    fone = _so_digitos(telefone)
    if not empresa or not fone:
        return vazio
    try:
        if db is None:
            from app.core.database import get_supabase_client
            db = get_supabase_client()
        if db is None:
            return vazio
        from app.services.o_fim_do_atendimento import janela_de_mensagens, janela_de_silencio_dias

        conversa = await _conversa_do_telefone(db, empresa, fone)
        if not conversa:
            return montar(historico=historico or [], n_dias=janela_de_silencio_dias()
                          if n_dias is None else int(n_dias))
        if historico is None:
            linhas, erro = await janela_de_mensagens(db, str(conversa.get("id") or ""),
                                                     teto=TETO_DE_MENSAGENS)
            historico = [] if erro else linhas
        return montar(historico=historico, user_name=conversa.get("user_name"),
                      ficha=conversa.get("ficha_atendimento"),
                      resumos=await _resumos(db, empresa, conversa),
                      n_dias=janela_de_silencio_dias() if n_dias is None else int(n_dias))
    except Exception as exc:  # noqa: BLE001 — ⛔ nada de conteúdo no log
        logger.warning("[QUEM] identidade pelo telefone indisponível (%s)", type(exc).__name__)
        return vazio


def bloco_para_o_prompt(quem: Optional[Dict[str, Any]]) -> str:
    """O texto do bloco — ≤ `TETO_DO_BLOCO` caracteres, ou `""` se nada se sabe.

    Escrito para um modelo inteligente: diz o que se sabe, de onde veio, e a
    ÚNICA regra que importa — confirme, não pergunte; primeiro nome antes do
    "sim" (telefone pode ser compartilhado, D2); ao segurado o CPF só mascarado
    (T19).
    """
    q = quem or {}
    final = str(q.get("cpf_final") or str(q.get("cpf") or "")[-4:])
    if not (q.get("nome") or q.get("cpf") or final or q.get("apolice") or q.get("caso_anterior")):
        return ""
    linhas = ["=== 🪪 O QUE JÁ SABEMOS DESTE SEGURADO (este telefone, esta corretora) ===",
              "Confirme numa linha; não pergunte do zero. Antes do \"sim\", só o 1º nome."]
    if q.get("nome"):
        linhas.append(f"· nome provável: {q['nome']} ({q.get('nome_origem')}) — confirme antes de usar")
    mais = "; disse outro também — confirme qual" if int(q.get("cpfs_distintos") or 0) > 1 else ""
    if q.get("cpf"):
        quando = ("num assunto anterior e CONFIRMOU agora" if q.get("cpf_de_assunto_anterior")
                  else "nesta conversa")
        linhas.append(f"· CPF/CNPJ que ele disse {quando}: {q['cpf']} — use nas ferramentas; "
                      f"a ele, só \"final {final}\"{mais}")
    elif final:
        # 🔴 X2: o de um assunto ANTERIOR não entra inteiro — o telefone pode ser de outra
        #    pessoa agora. Confirma-se o FINAL com ele; depois do "sim" o número aparece aqui.
        linhas.append(f"· CPF/CNPJ que ele disse num assunto anterior: final {final} — antes de usar, "
                      f"confirme com ele (\"é o CPF final {final}?\"); o número volta aqui depois do "
                      f"\"sim\"{mais}")
    if q.get("apolice"):
        linhas.append(f"· apólice do caso: {q['apolice']}")
    if q.get("caso_anterior"):
        linhas.append(f"· caso anterior {q['caso_anterior']}")
    linhas.append("Se ele disser que não é, ignore este bloco.")
    texto = "\n".join(linhas)
    if len(texto) > TETO_DO_BLOCO:
        # o que se corta é o caso anterior (memória), nunca a regra nem o CPF
        excesso = len(texto) - TETO_DO_BLOCO
        linhas = [(l[: max(0, len(l) - excesso - 1)] + "…") if l.startswith("· caso anterior") else l
                  for l in linhas]
        texto = "\n".join(linhas)[:TETO_DO_BLOCO]
    return texto


# --------------------------------------------------------------------------- #
# 🔴 Conserto X2 · T19 EM CÓDIGO — o documento inteiro nunca SAI ao segurado
# --------------------------------------------------------------------------- #
#: Rótulos que dizem que um número de 11/14 dígitos SEM pontuação NÃO é documento —
#: telefone, protocolo, OS, senha, apólice, renavam… (T6: esses saem EXATOS).
#: 🔴 AJUSTE ZN · Z-N2 — "Confirma os dados: 529…, apólice…" saía CRU porque o ARTIGO "os"
#:    casava a sigla OS (ordem de serviço): a sigla agora só em MAIÚSCULAS. "pedido" saiu da
#:    lista (nomeia o ASSUNTO — "dados do pedido: 529…" —, não o número; "número do pedido"
#:    continua). E o rótulo só vale na MESMA oração do número: vírgula/ponto e vírgula de lista
#:    cortam ("contato neste número, titular 529…" — o "contato" é do item anterior).
_ROTULO_DE_OUTRO_NUMERO = re.compile(
    r"\b(?:celular|cel|telefone|tel|fone|zap|whats(?:app)?|wpp|contato|liga\w*|lig[ue]\w*|"
    r"protocolo|senha|(?-i:OS|O\.S\.?)|ordem de servi[cç]o|chamado|atendimento|sinistro|ap[oó]lice|"
    r"renavam|chassi|placa|boleto|c[oó]digo|n[uú]mero d[oae])(?!\w)", re.IGNORECASE)


#: 🔴 SPEC-125 CONSERTO Z · N3 do laudo de confirmação — o rótulo que vem DEPOIS do número,
#:    colado nele: "O número 12345678909 é o seu protocolo." era mascarado ("final 8909")
#:    e o protocolo, que é T6 (sai EXATO), chegava errado. 📊 ~1 % dos números de 11 dígitos
#:    fecham o DV de CPF (laudo, 181/20.000). ⚠️ Só a forma que DIZ o que o número é
#:    ("X é o seu protocolo", "X (protocolo)", "X — protocolo da seguradora"): "o 529… está
#:    certo para abrir o pedido?" NÃO desmascara (o "pedido" ali não rotula o número).
#: 🔴 SPEC-125 AJUSTE ZN · Z-N2 do laudo de confirmação nº 2 — a forma acima desmascarava o
#:    CPF de um RESUMO em lista: "Confirma os dados: 529…, apólice 1234567" e "529… (pedido de
#:    guincho)" saíam CRUS — e a `REGRA_DO_RESUMO_DE_CONFIRMACAO` manda pôr o CPF no resumo.
#:    constante_justificada: depois do número, só o rótulo que DIZ o que ELE é:
#:    · PREDICADO ("é/foi/fica/será o seu protocolo", "é o número do pedido");
#:    · APOSTO colado ("(protocolo da seguradora)", "— protocolo da assistência");
#:    e só substantivo de IDENTIFICADOR (protocolo, senha, OS, código…). Vírgula de lista nunca
#:    rotula; "pedido/apólice/assistência" soltos nomeiam o ASSUNTO ("pedido de guincho"), não o
#:    número — só entram como "número do pedido". E o número que É o documento do caso
#:    mascara sempre (`documentos_do_caso`), rotulado ou não.
_IDENTIFICADOR_DEPOIS = (
    r"protocolo|ordem de servi[cç]o|(?-i:OS)|senha|renavam|chassi|boleto|c[oó]digo|"
    r"n[uú]mero\s+d[oae]\s+(?:protocolo|atendimento|assist[eê]ncia|ordem de servi[cç]o|os|"
    r"pedido|chamado|sinistro|ap[oó]lice|boleto)")
_ROTULO_DEPOIS_DO_NUMERO = re.compile(
    r"^\s*(?:"
    # predicado: "… é o seu protocolo", "… foi o número do atendimento", "… fica o chamado"
    r"(?:e|é|eh|era|sera|será|foi|fica)\s+(?:(?:o|a)\s+)?(?:(?:seu|sua|nosso|nossa)\s+)?"
    r"(?:" + _IDENTIFICADOR_DEPOIS + r"|atendimento|chamado|sinistro)\b"
    # aposto colado: "(protocolo da seguradora)", "— protocolo da assistência"
    r"|[-–—(]\s*(?:(?:o|a)\s+)?(?:(?:seu|sua)\s+)?(?:" + _IDENTIFICADOR_DEPOIS + r")\b)",
    re.IGNORECASE)


def documentos_do_caso(textos: Any) -> List[str]:
    """Os CPF/CNPJ que pertencem ao CASO (ditos pelo segurado, na ficha, nos argumentos das
    ferramentas) — na ordem. **PURA.** O número que o PRÓPRIO texto rotula como protocolo,
    telefone… ("meu protocolo é 123…") não é documento do caso."""
    saida: List[str] = []
    for t in textos or []:
        s = str(t or "")
        for d in documentos_ditos(s):
            if d in saida:
                continue
            soltos = list(re.finditer(r"(?<!\d)%s(?!\d)" % d, s))
            if soltos and all(_rotulado_como_outro_numero(s, m.start(), m.end()) for m in soltos):
                continue
            saida.append(d)
    return saida


def _rotulado_como_outro_numero(s: str, inicio: int, fim: int) -> bool:
    antes = re.split(r"[\d\n,;]", s[max(0, inicio - _JANELA_DO_ROTULO):inicio])[-1]
    if _ROTULO_DE_OUTRO_NUMERO.search(antes):
        return True
    if _ROTULO_DEPOIS_DO_NUMERO.search(s[fim:fim + _JANELA_DO_ROTULO].replace("*", "")):
        return True
    # Z-N2: na SAÍDA, o rótulo de telefone também só vale na mesma oração (a lista corta)
    return _dito_como_telefone(s, inicio, fim, corte_antes=r"[\d\n,;]")


def mascarar_documentos_na_saida(texto: Any, documentos_do_caso: Any = None) -> str:
    """A resposta ao SEGURADO com todo CPF/CNPJ VÁLIDO inteiro trocado por `final XXXX`. **PURA.**

    🔴 T19 (MANTER) deixa de depender do modelo obedecer ao prompt: este é o cinto no
    código, aplicado no ponto em que a resposta final sai (`nodes.agent_node`).

    DECISÃO — mascara SEMPRE, inclusive o número que o próprio segurado acabou de
    digitar: repetir o documento inteiro não ajuda ninguém (ele já o tem), e a mensagem
    pode ser lida por outra pessoa no mesmo telefone ou encaminhada. Confirmar pelo final
    é a forma do produto desde a SPEC-063. O lado seguro custa zero ao atendimento.

    Só o que fecha o dígito verificador vira máscara: CPF/CNPJ pontuado, ou depois da
    palavra CPF/CNPJ, sempre; 11/14 dígitos soltos, salvo quando rotulados como outro
    número (telefone, protocolo, senha, apólice… — esses saem exatos, T6).

    🔴 Z-N2: `documentos_do_caso` (os CPF/CNPJ do caso — `documentos_do_caso()` sobre a
    conversa, a ficha e os argumentos) mascaram SEMPRE, rotulados ou não: o modelo que
    chama o CPF do titular de "protocolo" não o põe inteiro no WhatsApp.
    """
    do_caso = {_so_digitos(d) for d in (documentos_do_caso or []) if _so_digitos(d)}
    s = str(texto or "")
    if not s or not re.search(r"\d{3}", s):
        return s
    trocas: List[tuple] = []
    for regra in (_CPF_FORMATADO, _CNPJ_FORMATADO, _DOC_APOS_A_PALAVRA):
        for m in regra.finditer(s):
            ini, fim = m.span(1)
            while fim > ini and not s[fim - 1].isdigit():
                fim -= 1
            trocas.append((ini, fim, False))
    for m in re.finditer(r"(?<!\d)(\d{14}|\d{11})(?!\d)", s):
        trocas.append((m.start(1), m.end(1), True))
    saida, ultimo_fim = [], 0
    for ini, fim, solto in sorted(trocas):
        if ini < ultimo_fim:
            continue
        dig = _so_digitos(s[ini:fim])
        if len(dig) not in (11, 14) or not _documento_valido(dig):
            continue
        if solto and dig not in do_caso and _rotulado_como_outro_numero(s, ini, fim):
            continue
        saida.append(s[ultimo_fim:ini] + "final " + dig[-4:])
        ultimo_fim = fim
    if not saida:
        return s
    return "".join(saida) + s[ultimo_fim:]
