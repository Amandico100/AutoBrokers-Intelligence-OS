"""Escolha de provider e aquisição. SPEC-060 §9.6, §14.1 e §33.6.

O router responde uma pergunta por vez: *qual caminho tem a melhor chance de
trazer esta fonte, agora, dentro do que é permitido?*

Duas regras que definem o desenho
---------------------------------
1. **§9.6: não escolher provider só pelo menor preço.** Para fonte oficial, o
   `direct_fetch` é ao mesmo tempo o mais barato e o mais confiável — mas é a
   confiabilidade que o coloca em primeiro, não o preço. A ordem seria a mesma
   se ele custasse caro.

2. **§33.6: degradar sem reduzir factualidade em silêncio.** Quando o crédito
   acaba (D18), o sistema não finge que a fonte não existia: ele registra a
   limitação, segue com o que consegue ler e **diz o motivo real**.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .content_sanitizer import ConteudoSaneado, sanitizar
from .providers import (SEM_CHAVE, SEM_CREDITO, MOTIVO_HUMANO, registro)
from .schemas import RespostaDeProvider, ResultadoDeFonte
from .source_policy import pode_adquirir
from .urls import dominio, normalizar

logger = logging.getLogger(__name__)

# §14.1 — a hierarquia de aquisição, do mais confiável ao mais caro.
HIERARQUIA_DE_LEITURA = ("direct_fetch", "firecrawl")

# Descoberta: quem sabe achar. Firecrawl traz conteúdo junto (economiza um
# passo); Tavily é mais barato e continua vivo sem crédito de Firecrawl.
HIERARQUIA_DE_BUSCA = ("tavily", "firecrawl")


@dataclass
class Aquisicao:
    """O resultado de tentar ler uma fonte, com a história da tentativa."""

    ok: bool
    url: str
    fonte: Optional[ResultadoDeFonte] = None
    saneado: Optional[ConteudoSaneado] = None
    provider: str = ""
    tentativas: list[dict] = field(default_factory=list)
    limitacao: Optional[str] = None
    creditos: float = 0.0
    duracao_ms: int = 0

    def como_limitacao(self) -> Optional[str]:
        """Frase para o campo `limitations` do resultado — §16.4."""
        return self.limitacao


@dataclass
class ResultadoDeBusca:
    ok: bool
    fontes: list[ResultadoDeFonte] = field(default_factory=list)
    providers_usados: list[str] = field(default_factory=list)
    limitacoes: list[str] = field(default_factory=list)
    creditos: float = 0.0
    usage: list[dict] = field(default_factory=list)


class ProviderRouter:
    def __init__(self, supabase: Any = None, *,
                 company_id: Optional[str] = None,
                 work_run_id: Optional[str] = None):
        self.company_id = company_id
        self.work_run_id = work_run_id
        self.providers = registro(supabase, company_id=company_id)
        self.usage: list[dict] = []

    # ------------------------------------------------------------------

    def _registrar(self, r: RespostaDeProvider) -> None:
        self.usage.append(r.como_usage())

    def disponiveis(self) -> list[str]:
        saida = []
        for chave, p in self.providers.items():
            try:
                if p.disponivel():
                    saida.append(chave)
            except Exception:  # noqa: BLE001
                continue
        return saida

    # ------------------------------------------------------------------
    # Descoberta
    # ------------------------------------------------------------------

    async def buscar(self, consulta: str, *, limite: int = 6,
                     dominios: Optional[list[str]] = None,
                     preferir_conteudo: bool = False,
                     dias: Optional[int] = None) -> ResultadoDeBusca:
        """Busca com fallback entre providers.

        `preferir_conteudo=True` inverte a ordem para o Firecrawl, que traz o
        texto junto do resultado. Vale a pena em `deep`, onde o texto vai ser
        necessário de qualquer jeito — e não vale em `quick`, onde o snippet
        basta para decidir o que ler.
        """
        ordem = list(HIERARQUIA_DE_BUSCA)
        if preferir_conteudo:
            ordem = ["firecrawl", "tavily"]

        fontes: list[ResultadoDeFonte] = []
        usados: list[str] = []
        limitacoes: list[str] = []
        creditos = 0.0

        for chave in ordem:
            provider = self.providers.get(chave)
            if provider is None:
                continue
            try:
                if not provider.disponivel():
                    limitacoes.append(
                        f"{chave}: {MOTIVO_HUMANO[SEM_CHAVE]}")
                    continue
            except Exception:  # noqa: BLE001
                continue

            r = await provider.search(consulta, limite=limite,
                                      dominios=dominios, dias=dias,
                                      work_run_id=self.work_run_id)
            self._registrar(r)
            creditos += r.creditos

            if r.ok and r.fontes:
                fontes.extend(r.fontes)
                usados.append(chave)
                # Um provider que respondeu bem já basta para a descoberta.
                # Consultar o segundo duplicaria custo para trazer, na maior
                # parte das vezes, as mesmas URLs.
                break

            if r.sem_credito:
                limitacoes.append(f"{chave}: {r.motivo_humano}")
                continue
            if not r.ok:
                limitacoes.append(
                    f"{chave}: {r.motivo_humano or 'não respondeu'}")

        return ResultadoDeBusca(
            ok=bool(fontes), fontes=_deduplicar_fontes(fontes),
            providers_usados=usados, limitacoes=limitacoes,
            creditos=creditos, usage=list(self.usage))

    # ------------------------------------------------------------------
    # Aquisição
    # ------------------------------------------------------------------

    async def ler(self, url: str, *, exigir_conteudo: bool = True) -> Aquisicao:
        """Lê uma fonte pela hierarquia de §14.1, sanitizando o resultado.

        A ordem é confiabilidade, não preço: `direct_fetch` primeiro porque
        para fonte oficial ele traz o documento original, sem intermediário
        que possa resumir ou reescrever. Com D18 ativa, ele também é o único
        caminho que continua funcionando.
        """
        alvo = normalizar(url)
        if not alvo:
            return Aquisicao(False, url or "", limitacao="endereço inválido")

        permissao = pode_adquirir(alvo, "provider_extract")
        if not permissao.permitido:
            return Aquisicao(False, alvo, limitacao=permissao.motivo,
                             tentativas=[{"provider": "policy",
                                          "resultado": "bloqueado",
                                          "motivo": permissao.motivo}])

        tentativas: list[dict] = []
        creditos = 0.0
        duracao = 0
        sem_credito_em: list[str] = []

        for chave in HIERARQUIA_DE_LEITURA:
            provider = self.providers.get(chave)
            if provider is None:
                continue
            try:
                if not provider.disponivel():
                    tentativas.append({"provider": chave, "resultado": "indisponivel",
                                       "motivo": MOTIVO_HUMANO[SEM_CHAVE]})
                    continue
            except Exception:  # noqa: BLE001
                continue

            metodo = getattr(provider, "fetch", None) or getattr(provider, "scrape", None)
            if metodo is None:
                continue

            r = await metodo(alvo, work_run_id=self.work_run_id)
            self._registrar(r)
            creditos += r.creditos
            duracao += r.duracao_ms

            if r.ok and r.fontes:
                fonte = r.fontes[0]
                bruto = fonte.conteudo
                saneado = sanitizar(bruto, e_html=(chave == "direct_fetch"))
                # A auditoria de site precisa do HTML original: os sinais
                # técnicos (title, canonical, dado estruturado) vivem
                # exatamente nas tags que o sanitizador remove. O bruto fica
                # em metadata, NUNCA em `conteudo` — o que vai para o modelo
                # continua sendo só o texto saneado.
                if chave == "direct_fetch" and len(bruto or "") <= 400_000:
                    fonte.metadata = {**(fonte.metadata or {}), "html": bruto}
                fonte.conteudo = saneado.texto
                tentativas.append({"provider": chave, "resultado": "ok",
                                   "caracteres": len(saneado.texto),
                                   "injection": saneado.status})

                if exigir_conteudo and len(saneado.texto.strip()) < 200:
                    # Página que devolve casca: continua para o próximo
                    # provider em vez de virar uma "fonte" sem conteúdo.
                    tentativas[-1]["resultado"] = "conteudo_insuficiente"
                    continue

                if not saneado.seguro_para_o_modelo:
                    # §15.4 — quarentena não vai para o modelo. A fonte fica
                    # registrada com o motivo, e o resultado declara isso.
                    return Aquisicao(
                        False, alvo, provider=chave, saneado=saneado,
                        tentativas=tentativas, creditos=creditos,
                        duracao_ms=duracao,
                        limitacao=("conteúdo colocado em quarentena por tentativa "
                                   "de manipulação detectada na página"))

                return Aquisicao(True, alvo, fonte=fonte, saneado=saneado,
                                 provider=chave, tentativas=tentativas,
                                 creditos=creditos, duracao_ms=duracao)

            if r.sem_credito:
                sem_credito_em.append(chave)
            tentativas.append({"provider": chave, "resultado": "falha",
                               "motivo": r.erro,
                               "mensagem": r.motivo_humano})

        # §14.6 — conteúdo inalcançável não se contorna. Registra o motivo, a
        # tentativa e o impacto na confiança.
        if sem_credito_em:
            limitacao = MOTIVO_HUMANO[SEM_CREDITO]
        else:
            limitacao = "não foi possível ler esta fonte por nenhum caminho permitido"

        return Aquisicao(False, alvo, tentativas=tentativas, creditos=creditos,
                         duracao_ms=duracao, limitacao=limitacao)

    async def ler_varias(self, urls: list[str], *, maximo: int = 10
                         ) -> list[Aquisicao]:
        """Lê em sequência, respeitando o teto.

        Sequencial de propósito: paralelizar leitura de um mesmo domínio é a
        forma mais rápida de ser tratado como abuso, e a política de taxa por
        fonte (§8.4) existe justamente para não chegarmos lá.
        """
        saida: list[Aquisicao] = []
        por_dominio: dict[str, int] = {}
        for u in urls[: maximo * 2]:
            if len(saida) >= maximo:
                break
            host = dominio(u)
            if por_dominio.get(host, 0) >= 4:
                continue  # não concentra o crawl num único site
            por_dominio[host] = por_dominio.get(host, 0) + 1
            saida.append(await self.ler(u))
        return saida


def _deduplicar_fontes(fontes: list[ResultadoDeFonte]) -> list[ResultadoDeFonte]:
    """Uma URL, uma fonte. Preserva a de maior autoridade quando repete."""
    from .urls import fingerprint

    melhor: dict[str, ResultadoDeFonte] = {}
    ordem: list[str] = []
    for f in fontes:
        fp = fingerprint(f.url)
        atual = melhor.get(fp)
        if atual is None:
            melhor[fp] = f
            ordem.append(fp)
            continue
        # Empate resolvido por tier (menor é melhor) e depois por conteúdo.
        if (f.tier, -len(f.conteudo or "")) < (atual.tier, -len(atual.conteudo or "")):
            melhor[fp] = f
    return [melhor[fp] for fp in ordem]
