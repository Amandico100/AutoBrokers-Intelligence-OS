# -*- coding: utf-8 -*-
"""O PEDIDO de cálculo, saneado — SPEC-129-B U2.

`PedidoDeCalculo` é o que a porta CIFRA e o motor DECIFRA e entrega ao robô. Os grupos e os nomes dos campos são os
de `portal_worker/multicalculo/contrato.CAMPOS_DO_PEDIDO_AUTO` (a 128 os leu do `calcularV2`) — um catálogo só; este
módulo não inventa campo de formulário. A única extensão é `questionario.km_mensal` (o perfil que o canal PERGUNTA,
D-MC-59: garagem · uso · km · jovem), que o contrato ainda não tem (ver `CAMPOS_EXTRAS`).

⛔ Nada aqui é logado. `repr` de `PedidoDeCalculo` não mostra valores (CPF, nome, placa…): só grupos e contagens.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple

from portal_worker.multicalculo import presets as _presets
from portal_worker.multicalculo.contrato import (
    CAMPOS_DE_CODIGO_INTEIRO, CAMPOS_DE_CODIGO_TEXTO, CAMPOS_DO_PEDIDO_AUTO, CAMPOS_DO_PEDIDO_RE, CAMPOS_SIM_NAO,
    CODIGOS_MEDIDOS, CODIGOS_MEDIDOS_RE, RAMO_AUTO, RAMO_CONDOMINIO, RAMO_EMPRESARIAL, RAMO_RESIDENCIAL, RAMOS_RE,
    SEGURADORA_ANTERIOR_NO_AGGER, problemas_do_pedido_re, tipo_do_campo_re,
)

# ---------------------------------------------------------------------------------------------------------------------
# SPEC-129-C — os OUTROS RAMOS (RE: condomínio 16 · residencial 2 · empresarial 18). O catálogo, os códigos, os TIPOS e
# a VALIDAÇÃO do pedido de RE são do CONTRATO (F1, §3 da SPEC: `CAMPOS_DO_PEDIDO_RE`, `CODIGOS_MEDIDOS_RE`,
# `tipo_do_campo_re`, `problemas_do_pedido_re`) e as coberturas de cada opção dos PRESETS (`presets.coberturas_re`):
# este módulo só SANEIA a entrada para o tipo do contrato e pergunta ao contrato o que falta — um catálogo e um
# validador só (CLAUDE.md §5).
# ---------------------------------------------------------------------------------------------------------------------
RAMOS_ACEITOS: Tuple[int, ...] = (RAMO_AUTO,) + RAMOS_RE
#: a cobertura BÁSICA (incêndio/raio/explosão) — a dos presets (F1); o VALOR é o do PEDIDO (D-129C-03)
CHAVE_DA_BASICA: str = _presets.CHAVE_DA_BASICA


class RamoIndisponivel(ValueError):
    """O ramo não é calculável (fora de `RAMOS_ACEITOS`)."""


def catalogo_do_ramo(ramo: int) -> Dict[str, Tuple[Any, ...]]:
    """O catálogo {grupo: campos} do ramo (o auto: o de sempre + `CAMPOS_EXTRAS`; o RE: o do contrato)."""
    if ramo == RAMO_AUTO:
        return {**CAMPOS_DO_PEDIDO_AUTO, **CAMPOS_EXTRAS}
    if ramo not in CAMPOS_DO_PEDIDO_RE:
        raise RamoIndisponivel(f"ramo {ramo} não implementado (aceitos: {', '.join(map(str, RAMOS_ACEITOS))})")
    return dict(CAMPOS_DO_PEDIDO_RE[ramo])


def _nomes(entradas: Iterable[Any]) -> List[str]:
    return [str(e[0]) for e in entradas or ()]


#: Grupos do pedido que o motor entrega ao robô. `coberturas` e `pacotes` NÃO moram no pedido: cada CÁLCULO tem as
#: suas (`multicalculo_calculos.coberturas`, resolvidas pela porta por opção). Ficam no dict como `{}` para que as
#: chaves sejam SEMPRE as do contrato.
GRUPOS_DO_CALCULO: Tuple[str, ...] = ("coberturas", "pacotes")

#: 💭 extensão do contrato da 128 — o "km por mês" do questionário. O caminho no `calcularV2` não foi medido (a tela
#: preenche um padrão). Quem mapeia para o corpo é o robô (F2); sem o mapa, o valor só serve para a pergunta do canal.
CAMPOS_EXTRAS: Dict[str, Tuple[Tuple[str, str, Optional[bool]], ...]] = {
    "questionario": (("km_mensal", "a medir", None),),
}

#: O perfil que o canal PERGUNTA e o auxiliar ASSUME (D-MC-59 · D-128-07): (grupo, campo).
#: Não são obrigatórios na tela (📊 E3: a tela os preenche com padrões e calcula), mas mudam o preço.
CAMPOS_DE_PERFIL: Tuple[Tuple[str, str], ...] = (
    ("pernoite", "garagem_residencia"),   # garagem
    ("veiculo", "uso"),                   # uso
    ("questionario", "km_mensal"),        # km
    ("condutor", "jovem_condutor"),       # jovem condutor
)

#: SPEC-133-A D-133A-03 — no CANAL a PLACA supre FIPE, ano de fabricação e combustível (a pessoa sabe a placa; ninguém
#: sabe o código FIPE). 🔴 Por que é verdade (CLAUDE.md §9.5), lido no robô que monta o pedido ao Agger:
#:   · `portal_worker/multicalculo/agger_robo.py:178-179` o robô só exige `veiculo.placa` OU `veiculo.fipe`;
#:   · `agger_robo.py:310-311` com placa ele chama `/calculo/buscaPlaca` e usa a FIPE dela (`fipe = auto.fipe || bp.fipe`);
#:   · `montador.js:121-129` preenche `anoFabricacao` (bp.anoFab||anoMod), `fipe` (bp.fipe) e `combustivel` (Flex→6 da
#:     tabela FIPE) quando o pedido NÃO os traz — "o pedido VENCE; os GETs preenchem".
#: ⚠️ combustível ≠ Flex fica nulo no montador (📊 só Flex=6 medido) — o Agger decide; a porta não inventa código.
#: Só na origem `canal`; a carteira (auxiliar/teste) continua exigindo os três.
CAMPOS_QUE_A_PLACA_SUPRE: Tuple[Tuple[str, str], ...] = (
    ("veiculo", "fipe"), ("veiculo", "ano_fabricacao"), ("veiculo", "combustivel"),
)

_CATALOGO: Dict[str, Tuple[str, ...]] = {
    grupo: tuple(c[0] for c in campos)
    for grupo, campos in {**CAMPOS_DO_PEDIDO_AUTO, **CAMPOS_EXTRAS}.items()
}

#: Os 16 obrigatórios da E3 (📊 `contrato.CAMPOS_DO_PEDIDO_AUTO`, `obrigatorio=True`).
OBRIGATORIOS: Tuple[Tuple[str, str], ...] = tuple(
    (grupo, nome)
    for grupo, campos in CAMPOS_DO_PEDIDO_AUTO.items()
    for (nome, _caminho, obrigatorio) in campos
    if obrigatorio is True
)

_SO_DIGITOS = {("segurado", "cpf_cnpj"), ("condutor", "cpf"), ("segurado", "cep"), ("pernoite", "cep_pernoite"),
               ("segurado", "telefone")}
_DATAS = {("segurado", "nascimento"), ("condutor", "nascimento"), ("renovacao", "fim_vigencia_anterior"),
          ("renovacao", "vigencia_inicio"), ("renovacao", "vigencia_fim")}


class CampoDesconhecido(ValueError):
    """Um campo fora do catálogo do contrato. A mensagem traz o NOME do campo, nunca o valor."""


def _vazio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _chave_de_texto(texto: str) -> str:
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in bruto if not unicodedata.combining(c)).strip().lower()


_INTEIROS = frozenset(CAMPOS_DE_CODIGO_INTEIRO)
_DIGITOS_TEXTO = frozenset(CAMPOS_DE_CODIGO_TEXTO)
_SIM_NAO = frozenset(CAMPOS_SIM_NAO)
_SIM = {"sim", "s", "true", "verdadeiro", "1"}
_NAO = {"nao", "n", "false", "falso", "0"}
_NOMES_NO_AGGER = {_chave_de_texto(n): n for n in SEGURADORA_ANTERIOR_NO_AGGER.values()}


def _codificar(grupo: str, nome: str, valor: Any) -> Any:
    """F4 (costura porta × robô): o valor no FORMATO que o robô manda ao Agger — código de lista, inteiro,
    dígitos, sim/não, nome da seguradora anterior na lista do Agger. O que não tem código MEDIDO volta como veio
    e `PedidoDeCalculo.sem_codigo()` o aponta (a porta recusa como `PedidoIncompleto`)."""
    chave = (grupo, nome)
    mapa = CODIGOS_MEDIDOS.get(chave)
    if mapa is not None and isinstance(valor, str) and _chave_de_texto(valor) in mapa:
        return mapa[_chave_de_texto(valor)]
    if chave in _INTEIROS:
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, int):
            return valor
        if isinstance(valor, float) and valor.is_integer():
            return int(valor)
        if isinstance(valor, str) and valor.strip().isdigit():
            return int(valor.strip())
        return valor
    if chave in _DIGITOS_TEXTO:
        if isinstance(valor, int) and not isinstance(valor, bool):
            return str(valor)
        return valor
    if chave in _SIM_NAO and isinstance(valor, str):
        k = _chave_de_texto(valor)
        return True if k in _SIM else False if k in _NAO else valor
    if chave == ("renovacao", "seguradora_anterior"):
        texto = str(valor).strip()
        if texto in SEGURADORA_ANTERIOR_NO_AGGER:                 # o coenti da SUSEP
            return SEGURADORA_ANTERIOR_NO_AGGER[texto]
        return _NOMES_NO_AGGER.get(_chave_de_texto(texto), valor)
    return valor


def _tem_codigo(grupo: str, nome: str, valor: Any) -> bool:
    chave = (grupo, nome)
    if chave in _INTEIROS:
        return isinstance(valor, int) and not isinstance(valor, bool)
    if chave in _DIGITOS_TEXTO:
        return isinstance(valor, str) and valor.isdigit()
    if chave in _SIM_NAO:
        return isinstance(valor, bool)
    mapa = CODIGOS_MEDIDOS.get(chave)
    if mapa is not None:
        return valor in set(mapa.values())
    if chave == ("renovacao", "seguradora_anterior"):
        return valor in set(SEGURADORA_ANTERIOR_NO_AGGER.values())
    return True


def _sanear(grupo: str, nome: str, valor: Any) -> Any:
    saneado = _sanear_bruto(grupo, nome, valor)
    return saneado if saneado is None else _codificar(grupo, nome, saneado)


def _sanear_bruto(grupo: str, nome: str, valor: Any) -> Any:
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        return (valor.date() if isinstance(valor, datetime) else valor).isoformat()
    if isinstance(valor, str):
        texto = unicodedata.normalize("NFC", valor).strip()
        if not texto:
            return None
        if (grupo, nome) in _SO_DIGITOS:
            return re.sub(r"\D", "", texto) or None
        if (grupo, nome) == ("veiculo", "placa"):
            return re.sub(r"[^A-Z0-9]", "", texto.upper()) or None
        if (grupo, nome) == ("veiculo", "chassi"):
            return re.sub(r"[^A-Z0-9]", "", texto.upper()) or None
        if (grupo, nome) in _DATAS:
            m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", texto)
            if m:
                return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        return texto
    if isinstance(valor, (bool, int, float)):
        return valor
    raise CampoDesconhecido(f"{grupo}.{nome}: tipo de valor não aceito ({type(valor).__name__})")


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-129-C — o saneamento do pedido de RE
# ---------------------------------------------------------------------------------------------------------------------
def _monetario(valor: Any) -> Any:
    """R$ → número: 1500000 · 1500000.0 · "1.500.000,00" · "R$ 1.500.000" · "1500000". O que não é número volta
    como veio (e `sem_codigo` o aponta)."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        t = re.sub(r"[R$\s]", "", valor)
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?|\d+(,\d{1,2})?", t):
            return float(t.replace(".", "").replace(",", "."))
        if re.fullmatch(r"\d+\.\d{1,2}", t):
            return float(t)
    return valor


