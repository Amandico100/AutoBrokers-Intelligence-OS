"""As perguntas que o portal de vidros VAI fazer — sabidas ANTES de entrar nele.

O defeito que esta peça desfaz
------------------------------
📊 39 acionamentos de `vidros_lanternas` (06 a 15/07/2026, Supabase
`dcajcvlzcjbmyapmklil`): **33 pararam em `needs_human`, 5 falharam, 1 terminou
"done" sem protocolo. Zero protocolos.** 📊 Das 33 paradas, 7 foram por um dado
que **já estava disponível** — na InfoCap, ou perguntável em uma frase.

O erro não é falta de inteligência. É **ordem**:

    ANTES   abre o portal → descobre o que falta → para → chama um humano
    AGORA   descobre o que falta → pergunta → abre o portal → preenche

Quando o sistema descobre a lacuna *dentro* do portal, o segurado já saiu do
WhatsApp, o robô está parado numa tela com um dropdown aberto, e alguém precisa
reabrir tudo. E reabrir é caro de um jeito que não se desfaz: 📊 o `Nº do
atendimento` nasce no passo 7, **no topo da tela, antes da escolha da loja**
(`docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §7) — repetir o fluxo cria um
SEGUNDO atendimento na seguradora, não corrige o primeiro.

O que este módulo é, e o que não é
----------------------------------
É o **catálogo medido** do que o portal pergunta, mais uma função pura que
responde, antes de qualquer navegador abrir: *quais perguntas ainda faltam para
este acionamento não travar?*

Não é um motor de coleta. O motor de "o que ainda falta" do **corredor de
WhatsApp** já existe e continua sendo dele:
`corridor_playbooks.missing_slots_for_subservice`. Aquele lê slots de playbook
de URA; este lê o mapa de um PORTAL web. São duas telas diferentes, com dois
conjuntos de campos medidos em fontes diferentes — e nenhum dos dois responde
pelo outro. O que **não** se duplica aqui é o vocabulário de peça: ele é
importado (ver `identidade_peca` abaixo).

As quatro decisões de desenho
-----------------------------
**1. A pergunta nasce da PEÇA.** As específicas do passo 6 (80%) dependem do que
quebrou: película/dianteira-traseira/lado são de vidro lateral; posição e
tamanho do trincado são de para-brisa. Perguntar de película a quem quebrou o
retrovisor é ruído. E se a peça ainda não é conhecida, **ela é a primeira
pergunta** — as outras nem existem ainda, porque não há como saber quais são.

**2. "Não perguntar" é diferente de "não sei".** A versão do veículo e o CEP
saem da InfoCap e **nunca** viram pergunta ao segurado (§8.3 do mapa: *"Perguntar
ao segurado o que está na apólice"* é proibido). Se a InfoCap não trouxe, isso é
uma **lacuna do PROVEDOR** — de quem opera a integração, não de quem quebrou o
vidro. Por isso `Pergunta.de_quem`.

**3. Peça não mapeada não pode virar bloqueio.** 📊 As específicas de retrovisor,
farol, lanterna, vigia e teto **não foram medidas** (§7 do mapa). O honesto é
declarar isso — `especificas_mapeadas()` devolve False e a mensagem ao agente diz
com todas as letras que não estão mapeadas — e deixar o caminho adaptativo, que
lê a tela real, resolver. Inventar pergunta seria pior que não perguntar:
mandaria o segurado responder algo que o portal não vai usar.

**4. "Não sabe" é veneno, mas existe.** 📊 Toda pergunta do 80% oferece "Não
sabe", e ela destrava a tela degradando o serviço (§8.2 do mapa). A diferença
que este módulo modela: responder "não sabe" **por preguiça do robô** é proibido;
responder "não sabe" **porque o segurado realmente não sabe** é legítimo — mas só
*depois de perguntada*. Por isso "não sabe" nunca aparece em `opcoes` (não é uma
opção que se ofereça) e só encerra a pergunta em `respondida()` quando
`aceita_nao_sabe` é True. Numa pergunta que o portal não deixa pular — a peça —
"não sabe" **não** encerra nada, e o caso continua faltando.

E a descrição não é pergunta
----------------------------
📊 O passo 4 exige **mínimo de 30 caracteres** em `descrever-acontecimento-textarea`.
Isso é burocracia do portal, não informação nova: pedir a um segurado assustado
que "escreva mais" é exatamente o tipo de pergunta que o produto existe para não
fazer. Então a descrição é **composta** do que já se sabe (peça + relato + data +
local), nunca perguntada — ver `compor_descricao`, que prova aritmeticamente o
mínimo de 30.

💭 Os textos das perguntas são copy ilustrativa (linguagem humana para WhatsApp),
não citáveis como medição. 📊 O que é medido é a *existência* de cada pergunta e
as *opções* que o portal oferece — fonte: captura tela a tela do Founder em
06/07/2026 (Yelum e Tokio), consolidada em
`docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`, que é a autoridade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# O VOCABULÁRIO DE PEÇA É UM SÓ — e ele já existe.
#
# `identidade_peca` é quem decide se "vidro da porta" e "VIDRO PARABRISA - CARGA"
# são a mesma coisa (não são). Escrever aqui uma segunda tabela de peças seria o
# motor paralelo do CLAUDE.md §5, e o preço dele está medido: 📊 três
# acionamentos de produção casaram 'vidro da porta' com 'VIDRO PARABRISA - CARGA'
# quando um token genérico bastava para decidir.
#
# O precedente é do próprio `portal_worker/adaptive.py`, que importa
# `explicar_match` de lá "em vez de manter um segundo, escrito em JS, que decidia
# diferente do que os testes provavam".
#
# 📊 O import atravessa pacotes e isso foi conferido, não suposto:
# `backend/Dockerfile` faz `COPY . .` com `WORKDIR /app`, então `portal_worker`
# viaja na imagem do backend e é importável de `/app`. E o único ponto que puxa
# esta cadeia (`graph.py` → `portal_tool` → `portal_params`) está dentro de um
# `try/except` que só registra warning: uma falha aqui tira a tool do ar, nunca
# o produto (CLAUDE.md §9.1).
from portal_worker.journeys.vidros_lanternas import identidade_peca

# UMA definição de "vazio disfarçado de resposta". `_tem_valor` já recusa
# `"não informado"` — o preenchimento que o modelo inventa para não deixar campo
# em branco. Duplicar a regra aqui faria o mesmo texto ser resposta de um lado e
# ausência do outro.
from app.services.attendance_ficha import _tem_valor

# --------------------------------------------------------------------------
# De quem é a resposta
# --------------------------------------------------------------------------
DO_SEGURADO = "segurado"    # pergunta-se, em linguagem humana, no WhatsApp
DO_PROVEDOR = "provedor"    # está (ou deveria estar) na InfoCap — NUNCA se pergunta

# --------------------------------------------------------------------------
# Para ONDE a resposta vai — SPEC-EXTRA-001.10 P1-3
# --------------------------------------------------------------------------
# 🔴 O achado que reorganiza a coleta: a maior parte do que a atendente humana
# pergunta **não é o questionário do portal**. É o que decide QUAL LINHA do
# catálogo da apólice (`GET /apolices/itens-cobertos`) vai no `CodigoItemCoberto`
# do PATCH. Capa pintada ou fosca, com pisca ou sem, bipartida da tampa ou da
# carroceria: cada resposta é um ITEM diferente, não uma opção de questionário.
#
# Misturar os dois destinos custa caro nos dois sentidos: mandar ao questionário
# uma resposta que o portal nunca pediu faz o robô parar numa tela; e deixar de
# usar no catálogo uma resposta que o segurado já deu manda buscar a peça errada.
DESTINO_CATALOGO = "catalogo"        # ajuda a ESCOLHER o item coberto (PATCH)
DESTINO_QUESTIONARIO = "questionario"  # é resposta do questionário do portal
# ⚠️ O terceiro destino existe porque um nome que mente reinfecta todo leitor
# seguinte (CLAUDE.md §12.1): a resposta do reparo **não** entra em
# `PerguntasResposta` nem no `CodigoItemCoberto` — ela vira
# `PUT /atendimentos/alterar-reparo {"Reparo": bool}`, uma chamada só dela.
DESTINO_REPARO = "reparo"
# 🔴 SPEC-EXTRA-001.10.1 C2 — o quarto destino: a PREFERÊNCIA do segurado.
# A resposta não escolhe peça, não responde questionário e não decide reparo:
# ela diz ao robô o que fazer quando o portal, DEPOIS do número, abrir a agenda
# (📊 `POST /agendamentos` concluído na captura lateral de 21/09, HAR [048]) ou
# oferecer a opção de vistoria (📊 lataria, `PermiteOpcaoVistoria:true`, HAR
# [089]). Nunca trava: sem ela o portal mostra as opções e o robô CONTINUA
# quando o segurado escolher.
DESTINO_PREFERENCIA = "preferencia"

# O que o segurado responde quando genuinamente não sabe. Só vale depois de a
# pergunta ter sido feita, e só nas perguntas que o portal deixa pular.
NAO_SABE = "nao_sabe"
_SINONIMOS_DE_NAO_SABE = ("nao_sabe", "nao sabe", "não sabe", "nao sei", "não sei",
                          "sei la", "sei lá", "nao lembro", "não lembro")

# 📊 `descrever-acontecimento-textarea`: mín. 30 / máx. 2000 (mapa §4, passo 4).
MINIMO_DA_DESCRICAO = 30
MAXIMO_DA_DESCRICAO = 2000

# --------------------------------------------------------------------------
# Os campos. O nome diz o que ele guarda — um nome que mente reinfecta todo
# leitor seguinte (CLAUDE.md §12.1).
# --------------------------------------------------------------------------
CPF_DO_TITULAR = "cpf_cnpj"
DATA_DO_DANO = "data_dano"
PECA = "peca"
COMO_OCORREU = "como_ocorreu"
ONDE_OCORREU = "onde_ocorreu"
DESCRICAO = "descricao"

PELICULA = "pelicula"
PORTA_DIANTEIRA_OU_TRASEIRA = "porta_dianteira_ou_traseira"
LADO_MOTORISTA_OU_CARONA = "lado_motorista_ou_carona"
POSICAO_DO_TRINCADO = "posicao_do_trincado"
# Guarda "maior"/"menor"/"não sabe" — não um booleano. `trincado_maior_que_10cm`
# mentiria sobre o terceiro valor, que existe e é o mais perigoso dos três.
TAMANHO_DO_TRINCADO = "tamanho_do_trincado"
VERSAO_DO_VEICULO = "versao_do_veiculo"
CEP_DO_SEGURADO = "cep_do_segurado"
# 📊 Passo 7: "Escolha a loja onde deseja realizar o serviço." Guarda a
# PREFERÊNCIA ("domicilio" / "loja"), nunca a loja escolhida — `loja_escolhida`
# mentiria sobre o que o campo pode conter, porque a lista de lojas só existe
# na tela do portal e o segurado nunca a viu.
ONDE_REALIZAR_O_SERVICO = "onde_realizar_o_servico"
# 🔴 SPEC-EXTRA-001.10.1 (D-E001101-05, decisão do Founder): DOMICÍLIO SAI.
# O campo continua existindo porque o caminho DOM (`adaptive.preferencia_do_
# segurado`) o lê — mas ninguém mais PERGUNTA: `build_portal_params` manda
# sempre "loja". A pergunta foi retirada de `_UNIVERSAIS`.
ONDE_REALIZAR_PADRAO = "loja"

# 🔴 SPEC-EXTRA-001.10.1 C2 — as duas preferências coletadas ANTES do portal.
#
# 📊 O token do portal EXPIRA (21/09 22:09 UTC → 401 em 23/09 23:40 UTC). Cada
# resposta que o robô já tem na hora do número é uma continuação a menos que
# depende do token viver até o segurado responder.
PREFERENCIA_AGENDA = "preferencia_agenda"
PREFERENCIA_VISTORIA = "preferencia_vistoria"

# 🔴 SPEC-EXTRA-001.10 P0-5 — O LUGAR, que não é a MODALIDADE.
#
# 📊 `CodigoCidade` é chave obrigatória do `PATCH /atendimentos` nas 4 capturas
# (20/09/2026), e 📊 a cidade é perguntada em **8 de 8 blocos** do .docx da
# atendente — junto com a data, a única presente em todos.
#
# 🔴 E ela NÃO é o CEP da apólice: quem quebra o vidro viajando conserta onde
# está. O CEP do cadastro é o de casa; a cidade do serviço é uma decisão, e só
# o segurado a tem.
#
# ⚠️ Não confundir com `ONDE_REALIZAR_O_SERVICO`, logo acima: aquele é
# MODALIDADE (técnico em casa × levar numa loja); este é LUGAR (qual município
# vira `CodigoCidade`). Responder um não responde o outro, e os dois convivem.
CIDADE_PARA_O_SERVICO = "cidade_para_o_servico"

# 🔴 SPEC-EXTRA-001.10 N-2 (D-E00110-02) — a decisão que o código não conhecia.
# 📊 `POST /questionarios/regras-reparo` → `{ExibirDialogDeReparo: true}` e o
# portal PARA para perguntar se o segurado topa tentar o reparo. Sem a resposta
# coletada antes, a journey para DEPOIS de o protocolo já existir — o lugar mais
# caro possível.
ACEITA_REPARO = "aceita_reparo"

# As específicas que o .docx da atendente cobre e que até aqui não existiam em
# lugar nenhum. Quase todas são de CATÁLOGO (ver DESTINO_CATALOGO).
SENSOR_DE_CHUVA = "sensor_de_chuva"
FAIXA_DEGRADE = "faixa_degrade"
SENSOR_DE_DIRECAO_OU_FAIXA = "sensor_de_direcao_ou_faixa"
CAPA_PINTADA_OU_FOSCA = "capa_pintada_ou_fosca"
RETROVISOR_TEM_PISCA = "retrovisor_tem_pisca"
REGULAGEM_DO_RETROVISOR = "regulagem_do_retrovisor"
CAPA_AINDA_NA_PECA = "capa_ainda_na_peca"
LANTERNA_BIPARTIDA_ONDE = "lanterna_bipartida_onde"
PARA_CHOQUE_DIANTEIRO_OU_TRASEIRO = "para_choque_dianteiro_ou_traseiro"
VIDRO_FIXO_OU_SOBE_DESCE = "vidro_fixo_ou_sobe_desce"
VIGIA_DESEMBACADOR_TERMICO = "vigia_desembacador_termico"
# Guarda a LISTA de peças amassadas do mesmo evento — `peca_lataria` mentiria
# sobre a cardinalidade, e é justamente a cardinalidade que faz a lataria ser um
# caminho próprio (📊 `ServicosMartelinhoLataria` é um array no PATCH).
PECAS_LATARIA = "pecas_lataria"
LATARIA_MESMO_EVENTO = "lataria_mesmo_evento"

# Onde a resposta MORA em `ja_sei`, quando não é na própria chave do campo.
# 📊 A versão sai do campo `Veículo` da InfoCap ("NIVUS COMFORTLINE 1.0 200 TSI
# FLEX AUT") e o CEP do cadastro do cliente — os dois já chegam prontos.
_ONDE_MORA = {
    VERSAO_DO_VEICULO: "veiculo",
    CEP_DO_SEGURADO: "cep",
}


@dataclass(frozen=True)
class Pergunta:
    """Uma pergunta que o portal vai fazer e que ainda não tem resposta.

    `texto` é o que o agente FALA — em português de gente, não em nome de campo.
    `opcoes` são as respostas que o portal aceita (📊 medidas); vazio = texto
    livre. "Não sabe" nunca está em `opcoes`: ela não se oferece, se aceita.
    """

    campo: str
    texto: str
    de_quem: str = DO_SEGURADO
    opcoes: Tuple[str, ...] = ()
    aceita_nao_sabe: bool = False
    porque: str = ""
    # Para onde a resposta vai (SPEC-EXTRA-001.10 P1-3): escolher o ITEM do
    # catálogo, responder o QUESTIONÁRIO, ou decidir o REPARO. O default é o
    # questionário porque era o único destino que existia antes desta SPEC.
    destino: str = DESTINO_QUESTIONARIO
    # 🔴 A pergunta foi VISTA numa tela do portal? `False` = a atendente humana
    # a faz (e por isso ela vale a pena), mas nenhuma captura a exibiu — então a
    # resposta serve para a CONVERSA e para escolher a peça, e **não** se manda
    # ao questionário do portal enquanto não houver captura. Declarar isso é o
    # que impede inventar pergunta (CLAUDE.md §12.1: 📊 × 💭).
    confirmada: bool = True
    # Como a resposta VOLTA para cá. Vazio = o agente já sabe (o campo tem o
    # nome dele no schema da tool). Preenchido = uma linha literal de instrução,
    # para a pergunta que o schema da tool ainda não nomeia. Sem isso a pergunta
    # é feita, o segurado responde, e a resposta morre no caminho de volta — o
    # laço que este repositório já pagou uma vez (`subservico_invalido`).
    como_devolver: str = ""

    @property
    def onde_mora(self) -> str:
        """A chave de `ja_sei` que guarda a resposta desta pergunta."""
        return _ONDE_MORA.get(self.campo, self.campo)


# --------------------------------------------------------------------------
# O catálogo — passo 1, passo 4 e passo 5 do mapa (não dependem da peça)
# --------------------------------------------------------------------------
# Ordem = ordem de conversa, não ordem de tela. O CPF vem primeiro porque é ele
# que destrava a InfoCap, e a InfoCap é que dispensa metade das perguntas. A
# peça vem em seguida porque é dela que nascem as específicas — perguntar
# qualquer específica antes de saber a peça é chutar.
_UNIVERSAIS: Tuple[Pergunta, ...] = (
    Pergunta(
        CPF_DO_TITULAR,
        "Pra eu localizar a apólice, me confirma o CPF do titular do seguro?",
        porque="⚠️ o portal rotula o campo como 'CPF/CNPJ (solicitante)', mas o valor "
               "esperado é o do TITULAR — é assim que a apólice é localizada (mapa §4).",
    ),
    Pergunta(
        PECA,
        "Qual vidro foi? O para-brisa (o da frente), o de uma porta, o de trás — "
        "ou foi outra peça, tipo retrovisor, farol ou lanterna?",
        porque="é a peça que decide TODAS as perguntas do passo 6 (80%).",
    ),
    Pergunta(
        COMO_OCORREU,
        "Me conta como aconteceu? (uma pedra na estrada, alguém quebrou pra furtar, "
        "você chegou e já estava assim...)",
        # 📊 Continua SEM `opcoes` fixas: a lista de "como ocorreu" MUDA conforme
        # a peça e conforme a apólice — palavras do Founder: "quando escolho
        # parabrisas vem algumas situações... São diferentes da situação dos
        # vidros laterais". 📊 Medido: 11 causas no para-brisa, 12 no vidro de
        # porta, 14 na lanterna, 7 na lataria. §8.1 do mapa proíbe decorar a
        # lista, e ninguém a decora: quem decide é sempre o `GET /motivos-dano`
        # daquela peça.
        #
        # 🔴 O QUE MUDOU em 20/09/2026, e por quê: o relato livre não chegava à
        # lista. 📊 De 29 frases reais de segurado, **18 não casavam com causa
        # nenhuma** — e cada uma delas vira um pedido que NASCE e TRAVA, porque
        # não existe journey de continuação (o token do portal vive só em
        # memória). Então a pergunta continua sendo aberta, e a RESPOSTA passa a
        # ser devolvida no vocabulário que o portal usa: `mensagem_para_o_agente`
        # imprime as causas MEDIDAS daquela família (`CAUSAS_MEDIDAS`) e manda
        # escolher UMA, literal. 📊 Com isso, 44 de 44 causas medidas casam com a
        # lista ao vivo, e zero casam errado.
        como_devolver="registre em `como_ocorreu` UMA das causas listadas abaixo, "
                      "copiada LITERALMENTE (o portal só aceita as dela). Se o que "
                      "ele contou não decidir entre duas, pergunte oferecendo 3 ou 4 "
                      "delas em língua de gente — e nunca escolha por ele.",
        porque="📊 o relato livre não casa com a lista do portal em 18 de 29 frases "
               "reais, e parar depois de abrir o pedido é terminal.",
    ),
    Pergunta(
        DATA_DO_DANO,
        "Em que dia isso aconteceu?",
    ),
    Pergunta(
        ONDE_OCORREU,
        "Foi na cidade ou na estrada/rodovia?",
        opcoes=("urbano", "rodoviario"),
        porque="📊 campo `ondeOcorreuDano` do passo 4.",
    ),
    # 🔴 SPEC-EXTRA-001.10 P0-5 — o campo que trava o PATCH e que ninguém pedia.
    #
    # ⛔ SEM `aceita_nao_sabe`, de propósito: numa cidade não existe "não sei"
    # honesto. Quem está com o carro sabe em que cidade está. E o portal não
    # oferece saída: 📊 `CodigoCidade` vem preenchido nas 4 capturas, e a rede
    # credenciada é consultada POR cidade (`GET /clientes/cidades`).
    Pergunta(
        CIDADE_PARA_O_SERVICO,
        "Em qual cidade você quer fazer o serviço? (pode ser diferente da cidade "
        "onde você mora — se você estiver viajando, é onde o carro está agora)",
        como_devolver="registre em especificos: {\"cidade_para_o_servico\": \"Joinville/SC\"} "
                      "— só a cidade, com o estado se você souber",
        porque="📊 `CodigoCidade` é chave obrigatória do PATCH nas 4 capturas (20/09/2026), "
               "e a cidade é perguntada em 8 de 8 blocos do roteiro da atendente. O CEP da "
               "apólice é o de CASA: quem quebra o vidro viajando conserta onde está.",
        destino=DESTINO_QUESTIONARIO,
    ),
    # 🔴 SPEC-EXTRA-001.10.1 (D-E001101-05) — AQUI MORAVA A PERGUNTA DO
    # DOMICÍLIO ("o técnico vai até você ou você leva numa loja?"). O Founder
    # decidiu: domicílio FORA — o robô não pergunta e não oferece. Ela TRAVAVA o
    # pedido (estava em `TRANSPORTAVEIS`), e perguntar o que não se entrega era
    # prometer o que o produto não faz. `build_portal_params` manda "loja".
    Pergunta(
        CEP_DO_SEGURADO,
        "O CEP do segurado não veio no cadastro da InfoCap. Ele é OPCIONAL no portal, "
        "mas é o que habilita atendimento a domicílio — e domicílio é o que transforma "
        "o serviço em conveniência. NÃO pergunte ao segurado: resolva no cadastro.",
        de_quem=DO_PROVEDOR,
        porque="📊 rótulo do portal: 'Informe seu CEP para encontrarmos a unidade mais "
               "próxima e verificar se há disponibilidade de atendimento em domicílio'.",
    ),
)

# --------------------------------------------------------------------------
# O catálogo — passo 6 (80%), POR PEÇA
# --------------------------------------------------------------------------
# 📊 São condicionais e progressivas no portal: a pergunta 2 só nasce depois da
# 1. Aqui elas vêm todas de uma vez de propósito — perguntar as três na mesma
# conversa custa três mensagens; descobri-las uma a uma dentro do portal custa
# o atendimento inteiro.
#
# A chave é a IDENTIDADE devolvida por `identidade_peca`, não o texto da peça.
# 'vidro de porta', 'vidro da porta' e 'janela' caem todos em `lateral`.
_ESPECIFICAS_POR_IDENTIDADE: Dict[str, Tuple[Pergunta, ...]] = {
    # 📊 Medido em Tokio Marine, para-brisa (captura de 06/07/2026).
    "parabrisa": (
        Pergunta(
            POSICAO_DO_TRINCADO,
            "Onde fica a trinca no para-brisa: bem na frente do motorista, na frente "
            "do carona, no meio, ou perto das bordas?",
            opcoes=("Em frente ao motorista", "Em frente ao carona", "Nas bordas", "No centro"),
            aceita_nao_sabe=True,
        ),
        Pergunta(
            TAMANHO_DO_TRINCADO,
            "A trinca é maior ou menor que 10 cm? (mais ou menos o tamanho de um cartão "
            "de crédito) — é isso que decide se dá pra reparar ou se troca o vidro.",
            opcoes=("Maior que 10 cm", "Menor que 10 cm"),
            aceita_nao_sabe=True,
            porque="📊 maior = troca, menor = possibilidade de reparo. Errar aqui manda "
                   "o vidraceiro com a peça errada (mapa §4c). 📊 A régua dos 10 cm VEM DO "
                   "PORTAL: pergunta 8 da captura de 20/09/2026, com as opções "
                   "'MAIOR (TROCA DO VIDRO)' e 'MENOR (POSSIBILIDADE DE REPARO)'.",
        ),
        # 🔴 N-2 · D-E00110-02 — A DECISÃO DO SEGURADO, COLETADA ANTES.
        #
        # 📊 Medido em 20/09/2026: `POST /questionarios/regras-reparo` devolveu
        # `{"ExibirDialogDeReparo": true}` e o portal parou para perguntar. Se a
        # resposta não estiver aqui, a journey PARA nesse ponto — e nesse ponto o
        # `CodigoAtendimento` já existe. Parar depois do protocolo não é "tentar
        # de novo": o pedido já está na seguradora.
        #
        # ⚠️ E é uma decisão DELE, não nossa: o reparo é grátis e rápido, mas é
        # o vidro dele. A copy diz as três coisas que fazem alguém decidir —
        # custo, tempo e o que acontece se não ficar bom.
        Pergunta(
            ACEITA_REPARO,
            "Se a seguradora oferecer REPARO em vez de trocar o vidro, você topa tentar? "
            "O reparo é normalmente sem franquia — eu confirmo o valor quando a seguradora responder, leva uns 30 minutos e mantém o vidro "
            "original do carro. Se não ficar bom, você ainda pode pedir a troca depois.",
            opcoes=("sim", "nao"),
            como_devolver="registre em especificos: {\"aceita_reparo\": \"sim\"} ou "
                          "{\"aceita_reparo\": \"nao\"}",
            porque="📊 sem ela a journey para DEPOIS de o número do atendimento existir "
                   "(regras-reparo → ExibirDialogDeReparo=true, captura de 20/09/2026).",
            destino=DESTINO_REPARO,
        ),
        # 📊 MEDIDA no portal em 20/09/2026 — pergunta 140, tipo P, opções
        # 'NÃO SABE' (798) · 'SIM' (799) · 'NÃO' (800). É o único ADAS que a
        # tela perguntou; não se inventa os outros.
        Pergunta(
            SENSOR_DE_DIRECAO_OU_FAIXA,
            "Seu carro tem aviso de saída de faixa ou assistente de direção? "
            "(aquele que apita ou mexe no volante quando o carro sai da faixa sozinho)",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
            porque="📊 pergunta 140 do questionário do para-brisa (Yelum, 20/09/2026). "
                   "O vidro com câmera de ADAS é outra peça e precisa de recalibração.",
            destino=DESTINO_QUESTIONARIO,
        ),
        # 🔴 AS DUAS QUE A ATENDENTE FAZ E O PORTAL NÃO PERGUNTOU.
        #
        # 📊 A captura de 20/09/2026 trouxe TRÊS perguntas de para-brisa —
        # posição, 10 cm e sensor de direção — e **não** perguntou chuva nem
        # degradê. Elas continuam valendo, porque escolhem o VIDRO (linha do
        # catálogo), não porque o questionário as peça: por isso
        # `destino=DESTINO_CATALOGO` e `confirmada=False`. A resposta ajuda a
        # pedir a peça certa e **não** vai ao questionário enquanto uma tela não
        # a exibir.
        Pergunta(
            SENSOR_DE_CHUVA,
            "O para-brisa tem sensor de chuva? (quando começa a chover, as palhetas "
            "ligam sozinhas)",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
            porque="a atendente pergunta em 100% dos para-brisas; 📊 nenhuma tela capturada "
                   "a exibiu — serve para escolher o vidro certo no catálogo da apólice.",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
        Pergunta(
            FAIXA_DEGRADE,
            "O vidro tem aquela faixa escura degradê na parte de cima?",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
            porque="mesma razão do sensor de chuva: escolhe a linha do catálogo, e 📊 nenhuma "
                   "tela capturada a perguntou.",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
        Pergunta(
            VERSAO_DO_VEICULO,
            "A versão do veículo (ex.: 'Comfortline') sai do campo `Veículo` da InfoCap "
            "— 'NIVUS COMFORTLINE 1.0 200 TSI FLEX AUT'. A InfoCap não trouxe o veículo: "
            "isso é lacuna do provedor. NUNCA pergunte a versão ao segurado.",
            de_quem=DO_PROVEDOR,
            aceita_nao_sabe=True,
            porque="📊 'A versão do veículo é comfortline?' é pergunta de APÓLICE "
                   "disfarçada de pergunta de dano (mapa §4b).",
        ),
    ),
    # 📊 Medido em Yelum, vidro de porta (captura de 06/07/2026).
    #
    # INFERÊNCIA declarada: o portal mediu "VIDRO DE PORTA"; `identidade_peca`
    # junta porta, janela, basculante e ventarola sob `lateral`. Aplicamos as
    # três perguntas a toda a família. O erro possível é perguntar uma a mais
    # (custa uma mensagem, e a resposta é ignorada se a tela não pedir); o erro
    # oposto — não perguntar — é o que produziu 📊 33 paradas.
    "lateral": (
        Pergunta(
            PELICULA,
            "Esse vidro tem película? (aquele filme escuro, o insulfilm)",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
        ),
        Pergunta(
            PORTA_DIANTEIRA_OU_TRASEIRA,
            "É o vidro da porta da frente ou o da porta de trás?",
            opcoes=("DIANTEIRA", "TRASEIRA"),
            aceita_nao_sabe=True,
        ),
        Pergunta(
            LADO_MOTORISTA_OU_CARONA,
            "É do lado do motorista ou do lado do carona? (se quebraram os dois lados, "
            "me avisa — cada lado é um pedido separado)",
            opcoes=("Lado do motorista", "Lado do carona"),
            aceita_nao_sabe=True,
            porque="📊 o portal aceita UM item por atendimento e manda abrir nova "
                   "solicitação para o outro lado (mapa §3). O aviso vai junto da "
                   "pergunta porque é o único momento em que ele chega a tempo.",
        ),
        # 📊 O .docx separa "é vidro fixo?" e "é vidro sobe e desce?" em duas
        # linhas, e a razão é de CATÁLOGO: o portal lista `VIDRO DE PORTA`,
        # `VIDRO DE JANELA` e a `MÁQUINA` do vidro como itens diferentes. São
        # duas perguntas no roteiro e UM slot aqui — a resposta é a mesma coisa.
        Pergunta(
            VIDRO_FIXO_OU_SOBE_DESCE,
            "Esse vidro sobe e desce, ou é um vidro fixo (daqueles pequenos, "
            "coladinho, que não abre)?",
            opcoes=("sobe e desce", "fixo"),
            aceita_nao_sabe=True,
            como_devolver="registre em especificos: {\"vidro_fixo_ou_sobe_desce\": \"fixo\"}",
            porque="escolhe entre VIDRO DE PORTA, VIDRO DE JANELA e a MÁQUINA do vidro no "
                   "catálogo da apólice — 📊 nenhuma tela capturada perguntou isso.",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
    ),
    # ----------------------------------------------------------------------
    # SPEC-EXTRA-001.10 P1-3 — as famílias que saíram de
    # `PECAS_SEM_ESPECIFICAS_MAPEADAS` porque o roteiro da atendente as cobre.
    #
    # 🔴 A fonte é o .docx da atendente, não dedução: cada pergunta abaixo tem
    # uma linha correspondente lá, e o guarda G8 lê o arquivo em tempo de
    # execução e reprova se aparecer uma que não casa com slot nenhum.
    #
    # ⚠️ Quase todas são `DESTINO_CATALOGO` e `confirmada=False`: elas escolhem
    # a LINHA do `itens-cobertos` (📊 `RETROVISOR COMPLETO PINTADO COM PISCA`,
    # `CAPA DE RETROVISOR`, `LENTE`, `PISCA` são itens distintos), e nenhuma
    # captura mostrou um questionário para elas. Não perguntá-las é abrir o
    # pedido da peça errada; mandá-las ao questionário do portal seria inventar.
    # ----------------------------------------------------------------------
    "retrovisor": (
        Pergunta(
            LADO_MOTORISTA_OU_CARONA,
            "Qual retrovisor foi: o do lado do motorista (esquerdo) ou o do carona (direito)?",
            opcoes=("Lado do motorista", "Lado do carona"),
            porque="📊 o portal aceita UM item por atendimento e cada lado é um pedido.",
            destino=DESTINO_CATALOGO,
        ),
        Pergunta(
            CAPA_PINTADA_OU_FOSCA,
            "A capa do retrovisor é pintada na cor do carro, ou é aquela preta fosca "
            "sem pintura? Se for pintada, me diz a cor.",
            opcoes=("pintada", "preta fosca"),
            aceita_nao_sabe=True,
            como_devolver="registre em especificos: {\"capa_pintada_ou_fosca\": \"pintada - prata\"}",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
        Pergunta(
            RETROVISOR_TEM_PISCA,
            "Esse retrovisor tem seta (pisca) nele?",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
        Pergunta(
            REGULAGEM_DO_RETROVISOR,
            "A regulagem dele é elétrica (por botão) ou manual (na mão)?",
            opcoes=("eletrica", "manual"),
            aceita_nao_sabe=True,
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
        Pergunta(
            CAPA_AINDA_NA_PECA,
            "A capa ainda está no retrovisor, ou ela se soltou/quebrou junto?",
            opcoes=("ainda esta na peca", "soltou ou quebrou"),
            aceita_nao_sabe=True,
            porque="decide se o pedido é o retrovisor COMPLETO ou só a lente/capa.",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
    ),
    "farol": (
        Pergunta(
            LADO_MOTORISTA_OU_CARONA,
            "Qual farol foi: o do lado do motorista (esquerdo) ou o do carona (direito)?",
            opcoes=("Lado do motorista", "Lado do carona"),
            porque="📊 um item por atendimento; cada lado é um pedido separado.",
            destino=DESTINO_CATALOGO,
        ),
        # ⛔ O TIPO do farol (xenon, LED, milha) NÃO entra aqui de propósito.
        # 📊 O catálogo varia POR APÓLICE (21 × 30 itens em duas apólices da
        # mesma seguradora), e ele só existe DEPOIS de o atendimento abrir
        # (o header `token_autorizacao` nasce no POST /atendimentos). Perguntar
        # o tipo antes é gastar uma mensagem que pode não mudar nada: se a
        # apólice tem um farol só, a resposta é irrelevante. Essa restrição é a
        # P1-4, e ela roda com o catálogo na mão.
    ),
    "lanterna": (
        Pergunta(
            LADO_MOTORISTA_OU_CARONA,
            "Qual lanterna foi: a do lado do motorista (esquerda) ou a do carona (direita)?",
            opcoes=("Lado do motorista", "Lado do carona"),
            destino=DESTINO_CATALOGO,
        ),
        Pergunta(
            LANTERNA_BIPARTIDA_ONDE,
            "Em muitos carros a lanterna é partida em duas: uma parte na lataria e outra "
            "na tampa do porta-malas. No seu, a que quebrou é a da TAMPA ou a da LATARIA?",
            opcoes=("tampa do porta-malas", "lataria"),
            aceita_nao_sabe=True,
            como_devolver="registre em especificos: {\"lanterna_bipartida_onde\": \"tampa\"}",
            porque="📊 são duas linhas diferentes do catálogo; errar troca a peça errada.",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
    ),
    "vigia": (
        Pergunta(
            VIGIA_DESEMBACADOR_TERMICO,
            "O vidro de trás tem desembaçador? (aqueles fiozinhos na horizontal, que "
            "esquentam o vidro)",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
        Pergunta(
            PELICULA,
            "Esse vidro tem película? (aquele filme escuro, o insulfilm)",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
    ),
    "para_choque": (
        Pergunta(
            PARA_CHOQUE_DIANTEIRO_OU_TRASEIRO,
            "É o para-choque da frente ou o de trás?",
            opcoes=("dianteiro", "traseiro"),
            como_devolver="registre em especificos: "
                          "{\"para_choque_dianteiro_ou_traseiro\": \"dianteiro\"}",
            destino=DESTINO_CATALOGO,
        ),
    ),
    "lataria": (
        # 🔴 COBRADA ANTES (entra em `TRANSPORTAVEIS`): 📊 na lataria o
        # `CodigoAtendimento` nasce logo depois do PATCH, sem questionário
        # nenhum — e é o PATCH que leva `ServicosMartelinhoLataria`. Perguntar
        # quais peças depois é conversar sobre um pedido que já nasceu.
        Pergunta(
            PECAS_LATARIA,
            "Quais peças ficaram amassadas? Me manda todas de uma vez "
            "(ex.: porta dianteira esquerda, paralama esquerdo).",
            como_devolver="registre em especificos: "
                          "{\"pecas_lataria\": [\"porta dianteira esquerda\", \"paralama esquerdo\"]}",
            porque="📊 `ServicosMartelinhoLataria` é uma LISTA no PATCH, e o número do "
                   "atendimento nasce logo depois dele — perguntar depois é tarde.",
            destino=DESTINO_CATALOGO,
        ),
        Pergunta(
            LATARIA_MESMO_EVENTO,
            "Esses amassados foram todos no MESMO acontecimento, no mesmo momento e do "
            "mesmo lado do carro? (a seguradora não junta danos de lados diferentes num "
            "pedido só)",
            opcoes=("sim", "nao"),
            como_devolver="registre em especificos: {\"lataria_mesmo_evento\": \"sim\"}",
            porque="regra escrita no roteiro da atendente: danos de eventos diferentes são "
                   "pedidos diferentes. Juntá-los faz a seguradora recusar o conjunto.",
            destino=DESTINO_CATALOGO,
            confirmada=False,
        ),
    ),
}

# ==========================================================================
# 🔴 SPEC-EXTRA-001.10.1 C2 — AS PREFERÊNCIAS, coletadas antes e sem travar
# ==========================================================================
# 📊 Na captura lateral de 21/09 o portal abriu AGENDA depois do número e o
# `POST /agendamentos` concluiu (HAR [048]); na lataria ele ofereceu a opção de
# vistoria (`PermiteOpcaoVistoria:true`, HAR [089]). Nos dois casos quem decide
# é o segurado — e o token do portal EXPIRA (📊 401 dois dias depois). Com a
# preferência na mão, o robô resolve na MESMA sessão; sem ela, mostra as opções
# e CONTINUA quando ele responder (journey `continuar_atendimento`).
#
# ⚠️ `confirmada=False` e destino PREFERÊNCIA, de propósito: nenhuma tela do
# portal faz ESTA pergunta — ela é nossa, para escolher na agenda que o portal
# publica. Por isso NUNCA trava (`trava_o_pedido`): faltar a preferência custa
# uma continuação, não o atendimento.
#
# As famílias da agenda são as de TROCA (vidro de porta, para-brisa, vigia,
# lanterna, farol, retrovisor) — a lataria não agenda: ela vai à vistoria.
_PERGUNTA_PREFERENCIA_AGENDA = Pergunta(
    PREFERENCIA_AGENDA,
    "Se a seguradora já liberar agenda, a partir de que dia e em qual período "
    "(manhã ou tarde) fica melhor levar o carro?",
    opcoes=("manhã", "tarde", "tanto faz"),
    como_devolver="registre em especificos: {\"preferencia_agenda\": \"amanhã de manhã\"} "
                  "— com as palavras dele (hoje, amanhã, um dia da semana ou DD/MM, e "
                  "manhã/tarde/tanto faz); eu converto",
    porque="📊 o portal abre a agenda DEPOIS do número e o token dele expira: com a "
           "preferência, o robô agenda na mesma sessão (D-E001101-02).",
    destino=DESTINO_PREFERENCIA,
    confirmada=False,
)
_PERGUNTA_PREFERENCIA_VISTORIA = Pergunta(
    PREFERENCIA_VISTORIA,
    "Se a seguradora pedir vistoria, você prefere receber um link no celular para "
    "mandar fotos, ou levar o carro numa loja?",
    opcoes=("link", "loja"),
    como_devolver="registre em especificos: {\"preferencia_vistoria\": \"link\"} ou "
                  "{\"preferencia_vistoria\": \"loja\"}",
    porque="📊 lataria: `PermiteOpcaoVistoria:true` e o portal grava a preferência como "
           "ocorrência (HAR [092][093]) antes de mandar ao analista.",
    destino=DESTINO_PREFERENCIA,
    confirmada=False,
)
for _familia in ("parabrisa", "lateral", "vigia", "lanterna", "farol", "retrovisor"):
    _ESPECIFICAS_POR_IDENTIDADE[_familia] = (
        _ESPECIFICAS_POR_IDENTIDADE[_familia] + (_PERGUNTA_PREFERENCIA_AGENDA,))
_ESPECIFICAS_POR_IDENTIDADE["lataria"] = (
    _ESPECIFICAS_POR_IDENTIDADE["lataria"] + (_PERGUNTA_PREFERENCIA_VISTORIA,))
del _familia

# 📊 O que continua SEM perguntas: só o teto. Retrovisor, farol, lanterna e
# vigia saíram desta lista em 20/09/2026 porque o roteiro da atendente humana
# (.docx de intake) traz as perguntas delas — ver `_ESPECIFICAS_POR_IDENTIDADE`.
# A ausência continua sendo informação: `especificas_mapeadas()` devolve False
# para o teto, e a mensagem ao agente diz isso em voz alta em vez de inventar.
PECAS_SEM_ESPECIFICAS_MAPEADAS = ("teto",)

# ==========================================================================
# 🔴 A TABELA LOCAL DE FAMÍLIAS MORREU — P-E00110-C-01, 20/09/2026
# ==========================================================================
# Aqui moravam `lataria` e `para_choque`, em `_FAMILIAS_AINDA_FORA_DO_VOCABULARIO`,
# porque 📊 `identidade_peca` devolvia conjunto vazio para as duas. Elas foram
# para `_PECAS` de `portal_worker/journeys/vidros_lanternas.py`, que é o
# vocabulário único (CLAUDE.md §5), junto com a regra de precedência que o caso
# real exigia: *"amassei a porta e o paralama"* é **lataria**, e não o VIDRO
# lateral, porque a palavra `vidro` não está na frase.
#
# ⛔ Nada de segunda tabela volta aqui. Família nova entra em `_PECAS`, e o
# guarda que prova a precedência vive em
# `tests/test_e00110_a_costura_do_agente_ao_desfecho.py`.


# --------------------------------------------------------------------------
# Respondida, não respondida, e o "não sabe" no meio
# --------------------------------------------------------------------------
def e_nao_sabe(valor: Any) -> bool:
    """O segurado disse que não sabe (em qualquer das formas que ele usa)."""
    return str(valor or "").strip().lower() in _SINONIMOS_DE_NAO_SABE


def respondida(valor: Any, aceita_nao_sabe: bool = False) -> bool:
    """A pergunta já tem resposta?

    Três estados, e o do meio é o que costuma sumir:

      ausente      → não foi perguntada. Falta.
      "não sabe"   → FOI perguntada, e o segurado não sabe. Só encerra a pergunta
                     se o portal oferecer essa saída (`aceita_nao_sabe`).
      um valor     → respondida.

    A peça é o caso em que a distinção decide o atendimento: "não sei qual vidro
    quebrou" não é uma resposta que o portal aceite — é um caso para gente.
    """
    # ⚠️ LISTA VAZIA É AUSÊNCIA, e `_tem_valor` não sabia disso: `str([])` é
    # `"[]"`, que é texto e passaria como resposta. A lista de peças da lataria
    # é o primeiro campo do produto que guarda uma lista — sem esta linha,
    # `{"pecas_lataria": []}` contaria como respondida e o PATCH sairia com
    # `ServicosMartelinhoLataria: []` num pedido que é justamente sobre peças.
    if isinstance(valor, (list, tuple, set)):
        return any(_tem_valor(item) for item in valor)
    if not _tem_valor(valor):
        return False
    if e_nao_sabe(valor):
        return bool(aceita_nao_sabe)
    return True


# --------------------------------------------------------------------------
# A peça e suas específicas
# --------------------------------------------------------------------------
def _sem_acento(texto: str) -> str:
    """Só dobra texto — não decide peça nenhuma (ver a nota de precedência)."""
    import unicodedata

    cru = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " " + " ".join("".join(c if c.isalnum() else " " for c in cru).lower().split()) + " "


def _identidades(peca: str) -> List[str]:
    """As identidades do texto. 🔴 UM vocabulário, e ele é `identidade_peca`.

    Esta função existia para consultar uma tabela local quando o vocabulário
    ficava mudo sobre lataria e para-choque. As duas famílias entraram em
    `_PECAS` (P-E00110-C-01) e a tabela local morreu: agora há um leitor só.
    """
    return sorted(identidade_peca(str(peca or "")))


def especificas_mapeadas(peca: str) -> bool:
    """As perguntas do 80% desta peça foram MEDIDAS?

    False para peça vazia, para peça ambígua ("luz" pode ser farol ou lanterna) e
    para toda peça de `PECAS_SEM_ESPECIFICAS_MAPEADAS`. False **não** é erro nem
    bloqueio: é a declaração honesta de que o caminho adaptativo vai ler a tela
    real e descobrir ali.
    """
    ids = _identidades(peca)
    return len(ids) == 1 and ids[0] in _ESPECIFICAS_POR_IDENTIDADE


def especificas_da_peca(peca: str) -> Tuple[Pergunta, ...]:
    """As perguntas do 80% que ESTA peça faz nascer. Vazio quando não mapeadas."""
    ids = _identidades(peca)
    if len(ids) != 1:
        return ()
    return _ESPECIFICAS_POR_IDENTIDADE.get(ids[0], ())


def universais() -> Tuple[Pergunta, ...]:
    """O catálogo que não depende da peça. Leitura pública do que hoje é `_UNIVERSAIS`.

    Existe para que a `description` da tool seja GERADA daqui (P0-5, as três
    verdades) em vez de escrita à mão num terceiro lugar.
    """
    return _UNIVERSAIS


def catalogo_de_familias() -> Dict[str, Tuple[Pergunta, ...]]:
    """`{família: perguntas}` — cópia rasa, para ninguém editar o catálogo por acidente."""
    return dict(_ESPECIFICAS_POR_IDENTIDADE)


def pergunta_do_campo(campo: str) -> Optional[Pergunta]:
    """A `Pergunta` que responde por este campo, onde quer que ela esteja."""
    alvo = str(campo or "").strip()
    for p in _UNIVERSAIS:
        if p.campo == alvo:
            return p
    for perguntas in _ESPECIFICAS_POR_IDENTIDADE.values():
        for p in perguntas:
            if p.campo == alvo:
                return p
    return None


def familia_da_peca(peca: str) -> str:
    """A FAMÍLIA desta peça, ou "" quando o texto não nomeia exatamente uma.

    É o nome que `_ESPECIFICAS_POR_IDENTIDADE` usa como chave — o mesmo que
    aparece no relatório e nos guardas. Existe para que ninguém precise repetir
    `sorted(identidade_peca(...))[0]` e, no caminho, escrever a segunda regra.
    """
    ids = _identidades(peca)
    return ids[0] if len(ids) == 1 else ""


def peca_ambigua(peca: str) -> bool:
    """O texto nomeia mais de uma peça ("a luz quebrou" = farol ou lanterna)."""
    return len(_identidades(peca)) > 1


def peca_conhecida(peca: str) -> bool:
    """O vocabulário único consegue dizer QUAL peça é?

    Exatamente uma identidade. Duas outras respostas, e as duas continuam sendo
    pergunta:

      **zero** — o texto não nomeia peça nenhuma. `"quebrou o vidro"` é o relato
      mais comum que existe e cai aqui: num portal de vidros, "vidro" é o nome
      do balcão, não o da peça.

      **mais de uma** — ambígua. `"a luz quebrou"` é farol ou lanterna.

    Um texto que não identifica peça não é uma peça respondida: é o problema
    adiado até o dropdown do passo 4, onde `match_option` para. 📊 E quando ele
    NÃO parou, o estrago foi pior: três acionamentos de produção casaram
    'vidro da porta' com 'VIDRO PARABRISA - CARGA' porque um token genérico
    bastava. Uma frase agora custa dez segundos; o dropdown custa o atendimento.
    """
    return len(_identidades(peca)) == 1


# --------------------------------------------------------------------------
# O coração
# --------------------------------------------------------------------------
def o_que_falta(peca: str, ja_sei: Optional[Dict[str, Any]] = None) -> List[Pergunta]:
    """O que ainda precisa ser perguntado para este acionamento NÃO travar.

    `peca` é o que o segurado disse que quebrou (texto livre; vazio se ainda não
    se sabe). `ja_sei` é tudo que já se apurou — o que o segurado respondeu MAIS
    os fatos que a InfoCap trouxe (`veiculo`, `cep`).

    Devolve as perguntas na ordem de conversa. Lista vazia = pode entrar no
    portal: nada do que ele vai perguntar está em aberto.

    Três regras que a assinatura não mostra:

    **A peça manda.** Sem peça (ou com peça ambígua), as específicas não entram —
    não porque sejam opcionais, mas porque não há como saber quais são.

    **Peça não mapeada não bloqueia.** Retrovisor, farol, lanterna, vigia e teto
    voltam só com as universais. Ver `especificas_mapeadas`.

    **A descrição não é pergunta.** Ela é composta (`compor_descricao`), e o
    mínimo de 30 caracteres do portal fica garantido por construção assim que
    peça e relato existem — que são duas perguntas desta lista.
    """
    ja_sei = dict(ja_sei or {})
    peca = str(peca or ja_sei.get(PECA) or "").strip()
    ja_sei.setdefault(PECA, peca)

    faltam: List[Pergunta] = []
    for pergunta in _UNIVERSAIS:
        if pergunta.campo == PECA:
            # A peça não se dá por respondida porque o campo tem texto: ela se
            # dá por respondida quando o vocabulário ÚNICO consegue identificá-la
            # (ver `peca_conhecida`). Um texto que não nomeia peça é o problema
            # adiado até o dropdown.
            if not peca_conhecida(peca):
                faltam.append(pergunta)
            continue
        if not respondida(ja_sei.get(pergunta.onde_mora), pergunta.aceita_nao_sabe):
            faltam.append(pergunta)

    # Sem peça identificada as específicas não entram — não por serem opcionais,
    # mas porque não há como saber quais são.
    if not peca_conhecida(peca):
        return faltam

    for pergunta in especificas_da_peca(peca):
        if not respondida(ja_sei.get(pergunta.onde_mora), pergunta.aceita_nao_sabe):
            faltam.append(pergunta)
    return faltam


def para_o_segurado(faltam: List[Pergunta]) -> List[Pergunta]:
    """Só o que se pergunta a uma pessoa. Lacuna de provedor NUNCA vira mensagem
    de WhatsApp — é o que impede o produto de pedir ao segurado a versão do carro
    dele, que já está na apólice."""
    return [p for p in (faltam or []) if p.de_quem == DO_SEGURADO]


def lacunas_do_provedor(faltam: List[Pergunta]) -> List[Pergunta]:
    """O que a InfoCap deveria ter trazido e não trouxe. É trabalho da corretora
    ou da integração, não do segurado."""
    return [p for p in (faltam or []) if p.de_quem == DO_PROVEDOR]


# --------------------------------------------------------------------------
# A descrição — composta, nunca perguntada
# --------------------------------------------------------------------------
def compor_descricao(ja_sei: Optional[Dict[str, Any]] = None) -> str:
    """O texto do passo 4, montado só com o que já se sabe.

    📊 O portal exige mínimo de 30 e máximo de 2000 caracteres. Pedir ao segurado
    que "escreva mais" para satisfazer um contador de caracteres é a pergunta que
    este produto existe para não fazer — então a descrição é DERIVADA.

    Nada é inventado: entram a peça (como ele a nomeou), o relato dele, a data e
    o local. Se o relato já passa de 30 caracteres, ele vai inteiro, com as
    palavras do segurado.

    O mínimo é garantido por aritmética, não por sorte: com peça e relato
    presentes o texto começa em `"Dano em " + peça + ". O segurado relatou: " +
    relato + "."` = 8+1+1 + 1 + 20+1+1 = **33 caracteres no pior caso**. E peça e
    relato (`como_ocorreu`) são duas perguntas de `o_que_falta` — quando elas
    estão respondidas, o mínimo está pago.
    """
    ja_sei = ja_sei or {}
    relato = str(ja_sei.get(DESCRICAO) or "").strip()
    if len(relato) >= MINIMO_DA_DESCRICAO:
        return relato[:MAXIMO_DA_DESCRICAO]

    if not relato:
        relato = str(ja_sei.get(COMO_OCORREU) or "").strip()

    partes: List[str] = []
    peca = str(ja_sei.get(PECA) or "").strip()
    if peca:
        partes.append(f"Dano em {peca}.")
    if relato:
        partes.append(f"O segurado relatou: {relato}.")
    data = str(ja_sei.get(DATA_DO_DANO) or "").strip()
    if data:
        partes.append(f"Ocorrido em {data}.")
    onde = str(ja_sei.get(ONDE_OCORREU) or "").strip()
    if onde:
        partes.append(f"Local: {onde}.")
    return " ".join(partes)[:MAXIMO_DA_DESCRICAO]


# --------------------------------------------------------------------------
# A mensagem que o agente lê
# --------------------------------------------------------------------------
def _marca_nao_sabe(pergunta: Pergunta) -> str:
    """A saída de "não sabe" só se anuncia na pergunta que a tem."""
    return "   [se ele nao souber, registre 'nao sabe']" if pergunta.aceita_nao_sabe else ""


def causas_para_oferecer(peca: str = "") -> Tuple[str, ...]:
    """As causas de dano MEDIDAS para a família desta peça.

    🔴 É **dica de coleta**, nunca a lista final: quem manda é o
    `GET /motivos-dano` daquela peça, naquela apólice, na hora. O que estas
    palavras compram é o agente perguntar ANTES usando o vocabulário que o
    portal vai usar — e é isso que evita o pedido nascer e travar.

    Importa de `portal_worker.journeys.vidros_api`, que é onde o contrato
    medido do portal mora. ⛔ Nenhuma segunda tabela aqui (CLAUDE.md §5).
    """
    try:
        from portal_worker.journeys.vidros_api import causas_medidas_de
    except Exception:  # noqa: BLE001
        return ()
    return tuple(causas_medidas_de(familia_da_peca(peca)))


def _linhas_das_causas(pergunta: Pergunta, peca: str) -> List[str]:
    """As causas, já em forma de instrução, só quando a pergunta é a da causa."""
    if pergunta.campo != COMO_OCORREU:
        return []
    causas = causas_para_oferecer(peca)
    if not causas:
        return []
    familia = familia_da_peca(peca)
    cabecalho = (f"  causas que o portal aceita para {familia or 'esta peca'} "
                 f"(📊 medidas; a lista real vem da apolice dele):")
    return [cabecalho] + [f"      · {c}" for c in causas]


def mensagem_para_o_agente(faltam: List[Pergunta], peca: str = "") -> str:
    """Traduz a lista em ordem de trabalho para o LLM. "" quando não há nada a dizer.

    Uma pergunta em destaque (a próxima), o resto listado para ele coletar na
    mesma conversa, e as duas proibições que o mapa impõe: não perguntar o que
    está na apólice, e não inventar pergunta para peça não mapeada.

    Uma de cada vez é instrução literal: 📊 o passo 6 do portal revela as
    perguntas uma a uma, e um segurado que recebe três perguntas numa mensagem
    responde uma.
    """
    faltam = list(faltam or [])
    perguntas = para_o_segurado(faltam)
    lacunas = lacunas_do_provedor(faltam)
    if not perguntas and not lacunas and especificas_mapeadas(peca):
        return ""

    linhas: List[str] = []
    if perguntas:
        linhas.append(
            f"Faltam dados do acionamento: ainda nao da para abrir o portal "
            f"({len(perguntas)} pergunta(s) em aberto). Colete TUDO nesta conversa, "
            "uma pergunta por mensagem, antes de me chamar de novo — depois que o "
            "portal abre, cada dado que falta custa o atendimento inteiro."
        )
        linhas.append("")
        linhas.append("PERGUNTE AGORA (use estas palavras, ou palavras tao simples quanto):")
        linhas.append(f'  "{perguntas[0].texto}"{_marca_nao_sabe(perguntas[0])}')
        if perguntas[0].opcoes:
            linhas.append(f"  respostas que o portal aceita: {' / '.join(perguntas[0].opcoes)}")
        if perguntas[0].como_devolver:
            linhas.append(f"  {perguntas[0].como_devolver}")
        # 🔴 A causa do dano é a única pergunta cujas respostas MUDAM por peça —
        # por isso elas não cabem em `opcoes` e entram aqui, já filtradas pela
        # família. Ver `causas_para_oferecer`.
        for linha in _linhas_das_causas(perguntas[0], peca):
            linhas.append(linha)
        if len(perguntas) > 1:
            linhas.append("")
            linhas.append("E na sequencia, uma de cada vez, ainda vou precisar destas:")
            for p in perguntas[1:]:
                linhas.append(f'  · "{p.texto}"{_marca_nao_sabe(p)}')
                # Uma pergunta cuja resposta nao tem como voltar e uma pergunta
                # feita a toa: o segurado responde e o schema descarta. Onde o
                # caminho de volta nao e obvio, ele vai escrito.
                if p.como_devolver:
                    linhas.append(f"      ({p.como_devolver})")
        linhas.append("")
        # A marca vai POR PERGUNTA, e nao numa frase geral, porque a frase geral
        # criava um laco: mandada em bloco, ela autoriza registrar "nao sabe" em
        # `como_ocorreu` — que o portal NAO deixa pular. O agente registraria,
        # este mesmo gate recusaria, e a pergunta voltaria para sempre.
        linhas.append(
            "Onde estiver escrito [se ele nao souber...], essa e a saida legitima — e SO "
            "depois de perguntar: responder 'nao sabe' por conta propria degrada o servico "
            "(o portal deixa de saber qual vidro pedir). Nas perguntas SEM essa marca a "
            "saida nao existe: reformule com exemplos concretos, porque registrar 'nao "
            "sabe' nelas traz o acionamento de volta para a mesma pergunta."
        )

    # 🔴 A HONESTIDADE SOBRE O QUE AINDA NÃO FOI VISTO NUMA TELA.
    #
    # Sem esta linha, uma pergunta de catálogo não-confirmada pareceria exigência
    # do portal — e o agente cobraria o segurado por ela como cobra o CPF. Ela é
    # útil (escolhe a peça certa) e é dispensável (o portal não a pede).
    # ⚠️ As PREFERÊNCIAS (agenda/vistoria) também são não-confirmadas, mas não
    # escolhem peça nenhuma — dizer que "servem para pedir a peça certa" seria o
    # texto mentindo sobre elas. Têm a linha própria logo abaixo.
    nao_confirmadas = [p for p in perguntas
                       if not p.confirmada and p.destino != DESTINO_PREFERENCIA]
    preferencias = [p for p in perguntas if p.destino == DESTINO_PREFERENCIA]
    if preferencias:
        linhas.append("")
        linhas.append(
            "Destas, " + ", ".join(f"'{p.campo}'" for p in preferencias) + " NAO travam o "
            "pedido: servem para eu resolver sozinho o que a seguradora oferecer DEPOIS "
            "do numero (agenda ou vistoria). Se o segurado nao souber, siga assim mesmo "
            "— eu mostro as opcoes e continuo quando ele escolher.")
    if nao_confirmadas:
        linhas.append("")
        linhas.append(
            "Destas, " + ", ".join(f"'{p.campo}'" for p in nao_confirmadas) + " servem para "
            "pedir a PECA CERTA (elas escolhem o item no catalogo da apolice) e o portal "
            "NAO as exige: se o segurado nao souber ou nao responder, siga assim mesmo."
        )

    if lacunas:
        linhas.append("")
        linhas.append("NAO pergunte ao segurado (isto e lacuna do cadastro, nao dele):")
        for p in lacunas:
            linhas.append(f"  · {p.texto}")

    if peca and not especificas_mapeadas(peca):
        linhas.append("")
        if peca_ambigua(peca):
            linhas.append(
                f"A peca '{peca}' esta AMBIGUA (pode ser mais de uma coisa) — confirme "
                "com o segurado exatamente qual peca quebrou antes de me chamar."
            )
        elif peca_conhecida(peca):
            linhas.append(
                f"As perguntas especificas de '{peca}' AINDA NAO FORAM MAPEADAS neste "
                "portal. NAO invente nenhuma: o robo vai ler a tela real e, se ela "
                "perguntar algo que eu nao tenho, eu volto e te digo exatamente o que "
                "perguntar."
            )
        else:
            # DIZER POR QUE a peca voltou. Sem esta frase o agente ve que mandou
            # `peca` e que estou pedindo `peca` de novo, conclui que e ruido, e
            # reenvia o MESMO texto — o laco que nenhuma recusa pode criar.
            #
            # E nao chamar isto de "peca nao mapeada" tambem importa: 'quebrou o
            # vidro' nao e uma peca sem mapa, e um texto que nao nomeia peca
            # nenhuma. Confundir os dois faria o agente esperar que eu lesse a
            # tela para descobrir algo que so o segurado sabe.
            linhas.append(
                f"Voce me mandou peca='{peca}', e isso NAO nomeia uma peca: num portal de "
                "vidros, 'vidro' e o nome do balcao, nao da peca. Nao reenvie o mesmo "
                "texto — pergunte QUAL vidro (para-brisa, de porta, vigia) ou qual peca "
                "(retrovisor, farol, lanterna, teto)."
            )

    linhas.append("")
    linhas.append(
        "Nunca pergunte ao segurado o que esta na apolice: placa, chassi, versao do "
        "veiculo, CEP e endereco eu ja busco sozinho na InfoCap."
    )
    return "\n".join(linhas).strip()
