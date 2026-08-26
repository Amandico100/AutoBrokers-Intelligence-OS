# -*- coding: utf-8 -*-
"""*"O que aconteceu ontem, o que falhou, e o que eu conserto hoje?"* — SPEC-090.

> **Terça de manhã. O Founder abre o chat e escreve: "o que aconteceu ontem?" —
> e recebe: quantos atendimentos, quantos travaram, em que telas, quem
> destravou, quanto tempo, e o que a Regina anotou.**

⛔ **É UMA LEITURA, NÃO UM MOTOR.** Nada aqui decide, agenda, envia ou grava
estado de negócio. Quem grava o travamento é `dispatch_router` (SPEC-093); quem
grava a tela cega é `tela_cega` (SPEC-087); quem grava a nota é o webhook. Este
módulo **só junta e conta** — e é por isso que ele é um arquivo só e não uma
pasta: `CLAUDE.md` §5.

Três perguntas, três blocos:

```
A  de qual conversa este acionamento nasceu?     `decidir_conversa_do_run`
B  como foi a trajetória de cada travamento?     `trajetoria_dos_travamentos`
D  o que aconteceu ontem, em números?            `o_que_aconteceu_ontem`
```

🔴 **E as três respeitam a mesma regra:** o que não dá para provar vira NULO ou
zero — nunca um palpite. Um relatório confiante e falso é pior que um vazio,
porque ninguém revisa um número que parece certo.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# BLOCO A · a chave de junção
# =============================================================================

#: Os workflows que NASCEM de uma conversa.
#:
#: ⛔ Os jobs de inteligência não entram: 📊 medido em 26/08, **2.774 de 2.778**
#: `work_runs` são deles (`intelligence.detect_signals` e companhia), e eles não
#: nascem de conversa nenhuma. Ligá-los seria inventar uma origem.
WORKFLOWS_COM_CONVERSA: Tuple[str, ...] = ("acionamento.seguradora",)

#: `case_id` nasce como `wa-<telefone>` — 📊 medido: `source_id = 'wa-554788087…'`.
#:
#: ⚠️ **As âncoras dos dois lados não são decoração.** Sem `^` e `$`, um
#: identificador com dígitos no meio viraria "telefone" — é literalmente a P-262,
#: onde um padrão sem fronteira comeu dígitos dentro de um sha256 e corrompeu uma
#: linha de produção.
_TELEFONE_DO_CASO = re.compile(r"^wa-(\d{10,15})$", re.I)


def telefone_do_caso(case_id: Any) -> str:
    """O telefone dentro do `case_id`, ou `""` — e ele **não adivinha**."""
    m = _TELEFONE_DO_CASO.match(str(case_id or "").strip())
    return m.group(1) if m else ""


#: Os motivos pelos quais um run fica SEM conversa. Cada um é reportado
#: separadamente, porque eles pedem consertos diferentes.
SEM_TELEFONE = "sem telefone no case_id"
SEM_CONVERSA = "nenhuma conversa desta corretora com este telefone"
AMBIGUA = "AMBÍGUA: mais de uma conversa viva na hora do run"
LIGADA = "ligada"


def decidir_conversa_do_run(
    candidatas: Sequence[Dict[str, Any]],
    nascimento_do_run: str,
) -> Tuple[Optional[str], str]:
    """Qual conversa gerou este run — **ou `None`, com o motivo**.

    🔴 FUNÇÃO PURA. Recebe as candidatas já filtradas por corretora e telefone
    (o filtro do §7 é de quem chama, e a FK composta é a segunda linha), e
    devolve `(conversation_id, motivo)`.

    Ser pura é o que torna o guarda honesto: o teste roda offline, em
    microssegundos, e a mutação da regra fica **vermelha de verdade** em vez de
    depender de o banco estar de pé.

    ---------------------------------------------------------------------------
    🔴 A JANELA É UM FILTRO QUE PODE RECUSAR — NÃO UM DESEMPATE

    Uma conversa estava viva quando o run nasceu se::

        created_at <= nascimento_do_run <= last_message_at

    ✅ **Exatamente uma viva** → é ela.
    ⛔ **Zero ou duas ou mais** → `None`. Ninguém sabe, e o backfill diz isso.

    ⚠️ **"A mais recente" seria a resposta errada disfarçada de certa.** Ela
    sempre devolve alguém — inclusive quando as duas conversas estão vivas ao
    mesmo tempo, que é exatamente o caso em que a resposta não existe.

    📊 E a janela não é enfeite: medido em 26/08, os 4 acionamentos existentes
    têm DOIS candidatos cada — a conversa do agente interno (04/07 a 15/07) e a
    do Espelho (17/08 a 20/08). Só por telefone, os quatro são ambíguos e ficam
    nulos. Com a janela, **os quatro resolvem**, e a conversa de julho estava
    morta havia um mês.

    ⚠️ `last_message_at` vazio cai para `created_at`: uma conversa sem nenhuma
    mensagem viveu um instante, e um instante não cobre um run de outro dia.
    """
    nascimento = str(nascimento_do_run or "").strip()
    if not nascimento:
        # Sem a hora do run não há janela, e sem janela não há prova.
        return None, SEM_CONVERSA
    if not candidatas:
        return None, SEM_CONVERSA

    vivas: List[str] = []
    for c in candidatas:
        inicio = str(c.get("created_at") or "").strip()
        if not inicio:
            continue
        fim = str(c.get("last_message_at") or "").strip() or inicio
        # ⚠️ Comparação de texto ISO-8601 em UTC é ordenação correta — e é o
        #    formato que o PostgREST devolve. Converter para datetime aqui só
        #    acrescentaria um jeito de errar de fuso.
        if inicio <= nascimento <= fim:
            vivas.append(str(c.get("id") or ""))

    vivas = [v for v in vivas if v]
    if len(vivas) == 1:
        return vivas[0], LIGADA
    if not vivas:
        return None, SEM_CONVERSA
    return None, AMBIGUA


# =============================================================================
# BLOCO B · a trajetória do travamento
# =============================================================================

ABERTO = "travamento.aberto"
DESTRAVADO = "travamento.destravado"
EVENTOS_DO_TRAVAMENTO: Tuple[str, ...] = (ABERTO, DESTRAVADO)

#: 📊 **O evento vale mais que a coluna, e é por isso que esta leitura existe.**
#:
#: `work_runs.unblock_state` é UMA coluna: um acionamento que trava, destrava e
#: trava de novo guarda só o último valor, e as duas primeiras vezes somem. A
#: pergunta *"quantas vezes travou ontem"* não tem resposta a partir dela.
#: `work_events` guarda um par por travamento — e é dele que sai a trajetória.

#: De onde veio o número de segundos. §12.1 aplicado a número calculado: quem lê
#: o relatório precisa saber se o tempo foi MEDIDO pelo escritor ou DEDUZIDO das
#: horas dos eventos.
TEMPO_MEDIDO = "medido"          # 📊 `payload.segundos_travado`, do `travado_desde`
TEMPO_DEDUZIDO = "deduzido"      # 💭 diferença entre os `created_at` dos eventos
TEMPO_ABERTO = "ainda_travado"   # 🔴 não terminou — o número é "até agora"


def _segundos_entre(inicio: str, fim: str) -> Optional[int]:
    """Segundos entre dois ISO-8601, ou `None`. ⛔ Nunca levanta."""
    from datetime import datetime

    try:
        a = datetime.fromisoformat(str(inicio).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(fim).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
    delta = (b - a).total_seconds()
    return int(delta) if delta >= 0 else None


def trajetoria_dos_travamentos(
    eventos: Sequence[Dict[str, Any]],
    *,
    agora_iso: str = "",
    conversa_por_run: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Cada travamento com seus cinco campos — **e os que nunca destravaram**.

    🔴 FUNÇÃO PURA. Recebe as linhas de `work_events` de UMA corretora (o filtro
    do §7 é de quem chama) e devolve uma lista de travamentos, cada um com::

        rota · tela · motivo · quem destravou · quanto tempo ficou

    ---------------------------------------------------------------------------
    ⛔ O TRAVAMENTO ABERTO NÃO É UM CASO DE BORDA — É O CASO QUE IMPORTA

    A SPEC diz que o gate ③ é o mais importante do bloco, e a razão é o produto:
    **um travamento que nunca destravou é um segurado que nunca foi atendido.**

    ⚠️ Uma implementação que só emparelhasse `aberto` com `destravado` faria
    esses sumirem — e o relatório da terça-feira diria *"3 travamentos, todos
    resolvidos"* num dia em que quatro pessoas ficaram esperando. Por isso o
    `aberto` entra na lista **quando é lido**, e o `destravado` só o fecha.

    ---------------------------------------------------------------------------
    🔴 E `destravado` SEM `aberto` também entra

    ⚠️ Descartá-lo seria a mesma família de erro: some do relatório um
    travamento que existiu. Ele entra com `aberto_em = None` e
    `quem_destravou` preenchido — o que se perde é o tempo, não o fato.

    📊 Isso acontece de verdade quando a leitura é de UM DIA: o travamento
    começou 23h50 de ontem e terminou 00h10 de hoje. O par está partido pela
    janela, não pelo produto.

    ---------------------------------------------------------------------------
    ⚠️ `agora_iso` é PARÂMETRO, não `datetime.now()`

    Quem chama passa a hora. Sem isso o teste do travamento aberto mediria uma
    duração que muda a cada rodada, e um guarda que não consegue repetir o
    próprio número não é guarda.

    ⚠️ E `conversa_por_run` também é parâmetro, pelo mesmo tipo de motivo:
    📊 `work_events` **não tem** coluna de conversa (12 colunas, medidas). Quem
    sabe é `work_runs.conversation_id`, que o BLOCO A acabou de criar. ⛔ Ler
    `e.get("conversation_id")` aqui devolveria `None` sempre — um campo que
    nasce vazio e parece que só não foi preenchido ainda.
    """
    mapa = conversa_por_run or {}
    por_run: Dict[str, List[Dict[str, Any]]] = {}
    for e in eventos:
        tipo = str(e.get("event_type") or "")
        if tipo not in EVENTOS_DO_TRAVAMENTO:
            continue
        # ⚠️ Sem `work_run_id` não há como emparelhar. Cai num balde próprio por
        #    run "desconhecido" em vez de sumir — 📊 sumir é o defeito que o
        #    gate ③ existe para pegar.
        chave = str(e.get("work_run_id") or f"sem-run:{e.get('id')}")
        por_run.setdefault(chave, []).append(e)

    saida: List[Dict[str, Any]] = []
    for run_id, linhas in por_run.items():
        # 🔴 ORDENA POR `id`, NÃO POR `created_at` — e a diferença é robustez.
        #
        # 📊 `work_events.id` é `bigint` serial e os eventos são escritos ao
        # vivo por `_evento()`: dentro de um run, a ordem de inserção É a ordem
        # dos fatos. `created_at` diz o mesmo, com uma fragilidade a mais.
        #
        # ⚠️ **E a fragilidade é real, não teórica.** Um guarda desta SPEC pegou
        # na primeira rodada: com `created_at` na frente, uma hora ilegível
        # ordena por TEXTO — `"hora invalida"` começa com `h` e vai depois de
        # `"2026-…"`. O `aberto` caía atrás do `destravado`, e UM travamento
        # virava DOIS: um órfão de fechamento e um aberto que nunca fechou.
        # ⛔ Um relatório que inventa um travamento é tão ruim quanto um que
        # esconde.
        #
        # ⚠️ `created_at` continua no desempate, para o caso de a leitura vir sem
        # a coluna `id` — aí os dois lados viram 0 e a ordenação cai para a hora.
        linhas = sorted(linhas, key=lambda x: (int(x.get("id") or 0),
                                               str(x.get("created_at") or "")))
        atual: Optional[Dict[str, Any]] = None
        for e in linhas:
            carga = e.get("payload_redacted") or {}
            if not isinstance(carga, dict):
                carga = {}
            quando = str(e.get("created_at") or "")

            if str(e.get("event_type")) == ABERTO:
                # 🔴 Um `aberto` seguido de outro `aberto` sem fechamento: o
                #    primeiro NÃO some — ele fica aberto e o segundo começa.
                if atual is not None:
                    saida.append(atual)
                atual = {
                    "work_run_id": run_id if not run_id.startswith("sem-run:") else None,
                    "company_id": str(e.get("company_id") or ""),
                    "conversation_id": mapa.get(run_id) or None,
                    "rota": str(carga.get("rota") or ""),
                    "tela": str(carga.get("tela") or ""),
                    "motivo": str(carga.get("motivo") or ""),
                    "aberto_em": quando,
                    "destravado_em": None,
                    "quem_destravou": None,
                    "canal": None,
                    "segundos": None,
                    "fonte_do_tempo": None,
                    "ainda_travado": True,
                }
                continue

            # DESTRAVADO
            if atual is None:
                # ⚠️ Fechamento órfão — o par ficou partido pela janela de
                #    leitura. Entra sem tempo, nunca sumindo.
                # 🔴 AS MESMAS CHAVES DA LINHA NORMAL — sem exceção.
                #
                # ⚠️ Este ramo nascia com SEIS chaves em vez de doze, e um
                # consumidor que fizesse `t["segundos"]` levava `KeyError`
                # exatamente na linha mais rara. Pego pelo guarda do órfão na
                # primeira rodada: uma forma que só aparece na virada da
                # meia-noite é a que ninguém testa à mão.
                atual = {
                    "work_run_id": run_id if not run_id.startswith("sem-run:") else None,
                    "company_id": str(e.get("company_id") or ""),
                    "conversation_id": mapa.get(run_id) or None,
                    "rota": str(carga.get("rota") or ""),
                    "tela": str(carga.get("tela") or ""),
                    "motivo": "",
                    "aberto_em": None,
                    "destravado_em": None,
                    "quem_destravou": None,
                    "canal": None,
                    "segundos": None,
                    "fonte_do_tempo": None,
                    "ainda_travado": True,
                }
            atual["destravado_em"] = quando
            atual["quem_destravou"] = str(carga.get("por") or "robo")
            atual["canal"] = str(carga.get("canal") or "") or None
            atual["ainda_travado"] = False

            # 📊 O tempo MEDIDO pelo escritor vence o DEDUZIDO — ele sai de
            #    `travado_desde`, e os `created_at` dos eventos são a hora em que
            #    a linha foi ESCRITA, que não é a mesma coisa.
            medido = carga.get("segundos_travado")
            if isinstance(medido, (int, float)) and medido >= 0:
                atual["segundos"] = int(medido)
                atual["fonte_do_tempo"] = TEMPO_MEDIDO
            elif atual.get("aberto_em"):
                deduzido = _segundos_entre(atual["aberto_em"], quando)
                atual["segundos"] = deduzido
                atual["fonte_do_tempo"] = TEMPO_DEDUZIDO if deduzido is not None else None
            saida.append(atual)
            atual = None

        if atual is not None:
            # 🔴 AINDA TRAVADO. Este é o gate ③.
            if agora_iso and atual.get("aberto_em"):
                atual["segundos"] = _segundos_entre(atual["aberto_em"], agora_iso)
                atual["fonte_do_tempo"] = TEMPO_ABERTO
            saida.append(atual)

    saida.sort(key=lambda t: (str(t.get("aberto_em") or t.get("destravado_em") or ""),
                              str(t.get("work_run_id") or "")))
    return saida


