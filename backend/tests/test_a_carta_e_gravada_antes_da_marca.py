# -*- coding: utf-8 -*-
"""A marca é o "não volte mais". Ela não pode chegar antes do conhecimento.

O defeito — P-109
-----------------
`aplicar.py` escrevia `summary.distilled` DENTRO do laço, conversa a conversa,
e só fazia o `upsert` das cartas no fim do arquivo. As duas escritas não são
uma transação.

Se a rodada caísse entre elas — rede, chave expirada, Ctrl-C — as sessões já
marcadas ficavam **declaradas destiladas sem uma carta no acervo**. E a marca é
justamente o "não volte mais": `exportar.py` e o destilador pulam quem tem
`summary.distilled`, para sempre.

Por que enganava
----------------
As duas pontas eram assimétricas e ninguém tinha olhado para a assimetria:

    a carta  →  `on_conflict=card_hash, ignore_duplicates`  →  REFAZÍVEL
    a marca  →  ninguém apaga, ninguém audita               →  DEFINITIVA

O sintoma de uma queda no meio é uma sessão que **parece pronta**. Não há erro,
não há linha órfã, não há contagem que feche errado — a perda não deixa rastro
nenhum. Um lote de 90 conversas some em silêncio e o próximo relatório diz que
tudo correu bem.

`aplicar_seguradoras.py` já fazia o contrário de propósito, e explicava por quê
no próprio cabeçalho (`_gravar`, linhas 94-100). O conserto é copiar a ordem —
não inventar uma terceira.
"""

from __future__ import annotations

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
OUTRO = "77983f63-5424-4484-bedc-c0b72330736e"

# Fatos REAIS do acervo (08/08/2026).
FATOS = [
    ("Quando o pagamento em cartao nao e autorizado, a seguradora gera boleto "
     "com novo prazo de vencimento."),
    ("A reguladora tem ate dois dias uteis para agendar a vistoria depois da "
     "abertura do sinistro."),
]


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
        self.conflito, self.ignorar = on_conflict, ignore_duplicates
        return self

    def execute(self):
        if self.acao == "select":
            s = self.db.sessoes.get(self.igual[1])
            return _Resposta([dict(s)] if s else [])
        if self.acao == self.db.explodir_em:
            self.db.escritas.append(("QUEDA", self.acao))
            raise RuntimeError(f"queda simulada no {self.acao}")
        self.db.escritas.append((self.acao, self.tabela))
        if self.acao == "upsert":
            for linha in self.payload:
                self.db.cartas.setdefault(linha["card_hash"], linha)
        else:
            self.db.sessoes[self.igual[1]].update(self.payload)
        return _Resposta([])


class BancoDeMentira:
    def __init__(self, sessoes=(), explodir_em=None):
        self.sessoes = {s["id"]: dict(s) for s in sessoes}
        self.cartas: dict = {}
        self.escritas: list = []
        self.explodir_em = explodir_em      # "upsert" | "update" | None

    def table(self, nome):
        return _Consulta(self, nome)


def _sessao(sid=SID):
    return {"id": sid, "summary": {}}


def _arquivo(ids=(SID,)):
    fh = tempfile.NamedTemporaryFile("w", suffix=".destilado.jsonl",
                                     delete=False, encoding="utf-8")
    for sid in ids:
        fh.write(json.dumps({"id": sid, "tipo": "cobranca", "ramo": "auto",
                             "servico": "cobranca", "seguradora": "porto",
                             "resumo_conduta": [], "perguntas_na_ordem": [],
                             "fatos_reutilizaveis": FATOS, "score": 8,
                             "flags": []}, ensure_ascii=False) + "\n")
    fh.close()
    return fh.name


def _marcada(db, sid=SID) -> bool:
    return bool((db.sessoes[sid].get("summary") or {}).get("distilled"))


# ── 1. a ordem, na rodada que dá certo ───────────────────────────────────────

