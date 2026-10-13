"""SPEC-131-0 parte A · F4 — a tela "Serviços" da corretora (D-131-0-07/08/10/12).

O manual de CADA serviço (Cotação · Renovação · Quem Cobra Menos) mora em `multicalculo_config.servicos` da corretora,
mesclado sobre a base dela por `config.carregar(…, servico=)` — o ÚNICO leitor (CLAUDE.md §5: nenhuma config paralela).
Este router é o PRIMEIRO escritor de `multicalculo_config` no produto:

    GET  /api/servicos-da-corretora?company_id=            o que a corretora sobrepôs + o efetivo de cada serviço
    PUT  /api/servicos-da-corretora                        grava SÓ `servicos.*` e as preferências de seguradoras
    GET  /api/servicos-da-corretora/prontidao?company_id=  os 4 passos da ordem guiada (D-131-0-07) — SÓ LEITURA

🔴 Chave interna (o proxy Next é quem fala com isto); o `company_id` vem da SESSÃO no proxy, nunca do navegador.
🔴 TODA leitura e escrita filtra `company_id` aqui (o backend usa service role — a RLS sem policy não protege, §7).
⛔ Nenhum número comercial escrito aqui (o guarda G8 da 130-A): padrões e faixas vêm de `config.py`.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.portal import _require_internal_key
from app.services.multicalculo import config as CFG

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/servicos-da-corretora", tags=["Serviços da corretora"])

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

#: os ramos que a tela mostra, na ordem da tela (o código é o do Agger, como o jsonb guarda)
RAMOS_DA_TELA = (("31", "Automóvel"), ("16", "Condomínio"), ("2", "Residencial"), ("18", "Empresarial"))
#: o que o corpo do PUT pode trazer — qualquer outra chave é recusada
_CHAVES_DO_PUT = frozenset({"company_id", "atualizado_por", "servicos", "preferencias_de_seguradoras", "versao"})
#: conserto 131-0 A (juiz P1 · red P2): a frase do conflito — dois admins salvando ao mesmo tempo
FRASE_DO_CONFLITO = ("Outra pessoa salvou os serviços antes de você. Recarregue a página para ver o que mudou e salve "
                     "de novo — nada do que você mandou foi gravado.")


class Conflito(Exception):
    """A linha mudou entre a leitura da tela e a gravação (a versão enviada não é mais a do banco)."""

#: os links de cada passo da ordem guiada (telas que já existem)
_LINK_CONECTORES = "/dashboard/personalizacao/conectores"
_LINK_EQUIPE = "/dashboard/personalizacao/equipe"
#: SPEC-131-B (D-131-06): as regras moram na aba Configurar do aplicativo — DIRETO, sem passar pelo redirect antigo
_LINK_SERVICOS = "/dashboard/auxiliares/renovacao?aba=configurar"


def _db():
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def _dados(resp: Any) -> List[Dict[str, Any]]:
    return list(getattr(resp, "data", None) or [])


def _cid(company_id: Any) -> str:
    cid = str(company_id or "").strip().lower()
    if not _UUID.match(cid):
        raise HTTPException(status_code=400, detail="company_id precisa ser um uuid")
    return cid


# ---------------------------------------------------------------------------------------------------------------------
# leitura
# ---------------------------------------------------------------------------------------------------------------------
def qcm_aderido(db: Any, company_id: str) -> bool:
    """A corretora participa do Quem Cobra Menos (adesão ATIVA em `multicalculo_adesoes`)?"""
    linhas = _dados(db.table("multicalculo_adesoes").select("corretora_company_id, ativa")
                    .eq("corretora_company_id", company_id).eq("ativa", True).limit(1).execute())
    return any(str(l.get("corretora_company_id", "")).lower() == company_id and l.get("ativa") for l in linhas)


def _linha(db: Any, company_id: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(db.table(CFG.TABELA).select("company_id, config, atualizado_em")
                    .eq("company_id", company_id).limit(1).execute())
    return next((l for l in linhas if str(l.get("company_id", "")).lower() == company_id), None)


def _versao(linha: Optional[Dict[str, Any]]) -> Optional[str]:
    """A VERSÃO da linha da corretora = o `atualizado_em` como o banco o devolveu (None: a corretora ainda não tem
    linha). A tela lê com o GET e devolve no PUT — concorrência otimista (conserto 131-0 A, juiz P1 · red P2)."""
    v = (linha or {}).get("atualizado_em")
    return str(v) if v else None


def _duplicada(exc: Exception) -> bool:
    texto = f"{getattr(exc, 'code', '')} {exc}".lower()
    return "23505" in texto or "duplicate key" in texto


def _efetivo(cfg: Dict[str, Any], servico: str) -> Dict[str, Any]:
    """O que a tela mostra de um serviço — já com a base e o que o serviço sobrepõe."""
    bloco = cfg["servicos"][servico]
    saida: Dict[str, Any] = {"modo": bloco["modo"], "excecoes_do_modo": list(bloco.get("excecoes_do_modo") or []),
                             "preferencias_de_seguradoras": cfg.get("preferencias_de_seguradoras") or {}}
    if servico == "renovacao":
        ren = cfg.get("renovacao") or {}
        saida.update({"conta_global_se_vence_em_dias": CFG.conta_global_se_vence_em_dias(cfg),
                      "antecedencia_dias": ren.get("antecedencia_dias"),
                      "reajuste_basica_pct": {r: CFG.reajuste_basica_pct(cfg, r)
                                              for r in CFG.PADRAO_DO_PRODUTO["renovacao"]["reajuste_basica_pct"]},
                      # SPEC-131-B G3 — a aba Configurar da Renovação lê pelos MESMOS leitores da madrugada
                      "opcoes": list(CFG.opcoes_da_renovacao(cfg)),
                      "teto_por_conta_noite": CFG.teto_por_conta_noite(cfg),
                      "antecipar_ate_dias": CFG.antecipar_ate_dias(cfg),
                      # SPEC-131-B G5 — "Com qual conta" (D-131-04), pelo leitor que `qual_agger.decidir` usa
                      "conta": CFG.conta_da_renovacao(cfg)})
    return saida


def _opcoes_da_renovacao_na_ordem() -> List[str]:
    """As opções da renovação na ORDEM do disparo (`presets.OPCOES_DA_RENOVACAO`): "quantas opções" N = as N primeiras."""
    from portal_worker.multicalculo.presets import OPCOES_DA_RENOVACAO

    return list(OPCOES_DA_RENOVACAO)


def retrato(db: Any, company_id: str) -> Dict[str, Any]:
    """A config dos serviços da corretora: o que ELA sobrepôs (cru) e o efetivo de cada serviço."""
    linha = _linha(db, company_id)
    bruto = dict((linha or {}).get("config") or {})
    aderido = qcm_aderido(db, company_id)
    servicos = ["cotacao", "renovacao"] + (["qcm"] if aderido else [])
    cfg_base = CFG.mesclar(bruto or None)
    sobreposto = bruto.get("servicos") if isinstance(bruto.get("servicos"), dict) else {}
    return {
        "company_id": company_id,
        "qcm_aderido": aderido,
        "servicos": servicos,
        "editaveis": sorted(CFG.EDITAVEL_POR_SERVICO),
        "modos": list(CFG.MODOS),
        "ramos": [{"codigo": c, "nome": n} for c, n in RAMOS_DA_TELA],
        "comum": {"preferencias_de_seguradoras": cfg_base.get("preferencias_de_seguradoras") or {}},
        "sobreposto": {"servicos": {s: sobreposto[s] for s in servicos if isinstance(sobreposto.get(s), dict)},
                       "preferencias_de_seguradoras": bruto.get("preferencias_de_seguradoras")},
        "efetivo": {s: _efetivo(CFG.mesclar(bruto or None, s), s) for s in servicos},
        "padrao": {s: _efetivo(CFG.mesclar(None, s), s) for s in servicos},
        "faixas": {"antecedencia_dias_max": CFG.ANTECEDENCIA_DIAS_MAX,
                   "conta_global_dias_max": CFG.CONTA_GLOBAL_DIAS_MAX,
                   # SPEC-131-B G3 — as faixas das chaves da madrugada que a aba Configurar edita (a tela não escreve
                   # nenhum número comercial: o guarda G8 da 130-A)
                   "teto_por_conta_noite": list(CFG.TETO_POR_CONTA_NOITE_FAIXA),
                   "antecipar_ate_dias": list(CFG.ANTECIPAR_ATE_DIAS_FAIXA),
                   "opcoes_da_renovacao": _opcoes_da_renovacao_na_ordem(),
                   "contas_da_renovacao": list(CFG.CONTAS_DA_RENOVACAO)},
        "configurado": bool(sobreposto),
        "versao": _versao(linha),
    }


@router.get("")
async def ler(company_id: str, x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    cid = _cid(company_id)
    try:
        return retrato(_db(), cid)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — nunca o corpo (pode trazer a linha)
        logger.error("[SERVICOS] leitura falhou (%s)", type(e).__name__)
        raise HTTPException(status_code=500, detail="não consegui ler os serviços da corretora agora")


# ---------------------------------------------------------------------------------------------------------------------
# escrita
# ---------------------------------------------------------------------------------------------------------------------
def gravar(db: Any, company_id: str, *, versao: Optional[str], servicos: Any = None,
           preferencias_de_seguradoras: Any = None, atualizado_por: Optional[str] = None) -> Dict[str, Any]:
    """Grava SÓ `servicos.<serviço>` (cada serviço enviado substitui o bloco dele; os outros ficam) e as preferências
    comuns. O resto da linha da corretora fica como estava. Recusa (`ValueError`) com a lista de erros.

    🔴 conserto 131-0 A (juiz P1 · red P2): `versao` é a que a tela LEU (`retrato()['versao']`). Grava SÓ se a linha
    ainda está nela — `update … where company_id = … and atualizado_em = versao`; sem linha, um `insert` que o banco
    recusa se outra pessoa criou antes. Mudou no meio → `Conflito` e NADA é gravado (dois admins nunca se apagam)."""
    erros = CFG.erros_da_edicao(servicos, preferencias_de_seguradoras)
    if servicos is None and preferencias_de_seguradoras is None:
        erros.append("nada para gravar: envie servicos e/ou preferencias_de_seguradoras")
    if erros:
        raise ValueError("; ".join(erros))
    linha = _linha(db, company_id)
    if (str(versao) if versao else None) != _versao(linha):
        raise Conflito(FRASE_DO_CONFLITO)
    nova = dict((linha or {}).get("config") or {})
    if servicos is not None:
        blocos = dict(nova.get("servicos") or {}) if isinstance(nova.get("servicos"), dict) else {}
        for s, bloco in servicos.items():
            # o que a tela EDITA vale como veio (chave não enviada = a tela a tirou); o que ela não edita fica
            antigo = blocos.get(s) if isinstance(blocos.get(s), dict) else {}
            blocos[s] = {**{k: v for k, v in antigo.items() if k not in CFG.EDITAVEL_POR_SERVICO[s]}, **dict(bloco)}
        nova["servicos"] = blocos
    if preferencias_de_seguradoras is not None:
        nova["preferencias_de_seguradoras"] = dict(preferencias_de_seguradoras)
    # 🔴 o que se grava SOBREVIVE à leitura: cada serviço editado, relido pelo único leitor, tem o que a tela mandou
    for s, bloco in (servicos or {}).items():
        efetivo = CFG.mesclar(nova, s)
        if "modo" in bloco and efetivo["servicos"][s]["modo"] != bloco["modo"]:
            raise ValueError(f"servicos.{s}.modo não sobreviveu à leitura")
        if "excecoes_do_modo" in bloco and len(efetivo["servicos"][s]["excecoes_do_modo"]) != len(
                bloco["excecoes_do_modo"]):
            raise ValueError(f"servicos.{s}.excecoes_do_modo não sobreviveu à leitura")
    autor = str(atualizado_por or "").strip().lower()
    patch = {"config": nova, "atualizado_em": datetime.now(timezone.utc).isoformat(),
             "atualizado_por": autor if _UUID.match(autor) else None}
    if linha is None:
        try:
            db.table(CFG.TABELA).insert({"company_id": company_id, **patch}).execute()
        except Exception as e:  # noqa: BLE001
            if _duplicada(e):
                raise Conflito(FRASE_DO_CONFLITO) from None
            raise
    else:
        feito = _dados(db.table(CFG.TABELA).update(patch).eq("company_id", company_id)
                       .eq("atualizado_em", linha["atualizado_em"]).execute())
        if not feito:
            raise Conflito(FRASE_DO_CONFLITO)
    return retrato(db, company_id)


@router.put("")
async def salvar(request: Request, x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="corpo inválido")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    fora = sorted(set(body) - _CHAVES_DO_PUT)
    if fora:
        raise HTTPException(status_code=422, detail=f"chave fora da lista: {', '.join(fora)}")
    cid = _cid(body.get("company_id"))
    if "versao" not in body:
        # a tela manda a versão que leu (null quando a corretora ainda não tem linha) — sem ela não há como saber se
        # outra pessoa salvou no meio
        raise HTTPException(status_code=422, detail="falta a versão que a tela leu: recarregue a página")
    try:
        return {"ok": True, **gravar(_db(), cid, versao=body.get("versao"), servicos=body.get("servicos"),
                                     preferencias_de_seguradoras=body.get("preferencias_de_seguradoras"),
                                     atualizado_por=body.get("atualizado_por"))}
    except Conflito as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error("[SERVICOS] gravação falhou (%s)", type(e).__name__)
        raise HTTPException(status_code=500, detail="não consegui salvar agora — nada mudou")


# ---------------------------------------------------------------------------------------------------------------------
# a ordem guiada (D-131-0-07) — 4 passos, SÓ LEITURA
# ---------------------------------------------------------------------------------------------------------------------
def _passo(chave: str, titulo: str, estado: str, detalhe: str, link: str, **extra: Any) -> Dict[str, Any]:
    return {"chave": chave, "titulo": titulo, "estado": estado, "detalhe": detalhe, "link": link, **extra}


def _sistema_de_gestao(db: Any, company_id: str) -> Dict[str, Any]:
    titulo = "Conectar o sistema de gestão"
    try:
        linhas = _dados(db.table("tenant_connections").select("id, company_id, status, connector_templates(slug)")
                        .eq("company_id", company_id).execute())
    except Exception as e:  # noqa: BLE001
        logger.warning("[SERVICOS] prontidão: conexões ilegíveis (%s)", type(e).__name__)
        return _passo("sistema_de_gestao", titulo, "nao_sei", "Não consegui conferir agora.", _LINK_CONECTORES)
    infocap = [l for l in linhas if str(l.get("company_id", "")).lower() == company_id
               and ((l.get("connector_templates") or {}).get("slug") == "infocap")]
    if any(l.get("status") == "connected" for l in infocap):
        return _passo("sistema_de_gestao", titulo, "pronto", "A InfoCap está conectada.", _LINK_CONECTORES)
    if infocap:
        return _passo("sistema_de_gestao", titulo, "atencao",
                      "A InfoCap está cadastrada, mas não está conectada. Abra a conexão e confira o login.",
                      _LINK_CONECTORES)
    return _passo("sistema_de_gestao", titulo, "falta",
                  "Conecte a InfoCap: é dela que o AutoBrokers lê as apólices que vão vencer e quem cuida de cada uma.",
                  _LINK_CONECTORES)


def _agger_da_corretora(db: Any, company_id: str) -> Dict[str, Any]:
    from portal_worker.multicalculo import conta_do_robo as CR  # a regra ÚNICA da conta da corretora

    titulo = "Conectar o Agger da corretora"
    try:
        conta = CR.conta_da_corretora(db, company_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("[SERVICOS] prontidão: Agger da corretora ilegível (%s)", type(e).__name__)
        return _passo("agger_da_corretora", titulo, "nao_sei", "Não consegui conferir agora.", _LINK_CONECTORES)
    if conta is None or str(conta.get("company_id", company_id)).lower() != company_id:
        return _passo("agger_da_corretora", titulo, "falta",
                      "Coloque o login do Agger que o robô usa. Ele é o reserva de todos os cálculos.", _LINK_CONECTORES)
    if not conta.get("secret_encrypted"):
        return _passo("agger_da_corretora", titulo, "falta", "O Agger da corretora está sem senha.", _LINK_CONECTORES)
    if conta.get("robo_estado") == "bloqueado":
        return _passo("agger_da_corretora", titulo, "atencao", "O Agger recusou a senha. Troque a senha.",
                      _LINK_CONECTORES)
    return _passo("agger_da_corretora", titulo, "pronto", "O Agger da corretora está conectado.", _LINK_CONECTORES)


def _equipe(db: Any, company_id: str) -> Dict[str, Any]:
    titulo = "Equipe e os Aggers de cada pessoa"
    try:
        membros = _dados(db.table("company_members").select("user_id, company_id, status, funcoes")
                         .eq("company_id", company_id).execute())
        tem_funcoes = True
    except Exception:  # noqa: BLE001 — a coluna `funcoes` é da F1; sem ela, ninguém tem função marcada ainda
        membros = _dados(db.table("company_members").select("user_id, company_id, status")
                         .eq("company_id", company_id).execute())
        tem_funcoes = False
    ativos = [m for m in membros if str(m.get("company_id", "")).lower() == company_id and m.get("status") == "active"]
    ids_ativos = {str(m.get("user_id")) for m in ativos}
    comerciais = {str(m.get("user_id")) for m in ativos if "comercial" in (m.get("funcoes") or [])} \
        if tem_funcoes else set()
    try:   # a conta de PESSOA (`uso='membro'`, F3) — só de membro ATIVO desta corretora, e com senha
        contas = _dados(db.table("portal_accounts").select("company_id, dono_user_id")
                        .eq("company_id", company_id).eq("portal_key", "agger").eq("uso", "membro")
                        .not_.is_("secret_encrypted", "null").execute())
        com_agger = {str(c.get("dono_user_id")) for c in contas
                     if str(c.get("company_id", "")).lower() == company_id and str(c.get("dono_user_id")) in ids_ativos}
    except Exception:  # noqa: BLE001 — a coluna `uso` é da F3; sem ela, ninguém tem Agger próprio ainda
        com_agger = set()
    try:   # o vínculo código de produtor ↔ pessoa (`membro_produtores`, F2)
        vinculos = len([v for v in _dados(db.table("membro_produtores").select("company_id, user_id")
                                          .eq("company_id", company_id).execute())
                        if str(v.get("company_id", "")).lower() == company_id])
    except Exception:  # noqa: BLE001 — a tabela é da F2; sem ela, nenhum vínculo
        vinculos = 0
    numeros = {"pessoas_ativas": len(ativos), "comerciais": len(comerciais),
               "comerciais_com_agger": len(comerciais & com_agger), "com_agger_proprio": len(com_agger),
               "vinculos_de_produtor": vinculos}
    if not comerciais:
        estado, detalhe = "falta", "Marque quem é comercial na equipe e ligue cada um ao código dele no sistema de gestão."
    elif len(comerciais & com_agger) < len(comerciais) or not vinculos:
        estado = "em_parte"
        detalhe = (f"{len(comerciais & com_agger)} de {len(comerciais)} comerciais com o Agger próprio; "
                   f"{vinculos} código(s) de produtor ligados a pessoas.")
    else:
        estado, detalhe = "pronto", "Todos os comerciais têm o Agger próprio e o código de produtor ligado."
    return _passo("equipe", titulo, estado, detalhe, _LINK_EQUIPE, numeros=numeros)


def _servicos_configurados(db: Any, company_id: str) -> Dict[str, Any]:
    titulo = "Escolher o que o AutoBrokers faz em cada serviço"
    linha = _linha(db, company_id)
    bruto = ((linha or {}).get("config") or {}).get("servicos")
    feitos = [s for s in CFG.EDITAVEL_POR_SERVICO if isinstance(bruto, dict) and bruto.get(s)]
    if feitos:
        return _passo("servicos", titulo, "pronto", "As regras de cada serviço estão escolhidas.", _LINK_SERVICOS)
    return _passo("servicos", titulo, "falta",
                  "Enquanto você não escolher, vale o padrão: o AutoBrokers só calcula e deixa pronto no Agger.",
                  _LINK_SERVICOS)


def prontidao(db: Any, company_id: str) -> Dict[str, Any]:
    passos = [_sistema_de_gestao(db, company_id), _agger_da_corretora(db, company_id), _equipe(db, company_id),
              _servicos_configurados(db, company_id)]
    return {"company_id": company_id, "passos": passos,
            "prontos": sum(1 for p in passos if p["estado"] == "pronto"), "total": len(passos)}


@router.get("/prontidao")
async def ler_prontidao(company_id: str,
                        x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key")):
    _require_internal_key(x_key)
    cid = _cid(company_id)
    try:
        return prontidao(_db(), cid)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("[SERVICOS] prontidão falhou (%s)", type(e).__name__)
        raise HTTPException(status_code=500, detail="não consegui conferir a configuração agora")
