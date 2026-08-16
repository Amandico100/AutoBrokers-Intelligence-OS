# -*- coding: utf-8 -*-
"""Question engine do Maxpar — `POST /questionarios/perguntas`, medido.

ORIGEM (captura 2026-08-15)
---------------------------
PERGUNTA_PELICULA ......... YELUM har entry 240 (200)
PERGUNTA_PORTA_DIANT_TRAS . YELUM har entry 252 (200)
PERGUNTA_LADO ............. YELUM har entry 255 (200)
PERGUNTA_LADO_PORTO ....... PORTO har entry 224 (200)
SEQUENCIA_YELUM ........... entries 240, 252, 255, 257 — a última é **204**
SEQUENCIA_PORTO ........... entries 224, 230 — a última é **204**

🔴 A DIFERENÇA QUE ESTE FIXTURE EXISTE PARA PRESERVAR
=====================================================
A MESMA pergunta (código 35, "QUAL O LADO DO ITEM DANIFICADO?") veio diferente
nas duas seguradoras:

                        Yelum                    Porto
    TipoPergunta        "O"                      "P"
    ordem das opções    40 · 38 · 39             40 · 39 · 38
    QuantidadeRespostas 26                       18

Mesmos códigos, mesmos textos, **posições trocadas e tipo diferente**. Um robô
que escolhesse "a segunda opção" trocaria motorista por carona ao mudar de
seguradora — e o vidraceiro trocaria a porta errada.

Normalizar a ordem aqui destruiria a única prova de que posição não serve.
Não normalize.

Sem PII: perguntas e opções são domínio.
"""
from __future__ import annotations

PERGUNTA_PELICULA = {
    "Codigo": 4,
    "DescricaoPergunta": "O VIDRO DANIFICADO TEM PELÍCULA DE CONTROLE SOLAR (INSULFILM)?",
    "DescricaoPerguntaCredenciado": "O VIDRO DANIFICADO TEM PELÍCULA DE CONTROLE SOLAR (INSULFILM)?",
    "NumeroOrdem": 4,
    "PossuiItemNaoCoberto": False,
    "TipoPergunta": "A",
    "TemProdutoMapeado": True,
    "Respostas": [
        {"CodigoPergunta": 4, "CodigoResposta": 1, "DescricaoResposta": "SIM",
         "Tipo": "A", "NumeroOrdem": 1, "QuantidadeProdutoRespostas": 0,
         "QuantidadeRespostas": 3, "StatusServicoMovel": "S", "StatusReparo": None},
        {"CodigoPergunta": 4, "CodigoResposta": 2, "DescricaoResposta": "NÃO",
         "Tipo": "A", "NumeroOrdem": 2, "QuantidadeProdutoRespostas": 0,
         "QuantidadeRespostas": 3, "StatusServicoMovel": "S", "StatusReparo": None},
        {"CodigoPergunta": 4, "CodigoResposta": 3, "DescricaoResposta": "NÃO SABE",
         "Tipo": "A", "NumeroOrdem": 3, "QuantidadeProdutoRespostas": 0,
         "QuantidadeRespostas": 3, "StatusServicoMovel": "S", "StatusReparo": None},
    ],
}

PERGUNTA_PORTA_DIANT_TRAS = {
    "Codigo": 39,
    "DescricaoPergunta": "O VIDRO DANIFICADO É DA PORTA DIANTEIRA OU TRASEIRA?",
    "NumeroOrdem": 0,
    "PossuiItemNaoCoberto": False,
    "TipoPergunta": "P",
    "TemProdutoMapeado": True,
    "Respostas": [
        {"CodigoPergunta": 39, "CodigoResposta": 123, "DescricaoResposta": "DIANTEIRA",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 6,
         "QuantidadeRespostas": 26, "StatusServicoMovel": None, "StatusReparo": "N"},
        {"CodigoPergunta": 39, "CodigoResposta": 124, "DescricaoResposta": "TRASEIRA",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 7,
         "QuantidadeRespostas": 26, "StatusServicoMovel": None, "StatusReparo": "N"},
        {"CodigoPergunta": 39, "CodigoResposta": 125, "DescricaoResposta": "NÃO SABE",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 13,
         "QuantidadeRespostas": 26, "StatusServicoMovel": None, "StatusReparo": "N"},
    ],
}

