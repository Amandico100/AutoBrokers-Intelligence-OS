"""A tela do portal de vidros tem TRÊS coisas, e o robô só lia uma.

📊 SPEC-071 BLOCO 6 — telas que a Regina entregou em 14/08/2026:

    Atendimento nº 23085997     ✅ já era lido
    Franquia R$ 925,00          ❌ ZERO menções no `portal_worker` inteiro
    https://vistoria.mobi/...   ❌ ZERO menções

Os três saem da MESMA tela e valem coisas diferentes para o segurado:
o protocolo é para **cobrar**, a franquia é quanto ele vai **pagar**, e o link é
por onde ele **manda as fotos**. Levar só o protocolo entrega um terço do
atendimento e obriga a atendente a abrir o portal para ver o resto — que é
exatamente o trabalho que o produto existe para tirar dela.

⚠️ E UMA CORREÇÃO DE ESCOPO, para quem ler isto depois: 📊 os 39 acionamentos
que produziram zero protocolos **não são um defeito a consertar**. Eles pararam
na tela 6 porque `confirm` vem de `acionamento_liberado(agente_ligado)`, e o
agente está desligado — é a regra R1 do Founder funcionando. O destravamento
legítimo é ligar o agente, não afrouxar a trava.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}" + (f"  ({detalhe})" if detalhe else ""))
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _vidros():
    nome = "_teste_vidros_lanternas"
    if nome in sys.modules:
        return sys.modules[nome]
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    caminho = os.path.join(RAIZ, "portal_worker", "journeys", "vidros_lanternas.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


# A tela real, como a Regina a fotografou.
TELA_DA_REGINA = """Atendimento realizado com sucesso!
Atendimento nº 23085997
Franquia R$ 925,00
Envie as fotos do veículo pelo link https://vistoria.mobi/aB3xK9
O prazo para envio é de 48 horas."""


def teste_a_tela_entrega_os_tres() -> None:
    print("\n[1] Da tela da Regina saem os TRÊS, não um")
    V = _vidros()
    checar(V.extrair_protocolo(TELA_DA_REGINA) == "23085997",
           "🔴 o protocolo — para o segurado COBRAR",
           V.extrair_protocolo(TELA_DA_REGINA))
    checar(V.extrair_franquia(TELA_DA_REGINA) == "925,00",
           "🔴 a franquia — quanto ele vai PAGAR",
           V.extrair_franquia(TELA_DA_REGINA))
    checar(V.extrair_link_de_vistoria(TELA_DA_REGINA) == "https://vistoria.mobi/aB3xK9",
           "🔴 o link — por onde ele MANDA AS FOTOS",
           V.extrair_link_de_vistoria(TELA_DA_REGINA))
    checar(V.tem_vistoria(TELA_DA_REGINA) and V.tem_protocolo(TELA_DA_REGINA),
           "e a tela é reconhecida pelos dois marcadores")


def teste_a_franquia_nao_pega_o_numero_errado() -> None:
    """🔴 Dizer a franquia errada é pior que não dizer nenhuma.

    O segurado leva o número para a seguradora. Se estiver errado, ele descobre
    na hora de pagar — e a corretora é quem responde.
    """
    print("\n[2] A franquia não pega o número de outra coisa")
    V = _vidros()

    checar(V.extrair_franquia("Valor do serviço R$ 1.800,00\nFranquia R$ 925,00") == "925,00",
           "🔴 CONTROLE — um R$ ANTES do rótulo não é a franquia",
           "a janela de busca começa no rótulo, não no início da tela")
    checar(V.extrair_franquia("Franquia R$ 1,00 por item") == "",
           "🔴 CONTROLE — R$ 1,00 é recusado",
           "o piso é em REAIS, não em dígitos: contar dígito mede a grafia")
    checar(V.extrair_franquia("Valor da franquia R$ 1.250,00") == "1.250,00",
           "o milhar sobrevive inteiro", "1.250,00, não 1")
    checar(V.extrair_franquia("Participação obrigatória: R$ 480,00") == "480,00",
           "e o outro nome que as seguradoras usam também é lido")
    checar(V.extrair_franquia("Atendimento nº 23085997") == "",
           "🔴 CONTROLE — tela sem franquia devolve vazio, não um chute")
    checar(V.extrair_franquia("") == "" and V.extrair_franquia(None) == "",
           "CONTROLE — texto vazio não explode")


def teste_o_link_e_o_da_vistoria_e_nao_o_do_rodape() -> None:
    print("\n[3] O link é o da vistoria, não qualquer um da página")
    V = _vidros()

    checar(V.extrair_link_de_vistoria(
        "Leia a https://abraseuatendimento.com.br/politica-de-privacidade") == "",
        "🔴 CONTROLE — link do rodapé NÃO vira link de vistoria",
        "senão o robô manda o segurado para a política de privacidade")
    checar(V.extrair_link_de_vistoria("acesse https://vistoria.mobi/abc.") ==
           "https://vistoria.mobi/abc",
           "a pontuação final da frase não gruda na URL")
    checar(V.extrair_link_de_vistoria(
        "Rodapé https://abraseuatendimento.com.br | Fotos: https://vistoria.mobi/xY7")
        == "https://vistoria.mobi/xY7",
        "🔴 CONTROLE — com DOIS links, escolhe o certo")

    # 🔴 O motivo de esta leitura ser a única que não normaliza o texto.
    checar(V.extrair_link_de_vistoria("HTTPS://VISTORIA.MOBI/AbC") ==
           "HTTPS://VISTORIA.MOBI/AbC",
           "🔴 CONTROLE — a URL volta com a CAIXA ORIGINAL",
           "normalizar destruiria o caminho; um link com caixa trocada não abre")


def main() -> int:
    print("=" * 74)
    print("O PORTAL DE VIDROS ENTREGA OS TRÊS: protocolo, franquia e link")
    print("=" * 74)
    for teste in (teste_a_tela_entrega_os_tres,
                  teste_a_franquia_nao_pega_o_numero_errado,
                  teste_o_link_e_o_da_vistoria_e_nao_o_do_rodape):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("OS TRÊS CHEGAM — E NENHUM DELES É UM CHUTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
