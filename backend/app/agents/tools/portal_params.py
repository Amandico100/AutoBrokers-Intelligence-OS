"""SPEC-020 P3 + SPEC-025 — logica PURA da tool portal_action (sem langchain, testavel).

SPEC-025: os FATOS (placa, veiculo, chassi, endereco, seguradora) vem da InfoCap
(server-side, endpoint /itens + /cliente_cpf) — o LLM NUNCA fornece nem inventa
placa/local. O LLM so decide o que e julgamento: qual apolice (se varias), o dano
(peca/como/onde/descricao) e a data. normalize_insurer traduz o nome legado da
InfoCap para a marca que o portal usa (Liberty -> Yelum).
"""
from __future__ import annotations

import unicodedata
from typing import Optional, Tuple

REQUIRED = ("cpf_cnpj", "data_dano")


def _fold(s: Optional[str]) -> str:
    """ASCII-fold para o que sera DIGITADO no portal (cidade/endereco): o teste
    validado digitou 'Florianopolis' sem acento — formato comprovado no autocomplete."""
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().strip()

# Sinonimos seguradora: nome/abreviacao da InfoCap -> marca no portal de vidros.
# Chave = fragmento (upper) testado por 'in'; ordem importa (mais especifico 1o).
_INSURER_ALIASES = (
    ("YELUM", "Yelum"),
    ("LIBERTY", "Yelum"),   # Liberty auto = Yelum (rebrand)
    ("LIBE", "Yelum"),
    ("TOKIO", "Tokio Marine"),
    ("PORTO", "Porto Seguro"),
    ("AZUL", "Azul"),
    ("ITAU", "Itau"),
    ("ITAÚ", "Itau"),
    ("MITSUI", "Mitsui"),
    ("MSIG", "Mitsui"),
    ("HDI", "HDI"),
    ("ALLIANZ", "Allianz"),
    ("BRADESCO", "Bradesco"),
    ("MAPFRE", "Mapfre"),
    ("SUHAI", "Suhai"),
    ("ZURICH", "Zurich"),
    ("SOMPO", "Sompo"),
)


def normalize_insurer(name: Optional[str]) -> str:
    """Nome da seguradora como o PORTAL a conhece. Fonte: seguradora da InfoCap."""
    raw = str(name or "").strip()
    up = raw.upper()
    for frag, canon in _INSURER_ALIASES:
        if frag in up:
            return canon
    return raw.title() if raw else ""


def build_portal_params(flat: dict, profile: dict, infocap: dict) -> Tuple[Optional[dict], Optional[str]]:
    """(params, erro). flat = decisoes do LLM (cpf, data, dano, placa_informada
    fallback). profile = perfil de acionamento da corretora. infocap = retorno REAL
    do vehicle lookup (policy/vehicle/client). erro != None quando falta fato."""
    flat = flat or {}
    missing = [k for k in REQUIRED if not str(flat.get(k) or "").strip()]
    if missing:
        return None, f"Faltam dados do acionamento: {', '.join(missing)}. Pergunte ao segurado."

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

    infocap = infocap or {}
    pol = infocap.get("policy") or {}
    veh = infocap.get("vehicle") or {}
    cli = infocap.get("client") or {}

    insurer = normalize_insurer(pol.get("seguradora") or pol.get("seguradora_abrev"))
    if not insurer:
        return None, "A InfoCap nao retornou a seguradora da apolice AUTO. Verifique a apolice."

    # Placa: SEMPRE da InfoCap. Fallback unico: o cliente informou (placa_informada)
    # porque a InfoCap nao tem — nunca a LLM por conta propria.
    placa = str(veh.get("placa") or "").strip().upper() or str(flat.get("placa_informada") or "").strip().upper()
    if not placa:
        return None, ("A apolice na InfoCap nao trouxe a PLACA do veiculo. Pergunte a placa ao segurado "
                      "e chame de novo com placa_informada.")

    endereco_txt = _fold(", ".join(p for p in (
        " ".join(x for x in (cli.get("logradouro"), cli.get("numero")) if x),
        cli.get("bairro"), f"{cli.get('cidade') or ''} {cli.get('estado') or ''}".strip(),
    ) if p))
    chassi = str(veh.get("chassi") or "").strip()

    params = {
        "insurer_name": insurer,
        "cpf_cnpj": str(flat["cpf_cnpj"]).strip(),
        "placa": placa,
        "data_dano": str(flat["data_dano"]).strip(),
        "solicitante": sol,
        "segurado": {
            "nome": str(cli.get("nome") or "").strip(),
            "apolice": str(pol.get("numapo") or "").strip(),
            "chassi": chassi,
            "ultimos_6_chassi": chassi[-6:] if chassi else "",
            "veiculo": str(veh.get("veiculo") or "").strip(),
            "cep": str(cli.get("cep") or "").strip(),
            "endereco": endereco_txt,
            "telefone": str(cli.get("telefone") or "").strip(),
            "email": str(cli.get("email") or "").strip(),
        },
        "dano": {
            "peca": str(flat.get("peca") or "").strip(),
            "como": str(flat.get("como_ocorreu") or "").strip(),
            "onde": str(flat.get("onde_ocorreu") or "").strip(),
            "descricao": str(flat.get("descricao") or "").strip(),
        },
        "local": {
            "estado": _fold(cli.get("estado")).upper(),
            "cidade": _fold(cli.get("cidade")).title(),
            "cep": str(cli.get("cep") or "").strip(),
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
        stage = str(((job or {}).get("evidence") or {}).get("stage_80") or "")
        captured = (ev.get("message") or "").lower()
        if stage or "80%" in captured or "confirmacao" in captured:
            return ("Abri o pedido no portal com os dados da apolice e cheguei ate a etapa final de "
                    "confirmacao da peca — falta so a aprovacao final para enviar. Diga isso ao cliente "
                    "com clareza (pedido aberto, em confirmacao final).")
        opts = ev.get("opcoes")
        base = ev.get("message") or "o portal parou numa etapa que preciso confirmar"
        if opts:
            return f"No portal, preciso decidir '{ev.get('campo')}' entre: {', '.join(opts[:12])}. ({base})"
        return f"Cheguei ate uma etapa que precisa de revisao no portal ({base})."
    if status == "failed":
        return f"Nao consegui concluir no portal: {job.get('error') or ev.get('message') or 'erro'}."
    return "Enfileirei o acionamento; o worker de portais ainda nao processou (o acesso a portais esta desligado?)."
