"""O agente entra no portal já sabendo — ou não entra.

Por que este teste existe
-------------------------
📊 39 acionamentos de vidros (06 a 15/07/2026, Supabase `dcajcvlzcjbmyapmklil`):
33 pararam em `needs_human`, 5 falharam, 1 ficou "done" sem protocolo. **Zero
protocolos.** 📊 Das 33 paradas, 7 foram por um dado que já estava disponível.

O erro não era burrice; era **ordem**. O sistema abria o portal e só então
descobria o que não sabia — e a essa altura o segurado já tinha saído do
WhatsApp e o robô estava parado numa tela com um dropdown aberto.

Este teste guarda a inversão: *descobrir o que falta ANTES de abrir*. E guarda,
uma por uma, as quatro decisões que fazem a diferença entre uma checagem útil e
um interrogatório:

1. **a pergunta nasce da PEÇA** — película é de vidro lateral, os 10 cm são de
   para-brisa, e perguntar a errada é ruído;
2. **o que está na apólice não se pergunta** — versão do veículo e CEP saem da
   InfoCap; se não vieram, a lacuna é do provedor, não do segurado;
3. **peça não mapeada não trava** — retrovisor, farol, lanterna, vigia e teto
   não foram medidos, e o honesto é dizer isso, não inventar pergunta;
4. **"não sabe" só existe depois de perguntada** — é a saída legítima de quem
   realmente não sabe, e é proibida como atalho do robô.

O CONTROLE, que é o que dá direito à conclusão
----------------------------------------------
Uma função que devolvesse **sempre** `[]` faria o produto entrar no portal
cego, e passaria em qualquer teste que só verifique "não travou". Uma que
devolvesse **sempre** uma pergunta transformaria o atendimento num
interrogatório, e passaria em qualquer teste que só verifique "perguntou".

Por isso as duas afirmações opostas estão aqui juntas — e as duas
implementações preguiçosas são construídas de propósito, para provar que os
guardas **conseguem** reprovar (CLAUDE.md §9.3).

Rodar: cd backend && python tests/test_o_agente_entra_no_portal_sabendo.py
"""
from __future__ import annotations

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
        print(f"  FALHA {descricao}" + (f" - {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def _carregar(dotted: str, rel: str):
    """Carrega por CAMINHO, sem passar pelos `__init__` pesados.

    `app/services/__init__.py` importa langchain, qdrant e minio; esta suite
    roda sem eles. E `backend/` entra no sys.path porque o catálogo importa
    `identidade_peca` do `portal_worker` — o vocabulário de peça é um só.
    """
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location(dotted, RAIZ / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


for _nome in ("app", "app.agents", "app.agents.tools", "app.services"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []

_carregar("app.services.attendance_ficha", "app/services/attendance_ficha.py")
P = _carregar("app.services.perguntas_do_portal_de_vidros",
              "app/services/perguntas_do_portal_de_vidros.py")
PP = _carregar("app.agents.tools.portal_params", "app/agents/tools/portal_params.py")

# `vidros_lanternas` entra pelo import NORMAL, de proposito: carrega-lo por
# caminho criaria um SEGUNDO objeto de modulo e o teste de identidade abaixo
# compararia duas copias — provando o contrario do que quer provar.
from portal_worker.journeys import vidros_lanternas as VL  # noqa: E402


def campos(perguntas) -> list:
    return [p.campo for p in perguntas]


# Tudo que a conversa e a InfoCap já apuraram, MENOS as específicas da peça.
# É o estado normal de um atendimento pouco antes de acionar.
UNIVERSAIS_OK = {
    "cpf_cnpj": "03074327936",
    "data_dano": "05/07/2026",
    "como_ocorreu": "uma pedra bateu no vidro na rodovia",
    "onde_ocorreu": "rodoviario",
    "veiculo": "NIVUS COMFORTLINE 1.0 200 TSI FLEX AUT",   # InfoCap
    "cep": "88040-600",                                     # InfoCap
}

PARABRISA_COMPLETO = {
    **UNIVERSAIS_OK,
    "peca": "parabrisa",
    "posicao_do_trincado": "No centro",
    "tamanho_do_trincado": "Maior que 10 cm",
}


# ------------------------------------------------------------------ #
# 1. O CONTROLE
# ------------------------------------------------------------------ #

def o_controle_da_direito_a_conclusao() -> None:
    """As duas afirmações opostas, e a prova de que elas conseguem reprovar."""
    checar(P.o_que_falta("parabrisa", PARABRISA_COMPLETO) == [],
           "CONTROLE A: com TUDO sabido, o_que_falta devolve LISTA VAZIA",
           str(campos(P.o_que_falta("parabrisa", PARABRISA_COMPLETO))))

    vazio = P.o_que_falta("", {})
    checar(len(vazio) > 0,
           "CONTROLE B: sem nada sabido, o_que_falta devolve PERGUNTA",
           "uma funcao que nunca pergunta manda o robo entrar no portal cego")

    # A prova de que os dois checks acima nao sao decorativos.
    def sempre_vazio(peca, ja_sei=None):
        return []

    def sempre_pergunta(peca, ja_sei=None):
        return [P._UNIVERSAIS[0]]

    for nome, falsa in (("que devolve sempre []", sempre_vazio),
                        ("que devolve sempre pergunta", sempre_pergunta)):
        reprovou = (falsa("parabrisa", PARABRISA_COMPLETO) != []
                    or len(falsa("", {})) == 0)
        checar(reprovou, f"e uma implementacao {nome} REPROVA em A ou em B",
               "guarda que nao tem como falhar nao guarda nada")


# ------------------------------------------------------------------ #
# 2. A DEPENDENCIA: a pergunta nasce da peca
# ------------------------------------------------------------------ #

def a_pergunta_nasce_da_peca() -> None:
    """📊 Passo 6 (80%): para-brisa pergunta dos 10 cm; porta pergunta do lado."""
    do_parabrisa = campos(P.o_que_falta("parabrisa", UNIVERSAIS_OK))
    da_porta = campos(P.o_que_falta("vidro de porta", UNIVERSAIS_OK))

    checar(P.TAMANHO_DO_TRINCADO in do_parabrisa,
           "parabrisa PERGUNTA se o trincado e maior ou menor que 10 cm",
           f"{do_parabrisa} - e 10 cm decide troca x reparo")
    checar(P.POSICAO_DO_TRINCADO in do_parabrisa,
           "parabrisa PERGUNTA a posicao do trincado", str(do_parabrisa))
    checar(P.PELICULA not in do_parabrisa,
           "e parabrisa NAO pergunta de pelicula",
           f"{do_parabrisa} - pelicula e pergunta de vidro lateral")
    checar(P.LADO_MOTORISTA_OU_CARONA not in do_parabrisa,
           "nem o lado (parabrisa nao tem lado)", str(do_parabrisa))

    checar(P.PELICULA in da_porta,
           "vidro de porta PERGUNTA de pelicula (insulfilm)", str(da_porta))
    checar(P.PORTA_DIANTEIRA_OU_TRASEIRA in da_porta,
           "vidro de porta PERGUNTA se e a porta dianteira ou traseira", str(da_porta))
    checar(P.LADO_MOTORISTA_OU_CARONA in da_porta,
           "vidro de porta PERGUNTA o lado (motorista ou carona)", str(da_porta))
    checar(P.TAMANHO_DO_TRINCADO not in da_porta,
           "e vidro de porta NAO pergunta dos 10 cm",
           f"{da_porta} - o trincado de 10 cm e pergunta de parabrisa")

    checar(not (set(do_parabrisa) & set(da_porta) & {
        P.PELICULA, P.LADO_MOTORISTA_OU_CARONA, P.PORTA_DIANTEIRA_OU_TRASEIRA,
        P.POSICAO_DO_TRINCADO, P.TAMANHO_DO_TRINCADO}),
        "nenhuma especifica de uma peca vaza para a outra",
        f"parabrisa={do_parabrisa} porta={da_porta}")

    # E o texto que o segurado ouve fala de gente, nao de formulario.
    lado = [p for p in P.o_que_falta("vidro de porta", UNIVERSAIS_OK)
            if p.campo == P.LADO_MOTORISTA_OU_CARONA][0]
    checar("motorista" in lado.texto.lower() and "carona" in lado.texto.lower(),
           "a pergunta do lado e feita em portugues de gente",
           f"texto={lado.texto!r} - 'informe a lateralidade' nao e portugues de gente")
    checar("lateralidade" not in lado.texto.lower(),
           "e a palavra 'lateralidade' nao aparece em nenhuma pergunta", lado.texto)


def a_peca_desconhecida_e_a_PRIMEIRA_pergunta() -> None:
    """Sem peça não há específicas — nem como saber quais seriam."""
    faltam = P.o_que_falta("", {**UNIVERSAIS_OK})
    nomes = campos(faltam)
    checar(P.PECA in nomes, "sem peca, a PECA e uma pergunta em aberto", str(nomes))
    checar(not (set(nomes) & {P.PELICULA, P.TAMANHO_DO_TRINCADO,
                              P.LADO_MOTORISTA_OU_CARONA, P.POSICAO_DO_TRINCADO}),
           "e NENHUMA especifica aparece antes de a peca ser conhecida",
           f"{nomes} - perguntar de pelicula sem saber a peca e chutar")

    # 'quebrou o vidro' é o relato mais comum, e não nomeia peça nenhuma.
    vago = P.o_que_falta("", {**UNIVERSAIS_OK, "peca": "quebrou o vidro"})
    checar(P.PECA in campos(vago),
           "'quebrou o vidro' NAO identifica peca - continua sendo pergunta",
           "'vidro' e o nome do balcao, nao da peca")

    # E o agente precisa saber POR QUE ela voltou — senao reenvia o mesmo texto,
    # e isso e o laco.
    texto = P.mensagem_para_o_agente(vago, "quebrou o vidro")
    checar("NAO nomeia uma peca" in texto and "Nao reenvie o mesmo" in texto,
           "e a mensagem explica POR QUE a peca voltou (senao o agente reenvia igual)",
           texto[-400:])
    checar("NAO FORAM MAPEADAS" not in texto,
           "e nao chama isso de 'peca nao mapeada' - e texto que nao nomeia peca nenhuma",
           "confundir os dois faria o agente esperar a tela resolver o que so o segurado sabe")


def a_peca_ambigua_vira_pergunta() -> None:
    """'a luz quebrou' pode ser farol OU lanterna — parar agora custa uma frase."""
    nomes = campos(P.o_que_falta("a luz quebrou", UNIVERSAIS_OK))
    checar(P.peca_ambigua("a luz quebrou"), "'a luz quebrou' e AMBIGUA (farol ou lanterna)")
    checar(P.PECA in nomes, "e peca ambigua volta como pergunta", str(nomes))
    checar(not P.especificas_mapeadas("a luz quebrou"),
           "peca ambigua nao tem especificas mapeadas")


# ------------------------------------------------------------------ #
# 3. O QUE ESTA NA APOLICE NAO SE PERGUNTA
# ------------------------------------------------------------------ #

def a_versao_do_veiculo_nunca_vira_pergunta_ao_segurado() -> None:
    """📊 'A versão do veículo é comfortline?' é pergunta de APÓLICE (mapa §4b)."""
    com_veiculo = P.o_que_falta("parabrisa", UNIVERSAIS_OK)
    checar(P.VERSAO_DO_VEICULO not in campos(com_veiculo),
           "com o veiculo na InfoCap, a VERSAO nem chega a ser perguntada",
           str(campos(com_veiculo)))

    sem_veiculo = P.o_que_falta("parabrisa", {**UNIVERSAIS_OK, "veiculo": ""})
    versao = [p for p in sem_veiculo if p.campo == P.VERSAO_DO_VEICULO]
    checar(len(versao) == 1,
           "sem o veiculo na InfoCap, a lacuna da VERSAO e declarada",
           str(campos(sem_veiculo)))
    checar(versao and versao[0].de_quem == P.DO_PROVEDOR,
           "e ela e do PROVEDOR - nunca do segurado",
           "perguntar 'seu carro e comfortline?' a quem quebrou o vidro e ridiculo")
    checar(P.VERSAO_DO_VEICULO not in campos(P.para_o_segurado(sem_veiculo)),
           "para_o_segurado NAO devolve a versao do veiculo",
           str(campos(P.para_o_segurado(sem_veiculo))))

    texto = P.mensagem_para_o_agente(sem_veiculo, "parabrisa")
    checar("NAO pergunte ao segurado" in texto,
           "e a mensagem ao agente separa a lacuna do provedor das perguntas", texto[:160])

    # CONTROLE do proprio guarda: se a versao NAO existisse no catalogo, os
    # checks acima passariam por vacuidade.
    checar(any(p.campo == P.VERSAO_DO_VEICULO
               for p in P._ESPECIFICAS_POR_IDENTIDADE["parabrisa"]),
           "CONTROLE: a versao do veiculo EXISTE no catalogo do parabrisa",
           "sem ela, os checks acima passariam sem provar nada")


def o_cep_e_lacuna_do_provedor_e_nao_bloqueia() -> None:
    """📊 CEP é 'opcional' no portal e obrigatório para nós — mas nunca do segurado."""
    sem_cep = P.o_que_falta("parabrisa", {**PARABRISA_COMPLETO, "cep": ""})
    cep = [p for p in sem_cep if p.campo == P.CEP_DO_SEGURADO]
    checar(len(cep) == 1, "sem CEP na InfoCap, a lacuna e declarada", str(campos(sem_cep)))
    checar(cep and cep[0].de_quem == P.DO_PROVEDOR, "e o CEP e do PROVEDOR")
    checar(P.para_o_segurado(sem_cep) == [],
           "e NENHUMA pergunta sobra para o segurado - o CEP nao bloqueia",
           str(campos(P.para_o_segurado(sem_cep))))


# ------------------------------------------------------------------ #
# 4. PECA NAO MAPEADA NAO TRAVA, E NAO INVENTA
# ------------------------------------------------------------------ #

def a_peca_nao_mapeada_nao_trava() -> None:
    """📊 Mapa §7: retrovisor, farol, lanterna, vigia e teto não foram medidos."""
    for peca in P.PECAS_SEM_ESPECIFICAS_MAPEADAS:
        faltam = P.o_que_falta(peca, UNIVERSAIS_OK)
        checar(not P.especificas_mapeadas(peca),
               f"'{peca}': as especificas NAO estao mapeadas - e isso e declarado")
        checar(P.para_o_segurado(faltam) == [],
               f"'{peca}': nao trava o acionamento (nenhuma pergunta pendente)",
               str(campos(faltam)))
        checar(P.especificas_da_peca(peca) == (),
               f"'{peca}': nenhuma pergunta INVENTADA para ela")
        texto = P.mensagem_para_o_agente(faltam, peca)
        checar("NAO FORAM MAPEADAS" in texto,
               f"'{peca}': a mensagem diz, em voz alta, que nao foram mapeadas",
               texto[:200])

    # CONTROLE: se a tabela de especificas estivesse VAZIA, todo o bloco acima
    # passaria e o produto teria voltado a entrar no portal sem saber nada.
    checar(P.especificas_mapeadas("parabrisa") and P.especificas_mapeadas("vidro de porta"),
           "CONTROLE: parabrisa e vidro de porta CONTINUAM mapeados",
           "uma tabela de especificas vazia passaria em todo o bloco acima")


# ------------------------------------------------------------------ #
# 5. A DESCRICAO E COMPOSTA, NUNCA PERGUNTADA
# ------------------------------------------------------------------ #

def a_descricao_e_composta_nunca_perguntada() -> None:
    """📊 Mínimo de 30 caracteres no passo 4. Isso é contador, não informação."""
    cenarios = [
        ("", {}),
        ("parabrisa", {}),
        ("vidro de porta", UNIVERSAIS_OK),
        ("retrovisor", UNIVERSAIS_OK),
        ("parabrisa", {**UNIVERSAIS_OK, "descricao": "quebrou"}),
    ]
    for peca, ja_sei in cenarios:
        nomes = campos(P.o_que_falta(peca, ja_sei))
        checar(P.DESCRICAO not in nomes,
               f"a descricao NUNCA e pergunta (peca={peca!r})",
               f"{nomes} - pedir 'escreva mais 20 caracteres' e a pergunta que o produto existe para nao fazer")

    curta = P.compor_descricao({"peca": "x", "como_ocorreu": "y"})
    checar(len(curta) >= P.MINIMO_DA_DESCRICAO,
           f"com peca e relato de 1 caractere, a composicao ja passa dos 30 ({len(curta)})",
           repr(curta))

    real = P.compor_descricao({**UNIVERSAIS_OK, "peca": "vidro da porta",
                               "descricao": "quebrou o vidro"})
    checar(len(real) >= P.MINIMO_DA_DESCRICAO, f"relato curto real vira {len(real)} chars", repr(real))
    checar("quebrou o vidro" in real,
           "e as PALAVRAS DO SEGURADO continuam la - nada e substituido", repr(real))
    checar("vidro da porta" in real and "05/07/2026" in real,
           "a composicao usa so fatos ja sabidos (peca e data)", repr(real))

    longo = "o carro estava estacionado na rua e alguem quebrou o vidro da porta do motorista"
    checar(P.compor_descricao({"peca": "vidro de porta", "descricao": longo}) == longo,
           "relato que ja passa de 30 vai INTEIRO, sem enfeite", repr(longo))


# ------------------------------------------------------------------ #
# 6. "NAO SABE" SO DEPOIS DE PERGUNTADA
# ------------------------------------------------------------------ #

def o_nao_sabe_encerra_a_pergunta_mas_nao_a_substitui() -> None:
    """📊 Mapa §8.2: responder 'Não sabe' para destravar é perda de serviço."""
    com_nao_sabe = {**PARABRISA_COMPLETO, "tamanho_do_trincado": P.NAO_SABE}
    checar(P.TAMANHO_DO_TRINCADO not in campos(P.o_que_falta("parabrisa", com_nao_sabe)),
           "'nao sabe' ENCERRA a pergunta dos 10 cm (o portal oferece essa saida)",
           str(campos(P.o_que_falta("parabrisa", com_nao_sabe))))
    checar(P.TAMANHO_DO_TRINCADO not in campos(
               P.o_que_falta("parabrisa", {**PARABRISA_COMPLETO, "tamanho_do_trincado": "não sei"})),
           "e 'nao sei', como o segurado fala, vale o mesmo")

    # E o contrario: pergunta que o portal NAO deixa pular nao aceita a saida.
    so_peca = {k: v for k, v in UNIVERSAIS_OK.items()}
    checar(P.PECA in campos(P.o_que_falta("", {**so_peca, "peca": P.NAO_SABE})),
           "mas 'nao sabe' NAO encerra a pergunta da PECA - ela nao aceita a saida",
           "'nao sei qual vidro quebrou' e caso para gente, nao resposta de portal")
    checar(P.DATA_DO_DANO in campos(P.o_que_falta("parabrisa", {**PARABRISA_COMPLETO,
                                                                "data_dano": "nao sabe"})),
           "nem a data do dano - sem ela a apolice nem e localizada")

    # Ausente nunca conta como resposta, e o preenchimento de fachada tampouco.
    checar(not P.respondida("", aceita_nao_sabe=True), "campo VAZIO nunca conta como resposta")
    checar(not P.respondida("nao informado", aceita_nao_sabe=True),
           "'nao informado' tambem nao - e o preenchimento de fachada do modelo")
    checar(P.respondida("Maior que 10 cm"), "e um valor de verdade conta")

    # O CONTROLE do proprio 'nao sabe': se `respondida` ignorasse a flag, os
    # dois lados dariam o mesmo resultado.
    checar(P.respondida(P.NAO_SABE, aceita_nao_sabe=True)
           != P.respondida(P.NAO_SABE, aceita_nao_sabe=False),
           "CONTROLE: 'nao sabe' CONSEGUE dar respostas diferentes conforme a pergunta",
           "se desse a mesma, a distincao inteira seria decorativa")

    # E "nao sabe" nunca e OFERECIDO como opcao.
    todas = list(P._UNIVERSAIS) + [p for g in P._ESPECIFICAS_POR_IDENTIDADE.values() for p in g]
    oferecem = [p.campo for p in todas if any(P.e_nao_sabe(o) for o in p.opcoes)]
    checar(not oferecem,
           "e 'nao sabe' NUNCA aparece na lista de opcoes que se oferece",
           f"{oferecem} - ela se aceita, nao se oferece")


# ------------------------------------------------------------------ #
# 7. O VOCABULARIO DE PECA E UM SO
# ------------------------------------------------------------------ #

def o_vocabulario_de_peca_e_um_so() -> None:
    """CLAUDE.md §5: consolidar antes de duplicar. Duas tabelas de peça divergem."""
    checar(P.identidade_peca is VL.identidade_peca,
           "o catalogo usa `identidade_peca` do portal_worker - nao uma copia",
           "duas tabelas de peca decidem diferente no dia em que uma for editada")
    checar(not any(k in P.__dict__ for k in ("_PECAS", "_EXPRESSOES", "_AMBIGUOS")),
           "e o modulo NAO redeclara o vocabulario de peca",
           str([k for k in ("_PECAS", "_EXPRESSOES", "_AMBIGUOS") if k in P.__dict__]))


# ------------------------------------------------------------------ #
# 8. O CAMINHO REAL: build_portal_params
# ------------------------------------------------------------------ #

PROFILE = {"nome": "Auto Fleet Corretora", "email": "operacional@autofleet.com.br",
           "telefone": "4833646664", "cpf_cnpj": "00000000000191"}

INFOCAP = {
    "ok": True, "status": "found",
    "policy": {"numapo": "312520261149211", "seguradora": "LIBERTY SEGUROS S/A",
               "seguradora_abrev": "LIBE", "active": True},
    "vehicle": {"placa": "QJQ0A91", "chassi": "98867513WJKH74022",
                "veiculo": "NIVUS COMFORTLINE 1.0 200 TSI FLEX AUT", "ano": "2022"},
    "client": {"nome": "RAFAEL LACAU DA SILVEIRA", "cpf_cnpj": "03074327936",
               "logradouro": "RUA CAPITAO ROMUALDO DE BARROS", "numero": "705",
               "bairro": "SACO DOS LIMOES", "cidade": "FLORIANOPOLIS", "estado": "SC",
               "cep": "88040-600"},
}

FLAT_COMPLETO = {"cpf_cnpj": "03074327936", "data_dano": "05/07/2026",
                 "peca": "vidro de porta", "como_ocorreu": "encontrou o veiculo danificado",
                 "onde_ocorreu": "urbano",
                 "descricao": "o carro estava estacionado e o vidro da porta foi quebrado"}


def o_portal_nao_abre_com_o_relato_vago() -> None:
    """'quebrou o vidro' não é peça — e é assim que o segurado fala."""
    p, e = PP.build_portal_params(
        {"cpf_cnpj": "03074327936", "data_dano": "05/07/2026", "peca": "quebrou o vidro",
         "como_ocorreu": "nao sei", "onde_ocorreu": ""}, PROFILE, INFOCAP)
    checar(p is None and bool(e), "relato vago NAO abre o portal", f"params={p is not None}")
    checar(e and "Qual vidro foi" in e,
           "e o agente recebe a PERGUNTA pronta, em portugues", (e or "")[:200])
    checar(e and "uma pergunta por mensagem" in e,
           "com a instrucao de perguntar uma de cada vez", (e or "")[:200])
    checar(e and "Nunca pergunte ao segurado o que esta na apolice" in e,
           "e a proibicao de perguntar o que ja esta na apolice", (e or "")[-200:])


def o_caso_completo_continua_abrindo() -> None:
    """CONTROLE do caminho real: o conserto não pode travar quem já tinha tudo."""
    p, e = PP.build_portal_params(FLAT_COMPLETO, PROFILE, INFOCAP)
    checar(e is None and p is not None, "CONTROLE: caso completo abre normalmente", str(e)[:160])
    checar(p and p["dano"]["peca"] == "vidro de porta", "e o dano continua chegando ao portal")
    checar(p and p["confirm"] is False, "e confirm continua False (nunca envia sozinha)")


def as_especificas_nao_travam_o_acionamento() -> None:
    """O laço infinito que NÃO pode nascer aqui.

    📊 `PortalActionInput` ainda não tem campo para as respostas do 80%. Se elas
    travassem, o agente perguntaria, o segurado responderia, o schema descartaria
    a resposta e a mesma pergunta voltaria para sempre — o defeito do
    `subservico_invalido` (test_o_acionamento_nao_pede_o_impossivel.py).
    """
    p, e = PP.build_portal_params(FLAT_COMPLETO, PROFILE, INFOCAP)
    faltam = P.o_que_falta("vidro de porta", {"cpf_cnpj": "1", "data_dano": "1",
                                              "como_ocorreu": "1", "onde_ocorreu": "1",
                                              "veiculo": "1", "cep": "1"})
    checar(len(P.para_o_segurado(faltam)) == 3,
           "as 3 especificas do vidro de porta CONTINUAM sendo cobradas por o_que_falta",
           str(campos(faltam)))
    checar(e is None and p is not None,
           "mas elas NAO travam build_portal_params - nao ha como transporta-las hoje",
           "travar sem transporte cria o laco infinito")
    checar(all(c in PP.TRANSPORTAVEIS for c in
               (P.CPF_DO_TITULAR, P.DATA_DO_DANO, P.PECA, P.COMO_OCORREU, P.ONDE_OCORREU)),
           "e o que TRAVA e exatamente o que a tool consegue receber de volta",
           str(PP.TRANSPORTAVEIS))


def a_primeira_pergunta_e_sempre_transportavel() -> None:
    """A pergunta em destaque tem de ser uma cuja resposta chega de volta."""
    casos = [
        {"cpf_cnpj": "", "data_dano": "", "peca": "", "como_ocorreu": "", "onde_ocorreu": ""},
        {"cpf_cnpj": "1", "data_dano": "05/07/2026", "peca": "parabrisa",
         "como_ocorreu": "", "onde_ocorreu": ""},
        {"cpf_cnpj": "1", "data_dano": "05/07/2026", "peca": "vidro de porta",
         "como_ocorreu": "pedra", "onde_ocorreu": ""},
    ]
    for flat in casos:
        ja_sei = {**flat, "veiculo": INFOCAP["vehicle"]["veiculo"],
                  "cep": INFOCAP["client"]["cep"]}
        perguntas = P.para_o_segurado(P.o_que_falta(str(flat.get("peca") or ""), ja_sei))
        checar(bool(perguntas) and perguntas[0].campo in PP.TRANSPORTAVEIS,
               f"a 1a pergunta ao segurado e transportavel (peca={flat['peca']!r})",
               str([p.campo for p in perguntas]))


def as_respostas_do_80_por_cento_chegam_ao_portal() -> None:
    """O transporte de `especificos` existe daqui para baixo — e agora é escrito."""
    especificos = {"pelicula": "NÃO", "porta_dianteira_ou_traseira": "DIANTEIRA",
                   "lado_motorista_ou_carona": "Lado do motorista"}
    p, e = PP.build_portal_params({**FLAT_COMPLETO, "especificos": especificos},
                                  PROFILE, INFOCAP)
    checar(e is None and p is not None, "params montados com as especificas", str(e)[:120])
    checar(p and p.get("especificos") == especificos,
           "e elas chegam em params['especificos'] - a chave que a journey ja le",
           str((p or {}).get("especificos")))

    p2, _ = PP.build_portal_params(FLAT_COMPLETO, PROFILE, INFOCAP)
    checar(p2 and p2.get("especificos") == {},
           "CONTROLE: sem coleta, a chave nasce VAZIA (nao inventada)",
           str((p2 or {}).get("especificos")))


def a_descricao_curta_e_consertada_antes_do_portal() -> None:
    """📊 Mín. 30 caracteres no passo 4 — o portal trava, e nós não perguntamos."""
    p, e = PP.build_portal_params({**FLAT_COMPLETO, "descricao": "quebrou"}, PROFILE, INFOCAP)
    checar(e is None and p is not None, "descricao curta NAO impede o acionamento", str(e)[:120])
    texto = (p or {}).get("dano", {}).get("descricao", "")
    checar(len(texto) >= P.MINIMO_DA_DESCRICAO,
           f"e ela chega ao portal com {len(texto)} caracteres (min 30)", repr(texto))
    checar("quebrou" in texto, "com o relato do segurado dentro", repr(texto))

    p3, _ = PP.build_portal_params(FLAT_COMPLETO, PROFILE, INFOCAP)
    checar(p3 and p3["dano"]["descricao"] == FLAT_COMPLETO["descricao"],
           "CONTROLE: descricao ja boa passa INTACTA", str((p3 or {})["dano"]["descricao"]))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print(__doc__)

    print("== 1. o controle que da direito a conclusao ==")
    o_controle_da_direito_a_conclusao()
    print("== 2. a pergunta nasce da peca ==")
    a_pergunta_nasce_da_peca()
    a_peca_desconhecida_e_a_PRIMEIRA_pergunta()
    a_peca_ambigua_vira_pergunta()
    print("== 3. o que esta na apolice nao se pergunta ==")
    a_versao_do_veiculo_nunca_vira_pergunta_ao_segurado()
    o_cep_e_lacuna_do_provedor_e_nao_bloqueia()
    print("== 4. peca nao mapeada nao trava, e nao inventa ==")
    a_peca_nao_mapeada_nao_trava()
    print("== 5. a descricao e composta, nunca perguntada ==")
    a_descricao_e_composta_nunca_perguntada()
    print("== 6. 'nao sabe' so depois de perguntada ==")
    o_nao_sabe_encerra_a_pergunta_mas_nao_a_substitui()
    print("== 7. o vocabulario de peca e um so ==")
    o_vocabulario_de_peca_e_um_so()
    print("== 8. o caminho real (build_portal_params) ==")
    o_portal_nao_abre_com_o_relato_vago()
    o_caso_completo_continua_abrindo()
    as_especificas_nao_travam_o_acionamento()
    a_primeira_pergunta_e_sempre_transportavel()
    as_respostas_do_80_por_cento_chegam_ao_portal()
    a_descricao_curta_e_consertada_antes_do_portal()

    print()
    if _falhas:
        print(f"VERMELHO - {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O AGENTE ENTRA NO PORTAL JA SABENDO - OU NAO ENTRA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
