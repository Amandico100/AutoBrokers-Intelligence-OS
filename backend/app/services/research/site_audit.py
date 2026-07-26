"""Auditoria de site: SEO, AEO e discoverability. SPEC-060 §21.

O que muda para a corretora
---------------------------
Ela não quer um relatório de SEO. Ela quer ser **encontrada** — no Google e,
cada vez mais, dentro da resposta que uma IA dá para "corretor de seguros em
Joinville". A segunda parte (AEO) é onde quase toda auditoria de mercado ainda
não olha, e é a que mais cresce.

A promessa que este módulo NÃO faz
----------------------------------
§21.4 é explícita: **não prometer ranking nem citação por IA**. Ninguém
controla isso. O que dá para afirmar é o que está tecnicamente no caminho —
página sem título, sem dado estruturado, sem resposta direta, sem NAP
consistente. Isso é verificável, e é o que sai aqui.

Cada achado carrega evidência (o que foi encontrado na página) e prioridade
calculada, não opinião.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extração — pura, sobre o HTML bruto
# ---------------------------------------------------------------------------

_TITULO = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META = re.compile(r"<meta\s+([^>]+)>", re.I)
_H = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.I | re.S)
_CANONICAL = re.compile(r"<link[^>]+rel=[\"']canonical[\"'][^>]*>", re.I)
_HREF = re.compile(r"<link[^>]+href=[\"']([^\"']+)[\"']", re.I)
_JSONLD = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.I | re.S)
_IMG_SEM_ALT = re.compile(r"<img(?![^>]*\balt\s*=)[^>]*>", re.I)
_TAGS = re.compile(r"<[^>]+>")

# Sinais de que a página responde perguntas — o que a IA cita.
_PERGUNTA = re.compile(r"<h[2-4][^>]*>\s*[^<]*\?\s*</h[2-4]>", re.I)

TELEFONE = re.compile(r"(?:\+?55\s*)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}")
CEP = re.compile(r"\b\d{5}-?\d{3}\b")


@dataclass
class Pagina:
    url: str
    titulo: str = ""
    descricao: str = ""
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    canonical: Optional[str] = None
    tem_jsonld: bool = False
    tipos_jsonld: list[str] = field(default_factory=list)
    imagens_sem_alt: int = 0
    palavras: int = 0
    perguntas_respondidas: int = 0
    tem_telefone: bool = False
    tem_endereco: bool = False
    noindex: bool = False
    idioma: Optional[str] = None
    status: Optional[int] = None


def analisar_pagina(url: str, html: str, *, status: Optional[int] = None) -> Pagina:
    """Extrai os sinais técnicos de uma página. Puro — §21.2."""
    bruto = html or ""
    p = Pagina(url=url, status=status)

    m = _TITULO.search(bruto)
    if m:
        p.titulo = " ".join(_TAGS.sub(" ", m.group(1)).split())[:300]

    for atributos in _META.findall(bruto):
        baixo = atributos.lower()
        conteudo = ""
        c = re.search(r"content=[\"']([^\"']*)[\"']", atributos, re.I)
        if c:
            conteudo = c.group(1).strip()
        if "name=\"description\"" in baixo or "name='description'" in baixo:
            p.descricao = conteudo[:400]
        if "name=\"robots\"" in baixo or "name='robots'" in baixo:
            if "noindex" in conteudo.lower():
                p.noindex = True

    for nivel, texto in _H.findall(bruto):
        limpo = " ".join(_TAGS.sub(" ", texto).split())[:200]
        if not limpo:
            continue
        if nivel == "1":
            p.h1.append(limpo)
        elif nivel == "2":
            p.h2.append(limpo)

    canon = _CANONICAL.search(bruto)
    if canon:
        href = _HREF.search(canon.group(0))
        if href:
            p.canonical = href.group(1)

    for bloco in _JSONLD.findall(bruto):
        p.tem_jsonld = True
        for tipo in re.findall(r"[\"']@type[\"']\s*:\s*[\"']([^\"']+)[\"']", bloco):
            if tipo not in p.tipos_jsonld:
                p.tipos_jsonld.append(tipo)

    p.imagens_sem_alt = len(_IMG_SEM_ALT.findall(bruto))
    p.perguntas_respondidas = len(_PERGUNTA.findall(bruto))

    texto = _TAGS.sub(" ", bruto)
    p.palavras = len(texto.split())
    p.tem_telefone = bool(TELEFONE.search(texto))
    p.tem_endereco = bool(CEP.search(texto))

    lang = re.search(r"<html[^>]+lang=[\"']([^\"']+)[\"']", bruto, re.I)
    if lang:
        p.idioma = lang.group(1)
    return p


# ---------------------------------------------------------------------------
# Achados
# ---------------------------------------------------------------------------


@dataclass
class Achado:
    chave: str
    titulo: str
    detalhe: str
    impacto: str          # alto | medio | baixo
    esforco: str          # baixo | medio | alto
    categoria: str        # tecnico | conteudo | aeo | local
    evidencia: str = ""
    paginas: list[str] = field(default_factory=list)

    @property
    def prioridade(self) -> int:
        """Impacto alto e esforço baixo primeiro. Ordem de execução, não nota.

        Um relatório que lista trinta problemas sem dizer por onde começar não
        é acionável — e o corretor não vai fazer nenhum.
        """
        peso_impacto = {"alto": 3, "medio": 2, "baixo": 1}.get(self.impacto, 1)
        peso_esforco = {"baixo": 3, "medio": 2, "alto": 1}.get(self.esforco, 2)
        return peso_impacto * 10 + peso_esforco

    def como_dict(self) -> dict:
        return {"chave": self.chave, "titulo": self.titulo,
                "detalhe": self.detalhe, "impacto": self.impacto,
                "esforco": self.esforco, "categoria": self.categoria,
                "evidencia": self.evidencia, "paginas": self.paginas[:5],
                "prioridade": self.prioridade}


def auditar(paginas: list[Pagina], *, robots: Optional[str] = None,
            tem_sitemap: bool = False) -> list[Achado]:
    """Achados priorizados. Puro — §21.2, §21.3 e §21.4.

    Só entra achado **verificável na página**. Nada de "seu conteúdo poderia
    ser mais envolvente": isso é opinião, e opinião num relatório técnico
    contamina o que é fato.
    """
    achados: list[Achado] = []
    if not paginas:
        return achados

    def _add(chave, titulo, detalhe, impacto, esforco, categoria,
             evidencia="", urls=None):
        achados.append(Achado(chave, titulo, detalhe, impacto, esforco,
                              categoria, evidencia, urls or []))

    sem_titulo = [p for p in paginas if not p.titulo]
    if sem_titulo:
        _add("titulo_ausente", "Páginas sem título",
             "O título é o que aparece como link no resultado de busca. Sem ele, "
             "o buscador inventa um a partir do texto — e quase sempre escolhe mal.",
             "alto", "baixo", "tecnico",
             f"{len(sem_titulo)} de {len(paginas)} páginas", [p.url for p in sem_titulo])

    titulos_curtos = [p for p in paginas if p.titulo and len(p.titulo) < 25]
    if titulos_curtos:
        _add("titulo_curto", "Títulos curtos demais",
             "Título com menos de 25 caracteres desperdiça o espaço que o "
             "buscador dá e raramente contém a cidade ou o produto.",
             "medio", "baixo", "tecnico",
             f"{len(titulos_curtos)} página(s)", [p.url for p in titulos_curtos])

    sem_descricao = [p for p in paginas if not p.descricao]
    if sem_descricao:
        _add("descricao_ausente", "Páginas sem descrição",
             "A descrição é o texto abaixo do link no Google. Sem ela, o "
             "buscador recorta um trecho qualquer da página.",
             "medio", "baixo", "tecnico",
             f"{len(sem_descricao)} de {len(paginas)}", [p.url for p in sem_descricao])

    sem_h1 = [p for p in paginas if not p.h1]
    if sem_h1:
        _add("h1_ausente", "Páginas sem título principal na tela",
             "O H1 diz do que a página trata. Sem ele, buscador e leitor de "
             "tela precisam adivinhar a hierarquia do conteúdo.",
             "medio", "baixo", "tecnico",
             f"{len(sem_h1)} página(s)", [p.url for p in sem_h1])

    multiplos_h1 = [p for p in paginas if len(p.h1) > 1]
    if multiplos_h1:
        _add("h1_multiplo", "Mais de um título principal na mesma página",
             "Dois H1 competem entre si e diluem o assunto da página.",
             "baixo", "baixo", "tecnico",
             f"{len(multiplos_h1)} página(s)", [p.url for p in multiplos_h1])

    noindex = [p for p in paginas if p.noindex]
    if noindex:
        _add("noindex", "Páginas bloqueadas para o buscador",
             "Estas páginas pedem explicitamente para não aparecer na busca. "
             "Se isso não foi intencional, elas estão invisíveis.",
             "alto", "baixo", "tecnico",
             f"{len(noindex)} página(s)", [p.url for p in noindex])

    if not tem_sitemap:
        _add("sitemap_ausente", "Sem mapa do site",
             "O sitemap.xml é como o buscador descobre páginas que não estão "
             "ligadas no menu.", "medio", "baixo", "tecnico")

    if robots is None:
        _add("robots_ausente", "Sem arquivo robots.txt",
             "Sem robots.txt o buscador assume que pode tudo — o que costuma "
             "funcionar, mas tira seu controle sobre o que é rastreado.",
             "baixo", "baixo", "tecnico")
    elif "disallow: /" in (robots or "").lower().replace(" ", " "):
        linhas = [l for l in (robots or "").splitlines()
                  if l.strip().lower().replace(" ", "") == "disallow:/"]
        if linhas:
            _add("robots_bloqueia_tudo", "O robots.txt bloqueia o site inteiro",
                 "Existe uma regra `Disallow: /` — ela pede que nada do site "
                 "seja rastreado. É o bloqueio mais grave possível.",
                 "alto", "baixo", "tecnico", evidencia="Disallow: /")

    # --- AEO / GEO — §21.4
    sem_jsonld = [p for p in paginas if not p.tem_jsonld]
    if sem_jsonld:
        _add("dados_estruturados_ausentes", "Sem dados estruturados",
             "Dado estruturado é como o site declara, em linguagem de máquina, "
             "que é uma corretora, onde fica e o que oferece. É o formato que "
             "buscadores e assistentes leem primeiro para montar resposta.",
             "alto", "medio", "aeo",
             f"{len(sem_jsonld)} de {len(paginas)} páginas",
             [p.url for p in sem_jsonld])

    tipos = {t for p in paginas for t in p.tipos_jsonld}
    if tipos and not (tipos & {"InsuranceAgency", "LocalBusiness",
                               "Organization", "FinancialService"}):
        _add("sem_tipo_de_negocio", "Dados estruturados sem o tipo de negócio",
             "Existe dado estruturado, mas nenhum declara que isto é uma "
             "corretora ou um negócio local. É o campo que faz aparecer em "
             "busca por região.", "medio", "baixo", "aeo",
             f"tipos encontrados: {', '.join(sorted(tipos))[:120]}")

    sem_perguntas = [p for p in paginas
                     if p.perguntas_respondidas == 0 and p.palavras > 300]
    if len(sem_perguntas) >= max(1, len(paginas) // 2):
        _add("sem_respostas_diretas", "O conteúdo não responde perguntas",
             "Assistentes de IA citam trechos que respondem uma pergunta direta. "
             "Páginas escritas só como texto corrido raramente são citadas.",
             "alto", "medio", "aeo",
             f"{len(sem_perguntas)} página(s) longas sem nenhuma pergunta como subtítulo",
             [p.url for p in sem_perguntas])

    rasas = [p for p in paginas if 0 < p.palavras < 250]
    if rasas:
        _add("conteudo_raso", "Páginas com pouco conteúdo",
             "Página com menos de 250 palavras raramente tem o que responder — "
             "e concorre com páginas que têm.", "medio", "alto", "conteudo",
             f"{len(rasas)} página(s)", [p.url for p in rasas])

    # --- Local — §21.3 (consistência NAP)
    com_telefone = sum(1 for p in paginas if p.tem_telefone)
    com_endereco = sum(1 for p in paginas if p.tem_endereco)
    if com_telefone == 0:
        _add("sem_telefone", "Telefone não encontrado no site",
             "Busca local usa nome, endereço e telefone para confirmar que o "
             "negócio existe e onde fica.", "alto", "baixo", "local")
    if com_endereco == 0:
        _add("sem_endereco", "Endereço não encontrado no site",
             "Sem endereço, a corretora não aparece em busca por cidade nem "
             "no mapa.", "alto", "baixo", "local")

    sem_alt = sum(p.imagens_sem_alt for p in paginas)
    if sem_alt >= 5:
        _add("imagens_sem_descricao", "Imagens sem descrição",
             "A descrição da imagem serve para acessibilidade e para busca por "
             "imagem.", "baixo", "baixo", "tecnico", f"{sem_alt} imagem(ns)")

    sem_canonical = [p for p in paginas if not p.canonical]
    if len(sem_canonical) >= max(2, len(paginas) // 2):
        _add("sem_canonical", "Páginas sem endereço canônico",
             "O canônico diz qual é o endereço oficial de uma página quando "
             "ela pode ser acessada por mais de uma URL. Sem ele, o buscador "
             "divide a força entre as versões.",
             "medio", "baixo", "tecnico",
             f"{len(sem_canonical)} página(s)", [p.url for p in sem_canonical])

    return sorted(achados, key=lambda a: -a.prioridade)


def resumo_da_auditoria(paginas: list[Pagina], achados: list[Achado]) -> dict:
    """Números da auditoria. Todos contados, nenhum estimado."""
    altos = [a for a in achados if a.impacto == "alto"]
    return {
        "paginas_analisadas": len(paginas),
        "achados": len(achados),
        "achados_de_alto_impacto": len(altos),
        "com_dados_estruturados": sum(1 for p in paginas if p.tem_jsonld),
        "com_titulo": sum(1 for p in paginas if p.titulo),
        "com_descricao": sum(1 for p in paginas if p.descricao),
        "bloqueadas_para_busca": sum(1 for p in paginas if p.noindex),
        "primeiro_passo": altos[0].titulo if altos else (
            achados[0].titulo if achados else None),
    }


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


class SiteAudit:
    def __init__(self, supabase_client: Any, *, company_id: str,
                 work_run_id: Optional[str] = None):
        self.raw = supabase_client
        self.company_id = company_id
        self.work_run_id = work_run_id

    async def auditar_site(self, url_base: str, *, max_paginas: int = 12) -> dict:
        """Mapeia, lê e audita. Degrada com elegância sem crédito (D18)."""
        from .provider_router import ProviderRouter
        from .urls import dominio, normalizar

        base = normalizar(url_base)
        if not base:
            return {"ok": False, "erro": "endereço do site inválido"}

        router = ProviderRouter(self.raw, company_id=self.company_id,
                                work_run_id=self.work_run_id)
        limitacoes: list[str] = []

        # §14.2 — mapear antes de rastrear.
        urls = [base]
        firecrawl = router.providers.get("firecrawl")
        if firecrawl is not None and firecrawl.disponivel():
            mapa = await firecrawl.map_site(base, limite=max_paginas * 3,
                                            work_run_id=self.work_run_id)
            if mapa.ok:
                urls = [f.url for f in mapa.fontes][:max_paginas] or [base]
            elif mapa.sem_credito:
                limitacoes.append(
                    "O mapeamento completo do site depende do provedor de "
                    "leitura, que está sem crédito. A auditoria cobriu apenas "
                    "a página inicial e o que está ligado a ela.")
        else:
            limitacoes.append(
                "O mapeamento completo do site não está disponível nesta "
                "instalação. A auditoria cobriu a página inicial.")

        # `robots.txt` e `sitemap.xml` são leitura direta e não dependem de
        # provider — continuam funcionando sem crédito.
        robots = await self._ler_texto(router, f"https://{dominio(base)}/robots.txt")
        sitemap = await self._ler_texto(router, f"https://{dominio(base)}/sitemap.xml")

        paginas: list[Pagina] = []
        for u in urls[:max_paginas]:
            a = await router.ler(u, exigir_conteudo=False)
            if a.ok and a.fonte:
                # A análise precisa do HTML BRUTO — o sanitizador remove
                # justamente as tags que carregam os sinais técnicos.
                bruto = (a.fonte.metadata or {}).get("html") or a.fonte.conteudo
                paginas.append(analisar_pagina(u, bruto, status=a.fonte.http_status))
            elif a.limitacao:
                limitacoes.append(f"{u}: {a.limitacao}")

        if not paginas:
            return {"ok": False, "limitacoes": limitacoes or [
                "Não consegui abrir nenhuma página do site."],
                "erro": "nenhuma página pôde ser lida"}

        achados = auditar(paginas, robots=robots, tem_sitemap=bool(sitemap))
        return {
            "ok": True, "site": base,
            "resumo": resumo_da_auditoria(paginas, achados),
            "achados": [a.como_dict() for a in achados],
            "paginas": [{"url": p.url, "titulo": p.titulo,
                         "palavras": p.palavras,
                         "dados_estruturados": p.tem_jsonld} for p in paginas],
            "limitacoes": limitacoes,
        }

    async def _ler_texto(self, router: Any, url: str) -> Optional[str]:
        a = await router.ler(url, exigir_conteudo=False)
        if a.ok and a.saneado:
            return a.saneado.texto
        return None
