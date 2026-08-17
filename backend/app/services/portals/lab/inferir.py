# -*- coding: utf-8 -*-
"""Browser-to-API — de tráfego observado a contrato CANDIDATO. SPEC-077.

Este é o instrumento de maior valor do Portal Intelligence Lab, e ele é
inteiramente **offline**: não abre browser, não fala com portal, não depende de
Node, de `browse` CLI, de Stagehand nem de Browserbase. Come `Trafego` (de HAR
ou de DeepTrace) e devolve OpenAPI 3.1 candidato, com confiança declarada e
lacunas de cobertura nomeadas.

A ideia vem do `browser-to-api` do `browserbase/skills` (MIT). O algoritmo foi
reescrito em Python porque o original é Node e porque o nosso vocabulário de
redação, normalização de path e classificação de origem já existe — reusá-lo
vale mais que traduzir o deles.

🔴 CANDIDATO nunca é CONTRATO
==============================
Inferência lê o que aconteceu. Ela não lê o que PODE acontecer. Um campo que
apareceu nas 5 amostras pode ser opcional na sexta; um `POST` que devolveu 200
pode ser não-idempotente; um endpoint que funcionou hoje pode exigir cabeçalho
amanhã.

Por isso tudo que sai daqui nasce em `OBSERVED`/`CANDIDATE`, e a promoção para
`APPROVED_*` é decisão humana com gate — nunca consequência de o inferidor ter
achado bonito. Ver `ciclo.py`.

O que a medição ensinou, e que mudou o desenho
===============================================
📊 16/08/2026, sobre os 9 HAR de `docs/intake/MATERIAIS`:

**O host da API quase nunca é o host do portal.** Maxpar navega em
`abraseuatendimento.com.br` e conversa com `api.autoglass.com.br`; a MAPFRE
serve a própria API por CloudFront; a Yelum, pelo domínio do grupo HDI. Um
inferidor que procurasse contrato em `first_party` não acharia nada em duas das
três. Por isso o alvo é `trafego.hosts_de_api()`, não a origem.

**O ruído domina em volume.** No HAR da MAPFRE são 299 chamadas de APM contra 18
do portal. Filtro de ruído não é refinamento; é pré-requisito para o relatório
ser legível.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.services.portals.lab.trafego import Chamada, Trafego, hosts_de_api

# --------------------------------------------------------------------------
# Estados do endpoint — SPEC-077 §11.3
# --------------------------------------------------------------------------
OBSERVED = "OBSERVED"
CANDIDATE = "CANDIDATE"
REPLAYED_READONLY = "REPLAYED_READONLY"
APPROVED_READONLY = "APPROVED_READONLY"
APPROVED_MATERIAL = "APPROVED_MATERIAL"
REJECTED = "REJECTED"
NEEDS_MORE_SAMPLES = "NEEDS_MORE_SAMPLES"

# Nenhum endpoint nasce acima disto, e não há caminho de código que promova.
ESTADO_INICIAL = OBSERVED


# --------------------------------------------------------------------------
# Inferência de forma
# --------------------------------------------------------------------------
def _tipo_json(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return "string"


# Formatos que a gente reconhece pelo VALOR, não pelo nome do campo.
#
# 🔴 Reconhecer por nome seria mais fácil e estaria errado: a SPEC-074 documenta
# um campo chamado `premio` que guardava parcela vencida. Nome mente; valor não.
_RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?")
_RE_DATA_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_RE_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_RE_SO_DIGITO = re.compile(r"^\d+$")


def _formato_de(v: Any) -> str:
    if not isinstance(v, str) or not v:
        return ""
    if _RE_UUID.match(v):
        return "uuid"
    if _RE_DATA_ISO.match(v):
        return "date-time"
    if _RE_DATA_BR.match(v):
        return "date-br"
    if _RE_SO_DIGITO.match(v) and len(v) >= 6:
        return "numeric-string"
    return ""


@dataclass
class Forma:
    """A forma inferida de um valor, acumulada sobre várias amostras.

    O acúmulo é o que separa este módulo de um `type()`: com uma amostra só,
    tudo parece obrigatório e nenhum tipo parece união. É vendo o segundo
    exemplo que se descobre que `Chassi` às vezes vem `null`.
    """

    tipos: Set[str] = field(default_factory=set)
    formatos: Set[str] = field(default_factory=set)
    # Em quantas amostras esta chave APARECEU, e em quantas ela poderia ter
    # aparecido. A razão entre os dois é o que decide obrigatório × opcional.
    vista_em: int = 0
    de_um_total_de: int = 0
    filhos: Dict[str, "Forma"] = field(default_factory=dict)
    item: Optional["Forma"] = None          # para array
    exemplos: List[Any] = field(default_factory=list)
    # Valores distintos observados em campo string curto — vira `enum` candidato.
    valores: Counter = field(default_factory=Counter)

    @property
    def obrigatoria(self) -> bool:
        """Só é obrigatória se apareceu em TODAS as amostras — e se houver mais
        de uma. Com amostra única, `obrigatorio` é indistinguível de `apareceu`,
        e afirmar obrigatoriedade a partir de um exemplo é o erro que faz um
        contrato recusar uma resposta legítima."""
        return self.de_um_total_de > 1 and self.vista_em == self.de_um_total_de

    @property
    def tipo_principal(self) -> str:
        reais = [t for t in self.tipos if t != "null"]
        if not reais:
            return "null"
        if len(reais) == 1:
            return reais[0]
        # integer + number convivem: number cobre os dois.
        if reais == ["integer", "number"] or set(reais) == {"integer", "number"}:
            return "number"
        return sorted(reais)[0]

    @property
    def anulavel(self) -> bool:
        return "null" in self.tipos


# Um campo string com poucos valores distintos e muitas ocorrências é enum.
# 8 é o teto: acima disso, provavelmente é dado, não domínio.
MAX_VALORES_PARA_ENUM = 8
MIN_OCORRENCIAS_PARA_ENUM = 3


def acumular(forma: Forma, valor: Any, *, profundidade: int = 0) -> None:
    """Funde mais uma amostra na forma. Recursivo, com teto de profundidade.

    O teto existe porque JSON de portal às vezes traz árvore de menu inteira
    aninhada; descer 12 níveis produz um schema ilegível e não ajuda ninguém.
    """
    forma.tipos.add(_tipo_json(valor))
    f = _formato_de(valor)
    if f:
        forma.formatos.add(f)

    if isinstance(valor, str) and 0 < len(valor) <= 40:
        forma.valores[valor] += 1
    if len(forma.exemplos) < 3 and valor is not None and not isinstance(valor, (dict, list)):
        forma.exemplos.append(valor)

    if profundidade >= 8:
        return

    if isinstance(valor, dict):
        for k in valor:
            filho = forma.filhos.setdefault(str(k), Forma())
            filho.vista_em += 1
            acumular(filho, valor[k], profundidade=profundidade + 1)
        # Toda chave conhecida ganha +1 no denominador, tenha aparecido ou não.
        for k, filho in forma.filhos.items():
            filho.de_um_total_de += 1
    elif isinstance(valor, list):
        if forma.item is None:
            forma.item = Forma()
        for v in valor[:50]:  # 50 itens bastam para a forma; o resto é repetição
            forma.item.vista_em += 1
            forma.item.de_um_total_de += 1
            acumular(forma.item, v, profundidade=profundidade + 1)


def para_json_schema(forma: Forma) -> Dict[str, Any]:
    """A forma acumulada vira JSON Schema (dialeto do OpenAPI 3.1)."""
    tipo = forma.tipo_principal
    esquema: Dict[str, Any] = {}

    if forma.anulavel and tipo != "null":
        esquema["type"] = [tipo, "null"]
    else:
        esquema["type"] = tipo

    if forma.formatos and tipo == "string":
        # Um formato só quando ele é consistente. Formatos conflitantes viram
        # nenhum formato — dizer "date-time" sobre um campo que às vezes é
        # `date-br` faria um validador recusar dado legítimo.
        if len(forma.formatos) == 1:
            fmt = next(iter(forma.formatos))
            if fmt in ("uuid", "date-time"):
                esquema["format"] = fmt
            else:
                esquema["x-formato-observado"] = fmt

    if tipo == "object" and forma.filhos:
        props: Dict[str, Any] = {}
        obrigatorios: List[str] = []
        for nome in sorted(forma.filhos):
            filho = forma.filhos[nome]
            props[nome] = para_json_schema(filho)
            if filho.obrigatoria:
                obrigatorios.append(nome)
        esquema["properties"] = props
        if obrigatorios:
            esquema["required"] = obrigatorios
    elif tipo == "array" and forma.item is not None:
        esquema["items"] = para_json_schema(forma.item)
    elif tipo == "string":
        distintos = len(forma.valores)
        total = sum(forma.valores.values())
        if 0 < distintos <= MAX_VALORES_PARA_ENUM and total >= MIN_OCORRENCIAS_PARA_ENUM:
            # 🔴 `x-enum-observado`, não `enum`. `enum` num contrato significa
            # "só estes valores existem", e nós só sabemos "só estes apareceram".
            # A diferença é um validador que recusa um valor novo e legítimo.
            esquema["x-enum-observado"] = sorted(forma.valores)
        elif forma.exemplos:
            esquema["examples"] = forma.exemplos[:2]

    return esquema


# --------------------------------------------------------------------------
# Agrupamento por endpoint
# --------------------------------------------------------------------------
@dataclass
class Endpoint:
    metodo: str
    caminho: str            # já normalizado: /pedidos/{n}
    host: str
    estado: str = ESTADO_INICIAL
    amostras: int = 0
    status_vistos: Counter = field(default_factory=Counter)
    query_params: Dict[str, Forma] = field(default_factory=dict)
    headers_vistos: Counter = field(default_factory=Counter)
    forma_req: Optional[Forma] = None
    formas_resp: Dict[int, Forma] = field(default_factory=dict)
    content_type_req: str = ""
    content_type_resp: str = ""
    duracao_media_ms: float = 0.0
    exige_preflight: bool = False

    @property
    def chave(self) -> str:
        return f"{self.metodo} {self.caminho}"

    @property
    def escreve(self) -> bool:
        return self.metodo in ("POST", "PUT", "PATCH", "DELETE")


def _normalizar(caminho: str) -> str:
    """Usa o normalizador da SPEC-073. É o mesmo que o profiler usa.

    Ele preserva número colado em palavra (`passo5` identifica a tela) e
    parametriza segmento puramente numérico (`/pedidos/12345` → `/pedidos/{n}`).
    Escrever um segundo aqui faria Lab e produção discordarem sobre o que é a
    mesma tela.
    """
    try:
        from portal_worker.profiler import normalizar_path

        return normalizar_path(caminho)
    except Exception:  # noqa: BLE001
        return caminho


def agrupar(trafego: Trafego, *, hosts: Optional[Sequence[str]] = None,
            minimo_json: int = 2) -> Dict[str, Endpoint]:
    """Agrupa as chamadas em endpoints, por `(método, caminho normalizado)`.

    Sem `hosts`, o alvo é descoberto por `hosts_de_api()` — de onde o JSON
    realmente vem. Ver o docstring de lá para o porquê.

    `minimo_json=2` por padrão: 📊 um único JSON de um host é quase sempre
    passageiro — nos HAR do Maxpar, `maps.googleapis.com` entrava com 1 e
    trazia junto os assets do Google Maps. Dois já indica conversa.
    """
    if hosts is None:
        hosts = [h for h, _ in hosts_de_api(trafego, minimo=minimo_json)]
    alvo = {str(h).lower() for h in hosts}

    endpoints: Dict[str, Endpoint] = {}
    duracoes: Dict[str, List[float]] = {}

    # 🔴 `OPTIONS` de preflight CORS não é endpoint — é protocolo.
    #
    # 📊 Medido nos HAR do Maxpar: das 70 "operações" da primeira versão deste
    # agrupador, **36 eram `OPTIONS`** — mais da metade do relatório era o
    # navegador perguntando ao servidor se podia perguntar. Um relatório em que
    # metade das linhas é ruído de protocolo não é lido.
    #
    # Mas a informação não se joga fora: o preflight PROVA que o endpoint é
    # cross-origin e exige CORS, e isso importa para quem for chamá-lo de fora
    # do navegador. Vira a marca `exige_preflight` no endpoint de verdade.
    preflights: Set[str] = set()
    for c in trafego:
        if c.metodo == "OPTIONS":
            preflights.add(_normalizar(c.caminho))

    for c in trafego:
        if alvo and c.host not in alvo:
            continue
        if c.origem == "telemetry":
            continue
        if c.metodo == "OPTIONS":
            continue
        caminho = _normalizar(c.caminho)
        chave = f"{c.metodo} {caminho}"
        ep = endpoints.get(chave)
        if ep is None:
            ep = Endpoint(metodo=c.metodo, caminho=caminho, host=c.host)
            endpoints[chave] = ep
            duracoes[chave] = []

        ep.amostras += 1
        ep.status_vistos[c.status] += 1
        duracoes[chave].append(c.duracao_ms)
        for nome in c.nomes_de_header_req:
            ep.headers_vistos[nome.lower()] += 1

        for k, v in c.query.items():
            f = ep.query_params.setdefault(k, Forma())
            f.vista_em += 1
            f.de_um_total_de += 1
            acumular(f, v)

        if c.corpo_req and "json" in (c.content_type_req or "").lower():
            ep.content_type_req = c.content_type_req
            try:
                dados = json.loads(c.corpo_req)
            except Exception:  # noqa: BLE001
                dados = None
            if dados is not None:
                if ep.forma_req is None:
                    ep.forma_req = Forma()
                ep.forma_req.vista_em += 1
                ep.forma_req.de_um_total_de += 1
                acumular(ep.forma_req, dados)

        if c.corpo_resp and c.e_json:
            ep.content_type_resp = c.content_type_resp
            try:
                dados = json.loads(c.corpo_resp)
            except Exception:  # noqa: BLE001
                dados = None
            if dados is not None:
                f = ep.formas_resp.setdefault(int(c.status or 0), Forma())
                f.vista_em += 1
                f.de_um_total_de += 1
                acumular(f, dados)

    for chave, ep in endpoints.items():
        ep.exige_preflight = ep.caminho in preflights
        ds = [d for d in duracoes.get(chave, []) if d > 0]
        ep.duracao_media_ms = round(sum(ds) / len(ds), 1) if ds else 0.0
    return endpoints


# --------------------------------------------------------------------------
# Confiança e lacunas — SPEC-077 §11.6
# --------------------------------------------------------------------------
@dataclass
class Confianca:
    nota: int                       # 0–100
    motivos: List[str] = field(default_factory=list)
    lacunas: List[str] = field(default_factory=list)


def avaliar(ep: Endpoint) -> Confianca:
    """Quanta fé se pode ter neste endpoint, e o que falta para ter mais.

    🔴 A nota NÃO é "quão bom é o endpoint". É **quanta evidência existe**. Um
    endpoint perfeito visto uma vez tira nota baixa, e está certo: nós vimos uma
    vez.

    As lacunas são o produto mais útil deste módulo. Elas substituem a pergunta
    que hoje é feita ao Founder — *"que prints ainda faltam?"* — por uma lista
    que o próprio tráfego responde.
    """
    nota = 0
    motivos: List[str] = []
    lacunas: List[str] = []

    # Amostras. Uma só não distingue obrigatório de presente.
    if ep.amostras >= 5:
        nota += 30
        motivos.append(f"{ep.amostras} amostras")
    elif ep.amostras >= 2:
        nota += 18
        motivos.append(f"{ep.amostras} amostras")
        lacunas.append("exercitar mais vezes: com menos de 5 amostras nao da "
                       "para saber que campo e opcional")
    else:
        nota += 6
        motivos.append("1 amostra")
        lacunas.append("🔴 amostra unica: TODO campo parece obrigatorio, e "
                       "nenhum tipo parece uniao")

    # Resposta com forma conhecida.
    sucesso = [s for s in ep.status_vistos if 200 <= s < 300]
    if any(ep.formas_resp.get(s) for s in sucesso):
        nota += 25
        motivos.append("forma da resposta de sucesso conhecida")
    elif sucesso:
        nota += 5
        lacunas.append("resposta de sucesso sem corpo capturado: exportar HAR "
                       "com conteudo, ou ligar captura de corpo no DeepTrace")
    else:
        lacunas.append("🔴 nunca foi observada uma resposta de sucesso")

    # Caminho de erro. Sem ele, não se sabe o que o portal diz quando recusa —
    # e é justamente disso que a journey precisa para explicar ao segurado.
    erros = [s for s in ep.status_vistos if s >= 400]
    if erros:
        nota += 20
        motivos.append(f"erro observado: {', '.join(str(s) for s in sorted(erros))}")
        if not any(ep.formas_resp.get(s) for s in erros):
            lacunas.append("o corpo do erro nao foi capturado — e e nele que o "
                           "portal costuma explicar o motivo")
    else:
        lacunas.append("nenhum caminho de erro observado: exercitar recusa "
                       "(dado invalido, sem cobertura, sessao expirada)")

    # Corpo de requisição, para quem escreve.
    if ep.escreve:
        if ep.forma_req is not None:
            nota += 15
            motivos.append("forma do corpo de requisicao conhecida")
        else:
            lacunas.append("🔴 metodo de escrita sem corpo capturado: nao da "
                           "para montar a chamada")
    else:
        nota += 15  # leitura não precisa de corpo

    # Cabeçalho de autorização — a descoberta cara da SPEC-074.
    auth = [h for h in ep.headers_vistos
            if any(m in h for m in ("token", "auth", "session", "key"))]
    if auth:
        nota += 10
        motivos.append(f"cabecalho de autorizacao identificado: {', '.join(sorted(auth))}")
    else:
        lacunas.append("nenhum cabecalho de autorizacao identificado — pode ser "
                       "endpoint publico, ou a sessao pode viajar em cookie")

    if ep.escreve:
        lacunas.append("🔴 metodo de ESCRITA: idempotencia NAO se infere de "
                       "trafego. Repetir este endpoint pode criar a segunda "
                       "operacao — so gate humano libera")

    return Confianca(nota=min(100, nota), motivos=motivos, lacunas=lacunas)


# --------------------------------------------------------------------------
# OpenAPI 3.1 candidato
# --------------------------------------------------------------------------
def openapi_candidato(trafego: Trafego, *,
                      titulo: str = "",
                      hosts: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """O documento OpenAPI 3.1 CANDIDATO, com a confiança embutida.

    🔴 Todo endpoint sai marcado `x-estado: OBSERVED` e
    `x-aviso: candidato inferido de trafego`. Não existe caminho neste módulo
    que produza `APPROVED_*` — promoção é decisão humana, em `ciclo.py`.
    """
    endpoints = agrupar(trafego, hosts=hosts)
    por_host: Counter = Counter(ep.host for ep in endpoints.values())
    servidor = por_host.most_common(1)[0][0] if por_host else ""

    paths: Dict[str, Any] = {}
    for chave in sorted(endpoints):
        ep = endpoints[chave]
        conf = avaliar(ep)

        operacao: Dict[str, Any] = {
            "summary": f"{ep.metodo} {ep.caminho}",
            "operationId": _operation_id(ep),
            "x-estado": ep.estado,
            "x-aviso": ("candidato inferido de trafego observado; NAO e "
                        "contrato aprovado"),
            "x-amostras": ep.amostras,
            "x-confianca": conf.nota,
            "x-confianca-motivos": conf.motivos,
            "x-lacunas": conf.lacunas,
            "x-host": ep.host,
            "x-exige-preflight-cors": ep.exige_preflight,
            "x-duracao-media-ms": ep.duracao_media_ms,
            "responses": {},
        }
        if ep.duracao_media_ms:
            operacao["x-duracao-media-ms"] = ep.duracao_media_ms

        params = []
        for nome in sorted(ep.query_params):
            params.append({
                "name": nome, "in": "query",
                "required": ep.query_params[nome].obrigatoria,
                "schema": para_json_schema(ep.query_params[nome]),
            })
        for seg in re.findall(r"\{([^}]+)\}", ep.caminho):
            params.append({
                "name": seg, "in": "path", "required": True,
                "schema": {"type": "string"},
            })
        if params:
            operacao["parameters"] = params

        if ep.forma_req is not None:
            operacao["requestBody"] = {
                "required": True,
                "content": {ep.content_type_req.split(";")[0] or "application/json":
                            {"schema": para_json_schema(ep.forma_req)}},
            }

        for status in sorted(ep.status_vistos):
            bloco: Dict[str, Any] = {
                "description": f"observado {ep.status_vistos[status]}x",
            }
            forma = ep.formas_resp.get(status)
            if forma is not None:
                bloco["content"] = {
                    ep.content_type_resp.split(";")[0] or "application/json":
                        {"schema": para_json_schema(forma)}}
            else:
                bloco["x-corpo"] = "nao capturado"
            operacao["responses"][str(status)] = bloco

        paths.setdefault(ep.caminho, {})[ep.metodo.lower()] = operacao

    return {
        "openapi": "3.1.0",
        "info": {
            "title": titulo or f"Candidato — {trafego.rotulo or servidor}",
            "version": "0.0.0-candidato",
            "description": (
                "🔴 DOCUMENTO CANDIDATO, gerado por inferencia sobre trafego "
                "observado (SPEC-077). Ele descreve o que ACONTECEU, nao o que "
                "o portal garante. Nenhum endpoint aqui esta aprovado para uso "
                "em producao; promocao exige gate humano.\n\n"
                f"fonte: {trafego.fonte} · {trafego.rotulo} · "
                f"{len(trafego)} chamadas analisadas"),
        },
        "servers": [{"url": f"https://{servidor}"}] if servidor else [],
        "paths": paths,
        "x-gerado-por": "portal_lab.inferir (SPEC-077)",
        "x-endpoints": len(endpoints),
        "x-hosts": [h for h, _ in por_host.most_common()],
    }


def _operation_id(ep: Endpoint) -> str:
    partes = [p for p in ep.caminho.strip("/").split("/") if p]
    limpo = [re.sub(r"[^a-zA-Z0-9]", "", p) or "x" for p in partes]
    return (ep.metodo.lower() + "".join(p.capitalize() for p in limpo)) or "op"


def relatorio_de_cobertura(trafego: Trafego, *,
                           hosts: Optional[Sequence[str]] = None) -> str:
    """O texto que substitui *"que prints ainda faltam?"*.

    É a saída mais imediatamente útil do módulo: em vez de eu perguntar ao
    Founder o que capturar, o próprio tráfego diz.
    """
    endpoints = agrupar(trafego, hosts=hosts)
    if not endpoints:
        return ("Nenhum endpoint de API encontrado neste trafego.\n"
                "Se o portal e API-first, confira se o HAR foi exportado COM "
                "conteudo (`HAR with content`) — sem os corpos, nao ha o que "
                "inferir.")

    linhas = [
        f"# Cobertura — {trafego.rotulo or trafego.fonte}",
        "",
        f"{len(trafego)} chamadas analisadas · {len(endpoints)} endpoints",
        "",
    ]
    avaliados = [(ep, avaliar(ep)) for ep in endpoints.values()]
    avaliados.sort(key=lambda par: (-par[1].nota, par[0].chave))

    linhas.append("| endpoint | amostras | status | confianca |")
    linhas.append("|---|---:|---|---:|")
    for ep, conf in avaliados:
        st = ", ".join(str(s) for s in sorted(ep.status_vistos))
        linhas.append(f"| `{ep.chave}` | {ep.amostras} | {st} | {conf.nota} |")

    linhas += ["", "## O que falta exercitar", ""]
    vistas: Set[str] = set()
    for ep, conf in avaliados:
        proprias = [g for g in conf.lacunas if g not in vistas]
        if not proprias:
            continue
        linhas.append(f"**`{ep.chave}`**")
        for g in proprias:
            linhas.append(f"- {g}")
            vistas.add(g)
        linhas.append("")

    materiais = [ep for ep, _ in avaliados if ep.escreve]
    if materiais:
        linhas += [
            "## 🔴 Endpoints de escrita observados",
            "",
            "Estes CRIAM coisa no mundo. Nenhum deles pode ser usado sem gate "
            "humano, e idempotencia nao se infere de trafego:",
            "",
        ]
        for ep in materiais:
            linhas.append(f"- `{ep.chave}`")
    return "\n".join(linhas) + "\n"
