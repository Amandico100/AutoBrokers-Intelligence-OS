# -*- coding: utf-8 -*-
"""Duas campanhas, duas marcas. E a marca não pode depender de memória humana.

O defeito
---------
`aplicar.py` tinha `MARCA = "destilacao_max_29_07_2026"` — uma constante
escrita à mão, no alto do arquivo, que ninguém trocou nunca.

A medição que o revelou
-----------------------
📊 As 1.941 cartas da campanha de 04/08/2026 estão no acervo com
`pii_check->>'por' = 'destilacao_max_29_07_2026'`. Duas campanhas, um marcador
só: pelo campo que existe justamente para separá-las, elas são a mesma coisa.
Só a data de criação as distingue — e a data não diz qual lote, qual prompt,
qual corretora.

Por que enganava
----------------
`CURADORIA-POR-SUBAGENTES.md:236` manda conferir a campanha assim:

    select count(*) from knowledge_cards where pii_check->>'por' = '<marca>'

A conferência RODAVA, devolvia um número e o número estava errado — somava as
duas campanhas. Um passo de conferência que responde com confiança a pergunta
errada é pior que passo nenhum: ele encerra a dúvida.

E `aplicar_seguradoras.py` já tinha acertado ao lado, com marca própria
(`destilacao_max_seguradoras_06_08_2026`). O defeito não era falta de ideia —
era o valor morar num lugar onde alguém precisa LEMBRAR de mexer.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTILACAO = os.path.join(RAIZ, "scripts", "destilacao_max")
sys.path.insert(0, DESTILACAO)

import aplicar as A            # noqa: E402

_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}")
    else:
        _PROBLEMAS.append(f"{o_que}{(' — ' + evidencia) if evidencia else ''}")
        print(f"  X   {o_que}  {evidencia}")


SID = "0d1f66ce-2dfc-4164-b5b2-e61fae919634"
FATO = ("Quando o pagamento em cartao nao e autorizado, a seguradora gera "
        "boleto com novo prazo de vencimento.")


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, db, tabela):
        self.db, self.tabela = db, tabela
        self.acao = self.payload = self.igual = None

    def select(self, _c):
        self.acao = "select"
        return self

    def eq(self, coluna, valor):
        self.igual = (coluna, valor)
        return self

    def limit(self, _n):
        return self

    def update(self, payload):
        self.acao, self.payload = "update", payload
        return self

    def upsert(self, linhas, on_conflict=None, ignore_duplicates=False):
        self.acao, self.payload = "upsert", linhas
        return self

    def execute(self):
        if self.acao == "select":
            s = self.db.sessoes.get(self.igual[1])
            return _Resposta([dict(s)] if s else [])
        self.db.escritas.append((self.acao, self.tabela))
        if self.acao == "upsert":
            for linha in self.payload:
                self.db.cartas.setdefault(linha["card_hash"], linha)
        else:
            self.db.sessoes[self.igual[1]].update(self.payload)
        return _Resposta([])


class BancoDeMentira:
    def __init__(self, sessoes=()):
        self.sessoes = {s["id"]: dict(s) for s in sessoes}
        self.cartas: dict = {}
        self.escritas: list = []

    def table(self, nome):
        return _Consulta(self, nome)


def _sessao(sid=SID):
    return {"id": sid, "summary": {}}


def _arquivo(fatos):
    fh = tempfile.NamedTemporaryFile("w", suffix=".destilado.jsonl",
                                     delete=False, encoding="utf-8")
    fh.write(json.dumps({"id": SID, "tipo": "cobranca", "ramo": "auto",
                         "servico": "cobranca", "seguradora": "porto",
                         "resumo_conduta": [], "perguntas_na_ordem": [],
                         "fatos_reutilizaveis": list(fatos), "score": 8,
                         "flags": []}, ensure_ascii=False) + "\n")
    fh.close()
    return fh.name


def _marca_gravada(db):
    return (list(db.cartas.values())[0]["pii_check"]["por"],
            db.sessoes[SID]["summary"]["distilled"]["por"])


# ── 1. a constante congelada não existe mais ─────────────────────────────────

def _so_codigo(arquivo: str) -> str:
    """O arquivo sem o docstring do topo e sem linhas de comentário.

    O cabeçalho CONTA a história e CITA a marca antiga — é documentação, e tem
    de continuar lá. O que não pode existir é ela sendo ATRIBUÍDA.
    """
    fonte = open(os.path.join(DESTILACAO, arquivo), encoding="utf-8").read()
    corpo = fonte.split('"""', 2)[-1]
    return "\n".join(l for l in corpo.splitlines()
                     if not l.lstrip().startswith("#"))


