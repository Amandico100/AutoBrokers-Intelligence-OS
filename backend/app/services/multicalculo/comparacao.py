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

from app.services.multicalculo.config import (PADRAO_DO_PRODUTO, casa_seguradora, coberturas_essenciais,
                                              e_produto_de_assinatura, normalizar, preferencias_do_ramo)
from app.services.multicalculo.pedido import CHAVE_DA_BASICA, RAMOS_RE

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
#: SPEC-129-C D-129C-04 — a seguradora sem atividade inequívoca para o empresarial SAI do cálculo e é LISTADA. O robô
#: (F1) a anuncia como evento: `tipo == SEM_ATIVIDADE_COMPATIVEL` (ou `familia == SEM_ATIVIDADE_COMPATIVEL`).
from portal_worker.multicalculo import contrato as _contrato  # noqa: E402

SEM_ATIVIDADE = str(getattr(_contrato, "SEM_ATIVIDADE_COMPATIVEL", "sem_atividade_compativel")).upper()
FRASE_DA_FAMILIA[SEM_ATIVIDADE] = "não tem na lista dela a atividade deste negócio"
#: no RE o "perfil" é um RISCO (o imóvel), não um motorista
FRASE_DA_FAMILIA_RE: Dict[str, str] = {ACEITACAO: "não aceitou este risco"}
# a família mais INFORMATIVA vence quando a mesma seguradora recusou de mais de um jeito
_PRIORIDADE_DA_FAMILIA = (SEM_ATIVIDADE, ACEITACAO, INSTABILIDADE, COMERCIAL, DADO, PENDENTE, CREDENCIAL, PERMISSAO,
                          DESCONHECIDA)

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
    avisos: Tuple[str, ...] = ()     # RE (conserto 129-C): COMPARÁVEL, mas com o que a seguradora não informou


COMPLETA = Classe(True, "completa")


def _sem_margem(cob: Dict[str, Any]) -> Dict[str, Any]:
    """🔴 G3 (SPEC-129-C): 📊 as 9 gravações de RE trazem `percComissao` DENTRO de `resultados[].coberturas` (ex.: 30)
    — a margem da corretora não pode sair por uma linha de cobertura nem pela `coberturas_brutas` do ranking.

    ⚠️ DECLARADO (red P7, conserto 129-C): vale para TODOS os ramos, o AUTO inclusive — `percComissao*`/`percDesconto*`
    saem também da `coberturas_brutas` do auto e da assinatura que `_repete` compara (a "Mais completa" que difere da
    referência SÓ no desconto passa a contar como repetida). Nada VISÍVEL muda no auto: a régua do auto lê
    `tipoPadronizado`/`casco`, as linhas públicas leem chaves nomeadas e nenhum consumidor do app/front lê essas chaves
    na `coberturas_brutas` — `test_spec129c_conserto_app.py::test_sem_margem_nao_muda_nada_visivel_no_auto` prova."""
    return {k: v for k, v in cob.items() if not str(k).lower().startswith(("perccomissao", "percdesconto"))}


def _coberturas(oferta: Mapping[str, Any]) -> Dict[str, Any]:
    c = oferta.get("coberturas")
    if isinstance(c, Mapping):
        return _sem_margem(dict(c))
    if isinstance(c, (list, tuple)):            # contrato.Oferta guarda tuplas (chave, valor)
        try:
            return _sem_margem({str(k): v for k, v in c})
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


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-129-C — a régua de RE (condomínio 16 · residencial 2 · empresarial 18)
# ---------------------------------------------------------------------------------------------------------------------
#: o nome que o segurado lê para cada chave de cobertura de RE — 📊 os RÓTULOS da tela do Agger
#: (`fixtures/agger_ramos/formulario_*.json`, campo `rotulo`, 11/10); onde o rótulo muda por ramo, o termo comum.
NOME_DA_COBERTURA_RE: Dict[str, str] = {
    CHAVE_DA_BASICA: "Básica (incêndio, raio e explosão)",
    "isDanosIncendioRaioExplosaoCond": "Incêndio do conteúdo dos condôminos", "isValorCondominio": "RC Condomínio",
    "isValorSindico": "RC Síndico", "isDanosEletricos": "Danos elétricos", "isDanosVendaval": "Vendaval",
    "isDanosImpactoVeiculo": "Impacto de veículos", "isDanosRoubo": "Roubo de bens",
    "rouboCondomino": "Roubo de bens dos condôminos", "isDanosPortoes": "Portões", "isDanosMorais": "Danos morais",
    "vidros": "Vidros", "isDanosDesmoronamento": "Desmoronamento", "isDanosAluguel": "Perda ou pagamento de aluguel",
    "isDanosVazamentoTanquesTubulacoes": "Vazamento de tanques e tubulações",
    "tumultoGreveLockOut": "Tumultos, greves e lock-out", "isDanosAlagamento": "Alagamento",
    "isDanosDespesasFixas": "Despesas fixas", "isEmpregador": "RC Empregador", "garagista": "RC Garagista",
    "garagistaExclusiva": "RC Garagista (exclusiva)", "responsabilidadeCivil": "Responsabilidade civil",
    "isDanosEquipamentosEletronicos": "Equipamentos eletrônicos", "equipamentos": "Equipamentos",
    "recomposicaoDocumentos": "Recomposição de documentos", "lucroCessante": "Lucros cessantes",
    "assist24hs": "Assistência",
}


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool) or v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _moda(valores: Sequence[float]) -> Optional[float]:
    """O valor mais comum; empate → o MENOR (a régua exige o que a maioria tem, nunca o que só a melhor tem)."""
    if not valores:
        return None
    contagem = Counter(round(v, 2) for v in valores)
    topo = max(contagem.values())
    return min(v for v, n in contagem.items() if n == topo)


