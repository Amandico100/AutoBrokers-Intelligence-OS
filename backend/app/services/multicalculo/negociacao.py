# -*- coding: utf-8 -*-
"""A NEGOCIAÇÃO do multicálculo, PURA — SPEC-130-A U3 (D-MC-63/67/72) · SPEC-130-A.1 U1 (D-MC-68 CORRIGIDA).

A porta (`porta.ordem_do_mais_barato`, `porta.cotacao_alvo`, `porta.avaliar_cotacao_alvo`) autoriza, lê e
ENFILEIRA; aqui só se DECIDE, sem I/O:

    ordem_do_mais_barato(oferta, config)   os passos na ordem D-MC-67 que ESTA seguradora obedece
    planejar(ofertas, alvo, config)         a 1ª etapa: tentativas de UM passo a partir do cálculo de origem
    escolher(resultados, alvo, config)      chegou no alvo? → a de MAIOR comissão (margem antes de cobertura)
    proxima_etapa(resultados, ...)          não chegou → o próximo passo ENCADEADO sobre o melhor parcial
    texto_da_alavanca(antes, depois, voz)   a frase da alavanca de fechamento, em REAIS

🔴 A régua da margem — D-MC-68 CORRIGIDA (Founder, 06/10 23h: "o agente PODE ir até o piso SEM autorização humana,
mas não direto — aos poucos; e usar os últimos pontos como alavanca de fechamento"). A versão anterior ("o piso só com
concorrência declarada E o corretor aprovando") estava ERRADA e saiu. (Os números ficam na config — o guarda G8.)
  · a comissão desce de `comissao.passo_pp` em `passo_pp` a partir da comissão ATUAL da oferta (um ponto por vez com
    o padrão), NUNCA pulando direto; o último degrau de cada trecho cai exatamente no limite dele (nunca o atravessa);
  · `entrada` → `autonomo_minimo` = a negociação NORMAL: sempre no plano;
  · `autonomo_minimo` → `piso` = a ALAVANCA DE FECHAMENTO: os degraus existem, NÃO pedem aprovação humana nem
    concorrência declarada, mas só entram no plano quando o chamador pede o fechamento (`fechamento=True` — o cliente
    sinalizou que fecha se melhorar). Ao cliente ela sai em REAIS (`texto_da_alavanca`), nunca em "%";
  · NUNCA abaixo do `piso` da corretora (a config dela pode ter um piso maior que o do produto).
🔴 Nas seguradoras que obedecem o desconto e ignoram a comissão (config `seguradoras_que_obedecem_desconto` —
📊 Porto, Azul, Itaú, 128 E5) o botão da margem é o DESCONTO = entrada − nível, com os MESMOS degraus: "comissão e
desconto como UMA regra" (D-MC-63).
🔴 A ORDEM fechamento × cortes de cobertura (decisão desta fatia): com `fechamento=True`, os degraus da alavanca vêm
LOGO DEPOIS dos degraus normais, ANTES de qualquer corte de cobertura. Porquê: o Founder quer o fechamento como a
ÚLTIMA cartada para fechar SEM tirar cobertura — "última" é no TEMPO da conversa (ela só existe quando o cliente
sinaliza que fecha; até lá o plano só tem a margem normal e os cortes), não na fila do plano; e D-MC-67 manda gastar
margem antes de cobertura. Pôr a alavanca depois dos cortes faria o cliente que já ia fechar perder carro reserva ou
vidros para a corretora guardar uns pontos de margem — o oposto do que ela existe para fazer.
🔴 Cobertura só cai DEPOIS da margem e todo corte é LISTADO (o cliente ouve "o que mudou").
Cada tentativa = 1 recálculo da corretora inteira (📊 ~30–50 s, E7): o plano é curto e tem teto na config; os degraus
menores entram primeiro, e `escolher` fica com a MAIOR comissão que chega — a corretora nunca cede mais que o preciso.
"""
from __future__ import annotations

import math
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
_EPS = 1e-9

