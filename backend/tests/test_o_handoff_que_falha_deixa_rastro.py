# -*- coding: utf-8 -*-
"""O handoff que falha deixa RASTRO — e o motivo nunca vai vazio.

📊 O QUE ACONTECEU EM 09/09/2026, primeiro dia de piloto real (AutoFleet)

    5   vezes a ferramenta `human_handoff` rodou
    5   vezes `_avisar_suporte` devolveu {"avisado": False,
        "motivo": "a corretora não tem destino de suporte humano configurado"}
    0   linhas em qualquer tabela
    4/5 conversas com `human_handoff_reason` NULL

A recusa estava CERTA: sem destino, a ferramenta não mente para o segurado.
O defeito é o que veio depois — a falha morreu num `logger.error`, e log de
contêiner some no próximo deploy. De fora, "o robô pediu ajuda humana cinco
vezes e ninguém recebeu" e "ninguém precisou de ajuda humana hoje" eram a
MESMA tela vazia. **Falha silenciosa é falha que ninguém conserta.**

🔴 E POR QUE O `claims.handoff_pedido` NÃO ERA O RASTRO

Ele existe desde a SPEC-093-B e é chamado a cada handoff. Mesmo assim,
`work_events` com `claims.%` = **0**. A causa não é o `except` do chamador
nem o do `registrar_gesto`: `claims_shadow.registrar_evento` sai por
`if not run_id: return False` quando a conversa não tem sombra de sinistro —
`work_events.work_run_id` é NOT NULL com FK para `work_runs`, e 📊 4 de 729
conversas têm run. **Nenhuma exceção foi levantada, logo nada foi engolido.**
Era um `return False` silencioso, por construção.

Por isso o rastro do handoff mora em `agent_activities`, pelo escritor que já
existe (`activity_log.log_activity`): tem `company_id`, não exige run e é o
feed que a corretora já lê.

O QUE ESTE GUARDA PROVA — chamando o MOTOR (`_arun`), nunca o texto-fonte:

    [A] sem destino  -> linha durável de FALHA + a frase honesta ao segurado
    [B] com destino  -> linha durável de ENTREGA + o dossiê sai
    [C] o motivo     -> gravado nos DOIS casos, em português, nunca NULL
    [D] o /health    -> nomeia a corretora ligada e sem quem receba
    [M] mutações     -> tirar a escrita da falha e tirar o motivo ficam VERMELHOS
"""

from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)                       # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
if TESTES not in sys.path:
    sys.path.insert(0, TESTES)

# 🔴 REUSO, NÃO CÓPIA (CLAUDE.md §5). O dublê de banco com as colunas NOT NULL
#    medidas mora no guarda da 097.1; o dublê ASSÍNCRONO que faz o resolvedor
#    rodar de verdade mora no guarda do handoff. Dois dublês novos aqui seriam
#    dois dublês para manter, e o terceiro envelheceria calado.
from test_handoff_chega_em_alguem import (  # noqa: E402
    CO_ALFA, CO_BETA, GRUPO_DE_ALFA, BancoDeDuasCorretoras,
    mundo_de_duas_corretoras,
)
from test_o_caso_se_explica_sozinho import Banco  # noqa: E402

CONVERSA_ALFA = "aaaaaaaa-1111-4111-8111-111111111111"
CONVERSA_BETA = "bbbbbbbb-2222-4222-8222-222222222222"

OK = 0
FALHOU: list = []


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def certo(cond, nome, detalhe=""):
    global OK
    if cond:
        OK += 1
        _p("  OK       %s" % nome)
    else:
        FALHOU.append(nome)
        _p("  [FALHOU] %s%s" % (nome, ("  -- " + str(detalhe)[:300]) if detalhe else ""))


# ===========================================================================
# O MUNDO — uma corretora com destino, outra ligada e muda
# ===========================================================================
def conversa(ident, empresa, sessao):
    """💭 Fixture fictícia e óbvia. ⛔ NUNCA telefone ou nome reais."""
    return {"id": ident, "company_id": empresa, "session_id": sessao,
            "user_phone": "5511900000001", "user_name": "Cliente Canario",
            "status": "open", "claimed_by": None, "claimed_by_name": None,
            "human_handoff_reason": None,
            "last_message_preview": "bati o carro agora, preciso falar com alguem",
            "ficha_atendimento": {"servico": "colisao", "faltando": []},
            "resolvido_em": None, "resolucao_motivo": None}