def referencia_re(ofertas: Iterable[Mapping[str, Any]], essenciais: Iterable[str]) -> Dict[str, Any]:
    """A CONFIGURAÇÃO do quadro de RE numa opção, lida das ofertas COM PREÇO — só o PLANO B (conserto 129-C, red P2):
    a régua compara com o PEDIDO (`pedido_re`); isto vale apenas quando o estado do cálculo não traz as coberturas
    pedidas (a régua sai marcada `re_sem_pedido`). A básica = a mais comum; cada essencial entra quando a MAIORIA a
    devolve > 0, com o valor mais comum. Sem nenhuma básica devolvida → `basica: None` (vale a genérica, marcada)."""
    com_preco = [o for o in ofertas if _premio(o) is not None]
    basicas = [b for b in (_num(_coberturas(o).get(CHAVE_DA_BASICA)) for o in com_preco) if b and b > 0]
    exigidas: Dict[str, float] = {}
    for chave in essenciais:
        if chave == CHAVE_DA_BASICA:
            continue
        valores = [v for v in (_num(_coberturas(o).get(chave)) for o in com_preco) if v and v > 0]
        if com_preco and 2 * len(valores) > len(com_preco):
            exigidas[chave] = _moda(valores)
    contagem = Counter(assinatura_de_coberturas(o) for o in com_preco)
    return {"basica": _moda(basicas), "essenciais": exigidas,
            "assinatura": contagem.most_common(1)[0][0] if contagem else None}


def _nome_re(chave: str) -> str:
    return NOME_DA_COBERTURA_RE.get(chave, chave)


#: o que NÃO se compara em R$: a assistência vai como CÓDIGO (1/2/3) e volta como o TEXTO da seguradora (📊 canário
#: 11/10 §3.6: "Plano Plus", "COMPLETO") — comparar os dois seria inventar "cobre menos"
_FORA_DA_COMPARACAO_RE = frozenset({"assist24hs", CHAVE_DA_BASICA})
#: 🔴 as EQUIVALÊNCIAS DE ECO do condomínio (16) — cada uma com a evidência (CLAUDE.md §9.5):
#:  · RC SOMADA: 📊 nas 3/3 gravações de condomínio (`fixtures/agger_ramos/gravacao_condominio_{1,2,3}.json`,
#:    `resultados[].coberturas`), a HDI devolve a RC Condomínio + a RC Síndico SOMADAS em `isValorSindico` e a Axa em
#:    `isValorCondominio`, no valor EXATO da soma do pedido (1 mi = 500 mil + 500 mil · 2 mi = 1 mi + 1 mi · 400 mil =
#:    200 mil + 200 mil; prova crua: `scratchpad/red/a3_rc_somada.py` do red team 129-C). O canário ao vivo repetiu
#:    (CANARIO-AO-VIVO §3.6: HDI síndico 600 mil e Axa condomínio 600 mil, pedido 300 mil + 300 mil). Regra: UMA chave
#:    de RC ecoada, a outra ausente, e o valor ecoado ≥ a soma do pedido → as duas RC do pedido estão cobertas.
#:  · `responsabilidadeCivil` = RC Condomínio: 📊 gravacao_condominio_3, a Allianz devolve `isValorSindico` 200 mil +
#:    `responsabilidadeCivil` 200 mil e NENHUM `isValorCondominio` (pedido: 200 mil + 200 mil). O formulário do
#:    condomínio NÃO tem a chave `responsabilidadeCivil` (`presets.CHAVES_DE_COBERTURA_RE[16]`): no ramo 16 ela só pode
#:    ser a RC do condomínio. Vale só quando `isValorCondominio` não veio.
RC_DO_CONDOMINIO: Tuple[str, str] = ("isValorCondominio", "isValorSindico")
RC_CONDOMINIO_COMO_A_SEGURADORA_CHAMA = "responsabilidadeCivil"
RAMO_CONDOMINIO = 16


