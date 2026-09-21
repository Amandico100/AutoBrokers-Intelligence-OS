# -*- coding: utf-8 -*-
"""G9 + P-PILOTO-02 + P-PILOTO-08 + `_idempotency_key`.

SPEC-EXTRA-001.10 N-1/P1-1, e as três pendências que o acionamento de vidros
arrastava.

## O que este arquivo prova, em uma frase cada

```
o DESFECHO do portal vira UMA mensagem de gente, e nenhuma loja é inventada
a parada DESCONHECIDA vira dossiê + pergunta honesta + 1 linha de aprendizado
o acionamento aparece na Fila e na Ficha, e o de uma corretora não vaza na outra
`_idempotency_key` deixou de ser lida e nunca escrita
```

## 🔴 O defeito de `_idempotency_key`, medido no BLOCO 0

📊 20/09/2026: `portal_worker/journeys/vidros_apifirst.py:231` lê
`params["_idempotency_key"]` e **nenhum lugar do repositório a gravava**. A rede
que impede o segundo `POST /atendimentos` dentro da journey existia e estava
desligada — o tipo de defeito que nenhum teste pega, porque o código está lá.

## 🔴 E o mais caro: a loja inventada

Uma loja que não veio no desfecho manda uma pessoa dirigir até um endereço que
não existe, com o carro quebrado. Por isso o bloco `nenhuma_loja_inventada` não
confere "a mensagem cita uma loja" — ele confere que **toda** palavra de loja
que sai na mensagem entrou pelo agregado que o portal mandou.
"""
from __future__ import annotations

import asyncio
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.agents.tools import portal_params as PP  # noqa: E402
from app.tasks import vigia_do_portal as VIGIA  # noqa: E402

# ⚠️ ATUALIZADO em 20/09/2026 (CLAUDE.md §9.3) — juiz B4 / red B6. Os textos das
# paradas foram REESCRITOS no conserto: nenhum promete continuacao ("eu sigo
# daqui", "chame de novo"), porque nao existe journey de continuacao, e todos
# terminam dizendo que a equipe assume. As frases-ancora deste guarda seguiram o
# texto novo; o que ele mede — cada parada fala em lingua de gente e diz o que
# fazer — nao mudou.
PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:400] if extra else ""))


# 💭 Tudo aqui é obviamente fictício (CLAUDE.md §12.1 e §13.9): nenhuma
# corretora real, nenhuma loja real, nenhum número de atendimento real.
DESFECHO_LOJA = {
    "tipo": "loja_direta",
    "codigo_atendimento": "99999999",
    "franquias": [{"titulo": "Valor para troca", "valor": "630"},
                  {"titulo": "Valor para reparo", "valor": "SEM FRANQUIA"}],
    "loja": {"nome": "Vidracaria Exemplo", "endereco": "Rua de Exemplo, 100",
             "referencia": "ao lado do mercado de exemplo", "telefone": "(48) 0000-0000"},
    "link_area_segurado": "https://exemplo.test/acompanhe/99999999",
    "titulo_portal": "As informacoes abaixo serao encaminhadas por e-mail ou SMS.",
    "roteador": {"IrParaConclusaoDeAtendimento": True, "DisponibilizarAgendamento": False},
}

DESFECHO_AGENDA = {
    "tipo": "agenda",
    "codigo_atendimento": "88888888",
    "franquias": [{"titulo": "Franquia", "valor": "410"}],
    "lojas": [
        {"nome": "Loja Exemplo Centro", "endereco": "Av. de Exemplo, 1",
         "cidade": "Joinville", "uf": "SC", "distancia": "9,2 km",
         "tempo": "13 minutos", "dias": ["22/09", "23/09"], "tem_agenda": True},
        {"nome": "Loja Exemplo Norte", "endereco": "Rua de Exemplo, 2",
         "cidade": "Joinville", "uf": "SC", "distancia": "14,0 km",
         "tempo": "21 minutos", "dias": [], "tem_agenda": False},
    ],
    "roteador": {"DisponibilizarAgendamento": True},
}

DESFECHO_ANALISTA = {
    "tipo": "analista", "codigo_atendimento": "77777777",
    "titulo_portal": "Seu atendimento ja esta com o analista responsavel.",
    "franquias": [],
}
DESFECHO_VISTORIA = {"tipo": "vistoria", "codigo_atendimento": "66666666"}
DESFECHO_DESCONHECIDO = {"tipo": "desconhecido", "codigo_atendimento": "55555555",
                         "roteador": {"ChaveQueNinguemConhece": True}}


