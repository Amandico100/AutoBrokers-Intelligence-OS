"""Quem já pareou uma vez consegue parear de novo.

03/08/2026. O Founder tentou reconectar o WhatsApp do Amandus e a tela disse
*"a configuração do canal precisa de ajuste pelo suporte"*, com um código.
**Não havia suporte a chamar: era o próprio código recusando a única saída.**

O caminho:

    /instance/create        409/422 — a instancia ja existe
    procura a "fantasma"    acha, mas ela TEM telefone pareado
    a limpeza so vale para casca vazia  -> pula
    status >= 400           -> provider_http_4xx -> configuration_error

E a armadilha fechava sozinha: a tela mostrava "Desconectado", então **não
aparecia o botão Desconectar**. Sem botão para soltar e sem QR para parear.

O conserto é menor do que o defeito: a linha logo depois do `create` já pergunta
o status e já sabe tratar os dois desfechos — LoggedIn verdadeiro vira
`already_connected`, falso segue para o QR novo. Nunca chegava lá. Agora chega.

**Instância já existir não é erro. É o caso normal de quem re-pareia.**
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FONTE = (RAIZ / "app/services/whatsapp/pairing_orchestrator.py").read_text(encoding="utf-8")

_falhas: list[str] = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}")
        _falhas.append(descricao)


def _corpo_do_provider_create() -> str:
    """Só o corpo da função — o docstring desta suíte não pode ser a evidência."""
    i = FONTE.index("async def _provider_create")
    j = FONTE.index("async def _prepare_and_connect", i)
    return FONTE[i:j]


def a_instancia_com_telefone_nao_e_mais_erro() -> None:
    corpo = _corpo_do_provider_create()

    checar(
        "elif ghost:" in corpo,
        "existe um ramo para a instancia que JA TEM telefone",
    )
    # Só o BLOCO do elif — recortado pela indentação, não até o fim da função.
    # A primeira versão deste teste pegava a função inteira e acusava o `raise`
    # final, que é o tratamento correto do 4xx que NÃO é instância existente.
    # Detector largo demais reprova código bom, e é o tipo de teste que ensina
    # a ignorar teste.
    bloco = ""
    todas = corpo.splitlines()
    inicio = next((n for n, ln in enumerate(todas) if ln.strip() == "elif ghost:"), None)
    if inicio is not None:
        # A partir do começo da LINHA, não da posição do texto — senão o recuo
        # da primeira linha dá zero e o recorte engole a função inteira.
        recuo = len(todas[inicio]) - len(todas[inicio].lstrip())
        bloco = todas[inicio] + "\n"
        for ln in todas[inicio + 1:]:
            if ln.strip() and (len(ln) - len(ln.lstrip())) <= recuo:
                break
            bloco += ln + "\n"

    checar(
        bool(bloco) and re.search(r"\n\s+return\b", bloco) is not None,
        "esse ramo devolve o controle em vez de estourar",
    )
    checar(
        bool(bloco) and "raise" not in bloco,
        "e o ramo em si nao levanta erro nenhum",
    )
    checar(
        "raise RuntimeError(f\"provider_http_{response.status_code}\")" in corpo,
        "e o 4xx que NAO e instancia existente continua estourando",
    )


def a_casca_vazia_continua_sendo_limpa() -> None:
    """O conserto nao pode ter apagado a limpeza que ja existia."""
    corpo = _corpo_do_provider_create()
    checar(
        "if ghost and not ghost.get(\"jid\") and ghost.get(\"id\"):" in corpo,
        "casca vazia (sem telefone) continua sendo detectada",
    )
    checar(
        "/instance/delete/" in corpo,
        "e continua sendo removida antes de recriar",
    )


def o_status_depois_do_create_trata_os_dois_desfechos() -> None:
    """A prova de que devolver o controle basta: quem decide vem logo depois."""
    i = FONTE.index("async def _prepare_and_connect")
    corpo = FONTE[i:i + 4000]
    checar(
        '"/instance/status"' in corpo,
        "logo apos o create, o codigo pergunta o status da instancia",
    )
    checar(
        'LoggedIn' in corpo and '"already_connected"' in corpo,
        "status com LoggedIn verdadeiro vira already_connected",
    )


def o_erro_4xx_continua_virando_configuration_error() -> None:
    """A traducao do erro nao mudou — mudou QUANDO ela acontece."""
    sys.path.insert(0, str(RAIZ))
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_pairing_sob_teste", RAIZ / "app/services/whatsapp/pairing_orchestrator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001
        print(f"  (pulado — modulo exige a stack completa: {type(exc).__name__})")
        return

    orq = mod.PairingOrchestrator
    checar(orq._error_state("provider_http_400") == "configuration_error",
           "400 continua virando configuration_error")
    checar(orq._error_state("provider_http_502") == "provider_unavailable",
           "502 continua virando provider_unavailable")


def main() -> int:
    print(__doc__)
    print("== instancia com telefone nao e mais erro ==")
    a_instancia_com_telefone_nao_e_mais_erro()
    print("== a casca vazia continua sendo limpa ==")
    a_casca_vazia_continua_sendo_limpa()
    print("== quem decide vem logo depois ==")
    o_status_depois_do_create_trata_os_dois_desfechos()
    print("== a traducao do erro nao mudou ==")
    o_erro_4xx_continua_virando_configuration_error()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("QUEM JA PAREOU UMA VEZ CONSEGUE PAREAR DE NOVO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
