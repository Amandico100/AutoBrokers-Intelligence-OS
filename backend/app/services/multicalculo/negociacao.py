# -*- coding: utf-8 -*-
"""A NEGOCIAÇÃO do multicálculo, PURA — SPEC-130-A U3 (D-MC-63/67/68/72).

A porta (`porta.ordem_do_mais_barato`, `porta.cotacao_alvo`, `porta.avaliar_cotacao_alvo`) autoriza, lê e
ENFILEIRA; aqui só se DECIDE, sem I/O:

    ordem_do_mais_barato(oferta, config)   os passos na ordem D-MC-67 que ESTA seguradora obedece
    planejar(ofertas, alvo, config)         a 1ª etapa: tentativas de UM passo a partir do cálculo de origem
    escolher(resultados, alvo, config)      chegou no alvo? → a de MAIOR comissão (margem antes de cobertura)
    proxima_etapa(resultados, ...)          não chegou → o próximo passo ENCADEADO sobre o melhor parcial

🔴 A regra da margem (D-MC-68 revendo a D-MC-63): até `comissao.autonomo_minimo` o agente aplica SOZINHO; o
`comissao.piso` só com `concorrencia_declarada` E `aprovado_pelo_corretor` (D-MC-67); NUNCA abaixo do piso.
🔴 Nas seguradoras que obedecem o desconto e ignoram a comissão (config `seguradoras_que_obedecem_desconto` —
📊 Porto, Azul, Itaú, 128 E5) o botão da margem é o DESCONTO = entrada − nível: "comissão e desconto como UMA
regra" (D-MC-63).
🔴 Cobertura só cai DEPOIS da margem e todo corte é LISTADO (o cliente ouve "o que mudou").
Cada tentativa = 1 recálculo da corretora inteira (📊 ~30–50 s, E7): o plano é curto e tem teto na config.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from portal_worker.multicalculo.contrato import RAMO_AUTO, Ajuste

from app.services.multicalculo.comparacao import classificar, dias_de_carro_reserva, nivel_de_vidros, nome_de_exibicao
from app.services.multicalculo.config import PADRAO_DO_PRODUTO, casa_seguradora, normalizar

CUSTO_POR_TENTATIVA = "1 recálculo da corretora inteira por tentativa"
STATUS_PENDENTES = ("na_fila", "disparando", "calculando")
ALAVANCAS_DE_MARGEM = ("desconto", "comissao")
_DESCRICAO = {"franquia": "franquia {v}", "carro_reserva": "carro reserva {v}", "vidros": "vidros {v}",
              "assistencia": "assistência {v}"}


@dataclass(frozen=True)
class Passo:
    alavanca: str                       # desconto · comissao · franquia · carro_reserva · vidros · assistencia
    ajuste: Ajuste
    comissao_resultante: Optional[float]
    corta_cobertura: bool
    precisa_aprovacao: bool
    descricao: str

    @property
    def id(self) -> str:
        return f"{self.alavanca}:{self.ajuste.valor}"

    def para_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "alavanca": self.alavanca,
                "ajuste": {"tipo": self.ajuste.tipo, "valor": self.ajuste.valor, "seguradora": self.ajuste.seguradora},
                "comissao_resultante": self.comissao_resultante, "corta_cobertura": self.corta_cobertura,
                "precisa_aprovacao": self.precisa_aprovacao, "descricao": self.descricao}


def _pct(v: float) -> str:
    return (f"{v:g}" if float(v).is_integer() else f"{v:.1f}".replace(".", ",")) + " %"


def _codigo(oferta: Mapping[str, Any]) -> Optional[int]:
    cod = oferta.get("seguradora_codigo")
    if cod is None or isinstance(cod, bool):
        return None
    try:
        return int(cod)
    except (TypeError, ValueError):
        return None


def _comissao_atual(oferta: Mapping[str, Any], cfg: Mapping[str, Any]) -> float:
    v = oferta.get("comissao_percentual")
    try:
        return float(v) if v is not None else float(cfg["comissao"]["entrada"])
    except (TypeError, ValueError):
        return float(cfg["comissao"]["entrada"])


def obedece_desconto(seguradora: Any, config: Mapping[str, Any]) -> bool:
    return casa_seguradora(seguradora, config.get("seguradoras_que_obedecem_desconto") or ())


def ordem_do_mais_barato(oferta: Mapping[str, Any], *, config: Optional[Mapping[str, Any]] = None,
                         concorrencia_declarada: bool = False) -> List[Passo]:
    """Os passos de UMA oferta, na ordem da config (D-MC-67), que a seguradora DELA obedece. Sem código de
    seguradora → nenhum passo (um ajuste sem seguradora mudaria TODAS as ofertas)."""
    cfg = config or PADRAO_DO_PRODUTO
    cod = _codigo(oferta)
    if cod is None:
        return []
    com = cfg["comissao"]
    entrada, autonomo, piso = float(com["entrada"]), float(com["autonomo_minimo"]), float(com["piso"])
    atual = _comissao_atual(oferta, cfg)
    niveis = [n for n in ([autonomo] + ([piso] if concorrencia_declarada else [])) if piso <= n < atual]
    por_desconto = obedece_desconto(oferta.get("seguradora"), cfg)
    cob = oferta.get("coberturas") if isinstance(oferta.get("coberturas"), Mapping) else {}
    cortes = cfg.get("cortes_de_cobertura") or {}
    passos: List[Passo] = []
    for alavanca in cfg.get("ordem_do_mais_barato") or ():
        if alavanca == "desconto":
            if por_desconto:              # a margem DESTA seguradora é o desconto (D-MC-63)
                for n in niveis:
                    valor = round(entrada - n, 2)
                    if valor <= 0:
                        continue
                    passos.append(Passo("desconto", Ajuste(tipo="desconto", valor=valor, seguradora=cod), n, False,
                                        n < autonomo, f"desconto de {_pct(valor)} (a margem da corretora fica em "
                                                      f"{_pct(n)})"))
            else:
                tabela = {normalizar(k): v for k, v in (cfg.get("desconto_permitido_pct") or {}).items()}
                lib = tabela.get(normalizar(oferta.get("seguradora")))
                if isinstance(lib, (int, float)) and not isinstance(lib, bool) and lib > 0:
                    passos.append(Passo("desconto", Ajuste(tipo="desconto", valor=float(lib), seguradora=cod), atual,
                                        False, False, f"desconto de {_pct(float(lib))} que a seguradora libera"))
        elif alavanca == "comissao":
            if por_desconto:
                continue                  # a seguradora ignora a comissão: o passo já saiu como desconto
            for n in niveis:
                passos.append(Passo("comissao", Ajuste(tipo="comissao", valor=n, seguradora=cod), n, False,
                                    n < autonomo, f"comissão da corretora de {_pct(atual)} para {_pct(n)}"))
        elif alavanca in _DESCRICAO and cortes.get(alavanca):
            alvo = cortes[alavanca]
            if not _ja_esta_no_corte(alavanca, alvo, oferta, cob):
                passos.append(Passo(alavanca, Ajuste(tipo=alavanca, valor=alvo, seguradora=cod), atual, True, False,
                                    _DESCRICAO[alavanca].format(v=alvo)))
    return passos


def _ja_esta_no_corte(alavanca: str, alvo: Any, oferta: Mapping[str, Any], cob: Mapping[str, Any]) -> bool:
    if alavanca == "franquia":
        return normalizar(oferta.get("franquia_tipo")) == normalizar(alvo)
    if alavanca == "carro_reserva":
        dias = dias_de_carro_reserva(cob)
        m = re.search(r"\d+", str(alvo))
        return dias is not None and m is not None and dias <= int(m.group(0))
    if alavanca == "vidros":
        nivel = nivel_de_vidros(cob)
        return nivel is not None and nivel <= 1
    if alavanca == "assistencia":
        return "basic" in normalizar(cob.get("assist24hs"))
    return False


# ---------------------------------------------------------------------------------------------------------------------
def _tentativa(oferta: Mapping[str, Any], passo: Passo, passos_antes: Sequence[str]) -> Dict[str, Any]:
    return {"origem_calculo_id": str(oferta.get("calculo_id") or ""), "oferta_de_origem_id": str(oferta.get("id") or ""),
            "seguradora": nome_de_exibicao(oferta.get("seguradora")), "seguradora_codigo": _codigo(oferta),
            "premio_de_origem": float(oferta.get("premio_total") or 0), "pacote_de_origem": oferta.get("pacote"),
            "passos": list(passos_antes) + [passo.id],
            "passo": passo.para_dict(), "ajuste": passo.ajuste,
            "comissao_resultante": passo.comissao_resultante,
            "corta_cobertura": _cortes_acumulados(list(passos_antes) + [passo.id]),
            "precisa_aprovacao": passo.precisa_aprovacao}


def _cortes_acumulados(passos: Sequence[str]) -> List[str]:
    return [p.split(":", 1)[0] for p in passos if p.split(":", 1)[0] not in ALAVANCAS_DE_MARGEM]


def _separar(tentativas: List[Dict[str, Any]], cfg: Mapping[str, Any], aprovado: bool) -> Dict[str, Any]:
    teto = int(cfg["negociacao"]["max_tentativas_por_etapa"])
    permitidas = [t for t in tentativas if aprovado or not t["precisa_aprovacao"]]
    aguardam = [t for t in tentativas if t["precisa_aprovacao"] and not aprovado]
    return {"tentativas": permitidas[:teto], "precisa_aprovacao": aguardam,
            "fora_do_teto": max(0, len(permitidas) - teto)}


def planejar(ofertas: Iterable[Mapping[str, Any]], *, alvo: float, config: Optional[Mapping[str, Any]] = None,
             seguradora: Any = None, concorrencia_declarada: bool = False,
             aprovado_pelo_corretor: bool = False) -> Dict[str, Any]:
    """A 1ª ETAPA da cotação-alvo. `ofertas` = as COMPLETAS da corretora DONA (com `calculo_id` e a comissão).
    Tentativas de UM passo a partir do cálculo de origem, passo a passo na ordem D-MC-67 entre as seguradoras mais
    baratas (teto `negociacao.max_seguradoras`/`max_tentativas_por_etapa`)."""
    cfg = config or PADRAO_DO_PRODUTO
    alvo = float(alvo)
    if alvo <= 0:
        raise ValueError("alvo precisa ser um valor positivo")
    lista = [o for o in ofertas if float(o.get("premio_total") or 0) > 0]
    if seguradora is not None:
        lista = [o for o in lista if _codigo(o) == seguradora or (isinstance(seguradora, str) and (
            casa_seguradora(o.get("seguradora"), [seguradora]) or casa_seguradora(nome_de_exibicao(o.get("seguradora")),
                                                                                [seguradora])))]
    if not lista:
        return {"status": "sem_oferta", "tentativas": [], "precisa_aprovacao": []}
    no_alvo = [o for o in lista if float(o["premio_total"]) <= alvo]
    if no_alvo:
        melhor = max(no_alvo, key=lambda o: (_comissao_atual(o, cfg), -float(o["premio_total"])))
        return {"status": "ja_no_alvo", "oferta_id": str(melhor.get("id") or ""),
                "seguradora": nome_de_exibicao(melhor.get("seguradora")), "premio_anual": float(melhor["premio_total"]),
                "tentativas": [], "precisa_aprovacao": []}
    candidatas = sorted(lista, key=lambda o: float(o["premio_total"]))[: int(cfg["negociacao"]["max_seguradoras"])]
    por_candidata = [(o, ordem_do_mais_barato(o, config=cfg, concorrencia_declarada=concorrencia_declarada))
                     for o in candidatas]
    tentativas: List[Dict[str, Any]] = []
    profundidade = max((len(p) for _, p in por_candidata), default=0)
    for i in range(profundidade):                      # passo-a-passo: o 1º passo de todas antes do 2º de qualquer
        for o, passos in por_candidata:
            if i < len(passos):
                tentativas.append(_tentativa(o, passos[i], []))
    if not tentativas:
        return {"status": "sem_caminho", "tentativas": [], "precisa_aprovacao": [],
                "recomendacao": "nenhum ajuste permitido nestas seguradoras"}
    return {"status": "planejado", **_separar(tentativas, cfg, aprovado_pelo_corretor)}


def escolher(resultados: Iterable[Mapping[str, Any]], *, alvo: float,
             config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """`resultados` = cada tentativa com a `oferta` que voltou (ou None). Chegou → entre as SEM corte, a de MAIOR
    comissão; só com corte → a de maior comissão com menos cortes, os cortes listados e a recomendação."""
    cfg = config or PADRAO_DO_PRODUTO
    alvo = float(alvo)
    validos = [r for r in resultados if r.get("oferta") and float(r["oferta"].get("premio_total") or 0) > 0]
    if not validos:
        return {"status": "nao_chegou", "melhor_parcial": None}
    chegaram = [r for r in validos if float(r["oferta"]["premio_total"]) <= alvo]

    def comissao(r: Mapping[str, Any]) -> float:
        # a do PASSO primeiro: nas que obedecem o desconto a oferta ainda diz a comissão que a seguradora ignora
        v = r.get("comissao_resultante")
        if v is None:
            v = r["oferta"].get("comissao_percentual")
        return float(v) if v is not None else float(cfg["comissao"]["entrada"])

    def cortes(r: Mapping[str, Any]) -> List[str]:
        return _cortes_acumulados(r.get("passos") or ())

    if chegaram:
        sem_corte = [r for r in chegaram if not cortes(r)]
        pool = sem_corte or chegaram
        r = max(pool, key=lambda x: (comissao(x), -len(cortes(x)), -float(x["oferta"]["premio_total"])))
        cs = cortes(r)
        recomendaveis = set(cfg["negociacao"].get("cortes_recomendaveis") or ())
        recomenda = not cs or (len(cs) == 1 and cs[0] in recomendaveis)
        return {"status": "chegou", "recomenda": recomenda, "corta_cobertura": cs,
                "escolhida": _resumo(r, comissao(r)),
                "recomendacao": ("chega no alvo sem mexer na cobertura" if not cs else
                                 ("chega no alvo mudando: " + ", ".join(cs) + (" — recomendo" if recomenda
                                                                               else " — NÃO recomendo")))}
    melhor = min(validos, key=lambda x: float(x["oferta"]["premio_total"]))
    return {"status": "nao_chegou", "melhor_parcial": _resumo(melhor, comissao(melhor))}


def _resumo(r: Mapping[str, Any], comissao: float) -> Dict[str, Any]:
    o = r["oferta"]
    return {"calculo_id": r.get("calculo_id"), "oferta_id": str(o.get("id") or ""),
            "seguradora": nome_de_exibicao(o.get("seguradora")), "seguradora_codigo": _codigo(o),
            "premio_anual": round(float(o["premio_total"]), 2), "comissao_percentual": comissao,
            "passos": list(r.get("passos") or ()), "corta_cobertura": _cortes_acumulados(r.get("passos") or ()),
            "_oferta": o}


def proxima_etapa(resultados: Iterable[Mapping[str, Any]], *, alvo: float, config: Optional[Mapping[str, Any]] = None,
                  concorrencia_declarada: bool = False, aprovado_pelo_corretor: bool = False) -> Dict[str, Any]:
    """Não chegou: os passos que FALTAM, encadeados sobre o MELHOR parcial (o novo cálculo de origem é o dele).
    Sem passo restante → "não recomendo" com o melhor parcial."""
    cfg = config or PADRAO_DO_PRODUTO
    decisao = escolher(resultados, alvo=alvo, config=cfg)
    if decisao["status"] == "chegou":
        return {"status": "chegou", **{k: v for k, v in decisao.items() if k != "status"}}
    parcial = decisao.get("melhor_parcial")
    if not parcial:
        return {"status": "sem_caminho", "tentativas": [], "precisa_aprovacao": [],
                "recomendacao": "nenhuma tentativa devolveu preço"}
    oferta = dict(parcial["_oferta"])
    oferta["calculo_id"] = parcial["calculo_id"]
    # a margem JÁ atingida pelo parcial: os níveis iguais ou acima dela não voltam (nem como desconto)
    oferta["comissao_percentual"] = parcial["comissao_percentual"]
    feitos = list(parcial["passos"])
    restantes = [p for p in ordem_do_mais_barato(oferta, config=cfg, concorrencia_declarada=concorrencia_declarada)
                 if p.id not in feitos]
    if not restantes:
        return {"status": "sem_caminho", "tentativas": [], "precisa_aprovacao": [],
                "melhor_parcial": {k: v for k, v in parcial.items() if k != "_oferta"},
                "recomendacao": "não recomendo: nem com todos os ajustes permitidos chega no alvo"}
    tentativas = [_tentativa(oferta, p, feitos) for p in restantes]
    return {"status": "proxima_etapa", "melhor_parcial": {k: v for k, v in parcial.items() if k != "_oferta"},
            **_separar(tentativas, cfg, aprovado_pelo_corretor)}


def resultado_da_tentativa(tentativa: Mapping[str, Any], ofertas: Iterable[Mapping[str, Any]], *,
                           company_id: str, config: Optional[Mapping[str, Any]] = None,
                           ramo: int = RAMO_AUTO) -> Optional[Dict[str, Any]]:
    """A oferta COMPLETA que o recálculo de uma tentativa devolveu para a seguradora DELA, na corretora dona.
    🔴 Só completa: a mesma seguradora devolve pacotes sem batida (ex. "Auto Roubo") mais baratos — contar um
    deles como "chegou no alvo" venderia outro produto. O mesmo pacote da origem vence; senão a menor completa."""
    cfg = config or PADRAO_DO_PRODUTO
    cod = tentativa.get("seguradora_codigo")
    achadas = [o for o in ofertas if str(o.get("calculo_id")) == str(tentativa.get("calculo_id"))
               and _codigo(o) == cod and str(o.get("corretora_company_id") or o.get("company_id")) == company_id
               and classificar(o, config=cfg, ramo=ramo).comparavel]
    if not achadas:
        return None
    mesmo = [o for o in achadas if normalizar(o.get("pacote")) == normalizar(tentativa.get("pacote_de_origem"))]
    return min(mesmo or achadas, key=lambda o: float(o["premio_total"]))
