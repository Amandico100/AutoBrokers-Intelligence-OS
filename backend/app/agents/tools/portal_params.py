"""SPEC-020 P3 — logica PURA da tool portal_action (sem langchain, testavel).

build_portal_params: monta os params do portal_job a partir dos dados do agente +
o perfil de acionamento da corretora (solicitante). format_result: traduz o job
terminado para uma frase que o agente usa na conversa.
"""
from __future__ import annotations

from typing import Optional, Tuple

REQUIRED = ("insurer_name", "cpf_cnpj", "placa", "data_dano")


def build_portal_params(flat: dict, profile: dict) -> Tuple[Optional[dict], Optional[str]]:
    """(params, erro). erro != None quando falta dado do acionamento ou o perfil
    de acionamento da corretora nao esta configurado (solicitante)."""
    missing = [k for k in REQUIRED if not str((flat or {}).get(k) or "").strip()]
    if missing:
        return None, f"Faltam dados do acionamento: {', '.join(missing)}. Pergunte ao segurado / consulte a apolice."
    profile = profile or {}
    sol = {
        "relacao": "Corretor",
        "nome": str(profile.get("nome") or "").strip(),
        "email": str(profile.get("email") or "").strip(),
        "telefone": str(profile.get("telefone") or "").strip(),
        "cpf_cnpj": str(profile.get("cpf_cnpj") or "").strip(),
    }
    if not (sol["nome"] and sol["email"]):
        return None, ("A corretora ainda nao configurou o Perfil de Acionamento (nome + e-mail). "
                      "Configure em Personalizacao -> Corretora antes de acionar portais.")
    params = {
        "insurer_name": str(flat["insurer_name"]).strip(),
        "cpf_cnpj": str(flat["cpf_cnpj"]).strip(),
        "placa": str(flat["placa"]).strip(),
        "data_dano": str(flat["data_dano"]).strip(),
        "solicitante": sol,
        "dano": {
            "peca": str(flat.get("peca") or "").strip(),
            "como": str(flat.get("como_ocorreu") or "").strip(),
            "onde": str(flat.get("onde_ocorreu") or "").strip(),
            "descricao": str(flat.get("descricao") or "").strip(),
        },
        "local": {
            "estado": str(flat.get("estado") or "").strip(),
            "cidade": str(flat.get("cidade") or "").strip(),
            "cep": str(flat.get("cep") or "").strip(),
        },
        "confirm": False,  # a tool NUNCA envia de verdade — para no 80% (aprovacao separada)
    }
    return params, None


def format_result(job: dict) -> str:
    """Traduz o job terminado para uma frase natural para o agente."""
    status = str((job or {}).get("status") or "")
    ev = (job or {}).get("evidence") or {}
    if status == "done":
        return f"Acionamento concluido no portal. {ev.get('message') or 'protocolo gerado'}".strip()
    if status == "needs_human":
        opts = ev.get("opcoes")
        base = ev.get("message") or "o portal parou numa etapa que preciso confirmar"
        if opts:
            return f"No portal, preciso decidir '{ev.get('campo')}' entre: {', '.join(opts[:12])}. ({base})"
        return f"Cheguei ate a confirmacao no portal ({base}). Reveja e aprove para enviar."
    if status == "failed":
        return f"Nao consegui concluir no portal: {job.get('error') or ev.get('message') or 'erro'}."
    return "Enfileirei o acionamento; o worker de portais ainda nao processou (o acesso a portais esta desligado?)."
