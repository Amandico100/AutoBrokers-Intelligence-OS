"""O acionamento não pede o impossível, e não aceita o inventado.

📊 03/08/2026, teste adversarial do atendimento. Dois defeitos na mesma
ferramenta — `insurer_dispatch_tool.py` — e o mesmo formato: um guarda que
existe pela metade.

**O sentinela virado campo.** `missing_slots_for_subservice` devolve
`["subservico_invalido"]` quando a seguradora simplesmente NÃO faz aquele
trabalho por aquele canal. É um sentinela de handoff, irmão de `sem_corredor`.
A tool traduzia *todo* `missing_slots` em `status="missing_data"`, então o LLM
recebia a ordem de perguntar ao cliente um campo chamado "subservico_invalido".
O cliente respondia qualquer coisa, o slot continuava faltando, e **o laço nunca
terminava.**

📊 Varrendo `_PLAYBOOKS` com `missing_slots_for_subservice(pb, sub, {})`:
`colisao`, `roubo` e `incendio` — os TRÊS sinistros — caem aí em **13 de 13**
corredores, e `vidros` em 10 de 13. O caminho mais grave do produto era
justamente o que perguntava ao segurado o nome de um campo que não existe.

**O guarda que lia o comentário errado.** O comentário da guarda anti-invenção
cita o incidente *"placa e telefone inventados foram parar na seguradora"* — e o
código conferia **só telefone**. `placa='1'` e `placa='nao sei'` chegavam a
`ready_to_send`. E o guarda de telefone, `(\\d)\\1{4,}`, reprovava
`48999990000`: um celular real de Florianópolis, que é o `CASO_COMPLETO` dos
testes deste próprio repositório.

Um guarda que reprova o verdadeiro ensina a desligar o guarda.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def _carregar(dotted: str, rel: str):
    """Carrega o módulo pelo caminho, sem passar por `app.agents.__init__`.

    O `__init__` importa `graph.py`, que importa `langgraph` — e a suíte roda
    sem as dependências pesadas. É o mesmo atalho de `test_golden_do_eletricista`.
    """
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location(dotted, RAIZ / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
_carregar("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
TOOL = _carregar("app.agents.tools.insurer_dispatch_tool",
                 "app/agents/tools/insurer_dispatch_tool.py")


def _acionar(**kwargs) -> dict:
    """A tool como o runtime a chama. `_run` nunca envia nada à seguradora."""
    return TOOL.InsurerDispatchTool(company_id="corretora-A")._run(**kwargs)


# Um caso AUTO com tudo verdadeiro: CPF que fecha a conta, placa nos formatos
# legais, celular que existe. Só o subserviço muda de teste para teste.
CASO_AUTO = {
    "line_kind": "auto",
    "insurer_key": "porto",
    "titular_cpf": "52998224725",
    "veiculo_placa": "ABC1D23",
    "local_atual": "Rua Bocaiuva, 2468, Centro, Florianopolis - SC",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose SC",
    "problema_descricao": "bateu na traseira de outro carro",
    "telefone_contato": "48991234567",
    "pessoa_no_local": "Maria",
    "quando": "agora",
    "dados_confirmados": True,
}


def o_sinistro_vira_handoff_e_nao_pergunta() -> None:
    """Os três sinistros, em toda seguradora: handoff, nunca coleta."""
    for sub in ("colisao", "roubo", "incendio"):
        r = _acionar(**{**CASO_AUTO, "subservice": sub})
        checar(r["status"] == "sem_corredor",
               f"`{sub}` devolve sem_corredor, nao missing_data",
               f"status={r['status']} missing={r.get('missing')}")
        checar(r.get("handoff_necessario") is True,
               f"`{sub}` marca handoff_necessario", str(r)[:110])
        checar("request_human_agent" in r["content"],
               f"`{sub}` manda chamar o humano — como o ramo `sem_corredor` ja fazia")
        checar("subservico_invalido" not in r["content"],
               "e o nome do SENTINELA nunca chega ao texto que o LLM le",
               "foi assim que ele virou pergunta para o segurado")
        checar(not r.get("missing"),
               "e `missing` fica VAZIO — nao ha campo faltando, ha caminho faltando",
               f"missing={r.get('missing')}")


def a_pergunta_impossivel_sumiu() -> None:
    """O texto que o LLM recebe nao pode mandar perguntar nada ao cliente."""
    r = _acionar(**{**CASO_AUTO, "subservice": "colisao"})
    for proibido in ("Ainda faltam estes dados", "PROCURE cada um na CONVERSA",
                     "Pergunte ao cliente SOMENTE"):
        checar(proibido not in r["content"],
               f"o texto de COLETA nao aparece: {proibido!r}",
               "era ele que mandava perguntar o campo inexistente")
    checar("não falta dado" in r["content"] or "não falta dado" in r["content"].lower(),
           "e o texto diz, com todas as letras, que nao falta dado", r["content"][:120])


def o_vidros_sem_corredor_tambem_sai_do_laco() -> None:
    """📊 `vidros` cai no sentinela em 10 dos 13 corredores."""
    sem = [ref for ref, pb in PB._PLAYBOOKS.items()
           if PB.missing_slots_for_subservice(pb, "vidros", {}) == [PB.SUBSERVICO_INVALIDO]]
    checar(len(sem) >= 8,
           f"`vidros` cai no sentinela em {len(sem)} de {len(PB._PLAYBOOKS)} corredores",
           "se isto cair a zero, o teste abaixo deixou de olhar alguma coisa")
    r = _acionar(**{**CASO_AUTO, "insurer_key": "bradesco", "subservice": "vidros",
                    "problema_descricao": "parabrisa trincado"})
    checar(r["status"] == "sem_corredor",
           "e a bradesco em vidros vira handoff, nao interrogatorio", str(r)[:120])


def o_que_a_seguradora_FAZ_continua_passando() -> None:
    """O controle: o conserto nao pode transformar trabalho valido em handoff."""
    r = _acionar(**{**CASO_AUTO, "subservice": "guincho",
                    "problema_descricao": "carro nao liga"})
    checar(r["status"] == "ready_to_send",
           "guincho na porto continua chegando a ready_to_send",
           f"status={r['status']} {str(r)[:130]}")
    r2 = _acionar(**{**CASO_AUTO, "subservice": "guincho",
                     "problema_descricao": "carro nao liga",
                     "telefone_contato": ""})
    checar(r2["status"] == "missing_data" and r2.get("missing") == ["telefone_contato"],
           "e DADO que falta de verdade continua sendo missing_data",
           f"{str(r2)[:130]}")


# ------------------------------------------------------------------ #
# O guarda anti-invenção
# ------------------------------------------------------------------ #

def a_placa_agora_e_conferida() -> None:
    """O comentario citava a placa; o codigo so conferia telefone."""
    for falsa in ("1", "nao sei", "não sei", "XYZ", "ABCDEFG", "0000000", "ABC12"):
        r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "veiculo_placa": falsa,
                        "problema_descricao": "pane"})
        checar(r["status"] == "missing_data" and r.get("missing") == ["veiculo_placa"],
               f"placa {falsa!r} e RECUSADA", f"status={r['status']} {str(r)[:100]}")

    for boa in ("ABC1D23", "ABC1234", "abc1d23", "ABC-1234", "abc 1d23"):
        r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "veiculo_placa": boa,
                        "problema_descricao": "pane"})
        checar(r["status"] == "ready_to_send",
               f"e a placa REAL {boa!r} passa nos dois formatos legais",
               f"status={r['status']} {str(r)[:100]}")


def o_cpf_agora_e_conferido() -> None:
    """CPF pelo DIGITO VERIFICADOR — onze digitos nao fazem um CPF."""
    for falso in ("1", "nao sei", "11122233344", "12345678901", "11111111111", "000"):
        r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "titular_cpf": falso,
                        "problema_descricao": "pane"})
        checar(r["status"] == "missing_data" and r.get("missing") == ["titular_cpf"],
               f"CPF {falso!r} e RECUSADO", f"status={r['status']} {str(r)[:100]}")

    for bom in ("52998224725", "529.982.247-25", "39053344705"):
        r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "titular_cpf": bom,
                        "problema_descricao": "pane"})
        checar(r["status"] == "ready_to_send", f"e o CPF valido {bom!r} passa",
               f"status={r['status']} {str(r)[:100]}")

    # CNPJ: o titular pode ser PESSOA JURIDICA (condominio, empresa). Reprovar
    # um CNPJ verdadeiro travaria carteira inteira no residencial.
    r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "titular_cpf": "11222333000181",
                    "problema_descricao": "pane"})
    checar(r["status"] == "ready_to_send",
           "e o CNPJ de um condominio/empresa tambem passa — a URA pede 'CPF ou CNPJ'",
           f"status={r['status']} {str(r)[:100]}")


def o_telefone_real_deixa_de_ser_reprovado() -> None:
    """O guarda antigo (`(\\d)\\1{4,}`) reprovava o numero do proprio repo."""
    checar(TOOL.telefone_br_valido("48999990000"),
           "48999990000 e ACEITO — celular real de Florianopolis",
           "e o `CASO_COMPLETO` de test_o_acionamento_nao_trava.py")
    r = _acionar(**{**CASO_AUTO, "subservice": "guincho",
                    "telefone_contato": "48999990000", "problema_descricao": "pane"})
    checar(r["status"] == "ready_to_send",
           "e o acionamento inteiro passa com ele", f"{str(r)[:110]}")

    # A prova de que o guarda continua guardando alguma coisa.
    for falso, porque in (
        ("11111111111", "todos os digitos iguais"),
        ("00999990000", "DDD 00 nao existe"),
        ("10999990000", "DDD 10 nao existe"),
        ("48199990000", "celular sem o 9 inicial"),
        ("999990000", "curto demais"),
        ("48988888888", "oito digitos repetidos seguidos"),
    ):
        r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "telefone_contato": falso,
                        "problema_descricao": "pane"})
        checar(r["status"] == "missing_data" and r.get("missing") == ["telefone_contato"],
               f"e {falso!r} continua recusado ({porque})",
               f"status={r['status']} {str(r)[:100]}")


def o_guarda_tem_como_falhar() -> None:
    """Validadores que devolvessem True para tudo passariam nos checks de cima
    que exigem `ready_to_send`. Aqui eles precisam RECUSAR — e aceitar."""
    aceita_tudo = [v for v in ("", "1", "x", "nao sei", "00000000000")
                   if TOOL.telefone_br_valido(v) or TOOL.placa_br_valida(v)
                   or TOOL.documento_br_valido(v)]
    checar(not aceita_tudo, "nenhum validador aceita lixo", f"aceitou: {aceita_tudo}")

    recusa_tudo = [v for v, f in (("48999990000", TOOL.telefone_br_valido),
                                  ("ABC1D23", TOOL.placa_br_valida),
                                  ("52998224725", TOOL.documento_br_valido))
                   if not f(v)]
    checar(not recusa_tudo, "e nenhum recusa o verdadeiro", f"recusou: {recusa_tudo}")

    # E o campo VAZIO nao e "invalido": e ausente, e quem trata ausencia e
    # `missing_slots`. Confundir os dois faria o guarda roubar a coleta.
    r = _acionar(**{**CASO_AUTO, "subservice": "guincho", "veiculo_placa": "",
                    "problema_descricao": "pane"})
    checar(r["status"] == "missing_data" and "veiculo_placa" in (r.get("missing") or []),
           "campo VAZIO cai na coleta normal, nao no guarda de formato",
           str(r)[:120])
    checar("não é válido" not in r["content"],
           "e a mensagem e a de coleta, nao a de invalidez",
           "dizer 'invalido' para um campo vazio confunde o LLM e o cliente")


def main() -> int:
    print(__doc__)
    print("== o sinistro vira handoff, e nao pergunta ==")
    o_sinistro_vira_handoff_e_nao_pergunta()
    print("== a pergunta impossivel sumiu ==")
    a_pergunta_impossivel_sumiu()
    print("== vidros sem corredor tambem sai do laco ==")
    o_vidros_sem_corredor_tambem_sai_do_laco()
    print("== e o que a seguradora FAZ continua passando ==")
    o_que_a_seguradora_FAZ_continua_passando()
    print("== a placa agora e conferida ==")
    a_placa_agora_e_conferida()
    print("== o CPF agora e conferido ==")
    o_cpf_agora_e_conferido()
    print("== o telefone real deixa de ser reprovado ==")
    o_telefone_real_deixa_de_ser_reprovado()
    print("== o guarda tem como falhar ==")
    o_guarda_tem_como_falhar()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O ACIONAMENTO NAO PEDE O IMPOSSIVEL, E NAO ACEITA O INVENTADO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