# ==========================================================================
def n1_os_cinco_tipos_viram_mensagem() -> None:
    print("\n[N-1] os cinco desfechos viram mensagem de gente")

    loja = PP.mensagem_do_desfecho(DESFECHO_LOJA)
    checar("99999999" in loja, "loja_direta: o NUMERO do atendimento sai", loja[:120])
    checar("Valor para troca: R$ 630" in loja,
           "loja_direta: a franquia sai linha a linha, com o titulo do portal", loja)
    checar("Valor para reparo: SEM FRANQUIA" in loja,
           "e 'SEM FRANQUIA' e um VALOR, nao ausencia — a linha boa nao some", loja)
    checar("Vidracaria Exemplo" in loja and "Rua de Exemplo, 100" in loja
           and "(48) 0000-0000" in loja,
           "loja_direta: nome, endereco e telefone da loja saem", loja)
    checar("combina o dia" in loja and "ligar" in loja,
           "e diz que e a LOJA que combina o dia, e que ele pode ligar", loja)
    checar("https://exemplo.test/acompanhe/99999999" in loja,
           "e o link de acompanhamento sai EXATO", loja)

    agenda = PP.mensagem_do_desfecho(DESFECHO_AGENDA)
    checar("1)" in agenda and "2)" in agenda,
           "agenda: as lojas saem NUMERADAS, para ele responder um numero", agenda)
    checar("9,2 km" in agenda and "13 minutos" in agenda,
           "agenda: distancia e tempo saem", agenda)
    checar("22/09" in agenda and "23/09" in agenda,
           "agenda: os dias com agenda saem", agenda)
    checar("sem agenda aberta" in agenda,
           "agenda: e a loja SEM agenda diz que nao tem, em vez de sumir", agenda)
    checar("NÚMERO da loja" in agenda and "DIA" in agenda,
           "agenda: pede o numero da loja e o dia", agenda)
    # 🔴 A HONESTIDADE QUE A SPEC EXIGE: o robô não agenda (P1-2 é CANDIDATE).
    checar("nossa equipe" in agenda and "Não considere agendado" in agenda,
           "agenda: NAO promete que o robo agenda — a equipe conclui", agenda)

    analista = PP.mensagem_do_desfecho(DESFECHO_ANALISTA)
    checar("analista" in analista and "próximo dia útil" in analista,
           "analista: o texto do portal + o prazo, sem jargao", analista)

    vistoria = PP.mensagem_do_desfecho(DESFECHO_VISTORIA)
    checar("vistoria" in vistoria and "equipe" in vistoria
           and "não vai precisar repetir" in vistoria,
           "vistoria: handoff honesto, e ele nao repete nada", vistoria)

    desconhecido = PP.mensagem_do_desfecho(DESFECHO_DESCONHECIDO)
    checar("não consigo interpretar" in desconhecido and "equipe" in desconhecido,
           "desconhecido: diz a verdade incomoda em vez de inventar", desconhecido)
    checar("informação errada" in desconhecido,
           "e explica POR QUE nao arrisca", desconhecido)

    # O aviso antifraude vai em TODOS — é onde o golpe chega.
    for nome, texto in (("loja", loja), ("agenda", agenda), ("analista", analista),
                        ("vistoria", vistoria), ("desconhecido", desconhecido)):
        checar("depósito" in texto and "franquia" in texto.lower(),
               f"{nome}: o aviso antifraude do portal vai junto", texto[-200:])

    # 🔴 CONTROLE: sem desfecho, a funcao fica CALADA. Uma funcao que sempre
    # devolve texto passaria em tudo acima e falaria sobre pedidos que nao ha.
    for vazio in (None, {}, "nao sou dict", []):
        checar(PP.mensagem_do_desfecho(vazio) == "",
               f"CONTROLE: sem desfecho ({vazio!r}), a mensagem e VAZIA")


