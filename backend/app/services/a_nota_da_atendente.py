# -*- coding: utf-8 -*-
"""A anotação das atendentes entra no produto — SPEC-090, BLOCO C.

> *"Enquanto os agentes vão atendendo e os humanos acompanhando no WhatsApp, a
> Central e um chat do Claude Code vão analisar todos os atendimentos […] **e as
> anotações das atendentes humanas**."* — o Founder

🔴 **É o bloco que decide se o piloto vira conserto ou vira conversa de WhatsApp
perdida.** Sem porta, o que as duas observarem no primeiro dia se perde.

===============================================================================
🔴 O QUE A MEDIÇÃO DERRUBOU DO DESENHO DA SPEC
===============================================================================

A SPEC manda a atendente escrever `#nota …` **na conversa do segurado**, e
promete que *"o prefixo é consumido: a mensagem é capturada, gravada e não
reenviada"*. O gate ② dela é *"🔴 ZERO chance de o `#nota` chegar ao segurado"*.

📊 **Medido em 26/08 — nesse caminho, esse gate é inalcançável:**

```
evolution_go_events.py:47   force_from_me = ev in ("sendmessage", "send.message")
evolution_inbound.py:847    if from_me: return {**out, "skip": True,
                                                "skip_reason": "from_me"}
```

⛔ **`fromMe` é o ECO de uma mensagem que o WhatsApp JÁ ENTREGOU.** Quando o
webhook chega, o segurado já leu. O produto não é o remetente, não está no
caminho, e não tem o que consumir — *"não reenviar"* é verdade e é irrelevante,
porque ninguém ia reenviar.

⚠️ A SPEC trata isso como o risco *"se o prefixo escapar uma vez"*. **Não é
risco: é o comportamento padrão desse caminho.**

===============================================================================
✅ ONDE O GATE ② É REAL — e é onde a nota deve ser escrita
===============================================================================

📊 `POST /api/webhook/send-message` (`webhook.py:1475`) é o envio do **painel**,
e ali o produto **É o remetente**: ele chama `whatsapp_service.send_message`.
Interceptar ali é interceptação de verdade — e o teste consegue contar
`platform_sends`, como o gate ② exige.

Então o bloco tem **dois caminhos, e eles são honestamente diferentes**:

```
PAINEL     `#nota …`  →  grava · ⛔ NÃO envia          origem='painel'
           outra coisa →  o caminho de hoje, intocado

WHATSAPP   `#nota …`  →  grava · ⛔ NÃO pausa a IA     origem='whatsapp'
                          ⚠️ e a linha DIZ que já foi entregue
           outra coisa →  o caminho de hoje: PAUSA    (a linha de controle)
```

🔴 **A coluna `origem` é o que impede o relatório confiante e falso.** Sem ela,
as duas notas ficariam indistinguíveis e o resumo diria *"12 notas capturadas,
nenhuma vazou"* sobre um dia em que sete foram lidas pelo segurado.

===============================================================================
⚠️ E A NOTA NÃO PODE PAUSAR O ROBÔ — o ponto que quase passou
===============================================================================

📊 [webhook.py:1247+](../api/webhook.py): desde 14/08, **QUALQUER `fromMe`
humano pausa a IA**, e a regra está certa — antes dela a atendente respondia por
áudio e o agente falava por cima, *"duas vozes na mesma conversa"*.

⛔ **Mas ela transformaria toda anotação em intervenção.** Anotar viraria
assumir, que é exatamente o que o Founder mandou não fazer.

⚠️ **E a estreiteza é o guarda:** o prefixo tem de estar no **começo**. *"o robô
errou #nota"* **não** é nota — é intervenção, e pausa. Uma exceção larga vira o
buraco que a regra de 14/08 fechou.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: O prefixo combinado. ⛔ Só vale no **começo absoluto** da mensagem.
PREFIXO = "#nota"

#: 🔴 SEM `\s*` ANTES DO `#`, E ISSO É O GUARDA INTEIRO.
#:
#: ⚠️ `^` casa o começo da string. Um espaço antes já derruba, e é assim que a
#: SPEC pede: *"o prefixo tem de estar no começo da mensagem, sem espaço antes"*.
#: ⛔ `"o robô errou #nota"` não casa — é intervenção, e pausa a IA.
#:
#: ⚠️ **Insensível a maiúscula, e isso não é frouxidão.** 📊 Teclado de celular
#: capitaliza a primeira letra: a Regina digita `#nota` e sai `#Nota`. Com a
#: regra sensível, a nota dela vira INTERVENÇÃO — pausa o robô **e** vai para o
#: segurado. ⛔ Errar para o lado estrito custa as duas coisas de uma vez.
#:
#: ⚠️ E exige separador depois: `#notas` é outra palavra, não este prefixo.
_PREFIXO_NO_COMECO = re.compile(r"^#nota(?=[\s:,\-–—]|$)", re.I)

#: O que sobra depois do prefixo e da pontuação de separação.
_SO_A_NOTA = re.compile(r"^#nota[\s:,\-–—]*", re.I)

#: 📊 As notas são frases curtas de gente com pressa. O teto existe para o dia
#: em que alguém colar uma tela inteira depois do prefixo.
TETO_DO_TEXTO = 2000

ORIGEM_PAINEL = "painel"      # ⛔ o produto interceptou — NUNCA saiu
ORIGEM_WHATSAPP = "whatsapp"  # ⚠️ já entregue quando o produto soube
ORIGENS = (ORIGEM_PAINEL, ORIGEM_WHATSAPP)


def e_nota(texto: Any) -> bool:
    """A mensagem é uma anotação? **PURA, e propositalmente estreita.**

    ⛔ Só `True` quando o prefixo abre a mensagem. Tudo mais segue o caminho de
    hoje — incluindo pausar a IA, que é o comportamento certo para intervenção.
    """
    return bool(_PREFIXO_NO_COMECO.match(str(texto or "")))


def texto_da_nota(texto: Any) -> str:
    """O que ela escreveu, sem o prefixo. `""` quando não é nota **ou quando só
    veio o prefixo** — 📊 e o banco também recusa texto vazio (CHECK)."""
    bruto = str(texto or "")
    if not e_nota(bruto):
        return ""
    return _SO_A_NOTA.sub("", bruto, count=1).strip()[:TETO_DO_TEXTO]


def _mascarar(texto: str) -> Optional[str]:
    """A nota mascarada, ou `None` se o mascarador não estiver de pé.

    🔴 **O mascarador é o ÚNICO da casa** — `redaction_service.mascara_de_tela`,
    a cascata `templatize → redigir` da SPEC-087. ⛔ Escrever um segundo aqui
    seria criar a lista que fica para trás, e a que fica para trás é justamente
    a que deixa passar o CPF (`CLAUDE.md` §5).

    ⚠️ **E a degradação é FECHADA:** sem mascarador, a nota **não é gravada**.
    Uma nota perdida é um incômodo que a Regina reescreve; uma placa crua numa
    tabela nova não se desfaz. 📊 O risco é baixo: `redaction_service` importa
    só `re`, e a cascata já cai sozinha para `redigir` quando o `templatize`
    falha.
    """
    try:
        from app.services.intelligence.redaction_service import mascara_de_tela
    except Exception as erro:  # noqa: BLE001
        logger.error("[NOTA] mascarador fora do ar (%s) — a nota NÃO foi "
                     "gravada. Degradação fechada: nota perdida é incômodo, "
                     "placa crua em tabela nova não se desfaz.",
                     type(erro).__name__)
        return None
    try:
        return mascara_de_tela(texto)
    except Exception as erro:  # noqa: BLE001
        logger.error("[NOTA] máscara falhou (%s) — a nota NÃO foi gravada",
                     type(erro).__name__)
        return None


def linha_da_nota(*, company_id: str, texto_bruto: str, origem: str,
                  conversation_id: Optional[str] = None,
                  work_run_id: Optional[str] = None,
                  autor_telefone: str = "",
                  rota: str = "", tela: str = "") -> Optional[Dict[str, Any]]:
    """A linha pronta para `notas_da_atendente`, ou `None`. **PURA**, tirando a
    máscara — que é a mesma função do resto da casa.

    ⛔ Devolve `None` quando não é nota, quando o texto fica vazio, quando o
    mascarador cai ou quando a origem é inválida. **Nada é gravado por engano.**
    """
    if origem not in ORIGENS:
        # ⚠️ O banco também recusa (CHECK), mas recusar aqui evita um INSERT
        #    que estoura no meio de um webhook.
        logger.error("[NOTA] origem %r não é uma das %s — nota descartada",
                     origem, ORIGENS)
        return None
    corpo = texto_da_nota(texto_bruto)
    if not corpo:
        return None
    mascarado = _mascarar(corpo)
    if not mascarado or not mascarado.strip():
        return None
    return {
        "company_id": str(company_id),
        "conversation_id": str(conversation_id) if conversation_id else None,
        "work_run_id": str(work_run_id) if work_run_id else None,
        "texto": mascarado[:TETO_DO_TEXTO],
        "autor_telefone": str(autor_telefone or "") or None,
        "origem": origem,
        "rota": str(rota or "")[:180] or None,
        "tela": str(tela or "")[:180] or None,
    }


async def gravar_nota(db, **campos: Any) -> Tuple[bool, str]:
    """Grava a nota. Devolve `(gravou, motivo)` — e **nunca levanta**.

    ⛔ Uma exceção aqui subiria pelo webhook e derrubaria o tratamento da
    mensagem inteira. A nota é o item menos crítico do caminho; ela não pode
    ser quem quebra o atendimento.
    """
    linha = linha_da_nota(**campos)
    if linha is None:
        return False, "nao_e_nota_ou_mascarador_fora"
    try:
        # 🔴 `company_id` está DENTRO da linha — §7. O backend usa service role,
        #    então a RLS não segura nada; quem segura é este campo.
        await db.client.table("notas_da_atendente").insert(linha).execute()
    except Exception as erro:  # noqa: BLE001
        # ⛔ NUNCA loga o texto nem o telefone — só o veredito.
        logger.warning("[NOTA] não gravada (%s) origem=%s",
                       type(erro).__name__, linha.get("origem"))
        return False, type(erro).__name__
    logger.info("[NOTA] anotação registrada origem=%s conversa=%s",
                linha["origem"], str(linha.get("conversation_id") or "-")[:8])

    # 🔴 SPEC-093-B BLOCO B — a anotação vira evento da sombra, SEM o texto.
    #
    # 📊 §1.4: `notas_da_atendente` tem 0 linhas e nenhuma tela a lê depois de
    # gravada. O que a sombra guarda não é a nota — é que ela EXISTIU, por onde
    # entrou e se trazia número. O conteúdo continua onde já estava.
    #
    # ⛔ `tem_numero` sai do texto CRU (`campos`), não da linha: o mascarador já
    # trocou os dígitos por marca, e perguntar ao texto mascarado devolveria
    # sempre `False` — um campo que mente por construção.
    #
    # =====================================================================
    # 🔴 E SÓ PELO WHATSAPP. A NOTA DO PAINEL JÁ TEM ESCRITOR — É O NEXT.
    # =====================================================================
    #
    # 📊 Achado pelo red team desta rodada: a nota escrita no PAINEL percorre
    # DOIS caminhos que gravam o MESMO evento.
    #
    #   1. `app/api/dashboard/conversas/[id]/route.ts:396` chama
    #      `registrarEventoDaSombra(… 'claims.nota_registrada' …)`;
    #   2. o mesmo `route.ts` chama `POST /api/admin/send-message`, que cai em
    #      `webhook._consumir_anotacao_do_painel` → `gravar_nota` → aqui.
    #
    # Resultado: DUAS linhas em `work_events` para UMA anotação. A trajetória
    # ganha um passo que ninguém deu, a assinatura da variante muda, e o
    # contador "com nota da atendente" continua certo por acaso (ele testa
    # presença, não contagem) enquanto a VARIANTE — o produto do BLOCO C —
    # descreve um processo que não existe. ⛔ Um evento duplicado não trava
    # nada: ele mente em silêncio (CLAUDE.md §9.5).
    #
    # ⚠️ O lado que fica é o do Next, e não este, por uma razão medida: só o
    # `route.ts` sabe que a origem é o painel de verdade. Aqui a origem chega
    # como parâmetro — e um parâmetro errado voltaria a duplicar.
    if linha.get("origem") == ORIGEM_WHATSAPP:
        try:
            from app.services.claims_shadow import registrar_gesto, tem_numero

            await registrar_gesto(
                db, company_id=linha["company_id"],
                conversation_id=linha.get("conversation_id"),
                event_type="claims.nota_registrada",
                # 🔴 `tem_numero` é a MESMA regra dos dois lados (`\d{6,}`), e
                # mora em `claims_shadow` para que só exista uma.
                payload={"origem": ORIGEM_WHATSAPP,
                         "tem_numero": tem_numero(campos.get("texto"))},
            )
        except Exception as erro:  # noqa: BLE001
            logger.warning("[SOMBRA] nota não registrada na sombra (%s)",
                           type(erro).__name__)
    return True, "gravada"


async def travamento_mais_recente(db, company_id: str,
                                  conversation_id: Optional[str]
                                  ) -> Dict[str, str]:
    """A rota e a tela do último travamento — *"ligada ao travamento mais
    recente"*, como a SPEC pede. Devolve `{}` quando não há.

    ⛔ **Nunca levanta e nunca inventa.** Sem travamento, a nota é gravada sem
    rota e sem tela — que é a verdade sobre ela.
    """
    if not company_id:
        return {}
    try:
        consulta = (db.client.table("work_events")
                    .select("work_run_id, payload_redacted, created_at")
                    .eq("company_id", str(company_id))   # 🔴 §7
                    .eq("event_type", "travamento.aberto")
                    .order("created_at", desc=True).limit(1))
        achado = await consulta.execute()
    except Exception as erro:  # noqa: BLE001
        logger.warning("[NOTA] travamento recente não consultado (%s)",
                       type(erro).__name__)
        return {}
    linhas = achado.data or []
    if not linhas:
        return {}
    carga = linhas[0].get("payload_redacted") or {}
    if not isinstance(carga, dict):
        return {}
    return {
        "work_run_id": str(linhas[0].get("work_run_id") or "") or "",
        "rota": str(carga.get("rota") or ""),
        "tela": str(carga.get("tela") or ""),
    }
