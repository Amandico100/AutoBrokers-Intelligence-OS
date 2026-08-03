"""Quem responde o segurado é quem foi feito para isso — ou ninguém.

O defeito, medido em 02/08/2026
-------------------------------
Uma mensagem de segurado chegava, e o motor escolhia quem responderia assim::

    .eq("company_id", company_id).eq("is_active", True)
    .order("created_at").limit(1)

**O agente ativo mais antigo da corretora. Sem olhar o papel.**

Nas três corretoras de produção, o primeiro por `created_at` é o **core** — o
copiloto interno do corretor, cujo prompt manda entregar CPF **sem mascarar**,
porque quem fala com ele é o dono da carteira.

Três coisas tinham de dar errado juntas, e as três davam:

1. `pairing_orchestrator` gravava ``"agent_id": None if purpose == "observer"
   else None`` — um ternário que devolve None nos DOIS ramos. A integração de
   atendimento nascia sem dono.
2. Sem dono, o webhook chamava o motor sem dizer quem responde.
3. O portão de silêncio usava `attendance_observation_mode`, que só devolve
   True quando o agente de atendimento **existe e está desligado**. Corretora
   que **não tem** agente de atendimento recebia False — e False significava
   "pode falar".

📊 As três corretoras têm `attendance(inativo), core(ativo)`, e o primeiro por
data é o core nas três. A Resulta tem integração `purpose='attendance'` ativa.
O que segurava isso era uma allowlist de UM número de telefone.

E o CPF vazava por DOIS caminhos, não um
----------------------------------------
`infocap_tool` já sabia distinguir o público (`_client_facing`) — mas
`_summarize` e `_summarize_detail` são `@staticmethod` e nunca receberam essa
informação. Os dois imprimiam ``CPF/CNPJ: {doc}`` cru, inclusive no caminho que
fala com o segurado.

**Quem consertasse só o prompt acharia que tinha resolvido.**

O que este teste protege
------------------------
Que a resposta ao segurado exija PROVA de papel, em três camadas independentes
— pareamento, portão e motor — e que o corte do CPF esteja no lugar que
escreve, não numa instrução que o modelo pode ignorar.

**Papel pedido é papel entregue. Na dúvida, silêncio.**
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


def _ler(*partes: str) -> str:
    with io.open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_py(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


# ---------------------------------------------------------------------------
# A1..A3 — o motor exige papel
# ---------------------------------------------------------------------------

def teste_o_motor_exige_papel():
    print("\n[A1] O seletor de agente aceita e EXIGE um papel")
    fonte = _sem_comentario_py(_ler("backend", "app", "services", "langchain_service.py"))

    checar("required_role" in fonte, "_get_raw_agent recebe required_role")
    checar('.eq("agent_role", papel)' in fonte,
           "filtra por agent_role quando o papel é exigido",
           "sem o filtro, volta a pegar 'o primeiro por created_at'")

    # A trava final: mesmo com agent_id explícito, o papel tem de bater.
    checar("papel_do_agente != papel" in fonte,
           "recusa agente cujo papel não bate, mesmo com id explícito",
           "id herdado de pareamento antigo não pode virar permissão de fala")
    checar("return None" in fonte.split("papel_do_agente != papel", 1)[-1][:400],
           "e a recusa devolve None — não um agente qualquer")


def teste_recusar_e_diferente_de_nao_achar():
    print("\n[A2] Faltar o papel certo levanta erro próprio, não silêncio ambíguo")
    fonte = _ler("backend", "app", "services", "langchain_service.py")
    checar("AGENTE_DE_PAPEL_AUSENTE" in fonte,
           "erro nomeado quando o papel exigido não existe",
           "'CONFIG_REQUIRED' genérico esconde a causa de quem for depurar")


# ---------------------------------------------------------------------------
# A3..A4 — o portão do webhook
# ---------------------------------------------------------------------------

def teste_o_portao_pergunta_no_positivo():
    print("\n[A3] Só fala quem PROVA ter agente de atendimento ligado")
    fonte = _sem_comentario_py(_ler("backend", "app", "api", "webhook.py"))

    checar("_em_silencio = not await attendance_agent_active(company_id)" in fonte,
           "o portão de fala usa a pergunta POSITIVA",
           "attendance_observation_mode devolve False p/ corretora SEM agente — "
           "e False ali significava 'pode falar'")

    checar("attendance_observation_mode" not in fonte,
           "o portão negativo não é mais usado no caminho de fala",
           "os dois estados 'desligado' e 'nunca existiu' caíam no mesmo ramo")

    # E o fail-closed do except continua.
    trecho = fonte.split("_em_silencio = not await", 1)[-1][:600]
    checar("_em_silencio = True" in trecho,
           "falha ao consultar o portão continua virando SILÊNCIO")


def teste_o_webhook_exige_o_papel_no_motor():
    print("\n[A4] O caminho do segurado exige o papel também no motor")
    fonte = _sem_comentario_py(_ler("backend", "app", "api", "webhook.py"))
    checar('required_role="attendance"' in fonte,
           "process_message é chamado exigindo o papel de atendimento",
           "é a segunda trava: o agent_id da integração pode estar velho")


# ---------------------------------------------------------------------------
# A5 — o pareamento grava o dono
# ---------------------------------------------------------------------------

def teste_o_pareamento_grava_o_dono():
    print("\n[A5] O pareamento de atendimento nasce com dono")
    fonte = _ler("backend", "app", "services", "whatsapp", "pairing_orchestrator.py")

    checar('"agent_id": None if purpose == "observer" else None' not in fonte,
           "o ternário morto foi removido",
           "devolvia None nos dois ramos — 'ninguém tem agente'")
    checar("_resolver_agente_de_atendimento" in fonte,
           "existe um resolvedor de agente de atendimento")
    checar('_resolver_agente_de_atendimento(company_id) if purpose == "attendance" else None' in fonte,
           "atendimento recebe dono; observador continua sem",
           "o observador é mudo por construção — dono ali seria mentira")

    # Fail-closed: erro ao resolver grava nulo (que faz calar), nunca um id chutado.
    corpo = fonte.split("def _resolver_agente_de_atendimento", 1)[-1].split("\ndef ", 1)[0]
    checar("return None" in corpo and "except Exception" in corpo,
           "falha ao resolver grava NULO — e nulo faz o webhook calar")
    checar('.eq("agent_role", "attendance")' in corpo,
           "resolve pelo PAPEL, não pelo primeiro agente que aparecer")


# ---------------------------------------------------------------------------
# A6..A7 — o CPF
# ---------------------------------------------------------------------------

def teste_o_cpf_nao_vaza_pela_tool():
    print("\n[A6] O CPF é cortado no lugar que ESCREVE, não no prompt")
    fonte = _ler("backend", "app", "agents", "tools", "infocap_tool.py")

    checar("_doc_para_o_publico" in fonte, "existe um cortador de documento")
    checar("def _summarize_detail(d: Dict[str, Any], unmasked: bool = False)" in fonte,
           "_summarize_detail recebe o público — e o padrão é MASCARAR")
    checar("def _summarize(r: Dict[str, Any], unmasked: bool = False)" in fonte,
           "_summarize recebe o público — e o padrão é MASCARAR")
    checar("unmasked=self._unmasked" in fonte,
           "o chamador informa o público real do agente")

    # Nenhum ponto imprime documento cru fora do cortador.
    #
    # A busca olha só linhas que CONSTROEM texto de saída (f-string com
    # `CPF/CNPJ:`). Sem esse recorte o teste acusava a própria docstring desta
    # correção, que cita o defeito para explicá-lo — e um teste que falha por
    # causa da explicação do conserto ensina a apagar a explicação.
    codigo = _sem_comentario_py(fonte)
    crus = [l.strip() for l in codigo.split("\n")
            if 'f"' in l and "CPF/CNPJ:" in l
            and "_doc}" not in l and "_docp}" not in l and "_docc" not in l]
    checar(not crus, "nenhum ponto imprime documento cru", f"{crus[:2]}")


def teste_o_cortador_funciona_de_verdade():
    """Teste funcional: a regra não vale se a função não fizer o que diz."""
    print("\n[A7] O cortador de documento faz o que promete")
    fonte = _ler("backend", "app", "agents", "tools", "infocap_tool.py")
    ini = fonte.index("    def _doc_para_o_publico")
    fim = fonte.index("    @property", ini)
    corpo = "class _T:\n    @staticmethod\n" + fonte[ini:fim]
    ns: dict = {"Any": object, "Optional": object}
    exec(compile(corpo, "<cortador>", "exec"), ns)  # noqa: S102 — código do próprio repo
    corta = ns["_T"]._doc_para_o_publico

    interno = corta("12345678901", True)
    segurado = corta("12345678901", False)
    checar(interno == "12345678901", "o corretor vê o documento inteiro", f"{interno}")
    checar(segurado is not None and "12345678901" not in str(segurado),
           "o segurado NÃO vê o documento inteiro", f"{segurado}")
    checar(str(segurado).endswith("8901"),
           "mas vê o suficiente para confirmar identidade", f"{segurado}")
    checar(corta(None, False) is None and corta("", True) is None,
           "documento ausente não vira texto inventado")
    checar("123" not in str(corta("123", False)),
           "documento curto demais some inteiro, não vira dica")


def main() -> int:
    print("=" * 68)
    print("QUEM ATENDE O SEGURADO — PAPEL PEDIDO E PAPEL ENTREGUE")
    print("=" * 68)
    for teste in (teste_o_motor_exige_papel,
                  teste_recusar_e_diferente_de_nao_achar,
                  teste_o_portao_pergunta_no_positivo,
                  teste_o_webhook_exige_o_papel_no_motor,
                  teste_o_pareamento_grava_o_dono,
                  teste_o_cpf_nao_vaza_pela_tool,
                  teste_o_cortador_funciona_de_verdade):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("NINGUEM RESPONDE O SEGURADO COM O PAPEL ERRADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
