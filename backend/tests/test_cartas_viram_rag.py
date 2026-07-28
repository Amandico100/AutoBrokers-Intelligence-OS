"""Da carta crua ao RAG, sem ninguém precisar apertar botão. SPEC-040/052.

O que estava travado
--------------------
1.274 cartas prontas, ZERO publicadas. O conhecimento existia, tinha sido
extraído de 7.622 atendimentos reais, e não chegava ao agente — porque
dependia de alguém abrir uma tela e apertar um botão que nem estava claro.

> Founder, 29/07/2026: "NAO SEI SE EU TENHO QUE APERTAR UM BOTAO OU VC QUE VAI
>  FAZER ISSO. SE FOR EU, TEM QUE ME EXPLICAR QUAL É O CAMINHO DENTRO DO
>  PORTAL ADMIN QUE ESTA CONFUSO PRA MIM AINDA."

Quando a resposta certa exige explicar um caminho, o caminho está errado. Com
centenas de cartas novas a cada corretora pareada, "alguém lembra" não é plano.

As três garantias deste arquivo
-------------------------------
**Junta o que diz a mesma coisa** — e só dentro da mesma seguradora, porque
"a HDI gera boleto" não é a mesma informação que a genérica.

**O assunto entra no texto do chunk** — a busca é híbrida e o BM25 casa por
palavra exata. Boleto é pedido de muitas formas ("não recebi", "segunda via",
"venceu", "manda o código"), e sem "cobrança" escrito no chunk essa pergunta
disputa espaço com uma carta de vistoria que por acaso menciona pagamento.

**Publicar faz parte da rodada** — não de um clique.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m

_spec = importlib.util.spec_from_file_location(
    "app.services.curadoria_cartas", os.path.join(RAIZ, "app", "services", "curadoria_cartas.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def teste_o_assunto_da_carta_e_o_que_o_corretor_digita():
    print("\n[1] Cada carta sabe de que assunto ela é")
    reais = {
        "Quando a parcela do cartão não é autorizada, a seguradora gera boleto": "cobranca",
        "Não recebi o boleto, é possível reenviar por WhatsApp": "cobranca",
        "Após o prazo limite sem pagamento, a apólice entra em processo de cancelamento": "cobranca",
        "A reguladora tem até dois dias úteis para agendar vistoria após abertura de sinistro": "sinistro",
        "O prestador de guincho entra em contato direto com o motorista": "assistencia",
        "Documentos como CNH devem ser enviados com boa qualidade de imagem": "documentos",
    }
    for texto, esperado in reais.items():
        checar(C.assunto_da_carta(texto) == esperado,
               f"{esperado:12} · {texto[:52]}...", C.assunto_da_carta(texto))


def teste_o_assunto_entra_no_texto_do_chunk():
    print("\n[2] E o assunto vai ESCRITO no chunk, não só no metadado")
    # Metadado não é indexado pelo BM25. Se "cobrança" não estiver no texto, a
    # metade lexical da busca não tem por onde casar.
    fonte = _ler("app", "services", "attendance_distiller.py")
    i = fonte.find("prefix_bits = [")
    trecho = fonte[i:i + 400] if i >= 0 else ""
    checar("assunto_da_carta" in trecho,
           "o assunto entra no prefixo do chunk",
           "sem ele, 'não recebi o boleto' disputa com uma carta de vistoria")
    checar("insurer_key" in trecho and "ramo" in trecho,
           "junto da seguradora e do ramo")


def teste_junta_a_mesma_ideia_e_preserva_a_seguradora():
    print("\n[3] Junta o repetido — mas nunca entre seguradoras diferentes")
    cartas = [
        {"id": "1", "insurer_key": None,
         "card_text": "Quando o pagamento EM cartão não é autorizado, a seguradora gera boleto com nova data"},
        {"id": "2", "insurer_key": None,
         "card_text": "Quando o pagamento NO cartão não é autorizado, a seguradora gera boleto com nova data"},
        {"id": "3", "insurer_key": "hdi",
         "card_text": "Quando o pagamento no cartão não é autorizado, a seguradora HDI gera boleto com nova data"},
        {"id": "4", "insurer_key": None,
         "card_text": "Boletos de pagamento são enviados diretamente ao segurado pela corretora"},
        {"id": "5", "insurer_key": None,
         "card_text": "A franquia do sinistro é paga pelo segurado diretamente à oficina que faz o reparo"},
    ]
    ficam, copias = C.escolher_representantes(cartas)
    checar(len(copias) == 1 and copias[0] in ("1", "2"),
           "duas frases iguais viram uma", f"copias={copias}")
    checar("3" in ficam,
           "a carta da HDI sobrevive separada",
           "é ela que dá confiança ao agente quando o segurado é da HDI")
    checar("4" in ficam and "5" in ficam,
           "e ideias distintas não são juntadas",
           "juntar dois fatos diferentes apaga conhecimento")


def teste_promessa_absoluta_e_barrada():
    print("\n[4] Promessa sem exceção não vai para o RAG")
    # Existe uma carta dizendo que apólice cancelada não tem recuperação E
    # outra dizendo que comprovante permite pedir reanálise. Em seguro quase
    # tudo tem exceção; um absoluto errado faz a corretora prometer o que não
    # pode cumprir.
    for texto in ("Allianz cancela a apólice sem possibilidade de recuperação",
                  "Vidro trincado nunca é coberto pela apólice",
                  "O reembolso sempre é pago em 3 dias"):
        checar(bool(C._ABSOLUTO.search(texto)), f"barrada: {texto[:56]}")
    for texto in ("Comprovante de pagamento pode ser usado para pedir reanálise",
                  "Coberturas de vidros costumam ter franquia e limite máximo"):
        checar(not C._ABSOLUTO.search(texto), f"passa: {texto[:56]}")


def teste_publicar_faz_parte_da_rodada():
    print("\n[5] Publicar não depende de alguém lembrar")
    fonte = _ler("app", "services", "attendance_distiller.py")
    checar("publicar_lote_sync" in fonte and "curar_sync" in fonte,
           "o Destilador cura e publica na própria rodada")
    i, j = fonte.find("curar_sync"), fonte.find("publicar_lote_sync")
    checar(0 <= i < j,
           "e CURA antes de publicar",
           "quase-cópia que entra no Qdrant é bem mais cara de tirar depois")
    checar("CARDS_PUBLISH_PER_RUN" in fonte,
           "com teto por rodada",
           "1.274 cartas de uma vez é um pico de custo sem necessidade")
    # Falhar ao publicar não pode derrubar a destilação inteira.
    trecho = fonte[max(0, i - 900):j + 700]
    checar("except Exception" in trecho, "e uma falha aqui não derruba a rodada")


def teste_a_carta_entra_no_rag_com_as_duas_metades():
    print("\n[6] Busca híbrida: denso E esparso")
    # A janela é a FUNÇÃO, não um punhado de caracteres. Medir por distância
    # dá alarme falso assim que alguém escreve um comentário — foi o que
    # aconteceu na primeira versão deste caso.
    fonte = _ler("app", "services", "attendance_distiller.py")
    i = fonte.find("def publish_card_sync")
    resto = fonte[i:]
    prox = re.search(r"\n(?:async\s+)?def\s", resto[1:])
    corpo = resto[:prox.start() + 1] if prox else resto
    checar("SparseTextEmbedding" in corpo,
           "a carta leva o vetor esparso (BM25)",
           "sem ele, procurar 'CVV' ou 'carta verde' não acha carta nenhuma")
    checar("sparse_embeddings=sparse" in corpo, "e ele é entregue ao Qdrant")
    checar("_card_pii_clean" in corpo,
           "e a PII é reconferida no instante da publicação",
           "é a terceira camada, a que não depende de ninguém lembrar")


def main() -> int:
    print("=" * 70)
    print("A CARTA VIRA CONHECIMENTO DO AGENTE SEM NINGUÉM APERTAR BOTÃO")
    print("=" * 70)
    for teste in (teste_o_assunto_da_carta_e_o_que_o_corretor_digita,
                  teste_o_assunto_entra_no_texto_do_chunk,
                  teste_junta_a_mesma_ideia_e_preserva_a_seguradora,
                  teste_promessa_absoluta_e_barrada,
                  teste_publicar_faz_parte_da_rodada,
                  teste_a_carta_entra_no_rag_com_as_duas_metades):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O QUE A EQUIPE ENSINOU CHEGA AO AGENTE, SOZINHO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
