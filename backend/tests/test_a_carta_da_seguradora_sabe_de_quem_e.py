# -*- coding: utf-8 -*-
"""O acervo observado sabe de quem é cada regra — sem repetir o erro do outro.

Por que este arquivo existe
---------------------------
Em 05/08/2026, 2.582 rótulos de seguradora foram rebaixados no acervo de
atendimento. A causa: a companhia da SESSÃO era carimbada em até 8 fatos da
conversa, e 📊 só 32,3% das cartas etiquetadas citavam a própria seguradora. O
campo guardava "apareceu numa conversa sobre a Allianz" e o nome prometia "é
regra da Allianz".

No dia seguinte nasceu um acervo com a evidência INVERTIDA: `observed_sessions`
é a corretora falando com a URA da seguradora. `insurer_key` ali não é palpite
sobre o assunto — é de quem é o robô do outro lado da linha.

📊 Medido em 06/08/2026 sobre os 918 fatos dos 18 lotes destilados até então,
com `curadoria_cartas.texto_nomeia_seguradora` sobre as chaves de
`_INSURER_ALIASES`:

    915 de 918 (99,7%)  nomeiam a própria seguradora da sessão
      0 de 918          nomeiam SÓ outra companhia
     12 de 918          nomeiam a própria E outra
      3 de 918          não nomeiam companhia nenhuma

    contra 32,3% no acervo de atendimento — a mesma medida, a outra evidência

Então `aplicar_seguradoras.py` aceita o rótulo direto. E é exatamente aí que
mora o risco de recriar o defeito de ontem num acervo novo: existe uma conversa
real com a **Porto** em que a URA diz que o titular é cliente **Azul Seguros** e
redireciona. Um fato tirado dali pode não ser sobre a Porto.

Cada guarda aqui prova as DUAS direções
---------------------------------------
Um guarda testado só contra o rótulo errado fica mais guloso a cada correção, e
o custo aparece onde ninguém olha: no rótulo CERTO que silenciosamente sumiu —
que é a única coisa que este acervo tem de melhor que o outro. Por isso todo
caso que deve ser recusado tem ao lado um caso com a mesma forma que PRECISA
sobreviver (CLAUDE.md §9.2).

Os textos de fato são reais, copiados dos `*.destilado.jsonl` de 06/08/2026.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTILACAO = os.path.join(RAIZ, "scripts", "destilacao_max")
sys.path.insert(0, DESTILACAO)

import aplicar as A            # noqa: E402
import aplicar_seguradoras as AS   # noqa: E402
from mascarar import _carregar_servico  # noqa: E402

C = _carregar_servico("curadoria_cartas")

FALHAS: list = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ── o banco de mentira ────────────────────────────────────────────────────────
#
# Ele registra CADA escrita. É isso que dá direito de afirmar que a simulação
# não grava: sem um duplo que consiga registrar escrita, "não escreveu" e "não
# soube ver" são a mesma frase.

class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, db, tabela):
        self.db, self.tabela = db, tabela
        self.acao = self.payload = self.dentro = self.igual = None

    def select(self, _campos):
        self.acao = "select"
        return self

    def in_(self, coluna, valores):
        self.dentro = (coluna, list(valores))
        return self

    def eq(self, coluna, valor):
        self.igual = (coluna, valor)
        return self

    def limit(self, _n):
        return self

    def order(self, *_a, **_k):
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
            return _Resposta(self._ler())
        self.db.escritas.append((self.acao, self.tabela, self.payload))
        if self.acao == "upsert":
            for linha in self.payload:
                # `ignore_duplicates=True`: quem já está não é reescrito.
                self.db.cartas.setdefault(linha["card_hash"], linha)
            return _Resposta(self.payload)
        if self.acao == "update":
            if self.db.explodir_no_update:
                raise RuntimeError("queda simulada ao marcar a sessão")
            self.db.sessoes[self.igual[1]].update(self.payload)
            return _Resposta([])
        raise AssertionError(f"ação não prevista: {self.acao}")

    def _ler(self):
        if self.tabela == "observed_sessions":
            if self.dentro:
                return [dict(s) for i, s in self.db.sessoes.items()
                        if i in set(self.dentro[1])]
            return [dict(self.db.sessoes[self.igual[1]])] \
                if self.igual and self.igual[1] in self.db.sessoes else []
        if self.tabela == "knowledge_cards":
            alvo = set(self.dentro[1]) if self.dentro else set()
            return [{"card_hash": h} for h in self.db.cartas if h in alvo]
        raise AssertionError(f"tabela não prevista: {self.tabela}")


class BancoDeMentira:
    def __init__(self, sessoes=()):
        self.sessoes = {s["id"]: dict(s) for s in sessoes}
        self.cartas: dict = {}
        self.escritas: list = []
        self.explodir_no_update = False

    def table(self, nome):
        return _Consulta(self, nome)


SID = "0d1f66ce-2dfc-4164-b5b2-e61fae919634"
OUTRO = "77983f63-5424-4484-bedc-c0b72330736e"


def _sessao(sid=SID, seguradora="porto", ramo=None, destilada=False):
    return {"id": sid, "insurer_key": seguradora, "ramo": ramo,
            "summary": {"distilled": {"por": "antes"}} if destilada else {}}


def _destilado(sid=SID, seguradora="porto", ramo="auto", fatos=()):
    return {"id": sid, "tipo": "sinistro", "ramo": ramo, "servico": "sinistro",
            "seguradora": seguradora, "resumo_conduta": [],
            "perguntas_na_ordem": [], "fatos_reutilizaveis": list(fatos),
            "score": 0, "flags": []}


def _arquivo(registros) -> str:
    fh = tempfile.NamedTemporaryFile("w", suffix=".destilado.jsonl",
                                     delete=False, encoding="utf-8")
    for r in registros:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    fh.close()
    return fh.name


# ── textos reais, de 06/08/2026 ───────────────────────────────────────────────

# Um dos 3 fatos REAIS (lote_020, sessão da Porto) que não nomeiam companhia
# nenhuma. Ele é conhecimento verdadeiro sobre a Porto, e é exatamente o que a
# regra do acervo de atendimento larga sem dono — a diferença entre os dois
# acervos, escrita numa frase de produção em vez de num exemplo inventado.
SEM_NOME = ("A cor do veículo é exigida também em serviços que não são "
            "guincho, como bateria nova, e vem antes da data e do endereço.")

PORTO_E_AZUL = ("A URA da Porto reconhece um CPF que não é de cliente Porto e "
                "responde que não localizou as informações na Porto mas "
                "identificou o titular como cliente Azul Seguros — o cadastro é "
                "consultado entre as empresas do grupo antes de recusar.")

AZUL_E_PORTO = ("A URA da Azul Seguros identifica pelo CPF ou CNPJ do segurado "
                "e chama o interlocutor pelo nome do titular sem confirmar se é "
                "ele: não existe o degrau de confirmação de identidade que a "
                "Porto faz por botão.")

SO_A_OUTRA = ("Clientes da Azul Seguros são atendidos pelo WhatsApp próprio da "
              "Azul Seguros, e é por lá que o guincho é aberto.")

GUINCHO = ("O prestador de guincho aguarda até trinta minutos no local e faz "
           "tentativas de contato pelo telefone informado na abertura.")

BOLETO = ("Quando a parcela do cartão não é autorizada, a seguradora gera "
          "boleto com novo vencimento e o envia pelo mesmo canal.")

CONDUTA = ("A conversa é encerrada sozinha depois de um período sem resposta, "
           "e retomar exige começar o fluxo do zero.")


# ── 1. o rótulo observado é aceito sem que o texto nomeie a seguradora ────────

def teste_o_rotulo_observado_nao_precisa_do_nome_no_texto():
    print("\n[1] A conversa É com ela — o texto não precisa dizer isso")
    chave, marcas = AS._dono_da_sessao_observada(SEM_NOME, "porto")
    checar(chave == "porto",
           "fato sem nome de companhia fica com a seguradora da sessão", str(chave))
    checar(marcas.get("acervo") == "observed_sessions",
           "e a marca diz de onde veio a confiança", str(marcas))

    # CONTROLE — a linha que dá direito à conclusão. A regra do acervo de
    # ATENDIMENTO, na MESMA frase, devolve None: lá a seguradora da sessão é
    # palpite e o texto tem de nomeá-la. Se este controle passar a devolver
    # "porto", alguém unificou as duas portas e o acervo antigo herdou de volta
    # o defeito de 05/08. Se a de cima devolver None, este acervo perdeu a
    # única vantagem que tem sobre o outro.
    antiga, _ = C.seguradora_do_fato(SEM_NOME, "porto")
    checar(antiga is None,
           "CONTROLE: a regra do acervo de atendimento recusa a MESMA frase",
           f"devolveu {antiga!r} — as duas portas deixaram de ser diferentes")

    # E as duas concordam quando o texto nomeia: a divergência é só na ausência.
    nomeando = "A URA da Porto exige o CPF do titular antes do menu."
    checar(C.seguradora_do_fato(nomeando, "porto")[0] == "porto"
           and AS._dono_da_sessao_observada(nomeando, "porto")[0] == "porto",
           "CONTROLE 2: com o nome no texto, as duas portas concordam")


# ── 2. a exceção da Porto/Azul ────────────────────────────────────────────────

def teste_o_fato_que_e_de_outra_companhia_perde_o_rotulo():
    print("\n[2] Quem age na frase é quem fica com a regra")
    chave, marcas = AS._dono_da_sessao_observada(SO_A_OUTRA, "porto")
    checar(chave is None,
           "fato que nomeia SÓ outra companhia não fica com a da sessão",
           str(chave))
    checar(marcas.get("seguradora_citada") == ["azul"],
           "e a companhia citada é registrada", str(marcas))
    checar(marcas.get("seguradora_da_sessao") == "porto",
           "junto com a da sessão — nada se perde, só é rebaixado", str(marcas))

    # CONTROLE 1: o texto REAL da conversa Porto→Azul. Ele nomeia as DUAS, e o
    # sujeito é a URA da Porto. Se o guarda comer este, ele come justamente o
    # melhor fato do acervo: o que ensina que acionar a Porto para segurado
    # Azul é caminho morto.
    chave, marcas = AS._dono_da_sessao_observada(PORTO_E_AZUL, "porto")
    checar(chave == "porto",
           "CONTROLE: o fato que nomeia as DUAS fica com a da sessão", str(chave))
    checar(marcas.get("tambem_cita") == ["azul"],
           "e a outra companhia fica registrada em `tambem_cita`", str(marcas))

    # CONTROLE 2: o mesmo caso pelo outro lado. Numa sessão da Azul que fala da
    # Porto, quem fica é a Azul. Se o guarda fosse "cita porto → cai", este
    # passaria a cair e ninguém veria.
    checar(AS._dono_da_sessao_observada(AZUL_E_PORTO, "azul")[0] == "azul",
           "CONTROLE 2: pelo outro lado, a sessão da Azul fica com a Azul")

    # CONTROLE 3: o gatilho é "cita OUTRA", não "não cita a própria". Sem esta
    # linha, um guarda que rebaixasse todo fato sem nome passaria nos de cima.
    checar(AS._dono_da_sessao_observada(CONDUTA, "porto")[0] == "porto",
           "CONTROLE 3: fato sem companhia nenhuma NÃO é rebaixado")


def teste_a_carta_rebaixada_continua_entrando_como_conhecimento():
    print("\n[3] Rebaixar tira o rótulo, não a carta")
    cartas = A._cartas_de(_destilado(fatos=[SO_A_OUTRA]), SID,
                          marca=AS.MARCA, dono=AS._dono_da_sessao_observada)
    checar(len(cartas) == 1, "a carta continua sendo gravada", str(len(cartas)))
    checar(cartas[0]["insurer_key"] is None, "sem dono", str(cartas[0]["insurer_key"]))
    checar(cartas[0]["status"] == "pending_review",
           "e em pending_review, como qualquer outra", cartas[0]["status"])
    checar(cartas[0]["pii_check"].get("seguradora_da_sessao") == "porto",
           "o caminho de volta fica gravado — é o mesmo do P-103",
           str(cartas[0]["pii_check"]))

    # CONTROLE: o caso vizinho, que NÃO é rebaixado, sai com dono. Sem ele,
    # este teste passaria igual se o script rebaixasse tudo.
    ok = A._cartas_de(_destilado(fatos=[PORTO_E_AZUL]), SID,
                      marca=AS.MARCA, dono=AS._dono_da_sessao_observada)
    checar(ok[0]["insurer_key"] == "porto",
           "CONTROLE: o fato vizinho sai com dono", str(ok[0]["insurer_key"]))


# ── 3. a seguradora vem do banco, não do arquivo ──────────────────────────────

def teste_a_seguradora_vem_do_banco_e_nao_do_arquivo():
    print("\n[4] O campo do arquivo é cópia feita por modelo; o banco é o observado")
    db = BancoDeMentira([_sessao(seguradora="porto")])
    arq = _arquivo([_destilado(seguradora="allianz", fatos=[GUINCHO])])
    r = AS.aplicar_arquivos(db, [arq], gravar=True)
    gravada = list(db.cartas.values())[0]
    checar(gravada["insurer_key"] == "porto",
           "a carta fica com a seguradora do BANCO", str(gravada["insurer_key"]))
    checar(r["contas"].get("seguradora do arquivo diverge do banco") == 1,
           "e a divergência é contada, não engolida", str(r["contas"]))
    marca = db.sessoes[SID]["summary"]["distilled"]
    checar(marca["seguradora"] == "porto",
           "o resumo da sessão também guarda a do banco", str(marca["seguradora"]))

    # CONTROLE: quando os dois concordam, nada é contado. Um contador que
    # dispara sempre não mede divergência, mede execução.
    db2 = BancoDeMentira([_sessao(seguradora="porto")])
    r2 = AS.aplicar_arquivos(db2, [_arquivo([_destilado(fatos=[GUINCHO])])], gravar=True)
    checar("seguradora do arquivo diverge do banco" not in r2["contas"],
           "CONTROLE: arquivo e banco de acordo → zero divergências",
           str(r2["contas"]))


def teste_sessao_que_nao_existe_no_banco_nao_vira_carta():
    print("\n[5] Sem sessão observada não há de quem seja a regra")
    db = BancoDeMentira([])           # o id é válido e não está no banco
    r = AS.aplicar_arquivos(db, [_arquivo([_destilado(fatos=[GUINCHO])])], gravar=True)
    checar(r["cartas"] == 0 and not db.cartas,
           "nenhuma carta é gravada", str(r["cartas"]))
    checar(r["contas"].get("sessao inexistente em observed_sessions") == 1,
           "e o motivo é dito", str(r["contas"]))

    # CONTROLE: a MESMA linha, com a sessão presente, vira carta. Sem isto o
    # teste acima passaria se o script não gravasse nada nunca.
    db2 = BancoDeMentira([_sessao()])
    r2 = AS.aplicar_arquivos(db2, [_arquivo([_destilado(fatos=[GUINCHO])])], gravar=True)
    checar(r2["cartas"] == 1, "CONTROLE: com a sessão no banco, a carta sai",
           str(r2["cartas"]))


# ── 4. assunto e ramo ─────────────────────────────────────────────────────────

def teste_o_assunto_sai_da_funcao_do_sistema():
    print("\n[6] Uma régua só de assunto — `curadoria_cartas.assunto_da_carta`")
    cartas = A._cartas_de(_destilado(fatos=[GUINCHO, BOLETO, CONDUTA]), SID,
                          marca=AS.MARCA, dono=AS._dono_da_sessao_observada)
    vistos = [c["category"] for c in cartas]
    for carta in cartas:
        checar(carta["category"] == C.assunto_da_carta(carta["card_text"]),
               f"{carta['category']:12} é o que a função do sistema devolve")
    # CONTROLE: os três precisam ser DIFERENTES. Um classificador que devolve
    # sempre o mesmo valor passaria na comparação acima sem classificar nada.
    checar(len(set(vistos)) == 3,
           "CONTROLE: os três caem em gavetas diferentes", str(vistos))
    checar(set(vistos) <= set(C.ASSUNTOS_VALIDOS),
           "e todos dentro dos cinco valores do acervo", str(vistos))


def teste_o_ramo_do_banco_vence_e_hoje_ele_esta_vazio():
    print("\n[7] O ramo observado venceria; 📊 hoje ele é NULL em 551 de 551")
    db = BancoDeMentira([_sessao(ramo=None)])
    AS.aplicar_arquivos(db, [_arquivo([_destilado(ramo="auto", fatos=[GUINCHO])])],
                        gravar=True)
    checar(list(db.cartas.values())[0]["ramo"] == "auto",
           "com a coluna vazia, o ramo vem do destilado")

    # CONTROLE: com a coluna preenchida, o BANCO vence — é ele que foi
    # observado. Sem esta linha, a ordem escrita no script não seria testada e
    # ninguém saberia que ela existe no dia em que a coluna for preenchida.
    db2 = BancoDeMentira([_sessao(ramo="residencial")])
    AS.aplicar_arquivos(db2, [_arquivo([_destilado(ramo="auto", fatos=[GUINCHO])])],
                        gravar=True)
    checar(list(db2.cartas.values())[0]["ramo"] == "residencial",
           "CONTROLE: com a coluna preenchida, o banco vence",
           str(list(db2.cartas.values())[0]["ramo"]))

    # CONTROLE 2: faltando os dois, `outro` — nunca vazio.
    db3 = BancoDeMentira([_sessao(ramo=None)])
    AS.aplicar_arquivos(db3, [_arquivo([_destilado(ramo=None, fatos=[GUINCHO])])],
                        gravar=True)
    checar(list(db3.cartas.values())[0]["ramo"] == "outro",
           "CONTROLE 2: sem os dois, `outro`",
           str(list(db3.cartas.values())[0]["ramo"]))


# ── 5. simular, gravar, repetir ───────────────────────────────────────────────

def teste_a_simulacao_nao_escreve_uma_linha():
    print("\n[8] Sem `--aplicar` o banco não é tocado")
    arq = _arquivo([_destilado(fatos=[GUINCHO, BOLETO])])
    db = BancoDeMentira([_sessao()])
    r = AS.aplicar_arquivos(db, [arq], gravar=False)
    checar(db.escritas == [], "nenhuma escrita foi feita", str(db.escritas))
    checar(db.sessoes[SID]["summary"] == {},
           "a sessão continua sem a marca `distilled`", str(db.sessoes[SID]))
    checar(r["cartas"] == 2 and r["sessoes"] == 1,
           "e mesmo assim a contagem prevista sai", str(r))

    # CONTROLE — é ele que dá direito à conclusão. Com `gravar=True` o MESMO
    # duplo registra escrita. Sem esta linha, "não escreveu" seria
    # indistinguível de "o duplo não sabe ver escrita".
    db2 = BancoDeMentira([_sessao()])
    AS.aplicar_arquivos(db2, [arq], gravar=True)
    checar(len(db2.escritas) >= 2,
           "CONTROLE: com gravar=True o mesmo duplo registra as escritas",
           str([e[:2] for e in db2.escritas]))


def teste_rodar_duas_vezes_nao_duplica():
    print("\n[9] A segunda rodada não tem o que fazer")
    arq = _arquivo([_destilado(fatos=[GUINCHO, BOLETO])])
    db = BancoDeMentira([_sessao()])
    primeira = AS.aplicar_arquivos(db, [arq], gravar=True)
    # CONTROLE primeiro: a primeira rodada gravou MESMO. "Não duplicou" é
    # trivialmente verdadeiro quando nada foi gravado na ida.
    checar(primeira["sessoes"] == 1 and len(db.cartas) == 2,
           "CONTROLE: a primeira rodada gravou 1 sessão e 2 cartas", str(primeira))
    checar(bool(db.sessoes[SID]["summary"].get("distilled")),
           "e a sessão ficou marcada")

    segunda = AS.aplicar_arquivos(db, [arq], gravar=True)
    checar(segunda["sessoes"] == 0,
           "a segunda rodada não remarca nenhuma sessão", str(segunda["sessoes"]))
    checar(segunda["contas"].get("ja destilada") == 1,
           "e diz por quê", str(segunda["contas"]))
    checar(len(db.cartas) == 2, "o acervo continua com 2 cartas", str(len(db.cartas)))


def teste_a_carta_e_gravada_antes_da_marca_da_sessao():
    print("\n[10] Queda no meio deixa trabalho refazível, não conhecimento perdido")
    arq = _arquivo([_destilado(fatos=[GUINCHO, BOLETO])])
    db = BancoDeMentira([_sessao()])
    db.explodir_no_update = True
    try:
        AS.aplicar_arquivos(db, [arq], gravar=True)
    except RuntimeError:
        pass
    else:
        checar(False, "a queda simulada precisava explodir", "não explodiu")
    checar(len(db.cartas) == 2,
           "as cartas já estavam gravadas quando a marca falhou", str(len(db.cartas)))
    checar(not db.sessoes[SID]["summary"].get("distilled"),
           "e a sessão NÃO ficou marcada — ela volta para a fila",
           str(db.sessoes[SID]["summary"]))

    # A recuperação: a rodada seguinte termina o serviço e não duplica nada.
    db.explodir_no_update = False
    r = AS.aplicar_arquivos(db, [arq], gravar=True)
    checar(r["sessoes"] == 1 and len(db.cartas) == 2,
           "a rodada seguinte marca a sessão sem duplicar carta", str(r["sessoes"]))

    # CONTROLE: com o banco sadio desde o começo, a marca É escrita. Sem isto,
    # "não ficou marcada" poderia significar que o script nunca marca nada.
    db2 = BancoDeMentira([_sessao()])
    AS.aplicar_arquivos(db2, [_arquivo([_destilado(fatos=[GUINCHO])])], gravar=True)
    checar(bool(db2.sessoes[SID]["summary"].get("distilled")),
           "CONTROLE: com o banco sadio, a marca é escrita",
           str(db2.sessoes[SID]["summary"]))


# ── 6. a porta da credencial ──────────────────────────────────────────────────

def teste_sem_credencial_ele_recusa_em_vez_de_gravar_pela_metade():
    print("\n[11] A porta fecha antes de conectar, não no meio da gravação")
    arq = _arquivo([_destilado(fatos=[GUINCHO])])
    original_cred, original_conn = AS._credenciais, AS._conectar
    conectou = []

    def _sem_credencial():
        raise SystemExit(2)

    AS._credenciais = _sem_credencial
    AS._conectar = lambda u, k: conectou.append(1) or BancoDeMentira([_sessao()])
    try:
        try:
            AS.main([arq])
        except SystemExit as saida:
            checar(saida.code == 2, "sai com código 2", str(saida.code))
        else:
            checar(False, "faltou a recusa", "main() retornou em vez de sair")
        checar(conectou == [],
               "e nem chegou a abrir conexão com o banco", str(conectou))

        # CONTROLE: com credencial, a MESMA chamada passa do portão e trabalha.
        # Sem esta linha, um `main()` quebrado passaria no teste acima.
        AS._credenciais = lambda: ("https://exemplo.supabase.co", "chave")
        db = BancoDeMentira([_sessao()])
        AS._conectar = lambda u, k: db
        codigo = AS.main([arq])
        checar(codigo == 0, "CONTROLE: com credencial, main() volta 0", str(codigo))
        checar(db.escritas == [],
               "CONTROLE 2: e sem `--aplicar` ele continua sem escrever",
               str(db.escritas))
        checar(AS.main([arq, "--aplicar"]) == 0 and db.escritas,
               "CONTROLE 3: com `--aplicar` ele escreve", str(db.escritas[:1]))
    finally:
        AS._credenciais, AS._conectar = original_cred, original_conn


# ── 7. nenhum motor paralelo ──────────────────────────────────────────────────

def teste_as_regras_de_gravacao_sao_importadas_e_nao_recopiadas():
    print("\n[12] Um motor só de gravação (CLAUDE.md §5)")
    fonte = open(os.path.join(DESTILACAO, "aplicar_seguradoras.py"),
                 encoding="utf-8").read()
    for trecho, porque in (
            ("from aplicar import", "as regras de carta vêm do aplicar.py"),
            ("from exportar import _credenciais", "a credencial vem da mesma porta"),
            ("from validar import UUID", "o formato do id vem do validador"),
            ("texto_nomeia_seguradora", "e a pergunta sobre o nome vem da curadoria")):
        checar(trecho in fonte, f"{porque}", trecho)

    # O que NÃO pode estar aqui: as regras que seriam a cópia.
    for proibido in ("hashlib.md5", "def assunto", "re.compile"):
        checar(proibido not in fonte,
               f"não reimplementa {proibido!r}",
               "uma segunda cópia envelhece separada da primeira")

    # CONTROLE: prove que essas regras EXISTEM mesmo no aplicar.py. Ausência só
    # prova reuso quando o original tem o que está ausente aqui; se o
    # `hashlib.md5` sumir de lá, o teste acima passa a celebrar uma regra morta.
    original = open(os.path.join(DESTILACAO, "aplicar.py"), encoding="utf-8").read()
    for exigido in ("hashlib.md5", "assunto_da_carta", "seguradora_do_fato"):
        checar(exigido in original,
               f"CONTROLE: `aplicar.py` continua sendo o dono de {exigido!r}")
    checar(A._cartas_de.__defaults__ is not None
           and A._dono_por_texto in A._cartas_de.__defaults__,
           "CONTROLE 2: o `aplicar.py` continua decidindo pela regra DELE",
           "a injeção não pode ter trocado o padrão do acervo de atendimento")


def main() -> int:
    print("=" * 74)
    print("A CARTA TIRADA DA URA SABE DE QUEM É — E O QUE NÃO É DELA, ELA LARGA")
    print("=" * 74)
    # O script se explica pelo stderr, e são 14 chamadas — o relato dele
    # enterraria o relato do teste. Fica guardado e só é impresso se houver
    # falha, que é quando ele passa a ser evidência em vez de ruído.
    original, relato = sys.stderr, io.StringIO()
    sys.stderr = relato
    for teste in (teste_o_rotulo_observado_nao_precisa_do_nome_no_texto,
                  teste_o_fato_que_e_de_outra_companhia_perde_o_rotulo,
                  teste_a_carta_rebaixada_continua_entrando_como_conhecimento,
                  teste_a_seguradora_vem_do_banco_e_nao_do_arquivo,
                  teste_sessao_que_nao_existe_no_banco_nao_vira_carta,
                  teste_o_assunto_sai_da_funcao_do_sistema,
                  teste_o_ramo_do_banco_vence_e_hoje_ele_esta_vazio,
                  teste_a_simulacao_nao_escreve_uma_linha,
                  teste_rodar_duas_vezes_nao_duplica,
                  teste_a_carta_e_gravada_antes_da_marca_da_sessao,
                  teste_sem_credencial_ele_recusa_em_vez_de_gravar_pela_metade,
                  teste_as_regras_de_gravacao_sao_importadas_e_nao_recopiadas):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")
    sys.stderr = original

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        print("\no que o script relatou enquanto isso:")
        for l in relato.getvalue().split("\n"):
            if l.strip():
                print(f"  | {l}")
        return 1
    print("O RÓTULO OBSERVADO É ACEITO — E O FATO QUE É DE OUTRO NÃO O USA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