def _inteiro_ou(valor: Any) -> Any:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, str) and valor.strip().isdigit():
        return int(valor.strip())
    return valor


def _codigo(ramo: int, nome: str, valor: Any, *, texto: bool) -> Any:
    """Rótulo da tela → código medido (`contrato.CODIGOS_MEDIDOS_RE[(ramo, campo)]`); número → o código no TIPO dele."""
    mapa = CODIGOS_MEDIDOS_RE.get((ramo, nome)) or {}
    if isinstance(valor, str) and _chave_de_texto(valor) in mapa:
        return mapa[_chave_de_texto(valor)]
    if texto:
        return str(valor) if isinstance(valor, int) and not isinstance(valor, bool) else valor
    return _inteiro_ou(valor)


def _sanear_re(ramo: int, grupo: str, nome: str, valor: Any) -> Any:
    """A entrada no TIPO que o contrato pede (`contrato.tipo_do_campo_re`). O que não converte volta como veio e o
    validador do contrato (`problemas_do_pedido_re`) o aponta — a porta recusa como `PedidoIncompleto`."""
    tipo = tipo_do_campo_re(grupo, nome)
    if tipo == "mapa_de_cobertura":
        return _extras(valor)
    if tipo == "dinheiro":
        return None if valor is None or (isinstance(valor, str) and not valor.strip()) else _monetario(valor)
    if tipo == "lista_de_codigos":
        if valor is None:
            return None
        itens = valor if isinstance(valor, (list, tuple)) else [valor]
        return [_codigo(ramo, nome, i.strip() if isinstance(i, str) else i, texto=False) for i in itens]
    if isinstance(valor, (list, dict, tuple)):
        raise CampoDesconhecido(f"{grupo}.{nome}: tipo de valor não aceito ({type(valor).__name__})")
    if tipo == "digitos":
        if isinstance(valor, int) and not isinstance(valor, bool):
            return str(valor)
        return re.sub(r"\D", "", valor) or None if isinstance(valor, str) else valor
    if tipo == "data":
        return _sanear_bruto("renovacao", "vigencia_inicio", valor)     # dd/mm/aaaa ou date → AAAA-MM-DD
    saneado = _sanear_bruto(grupo, nome, valor)
    if saneado is None:
        return None
    if tipo == "booleano" and isinstance(saneado, str):                # "não" nunca vira VERDADEIRO
        k = _chave_de_texto(saneado)
        return True if k in _SIM else False if k in _NAO else saneado
    if tipo == "inteiro":
        return _inteiro_ou(saneado)
    if tipo in ("codigo", "codigo_texto"):
        return _codigo(ramo, nome, saneado, texto=tipo == "codigo_texto")
    if (grupo, nome) == ("renovacao", "seguradora_anterior"):
        return _codificar(grupo, nome, saneado)                         # a mesma lista do Agger do auto
    if tipo == "texto" and isinstance(saneado, (int, float)) and not isinstance(saneado, bool):
        return str(int(saneado)) if float(saneado).is_integer() else str(saneado)   # 📊 anoFundacao "2005"
    return saneado


