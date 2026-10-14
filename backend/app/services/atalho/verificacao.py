# -*- coding: utf-8 -*-
"""SPEC-132-C C1 — a verificação do "Meu WhatsApp de trabalho" por POSSE (D-132C-02).

    numero_do_assistente(db)                                       o número do AutoBrokers (dígitos) ou None
    gerar_codigo(db, *, company_id, user_id)                       o código de 6 dígitos para a PRÓPRIA pessoa
    codigo_da_ativacao(texto)                                      "ATIVAR 123456" → "123456" (ou None)
    async consumir_codigo(db, *, telefone_remetente_e164, texto)   a C2 chama quando chega "ATIVAR …" ao assistente
    membros_verificados_por_telefone(db, telefone_e164)            quem é este telefone (só membros ATIVOS verificados)

O FIO (SPEC-132-C §2): Meu perfil → o número DECLARADO e confirmado pela pessoa → código (só o HASH no banco, 15 min,
uso único) + wa.me/<número do AutoBrokers>?text=ATIVAR 123456 → a pessoa manda do CELULAR DELA → webhook (C2) →
`consumir_codigo` → o REMETENTE tem de ser o número DECLARADO do dono do código → `whatsapp_trabalho_verificado_em` →
"Pronto, {nome}…". Nada é enviado a ninguém antes: quem prova a posse é quem manda.

🔴 O CÓDIGO AMARRA O NÚMERO DECLARADO (conserto P1 do juiz e do red team): gerar EXIGE `whatsapp_trabalho_e164` já
   confirmado no Meu perfil; consumir só aceita o remetente == esse número (forma canônica, com o 9º dígito). Remetente
   diferente → silêncio, conta tentativa, e o número/`confirmado_em` do membro NUNCA são reescritos (antes: o código
   vazado num print trocava a identidade do membro pelo número de quem o mandasse).
🔴 Teto GLOBAL de "ATIVAR" errados (💭 30/hora no total, além dos 💭 5/hora por número): acima dele, silêncio para todos
   (o atacante que roda números não chuta 10⁶ códigos).
🔴 Gerar exige o atalho LIGADO (`ATALHO_WHATSAPP_LIGADO`): desligado, o ATIVAR seria ignorado (P5 do juiz).

🔴 O membro vinculado é SEMPRE o (company_id, user_id) DO CÓDIGO — nunca do corpo, da sessão nem do telefone (mutação 3).
🔴 Uso único: o código só é marcado usado por um UPDATE condicionado a `usado_em is null` (mutação 2).
🔴 O código em claro NUNCA é gravado nem logado: só o HMAC-SHA256 com o segredo da aplicação.
🔴 Toda escrita no membro filtra company_id + user_id (CLAUDE.md §7 — o backend usa service role) e o CINTO descarta em
   Python a linha de outra empresa que volte do banco.
⛔ Nenhum telefone vai para log (só `mascarar`). Número desconhecido = silêncio (D-132C-03): `responder=False`.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

TABELA_CODIGOS = "whatsapp_atalho_codigos"
TABELA_TENTATIVAS = "whatsapp_atalho_tentativas"
PURPOSE_DO_ASSISTENTE = "assistente"
ENV_DO_NUMERO = "ATALHO_WHATSAPP_NUMERO"
#: o segredo do HMAC: o próprio, se houver; senão um segredo da aplicação que já existe em produção (nunca logado)
ENVS_DO_SEGREDO = ("ATALHO_CODIGO_SEGREDO", "ENCRYPTION_KEY", "APP_SECRET", "SECRET_KEY", "SESSION_SECRET")

VALIDADE = timedelta(minutes=15)
#: 💭 teto de códigos que um membro pede por hora (a 6ª vez é recusada com a frase)
TETO_DE_CODIGOS_POR_HORA = 5
#: 💭 teto de "ATIVAR" ERRADOS por número de telefone por hora — acima dele, silêncio (nem se procura o código)
TETO_DE_TENTATIVAS_ERRADAS_POR_HORA = 5
#: 💭 teto GLOBAL de "ATIVAR" ERRADOS por hora, somados todos os números — acima dele, silêncio para TODOS
TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA = 30
_TENTATIVAS_DE_SORTEIO = 10

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
#: "ATIVAR 123456" com tolerância de caixa, espaços (inclusive entre os dígitos), negrito do WhatsApp e ponto final
_ATIVAR = re.compile(r"^\s*\*?\s*ativar\s*[:\-]?\s*((?:\d\s*){6})\*?\s*[.!]?\s*$", re.IGNORECASE)


class Recusa(Exception):
    """O pedido foi recusado — a mensagem é para quem pediu, em português, sem dado sensível."""


@dataclass(frozen=True)
class ResultadoDaAtivacao:
    """O que a C2 faz com o "ATIVAR": `responder=False` → SILÊNCIO (nenhuma resposta, nenhum conteúdo registrado);
    `responder=True` → manda `mensagem` ao remetente pelo número do AutoBrokers.

    motivo: "" (ok) · nao_e_ativacao · numero_invalido · teto_de_tentativas · teto_global · codigo_invalido ·
            membro_inativo · numero_nao_declarado · numero_de_outra_pessoa · sem_segredo · erro"""
    ok: bool
    company_id: Optional[str] = None
    user_id: Optional[str] = None
    nome: Optional[str] = None
    motivo: str = ""
    responder: bool = False
    mensagem: Optional[str] = None


# ---------------------------------------------------------------------------------------------------------------------
# miúdos
# ---------------------------------------------------------------------------------------------------------------------
def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def _t(db: Any, tabela: str) -> Any:
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(tabela)


def _uuid(v: Any, oque: str = "id") -> str:
    s = str(v or "").strip().lower()
    if not _UUID.match(s):
        raise Recusa(f"{oque} inválido")
    return s


def _mesma(a: Any, b: str) -> bool:
    return str(a or "").strip().lower() == b


def _agora(agora: Optional[datetime]) -> datetime:
    return (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _quando(v: Any) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _segredo() -> Optional[bytes]:
    for nome in ENVS_DO_SEGREDO:
        valor = os.environ.get(nome)
        if valor:
            return valor.encode("utf-8")
    return None


def _hmac(rotulo: str, valor: str) -> str:
    segredo = _segredo()
    if not segredo:
        raise Recusa("A verificação pelo WhatsApp ainda não está disponível. Tente de novo mais tarde.")
    return hmac.new(segredo, f"{rotulo}:{valor}".encode("utf-8"), hashlib.sha256).hexdigest()


def hash_do_codigo(codigo: str) -> str:
    """O HMAC-SHA256 do código (o que o banco guarda). Exportado para os testes provarem que o claro não é gravado."""
    return _hmac("atalho-codigo", str(codigo))


def _hash_do_telefone(telefone_canonico: str) -> str:
    return _hmac("atalho-telefone", telefone_canonico)


def _canonico(telefone: Any) -> str:
    """A MESMA forma do canal (só dígitos, com o 9º dígito do celular BR) — `canal.repositorio.canonico`."""
    from app.services.canal.repositorio import canonico

    return canonico(telefone)


def _mascarar(telefone: Any) -> str:
    from app.services.canal.repositorio import mascarar

    return mascarar(telefone)


def _e164_de(telefone: Any) -> Optional[str]:
    """O telefone do remetente na forma do membro (`+55…`, a regra do CHECK `ck_company_members_whatsapp_e164`)."""
    from app.services.perfil_do_membro import e164_do_brasil

    c = _canonico(telefone)
    return e164_do_brasil("+" + c) if c else None


def _primeiro_nome(nome: str) -> str:
    return (nome or "").strip().split(" ")[0]


def _nomes_das_pessoas(db: Any, ids: List[str]) -> Dict[str, str]:
    if not ids:
        return {}
    pessoas = _dados(_t(db, "users_v2").select("id, first_name, last_name, status, deleted_at").in_("id", ids).execute())
    saida: Dict[str, str] = {}
    for p in pessoas:
        uid = str(p.get("id") or "").lower()
        if uid not in ids or p.get("status") != "active" or p.get("deleted_at"):
            continue
        nome = " ".join(x for x in (str(p.get("first_name") or "").strip(), str(p.get("last_name") or "").strip()) if x)
        saida[uid] = nome or "Sem nome"
    return saida


def _nomes_das_corretoras(db: Any, ids: List[str]) -> Dict[str, str]:
    if not ids:
        return {}
    linhas = _dados(_t(db, "companies").select("id, company_name").in_("id", ids).execute())
    return {str(x.get("id")).lower(): str(x.get("company_name") or "").strip() or "sua corretora"
            for x in linhas if str(x.get("id") or "").lower() in ids}


def _mesmo_telefone(a: Any, b: Any) -> bool:
    """Os dois números são o MESMO telefone (forma canônica do canal, com o 9º dígito do celular BR)."""
    ca, cb = _canonico(a), _canonico(b)
    return bool(ca) and ca == cb


def _membro(db: Any, cid: str, uid: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(_t(db, "company_members")
                    .select("user_id, company_id, status, whatsapp_trabalho_e164, whatsapp_trabalho_confirmado_em")
                    .eq("company_id", cid).eq("user_id", uid).limit(1).execute())
    linhas = [x for x in linhas if _mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)]
    return linhas[0] if linhas else None


# ---------------------------------------------------------------------------------------------------------------------
# o número do AutoBrokers
# ---------------------------------------------------------------------------------------------------------------------
def _digitos(v: Any) -> Optional[str]:
    d = "".join(ch for ch in str(v or "") if ch.isdigit())
    return d if 10 <= len(d) <= 15 else None


def numero_do_assistente(db: Any) -> Optional[str]:
    """O número do AutoBrokers (só dígitos, como o WhatsApp o pareou): a integração ATIVA `purpose='assistente'` da
    empresa da PLATAFORMA (`company_kind='platform_canal'`, pelo banco — §13.9) → senão o env `ATALHO_WHATSAPP_NUMERO`
    → senão None (a tela diz que o número ainda não foi ligado). Nunca levanta."""
    try:
        from app.services.canal.repositorio import KIND_DO_CANAL

        empresas = _dados(_t(db, "companies").select("id, company_kind").eq("company_kind", KIND_DO_CANAL).execute())
        ids = sorted({str(x.get("id") or "").lower() for x in empresas if x.get("company_kind") == KIND_DO_CANAL} - {""})
        if ids:
            linhas = _dados(_t(db, "integrations")
                            .select("company_id, purpose, is_active, paired_phone_e164, channel_status")
                            .eq("purpose", PURPOSE_DO_ASSISTENTE).eq("is_active", True).in_("company_id", ids)
                            .execute())
            linhas = [x for x in linhas if str(x.get("company_id") or "").lower() in ids
                      and x.get("purpose") == PURPOSE_DO_ASSISTENTE and x.get("is_active") is True]
            linhas.sort(key=lambda x: 0 if str(x.get("channel_status") or "").lower() == "connected" else 1)
            for linha in linhas:
                d = _digitos(linha.get("paired_phone_e164"))
                if d:
                    return d
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ATALHO] número do assistente ilegível no banco (%s)", type(erro).__name__)
    return _digitos(os.environ.get(ENV_DO_NUMERO))


def _wa_me(numero: Optional[str], codigo: str) -> Optional[str]:
    return f"https://wa.me/{numero}?text={quote('ATIVAR ' + codigo)}" if numero else None


# ---------------------------------------------------------------------------------------------------------------------
# gerar (a própria pessoa, pela sessão)
# ---------------------------------------------------------------------------------------------------------------------
def gerar_codigo(db: Any, *, company_id: Any, user_id: Any, agora: Optional[datetime] = None) -> Dict[str, Any]:
    """O código de 6 dígitos (aleatório, `secrets`) para o membro (company_id, user_id) — que a ROTA tira da sessão.
    Guarda SÓ o hash, vale 15 min, invalida o código anterior do membro, recusa a 6ª vez na hora.
    Devolve `{codigo, texto, expira_em, validade_minutos, wa_me_url | None, numero_assistente | None}`."""
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    t0 = _agora(agora)
    membro = _membro(db, cid, uid)
    if not membro or membro.get("status") != "active":
        raise Recusa("Você não está ativo na equipe desta corretora.")
    from app.services.atalho.entrada import ligado

    if not ligado():
        raise Recusa("Falar com o AutoBrokers pelo WhatsApp ainda não está disponível. Em breve.")
    if not (membro.get("whatsapp_trabalho_e164") and membro.get("whatsapp_trabalho_confirmado_em")):
        # 🔴 P1: o código amarra o número DECLARADO — sem ele, não há o que verificar
        raise Recusa("Primeiro salve e confirme o seu WhatsApp de trabalho acima. "
                     "O código só vale mandado desse número.")
    if not _segredo():  # sem segredo → a frase, ANTES de qualquer escrita (nunca um código sem hash)
        logger.error("[ATALHO] sem segredo para o HMAC — código não gerado")
        raise Recusa("A verificação pelo WhatsApp ainda não está disponível. Tente de novo mais tarde.")
    uma_hora = (t0 - timedelta(hours=1)).isoformat()
    recentes = [x for x in _dados(_t(db, TABELA_CODIGOS).select("id, company_id, user_id, criado_em")
                                  .eq("company_id", cid).eq("user_id", uid).gte("criado_em", uma_hora).execute())
                if _mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)
                and (_quando(x.get("criado_em")) or t0) >= t0 - timedelta(hours=1)]
    if len(recentes) >= TETO_DE_CODIGOS_POR_HORA:
        raise Recusa(f"Você já pediu {TETO_DE_CODIGOS_POR_HORA} códigos na última hora. "
                     "Espere um pouco e peça de novo.")

    codigo, h = "", ""
    for _ in range(_TENTATIVAS_DE_SORTEIO):
        candidato = f"{secrets.randbelow(10 ** 6):06d}"
        hc = hash_do_codigo(candidato)
        # dois códigos ATIVOS iguais (de quaisquer membros) tornariam o consumo ambíguo: sorteia outro
        iguais = [x for x in _dados(_t(db, TABELA_CODIGOS).select("id, codigo_hash, expira_em, usado_em, invalidado_em")
                                    .eq("codigo_hash", hc).is_("usado_em", "null").is_("invalidado_em", "null")
                                    .execute())
                  if x.get("codigo_hash") == hc and (_quando(x.get("expira_em")) or t0) > t0]
        if not iguais:
            codigo, h = candidato, hc
            break
    if not codigo:
        raise Recusa("Não consegui gerar o código agora. Tente de novo em instantes.")

    # o anterior deixa de valer (não é uso: `invalidado_em`) — só os DESTE membro
    _t(db, TABELA_CODIGOS).update({"invalidado_em": t0.isoformat()}) \
        .eq("company_id", cid).eq("user_id", uid).is_("usado_em", "null").is_("invalidado_em", "null").execute()
    expira = t0 + VALIDADE
    try:
        _t(db, TABELA_CODIGOS).insert({"company_id": cid, "user_id": uid, "codigo_hash": h,
                                       "expira_em": expira.isoformat(), "criado_em": t0.isoformat(),
                                       "tentativas": 0}).execute()
    except Exception as erro:  # noqa: BLE001 — dois pedidos ao mesmo tempo: o índice único deixa passar um só
        logger.warning("[ATALHO] código não gravado (%s)", type(erro).__name__)
        raise Recusa("Não consegui gerar o código agora. Tente de novo em instantes.") from None
    numero = numero_do_assistente(db)
    return {"codigo": codigo, "texto": f"ATIVAR {codigo}", "expira_em": expira.isoformat(),
            "validade_minutos": int(VALIDADE.total_seconds() // 60), "wa_me_url": _wa_me(numero, codigo),
            "numero_assistente": numero}


# ---------------------------------------------------------------------------------------------------------------------
# consumir (a C2 chama, com o telefone de quem MANDOU)
# ---------------------------------------------------------------------------------------------------------------------
def codigo_da_ativacao(texto: Any) -> Optional[str]:
    """"ATIVAR 123456" (caixa, espaços, *negrito*, ponto final tolerados) → "123456". Qualquer outra coisa → None."""
    m = _ATIVAR.match(str(texto or ""))
    return re.sub(r"\D", "", m.group(1)) if m else None


def _silencio(motivo: str) -> ResultadoDaAtivacao:
    return ResultadoDaAtivacao(ok=False, motivo=motivo, responder=False)


def _tentativas_erradas_no_total(db: Any, t0: datetime) -> int:
    """Quantos "ATIVAR" errados na última hora, de TODOS os números (o teto global)."""
    uma_hora = t0 - timedelta(hours=1)
    linhas = _dados(_t(db, TABELA_TENTATIVAS).select("id, criado_em").gte("criado_em", uma_hora.isoformat())
                    .limit(TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA + 1).execute())
    return len([x for x in linhas if (_quando(x.get("criado_em")) or t0) >= uma_hora])


def _contar_tentativa(db: Any, tel_hash: str, t0: datetime) -> None:
    _t(db, TABELA_TENTATIVAS).insert({"telefone_hash": tel_hash, "criado_em": t0.isoformat()}).execute()


def _tentativas_erradas(db: Any, tel_hash: str, t0: datetime) -> int:
    uma_hora = t0 - timedelta(hours=1)
    linhas = _dados(_t(db, TABELA_TENTATIVAS).select("id, telefone_hash, criado_em").eq("telefone_hash", tel_hash)
                    .gte("criado_em", uma_hora.isoformat()).execute())
    return len([x for x in linhas if x.get("telefone_hash") == tel_hash
                and (_quando(x.get("criado_em")) or t0) >= uma_hora])


def _consumir(db: Any, telefone: Any, texto: Any, agora: Optional[datetime]) -> ResultadoDaAtivacao:
    codigo = codigo_da_ativacao(texto)
    if not codigo:
        return _silencio("nao_e_ativacao")
    e164 = _e164_de(telefone)
    if not e164:
        return _silencio("numero_invalido")
    t0 = _agora(agora)
    try:
        tel_hash = _hash_do_telefone(e164)
        h = hash_do_codigo(codigo)
    except Recusa:
        logger.error("[ATALHO] sem segredo para o HMAC — a ativação cala")
        return _silencio("sem_segredo")
    if _tentativas_erradas_no_total(db, t0) >= TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA:
        logger.warning("[ATALHO] teto GLOBAL de ativações erradas atingido — a ativação cala para todos")
        return _silencio("teto_global")
    if _tentativas_erradas(db, tel_hash, t0) >= TETO_DE_TENTATIVAS_ERRADAS_POR_HORA:
        return _silencio("teto_de_tentativas")

    # 🔴 o código é procurado pelo HASH em QUALQUER corretora — e daqui em diante o membro é o DO CÓDIGO
    achados = [x for x in _dados(_t(db, TABELA_CODIGOS)
                                 .select("id, company_id, user_id, codigo_hash, expira_em, usado_em, invalidado_em, "
                                         "tentativas")
                                 .eq("codigo_hash", h).is_("usado_em", "null").is_("invalidado_em", "null").execute())
               if x.get("codigo_hash") == h and x.get("usado_em") is None and x.get("invalidado_em") is None
               and (_quando(x.get("expira_em")) or t0) > t0]
    if len(achados) != 1:
        if len(achados) > 1:
            logger.warning("[ATALHO] %d códigos ativos com o mesmo hash — recusado", len(achados))
        _contar_tentativa(db, tel_hash, t0)
        return _silencio("codigo_invalido")
    linha = achados[0]
    cid, uid = str(linha.get("company_id") or "").lower(), str(linha.get("user_id") or "").lower()
    if not (_UUID.match(cid) and _UUID.match(uid)):
        return _silencio("codigo_invalido")

    membro = _membro(db, cid, uid)
    if not membro or membro.get("status") != "active":
        _t(db, TABELA_CODIGOS).update({"invalidado_em": t0.isoformat()}).eq("id", linha["id"]) \
            .eq("company_id", cid).execute()
        return _silencio("membro_inativo")

    # 🔴 P1: o código vale SÓ do número que a pessoa declarou e confirmou no Meu perfil. Outro remetente (o print do
    # código vazado, o chute que acertou) → silêncio, tentativa contada, NADA muda no membro (nem número nem confirmação)
    if not (membro.get("whatsapp_trabalho_e164") and membro.get("whatsapp_trabalho_confirmado_em")) \
            or not _mesmo_telefone(membro.get("whatsapp_trabalho_e164"), e164):
        _contar_tentativa(db, tel_hash, t0)
        _t(db, TABELA_CODIGOS).update({"tentativas": int(linha.get("tentativas") or 0) + 1}) \
            .eq("id", linha["id"]).eq("company_id", cid).execute()
        logger.warning("[ATALHO] ativação de um número que não é o declarado (%s) — calada", _mascarar(e164))
        return _silencio("numero_nao_declarado")
    e164 = str(membro.get("whatsapp_trabalho_e164"))   # o número é o DECLARADO (a mesma pessoa, a mesma forma gravada)

    outros = [x for x in _dados(_t(db, "company_members").select("user_id, company_id, whatsapp_trabalho_e164, "
                                                                "whatsapp_trabalho_verificado_em")
                                .eq("company_id", cid).eq("whatsapp_trabalho_e164", e164)
                                .not_.is_("whatsapp_trabalho_verificado_em", "null").execute())
              if _mesma(x.get("company_id"), cid) and x.get("whatsapp_trabalho_e164") == e164
              and x.get("whatsapp_trabalho_verificado_em") and not _mesma(x.get("user_id"), uid)]
    if outros:
        _t(db, TABELA_CODIGOS).update({"tentativas": int(linha.get("tentativas") or 0) + 1}) \
            .eq("id", linha["id"]).eq("company_id", cid).execute()
        return ResultadoDaAtivacao(
            ok=False, company_id=cid, user_id=uid, motivo="numero_de_outra_pessoa", responder=True,
            mensagem="Este número já está ligado a outra pessoa da sua corretora no AutoBrokers. "
                     "Peça para ela tirá-lo em Meu perfil, ou mande a mensagem do seu próprio celular.")

    # 🔴 uso ÚNICO: só marca quem ainda não foi usado; quem perdeu a corrida recebe zero linhas
    usado = [x for x in _dados(_t(db, TABELA_CODIGOS).update({"usado_em": t0.isoformat()})
                               .eq("id", linha["id"]).eq("company_id", cid).eq("user_id", uid)
                               .is_("usado_em", "null").is_("invalidado_em", "null").execute())
             if _mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)]
    if not usado:
        return _silencio("codigo_invalido")

    # 🔴 só a VERIFICAÇÃO é escrita: o número e a confirmação são os que a pessoa gravou (nunca o remetente por cima).
    # O UPDATE é condicionado ao número declarado não ter mudado no meio (a pessoa trocou o número entre o código e o
    # ATIVAR → zero linhas → cala).
    patch = {"whatsapp_trabalho_verificado_em": t0.isoformat()}
    try:
        feito = [x for x in _dados(_t(db, "company_members").update(patch).eq("company_id", cid).eq("user_id", uid)
                                   .eq("whatsapp_trabalho_e164", e164).execute())
                 if _mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)]
    except Exception as erro:  # noqa: BLE001 — o índice único (o número já é de outra pessoa) ganhou a corrida
        logger.warning("[ATALHO] verificação não gravada para %s (%s)", _mascarar(e164), type(erro).__name__)
        _t(db, TABELA_CODIGOS).update({"usado_em": None}).eq("id", linha["id"]).eq("company_id", cid).execute()
        if "uq_company_members_whatsapp_verificado" in str(erro) or "duplicate" in str(erro).lower():
            return ResultadoDaAtivacao(
                ok=False, company_id=cid, user_id=uid, motivo="numero_de_outra_pessoa", responder=True,
                mensagem="Este número já está ligado a outra pessoa da sua corretora no AutoBrokers. "
                         "Peça para ela tirá-lo em Meu perfil, ou mande a mensagem do seu próprio celular.")
        return _silencio("erro")
    if not feito:
        return _silencio("membro_inativo")

    nome = _nomes_das_pessoas(db, [uid]).get(uid) or ""
    corretora = _nomes_das_corretoras(db, [cid]).get(cid) or "sua corretora"
    primeiro = _primeiro_nome(nome)
    saudacao = f"Pronto, {primeiro}!" if primeiro else "Pronto!"
    logger.info("[ATALHO] número verificado (%s)", _mascarar(e164))
    return ResultadoDaAtivacao(
        ok=True, company_id=cid, user_id=uid, nome=nome or None, motivo="", responder=True,
        mensagem=(f"{saudacao} Este número agora fala com o AutoBrokers da {corretora}. "
                  "Pode mandar o que precisa: texto, áudio, foto ou o PDF da apólice."))


async def consumir_codigo(db: Any, *, telefone_remetente_e164: Any, texto: Any,
                          agora: Optional[datetime] = None) -> ResultadoDaAtivacao:
    """A C2 chama quando chega uma mensagem ao número do AutoBrokers (já filtrados fromMe, grupo e anti-laço).
    `telefone_remetente_e164` é o telefone de QUEM MANDOU (o do webhook, nunca do texto). Nunca levanta."""
    try:
        return await asyncio.to_thread(_consumir, db, telefone_remetente_e164, texto, agora)
    except Exception as erro:  # noqa: BLE001 — na dúvida, o assistente CALA
        logger.error("[ATALHO] ativação falhou (%s)", type(erro).__name__)
        return _silencio("erro")


# ---------------------------------------------------------------------------------------------------------------------
# quem é este telefone (a C2 chama a cada mensagem que não é ativação)
# ---------------------------------------------------------------------------------------------------------------------
def membros_verificados_por_telefone(db: Any, telefone_e164: Any) -> List[Dict[str, str]]:
    """`[{company_id, user_id, nome, nome_da_corretora}]` dos membros ATIVOS (vínculo e pessoa) com este número
    VERIFICADO. Vazio = número desconhecido (a C2 cala). Mais de um = a mesma pessoa em várias corretoras (a C2 pergunta
    qual, uma vez). O telefone é comparado na forma canônica (com o 9º dígito)."""
    e164 = _e164_de(telefone_e164)
    if not e164:
        return []
    linhas = _dados(_t(db, "company_members")
                    .select("user_id, company_id, status, whatsapp_trabalho_e164, whatsapp_trabalho_verificado_em")
                    .eq("whatsapp_trabalho_e164", e164).eq("status", "active")
                    .not_.is_("whatsapp_trabalho_verificado_em", "null").execute())
    linhas = [x for x in linhas if x.get("whatsapp_trabalho_e164") == e164 and x.get("status") == "active"
              and x.get("whatsapp_trabalho_verificado_em")
              and _UUID.match(str(x.get("company_id") or "")) and _UUID.match(str(x.get("user_id") or ""))]
    if not linhas:
        return []
    uids = sorted({str(x["user_id"]).lower() for x in linhas})
    cids = sorted({str(x["company_id"]).lower() for x in linhas})
    pessoas = _nomes_das_pessoas(db, uids)
    corretoras = _nomes_das_corretoras(db, cids)
    saida = []
    for x in linhas:
        uid, cid = str(x["user_id"]).lower(), str(x["company_id"]).lower()
        if uid not in pessoas:   # a pessoa foi desativada/apagada: o número deixa de ser identidade
            continue
        saida.append({"company_id": cid, "user_id": uid, "nome": pessoas[uid],
                      "nome_da_corretora": corretoras.get(cid, "sua corretora")})
    return sorted(saida, key=lambda m: (m["nome_da_corretora"].lower(), m["company_id"]))


__all__ = ("Recusa", "ResultadoDaAtivacao", "numero_do_assistente", "gerar_codigo", "codigo_da_ativacao",
           "consumir_codigo", "membros_verificados_por_telefone", "hash_do_codigo", "PURPOSE_DO_ASSISTENTE",
           "ENV_DO_NUMERO", "VALIDADE", "TETO_DE_CODIGOS_POR_HORA", "TETO_DE_TENTATIVAS_ERRADAS_POR_HORA",
           "TETO_GLOBAL_DE_TENTATIVAS_ERRADAS_POR_HORA",
           "TABELA_CODIGOS", "TABELA_TENTATIVAS")
