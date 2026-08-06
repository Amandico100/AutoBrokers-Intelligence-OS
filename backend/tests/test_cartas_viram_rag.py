"""Da carta crua ao RAG, sem ninguém precisar apertar botão. SPEC-040/052.\n\nO que estava travado\n--------------------\n1.274 cartas prontas, ZERO publicadas. O conhecimento existia, tinha sido\nextraído de 7.622 atendimentos reais, e não chegava ao agente — porque\ndependia de alguém abrir uma tela e apertar um botão que nem estava claro.\n\n> Founder, 29/07/2026: "NAO SEI SE EU TENHO QUE APERTAR UM BOTAO OU VC QUE VAI
>  FAZER ISSO. SE FOR EU, TEM QUE ME EXPLICAR QUAL É O CAMINHO DENTRO DO
>  PORTAL ADMIN QUE ESTA CONFUSO PRA MIM AINDA."\n\nQuando a resposta certa exige explicar um caminho, o caminho está errado. Com\ncentenas de cartas novas a cada corretora pareada, "alguém lembra" não é plano.\n\nAs três garantias deste arquivo\n-------------------------------\n**Junta o que diz a mesma coisa** — e só dentro da mesma seguradora, porque\n"a HDI gera boleto" não é a mesma informação que a genérica.\n\n**O assunto entra no texto do chunk** — a busca é híbrida e o BM25 casa por\npalavra exata. Boleto é pedido de muitas formas ("não recebi", "segunda via",\n"venceu", "manda o código"), e sem "cobrança" escrito no chunk essa pergunta\ndisputa espaço com uma carta de vistoria que por acaso menciona pagamento.\n\n**Publicar faz parte da rodada** — não de um clique.\n"""

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
    # ATUALIZADO em 05/08/2026 — o caso da CNH mudou de resposta, de propósito.
    #
    # Ele esperava `documentos`, e `documentos` deixou de existir. Não era um
    # assunto: era um ARTEFATO, e artefato atravessa todos os momentos — CNH
    # aparece em sinistro, comprovante aparece em cobrança, laudo aparece em
    # vistoria. Uma carta com as duas coisas caía na gaveta que o regex
    # alcançasse primeiro, e a ordem do arquivo virava a decisão.
    #
    # A lição não morre, muda de lugar: a frase da CNH não é sobre um momento
    # do seguro, é sobre qualidade de envio — prática de atendimento. Ela agora
    # prova que o catch-all NOMEADO recebe o que não é momento, em vez de
    # inventar uma gaveta de artefato para ela.
    reais = {
        "Quando a parcela do cartão não é autorizada, a seguradora gera boleto": "cobranca",
        "Não recebi o boleto, é possível reenviar por WhatsApp": "cobranca",
        "Após o prazo limite sem pagamento, a apólice entra em processo de cancelamento": "cobranca",
        "A reguladora tem até dois dias úteis para agendar vistoria após abertura de sinistro": "sinistro",
        "O prestador de guincho entra em contato direto com o motorista": "assistencia",
        "Documentos como CNH devem ser enviados com boa qualidade de imagem": "atendimento",
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
    #
    # Medir a distância em caracteres já deu alarme falso três vezes neste
    # projeto: basta alguém escrever um comentário e a janela desliza. O que
    # importa é a ESTRUTURA — as duas chamadas dentro do mesmo `try`, com um
    # `except` logo depois.
    bloco = re.search(
        r"try:(?:.|\n)*?curar_sync(?:.|\n)*?publicar_lote_sync(?:.|\n)*?except Exception",
        fonte)
    checar(bool(bloco),
           "e uma falha aqui não derruba a rodada",
           "curar e publicar têm de estar no mesmo try, com except depois")


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


def teste_o_modelo_que_pensa_nao_joga_a_resposta_fora():
    print("\n[7] Resposta com bloco de pensamento continua legível")
    # O Claude Opus 5 PENSA por padrão (o Opus 4.8 não pensava se ninguém
    # pedisse). Com isso o LangChain devolve `content` como LISTA de blocos, e
    # `str()` numa lista devolve a repr da lista — o leitor de JSON encaixa o
    # bloco de pensamento junto e `json.loads` falha.
    #
    # Medido em 29/07/2026: 11 chamadas ao Opus 5 na síntese de playbook,
    # 3.395 tokens de saída cada, US$ 0,45 gastos, ZERO playbooks salvos.
    # O modelo respondeu, o token foi pago, e o resultado foi jogado fora —
    # sem erro aparecer em lugar nenhum.
    import json as _json

    fonte = _ler("app", "services", "attendance_distiller.py")
    i = fonte.find("def _texto_da_resposta")
    resto = fonte[i:]
    prox = re.search(r"\n(?:async\s+)?def\s", resto[1:])
    corpo = resto[:prox.start() + 1] if prox else resto
    ns = {"Any": object, "Optional": object}
    exec(corpo, ns)
    extrair = ns["_texto_da_resposta"]

    class _R:
        def __init__(self, c):
            self.content = c

    com_pensamento = _R([
        {"type": "thinking", "thinking": "vou montar o playbook {passo 1}"},
        {"type": "text", "text": '{"objetivo":"guincho","ficha_coleta":[{"campo":"placa"}]}'},
    ])
    texto = extrair(com_pensamento)
    checar(bool(texto) and "thinking" not in texto,
           "o bloco de pensamento não entra no texto", str(texto)[:80])
    try:
        checar(bool(_json.loads(texto)["ficha_coleta"]),
               "e o JSON do playbook é legível")
    except Exception as exc:  # noqa: BLE001
        checar(False, "e o JSON do playbook é legível", f"{type(exc).__name__}")

    checar(extrair(_R('{"a":1}')) == '{"a":1}', "texto puro continua funcionando")
    checar(extrair(_R([])) is None and extrair(_R(None)) is None,
           "e vazio continua virando None")

    # A checagem é dentro de `_call_llm`: o comentário de `_texto_da_resposta`
    # CITA o código antigo para explicar o defeito, e procurar no arquivo
    # inteiro acusaria a própria explicação.
    k = fonte.find("async def _call_llm")
    resto_call = fonte[k:]
    prox_call = re.search(r"\n(?:async\s+)?def\s", resto_call[1:])
    corpo_call = resto_call[:prox_call.start() + 1] if prox_call else resto_call
    checar('str(getattr(result, "content"' not in corpo_call,
           "a leitura crua com str() não voltou em `_call_llm`",
           "era ela que transformava a lista de blocos em lixo")


def main() -> int:
    print("=" * 70)
    print("A CARTA VIRA CONHECIMENTO DO AGENTE SEM NINGUÉM APERTAR BOTÃO")
    print("=" * 70)
    for teste in (teste_o_assunto_da_carta_e_o_que_o_corretor_digita,
                  teste_o_assunto_entra_no_texto_do_chunk,
                  teste_junta_a_mesma_ideia_e_preserva_a_seguradora,
                  teste_promessa_absoluta_e_barrada,
                  teste_publicar_faz_parte_da_rodada,
                  teste_a_carta_entra_no_rag_com_as_duas_metades,
                  teste_o_modelo_que_pensa_nao_joga_a_resposta_fora):
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