#: A frase da alavanca de fechamento (D-MC-68 corrigida). 🔴 Em REAIS, condicionada ao fechamento, sem "%", sem
#: "comissão", sem urgência falsa. `{diferenca}` e `{preco}` vêm do RECÁLCULO (`texto_da_alavanca`), nunca de conta.
FRASE_DA_ALAVANCA = ("Falei com a seguradora e consegui {diferenca} a menos no ano (fica {preco} por ano). "
                     "Vale se você fechar {com_quem}.")
#: quem fala: a corretora com o cliente dela (carteira) ou o canal comparador com o consumidor (D-130A1-07)
COM_QUEM = {"corretora": "comigo", "canal": "com a corretora"}


@dataclass(frozen=True)
class Passo:
    alavanca: str                       # desconto · comissao · franquia · carro_reserva · vidros · assistencia
    ajuste: Ajuste
    comissao_resultante: Optional[float]
    corta_cobertura: bool
    fechamento: bool                    # degrau da ALAVANCA DE FECHAMENTO (abaixo de `autonomo_minimo`)
    descricao: str

    @property
    def id(self) -> str:
        return f"{self.alavanca}:{self.ajuste.valor}"

    def para_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "alavanca": self.alavanca,
                "ajuste": {"tipo": self.ajuste.tipo, "valor": self.ajuste.valor, "seguradora": self.ajuste.seguradora},
                "comissao_resultante": self.comissao_resultante, "corta_cobertura": self.corta_cobertura,
                "fechamento": self.fechamento, "descricao": self.descricao}


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


def degraus(de: float, ate: float, passo: float) -> List[float]:
    """Os níveis estritamente abaixo de `de`, descendo de `passo` em `passo`, até `ate` INCLUSIVE. O último degrau cai
    exatamente em `ate` (nunca o atravessa); nenhum degrau é maior que `passo`. `de <= ate` → nenhum."""
    de, ate, passo = float(de), float(ate), float(passo)
    if passo <= 0:
        raise ValueError("passo precisa ser positivo")
    saida: List[float] = []
    n = de
    while n - ate > _EPS:
        n = max(round(n - passo, 2), ate)
        saida.append(n)
    return saida


def niveis_de_margem(atual: float, cfg: Mapping[str, Any]) -> List[tuple]:
    """[(nível, é_fechamento)] a partir da comissão `atual`: os degraus normais até `autonomo_minimo` e, depois, os da
    alavanca de fechamento até o `piso`. Quem decide se os de fechamento entram é o chamador."""
    com = cfg["comissao"]
    autonomo, piso, passo = float(com["autonomo_minimo"]), float(com["piso"]), float(com["passo_pp"])
    normais = degraus(atual, autonomo, passo)
    fech = degraus(min(float(atual), autonomo), piso, passo)
    return [(n, False) for n in normais] + [(n, True) for n in fech]


