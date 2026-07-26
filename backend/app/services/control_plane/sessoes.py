"""Sessões administrativas e step-up. SPEC-061 §7.3 e §7.4.

Duas perguntas que o Admin não sabia responder
----------------------------------------------
1. **"Quem está dentro agora?"** — não havia lista de sessões ativas nem jeito
   de encerrar a de alguém. Notebook perdido, pessoa que saiu da empresa,
   sessão esquecida num computador emprestado: nada disso tinha resposta.

2. **"Você é você mesmo, agora?"** — suspender uma corretora e ler o histórico
   de conversas exigiam o mesmo que abrir a tela de resumo: estar logado. Uma
   sessão aberta há oito horas num computador destravado podia fazer as duas.

Step-up não é login de novo
---------------------------
É confirmar que a pessoa **ainda está lá** antes de uma ação que não se
desfaz. A janela é curta de propósito (`JANELA_DE_STEP_UP_MINUTOS`): longa
demais e vira teatro; curta demais e o operador desiste do trabalho.

O que este módulo **não** faz: um provider de autenticação novo. §7.4 é
explícita — *"o mecanismo deve usar a fundação de autenticação existente"*. A
confirmação reusa a senha do `admin_users`, que é a mesma do login.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Quanto tempo uma confirmação de identidade vale. Quinze minutos cobre uma
# sequência de ações relacionadas — suspender uma corretora e registrar o
# motivo — sem cobrir o cafézinho seguinte.
JANELA_DE_STEP_UP_MINUTOS = 15


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class SessoesAdministrativas:
    """§7.3 — ver e revogar quem está dentro.

    A sessão em si vive no cookie assinado (iron-session), que é stateless: não
    dá para "apagar" um cookie que está no navegador de outra pessoa. O que se
    pode fazer é **invalidar** — e é isso que a tabela guarda.

    Por isso a revogação é registrada como um FATO com hora: qualquer sessão
    emitida antes daquele instante deixa de valer. É o mesmo princípio de
    "trocar a fechadura" — não se recolhe a chave de ninguém, muda-se o que a
    fechadura aceita.
    """

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def registrar_entrada(self, *, user_id: str, ip: Optional[str] = None,
                          agente: Optional[str] = None) -> dict:
        """Marca que alguém entrou. Chamado no login."""
        linha = {
            "admin_user_id": str(user_id),
            "source_type": "sessao",
            "source_id": f"login:{_agora().isoformat()}",
            "state": "read",
            "note_redacted": _resumir_dispositivo(agente, ip),
        }
        try:
            self.db.table("admin_inbox_states").upsert(
                linha, on_conflict="admin_user_id,source_type,source_id").execute()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Sessões] entrada não registrada: %s", type(exc).__name__)
            return {"ok": False}

    def listar(self, *, limite: int = 50) -> list[dict]:
        """Quem entrou, quando e de onde — sem IP inteiro.

        O IP completo identifica uma pessoa física em casa. Para reconhecer
        "esta não sou eu", os dois primeiros octetos bastam: dizem a cidade e o
        provedor, e é isso que faz alguém desconfiar.
        """
        try:
            linhas = (self.db.table("admin_inbox_states")
                      .select("admin_user_id, source_id, note_redacted, updated_at")
                      .eq("source_type", "sessao")
                      .order("updated_at", desc=True)
                      .limit(limite).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Sessões] leitura falhou: %s", type(exc).__name__)
            return []

        corte = self._revogacoes()
        saida = []
        for l in linhas:
            quando = str(l.get("updated_at") or "")
            user = str(l.get("admin_user_id") or "")
            saida.append({
                "user_id": user,
                "dispositivo": l.get("note_redacted") or "não informado",
                "ultima_atividade": quando,
                "valida": quando > corte.get(user, ""),
            })
        return saida

    def revogar_tudo(self, *, user_id: str, motivo: str,
                     revogado_por: str) -> dict:
        """Invalida toda sessão emitida antes de agora, para uma pessoa."""
        if len((motivo or "").strip()) < 10:
            return {"ok": False,
                    "erro": ("diga por que está encerrando as sessões — quem "
                             "ler isto depois precisa entender")}
        try:
            self.db.table("admin_inbox_states").upsert({
                "admin_user_id": str(user_id),
                "source_type": "sessao_revogada",
                "source_id": "corte",
                "state": "acknowledged",
                "snoozed_until": _agora().isoformat(),
                "note_redacted": f"por {revogado_por}: {motivo[:400]}",
                "updated_at": _agora().isoformat(),
            }, on_conflict="admin_user_id,source_type,source_id").execute()
            return {"ok": True,
                    "mensagem": ("Sessões encerradas. A pessoa precisa entrar "
                                 "de novo no próximo acesso.")}
        except Exception as exc:  # noqa: BLE001
            logger.error("[Sessões] revogação falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui encerrar as sessões"}

    def sessao_ainda_vale(self, *, user_id: str, emitida_em: str) -> bool:
        """A sessão foi emitida DEPOIS do último corte?

        Esta é a pergunta que o BFF faz a cada requisição administrativa. Sem
        ela, "revoguei o acesso" seria uma frase na tela e nada no mundo.
        """
        corte = self._revogacoes().get(str(user_id))
        if not corte:
            return True
        return str(emitida_em) > corte

    def _revogacoes(self) -> dict[str, str]:
        try:
            linhas = (self.db.table("admin_inbox_states")
                      .select("admin_user_id, snoozed_until")
                      .eq("source_type", "sessao_revogada")
                      .limit(500).execute()).data or []
            return {str(l["admin_user_id"]): str(l.get("snoozed_until") or "")
                    for l in linhas}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Sessões] cortes: %s", type(exc).__name__)
            # Falha aqui NÃO invalida ninguém: uma leitura que falhou não é
            # prova de revogação, e derrubar todo mundo por um erro de banco
            # seria trocar um risco por outro maior.
            return {}


# ---------------------------------------------------------------------------
# Step-up — §7.4
# ---------------------------------------------------------------------------


class ConfirmacaoDeIdentidade:
    """"Você ainda está aí?" antes de uma ação que não se desfaz.

    O registro fica em `admin_inbox_states` com `source_type='step_up'`. Não é
    tabela nova de propósito: seria uma tabela com uma linha por pessoa e um
    campo de data, e a §9 pede o modelo **mínimo**.
    """

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def confirmar(self, *, user_id: str, senha: str) -> dict:
        """Valida a senha atual e abre a janela.

        Reusa o hash de `admin_users` — a MESMA senha do login. §7.4: "sem
        criar provider paralelo". Um segundo fator próprio aqui seria uma
        segunda fonte de verdade sobre quem a pessoa é.
        """
        if not senha:
            return {"ok": False, "erro": "informe sua senha"}

        try:
            r = (self.db.table("admin_users").select("id, password_hash")
                 .eq("id", str(user_id)).limit(1).execute())
            linha = (r.data or [None])[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("[StepUp] leitura falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui confirmar agora"}

        if not linha or not linha.get("password_hash"):
            return {"ok": False, "erro": "não consegui confirmar agora"}

        if not _senha_confere(senha, str(linha["password_hash"])):
            # Mensagem única para senha errada e usuário inexistente: dizer
            # "usuário não encontrado" conta a quem sonda que a conta não
            # existe, o que é informação.
            return {"ok": False, "erro": "senha incorreta"}

        try:
            self.db.table("admin_inbox_states").upsert({
                "admin_user_id": str(user_id),
                "source_type": "step_up",
                "source_id": "confirmacao",
                "state": "acknowledged",
                "snoozed_until": (
                    _agora() + timedelta(minutes=JANELA_DE_STEP_UP_MINUTOS)
                ).isoformat(),
                "updated_at": _agora().isoformat(),
            }, on_conflict="admin_user_id,source_type,source_id").execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[StepUp] registro falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui registrar a confirmação"}

        return {"ok": True, "vale_por_minutos": JANELA_DE_STEP_UP_MINUTOS,
                "mensagem": (f"Identidade confirmada. Vale pelos próximos "
                             f"{JANELA_DE_STEP_UP_MINUTOS} minutos.")}

    def confirmado_recentemente(self, *, user_id: str) -> bool:
        try:
            r = (self.db.table("admin_inbox_states")
                 .select("snoozed_until")
                 .eq("admin_user_id", str(user_id))
                 .eq("source_type", "step_up").limit(1).execute())
            linha = (r.data or [None])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[StepUp] leitura: %s", type(exc).__name__)
            # Fail-closed: sem conseguir provar a confirmação, ela não vale.
            # Aqui o custo do erro é pedir a senha de novo — barato.
            return False

        if not linha or not linha.get("snoozed_until"):
            return False
        try:
            return datetime.fromisoformat(
                str(linha["snoozed_until"]).replace("Z", "+00:00")) > _agora()
        except Exception:  # noqa: BLE001
            return False


def _senha_confere(senha: str, hash_guardado: str) -> bool:
    """O MESMO esquema do login, inclusive o legado.

    `lib/auth.ts` (`verifyPasswordWithMigration`) aceita duas coisas: bcrypt
    (`$2a$`/`$2b$`, 60 caracteres) e SHA-256 puro (64 hex), que é o formato
    antigo ainda não migrado.

    Aceitar só bcrypt aqui criaria um efeito perverso: quem ainda tem senha
    legada consegue **entrar** e nunca consegue **confirmar** — ficaria
    trancado fora de toda ação crítica, sem entender por quê, porque a senha
    que ele acabou de digitar no login "não funciona".
    """
    guardado = (hash_guardado or "").strip()
    if not guardado or not senha:
        return False

    if guardado.startswith("$2"):
        try:
            import bcrypt

            return bcrypt.checkpw(senha.encode("utf-8"), guardado.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[StepUp] bcrypt indisponível: %s", type(exc).__name__)
            return False

    if len(guardado) == 64:
        import hashlib
        import hmac

        # `compare_digest` e não `==`: comparação comum vaza, pelo tempo, o
        # quanto do hash bateu.
        return hmac.compare_digest(
            hashlib.sha256(senha.encode("utf-8")).hexdigest(), guardado.lower())

    logger.warning("[StepUp] formato de senha não reconhecido")
    return False


def _resumir_dispositivo(agente: Optional[str], ip: Optional[str]) -> str:
    """Navegador e origem aproximada, sem IP inteiro."""
    navegador = "navegador desconhecido"
    ua = (agente or "").lower()
    for chave, nome in (("edg/", "Edge"), ("chrome", "Chrome"),
                        ("firefox", "Firefox"), ("safari", "Safari")):
        if chave in ua:
            navegador = nome
            break

    origem = ""
    if ip:
        partes = str(ip).split(".")
        if len(partes) == 4:
            # Dois octetos: dizem provedor e região, e é o bastante para alguém
            # reconhecer "esta não sou eu". Os outros dois identificariam a casa.
            origem = f" · {partes[0]}.{partes[1]}.x.x"
    return f"{navegador}{origem}"
