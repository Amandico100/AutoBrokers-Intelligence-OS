# -*- coding: utf-8 -*-
"""Injeção de falhas sobre o replay — SPEC-077 §30.2.

Este módulo é **puro**: sem rede, sem Supabase, sem Playwright, sem I/O no
import. Ele não substitui o `replay.py` da SPEC-075 — ele o **veste**. Toda
chamada continua passando pelo `ReplayDeSessao`, que continua contando,
conferindo corpo e barrando efeito não previsto. O que muda é o que a journey
recebe **de volta**.

O buraco que ele fecha
======================
O `ReplayDeSessao` só reproduz o que a fixture GRAVOU. Se a fixture tem um 200,
o replay devolve 200 — sempre, e só. Não havia como perguntar *"e se o portal
devolvesse 409 aqui?"*, e a pergunta não é hipotética: é exatamente o que o
portal faz quando já existe um atendimento aberto para o mesmo item.

Sem injeção, o QA adversarial exercita o caminho feliz da fixture e mais nada.
Um teste que só confirma o que já funciona não é teste — é uma segunda cópia da
fixture, com o custo de manutenção de um teste e o poder de detecção de zero.

🔴 A INVARIANTE QUE DÁ SENTIDO AO MÓDULO INTEIRO
=================================================
**Injetar "resposta perdida" NÃO desfaz a chamada.**

A falha `perde_resposta_apos_submit` é a mais importante daqui e é a mais fácil
de implementar errado. O jeito errado é curto e tentador: interceptar antes de
delegar, devolver um timeout, e pronto — a chamada nunca sai, o contador não
mexe, o teste "passa".

Esse teste ensina a coisa oposta da verdade. Ele ensina que perder a resposta é
o mesmo que não ter chamado. E é justamente aí que nasce o segundo pedido pago:
o código conclui *"não saiu, posso repetir"*, repete, e o segurado recebe dois
vidraceiros na porta — sem nenhum jeito de desfazer (SPEC-074 O4).

Por isso, aqui:

    1. a chamada é SEMPRE delegada ao `ReplayDeSessao` primeiro;
    2. `total_de_chamadas`, `chamadas`, `efeitos` e `chamou()` registram que ela
       SAIU — o injetor não tem uma contabilidade própria que possa divergir,
       ele delega esses atributos;
    3. só DEPOIS a resposta é destruída.

E a proibição é estrutural, não documental: `Falha.__post_init__` recusa
`perde_resposta_apos_submit=True` junto com `antes_da_chamada=True`. Não existe
como escrever a versão errada.

Isso é o `maybe_committed` da SPEC-073/074 reproduzido em bancada: a fase
`unknown` do guard, o estado de negócio `maybe_committed`, e o
`safe_to_retry_open=False` que o `vidros_estado.py` devolve para qualquer
desfecho que não seja `pre_protocolo`.

O que é medido e o que é ilustrativo — CLAUDE.md §12.1
=======================================================
📊 **A FORMA** dos corpos de erro é medida: o backend do portal é .NET e
responde `{"Message": ..., "Tipo": ...}`. Isso não é suposição — é o que
`vidros_api.classificar_preflight()` lê de um 400 capturado em 16/08/2026, e o
discriminador `TIPO_REGRA_DE_NEGOCIO = "regradenegocioexcecao"` veio dessa
mesma leitura.

💭 **O TEXTO** de cada corpo em `CORPO_DE_ERRO_POR_STATUS` é ilustrativo. Não
há captura de 401, 403, 409, 429 ou 500 do portal de vidros — as três capturas
existentes têm 200, 204 e 400. Os textos aqui são plausíveis e servem para
exercitar o parser; **nenhum deles é citável como medição**, e nenhuma decisão
de produto deve depender do texto exato. Se um dia um 409 real for capturado,
é este dicionário que muda — e o `Tipo` dele passa a ser 📊.

Duas notas de implementação que valem a leitura
================================================
1. **A resposta gravada é copiada antes de ser mexida.** `it.resposta` sai do
   replay por referência. Inverter uma lista "na resposta" inverteria a lista
   *na fixture*, e a próxima interação — ou o próximo cenário da bateria —
   herdaria a mutação. Um injetor que corrompe a fixture produz falha em
   cascata cuja causa está três cenários atrás.

2. **`mudar_caixa` mexe em VALOR, nunca em CHAVE.** 📊 O portal tem
   `<body ui-sentence-case-text>`: ele reescreve em runtime o que a pessoa lê
   (`Nº do Atendimento:` no template vira `Nº do atendimento:` no DOM). Quem
   sofre com caixa é texto de tela, não nome de campo JSON. Trocar a caixa das
   chaves seria outra falha — e essa já tem nome: `campo_faltando`.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
from dataclasses import dataclass, replace
from typing import (
    Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple,
)

from app.services.portals.replay import (
    InteracaoGravada,
    ReplayDeSessao,
    VERBOS_MATERIAIS,
    _caminhos_casam,
)

# --------------------------------------------------------------------------
# Vocabulário — importado, nunca redefinido (mesma disciplina do `replay.py`)
# --------------------------------------------------------------------------
# 🔴 Duas listas de nomes para a mesma coisa divergem no primeiro dia em que
# alguém corrige uma e esquece a outra. `unknown` e `maybe_committed` já têm
# dono; aqui é reuso. O import é tolerante porque este módulo é importável de
# contexto que não tem `portal_worker` no `sys.path`.
try:  # pragma: no cover - o caminho feliz é o único exercitado nos testes
    from portal_worker.guardrails import FASE_UNKNOWN as _FASE_UNKNOWN  # type: ignore
except Exception:  # noqa: BLE001
    _FASE_UNKNOWN = "unknown"

try:  # pragma: no cover
    from app.services.portals.contracts import (  # type: ignore
        NEGOCIO_TALVEZ_COMMITADO as _NEGOCIO_TALVEZ_COMMITADO,
    )
except Exception:  # noqa: BLE001
    _NEGOCIO_TALVEZ_COMMITADO = "maybe_committed"


# ==========================================================================
# Erros que a injeção levanta
# ==========================================================================
class FalhaInjetada(RuntimeError):
    """Base de tudo o que a injeção levanta. Carrega o contexto da chamada.

    Nunca é levantada por acaso: se ela aparece, foi porque um cenário pediu.
    Isso é o que separa "o teste encontrou um bug" de "o harness quebrou".
    """

    def __init__(self, mensagem: str, *, ordem: int = 0, metodo: str = "",
                 caminho: str = "", falha: str = "",
                 chamada_saiu: bool = False) -> None:
        super().__init__(mensagem)
        self.ordem = int(ordem)
        self.metodo = str(metodo)
        self.caminho = str(caminho)
        self.falha = str(falha)
        # 🔴 O atributo que o recovery lê. `False` significa "a requisição não
        # saiu da máquina"; `True` significa "saiu, e o mundo lá fora pode ter
        # mudado". Não existe terceiro valor, e o default é o otimista de
        # propósito: só quem realmente delegou tem direito de escrever `True`.
        self.chamada_saiu = bool(chamada_saiu)


class FalhaDeTransporte(FalhaInjetada):
    """A requisição NÃO saiu — DNS, recusa de conexão, proxy fechado.

    Este é o caso barato: nada mudou lá fora, repetir é seguro. Ele existe
    aqui principalmente para ter um par contra o qual comparar
    `RespostaPerdida` — sem esse contraste, "erro de rede" vira uma categoria
    só, e a categoria só tem o comportamento do caso barato.
    """


class RespostaPerdida(FalhaInjetada, asyncio.TimeoutError):
    """🔴 A chamada SAIU e a resposta se perdeu. O caro.

    Herda de `asyncio.TimeoutError` porque é assim que ela chega na vida real:
    um `await` que estoura. Código que já trata timeout continua tratando — e é
    exatamente esse código que este cenário existe para acusar, porque tratar
    timeout **como se fosse** `FalhaDeTransporte` é o defeito que produz o
    segundo pedido pago.

    Os três atributos que o chamador precisa ler:

        chamada_saiu ............... sempre `True`. Não há como construir
                                     esta exceção com `False`.
        fase_sugerida .............. `unknown` (SPEC-073): saiu da mão.
        estado_de_negocio_sugerido . `maybe_committed` (SPEC-074/contracts):
                                     está na lista `NAO_REPETIR`.
    """

    def __init__(self, mensagem: str, **kw: Any) -> None:
        kw["chamada_saiu"] = True   # não é parâmetro: é invariante
        super().__init__(mensagem, **kw)
        self.fase_sugerida = _FASE_UNKNOWN
        self.estado_de_negocio_sugerido = _NEGOCIO_TALVEZ_COMMITADO


# ==========================================================================
# A) `Falha` — a descrição de UMA injeção
# ==========================================================================
class _Sentinela:
    """Um `None` que se distingue de `None`.

    Necessário porque `corpo=None` é uma injeção legítima e frequente ("o
    portal respondeu 200 com corpo nulo"). Sem sentinela, "não mexer no corpo"
    e "trocar o corpo por nulo" seriam o mesmo valor.
    """

    __slots__ = ("_rotulo",)

    def __init__(self, rotulo: str) -> None:
        self._rotulo = rotulo

    def __repr__(self) -> str:  # pragma: no cover - conveniência de depuração
        return f"<{self._rotulo}>"

    def __bool__(self) -> bool:
        return False


NAO_MEXER = _Sentinela("nao_mexer")

# Caixa: os três modos, escritos por extenso para não virar `True`/`False`.
CAIXA_ALTA = "alta"
CAIXA_BAIXA = "baixa"
CAIXA_TITULO = "titulo"
_CAIXAS: Tuple[str, ...] = ("", CAIXA_ALTA, CAIXA_BAIXA, CAIXA_TITULO)

# O coringa de caminho, na mesma convenção que `_caminhos_casam` já usa.
AUTO = "*"


@dataclass(frozen=True)
class Falha:
    """Descreve UMA injeção: **onde**, **o quê** e **quantas vezes**.

    Congelada de propósito. Um catálogo de falhas compartilhadas entre cenários
    só é seguro se ninguém puder reconfigurar uma entrada por engano — e
    re-mirar uma falha é `dataclasses.replace()`, que devolve outra.

    ONDE (todos os filtros preenchidos precisam casar juntos)
    ---------------------------------------------------------
        metodo ................. `"POST"`; `""` casa qualquer verbo
        caminho ................ `"/atendimentos"`; usa o casamento tolerante
                                 a base URL do `replay._caminhos_casam`; `""`
                                 casa qualquer caminho
        indice_da_chamada ...... ordinal 1-based sobre TODAS as chamadas da
                                 sessão (é o `#N` das mensagens do replay);
                                 `None` = não filtra por ordinal
        somente_material ....... só casa verbo de escrita (`VERBOS_MATERIAIS`)

    QUANTAS VEZES
    -------------
        a_partir_da_ocorrencia . 1-based, contando só as chamadas que CASARAM.
                                 `2` = ignora a primeira, age da segunda em
                                 diante. É o que reproduz "funcionou uma vez e
                                 depois o portal virou".
        vezes .................. quantas aplicações no máximo. `1` (padrão) =
                                 só a primeira; `None` = sempre.

    O QUÊ (aplicado nesta ordem, e a ordem é parte do contrato)
    ------------------------------------------------------------
        atraso_s ............... registrado sempre; só dorme de verdade se o
                                 injetor foi construído com `dormir=True`
        status ................. troca `status` e recalcula `ok`
        corpo / corpo_vazio /
        corpo_bruto ............ trocam o payload (mutuamente exclusivos)
        remover_campos ......... apaga chaves da resposta gravada
        inverter_listas ........ inverte listas dentro da resposta
        mudar_caixa ............ troca a caixa dos VALORES string
        perde_resposta_apos_submit ... 🔴 destrói a resposta DEPOIS de a
                                 chamada ter saído e sido contada
        excecao ................ fábrica opcional da exceção final

    🔴 `antes_da_chamada=True` é o único modo em que a requisição NÃO é
    delegada — é a `FalhaDeTransporte`, o caso barato. Ele é incompatível com
    tudo o que altera resposta (não há resposta a alterar) e, sobretudo, com
    `perde_resposta_apos_submit`. `__post_init__` recusa as duas combinações.
    """

    nome: str = "falha"
    porque: str = ""

    # -- onde --------------------------------------------------------------
    metodo: str = ""
    caminho: str = ""
    indice_da_chamada: Optional[int] = None
    somente_material: bool = False

    # -- quantas vezes -----------------------------------------------------
    a_partir_da_ocorrencia: int = 1
    vezes: Optional[int] = 1

    # -- o quê -------------------------------------------------------------
    atraso_s: float = 0.0
    status: Optional[int] = None
    corpo: Any = NAO_MEXER
    corpo_vazio: bool = False
    corpo_bruto: Optional[str] = None
    remover_campos: Tuple[str, ...] = ()
    inverter_listas: Tuple[str, ...] = ()
    mudar_caixa: str = ""
    perde_resposta_apos_submit: bool = False
    excecao: Optional[Callable[["FalhaInjetada"], BaseException]] = None
    antes_da_chamada: bool = False

    # -- validação ---------------------------------------------------------
    def __post_init__(self) -> None:
        if self.perde_resposta_apos_submit and self.antes_da_chamada:
            raise ValueError(
                "🔴 `perde_resposta_apos_submit` com `antes_da_chamada` e uma "
                "contradicao, nao uma configuracao: perder a resposta exige "
                "que a chamada TENHA SAIDO. A combinacao ensinaria que perder "
                "a resposta e o mesmo que nao ter chamado — que e a causa "
                "raiz do segundo pedido pago (SPEC-074 O4). Para simular "
                "'nao saiu', use `FalhaDeTransporte` via `antes_da_chamada` "
                "sozinho.")

        if self.antes_da_chamada and self._mexe_na_resposta:
            raise ValueError(
                "`antes_da_chamada` nao pode alterar status/corpo/campos: se a "
                "requisicao nao saiu, nao existe resposta para alterar")

        if self.a_partir_da_ocorrencia < 1:
            raise ValueError("`a_partir_da_ocorrencia` e 1-based; minimo 1")
        if self.vezes is not None and self.vezes < 1:
            raise ValueError("`vezes` deve ser >= 1, ou `None` para sempre")
        if self.indice_da_chamada is not None and self.indice_da_chamada < 1:
            raise ValueError("`indice_da_chamada` e 1-based; minimo 1")
        if self.mudar_caixa not in _CAIXAS:
            raise ValueError(
                f"`mudar_caixa` deve ser um de {_CAIXAS!r}, veio "
                f"{self.mudar_caixa!r}")

        quantos_corpos = sum([
            self.corpo is not NAO_MEXER,
            bool(self.corpo_vazio),
            self.corpo_bruto is not None,
        ])
        if quantos_corpos > 1:
            raise ValueError(
                "escolha UM: `corpo`, `corpo_vazio` ou `corpo_bruto` — os tres "
                "descrevem o mesmo byte de payload e a ordem entre eles seria "
                "uma regra invisivel")

    @property
    def _mexe_na_resposta(self) -> bool:
        return bool(
            self.status is not None
            or self.corpo is not NAO_MEXER
            or self.corpo_vazio
            or self.corpo_bruto is not None
            or self.remover_campos
            or self.inverter_listas
            or self.mudar_caixa
        )

    # -- seleção -----------------------------------------------------------
    def casa(self, *, ordem: int, metodo: str, caminho: str) -> bool:
        """Esta chamada é alvo? Todos os filtros preenchidos precisam casar."""
        if self.indice_da_chamada is not None and ordem != self.indice_da_chamada:
            return False
        if self.metodo and metodo.upper() != self.metodo.strip().upper():
            return False
        if self.caminho and not _caminhos_casam(self.caminho, caminho):
            return False
        if self.somente_material and metodo.upper() not in VERBOS_MATERIAIS:
            return False
        return True

    def alvo_legivel(self) -> str:
        partes: List[str] = []
        if self.indice_da_chamada is not None:
            partes.append(f"#{self.indice_da_chamada}")
        if self.metodo or self.caminho:
            partes.append(f"{self.metodo or '*'} {self.caminho or '*'}")
        if self.somente_material:
            partes.append("material")
        if self.a_partir_da_ocorrencia > 1:
            partes.append(f"a partir da {self.a_partir_da_ocorrencia}a")
        return " ".join(partes) or "qualquer chamada"

    def para_dict(self) -> Dict[str, Any]:
        return {
            "nome": self.nome,
            "alvo": self.alvo_legivel(),
            "status": self.status,
            "atraso_s": self.atraso_s,
            "perde_resposta_apos_submit": self.perde_resposta_apos_submit,
            "antes_da_chamada": self.antes_da_chamada,
            "porque": self.porque,
        }


@dataclass
class FalhaAplicada:
    """Uma linha do diário: qual falha bateu em qual chamada, e o que fez.

    🔴 `chamada_saiu` é o campo que o relatório precisa. Sem ele, o diário
    diria "houve um timeout na chamada 4" — e quem lê não tem como saber se
    isso autoriza um retry. Com ele, a resposta está na mesma linha.
    """

    ordem: int
    falha: str
    metodo: str
    caminho: str
    chamada_saiu: bool
    efeito: str = ""

    def para_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


# ==========================================================================
# Corpos de erro — 📊 a FORMA, 💭 o TEXTO
# ==========================================================================
# 📊 Forma medida: o backend .NET do portal responde `{"Message", "Tipo"}`, e é
# disso que `vidros_api.classificar_preflight()` vive (captura de 16/08/2026).
# 💭 Textos ilustrativos: não há captura de 401/403/404/409/429/500 no portal de
# vidros. Servem para exercitar o parser; NÃO são citáveis como medição.
#
# Note o 409: `Tipo` = `RegraDeNegocioExcecao` normaliza para o
# `TIPO_REGRA_DE_NEGOCIO` que o classificador conhece — então a injeção de 409
# cai no ramo de regra de negócio de verdade, e não num `else` genérico.
CORPO_DE_ERRO_POR_STATUS: Dict[int, Dict[str, Any]] = {
    401: {"Message": "Autorizacao negada.", "Tipo": "NaoAutorizadoExcecao"},
    403: {"Message": "Acesso negado ao recurso.", "Tipo": "NaoAutorizadoExcecao"},
    404: {"Message": "Recurso nao encontrado.", "Tipo": "NaoEncontradoExcecao"},
    409: {"Message": "Ja existe atendimento aberto para o item informado.",
          "Tipo": "RegraDeNegocioExcecao"},
    429: {"Message": "Muitas requisicoes. Tente novamente em instantes.",
          "Tipo": "LimiteExcedidoExcecao"},
    500: {"Message": "Ocorreu um erro inesperado.", "Tipo": "ExcecaoNaoTratada"},
    503: {"Message": "Servico temporariamente indisponivel.",
          "Tipo": "ExcecaoNaoTratada"},
}

# 💭 Corpo de sessão expirada. A forma segue a mesma da casa; a flag extra
# existe para dar ao teste um sinal inequívoco sem depender do texto.
CORPO_SESSAO_EXPIRADA: Dict[str, Any] = {
    "Message": "Sessao expirada. Efetue o login novamente.",
    "Tipo": "NaoAutorizadoExcecao",
    "SessaoExpirada": True,
}

# 💭 JSON truncado: o que chega quando a conexão cai no meio do corpo, ou
# quando um proxy injeta uma página de erro em cima. Deliberadamente sem número
# nenhum dentro, para não tropeçar na `varredura_de_pii` do `replay.py`.
JSON_MALFORMADO: str = '{"Atendimento": {"CodigoAtendimento": "'


# ==========================================================================
# Caminhos pontilhados — `Atendimento.Opcoes[0].Titulo`
# ==========================================================================
_RE_INDICE = re.compile(r"\[(-?\d+)\]")


def _passos(caminho: Any) -> List[Any]:
    """`"a.b[1].c"` → `["a", "b", 1, "c"]`. Prefixo `$.` é tolerado."""
    bruto = str(caminho or "").strip()
    if bruto.startswith("$."):
        bruto = bruto[2:]
    elif bruto == "$":
        bruto = ""
    passos: List[Any] = []
    for pedaco in bruto.split("."):
        if not pedaco:
            continue
        nome = _RE_INDICE.sub("", pedaco)
        if nome:
            passos.append(nome)
        for m in _RE_INDICE.finditer(pedaco):
            passos.append(int(m.group(1)))
    return passos


def _descer(obj: Any, passos: Sequence[Any]) -> Tuple[Any, bool]:
    """Navega, devolvendo `(valor, achou)`. Nunca levanta."""
    atual = obj
    for p in passos:
        if isinstance(p, int):
            if not isinstance(atual, list) or not (-len(atual) <= p < len(atual)):
                return None, False
            atual = atual[p]
        else:
            if not isinstance(atual, dict) or p not in atual:
                return None, False
            atual = atual[p]
    return atual, True


def _remover_caminho(obj: Any, caminho: Any) -> bool:
    """Apaga a chave/posição. Devolve se apagou de verdade.

    O booleano importa: um cenário `campo_faltando` que não removeu nada é um
    cenário que virou o cenário de controle sem avisar — e passaria verde por
    não ter mudado coisa alguma. Quem chama registra isso.
    """
    passos = _passos(caminho)
    if not passos:
        return False
    pai, ok = _descer(obj, passos[:-1])
    if not ok:
        return False
    ultimo = passos[-1]
    if isinstance(ultimo, int):
        if isinstance(pai, list) and -len(pai) <= ultimo < len(pai):
            pai.pop(ultimo)
            return True
        return False
    if isinstance(pai, dict) and ultimo in pai:
        pai.pop(ultimo)
        return True
    return False


def _inverter_caminho(obj: Any, caminho: Any) -> bool:
    """Inverte a lista no caminho, no lugar. Devolve se inverteu."""
    alvo, ok = _descer(obj, _passos(caminho))
    if not ok or not isinstance(alvo, list) or len(alvo) < 2:
        return False
    alvo.reverse()
    return True


def chaves_do_topo(resposta: Any) -> List[str]:
    """Chaves de primeiro nível, em ordem ALFABÉTICA.

    Alfabética, e não de inserção, porque a ordem de inserção de um dict vindo
    de JSON depende de como o portal montou a resposta naquele dia. A bateria
    precisa ser a mesma lista amanhã.
    """
    if not isinstance(resposta, dict):
        return []
    return sorted(str(k) for k in resposta.keys())


def caminhos_de_listas(resposta: Any, *, minimo: int = 2,
                       _prefixo: str = "", _prof: int = 0) -> List[str]:
    """Caminhos de toda lista com pelo menos `minimo` itens, em ordem estável.

    Busca em profundidade, com as chaves de cada dict visitadas em ordem
    alfabética — pela mesma razão de `chaves_do_topo()`. Listas com um item só
    ficam de fora: inverter uma lista de um não muda nada, e um cenário que não
    muda nada é ruído que faz a bateria parecer maior do que é.
    """
    if _prof > 8:
        return []
    achados: List[str] = []
    if isinstance(resposta, dict):
        for k in sorted(str(x) for x in resposta.keys()):
            sub = f"{_prefixo}.{k}" if _prefixo else k
            achados.extend(caminhos_de_listas(
                resposta[k], minimo=minimo, _prefixo=sub, _prof=_prof + 1))
    elif isinstance(resposta, list):
        if len(resposta) >= minimo and _prefixo:
            achados.append(_prefixo)
        for i, v in enumerate(resposta):
            achados.extend(caminhos_de_listas(
                v, minimo=minimo, _prefixo=f"{_prefixo}[{i}]", _prof=_prof + 1))
    return achados


def _trocar_caixa(valor: Any, modo: str) -> Any:
    """Troca a caixa dos VALORES string, recursivamente. Chaves ficam intactas.

    📊 O `<body ui-sentence-case-text>` do portal reescreve o texto que a pessoa
    lê, não o nome dos campos. Um robô que compara `"Avançar"` com `==` quebra
    aqui; um que passa por `_norm()` (como `vidros_api` faz) sobrevive. É esse
    o defeito que este cenário procura.
    """
    if isinstance(valor, str):
        if modo == CAIXA_ALTA:
            return valor.upper()
        if modo == CAIXA_BAIXA:
            return valor.lower()
        if modo == CAIXA_TITULO:
            return valor.title()
        return valor
    if isinstance(valor, dict):
        return {k: _trocar_caixa(v, modo) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_trocar_caixa(v, modo) for v in valor]
    return valor


def _texto_de(payload: Any) -> str:
    """Serializa para o campo `text` do envelope da casa. Nunca levanta."""
    if payload is None:
        return ""
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001 - o `text` é diagnóstico, não contrato
        return str(payload)


# ==========================================================================
# B) `InjetorDeFalhas` — veste um `ReplayDeSessao`
# ==========================================================================
class InjetorDeFalhas:
    """Sessão falsa que responde como o replay — até a falha entrar em cena.

    Uso: onde a journey receberia um `ReplayDeSessao`, ela recebe isto. As
    portas são as mesmas (`requisitar`, `requisitar_sync`, `efeito_material`,
    `proxima_pergunta`), e todo o resto (`total_de_chamadas`, `chamadas`,
    `efeitos`, `chamou()`, `nao_consumidas`, `enviados`, `divergencias`) é
    **delegado** ao replay embrulhado.

    🔴 A delegação é a prova, não a conveniência. O injetor não mantém uma
    contagem própria de chamadas. Não existe, em nenhum caminho deste arquivo,
    um lugar onde o contador do replay possa discordar do que aconteceu — não
    porque alguém se lembrou de sincronizar, mas porque só há um contador.

    Parâmetros
    ----------
        replay .... o `ReplayDeSessao` já construído (com sua fixture, seu
                    `estrito`, seu `dry_run`). O injetor não reconfigura nada.
        falhas .... as `Falha` a aplicar. Ordem = ordem de aplicação quando
                    mais de uma casa na mesma chamada.
        dormir .... se `True`, `atraso_s` vira `await asyncio.sleep()` de
                    verdade no caminho async. Padrão `False`: uma bateria
                    adversarial roda centenas de cenários, e transformar
                    "atraso" em segundos de parede faria o time desligar a
                    bateria — que é a única falha que nenhum teste pega.
                    O atraso fica registrado em `atraso_acumulado_s` de
                    qualquer maneira.
    """

    def __init__(self, replay: ReplayDeSessao,
                 falhas: Iterable[Falha] = (),
                 *, nome: str = "", dormir: bool = False) -> None:
        self.replay = replay
        self.falhas: List[Falha] = list(falhas or [])
        self.nome_do_cenario = nome
        self.dormir = bool(dormir)

        # Diário e contadores próprios da INJEÇÃO (não das chamadas).
        self.aplicadas: List[FalhaAplicada] = []
        self.chamadas_sem_resposta: List[Dict[str, Any]] = []
        self.atraso_acumulado_s = 0.0
        self.avisos: List[str] = []

        self._ocorrencias: List[int] = [0] * len(self.falhas)
        self._aplicacoes: List[int] = [0] * len(self.falhas)
        self._atraso_pendente = 0.0

    # -- delegação ---------------------------------------------------------
    def __getattr__(self, nome: str) -> Any:
        """Tudo o que não é da injeção vem do replay — inclusive o contador.

        🔴 Escrito assim de propósito. Se `total_de_chamadas` fosse copiado
        para dentro do injetor, existiria a possibilidade de as duas contagens
        divergirem — e a divergência apareceria justamente no cenário de
        resposta perdida, que é onde ninguém pode se dar ao luxo de duvidar do
        número.
        """
        if nome.startswith("_") or nome == "replay":
            raise AttributeError(nome)
        try:
            alvo = object.__getattribute__(self, "replay")
        except AttributeError:  # pragma: no cover - só durante __init__
            raise AttributeError(nome) from None
        return getattr(alvo, nome)

    # -- seleção -----------------------------------------------------------
    def _armadas(self, ordem: int, metodo: str,
                 caminho: str) -> List[Tuple[int, Falha]]:
        """Quais falhas disparam nesta chamada, já atualizando os contadores.

        A contagem de OCORRÊNCIAS sobe para toda chamada que casa o filtro,
        tenha ela disparado ou não — é o que faz `a_partir_da_ocorrencia`
        significar o que promete. A contagem de APLICAÇÕES só sobe quando
        dispara, e é ela que `vezes` limita.
        """
        saida: List[Tuple[int, Falha]] = []
        for i, f in enumerate(self.falhas):
            if not f.casa(ordem=ordem, metodo=metodo, caminho=caminho):
                continue
            self._ocorrencias[i] += 1
            if self._ocorrencias[i] < f.a_partir_da_ocorrencia:
                continue
            if f.vezes is not None and self._aplicacoes[i] >= f.vezes:
                continue
            self._aplicacoes[i] += 1
            saida.append((i, f))
        return saida

    def _anotar(self, f: Falha, ordem: int, metodo: str, caminho: str, *,
                chamada_saiu: bool, efeito: str) -> None:
        self.aplicadas.append(FalhaAplicada(
            ordem=ordem, falha=f.nome, metodo=metodo, caminho=caminho,
            chamada_saiu=chamada_saiu, efeito=efeito))

    # -- o núcleo ----------------------------------------------------------
    def _responder(self, metodo: str, caminho: str, corpo: Any = None,
                   *, operacao: str = "") -> Dict[str, Any]:
        """O caminho único. Toda porta do injetor passa por aqui.

        A ordem dos degraus é o contrato do módulo:

            1. escolhe as falhas armadas para esta chamada
            2. falha `antes_da_chamada`  -> estoura SEM delegar (não saiu)
            3. 🔴 DELEGA ao replay        -> a chamada SAI e é CONTADA
            4. aplica as mutações de resposta, na ordem dos campos da `Falha`
            5. `perde_resposta_apos_submit` -> destrói a resposta, DEPOIS de 3
            6. `excecao` explícita       -> estoura, DEPOIS de 3

        🔴 Só o degrau 2 pula o 3, e ele é o único que pode dizer
        `chamada_saiu=False`. Tudo o que vem depois do 3 diz `True`, sem
        exceção e sem parâmetro que permita mentir.
        """
        m = str(metodo or "GET").strip().upper()
        c = str(caminho or "").strip()
        ordem = self.replay.total_de_chamadas + 1

        armadas = self._armadas(ordem, m, c)
        self._atraso_pendente = 0.0

        # -- 2) a requisição não sai ---------------------------------------
        for _i, f in armadas:
            if not f.antes_da_chamada:
                continue
            self._anotar(f, ordem, m, c, chamada_saiu=False,
                         efeito="abortada antes de sair da maquina")
            raise self._montar_excecao(
                f, ordem, m, c, chamada_saiu=False,
                padrao=FalhaDeTransporte,
                mensagem=(f"`{f.nome}`: a requisicao `{m} {c}` NAO saiu "
                          f"(chamada #{ordem}). Nada mudou no portal."))

        # -- 3) 🔴 a chamada sai e é contada pelo replay --------------------
        # Usa o funil único do `ReplayDeSessao`. As portas públicas dele todas
        # passam por aqui; ir por uma delas perderia o `operacao`, que é o que
        # dá nome legível ao `EfeitoMaterialRegistrado`.
        envelope = self.replay._responder(m, c, corpo, operacao=operacao)

        if not armadas:
            return envelope

        # -- 4/5/6) as mutações --------------------------------------------
        for _i, f in armadas:
            envelope = self._aplicar(f, envelope, ordem, m, c)
        return envelope

    def _aplicar(self, f: Falha, envelope: Dict[str, Any], ordem: int,
                 metodo: str, caminho: str) -> Dict[str, Any]:
        """Aplica UMA falha sobre o envelope já devolvido pelo replay."""
        env = dict(envelope)
        efeitos: List[str] = []

        # 🔴 Cópia profunda ANTES de qualquer mutação de payload. `env["json"]`
        # é a MESMA referência que está dentro de `InteracaoGravada.resposta`.
        # Inverter uma lista sem copiar inverteria a fixture — e o cenário
        # seguinte herdaria a mutação, produzindo uma falha cuja causa está
        # três cenários atrás. Já perdemos tempo com esse tipo de bug.
        if (f.remover_campos or f.inverter_listas or f.mudar_caixa):
            env["json"] = copy.deepcopy(env.get("json"))

        # -- atraso ---------------------------------------------------------
        if f.atraso_s:
            self.atraso_acumulado_s += float(f.atraso_s)
            self._atraso_pendente += float(f.atraso_s)
            env["atraso_injetado_s"] = float(f.atraso_s)
            efeitos.append(f"atraso {f.atraso_s}s")

        # -- status ----------------------------------------------------------
        if f.status is not None:
            st = int(f.status)
            env["status"] = st
            env["ok"] = st < 400
            env["fim_do_questionario"] = (st == 204)
            efeitos.append(f"status {st}")
            # Um 409 carregando o corpo de sucesso gravado é um cenário que não
            # existe no mundo. Quando o cenário não disse qual corpo quer, o
            # corpo padrão do status entra — cópia, nunca a referência do
            # dicionário de módulo.
            sem_corpo_declarado = (
                f.corpo is NAO_MEXER and not f.corpo_vazio
                and f.corpo_bruto is None)
            if st >= 400 and sem_corpo_declarado:
                padrao = CORPO_DE_ERRO_POR_STATUS.get(st)
                env["json"] = copy.deepcopy(padrao) if padrao is not None else None
                env["text"] = _texto_de(env["json"])
            elif st == 204 and sem_corpo_declarado:
                env["json"] = None
                env["text"] = ""

        # -- corpo -----------------------------------------------------------
        if f.corpo is not NAO_MEXER:
            env["json"] = copy.deepcopy(f.corpo)
            env["text"] = _texto_de(env["json"])
            efeitos.append("corpo trocado")
        elif f.corpo_vazio:
            # Corpo vazio de verdade: `text` é `""` e `json` é `None`, que é
            # exatamente o que `vidros_sessao._api()` produz quando o texto não
            # começa com `{` ou `[`.
            env["json"] = None
            env["text"] = ""
            env["corpo_vazio_injetado"] = True
            efeitos.append("corpo vazio")
        elif f.corpo_bruto is not None:
            # 🔴 JSON malformado NÃO estoura: a sessão da casa engole o
            # `JSONDecodeError` e devolve `json=None` com o status original
            # (`vidros_sessao._api()`). Reproduzir o estouro testaria um
            # caminho que o produto não tem. O caso real e cruel é o `200` com
            # `json=None`, que faz `r["json"]["X"]` levantar `TypeError` bem
            # longe daqui.
            env["json"] = None
            env["text"] = str(f.corpo_bruto)
            env["erro_de_json"] = True
            efeitos.append("json malformado")

        # -- campos ----------------------------------------------------------
        for alvo in f.remover_campos:
            caminhos = (chaves_do_topo(env.get("json"))[:1]
                        if str(alvo) == AUTO else [str(alvo)])
            if not caminhos:
                self.avisos.append(
                    f"`{f.nome}` na chamada #{ordem}: nada a remover — a "
                    "resposta gravada nao e um objeto com chaves")
            for cam in caminhos:
                if _remover_caminho(env.get("json"), cam):
                    efeitos.append(f"removido `{cam}`")
                else:
                    self.avisos.append(
                        f"`{f.nome}` na chamada #{ordem}: campo `{cam}` nao "
                        "existia na resposta gravada; o cenario virou o "
                        "controle sem mudar nada")

        for alvo in f.inverter_listas:
            caminhos = (caminhos_de_listas(env.get("json"))[:1]
                        if str(alvo) == AUTO else [str(alvo)])
            if not caminhos:
                self.avisos.append(
                    f"`{f.nome}` na chamada #{ordem}: nao ha lista com 2+ "
                    "itens na resposta gravada; nada a inverter")
            for cam in caminhos:
                if _inverter_caminho(env.get("json"), cam):
                    efeitos.append(f"invertida `{cam}`")
                else:
                    self.avisos.append(
                        f"`{f.nome}` na chamada #{ordem}: `{cam}` nao e uma "
                        "lista com 2+ itens; nada a inverter")

        # -- caixa -----------------------------------------------------------
        if f.mudar_caixa:
            env["json"] = _trocar_caixa(env.get("json"), f.mudar_caixa)
            if isinstance(env.get("text"), str) and env["text"]:
                env["text"] = _texto_de(env["json"])
            efeitos.append(f"caixa {f.mudar_caixa}")

        env["falha_injetada"] = f.nome

        # -- 5) 🔴 a resposta se perde DEPOIS do submit ----------------------
        if f.perde_resposta_apos_submit:
            registro = {
                "ordem": ordem, "metodo": metodo, "caminho": caminho,
                "falha": f.nome, "chamada_saiu": True,
                "fase_sugerida": _FASE_UNKNOWN,
                "estado_de_negocio_sugerido": _NEGOCIO_TALVEZ_COMMITADO,
            }
            self.chamadas_sem_resposta.append(registro)
            self._anotar(f, ordem, metodo, caminho, chamada_saiu=True,
                         efeito="resposta perdida DEPOIS do submit")
            raise self._montar_excecao(
                f, ordem, metodo, caminho, chamada_saiu=True,
                padrao=RespostaPerdida,
                mensagem=(
                    f"`{f.nome}`: `{metodo} {caminho}` (chamada #{ordem}) SAIU "
                    f"e a resposta se perdeu. A chamada esta contada — "
                    f"`total_de_chamadas` = {self.replay.total_de_chamadas}. "
                    f"Fase `{_FASE_UNKNOWN}`, estado de negocio "
                    f"`{_NEGOCIO_TALVEZ_COMMITADO}`: repetir e proibido ate "
                    "reconciliar."))

        # -- 6) exceção explícita -------------------------------------------
        if f.excecao is not None:
            self._anotar(f, ordem, metodo, caminho, chamada_saiu=True,
                         efeito="; ".join(efeitos + ["excecao"]) or "excecao")
            raise self._montar_excecao(
                f, ordem, metodo, caminho, chamada_saiu=True,
                padrao=FalhaInjetada,
                mensagem=f"`{f.nome}` na chamada #{ordem}")

        self._anotar(f, ordem, metodo, caminho, chamada_saiu=True,
                     efeito="; ".join(efeitos) or "nenhum")
        return env

    def _montar_excecao(self, f: Falha, ordem: int, metodo: str, caminho: str,
                        *, chamada_saiu: bool,
                        padrao: type, mensagem: str) -> BaseException:
        """A fábrica do cenário tem prioridade; o padrão preenche o resto.

        🔴 O contexto é ANEXADO mesmo quando o cenário trouxe a própria
        exceção. Uma `asyncio.TimeoutError` crua não diz se a chamada saiu — e
        essa é a única pergunta que o recovery tem para fazer.
        """
        contexto = padrao(mensagem, ordem=ordem, metodo=metodo,
                          caminho=caminho, falha=f.nome,
                          chamada_saiu=chamada_saiu)
        if f.excecao is None:
            return contexto
        try:
            custom = f.excecao(contexto)   # type: ignore[misc]
        except Exception:  # noqa: BLE001 - fábrica quebrada não vira verde
            return contexto
        if not isinstance(custom, BaseException):
            return contexto
        for atributo, valor in (("ordem", ordem), ("metodo", metodo),
                                ("caminho", caminho), ("falha", f.nome),
                                ("chamada_saiu", chamada_saiu)):
            try:
                setattr(custom, atributo, valor)
            except Exception:  # noqa: BLE001 - exceção com __slots__
                pass
        return custom

    # -- as portas ---------------------------------------------------------
    def requisitar_sync(self, metodo: str, caminho: str,
                        corpo: Any = None, **_: Any) -> Dict[str, Any]:
        """Espelha `ReplayDeSessao.requisitar_sync`. Não dorme (é síncrona)."""
        return self._responder(metodo, caminho, corpo)

    async def requisitar(self, metodo: str, caminho: str,
                         corpo: Any = None, **_: Any) -> Dict[str, Any]:
        """A porta normal de rede."""
        env = self._responder(metodo, caminho, corpo)
        await self._dormir_se_pedido()
        return env

    async def efeito_material(self, *, operacao: str, metodo: str = "POST",
                              caminho: str = "", corpo: Any = None,
                              **_: Any) -> Dict[str, Any]:
        """A porta educada. Como no replay, ela não é a proteção — é o rótulo."""
        env = self._responder(metodo, caminho or operacao, corpo,
                              operacao=operacao)
        await self._dormir_se_pedido()
        return env

    async def proxima_pergunta(self, respostas: Any) -> Dict[str, Any]:
        """Mesma assinatura de `ReplayDeSessao.proxima_pergunta`, COM injeção.

        Reimplementada em vez de delegada porque a versão do replay chama o
        `_responder` **dele**, e a injeção passaria batida justamente no laço
        do questionário — que é onde ela mais importa: é lá que o portal muda
        a ordem das opções, troca a caixa do texto e devolve 409.

        Lê `_cursor` do replay para descobrir qual interação vem a seguir. É
        acoplamento a atributo privado, e está declarado: se o cursor mudar de
        nome, este método quebra alto, que é melhor do que injetar no lugar
        errado em silêncio.
        """
        r = self.replay
        r.enviados.append(list(respostas or []))
        it = (r.interacoes[r._cursor]
              if r._cursor < len(r.interacoes) else None)
        caminho = it.caminho if it is not None else "/questionarios/perguntas"
        metodo = it.metodo if it is not None else "POST"
        env = self._responder(
            metodo, caminho, {"PerguntasResposta": list(respostas or [])})
        env.setdefault("fim_do_questionario", env.get("status") == 204)
        await self._dormir_se_pedido()
        return env

    async def _dormir_se_pedido(self) -> None:
        atraso, self._atraso_pendente = self._atraso_pendente, 0.0
        if self.dormir and atraso > 0:
            await asyncio.sleep(atraso)

    # -- leitura -----------------------------------------------------------
    @property
    def houve_chamada_sem_resposta(self) -> bool:
        """🔴 `True` obriga reconciliação antes de qualquer retry."""
        return bool(self.chamadas_sem_resposta)

    def resumo(self) -> Dict[str, Any]:
        """O resumo do replay + o diário da injeção, no mesmo dicionário."""
        base = dict(self.replay.resumo())
        base.update({
            "cenario": self.nome_do_cenario,
            "falhas_declaradas": [f.nome for f in self.falhas],
            "falhas_aplicadas": [a.para_dict() for a in self.aplicadas],
            "chamadas_sem_resposta": list(self.chamadas_sem_resposta),
            "houve_chamada_sem_resposta": self.houve_chamada_sem_resposta,
            "atraso_injetado_s": round(self.atraso_acumulado_s, 3),
            "avisos": list(self.avisos),
        })
        return base


# ==========================================================================
# C) O CATÁLOGO — §30.2
# ==========================================================================
# Os nomes são constantes para que um teste que cita um cenário quebre no
# import quando o cenário sumir, e não silenciosamente ao procurar uma string.
F_401 = "http_401_nao_autorizado"
F_403 = "http_403_proibido"
F_404 = "http_404_nao_encontrado"
F_409 = "http_409_conflito"
F_429 = "http_429_excesso_de_requisicoes"
F_500 = "http_500_erro_interno"
F_TIMEOUT = "timeout"
F_TRANSPORTE = "falha_de_transporte"
F_CORPO_VAZIO = "corpo_vazio"
F_JSON_MALFORMADO = "json_malformado"
F_CAMPO_FALTANDO = "campo_faltando"
F_ORDEM_TROCADA = "ordem_de_opcoes_trocada"
F_CAIXA_TROCADA = "mudanca_de_caixa_no_texto"
F_SESSAO_EXPIRADA = "sessao_expirada"
F_RESPOSTA_PERDIDA = "resposta_perdida_apos_submit"

# A ordem desta tupla é a ordem em que a bateria roda. Fixa, para que dois
# relatórios da mesma fixture sejam comparáveis linha a linha.
ORDEM_DO_CATALOGO: Tuple[str, ...] = (
    F_401, F_403, F_404, F_409, F_429, F_500,
    F_TIMEOUT, F_TRANSPORTE,
    F_CORPO_VAZIO, F_JSON_MALFORMADO,
    F_CAMPO_FALTANDO, F_ORDEM_TROCADA, F_CAIXA_TROCADA,
    F_SESSAO_EXPIRADA, F_RESPOSTA_PERDIDA,
)


def catalogo_de_falhas(*, metodo: str = "", caminho: str = "",
                       indice_da_chamada: Optional[int] = None,
                       a_partir_da_ocorrencia: int = 1) -> Dict[str, Falha]:
    """As falhas de §30.2, prontas, nomeadas e já miradas.

    Sem argumento, cada falha mira a **primeira** chamada que se encaixa no
    filtro dela (`vezes=1`). Os argumentos re-miram o catálogo inteiro de uma
    vez — é o que `cenarios_adversariais()` usa para percorrer uma fixture.

    O dicionário devolvido é novo a cada chamada; as `Falha` dentro dele são
    congeladas. Re-mirar uma delas é `dataclasses.replace(f, ...)`.
    """
    mira: Dict[str, Any] = {
        "metodo": metodo,
        "caminho": caminho,
        "indice_da_chamada": indice_da_chamada,
        "a_partir_da_ocorrencia": a_partir_da_ocorrencia,
    }

    def _http(nome: str, status: int, porque: str) -> Falha:
        return Falha(nome=nome, status=status, porque=porque, **mira)

    catalogo: Dict[str, Falha] = {
        F_401: _http(
            F_401, 401,
            "credencial recusada. 📊 O portal de vidros autentica por header "
            "custom `token_autorizacao` (nao `Bearer`), e o valor e o `Token` "
            "que nasce no `POST /atendimentos` — ou seja, a primeira fronteira "
            "material ja passou quando este 401 e possivel."),
        F_403: _http(
            F_403, 403,
            "autenticado e sem direito ao recurso. Nao e o mesmo que 401: "
            "reautenticar nao resolve, e insistir e o que dispara bloqueio."),
        F_404: _http(
            F_404, 404,
            "endpoint sumiu ou o recurso nao existe mais. 💭 O caso caro nao e "
            "o 404 em si: e o codigo que trata 404 como 'lista vazia'."),
        F_409: _http(
            F_409, 409,
            "conflito. 🔴 No portal de vidros o 409 tipico e 'ja existe "
            "atendimento aberto para este item' — o mesmo fato que o "
            "`GET /atendimentos/atendimentos-abertos-existentes` deveria ter "
            "pego antes. Tratar 409 como falha generica e repetir cria o "
            "segundo pedido."),
        F_429: _http(
            F_429, 429,
            "excesso de requisicoes. Exige recuo, nao retry imediato — e um "
            "laco de retry sem recuo transforma 429 em bloqueio de conta."),
        F_500: _http(
            F_500, 500,
            "erro do servidor. 🔴 Ambiguo por natureza: um 500 DEPOIS de um "
            "POST material nao diz se o registro nasceu. Quando cai numa "
            "fronteira, o desfecho honesto e `maybe_committed`."),

        F_TIMEOUT: Falha(
            nome=F_TIMEOUT, atraso_s=30.0,
            excecao=lambda ctx: asyncio.TimeoutError(str(ctx)),
            porque=(
                "a resposta nao chegou a tempo. A chamada SAIU: por isso esta "
                "falha delega antes de estourar, e `chamada_saiu` e `True`. "
                "Para o caso barato — a requisicao que nem saiu — use "
                f"`{F_TRANSPORTE}`."),
            **mira),
        F_TRANSPORTE: Falha(
            nome=F_TRANSPORTE, antes_da_chamada=True,
            porque=(
                "DNS, recusa de conexao, proxy fechado. Nada saiu, nada mudou "
                "no portal, repetir e seguro. E a LINHA DE CONTROLE do par: se "
                f"o codigo trata `{F_TIMEOUT}` igual a esta, ele vai repetir um "
                "submit que ja aconteceu."),
            **mira),

        F_CORPO_VAZIO: Falha(
            nome=F_CORPO_VAZIO, corpo_vazio=True,
            porque=(
                "200 com corpo vazio. 📊 `vidros_sessao._api()` devolve "
                "`json=None` quando o texto nao comeca com `{` ou `[` — sem "
                "levantar nada. Quem faz `r['json']['Campo']` recebe "
                "`TypeError` muito longe da origem."),
            **mira),
        F_JSON_MALFORMADO: Falha(
            nome=F_JSON_MALFORMADO, corpo_bruto=JSON_MALFORMADO,
            porque=(
                "corpo truncado ou pagina de erro de proxy no lugar do JSON. "
                "Indistinguivel de corpo vazio para quem so olha `json`; a "
                "diferenca esta em `text` e em `erro_de_json`."),
            **mira),

        F_CAMPO_FALTANDO: Falha(
            nome=F_CAMPO_FALTANDO, remover_campos=(AUTO,),
            porque=(
                "o portal parou de mandar um campo. 🔴 E a falha mais silenciosa "
                "de todas: nao ha erro, nao ha status ruim, so um `None` que "
                "atravessa o codigo e vira decisao errada. `*` remove a "
                "primeira chave em ordem alfabetica; `cenarios_adversariais()` "
                "gera um cenario por chave."),
            **mira),
        F_ORDEM_TROCADA: Falha(
            nome=F_ORDEM_TROCADA, inverter_listas=(AUTO,),
            porque=(
                "a ordem das opcoes mudou. 📊 O `CodigoItemCoberto` do portal e "
                "uma chave composta (`3|129|N|10700|1|0|V`) — quem escolhe pela "
                "chave sobrevive; quem escolhe por 'o primeiro da lista' pede a "
                "peca errada e nao descobre ate a instalacao."),
            **mira),
        F_CAIXA_TROCADA: Falha(
            nome=F_CAIXA_TROCADA, mudar_caixa=CAIXA_ALTA,
            porque=(
                "`\"Avancar\"` virou `\"AVANCAR\"`. 📊 O portal tem "
                "`<body ui-sentence-case-text>`, que reescreve caixa em "
                "runtime: o template diz `No do Atendimento:` e o DOM entrega "
                "`No do atendimento:`. Caixa NUNCA carrega significado de "
                "negocio, e comparar com `==` quebra na proxima release deles."),
            **mira),

        F_SESSAO_EXPIRADA: Falha(
            nome=F_SESSAO_EXPIRADA, status=401, corpo=CORPO_SESSAO_EXPIRADA,
            porque=(
                "401 com o corpo de sessao expirada. 🔴 Diferente do 401 "
                "generico numa coisa que decide o desfecho: a sessao so pode "
                "expirar DEPOIS de ter existido, e no portal de vidros ela "
                "nasce com o `Token` do `POST /atendimentos`. Logo, toda "
                "expiracao acontece com um `NumeroProtocolo` ja emitido — "
                "`safe_to_retry_open` e `False` (SPEC-074 O4)."),
            **mira),

        F_RESPOSTA_PERDIDA: Falha(
            nome=F_RESPOSTA_PERDIDA,
            perde_resposta_apos_submit=True,
            somente_material=True,
            porque=(
                "🔴 O cenario que causa o segundo pedido pago. A chamada "
                "material SAI, o portal a processa, e a resposta se perde no "
                "caminho de volta. `total_de_chamadas` registra que ela saiu, o "
                "efeito fica em `efeitos`, e a excecao carrega "
                f"`fase_sugerida={_FASE_UNKNOWN}` e "
                f"`estado_de_negocio_sugerido={_NEGOCIO_TALVEZ_COMMITADO}`. "
                "Repetir e proibido ate reconciliar."),
            **mira),
    }

    # A ordem do dicionário é a de `ORDEM_DO_CATALOGO`, e o assert é barato:
    # uma falha nova que alguém esqueça de listar quebra aqui, não na bateria.
    faltando = set(catalogo) - set(ORDEM_DO_CATALOGO)
    if faltando:  # pragma: no cover - defeito de manutenção, não de uso
        raise RuntimeError(
            f"falhas fora de `ORDEM_DO_CATALOGO`: {sorted(faltando)}")
    return {nome: catalogo[nome] for nome in ORDEM_DO_CATALOGO if nome in catalogo}


# ==========================================================================
# E) CENÁRIOS ADVERSARIAIS
# ==========================================================================
@dataclass
class CenarioAdversarial:
    """Um cenário nomeado: as falhas + por que vale a pena rodá-lo.

    `espera_maybe_committed` é o campo que a bateria lê para saber qual
    desfecho **cobrar** da journey. Um cenário de resposta perdida sobre uma
    fronteira material que termine em `failed` não é um teste que passou: é
    uma journey que vai autorizar um retry proibido.
    """

    nome: str
    falhas: Tuple[Falha, ...] = ()
    alvo: str = ""
    porque: str = ""
    material: bool = False
    espera_maybe_committed: bool = False

    @property
    def e_controle(self) -> bool:
        """🔴 A linha de controle: nenhuma falha injetada.

        CLAUDE.md §9.2 — *a linha de controle é o que dá direito à conclusão*.
        Sem ela, um cenário que "passou" pode ter passado porque a injeção não
        chegou a acontecer, e o mérito vai para o lugar errado.
        """
        return not self.falhas

    def injetar_em(self, replay: ReplayDeSessao, *,
                   dormir: bool = False) -> InjetorDeFalhas:
        """Veste um replay com as falhas deste cenário."""
        return InjetorDeFalhas(replay, self.falhas, nome=self.nome,
                               dormir=dormir)

    def para_dict(self) -> Dict[str, Any]:
        return {
            "nome": self.nome,
            "alvo": self.alvo,
            "porque": self.porque,
            "material": self.material,
            "espera_maybe_committed": self.espera_maybe_committed,
            "controle": self.e_controle,
            "falhas": [f.para_dict() for f in self.falhas],
        }


def _interacoes_de(fixture: Any) -> List[InteracaoGravada]:
    """Aceita a fixture como lista, como `ReplayDeSessao` ou como iterável."""
    if fixture is None:
        return []
    interacoes = getattr(fixture, "interacoes", None)
    if interacoes is not None:
        return list(interacoes)
    return list(fixture)


def cenarios_adversariais(
    fixture: Any,
    *,
    incluir_controle: bool = True,
    max_campos_por_resposta: int = 8,
    max_listas_por_resposta: int = 3,
) -> List[CenarioAdversarial]:
    """A bateria que vale a pena rodar contra esta fixture.

    Não é esperta — é **completa e determinística**. Mesma fixture, mesma
    lista, na mesma ordem, sempre. É isso que permite comparar o relatório de
    hoje com o de duas semanas atrás e saber que a diferença é do código.

    A ordem, e a razão de cada nível
    ---------------------------------
        1. o CONTROLE, primeiro                    §9.2 do CLAUDE.md
        2. para cada interação da fixture, em ordem
        3.   para cada falha, na ordem de `ORDEM_DO_CATALOGO`

    A mira é por `(metodo, caminho, N-ésima ocorrência)`, e não por ordinal de
    chamada. A diferença importa: se a journey mudar de ordem, uma mira por
    ordinal acertaria a chamada errada em silêncio, enquanto esta continua
    acertando o endpoint que se queria testar — ou não dispara, o que também é
    informação.

    Os cenários que dependem da forma da resposta só nascem quando a forma
    existe:

        campo_faltando ......... um cenário por chave de topo, em ordem
                                 alfabética, até `max_campos_por_resposta`
        ordem_de_opcoes_trocada  um por lista com 2+ itens, até
                                 `max_listas_por_resposta`
        mudanca_de_caixa ....... só se houver alguma string na resposta
        resposta_perdida ....... 🔴 SÓ em interação material. Perder a resposta
                                 de um GET custa uma releitura; perder a de um
                                 `POST /atendimentos` custa um vidraceiro.

    Os tetos são tetos, e estão declarados: com o agregado de ~58 campos do
    `GET /atendimentos`, remover um campo de cada vez geraria 58 cenários por
    interação. O corte é por custo, não por completude — quem quiser a
    varredura inteira sobe `max_campos_por_resposta`.
    """
    interacoes = _interacoes_de(fixture)
    cenarios: List[CenarioAdversarial] = []

    if incluir_controle:
        cenarios.append(CenarioAdversarial(
            nome="00.controle.sem_injecao",
            falhas=(),
            alvo="a fixture inteira, intacta",
            porque=(
                "🔴 A linha de controle. Ela repete a rodada sem nenhuma "
                "injecao e tem de terminar no `expected_state` do manifesto. "
                "Se o controle falha, nenhum resultado da bateria e "
                "atribuivel a injecao — CLAUDE.md §9.2."),
        ))

    # Quantas vezes cada (metodo, caminho) já apareceu antes desta posição.
    ja_vistos: Dict[Tuple[str, str], int] = {}

    for i, it in enumerate(interacoes):
        metodo = str(it.metodo or "GET").strip().upper()
        caminho = str(it.caminho or "").strip()
        chave = (metodo, caminho)
        ja_vistos[chave] = ja_vistos.get(chave, 0) + 1
        ocorrencia = ja_vistos[chave]

        material = bool(it.material) or metodo in VERBOS_MATERIAIS
        rotulo = f"{i + 1:02d}.{metodo}{caminho or '/'}"
        alvo = f"{it.nome} (ocorrencia {ocorrencia})"

        catalogo = catalogo_de_falhas(
            metodo=metodo, caminho=caminho,
            a_partir_da_ocorrencia=ocorrencia)

        chaves = chaves_do_topo(it.resposta)[:max(0, max_campos_por_resposta)]
        listas = caminhos_de_listas(it.resposta)[:max(0, max_listas_por_resposta)]
        tem_texto = _tem_string(it.resposta)

        for nome in ORDEM_DO_CATALOGO:
            base = catalogo[nome]

            if nome == F_CAMPO_FALTANDO:
                for k in chaves:
                    cenarios.append(CenarioAdversarial(
                        nome=f"{rotulo}::{nome}::{k}",
                        falhas=(replace(base, remover_campos=(k,)),),
                        alvo=alvo, porque=base.porque, material=material))
                continue

            if nome == F_ORDEM_TROCADA:
                for cam in listas:
                    cenarios.append(CenarioAdversarial(
                        nome=f"{rotulo}::{nome}::{cam}",
                        falhas=(replace(base, inverter_listas=(cam,)),),
                        alvo=alvo, porque=base.porque, material=material))
                continue

            if nome == F_CAIXA_TROCADA and not tem_texto:
                continue

            if nome == F_RESPOSTA_PERDIDA:
                # 🔴 Só sobre efeito material. Num GET, perder a resposta é
                # barato e o cenario nao ensina nada; numa fronteira, e o
                # cenario que separa uma journey correta de um segundo pedido.
                if not material:
                    continue
                cenarios.append(CenarioAdversarial(
                    nome=f"{rotulo}::{nome}",
                    falhas=(base,), alvo=alvo, porque=base.porque,
                    material=True, espera_maybe_committed=True))
                continue

            # 500 e timeout sobre fronteira material também terminam em
            # `maybe_committed`: o registro pode ter nascido antes do erro.
            ambiguo = material and nome in (F_500, F_TIMEOUT)

            cenarios.append(CenarioAdversarial(
                nome=f"{rotulo}::{nome}",
                falhas=(base,), alvo=alvo, porque=base.porque,
                material=material, espera_maybe_committed=ambiguo))

    return cenarios


def _tem_string(valor: Any, _prof: int = 0) -> bool:
    """Há algum valor string na resposta? Se não, trocar caixa é no-op."""
    if _prof > 8:
        return False
    if isinstance(valor, str):
        return bool(valor)
    if isinstance(valor, dict):
        return any(_tem_string(v, _prof + 1) for v in valor.values())
    if isinstance(valor, (list, tuple)):
        return any(_tem_string(v, _prof + 1) for v in valor)
    return False


__all__ = [
    # descrição de falha
    "Falha", "FalhaAplicada", "NAO_MEXER", "AUTO",
    "CAIXA_ALTA", "CAIXA_BAIXA", "CAIXA_TITULO",
    # injetor
    "InjetorDeFalhas",
    # erros
    "FalhaInjetada", "FalhaDeTransporte", "RespostaPerdida",
    # catálogo
    "catalogo_de_falhas", "ORDEM_DO_CATALOGO",
    "CORPO_DE_ERRO_POR_STATUS", "CORPO_SESSAO_EXPIRADA", "JSON_MALFORMADO",
    "F_401", "F_403", "F_404", "F_409", "F_429", "F_500",
    "F_TIMEOUT", "F_TRANSPORTE", "F_CORPO_VAZIO", "F_JSON_MALFORMADO",
    "F_CAMPO_FALTANDO", "F_ORDEM_TROCADA", "F_CAIXA_TROCADA",
    "F_SESSAO_EXPIRADA", "F_RESPOSTA_PERDIDA",
    # cenários
    "CenarioAdversarial", "cenarios_adversariais",
    # utilitários de caminho (usados pelos cenários e testáveis à parte)
    "chaves_do_topo", "caminhos_de_listas",
]