def teste_nao_ha_mais_uma_data_escrita_a_mao_no_codigo():
    print("\n[1] A data de 29/07 não está mais gravada no arquivo")
    ANTIGA = 'MARCA = "destilacao_max_29_07_2026"'
    corpo = _so_codigo("aplicar.py")
    checar(ANTIGA not in corpo,
           "nenhuma atribuição da marca de 29/07 sobrou no código")
    checar("marca_de_hoje" in corpo,
           "e existe uma função que devolve a marca do dia")

    # O mesmo defeito morava em `aplicar_sql.py`, palavra por palavra.
    corpo_sql = _so_codigo("aplicar_sql.py")
    checar(ANTIGA not in corpo_sql,
           "e nem no `aplicar_sql.py`, que tinha a MESMA linha")
    checar("from aplicar import marca_de_hoje" in corpo_sql,
           "ele importa a resposta em vez de manter a segunda cópia dela")

    # 🔴 CONTROLE — prove que este guarda CONSEGUE reprovar. Se `_so_codigo`
    # estivesse devolvendo string vazia (docstring mal fatiado, arquivo
    # renomeado), as três linhas acima passariam sem ler nada.
    inteiro = open(os.path.join(DESTILACAO, "aplicar.py"), encoding="utf-8").read()
    checar("destilacao_max_29_07_2026" in inteiro
           and "destilacao_max_29_07_2026" not in corpo,
           "CONTROLE: a marca antiga AINDA aparece no arquivo, no cabeçalho",
           "se ela sumisse daqui também, o guarda passaria por falta de texto")
    checar(len(corpo) > 2000 and len(corpo_sql) > 2000,
           "CONTROLE 2: e o que foi lido é código de verdade",
           f"{len(corpo)} e {len(corpo_sql)} caracteres")


# ── 2. duas campanhas, duas marcas — a linha de CONTROLE ────────────────────

def teste_duas_campanhas_diferentes_produzem_marcas_diferentes():
    print("\n[2] Campanhas diferentes recebem marcas diferentes")
    ontem = datetime.date(2026, 7, 29)
    hoje = datetime.date(2026, 8, 4)
    m1, m2 = A.marca_de_hoje(ontem), A.marca_de_hoje(hoje)
    checar(m1 == "destilacao_max_29_07_2026",
           "o formato antigo é preservado — o acervo já tem 5.295 assim", m1)

    # 🔴 CONTROLE — é ele que dá direito à conclusão. Sem esta linha, uma
    # função que devolvesse SEMPRE a mesma string passaria na checagem acima e
    # o defeito continuaria de pé com outro nome.
    checar(m1 != m2,
           "CONTROLE: dois dias, duas marcas — foi ISTO que faltou em 04/08",
           f"{m1} vs {m2}")
    checar(m2 == "destilacao_max_04_08_2026",
           "e a de 04/08 é a de 04/08", m2)


def teste_a_marca_escolhida_a_mao_vence_a_do_calendario():
    print("\n[3] Quem quiser nomear a campanha, nomeia")
    escolhida = "destilacao_max_reforco_autofleet"
    db = BancoDeMentira([_sessao()])
    A.aplicar_arquivos(db, [_arquivo([FATO])], escolhida)
    na_carta, na_sessao = _marca_gravada(db)
    checar(na_carta == escolhida, "a carta sai com a marca pedida", na_carta)
    checar(na_sessao == escolhida, "a sessão também", na_sessao)

    # 🔴 CONTROLE: sem `--marca`, a mesma rodada sai com OUTRA marca. Se as
    # duas fossem iguais, o argumento não estaria fazendo nada.
    db2 = BancoDeMentira([_sessao()])
    A.aplicar_arquivos(db2, [_arquivo([FATO])], A.marca_de_hoje())
    outra, _ = _marca_gravada(db2)
    checar(outra != escolhida,
           "CONTROLE: sem o argumento, a marca é outra", f"{outra} vs {escolhida}")


def teste_a_linha_de_comando_entrega_a_marca_ate_a_carta():
    print("\n[4] A marca atravessa da linha de comando até o `pii_check`")
    # A trava de credencial fica antes de qualquer escrita; aqui o teste para
    # no parser, que é o que ele quer exercitar.
    arq = _arquivo([FATO])
    lidos = {}

    def _falso_credenciais():
        lidos["chegou"] = True
        raise SystemExit(2)

    original = A._credenciais
    A._credenciais = _falso_credenciais
    try:
        codigo = 0
        try:
            A.main([arq, "--marca", "campanha_x"])
        except SystemExit as e:
            codigo = e.code
        checar(lidos.get("chegou") and codigo == 2,
               "sem credencial ele sai antes de escrever qualquer coisa")
        # CONTROLE: `--marca` sem valor é erro de uso, não marca vazia — uma
        # marca vazia gravaria `"por": ""` em milhares de cartas.
        erro = None
        try:
            A.main([arq, "--marca"])
        except SystemExit as e:
            erro = e.code
        checar(erro == 2, "CONTROLE: `--marca` sem valor é recusado", str(erro))
    finally:
        A._credenciais = original


def main() -> int:
    print("=" * 72)
    print("A MARCA DA CAMPANHA É DA CAMPANHA")
    print("=" * 72)
    for t in (teste_nao_ha_mais_uma_data_escrita_a_mao_no_codigo,
              teste_duas_campanhas_diferentes_produzem_marcas_diferentes,
              teste_a_marca_escolhida_a_mao_vence_a_do_calendario,
              teste_a_linha_de_comando_entrega_a_marca_ate_a_carta):
        t()
    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print(f"REPROVADO — {len(_PROBLEMAS)} problema(s):")
        for p in _PROBLEMAS:
            print(f"  · {p}")
        return 1
    print("APROVADO — nenhuma campanha herda o marcador da anterior")
    return 0


if __name__ == "__main__":
    sys.exit(main())
