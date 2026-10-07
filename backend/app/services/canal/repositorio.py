# -*- coding: utf-8 -*-
"""O banco do canal de cotação — SPEC-133-A F1 (o contrato é o da migration 20261007_01 e o §3 da SPEC).

🔴 TODA leitura e escrita leva o filtro `company_id` AQUI, no repositório — o backend usa service role e a RLS sem
policy não protege contra erro de filtro (CLAUDE.md §7). E o CINTO: linha de outra empresa que volte do banco é
descartada em Python também (`_da_empresa`).

`db` é o cliente PostgREST (`get_supabase_client().client`): `.table(...).select/insert/upsert/update/eq/in_`.
Síncrono, como o resto do produto; a entrada (async) chama por `asyncio.to_thread`.

O telefone mora SEMPRE na forma canônica (`canonico`: só dígitos, com o 9º dígito do celular BR). O WhatsApp entrega
contas antigas sem o 9 (📊 07/10: as 3 integrações ativas têm `paired_phone_e164` com 13 caracteres = `+55` + 10
dígitos, sem o 9) — uma forma só no banco é o que impede o mesmo convidado de existir duas vezes.
⛔ Nenhuma função daqui escreve telefone em log: só `mascarar` (os 4 últimos).
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

logger = logging.getLogger(__name__)

CONVIDADOS = "canal_convidados"
CONSENTIMENTOS = "canal_consentimentos"
LEADS = "canal_leads"
CONVERSAS = "canal_conversas"
KIND_DO_CANAL = "platform_canal"

# TODO(gerente 133-A): as duas chaves abaixo entram em `multicalculo/config.py` → `PADRAO_DO_PRODUTO["canal"]`
#   ("limite_cotacoes_por_dia" e "teto_mensagens_por_dia"). Até lá `_mesclar` IGNORA a chave desconhecida e vale o
#   padrão local. 💭 3 cotações/dia por número (piloto com o círculo do Founder) e 💭 60 mensagens nossas/dia por conversa
#   (a conversa inteira cabe em ~15: consentimento + ~12 perguntas + resultado + pergunta final + 2 lembretes).
LIMITE_COTACOES_PADRAO = 3
TETO_MENSAGENS_PADRAO = 60

#: o dia do limite é o dia de Brasília (sem horário de verão desde 2019)
FUSO_DO_CANAL = timezone(timedelta(hours=-3))

#: `company_kind` não muda em vida de processo; o cache poupa um SELECT por turno de TODAS as corretoras
_TTL_DO_TIPO_S = 300.0
_CACHE_DO_TIPO: Dict[str, tuple] = {}

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_TEL = re.compile(r"^[1-9][0-9]{9,14}$")


# ---------------------------------------------------------------------------------------------------------------------
# telefone e dia
# ---------------------------------------------------------------------------------------------------------------------
def canonico(telefone: Any) -> str:
    """Só dígitos, com o 9º dígito do celular BR (55 + DDD + 8 dígitos começando em 6–9 → ganha o 9). Inválido → ''."""
    d = "".join(ch for ch in str(telefone or "").split("@", 1)[0] if ch.isdigit())
    if d.startswith("55") and len(d) == 12 and d[4] in "6789":
        d = d[:4] + "9" + d[4:]
    return d if _TEL.match(d) else ""


def formas(telefone: Any) -> List[str]:
    """As grafias do mesmo número: canônica, sem o 9 (contas antigas) e com o `+` (o `paired_phone_e164`)."""
    c = canonico(telefone)
    if not c:
        return []
    saida = {c}
    if c.startswith("55") and len(c) == 13 and c[4] == "9":
        saida.add(c[:4] + c[5:])
    return sorted(saida | {"+" + s for s in saida})


def mascarar(telefone: Any) -> str:
    d = "".join(ch for ch in str(telefone or "") if ch.isdigit())
    return f"...{d[-4:]}" if d else "..."


def hoje() -> str:
    return datetime.now(FUSO_DO_CANAL).date().isoformat()


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cid(company_id: Any) -> str:
    cid = str(company_id or "").strip().lower()
    if not _UUID.match(cid):
        raise ValueError("company_id precisa ser um uuid")
    return cid


def _tel_ou_erro(telefone: Any) -> str:
    c = canonico(telefone)
    if not c:
        raise ValueError("telefone inválido (E.164, 10 a 15 dígitos)")
    return c


def _dados(resposta: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(resposta, "data", None) or []) if isinstance(x, dict)]


def _da_empresa(linhas: Iterable[Dict[str, Any]], cid: str) -> List[Dict[str, Any]]:
    """🔴 O CINTO: linha de outra empresa nunca passa, mesmo que o filtro do banco falhe."""
    return [x for x in linhas if str(x.get("company_id") or "").lower() == cid]


def _config_do_canal(config: Any) -> Mapping[str, Any]:
    canal = (config or {}).get("canal") if isinstance(config, Mapping) else None
    return canal if isinstance(canal, Mapping) else {}


def _inteiro(valor: Any, padrao: int) -> int:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
        return padrao
    return int(valor)


def limite_padrao(config: Any) -> int:
    return _inteiro(_config_do_canal(config).get("limite_cotacoes_por_dia"), LIMITE_COTACOES_PADRAO)


def teto_de_mensagens(config: Any) -> int:
    return _inteiro(_config_do_canal(config).get("teto_mensagens_por_dia"), TETO_MENSAGENS_PADRAO)


# ---------------------------------------------------------------------------------------------------------------------
# o CONTRATO §3 (F1 → F2)
# ---------------------------------------------------------------------------------------------------------------------
def eh_canal(db, company_id: str) -> bool:
    """A empresa é o canal (`company_kind='platform_canal'`)? Erro de banco → False (a corretora segue o caminho de
    sempre; o canal, sem o desvio, cai no observer e CALA — a direção segura)."""
    try:
        cid = _cid(company_id)
    except ValueError:
        return False
    agora = time.monotonic()
    guardado = _CACHE_DO_TIPO.get(cid)
    if guardado and agora - guardado[1] < _TTL_DO_TIPO_S:
        return guardado[0] == KIND_DO_CANAL
    try:
        linhas = _dados(db.table("companies").select("id, company_kind").eq("id", cid).limit(1).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[CANAL] tipo da empresa não lido (%s) — segue como corretora", type(erro).__name__)
        return False
    linha = next((x for x in linhas if str(x.get("id") or "").lower() == cid), None)
    tipo = str((linha or {}).get("company_kind") or "")
    _CACHE_DO_TIPO[cid] = (tipo, agora)
    return tipo == KIND_DO_CANAL


def convidado(db, company_id: str, telefone_e164: str) -> Optional[Dict[str, Any]]:
    """O convidado ATIVO daquele telefone naquele canal: `{"id", "apelido"?, "limite_dia"?}` — ou None."""
    cid, tel = _cid(company_id), canonico(telefone_e164)
    if not tel:
        return None
    linhas = _dados(db.table(CONVIDADOS).select("id, company_id, telefone, apelido, limite_dia, ativo")
                    .eq("company_id", cid).eq("telefone", tel).eq("ativo", True).limit(1).execute())
    linha = next((x for x in _da_empresa(linhas, cid) if x.get("telefone") == tel and x.get("ativo") is True), None)
    if not linha:
        return None
    saida: Dict[str, Any] = {"id": linha.get("id")}
    if linha.get("apelido"):
        saida["apelido"] = linha["apelido"]
    if linha.get("limite_dia") is not None:
        saida["limite_dia"] = int(linha["limite_dia"])
    return saida


def dentro_do_limite(db, company_id: str, telefone_e164: str, config) -> bool:
    """Ainda cabe uma cotação HOJE para este número? O limite é o do convidado (`limite_dia`) ou o da config do canal."""
    conv = convidado(db, company_id, telefone_e164)
    if conv is None:
        return False
    limite = conv.get("limite_dia")
    if limite is None:
        limite = limite_padrao(config)
    return cotacoes_de_hoje(db, company_id, telefone_e164) < int(limite)


def numero_de_corretora(db, telefone_e164: str) -> bool:
    """Anti-laço (D-133A-06/07): o número é a linha de uma CORRETORA (integração ativa de empresa que não é o canal) ou
    um destino de suporte ativo? Erro de banco → True (na dúvida, o canal CALA)."""
    fs = formas(telefone_e164)
    if not fs:
        return False
    digitos = [f for f in fs if not f.startswith("+")]
    try:
        linhas = _dados(db.table("integrations").select("company_id").eq("is_active", True)
                        .in_("paired_phone_e164", fs).execute())
        linhas += _dados(db.table("integrations").select("company_id").eq("is_active", True)
                         .in_("identifier", digitos).execute())
        empresas = sorted({str(x.get("company_id") or "") for x in linhas} - {""})
        if empresas:
            tipos = _dados(db.table("companies").select("id, company_kind").in_("id", empresas).execute())
            de_canal = {str(x.get("id")) for x in tipos if x.get("company_kind") == KIND_DO_CANAL}
            if any(e not in de_canal for e in empresas):
                return True
        destinos = _dados(db.table("human_support_destinations").select("id").eq("is_active", True)
                          .in_("destination_ref", digitos + [f"{d}@s.whatsapp.net" for d in digitos]).execute())
        return bool(destinos)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[CANAL] anti-laço não conferido (%s) — o canal cala", type(erro).__name__)
        return True


def registrar_consentimento(db, company_id, telefone_e164, *, aceito: bool, versao_do_texto: str) -> None:
    """Uma linha por resposta (append-only): o sim/não e a versão do texto que a pessoa leu (D-133A-05)."""
    versao = str(versao_do_texto or "").strip()
    if not versao or len(versao) > 40:
        raise ValueError("versao_do_texto obrigatória (até 40 caracteres)")
    db.table(CONSENTIMENTOS).insert({"company_id": _cid(company_id), "telefone": _tel_ou_erro(telefone_e164),
                                     "aceito": bool(aceito), "versao_do_texto": versao}).execute()


def registrar_lead(db, company_id, telefone_e164, *, primeiro_nome=None, pedido_id=None) -> None:
    """O lead do número (um por telefone): grava só o que veio — `None` não apaga o que já estava."""
    linha: Dict[str, Any] = {"company_id": _cid(company_id), "telefone": _tel_ou_erro(telefone_e164),
                             "atualizado_em": _agora_iso()}
    if primeiro_nome is not None:
        linha["primeiro_nome"] = str(primeiro_nome).strip()[:60] or None
    if pedido_id is not None:
        linha["pedido_id"] = str(pedido_id)
    db.table(LEADS).upsert(linha, on_conflict="company_id,telefone").execute()


def carregar_estado(db, company_id, telefone_e164) -> dict:
    """O estado da conversa, decifrado (`{}` na 1ª vez). Cifra ilegível (chave trocada sem a anterior) → `{}` e aviso
    sem conteúdo. Erro de BANCO sobe: recomeçar a conversa por um soluço do banco pediria o consentimento de novo."""
    linha = _linha_da_conversa(db, company_id, telefone_e164)
    cifrado = str((linha or {}).get("estado_cifrado") or "")
    if not cifrado:
        return {}
    from app.services import portal_vault

    try:
        estado = json.loads(portal_vault.decrypt(cifrado))
    except Exception as erro:  # noqa: BLE001
        logger.warning("[CANAL] estado de %s ilegível (%s) — recomeça", mascarar(telefone_e164), type(erro).__name__)
        return {}
    return estado if isinstance(estado, dict) else {}


def salvar_estado(db, company_id, telefone_e164, estado: dict) -> None:
    """Grava o estado CIFRADO (portal_vault — o mesmo cofre do `pedido_cifrado`). Os contadores não são tocados."""
    from app.services import portal_vault

    texto = json.dumps(estado if isinstance(estado, dict) else {}, ensure_ascii=False, default=str)
    db.table(CONVERSAS).upsert({"company_id": _cid(company_id), "telefone": _tel_ou_erro(telefone_e164),
                                "estado_cifrado": portal_vault.encrypt(texto), "atualizado_em": _agora_iso()},
                               on_conflict="company_id,telefone").execute()


# ---------------------------------------------------------------------------------------------------------------------
# os contadores do dia (uso da entrada — F1)
# ---------------------------------------------------------------------------------------------------------------------
_COLS_CONVERSA = ("company_id, telefone, estado_cifrado, cotacoes_dia, cotacoes_no_dia, enviadas_dia, enviadas_no_dia, "
                  "aviso_limite_dia")


def _linha_da_conversa(db, company_id, telefone_e164) -> Optional[Dict[str, Any]]:
    cid, tel = _cid(company_id), _tel_ou_erro(telefone_e164)
    linhas = _dados(db.table(CONVERSAS).select(_COLS_CONVERSA).eq("company_id", cid).eq("telefone", tel)
                    .limit(1).execute())
    return next((x for x in _da_empresa(linhas, cid) if x.get("telefone") == tel), None)


def _do_dia(linha: Optional[Mapping[str, Any]], coluna_dia: str, coluna_n: str) -> int:
    if not linha or str(linha.get(coluna_dia) or "")[:10] != hoje():
        return 0
    return _inteiro(linha.get(coluna_n), 0)


def cotacoes_de_hoje(db, company_id, telefone_e164) -> int:
    return _do_dia(_linha_da_conversa(db, company_id, telefone_e164), "cotacoes_dia", "cotacoes_no_dia")


def enviadas_hoje(db, company_id, telefone_e164) -> int:
    return _do_dia(_linha_da_conversa(db, company_id, telefone_e164), "enviadas_dia", "enviadas_no_dia")


def aviso_de_limite_dado_hoje(db, company_id, telefone_e164) -> bool:
    linha = _linha_da_conversa(db, company_id, telefone_e164)
    return bool(linha) and str(linha.get("aviso_limite_dia") or "")[:10] == hoje()


def _gravar_contadores(db, company_id, telefone_e164, campos: Dict[str, Any]) -> None:
    db.table(CONVERSAS).upsert({"company_id": _cid(company_id), "telefone": _tel_ou_erro(telefone_e164),
                                "atualizado_em": _agora_iso(), **campos},
                               on_conflict="company_id,telefone").execute()


def contar_cotacao(db, company_id, telefone_e164) -> int:
    """+1 cotação hoje. ⚠️ Ler-somar-gravar: a trava de turno do buffer garante UM turno por telefone por vez."""
    n = cotacoes_de_hoje(db, company_id, telefone_e164) + 1
    _gravar_contadores(db, company_id, telefone_e164, {"cotacoes_dia": hoje(), "cotacoes_no_dia": n})
    return n


def contar_enviadas(db, company_id, telefone_e164, quantas: int) -> int:
    n = enviadas_hoje(db, company_id, telefone_e164) + max(0, int(quantas or 0))
    _gravar_contadores(db, company_id, telefone_e164, {"enviadas_dia": hoje(), "enviadas_no_dia": n})
    return n


def marcar_aviso_de_limite(db, company_id, telefone_e164) -> None:
    _gravar_contadores(db, company_id, telefone_e164, {"aviso_limite_dia": hoje()})


# ---------------------------------------------------------------------------------------------------------------------
# os convidados (o comando do Founder e o admin)
# ---------------------------------------------------------------------------------------------------------------------
def empresa_do_canal(db) -> str:
    """O id da empresa do canal, PELO BANCO (§13.9 — nunca constante). Zero ou mais de uma → erro explícito."""
    linhas = _dados(db.table("companies").select("id, company_kind").eq("company_kind", KIND_DO_CANAL).limit(2).execute())
    ids = [str(x.get("id")) for x in linhas if x.get("company_kind") == KIND_DO_CANAL]
    if len(ids) != 1:
        raise LookupError(f"esperada 1 empresa do canal (company_kind='{KIND_DO_CANAL}'), achadas {len(ids)}")
    return ids[0]


def adicionar_convidado(db, company_id, telefone_e164, *, apelido=None, limite_dia=None) -> None:
    linha: Dict[str, Any] = {"company_id": _cid(company_id), "telefone": _tel_ou_erro(telefone_e164), "ativo": True,
                             "atualizado_em": _agora_iso()}
    if apelido is not None:
        linha["apelido"] = str(apelido).strip()[:60] or None
    if limite_dia is not None:
        if not 0 <= int(limite_dia) <= 100:
            raise ValueError("limite_dia entre 0 e 100")
        linha["limite_dia"] = int(limite_dia)
    db.table(CONVIDADOS).upsert(linha, on_conflict="company_id,telefone").execute()


def remover_convidado(db, company_id, telefone_e164) -> int:
    """Desativa (não apaga: o histórico do consentimento continua apontando para alguém). Devolve quantos mudaram."""
    cid, tel = _cid(company_id), _tel_ou_erro(telefone_e164)
    feito = _dados(db.table(CONVIDADOS).update({"ativo": False, "atualizado_em": _agora_iso()})
                   .eq("company_id", cid).eq("telefone", tel).execute())
    return len(_da_empresa(feito, cid))


def listar_convidados(db, company_id) -> List[Dict[str, Any]]:
    cid = _cid(company_id)
    linhas = _dados(db.table(CONVIDADOS).select("company_id, telefone, apelido, ativo, limite_dia, criado_em")
                    .eq("company_id", cid).order("criado_em").execute())
    return _da_empresa(linhas, cid)