def ordem_do_mais_barato(oferta: Mapping[str, Any], *, config: Optional[Mapping[str, Any]] = None,
                         fechamento: bool = False) -> List[Passo]:
    """Os passos de UMA oferta, na ordem da config (D-MC-67), que a seguradora DELA obedece. Sem código de
    seguradora → nenhum passo (um ajuste sem seguradora mudaria TODAS as ofertas).
    `fechamento=True` acrescenta os degraus da alavanca de fechamento logo depois dos normais (antes dos cortes)."""
    cfg = config or PADRAO_DO_PRODUTO
    cod = _codigo(oferta)
    if cod is None:
        return []
    entrada = float(cfg["comissao"]["entrada"])
    atual = _comissao_atual(oferta, cfg)
    niveis = [(n, f) for n, f in niveis_de_margem(atual, cfg) if fechamento or not f]
    por_desconto = obedece_desconto(oferta.get("seguradora"), cfg)
    cob = oferta.get("coberturas") if isinstance(oferta.get("coberturas"), Mapping) else {}
    cortes = cfg.get("cortes_de_cobertura") or {}
    passos: List[Passo] = []
    for alavanca in cfg.get("ordem_do_mais_barato") or ():
        if alavanca == "desconto":
            if por_desconto:              # a margem DESTA seguradora é o desconto (D-MC-63)
                for n, fech in niveis:
                    valor = round(entrada - n, 2)
                    if valor <= 0:
                        continue
                    passos.append(Passo("desconto", Ajuste(tipo="desconto", valor=valor, seguradora=cod), n, False,
                                        fech, f"desconto de {_pct(valor)} (a margem da corretora fica em {_pct(n)})"))
            else:
                tabela = {normalizar(k): v for k, v in (cfg.get("desconto_permitido_pct") or {}).items()}
                lib = tabela.get(normalizar(oferta.get("seguradora")))
                if isinstance(lib, (int, float)) and not isinstance(lib, bool) and lib > 0:
                    passos.append(Passo("desconto", Ajuste(tipo="desconto", valor=float(lib), seguradora=cod), atual,
                                        False, False, f"desconto de {_pct(float(lib))} que a seguradora libera"))
        elif alavanca == "comissao":
            if por_desconto:
                continue                  # a seguradora ignora a comissão: o passo já saiu como desconto
            # a descrição diz a comissão de ORIGEM real da tentativa (a da oferta de onde o recálculo parte), nunca um
            # degrau intermediário que não foi aplicado (conserto 130-A.1, juiz 6): cada tentativa recalcula da origem
            for n, fech in niveis:
                passos.append(Passo("comissao", Ajuste(tipo="comissao", valor=n, seguradora=cod), n, False, fech,
                                    f"comissão da corretora de {_pct(atual)} para {_pct(n)}"))
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


def _fechamento_guardado(oferta: Mapping[str, Any], cfg: Mapping[str, Any], feitos: Sequence[str] = ()) -> bool:
    """Ainda há degraus da alavanca de fechamento para ESTA oferta (o agente sabe que tem a última cartada)."""
    return any(p.fechamento and p.id not in feitos for p in ordem_do_mais_barato(oferta, config=cfg, fechamento=True))


# ---------------------------------------------------------------------------------------------------------------------
def _tentativa(oferta: Mapping[str, Any], passo: Passo, passos_antes: Sequence[str]) -> Dict[str, Any]:
    return {"origem_calculo_id": str(oferta.get("calculo_id") or ""), "oferta_de_origem_id": str(oferta.get("id") or ""),
            "seguradora": nome_de_exibicao(oferta.get("seguradora")), "seguradora_codigo": _codigo(oferta),
            "premio_de_origem": float(oferta.get("premio_total") or 0), "pacote_de_origem": oferta.get("pacote"),
            "passos": list(passos_antes) + [passo.id],
            "passo": passo.para_dict(), "ajuste": passo.ajuste,
            "comissao_resultante": passo.comissao_resultante,
            "corta_cobertura": _cortes_acumulados(list(passos_antes) + [passo.id]),
            "fechamento": passo.fechamento}


def _cortes_acumulados(passos: Sequence[str]) -> List[str]:
    return [p.split(":", 1)[0] for p in passos if p.split(":", 1)[0] not in ALAVANCAS_DE_MARGEM]


def _no_teto(tentativas: List[Dict[str, Any]], cfg: Mapping[str, Any]) -> Dict[str, Any]:
    teto = int(cfg["negociacao"]["max_tentativas_por_etapa"])
    return {"tentativas": tentativas[:teto], "fora_do_teto": max(0, len(tentativas) - teto)}


