"""O acervo tinha 10.818 cartas com dois rótulos que não diziam a verdade.

O que estava errado
-------------------
**O assunto era uma palavra só.** `category` valia `processo` em 100% das
11.640 cartas. Uma coluna que responde a mesma coisa para todo mundo não
responde nada — e ninguém percebia, porque ela existia, tinha nome e nunca
reclamava.

**A seguradora era da conversa, não do fato.** O destilador carimbava a
companhia da SESSÃO em até oito fatos, inclusive nos genéricos. 📊 Das 3.354
cartas etiquetadas, só 1.083 (32,3%) citavam a própria seguradora no texto.
Numa amostra de seis cartas `allianz` que não citavam a Allianz, seis eram fato
de mercado — uma delas de seguro PET, gravada como `allianz` / `auto`.

Por que isso era quase inofensivo, e por que deixou de ser
----------------------------------------------------------
Hoje `build_global_search_kwargs` aceita `carrier_slug` e o descarta: não existe
filtro por seguradora. Um rótulo errado num campo que ninguém lê não machuca
ninguém — e é exatamente por isso que ele sobreviveu dois meses. No dia em que
o filtro ligar, o agente passa a responder regra da Allianz a segurado da HDI
sem que nada quebre e sem que ninguém veja.

O que este arquivo guarda
-------------------------
Cada caso tem uma **linha de controle**: ao lado do texto que precisa perder o
rótulo, o texto quase igual que precisa MANTER. Um guarda que só sabe dizer
"não" acerta 100% das remoções apagando o acervo inteiro — e não guarda nada.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def _servico(nome: str):
    spec = importlib.util.spec_from_file_location(
        f"app.services.{nome}", os.path.join(RAIZ, "app", "services", f"{nome}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"app.services.{nome}"] = mod
    spec.loader.exec_module(mod)
    return mod


C = _servico("curadoria_cartas")
PB = _servico("corridor_playbooks")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _par(nome: str, mantem: tuple, rebaixa: tuple, esperado: str) -> None:
    """Um caso é sempre um PAR: o que fica e o que cai.

    Escrito assim de propósito. Um caso solto de rebaixamento passaria com uma
    função que devolve None sempre; o par só passa se a função souber
    distinguir — e a distinção é a coisa toda.
    """
    tx_m, seg_m = mantem
    tx_r, seg_r = rebaixa
    ficou, _ = C.seguradora_do_fato(tx_m, seg_m)
    caiu, _ = C.seguradora_do_fato(tx_r, seg_r)
    checar(ficou == esperado, f"{nome}: MANTÉM o rótulo certo ({esperado})", f"veio {ficou!r}")
    checar(caiu is None, f"{nome}: rebaixa o rótulo que o texto não confirma", f"veio {caiu!r}")


def teste_o_texto_e_que_manda():
    print("\n[1] A seguradora é do FATO, não da conversa")
    _par(
        "citação",
        mantem=("Na Allianz o boleto gerado por parcela nao autorizada sai com a "
                "data original de vencimento", "Allianz"),
        rebaixa=("Boleto vencido nao pode ser reemitido com novo vencimento pelo "
                 "sistema, gerando juros conforme instrucoes originais", "Allianz"),
        esperado="allianz",
    )
    # E o normalizador continua fazendo o trabalho dele: a grafia não importa.
    for grafia in ("Tokio Marine", "tokio_marine", "TÓKIO MARINE"):
        k, _ = C.seguradora_do_fato("Na Tokio o boleto traz QRCode PIX no proprio documento", grafia)
        checar(k == "tokio", f"'{grafia}' vira a mesma chave `tokio`", f"veio {k!r}")


def teste_exemplo_nao_e_dono():
    print("\n[2] Citar como EXEMPLO não transfere a propriedade da regra")
    _par(
        "exemplificação",
        mantem=("Na Porto a parcela em atraso pode ser reprogramada dentro de "
                "um limite de dias contados do vencimento", "porto"),
        rebaixa=("A parcela pode ser reprogramada como qualquer outra parcela; "
                 "nesta conversa foi num endosso da Porto", "porto"),
        esperado="porto",
    )
    # 📊 O marcador é estreito de propósito: "nesse caso" aparece em 113 cartas
    # e quase nunca marca exemplo — em "Nesse caso a AXA gera boleto novo", a
    # AXA é quem AGE. Um marcador largo rebaixaria ~130 rótulos corretos.
    k, _ = C.seguradora_do_fato(
        "Nesse caso a AXA gera boleto novo da parcela em aberto", "axa")
    checar(k == "axa", "'nesse caso' NÃO é marcador de exemplo",
           f"veio {k!r} — a AXA é quem age na frase")


def teste_o_banco_nao_e_a_seguradora():
    print("\n[3] Bradesco banco e Bradesco Seguros são empresas diferentes")
    _par(
        "banco",
        mantem=("Na Bradesco nao e possivel abrir um novo CAC enquanto houver "
                "outro em andamento para o mesmo caso", "bradesco"),
        rebaixa=("O banco Bradesco passou a exigir autorizacao do correntista "
                 "para debitar seguro em conta", "bradesco"),
        esperado="bradesco",
    )


def teste_prestadora_nao_e_seguradora():
    print("\n[4] Quem ATENDE pela seguradora não É a seguradora")
    # A armadilha: o texto NOMEIA a Autoglass. Confirmação textual sozinha
    # manteria o rótulo — e a Autoglass atende várias companhias, então o
    # filtro por seguradora devolveria a errada.
    k, prest = C.seguradora_do_fato(
        "Autoglass direciona vistorias de vidros para lojas credenciadas "
        "conforme item danificado", "autoglass")
    checar(k is None, "a prestadora sai de `insurer_key`", f"veio {k!r}")
    checar(prest == "autoglass", "e a informação NÃO se perde: vai para `prestadora`",
           f"veio {prest!r}")
    for nome in ("hantei", "mondial", "crawford brasil", "resulta", "autofleet"):
        k, prest = C.seguradora_do_fato(f"Na {nome} o prazo de retorno e de 5 dias uteis", nome)
        checar(k is None and bool(prest), f"{nome:16} não vira seguradora", f"{k!r}/{prest!r}")
    # CONTROLE: uma seguradora de verdade, na mesma frase, continua passando.
    k, prest = C.seguradora_do_fato("Na Mapfre o prazo de retorno e de 5 dias uteis", "mapfre")
    checar(k == "mapfre" and prest is None,
           "e a seguradora de verdade continua entrando", f"{k!r}/{prest!r}")


def teste_chave_composta_e_de_ninguem():
    print("\n[5] Fato visto em cinco companhias não é regra de uma delas")
    for composta in ("porto/azul", "allianz/zurich/porto/alfa/youse", "mapfre/yelum/ezze"):
        k, _ = C.seguradora_do_fato("Na Porto o boleto sai com a data original", composta)
        checar(k is None, f"{composta:32} vira NULL", f"veio {k!r}")
    # CONTROLE: sem a barra, a mesma carta mantém o rótulo.
    k, _ = C.seguradora_do_fato("Na Porto o boleto sai com a data original", "porto")
    checar(k == "porto", "e `porto` sozinho continua valendo", f"veio {k!r}")


def teste_caixa_dagua_nao_e_a_caixa_seguradora():
    print("\n[6] Nome de seguradora que também é palavra comum")
    # 📊 `caixa` aparece 80 vezes nas published; 31 são "caixa d'água". Aceitar
    # a palavra solta etiquetaria 48 cartas de assistência residencial com uma
    # companhia que não tem nada a ver com elas.
    k, _ = C.seguradora_do_fato(
        "A assistencia de limpeza contempla a caixa d agua e nao a cisterna", "caixa")
    checar(k is None, "'caixa d'água' não confirma a Caixa Seguradora", f"veio {k!r}")
    k, _ = C.seguradora_do_fato(
        "Na Caixa Seguradora o boleto da parcela sai com vencimento proprio", "caixa")
    checar(k == "caixa", "mas 'Caixa Seguradora' escrito por extenso confirma", f"veio {k!r}")


def teste_so_seguradora_conhecida_entra():
    print("\n[7] A lista de quem é seguradora mora em UM lugar")
    conhecidas = set(PB._INSURER_ALIASES.values())
    checar("essor" in conhecidas and "sulamerica" in conhecidas,
           "as companhias achadas no acervo entraram na tabela de apelidos",
           "senão `sul america` continuaria virando a chave `sul`")
    k = PB.normalize_insurer_key("Sul America", para="conhecimento")
    checar(k == "sulamerica", "e 'Sul America' deixou de virar `sul`", f"veio {k!r}")
    for lixo in ("brinox", "pedrita", "betel", "dva", "yellow", "allianza"):
        k, _ = C.seguradora_do_fato(f"Na {lixo} o prazo e de 5 dias", lixo)
        checar(k is None, f"{lixo:10} não é seguradora, mesmo citado no texto", f"veio {k!r}")


def teste_o_assunto_separa_cartas_diferentes():
    print("\n[8] Cartas de assuntos diferentes recebem valores diferentes")
    # A linha de controle deste eixo: o classificador tem de conseguir devolver
    # CINCO respostas distintas. Um classificador constante passaria em
    # qualquer caso isolado.
    casos = {
        "sinistro": "A reguladora agenda a vistoria dos danos apos a abertura do sinistro",
        "cobranca": "O boleto da parcela vence em cinco dias e pode ser pago por PIX",
        "assistencia": "O chaveiro chega em ate duas horas quando a chave fica trancada no carro",
        "apolice": "O endosso de troca de veiculo altera a vigencia da apolice",
        "atendimento": "Equipes de corretora costumam fazer revisao semanal de pendencias",
    }
    vistos = {}
    for esperado, texto in casos.items():
        veio = C.assunto_da_carta(texto)
        vistos[esperado] = veio
        checar(veio == esperado, f"{esperado:12} · {texto[:48]}...", veio)
    checar(len(set(vistos.values())) == 5,
           "os cinco valores são REALMENTE alcançáveis",
           f"só saíram {sorted(set(vistos.values()))}")
    checar(set(C.ASSUNTOS_VALIDOS) == set(casos),
           "e a lista fechada tem exatamente estes cinco",
           str(C.ASSUNTOS_VALIDOS))


def teste_o_catchall_e_o_ultimo_e_tem_nome():
    print("\n[9] O que sobra tem nome, e o nome vem por último")
    checar(C.ASSUNTO_PADRAO == "atendimento",
           "o catch-all se chama `atendimento`, não `processo`",
           "`processo` estava em 100% das 11.640 cartas e não dizia nada")
    checar(C.ASSUNTO_PADRAO not in [n for n, _ in C._ASSUNTOS],
           "e ele não tem regex próprio — só recebe quem não é momento nenhum")
    # A vistoria PRÉVIA é do contrato; a vistoria de dano é do sinistro. Se o
    # lookahead cair, as duas viram a mesma coisa e ninguém percebe.
    checar(C.assunto_da_carta("A vistoria previa vence antes da emissao") == "apolice",
           "vistoria PRÉVIA é da apólice")
    checar(C.assunto_da_carta("A vistoria dos danos e agendada pela loja") == "sinistro",
           "vistoria de DANO é do sinistro")


def teste_todos_os_caminhos_usam_a_mesma_decisao():
    print("\n[10] Um caminho só — nenhum motor paralelo (§5)")
    portas = {
        "destilador (runtime)": ("app", "services", "attendance_distiller.py"),
        "aplicar.py (lote)": ("scripts", "destilacao_max", "aplicar.py"),
        "aplicar_sql.py (MCP)": ("scripts", "destilacao_max", "aplicar_sql.py"),
        "atribuir_seguradora.py": ("scripts", "destilacao_max", "atribuir_seguradora.py"),
    }
    for nome, caminho in portas.items():
        fonte = _ler(*caminho)
        checar("seguradora_do_fato" in fonte,
               f"{nome:24} decide pela mesma função",
               "reescrever a regra aqui faria o acervo divergir conforme a porta de entrada")
    for nome, caminho in portas.items():
        if nome.startswith("atribuir"):
            continue
        fonte = _ler(*caminho)
        checar('"category": "processo"' not in fonte and "'processo'" not in fonte,
               f"{nome:24} não grava mais o assunto morto")
        checar("assunto_da_carta" in fonte,
               f"{nome:24} calcula o assunto de verdade")
    # `_chave_da_seguradora` era o atalho que gravava a companhia da sessão
    # direto. Se voltar, volta o defeito inteiro.
    fonte = _ler("app", "services", "attendance_distiller.py")
    checar("def _chave_da_seguradora" not in fonte,
           "o atalho antigo não voltou ao destilador")


def main() -> int:
    print("=" * 70)
    print("O RÓTULO DA CARTA DIZ O QUE O NOME DELE PROMETE")
    print("=" * 70)
    for teste in (teste_o_texto_e_que_manda,
                  teste_exemplo_nao_e_dono,
                  teste_o_banco_nao_e_a_seguradora,
                  teste_prestadora_nao_e_seguradora,
                  teste_chave_composta_e_de_ninguem,
                  teste_caixa_dagua_nao_e_a_caixa_seguradora,
                  teste_so_seguradora_conhecida_entra,
                  teste_o_assunto_separa_cartas_diferentes,
                  teste_o_catchall_e_o_ultimo_e_tem_nome,
                  teste_todos_os_caminhos_usam_a_mesma_decisao):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CAMPO GUARDA O QUE O NOME DELE DIZ QUE GUARDA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
