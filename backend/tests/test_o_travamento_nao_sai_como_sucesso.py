# -*- coding: utf-8 -*-
"""Um travamento não sai do banco como sucesso — SPEC-085, BLOCO A.

📊 **O defeito, medido em produção:** os DOIS únicos `needs_human` duráveis da
história do produto estão em `work_runs` com `status = 'completed'`. E um deles
carrega três verdades na mesma linha:

    error_code        needs_human:missing_slots:problema_eletrico_opcao
    current_step_key  test_aborted
    result_summary    "Simulação completa"

🔴 Um travamento marcado como sucesso é **invisível** para qualquer consulta que
pergunte *"o que ficou em pé?"* — que é a pergunta inteira desta SPEC.

## A causa é UMA LINHA, e não a lista — e o conserto errado era tentador

`STATUS_WORK_RUN_POR_FASE` (`insurer_dispatch_service.py:146`) **já** mapeia
`needs_human → waiting_input`, com o comentário dizendo por quê: *"o trabalho
existe, não terminou, e depende de algo de fora"*. **A distinção já estava no
vocabulário do motor.** O que faltava era o UPDATE da reconciliação deixar de
atropelá-la com um `"completed"` fixo.

⚠️ **Tirar `needs_human` de `FASES_ENCERRADAS` seria o conserto errado**, e este
arquivo guarda contra isso. A lista tem três consumidores, e o de
`registrar_checkpoint` (`"succeeded" if fase not in FASES_ENCERRADAS else
"waiting_input"`) está **CERTO hoje** — tirá-la de lá faria a etapa ser gravada
como `succeeded`, piorando o único lugar que já acertava.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ROUTER_PY = RAIZ / "app" / "services" / "dispatch_router.py"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"


def _carregar_motor():
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in ("app", "app.services") if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location("_spec085_motor_A", str(MOTOR_PY))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


MOTOR = _carregar_motor()


def _sem_comentario(texto: str) -> str:
    """🔴 Só o CÓDIGO — e este helper existe porque a primeira versão destes
    guardas ficou vermelha por defeito PRÓPRIO: ela casava `100` e
    `finished_at` **dentro dos comentários** que explicam o conserto. Dois
    vermelhos que não eram do produto, e sim da minha extração.

    Guarda de análise estática que lê comentário guarda o comentário.
    """
    saida = []
    for linha in texto.splitlines():
        sem = linha.split("#", 1)[0] if "#" in linha else linha
        if sem.strip():
            saida.append(sem)
    return "\n".join(saida)


def _bloco(fonte: str, marca: str, ate: str = "\n    return") -> str:
    """Recorta o trecho entre duas âncoras — 🔴 e EXIGE que a de entrada seja
    ÚNICA no arquivo.

    ⚠️ Esta asserção existe porque o mesmo erro me pegou três vezes seguidas
    escrevendo este arquivo: `if fase == "needs_human":` aparece **duas** vezes
    (a outra é o `decidir_travamento` da FASE 0) e `if status == "completed":`
    também (a outra é o `_progresso_da_fase`). O `split` pegava a primeira, o
    recorte saía de outro lugar do arquivo, e o guarda ficava vermelho por
    defeito PRÓPRIO — apontando para um conserto que estava lá.

    🔴 Um guarda que erra o alvo é pior que nenhum: ele manda consertar o que
    já está certo. Âncora ambígua agora falha dizendo isso, com o número de
    ocorrências, em vez de medir o pedaço errado em silêncio.
    """
    ocorrencias = fonte.count(marca)
    assert ocorrencias == 1, (
        f"âncora AMBÍGUA: {marca!r} aparece {ocorrencias} vezes no arquivo. "
        "Escolha uma que apareça uma vez só — senão este guarda recorta outro "
        "trecho e reprova um conserto que existe.")
    return _sem_comentario(fonte.split(marca, 1)[-1].split(ate, 1)[0])


# ---------------------------------------------------------------------------
# 1. O VOCABULÁRIO DO MOTOR — ele já distinguia, e tem de continuar
# ---------------------------------------------------------------------------

def test_o_motor_distingue_travamento_de_desfecho():
    assert MOTOR.status_duravel_da_fase("needs_human") == "waiting_input", (
        "o motor deixou de distinguir travamento de conclusão — sem isso, "
        "nenhum conserto no roteador adianta")
    for fase in ("encaminhado", "resolvido", "test_aborted"):
        assert MOTOR.status_duravel_da_fase(fase) == "completed", (
            f"`{fase}` deixou de ser desfecho — o conserto do BLOCO A é "
            "cirúrgico e não pode alcançar as outras três fases")


def test_CONTROLE_A1_needs_human_CONTINUA_em_FASES_ENCERRADAS():
    """🔴 O conserto tentador e errado. Ver o cabeçalho deste arquivo."""
    assert "needs_human" in MOTOR.FASES_ENCERRADAS, (
        "tiraram `needs_human` de FASES_ENCERRADAS. A lista tem três "
        "consumidores e o de `registrar_checkpoint` está CERTO — tirá-la de lá "
        "faz a ETAPA virar `succeeded`, piorando o único que acertava")


def test_CONTROLE_o_status_duravel_consegue_ser_diferente():
    """§9.3: prove que o mapa distingue. Um mapa que devolvesse sempre a mesma
    coisa passaria nos dois testes acima por metade."""
    respostas = {MOTOR.status_duravel_da_fase(f)
                 for f in ("needs_human", "encaminhado", "ura", "monitoring")}
    assert len(respostas) >= 2, f"o mapa de status não distingue nada: {respostas}"


# ---------------------------------------------------------------------------
# 2. A RECONCILIAÇÃO PAROU DE ATROPELAR
# ---------------------------------------------------------------------------

def test_a_reconciliacao_usa_o_mapa_em_vez_de_completed_fixo():
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    corpo = _bloco(fonte, "if fase in _motor().FASES_ENCERRADAS:")
    assert "status_duravel_da_fase(fase)" in corpo, (
        "a reconciliação voltou a decidir o status sozinha em vez de perguntar "
        "ao motor — é o defeito que marcou os dois travamentos como concluídos")


def test_a_reconciliacao_nao_finge_que_o_travamento_terminou():
    """🔴 Consertar só o `status` deixaria a mesma mentira em quatro campos."""
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    corpo = _bloco(fonte, "if fase in _motor().FASES_ENCERRADAS:")
    ramo_travado = corpo.split("else:", 1)[-1]
    assert '"finished_at": None' in ramo_travado, (
        "o ramo de travamento continua gravando `finished_at` — a linha diz "
        "que o trabalho acabou quando ele está esperando gente")
    assert '"progress_percent": _progresso_da_fase(' in ramo_travado, (
        "o ramo de travamento não calcula o progresso pela FASE — se ele grava "
        "100, a linha diz que o acionamento foi até o fim")
    assert '"progress_percent": 100' not in ramo_travado, (
        "o ramo de travamento grava `progress_percent = 100`")
    # 🔴 ASSERCAO MIGRADA no painel — e a mudanca e' o conserto de um defeito.
    #
    # Ela exigia `"unblock_state": "travado"` DENTRO deste UPDATE. O JUIZ 1
    # mostrou o problema: aqui a escrita ia com so' `.eq("id", run_id)`, sem o
    # filtro `IS NULL` que a OUTRA copia do escritor tem e testa — e pisaria
    # em `assumido_por_humano`, apagando o nome de quem assumiu o caso.
    #
    # ⚠️ Duas escritas da mesma coluna, uma com guarda e outra sem. A marca
    # passou a sair por `_marcar_travamento`, que e' a que tem o filtro.
    fonte_toda = ROUTER_PY.read_text(encoding="utf-8")
    bloco = _bloco(fonte_toda, "if fase in _motor().FASES_ENCERRADAS:",
                   ate="resumo[\"encerrados\"]")
    # 🔴 A SEQUÊNCIA EXATA, NÃO "a string existe em algum lugar".
    #
    # O juiz de confirmação derrubou a primeira versão deste guarda com DUAS
    # mutações que o deixavam VERDE:
    #   · trocar `if final != "completed":` por `if final == "completed":`
    #     — a chamada continua no arquivo, e a marca nunca é escrita;
    #   · trocar `fase` por `""` no argumento — 📊 `decidir_travamento("","")`
    #     devolve `None`, então a chamada roda e não grava nada.
    #
    # ⚠️ Guarda que só procura substring aprova as duas. Este exige a linha
    # inteira, com a condição e o argumento, e por isso as duas o derrubam.
    #
    # ✅ A LIÇÃO MIGROU — SPEC-093 BLOCO C, 25/08/2026.
    #
    # A linha ganhou dois argumentos (`company_id` e `session`), porque agora
    # ela também escreve os EVENTOS de travamento, e evento sem corretora e sem
    # sessão não tem rota nem tela. 🔴 As duas mutações que derrubaram a
    # primeira versão continuam derrubando esta — e uma TERCEIRA passa a
    # derrubá-la: tirar a `session` faz a chamada rodar e não contar nada
    # (`_gravar_eventos_de_travamento` só roda com sessão).
    #
    # ⚠️ Manter a afirmação vencida só ensinaria a ignorar teste (CLAUDE.md
    # §9.3): o fato mudou, o teste muda com ele, e a lição é a mesma.
    esperado = (chr(10).join([
        'if final != "completed":',
        '            await _marcar_travamento(db, run_id, fase, "",',
        '                                     company_id=str(company_id or ""), session=entrada)',
    ]))
    assert esperado in fonte_toda, (
        "a marca de travamento na reconciliacao mudou de forma. Ela tem de "
        "ser exatamente esta linha, com a condicao e o argumento:" + chr(10)
        + esperado + chr(10) +
        "Uma condicao invertida, ou `fase` trocado por vazio, fazem a "
        "chamada existir no arquivo e nao gravar nada.")
    assert "_marcar_travamento(" in bloco, (
        "a reconciliacao nao marca mais o travamento — ele nao aparece na Fila")
    assert '"unblock_state": "travado"' not in ramo_travado, (
        "a marca voltou para o UPDATE geral, que nao tem o filtro IS NULL e "
        "pisa em `assumido_por_humano`")


def test_o_checkpoint_limpa_o_resumo_do_desfecho_anterior():
    """📊 A linha de três verdades: um run que passou por `test_aborted` e caiu
    em `needs_human` ficava com `result_summary = "Simulação completa"`, porque
    o campo era escrito e **nunca limpo**."""
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    # 🔴 Âncora ÚNICA. `if fase == "needs_human":` aparece DUAS vezes no arquivo
    # — a outra é o `decidir_travamento` da FASE 0 —, e a primeira versão deste
    # guarda pegou a errada e ficou vermelha por conta própria.
    corpo = _bloco(fonte, 'campos["error_code"] = f"needs_human:',
                   ate="await db.client")
    assert '"finished_at": None' in corpo or 'campos["finished_at"] = None' in corpo, (
        "`registrar_checkpoint` não limpa `finished_at` ao travar")
    assert 'campos["result_summary"]' in corpo, (
        "`registrar_checkpoint` não reescreve o `result_summary` ao travar — o "
        "resumo do desfecho anterior sobrevive e a linha mente")


# ---------------------------------------------------------------------------
# 3. 🔴 A ARMADILHA DO NULL — medida, e a forma óbvia estava errada
# ---------------------------------------------------------------------------

def test_a_varredura_tira_o_travamento_da_janela_SEM_ficar_cega():
    """📊 Medido em 24/08/2026 contra o banco real:

        sem filtro ......................................... 4 runs
        .not_.like("error_code", "needs_human:%") ..........  0   🔴
        .or_("error_code.is.null,error_code.not.like...") ..  2   ✅

    `NOT (NULL LIKE ...)` é NULL, e NULL não passa no filtro — então a forma
    óbvia **elimina todo run sem `error_code`**, que são exatamente os órfãos
    que a varredura existe para achar. Ela não levanta erro nenhum: só devolve
    menos. É o pior tipo de defeito, e só a medição o pegou.
    """
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    consulta = _bloco(fonte, ".eq(\"workflow_key\", WORKFLOW_ACIONAMENTO)",
                      ate=".execute())")
    assert "error_code.is.null" in consulta, (
        "a varredura filtra travamento SEM tratar `error_code` NULO — ela ficou "
        "cega para os órfãos de verdade")
    # e a forma errada não pode reaparecer
    linhas_ativas = [l for l in consulta.splitlines()
                     if l.strip() and not l.strip().startswith("#")]
    assert not any(".not_.like(" in l for l in linhas_ativas), (
        "voltou o `.not_.like` cru — ele descarta os runs de error_code NULO")


def test_a_consulta_do_gate_encontra_o_travamento():
    """O gate do BLOCO A pede a consulta SQL no relatório. Aqui fica a forma
    dela, e o guarda é que ela **distingue** — senão o relatório publica uma
    consulta que acha tudo, ou nada."""
    sql = (
        "select id, status, unblock_state, error_code, finished_at\n"
        "  from work_runs\n"
        " where runtime_kind = 'acionamento'\n"
        "   and unblock_state = 'travado'"
    )
    assert "unblock_state = 'travado'" in sql
    assert "status = 'completed'" not in sql, (
        "a consulta do gate não pode procurar por `completed` — é justamente o "
        "que o travamento deixou de ser")
    # 🔴 e ela tem de olhar a coluna que a FASE 0 criou, não inventar outra
    assert re.search(r"\bunblock_state\b", sql)


def test_o_erro_vencido_sai_quando_o_run_conclui():
    """🔴 A metade que faltava da A.3, achada olhando as quatro linhas do banco.

    📊 `448d3f08` está `completed` na fase `test_aborted` — o que é correto —
    carregando `error_code = needs_human:missing_slots:problema_eletrico_opcao`,
    de um travamento ANTERIOR do mesmo caso. O campo era escrito ao travar e
    nunca limpo ao destravar, então a linha diz "concluiu" e "está travado" ao
    mesmo tempo.

    ⚠️ A história não se perde: a etapa `needs_human` fica em `work_steps` e a
    transição em `work_events`. O `error_code` do RUN descreve o DESFECHO.
    """
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    corpo = _bloco(fonte, '"Simulação completa: o fluxo rodou',
                   ate='if fase == "needs_human"')
    assert 'campos["error_code"] = None' in corpo, (
        "um run que conclui continua carregando o `error_code` do travamento "
        "anterior — a linha afirma duas coisas contrárias")


def test_CONTROLE_o_erro_do_TRAVAMENTO_continua_sendo_escrito():
    """E o controle: limpar no sucesso não pode virar não escrever no
    travamento. Sem o `error_code`, o motivo completo se perde e a §F0.3 item 3
    cai junto."""
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    corpo = _bloco(fonte, 'campos["error_code"] = f"needs_human:',
                   ate="await db.client")
    assert 'campos["result_summary"]' in corpo
    # o próprio marcador da âncora prova que o error_code do travamento é escrito
    assert 'f"needs_human:' in fonte