# Yelum — TipoPergunta "O", ordem: NÃO SABE · CARONA · MOTORISTA
PERGUNTA_LADO = {
    "Codigo": 35,
    "DescricaoPergunta": "QUAL O LADO DO ITEM DANIFICADO?",
    "NumeroOrdem": 0,
    "PossuiItemNaoCoberto": False,
    "TipoPergunta": "O",
    "TemProdutoMapeado": True,
    "Respostas": [
        {"CodigoPergunta": 35, "CodigoResposta": 40, "DescricaoResposta": "NÃO SABE",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 13,
         "QuantidadeRespostas": 26, "StatusServicoMovel": None, "StatusReparo": "N"},
        {"CodigoPergunta": 35, "CodigoResposta": 38, "DescricaoResposta": "LADO DO CARONA",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 6,
         "QuantidadeRespostas": 26, "StatusServicoMovel": None, "StatusReparo": "N"},
        {"CodigoPergunta": 35, "CodigoResposta": 39, "DescricaoResposta": "LADO DO MOTORISTA",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 7,
         "QuantidadeRespostas": 26, "StatusServicoMovel": None, "StatusReparo": "N"},
    ],
}

# Porto — TipoPergunta "P", ordem: NÃO SABE · MOTORISTA · CARONA
PERGUNTA_LADO_PORTO = {
    "Codigo": 35,
    "DescricaoPergunta": "QUAL O LADO DO ITEM DANIFICADO?",
    "NumeroOrdem": 0,
    "PossuiItemNaoCoberto": False,
    "TipoPergunta": "P",
    "TemProdutoMapeado": True,
    "Respostas": [
        {"CodigoPergunta": 35, "CodigoResposta": 40, "DescricaoResposta": "NÃO SABE",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 9,
         "QuantidadeRespostas": 18, "StatusServicoMovel": None, "StatusReparo": "N"},
        {"CodigoPergunta": 35, "CodigoResposta": 39, "DescricaoResposta": "LADO DO MOTORISTA",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 4,
         "QuantidadeRespostas": 18, "StatusServicoMovel": None, "StatusReparo": "N"},
        {"CodigoPergunta": 35, "CodigoResposta": 38, "DescricaoResposta": "LADO DO CARONA",
         "Tipo": "P", "NumeroOrdem": 0, "QuantidadeProdutoRespostas": 5,
         "QuantidadeRespostas": 18, "StatusServicoMovel": None, "StatusReparo": "N"},
    ],
}

# (request_body, status, response_body) — o acumulado cresce a cada rodada
SEQUENCIA_YELUM = [
    ({"PerguntasResposta": []}, 200, PERGUNTA_PELICULA),
    ({"PerguntasResposta": [{"CodigoPergunta": 4, "CodigoResposta": 1, "TipoPergunta": "A"}]},
     200, PERGUNTA_PORTA_DIANT_TRAS),
    ({"PerguntasResposta": [{"CodigoPergunta": 4, "CodigoResposta": 1, "TipoPergunta": "A"},
                            {"CodigoPergunta": 39, "CodigoResposta": 123, "TipoPergunta": "P"}]},
     200, PERGUNTA_LADO),
    ({"PerguntasResposta": [{"CodigoPergunta": 4, "CodigoResposta": 1, "TipoPergunta": "A"},
                            {"CodigoPergunta": 39, "CodigoResposta": 123, "TipoPergunta": "P"},
                            {"CodigoPergunta": 35, "CodigoResposta": 38, "TipoPergunta": "O"}]},
     204, None),
]

SEQUENCIA_PORTO = [
    ({"PerguntasResposta": []}, 200, PERGUNTA_LADO_PORTO),
    ({"PerguntasResposta": [{"CodigoPergunta": 35, "CodigoResposta": 38, "TipoPergunta": "P"}]},
     204, None),
]

# 📊 `POST /questionarios/regras-reparo` (YELUM entry 264) — decide reparo × troca.
REGRAS_REPARO_YELUM = {"ExibirDialogDeReparo": False}


class SessaoDeQuestionarioFalsa:
    """Reproduz o motor offline, na ordem exata da captura.

    Existe porque o motor é **stateless no servidor**: o cliente reenvia o
    acumulado inteiro a cada rodada. Isso torna o replay fiel — não é uma
    imitação do comportamento, é o mesmo protocolo com as mesmas respostas.
    """

    def __init__(self, sequencia):
        self.sequencia = list(sequencia)
        self.i = 0
        self.enviados = []

    async def proxima_pergunta(self, respostas):
        self.enviados.append(list(respostas or []))
        if self.i >= len(self.sequencia):
            return {"ok": False, "status": 0, "json": None, "fim_do_questionario": False}
        _req, status, corpo = self.sequencia[self.i]
        self.i += 1
        return {"ok": status < 400, "status": status, "json": corpo,
                "fim_do_questionario": status == 204}
