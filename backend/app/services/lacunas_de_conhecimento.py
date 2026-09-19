# -*- coding: utf-8 -*-
"""🔴 O QUE O AGENTE NÃO SOUBE RESPONDER VIRA TAREFA — e não morre no turno.

SPEC-EXTRA-001.5.1 · unidade D (defeito D12), com a emenda E1.

📊 **O defeito, medido em 19/09/2026:** `capability_gaps` tinha **0 linhas**, e
nenhum caminho de cobertura escrevia nela (`rg -n "capability_gaps" backend/app`
→ só a Auxiliary Factory e dois leitores). O segurado perguntava *"tem carro
reserva?"*, o agente respondia honestamente *"ainda não sei"* — e **ninguém
ficava sabendo**. A próxima destilação escolhia seguradora por palpite.

O QUE ESTE MÓDULO FAZ, NESTA ORDEM
==================================
```
1. GRAVA a lacuna em `capability_gaps`, por fingerprint, somando frequência
2. AVISA o humano — só quando a pergunta veio do SEGURADO, e no máximo
   1× por lacuna, por corretora, por dia (emenda E1)
```

⛔ **NENHUM MOTOR NOVO** (CLAUDE.md §5). Três peças já existiam e são
REUSADAS inteiras:

```
`auxiliaries/factory.py:407`   a FORMA do upsert: fingerprint · frequency_count
                              · first/last_seen. Aqui a chave muda (ela é de
                              COBERTURA), o mecanismo não
`redaction_service.redigir`   o redator do projeto. ⛔ A pergunta do cliente
                              NUNCA entra crua
`enviar_ao_grupo` (001.3)     a PORTA ÚNICA do grupo: guarda ("humano já está
                              aqui"), destino, um balão, contado
`reivindicar_o_envio` (001.3) o MARCADOR atômico no Redis — é ele que dá o teto
                              de 24 h, com a chave `lacuna:<fingerprint>`
```

🔴 **POR QUE O TETO DE 24 h NÃO É OPCIONAL (emenda E1).** Sem ele, TODA pergunta
que o agente não sabe vira um 🆘 no grupo — e a EXTRA-001.3 acabou de matar
exatamente esse ruído. Uma lacuna perguntada quarenta vezes é **uma** tarefa com
peso quarenta, não quarenta interrupções.

🔴 **E POR QUE SÓ NO CANAL DO SEGURADO.** No chat do corretor, quem precisa
saber já está lendo a resposta: ele acabou de ler *"ainda não tenho as condições
da HDI na base"*. Avisar o grupo seria contar a ele o que ele acabou de ver.
A lacuna, essa, é gravada nos dois canais — é dado de roadmap, não interrupção.

⚠️ **ESCOPO DECLARADO** (§5-D item 17): hoje isto cobre a lacuna de
**cobertura** (`capability_key='insurance.cobertura_e_assistencia'`). O
mecanismo aceita outras `capability_key` sem mudança nenhuma — estender a toda
pergunta que o agente não souber é uma SPEC própria, porque exige decidir o que
é "não saber" fora de um veredito determinístico.

⛔ **E ELE NUNCA DERRUBA A RESPOSTA.** Toda falha aqui é `logger.error` e
`{"gravou": False}`. Um segurado não pode ficar sem resposta porque uma linha de
backlog não entrou.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: A capacidade a que esta lacuna pertence. ⚠️ É o que faz a linha aparecer
#: agrupada no painel da Factory ("O que ainda não fazemos").
CAPABILITY_DE_COBERTURA = "insurance.cobertura_e_assistencia"

#: `gap_type` — 📊 o CHECK da tabela aceita (`pg_get_constraintdef`, 19/09/2026):
#: missing_skill · missing_tool · missing_connector · **missing_data** ·
#: missing_provider · missing_artifact · policy_blocked · unsupported_trigger ·
#: unsupported_workflow. Nenhuma migration é necessária.
TIPO_DA_LACUNA = "missing_data"

#: O teto do aviso: um por lacuna, por corretora, por dia (emenda E1).
JANELA_DO_AVISO_S = 24 * 3600

#: 🔴 Os estados que VIRAM lacuna. `fonte_indisponivel` **não** entra: é falha
#: de infraestrutura, e registrá-la como "falta o dado" mandaria alguém curar
#: uma condição geral que já está curada. O fallback genérico também não: ali a
#: casa RESPONDEU, com ressalva.
ESTADOS_QUE_VIRAM_LACUNA = ("nao_sabemos_ainda",)


def _redigir(texto: Any) -> str:
    """A redação canônica do projeto. Sem ela, nada é gravado.

    ⛔ Falhar para o lado de NÃO GRAVAR: uma pergunta crua em `capability_gaps`
    atravessa a fronteira corretora → plataforma, e ninguém percebe que
    atravessou até ser tarde (`factory.redigir`, mesma razão).
    """
    from app.services.intelligence.redaction_service import redigir

    return str(redigir(str(texto or "")) or "").strip()


def fingerprint_da_lacuna(cobertura: Dict[str, Any]) -> str:
    """`sha256("cobertura|seguradora|ramo|produto|servico")`, 32 hex.

    🔴 **GLOBAL POR CONTEÚDO, e isso é uma decisão, não um acaso.** 📊 O índice
    real é `capability_gaps_fingerprint_uk UNIQUE (fingerprint)` — sem
    `company_id` (`pg_indexes`, 19/09/2026). Logo: a MESMA falta, perguntada em
    duas corretoras, é UMA linha com peso dois. É o que se quer, porque a base
    de planos **é global** (D-PILOTO-01): quem cura a condição geral da HDI cura
    para todas. Duas linhas dariam a impressão de duas tarefas.

    ⚠️ `company_id` guarda a PRIMEIRA corretora que esbarrou na falta — é
    procedência, não dono. Nenhuma leitura desta tabela filtra por ele.
    """
    partes = "|".join([
        # ⚠️ A INTENÇÃO entra no fingerprint: "pediram e não temos linha" e
        # "perguntaram e não temos linha" são duas contagens que o painel lê de
        # formas diferentes. Somá-las esconderia a urgente dentro da outra.
        "cobertura:%s" % str(cobertura.get("intencao") or "pergunta"),
        str(cobertura.get("insurer_key") or "?"),
        str(cobertura.get("ramo") or "?"),
        str(cobertura.get("produto") or "?"),
        str(cobertura.get("servico") or "?"),
    ])
    return hashlib.sha256(partes.encode("utf-8")).hexdigest()[:32]


def descricao_da_lacuna(cobertura: Dict[str, Any]) -> str:
    """A frase que o humano lê no painel. **Sem PII, por construção.**

    ⛔ Nenhum campo desta frase vem da PERGUNTA: todos vêm do VEREDITO, que já é
    procedência (seguradora canônica, ramo, produto, serviço, motivo). A
    pergunta do cliente entra noutro lugar, redigida — e só no aviso ao humano.
    """
    servico = str(cobertura.get("servico") or "serviço não identificado")
    try:
        from app.services.skills.cobertura_e_assistencia import rotulo_do_servico

        servico = rotulo_do_servico(servico)
    except Exception:  # noqa: BLE001 — o rótulo nunca derruba o registro
        pass
    quem = str(cobertura.get("insurer_key") or "seguradora não identificada")
    ramo = str(cobertura.get("ramo") or "ramo não identificado")
    produto = str(cobertura.get("produto") or "produto não identificado")
    # 🔴 CONSERTO B4: `motivo` só chega aqui desde 19/09/2026 — `para_registro()`
    # não o carregava, e as cinco frases abaixo eram CÓDIGO MORTO em produção.
    # 📊 `plano_nao_identificado` e `sem_linha_publicada` gravavam a MESMA frase,
    # e o painel mandava curar o que podia já estar curado.
    motivo = str(cobertura.get("motivo") or "")
    porque = {
        "plano_nao_identificado": "o plano contratado não foi identificado na apólice",
        "sem_linha_publicada": "não há linha publicada na base para esse serviço",
        "seguradora_desconhecida": "a seguradora está fora do censo",
        "data_de_emissao_ilegivel": "a data de emissão da apólice não foi lida",
        "dois_planos_no_texto": "a apólice nomeia dois planos e nenhum vence",
    }.get(motivo, "não há linha publicada na base para esse serviço")
    # 🔴 RODADA 2 (N1-b): o painel precisa saber se o cliente PERGUNTOU ou
    # PEDIU. São duas prioridades de curadoria diferentes — "dez pessoas pediram
    # guincho na HDI e não temos linha" é mais urgente que dez dúvidas — e
    # escrever "perguntou" quando ele pediu é uma frase falsa num painel de
    # decisão.
    o_que_houve = ("Pedido de %s" if str(cobertura.get("intencao") or "pergunta")
                   == "pedido" else "Cobertura de %s") % servico
    return "%s · %s · %s · %s: %s" % (o_que_houve, quem, ramo, produto, porque)


def _texto_do_aviso(cobertura: Dict[str, Any], pergunta_redigida: str,
                    telefone: str = "") -> str:
    """O 🆘 da lacuna — a MESMA família de mensagem, o tamanho de um aviso.

    ⛔ **E ele NÃO diz quantas vezes já perguntaram** (CONSERTO P4). O
    `frequency_count` é GLOBAL por conteúdo: *"já perguntaram isto 2 vezes"* no
    grupo da corretora B pode estar contando a pergunta de um segurado da
    corretora A. Informação de outra corretora não atravessa (CLAUDE.md §7), e
    o número certo já vive no painel da plataforma, que é de quem pode vê-lo.

    ⚠️ **Por que não `human_handoff._montar_dossie`:** ele é montado a partir de
    uma linha de `conversations` e de um motivo de handoff, e uma lacuna não tem
    nenhum dos dois. Reusá-lo exigiria FORJAR uma linha de conversa — que é
    criar um segundo caminho com cara de primeiro. O que se reusa aqui é o que
    de fato é comum: o TIPO da mensagem, a porta e o traço do modelo.
    """
    from app.services.os_modelos_do_grupo import (
        _TRACO, _juntar, _linha, link_do_whatsapp,
    )

    servico = str(cobertura.get("servico") or "")
    try:
        from app.services.skills.cobertura_e_assistencia import rotulo_do_servico

        servico = rotulo_do_servico(servico)
    except Exception:  # noqa: BLE001
        pass
    return _juntar([
        "🆘 *PRECISO DE AJUDA* — não sei responder isto",
        _TRACO,
        _linha("O cliente perguntou", pergunta_redigida),
        _linha("Sobre", servico),
        _linha("Seguradora", cobertura.get("insurer_key")),
        _linha("Ramo", cobertura.get("ramo")),
        _linha("Produto", cobertura.get("produto")),
        _linha("Plano na apólice", cobertura.get("plano") or "não identificado"),
        "",
        "*👉 O QUE FAZER*",
        "Confirme com a seguradora e responda ao cliente. Eu não afirmei nada: "
        "disse que ia confirmar.",
        # 🔴 CONSERTO B2 — *"responda ao cliente"* sem dizer QUAL cliente é um
        # pedido que não dá para atender. O link é o MESMO de `human_handoff.
        # _montar_dossie` (`link_do_whatsapp`), pelo mesmo motivo medido no
        # piloto: no celular o número clicável custa UM TOQUE.
        _linha("WhatsApp do segurado", link_do_whatsapp(telefone)),
    ])


async def _gravar(db: Any, *, company_id: str, fp: str, descricao: str,
                  provider: Optional[str]) -> Dict[str, Any]:
    """O upsert por fingerprint. A FORMA é a de `factory.registrar_lacuna`."""
    from app.services.o_fim_do_atendimento import _cliente, _executar

    cli = _cliente(db)
    achado = await _executar(cli.table("capability_gaps")
                             .select("id, frequency_count")
                             .eq("fingerprint", fp).limit(1))
    linhas = list(getattr(achado, "data", None) or [])
    if linhas:
        atual = linhas[0]
        vezes = int(atual.get("frequency_count") or 1) + 1
        from datetime import datetime, timezone

        await _executar(cli.table("capability_gaps").update({
            "frequency_count": vezes,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", atual["id"]))
        return {"gravou": True, "nova": False, "id": atual["id"], "vezes": vezes}

    try:
        novo = await _executar(cli.table("capability_gaps").insert({
            # ⚠️ PROCEDÊNCIA, não dono: a primeira corretora que esbarrou na falta.
            "company_id": str(company_id or "") or None,
            "gap_type": TIPO_DA_LACUNA,
            "capability_key": CAPABILITY_DE_COBERTURA,
            "provider": provider,
            "description_redacted": descricao,
            "fingerprint": fp,
            "status": "open",
        }))
    except Exception as exc:  # noqa: BLE001
        # 🔴 CONSERTO P3 — A CORRIDA. Dois workers perguntam ao mesmo tempo, os
        # dois leem "não existe", os dois inserem: um ganha e o outro toma
        # `capability_gaps_fingerprint_uk`. Sem este ramo, o perdedor virava
        # `erro_ao_gravar` e a frequência ficava em 1 — a lacuna perguntada duas
        # vezes contava uma, que é exatamente o número que o painel usa para
        # priorizar.
        #
        # ⚠️ Relê e incrementa em vez de `ON CONFLICT`: o cliente aqui é o
        # PostgREST, que não expõe `ON CONFLICT ... DO UPDATE` com incremento.
        # A releitura é barata (índice único) e acontece só na corrida.
        if "fingerprint" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise
        logger.info("[LACUNA] corrida no fingerprint — releio e incremento")
        de_novo = await _executar(cli.table("capability_gaps")
                                  .select("id, frequency_count")
                                  .eq("fingerprint", fp).limit(1))
        linhas2 = list(getattr(de_novo, "data", None) or [])
        if not linhas2:
            raise
        atual2 = linhas2[0]
        vezes2 = int(atual2.get("frequency_count") or 1) + 1
        from datetime import datetime as _dt, timezone as _tz

        await _executar(cli.table("capability_gaps").update({
            "frequency_count": vezes2,
            "last_seen_at": _dt.now(_tz.utc).isoformat(),
        }).eq("id", atual2["id"]))
        return {"gravou": True, "nova": False, "id": atual2["id"], "vezes": vezes2}
    dados = list(getattr(novo, "data", None) or [{}])
    return {"gravou": True, "nova": True, "id": dados[0].get("id"), "vezes": 1}


def chave_do_marcador(fp: str, conversation_id: str = "") -> str:
    """A chave do teto de aviso. **PURA.**

    🔴 **D-E00151-03 — A PROMESSA TEM DONO** (decisão do gerente, 19/09/2026).

    O teto da emenda E1 era *1 aviso por lacuna por corretora por dia*. 📊 O
    efeito: o SEGUNDO segurado do dia com a mesma dúvida ouvia *"assim que eu
    tiver a confirmação, te respondo"* e **ninguém era avisado**. Promessa sem
    dono é pior que resposta seca — o cliente fica esperando alguém que não
    existe.

    A chave passa a incluir a CONVERSA quando ela existe: *1 aviso por lacuna
    por CONVERSA por dia*. O mesmo cliente perguntando de novo não repete o 🆘;
    outro cliente, a quem também se prometeu, gera o aviso dele.

    ⚠️ E a inundação continua limitada — não pelo relógio, mas pelo número de
    pessoas a quem o produto PROMETEU uma resposta. Cada uma delas precisa de um
    humano; é essa a conta (88 × manter o E1 puro 60).

    ⛔ Sem conversa (não deveria acontecer no canal do segurado depois do B2), a
    chave volta a ser a antiga — por corretora.
    """
    conversa = str(conversation_id or "").strip()
    return ("lacuna:%s:%s" % (fp, conversa)) if conversa else ("lacuna:%s" % fp)


async def _devolver_a_vez(company_id: str, fp: str,
                          conversation_id: str = "") -> None:
    """Libera o marcador de 24 h desta lacuna. **Nunca levanta** (CONSERTO B3)."""
    try:
        from app.services.o_grupo_so_o_que_importa import (
            TIPO_PEDIDO_DE_AJUDA, devolver_a_vez_do_grupo,
        )

        await devolver_a_vez_do_grupo(
            company_id, chave_do_marcador(fp, conversation_id),
            TIPO_PEDIDO_DE_AJUDA)
    except Exception as exc:  # noqa: BLE001
        logger.error("[LACUNA] marcador não devolvido (%s) — esta lacuna fica "
                     "muda por 24 h", type(exc).__name__)


async def registrar_lacuna(
    *,
    db: Any,
    company_id: str,
    canal: str,
    cobertura: Optional[Dict[str, Any]],
    pergunta: Any = "",
    conversation_id: str = "",
    telefone: str = "",
    enviar: Any = None,
    agora: Any = None,
) -> Dict[str, Any]:
    """Grava a lacuna e, quando for o caso, avisa o humano. **Nunca levanta.**

    ```
    canal='segurado'   grava  +  avisa (com a guarda da 001.3 e o teto de 24 h)
    canal='corretor'   grava  ·  NÃO avisa
    ```

    `enviar` existe para o guarda: é a porta do grupo, injetável por DUBLÊ.
    ⛔ Nenhum teste manda mensagem de verdade.
    """
    resposta = {"gravou": False, "nova": False, "avisou": False, "motivo": ""}
    cob = cobertura if isinstance(cobertura, dict) else {}
    estado = str(cob.get("estado") or "")
    if estado not in ESTADOS_QUE_VIRAM_LACUNA:
        # ⛔ `fonte_indisponivel` e o fallback não são falta de dado.
        resposta["motivo"] = "estado_nao_vira_lacuna:%s" % (estado or "sem_estado")
        return resposta

    try:
        fp = fingerprint_da_lacuna(cob)
        descricao = descricao_da_lacuna(cob)
        gravado = await _gravar(db, company_id=company_id, fp=fp, descricao=descricao,
                                provider=(str(cob.get("insurer_key") or "") or None))
        resposta.update(gravado)
    except Exception as exc:  # noqa: BLE001
        # 🔴 ERROR, não warning: uma lacuna que não entra é uma destilação que
        # não acontece. ⛔ E a resposta ao cliente segue intacta.
        logger.error("[LACUNA] não gravada (%s)", type(exc).__name__)
        resposta["motivo"] = "erro_ao_gravar:%s" % type(exc).__name__

    if str(canal or "") != "segurado":
        # 🔴 Emenda E1: no chat do corretor, quem precisa saber já está lendo.
        resposta["motivo"] = resposta["motivo"] or "canal_do_corretor_nao_avisa"
        return resposta

    if str(cob.get("intencao") or "pergunta") != "pergunta":
        # 🔴 RODADA 2 (N1-b) — UM PEDIDO NÃO INTERROMPE NINGUÉM.
        #
        # 📊 "preciso de guincho" faz `servico_canonico` devolver `guincho`, e
        # com 0 linhas publicadas o veredito é `nao_sabemos_ainda`. O 🆘 saía
        # dizendo *"O cliente perguntou: preciso de guincho"* e *"Eu não afirmei
        # nada: disse que ia confirmar"* — as duas frases FALSAS: ele não
        # perguntou, e o agente não prometeu confirmação nenhuma.
        #
        # ⚠️ A lacuna CONTINUA gravada (acima): "dez clientes pediram guincho na
        # HDI e não temos linha" é a informação mais útil do painel. O que não
        # acontece é a interrupção.
        resposta["motivo"] = resposta["motivo"] or "pedido_de_servico_nao_avisa"
        return resposta

    try:
        from app.services.o_grupo_so_o_que_importa import (
            TIPO_PEDIDO_DE_AJUDA, reivindicar_o_envio,
        )

        # 🔴 O TETO DE 24 h — no MESMO mecanismo que a porta já usa (§7.5 da
        # 001.3), só que a chave é a LACUNA, não a conversa: a mesma falta,
        # perguntada por dois segurados da mesma corretora no mesmo dia, avisa
        # UMA vez. ⚠️ `reivindicar_o_envio` devolve True quando JÁ avisaram.
        if await reivindicar_o_envio(company_id,
                                     chave_do_marcador(fp, conversation_id),
                                     TIPO_PEDIDO_DE_AJUDA, JANELA_DO_AVISO_S):
            resposta["motivo"] = "ja_avisei_esta_lacuna_hoje"
            return resposta

        pergunta_redigida = _redigir(pergunta)
        texto = _texto_do_aviso(cob, pergunta_redigida, str(telefone or ""))
        porta = enviar
        if porta is None:
            from app.services.o_grupo_so_o_que_importa import enviar_ao_grupo

            porta = enviar_ao_grupo
        saida = await porta(
            db, company_id=company_id, tipo=TIPO_PEDIDO_DE_AJUDA, texto=texto,
            conversation_id=str(conversation_id or ""), telefone=str(telefone or ""),
            motivo="lacuna de cobertura", motivo_classe="lacuna_de_cobertura",
            agora=agora)
        saida = saida if isinstance(saida, dict) else {}
        resposta["avisou"] = bool(saida.get("enviado"))
        resposta["motivo"] = str(saida.get("motivo") or "") or resposta["motivo"]
        if not saida.get("enviado") and not saida.get("calado"):
            # 🔴 CONSERTO B3 — O MARCADOR NÃO PODE QUEIMAR NUMA FALHA DE ENVIO.
            #
            # 📊 Medido pelo juiz em 19/09/2026, com a porta devolvendo
            # `enviado=False (Timeout)`: a 1ª pergunta não avisava (o envio
            # falhou) e a 2ª respondia `ja_avisei_esta_lacuna_hoje` — o marcador
            # já estava de pé. O dia inteiro fechava com **zero** avisos, e o
            # sintoma era indistinguível de "ninguém perguntou".
            #
            # ⚠️ A distinção importa: `calado=True` é a guarda funcionando (o
            # humano já está na conversa) e o marcador FICA — avisar de novo seria
            # o ruído que a 001.3 matou. `enviado=False` sem `calado` é FALHA, e
            # falha não consome a cota do dia. É a mesma devolução que a própria
            # porta faz com o marcador DELA (`o_grupo_so_o_que_importa.py:~700`).
            await _devolver_a_vez(company_id, fp, conversation_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[LACUNA] aviso não saiu (%s)", type(exc).__name__)
        resposta["motivo"] = "erro_ao_avisar:%s" % type(exc).__name__
        await _devolver_a_vez(company_id, fp, conversation_id)
    return resposta