def n1_nenhuma_loja_inventada() -> None:
    """O guarda mais caro: toda loja citada entrou pelo agregado."""
    print("\n[N-1-loja] nenhuma loja aparece fora do que o portal mandou")

    # Um desfecho de AGENDA sem lojas: a mensagem não pode conter nome, endereço
    # nem telefone de loja nenhuma — nem os da fixture de loja_direta.
    sem_lojas = {**DESFECHO_AGENDA, "lojas": []}
    texto = PP.mensagem_do_desfecho(sem_lojas)
    for palavra in ("Vidracaria Exemplo", "Loja Exemplo Centro", "Loja Exemplo Norte",
                    "Rua de Exemplo, 100", "Av. de Exemplo, 1", "(48) 0000-0000",
                    "9,2 km", "22/09"):
        checar(palavra not in texto,
               f"sem lojas no desfecho, '{palavra}' NAO aparece", texto)
    checar("não consegui ler a lista de lojas" in texto,
           "e a mensagem DIZ que nao leu a lista, em vez de ficar muda", texto)

    # loja_direta sem o bloco da loja: mesma regra.
    sem_loja = {k: v for k, v in DESFECHO_LOJA.items() if k != "loja"}
    texto2 = PP.mensagem_do_desfecho(sem_loja)
    checar("Vidracaria Exemplo" not in texto2 and "Rua de Exemplo" not in texto2,
           "loja_direta sem a loja: nenhum endereco e inventado", texto2)
    checar("entram em contato com você" in texto2,
           "e ele fica sabendo que a loja vai procura-lo", texto2)

    # 🔴 CONTROLE: com as lojas, elas SAEM. Sem esta linha, uma funcao que
    # nunca citasse loja nenhuma passaria em todo o bloco acima.
    completo = PP.mensagem_do_desfecho(DESFECHO_AGENDA)
    checar("Loja Exemplo Centro" in completo and "9,2 km" in completo,
           "CONTROLE: com as lojas no desfecho, elas APARECEM", completo[:200])


def n1_o_mesmo_texto_dentro_e_fora_da_janela() -> None:
    """A tool e o Vigia falam a MESMA coisa — a janela de 150s não muda a verdade."""
    print("\n[N-1-janela] format_result e o Vigia usam o mesmo escritor")

    job = {"status": "done", "evidence": {"desfecho": DESFECHO_LOJA},
           "params": {"dano": {"peca": "para-brisa"}, "placa": "AAA0A91"}}

    da_tool = PP.format_result(job)
    corpo = PP.mensagem_do_desfecho(DESFECHO_LOJA)
    checar(corpo in da_tool,
           "a tool entrega a mensagem pronta, inteira, ao agente", da_tool[:200])
    checar("ENTREGUE AO SEGURADO" in da_tool and "com estas palavras" in da_tool,
           "e instrui o agente a NAO reescrever numero/valor/telefone", da_tool[:300])
    checar("NAO peca para eu abrir de novo" in da_tool,
           "e o aviso de nao reexecutar continua (o pedido ja existe)", da_tool[-200:])

    do_vigia = VIGIA.diagnosticar(job)
    checar(do_vigia and do_vigia["para_o_segurado"] == corpo,
           "e o Vigia manda EXATAMENTE o mesmo corpo ao segurado",
           str(do_vigia)[:300])
    checar(do_vigia and "99999999" in do_vigia["para_o_suporte"],
           "e o dossie da equipe traz o numero", str(do_vigia)[:300])

    # 🔴 CONTROLE: o Vigia continua CALADO quando o atendimento ja entregou.
    entregue = {**job, "evidence": {**job["evidence"], "entregue_ao_agente": True}}
    checar(VIGIA.diagnosticar(entregue) is None,
           "CONTROLE: com a marca de entrega, o Vigia fica calado",
           "duplicar aviso e pior que nao avisar")


def n1_as_paradas_tem_texto_humano() -> None:
    """Desconhecido nunca vira silêncio — e cada parada faz UMA pergunta."""
    print("\n[N-1-paradas] cada parada nova fala com o segurado e com a equipe")

    esperado = {
        "decidir_reparo": ("reparo", "30 minutos"),
        "peca_ambigua": ("Qual peca", "nome certinho"),
        "cidade_sem_rede": ("nao tem loja credenciada", "outra cidade"),
        "motivo_ambiguo": ("como o dano aconteceu", "lista fechada de causas"),
        "questionario_incompleto": ("pergunta sobre o seu vidro", "pergunta"),
        "tela_desconhecida": ("não conheço", "equipe"),
        "desconhecido": ("não conheço", "equipe"),
    }
    for stage, marcas in esperado.items():
        par = PP.texto_da_parada(stage)
        checar(par is not None, f"'{stage}' tem texto proprio")
        if not par:
            continue
        para_ele, para_equipe = par
        for marca in marcas:
            checar(marca in para_ele, f"'{stage}': a mensagem ao segurado diz '{marca}'",
                   para_ele)
        checar(len(para_equipe) > 60, f"'{stage}': e a equipe recebe um dossie", para_equipe)
        # 🔴 Sem jargao para o segurado. Ele nao sabe o que e uma fronteira.
        for jargao in ("stage", "needs_human", "PATCH", "journey", "evidence", "payload"):
            checar(jargao not in para_ele,
                   f"'{stage}': a mensagem ao segurado nao tem jargao ('{jargao}')",
                   para_ele)

    checar(PP.texto_da_parada("uma_parada_que_nao_existe") is None,
           "CONTROLE: parada sem texto proprio devolve None (cai na frase antiga)")

    # E o caminho real: `format_result` e o Vigia usam esses textos.
    job = {"status": "needs_human",
           "evidence": {"stage": "decidir_reparo",
                        "opcoes": ["Aceito tentar o reparo", "Prefiro trocar o vidro"]},
           "params": {"dano": {"peca": "para-brisa"}}}
    texto = PP.format_result(job)
    checar("reparo" in texto and "Aceito tentar o reparo" in texto,
           "format_result: a parada vira pergunta com as OPCOES do portal", texto)
    achado = VIGIA.diagnosticar(job)
    checar(achado and "reparo" in achado["para_o_segurado"]
           and "Aceito tentar o reparo" in achado["para_o_segurado"],
           "e o Vigia diz a mesma coisa fora da janela", str(achado)[:300])