def pedido_re(coberturas_pedidas: Any) -> Optional[Dict[str, float]]:
    """As coberturas que o CÁLCULO mandou (a linha `multicalculo_calculos.coberturas`, que a porta devolve no estado
    como `coberturas_pedidas`) em número; sem a básica → None (não há o que comparar)."""
    if not isinstance(coberturas_pedidas, Mapping):
        return None
    saida = {str(k): _num(v) for k, v in _sem_margem(dict(coberturas_pedidas)).items()}
    saida = {k: v for k, v in saida.items() if v is not None}
    return saida if (saida.get(CHAVE_DA_BASICA) or 0) > 0 else None


def ecos_re(cob: Mapping[str, Any], pedido: Mapping[str, float], ramo: int) -> Dict[str, Optional[float]]:
    """Cada cobertura PEDIDA (> 0, menos básica e assistência) → o valor que a seguradora ECOOU para ela, com as
    equivalências medidas acima; None = não ecoou (FATO: não devolveu — nunca a inferência "não cobre")."""
    eco = {k: _num(v) for k, v in cob.items()}
    if int(ramo) == RAMO_CONDOMINIO:
        cond, sind = RC_DO_CONDOMINIO
        if eco.get(cond) is None and eco.get(RC_CONDOMINIO_COMO_A_SEGURADORA_CHAMA) is not None:
            eco[cond] = eco[RC_CONDOMINIO_COMO_A_SEGURADORA_CHAMA]
        ecoadas = [k for k in RC_DO_CONDOMINIO if eco.get(k) is not None]
        soma = sum(pedido.get(k) or 0 for k in RC_DO_CONDOMINIO)
        if len(ecoadas) == 1 and soma > 0 and eco[ecoadas[0]] >= soma - 1.0:
            for k in RC_DO_CONDOMINIO:                    # a RC somada cobre as duas do pedido
                if (pedido.get(k) or 0) > 0:
                    eco[k] = pedido[k]
    return {k: eco.get(k) for k, v in pedido.items() if v and v > 0 and k not in _FORA_DA_COMPARACAO_RE}


def _classificar_re(oferta: Mapping[str, Any], referencia: Any = None) -> Classe:
    """RE (conserto 129-C): a oferta contra o PEDIDO do cálculo dela (`referencia["pedido"]`), nunca contra o quadro.

        básica ausente ............. DIFERENTE ("não informou a básica")
        básica ≠ a do pedido ....... DIFERENTE (o preço é de outro seguro)
        essencial ecoada MENOR/0 ... DIFERENTE "cobre menos: X" (a config do ramo diz o que é essencial)
        pedida e NÃO ecoada ........ COMPARÁVEL com o aviso "não informou X" (📊 18 de 38 ofertas ecoam menos chaves que
                                     o enviado — não devolver é FATO; "não inclui" seria inferência)
        não essencial ecoada menor . COMPARÁVEL com o aviso "cobre menos que o pedido: X"
    Sem referência de básica (nenhuma oferta a devolveu) → a régua genérica (mesma configuração da maioria)."""
    ref = referencia if isinstance(referencia, Mapping) else None
    if ref is None or not ref.get("pedido"):
        return _classificar_generico(oferta, ref.get("assinatura") if ref else None)
    pedido, ramo = ref["pedido"], int(ref.get("ramo") or 0)
    essenciais = set(ref.get("essenciais") or ())
    cob = _coberturas(oferta)
    if not cob:
        return Classe(False, "sem_cobertura_informada", "a seguradora não informou as coberturas")
    basica = _num(cob.get(CHAVE_DA_BASICA))
    if basica is None or basica <= 0:
        return Classe(False, "basica_nao_informada", "não informou o valor da cobertura básica (incêndio)")
    alvo = float(pedido[CHAVE_DA_BASICA])
    if abs(basica - alvo) >= 1.0:
        de_quem = "o pedido" if ref.get("fonte") == "pedido" else "as outras"
        return Classe(False, "basica_diferente", f"calculou a cobertura básica (incêndio) com {reais(basica)}; "
                                                 f"{de_quem}, com {reais(alvo)}")
    ecos = ecos_re(cob, pedido, ramo)
    nao_informou = [k for k, v in ecos.items() if v is None]
    menores = [k for k, v in ecos.items() if v is not None and v < pedido[k] - 1.0]
    menos_essencial = [k for k in menores if k in essenciais]
    if menos_essencial:
        return Classe(False, "cobre_menos", "cobre menos: " + ", ".join(_nome_re(k) for k in menos_essencial))
    ordem = lambda ks: sorted(ks, key=lambda k: (k not in essenciais, list(pedido).index(k)))  # noqa: E731
    avisos = []
    if nao_informou:
        avisos.append("não informou " + ", ".join(_nome_re(k) for k in ordem(nao_informou)))
    if menores:
        avisos.append("cobre menos que o pedido: " + ", ".join(_nome_re(k) for k in ordem(menores)))
    return Classe(True, "completa", avisos=tuple(avisos)) if avisos else COMPLETA


