"""Ciclo de vida do artefato. SPEC-057 §Bloco B.

criar → versão rascunho → renderizar → publicar → compartilhar

Duas regras que o banco já cobra e que aqui só são obedecidas:

* **versão publicada é imutável.** Corrigir um número significa gerar a versão
  seguinte, não reescrever a anterior. É o que permite ao corretor dizer "foi
  isto que eu te mandei em julho" e provar.
* **a marca é congelada no ato da publicação.** Se a corretora mudar de
  identidade, as peças antigas continuam como eram.

E uma que só existe aqui: **compartilhar tem prazo**. O padrão é 30 dias.
Link público sem validade criado sem pensar é vazamento de dado de segurado
com prazo infinito.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALIDADE_PADRAO_DIAS = 30
VALIDADE_MAXIMA_DIAS = 180

#: 🔴 SPEC-095 · B.3. A variável que faz o canário de SPEC se declarar. Mora
#: AQUI, ao lado do único publicador, porque quem publica é quem marca — e
#: porque os dois caminhos que publicam (a tool do chat e a rotina do briefing)
#: já importam este módulo. Duas cópias da regra seriam dois canários.
#:
#: 📊 §1.1, medido em 04/09/2026: `tags` preenchida em **0/136** peças e
#: `requested_by` em **0/136**, enquanto 100% dos relatórios `origin='chat'` da
#: Resulta são execução de SPEC. Sem a marca, separar teste de trabalho real
#: dependia de cruzar o `created_at` com o `git log`.
VARIAVEL_DO_CANARIO = "AUTOBROKERS_CANARIO"
#: `"0"`, `"false"`, `"no"` e vazio são DESLIGADO; qualquer outra coisa liga.
#: ⚠️ Um `AUTOBROKERS_CANARIO=0` que LIGASSE o canário seria pior que a
#: variável não existir: marcaria como teste o relatório que o dono pediu.
_CANARIO_DESLIGADO = {"", "0", "false", "no", "off", "nao", "não"}

#: A tag que a peça de canário carrega. O script de limpeza (B.4) NUNCA toca
#: numa peça que a tenha: o canário arquiva o que ele mesmo criou.
TAG_DO_CANARIO = "canario"


def e_canario() -> bool:
    """A execução atual é canário de SPEC? Lê a variável — não a escreve."""
    valor = str(os.getenv(VARIAVEL_DO_CANARIO) or "").strip().lower()
    return valor not in _CANARIO_DESLIGADO


def tags_do_canario() -> Optional[list[str]]:
    """`["canario"]` quando a variável está ligada; `None` quando não."""
    return [TAG_DO_CANARIO] if e_canario() else None


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        # Um upsert por template por processo. Sem isto, toda criação de
        # artefato faria uma escrita a mais numa tabela que quase nunca muda.
        self._templates_conferidos: set = set()

    # ------------------------------------------------------------------

    def _evento(self, company_id: str, artifact_id: str, tipo: str, *,
                actor_kind: str = "system", actor_id: Optional[str] = None,
                detalhe: Optional[dict] = None) -> None:
        try:
            self.db.table("artifact_events").insert({
                "company_id": company_id, "artifact_id": artifact_id,
                "event_type": tipo, "actor_kind": actor_kind, "actor_id": actor_id,
                "detail": detalhe or {},
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[artifact] evento nao gravado: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def criar(self, *, company_id: str, title: str, template_key: str,
              payload: dict, composition: list[dict],
              subtitle: Optional[str] = None, summary: Optional[str] = None,
              kind: str = "report", origin: str = "chat",
              work_run_id: Optional[str] = None, requested_by: Optional[str] = None,
              data_sources: Optional[list[dict]] = None,
              subject_ref: Optional[dict] = None,
              tags: Optional[list[str]] = None,
              data_as_of: Optional[datetime] = None,
              confidence_note: Optional[str] = None,
              evento_extra: Optional[dict] = None) -> dict:
        """Cria o artefato e a versão 1 em rascunho, com a marca já congelada.

        SPEC-095 · B.2/B.3 acrescentaram quatro parâmetros, todos opcionais:

        ```
        tags             ["canario"] quando a peça nasce de um teste do produto
        data_as_of       a data do DADO — não a da escrita. Sem ela, NULL
        confidence_note  o que esta versão não conseguiu medir
        evento_extra     o que mais o `artifact.created` deve registrar
        ```
        """
        from ..brand.capture import BrandCaptureService

        self._garantir_template(template_key)
        marca = BrandCaptureService(self.db).snapshot_para_artefato(company_id)

        art = (self.db.table("artifacts").insert({
            "company_id": company_id, "kind": kind, "title": title,
            "subtitle": subtitle, "summary": summary, "template_key": template_key,
            "work_run_id": work_run_id, "requested_by": requested_by,
            "origin": origin, "status": "generating", "current_version": 0,
            "subject_ref": subject_ref or {},
            # 🔴 `tags` é a marca do CANÁRIO. 📊 SPEC-095 §1.1: 100% dos
            # relatórios `origin='chat'` da Resulta são execução de SPEC, e
            # `tags` estava preenchida em 0/136 peças — não havia como a lista
            # da corretora separar o que é dela do que é teste nosso.
            "tags": list(tags or []),
        }).execute()).data
        if not art:
            raise RuntimeError("artefato nao criado")
        artefato = art[0]

        versao = self._nova_versao(
            company_id, artefato["id"], 1, payload, composition, marca,
            data_sources or [], requested_by,
            data_as_of=data_as_of, confidence_note=confidence_note)

        detalhe = {"template": template_key,
                   "marca_padrao": marca.get("is_fallback")}
        if tags:
            detalhe["tags"] = list(tags)
        if evento_extra:
            detalhe.update(evento_extra)
        self._evento(company_id, artefato["id"], "artifact.created",
                     actor_kind="agent" if origin != "manual" else "user",
                     actor_id=requested_by, detalhe=detalhe)

        return {"artifact": artefato, "version": versao, "brand": marca}

    def _garantir_template(self, template_key: str) -> None:
        """Põe no banco o template que o catálogo declara, se ele ainda não estiver lá.

        Por que isto existe
        -------------------
        `artifacts.template_key` é chave estrangeira para `report_templates`. O
        catálogo de verdade, porém, vive em Python (`templates.py`), e a
        migration original não semeou nenhuma linha.

        O resultado, medido em 30/07/2026: dos 19 templates do catálogo, 8
        estavam no banco e 11 não. Entre os 11 ausentes estavam
        `briefing.daily_operational` e `briefing.weekly_executive` — justamente
        os dois que o briefing diário usa. Toda criação de artefato morria em
        violação de chave estrangeira, calada, e o banco mostrava
        `artifacts = 0` com dezessete briefings parados em `pending`: não havia
        o que entregar.

        Semear uma vez conserta o passado e não impede o retorno: o próximo
        template escrito em Python volta a faltar no banco. Como a fonte é o
        catálogo, é ele que deve mandar — e a hora de sincronizar é a hora do
        uso, que é a única em que se sabe que o template é necessário.
        """
        if template_key in self._templates_conferidos:
            return
        try:
            from .templates import POR_CHAVE

            t = POR_CHAVE.get(template_key)
            if t is not None:
                self.db.table("report_templates").upsert({
                    "template_key": t.key, "name": t.name,
                    "description": t.description, "category": t.category,
                    "narrative_shape": t.narrative_shape,
                    "audience": getattr(t, "audience", "internal"),
                }, on_conflict="template_key", ignore_duplicates=True).execute()
        except Exception as exc:  # noqa: BLE001
            # Não derruba a criação: se o template já existir, o insert seguinte
            # funciona; se não existir, a FK dará o erro claro logo abaixo.
            logger.warning("[ARTIFACTS] não consegui garantir o template %s: %s",
                           template_key, type(exc).__name__)
        self._templates_conferidos.add(template_key)

    def nova_versao(self, *, company_id: str, artifact_id: str, payload: dict,
                    composition: list[dict], data_sources: Optional[list[dict]] = None,
                    created_by: Optional[str] = None,
                    title: Optional[str] = None, subtitle: Optional[str] = None,
                    summary: Optional[str] = None,
                    data_as_of: Optional[datetime] = None,
                    confidence_note: Optional[str] = None) -> dict:
        """Nova versão de um artefato existente. A marca é recongelada agora.

        🔴 SPEC-095 · B.1: a versão nova pode **retitular a peça**. A mesma
        pergunta feita em outubro e em dezembro é a mesma PEÇA — mas o achado
        mudou, e o título da peça é o achado. Sem isto, a v5 de "Pulso 360 ·
        2026" continuaria anunciando na lista o achado da v1.

        O renome vira o evento `artifact.retitled` com `{de, para, versao}`:
        sem o título anterior gravado em algum lugar, o renome seria
        irreversível — e a lista da corretora deixaria de ter como responder
        "o que este card dizia antes?".
        """
        from ..brand.capture import BrandCaptureService

        atual = (self.db.table("artifacts").select("current_version, title")
                 .eq("id", artifact_id).eq("company_id", company_id)
                 .maybe_single().execute()).data or {}
        proxima = int(atual.get("current_version") or 0) + 1
        # 🔴 O título ANTERIOR é copiado AGORA, antes de qualquer escrita.
        # 📊 Achado pelo `--simular` do canário em 04/09/2026: lê-lo depois do
        # `update` fazia o evento `artifact.retitled` não sair — `de` e `para`
        # ficavam iguais. O dublê devolve a própria linha; um cliente real
        # devolve uma cópia decodificada, e a diferença entre os dois é
        # exatamente o tipo de coisa que só aparece em produção, meses depois,
        # como "o renome não deixou rastro".
        titulo_anterior = str(atual.get("title") or "")
        marca = BrandCaptureService(self.db).snapshot_para_artefato(company_id)
        versao = self._nova_versao(company_id, artifact_id, proxima, payload,
                                   composition, marca, data_sources or [],
                                   created_by, data_as_of=data_as_of,
                                   confidence_note=confidence_note)

        mudancas = {k: v for k, v in (("title", title), ("subtitle", subtitle),
                                      ("summary", summary)) if v is not None}
        if mudancas:
            self.db.table("artifacts").update(mudancas) \
                .eq("id", artifact_id).eq("company_id", company_id).execute()
            para = str(mudancas.get("title") or titulo_anterior)
            if para != titulo_anterior:
                self._evento(company_id, artifact_id, "artifact.retitled",
                             detalhe={"de": titulo_anterior, "para": para,
                                      "versao": proxima})
        return versao

    def _nova_versao(self, company_id: str, artifact_id: str, numero: int,
                     payload: dict, composition: list[dict], marca: dict,
                     fontes: list[dict], created_by: Optional[str], *,
                     data_as_of: Optional[datetime] = None,
                     confidence_note: Optional[str] = None) -> dict:
        """A linha da versão. 🔴 `data_as_of` só existe quando alguém a SABE.

        📊 SPEC-095 §1.9, medido em 04/09/2026: esta linha gravava
        `_agora().isoformat()` — o carimbo da ESCRITA — em 136/136 versões, e
        **30 delas ficaram no futuro do próprio `created_at`** (desvio de
        relógio por processo: o worker do tick grava a −0,1 s e o contêiner da
        API a +50…+70 s; nos 5 Pulsos, +69,9 s). A tela imprimia
        *"Dados de 4 de setembro de 2026, 02:55"* em cima disso
        (`[artifactId]/page.tsx:217`): uma afirmação de frescor que o sistema
        não tinha como sustentar, chegando à corretora.

        ⛔ Sem data passada, a coluna fica **NULL** — e a tela deixa de afirmar.
        NULL é "não sei"; um carimbo é uma afirmação. CLAUDE.md §12.1: quando o
        nome do campo mente sobre o que ele guarda, conserta-se o CAMPO.
        """
        # 🔴 A chave vai SEMPRE, e o valor é `None` quando ninguém sabe a data.
        # ⚠️ Omitir a chave pareceria equivalente e não é: sem ela, quem decide
        # o valor da coluna passa a ser o DEFAULT do banco — e um `default
        # now()` que alguém acrescentasse numa migration futura reintroduziria
        # este defeito inteiro, calado, sem tocar numa linha de Python. Escrever
        # `None` é o que faz a decisão morar AQUI.
        linha = {
            "company_id": company_id, "artifact_id": artifact_id, "version": numero,
            "payload": payload, "composition": composition,
            "brand_snapshot": marca, "data_sources": fontes,
            "data_as_of": None, "confidence_note": None,
            "status": "draft", "created_by": created_by,
        }
        if data_as_of is not None:
            linha["data_as_of"] = (data_as_of.isoformat()
                                   if hasattr(data_as_of, "isoformat")
                                   else str(data_as_of))
        if confidence_note:
            linha["confidence_note"] = confidence_note
        dados = (self.db.table("artifact_versions").insert(linha).execute()).data
        if not dados:
            raise RuntimeError("versao nao criada")
        return dados[0]

    # ------------------------------------------------------------------
    # Arquivar — reversível, com o motivo escrito
    # ------------------------------------------------------------------

    def arquivar(self, company_id: str, artifact_id: str,
                 motivo: str, *, user_id: Optional[str] = None) -> bool:
        """Tira a peça da biblioteca sem apagar nada. SPEC-095 · B.3.

        🔴 `archived_at`, e nunca DELETE. 📊 §1.1: 35 peças da biblioteca da
        Resulta e da AutoFleet são canários de execução de SPEC (081/094/094.1)
        — elas não são lixo, são registro de que o produto rodou. Apagá-las
        perderia o registro; escondê-las devolve a biblioteca ao dono.

        ⚠️ O `status` é mantido de propósito: a peça continua publicada e o
        link já entregue pelo chat continua abrindo (o BLOCO E do frontend
        passa a mostrar o banner "Arquivado em"). Arquivar é sobre a LISTA,
        não sobre o conteúdo.
        """
        r = (self.db.table("artifacts")
             .update({"archived_at": _agora().isoformat()})
             .eq("id", artifact_id).eq("company_id", company_id)
             .is_("archived_at", "null").execute()).data
        if not r:
            return False
        self._evento(company_id, artifact_id, "artifact.archived",
                     actor_kind="user" if user_id else "system", actor_id=user_id,
                     detalhe={"motivo": motivo})
        return True

    def desarquivar(self, company_id: str, artifact_id: str, *,
                    user_id: Optional[str] = None) -> bool:
        """Devolve a peça à biblioteca. O ROLLBACK do `arquivar`, por gesto."""
        r = (self.db.table("artifacts").update({"archived_at": None})
             .eq("id", artifact_id).eq("company_id", company_id).execute()).data
        if not r:
            return False
        self._evento(company_id, artifact_id, "artifact.unarchived",
                     actor_kind="user" if user_id else "system", actor_id=user_id)
        return True

    # ------------------------------------------------------------------
    # Renderização e publicação
    # ------------------------------------------------------------------

    def renderizar(self, *, company_id: str, version_id: str,
                   visual_style: Optional[str] = None) -> dict:
        """Gera o HTML e guarda como render. Não publica."""
        from .render import render_html
        from .templates import POR_CHAVE

        v = (self.db.table("artifact_versions").select("*")
             .eq("id", version_id).eq("company_id", company_id)
             .maybe_single().execute()).data
        if not v:
            raise ValueError("versao inexistente")

        art = (self.db.table("artifacts").select("title, template_key")
               .eq("id", v["artifact_id"]).maybe_single().execute()).data or {}

        marca = v.get("brand_snapshot") or {}
        tpl = POR_CHAVE.get(art.get("template_key") or "")
        estilo = (visual_style or marca.get("visual_style")
                  or (tpl.visual_style if tpl else "aurora"))

        inicio = _agora()
        html, diag = render_html(
            brand=marca,
            composition=v.get("composition") or (tpl.composition if tpl else []),
            visual_style=estilo,
            title=f"{art.get('title', 'Relatório')} · {marca.get('name', '')}".strip(" ·"),
            data_sources=v.get("data_sources") or [],
        )
        ms = int((_agora() - inicio).total_seconds() * 1000)

        # Conteúdo inline: o HTML de uma peça fica na casa dos 50 KB. Ida ao
        # storage aqui acrescentaria uma dependência de rede no caminho de
        # leitura sem economizar nada que importe.
        self.db.table("artifact_renders").upsert({
            "company_id": company_id, "artifact_version_id": version_id,
            "format": "html", "inline_content": html, "byte_size": len(html.encode()),
            "checksum": hashlib.sha256(html.encode()).hexdigest()[:32],
            "status": "ready", "duration_ms": ms,
        }, on_conflict="artifact_version_id,format").execute()

        if diag.get("falhas") or diag.get("desconhecidos"):
            # Peça incompleta em silêncio é o pior resultado: parece pronta.
            logger.warning("[artifact] render com pendencias: %s", diag)

        return {"html": html, "diagnostico": diag, "duracao_ms": ms}

    def publicar(self, *, company_id: str, version_id: str,
                 user_id: Optional[str] = None) -> dict:
        """Publica a versão. A partir daqui ela é imutável — o banco garante."""
        v = (self.db.table("artifact_versions").select("id, artifact_id, version, status, brand_snapshot")
             .eq("id", version_id).eq("company_id", company_id)
             .maybe_single().execute()).data
        if not v:
            raise ValueError("versao inexistente")

        # SPEC-096 B.3 — a peça publicada DENTRO de um turno de chat avisa o
        # turno. 🔴 Antes do `return` da republicação: republicar é publicar de
        # novo, e o corretor tem de ver o link do mesmo jeito. Fora de um turno
        # (rotina, tick, API) o ContextVar está vazio e isto não faz nada.
        from app.api.chat_eventos import registrar_peca
        registrar_peca(v["artifact_id"])

        if v["status"] == "published":
            return v

        marca = v.get("brand_snapshot") or {}
        if not marca.get("palette") or not marca.get("name"):
            # O CHECK do banco recusaria de qualquer forma; recusar aqui devolve
            # uma mensagem que alguém entende.
            raise ValueError(
                "esta versão não tem marca congelada — monte a identidade da "
                "corretora antes de publicar")

        # Versões anteriores viram 'superseded': só uma é a atual.
        self.db.table("artifact_versions").update({"status": "superseded"}) \
            .eq("artifact_id", v["artifact_id"]).eq("status", "published").execute()

        agora = _agora().isoformat()
        self.db.table("artifact_versions").update({
            "status": "published", "published_at": agora,
        }).eq("id", version_id).execute()

        self.db.table("artifacts").update({
            "status": "ready", "current_version": v["version"], "updated_at": agora,
        }).eq("id", v["artifact_id"]).execute()

        self._evento(company_id, v["artifact_id"], "version.published",
                     actor_kind="user" if user_id else "system", actor_id=user_id,
                     detalhe={"version": v["version"]})
        return {"id": version_id, "version": v["version"], "status": "published"}

    # ------------------------------------------------------------------
    # Compartilhamento
    # ------------------------------------------------------------------

    def compartilhar(self, *, company_id: str, artifact_id: str,
                     version_id: Optional[str] = None, dias: int = VALIDADE_PADRAO_DIAS,
                     audiencia: Optional[str] = None, max_views: Optional[int] = None,
                     white_label: bool = True,
                     user_id: Optional[str] = None) -> dict:
        """Cria o link público. Prazo obrigatório, teto de 180 dias."""
        if not version_id:
            v = (self.db.table("artifact_versions").select("id")
                 .eq("artifact_id", artifact_id).eq("company_id", company_id)
                 .eq("status", "published").order("version", desc=True)
                 .limit(1).execute()).data
            if not v:
                raise ValueError("não há versão publicada para compartilhar")
            version_id = v[0]["id"]

        dias = max(1, min(int(dias or VALIDADE_PADRAO_DIAS), VALIDADE_MAXIMA_DIAS))
        # 43 caracteres de base64url ≈ 256 bits. O CHECK do banco exige 32;
        # aqui se dá folga porque o custo é zero e o link é público.
        token = secrets.token_urlsafe(32)

        linha = (self.db.table("artifact_shares").insert({
            "company_id": company_id, "artifact_id": artifact_id,
            "artifact_version_id": version_id, "token": token,
            "audience_label": audiencia,
            "expires_at": (_agora() + timedelta(days=dias)).isoformat(),
            "max_views": max_views, "white_label": white_label,
            "created_by": user_id,
        }).execute()).data
        if not linha:
            raise RuntimeError("compartilhamento nao criado")

        self._evento(company_id, artifact_id, "share.created",
                     actor_kind="user" if user_id else "system", actor_id=user_id,
                     detalhe={"dias": dias, "audiencia": audiencia})
        return linha[0]

    def revogar(self, *, company_id: str, share_id: str,
                user_id: Optional[str] = None) -> bool:
        r = (self.db.table("artifact_shares").update({
            "revoked_at": _agora().isoformat(), "revoked_by": user_id,
        }).eq("id", share_id).eq("company_id", company_id).execute()).data
        return bool(r)

    def abrir_compartilhado(self, token: str) -> Optional[dict]:
        """Resolve um token público. Fecha em qualquer sinal de invalidez.

        Não recebe `company_id` de propósito: quem abre não tem sessão. Por isso
        o token é a única credencial, e cada motivo de recusa devolve o mesmo
        resultado vazio — distinguir "expirado" de "inexistente" ajudaria quem
        estivesse tentando adivinhar tokens.
        """
        s = (self.db.table("artifact_shares")
             .select("id, company_id, artifact_id, artifact_version_id, expires_at, "
                     "revoked_at, max_views, view_count, white_label, audience_label")
             .eq("token", token).maybe_single().execute()).data
        if not s or s.get("revoked_at"):
            return None
        try:
            if datetime.fromisoformat(str(s["expires_at"]).replace("Z", "+00:00")) <= _agora():
                return None
        except Exception:  # noqa: BLE001
            return None
        if s.get("max_views") and int(s["view_count"] or 0) >= int(s["max_views"]):
            return None

        render = (self.db.table("artifact_renders")
                  .select("inline_content, storage_ref")
                  .eq("artifact_version_id", s["artifact_version_id"])
                  .eq("format", "html").eq("status", "ready")
                  .maybe_single().execute()).data
        if not render or not render.get("inline_content"):
            return None

        art = (self.db.table("artifacts").select("title, subtitle, kind")
               .eq("id", s["artifact_id"]).maybe_single().execute()).data or {}

        try:
            self.db.table("artifact_shares").update({
                "view_count": int(s["view_count"] or 0) + 1,
                "last_viewed_at": _agora().isoformat(),
            }).eq("id", s["id"]).execute()
            self._evento(s["company_id"], s["artifact_id"], "share.viewed",
                         actor_kind="public",
                         detalhe={"audiencia": s.get("audience_label")})
        except Exception:  # noqa: BLE001
            pass  # contar visualização nunca pode impedir a leitura

        return {
            "html": render["inline_content"],
            "title": art.get("title") or "Relatório",
            "subtitle": art.get("subtitle"),
            "white_label": bool(s.get("white_label", True)),
        }

    # ------------------------------------------------------------------
    # Catálogo
    # ------------------------------------------------------------------

    def listar(self, company_id: str, *, limite: int = 40) -> list[dict]:
        r = (self.db.table("artifacts")
             .select("id, kind, title, subtitle, summary, template_key, status, "
                     "current_version, origin, tags, created_at, updated_at")
             .eq("company_id", company_id).is_("archived_at", "null")
             .order("created_at", desc=True).limit(limite).execute())
        return r.data or []