def _extras(valor: Any) -> Dict[str, Any]:
    """`risco.extras` = {chave de cobertura do Agger: valor em R$} — opcional (§3). Chave vazia/não-texto recusa."""
    if valor is None:
        return {}
    if not isinstance(valor, Mapping):
        raise CampoDesconhecido("risco.extras: esperava {cobertura: valor}")
    saida: Dict[str, Any] = {}
    for k, v in valor.items():
        if not isinstance(k, str) or not k.strip():
            raise CampoDesconhecido("risco.extras: chave de cobertura inválida")
        if v is not None:
            saida[k.strip()] = _monetario(v)
    return saida


@dataclass(frozen=True)
class PedidoDeCalculo:
    """O pedido saneado. Construa com `PedidoDeCalculo.de_dict(...)` ou `de_apolice(...)`.

    `campos`    {grupo: {campo: valor}} — só nomes do catálogo; vazio vira ausente.
    `assumidos` "grupo.campo" que NÃO vieram de quem pediu: valor deduzido (condutor = segurado, CEP de pernoite =
                CEP) ou deixado para o PADRÃO da tela (perfil, na origem auxiliar). O robô e a página mostram o que foi
                assumido; ninguém apresenta um assumido como dito pelo cliente.
    `avisos`    SPEC-130-B F4: o que o CORRETOR confere antes de cotar (códigos `AVISO_*`, nunca valores) — ex.: a
                ficha da apólice anterior cuja leitura não fechou. ⛔ NÃO vão em `para_dict()`: o contrato do robô não
                muda; quem mostra é quem chamou (a 131).
    """

    campos: Mapping[str, Mapping[str, Any]]
    ramo: int = RAMO_AUTO
    seguradoras: Tuple[int, ...] = ()
    assumidos: FrozenSet[str] = frozenset()
    avisos: FrozenSet[str] = frozenset()

    def __repr__(self) -> str:  # ⛔ nunca os valores
        preenchidos = sum(1 for g in self.campos.values() for v in g.values() if not _vazio(v))
        avisos = f", avisos={sorted(self.avisos)}" if self.avisos else ""
        return (f"PedidoDeCalculo(ramo={self.ramo}, grupos={sorted(self.campos)}, preenchidos={preenchidos}, "
                f"assumidos={len(self.assumidos)}{avisos})")

    __str__ = __repr__

    # ------------------------------------------------------------------ construção
    @classmethod
    def de_dict(cls, dados: Mapping[str, Any], *, ramo: int = RAMO_AUTO,
                seguradoras: Iterable[int] = (), assumidos: Iterable[str] = ()) -> "PedidoDeCalculo":
        if ramo != RAMO_AUTO:
            return cls._de_dict_re(dados, ramo=int(ramo), seguradoras=seguradoras, assumidos=assumidos)
        campos: Dict[str, Dict[str, Any]] = {}
        for grupo, valores in (dados or {}).items():
            if grupo in ("ramo", "seguradoras", "assumidos"):
                continue
            if grupo not in _CATALOGO:
                raise CampoDesconhecido(f"grupo desconhecido: {grupo}")
            if grupo in GRUPOS_DO_CALCULO:
                if valores:
                    raise CampoDesconhecido(f"{grupo} é do CÁLCULO (coberturas por opção), não do pedido")
                continue
            if not isinstance(valores, Mapping):
                raise CampoDesconhecido(f"{grupo}: esperava um objeto de campos")
            for nome, valor in valores.items():
                if nome not in _CATALOGO[grupo]:
                    raise CampoDesconhecido(f"campo desconhecido: {grupo}.{nome}")
                saneado = _sanear(grupo, nome, valor)
                if not _vazio(saneado):
                    campos.setdefault(grupo, {})[nome] = saneado
        for a in assumidos:
            g, _, n = str(a).partition(".")
            if g not in _CATALOGO or n not in _CATALOGO[g]:
                raise CampoDesconhecido(f"assumido desconhecido: {a}")
        segs = tuple(sorted({int(s) for s in seguradoras}))
        return cls(campos=campos, ramo=ramo, seguradoras=segs, assumidos=frozenset(str(a) for a in assumidos))

    @classmethod
    def _de_dict_re(cls, dados: Mapping[str, Any], *, ramo: int, seguradoras: Iterable[int],
                    assumidos: Iterable[str]) -> "PedidoDeCalculo":
        """SPEC-129-C: o pedido de RE (§3: `segurado` + `risco` + `renovacao`…), validado contra o catálogo DO RAMO
        no contrato. Os campos de lista viram o CÓDIGO medido (`CODIGOS_MEDIDOS_RE`); o que não tem código fica como
        veio e `sem_codigo()` o aponta. `risco.extras` é um dict {cobertura: R$}."""
        cat = catalogo_do_ramo(ramo)
        nomes = {g: set(_nomes(c)) for g, c in cat.items()}
        campos: Dict[str, Dict[str, Any]] = {}
        for grupo, valores in (dados or {}).items():
            if grupo in ("ramo", "seguradoras", "assumidos"):
                continue
            if grupo not in cat:
                raise CampoDesconhecido(f"grupo desconhecido no ramo {ramo}: {grupo}")
            if grupo in GRUPOS_DO_CALCULO:
                if valores:
                    raise CampoDesconhecido(f"{grupo} é do CÁLCULO (coberturas por opção), não do pedido")
                continue
            if not isinstance(valores, Mapping):
                raise CampoDesconhecido(f"{grupo}: esperava um objeto de campos")
            for nome, valor in valores.items():
                if nome not in nomes[grupo]:
                    raise CampoDesconhecido(f"campo desconhecido no ramo {ramo}: {grupo}.{nome}")
                saneado = _sanear_re(ramo, grupo, nome, valor)
                if not _vazio(saneado) and saneado not in ({}, []):
                    campos.setdefault(grupo, {})[nome] = saneado
        for a in assumidos:
            g, _, n = str(a).partition(".")
            if g not in nomes or n not in nomes[g]:
                raise CampoDesconhecido(f"assumido desconhecido: {a}")
        segs = tuple(sorted({int(s) for s in seguradoras}))
        return cls(campos=campos, ramo=ramo, seguradoras=segs, assumidos=frozenset(str(a) for a in assumidos))

    @property
    def e_re(self) -> bool:
        return self.ramo != RAMO_AUTO

    def com_comissao(self, percentual: float) -> "PedidoDeCalculo":
        """RE (D-129C-05): a comissão EXPLÍCITA do item — a da config do ramo (a porta a dá), quando quem pediu não a
        deu. O contrato a exige no RE: sem ela o Agger usaria a da conta (📊 0 % no empresarial)."""
        if not self.e_re or not _vazio(self.valor("comissao_desconto", "comissao_percentual")):
            return self
        campos = {g: dict(v) for g, v in self.campos.items()}
        campos.setdefault("comissao_desconto", {})["comissao_percentual"] = float(percentual)
        return replace(self, campos=campos)

    def _problemas_re(self) -> Tuple[List[str], List[str]]:
        """(faltando, sem código) do pedido de RE, pelo VALIDADOR DO CONTRATO (`problemas_do_pedido_re`): "g.c" é
        obrigatório ausente; "g.c:motivo" é valor sem código/tipo. + as extras fora das coberturas do ramo (e a
        básica, que é `risco.valor_basica`, nunca uma extra)."""
        faltam, sem = [], []
        for item in problemas_do_pedido_re(self.para_dict()):
            nome, _, motivo = item.partition(":")
            (sem if motivo else faltam).append(nome)
        validas = set(_presets.CHAVES_DE_COBERTURA_RE.get(self.ramo, ())) - {"assist24hs", CHAVE_DA_BASICA}
        sem += [f"risco.extras.{k}" for k in (self.valor("risco", "extras") or {}) if k not in validas]
        return faltam, sorted(set(sem))

    # ------------------------------------------------------------------ leitura
    def valor(self, grupo: str, nome: str) -> Any:
        return (self.campos.get(grupo) or {}).get(nome)

    def supridos_pela_placa(self, origem: Optional[str] = None) -> FrozenSet[str]:
        """D-133A-03: na origem `canal`, com placa, os campos de `CAMPOS_QUE_A_PLACA_SUPRE` ausentes ficam com o robô."""
        if origem != "canal" or _vazio(self.valor("veiculo", "placa")):
            return frozenset()
        return frozenset(f"{g}.{n}" for (g, n) in CAMPOS_QUE_A_PLACA_SUPRE if _vazio(self.valor(g, n)))

    def assumindo_pela_placa(self) -> "PedidoDeCalculo":
        """O que a placa supre vira `assumido` ("o Agger preenche pela placa") — nunca valor inventado."""
        novos = self.supridos_pela_placa("canal")
        if not novos:
            return self
        return replace(self, assumidos=frozenset(self.assumidos | novos))

    def faltando(self, *, origem: Optional[str] = None) -> List[str]:
        """Os obrigatórios da E3 que faltam, como "grupo.campo" (nomes, nunca valores). `origem='canal'`: a placa
        supre FIPE/ano/combustível (D-133A-03). RE (SPEC-129-C): o que o CONTRATO diz que falta."""
        if self.e_re:
            return self._problemas_re()[0]
        supridos = self.supridos_pela_placa(origem)
        faltam = [f"{g}.{n}" for (g, n) in OBRIGATORIOS if _vazio(self.valor(g, n)) and f"{g}.{n}" not in supridos]
        # F4: o robô recusa a renovação sem a seguradora anterior (`cotacao_do_pedido`) — a porta pergunta antes
        if self.renovacao and _vazio(self.valor("renovacao", "seguradora_anterior")):
            faltam.append("renovacao.seguradora_anterior")
        return faltam

    def sem_codigo(self) -> List[str]:
        """F4: os campos PRESENTES cujo valor não tem código medido no Agger (`contrato.CODIGOS_MEDIDOS`) — o robô
        os recusaria só no disparo. A porta os devolve como `PedidoIncompleto` (nomes, nunca valores)."""
        if self.e_re:
            return self._problemas_re()[1]
        return sorted(f"{g}.{n}" for g, campos in self.campos.items() for n, v in campos.items()
                      if not _vazio(v) and not _tem_codigo(g, n, v))

    def perfil_faltando(self) -> List[str]:
        if self.e_re:
            return []                     # o perfil do canal (garagem, uso, km, jovem) é do AUTO
        return [f"{g}.{n}" for (g, n) in CAMPOS_DE_PERFIL
                if _vazio(self.valor(g, n)) and f"{g}.{n}" not in self.assumidos]

    def assumindo_perfil(self) -> "PedidoDeCalculo":
        """O perfil que falta vira `assumido` (fica para o PADRÃO da tela) — a origem auxiliar (D-128-07)."""
        novos = {f"{g}.{n}" for (g, n) in CAMPOS_DE_PERFIL if _vazio(self.valor(g, n))}
        return replace(self, assumidos=frozenset(self.assumidos | novos))

    @property
    def documento(self) -> str:
        return str(self.valor("segurado", "cpf_cnpj") or "")

    @property
    def renovacao(self) -> bool:
        return self.valor("renovacao", "renovacao") is True

    def para_dict(self) -> Dict[str, Any]:
        """O que o MOTOR decifra e entrega ao robô (`agger_robo.disparar(sessao, pedido, coberturas)`).

        Formato (JSON puro, estável):
            {
              "ramo": 31,
              "segurado":          {campo: valor, ...},   # nomes de contrato.CAMPOS_DO_PEDIDO_AUTO["segurado"]
              "veiculo":           {...},                  # idem "veiculo"
              "pernoite":          {...},
              "condutor":          {...},                  # UM condutor (o principal)
              "renovacao":         {...},                  # renovacao=True quando vem de `de_apolice`
              "coberturas":        {},                     # SEMPRE vazio: as do CÁLCULO vêm de calculos.coberturas
              "pacotes":           {},                     # SEMPRE vazio (idem; E20)
              "comissao_desconto": {...},
              "questionario":      {"km_mensal": ...},     # extensão (CAMPOS_EXTRAS), pode vir vazio
              "seguradoras":       [códigos int],          # vazio = todas as habilitadas na conta
              "assumidos":         ["grupo.campo", ...],   # ordenado
            }
        Datas em ISO (AAAA-MM-DD); CPF/CEP/telefone só dígitos; placa e chassi em maiúsculas sem separador. Campo
        ausente NÃO aparece (o robô deixa a tela com o padrão dela). Todas as chaves de grupo aparecem sempre.
        """
        saida: Dict[str, Any] = {"ramo": self.ramo}
        if self.e_re:
            # SPEC-129-C: as chaves de grupo são as do catálogo DO RAMO (§3: segurado · risco · renovacao …);
            # `risco.extras` sai como {cobertura: R$}
            # (a forma de `contrato.PedidoDeCalculoRE.para_dict`: + "coberturas"/"pacotes" sempre vazios)
            for grupo in catalogo_do_ramo(self.ramo):
                saida[grupo] = {k: (dict(v) if isinstance(v, Mapping) else list(v) if isinstance(v, list) else v)
                                for k, v in (self.campos.get(grupo) or {}).items()}
            saida.update({"seguradoras": list(self.seguradoras), "assumidos": sorted(self.assumidos),
                          "coberturas": {}, "pacotes": {}})
            return saida
        for grupo in _CATALOGO:
            saida[grupo] = {} if grupo in GRUPOS_DO_CALCULO else dict(self.campos.get(grupo) or {})
        saida["seguradoras"] = list(self.seguradoras)
        saida["assumidos"] = sorted(self.assumidos)
        return saida


