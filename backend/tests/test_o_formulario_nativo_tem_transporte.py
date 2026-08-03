"""O formulário nativo sai — a rota, o embrulho e a ponte.

📊 03/08/2026, medido no ar entre dois números nossos. Seis formas enviadas,
cinco recusadas com o mesmo erro 479 — que o whatsmeow documenta como
*"Invalid stanza sent"* — e uma aceita:

    controle (sem embrulho)          479
    embrulho DocumentWithCaption     200, e o servidor devolveu
                                     Type: "InteractiveResponseMessage"

Três coisas mudaram por causa disso, e este teste guarda as três.

**A ROTA.** O portão nascia vazio de propósito, porque escolher uma rota
parecida seria inventar endpoint. Deixou de ser palpite quando a rota passou a
existir e foi provada. Agora o padrão é a rota provada, e a variável de ambiente
mudou de papel: era o que LIGAVA, virou o que corrige ou desliga.

**O EMBRULHO.** Não é preferência de estilo: sem ele o WhatsApp recusa a
mensagem inteira — em silêncio para o cliente e com um número para nós.

**A PONTE.** O motor sempre soube montar a resposta. Nunca teve por onde
entregá-la: `flow_sender` chegava `None` e todo formulário virava
`formulario_pronto_sem_transporte`, parado, com a resposta pronta ao lado.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def _carregar_provider():
    """Carrega o provider sem executar os `__init__` do caminho.

    `app/services/__init__.py` importa a stack de IA inteira, que não está
    instalada aqui e não tem nada a ver com transporte de mensagem. Registrar os
    pacotes como casca — com `__path__` apontando para as pastas reais — deixa os
    submódulos de verdade serem importados, e só os `__init__` ficam de fora.

    O que se testa continua sendo o arquivo que roda em produção, linha por
    linha. O que se evita é carregar meio produto para conferir um dicionário.
    """
    import types

    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    for nome in ("app", "app.services", "app.services.whatsapp",
                 "app.services.whatsapp.providers"):
        if nome not in sys.modules:
            casca = types.ModuleType(nome)
            casca.__path__ = [str(RAIZ / nome.replace(".", "/"))]  # type: ignore[attr-defined]
            sys.modules[nome] = casca

    caminho = RAIZ / "app/services/whatsapp/providers/evolution_go.py"
    spec = importlib.util.spec_from_file_location("_evolution_go_sob_teste", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_evolution_go_sob_teste"] = mod
    spec.loader.exec_module(mod)
    return mod


def a_rota_provada_e_o_padrao(mod) -> None:
    checar(
        mod.rota_de_flow_reply({}) == "/send/interactiveResponse",
        "sem variavel de ambiente, usa a rota PROVADA",
    )
    checar(
        mod.rota_de_flow_reply({"EVOLUTION_GO_FLOW_REPLY_PATH": "/outra/rota"}) == "/outra/rota",
        "um valor explicito continua vencendo",
    )
    checar(
        mod.rota_de_flow_reply({"EVOLUTION_GO_FLOW_REPLY_PATH": "sem/barra"}) == "/sem/barra",
        "a barra da frente e acrescentada quando falta",
    )
    # O desligamento tem de existir: se o fork mudar de caminho, alguem precisa
    # conseguir parar o envio sem esperar por um deploy.
    for palavra in ("off", "0", "none", "desligado"):
        checar(
            mod.rota_de_flow_reply({"EVOLUTION_GO_FLOW_REPLY_PATH": palavra}) == "",
            f"'{palavra}' DESLIGA o envio",
        )


def o_embrulho_viaja_sempre(mod) -> None:
    """O que sai pelo fio tem de carregar o embrulho — sempre, sem exceção."""
    capturado: dict = {}

    class ProviderEspiao(mod.EvolutionGoProvider):
        def _post(self, path, payload):  # type: ignore[override]
            capturado["path"] = path
            capturado["payload"] = payload
            return mod.SendResult(ok=True)

    p = ProviderEspiao({"base_url": "http://x", "token": "t", "provider": "evolution-go"})
    r = p.send_native_flow_response(
        "5547999990000",
        flow_token="uuid:1:2",
        params={"campo": "valor"},
        nome_do_envelope="galaxy_message",
    )

    checar(bool(getattr(r, "ok", False)), "o envio foi ate o transporte")
    checar(capturado.get("path") == "/send/interactiveResponse", "bateu na rota provada")

    corpo = capturado.get("payload") or {}
    checar(
        corpo.get("wrapInDocumentWithCaption") is True,
        "o EMBRULHO viaja — sem ele o WhatsApp recusa (479)",
    )
    checar(corpo.get("name") == "galaxy_message", "o envelope ecoado viaja")
    checar("flow_token" in str(corpo.get("paramsJSON") or ""), "o flow_token viaja dentro do paramsJSON")
    checar(corpo.get("number") == "5547999990000", "o destino viaja")


def a_ponte_esta_ligada() -> None:
    """`flow_sender` deixou de ser None no caminho real."""
    fonte = (RAIZ / "app/api/webhook.py").read_text(encoding="utf-8")

    checar(
        "def _responder_formulario_nativo" in fonte,
        "o transporte existe no webhook",
    )
    # A linha da CHAMADA, não a definição nem o comentário que a explica.
    passagem = [
        ln for ln in fonte.splitlines()
        if ln.strip().startswith("flow_sender=") and "None" not in ln
    ]
    checar(len(passagem) >= 1, "o transporte e PASSADO para o roteador")
    checar(
        any("_responder_formulario_nativo" in ln for ln in passagem),
        "e o que se passa e exatamente essa funcao",
    )
    checar(
        "send_native_flow_response" in fonte,
        "e ela chama o metodo que responde formulario",
    )


def a_falha_pausa_em_vez_de_derrubar() -> None:
    """Transporte que estoura derrubaria o inbound inteiro."""
    fonte = (RAIZ / "app/api/webhook.py").read_text(encoding="utf-8")
    i = fonte.index("def _responder_formulario_nativo")
    j = fonte.index("async def _human_reply_provider", i)
    corpo = fonte[i:j]
    checar("except Exception" in corpo, "a funcao captura falha")
    checar("return False" in corpo, "e devolve False em vez de estourar")
    checar("raise" not in corpo, "nunca levanta excecao para cima")


def main() -> int:
    print(__doc__)
    mod = _carregar_provider()
    print("== a rota provada e o padrao ==")
    a_rota_provada_e_o_padrao(mod)
    print("== o embrulho viaja sempre ==")
    o_embrulho_viaja_sempre(mod)
    print("== a ponte esta ligada ==")
    a_ponte_esta_ligada()
    print("== falha pausa, nao derruba ==")
    a_falha_pausa_em_vez_de_derrubar()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O FORMULARIO NATIVO TEM ROTA, EMBRULHO E TRANSPORTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
