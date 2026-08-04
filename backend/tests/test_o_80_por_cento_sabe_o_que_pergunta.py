"""O passo 6 não pergunta PEÇA — pergunta LADO, POSIÇÃO, TAMANHO e VERSÃO.

E o portal não deixa corrigir. 📊 `docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`
§3, texto literal presente em TODAS as telas:

    "O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para TROCA/REPARO
     por atendimento. Se o item escolhido possuir lateralidade (por exemplo, lado
     esquerdo e lado direito), será necessário abrir uma nova solicitação."

Marcar o lado errado não é um campo errado num formulário: é o vidraceiro
chegando com a peça do outro lado, e o conserto exigindo um SEGUNDO acionamento.

M1 · O que estava errado, medido antes de mexer
------------------------------------------------
📊 04/08/2026 — as duas funções de então, rodadas contra as opções reais das
telas capturadas em 06/07/2026. Este arquivo mede de novo, na seção [M1], para
que o número não vire folclore.

    explicar_match("porta dianteira", ["DIANTEIRA","TRASEIRA","Não sabe"]) -> None

Não é azar de placar: é VETO. `identidade_peca('porta dianteira')` = {lateral},
`identidade_peca('DIANTEIRA')` = {parabrisa} — porque o mapa `_POSICAO` manda
`dianteira -> parabrisa`. O veto eliminou as DUAS opções reais e sobrou só
"Não sabe". **O mapa certo na tela da peça é o mapa errado na tela do atributo:**
lá `dianteira` é o para-brisa; aqui é a porta da frente — e a peça já foi
escolhida duas telas antes.

E o placar por tokens não tinha como resolver o resto: `lado do passageiro` e
`Lado do carona` só compartilham `lado`, que aparece em TODA opção e por isso
pesa 0.0. Nenhum ajuste de peso descobre que passageiro = carona. Isso não é
semelhança de texto — é **tabela de fato**.

M2 · A metade que ERRAVA, e não parava
---------------------------------------
Abstenção não era o pior. 📊 A decisão real do `_apply_mdselect` é composta:

    critico = _is_critical_select(target)
    escolha = explicar_match(...)["escolha"]
    if escolha is None and not critico: escolha = reais[0][0]   # 1a opção

`_is_critical_select` era `("item","peca","danific","ocorreu","causa","dano")`.
As perguntas do para-brisa não têm nenhuma dessas palavras — e a da loja também
não. Medido em 20 decisões reconstruídas das telas reais, **6 saíam ERRADAS**:

    "menor que 10 cm"        -> Maior (troca do vidro)      trocar vidro reparável
    "uma trinca pequena"     -> Maior (troca do vidro)
    "do tamanho de uma moeda"-> Maior (troca do vidro)
    "no meio do vidro"       -> Em frente ao motorista
    "na quina do vidro"      -> Em frente ao motorista
    "a mais perto do segurado" -> a 1a loja da lista         sorteio de oficina

A pior é a primeira: o segurado responde literalmente **"menor"** e o portal
recebe **"Maior"**. O 10 cm não é burocracia — é o que decide troca × reparo.

M3 · "Não sabe" está em toda pergunta, e é uma armadilha
---------------------------------------------------------
📊 Mapa §4(a): "Não sabe" destrava a tela e o portal deixa de saber qual vidro
pedir. Responder isso por preguiça do robô é perda de serviço disfarçada de
progresso. Só é honesto quando o SEGURADO não sabe.

Havia a inversão simétrica, achada ao medir: numa pergunta SIM/NÃO, "não sei"
contém o token `não` — e o robô respondia **NÃO** ("o vidro não tem película"),
afirmando um fato que ninguém deu. Inventar fato é pior que parar.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# O console do Windows nasce em cp1252 e engasga com 📊 e com os acentos do
# português — sem isto o teste morre de UnicodeEncodeError antes de checar nada.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# As opções REAIS das telas do 80%, copiadas do mapa medido
# (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md §4, captura de 06/07/2026).
# ---------------------------------------------------------------------------
LADO = ["Lado do carona", "Lado do motorista", "Não sabe"]
PORTA = ["DIANTEIRA", "TRASEIRA", "Não sabe"]
PELICULA = ["SIM", "NÃO", "Não sabe"]
POSICAO = ["Em frente ao motorista", "Em frente ao carona", "Nas bordas",
           "No centro", "Não sabe"]
TAMANHO = ["Maior (troca do vidro)", "Menor (possibilidade de reparo)", "Não sabe"]
VERSAO = ["Sim", "Não", "Não sabe"]

Q_LADO = "Qual o lado do item danificado?"
Q_PORTA = "O vidro danificado é da porta dianteira ou traseira?"
Q_PELICULA = "O vidro danificado tem película de controle solar (insulfilm)?"
Q_POSICAO = "Poderia informar a posição do trincado?"
Q_TAMANHO = "O trincado está maior ou menor que 10 cm?"
Q_VERSAO = "A versão do veículo é comfortline?"
Q_LOJA = "Escolha a loja onde deseja realizar o serviço"

# Listas de PEÇA e de FORMATO — os controles. Nenhuma delas pode ser capturada
# pelo vocabulário do 80%, ou o conserto de uma tela quebra a outra.
PECAS = ["Selecione uma opção", "VIDRO PARABRISA", "VIDRO DE PORTA",
         "VIDRO VIGIA (TRASEIRO)"]
LUZES = ["FAROL DIANTEIRO", "LANTERNA TRASEIRA"]
PORTA_PECA = ["VIDRO DE PORTA DIANTEIRA", "VIDRO DE PORTA TRASEIRA"]
PORTA_LADO = ["VIDRO PORTA DIREITA", "VIDRO PORTA ESQUERDA"]
TELEFONE = ["Selecione uma opção", "COMERCIAL (Apenas ligações)", "CELULAR CORRETOR"]
RELACAO = ["Selecione uma opção", "O próprio", "Cônjuge", "Filho", "Corretor", "Outros"]
# 📊 Passo 7, exemplo real do mapa §4: o endereço inteiro vem dentro da opção —
# e um dos bairros se chama Centro.
LOJAS = ["AUTOGLASS MG19 - Rua Camilo Veríssimo da Silva 555, Rocado, São José/SC",
         "AUTOGLASS SC02 - Av. Ivo Silveira 2000, Centro, Florianópolis/SC",
         "Agendar a domicílio"]


def teste_m1_a_medicao_que_motivou_o_conserto():
    print("\n[M1] O que o casamento de PEÇAS fazia nas perguntas do 80%")
    from portal_worker.journeys.vidros_lanternas import explicar_match, identidade_peca

    d = explicar_match("porta dianteira", PORTA)
    checar(d["escolha"] is None,
           "'porta dianteira' contra ['DIANTEIRA','TRASEIRA'] não escolhia nada",
           f"📊 medido agora: {d['escolha']} ({d['motivo']})")
    checar(identidade_peca("porta dianteira") == {"lateral"}
           and identidade_peca("DIANTEIRA") == {"parabrisa"},
           "e a causa é nomeável: o mapa manda 'dianteira' para PARA-BRISA",
           "o veto de peça eliminava as duas opções reais — sobrava só 'Não sabe'")
    checar(explicar_match("lado do passageiro", LADO)["escolha"] is None,
           "'lado do passageiro' também não casava com 'Lado do carona'",
           "token em comum: só 'lado', que aparece em toda opção e pesa 0.0")

    # CONTROLE: o casamento de peças não estava quebrado — estava fora do seu
    # domínio. Na tela DELE ele acerta, antes e depois deste teste existir.
    checar(explicar_match("vidro da porta", PECAS)["escolha"] == "VIDRO DE PORTA",
           "CONTROLE: na tela da PEÇA ele continua acertando",
           "o problema nunca foi a função; foi usá-la numa pergunta que não é dela")


def teste_m2_a_metade_que_errava():
    print("\n[M2] As 6 decisões que saíam ERRADAS — e o que sai agora")
    from portal_worker.adaptive import _is_critical_select
    from portal_worker.journeys.vidros_lanternas import explicar_especifico, explicar_match

    def decide(pergunta, resposta, opcoes):
        """As MESMAS linhas de decisão do _apply_mdselect, sem navegador."""
        reais = [o for o in opcoes if "selecione" not in o.lower()]
        critico = _is_critical_select(pergunta)
        esp = explicar_especifico(resposta, reais, pergunta)
        escolha = (esp["escolha"] if esp["dominio"] != "nenhum"
                   else explicar_match(resposta, reais)["escolha"])
        if escolha is None and not critico and esp["dominio"] == "nenhum":
            escolha = reais[0]
        return escolha

    # (pergunta, resposta, opções, esperado, o que saía antes 📊)
    for pergunta, resposta, opcoes, esperado, antes in (
        (Q_TAMANHO, "menor que 10 cm", TAMANHO, "Menor (possibilidade de reparo)",
         "Maior (troca do vidro)"),
        (Q_TAMANHO, "uma trinca pequena", TAMANHO, "Menor (possibilidade de reparo)",
         "Maior (troca do vidro)"),
        (Q_TAMANHO, "do tamanho de uma moeda", TAMANHO, "Menor (possibilidade de reparo)",
         "Maior (troca do vidro)"),
        (Q_POSICAO, "no meio do vidro", POSICAO, "No centro", "Em frente ao motorista"),
        (Q_POSICAO, "na quina do vidro", POSICAO, "Nas bordas", "Em frente ao motorista"),
        (Q_LOJA, "a mais perto do segurado", LOJAS, None, LOJAS[0]),
    ):
        got = decide(pergunta, resposta, opcoes)
        checar(got == esperado, f"'{resposta}' -> {esperado}", f"📊 antes: {antes} · agora: {got}")

    checar(decide(Q_TAMANHO, "uns 20 centímetros", TAMANHO) == "Maior (troca do vidro)",
           "CONTROLE: as que já acertavam continuam acertando",
           "📊 'uns 20 centímetros' acertava por sorte (era a 1a opção); agora acerta por medida")


def teste_o_lado_e_tabela_de_fato_nao_e_semelhanca():
    print("\n[7.4a] 🔴 No Brasil o motorista senta à ESQUERDA")
    from portal_worker.journeys.vidros_lanternas import responder_especifico as R

    # Prova nos DOIS sentidos: cada frase tem de cair no lado certo E jamais no
    # outro. Um teste que só afirmasse o esperado não pegaria a inversão.
    #
    # 📊 04/08/2026 — checado por MUTAÇÃO, e o resultado corrige a intuição:
    #   trocar os NOMES das duas classes ('motorista' <-> 'carona') mantém tudo
    #   VERDE, e está certo que mantenha — resposta e opções são classificadas
    #   pela MESMA tabela, então o casamento é invariante ao nome do grupo;
    #   mas mover 'direito/esquerdo' de grupo (= 'o motorista senta à direita')
    #   ou pôr 'passageiro' no grupo do motorista deixa isto VERMELHO na hora.
    # Ou seja: quem guarda o fato são os SINÔNIMOS abaixo, não o rótulo da
    # classe. Enxugar esta lista para "só o essencial" desarma o guarda.
    for frase, certo, errado in (
        ("lado do passageiro", "Lado do carona", "Lado do motorista"),
        ("do lado do passageiro", "Lado do carona", "Lado do motorista"),
        ("lado direito", "Lado do carona", "Lado do motorista"),
        ("o vidro da direita", "Lado do carona", "Lado do motorista"),
        ("lado do carona", "Lado do carona", "Lado do motorista"),
        ("lado do motorista", "Lado do motorista", "Lado do carona"),
        ("lado esquerdo", "Lado do motorista", "Lado do carona"),
        ("lado de quem dirige", "Lado do motorista", "Lado do carona"),
        ("do lado do volante", "Lado do motorista", "Lado do carona"),
        ("lado do condutor", "Lado do motorista", "Lado do carona"),
    ):
        got = R(frase, LADO, Q_LADO)
        checar(got == certo and got != errado, f"'{frase}' -> {certo}",
               f"deu {got} — trocar o lado manda o vidraceiro com a peça errada")

    checar(R("do meu lado", LADO, Q_LADO) is None,
           "'do meu lado' PARA: quem fala pode ser o segurado, o corretor ou o carona",
           "esta é a frase que nunca pode ganhar um palpite")
    checar(R("quebraram o vidro do motorista e o do carona", LADO, Q_LADO) is None,
           "os DOIS lados -> para (📊 mapa §3: são DOIS acionamentos, não um)",
           "abrir um só e avisar que resolveu deixa o outro lado quebrado")


def teste_dianteira_traseira_sem_o_mapa_de_pecas():
    print("\n[7.4b] Na tela do atributo, DIANTEIRA é a porta da frente")
    from portal_worker.journeys.vidros_lanternas import responder_especifico as R

    for frase, certo in (("porta dianteira", "DIANTEIRA"), ("dianteira", "DIANTEIRA"),
                         ("porta da frente", "DIANTEIRA"), ("a da frente", "DIANTEIRA"),
                         ("porta traseira", "TRASEIRA"), ("traseira", "TRASEIRA"),
                         ("porta de trás", "TRASEIRA"), ("a de trás", "TRASEIRA"),
                         ("o vidro de trás", "TRASEIRA")):
        checar(R(frase, PORTA, Q_PORTA) == certo, f"'{frase}' -> {certo}",
               f"deu {R(frase, PORTA, Q_PORTA)}")
    checar(R("o vidro da porta", PORTA, Q_PORTA) is None,
           "sem dizer qual porta -> para (a pergunta é exatamente essa)")


def teste_pelicula_e_a_negacao_que_inverte():
    print("\n[7.4c] 'não tem película' cita película — e a resposta é NÃO")
    from portal_worker.journeys.vidros_lanternas import responder_especifico as R

    for frase, certo in (("sim", "SIM"), ("tem insulfilm", "SIM"), ("vidro fumê", "SIM"),
                         ("escurecido", "SIM"), ("tem película", "SIM"),
                         ("não", "NÃO"), ("não tem película", "NÃO"),
                         ("sem insulfilm", "NÃO"), ("o vidro é original de fábrica", "NÃO")):
        checar(R(frase, PELICULA, Q_PELICULA) == certo, f"'{frase}' -> {certo}",
               f"deu {R(frase, PELICULA, Q_PELICULA)}")

    # CONTROLE da inversão: as duas frases citam 'película' e têm de sair
    # DIFERENTES. Se o guarda não conseguisse distingui-las, ele não guardaria nada.
    checar(R("tem película", PELICULA, Q_PELICULA) != R("não tem película", PELICULA, Q_PELICULA),
           "CONTROLE: 'tem película' e 'não tem película' NÃO podem dar o mesmo",
           "é a negação que separa as duas; um placar por tokens juntaria as duas")


def teste_dez_centimetros_decidem_troca_ou_reparo():
    print("\n[7.4d] Os 10 cm não são burocracia: são troca × reparo")
    from portal_worker.journeys.vidros_lanternas import responder_especifico as R

    GRANDE, PEQUENO = "Maior (troca do vidro)", "Menor (possibilidade de reparo)"
    for frase, certo in (("maior que 10 cm", GRANDE), ("uns 20 centímetros", GRANDE),
                         ("mais de 10 cm", GRANDE), ("1 metro", GRANDE),
                         ("uma trinca grande atravessando o vidro", GRANDE),
                         ("rachou o para-brisa de ponta a ponta", GRANDE),
                         ("menor que 10 cm", PEQUENO), ("5 cm", PEQUENO),
                         ("3 mm", PEQUENO), ("do tamanho de uma moeda", PEQUENO),
                         ("uma trinca pequena", PEQUENO), ("um pontinho só", PEQUENO)):
        checar(R(frase, TAMANHO, Q_TAMANHO) == certo, f"'{frase}' -> {certo.split(' (')[0]}",
               f"deu {R(frase, TAMANHO, Q_TAMANHO)}")

    checar(R("exatamente 10 cm", TAMANHO, Q_TAMANHO) is None,
           "10 cm CRAVADOS -> para: a pergunta é 'maior OU menor', não tem 'igual'")
    checar(R("menor que 20 cm", TAMANHO, Q_TAMANHO) is None,
           "'menor que 20 cm' -> para: cabe dos dois lados dos 10",
           "a medida contradiz a palavra; não há resposta honesta")


def teste_posicao_do_trincado():
    print("\n[7.4e] A posição do trincado tem quatro respostas, não duas")
    from portal_worker.journeys.vidros_lanternas import responder_especifico as R

    for frase, certo in (("em frente ao motorista", "Em frente ao motorista"),
                         ("na frente do volante", "Em frente ao motorista"),
                         ("em frente ao carona", "Em frente ao carona"),
                         ("na frente do passageiro", "Em frente ao carona"),
                         ("nas bordas", "Nas bordas"), ("no canto", "Nas bordas"),
                         ("na quina", "Nas bordas"), ("perto da moldura", "Nas bordas"),
                         ("no centro", "No centro"), ("no meio do vidro", "No centro"),
                         ("bem no meio", "No centro")):
        checar(R(frase, POSICAO, Q_POSICAO) == certo, f"'{frase}' -> {certo}",
               f"deu {R(frase, POSICAO, Q_POSICAO)}")
    checar(R("na borda do lado do motorista", POSICAO, Q_POSICAO) is None,
           "'na borda do lado do motorista' -> para: é ambíguo DE VERDADE",
           "a lista oferece as duas como respostas mutuamente exclusivas")


def teste_a_versao_esta_na_apolice_nao_no_segurado():
    print("\n[7.4f] 'comfortline' é pergunta de apólice — e ausência não é prova")
    from portal_worker.journeys.vidros_lanternas import responder_especifico as R

    checar(R("sim", VERSAO, Q_VERSAO) == "Sim", "'sim' -> Sim")
    checar(R("não", VERSAO, Q_VERSAO) == "Não", "'não' -> Não")
    checar(R("NIVUS COMFORTLINE 1.0 200 TSI FLEX AUT", VERSAO, Q_VERSAO) == "Sim",
           "a descrição do veículo da InfoCap cita comfortline -> Sim",
           "📊 mapa §8.3: o que está na apólice não se pergunta ao segurado")
    checar(R("NIVUS HIGHLINE 1.0", VERSAO, Q_VERSAO) is None,
           "mas a AUSÊNCIA de 'comfortline' na descrição NÃO vira 'Não'",
           "descrição truncada -> 'Não' errado -> para-brisa sem o suporte do sensor")
    checar(R("escurecido", VERSAO, Q_VERSAO) is None,
           "e o vocabulário de película não vaza para a pergunta da versão",
           "a pergunta nomeia outro termo; 'escurecido' ali não significa sim")


def teste_nao_sabe_nunca_e_atalho():
    print("\n[7.4g] 'Não sabe' destrava a tela e ESTRAGA o pedido")
    from portal_worker.journeys.vidros_lanternas import explicar_especifico as E

    d = E("não sei qual lado, não estava no carro", LADO, Q_LADO)
    checar(d["escolha"] == "Não sabe" and d["motivo"] == "nao_sabe_honesto",
           "quando o SEGURADO não sabe, 'Não sabe' é a resposta honesta",
           "📊 mapa §4(a): as duas coisas são diferentes — só a segunda é honesta")

    # CONTROLE: a mesma frase de ignorância, com a resposta dentro. Não pode
    # virar atalho. Se as duas saíssem iguais, o guarda não guardaria nada.
    d2 = E("não sei o que houve, mas quebraram o do lado do motorista", LADO, Q_LADO)
    checar(d2["escolha"] == "Lado do motorista",
           "CONTROLE: 'não sei o que houve, MAS ... lado do motorista' -> responde",
           f"deu {d2['escolha']} — 'não sei' na frase não pode apagar a resposta que está nela")
    checar(d["escolha"] != d2["escolha"],
           "e as duas frases com 'não sei' saem DIFERENTES",
           "é o que prova que a distinção existe de verdade")

    # A inversão achada ao medir: num SIM/NÃO, 'não sei' tem o token 'não'.
    d3 = E("não sei", PELICULA, Q_PELICULA)
    checar(d3["escolha"] == "Não sabe" and d3["motivo"] == "nao_sabe_honesto",
           "'não sei' numa pergunta SIM/NÃO -> 'Não sabe', nunca 'NÃO'",
           f"deu {d3['escolha']}: afirmar que não tem película é inventar fato")
    checar(E("não", PELICULA, Q_PELICULA)["escolha"] == "NÃO",
           "CONTROLE: e um 'não' seco continua sendo NÃO",
           "senão o conserto teria matado a resposta legítima")


def teste_o_vocabulario_do_80_nao_invade_a_tela_da_peca():
    print("\n[7.4h] Cada vocabulário sabe quando a lista NÃO é dele")
    from portal_worker.journeys.vidros_lanternas import explicar_especifico as E
    from portal_worker.journeys.vidros_lanternas import match_option

    for nome, opcoes in (("peças do passo 4", PECAS), ("farol x lanterna", LUZES),
                         ("porta dianteira x traseira COM a peça", PORTA_PECA),
                         ("porta direita x esquerda COM a peça", PORTA_LADO),
                         ("tipo de telefone", TELEFONE), ("relação com o titular", RELACAO),
                         ("lojas do passo 7", LOJAS)):
        checar(E("qualquer coisa", opcoes, "")["dominio"] == "nenhum",
               f"'{nome}' -> dominio 'nenhum' (não é pergunta de atributo)")

    # E o que sobrevive disso: as decisões de PEÇA seguem idênticas. São as
    # mesmas afirmações do test_portal_de_reparos — repetidas aqui de propósito,
    # porque é este arquivo que poderia tê-las quebrado.
    checar(match_option("farol", LUZES) == "FAROL DIANTEIRO",
           "CONTROLE: 'farol' contra ['FAROL DIANTEIRO','LANTERNA TRASEIRA'] segue casando",
           "sem o portão de peça, 'dianteira/traseira' teria capturado esta lista")
    checar(match_option("vidro da porta traseira", PORTA_PECA) == "VIDRO DE PORTA TRASEIRA",
           "e a peça com posição no nome também")
    checar(match_option("vidro da porta", PORTA_LADO) is None,
           "e a que precisava parar continua parando (lado não foi dito)")


def teste_73_a_loja_e_campo_critico():
    print("\n[7.3] Campo não-crítico cai na 1a opção — e a 1a loja é sorteio")
    from portal_worker.adaptive import _is_critical_select as C

    for alvo in (Q_LOJA, "Escolha a unidade de atendimento", "oficina credenciada",
                 "Agendar a domicílio", "agendamento", "horario de atendimento",
                 Q_LADO, Q_PORTA, Q_PELICULA, Q_POSICAO, Q_TAMANHO, Q_VERSAO,
                 "Estado", "Cidade", "CEP", "Município", "Bairro",
                 "qualItemDanificado", "comoOcorreuDanoVeiculo", "ondeOcorreuDano"):
        checar(C(alvo) is True, f"crítico: '{alvo[:52]}'",
               "📊 antes: False — caía na 1a opção sem ninguém saber")

    # ⚠️ CONTROLE OBRIGATÓRIO: campo de FORMATO tem de continuar tolerante. Se
    # virar crítico, o robô trava num campo onde qualquer valor serve — e travar
    # ali não protege ninguém. Estes são os nomes REAIS (📊 mapa §4, passo 3).
    print("      -- controle: os que NÃO podem virar críticos --")
    for alvo in ("Tipo de telefone", "TipoTelefoneSolicitante0", "tipo de contato",
                 "DDD", "Como prefere ser atendido", "segr", "telefone-input",
                 "email-segurado-input", "nome-solicitante-input",
                 "cpf-cnpj-solicitante-input", "Sua relação com o titular"):
        checar(C(alvo) is False, f"tolerante: '{alvo}'",
               "campo de formato/identidade: parar aqui trava o acionamento à toa")

    checar(C("Tipo de telefone") != C("Qual o lado do item danificado?"),
           "CONTROLE: crítico e tolerante CONSEGUEM sair diferentes",
           "um guarda que devolvesse sempre o mesmo valor não guardaria nada")


def teste_73_o_select_nativo_tinha_a_mesma_porta():
    print("\n[7.3b] O sorteio também entrava pelo <select> nativo")
    from portal_worker.adaptive import _apply_select

    class _Sel:
        def __init__(self, name, opts):
            self.name, self.opts, self.escolhido = name, opts, None

        async def get_attribute(self, k):
            return self.name if k == "name" else ""

        async def evaluate(self, js, *a):
            return self.opts

        async def select_option(self, **kw):
            self.escolhido = kw.get("label")

    class _Page:
        def __init__(self, selects):
            self.selects = selects

        async def query_selector_all(self, sel):
            return self.selects if sel == "select" else []

        async def wait_for_timeout(self, ms):
            pass

    loja = _Sel("Escolha a loja onde deseja realizar o serviço", LOJAS)
    r = asyncio.run(_apply_select(_Page([loja]), loja.name, "a mais perto do segurado"))
    checar(r.startswith("select_options=") and loja.escolhido is None,
           "campo crítico sem match -> devolve as opções e NÃO seleciona nada", r)
    checar("AUTOGLASS MG19" in r and "AUTOGLASS SC02" in r,
           "e a lista devolvida tem as lojas reais para o cérebro copiar")

    # CONTROLE: campo de formato continua caindo na 1a opção real. Sem isto o
    # conserto teria travado o passo 3 num dropdown onde qualquer valor serve.
    tel = _Sel("TipoTelefoneSolicitante0", TELEFONE)
    r2 = asyncio.run(_apply_select(_Page([tel]), tel.name, "valor-que-nao-existe"))
    checar(r2.startswith("select_default=") and tel.escolhido == "COMERCIAL (Apenas ligações)",
           "CONTROLE: campo de formato ainda pega a 1a opção real", f"{r2} / {tel.escolhido}")


def teste_o_lugar_da_decisao_continua_sendo_um_so():
    print("\n[7.4i] Dois vocabulários, nenhum placar paralelo")
    ad = _ler("portal_worker", "adaptive.py")

    checar("from portal_worker.journeys.vidros_lanternas import explicar_match, explicar_especifico"
           in ad, "o adaptive IMPORTA as duas funções puras em vez de reimplementar")
    checar('esp = explicar_especifico(value, [t for t, _ in reais], target)' in ad
           and 'explicar_match(value, [t for t, _ in reais])["escolha"]' in ad,
           "e são elas que decidem dentro do _apply_mdselect")
    checar("let best = null, bestScore = -1;" not in ad and "if (bestScore <= 0) {" not in ad,
           "o placar escrito em JS continua não existindo",
           "era ELE que rodava em produção enquanto os testes provavam o outro")
    checar('if escolha is None and not critico and esp["dominio"] == "nenhum":' in ad,
           "e a 1a opção só é sorteada fora de qualquer pergunta do 80%",
           "dupla trava: nem campo crítico, nem pergunta de atributo")


def teste_a_trava_do_80_nao_afrouxou():
    print("\n[7.x] A trava que impede enviar o pedido continua no lugar")
    from portal_worker.adaptive import is_confirm_screen

    ad = _ler("portal_worker", "adaptive.py")
    checar(is_confirm_screen({"heading": "", "text":
           "80% Confirme a peça danificada ... película de controle solar (insulfilm)?"}),
           "a tela dos 80% continua sendo reconhecida")
    checar(not is_confirm_screen({"heading": "", "text":
           "20% Confirme seus dados. O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM"}),
           "CONTROLE: e o banner permanente continua NÃO sendo confundido com ela")
    checar("if is_confirm_screen(state) and not confirm:" in ad,
           "sem confirm=True, run_adaptive continua parando na confirmação")
    checar("NAO clique em botao que FINALIZE o pedido" in ad,
           "e o cérebro continua instruído a não finalizar por conta própria")


def main() -> int:
    print("=" * 72)
    print("O 80% SABE O QUE PERGUNTA — LADO, TAMANHO E POSICAO NAO SAO PECA")
    print("=" * 72)
    for t in (teste_m1_a_medicao_que_motivou_o_conserto,
              teste_m2_a_metade_que_errava,
              teste_o_lado_e_tabela_de_fato_nao_e_semelhanca,
              teste_dianteira_traseira_sem_o_mapa_de_pecas,
              teste_pelicula_e_a_negacao_que_inverte,
              teste_dez_centimetros_decidem_troca_ou_reparo,
              teste_posicao_do_trincado,
              teste_a_versao_esta_na_apolice_nao_no_segurado,
              teste_nao_sabe_nunca_e_atalho,
              teste_o_vocabulario_do_80_nao_invade_a_tela_da_peca,
              teste_73_a_loja_e_campo_critico,
              teste_73_o_select_nativo_tinha_a_mesma_porta,
              teste_o_lugar_da_decisao_continua_sendo_um_so,
              teste_a_trava_do_80_nao_afrouxou):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O LADO CERTO, O TAMANHO CERTO, A LOJA ESCOLHIDA — OU A PARADA COM A LISTA NA MAO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
