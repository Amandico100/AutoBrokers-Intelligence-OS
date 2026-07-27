"""SPEC-062 §18 e §33 — o que se mede, e o que se declara pronto.

Dois jeitos de um checklist mentir
----------------------------------
1. **Dando o benefício da dúvida.** Item que não pôde ser verificado contado
   como pronto. O painel fica verde e ninguém olhou.
2. **Misturando perguntas diferentes.** "Podemos ir ao ar?" são quatro
   perguntas com donos diferentes — infraestrutura, release, corretora e
   comercial. Juntar as quatro produz um "não pronto" para um sistema que está
   funcionando, ou um "pronto" para um que não está.

Hoje o caso 2 é concreto: **não existe catálogo comercial** (D22), e isso é
decisão do Founder, não pendência técnica. Resulta e AutoFleet precisam operar
plenamente sem preço definido.

E dois jeitos de uma medição mentir
-----------------------------------
1. **Medindo só o caminho feliz** — produz um p95 lindo. A lentidão mora onde
   as coisas dão errado.
2. **Chamando ruído de estatística** — um p99 sobre 7 amostras é o pior de 7
   medições, não uma promessa que se possa fazer a um cliente.
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
               ("app.services.observability", ("app", "services", "observability")),
               ("app.services.control_plane", ("app", "services", "control_plane"))):
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


S = carregar("app.services.observability.sli")


# --------------------------------------------------------------------------
def teste_contexto_nunca_leva_conteudo():
    print("\n[1] Métrica não carrega conversa de segurado")
    # §19.3 — contexto proibido. Uma tabela de métrica é lida por muita gente e
    # exportada para gráfico; é o último lugar onde PII deveria aparecer.
    sujo = {"modelo": "claude-sonnet-5", "texto": "meu CPF é 123.456.789-00",
            "telefone": "47988087463", "message": "oi", "etapa": 3,
            "api_key": "sk-abc", "erro": False}
    limpo = S._limpar(sujo)
    for proibido in ("texto", "telefone", "message", "api_key"):
        checar(proibido not in limpo, f"'{proibido}' foi descartado", str(limpo))
    checar("modelo" in limpo and "etapa" in limpo and "erro" in limpo,
           "e o que ajuda a explicar o número permanece", str(limpo))


def teste_amostragem_e_reproduzivel():
    print("\n[2] A amostragem dá a mesma resposta em qualquer máquina")
    # `random` faria dois processos discordarem sobre o mesmo evento e tornaria
    # impossível reproduzir uma janela de medição.
    os.environ["SLI_SAMPLE_RATE"] = "0.5"
    try:
        chave = "chat.primeira_resposta_ms:empresa-x:1753900000000"
        respostas = {S._sorteia(chave) for _ in range(50)}
        checar(len(respostas) == 1,
               "a mesma chave sempre dá a mesma resposta", str(respostas))
        # E a taxa é respeitada de forma aproximada.
        amostradas = sum(S._sorteia(f"k{i}") for i in range(1000))
        checar(350 < amostradas < 650,
               f"taxa 0.5 amostra perto da metade ({amostradas}/1000)")
    finally:
        os.environ.pop("SLI_SAMPLE_RATE", None)
    checar(S._taxa() == 1.0, "sem a variável, mede TUDO",
           "a primeira semana precisa de base densa")


def teste_medir_pega_o_erro_tambem():
    print("\n[3] O cronômetro mede também quando dá erro")
    gravados: list[tuple] = []
    original = S.registrar
    S.registrar = lambda sli, valor, **k: gravados.append((sli, k.get("contexto")))
    try:
        try:
            with S.medir("teste.x"):
                raise RuntimeError("falhou")
        except RuntimeError:
            pass
        checar(len(gravados) == 1, "gravou mesmo com exceção")
        checar(gravados and gravados[0][1].get("erro") is True,
               "e marcou que houve erro", str(gravados))

        with S.medir("teste.x"):
            pass
        checar(len(gravados) == 2 and gravados[1][1].get("erro") is False,
               "no caminho feliz marca erro=False")
    finally:
        S.registrar = original


def teste_resumo_avisa_quando_e_ruido():
    print("\n[4] Poucas amostras não viram promessa")
    class FakeQ:
        def __init__(self, n): self.n = n
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def gte(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            return types.SimpleNamespace(
                data=[{"valor": float(i)} for i in range(self.n)])

    class FakeDB:
        def __init__(self, n): self.n = n
        client = None
        def table(self, _): return FakeQ(self.n)

    original = S._cliente
    try:
        S._cliente = lambda: FakeDB(7)
        r = S.resumo("teste.x")
        checar(r["amostras"] == 7, "conta as amostras")
        checar(r["base_confiavel"] is False, "7 amostras não é base confiável")
        checar("ruído" in r["frase"], "e a frase avisa", r["frase"])

        S._cliente = lambda: FakeDB(500)
        r2 = S.resumo("teste.x")
        checar(r2["base_confiavel"] is True, "500 amostras já sustenta um SLO")
        checar(r2["p50"] < r2["p95"] < r2["p99"], "os percentis sobem",
               f"{r2['p50']} {r2['p95']} {r2['p99']}")
    finally:
        S._cliente = original


def teste_sem_medicao_nao_inventa_numero():
    print("\n[5] Sem medição, o resumo NÃO inventa número")
    class Vazio:
        client = None
        def table(self, _):
            raise RuntimeError("sem banco")
    original = S._cliente
    try:
        S._cliente = lambda: Vazio()
        r = S.resumo("teste.x")
        checar(r.get("ok") is False or r.get("amostras") == 0,
               "devolve ausência, não zero disfarçado de resultado", str(r))
        for campo in ("p50", "p95", "p99"):
            checar(campo not in r, f"não devolve {campo} sem dado")
    finally:
        S._cliente = original


# --------------------------------------------------------------------------
P = carregar("app.services.control_plane.prontidao")


def teste_operar_e_vender_sao_perguntas_diferentes():
    print("\n[6] Operar e vender são perguntas diferentes")
    # É o estado de HOJE: sem catálogo comercial (D22), e Resulta e AutoFleet
    # precisam trabalhar plenamente assim.
    p = P.Prontidao(None)
    r = p.completa()
    checar("pode_operar" in r and "pode_vender" in r,
           "a resposta separa as duas")
    checar(r["niveis"]["comercial"]["pronto"] is False,
           "sem catálogo comercial, o nível comercial não está pronto")
    checar("D22" in str(r["niveis"]["comercial"]),
           "e aponta a decisão que falta", str(r["niveis"]["comercial"]["faltam"]))
    # O comercial não pode derrubar o "pode_operar".
    checar(r["pode_vender"] is False, "não dá para vender")
    checar("operar" in r["frase"].lower() or "pendência" in r["frase"].lower(),
           "a frase explica em que pé está", r["frase"])


def teste_nao_verificado_conta_como_nao_pronto():
    print("\n[7] O que não foi verificado NÃO é dado como pronto")
    # Um checklist que dá o benefício da dúvida aprova o que não olhou.
    p = P.Prontidao(None)  # sem banco de propósito
    r = p.corretora("empresa-qualquer")
    checar(r["pronto"] is False, "sem banco, a corretora não é dada como pronta")
    checar(any("banco" in f.lower() or "verific" in f.lower() for f in r["faltam"]),
           "e o motivo diz que não deu para verificar", str(r["faltam"]))


def teste_cobranca_ligada_sem_fronteira_e_perigo():
    print("\n[8] Cobrança ligada sem fronteira comercial é sinalizada")
    from app.services.billing_gate import FLAG, FRONTEIRA  # noqa: PLC0415

    os.environ[FLAG] = "1"
    os.environ.pop(FRONTEIRA, None)
    try:
        r = P.Prontidao(None).comercial()
        item = [i for i in r["itens"] if i["chave"] == "cobranca_coerente"]
        checar(bool(item) and item[0]["pronto"] is False,
               "o descompasso é detectado")
        checar(bool(item) and "PERIGO" in item[0]["frase"],
               "e é dito com todas as letras",
               item[0]["frase"] if item else "")
    finally:
        os.environ.pop(FLAG, None)


def teste_decisao_de_lancamento_e_registrada_com_evidencia():
    print("\n[9] A decisão de lançamento guarda a evidência do momento")
    fonte = open(os.path.join(RAIZ, "app", "services", "control_plane",
                              "prontidao.py"), encoding="utf-8").read()
    checar('"evidencia": self.completa(' in fonte,
           "o registro carrega o retrato da prontidão",
           "sem evidência, 'por que fomos ao ar naquele dia?' vira memória")
    checar('decisao not in ("go", "no_go", "adiado")' in fonte,
           "e só aceita decisões nomeadas")

    mig = os.path.join(RAIZ, "supabase", "migrations")
    tem = any("launch_decisions" in open(os.path.join(mig, f), encoding="utf-8").read()
              for f in os.listdir(mig) if f.endswith(".sql"))
    checar(tem, "a migration da tabela está no repositório",
           "aplicar em produção sem arquivo é o que produziu as 9 versões órfãs")


def main() -> int:
    print("=" * 70)
    print("SPEC-062 §18 e §33 — O QUE SE MEDE E O QUE SE DECLARA PRONTO")
    print("=" * 70)
    for teste in (teste_contexto_nunca_leva_conteudo,
                  teste_amostragem_e_reproduzivel,
                  teste_medir_pega_o_erro_tambem,
                  teste_resumo_avisa_quando_e_ruido,
                  teste_sem_medicao_nao_inventa_numero,
                  teste_operar_e_vender_sao_perguntas_diferentes,
                  teste_nao_verificado_conta_como_nao_pronto,
                  teste_cobranca_ligada_sem_fronteira_e_perigo,
                  teste_decisao_de_lancamento_e_registrada_com_evidencia):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("MEDE-SE PRIMEIRO; PROMETE-SE DEPOIS. E NÃO VERIFICADO NÃO É PRONTO.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
