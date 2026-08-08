# -*- coding: utf-8 -*-
"""Conversa anônima e conversa útil não são a mesma coisa. P-67.

O defeito
---------
O caminho `conversa → transcrição → carta → RAG` estava aberto de ponta a
ponta, e **nada nele perguntava "isto é sobre seguro?"**. `publicar_lote_sync`
leva `pending_review → published` sem humano nenhum no meio.

O que enganava
--------------
Havia um filtro, ele reprovava de verdade, e ele respondia OUTRA pergunta.
📊 `knowledge_cards` tem 320 cartas `rejected_pii`: o portão de dado pessoal
funciona. Mas o WhatsApp de uma corretora é um telefone de gente. O grupo do
prédio, o convite de aniversário, o cunhado pedindo dinheiro — **uma conversa
doméstica sem um único CPF passa nesse filtro sem disparar nada.** Ela está
perfeitamente anônima e continua não valendo nada para o cérebro.

📊 Em 03/08/2026 o Observador capturou 630 contatos pessoais e 2.556
transcrições. Foi revertido a tempo e zero cartas foram geradas — por sorte, e
sorte não é guarda.

A medição que fixou a régua
--------------------------
📊 08/08/2026, contra as 12.063 `published` do projeto `dcajcvlzcjbmyapmklil`,
refazendo a mesma consulta a cada ajuste do vocabulário:

    um vocabulário só, sem nomes de companhia          184  (1,53%)
    dois níveis, sem os nomes das seguradoras          399  (3,31%)  ← PIOROU
    + nomes de seguradora no nível forte               169  (1,40%)
    + dinheiro repartido em seis entradas               64  (0,53%)  ← esta

O passo que piorou é o que ensina: dois níveis com vocabulário estreito recusa
MAIS que um nível largo. O mérito não é de "ter dois níveis" — é do que está
dentro de cada um. E cada linha dessa tabela foi medida, não deduzida
(CLAUDE.md §9.2).

Os textos de seguro deste arquivo são REAIS, copiados do acervo. Os domésticos
são inventados 💭 — o acervo não tem nenhum, e é isso que este guarda protege.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROBLEMAS: list = []


def _carregar(nome: str):
    for n, p in (("app", ("app",)), ("app.services", ("app", "services")),
                 ("app.core", ("app", "core"))):
        if n not in sys.modules:
            m = types.ModuleType(n)
            m.__path__ = [os.path.join(RAIZ, *p)]
            m.__package__ = n
            sys.modules[n] = m
    spec = importlib.util.spec_from_file_location(
        f"app.services.{nome}", os.path.join(RAIZ, "app", "services", f"{nome}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"app.services.{nome}"] = mod
    spec.loader.exec_module(mod)
    return mod


C = _carregar("curadoria_cartas")


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}")
    else:
        _PROBLEMAS.append(f"{o_que}{(' — ' + evidencia) if evidencia else ''}")
        print(f"  X   {o_que}  {evidencia}")


# ── textos REAIS do acervo, 08/08/2026 ───────────────────────────────────────

DE_SEGURO = [
    ("Na rede de vidros, a consulta de andamento pelo WhatsApp exige protocolo "
     "do atendimento e placa do veículo; o retorno automático traz a loja "
     "liberada, endereço e telefone."),
    ("A Allianz encerra o atendimento por inatividade no degrau da propulsão "
     "sem reenviar a pergunta pendente e sem preservar nada do que já foi "
     "respondido."),
    ("A Yelum não aceita LINK de mapa como localização: um endereço enviado "
     "como link do Google Maps volta como 'não foi possível'."),
    "Assinaturas de herdeiros e testemunhas podem ser exigidas com firma reconhecida",
    "Prazo padrão de retorno de solicitações é de 5 dias úteis",
    "O analista pode solicitar documentos adicionais além dos padrões",
    "Cobranças alternativas costumam ter data de vencimento definida",
    "Nota fiscal de reposição é solicitada caso os reparos já tenham sido realizados",
    ("Quando o pagamento em cartão não é autorizado, a seguradora gera boleto "
     "com novo prazo de vencimento"),
    ("A reguladora tem até dois dias úteis para agendar vistoria após a "
     "abertura do sinistro"),
]

# 💭 INVENTADOS — e inventados de propósito. O acervo não tem papo doméstico
# porque a captura de 03/08 foi revertida antes de virar carta. O dia em que
# tiver, é este guarda que decide.
DOMESTICAS = [
    "Oi amor, quando você vai no mercado? Traz pão e leite",
    "A festa de aniversário da Maria vai ser no salão do prédio, sábado às três",
    "O grupo do prédio combina o churrasco de domingo sempre por mensagem",
    "Manda a foto do bolo no WhatsApp para a família toda ver",
    "Bom dia a todos, que hoje seja um dia abençoado para cada um de vocês",
    "O cunhado pediu dinheiro emprestado de novo e ficou de devolver no mês que vem",
    "Combinar o almoço de domingo com antecedência evita conflito de horário",
    "A escola avisou que a reunião de pais mudou para quinta à noite",
]

# REAIS, e recusadas — as 📊 64 de 08/08/2026. São trabalho de escritório que
# serviria a uma pizzaria: não ensinam seguro a ninguém.
SEM_VALOR_REAIS = [
    "Reentrar no sistema (logout/login) pode resolver falhas de exibição de dados",
    ("Problemas de conexão via QR Code podem ser resolvidos dando refresh na "
     "página e gerando um novo QR Code"),
    ("É comum informar previamente o DDD do número que fará o contato para "
     "evitar que o cliente ignore a ligação"),
]


# ── 1. ele diz SIM para seguro de verdade ────────────────────────────────────

def teste_carta_de_seguro_real_passa():
    print("\n[1] As cartas REAIS do acervo continuam entrando")
    for texto in DE_SEGURO:
        checar(C.e_sobre_seguro(texto), f"passa · {texto[:58]}...")


# ── 2. ele diz NÃO — e esta é a linha que dá direito à conclusão ─────────────

def teste_papo_pessoal_e_recusado():
    print("\n[2] E o papo de casa não")
    for texto in DOMESTICAS:
        checar(not C.e_sobre_seguro(texto), f"recusa · {texto[:58]}...",
               "esta carta iria para o RAG da corretora")

    # 🔴 CONTROLE — sem ele o teste [1] seria passado por uma função que
    # devolve `True` sempre, e ninguém saberia. A prova de que a régua CONSEGUE
    # dizer não é o que dá direito a acreditar quando ela diz sim.
    checar(any(not C.e_sobre_seguro(t) for t in DOMESTICAS),
           "CONTROLE: a regra é capaz de recusar alguma coisa",
           "uma função que sempre aceita passaria no teste [1] sem filtrar nada")
    checar(any(C.e_sobre_seguro(t) for t in DE_SEGURO),
           "CONTROLE 2: e é capaz de aceitar alguma coisa",
           "uma função que sempre recusa passaria no teste [2] sem filtrar nada")


def teste_a_conduta_generica_que_serviria_a_uma_pizzaria_sai():
    print("\n[3] O que sobra nas 64 recusadas REAIS é o que deve sobrar")
    for texto in SEM_VALOR_REAIS:
        checar(not C.e_sobre_seguro(texto), f"recusa · {texto[:58]}...")


# ── 3. os dois níveis existem MESMO ──────────────────────────────────────────

def teste_uma_palavra_de_trabalho_nao_basta_e_duas_bastam():
    print("\n[4] O nível fraco exige DUAS menções — e é um limiar de verdade")
    # 💭 Frase construída para bater em UMA entrada de `_TRABALHO` (`prazo`) e
    # em nenhuma de `_SOBRE_SEGURO`.
    uma = "O prazo combinado para a entrega da encomenda foi de tres dias"
    duas = "O prazo combinado para a analise do documento foi de tres dias"
    checar(not C.e_sobre_seguro(uma), "uma palavra do trabalho não basta", uma)
    checar(C.e_sobre_seguro(duas), "duas bastam", duas)

    # 🔴 CONTROLE — as duas frases têm de ser MESMO diferentes aos olhos da
    # regra. Se as duas fossem recusadas (ou aceitas) por outro motivo, o par
    # não provaria nada sobre o limiar. Aqui a diferença é uma palavra só.
    checar(C.e_sobre_seguro(uma) != C.e_sobre_seguro(duas),
           "CONTROLE: trocar UMA palavra muda a decisão",
           f"uma={C.e_sobre_seguro(uma)} duas={C.e_sobre_seguro(duas)}")
    checar(C.MENCOES_DE_TRABALHO == 2,
           "e o limiar declarado é o que está sendo exercido",
           str(C.MENCOES_DE_TRABALHO))


def teste_o_nome_da_seguradora_sozinho_ja_e_assunto():
    print("\n[5] O nome da companhia, sozinho, prova o assunto")
    # REAL: a carta do acervo observado descreve o robô do outro lado e pode
    # não escrever nenhuma outra palavra de seguro.
    so_o_nome = "A Yelum pergunta o nome duas vezes na mesma sessao"
    checar(C.e_sobre_seguro(so_o_nome), "com o nome, passa", so_o_nome)

    # 🔴 CONTROLE: a MESMA frase sem o nome tem de ser recusada. Sem esta
    # linha, "passou" poderia ser mérito de qualquer outra palavra da frase.
    sem_o_nome = so_o_nome.replace("A Yelum", "A empresa")
    checar(not C.e_sobre_seguro(sem_o_nome),
           "CONTROLE: sem o nome, a mesma frase é recusada", sem_o_nome)

    # E `caixa` continua fora: 📊 31 das 80 ocorrências são "caixa d'água".
    checar("caixa" in C._NOME_AMBIGUO,
           "`caixa` continua na lista de nome ambíguo")


def teste_a_regra_nao_chama_modelo_nenhum():
    print("\n[6] Determinística: sem LLM, sem rede, sem custo")
    fonte = open(os.path.join(RAIZ, "app", "services", "curadoria_cartas.py"),
                 encoding="utf-8").read()
    i = fonte.find("def e_sobre_seguro")
    corpo = fonte[i:fonte.find("\ndef ", i + 10)]
    for proibido in ("openai", "OpenAI", "requests", "httpx", "await ", "embed"):
        checar(proibido not in corpo, f"não usa {proibido!r}")
    # CONTROLE: a mesma carta, mil vezes, dá a mesma resposta. Um modelo não
    # promete isso — e é por isso que ele não pode estar aqui.
    r = {C.e_sobre_seguro(DE_SEGURO[0]) for _ in range(200)}
    checar(r == {True}, "CONTROLE: 200 chamadas, uma resposta só", str(r))


# ── 4. o portão está no caminho, e a marca não mente ─────────────────────────

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
        if self.acao == "select" and coluna == "status":
            self.filtro = valor
        self.igual = (coluna, valor)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, _n):
        return self

    def update(self, payload):
        self.acao, self.payload = "update", payload
        return self

    def execute(self):
        if self.acao == "select":
            if self.igual and self.igual[0] == "pii_check->>qdrant_pendente":
                return _Resposta([])
            return _Resposta([dict(c) for c in self.db.fila])
        self.db.escritas.append((self.igual[1], dict(self.payload)))
        for c in self.db.fila:
            if c["id"] == self.igual[1]:
                c.update(self.payload)
        return _Resposta([])


class BancoDeMentira:
    def __init__(self, fila):
        self.fila = [dict(c) for c in fila]
        self.escritas: list = []

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self, nome)


def _instalar_duplos(db, publicadas: list):
    sys.modules["app.core.database"] = types.SimpleNamespace(
        get_supabase_client=lambda: db)
    sys.modules["app.services.attendance_distiller"] = types.SimpleNamespace(
        publish_card_sync=lambda c: (publicadas.append(c["id"]) or True),
        despublicar_carta_sync=lambda *_a, **_k: True)


def teste_o_publicador_automatico_consulta_o_filtro():
    print("\n[7] O portão está NO caminho automático, não só no módulo")
    fila = [
        {"id": "boa", "card_text": DE_SEGURO[8], "insurer_key": None, "ramo": "auto"},
        {"id": "casa", "card_text": DOMESTICAS[0], "insurer_key": None, "ramo": "outro"},
    ]
    db = BancoDeMentira(fila)
    publicadas: list = []
    _instalar_duplos(db, publicadas)

    r = C.publicar_lote_sync(limite=10)
    checar(publicadas == ["boa"],
           "só a carta de seguro chegou ao publicador", str(publicadas))
    checar(r.get("fora_de_escopo") == 1,
           "e a rodada CONTA quantas barrou", str(r))

    estado = {c["id"]: c.get("status") for c in db.fila}
    checar(estado.get("casa") == C.STATUS_FORA_DE_ESCOPO,
           "a doméstica ficou achável, com status próprio", str(estado))
    # 🔴 O NOME É A INFORMAÇÃO. `rejected_pii` significa "vazou dado de
    # alguém", e esta carta não vazou nada — ela só não é sobre seguro. Um
    # nome que mente sobre o que guarda reinfecta todo leitor seguinte
    # (CLAUDE.md §12.1): o próximo a contar "quantas vazaram PII?" contaria
    # esta junto.
    checar(estado.get("casa") != "rejected_pii",
           "e NÃO foi marcada como vazamento de PII", str(estado))
    checar(estado.get("boa") == "published",
           "CONTROLE: a de seguro seguiu e foi publicada", str(estado))

    # 🔴 CONTROLE 2 — o duplo tem de conseguir ver as duas coisas. Com a fila
    # inteira sendo de seguro, `fora_de_escopo` cai a zero e ninguém é barrado.
    # Sem esta linha, "barrou 1" seria indistinguível de "barra sempre 1".
    db2 = BancoDeMentira([{"id": "a", "card_text": DE_SEGURO[0]},
                          {"id": "b", "card_text": DE_SEGURO[1]}])
    pub2: list = []
    _instalar_duplos(db2, pub2)
    r2 = C.publicar_lote_sync(limite=10)
    checar(r2.get("fora_de_escopo") == 0 and sorted(pub2) == ["a", "b"],
           "CONTROLE 2: sem carta fora de escopo, ninguém é barrado", str(r2))


def main() -> int:
    print("=" * 72)
    print("A CARTA PRECISA SER SOBRE SEGURO — P-67")
    print("=" * 72)
    for t in (teste_carta_de_seguro_real_passa,
              teste_papo_pessoal_e_recusado,
              teste_a_conduta_generica_que_serviria_a_uma_pizzaria_sai,
              teste_uma_palavra_de_trabalho_nao_basta_e_duas_bastam,
              teste_o_nome_da_seguradora_sozinho_ja_e_assunto,
              teste_a_regra_nao_chama_modelo_nenhum,
              teste_o_publicador_automatico_consulta_o_filtro):
        t()
    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print(f"REPROVADO — {len(_PROBLEMAS)} problema(s):")
        for p in _PROBLEMAS:
            print(f"  · {p}")
        return 1
    print("APROVADO — o caminho automático pergunta 'isto é sobre seguro?'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