def planejar(ofertas: Iterable[Mapping[str, Any]], *, alvo: float, config: Optional[Mapping[str, Any]] = None,
             seguradora: Any = None, fechamento: bool = False) -> Dict[str, Any]:
    """A 1ª ETAPA da cotação-alvo. `ofertas` = as COMPLETAS da corretora DONA (com `calculo_id` e a comissão).
    Tentativas de UM passo a partir do cálculo de origem, passo a passo na ordem D-MC-67 entre as seguradoras mais
    baratas (teto `negociacao.max_seguradoras`/`max_tentativas_por_etapa`). Sem `fechamento`, nenhum degrau abaixo
    de `comissao.autonomo_minimo`; `fechamento_disponivel` diz se a alavanca ainda está guardada."""
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
        return {"status": "sem_oferta", "tentativas": []}
    no_alvo = [o for o in lista if float(o["premio_total"]) <= alvo]
    if no_alvo:
        melhor = max(no_alvo, key=lambda o: (_comissao_atual(o, cfg), -float(o["premio_total"])))
        return {"status": "ja_no_alvo", "oferta_id": str(melhor.get("id") or ""),
                "seguradora": nome_de_exibicao(melhor.get("seguradora")), "premio_anual": float(melhor["premio_total"]),
                "tentativas": []}
    candidatas = sorted(lista, key=lambda o: float(o["premio_total"]))[: int(cfg["negociacao"]["max_seguradoras"])]
    por_candidata = [(o, ordem_do_mais_barato(o, config=cfg, fechamento=fechamento)) for o in candidatas]
    guardado = (not fechamento) and any(_fechamento_guardado(o, cfg) for o in candidatas)
    tentativas: List[Dict[str, Any]] = []
    profundidade = max((len(p) for _, p in por_candidata), default=0)
    for i in range(profundidade):                      # passo-a-passo: o 1º passo de todas antes do 2º de qualquer
        for o, passos in por_candidata:
            if i < len(passos):
                tentativas.append(_tentativa(o, passos[i], []))
    if not tentativas:
        return {"status": "sem_caminho", "tentativas": [], "fechamento_disponivel": guardado,
                "recomendacao": "nenhum ajuste permitido nestas seguradoras"}
    return {"status": "planejado", "fechamento_disponivel": guardado, **_no_teto(tentativas, cfg)}


def texto_da_alavanca(preco_antes: float, preco_depois: float, *, voz: str = "corretora") -> str:
    """A frase da ALAVANCA DE FECHAMENTO, em REAIS (D-MC-68 corrigida). `preco_antes` = o preço que o cliente já
    ouviu; `preco_depois` = o que a seguradora DEVOLVEU no recálculo com a margem de fechamento — a diferença é a
    conta entre dois preços reais, nunca um percentual nem um número inventado. 🔴 Nunca "%", nunca "comissão",
    nunca urgência ("só hoje", "corra", "expira"): a única condição é o fechamento."""
    if voz not in COM_QUEM:
        raise ValueError("voz: " + " · ".join(COM_QUEM))
    antes, depois = float(preco_antes), float(preco_depois)
    if depois <= 0 or antes - depois < 0.01:
        raise ValueError("a alavanca precisa de uma diferença positiva entre dois preços reais")
    return FRASE_DA_ALAVANCA.format(diferenca=reais(antes - depois), preco=reais(depois), com_quem=COM_QUEM[voz])


def reais(v: float) -> str:
    """R$ no formato brasileiro, sem arredondar para cima: "R$ 1.312,40"; centavos zerados somem ("R$ 312")."""
    centavos = int(math.floor(float(v) * 100 + _EPS))
    inteiro, cent = divmod(centavos, 100)
    texto = f"{inteiro:,}".replace(",", ".")
    return f"R$ {texto}" + (f",{cent:02d}" if cent else "")


