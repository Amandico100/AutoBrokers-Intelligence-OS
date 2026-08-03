"""O atendimento lembra o que o cliente já respondeu — e sabe como se conduz.

Os dois defeitos, medidos em 02/08/2026
---------------------------------------
**S · Não existia estado de atendimento.**

📊 ``grep -niE "\\bfase|phase|etapa|stage|slot" backend/app/agents/*.py`` → ZERO.
O `AgentState` tem mensagens, empresa, usuário, sessão, prompts e métricas — e
nenhum campo de fase, de dado confirmado ou de objetivo.

A memória do que já foi perguntado **era a janela de contexto**: 60 mensagens.
Passou disso, o CPF que o cliente deu no começo sumia. O único remédio no código
era o prompt mandando *"RELEIA a conversa"* — e o comentário do
`langchain_service` registra que isso **já quebrou em produção**: o agente
repediu o CPF do mesmo cliente.

E a tool de acionamento obriga o modelo a **re-declarar 15+ campos a cada
chamada**, reconstruídos do texto. Perdeu a janela, perdeu a coleta.

Num sinistro real — que passa de 60 mensagens com facilidade — isso é pedir o
CPF de novo a quem acabou de bater o carro.

**G · A conduta destilada não chegava a lugar nenhum.**

📊 16 playbooks de conduta (12 ativos, ~97 KB), gerados por `claude-opus-5` a
partir de **297 atendimentos humanos reais**, com objetivo, verificações
prévias, ficha de coleta de até 19 campos, acolhimento e sensibilidade.

Todos os leitores: o juiz que os aprova, o otimizador semanal, o destilador que
os escreve, e duas telas de admin. ``grep conduct_playbook graph.py`` → **zero**.

As "fases" que o agente seguia eram **seis parágrafos escritos à mão** no
prompt. Ativar um playbook mudava uma string de status e um contador no painel.

O laço que este teste guarda
----------------------------
```
o modelo declara os slots na tool  →  a ficha GRAVA (nodes.py)
                                          ↓
        o turno seguinte MOSTRA de volta (graph.py)  →  não repergunta
```

Duas propriedades que não podem se perder:

* **Merge aditivo.** Um turno em que o modelo omite um campo não pode apagar o
  que o cliente já disse. É literalmente o defeito sendo consertado.
* **Fase derivada, nunca declarada.** O modelo informa o que descobriu; quem
  decide em que ponto o caso está é o código. Deixar o modelo escrever a fase
  seria deixá-lo dizer "já acionei" sem ter acionado.
"""

from __future__ import annotations

import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


def _carregar_ficha_isolada():
    """Carrega `attendance_ficha` SEM importar o pacote de serviços.

    `app/services/__init__.py` puxa `openai` e outras dependências pesadas que a
    suíte não tem — e não precisa ter. A lógica da ficha é pura; o I/O é o único
    trecho que fala com o banco, e ele não é exercitado aqui.
    """
    import types

    caminho = os.path.join(RAIZ, "backend", "app", "services", "attendance_ficha.py")
    fonte = io.open(caminho, encoding="utf-8").read()
    mod = types.ModuleType("attendance_ficha")
    mod.__dict__["__name__"] = "attendance_ficha"
    exec(compile(fonte, caminho, "exec"), mod.__dict__)  # noqa: S102 — código do repo
    return mod


# --------------------------------------------------------------------- #
# S — a ficha
# --------------------------------------------------------------------- #

def teste_a_ficha_nunca_esquece():
    """A prova do defeito: o turno 2 não repete o CPF, e ele tem de sobreviver."""
    print("\n[S1] Dado confirmado sobrevive a um turno que não o repete")
    f = _carregar_ficha_isolada()
    OBRIG = ["titular_cpf", "veiculo_placa", "local_atual", "local_destino"]

    ficha = f.fundir(f.ficha_vazia(), {
        "ramo": "auto", "servico": "guincho", "seguradora": "allianz",
        "confirmados": {"titular_cpf": "12345678901"},
    }, OBRIG)
    checar(ficha["confirmados"].get("titular_cpf") == "12345678901",
           "turno 1 grava o CPF")

    # O turno seguinte só traz a placa — exatamente o que acontece de verdade.
    ficha = f.fundir(ficha, {"confirmados": {"veiculo_placa": "ABC1D23"}}, OBRIG)
    checar(ficha["confirmados"].get("titular_cpf") == "12345678901",
           "turno 2 NÃO apaga o CPF",
           "é o defeito inteiro: o agente repediu o CPF do mesmo cliente")
    checar(ficha["confirmados"].get("veiculo_placa") == "ABC1D23",
           "e a placa entrou")

    # Um campo enviado vazio não pode zerar o que existe.
    ficha = f.fundir(ficha, {"confirmados": {"titular_cpf": ""}}, OBRIG)
    checar(ficha["confirmados"].get("titular_cpf") == "12345678901",
           "campo vazio não apaga confirmado")

    # E "não informado" não vale como confirmado.
    ficha2 = f.fundir(f.ficha_vazia(),
                      {"confirmados": {"local_atual": "não informado"}}, OBRIG)
    checar("local_atual" not in ficha2["confirmados"],
           "'não informado' não conta como coletado",
           "aceitar isso declararia completo um caso que não está")


