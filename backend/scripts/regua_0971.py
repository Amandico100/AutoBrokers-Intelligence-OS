# -*- coding: utf-8 -*-
"""A RÉGUA DO PÓS-ACIONAMENTO — SPEC-097.1 U4/R8.

Duas linhas, uma unidade:

    resolvido_pelo_agente   carta ∨ estado ∨ handoff PÓS com dossiê COMPLETO
    resolvido_sem_humano    carta ∨ estado

🧑 A primeira é a meta do Founder (*"entregar para o humano é um status em que
o agente não tem mais o que fazer"*). A segunda fica publicada ao lado para
que o esforço humano continue visível — 📊 e porque a taxonomia tem um TETO
aritmético: 27 dos 283 turnos com intenção do acervo são humanos por desenho,
o que dá **94,7 %** (com J contando como estado) ou **90,5 %** (sem J). Nem no
melhor caso uma régua honesta chega a 95 % pelo caminho sem humano.

🔴 **A régua chama o MOTOR** (CLAUDE.md §9.4). O classificador de turno, o mapa
de cartas e a lista de situações humanas são IMPORTADOS de
`app.atendimento.pos_acionamento` — os MESMOS objetos que o prompt do agente e
o dossiê do handoff usam (o guarda prova a identidade por `is`). Um
classificador próprio aqui mediria o classificador próprio, e não o produto.

⛔ **Sem LLM em ponto nenhum.** A cascata é regex e o mapa é um dicionário:
custo zero, resultado reproduzível.

Uso::

    cd backend
    PYTHONIOENCODING=utf-8 python scripts/regua_0971.py            # o acervo
    PYTHONIOENCODING=utf-8 python scripts/regua_0971.py --fixture  # sem banco
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app.atendimento.pos_acionamento import (  # noqa: E402
    SEM_INTENCAO,
    SITUACOES_PARA_HUMANO,
    _norm,
    classificar_turno,
    e_atendimento_de_seguro,
    mapa_de_cartas,
    vai_para_humano,
)

#: 🔴 Os rótulos que só o ESTADO ESCRITO resolve — não há carta que responda
#: *"e o meu caso?"*. ⚠️ `J` está aqui porque a SPEC precisa publicar o teto
#: **com** e **sem** ele (E8): pedir que a corretora cobre a seguradora é uma
#: pergunta que o estado responde ("já estamos cobrando desde …").
ROTULOS_DE_ESTADO = ("A", "H", "G", "J")

#: 📊 O TETO ARITMÉTICO da taxonomia medida (E8) — publicado AO LADO do número,
#: nunca no lugar dele.
TETO = {"com_J": 94.7, "sem_J": 90.5,
        "fonte": "reality-report-0971.md §2 · 283 turnos com intenção · 27 humanos por desenho"}

#: 🧑 A meta do Founder (SPEC §7.1). ⚠️ Ela mora aqui para que a saída possa
#: DIZER quando não a alcança — um número publicado ao lado de uma meta, sem a
#: comparação escrita, deixa o leitor fazer a conta errada ([6] do red team).
META_DO_FOUNDER = 95.0


# ===========================================================================
# 🔴 O DOSSIÊ NÃO SE AFIRMA: ELE SE EXECUTA (§9.4)
#
# 📊 Achado [5] do red team em 05/09/2026: `_dossie_completo` lia
# `turno["dossie"]["onde_parou"]` — um dicionário que **o acervo nunca carrega**
# e que nenhum motor produz. Zero chamadas a `_dossie_de_pos_acionamento`. O
# arquivo provava que os campos existiriam, não que o motor os produz; e por
# isso `handoff_pos` era ZERO na corrida real e o terceiro termo de R8 nunca
# contribuiu. É o corolário da SPEC-083, palavra por palavra: **o que se afirma
# é o comportamento do MOTOR sobre o texto REAL.**
#
# ⚠️ E ligar o motor sem cuidado vira CARIMBO: a recomendação do dossiê devolve
# sempre texto não-vazio, e `_onde_parou` sem espera devolve *"não há espera
# registrada para este caso"*. Contar isso como dossiê completo faria toda
# desistência virar "resolvido pelo agente" (§9.5: o guarda precisa poder ficar
# VERMELHO).
#
# 🔴 E o nome da função do motor NÃO aparece antes do import lá embaixo, de
# propósito: a mutação U8 troca a **primeira** ocorrência do arquivo
# (`replace(de, para, 1)`), e uma âncora que cai num comentário muta um texto
# que ninguém executa — a mutação nasceria verde e o bloco seria carimbo. A
# âncora mora na 1ª ocorrência em CÓDIGO. É a lição que a 097.1 já pagou duas
# vezes (U2 e U6B).
# 🔴 Por isso a frase de ausência é uma CONSTANTE lida aqui, e o CONTROLE da
# saída roda a mesma medição com o estado removido.
# ===========================================================================

class _BancoDoTurno:
    """O mundo do turno, em memória: a conversa, a espera e nenhuma mensagem.

    ⛔ **Zero rede e zero PII**: só devolve o que o próprio turno da fixture
    carrega. ⚠️ Ele existe porque o motor do dossiê LÊ o estado (`work_waits`)
    em vez de recebê-lo — e é essa leitura que decide se há `Onde parou`.
    """

    def __init__(self, espera=None):
        self._espera = [espera] if isinstance(espera, dict) and espera else []
        self._tabela = ""

    def table(self, nome):
        self._tabela = str(nome)
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self, *a, **k):
        linhas = self._espera if self._tabela == "work_waits" else []
        return type("R", (), {"data": list(linhas)})()


def _secao_do_dossie(texto: str, titulo: str) -> str:
    """O corpo de uma seção `*Título*` do dossiê. `""` quando ela não existe."""
    linhas = str(texto or "").split(chr(10))
    try:
        i = linhas.index(titulo)
    except ValueError:
        return ""
    corpo = []
    for linha in linhas[i + 1:]:
        if linha.startswith("*") and linha.endswith("*"):
            break
        if linha.strip():
            corpo.append(linha.strip())
    return " ".join(corpo).strip()


def _caso_do_turno(turno: Any) -> Dict[str, Any]:
    """O CASO deste turno: a conversa lida do banco + a rajada REAL do turno.

    🔴 Achado [J-3] do juiz (06/09/2026): `_ler_acervo` nunca escrevia `caso`,
    e por isso `_dossie_do_motor` devolvia `""` em **464 de 464** turnos. O
    motor estava ligado e nunca alimentado — a mesma forma do P0 [1] (leitor
    sem escritor), e o terceiro termo da R8 não contribuía **por isso**, não
    por limite do histórico.

    ⚠️ As mensagens do turno viajam DENTRO do caso porque é sobre elas que o
    motor decide o rótulo (§9.4: o texto vem do acervo, não da prévia de uma
    linha só).
    """
    caso = (turno or {}).get("caso")
    if not isinstance(caso, dict) or not caso:
        return {}
    mensagens = (turno or {}).get("mensagens") or []
    return dict(caso, mensagens=[str(m or "") for m in mensagens])


def _dossie_do_motor(turno: Any) -> str:
    """Roda `HumanHandoffTool._montar_dossie` — o MOTOR REAL, sobre o CASO.

    🔴 **`_montar_dossie`, e não `_dossie_de_pos_acionamento` direto.** A
    diferença é a regra inteira: é `_montar_dossie` quem pergunta
    `_e_pos_acionamento` e quem LÊ a espera. Chamar o formato pós direto
    escreveria `Onde parou` até para um caso sem lastro nenhum — e a régua
    viraria carimbo (§9.5: o guarda tem de conseguir ficar vermelho).
    """
    caso = _caso_do_turno(turno)
    if not caso:
        return ""
    try:
        from app.agents.tools.human_handoff import HumanHandoffTool

        banco = _BancoDoTurno((turno or {}).get("espera_do_caso"))
        return HumanHandoffTool(banco)._montar_dossie(caso, "")
    except Exception:  # noqa: BLE001
        return ""


def _dossie_completo(turno: Any) -> bool:
    """O handoff PÓS só CONTA quando o MOTOR entrega o dossiê inteiro (R8).

    ⛔ Sem esta linha, *"foi para humano"* viraria carimbo de resolvido: bastaria
    o agente desistir para a régua subir (CLAUDE.md §9.5).

    ⚠️ E o que se mede é o TEXTO que a atendente recebe: as duas seções que a
    R8 exige, presentes e **com lastro**. 📊 `_onde_parou` devolve
    *"não há espera registrada para este caso"* quando `work_waits` está vazia
    — passaria num teste de "não-vazio" e é exatamente o oposto de um dossiê.
    """
    try:
        # 🔴 AS DUAS RESPOSTAS DO MOTOR, importadas do produto — nunca
        #    reescritas aqui. É o que faz esta medição ser sobre o dossiê que a
        #    atendente recebe, e não sobre uma cópia que concorda consigo mesma.
        from app.agents.tools.human_handoff import (
            RECOMENDACAO_SEM_SITUACAO, _com_a_espera, _o_que_fazer, _onde_parou,
        )
    except Exception:  # noqa: BLE001
        return False

    texto = _dossie_do_motor(turno)
    if not texto:
        return False
    onde = _secao_do_dossie(texto, "*Onde parou*")
    fazer = _secao_do_dossie(texto, "*O que fazer*")
    if not onde or not fazer:
        return False
    if "não há espera registrada" in onde.lower():
        return False
    # 🔴 [J-4] — E A AÇÃO TEM DE SER A DA SITUAÇÃO, NÃO A LINHA GENÉRICA.
    #
    # ⛔ `RECOMENDACAO_SEM_SITUACAO` é o que o motor escreve quando a R9 **não
    #    conhece** a situação do turno: *"cobrar quem está devendo"*. É uma boa
    #    frase para a atendente e uma péssima prova para a régua — ela é
    #    CONSTANTE, então aceitá-la faria o dossiê continuar "completo" com
    #    `SITUACOES_PARA_HUMANO` VAZIA, e a R9 seria inerte (o controle do juiz
    #    tem de INVERTER: sem a lista, zero completos).
    if fazer.strip().startswith(RECOMENDACAO_SEM_SITUACAO.strip()):
        return False
    # ⛔ E as seções têm de carregar exatamente o que o MOTOR produziu: um
    #    título com texto de outra origem seria a régua medindo a si mesma.
    caso = _caso_do_turno(turno)
    espera = (turno or {}).get("espera_do_caso")
    return bool(_onde_parou(caso, espera).strip() in texto
                and _o_que_fazer(_com_a_espera(caso, espera), "").strip() in texto)


def _conversas_descartadas(turnos: Iterable[Dict[str, Any]]) -> set:
    """R11 — a conversa inteira é o que se aceita ou se descarta, não o turno.

    ⚠️ **A unidade aqui é a CONVERSA de propósito.** 📊 56,3 % das mensagens
    têm ≤ 24 caracteres: julgar `"Ta!"` isoladamente descartaria o fio inteiro
    do segurado parado no acostamento. Quem carrega o vocabulário é a conversa.
    """
    por_conversa: Dict[str, List[str]] = {}
    for turno in turnos:
        chave = str((turno or {}).get("conversa") or (turno or {}).get("conversation_id") or "")
        por_conversa.setdefault(chave, [])
        por_conversa[chave].extend(str(m or "") for m in (turno.get("mensagens") or []))
    return {chave for chave, msgs in por_conversa.items()
            if not e_atendimento_de_seguro({"mensagens": msgs})}


def medir(turnos: Iterable[Dict[str, Any]], mapa: Optional[Dict[str, str]] = None,
          com_estado: bool = True) -> Dict[str, Any]:
    """As duas réguas sobre uma lista de turnos. **PURA — sem banco e sem LLM.**

    `mapa=None` usa o mapa do módulo; `mapa={}` é a LINHA DE CONTROLE, e é ela
    que dá direito à conclusão: se o número não cair sem as cartas, as cartas
    não eram a causa (CLAUDE.md §9.2).

    `com_estado=False` é a SEGUNDA linha de controle: a MESMA passada com a
    espera arrancada de todo turno. 🔴 Sem ela o `handoff_pos` seria um número
    que só sobe — e número que não sabe cair não prova causa nenhuma. ⚠️ Era
    exatamente aqui que a régua morria em traceback ([J-2] do juiz): o bloco
    de controle chamava um argumento que a função não tinha, e a prova exigida
    pelo conserto do achado [5] **nunca rodou**.
    """
    if mapa is None:
        mapa = mapa_de_cartas()
    lista = [t for t in (turnos or []) if isinstance(t, dict) and t.get("mensagens") is not None]
    if not com_estado:
        lista = [dict(t, espera_do_caso=None, espera_ativa=False) for t in lista]
    descartadas = _conversas_descartadas(lista)

    r = {"denominador": 0, "descartados": 0, "resolvido_por_carta": 0,
         "estado_REAL": 0, "estado_SIMULADO": 0, "handoff_pos": 0,
         "volta_ao_corredor": 0, "humanos_por_desenho": 0,
         "humanos_sem_estado": 0,
         "resolvido_sem_humano": 0, "resolvido_pelo_agente": 0,
         "para_humano": 0, "para_humano_sem_dossie": 0,
         "por_rotulo": {}, "teto": TETO}

    agente_simulado = 0
    for turno in lista:
        chave = str(turno.get("conversa") or turno.get("conversation_id") or "")
        if chave in descartadas:
            # ⛔ R11: nunca vira carta, nunca entra no denominador — e é CONTADO.
            r["descartados"] += 1
            continue

        rotulo = classificar_turno(turno.get("mensagens") or [])
        r["por_rotulo"][rotulo] = int(r["por_rotulo"].get(rotulo) or 0) + 1
        if rotulo in SEM_INTENCAO:
            continue
        r["denominador"] += 1

        humano_por_desenho = vai_para_humano(rotulo)
        if humano_por_desenho:
            r["humanos_por_desenho"] += 1
            if rotulo not in ROTULOS_DE_ESTADO:
                r["humanos_sem_estado"] += 1
        # ⚠️ Uma carta NÃO resolve o que é humano por desenho. C6 existe para o
        #    prestador que não chegou — mas ela é o que o agente DIZ enquanto
        #    passa o caso, não um substituto da pessoa (R9).
        carta = None if humano_por_desenho else mapa.get(rotulo)

        estado_simulado = rotulo in ROTULOS_DE_ESTADO
        estado_real = bool(estado_simulado and turno.get("espera_ativa"))
        if carta:
            r["resolvido_por_carta"] += 1
        if estado_real:
            r["estado_REAL"] += 1
        if estado_simulado:
            r["estado_SIMULADO"] += 1

        sem_humano = bool(carta) or estado_real
        sem_humano_sim = bool(carta) or estado_simulado
        if sem_humano:
            r["resolvido_sem_humano"] += 1

        # 🔴 QUEM DECIDE SE É HANDOFF É A R9 (`SITUACOES_PARA_HUMANO`), E O
        #    MOTOR DO DOSSIÊ DECIDE SE ELE CONTA.
        #
        # ⛔ `I` (abrir um caso NOVO no mesmo fio) tem dossê completo e mesmo
        #    assim NÃO é handoff: a R9 o manda de volta ao corredor de
        #    acionamento, e contá-lo como "resolvido pelo agente" seria carimbar
        #    de resolvido um caso que ainda nem começou.
        #
        # ⚠️ E ele também não é "foi para humano": tem linha PRÓPRIA. Um número
        #    que não cabe em nenhuma das duas colunas e mesmo assim é somado a
        #    uma delas é como se inventa 3,6 pontos.
        handoff = humano_por_desenho and _dossie_completo(turno)
        if handoff:
            r["handoff_pos"] += 1
        if rotulo == "I":
            r["volta_ao_corredor"] += 1
        if sem_humano or handoff:
            r["resolvido_pelo_agente"] += 1
        elif humano_por_desenho:
            r["para_humano_sem_dossie"] += 1
        if sem_humano_sim or handoff:
            agente_simulado += 1

    r["para_humano"] = r["denominador"] - r["resolvido_pelo_agente"]
    base = r["denominador"] or 1
    r["pct_real"] = round(100.0 * r["resolvido_pelo_agente"] / base, 1)
    r["pct_simulado"] = round(100.0 * agente_simulado / base, 1)
    r["pct_sem_humano"] = round(100.0 * r["resolvido_sem_humano"] / base, 1)

    # 🔴 O TETO, CALCULADO AO VIVO E NA UNIDADE DESTA CORRIDA.
    #
    # ⚠️ Achado da lente DADO+verdade: `TETO` é uma CONSTANTE copiada do
    # relatório, e o relatório contou **mensagens**, não turnos. Publicar 94,7 %
    # ao lado de um denominador de TURNOS é comparar duas réguas diferentes e
    # chamar a diferença de resultado (§12.1). As duas ficam impressas, cada uma
    # com a sua unidade dita em voz alta.
    r["teto_vivo"] = {
        "com_J": round(100.0 * (base - r["humanos_sem_estado"]) / base, 1),
        "sem_J": round(100.0 * (base - r["humanos_por_desenho"]) / base, 1),
        "unidade": "TURNOS desta corrida (denominador=%d)" % r["denominador"],
    }
    return r


# ===========================================================================
# O ACERVO — só SELECT, zero PII na saída
#
# 📊 A regra de reconhecimento do acionamento é a do `reality-report-0971.md`
# §0.4, e ela foi medida em **Postgres**. ⚠️ CLAUDE.md §9.4: um padrão medido
# com um motor e aplicado com outro é um padrão sobre outra coisa — por isso
# aqui a normalização é a MESMA (`_norm`: minúsculas + acentos removidos, o
# `translate` do SQL) e todo `.` roda com `re.S`, porque no Postgres o ponto
# casa `\n` e em Python NÃO casa.
# ===========================================================================

TENANTS = (
    ("Resulta Seguros", "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab", r"^\+?55?48"),
    ("AutoFleet", "6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a", None),
)

_T0 = re.compile(
    r"protocolo[^a-z0-9]{0,12}[a-z]?[0-9]{5,}"
    r"|segue o protocolo|protocolo:|aqui esta seu protocolo"
    r"|foi acionad|acionamos|acionei o|abrimos o (sinistro|atendimento|chamado)"
    r"|sinistro (foi )?(aberto|registrado)"
    r"|agendamento confirmado|atendimento foi agendado|servico (foi )?agendado"
    r"|previsao de ate [0-9]+ *(min|hora)|estamos buscando um prestador"
    r"|prestador (ja )?(esta|foi) (a caminho|em deslocamento|designado)"
    r"|aguarde a chegada do prestador", re.S)


def _turnos_da_conversa(mensagens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R1 — a rajada do cliente sem resposta no meio vira UM turno."""
    t0 = None
    for m in mensagens:
        if str(m.get("role")) == "assistant" and _T0.search(_norm(m.get("content"))):
            t0 = str(m.get("created_at") or "")
            break
    if t0 is None:
        return []
    turnos: List[Dict[str, Any]] = []
    rajada: List[str] = []
    quando = ""
    for m in mensagens:
        if str(m.get("created_at") or "") <= t0:
            continue
        if str(m.get("role")) == "user":
            rajada.append(str(m.get("content") or ""))
            quando = str(m.get("created_at") or "") or quando
        elif rajada:
            turnos.append({"mensagens": list(rajada), "em": quando})
            rajada = []
    if rajada:
        turnos.append({"mensagens": list(rajada), "em": quando})
    return turnos