def escolher(resultados: Iterable[Mapping[str, Any]], *, alvo: float,
             config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """`resultados` = cada tentativa com a `oferta` que voltou (ou None). Chegou → entre as SEM corte, a de MAIOR
    comissão; só com corte → a de maior comissão com menos cortes, os cortes listados e a recomendação.
    A escolhida abaixo de `autonomo_minimo` traz `fechamento` = o preço antes (o que o cliente já ouviu da MESMA
    seguradora, sem corte, na margem normal), o depois (o recálculo) e a frase em reais."""
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
        saida = {"status": "chegou", "recomenda": recomenda, "corta_cobertura": cs,
                 "escolhida": _resumo(r, comissao(r)),
                 "recomendacao": ("chega no alvo sem mexer na cobertura" if not cs else
                                  ("chega no alvo mudando: " + ", ".join(cs) + (" — recomendo" if recomenda
                                                                                else " — NÃO recomendo"))),
                 "fechamento": None}
        if comissao(r) < float(cfg["comissao"]["autonomo_minimo"]) - _EPS:
            saida["fechamento"] = _a_alavanca(r, validos, cfg, comissao)
        return saida
    melhor = min(validos, key=lambda x: float(x["oferta"]["premio_total"]))
    return {"status": "nao_chegou", "melhor_parcial": _resumo(melhor, comissao(melhor))}


def _a_alavanca(r: Mapping[str, Any], validos: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any],
                comissao) -> Optional[Dict[str, Any]]:
    """O antes e o depois da alavanca, ambos preços que a SEGURADORA devolveu: o depois é o da escolhida; o antes é o
    menor preço da MESMA seguradora, sem corte, ainda na margem normal (senão, o preço da origem da tentativa)."""
    cod = r.get("seguradora_codigo", _codigo(r["oferta"]))
    autonomo = float(cfg["comissao"]["autonomo_minimo"])
    normais = [float(x["oferta"]["premio_total"]) for x in validos
               if x.get("seguradora_codigo", _codigo(x["oferta"])) == cod and not _cortes_acumulados(x.get("passos") or ())
               and comissao(x) >= autonomo - _EPS]
    antes = min(normais) if normais else float(r.get("premio_de_origem") or 0)
    depois = float(r["oferta"]["premio_total"])
    if antes - depois < 0.01:
        return None                       # a margem de fechamento não baixou o preço: não há o que oferecer em reais
    return {"preco_antes": round(antes, 2), "preco_depois": round(depois, 2), "diferenca": round(antes - depois, 2),
            "texto": {voz: texto_da_alavanca(antes, depois, voz=voz) for voz in COM_QUEM}}


def _resumo(r: Mapping[str, Any], comissao: float) -> Dict[str, Any]:
    o = r["oferta"]
    return {"calculo_id": r.get("calculo_id"), "oferta_id": str(o.get("id") or ""),
            "seguradora": nome_de_exibicao(o.get("seguradora")), "seguradora_codigo": _codigo(o),
            "premio_anual": round(float(o["premio_total"]), 2), "comissao_percentual": comissao,
            "passos": list(r.get("passos") or ()), "corta_cobertura": _cortes_acumulados(r.get("passos") or ()),
            "_oferta": o}


def proxima_etapa(resultados: Iterable[Mapping[str, Any]], *, alvo: float, config: Optional[Mapping[str, Any]] = None,
                  fechamento: bool = False) -> Dict[str, Any]:
    """Não chegou: os passos que FALTAM, encadeados sobre o MELHOR parcial (o novo cálculo de origem é o dele).
    Sem passo restante → "não recomendo" com o melhor parcial (e se a alavanca de fechamento ainda está guardada)."""
    cfg = config or PADRAO_DO_PRODUTO
    decisao = escolher(resultados, alvo=alvo, config=cfg)
    if decisao["status"] == "chegou":
        return {"status": "chegou", **{k: v for k, v in decisao.items() if k != "status"}}
    parcial = decisao.get("melhor_parcial")
    if not parcial:
        return {"status": "sem_caminho", "tentativas": [], "recomendacao": "nenhuma tentativa devolveu preço"}
    oferta = dict(parcial["_oferta"])
    oferta["calculo_id"] = parcial["calculo_id"]
    # a margem JÁ atingida pelo parcial: os níveis iguais ou acima dela não voltam (nem como desconto)
    oferta["comissao_percentual"] = parcial["comissao_percentual"]
    feitos = list(parcial["passos"])
    restantes = [p for p in ordem_do_mais_barato(oferta, config=cfg, fechamento=fechamento) if p.id not in feitos]
    guardado = (not fechamento) and _fechamento_guardado(oferta, cfg, feitos)
    publico = {k: v for k, v in parcial.items() if k != "_oferta"}
    if not restantes:
        return {"status": "sem_caminho", "tentativas": [], "melhor_parcial": publico, "fechamento_disponivel": guardado,
                "recomendacao": "não recomendo: nem com todos os ajustes permitidos chega no alvo"}
    tentativas = [_tentativa(oferta, p, feitos) for p in restantes]
    return {"status": "proxima_etapa", "melhor_parcial": publico, "fechamento_disponivel": guardado,
            **_no_teto(tentativas, cfg)}


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