def mundo_do_banco_da_tool():
    return {"conversations": [conversa(CONVERSA_ALFA, CO_ALFA, "ss-alfa-1"),
                              conversa(CONVERSA_BETA, CO_BETA, "ss-beta-1")],
            "messages": [], "work_runs": [], "work_events": [],
            "agent_activities": []}


class _Integracao(dict):
    """O que `get_whatsapp_integration` devolve — só precisa ser verdadeiro."""


class _ServicoDeIntegracao:
    def __init__(self, *a, **k):
        pass

    def get_whatsapp_integration(self, company_id):
        return _Integracao({"company_id": company_id})


class _WhatsAppQueNaoSai:
    """Registra o envio em vez de fazê-lo. ⛔ Nenhum byte na rede."""

    def __init__(self):
        self.enviados: list = []

    def send_message(self, destino, texto, integ, **k):
        self.enviados.append({"destino": destino, "tamanho": len(texto or ""),
                              "bloco_unico": k.get("bloco_unico")})
        return True


def rodar_handoff(empresa, sessao, motivo="", com_destino=True):
    """Roda `_arun` DE VERDADE. Devolve (resposta, banco, wa).

    ⚠️ Os dublês trocam só TRANSPORTE e RELÓGIO — banco, Redis, WhatsApp. O
    resolvedor de destino, a marcação da conversa, o dossiê e a decisão do que
    devolver ao segurado são o motor real (CLAUDE.md §9.4).
    """
    import app.agents.tools.human_handoff as HH
    from app.core import database as _db
    from app.services import integration_service as _integ
    from app.services import whatsapp_service as _wa

    banco = Banco(mundo_do_banco_da_tool(), sincrono=True)
    async_banco = BancoDeDuasCorretoras(mundo_de_duas_corretoras())
    wa = _WhatsAppQueNaoSai()

    async def _cliente_async():
        return async_banco

    # ⚠️ `**kw` desde 16/09/2026: a SPEC-EXTRA-001.3 §7.5 acrescentou
    # `company_id` e `tipo` à chave do marcador. O dublê aceita o que vier —
    # o marcador do Redis não é o alvo DESTE guarda, e um dublê que trave na
    # assinatura transforma toda evolução de contrato em falso vermelho.
    async def _sem_marcador(conversa_id, horas, **kw):
        return False        # a vez é sua — o marcador do Redis não é o alvo aqui

    async def _devolve(conversa_id, **kw):
        return None

    def _sync_client():
        return banco

    guardados = {
        "create": getattr(_db, "create_async_supabase_client", None),
        "get_sync": getattr(_db, "get_supabase_client", None),
        "reivindicar": HH.reivindicar_o_aviso,
        "devolver": HH.devolver_a_vez,
        "integ": _integ.get_integration_service,
        "wa": _wa.get_whatsapp_service,
    }
    _db.create_async_supabase_client = _cliente_async
    _db.get_supabase_client = _sync_client          # é por aqui que `log_activity` grava
    HH.reivindicar_o_aviso = _sem_marcador
    HH.devolver_a_vez = _devolve
    _integ.get_integration_service = lambda *a, **k: _ServicoDeIntegracao()
    _wa.get_whatsapp_service = lambda *a, **k: wa
    try:
        tool = HH.HumanHandoffTool(banco)
        resposta = asyncio.run(tool._arun(reason=motivo, session_id=sessao,
                                          company_id=empresa))
    finally:
        _db.create_async_supabase_client = guardados["create"]
        _db.get_supabase_client = guardados["get_sync"]
        HH.reivindicar_o_aviso = guardados["reivindicar"]
        HH.devolver_a_vez = guardados["devolver"]
        _integ.get_integration_service = guardados["integ"]
        _wa.get_whatsapp_service = guardados["wa"]
    return resposta, banco, wa


def atividades(banco):
    return [dict(r["carga"]) for r in banco.escritas("agent_activities", "insert")]


def motivos_gravados(banco):
    return [str((r["carga"] or {}).get("human_handoff_reason") or "")
            for r in banco.escritas("conversations", "update")]


