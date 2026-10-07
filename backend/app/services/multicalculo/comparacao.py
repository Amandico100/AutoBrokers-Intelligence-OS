# -*- coding: utf-8 -*-
"""A COMPARAÇÃO das ofertas do multicálculo — SPEC-130-A U1 (D-130A-03/04/09, D-MC-66/69/74, P-129B-06).

PURO: nenhum I/O. Recebe o que `porta.consultar` devolve (ofertas, eventos, estados) e a config
(`config.carregar`), e devolve:

    classificar(oferta)  → Classe   COMPLETA (comparável) ou DIFERENTE com o MOTIVO em frase de gente
    comparar(...)        → Comparacao   ranking das COMPLETAS por OPÇÃO (padrão, econômica, ajuste NUNCA se
                                        misturam), os diferentes agrupados, quem não respondeu (frase humana,
                                        nunca o texto cru) e a corretora VENCEDORA entre as parceiras
    opcoes(...)          → list[dict]   as 2–3 opções da situação, com nota 0–100, motivos e "o que muda"

🔴 A opção NÃO é coluna da oferta: vem do `calculo_id` → `estados[].opcao` (o gerente, 06/10: 📊 o pedido real tem
38 ofertas da padrão · 44 da econômica · 22 do ajuste, e a econômica TAMBÉM é compreensiva casco 100). Oferta cujo
cálculo não está nos estados não entra em ranking nenhum (fail-closed, contada em `sem_opcao`).

🔴 A comissão não entra aqui: nenhuma saída desta peça carrega `comissao_percentual` (G3 — vai para a página).

Regras POR RAMO (`REGRAS_POR_RAMO`): o AUTO (31) tem a régua medida (compreensiva + casco 100 % FIPE + prêmio
anual); qualquer outro ramo cai em "comparável se a MESMA configuração de coberturas que a maioria do quadro" 💭
até a 129-C medir cada ramo — a peça serve QUALQUER ramo sem quebrar.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from portal_worker.multicalculo.contrato import (
    ACEITACAO,
    COMERCIAL,
    CREDENCIAL,
    DADO,
    DESCONHECIDA,
    INSTABILIDADE,
    OFERTA,
    PENDENTE,
    PERMISSAO,
    RAMO_AUTO,
    SEGURADORA_RECUSOU,
)

from app.services.multicalculo.config import PADRAO_DO_PRODUTO, casa_seguradora, e_produto_de_assinatura, normalizar

SITUACOES: Tuple[str, ...] = ("novo_sem_apolice", "novo_com_apolice", "renovacao")
MAX_MOTIVOS = 4               # o cartão do celular mostra poucos; a ordem já é a de importância (preço primeiro)
CASCO_COMPLETO_PCT = 100      # D-130A-03: completa = paga 100 % da tabela FIPE (régua do produto, não comercial)

# ⛔ a frase que o SEGURADO lê para cada família (nunca o texto cru da seguradora)
FRASE_DA_FAMILIA: Dict[str, str] = {
    INSTABILIDADE: "sistema da seguradora indisponível",
    ACEITACAO: "não aceitou este perfil",
    CREDENCIAL: "não foi possível consultar",
    PERMISSAO: "não foi possível consultar",
    PENDENTE: "não respondeu a tempo",
    COMERCIAL: "não ofereceu preço para este pedido",
    DADO: "pediu um dado a mais para calcular",
    DESCONHECIDA: "não devolveu preço",
}
# a família mais INFORMATIVA vence quando a mesma seguradora recusou de mais de um jeito
_PRIORIDADE_DA_FAMILIA = (ACEITACAO, INSTABILIDADE, COMERCIAL, DADO, PENDENTE, CREDENCIAL, PERMISSAO, DESCONHECIDA)

# o nome que o segurado reconhece (o Agger devolve o nome interno da integração)
NOME_DE_EXIBICAO: Dict[str, str] = {
    "liberty site": "Yelum",            # a ex-Liberty (contrato.SEGURADORA_ANTERIOR_NO_AGGER: "Yelum Seguradora")
    "hdi": "HDI",
    "itau": "Itaú",
    "porto seguro": "Porto",
    "azul assinatura": "Azul por Assinatura",
    "tokio": "Tokio Marine",
}


def nome_de_exibicao(seguradora: Any) -> str:
    bruto = re.sub(r"\s+", " ", str(seguradora or "")).strip()
    return NOME_DE_EXIBICAO.get(normalizar(bruto), bruto)


# ---------------------------------------------------------------------------------------------------------------------
# A CLASSE de uma oferta
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Classe:
    comparavel: bool
    chave: str                       # completa · assinatura · so_terceiros · sem_batida · so_perda_total ·
                                     # casco_parcial · casco_nao_informado · sem_cobertura_informada ·
                                     # configuracao_diferente · sem_preco
    motivo: Optional[str] = None     # a frase humana (None quando comparável)
    exibe_preco: bool = True         # assinatura: o prêmio NÃO é anual — nunca se mostra


COMPLETA = Classe(True, "completa")


def _coberturas(oferta: Mapping[str, Any]) -> Dict[str, Any]:
    c = oferta.get("coberturas")
    if isinstance(c, Mapping):
        return dict(c)
    if isinstance(c, (list, tuple)):            # contrato.Oferta guarda tuplas (chave, valor)
        try:
            return {str(k): v for k, v in c}
        except (TypeError, ValueError):
            return {}
    return {}


def _classificar_auto(oferta: Mapping[str, Any], _referencia: Any = None) -> Classe:
    cob = _coberturas(oferta)
    tipo = normalizar(cob.get("tipoPadronizado") or cob.get("tipo"))
    if not tipo:
        return Classe(False, "sem_cobertura_informada", "a seguradora não informou a cobertura")
    if "compreensiva" not in tipo:
        if "colisao" in tipo:
            return Classe(False, "so_perda_total", "só cobre batida com perda total")
        if "roubo" in tipo or "furto" in tipo or "incendio" in tipo:
            return Classe(False, "sem_batida", "não cobre batida no seu carro")
        if "rcf" in tipo or "terceiro" in tipo:
            return Classe(False, "so_terceiros", "só cobre danos a terceiros")
        return Classe(False, "sem_cobertura_informada", "cobertura diferente da completa")
    casco = cob.get("casco")
    if casco is None or isinstance(casco, bool):
        return Classe(False, "casco_nao_informado", "não informou quanto paga da tabela FIPE")
    try:
        pct = float(casco)
    except (TypeError, ValueError):
        return Classe(False, "casco_nao_informado", "não informou quanto paga da tabela FIPE")
    if pct < CASCO_COMPLETO_PCT:
        return Classe(False, "casco_parcial", f"paga só {pct:g} % da tabela FIPE")
    return COMPLETA


_VOLATEIS = frozenset({"modeloSelecionado"})


def assinatura_de_coberturas(oferta: Mapping[str, Any]) -> Tuple[Tuple[str, str], ...]:
    """A CONFIGURAÇÃO de coberturas de uma oferta (ramos sem régua própria): as chaves e valores devolvidos."""
    return tuple(sorted((str(k), repr(v)) for k, v in _coberturas(oferta).items() if k not in _VOLATEIS))


def _classificar_generico(oferta: Mapping[str, Any], referencia: Any = None) -> Classe:
    if referencia is None or assinatura_de_coberturas(oferta) == referencia:
        return COMPLETA
    return Classe(False, "configuracao_diferente", "cobre um conjunto diferente do pedido")


#: ramo → a régua. O que não está aqui usa `_classificar_generico` (D-MC-73: a 129-C mede e acrescenta).
REGRAS_POR_RAMO: Dict[int, Callable[[Mapping[str, Any], Any], Classe]] = {RAMO_AUTO: _classificar_auto}


def _premio(oferta: Mapping[str, Any]) -> Optional[float]:
    try:
        v = float(oferta.get("premio_total"))
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def classificar(oferta: Mapping[str, Any], *, config: Optional[Mapping[str, Any]] = None, ramo: int = RAMO_AUTO,
                referencia: Any = None) -> Classe:
    """COMPLETA ou DIFERENTE (com o motivo). Assinatura é DIFERENTE em qualquer ramo (P-129B-06)."""
    cfg = config or PADRAO_DO_PRODUTO
    if _premio(oferta) is None:
        return Classe(False, "sem_preco", "sem preço")
    if e_produto_de_assinatura(oferta.get("seguradora"), oferta.get("pacote"), cfg):
        return Classe(False, "assinatura", "preço de assinatura, não é um prêmio anual", exibe_preco=False)
    regra = REGRAS_POR_RAMO.get(int(ramo), _classificar_generico)
    return regra(oferta, referencia)


# ---------------------------------------------------------------------------------------------------------------------
# As características que viram motivo e nota (lidas do texto que a seguradora devolve)
# ---------------------------------------------------------------------------------------------------------------------
_RE_DIAS = re.compile(r"(\d+)\s*(?:dias|diarias|diaria|dia)\b")
_RE_KM = re.compile(r"(\d[\d.]*)\s*km\b")


def dias_de_carro_reserva(cob: Mapping[str, Any]) -> Optional[int]:
    texto = normalizar(cob.get("carroReserva"))
    if not texto:
        return None
    if texto.startswith("nao"):
        return 0
    m = _RE_DIAS.search(texto)
    return int(m.group(1)) if m else None


def guincho(cob: Mapping[str, Any]) -> Tuple[Optional[float], bool]:
    """(km, ilimitado). Desconhecido → (None, False)."""
    texto = normalizar(cob.get("assist24hs"))
    if not texto:
        return None, False
    if "ilimitad" in texto or "km livre" in texto:
        return None, True
    m = _RE_KM.search(texto)
    if m:
        try:
            return float(m.group(1).replace(".", "")), False
        except ValueError:
            return None, False
    return None, False


def nivel_de_vidros(cob: Mapping[str, Any]) -> Optional[int]:
    """0 sem · 1 só vidros/básico · 2 vidros + faróis/lanternas/retrovisores (ou "completo"). None = não informou."""
    texto = normalizar(cob.get("vidros"))
    if not texto:
        return None
    if texto.startswith("nao") or texto in ("false", "0"):
        return 0
    if any(p in texto for p in ("farol", "farois", "lantern", "retrovisor", "complet", "top", "plus")):
        return 2
    return 1


def _limpo(texto: Any) -> Optional[str]:
    """O rótulo da seguradora sem o código do sistema dela ("76 - Vidros…", "… (063)")."""
    if texto is None or isinstance(texto, bool):
        return None
    t = re.sub(r"^\s*\d+\s*-\s*", "", str(texto))
    t = re.sub(r"\s*\(\d+\)\s*$", "", t).strip().rstrip(".")
    return t or None


def _km(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def reais(v: Any) -> str:
    """R$ no formato do Brasil; sem ",00" quando o valor é inteiro."""
    f = round(float(v), 2)
    inteiro = abs(f - round(f)) < 0.005
    corpo = f"{abs(f):,.0f}" if inteiro else f"{abs(f):,.2f}"
    corpo = corpo.replace(",", "§").replace(".", ",").replace("§", ".")
    return ("-" if f < 0 else "") + "R$ " + corpo


def _mil(v: Any) -> Optional[str]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f <= 0:
        return None
    return f"R$ {f / 1000:g} mil".replace(".", ",") if f >= 1000 else reais(f)


def parcelas_de(oferta: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """A MAIOR quantidade de parcelas e, entre elas, o menor valor."""
    melhor = None
    for p in oferta.get("parcelamentos") or ():
        p = p if isinstance(p, Mapping) else getattr(p, "__dict__", {})
        try:
            vezes = int(p.get("parcelas"))
            valor = float(p.get("demais_parcelas") or p.get("primeira_parcela"))
        except (TypeError, ValueError):
            continue
        if vezes < 1 or valor <= 0:
            continue
        if melhor is None or (vezes, -valor) > (melhor["vezes"], -melhor["valor"]):
            melhor = {"vezes": vezes, "valor": round(valor, 2)}
    return melhor


def coberturas_publicas(oferta: Mapping[str, Any], *, ramo: int = RAMO_AUTO) -> List[Dict[str, str]]:
    """As linhas de cobertura para a página (CONTRATO §5). Ausente não aparece."""
    cob = _coberturas(oferta)
    linhas: List[Dict[str, str]] = []
    if int(ramo) != RAMO_AUTO:
        for k, v in cob.items():
            if k in _VOLATEIS or isinstance(v, (dict, list, bool)) or v in (None, ""):
                continue
            linhas.append({"chave": str(k), "nome": str(k), "valor": str(v)})
        return linhas
    if cob.get("casco") is not None and not isinstance(cob.get("casco"), bool):
        linhas.append({"chave": "casco", "nome": "Batida, roubo e incêndio", "valor": f"{float(cob['casco']):g}% da tabela FIPE"})
    m, c = _mil(cob.get("isDanosMateriais")), _mil(cob.get("isDanosCorporais"))
    if m and c:
        linhas.append({"chave": "terceiros", "nome": "Danos a outros carros e pessoas", "valor": f"{m} + {c}"})
    for chave, campo, nome in (("vidros", "vidros", "Vidros"), ("reserva", "carroReserva", "Carro reserva"),
                               ("assistencia", "assist24hs", "Guincho e assistência")):
        valor = _limpo(cob.get(campo))
        if valor:
            linhas.append({"chave": chave, "nome": nome, "valor": valor})
    app = _mil(cob.get("isAppMorte"))
    if app:
        linhas.append({"chave": "app", "nome": "Acidentes com passageiros", "valor": f"{app} por pessoa"})
    morais = _mil(cob.get("isDanosMorais"))
    if morais:
        linhas.append({"chave": "morais", "nome": "Danos morais", "valor": morais})
    return linhas


# ---------------------------------------------------------------------------------------------------------------------
# A COMPARAÇÃO
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Comparacao:
    ramo: int
    papeis: Dict[str, str]                                  # papel → opção da porta (config.calculo_por_papel)
    por_opcao: Dict[str, List[Dict[str, Any]]]              # opção → COMPLETAS, menor primeiro (1 por seg × corretora)
    diferentes_por_opcao: Dict[str, List[Dict[str, Any]]]
    nao_responderam_por_opcao: Dict[str, List[Dict[str, Any]]]
    entre_corretoras: List[Dict[str, Any]]
    resumo: Dict[str, Any]
    sem_opcao: int = 0
    corretoras: Tuple[str, ...] = ()

    @property
    def opcao_completa(self) -> str:
        return self.papeis.get("completa", "padrao")

    @property
    def vencedora(self) -> Optional[str]:
        return next((e["corretora_company_id"] for e in self.entre_corretoras if e.get("vencedora")), None)

    def ranking(self, opcao: Optional[str] = None, corretora: Optional[str] = None) -> List[Dict[str, Any]]:
        linhas = self.por_opcao.get(opcao or self.opcao_completa, [])
        return [dict(l) for l in linhas if corretora is None or l["corretora_company_id"] == corretora]

    @property
    def diferentes(self) -> List[Dict[str, Any]]:
        return [dict(d) for d in self.diferentes_por_opcao.get(self.opcao_completa, [])]

    @property
    def nao_responderam(self) -> List[Dict[str, Any]]:
        return [dict(d) for d in self.nao_responderam_por_opcao.get(self.opcao_completa, [])]


def _chave_seguradora(item: Mapping[str, Any]) -> str:
    cod = item.get("seguradora_codigo")
    if cod not in (None, "") and not isinstance(cod, bool):
        return f"cod:{cod}"
    return "nome:" + normalizar(item.get("seguradora"))


def _entrada(oferta: Mapping[str, Any], opcao: str, corretora: str, ramo: int) -> Dict[str, Any]:
    """A linha de ranking — campos ESCOLHIDOS um a um (a comissão nunca é copiada)."""
    cob = _coberturas(oferta)
    fv = oferta.get("franquia_valor")
    try:
        fv = float(fv) if fv is not None else None
    except (TypeError, ValueError):
        fv = None
    return {
        "oferta_id": str(oferta.get("id") or ""), "calculo_id": str(oferta.get("calculo_id") or ""),
        "corretora_company_id": corretora, "opcao": opcao, "ramo": ramo,
        "seguradora": nome_de_exibicao(oferta.get("seguradora")),
        "seguradora_original": str(oferta.get("seguradora") or "").strip(),
        "seguradora_codigo": oferta.get("seguradora_codigo"),
        "produto": str(oferta.get("pacote") or "").strip(),
        "premio_anual": round(float(oferta.get("premio_total")), 2),
        "franquia": {"valor": fv, "tipo": oferta.get("franquia_tipo")},
        "parcelas": parcelas_de(oferta),
        "tem_pdf_da_seguradora": bool(oferta.get("tem_pdf")),
        "coberturas_brutas": cob,
    }


def comparar(ofertas: Iterable[Mapping[str, Any]], eventos: Iterable[Mapping[str, Any]] = (), *,
             estados: Iterable[Mapping[str, Any]], config: Optional[Mapping[str, Any]] = None,
             ramo: int = RAMO_AUTO, corretoras_info: Optional[Mapping[str, Mapping[str, Any]]] = None,
             ordem_corretoras: Sequence[str] = ()) -> Comparacao:
    """O quadro inteiro, POR OPÇÃO. `estados` = `Andamento.estados` (calculo_id → corretora × opção).

    `corretoras_info` (desempate D-130A-04): {company_id: {"nota_google": float, "ordem_de_adesao": int}}.
    `ordem_corretoras`: a ordem do pedido (último critério antes do id)."""
    cfg = config or PADRAO_DO_PRODUTO
    ramo = int(ramo)
    papeis = dict(cfg.get("calculo_por_papel") or {"completa": "padrao"})
    por_calculo: Dict[str, Tuple[str, str]] = {}
    corretoras: List[str] = []
    for e in estados or ():
        cid = str(e.get("calculo_id") or e.get("id") or "")
        if not cid or not e.get("opcao"):
            continue
        corr = str(e.get("corretora_company_id") or e.get("company_id") or "")
        por_calculo[cid] = (str(e["opcao"]), corr)
        if corr and corr not in corretoras:
            corretoras.append(corr)

    agrupadas: Dict[str, List[Tuple[Mapping[str, Any], str]]] = {}
    sem_opcao = 0
    for o in ofertas or ():
        alvo = por_calculo.get(str(o.get("calculo_id") or ""))
        if alvo is None:
            sem_opcao += 1
            continue
        opcao, corr_estado = alvo
        corr = str(o.get("corretora_company_id") or o.get("company_id") or corr_estado)
        if corr_estado and corr != corr_estado:      # oferta com corretora trocada: não é deste cálculo
            sem_opcao += 1
            continue
        agrupadas.setdefault(opcao, []).append((o, corr))
        if corr not in corretoras:
            corretoras.append(corr)

    por_opcao: Dict[str, List[Dict[str, Any]]] = {}
    diferentes_por_opcao: Dict[str, List[Dict[str, Any]]] = {}
    responderam: Dict[str, set] = {}
    for opcao, itens in agrupadas.items():
        referencia = None
        if ramo not in REGRAS_POR_RAMO:
            contagem = Counter(assinatura_de_coberturas(o) for o, _ in itens if _premio(o) is not None)
            referencia = contagem.most_common(1)[0][0] if contagem else None
        melhores: Dict[Tuple[str, str], Dict[str, Any]] = {}
        difs: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        responderam[opcao] = set()
        for o, corr in itens:
            responderam[opcao].add(_chave_seguradora(o))
            classe = classificar(o, config=cfg, ramo=ramo, referencia=referencia)
            if classe.comparavel:
                ent = _entrada(o, opcao, corr, ramo)
                k = (corr, _chave_seguradora(o))
                if k not in melhores or ent["premio_anual"] < melhores[k]["premio_anual"]:
                    melhores[k] = ent
                continue
            seg = nome_de_exibicao(o.get("seguradora"))
            prod = str(o.get("pacote") or "").strip()
            k2 = (normalizar(seg), normalizar(prod), classe.chave)
            premio = _premio(o) if classe.exibe_preco else None
            d = difs.get(k2)
            if d is None:
                difs[k2] = {"seguradora": seg, "produto": prod, "motivo": classe.motivo, "chave_motivo": classe.chave,
                            "premio_anual": round(premio, 2) if premio else None, "corretoras": [corr]}
            else:
                if premio and (d["premio_anual"] is None or premio < d["premio_anual"]):
                    d["premio_anual"] = round(premio, 2)
                if corr not in d["corretoras"]:
                    d["corretoras"].append(corr)
        por_opcao[opcao] = sorted(melhores.values(), key=lambda e: (e["premio_anual"], e["seguradora"]))
        diferentes_por_opcao[opcao] = sorted(difs.values(), key=lambda d: (d["premio_anual"] is None,
                                                                           d["premio_anual"] or 0, d["seguradora"]))

    # quem NÃO respondeu, por opção: recusa/pendência de uma seguradora que NÃO tem oferta nenhuma nessa opção
    recusas: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for ev in eventos or ():
        familia = str(ev.get("familia") or "").upper()
        if ev.get("tipo") != SEGURADORA_RECUSOU and familia != PENDENTE:
            continue
        if not familia or familia == OFERTA:
            continue
        alvo = por_calculo.get(str(ev.get("calculo_id") or ""))
        if alvo is None:
            continue
        opcao = alvo[0]
        chave = _chave_seguradora(ev)
        if chave in responderam.get(opcao, set()):
            continue                                 # 📊 caso real: ofertou na opção e tem recusa noutro pacote
        atual = recusas.setdefault(opcao, {}).get(chave)
        prio = _PRIORIDADE_DA_FAMILIA.index(familia) if familia in _PRIORIDADE_DA_FAMILIA else len(_PRIORIDADE_DA_FAMILIA)
        if atual is None or prio < atual["_prio"]:
            recusas[opcao][chave] = {"seguradora": nome_de_exibicao(ev.get("seguradora")), "familia": familia,
                                     "motivo": FRASE_DA_FAMILIA.get(familia, FRASE_DA_FAMILIA[DESCONHECIDA]),
                                     "_prio": prio}
    nao_responderam_por_opcao = {
        op: sorted(({k: v for k, v in r.items() if k != "_prio"} for r in rs.values()), key=lambda r: r["seguradora"])
        for op, rs in recusas.items()}

    opcao_completa = papeis.get("completa", "padrao")
    entre = _entre_corretoras(por_opcao.get(opcao_completa, []), corretoras, cfg, corretoras_info or {},
                              list(ordem_corretoras or ()))

    ranking_c = por_opcao.get(opcao_completa, [])
    com_preco = {_chave_seguradora(e) for e in ranking_c}
    diferentes_seg = {_chave_seguradora({"seguradora": o.get("seguradora"), "seguradora_codigo": o.get("seguradora_codigo")})
                      for o, _ in agrupadas.get(opcao_completa, [])} - com_preco
    nao_resp = nao_responderam_por_opcao.get(opcao_completa, [])
    resumo = {"seguradoras_cotadas": len(com_preco) + len(diferentes_seg) + len(nao_resp),
              "com_preco_comparavel": len(com_preco), "com_produto_diferente": len(diferentes_seg),
              "nao_responderam": len(nao_resp)}
    if len(corretoras) > 1:
        resumo["corretoras_comparadas"] = len(corretoras)
    return Comparacao(ramo=ramo, papeis=papeis, por_opcao=por_opcao, diferentes_por_opcao=diferentes_por_opcao,
                      nao_responderam_por_opcao=nao_responderam_por_opcao, entre_corretoras=entre, resumo=resumo,
                      sem_opcao=sem_opcao, corretoras=tuple(corretoras))


def _entre_corretoras(ranking: List[Dict[str, Any]], corretoras: List[str], cfg: Mapping[str, Any],
                      info: Mapping[str, Mapping[str, Any]], ordem: List[str]) -> List[Dict[str, Any]]:
    """D-130A-04: a melhor COMPLETA de cada parceira; vencedora = a menor; empate pela regra da config."""
    melhor: Dict[str, Dict[str, Any]] = {}
    for e in ranking:
        c = e["corretora_company_id"]
        if c not in melhor or e["premio_anual"] < melhor[c]["premio_anual"]:
            melhor[c] = e
    criterios = list(cfg.get("desempate_entre_corretoras") or ())

    def chave_de_desempate(c: str) -> Tuple:
        partes: List[Any] = []
        dado = info.get(c) or {}
        for crit in criterios:
            v = dado.get(crit)
            if crit == "nota_google":                # maior nota primeiro; sem nota por último
                partes.append((v is None, -(float(v) if v is not None else 0.0)))
            else:                                    # ordem de adesão: menor primeiro; sem ordem por último
                partes.append((v is None, float(v) if v is not None else 0.0))
        partes.append(ordem.index(c) if c in ordem else len(ordem))
        partes.append(c)
        return tuple(partes)

    linhas = []
    for c in corretoras:
        e = melhor.get(c)
        linhas.append({"corretora_company_id": c, "melhor_completa": e["premio_anual"] if e else None,
                       "seguradora": e["seguradora"] if e else None, "oferta_id": e["oferta_id"] if e else None,
                       "vencedora": False})
    com_preco = [l for l in linhas if l["melhor_completa"] is not None]
    if com_preco:
        menor = min(l["melhor_completa"] for l in com_preco)
        empatadas = [l for l in com_preco if abs(l["melhor_completa"] - menor) < 0.005]
        sorted(empatadas, key=lambda l: chave_de_desempate(l["corretora_company_id"]))[0]["vencedora"] = True
    return sorted(linhas, key=lambda l: (l["melhor_completa"] is None, l["melhor_completa"] or 0,
                                         not l["vencedora"], l["corretora_company_id"]))


# ---------------------------------------------------------------------------------------------------------------------
# As OPÇÕES (D-MC-66/69 · D-130A-09)
# ---------------------------------------------------------------------------------------------------------------------
def _caracteristicas(e: Mapping[str, Any]) -> Dict[str, Any]:
    cob = e.get("coberturas_brutas") or {}
    km, ilimitado = guincho(cob)
    return {"reserva": dias_de_carro_reserva(cob), "km": km, "ilimitado": ilimitado, "vidros": nivel_de_vidros(cob)}


def _frac(v: Optional[float], lo: float, hi: float, menor_melhor: bool) -> float:
    if v is None:
        return 0.0
    if hi - lo < 1e-9:
        return 1.0
    x = (v - lo) / (hi - lo)
    return max(0.0, min(1.0, 1.0 - x if menor_melhor else x))


def nota_de(e: Mapping[str, Any], pool: Sequence[Mapping[str, Any]], config: Mapping[str, Any]) -> int:
    """Determinística, 0–100: preço e franquia (menor é melhor, relativo ao quadro) e coberturas (carro reserva,
    guincho, vidros, relativo ao melhor do quadro). Pesos na config; nunca acima de 100."""
    pesos = config["nota"]["pesos"]
    precos = [p["premio_anual"] for p in pool] or [e["premio_anual"]]
    franqs = [p["franquia"]["valor"] for p in pool if p["franquia"]["valor"] is not None]
    c_pre = _frac(e["premio_anual"], min(precos), max(precos), True)
    fv = e["franquia"]["valor"]
    c_fra = _frac(fv, min(franqs), max(franqs), True) if franqs and fv is not None else 0.0
    car = [_caracteristicas(p) for p in pool]
    meu = _caracteristicas(e)
    max_res = max([c["reserva"] or 0 for c in car] + [meu["reserva"] or 0])
    max_km = max([c["km"] or 0 for c in car] + [meu["km"] or 0])
    partes = [((meu["reserva"] or 0) / max_res) if max_res else 0.0,
              1.0 if meu["ilimitado"] else (((meu["km"] or 0) / max_km) if max_km else 0.0),
              ((meu["vidros"] or 0) / 2.0)]
    c_cob = sum(partes) / len(partes)
    total = float(pesos["preco"]) * c_pre + float(pesos["franquia"]) * c_fra + float(pesos["coberturas"]) * c_cob
    return int(max(0, min(100, round(total))))


def _motivos(e: Mapping[str, Any], papel: str, *, ranking_completa: Sequence[Mapping[str, Any]],
             referencia: Optional[Mapping[str, Any]], rotulo_ref: Optional[str], pool: Sequence[Mapping[str, Any]],
             apolice_atual: Optional[Mapping[str, Any]], ramo: int) -> List[str]:
    m: List[str] = []
    n = len(ranking_completa)
    if papel in ("completa", "igual") and n:
        pos = next((i for i, r in enumerate(ranking_completa, start=1) if r["oferta_id"] == e["oferta_id"]), None)
        if pos == 1:
            m.append(f"Menor preço entre as {n} seguradoras com cobertura completa" if n > 1
                     else "A única seguradora com cobertura completa que devolveu preço")
        elif pos:
            m.append(f"{pos}º menor preço entre as {n} seguradoras com cobertura completa")
    elif referencia is not None and rotulo_ref:
        dif = e["premio_anual"] - referencia["premio_anual"]
        if abs(dif) >= 0.01:
            m.append(f"{reais(abs(dif))} {'a menos' if dif < 0 else 'a mais'} por ano que a opção \"{rotulo_ref}\"")
    atual = (apolice_atual or {}).get("premio_anual")
    if atual:
        try:
            atual = float(atual)
            dif = e["premio_anual"] - atual
            if abs(dif) >= 0.01 and atual > 0:
                pct = abs(dif) / atual * 100
                m.append(f"{reais(abs(dif))} {'a menos' if dif < 0 else 'a mais'} que a sua apólice atual "
                         f"({pct:.0f} %)")
        except (TypeError, ValueError):
            pass
    fv = e["franquia"]["valor"]
    if fv is not None and fv > 0:
        franqs = [p["franquia"]["valor"] for p in pool if p["franquia"]["valor"]]
        if len(set(franqs)) > 1 and fv <= min(franqs) + 0.005:
            m.append(f"A menor franquia do quadro: {reais(fv)}")
        else:
            tipo = str(e["franquia"].get("tipo") or "").strip().lower()
            m.append(f"Franquia {tipo + ' ' if tipo else ''}de {reais(fv)}")
    car = _caracteristicas(e)
    if car["reserva"]:
        m.append(f"Carro reserva por {car['reserva']} dias")
    if car["ilimitado"]:
        m.append("Guincho sem limite de quilometragem")
    elif car["km"]:
        m.append(f"Guincho até {_km(car['km'])} km")
    p = e.get("parcelas")
    if p and p["vezes"] > 1:
        m.append(f"Em até {p['vezes']}x de {reais(p['valor'])}")
    m = m[:MAX_MOTIVOS]
    if len(m) < 2:
        m.append("Cobertura completa: batida, roubo, incêndio e danos a terceiros, 100 % da tabela FIPE"
                 if ramo == RAMO_AUTO else "Mesma configuração de coberturas das outras opções comparadas")
    return m


def _o_que_muda(e: Mapping[str, Any], ref: Optional[Mapping[str, Any]], rotulo_ref: Optional[str],
                papel: str = "") -> List[str]:
    """`papel == "minima"` (D-130A1-05): a mínima foi PEDIDA sem carro reserva. Se a seguradora não informou o carro
    reserva, "Sem carro reserva" é a leitura que cobre MENOS (nunca a que promete a mais); se ela DEU dias mesmo assim,
    vale o que ela devolveu."""
    if ref is None or ref["oferta_id"] == e["oferta_id"]:
        return []
    r = rotulo_ref or "recomendada"
    saida: List[str] = []
    dif = e["premio_anual"] - ref["premio_anual"]
    if abs(dif) >= 0.01:
        saida.append(f"{reais(abs(dif))} {'a menos' if dif < 0 else 'a mais'} por ano que a opção \"{r}\"")
    if e["seguradora"] != ref["seguradora"]:
        saida.append(f"Seguradora {e['seguradora']} (na opção \"{r}\": {ref['seguradora']})")
    fv, fr = e["franquia"]["valor"], ref["franquia"]["valor"]
    if fv is not None and fr is not None and abs(fv - fr) >= 0.01:
        saida.append(f"Franquia de {reais(fv)} ({reais(abs(fv - fr))} {'menor' if fv < fr else 'maior'})")
    ce, cr = _caracteristicas(e), _caracteristicas(ref)
    if ce["reserva"] is not None and cr["reserva"] is not None and ce["reserva"] != cr["reserva"]:
        saida.append("Sem carro reserva" if ce["reserva"] == 0
                     else f"Carro reserva por {ce['reserva']} dias (na opção \"{r}\": {cr['reserva']})")
    elif papel == "minima" and not ce["reserva"] and cr["reserva"] != 0:
        saida.append("Sem carro reserva")
    if ce["vidros"] is not None and cr["vidros"] is not None and ce["vidros"] != cr["vidros"]:
        texto = _limpo((e.get("coberturas_brutas") or {}).get("vidros")) or "não inclui"
        saida.append(f"Vidros: {texto}")
    if (ce["ilimitado"], ce["km"]) != (cr["ilimitado"], cr["km"]) and (ce["ilimitado"] or ce["km"]):
        saida.append("Guincho sem limite de quilometragem" if ce["ilimitado"] else f"Guincho até {_km(ce['km'])} km")
    return saida


def _opcao(e: Mapping[str, Any], id_: str, rotulo: str, papel: str, **ctx: Any) -> Dict[str, Any]:
    ramo = int(e.get("ramo") or RAMO_AUTO)
    ref, rotulo_ref = ctx["referencia"], ctx["rotulo_ref"]
    return {
        "id": id_, "rotulo": rotulo, "seguradora": e["seguradora"], "produto": e["produto"],
        "premio_anual": e["premio_anual"], "parcelas": e["parcelas"], "franquia": dict(e["franquia"]),
        "coberturas": coberturas_publicas({"coberturas": e.get("coberturas_brutas") or {}}, ramo=ramo),
        "nota": nota_de(e, ctx["pool"], ctx["config"]),
        "motivos": _motivos(e, papel, ranking_completa=ctx["ranking_completa"],
                            referencia=None if ref is None or ref["oferta_id"] == e["oferta_id"] else ref,
                            rotulo_ref=rotulo_ref, pool=ctx["pool"], apolice_atual=ctx["apolice_atual"], ramo=ramo),
        "o_que_muda": _o_que_muda(e, ref, rotulo_ref, papel),
        "tem_pdf_da_seguradora": e.get("tem_pdf_da_seguradora", False),
        "ref": {"oferta_id": e["oferta_id"], "calculo_id": e["calculo_id"],
                "corretora_company_id": e["corretora_company_id"], "opcao": e["opcao"]},
    }


def _repete(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """J-P4 (juiz, 06/10): a "Mais completa" que não acrescenta nada à referência — a MESMA seguradora com o mesmo
    prêmio (± R$ 1) ou com as mesmas coberturas devolvidas — não é uma opção, é a mesma repetida com outro rótulo."""
    if normalizar(a.get("seguradora")) != normalizar(b.get("seguradora")):
        return False
    if abs(float(a["premio_anual"]) - float(b["premio_anual"])) < 1.0:
        return True
    return (assinatura_de_coberturas({"coberturas": a.get("coberturas_brutas") or {}})
            == assinatura_de_coberturas({"coberturas": b.get("coberturas_brutas") or {}}))


def precisa_de_apolice(situacao: str) -> bool:
    return situacao in ("novo_com_apolice", "renovacao")


def conferir_apolice(situacao: str, apolice_atual: Optional[Mapping[str, Any]]) -> None:
    """J-B2 (juiz, 06/10): com apólice / renovação SEM a apólice atual, a página rotularia "Igual à sua atual" ou "Sua
    renovação" uma seguradora que não é a do cliente. Recusa com o motivo — nunca um rótulo inventado."""
    if not precisa_de_apolice(situacao):
        return
    seg = str((apolice_atual or {}).get("seguradora") or "").strip() if isinstance(apolice_atual, Mapping) else ""
    if not seg:
        raise ValueError(f"a situação {situacao!r} precisa da apólice atual do cliente (ao menos a seguradora): sem "
                         "ela a página chamaria de \"igual à sua atual\" uma seguradora que não é a dele")