#: ramo → a régua. O que não está aqui usa `_classificar_generico` (D-MC-73: a 129-C mede e acrescenta).
REGRAS_POR_RAMO: Dict[int, Callable[[Mapping[str, Any], Any], Classe]] = {
    RAMO_AUTO: _classificar_auto, **{r: _classificar_re for r in RAMOS_RE}}


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
    # SPEC-129-C: produto de ASSINATURA é do carro (Azul por Assinatura) — no RE o prêmio devolvido é o anual
    if int(ramo) not in RAMOS_RE and e_produto_de_assinatura(oferta.get("seguradora"), oferta.get("pacote"), cfg):
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
            if int(ramo) in RAMOS_RE:            # SPEC-129-C: o nome da TELA e o valor em R$
                n = _num(v)
                valor = reais(n) if n is not None and k != "assist24hs" else str(v)
                linhas.append({"chave": str(k), "nome": NOME_DA_COBERTURA_RE.get(k, str(k)), "valor": valor})
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


def posicao_de_preferencia(oferta: Mapping[str, Any], preferidas: Sequence[Any]) -> Optional[int]:
    """D-129C-07: a posição (1 = a mais preferida) da seguradora da oferta na lista do ramo, ou None. Item `int` casa
    o código da seguradora no Agger; item texto casa o nome (começo de palavra, `casa_seguradora`)."""
    cod = oferta.get("seguradora_codigo")
    nomes = [str(oferta.get("seguradora") or ""), nome_de_exibicao(oferta.get("seguradora"))]
    for i, item in enumerate(preferidas or (), start=1):
        if isinstance(item, int) and not isinstance(item, bool):
            if cod is not None and not isinstance(cod, bool) and str(cod) == str(item):
                return i
        elif isinstance(item, str) and any(casa_seguradora(n, [item]) for n in nomes):
            return i
    return None


