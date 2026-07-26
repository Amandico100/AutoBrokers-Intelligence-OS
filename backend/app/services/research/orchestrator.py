"""Research Orchestrator — o único dono da pesquisa. SPEC-060 §4.1, §6, §23.

O que "único" significa aqui
----------------------------
§4.1: provider externo pode buscar, rastrear e extrair. Ele **não** é
autoridade sobre plano, política de fontes, claims aceitos, citações
apresentadas nem classificação de risco. Este módulo é onde essa autoridade
mora — e é por isso que trocar Tavily por outro provider não muda uma linha de
Skill.

Fluxo (§23.1): intake → plan → search → fetch → extract → claims → verify →
contradiction → synthesize.

Degradação honesta (D18)
------------------------
Quando o provider de leitura está sem crédito, a pesquisa **não falha**: ela
segue com busca + leitura direta, registra a limitação com o motivo real e
declara o que não pôde ser lido. §33.6 é explícita — degradar sim, reduzir
factualidade em silêncio não.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .claim_service import (ClaimService, Veredito, detectar_contradicoes,
                            localizar_trecho, montar_citacao, verificar)
from .planner import Plano, deve_parar, deve_replanejar, planejar, resolver_modo
from .provider_router import Aquisicao, ProviderRouter
from .schemas import (DEEP, ClaimDraft, ResearchRequest, ResultadoDeFonte,
                      e_oficial)
from .source_registry import SourceRegistry
from .urls import diversidade, fingerprint

logger = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ResultadoDaPesquisa:
    ok: bool
    request_id: Optional[str] = None
    pergunta: str = ""
    modo: str = "quick"
    resumo: str = ""
    claims: list[dict] = field(default_factory=list)
    fontes: list[dict] = field(default_factory=list)
    limitacoes: list[str] = field(default_factory=list)
    contradicoes: list[dict] = field(default_factory=list)
    cobertura_de_citacao: Optional[float] = None
    fontes_oficiais: int = 0
    diversidade_de_publishers: int = 0
    creditos: float = 0.0
    duracao_ms: int = 0
    parou_porque: str = ""
    status: str = "completed"

    def como_dict(self) -> dict:
        return {
            "ok": self.ok, "request_id": self.request_id,
            "pergunta": self.pergunta, "modo": self.modo,
            "resumo": self.resumo, "claims": self.claims, "fontes": self.fontes,
            "limitacoes": self.limitacoes, "contradicoes": self.contradicoes,
            "cobertura_de_citacao": self.cobertura_de_citacao,
            "fontes_oficiais": self.fontes_oficiais,
            "publishers_distintos": self.diversidade_de_publishers,
            "creditos": self.creditos, "duracao_ms": self.duracao_ms,
            "parou_porque": self.parou_porque, "status": self.status,
        }


class ResearchOrchestrator:
    def __init__(self, supabase_client: Any, *, company_id: str,
                 work_run_id: Optional[str] = None,
                 user_id: Optional[str] = None):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)
        self.company_id = company_id
        self.work_run_id = work_run_id
        self.user_id = user_id
        self.registry = SourceRegistry(supabase_client)
        self.claims = ClaimService(supabase_client)
        self.router = ProviderRouter(supabase_client, company_id=company_id,
                                     work_run_id=work_run_id)

    # ------------------------------------------------------------------

    async def pesquisar(self, pedido: ResearchRequest) -> ResultadoDaPesquisa:
        """Executa a pesquisa ponta a ponta."""
        inicio = time.monotonic()

        ok, motivo = pedido.valido()
        if not ok:
            return ResultadoDaPesquisa(False, pergunta=pedido.question,
                                       modo=pedido.mode, resumo=motivo,
                                       status="failed")

        registro = self._registrar_pedido(pedido)
        request_id = (registro or {}).get("id")
        plano = planejar(pedido)
        self._registrar_plano(request_id, plano)

        # 1. Descoberta.
        encontradas, limitacoes = await self._descobrir(plano)
        if not encontradas:
            return self._encerrar_sem_fonte(request_id, pedido, plano,
                                            limitacoes, inicio)

        motivo_replan = deve_replanejar(
            fontes_encontradas=len(encontradas),
            oficiais_encontradas=sum(1 for f in encontradas if f.oficial),
            plano=plano)
        if motivo_replan and plano.modo == DEEP:
            # §12.3 — replan cria versão nova e fica registrado. Sem o
            # registro, ninguém entende depois por que a pesquisa custou o
            # dobro.
            plano.consultas = [f"{c} fonte oficial" for c in plano.consultas[:3]]
            self._registrar_plano(request_id, plano, versao=2,
                                  motivo=motivo_replan)
            extras, mais_limites = await self._descobrir(plano)
            encontradas = _mesclar(encontradas, extras)
            limitacoes.extend(mais_limites)

        # 2. Aquisição e extração, com as regras de parada do plano.
        aquisicoes, parou_porque = await self._adquirir(plano, encontradas, inicio)
        snapshots = self._gravar_snapshots(aquisicoes, request_id)

        for a in aquisicoes:
            if a.limitacao:
                limitacoes.append(f"{a.url}: {a.limitacao}")

        # 3. Claims a partir do que foi lido de verdade.
        rascunhos = self._extrair_claims(plano, aquisicoes, snapshots)
        contradicoes = detectar_contradicoes(rascunhos)
        gravados = self._gravar_claims(request_id, rascunhos)

        # 4. Síntese — determinística. O texto bonito é da Skill; aqui sai o
        # que os claims sustentam, nem uma palavra além.
        resumo, limitacoes_da_sintese = self._sintetizar(
            plano, gravados, aquisicoes, contradicoes)
        limitacoes.extend(limitacoes_da_sintese)

        fontes_publicas = [{
            "url": s.get("_url"), "titulo": s.get("_titulo"),
            "tier": s.get("_tier"), "oficial": s.get("_oficial"),
            "recuperado_em": s.get("retrieved_at"),
            "snapshot_id": s.get("id"),
        } for s in snapshots.values()]

        resultado = ResultadoDaPesquisa(
            ok=bool(gravados),
            request_id=request_id, pergunta=pedido.question, modo=pedido.mode,
            resumo=resumo, claims=gravados, fontes=fontes_publicas,
            limitacoes=_unicos(limitacoes), contradicoes=contradicoes,
            cobertura_de_citacao=self.claims.cobertura_de_citacao(gravados),
            fontes_oficiais=sum(1 for f in fontes_publicas if f.get("oficial")),
            diversidade_de_publishers=diversidade(
                [f["url"] for f in fontes_publicas if f.get("url")]),
            creditos=sum(a.creditos for a in aquisicoes),
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            parou_porque=parou_porque,
            status="completed" if gravados else "partial")

        self._encerrar_pedido(request_id, resultado)
        self._registrar_consumo(request_id)
        return resultado

    # ------------------------------------------------------------------
    # Etapas
    # ------------------------------------------------------------------

    async def _descobrir(self, plano: Plano) -> tuple[list[ResultadoDeFonte], list[str]]:
        fontes: list[ResultadoDeFonte] = []
        limitacoes: list[str] = []
        for consulta in plano.consultas:
            r = await self.router.buscar(
                consulta, limite=max(3, plano.max_fontes // 2),
                dominios=plano.dominios_preferidos or None,
                preferir_conteudo=(plano.modo == DEEP))
            limitacoes.extend(r.limitacoes)
            fontes = _mesclar(fontes, r.fontes)
            if len(fontes) >= plano.max_fontes * 2:
                break
        return fontes, limitacoes

    async def _adquirir(self, plano: Plano, encontradas: list[ResultadoDeFonte],
                        inicio: float) -> tuple[list[Aquisicao], str]:
        """Lê as fontes até a regra de parada disparar — §12.2."""
        # Oficiais primeiro. Quando o orçamento acaba no meio, o que sobra é
        # a fonte que mais sustenta — não a que apareceu primeiro na busca.
        ordenadas = sorted(encontradas, key=lambda f: (f.tier, -len(f.conteudo or "")))

        aquisicoes: list[Aquisicao] = []
        sem_novidade = 0
        vistos_hashes: set[str] = set()
        parou_porque = "todas as fontes do plano foram lidas"

        for fonte in ordenadas:
            gasto = time.monotonic() - inicio
            parar, motivo = deve_parar(
                fontes_lidas=len([a for a in aquisicoes if a.ok]),
                claims_novos_seguidos_sem=sem_novidade,
                subquestoes_cobertas=_cobertura(plano, aquisicoes),
                plano=plano, segundos_gastos=gasto)
            if parar:
                parou_porque = motivo
                break

            # A busca já pode ter trazido o conteúdo (Firecrawl). Reler seria
            # pagar duas vezes pela mesma página.
            if fonte.tem_conteudo():
                from .content_sanitizer import sanitizar

                saneado = sanitizar(fonte.conteudo, e_html=False)
                if saneado.seguro_para_o_modelo:
                    aquisicoes.append(Aquisicao(True, fonte.url, fonte=fonte,
                                                saneado=saneado,
                                                provider=fonte.provider))
                    continue

            a = await self.router.ler(fonte.url)
            aquisicoes.append(a)
            if a.ok and a.saneado:
                h = a.saneado.content_hash()
                # §24.5: mesma página por outro caminho não é fonte nova.
                if h in vistos_hashes:
                    sem_novidade += 1
                else:
                    vistos_hashes.add(h)
                    sem_novidade = 0
            else:
                sem_novidade += 1

        return aquisicoes, parou_porque

    def _gravar_snapshots(self, aquisicoes: list[Aquisicao],
                          request_id: Optional[str]) -> dict[str, dict]:
        snapshots: dict[str, dict] = {}
        for a in aquisicoes:
            if not (a.ok and a.fonte and a.saneado):
                continue
            snap = self.registry.gravar_snapshot(
                fonte=a.fonte, saneado=a.saneado,
                company_id=self.company_id, research_request_id=request_id,
                work_run_id=self.work_run_id,
                # Conteúdo público, sem a pergunta junto: compartilhável.
                # É o que permite a próxima corretora reaproveitar a leitura.
                compartilhavel=True)
            if snap:
                snapshots[fingerprint(a.fonte.url)] = snap
        return snapshots

    def _extrair_claims(self, plano: Plano, aquisicoes: list[Aquisicao],
                        snapshots: dict[str, dict]) -> list[ClaimDraft]:
        """Extrai afirmações do que foi lido. Determinístico.

        A extração é por sentença ancorada nos termos da subpergunta. Ela é
        deliberadamente conservadora: prefere um claim a menos, bem citado, a
        cinco claims genéricos. Um resumo com dez afirmações vagas é pior que
        três afirmações com fonte — porque as dez não podem ser conferidas.
        """
        from .planner import termos_relevantes

        rascunhos: list[ClaimDraft] = []
        vistos: set[str] = set()

        for sub in plano.subquestoes:
            termos = set(termos_relevantes(sub, maximo=6))
            if not termos:
                continue
            for a in aquisicoes:
                if not (a.ok and a.fonte and a.saneado):
                    continue
                snap = snapshots.get(fingerprint(a.fonte.url))
                if not snap:
                    continue
                for sentenca in _sentencas(a.saneado.texto):
                    baixo = sentenca.lower()
                    if sum(1 for t in termos if t in baixo) < 2:
                        continue
                    if len(sentenca) < 40 or len(sentenca) > 500:
                        continue
                    chave_texto = " ".join(baixo.split())[:120]
                    if chave_texto in vistos:
                        continue
                    vistos.add(chave_texto)

                    rascunho = ClaimDraft(
                        claim_text=sentenca,
                        claim_type=_tipo_de_claim(sentenca),
                        subquestao=sub,
                        freshness=plano.regras_de_verificacao.get(
                            "freshness", "stable") or "stable")
                    trecho = localizar_trecho(a.saneado.texto, sentenca)
                    rascunho.citacoes.append(montar_citacao(
                        a.fonte, snap, papel="supports", trecho=trecho,
                        localizador={"provider": a.provider}))
                    rascunhos.append(rascunho)
                    break  # um claim por fonte por subpergunta: evita inundar
            if len(rascunhos) >= 24:
                break

        # Reforço cruzado: o mesmo claim visto em duas fontes ganha a segunda
        # citação em vez de virar dois claims. É o que faz "duas fontes" ser
        # verdade em §7.2, e não duas linhas parecidas.
        return _fundir_equivalentes(rascunhos)

    def _gravar_claims(self, request_id: Optional[str],
                       rascunhos: list[ClaimDraft]) -> list[dict]:
        if not request_id:
            return []
        saida: list[dict] = []
        for r in rascunhos:
            v = verificar(r)
            linha = self.claims.gravar(
                company_id=self.company_id, research_request_id=request_id,
                rascunho=r, veredito=v, work_run_id=self.work_run_id)
            if linha:
                linha["_veredito"] = v.como_dict()
                linha["_citacoes_detalhe"] = r.citacoes
                saida.append(linha)
        return saida

    def _sintetizar(self, plano: Plano, claims: list[dict],
                    aquisicoes: list[Aquisicao],
                    contradicoes: list[dict]) -> tuple[str, list[str]]:
        """Resumo a partir dos claims. Sem número novo, sem conclusão nova."""
        limitacoes: list[str] = []
        sustentados = [c for c in claims
                       if c.get("status") in ("supported", "partially_supported")]
        lidas = len([a for a in aquisicoes if a.ok])
        falhas = len([a for a in aquisicoes if not a.ok])

        if not sustentados:
            limitacoes.append(
                "Nenhuma afirmação pôde ser sustentada com as fontes que "
                "conseguimos abrir. Isso não significa que a resposta não "
                "exista — significa que não a encontramos com procedência.")
            return ("Não encontrei fonte suficiente para responder com "
                    "procedência."), limitacoes

        oficiais = sum(1 for c in sustentados if int(c.get("official_citation_count") or 0))
        partes = [
            f"{len(sustentados)} afirmação(ões) sustentada(s) por {lidas} fonte(s) lida(s)"
        ]
        if oficiais:
            partes.append(f"{oficiais} com fonte oficial")
        if contradicoes:
            partes.append(f"{len(contradicoes)} divergência(s) entre fontes")
        if falhas:
            limitacoes.append(
                f"{falhas} fonte(s) não puderam ser lidas — o resultado usa "
                "apenas o que foi possível abrir.")

        if plano.exige_oficial and not oficiais:
            limitacoes.append(
                "O assunto pede fonte oficial e não encontramos nenhuma. Trate "
                "o resultado como indicação, não como regra confirmada.")

        return "; ".join(partes) + ".", limitacoes

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _registrar_pedido(self, pedido: ResearchRequest) -> Optional[dict]:
        linha = {
            "company_id": self.company_id, "user_id": self.user_id,
            "conversation_id": pedido.conversation_id,
            "work_run_id": self.work_run_id,
            "request_type": pedido.requested_by_kind,
            "requested_by_kind": pedido.requested_by_kind,
            "mode": pedido.mode, "objective": pedido.objective or pedido.question,
            "question": pedido.question, "scope": pedido.escopo,
            "constraints": pedido.restricoes,
            "requested_outputs": pedido.saidas,
            "freshness_requirement": pedido.freshness,
            "source_requirements": pedido.requisitos_de_fonte,
            "time_budget_seconds": pedido.tempo_maximo_s,
            "budget_brl": pedido.orcamento_brl,
            "status": "running",
            "idempotency_key": pedido.chave_idempotente(),
        }
        try:
            r = self.db.table("research_requests").insert(linha).execute()
            return (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                try:
                    return (self.db.table("research_requests").select("*")
                            .eq("company_id", self.company_id)
                            .eq("idempotency_key", pedido.chave_idempotente())
                            .maybe_single().execute()).data
                except Exception:  # noqa: BLE001
                    return None
            logger.error("[Research] pedido nao registrado: %s", type(exc).__name__)
            return None

    def _registrar_plano(self, request_id: Optional[str], plano: Plano, *,
                         versao: int = 1, motivo: Optional[str] = None) -> None:
        if not request_id:
            return
        try:
            self.db.table("research_plans").insert({
                "company_id": self.company_id,
                "research_request_id": request_id,
                "work_run_id": self.work_run_id,
                "version": versao, "status": "published",
                "replan_reason": motivo,
                **plano.como_linha(),
            }).execute()
        except Exception as exc:  # noqa: BLE001
            if "duplicate" not in str(exc).lower():
                logger.warning("[Research] plano nao gravado: %s", type(exc).__name__)

    def _encerrar_pedido(self, request_id: Optional[str],
                         resultado: ResultadoDaPesquisa) -> None:
        if not request_id:
            return
        try:
            self.db.table("research_requests").update({
                "status": resultado.status,
                "result_summary": resultado.resumo[:2_000],
                "limitations": "\n".join(resultado.limitacoes)[:4_000] or None,
            }).eq("id", request_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Research] encerramento: %s", type(exc).__name__)

    def _registrar_consumo(self, request_id: Optional[str]) -> None:
        """§33.2 — consumo por provider, atribuído ao tenant e ao Work Run."""
        if not self.router.usage:
            return
        linhas = []
        for u in self.router.usage:
            linhas.append({
                "company_id": self.company_id,
                "work_run_id": self.work_run_id,
                "research_request_id": request_id,
                "unit_kind": "provider_call",
                **u,
            })
        try:
            self.db.table("research_provider_usage").insert(linhas).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Research] consumo nao registrado: %s", type(exc).__name__)

    def _encerrar_sem_fonte(self, request_id, pedido, plano, limitacoes,
                            inicio) -> ResultadoDaPesquisa:
        """Nenhuma fonte encontrada. §16.3 — ausência não prova inexistência."""
        sem_credito = any("crédito" in l or "credito" in l for l in limitacoes)
        resumo = (
            "Não consegui consultar fontes agora porque o provedor de leitura "
            "da web está sem crédito. A pesquisa fica registrada e pode ser "
            "repetida assim que houver crédito."
            if sem_credito else
            "Não encontrei fonte utilizável para esta pergunta. Isso não prova "
            "que a informação não exista — apenas que não a localizei com "
            "procedência.")
        resultado = ResultadoDaPesquisa(
            False, request_id=request_id, pergunta=pedido.question,
            modo=pedido.mode, resumo=resumo,
            limitacoes=_unicos(limitacoes),
            duracao_ms=int((time.monotonic() - inicio) * 1000),
            parou_porque="nenhuma fonte encontrada",
            status="blocked" if sem_credito else "partial")
        self._encerrar_pedido(request_id, resultado)
        self._registrar_consumo(request_id)
        return resultado


# ---------------------------------------------------------------------------
# Auxiliares puros
# ---------------------------------------------------------------------------


def _sentencas(texto: str) -> list[str]:
    import re

    bruto = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú])", texto or "")
    return [" ".join(s.split()) for s in bruto if len(s.strip()) > 30]


def _tipo_de_claim(sentenca: str) -> str:
    import re

    baixo = sentenca.lower()
    if any(t in baixo for t in ("susep", "resolução", "resolucao", "circular",
                                "lei ", "norma", "regulament", "cnsp")):
        return "regulatory"
    if re.search(r"\d+\s*(%|por cento|reais|r\$)", baixo):
        return "numeric"
    if re.search(r"\b(19|20)\d{2}\b|a partir de|desde|até|passa a valer", baixo):
        return "temporal"
    if any(t in baixo for t in ("mais que", "menos que", "comparado", "enquanto")):
        return "comparative"
    if any(t in baixo for t in ("porque", "devido a", "em razão", "por causa")):
        return "causal"
    return "factual"


def _fundir_equivalentes(rascunhos: list[ClaimDraft]) -> list[ClaimDraft]:
    """Claims quase iguais viram um, com as citações somadas."""
    saida: list[ClaimDraft] = []
    for r in rascunhos:
        termos_r = {t for t in r.claim_text.lower().split() if len(t) > 5}
        fundido = False
        for existente in saida:
            termos_e = {t for t in existente.claim_text.lower().split() if len(t) > 5}
            if not termos_r or not termos_e:
                continue
            sobreposicao = len(termos_r & termos_e) / max(1, min(len(termos_r), len(termos_e)))
            if sobreposicao >= 0.75:
                for c in r.citacoes:
                    if c.get("source_snapshot_id") not in {
                            x.get("source_snapshot_id") for x in existente.citacoes}:
                        existente.citacoes.append(c)
                fundido = True
                break
        if not fundido:
            saida.append(r)
    return saida


def _mesclar(a: list[ResultadoDeFonte], b: list[ResultadoDeFonte]) -> list[ResultadoDeFonte]:
    vistos = {fingerprint(f.url) for f in a}
    saida = list(a)
    for f in b:
        fp = fingerprint(f.url)
        if fp not in vistos:
            vistos.add(fp)
            saida.append(f)
    return saida


def _cobertura(plano: Plano, aquisicoes: list[Aquisicao]) -> float:
    """Fração das subperguntas com pelo menos uma fonte lida que as menciona."""
    from .planner import termos_relevantes

    if not plano.subquestoes:
        return 1.0
    lidas = [a.saneado.texto.lower() for a in aquisicoes
             if a.ok and a.saneado]
    if not lidas:
        return 0.0
    cobertas = 0
    for sub in plano.subquestoes:
        termos = [t for t in termos_relevantes(sub, maximo=5)]
        if not termos:
            cobertas += 1
            continue
        if any(sum(1 for t in termos if t in texto) >= 2 for texto in lidas):
            cobertas += 1
    return cobertas / len(plano.subquestoes)


def _unicos(itens: list[str]) -> list[str]:
    saida: list[str] = []
    for i in itens:
        limpo = (i or "").strip()
        if limpo and limpo not in saida:
            saida.append(limpo)
    return saida[:12]


# ---------------------------------------------------------------------------
# Fachada
# ---------------------------------------------------------------------------


async def pesquisar(supabase_client: Any, *, company_id: str, pergunta: str,
                    modo: Optional[str] = None, user_id: Optional[str] = None,
                    work_run_id: Optional[str] = None,
                    conversation_id: Optional[str] = None,
                    origem: str = "user") -> ResultadoDaPesquisa:
    """Ponto único de entrada. O modo é resolvido quando não vem declarado."""
    pedido = ResearchRequest(
        company_id=company_id, question=pergunta,
        mode=modo or resolver_modo(pergunta), user_id=user_id,
        conversation_id=conversation_id, requested_by_kind=origem)
    orquestrador = ResearchOrchestrator(
        supabase_client, company_id=company_id, work_run_id=work_run_id,
        user_id=user_id)
    return await orquestrador.pesquisar(pedido)