# ===========================================================================
# [A] SEM DESTINO — a falha vira linha, e o segurado ouve a verdade
# ===========================================================================
def bloco_A():
    _p("\n[A] Sem destino de suporte: a falha DEIXA RASTRO e ninguem promete nada")
    import app.agents.tools.human_handoff as HH
    from app.agents.honestidade_do_handoff import FALHA_DO_HANDOFF

    resposta, banco, wa = rodar_handoff(CO_BETA, "ss-beta-1",
                                        motivo="cliente bateu o carro e pediu uma pessoa")
    linhas = atividades(banco)

    certo(len(linhas) == 1, "[A1] a falha grava UMA linha duravel em agent_activities",
          "gravou %d: %r" % (len(linhas), linhas))
    if not linhas:
        return
    linha = linhas[0]
    certo(str(linha.get("company_id")) == CO_BETA,
          "[A2] com o company_id da corretora certa (CLAUDE.md §7)", repr(linha))
    certo(linha.get("title") == HH.TITULO_HANDOFF_FALHOU,
          "[A3] com o titulo da FALHA, nao o da entrega", repr(linha.get("title")))
    detalhe = str(linha.get("detail") or "")
    certo("ninguem foi avisado" in detalhe.lower()
          .replace("ninguém", "ninguem"),
          "[A4] o detalhe diz, em portugues, que ninguem foi avisado", detalhe)
    certo("destino de suporte" in detalhe,
          "[A5] e diz o MOTIVO real: a corretora nao tem destino de suporte", detalhe)
    certo("ss-beta-1" not in detalhe and "5511900000001" not in detalhe,
          "[A6] e NAO leva session_id nem telefone -- o session_id carrega o numero",
          detalhe)

    carimbo = FALHA_DO_HANDOFF.split("·", 1)[0].strip()
    certo(carimbo and carimbo in resposta,
          "[A7] o segurado recebe a frase honesta de FALHA_DO_HANDOFF", resposta[:200])
    certo("HANDOFF_OK" not in resposta,
          "[A8] e NUNCA o carimbo que autoriza prometer atendente", resposta[:200])
    certo(wa.enviados == [],
          "[A9] CONTROLE: nada foi enviado -- nao ha para onde", repr(wa.enviados))


# ===========================================================================
# [B] COM DESTINO — o dossiê sai e a entrega vira linha
# ===========================================================================
def bloco_B():
    _p("\n[B] Com destino: o dossie SAI e a entrega vira linha")
    import app.agents.tools.human_handoff as HH

    resposta, banco, wa = rodar_handoff(CO_ALFA, "ss-alfa-1",
                                        motivo="cliente pediu falar com uma pessoa")
    linhas = atividades(banco)

    certo(len(wa.enviados) == 1 and wa.enviados[0]["destino"] == GRUPO_DE_ALFA,
          "[B1] CONTROLE: o dossie foi para o grupo DA ALFA -- e so para ele",
          repr(wa.enviados))
    certo(len(linhas) == 1 and linhas[0].get("title") == HH.TITULO_HANDOFF_ENTREGUE,
          "[B2] a entrega grava a linha de ENTREGUE", repr(linhas))
    certo(linhas and str(linhas[0].get("company_id")) == CO_ALFA,
          "[B3] com o company_id da ALFA", repr(linhas))
    certo("HANDOFF_OK" in resposta,
          "[B4] e o agente recebe o carimbo que autoriza dizer que encaminhou",
          resposta[:200])
    certo(linhas and HH.TITULO_HANDOFF_FALHOU != linhas[0].get("title"),
          "[B5] e a linha NAO e a de falha -- os dois desfechos se distinguem")


