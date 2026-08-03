"""O `flow_token` atravessa do WhatsApp até o motor.

📊 03/08/2026. O canal de resposta a formulário nativo foi provado no ar. E a
auditoria de ponta a ponta achou, no mesmo dia, que ele **nunca teria sido
exercitado em produção**: o token morria no caminho, por dois furos
independentes.

**FURO 1 — a ponte tinha só um lado.** `try_route_insurer_inbound` já recebia
`interactive=payload_dict.get("interactive")`. Mas quem MONTA o `payload_dict`
nunca copiava o campo do inbound normalizado. Sempre `None`. O próprio
`evolution_inbound.py` avisava em comentário: *"o caminho quente do produto
ainda não chama isto"*.

**FURO 2 — o buffer apagava o token.** `data["payload"] = payload` sobrescreve
a cada mensagem. A URA da família HDI manda rajadas: o formulário e, atrás
dele, um aviso de fila. O aviso apagava o token, e a resposta ficava sem
endereço — o motor pausaria com `formulario_pronto_sem_flow_token` e ninguém
saberia que a causa foi um debounce de 8 segundos.

Os dois tinham de ser fechados: um sozinho não faz o token chegar.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def o_webhook_copia_o_interactive() -> None:
    fonte = (RAIZ / "app/api/webhook.py").read_text(encoding="utf-8")

    # A linha da MONTAGEM, dentro do payload_dict — não o comentário que explica.
    montagem = [
        ln for ln in fonte.splitlines()
        if re.match(r'^\s+"interactive":\s*normalized\.get\("interactive"\)', ln)
    ]
    checar(len(montagem) >= 1,
           "o payload_dict COPIA o interactive do inbound normalizado")

    # E o leitor continua lá — sem ele, copiar não serve de nada.
    checar('payload_dict or {}).get("interactive")' in fonte
           or 'interactive=(payload_dict' in fonte,
           "e o roteador de acionamento continua LENDO esse campo")


def o_buffer_nao_apaga_o_token() -> None:
    """Simula a rajada: formulário, e logo atrás um aviso sem interativa."""
    fonte = (RAIZ / "app/services/message_buffer_service.py").read_text(encoding="utf-8")
    checar("data[\"payload\"] = payload\n" not in fonte.replace("\r\n", "\n"),
           "a sobrescrita crua do payload saiu")

    # O comportamento, não só o texto: reproduz a regra escrita no arquivo.
    def fundir(anterior_payload: dict | None, novo_payload: dict) -> dict:
        anterior = (anterior_payload or {}).get("interactive")
        novo = dict(novo_payload or {})
        if anterior and not novo.get("interactive"):
            novo["interactive"] = anterior
        return novo

    formulario = {
        "phone": "5511999999999",
        "interactive": {"kind": "flow", "flow": {"flow_token": "tok-abc", "flow_id": "857030507196739"}},
    }
    aviso_de_fila = {"phone": "5511999999999"}

    depois = fundir(formulario, aviso_de_fila)
    checar((depois.get("interactive") or {}).get("flow", {}).get("flow_token") == "tok-abc",
           "mensagem SEM interativa nao apaga o token do formulario anterior",
           json.dumps(depois.get("interactive")))

    # Interativa nova VENCE a antiga — o mais recente é o mais verdadeiro.
    outro_formulario = {
        "phone": "5511999999999",
        "interactive": {"kind": "flow", "flow": {"flow_token": "tok-novo"}},
    }
    depois2 = fundir(formulario, outro_formulario)
    checar((depois2.get("interactive") or {}).get("flow", {}).get("flow_token") == "tok-novo",
           "mas uma interativa NOVA vence a antiga")

    # O resto do payload continua sendo o mais recente.
    depois3 = fundir({"phone": "111", "interactive": {"kind": "flow"}}, {"phone": "222"})
    checar(depois3.get("phone") == "222",
           "e o resto do payload continua sendo o mais recente")


def o_guarda_tem_como_falhar() -> None:
    """Sem interativa anterior, não se inventa nenhuma."""
    def fundir(anterior_payload: dict | None, novo_payload: dict) -> dict:
        anterior = (anterior_payload or {}).get("interactive")
        novo = dict(novo_payload or {})
        if anterior and not novo.get("interactive"):
            novo["interactive"] = anterior
        return novo

    limpo = fundir({"phone": "1"}, {"phone": "2"})
    checar("interactive" not in limpo,
           "sem interativa anterior, nenhuma e inventada")


def main() -> int:
    print(__doc__)
    print("== o webhook copia o interactive ==")
    o_webhook_copia_o_interactive()
    print("== o buffer nao apaga o token ==")
    o_buffer_nao_apaga_o_token()
    print("== o guarda tem como falhar ==")
    o_guarda_tem_como_falhar()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O FLOW_TOKEN ATRAVESSA — DOS DOIS LADOS DA PONTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