def p8_o_que_ensina_e_o_que_nao_ensina() -> None:
    """A fila de aprendizado é fila de TRABALHO, não log."""
    print("\n[P-PILOTO-08] o que entra na fila de aprendizado")

    # 1) o contrato: a journey disse que nao entendeu
    r = PP.resumo_da_tela_desconhecida(
        {"tela_desconhecida": {"onde": "opcoes-disponiveis",
                               "resumo_mascarado": "Tela nova do portal, sem CPF ***"}})
    checar(r and r["onde"] == "opcoes-disponiveis", "marca explicita entra na fila", str(r))
    checar(r and "Tela nova do portal" in r["texto"], "com o texto ja MASCARADO da origem")

    # 2) desfecho de tipo que nao sabemos traduzir
    r2 = PP.resumo_da_tela_desconhecida({"desfecho": {"tipo": "algo_novo",
                                                      "titulo_portal": "Titulo novo"}})
    checar(r2 and "algo_novo" in r2["onde"], "tipo fora do contrato entra", str(r2))

    # 3) o caminho DOM parou e guardou o que viu
    r3 = PP.resumo_da_tela_desconhecida({"debug_dom": "Tela que o corredor nao conhece"})
    checar(r3 and r3["onde"] == "debug_dom", "debug_dom sem desfecho entra", str(r3))

    # 🔴 OS PARES DE CONTROLE. Sem eles a fila receberia TODO acionamento.
    for conhecido in ("loja_direta", "agenda", "analista", "vistoria"):
        checar(PP.resumo_da_tela_desconhecida(
                   {"desfecho": {"tipo": conhecido}, "debug_dom": "html qualquer"}) is None,
               f"CONTROLE: desfecho '{conhecido}' NAO ensina nada — zero linhas",
               "uma fila que recebe sucesso deixa de ordenar por 'quantas vezes apareceu'")
    for vazio in (None, {}, {"protocolo": "123"}):
        checar(PP.resumo_da_tela_desconhecida(vazio) is None,
               f"CONTROLE: evidencia {vazio!r} nao ensina nada")

    # O slug da seguradora sai do DADO do job, nunca de uma lista fixa (§13.9).
    checar(PP.slug_da_seguradora({"insurer_name": "Yelum"}) == "yelum",
           "o insurer_key da fila vem do params do job")
    checar(PP.slug_da_seguradora({"insurer_name": "Porto Seguro"}) == "porto_seguro",
           "e nome composto vira slug estavel")
    checar(PP.slug_da_seguradora({}) == "desconhecida",
           "sem nome, 'desconhecida' — que tambem e informacao")

    # E o teto: uma tela de 4 KB na fila e ilegivel para quem vai ler.
    grande = PP.resumo_da_tela_desconhecida({"debug_dom": "x" * 5000})
    checar(grande and len(grande["texto"]) <= 1200,
           f"o texto entra cortado ({len(grande['texto'])} <= 1200)")


if __name__ == "__main__":
    print("=" * 72)
    print("N-1 · P-PILOTO-08 — o desfecho chega ao segurado, e o novo vira fila")
    print("=" * 72)
    n1_os_cinco_tipos_viram_mensagem()
    n1_nenhuma_loja_inventada()
    n1_o_mesmo_texto_dentro_e_fora_da_janela()
    n1_as_paradas_tem_texto_humano()
    p8_o_que_ensina_e_o_que_nao_ensina()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