def _entrada(oferta: Mapping[str, Any], opcao: str, corretora: str, ramo: int,
             preferidas: Sequence[Any] = (), avisos: Sequence[str] = ()) -> Dict[str, Any]:
    """A linha de ranking — campos ESCOLHIDOS um a um (a comissão nunca é copiada)."""
    cob = _coberturas(oferta)
    pref = posicao_de_preferencia(oferta, preferidas)
    fv = oferta.get("franquia_valor")
    try:
        fv = float(fv) if fv is not None else None
    except (TypeError, ValueError):
        fv = None
    linha = {
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
        # SPEC-129-C D-129C-07: a preferida da corretora no ramo é MARCADA — nunca esconde as outras
        "preferida": pref is not None, "ordem_de_preferencia": pref,
    }
    if ramo in RAMOS_RE:
        # conserto 129-C (red P1 · juiz P3): COMPARÁVEL, mas o corretor LÊ o que a seguradora não devolveu
        linha["avisos"] = list(avisos)
    return linha


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
    pedidos_re: Dict[str, Dict[str, float]] = {}      # SPEC-129-C conserto: calculo_id → as coberturas PEDIDAS
    for e in estados or ():
        cid = str(e.get("calculo_id") or e.get("id") or "")
        if not cid or not e.get("opcao"):
            continue
        corr = str(e.get("corretora_company_id") or e.get("company_id") or "")
        por_calculo[cid] = (str(e["opcao"]), corr)
        if ramo in RAMOS_RE:
            ped_re = pedido_re(e.get("coberturas_pedidas"))
            if ped_re:
                pedidos_re[cid] = ped_re
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
    preferidas = preferencias_do_ramo(cfg, ramo)
    reguas: Dict[str, str] = {}
    for opcao, itens in agrupadas.items():
        referencia = None
        ref_por_calculo: Dict[str, Dict[str, Any]] = {}
        if ramo in RAMOS_RE:
            # conserto 129-C (red P2 · canário #2): cada oferta contra o PEDIDO do cálculo dela; o quadro (a moda) só
            # quando o estado não trouxe as coberturas pedidas — e a régua sai marcada `re_sem_pedido`, nunca calada
            essenciais = coberturas_essenciais(cfg, ramo)
            quadro_re = referencia_re([o for o, _ in itens], essenciais)
            if quadro_re["basica"] is None:
                referencia = quadro_re                    # nenhuma oferta devolveu a básica: a genérica, marcada
                reguas[opcao] = "generica_sem_basica"
            else:
                plano_b = {"ramo": ramo, "essenciais": tuple(essenciais), "fonte": "quadro",
                           "pedido": {CHAVE_DA_BASICA: quadro_re["basica"], **quadro_re["essenciais"]}}
                sem_pedido = False
                for o, _ in itens:
                    cid = str(o.get("calculo_id") or "")
                    if cid in pedidos_re:
                        ref_por_calculo[cid] = {"ramo": ramo, "essenciais": tuple(essenciais), "fonte": "pedido",
                                                "pedido": pedidos_re[cid]}
                    else:
                        ref_por_calculo[cid], sem_pedido = plano_b, True
                reguas[opcao] = "re_sem_pedido" if sem_pedido else "re"
        elif ramo not in REGRAS_POR_RAMO:
            contagem = Counter(assinatura_de_coberturas(o) for o, _ in itens if _premio(o) is not None)
            referencia = contagem.most_common(1)[0][0] if contagem else None
        melhores: Dict[Tuple[str, str], Dict[str, Any]] = {}
        difs: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        responderam[opcao] = set()
        for o, corr in itens:
            responderam[opcao].add(_chave_seguradora(o))
            classe = classificar(o, config=cfg, ramo=ramo,
                                 referencia=ref_por_calculo.get(str(o.get("calculo_id") or ""), referencia))
            if classe.comparavel:
                ent = _entrada(o, opcao, corr, ramo, preferidas, classe.avisos)
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
        # no MESMO prêmio, a preferida da corretora vem antes (D-129C-07); sem preferência, a ordem de sempre
        por_opcao[opcao] = sorted(melhores.values(), key=lambda e: (
            e["premio_anual"], e["ordem_de_preferencia"] is None, e["ordem_de_preferencia"] or 0, e["seguradora"]))
        diferentes_por_opcao[opcao] = sorted(difs.values(), key=lambda d: (d["premio_anual"] is None,
                                                                           d["premio_anual"] or 0, d["seguradora"]))

    # quem NÃO respondeu, por opção: recusa/pendência de uma seguradora que NÃO tem oferta nenhuma nessa opção
    recusas: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for ev in eventos or ():
        familia = str(ev.get("familia") or "").upper()
        if str(ev.get("tipo") or "").upper() == SEM_ATIVIDADE:
            familia = SEM_ATIVIDADE                  # SPEC-129-C D-129C-04: saiu do cálculo, listada
        elif ev.get("tipo") != SEGURADORA_RECUSOU and familia != PENDENTE:
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
                                     "motivo": (FRASE_DA_FAMILIA_RE.get(familia) if ramo in RAMOS_RE else None)
                                     or FRASE_DA_FAMILIA.get(familia, FRASE_DA_FAMILIA[DESCONHECIDA]),
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
    if ramo in RAMOS_RE:
        # SPEC-129-C: QUAL régua decidiu o "comparável" da opção completa — "re" (contra o PEDIDO) · "re_sem_pedido"
        # (algum estado sem as coberturas pedidas: contra a moda do quadro) · "generica_sem_basica" (nenhuma oferta
        # devolveu a básica): fica VISÍVEL, nunca calado
        resumo["regua"] = reguas.get(opcao_completa)
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


def _aspas(rotulo: str, renovacao: bool) -> str:
    """O nome de uma opção citado no texto: aspas tipográficas na RENOVAÇÃO (laudo de design 131-B, conserto 2); a
    cotação segue byte a byte como era."""
    return f"“{rotulo}”" if renovacao else f"\"{rotulo}\""