# ---------------------------------------------------------------------------------------------------------------------
# A RENOVAÇÃO a partir da FICHA ÚNICA da apólice (SPEC-129-B G13 · SPEC-130-B F4)
# ---------------------------------------------------------------------------------------------------------------------
#: SPEC-130-B F4 — família da porta (`policy_data_provider.familia_de_ramo`) → o ramo do Agger (`contrato.RAMO_*`).
#: 🔴 Por que está certo (CLAUDE.md §9.5): "resi"/"cond"/"empr" são as famílias dos sinônimos residencial/condomínio/
#: empresarial em `FAMILIAS_DE_RAMO`, e o contrato da 129-C chama esses MESMOS ramos de 2/16/18 (lidos do formulário de
#: cada ramo no Agger). Família fora daqui (vida, viagem, saúde…) não tem pedido no Agger → `RamoIndisponivel`.
#: `None` ("não sei", a abreviatura fora do agrupamento) segue como AUTO — o comportamento de antes da F4 (controle).
RAMO_DO_AGGER_POR_FAMILIA: Dict[str, int] = {
    "auto": RAMO_AUTO, "resi": RAMO_RESIDENCIAL, "cond": RAMO_CONDOMINIO, "empr": RAMO_EMPRESARIAL,
}

#: O grupo de `providers/rotulos_de_cobertura.json` que É a Básica. 🔴 Por que: `basica_simples` reúne "incendio raio
#: explosao" e "basica simples" (📊 Allianz condomínio do golden, LMI igual nos dois lados) — a cobertura que o Agger
#: chama `isDanosIncendioRaioExplosao` (`presets.CHAVE_DA_BASICA`). Um rótulo de OUTRO grupo declarado (📊
#: `incendio_bens_condominos`, que no Agger é outra chave: `isDanosIncendioRaioExplosaoCond`) nunca é a Básica.
GRUPO_DA_BASICA: str = "basica_simples"
#: Rótulo FORA do catálogo (o catálogo só tem 2 grafias, as da Allianz): é a Básica quando nomeia o incêndio E o raio
#: ou a explosão — 📊 as grafias medidas em `programa-multicalculo/129-C/RAMOS-NA-INFOCAP.md` §3.1–3.3: "Incêndio / raio
#: / explosão / fumaça" (residencial 13/13), "… / fumaça / aeronave" (condomínio Tokio, empresarial Sura) — ou quando
#: se diz "básica" ("Básica Simples"/"Cobertura Básica").
_PALAVRAS_DO_INCENDIO = frozenset({"incendio"})
_PALAVRAS_DO_RAIO_OU_EXPLOSAO = frozenset({"raio", "explosao"})
#: ⛔ e NUNCA quando nomeia outra coisa: 📊 "Incêndio de bens dos condôminos" (condomínio Tokio, R$ 2 mi ao lado da
#: Básica de R$ 17,6 mi) e a "Assistência … Básica" (é o NÍVEL da assistência, `presets.ASSISTENCIA_RE`, não a Básica).
_PALAVRAS_QUE_NAO_SAO_A_BASICA = frozenset({"bens", "condominos", "condomino", "condomin", "assistencia",
                                            "assitencia", "assist", "franquia"})

