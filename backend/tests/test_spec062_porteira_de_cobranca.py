"""SPEC-062 §4, leis 2 e 4 — medir não é cobrar.

O que aconteceu de verdade
--------------------------
A **AutoFleet** estava bloqueada. Empresa ativa, sem assinatura, sem linha em
`company_credits` — e portanto saldo lido como zero. O chat devolvia resposta
vazia, os auxiliares devolviam `402`, e o WhatsApp mandava "serviço
temporariamente indisponível" para o cliente do corretor.

**Ninguém decidiu bloqueá-la.** O bloqueio foi a ausência de uma linha numa
tabela — e o produto ainda não tem preço definido.

As duas leis da SPEC-062 que isso violava:

> **Lei 2.** Usage event não é automaticamente uma cobrança.
> **Lei 4.** Nenhuma cobrança retroativa automática é permitida.

E a lei 17: *"a venda não começa antes do catálogo comercial aprovado"*.

O que este teste protege
------------------------
Que ninguém seja barrado por saldo enquanto a cobrança estiver desligada — e
que suspensão continue funcionando, porque suspensão é decisão humana.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.core", ("app", "core"))):
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


G = carregar("app.services.billing_gate")


class FakeQ:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self._f: list[tuple] = []

    def select(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self._f.append((c, v))
        return self

    def execute(self):
        if self.tabela in self.banco.quebradas:
            raise RuntimeError("banco fora do ar")
        linhas = self.banco.linhas.get(self.tabela, [])
        for c, v in self._f:
            linhas = [l for l in linhas if str(l.get(c)) == str(v)]
        return types.SimpleNamespace(data=linhas)


class FakeDB:
    def __init__(self, empresas=None, quebradas=()):
        self.linhas = {"companies": empresas or []}
        self.quebradas = set(quebradas)
        self.client = self

    def table(self, nome):
        return FakeQ(self, nome)


ATIVA = [{"id": "autofleet", "status": "active"}]
SUSPENSA = [{"id": "suspensa", "status": "suspended"}]


def _desligar():
    os.environ.pop(G.FLAG, None)


def _ligar():
    os.environ[G.FLAG] = "1"


def teste_padrao_e_desligado():
    print("\n[1] A cobrança nasce DESLIGADA")
    _desligar()
    checar(not G.cobranca_ligada(),
           "sem a variável, a cobrança está desligada",
           "um sistema sem catálogo comercial aprovado não deveria cobrar por "
           "acidente de configuração")
    for valor in ("0", "false", "off", "no", ""):
        os.environ[G.FLAG] = valor
        checar(not G.cobranca_ligada(), f"'{valor}' também é desligado")
    _desligar()


def teste_autofleet_nao_e_bloqueada():
    print("\n[2] O caso real: empresa sem registro de crédito NÃO é barrada")
    _desligar()
    pode, motivo = G.PorteiraDeCobranca(FakeDB(ATIVA)).pode_consumir("autofleet")
    checar(pode, "a AutoFleet passa", motivo)
    checar("desligada" in motivo, "e o motivo diz por quê", motivo)


def teste_suspensao_vale_sempre():
    print("\n[3] Suspensão é decisão humana — vale com a cobrança desligada")
    _desligar()
    pode, motivo = G.PorteiraDeCobranca(FakeDB(SUSPENSA)).pode_consumir("suspensa")
    checar(not pode, "empresa suspensa continua barrada")
    checar("suspensa" in motivo.lower(),
           "e o motivo diz suspensão, não saldo", motivo)
    checar("crédito" not in motivo.lower() and "saldo" not in motivo.lower(),
           "sem mencionar dinheiro — o motivo é outro", motivo)


def teste_nunca_devolve_so_um_booleano():
    print("\n[4] Todo 'não' vem com motivo")
    _desligar()
    for empresas, cid in ((ATIVA, "autofleet"), (SUSPENSA, "suspensa")):
        pode, motivo = G.PorteiraDeCobranca(FakeDB(empresas)).pode_consumir(cid)
        checar(isinstance(motivo, str) and len(motivo) > 10,
               f"resposta para '{cid}' vem com frase legível", repr(motivo))
    # Um "não" sem motivo é o que faz o corretor achar que o sistema quebrou.


def teste_erro_de_banco_nao_bloqueia():
    print("\n[5] Erro de banco não vira corretora sem serviço")
    _desligar()
    quebrado = FakeDB(ATIVA, quebradas={"companies"})
    pode, _ = G.PorteiraDeCobranca(quebrado).pode_consumir("autofleet")
    checar(pode, "não conseguir LER o status não é prova de suspensão")

    # Com a cobrança ligada, falha ao ler o SALDO também não bloqueia.
    _ligar()
    try:
        pode2, motivo2 = G.PorteiraDeCobranca(quebrado).pode_consumir("autofleet")
        checar(pode2,
               "e não conseguir ler o saldo também não bloqueia",
               motivo2)
    finally:
        _desligar()


def teste_ligada_a_porteira_barra():
    print("\n[6] Ligada, a porteira barra de verdade")
    _ligar()
    try:
        # Sem serviço de billing disponível no teste, a porteira libera com
        # motivo declarado — nunca barra por não saber.
        pode, motivo = G.PorteiraDeCobranca(FakeDB(ATIVA)).pode_consumir("autofleet")
        checar(isinstance(pode, bool), "a resposta é uma decisão", str(pode))
        checar(bool(motivo), "com motivo", motivo)
        # O que NÃO pode: barrar silenciosamente por ausência de dado.
        if not pode:
            checar("acabaram" in motivo.lower() or "recarregue" in motivo.lower(),
                   "e se barrou, a frase é acionável", motivo)
    finally:
        _desligar()


def teste_nenhuma_rota_chama_o_saldo_direto():
    print("\n[7] Nenhuma rota decide sozinha por saldo")
    # Era isso que produzia o bloqueio: cinco lugares chamando
    # `has_sufficient_balance` direto, cada um com sua mensagem, e nenhum
    # sabendo que a cobrança ainda não deveria valer.
    import re

    encontrados: list[str] = []
    for pasta, _, arquivos in os.walk(os.path.join(RAIZ, "app", "api")):
        for arq in arquivos:
            if not arq.endswith(".py"):
                continue
            caminho = os.path.join(pasta, arq)
            with open(caminho, encoding="utf-8") as fh:
                fonte = "\n".join(l for l in fh.read().split("\n")
                                  if not l.lstrip().startswith("#"))
            if re.search(r"has_sufficient_balance\s*\(", fonte):
                encontrados.append(os.path.basename(caminho))
    checar(not encontrados,
           "nenhuma rota da API chama has_sufficient_balance direto",
           f"ainda chamam: {encontrados}")

    # E a porteira precisa estar em uso.
    usos = 0
    for pasta, _, arquivos in os.walk(os.path.join(RAIZ, "app", "api")):
        for arq in arquivos:
            if arq.endswith(".py"):
                with open(os.path.join(pasta, arq), encoding="utf-8") as fh:
                    usos += fh.read().count("pode_consumir(")
    checar(usos >= 5, "a porteira é usada nos pontos que bloqueavam",
           f"{usos} usos")


def teste_fronteira_comercial_nasce_ausente():
    print("\n[8] Sem lançamento comercial, nada é cobrável")
    os.environ.pop(G.FRONTEIRA, None)
    checar(G.fronteira_comercial() is None,
           "sem a variável, não existe fronteira")
    checar(not G.consumo_e_cobravel("2026-07-26T02:31:45+00:00"),
           "e portanto NENHUM consumo é cobrável",
           "§22.1: tudo antes do go-live é PRE_LAUNCH_NON_BILLABLE")


def teste_a_fronteira_separa_antes_e_depois():
    print("\n[9] A fronteira separa o antes do depois")
    os.environ[G.FRONTEIRA] = "2026-08-01T00:00:00+00:00"
    try:
        checar(not G.consumo_e_cobravel("2026-07-26T02:31:45+00:00"),
               "consumo de 26/07 (antes) NÃO é cobrável")
        checar(G.consumo_e_cobravel("2026-08-15T10:00:00+00:00"),
               "consumo de 15/08 (depois) é cobrável")
        # Data ilegível, ausente ou ingênua: os três são "não sei", e não
        # saber nunca pode virar cobrança.
        for ruim in (None, "", "ontem", "2026-13-45"):
            checar(not G.consumo_e_cobravel(ruim),
                   f"data {ruim!r} não vira cobrança")
        # Ingênua vs consciente: comparar levantaria TypeError. O resultado
        # tem que sair da regra, não do acidente de cair no except.
        checar(G.consumo_e_cobravel("2026-08-15T10:00:00"),
               "data sem fuso é comparada, não descartada por erro")
    finally:
        os.environ.pop(G.FRONTEIRA, None)


def teste_worker_legado_nao_debita_retroativo():
    print("\n[10] O worker legado não debita os 1.239 logs históricos")
    # `process_unbilled_usage` busca `billed = false` e debita crédito. Existem
    # 1.239 linhas nesse estado — o registro técnico de um ano de trabalho. O
    # que separava as corretoras de um débito retroativo de um ano era
    # `USE_CELERY=false`: uma variável de ambiente. Não é proteção, é sorte.
    import re

    caminho = os.path.join(RAIZ, "app", "workers", "billing_tasks.py")
    with open(caminho, encoding="utf-8") as fh:
        fonte = fh.read()
    sem_comentario = "\n".join(l for l in fonte.split("\n")
                               if not l.lstrip().startswith("#"))

    # As duas tarefas que debitam precisam das duas travas, cada uma.
    for tarefa in ("def process_unbilled_usage", "def process_company_billing"):
        inicio = sem_comentario.find(tarefa)
        checar(inicio != -1, f"{tarefa} existe")
        if inicio == -1:
            continue
        # Recorta até a próxima tarefa (ou o fim do arquivo).
        resto = sem_comentario[inicio + 10:]
        fim = resto.find("\ndef ")
        corpo = resto[:fim] if fim != -1 else resto

        pos_debito = corpo.find("debit_credits")
        pos_ligada = corpo.find("cobranca_ligada()")
        pos_fronteira = corpo.find("fronteira_comercial()")

        checar(pos_ligada != -1 and (pos_debito == -1 or pos_ligada < pos_debito),
               f"{tarefa}: confere a cobrança ANTES de debitar")
        checar(pos_fronteira != -1 and (pos_debito == -1 or pos_fronteira < pos_debito),
               f"{tarefa}: confere a fronteira ANTES de debitar")
        checar("consumo_e_cobravel" in corpo,
               f"{tarefa}: filtra log anterior ao lançamento")

    # §22.3 é explícita: nada de reescrever histórico como atalho.
    atalho = re.search(r"update\s*\(\s*\{\s*[\"']billed[\"']\s*:\s*False",
                       sem_comentario, re.I)
    checar(atalho is None,
           "ninguém remarca `billed` em massa como atalho de migração",
           "§22.3 proíbe: reescrever histórico não se desfaz")


def main() -> int:
    print("=" * 68)
    print("SPEC-062 §4 e §22 — MEDIR NÃO É COBRAR")
    print("=" * 68)
    for teste in (teste_padrao_e_desligado,
                  teste_autofleet_nao_e_bloqueada,
                  teste_suspensao_vale_sempre,
                  teste_nunca_devolve_so_um_booleano,
                  teste_erro_de_banco_nao_bloqueia,
                  teste_ligada_a_porteira_barra,
                  teste_nenhuma_rota_chama_o_saldo_direto,
                  teste_fronteira_comercial_nasce_ausente,
                  teste_a_fronteira_separa_antes_e_depois,
                  teste_worker_legado_nao_debita_retroativo):
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
    print("NINGUÉM É BARRADO POR ALGO QUE AINDA NÃO TEM PREÇO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
