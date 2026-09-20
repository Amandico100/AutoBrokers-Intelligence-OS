# -*- coding: utf-8 -*-
"""📊 A MEDIÇÃO DIÁRIA DO PILOTO — SPEC-EXTRA-001.7, unidades B e C.

O Founder roda UM comando e recebe, por **dia × corretora**, os números do
piloto; e, no agregado do período, a **nota 0–100 de cada dimensão** do §0 do
diagnóstico — ou ``NÃO AVALIADA`` com o motivo escrito.

```
cd backend
PYTHONIOENCODING=utf-8 python scripts/medir_o_piloto.py \
    --de 2026-09-08 --ate 2026-09-20 --formato markdown --saida ../docs/.../X.md
```

🔴 **A MEDIÇÃO CHAMA O MOTOR** (CLAUDE.md §5 e §9.4). Nada aqui reconta o que o
produto já conta:

```
contagens_do_dia      os MESMOS números que a corretora lê às 19h
eficiencia_do_dia     a fórmula de D-PILOTO-13, com `None` no denominador zero
classe_do_silencio    a classe do motivo, aplicada ao `detail` EM MEMÓRIA
e_origem_humana       quem escreveu a linha: teclado da corretora ou robô
TITULO_HANDOFF_*      as constantes de quem ESCREVE o handoff no feed
fuso_da_corretora     o dia é o dia LOCAL, a mesma conta de `montar_o_resumo`
ler_paginado_async    o PostgREST corta em 1000 linhas em silêncio
```

Um contador próprio aqui mediria o contador próprio, e dois contadores
divergindo sobre o mesmo dia seriam, eles mesmos, o defeito. O guarda
``reconcilia_com_o_motor`` prova a identidade.

⛔ **SOMENTE SELECT.** Nada é escrito, nada é enviado, nenhum modelo é chamado.

⛔ **ZERO PII.** A saída é só CONTAGEM. `phone`, `summary`, `content`,
`user_name`, `ficha_atendimento` e `detail` nunca são selecionados — e `detail`,
que é lido para o motor classificar o silêncio, morre em memória: sai dele
apenas a CLASSE.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# --------------------------------------------------------------------------- #
# 🔴 O MOTOR — importado, nunca reimplementado
# --------------------------------------------------------------------------- #
from app.agents.tools.human_handoff import (  # noqa: E402
    TITULO_HANDOFF_ENTREGUE,
    TITULO_HANDOFF_FALHOU,
)
from app.leitura_completa import ler_paginado_async  # noqa: E402
from app.services.o_fim_do_atendimento import (  # noqa: E402
    MOTIVOS,
    MOTIVOS_DE_SUCESSO,
    classe_do_silencio,
    e_origem_humana,
)
from app.services.o_grupo_so_o_que_importa import (  # noqa: E402
    TIPO_COBRANCA,
    TIPO_CONCLUSAO,
    TIPO_ESPERA_VENCIDA,
    TIPO_PAUSA_HUMANA,
    TIPO_PEDIDO_DE_AJUDA,
    TIPO_QUEDA_DE_CANAL,
    TIPO_RESUMO_DIARIO,
    TIPO_RETOMADA,
    TIPO_SINISTRO,
    TIPO_VIGIA,
)
from app.services.os_modelos_do_grupo import (  # noqa: E402
    LIMITE_DE_DESCONHECIDOS,
    contagens_do_dia,
    eficiencia_do_dia,
)
from app.services.platform_outbound import fuso_da_corretora  # noqa: E402

# --------------------------------------------------------------------------- #
# As constantes que DECIDEM, cada uma com o porquê ao lado (CLAUDE.md §9.5)
# --------------------------------------------------------------------------- #

#: As corretoras do piloto, por `companies.company_name`. O id é resolvido por
#: SELECT — 🔴 um id escrito aqui envelheceria em silêncio.
CORRETORAS_PADRAO: Tuple[str, ...] = ("Resulta Seguros", "AutoFleet")

#: 🔴 O dia em que `payload.origem='agente'` passou a existir (EXTRA-001.2,
#: 14/09/2026). ⚠️ ANTES disto a resposta do agente era gravada **sem payload**
#: e é indistinguível de uma resposta sem marca: a métrica "conversas atendidas
#: pelo agente" é **NÃO MENSURÁVEL** nesses dias — e isso não é zero. Publicar
#: zero seria afirmar que o agente não falou, quando o que se sabe é que o
#: produto não anotava quem falou.
PRIMEIRO_DIA_COM_ORIGEM_DO_AGENTE = date(2026, 9, 14)

#: A marca que o agente deixa hoje em `messages.payload`.
ORIGEM_DO_AGENTE = "agente"

#: 📊 O título que `o_fim_do_atendimento.anotar_silencio_no_feed` grava
#: (`:1768`) e a categoria do feed (`:1772`). ⚠️ Eles são LITERAIS no produto —
#: não há constante a importar — e por isso o guarda
#: `o_titulo_do_silencio_e_o_do_produto` casa este texto contra o código-fonte
#: do motor: uma renomeação lá que não chegue aqui fica VERMELHA.
TITULO_SILENCIO = "O agente ficou em silêncio nesta conversa"
TITULO_SILENCIO_EXCECAO = "O agente respondeu mesmo com a conversa pausada"
CATEGORIA_DO_FEED = "atendimentos"

#: `platform_sends.kind` do que SAIU para o segurado ao fim de um acionamento.
#: 🔴 `work_runs.status='completed'` **não** serve: `completed` inclui o
#: "encaminhado" — o caso que foi para a seguradora SEM protocolo. "Com
#: protocolo" é a linha de `platform_sends`, e nada mais.
KIND_PROTOCOLO = "acionamento_protocolo"
KIND_ENCAMINHAMENTO = "acionamento_encaminhamento"

#: Os dez tipos de mensagem ao grupo, importados de quem os escreve.
TIPOS_DO_GRUPO: Tuple[str, ...] = (
    TIPO_PEDIDO_DE_AJUDA, TIPO_SINISTRO, TIPO_CONCLUSAO, TIPO_ESPERA_VENCIDA,
    TIPO_VIGIA, TIPO_RESUMO_DIARIO, TIPO_QUEDA_DE_CANAL, TIPO_COBRANCA,
    TIPO_PAUSA_HUMANA, TIPO_RETOMADA,
)

#: Quantas conversas por lote no `in_` de `messages`. ⚠️ `messages` **não tem
#: `company_id`** — o isolamento (CLAUDE.md §7) vem de só perguntar pelas
#: conversas que já foram filtradas por `conversations.company_id`. Um lote
#: grande demais estoura o tamanho da URL do PostgREST.
LOTE_DE_CONVERSAS = 40

#: ≥ 2 ids de WhatsApp numa linha = a rajada foi FUNDIDA numa só.
MINIMO_DE_IDS_PARA_SER_RAJADA = 2

#: 🔴 O texto que, quando aparece na saída, é defeito de privacidade. O guarda
#: G3 roda isto sobre o JSON e o markdown inteiros.
PADROES_DE_PII: Tuple[Tuple[str, str], ...] = (
    ("telefone", r"(?<!\d)(?:\+?55)?\s?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)"),
    ("cpf", r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
    ("placa", r"(?<![A-Za-z0-9])[A-Z]{3}-?\d[A-Z0-9]\d{2}(?![A-Za-z0-9])"),
    ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
)


def procurar_pii(texto: str) -> List[Tuple[str, str]]:
    """O que, nesta saída, parece dado de pessoa. **PURA.**"""
    achados: List[Tuple[str, str]] = []
    for nome, padrao in PADROES_DE_PII:
        for casou in re.finditer(padrao, texto or ""):
            achados.append((nome, casou.group(0)))
    return achados


# =========================================================================== #
# ① LER — SELECT paginado, filtrado por `company_id`, no dia LOCAL da corretora
# =========================================================================== #

class _DB:
    """O embrulho que o motor espera (`o_fim_do_atendimento._cliente`)."""

    def __init__(self, cliente: Any) -> None:
        self.client = cliente


def limites_do_dia(dia: date, tz) -> Tuple[datetime, datetime]:
    """(início, fim) do dia LOCAL da corretora, em UTC. **PURA.**

    🔴 A mesma conta de `os_modelos_do_grupo.montar_o_resumo`: o dia do resumo
    das 19h e o dia desta medição têm de ser o MESMO dia, ou os dois números
    seriam sobre janelas diferentes com o mesmo rótulo.
    """
    inicio_local = datetime(dia.year, dia.month, dia.day, tzinfo=tz)
    return (inicio_local.astimezone(timezone.utc),
            (inicio_local + timedelta(days=1)).astimezone(timezone.utc))


async def _pagina(cliente, tabela: str, colunas: str, company_id: Optional[str],
                  inicio: datetime, fim: datetime, rotulo: str,
                  coluna_de_data: str = "created_at") -> Tuple[List[dict], bool]:
    def _consulta():
        q = cliente.table(tabela).select(colunas)
        if company_id is not None:
            q = q.eq("company_id", str(company_id))       # 🔴 CLAUDE.md §7
        return (q.gte(coluna_de_data, inicio.isoformat())
                 .lt(coluna_de_data, fim.isoformat()))

    return await ler_paginado_async(_consulta, chave_unica="id", rotulo=rotulo)


async def ler_o_dia(cliente, company_id: str, inicio: datetime,
                    fim: datetime) -> Dict[str, Any]:
    """As linhas do dia, de todas as tabelas do FIO. ⛔ Só SELECT.

    ⛔ Nenhuma coluna de conteúdo entra aqui, com UMA exceção declarada:
    `agent_activities.detail`, que o motor precisa ler para classificar o
    silêncio. Ele é consumido em memória por `medir_o_dia` e **jamais** atravessa
    para a saída — o guarda G3 mede isso sobre o texto final.
    """
    truncou = False
    leitura: Dict[str, Any] = {}

    conversas, t = await _pagina(
        cliente, "conversations",
        "id, status, resolucao_motivo, resolvido_em, updated_at, ficha_atendimento",
        company_id, inicio, fim, "piloto/conversas", coluna_de_data="updated_at")
    truncou = truncou or t
    # ⛔ A FICHA MORRE AQUI. Ela carrega nome, telefone, placa e apólice; a
    #    única coisa que a medição precisa dela é um sim/não, e é só isso que
    #    atravessa esta linha. PII nunca chega a `medir_o_dia`.
    for c_ in conversas:
        ficha = c_.get("ficha_atendimento")
        c_["apolice_confirmada"] = bool(
            (ficha or {}).get("apolice_confirmada") is True
            if isinstance(ficha, dict) else False)
        c_.pop("ficha_atendimento", None)
    leitura["conversas"] = conversas

    # `messages` NÃO tem `company_id` (🔴 §7): só se pergunta pelas conversas
    # que o filtro acima já provou serem desta corretora.
    ids = [str(c.get("id")) for c in conversas if c.get("id")]
    mensagens: List[dict] = []
    for i in range(0, len(ids), LOTE_DE_CONVERSAS):
        lote = ids[i:i + LOTE_DE_CONVERSAS]

        def _consulta(lote=lote):
            return (cliente.table("messages")
                    .select("id, conversation_id, role, payload, created_at")
                    .in_("conversation_id", lote)
                    .gte("created_at", inicio.isoformat())
                    .lt("created_at", fim.isoformat()))

        parte, t = await ler_paginado_async(_consulta, chave_unica="id",
                                            rotulo="piloto/mensagens")
        truncou = truncou or t
        mensagens.extend(parte)
    leitura["mensagens"] = mensagens

    for tabela, colunas, chave in (
            # ⛔ `platform_sends`: NUNCA `phone`, NUNCA `summary`.
            ("platform_sends", "id, kind, created_at", "envios"),
            ("work_runs", "id, runtime_kind, status, created_at", "runs"),
            ("agent_activities", "id, category, title, detail, created_at",
             "atividades"),
            ("work_events", "id, event_type, payload_redacted, created_at",
             "eventos"),
            ("conversation_logs", "id, status, response_time_ms, created_at",
             "chat"),
    ):
        linhas, t = await _pagina(cliente, tabela, colunas, company_id,
                                  inicio, fim, "piloto/" + chave)
        truncou = truncou or t
        leitura[chave] = linhas

    # 🔴 O MOTOR, com a MESMA janela. É deste dicionário que saem os números
    #    que a corretora lê às 19h.
    leitura["contagens"] = await contagens_do_dia(_DB(cliente), company_id,
                                                  inicio, fim)
    leitura["truncou"] = bool(truncou) or bool(leitura["contagens"].get("truncou"))
    return leitura


# =========================================================================== #
# ② MEDIR — só contagem, e o motor decide toda classificação
# =========================================================================== #

NAO_MENSURAVEL = "NÃO MENSURÁVEL"


def medir_o_dia(leitura: Dict[str, Any], *, dia: date) -> Dict[str, Any]:
    """As 8 métricas do dia, a partir das linhas. **PURA.**"""
    c = dict(leitura.get("contagens") or {})
    mensagens = list(leitura.get("mensagens") or [])
    atividades = list(leitura.get("atividades") or [])
    envios = list(leitura.get("envios") or [])
    runs = list(leitura.get("runs") or [])
    eventos = list(leitura.get("eventos") or [])
    conversas = list(leitura.get("conversas") or [])
    chat = list(leitura.get("chat") or [])

    # ------------------------------------------------------------- ① atendidas
    por_conversa: Dict[str, Dict[str, bool]] = {}
    for m in mensagens:
        chave = str(m.get("conversation_id") or "")
        if not chave:
            continue
        marca = por_conversa.setdefault(chave, {"agente": False, "humano": False})
        carga = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        if str((carga or {}).get("origem") or "").strip().lower() == ORIGEM_DO_AGENTE:
            marca["agente"] = True
        elif e_origem_humana(m):          # 🔴 o discriminador canônico do motor
            marca["humano"] = True
    so_agente = sum(1 for v in por_conversa.values() if v["agente"] and not v["humano"])
    so_humano = sum(1 for v in por_conversa.values() if v["humano"] and not v["agente"])
    ambos = sum(1 for v in por_conversa.values() if v["agente"] and v["humano"])
    mensuravel = dia >= PRIMEIRO_DIA_COM_ORIGEM_DO_AGENTE
    atendidas: Dict[str, Any] = {
        "mensuravel": mensuravel,
        "porque": ("" if mensuravel else
                   "antes de 14/09/2026 a resposta do agente era gravada sem marca "
                   "de origem: não dá para separar robô de pessoa (EXTRA-001.2)"),
        "com_agente": (so_agente + ambos) if mensuravel else NAO_MENSURAVEL,
        "so_com_pessoa": so_humano if mensuravel else NAO_MENSURAVEL,
        "com_os_dois": ambos if mensuravel else NAO_MENSURAVEL,
        "conversas_mexidas": len(conversas),
    }

    # --------------------------------------------------------------- ② rajadas
    rajadas = 0
    for m in mensagens:
        carga = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        ids = (carga or {}).get("wa_message_ids")
        if isinstance(ids, list) and len(ids) >= MINIMO_DE_IDS_PARA_SER_RAJADA:
            rajadas += 1

    # ------------------------------------------------- ③ apólice (SEM ESCRITOR)
    apolice_confirmada = sum(1 for c_ in conversas
                             if c_.get("apolice_confirmada") is True)

    # ----------------------------------------------------------- ④ acionamentos
    protocolos = sum(1 for e in envios if str(e.get("kind") or "") == KIND_PROTOCOLO)
    encaminhados = sum(1 for e in envios
                       if str(e.get("kind") or "") == KIND_ENCAMINHAMENTO)
    runs_acionamento: Dict[str, int] = {}
    for r in runs:
        if str(r.get("runtime_kind") or "") == "acionamento":
            runs_acionamento[str(r.get("status") or "?")] = \
                runs_acionamento.get(str(r.get("status") or "?"), 0) + 1

    # --------------------------------------------------------------- ⑤ handoffs
    entregues = sum(1 for a in atividades
                    if str(a.get("title") or "") == TITULO_HANDOFF_ENTREGUE)
    falhados = sum(1 for a in atividades
                   if str(a.get("title") or "") == TITULO_HANDOFF_FALHOU)
    realertados = sum(1 for e in eventos
                      if str(e.get("event_type") or "") == "handoff.realertado")
    no_teto = sum(1 for e in eventos
                  if str(e.get("event_type") or "") == "handoff.teto_de_lembretes")

    # -------------------------------------------------------- ⑥ grupo, por tipo
    por_tipo = {t: 0 for t in TIPOS_DO_GRUPO}
    outros_tipos = 0
    for e in eventos:
        if str(e.get("event_type") or "") != "grupo.enviado":
            continue
        carga = e.get("payload_redacted")
        carga = carga if isinstance(carga, dict) else {}
        tipo = str(carga.get("tipo") or "")
        if tipo in por_tipo:
            por_tipo[tipo] += 1
        else:
            outros_tipos += 1

    # ------------------------------------------------------ ⑦ silêncios, por CLASSE
    #
    # ⛔ `detail` de takeover carrega NOME DE PESSOA. Ele entra no MOTOR e sai
    #    como classe; nunca é impresso, guardado nem devolvido.
    silencios: Dict[str, int] = {}
    excecoes = 0
    for a in atividades:
        titulo = str(a.get("title") or "")
        if titulo == TITULO_SILENCIO_EXCECAO:
            excecoes += 1
            continue
        if titulo != TITULO_SILENCIO:
            continue
        classe = classe_do_silencio(a.get("detail"))
        silencios[classe] = silencios.get(classe, 0) + 1

    # ---------------------------------------------- ⑧ quanto resolveu sozinho
    eficiencia = eficiencia_do_dia(
        acionamentos_entregues=int(c.get("acionamentos_entregues") or 0),
        sinistros_com_dossie=int(c.get("sinistros_com_dossie") or 0),
        ajudas_por_incapacidade=int(c.get("ajudas_incapacidade") or 0))
    ajudas_totais = (int(c.get("ajudas_incapacidade") or 0)
                     + int(c.get("ajudas_regra") or 0)
                     + int(c.get("ajudas_desconhecidas") or 0))
    fatia_desconhecida = ((int(c.get("ajudas_desconhecidas") or 0) / ajudas_totais)
                          if ajudas_totais else 0.0)
    # 🔴 O MESMO limite do resumo das 19h: acima dele o número NÃO é publicado.
    eficiencia_publicavel = (eficiencia is not None
                             and fatia_desconhecida <= LIMITE_DE_DESCONHECIDOS)
    desfechos = {m: 0 for m in MOTIVOS}
    for c_ in conversas:
        motivo = str(c_.get("resolucao_motivo") or "")
        if motivo in desfechos:
            desfechos[motivo] += 1

    tempos = sorted(int(l.get("response_time_ms") or 0) for l in chat
                    if l.get("response_time_ms") is not None)
    estados_do_chat: Dict[str, int] = {}
    for l in chat:
        e = str(l.get("status") or "?")
        estados_do_chat[e] = estados_do_chat.get(e, 0) + 1

    return {
        "dia": dia.isoformat(),
        "truncou": bool(leitura.get("truncou")),
        "atendidas": atendidas,
        "rajadas_coalescidas": rajadas,
        "apolice": {"confirmada_hoje": apolice_confirmada,
                    "em_uma_rodada": "SEM ESCRITOR"},
        "acionamentos": {"com_protocolo": protocolos,
                         "encaminhados_sem_protocolo": encaminhados,
                         "runs_por_status": runs_acionamento},
        "handoffs": {"entregues": entregues, "sem_ninguem_para_receber": falhados,
                     "relembrados": realertados, "no_teto_de_lembretes": no_teto},
        "grupo": {"por_tipo": por_tipo, "de_tipo_desconhecido": outros_tipos,
                  "calados": int(c.get("calados_total") or 0),
                  "calados_pela_janela": int(c.get("calados_pela_janela") or 0),
                  "ja_com_a_equipe": int(c.get("ja_com_a_equipe") or 0)},
        "silencios_do_agente": {"por_classe": silencios,
                                "respondeu_por_excecao": excecoes},
        "resolveu_sozinho": {
            "eficiencia_pct": eficiencia,
            "publicavel": eficiencia_publicavel,
            "ajudas_sem_motivo": int(c.get("ajudas_desconhecidas") or 0),
            "ajudas_totais": ajudas_totais,
            "desfechos": desfechos},
        "chat_principal": {"perguntas": len(chat), "por_estado": estados_do_chat,
                           "p90_ms": (tempos[min(len(tempos) - 1,
                                                 int(round(0.9 * (len(tempos) - 1))))]
                                      if tempos else None)},
        "contagens_do_motor": c,
    }


def somar_os_dias(dias: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """O agregado do período por corretora — a base da régua. **PURA.**

    ⚠️ Cada soma diz de quantos dias ela veio: um agregado sem o `n` deixa o
    leitor tomar 3 dias por 13.
    """
    def _s(caminho: Sequence[str]) -> int:
        total = 0
        for d in dias:
            no = d
            for p in caminho:
                no = (no or {}).get(p) if isinstance(no, dict) else None
            total += int(no or 0)
        return total

    silencios: Dict[str, int] = {}
    tipos = {t: 0 for t in TIPOS_DO_GRUPO}
    desfechos = {m: 0 for m in MOTIVOS}
    for d in dias:
        for k, v in (d["silencios_do_agente"]["por_classe"] or {}).items():
            silencios[k] = silencios.get(k, 0) + int(v or 0)
        for k, v in (d["grupo"]["por_tipo"] or {}).items():
            tipos[k] = tipos.get(k, 0) + int(v or 0)
        for k, v in (d["resolveu_sozinho"]["desfechos"] or {}).items():
            desfechos[k] = desfechos.get(k, 0) + int(v or 0)

    dias_mensuraveis = [d for d in dias if d["atendidas"]["mensuravel"]]
    tempos = [d["chat_principal"]["p90_ms"] for d in dias
              if d["chat_principal"]["p90_ms"] is not None]

    return {
        "dias": len(dias),
        "dias_com_origem_do_agente": len(dias_mensuraveis),
        "truncou": any(d["truncou"] for d in dias),
        "conversas_com_agente": sum(int(d["atendidas"]["com_agente"] or 0)
                                    for d in dias_mensuraveis),
        "conversas_so_com_pessoa": sum(int(d["atendidas"]["so_com_pessoa"] or 0)
                                       for d in dias_mensuraveis),
        "conversas_com_os_dois": sum(int(d["atendidas"]["com_os_dois"] or 0)
                                     for d in dias_mensuraveis),
        "conversas_mexidas": _s(("atendidas", "conversas_mexidas")),
        "rajadas_coalescidas": _s(("rajadas_coalescidas",)),
        "apolice_confirmada_hoje": _s(("apolice", "confirmada_hoje")),
        "acionamentos_com_protocolo": _s(("acionamentos", "com_protocolo")),
        "acionamentos_encaminhados": _s(("acionamentos",
                                         "encaminhados_sem_protocolo")),
        "acionamentos_iniciados": sum(
            sum((d["acionamentos"]["runs_por_status"] or {}).values()) for d in dias),
        "handoffs_entregues": _s(("handoffs", "entregues")),
        "handoffs_sem_ninguem": _s(("handoffs", "sem_ninguem_para_receber")),
        "handoffs_no_teto": _s(("handoffs", "no_teto_de_lembretes")),
        "grupo_por_tipo": tipos,
        "grupo_calados": _s(("grupo", "calados")),
        "silencios_por_classe": silencios,
        "silencios_total": sum(silencios.values()),
        "acionamentos_entregues_motor": _s(("contagens_do_motor",
                                            "acionamentos_entregues")),
        "sinistros_com_dossie_motor": _s(("contagens_do_motor",
                                          "sinistros_com_dossie")),
        "ajudas_incapacidade": _s(("contagens_do_motor", "ajudas_incapacidade")),
        "ajudas_regra": _s(("contagens_do_motor", "ajudas_regra")),
        "ajudas_desconhecidas": _s(("contagens_do_motor", "ajudas_desconhecidas")),
        "desfechos": desfechos,
        "chat_perguntas": _s(("chat_principal", "perguntas")),
        "chat_p90_ms_pior_dia": max(tempos) if tempos else None,
        "chat_estados": {k: v for d in dias
                         for k, v in (d["chat_principal"]["por_estado"] or {}).items()},
    }


# =========================================================================== #
# ③ A RÉGUA — nota 0–100 por dimensão, ou NÃO AVALIADA com o motivo
# =========================================================================== #

NAO_AVALIADA = "NÃO AVALIADA"

#: 💭 As notas-palpite dos auditores em 12/09/2026 (diagnóstico §0). ⚠️ Elas
#: são ILUSTRATIVAS (CLAUDE.md §12.1): ficam ao lado para comparação e **não
#: são citáveis como medição**.
PALPITE: Dict[str, int] = {
    "atendimento.apolice_certa": 50, "atendimento.coleta_e_age": 40,
    "atendimento.aciona": 25, "atendimento.fala_como_humano": 60,
    "atendimento.sabe_calar": 45, "atendimento.sabe_pedir_ajuda": 55,
    "chat.apolice_certa": 35, "chat.uma_rodada": 25, "chat.completude": 45,
    "chat.confiabilidade": 80, "chat.velocidade": 60,
}

#: 🔴 A AMOSTRA MÍNIMA de cada dimensão com fonte. Abaixo dela sai
#: `NÃO AVALIADA — amostra insuficiente`.
#:
#: **Por que 5, e não 1:** com denominador 1 a nota só pode ser 0 ou 100, e um
#: único caso vira "o agente aciona perfeitamente" ou "o agente nunca aciona".
#: 📊 O piloto do Founder são 3 dias; 5 casos é o menor número que ainda deixa
#: a nota andar em degraus de 20 pontos em vez de saltar entre os extremos.
N_MINIMO_DE_CASOS = 5

#: **Por que 20 no chat:** um p90 é um percentil — com menos de 20 pontos ele é
#: praticamente o máximo da amostra, e o máximo de 3 perguntas não descreve
#: velocidade nenhuma.
N_MINIMO_DE_PERGUNTAS = 20

#: A régua da velocidade do chat, e o porquê de cada ponta.
#: 📊 `conversation_logs.response_time_ms` é o tempo que o produto já mede.
#: ⚠️ ATÉ 5 s a resposta chega antes de a pessoa trocar de aba (100).
#: ⚠️ A PARTIR DE 30 s ela já abriu outra coisa e a resposta chega sozinha (0).
VELOCIDADE_OTIMA_MS = 5_000
VELOCIDADE_PESSIMA_MS = 30_000

#: 🔴 A nota agregada só sai com a MAIORIA das dimensões avaliada. Uma média de
#: 1 dimensão em 6 tem cara de nota do bloco inteiro e não é.
FRACAO_MINIMA_AVALIADA = 0.5


def _avaliada(chave: str, nota: int, criterio: str, fonte: str,
              n: int, n_minimo: int) -> Dict[str, Any]:
    return {"chave": chave, "nota": int(max(0, min(100, nota))),
            "criterio": criterio, "fonte": fonte, "n": int(n),
            "n_minimo": int(n_minimo), "palpite_antigo": PALPITE.get(chave)}


def _sem_nota(chave: str, criterio: str, motivo: str,
              n: int = 0, n_minimo: int = 0) -> Dict[str, Any]:
    return {"chave": chave, "nota": NAO_AVALIADA, "criterio": criterio,
            "fonte": motivo, "n": int(n), "n_minimo": int(n_minimo),
            "palpite_antigo": PALPITE.get(chave)}


def _taxa(chave: str, criterio: str, fonte: str, acertos: int, total: int,
          n_minimo: int = N_MINIMO_DE_CASOS) -> Dict[str, Any]:
    """Nota = a fatia que deu certo, com piso de amostra.

    🔴 **MENOS DADO NUNCA CRIA NOTA.** Abaixo do piso a dimensão sai
    `NÃO AVALIADA` — é por isso que "sabe pedir ajuda" **não** pode dar 100
    num período sem nenhum pedido de ajuda: zero de zero não é perfeição, é
    ausência de prova.
    """
    if total < n_minimo:
        return _sem_nota(chave, criterio,
                         "amostra insuficiente (%d de %d)" % (total, n_minimo),
                         n=total, n_minimo=n_minimo)
    return _avaliada(chave, int(round(100.0 * acertos / total)), criterio, fonte,
                     n=total, n_minimo=n_minimo)


def regua_por_dimensao(a: Dict[str, Any]) -> Dict[str, Any]:
    """As 11 dimensões do §0 do diagnóstico, sobre o agregado. **PURA.**"""
    atendimento: List[Dict[str, Any]] = []
    chat: List[Dict[str, Any]] = []

    # ----------------------------------------------------------- ATENDIMENTO
    atendimento.append(_sem_nota(
        "atendimento.apolice_certa",
        "de cada 10 atendimentos, em quantos o agente fixou a apólice certa "
        "logo na primeira tentativa",
        "o produto ainda não grava em quantas rodadas a apólice foi fixada: só "
        "existe um sim/não que é sobrescrito, sem histórico "
        "(conversations.ficha_atendimento.apolice_confirmada)"))

    base = a["acionamentos_entregues_motor"] + a["sinistros_com_dossie_motor"]
    denominador = base + a["ajudas_incapacidade"]
    ajudas = a["ajudas_incapacidade"] + a["ajudas_regra"] + a["ajudas_desconhecidas"]
    fatia = (a["ajudas_desconhecidas"] / ajudas) if ajudas else 0.0
    criterio_coleta = ("de cada 10 casos que o agente pegou, em quantos ele foi "
                       "até o fim sozinho em vez de parar por não conseguir")
    if fatia > LIMITE_DE_DESCONHECIDOS and ajudas:
        # 🔴 O MESMO corte do resumo das 19h: um número calculado sobre a
        #    minoria classificada PARECE medição e é pior que número nenhum.
        atendimento.append(_sem_nota(
            "atendimento.coleta_e_age", criterio_coleta,
            "%d de %d pedidos de ajuda saíram sem motivo registrado — acima do "
            "limite de %d%% que o próprio resumo das 19h respeita"
            % (a["ajudas_desconhecidas"], ajudas,
               int(LIMITE_DE_DESCONHECIDOS * 100)),
            n=denominador, n_minimo=N_MINIMO_DE_CASOS))
    else:
        eficiencia = eficiencia_do_dia(
            acionamentos_entregues=a["acionamentos_entregues_motor"],
            sinistros_com_dossie=a["sinistros_com_dossie_motor"],
            ajudas_por_incapacidade=a["ajudas_incapacidade"])
        if eficiencia is None or denominador < N_MINIMO_DE_CASOS:
            atendimento.append(_sem_nota(
                "atendimento.coleta_e_age", criterio_coleta,
                "amostra insuficiente (%d de %d) — denominador zero não é 0%%, é "
                "'sem acionamentos no período'" % (denominador, N_MINIMO_DE_CASOS),
                n=denominador, n_minimo=N_MINIMO_DE_CASOS))
        else:
            atendimento.append(_avaliada(
                "atendimento.coleta_e_age", eficiencia, criterio_coleta,
                "eficiencia_do_dia do motor do resumo das 19h (D-PILOTO-13)",
                n=denominador, n_minimo=N_MINIMO_DE_CASOS))

    atendimento.append(_taxa(
        "atendimento.aciona",
        "de cada 10 acionamentos que o agente abriu, em quantos o segurado "
        "recebeu o protocolo no fim",
        "platform_sends kind='acionamento_protocolo' sobre os work_runs de "
        "acionamento abertos no período",
        a["acionamentos_com_protocolo"], a["acionamentos_iniciados"]))

    atendimento.append(_sem_nota(
        "atendimento.fala_como_humano",
        "o segurado sentiu que falou com uma pessoa, e não com um robô",
        "não há fonte durável: julgar isto exige LER a mensagem, e conteúdo de "
        "conversa não entra em medição (CLAUDE.md §7). Nenhuma nota, nenhuma "
        "avaliação automática e nenhum sinal do segurado são gravados"))

    silencios = a["silencios_total"]
    atendimento.append(_sem_nota(
        "atendimento.sabe_calar",
        "quando havia uma pessoa da corretora na conversa, o agente ficou "
        "quieto — e falou quando era a vez dele",
        "o produto grava QUANTAS vezes o agente calou (%d no período, por "
        "classe) mas nunca se o silêncio era o certo: não existe registro de "
        "'devia ter falado e não falou'. ⛔ Um período sem silêncio nenhum "
        "seria 100 por ausência de prova, e isso é proibido"
        % silencios))

    atendimento.append(_taxa(
        "atendimento.sabe_pedir_ajuda",
        "de cada 10 vezes que o agente pediu ajuda humana, em quantas alguém "
        "da equipe realmente recebeu o caso",
        "agent_activities com os títulos que human_handoff escreve "
        "(entregue × sem ninguém para receber)",
        a["handoffs_entregues"],
        a["handoffs_entregues"] + a["handoffs_sem_ninguem"]))

    # --------------------------------------------------------- CHAT PRINCIPAL
    chat.append(_sem_nota(
        "chat.apolice_certa",
        "quando a corretora pergunta sobre uma apólice, o chat traz a apólice "
        "certa",
        "sem escritor: nada liga a pergunta do chat à apólice que foi usada "
        "para responder (conversation_logs não grava a apólice)"))
    chat.append(_sem_nota(
        "chat.uma_rodada",
        "a corretora recebe a resposta sem ter de repetir a pergunta",
        "sem escritor: nenhuma linha diz se a pergunta seguinte foi uma "
        "repetição da anterior"))
    chat.append(_sem_nota(
        "chat.completude",
        "a resposta traz tudo o que foi perguntado, e não metade",
        "não há fonte durável: julgar completude exige ler a resposta e "
        "compará-la com a pergunta — é trabalho de avaliador, não de SELECT"))

    estados = a["chat_estados"] or {}
    chat.append(_sem_nota(
        "chat.confiabilidade",
        "de cada 10 perguntas, em quantas o chat respondeu em vez de falhar",
        "a única coluna disponível não consegue discordar: 📊 conversation_logs."
        "status é '%s' em 100%% das linhas medidas (%d). Um guarda que não tem "
        "como falhar não guarda nada (CLAUDE.md §9.3) — e uma resposta que "
        "nunca saiu não deixa linha nenhuma"
        % ("/".join(sorted(estados)) or "success", sum(estados.values())),
        n=sum(estados.values())))

    p90 = a["chat_p90_ms_pior_dia"]
    criterio_vel = ("a resposta chega antes de a pessoa desistir de esperar "
                    "(até %ds vale 100; a partir de %ds, 0)"
                    % (VELOCIDADE_OTIMA_MS // 1000, VELOCIDADE_PESSIMA_MS // 1000))
    if p90 is None or a["chat_perguntas"] < N_MINIMO_DE_PERGUNTAS:
        chat.append(_sem_nota(
            "chat.velocidade", criterio_vel,
            "amostra insuficiente (%d de %d perguntas)"
            % (a["chat_perguntas"], N_MINIMO_DE_PERGUNTAS),
            n=a["chat_perguntas"], n_minimo=N_MINIMO_DE_PERGUNTAS))
    else:
        faixa = VELOCIDADE_PESSIMA_MS - VELOCIDADE_OTIMA_MS
        nota = int(round(100.0 * (VELOCIDADE_PESSIMA_MS - p90) / faixa))
        chat.append(_avaliada(
            "chat.velocidade", nota, criterio_vel,
            "p90 do response_time_ms do pior dia do período (%d ms)" % p90,
            n=a["chat_perguntas"], n_minimo=N_MINIMO_DE_PERGUNTAS))

    return {"atendimento": _bloco(atendimento, "atendimento"),
            "chat_principal": _bloco(chat, "chat principal")}


def _bloco(dimensoes: List[Dict[str, Any]], nome: str) -> Dict[str, Any]:
    """A nota do bloco — só com a MAIORIA das dimensões avaliada. **PURA.**"""
    com_nota = [d for d in dimensoes if d["nota"] != NAO_AVALIADA]
    if len(com_nota) < FRACAO_MINIMA_AVALIADA * len(dimensoes) or not com_nota:
        nota: Any = NAO_AVALIADA
        porque = ("%d de %d dimensões têm fonte durável hoje — uma média sobre a "
                  "minoria teria cara de nota do bloco inteiro"
                  % (len(com_nota), len(dimensoes)))
    else:
        nota = int(round(sum(int(d["nota"]) for d in com_nota) / len(com_nota)))
        porque = "média de %d dimensões avaliadas de %d" % (len(com_nota),
                                                            len(dimensoes))
    return {"nome": nome, "nota": nota, "porque": porque, "dimensoes": dimensoes}


# =========================================================================== #
# ④ O RELATÓRIO
# =========================================================================== #

async def resolver_corretoras(cliente, nomes: Sequence[str]) -> List[Tuple[str, str]]:
    """(nome, id) por `companies.company_name`. ⛔ Nenhum id escrito em código."""
    achadas: List[Tuple[str, str]] = []
    for nome in nomes:
        linhas = (await cliente.table("companies").select("id, company_name")
                  .eq("company_name", nome).limit(2).execute()).data or []
        if not linhas:
            raise SystemExit("⛔ corretora não encontrada em companies: %r" % nome)
        achadas.append((nome, str(linhas[0]["id"])))
    return achadas


async def medir(cliente, corretoras: Sequence[Tuple[str, str]], de: date,
                ate: date, *, tz=None) -> Dict[str, Any]:
    tz = tz or fuso_da_corretora()
    corpo: Dict[str, Any] = {"de": de.isoformat(), "ate": ate.isoformat(),
                             "corretoras": {}}
    for nome, cid in corretoras:
        dias: List[Dict[str, Any]] = []
        d = de
        while d <= ate:
            inicio, fim = limites_do_dia(d, tz)
            dias.append(medir_o_dia(await ler_o_dia(cliente, cid, inicio, fim),
                                    dia=d))
            d += timedelta(days=1)
        agregado = somar_os_dias(dias)
        corpo["corretoras"][nome] = {"dias": dias, "agregado": agregado,
                                     "regua": regua_por_dimensao(agregado)}
    return corpo


def _n(v: Any) -> str:
    return NAO_MENSURAVEL if v == NAO_MENSURAVEL else str(v)


def em_markdown(corpo: Dict[str, Any], *, comando: str, gerado_em: str) -> str:
    """A saída em linguagem de gente. ⛔ Nome de tabela só entre parênteses."""
    L: List[str] = []
    L.append("# 📊 O piloto medido — %s a %s" % (corpo["de"], corpo["ate"]))
    L.append("")
    L.append("> 📊 **Medido em %s** · fonte: o banco de produção, só SELECT · "
             "gerado por:" % gerado_em)
    L.append("> ```")
    L.append("> %s" % comando)
    L.append("> ```")
    L.append("> Todo número desta página é 📊 MEDIDO. As notas antigas ao lado "
             "são 💭 palpite dos auditores em 12/09/2026 e **não são citáveis "
             "como medição** (CLAUDE.md §12.1).")
    L.append("")
    # 🔴 Um período que chega em HOJE não fecha: rodar de novo daqui a uma hora
    #    dá outro número, e duas páginas com o mesmo título e números diferentes
    #    é como se perde a confiança numa medição. A página diz isso sozinha.
    if corpo["ate"] >= datetime.now(timezone.utc).astimezone(
            fuso_da_corretora()).date().isoformat():
        L.append("⚠️ **O último dia (%s) ainda está correndo**: ele muda a cada "
                 "hora. Para um número que não se mexe, peça até o dia anterior."
                 % corpo["ate"])
        L.append("")

    for nome, bloco in corpo["corretoras"].items():
        a = bloco["agregado"]
        L.append("## %s" % nome)
        L.append("")
        if a["truncou"]:
            L.append("⚠️ **A leitura parou no teto em pelo menos um dia**: os "
                     "números abaixo são um piso, não o total.")
            L.append("")
        L.append("### Dia a dia")
        L.append("")
        L.append("| dia | conversas que o agente atendeu | conversas só com "
                 "pessoa | rajadas juntadas | acionamentos com protocolo | "
                 "handoffs entregues | avisos ao grupo | silêncios do agente |")
        L.append("|---|---|---|---|---|---|---|---|")
        for d in bloco["dias"]:
            L.append("| %s | %s | %s | %d | %d | %d | %d | %d |" % (
                d["dia"], _n(d["atendidas"]["com_agente"]),
                _n(d["atendidas"]["so_com_pessoa"]), d["rajadas_coalescidas"],
                d["acionamentos"]["com_protocolo"], d["handoffs"]["entregues"],
                sum(d["grupo"]["por_tipo"].values()),
                sum(d["silencios_do_agente"]["por_classe"].values())))
        L.append("")
        L.append("📊 No período inteiro (%d dias): **%d** conversas com fala do "
                 "agente, **%d** só com uma pessoa da corretora, **%d** com os "
                 "dois. ⚠️ Só **%d** desses dias são mensuráveis: antes de "
                 "14/09/2026 o produto não marcava quem escreveu a resposta."
                 % (a["dias"], a["conversas_com_agente"],
                    a["conversas_so_com_pessoa"], a["conversas_com_os_dois"],
                    a["dias_com_origem_do_agente"]))
        L.append("")
        L.append("📊 Avisos ao grupo, por tipo: %s." % (", ".join(
            "%s %d" % (t.replace("_", " "), n)
            for t, n in sorted(a["grupo_por_tipo"].items()) if n) or "nenhum"))
        L.append("")
        L.append("📊 Silêncios do agente, por classe: %s. ⚠️ Silêncio do agente "
                 "(com o segurado) e grupo calado (%d) são coisas diferentes e "
                 "nunca se somam. ⚠️ A trava que evita repetir a mesma linha "
                 "mora na memória de cada processo: se houver mais de um "
                 "trabalhador no ar, pode haver linha repetida aqui."
                 % (", ".join("%s %d" % (k, v) for k, v in
                              sorted(a["silencios_por_classe"].items()))
                    or "nenhum", a["grupo_calados"]))
        L.append("")
        L.append("📊 Handoffs: %d entregues, %d sem ninguém para receber, %d "
                 "lembretes no teto. ⚠️ O lembrete no teto é contado **por "
                 "varredura do vigia**, não por conversa: o mesmo caso parado "
                 "reaparece a cada rodada."
                 % (a["handoffs_entregues"], a["handoffs_sem_ninguem"],
                    a["handoffs_no_teto"]))
        L.append("")
        L.append("📊 Rajadas juntadas no período: **%d**. ⚠️ Só a FUSÃO deixa "
                 "rastro durável; a janela de espera e o teto de mensagens "
                 "moram no log e na memória rápida, e **não são mensuráveis** "
                 "por aqui." % a["rajadas_coalescidas"])
        L.append("")
        L.append("📊 Apólices marcadas como confirmadas hoje: **%d** — é "
                 "INFORMAÇÃO, não nota: o produto não guarda em quantas "
                 "rodadas isso aconteceu." % a["apolice_confirmada_hoje"])
        L.append("")

        for chave in ("atendimento", "chat_principal"):
            b = bloco["regua"][chave]
            L.append("### A régua — %s" % b["nome"])
            L.append("")
            L.append("**Nota do bloco: %s** — %s" % (b["nota"], b["porque"]))
            L.append("")
            L.append("| dimensão | nota medida | 💭 palpite de 12/09 | o "
                     "critério | amostra |")
            L.append("|---|---|---|---|---|")
            for d in b["dimensoes"]:
                rotulo = d["chave"].split(".", 1)[1].replace("_", " ")
                if d["nota"] == NAO_AVALIADA:
                    nota = "**NÃO AVALIADA** — %s" % d["fonte"]
                    amostra = "%d (mínimo %d)" % (d["n"], d["n_minimo"])
                else:
                    nota = "**%d**" % d["nota"]
                    amostra = "%d casos (mínimo %d) · %s" % (d["n"], d["n_minimo"],
                                                             d["fonte"])
                L.append("| %s | %s | 💭 %s | %s | %s |" % (
                    rotulo, nota, d["palpite_antigo"], d["criterio"], amostra))
            L.append("")
    return "\n".join(L) + "\n"


def _dia(texto: str) -> date:
    return datetime.strptime(texto, "%Y-%m-%d").date()


def sem_o_carimbo(texto: str) -> str:
    """O corpo comparável entre duas rodadas — sem a hora de geração.

    🔴 G2 compara DUAS rodadas sobre um intervalo fechado. O carimbo de geração
    muda a cada rodada por construção; compará-lo provaria só que o relógio anda.
    """
    return "\n".join(l for l in (texto or "").splitlines()
                     if "Medido em" not in l and '"gerado_em"' not in l)


async def _principal(args) -> int:
    from app.core.database import create_async_supabase_client

    cliente = (await create_async_supabase_client()).client
    corretoras = await resolver_corretoras(cliente, args.corretora
                                           or list(CORRETORAS_PADRAO))
    corpo = await medir(cliente, corretoras, _dia(args.de), _dia(args.ate))
    comando = "cd backend && python scripts/medir_o_piloto.py " + " ".join(sys.argv[1:])
    gerado_em = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    if args.formato == "json":
        corpo["gerado_em"] = gerado_em
        corpo["comando"] = comando
        saida = json.dumps(corpo, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        saida = em_markdown(corpo, comando=comando, gerado_em=gerado_em)

    # 🔴 G3 — a saída NÃO sai do processo antes de ser varrida.
    achados = procurar_pii(saida)
    if achados:
        print("⛔ PII na saída (%d): %s" % (len(achados),
                                            sorted({a[0] for a in achados})))
        return 2

    if args.saida:
        with io.open(args.saida, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(saida)
        print("📊 escrito em %s · %d bytes · sha256(sem carimbo)=%s"
              % (args.saida, len(saida.encode("utf-8")),
                 hashlib.sha256(sem_o_carimbo(saida).encode("utf-8")).hexdigest()[:16]))
    else:
        print(saida)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="📊 a medição diária do piloto")
    p.add_argument("--de", required=True, help="AAAA-MM-DD (dia local da corretora)")
    p.add_argument("--ate", required=True, help="AAAA-MM-DD, inclusive")
    p.add_argument("--corretora", action="append",
                   help="company_name; repetível. Padrão: %s"
                        % ", ".join(CORRETORAS_PADRAO))
    p.add_argument("--formato", choices=("json", "markdown"), default="markdown")
    p.add_argument("--saida", help="caminho do arquivo; sem ele, imprime")
    args = p.parse_args(list(argv) if argv is not None else None)

    from dotenv import load_dotenv

    load_dotenv(os.path.join(RAIZ, ".env"))
    return asyncio.run(_principal(args))


if __name__ == "__main__":
    sys.exit(main())