def _motivos(e: Mapping[str, Any], papel: str, *, ranking_completa: Sequence[Mapping[str, Any]],
             referencia: Optional[Mapping[str, Any]], rotulo_ref: Optional[str], pool: Sequence[Mapping[str, Any]],
             apolice_atual: Optional[Mapping[str, Any]], ramo: int, renovacao: bool = False) -> List[str]:
    """Os motivos do ✓ ("por que recomendamos"). `renovacao` (SPEC-131-B, laudo de design, consertos 1 e 2): um AUMENTO
    sobre a apólice de hoje NUNCA é motivo (ele é informação neutra no "o seu seguro hoje × a renovação"); a franquia é
    "Franquia: R$ X" (o "reduzida" é só o NOME de uma opção); "7%" e "100%" sem espaço; aspas tipográficas."""
    m: List[str] = []
    n = len(ranking_completa)
    pct_sep = "" if renovacao else " "
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
            m.append(f"{reais(abs(dif))} {'a menos' if dif < 0 else 'a mais'} por ano que a opção "
                     f"{_aspas(rotulo_ref, renovacao)}")
    atual = (apolice_atual or {}).get("premio_anual")
    if atual:
        try:
            atual = float(atual)
            dif = e["premio_anual"] - atual
            # renovação: só a ECONOMIA é motivo — o aumento não ganha ✓ (fica no "o que mudou", neutro)
            if abs(dif) >= 0.01 and atual > 0 and not (renovacao and dif > 0):
                pct = abs(dif) / atual * 100
                m.append(f"{reais(abs(dif))} {'a menos' if dif < 0 else 'a mais'} que a sua apólice atual "
                         f"({pct:.0f}{pct_sep}%)")
        except (TypeError, ValueError):
            pass
    fv = e["franquia"]["valor"]
    if fv is not None and fv > 0:
        franqs = [p["franquia"]["valor"] for p in pool if p["franquia"]["valor"]]
        if len(set(franqs)) > 1 and fv <= min(franqs) + 0.005:
            m.append(f"A menor franquia do quadro: {reais(fv)}")
        elif renovacao:
            m.append(f"Franquia: {reais(fv)}")
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
        m.append(f"Cobertura completa: batida, roubo, incêndio e danos a terceiros, 100{pct_sep}% da tabela FIPE"
                 if ramo == RAMO_AUTO else "Mesma configuração de coberturas das outras opções comparadas")
    return m


