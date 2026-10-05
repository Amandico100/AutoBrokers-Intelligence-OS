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
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple

from portal_worker.multicalculo.contrato import (
    CAMPOS_DE_CODIGO_INTEIRO, CAMPOS_DE_CODIGO_TEXTO, CAMPOS_DO_PEDIDO_AUTO, CAMPOS_SIM_NAO, CODIGOS_MEDIDOS,
    RAMO_AUTO, SEGURADORA_ANTERIOR_NO_AGGER,
)

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


@dataclass(frozen=True)
class PedidoDeCalculo:
    """O pedido saneado. Construa com `PedidoDeCalculo.de_dict(...)` ou `de_apolice(...)`.

    `campos`    {grupo: {campo: valor}} — só nomes do catálogo; vazio vira ausente.
    `assumidos` "grupo.campo" que NÃO vieram de quem pediu: valor deduzido (condutor = segurado, CEP de pernoite =
                CEP) ou deixado para o PADRÃO da tela (perfil, na origem auxiliar). O robô e a página mostram o que foi
                assumido; ninguém apresenta um assumido como dito pelo cliente.
    """

    campos: Mapping[str, Mapping[str, Any]]
    ramo: int = RAMO_AUTO
    seguradoras: Tuple[int, ...] = ()
    assumidos: FrozenSet[str] = frozenset()

    def __repr__(self) -> str:  # ⛔ nunca os valores
        preenchidos = sum(1 for g in self.campos.values() for v in g.values() if not _vazio(v))
        return (f"PedidoDeCalculo(ramo={self.ramo}, grupos={sorted(self.campos)}, preenchidos={preenchidos}, "
                f"assumidos={len(self.assumidos)})")

    __str__ = __repr__

    # ------------------------------------------------------------------ construção
    @classmethod
    def de_dict(cls, dados: Mapping[str, Any], *, ramo: int = RAMO_AUTO,
                seguradoras: Iterable[int] = (), assumidos: Iterable[str] = ()) -> "PedidoDeCalculo":
        if ramo != RAMO_AUTO:
            raise ValueError(f"ramo {ramo} não implementado (a v1 é o AUTO, {RAMO_AUTO})")
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

    # ------------------------------------------------------------------ leitura
    def valor(self, grupo: str, nome: str) -> Any:
        return (self.campos.get(grupo) or {}).get(nome)

    def faltando(self) -> List[str]:
        """Os obrigatórios da E3 que faltam, como "grupo.campo" (nomes, nunca valores)."""
        faltam = [f"{g}.{n}" for (g, n) in OBRIGATORIOS if _vazio(self.valor(g, n))]
        # F4: o robô recusa a renovação sem a seguradora anterior (`cotacao_do_pedido`) — a porta pergunta antes
        if self.renovacao and _vazio(self.valor("renovacao", "seguradora_anterior")):
            faltam.append("renovacao.seguradora_anterior")
        return faltam

    def sem_codigo(self) -> List[str]:
        """F4: os campos PRESENTES cujo valor não tem código medido no Agger (`contrato.CODIGOS_MEDIDOS`) — o robô
        os recusaria só no disparo. A porta os devolve como `PedidoIncompleto` (nomes, nunca valores)."""
        return sorted(f"{g}.{n}" for g, campos in self.campos.items() for n, v in campos.items()
                      if not _vazio(v) and not _tem_codigo(g, n, v))

    def perfil_faltando(self) -> List[str]:
        return [f"{g}.{n}" for (g, n) in CAMPOS_DE_PERFIL
                if _vazio(self.valor(g, n)) and f"{g}.{n}" not in self.assumidos]

    def assumindo_perfil(self) -> "PedidoDeCalculo":
        """O perfil que falta vira `assumido` (fica para o PADRÃO da tela) — a origem auxiliar (D-128-07)."""
        novos = {f"{g}.{n}" for (g, n) in CAMPOS_DE_PERFIL if _vazio(self.valor(g, n))}
        return PedidoDeCalculo(campos=self.campos, ramo=self.ramo, seguradoras=self.seguradoras,
                               assumidos=frozenset(self.assumidos | novos))

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
        for grupo in _CATALOGO:
            saida[grupo] = {} if grupo in GRUPOS_DO_CALCULO else dict(self.campos.get(grupo) or {})
        saida["seguradoras"] = list(self.seguradoras)
        saida["assumidos"] = sorted(self.assumidos)
        return saida


# ---------------------------------------------------------------------------------------------------------------------
# A RENOVAÇÃO a partir da ficha da InfoCap
# ---------------------------------------------------------------------------------------------------------------------
def _valor_de(campo: Any) -> Any:
    """Um `CampoComOrigem` (ou None) → o valor, ou None se indisponível."""
    if campo is None:
        return None
    if getattr(campo, "tem_valor", False):
        return campo.valor
    return None


def _mais_um_ano(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:            # 29/02
        return d.replace(year=d.year + 1, day=28)


def de_apolice(apolice: Any, perfil: Optional[Mapping[str, Mapping[str, Any]]] = None) -> PedidoDeCalculo:
    """A RENOVAÇÃO: `policy_data_provider.Apolice` + o `perfil` da ficha → `PedidoDeCalculo` com `renovacao=True`.

    Da `Apolice` (o tipo canônico) vêm: número da apólice anterior, seguradora anterior, fim da vigência anterior →
    vigência nova (fim + 1 ano), placa (`item_de_risco`).
    📊 BLOCO 0 (05/10): o tipo `Apolice` NÃO carrega FIPE, chassi, anos, bônus, nascimento, sexo nem CEP — a E2 os
    achou nas rotas `/itens` e `/cliente` da InfoCap, que não viram campo da `Apolice`. Eles chegam em `perfil`
    ({grupo: {campo: valor}}, os nomes do contrato), que quem chama monta da ficha. O bônus é
    `perfil["renovacao"]["bonus_anterior"]` e NUNCA é descartado (G13).

    O que falta e é deduzível vira `assumido`: condutor = o próprio segurado (relação "proprio"), CEP de pernoite = CEP
    do segurado. O que falta e NÃO é deduzível (estado civil, tempo de habilitação) não é inventado: fica faltando e a
    porta devolve `PedidoIncompleto` — o canal pergunta, o auxiliar pede ao corretor.
    """
    perfil = {g: dict(v or {}) for g, v in (perfil or {}).items()}
    ramo = getattr(apolice, "ramo", None)
    try:
        from app.providers.policy_data_provider import familia_de_ramo

        familia = familia_de_ramo(ramo)
    except Exception:  # noqa: BLE001
        familia = None
    if familia is not None and familia != "auto":
        raise ValueError(f"renovação de ramo '{familia}' não implementada (a v1 é o AUTO)")

    renov = dict(perfil.get("renovacao") or {})
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
    perfil["renovacao"] = renov

    veic = dict(perfil.get("veiculo") or {})
    placa = _valor_de(getattr(getattr(apolice, "item_de_risco", None), "placa", None))
    if placa and not veic.get("placa"):
        veic["placa"] = placa
    perfil["veiculo"] = veic

    assumidos: set = set()
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