def teste_a_fase_e_derivada_nao_declarada():
    print("\n[S2] A fase é consequência do que se sabe")
    f = _carregar_ficha_isolada()
    OBRIG = ["titular_cpf", "veiculo_placa"]

    vazia = f.ficha_vazia()
    checar(f.derivar_fase(vazia, OBRIG) == f.FASE_INTAKE, "sem nada: intake")

    meio = f.fundir(vazia, {"ramo": "auto", "servico": "guincho",
                            "confirmados": {"titular_cpf": "1"}}, OBRIG)
    checar(meio["fase"] == f.FASE_COLETA, "com dado parcial: coleta")

    # Faltando a apólice confirmada, NÃO pode dizer que está pronto.
    quase = f.fundir(meio, {"confirmados": {"veiculo_placa": "X"}}, OBRIG)
    checar(quase["fase"] != f.FASE_PRONTO,
           "slots completos mas apólice não confirmada NÃO é 'pronto'",
           "confirmar apólice é pré-requisito de acionar — guardrail policy_required")

    pronto = f.fundir(quase, {"apolice_confirmada": True}, OBRIG)
    checar(pronto["fase"] == f.FASE_PRONTO, "com apólice confirmada: pronto")

    # O modelo NÃO pode se declarar acionado.
    mentira = f.fundir(pronto, {"fase": f.FASE_ACIONADO}, OBRIG)
    checar(mentira["fase"] != f.FASE_ACIONADO,
           "o modelo não consegue se declarar 'acionado'",
           "só prova de acionamento (enviado_em/protocolo) muda essa fase")

    real = f.fundir(pronto, {"acionamento": {"enviado_em": "2026-08-03T00:00:00Z"}}, OBRIG)
    checar(real["fase"] == f.FASE_ACIONADO, "com prova de envio: acionado")

    com_protocolo = f.fundir(real, {"acionamento": {"protocolo": "AB123456"}}, OBRIG)
    checar(com_protocolo["fase"] == f.FASE_ACOMPANHANDO,
           "com protocolo: acompanhando")


def teste_o_humano_trava_a_fase():
    print("\n[S3] Devolvido a humano não volta a ser automático sozinho")
    f = _carregar_ficha_isolada()
    ficha = f.fundir(f.ficha_vazia(), {"ramo": "auto", "fase": f.FASE_COM_HUMANO}, [])
    checar(ficha["fase"] == f.FASE_COM_HUMANO, "a fase trava em com_humano")
    depois = f.fundir(ficha, {"confirmados": {"titular_cpf": "1"}}, [])
    checar(depois["fase"] == f.FASE_COM_HUMANO,
           "e continua travada mesmo com dado novo",
           "só uma pessoa tira de lá — o robô não se re-assume")


def teste_o_bloco_diz_o_que_falta_e_o_que_nao_perguntar():
    print("\n[S4] O bloco do prompt diz o essencial e nada além")
    f = _carregar_ficha_isolada()
    OBRIG = ["titular_cpf", "veiculo_placa", "local_atual"]
    ficha = f.fundir(f.ficha_vazia(), {
        "ramo": "auto", "servico": "guincho", "seguradora": "allianz",
        "confirmados": {"titular_cpf": "12345678901"},
    }, OBRIG)
    bloco = f.bloco_para_o_prompt(ficha, OBRIG)

    checar("não pergunte de novo" in bloco,
           "manda explicitamente não reperguntar")
    checar("12345678901" in bloco, "mostra o que já foi confirmado")
    checar("placa do veículo" in bloco and "onde o veículo está" in bloco,
           "lista o que ainda falta, com nome humano",
           "chave técnica não ajuda o modelo a conversar")
    checar("CPF do titular" in bloco, "usa rótulo legível, não a chave crua")
    checar(f.bloco_para_o_prompt(f.ficha_vazia(), OBRIG) == "",
           "ficha vazia não polui o prompt com bloco vazio")


