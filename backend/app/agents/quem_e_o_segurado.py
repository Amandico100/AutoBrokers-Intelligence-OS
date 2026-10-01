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
_NOME_EXPLICITO = re.compile(
    r"\b(?:meu nome (?:é|e)|me chamo|aqui (?:é|e) (?:o|a)|quem fala (?:é|e)(?: o| a)?)\s+"
    r"([A-Za-zÀ-ÿ]{3,})", re.IGNORECASE)
#: "sou o João" só com MAIÚSCULA — "sou a segurada" não é nome.
_NOME_SOU = re.compile(r"\bsou (?:o|a)\s+([A-ZÀ-Ý][a-zà-ÿ]{1,})")
#: Palavras que a régua de nome casaria e não são nome de gente.
_NAO_E_NOME = frozenset({
    "segurado", "segurada", "cliente", "titular", "dono", "dona", "proprietario",
    "proprietário", "filho", "filha", "esposo", "esposa", "marido", "mulher", "mae",
    "mãe", "pai", "irmao", "irmão", "irma", "irmã", "responsavel", "responsável",
    "motorista", "condutor", "corretor", "corretora", "sindico", "síndico", "mesmo",
    "mesma", "que", "quem", "seu", "sua",
})


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


def _parece_celular(digitos: str) -> bool:
    """DDD + 9 + 8 dígitos. 11 dígitos SOLTOS que têm cara de celular não são CPF."""
    return len(digitos) == 11 and digitos[2] == "9" and digitos[0] != "0"


def documentos_ditos(texto: Any) -> List[str]:
    """Os CPF/CNPJ (só dígitos, válidos) que aparecem num texto, na ordem. **PURA.**"""
    s = str(texto or "")
    achados: List[tuple] = []
    for regra in (_CPF_FORMATADO, _CNPJ_FORMATADO, _DOC_APOS_A_PALAVRA):
        for m in regra.finditer(s):
            achados.append((m.start(), _so_digitos(m.group(1))))
    for m in _ONZE_DIGITOS.finditer(s):
        if not _parece_celular(m.group(1)):
            achados.append((m.start(), m.group(1)))
    saida: List[str] = []
    for _pos, dig in sorted(achados):
        if len(dig) in (11, 14) and dig not in saida and _documento_valido(dig):
            saida.append(dig)
    return saida


def nome_dito(texto: Any) -> str:
    """O primeiro nome que o segurado DISSE ser o dele, ou `""`. **PURA.**"""
    s = str(texto or "")
    for regra in (_NOME_EXPLICITO, _NOME_SOU):
        for m in regra.finditer(s):
            nome = m.group(1).strip()
            if nome.lower() not in _NAO_E_NOME:
                return nome[:1].upper() + nome[1:].lower()
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
    return {"nome": "", "nome_origem": "", "cpf": "", "cpf_mascarado": "",
            "cpfs_distintos": 0, "cpf_de_assunto_anterior": False, "apolice": "",
            "caso_anterior": "", "perguntar_cpf": True}


def montar(*, historico: Any, user_name: Any = "", ficha: Optional[Dict[str, Any]] = None,
           resumos: Optional[List[Dict[str, Any]]] = None, n_dias: int = 7) -> Dict[str, Any]:
    """O que já sabemos — a partir do que JÁ foi lido desta corretora. **PURA.**

    ⛔ Quem chama garante que `historico`, `ficha` e `resumos` são da MESMA
    corretora (é o que `quem_e_o_segurado` faz, com filtro e cinto).
    """
    saida = identidade_vazia()
    linhas = _em_ordem(historico)
    inicio = _inicio_do_assunto_atual(linhas, n_dias)

    docs: List[tuple] = []   # (indice, digitos) — só o que o SEGURADO escreveu
    nome = ""
    for i, m in enumerate(linhas):
        if not _do_segurado(m):
            continue
        for d in documentos_ditos(m.get("content")):
            docs.append((i, d))
        nome = nome_dito(m.get("content")) or nome
    if docs:
        indice, ultimo = docs[-1]
        saida.update(cpf=ultimo, cpf_mascarado=mascarar_documento(ultimo),
                     cpfs_distintos=len({d for _i, d in docs}),
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
        from app.services.attendance_ficha import ORIGEM_SISTEMA_DE_GESTAO, apolice_do_caso, origem_de, valor_de
        from app.services.policy_context import nome_humano_do_ramo
    except Exception:  # noqa: BLE001
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
    if not (q.get("nome") or q.get("cpf") or q.get("apolice") or q.get("caso_anterior")):
        return ""
    linhas = ["=== 🪪 O QUE JÁ SABEMOS DESTE SEGURADO (este telefone, esta corretora) ===",
              "Confirme numa linha; não pergunte do zero. Antes do \"sim\", só o 1º nome."]
    if q.get("nome"):
        linhas.append(f"· nome provável: {q['nome']} ({q.get('nome_origem')}) — confirme antes de usar")
    if q.get("cpf"):
        quando = "num assunto anterior" if q.get("cpf_de_assunto_anterior") else "nesta conversa"
        mais = "; disse outro também — confirme qual" if int(q.get("cpfs_distintos") or 0) > 1 else ""
        linhas.append(f"· CPF/CNPJ que ele disse {quando}: {q['cpf']} — use nas ferramentas; "
                      f"a ele, só \"final {q['cpf'][-4:]}\"{mais}")
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
