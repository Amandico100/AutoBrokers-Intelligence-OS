"""SPEC-059 — Intelligence Fabric: as garantias que protegem o corretor.

Este arquivo entra no Broker Outcome Regression Pack. Cada caso aqui existe
porque a falha dele significa que **o corretor perde alguma coisa**: recebe um
alerta inventado, recebe o mesmo aviso cinco vezes, é acordado de madrugada por
um item que podia esperar, ou vê "resolvido" onde ninguém mediu nada.

Carga isolada
-------------
`app/services/__init__.py` importa LangChain, Qdrant e MinIO. Um teste de gate
que depende disso vira SKIP no primeiro ambiente enxuto — e um gate que pula
silenciosamente deixa de proteger. Aqui os pacotes são registrados como stubs
com `__path__`, e cada módulo é carregado por caminho.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
FALHAS: list[str] = []


def _pacote(nome: str, *partes: str, executar_init: bool = False) -> None:
    """Registra o pacote sem passar pelo `__init__.py` pesado de `app.services`.

    `executar_init=True` só para pacotes cujo `__init__` carrega conteúdo real
    (o registro de detectores, por exemplo) e não arrasta dependência externa.
    """
    if nome in sys.modules:
        return
    caminho = os.path.join(RAIZ, *partes)
    m = types.ModuleType(nome)
    m.__path__ = [caminho]
    m.__package__ = nome
    sys.modules[nome] = m
    if executar_init:
        init = os.path.join(caminho, "__init__.py")
        spec = importlib.util.spec_from_file_location(
            nome, init, submodule_search_locations=[caminho])
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nome] = modulo
        spec.loader.exec_module(modulo)


for _nome, _partes, _init in (
    ("app", ("app",), False),
    ("app.services", ("app", "services"), False),
    ("app.services.intelligence", ("app", "services", "intelligence"), False),
    ("app.services.auxiliaries", ("app", "services", "auxiliaries"), False),
    ("app.services.intelligence.detectors",
     ("app", "services", "intelligence", "detectors"), True),
):
    _pacote(_nome, *_partes, executar_init=_init)


def carregar(nome: str):
    if nome in sys.modules and hasattr(sys.modules[nome], "__file__"):
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


AGORA = datetime(2026, 7, 26, 14, 0, tzinfo=timezone.utc)
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"


# ==========================================================================

def teste_evidencia_obrigatoria():
    print("\n[1] Nenhum alerta existe sem evidência")
    s = carregar("app.services.intelligence.schemas")

    sem_evidencia = s.SignalDraft(
        company_id=EMPRESA_A, signal_type="approval_pending",
        subject_type="approval_queue", summary_redacted="4 aprovações paradas",
        dedupe_key="k1")
    ok, motivo = sem_evidencia.valido()
    checar(not ok, "sinal sem evidência é recusado", motivo)
    checar("evid" in motivo.lower(), "e o motivo diz o porquê", motivo)

    com_evidencia = s.SignalDraft(
        company_id=EMPRESA_A, signal_type="approval_pending",
        subject_type="approval_queue", summary_redacted="4 aprovações paradas",
        dedupe_key="k1", trust_tier=s.TIER_DADO_VIVO,
        evidencias=[s.evidencia(tipo="contagem", sistema="approval_requests",
                                ref="c:1", resumo="4 pendentes",
                                tier=s.TIER_DADO_VIVO)])
    ok, _ = com_evidencia.valido()
    checar(ok, "com evidência de dado vivo, o sinal é aceito")


def teste_critico_exige_dado_forte():
    print("\n[2] Alerta crítico nunca nasce de palpite do modelo")
    s = carregar("app.services.intelligence.schemas")
    p = carregar("app.services.intelligence.policy")

    inferencia = s.SignalDraft(
        company_id=EMPRESA_A, signal_type="attendance_quality",
        subject_type="quality", summary_redacted="a qualidade parece ter caído",
        dedupe_key="k2", severity="critical", trust_tier=s.TIER_INFERENCIA_LLM,
        evidencias=[s.evidencia(tipo="hipotese", sistema="llm", ref="-",
                                resumo="parece", tier=s.TIER_INFERENCIA_LLM)])
    ok, motivo = inferencia.valido()
    checar(not ok, "sinal crítico apoiado em Tier 5 é recusado", motivo)

    d = p.pode_alertar_como_critico(trust_tier=s.TIER_INFERENCIA_LLM,
                                    evidencias=3, signal_type="attendance_quality")
    checar(not d.permitido, "a policy também recusa alerta crítico Tier 5", d.motivo)

    d2 = p.pode_alertar_como_critico(trust_tier=s.TIER_DADO_VIVO, evidencias=1,
                                     signal_type="connection_health")
    checar(d2.permitido, "dado vivo com evidência sustenta alerta crítico")

    checar(not s.pode_ser_apresentado_como_fato(s.TIER_DECLARACAO),
           "declaração do corretor não é apresentada como fato")
    checar(s.pode_ser_apresentado_como_fato(s.TIER_ANALISE),
           "análise derivada reproduzível sustenta fato")


def teste_prioridade_explicavel():
    print("\n[3] A prioridade é uma conta que dá para mostrar")
    prio = carregar("app.services.intelligence.priority_service")

    alto = prio.Dimensoes(impacto=90, urgencia=90, confianca=100,
                          actionability=90, recorrencia=80, freshness=100,
                          alinhamento=80)
    score = prio.calcular(alto)
    checar(score >= 85, "quadro grave pontua alto", f"score={score}")
    checar(prio.nivel(score, risco_critico=False) == "P1",
           "score alto SEM risco crítico não vira P0",
           f"nível={prio.nivel(score, risco_critico=False)}")
    checar(prio.nivel(score, risco_critico=True) == "P0",
           "com risco crítico satisfeito, vira P0")

    com_penalidade = prio.calcular(alto, ["dispensado_recentemente"])
    checar(com_penalidade < score,
           "dispensar recentemente derruba a prioridade",
           f"{score} -> {com_penalidade}")

    checar(prio.urgencia_por_prazo(None) > 0,
           "prazo desconhecido NÃO vira urgência zero (lei 4)",
           f"urgência={prio.urgencia_por_prazo(None)}")
    checar(prio.urgencia_por_prazo(0) == 100.0, "prazo vencido é urgência máxima")
    checar(prio.freshness_por_idade(24, 24) < prio.freshness_por_idade(1, 24),
           "oportunidade velha perde força para a de hoje")

    explicacao = prio.resumo_explicavel(alto, ["repeticao"], com_penalidade)
    checar("dimensoes" in explicacao and "penalidades" in explicacao,
           "a explicação carrega as parcelas da conta")


def teste_nao_repete_o_mesmo_aviso():
    print("\n[4] O corretor não recebe o mesmo aviso todo dia")
    d = carregar("app.services.intelligence.dedupe_service")

    estado = d.EstadoDeEntrega(
        ultima_entrega_em=AGORA - timedelta(hours=2),
        prioridade_na_ultima_entrega=70.0)
    r = d.pode_repetir(estado, prioridade_atual=71.0, agora=AGORA)
    checar(not r.repetir, "dentro da janela de silêncio, não repete", r.motivo)

    r2 = d.pode_repetir(estado, prioridade_atual=71.0, agora=AGORA,
                        provider_voltou_a_falhar=True)
    checar(r2.repetir and r2.escalonamento,
           "provider que voltou a falhar FURA o silêncio (§11.4)", r2.motivo)

    r3 = d.pode_repetir(estado, prioridade_atual=90.0, agora=AGORA)
    checar(r3.repetir and r3.escalonamento,
           "salto grande de prioridade também escala",
           f"delta={r3.detalhes.get('delta_prioridade')}")

    dispensado = d.EstadoDeEntrega(dispensado_em=AGORA - timedelta(days=1))
    r4 = d.pode_repetir(dispensado, prioridade_atual=60.0, agora=AGORA)
    checar(not r4.repetir, "assunto dispensado fica em silêncio por dias", r4.motivo)

    resolvido = d.EstadoDeEntrega(resolvido=True)
    checar(not d.pode_repetir(resolvido, prioridade_atual=95.0, agora=AGORA).repetir,
           "problema resolvido não volta nem com prioridade alta")

    em_andamento = d.EstadoDeEntrega(acao_em_andamento=True)
    checar(not d.pode_repetir(em_andamento, prioridade_atual=80.0, agora=AGORA).repetir,
           "com ação em andamento, não cobra de novo")


def teste_dedupe_isola_corretoras():
    print("\n[5] A chave de dedupe nunca cruza corretoras")
    d = carregar("app.services.intelligence.dedupe_service")

    a = d.chave_de_sinal(company_id=EMPRESA_A, signal_type="work_failure",
                         subject_type="grupo", subject_id="timeout",
                         rule_key="r", rule_version="1.0.0")
    b = d.chave_de_sinal(company_id=EMPRESA_B, signal_type="work_failure",
                         subject_type="grupo", subject_id="timeout",
                         rule_key="r", rule_version="1.0.0")
    checar(a != b, "mesma falha em corretoras diferentes tem chaves diferentes")

    v1 = d.chave_de_sinal(company_id=EMPRESA_A, signal_type="work_failure",
                          subject_type="grupo", subject_id="timeout",
                          rule_key="r", rule_version="1.0.0")
    v2 = d.chave_de_sinal(company_id=EMPRESA_A, signal_type="work_failure",
                          subject_type="grupo", subject_id="timeout",
                          rule_key="r", rule_version="1.1.0")
    checar(v1 != v2,
           "mudar o limiar da regra cria observação nova, não repetição")
    checar(a == v1, "a mesma observação produz sempre a mesma chave")


def teste_quiet_hours():
    print("\n[6] Ninguém é acordado de madrugada por item que espera")
    dp = carregar("app.services.intelligence.delivery_policy")

    madrugada = datetime(2026, 7, 26, 6, 0, tzinfo=timezone.utc)   # 3h no Brasil
    comercial = datetime(2026, 7, 26, 17, 0, tzinfo=timezone.utc)  # 14h no Brasil
    checar(dp.em_quiet_hours(madrugada), "3h da manhã está na janela de silêncio")
    checar(not dp.em_quiet_hours(comercial), "14h não está")

    ctx = dp.ContextoDeEntrega(severidade="high", tem_acao_clara=True)
    r = dp.decidir(ctx, agora_utc=madrugada)
    checar(not r.push, "item alto NÃO vira push de madrugada", r.motivo)
    checar(r.adiar_para is not None, "e fica agendado para o horário útil")
    checar(r.incluir_no_briefing, "mas continua no briefing — não some")

    critico = dp.ContextoDeEntrega(severidade="critical", tem_acao_clara=True)
    checar(dp.decidir(critico, agora_utc=madrugada).push,
           "crítico atravessa o silêncio")

    sem_acao = dp.ContextoDeEntrega(severidade="high", tem_acao_clara=False)
    checar(not dp.decidir(sem_acao, agora_utc=comercial).push,
           "mensagem sem ação clara não interrompe (§15.2)")

    estourou = dp.ContextoDeEntrega(severidade="high", tem_acao_clara=True,
                                    pushes_hoje=3)
    checar(not dp.decidir(estourou, agora_utc=comercial).push,
           "o limite diário de avisos é respeitado")

    checar(dp.ajustar_cooldown_por_feedback(86400, "not_relevant")
           > dp.ajustar_cooldown_por_feedback(86400, "wrong_data"),
           "'não é relevante' silencia mais que 'o dado está errado'")


def teste_fato_separado_da_inferencia():
    print("\n[7] Inferência nunca é apresentada como fato")
    fe = carregar("app.services.intelligence.finding_engine")
    s = carregar("app.services.intelligence.schemas")

    sinal = {"id": "s1", "signal_type": "attendance_quality", "severity": "medium",
             "confidence": 0.85, "priority_score": 70, "occurrence_count": 1,
             "subject_type": "quality_window", "subject_id": "24h",
             "summary_redacted": "a nota caiu de 82 para 68", "metadata": {}}

    so_inferencia = {"s1": [{"trust_tier": s.TIER_INFERENCIA_LLM,
                             "summary_redacted": "o modelo acha que piorou"}]}
    checar(fe.compor([sinal], so_inferencia, company_id=EMPRESA_A) is None,
           "sem evidência factual, o Finding NÃO nasce")

    com_fato = {"s1": [
        {"trust_tier": s.TIER_DADO_VIVO,
         "summary_redacted": "média 68 em 12 conversas nas últimas 24h"},
        {"trust_tier": s.TIER_ANALISE, "summary_redacted": "queda de 14 pontos"}]}
    f = fe.compor([sinal], com_fato, company_id=EMPRESA_A)
    checar(f is not None, "com evidência factual, o Finding é montado")
    checar(f.fact_statement and "68" in f.fact_statement,
           "o bloco de FATO carrega o número medido", str(f.fact_statement))
    checar(f.inference_statement and f.inference_statement != f.fact_statement,
           "a leitura vem em bloco separado", str(f.inference_statement))
    checar(bool(f.missing_data), "e o que falta saber é declarado",
           str(f.missing_data))
    checar(f.why_now, "o Finding responde 'por que agora'")


def teste_resultado_nao_medido_e_inconclusivo():
    print("\n[8] Resultado não medido é inconclusivo, nunca sucesso")
    o = carregar("app.services.intelligence.outcome_service")

    m = o.avaliar(None, 3.0)
    checar(m.status == "inconclusive", "sem linha de base, inconclusivo", m.status)
    m2 = o.avaliar(5.0, None)
    checar(m2.status == "inconclusive", "sem leitura atual, inconclusivo", m2.status)

    piorou = o.avaliar(4.0, 9.0, direcao="menor_melhor")
    checar(piorou.status == "negative", "indicador que piorou é NEGATIVO",
           piorou.resumo)

    resolveu = o.avaliar(6.0, 0.0, direcao="menor_melhor")
    checar(resolveu.status == "realized", "zerou o problema: resultado confirmado",
           resolveu.resumo)

    parcial = o.avaliar(10.0, 7.0, direcao="menor_melhor")
    checar(parcial.status == "partially_realized", "melhora parcial é parcial",
           parcial.resumo)

    igual = o.avaliar(10.0, 10.0, direcao="menor_melhor")
    checar(igual.status == "inconclusive",
           "sem mudança relevante não se atribui mérito à ação", igual.resumo)

    subiu = o.avaliar(60.0, 85.0, direcao="maior_melhor")
    checar(subiu.status in ("realized", "partially_realized"),
           "em 'maior é melhor', subir é bom", subiu.resumo)


def teste_pii_nao_atravessa():
    print("\n[9] Dado de segurado não vaza para painel nem para agregado")
    r = carregar("app.services.intelligence.redaction_service")

    bruto = ("Cobrar o João, CPF 123.456.789-01, tel (48) 99156-9402, "
             "email joao@x.com.br, apólice nº 4471-XY, placa MKJ-4471")
    limpo = r.redigir(bruto)
    for vazamento in ("123.456.789-01", "99156-9402", "joao@x.com.br", "MKJ-4471"):
        checar(vazamento not in limpo, f"'{vazamento}' foi removido", limpo[:80])
    checar(r.contem_pii(bruto) and not r.contem_pii(limpo),
           "o detector de PII acusa antes e libera depois")
    rel = r.relatorio_pii(bruto)
    checar(not rel["limpo"] and rel["achados"],
           "o relatório conta o que achou, sem guardar o dado", str(rel["achados"]))


def teste_aprendizado_nao_publica_sozinho():
    print("\n[10] Nada entra no conhecimento sem alguém olhar")
    k = carregar("app.services.intelligence.knowledge_candidate_adapter")

    ok, motivo = k.elegivel(origem="feature_request",
                            texto="queria um botão de exportar planilha toda semana",
                            trust_tier=4)
    checar(not ok, "pedido de funcionalidade não vira conhecimento", motivo)

    ok2, motivo2 = k.elegivel(origem="procedimento_observado",
                              texto="o modelo acha que a seguradora mudou o fluxo",
                              trust_tier=5)
    checar(not ok2, "inferência de modelo não vira conhecimento", motivo2)

    ok3, motivo3 = k.elegivel(
        origem="mudanca_operacional_confirmada",
        texto=("A Bradesco passou a exigir o número do chassi no aviso de "
               "sinistro de automóvel a partir de julho de 2026."),
        trust_tier=2, fontes=2)
    checar(ok3, "mudança operacional confirmada por documento é elegível", motivo3)

    ok4, motivo4 = k.elegivel(
        origem="conhecimento_de_dominio_com_fonte",
        texto="O segurado João, CPF 123.456.789-01, relatou o procedimento novo",
        trust_tier=2)
    checar(not ok4, "texto com dado pessoal nunca vira candidato", motivo4)

    checar(k.classificar_risco("regra de cobertura para sinistro de vidros") == "high",
           "assunto de cobertura entra como alto risco")


def teste_demanda_global_e_anonima():
    print("\n[11] O agregado da plataforma não identifica a corretora")
    dc = carregar("app.services.intelligence.demand_cluster_service")

    h1 = dc.hash_de_tenant(EMPRESA_A)
    h2 = dc.hash_de_tenant(EMPRESA_B)
    checar(h1 != h2, "corretoras diferentes têm hashes diferentes")
    checar(h1 == dc.hash_de_tenant(EMPRESA_A), "o hash é estável para contar")
    checar(EMPRESA_A not in h1 and EMPRESA_A[:8] not in h1,
           "o id da corretora não aparece no hash", h1)

    poucas = dc.calcular_score(tenant_count=1, request_count=10)
    muitas = dc.calcular_score(tenant_count=6, request_count=10)
    checar(muitas["demand_score"] > poucas["demand_score"],
           "dez pedidos de seis corretoras valem mais que dez de uma só",
           f"{poucas['demand_score']} vs {muitas['demand_score']}")


def teste_briefing_nao_inventa():
    print("\n[12] O briefing não preenche vazio com frase bonita")
    b = carregar("app.services.intelligence.briefing_service")

    inicio, fim = AGORA - timedelta(days=1), AGORA
    vazio = b.compor(
        company_id=EMPRESA_A, briefing_type="daily_operational",
        findings=[], recomendacoes=[], trabalhos_em_curso=[], resultados=[],
        outcomes=[], faltando=["Ainda não há conversas auditadas suficientes."],
        period_start=inicio, period_end=fim)
    texto = (vazio.headline + " " + vazio.executive_summary).lower()
    checar("estável" not in texto and "estavel" not in texto,
           "sem amostra, NÃO diz que a qualidade ficou estável", texto[:90])
    checar(any("não há" in m.lower() or "ainda" in m.lower()
               for m in vazio.missing_data),
           "declara explicitamente o que não dá para afirmar")
    checar(any(i.item_type == "missing_data" for i in vazio.itens),
           "e isso aparece como item, não some")

    findings = [{"id": f"f{i}", "finding_type": "aprovacao_parada",
                 "title": f"Ponto {i}", "summary": "resumo", "why_now": "agora",
                 "severity": "high", "confidence": 0.9, "priority_score": 90 - i,
                 "metadata": {}} for i in range(12)]
    cheio = b.compor(
        company_id=EMPRESA_A, briefing_type="daily_operational",
        findings=findings, recomendacoes=[], trabalhos_em_curso=[],
        resultados=[{"id": "w1", "outcome_title": "Relatório entregue"}],
        outcomes=[], faltando=[], period_start=inicio, period_end=fim,
        max_itens=7)
    acionaveis = [i for i in cheio.itens if i.item_type == "finding"]
    checar(len(acionaveis) == 7, "o teto de itens é respeitado",
           f"{len(acionaveis)} itens")
    checar(any(i.item_type == "result" for i in cheio.itens),
           "resultado não compete com prioridade pelo teto")
    checar(acionaveis[0].priority_score >= acionaveis[-1].priority_score,
           "e a ordem é por prioridade")

    hashes = {vazio.content_hash(), cheio.content_hash()}
    checar(len(hashes) == 2, "conteúdos diferentes têm hashes diferentes")


def teste_recomendacao_so_promete_o_que_cumpre():
    print("\n[13] O botão 'Resolver' só aparece quando existe caminho")
    rs = carregar("app.services.intelligence.recommendation_service")

    finding = {"id": "f1", "company_id": EMPRESA_A, "title": "Aprovações paradas",
               "summary": "4 paradas", "why_now": "trabalho parado",
               "confidence": 0.9, "priority_score": 80, "metadata": {"quantidade": 4}}

    opcoes, chave = rs.montar_opcoes(finding, "revisar_aprovacoes",
                                     caminho_disponivel=True)
    checar(chave == "revisar_aprovacoes", "com caminho, a ação principal aparece")
    checar(any(o.key == "explicar" for o in opcoes),
           "'por que estou vendo isso' está sempre disponível (§15.5)")

    sem, chave2 = rs.montar_opcoes(finding, "propor_automacao",
                                   caminho_disponivel=False,
                                   o_que_falta="falta conectar o WhatsApp")
    checar(chave2 is None, "sem caminho, NÃO há ação recomendada")
    checar(any("WhatsApp" in (o.label or "") for o in sem),
           "e o que falta é dito com todas as letras")
    checar(all(not o.executavel for o in sem if o.key == "indisponivel"),
           "a opção indisponível não se apresenta como executável")

    plano = rs.plano_de_medicao("revisar_aprovacoes", finding)
    checar(plano["metrica"] == "aprovacoes_pendentes" and plano["baseline"] == 4,
           "a linha de base é capturada ANTES de executar (§20.2)", str(plano))
    plano_auto = rs.plano_de_medicao("propor_automacao", finding)
    checar(plano_auto["automation_level"] == "estimated",
           "tempo economizado é marcado como estimativa, nunca como fato")


def teste_detectores_deterministicos():
    print("\n[14] Os detectores contam o que existe, não o que parece")
    op = carregar("app.services.intelligence.detectors.operacao")
    q = carregar("app.services.intelligence.detectors.qualidade")

    aprovacoes = [
        {"id": "a1", "requested_at": (AGORA - timedelta(hours=48)).isoformat()},
        {"id": "a2", "requested_at": (AGORA - timedelta(hours=2)).isoformat()},
        {"id": "a3", "requested_at": (AGORA - timedelta(hours=30)).isoformat(),
         "expires_at": (AGORA - timedelta(hours=1)).isoformat()},
    ]
    paradas = op.analisar_aprovacoes(aprovacoes, AGORA, horas_minimas=24)
    ids = {p["id"] for p in paradas}
    checar(ids == {"a1"}, "só entra o que passou da janela E ainda é decidível",
           f"entraram: {sorted(ids)}")

    runs = [{"id": f"r{i}", "status": "failed", "error_code": "timeout",
             "workflow_key": "w"} for i in range(4)]
    runs += [{"id": "r9", "status": "failed", "error_code": "auth", "workflow_key": "w"}]
    grupos = op.analisar_falhas(runs, minimo=3)
    checar(len(grupos) == 1 and grupos[0]["causa"] == "timeout",
           "falhas são agrupadas por causa, e causa isolada não alerta",
           str([g["causa"] for g in grupos]))

    conversas = [
        {"id": "c1", "status": "open", "channel": "whatsapp",
         "last_message_at": (AGORA - timedelta(hours=48)).isoformat()},
        {"id": "c2", "status": "closed", "channel": "whatsapp",
         "last_message_at": (AGORA - timedelta(hours=72)).isoformat()},
        {"id": "c3", "status": "open", "channel": "whatsapp",
         "last_message_at": (AGORA - timedelta(hours=2)).isoformat()},
    ]
    paradas2 = q.analisar_paradas(conversas, AGORA, horas=24,
                                  considerar_horario_comercial=False)
    checar({p["id"] for p in paradas2} == {"c1"},
           "conversa encerrada não conta como parada",
           str([p["id"] for p in paradas2]))

    checar(op._faixa(1) != op._faixa(7),
           "a faixa de quantidade muda quando o problema muda de tamanho")
    checar(op._faixa(3) == op._faixa(5),
           "e não muda a cada item novo, para não repetir o aviso")


def teste_falsos_positivos_do_canario():
    print("\n[19] Os dois falsos positivos que o dado real revelou")
    q = carregar("app.services.intelligence.detectors.qualidade")
    cx = carregar("app.services.intelligence.detectors.conexoes")

    # ACHADO 1 — o chat do próprio corretor não é fila de atendimento.
    # Na Resulta, 18 das 20 conversas "paradas" eram conversas dele com o
    # AutoBrokers no dashboard, que ficam `active` para sempre.
    conversas = [
        {"id": "chat1", "status": "active", "channel": "web",
         "last_message_at": (AGORA - timedelta(hours=72)).isoformat()},
        {"id": "wpp1", "status": "open", "channel": "whatsapp",
         "last_message_at": (AGORA - timedelta(hours=48)).isoformat()},
        {"id": "pedido", "status": "HUMAN_REQUESTED", "channel": "web",
         "last_message_at": (AGORA - timedelta(hours=48)).isoformat()},
    ]
    paradas = q.analisar_paradas(conversas, AGORA, horas=24,
                                 considerar_horario_comercial=False)
    ids = {p["id"] for p in paradas}
    checar("chat1" not in ids,
           "conversa do corretor com o AutoBrokers NÃO é atendimento parado",
           str(sorted(ids)))
    checar("wpp1" in ids, "conversa de WhatsApp parada continua sendo detectada")
    checar("pedido" in ids,
           "mas pedido de atendimento humano entra mesmo vindo do web",
           "alguém pediu uma pessoa e ninguém veio")

    # ACHADO 2 — canal desligado de propósito não é canal quebrado.
    integracoes = [
        {"id": "velha1", "provider": "evolution", "purpose": "attendance",
         "is_active": False, "channel_status": "close"},
        {"id": "velha2", "provider": "evolution-go", "purpose": "attendance",
         "is_active": False, "channel_status": "retired"},
        {"id": "viva", "provider": "evolution-go", "purpose": "attendance",
         "is_active": True, "channel_status": "close"},
        {"id": "conectando", "provider": "evolution-go", "purpose": "observer",
         "is_active": True, "channel_status": "connecting"},
    ]
    problemas = {p["id"] for p in cx.canais_com_problema(integracoes)}
    checar(problemas == {"viva"},
           "só o canal LIGADO e caído vira alerta",
           f"detectados: {sorted(problemas)}")
    checar("velha1" not in problemas and "velha2" not in problemas,
           "canal aposentado é decisão da corretora, não defeito")
    checar("conectando" not in problemas,
           "estado de transição não vira aviso a cada reconexão")


def teste_memoria_fecha_sessao():
    print("\n[15] O AutoBrekers lembra do corretor entre conversas")
    mf = carregar("app.services.memory_fabric")

    conversas = [
        {"id": "c1", "last_message_at": (AGORA - timedelta(minutes=90)).isoformat()},
        {"id": "c2", "last_message_at": (AGORA - timedelta(minutes=5)).isoformat()},
        {"id": "c3", "last_message_at": (AGORA - timedelta(minutes=31)).isoformat()},
    ]
    encerradas = mf.sessoes_encerradas(conversas, AGORA, timeout_min=30)
    checar({c["id"] for c in encerradas} == {"c1", "c3"},
           "conversa parada há mais que o timeout é considerada encerrada",
           str([c["id"] for c in encerradas]))
    checar(encerradas[0]["id"] == "c1", "a mais antiga vem primeiro")

    checar(mf.contradiz("a corretora atende sábado pela manhã",
                        "a corretora não atende sábado pela manhã"),
           "contradição óbvia é detectada")
    checar(not mf.contradiz("a corretora atende sábado",
                            "a corretora usa a Porto Seguro"),
           "assuntos diferentes não são tratados como contradição")
    checar(mf.chave_de_memoria("Atende  SÁBADO") == mf.chave_de_memoria("atende sábado"),
           "a chave do fato ignora caixa e espaço")


def teste_evento_vira_sinal():
    print("\n[16] Evento avulso não entra no pipeline sem contrato")
    ea = carregar("app.services.intelligence.event_adapter")

    checar(ea.normalizar(event_type="inventado.qualquer", company_id=EMPRESA_A,
                         source_system="x", subject_type="y") is None,
           "tipo de evento fora do contrato é recusado")
    checar(ea.normalizar(event_type="connector.degraded", company_id=None,
                         source_system="whatsapp", subject_type="conexao") is None,
           "evento de tenant sem company_id é recusado")

    env = ea.normalizar(event_type="connector.expired", company_id=EMPRESA_A,
                        source_system="whatsapp", subject_type="conexao",
                        subject_id="i1", resumo="a conexão expirou")
    checar(env is not None, "evento válido é aceito")
    checar(env.event_id == env.dedupe_key(),
           "o evento carrega chave estável — reprocessar não duplica")

    sinal = ea.para_sinal(env)
    checar(sinal is not None and sinal.signal_type == "connection_health",
           "e vira sinal do tipo certo")
    ok, motivo = sinal.valido()
    checar(ok, "com evidência do próprio evento, o sinal é válido", motivo)


def teste_cutover_desliga_envio_direto():
    print("\n[17] Nenhum motor antigo volta a enviar por conta própria")
    la = carregar("app.services.intelligence.legacy_adapter")

    os.environ["INTELLIGENCE_CUTOVER"] = "1"
    checar(la.cutover_ligado(), "o cutover vem ligado por padrão")
    checar(la.sugestoes_desativadas() == 0, "a mensagem semanal fixa não envia")
    checar(la.relatorio_semanal_desativado() == 0, "o relatório de sábado não envia")
    checar(la.regressao_delegada() == 0, "a sentinela não dispara WhatsApp direto")

    os.environ["INTELLIGENCE_CUTOVER"] = "0"
    checar(not la.cutover_ligado(),
           "e existe caminho de rollback sem deploy")
    os.environ["INTELLIGENCE_CUTOVER"] = "1"

    contagens = {"por_categoria": {"atendimentos": 12, "qualidade": 3},
                 "dias": 7, "fonte": "agent_activities"}
    indicadores = la.indicadores_da_semana(contagens)
    checar(all(i.get("periodo") and i.get("fonte") for i in indicadores),
           "todo indicador do briefing carrega período e fonte (§24.1)",
           str(indicadores[:1]))


def teste_gates_de_dominio():
    print("\n[18] Cobertura e dinheiro nunca rodam sozinhos")
    p = carregar("app.services.intelligence.policy")

    d = p.pode_executar_sem_humano(assunto="revisar cobertura da apólice",
                                   side_effect_class="read")
    checar(d.exige_humano_responsavel,
           "assunto de cobertura exige pessoa responsável", d.motivo)

    d2 = p.pode_executar_sem_humano(assunto="enviar aviso ao cliente",
                                    side_effect_class="communication")
    checar(d2.exige_aprovacao, "comunicação externa passa por aprovação", d2.motivo)

    d3 = p.pode_executar_sem_humano(assunto="listar aprovações pendentes",
                                    side_effect_class="read", confianca=0.9)
    checar(not d3.exige_aprovacao, "leitura simples não precisa de aprovação")

    conflito = p.deve_marcar_conflito([0, 1], concordam=False)
    checar(not conflito.permitido,
           "duas fontes fortes que discordam bloqueiam ação sensível",
           conflito.motivo)
    fraco = p.deve_marcar_conflito([0, 5], concordam=False)
    checar(fraco.permitido,
           "dado vivo contra palpite do modelo não é contradição")

    checar(not p.sensibilidade_permitida("redacted", "owner"),
           "o padrão 'redigido' não abre dado sensível nem para o dono")
    checar(p.sensibilidade_permitida("allowed_for_role", "owner"),
           "e o dono só vê quando o perfil autoriza explicitamente")


# ==========================================================================

def main() -> int:
    print("=" * 68)
    print("SPEC-059 — INTELLIGENCE FABRIC")
    print("=" * 68)
    for teste in (
        teste_evidencia_obrigatoria,
        teste_critico_exige_dado_forte,
        teste_prioridade_explicavel,
        teste_nao_repete_o_mesmo_aviso,
        teste_dedupe_isola_corretoras,
        teste_quiet_hours,
        teste_fato_separado_da_inferencia,
        teste_resultado_nao_medido_e_inconclusivo,
        teste_pii_nao_atravessa,
        teste_aprendizado_nao_publica_sozinho,
        teste_demanda_global_e_anonima,
        teste_briefing_nao_inventa,
        teste_recomendacao_so_promete_o_que_cumpre,
        teste_detectores_deterministicos,
        teste_falsos_positivos_do_canario,
        teste_memoria_fecha_sessao,
        teste_evento_vira_sinal,
        teste_cutover_desliga_envio_direto,
        teste_gates_de_dominio,
    ):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} GARANTIA(S) QUEBRADA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("TODAS AS GARANTIAS VERIFICADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