#: 🔴 O CORPUS MEDIDO na última corrida do acervo — preenchido por
#: `_ler_acervo` e impresso em voz alta. ⚠️ Achado da lente DADO+verdade: os 📊
#: do BLOCO 0 do relatório **não reproduzem** por aqui, e um número que não
#: reproduz precisa ser mostrado com a régua que o produziu, nunca escondido.
CORPUS: Dict[str, Any] = {"conversas": 0, "com_t0": 0, "msgs_do_cliente": 0,
                          "turnos": 0}

#: 📊 Quantas conversas de cada corretora têm espera ATIVA no banco. Preenchido
#: por `_ler_acervo`. ⚠️ Fica impresso mesmo (e principalmente) quando é zero:
#: é ele que distingue *"o motor não produz"* de *"o motor não tem o que ler"*.
ESPERAS_REAIS: Dict[str, int] = {}


def _espera_sintetica(turno: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """💭 A espera que a U1 ESCREVERIA para este caso — **ilustrativa** (§12.1).

    ⛔ Ela NUNCA entra na linha REAL. Existe só para responder a pergunta do
    Founder — *"quando a U1 estiver escrevendo, o número chega à meta?"* — e
    aparece na saída com o 💭 colado, porque um número projetado citado como
    medido é o defeito que a §12.1 nomeia.

    A data é a do TURNO REAL: o que é imaginado aqui é a LINHA em `work_waits`,
    não o acervo.
    """
    caso = (turno or {}).get("caso")
    if not isinstance(caso, dict) or not caso:
        return None
    return {"id": "projetada", "company_id": caso.get("company_id"),
            "conversation_id": caso.get("id"),
            "kind": "esperando_seguradora", "scope": "pos_acionamento",
            "status": "ativo", "vence_em": None,
            "created_at": str((turno or {}).get("em") or "")}


def _com_espera_sintetica(turnos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A MESMA lista de turnos, cada um com a 💭 espera projetada.

    ⚠️ **Só a espera do DOSSIÊ muda.** `espera_ativa` (o termo do ESTADO)
    continua como o banco o entregou: quem projeta o estado é `pct_simulado`,
    que já existe. Mexer nos dois de uma vez faria dois fatores mudarem na
    mesma linha, e aí nenhum dos dois responderia por nada (§9.2).
    """
    saida = []
    for turno in turnos:
        espera = _espera_sintetica(turno)
        saida.append(dict(turno, espera_do_caso=espera) if espera else dict(turno))
    return saida

#: A regra de corte da rajada (R1), escrita para poder ser conferida.
REGRA_DA_RAJADA = ("mensagens `user` consecutivas depois do t0, sem linha do "
                   "assistente no meio, viram UM turno; a resposta do "
                   "assistente fecha a rajada")


def _ler_acervo() -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    cliente = get_supabase_client().client
    turnos: List[Dict[str, Any]] = []
    CORPUS.update({"conversas": 0, "com_t0": 0, "msgs_do_cliente": 0, "turnos": 0})
    for nome, empresa, filtro_fone in TENANTS:
        # 🔴 [J-3]: a CONVERSA INTEIRA, porque é ela o `caso` que o motor do
        #    dossiê lê. `ficha_atendimento` e `user_name` não são enfeite: são
        #    o que decide o título, o serviço e a apólice na tela da atendente.
        #    ⛔ Só SELECT, e nenhum campo de conteúdo entra na saída (zero PII).
        conversas = (cliente.table("conversations")
                     .select("id, company_id, session_id, user_name, user_phone, "
                             "ficha_atendimento, last_message_preview, "
                             "claimed_by_name")
                     .eq("company_id", empresa).limit(2000).execute().data or [])
        # 🔴 A ESPERA REAL, se houver. 📊 06/09/2026 são ZERO em toda a tabela —
        #    e a régua diz isso em voz alta em vez de simular o que não houve.
        esperas_por_conversa: Dict[str, Dict[str, Any]] = {}
        try:
            for linha in (cliente.table("work_waits")
                          .select("id, company_id, conversation_id, kind, scope, "
                                  "status, vence_em, created_at")
                          .eq("company_id", empresa).eq("status", "ativo")
                          .limit(2000).execute().data or []):
                chave_w = str(linha.get("conversation_id") or "")
                if chave_w and chave_w not in esperas_por_conversa:
                    esperas_por_conversa[chave_w] = linha
        except Exception:  # noqa: BLE001
            esperas_por_conversa = {}
        ESPERAS_REAIS[nome] = len(esperas_por_conversa)
        if filtro_fone:
            padrao = re.compile(filtro_fone)
            conversas = [c for c in conversas
                         if padrao.search(str(c.get("user_phone") or ""))]
        CORPUS["conversas"] += len(conversas)
        for conversa in conversas:
            msgs = (cliente.table("messages")
                    .select("role, content, created_at")
                    .eq("conversation_id", conversa["id"])
                    .order("created_at").limit(1000).execute().data or [])
            reconstruidos = _turnos_da_conversa(msgs)
            if reconstruidos:
                CORPUS["com_t0"] += 1
                CORPUS["msgs_do_cliente"] += sum(
                    len(t.get("mensagens") or []) for t in reconstruidos)
            espera_real = esperas_por_conversa.get(str(conversa["id"]))
            for i, turno in enumerate(reconstruidos):
                turno["conversa"] = "%s:%s" % (nome[:3].lower(), conversa["id"])
                # ⛔ `espera_ativa` sai do BANCO, e hoje é FALSO no acervo
                #    inteiro — 📊 `work_waits` tem zero linhas ativas (E10). A
                #    régua lê a tabela e diz o que achou; ela não simula.
                turno["espera_ativa"] = bool(espera_real)
                turno["caso"] = dict(conversa)
                turno["espera_do_caso"] = dict(espera_real) if espera_real else None
                turnos.append(turno)
    CORPUS["turnos"] = len(turnos)
    return turnos


def _imprimir(rotulo: str, r: Dict[str, Any]) -> None:
    print("")
    print("  %s" % rotulo)
    print("  " + "-" * 68)
    print("  denominador (turnos com intenção) ....... %5d" % r["denominador"])
    print("  descartados por R11 (pessoal/colega) .... %5d" % r["descartados"])
    print("  resolvido_por_carta ..................... %5d" % r["resolvido_por_carta"])
    print("  estado_REAL   (espera escrita) .......... %5d   📊 hoje ZERO no acervo (E10)"
          % r["estado_REAL"])
    print("  estado_SIMULADO (💭 se a U1 já rodasse) .. %5d" % r["estado_SIMULADO"])
    print("  handoff PÓS com dossiê completo ......... %5d" % r["handoff_pos"])
    print("  volta ao corredor (`I`: caso NOVO) ...... %5d   ⚠️ nem resolvido, "
          "nem humano" % r["volta_ao_corredor"])
    print("  para_humano_sem_dossie .................. %5d" % r["para_humano_sem_dossie"])
    print("  para_humano (o que sobra) ............... %5d" % r["para_humano"])
    print("  " + "-" * 68)
    print("  resolvido_pelo_agente ................... %5d   %5.1f %%"
          % (r["resolvido_pelo_agente"], r["pct_real"]))
    print("  resolvido_sem_humano .................... %5d   %5.1f %%"
          % (r["resolvido_sem_humano"], r["pct_sem_humano"]))
    print("  💭 PROJETADO (com a U1 escrevendo a espera) %5.1f %%"
          % r["pct_simulado"])
    vivo = r.get("teto_vivo") or {}
    print("  📊 teto CALCULADO nesta corrida: %.1f %% (com J) · %.1f %% (sem J)"
          % (vivo.get("com_J") or 0.0, vivo.get("sem_J") or 0.0))
    print("     unidade: %s · humanos por desenho=%d"
          % (vivo.get("unidade") or "?", r.get("humanos_por_desenho") or 0))
    print("  📊 teto do RELATÓRIO: %.1f %% (com J) · %.1f %% (sem J)"
          % (r["teto"]["com_J"], r["teto"]["sem_J"]))
    print("     unidade: 283 MENSAGENS com intenção — o relatório contou MENSAGEM")
    print("     e esta régua conta TURNO: as duas não se comparam direto (§12.1)")
    # 🔴 [6] do red team: o teto publicado (94,7 %) é MENOR que a meta do
    #    Founder (95 %). Publicar os dois sem dizer isso é deixar o leitor
    #    concluir que "faltaram 3,6 pontos" — quando a distância é de DESENHO.
    #    ⛔ Nenhuma linha desta saída carimba "meta atingida".
    projetado = float(r.get("pct_simulado") or 0.0)
    if projetado < META_DO_FOUNDER:
        print("  ⛔ o PROJETADO (%.1f %%) NÃO alcança a meta de %.1f %% (§7.1) — "
              "faltam %.1f pontos" % (projetado, META_DO_FOUNDER,
                                      META_DO_FOUNDER - projetado))
    if r["teto"]["com_J"] < META_DO_FOUNDER:
        print("  ⛔ e o TETO da taxonomia medida é %.1f %%: a meta de %.1f %% é "
              "INALCANÇÁVEL pelo caminho sem humano, não é uma diferença de "
              "esforço (E8)" % (r["teto"]["com_J"], META_DO_FOUNDER))


def _sem_situacoes_humanas(turnos: List[Dict[str, Any]]) -> int:
    """A MESMA medição com `SITUACOES_PARA_HUMANO` vazia — a linha de CONTROLE.

    🔴 Se `handoff_pos` não cair aqui, ele não estava contando handoff: estava
    contando qualquer coisa. ⚠️ O dicionário é restaurado no `finally`, sempre —
    a régua não pode deixar o produto alterado atrás de si.
    """
    from app.atendimento import pos_acionamento as PA

    guardado = dict(PA.SITUACOES_PARA_HUMANO)
    try:
        PA.SITUACOES_PARA_HUMANO.clear()
        return int(medir(turnos).get("handoff_pos") or 0)
    finally:
        PA.SITUACOES_PARA_HUMANO.update(guardado)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    print("=" * 72)
    print("  A RÉGUA DO PÓS-ACIONAMENTO — SPEC-097.1 U4/R8")
    print("=" * 72)

    if "--fixture" in argv:
        caminho = os.path.join(RAIZ, "tests", "fixtures", "turnos_0971.json")
        bruto = json.load(io.open(caminho, encoding="utf-8"))
        turnos = [t for t in bruto if isinstance(t, dict) and "turno" in t]
        origem = "FIXTURE 💭 sintética (%s)" % os.path.basename(caminho)
    else:
        try:
            turnos = _ler_acervo()
            origem = "📊 ACERVO REAL (Resulta/DDD-48 + AutoFleet), só SELECT"
        except Exception as erro:  # noqa: BLE001
            print("\n  ⛔ o acervo não pôde ser lido: %s: %s"
                  % (type(erro).__name__, erro))
            print("     (rode com `--fixture` para medir sem banco)")
            return 2

    print("\n  origem: %s" % origem)
    print("  turnos reconstruídos: %d" % len(turnos))
    if CORPUS.get("conversas"):
        # 🔴 O CORPUS, EM VOZ ALTA — e a comparação com o relatório, escrita.
        #    ⚠️ Achado da lente DADO+verdade: o BLOCO 0 do relatório mediu em
        #    Postgres (`translate(lower(...))`, `~`) e esta régua mede em Python
        #    sobre `_norm`. CLAUDE.md §9.4: um padrão medido num motor e
        #    aplicado noutro é um padrão sobre outra coisa — então os dois
        #    números ficam lado a lado e a diferença NÃO é forçada.
        print("  " + "-" * 68)
        print("  📊 CORPUS desta corrida (Python sobre `_norm`)")
        print("     conversas varridas .................... %5d"
              % CORPUS["conversas"])
        print("     com acionamento reconhecido (t0) ...... %5d   (relatório §0: 36)"
              % CORPUS["com_t0"])
        print("     mensagens do cliente depois do t0 ..... %5d   (relatório §0: 1.088)"
              % CORPUS["msgs_do_cliente"])
        print("     turnos reconstruídos .................. %5d   (relatório §2: 542)"
              % CORPUS["turnos"])
        print("     regra da rajada: %s" % REGRA_DA_RAJADA)
        if CORPUS["msgs_do_cliente"] != 1088:
            print("     ⚠️ o corpus NÃO reproduz o do relatório: as CONVERSAS batem")
            print("        e as MENSAGENS não. A régua publica o que ELA mediu —")
            print("        forçar o número seria inventar o dado (§12.1).")
    completo = medir(turnos)
    _imprimir("COM AS CARTAS", completo)
    _imprimir("🔴 CONTROLE — a MESMA passada com o mapa de cartas VAZIO",
              medir(turnos, mapa={}))

    # 🔴 A LINHA PROJETADA (💭) — a pergunta do Founder, com a marca colada.
    #
    # ⚠️ 📊 `handoff_pos` REAL é o que o motor produz com o que ESTÁ ESCRITO
    # hoje; o PROJETADO é o mesmo motor com a espera que a U1 escreveria. Os
    # dois ficam impressos SEPARADOS porque somá-los seria publicar uma
    # projeção com cara de medição (§12.1).
    projetados = _com_espera_sintetica(turnos)
    projetado = medir(projetados)
    _imprimir("💭 PROJETADO — a MESMA passada com a espera que a U1 escreveria",
              projetado)

    # 🔴 OS DOIS CONTROLES DO HANDOFF (R8) — §9.2/§9.5.
    #
    # `handoff_pos` sai do MOTOR do dossiê. Um número que sobe sozinho não prova
    # nada; o que dá direito à conclusão é ele CAIR quando se tira a causa.
    sem_estado = medir(projetados, com_estado=False)
    sem_humanos = _sem_situacoes_humanas(projetados)
    print("")
    print("  🔴 CONTROLE do handoff PÓS — `handoff_pos` sai do MOTOR do dossiê")
    print("  " + "-" * 68)
    if ESPERAS_REAIS:
        print("  📊 conversas com espera ATIVA no banco: %s"
              % ", ".join("%s=%d" % (k, v) for k, v in sorted(ESPERAS_REAIS.items())))
    print("  📊 handoff_pos REAL (a espera que ESTÁ escrita) %5d" % completo["handoff_pos"])
    print("  💭 handoff_pos PROJETADO (espera sintética) ... %5d" % projetado["handoff_pos"])
    print("  SEM estado: o motor diz 'não há espera registrada' %2d   %s"
          % (sem_estado["handoff_pos"],
             "OK" if sem_estado["handoff_pos"] < projetado["handoff_pos"]
             else "⛔ o guarda NÃO sabe reprovar"))
    print("  com `SITUACOES_PARA_HUMANO` VAZIA ............. %5d   %s"
          % (sem_humanos,
             "OK" if sem_humanos < projetado["handoff_pos"]
             else "⛔ o guarda NÃO sabe reprovar"))
    print("\n  ⚠️ O controle é o que dá direito à conclusão: se o número não cai")
    print("     sem as cartas, não foram elas que resolveram (CLAUDE.md §9.2).")
    print("  ⛔ Zero PII: esta saída só tem CONTAGENS.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
