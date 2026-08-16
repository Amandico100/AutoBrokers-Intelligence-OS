# -*- coding: utf-8 -*-
"""O motor de perguntas dinâmico — SPEC-074 Bloco I.

O contrato, medido
==================
📊 `POST /questionarios/perguntas`, 16/08/2026:

    request   {"PerguntasResposta": [ {CodigoPergunta, CodigoResposta, TipoPergunta} ]}
              ↑ o cliente reenvia o ACUMULADO INTEIRO a cada rodada
    200       UMA pergunta, com as opções reais dela
    204       acabou

O servidor é stateless entre rodadas. Isso tem duas consequências boas: o motor
é trivialmente replayável offline, e não existe estado escondido para dessincronizar.

O que este módulo se recusa a fazer
===================================
    ✗ roteiro fixo de perguntas       📊 Yelum fez 3, Porto fez 1, mesma família
    ✗ contar quantas virão            só o 204 sabe
    ✗ escolher por posição            ver abaixo — é o ponto mais importante
    ✗ decorar catálogo de opções      elas vêm na resposta, sempre
    ✗ usar "Não sabe" para avançar    SPEC-074 R6

🔴 A prova de que posição não serve
===================================
A MESMA pergunta — *"Qual o lado do item danificado?"*, código 35 — veio nas
duas capturas com ordem diferente:

    YELUM :  40 (Não sabe) · 38 (carona)    · 39 (motorista)
    PORTO :  40 (Não sabe) · 39 (motorista) · 38 (carona)

Mesmos códigos, mesmos textos, posições trocadas. Um robô que pegasse "a
segunda opção" trocaria motorista por carona entre uma seguradora e outra — e o
vidraceiro trocaria a porta errada. **Código e semântica vencem posição, e isto
está medido, não suposto.**
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 📊 Teto de segurança. A captura mais longa fez 3 rodadas; 12 dá folga de 4x e
# ainda denuncia um servidor que devolvesse a mesma pergunta para sempre.
MAX_RODADAS = 12

# Resultados possíveis do motor.
COMPLETO = "completo"                 # 204: todas respondidas
FALTA_RESPOSTA = "falta_resposta"     # o segurado não disse; precisa perguntar
AMBIGUO = "ambiguo"                   # a resposta dele casa com mais de uma opção
SEM_PROGRESSO = "sem_progresso"       # o portal repetiu a mesma pergunta
ERRO_API = "erro_api"


@dataclass
class Pergunta:
    """Uma pergunta do motor, como a API a devolve."""

    codigo: int
    texto: str
    tipo: str
    opcoes: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def textos_das_opcoes(self) -> List[str]:
        return [str(o.get("DescricaoResposta") or "") for o in self.opcoes]

    def codigo_da_opcao(self, texto_escolhido: Any) -> Optional[int]:
        """Do TEXTO escolhido para o CÓDIGO que a API espera.

        🔴 Casamento por texto exato primeiro; só depois por continência. Nunca
        por índice — ver a docstring do módulo.
        """
        alvo = str(texto_escolhido or "").strip().lower()
        if not alvo:
            return None
        for o in self.opcoes:
            if str(o.get("DescricaoResposta") or "").strip().lower() == alvo:
                try:
                    return int(o.get("CodigoResposta"))
                except (TypeError, ValueError):
                    return None
        for o in self.opcoes:
            d = str(o.get("DescricaoResposta") or "").strip().lower()
            if d and (alvo in d or d in alvo):
                try:
                    return int(o.get("CodigoResposta"))
                except (TypeError, ValueError):
                    return None
        return None


def ler_pergunta(corpo: Any) -> Optional[Pergunta]:
    """Traduz a resposta 200 da API. `None` quando não há pergunta legível."""
    if not isinstance(corpo, dict) or not corpo:
        return None
    cod = corpo.get("Codigo")
    if cod is None:
        return None
    try:
        cod_i = int(cod)
    except (TypeError, ValueError):
        return None
    respostas = corpo.get("Respostas")
    opcoes = [r for r in respostas if isinstance(r, dict)] if isinstance(respostas, list) else []
    return Pergunta(
        codigo=cod_i,
        texto=str(corpo.get("DescricaoPergunta") or ""),
        tipo=str(corpo.get("TipoPergunta") or ""),
        opcoes=opcoes,
    )


def escolher_resposta(pergunta: Pergunta,
                      *,
                      respostas_do_segurado: Dict[str, Any],
                      relato: str = "") -> Dict[str, Any]:
    """Casa o que o segurado disse com uma opção REAL da pergunta.

    Usa o vocabulário que já existe em `vidros_lanternas` — `explicar_especifico`
    — em vez de criar um segundo casador. Ele já sabe lado, dianteira/traseira,
    película, tamanho e posição de trincado, e já tem pisos de confiança.

    Devolve `{"situacao", "codigo", "texto", "motivo", "opcoes"}`.

    🔴 Sem match confiante, a resposta é `FALTA_RESPOSTA` **com as opções reais
    dentro** — e é isso que vira a pergunta que o atendente faz ao segurado. A
    alternativa (chutar) foi o que a SPEC-073 removeu do `_FORCE_CHOOSE`.
    """
    from portal_worker.journeys.vidros_lanternas import (
        explicar_especifico, explicar_match,
    )

    opcoes = pergunta.textos_das_opcoes
    if not opcoes:
        return {"situacao": ERRO_API, "codigo": None, "texto": "",
                "motivo": "a pergunta veio sem opcoes", "opcoes": []}

    # O que o segurado já disse, do mais específico para o mais geral. O relato
    # livre entra por último: ele é o que menos identifica um atributo.
    candidatos: List[str] = []
    for v in (respostas_do_segurado or {}).values():
        if isinstance(v, str) and v.strip():
            candidatos.append(v)
    if relato:
        candidatos.append(relato)

    for cand in candidatos:
        veredito = explicar_especifico(cand, opcoes, pergunta.texto)
        if not isinstance(veredito, dict):
            veredito = {}

        # 🔴 O PROTOCOLO DE COEXISTÊNCIA DOS DOIS VOCABULÁRIOS.
        #
        # `explicar_especifico` sabe de ATRIBUTO: lado, dianteira/traseira,
        # película, tamanho, posição do trincado, sim/não. Quando ele devolve
        # `dominio == "nenhum"`, está dizendo *"esta lista não é minha"* — e a
        # resposta certa NÃO é insistir, é cair no vocabulário de PEÇA
        # (`explicar_match`), que tem placar próprio e veto de peça diferente.
        #
        # 📊 O teste `test_o_80_por_cento_sabe_o_que_pergunta.py:354`
        # (`teste_o_vocabulario_do_80_nao_invade_a_tela_da_peca`) existe
        # exatamente para guardar esta fronteira. Sem esta ramificação, uma
        # pergunta de peça vinda do motor cairia no casador errado — que a
        # recusaria por não reconhecer o domínio — e o robô pararia num campo
        # que ele sabia responder.
        if str(veredito.get("dominio") or "") == "nenhum":
            veredito = explicar_match(cand, opcoes)
            if not isinstance(veredito, dict):
                veredito = {}

        escolha = veredito.get("escolha")
        if escolha:
            cod = pergunta.codigo_da_opcao(escolha)
            if cod is None:
                # A opção casou por texto mas não tem código: contrato mudou.
                # Parar é o certo — enviar sem código faria o portal decidir
                # sozinho qual resposta gravar.
                return {"situacao": ERRO_API, "codigo": None, "texto": escolha,
                        "motivo": "opcao sem CodigoResposta na resposta da API",
                        "opcoes": opcoes}
            return {"situacao": "ok", "codigo": cod, "texto": escolha,
                    "motivo": str((veredito or {}).get("motivo") or ""),
                    "opcoes": opcoes}

    return {"situacao": FALTA_RESPOSTA, "codigo": None, "texto": "",
            "motivo": f"o segurado nao respondeu: {pergunta.texto}",
            "opcoes": opcoes}


@dataclass
class ResultadoDoQuestionario:
    situacao: str
    respostas: List[Dict[str, Any]] = field(default_factory=list)
    pergunta_pendente: Optional[Pergunta] = None
    motivo: str = ""
    rodadas: int = 0
    perguntas_vistas: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def completo(self) -> bool:
        return self.situacao == COMPLETO

    def para_evidencia(self) -> Dict[str, Any]:
        """Sem PII: códigos, textos de domínio e o veredito. Nada do segurado."""
        return {
            "situacao": self.situacao,
            "rodadas": self.rodadas,
            "respondidas": len(self.respostas),
            "perguntas": self.perguntas_vistas[:12],
            "pendente": ({"codigo": self.pergunta_pendente.codigo,
                          "texto": self.pergunta_pendente.texto,
                          "opcoes": self.pergunta_pendente.textos_das_opcoes}
                         if self.pergunta_pendente else None),
            "motivo": self.motivo[:240],
        }


async def rodar_questionario(sessao: Any,
                             *,
                             respostas_do_segurado: Dict[str, Any],
                             relato: str = "",
                             max_rodadas: int = MAX_RODADAS) -> ResultadoDoQuestionario:
    """O laço: pergunta → casa → acumula → repete, até 204.

    Não escreve nada no portal. `POST /questionarios/perguntas` é consulta: ele
    devolve a próxima pergunta e não persiste resposta nenhuma. Quem persiste é
    `POST /questionarios`, que é a **fronteira B** e mora na journey, atrás do
    guard.

    Essa separação é o que permite rodar o questionário inteiro em modo de
    leitura, descobrir que falta um dado, e parar **sem ter tocado no pedido**.
    """
    acumulado: List[Dict[str, Any]] = []
    vistas: List[Dict[str, Any]] = []
    ultimo_codigo: Optional[int] = None
    repeticoes = 0

    for rodada in range(1, max_rodadas + 1):
        r = await sessao.proxima_pergunta(acumulado)

        if r.get("fim_do_questionario"):
            return ResultadoDoQuestionario(COMPLETO, acumulado, None,
                                           "204: questionario completo",
                                           rodada, vistas)

        if not r.get("ok"):
            return ResultadoDoQuestionario(
                ERRO_API, acumulado, None,
                f"http {r.get('status')} ao pedir a proxima pergunta",
                rodada, vistas)

        pergunta = ler_pergunta(r.get("json"))
        if pergunta is None:
            return ResultadoDoQuestionario(
                ERRO_API, acumulado, None,
                "resposta 200 sem pergunta legivel", rodada, vistas)

        # O portal repetiu a mesma pergunta: ou não aceitou a resposta, ou o
        # contrato mudou. Insistir gastaria as 12 rodadas para chegar no mesmo
        # lugar — parar com o dossiê é mais útil e mais rápido.
        if pergunta.codigo == ultimo_codigo:
            repeticoes += 1
            if repeticoes >= 2:
                return ResultadoDoQuestionario(
                    SEM_PROGRESSO, acumulado, pergunta,
                    f"o portal repetiu a pergunta {pergunta.codigo} apos a resposta",
                    rodada, vistas)
        else:
            repeticoes = 0
        ultimo_codigo = pergunta.codigo

        vistas.append({"codigo": pergunta.codigo, "texto": pergunta.texto,
                       "tipo": pergunta.tipo,
                       "opcoes": pergunta.textos_das_opcoes})

        escolha = escolher_resposta(pergunta,
                                    respostas_do_segurado=respostas_do_segurado,
                                    relato=relato)
        if escolha["situacao"] != "ok":
            return ResultadoDoQuestionario(
                escolha["situacao"], acumulado, pergunta,
                escolha["motivo"], rodada, vistas)

        acumulado.append({
            "CodigoPergunta": pergunta.codigo,
            "CodigoResposta": escolha["codigo"],
            "TipoPergunta": pergunta.tipo,
        })

    return ResultadoDoQuestionario(
        SEM_PROGRESSO, acumulado, None,
        f"teto de {max_rodadas} rodadas sem 204", max_rodadas, vistas)