def opcoes(comparacao: Comparacao, *, situacao: str, apolice_atual: Optional[Mapping[str, Any]] = None,
           config: Optional[Mapping[str, Any]] = None, corretora: Optional[str] = None,
           incluir_minima: bool = False) -> List[Dict[str, Any]]:
    """As opções da proposta (D-130A-09), na ordem em que aparecem (as 2 primeiras vão ao WhatsApp, D-MC-74):

    sem apólice  → Recomendada (menor completa) · Mais em conta (menor econômica, se MAIS BARATA) · Mais completa
                   (se houver cálculo `completa_mais` que acrescente algo) — senão "Menor franquia" (se a menor
                   franquia do quadro é de OUTRA seguradora) ou "Outra completa" (2ª menor completa)
    com apólice  → a seguradora da apólice É a menor completa: "Igual à sua atual" ("Sua renovação") em 1º · Mais em
    / renovação    conta · Mais completa (senão a "Outra completa"/"Menor franquia")
                   não é: Recomendada (a menor completa) em 1º · "Igual à sua atual" · Mais em conta (senão Mais completa)
                   a seguradora da apólice não está no quadro: como sem apólice (nenhum "igual" inventado)

    🔴 A 1ª opção é SEMPRE a menor completa (RT-B1, red team 06/10): é ela que a página chama de "a melhor das N" e a
    mensagem leva primeiro. A seguradora da apólice entra como "igual", na posição VERDADEIRA dela no ranking.
    `apolice_atual` obrigatória com apólice/renovação (J-B2: `ValueError`).
    `corretora`: de quem são as ofertas (padrão: a VENCEDORA — a anfitriã fecha o que mostra).
    `incluir_minima` (SPEC-130-A.1 D-130A1-05, só o canal): a "Mais em conta" pode vir do cálculo `minima` (o mínimo do
    mínimo) quando ele é mais barato — sempre dizendo o que deixa de cobrir; nunca é a 1ª opção."""
    if situacao not in SITUACOES:
        raise ValueError(f"situação desconhecida: {situacao!r} (aceitas: {', '.join(SITUACOES)})")
    conferir_apolice(situacao, apolice_atual)
    cfg = config or PADRAO_DO_PRODUTO
    papeis = comparacao.papeis
    dona = corretora or comparacao.vencedora
    if dona is None:
        return []
    C = comparacao.ranking(papeis.get("completa", "padrao"), dona)
    E = comparacao.ranking(papeis.get("economica", "economica"), dona)
    M = comparacao.ranking(papeis.get("completa_mais", "completa_mais"), dona)
    # a mínima (D-130A1-05) só existe para quem a PEDE: sem `incluir_minima`, o cálculo dela nem entra no pool da nota
    Mn = comparacao.ranking(papeis.get("minima", "minima"), dona) if incluir_minima else []
    if not C:
        return []
    pool = C + E + M + Mn
    escolhidas: List[Tuple[Dict[str, Any], str, str, str]] = []   # (entrada, id, rótulo, papel)

    def terceira_completa(excluir: Iterable[str]) -> Optional[Tuple[Dict[str, Any], str, str, str]]:
        fora = set(excluir)
        resto = [c for c in C if c["oferta_id"] not in fora]
        if not resto:
            return None
        com_franquia = [c for c in C if c["franquia"]["valor"] is not None]
        if com_franquia:
            menor = min(com_franquia, key=lambda c: (c["franquia"]["valor"], c["premio_anual"]))
            if menor["oferta_id"] not in fora and menor["seguradora"] != C[0]["seguradora"]:
                return (menor, "menor_franquia", "Menor franquia", "completa")
        return (resto[0], "outra_completa", "Outra completa", "completa")

    melhor = C[0]                                               # a menor completa: a 1ª opção, sempre
    igual = None
    if precisa_de_apolice(situacao):
        atual_seg = str(apolice_atual["seguradora"]).strip()
        # só a MESMA seguradora vira "igual" — se ela não está no quadro, não existe opção "igual" (J-B2/P4b)
        igual = next((c for c in C if casa_seguradora(c["seguradora_original"], [atual_seg])
                      or casa_seguradora(c["seguradora"], [atual_seg])
                      or casa_seguradora(atual_seg, [c["seguradora_original"]])
                      or casa_seguradora(atual_seg, [c["seguradora"]])), None)
    id_igual, rot_igual = (("sua_renovacao", "Sua renovação") if situacao == "renovacao"
                           else ("igual_a_atual", "Igual à sua atual"))
    if igual is not None and igual["oferta_id"] == melhor["oferta_id"]:
        escolhidas.append((melhor, id_igual, rot_igual, "igual"))   # a seguradora dele JÁ é a menor completa
    else:
        escolhidas.append((melhor, "recomendada", "Recomendada", "completa"))
        if igual is not None:
            escolhidas.append((igual, id_igual, rot_igual, "igual"))
    # "Mais em conta" = a MAIS BARATA entre a menor econômica e a menor mínima (empate: a econômica, que cobre mais),
    # se for mais barata que a 1ª. 🔴 G7: a mínima nunca é a 1ª (a 1ª já foi escolhida, de C) nem entra em C
    candidatas = [(x, papel) for x, papel in ((E[0] if E else None, "economica"), (Mn[0] if Mn else None, "minima"))
                  if x is not None]
    if candidatas:
        barata, papel_barata = min(candidatas, key=lambda xp: xp[0]["premio_anual"])
        if barata["premio_anual"] < melhor["premio_anual"]:
            escolhidas.append((barata, "mais_em_conta", "Mais em conta", papel_barata))
    if M and not _repete(M[0], melhor):
        escolhidas.append((M[0], "mais_completa", "Mais completa", "completa_mais"))
    t = terceira_completa([e[0]["oferta_id"] for e in escolhidas])
    if t:
        escolhidas.append(t)

    vistos: set = set()
    unicas = []
    for item in escolhidas:
        if item[0]["oferta_id"] in vistos:
            continue
        vistos.add(item[0]["oferta_id"])
        unicas.append(item)
    unicas = unicas[: int(cfg["opcoes"]["na_pagina"])]
    ref, rotulo_ref = unicas[0][0], unicas[0][2]
    ctx = {"referencia": ref, "rotulo_ref": rotulo_ref, "pool": pool, "config": cfg, "ranking_completa": C,
           "apolice_atual": apolice_atual}
    return [_opcao(e, id_, rot, papel, **ctx) for e, id_, rot, papel in unicas]
