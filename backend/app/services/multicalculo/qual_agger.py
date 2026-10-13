# -*- coding: utf-8 -*-
"""QUAL AGGER calcula — SPEC-131-0 parte A · F3 (U5), decisões D-131-0-05/06/29/32.

UMA função decide em qual conta do Agger cada cálculo acontece; a porta (`porta.calcular`/`recalcular`) a chama POR
CORRETORA do pedido e grava a decisão em `multicalculo_calculos` (`conta_exigida_id`, `conta_regra`, `conta_fallback`,
`conta_motivo`); o motor obedece (`robos.escolher(somente=conta_exigida_id)` — essa, nunca outra).

    decidir(db, *, company_id, servico, solicitante_user_id=None, dono_user_id=None, conta_de_origem_id=None,
            vence_em_dias=None, cfg=None) -> DecisaoDeConta

As regras (SPEC §5):
    qcm ........ o Agger da CORRETORA (`conta_id` None: o motor gira SÓ entre as contas `uso='global'`)
    cotacao .... o Agger de QUEM PEDIU, se ativo; senão o da corretora, com aviso
    renovacao .. o Agger do DONO da apólice; sem dono / sem conta / dono fora da equipe → o da corretora + aviso ao
                 admin; senha do dono recusada → RECUSA (o cálculo não sai), e vai para o da corretora só se a apólice
                 vence em menos de `servicos.renovacao.conta_global_se_vence_em_dias` dias (padrão 5)
    recálculo .. (`conta_de_origem_id`) a MESMA conta — o negócio mora nela

🔴 O Agger de uma pessoa só vale se ela é membro ATIVO DESTA corretora e o usuário dela está ativo — reconferido aqui
(`robos.membro_ativo`, o MESMO que o motor usa na hora de escolher) e de novo no motor. Falha = inelegível (fail-closed).
🔴 Toda leitura filtra `company_id` (CLAUDE.md §7). Nada aqui lê ou devolve senha, segredo ou login.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional

from portal_worker.multicalculo import robos as ROB

logger = logging.getLogger(__name__)

SERVICOS = ("qcm", "cotacao", "renovacao")
#: SPEC §5.3 — a F4 põe a chave no padrão do produto; aqui o MESMO número vale quando ela falta
PADRAO_CONTA_GLOBAL_SE_VENCE_EM_DIAS = 5
#: o Agger de uma pessoa pode calcular nestes estados (ocupada: a pessoa está nele — o motor espera e tenta de novo)
_ESTADOS_QUE_CALCULAM = (ROB.ATIVO, ROB.OCUPADA)


@dataclass(frozen=True)
class DecisaoDeConta:
    """`conta_id` None = o rodízio das contas da corretora (`uso='global'`). `recusa` não-nula = o cálculo NÃO sai."""
    conta_id: Optional[str]
    uso: Optional[str]
    regra: str
    fallback: bool
    motivo: str
    aviso: Optional[str] = None
    recusa: Optional[str] = None
    #: SPEC-131-A (D-131-08): a quem o AVISO desta decisão vai — o SUBSTITUTO quando o dono está ausente; None = o
    #: dono/quem pediu, como sempre (quem entrega é a madrugada, pelo canal in-app que já existe)
    avisar_user_id: Optional[str] = None

    def texto_para_o_banco(self) -> str:
        """O que vai para `multicalculo_calculos.conta_motivo` (≤ 500): o porquê e, quando há, o aviso a quem precisa
        saber (quem o entrega é a 131/132)."""
        partes = [self.motivo] + ([self.aviso] if self.aviso else [])
        return " ".join(p.strip() for p in partes if p and p.strip())[:500]


def _cliente(db: Any) -> Any:
    return db if hasattr(db, "table") else getattr(db, "client", db)


def _dados(r: Any) -> list:
    return list(getattr(r, "data", None) or [])


# ---------------------------------------------------------------------------------------------------------------------
# as leituras (sempre com company_id)
# ---------------------------------------------------------------------------------------------------------------------
_COLS = "id, company_id, portal_key, uso, dono_user_id, robo_estado, secret_encrypted"


def _conta_da_pessoa(supa: Any, company_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(supa.table("portal_accounts").select(_COLS).eq("company_id", str(company_id))
                    .eq("portal_key", ROB.PORTAL_KEY).eq("uso", ROB.MEMBRO).eq("dono_user_id", str(user_id))
                    .limit(1).execute())
    linhas = [c for c in linhas if str(c.get("company_id")) == str(company_id)
              and str(c.get("dono_user_id")) == str(user_id) and c.get("uso") == ROB.MEMBRO]
    return linhas[0] if linhas else None


def _conta_por_id(supa: Any, company_id: str, conta_id: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(supa.table("portal_accounts").select(_COLS).eq("id", str(conta_id))
                    .eq("company_id", str(company_id)).eq("portal_key", ROB.PORTAL_KEY).limit(1).execute())
    linhas = [c for c in linhas if str(c.get("company_id")) == str(company_id)]
    return linhas[0] if linhas else None


def _tem_global_conectada(supa: Any, company_id: str) -> bool:
    try:
        linhas = _dados(supa.table("portal_accounts").select(_COLS).eq("company_id", str(company_id))
                        .eq("portal_key", ROB.PORTAL_KEY).eq("uso", ROB.GLOBAL).execute())
    except Exception:  # noqa: BLE001 — é só para o aviso: na dúvida, não acrescenta nada
        return True
    return any(c.get("secret_encrypted") and c.get("robo_estado") in (ROB.ATIVO, ROB.OCUPADA) for c in linhas)


def _limite_em_dias(cfg: Optional[Mapping[str, Any]]) -> int:
    """`servicos.renovacao.conta_global_se_vence_em_dias` pelo leitor ÚNICO da config (`config.conta_global_se_vence_
    em_dias`, F4 — o padrão do produto quando falta). Sem config legível → o mesmo padrão."""
    if cfg is None:
        return PADRAO_CONTA_GLOBAL_SE_VENCE_EM_DIAS
    from app.services.multicalculo import config as CFG

    return int(CFG.conta_global_se_vence_em_dias(cfg))


def _cfg_da_renovacao(company_id: str, supa: Any) -> Optional[Mapping[str, Any]]:
    """A config da corretora com o manual da renovação (o manual da renovação, F4). Ilegível → None
    (vale o padrão 5, com log)."""
    try:
        from app.services.multicalculo import config as CFG

        return CFG.carregar(company_id, db=supa, servico="renovacao")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[QUAL_AGGER] config da renovação ilegível (%s) — vale o padrão de %s dias",
                       type(exc).__name__, PADRAO_CONTA_GLOBAL_SE_VENCE_EM_DIAS)
        return None


def _primeiro_nome(supa: Any, company_id: str, user_id: Optional[str]) -> Optional[str]:
    """O primeiro nome de um MEMBRO desta corretora (o aviso NOMEIA a pessoa: "nunca calado"). Só se ele é da equipe
    (`company_members` filtrado por `company_id`); qualquer falha → None (o aviso diz "o dono"/"o substituto")."""
    if not user_id:
        return None
    try:
        vinc = _dados(supa.table("company_members").select("user_id, company_id").eq("company_id", str(company_id))
                      .eq("user_id", str(user_id)).limit(1).execute())
        if not [v for v in vinc if str(v.get("company_id")) == str(company_id)]:
            return None
        usr = _dados(supa.table("users_v2").select("id, first_name").eq("id", str(user_id)).limit(1).execute())
        nome = str((usr[0] if usr else {}).get("first_name") or "").strip().split(" ")[0]
        return nome[:40] or None
    except Exception:  # noqa: BLE001
        return None


def _hoje() -> date:
    """O dia de HOJE no horário de Brasília (a janela e a ausência são escritas nele; mesmo fuso fixo dos robôs)."""
    return datetime.now(ROB.FUSO_DA_JANELA).date()


def substituto_ativo(supa: Any, company_id: str, user_id: Optional[str], hoje: Optional[date] = None) -> Optional[str]:
    """SPEC-131-A (D-131-08): o substituto de `user_id` com AUSÊNCIA ATIVA hoje (`membro_ausencias`, `de ≤ hoje ≤ ate`),
    nesta corretora — ou None. Tabela ausente (migration não aplicada) ou ilegível → None, com log (o cálculo segue)."""
    if not user_id:
        return None
    dia = (hoje or _hoje()).isoformat()
    try:
        linhas = _dados(supa.table("membro_ausencias").select("company_id, user_id, substituto_user_id, de, ate")
                        .eq("company_id", str(company_id)).eq("user_id", str(user_id))
                        .lte("de", dia).gte("ate", dia).execute())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[QUAL_AGGER] ausências ilegíveis (%s) — segue sem substituto", type(exc).__name__)
        return None
    linhas = [x for x in linhas if str(x.get("company_id")) == str(company_id) and str(x.get("user_id")) == str(user_id)
              and str(x.get("de") or "")[:10] <= dia <= str(x.get("ate") or "")[:10] and x.get("substituto_user_id")]
    return str(linhas[0]["substituto_user_id"]) if linhas else None


#: o desvio das 06:15 (madrugada) e outros motivos conhecidos de forçar o Agger da corretora → a frase do aviso
_FRASE_DO_DESVIO = {
    "renovacao_desvio_0615": "o Agger {de} não ficou livre de madrugada",
}


def _frase_do_desvio(motivo: str, de: str) -> str:
    """O porquê do desvio em português de gente: o código conhecido vira frase; texto livre vai saneado e curto."""
    m = str(motivo or "").strip()
    if m in _FRASE_DO_DESVIO:
        return _FRASE_DO_DESVIO[m].format(de=de)
    limpo = re.sub(r"\s+", " ", re.sub(r"[^\w\sÀ-ÿ.,:()%-]", "", m))[:160].strip()
    return limpo or f"o Agger {de} não pôde ser usado"


# ---------------------------------------------------------------------------------------------------------------------
# os textos (português de gente — eles chegam à corretora)
# ---------------------------------------------------------------------------------------------------------------------
_AVISO_SEM_GLOBAL = ("O Agger da corretora também não está conectado: conecte-o em Conexões para este cálculo sair.")


def _da_corretora(supa: Any, company_id: str, *, regra: str, motivo: str, aviso: Optional[str],
                  fallback: bool = True) -> DecisaoDeConta:
    if fallback and not _tem_global_conectada(supa, company_id):
        aviso = " ".join(x for x in (aviso, _AVISO_SEM_GLOBAL) if x)
    return DecisaoDeConta(conta_id=None, uso=ROB.GLOBAL, regra=regra, fallback=fallback, motivo=motivo, aviso=aviso)


def _situacao(conta: Optional[Dict[str, Any]]) -> str:
    """sem_conta · desconectado · senha_recusada · pausado · pronta."""
    if conta is None:
        return "sem_conta"
    if not conta.get("secret_encrypted"):
        return "desconectado"
    if conta.get("robo_estado") == ROB.BLOQUEADO:
        return "senha_recusada"
    if conta.get("robo_estado") not in _ESTADOS_QUE_CALCULAM:
        return "pausado"
    return "pronta"


# ---------------------------------------------------------------------------------------------------------------------
# a decisão
# ---------------------------------------------------------------------------------------------------------------------
def decidir(db: Any, *, company_id: str, servico: str, solicitante_user_id: Optional[str] = None,
            dono_user_id: Optional[str] = None, conta_de_origem_id: Optional[str] = None,
            vence_em_dias: Optional[int] = None, cfg: Optional[Mapping[str, Any]] = None,
            substituto_user_id: Optional[str] = None, forcar_corretora_motivo: Optional[str] = None,
            hoje: Optional[date] = None) -> DecisaoDeConta:
    """Em qual conta do Agger DESTA corretora (`company_id` = a corretora de registro do cálculo) o cálculo sai.

    SPEC-131-A (D-131-04/08), só na RENOVAÇÃO:
      · `forcar_corretora_motivo` — o desvio das 06:15: o Agger da CORRETORA, com o aviso NOMEANDO o dono e o porquê
        (nunca calado; o motivo vazio é recusado).
      · ausência ativa do dono (`membro_ausencias`, ou `substituto_user_id` passado por quem já leu) — o cálculo SEGUE no
        Agger do dono e o AVISO vai ao substituto, nomeado (`avisar_user_id`)."""
    if servico not in SERVICOS:
        raise ValueError(f"serviço desconhecido: {servico!r} (aceitos: {', '.join(SERVICOS)})")
    if not company_id:
        raise ValueError("company_id obrigatório")
    if (forcar_corretora_motivo is not None or substituto_user_id is not None) and servico != "renovacao":
        raise ValueError("forçar o Agger da corretora e o substituto só valem na renovação")
    supa = _cliente(db)
    if servico == "renovacao" and conta_de_origem_id is None:
        if forcar_corretora_motivo is not None:
            return _desvio_para_a_corretora(supa, company_id, dono_user_id, forcar_corretora_motivo)
        d = _decidir(supa, company_id=company_id, servico=servico, solicitante_user_id=solicitante_user_id,
                     dono_user_id=dono_user_id, conta_de_origem_id=None, vence_em_dias=vence_em_dias, cfg=cfg)
        return _com_o_substituto(supa, company_id, dono_user_id, substituto_user_id, d, hoje)
    return _decidir(supa, company_id=company_id, servico=servico, solicitante_user_id=solicitante_user_id,
                    dono_user_id=dono_user_id, conta_de_origem_id=conta_de_origem_id, vence_em_dias=vence_em_dias,
                    cfg=cfg)


def _desvio_para_a_corretora(supa: Any, company_id: str, dono_user_id: Optional[str], motivo: str) -> DecisaoDeConta:
    """O desvio das 06:15: SEMPRE o Agger da corretora, e o aviso diz DE QUEM era a renovação e POR QUÊ saiu dali."""
    if not str(motivo or "").strip():
        raise ValueError("forçar o Agger da corretora exige o motivo (o aviso nunca sai calado)")
    nome = _primeiro_nome(supa, company_id, dono_user_id)
    de = f"de {nome}" if nome else ("do dono" if dono_user_id else "de quem cuida desta apólice")
    porque = _frase_do_desvio(motivo, de)
    quem = f"{nome}, esta" if nome else "Esta"
    return _da_corretora(supa, company_id, regra="renovacao_desvio_da_corretora",
                         motivo=f"Calculada no Agger da corretora porque {porque}.",
                         aviso=f"{quem} renovação foi calculada no Agger da CORRETORA, não no seu — confira lá.")


def _com_o_substituto(supa: Any, company_id: str, dono_user_id: Optional[str], substituto_user_id: Optional[str],
                      d: DecisaoDeConta, hoje: Optional[date]) -> DecisaoDeConta:
    """D-131-08: o dono ausente HOJE → a conta é a MESMA da decisão (o Agger do dono, ou o da corretora pelas regras de
    sempre) e o aviso NOMEIA o substituto e vai a ele. Recusa continua recusa (só ganha o nome de quem é avisado)."""
    if not dono_user_id:
        return d
    sub = substituto_user_id or substituto_ativo(supa, company_id, dono_user_id, hoje)
    if not sub or str(sub) == str(dono_user_id) or not ROB.membro_ativo(supa, company_id, sub):
        return d
    nome_sub = _primeiro_nome(supa, company_id, sub)
    nome_dono = _primeiro_nome(supa, company_id, dono_user_id)
    texto = (f"{nome_dono or 'O dono'} está ausente: o aviso desta renovação vai para "
             f"{nome_sub or 'quem o substitui'}, que cuida dela até a volta.")
    return replace(d, aviso=" ".join(x for x in (d.aviso, texto) if x), avisar_user_id=str(sub))


def _decidir(supa: Any, *, company_id: str, servico: str, solicitante_user_id: Optional[str],
             dono_user_id: Optional[str], conta_de_origem_id: Optional[str], vence_em_dias: Optional[int],
             cfg: Optional[Mapping[str, Any]]) -> DecisaoDeConta:
    """As regras da 131-0 A, byte a byte (o substituto e o desvio são camadas por cima, em `decidir`)."""

    # -- o recálculo: o negócio mora na conta em que saiu ------------------------------------------------------------
    if conta_de_origem_id:
        conta = _conta_por_id(supa, company_id, conta_de_origem_id)
        if conta is None:
            return DecisaoDeConta(None, None, "recalculo_mesma_conta", False,
                                  "O cálculo de origem não saiu numa conta desta corretora.",
                                  recusa="Não dá para recalcular: o cálculo de origem não é desta corretora.")
        if conta.get("uso") == ROB.MEMBRO and not ROB.membro_ativo(supa, company_id, conta.get("dono_user_id")):
            return DecisaoDeConta(None, ROB.MEMBRO, "recalculo_mesma_conta", False,
                                  "O negócio está no Agger de uma pessoa que não está mais ativa na equipe.",
                                  recusa="Não dá para recalcular: o negócio está no Agger de uma pessoa que saiu da "
                                         "equipe. Peça um cálculo novo.")
        return DecisaoDeConta(str(conta["id"]), conta.get("uso"), "recalculo_mesma_conta", False,
                              "O recálculo entra no mesmo negócio, no mesmo Agger em que o cálculo saiu.")

    # -- o Quem Cobra Menos: sempre o Agger da corretora ------------------------------------------------------------
    if servico == "qcm":
        return DecisaoDeConta(None, ROB.GLOBAL, "qcm_global", False,
                              "O Quem Cobra Menos calcula sempre no Agger da corretora.")

    # -- a cotação: o Agger de quem pediu -----------------------------------------------------------------------------
    if servico == "cotacao":
        if not solicitante_user_id:
            return _da_corretora(supa, company_id, regra="cotacao_da_corretora",
                                 motivo="Não sei quem pediu esta cotação.",
                                 aviso="Ela vai pelo Agger da corretora.")
        if not ROB.membro_ativo(supa, company_id, solicitante_user_id):
            return _da_corretora(supa, company_id, regra="cotacao_da_corretora",
                                 motivo="Quem pediu não está ativo na equipe desta corretora.",
                                 aviso="A cotação vai pelo Agger da corretora.")
        conta = _conta_da_pessoa(supa, company_id, solicitante_user_id)
        situacao = _situacao(conta)
        if situacao == "pronta":
            return DecisaoDeConta(str(conta["id"]), ROB.MEMBRO, "cotacao_da_pessoa", False,
                                  "Calculada no Agger de quem pediu.")
        porque = {
            "sem_conta": "Quem pediu ainda não tem o próprio Agger conectado.",
            "desconectado": "O Agger de quem pediu está desconectado.",
            "senha_recusada": "O Agger de quem pediu recusou a senha — troque a senha dele em Conexões.",
            "pausado": "O Agger de quem pediu está pausado.",
        }[situacao]
        return _da_corretora(supa, company_id, regra="cotacao_da_corretora", motivo=porque,
                             aviso="Esta cotação vai pelo Agger da corretora.")

    # -- a renovação: o Agger do dono --------------------------------------------------------------------------------
    if cfg is None and vence_em_dias is not None:
        cfg = _cfg_da_renovacao(company_id, supa)
    limite = _limite_em_dias(cfg)
    if not dono_user_id:
        return _da_corretora(supa, company_id, regra="renovacao_da_corretora",
                             motivo="Esta apólice não tem dono definido na equipe.",
                             aviso="A renovação vai pelo Agger da corretora — confira quem é o responsável por ela.")
    if not ROB.membro_ativo(supa, company_id, dono_user_id):
        return _da_corretora(supa, company_id, regra="renovacao_da_corretora",
                             motivo="O dono desta renovação não está ativo na equipe desta corretora.",
                             aviso="A renovação vai pelo Agger da corretora — confira quem assume esta carteira.")
    conta = _conta_da_pessoa(supa, company_id, dono_user_id)
    situacao = _situacao(conta)
    if situacao == "pronta":
        return DecisaoDeConta(str(conta["id"]), ROB.MEMBRO, "renovacao_do_dono", False,
                              "Calculada no Agger do dono da apólice.")
    if situacao == "senha_recusada":
        if vence_em_dias is not None and int(vence_em_dias) < limite:
            return _da_corretora(supa, company_id, regra="renovacao_da_corretora_urgente",
                                 motivo=f"O Agger do dono recusou a senha e a apólice vence em {int(vence_em_dias)} "
                                        f"dia(s) — menos de {limite}.",
                                 aviso="A renovação foi pelo Agger da corretora para não perder o prazo. Troque a "
                                       "senha do Agger do dono em Conexões.")
        return DecisaoDeConta(None, ROB.MEMBRO, "renovacao_recusada", False,
                              "O Agger do dono recusou a senha.",
                              aviso=None,
                              recusa=f"A renovação não foi calculada: o Agger do dono recusou a senha. Troque a senha "
                                     f"dele em Conexões. Se faltarem menos de {limite} dias para vencer, ela vai pelo "
                                     f"Agger da corretora.")
    porque = {
        "sem_conta": "O dono desta renovação ainda não tem o próprio Agger conectado.",
        "desconectado": "O Agger do dono desta renovação está desconectado.",
        "pausado": "O Agger do dono desta renovação está pausado.",
    }[situacao]
    return _da_corretora(supa, company_id, regra="renovacao_da_corretora", motivo=porque,
                         aviso="A renovação vai pelo Agger da corretora.")


__all__ = ("DecisaoDeConta", "decidir", "SERVICOS", "PADRAO_CONTA_GLOBAL_SE_VENCE_EM_DIAS", "substituto_ativo")