def teste_a_carta_entra_no_acervo_antes_da_marca():
    print("\n[1] Numa rodada normal, o upsert vem antes do update")
    db = BancoDeMentira([_sessao()])
    A.aplicar_arquivos(db, [_arquivo()], "campanha_teste")

    acoes = [a for a, _ in db.escritas]
    checar("upsert" in acoes and "update" in acoes,
           "as duas escritas aconteceram", str(acoes))
    checar(acoes.index("upsert") < acoes.index("update"),
           "e a CARTA foi gravada primeiro", str(acoes))
    checar(len(db.cartas) == 2 and _marcada(db),
           "com as duas cartas no acervo e a sessão marcada",
           f"{len(db.cartas)} cartas · marcada={_marcada(db)}")


# ── 2. a queda no meio — o que a ordem compra ───────────────────────────────

def teste_queda_depois_das_cartas_deixa_trabalho_refazivel():
    print("\n[2] Caindo entre as duas escritas, nada se perde em silêncio")
    db = BancoDeMentira([_sessao()], explodir_em="update")
    caiu = False
    try:
        A.aplicar_arquivos(db, [_arquivo()], "campanha_teste")
    except RuntimeError:
        caiu = True

    checar(caiu, "a rodada caiu de verdade", str(db.escritas))
    checar(len(db.cartas) == 2,
           "as cartas JÁ ESTÃO no acervo", f"{len(db.cartas)} cartas")
    checar(not _marcada(db),
           "e a sessão NÃO ficou com o 'não volte mais'",
           str(db.sessoes[SID]))
    # Rodar de novo termina o serviço: a carta é idempotente pelo `card_hash`
    # e a sessão ainda está na fila. É esta a definição de refazível.
    db.explodir_em = None
    A.aplicar_arquivos(db, [_arquivo()], "campanha_teste")
    checar(len(db.cartas) == 2 and _marcada(db),
           "e a segunda rodada termina o serviço sem duplicar nada",
           f"{len(db.cartas)} cartas · marcada={_marcada(db)}")


def teste_a_ordem_importa_e_a_ordem_invertida_perde_conhecimento():
    print("\n[3] 🔴 CONTROLE — a MESMA queda, na ordem antiga, apaga o lote")

    def _ordem_antiga(db, sessoes, cartas):
        """A `_gravar` de antes de 08/08/2026, reconstituída aqui.

        Ela não vive mais no repositório — e é exatamente por isso que precisa
        existir neste teste. Um guarda que só exercita a ordem CERTA não tem
        como falhar: ele passaria igual se alguém invertesse tudo de volta
        amanhã. É este bloco que prova que a diferença entre as duas ordens é
        real, e que ela custa conhecimento.
        """
        marcadas = 0
        for sid, resumo in sessoes:
            agora = dict(db.sessoes[sid].get("summary") or {})
            agora["distilled"] = resumo["distilled"]
            db.table("attendance_sessions").update({"summary": agora}) \
                .eq("id", sid).execute()
            marcadas += 1
        linhas = list(cartas.values())
        for i in range(0, len(linhas), 200):
            db.table("knowledge_cards").upsert(
                linhas[i:i + 200], on_conflict="card_hash",
                ignore_duplicates=True).execute()
        return marcadas

    # A queda é a MESMA nos dois lados: a segunda escrita falha. Só a ordem
    # muda — que é o único fator que este teste tem direito de variar.
    velho = BancoDeMentira([_sessao()], explodir_em="upsert")
    sessoes, cartas, _ = A._planejar(velho, _arquivo(), "campanha_teste")
    velho.explodir_em = "upsert"
    try:
        _ordem_antiga(velho, sessoes, cartas)
    except RuntimeError:
        pass
    checar(_marcada(velho) and not velho.cartas,
           "ordem ANTIGA: sessão declarada destilada e ZERO cartas — a perda "
           "silenciosa do P-109",
           f"marcada={_marcada(velho)} cartas={len(velho.cartas)}")

    novo = BancoDeMentira([_sessao()], explodir_em="update")
    try:
        A.aplicar_arquivos(novo, [_arquivo()], "campanha_teste")
    except RuntimeError:
        pass
    checar(not _marcada(novo) and len(novo.cartas) == 2,
           "ordem NOVA: cartas no acervo e sessão ainda na fila",
           f"marcada={_marcada(novo)} cartas={len(novo.cartas)}")

    # A linha que fecha: os dois estados são OPOSTOS. Se fossem iguais, a
    # ordem não estaria fazendo diferença nenhuma e trocá-la seria enfeite.
    checar(_marcada(velho) != _marcada(novo)
           and bool(velho.cartas) != bool(novo.cartas),
           "CONTROLE: as duas ordens produzem estados opostos — a ordem IMPORTA",
           f"antiga(marcada={_marcada(velho)}, cartas={len(velho.cartas)}) "
           f"nova(marcada={_marcada(novo)}, cartas={len(novo.cartas)})")


