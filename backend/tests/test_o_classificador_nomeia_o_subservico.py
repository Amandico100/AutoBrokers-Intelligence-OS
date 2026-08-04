"""O classificador nomeia o SUBSERVIÇO — e por isso o acionamento acontece.

P-47. "residencial" não é o nome de trabalho nenhum.
-----------------------------------------------------
`infer_ramo_servico` devolve o par ``(ramo, servico)`` e é o único
classificador determinístico do produto: o Atlas usa, e `graph.py` usa para
achar o playbook de conduta. Um segundo classificador seria dois jeitos de
responder a mesma pergunta, divergindo com o tempo.

O defeito era um balde. Uma linha só::

    ("residencial", ("encanador", "eletricista", "chaveiro residencial",
                     "residencia", "residência")),

*Encanador*, *eletricista* e a própria palavra *residência* caíam no mesmo
lugar, e a função devolvia ``("residencial", "residencial")``.

Só que **"residencial" não é subserviço de nada**. Os declarados nos três
corredores residenciais são::

    Allianz   chaveiro · eletricista · eletrodomesticos · encanador
    HDI       chaveiro · desentupimento · eletricista · eletrodomesticos · encanador
    Porto     eletricista · eletrodomesticos · encanador

O que acontecia com um segurado dizendo "preciso de um eletricista":

1. o classificador devolvia serviço = ``residencial``;
2. `missing_slots_for_subservice` não encontrava esse subserviço e devolvia
   ``["subservico_invalido"]``;
3. o acionamento virava **handoff humano** — para um trabalho que os três
   corredores sabem fazer sozinhos.

E o dano não parava aí: `graph.py` procura o playbook de conduta por
``ramo`` + ``servico``, e nenhum playbook se chama "residencial/residencial".
A busca voltava vazia **sempre**.

Por que os termos são os mesmos de `_SUBSERVICE_ALIASES`
--------------------------------------------------------
A Porto chama de *"elétrica"* e *"hidráulica"* o que a Allianz e a HDI chamam de
eletricista e encanador. Esse vocabulário já está escrito uma vez, em
`corridor_playbooks._SUBSERVICE_ALIASES`. Inventar outro aqui criaria a segunda
verdade que o comentário do próprio produto diz que não pode existir.

E o RAMO continua vindo da palavra
-----------------------------------
"residência" nunca foi um serviço — é um ramo, e continua decidindo o ramo. O
que mudou é que ela parou de se disfarçar de trabalho. Para quem NÃO diz a
palavra ("preciso de um encanador"), o ramo sai do próprio subserviço: não
existe encanador de automóvel. `chaveiro` fica de fora dessa regra de
propósito — ele existe nos dois ramos.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


for _nome in ("app", "app.services", "app.services.atlas"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(RAIZ, rel))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


TPL = _carregar("app.services.atlas.templater", "app/services/atlas/templater.py")
PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")

RESIDENCIAIS = ("allianz", "hdi", "porto")

# O caso completo de um residencial (os slots que os três corredores pedem).
CASO_RESID = {
    "titular_cpf": "11122233344",
    "endereco_numero": "1678",
    "telefone_contato": "48991234567",
    "problema_descricao": "Tomadas da cozinha sem energia, sem cheiro de queimado",
    "periodo_preferido": "tarde",
    "risco_confirmado_sem_fumaca": "sim",
}


def _pb_resid(insurer: str) -> dict:
    return PB.get_playbook(PB.resolve_playbook_ref(insurer, "residencial"))


# --------------------------------------------------------------------------- #
# Casos
# --------------------------------------------------------------------------- #

def teste_o_servico_e_o_subservico():
    print("\n[1] As frases do segurado viram o NOME do trabalho")
    frases = {
        "preciso de um eletricista, a tomada da cozinha parou": ("residencial", "eletricista"),
        "tem um vazamento embaixo da pia, preciso de encanador": ("residencial", "encanador"),
        "o encanamento do banheiro estourou": ("residencial", "encanador"),
        "a pia esta entupida, preciso de desentupimento": ("residencial", "desentupimento"),
        "minha geladeira parou, e eletrodomestico": ("residencial", "eletrodomesticos"),
        # A Porto chama pelos outros nomes — e é o mesmo trabalho.
        "quero acionar a assistencia hidraulica": ("residencial", "encanador"),
        "preciso da assistencia eletrica da minha casa": ("residencial", "eletricista"),
    }
    for frase, (ramo_esp, serv_esp) in frases.items():
        ramo, servico = TPL.infer_ramo_servico([], frase)
        checar((ramo, servico) == (ramo_esp, serv_esp),
               f"{frase[:44]}… → {ramo_esp}/{serv_esp}", f"veio {ramo}/{servico}")

    checar(TPL.infer_ramo_servico([], "preciso de eletricista")[1] != "residencial",
           "e NENHUMA frase devolve mais o balde 'residencial' como servico",
           "'residencial' e ramo; como nome de trabalho nao existe em lugar nenhum")

    # O QUE ESTE CLASSIFICADOR NÃO FAZ, e não finge fazer: ler a intenção.
    # "Estou sem luz só na cozinha" é eletricista para uma pessoa e não casa
    # termo nenhum aqui — é o juízo que GOLD-ELEC-001 já declara como lacuna de
    # modelo. Este arquivo guarda o VOCABULÁRIO; o juízo é de outro.
    checar(TPL.infer_ramo_servico([], "estou sem luz so na cozinha")[1] == "",
           "frase sem o nome do trabalho continua SEM servico",
           "adivinhar aqui seria apertar uma tecla por conta propria — o "
           "classificador nomeia o que foi dito, nao o que talvez seja")


def teste_o_nome_e_aceito_pelo_corredor():
    print("\n[2] O nome devolvido ABRE o corredor — nao cai em subservico_invalido")
    # Este é o caso inteiro: a saída do classificador entra no motor sem
    # tradutor no meio. Era aqui que morria.
    _, servico = TPL.infer_ramo_servico([], "preciso de um eletricista urgente em casa")
    for insurer in RESIDENCIAIS:
        pbk = _pb_resid(insurer)
        checar(PB.subservice_supported(pbk, servico),
               f"{insurer}: reconhece {servico!r}")
        faltam = PB.missing_slots_for_subservice(pbk, servico, CASO_RESID)
        checar(faltam != ["subservico_invalido"],
               f"{insurer}: e o acionamento NAO cai em subservico_invalido",
               f"faltam={faltam}")

    _, encanador = TPL.infer_ramo_servico([], "tem um vazamento, preciso de encanador")
    for insurer in RESIDENCIAIS:
        pbk = _pb_resid(insurer)
        checar(PB.subservice_supported(pbk, encanador), f"{insurer}: reconhece {encanador!r}")

    # E o canônico é o próprio nome: o classificador fala a língua do corredor.
    for nome in ("eletricista", "encanador", "desentupimento", "eletrodomesticos"):
        checar(PB.canonical_subservice(nome) == nome,
               f"{nome!r} ja e o nome canonico — sem tradutor no meio")


def teste_o_ramo_continua_saindo_da_palavra():
    print("\n[3] 'residencia' continua decidindo o RAMO — so parou de virar servico")
    ramo, servico = TPL.infer_ramo_servico([], "quero atendimento residencial")
    checar(ramo == "residencial", "a palavra sozinha da o ramo", ramo)
    checar(servico == "",
           "e NAO inventa um servico",
           f"veio {servico!r} — dizer 'residencial' nao diz qual trabalho e")

    # Sem a palavra, o ramo sai do próprio subserviço: não há encanador de carro.
    ramo2, _ = TPL.infer_ramo_servico([], "preciso de um encanador")
    checar(ramo2 == "residencial",
           "e o subservico sozinho ja implica o ramo", ramo2)

    # `chaveiro` existe nos DOIS ramos — e por isso NÃO implica ramo nenhum.
    checar(TPL.infer_ramo_servico([], "chaveiro, tranquei a chave dentro do carro")
           == ("auto", "chaveiro"),
           "chaveiro sem 'residencia' é AUTO")
    checar(TPL.infer_ramo_servico([], "chaveiro residencial, tranquei a porta de casa")
           == ("residencial", "chaveiro"),
           "e com 'residencial' é RESIDENCIAL — mesmo subservico, ramos diferentes")


def teste_o_lado_auto_nao_regrediu():
    print("\n[4] O que ja funcionava continua igual")
    casos = {
        "acabou o combustivel na estrada, o carro parou": ("auto", "pane_seca"),
        "preciso de guincho, bati o carro": ("auto", "guincho"),
        "a bateria arriou": ("auto", "bateria"),
        "furei o pneu": ("auto", "pneu"),
        "trincou o para-brisa": ("auto", "vidros"),
        "reboque para o meu veiculo": ("auto", "guincho"),
    }
    for frase, esperado in casos.items():
        veio = TPL.infer_ramo_servico([], frase)
        checar(veio == esperado, f"{frase[:38]}… → {esperado}", str(veio))

    # O rótulo de menu do Atlas (o outro chamador) também não mudou.
    checar(TPL.infer_ramo_servico(["Guincho (reboque)", "Chaveiro", "Bateria"],
                                  "assistencia 24h veiculo") == ("auto", "guincho"),
           "e a inferencia por LABELS de menu continua a mesma")

    # O RISCO QUE OS TERMOS NOVOS TROUXERAM, e o que o segura.
    # "elétrica" agora é termo de eletricista — e carro também tem parte
    # elétrica. Quem protege é a ORDEM: os subserviços de auto são avaliados
    # primeiro, e o laço para no primeiro que casa.
    for frase, esperado in (
        ("o carro nao liga, acho que e a bateria, parte eletrica", ("auto", "bateria")),
        ("preciso de guincho, deu pane eletrica no veiculo", ("auto", "guincho")),
    ):
        veio = TPL.infer_ramo_servico([], frase)
        checar(veio == esperado,
               f"caso de AUTO com a palavra 'eletrica' → {esperado}", str(veio))


def teste_um_vocabulario_so():
    print("\n[5] Os termos sao os do corredor, nao um dicionario paralelo")
    # A Porto chama de "elétrica"/"hidráulica"; o corredor já traduz. Se o
    # classificador tivesse a própria lista, as duas divergiriam com o tempo.
    for apelido, canonico in (("eletrica", "eletricista"), ("hidraulica", "encanador"),
                              ("encanamento", "encanador")):
        checar(PB.canonical_subservice(apelido) == canonico,
               f"o corredor traduz {apelido!r} → {canonico!r}")
        checar(TPL.infer_ramo_servico([], f"preciso de {apelido}")[1] == canonico,
               f"e o classificador chega no MESMO {canonico!r}",
               "duas listas de sinonimos e como a segunda fica para tras")

    fonte = open(os.path.join(RAIZ, "app", "services", "atlas", "templater.py"),
                 encoding="utf-8").read()
    checar("_SUBSERVICE_ALIASES" in fonte,
           "e o codigo diz de onde os termos vieram",
           "sem a referencia escrita, a proxima pessoa acrescenta so de um lado")


def teste_o_guarda_tem_como_falhar():
    print("\n[6] CONTROLE — o classificador de ANTES reprova")
    def antes(texto: str):
        """A função como era, verbatim na parte que interessa."""
        blob = texto.lower()
        servico = ""
        for key, terms in (
            ("guincho", ("guincho", "reboque", "remocao", "remoção")),
            ("chaveiro", ("chaveiro", "chave", "trancad")),
            ("bateria", ("bateria", "carga")),
            ("pane_seca", ("pane seca", "combustivel", "combustível")),
            ("pneu", ("pneu", "troca de pneu", "estepe")),
            ("vidros", ("vidro", "para-brisa", "parabrisa")),
            ("residencial", ("encanador", "eletricista", "chaveiro residencial",
                             "residencia", "residência")),
        ):
            if any(t in blob for t in terms):
                servico = key
                break
        ramo = "residencial" if servico == "residencial" or "residenc" in blob else "auto"
        return ramo, servico

    frase = "preciso de um eletricista urgente em casa"
    ramo_antes, serv_antes = antes(frase)
    checar((ramo_antes, serv_antes) == ("residencial", "residencial"),
           "o classificador de ANTES devolve o balde 'residencial'",
           f"veio {ramo_antes}/{serv_antes} — se nao devolvesse, o controle "
           "nao provaria nada")

    pbk = _pb_resid("allianz")
    checar(not PB.subservice_supported(pbk, serv_antes),
           "e esse nome NAO e reconhecido por nenhum corredor")
    checar(PB.missing_slots_for_subservice(pbk, serv_antes, CASO_RESID)
           == ["subservico_invalido"],
           "o acionamento cairia em subservico_invalido — o defeito de P-47",
           "se este caso ficar vermelho, o caso [2] passaria com ou sem o "
           "conserto e nao guarda nada (CLAUDE.md §9.3)")

    # E o de hoje resolve o MESMO texto de um jeito que o corredor aceita.
    _, serv_hoje = TPL.infer_ramo_servico([], frase)
    checar(serv_hoje != serv_antes, "hoje o nome e outro", f"{serv_antes!r} → {serv_hoje!r}")
    checar(PB.subservice_supported(pbk, serv_hoje),
           "e o corredor aceita — os dois lados conseguem ser diferentes")


def main() -> int:
    print("=" * 74)
    print("O CLASSIFICADOR NOMEIA O SUBSERVICO — P-47")
    print("=" * 74)

    for teste in (teste_o_servico_e_o_subservico,
                  teste_o_nome_e_aceito_pelo_corredor,
                  teste_o_ramo_continua_saindo_da_palavra,
                  teste_o_lado_auto_nao_regrediu,
                  teste_um_vocabulario_so,
                  teste_o_guarda_tem_como_falhar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CLASSIFICADOR FALA A LINGUA DO CORREDOR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