def teste_a_ficha_esta_ligada_no_turno():
    print("\n[S5] A ficha é lida na entrada e escrita na saída do turno")
    graph = _sem_comentario(_ler("backend", "app", "agents", "graph.py"))
    checar("from app.services.attendance_ficha import bloco_para_o_prompt, carregar" in graph,
           "graph.py carrega a ficha")
    checar('dynamic_context += f"\\n\\n{_bloco_ficha}"' in graph,
           "e injeta no contexto do turno")
    checar('if str(_agent_role or "").lower() in ("attendance", "insured_external"):' in graph,
           "só para quem fala com o segurado",
           "o copiloto interno não tem ficha de atendimento")

    nodes = _sem_comentario(_ler("backend", "app", "agents", "nodes.py"))
    checar("_gravar_ficha_do_turno" in nodes, "nodes.py grava o que o turno apurou")
    checar('if tool_name in ("insurer_dispatch", "request_human_agent"):' in nodes,
           "nas duas tools que mudam o estado do caso")
    # Procura a CHAMADA (`await …`), não a definição — que fica antes no arquivo.
    pos_ok = nodes.find("registro.ok(result)")
    pos_chamada = nodes.find("await _gravar_ficha_do_turno(")
    checar(pos_ok != -1 and pos_chamada > pos_ok,
           "grava DEPOIS de a tool executar",
           "o que o modelo alegou numa chamada que estourou não é dado confirmado")


def teste_protocolo_so_vem_do_resultado():
    print("\n[S6] Protocolo só entra se veio do RESULTADO da tool")
    nodes = _ler("backend", "app", "agents", "nodes.py")
    corpo = nodes.split("async def _gravar_ficha_do_turno", 1)[-1].split("\nasync def ", 1)[0]
    checar("texto = str(result if isinstance(result, str)" in corpo,
           "a busca do protocolo é feita sobre o RESULTADO")
    checar("tool_args" not in corpo.split("protocolo", 1)[-1][:200],
           "e não sobre o que o modelo escreveu",
           "protocolo inventado é o que o guardrail no_fake_protocol impede")


# --------------------------------------------------------------------- #
# G — a conduta
# --------------------------------------------------------------------- #

def teste_a_conduta_chega_ao_turno():
    print("\n[G1] Os playbooks de conduta chegam ao prompt")
    graph = _sem_comentario(_ler("backend", "app", "agents", "graph.py"))
    checar("conduct_playbooks" in graph,
           "graph.py lê conduct_playbooks",
           "📊 antes: grep conduct_playbook graph.py → zero")
    checar("_conduta_do_caso" in graph, "há uma função que monta o bloco")
    checar('.eq("status", "active")' in graph,
           "só playbook ATIVO entra",
           "draft é rascunho: 4 dos 16 têm 3 a 6 sessões de base")


def teste_a_conduta_tem_teto():
    print("\n[G2] A conduta não empurra o conhecimento para fora")
    graph = _ler("backend", "app", "agents", "graph.py")
    checar("_TETO_DA_CONDUTA" in graph, "existe teto explícito")
    import re
    m = re.search(r"_TETO_DA_CONDUTA = (\d+)", graph)
    checar(bool(m), "o teto é um número")
    if m:
        teto = int(m.group(1))
        checar(500 < teto < 4000,
               f"o teto ({teto}) é razoável",
               "os playbooks têm 6 a 10 KB — colar inteiro tiraria o RAG do contexto")
    checar("rsplit(chr(10), 1)[0]" in graph,
           "o corte respeita fim de linha",
           "conduta cortada no meio de uma orientação é pior que ausente")


def teste_a_conduta_reusa_o_classificador_que_existe():
    print("\n[G3] Não foi criado um segundo classificador de ramo/serviço")
    graph = _ler("backend", "app", "agents", "graph.py")
    checar("from app.services.atlas.templater import infer_ramo_servico" in graph,
           "reusa o classificador do Atlas",
           "dois jeitos de responder a mesma pergunta divergem com o tempo")
    corpo = graph.split("async def _conduta_do_caso", 1)[-1].split("\nasync def ", 1)[0]
    checar("_AUTO_INTENT_RE" not in corpo and "def _classificar" not in corpo,
           "e não define regex próprio ao lado")


def main() -> int:
    print("=" * 68)
    print("O ATENDIMENTO TEM MEMORIA — E SABE COMO SE CONDUZ")
    print("=" * 68)
    for t in (teste_a_ficha_nunca_esquece,
              teste_a_fase_e_derivada_nao_declarada,
              teste_o_humano_trava_a_fase,
              teste_o_bloco_diz_o_que_falta_e_o_que_nao_perguntar,
              teste_a_ficha_esta_ligada_no_turno,
              teste_protocolo_so_vem_do_resultado,
              teste_a_conduta_chega_ao_turno,
              teste_a_conduta_tem_teto,
              teste_a_conduta_reusa_o_classificador_que_existe):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CLIENTE NAO OUVE DUAS VEZES A MESMA PERGUNTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
