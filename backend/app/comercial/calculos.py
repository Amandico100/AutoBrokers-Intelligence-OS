# -*- coding: utf-8 -*-
"""Os cruzamentos que transformam carteira em relatório — SPEC-081 Bloco B.

Tudo aqui é **função pura**: entra lista de dataclass, sai número. Nada de
rede, nada de banco, nada de relógio — o único `date.today()` do módulo mora
em `entender_periodo`, e é injetável.

Isso não é preferência de estilo. É o que permite testar a regra de negócio
sem depender da InfoCap estar de pé, e é o que garante que o relatório mostre
o mesmo número duas vezes seguidas.

## As três armadilhas que estas funções existem para evitar

**1. Somar todos os produtores triplica o faturamento.** 📊 A média é de 3
produtores por apólice (2025, n=3.536: 2→1.204, 3→1.221, 4→1.046, 5→64). O
`ordem=1` acontece na camada de dados; aqui a garantia é que **cada apólice
entra no ranking uma vez só**.

**2. Cobertura parcial vira mentira se não for declarada.** 📊 19,4% das
apólices de 2025 não têm produtor identificado. `cobertura()` existe para que
o relatório diga o número em vez de omiti-lo.

**3. Ticket médio esconde a história.** 📊 O #1 do ranking fez 250 apólices a
R$ 1.068 de ticket; o #2 fez **7** apólices a R$ 37.366. Volume e valor são
eixos diferentes, e um ranking que só ordena por total apaga isso.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# O que sai
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class LinhaDoRanking:
    nome: str
    apolices: int
    premio: float
    comissao: float
    repasse: float

    @property
    def ticket(self) -> float:
        """Comissão média por apólice. É o que separa volume de valor."""
        return self.comissao / self.apolices if self.apolices else 0.0

    @property
    def custo_de_aquisicao(self) -> float:
        """Quanto de cada real de comissão vai embora como repasse, em %.

        🔴 É o número que não existe em tela nenhuma da corretora: ele mora em
        dois endpoints diferentes e só passa a existir quando alguém os cruza.
        📊 Medido em 2025: varia de **0,7% a 38,0%** entre canais.
        """
        return 100.0 * self.repasse / self.comissao if self.comissao else 0.0


@dataclass(frozen=True)
class Cobertura:
    """Quanto do período o relatório realmente consegue atribuir.

    🔴 Vai IMPRESSO na peça. Um relatório que soma 80,6% e se apresenta como
    "o ano inteiro" mente por omissão — e mentira em peça com a logo da
    corretora, lida em voz alta, é o pior resultado possível.
    """

    apolices_total: int
    apolices_com_produtor: int
    comissao_total: float
    comissao_atribuida: float

    @property
    def pct_apolices(self) -> float:
        return (100.0 * self.apolices_com_produtor / self.apolices_total
                if self.apolices_total else 0.0)

    @property
    def pct_comissao(self) -> float:
        return (100.0 * self.comissao_atribuida / self.comissao_total
                if self.comissao_total else 0.0)

    def frase(self) -> str:
        """A declaração que vai no `callout` da peça."""
        return (
            f"{self.apolices_com_produtor:,} das {self.apolices_total:,} apólices "
            f"({self.pct_apolices:.1f}%) têm produtor identificado. O ranking "
            f"cobre {_reais(self.comissao_atribuida)} dos "
            f"{_reais(self.comissao_total)} de comissão do período."
        ).replace(",", ".")


@dataclass(frozen=True)
class Periodo:
    inicio: date
    fim: date
    rotulo: str
    # 💭 Quando o pedido não trouxe período e caímos no padrão, isto fica
    # `True` e a capa avisa. Nunca devolvemos pergunta ao corretor.
    e_padrao: bool = False

    @property
    def dias(self) -> int:
        return (self.fim - self.inicio).days + 1

    def anterior(self) -> "Periodo":
        """O período de MESMA duração imediatamente antes.

        Para um ano civil devolve o ano civil anterior — e não 365 dias para
        trás — porque comparar "2025" com "2024" é o que o corretor entende, e
        um deslocamento de 365 dias sobre ano bissexto criaria uma janela que
        não corresponde a nada.
        """
        if (self.inicio.month, self.inicio.day) == (1, 1) and \
           (self.fim.month, self.fim.day) == (12, 31) and \
           self.inicio.year == self.fim.year:
            a = self.inicio.year - 1
            return Periodo(date(a, 1, 1), date(a, 12, 31), str(a))
        d = self.dias
        fim = self.inicio - timedelta(days=1)
        ini = fim - timedelta(days=d - 1)
        return Periodo(ini, fim, f"{ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}")


# --------------------------------------------------------------------------
# Os cálculos
# --------------------------------------------------------------------------
def ranking_por_produtor(apolices: Sequence, mapa: Dict[str, object],
                         teto: int = 0) -> List[LinhaDoRanking]:
    """Quem vendeu quanto. Uma apólice conta UMA vez.

    🔴 O `visto` não é paranoia. Se a camada de dados algum dia devolver a
    mesma apólice em duas fatias de período (a fronteira do ano civil é o
    lugar óbvio), o total inflaria em silêncio — e "silêncio que infla número"
    é a família de defeito que mais custou nesta base.
    """
    acc: Dict[str, List[float]] = {}
    visto: set = set()
    for a in apolices:
        if a.nosnum in visto:
            continue
        visto.add(a.nosnum)
        p = mapa.get(a.nosnum)
        if p is None:
            continue
        nome = str(getattr(p, "nome", "") or "").strip()
        if not nome:
            continue
        linha = acc.setdefault(nome, [0.0, 0.0, 0.0, 0.0])
        linha[0] += 1
        linha[1] += a.premio
        linha[2] += a.comissao
        linha[3] += getattr(p, "repasse", 0.0)
    saida = [LinhaDoRanking(n, int(v[0]), v[1], v[2], v[3]) for n, v in acc.items()]
    saida.sort(key=lambda x: (-x.comissao, x.nome))
    return saida[:teto] if teto else saida


def cobertura(apolices: Sequence, mapa: Dict[str, object]) -> Cobertura:
    """Quanto do período tem vendedor conhecido. Sempre acompanha o ranking."""
    total = com = 0
    ct = ca = 0.0
    visto: set = set()
    for a in apolices:
        if a.nosnum in visto:
            continue
        visto.add(a.nosnum)
        total += 1
        ct += a.comissao
        if a.nosnum in mapa:
            com += 1
            ca += a.comissao
    return Cobertura(total, com, ct, ca)


def por_dimensao(apolices: Sequence, campo: str, teto: int = 0) -> List[Tuple[str, int, float]]:
    """Agrupa por seguradora ou ramo. Devolve `(rótulo, apólices, comissão)`.

    🔴 Normaliza o rótulo. 📊 A base tem `Allianz`, `allianz`, `ALLIANZ` e
    `Allianz Seguros` contando separado — 56 valores crus que viram ~30. Uma
    rosca com a mesma seguradora em quatro fatias não é gráfico, é defeito.
    """
    acc: Dict[str, List[float]] = {}
    rotulo_bonito: Dict[str, str] = {}
    for a in apolices:
        cru = str(getattr(a, campo, "") or "").strip()
        if not cru:
            cru = "(não informado)"
        chave = _normalizar(cru)
        rotulo_bonito.setdefault(chave, cru)
        linha = acc.setdefault(chave, [0.0, 0.0])
        linha[0] += 1
        linha[1] += a.comissao
    saida = [(rotulo_bonito[k], int(v[0]), v[1]) for k, v in acc.items()]
    saida.sort(key=lambda x: (-x[2], x[0]))
    return saida[:teto] if teto else saida


def novo_versus_renovacao(apolices: Sequence) -> Dict[str, Tuple[int, float]]:
    """Quanto do período é negócio novo e quanto é carteira que se manteve.

    📊 A chave é `nosnum_ren`: vazio = novo, preenchido = aponta a apólice
    anterior. 2025 mediu 717 novo / 963 renovação.
    """
    novo = [0, 0.0]
    renov = [0, 0.0]
    for a in apolices:
        alvo = renov if a.e_renovacao else novo
        alvo[0] += 1
        alvo[1] += a.comissao
    return {"novo": (int(novo[0]), novo[1]),
            "renovacao": (int(renov[0]), renov[1])}


def serie_mensal(apolices: Sequence) -> List[Tuple[str, int, float]]:
    """Comissão mês a mês, em ordem cronológica. `(AAAA-MM, apólices, R$)`."""
    acc: Dict[str, List[float]] = {}
    for a in apolices:
        m = _mes_de(a.inivig)
        if not m:
            continue
        linha = acc.setdefault(m, [0.0, 0.0])
        linha[0] += 1
        linha[1] += a.comissao
    return [(k, int(v[0]), v[1]) for k, v in sorted(acc.items())]


def comparar(atual: Sequence, anterior: Sequence) -> Dict[str, float]:
    """A variação entre dois períodos, em valor e em percentual.

    Devolve `delta_pct = 0.0` quando o período anterior foi zero, e não
    infinito: um cartão que mostra "∞%" não informa nada e quebra o layout.
    """
    ca = sum(x.comissao for x in atual)
    cb = sum(x.comissao for x in anterior)
    pa = sum(x.premio for x in atual)
    pb = sum(x.premio for x in anterior)
    return {
        "comissao_atual": ca, "comissao_anterior": cb,
        "comissao_delta": ca - cb,
        "comissao_delta_pct": (100.0 * (ca - cb) / cb) if cb else 0.0,
        "premio_atual": pa, "premio_anterior": pb,
        "premio_delta_pct": (100.0 * (pa - pb) / pb) if pb else 0.0,
        "apolices_atual": float(len(atual)), "apolices_anterior": float(len(anterior)),
    }


def projetar(serie: Sequence[Tuple[str, int, float]], meses_no_periodo: int) -> float:
    """Onde o período fecha, se o ritmo dos meses COMPLETOS se mantiver.

    🔴 Descarta o último mês da série. Mês em curso tem produção parcial, e
    projetar a partir dele subestima sempre — é o erro clássico de dashboard,
    e ele aparece como "queda" no gráfico todo dia primeiro.

    Devolve 0.0 quando não há dois meses completos: projeção sobre um ponto é
    adivinhação com cara de número.
    """
    if len(serie) < 3:
        return 0.0
    completos = list(serie)[:-1]
    media = sum(x[2] for x in completos) / len(completos)
    return media * meses_no_periodo


def por_vendedor_no_radar(vencimentos: Sequence, teto: int = 0) -> List[Tuple[str, int, float, int]]:
    """O Radar agrupado por VENDEDOR — `(nome, apólices, prêmio, dias_min)`.

    🔴 Foi pedido explícito do Founder: *"tem que ser por período, e separado
    por vendedor — quem tem mais renovações, comissões em jogo. Não do ano
    inteiro."*

    `dias_min` é o vencimento mais próximo daquele vendedor. Ordenar só por
    valor colocaria em cima quem tem muito dinheiro vencendo em 89 dias na
    frente de quem tem menos vencendo amanhã.
    """
    acc: Dict[str, List[float]] = {}
    for v in vencimentos:
        nome = str(getattr(v, "produtor", "") or "").strip() or "(sem produtor)"
        linha = acc.setdefault(nome, [0.0, 0.0, 9999.0])
        linha[0] += 1
        linha[1] += v.premio
        linha[2] = min(linha[2], float(v.dias_a_vencer))
    saida = [(n, int(v[0]), v[1], int(v[2])) for n, v in acc.items()]
    saida.sort(key=lambda x: (-x[2], x[0]))
    return saida[:teto] if teto else saida


def faixas_de_urgencia(vencimentos: Sequence) -> List[Tuple[str, int, float]]:
    """Quanto vence em cada janela. A ordem é cronológica, sempre."""
    faixas = [("vencidas", -99999, -1), ("até 15 dias", 0, 15),
              ("16 a 30 dias", 16, 30), ("31 a 60 dias", 31, 60),
              ("61 a 90 dias", 61, 90), ("mais de 90 dias", 91, 99999)]
    saida = []
    for rotulo, lo, hi in faixas:
        sel = [v for v in vencimentos if lo <= v.dias_a_vencer <= hi]
        if sel:
            saida.append((rotulo, len(sel), sum(v.premio for v in sel)))
    return saida


# --------------------------------------------------------------------------
# Entender o que o corretor digitou
# --------------------------------------------------------------------------
_MESES = {
    "janeiro": 1, "jan": 1, "fevereiro": 2, "fev": 2, "marco": 3, "mar": 3,
    "abril": 4, "abr": 4, "maio": 5, "mai": 5, "junho": 6, "jun": 6,
    "julho": 7, "jul": 7, "agosto": 8, "ago": 8, "setembro": 9, "set": 9,
    "outubro": 10, "out": 10, "novembro": 11, "nov": 11, "dezembro": 12, "dez": 12,
}


def entender_periodo(texto: str, hoje: Optional[date] = None,
                     padrao_dias_futuro: int = 0) -> Periodo:
    """Vira qualquer jeito de dizer um período numa janela de datas.

    🔴 **NUNCA levanta, NUNCA devolve pergunta.** Se não entender, cai no
    padrão e marca `e_padrao=True` para a capa avisar qual período foi usado.

    O motivo é de palco: o Founder vai digitar isso na frente de gente. Um
    relatório que responde "não entendi, qual período?" no meio de uma
    apresentação é pior que um relatório do período errado — o período errado
    ele corrige numa frase; a pergunta de volta quebra o ritmo e a confiança.

    `padrao_dias_futuro > 0` muda o padrão para uma janela À FRENTE (o Radar
    olha para o futuro; o Raio-X, para trás).
    """
    hoje = hoje or date.today()
    t = _normalizar(texto or "")

    if padrao_dias_futuro:
        padrao = Periodo(hoje, hoje + timedelta(days=padrao_dias_futuro),
                         f"próximos {padrao_dias_futuro} dias", e_padrao=True)
    else:
        padrao = Periodo(date(hoje.year, 1, 1), hoje, str(hoje.year), e_padrao=True)

    if not t:
        return padrao

    # "de 01/03/2026 a 30/06/2026"
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4}).{0,12}?(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        try:
            a = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            b = date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
            if b < a:
                a, b = b, a
            return Periodo(a, b, f"{a.strftime('%d/%m/%Y')} a {b.strftime('%d/%m/%Y')}")
        except ValueError:
            pass

    # "próximos 90 dias" / "nos ultimos 45 dias"
    m = re.search(r"(proximos?|ultimos?)\s+(\d{1,4})\s*dias", t)
    if m:
        n = int(m.group(2))
        if m.group(1).startswith("prox"):
            return Periodo(hoje, hoje + timedelta(days=n), f"próximos {n} dias")
        return Periodo(hoje - timedelta(days=n), hoje, f"últimos {n} dias")

    # "ultimos 12 meses"
    m = re.search(r"ultimos?\s+(\d{1,2})\s*meses", t)
    if m:
        n = int(m.group(1))
        ini = _somar_meses(hoje, -n)
        return Periodo(ini, hoje, f"últimos {n} meses")

    # "proximo trimestre" / "proximos 2 meses"
    m = re.search(r"proximos?\s+(\d{1,2})\s*meses", t)
    if m:
        n = int(m.group(1))
        return Periodo(hoje, _somar_meses(hoje, n), f"próximos {n} meses")

    # trimestre nomeado: "3o trimestre", "primeiro trimestre"
    tri = None
    for palavra, n in (("primeiro", 1), ("segundo", 2), ("terceiro", 3), ("quarto", 4)):
        if palavra + " trimestre" in t:
            tri = n
    m = re.search(r"([1-4])\s*[oº°]?\s*trimestre", t)
    if m:
        tri = int(m.group(1))
    if tri:
        ano = _ano_no_texto(t) or hoje.year
        ini = date(ano, 3 * tri - 2, 1)
        fim = _fim_do_mes(date(ano, 3 * tri, 1))
        return Periodo(ini, fim, f"{tri}º trimestre de {ano}")
    if "proximo trimestre" in t:
        return Periodo(hoje, _somar_meses(hoje, 3), "próximo trimestre")

    # semestre
    if "primeiro semestre" in t or "1o semestre" in t:
        ano = _ano_no_texto(t) or hoje.year
        return Periodo(date(ano, 1, 1), date(ano, 6, 30), f"1º semestre de {ano}")
    if "segundo semestre" in t or "2o semestre" in t:
        ano = _ano_no_texto(t) or hoje.year
        return Periodo(date(ano, 7, 1), date(ano, 12, 31), f"2º semestre de {ano}")

    # mês nomeado: "agosto", "agosto de 2025"
    for nome, num in _MESES.items():
        if re.search(rf"\b{nome}\b", t):
            ano = _ano_no_texto(t) or hoje.year
            ini = date(ano, num, 1)
            return Periodo(ini, _fim_do_mes(ini), f"{nome.capitalize()} de {ano}")

    # "este mes" / "mes passado"
    if "este mes" in t or "mes atual" in t or "esse mes" in t:
        ini = date(hoje.year, hoje.month, 1)
        return Periodo(ini, _fim_do_mes(ini), "este mês")
    if "mes passado" in t or "mes anterior" in t:
        ini = _somar_meses(date(hoje.year, hoje.month, 1), -1)
        return Periodo(ini, _fim_do_mes(ini), "mês passado")

    # "ano passado" / "este ano"
    if "ano passado" in t or "ano anterior" in t:
        a = hoje.year - 1
        return Periodo(date(a, 1, 1), date(a, 12, 31), str(a))
    if "este ano" in t or "ano atual" in t or "esse ano" in t:
        return Periodo(date(hoje.year, 1, 1), hoje, str(hoje.year))

    # um ano solto: "2025"
    ano = _ano_no_texto(t)
    if ano:
        fim = date(ano, 12, 31)
        if ano == hoje.year:
            fim = hoje
        return Periodo(date(ano, 1, 1), fim, str(ano))

    return padrao


# --------------------------------------------------------------------------
# Miudezas
# --------------------------------------------------------------------------
def _normalizar(s: str) -> str:
    """Minúsculas, sem acento, espaço colapsado. Para comparar, nunca para exibir."""
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def _ano_no_texto(t: str) -> Optional[int]:
    """Um ano plausível no texto. 2000-2099 — 📊 a base começa em 2018."""
    m = re.search(r"\b(20\d{2})\b", t)
    return int(m.group(1)) if m else None


def _mes_de(iso_ou_br: str) -> str:
    """`AAAA-MM` a partir do que a API devolver.

    📊 A InfoCap devolve data como `2025-03-14` em alguns campos e
    `14/03/2025` em outros. Aceitar as duas aqui evita um `if` em cada
    chamador — e é onde o defeito apareceria primeiro, calado, como um mês
    faltando no gráfico.
    """
    s = str(iso_ou_br or "").strip()
    m = re.match(r"(\d{4})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"\d{1,2}/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    return ""


def _fim_do_mes(d: date) -> date:
    return _somar_meses(date(d.year, d.month, 1), 1) - timedelta(days=1)


def _somar_meses(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    ano, mes = divmod(total, 12)
    mes += 1
    ultimo = [31, 29 if (ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)) else 28,
              31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1]
    return date(ano, mes, min(d.day, ultimo))


def _reais(v: float) -> str:
    """R$ 1,86 mi — curto o bastante para caber num cartão."""
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:.2f} mi".replace(".", ",")
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:.0f} mil"
    return f"R$ {v:.0f}"