def as_rotas_que_mais_travam(trajetoria: Sequence[Dict[str, Any]],
                             ) -> List[Dict[str, Any]]:
    """🔴 A lista de conserto do dia seguinte, ordenada pela dor.

    ⚠️ **A ordem é por travamentos ABERTOS primeiro, depois pelo total.** Uma
    rota que trava 10 vezes e destrava sozinha nas 10 dói menos que uma que
    trava 3 e deixa as 3 pessoas esperando — e uma lista ordenada só pelo total
    manda consertar a errada.
    """
    contas: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for t in trajetoria:
        chave = (str(t.get("rota") or ""), str(t.get("tela") or ""))
        c = contas.setdefault(chave, {"rota": chave[0], "tela": chave[1],
                                      "travou": 0, "sem_destravar": 0})
        c["travou"] += 1
        if t.get("ainda_travado"):
            c["sem_destravar"] += 1
    return sorted(contas.values(),
                  key=lambda c: (-c["sem_destravar"], -c["travou"], c["rota"]))


def resumo_dos_travamentos(trajetoria: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Os números do dia — **e o tempo mediano só conta quem terminou**.

    ⚠️ Misturar os segundos de um travamento ABERTO na mediana estragaria os
    dois números: o aberto ainda está contando, então ele sobe sozinho a cada
    hora que passa, e um relatório de terça-feira sobre segunda-feira daria uma
    mediana diferente a cada vez que fosse aberto.

    🔴 Por isso os abertos são contados à parte, com o tempo deles marcado
    `ainda_travado`. Eles são o número que importa, não o que se dilui.
    """
    fechados = [t for t in trajetoria if not t.get("ainda_travado")]
    abertos = [t for t in trajetoria if t.get("ainda_travado")]

    tempos = sorted(int(t["segundos"]) for t in fechados
                    if isinstance(t.get("segundos"), int))
    mediana: Optional[int] = None
    if tempos:
        meio = len(tempos) // 2
        mediana = (tempos[meio] if len(tempos) % 2
                   else (tempos[meio - 1] + tempos[meio]) // 2)

    quem: Dict[str, int] = {}
    for t in fechados:
        por = str(t.get("quem_destravou") or "robo")
        quem[por] = quem.get(por, 0) + 1

    # 📊 §12.1 aplicado a número calculado: quantos dos tempos vieram MEDIDOS do
    #    escritor e quantos foram DEDUZIDOS das horas dos eventos. Sem isto, uma
    #    mediana de tempos deduzidos parece tão firme quanto uma de medidos.
    fontes: Dict[str, int] = {}
    for t in fechados:
        f = str(t.get("fonte_do_tempo") or "sem_tempo")
        fontes[f] = fontes.get(f, 0) + 1

    return {
        "travamentos": len(trajetoria),
        "destravados": len(fechados),
        "ainda_travados": len(abertos),
        "segundos_mediano": mediana,
        "tempos_considerados": len(tempos),
        "fontes_do_tempo": fontes,
        "quem_destravou": quem,
        "rotas": as_rotas_que_mais_travam(trajetoria)[:3],
    }