# ===========================================================================
# [C] O MOTIVO — gravado nos dois casos, em portugues, nunca NULL
# ===========================================================================
def bloco_C():
    _p("\n[C] `human_handoff_reason` NUNCA vai vazio -- 4/5 NULL em 09/09")
    import app.agents.tools.human_handoff as HH

    _r, banco_falha, _w = rodar_handoff(CO_BETA, "ss-beta-1",
                                        motivo="cliente com sinistro pediu uma pessoa")
    _r2, banco_ok, _w2 = rodar_handoff(CO_ALFA, "ss-alfa-1",
                                       motivo="cliente com sinistro pediu uma pessoa")
    m_falha = [m for m in motivos_gravados(banco_falha) if m]
    m_ok = [m for m in motivos_gravados(banco_ok) if m]
    certo(m_falha and m_falha[0] == "cliente com sinistro pediu uma pessoa",
          "[C1] handoff que FALHOU grava o motivo mesmo assim",
          repr(motivos_gravados(banco_falha)))
    certo(m_ok and m_ok[0] == "cliente com sinistro pediu uma pessoa",
          "[C2] handoff que DEU CERTO grava o mesmo motivo, sem reescrever",
          repr(motivos_gravados(banco_ok)))

    # 🔴 O CASO DE 09/09: o modelo chama a tool SEM `reason`, e a conversa NAO
    #    e pos-acionamento -- o ramo que a 097.1 consertou nao pega este.
    _r3, banco_mudo, _w3 = rodar_handoff(CO_BETA, "ss-beta-1", motivo="")
    m_mudo = [m for m in motivos_gravados(banco_mudo) if m]
    certo(m_mudo and m_mudo[0] == HH.MOTIVO_SEM_DECLARACAO,
          "[C3] motivo AUSENTE em caso NAO acionado grava o 'nao declarado' -- nunca NULL",
          repr(motivos_gravados(banco_mudo)))
    certo(all("_" not in m or " " in m for m in m_mudo),
          "[C4] e o que a atendente le e frase, nao nome de variavel", repr(m_mudo))

    # A humanizacao, no motor puro.
    certo(HH._motivo_em_portugues("cliente_pediu_humano") == "cliente pediu humano",
          "[C5] um slug do modelo vira frase",
          repr(HH._motivo_em_portugues("cliente_pediu_humano")))
    certo(HH._motivo_em_portugues("  pediu\n   humano  ") == "pediu humano",
          "[C6] quebras e espacos colapsam")
    certo(HH._motivo_em_portugues("cliente pediu pessoa") == "cliente pediu pessoa",
          "[C7] CONTROLE: frase que ja e humana passa INTACTA "
          "(guarda [D2] da 097.1 compara por igualdade)")
    certo(len(HH._motivo_em_portugues("x" * 900)) <= 300,
          "[C8] e tem teto -- a Fila mostra uma linha, nao um paragrafo")


# ===========================================================================
# [D] O /health nomeia a corretora ligada e sem quem receba
# ===========================================================================
def bloco_D():
    _p("\n[D] /health: corretora com agente LIGADO e sem destino de suporte")
    if os.getenv("RASTRO_SEM_MAIN") == "1":
        _p("  (pulado no subprocesso das mutacoes: importar `app.main` custa "
           "📊 ~60 s por processo, e as duas mutacoes declaradas moram em "
           "`human_handoff.py`)")
        return
    from app.core import database as _db

    import app.main as M

    mundo = mundo_de_duas_corretoras()
    for linha in mundo["companies"]:
        linha["company_name"] = {CO_ALFA: "Corretora Alfa",
                                 CO_BETA: "Corretora Beta"}.get(linha["id"],
                                                                "Corretora X")
    mundo["agents"] = [
        {"company_id": CO_ALFA, "agent_role": "attendance", "is_active": True},
        {"company_id": CO_BETA, "agent_role": "attendance", "is_active": True},
        # ⚠️ CONTROLE: desligada e sem destino NAO entra -- a lista e sobre quem
        #    ESTA ligado. Sem esta linha o guarda nao distinguiria "sem destino"
        #    de "sem destino E ligado", que sao problemas diferentes.
        {"company_id": "co-desligada-0000-0000-000000000009",
         "agent_role": "attendance", "is_active": False},
        # ⚠️ CONTROLE 2: outro papel, ligado, sem destino -- tambem NAO entra.
        {"company_id": "co-cobranca-0000-0000-000000000010",
         "agent_role": "auxiliary", "is_active": True},
    ]
    banco = BancoDeDuasCorretoras(mundo)

    async def _cliente_async():
        return banco

    guardado = getattr(_db, "create_async_supabase_client", None)
    _db.create_async_supabase_client = _cliente_async
    try:
        lista = asyncio.run(M._corretoras_ligadas_sem_destino_de_suporte(banco))
    finally:
        _db.create_async_supabase_client = guardado

    certo(lista == ["Corretora Beta"],
          "[D1] a lista tem SO a corretora ligada e sem destino, pelo NOME", repr(lista))
    certo("Corretora Alfa" not in lista,
          "[D2] CONTROLE: a que TEM destino nao aparece", repr(lista))
    certo(not any("desligada" in str(x) for x in lista),
          "[D3] CONTROLE: agente desligado nao aparece", repr(lista))
    certo(not any("cobranca" in str(x) for x in lista),
          "[D4] CONTROLE: outro papel nao aparece", repr(lista))
    certo(not any("@g.us" in str(x) or "5547" in str(x) for x in lista),
          "[D5] e a lista nao carrega destino, telefone nem segredo", repr(lista))


