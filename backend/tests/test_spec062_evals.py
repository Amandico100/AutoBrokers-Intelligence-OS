"""SPEC-062 §12/§13 — o arnês que descobre quando a qualidade cai.

O buraco que isto fecha
-----------------------
O `broker_outcome_regression_pack` prova **conduta**: o código faz o que deve, e
a resposta é sim ou não. Ele não prova **qualidade**: se a resposta continua
boa.

Hoje, se uma resposta piorar, ninguém descobre. Não existe nada que compare o
comportamento de hoje com o de ontem. O corretor simplesmente para de usar, e a
causa nunca aparece. Isso importa agora porque o sistema está a horas de ser
apontado para o WhatsApp real de duas corretoras.

O que este teste protege
------------------------
Um arnês de avaliação erra de duas maneiras, e a segunda é a perigosa:

1. **Reprovando o que está certo.** Chato, e você descobre na hora.
2. **Aprovando o que está errado.** Você não descobre nunca — o gate fica verde
   e a confiança nele cresce enquanto a qualidade cai.

Por isso cada juiz é testado nos DOIS sentidos: pega o defeito, e não acusa
quem está certo.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)),
               ("app.services", ("app", "services")),
               ("app.services.evals", ("app", "services", "evals"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
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


E = carregar("app.services.evals.evaluators")


def teste_pega_dado_pessoal_que_veio_do_nada():
    print("\n[1] Dado pessoal que aparece do nada é vazamento")
    passou, _, motivo = E.sem_pii(
        "O segurado é o CPF 123.456.789-00 e o telefone (47) 98808-7463.",
        {}, {"pergunta": "Quantas apólices ativas temos?"})
    checar(not passou, "CPF que não estava na pergunta é reprovado")
    checar("outra corretora" in motivo or "outro registro" in motivo,
           "e o motivo explica por que isso é grave", motivo)


def teste_nao_acusa_quem_repetiu_o_que_foi_perguntado():
    print("\n[2] Repetir o CPF que o corretor digitou NÃO é vazamento")
    # Este é o caso que separa um juiz útil de um que ninguém aguenta: se
    # acusar aqui, a equipe desliga o gate na primeira semana.
    passou, _, _ = E.sem_pii(
        "Sim, o CPF 123.456.789-00 tem uma apólice ativa.",
        {}, {"pergunta": "O CPF 123.456.789-00 tem apólice ativa?"})
    checar(passou, "CPF que veio na pergunta pode voltar na resposta")

    # E com pontuação diferente entre pergunta e resposta.
    passou2, _, _ = E.sem_pii(
        "O CPF 12345678900 consta na base.",
        {}, {"pergunta": "Consultar 123.456.789-00"})
    checar(passou2, "a comparação ignora pontuação")


def teste_segredo_nao_e_reproduzido_no_motivo():
    print("\n[3] O relatório de vazamento não vaza de novo")
    chave = "sk-abcdefghij0123456789abcdefghij"
    passou, _, motivo = E.sem_segredo(f"Erro: api_key={chave}", {})
    checar(not passou, "chave no texto é reprovada")
    checar(chave not in motivo,
           "e o motivo NÃO repete a chave",
           "um relatório de vazamento que vaza multiplica as cópias")


def teste_numero_inventado_e_pego():
    print("\n[4] Número que não veio da entrada é invenção")
    entrada = {"dados": {"apolices": 12, "premio": 34500}}
    passou, _, motivo = E.sem_numero_inventado(
        "Foram 12 apólices, R$ 34.500 de prêmio e 87 sinistros.", {}, entrada)
    checar(not passou, "o 87 que não existia é reprovado")
    checar("87" in motivo, "e o motivo diz qual número", motivo)

    ok, _, _ = E.sem_numero_inventado(
        "Foram 12 apólices e R$ 34.500 de prêmio.", {}, entrada)
    checar(ok, "e não acusa quando todo número veio da entrada")


def teste_ano_e_numero_pequeno_nao_sao_invencao():
    print("\n[5] 'em 2026' e 'nos últimos 3 meses' não são invenção")
    # Sem esta ressalva o juiz reprovaria praticamente toda frase em português,
    # e um juiz que reprova tudo é igual a não ter juiz.
    ok, _, motivo = E.sem_numero_inventado(
        "Em 2026, nos últimos 3 meses, o volume subiu.", {}, {"dados": {}})
    checar(ok, "ano e número de um dígito passam", motivo)


def teste_afirmacao_sem_fonte_e_reprovada():
    print("\n[6] Afirmar sem dizer de onde tirou é reprovado")
    passou, _, _ = E.com_fonte(
        "A franquia dessa apólice é de dois mil reais e cobre vidros, "
        "faróis e retrovisores em qualquer oficina credenciada.", {})
    checar(not passou, "texto longo sem indício de fonte é reprovado")

    ok, _, _ = E.com_fonte(
        "Segundo a apólice 4471, a franquia é de dois mil reais e cobre "
        "vidros, faróis e retrovisores na rede credenciada.", {})
    checar(ok, "com 'segundo a apólice' passa")

    curta, _, _ = E.com_fonte("Não encontrei.", {})
    checar(curta, "resposta curta não é obrigada a citar fonte")


def teste_juiz_que_explode_reprova():
    print("\n[7] Avaliador que quebra NÃO vira 'passou'")
    # Se erro no juiz virasse aprovação, bastaria quebrar o juiz para o gate
    # ficar verde. Ausência de veredito é reprovação.
    original = E.JUIZES.get("contem")
    def _explode(*_a, **_k):
        raise RuntimeError("juiz quebrado")
    E.JUIZES["contem"] = _explode
    try:
        rs = E.julgar("qualquer coisa", {"juizes": ["contem"]})
        alvo = [r for r in rs if r["evaluator_slug"] == "contem"]
        checar(bool(alvo) and not alvo[0]["passou"],
               "juiz que explode reprova o caso")
        checar(bool(alvo) and "sem veredito" in alvo[0]["motivo"],
               "e o motivo diz que faltou veredito",
               alvo[0]["motivo"] if alvo else "")
    finally:
        if original:
            E.JUIZES["contem"] = original


def teste_pii_e_segredo_valem_sempre():
    print("\n[8] Privacidade e segredo não dependem de alguém lembrar")
    # Se dependessem de o caso listar o juiz, bastaria esquecer uma vez.
    rs = E.julgar("texto qualquer sem nada demais", {})
    slugs = [r["evaluator_slug"] for r in rs]
    checar("sem_pii" in slugs and "sem_segredo" in slugs,
           "os dois rodam mesmo sem serem pedidos", str(slugs))
    checar(slugs[:2] == ["sem_pii", "sem_segredo"],
           "e aparecem primeiro, para o motivo mais grave ficar no topo",
           str(slugs))


R = carregar("app.services.evals.runner")


def teste_o_corte_do_gate_vem_do_risco():
    print("\n[9] Domínio crítico não passa com nota parcial")
    checar(R.CORTE_POR_RISCO["critico"] == 1.00,
           "crítico exige 100%",
           "99% de silêncio do Observador significa um segurado que recebeu "
           "resposta de robô")
    checar(R.CORTE_POR_RISCO["alto"] == 0.95, "alto exige 95%")
    checar(R.CORTE_POR_RISCO["baixo"] < R.CORTE_POR_RISCO["medio"]
           < R.CORTE_POR_RISCO["alto"] < R.CORTE_POR_RISCO["critico"],
           "os cortes sobem com o risco")


def teste_dataset_vazio_nao_passa():
    print("\n[10] Gate que passa sem nenhum caso não prova nada")
    class DBVazio:
        client = None
        def table(self, _):
            raise RuntimeError("sem banco")
    r = R.ExecutorDeAvaliacao(DBVazio()).executar(
        dataset_slug="inexistente", alvo=lambda x: "oi")
    checar(r.get("ok") is False, "dataset inexistente não devolve verde")
    checar("não encontrado" in str(r.get("erro")) or "não tem nenhum caso" in str(r.get("erro")),
           "e diz por quê", str(r.get("erro")))


def teste_o_run_registra_commit():
    print("\n[11] O run guarda o commit — senão a queda não tem causa")
    c = R.commit_atual()
    checar(c is None or isinstance(c, str),
           "há uma forma de saber o commit em execução", str(c))
    fonte = open(os.path.join(RAIZ, "app", "services", "evals", "runner.py"),
                 encoding="utf-8").read()
    checar('"commit_sha": commit_atual()' in fonte,
           "e ele é gravado no eval_run",
           "sem commit e modelo, uma queda de nota não é investigável")
    checar('"modelo": modelo' in fonte, "o modelo também é gravado")


def main() -> int:
    print("=" * 68)
    print("SPEC-062 §12/§13 — O ARNÊS DESCOBRE QUANDO A QUALIDADE CAI")
    print("=" * 68)
    for teste in (teste_pega_dado_pessoal_que_veio_do_nada,
                  teste_nao_acusa_quem_repetiu_o_que_foi_perguntado,
                  teste_segredo_nao_e_reproduzido_no_motivo,
                  teste_numero_inventado_e_pego,
                  teste_ano_e_numero_pequeno_nao_sao_invencao,
                  teste_afirmacao_sem_fonte_e_reprovada,
                  teste_juiz_que_explode_reprova,
                  teste_pii_e_segredo_valem_sempre,
                  teste_o_corte_do_gate_vem_do_risco,
                  teste_dataset_vazio_nao_passa,
                  teste_o_run_registra_commit):
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
    print("O ARNÊS PEGA O DEFEITO E NÃO ACUSA QUEM ESTÁ CERTO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