#: Os AVISOS do pedido (`PedidoDeCalculo.avisos`) — o corretor confere antes de cotar; nenhum RECUSA o pedido.
#: a leitura do documento não fechou (F1: `Sinal("documento_nao_conferido")` ou `leitura.estado` ≠ "fechou")
AVISO_COBERTURAS_NAO_CONFERIDAS = "coberturas_nao_conferidas"
#: nenhuma cobertura veio do documento: a Básica é a do CADASTRO (📊 `/itens` traz garantias em só 4 de 15 documentos)
AVISO_COBERTURAS_DO_CADASTRO = "coberturas_do_cadastro"
#: duas linhas que são a Básica, com limites diferentes (ex.: prédio e conteúdo) — nenhuma é escolhida
AVISO_BASICA_AMBIGUA = "basica_ambigua"
#: a config da corretora não tem o reajuste da Básica para o ramo — a anterior NÃO vai "sem reajuste"
AVISO_SEM_REGRA_DE_REAJUSTE = "sem_regra_de_reajuste"
#: o documento lido é endosso/proposta/cotação/CRLV (F1 `tipo_de_documento`), não a apólice
AVISO_DOCUMENTO_NAO_E_A_APOLICE = "documento_nao_e_a_apolice"
#: AUTO: a placa do cadastro e a do documento diferem (o endosso troca o carro; vale a do cadastro)
AVISO_PLACA_DIVERGE = "placa_diverge_do_documento"