# ===========================================================================
# [M] AS MUTAÇÕES — sem elas o bloco acima é carimbo, não guarda
# ===========================================================================
MUTACOES = [
    # M1 -- a escrita da falha some -> [A1..A6] vermelhos
    ("app/agents/tools/human_handoff.py",
     "await registrar_o_desfecho_do_handoff(\n"
     "            company_id, EVENTO_HANDOFF_FALHOU,\n"
     '            aviso["motivo"] or "motivo desconhecido", conversa_id)',
     "pass  # _MUTADO_RASTRO_M1",
     "M1"),
    # M2 -- o motivo volta a so ser escrito quando existe -> [C3] vermelho
    ("app/agents/tools/human_handoff.py",
     "            if not motivo_gravado:\n"
     "                motivo_gravado = MOTIVO_SEM_DECLARACAO\n"
     '            dados["human_handoff_reason"] = motivo_gravado',
     "            if motivo_gravado:  # _MUTADO_RASTRO_M2\n"
     '                dados["human_handoff_reason"] = motivo_gravado',
     "M2"),
]


def _nomes_falhos_num_filho():
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--filho"],
                       cwd=RAIZ, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8",
                            "RASTRO_SEM_MAIN": "1"})
    nomes = {l.split("[FALHOU]", 1)[-1].split("--", 1)[0].strip()
             for l in (r.stdout or "").splitlines() if "[FALHOU]" in l}
    return nomes, r


def rodar_mutacoes():
    _p("\n[M] MUTACOES POR COPIA -- a arvore precisa estar parada")
    base, _r = _nomes_falhos_num_filho()
    _p("      linha de BASE (no filho): %d nome(s) ja vermelho(s)" % len(base))
    verdes = []
    for caminho, de, para, marcador in MUTACOES:
        alvo = os.path.join(RAIZ, caminho)
        original = io.open(alvo, encoding="utf-8").read()
        if de not in original:
            FALHOU.append("mutacao %s nao aplica" % marcador)
            _p("  [FALHOU] mutacao %s: a ancora nao existe -- mutacao que nao "
               "aplica NAO e mutacao passada" % marcador)
            continue
        backup = alvo + ".bak-rastro"
        shutil.copyfile(alvo, backup)
        try:
            io.open(alvo, "w", encoding="utf-8").write(original.replace(de, para, 1))
            nomes, r = _nomes_falhos_num_filho()
            novos = nomes - base
            if r.returncode not in (0, 1):
                novos.add("[SUBPROCESSO] rc=%d: %s"
                          % (r.returncode, (r.stderr or r.stdout or "")[-300:]))
            if novos:
                _p("  OK       mutacao %s -> VERMELHOS novos: %s"
                   % (marcador, "; ".join(sorted(novos))))
            else:
                verdes.append(marcador)
                _p("  [FALHOU] mutacao %s NAO ficou vermelha -- o bloco e carimbo"
                   % marcador)
        finally:
            shutil.copyfile(backup, alvo)
            os.remove(backup)
    return verdes


def main() -> int:
    _p("=" * 78)
    _p("O HANDOFF QUE FALHA DEIXA RASTRO -- e o motivo nunca vai vazio")
    _p("=" * 78)
    for bloco in (bloco_A, bloco_B, bloco_C, bloco_D):
        try:
            bloco()
        except Exception as exc:  # noqa: BLE001
            FALHOU.append(bloco.__name__)
            _p("  [FALHOU] %s EXPLODIU: %s: %s" % (bloco.__name__,
                                                   type(exc).__name__, exc))
    verdes = []
    if "--filho" not in sys.argv:
        verdes = rodar_mutacoes()
    _p("\n" + "=" * 78)
    _p("  PLACAR: %d verde(s) . %d vermelho(s)" % (OK, len(FALHOU)))
    if FALHOU:
        for nome in FALHOU:
            _p("    - %s" % nome)
    if verdes:
        _p("  ⛔ %d mutacao(oes) NAO ficaram vermelhas: %s"
           % (len(verdes), ", ".join(verdes)))
    _p("=" * 78)
    return 1 if (FALHOU or verdes) else 0


def test_o_handoff_que_falha_deixa_rastro():
    """Roda a si mesmo num subprocesso: este guarda troca `sys.modules` e
    aplica mutacoes na arvore -- nao pode dividir processo com outros testes."""
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=RAIZ,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 0, (r.stdout[-5000:] + r.stderr[-1500:])


if __name__ == "__main__":
    sys.exit(main())
