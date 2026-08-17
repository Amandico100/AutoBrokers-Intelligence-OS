# -*- coding: utf-8 -*-
"""O formato único de tráfego observado — SPEC-077 Blocos 1 e 2.

Duas fontes muito diferentes precisam alimentar o MESMO inferidor:

    HAR exportado pelo navegador   ← o Founder, hoje, com F12 aberto
    DeepTrace do portal-worker     ← o robô, depois, navegando sozinho

Se cada uma tivesse o seu inferidor, o segundo nasceria pior e divergiria do
primeiro no primeiro campo novo. Então existe `Chamada`: um formato pequeno,
achatado e sem opinião, para o qual as duas convertem.

🔴 Por que HAR é cidadão de PRIMEIRA classe, e não formato legado
==================================================================
A SPEC-077 original assume `DeepTrace → inferidor`. Isso ignora um fato caro:
📊 no fluxo da SPEC-076, **quem navega é o Founder**, no Chrome dele, com a
credencial dele e um cliente real — porque o robô ainda não completa o fluxo.
DeepTrace roda dentro do nosso worker; ele não ajuda quem está com o F12 aberto.

E ignora um ativo: 📊 medido em 16/08/2026, `docs/intake/MATERIAIS/` guarda
**142 MB de HAR de 6 seguradoras, com 223 respostas JSON** — o material que eu
li com os olhos para escrever as journeys da 073 e da 074.

HAR-first entrega valor sem esperar o DeepTrace existir, e dá um conjunto de
validação que nenhum trace novo daria: dá para perguntar ao inferidor *"você
acha o que eu achei à mão?"*.

Sobre PII
=========
🔴 Os HAR de origem **contêm PII de segurado** e por isso estão no `.gitignore`
(`docs/intake/`). Este módulo lê deles, mas o que ele DEVOLVE nunca deve ser
persistido sem passar pelo redator. A separação é deliberada: `Chamada` carrega
o corpo cru em memória porque o inferidor precisa dele para extrair a forma; é
o inferidor que decide o que sai do processo. Ver `inferir.py`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import parse_qsl, urlsplit

# --------------------------------------------------------------------------
# O formato único
# --------------------------------------------------------------------------
@dataclass
class Chamada:
    """Uma requisição observada, do jeito que o inferidor precisa vê-la."""

    metodo: str
    url: str
    status: int = 0
    # Só o que serve à inferência. Cabeçalhos sensíveis são descartados na
    # entrada — não adianta redigir depois o que não precisava ter entrado.
    content_type_req: str = ""
    content_type_resp: str = ""
    corpo_req: Optional[str] = None
    corpo_resp: Optional[str] = None
    resource_type: str = ""
    iniciado_em: str = ""
    duracao_ms: float = 0.0
    # Nomes dos cabeçalhos, SEM valores. Serve para descobrir que o portal usa
    # `token_autorizacao` em vez de `Authorization` — que foi uma descoberta
    # cara na SPEC-074 e teria saído de graça daqui.
    nomes_de_header_req: Tuple[str, ...] = ()
    origem: str = ""  # first_party | asset | telemetry | third_party | unknown

    @property
    def host(self) -> str:
        try:
            return (urlsplit(self.url).hostname or "").lower()
        except ValueError:
            return ""

    @property
    def caminho(self) -> str:
        try:
            return urlsplit(self.url).path or "/"
        except ValueError:
            return "/"

    @property
    def query(self) -> Dict[str, str]:
        try:
            return dict(parse_qsl(urlsplit(self.url).query, keep_blank_values=True))
        except ValueError:
            return {}

    @property
    def e_json(self) -> bool:
        return "json" in (self.content_type_resp or "").lower()

    @property
    def escreve(self) -> bool:
        """🔴 Semântica, não verbo — a lição da SPEC-073.

        `POST /questionarios/perguntas` do Maxpar **lê** a próxima pergunta; o
        verbo diz POST e o efeito é leitura. Por isso este campo responde só
        *"o verbo sugere escrita?"* e nunca decide sozinho se algo é material.
        Quem decide é o guard, com o rótulo que a journey declara.
        """
        return self.metodo.upper() in ("POST", "PUT", "PATCH", "DELETE")


@dataclass
class Trafego:
    """Um conjunto de chamadas com procedência declarada."""

    chamadas: List[Chamada] = field(default_factory=list)
    fonte: str = ""          # har | deep_trace
    rotulo: str = ""         # nome do arquivo/execução, para o relatório
    host_portal: str = ""    # ajuda `classificar_origem` a saber quem é a casa

    def __len__(self) -> int:
        return len(self.chamadas)

    def __iter__(self) -> Iterator[Chamada]:
        return iter(self.chamadas)


# --------------------------------------------------------------------------
# Cabeçalhos que nunca entram
#
# 🔴 A regra é NÃO IMPORTAR, e não "importar e redigir". Um valor que nunca
# entrou no processo não pode vazar por um `print` de depuração, por um traceback
# ou por um `json.dumps` de diagnóstico. Redigir na saída protege o arquivo
# final; não importar protege tudo.
# --------------------------------------------------------------------------
HEADERS_QUE_NAO_ENTRAM = (
    "authorization", "cookie", "set-cookie", "proxy-authorization",
    "x-api-key", "api-key", "token_autorizacao", "x-auth-token",
    "x-csrf-token", "x-xsrf-token", "authentication",
)


def _cabecalho_entra(nome: str) -> bool:
    return str(nome or "").strip().lower() not in HEADERS_QUE_NAO_ENTRAM


# --------------------------------------------------------------------------
# HAR
# --------------------------------------------------------------------------
# Tipos de conteúdo que servem à inferência de contrato. Imagem, fonte e vídeo
# não têm schema a inferir e só engordariam a memória.
CONTENT_TYPES_UTEIS = ("json", "text/plain", "application/x-www-form-urlencoded",
                       "text/xml", "application/xml", "graphql")

# Teto por corpo. 📊 O maior corpo JSON útil medido nos 142 MB de HAR do
# `docs/intake` tem ~180 KB (catálogo de peças do Maxpar). 2 MB dá folga de uma
# ordem de grandeza e ainda impede que um HTML de 20 MB entre por engano.
TETO_DE_CORPO_BYTES = 2 * 1024 * 1024


def _conteudo_util(mime: str) -> bool:
    m = str(mime or "").lower()
    return any(t in m for t in CONTENT_TYPES_UTEIS)


def importar_har(caminho: Any, *, host_portal: str = "",
                 incluir_ruido: bool = False) -> Trafego:
    """Lê um `.har` do navegador e devolve `Trafego`.

    Tolerante por desenho: HAR de 30 MB vindo do DevTools costuma ter entradas
    truncadas, `content.text` ausente e encoding duvidoso. Uma entrada ruim faz
    a entrada ser pulada, nunca a importação inteira falhar — 📊 o HAR da MAPFRE
    tem 574 entradas e só 255 com corpo; recusar o arquivo por causa das 319
    seria jogar fora o que interessa.

    `incluir_ruido=False` (default) descarta telemetria/asset já na entrada. O
    filtro é o `classificar_origem` da SPEC-073 — o mesmo que o profiler usa,
    para que Lab e produção nunca discordem sobre o que é ruído.
    """
    p = Path(caminho)
    with p.open(encoding="utf-8", errors="ignore") as fh:
        bruto = json.load(fh)

    entradas = ((bruto or {}).get("log") or {}).get("entries") or []
    if not host_portal:
        host_portal = _host_predominante(entradas)

    saida: List[Chamada] = []
    for e in entradas:
        try:
            c = _chamada_de_entrada_har(e, host_portal)
        except Exception:  # noqa: BLE001
            continue
        if c is None:
            continue
        if not incluir_ruido and c.origem in ("telemetry", "asset"):
            continue
        saida.append(c)

    return Trafego(chamadas=saida, fonte="har", rotulo=p.name,
                   host_portal=host_portal)


def _chamada_de_entrada_har(e: Dict[str, Any], host_portal: str) -> Optional[Chamada]:
    req = e.get("request") or {}
    resp = e.get("response") or {}
    url = str(req.get("url") or "")
    if not url:
        return None

    conteudo = resp.get("content") or {}
    mime_resp = str(conteudo.get("mimeType") or "")
    texto = conteudo.get("text")
    if texto is not None:
        if not _conteudo_util(mime_resp) or len(texto) > TETO_DE_CORPO_BYTES:
            texto = None

    post = req.get("postData") or {}
    mime_req = str(post.get("mimeType") or "")
    corpo_req = post.get("text")
    if corpo_req is not None:
        if not _conteudo_util(mime_req) or len(corpo_req) > TETO_DE_CORPO_BYTES:
            corpo_req = None

    nomes = tuple(str(h.get("name") or "") for h in (req.get("headers") or [])
                  if _cabecalho_entra(h.get("name")))

    host = ""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        pass

    return Chamada(
        metodo=str(req.get("method") or "GET").upper(),
        url=url,
        status=int(resp.get("status") or 0),
        content_type_req=mime_req,
        content_type_resp=mime_resp,
        corpo_req=corpo_req,
        corpo_resp=texto,
        resource_type=str(e.get("_resourceType") or ""),
        iniciado_em=str(e.get("startedDateTime") or ""),
        duracao_ms=float(e.get("time") or 0.0),
        nomes_de_header_req=nomes,
        origem=_classificar(host, host_portal, str(e.get("_resourceType") or "")),
    )


def _host_predominante(entradas: Iterable[Dict[str, Any]]) -> str:
    """Qual host é "a casa" deste HAR — o PRIMEIRO documento, cronologicamente.

    🔴 A heurística óbvia está errada, e eu a escrevi antes de medir. "O host
    com mais entradas do tipo `document`" parece razoável até você lembrar que
    **iframe de rastreamento também é `document`**.

    📊 Medido em 16/08/2026 sobre os 9 HAR de `docs/intake/MATERIAIS`, a versão
    por contagem elegeu:

        MAPFRE  → `bf67246skn.bf.dynatrace.com`   (telemetria)
        Maxpar  → `www.facebook.com`              (pixel)

    Errar aqui não é cosmético: `host_portal` alimenta `classificar_origem`, e
    com o host errado o **portal de verdade vira `third_party`** enquanto o
    rastreador vira "a casa". O filtro passa a proteger o pixel.

    O primeiro documento em ordem cronológica é a navegação que a pessoa
    iniciou. Pixel e APM carregam **depois** — eles precisam de uma página para
    se pendurar. Isso não é sempre verdade, mas é verdade nos 9 HAR medidos, e
    a saída fica visível no relatório para quem quiser sobrepor com
    `host_portal=`.
    """
    docs: List[Tuple[str, str]] = []
    xhr: Dict[str, int] = {}
    todos: Dict[str, int] = {}
    for e in entradas:
        url = str(((e.get("request") or {}).get("url")) or "")
        try:
            h = (urlsplit(url).hostname or "").lower()
        except ValueError:
            continue
        if not h:
            continue
        todos[h] = todos.get(h, 0) + 1
        tipo = str(e.get("_resourceType") or "")
        if tipo == "document":
            docs.append((str(e.get("startedDateTime") or ""), h))
        elif tipo in ("xhr", "fetch"):
            xhr[h] = xhr.get(h, 0) + 1

    if docs:
        docs.sort(key=lambda par: par[0])
        return docs[0][1]
    # Sem documento — 📊 acontece de verdade: o HAR da MAPFRE tem ZERO
    # documentos, porque o `Preserve log` foi ligado depois da navegação. Aí o
    # que sobra é contar XHR, e aí mora a segunda armadilha: naquele mesmo HAR
    # o Dynatrace faz **299** chamadas contra **18** do portal. A telemetria
    # ganha a contagem bruta com folga.
    #
    # Por isso a telemetria é descontada antes de contar.
    limpo = {h: n for h, n in xhr.items() if _classificar(h, "", "xhr") != "telemetry"}
    if limpo:
        return max(limpo, key=limpo.get)
    if xhr:
        return max(xhr, key=xhr.get)
    return max(todos, key=todos.get) if todos else ""


def hosts_de_api(trafego: "Trafego", minimo: int = 1) -> List[Tuple[str, int]]:
    """Onde a API realmente mora, por contagem de respostas JSON.

    🔴 Esta função existe porque **o host da API quase nunca é o host do
    portal**, e tratar os dois como a mesma coisa faz o inferidor procurar
    contrato no lugar errado.

    📊 Medido em 16/08/2026 sobre os 9 HAR de `docs/intake/MATERIAIS`:

        Maxpar   navega em `abraseuatendimento.com.br`
                 API em    `api.autoglass.com.br`            (44 JSON)
        MAPFRE   API em    `dwwngb2iz4xom.cloudfront.net`    (62 JSON)
        Yelum    API em    `integracao.grupohdiseguros.com.br` (37 JSON)

    As duas últimas eu não sabia: a MAPFRE serve a própria API por CloudFront, e
    a Yelum (grupo HDI) pelo domínio do grupo. Nenhuma das duas seria encontrada
    procurando por `first_party`, porque para o classificador elas são
    terceiros — o que, de um ponto de vista de DNS, elas são.

    É por isso que o inferidor trabalha sobre ESTA lista, e não sobre
    `origem == "first_party"`.
    """
    contagem: Dict[str, int] = {}
    for c in trafego:
        if c.e_json and c.corpo_resp:
            if c.origem == "telemetry":
                continue
            contagem[c.host] = contagem.get(c.host, 0) + 1
    return sorted(((h, n) for h, n in contagem.items() if n >= minimo),
                  key=lambda par: (-par[1], par[0]))


def _classificar(host: str, host_portal: str, resource_type: str) -> str:
    """Usa o classificador da SPEC-073. Sem ele disponível, degrada honestamente.

    O import é tardio porque este módulo roda no `smith-api`, onde o pacote
    `portal_worker` está presente — mas também roda em ferramenta de linha de
    comando, onde o `sys.path` pode não incluí-lo. Degradar para `unknown` faz
    a chamada ser MANTIDA (o filtro só descarta `telemetry`/`asset`), que é o
    lado seguro: perder um endereço do portal é pior que analisar um pixel.
    """
    try:
        from portal_worker.profiler import classificar_origem

        return classificar_origem(host, host_portal, resource_type)
    except Exception:  # noqa: BLE001
        return "unknown"


# --------------------------------------------------------------------------
# DeepTrace → Chamada
# --------------------------------------------------------------------------
def importar_deep_trace(eventos: Iterable[Dict[str, Any]], *,
                        host_portal: str = "",
                        rotulo: str = "") -> Trafego:
    """Converte a saída do `portal_worker.deep_trace` para o mesmo formato.

    🔴 O join evento↔corpo é por `requestId`, **nunca por URL nem timestamp**.
    A mesma URL é chamada várias vezes numa navegação (polling, retry,
    paginação), e casar por URL misturaria o corpo de uma resposta com os
    cabeçalhos de outra — produzindo um schema que nunca existiu.

    (📊 Aprendido lendo o `browser-trace` do `browserbase/skills`, MIT, que
    documenta exatamente esta armadilha.)
    """
    por_id: Dict[str, Dict[str, Any]] = {}
    for ev in eventos:
        rid = str(ev.get("requestId") or ev.get("request_id") or "")
        if not rid:
            continue
        por_id.setdefault(rid, {}).update(ev)

    saida: List[Chamada] = []
    for rid, ev in por_id.items():
        url = str(ev.get("url") or "")
        if not url:
            continue
        host = ""
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            pass
        nomes = tuple(n for n in (ev.get("header_names") or ())
                      if _cabecalho_entra(n))
        saida.append(Chamada(
            metodo=str(ev.get("method") or "GET").upper(),
            url=url,
            status=int(ev.get("status") or 0),
            content_type_req=str(ev.get("content_type_req") or ""),
            content_type_resp=str(ev.get("mime_type") or ev.get("content_type") or ""),
            corpo_req=ev.get("request_body"),
            corpo_resp=ev.get("response_body"),
            resource_type=str(ev.get("resource_type") or ""),
            iniciado_em=str(ev.get("ts") or ""),
            duracao_ms=float(ev.get("duration_ms") or 0.0),
            nomes_de_header_req=nomes,
            origem=_classificar(host, host_portal,
                                str(ev.get("resource_type") or "")),
        ))
    return Trafego(chamadas=saida, fonte="deep_trace", rotulo=rotulo,
                   host_portal=host_portal)
