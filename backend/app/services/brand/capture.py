"""Captura da identidade da corretora. SPEC-057 §Bloco A.

Orquestra: fontes declaradas → busca → sinais → logo → paleta → sistema de
design → procedência campo a campo → versão.

Três regras que não se negociam
-------------------------------
1. **O logo manda na cor.** Ficou provado no primeiro site real testado: o CSS
   da Resulta devolve `#f78da7`, `#cf2e2e`, `#ff6900`, `#fcb900` — a paleta
   padrão do editor do WordPress, sem uma única cor da marca. O logo devolve
   `#1D5579` e `#EE7501`, que são a marca. CSS entra como confirmação, nunca
   como origem.

2. **Edição humana nunca é sobrescrita.** Recaptura respeita `human_edited`.
   Automação que desfaz decisão do dono não é automação, é perda de controle.

3. **Todo campo carrega de onde veio e com que confiança.** É o que permite ao
   corretor conferir em vez de aceitar mágica.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from .color import cores_css_confiaveis as _cores_css_confiaveis, parse_color
from .extract import analisar_logo
from .system import FALLBACK_ACENTO, FALLBACK_PRIMARIA, build_design_system
from .web import SinaisWeb, baixar_binario, coletar

logger = logging.getLogger(__name__)

CAMPOS_TEXTO = (
    "display_name", "legal_name", "tagline", "mission", "about_md",
    "service_area", "susep_code",
)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_url(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    try:
        p = urlparse(u)
        return u if p.hostname else None
    except Exception:  # noqa: BLE001
        return None


@dataclass
class CampoProposto:
    """Um valor candidato, com sua origem. A origem viaja junto do valor."""

    valor: Any
    source_kind: str
    source_detail: str = ""
    confidence: float = 0.5
    source_id: Optional[str] = None


@dataclass
class ResultadoCaptura:
    profile_id: str
    campos: dict[str, CampoProposto] = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)
    completeness: float = 0.0
    status: str = "captured"
    erro: Optional[str] = None
    avisos: list[str] = field(default_factory=list)


class BrandCaptureService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Perfil
    # ------------------------------------------------------------------

    def obter_ou_criar(self, company_id: str) -> dict:
        # `limit(1)` e nao `maybe_single()`: o PostgREST responde HTTP 406 quando
        # maybe_single nao acha linha, e isso aparece no log como erro numa
        # situacao que e o caminho normal — primeira visita da corretora. Log
        # que grita em fluxo normal treina quem le a ignorar log.
        try:
            r = (self.db.table("brand_profiles").select("*")
                 .eq("company_id", company_id).limit(1).execute())
            if r and r.data:
                return r.data[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] leitura de perfil falhou: %s", type(exc).__name__)
        novo = (self.db.table("brand_profiles")
                .insert({"company_id": company_id}).execute()).data
        return novo[0] if novo else {}

    def _protegidos(self, profile_id: str) -> set[str]:
        """Campos que o humano editou — recaptura não encosta."""
        r = (self.db.table("brand_field_provenance")
             .select("field_path").eq("brand_profile_id", profile_id)
             .eq("human_edited", True).execute())
        return {x["field_path"] for x in (r.data or [])}

    # ------------------------------------------------------------------
    # Captura
    # ------------------------------------------------------------------

    async def capturar(self, company_id: str, *, run_id: Optional[str] = None,
                       forcar: bool = False) -> ResultadoCaptura:
        perfil = self.obter_ou_criar(company_id)
        pid = perfil["id"]

        urls = {
            "website": _norm_url(perfil.get("website_url")),
            "instagram": _norm_url(perfil.get("instagram_url")),
            "linkedin": _norm_url(perfil.get("linkedin_url")),
            "google_business": _norm_url(perfil.get("google_business_url")),
            "facebook": _norm_url(perfil.get("facebook_url")),
        }
        declaradas = [u for u in urls.values() if u]
        if not declaradas:
            return ResultadoCaptura(pid, status="empty",
                                    erro="nenhuma fonte declarada — informe ao menos o site")

        self.db.table("brand_profiles").update({
            "capture_status": "capturing", "capture_run_id": run_id,
            "capture_error": None, "updated_at": _agora(),
        }).eq("id", pid).execute()

        resultado = ResultadoCaptura(pid)
        protegidos = set() if forcar else self._protegidos(pid)
        sinais_por_fonte: dict[str, SinaisWeb] = {}

        # ---- 1. buscar cada fonte declarada -------------------------------
        for kind, url in urls.items():
            if not url:
                continue
            inicio = time.monotonic()
            try:
                sinais = await coletar(url, allowlist=declaradas,
                                       supabase=self.db, company_id=company_id)
                ok = bool(sinais.http_status and sinais.http_status < 400)
                fonte = {
                    "company_id": company_id, "brand_profile_id": pid, "kind": kind,
                    "url": url, "status": "fetched" if ok else "failed",
                    "http_status": sinais.http_status,
                    "fetched_at": _agora(),
                    "duration_ms": int((time.monotonic() - inicio) * 1000),
                    "extract": sinais.as_extract(),
                    "content_hash": hashlib.sha256(
                        (sinais.texto_md or "").encode("utf-8")).hexdigest()[:32],
                }
                if ok:
                    sinais_por_fonte[kind] = sinais
                else:
                    fonte["error"] = f"HTTP {sinais.http_status}"
                    resultado.avisos.append(f"{kind}: HTTP {sinais.http_status}")
            except Exception as exc:  # noqa: BLE001
                fonte = {
                    "company_id": company_id, "brand_profile_id": pid, "kind": kind,
                    "url": url, "status": "blocked" if "Egress" in type(exc).__name__ else "failed",
                    "error": type(exc).__name__,
                    "duration_ms": int((time.monotonic() - inicio) * 1000),
                    "fetched_at": _agora(), "extract": {},
                }
                resultado.avisos.append(f"{kind}: {type(exc).__name__}")

            gravada = (self.db.table("brand_sources").insert(fonte).execute()).data
            if gravada:
                fonte["id"] = gravada[0]["id"]
            resultado.sources.append(fonte)

        site = sinais_por_fonte.get("website")
        id_do_site = next((f.get("id") for f in resultado.sources
                           if f["kind"] == "website"), None)

        # ---- 2. texto ------------------------------------------------------
        if site:
            self._propor_texto(resultado, site, id_do_site)

        # ---- 3. logo e cor -------------------------------------------------
        await self._propor_visual(resultado, company_id, pid, site, declaradas, id_do_site)

        # ---- 4. gravar respeitando o que é humano --------------------------
        aplicados = self._aplicar(company_id, pid, resultado, protegidos)
        # O mesmo dado alimenta o cadastro da empresa. Fazer o corretor digitar
        # CNPJ e endereço duas vezes é pedir para ter duas verdades diferentes.
        self._completar_cadastro(company_id, site)
        resultado.completeness = self._completude(company_id, pid)

        status = "captured" if aplicados else "partial"
        if not sinais_por_fonte:
            status = "failed"
        self.db.table("brand_profiles").update({
            "capture_status": status, "captured_at": _agora(),
            "completeness": resultado.completeness,
            "capture_error": "; ".join(resultado.avisos[:3]) or None,
            "updated_at": _agora(),
        }).eq("id", pid).execute()
        resultado.status = status

        self._versionar(company_id, pid, "capture", sorted(aplicados))
        return resultado

    # ------------------------------------------------------------------
    # Propostas
    # ------------------------------------------------------------------

    def _propor_texto(self, res: ResultadoCaptura, s: SinaisWeb, sid: Optional[str]) -> None:
        def por(campo: str, valor, conf: float, detalhe: str = "") -> None:
            if valor:
                res.campos[campo] = CampoProposto(
                    valor, "website", detalhe or s.url, conf, sid)

        por("display_name", s.nome or _nome_do_titulo(s.titulo), 0.85 if s.nome else 0.55,
            "og:site_name / JSON-LD" if s.nome else "<title>")
        por("legal_name", s.legal_name, 0.90, "JSON-LD legalName")

        # `og:title` costuma ser título de SEO, não slogan. Só vira tagline se
        # parecer frase de marca: curta e sem separador de SEO.
        if s.tagline and len(s.tagline) < 90 and "|" not in s.tagline:
            por("tagline", s.tagline, 0.60, "og:title")
        elif s.descricao:
            frase = s.descricao.split(".")[0].strip()
            if 18 < len(frase) < 130:
                por("tagline", frase, 0.45, "meta description (1ª frase)")

        por("about_md", s.descricao, 0.70, "meta description")

        if s.servicos:
            res.campos["services"] = CampoProposto(
                [{"name": n, "source": "site"} for n in s.servicos],
                "website", "vocabulário de ramos no texto do site", 0.75, sid)

        contato = {}
        if s.telefones:
            contato["phones"] = s.telefones[:6]
        if s.emails:
            contato["emails"] = s.emails[:4]
        if s.endereco:
            contato["address"] = {k: v for k, v in s.endereco.items() if v}
        if s.sociais.get("whatsapp"):
            contato["whatsapp"] = s.sociais["whatsapp"]
        if contato:
            res.campos["contact"] = CampoProposto(contato, "website", s.url, 0.80, sid)

        if s.endereco.get("cidade"):
            uf = s.endereco.get("uf") or ""
            por("service_area", f"{s.endereco['cidade']}{' - ' + uf if uf else ''}",
                0.70, "JSON-LD address")

        for rede in ("instagram", "linkedin", "facebook"):
            if s.sociais.get(rede):
                res.campos[f"{rede}_url"] = CampoProposto(
                    s.sociais[rede], "website", "link no rodapé/cabeçalho", 0.85, sid)

    async def _propor_visual(self, res: ResultadoCaptura, company_id: str, pid: str,
                             s: Optional[SinaisWeb], allowlist: list[str],
                             sid: Optional[str]) -> None:
        """Baixa candidatos a logo, mede a tinta e monta o sistema de design."""
        analise = None
        origem_logo = ""
        asset_id = None

        candidatos: list[str] = []
        if s:
            candidatos = list(dict.fromkeys(s.logo_urls + s.icon_urls[:2]
                                            + ([s.og_image] if s.og_image else [])))

        for url in candidatos[:5]:
            try:
                dados, mime = await baixar_binario(url, allowlist=allowlist + [url])
            except Exception as exc:  # noqa: BLE001
                res.avisos.append(f"logo {type(exc).__name__}")
                continue
            if not dados:
                continue
            a = analisar_logo(dados, mime)
            if not a or not a.ink_colors:
                continue

            gravado = (self.db.table("brand_assets").upsert({
                "company_id": company_id,
                "kind": "logo_primary" if a.primary and not analise else "symbol",
                "storage_ref": url,          # SPEC-057 B: reescrito ao subir p/ storage
                "mime_type": mime.split(";")[0] or None,
                "byte_size": len(dados), "width": a.width, "height": a.height,
                "has_transparency": a.has_transparency,
                "ink_colors": [c.as_dict() for c in a.ink_colors],
                "source_url": url, "source_kind": "website",
                "confidence": a.confidence, "is_current": analise is None,
            }, on_conflict="company_id,kind").execute()).data
            res.assets.append({"url": url, "confidence": a.confidence,
                               "cores": [c.hex for c in a.ink_colors[:3]]})
            if analise is None and a.confidence >= 0.4:
                analise, origem_logo = a, url
                asset_id = gravado[0]["id"] if gravado else None

        # --- decidir a cor ---------------------------------------------------
        primaria = acento = None
        conf = 0.30
        detalhe = "padrão da casa (nenhuma fonte de cor confiável)"
        origem = "default"

        if analise and analise.primary:
            primaria, acento = analise.primary, analise.accent
            conf, origem = analise.confidence, "logo_pixels"
            detalhe = f"área de tinta do logo ({origem_logo})"
        elif s and s.theme_color and parse_color(s.theme_color):
            # Declarada pelo dono para a barra do navegador. Sinal médio: é
            # escolha consciente, mas muitos temas preenchem sozinhos.
            primaria, conf, origem = s.theme_color, 0.55, "website"
            detalhe = "<meta name=theme-color>"
        else:
            css = _cores_css_confiaveis(s.cores_css if s else [])
            if css:
                primaria, conf, origem = css[0], 0.35, "website"
                acento = css[1] if len(css) > 1 else None
                detalhe = "variável CSS de marca (sinal fraco)"
                res.avisos.append(
                    "cor vinda do CSS — confira: temas prontos costumam trazer "
                    "a paleta do editor, não a da marca")

        if not primaria:
            primaria, acento = FALLBACK_PRIMARIA, FALLBACK_ACENTO

        tipografia = {}
        if s and s.fontes:
            fam = s.fontes[0]
            tipografia = {"body": f"'{fam}', system-ui, sans-serif",
                          "display": f"'{fam}', Georgia, serif", "source": "google fonts do site"}

        sistema = build_design_system(primaria, acento, typography=tipografia or None)

        res.campos["palette"] = CampoProposto(
            {"primary": sistema["primary"], "accent": sistema["accent"],
             "scales": sistema["scales"], "themes": sistema["themes"],
             "audit": sistema["audit"], "origin": origem},
            origem, detalhe, conf, sid)

        if tipografia:
            res.campos["typography"] = CampoProposto(
                sistema["typography"], "website",
                f"Google Fonts declarada no site ({s.fontes[0]})", 0.75, sid)
        else:
            res.campos["typography"] = CampoProposto(
                sistema["typography"], "default", "tipografia padrão da casa", 0.30, sid)

        if asset_id:
            res.campos["logo_asset_id"] = CampoProposto(
                asset_id, "website", origem_logo, analise.confidence if analise else 0.4, sid)

    # ------------------------------------------------------------------
    # Gravação
    # ------------------------------------------------------------------

    def _aplicar(self, company_id: str, pid: str, res: ResultadoCaptura,
                 protegidos: set[str]) -> set[str]:
        patch: dict[str, Any] = {}
        aplicados: set[str] = set()

        for campo, proposto in res.campos.items():
            if campo in protegidos:
                continue
            patch[campo] = proposto.valor
            aplicados.add(campo)

            self.db.table("brand_field_provenance").upsert({
                "company_id": company_id, "brand_profile_id": pid,
                "field_path": campo, "source_id": proposto.source_id,
                "source_kind": proposto.source_kind,
                "source_detail": proposto.source_detail[:500],
                "confidence": round(min(max(proposto.confidence, 0.0), 1.0), 2),
                "human_edited": False, "captured_at": _agora(),
            }, on_conflict="brand_profile_id,field_path").execute()

        if patch:
            patch["updated_at"] = _agora()
            self.db.table("brand_profiles").update(patch).eq("id", pid).execute()
        return aplicados

    def _completar_cadastro(self, company_id: str, s: Optional[SinaisWeb]) -> list[str]:
        """Preenche `companies` com o que o site revelou — **só o que está vazio**.

        A regra de só-preencher-vazio não é cautela: o cadastro é o que o
        corretor conferiu e assinou. Um telefone extraído de rodapé de site
        sobrescrevendo o telefone que ele digitou seria trocar dado verificado
        por dado inferido, e ninguém perceberia até um cliente ligar no número
        errado.
        """
        if not s:
            return []

        atual = (self.db.table("companies").select(
            "company_name, legal_name, cnpj, primary_contact_phone, "
            "primary_contact_email, cep, street, number, neighborhood, city, state"
        ).eq("id", company_id).maybe_single().execute()).data or {}

        end = s.endereco or {}
        candidatos = {
            "company_name": s.nome or _nome_do_titulo(s.titulo),
            "legal_name": s.legal_name,
            "cnpj": s.cnpj,
            "primary_contact_phone": (s.telefones or [None])[0],
            "primary_contact_email": (s.emails or [None])[0],
            "cep": end.get("cep"),
            "street": end.get("logradouro"),
            "neighborhood": end.get("bairro"),
            "city": end.get("cidade"),
            "state": end.get("uf"),
        }

        patch = {k: v for k, v in candidatos.items()
                 if v and not (atual.get(k) or "").strip()}
        if not patch:
            return []

        try:
            self.db.table("companies").update(patch).eq("id", company_id).execute()
            logger.info("[brand] cadastro complementado: %s", sorted(patch))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] cadastro nao complementado: %s", type(exc).__name__)
            return []
        return sorted(patch.keys())

    def _completude(self, company_id: str, pid: str) -> float:
        """Quanto da identidade está de pé. Vira barra de progresso e gate.

        Peso por impacto na peça entregue: sem logo e sem cor, toda saída fica
        genérica — então esses dois valem mais que o resto somado.
        """
        p = (self.db.table("brand_profiles").select("*").eq("id", pid)
             .maybe_single().execute()).data or {}
        pesos = {
            "logo_asset_id": 0.26,
            "palette": 0.24,
            "display_name": 0.10,
            "about_md": 0.09,
            "services": 0.09,
            "contact": 0.08,
            "tagline": 0.06,
            "typography": 0.05,
            "website_url": 0.03,
        }
        total = 0.0
        for campo, peso in pesos.items():
            v = p.get(campo)
            if campo == "palette":
                if isinstance(v, dict) and v.get("primary"):
                    total += peso
            elif isinstance(v, (list, dict)):
                if v:
                    total += peso
            elif v:
                total += peso
        return round(min(total, 1.0), 2)

    def _versionar(self, company_id: str, pid: str, motivo: str,
                   campos: list[str]) -> None:
        atual = (self.db.table("brand_profiles").select("*").eq("id", pid)
                 .maybe_single().execute()).data or {}
        r = (self.db.table("brand_profile_versions").select("version")
             .eq("brand_profile_id", pid).order("version", desc=True)
             .limit(1).execute())
        proxima = ((r.data or [{}])[0].get("version") or 0) + 1
        try:
            self.db.table("brand_profile_versions").insert({
                "company_id": company_id, "brand_profile_id": pid,
                "version": proxima, "snapshot": atual, "reason": motivo,
                "changed_fields": campos,
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[brand] versao nao gravada: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Edição humana
    # ------------------------------------------------------------------

    def editar(self, company_id: str, campos: dict[str, Any],
               user_id: Optional[str] = None) -> dict:
        """Grava edição do corretor e marca os campos como protegidos."""
        perfil = self.obter_ou_criar(company_id)
        pid = perfil["id"]

        patch = {k: v for k, v in campos.items() if k not in ("id", "company_id")}
        if "palette" in patch and isinstance(patch["palette"], dict):
            # Cor escolhida à mão também precisa de sistema completo e de
            # contraste conferido — senão a edição manual vira o caminho fácil
            # para gerar peça ilegível.
            sistema = build_design_system(
                patch["palette"].get("primary"), patch["palette"].get("accent"),
                typography=patch.get("typography") or perfil.get("typography"))
            patch["palette"] = {
                "primary": sistema["primary"], "accent": sistema["accent"],
                "scales": sistema["scales"], "themes": sistema["themes"],
                "audit": sistema["audit"], "origin": "human",
            }

        patch["updated_at"] = _agora()
        patch["updated_by"] = user_id
        if perfil.get("capture_status") == "empty":
            patch["capture_status"] = "manual"
        self.db.table("brand_profiles").update(patch).eq("id", pid).execute()

        agora = _agora()
        for campo in patch:
            if campo in ("updated_at", "updated_by", "capture_status"):
                continue
            self.db.table("brand_field_provenance").upsert({
                "company_id": company_id, "brand_profile_id": pid,
                "field_path": campo, "source_kind": "human",
                "source_detail": "editado no painel da corretora",
                "confidence": 1.0, "human_edited": True,
                "human_edited_at": agora, "human_edited_by": user_id,
                "captured_at": agora,
            }, on_conflict="brand_profile_id,field_path").execute()

        completude = self._completude(company_id, pid)
        self.db.table("brand_profiles").update(
            {"completeness": completude}).eq("id", pid).execute()
        self._versionar(company_id, pid, "human_edit", sorted(patch.keys()))

        return (self.db.table("brand_profiles").select("*").eq("id", pid)
                .maybe_single().execute()).data or {}

    # ------------------------------------------------------------------
    # Leitura para uso nas peças
    # ------------------------------------------------------------------

    def snapshot_para_artefato(self, company_id: str) -> dict:
        """A marca no formato que o renderizador congela dentro da versão.

        Sempre devolve algo utilizável: sem perfil, a peça sai com a identidade
        padrão em vez de sair quebrada. O que ela nunca faz é sair sem marca
        nenhuma — o `CHECK` do banco recusaria publicar.
        """
        p = (self.db.table("brand_profiles").select("*")
             .eq("company_id", company_id).maybe_single().execute()).data
        if not p or not (p.get("palette") or {}).get("primary"):
            sistema = build_design_system(FALLBACK_PRIMARIA, FALLBACK_ACENTO)
            nome = (p or {}).get("display_name") or "Corretora"
            return {"name": nome, "palette": sistema, "logo": None,
                    "visual_style": "aurora", "is_fallback": True}

        logo = None
        if p.get("logo_asset_id"):
            a = (self.db.table("brand_assets")
                 .select("storage_ref, width, height, has_transparency, mime_type")
                 .eq("id", p["logo_asset_id"]).maybe_single().execute()).data
            if a:
                logo = a

        return {
            "name": p.get("display_name") or "Corretora",
            "legal_name": p.get("legal_name"),
            "tagline": p.get("tagline"),
            "palette": p.get("palette") or {},
            "typography": p.get("typography") or {},
            "logo": logo,
            "contact": p.get("contact") or {},
            "visual_style": p.get("visual_style") or "aurora",
            "susep_code": p.get("susep_code"),
            "captured_at": p.get("captured_at"),
            "is_fallback": False,
        }


# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------

def _nome_do_titulo(titulo: Optional[str]) -> Optional[str]:
    """`<title>` de site costuma ser 'Frase de SEO | Nome'. O nome fica no fim."""
    if not titulo:
        return None
    partes = [p.strip() for p in re.split(r"[|\-–—·]", titulo) if p.strip()]
    if not partes:
        return None
    return min(partes[-1:] + partes[:1], key=len)[:120]