def teste_a_sessao_ja_destilada_nao_e_remarcada():
    print("\n[4] A releitura antes de marcar continua valendo")
    db = BancoDeMentira([_sessao()])
    sessoes, cartas, _ = A._planejar(db, _arquivo(), "campanha_teste")
    # Alguém marcou a sessão entre o plano e a escrita — outra rodada, outro
    # operador. O `_gravar` tem de respeitar quem chegou primeiro.
    db.sessoes[SID]["summary"] = {"distilled": {"por": "outra_campanha"}}
    marcadas = A._gravar(db, sessoes, cartas)
    checar(marcadas == 0, "nenhuma sessão foi remarcada", str(marcadas))
    checar(db.sessoes[SID]["summary"]["distilled"]["por"] == "outra_campanha",
           "e a marca de quem chegou primeiro ficou de pé")
    # CONTROLE: sem a corrida, a mesma chamada marca. Sem esta linha, "não
    # remarcou" seria indistinguível de "nunca marca".
    db2 = BancoDeMentira([_sessao()])
    s2, c2, _ = A._planejar(db2, _arquivo(), "campanha_teste")
    checar(A._gravar(db2, s2, c2) == 1,
           "CONTROLE: sem corrida, ela marca normalmente")


def teste_o_arquivo_com_duas_sessoes_grava_tudo_antes_de_marcar_qualquer_uma():
    print("\n[5] Com duas sessões no arquivo, nenhuma marca precede as cartas")
    db = BancoDeMentira([_sessao(SID), _sessao(OUTRO)])
    A.aplicar_arquivos(db, [_arquivo([SID, OUTRO])], "campanha_teste")
    acoes = [a for a, _ in db.escritas]

    # A PRIMEIRA escrita da rodada tem de ser uma carta. Sem esta linha o teste
    # não tinha como falhar: com a ordem invertida, `acoes.index("update")` vale
    # 0, a fatia `acoes[:0]` é vazia e `all([])` é `True`. Um guarda que passa
    # justamente no caso que ele existe para pegar não guarda nada
    # (CLAUDE.md §9.3) — descoberto pela prova por mutação, não por leitura.
    checar(acoes and acoes[0] == "upsert",
           "a PRIMEIRA escrita da rodada é uma carta", str(acoes))
    primeira_marca = acoes.index("update")
    checar(primeira_marca > 0 and all(a == "upsert" for a in acoes[:primeira_marca]),
           "e tudo o que vem antes da primeira marca também", str(acoes))
    checar(_marcada(db, SID) and _marcada(db, OUTRO),
           "com as duas sessões marcadas no fim")


def main() -> int:
    print("=" * 72)
    print("A CARTA É GRAVADA ANTES DA MARCA — P-109")
    print("=" * 72)
    for t in (teste_a_carta_entra_no_acervo_antes_da_marca,
              teste_queda_depois_das_cartas_deixa_trabalho_refazivel,
              teste_a_ordem_importa_e_a_ordem_invertida_perde_conhecimento,
              teste_a_sessao_ja_destilada_nao_e_remarcada,
              teste_o_arquivo_com_duas_sessoes_grava_tudo_antes_de_marcar_qualquer_uma):
        t()
    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print(f"REPROVADO — {len(_PROBLEMAS)} problema(s):")
        for p in _PROBLEMAS:
            print(f"  · {p}")
        return 1
    print("APROVADO — queda no meio deixa trabalho refazível, não perda muda")
    return 0


if __name__ == "__main__":
    sys.exit(main())
