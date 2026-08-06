"""A confirmação confere antes de abrir — e consegue reprovar.

O QUE ESTE ARQUIVO GUARDA
-------------------------
O acionamento tem UMA decisão irreversível: dizer "sim" à seguradora. Depois
dela existe um guincho na rua e uma pessoa esperando. Todo o resto do corredor
se conserta na mensagem seguinte; esta não.

📊 Medido em 05/08/2026 contra o motor real, com `DISPATCH_FINALIZE_MODE=live`
(o padrão desde 04/08), sobre a tela real da Allianz:

    o caso diz .......... Rua Doutor Fúlvio Aducci, 1235
    o resumo da URA diz . Rua Doutor Fúlvio Aducci, 1253
    o motor respondeu ... "1"      ← CONFIRMOU

Três caracteres de diferença, e o guincho sai para uma casa que EXISTE, na rua
certa, com a pessoa errada atendendo a porta.

📊 E `guard_human_phase_reply` aprovou os QUATRO rascunhos afirmativos sobre o
MESMO resumo errado ("1", "Sim", "Sim, pode confirmar", "Confirmo, está
correto"). Não é defeito dele: a assinatura é `(reply, session)` — ele nunca
recebeu a mensagem da seguradora e não tem como saber com o que está
concordando. Ele fiscaliza o RASCUNHO; ninguém fiscalizava o FATO.

📊 E o caminho principal NEM É A LLM. Quem responde a tela de confirmação é o
passo determinístico do corredor: `confirmar_atendimento` → "1",
`confirmar_solicitacao` → "Confirmar solicitação", `confirmar_abertura` → "Sim".
Um guarda que morasse dentro de `guard_human_phase_reply` não protegeria quem
mais dispara. Por isso ele mora no choke point por onde os DOIS passam.

A CONFERÊNCIA ERA PROSA
-----------------------
A checagem dos quatro campos já existia — em `_AUTO_HUMAN_PHASE_GUIDANCE`,
dentro do prompt: *"antes de confirmar, confira (1) placa e veículo (2) o
serviço (3) o endereço de origem (4) o destino"*. Um modelo lendo "1253" logo
abaixo de "1235" concorda com facilidade. Texto no prompt é PEDIDO, não
verificação.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
Um guarda que não consegue reprovar não guarda nada — e um que reprova tudo
também não. Os casos [C3], [C6], [C7] e [C10] rodam a MESMA chamada DUAS vezes:
com o dado errado (reprova) e com o dado certo (aprova). É a segunda que dá o
direito de concluir que o mérito foi do dado, e não de o guarda estar sempre
dizendo não.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(AQUI, ".."))

FALHAS: list = []


def checar(condicao: bool, descricao: str, porque: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  X     {descricao}")
        if porque:
            print(f"        {porque}")
        FALHAS.append(descricao)


# Importar pelo pacote puxaria `openai`/`pydantic_settings`, que não existem na
# máquina de desenvolvimento — o teste reprovaria por ausência de dependência e
# não por defeito, que é a pior espécie de vermelho: ela ensina a ignorar o
# teste. Os dois módulos só importam biblioteca padrão no topo (e um ao outro).
for _nome in ("app", "app.services", "app.services.atlas"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(BACKEND, rel))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
DS = _carregar("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")

# ARMADO DE PROPÓSITO (CLAUDE.md §9.3): a conferência só é interessante em modo
# `live`, que é o padrão desde 04/08 — mas um teste que DEPENDE de um padrão
# para de testar no dia em que o padrão muda. Aqui o modo é escrito.
os.environ["DISPATCH_FINALIZE_MODE"] = "live"
os.environ.pop("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", None)
os.environ.pop(DS.FREIO_DE_EMERGENCIA, None)


# ---------------------------------------------------------------------------
# As telas, como as seguradoras as escrevem — com negrito e tudo.
# ---------------------------------------------------------------------------
CERTO = "Rua Doutor Fúlvio Aducci, 1235 - Estreito - Florianópolis - SC"
ERRADO = "Rua Doutor Fúlvio Aducci, 1253 - Estreito - Florianópolis - SC"
DESTINO = "Rua São José, 90 - Centro - São José - SC"

SLOTS = {
    "titular_cpf": "11122233344", "titular_nome": "João da Silva",
    "veiculo_placa": "JCL9A59", "veiculo_descricao": "Toyota Hilux SW4 2019",
    "local_atual": CERTO, "local_destino": DESTINO,
    "problema_descricao": "não liga", "quando": "agora",
    "telefone_contato": "48991072089", "servico_opcao": "3",
}


def _resumo_allianz(origem: str, servico: str = "reboque para pane mecânica") -> str:
    return ("*RESUMO DA SOLICITAÇÃO*\n"
            "*Placa:* JC#-###9\n"
            "*Veículo:* HILUX SW4\n"
            f"*Serviço:* {servico}\n"
            f"*Origem:* {origem}\n"
            f"*Destino:* {DESTINO}\n"
            "Podemos confirmar o atendimento?\n*1 -* Sim\n*2 -* Não, desejo reiniciar\n*0 -* Sair")


RESUMO_AZUL = ("Antes de confirmar a solicitação, confira as informações 👇\n"
               "Serviço: Guincho\n"
               f"Origem: {ERRADO}\n"
               f"Destino: {DESTINO}")
DECISAO_AZUL = ("Como você quer prosseguir?\nConfirmar solicitação\nMudar localização atual\n"
                "Alterar local de destino\nAlterar dados de contato\nSair e não agendar")
TELA_YELUM = ("Você precisa do atendimento agora ou prefere agendar para outro momento?\n"
              "Botão 1: Agora\nBotão 2: Agendar\nBotão 3: Voltar")


def _sessao(slots=None, playbook_ref: str = "allianz-auto-whatsapp@v1", sub: str = "guincho"):
    s = DS.new_dispatch_session(case_id="c-conferencia", company_id="co1",
                                playbook_ref=playbook_ref, subservice=sub,
                                slots=dict(SLOTS if slots is None else slots))
    return DS.start_dispatch(s)


def _saidas(session) -> list:
    """O que o motor MANDOU, sem a mensagem de abertura do `start_dispatch`.

    A abertura é sempre a saída de índice 0 e não decide nada; deixá-la aqui
    faria toda comparação carregar um 'Olá' que não é objeto de teste nenhum.
    """
    todas = [t for t in (session.get("transcript") or []) if t.get("direction") == "out"]
    return [t.get("text") for t in todas if t.get("step") is not None]


def _passos(session) -> list:
    todas = [t for t in (session.get("transcript") or []) if t.get("direction") == "out"]
    return [t.get("step") for t in todas if t.get("step") is not None]


# ===========================================================================
# [C1] A MÁSCARA — comparar `JC#-###9` com `JCL9A59` sem mentir para nenhum lado
# ===========================================================================
def teste_a_mascara_nao_e_comparada_como_texto() -> None:
    print("\n[C1] a placa vem mascarada, e mascarado não se compara com ==")
    checar("JC#-###9" != "JCL9A59", "o erro clássico: == entre máscara e placa dá False",
           "reprovaria o veículo CERTO")
    checar(PB.bate_com_mascara("JC#-###9", "JCL9A59") is True, "máscara da placa certa bate")
    checar(PB.bate_com_mascara("JD#-###2", "JCL9A59") is False, "máscara de OUTRO veículo não bate")
    # CONTROLE do próprio [C1]: sem esta linha, um `return None` embutido faria
    # as duas de cima passarem sem comparar nada.
    checar(PB.bate_com_mascara("JC#-##9", "JCL9A59") is None,
           "comprimento diferente = NÃO COMPARÁVEL (nem sim nem não)")
    checar(PB.bate_com_mascara("", "JCL9A59") is None, "máscara vazia não vira veredito")

    # A peça que já existia continua inteira — e passou a USAR a generalização,
    # em vez de ganhar uma cópia ao lado (CLAUDE.md §5).
    menu = "1 - COROLLA, placa JD#-###2\n2 - HILUX SW4, placa JC#-###9"
    checar(PB.pick_option_by_plate(menu, "JCL9A59") == "2", "pick_option_by_plate segue escolhendo a 2")
    checar(PB.pick_option_by_plate(menu, "ZZZ0Z00") == "", "e segue não chutando veículo")
    checar(PB.pick_option_by_plate("1 - X, placa JC#-###9\n2 - Y, placa JC#-###9", "JCL9A59") == "",
           "duas opções que casam continuam devolvendo '' (ambiguidade não é escolha)")


# ===========================================================================
# [C2] LER O RESUMO — etiqueta por etiqueta, nos dois formatos reais
# ===========================================================================
def teste_o_resumo_e_lido_campo_a_campo() -> None:
    print("\n[C2] o resumo vira campos — uma etiqueta por linha e várias na mesma")
    r = PB.ler_resumo(_resumo_allianz(CERTO))
    checar(r.get("placa") == "JC#-###9", "placa lida", str(r.get("placa")))
    checar(str(r.get("servico", "")).startswith("reboque"), "serviço lido", str(r.get("servico")))
    checar(r.get("origem") == CERTO, "origem lida", str(r.get("origem")))
    checar(r.get("destino") == DESTINO, "destino lido", str(r.get("destino")))
    # 📊 Sem a fronteira "uma etiqueta termina onde a próxima começa", o serviço
    # engolia o campo seguinte e a conferência deixava de comparar o que leu.
    uma_linha = "*Serviço:* Encanador *Origem:* Rua B, 50 - Centro - Palhoça - SC *Destino:* -"
    r2 = PB.ler_resumo(uma_linha)
    checar(r2.get("servico") == "Encanador", "3 etiquetas na MESMA linha: serviço", str(r2))
    checar(str(r2.get("origem", "")).startswith("Rua B, 50"), "3 etiquetas na MESMA linha: origem", str(r2))


# ===========================================================================
# [C3] O CASO QUE PAGOU O TESTE — e a LINHA DE CONTROLE
# ===========================================================================
def teste_tres_caracteres_no_numero_da_rua_reprovam() -> None:
    print("\n[C3] 1253 no lugar de 1235 — e o controle que dá direito à conclusão")
    pb = PB.get_playbook("allianz-auto-whatsapp@v1")
    mau = PB.conferir_confirmacao(pb, [_resumo_allianz(ERRADO)], SLOTS, "guincho",
                                  parse_address=PB.parse_address_br)
    checar(mau["ok"] is False, "resumo com 1253 REPROVA", str(mau["divergencias"]))
    checar(any(d["campo"] == "origem_numero" for d in mau["divergencias"]),
           "e diz exatamente qual campo divergiu", str(mau["divergencias"]))

    # 🔴 LINHA DE CONTROLE — a MESMA chamada, com o número certo.
    bom = PB.conferir_confirmacao(pb, [_resumo_allianz(CERTO)], SLOTS, "guincho",
                                  parse_address=PB.parse_address_br)
    checar(bom["ok"] is True, "o MESMO resumo com 1235 APROVA", str(bom["divergencias"]))
    checar(set(bom["conferidos"]) >= {"placa", "servico", "origem", "destino"},
           "e os quatro campos foram de fato comparados", str(bom["conferidos"]))

    # A armadilha do substring, que é como este guarda falharia em silêncio.
    checar("125" in ERRADO and PB.bate_com_mascara("125", "1253") is None,
           "'125' está DENTRO de '1253' — comparar por `in` aprovaria o errado")

    # 🔴 `Cidade/UF` — o formato mais comum do Brasil, e ele REPROVAVA sozinho.
    #
    # 📊 05/08/2026, achado auditando esta própria conferência: `parse_address_br`
    # não quebrava na barra, então "Palhoça/SC" virava a CIDADE inteira e a UF
    # ficava vazia. A conferência comparava "Palhoça/SC" com "Palhoça" e recusava
    # uma confirmação legítima — e os passos que mandam `{local_cidade}` e
    # `{destino_uf}` para a URA carregavam o mesmo estrago desde antes disto aqui
    # existir.
    checar(PB.parse_address_br("R. das Flores, 250, Centro, Palhoça/SC").get("cidade") == "Palhoça",
           "a barra separa cidade de UF", str(PB.parse_address_br("R. das Flores, 250, Centro, Palhoça/SC")))
    checar(PB.parse_address_br("R. das Flores, 250, Centro, Palhoça/SC").get("uf") == "SC",
           "e a UF deixa de ficar vazia")
    casa = {"local_atual": "Rua das Flores, 250 - Centro - Palhoça - SC", "veiculo_placa": "JCL9A59"}
    com_barra = PB.conferir_confirmacao(pb, ["Origem: R. das Flores, 250, Centro, Palhoça/SC\n"
                                             "Podemos confirmar o atendimento?"],
                                        casa, "guincho", parse_address=PB.parse_address_br)
    checar(com_barra["ok"] is True, "e o MESMO endereço escrito com barra confirma",
           str(com_barra["divergencias"]))
    # 🔴 CONTROLE: cidade de verdade diferente continua reprovando. Sem esta
    # linha, afrouxar a cidade até o ponto de não comparar nada passaria igual.
    outra_cidade = PB.conferir_confirmacao(pb, ["Origem: R. das Flores, 250, Centro, Biguaçu/SC\n"
                                                "Podemos confirmar o atendimento?"],
                                           casa, "guincho", parse_address=PB.parse_address_br)
    checar(outra_cidade["ok"] is False
           and any(d["campo"] == "origem_cidade" for d in outra_cidade["divergencias"]),
           "e outra cidade continua reprovando", str(outra_cidade["divergencias"]))


# ===========================================================================
# [C4] AUSÊNCIA NÃO É DIVERGÊNCIA — senão o agente nunca confirma nada
# ===========================================================================
def teste_campo_ausente_nao_impede_a_confirmacao() -> None:
    print("\n[C4] o resumo é quase sempre parcial — e parcial confirma")
    pb = PB.get_playbook("allianz-auto-whatsapp@v1")
    so_servico = "*Serviço:* reboque\nPodemos confirmar o atendimento?\n*1 -* Sim\n*2 -* Não"
    v = PB.conferir_confirmacao(pb, [so_servico], SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(v["ok"] is True, "resumo só com o serviço confirma", str(v))
    checar(v["conferidos"] == ["servico"], "e conferiu só o que apareceu", str(v["conferidos"]))

    # 📊 A tela de não-retorno da família HDI/Yelum não tem resumo NENHUM:
    # responder "Agora" abre o serviço na hora. Exigir campos aqui travaria o
    # corredor inteiro numa tela onde não há nada a conferir.
    pbh = PB.get_playbook("hdi-auto-whatsapp@v1")
    checar(PB.detect_finalize_anchor(pbh, TELA_YELUM) is not None,
           "'agora ou prefere agendar' É ponto de não-retorno")
    vy = PB.conferir_confirmacao(pbh, [TELA_YELUM], SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(vy["ok"] is True and vy["motivo"] == "nada_a_conferir",
           "e ela confirma, com o motivo escrito", str(vy))

    # O limite deste desenho, MEDIDO em vez de escondido: um resumo com etiquetas
    # que não conhecemos confirma — mas se declara `resumo_nao_lido`, e é esse
    # rótulo que vira lista de trabalho de quem escreve o corredor.
    estranho = ("Ficha do chamado\nBem móvel: HILUX\nPonto de saída: Rua X, 9\n"
                "Ponto de entrega: Rua Y, 8\nPosso confirmar?")
    ve = PB.conferir_confirmacao(pb, [estranho], SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(ve["ok"] is True and ve["motivo"] == "resumo_nao_lido",
           "resumo ilegível confirma, mas grita o próprio nome", str(ve))


# ===========================================================================
# [C5] O "SIM" É O DA TELA — não uma lista fixa de palavras
# ===========================================================================
def teste_o_sim_sai_das_opcoes_da_propria_tela() -> None:
    print("\n[C5] afirmativa é o que ESTA tela aceita como sim")
    tela = _resumo_allianz(CERTO)
    # 📊 Os quatro rascunhos que `guard_human_phase_reply` aprovou sobre o resumo
    # ERRADO — aqui eles são reconhecidos como o que são: quatro "sim".
    for draft in ("1", "Sim", "Sim, pode confirmar", "Confirmo, está correto"):
        checar(PB.e_afirmativa(draft, tela) is True, f"afirmativa reconhecida: {draft!r}")
    for draft in ("2", "0", "Não, desejo reiniciar", "Sair"):
        checar(PB.e_afirmativa(draft, tela) is False, f"negativa reconhecida: {draft!r}")
    checar(PB.e_afirmativa("Confirmar solicitação", DECISAO_AZUL) is True,
           "lista da Azul: o rótulo afirmativo")
    checar(PB.e_afirmativa("Mudar localização atual", DECISAO_AZUL) is False,
           "lista da Azul: corrigir NÃO é confirmar")
    checar(PB.e_afirmativa("Sair e não agendar", DECISAO_AZUL) is False, "e sair não é confirmar")
    # "Agora" só quer dizer sim porque a TELA diz que quer.
    checar(PB.e_afirmativa("Agora", TELA_YELUM) is True, "Yelum: 'Agora' é o sim")
    checar(PB.e_afirmativa("Agendar", TELA_YELUM) is False, "Yelum: 'Agendar' não é o sim")


# ===========================================================================
# [C6] AS OUTRAS TRÊS DIVERGÊNCIAS — serviço, placa e destino inventado
# ===========================================================================
def teste_os_outros_tres_campos_tambem_reprovam() -> None:
    print("\n[C6] placa de outro carro, serviço trocado, destino que ninguém pediu")
    pb = PB.get_playbook("allianz-auto-whatsapp@v1")
    outro = _resumo_allianz(CERTO).replace("JC#-###9", "JD#-###2")
    v = PB.conferir_confirmacao(pb, [outro], SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(v["ok"] is False and any(d["campo"] == "placa" for d in v["divergencias"]),
           "placa de OUTRO veículo da apólice reprova", str(v["divergencias"]))

    troca = _resumo_allianz(CERTO, servico="troca de pneu")
    v2 = PB.conferir_confirmacao(pb, [troca], SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(v2["ok"] is False and any(d["campo"] == "servico" for d in v2["divergencias"]),
           "o segurado pediu guincho e o resumo diz pneu → reprova", str(v2["divergencias"]))

    sem_destino = {k: v for k, v in SLOTS.items() if k != "local_destino"}
    v3 = PB.conferir_confirmacao(pb, [_resumo_allianz(CERTO)], sem_destino, "bateria",
                                 parse_address=PB.parse_address_br)
    checar(v3["ok"] is False and any(d["campo"] == "destino_inexistente" for d in v3["divergencias"]),
           "caso sem destino + resumo com destino → reprova", str(v3["divergencias"]))
    # 🔴 CONTROLE do [C6]: o mesmo caso sem destino, com um resumo sem destino.
    v4 = PB.conferir_confirmacao(pb, ["*Serviço:* recarga de bateria\nPodemos confirmar o atendimento?"],
                                 sem_destino, "bateria", parse_address=PB.parse_address_br)
    checar(v4["ok"] is True, "e sem destino nos dois lados, confirma", str(v4))


# ===========================================================================
# [C7] A JANELA — na Azul o resumo e a pergunta são mensagens diferentes
# ===========================================================================
def teste_o_resumo_da_azul_vem_uma_mensagem_antes() -> None:
    print("\n[C7] o resumo que se confere não está na mensagem que pergunta")
    pb = PB.get_playbook("azul-auto-whatsapp@v1")
    checar(PB.detect_finalize_anchor(pb, RESUMO_AZUL) is None,
           "📊 o RESUMO da Azul não casa NENHUMA finalize_anchor")
    checar(PB.detect_finalize_anchor(pb, DECISAO_AZUL) is not None,
           "📊 quem casa é a mensagem SEGUINTE, que não tem os dados")
    so_a_pergunta = PB.conferir_confirmacao(pb, [DECISAO_AZUL], SLOTS, "guincho",
                                            parse_address=PB.parse_address_br)
    checar(so_a_pergunta["conferidos"] == [],
           "olhar só a pergunta não confere nada — é o buraco", str(so_a_pergunta))
    com_janela = PB.conferir_confirmacao(pb, [RESUMO_AZUL, DECISAO_AZUL], SLOTS, "guincho",
                                         parse_address=PB.parse_address_br)
    checar(com_janela["ok"] is False, "com a janela de 2 telas, o 1253 da Azul reprova",
           str(com_janela["divergencias"]))
    # 🔴 CONTROLE: a mesma janela com o endereço certo.
    ok_azul = PB.conferir_confirmacao(pb, [RESUMO_AZUL.replace(ERRADO, CERTO), DECISAO_AZUL],
                                      SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(ok_azul["ok"] is True, "e com o endereço certo, confirma", str(ok_azul["divergencias"]))


# ===========================================================================
# [C8] QUANDO REPROVA, O AGENTE CORRIGE — não chama humano
# ===========================================================================
def teste_a_recusa_vira_correcao_e_nao_handoff() -> None:
    print("\n[C8] reprovar não é parar: a própria tela costuma oferecer o conserto")
    div = [{"campo": "origem_numero", "resumo": "1253", "caso": "1235"}]
    pela_tela = PB.resposta_de_correcao(div, DECISAO_AZUL, SLOTS)
    checar(pela_tela["tipo"] == "opcao" and "localiza" in pela_tela["reply"].lower(),
           "Azul: responde 'Mudar localização atual' — a opção da própria tela", str(pela_tela))

    por_texto = PB.resposta_de_correcao(div, _resumo_allianz(ERRADO), SLOTS)
    checar(por_texto["tipo"] == "texto" and "1235" in por_texto["reply"],
           "Allianz: sem opção de endereço, diz o valor CERTO do caso", str(por_texto))
    # E a correção tem de sobreviver ao guard que já existe: o número dela sai
    # dos slots, então não é "número inventado".
    sessao = {"slots": dict(SLOTS), "captured": {}}
    v = DS.guard_human_phase_reply(por_texto["reply"], sessao)
    checar(v["ok"] is True, "a correção passa no guard de dígitos que já existe", str(v))
    # 🔴 CONTROLE: um número que NÃO é do caso continua sendo barrado.
    v2 = DS.guard_human_phase_reply("Antes de confirmar: o endereço de origem é Rua X, 99887.", sessao)
    checar(v2["ok"] is False and v2["reason"] == "invented_number",
           "e um número inventado continua barrado", str(v2))


# ===========================================================================
# [C9] A TRAVA DA CONFIRMAÇÃO ÚNICA — dois "sim" são dois prestadores
# ===========================================================================
def teste_ninguem_confirma_duas_vezes_o_mesmo_pedido() -> None:
    print("\n[C9] confirmar duas vezes manda dois guinchos para o mesmo endereço")
    pb = PB.get_playbook("allianz-auto-whatsapp@v1")
    v = PB.conferir_confirmacao(pb, [_resumo_allianz(CERTO)], SLOTS, "guincho",
                                parse_address=PB.parse_address_br)
    d1 = PB.digest_da_conferencia(v)
    sessao: dict = {}
    checar(PB.pode_confirmar_de_novo(sessao, d1)["ok"] == "1", "a primeira confirmação passa")
    PB.registrar_confirmacao(sessao, d1, "podemos confirmar o atendimento", "2026-08-05T12:00:00Z")

    repetida = PB.pode_confirmar_de_novo(sessao, d1)
    checar(repetida["ok"] == "" and repetida["acao"] == "perguntar_status",
           "a MESMA tela de novo não vira segundo 'sim' — vira PERGUNTA de status", str(repetida))

    # Etapa nova (a seguradora mudou o destino depois da nossa correção): outro
    # digest, e aí confirmar é o certo.
    novo_destino = "Rua Nova, 10 - Centro - Palhoça - SC"
    outra = PB.conferir_confirmacao(pb, [_resumo_allianz(CERTO).replace(DESTINO, novo_destino)],
                                    {**SLOTS, "local_destino": novo_destino},
                                    "guincho", parse_address=PB.parse_address_br)
    d2 = PB.digest_da_conferencia(outra)
    checar(d2 != d1, "resumo diferente = digest diferente", f"{d1} / {d2}")
    checar(PB.pode_confirmar_de_novo(sessao, d2)["ok"] == "1", "etapa nova confirma")
    PB.registrar_confirmacao(sessao, d2, "podemos confirmar o atendimento", "2026-08-05T12:05:00Z")

    terceira = PB.pode_confirmar_de_novo(sessao, "digest-3")
    checar(terceira["ok"] == "" and terceira["motivo"] == "teto_de_confirmacoes",
           "e existe teto: a terceira para, com motivo escrito", str(terceira))

    # O DIGEST É DOS CAMPOS LIDOS, NÃO DOS BYTES DA MENSAGEM.
    # A URA reescreve espaço, emoji e negrito entre reenvios; um hash de bytes
    # acharia que são dois pedidos diferentes e mandaria o segundo guincho.
    remexido = (_resumo_allianz(CERTO).replace("*", "").replace("\n", "  \n")
                + "\n\n✅ tudo certo?")
    v_remexido = PB.conferir_confirmacao(pb, [remexido], SLOTS, "guincho",
                                         parse_address=PB.parse_address_br)
    checar(PB.digest_da_conferencia(v_remexido) == d1,
           "mesma tela reescrita = MESMO digest", f"{PB.digest_da_conferencia(v_remexido)} / {d1}")

    # 🔴 E A TELA SEM RESUMO NENHUM PRECISA DE IDENTIDADE PRÓPRIA.
    # 📊 Achado em 05/08/2026 auditando este próprio bloco: sem a âncora no
    # digest, TODA tela de confirmação sem resumo legível colidia num único
    # `"vazio"`. Na família HDI/Yelum são duas telas diferentes de não-retorno,
    # e a segunda era recusada como duplicata da primeira — o corredor travava
    # numa confirmação legítima.
    pbh = PB.get_playbook("hdi-auto-whatsapp@v1")
    sem_resumo_a = PB.conferir_confirmacao(pbh, [TELA_YELUM], SLOTS, "guincho",
                                           parse_address=PB.parse_address_br)
    sem_resumo_b = PB.conferir_confirmacao(pbh, ["Posso confirmar?\nBotão 1: Sim\nBotão 2: Não"],
                                           SLOTS, "guincho", parse_address=PB.parse_address_br)
    checar(sem_resumo_a["resumo"] == {} and sem_resumo_b["resumo"] == {},
           "as duas telas não têm resumo nenhum para ler", str(sem_resumo_a["resumo"]))
    da = PB.digest_da_conferencia(sem_resumo_a, "atendimento agora ou prefere")
    db = PB.digest_da_conferencia(sem_resumo_b, "posso confirmar")
    checar(da != db, "telas SEM resumo têm digests diferentes — a âncora as separa", f"{da} / {db}")
    # 🔴 CONTROLE: a MESMA tela sem resumo continua sendo o MESMO pedido.
    checar(PB.digest_da_conferencia(sem_resumo_a, "atendimento agora ou prefere") == da,
           "e a mesma tela sem resumo continua colidindo consigo mesma")


# ===========================================================================
# [C10] O MOTOR DE VERDADE — o caso medido, ponta a ponta, com o controle
# ===========================================================================
def teste_o_motor_nao_confirma_mais_o_endereco_errado() -> None:
    print("\n[C10] 📊 o motor respondia '1' para o 1253 — agora ele corrige")
    errado = _sessao()
    errado = DS.handle_insurer_message(errado, _resumo_allianz(ERRADO))
    saidas = _saidas(errado)
    checar("1" not in saidas, "o motor NÃO responde mais '1' ao resumo errado", str(saidas))
    checar(any("1235" in str(s) for s in saidas),
           "ele responde com o endereço DO CASO", str(saidas))
    checar(errado.get("state") in ("ura", "human_phase"),
           "e não vira handoff: corrigir é trabalho do agente", str(errado.get("state")))
    checar(errado["conferencia"]["ok"] is False
           and any(d["campo"] == "origem_numero" for d in errado["conferencia"]["divergencias"]),
           "o veredito fica na sessão, com o campo nomeado", str(errado.get("conferencia")))

    # 🔴 LINHA DE CONTROLE — o MESMO motor, a MESMA tela, o endereço certo.
    # Sem ela, um guarda que recusasse TUDO passaria neste teste.
    bom = _sessao()
    bom = DS.handle_insurer_message(bom, _resumo_allianz(CERTO))
    checar(_saidas(bom) == ["1"], "com o endereço certo, o motor confirma — '1'", str(_saidas(bom)))
    checar(_passos(bom) == ["confirmar_atendimento"],
           "📊 e quem responde é o PASSO determinístico, não a LLM", str(_passos(bom)))
    checar(bom["conferencia"]["ok"] is True
           and set(bom["conferencia"]["conferidos"]) >= {"placa", "servico", "origem", "destino"},
           "com os quatro campos conferidos", str(bom.get("conferencia")))


# ===========================================================================
# [C11] O MESMO RESUMO DUAS VEZES — e a trava sobrevive ao restart
# ===========================================================================
def teste_o_mesmo_resumo_duas_vezes_nao_vira_dois_guinchos() -> None:
    print("\n[C11] a URA reenviou a mesma tela — isso não é um segundo pedido")
    # 📊 ATUALIZADO (CLAUDE.md §9.3). Este check afirmava, em 05/08/2026, que o
    # motor respondia "1" DUAS vezes para o MESMO resumo — `_would_loop` só para
    # na TERCEIRA, e a terceira já é tarde: dois "sim" são dois prestadores.
    # Era verdade até a trava existir. A lição não morreu, MIGROU: o que se
    # testa agora é que o segundo "1" não sai.
    s = _sessao()
    s = DS.handle_insurer_message(s, _resumo_allianz(CERTO))
    s = DS.handle_insurer_message(s, _resumo_allianz(CERTO))
    saidas = _saidas(s)
    checar(saidas.count("1") == 1, "um resumo, UM '1' — nunca dois", str(saidas))
    checar("número do atendimento" in str(saidas[-1]),
           "a segunda vez PERGUNTA o status em vez de confirmar de novo", str(saidas))

    # ⚠️ A trava tem de atravessar o retrato durável. `snapshot_duravel` corta
    # toda chave que case `_CHAVES_PROIBIDAS` — se ela se chamasse
    # `confirm_token`, sumiria no restart, e uma trava que só mora no Redis não
    # é trava.
    retrato = DS.snapshot_duravel(s)
    checar(bool(retrato.get("confirmacoes")), "a trava sobrevive ao snapshot durável",
           str(sorted(retrato.keys())))
    checar(not any(p in "confirmacoes" for p in DS._CHAVES_PROIBIDAS),
           "e o nome da chave não casa nenhuma proibida")
    # 🔴 CONTROLE do próprio guarda de nome: um nome PROIBIDO some mesmo. Sem
    # esta linha, o check de cima passaria mesmo que `snapshot_duravel` não
    # cortasse nada.
    checar("confirm_token" not in DS.snapshot_duravel({**s, "confirm_token": "x"}),
           "e um nome com 'token' seria de fato cortado — o guarda consegue cortar")

    # E a sessão RESTAURADA continua travada: é o caso do restart de verdade.
    voltou = DS.sessao_restaurada(retrato, motivo="teste")
    voltou = DS.handle_insurer_message(voltou, _resumo_allianz(CERTO))
    checar(_saidas(voltou).count("1") == 1, "depois do restart, ainda UM '1'", str(_saidas(voltou)))

    # 📊 E A PERGUNTA DE STATUS TAMBÉM TEM DE PARAR. Achado auditando este bloco
    # em 05/08/2026: com a URA reenviando a mesma tela cinco vezes, saíam CINCO
    # perguntas idênticas — o corredor trocava o loop de "sim" por um loop de
    # pergunta e não chamava ninguém.
    teimosa = _sessao()
    for _ in range(5):
        teimosa = DS.handle_insurer_message(teimosa, _resumo_allianz(CERTO))
    checar(_saidas(teimosa).count("1") == 1, "ainda UM '1' depois de cinco reenvios",
           str(_saidas(teimosa)))
    checar(_passos(teimosa).count("confirmacao_repetida") <= 2,
           "e no máximo DUAS perguntas de status", str(_passos(teimosa)))
    checar(teimosa.get("state") == "needs_human",
           "a URA que não responde vira gente, e não um loop educado", str(teimosa.get("state")))


# ===========================================================================
# [C12] REGISTRAR NÃO É EMITIR — a trava que não protegeu nada não pode travar
# ===========================================================================
def teste_confirmacao_que_nunca_saiu_nao_bloqueia_a_proxima() -> None:
    print("\n[C12] o registro vem antes do envio — e o envio pode não acontecer")
    # A trava é gravada ANTES de emitir de propósito: ela tem de valer no
    # instante em que o processo cai. O preço disso é este caso — o fluxo pode
    # terminar sem emitir nada (slot faltando, LLM que preferiu perguntar). Uma
    # trava desse registro bloquearia o "sim" LEGÍTIMO da tela seguinte.
    tela = _resumo_allianz(CERTO)
    fantasma = {"transcript": [{"direction": "in", "text": tela}],
                "confirmacoes": [{"digest": "d1", "saida_em": 1, "tela": tela[-400:]}]}
    checar(DS._confirmacoes_que_de_fato_sairam(fantasma) == [],
           "registro sem nenhum 'sim' emitido é descartado", str(fantasma))

    # 🔴 CONTROLE: o registro cujo "sim" SAIU continua de pé. Sem esta linha, um
    # `return []` cru passaria no check de cima — e a trava inteira sumiria.
    real = {"transcript": [{"direction": "in", "text": tela},
                           {"direction": "out", "text": "1", "step": "confirmar_atendimento"}],
            "confirmacoes": [{"digest": "d1", "saida_em": 1, "tela": tela[-400:]}]}
    checar(len(DS._confirmacoes_que_de_fato_sairam(real)) == 1,
           "e o registro cujo '1' saiu de verdade CONTINUA travando", str(real))

    # A NOSSA PRÓPRIA CORREÇÃO NÃO É UMA CONFIRMAÇÃO — e o que separa as duas é
    # o PASSO, não o texto.
    correcao = "Antes de confirmar: o endereço de origem é Rua X, 1235."
    corrigiu = {"transcript": [{"direction": "in", "text": tela},
                               {"direction": "out", "text": correcao, "step": "correcao:origem"}],
                "confirmacoes": [{"digest": "d1", "saida_em": 1, "tela": DECISAO_AZUL[-400:]}]}
    checar(DS._confirmacoes_que_de_fato_sairam(corrigiu) == [],
           "uma correção não é uma confirmação", str(corrigiu))
    # O LIMITE, MEDIDO EM VEZ DE ESCONDIDO: pelo texto sozinho, `e_afirmativa`
    # LERIA a correção como afirmativa — ela casa a palavra "confirmar". É a
    # falha-para-o-lado-do-sim, e ela é de propósito: custa uma pergunta de
    # status a mais, nunca um segundo guincho. A precisão vem de
    # `_PASSOS_QUE_NAO_CONFIRMAM`, que só pode existir porque são passos NOSSOS.
    checar(PB.e_afirmativa(correcao, DECISAO_AZUL) is True,
           "📊 pelo texto sozinho ela seria lida como 'sim' — por isso o passo entra na conta")
    # 🔴 CONTROLE: o MESMO texto, com um passo que NÃO está na lista, mantém a
    # trava. É o que prova que a lista discrimina de verdade — e não que o
    # descarte de cima veio do texto ter dado negativo por acaso.
    outro_passo = {"transcript": [dict(t) for t in corrigiu["transcript"]],
                   "confirmacoes": [{"digest": "d1", "saida_em": 1, "tela": DECISAO_AZUL[-400:]}]}
    outro_passo["transcript"][1]["step"] = "confirmar_solicitacao"
    checar(len(DS._confirmacoes_que_de_fato_sairam(outro_passo)) == 1,
           "com um passo fora da lista, a trava fica de pé", str(outro_passo["confirmacoes"]))


# ===========================================================================
# [C13] A ESCADA DA CORREÇÃO — e o teto que a fecha
# ===========================================================================
def teste_a_correcao_tem_teto_e_termina_em_gente() -> None:
    print("\n[C13] corrigir para sempre é uma URA presa numa tela até o timeout")
    s = _sessao()
    for _ in range(PB.MAX_CORRECOES_POR_CAMPO):
        s = DS.handle_insurer_message(s, _resumo_allianz(ERRADO))
    checar(s.get("state") in ("ura", "human_phase"),
           f"até {PB.MAX_CORRECOES_POR_CAMPO} correções, o agente segue sozinho", str(s.get("state")))
    s = DS.handle_insurer_message(s, _resumo_allianz(ERRADO))
    checar(s.get("state") == "needs_human" and str(s.get("reason", "")).startswith("conferencia_divergente"),
           "esgotado o teto, aí sim vira gente — com o motivo escrito", str(s.get("reason")))
    # O dossiê que já existia continua servindo: quem assume lê o caso inteiro.
    dossie = DS.build_handoff_dossier(s, s.get("reason") or "")
    checar("1235" in dossie and "conferencia_divergente" in dossie,
           "e o dossiê leva o endereço CERTO e o motivo", dossie[:200])

    # 🔴 CONTROLE: a Azul, cuja tela OFERECE o conserto, responde a OPÇÃO —
    # o degrau 1 da escada, e não o texto do degrau 2.
    az = _sessao(playbook_ref="azul-auto-whatsapp@v1")
    az = DS.handle_insurer_message(az, RESUMO_AZUL)
    az = DS.handle_insurer_message(az, DECISAO_AZUL)
    checar(_saidas(az)[-1] == "Mudar localização atual",
           "Azul: o conserto é a opção da própria tela", str(_saidas(az)))
    checar("Confirmar solicitação" not in _saidas(az),
           "e o 'Confirmar solicitação' NÃO saiu", str(_saidas(az)))


# ===========================================================================
# [C14] O GUARDA TEM DE RECONHECER O CONSERTO QUE ELE MESMO PEDIU
# ===========================================================================
def teste_o_resumo_corrigido_pela_ura_e_confirmado() -> None:
    print("\n[C14] a URA arrumou o endereço — reprovar de novo seria só teimosia")
    # 📊 ESTE CASO É O DEFEITO QUE A AUSÊNCIA DE CONTROLE ESCONDEU (05/08/2026).
    # O [C13] só mandava resumos ERRADOS, então nunca percebeu: a janela lia da
    # mensagem mais ANTIGA para a mais nova e o resumo velho sombreava o novo.
    # O agente corrigia, a URA obedecia, e o guarda reprovava assim mesmo — até
    # estourar o teto e chamar um humano para um resumo que já estava certo.
    #
    # Um guarda que não reconhece o conserto que pediu não guarda: ele só recusa.
    s = _sessao()
    s = DS.handle_insurer_message(s, _resumo_allianz(ERRADO))
    checar(_passos(s) == ["correcao:origem"], "primeiro a correção sai", str(_passos(s)))
    s = DS.handle_insurer_message(s, _resumo_allianz(CERTO))
    checar(_saidas(s)[-1] == "1", "e o resumo CORRIGIDO é confirmado", str(_saidas(s)))
    checar(s["conferencia"]["ok"] is True, "o veredito da segunda passagem aprova",
           str(s.get("conferencia")))

    # 🔴 CONTROLE: o mesmo par, na ordem inversa. Se a URA mandar o resumo certo
    # e DEPOIS um errado, quem vale é o ERRADO — é o último que ela disse, e é
    # ele que está prestes a virar serviço.
    r = _sessao()
    r = DS.handle_insurer_message(r, _resumo_allianz(CERTO))
    r = DS.handle_insurer_message(r, _resumo_allianz(ERRADO))
    checar(_saidas(r)[-1] != "1", "resumo certo seguido de errado NÃO confirma o errado",
           str(_saidas(r)))
    checar(any("1235" in str(x) for x in _saidas(r)[-1:]),
           "ele corrige com o endereço do caso", str(_saidas(r)))


def main() -> int:
    print("=" * 74)
    print("A CONFIRMACAO CONFERE ANTES DE ABRIR — E CONSEGUE REPROVAR")
    print("=" * 74)
    for t in (teste_a_mascara_nao_e_comparada_como_texto,
              teste_o_resumo_e_lido_campo_a_campo,
              teste_tres_caracteres_no_numero_da_rua_reprovam,
              teste_campo_ausente_nao_impede_a_confirmacao,
              teste_o_sim_sai_das_opcoes_da_propria_tela,
              teste_os_outros_tres_campos_tambem_reprovam,
              teste_o_resumo_da_azul_vem_uma_mensagem_antes,
              teste_a_recusa_vira_correcao_e_nao_handoff,
              teste_ninguem_confirma_duas_vezes_o_mesmo_pedido,
              teste_o_motor_nao_confirma_mais_o_endereco_errado,
              teste_o_mesmo_resumo_duas_vezes_nao_vira_dois_guinchos,
              teste_confirmacao_que_nunca_saiu_nao_bloqueia_a_proxima,
              teste_a_correcao_tem_teto_e_termina_em_gente,
              teste_o_resumo_corrigido_pela_ura_e_confirmado):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X     {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O 'SIM' PASSOU A SER UMA VERIFICACAO, E ELA CONSEGUE DIZER NAO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