#: o sinal que a F1 acende em `reconciliar` (SPEC-130-B §4) e os tipos de documento da F1 que não são a apólice
SINAL_DOCUMENTO_NAO_CONFERIDO = "documento_nao_conferido"
_TIPOS_QUE_NAO_SAO_A_APOLICE = frozenset({"endosso", "proposta", "cotacao", "crlv"})


class FichaIncompleta(ValueError):
    """`de_apolice(..., exigir_completo=True)`: a ficha + o perfil não fecham o pedido. `faltando` = "grupo.campo"
    (NOMES, nunca valores) — a mesma lista que a porta devolveria como `PedidoIncompleto`."""

    def __init__(self, faltando: Iterable[str], *, avisos: Iterable[str] = ()):
        self.faltando = list(faltando)
        self.avisos = sorted(set(avisos))
        super().__init__("a ficha da apólice não fecha o pedido de renovação; falta: " + ", ".join(self.faltando))


def _valor_de(campo: Any) -> Any:
    """Um `CampoComOrigem` (ou None) → o valor, ou None se indisponível."""
    if campo is None:
        return None
    if getattr(campo, "tem_valor", False):
        return campo.valor
    return None


def _cru(valor: Any) -> Any:
    """Valor do objeto do risco: aceita o valor puro ou um `CampoComOrigem` (a F1 pode entregar qualquer um)."""
    if valor is None:
        return None
    if hasattr(valor, "tem_valor") and hasattr(valor, "origem"):
        return _valor_de(valor)
    return None if isinstance(valor, str) and not valor.strip() else valor