def _o_que_muda(e: Mapping[str, Any], ref: Optional[Mapping[str, Any]], rotulo_ref: Optional[str],
                papel: str = "", renovacao: bool = False) -> List[str]:
    """`papel == "minima"` (D-130A1-05): a mínima foi PEDIDA sem carro reserva. Se a seguradora não informou o carro
    reserva, "Sem carro reserva" é a leitura que cobre MENOS (nunca a que promete a mais); se ela DEU dias mesmo assim,
    vale o que ela devolveu. `renovacao` (laudo de design 131-B, conserto 2): aspas tipográficas e a franquia como
    "Franquia: R$ X" (o "(R$ X menor)" repetia o que o "por que" do cartão já diz)."""
    if ref is None or ref["oferta_id"] == e["oferta_id"]:
        return []
    r = _aspas(rotulo_ref or "recomendada", renovacao)
    saida: List[str] = []
    dif = e["premio_anual"] - ref["premio_anual"]
    if abs(dif) >= 0.01:
        saida.append(f"{reais(abs(dif))} {'a menos' if dif < 0 else 'a mais'} por ano que a opção {r}")
    if e["seguradora"] != ref["seguradora"]:
        saida.append(f"Seguradora {e['seguradora']} (na opção {r}: {ref['seguradora']})")
    fv, fr = e["franquia"]["valor"], ref["franquia"]["valor"]
    if fv is not None and fr is not None and abs(fv - fr) >= 0.01:
        saida.append(f"Franquia: {reais(fv)}" if renovacao
                     else f"Franquia de {reais(fv)} ({reais(abs(fv - fr))} {'menor' if fv < fr else 'maior'})")
    ce, cr = _caracteristicas(e), _caracteristicas(ref)
    if ce["reserva"] is not None and cr["reserva"] is not None and ce["reserva"] != cr["reserva"]:
        saida.append("Sem carro reserva" if ce["reserva"] == 0
                     else f"Carro reserva por {ce['reserva']} dias (na opção {r}: {cr['reserva']})")
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
    renovacao = bool(ctx.get("renovacao"))          # só `_opcoes_da_renovacao` liga (a cotação segue byte a byte)
    return {
        "id": id_, "rotulo": rotulo, "seguradora": e["seguradora"], "produto": e["produto"],
        "premio_anual": e["premio_anual"], "parcelas": e["parcelas"], "franquia": dict(e["franquia"]),
        "coberturas": coberturas_publicas({"coberturas": e.get("coberturas_brutas") or {}}, ramo=ramo),
        "nota": nota_de(e, ctx["pool"], ctx["config"]),
        "motivos": _motivos(e, papel, ranking_completa=ctx["ranking_completa"],
                            referencia=None if ref is None or ref["oferta_id"] == e["oferta_id"] else ref,
                            rotulo_ref=rotulo_ref, pool=ctx["pool"], apolice_atual=ctx["apolice_atual"], ramo=ramo,
                            renovacao=renovacao),
        "o_que_muda": _o_que_muda(e, ref, rotulo_ref, papel, renovacao=renovacao),
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


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-131-B (D-131-22/40, laudo I3 §1.3/§2.3) — a ordem da RENOVAÇÃO: quem JÁ é cliente
# ---------------------------------------------------------------------------------------------------------------------
#: os cálculos da renovação (131-A, `porta.OPCOES_DA_RENOVACAO`) → o cartão que cada um vira, NA ORDEM da página. O 1º
#: (a apólice de hoje, iguais ou maiores) é o papel `completa` — `config_da_renovacao` o aponta para `anterior`.
CARTOES_DA_RENOVACAO: Tuple[Tuple[str, str, str], ...] = (
    ("franquia_reduzida", "franquia_reduzida", "Franquia reduzida"),
    ("completa_mais", "mais_completa", "Mais completa"),
)


def config_da_renovacao(config: Optional[Mapping[str, Any]], estados: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """A config com o papel `completa` no cálculo `anterior` quando o pedido o tem (131-A: as coberturas da apólice de
    hoje, iguais ou maiores) — é ele que vira o ranking, o resumo e "Sua renovação". Sem `anterior` (o pedido da 131-0
    sem a ficha), o papel fica como estava (`padrao`). Cópia: a config de quem chama não muda."""
    cfg = dict(config or PADRAO_DO_PRODUTO)
    papeis = dict(cfg.get("calculo_por_papel") or {"completa": "padrao"})
    if any(str(e.get("opcao") or "") == "anterior" for e in estados or ()):
        papeis["completa"] = "anterior"
    for calc, _id, _rot in CARTOES_DA_RENOVACAO:
        papeis.setdefault(calc, calc)
    cfg["calculo_por_papel"] = papeis
    return cfg


def _da_seguradora(lista: Sequence[Mapping[str, Any]], seguradora: str) -> Optional[Dict[str, Any]]:
    return next((dict(c) for c in lista if casa_seguradora(c["seguradora_original"], [seguradora])
                 or casa_seguradora(c["seguradora"], [seguradora])
                 or casa_seguradora(seguradora, [c["seguradora_original"]])
                 or casa_seguradora(seguradora, [c["seguradora"]])), None)


def _por_que_da_renovacao(e: Mapping[str, Any], id_: str, base: Mapping[str, Any], ramo: int) -> str:
    """O "por que recomendamos" de cada cartão da renovação — só o que a construção GARANTE (nada de ranking)."""
    de_hoje = e.get("opcao") == "anterior"          # o cálculo montado da apólice de hoje (131-A F2)
    if id_ == "sua_renovacao":
        return ("As coberturas do seu seguro de hoje, iguais ou maiores, na mesma seguradora: você renova sem perder "
                "nada." if de_hoje else "Cobertura completa na mesma seguradora de hoje: você continua com quem já "
                "conhece.")
    if id_ == "recomendada":
        return ("A sua seguradora de hoje não devolveu preço para estas coberturas; esta tem as coberturas do seu "
                "seguro de hoje, iguais ou maiores." if de_hoje else
                "A sua seguradora de hoje não devolveu preço com cobertura completa; esta tem cobertura completa.")
    if id_ == "franquia_reduzida":
        fv, fb = e["franquia"]["valor"], base["franquia"]["valor"]
        if fv is not None and fb is not None and fb - fv >= 0.01:
            return (f"A sua renovação com a franquia reduzida: se precisar acionar o seguro, você paga "
                    f"{reais(fb - fv)} a menos.")
        return "A sua renovação com a franquia reduzida: você paga menos se precisar acionar o seguro."
    if id_ == "mais_completa":
        if ramo == RAMO_AUTO and (e.get("coberturas_brutas") or {}).get("reparoRapido"):
            return "A sua renovação com a cobertura de pequenos reparos, para os consertos do dia a dia."
        return "A opção mais completa que calculamos para a sua renovação."
    if id_ == "menor_franquia":
        return f"A menor franquia entre as seguradoras com as mesmas coberturas: {reais(e['franquia']['valor'])}."
    return ("As mesmas coberturas em outra seguradora, se você quiser comparar." if de_hoje
            else "Cobertura completa em outra seguradora, se você quiser comparar.")


def _repete_na_renovacao(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """O `_repete` (J-P4) com a FRANQUIA: a "Franquia reduzida" tem as MESMAS coberturas da "Sua renovação" e só a
    franquia muda — pela assinatura das coberturas ela seria "a mesma repetida". Repetida = a mesma seguradora com o
    mesmo prêmio (± R$ 1), ou com as mesmas coberturas E a mesma franquia."""
    if normalizar(a.get("seguradora")) != normalizar(b.get("seguradora")):
        return False
    if abs(float(a["premio_anual"]) - float(b["premio_anual"])) < 1.0:
        return True
    fa, fb = a["franquia"]["valor"], b["franquia"]["valor"]
    mesma_franquia = (fa is None and fb is None) or (fa is not None and fb is not None and abs(fa - fb) < 0.01)
    return mesma_franquia and _repete(a, b)


def _opcoes_da_renovacao(comparacao: Comparacao, *, apolice_atual: Mapping[str, Any], config: Mapping[str, Any],
                         dona: str) -> List[Dict[str, Any]]:
    """🔴 SPEC-131-B (laudo I3 §1.3, D-131-22): na renovação a 1ª opção é a "Sua renovação" — a seguradora de HOJE no
    cálculo da apólice de hoje (`anterior`), mesmo que outra seja mais barata (RT-B1 vale para quem NÃO é cliente). Depois
    a franquia reduzida e a mais completa, da MESMA seguradora quando ela as calculou. ⛔ Econômica e mínima NUNCA (a
    "Mais em conta" e a "menor completa em 1º" são da cotação). A seguradora de hoje sem preço → a 1ª é a "Recomendada"
    (a menor com as mesmas coberturas), nunca chamada de "Sua renovação" (J-B2). Vaga sobrando → "Menor franquia" de
    outra seguradora, senão "Outra seguradora"."""
    papeis = comparacao.papeis
    A = comparacao.ranking(papeis.get("completa", "padrao"), dona)
    if not A:
        return []
    atual_seg = str(apolice_atual["seguradora"]).strip()
    base = _da_seguradora(A, atual_seg)
    escolhidas: List[Tuple[Dict[str, Any], str, str, str]] = []
    if base is not None:
        escolhidas.append((base, "sua_renovacao", "Sua renovação", "renovacao"))
    else:
        base = A[0]
        escolhidas.append((base, "recomendada", "Recomendada", "renovacao"))
    pool = list(A)
    for calc, id_, rot in CARTOES_DA_RENOVACAO:
        L = comparacao.ranking(papeis.get(calc, calc), dona)
        pool += L
        x = _da_seguradora(L, base["seguradora_original"] or base["seguradora"]) or (L[0] if L else None)
        if x is not None and not _repete_na_renovacao(x, base):
            escolhidas.append((x, id_, rot, calc))
    na_pagina = int(config["opcoes"]["na_pagina"])
    if len(escolhidas) < na_pagina:
        fora = {e[0]["oferta_id"] for e in escolhidas}
        outras = [c for c in A if c["oferta_id"] not in fora and normalizar(c["seguradora"]) != normalizar(base["seguradora"])]
        fb = base["franquia"]["valor"]
        menores = [c for c in outras if c["franquia"]["valor"] is not None and fb is not None
                   and c["franquia"]["valor"] < fb - 0.005]
        if menores:
            escolhidas.append((min(menores, key=lambda c: (c["franquia"]["valor"], c["premio_anual"])),
                               "menor_franquia", "Menor franquia", "completa"))
        elif outras:
            escolhidas.append((outras[0], "outra_seguradora", "Outra seguradora", "completa"))
    vistos: set = set()
    unicas = []
    for item in escolhidas:
        if item[0]["oferta_id"] not in vistos:
            vistos.add(item[0]["oferta_id"])
            unicas.append(item)
    unicas = unicas[:na_pagina]
    ctx = {"referencia": base, "rotulo_ref": unicas[0][2], "pool": pool, "config": config, "ranking_completa": A,
           "apolice_atual": apolice_atual, "renovacao": True}
    saida = []
    for e, id_, rot, papel in unicas:
        o = _opcao(e, id_, rot, papel, **ctx)
        o["por_que"] = _por_que_da_renovacao(e, id_, base, int(e.get("ramo") or RAMO_AUTO))
        saida.append(o)
    return saida


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
    renovação    → SPEC-131-B (`_opcoes_da_renovacao`): "Sua renovação" (a seguradora de HOJE) em 1º · Franquia reduzida
                   · Mais completa — nunca a econômica, a mínima nem a "menor completa em 1º"
    com apólice  → a seguradora da apólice É a menor completa: "Igual à sua atual" em 1º · Mais em
                   conta · Mais completa (senão a "Outra completa"/"Menor franquia")
                   não é: Recomendada (a menor completa) em 1º · "Igual à sua atual" · Mais em conta (senão Mais completa)
                   a seguradora da apólice não está no quadro: como sem apólice (nenhum "igual" inventado)

    🔴 Fora da renovação, a 1ª opção é SEMPRE a menor completa (RT-B1, red team 06/10): é ela que a página chama de "a melhor das N" e a
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
    if situacao == "renovacao":                                  # SPEC-131-B: a ordem de quem JÁ é cliente
        return _opcoes_da_renovacao(comparacao, apolice_atual=apolice_atual, config=cfg, dona=dona)
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
