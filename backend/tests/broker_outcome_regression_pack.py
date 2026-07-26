"""Broker Outcome Regression Pack — SPEC-054 Bloco C.

Todas as SPECs de 054 a 062 referenciam este pack como gate de release.
Ele não existia como artefato executável: havia ~60 runners isolados, sem
critério comum. Um gate verde de uma SPEC não dizia nada sobre a outra.

Este é o comando único. Cada SPEC posterior adiciona seus casos AQUI.

    python backend/tests/broker_outcome_regression_pack.py
    python backend/tests/broker_outcome_regression_pack.py --suite seguranca

Regra: um caso só entra se a falha dele significar que **o corretor perdeu
alguma coisa**. Teste que não protege resultado do corretor não pertence a
este pack — pertence à suíte da sua própria SPEC.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
TESTES = os.path.join(RAIZ, "tests")


@dataclass
class Caso:
    """Um resultado que o corretor não pode perder."""

    id: str
    suite: str
    resultado_protegido: str
    spec: str
    executor: Callable[[], tuple[bool, str]]
    obrigatorio: bool = True


@dataclass
class Resultado:
    caso: Caso
    passou: bool
    detalhe: str
    segundos: float = 0.0


# ---------------------------------------------------------------------------
# Executores
# ---------------------------------------------------------------------------


def _roda_script(nome: str) -> tuple[bool, str]:
    """Executa um runner existente e devolve (passou, detalhe)."""
    caminho = os.path.join(TESTES, nome)
    if not os.path.exists(caminho):
        return False, f"runner ausente: {nome}"
    # O runner filho escreve acentuação e setas. Sem forçar UTF-8, no Windows
    # ele herda o codepage do console (cp1252), estoura UnicodeEncodeError ao
    # imprimir e sai com código 1 — e o gate acusa regressão de produto onde só
    # houve encoding de terminal. Um gate que grita lobo passa a ser ignorado,
    # que é o pior estado possível para um gate.
    ambiente = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        p = subprocess.run(
            [sys.executable, caminho], capture_output=True, text=True, timeout=300,
            cwd=RAIZ, env=ambiente, encoding="utf-8", errors="replace"
        )
    except subprocess.TimeoutExpired:
        return False, "timeout de 300s"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"

    if p.returncode == 0:
        return True, "ok"
    saida = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
    # Dependência de ambiente ausente não é regressão de produto.
    for linha in saida:
        if "ModuleNotFoundError" in linha or "ImportError" in linha:
            return False, f"SKIP_AMBIENTE: {linha.strip()[:120]}"
    return False, (saida[-1][:200] if saida else f"exit {p.returncode}")


def _carrega_isolado(caminho_rel: str, nome_modulo: str):
    """Importa um módulo por caminho, sem passar pelo pacote `app`."""
    caminho = os.path.join(RAIZ, caminho_rel)
    spec = importlib.util.spec_from_file_location(nome_modulo, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome_modulo] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def caso_egress_ssrf() -> tuple[bool, str]:
    """O agente não pode ser usado para varrer a rede interna da plataforma."""
    try:
        g = _carrega_isolado("app/core/egress_guard.py", "_pack_egress")
    except Exception as exc:  # noqa: BLE001
        return False, f"nao carregou: {type(exc).__name__}"

    pol = g.EgressPolicy.from_iterable(["api.exemplo.com"])
    proibidos = ["127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "::1", "::ffff:127.0.0.1"]
    for ip in proibidos:
        try:
            g.check_url("https://api.exemplo.com/", pol, lambda h, _ip=ip: [_ip])
            return False, f"NAO bloqueou destino interno {ip}"
        except g.EgressBlocked:
            pass
    try:
        g.check_url("https://evil.com/", pol, lambda h: ["93.184.216.34"])
        return False, "NAO bloqueou host fora da allowlist"
    except g.EgressBlocked:
        pass
    return True, f"{len(proibidos)} destinos internos + host externo bloqueados"


def caso_storage_isolamento() -> tuple[bool, str]:
    """Documento de uma corretora não pode ser lido por outra."""
    caminho = os.path.join(os.path.dirname(RAIZ), "lib", "storage", "resolver.ts")
    if not os.path.exists(caminho):
        return False, "lib/storage/resolver.ts ausente"
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    exigidos = [
        ("canAccessObject", "autorização por tenant"),
        ("ownerCompanyOf", "dono derivado do path"),
        ("isPlatformMaster", "exceção explícita de suporte"),
        ("normalizeObjectPath", "bloqueio de traversal"),
    ]
    faltando = [nome for nome, _ in exigidos if nome not in fonte]
    if faltando:
        return False, f"resolver sem: {', '.join(faltando)}"
    if "return false" not in fonte.lower():
        return False, "resolver sem negação explícita"
    return True, "resolver com autorização por tenant e bloqueio de traversal"


def caso_mcp_env() -> tuple[bool, str]:
    """Segredo da plataforma não pode vazar para subprocesso MCP."""
    caminho = os.path.join(RAIZ, "app", "services", "mcp_gateway_service.py")
    if not os.path.exists(caminho):
        return False, "mcp_gateway_service.py ausente"
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    if "_ENV_ALLOWLIST" not in fonte:
        return False, "allowlist de env ausente"
    if "env = dict(os.environ)" in fonte:
        return False, "REGRESSAO: ainda herda os.environ completo"
    return True, "ambiente do subprocesso por allowlist"


def caso_rag_global_unico() -> tuple[bool, str]:
    """Conhecimento não publicado não pode entrar no runtime."""
    caminho = os.path.join(RAIZ, "app", "services", "search_service.py")
    if not os.path.exists(caminho):
        return False, "search_service.py ausente"
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    if 'os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID"' in fonte or "_os.getenv(\"GLOBAL_KNOWLEDGE_COMPANY_ID\"" in fonte:
        return False, "REGRESSAO: segundo caminho global de LEITURA reintroduzido"
    if "build_global_search_kwargs" not in fonte:
        return False, "caminho global canônico ausente"
    return True, "um único caminho global de recuperação"


def caso_memoria_alcancavel() -> tuple[bool, str]:
    """O AutoBrokers precisa lembrar do corretor entre conversas."""
    caminho = os.path.join(RAIZ, "app", "services", "memory_service.py")
    if not os.path.exists(caminho):
        return False, "memory_service.py ausente"
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    if 'if mode == "session_end" and session_ended:' in fonte:
        return False, "REGRESSAO: condição de sumarização voltou a ser inalcançável"
    if "NO_TRIGGER" not in fonte:
        return False, "observabilidade de não disparo ausente"
    return True, "gatilho alcançável e não disparo observável"


def caso_upload_derivado_da_sessao() -> tuple[bool, str]:
    """O browser não pode escolher em qual corretora grava arquivo."""
    caminho = os.path.join(os.path.dirname(RAIZ), "app", "api", "upload", "route.ts")
    if not os.path.exists(caminho):
        return False, "app/api/upload/route.ts ausente"
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    if "resolveOwner" not in fonte:
        return False, "empresa não é derivada da sessão"
    if "rejectByMagicBytes" not in fonte:
        return False, "validação de conteúdo real ausente"
    if "getPublicUrl" in fonte:
        return False, "REGRESSAO: voltou a emitir URL pública"
    return True, "empresa da sessão + magic bytes + sem URL pública"


def caso_admin_sem_upload_anon() -> tuple[bool, str]:
    """Tela do Admin não pode gravar direto com a chave pública."""
    caminho = os.path.join(os.path.dirname(RAIZ), "app", "admin", "conversations", "page.tsx")
    if not os.path.exists(caminho):
        return False, "page.tsx ausente"
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    if "supabase.storage" in fonte:
        return False, "REGRESSAO: upload direto do browser reintroduzido"
    if "resolveMediaUrl" not in fonte:
        return False, "renderização não passa pelo resolver"
    return True, "upload server-side e leitura pelo proxy"


def caso_work_os_durabilidade() -> tuple[bool, str]:
    """Trabalho longo tem dono, batimento e retomada — não morre no restart."""
    exigidos = [
        ("app/services/work/runs.py", ["adquirir_lease", "heartbeat", "recuperar_orfaos",
                                       "liberar_lease", "cancelamento_pedido"]),
        ("app/services/work/queue.py", ["OutboxDispatcher", "claim_abandonadas", "ensure_group"]),
        ("app/services/work/effects.py", ["reserve", "EffectAlreadyExecuted",
                                          "pendentes_de_reconciliacao"]),
        ("app/services/work/approvals.py", ["validar_para_execucao", "ApprovalFingerprintMismatch",
                                            "marcar_executada"]),
        ("app/workers/smith_worker.py", ["_laco_orfaos", "_heartbeat", "_laco_dispatcher"]),
    ]
    for rel, simbolos in exigidos:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.exists(caminho):
            return False, f"ausente: {rel}"
        with open(caminho, encoding="utf-8") as fh:
            fonte = fh.read()
        faltando = [s for s in simbolos if s not in fonte]
        if faltando:
            return False, f"{rel} sem: {', '.join(faltando)}"

    # o scheduler in-process não pode voltar a ser o único caminho
    engine = os.path.join(RAIZ, "app", "services", "routine_engine.py")
    with open(engine, encoding="utf-8") as fh:
        if "_routine_bridge_enabled" not in fh.read():
            return False, "REGRESSAO: ponte de Rotinas para Work Run removida"

    return True, "lease, heartbeat, outbox, recuperação, reserva e fingerprint presentes"


def caso_efeito_grave_exige_aprovacao() -> tuple[bool, str]:
    """Enviar, comprometer ou mexer em dinheiro sempre passa pelo humano."""
    gw = os.path.join(RAIZ, "app", "services", "skills", "gateway.py")
    if not os.path.exists(gw):
        return False, "gateway.py ausente"
    with open(gw, encoding="utf-8") as fh:
        fonte = fh.read()

    # aprovação tem de ser o MAIOR entre tool, escopo e override
    if "requires_approval" not in fonte or "escopo.get(\"requires_approval\")" not in fonte:
        return False, "aprovação não considera o escopo da capability"
    if "approval_override" not in fonte:
        return False, "override da Skill não é considerado"
    # a capability precisa ser o gate
    if "if cap not in ativas" not in fonte:
        return False, "REGRESSAO: capability deixou de ser autoridade do Gateway"

    # o CHECK do banco é a última linha de defesa e precisa continuar declarado
    mig = os.path.join(RAIZ, "supabase", "migrations")
    return True, "aprovação pelo mais restritivo e capability como autoridade"


def caso_inteligencia_estrutural() -> tuple[bool, str]:
    """As garantias da SPEC-059 que precisam existir no CÓDIGO, não só passar.

    Um teste de comportamento verde não impede alguém de remover a checagem
    que o torna verde e substituí-la por outra coisa. Estes símbolos são as
    fronteiras: evidência obrigatória, tier que sustenta fato, cutover do
    envio direto e o gatilho de memória que vive fora do turno.
    """
    exigidos = [
        ("app/services/intelligence/schemas.py",
         ["sinal sem evidencia", "TIERS_QUE_SUSTENTAM_ALERTA_CRITICO",
          "pode_sustentar_alerta_critico"]),
        ("app/services/intelligence/evidence_service.py",
         ["def tier_de", "tier_dominante"]),
        ("app/services/intelligence/finding_engine.py",
         ["TIERS_QUE_SUSTENTAM_FATO", "fact_statement"]),
        ("app/services/intelligence/delivery_policy.py",
         ["em_quiet_hours", "tem_acao_clara", "SEVERIDADES_QUE_FURAM_SILENCIO"]),
        ("app/services/intelligence/dedupe_service.py",
         ["pode_repetir", "COOLDOWN_APOS_DISPENSA_SEGUNDOS"]),
        ("app/services/intelligence/outcome_service.py",
         ["inconclusive", "measured_at"]),
        ("app/services/intelligence/legacy_adapter.py", ["cutover_ligado"]),
        ("app/services/memory_fabric.py",
         ["sessoes_encerradas", "fechar_sessoes_inativas"]),
        ("app/workers/smith_worker.py",
         ["_tick_de_inteligencia", "_varrer_memoria"]),
    ]
    for rel, simbolos in exigidos:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.exists(caminho):
            return False, f"ausente: {rel}"
        with open(caminho, encoding="utf-8") as fh:
            fonte = fh.read()
        faltando = [s for s in simbolos if s not in fonte]
        if faltando:
            return False, f"{rel} sem: {', '.join(faltando)}"

    # O envio direto do legado não pode voltar a ser incondicional.
    for rel in ("app/services/proactive_suggestions.py",
                "app/services/weekly_report.py",
                "app/services/regression_sentinel.py",
                "app/services/broker_insights.py"):
        with open(os.path.join(RAIZ, rel), encoding="utf-8") as fh:
            if "cutover_ligado" not in fh.read():
                return False, f"REGRESSAO: {rel} voltou a enviar sem passar pelo cutover"

    return True, "evidência, tier, cooldown, quiet hours, outcome e cutover presentes"


def caso_pesquisa_estrutural() -> tuple[bool, str]:
    """As fronteiras da SPEC-060 que precisam existir no CÓDIGO.

    Pesquisa é a área onde o dano não aparece no teste: uma afirmação sem
    procedência passa em qualquer suíte verde e só quebra quando o corretor
    repete ao cliente. Estes símbolos são as fronteiras que sustentam a
    procedência — se sumirem, a pesquisa continua "funcionando" e deixa de
    valer alguma coisa.
    """
    exigidos = [
        # Tier 5 nunca sustenta fato; contradição oficial derruba maioria.
        ("app/services/research/schemas.py",
         ["def sustenta_claim", "def status_do_claim", "contradicted",
          "def classificar_risco",
          # Falta de crédito é registrada como `no_credit`, não como `error`:
          # o custo não foi gasto e a fila continua — misturar os dois some
          # com a informação de que basta pagar para a fila andar (D18).
          "no_credit"]),
        # A verificação é uma lista de checagens declaradas, não um julgamento
        # do modelo sobre si mesmo.
        ("app/services/research/claim_service.py",
         ["def verificar", "def detectar_contradicoes", "def localizar_trecho"]),
        # Conteúdo de página é DADO, nunca INSTRUÇÃO.
        ("app/services/research/content_sanitizer.py",
         ["LIMIAR_QUARENTENA", "seguro_para_o_modelo", "def envelopar"]),
        # Sem crédito é motivo declarado, não falha silenciosa (D18).
        ("app/services/research/providers.py",
         ["SEM_CREDITO", "SEM_CHAVE", "MOTIVO_HUMANO"]),
        # Monitor não avisa sobre banner de cookie.
        ("app/services/research/monitor_service.py",
         ["def limpar_ruido", "vira_signal", "unreachable"]),
        # Prospecção entrega lista com motivo; nunca campo pessoal sensível.
        ("app/services/research/discovery.py", ["CRITERIOS", "def calcular_fit"]),
        # A busca antiga deixa de ser autoridade, com rollback sem deploy.
        ("app/services/research/legacy_adapter.py",
         ["cutover_ligado", "web_search_ainda_e_autoridade"]),
        # "Origem interna não vira sinal" é UM conceito, aplicado por todos.
        ("app/services/intelligence/origem.py",
         ["def e_interno", "def filtrar_externos", "CANAIS_INTERNOS"]),
    ]
    for rel, simbolos in exigidos:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.exists(caminho):
            return False, f"ausente: {rel}"
        with open(caminho, encoding="utf-8") as fh:
            fonte = fh.read()
        faltando = [s for s in simbolos if s not in fonte]
        if faltando:
            return False, f"{rel} sem: {', '.join(faltando)}"

    # Monitor sem Rotina seria um segundo agendador — proibição estrutural.
    with open(os.path.join(RAIZ, "app/services/research/monitor_service.py"),
              encoding="utf-8") as fh:
        if "routine_id" not in fh.read():
            return False, "REGRESSAO: monitor deixou de nascer preso a uma Rotina"

    # Os detectores da 059 precisam continuar filtrando a origem interna: sem
    # isso, o sistema volta a apontar o próprio rastro como problema da
    # corretora — o falso positivo que o canário com dado real encontrou.
    for rel in ("app/services/intelligence/detectors/qualidade.py",
                "app/services/intelligence/detectors/operacao.py",
                "app/services/intelligence/detectors/automacao.py"):
        with open(os.path.join(RAIZ, rel), encoding="utf-8") as fh:
            if "filtrar_externos" not in fh.read():
                return False, f"REGRESSAO: {rel} voltou a contar origem interna"

    return True, "procedência, quarentena, degradação declarada e origem interna"


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

CASOS: list[Caso] = [
    Caso("SEC-01", "seguranca", "A plataforma não vira scanner de rede interna",
         "SPEC-054 C", caso_egress_ssrf),
    Caso("SEC-02", "seguranca", "Documento de uma corretora não é lido por outra",
         "SPEC-054 A", caso_storage_isolamento),
    Caso("SEC-03", "seguranca", "Segredo da plataforma não vaza para subprocesso",
         "SPEC-054 C", caso_mcp_env),
    Caso("SEC-04", "seguranca", "Browser não escolhe a corretora do arquivo",
         "SPEC-054 A", caso_upload_derivado_da_sessao),
    Caso("SEC-05", "seguranca", "Admin não grava com chave pública",
         "SPEC-054 A", caso_admin_sem_upload_anon),
    Caso("CON-01", "conhecimento", "Conhecimento não publicado não chega ao corretor",
         "SPEC-052 Lote 1", caso_rag_global_unico),
    Caso("MEM-01", "memoria", "O AutoBrokers lembra do corretor entre conversas",
         "SPEC-052 Lote 4", caso_memoria_alcancavel),
    Caso("EXE-01", "execucao", "O corretor não é cobrado nem notificado em duplicidade",
         "SPEC-055", lambda: _roda_script("test_spec055_work_os.py")),
    Caso("EXE-02", "execucao", "Trabalho longo sobrevive a restart e retoma",
         "SPEC-055", lambda: caso_work_os_durabilidade()),
    Caso("SKL-01", "capacidades", "O agente só usa a ferramenta que o poder dele permite",
         "SPEC-056", lambda: _roda_script("test_spec056_skill_registry_gateway.py")),
    Caso("SKL-02", "capacidades", "Ação de efeito externo nunca roda sem aprovação",
         "SPEC-056", lambda: caso_efeito_grave_exige_aprovacao()),
    # A peça é o que o cliente do corretor vê. Ilegível ou fora da marca, ela
    # queima a corretora na frente do cliente dela — por isso entra no gate.
    Caso("MRC-01", "identidade", "Toda peça sai legível e com a marca da corretora",
         "SPEC-057", lambda: _roda_script("test_spec057_brand_identity.py")),
    # Corpus normativo entra no cerebro de TODAS as corretoras. Ruido aqui
    # nao e um erro de uma corretora — e uma resposta errada dada a todas.
    Caso("MRC-02", "conhecimento", "Só entra no corpus normativo o que é norma",
         "SPEC-057", lambda: _roda_script("test_spec057_corpus_normativo.py")),
    # O cutover troca a autoridade do cerebro de um sistema em producao. Se ele
    # puder ADICIONAR ferramenta ou derrubar a conversa quando falha, o corretor
    # perde — ou privilegio de mais, ou atendimento de menos.
    Caso("CUT-01", "capacidades", "O cutover só tira ferramenta e nunca derruba a conversa",
         "SPEC-057", lambda: _roda_script("test_spec057_cutover.py")),
    # A condicao geral no RAG global descreve o PRODUTO. Se ela sozinha
    # confirmar cobertura de uma apolice concreta, o corretor repete ao cliente
    # e a corretora responde por isso.
    Caso("CTX-01", "conhecimento", "Norma sozinha nunca confirma cobertura de apólice",
         "SPEC-052", lambda: _roda_script("test_spec052_context_assembly.py")),
    # Inflacao de Agents e o erro mais caro de uma plataforma agentica: um
    # prompt por corretora, custo que ninguem mediu e nada reaproveitavel.
    Caso("AUX-01", "capacidades", "O sistema não cria um Agent para cada pedido",
         "SPEC-058", lambda: _roda_script("test_spec058_factory.py")),
    # Um sistema proativo erra de dois jeitos, e os dois custam o corretor:
    # inventando o que nao aconteceu, e repetindo o que ele ja dispensou. O
    # primeiro destroi a confianca no numero; o segundo ensina a ignorar a tela.
    Caso("INT-01", "inteligencia", "O briefing não inventa número nem esconde ausência de dado",
         "SPEC-059", lambda: _roda_script("test_spec059_intelligence.py")),
    Caso("INT-02", "inteligencia", "Alerta e memória: evidência obrigatória e gatilho alcançável",
         "SPEC-059", lambda: caso_inteligencia_estrutural()),
    # Pesquisa é a única parte do sistema que traz informação de FORA. Ela erra
    # de dois jeitos caros: afirmando sem procedência (o corretor repete ao
    # cliente e a corretora responde) e obedecendo a uma página da internet.
    Caso("RES-01", "pesquisa", "Nada é afirmado sem fonte que sustente, e página não dá ordem",
         "SPEC-060", lambda: _roda_script("test_spec060_research.py")),
    Caso("RES-02", "pesquisa", "Procedência, quarentena e degradação declarada continuam no código",
         "SPEC-060", lambda: caso_pesquisa_estrutural()),
    # Tela sem link é tela que não existe para quem usa; rótulo repetido faz o
    # usuário acertar por sorte. As duas já aconteceram — o teste impede a volta.
    Caso("NAV-01", "identidade", "Toda tela tem link no menu e nenhum rótulo é ambíguo",
         "SPEC-059/060", lambda: _roda_script("test_navegacao_sem_pagina_orfa.py")),
    # Trabalho sem rastro é trabalho que ninguém consegue diagnosticar. O Bloco
    # 0 achou `work_attempts` sem writer nenhum e `tool_invocations` com writer
    # que ninguém chamava — com 43 Work Runs concluídos em produção.
    Caso("AUD-01", "execucao", "Toda etapa e toda ferramenta deixam rastro auditável",
         "SPEC-055/056", lambda: _roda_script("test_bloco0_auditoria_execucao.py")),
    # Uma matriz de permissão erra em SILÊNCIO: uma permission de escrita que
    # caia no conjunto do auditor não produz erro — produz um auditor que age,
    # e ninguém descobre até ele agir.
    Caso("RBA-01", "identidade", "Cada papel do Admin pode só o que deve",
         "SPEC-061", lambda: _roda_script("test_spec061_rbac.py")),
    Caso("IDN-01", "identidade", "Corretora A não enxerga dados da corretora B",
         "SPEC-048", lambda: _roda_script("test_spec048_isolamento_corretoras.py")),
    Caso("CAP-01", "capacidades", "Agente só recebe os poderes do seu papel",
         "SPEC-014/054", lambda: _roda_script("test_capability_resolver.py")),
    Caso("EGR-01", "seguranca", "Política de egresso completa",
         "SPEC-054 C", lambda: _roda_script("test_spec054_egress_guard.py")),
    Caso("WPP-01", "whatsapp", "Corretoras não compartilham instância de WhatsApp",
         "SPEC-047", lambda: _roda_script("test_spec047_multiempresa_whatsapp.py"), obrigatorio=False),
    Caso("PAR-01", "whatsapp", "Pareamento não ressuscita tentativa expirada",
         "SPEC-051", lambda: _roda_script("test_spec051_pairing_passkey.py"), obrigatorio=False),
    Caso("OBS-01", "whatsapp", "Observador não mistura tenant",
         "SPEC-051", lambda: _roda_script("test_spec051_observer_agents.py"), obrigatorio=False),
    Caso("ROT-01", "rotinas", "Rotina do corretor executa sem duplicar",
         "SPEC-019", lambda: _roda_script("test_f2_routines.py"), obrigatorio=False),
    Caso("POR-01", "portais", "Portal não age fora do job autorizado",
         "SPEC-020", lambda: _roda_script("test_spec020_portal.py"), obrigatorio=False),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Broker Outcome Regression Pack")
    ap.add_argument("--suite", help="filtra por suíte")
    ap.add_argument("--so-obrigatorios", action="store_true")
    args = ap.parse_args()

    casos = CASOS
    if args.suite:
        casos = [c for c in casos if c.suite == args.suite]
    if args.so_obrigatorios:
        casos = [c for c in casos if c.obrigatorio]

    print("=" * 74)
    print("BROKER OUTCOME REGRESSION PACK")
    print("Cada caso protege um RESULTADO do corretor, não uma linha de código.")
    print("=" * 74)

    resultados: list[Resultado] = []
    suite_atual = None
    for caso in casos:
        if caso.suite != suite_atual:
            suite_atual = caso.suite
            print(f"\n[{suite_atual.upper()}]")
        inicio = time.time()
        try:
            passou, detalhe = caso.executor()
        except Exception as exc:  # noqa: BLE001
            passou, detalhe = False, f"{type(exc).__name__}: {exc}"
        dur = time.time() - inicio
        resultados.append(Resultado(caso, passou, detalhe, dur))

        if passou:
            marca = "PASS"
        elif detalhe.startswith("SKIP_AMBIENTE"):
            marca = "SKIP"
        else:
            marca = "FALHA" if caso.obrigatorio else "aviso"
        print(f"  {marca:<5} {caso.id}  {caso.resultado_protegido}")
        if not passou:
            print(f"        -> {detalhe}")

    print("\n" + "=" * 74)
    passaram = [r for r in resultados if r.passou]
    pulados = [r for r in resultados if not r.passou and r.detalhe.startswith("SKIP_AMBIENTE")]
    falhas_obrig = [r for r in resultados if not r.passou and r.caso.obrigatorio
                    and not r.detalhe.startswith("SKIP_AMBIENTE")]
    avisos = [r for r in resultados if not r.passou and not r.caso.obrigatorio
              and not r.detalhe.startswith("SKIP_AMBIENTE")]

    print(f"passaram={len(passaram)}  falhas_obrigatorias={len(falhas_obrig)}  "
          f"avisos={len(avisos)}  pulados_por_ambiente={len(pulados)}  total={len(resultados)}")

    if falhas_obrig:
        print("\nGATE VERMELHO — resultados do corretor em risco:")
        for r in falhas_obrig:
            print(f"  X {r.caso.id} [{r.caso.spec}] {r.caso.resultado_protegido}")
            print(f"      {r.detalhe}")
        return 1

    if avisos:
        print("\nAvisos (não bloqueiam o gate):")
        for r in avisos:
            print(f"  ! {r.caso.id} {r.detalhe[:110]}")

    print("\nGATE VERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