def _mais_um_ano(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:            # 29/02
        return d.replace(year=d.year + 1, day=28)


def _objeto_do_risco(apolice: Any, ficha: Any) -> Dict[str, Any]:
    """O objeto do risco da FICHA (`ApoliceDocumental.objeto_do_risco`, F1) — ou o que a porta pôr na `Apolice`.
    Leitura tolerante: ficha de antes da 130-B (sem o campo) → {}."""
    for fonte in (ficha, apolice):
        obj = getattr(fonte, "objeto_do_risco", None) if fonte is not None else None
        if isinstance(obj, Mapping) and obj:
            return {str(k): _cru(v) for k, v in obj.items() if _cru(v) is not None}
    return {}


def _avisos_da_leitura(apolice: Any, ficha: Any) -> set:
    avisos: set = set()
    sinais = getattr(apolice, "sinais", None) or ()
    if any(getattr(s, "codigo", None) == SINAL_DOCUMENTO_NAO_CONFERIDO for s in sinais):
        avisos.add(AVISO_COBERTURAS_NAO_CONFERIDAS)
    leitura = getattr(ficha, "leitura", None) if ficha is not None else None
    if isinstance(leitura, Mapping) and str(leitura.get("estado") or "") not in ("", "fechou"):
        avisos.add(AVISO_COBERTURAS_NAO_CONFERIDAS)
    tipo = getattr(ficha, "tipo_documento", None) if ficha is not None else None
    if tipo and _chave_de_texto(tipo) in _TIPOS_QUE_NAO_SAO_A_APOLICE:
        avisos.add(AVISO_DOCUMENTO_NAO_E_A_APOLICE)
    return avisos


def e_a_cobertura_basica(cobertura: Any) -> bool:
    """A cobertura é a Básica (incêndio/raio/explosão)? Pelo GRUPO declarado; sem grupo, pelas palavras do rótulo."""
    from app.providers.policy_data_provider import grupo_de_rotulo, normalizar_rotulo

    rotulo = getattr(cobertura, "rotulo", "") or ""
    gid = getattr(cobertura, "grupo", None) or grupo_de_rotulo(rotulo)
    if gid:
        return gid == GRUPO_DA_BASICA
    palavras = set(normalizar_rotulo(rotulo).split())
    if palavras & _PALAVRAS_QUE_NAO_SAO_A_BASICA:
        return False
    return bool((palavras & _PALAVRAS_DO_INCENDIO and palavras & _PALAVRAS_DO_RAIO_OU_EXPLOSAO)
                or "basica" in palavras)


def coberturas_da_ficha(apolice: Any) -> Tuple[Dict[str, Any], ...]:
    """As coberturas da ficha (a `Apolice` reconciliada) para o corretor CONFERIR: rótulo, limite, de onde veio e se é
    a Básica. ⛔ Só rótulo e dinheiro — a cobertura não carrega dado pessoal."""
    saida = []
    for c in getattr(apolice, "coberturas", None) or ():
        limite = getattr(c, "limite", None)
        saida.append({"rotulo": getattr(c, "rotulo", ""), "limite": _valor_de(limite),
                      "origem": getattr(limite, "origem", None), "basica": e_a_cobertura_basica(c)})
    return tuple(saida)


def _basica_da_ficha(apolice: Any) -> Tuple[Optional[Decimal], Optional[str], bool]:
    """(limite da Básica, origem, ambígua). Duas Básicas com limites DIFERENTES → (None, None, True): nunca escolhe.

    🔴 O DOCUMENTO vence o cadastro (a regra de `reconciliar` para cobertura/limite): havendo Básica lida do documento,
    só ela conta. 📊 Sem isso, um rótulo do cadastro que o catálogo casa ("INCENDIO RAIO EXPLOSAO") e um do PDF que ele
    não casa ("Incêndio, Raio e Explosão") ficam LADO A LADO depois de `reconciliar` — e o limite antigo do cadastro
    empataria com o do documento (o teste do fio residencial nasceu vermelho por isso)."""
    achadas = [c for c in coberturas_da_ficha(apolice)
               if c["basica"] and isinstance(c["limite"], (Decimal, int, float)) and not isinstance(c["limite"], bool)
               and c["limite"] > 0]
    do_documento = [c for c in achadas if c["origem"] == "documento_oficial"]
    achadas = do_documento or achadas
    valores = {Decimal(str(c["limite"])) for c in achadas}
    if len(valores) > 1:
        return None, None, True
    if not valores:
        return None, None, False
    origens = {c["origem"] for c in achadas}
    return valores.pop(), ("documento_oficial" if "documento_oficial" in origens else next(iter(origens))), False


def _renovacao_da_apolice(apolice: Any, renov: Dict[str, Any]) -> Dict[str, Any]:
    """O bloco `renovacao` (AUTO e RE): número, seguradora anterior (o NOME da lista do Agger), vigência nova."""
    renov = dict(renov)
    renov["renovacao"] = True
    numero = str(getattr(apolice, "numero_humano", "") or "").strip()
    if numero and not renov.get("numero_apolice_anterior"):
        renov["numero_apolice_anterior"] = numero
    seg = getattr(apolice, "seguradora", None)
    if seg is not None and not renov.get("seguradora_anterior"):
        # F4 (junta 4): o robô procura a anterior em `seguradorasRenovacao` pelo NOME — vai o nome EXATO da lista do
        # Agger, pelo coenti (`contrato.SEGURADORA_ANTERIOR_NO_AGGER`). Sem linha na tabela → fica faltando e a porta
        # pergunta (`PedidoIncompleto`), em vez de um disparo recusado lá na frente.
        anterior = SEGURADORA_ANTERIOR_NO_AGGER.get(str(seg.coenti)) if getattr(seg, "conhecida", False) else None
        if anterior:
            renov["seguradora_anterior"] = anterior
    vig = getattr(apolice, "vigencia", None)
    fim = getattr(vig, "fim", None)
    if isinstance(fim, date):
        renov.setdefault("fim_vigencia_anterior", fim.isoformat())
        renov.setdefault("vigencia_inicio", fim.isoformat())
        renov.setdefault("vigencia_fim", _mais_um_ano(fim).isoformat())
    return renov


def _ramo_do_agger(apolice: Any) -> int:
    try:
        from app.providers.policy_data_provider import familia_de_ramo

        familia = familia_de_ramo(getattr(apolice, "ramo", None))
    except Exception:  # noqa: BLE001
        familia = None
    if familia is None:
        return RAMO_AUTO
    if familia not in RAMO_DO_AGGER_POR_FAMILIA:
        raise RamoIndisponivel(f"renovação do ramo '{familia}' não implementada (há: auto, residencial, condomínio, "
                               "empresarial)")
    return RAMO_DO_AGGER_POR_FAMILIA[familia]


def de_apolice(apolice: Any, perfil: Optional[Mapping[str, Mapping[str, Any]]] = None, *, ficha: Any = None,
               config: Optional[Mapping[str, Any]] = None, exigir_completo: bool = False) -> PedidoDeCalculo:
    """A RENOVAÇÃO: a FICHA ÚNICA da apólice (`policy_data_provider.Apolice`, já `reconciliar`-ada) + o `perfil` →
    `PedidoDeCalculo` com `renovacao=True`, no AUTO e no RE (residencial 2 · condomínio 16 · empresarial 18).

    Da `Apolice` vêm: número da apólice anterior, seguradora anterior, fim da vigência anterior → vigência nova (fim +
    1 ano), placa (`item_de_risco`) e — no RE — as COBERTURAS: a Básica (incêndio) da ficha, reajustada pela config da
    corretora (`renovacao.reajuste_basica_pct`, D-129C-06, via `config.basica_renovada`), vira `risco.valor_basica`
    (D-129C-03: o valor vem do PEDIDO) e fica `assumido` (é deduzida, não dita).
    Da `ficha` (`ApoliceDocumental`, SPEC-130-B) vêm o objeto do risco (`objeto_do_risco`: AUTO placa/chassi/ano_modelo;
    RE cep e, no empresarial, atividade), o estado da leitura e o tipo do documento — lidos de forma TOLERANTE (uma
    ficha sem esses campos funciona).
    📊 BLOCO 0 (05/10): o tipo `Apolice` NÃO carrega FIPE, bônus, nascimento, sexo nem o endereço do risco — eles chegam
    em `perfil` ({grupo: {campo: valor}}, os nomes do contrato DO RAMO). O bônus nunca é descartado (G13).

    Quem VENCE: o `perfil` (o que quem pediu disse agora) > o cadastro (`item_de_risco`: o endosso troca o carro) > o
    documento. ⛔ O que falta e não é deduzível NÃO é inventado: fica em `faltando()` (a porta devolve
    `PedidoIncompleto`); com `exigir_completo=True` sai já aqui como `FichaIncompleta(faltando=[...])`.
    A ficha cuja leitura NÃO fechou não recusa o pedido: ele sai com o aviso `coberturas_nao_conferidas` (`avisos`).
    """
    perfil = {g: dict(v or {}) for g, v in (perfil or {}).items()}
    ramo = _ramo_do_agger(apolice)
    perfil["renovacao"] = _renovacao_da_apolice(apolice, perfil.get("renovacao") or {})
    objeto = _objeto_do_risco(apolice, ficha)
    avisos = _avisos_da_leitura(apolice, ficha)
    assumidos: set = set()

    if ramo == RAMO_AUTO:
        pedido = _de_apolice_auto(apolice, perfil, objeto, avisos, assumidos)
    else:
        pedido = _de_apolice_re(apolice, perfil, objeto, avisos, assumidos, ramo=ramo, config=config)
    pedido = replace(pedido, avisos=frozenset(avisos))
    if exigir_completo:
        faltam = pedido.faltando()
        faltam += [c for c in pedido.sem_codigo() if c not in faltam]
        if faltam:
            raise FichaIncompleta(faltam, avisos=pedido.avisos)
    return pedido


def _de_apolice_auto(apolice: Any, perfil: Dict[str, Dict[str, Any]], objeto: Mapping[str, Any], avisos: set,
                     assumidos: set) -> PedidoDeCalculo:
    veic = dict(perfil.get("veiculo") or {})
    placa_cadastro = _valor_de(getattr(getattr(apolice, "item_de_risco", None), "placa", None))
    placa_documento = objeto.get("placa")
    if placa_cadastro and placa_documento and (_sanear("veiculo", "placa", str(placa_cadastro))
                                               != _sanear("veiculo", "placa", str(placa_documento))):
        avisos.add(AVISO_PLACA_DIVERGE)
    for nome, valor in (("placa", placa_cadastro or placa_documento), ("chassi", objeto.get("chassi")),
                        ("ano_modelo", objeto.get("ano_modelo"))):
        if not _vazio(valor) and _vazio(veic.get(nome)):
            veic[nome] = valor
    perfil["veiculo"] = veic

    seg_ = perfil.get("segurado") or {}
    cond = dict(perfil.get("condutor") or {})
    if not any(not _vazio(cond.get(k)) for k in ("cpf", "nome")):
        for de, para in (("cpf_cnpj", "cpf"), ("nome", "nome"), ("nascimento", "nascimento"), ("sexo", "sexo"),
                         ("estado_civil", "estado_civil")):
            if not _vazio(seg_.get(de)):
                cond[para] = seg_[de]
                assumidos.add(f"condutor.{para}")
        cond.setdefault("relacao_com_segurado", "proprio")
        assumidos.add("condutor.relacao_com_segurado")
    perfil["condutor"] = cond
    pern = dict(perfil.get("pernoite") or {})
    if _vazio(pern.get("cep_pernoite")) and not _vazio(seg_.get("cep")):
        pern["cep_pernoite"] = seg_["cep"]
        assumidos.add("pernoite.cep_pernoite")
    perfil["pernoite"] = pern
    return PedidoDeCalculo.de_dict(perfil, assumidos=assumidos)


def _de_apolice_re(apolice: Any, perfil: Dict[str, Dict[str, Any]], objeto: Mapping[str, Any], avisos: set,
                   assumidos: set, *, ramo: int, config: Optional[Mapping[str, Any]]) -> PedidoDeCalculo:
    risco = dict(perfil.get("risco") or {})
    # o objeto do risco da ficha: o CEP (os 3 ramos); a atividade só onde o contrato a tem (empresarial — no
    # residencial `atividade_no_local` é um sim/não, outra pergunta)
    if _vazio(risco.get("cep")) and not _vazio(objeto.get("cep")):
        risco["cep"] = objeto["cep"]
    if ramo == RAMO_EMPRESARIAL and _vazio(risco.get("atividade")) and not _vazio(objeto.get("atividade")):
        risco["atividade"] = objeto["atividade"]
    if _vazio(risco.get("valor_basica")):
        anterior, origem, ambigua = _basica_da_ficha(apolice)
        if ambigua:
            avisos.add(AVISO_BASICA_AMBIGUA)
        if anterior is not None:
            if config is None:
                raise TypeError("a renovação de RE precisa da config da corretora (renovacao.reajuste_basica_pct): "
                                "nenhum reajuste é presumido")
            from app.services.multicalculo.config import basica_renovada

            nova = basica_renovada(config, ramo, anterior)
            if nova is None:
                avisos.add(AVISO_SEM_REGRA_DE_REAJUSTE)
            else:
                risco["valor_basica"] = nova
                assumidos.add("risco.valor_basica")
                if origem != "documento_oficial":
                    avisos.add(AVISO_COBERTURAS_DO_CADASTRO)
    perfil["risco"] = risco
    return PedidoDeCalculo.de_dict(perfil, ramo=ramo, assumidos=assumidos)
