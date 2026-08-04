"""O que já se sabe é escrito por código; o modelo decide só o que é julgamento.

A autópsia que produziu este arquivo
-------------------------------------
📊 04/08/2026, os 39 acionamentos de `vidros_lanternas` (Supabase
`dcajcvlzcjbmyapmklil`), lidos um a um:

    9   estouraram o teto de 22 passos
    4   o cérebro PERGUNTOU um dado que estava no payload — inclusive
        *"Qual é o tipo de telefone do segurado?"*, que o próprio prompt do
        sistema proíbe com todas as letras
    7   ele repetiu uma ação que já tinha voltado `filled` /
        `mdselect=corretor` — ou seja, que **tinha funcionado**
    1   escreveu "Santa Catarina" num autocomplete onde o prompt manda a SIGLA

📊 E não foi falta de cérebro: **zero** jobs registram `cerebro de visao
indisponivel` ou `nao consegui decidir`. Ele estava lá, com a instrução na
frente, e não seguiu.

Nome da corretora, e-mail, CNPJ, telefone, relação (`Corretor`), estado, cidade
e CEP têm **um único valor certo, sabido antes de a tela abrir**. Pedir a um
modelo que "decida" preenchê-los cria três riscos de graça: ele pergunta o que
já sabe, erra o formato, ou gasta passos do teto — e o teto foi atingido 9 vezes.

O guarda que mais importa é o [2]
----------------------------------
Preencher automaticamente é poderoso e perigoso na mesma medida. O campo de CPF
do **passo 1** é do titular da apólice; o do **passo 2** é da corretora. Escrever
o CNPJ da corretora no campo do titular abriria o pedido **da apólice errada** —
e o mapa (§7) diz que isso não se desfaz: vira um segundo atendimento.

Por isso a regra é: **só preenche quando exatamente UM campo visível e vazio
casa.** Duas correspondências é ambiguidade, e ambiguidade volta para o cérebro.
É o mesmo princípio do `explicar_match`: na dúvida, não chuta.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _carregar():
    caminho = os.path.join(RAIZ, "backend", "portal_worker", "adaptive.py")
    spec = importlib.util.spec_from_file_location("_adaptive", caminho)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_adaptive"] = m
    spec.loader.exec_module(m)
    return m


AD = _carregar()

# O que a corretora é — vem de `companies`, nunca do LLM, nunca do segurado.
CORRETORA = {"relacao": "Corretor", "nome": "Resulta Seguros Ltda",
             "email": "operacional@resulta.com.br", "telefone": "4833646664",
             "cpf_cnpj": "12345678000199"}
LOCAL = {"estado": "SC", "cidade": "Florianopolis", "cep": "88010-001"}
SABIDO = {"solicitante": CORRETORA, "local": LOCAL}


def _tela(*campos):
    """Uma tela como o `capture_state` a devolve."""
    return {"inputs": list(campos), "mdselects": [], "selects": []}


def _campo(**kw):
    base = {"id": "", "name": "", "placeholder": "", "label": "", "value": ""}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------

def teste_o_passo2_se_preenche_sozinho():
    print("\n[1] A tela 'Confirme seus dados' (20%) não precisa de modelo")

    # 📊 Os nomes reais, lidos dos `portal_jobs` de produção.
    tela = _tela(
        _campo(id="email-segurado-input", label="E-mail"),
        _campo(id="nome-solicitante-input", label="Seu nome completo (solicitante)"),
        _campo(id="cpf-cnpj-solicitante-input", label="CPF ou CNPJ (solicitante)"),
        _campo(id="telefone-input", label="Telefone"),
    )
    achados = {f["de"]: f["valor"] for f in AD.fatos_da_tela(tela, SABIDO)}
    for chave, esperado in (("email", CORRETORA["email"]), ("nome", CORRETORA["nome"]),
                            ("cpf_cnpj", CORRETORA["cpf_cnpj"]), ("telefone", CORRETORA["telefone"])):
        checar(achados.get(chave) == esperado, f"'{chave}' é preenchido por código",
               f"achado={achados.get(chave)!r}")

    # 📊 O cérebro perguntou o nome do segurado 1x e o tipo de telefone 1x —
    # com tudo isso no payload. Cada um destes é um passo do teto devolvido.
    checar(len(achados) == 4, "os quatro campos da tela saem de uma vez",
           f"{sorted(achados)}")


def teste_nao_escreve_no_campo_errado():
    print("\n[2] CONTROLE DO DANO — não escreve onde não deve")
    print("     (o CNPJ da corretora no campo do titular abriria a apólice errada)")

    # O campo do passo 1 é do TITULAR. O CNPJ da corretora não pode ir ali.
    tela_passo1 = _tela(
        _campo(id="inserir-cpf-input", label="CPF/CNPJ (solicitante)"),
        _campo(id="input_1", label="Placa do veículo (segurado)"),
    )
    achados = AD.fatos_da_tela(tela_passo1, SABIDO)
    checar(achados == [], "no passo 1, NADA é preenchido por código",
           f"escreveria: {achados}")

    # Campo já preenchido não se toca — reescrever é o que fazia o cérebro
    # repetir ação e a tela ser declarada travada (📊 7 casos).
    tela_cheia = _tela(_campo(id="email-segurado-input", label="E-mail",
                              value="ja@estava.com"))
    checar(AD.fatos_da_tela(tela_cheia, SABIDO) == [],
           "campo JÁ PREENCHIDO não é reescrito",
           "reescrever é o que fazia a tela ser declarada travada")

    # Ambiguidade: dois campos casam. Quem decide é o cérebro, com a tela toda.
    tela_ambigua = _tela(
        _campo(id="email-um", label="E-mail"),
        _campo(id="email-dois", label="E-mail de confirmação"),
    )
    achados = [f for f in AD.fatos_da_tela(tela_ambigua, SABIDO) if f["de"] == "email"]
    checar(achados == [], "com DOIS campos de e-mail, não escreve em nenhum",
           f"escreveria: {achados}")

    # E o segurado nunca é confundido com o solicitante.
    tela_nome = _tela(_campo(id="nome-do-segurado", label="Nome do segurado"))
    checar(AD.fatos_da_tela(tela_nome, SABIDO) == [],
           "'Nome do segurado' NÃO recebe o nome da corretora",
           "são pessoas diferentes — a corretora é quem SOLICITA")


def teste_o_local_vai_no_formato_que_o_portal_aceita():
    print("\n[3] Estado, cidade e CEP — o passo do 'onde consertar'")

    tela = _tela(
        _campo(id="fl-input-65", label="Selecione o estado onde deseja ser atendido."),
        _campo(id="fl-input-66", label="Escolha a cidade disponível para atendimento."),
        _campo(id="fl-input-67", label="CEP (opcional)"),
    )
    achados = {f["de"]: f["valor"] for f in AD.fatos_da_tela(tela, SABIDO)}
    # 📊 Um job mandou "Santa Catarina" e o autocomplete não devolveu nada. A
    # sigla vem pronta do `build_portal_params`; ninguém precisa lembrar disso.
    checar(achados.get("estado") == "SC", "o estado vai como SIGLA", str(achados.get("estado")))
    checar(achados.get("cidade") == "Florianopolis", "a cidade vai")
    # "Opcional" no portal; obrigatório para nós — é ele que acha a unidade
    # mais próxima e libera atendimento a domicílio.
    checar(achados.get("cep") == "88010-001", "e o CEP vai, mesmo sendo 'opcional'",
           "sem CEP não há atendimento a domicílio")

    # CONTROLE — estado e cidade não se confundem.
    checar(achados.get("estado") != achados.get("cidade"),
           "CONTROLE — estado e cidade não recebem o mesmo valor")


def teste_o_guarda_consegue_ficar_calado():
    print("\n[4] CONTROLE — sem dado conhecido, não inventa nada")

    tela = _tela(_campo(id="email-segurado-input", label="E-mail"),
                 _campo(id="telefone-input", label="Telefone"))

    # Corretora sem perfil configurado: nada a escrever.
    checar(AD.fatos_da_tela(tela, {"solicitante": {}, "local": {}}) == [],
           "sem perfil da corretora, nada é preenchido")
    checar(AD.fatos_da_tela(tela, {}) == [], "sem `collected`, nada é preenchido")
    checar(AD.fatos_da_tela({}, SABIDO) == [], "sem tela, nada é preenchido")

    # E a CONTRAPROVA: a mesma tela COM os dados escreve. Sem este par, uma
    # função que devolvesse `[]` sempre passaria em todo o resto do arquivo.
    checar(len(AD.fatos_da_tela(tela, SABIDO)) == 2,
           "CONTRAPROVA — a mesma tela COM os dados preenche os dois",
           "prova que os silêncios acima vêm da falta de dado, não de cegueira")


def teste_o_loop_usa_isso_antes_de_chamar_o_modelo():
    print("\n[5] O loop preenche ANTES de gastar um passo com o modelo")
    with open(os.path.join(RAIZ, "backend", "portal_worker", "adaptive.py"),
              encoding="utf-8") as fh:
        fonte = fh.read()
    sem_com = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    corpo = sem_com.split("async def run_adaptive", 1)[-1]
    i_fato = corpo.find("preencher_o_que_e_fato(page")
    i_cerebro = corpo.find("decide_next_action(state")
    checar(0 < i_fato < i_cerebro,
           "o preenchimento vem ANTES da decisão do modelo",
           f"fato={i_fato} cerebro={i_cerebro} — depois, seria inútil")

    # CONTROLE — o freio do 80% continua intocado. Nada disto pode ter chegado
    # perto dele: é ele que impede o pedido de ser enviado sem aprovação.
    checar("if is_confirm_screen(state) and not confirm:" in sem_com,
           "CONTROLE — a trava do 80% continua exatamente onde estava")
    checar("MAX_STEPS = 22" in sem_com, "CONTROLE — o teto de passos continua existindo")


def main() -> int:
    print("=" * 70)
    print("O QUE E FATO NAO PASSA POR UM MODELO")
    print("=" * 70)
    for teste in (teste_o_passo2_se_preenche_sozinho,
                  teste_nao_escreve_no_campo_errado,
                  teste_o_local_vai_no_formato_que_o_portal_aceita,
                  teste_o_guarda_consegue_ficar_calado,
                  teste_o_loop_usa_isso_antes_de_chamar_o_modelo):
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
    print("O MODELO DECIDE SO O QUE E JULGAMENTO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
